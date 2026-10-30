/* ============================================================================
 * backdrop_sky_copier_8003b280.c — sky color copier + chunk-29 backdrop format [HRE-009]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESSES : sky-color copier loop at 0x8003B280..0x8003B31C+ (inside the
 *                      level-load path near the LZ decompressor drivers 0x8003A318/
 *                      0x8003B92C); consumer FUNC_800639CC (per-frame GP0 02 fill).
 * CONFIDENCE         : CONFIRMED copier math (disasm) + palette source (offline dump,
 *                      cross-level) + disc recolor lever (cold-boot sunset proof
 *                      2026-07-02). OPEN: the second color's meaning, header a/b
 *                      fields, VRAM upload site, backdrop draw transform.
 * SOURCE NOTES       : ObsidianVault/Systems/Backdrop and sky layer.md; r2 disasm.
 * CORRECTS           : Finding - Sky color on-disk table (the on-disk source is the
 *                      LEVEL.RAW CHUNK-29 palette, NOT chunk 32 — the old s3 register
 *                      capture read a staging address, not the byte source; that is
 *                      why "31 59 DB" was never found in chunk 32 but sits at chunk-29
 *                      local +0x10 = palette entry 0).
 * ============================================================================ */

#include "re_types.h"

#define LBU(p)  (*(uint8_t  *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))

#define G_SKY_CACHE_R 0x800771BCu /* DRAWENV cache; FUNC_800639CC builds GP0 02BBGGRR */
#define G_SKY_CACHE_G 0x800771C0u
#define G_SKY_CACHE_B 0x800771C4u

/* LEVEL.RAW chunk 29 — the per-level BACKDROP PANORAMA (decoded 2026-07-02).
 * LEVEL01 = the horizon (sky band / distant hills / grass rim / layered dirt wall);
 * LEVEL05 = the moonlit box city; LEVEL07 = a clover forest (128x160). Consumed at
 * level load: sky color extracted below; the indexed image is uploaded to VRAM as the
 * far-horizon texture (the palette run no longer exists in RAM at gameplay). */
typedef struct {
    uint32_t a;            /* +0x00 LEVEL01: 0x24 — meaning OPEN (draw params?)  */
    uint32_t b;            /* +0x04 LEVEL01: 0x4C — meaning OPEN                 */
    uint16_t width;        /* +0x08 LEVEL01: 128                                 */
    uint16_t height;       /* +0x0A LEVEL01: 96 (levels vary: 128, 160, ...)     */
    uint32_t pal_info;     /* +0x0C 0x00010300: lo16 = palette bytes (0x300),    */
                           /*        hi16 = 1 (format flag)                      */
    uint8_t  palette[256][3]; /* +0x010 RGB888 — entry 0 (LEVEL01) = 31 59 DB =  */
                              /* the sky fill: the flat sky seamlessly continues */
                              /* the image's top edge                            */
    /* uint8_t image[height][width];  +0x310 8bpp indexed panorama               */
} BackdropChunk29;

/* Copier at 0x8003B280 (level load; s3 = the chunk-29 staging base):
 *   record = s3 + (t1 & ~1); idx = record[+0x10];
 *   sky RGB = palette[idx] (table base s3+0x10, stride 3) -> DRAWENV cache.
 * A second lookup follows (index byte at [record'+0xF] after a mult-based advance)
 * feeding the next cache slots — LIKELY the far/fog companion color (OPEN). */
void sky_color_copier_8003b280(const uint8_t *s3 /* chunk-29 staging */, int t1)
{
    const uint8_t *record = s3 + (t1 & ~1);
    unsigned idx = LBU(record + 0x10);
    const uint8_t *entry = s3 + idx * 3;
    SW(G_SKY_CACHE_R, LBU(entry + 0x10));
    SW(G_SKY_CACHE_G, LBU(entry + 0x11));
    SW(G_SKY_CACHE_B, LBU(entry + 0x12));
    /* ... second color read (record'[+0xF] -> palette) follows in the original. */
}

/* ----------------------------------------------------------------------------
 * AUTHORING (proven cold-boot 2026-07-02, scratch disc ABL_SUNSET):
 *   decompress chunk 29 (seed_table.read_chunk_decompressed) -> edit palette or
 *   image -> tools/lz_encode_level_raw.compress_chunk (REAL back-reference LZ;
 *   the old literal-run recompressor would overflow LEVEL.RAW's fixed sector
 *   budget) -> splice + pad to the exact original file size -> rebuild.
 *   One palette edit recolors BOTH the flat sky and the horizon image.
 * ---------------------------------------------------------------------------- */
