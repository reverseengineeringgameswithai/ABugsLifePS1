---
kind: system
id: SYS_cannon_plant
created: 2026-08-03
updated: 2026-08-03
status: live_confirmed_bounded
confidence: high
source_state: original_game
functions: [seed_plant_cannon_handler, player_vertical_update]
memory: [0x800A657C, 0x800A6580, 0x800A659E]
evidence: [EXP_2026-08-03_phase4_b04_cannon_plant]
src_paths: [src_re/brown_seed_plants.c, tools/phase4_b04_static.c, tools/phase4_b04_capsule.c]
patch_policy: safe_to_read
---

# SYS_cannon_plant - cannon seat, launch, combo, and landing

## Dispatch and contact

Brown count 4 selects plant type 2, dispatched by the plant walker to
`seed_plant_cannon_handler` at `0x8005C110`. The handler requires the selected-contact
gate, plant state `1`, maturity bit `slot+0x2E & 2`, and contact-object trigger bit
`+0x34 & 0x80`. It clears carry-related state, changes the cannon animation/state, and
stores `17` in the player lockout timer at `0x800A657C`.

The handler does **not** write player velocity. That older attribution is superseded.

## Seated phase and launch source

The shared player path `0x80048658..0x800486D8` owns the launch:

- While `player+0x7C` remains positive, it decrements once per physics update and writes
  zero to `vx`, `vy`, `vz`, and two auxiliary velocity fields. The retained movie shows
  the `17..1` countdown on alternating movie frames with position fixed.
- On expiry, it selects mode `5`, clears contact/air words, and stores the fixed literal
  `-8192` at player `vy` (`0x800486B8`/`0x800486CC`). There is no launch-vector table.
- Ordinary gravity adds `+256` in the same update and the shared state advances, so the
  first retained boundary is mode `6`, `vy=-7936`; the next is `-7680`. The older claim
  that `-7680` was the launch impulse confused this later frame boundary with the seed.
- The cannon seed vector is `(0,-8192,0)`. Lateral values present at the first boundary
  are ordinary in-air steering after the seed, not cannon-authored vector components.

## Captured trajectory

In `B04_cannon_dandelion_combo.movie.json`, contact fires at movie frame `119`, the
launch boundary is `153`, and the apex is frame `215` at player Y `-148826`: a
`126976`-unit rise from the seated Y `-21850`. Vertical speed follows `vy += 256` per
physics tick and reaches the ordinary falling terminal value `+4096`.

The cannon plant returns from animation state `2` to ready state `1` at movie frame
`191`; the handler contains no permanent one-shot latch. The fixture does not perform a
second entry, so unlimited repeat-entry behavior remains a structural inference rather
than a separately exercised claim.

## Cannon-to-dandelion combo

At movie frame `275`, the dandelion volume writes interaction latch `11` at
`0x800A659E`. The shared player path `0x800486DC..0x80048728` then applies:

```c
if (airborne)
    vy = (vy < 350) ? vy + 256 : 350;
else
    interaction_latch = 0;
```

The capture changes `vy=4096` to `vy=350` at frame `277`, sustains the `+350` slow-fall
through frame `457`, and preserves ordinary horizontal steering. Landing contact occurs
at frame `459`; mode returns to `0` and latch `11` clears at frame `461`.

## Camera boundary

Neither `0x8005C110` nor the launch/slow-fall player block writes the camera struct at
`0x80095358`. The flight remains in the standard camera-follow path. Exact transform
evolution, animation-frame identity, and SPU asset identity are deliberately deferred:
they do not affect the B04 contact/physics/combo/landing contract.

## Provenance

See [[EXP_2026-08-03_phase4_b04_cannon_plant]], `analysis/phase4_b04_static.json`,
`analysis/phase4_b04_capsule.json`, and `analysis/phase4_b04_bounded_exhaustion.json`.

## Phase 4 B04 closure audit — 2026-08-04

B04 is **Substantiated Partial / bounded-exhausted**. Pristine C analysis verifies the mature type-2 contact gates, 17-tick seated lockout, fixed launch seed `(0,-8192,0)`, shared ballistic path, dandelion latch `11`, `+256` slow-fall convergence to terminal `vy=350`, and grounded latch clear. The complete retained capsule reproduces the full contact-to-landing chain with exact control fingerprints.

Evidence: [[EXP_2026-08-03_phase4_b04_cannon_plant]], `analysis/phase4_b04_bounded_exhaustion.json`, `analysis/phase4_b04_static.json`, and `analysis/phase4_b04_capsule.json`.
