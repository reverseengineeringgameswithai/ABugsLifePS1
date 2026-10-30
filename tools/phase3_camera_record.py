#!/usr/bin/env python3
"""Phase-3 WP5: type the camera record — and establish that it is DERIVED.

The camera struct (0x80095358, Canon: written by camera_follow_update 0x8004DF18)
holds two position triples. Naming them is easy; the useful question for a mod is
which of them, if any, is AUTHORITATIVE. So this tool answers that with
experiments rather than adjectives:

  follow law     does the camera position exponentially chase the +0x0C triple?
                 (measured: the fraction of the remaining gap it closes per tick)
  write position poke camera_pos +50000 and watch it for 24 frames
  write target   poke camera_target +50000 and watch BOTH triples

Result (see the artifact): a poke into EITHER triple decays away — the position is
pulled back toward the target by the follow law, and the target is itself
recomputed from scratch every tick. **The camera struct is an OUTPUT.** A mod that
wants to move the camera must change the code that produces it (or the inputs that
code reads), not poke the struct. That is a contract you cannot get from a symbol
name, and it is exactly the kind of thing the roadmap's DoF #6 asks for.

Usage: python3 tools/phase3_camera_record.py [--port 23473]
Output: analysis/phase3_camera_record.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         inspect_state_before_load,
                                         verified_media_identity,
                                         write_live_evidence)
except ModuleNotFoundError:  # imported as tools.phase3_camera_record in tests
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               inspect_state_before_load,
                                               verified_media_identity,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

CAMERA = 0x80095358
POS, TARGET = 0x00, 0x0C
PLAYER = 0x800A6500
POKE = 50000


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

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def tri(buf, off):
        return struct.unpack_from("<iii", buf, off)

    def load():
        r = c.call("emulator.loadState",
                   {"path": str(ROOT / anchor), "pause_after_load": True})
        assert r.get("loaded"), r
        c.call("emulator.clearControllerState", {"port": 0})

    # ---- 1. the follow law: pos chases target ------------------------------
    load()
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    c.call("emulator.advanceFrames", {"frames": 15})
    frames = []
    for _ in range(40):
        frames.append(rd(CAMERA, 0x60))
        c.call("emulator.advanceFrames", {"frames": 1})
    c.call("emulator.clearControllerState", {"port": 0})

    ratios = []
    for t in range(len(frames) - 1):
        p0, p1, tg = tri(frames[t], POS), tri(frames[t + 1], POS), tri(frames[t], TARGET)
        for ax in range(3):
            gap, step = tg[ax] - p0[ax], p1[ax] - p0[ax]
            if abs(gap) > 200 and step:
                ratios.append(step / gap)
    ratios.sort()
    follow = round(ratios[len(ratios) // 2], 4) if ratios else None

    # ---- 2/3. is EITHER triple authoritative? poke each and watch ----------
    def poke_trial(off: int):
        load()
        c.call("emulator.advanceFrames", {"frames": 6})
        b = rd(CAMERA, 0x60)
        base_pos, base_tgt = tri(b, POS), tri(b, TARGET)
        src = base_pos if off == POS else base_tgt
        c.call("debugger.scatterWrite", {"atomic": True, "writes": [
            {"address": "0x%08X" % (CAMERA + off + i * 4), "type": "u32",
             "value": (src[i] + POKE) & 0xFFFFFFFF} for i in range(3)]})
        traj = []
        for _ in range(6):
            c.call("emulator.advanceFrames", {"frames": 4})
            b = rd(CAMERA, 0x60)
            traj.append({"pos_x": tri(b, POS)[0], "target_x": tri(b, TARGET)[0]})
        written = src[0] + POKE
        drift = traj[-1]["pos_x" if off == POS else "target_x"] - written
        return {
            "poked": "camera_pos" if off == POS else "camera_target",
            "written_value_x": written,
            "trajectory": traj,
            "drift_from_written": drift,
            "held": abs(drift) < 8000,
        }

    pos_trial = poke_trial(POS)
    tgt_trial = poke_trial(TARGET)
    derived = not pos_trial["held"] and not tgt_trial["held"]
    run_provenance = finish_run(
        args, generator="tools/phase3_camera_record.py",
        anchor={"save": anchor, "fixture_sha256": fixture_pin(anchor),
                "state_inspections": [state_inspection],
                "media_identity": media_identity},
        timing={"settle_frames": 24, "poke_advance_frames": 24,
                "poke_delta": POKE},
    )

    doc = {
        "_comment": "Phase-3 camera record: the struct's two position triples, and "
                    "the experiments showing the struct is an OUTPUT (a poke into "
                    "EITHER triple decays away — the position is pulled back toward "
                    "the target by the follow law, and the target is recomputed each "
                    "tick). A mod must change the producer, not the struct. "
                    "Regenerate: tools/phase3_camera_record.py",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "media": {"serial": status.get("game_serial")},
        "media_identity_after_connect": media_identity,
        "fixture_sha256": fixture_pin(anchor),
        "struct": {"base": "0x%08X" % CAMERA,
                   "writer": "camera_follow_update 0x8004DF18 (Canon)",
                   "camera_pos": "+0x00 s32 x3",
                   "camera_target": "+0x0C s32 x3"},
        "follow_law": {
            "_comment": "fraction of the remaining gap the camera position closes "
                        "toward the target per frame (median over moved ticks)",
            "gap_fraction_per_frame": follow,
            "samples": len(ratios),
        },
        "authority": {
            "write_camera_pos": pos_trial,
            "write_camera_target": tgt_trial,
            "struct_is_derived": derived,
            "verdict": ("DERIVED OUTPUT — neither triple is authoritative; both "
                        "pokes decay. Move the camera by changing its producer "
                        "(camera_follow_update 0x8004DF18) or that code's inputs."
                        if derived else
                        "at least one triple held the poke — re-examine"),
        },
    }
    path = ROOT / "analysis" / "phase3_camera_record.json"
    write_live_evidence(path, doc)
    print(f"[camera] follow law: closes {follow} of the gap per frame "
          f"({len(ratios)} samples)")
    print(f"[camera] poke camera_pos    -> drift {pos_trial['drift_from_written']:+d} "
          f"(held={pos_trial['held']})")
    print(f"[camera] poke camera_target -> drift {tgt_trial['drift_from_written']:+d} "
          f"(held={tgt_trial['held']})")
    print(f"[camera] struct is derived: {derived}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
