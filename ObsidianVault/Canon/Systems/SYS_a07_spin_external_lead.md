---
kind: system
id: SYS_a07_spin_external_lead
name: A07 directional spin recognizer
status: partial
confidence: confirmed
updated: 2026-08-04
---

# A07 directional spin recognizer

The external lead is resolved. The pristine game recognizes two clockwise exact
cardinal rotations:

`Up, Right, Down, Left, Up, Right, Down, Left`.

The table-driven branch is `0x800481C4..0x800483AC` inside
[[FUNC_80048138_player_vertical_update]]. It maintains eight `u16` history entries
at `0x800894D0`, next index `0x800823B0`, and inactivity counter `0x8008229A`.
The sole reference table at `0x80077304` contains
`{0x10,0x20,0x40,0x80}` twice.

Only a changed full pad word equal to one cardinal is admitted. Diagonals and a
cardinal combined with any action button are ignored. Twenty non-admitted player
ticks append zero and invalidate a stale match. Spawn clears the full ring and both
counters at `0x80046B34..0x80046B60`.

All eight entries must match and `player+0x90 & 0x80` must be clear. Admission:

- requests animation 13 without creating a new `player+0x80` mode;
- arms shared timer `0x80082294=120` when entering clip 13;
- clears action lock `+0x7A`, carried offset `+0x5C`, seed mode `+0xA3`, and
  queued action `+0x9E`;
- stops/releases a selected carried actor and calls byte-matched
  [[FUNC_80041A74]] to clear an indexed attachment.

The complete entry block has no attack, damage, unlock, save, or persistent cheat
write. Animation 13 is also used by the propeller path. Its shared actor-update tail
retains the clip while motion remains above the two 64-unit checks and periodically
calls `0x80050C40` with SFX ID 64 after the timer expires.

The Interpreter movie confirms branch windows 133..145 and 209..247. The second is
the exact 20-tick timeout control. Input becomes neutral at 848; ordinary idle 22 is
first requested at 851 and committed at 857 after motion decays.

## Confidence and MOD contract

The recognizer, state, gates, entry effects, timeout, spawn reset, animation latch,
and recovery are confirmed. A07 remains a substantiated Partial rather than strict
Full because the live escalation was not predeclared in the Phase 4 ledger, and the
no-seed/no-enemy movie does not cover carried-seed presentation or an incidental
enemy-contact effect.

Safe consumers may rely on the exact table/ring contract and on animation 13 not
being unique to spin. They must not repurpose the ring, counters, timer, animation
13, carry cleanup, `+0x90` bit `0x80`, or attachment reset independently. They must
not describe the move as a proven damaging attack or persistent cheat.

Authoritative evidence:

- `analysis/phase4_a07_spin.json`
- `tools/phase4_a07_static.c`
- `src_re/spin_directional_80048138.c` (documentation-grade, not matching)
- [[EXP_2026-08-04_phase4_a07_spin]]
- `analysis/phase3_spin_functional.json` and
  `analysis/phase2_spin_disproof.json` (superseded bounded-negative history)
- [[EXP_2026-07-13_a07_spin_move_disproof]] (superseded conclusion, retained method)
