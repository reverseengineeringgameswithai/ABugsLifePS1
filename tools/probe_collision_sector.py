#!/usr/bin/env python3
"""LIVE probe: find the collision sector the resolver SELECTS as Flik's floor (§2.1).

The collision resolver (FUNC_800345CC) does NOT simply pick the nearest sector by origin
XZ — at spawn, offline XZ-proximity picks the WRONG sector. This drives the running game
to settle Flik at a spot, then perturbs each candidate sector's runtime origin-Y
(0x800A7E48 + i*0x30 + 4) one at a time (no-drift via save/loadState) and watches which
poke moves Flik's Y. That sector is his actual floor — the one to edit for a LOCALIZED
matched bump (paired with sculpt_terrain.py over the same spot; calibration is 1:1 in
src/node units, since terrain node-frame == runtime>>5 == collision src-frame).

Requires the isolated debugger instance running on the PRISTINE disc (so the probe reads
true floors). NOT CI-safe (live emulator). Example:
  python3 tools/probe_collision_sector.py --port 23461 --token cc5-token \
      --walk "up:3:40" --walk "up:8:12"
"""
from __future__ import annotations

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.expanduser(os.environ.get("DUCKSTATION_DIR", "~/duckstation")
                                      .replace("~", os.path.expanduser("~")) + "/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

TBL = 0x800A7E48
FLIK = 0x800a6500
MOVIE = "flik_to_level01_stall.mv.movie.json"
N_CHUNK32_SECTORS = 189


def main() -> int:
    ap = argparse.ArgumentParser(description="Find the collision sector under Flik (live poke-probe).")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--movie", default=MOVIE, help="from-boot movie to reach LEVEL01")
    ap.add_argument("--movie-frames", type=int, default=6470)
    ap.add_argument("--walk", action="append", default=[], metavar="BTN:HOLD:IDLE",
                    help="after reaching LEVEL01, hold BTN for HOLD frames then idle IDLE; may repeat")
    ap.add_argument("--candidates", type=int, default=10, help="how many nearest-XZ sectors to test")
    ap.add_argument("--poke", type=int, default=-6000, help="runtime origin-Y perturbation for the probe")
    ap.add_argument("--state", default="/tmp/probe_collision.sav", help="scratch save-state path")
    args = ap.parse_args()

    c = DebuggerClient(args.host, args.port, "ws"); c.authenticate(args.token)
    c.transport.sock.settimeout(180)
    def call(m, p=None): return c.call(m, p or {})
    def rmem(a, n): return bytes.fromhex(call("debugger.readMemory", {"address": "0x%08x" % a, "length": n})["hex"])
    def w32(a, v): call("debugger.writeMemory", {"address": "0x%08x" % a, "hex": struct.pack("<i", v).hex()})
    def flik(): return struct.unpack("<iii", rmem(FLIK, 12))
    def origY(s): return struct.unpack_from("<i", rmem(TBL + s * 0x30 + 4, 4), 0)[0]

    # clear any stale playback/recording left by a previous run
    for m in ("movie.stopPlayback", "movie.stopRecording"):
        try:
            call(m)
        except Exception:
            pass
    call("movie.load", {"path": os.path.abspath(args.movie)})
    call("movie.startPlayback", {"start_frame": 0, "load_start_state": True})
    done = 0
    while done < args.movie_frames:
        n = min(500, args.movie_frames - done); call("emulator.advanceFrames", {"frames": n}); done += n
    # unpause (movie ends in start-menu pause)
    call("emulator.clearControllerState", {"port": 0})
    call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}}); call("emulator.advanceFrames", {"frames": 4})
    call("emulator.clearControllerState", {"port": 0}); call("emulator.advanceFrames", {"frames": 20})

    walk_steps = []
    for spec in args.walk:
        btn, hold, idle = spec.split(":"); walk_steps.append((btn, int(hold), int(idle)))

    def do_walk():
        for btn, hold, idle in walk_steps:
            call("emulator.setControllerState", {"port": 0, "buttons": {btn: True}})
            call("emulator.advanceFrames", {"frames": hold})
            call("emulator.clearControllerState", {"port": 0})
            call("emulator.advanceFrames", {"frames": idle})

    do_walk()
    fx, fy, fz = flik()
    print(f"Flik settled at X={fx} Y={fy} Z={fz}")

    # Sector origins are reference points (NOT spatial centers), so XZ-proximity is unreliable
    # (it misses the true floor). BINARY-SEARCH all chunk-32 sectors instead: poke a whole
    # group's origin-Y, nudge, and see if Flik moved — exactly one sector is his floor, so the
    # group containing it is the one that moves him. ~log2(189) ≈ 8 settle cycles.
    call("emulator.saveState", {"path": args.state})

    def nudge_one():
        call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
        call("emulator.advanceFrames", {"frames": 8})
        call("emulator.clearControllerState", {"port": 0})
        call("emulator.advanceFrames", {"frames": 12})

    def poke_group(group, delta):
        # scatterWrite is capped ~24/call -> chunk it
        writes = [{"address": "0x%08x" % (TBL + s * 0x30 + 4), "type": "u32",
                   "value": (origY(s) + delta) & 0xffffffff} for s in group]
        for k in range(0, len(writes), 20):
            call("debugger.scatterWrite", {"writes": writes[k:k + 20], "atomic": True})

    def moved_if_poked(group):
        call("emulator.loadState", {"path": args.state, "pause_after_load": True})
        poke_group(group, args.poke)
        nudge_one()
        return abs(flik()[1] - ctrl) > abs(args.poke) // 4

    call("emulator.loadState", {"path": args.state, "pause_after_load": True})
    nudge_one(); ctrl = flik()[1]
    print(f"control floor (no poke) Y={ctrl}")
    lo, hi = 0, N_CHUNK32_SECTORS
    if not moved_if_poked(list(range(lo, hi))):
        print("\nNo chunk-32 sector moves Flik here (floor may be in chunk 33, sectors 189..222).")
        return 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if moved_if_poked(list(range(lo, mid))):
            hi = mid
        else:
            lo = mid
        print(f"  narrowed to sectors [{lo},{hi})")
    selected = lo
    print(f"\nSELECTED collision sector under Flik = {selected}")
    print("→ edit it with: tools/edit_collision_sector.py --sector %s --src-delta-y <D>" % selected)
    print("  (pair with sculpt_terrain.py over the same spot, same D — 1:1 in src/node units)")
    return 0 if selected is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
