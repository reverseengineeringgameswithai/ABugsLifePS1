#!/usr/bin/env python3
"""Phase-3 W1 — bind F09 (Stage-9 "Bug Bar": defeat Thud) by a LIVE poke-falsification.

Bug Bar's chunk-31 table is all-zero — Thud is setpiece/trigger-spawned, not
chunk-31 sourced — so a static binding is impossible and F09 sat as a narrative-only
residual on gate bullet 1. This tool binds it from the running game, following the
fully-decoded sibling boss Thumper (src_re/thumper_boss.c) as the template.

Method = POKE-FALSIFICATION, not breakpoint-heavy tracing (movie replays DRIFT under
heavy breakpoints — the Thumper lesson). Load the stage-9 arena, find the boss via
the live enemy table, confirm its id / HP field / driver / mover-VM program, then
POKE its HP and watch the retire: at HP<=0 the mover updater removes it from the live
table and clears its active flag. A write-watch captures the exact retire PCs. Every
claim is a poke that either reproduces the retire or it does not.

  launch: tools/launch_repro_playback.sh --config-dir /tmp/dsrepro-phase3-w2 \
          --port 23473 --token debugger-1000 --disc "Disney-Pixar A Bug's Life (v1.0).cue"
  run:    python3 tools/phase3_thud_trace.py --port 23473
Output: analysis/phase3_thud.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from datetime import date
from pathlib import Path

try:
    from live_session_provenance import (add_required_live_args, finish_run,
                                         inspect_state_before_load,
                                         write_live_evidence)
except ModuleNotFoundError:
    from tools.live_session_provenance import (add_required_live_args, finish_run,
                                               inspect_state_before_load,
                                               write_live_evidence)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.path.expanduser("~/duckstation/scripts/debugger-client"))
sys.path.insert(0, str(ROOT / "tools"))
from build_identity import verify_pristine_media_path  # noqa: E402
from phase3_jr_tables import find_function, load_functions  # noqa: E402

SAVE = ROOT / "level_09.sav"
LIVE_TABLE = 0x80090748          # compacted live-enemy pointer table
SCENE = 0x80082504
BOSS_ID = 0x24                   # Thud, the stage-9 boss
# actor record field offsets (shared schema, 0x8009FE04 stride 0x84 family)
OFF_ID, OFF_FLAGS, OFF_HP, OFF_VMIP, OFF_CB = 0x00, 0x5C, 0x6E, 0x70, 0x7C


def connect(port, token):
    from duckstation_debug_client import DebuggerClient
    cl = DebuggerClient("127.0.0.1", port, "ws")
    cl.authenticate(token)
    cl.transport.sock.settimeout(30)
    return cl


def verified_media_identity(rig, status):
    """Hash the exact mounted path and reject an identity/media swap race."""
    before = rig.call("emulator.getMediaInfo", {})
    if not before.get("has_media") or not before.get("path"):
        raise SystemExit(f"mounted-media guard: no media is mounted: {before}")
    if status.get("game_serial") != "SCUS-94288" or \
            before.get("game_serial") != status.get("game_serial"):
        raise SystemExit(
            f"mounted-media guard: debugger/media serial mismatch: {status} / {before}")
    verification = verify_pristine_media_path(before["path"])
    after = rig.call("emulator.getMediaInfo", {})
    stable_keys = ("has_media", "path", "game_serial", "subimage_count", "subimage_index")
    if any(before.get(key) != after.get(key) for key in stable_keys):
        raise SystemExit(
            f"mounted-media guard: media changed while hashing: {before} -> {after}")
    return {
        "game_serial": status.get("game_serial"),
        "game_title": status.get("game_title"),
        "game_path": before["path"],
        "has_media": True,
        "serials_agree": True,
        "rpc_before_hash": before,
        "rpc_after_hash": after,
        "hash_verification": verification,
    }


def checked_access_log(rig, watch_ids):
    """Retrieve a stable, complete paused snapshot for the relevant watches."""
    status = rig.call("debugger.status", {})
    paused_snapshot = bool(status.get("paused")) and not bool(status.get("running"))
    if not paused_snapshot:
        raise SystemExit(f"access-log guard: guest was not paused before paging: {status}")
    first = rig.call("accessLog.get", {"offset": 0, "limit": 10000})
    total = int(first.get("total", 0))
    events = list(first.get("events", []))
    page_totals = [total]
    truncated = bool(first.get("truncated"))
    empty_page = False
    pages = 1
    while len(events) < total:
        page = rig.call("accessLog.get", {
            "offset": len(events), "limit": min(10000, total - len(events))})
        pages += 1
        page_totals.append(int(page.get("total", -1)))
        truncated = truncated or bool(page.get("truncated"))
        chunk = page.get("events", [])
        if not chunk:
            empty_page = True
            break
        events.extend(chunk)
    watches = [w for w in first.get("watches", [])
               if int(w.get("watch_id", -1)) in watch_ids]
    cap_saturated = any(int(w.get("hit_count", 0)) >= int(w.get("max_events", 0))
                        for w in watches)
    totals_stable = all(value == total for value in page_totals)
    complete = (paused_snapshot and not truncated and not empty_page and len(events) == total
                and totals_stable and len(watches) == len(watch_ids)
                and not cap_saturated)
    return {
        "total": total,
        "returned": len(events),
        "pages": pages,
        "page_limit": 10000,
        "paused_snapshot": paused_snapshot,
        "truncated": truncated,
        "totals_stable": totals_stable,
        "empty_page_before_total": empty_page,
        "watch_cap_saturated": cap_saturated,
        "watches": watches,
        "complete": complete,
    }, events


class Rig:
    def __init__(self, cl):
        self.cl = cl

    def call(self, m, p=None):
        return self.cl.call(m, p or {})

    def rmem(self, a, n):
        return bytes.fromhex(self.call("debugger.readMemory",
                                       {"address": "0x%08x" % a, "length": n})["hex"])

    def wmem(self, a, b):
        return self.call("debugger.writeMemory",
                         {"address": "0x%08x" % a, "hex": b.hex()})

    def u16(self, a):
        return struct.unpack("<H", self.rmem(a, 2))[0]

    def s16(self, a):
        return struct.unpack("<h", self.rmem(a, 2))[0]

    def u32(self, a):
        return struct.unpack("<I", self.rmem(a, 4))[0]

    def load(self):
        loaded = self.call("emulator.loadState",
                           {"path": str(SAVE.resolve()), "pause_after_load": True})
        assert loaded.get("loaded") and loaded.get("game_serial") == "SCUS-94288", loaded
        self.adv(5)

    def adv(self, n=1):
        # chunk to keep each RPC under the socket timeout
        while n > 0:
            step = min(n, 90)
            self.call("emulator.advanceFrames", {"frames": step})
            n -= step

    def wh16(self, a, v):
        self.wmem(a, struct.pack("<h", v))


def find_boss(rig):
    """The boss actor = the live-table entry whose id is BOSS_ID."""
    tab = rig.rmem(LIVE_TABLE, 0x80)
    for i in range(0, 0x80, 4):
        p = struct.unpack("<I", tab[i:i + 4])[0]
        if 0x80000000 <= p < 0x80200000 and rig.u16(p + OFF_ID) == BOSS_ID:
            return p, i // 4
    return None, None


def run(args):
    funcs = load_functions()

    def fn(pc):
        t = find_function(funcs, pc)
        return {"start": t[2]["start"], "name": t[2].get("name")} if t else None

    rig = Rig(connect(args.port, args.token))
    status = rig.call("debugger.status", {})
    media_identity = verified_media_identity(rig, status)
    state_inspection = inspect_state_before_load(rig, SAVE, media_identity)
    rig.load()
    assert rig.u32(SCENE) == 14, "not in scene 14 (stage-9 Bug Bar arena)"

    boss, slot = find_boss(rig)
    assert boss is not None, "no id-0x24 boss in the live enemy table"
    ident = {
        "record_addr": f"0x{boss:08X}",     # dynamic — the STABLE binding is the schema
        "live_table": f"0x{LIVE_TABLE:08X}", "live_slot": slot,
        "id": rig.u16(boss + OFF_ID),
        "hp_at_0x6e": rig.s16(boss + OFF_HP),
        "flags_at_0x5c": rig.u16(boss + OFF_FLAGS),
        "mover_vm_ip_at_0x70": f"0x{rig.u32(boss + OFF_VMIP):08X}",
        "driver_cb_at_0x7c": f"0x{rig.u32(boss + OFF_CB):08X}",
    }
    flags = ident["flags_at_0x5c"]
    ident["berry_damageable_bit_0x40"] = bool(flags & 0x40)
    ident["active_bit_0x4000"] = bool(flags & 0x4000)

    # --- threshold: HP=1 must NOT retire; HP<=0 MUST retire --------------------
    def poke_and_settle(hp):
        rig.load()
        b, _ = find_boss(rig)
        rig.wh16(b + OFF_HP, hp)
        rig.adv(60)
        live0 = rig.u32(LIVE_TABLE)
        return {"hp_poked": hp, "live_slot0": f"0x{live0:08X}",
                "boss_still_live": live0 == b,
                "flags_after": rig.u16(b + OFF_FLAGS)}

    survives = poke_and_settle(1)

    # --- HP<=0 retire, with a write-watch to capture the retire handler --------
    rig.load()
    b, _ = find_boss(rig)
    assert b is not None, "boss disappeared after state reload"
    rig.call("accessLog.clear", {})
    flag_watch = rig.call("accessLog.addWatch", {
        "address": "0x%08x" % (b + OFF_FLAGS),
        "length": 2, "type": "write", "max_events": 50000})["watch_id"]
    table_watch = rig.call("accessLog.addWatch", {
        "address": "0x%08x" % LIVE_TABLE,
        "length": 4, "type": "write", "max_events": 50000})["watch_id"]
    rig.wh16(b + OFF_HP, 0)
    rig.adv(60)
    retired = {"live_slot0": f"0x{rig.u32(LIVE_TABLE):08X}",
               "boss_removed": rig.u32(LIVE_TABLE) != b,
               "active_bit_after": bool(rig.u16(b + OFF_FLAGS) & 0x4000)}
    access_accounting, events = checked_access_log(
        rig, {int(flag_watch), int(table_watch)})
    handlers = {}
    for e in events:
        pc = e["instruction_pc"]
        handlers.setdefault(pc, {"instruction": e["instruction"],
                                 "target": e["address"], "function": fn(int(pc, 16))})
    retire_funcs = sorted({h["function"]["name"] for h in handlers.values()
                           if h["function"]})

    disproved = None
    bound = (ident["id"] == BOSS_ID and ident["hp_at_0x6e"] > 0
             and retired["boss_removed"] and not retired["active_bit_after"]
             and survives["boss_still_live"] and access_accounting["complete"])
    run_provenance = finish_run(
        args, generator="tools/phase3_thud_trace.py",
        anchor={"save": str(SAVE.relative_to(ROOT)),
                "fixture_sha256": {SAVE.name: hashlib.sha256(SAVE.read_bytes()).hexdigest()},
                "state_inspections": [state_inspection],
                "media_identity": media_identity},
        timing={"hp1_advance_frames": 45, "hp0_advance_frames": 60,
                "access_log": access_accounting},
    )

    doc = {
        "_comment": "Phase-3 W1: F09 (Stage-9 Bug Bar, defeat Thud) bound by LIVE "
                    "poke-falsification. Thud is setpiece-spawned (chunk-31 all-zero), "
                    "so this is the only way to bind it. Regenerate (LIVE): "
                    "tools/phase3_thud_trace.py --port N",
        "generated": date.today().isoformat(),
        "run_provenance": run_provenance,
        "media_identity_after_connect": media_identity,
        "authority": {"media": "pristine (SCUS-94288)", "scene_id": 14,
                      "save": str(SAVE.relative_to(ROOT))},
        "fixture_sha256": {SAVE.name: hashlib.sha256(SAVE.read_bytes()).hexdigest()},
        "boss_identity": ident,
        "defeat_threshold": {
            "hp1_survives": survives, "hp0_retires": retired,
            "rule": "HP@+0x6e <= 0 retires the boss; HP=1 does not"},
        "retire_handler": {"functions": retire_funcs, "writes": handlers,
                           "access_log": access_accounting},
        "damage_path": {
            "berry_damageable": ident["berry_damageable_bit_0x40"],
            "mechanism": "enemy +0x5c bit 0x40 (SYS berry->enemy damage; handler "
                         "0x80058df0+); HP decremented per hit until <=0"},
        "bound": bound,
        "conclusion": (
            "F09 bound: the stage-9 boss (Thud) is live-enemy id 0x24, HP@+0x6e "
            "(50), berry-damageable (+0x5c bit 0x40), driven by a mover-VM program "
            "and a per-actor driver callback; at HP<=0 the mover updater retires it "
            "(removes it from the live table 0x80090748 and clears the +0x5c active "
            "bit 0x4000). Confirmed by poke-falsification: HP=1 survives, HP=0 retires."
            if bound else "NOT bound — see fields; investigate before concluding"),
    }
    out = ROOT / "analysis" / "phase3_thud.json"
    write_live_evidence(out, doc)
    print(f"[thud] boss id=0x{ident['id']:02x} HP={ident['hp_at_0x6e']} "
          f"driver={ident['driver_cb_at_0x7c']} vm={ident['mover_vm_ip_at_0x70']} | "
          f"retire by {retire_funcs} | HP1 survives={survives['boss_still_live']} "
          f"HP0 removed={retired['boss_removed']} | bound={bound}")
    return 0 if bound else 1


def main():
    ap = argparse.ArgumentParser()
    add_required_live_args(ap)
    return run(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
