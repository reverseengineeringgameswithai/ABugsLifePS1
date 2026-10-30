/*
 * phase4_e16_image_header.c -- test the CONSUMER-DERIVED header layouts for the
 * pointer-registered LEVEL.RAW chunks (E16).
 *
 * The three chunk pointer tables are read by exactly three sites, found live by
 * tools/phase4_e16_table_read_watch.py and disassembled with
 * tools/mips_ea_window.c on the pristine EXE. They split into TWO families with
 * DIFFERENT header layouts, and the split is visible in the code itself:
 *
 *  FAMILY A -- markers 0x28..0x2F, table 0x8009C170, read at 0x8003c3c0 inside
 *      vram_upload_wait (0x8003c388). It reads `lw v0,4(s4)` and `lw v1,8(s4)`
 *      -- 32-BIT fields -- and hands LoadImage `addiu a1,s4,16`, so the pixel
 *      data starts at +16:
 *          u32 marker @0, u32 width @+4, u32 height @+8, u32 @+12,
 *          16bpp pixels at +16.
 *          size == 16 + width*height*2
 *
 *  FAMILY B -- markers 0x30..0x5F, tables 0x8009B4E8 and 0x800A6450, read at
 *      0x8003c920 (level_texture_stage -> level_texture_upload 0x8003cc58) and
 *      0x8003c5ec (vram_upload_wait -> LoadImage). Both read `lhu` at +4/+6/+8
 *      (0x8003c5ec also +10) and take the payload from +12:
 *          u32 marker @0, u16 width @+4, u16 height @+6,
 *          u16 palette_bytes @+8, u16 depth_flag @+10,
 *          palette at +12, indexed pixels after it.
 *          size == 12 + palette_bytes + width*height        (depth_flag == 1, 8bpp)
 *          size == 12 + palette_bytes + width*height/2      (depth_flag == 0, 4bpp)
 *
 * Reading family A's 32-bit fields as 16-bit is what makes its height look like
 * 0 and its "depth flag" look like 0 -- those are just the high halves. Both
 * interpretations are reported so that confusion stays visible.
 *
 * These laws are DERIVED FROM THE CONSUMERS, not fitted to the sizes. That
 * matters here: a permissive size-formula search once "solved" 74/74 chunks and
 * a uniqueness check then showed ZERO of them were uniquely determined (see
 * UNKNOWN_MARKER_ANALYSIS in analysis/phase4_e16_chunk_census.json). This tool
 * has no free parameters -- each family's size law either holds exactly or does
 * not, and the result is reported either way.
 *
 * Build: cc -O2 -Werror -o /tmp/e16hdr tools/phase4_e16_image_header.c
 * Usage: /tmp/e16hdr <decompressed_chunk.bin> <chunk_id>
 * Output: one JSON object on stdout.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint16_t rd16(const uint8_t *b, long n, long off)
{
    if (off + 2 > n) return 0;
    return (uint16_t)(b[off] | (b[off + 1] << 8));
}

static uint32_t rd32(const uint8_t *b, long n, long off)
{
    if (off + 4 > n) return 0;
    return (uint32_t)b[off] | ((uint32_t)b[off + 1] << 8) |
           ((uint32_t)b[off + 2] << 16) | ((uint32_t)b[off + 3] << 24);
}

int main(int argc, char **argv)
{
    if (argc != 3) { fprintf(stderr, "usage: %s chunk.bin chunk_id\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *b = malloc(n > 0 ? n : 1);
    if (!b || fread(b, 1, n, f) != (size_t)n) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);

    if (n < 16) {
        printf("{\"chunk_id\":%s,\"ok\":false,\"reason\":\"shorter than a 16-byte header\"}\n",
               argv[2]);
        free(b);
        return 0;
    }

    uint32_t marker = rd32(b, n, 0);
    uint16_t f4 = rd16(b, n, 4), f6 = rd16(b, n, 6);
    uint16_t f8 = rd16(b, n, 8), f10 = rd16(b, n, 10);
    uint32_t w32 = rd32(b, n, 4), h32 = rd32(b, n, 8);

    const int family_a = (marker >= 0x28 && marker <= 0x2F);
    long expect = 0;
    const char *law;
    if (family_a) {
        expect = 16 + (long)w32 * (long)h32 * 2;
        law = "16 + w32*h32*2 (16bpp, pixels at +16)";
    } else if (f10 == 1) {
        expect = 12 + (long)(f8 & ~1u) + (long)f4 * (long)f6;
        law = "12 + palette_bytes + w*h (8bpp indexed)";
    } else {
        expect = 12 + (long)(f8 & ~1u) + (long)f4 * (long)f6 / 2;
        law = "12 + palette_bytes + w*h/2 (4bpp indexed)";
    }

    printf("{\"chunk_id\":%s,\"marker\":\"0x%04x\",\"size\":%ld,\"family\":\"%s\","
           "\"u16_at_4\":%u,\"u16_at_6\":%u,\"u16_at_8\":%u,\"u16_at_10\":%u,"
           "\"u32_at_4\":%u,\"u32_at_8\":%u,"
           "\"width\":%u,\"height\":%u,\"depth_bpp\":%d,\"palette_bytes\":%u,"
           "\"size_law\":\"%s\",\"expected_size\":%ld,\"size_law_holds\":%s,\"ok\":true}\n",
           argv[2], marker, n, family_a ? "A_markers_0x28_0x2F" : "B_markers_0x30_0x5F",
           f4, f6, f8, f10, w32, h32,
           family_a ? w32 : f4, family_a ? h32 : f6,
           family_a ? 16 : (f10 == 1 ? 8 : 4),
           family_a ? 0u : (unsigned)(f8 & ~1u),
           law, expect, (expect == n) ? "true" : "false");
    free(b);
    return 0;
}
