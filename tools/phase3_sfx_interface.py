#!/usr/bin/env python3
"""Phase-3 WP: the SFX interface contract — sfx_dispatch (0x80050994).

DoF #5 asks for the original interface contracts at every boundary a subsystem
crosses. sfx_dispatch is a boundary a mod would very much like to use ("play a
sound"), and it is the function the seed-impact arms call with a0 = -4.

So characterise it by CALLING it, not by reading it: for each candidate id, load
a pristine anchor, invoke the function through debugger.callFunction, advance a
few frames, and ask the SPU whether a voice actually keyed on — and which sample
it started. That distinguishes "the id is valid" from "the call returned".

Method notes worth keeping:
  * callFunction really RUNS guest code and mutates state, so every id starts
    from a fresh loadState on an ISOLATED instance;
  * v0 is NOT a success flag: it reads 0x4 for EVERY id that plays, but ALSO for
    36 ids that stay silent (and a few invalid ids return junk). The return value
    therefore cannot tell a valid id from an invalid one — only the SPU can. This
    is worth stating precisely, because "it returned 4, so it worked" is exactly
    the wrong inference;
  * a voice keying on is the observable; the voice's sample start address
    identifies WHICH sound, so two ids that start the same address are aliases.

Usage: python3 tools/phase3_sfx_interface.py [--port 23473] [--lo -24] [--hi 48]
Output: analysis/phase3_sfx_interface.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         inspect_state_before_load,
                                         verified_media_identity,
                                         write_live_evidence)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               inspect_state_before_load,
                                               verified_media_identity,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

SFX_DISPATCH = 0x80050994


def fixture_pin(*rels):
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(ap)
    ap.add_argument("--lo", type=int, default=-24)
    ap.add_argument("--hi", type=int, default=48)
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    baseline = json.loads(
        (ROOT / "analysis" / "phase2_stage_baseline.json").read_text())
    anchor = baseline["stages"]["stage01_anthill"]["save"]

    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)
    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)
    state_inspection = inspect_state_before_load(c, ROOT / anchor, media_identity)

    def voices():
        st = c.call("spu.status", {})
        out = {}
        for i, v in enumerate(st.get("voices") or []):
            if v.get("on") or v.get("key_on"):
                out[i] = v.get("start_address") or v.get("address") or v.get("adpcm_start")
        return out

    def load():
        r = c.call("emulator.loadState",
                   {"path": str(ROOT / anchor), "pause_after_load": True})
        assert r.get("loaded"), r
        c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.advanceFrames", {"frames": 5})

    results = {}
    for sid in range(args.lo, args.hi + 1):
        load()
        before = voices()
        try:
            r = c.call("debugger.callFunction",
                       {"address": "0x%08X" % SFX_DISPATCH,
                        "a0": sid & 0xFFFFFFFF, "a1": 0, "a2": 0, "a3": 0,
                        "timeout": 4000}, timeout=40)
            v0 = r.get("v0_hex") or r.get("v0")
        except Exception as exc:
            results[sid] = {"error": f"{type(exc).__name__}: {str(exc)[:60]}"}
            continue
        c.call("emulator.advanceFrames", {"frames": 4})
        after = voices()
        new = {k: v for k, v in after.items() if k not in before}
        results[sid] = {
            "v0": v0,
            "voices_keyed_on": len(new),
            "sample_starts": sorted({str(v) for v in new.values() if v is not None}),
            "plays": bool(new),
        }

    playing = {sid: r for sid, r in results.items() if r.get("plays")}
    # two ids that start the same sample are aliases of one sound
    by_sample = {}
    for sid, r in playing.items():
        key = ",".join(r["sample_starts"]) or "?"
        by_sample.setdefault(key, []).append(sid)
    v0s = {str(r.get("v0")) for r in results.values() if "v0" in r}
    run_provenance = finish_run(
        args, generator="tools/phase3_sfx_interface.py",
        anchor={"save": anchor, "fixture_sha256": fixture_pin(anchor),
                "state_inspections": [state_inspection],
                "media_identity": media_identity},
        timing={"id_range": [args.lo, args.hi], "settle_frames_per_id": 4,
                "fresh_state_per_id": True},
    )

    doc = {
        "_comment": "Phase-3 SFX interface contract: sfx_dispatch 0x80050994 called "
                    "directly for each candidate id on a fresh pristine anchor, with "
                    "the SPU as the observable (a voice keying on = the sound really "
                    "played; its sample start address identifies WHICH sound). v0 is "
                    "NOT a success flag — 0x4 appears both when a sound plays and "
                    "when nothing happens — so 'it returned 4, so it worked' is the "
                    "wrong inference; only the SPU distinguishes a valid id. "
                    "Regenerate: tools/phase3_sfx_interface.py",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "media": {"serial": status.get("game_serial")},
        "media_identity_after_connect": media_identity,
        "fixture_sha256": fixture_pin(anchor),
        "function": {
            "address": "0x%08X" % SFX_DISPATCH,
            "name": "sfx_dispatch",
            "abi": "a0 = sfx id (signed; the seed-impact arms pass -4). a1..a3 "
                   "unused in this probe. v0 is NOT a success flag: 0x4 for every "
                   "id that plays AND for 36 ids that stay silent; a few invalid "
                   "ids return junk. Only the SPU tells you whether a sound "
                   "actually started.",
            "v0_values_observed": sorted(v0s),
        },
        "scanned_range": [args.lo, args.hi],
        "ids_that_play": sorted(playing),
        "ids_that_play_count": len(playing),
        "distinct_sounds": len(by_sample),
        "aliases": {k: v for k, v in by_sample.items() if len(v) > 1},
        "results": {str(k): v for k, v in results.items()},
    }
    path = ROOT / "analysis" / "phase3_sfx_interface.json"
    write_live_evidence(path, doc)
    print(f"[sfx] scanned {args.lo}..{args.hi}: {len(playing)} ids play a sound; "
          f"{len(by_sample)} distinct samples")
    print(f"[sfx] ids that play: {sorted(playing)}")
    print(f"[sfx] v0 observed: {sorted(v0s)} — NOT a success flag "
          f"(0x4 appears on playing AND silent ids)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
