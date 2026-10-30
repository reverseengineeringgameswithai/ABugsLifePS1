/* Phase 4 C05: pin the THREE-TOKEN bit map.
 *
 * ⚠️ CORRECTED 2026-08-04 -- this header originally called fcn.80051b84 "the
 * results-screen THREE-TOKEN renderer" and the callee a "token draw" selecting
 * "locked vs earned".  That framing is WRONG.  fcn.80051b84 is an IN-WORLD
 * marker stage called only from the gameplay state machine 0x8004ECD4, and the
 * bit picks a draw TINT component, not an icon.  See
 * tools/phase4_c05_marker_stage.c (47/47), which pins the corrected reading.
 * THE PINS BELOW AND THE BIT MAP ARE UNCHANGED AND REMAIN CORRECT.
 *
 * fcn.80051b84's second half walks the three reward-token records. Each block:
 *   a0 = the token's source record   (skip if its word == 0x80000000,
 *                                     the documented "consumed" sentinel)
 *   a1 = sprite id
 *   a2 = unlock_array[current_level] & <one bit>
 *   jal fcn.80051938                                 ; marker stage
 * with the level index read from 0x8008245C and the array at 0x8009B878
 * (the same 16-byte per-level array C17 decoded; value 7 == all three bits).
 *
 *   bit 0x01  source 0x80090B80 (G_REWARD_SNAPSHOT, grain reward)   sprite 0x28
 *   bit 0x02  source 0x800B3988 (G_FLK_SNAPSHOT,  FLIK letters)     sprite 0x1F
 *   bit 0x04  source 0x80090B68 (all-defeated event obj, enemies)   sprite 0x1B
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_c05_tokens_static.c \
 *      -o /tmp/phase4_c05_tokens_static
 *   /tmp/phase4_c05_tokens_static REBUILD/files/SCUS_942.88
 *
 * Expected EXE SHA-256: 1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { EXE_HEADER_SIZE = 0x800, EXE_LOAD_VA = 0x80010000u };

static uint8_t *exe;
static size_t exe_size;

static uint32_t exe_u32(uint32_t va)
{
    size_t off;
    if (va < EXE_LOAD_VA) { fprintf(stderr, "va below base %08" PRIx32 "\n", va); exit(2); }
    off = EXE_HEADER_SIZE + (size_t)(va - EXE_LOAD_VA);
    if (off + 4 > exe_size) { fprintf(stderr, "va outside image %08" PRIx32 "\n", va); exit(2); }
    return (uint32_t)exe[off] | ((uint32_t)exe[off+1] << 8) |
           ((uint32_t)exe[off+2] << 16) | ((uint32_t)exe[off+3] << 24);
}

struct pin { uint32_t pc, word; const char *role; };

static const struct pin pins[] = {
    /* shared: the consumed-sentinel compare value */
    {0x80051D10u, 0x3C108000u, "s0 = 0x80000000 (consumed sentinel)"},

    /* token A: FLIK letters -> bit 0x02, sprite 0x1F */
    {0x80051D04u, 0x3C04800Bu, "A: lui for source 0x800B3988"},
    {0x80051D08u, 0x24843988u, "A: a0 = 0x800B3988 (G_FLK_SNAPSHOT)"},
    {0x80051D14u, 0x10500008u, "A: skip draw if source == sentinel"},
    {0x80051D18u, 0x2405001Fu, "A: sprite id 0x1F"},
    {0x80051D20u, 0x8442245Cu, "A: level index [0x8008245C]"},
    {0x80051D2Cu, 0x9026B878u, "A: a2 = unlock_array[level]"},
    {0x80051D30u, 0x0C01464Eu, "A: jal token draw 0x80051938"},
    {0x80051D34u, 0x30C60002u, "A: mask bit 0x02  <= FLIK"},

    /* token B: enemies (all-defeated event object) -> bit 0x04, sprite 0x1B */
    {0x80051D38u, 0x3C048009u, "B: lui for source 0x80090B68"},
    {0x80051D3Cu, 0x24840B68u, "B: a0 = 0x80090B68 (all-defeated event obj)"},
    {0x80051D48u, 0x10500008u, "B: skip draw if source == sentinel"},
    {0x80051D4Cu, 0x2405001Bu, "B: sprite id 0x1B"},
    {0x80051D54u, 0x8442245Cu, "B: level index [0x8008245C]"},
    {0x80051D60u, 0x9026B878u, "B: a2 = unlock_array[level]"},
    {0x80051D64u, 0x0C01464Eu, "B: jal token draw 0x80051938"},
    {0x80051D68u, 0x30C60004u, "B: mask bit 0x04  <= ENEMIES"},

    /* token C: grain reward -> bit 0x01, sprite 0x28 */
    {0x80051D6Cu, 0x3C048009u, "C: lui for source 0x80090B80"},
    {0x80051D70u, 0x24840B80u, "C: a0 = 0x80090B80 (G_REWARD_SNAPSHOT)"},
    {0x80051D7Cu, 0x10500008u, "C: skip draw if source == sentinel"},
    {0x80051D80u, 0x24050028u, "C: sprite id 0x28"},
    {0x80051D88u, 0x8442245Cu, "C: level index [0x8008245C]"},
    {0x80051D94u, 0x9026B878u, "C: a2 = unlock_array[level]"},
    {0x80051D98u, 0x0C01464Eu, "C: jal token draw 0x80051938"},
    {0x80051D9Cu, 0x30C60001u, "C: mask bit 0x01  <= GRAIN"},
};

int main(int argc, char **argv)
{
    FILE *f; long end; size_t i, bad = 0;
    if (argc != 2) { fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]); return 2; }
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
    free(exe);
    if (bad) { fprintf(stderr, "%zu pin(s) failed\n", bad); return 1; }
    printf("C05 three-token renderer pins: %zu/%zu OK\n",
           sizeof(pins)/sizeof(pins[0]), sizeof(pins)/sizeof(pins[0]));
    puts("TOKEN BIT MAP (unlock_array[level] @0x8009B878, all three set == 7):");
    puts("  bit 0x01  grain reward   src 0x80090B80  sprite 0x28   (row C02)");
    puts("  bit 0x02  FLIK letters   src 0x800B3988  sprite 0x1F   (row C03)");
    puts("  bit 0x04  enemies        src 0x80090B68  sprite 0x1B   (row C04)");
    puts("Value 7 is exactly what C17 found unlocks that level's bonus movie clip.");
    return 0;
}
