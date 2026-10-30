/* Phase 4 C05 CORRECTION: what fcn.80051b84 and its callee actually are.
 *
 * My first C05 pass called fcn.80051b84 "the results-screen token renderer" and
 * said the masked unlock bit selects "earned-vs-locked presentation (the real
 * icon versus the red '?')".  BOTH CLAIMS ARE WRONG.  This tool pins the
 * evidence that corrects them.  The bit->record->sprite MAP itself is unchanged
 * and is re-pinned here so this tool stands alone.
 *
 * What fcn.80051b84 really is: an IN-WORLD marker render stage.
 *   - Its only caller is the per-frame gameplay state machine 0x8004ECD4.
 *   - Its first half is gated on live player fields (0x800A659E == 0x0B,
 *     0x800A657C == 0) and draws at FLIK'S LIVE WORLD POSITION
 *     (0x800A6500/04/08) -- coordinates a results screen has no use for.
 *   - Its second half walks the three reward-token records and, for each one
 *     that is not consumed, calls the marker stage with that axis's unlock bit.
 *
 * What the callee fcn.80051938 (falls through into 0x80051940) really does:
 *   a0 = record ptr, a1 = sprite id, a2 = the masked unlock bit
 *   1. reads record[0]/[4]/[8] as world X/Y/Z
 *   2. squared distance to 0x8009EC50/54/58 with each delta >>8
 *   3. if that exceeds 0x0004C8FF, RETURN -- a distance cull, not a draw
 *   4. a2 != 0  ->  a2 = 0x60      (bit set)
 *      a2 == 0  ->  a2 stays 0     (bit clear)
 *      then v0 = 0x60 - a2, so the pair (0xC0, v0) is 0xC0/0x00 when the bit is
 *      set and 0xC0/0x60 when it is clear -- a COLOUR/TINT component pair handed
 *      to the same sprite draw fcn.80022FE0 the first half uses, at
 *      record Y - 0x1A00 (i.e. hoisted above the object).
 *   5. registers the record into the marker list 0x800B1B58 + i*16, count at
 *      0x800824CA, capped at 0x2F.
 *
 * So the bit modulates an IN-WORLD MARKER'S TINT, distance-culled.  It is not a
 * results-screen icon and there is no '?' sprite anywhere in this path.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_c05_marker_stage.c \
 *      -o /tmp/phase4_c05_marker_stage
 *   /tmp/phase4_c05_marker_stage REBUILD/files/SCUS_942.88
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
    return (uint32_t)exe[off] | ((uint32_t)exe[off + 1] << 8) |
           ((uint32_t)exe[off + 2] << 16) | ((uint32_t)exe[off + 3] << 24);
}

struct pin { uint32_t pc, word; const char *role; };

static const struct pin pins[] = {
    /* ---- (1) this is gameplay code, not a results screen ---------------- */
    {0x80051B88u, 0x3C03800Au, "gate: lui for player field 0x800A659E"},
    {0x80051B8Cu, 0x8463659Eu, "gate: lh v1, [0x800A659E]"},
    {0x80051B90u, 0x2402000Bu, "gate: compare against 0x0B"},
    {0x80051BA4u, 0x8442657Cu, "gate: lh v0, [0x800A657C] (must be 0)"},
    {0x80051BB8u, 0x8CA56504u, "first half reads FLIK LIVE POSITION Y 0x800A6504"},
    {0x80051BC8u, 0x8CC66508u, "first half reads FLIK LIVE POSITION Z 0x800A6508"},
    {0x80051C10u, 0x8C426500u, "first half reads FLIK LIVE POSITION X 0x800A6500"},
    {0x80051C30u, 0x0C008BF8u, "first half: jal 0x80022FE0 (sprite draw)"},

    /* ---- (2) the three reward-token records, bit and sprite (unchanged) -- */
    {0x80051D10u, 0x3C108000u, "shared: s0 = 0x80000000 consumed sentinel"},

    {0x80051D08u, 0x24843988u, "A: a0 = record 0x800B3988 (G_FLK_SNAPSHOT)"},
    {0x80051D14u, 0x10500008u, "A: skip when record[0] == sentinel"},
    {0x80051D18u, 0x2405001Fu, "A: a1 = sprite id 0x1F"},
    {0x80051D20u, 0x8442245Cu, "A: level index [0x8008245C]"},
    {0x80051D2Cu, 0x9026B878u, "A: a2 = unlock_array[level] (0x8009B878)"},
    {0x80051D30u, 0x0C01464Eu, "A: jal 0x80051938 (marker stage)"},
    {0x80051D34u, 0x30C60002u, "A: mask bit 0x02  <= FLIK letters"},

    {0x80051D3Cu, 0x24840B68u, "B: a0 = record 0x80090B68 (all-defeated obj)"},
    {0x80051D48u, 0x10500008u, "B: skip when record[0] == sentinel"},
    {0x80051D4Cu, 0x2405001Bu, "B: a1 = sprite id 0x1B"},
    {0x80051D64u, 0x0C01464Eu, "B: jal 0x80051938 (marker stage)"},
    {0x80051D68u, 0x30C60004u, "B: mask bit 0x04  <= ENEMIES"},

    {0x80051D70u, 0x24840B80u, "C: a0 = record 0x80090B80 (G_REWARD_SNAPSHOT)"},
    {0x80051D7Cu, 0x10500008u, "C: skip when record[0] == sentinel"},
    {0x80051D80u, 0x24050028u, "C: a1 = sprite id 0x28"},
    {0x80051D98u, 0x0C01464Eu, "C: jal 0x80051938 (marker stage)"},
    {0x80051D9Cu, 0x30C60001u, "C: mask bit 0x01  <= GRAIN reward"},

    /* ---- (3) the callee: cull + tint, NOT an icon selector --------------- */
    {0x80051938u, 0x3C02800Au, "callee entry: lui for 0x8009EC50"},
    {0x8005193Cu, 0x8C42EC50u, "callee entry: v0 = [0x8009EC50] (compare X)"},
    {0x80051950u, 0x8E030000u, "callee: v1 = record[0] (world X)"},
    {0x80051968u, 0x8E050004u, "callee: a1 = record[4] (world Y)"},
    {0x80051970u, 0x8C42EC54u, "callee: v0 = [0x8009EC54] (compare Y)"},
    {0x80051984u, 0x8E030008u, "callee: v1 = record[8] (world Z)"},
    {0x8005198Cu, 0x8C42EC58u, "callee: v0 = [0x8009EC58] (compare Z)"},
    {0x8005195Cu, 0x00021203u, "callee: delta >> 8 before squaring"},
    {0x800519A0u, 0x3C030004u, "callee: cull radius hi  0x0004____"},
    {0x800519A4u, 0x3463C8FFu, "callee: cull radius lo  0x____C8FF"},
    {0x800519B4u, 0x0062182Au, "callee: slt v1, radius, dist2"},
    {0x800519B8u, 0x1460006Bu, "callee: if beyond radius -> RETURN (cull)"},
    {0x800519C0u, 0x10C00002u, "callee: TINT SELECT beqz a2 (the unlock bit)"},
    {0x800519C8u, 0x24060060u, "callee: bit SET   -> a2 = 0x60"},
    {0x800519D0u, 0x240200C0u, "callee: fixed component 0xC0"},
    {0x800519DCu, 0x00461023u, "callee: v0 = 0x60 - a2 (so 0x00 set / 0x60 clear)"},
    {0x800519CCu, 0x24A5E600u, "callee: a1 = record Y - 0x1A00 (hoisted above)"},
    {0x800519F4u, 0x0C008BF8u, "callee: jal 0x80022FE0 -- the SAME sprite draw"},

    /* ---- (4) marker list registration ----------------------------------- */
    {0x80051A00u, 0x846324CAu, "callee: marker count [0x800824CA]"},
    {0x80051A08u, 0x2862002Fu, "callee: count cap 0x2F"},
    {0x80051A24u, 0xAC221B58u, "callee: marker list 0x800B1B58 + i*16"},
};

int main(int argc, char **argv)
{
    FILE *f;
    long n;
    size_t i, ok = 0, total = sizeof pins / sizeof pins[0];

    if (argc != 2) { fprintf(stderr, "usage: %s <SCUS_942.88>\n", argv[0]); return 2; }
    f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    if (fseek(f, 0, SEEK_END) != 0) { perror("fseek"); fclose(f); return 2; }
    n = ftell(f);
    if (n <= 0) { fprintf(stderr, "empty image\n"); fclose(f); return 2; }
    rewind(f);
    exe_size = (size_t)n;
    exe = malloc(exe_size);
    if (!exe) { fprintf(stderr, "oom\n"); fclose(f); return 2; }
    if (fread(exe, 1, exe_size, f) != exe_size) { fprintf(stderr, "short read\n"); fclose(f); free(exe); return 2; }
    fclose(f);

    for (i = 0; i < total; i++) {
        uint32_t got = exe_u32(pins[i].pc);
        int good = (got == pins[i].word);
        ok += (size_t)good;
        printf("%s %08" PRIx32 "  want %08" PRIx32 "  got %08" PRIx32 "  %s\n",
               good ? "ok  " : "FAIL", pins[i].pc, pins[i].word, got, pins[i].role);
    }

    printf("\n%zu/%zu OK\n", ok, total);
    if (ok != total) { free(exe); return 1; }

    puts("\nCORRECTED READING (all of the above verified against the pristine image):");
    puts("  fcn.80051b84 is an IN-WORLD reward-token marker stage called only from");
    puts("  the gameplay state machine 0x8004ECD4 -- NOT a results-screen renderer.");
    puts("  The masked unlock bit picks a DRAW TINT COMPONENT (0xC0/0x00 when set,");
    puts("  0xC0/0x60 when clear) on a distance-culled sprite hoisted 0x1A00 above");
    puts("  the record's world position.  There is no icon/'?' selection here.");
    puts("  UNCHANGED: bit 0x01 grain 0x80090B80 sprite 0x28 | bit 0x02 FLIK");
    puts("  0x800B3988 sprite 0x1F | bit 0x04 enemies 0x80090B68 sprite 0x1B.");
    free(exe);
    return 0;
}
