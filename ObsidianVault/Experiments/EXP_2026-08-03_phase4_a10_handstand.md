---
kind: experiment
id: EXP_2026_08_03_phase4_a10_handstand
status: bounded_exhausted
created: 2026-08-03
updated: 2026-08-03
confidence: high
related:
  - PLAYBOOK_game_solving_phase_4
  - SYS_fixed_seed_handstand
  - SYS_seed_carry_plant_lifecycle
---

# Phase 4 A10 - fixed-seed handstand

## Question

Close the earlier A10 gaps without assuming that the surviving actor-coordinate
scan identified the support: bind the selected object, mount writer, sustained
latch, release, state-6 dismount, landing, and camera implication.

## Evidence accepted first

Retained capsule:

`~/Downloads/ABL-external-evidence/trace-capsules/Phase4/a10-a11-v2-20260719/Phase_Helpers__carry_handstand`

- manifest SHA-256:
  `5188a58af0c5c347b5f2a7685e12748631686823edf78ad15c2649d716f02a26`
- movie SHA-256:
  `65d344960a2c14b828a800bebd8ae0a9af30ba24db4b6822f48a630e7f46901c`
- state SHA-256:
  `faa1874797000bb5d9b9581ddeca8a6a28abff33e762cd1df4e4fc113b19b3b2`
- pristine serial `SCUS-94288`
- 1,359 frame boundaries, movie 0..1358, emulator 9861..11219
- 337,948,228 instructions and 50,130,818 passive blocks
- complete true, truncated false, error empty
- independent-control mismatches `{}` across cycles, frames, registers, RAM,
  VRAM, SPU RAM, and full machine state

The capsule was forced to CachedInterpreter. It is accepted for exact
frame-boundary reconstruction and passive block flow only. It is not an
instrumented replay claim.

## Native C reduction

The reducers reconstructed and hash-checked every RAM/VRAM/SPU frame, then
reduced the relevant input, player, actor, flow, and camera windows.

```bash
gcc -O2 -std=c11 -Wall -Wextra -o /tmp/phase4_a10_capsule \
  tools/phase4_a10_capsule.c -lzstd -lcrypto
/tmp/phase4_a10_capsule "$CAPSULE"

gcc -O2 -std=c11 -Wall -Wextra -o /tmp/phase4_a10_support \
  tools/phase4_a10_support.c -lzstd
/tmp/phase4_a10_support "$CAPSULE"

gcc -O2 -std=c11 -Wall -Wextra -o /tmp/phase4_a10_flow_diff \
  tools/phase4_a10_flow_diff.c -lzstd
/tmp/phase4_a10_flow_diff "$CAPSULE"

gcc -O2 -std=c11 -Wall -Wextra -o /tmp/phase4_a10_camera \
  tools/phase4_a10_camera.c -lzstd
/tmp/phase4_a10_camera "$CAPSULE"
```

Transient reducer/output hashes are preserved in
`analysis/phase4_a10_capsule.json`.

## Observation

### Positive and negative mount

- Movie frames 1024..1039 are a native proximity/no-Square control: mode 0,
  selected offset 0, grounded, and no mount.
- Square begins at 1040; the mount is committed at 1042.
- Player `+0x5C` becomes `0x108`, selecting actor `0x8009FE88` from base
  `0x8009FD80`.
- The selected actor has source pointer `0x80094A70`, behavior `+0x40 = 3`, and
  mounted flags `+0x5C = 0x4071`.
- Player `+0xA3` becomes mode 14.

### Sustained mount

- Mode 14 spans 1042..1215: 174 frame boundaries.
- Player XYZ is exactly constant for 1102..1215: 114 frame boundaries.
- Grounded remains zero while mounted.
- No Square edge occurs during the sustained hold, and no automatic release is
  observed.

### Release and landing

- Square begins at 1213; release commits at 1216.
- The selected offset and mode clear and vertical state becomes 5.
- State 6 begins at 1222 and lasts through 1253 (32 boundaries).
- Grounded becomes nonzero at 1252; the vertical state returns to 0 at 1254.

### Camera

The normal camera record continues updating. Camera target is stable at
1054..1105 and again at 1166..1221, while camera position continues converging.
There is no full-camera freeze and no persistent camera field introduced by the
handstand.

## Static causal binding

Pristine hashes:

- `REBUILD/files/SCUS_942.88`:
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- `REBUILD/files/LEVEL01/LEVEL.BIN`:
  `f3b1bef4db67bb10a58ace167941f6e2becc4d8303756a58b5d0ba7601df1c21`

The resident mount path loads actor behavior `+0x40` at `0x8004785C`. The
threshold at `0x80047864` selects mode 8 for values below 3 and mode 14 at
`0x80047870` otherwise; `0x80047874` commits player `+0xA3`. Passive flow takes
the mode-14 block exactly once at mount frame 1042.

During mount, `0x80048B2C..0x80048B34` sends mode 14 directly to `0x80048D90`,
skipping the ordinary vertical-state section.

At release frame 1216, passive flow takes `0x80047C34`, `0x80047C4C`, and the
behavior-3 block `0x80047CD0`; it also reaches the transient-mode clear at
`0x800490AC`. At frame 1222, flow reaches the state-6 store at `0x80048D64`.

`camera_follow_update` has no handstand-mode reference and no action-16 special
case. It remains the ordinary derived camera producer. LEVEL01 has no overlay
writer for the A10 latch.

## Inference and causal confirmation

Observation: mode 14, actor offset `0x108`, behavior 3, grounded zero, and exact
player freeze co-exist for the sustained handstand.

Inference: actor behavior class, rather than actor ID or the old coordinate-scan
survivor, selects the fixed-seed mount variant.

Causal confirmation: pristine code chooses mode 14 from behavior `>= 3`, and
the passive mount frame takes that exact block. The fresh-Square release takes
the same actor's behavior-3 branch, clears the latch, and reaches the resident
state-6 writer.

## Closure decision

A10 remains `partial` under strict campaign vocabulary but is
`bounded-exhausted_move_on` for Phase 4. The row-owned positive, negative,
identity, mount, sustained latch, release, dismount, landing, and camera
questions are closed.

Residual every-level placement geometry is content breadth. The exact authored
cause of the intermediate camera-target transition belongs to the camera
subsystem; no A10-owned camera latch remains. Neither residual justifies another
A10 replay.

No Interpreter movie is required.
