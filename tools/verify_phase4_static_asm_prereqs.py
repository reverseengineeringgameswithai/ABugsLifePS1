#!/usr/bin/env python3
"""Independent hard-truth verifier for the static-ASM prerequisite receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_int(value: Any) -> int:
    return value if isinstance(value, int) else int(value, 0)


def reject_absolute_strings(value: Any, location: str = "$") -> list[str]:
    failures: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            failures.extend(reject_absolute_strings(child, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            failures.extend(reject_absolute_strings(child, f"{location}[{index}]"))
    elif isinstance(value, str) and value.startswith("/"):
        failures.append(location)
    return failures


def independent_candidate_set(image: bytes, base: int, text_size: int,
                              extents: list[dict[str, Any]]) -> set[tuple[str, int, int, str]]:
    result: set[tuple[str, int, int, str]] = set()
    for offset in range(0, text_size, 4):
        word = struct.unpack_from("<I", image, 0x800 + offset)[0]
        address = base + offset
        kind = None
        register = (word >> 21) & 31
        if word >> 26 == 0 and word & 0x001FFFFF == 8:
            kind = "jr_return" if register == 31 else "jr"
        elif word >> 26 == 0 and word & 0x001F07FF == 9:
            kind = "jalr"
        if kind is None:
            continue
        range_type = "unclaimed"
        for extent in extents:
            if parse_int(extent["start"]) <= address < parse_int(extent["end"]):
                range_type = extent["range_type"]
                break
        result.add((kind, address, register, range_type))
    return result


def verify(root: Path, artifact_path: Path, rebuild: bool) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if artifact.get("schema") != "phase4-static-asm-prerequisites/1":
        failures.append("schema mismatch")
    absolute_locations = reject_absolute_strings(artifact)
    if absolute_locations:
        failures.append("absolute paths at " + ", ".join(absolute_locations))

    paths = artifact["inputs"]["paths"]
    hashes = artifact["inputs"]["sha256"]
    for relative in paths.values():
        candidate = root / relative
        if not candidate.is_file():
            failures.append(f"missing input {relative}")
        elif sha256(candidate) != hashes.get(relative):
            failures.append(f"input hash mismatch {relative}")

    image_path = root / paths["image"]
    image = image_path.read_bytes()
    if image[:8] != b"PS-X EXE":
        failures.append("image is not PS-X EXE")
        base = text_size = 0
    else:
        base, text_size = struct.unpack_from("<II", image, 0x18)
    partition = artifact["image_partition"]
    if partition["claimed_bytes"] + partition["unclassified_bytes"] != text_size:
        failures.append("byte partition does not equal loaded text")
    gaps = sorted(
        (parse_int(item["start"]), parse_int(item["end"]))
        for item in partition["gaps"]
    )
    if sum(end - start for start, end in gaps) != partition["unclassified_bytes"]:
        failures.append("gap interval sum mismatch")

    candidates = artifact["instruction_candidate_census"]["candidates"]
    extents_by_name: dict[str, dict[str, Any]] = {}
    for row in candidates:
        name = row["extent"]
        if name is not None and name not in extents_by_name:
            # Candidate rows carry the type but not bounds; the independently
            # rebuilt artifact below proves extent identity.  For the raw scan,
            # classify by the candidate row's exact address/type map.
            extents_by_name[name] = {"range_type": row["range_type"]}
    reported = {
        (row["kind"], parse_int(row["pc"]), int(row["register"]), row["range_type"])
        for row in candidates
    }
    # Independent opcode decoding.  Type labels are matched using the reported
    # address map here and are independently re-derived by --rebuild below.
    address_types = {parse_int(row["pc"]): row["range_type"] for row in candidates}
    independent: set[tuple[str, int, int, str]] = set()
    for offset in range(0, text_size, 4):
        word = struct.unpack_from("<I", image, 0x800 + offset)[0]
        address = base + offset
        register = (word >> 21) & 31
        if word >> 26 == 0 and word & 0x001FFFFF == 8:
            kind = "jr_return" if register == 31 else "jr"
        elif word >> 26 == 0 and word & 0x001F07FF == 9:
            kind = "jalr"
        else:
            continue
        independent.add((kind, address, register, address_types.get(address, "missing")))
    if reported != independent:
        failures.append("exact raw instruction-candidate set mismatch")

    typed_sites = {
        (row["kind"], parse_int(row["pc"]))
        for row in candidates
        if row["kind"] in {"jr", "jalr"} and row["range_type"] in {"code", "thunk"}
    }
    indirect = artifact["indirect_control"]
    inventory_sites = {
        ("jr", parse_int(row["pc"])) for row in indirect["jr_sites"]
    } | {
        ("jalr", parse_int(row["pc"])) for row in indirect["jalr_sites"]
    }
    if typed_sites != inventory_sites:
        failures.append("typed site inventory differs from candidate census")

    rebuilt_equal = None
    if rebuild and not failures:
        with tempfile.TemporaryDirectory(prefix="phase4-static-asm-verify-") as raw_temp:
            output = Path(raw_temp) / "rebuilt.json"
            command = [
                "python3",
                paths["c_probe"].replace("phase4_static_asm_probe.c", "phase4_static_asm_prereqs.py"),
                "--root", ".",
                "--image", paths["image"],
                "--functions", paths["functions"],
                "--repaired-extents", paths["repaired_extents"],
                "--dispatch-map", paths["dispatch_map"],
                "--jr-analysis", paths["jr_analysis"],
                "--contract", paths["contract"],
                "--c-probe", paths["c_probe"],
                "--output", str(output),
            ]
            subprocess.run(command, cwd=root, check=True)
            rebuilt = json.loads(output.read_text(encoding="utf-8"))
            rebuilt_equal = rebuilt == artifact
            if not rebuilt_equal:
                failures.append("clean rebuild differs from committed artifact")

    return {
        "schema": "phase4-static-asm-prerequisite-verdict/1",
        "artifact": artifact_path.relative_to(root).as_posix(),
        "artifact_sha256": sha256(artifact_path),
        "exact_raw_candidate_set_verified": "exact raw instruction-candidate set mismatch" not in failures,
        "typed_site_inventory_verified": "typed site inventory differs from candidate census" not in failures,
        "input_hashes_verified": not any(item.startswith("input hash mismatch") or item.startswith("missing input") for item in failures),
        "rebuilt_equal": rebuilt_equal,
        "artifact_verification_passed": not failures,
        "semantic_image_ownership_complete": artifact["verdicts"]["semantic_image_ownership_complete"],
        "indirect_target_sets_complete": artifact["verdicts"]["indirect_target_sets_complete"],
        "item2_ready_for_review": False,
        "strict_frontier_closed": False,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--artifact", type=Path, default=Path("analysis/phase4_static_asm_prerequisites.json"))
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    artifact = args.artifact if args.artifact.is_absolute() else root / args.artifact
    verdict = verify(root, artifact, args.rebuild)
    rendered = json.dumps(verdict, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if verdict["artifact_verification_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
