---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - Player state 800A6500.md
aliases:
  - "MEM - Player state 800A6500"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - Player state 800A6500.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_Player_state_800A6500.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: MEM - Player state 800A6500
type: memory-structure
address: 0x800A6500
confidence: CONFIRMED
tags: [memory, player, physics, progress]
---

# MEM — Player state + per-level progress block `0x800A6500`

> Flik's position and the per-level pickup-progress counters. The most-watched RAM in the project.

## Player position
| Address | Field | Notes |
|---------|-------|-------|
| `0x800A6500` / `0x800A6504` / `0x800A6508` | player X / **Y** / Z | Y is the collision-corrected output; written by [[FUNC_8003633C]] at `0x80036cec` |
| `0x800A652C` | velocity / delta | resolver input (`s5`); also checkpoint coord |
| `0x800A6582` | contact flags | |

> Y is biased `−0x1cc0` inside the contact walker math and `−0xe6` inside the type-0x3f construct pass — different biases in different consumers.

## Progress counters (pickup track)
| Address | Field |
|---------|-------|
| `0x800A658E` | **enemies remaining / gold-defeat quota** (u16). Gold permanent kills and the [[Gold-berry drop on non-gold kills]] walk-over token decrement this; the bottom gold-defeat counter displays total enemies minus this value. |
| `0x800A6596` | active thrown-berry gate/counter; native throw caller blocks at `>=4` |
| `0x800A6597` | FLIK/berry marker byte (0..4) |
| `0x800A6598 / 99 / 9a` | seed-token counters (kinds 0x29 / 0x2a / 0x2b; encoding `(n&7)*17`) |
| `0x800A65A0` | **LIVES** (u8) — CONFIRMED gating/editable counter (poke up → prevents game-over; `0` = last life) → [[Menu and HUD structure]]. *(was mislabeled "FLIK F progress / progress latch" — corrected 2026-06-18.)* |
| `0x800A65A1` | grain count (target `0x32`=50; HUD mirror) |
| `0x800A65A2` | FLIK bitmask (bits 0..3) |

## Related
- System: [[Menu and HUD structure]] — the SELECT status icons (FLIK letters, seed power, grain) mirror the progress counters above (health leaf + lives still unmapped).
- Functions: [[FUNC_8003633C]] (writes Y) · [[FUNC_800586B0]] (reads pos) · [[FUNC_80053814]] · [[FUNC_80054EAC]] · [[FUNC_800526F4]] (HUD)
- Structures: [[MEM - Collision sector table 800A7E48]] · [[MEM - Contact array 800B0D18]]
- Findings: [[Finding - Player Y writer FUNC_3633C]] · [[Finding - Collision RAM edit moves footing 1to1]]
- Symbols: full list in [[Symbols Index]]
