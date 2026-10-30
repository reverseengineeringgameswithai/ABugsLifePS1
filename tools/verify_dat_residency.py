#!/usr/bin/env python3
"""Prove the GROWN LEVEL.DAT is the one actually resident in RAM.

The +22-sector growth test (docs/G3_NATIVE_DAT_GROWTH_RESULT.md) passed all four smoke
gates, but all three passing discs returned identical metrics, so the test could not
separate "grew and works" from "grew and was silently ignored". This settles it by
comparing guest RAM at DATbase against BOTH candidate files.

Decisive probe: offsets BEYOND the pristine length (332,824 B). Those bytes exist only in
the grown file, so a match there is proof the grown DAT was loaded whole.
"""
from __future__ import annotations
import json, os, struct, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUCK = os.path.expanduser("~/duckstation")
sys.path.insert(0, os.path.join(DUCK, "scripts", "debugger-client"))
CFG, PORT, TOKEN = "/tmp/dsresidency", 23469, "debugger-resid"
MOVIE = os.path.join(ROOT, "flik_to_level01_stall.mv.movie.json")
FORK = os.path.join(DUCK, "scripts/debugger-client/launch_debugger_instance.sh")
REPRO = os.path.join(ROOT, "tools/launch_repro_playback.sh")
DATBASE_PTR, FLIK_X, XMIN = 0x80082498, 0x800A6500, 50000

def main():
    disc  = sys.argv[1] if len(sys.argv) > 1 else "build/ABL_tailfix.cue"
    grown = sys.argv[2] if len(sys.argv) > 2 else "~/.claude/jobs/dd545f9b/tmp/LEVEL_tailfix.DAT"
    G = open(grown, "rb").read()
    P = open(os.path.join(ROOT, "REBUILD/files/LEVEL01/LEVEL.DAT"), "rb").read()
    subprocess.run([FORK, "stop", "--config-dir", CFG], capture_output=True)
    r = subprocess.run([REPRO, "--config-dir", CFG, "--port", str(PORT), "--token", TOKEN,
                        "--disc", os.path.join(ROOT, disc)], capture_output=True, text=True)
    if r.returncode: sys.exit(r.stdout + r.stderr)
    time.sleep(2)
    res = {"disc": disc, "grown_file": os.path.basename(grown),
           "grown_len": len(G), "pristine_len": len(P)}
    try:
        from duckstation_debug_client import DebuggerClient
        c = DebuggerClient("127.0.0.1", PORT, "ws"); c.authenticate(TOKEN)
        c.transport.sock.settimeout(300)
        rd = lambda a, n: bytes.fromhex(c.call("debugger.readMemory",
                {"address": "0x%08x" % a, "length": n})["hex"])
        c.call("emulator.setTurbo", {"enabled": True}); c.call("debugger.reset", {})
        c.call("movie.load", {"path": MOVIE}); c.call("movie.startPlayback", {})
        for _ in range(75):
            if struct.unpack("<i", rd(FLIK_X, 4))[0] > XMIN: break
            c.call("emulator.advanceFrames", {"frames": 300})
        c.call("emulator.advanceFrames", {"frames": 8})
        try: c.call("movie.stopPlayback", {})
        except Exception: pass
        c.call("emulator.setTurbo", {"enabled": False})
        base = struct.unpack("<I", rd(DATBASE_PTR, 4))[0]
        res["datbase"] = hex(base)
        probes = []
        for off in (0, 0x1000, 0x20000, 0x40000,
                    len(P) - 0x100, len(P) + 0x10, len(P) + 0x2000, len(G) - 0x100):
            if off < 0 or off + 64 > len(G): continue
            ram = rd(base + off, 64)
            probes.append({"offset": hex(off), "beyond_pristine": off >= len(P),
                           "matches_grown": ram == G[off:off+64],
                           "matches_pristine": (off + 64 <= len(P)) and ram == P[off:off+64]})
        res["probes"] = probes
        beyond = [p for p in probes if p["beyond_pristine"]]
        res["decisive_probes"] = len(beyond)
        res["grown_dat_is_resident"] = bool(beyond) and all(p["matches_grown"] for p in beyond)
        res["all_probes_match_grown"] = all(p["matches_grown"] for p in probes)
        for p in probes:
            print(f"  off {p['offset']:>9}  beyond_pristine={str(p['beyond_pristine']):5} "
                  f"grown={str(p['matches_grown']):5} pristine={p['matches_pristine']}")
        print(f"\nGROWN DAT RESIDENT: {res['grown_dat_is_resident']} "
              f"({res['decisive_probes']} decisive probes past the pristine length)")
    finally:
        subprocess.run([FORK, "stop", "--config-dir", CFG], capture_output=True)
    out = os.path.join(ROOT, "analysis/dat_residency_check.json")
    json.dump(res, open(out, "w"), indent=1); print("wrote", out)
if __name__ == "__main__": main()
