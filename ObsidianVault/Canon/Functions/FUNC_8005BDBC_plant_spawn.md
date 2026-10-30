---
kind: function
id: FUNC_8005BDBC
aliases: [FUNC_8005BDBC, 0x8005bdbc, plant_spawn]
address: 0x8005BDBC
name: plant_spawn
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
evidence:
  - src_re/plant_spawn_8005bdbc.c
  - EXP_2026-07-09_identity_reconciliation
src_paths:
  - src_re/plant_spawn_8005bdbc.c
patch_policy: unknown
---

# FUNC_8005BDBC - fcn 8003e760

> **RCA a3 identity fix (2026-07-09):** Renamed fcn_8003e760 -> **plant_spawn**. The old slug embedded a **foreign** address: `0x8003E760` is `token_descriptor_reskin` (13 callers), a DIFFERENT function from `0x8005BDBC` (2 callers) — both confirmed distinct/`exact` in [[EXP_2026-07-09_identity_reconciliation]].


## Purpose

Generated from C source coverage. The original-game behavior should be refined manually with call/read/write links.

## Known behavior

See the exact source excerpt below. Preserve `UNKNOWN`, `LIKELY`, and `TODO` labels from the source comments.

## Address / identity

- Address: `0x8005BDBC`
- Name: `fcn_8003e760`
- Source path: `src_re/plant_spawn_8005bdbc.c`

## C source excerpt

Source: `src_re/plant_spawn_8005bdbc.c`

```c
/* ============================================================================
 * plant_spawn_8005bdbc.c — seed→plant spawner + plant slot machinery [HRE-004 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESSES : fcn.8005bdbc (plant spawner, bounds 0x8005bdbc..0x8005bfb8,
 *                      functionBounds confidence "exact"); fcn.8003e760 (token
 *                      descriptor re-skin); plant behavior walker 0x8005bfbc..
 *                      (jump table 0x8001b848, types 2..14); plant renderer slot
 *                      read at 0x80021354..0x800213c8.
 * CONFIDENCE         : CONFIRMED selection law, type/extra table, slot layout,
 *                      model-table binding, override byte (all live-verified on
 *                      LEVEL01 fixture SCUS-94288_8.sav, 20/20 matrix combos).
 *                      Type-6/7 handler bodies partially decoded (labelled).
 * SOURCE NOTES       : ObsidianVault/Systems/Seed plant output binding.md,
 *                      Seed planting system.md, r2 disasm (MIPS LE, EXE base
 *                      file_off = vaddr - 0x8000f800).
 * KNOWN CALLERS      : 0x8004d4e0 (seed actor update — natural jump-on-seed path,
 *                      after the sink timer expires), 0x8005bd58 (local wrapper).
 * KNOWN CALLEES      : contact_alloc 0x80059e44 (type-6 berry/shield spawn, seed
 *                      sink dirt puffs).
 * KNOWN GLOBALS      : see #defines. Token counters 0x800a6598..9c are CONTIGUOUS,
 *                      one byte per lane (kinds 0x29..0x2d), stored as n*17.
 * UNRESOLVED         : purple-lane ctor 0x20..0x23 -> berry kind/marker map (table
 *                      B 0x8007941c rows 0x1f..0x23 undecoded); per-level plant
 *                      model manifest source on disc; scene-0x11 special seed path.
 *
 * IMPORTANT CONTEXT:
 *   fcn.8003e760 (called on token PICKUP) does NOT choose the plant — it only
 *   re-skins the pickup sprite descriptor. The plant is chosen at PLANT time
 *   (jump-on-seed) by fcn.8005bdbc from the seed record's color byte + the lane
 *   counter, or from a per-seed override byte. Models bind 1:1: type N renders
 *   PLANTNN.ALL (per-level table 0x800a649c; NULL = model not loaded in this
 *   level -> functioning but invisible actor).
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LBU(p)  (*(uint8_t  *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))
#define SH(p,v) (*(uint16_t *)(p) = (uint16_t)(v))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))

#define G_SCENE_ID            0x80082504u
#define G_SEED_COUNTERS       0x800a6598u /* [5] lanes: 0x29 orange,0x2a blue,0x2b green,0x2c,0x2d */
#define G_PLANT_TYPE_TABLE    0x8007a448u /* [20] {u16 type, u16 extra}, idx = color*4+count-1 */
#define G_PLANT_DATA_TABLE    0x8007a40cu /* [15] ptr -> growth-anim script per type (0 = none) */
#define G_PLANT_SLOTS         0x80090bf0u /* [20] stride 0x30 */
#define G_PLANT_SLOT_CURSOR   0x800822b8u /* next slot, wraps at 0x14, skips occupied */
#define G_PLANT_MODEL_TABLE   0x800a649cu /* [15] per-LEVEL model ptrs; type N -> PLANTNN.ALL image */
#define G_PLANT_BEHAV_TABLE   0x8001b848u /* [13] handlers, index type-2 (see list at bottom) */
#define G_PLANT_NAME_TABLE    0x8001baf8u /* "plants\plant01".."plants2\plant14", stride 0x10 */
#define G_OBJ_DESC_LIST       0x80096b98u /* object_pointer_list: kind -> render descriptor */

typedef struct {

extern ContactRecord *contact_alloc(int32_t x, int32_t y, int32_t z, int ctorType, int stackArg);












void fcn_8003e760(int objIndex, int level)
{
    uint8_t *desc = (uint8_t *)(uintptr_t)LW(G_OBJ_DESC_LIST + objIndex * 4);
    SH(desc + 6, (LHU(desc + 6) & 0xfffcu) + level);
    for (int off = 8; off < 0x14; off += 2) {
        SB(desc + off, (LBU(desc + off) & 0x3f) | (level << 6));
    }
}
/* Full source is in the listed source path. */
```

## Evidence

- Source: `src_re/plant_spawn_8005bdbc.c`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`
