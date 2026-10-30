#!/usr/bin/env python3
"""Pin the B06/B08 decisive fixtures by hash, and verify them.

WHY THIS EXISTS
---------------
`movies/` is gitignored by policy ("forbidden local-capture artifacts"), so the
movies and save states that carry every runtime claim for these rows CANNOT be
committed. That is fine -- but it means a clean checkout has no way to tell whether
the operator's local `B08_movie.json` is the one the evidence was taken from. When
these rows were first (wrongly) called solved, their hashes lived only inside the
prose artifact, which fails the clean-checkout rule.

This writes a committed manifest of what the evidence depends on, and can re-verify
it. It also records, per fixture, the three bindings the movie format does NOT carry,
because each of them fails silently:

  * `start_state.sha256` is null in every movie -- a movie does not pin the state it
    was recorded against, so the wrong `.sav` replays as a silent desync.
  * the CPU execution mode is not recorded -- a CachedInterpreter recording desyncs
    the moment anything is armed.
  * the arm phase is not recorded -- a save-state movie can replay one frame out of
    phase, silently.

So this manifest deliberately pins the `.sav` hash ITSELF, which is the binding the
format is missing.

USAGE
    tools/phase4_b06_b08_pin_fixtures.py --write     # (re)generate the manifest
    tools/phase4_b06_b08_pin_fixtures.py             # verify; non-zero on drift
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "analysis/phase4_b06_b08_fixtures.json"

# Every fixture a runtime claim for these rows rests on.
FIXTURES = {
    # --- COLD-BOOT oracles (DoD item 1). Operator-recorded 2026-08-01, from_boot,
    #     no pokes anywhere in the run. These are the decisive fixtures now.
    "Phase4/b06_invincibility_hits_from_boot.movie.json":
        "B06 COLD-BOOT ORACLE, LEVEL01 (scene 1). Natural collect -> contacts while "
        "active -> natural expiry -> a contact that lands. Asserted by "
        "tools/phase4_b06_b08_oracle.py --row b06. Recorded in a stage OTHER than the "
        "scene-11 Birdnest every earlier fixture used, so it also breaks the "
        "single-stage confinement.",
    "Phase4/B08_bubble_repeated_hits_from_boot.movie.json":
        "B08 COLD-BOOT ORACLE, LEVEL06 (scene 11). Natural collect -> 3 absorbs -> pop "
        "-> a contact that lands, and no tick touches the slot while it is negative. "
        "Asserted by tools/phase4_b06_b08_oracle.py --row b08.",
    "b06_08_LEVEL13.movie.json":
        "BREADTH FIXTURE, operator-recorded 2026-08-01. Level 13 = scene 9 = disc dir "
        "LEVEL09, a directory neither earlier fixture used. Both powers collected "
        "NATURALLY in one run: B06 grant 400 @f13513 with a full 400-tick countdown, B08 "
        "grant -3 @f14547 with all three absorbs to the pop, then damage lands. Format v4 "
        "with armed_while_paused=true, so the emulator applies the phase correction "
        "itself -- no rephase needed.",
    # --- earlier save-state fixtures, retained: they carry the perturbation runs
    #     (capacity, cross-power transition, harvester) that the cold-boot movies do not.
    "B08_movie.json": "Save-state anchored. The R0-R5 perturbation runs: capacity "
                      "refresh, cross-power transition, harvester intersection.",
    "B06_movie.json": "Save-state anchored. Natural invincibility grant at frame 116821.",
    "b06_desync_test.movie.json": "The arm-phase desync fixture (see "
                                  "EXP_2026-08-01_savestate_movie_arm_phase_desync).",
}

# Which stage each fixture exercises. Operator-attested, cross-checked against the
# measured save-state -> scene mapping from the 16-scene sweep (level01.sav -> scene 1,
# level_06.sav -> scene 11).
FIXTURE_SCENE = {
    "b06_08_LEVEL13.movie.json": {"level": "LEVEL13", "scene_id": 9},
    "Phase4/b06_invincibility_hits_from_boot.movie.json": {"level": "LEVEL01", "scene_id": 1},
    "Phase4/B08_bubble_repeated_hits_from_boot.movie.json": {"level": "LEVEL06", "scene_id": 11},
    "B08_movie.json": {"level": "LEVEL06", "scene_id": 11},
    "B06_movie.json": {"level": "LEVEL06", "scene_id": 11},
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(name: str, purpose: str) -> dict:
    mv = ROOT / "movies" / name
    rec = {"purpose": purpose, "movie": f"movies/{name}"}
    if name in FIXTURE_SCENE:
        rec["stage"] = FIXTURE_SCENE[name]
    if not mv.exists():
        rec["status"] = "MISSING -- gitignored and not present in this working tree"
        return rec
    doc = json.loads(mv.read_text())
    ss = doc.get("start_state") or {}
    sav_path = ss.get("path")
    rec.update({
        "status": "present",
        "movie_sha256": sha256(mv),
        "movie_size": mv.stat().st_size,
        "frames": len(doc.get("frames") or []),
        "format_version": doc.get("version"),
        "from_boot": bool(ss.get("from_boot")),
        "reproducible_only_from_state": bool(ss.get("reproducible_only_from_state")),
        "declared_start_state": sav_path,
        "start_state_sha256_in_movie": ss.get("sha256"),
        "armed_while_paused": doc.get("armed_while_paused"),
    })
    if sav_path:
        sav = Path(sav_path)
        if not sav.is_absolute():
            sav = ROOT / sav
        if sav.exists():
            rec["start_state_sha256_measured"] = sha256(sav)
            rec["start_state_size"] = sav.stat().st_size
        else:
            rec["start_state_sha256_measured"] = None
            rec["start_state_status"] = "MISSING"
    return rec


def build() -> dict:
    return {
        "_comment": (
            "Central hash pin for the fixtures the B06/B08 runtime evidence depends on. "
            "These files are gitignored by policy and therefore absent from a clean "
            "checkout; this manifest is how a clean checkout can tell whether an "
            "operator-held copy is the one the evidence came from. Regenerate/verify: "
            "tools/phase4_b06_b08_pin_fixtures.py [--write]"),
        "_missing_bindings": (
            "start_state.sha256 is null in EVERY movie, so the format does not pin the "
            "state it was recorded against; neither the CPU execution mode nor the arm "
            "phase is recorded either. All three fail silently. This manifest pins the "
            ".sav hash itself, which is the binding the format lacks."),
        "_oracle_status": (
            "As of 2026-08-01 both rows HAVE a cold-boot oracle: the two Phase4/*_from_boot "
            "movies are anchored to a power-on boot (from_boot true) and their full natural "
            "lifecycles are asserted, with no pokes, by tools/phase4_b06_b08_oracle.py. The "
            "remaining save-state fixtures are retained because they carry the perturbation "
            "runs (capacity refresh, cross-power transition, harvester intersection) that a "
            "natural playthrough cannot produce on demand."),
        "fixtures": {k: describe(k, v) for k, v in FIXTURES.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="regenerate the manifest")
    args = ap.parse_args()

    cur = build()
    if args.write:
        MANIFEST.write_text(json.dumps(cur, indent=1, sort_keys=True) + "\n")
        print("wrote", MANIFEST.relative_to(ROOT))
        for name, rec in sorted(cur["fixtures"].items()):
            print("  %-30s %s" % (name, rec.get("status")))
        return 0

    if not MANIFEST.exists():
        print("no manifest yet; run with --write")
        return 1
    old = json.loads(MANIFEST.read_text())
    fail = 0
    for name, rec in sorted(cur["fixtures"].items()):
        was = old["fixtures"].get(name, {})
        if rec.get("status") != "present":
            print("  %-30s ABSENT (gitignored fixture not in this tree)" % name)
            continue
        for field in ("movie_sha256", "start_state_sha256_measured"):
            if was.get(field) and rec.get(field) != was.get(field):
                print("  %-30s DRIFT %s\n      pinned   %s\n      measured %s"
                      % (name, field, was.get(field), rec.get(field)))
                fail = 1
        if not fail:
            print("  %-30s OK  movie %s.. state %s.." % (
                name, rec["movie_sha256"][:12],
                (rec.get("start_state_sha256_measured") or "----")[:12]))
    print("FIXTURE PIN:", "FAIL" if fail else "PASS")
    return fail


if __name__ == "__main__":
    raise SystemExit(main())
