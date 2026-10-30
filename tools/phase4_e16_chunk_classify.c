/*
 * phase4_e16_chunk_classify.c -- structural classifier for LEVEL.RAW chunks (E16).
 *
 * The committed census (analysis/level_raw_chunks.json) labelled 17 chunks
 * "confirmed_format", 6 "confirmed" and left 46 as "likely" semantic guesses,
 * all derived from ONE file (LEVEL01/LEVEL.RAW) via boot traces.
 *
 * This classifier reads the chunk's own SUBTYPE MARKER -- a u32 at decompressed
 * offset 0 -- plus the secondary word at +4, so a chunk's family is read off
 * its bytes instead of inferred from load order. Known marker space:
 *
 *   0x0000..0x001F : texture/VRAM page (the value is the page's own index word)
 *   0x0020         : sky/backdrop RGB555 image
 *   0x0022         : sprite/animation strip container
 *   0x0023         : seed table
 *   0x0024         : backdrop panorama + sky palette
 *   0x0101         : mesh DEFINITION   (+4 = object id, +0x0A = sub-mesh count)
 *   0x0102         : mesh PAYLOAD      (+4 = object id -- pairs with its 0x101)
 *   0x0103         : collision planes + sky table
 *   0x0104         : collision sector-source table
 *
 * Reading one file proves nothing about the format; the driver runs this over
 * every chunk of every LEVEL*.RAW so the marker space can be shown to be closed
 * campaign-wide, and so each 0x101 can be paired with a 0x102 of the same id.
 *
 * Build: cc -O2 -Werror -o /tmp/e16 tools/phase4_e16_chunk_classify.c
 * Usage: /tmp/e16 <chunk.bin> <chunk_id>
 * Output: one JSON object on stdout.
 *
 * Correction history: the first classifier returned UNKNOWN for 0x20. The
 * pristine loader arm at 0x8003ADA4..0x8003AEE4 pins it as the sky/backdrop
 * RGB555 resource; leaving UNKNOWN live contradicted the later loader proof.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *family(uint32_t m)
{
    if (m < 0x20)     return "texture_page";
    switch (m) {
    case 0x20:        return "sky_backdrop";
    case 0x22:        return "sprite_strip_container";
    case 0x23:        return "seed_table";
    case 0x24:        return "backdrop_panorama";
    case 0x101:       return "mesh_definition";
    case 0x102:       return "mesh_payload";
    case 0x103:       return "collision_planes";
    case 0x104:       return "collision_sector_source";
    default:          return "UNKNOWN";
    }
}

int main(int argc, char **argv)
{
    if (argc != 3) { fprintf(stderr, "usage: %s chunk.bin chunk_id\n", argv[0]); return 2; }
    long id = strtol(argv[2], NULL, 0);
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *b = malloc(n < 16 ? 16 : n);
    if (!b || fread(b, 1, n, f) != (size_t)n) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);
    if (n < 8) { printf("{\"chunk_id\":%ld,\"ok\":false,\"why\":\"short\"}\n", id); return 1; }

    uint32_t marker, second; uint16_t submesh = 0;
    memcpy(&marker, b, 4);
    memcpy(&second, b + 4, 4);
    if (n >= 0xC) memcpy(&submesh, b + 0x0A, 2);

    /* structural probes per family, all read-only and bounds-checked */
    long extra = -1;
    if (marker == 0x22 && n >= 0x10) {
        uint32_t w, h; memcpy(&w, b + 8, 4); memcpy(&h, b + 12, 4);
        extra = (long)(w & 0xFFFF) * (h >> 16 ? 1 : 1);   /* dims live at +8/+0xA */
    }

    printf("{\"chunk_id\":%ld,\"ok\":true,\"size\":%ld,\"marker\":\"0x%04x\","
           "\"family\":\"%s\",\"second_word\":%u,\"submesh_count\":%u,\"probe\":%ld}\n",
           id, n, marker, family(marker), second, submesh, extra);
    return 0;
}
