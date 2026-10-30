#!/usr/bin/env python3
"""Run the mandatory, pre-frozen Phase-4 caller-domain pilot.

Instruction decoding, caller-edge scanning, address-taken probing, and source
classification are performed by compiled C.  This driver owns only pinned
input selection, deterministic manifest construction, cross-implementation
comparison, receipt rendering, and ``--check`` identity.

The pilot is a hard gate.  It never launches the full corpus pass.  A GO would
authorize a later invocation/commit that implements Stages A-C; a NO-GO banks
the reviewed negative and stops at the sample-scoped receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_caller_domain_pilot.json"
INDEX = ROOT / "analysis/phase4_static_frontier_index.json"
CAMPAIGN = ROOT / "analysis/phase4_f01_local_base_recovery.json"
JR_TABLES = ROOT / "analysis/phase3_jr_tables.json"
GATE = ROOT / "analysis/phase3_gate_audit.json"
CAPSULES = ROOT / "analysis/phase4_trace_capsule_set.json"
F01_RESULT = ROOT / "analysis/phase4_f01_frontier_result.json"
WORK_ORDER = ROOT / "engineering-specs/phase4-caller-domain-work-order.md"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"
PRIMARY_C = ROOT / "tools/phase4_caller_domain_probe.c"
CROSSCHECK_C = ROOT / "tools/phase4_caller_domain_crosscheck.c"
DRIVER = Path(__file__).resolve()

BASELINE_COMMIT = "fc2a708754320a38877c59f47f6997a0a42f25ce"
FREEZE_COMMIT = "de8b10512c69"
HISTORICAL_INDEXDOM_COMMIT = "92e249a8807b"
HISTORICAL_CAMPAIGN_PATH = "analysis/phase4_f01_local_base_recovery.json"
SCHEMA = "abl-phase4-caller-domain-pilot/1"
DEPTH_CAP = 3
WIDENING_CAP = 32

STACK_IDS = (
    "LEVEL02_LEVEL1:0x800B3F14:sp",
    "LEVEL02_LEVEL1:0x800B43AC:sp",
    "LEVEL05_LEVEL:0x800B4040:sp",
    "LEVEL05_LEVEL:0x800B4048:sp",
    "LEVEL08_LEVEL1:0x800B416C:sp",
)
RETURN_IDS = (
    "LEVEL03_LEVEL1:0x800B41AC:v1",
    "LEVEL05_LEVEL1:0x800B494C:s0",
    "LEVEL07_LEVEL:0x800B4774:a3",
    "LEVEL08_LEVEL:0x800B4284:s0",
    "LEVEL09_LEVEL:0x800B4640:s0",
)
INDEX_IDS = (
    "LEVEL02_LEVEL:0x800B4788:a0",
    "LEVEL04_LEVEL1:0x800B4AA8:v1",
    "MEMORY:0x800B7EA4:at",
    "MEMORY:0x800B7F04:at",
    "MEMORY:0x800B7F64:at",
    "SCUS_942_88:0x8005C5B4:s2",
    "SCUS_942_88:0x8005C5C0:s2",
    "SCUS_942_88:0x8005C5C8:s2",
    "SCUS_942_88:0x8005C5D4:s2",
    "SCUS_942_88:0x8005C5E8:s2",
)
PILOT_IDS = STACK_IDS + RETURN_IDS + INDEX_IDS

REGNUM = {
    "zero": 0, "at": 1, "v0": 2, "v1": 3,
    "a0": 4, "a1": 5, "a2": 6, "a3": 7,
    "t0": 8, "t1": 9, "t2": 10, "t3": 11,
    "t4": 12, "t5": 13, "t6": 14, "t7": 15,
    "s0": 16, "s1": 17, "s2": 18, "s3": 19,
    "s4": 20, "s5": 21, "s6": 22, "s7": 23,
    "t8": 24, "t9": 25, "k0": 26, "k1": 27,
    "gp": 28, "sp": 29, "fp": 30, "ra": 31,
}

LOCAL_BREAKERS = {
    "LEVEL02_LEVEL:0x800B4788:a0": 0x800B4734,
    "LEVEL04_LEVEL1:0x800B4AA8:v1": 0x800B4A8C,
    "MEMORY:0x800B7EA4:at": 0x800B7E68,
    "MEMORY:0x800B7F04:at": 0x800B7EC8,
    "MEMORY:0x800B7F64:at": 0x800B7F28,
}


class PilotError(RuntimeError):
    """Fail-closed pilot construction or verification error."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text, 16 if text.lower().startswith("0x") else 10)


def _git_show(commit: str, path: Path | str) -> bytes:
    rel = str(path.relative_to(ROOT) if isinstance(path, Path) else path)
    proc = subprocess.run(
        ["git", "show", f"{commit}:{rel}"], cwd=ROOT,
        capture_output=True, check=False,
    )
    if proc.returncode:
        raise PilotError(
            f"cannot read pinned Git object {commit}:{rel}: "
            + proc.stderr.decode(errors="replace").strip())
    return proc.stdout


def _load_git_json(commit: str, path: Path) -> tuple[dict, bytes]:
    """Load a derived input from the named committed snapshot, never ambient WIP."""
    raw = _git_show(commit, path)
    return json.loads(raw), raw


def _verify_freeze_note() -> tuple[bytes, list[str]]:
    raw = _git_show(FREEZE_COMMIT, EXPERIMENT)
    text = raw.decode("utf-8")
    marker = "caller-domain pilot universe frozen (PRE-OUTCOME record)"
    if marker not in text:
        raise PilotError("freeze commit lacks the pre-outcome marker")
    section = text.split(marker, 1)[1]
    found = re.findall(
        r"\| (?:stack-entry|return-domain|argument-carrier index) \| `([^`]+)` \|",
        section,
    )
    if found != list(PILOT_IDS):
        raise PilotError(f"frozen note site order differs: {found!r}")
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_COMMIT, FREEZE_COMMIT],
        cwd=ROOT, check=False,
    )
    if proc.returncode:
        raise PilotError("issued baseline is not an ancestor of the freeze commit")
    return raw, found


def _width(row: dict) -> int:
    return {"sb": 1, "sh": 2, "sw": 4, "swl": 4, "swr": 4}.get(
        str(row.get("mnemonic") or "").lower(), 4)


def _func_record(index: dict, image: str, entry: int) -> dict:
    rows = [
        row for row in index["records"]
        if row.get("entry") and row["image_id"] == image
        and _int(row["entry"]) == entry
    ]
    if len(rows) != 1:
        raise PilotError(f"expected one function record for {image}:0x{entry:08x}")
    return rows[0]


def _site_manifest_fields(row: dict, index: dict) -> tuple[str, str, int, int, int]:
    """Return mode, root image/entry/end, and exact C breaker PC."""
    site_id = row["id"]
    if site_id in STACK_IDS:
        return "CALLER", row["image"], _int(row["extent"][0]), _int(row["extent"][1]), 0
    if site_id.startswith("SCUS_942_88:0x8005C5"):
        return "CALLER", "SCUS_942_88", _int(row["extent"][0]), _int(row["extent"][1]), 0
    if site_id in LOCAL_BREAKERS:
        return ("LOCAL", row["image"], _int(row["extent"][0]),
                _int(row["extent"][1]), LOCAL_BREAKERS[site_id])
    if site_id in RETURN_IDS:
        # The first and third rows are stores in the JAL delay slot.  The other
        # three call an alternate entry at A0E0 which falls through into the
        # A0F0..A308 body; the exact v0 <- s0 return copy is the breaker.
        if site_id in (RETURN_IDS[0], RETURN_IDS[2]):
            rec = _func_record(index, "SCUS_942_88", 0x8004C10C)
            return "RETURN", "SCUS_942_88", 0x8004C10C, _int(rec["end"]), _int(row["pc"]) - 4
        return "RETURN", "SCUS_942_88", 0x8005A0E0, 0x8005A308, 0x8005A2F0
    raise PilotError(f"site {site_id} has no manifest mode")


def _manifest(index: dict, campaign: dict, jr: dict) -> bytes:
    lines = ["VERSION 1"]
    images = index.get("images") or []
    image_ids = {image["image_id"] for image in images}
    if len(images) != 21 or len(image_ids) != len(images):
        raise PilotError("static index image universe is not the pinned 21 unique images")
    for image in images:
        path = ROOT / image["path"]
        raw = path.read_bytes()
        if len(raw) != int(image["size"]) or _sha(raw) != image["sha256"]:
            raise PilotError(f"image identity failed: {image['image_id']}")
        lines.append(
            f"IMAGE {image['image_id']} {image['path']} "
            f"{_int(image['file_va_base']):08x} {len(raw)}")

    func_count = 0
    for row in index["records"]:
        if not row.get("entry") or not row.get("end") or row["image_id"] not in image_ids:
            continue
        name = re.sub(r"\s+", "_", str(row.get("name") or f"anon_{row['entry']}"))
        lines.append(
            f"FUNC {row['image_id']} {_int(row['entry']):08x} "
            f"{_int(row['end']):08x} {name}")
        func_count += 1
    if func_count != 1191:
        raise PilotError(f"function universe drifted: {func_count} != 1191")

    proved: set[tuple[int, int]] = set()
    for key in ("indirect_jump_targets", "indirect_jump_targets_from_gate"):
        source = index.get(key) or {}
        for pc, targets in (source.get("site_targets") or {}).items():
            for target in targets:
                proved.add((_int(pc), _int(target)))
    for pc, target in sorted(proved):
        lines.append(f"PROVED SCUS_942_88 {pc:08x} {target:08x}")

    tables: set[tuple[int, int]] = set()
    for item in (jr.get("decoded") or {}).values():
        lo = _int(item["table"])
        hi = lo + int(item["entries"]) * 4
        tables.add((lo, hi))
    for lo, hi in sorted(tables):
        lines.append(f"TABLE SCUS_942_88 {lo:08x} {hi:08x}")

    by_id = {row["id"]: row for row in campaign["sites"]}
    if len(by_id) != len(campaign["sites"]):
        raise PilotError("campaign site IDs are not unique")
    expected = {
        **{site_id: "blocked_stack_entry_value_caller_dependent" for site_id in STACK_IDS},
        **{site_id: "blocked_return_domain_unrecovered" for site_id in RETURN_IDS},
        **{site_id: "blocked_index_interval_unproved_instruction" for site_id in INDEX_IDS},
    }
    for site_id in PILOT_IDS:
        row = by_id.get(site_id)
        if row is None or row.get("outcome") != expected[site_id]:
            raise PilotError(f"pilot site/wall drift: {site_id}")
        mode, root_image, root_lo, root_hi, breaker = _site_manifest_fields(row, index)
        reg = str(row["base_register"])
        stratum = ("stack_entry" if site_id in STACK_IDS else
                   "return_domain" if site_id in RETURN_IDS else "argument_index")
        lines.append(
            f"SITE {mode} {stratum} {site_id} {root_image} "
            f"{root_lo:08x} {root_hi:08x} {row['image']} {_int(row['pc']):08x} "
            f"{int(row['offset'])} {_width(row)} {REGNUM[reg]} {breaker:08x}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _compile(source: Path, output: Path, *, gnu: bool) -> bytes:
    cmd = [
        "cc", "-std=gnu11" if gnu else "-std=c11", "-O2",
        "-Wall", "-Wextra", "-Werror", "-o", str(output), str(source),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise PilotError(f"C compile failed ({source.name}): {proc.stderr.strip()}")
    return output.read_bytes()


def _run_json(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode:
        raise PilotError(f"command failed ({' '.join(cmd)}): {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PilotError(f"non-JSON C output: {exc}: {proc.stdout[:500]!r}") from exc


def _capsule_gate(capsules: dict, decided_ids: list[str]) -> dict:
    rows = capsules.get("capsules") or []
    if (capsules.get("capsule_count") != 50 or len(rows) != 50
            or capsules.get("complete") is not True or capsules.get("errors") != []
            or any(row.get("control_match") is not True for row in rows)):
        raise PilotError("the pinned 50-capsule universe is incomplete or control-divergent")
    if decided_ids:
        # Count-mode capsules retain full registers only at frame boundaries,
        # not at every basic-block execution.  A site-time domain comparison
        # must fail closed rather than turn zero samples into a clean control.
        return {
            "status": "UNAVAILABLE_SITE_TIME_REGISTER_DOMAIN",
            "decided_site_ids": decided_ids,
            "capsule_universe": 50,
            "site_time_observations": 0,
            "all_observed_values_within_domains": None,
            "soundness_violation": False,
            "clean_for_go": False,
            "reason": ("count-mode trace capsules contain frame-boundary registers and "
                       "per-frame block counts, not registers at each named site; zero "
                       "site-time samples is not relabelled as a clean cross-check"),
        }
    return {
        "status": "NOT_APPLICABLE_NO_DECIDED_DOMAINS",
        "decided_site_ids": [],
        "capsule_universe": 50,
        "site_time_observations": 0,
        "all_observed_values_within_domains": True,
        "soundness_violation": False,
        "clean_for_go": False,
        "reason": "no proved/decided pilot domain exists to compare",
    }


def build() -> dict:
    freeze_raw, frozen_ids = _verify_freeze_note()
    # The pre-outcome freeze is also the immutable derived-input snapshot. This
    # prevents unrelated operator WIP under analysis/ from changing a receipt
    # that must reproduce in a detached checkout. Current C/Python source is
    # intentionally read from the worktree and identity-pinned below.
    campaign, campaign_raw = _load_git_json(FREEZE_COMMIT, CAMPAIGN)
    index, index_raw = _load_git_json(FREEZE_COMMIT, INDEX)
    jr, jr_raw = _load_git_json(FREEZE_COMMIT, JR_TABLES)
    gate, gate_raw = _load_git_json(FREEZE_COMMIT, GATE)
    capsules, capsules_raw = _load_git_json(FREEZE_COMMIT, CAPSULES)
    f01, f01_raw = _load_git_json(FREEZE_COMMIT, F01_RESULT)
    work_raw = _git_show(FREEZE_COMMIT, WORK_ORDER)
    historical_raw = _git_show(HISTORICAL_INDEXDOM_COMMIT, HISTORICAL_CAMPAIGN_PATH)
    manifest = _manifest(index, campaign, jr)

    with tempfile.TemporaryDirectory(prefix="phase4-caller-domain-") as tmp_text:
        tmp = Path(tmp_text)
        manifest_path = tmp / "pilot.manifest"
        manifest_path.write_bytes(manifest)
        primary_bin = tmp / "phase4_caller_domain_probe"
        cross_bin = tmp / "caller_domain_crosscheck"
        primary_binary = _compile(PRIMARY_C, primary_bin, gnu=True)
        cross_binary = _compile(CROSSCHECK_C, cross_bin, gnu=False)
        primary_selftest = _run_json([str(primary_bin), "--caller-domain-self-test"])
        cross_selftest = _run_json([str(cross_bin), "--self-test"])
        primary = _run_json([str(primary_bin), "--caller-domain-pilot", str(manifest_path)])
        cross = _run_json([str(cross_bin), str(manifest_path)])

    if primary_selftest.get("verdict") is not True or cross_selftest.get("verdict") is not True:
        raise PilotError("a C self-test failed")
    primary_sites = primary.get("sites") or []
    cross_sites = cross.get("sites") or []
    if [row.get("id") for row in primary_sites] != list(PILOT_IDS):
        raise PilotError("primary C site order differs from frozen pilot")
    if [row.get("id") for row in cross_sites] != list(PILOT_IDS):
        raise PilotError("independent C site order differs from frozen pilot")
    disagreements = []
    merged = []
    for a, b in zip(primary_sites, cross_sites):
        agree = (a.get("decided"), a.get("wall")) == (b.get("decided"), b.get("wall"))
        if not agree:
            disagreements.append({
                "id": a.get("id"),
                "primary": {"decided": a.get("decided"), "wall": a.get("wall")},
                "independent": {"decided": b.get("decided"), "wall": b.get("wall")},
            })
        merged.append({
            **a,
            "independent_crosscheck": {
                "agrees": agree,
                "decided": b.get("decided"),
                "wall": b.get("wall"),
                **({"witness": b["independent_witness"]} if b.get("independent_witness") else {}),
                **({"breaker": b["independent_breaker"]} if b.get("independent_breaker") else {}),
            },
        })
    if disagreements:
        raise PilotError(f"independent implementation disagreement: {disagreements!r}")

    decided_ids = sorted(row["id"] for row in merged if row.get("decided"))
    open_ids = sorted(row["id"] for row in merged
                      if row.get("wall") == "open_caller_set_poison")
    wall_sets: dict[str, list[str]] = {}
    for row in merged:
        if not row.get("decided"):
            wall_sets.setdefault(str(row["wall"]), []).append(row["id"])
    wall_sets = {key: sorted(value) for key, value in sorted(wall_sets.items())}
    capsule_gate = _capsule_gate(capsules, decided_ids)

    no_go_reasons = []
    if len(decided_ids) < 3:
        no_go_reasons.append("decided_site_count_below_3")
    if len(open_ids) > 10:
        no_go_reasons.append("open_caller_set_poison_above_10")
    if capsule_gate["soundness_violation"]:
        decision = "HALT_SOUNDNESS_BUG"
    elif not no_go_reasons and len(decided_ids) >= 3 and capsule_gate["clean_for_go"]:
        decision = "GO"
    else:
        decision = "NO-GO"
        if not no_go_reasons:
            no_go_reasons.append("capsule_crosscheck_not_clean_for_go")
    if decision != "NO-GO":
        raise PilotError(f"this sample result unexpectedly requires continuation: {decision}")

    current_tally = campaign.get("tally") or {}
    return {
        "_comment": ("Mandatory caller-domain pilot. The exact site list was committed "
                     "before outcomes in de8b10512c69. A NO-GO is a reviewed negative "
                     "and forbids the full Stage-A/B/C pass in this increment."),
        "schema": SCHEMA,
        "inputs": {
            "work_order": str(WORK_ORDER.relative_to(ROOT)),
            "work_order_sha256": _sha(work_raw),
            "issued_baseline_commit": BASELINE_COMMIT,
            "pre_outcome_freeze_commit": FREEZE_COMMIT,
            "derived_input_snapshot_commit": FREEZE_COMMIT,
            "pre_outcome_freeze_note_sha256": _sha(freeze_raw),
            "campaign": str(CAMPAIGN.relative_to(ROOT)),
            "campaign_sha256": _sha(campaign_raw),
            "static_index": str(INDEX.relative_to(ROOT)),
            "static_index_sha256": _sha(index_raw),
            "jr_tables": str(JR_TABLES.relative_to(ROOT)),
            "jr_tables_sha256": _sha(jr_raw),
            "gate": str(GATE.relative_to(ROOT)),
            "gate_sha256": _sha(gate_raw),
            "historical_index_source_object":
                f"{HISTORICAL_INDEXDOM_COMMIT}:{HISTORICAL_CAMPAIGN_PATH}",
            "historical_index_source_sha256": _sha(historical_raw),
            "capsule_set": str(CAPSULES.relative_to(ROOT)),
            "capsule_set_sha256": _sha(capsules_raw),
            "f01_result": str(F01_RESULT.relative_to(ROOT)),
            "f01_result_sha256": _sha(f01_raw),
            "c_manifest_sha256": _sha(manifest),
            "driver": str(DRIVER.relative_to(ROOT)),
            "driver_sha256": _sha(DRIVER.read_bytes()),
            "primary_c": str(PRIMARY_C.relative_to(ROOT)),
            "primary_c_sha256": _sha(PRIMARY_C.read_bytes()),
            "primary_binary_sha256": _sha(primary_binary),
            "independent_c": str(CROSSCHECK_C.relative_to(ROOT)),
            "independent_c_sha256": _sha(CROSSCHECK_C.read_bytes()),
            "independent_binary_sha256": _sha(cross_binary),
        },
        "pilot_universe": {
            "definition": ("the exact 20 IDs committed in the experiment log before "
                           "any caller-closure/domain outcome"),
            "site_ids": frozen_ids,
            "site_count": len(frozen_ids),
            "strata": {
                "blocked_stack_entry_value_caller_dependent": list(STACK_IDS),
                "blocked_return_domain_unrecovered": list(RETURN_IDS),
                "argument_carrier_blocked_index_interval_unproved_instruction": list(INDEX_IDS),
            },
            "sample_is_not_corpus_universe": True,
        },
        "configuration": {
            "depth_cap": DEPTH_CAP,
            "widening_cap": WIDENING_CAP,
            "widening_cap_hit": False,
            "full_corpus_pass_performed": False,
            "runtime_replay_performed": False,
        },
        "stage_a_sample_caller_closure": {
            "scope": "pilot roots and their coexisting-image incoming-edge universe only",
            "primary_universe": primary["universe"],
            "closure_roots": primary["closure_roots"],
            "closed_root_keys": sorted(row["key"] for row in primary["closure_roots"]
                                       if row["classification"] == "CLOSED"),
            "open_root_keys": sorted(row["key"] for row in primary["closure_roots"]
                                     if row["classification"] == "OPEN"),
            "full_census_artifact_emitted": False,
            "why_no_full_census": "pilot NO-GO forbids the full Stage-A pass",
        },
        "stage_b_sample_domains": {
            "fixpoint_rounds": 0,
            "proved_site_ids": decided_ids,
            "proved_site_count": len(decided_ids),
            "absent_site_ids": sorted(row["id"] for row in merged if not row.get("decided")),
            "absent_site_count": sum(not row.get("decided") for row in merged),
            "wall_site_sets": wall_sets,
            "note": ("OPEN roots poison entry-dependent domains before propagation; "
                     "local-clobber and delay-slot/fallthrough-return breakers remain "
                     "separate and are not inflated into the OPEN count"),
        },
        "independent_crosscheck": {
            "implementation": str(CROSSCHECK_C.relative_to(ROOT)),
            "sample_site_ids": [row["id"] for row in cross_sites],
            "disagreements": disagreements,
            "all_20_agree": not disagreements and len(cross_sites) == 20,
            "primary_selftest": primary_selftest,
            "independent_selftest": cross_selftest,
        },
        "sites": merged,
        "capsule_crosscheck": capsule_gate,
        "decision": {
            "verdict": decision,
            "go_threshold_decided_sites": 3,
            "decided_site_count": len(decided_ids),
            "decided_site_ids": decided_ids,
            "open_poison_threshold": 10,
            "open_poison_comparison": "strictly_greater_than_10",
            "open_poison_site_count": len(open_ids),
            "open_poison_site_ids": open_ids,
            "reasons": no_go_reasons,
            "full_pass_authorized": False,
            "next_increment_if_banked": "prove_indirect_table_and_address-taken universes",
        },
        "stage_c_not_run": {
            "reason": "mandatory pilot returned NO-GO",
            "fixture_store_movement": {"gained_ids": [], "lost_ids": []},
            "ledger_movement": {"gained_ids": [], "lost_ids": []},
            "campaign_row_movement": {"gained_ids": [], "lost_ids": []},
            "old_pins_replaced": [],
            "current_campaign_tally_unchanged": current_tally,
        },
        "protected_state": {
            "f01_status": "partial",
            "item_2": "not_met",
            "dimension_promoted": f01["verdicts"]["dimension_promoted"],
            "item2_ready_for_review": f01["verdicts"]["item2_ready_for_review"],
            "review_blockers": f01["verdicts"]["review_blockers"],
            "mechanics_baseline_modified": False,
            "movie_or_fixture_modified": False,
        },
        "authority": {
            "changes_campaign_registry": False,
            "promotes_dimension": False,
            "closes_item_2": False,
            "banks_f01_status": False,
            "fresh_detached_verifier_required_for_any_status_change": True,
        },
    }


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    out = args.output if args.output.is_absolute() else ROOT / args.output
    rendered = render(build())
    if args.check:
        if not out.is_file() or out.read_bytes() != rendered:
            print(f"stale: {out.relative_to(ROOT)}", flush=True)
            return 1
        print(f"ok: {out.relative_to(ROOT)}")
        return 0
    out.write_bytes(rendered)
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
