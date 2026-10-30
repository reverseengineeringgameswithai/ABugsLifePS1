# Seed color change

## Scope

This note records confirmed original-game behavior for Phase 4 row
A12_seed_color_change. It supersedes the A12 interpretation of the invalidated
2026-07-30 address-narrowing scan, but preserves that experiment as negative history.

## Confirmed behavior

- Triangle changes the currently selected seed's color only on a fresh press.
- The action is admitted when selected offset 0x800A655C is positive. There is no
  separate carry-mode or level-number gate in the resident handler.
- The selected actor's source record is actor+0x80. Current color is source+0x0E,
  authored/default color is source+0x0F, and the transition/presentation timer is
  source+0x18.
- Runtime unlock order is four low-to-high nibbles in 0x800B0196. First collection of
  token kinds 0x2A, 0x2B, 0x2C, and 0x2D appends indices 1, 2, 3, and 4. Baseline token
  kind 0x29 does not add a nibble.
- With unlock word 0x4321, fresh presses cycle 0, 1, 2, 3, 4, 0. Holding Triangle does
  not repeat. An unknown current value wraps to the first unlocked nibble.
- With no unlocks, Triangle leaves color 0 but still performs the timer, sound, and
  presentation path. With no selected seed, the handler returns before those effects.
- A nonzero source+0x0F forces its low nibble instead of cycling. Actor reinitialization
  at 0x80049DF4 restores source+0x0E from that default and clears source+0x18.
- The same action applies to a fixed/mounted selected seed. A pristine control at
  selected offset 0x0108 resolved actor 0x8009FE88 to source 0x80094A70 and changed
  source color 0->1. Carry mode is not an admission condition.

## Color domain and feedback

| Index | Display color | RGB at 0x80078E58 | Sound cue | Effect object |
|---|---|---|---|---|
| 0 | brown | 128, 64, 0 | 30 | 124 |
| 1 | blue | 0, 64, 128 | 31 | 125 |
| 2 | green | 32, 128, 32 | 32 | 126 |
| 3 | purple | 128, 32, 112 | 33 | 127 |
| 4 | orange/yellow | 200, 127, 0 | 34 | 128 |

The action writes source+0x18=16, calls 0x8005044C with 30+color, and calls
0x800577DC. The latter indexes the RGB triplet above and spawns color+124 radial
objects plus a second effect. The HUD consumes the same unlock-order list for seed
availability meters; no separate current-color HUD highlight was established.

## Ownership

- Action handler: 0x800473B0, decisive writer 0x80047464.
- Actor reinitialization writer: 0x80049DF4.
- Unlock-order pickup producers: 0x80054288..0x80054554.
- Unlock-order scene reset: 0x8005BB60.
- Sound dispatch: 0x8005044C.
- Color presentation: 0x800577DC.

The whole pristine resident executable contains exactly two stores to source+0x0E:
the Triangle writer and the actor-reinitialization writer.

## Campaign content census

A compiled C census covers every physical pristine resource in REBUILD/files:

- 21 LEVEL*.DAT files parse successfully. Totals for token kinds 0x29..0x2D are
  18, 25, 36, 26, and 7.
- 24 LEVEL*.RAW files contain 130 id-11 seed records.
- Authored current colors are limited to 0..4 with counts 103, 14, 5, 4, and 4.
- All 130 records satisfy source+0x0E == (source+0x0F & 0x0F). The high nibble of
  source+0x0F is flags/metadata, while its low nibble is the reset color.
- 20 LEVEL*.BIN overlays contain no direct byte store to base+0x0E. Five direct
  reads exist, but they do not introduce an alternate writer.

Exact per-resource counts are retained in analysis/phase4_a12_campaign_census.json.

## Boundary

The reusable law is bounded-exhausted. Stage-specific availability is content-driven
by which censused colored tokens can be collected after the scene resets 0x800B0196.
Natural execution of every stage, exact effect-frame timing, and SPU waveform identity
remain deferred because they do not change the control semantics.

## Evidence

- [[EXP_2026-08-03_phase4_a12_seed_color_change]]
- [[EXP_2026-07-30_phase4_a12_level01_seed_color_address_narrowing]]
- analysis/phase4_a12_seed_color_change.json
- src_re/seed_color_change_800473b0.c
- tools/phase4_a12_static.c
- tools/phase4_a12_capsule.c
- tools/phase4_a12_adversarial.c
- analysis/phase4_a12_campaign_census.json
