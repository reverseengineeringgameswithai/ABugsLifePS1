#!/usr/bin/env python3
"""Step 3 helper: connect to the isolated DuckStation, load a LEVEL01 spawn
state (ABL_SPAWN_SAV), and expose the debugger client for tpage/VRAM work."""
import os
import sys
import struct

sys.path.insert(0, os.path.expanduser("~/duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa
from _env import ABL_SAVESTATES  # noqa: F401  (kept for interactive use)

PORT = 23460
TOKEN = "debugger-1000"
# Numbered-slot fixtures were retired 2026-07-08; name the state explicitly.
SAV = os.environ.get("ABL_SPAWN_SAV", "")


def connect():
    c = DebuggerClient("127.0.0.1", PORT, "ws")
    c.authenticate(TOKEN)
    try:
        c.transport.sock.settimeout(30)
    except Exception as e:  # noqa
        print("settimeout warn:", e)
    return c


def ru32(c, addr):
    m = c.call("debugger.readMemory", {"address": addr if isinstance(addr, str) else "0x%08x" % addr,
                                       "length": 4})
    return struct.unpack("<I", bytes.fromhex(m["hex"]))[0]


if __name__ == "__main__":
    if not SAV:
        sys.exit("_step3: set ABL_SPAWN_SAV to a LEVEL01 spawn .sav "
                 "(numbered-slot fixtures retired 2026-07-08)")
    c = connect()
    print("loadState...")
    r = c.call("emulator.loadState", {"path": SAV, "pause_after_load": True})
    print("loadState ->", r)
    c.call("emulator.advanceFrames", {"frames": 2})
    datbase = ru32(c, 0x80082498)
    fx, fy, fz = (struct.unpack("<i", bytes.fromhex(
        c.call("debugger.readMemory", {"address": "0x%08x" % a, "length": 4})["hex"]))[0]
        for a in (0x800A6500, 0x800A6504, 0x800A6508))
    print(f"DATbase=0x{datbase:08x} (want 0x801607f8)  Flik=({fx},{fy},{fz})")
    print("status:", c.call("debugger.status"))
