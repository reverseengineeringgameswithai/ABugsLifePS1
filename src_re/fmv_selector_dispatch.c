/* Documentation-grade reconstruction of pristine FMV selector ownership.
 *
 * This file is not a build input and makes no matching-C claim. Addresses,
 * jump targets, tables, call sites, and completion-request xrefs are
 * regenerated from hash-pinned SCUS, MEMORY.BIN, and FMV.BIN bytes by
 * tools/phase4_fmv_static_owners.py.
 */
#include <stdint.h>

enum {
    FMV_SELECTOR_TT = 0,
    FMV_SELECTOR_DLOGO = 1,
    FMV_SELECTOR_AD = 2,
    FMV_SELECTOR_LEV1A = 10,
    FMV_SELECTOR_LEV1B = 11,
    FMV_SELECTOR_LEV15C = 40,
    FMV_SELECTOR_LEV15D = 41,
    FMV_SELECTOR_ALT1 = 42,
    FMV_SELECTOR_ALT2 = 43,
    FMV_SELECTOR_ALT3 = 44,
    FMV_SELECTOR_INTRO = 45,
    FMV_SELECTOR_LOSE = 46,
    FMV_SELECTOR_COUNT = 47,
};

/* 0x8007A08B, indexed by the resident music/progress ID. */
static const uint8_t level_a_selector[16] = {
    FMV_SELECTOR_TT,
    10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38,
};

/* 0x80077FE3. ID zero branches around the call; 0xFF is its sentinel. */
static const uint8_t level_b_selector[16] = {
    0xFF,
    11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39,
};

/* Exact arithmetic at 0x8004FFAC..0x8004FFD8. The byte write wraps, then
 * the selector add occurs in the fmv_bin_load call's delay slot. */
static unsigned bonus_clip_selector(uint8_t old_cursor)
{
    uint8_t next = (uint8_t)(old_cursor + 1);
    return (unsigned)next + FMV_SELECTOR_LEV15D;
}

/* FMV.BIN 0x800CAC10 is a residency-qualified u32 completion request.
 * The complete aligned xref census has three writers and one reader:
 *
 *   0x800B6B24  write 1 after frame-order regression
 *   0x800B6B48  write 1 after reaching the selected limit
 *   0x800B6DD0  clear at stream start
 *   0x800B743C  read inside player 0x800B6D68..0x800B752C
 *
 * The pristine LEV1A no-input control attributes the selected-limit path:
 * 0x800B6DC0 selects 386, 0x80070A8C reaches backloc 384 and then 385,
 * and 0x800B6B48 publishes completion request 0 -> 1. No decoded-record
 * stop-latch write occurs while exact FMV.BIN remains resident. This runtime
 * fact is bounded to that control; it does not generalize pause/error policy.
 *
 * A distinct natural completed-Level-B control reaches 0x8005031C with
 * progress ID 1. Its load and JAL delay slots make fmv_bin_load observe
 * selector 11/mode -1, then 0x800B6DC0 selects 485. Unlike LEV1A, this route
 * publishes completion 0 -> 1 through frame-order-regression writer
 * 0x800B6B24 before the common StClearRing/callback teardown path. The paired
 * all-neutral input reaches neither 0x8005031C, its loader entry nor limit
 * 485; two different frontend loader calls are retained outside that negative.
 *
 * At 0x800B7444, request == the s4 sentinel 1 branches back to the player's
 * stop path at 0x800B6E38. Teardown is 0x800B7464..0x800B752C. The player has
 * 50 direct calls to 30 unique targets and no jalr site, so its call frontier
 * is closed without claiming higher-level stop, error, or viewer policy.
 */
struct fmv_region_b_state {
    uint8_t unknown_0000[0x15488];
    volatile uint32_t completion_request;
};

/* Selector ownership boundary:
 * - 0/1/45: resident boot shell;
 * - 10..39: resident level-A/B tables for IDs 1..15;
 * - 40: finale; 41: all-level completion;
 * - 42..46: the bonus clip cursor's ordinary 0..4 sequence;
 * - 46 also has the game-over call;
 * - 2 (`fmv/ad.str`, limit 1410) is unreachable from the complete pristine
 *   direct argument sources. All 23 resident, level, MEMORY and FMV code-owner
 *   images contain neither a literal loader pointer nor a compiler-standard
 *   LUI/ADDIU or LUI/ORI materialization. Exact def-use closes the four
 *   formerly unresolved resident jalr sites: three target BIOS vector 0xB0;
 *   the fourth receives a GPU callback argument that cannot be supplied the
 *   unmaterialized loader address. The retained 139-site census also installs
 *   no fmv_bin_load callback;
 * - 3..9 and >=47 take the no-stream path in FMV.BIN.
 * This is an unused-manifest-row conclusion, not evidence for movie-viewer
 * behavior. This does not close the wider static frontier: libcd/libpress
 * callbacks, frontend/viewer and level-transition consumers, remaining
 * transition writers, and exceptional-path functions remain open.
 */
