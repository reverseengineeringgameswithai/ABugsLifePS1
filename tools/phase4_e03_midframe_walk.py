#!/usr/bin/env python3
"""Phase-4 E03: mid-frame OT snapshot + same-frame gp0Trace cross-check driver.

Discovered structure (this row): each rendered frame PRESENTS A SEQUENCE OF
LINKED LISTS through one DMA-kick helper call site (0x80064F28), with the list
head in a1 at the call:
  kick 0: the 7-command env preamble node (buffer_base+0x1C; its terminator is
          real -- env is its own list, never linked into the body chain),
  kick 1: the depth-bucket chain (the frame's whole draw list),
  kicks 2+: scene-dependent auxiliary lists (scratchpad 0x1F8010F0-built,
          stack-built) contributing no GP0 draw commands in traced frames.

This driver halts at kick 0 and kick 1, records a1 for both, dumps 2 MiB RAM at
kick 1 (body chain complete, not yet presented), then arms gp0Trace and
advances past the present to fetch the dispatch-time stream of the same frame.
tools/phase4_e03_ot_walk.c walks the dump from the kick-1 head;
tools/phase4_e03_crosscheck.py diffs walker vs trace (minus the 7 env cmds).

Usage: python3 tools/phase4_e03_midframe_walk.py --port 23701 --save level02.sav \
           --label normal_gameplay --out-dir <scratch>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
sys.path.insert(0, str(ROOT / "tools"))

from live_session_provenance import (inspect_state_before_load,
                                     verified_media_identity)

PRESENT_PC = 0x80064F28


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=23701)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--save", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--settle", type=int, default=30)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    outdir = Path(args.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(60)

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)

    path = ROOT / args.save
    inspect_state_before_load(c, path, media_identity)
    r = c.call("emulator.loadState", {"path": str(path), "pause_after_load": True})
    assert r.get("loaded"), r
    c.call("emulator.advanceFrames", {"frames": args.settle})

    for old in c.call("debugger.listBreakpoints", {}).get("breakpoints", []):
        c.call("debugger.removeBreakpoint", {"id": old["id"]})
    bp = c.call("debugger.addBreakpoint", {"address": "0x%08x" % PRESENT_PC,
                                           "type": "execute"})

    def resume_to_hit():
        c.call("debugger.resume", {})
        for _ in range(400):
            st = c.call("debugger.status", {})
            if st.get("paused"):
                return c.call("debugger.getRegisters", {}).get("registers_hex", {})
            time.sleep(0.02)
        raise SystemExit("breakpoint never hit")

    regs0 = resume_to_hit()          # kick 0: env list
    regs1 = resume_to_hit()          # kick 1: body (bucket-chain) list

    dump = outdir / f"{args.label}_midframe_ram.bin"
    with dump.open("wb") as fh:
        for base in range(0x80000000, 0x80200000, 0x10000):
            fh.write(bytes.fromhex(c.call(
                "debugger.readMemory",
                {"address": "0x%08x" % base, "length": 0x10000})["hex"]))

    c.call("gp0Trace.start", {"max_entries": 65536, "max_params": 16})
    c.call("gp0Trace.clear", {})
    c.call("debugger.removeBreakpoint", {"id": bp["id"]})
    c.call("emulator.advanceFrames", {"frames": 2})

    entries, off = [], 0
    while True:
        page = c.call("gp0Trace.get", {"offset": off, "limit": 4096})
        entries.extend(page["entries"])
        off += page["count"]
        if off >= page["total"] or page["count"] == 0:
            break
    c.call("gp0Trace.stop", {})

    meta = {
        "label": args.label, "save": args.save,
        "save_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "present_pc": f"0x{PRESENT_PC:08x}",
        "env_list_head_a1": regs0.get("a1"),
        "body_list_head_a1": regs1.get("a1"),
        "kick0_registers": regs0,
        "kick1_registers": regs1,
        "ram_dump": str(dump),
        "ram_dump_sha256": hashlib.sha256(dump.read_bytes()).hexdigest(),
        "trace_total": len(entries),
        "trace_entries": entries,
    }
    out = outdir / f"{args.label}_midframe.json"
    out.write_text(json.dumps(meta, indent=1) + "\n")
    print(f"env_head={regs0.get('a1')} body_head={regs1.get('a1')} "
          f"trace={len(entries)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
