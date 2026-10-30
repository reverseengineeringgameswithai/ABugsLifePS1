#!/usr/bin/env python3
"""Run the Phase-4 Ghidra exporter in disposable external projects.

Retail bytes, Ghidra projects, TSV specifications, logs, and raw high p-code
remain under ``--external-root``.  Only a bounded comparison receipt may be
written to the repository.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import phase4_static_frontier as frontier


ROOT = frontier.ROOT
INDEX_PATH = frontier.INDEX_OUTPUT
EXPORTER_PATH = ROOT / "ghidra/scripts/ExportPhase4StaticFrontier.java"
RECEIPT_PATH = ROOT / "analysis/phase4_ghidra_regeneration_receipt.json"
HEADLESS = "/app/lib/ghidra/support/analyzeHeadless"
APP_ID = "org.ghidra_sre.Ghidra"
EXPECTED_STATUSES = {
    "high_pcode": 1108,
    "instruction_fallback_required": 4,
    "not_applicable": 78,
}
EXPECTED_RANGE_STATUSES = {
    ("code", "high_pcode"): 1054,
    ("code", "instruction_fallback_required"): 4,
    ("data", "not_applicable"): 78,
    ("thunk", "high_pcode"): 54,
}
EXPECTED_RAW_RECORD_CONTRACT_SHA256 = \
    "a7a7911bb2272ad36742511408195ee778f5dc9cec43c30b1633ce581b04e9f6"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def render(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def json_sha256(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def raw_record_contract_sha256(records: dict[str, str]) -> str:
    return json_sha256({
        "schema": "abl-phase4-ghidra-raw-record-contract/1",
        "records": [{"key": key, "sha256": records[key]} for key in sorted(records)],
    })


def pcode_fingerprint(operations: list[str]) -> str:
    digest = hashlib.sha256()
    for operation in operations:
        digest.update(operation.encode())
        digest.update(b"\n")
    return digest.hexdigest()


def checked_external_root(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("--external-root must be absolute")
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("--external-root must be outside the repository")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def flatpak_identity() -> dict:
    result = subprocess.run(
        ["flatpak", "info", APP_ID], text=True, capture_output=True, check=True)
    fields = {}
    for line in result.stdout.splitlines():
        match = re.match(r"\s*([^:]+):\s*(.*?)\s*$", line)
        if match:
            fields[match.group(1)] = match.group(2)
    return {"app_id": APP_ID, "version": fields.get("Version"),
            "commit": fields.get("Commit")}


def image_rows(index: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in index["records"]:
        grouped.setdefault(row["image_id"], []).append(row)
    return {key: sorted(value, key=lambda row: row["entry"])
            for key, value in sorted(grouped.items())}


def write_spec(path: Path, rows: list[dict]) -> None:
    lines = ["# start\tend\trange_type\tname"]
    for row in rows:
        safe_name = str(row.get("name") or "").replace("\t", " ").replace("\n", " ")
        lines.append(f"{row['entry']}\t{row['end']}\t{row['range_type']}\t{safe_name}")
    path.write_text("\n".join(lines) + "\n")


def run_image(run_root: Path, image_id: str, rows: list[dict], image: dict,
              runtime_gp: str) -> dict:
    image_root = run_root / image_id
    image_root.mkdir(parents=True, exist_ok=True)
    spec = image_root / "functions.tsv"
    raw = image_root / "raw.json"
    log = image_root / "headless.log"
    script_log = image_root / "script.log"
    write_spec(spec, rows)
    lo = min(int(row["entry"], 0) for row in rows)
    hi = max(int(row["end"], 0) for row in rows)
    project_location = image_root / "project"
    project_location.mkdir(exist_ok=True)
    binary = ROOT / image["path"]
    command = [
        "flatpak", "run", f"--filesystem={ROOT}:ro",
        f"--filesystem={run_root}", f"--command={HEADLESS}", APP_ID,
        str(project_location), "phase4", "-import", str(binary),
        "-processor", "MIPS:LE:32:default", "-loader", "BinaryLoader",
        "-loader-baseAddr", image["file_va_base"],
        "-scriptPath", str(EXPORTER_PATH.parent),
        "-postScript", EXPORTER_PATH.name, str(spec), str(raw), runtime_gp,
        f"0x{lo:08X}", f"0x{hi:08X}", image_id,
        "-analysisTimeoutPerFile", "900", "-max-cpu", "2", "-deleteProject",
        "-log", str(log), "-scriptlog", str(script_log),
    ]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    (image_root / "console.log").write_text(result.stdout)
    if result.returncode != 0 or not raw.is_file():
        tail = "\n".join(result.stdout.splitlines()[-20:])
        raise RuntimeError(f"Ghidra export failed for {image_id} ({result.returncode})\n{tail}")
    document = json.loads(raw.read_text())
    output_rows = document.get("functions") or []
    if len(output_rows) != len(rows):
        raise RuntimeError(f"{image_id}: raw row count {len(output_rows)} != {len(rows)}")
    expected_keys = [(row["entry"], row["end"], row["range_type"]) for row in rows]
    actual_keys = [(row.get("entry"), row.get("end"), row.get("range_type"))
                   for row in output_rows]
    if actual_keys != expected_keys:
        raise RuntimeError(f"{image_id}: raw function identities differ from census spec")
    statuses = Counter(row.get("status") for row in output_rows)
    allowed = {"high_pcode", "instruction_fallback_required", "not_applicable"}
    if set(statuses) - allowed:
        raise RuntimeError(f"{image_id}: unclassified Ghidra statuses {dict(statuses)}")
    return {
        "image_id": image_id, "input_sha256": image["sha256"],
        "file_va_base": image["file_va_base"], "rows": len(rows),
        "raw_sha256": sha256(raw), "raw_size": raw.stat().st_size,
        "statuses": dict(sorted(statuses.items())),
    }


def run_export(external_root: Path, run_id: str, selected: set[str] | None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise ValueError("run ID may contain only letters, digits, dot, underscore, and dash")
    index = json.loads(INDEX_PATH.read_text())
    if not index.get("valid"):
        raise ValueError("retained static index is invalid")
    toolchain = frontier.load_yaml(frontier.CONFIG_PATH)["toolchain"]
    identity = flatpak_identity()
    if identity["version"] != str(toolchain["version"]) or \
            identity["commit"] != toolchain["flatpak_commit"]:
        raise RuntimeError(f"Ghidra identity drift: {identity}")
    grouped = image_rows(index)
    unknown = (selected or set()) - set(grouped)
    if unknown:
        raise ValueError(f"unknown image IDs: {sorted(unknown)}")
    chosen = sorted(selected or grouped)
    run_root = external_root / run_id
    if run_root.exists() and any(run_root.iterdir()):
        raise ValueError(f"fresh run directory required: {run_root}")
    run_root.mkdir(parents=True, exist_ok=True)
    meta = {row["image_id"]: row for row in index["images"]}
    images = []
    for position, image_id in enumerate(chosen, 1):
        print(f"[phase4-ghidra] {position}/{len(chosen)} {image_id}", flush=True)
        images.append(run_image(run_root, image_id, grouped[image_id], meta[image_id],
                                meta[image_id]["runtime_gp"]))
    statuses = Counter()
    for image in images:
        statuses.update(image["statuses"])
    manifest = {
        "schema": "abl-phase4-ghidra-external-run/1",
        "run_id": run_id, "source_index_sha256": sha256(INDEX_PATH),
        "exporter_sha256": sha256(EXPORTER_PATH), "toolchain": identity,
        "images": images,
        "summary": {"images": len(images), "records": sum(row["rows"] for row in images),
                    "statuses": dict(sorted(statuses.items()))},
        "raw_output_policy": "external_only", "complete": len(images) == len(chosen),
    }
    (run_root / "manifest.json").write_text(render(manifest))
    print(f"[phase4-ghidra] wrote external manifest for {len(images)} images", flush=True)
    return manifest


def validate_manifest(external_root: Path, run_id: str, index: dict) -> dict:
    """Recompute every manifest claim from canonical index rows and raw exports."""
    errors: list[str] = []
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        return {"manifest": {}, "raw_sha256": {},
                "errors": ["RUN_ID_INVALID"], "valid": False}
    manifest_path = external_root / run_id / "manifest.json"
    if not manifest_path.is_file():
        return {"manifest": {}, "raw_sha256": {},
                "errors": ["MANIFEST_MISSING"], "valid": False}
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {"manifest": {}, "raw_sha256": {},
                "errors": [f"MANIFEST_INVALID:{exc}"], "valid": False}

    grouped = image_rows(index)
    image_meta = {row["image_id"]: row for row in index["images"]}
    expected_ids = set(grouped)
    tool = frontier.load_yaml(frontier.CONFIG_PATH)["toolchain"]
    expected_toolchain = {
        "app_id": tool["app_id"], "version": str(tool["version"]),
        "commit": tool["flatpak_commit"],
    }
    exact_fields = {
        "schema": "abl-phase4-ghidra-external-run/1",
        "run_id": run_id,
        "source_index_sha256": sha256(INDEX_PATH),
        "exporter_sha256": sha256(EXPORTER_PATH),
        "toolchain": expected_toolchain,
        "raw_output_policy": "external_only",
        "complete": True,
    }
    for key, expected in exact_fields.items():
        if manifest.get(key) != expected:
            errors.append(f"MANIFEST_{key.upper()}_DRIFT")

    manifest_images = manifest.get("images")
    if not isinstance(manifest_images, list):
        errors.append("MANIFEST_IMAGES_INVALID")
        manifest_images = []
    manifest_ids = [row.get("image_id") for row in manifest_images
                    if isinstance(row, dict)]
    if len(manifest_ids) != len(set(manifest_ids)):
        errors.append("MANIFEST_IMAGE_DUPLICATE")
    if set(manifest_ids) != expected_ids:
        errors.append("MANIFEST_IMAGE_SET_DRIFT")
    by_id = {row.get("image_id"): row for row in manifest_images
             if isinstance(row, dict) and row.get("image_id") in expected_ids}

    raw_hashes = {}
    raw_record_hashes = {}
    raw_statuses = Counter()
    raw_range_statuses = Counter()
    raw_records = 0
    allowed = {"high_pcode", "instruction_fallback_required", "not_applicable"}
    for image_id in sorted(expected_ids):
        row = by_id.get(image_id)
        if row is None:
            continue
        raw_path = external_root / run_id / image_id / "raw.json"
        if not raw_path.is_file():
            errors.append(f"RAW_MISSING:{image_id}")
            continue
        actual_hash = sha256(raw_path)
        actual_size = raw_path.stat().st_size
        raw_hashes[image_id] = actual_hash
        expected_row_fields = {
            "image_id": image_id,
            "input_sha256": image_meta[image_id]["sha256"],
            "file_va_base": image_meta[image_id]["file_va_base"],
            "rows": len(grouped[image_id]),
            "raw_sha256": actual_hash,
            "raw_size": actual_size,
        }
        for key, expected in expected_row_fields.items():
            if row.get(key) != expected:
                errors.append(f"IMAGE_{key.upper()}_DRIFT:{image_id}")
        try:
            raw = json.loads(raw_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"RAW_INVALID:{image_id}:{exc}")
            continue
        if raw.get("schema") != "abl-phase4-ghidra-raw/1":
            errors.append(f"RAW_SCHEMA_DRIFT:{image_id}")
        if raw.get("image_id") != image_id:
            errors.append(f"RAW_IMAGE_ID_DRIFT:{image_id}")
        if raw.get("gp") != image_meta[image_id]["runtime_gp"]:
            errors.append(f"RAW_GP_DRIFT:{image_id}")
        functions = raw.get("functions")
        if not isinstance(functions, list):
            errors.append(f"RAW_FUNCTIONS_INVALID:{image_id}")
            continue
        expected_keys = [(item["entry"], item["end"], item["range_type"])
                         for item in grouped[image_id]]
        actual_keys = [(item.get("entry"), item.get("end"), item.get("range_type"))
                       for item in functions if isinstance(item, dict)]
        if actual_keys != expected_keys:
            errors.append(f"RAW_FUNCTION_IDENTITIES_DRIFT:{image_id}")
        for spec, item in zip(grouped[image_id], functions):
            if not isinstance(item, dict):
                errors.append(f"RAW_FUNCTION_INVALID:{image_id}")
                continue
            raw_record_hashes[f"{image_id}:{spec['entry']}"] = json_sha256({
                "image_id": image_id, "function": item})
            required_fields = {
                "entry", "end", "range_type", "name", "status",
                "pcode_op_count", "pcode_fingerprint", "pcode_ops", "calls", "memory_ops",
            }
            missing = sorted(required_fields - set(item))
            if missing:
                errors.append(
                    f"RAW_FIELDS_MISSING:{image_id}:{spec['entry']}:{','.join(missing)}")
            if item.get("name") != str(spec.get("name") or ""):
                errors.append(f"RAW_NAME_DRIFT:{image_id}:{spec['entry']}")
            status = item.get("status")
            range_type = spec["range_type"]
            allowed_statuses = ({"not_applicable"} if range_type == "data" else
                                {"high_pcode", "instruction_fallback_required"})
            if status not in allowed_statuses:
                errors.append(
                    f"RAW_STATUS_RANGE_MISMATCH:{image_id}:{spec['entry']}:"
                    f"{range_type}:{status}")
            raw_range_statuses[(range_type, status)] += 1
            pcode_ops = item.get("pcode_ops")
            calls = item.get("calls")
            memory_ops = item.get("memory_ops")
            if not isinstance(pcode_ops, list) or not all(
                    isinstance(value, str) and value for value in pcode_ops):
                errors.append(f"RAW_PCODE_OPS_INVALID:{image_id}:{spec['entry']}")
            if not isinstance(calls, list) or not all(
                    isinstance(value, str) and re.match(r"^CALL(IND)?\|", value)
                    for value in calls):
                errors.append(f"RAW_CALLS_INVALID:{image_id}:{spec['entry']}")
            if not isinstance(memory_ops, list) or not all(
                    isinstance(value, str) and re.match(r"^(LOAD|STORE)\|", value)
                    for value in memory_ops):
                errors.append(f"RAW_MEMORY_OPS_INVALID:{image_id}:{spec['entry']}")
            if status == "high_pcode":
                if not isinstance(item.get("pcode_op_count"), int) or not isinstance(
                        pcode_ops, list) or item.get("pcode_op_count") != len(pcode_ops) \
                        or not pcode_ops:
                    errors.append(f"RAW_PCODE_COUNT_INVALID:{image_id}:{spec['entry']}")
                if not isinstance(item.get("pcode_fingerprint"), str) or not isinstance(
                        pcode_ops, list) or item.get("pcode_fingerprint") != pcode_fingerprint(
                            pcode_ops):
                    errors.append(f"RAW_PCODE_FINGERPRINT_INVALID:{image_id}:{spec['entry']}")
                if isinstance(pcode_ops, list) and calls != [
                        value for value in pcode_ops if re.match(r"^CALL(IND)?\|", value)]:
                    errors.append(f"RAW_CALLS_DERIVATION_DRIFT:{image_id}:{spec['entry']}")
                if isinstance(pcode_ops, list) and memory_ops != [
                        value for value in pcode_ops if re.match(r"^(LOAD|STORE)\|", value)]:
                    errors.append(f"RAW_MEMORY_OPS_DERIVATION_DRIFT:{image_id}:{spec['entry']}")
            elif status == "instruction_fallback_required":
                if not str(item.get("error") or "").strip():
                    errors.append(f"RAW_FALLBACK_REASON_MISSING:{image_id}:{spec['entry']}")
                if item.get("pcode_op_count") != 0 or item.get("pcode_fingerprint") is not None \
                        or pcode_ops != [] or calls != [] or memory_ops != []:
                    errors.append(f"RAW_FALLBACK_CONTENT_INVALID:{image_id}:{spec['entry']}")
            elif status == "not_applicable":
                if item.get("pcode_op_count") != 0 or item.get("pcode_fingerprint") is not None \
                        or pcode_ops != [] or calls != [] or memory_ops != []:
                    errors.append(f"RAW_NONCODE_CONTENT_INVALID:{image_id}:{spec['entry']}")
        statuses = Counter(item.get("status") for item in functions
                           if isinstance(item, dict))
        if set(statuses) - allowed:
            errors.append(f"RAW_STATUS_INVALID:{image_id}")
        expected_statuses = dict(sorted(statuses.items()))
        if row.get("statuses") != expected_statuses:
            errors.append(f"IMAGE_STATUSES_DRIFT:{image_id}")
        raw_statuses.update(statuses)
        raw_records += len(functions)

    recomputed_summary = {
        "images": len(raw_hashes), "records": raw_records,
        "statuses": dict(sorted(raw_statuses.items())),
    }
    if manifest.get("summary") != recomputed_summary:
        errors.append("MANIFEST_SUMMARY_DRIFT")
    if dict(sorted(raw_statuses.items())) != EXPECTED_STATUSES:
        errors.append("RAW_EXPECTED_STATUS_CENSUS_DRIFT")
    if dict(raw_range_statuses) != EXPECTED_RANGE_STATUSES:
        errors.append("RAW_EXPECTED_RANGE_STATUS_CENSUS_DRIFT")
    contract_sha256 = raw_record_contract_sha256(raw_record_hashes)
    if contract_sha256 != EXPECTED_RAW_RECORD_CONTRACT_SHA256:
        errors.append("RAW_RECORD_CONTRACT_DRIFT")
    return {
        "manifest": manifest, "manifest_sha256": sha256(manifest_path),
        "raw_sha256": raw_hashes, "summary": recomputed_summary,
        "raw_record_contract_sha256": contract_sha256,
        "errors": sorted(set(errors)), "valid": not errors,
    }


def comparison(external_root: Path, first: str, second: str) -> dict:
    index = json.loads(INDEX_PATH.read_text())
    validated = [validate_manifest(external_root, run_id, index)
                 for run_id in (first, second)]
    left, right = validated
    expected_ids = set(image_rows(index))
    identities_match = (set(left["raw_sha256"]) == set(right["raw_sha256"])
                        == expected_ids)
    raw_matches = identities_match and all(
        left["raw_sha256"][key] == right["raw_sha256"][key]
        for key in expected_ids)
    full_corpus = (left.get("summary", {}).get("images") ==
                   right.get("summary", {}).get("images") == len(expected_ids)
                   and left.get("summary", {}).get("records") ==
                   right.get("summary", {}).get("records") == len(index["records"]))
    tool = frontier.load_yaml(frontier.CONFIG_PATH)["toolchain"]
    toolchain = {"app_id": tool["app_id"], "version": str(tool["version"]),
                 "commit": tool["flatpak_commit"]}
    return {
        "schema": "abl-phase4-ghidra-regeneration-receipt/1",
        "run_ids": [first, second],
        "source_index_sha256": sha256(INDEX_PATH),
        "exporter_sha256": sha256(EXPORTER_PATH),
        "toolchain": toolchain,
        "run_manifest_sha256": [row.get("manifest_sha256") for row in validated],
        "run_validation_errors": {
            run_id: row["errors"] for run_id, row in zip((first, second), validated)},
        "summary": left.get("summary", {}),
        "raw_record_contract_sha256": left.get("raw_record_contract_sha256"),
        "image_identities_match": identities_match,
        "raw_exports_byte_identical": raw_matches,
        "full_corpus": full_corpus,
        "raw_output_policy": "external_only",
        "valid": left["valid"] and right["valid"]
                 and identities_match and raw_matches and full_corpus,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", type=Path, required=True)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--run-id")
    actions.add_argument("--compare", nargs=2, metavar=("RUN_A", "RUN_B"))
    parser.add_argument("--images", help="comma-separated image IDs; default is full corpus")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    external_root = checked_external_root(args.external_root)
    if args.run_id:
        selected = set(args.images.split(",")) if args.images else None
        run_export(external_root, args.run_id, selected)
        return 0
    document = comparison(external_root, args.compare[0], args.compare[1])
    print(render(document), end="")
    if args.write_receipt:
        RECEIPT_PATH.write_text(render(document))
        print(f"[phase4-ghidra] wrote {RECEIPT_PATH.relative_to(ROOT)}")
    return 0 if document["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
