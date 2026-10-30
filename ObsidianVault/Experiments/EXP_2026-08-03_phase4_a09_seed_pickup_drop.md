# EXP 2026-08-03 - Phase 4 A09 seed pickup and drop

## Question

What exactly owns movable-seed pickup, carried attachment, manual drop, and reset, and is A09 sufficiently substantiated to move on without another Interpreter movie?

## Method

The retained capsule was validated and queried before considering live DuckStation:

- `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/A09_seed_blocked_drop_LEVEL01`
- Manifest SHA-256: `382287246d1cfeaf4ef045e4b16d70e70018a59699b9518ca3ff9bd7dba53faf`
- Movie SHA-256: `803729cd6279facb5710b9c61173b431db9481ead83fe642da0f5cd7bfdc53f9`
- State SHA-256: `f7580c58022b3b7edcfab499bf44381f7513d1bb7bfd623f5aebcb43000ea4e9`
- Media: pristine `SCUS-94288`
- Complete: true; truncated: false; independent control mismatches: `{}`

`tools/phase4_a09_capsule.c` decompressed all 15 chunks, reconstructed 870 boundaries, verified 2,610 RAM/VRAM/SPU-RAM hashes, parsed Square edges from the movie, and tracked player plus seed actor 11. `tools/phase4_a09_static.c` mapped decisive pristine-ASM PCs, while `tools/phase4_a09_writer_union.c` censused literal references across 892 hand-ASM units.

The capsule was collected under the legacy forced CachedInterpreter lane. It is accepted because its manifest is complete and its independent control is exact across cycle, frame, registers, RAM, VRAM, SPU RAM, and full machine state. It was not replayed with new instrumentation and supports no new execTrace claim.

Repository revision during analysis: `873bba7c0cf8be24d4e28ed9551feefe84dfa222`.

## Static result

### Identity and phase are separate fields

- `0x800A655C` is a `u32` selected-object offset. Zero means none; positive movable-actor values are added to `0x8009FD80`. LEVEL01 uses `0x00000A50`, selecting actor `0x800A07D0`, id 11.
- `0x800A65A3` is a `u8` interaction phase. Movable seed pickup progresses through 8, 9, 10, 11, and 12. Manual release writes transient mode 13 before later player update returns it to zero.

The older address-narrowing note correctly correlated these fields but did not separate ownership. The static and capsule evidence now do: the offset owns selected identity; the mode owns lift/carry/release phase.

### Pickup gate

`player_contact_response` at `0x80047284` accepts a fresh Square edge at `0x80047728/0x80047740`. The actor scan requires:

- actor `+0x5C` bit `0x20`;
- actor `+0x5E != 0`;
- actor behavior state `+0x40 != 4`;
- quantized three-dimensional squared distance at most `0x270FF`;
- modular facing delta inside the 1024-unit native window;
- compatible player action fields (`+0x82`, `+0x84`, `+0xA3`, `+0x88`, `+0x7A`).

The commit writes the actor offset at `0x80047858`, writes mode 8 or 14 at `0x80047874`, sets actor flag `0x40` at `0x80047888`, and clears player horizontal motion.

### Lift and attachment

Actor update `0x8004BA38..0x8004BB00` owns mode 11. It raises the seed toward player `Y-19200`, centers X/Z, clamps approach components to `+/-2048`, and enters mode 12 once the residuals are each below 128.

Mode 12 validates the attachment separation at `0x8004BB68..0x8004BC10`. If its quantized squared error reaches 10001, it clears the selected offset, carried flag, and mode. Stable mode 12 has the exact law:

- seed X equals player X;
- seed Z equals player Z;
- seed Y equals player Y minus 19200.

### Manual drop

A fresh Square edge is checked at `0x80047C28/0x80047C40`. The ordinary positive-offset path clears actor flag `0x40` at `0x80047C60`, clears the selected offset at `0x80047CE8`, and writes transient mode 13 at `0x80047D00`. An ordinary movable seed receives heading-derived X/Z motion; initial Y motion is zero, and gravity advances it before the next frame-boundary sample.

There is no environmental obstruction gate in the manual release decision. The fixture name `A09_seed_blocked_drop_LEVEL01` describes what can happen to the detached trajectory, not a denied Square release.

### Lifecycle and cross-system clearers

Separate clearers cover forced detach (`0x80046D04`), player action cancellation (`0x80048394`), mode-11 timeout (`0x8004BB38`), mode-12 separation (`0x8004BBF8`), respawn (`0x8005B258`), and cannon consumption (`0x8005C204`). Level/player spawn at `0x80046B20` clears the complete 168-byte player block.

These are lifecycle consumers, not competing pickup owners.

## Capsule result

Six fresh Square edges form three exact pairs:

| Operation | Input frame | Commit frame |
|---|---:|---:|
| pickup 1 | 111 | 114 |
| drop 1 | 171 | 174 |
| pickup 2 | 245 | 248 |
| drop 2 | 556 | 558 |
| pickup 3 | 644 | 646 |
| drop 3 | 696 | 698 |

The three carry epochs are 60, 310, and 52 boundaries. Their initial mode-8..11 lift phases explain why X/Z are not yet identical over every boundary. Once mode 12 is reached, X/Z identity and the `-19200` Y offset hold exactly.

Passive block flow independently records three executions each of pickup scan/success/commit (`0x80047764`, `0x80047784`, `0x80047874`) and three ordinary drop tails (`0x80047CD4`). The negative plant-offset path and generic `0x80046CAC` forced-detach helper each have zero executions. This disproves the previous implication that manual release calls `0x80046CAC`.

All three drops become ballistic and later settle:

| Drop frame | First zero-motion frame | Flight boundaries | Settled delta from first detached sample |
|---:|---:|---:|---|
| 174 | 206 | 32 | `(1353,12456,-8954)` |
| 558 | 608 | 50 | `(133,20630,17347)` |
| 698 | 748 | 50 | `(3238,21413,18917)` |

Frames 280 through 555 provide a long no-Square control: carry persists, so there is no ordinary timeout release. Frames 0 through 110 provide the complementary no-Square control: proximity alone does not pick the seed up.

The independent pristine Training oracle in `analysis/phase2_carry_handstand_oracle.json` reproduces the same stable X/Z identity and `-19200` Y offset in a second scene.

## Observation, inference, and confirmation

- Observation: three Square pickups and three Square drops transition the two carry fields and actor flag consistently.
- Observation: stable carry has exact X/Z identity and fixed `-19200` Y offset in LEVEL01 and Training.
- Static confirmation: the native pickup, lift, stable-validation, release, cancellation, and respawn writers are identified at exact PCs.
- Correction: manual Square release does not execute `0x80046CAC`, and the named blocked-drop fixture contains no denied Square release.
- Bounded inference: identical behavior in two scenes plus resident non-overlay ASM supports a common movable-seed law; exhaustive placement geometry for every level is not claimed.

## Disposition

A09 remains `Partial` in the whole-game baseline but is bounded-exhausted for Phase 4 and safe to move past. No named state, control-flow, lifecycle, interaction, or behavioral-control gap requires live DuckStation. Exhaustively recording every level's approach geometry would be low-return content breadth rather than a stronger resident-law result.

No additional Interpreter movie is required.
