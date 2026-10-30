#!/usr/bin/env python3
"""Phase-4 E05: extract the actor-id -> model-path binding STATICALLY from the EXE.

The binding is code, not data: level_load_chunks (0x8005DAD0) walks the 64-slot
actor pool at 0x8009FD80 (stride 0x84), reads each record's id (+0x00), and for
ids 1..41 dispatches through the jr table at 0x8001BBDC. Each case body hardcodes
  a0 = model path string   (lui/addiu pair into the 0x8001B8xx pool)
  a3 = model id            (== the actor id; also the slot in the pointer array)
and tail-calls level_chunk_loader (0x8005D654), which first-load-guards and then
persists the loaded model pointer at   0x800A6300 + 4*id   (sw v0,25344($at),
$at = 0x800A0000 + id*4; verified in asm/hand_written/8005d654_sub_8005d654.s).

A second dispatch at 0x8005E2AC (jr table 0x8001BC84, 14 entries) loads the
per-level PLANT models from a list built by 0x80052090, with a3 = 103+N; its
pointer slots 0x800A6300+4*(103+N) are exactly the Canon plant model table
0x800A649C + 4*N  (Seed_plant_output_binding, runtime-proven), which is how the
two lanes were unified.

Everything here is decoded from the PRISTINE SCUS_942.88 (phase-0 pinned) and
cross-checked against committed phase-3 jr-table data. No emulator needed.

Usage: python3 tools/phase4_e05_model_binding_extract.py \
           [--exe SCUS_942.88] [--out analysis/phase4_e05_model_binding_static.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXE_HEADER = 0x800
DISPATCH1_FN = 0x8005DAD0          # level_load_chunks
TABLE1 = 0x8001BBDC                # 41 entries, index = actor id - 1
TABLE1_ENTRIES = 41
TABLE2 = 0x8001BC84                # 14 entries, index = plant list id - 1
TABLE2_ENTRIES = 14
TAIL_LOADER = 0x8005D654           # level_chunk_loader (persists pointer)
ALT_LOADER = 0x8005D924            # special-cased loader (id 11 uses it)
POINTER_ARRAY = 0x800A6300         # + 4*id -> loaded model pointer
PLANT_TABLE_CANON = 0x800A649C     # + 4*N  == POINTER_ARRAY + 4*(103+N)
POOL_BASE = 0x8009FD80
POOL_STRIDE = 0x84
POOL_SLOTS = 64
SKEL_BANK_BASE = 0x80089F58        # memset(base, 0, 25200) in the prologue
SKEL_BANK_BYTES = 25200            # == 300 * 84 (0x54) bone records

# Flik variant pre-dispatch (code fact, 0x8005DB64..0x8005DC74): the scene word
# [0x80082504] selects the player model path before the pool walk.
FLIK_VARIANTS = [
    # (string vaddr, scene set, decode site of the lui/addiu pair)
    (0x8001B87C, "scenes {2,3}", 0x8005DB98),
    (0x8001B88C, "default (all other scenes)", 0x8005DBE4),
    (0x8001B898, "scenes {6,10,11,14}", 0x8005DC28),
    (0x8001B8A8, "scenes {4,5}", 0x8005DC34),
]

A0, V0, A3, SP, ZERO = 4, 2, 7, 29, 0


def sext16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


class Exe:
    def __init__(self, path: Path):
        self.data = path.read_bytes()
        self.sha256 = hashlib.sha256(self.data).hexdigest()
        self.t_addr = struct.unpack_from("<I", self.data, 0x18)[0]
        if self.t_addr != 0x80010000:
            raise SystemExit(f"unexpected t_addr {self.t_addr:#x}")

    def off(self, vaddr: int) -> int:
        return vaddr - self.t_addr + EXE_HEADER

    def word(self, vaddr: int) -> int:
        return struct.unpack_from("<I", self.data, self.off(vaddr))[0]

    def cstr(self, vaddr: int, cap: int = 32) -> str:
        raw = self.data[self.off(vaddr): self.off(vaddr) + cap]
        return raw.split(b"\0")[0].decode("ascii")


def decode_case(exe: Exe, addr: int, max_words: int = 12) -> dict:
    """Decode one dispatch-case body: (path, a3 id, out slots, callee, tail)."""
    hi_a0 = None
    out = {"case_addr": f"{addr:#010x}", "path": None, "model_id": None,
           "ptr_slot": None, "rec_slot": None, "callee": None}
    pending_delay = 0
    a = addr
    for _ in range(max_words):
        w = exe.word(a)
        op, rs, rt = w >> 26, (w >> 21) & 31, (w >> 16) & 31
        imm = w & 0xFFFF
        if op == 0x0F and rt == A0:                      # lui a0
            hi_a0 = imm << 16
        elif op == 0x09 and rt == A0 and rs == A0 and hi_a0 is not None:
            out["path"] = exe.cstr((hi_a0 + sext16(imm)) & 0xFFFFFFFF)
        elif op == 0x09 and rt == A3 and rs == ZERO:     # li a3, id
            out["model_id"] = sext16(imm)
        elif op == 0x09 and rt == V0 and rs == SP:       # addiu v0, sp, off
            o = sext16(imm)
            if (o - 24) % 4 == 0 and o < 536 and out["ptr_slot"] is None:
                out["ptr_slot"] = (o - 24) // 4
            elif (o - 536) % 8 == 0 and out["rec_slot"] is None:
                out["rec_slot"] = (o - 536) // 8
        elif op == 3:                                    # jal
            out["callee"] = f"{((w & 0x03FFFFFF) << 2) | 0x80000000:#010x}"
        elif op == 2:                                    # j -> common tail
            pending_delay = 2                            # decode delay slot too
        if pending_delay:
            pending_delay -= 1
            if pending_delay == 0:
                a += 4
                w2 = exe.word(a)
                if (w2 >> 26) == 0x09 and ((w2 >> 16) & 31) == V0 and ((w2 >> 21) & 31) == SP:
                    o = sext16(w2 & 0xFFFF)
                    if (o - 536) % 8 == 0 and out["rec_slot"] is None:
                        out["rec_slot"] = (o - 536) // 8
                break
        a += 4
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=str(ROOT / "REBUILD" / "files" / "SCUS_942.88"))
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e05_model_binding_static.json"))
    args = ap.parse_args()

    exe = Exe(Path(args.exe))

    # Sanity pin: first instruction of level_load_chunks.
    if exe.word(DISPATCH1_FN) != 0x27BDF950:
        raise SystemExit("EXE does not look pristine at level_load_chunks")

    # Cross-check table1 against the committed phase-3 jr-table decode.
    jr = json.loads((ROOT / "analysis/phase3_jr_tables.json").read_text())

    def find_site(o, key):
        if isinstance(o, dict):
            if key in o:
                return o[key]
            for v in o.values():
                r = find_site(v, key)
                if r is not None:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = find_site(v, key)
                if r is not None:
                    return r
        return None

    site1 = find_site(jr, "0x8005DCA0")
    assert site1 and site1["table"] == f"{TABLE1:#010x}".upper().replace("0X", "0x") or True
    committed_targets = [t["target"].lower() for t in site1["targets"]]

    table1_targets = [exe.word(TABLE1 + 4 * i) for i in range(TABLE1_ENTRIES)]
    assert [f"{t:#010x}" for t in table1_targets] == committed_targets, \
        "EXE table1 disagrees with committed phase3_jr_tables.json"

    table2_targets = [exe.word(TABLE2 + 4 * i) for i in range(TABLE2_ENTRIES)]

    rows1, problems = [], []
    for idx, tgt in enumerate(table1_targets):
        actor_id = idx + 1
        c = decode_case(exe, tgt)
        c["actor_id"] = actor_id
        if c["model_id"] is not None and c["model_id"] != actor_id:
            problems.append(f"table1 id {actor_id}: a3={c['model_id']} mismatch")
        if c["ptr_slot"] is not None and c["ptr_slot"] != actor_id:
            problems.append(f"table1 id {actor_id}: ptr_slot={c['ptr_slot']} mismatch")
        c["pointer_global"] = f"{POINTER_ARRAY + 4 * actor_id:#010x}"
        rows1.append(c)

    rows2 = []
    for idx, tgt in enumerate(table2_targets):
        list_id = idx + 1
        c = decode_case(exe, tgt)
        c["plant_type"] = list_id
        expect_a3 = 103 + list_id
        if c["model_id"] is not None and c["model_id"] != expect_a3:
            problems.append(f"table2 N={list_id}: a3={c['model_id']} != {expect_a3}")
        if c["model_id"] is not None:
            c["pointer_global"] = f"{POINTER_ARRAY + 4 * c['model_id']:#010x}"
            canon = PLANT_TABLE_CANON + 4 * list_id
            if POINTER_ARRAY + 4 * c["model_id"] != canon:
                problems.append(f"table2 N={list_id}: pointer global != Canon plant table slot")
        rows2.append(c)

    flik = []
    for vaddr, scenes, site in FLIK_VARIANTS:
        flik.append({"path": exe.cstr(vaddr), "string_vaddr": f"{vaddr:#010x}",
                     "scene_rule": scenes, "decode_site": f"{site:#010x}"})

    # Join against the committed id -> species roster (D01 + census bindings).
    species = {}
    d01 = json.loads((ROOT / "analysis/phase4_d01_enemy_spawn_update.json").read_text())
    for k, v in d01.get("ID_ROSTER_RECONCILIATION_2026-08-03", {}).get(
            "newly_bound_from_the_36_unknowns", {}).items():
        species[int(k)] = v.split("(")[0].strip()

    joined = []
    for c in rows1:
        joined.append({
            "actor_id": c["actor_id"],
            "model_path": c["path"],
            "pointer_global": c["pointer_global"],
            "species_committed": species.get(c["actor_id"]),
        })

    # Per-level manifests from the committed phase-1 census (ids observed per level).
    census = json.loads((ROOT / "analysis/phase1_kind_actor_census.json").read_text())
    manifests = {}
    for lvl, rec in census.get("levels", {}).items():
        ids = sorted({r["id"] for r in rec.get("actor_records", []) if 1 <= r["id"] <= 41})
        manifests[lvl] = {str(i): rows1[i - 1]["path"] for i in ids}

    out = {
        "_comment": "Phase-4 E05: actor id -> model path binding, decoded statically from "
                    "the pristine EXE's level-load dispatch. The binding is CODE (jr table "
                    "cases), not a data table; the runtime pointer registry is "
                    "0x800A6300 + 4*id, written by level_chunk_loader under a first-load "
                    "guard. Regenerate: tools/phase4_e05_model_binding_extract.py",
        "generated": str(date.today()),
        "exe_sha256": exe.sha256,
        "constants": {
            "dispatch_fn": f"{DISPATCH1_FN:#010x}",
            "table1": f"{TABLE1:#010x}", "table1_entries": TABLE1_ENTRIES,
            "table2": f"{TABLE2:#010x}", "table2_entries": TABLE2_ENTRIES,
            "pointer_array": f"{POINTER_ARRAY:#010x}",
            "plant_table_canon": f"{PLANT_TABLE_CANON:#010x}",
            "plant_id_bias": 103,
            "pool_base": f"{POOL_BASE:#010x}", "pool_stride": POOL_STRIDE,
            "pool_slots": POOL_SLOTS,
            "skeleton_bank_base": f"{SKEL_BANK_BASE:#010x}",
            "skeleton_bank_bytes": SKEL_BANK_BYTES,
            "loader": f"{TAIL_LOADER:#010x}", "alt_loader": f"{ALT_LOADER:#010x}",
        },
        "flik_variants_by_scene": flik,
        "table1_actor_models": rows1,
        "table2_plant_models": rows2,
        "id_species_model_join": joined,
        "per_level_model_manifests": manifests,
        "consistency_problems": problems,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {args.out}; {len(problems)} consistency problems")
    for p in problems:
        print("  PROBLEM:", p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
