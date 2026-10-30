/* ============================================================================
 * pickup_handlers_80054288_80054554.c  — pickup/action handlers [PHASE 5 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESSES : source-side action labels inside fcn.80053814:
 *                      0x80053d04/0x80053e64/0x80053fc0/0x8005411c (FLIK bits,
 *                      summarized), 0x80054288..0x80054554 (berry/token/telescope),
 *                      plus fcn.80054eac (grain handler, 0x80054eac..0x80055188).
 * CONFIDENCE         : CONFIRMED marker/counter writes, token counter encoding, seed
 *                      power-up calls, telescope activation writes, grain count/reward branch.
 *                      Some side-effect globals remain UNKNOWN and are labelled.
 * SOURCE NOTES       : docs/LEVEL01_TYPE3F_MAP.md, docs/COORDINATE_MODDING.md,
 *                      docs/EXECUTABLE_AND_OVERLAYS.md, docs/EXPERIMENT_LOG.md,
 *                      Phase 2 source3f_dispatch_80053814.c, Phase 4 walker,
 *                      r2 disasm (MIPS LE, gp=0x80081d98).
 * KNOWN CALLERS      : fcn.80053814 source-side jump table 0x8001b42c; fcn.800586b0
 *                      record-side jump table 0x8001b570 mirrors several marker/grain cases.
 * KNOWN CALLEES      : fcn.80050994 (sound/event by id), fcn.8003e760 (token sprite
 *                      re-skin ONLY — plant selection happens at plant time, see
 *                      plant_spawn_8005bdbc.c / HRE-004),
 *                      fcn.8005044c (post-pickup bookkeeping), fcn.80045678,
 *                      fcn.80044d28, fcn.800571e0, fcn.8005721c.
 * KNOWN GLOBALS      : G_BERRY_MARKER, G_GRAIN_COUNT, G_SEED_CTR_ORANGE/BLUE/GREEN,
 *                      0x800a659b/9c (extra seed counters for kinds 0x2c/0x2d),
 *                      seed obj-id table 0x80078e90={0x17,0x19,0x18,0x2f},
 *                      0x800b0196 seed-nibble mask, 0x800824dc telescope-view active flag.
 * UNRESOLVED         : downstream gameplay EFFECT of each berry marker value; exact
 *                      meaning of seed-nibble mask 0x800b0196, grain pre-effect
 *                      fcn.80044d28, and several global timers/counters.
 *
 * IMPORTANT CONTEXT:
 *   The labels at 0x80054288..0x80054554 are not standalone ABI functions. They are
 *   jump-table cases inside fcn.80053814 and use that function's live registers:
 *     s4 = Type3FEntry* entry, s2 = entry+4, s3 = collected-bitmask/global byte,
 *     s1 = post-loop result code, fp = count/index for kind 0x30 cases.
 *   The C below models each case as a helper with explicit parameters.
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LBU(p)  (*(uint8_t  *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))
#define SH(p,v) (*(uint16_t *)(p) = (uint16_t)(v))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))

#define G_SCRIPT_CURSOR         0x800822f4u
#define G_SCENE_ID              0x80082504u
#define G_MASTER_GAME_STATE     0x800823a0u /* UNKNOWN name outside notes; compared to 2 */
#define G_GRAIN_PRE_EFFECT_GATE 0x8008244cu /* UNKNOWN gp+0x6b4 */
#define G_PROGRESS_BYTE         0x800a65a0u /* CONFIRMED FLIK/grain reward progress byte (<9) */
#define G_PLAYER_EXTRA_6548     0x800a6548u /* UNKNOWN companion player/global word */
#define G_UNK_FLAGS_6590        0x800a6590u /* UNKNOWN flags halfword; bit2 gates grain pre-effect */
#define G_UNK_COUNTER_6594      0x800a6594u /* UNKNOWN halfword touched by token/grain/walker */
#define G_EXTRA_SEED_CTR_2C     0x800a659bu /* CONFIRMED extra token counter for action 0x2c */
#define G_EXTRA_SEED_CTR_2D     0x800a659cu /* CONFIRMED extra token counter for action 0x2d */
#define G_TELESCOPE_ACTIVE      0x800824dcu
#define G_TELESCOPE_INDEX       0x800823ccu
#define G_PLAYER_VEL_X          0x800a652cu
#define G_PLAYER_VEL_Y          0x800a6530u
#define G_PLAYER_VEL_Z          0x800a6534u
#define G_PLAYER_GROUNDED       0x800a6582u
#define G_SEED_NIBBLE_MASK      0x800b0196u
#define G_BOB_188              0x800b0188u
#define G_BOB_18C              0x800b018cu
#define G_BOB_190              0x800b0190u
#define G_BOB_194              0x800b0194u
#define G_REWARD_SNAPSHOT      0x80090b80u
#define G_FLK_SNAPSHOT         0x800b3988u
#define G_TABLE_80078378       0x80078378u /* indexed by (0x30/0x31)<<4; meaning UNKNOWN */
#define G_KIND_VALUE_TABLE     0x80078d84u /* kind -> value copied during post-loop finalize */
#define G_SEED_OBJ_TABLE       0x80078e90u /* bytes: 0x17,0x19,0x18,0x2f */
#define ACTOR_BERRY_COLUMN_TABLE 0x80089938u

/* 2026-07-06 live GPU extraction of the in-world F/L/I/K pickup face tiles.
 * These are the collectible-object face textures, not the SELECT-panel HUD
 * 24x23 spin strips documented in hud_800526f4.c.
 *
 * Captured from SPINNING_F/L/I/K.sav against build/ABL_ALLMODS.cue while
 * holding L1+DOWN. gpu.pickObject/gpu.traceRegion resolved the visible face as
 * a 4bpp textured quad on tpage (640,0), CLUT (880,217). Later Training work
 * showed these UV cells also receive repeated narrow 6x24 VRAM uploads, so the
 * extracted 24x24 tile is a phase/source sample rather than the whole spin model.
 * Extracted reference PNGs: mod/glyphs/pickup_letters/.
 *
 * Training's `TRAINING` word mod keeps the native kind handlers but remaps scene
 * 0x11 type-0x3f entries 50-53 and 62-65 to generated pickup art. Source PNGs
 * come from tools/generate_training_pickup_letters.py; tools/training_word_pickups.py
 * bakes 8-frame rows into LEVEL07/LEVEL.RAW chunk 11 and LEVEL07/LEVEL1.RAW
 * chunk 12, then a resident helper selects the current row/frame by VSync phase.
 */
#define FLIK_PICKUP_TPAGE_X    640u
#define FLIK_PICKUP_TPAGE_Y    0u
#define FLIK_PICKUP_CLUT_X     880u
#define FLIK_PICKUP_CLUT_Y     217u
#define FLIK_PICKUP_GLYPH_W    24u
#define FLIK_PICKUP_GLYPH_H    24u
#define FLIK_PICKUP_F_U        192u
#define FLIK_PICKUP_F_V        64u
#define FLIK_PICKUP_L_U        216u
#define FLIK_PICKUP_L_V        64u
#define FLIK_PICKUP_I_U        192u
#define FLIK_PICKUP_I_V        88u
#define FLIK_PICKUP_K_U        216u
#define FLIK_PICKUP_K_V        88u

extern void fcn_80050994(int sound_or_event_id);
extern void fcn_8003e760(int object_id, int level);
extern void fcn_8005044c(int result, void *context);
extern int  fcn_80045678(void *player_base);
extern void fcn_80044d28(void *player_base, int a1, int a2, int a3, int stack0, int stack1);
extern void fcn_800571e0(int a0, int a1);
extern void fcn_8005721c(int a0, int a1);

static void normalize_bob_halfword(uint32_t addr)
{
    /* Repeated idiom: if value >= 0xc00, mirror from 0x1000; else clamp down
     * to 0x400 when value > 0x400; if zero, force 0x40. */
    int16_t v = LH(addr);
    if (v >= 0x0c00) {
        SH(addr, 0x1000 - v);
    } else if (v >= 0x0401) {
        SH(addr, 0x0400);
    }
    if (LH(addr) == 0) {
        SH(addr, 0x0040);
    }
}

static void marker_action(uint8_t marker, int sound, int *s1_out)
{
    /* Original equip cases change only the selector. The active-projectile byte
     * at player+0x96 is owned by throw/retirement and is deliberately untouched. */
    SB(G_BERRY_MARKER, marker);
    fcn_80050994(sound);
    *s1_out = -5;                         /* shared source-side berry result */
}

/* 0x80054288/98/ac/c0/d4 — source-side berry/power-up marker cases.
 * Record-side walker mirrors at 0x80058940..0x80058988 do the same marker/sound
 * writes, then set record state. */
void source_marker_action_case(uint8_t kind, int *s1_out)
{
    switch (kind) {
    case 0x20: marker_action(0, -3,   s1_out); break; /* 0x80054288 */
    case 0x21: marker_action(2, 0x36, s1_out); break; /* Green/Homing */
    case 0x22: marker_action(3, 0x38, s1_out); break; /* Gold */
    case 0x23: marker_action(1, 0x35, s1_out); break; /* Blue/Super */
    case 0x24: marker_action(4, 0x37, s1_out); break; /* Purple/Mega */
    default:   *s1_out = -2; break;                   /* table default */
    }
}

static uint8_t bump_seed_counter(uint32_t counter_addr)
{
    /* CONFIRMED encoding: new logical count n=(old+1)&7 is stored as n*17.
     * Later `(stored & 7) - 1` recovers power-up level n-1 because 17 == 1 mod 8. */
    uint8_t n = (uint8_t)((LBU(counter_addr) + 1) & 7);
    uint8_t stored = (uint8_t)((n << 4) + n);
    SB(counter_addr, stored);
    return stored;
}

static void set_seed_nibble_once(int seed_index)
{
    /* CONFIRMED only for token kinds 0x2a..0x2d when logical counter wraps/starts at 1.
     * Finds the first zero low nibble in 0x800b0196 and ORs in seed_index shifted by
     * nibble position. Gameplay meaning UNKNOWN. */
    int16_t mask = LH(G_SEED_NIBBLE_MASK);
    int nib = 0;
    for (;;) {
        if ((mask & 0x0f) == 0) {
            SH(G_SEED_NIBBLE_MASK, LHU(G_SEED_NIBBLE_MASK) | (seed_index << (nib * 4)));
            return;
        }
        nib++;
        if (nib >= 4) return;
        mask >>= 4;
    }
}

static void seed_token_common(uint32_t counter_addr, int object_id, int seed_index, int *s1_out)
{
    uint8_t stored = bump_seed_counter(counter_addr);
    int level = (stored & 7) - 1;
    fcn_8003e760(object_id, level);

    if ((LBU(counter_addr) & 7) == 1 && seed_index > 0) {
        set_seed_nibble_once(seed_index);
    }

    fcn_80050994(-3);
    *s1_out = -3;
}

/* 0x800542f4..0x800544d0 — seed token handlers.
 * 0x29 hardcodes object 0x16 and has no nibble-mask path.
 * 0x2a..0x2d use table 0x80078e90 = {0x17,0x19,0x18,0x2f}. */
void source_seed_token_action(uint8_t kind, int *s1_out)
{
    switch (kind) {
    case 0x29: {
        uint8_t stored = bump_seed_counter(G_SEED_CTR_ORANGE);
        fcn_80050994(-3);
        fcn_8003e760(0x16, (stored & 7) - 1);
        *s1_out = -3;
        break;
    }
    case 0x2a:
        seed_token_common(G_SEED_CTR_BLUE,  LBU(G_SEED_OBJ_TABLE + 0), 1, s1_out);
        break;
    case 0x2b:
        seed_token_common(G_SEED_CTR_GREEN, LBU(G_SEED_OBJ_TABLE + 1), 2, s1_out);
        break;
    case 0x2c:
        seed_token_common(G_EXTRA_SEED_CTR_2C, LBU(G_SEED_OBJ_TABLE + 2), 3, s1_out);
        break;
    case 0x2d:
        seed_token_common(G_EXTRA_SEED_CTR_2D, LBU(G_SEED_OBJ_TABLE + 3), 4, s1_out);
        break;
    default:
        *s1_out = -2;
        break;
    }
}

/* 0x80054554 / 0x800545a0 — telescope/hint-view cases for kind 0x30/0x31.
 * `entry_plus_4` is s2 in fcn.80053814 (points at Type3FEntry.y). */
void source_telescope_action(uint8_t *entry_plus_4, int fp_index, int *s1_out)
{
    if (LW(G_TELESCOPE_ACTIVE) == 0) {
        SW(G_TELESCOPE_INDEX, fp_index);
        SW(G_TELESCOPE_ACTIVE, -1);
        SW(G_PLAYER_VEL_X, 0);
        SW(G_PLAYER_VEL_Y, 0);
        SW(G_PLAYER_VEL_Z, 0);
        SH(G_PLAYER_GROUNDED, 0);
        *s1_out = -9;
        return;
    }

    /* Alternate path at 0x800545a0: if entry.y equals (lh entry+0x0e - 0x70),
     * decrement entry.y, play event -3, and return -10. Otherwise fall through. */
    if (LW(entry_plus_4) == LH(entry_plus_4 + 0x0a) - 0x70) {
        SW(entry_plus_4, LW(entry_plus_4) - 1);
        fcn_80050994(-3);
        *s1_out = -10;
    }
}

/* FLIK letter cases 0x80053d04/0x80053e64/0x80053fc0/0x8005411c.
 * Phase 5 confirms the shared structure and the F anomaly; exact bob/global
 * semantics remain TODO.
 *
 * Retail has four bits and completes on mask 0x0f. The 2026-07-05 FLIK5 test
 * proves this is code-gated, not an engine object-count limit: an appended
 * duplicate F entry can be special-cased in the F handler to set bit 0x10,
 * and changing the completion compare to 0x1f makes the token/progress advance
 * only after five letters. Keep the appended letter as native kind 0x10 if it
 * should render as F; changing shared descriptor bytes for a fake kind polluted
 * the top-left Flik-head HUD icon.
 *
 * 2026-07-06 Training word mod: `tools/training_word_pickups.py` uses the FLIK5
 * lesson without making a fake kind. In the Training scene (scene 0x11; user-facing
 * LEVEL00, retail files LEVEL07), original entries 50-53 and appended entries
 * 62-65 spell TRAINING. The collection cave at 0x800811c0 maps entries 50-53 to
 * bits 0..3 and entries 62-65 to bits 4..7; a scene-gated compare cave returns
 * completion mask 0xff for Training and 0x0f everywhere else. Final caves are
 * collection 0x800811c0, animated visual helper 0x800813ac, visual gate
 * 0x80081430, compare 0x80081488, helper data 0x80081580. The earlier
 * 0x8007fbc8 gate is overwritten during Training scene load. A later
 * 0x8007f130 helper also failed because its table clobbered live
 * retail state at 0x8007f16c, read by code around 0x800616c0, causing an invalid
 * word read crash. A static custom-UV version was also wrong: native F/L/I/K
 * slots receive repeated 6x24 VRAM uploads for their spin, while the new UVs
 * sampled static flower/background texels. The fixed helper selects an 8-frame
 * baked spin strip by VSync phase. Non-Training scenes still receive each
 * handler's native bit through the hook delay slot. Address 0x800811bc must
 * remain a nop because it is the delay slot of blackberry CAVE_THROW's return
 * jump at 0x800811b8; placing collection code there crashed berry throws.
 *
 * FLIK completion emblem image/glyph note (2026-07-05; reconfirmed 2026-07-06
 * from collecting_flik.sav, hold UP ~60f then pause): live gpu.pickObject on the
 * collected emblem resolves the visible top GP0(2c) quad to tpage 0x066b
 * (VRAM x=704,y=0), CLUT 0x35f1 (x=784,y=215), UV 64..127 / 0..63. Static
 * decode makes that source tile look gold; the runtime CLUT recolors it silver.
 * The matching on-disc CLUT is palette slot 1 in the same source chunks; patch
 * that palette with the texel data or custom art renders through the native
 * silver ramp. Palette entry 0 must remain the native disc green-key
 * (0,255,0); RGB black at entry 0 renders as a visible square. Patch both
 * source copies: LEVEL01/LEVEL.RAW chunk 13 rect (64,0,64,64) and
 * LEVEL01/LEVEL1.RAW chunk 12 same rect. Training is separate:
 * LEVEL00/LEVEL.RAW chunk 3, rect (64,96,64,80); do not route Training through
 * LEVEL01. */
void source_flik_letter_action(uint8_t kind, uint8_t *collected_mask, int *s1_out)
{
    uint8_t bit = (uint8_t)(1u << (kind - 0x10)); /* 0x10 F=1, 0x11 L=2, 0x12 I=4, 0x13 K=8 */
    *collected_mask |= bit;
    normalize_bob_halfword(G_BOB_194);

    if (*collected_mask != 0x0f) { /* FLIK5 mod changes this immediate to 0x1f. */
        *s1_out = -2;
        return;
    }

    /* When all four FLIK bits are set, all four cases run this shared completion
     * path; F's case was where the extra behavior was first observed. */
    SW(G_FLK_SNAPSHOT + 0x00, LW(G_PLAYER_X));
    SW(G_FLK_SNAPSHOT + 0x04, LW(G_PLAYER_Y));
    SW(G_FLK_SNAPSHOT + 0x08, LW(G_PLAYER_Z));
    SW(G_FLK_SNAPSHOT + 0x0c, LW(G_PLAYER_EXTRA_6548));
    SW(G_FLK_SNAPSHOT + 0x10, 0x400);
    fcn_8005044c(-0x0b, (void *)G_PLAYER_X);

    if (LBU(G_PROGRESS_BYTE) < 9) {
        SB(G_PROGRESS_BYTE, LBU(G_PROGRESS_BYTE) + 1);
        fcn_8005044c(-8, (void *)G_PLAYER_X);
        normalize_bob_halfword(G_BOB_188);
    }
    *s1_out = -2;
}

static void maybe_grain_pre_effect(uint8_t first_script_byte, uint8_t *cursor_before)
{
    /* Optional pre-effect before grain_count++; exact gameplay effect UNKNOWN. */
    if ((first_script_byte & 0x0f) != 0) return;
    if (LW(G_SCENE_ID) == 0x11) return;

    uint8_t *cur = cursor_before;
    SW(G_SCRIPT_CURSOR, (int32_t)(uintptr_t)(cur + 2));
    uint8_t second = LBU(cur + 1);
    int variant = second & 1;

    if (fcn_80045678((void *)G_PLAYER_X) != 0) return;
    if (LH(G_MASTER_GAME_STATE) == 2) return;
    if (LHU(G_UNK_FLAGS_6590) & 4) return;
    if (LW(G_GRAIN_PRE_EFFECT_GATE) != 0) return;

    fcn_80044d28((void *)G_PLAYER_X,
                 variant | 0x20,
                 (variant << 7) | 0x1200,
                 LH(G_TABLE_80078378 + ((variant + 0x30) << 4)),
                 0,
                 0);
}

/* fcn.80054eac — grain pickup handler.
 * Called by source-side kind 0x14 and by walker action_id 0x14. */
void grain_pickup_handler_80054eac(void)
{
    uint8_t *cur = (uint8_t *)(uintptr_t)LW(G_SCRIPT_CURSOR);
    SW(G_SCRIPT_CURSOR, (int32_t)(uintptr_t)(cur + 1));
    uint8_t first = LBU(cur);

    maybe_grain_pre_effect(first, cur);

    SB(G_GRAIN_COUNT, LBU(G_GRAIN_COUNT) + 1);
    normalize_bob_halfword(G_BOB_18C);

    if (LBU(G_GRAIN_COUNT) != G_GRAIN_TARGET) {
        return;
    }

    /* All-grain reward path (only when count reaches 50 exactly). */
    SW(G_REWARD_SNAPSHOT + 0x00, LW(G_PLAYER_X));
    SW(G_REWARD_SNAPSHOT + 0x04, LW(G_PLAYER_Y));
    SW(G_REWARD_SNAPSHOT + 0x08, LW(G_PLAYER_Z));
    SW(G_REWARD_SNAPSHOT + 0x0c, LW(G_PLAYER_EXTRA_6548));
    SW(G_REWARD_SNAPSHOT + 0x10, 0x400);
    fcn_8005044c(-0x0b, (void *)G_PLAYER_X);

    /* Static comparison in the resident image is false (0x80090b80 != 0x800b3988),
     * but preserve the branch because it exists in the code. */
    if ((uint8_t *)G_REWARD_SNAPSHOT == (uint8_t *)G_FLK_SNAPSHOT) {
        if (LBU(G_PROGRESS_BYTE) < 9) {
            SB(G_PROGRESS_BYTE, LBU(G_PROGRESS_BYTE) + 1);
            fcn_8005044c(-8, (void *)G_PLAYER_X);
            normalize_bob_halfword(G_BOB_188);
        }
    }

    SH(G_UNK_COUNTER_6594, 4);
    normalize_bob_halfword(G_BOB_190);
}

/* Shared post-loop tail from fcn.80053814 (0x800545e8..0x80054808), included
 * here because these action cases feed s1 and marker changes into it.
 *
 * Resolved edge contract (live disassembly + function trace, 2026-07-11):
 * 0x800545cc assigns s1=-2, 0x800545d0 advances the source pointer, and this
 * tail calls fcn_8005044c for every nonzero s1. Thus -2 is not a silent/no-op
 * value. A MOD path that denies an award without feedback must enter at
 * 0x800545d0 with s1=0; entering at 0x800545cc audibly dispatches -2. */
void source3f_action_post_loop_tail(int s1, uint8_t old_marker, void *coords_or_player)
{
    if (s1 != 0) {
        fcn_8005044c(s1, coords_or_player);
        if (fcn_80045678((void *)G_PLAYER_X) == 0) {
            fcn_8005721c(8, 0x1e);
        }
        fcn_800571e0(4, 0x1e);
    }

    /* First-use berry-column inheritance: new-game state initializes only
     * column zero and leaves columns 1..4 at 0xff. On the first switch to an
     * uninitialized column, inherit every actor row from the previously
     * equipped column. This is persistent adaptive encounter state, not a
     * marker-rotation or frontend table. */
    if (old_marker != LBU(G_BERRY_MARKER)
        && LBU(ACTOR_BERRY_COLUMN_TABLE + LBU(G_BERRY_MARKER)) == 0xff) {
        uint8_t *table = (uint8_t *)ACTOR_BERRY_COLUMN_TABLE;
        for (int i = 0, off = 0; i < 0x40; i++, off += 5) {
            table[off + LBU(G_BERRY_MARKER)] = table[off + old_marker];
        }
    }

    /* The remaining 0x800546a0..0x80054808 path copies nearest-entry coords and
     * kind-derived values into 0x8009fa28.. when gates pass. It is peripheral to
     * pickup identity and remains UNKNOWN/TODO. */
}

/* ----------------------------------------------------------------------------
 * PHASE 5 FINDINGS:
 *  - CONFIRMED berry marker cases: kind 0x20 clears marker, 0x21/22/23/24 set
 *    marker 2/3/1/4 and play sounds -3/0x36/0x38/0x35/0x37.
 *  - CONFIRMED source-side token cases 0x29..0x2d. Counters store `(n&7)*17`;
 *    power-up level is `(stored & 7)-1`. Object ids: 0x29 hardcodes 0x16;
 *    0x2a..0x2d read table 0x80078e90 = {0x17,0x19,0x18,0x2f}.
 *  - CONFIRMED extra token counters 0x800a659b/0x800a659c for kinds 0x2c/0x2d.
 *  - CONFIRMED telescope first-activation path: 0x800824dc gate, saves the kind-0x30
 *    ordinal to 0x800823cc, clears player velocity/grounded state, and returns s1=-9.
 *    These writes belong to the camera/hint-view interaction, not respawn state.
 *  - CONFIRMED grain handler increments G_GRAIN_COUNT and only enters reward path
 *    when count == 0x32. Reward snapshots player fields and calls fcn.8005044c(-0xb).
 *  - NO ContactRecord field promotions in re_types.h: this phase mostly decodes globals
 *    and source-entry action behavior, not runtime record layout.
 *  - Phase 6 (HUD) is ready; it can now consume the confirmed grain/seed/marker globals.
 * ---------------------------------------------------------------------------- */
