#!/usr/bin/env python3
"""F11: what objects actually exist in The Tree? A live actor census.

The row's last residual is "do acorns exist as objects at all". That was parked on the
operator answering it; it is measurable instead.

Scene 12's chunk-31 actor array is walked exactly the way the game's own species
dispatcher does (established in D16): actors at ACTOR_BASE + n*0x84, each carrying a
roster pointer at +0x80, and the species byte at roster+0x0C. This enumerates every live
actor in the stage with its species, model id, HP and VM program, so the object roster is
a measurement rather than a guess.

Known from this row already: species 32 = scout (five of them), species 14 = Dot.

    tools/phase4_f11_actor_census.py --port 23790
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ACTOR_BASE, STRIDE, SLOTS = 0x8009FD80, 0x84, 64
ROSTER_PTR_OFF, SPECIES_OFF = 0x80, 0x0C
MODEL_REGISTRY = 0x800A6300          # E05: registry 0x800A6300 + 4*id
KNOWN = {32: "scout (F11)", 14: "Dot guide NPC"}


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def launch(port, token, disc, cfg, log, launcher, cwd, mode):
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    with Path(log).open("w") as fh:
        subprocess.run(["bash", str(launcher), "--execution-mode", mode,
                        "--config-dir", str(cfg), "--port", str(port), "--token", token,
                        "--disc", str(disc)], cwd=str(cwd), stdout=fh, stderr=fh,
                       check=False)
    text = Path(log).read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-800:])
    return text.split("pid=")[1].split()[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--save", type=Path, default=ROOT / "LEVEL11_5.sav")
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23790)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_f11_actor_census.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/f11-census")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {"row": "F11_the_tree", "question": "what objects exist in The Tree",
           "save": str(args.save.name),
           "method": ("walk chunk-31 exactly as the game's species dispatcher does: "
                      "actor = 0x8009FD80 + n*0x84, roster ptr at +0x80, species at "
                      "roster+0x0C")}
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(600)
        c.call("emulator.loadState", {"path": str(args.save), "pause_after_load": True})
        time.sleep(1.0)

        def rd(a, n):
            return bytes.fromhex(c.call("debugger.readMemory",
                                        {"address": "0x%08x" % a, "length": n})["hex"])

        out["scene_id"] = int.from_bytes(rd(0x80082504, 4), "little")
        actors = rd(ACTOR_BASE, STRIDE * SLOTS)
        rows_ = []
        for n in range(SLOTS):
            o = n * STRIDE
            rp = int.from_bytes(actors[o + ROSTER_PTR_OFF:o + ROSTER_PTR_OFF + 4], "little")
            if not (0x80000000 <= rp < 0x80200000):
                continue
            sp = rd(rp + SPECIES_OFF, 1)[0]
            if sp == 0:
                continue
            model = int.from_bytes(rd(MODEL_REGISTRY + 4 * sp, 4), "little") \
                if sp < 64 else 0
            rows_.append({
                "slot": n,
                "addr": "0x%08X" % (ACTOR_BASE + o),
                "species": sp,
                "known_as": KNOWN.get(sp),
                "hp": s16(int.from_bytes(actors[o + 0x6E:o + 0x70], "little")),
                "flags": int.from_bytes(actors[o + 0x5C:o + 0x5E], "little"),
                "vm_ip": "0x%08X" % int.from_bytes(actors[o + 0x70:o + 0x74], "little"),
                "callback": "0x%08X" % int.from_bytes(actors[o + 0x7C:o + 0x80], "little"),
                "model_entry": "0x%08X" % model,
            })
        out["actors"] = rows_
        hist = {}
        for r in rows_:
            hist[str(r["species"])] = hist.get(str(r["species"]), 0) + 1
        out["species_histogram"] = hist
        out["distinct_species"] = sorted({r["species"] for r in rows_})
        out["unidentified_species"] = sorted({r["species"] for r in rows_
                                              if r["species"] not in KNOWN})
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"scene_id": out.get("scene_id"),
                      "actor_count": len(out.get("actors", [])),
                      "species_histogram": out.get("species_histogram"),
                      "unidentified_species": out.get("unidentified_species")}, indent=1))
    for r in out.get("actors", []):
        print("  slot %2d %s sp=%-3d hp=%-5d flags=0x%04x vm=%s cb=%s %s"
              % (r["slot"], r["addr"], r["species"], r["hp"], r["flags"],
                 r["vm_ip"], r["callback"], r["known_as"] or ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
