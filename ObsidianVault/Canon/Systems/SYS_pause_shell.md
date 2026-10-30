---
kind: system
id: SYS_pause_shell
name: Pause Shell
status: substantiated_partial
confidence: confirmed_core_bounded_residuals
source_state: original_game
functions:
  - FUNC_8004ECD4
  - FUNC_8004F478
  - FUNC_8004F480
memory:
  - MEM_8008224E
evidence:
  - EXP_2026-08-03_phase4_a18_pause
  - analysis/phase4_a18_pause.json
  - tools/phase4_a18_static.c
---

# SYS_pause_shell

## Canon contract

`s16 0x8008224E` selects gameplay versus the pause shell:

- zero: execute `gameplay_state_machine` at `0x8004ECD4`
- nonzero: execute pause render/input at `0x8004F478`/`0x8004F480`

Both paths retain the outer presentation tail. Pause is therefore a game-owned
alternate scheduler, not a frozen emulator.

## Admission

Pause requires a rising START edge in current/previous input halfwords
`0x80082412` and `0x800822E4`, plus numeric gates:

- `0x800822F8 == 0`
- `0x8008216C == 3`
- `0x80082388 == 0x80`

`0x8004F3AC` writes pause value one and initializes the menu to resume.

## Freeze ownership

The resident scheduler omits player physics, actors, movers, HUD animation,
contact objects/projectiles, and plants while paused. Matched pristine runtime
controls confirm exact stability of the canonical actor/contact pools, plant and
HUD samples, camera, and established player simulation fields.

Scene presentation and pause-menu rendering continue. A settled 60-frame pause
diff changes only the menu region in the measured fixture.

## Audio boundary

XA/CD read position stops while paused. Pause-menu SFX remain available and
`_SsVmFlush` continues low-level sound servicing. Its modulo-16 cursor is
`0x800A65A8`; this address is adjacent to player state but is not player
simulation ownership.

Exact per-voice SPU behavior remains open because the pinned debugger binary
does not implement the SPU method advertised by its dirty source/docs.

## Menu lifecycle

The main menu uses `0x80082472`: zero resumes, one enters exit confirmation.
Confirmation uses `0x800824BC`: one is cancel and two is exit.

Resume clears the pause flag at `0x8004F858`.

Confirmed exit writes:

- pause zero at `0x8004F9C0`
- shell flow state five at `0x8004F9E4`
- transition timer 23 at `0x8004F9FC`
- player flags OR `0x0004` at `0x8004FA1C`

## Bounded residuals

- boss, FMV, telescope, and special-overlay pause admission breadth
- exact per-voice SPU and host-output evolution
- semantic names for the three numeric admission gates
- every authored combination of active actors, projectiles, plants, and streams

These residuals do not block moving on from Phase 4 A18.

## Evidence

- [[EXP_2026-08-03_phase4_a18_pause]]
- `analysis/phase4_a18_pause.json`
- `config/phase4_a18_pause.yaml`
- `src_re/pause_shell_8004ecd4_8004f480.c`
- `tools/phase4_a18_static.c`
