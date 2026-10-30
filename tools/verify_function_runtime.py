#!/usr/bin/env python3
"""Runtime verification of a resident function via the DuckStation debugger API.

Campaign v3 (6E): confirm a decompiled/named function's IDENTITY and I/O at runtime,
complementing the SHA-1 byte-match (which proves byte-identity but not behaviour
understanding). Three checks, all read-mostly except `call`:

  bounds  debugger.functionBounds  — extent + confidence (trust "exact" only)
          debugger.xrefsTo         — callers (compare to the census call-graph)
  call    debugger.callFunction {address,a0..a3} — invoke the guest subroutine
          directly (pause first), report v0/v1/return/status, optional memory read-back.

callFunction GOTCHAS (see .claude/skills/duckstation-external-debugger): the guest MUST
be paused; it really RUNS the function (mutates state/VRAM) — use a THROWAWAY isolated
instance, never the operator's own; if control halts elsewhere it returns
reason:"stopped_elsewhere". Set the socket timeout; relaunch between side-effecting calls.

  python3 tools/verify_function_runtime.py --port 23460 --token debugger-1000 bounds 0x80060154
  python3 tools/verify_function_runtime.py --port 23460 --token debugger-1000 \
        call 0x80060154 --a0 0x10000 --read 0x800a6500:16
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _client(port: int, token: str, timeout: int):
    sys.path.insert(0, str(Path.home() / "duckstation" / "scripts" / "debugger-client"))
    from duckstation_debug_client import DebuggerClient  # noqa: E402
    c = DebuggerClient("127.0.0.1", port, "ws")
    c.authenticate(token)
    c.transport.sock.settimeout(timeout)
    st = c.call("debugger.status", {})
    if st.get("game_serial") != "SCUS-94288":
        raise SystemExit(f"wrong/no game: {st.get('game_serial')}")
    return c


def _u32(s: str) -> int:
    return int(s, 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=23460)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=int, default=30)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bounds"); b.add_argument("address")
    c = sub.add_parser("call")
    c.add_argument("address")
    for r in ("a0", "a1", "a2", "a3"):
        c.add_argument(f"--{r}", default=None)
    c.add_argument("--read", default=None, help="ADDR:LEN to read back after the call")
    c.add_argument("--call-timeout", type=int, default=5000)
    args = ap.parse_args()

    conn = _client(args.port, args.token, args.timeout)
    addr = _u32(args.address)

    if args.cmd == "bounds":
        fb = conn.call("debugger.functionBounds", {"address": f"{addr:#x}"})
        print(f"functionBounds {addr:#010x}: start={fb.get('functionStart')} end={fb.get('functionEnd')} "
              f"span={fb.get('spanBytes')} confidence={fb.get('confidence')} "
              f"merged={fb.get('mergedRegion')} cleanEnd={fb.get('cleanEnd')}")
        xr = conn.call("debugger.xrefsTo", {"address": f"{addr:#x}"})
        callers = xr.get("callers") or xr.get("xrefs") or xr.get("results") or []
        print(f"xrefsTo: {len(callers)} caller(s): {callers[:12]}")
        return 0

    if args.cmd == "call":
        conn.call("debugger.pause", {})
        params = {"address": f"{addr:#x}", "timeout": args.call_timeout}
        for r in ("a0", "a1", "a2", "a3"):
            v = getattr(args, r)
            if v is not None:
                params[r] = _u32(v)
        r = conn.call("debugger.callFunction", params)
        print(f"callFunction {addr:#010x} "
              f"a0={params.get('a0')} a1={params.get('a1')} a2={params.get('a2')} a3={params.get('a3')}")
        print(f"  -> v0={r.get('v0_hex') or r.get('v0')} v1={r.get('v1')} "
              f"return={r.get('return_address')} stopped_at={r.get('stopped_at')} status={r.get('status')}")
        if args.read:
            a, _, n = args.read.partition(":")
            mm = conn.call("debugger.readMemory", {"address": a, "length": int(n)})
            print(f"  read {a}:{n} = {mm.get('hex')}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
