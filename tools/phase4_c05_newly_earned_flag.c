/* Phase 4 C05 last loose end: what consumes the newly-earned flag 0x800823E4.
 *
 * The results-screen evaluator sets 0x800823E4 = 1 whenever any axis is earned for
 * the FIRST time (three stores, one per axis).  Nothing in the resident executable
 * ever reads it.  Inside BITS/MEMORY.BIN there is exactly ONE load, at 0x800B8AD0,
 * in a routine that begins at 0x800B8ACC -- and it is the SAVE path.
 *
 *   v0 = [0x800823E4]                  ; newly-earned flag
 *   [0x800BE5A4] = 0
 *   if (v0 == 0) goto done             ; nothing new -> do not save at all
 *   v0 = 0x800B7BA4()                  ; gate routine; its result decides
 *   [0x800823E4] = v0
 *   if (v0 == 0) goto clear            ; gate said no -> skip
 *   s0 = 0x8009EC68                    ; THE SAVE BUFFER
 *   0x80055478(s0)                     ; serialize_savegame_buffer   (Canon)
 *   if (0x800BB6F4() != 0)             ; the card write
 *       [0x8008245C] = -2              ; failure sentinel into the level index
 *   0x80055538(s0)                     ; the save DESERIALIZER        (Canon)
 * clear:
 *   [0x800823E4] = 0
 * done:
 *
 * So the flag's whole purpose is: "progress changed on this results screen --
 * therefore run the save flow."  It is the link between the C05 token evaluation
 * and E14's save schema, and it explains why a level that is merely REPLAYED (every
 * axis already earned, so every slot == 2) does not trigger a save: the flag is
 * never set, so this routine skips the entire block.
 *
 * NOTE: an earlier guess that this flag gated the "Congratulations! Bonus Movie
 * Clip Earned" screen was WRONG.  It was recorded as an untested hypothesis and is
 * corrected here.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_c05_newly_earned_flag.c \
 *      -o /tmp/c05_flag
 *   /tmp/c05_flag REBUILD/files/BITS/MEMORY.BIN
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define OVL_BASE 0x800B5788u

static uint8_t *img;
static long img_size;

static uint32_t va32(uint32_t va)
{
    long off = (long)(va - OVL_BASE);
    if (off < 0 || off + 4 > img_size) { fprintf(stderr, "va %08" PRIx32 " outside\n", va); exit(2); }
    return (uint32_t)img[off] | ((uint32_t)img[off+1] << 8) |
           ((uint32_t)img[off+2] << 16) | ((uint32_t)img[off+3] << 24);
}

struct pin { uint32_t va, word; const char *role; };

static const struct pin pins[] = {
    /* the three producers, inside the results evaluator */
    {0x800B7EACu, 0xAC2923E4u, "producer A (grain newly earned): [0x800823E4] = 1"},
    {0x800B7F0Cu, 0xAC2923E4u, "producer B (FLIK newly earned):  [0x800823E4] = 1"},
    {0x800B7F6Cu, 0xAC2923E4u, "producer C (enemies newly earned):[0x800823E4] = 1"},

    /* the single consumer -- the save path */
    {0x800B8ACCu, 0x3C028008u, "consumer entry 0x800B8ACC: lui v0, 0x8008"},
    {0x800B8AD0u, 0x8C4223E4u, "consumer: v0 = [0x800823E4]   (the ONLY load anywhere)"},
    {0x800B8AD4u, 0x27BDFF60u, "consumer prologue: addiu sp, sp, -0xA0"},
    {0x800B8B08u, 0x10400015u, "if flag == 0 -> skip the whole save block"},
    {0x800B8B10u, 0x0C02DEE9u, "jal 0x800B7BA4 (gate routine)"},
    {0x800B8B1Cu, 0xAC2223E4u, "[0x800823E4] = gate result"},
    {0x800B8B20u, 0x1040000Du, "if gate result == 0 -> skip to the clear"},
    {0x800B8B2Cu, 0x2610EC68u, "s0 = 0x800A0000 - 0x1398 = 0x8009EC68  (SAVE BUFFER)"},
    {0x800B8B30u, 0x0C01551Eu, "jal 0x80055478  serialize_savegame_buffer"},
    {0x800B8B34u, 0x02002021u, "  a0 = s0 (the buffer)"},
    {0x800B8B38u, 0x0C02EDBDu, "jal 0x800BB6F4  (the card write)"},
    {0x800B8B40u, 0x10400003u, "if write returned 0 -> skip the failure sentinel"},
    {0x800B8B44u, 0x2402FFFEu, "failure sentinel value -2"},
    {0x800B8B4Cu, 0xA422245Cu, "  [0x8008245C] = -2   (the level index)"},
    {0x800B8B50u, 0x0C01554Eu, "jal 0x80055538  (the save deserializer)"},
    {0x800B8B54u, 0x02002021u, "  a0 = s0 (the same buffer)"},
    {0x800B8B5Cu, 0xAC2023E4u, "[0x800823E4] = 0   (clear the flag)"},
};

int main(int argc, char **argv)
{
    FILE *f;
    size_t i, ok = 0, total = sizeof pins / sizeof pins[0];

    if (argc != 2) { fprintf(stderr, "usage: %s <BITS/MEMORY.BIN>\n", argv[0]); return 2; }
    f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 2; }
    img_size = ftell(f);
    rewind(f);
    img = malloc((size_t)img_size);
    if (!img) { fclose(f); return 2; }
    if (fread(img, 1, (size_t)img_size, f) != (size_t)img_size) { free(img); fclose(f); return 2; }
    fclose(f);

    for (i = 0; i < total; i++) {
        uint32_t got = va32(pins[i].va);
        int good = (got == pins[i].word);
        ok += (size_t)good;
        printf("%s %08" PRIx32 " (+0x%05lx)  want %08" PRIx32 "  got %08" PRIx32 "  %s\n",
               good ? "ok  " : "FAIL", pins[i].va, (long)(pins[i].va - OVL_BASE),
               pins[i].word, got, pins[i].role);
    }

    printf("\n%zu/%zu pins OK\n", ok, total);
    if (ok != total) { free(img); return 1; }

    puts("\nLOOSE END CLOSED: 0x800823E4 is the SAVE TRIGGER.");
    puts("  set by the results screen when any axis is earned for the FIRST time;");
    puts("  read exactly once, at 0x800B8AD0, to decide whether to run the save flow");
    puts("  (serialize 0x80055478 -> card write 0x800BB6F4 -> restore 0x80055538)");
    puts("  over the buffer at 0x8009EC68, then cleared.");
    puts("  A pure REPLAY of an already-100% level therefore never saves: every slot");
    puts("  is 2, the flag is never set, and this routine skips the whole block.");
    free(img);
    return 0;
}
