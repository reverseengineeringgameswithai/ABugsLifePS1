#!/usr/bin/env python3
"""Build the F01 trig/dispatch static hard-truth receipt.

The compiled C probe owns instruction decoding and content derivation.  This
driver owns repository identities and exact-set reconciliation against the two
already-retained jr sources.  A count match is never accepted as identity.

Usage:
  tools/phase4_f01_static_hard_truth.py \
      --output analysis/phase4_f01_static_hard_truth.json [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/phase4_f01_static_hard_truth.c"
IMAGE = ROOT / "REBUILD/files/SCUS_942.88"
BASELINES = ROOT / "tools/build_baselines.json"
PHASE3_JR = ROOT / "analysis/phase3_jr_tables.json"
GATE = ROOT / "analysis/phase4_static_asm_prerequisites.json"
SCHEMA = "abl-phase4-f01-static-hard-truth/1"
IMAGE_ID = "SCUS_942_88"


class HardTruthError(RuntimeError):
    """The receipt cannot be built without weakening a required invariant."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256(path.read_bytes())


def as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text, 16 if text.lower().startswith("0x") else 10)


def hx(value: int) -> str:
    return f"0x{value:08X}"


def entry_pairs(entries: list[dict[str, Any]]) -> set[tuple[int, int]]:
    return {(int(row["index"]), as_int(row["target"])) for row in entries}


def render_pairs(values: set[tuple[int, int]]) -> list[dict[str, Any]]:
    return [{"index": index, "target": hx(target)}
            for index, target in sorted(values)]


def phase3_site(document: dict[str, Any], pc: str) -> dict[str, Any]:
    row = (document.get("decoded") or {}).get(pc)
    if row is None:
        raise HardTruthError(f"phase3 jr receipt has no {pc}")
    return row


def gate_site(document: dict[str, Any], pc: str) -> dict[str, Any]:
    matches = [row for row in document["indirect_control"]["jr_sites"]
               if str(row.get("pc")).upper() == pc.upper()]
    if len(matches) != 1:
        raise HardTruthError(f"gate has {len(matches)} jr rows for {pc}")
    return matches[0]


def reconcile_dispatch(c_row: dict[str, Any], phase3: dict[str, Any],
                       gate: dict[str, Any]) -> dict[str, Any]:
    pc = str(c_row["pc"])
    p3 = phase3_site(phase3, pc)
    gs = gate_site(gate, pc)
    c_pairs = entry_pairs(c_row["entries"])
    p3_pairs = entry_pairs(p3["targets"])
    gate_targets = (gs.get("resolution") or {}).get("targets") or []
    gate_pairs = {(index, as_int(target))
                  for index, target in enumerate(gate_targets)}
    if as_int(p3["table"]) != as_int(c_row["table"]):
        raise HardTruthError(f"{pc}: phase3/C table bases differ")
    if as_int((gs.get("resolution") or {}).get("table")) != as_int(c_row["table"]):
        raise HardTruthError(f"{pc}: gate/C table bases differ")
    if not (gs.get("resolution") or {}).get("target_set_complete"):
        raise HardTruthError(f"{pc}: gate no longer calls the set complete")
    c_only_phase3 = c_pairs - p3_pairs
    phase3_only_c = p3_pairs - c_pairs
    c_only_gate = c_pairs - gate_pairs
    gate_only_c = gate_pairs - c_pairs
    if c_only_phase3 or phase3_only_c or c_only_gate or gate_only_c:
        raise HardTruthError(
            f"{pc}: dispatch entry identities disagree: "
            f"C-only-phase3={sorted(c_only_phase3)}, "
            f"phase3-only-C={sorted(phase3_only_c)}, "
            f"C-only-gate={sorted(c_only_gate)}, gate-only-C={sorted(gate_only_c)}")
    distinct = sorted({target for _, target in c_pairs})
    identity = [{"index": index, "target": hx(target)}
                for index, target in sorted(c_pairs)]
    return {
        "pc": pc,
        "table": c_row["table"],
        "entry_count": len(c_pairs),
        "distinct_target_count": len(distinct),
        "distinct_targets": [hx(target) for target in distinct],
        "entry_identity_sha256": sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()),
        "comparison": "exact (index,target) set in both directions",
        "c_only_phase3": render_pairs(c_only_phase3),
        "phase3_only_c": render_pairs(phase3_only_c),
        "c_only_gate": render_pairs(c_only_gate),
        "gate_only_c": render_pairs(gate_only_c),
        "phase3_artifact": str(PHASE3_JR.relative_to(ROOT)),
        "phase3_artifact_sha256": sha256_path(PHASE3_JR),
        "gate_artifact": str(GATE.relative_to(ROOT)),
        "gate_artifact_sha256": sha256_path(GATE),
        "verified": True,
    }


def build() -> dict[str, Any]:
    image_raw = IMAGE.read_bytes()
    baselines_raw = BASELINES.read_bytes()
    baselines = json.loads(baselines_raw)
    expected = baselines["staged_inputs"]["SCUS_942.88"]
    actual_sha = sha256(image_raw)
    if actual_sha != expected["sha256"] or len(image_raw) != int(expected["size"]):
        raise HardTruthError("resident image is not the hash-pinned pristine input")

    with tempfile.TemporaryDirectory(prefix="abl_f01_static_") as directory:
        binary = Path(directory) / "phase4_f01_static_hard_truth"
        command = ["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                   str(SOURCE), "-lm", "-o", str(binary)]
        subprocess.run(command, cwd=ROOT, check=True)
        binary_sha = sha256_path(binary)
        proc = subprocess.run([str(binary), str(IMAGE)], cwd=ROOT,
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise HardTruthError(
                f"C probe failed ({proc.returncode}): {proc.stderr.strip()}")
        try:
            c_receipt = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise HardTruthError(f"C probe emitted invalid JSON: {exc}") from exc

    verdicts = c_receipt.get("verdicts") or {}
    if not verdicts.get("trig_semantic_disposition_supported"):
        raise HardTruthError("C probe did not support the trig semantic disposition")
    if verdicts.get("requested_dispatch_sets_proved"):
        raise HardTruthError("claimed dispatch PCs unexpectedly became proved sets")
    if int(verdicts.get("new_indirect_target_sets_to_register", -1)) != 0:
        raise HardTruthError("C receipt requested an indirect-target import")

    phase3_raw = PHASE3_JR.read_bytes()
    gate_raw = GATE.read_bytes()
    phase3 = json.loads(phase3_raw)
    gate = json.loads(gate_raw)
    actual_rows = c_receipt["actual_dispatch_controls"][:2]
    reconciliations = [reconcile_dispatch(row, phase3, gate)
                       for row in actual_rows]

    phase3_pcs = {str(pc).upper() for pc in (phase3.get("decoded") or {})}
    gate_jr_pcs = {str(row.get("pc")).upper()
                   for row in gate["indirect_control"]["jr_sites"]}
    gate_jalr_pcs = {str(row.get("pc")).upper()
                     for row in gate["indirect_control"]["jalr_sites"]}
    claimed_registration = []
    for row in c_receipt["requested_dispatch_sites"]:
        pc = str(row["pc"])
        claimed_registration.append({
            "pc": pc,
            "decoded_kind": row["decoded_kind"],
            "present_as_phase3_jr": pc.upper() in phase3_pcs,
            "present_as_gate_jr": pc.upper() in gate_jr_pcs,
            "present_as_gate_jalr": pc.upper() in gate_jalr_pcs,
            "new_set_registered": False,
        })
    if any(row["present_as_phase3_jr"] or row["present_as_gate_jr"] or
           row["present_as_gate_jalr"] for row in claimed_registration):
        raise HardTruthError("a direct jal is registered as indirect control")

    return {
        "schema": SCHEMA,
        "generated": "2026-08-06",
        "question": ("Do instruction-derived reader ranges plus an independent "
                     "full content derivation semantically dispose the two trig "
                     "gaps, and do the two live-attributed PCs really carry "
                     "bounded jalr dispatches?"),
        "inputs": {
            "pristine_image": str(IMAGE.relative_to(ROOT)),
            "pristine_image_sha256": actual_sha,
            "pristine_image_size": len(image_raw),
            "build_baselines": str(BASELINES.relative_to(ROOT)),
            "build_baselines_sha256": sha256(baselines_raw),
            "c_source": str(SOURCE.relative_to(ROOT)),
            "c_source_sha256": sha256_path(SOURCE),
            "c_binary_sha256": binary_sha,
            "compile_argv": ["cc", "-O2", "-std=c11", "-Wall", "-Wextra",
                             "-Werror", "tools/phase4_f01_static_hard_truth.c",
                             "-lm", "-o", "<temporary-binary>"],
            "phase3_jr_tables": str(PHASE3_JR.relative_to(ROOT)),
            "phase3_jr_tables_sha256": sha256(phase3_raw),
            "static_asm_gate": str(GATE.relative_to(ROOT)),
            "static_asm_gate_sha256": sha256(gate_raw),
        },
        "evidence_boundary": {
            "static_instruction_and_content_facts": "proof-grade within the pinned image",
            "live_replay_role": ("lead and attribution falsifier only; no runtime "
                                 "observation is promoted to a complete target set"),
            "gap_extent_rule": ("the full tables are compared, but downstream census "
                                "ownership may cover only the two exact pre-existing "
                                "gap intervals; no extent may be widened"),
        },
        "c_probe": c_receipt,
        "registered_actual_jr_reconciliation": reconciliations,
        "claimed_pc_registration_check": claimed_registration,
        "dispatch_import_delta": {
            "new_sites": [],
            "removed_sites": [],
            "new_site_count": 0,
            "reason": ("both requested PCs decode as direct jal; the nearby real jr "
                       "sets were already present and match the C enumeration exactly"),
        },
        "verdicts": {
            "trig_semantic_disposition_supported": True,
            "requested_dispatch_sites_proved": False,
            "requested_dispatch_sites_fail_closed": True,
            "actual_jr_sets_exactly_reconciled": all(r["verified"] for r in reconciliations),
            "new_indirect_target_sets_to_register": 0,
            "gate_receipt_modified": False,
        },
    }


def render(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = render(build())
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != payload:
            print(f"[f01-static-hard-truth] STALE: {args.output}")
            return 1
        print(f"[f01-static-hard-truth] {args.output}: fresh")
        return 0
    args.output.write_bytes(payload)
    doc = json.loads(payload)
    tables = doc["c_probe"]["trigonometric_tables"]
    print(f"[f01-static-hard-truth] wrote {args.output}")
    print("  trig gap bytes content+reader disposed:",
          sum(row["gap"]["byte_count"] for row in tables))
    print("  requested dispatch sets: 0 proved, 2 failed closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
