---
title: Phase 4 C08 green homing berry bounded exhaustion
date: 2026-08-04
status: bounded_exhausted
source_state: original_game
row: C08_green_homing_berry
---

# Phase 4 C08 green homing berry bounded exhaustion

## Question

Can C08's target acquisition limits, loss/retarget law, collision payload, and lifecycle be closed from the pristine executable and retained evidence, or is a new Interpreter movie required?

## Method

- Queried the central Phase 4 capsule index before considering a live replay.
- Validated the closest relevant capsule, `b12_homing_shooter_multi_target`: manifest SHA-256 `b2a96b6fad84ebf5a7cc555fe2e84bf8821cd7394a1ce6ee4e783007f8a0ebac`; all 27 declared files matched; errors were empty; the movie was not truncated; clean and traced full-machine fingerprints matched.
- Bounded that capsule to shared-code corroboration because it is B12 plant-projectile evidence, not a player-thrown C08 target-loss control.
- Compiled `tools/phase4_c08_static.c` with `cc -O2 -Wall -Wextra ... -lcrypto` and ran it against pristine `SCUS_942.88`, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- The native C gate checked 38 raw opcodes, both green parameter rows, cleanup jump-table ownership, every direct `0x8005743C` xref, and the absence of that call from `0x8005A308..0x8005B128`.
- ASM sources were `asm/hand_written/8005743c_berry_homing_target_acquire.s`, SHA-256 `24b3682e37f89bce35a07836337facf5c3e3d6eb6a78caad3a9348efb73a660a`, and `asm/hand_written/8005a308_berry_projectile_update.s`, SHA-256 `0e1682770aeef1ce70d0cdbd3c85d2303966434a20d57cc8137ce1b2886efdbc`.
- No DuckStation launch, disc mutation, RAM mutation, save mutation, or movie mutation was used.

## Observation

### Primary and acquisition cadence

Equip index `2` constructs primary type `8`. Its parameter row is at `0x800794BC`: timer `8`, model `123`, subtype `5`, flags `0xE5`, and damage byte `12`.

The primary does **not** rescan each frame. When it reaches terminal cleanup, subtype `5` dispatches to `0x8005972C`; the call at `0x80059730` invokes `FUNC_8005743C(primary, 1)` exactly once. This corrects the older loose wording in `src_re/berry_homing.c`.

### Target selection limits

`FUNC_8005743C` scans pointers beginning at `0x80090748` until the first NULL pointer. A candidate requires `enemy+0x5C & 0x0001` and is excluded by `enemy+0x5C & 0x00A0`. Distance is:

```text
dx = (primary.x - enemy.x) >> 5
dz = (primary.z - enemy.z) >> 5
distance = dx*dx + dz*dz
```

Y is ignored and the scanner has no range cutoff. The comparison skips only when `bestDistance < newDistance`; equality therefore replaces the earlier candidate, so the later table entry wins an exact tie.

A valid mode-`1` selection is passed at stack argument `+0x10` to the type-`16` constructor and becomes child record `+0x10`. If no target exists, no type-16 child is created: the primary becomes timer `80`, subtype `3`, and later retires through ordinary cleanup.

### Seek and target loss

The type-16 row at `0x8007955C` has timer `100`, model `123`, subtype/connection class `3`, flags `0xED`, and damage byte `12`. Bit `0x08` enables the common homing updater. It turns by one signed quarter of angular error, clamps vertical correction to `[-1024, 1024]`, and rebuilds velocity from the sine table at `>>3` scale.

For a live target, the child reads current transform data through target `+0x44/+0x74`. If target `+0x6E == 0` or target `+0x5C & 0x0880`, instructions `0x8005A3E0..0x8005A400` stage the child timer to `1`. The polarity is `== 0`, correcting the older source comment.

There are exactly three direct calls to acquisition in the pristine executable: `0x80059730`, `0x8005989C`, and `0x80059A1C`. All are primary/subtype dispatcher arms. The child updater contains zero such calls. Target loss therefore retires the existing child; it cannot retarget.

### Collision, damage, and cleanup

The damaging child uses connection class `3` and damage byte `12`. This bypasses the class-`1`/damage-byte-`1` berry-tough reaction-only cases and reaches the exact `-2` local-counter path. Class `3` is not permanent class `11`, and its secondary marker is not `6`, so defeated enemies remain temporary.

The child has a 100-tick ceiling plus the common floor, far-distance, missing-flag, collision, and target-invalid retirement paths established by A08. Terminal staging is `0 -> -1 -> 0`, then subtype `3` cleanup. That arm decrements the owned-throw counter at `0x800A6596` exactly once.

## Retained capsule boundary

The valid B12 capsule counted acquisition entry `0x8005743C` 10 times, common updater loop `0x8005A340` 41,344 times, and the targeted-child path `0x8005A3D0` 161 times. The expiry write was not covered, so this capsule corroborates the shared valid-target path only. It is not misrepresented as target-loss evidence.

## Evidence classification

**Observation:** the preserved capsule executed the shared acquisition and targeted-child blocks without an invalidation event; prior live controls matched nearest-target selection in four of four acquisitions and changed selection when the nearest candidate was invalidated before spawn.

**Inference:** no range check means every eligible table member is considered within ordinary retail coordinate arithmetic; exact ties favor the later entry.

**Causal confirmation:** raw xrefs confine acquisition to primary cleanup arms, while raw invalid-state branches set timer `1` and the bound subtype-3 cleanup arm decrements ownership. This proves retire-without-retarget for the instruction-bound core.

## Disposition

C08 remains strict all-context `partial`, but its direct Phase 4 mechanics are **bounded-exhausted** and the closure gate is **PASS**. No Interpreter movie is required to move on.

Deferred low-return work is exact trail/impact GPU ownership, exact SPU attribution, campaign-wide enemy/boss-overlay presentation breadth, unreachable signed-distance overflow cases, and the exact visible disappearance frame after target loss. Request a movie only when one of those becomes a concrete dependency. Cold boot is not required because no disc, code, or asset changed.

Machine evidence: `analysis/phase4_c08_green_homing_berry.json` and `analysis/phase4_c08_bounded_exhaustion.json`. Canonical synthesis: [[SYS_green_homing_berry]].
