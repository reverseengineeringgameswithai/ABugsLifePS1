#!/usr/bin/env python3
"""Derive the Phase-2 control-coverage map from the registry AND the evidence.

Two review rounds shaped this generator:
 1. The original hand-authored map omitted five core actions and its test
    allowed an empty gap list — a self-grading artifact.
 2. The first derived version enumerated rows from the registry but still
    DECLARED every verdict in a hand-written COVERED dict with a hardcoded
    empty GAPS list, so a wrong declaration (A15's invalid f900 window, A16's
    two-anchor comparison) still counted as covered.

This version INSPECTS the evidence: each row maps to concrete checks —
(artifact file, JSON path, predicate, expected) — that are evaluated at
generation time against the committed artifact content. A row is COVERED only
if every check passes; anything else (missing artifact, missing path, failed
check, unmapped row) becomes a GAP automatically. The gap list is COMPUTED,
never authored.

Usage: python3 tools/phase2_coverage_map.py
Output: analysis/phase2_negative_coverage_map.json  (exit 1 if any gap remains)
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

BEHAVIOR = "analysis/phase2_action_behavior.json"
ORACLE = "analysis/phase2_action_oracle.json"
NEG = "analysis/phase2_negative_controls.json"
SLIDE = "analysis/phase2_buttslide_oracle.json"
CARRY = "analysis/phase2_carry_handstand_oracle.json"
SEEDS = "analysis/phase2_seed_action_controls.json"
FINAL = "analysis/phase2_final_action_pairs.json"
SPIN = "analysis/phase2_spin_disproof.json"
LIFE = "analysis/phase2_lifecycle_oracle.json"
POOL = "analysis/phase2_pool_arc_oracle.json"

# row -> (observable, [(artifact, dotted.path, op, expected), ...])
# ops: "eq" ==, "min" >=, "max" <=, "contains"/"not_contains",
#      "min_len" (len >= expected), "nonempty" (truthy container)
CHECKS: dict[str, tuple[str, list]] = {
    "A01_move_run": ("position/state under input vs idle", [
        (ORACLE, "synthetic_probes.slow_walk.run_60f", "nonempty", None),
        (NEG, "controls.no_input_idle.s80_values", "contains", 0),
        (NEG, "controls.no_input_idle.grounded_always", "eq", True),
    ]),
    "A02_slow_walk": ("displacement ratio walk/run (0.605x)", [
        (ORACLE, "synthetic_probes.slow_walk.displacement_ratio_x", "min", 0.4),
        (ORACLE, "synthetic_probes.slow_walk.displacement_ratio_x", "max", 0.8),
    ]),
    "A03_jump": ("state word 0x800A6580 (air state 1)", [
        (NEG, "controls.single_jump_no_slide_states.s80_values_seen", "contains", 1),
        (NEG, "controls.single_jump_no_slide_states.s80_values_seen", "not_contains", 4),
    ]),
    "A04_kick": ("kick timer 0x800A657A := -16", [
        (BEHAVIOR, "controls.kick.l2_kick_fires", "eq", True),
        (BEHAVIOR, "controls.kick.r2_kick_fires", "eq", True),
        (BEHAVIOR, "controls.kick.square_alone_no_kick", "eq", True),
        (BEHAVIOR, "controls.kick.no_input_no_kick", "eq", True),
    ]),
    "A05_abdomen_bounce": ("double-tap slam state 4 (double-tap exclusive)", [
        (SLIDE, "signature.state80_sequence", "contains", 4),
        (SLIDE, "deterministic_across_replays", "eq", True),
    ]),
    "A06_downhill_slide": ("slide states 0->1->4->5; single jump never 4", [
        (SLIDE, "signature.ground_slide_state80", "eq", 5),
        (SLIDE, "deterministic_across_replays", "eq", True),
        (NEG, "controls.single_jump_no_slide_states.s80_values_seen", "not_contains", 4),
    ]),
    # A07 intentionally has no covering checks. The reproducible static scan is
    # bounded and cannot prove the secondary-source mechanic absent; keeping
    # this row a computed GAP prevents the old absolute disproof from silently
    # satisfying the action-control gate.
    "A07_spin": ("documented external lead; bounded static negative only", []),
    "A08_berry_throw": ("projectile arc + in-flight counter 0x800A6596", [
        (POOL, "arc_sentinel.deterministic_across_reloads", "eq", True),
        (NEG, "controls.no_input_idle.inflight_always_zero", "eq", True),
    ]),
    "A09_seed_pickup_drop": ("seed record vs player XYZ (attachment law)", [
        (CARRY, "laws.carry_attached_at_f660", "eq", True),
        (NEG, "controls.walk_no_square_no_carry.attachment_samples", "eq", 0),
        (NEG, "controls.walk_no_square_no_carry.player_displacement", "min", 1),
    ]),
    "A10_handstand": ("grounded 0x800A6582 + position freeze", [
        (CARRY, "laws.handstand_frozen", "eq", True),
        (SEEDS, "controls.A10_handstand_negative.not_mounted", "eq", True),
        (SEEDS, "controls.A10_handstand_negative.beside_seed_no_square.after.grounded", "eq", 1),
    ]),
    "A11_seed_as_weapon": ("carry break -> ballistic hit -> enemy+0x6C := -20 "
                           "-> kill; no press -> nothing", [
        (FINAL, "controls.A11_seed_as_weapon.causal.positive.carry_broken", "eq", True),
        (FINAL, "controls.A11_seed_as_weapon.causal.positive."
                "knockback_write", "eq", -20),
        (FINAL, "controls.A11_seed_as_weapon.causal.positive."
                "seed_lands_on_hit_frame", "eq", True),
        (FINAL, "controls.A11_seed_as_weapon.causal.positive."
                "measured_decay_per_frame", "min", 0.3),
        (FINAL, "controls.A11_seed_as_weapon.causal.positive."
                "measured_decay_per_frame", "max", 0.7),
        (FINAL, "controls.A11_seed_as_weapon.causal.positive."
                "enemy_removed_from_live_table", "eq", True),
        (FINAL, "controls.A11_seed_as_weapon.causal.negative_no_press."
                "carry_broken", "eq", False),
        (FINAL, "controls.A11_seed_as_weapon.causal.negative_no_press."
                "hit_frame", "eq", None),
    ]),
    "A12_seed_color_change": ("Triangle while genuinely carrying vs control", [
        (SEEDS, "controls.A12_seed_color_change.positive.carry_attached", "eq", True),
        (SEEDS, "controls.A12_seed_color_change.negative.carry_attached", "eq", True),
        (SEEDS, "controls.A12_seed_color_change.distinct_outcome", "eq", True),
    ]),
    "A13_cycle_plant_output": ("X while carrying vs control", [
        (SEEDS, "controls.A13_cycle_plant_output.positive.carry_attached", "eq", True),
        (SEEDS, "controls.A13_cycle_plant_output.negative.carry_attached", "eq", True),
        (SEEDS, "controls.A13_cycle_plant_output.distinct_outcome", "eq", True),
        (SEEDS, "controls.A13_cycle_plant_output.distinct_from_triangle", "eq", True),
    ]),
    "A14_plant_seed": ("plant slot creations follow cross presses (4/4)", [
        (FINAL, "controls.A14_plant_seed.creations", "min_len", 4),
        (FINAL, "controls.A14_plant_seed.creation_types", "contains", 6),
        (FINAL, "controls.A14_plant_seed.all_creations_follow_cross_press",
         "eq", True),
    ]),
    "A15_uproot_plant": ("plant teardowns follow square presses; seed "
                         "descends to ground at pinned X/Z (4/4)", [
        (FINAL, "controls.A15_uproot_plant.teardowns", "min_len", 4),
        (FINAL, "controls.A15_uproot_plant.all_teardowns_follow_square_press",
         "eq", True),
        (FINAL, "controls.A15_uproot_plant.seed_return_law", "eq", True),
    ]),
    "A16_swinging": ("same-anchor grab (up+cross -> sustained state 5) and "
                     "release (cross -> leaves 5, lands)", [
        (SEEDS, "controls.A16_swinging.grab.positive.sustained_attach",
         "eq", True),
        (SEEDS, "controls.A16_swinging.grab.negative_no_input."
                "sustained_attach", "eq", False),
        (SEEDS, "controls.A16_swinging.release.positive.left_state5",
         "eq", True),
        (SEEDS, "controls.A16_swinging.release.negative_idle.left_state5",
         "eq", False),
    ]),
    "A17_camera_controls": ("camera struct 0x80095358 moves under L1 only", [
        (BEHAVIOR, "controls.camera.l1_changes_camera", "eq", True),
        (BEHAVIOR, "controls.camera.negative_control_camera_static", "eq", True),
    ]),
    "A18_pause": ("position freeze/resume", [
        (LIFE, "experiments.pause_freeze.resume_restores_motion", "eq", True),
        (NEG, "controls.no_start_no_pause.displacement", "min", 1),
    ]),
    "A19_status_display": ("Select panel frame vs identical no-Select window", [
        (BEHAVIOR, "controls.status.select_produces_different_frame", "eq", True),
    ]),
    "A20_circle_noop": ("null delta on all non-display fields", [
        (ORACLE, "synthetic_probes.circle_negative.null_delta_fields",
         "nonempty", None),
    ]),
}

SYSTEMS = {
    "audio_spu": "phase2_spu_pitch_mutation (same-scene pitch fires spu_voices only)",
    "presentation": "phase2_presentation_baseline + ALLMODS mutation test",
    "contact_pool": "phase2_pool_arc_oracle + capacity hang proof",
    "death_lifecycle": "phase2_death_matrix (14/16 stages) + phase2_lifecycle_oracle",
    "results_screens": "phase2_results_baseline (23 anchors, compared by the runner)",
}

_cache: dict[str, object] = {}


def lookup(artifact: str, dotted: str):
    if artifact not in _cache:
        _cache[artifact] = json.loads((ROOT / artifact).read_text())
    node = _cache[artifact]
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"{artifact}:{dotted} (missing at '{part}')")
        node = node[part]
    return node


def run_check(artifact, path, op, expected):
    try:
        val = lookup(artifact, path)
    except (KeyError, FileNotFoundError) as exc:
        return False, f"unreadable: {exc}"
    ok = {"eq": lambda: val == expected,
          "min": lambda: isinstance(val, (int, float)) and val >= expected,
          "max": lambda: isinstance(val, (int, float)) and val <= expected,
          "contains": lambda: (str(expected) in val if isinstance(val, str)
                               else expected in (val or ())),
          "not_contains": lambda: (str(expected) not in val if isinstance(val, str)
                                   else expected not in (val or ())),
          "min_len": lambda: hasattr(val, "__len__") and len(val) >= expected,
          "nonempty": lambda: bool(val)}[op]()
    return ok, (f"{artifact.split('/')[-1]}:{path} {op} {expected!r} -> "
                f"{'OK' if ok else f'FAIL (got {val!r})'}")


def main() -> int:
    reg = yaml.safe_load((ROOT / "analysis" / "mechanics_baseline.yaml").read_text())
    rows = [r for r in reg["rows"] if r["section"] == "A"]
    entries, gaps = {}, []
    for r in rows:
        rid = r["id"]
        observable, checks = CHECKS.get(rid, (None, []))
        results = [run_check(*chk) for chk in checks]
        covered = bool(checks) and all(ok for ok, _ in results)
        entries[rid] = {
            "name": r["name"],
            "registry_status": r["status"],
            "covered": covered,
            "observable": observable,
            "evidence_checks": [msg for _, msg in results] or
                               ["NO EVIDENCE MAPPED"],
        }
        if not covered:
            gaps.append({"row": rid,
                         "reason": ("no evidence mapped" if not checks else
                                    "; ".join(m for ok, m in results if not ok)),
                         "next": r.get("next", "")})
    doc = {
        "_comment": "DERIVED coverage map: rows enumerated from the registry, "
                    "verdicts computed by INSPECTING the evidence artifacts "
                    "(file+path+predicate per check — see tools/"
                    "phase2_coverage_map.py CHECKS). Gaps are computed, never "
                    "authored. Regenerate: tools/phase2_coverage_map.py.",
        "generated": date.today().isoformat(),
        "registry_rows": len(rows),
        "covered": sum(1 for e in entries.values() if e["covered"]),
        "rows": entries,
        "gaps": gaps,
        "gate_bullet_3_met": not gaps,
        "systems": SYSTEMS,
    }
    out = ROOT / "analysis" / "phase2_negative_coverage_map.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[coverage] {doc['covered']}/{doc['registry_rows']} core actions "
          f"covered; gaps: {len(gaps) or 'none'}")
    for g in gaps:
        print(f"  GAP {g['row']}: {g['reason']}")
    print(f"[coverage] gate bullet 3: {'met' if not gaps else 'NOT met'}")
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
