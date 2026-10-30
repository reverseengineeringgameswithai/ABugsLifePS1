---
title: Phase 4 C09 mega homing berry differential closure
date: 2026-08-04
status: bounded_exhausted
source_state: original_game
row: C09_mega_homing_berry
---

# Phase 4 C09 mega homing berry differential closure

## Question

What exactly makes the purple/Mega Homing Berry different from green: launch speed, turn rate, lifetime, damage, collision class, or presentation? Is a side-by-side Interpreter movie required?

## Method

- Queried the central retained-capsule index first. It has no C09 or Mega Homing entry.
- Bounded the already-validated B12 capsule to common-updater corroboration; it is not C09-specific evidence.
- Hashed the existing fixture `mega_homing_berry.sav` as `94870aab95ba8703e52c8c11ac34d307c3834f8df76ae2ccbda8f7fe6ae3a1a8`. Its retained RAM-usage artifact is only a 300-frame changed-byte census, not a trace capsule.
- Compiled and ran `tools/phase4_c09_static.c` against pristine `SCUS_942.88`, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Compared raw type `8/45` primary rows and `16/48` child rows, the mode-`1/0` child-spawn blocks, all acquisition xrefs, constructor field-copy instructions, shared updater, damage switch, permanence gate, and cleanup jump table.
- Reused D04's two complete berry-tough five-berry controls only for runtime corroboration of Mega `-3` and temporary defeat.
- No DuckStation launch, save mutation, movie mutation, RAM write, or disc mutation was used.

## Exact parameter differential

Both primary and child comparisons differ at exactly six of twenty bytes:

| Offset | Green | Mega | Confirmed role |
|---:|---:|---:|---|
| `+0x04` | 123 | 124 | model |
| `+0x0C` | 5 / 3 | 9 / 8 | primary / terminal connection subtype |
| `+0x0F` | 12 | 13 | secondary kind |
| `+0x11` | 12 | 128 | damage selector |
| `+0x12` | `0x60` | `0x20` | presentation byte |
| `+0x13` | `0x00` | `0x80` | presentation byte |

Every other row field is identical within its primary or child pair. In particular, `+0x0E` is zero for both. The constructor proves `+0x0E` is an orientation-sign selector and `+0x0F` is a separate secondary byte; treating the combined halfword `0x0C00/0x0D00` as a speed value was incorrect.

## Native control

Equip index `4` constructs timer-8 type `45`, subtype `9`. Terminal subtype 9 calls `FUNC_8005743C(primary, 0)` once. It uses the same NULL-terminated target table, eligibility filter, nearest-XZ/tie law, and target-loss rules established for C08.

A valid target creates timer-100 type `48`, subtype `8`. With no target, the primary becomes timer `80`, subtype `8`. Terminal subtype 8 decrements the owned-throw counter at `0x800A6596` exactly once.

## Speed and steering correction

Mega is **not faster than green** in the native instruction path:

- Both primaries use `vy=-2048` and the same common launch code.
- The type-48 and type-16 child-spawn blocks are instruction-identical except for constructor literal `48` versus `16`.
- Both child rows have the same timer `100` and flags `0xED`.
- Both enter the single common updater selected by homing flag `0x08`.
- Both turn by one signed quarter of angular error.
- Both clamp vertical correction to `[-1024,1024]`.
- Both rebuild velocity from the sine table at fixed `>>3` scale.

The roadmap's former “stronger/faster” description therefore mixed a real strength difference with an unsupported speed assumption.

## Damage, resistance, and permanence

The constructor copies Mega row `+0x11 == 128` to contact record `+0x34`. The damage switch loads that byte and reaches the explicit `-3` instruction at `0x800590B4`. Green selector `12` reaches exact `-2`.

Mega connection class `8` and damage selector `128` bypass the berry-tough reaction-only comparisons, so ordinary and berry-tough actors take `-3`. D04's complete shell-bug and worm controls corroborate this result.

Mega remains temporary. Class `8` is not gold permanence class `11`, and secondary kind `13` is not mine permanence kind `6`.

## Target loss and lifecycle

Type 48 shares green's live-target steering and invalid-target branches. Target counter zero or state mask `0x0880` stages timer `1`. No child updater calls acquisition, so Mega retires without retargeting.

Lifecycle is primary `8` ticks, child `100` ticks, or no-target fallback `80` ticks, plus the common floor, distance, flags, collision, and target-invalid retirement paths.

## Evidence classification

**Observation:** the pristine row pairs differ only at the six listed bytes, and the two child-spawn blocks differ only in their constructor literal.

**Inference:** different model/trail presentation and killing an enemy in fewer hits can make Mega look faster, but neither changes projectile kinematics.

**Causal confirmation:** type 48 enters the same flag-driven fixed sine/8 updater as type 16, while selector `128` reaches the dedicated `-3` damage instruction.

## Disposition

C09 remains strict all-context `partial` but is **bounded-exhausted** for direct Phase 4 mechanics. The closure gate is **PASS**, and no Interpreter movie is required to move on.

Deferred low-return work is exact GPU/SPU ownership of Mega-specific presentation/effects, campaign-wide boss-overlay floors, and a visual side-by-side that would repeat identical kinematic instructions. Request a movie only if one of those becomes a concrete dependency.

Machine evidence: `analysis/phase4_c09_mega_homing_berry.json` and `analysis/phase4_c09_bounded_exhaustion.json`. Canonical synthesis: [[SYS_mega_homing_berry]].
