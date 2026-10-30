---
kind: memory
id: MEM_800A6500
aliases: [MEM_800A6500, 0x800a6500, "MEM - Player state 800A6500", "MEM - Player state", MEM_-_Player_state_800A6500]
address: 0x800A6500
name: Player_state_800A6500
status: static_seen
confidence: confirmed
source_state: original_game
system: [SYS_player_power_slot]
read_by: []
written_by: []
related_structs: []
evidence: [EXP_2026-08-01_phase4_b06_b08_power_slot]
src_paths: []
patch_policy: safe_to_read
---

# MEM_800A6500 - Player state 800A6500

## Purpose

Flik's position and the per-level pickup-progress counters. The most-watched RAM in the project.

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

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
| `0x800A652C` | velocity / delta | resolver input (`s5`); telescope activation clears it with the other velocity components |
| `0x800A6582` | contact flags | |

> Y is biased `−0x1cc0` inside the contact walker math and `−0xe6` inside the type-0x3f construct pass — different biases in different consumers.

## Progress counters (pickup track)
| Address | Field |
|---------|-------|
| `0x800A658E` | **enemies remaining / gold-defeat quota** (u16). Gold permanent kills and the [[MOD_gold_berry_token_drop|Gold-berry drop on non-gold kills]] walk-over token decrement this; the bottom gold-defeat counter displays total enemies minus this value. |
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


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Player state 800A6500.md`
- Migration status: copy-first Canon seed.

## Power / damage fields (2026-08-01, [[SYS_player_power_slot]])

| Address | Field | Notes |
|---|---|---|
| `0x800A657C` | `s16` player-action lockout timer | set 17 by seed_plant_cannon_handler (`0x8005C24C`), 5 by the knockdown reaction (`0x8004AFA4`); ticked by the same routine as `+0x7E` (`0x8004866C`, same `blez` guard); on reaching exactly 0 writes 1 to `+0x90` and 10 to `+0x88`; zeroed on respawn |
| `0x800A657E` | `s16` **power slot**, sign-multiplexed | **> 0** = invincibility countdown (time-consumed, tick 1 per 2 frames); **< 0** = bubble hit quota (hit-consumed, never ticked); **0** = none; **1** = transient, written by the harvester while equipped. 7 writers / 5 readers, censused complete |
| `0x800A6590` | `u16` power-flags word | Full bit map, from the ori/andi immediate at all **26** writers: `0x01` ground/locomotion · `0x02` **transient** ~2-frame per-action flag (set `0x8004A7B0` damage, cleared `0x80048600`) — *not* a power · `0x04` transient contact/AI · `0x08` **checkpoint marker** (`checkpoint_save` `0x80054E90`) · `0x20` **super jump** (B09; set `0x800588F8` in contact_pickup_walker with sfx 75) · `0x80` **harvester** (C13; also gates contact damage at `0x8004B160`). ⚠️ Respawn `0x8005B340` does `andi 0x0020` — it **keeps only** super jump and clears the rest. **Invincibility and the bubble use the slot `+0x7E`, not any bit here.** |
| `0x800A6592` | `s16` stagger timer | `-30` at `0x8004A814` on every intercepted contact, `-45` on the death branch; gates whether a shield hit is consumed |
| `0x800A6594` | `s16` **true health** | decremented ONLY by `0x8004A888` on the damage side. Exactly 4 writers image-wide: spawn init `0x80046C04`, damage `0x8004A888`, heal `0x80055124`, respawn restore `0x8005B30C`. ⚠️ An older Canon paragraph on [[FUNC_8004A700]] called this a "level-exit counter" — that is wrong and is corrected there |
| `0x800A659E` | `s16` plant/contact interaction latch | C static census over 892 hand-written ASM files finds the only direct nonzero literal writers: `11` at dandelion `0x8005C8BC` and `12` at player contact response `0x80047A58`. Propeller reads the latch at `0x8005C3B8/3DC` and clears state 12 at `0x8005C3F0`; vertical update, transition, respawn, and other lifecycle paths clear it. State 11 extends the propeller's inner vertical activation band. This is a complete **direct absolute-access census of the retained ASM corpus**, not proof that no indirect/overlay access exists. |
