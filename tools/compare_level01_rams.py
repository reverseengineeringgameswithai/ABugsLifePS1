#!/usr/bin/env python3
"""Compare selected LEVEL01 runtime state between two raw PS1 RAM dumps."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


RAM_BASE = 0x80000000
RAM_SIZE = 0x200000
CONTACT_BASE = 0x800B0D18
CONTACT_STRIDE = 0x38
VIS_BASE = 0x8009C870
VIS_STRIDE = 0x344


def off(va: int) -> int:
    if not RAM_BASE <= va < RAM_BASE + RAM_SIZE:
        raise ValueError(hex(va))
    return va - RAM_BASE


def u8(ram: bytes, va: int) -> int:
    return ram[off(va)]


def u16(ram: bytes, va: int) -> int:
    return struct.unpack_from("<H", ram, off(va))[0]


def s16(ram: bytes, va: int) -> int:
    return struct.unpack_from("<h", ram, off(va))[0]


def u32(ram: bytes, va: int) -> int:
    return struct.unpack_from("<I", ram, off(va))[0]


def s32(ram: bytes, va: int) -> int:
    return struct.unpack_from("<i", ram, off(va))[0]


def contact_stats(ram: bytes) -> dict[str, int]:
    stats = {
        "active22": 0,
        "flag80": 0,
        "both": 0,
        "action04": 0,
        "nonzero": 0,
    }
    for i in range(64):
        va = CONTACT_BASE + i * CONTACT_STRIDE
        x, y, z = s32(ram, va), s32(ram, va + 4), s32(ram, va + 8)
        action = u16(ram, va + 0x20)
        active = u16(ram, va + 0x22)
        flags33 = u8(ram, va + 0x33)
        if active:
            stats["active22"] += 1
        if flags33 & 0x80:
            stats["flag80"] += 1
        if active and flags33 & 0x80:
            stats["both"] += 1
        if action == 4:
            stats["action04"] += 1
        if x or y or z or action or active or flags33:
            stats["nonzero"] += 1
    return stats


def visual_stats(ram: bytes) -> list[tuple[int, int, tuple[int, int, int], tuple[int, int, int]]]:
    rows = []
    for i in range(8):
        va = VIS_BASE + i * VIS_STRIDE
        active = u16(ram, va)
        home = (s32(ram, va + 0x24), s32(ram, va + 0x28), s32(ram, va + 0x2C))
        render = (s32(ram, va + 0x34), s32(ram, va + 0x38), s32(ram, va + 0x3C))
        rows.append((i, active, home, render))
    return rows


def type_ptrs(ram: bytes) -> dict[int, int]:
    base = 0x80096DA0
    out = {}
    for i in range(0x50):
        ptr = u32(ram, base + i * 4)
        if ptr:
            out[i] = ptr
    return out


def print_key_table(good: bytes, bad: bytes) -> None:
    fields = [
        ("shell_substate", 0x8008243C, "s32"),
        ("scene_slot", 0x8008245C, "s16"),
        ("current_scene_id", 0x80082504, "s32"),
        ("allocator_cursor", 0x8008234C, "u32"),
        ("type3f_ptr", 0x80096E9C, "u32"),
        ("phase_gate", 0x800910A4, "u8"),
        ("player_x", 0x800A6500, "s32"),
        ("player_y", 0x800A6504, "s32"),
        ("player_z", 0x800A6508, "s32"),
        ("actor_x", 0x800A0A68, "s32"),
        ("actor_y", 0x800A0A6C, "s32"),
        ("actor_z", 0x800A0A70, "s32"),
    ]
    funcs = {"u8": u8, "s16": s16, "s32": s32, "u32": u32}
    print("key globals")
    print("name               addr        good        bad")
    for name, va, kind in fields:
        fn = funcs[kind]
        gv = fn(good, va)
        bv = fn(bad, va)
        def fmt(v: int) -> str:
            return hex(v) if kind in ("u8", "u32") else str(v)
        print(f"{name:18s} {va:#010x} {fmt(gv):>10s} {fmt(bv):>10s}")
    print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("good", type=Path)
    ap.add_argument("bad", type=Path)
    args = ap.parse_args()
    good = args.good.read_bytes()
    bad = args.bad.read_bytes()
    if len(good) != RAM_SIZE or len(bad) != RAM_SIZE:
        raise SystemExit("expected two 2 MiB raw RAM dumps")

    print_key_table(good, bad)

    print("type-0x3f headers")
    for label, ram in (("good", good), ("bad", bad)):
        ptr = u32(ram, 0x80096E9C)
        print(
            f"{label:4s} ptr={ptr:#010x} count={u16(ram, ptr)} "
            f"type={s16(ram, ptr + 2):#x}"
        )
    print()

    print("contact stats")
    print("dump nonzero +0x22!=0 +0x33&0x80 both action04")
    for label, ram in (("good", good), ("bad", bad)):
        st = contact_stats(ram)
        print(
            f"{label:4s} {st['nonzero']:7d} {st['active22']:8d} "
            f"{st['flag80']:10d} {st['both']:4d} {st['action04']:8d}"
        )
    print()

    print("visual slots")
    print("dump idx active home_xyz render_xyz")
    for label, ram in (("good", good), ("bad", bad)):
        for i, active, home, render in visual_stats(ram):
            if active or home != (0, 0, 0) or render != (0, 0, 0):
                print(f"{label:4s} {i:3d} {active:6d} {home!s:>32s} {render!s:>32s}")
    print()

    print("type pointer differences")
    gp, bp = type_ptrs(good), type_ptrs(bad)
    for idx in sorted(set(gp) | set(bp)):
        gv = gp.get(idx, 0)
        bv = bp.get(idx, 0)
        if gv != bv:
            print(f"type {idx:02x}: good={gv:#010x} bad={bv:#010x} delta={bv-gv:+#x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
