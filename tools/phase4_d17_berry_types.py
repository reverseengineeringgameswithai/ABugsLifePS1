#!/usr/bin/env python3
"""D17: which berry type is 127 and which is 128 -- by register capture at the hit.

`berry_tough_damage_dispatch` picks the damage from a berry-TYPE byte at
`projectile + 0x2C` (pool base 0x800B0D18, entries at +8, stride 0x38):

    0x80059068  slti v0,v0,100        ; *** targets with HP >= 100 are IMMUNE ***
    0x80059074  lbu v1,0x2C(s1)       ; the berry type
    0x8005907C  v1 == 12   -> -2
    0x8005908C  v1 == 0    -> -2
    0x80059094  v1 == 1    -> hp - 99
    0x800590A8  v1 == 127  -> -4
    0x800590B0  v1 == 128  -> -3
    default               -> -1

A data watch cannot answer which berry is which: the type is read from a pooled entry
that is reused, so "the most recent write" is not necessarily the entry that hit. But
`v1` is NOT clobbered between the load at 0x80059074 and the store at 0x800590E4 on any
of the arms, so a BREAKPOINT at 0x800590E4 reads the exact type for that hit, alongside
s2 (the target actor) and the resulting HP.

⚠️⚠️ THE BREAKPOINT ADDRESS MUST BE PHYSICAL (`addr & 0x1FFFFFFF`). Passing the KSEG0
form (0x800590E4) is accepted, reported `enabled: true`, and NEVER FIRES -- hit_count
stays 0 forever, in every regime. This is the same gotcha already documented for
`transferLog.resolve`. Measured side by side against a PC executing 2,079 times:
    virtual 0x8004c834 + debugger.resume       -> hit_count 0
    virtual 0x8004c834 + movie.advanceToFrame  -> hit_count 0
    physical 0x0004c834 + debugger.resume      -> hit_count 1  (halts correctly)

Halting breakpoints do not desync an Interpreter movie; they stop the core MID-FRAME,
which is fine here -- this reads registers at the halt, it does not compare RAM snapshots.

    tools/phase4_d17_berry_types.py --port 23720
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
DAMAGE_STORE = 0x800590E4
POOL_BASE, POOL_ENTRY0, POOL_STRIDE, TYPE_OFF = 0x800B0D18, 0x800B0D20, 0x38, 0x2C
IMMUNE_AT = 100


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
    ap.add_argument("--movie", type=Path,
                    default=ROOT / "movies/Phase4/Interpreter/D17_Goldberry.movie.json")
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23720)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--max-hits", type=int, default=120)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_d17_berry_types.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/d17-berry")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": "D17_bird",
        "question": "which berry type is 127 vs 128, by register capture at the hit",
        "movie": str(args.movie.relative_to(ROOT)),
        "method": ("breakpoint at PHYSICAL 0x000590E4 reading v1 (the berry type, not "
                   "clobbered between its load at 0x80059074 and this store) plus s2 (the "
                   "target actor). ⚠️ The KSEG0 form 0x800590E4 is accepted and NEVER "
                   "fires -- same gotcha as transferLog.resolve."),
        "damage_table_static": {"0": -2, "1": "hp-99", "12": -2, "127": -4, "128": -3,
                                "default": -1},
        "immunity_gate": ("0x80059068 slti v0,v0,100 -- a target whose HP is >= %d never "
                          "reaches the damage table at all" % IMMUNE_AT),
    }
    hits = []
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(1200)
        st = c.call("movie.load", {"path": str(args.movie)})
        out["frames"] = st.get("frame_count")
        c.call("movie.startPlayback", {"load_start_state": True})

        # a stale breakpoint makes addBreakpoint fail with -32006; clear first
        try:
            for bp in (c.call("debugger.listBreakpoints", {}) or {}).get("breakpoints", []):
                c.call("debugger.removeBreakpoint", {"address": bp.get("address")})
        except Exception:
            pass
        # PHYSICAL address -- the virtual form silently never fires
        c.call("debugger.addBreakpoint",
               {"address": "0x%08x" % (DAMAGE_STORE & 0x1FFFFFFF)})

        # ⚠️ This breakpoint is SPARSE -- it only fires when an enemy takes a hit, and
        # the bird fight starts ~3,900 frames into this movie (~65s of playback). An
        # inner wait of a few seconds times out before the first hit and looks exactly
        # like "breakpoints do not work". Poll against the OVERALL timeout instead.
        began = time.time()
        c.call("debugger.resume", {})
        while len(hits) < args.max_hits and time.time() - began < args.timeout:
            time.sleep(0.1)
            try:
                stt = c.call("debugger.status", {})
            except Exception:
                break
            if stt.get("running", True):
                continue
            pc = int(str(stt.get("pc", "0")), 16) & 0x1FFFFFFF
            if pc != (DAMAGE_STORE & 0x1FFFFFFF):
                # halted for some other reason -- keep going
                c.call("debugger.resume", {})
                continue
            hit = True
            try:
                regs = c.call("debugger.getRegisters").get("registers_hex", {})
                v1 = int(regs.get("v1", "0"), 16) & 0xFF
                v0 = s16(int(regs.get("v0", "0"), 16) & 0xFFFF)
                s2 = int(regs.get("s2", "0"), 16)
                s1 = int(regs.get("s1", "0"), 16)
                frame = c.call("movie.status", {}).get("playback_index")
            except Exception as exc:                      # noqa: BLE001
                out.setdefault("errors", []).append(str(exc)[:120])
                break
            hits.append({"f": frame, "berry_type": v1, "new_hp": v0,
                         "target_actor": "0x%08X" % s2,
                         "pool_entry": "0x%08X" % s1,
                         "entry_index": ((s1 - POOL_ENTRY0) // POOL_STRIDE)
                                        if s1 >= POOL_ENTRY0 else None})
            c.call("debugger.resume", {})
        out["final_playback_index"] = hits[-1]["f"] if hits else None
        try:
            out["breakpoint_state"] = c.call("debugger.listBreakpoints", {})
        except Exception:
            pass
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    out["hit_count"] = len(hits)
    out["hits"] = hits[:120]

    # group by target actor, then by type -> damage
    per_target = {}
    for h in hits:
        per_target.setdefault(h["target_actor"], []).append(h)
    out["targets"] = {k: {"hits": len(v),
                          "types": sorted({x["berry_type"] for x in v}),
                          "hp_track": [x["new_hp"] for x in v][:24]}
                      for k, v in per_target.items()}

    types = sorted({h["berry_type"] for h in hits})
    out["findings"] = {
        "berry_types_observed": types,
        "type_127_seen": 127 in types,
        "type_128_seen": 128 in types,
        "verdict": None,
    }
    # the bird is the target that takes -4 steps
    for tgt, v in per_target.items():
        deltas = [b["new_hp"] - a["new_hp"] for a, b in zip(v, v[1:])]
        if -4 in deltas:
            t4 = sorted({x["berry_type"] for x, d in zip(v[1:], deltas) if d == -4})
            t3 = sorted({x["berry_type"] for x, d in zip(v[1:], deltas) if d == -3})
            out["findings"]["verdict"] = (
                "target %s: -4 hits carry berry type(s) %s, -3 hits carry %s"
                % (tgt, t4, t3))
            out["findings"]["bird_actor"] = tgt
            break
    if out["findings"]["verdict"] is None and types:
        out["findings"]["verdict"] = (
            "no -4 staircase captured in this window; types seen: %s. The static table "
            "stands unconfirmed live." % types)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"hit_count": out["hit_count"],
                      "targets": out["targets"],
                      "findings": out["findings"]}, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
