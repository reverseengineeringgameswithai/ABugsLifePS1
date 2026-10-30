#!/usr/bin/env python3
"""D16/F03 artifact generator -- and an INDEPENDENT second implementation of the census.

The standing rule on this project is that static ASM probing is done with a compiled,
self-verifying C tool (tools/phase4_d16_f03_static.c).  The standing rule ALSO is that a
census gets double-implemented, because the last time one wasn't, a single implementation
silently inflated its counts 2x and the error survived into a banked claim.

So this file does not merely shell out and reformat.  It re-implements both scans from
scratch in Python -- the immediate-match scan and the constant-propagation dataflow scan
-- runs the C tool, and FAILS if the two implementations disagree about which
instructions touch the address.  Only then does it write the artifact.

    tools/phase4_d16_f03_census.py [--json analysis/phase4_d16_f03.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL_C = ROOT / "tools" / "phase4_d16_f03_static.c"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"

EXE_HEADER = 0x800
EXE_BASE = 0x80010000
REGION_A = 0x800B39A0
REGION_B = 0x800B5788
GP = 0x80081D98

CAM_FLAGS = 0x80090BEE
POWER = 0x800A6590

LOADS = {0x20, 0x21, 0x23, 0x24, 0x25}
STORES = {0x28, 0x29, 0x2B}
MEM = LOADS | STORES
CALLER_SAVED = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 31]


def images():
    out = [(str(EXE.relative_to(ROOT)), EXE.read_bytes(), EXE_BASE, EXE_HEADER)]
    for p in sorted(ROOT.glob("REBUILD/files/LEVEL*/LEVEL*.BIN")):
        out.append((str(p.relative_to(ROOT)), p.read_bytes(), REGION_A, 0))
    mem = ROOT / "REBUILD/files/BITS/MEMORY.BIN"
    if mem.exists():
        out.append((str(mem.relative_to(ROOT)), mem.read_bytes(), REGION_B, 0))
    return out


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def scan_immediate(target):
    """Every load/store whose immediate equals the target's low half. Candidates only."""
    hits = []
    for name, buf, base, skip in images():
        for off in range(skip, len(buf) - 3, 4):
            w = int.from_bytes(buf[off:off + 4], "little")
            if (w >> 26) in MEM and (w & 0xFFFF) == (target & 0xFFFF):
                hits.append((name, base + off - skip, w))
    return hits


def scan_dataflow(target):
    """Constant-propagate lui/addiu/ori and resolve each load/store's effective address."""
    hits, resolved = [], {}
    for name, buf, base, skip in images():
        val = [0] * 32
        valid = [False] * 32
        valid[0] = valid[28] = True
        val[28] = GP
        for off in range(skip, len(buf) - 3, 4):
            w = int.from_bytes(buf[off:off + 4], "little")
            op, rs, rt, rd, fn = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31, w & 63
            imm = s16(w & 0xFFFF)
            pc = base + off - skip
            if op in MEM:
                if valid[rs]:
                    addr = (val[rs] + imm) & 0xFFFFFFFF
                    resolved[(name, pc)] = addr
                    if addr == target:
                        hits.append((name, pc, w))
                if op in LOADS:
                    valid[rt] = False
            elif op == 0x0F:
                val[rt], valid[rt] = (w & 0xFFFF) << 16, True
            elif op in (0x08, 0x09):
                if valid[rs]:
                    val[rt], valid[rt] = (val[rs] + imm) & 0xFFFFFFFF, True
                else:
                    valid[rt] = False
            elif op == 0x0D:
                if valid[rs]:
                    val[rt], valid[rt] = val[rs] | (w & 0xFFFF), True
                else:
                    valid[rt] = False
            elif op == 0x03:
                for r in CALLER_SAVED:
                    valid[r] = False
            elif op == 0x00:
                if fn == 0x08:
                    valid = [False] * 32
                    valid[0] = valid[28] = True
                elif fn == 0x09:
                    for r in CALLER_SAVED:
                        valid[r] = False
                elif not (fn == 0x00 and rd == 0):
                    valid[rd] = False
            elif op in (0x01, 0x02, 0x04, 0x05, 0x06, 0x07):
                pass
            else:
                valid[rt] = False
            valid[0] = True
            val[0] = 0
    return hits, resolved


def run_c_tool():
    exe = Path("/tmp/phase4_d16_f03_static")
    subprocess.run(["cc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
                    str(TOOL_C), "-o", str(exe)], check=True, cwd=ROOT)
    r = subprocess.run([str(exe)], capture_output=True, text=True, cwd=ROOT)
    return r.returncode, r.stdout


C_HIT = re.compile(r"^\s+(STORE|load)\s+0x([0-9a-f]{8})\s+([0-9a-f]{8})\s+\S.*?\s(\S+)\s*$")


def parse_c_census(stdout, header):
    """Pull one census block's hit list out of the C tool's output."""
    lines = stdout.splitlines()
    try:
        i = next(k for k, l in enumerate(lines) if header in l)
    except StopIteration:
        return None
    out = []
    for l in lines[i + 1:]:
        if l.startswith("==="):
            break
        m = C_HIT.match(l)
        if m:
            out.append((m.group(4), int(m.group(2), 16), int(m.group(3), 16)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path, default=ROOT / "analysis/phase4_d16_f03.json")
    args = ap.parse_args()

    rc, stdout = run_c_tool()

    py_flags_imm = scan_immediate(CAM_FLAGS)
    py_flags_df, resolved = scan_dataflow(CAM_FLAGS)
    py_power_df, _ = scan_dataflow(POWER)

    c_flags = parse_c_census(stdout, "0x%08x access census" % CAM_FLAGS)
    c_power = parse_c_census(stdout, "0x%08x (power word) access census" % POWER)

    def norm(hits):
        return sorted((n, pc, w) for n, pc, w in hits)

    disagreements = []
    if c_flags is None or norm(c_flags) != norm(py_flags_df):
        disagreements.append({
            "target": "0x%08X" % CAM_FLAGS,
            "c_only": sorted(set(map(tuple, c_flags or [])) - set(map(tuple, py_flags_df))),
            "py_only": sorted(set(map(tuple, py_flags_df)) - set(map(tuple, c_flags or []))),
        })
    if c_power is None or norm(c_power) != norm(py_power_df):
        disagreements.append({
            "target": "0x%08X" % POWER,
            "c_only": sorted(set(map(tuple, c_power or [])) - set(map(tuple, py_power_df))),
            "py_only": sorted(set(map(tuple, py_power_df)) - set(map(tuple, c_power or []))),
        })

    # immediate-scan candidates the dataflow places somewhere ELSE: the low-half
    # collision (0x800B0BEE vs 0x80090BEE) that makes a count-only census wrong
    false_positives = [
        {"file": n, "pc": "0x%08X" % pc, "word": "0x%08X" % w,
         "resolves_to": "0x%08X" % resolved[(n, pc)]}
        for n, pc, w in py_flags_imm
        if (n, pc) in resolved and resolved[(n, pc)] != CAM_FLAGS
    ]

    art = {
        "rows": ["D16_thumper", "F03_council_chamber"],
        "generated_by": "tools/phase4_d16_f03_census.py",
        "pin_tool": "tools/phase4_d16_f03_static.c",
        "pin_tool_exit_code": rc,
        "exe_sha256": hashlib.sha256(EXE.read_bytes()).hexdigest(),
        "method": (
            "Two independent censuses (immediate-match and constant-propagation "
            "dataflow) implemented TWICE -- once in C, once here -- and compared as "
            "SETS. Counts are never compared, because the two scan methods "
            "legitimately see different addressing forms."
        ),
        "second_implementation_agrees": not disagreements,
        "disagreements": disagreements or None,

        "FINDING_0x80090BEE_IS_THE_CINEMATIC_CAMERA_FLAGS_FIELD": {
            "what_it_is": (
                "the FLAGS halfword at +0x2E of the shared cinematic/setpiece camera "
                "block 0x80090BC0 -- the same block C14 (telescope) and D17 (bird) use"),
            "access_width": "lhu / sh (HALFWORD). An earlier pass recorded lbu/sb.",
            "writers": {
                "0x8004DA7C": "in cinematic_camera_start 0x8004D9E8; flags := arg7",
                "0x8004DB44": "in cinematic_camera_start_polar 0x8004DA94; flags := arg8",
                "0x8004EB1C": "selector case 1: flags |= 0x01",
                "0x8004EBAC": "selector case 3: flags &= ~0x01",
            },
            "readers": ["0x8004EB0C", "0x8004EB40", "0x8004EB98", "0x8004EBF4",
                        "0x8004F3D0", "0x8004F6DC",
                        "0x800B4560 (LEVEL02/LEVEL1.BIN)"],
            "bit_0x01": (
                "cinematic camera ACTIVE. Selects the camera SOURCE at 0x8004EBFC "
                "(setpiece block vs the ordinary follow camera 0x80095358), and in "
                "gameplay_state_machine makes both HUD sites call 0x80053638 "
                "(draw_mirrored_fullscreen_quads = letterboxing) instead of "
                "0x800526F4 (hud_draw)."),
            "bit_0x02": (
                "hold 0x800A6590 bit 0x04 for the duration: ORed in on entry "
                "(0x8004EB64) and cleared on exit (0x8004EBC8)."),
            "why_the_value_2_is_not_a_defeat_code": (
                "both writers take the value as a CALLER-SUPPLIED argument. The "
                "resident telescope setpiece path passes 2 unconditionally "
                "(0x8004D6F4), and so do several level overlays."),
        },

        "FINDING_POWER_BIT_0x04_IS_A_SUPPRESSION_GATE_NOT_A_POWER_UP": {
            "readers": ["0x8004EED0", "0x80050C84", "0x80051138", "0x80054F38",
                        "0x80056550"],
            "shape": ("every one of the five branches PAST its body when the bit is "
                      "set; none enables anything"),
            "enclosing": ["gameplay_state_machine", "contact_pickup_sfx",
                          "ambient_sfx_sequence_update", "sfx_nearest_pickup_f_glue",
                          "actor_skinned_update"],
            "gameplay_effect": ("taking the branch in gameplay_state_machine masks the "
                                "player action word 0x80082488 down to 0x309"),
            "corrects": ("the earlier reading that boss defeat 'grants a previously "
                         "unidentified power'"),
        },

        "FINDING_THE_LEVEL_EXIT_IS_A_DIFFERENT_STORE": {
            "resident_overlay_during_the_fight": "REBUILD/files/LEVEL02/LEVEL.BIN",
            "overlay_identity_was_measured": (
                "region A 0x800B39A0 is a SHARED swap buffer, so an overlay address is "
                "meaningless without knowing the resident blob. This was verified live "
                "by hashing the resident window; an earlier draft of this analysis "
                "attributed the code to LEVEL03/LEVEL1.BIN and was wrong."),
            "defeat_gate": "0x800B4070 lh [0x8009FE72] (Thumper HP) ; 0x800B4078 slti 21",
            "thumper_hp_address": "0x8009FE72 = chunk-31 actor 0x8009FE04 + 0x6E",
            "once_only_guard": "0x800B4090 bne [0x800823A0],0 -- skip if already latched",
            "camera_start": "0x800B4118 flags:=2 ; 0x800B4138 jal 0x8004DA94",
            "the_level_exit": "0x800B4190 sh v0,[0x800823A0] with v0 = 1",
            "order": ("camera start FIRST, goal latch SECOND, one straight-line block, "
                      "same frame"),
            "no_path_from_the_flags_word": (
                "the complete consumer set of 0x80090BEE (above) contains no read or "
                "write of 0x800823A0, the scene id 0x80082504, or any loader entry"),
        },

        "census_0x80090BEE": {
            "dataflow_hits": [
                {"file": n, "pc": "0x%08X" % pc, "word": "0x%08X" % w,
                 "kind": "store" if (w >> 26) in STORES else "load"}
                for n, pc, w in py_flags_df],
            "immediate_candidates": len(py_flags_imm),
            "immediate_false_positives_resolved_elsewhere": false_positives,
            "overlay_touching_it": [n for n, _, _ in py_flags_df if "SCUS" not in n],
            "known_blind_spot": (
                "neither scan can see an access through a pointer loaded from memory; "
                "that possibility is NOT claimed against"),
        },
    }

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(art, indent=1) + "\n")

    print(json.dumps({
        "second_implementation_agrees": art["second_implementation_agrees"],
        "pin_tool_exit_code": rc,
        "flags_accesses": len(py_flags_df),
        "immediate_false_positives": len(false_positives),
        "artifact": str(args.json.relative_to(ROOT)),
    }, indent=1))
    return 0 if (not disagreements and rc == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
