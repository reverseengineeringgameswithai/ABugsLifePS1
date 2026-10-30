#!/usr/bin/env python3
"""Phase-3 WP4: classify every resident `jalr` — the indirect CALL sites.

`jr` sites were the jump tables. The 139 `jalr` sites are the other half of the
indirect-dispatch bound: calls through a function POINTER. What matters for a mod
is not that they exist but WHERE THE POINTER COMES FROM, because that determines
whether it can be redirected and what redirecting it would break:

  global_slot   the pointer is loaded from a fixed address (lui/addiu base).
                That address is a CALLBACK SLOT — a mod can install a handler by
                writing it, and the slot can be read live to see what is installed.
  struct_field  the pointer is loaded from a runtime base register at a fixed
                offset — i.e. it is a FUNCTION-POINTER FIELD of some record.
                The offset is reported, because that is a typed-record fact.
  call_result   the pointer came back from another call (v0) — a factory/vtable
                lookup; not statically resolvable here.
  unresolved    everything else, reported with its reason.

Then the global slots are RESOLVED LIVE across pristine anchors: reading a slot
tells you which handler the game actually installs, which no static read can.

Usage: python3 tools/phase3_jalr_callbacks.py [--port 23473]  (live part optional)
Output: analysis/phase3_jalr_callbacks.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         inspect_state_before_load,
                                         require_optional_live_args,
                                         verified_media_identity,
                                         write_live_evidence)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               inspect_state_before_load,
                                               require_optional_live_args,
                                               verified_media_identity,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
OUT = ROOT / "analysis" / "phase3_jalr_callbacks.json"
EXE_BASE = 0x8000F800
RAM_LO, RAM_HI = 0x80000000, 0x80200000

sys.path.insert(0, str(ROOT / "tools"))
from phase3_jr_tables import (find_function, find_lui, last_defs,  # noqa: E402
                              load_functions, load_symbols, s16, word)


def fixture_pin(*rels):
    out = {}
    for rel in rels:
        p = ROOT / rel
        if p.exists():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def classify_jalr(exe, pc, fstart):
    """Where does the called function pointer come from?"""
    reg = (word(exe, pc) >> 21) & 0x1F
    defs = last_defs(exe, fstart, pc)
    cur, seen = reg, set()
    for _ in range(8):
        if cur not in defs:
            return "unresolved", {"why": "the called register is never defined "
                                         "in this function (passed in as an arg?)"}
        va, i, _ = defs[cur]
        op, fn = i >> 26, i & 0x3F
        if op == 0x23:                                    # lw reg, imm(base)
            base, imm = (i >> 21) & 0x1F, s16(i & 0xFFFF)
            hi = find_lui(exe, fstart, va, base)
            if hi is not None:
                slot = hi + imm
                if RAM_LO <= slot <= RAM_HI:
                    return "global_slot", {"slot": f"0x{slot:08X}"}
                return "unresolved", {"why": f"slot 0x{slot:08X} outside RAM"}
            return "struct_field", {"offset": f"+0x{imm & 0xFFFF:X}"
                                    if imm >= 0 else f"-0x{-imm:X}",
                                    "base_register": base}
        if op == 0 and fn in (0x21, 0x25):                # move / addu
            rs, rt = (i >> 21) & 0x1F, (i >> 16) & 0x1F
            nxt = (rs or rt) if 0 in (rs, rt) else None
            if nxt is None or nxt in seen:
                return "unresolved", {"why": "pointer built by arithmetic"}
            seen.add(nxt)
            cur = nxt
            continue
        if cur == 2 and op == 0x03:                       # v0 from a jal
            return "call_result", {"from": f"0x{((i & 0x3FFFFFF) * 4) | 0x80000000:08X}"}
        if op in (0x0F, 0x09):
            return "unresolved", {"why": "pointer materialised as a constant"}
        return "unresolved", {"why": f"defined by opcode {op:#04x}"}
    return "unresolved", {"why": "move chain did not terminate"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(ap, optional=True)
    ap.add_argument("--no-live", action="store_true",
                    help="skip resolving the global slots on a running game")
    args = ap.parse_args()
    if not args.no_live:
        require_optional_live_args(args)

    exe = EXE.read_bytes()
    funcs = load_functions()
    syms = load_symbols()
    dmap = json.loads((ROOT / "analysis" / "phase3_dispatch_map.json").read_text())
    sites = [s for s in dmap["indirect_sites"]["sites"] if s["kind"] == "jalr"]

    rows = {}
    for site in sites:
        pc = int(site["pc"], 16)
        fn = find_function(funcs, pc)
        if fn is None:
            rows[site["pc"]] = {"class": "unresolved",
                                "why": "pc outside any censused function"}
            continue
        kind, detail = classify_jalr(exe, pc, fn[0])
        rows[site["pc"]] = {"class": kind, "function": site.get("function"),
                            **detail}

    slots = sorted({r["slot"] for r in rows.values() if r.get("slot")})
    struct_fields = Counter(r["offset"] for r in rows.values()
                            if r["class"] == "struct_field")

    # ---- LIVE: what handler is actually installed in each callback slot? -----
    installed = {}
    run_provenance = None
    if slots and not args.no_live:
        from duckstation_debug_client import DebuggerClient
        baseline = json.loads(
            (ROOT / "analysis" / "phase2_stage_baseline.json").read_text())
        anchor = baseline["stages"]["stage01_anthill"]["save"]
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(120)
        st = c.call("debugger.status", {})
        assert st.get("game_serial") == "SCUS-94288", st
        media_identity = verified_media_identity(c, st)
        state_inspection = inspect_state_before_load(
            c, ROOT / anchor, media_identity)
        loaded = c.call("emulator.loadState",
                        {"path": str(ROOT / anchor), "pause_after_load": True})
        assert loaded.get("loaded") and loaded.get("game_serial") == "SCUS-94288", loaded
        c.call("emulator.advanceFrames", {"frames": 10})
        for slot in slots:
            a = int(slot, 16)
            raw = bytes.fromhex(c.call("debugger.readMemory",
                                       {"address": slot, "length": 4})["hex"])
            v = struct.unpack("<I", raw)[0]
            f = find_function(funcs, v) if RAM_LO <= v < RAM_HI else None
            installed[slot] = {
                "value": f"0x{v:08X}",
                "handler": (f[2].get("name") or syms.get(f[0])) if f else None,
                "is_code": bool(f and f[2].get("range_type") in ("code", "thunk")),
            }

    # Static refresh must not destroy the live half of the shared evidence.
    # A clean checkout carries the banked run; --no-live recomputes every static
    # classification and preserves that run only when it covers this exact slot
    # universe and pristine executable pin.  Missing/stale live evidence is a
    # hard failure, never silently replaced by an empty dictionary.
    if args.no_live:
        try:
            retained = json.loads(OUT.read_text())
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise SystemExit(
                "--no-live requires the retained hash-pinned live JALR artifact; "
                "run the isolated live command first") from exc
        retained_slots = retained.get("global_callback_slots") or []
        retained_installed = retained.get("installed_handlers") or {}
        retained_run = retained.get("run_provenance")
        retained_pin = (retained.get("fixture_sha256") or {}).get(
            "REBUILD/files/SCUS_942.88")
        current_pin = fixture_pin("REBUILD/files/SCUS_942.88").get(
            "REBUILD/files/SCUS_942.88")
        if retained_slots != slots or set(retained_installed) != set(slots):
            raise SystemExit(
                "retained live JALR evidence does not cover the recomputed callback slots")
        if not isinstance(retained_run, dict) or retained_pin != current_pin:
            raise SystemExit(
                "retained live JALR provenance/pin is absent or stale; rerun live")
        installed = retained_installed
        run_provenance = retained_run

    counts = Counter(r["class"] for r in rows.values())
    if not args.no_live:
        run_provenance = finish_run(
            args, generator="tools/phase3_jalr_callbacks.py",
            anchor={"save": anchor, "fixture_sha256": fixture_pin(anchor),
                    "state_inspections": [state_inspection],
                    "media_identity": media_identity},
            timing={"settle_frames": 10, "callback_slots": len(slots)},
        )
    doc = {
        "_comment": "Phase-3 WP4: every resident `jalr` (indirect CALL) classified by "
                    "WHERE THE FUNCTION POINTER COMES FROM — a global callback slot "
                    "(installable/redirectable, and resolved LIVE here to show what "
                    "the game actually installs), a struct FIELD (a function-pointer "
                    "field of some record — a typed-record fact), a call result "
                    "(factory/vtable), or unresolved with a reason. "
                    "CAVEAT: slots holding NULL at this anchor are NOT thereby "
                    "'free hooks' — whether the call site guards against NULL is "
                    "UNVERIFIED, and several slots (trapIntrVSync, def_cbsync, "
                    "def_cbread) run in INTERRUPT CONTEXT, where a handler must be "
                    "interrupt-safe. Handlers are read at ONE anchor and may differ "
                    "per scene. Regenerate: tools/phase3_jalr_callbacks.py",
        "run_provenance": run_provenance,
        "fixture_sha256": fixture_pin("REBUILD/files/SCUS_942.88"),
        "jalr_sites": len(sites),
        "classification": dict(counts),
        "global_callback_slots": slots,
        "installed_handlers": installed,
        "struct_field_offsets": {k: v for k, v in struct_fields.most_common()},
        "sites": rows,
    }
    write_live_evidence(OUT, doc)
    print(f"[jalr] {len(sites)} indirect call sites: {dict(counts)}")
    print(f"[jalr] {len(slots)} distinct global callback slots")
    for slot, inf in list(installed.items())[:8]:
        if slot.startswith("_"):
            print(f"    live resolve failed: {inf}")
            break
        print(f"    {slot} -> {inf['value']} {inf['handler'] or '(not code)'}")
    if struct_fields:
        print(f"[jalr] function-pointer FIELDS seen: "
              f"{dict(struct_fields.most_common(6))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
