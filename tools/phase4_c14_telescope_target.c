/* Phase 4 C14: pin the telescope TARGET-SELECTION chain and dump the authored
 * path records the preview flies.
 *
 * Chain (all words verified against the pristine EXE below):
 *   setpiece_spawn_manager 0x8004D698
 *     v0 = [0x800823CC]                     ; telescope index (or setpiece slot)
 *     v1 = [0x800824DC]                     ; shared special-view state
 *     s0 = [0x80096DC8 + v0*4]              ; -> LEVEL.DAT path record (BSS ptr table)
 *     if (state == -1):                     ; the shared trigger
 *        spawn_init(rec[+0x10,+0x14,+0x18]<<5,   ; waypoint 1 -> actor position
 *                   rec[+0x04]<<5,               ; waypoint 0 x -> target
 *                   rec[+0x08]<<5, rec[+0x0C]<<5,; waypoint 0 y,z -> target
 *                   kind = 2)
 *   setpiece_spawn_init 0x8004D9E8
 *     writes the SETPIECE ACTOR struct 0x80090BC0:
 *       +0x00/04/08 position (= waypoint 1), mirrored at +0x18/1C/20
 *       +0x0C/10/14 target   (= waypoint 0)
 *       +0x26 heading = atan2_heading(0x80060AE4)(tx-px, tz-pz)
 *       +0x2C state = 2, +0x2E kind (2 here)
 *
 * The follow camera (0x80095358) is NOT involved -- live tracing shows it parked
 * for the whole view. The preview is rendered from this setpiece actor.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_c14_telescope_target.c \
 *      -o /tmp/phase4_c14_telescope_target
 *   /tmp/phase4_c14_telescope_target REBUILD/files/SCUS_942.88 REBUILD/files/LEVEL01/LEVEL.DAT
 *
 * Expected EXE SHA-256: 1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { EXE_HEADER_SIZE = 0x800, EXE_LOAD_VA = 0x80010000u };

/* LEVEL01 setpiece/telescope path records (committed: Enemy_spawn_architecture). */
static const uint32_t LEVEL01_PATH_RECORDS[] = {0x94Cu, 0xA10u, 0xAD4u};
#define PATH_RECORD_STRIDE 0xC4u /* 4-byte header + 16 waypoints * 12 bytes */

static uint8_t *exe;
static size_t exe_size;

static uint32_t exe_u32(uint32_t va)
{
    size_t off;
    if (va < EXE_LOAD_VA) {
        fprintf(stderr, "va below load base: %08" PRIx32 "\n", va);
        exit(2);
    }
    off = EXE_HEADER_SIZE + (size_t)(va - EXE_LOAD_VA);
    if (off + 4 > exe_size) {
        fprintf(stderr, "va outside image: %08" PRIx32 "\n", va);
        exit(2);
    }
    return (uint32_t)exe[off] | ((uint32_t)exe[off + 1] << 8) |
           ((uint32_t)exe[off + 2] << 16) | ((uint32_t)exe[off + 3] << 24);
}

struct pin { uint32_t pc, word; const char *role; };

static const struct pin pins[] = {
    /* manager: index -> path-record pointer */
    {0x8004D698u, 0x3C028008u, "manager: lui for index read"},
    {0x8004D69Cu, 0x8C4223CCu, "manager: v0 = telescope index [0x800823CC]"},
    {0x8004D6A4u, 0x8C6324DCu, "manager: v1 = shared state [0x800824DC]"},
    {0x8004D6B4u, 0x00021080u, "manager: index *= 4"},
    {0x8004D6B8u, 0x3C018009u, "manager: lui 0x8009 for the ptr table"},
    {0x8004D6BCu, 0x00220821u, "manager: at += index*4"},
    {0x8004D6C0u, 0x8C306DC8u, "manager: s0 = [0x80096DC8 + index*4] (path record)"},
    {0x8004D6ECu, 0x2402FFFFu, "manager: li -1 (trigger compare)"},
    {0x8004D6F0u, 0x14620014u, "manager: branch unless state == -1"},
    {0x8004D6F4u, 0x24030002u, "manager: li kind = 2"},
    /* the six authored coordinate loads, all <<5 (file -> runtime) */
    {0x8004D6F8u, 0x8E040010u, "record +0x10 -> a0 (waypoint1 x)"},
    {0x8004D6FCu, 0x8E050014u, "record +0x14 -> a1 (waypoint1 y)"},
    {0x8004D700u, 0x8E060018u, "record +0x18 -> a2 (waypoint1 z)"},
    {0x8004D704u, 0x8E020008u, "record +0x08 -> v0 (waypoint0 y)"},
    {0x8004D708u, 0x8E070004u, "record +0x04 -> a3 (waypoint0 x)"},
    {0x8004D720u, 0x8E02000Cu, "record +0x0C -> v0 (waypoint0 z)"},
    {0x8004D70Cu, 0x00042140u, "a0 <<= 5"},
    {0x8004D710u, 0x00052940u, "a1 <<= 5"},
    {0x8004D718u, 0x00063140u, "a2 <<= 5"},
    {0x8004D724u, 0x00073940u, "a3 <<= 5"},
    {0x8004D730u, 0x0C01367Au, "manager: jal setpiece_spawn_init 0x8004D9E8"},
    /* setpiece_spawn_init: writes the setpiece actor struct 0x80090BC0 */
    {0x8004DA00u, 0xAC240BC0u, "init: actor +0x00 = position x"},
    {0x8004DA18u, 0xAC250BC4u, "init: actor +0x04 = position y"},
    {0x8004DA20u, 0xAC260BC8u, "init: actor +0x08 = position z"},
    {0x8004DA28u, 0xAC270BCCu, "init: actor +0x0C = target x"},
    {0x8004DA48u, 0xAC230BD0u, "init: actor +0x10 = target y"},
    {0x8004DA50u, 0xAC220BD4u, "init: actor +0x14 = target z"},
    {0x8004DA08u, 0xAC240BD8u, "init: actor +0x18 = position x mirror"},
    {0x8004DA54u, 0x0C0182B9u, "init: jal atan2_heading 0x80060AE4"},
    {0x8004DA60u, 0xA4220BE6u, "init: actor +0x26 = heading"},
    {0x8004DA74u, 0xA4220BECu, "init: actor +0x2C = state 2"},
    {0x8004DA7Cu, 0xA4300BEEu, "init: actor +0x2E = kind"},
};

static int32_t dat_s32(const uint8_t *d, size_t n, uint32_t off)
{
    if ((size_t)off + 4 > n) { fprintf(stderr, "DAT offset out of range\n"); exit(2); }
    return (int32_t)((uint32_t)d[off] | ((uint32_t)d[off+1] << 8) |
                     ((uint32_t)d[off+2] << 16) | ((uint32_t)d[off+3] << 24));
}

int main(int argc, char **argv)
{
    FILE *f; long end; size_t i, bad = 0;
    uint8_t *dat = NULL; size_t dat_size = 0;

    if (argc != 3) {
        fprintf(stderr, "usage: %s SCUS_942.88 LEVEL01/LEVEL.DAT\n", argv[0]);
        return 2;
    }
    f = fopen(argv[1], "rb");
    if (!f || fseek(f, 0, SEEK_END) || (end = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) {
        perror(argv[1]); return 2;
    }
    exe_size = (size_t)end;
    exe = malloc(exe_size);
    if (!exe || fread(exe, 1, exe_size, f) != exe_size) { fprintf(stderr, "short read\n"); return 2; }
    fclose(f);

    for (i = 0; i < sizeof(pins)/sizeof(pins[0]); i++) {
        uint32_t got = exe_u32(pins[i].pc);
        if (got != pins[i].word) {
            fprintf(stderr, "MISMATCH %08" PRIx32 " (%s): got %08" PRIx32 " want %08" PRIx32 "\n",
                    pins[i].pc, pins[i].role, got, pins[i].word);
            bad++;
        }
    }
    if (bad) { fprintf(stderr, "%zu pin(s) failed\n", bad); return 1; }
    printf("C14 target-selection pins: %zu/%zu OK\n",
           sizeof(pins)/sizeof(pins[0]), sizeof(pins)/sizeof(pins[0]));

    f = fopen(argv[2], "rb");
    if (!f || fseek(f, 0, SEEK_END) || (end = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) {
        perror(argv[2]); return 2;
    }
    dat_size = (size_t)end;
    dat = malloc(dat_size);
    if (!dat || fread(dat, 1, dat_size, f) != dat_size) { fprintf(stderr, "short DAT read\n"); return 2; }
    fclose(f);

    puts("\nLEVEL01 authored path records (file coords, and <<5 runtime):");
    for (i = 0; i < sizeof(LEVEL01_PATH_RECORDS)/sizeof(LEVEL01_PATH_RECORDS[0]); i++) {
        uint32_t base = LEVEL01_PATH_RECORDS[i];
        int32_t w0x = dat_s32(dat, dat_size, base + 0x04);
        int32_t w0y = dat_s32(dat, dat_size, base + 0x08);
        int32_t w0z = dat_s32(dat, dat_size, base + 0x0C);
        int32_t w1x = dat_s32(dat, dat_size, base + 0x10);
        int32_t w1y = dat_s32(dat, dat_size, base + 0x14);
        int32_t w1z = dat_s32(dat, dat_size, base + 0x18);
        int32_t hdr = dat_s32(dat, dat_size, base + 0x00);
        printf("  record %zu @0x%04" PRIx32 " hdr=%" PRId32 " (stride 0x%X)\n",
               i, base, hdr, PATH_RECORD_STRIDE);
        printf("    waypoint1 (actor POSITION): file(%8" PRId32 ",%8" PRId32 ",%8" PRId32 ")"
               "  runtime(%10" PRId32 ",%10" PRId32 ",%10" PRId32 ")\n",
               w1x, w1y, w1z, w1x << 5, w1y << 5, w1z << 5);
        printf("    waypoint0 (look TARGET)   : file(%8" PRId32 ",%8" PRId32 ",%8" PRId32 ")"
               "  runtime(%10" PRId32 ",%10" PRId32 ",%10" PRId32 ")\n",
               w0x, w0y, w0z, w0x << 5, w0y << 5, w0z << 5);
    }
    free(exe); free(dat);
    return 0;
}
