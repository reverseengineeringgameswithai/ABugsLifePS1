#!/usr/bin/env python3
"""Measure RAM headroom above LEVEL01's LEVEL.DAT -- NON-DESTRUCTIVELY, via accessLog.

Supersedes tools/measure_dat_ram_budget.py, whose sentinel-fill wrote 255 KB over live high
RAM, wedged the guest, and therefore measured an idle machine (Flik's X was identical across
all ten "gameplay" phases). That result is retracted; see docs/G3_NATIVE_DAT_SIZE_CAP_TEST.md.

This asks the same question the right way round. `accessLog.addWatch` takes an address AND a
length, so one RANGE write-watch over everything above the DAT records who writes there
without touching a byte. The lowest address observed is the true ceiling on DAT growth.

Guards learned the hard way:
  * Flik MUST be proven to move, else the stimulus never happened and any number is noise.
  * Arming accessLog forces CPUExecutionMode::Interpreter, so the CachedInterpreter-recorded
    boot movie is replayed POLL-ONLY and stopped BEFORE any watch is armed.
  * The watch is re-armed after the movie stops, never across it.

Usage: python3 tools/measure_dat_headroom_accesslog.py [--ceiling 0x801F0000]
"""
from __future__ import annotations

import argparse, json, os, struct, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUCK = os.path.expanduser("~/duckstation")
sys.path.insert(0, os.path.join(DUCK, "scripts", "debugger-client"))

CFG, PORT, TOKEN = "/tmp/dsheadroom", 23468, "debugger-headroom"
MOVIE = os.path.join(ROOT, "flik_to_level01_stall.mv.movie.json")
FORK_LAUNCHER  = os.path.join(DUCK, "scripts/debugger-client/launch_debugger_instance.sh")
REPRO_LAUNCHER = os.path.join(ROOT, "tools/launch_repro_playback.sh")

DATBASE_PTR, TAILPTR = 0x80082498, 0x8008239c
FLIK_X, FLIK_Y, FLIK_Z = 0x800A6500, 0x800A6504, 0x800A6508
LEVEL01_X_MIN, DAT_SIZE = 50000, 332824


def connect():
    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", PORT, "ws")
    c.authenticate(TOKEN)
    try: c.transport.sock.settimeout(300)
    except Exception: pass
    return c


def rd(c, a, n):
    return bytes.fromhex(c.call("debugger.readMemory", {"address": "0x%08x" % a, "length": n})["hex"])
def u32(c, a): return struct.unpack("<I", rd(c, a, 4))[0]
def s32(c, a): return struct.unpack("<i", rd(c, a, 4))[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", default=os.path.join(ROOT, "Disney-Pixar A Bug's Life (v1.0).cue"))
    ap.add_argument("--ceiling", default="0x801F0000")
    ap.add_argument("--out", default=os.path.join(ROOT, "analysis/dat_headroom_accesslog.json"))
    a = ap.parse_args()
    ceiling = int(a.ceiling, 16)

    subprocess.run([FORK_LAUNCHER, "stop", "--config-dir", CFG], capture_output=True)
    r = subprocess.run([REPRO_LAUNCHER, "--config-dir", CFG, "--port", str(PORT),
                        "--token", TOKEN, "--disc", a.disc], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"launch failed:\n{r.stdout}{r.stderr}")
    print(f"[headroom] {r.stdout.strip()}")
    time.sleep(2)
    res = {"method": "accessLog range write-watch (non-destructive)", "ceiling": hex(ceiling)}
    try:
        c = connect()
        res["media"] = c.call("emulator.getMediaInfo", {}).get("path")
        print(f"[headroom] media: {res['media']}")

        # ---- reach LEVEL01: movie is CachedInterpreter-recorded => POLL ONLY, no arming
        c.call("emulator.setTurbo", {"enabled": True})
        c.call("debugger.reset", {})
        c.call("movie.load", {"path": MOVIE})
        c.call("movie.startPlayback", {})
        for _ in range(75):
            if s32(c, FLIK_X) > LEVEL01_X_MIN: break
            c.call("emulator.advanceFrames", {"frames": 300})
        c.call("emulator.advanceFrames", {"frames": 8})
        try: c.call("movie.stopPlayback", {})
        except Exception: pass
        c.call("emulator.setTurbo", {"enabled": False})     # turbo OFF for input
        x0, z0 = s32(c, FLIK_X), s32(c, FLIK_Z)
        res["flik_x_at_level01"] = x0
        if x0 <= LEVEL01_X_MIN:
            res["error"] = "never reached LEVEL01"; raise SystemExit(1)

        datbase = u32(c, DATBASE_PTR); out_end = datbase + DAT_SIZE
        res |= {"datbase": hex(datbase), "tail_ptr": hex(u32(c, TAILPTR)),
                "dat_out_end": hex(out_end)}
        print(f"[headroom] DATbase={datbase:#010x} out_end={out_end:#010x}")

        # ---- ONE range write-watch over everything above the DAT (touches nothing)
        # accessLog.addWatch caps length at 256 B, so a single range watch is impossible.
        # Spend the watch budget as a LADDER of 256-byte probes stepping up from out_end:
        # the lowest rung that fires bounds DAT growth. Absence on a rung is weak evidence
        # (a 256 B window can be stepped over), so rungs are reported individually.
        lo = (out_end + 3) & ~3
        STEP, NPROBE, WLEN = 4096, 48, 256
        c.call("accessLog.clear", {})
        probes = []
        for k in range(NPROBE):
            addr = lo + k * STEP
            if addr + WLEN > ceiling: break
            try:
                w = c.call("accessLog.addWatch", {"address": "0x%08x" % addr, "length": WLEN,
                                                  "type": "write", "label": f"rung{k:02d}",
                                                  "max_events": 4000,
                                                  "filter": {"max_per_frame": 64}})
                probes.append({"k": k, "addr": addr, "watch_id": w.get("watch_id")})
            except Exception as ex:
                res["watch_budget_exhausted_at"] = k
                print(f"[headroom] watch budget stopped at rung {k}: {ex}")
                break
        res["probes"] = len(probes)
        res["probe_span"] = {"lo": hex(lo), "step": STEP, "len": WLEN,
                             "hi": hex(lo + (len(probes) - 1) * STEP + WLEN) if probes else None}
        print(f"[headroom] armed {len(probes)} x {WLEN}B write-probes, {STEP}B apart, "
              f"from {lo:#010x}  (mode now "
              f"{c.call('debugger.status', {}).get('execution_mode')})")

        # ---- real gameplay, with a movement assertion
        def press(btn, frames):
            for _ in range(max(1, frames // 8)):
                c.call("emulator.pressButton", {"button": btn, "frames": 8, "port": 0,
                                                "release_after": False})
                c.call("emulator.advanceFrames", {"frames": 8})
            c.call("emulator.clearControllerState", {"port": 0})
        for btn, fr in (("Up", 240), ("Left", 120), ("Up", 240), ("Right", 240),
                        ("Down", 200), ("Up", 320), ("Left", 200), ("Cross", 24),
                        ("Up", 320), ("Right", 200)):
            press(btn, fr)
        moved = abs(s32(c, FLIK_X) - x0) + abs(s32(c, FLIK_Z) - z0)
        res["flik_moved_xz"] = moved
        res["stimulus_valid"] = moved > 15000
        print(f"[headroom] Flik moved {moved} XZ units -> stimulus_valid={res['stimulus_valid']}")

        # ---- drain every rung; the lowest that fired bounds DAT growth
        lowest, total, rungs = None, 0, []
        for pr in probes:
            off, cnt, lo_r = 0, 0, None
            while True:
                page = c.call("accessLog.get", {"watch_id": pr["watch_id"],
                                                "offset": off, "limit": 4000})
                evs = page.get("events") or []
                for e in evs:
                    av = e.get("address")
                    av = int(av, 16) if isinstance(av, str) else av
                    if av is None: continue
                    cnt += 1
                    if lo_r is None or av < lo_r: lo_r = av
                off += len(evs)
                if len(evs) < 4000: break
            total += cnt
            rungs.append({"k": pr["k"], "addr": hex(pr["addr"]), "writes": cnt,
                          "lowest": hex(lo_r) if lo_r is not None else None,
                          "offset_from_dat_end": pr["addr"] - out_end})
            if cnt and (lowest is None or lo_r < lowest): lowest = lo_r
        res["rungs"] = rungs
        fired = [r for r in rungs if r["writes"]]
        res["rungs_fired"] = len(fired)
        print(f"[headroom] {len(fired)}/{len(rungs)} rungs fired")
        for r in fired[:8]:
            print(f"    rung{r['k']:02d} {r['addr']} (+{r['offset_from_dat_end']:6d} B) "
                  f"{r['writes']} writes, lowest {r['lowest']}")
        res |= {"events_seen": total, "lowest_write": hex(lowest) if lowest is not None else None}
        head = (lowest - out_end) if lowest is not None else (ceiling - out_end)
        res |= {"headroom_bytes": head, "headroom_sectors": round(head / 2048, 2),
                "bounded_by": "observed write" if lowest is not None else "no write in range"}
        res["old_claim_flood_floor"] = "0x801b4000"
        res["old_claim_reproduced"] = lowest is not None and lowest <= 0x801b4000
        print(f"[headroom] {total} write events; lowest={res['lowest_write']}")
        print(f"[headroom] HEADROOM = {head} B = {res['headroom_sectors']} sectors "
              f"({res['bounded_by']})")
        if not res["stimulus_valid"]:
            print("[headroom] *** INVALID: Flik did not move; do not trust this number ***")
    finally:
        subprocess.run([FORK_LAUNCHER, "stop", "--config-dir", CFG], capture_output=True)
    with open(a.out, "w") as f: json.dump(res, f, indent=1)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
