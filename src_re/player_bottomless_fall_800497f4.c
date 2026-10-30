/* ============================================================================
 * player_bottomless_fall_800497f4.c — native scene-relative fall/respawn guard
 * ----------------------------------------------------------------------------
 * DOCUMENTATION-GRADE SLICE ONLY. This reconstructs 0x800497F4..0x80049870 at
 * the tail of FUNC_80048138; it is not a standalone retail function and is not
 * linked into the MOD.
 *
 * When ungrounded, the preceding native vertical block adds 256 to player VY,
 * caps it at 4096, and commits that velocity at 0x80048D8C. The fall test is
 * scene-relative rather than a single universal Y constant:
 *
 *     player_y > scene_fall_y_base + 8192
 *
 * If no transition is active and the local guard is not positive, the block
 * initiates FUNC_8004A700 mode 2. That path stores transition state 2 at
 * 0x8004A9F4 and fade timer 23 at 0x8004AA00. The respawn handler at
 * 0x8005B134 restores player X/Y/Z from player+0x50/+0x54/+0x58 and performs
 * the paired life adjustment at 0x8005B348. The temporary byte increment at
 * 0x80049858 must therefore not be read in isolation as the life-loss policy.
 *
 * P70 causal confirmation used a media-validated pristine LEVEL01 save and the
 * narrow mutation Y=(scene base+8192)+1, VY=4096, air_state=2, grounded=0.
 * It observed one execution each at 0x80049858, 0x80049868, 0x8004A9F4, and
 * 0x8005B348, followed by a grounded safe-anchor respawn with the same displayed
 * life count. This matches the solved SCUS-94288 assembly.
 * ============================================================================ */

#include "re_types.h"

#define PLAYER_Y_VALUE          (*(volatile int32_t *)0x800a6504)
#define G_SCENE_FALL_Y_BASE     (*(volatile int32_t *)0x800822b4)
#define G_TRANSITION_STATE      (*(volatile int16_t *)0x800823a0)
#define G_FALL_REQUEST_GUARD    (*(volatile int32_t *)0x800824d4)
#define G_DISPLAYED_LIVES       (*(volatile uint8_t *)0x800a65a0)

extern void FUNC_8004A700(int32_t x, int32_t z, void *scratch, int32_t mode);

static void player_bottomless_fall_guard_slice(void)
{
    int32_t unused_scratch = 0;

    if (PLAYER_Y_VALUE <= G_SCENE_FALL_Y_BASE + 8192)
        return;                                      /* branch at 0x8004980C */
    if (G_TRANSITION_STATE != 0)
        return;                                      /* 0x80049820 */
    if (G_FALL_REQUEST_GUARD > 0)
        return;                                      /* 0x80049830 */

    G_FALL_REQUEST_GUARD++;                          /* 0x80049844 */
    if (G_DISPLAYED_LIVES < 9)
        G_DISPLAYED_LIVES++;                         /* 0x80049858 */

    FUNC_8004A700(0, 0, &unused_scratch, 2);         /* JAL 0x80049868 */
}

void player_bottomless_fall_refs(void)
{
    (void)player_bottomless_fall_guard_slice;
}
