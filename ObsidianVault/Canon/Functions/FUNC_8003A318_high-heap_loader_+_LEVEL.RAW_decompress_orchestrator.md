---
kind: function
id: FUNC_8003A318
aliases: [FUNC_8003A318, 0x8003a318]
address: 0x8003A318
name: high-heap_loader_+_LEVEL.RAW_decompress_orchestrator
status: static_seen
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: []
src_paths:
  - src_re/enemy_actor_spawn.c
patch_policy: unknown
---

# FUNC_8003A318 - high-heap loader + LEVEL.RAW decompress orchestrator

## Purpose

Loads compressed LEVEL.RAW into the high heap, then decompresses it chunk-by-chunk and builds the runtime geometry/collision resources.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8003A318.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8003A318`
- Name: `high-heap_loader_+_LEVEL.RAW_decompress_orchestrator`
- Original note: `ObsidianVault/Functions/FUNC_8003A318.md`
- Source path: `src_re/enemy_actor_spawn.c`

## C source excerpt

Source: `src_re/enemy_actor_spawn.c`

```c
/* ============================================================================
 * enemy_actor_spawn.c — regular-enemy spawning: chunk-31 records -> live actors
 * ----------------------------------------------------------------------------
 * Enemy-spawning track A (2026-07-03). Live-traced + DISC-POC-PROVEN (isolated
 * DuckStation, SCUS-94288; spider_walking.sav + cold-boot movie on an edited disc).
 *
 * HEADLINE: regular enemies spawn AT LEVEL LOAD from LEVEL.RAW chunk-31 placement
 * records. There is no proximity/area trigger for them; the only script-triggered
 * spawn is the scripted setpiece/bird actor (setpiece_spawn_8004d698.c). Their
 * per-frame driver is the mover-VM FUNC_8004C13C (0x8004c13c..0x8004d220) — the
 * separate "chaser AI @0x80095358" was a misread of the CAMERA struct.
 *
 * ---------------------------------------------------------------------------
 * DISC SOURCE — LEVEL.RAW chunk 31 (compressed; stride-0x1c placement records)
 * ---------------------------------------------------------------------------
 *   Record (0x1c bytes), first record at chunk-local +0x4:
 *     +0x00 s32 X   \
 *     +0x04 s32 Y    > FILE coords; runtime = coord << 5
 *     +0x08 s32 Z   /
 *     +0x0c u16 type  (LEVEL01 census: 0x0109 x7 [spider class incl. THE spider],
 *                      0x030a x3, 0x030b x5, 0x040a, 0x050d x5, 0x070e, 0x000b x4,
 *                      0x2223, 0x2427 x2 [pill beetle], 0x2528 x3 [worm]; seeds are
 *                      the same chunk/stride — chunk 31 = the general actor chunk)
 *     +0x0e u16 (hi of the type word; varies)
 *     +0x10/+0x14 u32 params (behavior/appearance words)
 *     +0x18 u32 flags
 *   LEVEL01 chunk 31: 64 record slots (many zero), decompressed size 1796.
 *
 * ---------------------------------------------------------------------------
 * LOAD-TIME PIPELINE (live-captured writer PCs, cold-boot movie)
 * ---------------------------------------------------------------------------
 *   1. The level-loader (FUNC_8003A318, 0x8003a318..0x8003c384; copy loop writes
 *      @0x8003b92c..) decompresses chunk 31 and copies the records to the RUNTIME
 *      SPAWN TABLE at 0x80094a38+ (EXE BSS; LEVEL01: spider rec @0x80094a38,
 *      others @0x80094cd8/0x80094cf4/0x80094d10 ... stride 0x1c).
 *   2. Enemy ACTORS are instantiated from those records into the 0x84-stride actor
 *      array (LEVEL01 spider = 0x8009fd80; 0x8009fd80+0x84 = 0x8009fe04 = next) and
 *      registered in damageable_object_ptr_table 0x80090748.
 *   3. Per-frame driving = the mover-VM FUNC_8004C13C (writer PCs 0x8004cd68/
 *      0x8004ce3c/0x8004cf70/0x8004cf7c/0x8004cfd8 hit the actor every frame).
 *
 * ---------------------------------------------------------------------------
 * LIVE ACTOR STRUCT (spawn-relevant fields; 0x84 stride)
 * ---------------------------------------------------------------------------
 *   +0x00 id (spider=9; indexes enemy_hp_table)      +0x04/08/0c current pos
 *   +0x28/2c/30 ANCHOR = record XYZ << 5 (the "home/spawn point")
 *   +0x5c state word (bit 0x1 targetable, 0x40 berry-tough, 0x880 recoil ...)
 *   +0x70 mover-VM program ptr (resident, e.g. 0x8007749a)
 *   +0x74 level-data ptr (0x8013xxxx region)
 *   +0x7c per-actor code/callback ptr (e.g. 0x80049e88)
 *   +0x80 BACKLINK to the runtime spawn record (0x80094a38 for the spider)
 *
 * ---------------------------------------------------------------------------
 * POC — MOVE THE SPAWN POINT ON DISC (PROVEN 2026-07-03)
 * ---------------------------------------------------------------------------
 *   Edited chunk 31 record @+0x4 (the spider): X 3095 -> 5095 (runtime 99040 ->
 *   163040), recompressed chunk 31 (recompress_level_raw.compress_chunk),
 *   rebuilt disc REBUILD/ABL_SPIDER_MOVE.bin/.cue (mkpsxiso abl_autolayout.xml).
 *   Cold boot + flik_to_level01_stall movie:
 *     - runtime record @0x80094a38 = (5095,-80,16750); original triple gone;
 *     - the spider actor spawned with anchor +0x28 == 163040 (the NEW home),
 *       record backlink +0x80 == 0x80094a38, registered in 0x80090748;
 *     - ALIVE + WORKING: pos/heading fields updating every frame, actor walking
 *       (moving toward Flik = aggro behavior intact).
 *   => enemy home/spawn-point relocation is a plain chunk-31 data edit.
 *
 * ---------------------------------------------------------------------------
 * CROSS-LEVEL VERIFICATION (2026-07-03, 14 enemy saves, byte+offset-exact)
 * ---------------------------------------------------------------------------
 *   Every live actor's backlinked runtime record was located in its level's
 *   actor chunk at the SAME offset (chunk-local +0x4 <-> table +0x0):
 *     scene 1  -> LEVEL01 chunk 31   (spider/bee/worm/pill/mosquito)
 *     scene 3  -> LEVEL03 chunk 27   (grasshopper/earthworm/wall_worm)
 *     scene 4  -> LEVEL04 chunk 30   (shell_bug)
 *     scene 5  -> LEVEL05 chunk 31   (Redbug)
 *     scene 6  -> LEVEL06 chunk 29   (canyon_bug/dragonfly)
 *     scene 10 -> LEVEL10 chunk 30   (huge_spider/Horsefly)
 *   - The actor-chunk INDEX varies per level (27..31); the runtime table is the
 *     fixed 0x80094a38 everywhere.
 *   - Runtime record slots MUTATE during play (live bookkeeping rewrites some
 *     slots; patrol targets step the actor +0x28 anchor) — the disc chunk is the
 *     pristine spawn source.
 *   - TYPE-WORD LOW BYTE == ACTOR ID (44/44): 0x0109->9 spider, 0x0b11->17
 *     huge_spider, 0x0422->34 dragonfly, 0x1a1e->30 canyon, 0x1712->18 shell,
 *     0x0c13->19 Redbug, 0x080f->15 grasshopper, 0x060c->12 earthworm,
 *     0x2629->41 wall_worm, 0x2528->40 worm, 0x2427->39 pill, 0x0f06->6 Horsefly.
 *     id indexes enemy_hp_table; high byte = variant/class.
 *
 * ---------------------------------------------------------------------------
 * ADD-NEW RECORD — PROVEN (2026-07-03, disc REBUILD/ABL_ENEMY_ADD)
 * ---------------------------------------------------------------------------
 *   Cloned the spider record (type 0x0109 + params) into the first free
 *   all-zero chunk-31 slot (LEVEL01 slot 31 @ local 0x368) at a new position
 *   near Flik's spawn. Cold boot:
 *     - runtime record slot 31 = the new record;
 *     - a NEW live actor instantiated at the new anchor (id 9, registered in
 *       the damageable table, running the spider VM program) and it CHASED
 *       Flik (moved 18.7k on approach);
 *     - **G_ENEMIES_REMAINING went 21 -> 22**: the permanent-kill quota is
 *       DERIVED FROM THE RECORD COUNT at load — custom levels automatically
 *       get correct all-enemies-defeated totals.
 *   => custom levels can ADD enemies: write a record (donor params of the
 *   wanted type) into any free slot; free slots exist in every level chunk.
 * ============================================================================ */

#include "re_types.h"

#define ENEMY_SPAWN_RECORD_TABLE 0x80094a38u /* runtime copy of chunk-31 records (LEVEL01) */
#define ENEMY_ACTOR_ARRAY_SPIDER 0x8009fd80u /* LEVEL01 spider actor (0x84 stride array)    */
#define ACTOR_ANCHOR_OFF         0x28        /* +0x28/2c/30 = record XYZ << 5 (home point)  */
#define ACTOR_RECORD_BACKLINK    0x80        /* -> the actor's runtime spawn record          */
#define ENEMY_RECORD_STRIDE      0x1c
#define FILE_TO_RUNTIME_SHIFT    5

void enemy_actor_spawn_refs(void)
{
    volatile unsigned t = ENEMY_SPAWN_RECORD_TABLE ^ ENEMY_ACTOR_ARRAY_SPIDER ^
                          (ACTOR_ANCHOR_OFF + ACTOR_RECORD_BACKLINK +
                           ENEMY_RECORD_STRIDE + FILE_TO_RUNTIME_SHIFT);
    (void)t;
}
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8003A318.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8003A318.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8003A318.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

