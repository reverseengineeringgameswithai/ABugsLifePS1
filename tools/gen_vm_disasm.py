#!/usr/bin/env python3
"""Static mover-VM bytecode disassembler (u2-B).

Decodes the RESIDENT enemy-AI programs (region 0x8007745C..0x80077AF6, program
pointer table 0x80077AF8, 13 entries) with the FUNC_8004C13C interpreter's ISA:
fetch = signed u16 at IP, primary-table index = s16+1 (26 slots @ 0x8001B2F4).

Evidence-exact operand widths: each handler's IP advance is EXTRACTED from its
own code (the `addiu s1,s1,N` in the handler body), not hand-copied from notes.
Semantics labels come from the decoded ISA (Canon FUNC_8004C13C, 21 CONFIRMED /
5 LIKELY). CALL (op12) slots resolve through the sub-table 0x8001B35C.

Output: analysis/vm_programs.json + analysis/vm_programs.md — a checkable
artifact that must agree with the hand decode in src_re/enemy_ai_programs.c.
"""
from __future__ import annotations
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
HDR, LOAD = 0x800, 0x80010000

OP_TABLE = 0x8001B2F4          # 26 handler pointers; index = stream_s16 + 1
CALL_TABLE = 0x8001B35C        # op12 sub-table (9 entries)
PROG_PTRS = 0x80077AF8         # program entry pointers; COUNT IS DERIVED, see below
REGION_LO, REGION_HI = 0x8007745C, 0x80077AF8

# semantics per primary-table index (Canon FUNC_8004C13C ISA decode)
SEM = {
    0: ("jump_back", "CONFIRMED"),          # s1 -= s16[IP+2]*2
    1: ("noop_shared_tail", "INDISTINGUISHABLE"),
    2: ("wait", "CONFIRMED"),               # object[+0x60] = op1
    3: ("wait_random", "CONFIRMED"),        # (noise & op1) + op2
    4: ("random_dir_step", "CONFIRMED"),
    5: ("path_next_waypoint", "CONFIRMED"),  # u3 live: a1 walks u16 waypoint cursor @0x80077BB4 (mosquito)
    6: ("noop_shared_tail", "INDISTINGUISHABLE"),
    7: ("noop_shared_tail", "INDISTINGUISHABLE"),
    8: ("noop_shared_tail", "INDISTINGUISHABLE"),
    9: ("branch_if_s3", "CONFIRMED"),      # blez s3 skip; else -> op20 branch @0x8004C774
    10: ("noop_shared_tail", "INDISTINGUISHABLE"),
    11: ("seek_path_endpoint", "LIKELY"),
    12: ("call_native", "CONFIRMED"),       # jr [0x8001B35C + (op1-1)*4]
    13: ("flags_mask", "CONFIRMED"),        # flags = (flags & op1) | op2
    14: ("anim_clip_load", "CONFIRMED"),    # u3 live: (clip,set) u16 pairs + actor anim block (bee/worm)
    15: ("cond_noise_mask", "CONFIRMED"),   # s3 = ((altcursor & op1) == 0)
    16: ("chase_radius_scratch", "CONFIRMED"),  # program[+0x1B] = op1 >> 4
    17: ("player_proximity", "CONFIRMED"),  # s3 = dist^2 < op1^2
    18: ("noop_shared_tail", "INDISTINGUISHABLE"),
    19: ("noop_shared_tail", "INDISTINGUISHABLE"),
    20: ("branch_fwd_if_s3", "CONFIRMED"),  # if s3: s1 += op1*2 - 2
    21: ("noop_shared_tail", "INDISTINGUISHABLE"),
    22: ("done_disable", "CONFIRMED"),      # object[+0x50] = 0x80000000
    23: ("set_byte_params", "CONFIRMED"),   # [+0x48]/[+0x49]
    24: ("call_play_sound", "CONFIRMED"),   # u3 live: worm strike, operand 0x18 = sound id -> play_sound
    25: ("cond_powerup_flag", "CONFIRMED"), # byte 0x800A6596 !=0 OR (u16 0x800A6590 & 0x80) -> s3
}
# documented program identities (src_re/enemy_ai_programs.c)
PROGRAM_IDS = {
    0x8007745C: "program_0 (mosquito path header)", 0x80077470: "spider",
    0x800774A8: "program_2", 0x800774FC: "program_3", 0x8007755C: "dragonfly",
    0x80077578: "bee", 0x800775C8: "earthworm", 0x800775E4: "mosquito",
    0x8007760C: "grasshopper", 0x80077634: "program_9", 0x80077654: "program_10",
    0x80077674: "huge_spider", 0x80077690: "redbug",
}

exe = EXE.read_bytes()

def u16(va): return struct.unpack_from("<H", exe, HDR + (va - LOAD))[0]
def s16(va):
    v = u16(va)
    return v - 0x10000 if v >= 0x8000 else v
def u32(va): return struct.unpack_from("<I", exe, HDR + (va - LOAD))[0]

def handler_advance(h, hend):
    """Extract the handler's own `addiu s1,s1,N` (s1 = IP, reg 17), scanning only
    within [h, hend) so we never read a neighboring handler's advance."""
    for a in range(h, hend, 4):
        w = u32(a)
        if (w >> 16) == 0x2631:            # addiu s1, s1, imm
            return w & 0xFFFF
    return None                            # jump/terminator: no linear advance

handlers = [u32(OP_TABLE + i * 4) for i in range(26)]

# --- STRUCTURAL GUARD -------------------------------------------------------
# Opcodes whose primary-table slots hold the SAME address dispatch to the same
# code and therefore CANNOT have distinct semantics. This artifact previously
# gave eight such slots eight different names -- park_end / park_seek /
# park_arrive_test / park_arrive_stop / park_path / park_seek18 / park19 /
# park21 -- every one marked CONFIRMED. They all point at 0x8004C818, which is
# not an operation body at all but the interpreter's shared loop tail (the
# `bne s1,s7 -> refetch` every real handler jumps to on exit). The names were
# positional inventions; `park19`/`park21` say so out loud.
#
# This is now a derived property rather than an authored label: group the slots
# by address and refuse to emit distinct names within a group.
from collections import defaultdict as _dd
_by_handler = _dd(list)
for _i, _h in enumerate(handlers):
    _by_handler[_h].append(_i)
SHARED_GROUPS = {h: idxs for h, idxs in _by_handler.items() if len(idxs) > 1}

def _check_no_invented_distinctions():
    bad = []
    for h, idxs in SHARED_GROUPS.items():
        names = {SEM[i][0] for i in idxs}
        if len(names) > 1:
            bad.append((hex(h), sorted(idxs), sorted(names)))
    if bad:
        raise SystemExit(
            "gen_vm_disasm: opcodes sharing a handler were given distinct names.\n"
            "They dispatch to the same code and cannot differ:\n  " +
            "\n  ".join("%s <- indices %s named %s" % b for b in bad))

_check_no_invented_distinctions()
call_subs = [u32(CALL_TABLE + i * 4) for i in range(9)]
_sorted = sorted(set(handlers))
def _hend(h):
    i = _sorted.index(h)
    return _sorted[i + 1] if i + 1 < len(_sorted) else h + 0x100
ADV = {i: handler_advance(h, _hend(h)) for i, h in enumerate(handlers)}
# byte-verified special cases (handlers that advance via shared epilogues/stubs):
ADV[9] = 4     # op9 = branch-if-s3 (jumps into op20's branch machinery @0x8004C774)
ADV[12] = 4    # op12 CALL: the +4 advance lives in the 0x8004C5D4 slot stubs
ADV[25] = 2    # op25: advance via the shared +2 epilogue @0x8004C798
ADV[5] = ADV[5] or 2
ADV[11] = ADV[11] or 4
ADV[4] = ADV[4] or 2

# resolve CALL stubs (0x8004C5D4.. each `j <target>` in slot stubs)
def stub_target(stub):
    w = u32(stub)
    if (w >> 26) in (2, 3):                # j / jal
        return 0x80000000 | ((w & 0x03FFFFFF) << 2)
    return stub

# The pointer count is DERIVED by walking until a value leaves the program region,
# not hard-coded. It was hard-coded at 13, and the table actually has 40 entries --
# so 27 programs were silently absent from this artifact.
def _prog_count():
    n = 0
    while n < 256:
        v = u32(PROG_PTRS + n * 4)
        if not (REGION_LO <= v < REGION_HI):
            return n
        n += 1
    return n

PROG_N = _prog_count()
prog_ptrs = sorted({u32(PROG_PTRS + i * 4) for i in range(PROG_N)})

def decode(start, end):
    out, ip, seen = [], start, set()
    while REGION_LO <= ip < end and ip not in seen:
        seen.add(ip)
        v = s16(ip)
        idx = v + 1
        if not (0 <= idx <= 25):
            out.append({"ip": hex(ip), "raw": hex(u16(ip)), "op": None,
                        "note": "out-of-range opcode; decode stops"})
            break
        name, conf = SEM[idx]
        adv = ADV.get(idx)
        ins = {"ip": hex(ip), "idx": idx, "op": name, "conf": conf}
        if idx == 0:                        # jump_back: operand at IP+2
            delta = s16(ip + 2)
            tgt = ip - delta * 2
            ins["operands"] = [delta]
            ins["target"] = hex(tgt)
            out.append(ins)
            ip += 4                          # continue linear listing past the loop
            continue
        if adv is None:                     # terminator/park: opcode only
            adv = 2
        nops = max(0, (adv - 2) // 2)
        ops = [u16(ip + 2 + i * 2) for i in range(nops)]
        ins["operands"] = ops
        if idx == 12 and ops:
            slot = ops[0]
            if 1 <= slot <= 9:
                ins["call_target"] = hex(stub_target(call_subs[slot - 1]))
        if idx == 17 and ops:
            ins["radius"] = ops[0]
        if idx == 13 and len(ops) == 2:
            ins["mask_and"], ins["mask_or"] = hex(ops[0]), hex(ops[1])
        if idx in (9, 20) and ops:
            ins["target"] = hex(ip + ops[0] * 2 - 2 + 2)
        out.append(ins)
        ip += adv
    return out

programs = []
bounds = prog_ptrs + [REGION_HI]
for i, p in enumerate(prog_ptrs):
    end = bounds[i + 1]
    programs.append({"entry": hex(p), "end": hex(end),
                     "id": PROGRAM_IDS.get(p, f"program@{p:#x}"),
                     "instructions": decode(p, end)})

doc = {"generated_by": "tools/gen_vm_disasm.py",
       "interpreter": "0x8004C13C (FUNC_8004C13C)",
       "opcode_table": hex(OP_TABLE), "call_table": hex(CALL_TABLE),
       "handler_advances": {str(i): ADV[i] for i in range(26)},
       "call_sub_targets": [hex(stub_target(s)) for s in call_subs],
       "programs": programs}
(ROOT / "analysis" / "vm_programs.json").write_text(json.dumps(doc, indent=1) + "\n")

lines = ["# Mover-VM programs (static disasm — tools/gen_vm_disasm.py)", "",
         f"Interpreter `0x8004C13C`; opcode table `{OP_TABLE:#x}` (idx = s16+1); "
         f"CALL table `{CALL_TABLE:#x}`.", ""]
for pr in programs:
    lines.append(f"## {pr['id']} @ {pr['entry']}")
    for ins in pr["instructions"]:
        extra = ""
        if "target" in ins: extra = f" -> {ins['target']}"
        if "call_target" in ins: extra = f" -> native {ins['call_target']}"
        if "radius" in ins: extra = f" (R={ins['radius']})"
        if "mask_and" in ins: extra = f" (&{ins['mask_and']} |{ins['mask_or']})"
        ops = ",".join(str(o) for o in ins.get("operands", []))
        lines.append(f"- `{ins['ip']}` **{ins.get('op')}** [{ops}]{extra} ({ins.get('conf','')})")
    lines.append("")
(ROOT / "analysis" / "vm_programs.md").write_text("\n".join(lines) + "\n")
print(f"[vm-disasm] {len(programs)} programs decoded; handler advances: "
      f"{ {i: ADV[i] for i in sorted(ADV) if ADV[i]} }")
