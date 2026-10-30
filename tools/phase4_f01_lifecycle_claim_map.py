#!/usr/bin/env python3
"""F01 `lifecycle`: register the per-phase claim map that never existed.

The written-bar assessment's gap for this dimension was exact: "no per-phase claim map
exists; phases are evidenced ad hoc rather than registered — cheap to assemble, never
assembled." This assembles it. The lifecycle axis (mechanics_baseline.yaml, section G):
cold boot / load / first use / repeated use / exhaustion / retirement / reuse — applied
to F01's subject, the scene-transition request machinery (0x800823A0, region dispatch,
finalizer).

Facts derived from pinned artifacts at run time; judgments authored. Assesses, does not
promote; fresh verifier owns status. Usage: python3 tools/phase4_f01_lifecycle_claim_map.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_f01_lifecycle_claim_map.json"))
    args = ap.parse_args()

    pins = []

    def derive(rel: str) -> dict:
        p = ROOT / rel
        pins.append({"path": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        return json.loads(p.read_text())

    oracle = derive("analysis/phase4_f01_original_oracle.json")
    probe = derive("analysis/phase4_f01_request2_probe.json")
    breadth = derive("analysis/phase4_f01_breadth_assertions.json")
    sweep = derive("analysis/phase4_f01_campaign_breadth.json")
    static = derive("analysis/phase4_f01_objective_lifecycle.json")
    attr = derive("analysis/phase4_f01_retirement_attribution.json")

    v = sweep["f01_transition_request_0x800823A0"]["by_value"]
    facts = {
        "cold_boot_fixtures": 2,
        "oracle_timeline_scenes": [s["scene"] for s in oracle["scene_timeline"]],
        "oracle_all_passed": oracle["all_passed"],
        "death_control_outcome": probe["element_outcome"],
        "levels_with_decisions": breadth["levels_asserted"],
        "total_decisions": breadth["total_decisions_checked"],
        "max_decisions_one_level": max(
            r["counts"]["decisions"] for r in breadth["results"].values() if not r.get("error")),
        "clear_writers_observed": v["0"]["writer_pcs"],
        "clear_writer_level_count": v["0"]["levels"],
        "static_assertion_tool": static["tool"],
        "attr_convention_holds": attr["convention_holds_at_every_row"],
    }

    phases = {
        "cold_boot": {
            "state": "covered",
            "claim": "the machinery is exercised from genuine cold boot, twice, with "
                     "nothing injected: one natural completion (request 1 -> finalizer) "
                     "and one natural death (request 2 -> skip)",
            "evidence": ["analysis/phase4_f01_original_oracle.json",
                         "analysis/phase4_f01_request2_probe.json"],
            "fact": f"oracle all_passed={facts['oracle_all_passed']}, death control "
                    f"{facts['death_control_outcome']}; both from-boot with pre-load "
                    "noise rejected by instruction self-certification",
        },
        "load": {
            "state": "covered",
            "claim": "load-time construction of the machinery's state is pinned: the "
                     "converter builds the sector/region table at scene load and the "
                     "request cell's load-time value is observed as 0",
            "evidence": ["analysis/phase4_f01_objective_lifecycle.json",
                         "analysis/phase4_e02_disc_region_code_census.json"],
            "fact": f"static census via {facts['static_assertion_tool']}; disc-side "
                    "census 16/16 scenes, 0 disagreements",
        },
        "first_use": {
            "state": "covered",
            "claim": "the first transition decision of every level obeys the branch law",
            "evidence": ["analysis/phase4_f01_breadth_assertions.json"],
            "fact": f"{facts['levels_with_decisions']}/19 levels, first decision "
                    "asserted on each, 0 law failures",
        },
        "repeated_use": {
            "state": "covered",
            "claim": "multiple decisions within one level obey the law, including "
                     "mixed call/skip sequences",
            "evidence": ["analysis/phase4_f01_breadth_assertions.json"],
            "fact": f"{facts['total_decisions']} decisions total; up to "
                    f"{facts['max_decisions_one_level']} in one level (LEVEL07: 1 call "
                    "+ 4 skips)",
        },
        "exhaustion": {
            "state": "not_applicable_with_reason",
            "claim": "the request word is a scalar latch, not a pool; its saturated "
                     "state IS the single-shot guard ([0x800823A0] != 0 suppresses "
                     "every further region trigger in the scene)",
            "evidence": ["analysis/phase4_f01_objective_lifecycle.json"],
            "fact": "guard pinned statically (re-read at 0x8004965C, bnez 0x80049664); "
                    "exactly one exit decision per completed level across 19 replays is "
                    "the guard operating",
        },
        "retirement": {
            "state": "covered",
            "claim": "the cell is cleared (retired to 0) after consumption, by a small "
                     "observed writer set, on every level -- attributed to EXACT store "
                     "instructions, with the write-watch +4 reporting convention "
                     "disclosed",
            "evidence": ["analysis/phase4_f01_campaign_breadth.json",
                         "analysis/phase4_f01_retirement_attribution.json"],
            "fact": f"reported value-0 writer PCs {facts['clear_writers_observed']} "
                    f"observed on {facts['clear_writer_level_count']}/19 levels; each "
                    "reported pc is the true store +4 (compiled-C verified, "
                    f"convention_holds_at_every_row={facts['attr_convention_holds']}). "
                    "Instruction-exact: two mechanisms -- shell clears via "
                    "`sh zero,0x23a0(at)` at 0x8004FE44/0x8005B888 (direct), and the "
                    "movement integrator's 16-bit clear split into byte pairs "
                    "`sb zero,0/1(s6)` at 0x80036B8C/0x80036CCC/0x80036D08 "
                    "(register-base; the watch itself proved each write landed on the "
                    "cell)",
        },
        "reuse": {
            "state": "covered",
            "claim": "the cell is reused after each retirement: successive "
                     "set->consume->clear cycles within one session, plus the full "
                     "birth-to-retirement arc from BIOS in a single from-boot run",
            "evidence": ["analysis/phase4_f01_breadth_assertions.json",
                         "analysis/phase4_f01_request2_probe.json"],
            "fact": f"up to {facts['max_decisions_one_level']} successive request "
                    "cycles in one LEVEL07 session (4 skips then the exit call); the "
                    "from-boot death session's access log shows the whole arc -- BIOS "
                    "init (fr 98), EXE-init clear (0x8005F6A0, fr 1141), shell clear "
                    "(0x8004FADC), level-entry clears (0x8005B888/0x8004FE44, fr "
                    "5724-5725), certified death store 2 (0x8004A8B4, fr 6536), "
                    "consumer clear one frame after the decision (0x8004FE44, fr 6656)",
            "residual_note": "a cross-LEVEL chain (level->results->next-level) in one "
                             "armed session remains unobserved, but that belongs to the "
                             "scene+overlay TRANSITIONS axis, not to this cell's reuse; "
                             "recorded here so it is not lost. ⚠️ It CANNOT be closed "
                             "by arming a go_to_end movie -- those are CachedInterpreter "
                             "recordings and desync silently under any CPU hook; it "
                             "needs an Interpreter recording or poll-only observation",
        },
    }

    counts = {}
    for p in phases.values():
        counts[p["state"]] = counts.get(p["state"], 0) + 1

    doc = {
        "_comment": "F01 lifecycle per-phase claim map -- the registration the "
                    "written-bar assessment named as its gap. Facts derived from pinned "
                    "artifacts; judgments authored. Regenerate: "
                    "tools/phase4_f01_lifecycle_claim_map.py",
        "schema": "abl-phase4-f01-lifecycle-claim-map/1",
        "generated": date.today().isoformat(),
        "row_id": "F01_anthill",
        "subject": "scene-transition request machinery (0x800823A0, region dispatch, "
                   "finalizer)",
        "axis": "cold boot / load / first use / repeated use / exhaustion / retirement "
                "/ reuse (mechanics_baseline.yaml section G)",
        "authority": {"promotes_row_or_dimension": False, "requires_fresh_verifier": True},
        "facts": facts,
        "evidence_pins": pins,
        "phases": phases,
        "counts": counts,
        "summary": f"{counts.get('covered', 0)} covered, "
                   f"{counts.get('not_applicable_with_reason', 0)} n/a-with-reason, "
                   f"{counts.get('partial', 0)} partial of 7 phases. Remaining gap is "
                   "ONE claim: a multi-level chain with watches armed.",
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[lifecycle-map] {doc['summary']}")
    for name, p in phases.items():
        print(f"  {p['state']:26s} {name}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
