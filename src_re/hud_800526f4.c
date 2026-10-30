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
#define G_HUD_OBJECT_STATE      0x800b5774u /* scene 7 five-icon state bitfield */
#define G_HUD_OBJECT_ICON       0x800b577cu /* scene 7 numeric icon value */
#define G_HUD_SCENE2_PROGRESS   0x8009fe72u
#define G_HUD_SCENE11_PROGRESS  0x800a0316u
#define G_HUD_SCENE12_DIGIT     0x800b4a48u
#define G_HUD_SCENE13_PROGRESS  0x800b45f4u
#define G_HUD_SCENE14_REMAINING 0x800b4cc8u
#define G_HUD_SCENE15_PROGRESS  0x800b4ba8u
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
extern void fcn_800260f8(int x_or_value, int y, int tile, int variant);
extern void fcn_80026588(int x, int y, int tile, int variant, int w, int h, int color);
extern void fcn_80026a68(int x, int y, int tile, int variant, int w, int h, int color, int alpha);
extern void fcn_80026df4(int tile, int zero, int count);
extern void fcn_80026d78(void);
extern void fcn_8005044c(int result, void *context);

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

static void advance_pulse(uint32_t addr, int frame_step)
{
    int16_t v = (int16_t)(LHU(addr) + frame_step);
    SH(addr, (v < 0x1000) ? v : 0);
}

static void draw_progress_panel(int frame_step)
{
    int16_t pulse = LH(G_HUD_PULSE_PROGRESS);
    if (pulse <= 0) return;

    int y = hud_wave_y_from_pulse(pulse, -0x30);
    int x_off = 0;
    if (LW(G_GAME_MODE) == 2) {
        uint16_t flags = LHU(G_HUD_FLAGS_2488);
        if (flags & 0x80) x_off = -2;
        if (flags & 0x20) x_off = 2;
    }

    fcn_80025f54(0x20 + x_off, y + 0x0a, 0x74, 0);
    fcn_80025f54(0x35 + x_off, y + 0x0a, 0x74, 0);
    fcn_800260f8(0x10, y, 0x1c, 0);
    fcn_80025f54(0x4c, y + 0x0c, 0x1e, LH(G_HUD_PROGRESS_LATCH));

    if (LH(G_HUD_PULSE_PROGRESS) == 0x400) {
        SH(G_HUD_PROGRESS_LATCH, LBU(0x800a65a0u));
    }
    advance_pulse(G_HUD_PULSE_PROGRESS, frame_step);
}

static void draw_seed_total_panel(int frame_step)
{
    if (LH(G_UNK_COUNTER_6594) >= 5) SH(G_UNK_COUNTER_6594, 4);

    int16_t pulse = LH(G_HUD_PULSE_SEED);
    int y = hud_wave_y_from_pulse(pulse, -0x30);
    if (pulse > 0) {
        fcn_800260f8(0x110, y, 0x1d, 0);
        if (pulse == 0x400 && LH(G_HUD_SEED_LATCH) != LH(G_UNK_COUNTER_6594)) {
            int count = 4 - LH(G_UNK_COUNTER_6594);
            if (count >= 5) count = 4;
            fcn_80026df4(0x1d, 0, count);
            if (LH(G_UNK_COUNTER_6594) < LH(G_HUD_SEED_LATCH)) {
                fcn_8005044c(0x1c, 0);
            }
            SH(G_HUD_SEED_LATCH, LHU(G_UNK_COUNTER_6594));
        }
        advance_pulse(G_HUD_PULSE_SEED, frame_step);
    }

    if (LW(G_GAME_MODE) == 3) {
        y += 0x34;
        if (y < 0x10) y = 0x10;
        if (y >= 0x45) y = 0x44;
        fcn_800260f8(0x110, y, 0x73, 0);
    }
}

static uint16_t pack_decimal_0_99(uint8_t value)
{
    uint8_t tens = value / 10;
    uint8_t ones = value - tens * 10;
    return (uint16_t)(tens | (ones << 8));
}

static void draw_grain_panel(int frame_step)
{
    int16_t pulse = LH(G_HUD_PULSE_GRAIN);
    if (pulse <= 0) return;

    int32_t p = pulse;
    if (p > 0x0c00) p -= 0x0800;
    else if (p > 0x0400) {
        if (LBU(G_GRAIN_COUNT) >= G_GRAIN_TARGET) {
            SH(G_HUD_PULSE_GRAIN, 0x400);
        }
        p = 0x400;
    }

    int y = 0x110 - (((int32_t)((int16_t)LHU(G_SIN_TABLE + p * 2) << 16)) >> 24);
    fcn_800260f8(0x10, y, 0x14, 0);
    fcn_80025f54(0x33, y, 0x1e, LBU(G_HUD_GRAIN_DIGITS));
    fcn_80025f54(0x3f, y, 0x1e, (int8_t)LHU(G_HUD_GRAIN_DIGITS));

    if (LH(G_HUD_PULSE_GRAIN) == 0x400) {
        SH(G_HUD_GRAIN_DIGITS, pack_decimal_0_99(LBU(G_GRAIN_COUNT)));
    }
    advance_pulse(G_HUD_PULSE_GRAIN, frame_step);
}

static void draw_misc_counter_panel(int frame_step)
{
    /* 0x800b0198 is the misc/gold-defeat pulse panel. The displayed count is
     * total enemies minus enemies remaining; the gold-drop token pickup advances
     * it by decrementing 0x800a658e. */
    int16_t pulse = LH(G_HUD_PULSE_MISC);
    if (pulse <= 0) return;

    int y = 0x110 - (((int32_t)((int16_t)LHU(G_SIN_TABLE + pulse * 2) << 16)) >> 24);
    fcn_800260f8(0x7d, y - 0x10, 0x7b, LH(0x800a7e2au));
    fcn_80025f54(0xfa,  y, 0x1e, LBU(G_HUD_MISC_DIGITS));
    fcn_80025f54(0x106, y, 0x1e, (int8_t)LHU(G_HUD_MISC_DIGITS));
    fcn_80025f54(0x112, y, 0x1e, 0x0a);
    fcn_80025f54(0x11e, y, 0x1e, LBU(G_HUD_MISC_DIGITS2));
    fcn_80025f54(0x12a, y, 0x1e, (int8_t)LHU(G_HUD_MISC_DIGITS2));

    if (LH(G_HUD_PULSE_MISC) == 0x400) {
        int value = LW(0x80082258u) - LH(0x800a658eu);
        SH(G_HUD_MISC_DIGITS, pack_decimal_0_99((uint8_t)value));
    }
    advance_pulse(G_HUD_PULSE_MISC, frame_step);
}

/* The SELECT-hold status panel's 4-letter word ("FLIK" in retail).
 *
 * This loop draws sprite tiles 0x10..0x13 (the F/L/I/K glyph SLOTS) at
 * x = 0x70 + i*0x18. The C only references tile IDs -- the letter PIXELS are
 * 24x23 4-bit golden sprites (spin-animated, ~16 frames) in the level texture
 * atlas LEVEL01/LEVEL.RAW + LEVEL1.RAW. To change the word (e.g. FLIK->ATTA),
 * edit the glyph art, NOT this code:
 *     - set the word in           mod/glyphs/flik_word.h   (FLIK_WORD)
 *     - drop per-letter art in     mod/glyphs/letters/<LETTER>.png
 *     - run                        tools/patch_flik_word.py   (+ rebuild disc)
 * Slot i renders FLIK_WORD[i]. See mod/glyphs/flik_word.h for the slot table.
 *
 * FLIK5 mod proof (2026-07-05): the SELECT panel can be extended by adding one
 * more draw of tile 0x10 at x=0xd0, gated by bit 0x10 in G_FLIK_PROGRESS_BITS.
 * Keep this as an extra draw call; do not repoint/overwrite shared pickup or UI
 * descriptor bytes to make a fake F kind, because that replaced the top-left
 * Flik-head HUD icon in the failed attempt.
 *
 * Training TRAINING mod note (2026-07-07): the 8-letter Training-only panel
 * cannot be centered cleanly from the old tail-only hook because slots 0..3
 * have already drawn at the retail 4-letter positions by then. The active
 * stager hooks the first bitmask load at 0x80052D98, scene-gates on Training,
 * and draws all 8 slots from a RAW-resident blob at x=0x48+i*0x18. Outside
 * Training it replays the displaced load and returns here, preserving this
 * native 4-letter placement. */
static void draw_flik_bit_panel(int frame_step)
{
    int16_t pulse = LH(G_HUD_PULSE_FLIK);
    if (pulse <= 0) return;

    int32_t p = pulse;
    if (p > 0x0c00) p -= 0x0800;
    else if (p > 0x0400) {
        if (LBU(G_FLIK_PROGRESS_BITS) == 0x0f) { /* FLIK5 mod changes this immediate to 0x1f. */
            SH(G_HUD_PULSE_FLIK, 0x400);
        }
        p = 0x400;
    }

    int y = (((int32_t)((int16_t)LHU(G_SIN_TABLE + p * 2) << 16)) >> 24) - 0x30;
    uint8_t bits = LBU(G_FLIK_PROGRESS_BITS);
    for (int i = 0; i < 4; i++) {
        int x = 0x70 + i * 0x18;
        int tile = 0x10 + i;
        if (bits & (1u << i)) {
            fcn_800260f8(x, y, tile, 0);
        } else {
            fcn_80026588(x, y, tile, 0, 0x40, 0x20, 0x20);
        }
    }
    advance_pulse(G_HUD_PULSE_FLIK, frame_step);
}

static void draw_seed_meters(void)
{
    /* CONFIRMED loop at 0x80052fa4. It uses only the three displayed seed
     * counters 0x6598..0x659a, not the extra 0x659b/9c Phase-5 counters. */
    int x = 0x11c;
    int y = 0xc1;
    int nibble_mask = LH(G_SEED_NIBBLE_MASK);

    for (int i = 0; i < 3 && (nibble_mask & 0x0f) != 0; i++) {
        uint8_t counter = LBU(G_SEED_CTR_ORANGE + i);
        if (counter != 0) {
            int phase = counter >> 4;
            int table_index = ((i * 4) + phase) * 2;
            int tile_a = LBU(G_SEED_ICON_TABLE_A + table_index);
            int tile_b = LBU(G_SEED_ICON_TABLE_B + table_index);

            int anim;
            if (tile_a == 0) {
                anim = LH(0x800a7e2cu) + i;
                if (anim >= 6) anim -= 6;
            } else {
                anim = LH(0x800a7e2eu) + i * 2;
                if (anim >= 10) anim -= 10;
                if (anim >= 6) anim = 10 - anim;
            }

            fcn_800260f8(x, y - 0x0d, tile_b, anim);
            fcn_80026588(x + 2, y + 0x10, 0x0a, 0,
                         LBU(G_SEED_BOX_TABLE + i*3 + 0),
                         LBU(G_SEED_BOX_TABLE + i*3 + 1),
                         LBU(G_SEED_BOX_TABLE + i*3 + 2));
        }

        nibble_mask >>= 4;
        x -= 0x17;
        y -= 0x17;
    }
}

static void draw_flik_record_icons(void)
{
    if (LW(G_SCENE_ID) != 5) return;

    int y = hud_wave_y_from_pulse(LH(G_HUD_PULSE_FLIK), -0x15);
    if (y < 0x10) y = 0x10;

    if (LBU(LW(G_FLIK_PTR_F) + 0x1b)) fcn_800260f8(0x54, y, 0x32, 0);
    if (LBU(LW(G_FLIK_PTR_L) + 0x1b)) fcn_800260f8(0x7c, y, 0x34, 0);
    if (LBU(LW(G_FLIK_PTR_I) + 0x1b)) fcn_800260f8(0xa4, y, 0x35, 0);
    if (LBU(LW(G_FLIK_PTR_K) + 0x1b)) {
        fcn_800260f8(0xcc, y,     0x33, 0);
        fcn_800260f8(0xdc, y + 2, 0x36, 0);
    }
}

static void draw_scene7_panel(void)
{
    if (LW(G_SCENE_ID) != 7) return;

    int y = hud_wave_y_from_pulse(LH(G_HUD_PULSE_FLIK), -0x15);
    if (y < 0x10) y = 0x10;
    int y2 = y + 9;
    uint32_t flags = LW(G_HUD_OBJECT_STATE);

    fcn_80025f54(0xfb, y2,      ((flags & 1)  ? 0x3b : 0x32), 0);
    fcn_80025f54(0xfb, y,       ((flags & 2)  ? 0x3c : 0x33), 0);
    fcn_80025f54(0xfa, y + 0x1d,((flags & 4)  ? 0x3d : 0x34), 0);
    fcn_80025f54(0xe0, y2,      ((flags & 8)  ? 0x3e : 0x35), 0);
    fcn_80025f54(0x105, y2,     ((flags & 16) ? 0x3f : 0x36), 0);
    fcn_80025f54(0x10d, y + 0x15, 0x1e, LW(G_HUD_OBJECT_ICON));
}

static void draw_other_scene_panels(void)
{
    /* Address roles for the remaining scene-specific sources are pinned in
     * analysis/loose_ends.json. Their story/object labels remain unknown. */
    if (LW(G_SCENE_ID) == 0x0c) {
        int y = hud_wave_y_from_pulse(LH(G_HUD_PULSE_FLIK), -0x15);
        if (y < 0x10) y = 0x10;
        fcn_800260f8(0x8a, y - 0x10, 0x34, 0);
        fcn_80025f54(0x118, y + 0x0c, 0x1e, LW(G_HUD_SCENE12_DIGIT));
    }
    /* Scenes 2/11/13/14/15 select the raw progress globals above and render
     * a common five-segment tile-0x75 meter. */
}

/*
 * fcn.800526f4 — draw/update HUD panels. `frame_step` is added to active
 * 0x800b0188/18c/190/194/198 pulse halfwords.
 */
void hud_draw(int frame_step)
{
    if (LH(G_HUD_FLASH_TIMER) != 0 && LH(G_MASTER_GAME_STATE) == 0) {
        SH(G_HUD_PULSE_PROGRESS, 0x400);
        SH(G_HUD_PULSE_GRAIN, 0x400);
        SH(G_HUD_PULSE_SEED, 0x400);
    }

    if (LW(0x800822f8u) == 1) {
        SH(G_HUD_BLINK_COUNTER, (LHU(G_HUD_BLINK_COUNTER) + 1) & 0x1f);
        if (LH(G_HUD_BLINK_COUNTER) < 0x10) {
            fcn_80025f54(0xe0, 0x70, 0x25, 0);
        }
    }

    draw_progress_panel(frame_step);
    draw_seed_total_panel(frame_step);
    draw_grain_panel(frame_step);
    draw_misc_counter_panel(frame_step);
    draw_flik_bit_panel(frame_step);
    draw_seed_meters();
    draw_flik_record_icons();
    draw_scene7_panel();
    draw_other_scene_panels();

    fcn_80026d78();
}

/* ----------------------------------------------------------------------------
 * PHASE 6 FINDINGS:
 *  - CONFIRMED grain HUD reads G_GRAIN_COUNT (0x800a65a1), target 0x32, and
 *    draws packed decimal digits into 0x800b018e when pulse 0x800b018c == 0x400.
 *  - CONFIRMED seed HUD loop reads exactly G_SEED_CTR_ORANGE/BLUE/GREEN
 *    (0x800a6598..9a). The high nibble indexes icon tables near 0x80078e66/67.
 *  - CONFIRMED FLIK bitmask HUD reads G_FLIK_PROGRESS_BITS (0x800a65a2), bits
 *    0..3, drawing tiles 0x10..0x13 or dimmed boxes.
 *  - CONFIRMED FLIK record-icon HUD reads pointers 0x800a0220/0430/0a60/0d78
 *    and collected flag +0x1b; tile/x map: 0x32@0x54, 0x34@0x7c, 0x35@0xa4,
 *    0x33(+0x36)@0xcc/0xdc.
 *  - re_types.h promoted only G_FLIK_PROGRESS_BITS; no struct fields promoted.
 *  - Scene-specific source addresses and transforms are pinned; only their
 *    story/object labels remain unknown.
 * ---------------------------------------------------------------------------- */
