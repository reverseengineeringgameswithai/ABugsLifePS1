---
kind: system
id: SYS_hud_counters
name: HUD Counters
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - FUNC_800526F4
memory:
  - MEM_800A6500
  - MEM_800A658E
  - MEM_800B0198
  - MEM_80082258
tables: []
constants: []
evidence:
  - EXP_2026_07_07_golddrop_pickup_verifier
  - src_re/hud_800526f4.c
  - EXP_2026-07-07_golddrop_pickup_verifier
src_paths:
  - src_re/hud_800526f4.c
---

# SYS_hud_counters

## Purpose

Canonical hub for gameplay HUD and SELECT-panel counters relevant to Gold Berry, grain, FLIK, and progress display.

## Confirmed original-game behavior

- Grain and FLIK/seed progress live in the `0x800A6500` progress block.
- The misc/gold-defeat pulse panel uses `0x800B0198`.
- The bottom gold-defeat count displays `LW(0x80082258) - LH(0x800A658E)`.
- A counter increment can therefore be produced by decrementing `0x800A658E`; the HUD does not need a separate direct "gold defeated" write for the display value.

## Gold Berry token relevance

The Gold Berry token mod pickup hook decrements `0x800A658E` and pulses `0x800B0198`. That is why collecting the floor glyph makes the bottom counter advance as if an enemy was killed with a retail Gold Berry.

## Scene Panels

The renderer now has address-level roles for every scene-specific source:

| Scene | Source | Render use |
|---:|---|---|
| 2 | `0x8009FE72` | raw progress minus 19 |
| 7 | flags `0x800B5774`, icon `0x800B577C` | five state icons plus one numeric icon |
| 11 | `0x800A0316` | raw progress minus 19 |
| 12 | `0x800B4A48` | one displayed digit |
| 13 | `0x800B45F4` | raw progress minus 19 |
| 14 | `0x800B4CC8` | `(8 - raw) * 4`, capped to 31 |
| 15 | `0x800B4BA8` | raw progress |

Scenes 2/11/13/14/15 feed the common five-segment tile-`0x75` meter after
clamping and halving. Their address and renderer roles are closed; the
story/object name represented by each raw value remains deliberately unlabeled.
