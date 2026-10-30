---
kind: system
id: SYS_green_homing_berry
name: Green Homing Berry
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - FUNC_8005743C
  - FUNC_8005953C
  - FUNC_8005A0E0
  - FUNC_8005A308
memory:
  - MEM_80090748
  - MEM_800B0D18
  - MEM_800A6596
tables:
  - TABLE_8007941C
evidence:
  - analysis/phase4_c08_green_homing_berry.json
  - analysis/phase4_c08_bounded_exhaustion.json
  - EXP_2026-08-04_phase4_c08_green_homing_berry
src_paths:
  - src_re/green_homing_berry.c
  - src_re/berry_homing.c
---

# SYS_green_homing_berry

## Confirmed original-game behavior

- Equip index `2` creates an eight-tick type-`8` primary with subtype `5`.
- Subtype-5 terminal cleanup calls `FUNC_8005743C(primary, 1)` once. Acquisition is not a per-frame primary scan.
- Acquisition walks the NULL-terminated damageable pointer table at `0x80090748`.
- Candidates require state bit `0x0001`; state bits `0x00A0` exclude them.
- Selection minimizes squared XZ distance after each delta is shifted right five. Y is ignored and there is no range cutoff inside this routine.
- An exact distance tie replaces the earlier candidate, so the later table entry wins.
- A valid selection creates type `16` and stores the selected enemy pointer at child `+0x10`.
- With no target, no child is created; the primary becomes timer `80`, subtype `3`.
- Type `16` has timer `100`, homing flag `0x08`, connection/subtype class `3`, and damage byte `12`.
- The child turns by one signed quarter of heading error, clamps vertical correction to `[-1024,1024]`, and rebuilds XZ velocity from the sine table at `>>3` scale.
- Target `+0x6E == 0` or state mask `0x0880` stages timer `1`. The child updater never calls acquisition, so target loss retires rather than retargets.
- A hit applies exact `-2` actor-local damage even to berry-tough actors. Defeat remains temporary.
- Terminal subtype `3` decrements the owned-throw counter at `0x800A6596` once.

## Evidence boundary

The B12 retained capsule is valid shared-code corroboration, not direct C08 target-loss proof. It covers acquisition and the valid targeted-child branch but not the invalid-target expiry write. Retire-without-retarget is instruction-bound by the complete direct-xref scan and raw branch/store sequence in pristine `SCUS_942.88`.

## Phase 4 disposition

C08 is `partial (bounded-exhausted 2026-08-04)`. Remaining strict-Full work is low-return presentation/overlay breadth and exact GPU/SPU ownership, not an unresolved direct gameplay law. No Interpreter movie is currently required.
