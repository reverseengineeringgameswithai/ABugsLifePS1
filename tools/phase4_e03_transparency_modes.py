#!/usr/bin/env python3
"""Phase-4 E03: decode semi-transparency blend modes from mid-frame captures.

Sources: the *_midframe.json captures from tools/phase4_e03_midframe_walk.py
(full command words per GP0 command). Two decodes:
  - E1 draw-mode commands: STP mode = bits 5-6 of the command word;
  - textured semi-transparent polygons (opcode bit 0x02 set, bit 0x04 set):
    STP mode = bits 5-6 of the texpage attribute, which rides the high half of
    the SECOND uv word -- w[4] for flat-shaded, w[5] for gouraud (clut rides
    uv word 1's high half).
Internal check: per scene, the per-mode counts must sum to the scene's
semi-transparent prim count.

Usage: python3 tools/phase4_e03_transparency_modes.py --dump-dir <dir> \
           [--out analysis/phase4_e03_transparency_modes.json]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODES = {0: "B/2+F/2 (average)", 1: "B+F (additive)",
         2: "B-F (subtractive)", 3: "B+F/4 (quarter)"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-dir", required=True)
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e03_transparency_modes.json"))
    args = ap.parse_args()

    scenes = {}
    for meta_path in sorted(Path(args.dump_dir).glob("*_midframe.json")):
        m = json.loads(meta_path.read_text())
        f0num = m["trace_entries"][0]["frame"]
        f0 = [e for e in m["trace_entries"] if e["frame"] == f0num]
        e1_modes, prim_modes = Counter(), Counter()
        semis = 0
        for e in f0:
            op = e["command_id"]
            w = [int(x, 16) for x in e.get("words", [])]
            if op == 0xE1:
                e1_modes[MODES[(w[0] >> 5) & 3]] += 1
            elif 0x20 <= op <= 0x7F and (op & 0x02):
                semis += 1
                if 0x20 <= op <= 0x3F and (op & 0x04):
                    idx = 5 if op & 0x10 else 4
                    if idx < len(w):
                        prim_modes[MODES[(w[idx] >> 16 >> 5) & 3]] += 1
        scenes[m["label"]] = {
            "save": m["save"], "save_sha256": m["save_sha256"],
            "traced_frame": f0num,
            "e1_stp_modes": dict(e1_modes),
            "semitrans_prims": semis,
            "textured_semitrans_prim_modes": dict(prim_modes),
            "all_semitrans_are_textured_polys": sum(prim_modes.values()) == semis,
        }
    out = {
        "_comment": "Phase-4 E03 semi-transparency blend-mode distribution per "
                    "scene class, decoded from mid-frame gp0Trace words (E1 bits "
                    "5-6; textured prims: texpage attr in the 2nd uv word's high "
                    "half). Regenerate: midframe_walk.py per scene, then this.",
        "generated": str(date.today()),
        "scenes": scenes,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    for lbl, s in scenes.items():
        print(lbl, s["semitrans_prims"], s["textured_semitrans_prim_modes"],
              "consistent:", s["all_semitrans_are_textured_polys"])
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
