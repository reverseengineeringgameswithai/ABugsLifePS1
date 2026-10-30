#!/usr/bin/env python3
"""Phase-2 seed-carry + handstand oracle from the operator helper fixture
movies/Phase_Helpers/carry_handstand.movie.json (save-anchored, pristine
Training; replays deterministically end to end).

Laws extracted (verified byte-identical across two replays):
  CARRY  the carried movable seed is a chunk-31 actor (id 11 here, record 0);
         while carried its record X/Z EQUAL the player's exactly and its Y sits
         at a FIXED overhead offset of 19200 units (600<<5; Y-down, so the seed
         rides 19200 above the player). Pickup (Square, ~f310) pulls the record
         to the player; drop (~f673) detaches it at the drop site. (The first
         version claimed XYZ identity and tested only X/Z — external review
         caught the untested Y offset in the artifact's own f660 sample.)
  HANDSTAND  stationary mount: player position frozen for >100 frames while the
         grounded flag (0x800A6582) reads 0 and animation cycles; dismount hop
         sets the state word 0x800A6580 = 6 (a new state id beyond the slide's
         0/1/4/5).

Usage: python3 tools/phase2_carry_handstand_oracle.py [--port 23472]
Output: analysis/phase2_carry_handstand_oracle.json
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

MOVIE = "movies/Phase_Helpers/carry_handstand.movie.json"
ANCHOR = "movies/Phase_Helpers/carry_handstand.movie.sav"
RECORDS = 0x8009FE04


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

    def sample():
        p = struct.unpack("<iii", rd(0x800A6500, 12))
        rid, x, y, z = struct.unpack("<Iiii", rd(RECORDS, 16))
        b = rd(0x800A6540, 0x60)
        return {"player": list(p), "rec0_id": rid, "rec0_xyz": [x, y, z],
                "anim": [b[0x02], b[0x06]], "s80": b[0x40], "grounded": b[0x42]}

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"

    FRAMES = (290, 330, 540, 570, 600, 660, 680, 700,
              1080, 1120, 1160, 1200, 1240)
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
        for mf in FRAMES:
            c.call("movie.advanceToFrame",
                   {"frame": mf, "max_frames": r["frame_count"] + 700}, timeout=600)
            series[str(mf)] = sample()
        runs.append(series)

    s = runs[0]
    attached = s["660"]
    carry_y_offset = attached["player"][1] - attached["rec0_xyz"][1]
    carry_attached = (attached["player"][0] == attached["rec0_xyz"][0]
                      and attached["player"][2] == attached["rec0_xyz"][2]
                      and carry_y_offset == 19200)
    hs_frozen = (s["1120"]["player"] == s["1160"]["player"] == s["1200"]["player"])
    doc = {
        "_comment": "Seed-carry + handstand oracle (rows A09/A10) from the operator "
                    "helper fixture. Regenerate: tools/phase2_carry_handstand_oracle.py.",
        "generated": date.today().isoformat(),
        "fixture": {"movie": MOVIE, "movie_sha256": sha256_file(ROOT / MOVIE),
                    "anchor": ANCHOR, "anchor_sha256": sha256_file(ROOT / ANCHOR),
                    "scene": "Training (17)",
                    "input_edges": {"pickup_square": 310, "drop_square": 673,
                                    "handstand_window": [1040, 1240]}},
        "deterministic_across_replays": runs[0] == runs[1],
        "series": s,
        "laws": {
            "carry_attachment": "carried seed record X/Z == player X/Z exactly; "
                                "Y = player Y - 19200 (fixed overhead offset, 600<<5)",
            "carry_y_offset": carry_y_offset,
            "carry_seed": "chunk-31 record 0, id 11 (movable seed class)",
            "carry_attached_at_f660": carry_attached,
            "drop": "record detaches and rests at the drop site (f680/f700)",
            "handstand": "player position frozen >100 frames with grounded==0 "
                         "while animation cycles",
            "handstand_frozen": hs_frozen,
            "dismount_state": {"frame": 1240, "s80": s["1240"]["s80"],
                               "note": "state word 6 = dismount hop (new state id)"},
        },
    }
    out = ROOT / "analysis" / "phase2_carry_handstand_oracle.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[carry_handstand] wrote {out}: deterministic="
          f"{doc['deterministic_across_replays']} attached={carry_attached} "
          f"handstand_frozen={hs_frozen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
