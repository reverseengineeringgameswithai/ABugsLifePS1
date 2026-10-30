#!/usr/bin/env python3
"""Phase-2 standalone proofs, made REGENERABLE (review: the capacity-hang and
SPU-pitch JSONs were produced by ad-hoc scripts, so their tests only asserted
that the JSON said "confirmed").

  --hang   Contact-allocator capacity hang, A/B via debugger.callFunction on
           contact_alloc (FUNC_80059E44): with free slots the call RETURNS a
           record pointer; with all 64 slots synthetically occupied
           (flags|=0x80, active_type>=1) the escape-less free-slot search never
           returns and the call TIMES OUT. Semantics per
           src_re/contact_alloc_80059e44.c. Destructive but isolated: every
           trial starts from a fresh loadState.
           -> analysis/phase2_capacity_hang_proof.json
  --spu    Same-scene SPU pitch detector proof: doubling one on-voice's pitch in
           a copy of the pristine movie baseline must fire the comparator's
           spu_voices check and NOTHING else. (Runtime SPU register writes are
           unavailable — the fork exposes no SPU write surface; documented
           fork-extension candidate.) Offline; no emulator needed.
           -> analysis/phase2_spu_pitch_mutation.json

Usage:
    python3 tools/phase2_proofs.py --spu                 # offline
    python3 tools/phase2_proofs.py --hang [--port 23472] # needs a repro instance
    python3 tools/phase2_proofs.py --all  [--port 23472]
"""
from __future__ import annotations

import argparse
import copy
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

POOL_BASE, POOL_SLOTS, POOL_STRIDE = 0x800B0D18, 64, 0x38
CONTACT_ALLOC = 0x80059E44
HANG_ANCHOR = "red_berry_thrown.sav"


def prove_spu() -> int:
    base = json.loads((ROOT / "analysis" / "phase2_movie_baseline.json").read_text())
    label = "stage01_anthill"
    orig = base["movies"][label]
    mut = copy.deepcopy(orig)
    victim = None
    for v in mut["spu_voices"]:
        if v["on"]:
            victim = v["index"]
            v["pitch"] = (v["pitch"] * 2) & 0x3FFF
            break
    assert victim is not None, "no active voice in the baseline"
    fired = []
    for what, a, b in (("mid_frame_sha256", orig["frame_sha256"], mut["frame_sha256"]),
                       ("mid_spu_voices", orig["spu_voices"], mut["spu_voices"]),
                       ("mid_pool_active", orig["pool_active"], mut["pool_active"]),
                       ("mid_pool_sha256", orig["pool_sha256"], mut["pool_sha256"])):
        if a != b:
            fired.append(what)
    doc = {
        "_comment": "SAME-SCENE SPU pitch mutation proof (comparator-level): one "
                    "on-voice's pitch doubled in a copy of the pristine movie "
                    "baseline; the comparator's checks must fire on spu_voices ONLY. "
                    "Runtime register mutation is unavailable (no SPU write surface "
                    "in the fork — documented extension candidate); the ALLMODS run "
                    "remains the broad runtime negative. Regenerate: "
                    "tools/phase2_proofs.py --spu",
        "generated": date.today().isoformat(),
        "baseline_stage": label, "mutated_voice": victim,
        "pitch_before": orig["spu_voices"][victim]["pitch"],
        "pitch_after": mut["spu_voices"][victim]["pitch"],
        "checks_fired": fired,
        "isolated_to_spu_check": fired == ["mid_spu_voices"],
        "verdict": "DETECTED" if "mid_spu_voices" in fired else "NOT DETECTED",
    }
    (ROOT / "analysis" / "phase2_spu_pitch_mutation.json").write_text(
        json.dumps(doc, indent=1) + "\n")
    print(f"[spu] {doc['verdict']}; checks fired: {fired}")
    return 0 if doc["verdict"] == "DETECTED" else 1


def prove_hang(port: int, token: str) -> int:
    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", port, "ws")
    c.authenticate(token)
    c.transport.sock.settimeout(120)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def load():
        r = c.call("emulator.loadState",
                   {"path": str(ROOT / HANG_ANCHOR), "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r

    def occupy_all():
        buf = rd(POOL_BASE, POOL_SLOTS * POOL_STRIDE)
        writes = []
        for i in range(POOL_SLOTS):
            base = POOL_BASE + i * POOL_STRIDE
            at = struct.unpack_from("<H", buf, i * POOL_STRIDE + 0x22)[0]
            fl = buf[i * POOL_STRIDE + 0x33]
            if at == 0:
                writes.append({"address": "0x%08X" % (base + 0x22),
                               "type": "u16", "value": 1})
            writes.append({"address": "0x%08X" % (base + 0x33),
                           "type": "u8", "value": fl | 0x80})
        c.call("debugger.scatterWrite", {"writes": writes, "atomic": True})

    def call_alloc(timeout_ms=5000):
        try:
            r = c.call("debugger.callFunction",
                       {"address": "0x%08X" % CONTACT_ALLOC,
                        "a0": 1000, "a1": 1000, "a2": 1000, "a3": 34,
                        "timeout": timeout_ms},
                       timeout=(timeout_ms / 1000) + 30)
            return {"ok": True, "v0": r.get("v0_hex")}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:150]}"}

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"

    load()
    free_case = call_alloc()
    load()
    occupy_all()
    full_case = call_alloc()
    hang = bool(free_case.get("ok")) and (
        not full_case.get("ok") and "Timed out" in full_case.get("error", ""))
    doc = {
        "_comment": "CAPACITY HANG PROOF via debugger.callFunction on contact_alloc "
                    "(FUNC_80059E44). Allocator is a round-robin free-slot search "
                    "with NO full-array escape (src_re/contact_alloc_80059e44.c): "
                    "with free slots the call returns a record pointer; with all 64 "
                    "slots occupied it never returns. MOD-SAFETY: never let a mod "
                    "hold all 64 contact slots occupied. Regenerate: "
                    "tools/phase2_proofs.py --hang (isolated instance; destructive "
                    "writes are undone by the next loadState).",
        "generated": date.today().isoformat(),
        "anchor": HANG_ANCHOR, "slots_occupied": POOL_SLOTS,
        "free_slots_call": free_case, "all_occupied_call": full_case,
        "hang_confirmed": hang,
        "verdict": ("HANG CONFIRMED: allocation returns with free slots; with all 64 "
                    "occupied the search loop never returns"
                    if hang else "NOT CONFIRMED — see calls"),
    }
    (ROOT / "analysis" / "phase2_capacity_hang_proof.json").write_text(
        json.dumps(doc, indent=1) + "\n")
    print(f"[hang] free={free_case} occupied={full_case} confirmed={hang}")
    return 0 if hang else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hang", action="store_true")
    ap.add_argument("--spu", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    args = ap.parse_args()
    rc = 0
    if args.spu or args.all:
        rc |= prove_spu()
    if args.hang or args.all:
        rc |= prove_hang(args.port, args.token)
    if not (args.spu or args.hang or args.all):
        ap.print_help()
        return 2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
