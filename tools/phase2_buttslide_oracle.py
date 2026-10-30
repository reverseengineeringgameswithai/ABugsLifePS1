#!/usr/bin/env python3
"""Phase-2 buttslide (downhill abdomen slide) oracle from the operator helper
fixture movies/Phase_Helpers/buttslide_carry_handstand.movie.json.

The fixture is save-anchored on the pristine image (Training, scene 17). Its
EARLY section (the buttslide, movie frames ~341..520) replays deterministically;
later sections (carry, handstand) desync and are NOT used as evidence.

Slide state machine (player globals; verified byte-identical across replays):
  anim pair   u8 0x800A6542 / 0x800A6546   walk=(6,7); slide anim = (11,12)
  state word  u8 0x800A6580               0 ground, 1 air(jump), 4 slam/dive,
                                          5 ground slide
  grounded    u8 0x800A6582               0 while airborne
Sequence on double-tap X while moving: 0 -> 1 -> 4 (airborne dive, anim 11/12)
-> 5 (grounded slide, fast displacement) -> back to 0/walk.

Usage: python3 tools/phase2_buttslide_oracle.py [--port 23472]
Output: analysis/phase2_buttslide_oracle.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

MOVIE = "movies/Phase_Helpers/buttslide_carry_handstand.movie.json"
ANCHOR = "movies/Phase_Helpers/buttslide_carry_handstand.movie.sav"
SAMPLE_FRAMES = (300, 341, 360, 380, 400, 430, 460, 500)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def probe():
        b = rd(0x800A6540, 0x60)
        return {"anim_a": b[0x02], "anim_b": b[0x06], "state80": b[0x40],
                "grounded": b[0x42], "flag83": b[0x43], "flag84": b[0x44],
                "pos": list(struct.unpack("<iii", rd(0x800A6500, 12)))}

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"

    runs = []
    for _rep in range(2):
        for m in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(m, {})
            except Exception:
                pass
        r = c.call("movie.load", {"path": str(ROOT / MOVIE)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        assert st.get("playing") and st.get("reproducible"), st
        series = {}
        for mf in SAMPLE_FRAMES:
            c.call("movie.advanceToFrame",
                   {"frame": mf, "max_frames": r["frame_count"] + 700}, timeout=600)
            series[str(mf)] = probe()
        runs.append(series)

    slide_air = runs[0]["400"]
    slide_ground = runs[0]["430"]
    doc = {
        "_comment": "Buttslide (A06) oracle from the operator helper fixture; early "
                    "section only (later carry/handstand sections desync — see the "
                    "Phase-2 note). Regenerate: tools/phase2_buttslide_oracle.py.",
        "generated": date.today().isoformat(),
        "fixture": {"movie": MOVIE, "movie_sha256": sha256_file(ROOT / MOVIE),
                    "anchor": ANCHOR, "anchor_sha256": sha256_file(ROOT / ANCHOR),
                    "scene": "Training (17)",
                    "double_tap_frames": [356, 376]},
        "deterministic_across_replays": runs[0] == runs[1],
        "series": runs[0],
        "signature": {
            "slide_anim_pair": [11, 12],
            "state80_sequence": "0 -> 1 (air) -> 4 (slam/dive) -> 5 (ground slide)",
            "airborne_slide": {"anim": [slide_air["anim_a"], slide_air["anim_b"]],
                               "state80": slide_air["state80"],
                               "grounded": slide_air["grounded"]},
            "ground_slide_state80": slide_ground["state80"],
        },
    }
    out = ROOT / "analysis" / "phase2_buttslide_oracle.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[buttslide] wrote {out}: deterministic={doc['deterministic_across_replays']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
