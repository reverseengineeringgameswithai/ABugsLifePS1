/* ==========================================================================
 * SUPERSEDED 2026-08-04 -- DO NOT USE. Both of this tool's premises are wrong:
 *   (1) 0x8001B570 is the TABLE, not a dispatcher function. This tool looked for
 *       the table at 0x8001B570 + 696 (the census function size) and found an
 *       unrelated pointer run followed by ASCII.
 *   (2) The `a3` the spawner passes is a ctorType, not an action id. The action id
 *       is metaB[ctorType]+0x00 (0x8007941C, stride 0x14). Indexing the dispatch
 *       table by a3-2 reads an unrelated slot.
 * Replaced by tools/phase4_f02_debris_class_bind.c. Kept for the audit trail.
 * ========================================================================== */
/* phase4_f02_contact_action_table -- bind a contact action class to its handler.
 *
 * THE ROW ITEM
 * ------------
 * F02_tunnels asks to "capture falling-debris actors in stage 2; bind them to
 * their spawner and DAMAGE CLASS". The spawner is captured
 * (analysis/phase4_f02_spawner_trace.json): overlay 0x800B43F8 releases 717
 * objects in one run, all with argument a3 = 0x5A, all at a constant height
 * a1 = 0xE3A0, across 33 horizontal positions. This resolves what class 0x5A
 * does, which is the damage half -- and it is pure static work.
 *
 * THE TABLE -- AND WHAT IT IS NOT
 * ------------------------------
 * Canon: "the action dispatcher at 0x8001B570 has 117 entries for action IDs
 * 2..118; 15 use specialized targets and the rest use the default path."
 *
 * I assumed the table began at the dispatcher's end (0x8001B828, since the census
 * lists the function as 696 bytes) and ran 117 entries. IT DOES NOT. Exactly 21
 * plausible handler pointers sit there -- action ids 2..22 -- and entry 21 is
 * ASCII: 0x72616863 "char", then "s3\flick", a file path. The table terminates in
 * string data.
 *
 * So this is a 21-entry dispatch, NOT the 117-entry one Canon describes, and the
 * debris class 0x5A (90) cannot be resolved through it. Where the 117-entry table
 * lives is unresolved.
 *
 * The 21 entries are still a real result: ids 2..22 with 0x8005CCE8 shared by ids
 * 12/17/18/20 -- and 0x8005CCE8 is the green-seed passive-collision handler, so
 * this table is a SEED/PLANT contact dispatch rather than the general one.
 *
 * It is also the table tools/repair_function_coverage.c had to REFUSE to walk as
 * code: its 51%-implausible "extension" of contact_action_dispatch was exactly
 * these pointers plus the strings behind them.
 *
 * WHAT IT REPORTS
 * ---------------
 * How many consecutive plausible handler pointers follow the dispatcher, the
 * handler for each class the Tunnels run actually used, and for each handler
 * whether its body touches the player's health halfword or reaches a known
 * damage entry -- which is what "damage class" means operationally.
 *
 * Self-verifies against the pristine image: t_addr plus two pinned words (the
 * first table entry, and the dispatcher's own first instruction). It refuses to
 * report a table it cannot recognise rather than printing plausible addresses.
 *
 * Build: cc -O2 -Wall -Wextra -Werror -o /tmp/f02t tools/phase4_f02_contact_action_table.c
 * Usage: /tmp/f02t SCUS_942.88 [--json out.json]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define TEXT_LO 0x80010000u
#define TEXT_HI 0x80082800u
#define HDR     0x800u
#define DISPATCH 0x8001B570u
#define TABLE    0x8001B828u          /* dispatcher end = 0x8001B570 + 696 */
#define HEALTH   0x800A6594u          /* TRUE HEALTH, s16 (Phase-2 oracle) */
#define MAXH     256

static uint8_t *img;
static long img_len;

static uint32_t rd32(uint32_t va)
{
    long off = (long)HDR + (long)(va - TEXT_LO);
    if (off < 0 || off + 4 > img_len) return 0;
    return (uint32_t)img[off] | ((uint32_t)img[off + 1] << 8) |
           ((uint32_t)img[off + 2] << 16) | ((uint32_t)img[off + 3] << 24);
}

static int in_text(uint32_t a) { return a >= TEXT_LO && a < TEXT_HI; }

/* Walk a handler's straight-line body far enough to see what it touches. Stops at
 * the first `jr ra`, so this characterises the entry path, not every branch. */
struct probe { int touches_health; int calls; uint32_t first_call; int insns; };

static struct probe probe_handler(uint32_t pc)
{
    struct probe p = {0, 0, 0, 0};
    uint32_t hi_val[32] = {0};
    int hi_ok[32] = {0};
    for (int i = 0; i < 400 && in_text(pc); i++, pc += 4) {
        uint32_t w = rd32(pc), op = w >> 26;
        uint32_t rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int16_t imm = (int16_t)(w & 0xFFFFu);
        p.insns++;
        if (op == 0x0Fu) { hi_val[rt] = (uint32_t)(w & 0xFFFFu) << 16; hi_ok[rt] = 1; continue; }
        if (op == 3u) {                                   /* jal */
            uint32_t t = ((pc + 4u) & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2);
            if (!p.calls) p.first_call = t;
            p.calls++;
        }
        /* any load/store whose lui-formed effective address is the health field */
        int is_mem = (op >= 0x20u && op <= 0x26u) || (op >= 0x28u && op <= 0x2Eu);
        if (is_mem && hi_ok[rs]) {
            uint32_t ea = hi_val[rs] + (uint32_t)(int32_t)imm;
            if (ea == HEALTH) p.touches_health = 1;
        }
        if (op == 0u && (w & 0x3Fu) == 8u && rs == 31u) break;   /* jr ra */
    }
    return p;
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s <exe> [--json out]\n", argv[0]); return 2; }
    const char *jsonout = NULL;
    for (int i = 2; i < argc; i++)
        if (!strcmp(argv[i], "--json") && i + 1 < argc) jsonout = argv[++i];

    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    fseek(f, 0, SEEK_END); img_len = ftell(f); fseek(f, 0, SEEK_SET);
    img = malloc((size_t)img_len);
    if (!img || fread(img, 1, (size_t)img_len, f) != (size_t)img_len) {
        fprintf(stderr, "read failed\n"); return 2;
    }
    fclose(f);
    if (img_len < 0x800 || memcmp(img, "PS-X EXE", 8) != 0) {
        fprintf(stderr, "not a PSX-EXE\n"); return 2;
    }
    uint32_t t_addr = (uint32_t)img[0x18] | ((uint32_t)img[0x19] << 8) |
                      ((uint32_t)img[0x1A] << 16) | ((uint32_t)img[0x1B] << 24);
    if (t_addr != TEXT_LO) { fprintf(stderr, "t_addr mismatch\n"); return 2; }
    if (!in_text(rd32(TABLE))) {
        fprintf(stderr, "no handler pointer at 0x%08X -- table not recognised\n", TABLE);
        return 2;
    }

    /* how many consecutive plausible handler pointers follow */
    uint32_t handlers[MAXH];
    int n = 0;
    for (; n < MAXH; n++) {
        uint32_t h = rd32(TABLE + 4u * (uint32_t)n);
        if (!in_text(h)) break;
        handlers[n] = h;
    }

    /* classes the Tunnels run actually passed as a3 */
    /* a3 values the Tunnels run passed. Index is id-2 per Canon; ids below 2 or
     * above 22 cannot be in this table at all. */
    const uint32_t used[] = {0x5A, 0x31, 0x71, 0x59, 0x0E, 0x15, 0x16, 0x17,
                             0x5D, 0x5E, 0x5F, 0x01, 0x00, 0x06};
    const int nused = (int)(sizeof used / sizeof used[0]);

    printf("dispatcher 0x%08X, table 0x%08X\n", DISPATCH, TABLE);
    printf("consecutive handler pointers: %d  (Canon describes 117 entries for ids "
           "2..118 -- so this is NOT that table)\n", n);
    printf("action ids covered: %d..%d ; entry %d is 0x%08X (ASCII, not a pointer)\n\n",
           2, n + 1, n, rd32(TABLE + 4u * (uint32_t)n));
    printf("%-8s %-12s %-6s %-8s %s\n", "class", "handler", "insns", "health?", "first call");
    for (int i = 0; i < nused; i++) {
        uint32_t k = used[i];
        int idx = (int)k - 2;                       /* Canon: ids start at 2 */
        if (idx < 0 || idx >= n) {
            printf("  0x%02X    NOT IN THIS TABLE (id %u, table covers 2..%d)\n",
                   k, k, n + 1);
            continue;
        }
        struct probe p = probe_handler(handlers[idx]);
        printf("  0x%02X    0x%08X   %-6d %-8s %s0x%08X\n", k, handlers[idx], p.insns,
               p.touches_health ? "YES" : "-", p.calls ? "" : "(none) ",
               p.calls ? p.first_call : 0);
    }

    if (jsonout) {
        FILE *j = fopen(jsonout, "w");
        if (!j) { perror(jsonout); return 2; }
        fprintf(j, "{\n \"_comment\": \"Contact action class -> handler, for the classes the "
                   "Tunnels run used. Regenerate: tools/phase4_f02_contact_action_table.c\",\n");
        fprintf(j, " \"row_id\": \"F02_tunnels\",\n");
        fprintf(j, " \"dispatcher\": \"0x%08X\",\n \"table\": \"0x%08X\",\n", DISPATCH, TABLE);
        fprintf(j, " \"consecutive_handler_pointers\": %d,\n", n);
        fprintf(j, " \"canon_action_count\": 117,\n");
        fprintf(j, " \"health_field\": \"0x%08X\",\n", HEALTH);
        fprintf(j, " \"probe_limits\": \"Each handler is walked straight-line to its first "
                   "`jr ra` (max 400 insns); branches are not followed, so 'health' is a "
                   "property of the ENTRY PATH, not a whole-handler proof.\",\n");
        fprintf(j, " \"classes\": [\n");
        for (int i = 0; i < nused; i++) {
            uint32_t k = used[i];
            int idx = (int)k - 2;
            int ok = idx >= 0 && idx < n;
            struct probe p = ok ? probe_handler(handlers[idx]) : (struct probe){0, 0, 0, 0};
            fprintf(j, "  {\"class\": \"0x%02X\", \"in_table\": %s", k, ok ? "true" : "false");
            if (ok)
                fprintf(j, ", \"handler\": \"0x%08X\", \"entry_insns\": %d, "
                           "\"entry_touches_health\": %s, \"first_call\": \"0x%08X\"",
                        handlers[idx], p.insns, p.touches_health ? "true" : "false",
                        p.calls ? p.first_call : 0);
            fprintf(j, "}%s\n", i + 1 < nused ? "," : "");
        }
        fprintf(j, " ],\n \"debris_class\": \"0x5A\",\n \"debris_class_resolved\": false,\n"
                   " \"why_not\": \"The table at 0x8001B828 holds 21 entries (action ids "
                   "2..22) and then ASCII string data. Class 0x5A is id 90, far outside it. "
                   "Canon's 117-entry table for ids 2..118 is elsewhere and is NOT located "
                   "here.\",\n");
        fprintf(j, " \"debris_spawner\": \"0x800B43F8 (Tunnels overlay), 717 calls, constant "
                   "a3=0x5A, constant height a1=0xE3A0, 33 X positions\"\n}\n");
        fclose(j);
        printf("\nwrote %s\n", jsonout);
    }
    free(img);
    return 0;
}
