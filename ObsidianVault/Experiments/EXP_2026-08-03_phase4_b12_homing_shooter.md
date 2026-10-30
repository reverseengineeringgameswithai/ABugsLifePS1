---
kind: experiment
id: EXP_2026-08-03_phase4_b12_homing_shooter
name: Phase 4 B12 - yellow tier-2 shooter correction
status: completed
created: 2026-08-03
updated: 2026-08-03
confidence: high
---

# Phase 4 B12 - yellow tier-2 shooter correction

## Question

Does the second yellow combat plant independently acquire enemies and steer a
purple homing projectile, and are B12's acquisition, cadence, immunity, and
lifecycle requirements sufficiently closed to move on?

## Disposition

**B12 remains Partial, but the high-value row is substantiated as a correction
and bounded-exhausted. Move on.** The legacy description is not the retail
mechanism represented by the row's fixtures.

- Yellow tier 2 creates plant type 13.
- Type 13 has no enemy acquisition or steering path.
- It launches constructor ID 67 straight upward every 88 video frames.
- The dedicated movie's Square-triggered projectiles are player red berries,
  not homing shots and not autonomous type-13 emissions.
- Genuine player homing behavior is already closed by A08 and D04.

No Interpreter movie or cold boot is required.

## Method

The Phase 4 capsule-first rule was applied before considering live DuckStation.

1. Accepted the retained `b12_homing_shooter_multi_target` and
   `A13__yellow_seed_levels` capsules only after their manifests reported
   complete, untruncated, error-free collection, pristine SCUS-94288 media,
   matching independent controls, and zero domain reconstruction mismatch.
2. Used compiled C reducers over the capsule chunks to reconstruct the plant
   table, contact pool, execution blocks, ownership counter, and exact
   frame-boundary recurrences.
3. Used compiled C against the hash-verified pristine executable and retained
   ASM to resolve the plant dispatch, type-13 handler, constructor ID, contact
   metadata, and all constructor call sites.
4. Correlated the movie's actual Square frames against contact construction.
5. Joined the already-banked A08 throw/homing law and D04 resistance law rather
   than replaying behavior those rows already close.

Bulk capsules, movies, and states remain external evidence. Only hashes and
bounded results are committed.

## Capsule acceptance

### Dedicated B12 capsule

- Capsule:
  `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/b12_homing_shooter_multi_target`
- Manifest SHA-256:
  `b2a96b6fad84ebf5a7cc555fe2e84bf8821cd7394a1ce6ee4e783007f8a0ebac`
- Movie SHA-256:
  `5276994b2b5eba7bac2882e7bddcfbbe5edd55fe9302cba9b7418bdca73f165f`
- State SHA-256:
  `a82942d68aab664fb50bbf3345bd13086554013e71895dd6ee606b44d61d2d47`
- Manifest movie length: 1,293 frames.
- Reconstructed boundary records: 1,294.

### Yellow-tier capsule

- Capsule:
  `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/A13__yellow_seed_levels`
- Manifest SHA-256:
  `03b5872a5bb7ecbdd21c32ffe14c20675ebbef2ff5c98600a4940b473dd89afc`
- Movie SHA-256:
  `a694c08034893a52f1cbf924cab06f4fb57417cc5e4aff8f8377761e6272c087`
- State SHA-256:
  `1f00b97137698fe37d7c0a8af31de9eca88574c284769de407d6bad11234e9ce`
- Reconstructed frames: 3,424.
- Authored tier output sequence: types `14, 13, 11, 1`.

## Static result

The type-13 dispatch entry is `0x8005CA24`. Its entire distinct prefix is only
22 instructions before it jumps into the shared constructor tail.

Admission requires:

- plant `s16 +0x02 == 2`; and
- plant `u32 +0x04 == 0x00010000`.

The launch is fixed:

| Field | Value |
|---|---:|
| X | plant `+0x08` |
| Y | plant `+0x0C - 0x6400` |
| Z | plant `+0x10` |
| VX | 0 |
| VY | -2048 |
| VZ | 0 |
| Gravity | 128 |
| Constructor ID | 67 |

The prefix does not call target solver `0x80046D24`, read the enemy target
table, or write a steered X/Z vector. It jumps from `0x8005CA74` to the shared
constructor call at `0x8005CCD4`.

ID 67 materializes in the shared 64-slot contact pool as class 2, timer 20,
model 124, radii 50/50, subtype 14, flags `0xE5`, and byte `+0x27 = 0`.

## Runtime result

### Type-13 cadence

In the dedicated capsule, type 13 appears at movie frame 288, reaches state 1
at 354, state 2 at 402, and emits its first ID-67 shot at 406. The retained
shot series is:

`406, 494, 582, 670, 758, 846, 934, 1022, 1110, 1198, 1286`

Every interval is exactly 88 video frames, or 44 30 Hz logic ticks. A natural
no-contact ID-67 generation lasts 20 logic ticks / 40 video frames. X and Z
remain fixed; Y integrates the initial `-2048` velocity while VY increases by
128 per logic tick. The player-owned throw counter remains zero at these plant
shot events.

The yellow-tier capsule independently shows type-13 allocation at 1120,
state 1 at 1186, state 2 at 1234, first ID-67 shot at 1238, operator teardown
state 3 at 1488, and slot clear at 1556.

### Movie-name confounder

The dedicated movie contains Square holds beginning at frames 318, 373, 694,
and 1094 in its main throw trials. The following constructed model-110 records
are class 2/subtype 1 and increment the player-owned throw counter. Subtype 1
is the red straight projectile from A08, not a homing primary. Therefore the
filename is not a positive homing control.

This does not invalidate the capsule. It makes it useful negative evidence:
the type-13 plant continues its separate ID-67 cadence while player throws are
independently attributable.

## Where the real homing law lives

A08's pristine static closure identifies equipped homing primary type 8 and
child type 16. The primary chooses the nearest valid enemy in X/Z; steering
adds one quarter of signed angular error modulo 4096, clamps vertical seek to
`[-1024, 1024]`, and uses sine-table velocity scaled by eight. Cleanup transfers
from primary to child/fallback and balances the four-projectile ownership cap.

D04 closes immunity as a two-state law. Homing causes temporary `-2` damage in
both the ordinary damageable and berry-tough `enemy+0x5C & 0x40` states. It is
not permanent. Gold is the only native permanent berry class.

This synthesis answers B12's named acquisition, steering, immunity, and actor
lifecycle questions without pretending type 13 owns the player homing path.

## Rejected evidence and corrections

- An initial transient probe incorrectly indexed the dispatch table by raw
  type and attempted to interpret type 15. The table ends at type 14; adjacent
  bytes are string data. No conclusion uses that attempt.
- The first contact reducer printed unrelated objects already live in the
  shared pool. Its unfiltered listing is not used for semantic attribution.
- The B12 movie filename was rejected as behavioral authority after its inputs,
  metadata, and ownership transitions identified red subtype-1 throws.

## Phase 4 closure metrics

| # | Metric | Result |
|---|---|---|
| 1 | Original oracle | Advanced: two accepted capsules cover construction, cadence, teardown, and the negative homing control |
| 2 | Complete frontier | Advanced for the correction: selector, type dispatch, ID-67 constructor, recurrence, and genuine homing owner are separated |
| 3 | Typed state | Advanced: plant state/phase and contact class/timer/model/subtype/flags are bound |
| 4 | Lifecycle | Advanced: construct, mature, fire, projectile expiry, uproot, and clear are observed |
| 5 | Original interfaces | Advanced: selector, plant scheduler, contact pool, player throw, and resistance interfaces are joined |
| 6 | Campaign breadth | Bounded: ordinary-stage capsules; campaign visual-instance breadth deferred |
| 7 | Cross-system | Advanced: yellow selector and Square throw paths are causally separated |
| 8 | Source closure | Partial: pristine opcode-level C/ASM analysis, no promoted documentation-grade decompilation |
| 9 | Durable evidence | Advanced: JSON, Canon, Experiment, fixture hashes, capsule hashes, and C artifact hashes |

## Residual boundary

Strict Full would still require a campaign-wide type-13 visual-instance census,
natural plant expiry without uproot, every generic ID-67 impact/cull path, and
exact GPU/SPU ownership. A new genuine type-8 Interpreter movie is useful only
if per-frame target-loss or retarget timing becomes an explicit requirement.
Those are low-return breadth/presentation questions and do not keep B12 open.

## Evidence

- Machine result: `analysis/phase4_b12_homing_shooter.json`
- Canon: [[SYS_yellow_tier2_vertical_shooter]]
- Existing homing owner: [[SYS_berry_projectile_and_homing]]
- Existing immunity owner: [[EXP_2026-08-03_phase4_d04_berry_immunity_matrix]]

