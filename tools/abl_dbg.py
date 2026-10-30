#!/usr/bin/env python3
"""ABL geometry RE driver over DuckStation external debugger.
Persistent home (tmp gets wiped). Run scripts with this dir on sys.path, e.g.:
    cd "$(git rev-parse --show-toplevel)/tools" && python3 -c "from abl_dbg import D; ..."

Config via environment (host-portable):
    DUCKSTATION_DIR   path to the DuckStation fork checkout (default: ~/duckstation)
    ABL_SAVESTATES    DuckStation savestate dir (default: ~/.local/share/duckstation/savestates)
"""
import sys, os, json, struct
_DUCK = os.environ.get("DUCKSTATION_DIR", os.path.expanduser("~/duckstation"))
sys.path.insert(0, os.path.join(_DUCK, "scripts", "debugger-client"))
SAVESTATES = os.environ.get(
    "ABL_SAVESTATES", os.path.expanduser("~/.local/share/duckstation/savestates"))
from duckstation_debug_client import DebuggerClient, find_token, RpcError  # noqa

def hexa(a): return a if isinstance(a, str) else ("0x%08x" % a)

class D:
    def __init__(self, host="127.0.0.1", port=2346):
        self.c = DebuggerClient(host, port, "ws")
        tok = find_token()
        if not tok: raise SystemExit("no token")
        self.c.authenticate(tok)
    def call(self, m, p=None): return self.c.call(m, p or {})
    def status(self): return self.call("debugger.status")
    def regs(self): return self.call("debugger.getRegisters").get("registers_hex", {})
    def rmem(self, a, n): return bytes.fromhex(self.call("debugger.readMemory", {"address": hexa(a), "length": n})["hex"])
    def wmem(self, a, data):
        if isinstance(data, (bytes, bytearray)): data = bytes(data).hex()
        return self.call("debugger.writeMemory", {"address": hexa(a), "hex": data})
    def ru32(self, a): return struct.unpack("<I", self.rmem(a, 4))[0]
    def rs32(self, a): return struct.unpack("<i", self.rmem(a, 4))[0]
    def wu32(self, a, v): return self.wmem(a, struct.pack("<I", v & 0xffffffff))
    def dis(self, a, n=12):
        r = self.call("debugger.disassemble", {"address": hexa(a), "count": n})
        return [(i["address"], i["bytes"], i["text"], i.get("branch_target")) for i in r["instructions"]]
    def pdis(self, a, n=12):
        for ad, b, t, bt in self.dis(a, n): print(f"  {ad}  {t}" + (f"   -> {bt}" if bt else ""))
    def load(self, path): return self.call("emulator.loadState", {"path": path, "pause_after_load": True})
    def press(self, button, frames=1, port=0, release=True):
        return self.call("emulator.pressButton", {"button": button, "frames": frames, "port": port, "release_after": release})
    def adv(self, frames=1): return self.call("emulator.advanceFrames", {"frames": frames})
    def cap(self, path): return self.call("emulator.captureFrame", {"path": path})

if __name__ == "__main__":
    print(json.dumps(D().status(), indent=2))
