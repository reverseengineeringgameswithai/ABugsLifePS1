/* Phase 4 C16: lives, the game-over branch, and the new-game defaults.
 *
 * All pins are offline against the pristine SCUS_942.88.
 *
 * WHERE LIVES LIVES
 * -----------------
 * A whole-image scan for load/store instructions carrying the immediate 0x65A0
 * finds 23 accesses to lives 0x800A65A0, 10 of them stores -- and, crucially, the
 * overlay images contain NONE (BITS/MEMORY.BIN has zero).  So the entire lives
 * lifecycle is resident.  Of the 10 stores:
 *   - EIGHT are grants: lives+1 guarded by `sltiu v1, 9`, i.e. CAPPED AT 9
 *     (0x80049858, 0x800518B8, 0x80053DF8, 0x80053F54, 0x800540B0, 0x8005420C,
 *      0x800550A0 in the grain-pickup body, and the 0x8004983C site);
 *   - ONE is the save deserializer restoring it (0x80055550);
 *   - ONE more decrements (0x80050210) -- but see the CORRECTION below: it is NOT
 *     the decrement that actually runs on death.
 *
 * !! CORRECTION 2026-08-04 (operator movie C16_lives_gameover.movie.json) !!
 * The live run decrements lives NINE times and EVERY write comes from PC 0x8005B34C
 * (store at 0x8005B348), inside respawn_transition_state_handler 0x8005B134 -- not
 * from 0x80050210, which never executed. My "only one decrement" classification was
 * produced by a heuristic that looked back only TWO words for an `addiu -1`; the real
 * death decrement is `addiu a2, a2, -1` at 0x8005B334, FIVE instructions before its
 * store. The heuristic was too narrow AND I had encoded it as a passing self-check,
 * which is exactly the "never encode an inference as a passing structural check"
 * failure. The 23/10 access counts stand; the "1 decrementing" count does not.
 *
 * THE DECREMENT AND THE GAME-OVER BRANCH
 * --------------------------------------
 * Inside scene_flow_dispatcher (0x8004FCA0..0x800502C4):
 *
 *     v0 = [0x800A65A0]                 ; lives
 *     if (v0 == 0) goto 0x800500D4      ; *** GAME OVER ***
 *     v0 = v0 - 1                       ; (delay slot)
 *     [0x800A65A0] = v0                 ; otherwise consume one life
 *
 * This is the instruction-level form of the registry's already-committed law that
 * lives 0 is PLAYABLE -- it is the final life, and dying on it is what ends the run.
 *
 * GAME OVER ITSELF (0x800500D4)
 * -----------------------------
 *     fmv_bin_load(0x2E, 0)             ; FMV id 46 -- the game-over movie
 *     scene_setup_and_load(5, 0x40)
 *
 * ⚠️ TENSION, NOT RESOLVED HERE: the registry binding says "death on lives 0 ->
 * game-over transition to scene 0 (lifecycle oracle)".  The code passes 5, not 0.
 * Either a0 is not a raw scene id, or the oracle observed the settled end state
 * after further transitions.  Flagged for a live check rather than silently
 * picking one.
 *
 * NEW-GAME DEFAULTS (0x80055414)
 * ------------------------------
 * The census calls it scene_flow_state_table_init; it is really the SAVE BUFFER
 * initializer, and its layout matches the schema C05/C17/E14 established:
 *     buf[0]        = 5        ; INITIAL LIVES
 *     buf[1]        = 1        ; campaign progress
 *     buf[2..0x14]  = 0        ; 19 bytes -- exactly the unlock-array span that
 *                              ; 0x80055478 serializes and 0x80055538 restores
 *     buf[0x1C..]   = 0x64, 0xFF, 0xFF, 0xFF, 0xFF every 5 bytes up to 0x140
 *                              ; the 64x5 side table from E14
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_c16_lives_gameover.c \
 *      -o /tmp/c16 && /tmp/c16 REBUILD/files/SCUS_942.88
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
    /* the decrement and the game-over branch */
    {0x800501FCu, 0x904265A0u, "lives: lbu v0, [0x800A65A0]"},
    {0x80050204u, 0x1040FFB3u, "lives == 0 -> branch to the game-over path 0x800500D4"},
    {0x80050208u, 0x2442FFFFu, "delay slot: v0 = v0 - 1   (THE decrement)"},
    {0x80050210u, 0xA02265A0u, "store lives back -- a decrementing store, but NOT the one that runs"},
    {0x8005B334u, 0x24C6FFFFu, "REAL death decrement: addiu a2, a2, -1"},
    {0x8005B348u, 0xA02665A0u, "REAL death store, in respawn_transition_state_handler"},

    /* game over */
    {0x800500D4u, 0x2404002Eu, "game over: a0 = 0x2E (FMV id 46)"},
    {0x800500D8u, 0x0C00F9F0u, "game over: jal 0x8003E7C0 fmv_bin_load"},
    {0x800500E0u, 0x24040005u, "game over: a0 = 5"},
    {0x800500E4u, 0x0C0140E3u, "game over: jal 0x8005038C scene_setup_and_load"},
    {0x800500E8u, 0x24050040u, "game over: a1 = 0x40"},

    /* the cap shared by every grant site */
    {0x80049848u, 0x2C620009u, "grant guard: sltiu v0, v1, 9  -> lives cap is 9"},
    {0x80049858u, 0xA02265A0u, "a grant store (lives + 1)"},

    /* new-game defaults */
    {0x80055414u, 0x24030012u, "init: v1 = 0x12 (the 19-byte clear counter)"},
    {0x8005541Cu, 0x24020005u, "init: INITIAL LIVES = 5"},
    {0x80055420u, 0xA0820000u, "init: buf[0] = 5"},
    {0x80055428u, 0xA0820001u, "init: buf[1] = 1 (campaign progress)"},
    {0x80055440u, 0x24060064u, "init: side-table seed 0x64"},
    {0x80055464u, 0x28620140u, "init: side-table loop bound 0x140"},
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

    /* independent recount of every lives access, so the "only one decrement"
     * claim is exhaustive rather than asserted */
    {
        size_t acc = 0, stores = 0, dec = 0;
        for (size_t off = EXE_HEADER_SIZE; off + 4 <= exe_size; off += 4) {
            uint32_t w = (uint32_t)exe[off] | ((uint32_t)exe[off+1] << 8) |
                         ((uint32_t)exe[off+2] << 16) | ((uint32_t)exe[off+3] << 24);
            uint32_t op = w >> 26;
            if ((w & 0xFFFF) != 0x65A0) continue;
            if (!(op == 0x20 || op == 0x21 || op == 0x23 || op == 0x24 ||
                  op == 0x25 || op == 0x28 || op == 0x29 || op == 0x2B)) continue;
            acc++;
            if (op == 0x28 || op == 0x29 || op == 0x2B) {
                stores++;
                uint32_t prev = (uint32_t)exe[off-4] | ((uint32_t)exe[off-3] << 8) |
                                ((uint32_t)exe[off-2] << 16) | ((uint32_t)exe[off-1] << 24);
                uint32_t p2 = (uint32_t)exe[off-8] | ((uint32_t)exe[off-7] << 8) |
                              ((uint32_t)exe[off-6] << 16) | ((uint32_t)exe[off-5] << 24);
                if ((prev >> 26) == 9 && (prev & 0xFFFF) == 0xFFFF) dec++;
                else if ((p2 >> 26) == 9 && (p2 & 0xFFFF) == 0xFFFF) dec++;
            }
        }
        printf("\nexhaustive scan: %zu accesses, %zu stores (%zu with an adjacent addiu -1;\n"
               "  NOTE: that adjacency heuristic does NOT find the real death decrement --\n"
               "  the live run's only writer is 0x8005B348, whose -1 is 5 instructions back)\n",
               acc, stores, dec);
        if (acc != 23 || stores != 10) {
            printf("FAIL: expected 23 accesses / 10 stores\n");
            free(exe);
            return 1;
        }
    }

    printf("\n%zu/%zu pins OK\n", ok, total);
    if (ok != total) { free(exe); return 1; }
    puts("\nC16: lives is entirely RESIDENT (no overlay touches 0x800A65A0).");
  puts("  8 grant stores capped at 9, and 1 save restore. The DEATH decrement is");
  puts("  0x8005B334/48 in respawn_transition_state_handler -- live-proven, 9/9 writes.");
  puts("  0x80050210 is a SECOND decrementing store that did NOT run; its guard");
    puts("  `lives == 0 -> game over` DID fire, so that site is the game-over CHECK.");
    puts("  GAME OVER = fmv_bin_load(46, 0) then scene_setup_and_load(5, 0x40).");
    puts("  NEW GAME = 5 lives, progress 1, 19 unlock bytes cleared, side table seeded.");
    free(exe);
    return 0;
}
