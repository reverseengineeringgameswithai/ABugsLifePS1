---
kind: system
id: SYS_vine_web_swinging
name: Vine and web swinging
status: partial_high_value_bounded_exhausted
confidence: high
source_state: original_game
row: A16_swinging
evidence:
  - EXP_2026-08-03_phase4_a16_swinging
  - analysis/phase4_a16_swinging.json
---

# Vine and web swinging

## Canon behavior

Flik attaches to the Tree swing through the resident moving-surface collision path, not through a standalone vine-only player mode. The Phase 2 positive control approaches the vine with Up+Cross and enters player mode `5`; cross-only and neutral controls from the same approach anchor do not attach. Once attached, `grounded` remains zero while the moving surface projects a changing velocity into Flik.

The accepted retained capsule contains one sustained attached interval at movie frames `124..905`: 782 display-frame boundaries, or 391 30 Hz gameplay ticks, with mode `5` and grounded `0` throughout. This is a latch, not a one-frame collision response.

## Attachment identity

`player+0x8C` (`0x800A658C`) holds a one-based handle into the eight-entry, `0x344`-stride visual-sprite/mover pool rooted at `0x8009C870`. In `on_swing.sav` the handle is `2`, selecting record index `1` at `0x8009CBB4`. The detach field used by the player helper is record `+0x04`, `0x8009CBB8`.

An 8-display-frame Interpreter access trace kept the handle at `2` and mode at `5` while 132 bytes changed in the record's transform/geometry body. The resident `0x800409F8..0x80041A70` transform/normal routine owns the bulk record writes; the `0x80042428` pool updater also writes the record. This establishes the swing as a moving surface record rather than a passive decorative prop.

## Player ownership chain

- `0x80041AC4..0x800423F4` consumes moving-surface geometry, publishes the one-based handle at `player+0x8C`, and stores projected velocity at `player+0x2C/+0x30/+0x34`.
- A nonzero surface result reaches `0x8004892C`, which writes mode `5` and clears the mode timer/bind field.
- `FUNC_80047EBC` supplies the shared camera-relative target heading. The mode-5 path turns the active heading toward that target and asks `0x80041AC4` for the corresponding surface projection.
- The ordinary player integrator stores X/Y/Z position at `0x80036D20`, `0x80036D34`, and `0x80036D48`.

This is the pendulum writer chain at Phase 4's useful semantic boundary: moving record geometry -> surface projection -> player velocity -> ordinary XYZ integration.

## Steering

Same-save 30-display-frame controls from `on_swing.sav` all retained mode `5`, grounded `0`, and handle `2`:

| Input | Final heading | Target heading | Result |
|---|---:|---:|---|
| Idle | 2207 | 2209 | Baseline forward arc |
| Up | 2207 | 2209 | Identical to idle because the anchor already faces forward |
| Left | 1727 | 968 | Distinct left trajectory |
| Right | 2687 | 3438 | Distinct right trajectory |
| Down | 2207 | 161 | Reversed target and distinct trajectory |

Thus directional steering modifies the shared heading target while the attachment latch remains owned by the moving-surface handle.

## Release and landing

The attached path requires a fresh Cross edge: current pad `0x80082488 & 0x4000` is set while previous pad `0x80082380 & 0x4000` is clear. The release branch:

1. calls `FUNC_80041A74`, which writes `-30` to attached record `+0x04` and clears `player+0x8C`;
2. selects action/animation `3`;
3. switches immediately from mode `5` to mode `1`;
4. doubles X and Z velocity; and
5. subtracts `0x800` from Y velocity.

The immediate state is mode `1`, correcting the older coarse claim that release goes directly to mode `2`. In the live control, two display frames after Cross Flik was mode `1`, airborne, handle `0`, velocity `(386,-2140,1516)`. At 60 display frames he was mode `0`, grounded `0x0101`, action `22`.

## Bounded residual

A16 is a substantiated partial with bounded exhaustion. Naming every per-vertex constant in the shared `0x800409F8` geometry routine and decomposing the swing-specific camera response would be shared mover/camera research, not a missing A16 behavior branch. Reopen this row only if that general engine work specifically needs the swing fixture.

See [[EXP_2026-08-03_phase4_a16_swinging]].
