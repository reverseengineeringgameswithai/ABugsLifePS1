---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Enemy spawn architecture.md
aliases:
  - "Enemy spawn architecture"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Enemy spawn architecture.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Enemy_spawn_architecture.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Enemy spawn architecture
type: system
updated: 2026-07-03
confidence: CONFIRMED-live + disc-POC
tags: [system, enemy, spawn, chunk-31, setpiece, mover-vm, modding]
---

# Enemy spawn architecture (how enemies come to exist)

> Enemy-spawning tracks C+A (2026-07-03). Live + static + **disc POC proven** (moved the
> LEVEL01 spider's home on disc; it cold-boot spawned at the new point and still works).
> RE sources: `src_re/enemy_actor_spawn.c` (regular enemies) + `src_re/setpiece_spawn_8004d698.c`
> (scripted setpiece). Carries a **major correction** to [[Enemy AI state machine]].

## The two spawn lanes

| Lane | Who | When | Source data | Actor |
|---|---|---|---|---|
| **Load-time** | ALL regular enemies (spider/worm/pill/…) | at level load, unconditionally | **LEVEL.RAW chunk-31 records** (stride 0x1c) | 0x84-stride actor array (`0x8009fd80`+…), registered in `damageable_object_ptr_table 0x80090748` |
| **Script-triggered** | the scripted setpiece/bird (`FUNC_8004DD98`'s subject) | when the script writes **`[0x800824dc] = -1`** | LEVEL.DAT 16-waypoint path records (table `0x80096dc8`; LEVEL01 `0x94c/0xa10/0xad4`) | `setpiece_actor 0x80090bc0` |

**There is no proximity-triggered enemy spawn.** Regular enemies exist from load; the only gated spawn is the setpiece (`setpiece_spawn_manager 0x8004d698`, called per-frame by the gameplay state machine; fires once when the trigger var holds −1, then sets it to −2). This is why teleporting Flik into a "spawn area" never spawned anything.

## Corrections (2026-07-03)
- **`0x80095358` is the CAMERA-state struct** (GAP-0028's), NOT a "chaser slot". Live: it lags Flik at ~half speed, sits ~24k above, distance grows (follow smoothing `C+=(target−C)>>3`); `+0x20` is the 12-bit camera θ. `FUNC_8004DF18` = the camera follow-law. The [[Enemy AI state machine]] "chaser AI" story at that address is contaminated (banner added there).
- The "chaser spawn-area records" (LEVEL.DAT `0x94c/0xa10/0xad4`) are the **setpiece/bird flight paths**, not chaser patrol areas.
- Regular "chasers" (spider etc.) are **mover-VM actors** like the worm: the LEVEL01 spider's per-frame writer PCs (`0x8004cd68/ce3c/cf70/cf7c/cfd8`) live inside **`FUNC_8004C13C`** (0x8004c13c..0x8004d220). One driver family for all regular enemies.

## Regular-enemy pipeline (live-captured)
1. **Disc**: LEVEL.RAW **chunk 31** = the general actor-placement chunk (seeds too). Record (0x1c B, first @ chunk-local +0x4): `X,Y,Z` s32 **file coords** (`runtime = <<5`), `+0xc` u16 **type** (LEVEL01: spider-class `0x0109` ×7, `0x2427` pill ×2, `0x2528` worm ×3, `0x030a/0x030b/0x040a/0x050d/0x070e/0x000b/0x2223`), `+0x10/+0x14` params, `+0x18` flags. LEVEL01: 64 slots, decompressed 1796 B.
2. **Load**: the level loader (**`FUNC_8003A318`**, copy loop @`0x8003b92c`+) copies the records to the **runtime spawn table `0x80094a38`+** (spider @`0x80094a38`; others `0x80094cd8/cf4/d10`…).
3. **Instantiate**: actors built in the 0x84-stride array; key fields: `+0x00` id → `enemy_hp_table` · **`+0x28/2c/30` ANCHOR = record XYZ<<5 (the home/spawn point)** · `+0x70` mover-VM program ptr · `+0x74` level-data ptr · `+0x7c` per-actor callback (`0x80049e88`) · **`+0x80` backlink to its runtime spawn record**. Registered in `0x80090748`.
4. **Drive**: mover-VM `FUNC_8004C13C` every frame.

## POC — spawn-point relocation on disc (PROVEN)
Moved the spider's chunk-31 record `X 3095→5095` (+64000 runtime), recompressed chunk 31 (`recompress_level_raw.compress_chunk`), rebuilt **`REBUILD/ABL_SPIDER_MOVE.bin/.cue`**. Cold boot + `flik_to_level01_stall` movie:
- runtime record @`0x80094a38` = the moved triple, original absent;
- spider actor spawned with **anchor `+0x28` = 163040** (the new home), backlink `+0x80 = 0x80094a38`, registered;
- **alive + working**: pos/heading updating every frame, walking (closing on Flik — aggro intact).

⇒ **Moving an enemy's home/spawn point = a plain chunk-31 data edit** (decompress → move XYZ → recompress → rebuild). Same pipeline as the proven ABL_WORM/ABL_PILL discs — now understood as the universal regular-enemy mechanism, not a stationary-only special case.

## Modding levers
- **Relocate**: edit the record XYZ — ✅ PROVEN (`ABL_SPIDER_MOVE`).
- **Add** — **✅ PROVEN (2026-07-03, `REBUILD/ABL_ENEMY_ADD`)**: cloned the spider record into a free zero slot at a new position → cold boot: a NEW live actor spawned there (registered, running the spider VM program, chased Flik 18.7k). **Bonus: `G_ENEMIES_REMAINING` went 21→22 — the permanent-kill quota is DERIVED from the record count at load**, so custom levels get correct all-defeated totals automatically.
- **Remove**: zero a record (untested; the loader already skips zero slots).
- **Re-type**: `+0xc` type swap (untested — model residency caveat applies).

## Cross-level verification (2026-07-03, 14 enemy saves)
The architecture holds in **every** enemy save — each live actor's backlinked runtime record was found **byte- and offset-exact** in its level's actor chunk (chunk-local `+0x4` ↔ runtime table `+0x0`):

| Scene | Enemies (saves) | Disc source | Vote |
|---:|---|---|---|
| 1 | spider, bee, worm, pill, mosquito | **LEVEL01 chunk 31** | 5/5 saves |
| 3 | grasshopper, earthworm, wall_worm | **LEVEL03 chunk 27** | 1/1 · 2/3 · 1/3 |
| 4 | shell_bug | **LEVEL04 chunk 30** | offset-exact |
| 5 | Redbug | **LEVEL05 chunk 31** | 5/5 records |
| 6 | canyon_bug, dragonfly | **LEVEL06 chunk 29** | 3/4 · 3/3 |
| 10 | huge_spider, Horsefly | **LEVEL10 chunk 30** | 5/5 · 4/4 |

- **The actor-chunk INDEX varies per level** (27/29/30/31) — same role, shifted numbering (per-level chunk counts differ). The runtime table is the fixed `0x80094a38` everywhere.
- **Runtime record slots MUTATE during play** (live bookkeeping overwrites some slots) — the sub-unanimous votes and the sweep's `anchor≠record` rows are mutated slots/stepped patrol targets, not counter-evidence. The pristine spawn source is the disc chunk.
- **Type-word low byte == the actor id (44/44 actors)**: spider `0x0109`→id 9, huge_spider `0x0b11`→17, dragonfly `0x0422`→34, canyon `0x1a1e`→30, shell `0x1712`→18, Redbug `0x0c13`→19, grasshopper `0x080f`→15, earthworm `0x060c`→12, wall_worm `0x2629`→41, worm `0x2528`→40, pill `0x2427`→39, Horsefly `0x0f06`→6 … The id indexes `enemy_hp_table`; the high byte = variant/class word. This is the key to the per-level **enemy roster** (RCG-006 residual).

## Residuals
- The actor-instantiation function itself (record → actor construction; between the loader copy and the first mover-VM frame) — writer capture got the copy loop + per-frame driver; the constructor PC wasn't isolated.
- Type-word **high** byte semantics + the `+0x10/+0x14/+0x18` param words; a full id→retail-name roster table.
- Remove/re-type levers untested (ADD is proven).
- The runtime-slot mutation semantics (what rewrites a record slot during play — respawn/kill bookkeeping?).

## Related
[[Enemy AI state machine]] (correction banner) · [[Enemy death and permanence]] · [[Event and scripting system]] (mover-VM) · [[Seed planting system]] (same chunk) · [[Core - Camera and Projection]] (`0x80095358`) · [[Retail Gameplay Completeness Gap Audit]] RCG-006
