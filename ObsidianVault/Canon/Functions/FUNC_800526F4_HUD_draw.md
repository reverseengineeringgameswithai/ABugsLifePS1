---
kind: function
id: FUNC_800526F4
aliases: [FUNC_800526F4, 0x800526f4]
address: 0x800526F4
name: HUD_draw
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
  - src_re/hud_800526f4.c
patch_policy: unknown
---

# FUNC_800526F4 - HUD draw

## Purpose

Draws and animates the HUD panels each frame from the pickup/progress globals. The visible read-out of the pickup pipeline.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_800526F4.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x800526F4`
- Name: `HUD_draw`
- Original note: `ObsidianVault/Functions/FUNC_800526F4.md`
- Source path: `src_re/hud_800526f4.c`

## C source excerpt

Source: `src_re/hud_800526f4.c`

```c
/* ============================================================================
 * hud_800526f4.c  — HUD draw (grain / FLIK / seed meters) [PHASE 6 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.800526f4  (size 3908 bytes, 0x800526f4..0x80053634)
 * CONFIDENCE       : CONFIRMED pickup/HUD data sources and draw-call arguments for
 *                    grain, FLIK letters, and seed meters. Peripheral scene-specific
 *                    panels are summarized and labelled UNKNOWN/TODO.
 * SOURCE NOTES     : docs/EXECUTABLE_AND_OVERLAYS.md (HUD), docs/EXPERIMENT_LOG.md
 *                    (seed meters), Phase 5 pickup_handlers_*, r2 disasm.
 * KNOWN CALLERS    : fcn.8004ecd4 / fcn.8004f478. a0 is copied to s3 and used as
 *                    the per-frame animation increment for HUD pulse halfwords.
 * KNOWN CALLEES    : fcn.800260f8 (draw HUD number/glyph from table), fcn.80025f54
 *                    (draw sprite/tile), fcn.80026588 / fcn.80026a68 / fcn.80026df4
 *                    (rect/effect helpers), fcn.8005044c, fcn.80026d78.
 * KNOWN GLOBALS    : G_GRAIN_COUNT, G_SEED_CTR_ORANGE..GREEN, G_FLIK_PROGRESS_BITS,
 *                    FLIK record ptrs 0x800a0220/0430/0a60/0d78 (flag +0x1b),
 *                    HUD pulse halfwords 0x800b0188/18c/190/194/198.
 * UNRESOLVED       : exact sprite atlas semantics; non-pickup scene-specific panels
 *                    after 0x80053264; true ownership of several animation timers.
 *
 * CONFIRMED PICKUP HUD MODEL:
 *   - Grain count: lbu 0x800a65a1, target 0x32. Draws when pulse 0x800b018c > 0.
 *   - Seed meters: loop over 0x800a6598+i for i=0..2. Counter high nibble selects
 *     rows in tables near 0x80078e66/67; low bits/phase choose animated digits/icons.
 *   - FLIK bit HUD: byte 0x800a65a2 uses bits 0/1/2/3 for 0x10/0x11/0x12/0x13.
 *   - FLIK record HUD: pointers at 0x800a0220/0430/0a60/0d78, collected flag +0x1b;
 *     if set, draw icons at x=0x54/0x7c/0xa4/0xcc, y from pulse 0x800b0194,
 *     tile IDs 0x32/0x34/0x35/0x33, plus a second tile 0x36 for the last letter.
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LBU(p)  (*(uint8_t  *)(p))
#define SH(p,v) (*(uint16_t *)(p) = (uint16_t)(v))

#define G_SCENE_ID              0x80082504u
#define G_MASTER_GAME_STATE     0x800823a0u
#define G_GAME_MODE             0x80082220u /* UNKNOWN; compared to 2/3 */
#define G_HUD_FLASH_TIMER       0x80082470u /* UNKNOWN */
#define G_HUD_BLINK_COUNTER     0x800822b0u /* CONFIRMED increments mod 0x20 */
#define G_HUD_FLAGS_2488        0x80082488u /* UNKNOWN bit flags */
#define G_HUD_OBJECT_PTR        0x8008242cu /* UNKNOWN struct ptr for seed HUD */
#define G_HUD_OBJECT_STATE      0x800b5774u /* UNKNOWN scene 7 bitfield */
#define G_HUD_OBJECT_ICON       0x800b577cu /* UNKNOWN scene 7 icon */
#define G_FLIK_PTR_F            0x800a0220u
#define G_FLIK_PTR_L            0x800a0430u
#define G_FLIK_PTR_I            0x800a0a60u
#define G_FLIK_PTR_K            0x800a0d78u
#define G_HUD_PULSE_PROGRESS    0x800b0188u
#define G_HUD_PULSE_GRAIN       0x800b018cu
#define G_HUD_PULSE_SEED        0x800b0190u
#define G_HUD_PULSE_FLIK        0x800b0194u
#define G_HUD_PULSE_MISC        0x800b0198u
#define G_HUD_PROGRESS_LATCH    0x800b018au
#define G_HUD_SEED_LATCH        0x800b0192u
#define G_HUD_GRAIN_DIGITS      0x800b018eu /* packed tens/ones: tens | (ones << 8) */
#define G_HUD_MISC_DIGITS       0x800b019au
#define G_HUD_MISC_DIGITS2      0x800b019cu
#define G_UNK_COUNTER_6594      0x800a6594u
#define G_SEED_NIBBLE_MASK      0x800b0196u
#define G_SEED_ICON_TABLE_A     0x80078e66u
#define G_SEED_ICON_TABLE_B     0x80078e67u
#define G_SEED_BOX_TABLE        0x80078e58u
#define G_SIN_TABLE             0x80074970u
#define G_UNK_800910A8         0x800910a8u

extern void fcn_80025f54(int x, int y, int tile, int variant);
static int hud_wave_y_from_pulse(int16_t pulse, int base)
{
    /* MIPS clamps/mirrors the 0x1000-ish pulse, indexes 0x80074970 halfword
     * table, sign-extends the high byte, then applies a base offset. */
    int32_t p = pulse;
    if (p > 0x0c00) p -= 0x0800;
    else if (p > 0x0400) p = 0x0400;
    int16_t wave = (int16_t)LHU(G_SIN_TABLE + p * 2);
    return ((int32_t)(wave << 16) >> 24) + base;
}
/* Full source is in the listed source path. */
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_800526F4.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_800526F4.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_800526F4.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

