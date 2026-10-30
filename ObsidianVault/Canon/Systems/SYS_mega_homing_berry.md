---
kind: system
id: SYS_mega_homing_berry
name: Purple Mega Homing Berry
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - FUNC_80047170
  - FUNC_8005743C
  - FUNC_8005905C
  - FUNC_8005953C
  - FUNC_8005A0E0
  - FUNC_8005A308
memory:
  - MEM_80090748
  - MEM_800A6596
  - MEM_800B0D18
tables:
  - TABLE_8007941C
evidence:
  - analysis/phase4_c09_mega_homing_berry.json
  - analysis/phase4_c09_bounded_exhaustion.json
  - EXP_2026-08-04_phase4_c09_mega_homing_berry
src_paths:
  - src_re/mega_homing_berry.c
---

# SYS_mega_homing_berry

## Confirmed original-game behavior

- Equip index `4` creates timer-8 primary type `45`, subtype `9`.
- Subtype 9 calls shared nearest-valid-XZ acquisition once with mode `0`.
- A selected target is handed to timer-100 child type `48`, subtype `8`.
- With no target, the primary becomes timer `80`, subtype `8`.
- Mega and green have identical launch, acquisition, turn rate, vertical clamp, sine/8 velocity scale, target-loss law, and primary/child lifetimes.
- Mega is not faster than green. Its mechanical strength difference is damage.
- Damage selector `128` applies exact `-3` versus green selector `12` exact `-2`.
- Mega damages berry-tough actors and produces temporary, not permanent, defeat.
- Target invalidity stages timer `1`; the updater has no reacquisition call, so the projectile retires without retargeting.
- Terminal subtype `8` decrements `0x800A6596` exactly once.

## Presentation boundary

Mega uses model `124`, secondary kind `13`, and presentation bytes `[0x20,0x80]`; green uses model `123`, secondary kind `12`, and `[0x60,0x00]`. The byte copies are instruction-confirmed, but exact GPU/SPU semantics remain deferred.

## Phase 4 disposition

C09 is `partial (bounded-exhausted 2026-08-04)`. Direct native mechanics are closed; remaining work is low-return presentation and overlay breadth. No Interpreter movie is currently required.
