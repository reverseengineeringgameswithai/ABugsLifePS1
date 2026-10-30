/* Phase 4 C05 item 3, RESOLVED STATICALLY: the marker bit is a SEMI-TRANSPARENCY
 * selector, not a colour/tint.
 *
 * History of this claim, because it took three passes to get right:
 *   2026-08-03  "the bit selects earned-vs-locked icons"      -- WRONG (venue)
 *   2026-08-04  "the bit picks a colour/tint component pair"  -- WRONG (semantic)
 *   2026-08-04  retracted to "meaning not established"        -- honest but open
 *   2026-08-04  THIS TOOL: the meaning, from the consumer     -- resolved
 *
 * THE CHAIN
 * ---------
 * Producer, in the marker stage's callee 0x80051940:
 *     bit SET   -> a2 = 0x60 -> v0 = 0x60 - 0x60 = 0x00
 *     bit CLEAR -> a2 = 0    -> v0 = 0x60 - 0    = 0x60
 *     sw v0, 0x18(sp)                       ; the 7th argument
 *
 * effect_mesh_transform 0x80022FE0 takes that 7th argument into s7 and stores it
 * at 0x8009E8E2 + index*28.
 *
 * The record actually begins at 0x8009E8D0 (28 bytes), so that field is +0x12.
 * There is exactly ONE consumer of these records -- 0x80023ABC, established by
 * the fact that only four functions touch the record count at 0x80082374
 * (gp+0x5DC): the two producers, this consumer, and a reset.  The consumer sets
 *     t6 = 0x800A0000 - 0x1730 = 0x8009E8D0
 *     t0 = t6 + 0x12          <-- EXACTLY the field the bit writes
 *     t0 += 0x1C per record
 * and then does:
 *     lh   v1, (t0)
 *     li   v0, 0x60
 *     beq  v1, v0, skip          ; == 0x60 -> leave it alone
 *     prim = [0x8008249C]
 *     prim[7] |= 0x02
 *   skip:
 *
 * prim bytes 4,5,6 are loaded from the same record's +0x08/+0x09/+0x0A, i.e. R,G,B.
 * In a PS1 GPU packet the first word after the tag is 0xCC_BBGGRR, so byte 7 is the
 * COMMAND byte -- and bit 0x02 of a polygon/rect command is the semi-transparency
 * (ABE) flag.  ORing 0x02 into byte 7 therefore turns the primitive translucent.
 *
 * RESULT, and note the direction:
 *     bit CLEAR (axis NOT yet earned) -> value 0x60 -> == 0x60 -> OPAQUE
 *     bit SET   (axis already earned) -> value 0x00 -> != 0x60 -> SEMI-TRANSPARENT
 *
 * So an already-earned reward keeps a translucent in-world marker.  That is the
 * same visual language as the results screen's dimmed already-earned token, but a
 * different mechanism: the screen modulates colour through 0x80026858, this sets
 * the GPU's semi-transparency bit.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror \
 *      tools/phase4_c05_marker_semitransparency.c -o /tmp/c05_semi
 *   /tmp/c05_semi REBUILD/files/SCUS_942.88
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
    if (va < EXE_LOAD_VA) { fprintf(stderr, "va below base\n"); exit(2); }
    off = EXE_HEADER_SIZE + (size_t)(va - EXE_LOAD_VA);
    if (off + 4 > exe_size) { fprintf(stderr, "va outside image\n"); exit(2); }
    return (uint32_t)exe[off] | ((uint32_t)exe[off+1] << 8) |
           ((uint32_t)exe[off+2] << 16) | ((uint32_t)exe[off+3] << 24);
}

struct pin { uint32_t va, word; const char *role; };

static const struct pin pins[] = {
    /* producer: the bit becomes 0x00 (set) or 0x60 (clear) */
    {0x800519C0u, 0x10C00002u, "producer: beqz a2 (the masked unlock bit)"},
    {0x800519C8u, 0x24060060u, "producer: bit SET -> a2 = 0x60"},
    {0x800519DCu, 0x00461023u, "producer: v0 = 0x60 - a2   (0x00 set / 0x60 clear)"},
    {0x800519E4u, 0xAFA20018u, "producer: sw v0, 0x18(sp)  = the 7th argument"},

    /* effect_mesh_transform stores it into the record at +0x12 (0x8009E8E2) */
    {0x8002301Cu, 0x8FB700C0u, "effect_mesh_transform: s7 = 7th argument"},
    {0x800234BCu, 0xA437E8E2u, "effect_mesh_transform: sh s7 -> 0x8009E8E2 + i*28"},

    /* the sole consumer: base, field pointer, stride */
    {0x80023AE8u, 0x25CEE8D0u, "consumer: t6 = 0x800A0000 - 0x1730 = 0x8009E8D0"},
    {0x80023AF0u, 0x25C80012u, "consumer: t0 = t6 + 0x12  <- THE field"},
    {0x80023CFCu, 0x2508001Cu, "consumer: t0 += 0x1C (28-byte stride)"},

    /* the decision */
    {0x80023C54u, 0x85030000u, "consumer: lh v1, (t0)"},
    {0x80023C58u, 0x24020060u, "consumer: li v0, 0x60"},
    {0x80023C5Cu, 0x10620008u, "consumer: beq v1, v0 -> SKIP (leave opaque)"},
    {0x80023C70u, 0x90620007u, "consumer: lbu v0, 7(prim)   (the GPU command byte)"},
    {0x80023C78u, 0x34420002u, "consumer: ori v0, v0, 0x02  = SEMI-TRANSPARENCY"},
    {0x80023C7Cu, 0xA0620007u, "consumer: sb v0, 7(prim)"},

    /* proof that bytes 4/5/6 are R,G,B -- which is what makes byte 7 the command */
    {0x80023C10u, 0x9022E8E8u, "consumer: lbu from record +0x08"},
    {0x80023C18u, 0xA0620004u, "consumer: sb -> prim[4]  = R"},
    {0x80023C2Cu, 0x9022E8E9u, "consumer: lbu from record +0x09"},
    {0x80023C34u, 0xA0620005u, "consumer: sb -> prim[5]  = G"},
    {0x80023C48u, 0x9022E8EAu, "consumer: lbu from record +0x0A"},
    {0x80023C50u, 0xA0620006u, "consumer: sb -> prim[6]  = B"},
};

int main(int argc, char **argv)
{
    FILE *f;
    long n;
    size_t i, ok = 0, total = sizeof pins / sizeof pins[0];

    if (argc != 2) { fprintf(stderr, "usage: %s <SCUS_942.88>\n", argv[0]); return 2; }
    f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 2; }
    n = ftell(f);
    if (n <= 0) { fclose(f); return 2; }
    rewind(f);
    exe_size = (size_t)n;
    exe = malloc(exe_size);
    if (!exe) { fclose(f); return 2; }
    if (fread(exe, 1, exe_size, f) != exe_size) { free(exe); fclose(f); return 2; }
    fclose(f);

    for (i = 0; i < total; i++) {
        uint32_t got = exe_u32(pins[i].va);
        int good = (got == pins[i].word);
        ok += (size_t)good;
        printf("%s %08" PRIx32 "  want %08" PRIx32 "  got %08" PRIx32 "  %s\n",
               good ? "ok  " : "FAIL", pins[i].va, pins[i].word, got, pins[i].role);
    }

    printf("\n%zu/%zu pins OK\n", ok, total);
    if (ok != total) { free(exe); return 1; }

    puts("\nITEM 3 RESOLVED -- the field is a SEMI-TRANSPARENCY selector, not a tint:");
    puts("  bit CLEAR (axis NOT yet earned) -> 0x60 -> == 0x60 -> OPAQUE marker");
    puts("  bit SET   (axis already earned) -> 0x00 -> != 0x60 -> SEMI-TRANSPARENT");
    puts("  (prim[4..6] = R,G,B, so prim[7] is the GPU command byte and 0x02 is ABE)");
    free(exe);
    return 0;
}
