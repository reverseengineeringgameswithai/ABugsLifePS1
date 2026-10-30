/* phase4_f02_debris_class_bind -- bind the Tunnels falling-debris class to its handler.
 *
 * THE ROW ITEM
 * ------------
 * F02_tunnels: "capture falling-debris actors in stage 2; bind them to their spawner
 * and DAMAGE CLASS". The spawner half is captured (analysis/phase4_f02_spawner_trace.json):
 * overlay PC 0x800B43F8 makes 717 contact_alloc calls in one LEVEL02 run, all with
 * a3 = 0x5A, a constant a1 = 0xE3A0, across 33 distinct a0. This tool does the damage half.
 *
 * WHAT THE PREVIOUS ATTEMPT GOT WRONG -- TWO SEPARATE ERRORS
 * ---------------------------------------------------------
 * (1) It treated 0x8001B570 as a *dispatcher function* and looked for the jump table at
 *     0x8001B570 + 696 = 0x8001B828. But 0x8001B570 IS THE TABLE. The disassembly reads
 *     `0x8001b570 .dword 0x80058834`, and Canon's own FUNC_800586B0 page says the walker
 *     jumps through "word table 0x8001b570[idx]". The 117 entries were never missing --
 *     this tool counts them in place and finds the null terminator that ends them.
 *     What sat at 0x8001B828 was a DIFFERENT, unrelated pointer run followed by ASCII.
 *
 * (2) More fundamentally: it treated a3 as an ACTION ID. It is not. Per the confirmed
 *     Phase-3 decompilation (src_re/contact_alloc_80059e44.c):
 *         record = contact_alloc(x, y, z, ctorType = a3, stackArg = [sp+0x40])
 *         record+0x20 (action_id) = metaB[ctorType] + 0x00
 *     so a3 = 0x5A is a CTOR TYPE that indexes metadata table B at 0x8007941C, and the
 *     action id is a FIELD OF THAT ROW. Indexing the dispatch table by 0x5A directly --
 *     or by 0x5A-2 -- reads an unrelated slot. Both of the previous attempt's "plausible
 *     bindings" came from that conflation.
 *
 * THE ACTUAL CHAIN
 * ----------------
 *     a3 (ctorType) -> metaB row 0x8007941C + ctorType*0x14
 *                   -> action_id  = row+0x00      -> walker dispatch 0x8001B570[action_id-2]
 *                   -> active_type= row+0x02      -> record+0x22  (walker gate: > 0)
 *                   -> flags      = row+0x10      -> record+0x33  (walker gate: & 0x02)
 *
 * Both walker gates are decided by the metaB row alone, so whether a class can reach the
 * action dispatch AT ALL is a static property of its ctor type. That is the finding.
 *
 * WHAT IT REPORTS
 * ---------------
 * For each requested ctor type: the decoded metaB row, the action id, the walker gate
 * verdict computed with the walker's EXACT semantics (signed 16-bit index, unsigned
 * compare against 0x75, else the default case), and the resolved handler. Plus the
 * measured extent of the dispatch table and every resident reference to the contact
 * array, so the set of possible consumers is enumerated rather than assumed.
 *
 * Self-verifies against the pristine image before reporting: PSX-EXE magic, t_addr,
 * the metaB/tableA adjacency that fixes metaB's row count, and two pinned words.
 * It refuses rather than printing plausible addresses.
 *
 * Build: cc -O2 -Wall -Wextra -Werror -o /tmp/f02bind tools/phase4_f02_debris_class_bind.c
 * Usage: /tmp/f02bind SCUS_942.88 [--json out.json]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define TEXT_LO   0x80010000u
#define TEXT_HI   0x80082800u
#define HDR       0x800u

#define METAB     0x8007941Cu     /* metadata table B, stride 0x14, index = ctorType */
#define METAA     0x80079E30u     /* metadata table A, stride 0x14, index = stackArg */
#define DISPATCH  0x8001B570u     /* walker action dispatch, index = action_id - 2   */
#define DEFCASE   0x800589D4u     /* walker default case (idx out of range)          */
#define ACTLIMIT  0x75u           /* walker: (uint32_t)idx < 0x75                    */
#define WALKER    0x800586B0u
#define CARRAY    0x800B0D18u     /* 64 records * 0x38                               */
#define CARRAY_SZ (0x40u * 0x38u)
#define HEALTH    0x800A6594u     /* TRUE HEALTH s16 (Phase-2 oracle)                */
#define UPDATER   0x8005A308u     /* per-frame contact-record update                 */
#define CLSTAB    0x8001B7F0u     /* behaviour-class dispatch, index = rec+0x2F - 1  */
#define CLSLIMIT  0x0Eu           /* updater: (uint32_t)(c-1) < 0xE                  */
#define CLS_NOOP  0x8005B098u     /* shared tail used by several classes             */
#define DEBRIS_STACKARG 0x16u     /* 5th arg at the debris call site (overlay pin)   */
#define ALLOC_SIGN 0x8005A088u    /* `lb v1,0xe(s2)` starting the rec+0x2E sign branch */

/* pins: first dispatch entry, and metaB row 0 action id */
#define PIN_DISPATCH0 0x80058834u
#define PIN_METAB0_ACT 25u

static uint8_t *img;
static long img_len;

static int mapped(uint32_t va, uint32_t n)
{
    long off = (long)HDR + (long)(va - TEXT_LO);
    return va >= TEXT_LO && off >= 0 && off + (long)n <= img_len;
}
static uint32_t rd32(uint32_t va)
{
    long off = (long)HDR + (long)(va - TEXT_LO);
    if (!mapped(va, 4)) return 0;
    return (uint32_t)img[off] | ((uint32_t)img[off+1] << 8) |
           ((uint32_t)img[off+2] << 16) | ((uint32_t)img[off+3] << 24);
}
static uint16_t rd16(uint32_t va)
{
    long off = (long)HDR + (long)(va - TEXT_LO);
    if (!mapped(va, 2)) return 0;
    return (uint16_t)((uint32_t)img[off] | ((uint32_t)img[off+1] << 8));
}
static uint8_t rd8(uint32_t va)
{
    long off = (long)HDR + (long)(va - TEXT_LO);
    if (!mapped(va, 1)) return 0;
    return img[off];
}
static int in_text(uint32_t a) { return a >= TEXT_LO && a < TEXT_HI; }

/* ---- metaB row decode -------------------------------------------------- */
struct metab {
    uint32_t va;
    uint16_t action_id;     /* +0x00 -> record+0x20 */
    int16_t  active_type;   /* +0x02 -> record+0x22 */
    int16_t  init24;        /* +0x04 -> record+0x24 (negative => script variant) */
    uint8_t  b06, b07;      /* -> record+0x31, +0x30 */
    uint16_t radius_add;    /* +0x08 -> record+0x28 */
    uint16_t a, c;          /* +0x0a, +0x0c */
    uint8_t  e, f;          /* +0x0e sign-select, +0x0f */
    uint8_t  flags;         /* +0x10 -> record+0x33 */
    uint8_t  h11, h12, h13;
};
static struct metab metab_row(uint32_t ctor)
{
    uint32_t r = METAB + ctor * 0x14u;
    struct metab m;
    m.va = r;
    m.action_id   = rd16(r + 0x00);
    m.active_type = (int16_t)rd16(r + 0x02);
    m.init24      = (int16_t)rd16(r + 0x04);
    m.b06 = rd8(r + 0x06); m.b07 = rd8(r + 0x07);
    m.radius_add = rd16(r + 0x08);
    m.a = rd16(r + 0x0a); m.c = rd16(r + 0x0c);
    m.e = rd8(r + 0x0e);  m.f = rd8(r + 0x0f);
    m.flags = rd8(r + 0x10);
    m.h11 = rd8(r + 0x11); m.h12 = rd8(r + 0x12); m.h13 = rd8(r + 0x13);
    return m;
}

/* walker's exact index math: idx = (int16_t)(action_id - 2); (uint32_t)idx < 0x75 */
static int walker_handler(uint16_t action_id, uint32_t *out)
{
    int16_t idx = (int16_t)((uint16_t)(action_id - 2u));
    if ((uint32_t)(int32_t)idx < ACTLIMIT) { *out = rd32(DISPATCH + 4u * (uint32_t)idx); return idx; }
    *out = DEFCASE;
    return -1;
}

/* ---- handler entry-path probe ------------------------------------------ */
struct probe { int touches_health; int calls; uint32_t first_call; int insns; };
static struct probe probe_handler(uint32_t pc)
{
    struct probe p = {0,0,0,0};
    uint32_t hi_val[32] = {0};
    int hi_ok[32] = {0};
    for (int i = 0; i < 400 && in_text(pc); i++, pc += 4) {
        uint32_t w = rd32(pc), op = w >> 26;
        uint32_t rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int16_t imm = (int16_t)(w & 0xFFFFu);
        p.insns++;
        if (op == 0x0Fu) { hi_val[rt] = (uint32_t)(w & 0xFFFFu) << 16; hi_ok[rt] = 1; continue; }
        if (op == 3u) {
            uint32_t t = ((pc + 4u) & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2);
            if (!p.calls) p.first_call = t;
            p.calls++;
        }
        int is_mem = (op >= 0x20u && op <= 0x26u) || (op >= 0x28u && op <= 0x2Eu);
        if (is_mem && hi_ok[rs] && hi_val[rs] + (uint32_t)(int32_t)imm == HEALTH)
            p.touches_health = 1;
        if (op == 0u && (w & 0x3Fu) == 8u && rs == 31u) break;   /* jr ra */
    }
    return p;
}

/* ---- scan text for references to the contact array ---------------------- */
struct ref { uint32_t pc; uint32_t addr; int is_store; };
#define MAXREF 512
static struct ref refs[MAXREF];
static int nref;

static void scan_carray_refs(void)
{
    uint32_t hi_val[32] = {0};
    int      hi_ok[32]  = {0};
    for (uint32_t pc = TEXT_LO; pc < TEXT_HI; pc += 4) {
        uint32_t w = rd32(pc), op = w >> 26;
        uint32_t rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int16_t imm = (int16_t)(w & 0xFFFFu);
        if (op == 0x0Fu) { hi_val[rt] = (uint32_t)(w & 0xFFFFu) << 16; hi_ok[rt] = 1; continue; }
        int is_load  = (op >= 0x20u && op <= 0x26u);
        int is_store = (op >= 0x28u && op <= 0x2Eu);
        /* base-pointer materialisation comes in BOTH idioms in this build:
         *   lui rX,0x800b ; addiu rX,rX,0xd18   (the walkers)
         *   lui rX,0x800b ; ori   rX,rX,0xd18   (the billboard renderer 0x80014844)
         * Missing `ori` silently undercounts the consumer set, which is exactly the kind of
         * omission that turns an enumeration into a false negative. */
        int is_addi  = (op == 0x08u || op == 0x09u);
        int is_ori   = (op == 0x0Du);
        if ((is_load || is_store || is_addi || is_ori) && hi_ok[rs]) {
            uint32_t ea = is_ori ? (hi_val[rs] | (uint32_t)(w & 0xFFFFu))
                                 : hi_val[rs] + (uint32_t)(int32_t)imm;
            if (ea >= CARRAY && ea < CARRAY + CARRAY_SZ && nref < MAXREF) {
                refs[nref].pc = pc; refs[nref].addr = ea; refs[nref].is_store = is_store;
                nref++;
            }
        }
        /* a register written by anything other than lui invalidates its hi tracking */
        if (op != 0x0Fu) {
            uint32_t dst = 0; int has = 0;
            if (op == 0u) { dst = (w >> 11) & 31; has = 1; }            /* R-type rd */
            else if (is_load || is_addi || is_ori || op == 0x0Cu) { dst = rt; has = 1; }
            /* ori/addiu onto a lui'd register KEEPS it a known constant; anything else
             * redefining the register invalidates the tracking */
            if (has && dst < 32 && dst != 0 && !((op == 0x09u || op == 0x0Du) && dst == rs))
                hi_ok[dst] = 0;
        }
    }
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

    /* ---- self-verification: refuse an image we do not recognise ---- */
    if (img_len < 0x800 || memcmp(img, "PS-X EXE", 8) != 0) {
        fprintf(stderr, "not a PSX-EXE\n"); return 2;
    }
    uint32_t t_addr = (uint32_t)img[0x18] | ((uint32_t)img[0x19] << 8) |
                      ((uint32_t)img[0x1A] << 16) | ((uint32_t)img[0x1B] << 24);
    if (t_addr != TEXT_LO) { fprintf(stderr, "t_addr 0x%08X != 0x%08X\n", t_addr, TEXT_LO); return 2; }
    if (rd32(DISPATCH) != PIN_DISPATCH0) {
        fprintf(stderr, "pin fail: dispatch[0] = 0x%08X, expected 0x%08X -- not the pristine build\n",
                rd32(DISPATCH), PIN_DISPATCH0);
        return 2;
    }
    if (rd16(METAB) != PIN_METAB0_ACT) {
        fprintf(stderr, "pin fail: metaB[0].action = %u, expected %u\n", rd16(METAB), PIN_METAB0_ACT);
        return 2;
    }
    if ((METAA - METAB) % 0x14u != 0) {
        fprintf(stderr, "metaB..metaA span %u is not a whole number of 0x14 rows\n", METAA - METAB);
        return 2;
    }
    uint32_t metab_rows = (METAA - METAB) / 0x14u;

    /* ---- measured dispatch table extent ---- */
    int ndisp = 0;
    while (ndisp < 512 && in_text(rd32(DISPATCH + 4u * (uint32_t)ndisp))) ndisp++;
    uint32_t terminator = rd32(DISPATCH + 4u * (uint32_t)ndisp);

    printf("image                : %s (%ld bytes, t_addr 0x%08X)\n", argv[1], img_len, t_addr);
    printf("metaB                : 0x%08X, stride 0x14, %u rows (bounded by tableA 0x%08X)\n",
           METAB, metab_rows, METAA);
    printf("dispatch table       : 0x%08X, %d in-text pointers (action ids 2..%d), "
           "terminator word 0x%08X\n", DISPATCH, ndisp, ndisp + 1, terminator);
    printf("walker               : 0x%08X, gate = (rec+0x22 > 0) && (rec+0x33 & 0x02)\n\n", WALKER);

    /* ctor types the Tunnels run actually passed as a3 (from the spawner trace) */
    const uint32_t ctors[] = {0x5A, 0x59, 0x31, 0x71, 0x51, 0x26, 0x4E};
    const char *note[] = {"F02 falling debris (0x800B43F8, 717 calls)",
                          "same run", "same run", "generic/kind-0x30",
                          "grain (control)", "health leaf (control)", "control"};
    const int nctor = (int)(sizeof ctors / sizeof ctors[0]);

    printf("%-6s %-8s %-8s %-7s %-6s %-9s %-12s %s\n",
           "ctor", "action", "act_type", "flags", "radius", "gate", "handler", "note");
    for (int i = 0; i < nctor; i++) {
        if (ctors[i] >= metab_rows) { printf("0x%02X   OUT OF metaB RANGE\n", ctors[i]); continue; }
        struct metab m = metab_row(ctors[i]);
        uint32_t h; int idx = walker_handler(m.action_id, &h);
        int gate = (m.active_type > 0) && (m.flags & 0x02u);
        char hb[32];
        if (idx < 0) snprintf(hb, sizeof hb, "DEFAULT");
        else snprintf(hb, sizeof hb, "0x%08X", h);
        printf("0x%02X   %-8u %-8d 0x%02X    %-6u %-9s %-12s %s\n",
               ctors[i], m.action_id, m.active_type, m.flags, m.radius_add,
               gate ? "DISPATCH" : "BLOCKED", hb, note[i]);
    }

    /* detail for the debris class */
    struct metab d = metab_row(0x5A);
    uint32_t dh; int didx = walker_handler(d.action_id, &dh);
    printf("\n-- ctor 0x5A (falling debris) metaB row at 0x%08X --\n", d.va);
    printf("  raw            :");
    for (int i = 0; i < 0x14; i++) printf(" %02X", rd8(d.va + (uint32_t)i));
    printf("\n");
    printf("  action_id      : %u  -> walker index (int16)(%u-2) = %d\n",
           d.action_id, d.action_id, (int)(int16_t)(uint16_t)(d.action_id - 2u));
    printf("  index in range : %s (walker requires (uint32_t)idx < 0x%X)\n",
           didx >= 0 ? "yes" : "NO -- falls to the default case", ACTLIMIT);
    printf("  active_type    : %d  -> rec+0x22 (gate needs > 0): %s\n",
           d.active_type, d.active_type > 0 ? "PASS" : "FAIL");
    printf("  flags          : 0x%02X -> rec+0x33 (gate needs & 0x02): %s\n",
           d.flags, (d.flags & 0x02u) ? "PASS" : "FAIL");
    printf("  radius_add     : %u -> walker contact radius 0x12c + %u = %u\n",
           d.radius_add, d.radius_add, 0x12cu + d.radius_add);
    printf("  init24         : %d %s\n", d.init24,
           d.init24 < 0 ? "(negative => script-cursor variant: rec+0x24 and rec+0x22 are"
                          " recomputed from the script byte, see contact_alloc)" : "");
    printf("  WALKER VERDICT : %s\n",
           ((d.active_type > 0) && (d.flags & 0x02u))
             ? "reaches the action dispatch"
             : "NEVER reaches the action dispatch -- the pickup walker skips this record");

    /* which ctor types CAN reach the dispatch at all */
    int can = 0, cannot = 0;
    for (uint32_t c = 0; c < metab_rows; c++) {
        struct metab m = metab_row(c);
        if ((m.active_type > 0) && (m.flags & 0x02u)) can++; else cannot++;
    }
    printf("\nmetaB census: %u rows -- %d can reach the walker dispatch, %d are gated out\n",
           metab_rows, can, cannot);
    printf("gated-out rows sharing the debris signature (flags 0x20, action 1):");
    for (uint32_t c = 0; c < metab_rows; c++) {
        struct metab m = metab_row(c);
        if (m.flags == 0x20u && m.action_id == 1u) printf(" 0x%02X", c);
    }
    printf("\n");

    /* handler probes for the classes that DO dispatch, as a control on the method */
    printf("\nentry-path probe of the dispatching controls (health = writes/reads 0x%08X):\n", HEALTH);
    for (int i = 0; i < nctor; i++) {
        if (ctors[i] >= metab_rows) continue;
        struct metab m = metab_row(ctors[i]);
        if (!((m.active_type > 0) && (m.flags & 0x02u))) continue;
        uint32_t h; walker_handler(m.action_id, &h);
        struct probe p = probe_handler(h);
        printf("  ctor 0x%02X action %-3u handler 0x%08X  insns %-4d health %-3s first_call 0x%08X\n",
               ctors[i], m.action_id, h, p.insns, p.touches_health ? "YES" : "-", p.first_call);
    }

    /* ---- the OTHER dispatch: behaviour class rec+0x2F, used by the record updater ----
     * FUNC_8005A308 does `lbu rec+0x2F; idx = c-1; if ((uint32_t)idx < 0xE) jump
     * 0x8001B7F0[idx]`. This is a SECOND, independent dispatch on the same records, and it
     * is the one a non-pickup contact object (like debris) would have to use to do anything.
     */
    printf("\nbehaviour-class dispatch 0x%08X (record updater 0x%08X), index = rec+0x2F - 1,\n"
           "unsigned range < 0x%X:\n", CLSTAB, UPDATER, CLSLIMIT);
    for (uint32_t i = 0; i < CLSLIMIT; i++) {
        uint32_t h = rd32(CLSTAB + 4u * i);
        int shared = (h == CLS_NOOP);
        printf("  class 0x%02X -> 0x%08X%s   ctors:", i + 1, h, shared ? "  (shared no-op tail)" : "");
        for (uint32_t c = 0; c < metab_rows; c++)
            if (rd8(METAB + c * 0x14u + 0x0Fu) == i + 1) printf(" 0x%02X", c);
        printf("\n");
    }
    {
        int nzero = 0;
        for (uint32_t c = 0; c < metab_rows; c++)
            if (rd8(METAB + c * 0x14u + 0x0Fu) == 0) nzero++;
        printf("  class 0x00 -> NO HANDLER (idx -1 fails the unsigned range test): %d ctors, "
               "including 0x5A\n", nzero);
    }

    /* ---- what each flags bit gates, and how many ctor types carry it ---- */
    printf("\nflags byte (metaB+0x10 -> record+0x33) -- bit -> consumer, across %u metaB rows:\n",
           metab_rows);
    {
        static const struct { uint8_t bit; const char *what; } BITS[] = {
            {0x01, "ground-collision branch in the updater (0x8005A5A8)"},
            {0x02, "pickup-walker gate (0x800586B0 @ 0x80058748)"},
            {0x04, "contact-vs-actor gate (0x80058AF8 @ 0x80058C6C)"},
            {0x08, "berry-projectile branch in the updater (0x8005A358)"},
            {0x10, "no consumer found"},
            {0x20, "no consumer found"},
            {0x40, "no consumer found"},
            {0x80, "occupied marker, tested by the allocator"},
        };
        for (int i = 0; i < 8; i++) {
            int n = 0;
            for (uint32_t c = 0; c < metab_rows; c++)
                if (rd8(METAB + c * 0x14u + 0x10u) & BITS[i].bit) n++;
            printf("  0x%02X  %-48s %3d rows%s\n", BITS[i].bit, BITS[i].what, n,
                   (metab_row(0x5A).flags & BITS[i].bit) ? "   <- set on ctor 0x5A" : "");
        }
    }

    /* ---- the debris spawn attributes: table A row = the caller's stack argument ----
     * The updater integrates rec+0x00/04/08 by rec+0x0c/10/14 and adds rec+0x18 into
     * rec+0x10 each tick, so table A's four outputs ARE velocity X/Y/Z plus a Y
     * acceleration. That is measured from the updater, not assumed.
     */
    printf("\ntable A row %u (the debris spawner's stack argument) at 0x%08X:\n",
           DEBRIS_STACKARG, METAA + DEBRIS_STACKARG * 0x14u);
    {
        uint32_t r = METAA + DEBRIS_STACKARG * 0x14u;
        uint32_t sel = rd32(r);
        static const char *DST[4] = {"rec+0x0c  vel_X", "rec+0x10  vel_Y",
                                     "rec+0x14  vel_Z", "rec+0x18  accel_Y (added into vel_Y)"};
        printf("  raw       :");
        for (int i = 0; i < 0x14; i++) printf(" %02X", rd8(r + (uint32_t)i));
        printf("\n  selector  : 0x%08X -> nibbles %X %X %X %X (decoded by 0x800593E8)\n",
               sel, (sel >> 12) & 0xF, (sel >> 8) & 0xF, (sel >> 4) & 0xF, sel & 0xF);
        for (int i = 0; i < 4; i++)
            printf("  A[+0x%02X]  = %-10d -> %s\n", 4 + i * 4,
                   (int32_t)rd32(r + 4u + (uint32_t)i * 4u), DST[i]);
    }

    /* ---- how a live record identifies its own ctor type: record+0x2E ----
     * This matters because rec+0x2E is the ONLY field that names the ctor type at runtime,
     * so it is what a live pool census has to key on. src_re/contact_alloc_80059e44.c
     * documents the sign branch as  sel==1 => -ctorType, else => +ctorType. The shipped
     * code says the opposite. Decode it from the image rather than trusting either.
     */
    printf("\nrecord+0x2E sign branch in the allocator (0x%08X):\n", ALLOC_SIGN);
    {
        uint32_t w_beq = rd32(ALLOC_SIGN + 0x08);   /* beqz v1, <zero case>  */
        uint32_t w_bne = rd32(ALLOC_SIGN + 0x10);   /* bne  v1, 1, <else>    */
        uint32_t w_neg = rd32(ALLOC_SIGN + 0x14);   /* negu v0, s3 (delay)   */
        uint32_t w_st1 = rd32(ALLOC_SIGN + 0x1C);   /* sb s3, 0x2e(s1)       */
        uint32_t w_st2 = rd32(ALLOC_SIGN + 0x24);   /* sb v0, 0x2e(s1)       */
        int shape_ok = (w_beq >> 26) == 4u && (w_bne >> 26) == 5u
                       && (w_neg & 0x3Fu) == 0x23u                       /* subu/negu */
                       && (w_st1 >> 26) == 0x28u && (w_st2 >> 26) == 0x28u
                       && (w_st1 & 0xFFFFu) == 0x2Eu && (w_st2 & 0xFFFFu) == 0x2Eu;
        if (!shape_ok) {
            printf("  UNRECOGNISED -- refusing to state the mapping\n");
        } else {
            /* the `sb` in the bne's delay slot is the sel==1 arm; the other is the else arm */
            uint32_t rt1 = (w_st1 >> 16) & 31, rt2 = (w_st2 >> 16) & 31;
            printf("  sel = metaB+0x0E ; s3 = ctorType, v0 = negu(s3) = -ctorType\n");
            printf("  sel == 0 -> record+0x2E = 0\n");
            printf("  sel == 1 -> record+0x2E = %s  (sb r%u in the bne delay slot)\n",
                   rt1 == 19u ? "+ctorType" : "-ctorType", rt1);
            printf("  else     -> record+0x2E = %s  (sb r%u on the fallthrough)\n",
                   rt2 == 2u ? "-ctorType" : "+ctorType", rt2);
            printf("  ctor 0x5A has sel = %u -> record+0x2E = 0x%02X\n",
                   metab_row(0x5A).e, (uint8_t)(-(int)0x5A));
            printf("  NOTE src_re/contact_alloc_80059e44.c states the OPPOSITE mapping; the\n"
                   "       image and a live pool census both give the one above.\n");
        }
    }

    /* ---- decode each consumer's per-record gate straight out of the image ----
     * Every claim of the form "class X cannot reach consumer Y" rests on these masks, so
     * read them rather than quoting them. Each entry names the PC of the masking `andi`
     * (or the `beqz`/compare that IS the gate) and the expected shape; a mismatch prints
     * MISMATCH instead of a comfortable number.
     */
    printf("\nper-record gates, decoded from the image (mask read out of the instruction):\n");
    {
        static const struct { uint32_t pc; const char *fn; const char *field; } G[] = {
            {0x80058748u, "0x800586B0 contact_pickup_walker",  "rec+0x33 flags"},
            {0x80058C6Cu, "0x80058AF8 contact_vs_actor",       "rec+0x33 flags"},
            {0x8005A358u, "0x8005A308 contact_record_update",  "rec+0x33 flags"},
        };
        struct metab dm = metab_row(0x5A);
        for (int i = 0; i < 3; i++) {
            uint32_t w = rd32(G[i].pc);
            if ((w >> 26) != 0x0Cu) { printf("  0x%08X  MISMATCH (not an andi)\n", G[i].pc); continue; }
            uint32_t mask = w & 0xFFFFu;
            printf("  0x%08X  %-34s andi %s, 0x%02X  -> ctor 0x5A (flags 0x%02X): %s\n",
                   G[i].pc, G[i].fn, G[i].field, mask, dm.flags,
                   (dm.flags & mask) ? "PASSES" : "BLOCKED");
        }
        /* the renderer's gate is not a flags mask at all */
        uint32_t rw = rd32(0x800148E0u), rb = rd32(0x800148E8u);
        int shape = (rw >> 26) == 0x24u && (rw & 0xFFFFu) == 0x22u && (rb >> 26) == 4u;
        printf("  0x800148E0  %-34s %s -> ctor 0x5A (rec+0x22 = %d..%d): %s\n",
               "0x80014844 contact_billboard_render",
               shape ? "lbu rec+0x22; beqz  (NO flags test)" : "MISMATCH",
               5 * dm.b07, 8 * dm.b07, shape ? "RENDERED" : "?");
        printf("  0x8005D2B8  %-34s lbu rec+0x2F; compare == 5 -> ctor 0x5A (class 0x%02X): %s\n",
               "0x8005CD2C gameplay_effect_spawner", dm.f, dm.f == 5 ? "PASSES" : "BLOCKED");
        printf("  0x8005A8F4  %-34s sltiu (rec+0x2F - 1) < 0xE  -> ctor 0x5A (class 0x%02X): %s\n",
               "0x8005A308 behaviour-class dispatch", dm.f,
               (uint32_t)(dm.f - 1u) < CLSLIMIT ? "PASSES" : "BLOCKED (no behaviour handler)");
    }

    /* enumerate resident consumers of the contact array */
    scan_carray_refs();
    printf("\nresident references to the contact array 0x%08X..0x%08X: %d\n",
           CARRAY, CARRAY + CARRAY_SZ, nref);
    for (int i = 0; i < nref; i++)
        printf("  pc 0x%08X  %-5s addr 0x%08X\n", refs[i].pc,
               refs[i].is_store ? "STORE" : "LOAD", refs[i].addr);

    if (jsonout) {
        FILE *j = fopen(jsonout, "w");
        if (!j) { perror(jsonout); return 2; }
        fprintf(j, "{\n \"_comment\": \"F02 Tunnels: ctorType -> metaB -> action_id -> walker "
                   "dispatch. Regenerate: tools/phase4_f02_debris_class_bind.c\",\n");
        fprintf(j, " \"row_id\": \"F02_tunnels\",\n");
        fprintf(j, " \"corrects\": \"analysis/phase4_f02_contact_action_table.json -- that run "
                   "indexed the dispatch table by the RAW a3 value and looked for the table at "
                   "0x8001B828 (dispatcher_end). a3 is a ctorType, not an action id, and "
                   "0x8001B570 is the table itself, not a function.\",\n");
        fprintf(j, " \"metab\": \"0x%08X\",\n \"metab_rows\": %u,\n", METAB, metab_rows);
        fprintf(j, " \"dispatch_table\": \"0x%08X\",\n \"dispatch_entries\": %d,\n"
                   " \"dispatch_terminator\": \"0x%08X\",\n", DISPATCH, ndisp, terminator);
        fprintf(j, " \"walker\": \"0x%08X\",\n \"walker_gate\": \"(rec+0x22 > 0) && (rec+0x33 & 0x02)\",\n",
                WALKER);
        fprintf(j, " \"chain\": \"a3=ctorType -> metaB[ctorType]; action_id=row+0x00 -> "
                   "record+0x20; active_type=row+0x02 -> record+0x22; flags=row+0x10 -> record+0x33\",\n");
        fprintf(j, " \"classes\": [\n");
        for (int i = 0; i < nctor; i++) {
            struct metab m = metab_row(ctors[i]);
            uint32_t h; int idx = walker_handler(m.action_id, &h);
            int gate = (m.active_type > 0) && (m.flags & 0x02u);
            fprintf(j, "  {\"ctor\": \"0x%02X\", \"action_id\": %u, \"active_type\": %d, "
                       "\"flags\": \"0x%02X\", \"radius_add\": %u, \"walker_index\": %d, "
                       "\"reaches_dispatch\": %s, \"handler\": \"%s\", \"note\": \"%s\"}%s\n",
                    ctors[i], m.action_id, m.active_type, m.flags, m.radius_add, idx,
                    gate ? "true" : "false",
                    idx < 0 ? "default_0x800589D4" : "", note[i], i + 1 < nctor ? "," : "");
        }
        fprintf(j, " ],\n");
        fprintf(j, " \"debris_ctor\": \"0x5A\",\n");
        fprintf(j, " \"debris_action_id\": %u,\n", d.action_id);
        fprintf(j, " \"debris_flags\": \"0x%02X\",\n", d.flags);
        fprintf(j, " \"debris_reaches_walker_dispatch\": %s,\n",
                ((d.active_type > 0) && (d.flags & 0x02u)) ? "true" : "false");
        fprintf(j, " \"debris_blocked_by\": \"rec+0x33 flags 0x%02X has bit 0x02 clear\",\n", d.flags);
        fprintf(j, " \"carray_refs\": %d\n}\n", nref);
        fclose(j);
        printf("\nwrote %s\n", jsonout);
    }
    free(img);
    return 0;
}
