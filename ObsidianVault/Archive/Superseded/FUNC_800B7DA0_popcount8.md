---
kind: archived_canon_note
id: LEGACY_FUNC_800B7DA0_popcount8
aliases: [LEGACY_FUNC_800B7DA0_popcount8]
address: 0x800B7DA0
name: popcount8
status: superseded
canonical_address: false
superseded_by: FUNC_800B7DA0_results_screen_evaluate_and_draw
confidence: medium
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - src_re/level_complete_results_800b7da0.c
src_paths:
  - src_re/level_complete_results_800b7da0.c
patch_policy: unknown
---

# FUNC_800B7DA0 - popcount8

## Purpose

Generated from C source coverage. The original-game behavior should be refined manually with call/read/write links.

## Known behavior

See the exact source excerpt below. Preserve `UNKNOWN`, `LIKELY`, and `TODO` labels from the source comments.

## Address / identity

- Address: `0x800B7DA0`
- Name: `popcount8`
- Source path: `src_re/level_complete_results_800b7da0.c`

## C source excerpt

Source: `src_re/level_complete_results_800b7da0.c`

```c
/*
 * level_complete_results_800b7da0.c -- RE notes for the LEVEL COMPLETE results
 * overlay in BITS/MEMORY.BIN.
 *
 * Status 2026-07-07:
 * - The row-2 FLIK/word renderer is disc-persisted for ALLMODS through
 *   tools/training_word_pickups.py by patching BITS/MEMORY.BIN, not by a
 *   resident EXE cave.
 * - The Training word path draws the same tile ids used by the in-level and
 *   SELECT-panel TRAINING word, pumps those tiles through the native 16-frame
 *   animated-texture uploader, and caps the count-up at the popcount of the
 *   collected-letter bitmask.
 * - Do not use 0x800BE444 as scratch. Flik's Journey uses that region as
 *   level-select vine/leaf data; overwriting it removes the visible vine path.
 */
#include <stdint.h>

#define RESULT_MEMORY_BIN_BASE          0x800B5788u
#define RESULT_FUNC_START               0x800B7DA0u
#define RESULT_FUNC_END                 0x800B8788u
#define RESULT_ROW2_START               0x800B80A8u
#define RESULT_ROW2_RESUME              0x800B8258u
#define RESULT_ROW2_SPAN                (RESULT_ROW2_RESUME - RESULT_ROW2_START)

#define RESULT_PROGRESS_BITS            0x800A65A2u
#define RESULT_COUNT_TARGET             0x800B8248u
#define RESULT_WORD_LEN                 0x800B8249u
#define RESULT_TILE_TABLE               0x800B8250u
#define RESULT_MEDAL_LEN_CAVE           0x800B81FCu
#define RESULT_MEDAL_DIM_CAVE           0x800B8214u
#define RESULT_MEDAL_FAST_SITE          0x800B8380u
#define RESULT_MEDAL_DIM_SITE           0x800B8388u
#define RESULT_MEDAL_COMPARE            0x800B83ACu

#define RESULT_ANIM_TABLE               0x80089638u
#define RESULT_EXTRA_DESC_26            0x80082024u
#define RESULT_EXTRA_DESC_27            0x80082018u
#define RESULT_GOLDEN_CLUT              0x3677u

#define RESULT_DRAW_DIGIT               0x80025F54u
#define RESULT_DRAW_GLYPH_LIT           0x800260F8u
#define RESULT_DRAW_GLYPH_DIM           0x80026588u
#define RESULT_UPLOAD_ANIM_FRAME        0x80026DF4u

/*
 * Original retail row 2:
 * - four unrolled F/L/I/K blocks;
 * - denominator literal 4 at 0x800B8254;
 * - later medal reveal compares s6 against literal 4;
 * - s6 count target is table[progress_bits], but the retail table is only
 *   meaningful for reachable 4-bit masks.
 *
 * The table bug is why forcing 0xff in RAM made the counter continue into
 * garbage values and delayed row 3's reveal threshold.
 */
struct result_row2_patch_layout {
    uint8_t collected_count; /* At 0x800B8248: inline popcount(progress_bits). */
    uint8_t word_len;        /* At 0x800B8249: staged active word length. */
    uint8_t pad[6];
    uint8_t tile_ids[8];  /* At 0x800B8250: 10 11 12 13 26 13 26 27. */
};

static uint8_t popcount8(uint8_t value)
{
    uint8_t n = 0;
    for (uint8_t i = 0; i < 8; i++) {
        n += (uint8_t)(value & 1u);
        value >>= 1;
    }
    return n;
}

/*
 * Pseudocode for the patched row-2 replacement at 0x800B80A8.
 * Registers follow the live routine convention: s6 is the animated numerator,
 * s7 becomes the active word length, and s0 is the slot index.
 */
static void patched_result_row2_pseudocode(uint8_t progress_bits,
                                           uint8_t staged_word_len,
                                           uint8_t s6,
                                           uint8_t spin_phase)
{
    static const uint8_t training_tiles[8] = {
        0x10, 0x11, 0x12, 0x13, 0x26, 0x13, 0x26, 0x27
    };

    /*
     * Result-time scene/RAW loading can drift the two extra descriptors' CLUT
     * halfwords, so the row stamps them to the native gold CLUT before drawing.
     */
    /* SH(RESULT_EXTRA_DESC_26 + 6, RESULT_GOLDEN_CLUT); */
    /* SH(RESULT_EXTRA_DESC_27 + 6, RESULT_GOLDEN_CLUT); */

    const uint8_t collected_count = popcount8(progress_bits);
    const uint8_t word_len = staged_word_len;  /* Read from RESULT_WORD_LEN. */
    /* SB(RESULT_COUNT_TARGET, collected_count); retail count-up readers use this target. */

    for (uint8_t i = 0; i < word_len; i++) {
        const uint16_t x = (uint16_t)(8u + (i * 10u));
        const uint8_t tile = training_tiles[i];

        /*
         * LEVEL00/LEVEL2.RAW carries type-0x22 strip records for these six tile
         * ids, so anim_table[tile] is resident on the results screen. Pump
         * before the lit/dim branch: both draw paths use the same tile cell, and
         * uncollected dim letters otherwise freeze on one face.
         */
        /* fcn_80026df4(tile, 0, (spin_phase + i * 2) & 0x0f) */

        if (progress_bits & (uint8_t)(1u << i)) {
            /* fcn_800260f8(x, 116, tile, 0) */
        } else {
            /* fcn_80026588(x, 116, tile, 0, 0x40, 0x20, 0x20) */
        }
    }

    const uint16_t counter_x = (uint16_t)(8u + (word_len * 10u) + 88u);
    /* fcn_80025f54(counter_x + 0,  116, 56, s6) */
    /* fcn_80025f54(counter_x + 20, 116, 56, 10) */
    /* fcn_80025f54(counter_x + 40, 116, 56, word_len) */
}

/*
 * Verification, ALLMODS 2026-07-07:
 * - build/ABL_ALLMODS.bin sha256
 *   fe11deabc6b84a94c6a00d28081a34f6669c48d4e473dc46e7cf0a0b132bdc2a.
 * - build/training_word_BITS_MEMORY.BIN sha256
 *   f8d447f30877987edbf5e0d58f2c79a8656ba449faf87199d8ccd1c6021ec276.
 * - build/training_word_LEVEL00_LEVEL2.RAW sha256
 *   cc5937ae9de1f466e26c367a72180b96f7b379b31b496fe2d22e9e1d4ae54afe.
 * - ALLMODS_COLLECTING_TRAINING.movie.json stayed reproducible through the
 *   result-screen window: frame 7218 was scene 0x11 with progress 0xff; frame
 *   8000 and 8300 were the results overlay and movie.status still reported
 *   reproducible.
 * - Result frame 8000 had anim_table[0x10], anim_table[0x26], and
 *   anim_table[0x27] nonzero, proving the result RAW strip records loaded.
 * - Live descriptors for 0x10,0x11,0x12,0x13,0x26,0x27 all carried CLUT
 *   0x3677 after the row-time stamp.
 * - execTrace at 0x800B8258 captured counter base s0=0xB0 (176), s7=8,
 *   and s6 reaching 8. execTrace at 0x800B853C captured v0=8 throughout
 *   the cap compare, so the counter stops at the collected count.
 * - Captures /tmp/traindimfinal/result_8000.png and result_8300.png show
 *   the tighter staggered spinning TRAINING row clear of the capped 8/8 counter.
 * - Forced-uncollected visual check at result frame 8000 wrote 0x800A65A2=0x00;
 *   state bytes became 00 08, and /tmp/traindimspin/dim_a.png, dim_b.png, and
 *   dim_c.png showed the dim TRAINING row changing spin phase instead of freezing.
 */
```

## Evidence

- Source: `src_re/level_complete_results_800b7da0.c`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`
