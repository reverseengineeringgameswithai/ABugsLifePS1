/*
 * Phase 4 A19 component-level reconstruction.
 * Evidence: pristine SCUS_942.88 static C decode plus bounded Interpreter
 * execTrace matrices. This is descriptive pseudocode, not build input.
 */
#include <stdint.h>

typedef struct {
    uint8_t health;           /* 0x800A6594 */
    uint8_t seed_power[4];    /* 0x800A6598..0x800A659B */
    uint8_t lives;            /* 0x800A65A0 */
    uint8_t grain;            /* 0x800A65A1 */
    uint8_t flik_mask;        /* 0x800A65A2 */
} StatusSources;

typedef struct {
    uint16_t lives_pulse;     /* 0x800B0188 */
    uint16_t lives_latch;     /* 0x800B018A */
    uint16_t grain_pulse;     /* 0x800B018C */
    uint16_t grain_digits;    /* 0x800B018E: low=tens, high=ones */
    uint16_t health_pulse;    /* 0x800B0190 */
    uint16_t health_latch;    /* 0x800B0192 */
    uint16_t seed_pulse;      /* 0x800B0194 */
} StatusDisplayState;

extern void hud_draw_sprite_tile(int x, int y, int tile, int variant); /* 0x80025F54 */
extern void hud_draw_glyph(int x, int y, int tile, int variant);       /* 0x800260F8 */
extern void hud_draw_glyph_tinted(int x, int y, int tile, int variant);/* 0x80026588 */
extern void result_upload_anim_frame(int tile, int variant, int frame);/* 0x80026DF4 */

static void draw_lives(const StatusDisplayState *d, int y)
{
    hud_draw_glyph(0x10, y, 0x1C, 0);              /* fixed Flik head */
    hud_draw_sprite_tile(0x4C, y + 0x0C, 0x1E,
                         d->lives_latch);           /* direct digit */
}

static void refresh_health(StatusDisplayState *d, const StatusSources *s)
{
    hud_draw_glyph(0x110, 0x10, 0x1D, 0);
    if (d->health_latch != s->health) {
        d->health_latch = s->health;
        result_upload_anim_frame(0x1D, 0, 4 - s->health);
    }
}

static void draw_grain(const StatusDisplayState *d, int y)
{
    hud_draw_glyph(0x10, y, 0x14, 0);
    hud_draw_sprite_tile(0x33, y, 0x1E, d->grain_digits & 0xFF);
    hud_draw_sprite_tile(0x3F, y, 0x1E, d->grain_digits >> 8);
}

static void draw_flik_letters(const StatusSources *s, int y)
{
    int i;
    for (i = 0; i != 4; ++i) {
        int x = 0x70 + i * 0x18;
        int tile = 0x10 + i;
        if (s->flik_mask & (1u << i))
            hud_draw_glyph(x, y, tile, 0);
        else
            hud_draw_glyph_tinted(x, y, tile, 0);
    }
}

/*
 * The selected seed-power indicator at 0x80053050 is suppressed when the
 * selected counter is zero. In the level01 fixture the selected counter was
 * seed_power[0]. Runtime variants for high nibbles 1,2,3,4 were 4,5,5,0.
 * The selector's owning address and inactive 0x80052C00 presentation branch
 * remain deliberately unnamed because neither is required by A19 closure.
 */
