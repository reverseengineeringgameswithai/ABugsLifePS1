/* =============================================================================
 * FUNC_8003633C  --  player movement integrator: collision-resolved Y commit (TAIL)
 * =============================================================================
 * REVERSE-ENGINEERED original code (decompiled from SCUS-94288). This documents the
 * Y-RESOLUTION TAIL of the integrator -- the part the Tier-3 custom-collision hook
 * attaches to -- NOT the whole (large) function. The MOD that hooks it is in
 * mod/caves/tier3_collision.c + mod/patch_tier3_collision.asm.
 *
 * Per frame the integrator writes Flik's Y (s7 = player pos = 0x800A6500; X@+0, Y@+4,
 * Z@+8, w@+0xc) up to three times:
 *   (1) GRAVITY            0x80036380  sw v0,4(s7)   after  addiu v0,v0,-3200
 *   (2) COLLISION COMMIT   0x80036cec  sw v1,4(s7)   from the resolved pos at sp+0x1c
 *   (3) FINAL +3200 ADJUST 0x80036d54  sw a0,4(s7)   a0 = Y + 3200   <-- last writer
 * The native floor source is the collision system (per-sector origin-Y + the swept
 * planes resolved by FUNC_800345CC). Tier-3 replaces writer (3) so OUR mesh decides Y.
 *
 * -----------------------------------------------------------------------------
 * Engine ABI / addresses (from disassembly):
 *   s7   = 0x800A6500   player position (X,Y,Z,w as int32)
 *   s5   = 0x800A652C   velocity vector (VX,VY,VZ) -- confirmed live at 0x80036d00
 *   sp+0x18/+0x1c/+0x20/+0x24 = the resolved next position (X,Y,Z,w) staged on stack
 *   sp+0x28 = pointer to a small contact-flag struct (bytes at +0 / +1)
 *   FUNC_80035F24, FUNC_800345CC (swept-plane resolver), FUNC_80035280 = collision passes
 *   0x800A6510 = PREVIOUS-TICK position mirror (X,Y,Z; confirmed live 2026-07-11:
 *          lags 0x800A6500 by exactly one 30fps game tick, refreshed at tick start).
 *          The tail also compares Flik.X against it (edge/limit check).
 *   3200 = a fixed Y offset bracketing the collision pass (contact-point vs origin);
 *          gravity subtracts it before resolution, the tail adds it back after.
 *
 * UNRESOLVED-MOVE FALLBACK (0x80036d00..0x80036d44, found 2026-07-11 via the
 *   TRAINING cage roof): when the collision loop does NOT settle, an alternate
 *   commit path skips the resolved-stack store and instead adds the velocity
 *   vector to the player position in place (player.XYZ += [s5]).  Importantly,
 *   the movement code's RAW pre-integrator position proposal (which the
 *   resolved commit at 0x80036cd8..0x80036cf4 normally DISCARDS) survives on
 *   this path.  Standing ~15k above the sector floor on a MOD platform, that
 *   surviving proposal appeared as ~1500-unit horizontal lurches on
 *   alternating ticks.  On real ground the resolved commit makes measured
 *   motion exactly previous + velocity per tick; MOD platforms must re-commit
 *   that themselves (mod/caves/training_grain_gate.c roof pin).
 *
 * GROUNDED FLAG (player[+0x82] = 0x800A6582; grounded=0x0101, airborne=0):
 *   the player caller passes a2 = player+0x82 at 0x800495B8. This integrator saves
 *   that pointer, loads s1=1, and at 0x80036CB8 plus the 0x80036CC0 delay slot writes
 *   byte values {1,1}, producing little-endian 0x0101. The raw set condition is
 *   a3 != 2 && (s0 == 1 || a3 == 1); naming those raw results "ground contact" is
 *   an interpretation, separately supported by a pristine jump+land observation.
 *   A general static census resolves 16 other resident writers, all zero clears,
 *   while retaining 12,956 unresolved-base accesses (450 same-width sites in related
 *   functions) and 149 unresolved indirect calls. Thus this exact player-call
 *   producer is proven, but global exclusivity is not.
 *   CORRECTION HISTORY (2026-08-04 audit): the former approximate PCs
 *   0x80036B90/0x80036CBC/0x80036CD0 are a load/jump/branch, not stores; the write
 *   is in this integrator, not a collision callee. The former ONLY-producer claim
 *   exceeded the unresolved census and is retracted. Tier-3 republishes [+0x82]
 *   from its own floor; see src_re/player_update_80048138.c for the consumer.
 * ===========================================================================*/

#include <stdint.h>

#define PLAYER ((volatile int32_t *)0x800A6500)   /* [0]=X [1]=Y [2]=Z [3]=w */
#define X_REF  (*(volatile int32_t *)0x800A6510)

/* Opaque collision-pass result: 2 = "done/settled", >0 = "iterate again". */
extern int  FUNC_80035F24(void *out_pos, void *a1, void *a2, void *a3);   /* 0x80035f24 */
extern int  FUNC_800345CC(void *out_pos, void *a1, void *a2, void *a3);   /* swept planes */
extern int  FUNC_80035280(void *out_pos, void *a1, void *a2, void *a3);   /* 0x80035280 */
extern void FUNC_80036DD4(void);                                          /* X-ref branch */

/* The Y-resolution tail of FUNC_8003633C, in C. The integrator runs a collision loop that
 * refines a candidate position (resolved[]) until a pass reports "settled" (code 2), writes
 * it into the player, then applies the +3200 adjust. Locals below mirror the stack slots. */
void movement_integrator_tail(void *ctx_a1, void *ctx_a2, void *ctx_a3, void *flags,
                              int path_result /* models s0 in the omitted dispatch */)
{
    int32_t resolved[4];          /* sp+0x18..0x24 : the collision-resolved X,Y,Z,w */
    int iters = 0;                /* s2 : collision-pass counter */
    int code;                     /* a3 : last pass result */
    unsigned char *flag = flags;  /* sp+0x28 : 2-byte contact-flag struct */

    /* --- collision loop (0x80036c1c .. 0x80036cd4) --------------------------------------
     * Each iteration runs the collision passes against the candidate move; the chosen pass
     * writes the refined position into resolved[]. Loop while the result is still "open". */
    do {
        code = FUNC_80035F24(resolved, ctx_a1, ctx_a2, ctx_a3);   /* 0x80035f24 */
        code = FUNC_800345CC(resolved, ctx_a1, ctx_a2, ctx_a3);   /* swept planes 0x800345cc */
        /* (a third pass FUNC_80035280 is selected on other branches: 0x80035280) */

        /* Exact 0x80036C98..0x80036CCC control flow. Earlier pseudocode wrote
         * {1,0} for every code != 2; that was wrong and is retained here as
         * correction history. The set arm writes {1,1}; the other arm clears
         * only byte 1. */
        if (code != 2 && (path_result == 1 || code == 1)) {
            flag[0] = (unsigned char)1;
            flag[1] = (unsigned char)1;
        } else {
            flag[1] = 0;
        }
        iters++;
    } while (code > 0);

    /* --- commit the resolved position into the player (0x80036cd8 .. 0x80036cf4) -------- */
    PLAYER[0] = resolved[0];             /* X */
    PLAYER[1] = resolved[1];             /* Y  (writer 2: 0x80036cec) */
    PLAYER[2] = resolved[2];             /* Z */
    PLAYER[3] = resolved[3];             /* w */

    /* --- final +3200 Y adjust + X-reference check (0x80036d48 .. 0x80036d64) ------------
     * Re-reads the just-committed Y, adds the 3200 offset back, stores it (THIS is writer 3,
     * the last word on Flik's Y -- the Tier-3 hook replaces this `sw`). Then compares Flik.X
     * to the reference at 0x800A6510 and branches. */
    int32_t y = PLAYER[1];
    int32_t x = PLAYER[0];
    PLAYER[1] = y + 3200;                /* writer 3: 0x80036d54  <-- Tier-3 hook site */
    if (x != X_REF)
        FUNC_80036DD4();                 /* 0x80036d64 bne -> 0x80036dd4 */
}
