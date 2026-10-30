/* Phase 4 D16: the species dispatch, Thumper's callback, and the mosquito.
 *
 * Re-derives the archived Thumper note's claims about the mosquito throw and
 * Thumper's "flight/attack cycle". That note is a COMPROMISED SOURCE: the same
 * page's "fight phase/attack counters at 0x80090BF2/0x80090BF6" claim was refuted
 * by a write-watch on 2026-08-04 (0x80090BF6 is BIOS-only). So nothing here is
 * cited from it; every claim is re-derived and pinned.
 *
 * THE SPECIES DISPATCH -- 0x8004A484..0x8004A6C0
 * ---------------------------------------------
 * One pass over 64 actor slots at load:
 *   actors  base = caller's arg (0x8009FE04 in the Council Chamber), stride 0x84
 *   roster  base = 0x80094A38,                                       stride 0x1C
 *   species byte = roster + 0x0C
 *   s3 = actor base, s1 = s3 + 8, s0 = roster + 0x12, s2 = roster
 *
 * ⚠️ THE +8 IS EASY TO MISS AND CHANGES EVERY OFFSET. Stores are written against
 * s1, so `sw x,0x74(s1)` is actor **+0x7C**, not +0x74. Reading the store offset
 * literally gives an answer that is wrong by exactly 8 -- which is how a first
 * pass at this file concluded "+0x74" and had to be corrected. Confirmed against
 * the same function's own HP store: mover_init_from_record writes HP at
 * `sh v0,110(t0)` with t0 = actor base = +0x6E, and Thumper's HP is at
 * 0x8009FE72 = 0x8009FE04 + 0x6E.
 *
 * Species 6..41 dispatch through the jump table at 0x8001B264. Each arm sets a
 * class byte at roster+0x10 and, for species that have one, installs a SPECIES
 * CALLBACK pointer at actor +0x7C.
 *
 *   species 16 (Thumper) -> 0x8004A5EC : sw fp,0x74(s1)   fp = 0x8004A0F4
 *   species 22, 36       -> 0x8004A5EC : the SAME arm, so the same callback
 *   species 10 (mosquito)-> 0x8004A540 : v0 = 0x8004A180, stored at 0x8004A604
 *
 * WHAT THUMPER'S CALLBACK ACTUALLY IS
 * -----------------------------------
 * The function census calls 0x8004A0F4 `thumper_driver_cb`. It is 40 bytes:
 *
 *     a1 = [a0+4];  play_sound(26, a1+4);  return
 *
 * It is a SOUND TRIGGER, not a fight driver -- the identical shape to its
 * neighbours object_play_sound_38_type_1_10 (0x8004A0A0) and
 * object_play_sound_125 (0x8004A11C). This is the same trap D18 already banked
 * for Thud ("+0x7C = play_sound not a driver"), on the same field, and the census
 * name encodes the wrong assumption. Thumper's fight logic is NOT here.
 *
 * WHAT THE MOSQUITO'S CALLBACK ACTUALLY IS
 * ----------------------------------------
 * 0x8004A180 (census: mosquito_species_callback) is real behaviour, 140 bytes:
 *
 *     s0 = [a0+4]                            ; the actor
 *     if ([s0+0x44] == 1) play_sound(42, s0+4)
 *     flags = [s0+0x5C]
 *     if ((flags & 0x1000) && [s0+0x44] == 1) {
 *         [s0+0x5C] = flags & ~0x1000        ; consume the trigger -- ONE SHOT
 *         [s0+0x6C] = 25
 *         [s0+0x1C] <<= 1                    ; DOUBLE
 *         [s0+0x24] <<= 1                    ; DOUBLE
 *     }
 *
 * Flags bit 0x1000 is a one-shot request; servicing it doubles two fields and
 * sets +0x6C = 25. The operator's observation that "the mosquito rises after the
 * hit" is consistent with this, but which field is vertical is NOT established
 * here -- see the live trace.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_d16_fight_static.c \
 *      -o /tmp/d16f && /tmp/d16f REBUILD/files/SCUS_942.88
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { EXE_HEADER_SIZE = 0x800, EXE_LOAD_VA = 0x80010000u };

#define DISPATCH_TABLE 0x8001B264u   /* species 6..41 */
#define SPECIES_LO 6
#define SPECIES_N  36
#define THUMPER_SPECIES  16
#define MOSQUITO_SPECIES 10
#define THUMPER_CB  0x8004A0F4u
#define MOSQUITO_CB 0x8004A180u
#define SHARED_ARM  0x8004A5ECu      /* species 16, 22 and 36 all land here */

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
    /* --- loop shape: strides, slot count, roster base ------------------- */
    {0x8004A488u, 0x26524A38u, "s2 = roster base 0x80094A38"},
    {0x8004A48Cu, 0x02009821u, "s3 = actor base (the caller's array pointer)"},
    {0x8004A4A8u, 0x26500012u, "s0 = roster + 0x12"},
    {0x8004A4ACu, 0x26710008u, "s1 = s3 + 8   <-- the +8 that shifts every store"},
    {0x8004A6A8u, 0x26310084u, "s1 += 132  (actor stride 0x84)"},
    {0x8004A6ACu, 0x26730084u, "s3 += 132  (actor stride 0x84)"},
    {0x8004A6B0u, 0x2610001Cu, "s0 += 28   (roster stride 0x1C)"},
    {0x8004A6B8u, 0x2A820040u, "slti s4,64 -- exactly 64 slots"},
    {0x8004A664u, 0x0C01270Cu, "jal 0x80049C30 mover_init_from_record(actor)"},

    /* --- the dispatch itself -------------------------------------------- */
    {0x8004A4B8u, 0x9203FFFAu, "lbu v1,-6(s0) = roster + 0x0C = SPECIES byte"},
    {0x8004A508u, 0x2443FFFAu, "v1 = species - 6"},
    {0x8004A50Cu, 0x2C620024u, "slti v1,36 -- species 6..41 are dispatched"},
    {0x8004A520u, 0x8C22B264u, "lw v0,[0x8001B264 + (species-6)*4]"},
    {0x8004A528u, 0x00400008u, "jr v0 -- the per-species arm"},

    /* --- Thumper: species 16 shares an arm with 22 and 36 --------------- */
    {0x8004A4A0u, 0x3C1E8005u, "fp = 0x8005_0000 ..."},
    {0x8004A4A4u, 0x27DEA0F4u, "... + (-24332) = 0x8004A0F4 (Thumper's callback)"},
    {0x8004A5ECu, 0x08012988u, "species 16/22/36 arm: j 0x8004A620"},
    {0x8004A5F0u, 0xAE3E0074u, "delay slot: sw fp,0x74(s1) -> actor +0x7C"},

    /* --- Thumper's callback is a play_sound wrapper, not a driver ------- */
    {0x8004A0F4u, 0x27BDFFE8u, "0x8004A0F4 entry (40 bytes total)"},
    {0x8004A0FCu, 0x8C850004u, "a1 = [a0+4]"},
    {0x8004A100u, 0x2404001Au, "a0 = 26  -- SOUND ID"},
    {0x8004A104u, 0x0C014113u, "jal 0x8005044C play_sound"},
    {0x8004A114u, 0x03E00008u, "jr ra -- that is the whole function"},

    /* --- mosquito: species 10 ------------------------------------------- */
    {0x8004A540u, 0x3C028005u, "species 10 arm: v0 = 0x8005_0000 ..."},
    {0x8004A544u, 0x2442A180u, "... + (-24192) = 0x8004A180 (mosquito callback)"},
    {0x8004A548u, 0x08012980u, "j 0x8004A600"},
    {0x8004A604u, 0xAE220074u, "sw v0,0x74(s1) -> actor +0x7C"},

    /* --- the mosquito callback's one-shot -------------------------------- */
    {0x8004A190u, 0x8C900004u, "s0 = [a0+4] (the actor)"},
    {0x8004A1B0u, 0x9604005Cu, "a0 = [s0+0x5C] flags"},
    {0x8004A1B8u, 0x30821000u, "andi 0x1000 -- the one-shot request bit"},
    {0x8004A1C8u, 0x3082EFFFu, "andi 0xefff -- CONSUME it"},
    {0x8004A1D0u, 0xA602005Cu, "store flags back"},
    {0x8004A1D4u, 0x24020019u, "v0 = 25"},
    {0x8004A1D8u, 0xA602006Cu, "[s0+0x6C] = 25"},
    {0x8004A1E4u, 0x00021040u, "sll v0,v0,1  -- DOUBLE [s0+0x1C]"},
    {0x8004A1E8u, 0x00031840u, "sll v1,v1,1  -- DOUBLE [s0+0x24]"},
    {0x8004A1ECu, 0xAE02001Cu, "store [s0+0x1C]"},
    {0x8004A1F0u, 0xAE030024u, "store [s0+0x24]"},

    /* --- the VM program pointer table ------------------------------------ */
    {0x80077B20u, 0x80077654u, "program table[10] = 0x80077654"},
    {0x80077B2Cu, 0x800776ACu, "program table[13] = 0x800776AC"},
};

int main(int argc, char **argv)
{
    FILE *f;
    long n;
    size_t i, ok = 0, total = sizeof pins / sizeof pins[0];
    int rc = 0;

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

    printf("=== species jump table 0x%08X (species %d..%d) ===\n",
           DISPATCH_TABLE, SPECIES_LO, SPECIES_LO + SPECIES_N - 1);
    {
        uint32_t thumper_arm = exe_u32(DISPATCH_TABLE + (THUMPER_SPECIES - SPECIES_LO) * 4);
        uint32_t mosq_arm    = exe_u32(DISPATCH_TABLE + (MOSQUITO_SPECIES - SPECIES_LO) * 4);
        int shared = 0;
        for (i = 0; i < SPECIES_N; i++) {
            uint32_t arm = exe_u32(DISPATCH_TABLE + (uint32_t)i * 4);
            if (arm == thumper_arm) shared++;
        }
        printf("  species %2d (Thumper)  -> 0x%08" PRIx32 "\n", THUMPER_SPECIES, thumper_arm);
        printf("  species %2d (mosquito) -> 0x%08" PRIx32 "\n", MOSQUITO_SPECIES, mosq_arm);
        printf("  %d species share Thumper's arm (so they share his callback)\n", shared);
        if (thumper_arm != SHARED_ARM) {
            printf("  FAIL: Thumper's arm moved\n");
            rc = 1;
        }
        /* Enumerate them, so "shared" is a listed fact rather than a count. */
        printf("  sharing species:");
        for (i = 0; i < SPECIES_N; i++)
            if (exe_u32(DISPATCH_TABLE + (uint32_t)i * 4) == thumper_arm)
                printf(" %zu", i + SPECIES_LO);
        putchar('\n');
    }

    printf("\n=== instruction pins ===\n");
    for (i = 0; i < total; i++) {
        uint32_t got = exe_u32(pins[i].va);
        int good = (got == pins[i].word);
        ok += (size_t)good;
        printf("  %s 0x%08" PRIx32 "  want %08" PRIx32 "  got %08" PRIx32 "  %s\n",
               good ? "ok  " : "FAIL", pins[i].va, pins[i].word, got, pins[i].role);
    }
    printf("  %zu/%zu pins OK\n", ok, total);
    if (ok != total) rc = 1;

    puts("");
    puts("D16 fight/mosquito, STATIC:");
    puts("  * the species callback field is actor +0x7C (stores are against s1 = actor+8,");
    puts("    so the literal 0x74 in the encoding is NOT the actor offset).");
    puts("  * Thumper (species 16) shares his arm -- and therefore his callback -- with");
    puts("    species 22 and 36; the callback 0x8004A0F4 is a 40-byte play_sound(26)");
    puts("    wrapper, NOT a fight driver. The census name `thumper_driver_cb` is wrong");
    puts("    in the same way D18 already recorded for Thud.");
    puts("  * the mosquito is species 10; its callback 0x8004A180 IS real behaviour: a");
    puts("    one-shot on flags bit 0x1000 that sets +0x6C = 25 and doubles +0x1C/+0x24.");
    puts("  * Thumper's fight logic is therefore NOT in his species callback. Where it");
    puts("    lives is a question for the live trace, not for this tool.");
    free(exe);
    return rc;
}
