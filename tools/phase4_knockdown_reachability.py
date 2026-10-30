#!/usr/bin/env python3
"""Decide the knockdown store 0x8004AFB0: is it reachable, and what does it target?

WHY THIS EXISTS
---------------
DoD item 4 (lifecycle) for rows B06/B08 was held open by one site. An earlier revision
said `0x8004AFB0` cleared the power slot and had never executed in the fixture corpus.
Both claims were wrong: it executes naturally, and the pristine address chain proves
that it stores to player+0x82, four bytes past the power slot.

An earlier attempt poked `player+0x7C := 17` before a known contact and the site still
did not fire, which was read as evidence the divert was upstream of player state. It
was: the branch that decides this is `0x8004AEBC`, and it tests a DIFFERENT field.

WHAT THE DISASSEMBLY SETTLES
---------------------------
Two facts that change the model:

1. `0x8004AFB0  sh zero, 0x7e(fp)` sits in the DELAY SLOT of `jal play_sound` at
   `0x8004AFAC`. It is part of the knockdown reaction's tail and executes
   unconditionally once the reaction is entered.

2. `fp` is the player block PLUS FOUR. The image explicitly materializes
   `v1 = 0x800A6500` at `0x8004AC18/1C`, then executes
   `0x8004AC70 addiu fp,v1,4`. Therefore `fp+0x7E = 0x800A6582`, not the power slot
   at `0x800A657E`. The former "runtime object pointer" account was also wrong.

   Runtime corroborates the static address calculation: with the slot poked live to
   400, the store executed at frame 5966 and the tick kept decrementing straight through
   it (381 -> 380 -> 379), so `0x800A657E` was never written.

THE REACHABILITY ARGUMENT
-------------------------
The chain looks self-contradictory at first read, which is why it was called unreachable:
`0x8004AF34` requires `actor+0x5E != 0`, but the block at `0x8004AED4..0x8004AEF8` --
which runs exactly when `actor+0x5E != 0` -- sets `actor+0x6C := 10`, and `0x8004AF04`
then diverts on `actor+0x6C != 0`. Along THAT path the knockdown is indeed unreachable.

It is reachable along the other one. `0x8004AEBC  bne v1, v0, 0x8004AEFC` (with
`v1 = player+0x84`, `v0 = 1`) jumps straight to `0x8004AEFC` when `player+0x84 != 1`,
BYPASSING the `actor+0x6C := 10` write. `actor+0x6C` then holds whatever it held, and
if it is zero the fall-through continues into the knockdown chain with `actor+0x5E != 0`
still satisfiable.

So the site is REACHABLE, and this tool emits the exact state that reaches it -- which is
the fixture recipe item 4 needs, and the thing to falsify at runtime.

USAGE
    tools/phase4_knockdown_reachability.py
    tools/phase4_knockdown_reachability.py --json analysis/phase4_knockdown_path.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import census_address as ca  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLEAR = 0x8004AFB0
PLAYER = 0x800A6500

# Each entry: (pc, what it reads, the condition REQUIRED to reach the store)
GUARDS = [
    (0x8004AE9C, "actor+0x5C & 0x20", "!= 0",
     "beq -> 0x8004B0C4 when clear; bit 0x20 of the actor flag word must be SET"),
    (0x8004AEA8, "actor+0x5C & 0x40", "== 0",
     "bne -> 0x8004B67C when set; bit 0x40 must be CLEAR"),
    (0x8004AEBC, "player+0x84", "!= 1",
     "THE DECIDING BRANCH. bne v1,1 -> 0x8004AEFC takes the path that BYPASSES the "
     "actor+0x6C := 10 write. When player+0x84 == 1 the fall-through path writes "
     "actor+0x6C := 10 (if actor+0x5E != 0) and 0x8004AF04 then diverts, making the "
     "clear unreachable. This is the guard the earlier probe never controlled."),
    (0x8004AF04, "actor+0x6C", "== 0",
     "bne -> 0x8004B67C; must be zero on entry, which the bypass preserves"),
    (0x8004AF18, "player+0x00 < actor+0x08", "true",
     "slt/beq -> 0x8004B054; a positional test between the player and the actor"),
    (0x8004AF2C, "player+0x9F", "== 0",
     "bne -> 0x8004B054"),
    (0x8004AF3C, "actor+0x5E", "!= 0",
     "beq -> 0x8004AFC0; the actor-side knockdown enable"),
    (0x8004AF4C, "player+0x2C", ">= 0",
     "bltz -> 0x8004AFC0; player vertical velocity must not be negative (not rising)"),
    (0x8004AF5C, "player+0x7C", "!= 0",
     "beq -> 0x8004AFBC; the player must already be in an action-locked state"),
    (0x8004AF6C, "player+0x84", "!= 17",
     "beq -> 0x8004AFBC; combined with 0x8004AEBC this pins player+0x84 to a value "
     "that is neither 1 nor 17"),
]

EFFECTS = [
    (0x8004AF7C, "actor+0x6C  := 10"),
    (0x8004AF8C, "actor+0x50  := actor+0x08 & ~1"),
    (0x8004AF94, "player+0x2C := -1536   (launched upward -- the knockback)"),
    (0x8004AF9C, "player+0x84 := 3"),
    (0x8004AFA4, "player+0x7C := 5       (hit-reaction action state)"),
    (0x8004AFA8, "player+0x80 := 0"),
    (0x8004AFAC, "jal play_sound(-15, actor+4)"),
    (0x8004AFB0, "player+0x82 := 0       (jal delay slot; NOT the power slot)"),
    (0x8004AFB4, "j 0x8004B67C"),
]


def verify_against_image(exe: Path, functions: Path) -> dict:
    """Re-derive the two structural claims from the pristine image."""
    img = ca.Image(exe, functions)
    out = {}

    w = img.word(0x8004AFAC)
    out["store_is_in_a_jal_delay_slot"] = (w >> 26) == 3
    out["jal_target"] = "0x%08X" % ((0x8004AFAC & 0xF0000000) | ((w & 0x3FFFFFF) << 2))

    # sh zero, 0x7e(fp): op 0x29, rt = zero, imm = 0x7e
    c = img.word(CLEAR)
    out["store_insn_is_sh_zero_0x7e_fp"] = (
        (c >> 26) == 0x29 and ((c >> 16) & 31) == 0 and (c & 0xFFFF) == 0x7E)

    base_lui = img.word(0x8004AC18)
    base_addiu = img.word(0x8004AC1C)
    fp_addiu = img.word(0x8004AC70)
    base = ((base_lui & 0xFFFF) << 16) + ca.s16(base_addiu & 0xFFFF)
    fp = base + ca.s16(fp_addiu & 0xFFFF)
    out["player_base_materialization_is_pinned"] = (
        base_lui == 0x3C03800A and base_addiu == 0x24636500)
    out["fp_plus_four_is_pinned"] = fp_addiu == 0x247E0004
    out["fp"] = "0x%08X" % fp
    out["store_effective_address"] = "0x%08X" % (fp + 0x7E)
    out["store_avoids_power_slot"] = (fp + 0x7E) != 0x800A657E

    # The absolute read at 0x8004AEB4 is of the PLAYER's +0x84, used as a global. It says
    # This absolute read corroborates the independently pinned player-base chain above.
    lui = img.word(0x8004AEB0)
    lh = img.word(0x8004AEB4)
    abs_ea = ((lui & 0xFFFF) << 16) + ca.s16(lh & 0xFFFF)
    out["absolute_read_at_0x8004AEB4"] = "0x%08X" % abs_ea
    out["that_read_is_player_plus_0x84"] = (abs_ea - 0x84) == PLAYER
    out["CORRECTION_fp_base"] = (
        "An earlier revision called fp a runtime object pointer and treated this as a "
        "possible power-slot clear. The image pins v1=0x800A6500 and fp=v1+4, so the "
        "store always lands at player+0x82.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", type=Path, default=ROOT / "REBUILD" / "files" / "SCUS_942.88")
    ap.add_argument("--functions", type=Path, default=ROOT / "analysis/functions.json")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    checks = None
    if args.exe.exists():
        checks = verify_against_image(args.exe, args.functions)
        bad = [k for k, v in checks.items() if v is False]
        if bad:
            print("STRUCTURAL CHECK FAILED:", bad)
            return 1
        print("structural checks against the pristine image: OK")
        for k, v in checks.items():
            print("   %-36s %s" % (k, v))
    else:
        print("(pristine EXE absent -- structural checks skipped; static path below is "
              "the recorded derivation)")

    print("\nGUARD CHAIN -- every condition must hold to reach 0x%08X" % CLEAR)
    for pc, reads, need, why in GUARDS:
        print("  0x%08X  %-26s %-6s  %s" % (pc, reads, need, why.split(";")[0]))

    print("\nEFFECTS once entered (all unconditional):")
    for pc, eff in EFFECTS:
        print("  0x%08X  %s" % (pc, eff))

    out = {
        "_comment": "Reachability and target of knockdown store 0x8004AFB0. "
                    "Regenerate: tools/phase4_knockdown_reachability.py",
        "clear_site": "0x%08X" % CLEAR,
        "function": "actor_player_contact_resolver (0x8004ABF4)",
        "verdict": "REACHABLE. The chain is only self-contradictory along the path where "
                   "player+0x84 == 1; the branch at 0x8004AEBC takes the other path, "
                   "which bypasses the actor+0x6C := 10 write and leaves actor+0x5E "
                   "free to be non-zero.",
        "structural_checks": checks,
        "guards": [{"pc": "0x%08X" % pc, "reads": r, "required": n, "note": w}
                   for pc, r, n, w in GUARDS],
        "effects": [{"pc": "0x%08X" % pc, "effect": e} for pc, e in EFFECTS],
        "why_earlier_probes_missed_it":
            "The earlier attempt poked player+0x7C := 17 to satisfy 0x8004AF5C, but never "
            "controlled player+0x84, which 0x8004AEBC tests against 1. It also never "
            "controlled the actor-side fields (0x5C bits, 0x5E, 0x6C). With player+0x84 "
            "== 1 the clear is genuinely unreachable, so the probe was measuring the "
            "wrong path and the zero-event execTrace was consistent with that.",
        "runtime_confirmation":
            "Historical oracle: at a known contact, set player+0x84 to a value that is "
            "neither 1 nor 17, player+0x7C non-zero, player+0x2C >= 0, player+0x9F == 0, "
            "actor+0x5E non-zero, actor+0x6C == 0, actor+0x5C with bit 0x20 set and bit "
            "0x40 clear; then watch 0x8004AFB0 for execution and confirm there is NO "
            "write to the slot. Confirm player+0x2C == -1536 and player+0x7C == 5 "
            "afterwards, which distinguishes a real knockdown from an incidental event.",
    }
    if args.json:
        args.json.write_text(json.dumps(out, indent=1) + "\n")
        print("\nwrote", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
