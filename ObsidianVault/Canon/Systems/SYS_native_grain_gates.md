---
kind: system
id: SYS_native_grain_gates
name: Native grain-threshold gates
status: live_confirmed
confidence: confirmed
source_state: original_game
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-07-11_native_and_training_grain_gate
src_paths:
  - src_re/level02_grain_gate_update.c
---

# SYS_native_grain_gates

## Confirmed original-game contract

LEVEL02 contains per-gate records with a current gate state, an id, a grain
threshold, and X/Z anchors. At the gate in the operator's pristine
`level02_graingate_locked.sav`, the nearest live record is
`{4295, 26, 20, 193754, 131692}` in the nine-entry table at runtime
`0x800B4C1C` (stride `0x14`).

The live overlay reads collected grain from `0x800A65A1` at `0x800B44BC` and
compares it with the selected record's threshold. Below the threshold the gate
state and collision remain closed. At the threshold, writer `0x800B4530`
changes the state from `4295` to `4200`; writer `0x800B4624` then subtracts
`140` on the gate's update cadence. The sequence observed was
`4200, 4060, 3920, ... 1680`. Resident helper `0x80029030` consumes that state
to lower/deform the gate geometry, after which Flik can cross.

The exact denial sound/feedback branch and cadence predicate remain unresolved.
The checked-out LEVEL02 overlay bytes also differ from the overlay captured in
the supplied save, so the addresses above are explicitly live-state provenance.
See `src_re/level02_grain_gate_update.c` for the bounded partial reconstruction.

## MOD separation

TRAINING's corner cage is not original-game behavior. It reuses only this
threshold/closed/stepped-drop contract and belongs in
[[MOD_training_25_grain_corner_cage]]. Its geometry, threshold `25`, collision
plane, RAW-resident C, plaque, and private state are MOD-owned.

See [[EXP_2026-07-11_native_and_training_grain_gate]].

## Phase 4 E09 bounded exhaustion (2026-08-02)

The Phase 4 row-specific frontier is now closed by validated trace-capsule reconstruction
and C-decoded live-overlay ASM. Strict row status remains `partial`; see
[[EXP_2026-08-02_phase4_e09_bounded_exhaustion]] and
`analysis/phase4_e09_bounded_exhaustion.json` for the nine-item scorecard.

### LEVEL02 authored census and exact rules

- Nine records live at `0x800B4C1C`, stride `0x14`: `{state,id,threshold,x,z}`.
- Thresholds in table order are `20,10,10,10,20,20,30,10,30`; exact IDs and positions
  are preserved in `analysis/phase4_e09_static.json`.
- `0x800B44BC` accepts `grain >= record.threshold`.
- Success additionally requires planar fixed-point distance squared `<10000`, dispatches
  SFX 63, writes `4295 -> 4200`, then steps by `-140` to terminal 1680.
- Five capsule openings independently show all 19 transitions at two-frame cadence.
- Records 0 and 4 are paired: opening either also opens the other.
- Insufficient-grain feedback requires the tighter distance squared `<1600`, calls
  `0x80050C40` with ID 76, and arms `0x800B4D10 = next_cursor_byte + 60`.
- The cooldown decrements once per positive overlay update, normally every two emulator
  frames. This closes the former denial-feedback/cadence unknown.
- `0x80029030` is the geometry transform helper. The gate path passes
  `(object_id,4200,new_state,4200)` and applies authored fixed-point coefficients.

### LEVEL07 is a distinct three-gate implementation

- Function `0x800B3D84` owns three states at `0x800B4570`; closed is `-1`.
- Threshold is computed as `10*(index+1)`, giving 10, 20, and 30.
- `0x800524B8` performs planar squared-distance `< radius^2`; the three authored radii
  are 80, 90, and 100. Exact positions, object pairs and deltas are in the static JSON.
- Success dispatches SFX 63, writes 32, decrements toward 0, and translates two geometry
  channels per update through `0x800292DC`.
- Denial uses the same ID-76/cursor-byte-plus-60 design at `0x800B456C`.
- Retained LEVEL07 capsules are one-short controls at grain 9/19/29. They prove denial,
  not successful `32 -> 0` completion; that remaining behavioral boundary is explicit.

### Evidence boundary

Twelve capsules reconstruct 12,239 frame records with 36,717 RAM/VRAM/SPU hash checks
and zero mismatches, and all match independent controls in the central preservation set.
They are frame-boundary evidence. No claim of every-cycle capture or strict Phase 4
promotion is made.
