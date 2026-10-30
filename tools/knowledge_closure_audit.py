#!/usr/bin/env python3
"""Retroactive Phase-0..2 knowledge-closure inventory and validator.

Writes two committed, freshness-tested artifacts:
  analysis/phase0_2_knowledge_closure_report.json
  analysis/phase0_2_external_fixture_set.json

Default mode reports honestly and exits zero when the report matches the declared
partial/blocked states.  --strict exits non-zero while any knowledge phase is not
closed, a referenced fixture lacks a central pin/classification, a confirmed address
lacks an authoritative machine representation, or tracked Python imports untracked
local source.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixture_reference_sets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "analysis/phase0_2_knowledge_closure.yaml"
REPORT = ROOT / "analysis/phase0_2_knowledge_closure_report.json"
FIXTURE_SET = ROOT / "analysis/phase0_2_external_fixture_set.json"
VALID_REQ = {"complete", "partial", "blocked", "not_applicable"}
FIXTURE_SUFFIXES = (".sav",)
MOVIE_FIXTURE = re.compile(r"\.movie[^/]*\.json$")
OPERATOR_ROOT = Path(os.environ.get(
    "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads" / "ABL"))).resolve()

PHASE_PATTERNS = {
    "phase0": ["analysis/phase0*", "tools/build_identity.py", "tools/build_baselines.json",
               "tools/disc_provenance.json", "mod/build.py", "mod/module_matrix.yaml",
               "tests/test_build_identity.py", "tests/test_repro_manifest.py"],
    "phase1": ["analysis/mechanics_baseline.yaml", "analysis/phase1*",
               "tools/mechanics_baseline.py", "tools/phase1*", "tests/test_mechanics_baseline.py",
               "tests/test_phase1_census.py"],
    "phase2": ["analysis/phase2*", "tools/phase2*", "tests/test_phase2*",
               "tools/scenarios/duckstation/stage_identity*", "tools/launch_repro_playback.sh"],
}

# This is the clean-checkout regeneration surface exercised by the complete
# ``pytest -m local_media`` pass.  Keeping both generators/inputs and products in
# the retained report makes a post-regeneration drift visible to Phase 3's gate,
# instead of allowing the historical phase labels to hide it.
DURABILITY_PATHS = {
    "analysis/asm_to_c_queue.json",
    "analysis/code_coverage.md",
    "analysis/decomp_candidates.json",
    "analysis/functions.csv",
    "analysis/functions.json",
    "analysis/memory_map.json",
    "analysis/overlay_decomp_progress.json",
    "analysis/phase2_spin_disproof.json",
    "analysis/phase0_2_knowledge_closure.yaml",
    "config/overlays.yml",
    "config/fixture_reference_sets.yaml",
    "config/segments.yml",
    "symbols/re_symbols.sym",
    "tools/asm_to_c_candidates.py",
    "tools/build_memory_map.py",
    "tools/build_overlay.py",
    "tools/build_psx_exe.py",
    "tools/decomp_candidates.py",
    "tools/function_census.py",
    "tools/fixture_reference_sets.py",
    "tools/phase2_spin_disproof.py",
    "tools/provision_clean_checkout_inputs.py",
    "tools/re_baseline.py",
    "tools/re_baseline_inputs.sha256",
    "tools/validate_build.py",
    "tools/repro_inputs.sha256",
}

# Phase-4 evidence is normally outside this Phase-0..2 inventory.  These exact
# cross-phase consumers are admitted because their external fixtures must remain in the
# one central preservation manifest rather than growing a second, weaker pin store.
ADDITIONAL_FIXTURE_CONSUMERS = {
    "analysis/phase4_f01_original_oracle.json",
}

CROSS_PHASE_FIXTURE_PINS = {
    "movies/Phase4/Interpreter/Any% Runs/LEVEL01_AntHill_FromBoot.movie.json": {
        "sha256": "b29ae83945aaea1d59c03095867376130a3ac3eefcf4b6042a2c36b8369e2e24",
        "size": 5062842,
        "media_class": "pristine_serial",
    },
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_lines(*args: str) -> list[str]:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).splitlines()


def tracked_paths() -> tuple[set[str], str]:
    try:
        return set(git_lines("ls-files")), "git_index"
    except (subprocess.CalledProcessError, FileNotFoundError):
        # `git archive` intentionally has no .git directory. Every file in that
        # archive is tracked by construction, so a filesystem census is the
        # authoritative equivalent (transient caches are never archive inputs).
        files = {str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()
                 and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts}
        return files, "git_archive_filesystem"


def durable_text(rel: str) -> str:
    """Read committed bytes when Git exists; archive bytes otherwise.

    Dirty tracked files are operator WIP and must not make the committed report
    claim that a clean checkout contains knowledge which exists only locally.
    """
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD:{rel}"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return (ROOT / rel).read_text(errors="ignore")


def inventory_files(tracked: set[str]) -> dict:
    out = {}
    generated_self = {
        "analysis/phase0_2_knowledge_closure_report.json",
        "analysis/phase0_2_external_fixture_set.json",
    }
    for phase, patterns in PHASE_PATTERNS.items():
        files = sorted({p for p in tracked if p not in generated_self and
                        any(fnmatch.fnmatch(p, pat) for pat in patterns)})
        out[phase] = [{"path": p, "sha256": sha(ROOT / p), "tracked": True} for p in files]
    durability = sorted(DURABILITY_PATHS & tracked)
    out["clean_checkout_regeneration"] = [
        {"path": p, "sha256": sha(ROOT / p), "tracked": True}
        for p in durability
    ]
    return out


def local_import_gaps(tracked: set[str]) -> list[dict]:
    local = {p.stem: str(p.relative_to(ROOT)) for p in (ROOT / "tools").glob("*.py")}
    gaps = set()
    for rel in sorted(p for p in tracked if p.startswith("tools/") and p.endswith(".py")):
        try:
            tree = ast.parse((ROOT / rel).read_text())
        except (SyntaxError, UnicodeDecodeError):
            continue
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module.split(".")[0])
        for name in names:
            target = local.get(name)
            if target and target not in tracked:
                gaps.add((rel, name, target))
    return [{"importer": a, "module": b, "untracked_path": c}
            for a, b, c in sorted(gaps)]


def validate_provisioned_sources(matrix: dict, tracked: set[str]) -> list[dict]:
    """Prove every operator-root source provision became exact tracked bytes.

    The external source location records provenance only.  A clean checkout does
    not need that operator path: the hash-pinned, non-copyrighted bytes themselves
    must now be tracked and are the durable input.
    """
    errors = []
    seen = set()
    for row in matrix.get("provisioned_external_source_inputs", []):
        rel = row.get("path")
        if not rel or rel in seen:
            errors.append({"path": rel, "reason": "missing or duplicate path"})
            continue
        seen.add(rel)
        path = ROOT / rel
        reasons = []
        if rel not in tracked:
            reasons.append("path is not tracked")
        if not path.is_file():
            reasons.append("path is absent")
        else:
            if path.stat().st_size != row.get("size"):
                reasons.append(
                    f"size {path.stat().st_size} != declared {row.get('size')}")
            actual = sha(path)
            if actual != row.get("sha256"):
                reasons.append(f"sha256 {actual} != declared {row.get('sha256')}")
        try:
            Path(row.get("source") or "").resolve().relative_to(OPERATOR_ROOT)
        except (TypeError, ValueError):
            reasons.append("source is outside the declared operator root")
        if not str(row.get("media_class") or "").startswith("noncopyrighted_"):
            reasons.append("media_class is not noncopyrighted")
        if reasons:
            errors.append({"path": rel, "reasons": reasons})
    return errors


def validate_external_local_media_inputs(matrix: dict, tracked: set[str]) -> list[dict]:
    """Validate ignored retail-derived inputs and their preservation contract.

    Unlike provisioned source, these bytes must *not* be tracked.  They must be
    present for a closure run, match the operator-root source and central pin,
    and name tracked generators and consumers.  This turns missing r2 listings
    into a hard durability error rather than a local-media skip.
    """
    errors = []
    seen = set()
    for row in matrix.get("external_local_media_inputs", []):
        rel = row.get("path")
        reasons = []
        if not rel or rel in seen:
            reasons.append("missing or duplicate path")
        seen.add(rel)
        path = ROOT / str(rel or "")
        source = Path(row.get("source") or "")
        try:
            source.resolve().relative_to(OPERATOR_ROOT)
        except (TypeError, ValueError):
            reasons.append("source is outside the declared operator root")
        if rel in tracked:
            reasons.append("retail-derived local media must stay outside Git")
        if row.get("media_class") not in {
                "derived_retail_metadata", "derived_retail_disassembly"}:
            reasons.append("media_class must identify derived retail metadata/disassembly")
        generator = str(row.get("generator") or "").split(maxsplit=1)[0]
        if generator not in tracked:
            reasons.append(f"generator is not tracked: {generator!r}")
        consumers = row.get("consumers") or []
        if not consumers:
            reasons.append("no consumers declared")
        for consumer in consumers:
            if consumer not in tracked:
                reasons.append(f"consumer is not tracked: {consumer}")
        for label, candidate in (("workspace", path), ("operator source", source)):
            if not candidate.is_file():
                reasons.append(f"{label} path is absent")
                continue
            if candidate.stat().st_size != row.get("size"):
                reasons.append(
                    f"{label} size {candidate.stat().st_size} != {row.get('size')}")
            actual = sha(candidate)
            if actual != row.get("sha256"):
                reasons.append(
                    f"{label} sha256 {actual} != {row.get('sha256')}")
        if reasons:
            errors.append({"path": rel, "reasons": reasons})
    return errors


def external_manifest_rows(matrix: dict) -> list[dict]:
    """Expand centrally pinned hash manifests into ordinary fixture rows."""
    rows = []
    for spec in matrix.get("external_local_media_manifests", []):
        manifest = ROOT / spec["path"]
        prefix = spec["prefix"]
        if not manifest.is_file():
            continue
        for line in manifest.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and len(parts[0]) == 64 and parts[1].startswith(prefix):
                source = Path(spec["source_root"]) / parts[1]
                rows.append({
                    "path": parts[1],
                    "source": str(source),
                    "sha256": parts[0],
                    "size": source.stat().st_size if source.is_file() else None,
                    "media_class": spec["media_class"],
                    "generator": spec["generator"],
                    "consumers": (list(spec.get("consumers") or []) or
                                  [spec["consumer_manifest"]]),
                    "manifest": spec["path"],
                    "provisioner": spec["provisioner"],
                })
    return rows


def validate_external_local_media_manifests(matrix: dict, tracked: set[str]) -> list[dict]:
    errors = []
    for spec in matrix.get("external_local_media_manifests", []):
        reasons = []
        required_tracked = [spec.get("path"), spec.get("generator")]
        required_tracked.extend(spec.get("consumers") or [])
        if spec.get("consumer_manifest"):
            required_tracked.append(spec["consumer_manifest"])
        for value in required_tracked:
            rel = str(value or "").split(maxsplit=1)[0]
            if rel not in tracked:
                reasons.append(f"manifest dependency is not tracked: {rel!r}")
        source_root = Path(spec.get("source_root") or "")
        try:
            source_root.resolve().relative_to(OPERATOR_ROOT)
        except (TypeError, ValueError):
            reasons.append("source_root is outside the declared operator root")
        rows = external_manifest_rows({"external_local_media_manifests": [spec]})
        if not rows:
            reasons.append("manifest contains no pinned rows for its prefix")
        if spec.get("consumer_manifest"):
            declared = set()
            consumer = yaml.safe_load((ROOT / spec["consumer_manifest"]).read_text())
            for item in consumer.get("attempted") or []:
                source = item.get("source")
                if isinstance(source, str) and source.startswith(spec["prefix"]):
                    declared.add(source)
                for part in item.get("parts") or []:
                    source = part.get("source")
                    if isinstance(source, str) and source.startswith(spec["prefix"]):
                        declared.add(source)
            pinned = {row["path"] for row in rows}
            if pinned != declared:
                reasons.append(
                    f"manifest/config source sets differ: "
                    f"missing={sorted(declared-pinned)[:8]} "
                    f"extra={sorted(pinned-declared)[:8]}")
        for row in rows:
            for label, candidate in (("workspace", ROOT / row["path"]),
                                     ("operator source", Path(row["source"]))):
                if not candidate.is_file():
                    reasons.append(f"{label} absent: {row['path']}")
                    continue
                if sha(candidate) != row["sha256"]:
                    reasons.append(f"{label} hash mismatch: {row['path']}")
        if reasons:
            errors.append({"path": spec.get("path"), "reasons": reasons})
    return errors


def recursive_strings(node, *, skip_keys=frozenset()):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            if k in skip_keys:
                continue
            yield from recursive_strings(k, skip_keys=skip_keys)
            yield from recursive_strings(v, skip_keys=skip_keys)
    elif isinstance(node, list):
        for v in node:
            yield from recursive_strings(v, skip_keys=skip_keys)


def normalize_fixture(value: str) -> str | None:
    value = value.split(" @f", 1)[0].strip()
    if Path(value).is_absolute():
        return None  # transient scratch path, not a preservation fixture
    if any(value.endswith(s) for s in FIXTURE_SUFFIXES) or MOVIE_FIXTURE.search(value):
        return value
    return None


def fixture_consumers() -> dict[str, set[str]]:
    consumers: dict[str, set[str]] = defaultdict(set)
    mechanics = yaml.safe_load((ROOT / "analysis/mechanics_baseline.yaml").read_text())
    reference_sets = fixture_reference_sets.load()
    fixture_reference_sets.validate_rows(mechanics["rows"], reference_sets)
    for row in mechanics["rows"]:
        for value in fixture_reference_sets.resolve_row(row, reference_sets):
            if fx := normalize_fixture(str(value)):
                consumers[fx].add(f"mechanics:{row['id']}")
    findings = yaml.safe_load((ROOT / "config/phase3_findings.yaml").read_text())
    for finding in findings.get("findings", []):
        for value in (finding.get("provenance") or {}).get("fixtures") or []:
            if fx := normalize_fixture(str(value)):
                consumers[fx].add(f"phase3_finding:{finding['id']}")
    # Phase-3 generators may consume fixtures indirectly through a Phase-2
    # baseline. Scan their retained evidence too so the central manifest names
    # the real downstream consumers instead of stopping at the intermediate JSON.
    for path in sorted((ROOT / "analysis").glob("phase[123]_*.json")):
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        # phase3_gate_audit retains this audit's previous findings under this
        # exact key. They are gate output, not fixture-source references; only
        # suppress that self-referential field in that one generated consumer.
        skip_keys = ({"missing_fixture_pins"}
                     if path.name == "phase3_gate_audit.json" else set())
        for value in recursive_strings(doc, skip_keys=skip_keys):
            if fx := normalize_fixture(value):
                consumers[fx].add(str(path.relative_to(ROOT)))
    for rel in sorted(ADDITIONAL_FIXTURE_CONSUMERS):
        path = ROOT / rel
        try:
            doc = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for value in recursive_strings(doc):
            if fx := normalize_fixture(value):
                consumers[fx].add(rel)
    return consumers


def phase3_artifact_generators() -> dict[str, set[str]]:
    """Map retained Phase-3 outputs back to their owning generators."""
    path = ROOT / "analysis/phase3_evidence_inventory.json"
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    owners: dict[str, set[str]] = defaultdict(set)
    for generator, row in (doc.get("generators") or {}).items():
        for output in row.get("outputs") or []:
            rel = output.get("path") if isinstance(output, dict) else output
            if rel:
                owners[rel].add(generator)
    return owners


def build_fixture_set(tracked: set[str]) -> tuple[dict, list[dict]]:
    audit = json.loads((ROOT / "analysis/phase2_fixture_audit.json").read_text())
    central = {**audit["saves"], **audit["movies"]}
    consumers = fixture_consumers()
    indirect_generators = phase3_artifact_generators()
    generator_text = {}
    for rel in tracked:
        if rel.startswith("tools/") and rel.endswith((".py", ".sh")):
            try:
                generator_text[rel] = durable_text(rel)
            except OSError:
                pass
    entries, missing = {}, []
    for rel in sorted(consumers):
        pin = central.get(rel) or CROSS_PHASE_FIXTURE_PINS.get(rel)
        if not pin:
            missing.append({"path": rel, "consumers": sorted(consumers[rel]),
                            "reason": "absent from analysis/phase2_fixture_audit.json"})
            continue
        generators = {
            path for path, body in generator_text.items()
            if rel in body or Path(rel).name in body
        }
        for consumer in consumers[rel]:
            generators.update(indirect_generators.get(consumer, set()))
        entries[rel] = {"sha256": pin["sha256"], "size": pin["size"],
                        "media_class": pin["media_class"],
                        "consumers": sorted(consumers[rel]),
                        "generator_references": sorted(generators),
                        "capture_origin": ("repo_generator_or_replay_tool" if generators
                                           else "operator_owned_external_capture"),
                        "preservation_required": True,
                        "copyrighted_or_operator_owned": True}
    matrix = yaml.safe_load(MATRIX.read_text())
    for row in matrix.get("external_local_media_inputs", []):
        rel = row["path"]
        if rel in entries:
            missing.append({"path": rel, "reason": "duplicate central fixture path"})
            continue
        generator = str(row["generator"]).split(maxsplit=1)[0]
        entries[rel] = {
            "sha256": row["sha256"],
            "size": row["size"],
            "media_class": row["media_class"],
            "consumers": list(row["consumers"]),
            "generator_references": [generator],
            "regeneration_command": row["generator"],
            "capture_origin": "repo_generator_or_replay_tool",
            "preservation_required": True,
            "copyrighted_or_operator_owned": True,
        }
    for row in external_manifest_rows(matrix):
        rel = row["path"]
        entries[rel] = {
            "sha256": row["sha256"],
            "size": row["size"],
            "media_class": row["media_class"],
            "consumers": row["consumers"],
            "generator_references": [row["generator"]],
            "regeneration_command": row["generator"],
            "provision_command": row["provisioner"],
            "pin_manifest": row["manifest"],
            "capture_origin": "repo_generator_or_replay_tool",
            "preservation_required": True,
            "copyrighted_or_operator_owned": True,
        }
    doc = {"_comment": "Declared external preservation set for every Phase-1/2 evidence fixture reference. Bytes stay outside Git; hashes, media class, consumers, and preservation requirement are authoritative here. Regenerate: tools/knowledge_closure_audit.py --write.",
           "generated": date.today().isoformat(), "entries": entries,
           "missing_central_pins": missing}
    return doc, missing


def address_promotion(tracked: set[str]) -> tuple[list[dict], list[dict]]:
    mechanics = yaml.safe_load((ROOT / "analysis/mechanics_baseline.yaml").read_text())
    candidates: dict[str, set[str]] = defaultdict(set)
    for row in mechanics["rows"]:
        evidence = set(row.get("evidence") or [])
        if not evidence.intersection({"runtime_trace", "static_code", "pristine_observation", "asset_disc"}):
            continue
        for binding in row.get("bindings") or []:
            binding_text = str(binding)
            range_bounds = set()
            for lo, hi in re.findall(
                    r"(0x[89][0-9A-Fa-f]{7})\s*[-–]\s*(0x[89][0-9A-Fa-f]{7})",
                    binding_text):
                range_bounds.update((lo.lower(), hi.lower()))
            for addr in re.findall(r"0x[89][0-9A-Fa-f]{7}", binding_text):
                if addr.lower() in range_bounds:
                    continue  # scan/search extent, not a discovered site
                candidates[addr.lower()].add(row["id"])
    roots = [ROOT / "symbols/re_symbols.sym", ROOT / "analysis/functions.csv",
             ROOT / "analysis/memory_map.json", ROOT / "analysis/overlay_symbols.json",
             ROOT / "config/semantic_state.yaml", ROOT / "config/record_types.yaml",
             ROOT / "config/confirmed_sites.yaml"]
    roots += list((ROOT / "asm/hand_written").glob("*.s"))
    roots += list((ROOT / "src").rglob("*.c")) + list((ROOT / "src_re").glob("*.c"))
    roots = sorted((p for p in roots if p.exists() and
                    str(p.relative_to(ROOT)) in tracked),
                   key=lambda p: str(p.relative_to(ROOT)))
    texts = []
    for p in roots:
        try:
            rel = str(p.relative_to(ROOT))
            raw = durable_text(rel).lower()
            if p.name == "re_symbols.sym":
                # The symbol format is `8004719c name`, without a 0x prefix.
                raw += "\n" + "\n".join(
                    f"0x{line.split()[0]}" for line in raw.splitlines()
                    if re.match(r"^[0-9a-f]{8}\s", line))
            texts.append((rel, raw))
        except OSError:
            pass
    represented, missing = [], []
    for addr, rows in sorted(candidates.items()):
        hits = [rel for rel, text in texts if addr in text]
        item = {"address": addr, "registry_rows": sorted(rows), "machine_layers": hits[:12]}
        (represented if hits else missing).append(item)
    return represented, missing


def validate_matrix(doc: dict) -> list[str]:
    errors = []
    reqs = doc["requirements"]
    ids = set()
    for item in doc["deliverables"]:
        if item["id"] in ids:
            errors.append(f"duplicate deliverable {item['id']}")
        ids.add(item["id"])
        if set(item["requirements"]) != set(reqs):
            errors.append(f"{item['id']}: requirement keys differ from the eight-part definition")
        for key, status in item["requirements"].items():
            if status not in VALID_REQ:
                errors.append(f"{item['id']}.{key}: invalid status {status}")
        for group, refs in item.get("inventory", {}).items():
            for ref in refs:
                if not (ROOT / ref).exists():
                    errors.append(f"{item['id']}.{group}: missing {ref}")
    for dependency, info in doc.get("known_closed_dependencies", {}).items():
        if not (ROOT / dependency).exists():
            errors.append(f"closed dependency missing: {dependency}")
        for consumer in info.get("consumers", []):
            path = ROOT / consumer
            if not path.exists() or Path(dependency).stem not in path.read_text(errors="ignore"):
                errors.append(f"{consumer}: does not consume declared {dependency}")
    return errors


def build_report() -> tuple[dict, dict]:
    """Compute the low-level report without consuming any retained verdict."""
    matrix = yaml.safe_load(MATRIX.read_text())
    tracked, tracked_source = tracked_paths()
    fixture_set, missing_fixtures = build_fixture_set(tracked)
    represented, missing_addresses = address_promotion(tracked)
    source_gaps = local_import_gaps(tracked)
    provisioned_source_errors = validate_provisioned_sources(matrix, tracked)
    external_local_media_errors = validate_external_local_media_inputs(matrix, tracked)
    external_manifest_errors = validate_external_local_media_manifests(matrix, tracked)
    matrix_errors = validate_matrix(matrix)
    phase_status = {p: d["knowledge_status"] for p, d in matrix["phases"].items()}
    report = {
        "_comment": "Retroactive Phase-0..2 knowledge-closure audit. Regenerate: tools/knowledge_closure_audit.py --write. --strict fails until every phase is knowledge-closed.",
        "generated": date.today().isoformat(),
        "phase_status": phase_status,
        "tracked_source": "git index or git-archive filesystem (equivalent tracked snapshot)",
        "matrix_errors": matrix_errors,
        "inventory": inventory_files(tracked),
        "tracked_python_untracked_imports": source_gaps,
        "provisioned_source_input_errors": provisioned_source_errors,
        "external_local_media_input_errors": external_local_media_errors,
        "external_local_media_manifest_errors": external_manifest_errors,
        "known_dependency_checks": {
            "tools/glyph_spin_native.py": {
                "tracked": "tools/glyph_spin_native.py" in tracked,
                "consumers": matrix["known_closed_dependencies"]
                    ["tools/glyph_spin_native.py"]["consumers"],
                "closure_commit": matrix["known_closed_dependencies"]
                    ["tools/glyph_spin_native.py"]["closure_commit"],
            },
        },
        "fixture_summary": {"declared": len(fixture_set["entries"]),
                            "missing_central_pins": missing_fixtures},
        "address_promotion": {"represented": represented,
                              "missing_authoritative_machine_layer": missing_addresses},
        "strict_blockers": {
            "knowledge_phases_not_closed": sorted(p for p, s in phase_status.items() if s != "closed"),
            "matrix_errors": matrix_errors,
            "untracked_imports": source_gaps,
            "provisioned_source_input_errors": provisioned_source_errors,
            "external_local_media_input_errors": external_local_media_errors,
            "external_local_media_manifest_errors": external_manifest_errors,
            "missing_fixture_pins": missing_fixtures,
            "unpromoted_confirmed_addresses": missing_addresses,
        },
    }
    return report, fixture_set


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    report, fixture_set = build_report()
    if args.write:
        FIXTURE_SET.write_text(json.dumps(fixture_set, indent=1) + "\n")
        REPORT.write_text(json.dumps(report, indent=1) + "\n")
    blockers = report["strict_blockers"]
    print(f"[knowledge] phases={report['phase_status']}; "
          f"fixtures={report['fixture_summary']['declared']} "
          f"missing_pins={len(blockers['missing_fixture_pins'])} "
          f"untracked_imports={len(blockers['untracked_imports'])} "
          f"source_pin_errors={len(blockers['provisioned_source_input_errors'])} "
          f"local_media_errors={len(blockers['external_local_media_input_errors'])} "
          f"local_manifest_errors={len(blockers['external_local_media_manifest_errors'])} "
          f"unpromoted_addresses={len(blockers['unpromoted_confirmed_addresses'])} "
          f"matrix_errors={len(blockers['matrix_errors'])}")
    strict_fail = any(bool(v) for v in blockers.values())
    return 1 if args.strict and strict_fail else (1 if blockers["matrix_errors"] else 0)


if __name__ == "__main__":
    raise SystemExit(main())
