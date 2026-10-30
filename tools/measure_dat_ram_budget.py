#!/usr/bin/env python3
"""Measure the REAL RAM headroom above LEVEL01's LEVEL.DAT buffer, live.

Everything in the terrain pipeline is bounded by how far LEVEL.DAT may grow. The disc half
of that question is settled (docs/G3_NATIVE_DAT_SIZE_CAP_TEST.md: LEVEL.RAW moves fine,
loading is by name). The RAM half was only ever an ARITHMETIC RECONSTRUCTION from a June
measurement plus a sentinel scan quoted as "0x801b4000". This measures it instead.

METHOD
  1. Cold-boot the pristine disc to LEVEL01 via the proven movie.
  2. Read DATbase = [0x80082498] and the parser's tail pointer [0x8008239c] -- so the buffer
     is located from the game's own state, never assumed.
  3. Fill everything from DAT end up to a ceiling with a sentinel pattern.
  4. Run real gameplay (walk + turn the camera -- the "busy view" that floods high RAM).
  5. Read back. The LOWEST sentinel word the game overwrote is the true headroom: the DAT
     cannot grow past it without being clobbered.

The sentinel write is deliberately destructive to free space only. If the guest wedges
immediately, that is itself the answer (the region is hot right above the DAT).

Usage: python3 tools/measure_dat_ram_budget.py [--disc CUE] [--ceiling 0x801F0000]
"""
from __future__ import annotations

import argparse, json, os, struct, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUCK = os.path.expanduser("~/duckstation")
sys.path.insert(0, os.path.join(DUCK, "scripts", "debugger-client"))

CFG   = "/tmp/dsbudget-probe"          # dedicated config dir -- never the operator's
PORT  = 23467                          # dedicated loopback port
TOKEN = "debugger-budget"
MOVIE = os.path.join(ROOT, "flik_to_level01_stall.mv.movie.json")
FORK_LAUNCHER  = os.path.join(DUCK, "scripts/debugger-client/launch_debugger_instance.sh")
REPRO_LAUNCHER = os.path.join(ROOT, "tools/launch_repro_playback.sh")

DATBASE_PTR = 0x80082498     # gp+0x700: destination heap pointer for the DAT load
TAILPTR     = 0x8008239c     # gp+0x604: fcn.8001cdc0 epilogue result
FLIK_X      = 0x800A6500
LEVEL01_X_MIN = 50000
DAT_SIZE    = 332824         # pristine LEVEL01/LEVEL.DAT
SENTINEL    = 0xA5C3
CHUNK       = 0x1000   # 4 KB: a 32 KB chunk becomes 64 KB of hex and resets the RPC


def connect():
    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", PORT, "ws")
    c.authenticate(TOKEN)
    try: c.transport.sock.settimeout(180)
    except Exception: pass
    return c


def rd(c, addr, n):
    return bytes.fromhex(c.call("debugger.readMemory",
                                {"address": "0x%08x" % addr, "length": n})["hex"])


def wr(c, addr, data: bytes):
    c.call("debugger.writeMemory", {"address": "0x%08x" % addr, "hex": data.hex()})


def u32(c, a):  return struct.unpack("<I", rd(c, a, 4))[0]
def s32(c, a):  return struct.unpack("<i", rd(c, a, 4))[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", default=os.path.join(ROOT, "Disney-Pixar A Bug's Life (v1.0).cue"))
    ap.add_argument("--ceiling", default="0x801F0000")
    ap.add_argument("--out", default=os.path.join(ROOT, "analysis/dat_ram_budget.json"))
    a = ap.parse_args()
    ceiling = int(a.ceiling, 16)
    if not os.path.exists(a.disc):
        sys.exit(f"disc not found: {a.disc}")

    subprocess.run([FORK_LAUNCHER, "stop", "--config-dir", CFG], capture_output=True)
    r = subprocess.run([REPRO_LAUNCHER, "--config-dir", CFG, "--port", str(PORT),
                        "--token", TOKEN, "--disc", a.disc], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"launch failed:\n{r.stdout}{r.stderr}")
    print(f"[budget] {r.stdout.strip()}")
    time.sleep(2)
    res = {"disc": os.path.basename(a.disc), "ceiling": hex(ceiling)}
    try:
        c = connect()
        media = c.call("emulator.getMediaInfo", {})
        res["media"] = media.get("path") or media
        print(f"[budget] media: {res['media']}")

        # --- boot to LEVEL01 -------------------------------------------------
        c.call("emulator.setTurbo", {"enabled": True})
        c.call("debugger.reset", {})
        c.call("movie.load", {"path": MOVIE})
        c.call("movie.startPlayback", {})
        for _ in range(75):
            if s32(c, FLIK_X) > LEVEL01_X_MIN:
                break
            c.call("emulator.advanceFrames", {"frames": 300})
        c.call("emulator.advanceFrames", {"frames": 8})
        try: c.call("movie.stopPlayback", {})
        except Exception: pass
        c.call("emulator.setTurbo", {"enabled": False})
        x = s32(c, FLIK_X)
        res["flik_x_at_level01"] = x
        if x <= LEVEL01_X_MIN:
            res["error"] = "never reached LEVEL01"
            raise SystemExit(json.dumps(res, indent=1))
        print(f"[budget] at LEVEL01, flik_x={x}")

        # --- locate the DAT buffer from the GAME'S OWN state -----------------
        datbase = u32(c, DATBASE_PTR)
        tailptr = u32(c, TAILPTR)
        out_end = datbase + DAT_SIZE
        res |= {"datbase": hex(datbase), "tail_ptr": hex(tailptr),
                "dat_size": DAT_SIZE, "dat_out_end": hex(out_end)}
        print(f"[budget] DATbase={datbase:#010x}  out_end={out_end:#010x}  tail_ptr={tailptr:#010x}")
        if not (0x80000000 <= datbase < 0x80200000):
            res["error"] = "DATbase not in main RAM"
            raise SystemExit(json.dumps(res, indent=1))

        lo = (out_end + 3) & ~3
        res["sentinel_lo"] = hex(lo)
        if lo >= ceiling:
            res["error"] = "DAT already reaches the ceiling"
            raise SystemExit(json.dumps(res, indent=1))

        # --- sentinel fill: addr-tagged so a survivor is unambiguous ---------
        n = ceiling - lo
        buf = bytearray()
        for off in range(0, n, 4):
            buf += struct.pack("<HH", (lo + off) & 0xFFFF, SENTINEL)
        for off in range(0, n, CHUNK):
            wr(c, lo + off, bytes(buf[off:off + CHUNK]))
        print(f"[budget] sentinel-filled {n} B ({lo:#010x}..{ceiling:#010x})")

        # --- escalating gameplay phases, monotonic watermark ------------------
        # The 2026-06-26 note claims a "busy view" floods every region 0x1b4000..0x1f8000.
        # A short burst near spawn saw only 2.2% disturbed. This runs progressively harder
        # phases and re-measures after each, so the answer is a CURVE: if the watermark
        # keeps descending toward 0x801b4000 the old claim holds; if it converges, it does not.
        def press(btn, frames):
            # ⚠️ emulator.pressButton with a CAPITALISED name, held in short bursts. An
            # earlier version used setControllerState with lowercase keys: it silently
            # no-opped, Flik never moved (flik_x identical across all 10 phases), and the
            # probe measured the same idle state ten times. Always assert motion.
            for _ in range(max(1, frames // 8)):
                c.call("emulator.pressButton", {"button": btn, "frames": 8, "port": 0,
                                                "release_after": False})
                c.call("emulator.advanceFrames", {"frames": 8})
            c.call("emulator.clearControllerState", {"port": 0})

        def scan(upto):
            """lowest clobbered addr in [lo, upto); None if clean. Only scans BELOW the
            current watermark -- everything above is already known dirty."""
            first, cnt = None, 0
            span = upto - lo
            for off in range(0, span, CHUNK):
                got = rd(c, lo + off, min(CHUNK, span - off))
                for k in range(0, len(got) - 3, 4):
                    tag, sen = struct.unpack_from("<HH", got, k)
                    if sen != SENTINEL or tag != ((lo + off + k) & 0xFFFF):
                        cnt += 1
                        if first is None:
                            first = lo + off + k
                if first is not None:
                    break          # lowest found in this chunk; nothing lower can exist
            return first, cnt

        PHASES = [
            ("settle",            [("Up", 30)]),
            ("turn_360_at_spawn", [("Left", 90), ("Right", 180), ("Left", 90)]),
            ("walk_north_far",    [("Up", 600)]),
            ("sweep_after_north", [("Left", 120), ("Right", 240), ("Left", 120)]),
            ("walk_east_far",     [("Right", 600)]),
            ("walk_south_far",    [("Down", 600)]),
            ("walk_west_far",     [("Left", 600)]),
            ("camera_look_L1",    [("L1", 180), ("Up", 120), ("L1", 180)]),
            ("jump_and_turn",     [("Cross", 20), ("Left", 150), ("Cross", 20), ("Right", 150)]),
            ("long_free_run",     [("Up", 900), ("Right", 450), ("Up", 900), ("Left", 450)]),
        ]
        water = ceiling
        curve = []
        c.call("emulator.setTurbo", {"enabled": True})
        for name, steps in PHASES:
            for btn, fr in steps:
                press(btn, fr)
            c.call("emulator.advanceFrames", {"frames": 30})
            first, cnt = scan(water)
            if first is not None:
                water = first
            fx = s32(c, FLIK_X)
            curve.append({"phase": name, "watermark": hex(water),
                          "headroom_bytes": water - out_end,
                          "headroom_sectors": round((water - out_end) / 2048, 2),
                          "flik_x": fx})
            print(f"[budget] {name:20} watermark={water:#010x}  "
                  f"headroom={water-out_end:7d} B ({(water-out_end)/2048:5.1f} sec)  x={fx}")
        c.call("emulator.setTurbo", {"enabled": False})
        res["phase_curve"] = curve
        xs = {p["flik_x"] for p in curve}
        res["flik_moved_during_session"] = len(xs) > 1
        if len(xs) <= 1:
            res["error"] = ("INVALID: Flik never moved -- input no-opped, so this measured "
                            "an idle state, not a busy view")
            print("[budget] *** INVALID: Flik never moved; input did not take effect ***")
        first_bad = None if water >= ceiling else water
        bad_count = sum(1 for _ in ())  # recomputed below over the full region
        full_bad = 0
        for off in range(0, n, CHUNK):
            got = rd(c, lo + off, min(CHUNK, n - off))
            for k in range(0, len(got) - 3, 4):
                tag, sen = struct.unpack_from("<HH", got, k)
                if sen != SENTINEL or tag != ((lo + off + k) & 0xFFFF):
                    full_bad += 1
        bad_count = full_bad
        res["sentinel_words_total"] = n // 4
        res["sentinel_words_clobbered"] = bad_count
        res["first_clobbered"] = hex(first_bad) if first_bad is not None else None
        head = (first_bad - out_end) if first_bad is not None else (ceiling - out_end)
        res["old_claim_flood_floor"] = "0x801b4000"
        res["old_claim_reproduced"] = first_bad is not None and first_bad <= 0x801b4000
        res["headroom_bytes"] = head
        res["headroom_sectors"] = round(head / 2048, 2)
        res["bounded_by"] = "observed write" if first_bad is not None else "probe ceiling (no write seen)"
        print(f"[budget] first clobbered: {res['first_clobbered']}  "
              f"({bad_count}/{n//4} words)")
        print(f"[budget] HEADROOM above DAT = {head} B = {res['headroom_sectors']} sectors "
              f"({res['bounded_by']})")
    finally:
        subprocess.run([FORK_LAUNCHER, "stop", "--config-dir", CFG], capture_output=True)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
