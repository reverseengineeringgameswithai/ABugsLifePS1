/* Phase 4 D16_thumper / F03_council_chamber: what 0x80090BEE actually is.
 *
 * Both rows carried the binding "Thumper defeat -> 0x80090BEE = 2" and the shared
 * `next` "trace 0x80090BEE = 2 consumers into the level-exit transition".  That
 * premise is a CATEGORY ERROR, and this tool is the compiled re-derivation that
 * shows it.  Everything below is measured against the pristine SCUS_942.88 and all
 * 21 overlay blobs; nothing is inherited from the earlier disassembler-dump pass,
 * which got the access width, the overlay involvement and the semantics all wrong.
 *
 * WHAT 0x80090BEE IS
 * ------------------
 * It is the FLAGS halfword (+0x2E) of the shared CINEMATIC-CAMERA block at
 * 0x80090BC0 -- the same setpiece block C14 (telescope) and D17 (bird) already
 * reach through.  Accesses are `lhu`/`sh`, NOT `lbu`/`sb`.
 *
 * Only two functions ever write it, and both take the value as a CALLER-SUPPLIED
 * argument, which is why "2" is not a defeat code:
 *   0x8004D9E8  cinematic_camera_start        flags = arg7  (0x8004DA7C)
 *   0x8004DA94  cinematic_camera_start_polar  flags = arg8  (0x8004DB44)
 * Both also set the camera PHASE 0x80090BEC := 2, which starts the sequence.
 *
 * THE SELECTOR 0x8004EA8C (census name `enemy_ai_dispatcher` is WRONG)
 * -------------------------------------------------------------------
 * switch ([0x80090BEC]):
 *   case 2: four_byte_store(0,0,0,16);       phase := 1
 *           if (flags & 2) [0x800A6590] |= 0x04
 *   case 1: if ([0x80082388]) break;  four_byte_store(128,128,128,16)
 *           flags |= 0x01;  phase := 0
 *   case 3: if ([0x80082388]) break;  four_byte_store(128,128,128,16)
 *           phase := 0; flags &= ~0x01
 *           if (flags & 2) [0x800A6590] &= ~0x04
 *   case 4: four_byte_store(0,0,0,16);       phase := 3
 * tail:  if (flags & 1) camera params come from the setpiece block 0x80090BC0
 *        (after setpiece_actor_update, a0 = s0-46 = 0x80090BC0)
 *        else from the ordinary follow camera 0x80095358.
 *        Either way the result lands at 0x8009EC50.
 *
 * So:  bit 0x01 = CINEMATIC CAMERA ACTIVE.
 *      bit 0x02 = "also toggle 0x800A6590 bit 0x04 for the duration".
 *
 * BIT 0x01 AND THE HUD
 * --------------------
 * gameplay_state_machine reads it twice (0x8004F3D0, 0x8004F6DC) and, when set,
 * SKIPS the in-game HUD stage `jal 0x800526F4` (hud_draw, per E13) and calls
 * `jal 0x80053638` instead -- draw_mirrored_fullscreen_quads, i.e. cinematic
 * letterboxing.  It is NOT a boss health bar; that earlier hypothesis is refuted.
 *
 * POWER-WORD BIT 0x04 IS NOT A POWER-UP
 * -------------------------------------
 * All five readers of 0x800A6590 bit 0x04 (0x8004EED0, 0x80050C84, 0x80051138,
 * 0x80054F38, 0x80056550) use it the same way: SET -> branch PAST the body.  It is
 * never used to enable anything.  Three sit in SFX functions, one in
 * gameplay_state_machine (where taking it masks the player action word 0x80082488
 * down to 0x309), one in actor_skinned_update.  It is a cutscene SUPPRESSION gate.
 *
 * THE ROWS' ACTUAL QUESTION
 * -------------------------
 * There is NO path from 0x80090BEE to the level-exit transition.  Its complete
 * consumer set is the selector above plus the two HUD sites plus one overlay read;
 * none of them touches 0x800823A0, the scene id, or a loader.  The Council Chamber
 * exit is a DIFFERENT store in the same overlay basic block that starts the camera:
 *
 *   LEVEL02/LEVEL.BIN  (the blob resident in region A during the fight -- verified
 *                       live, NOT assumed; region A is a shared swap buffer)
 *     0x800B4070  lh v0,[0x8009FE72]      ; Thumper HP = actor 0x8009FE04 + 0x6E
 *     0x800B4078  slti v0,v0,21           ; defeat threshold: HP <= 20
 *     0x800B4090  bne  [0x800823A0],0     ; once-only guard: skip if already latched
 *     0x800B4118  flags argument := 2
 *     0x800B4138  jal 0x8004DA94          ; start the cinematic camera
 *     0x800B4190  sh v0,[0x800823A0]      ; *** THE LEVEL EXIT *** (v0 = 1)
 *
 * The camera start comes FIRST and the latch second, in one straight-line block.
 * Live confirmation: tools/phase4_d16_f03_oracle.py / analysis/phase4_d16_f03_oracle.json.
 *
 * METHOD
 * ------
 * Two INDEPENDENT censuses of every access to a given absolute address, so that
 * neither one's blind spot is load-bearing:
 *
 *   (A) IMMEDIATE scan -- every load/store whose 16-bit immediate equals the low
 *       half of the target.  Exhaustive for the canonical `lui base,hi` +
 *       `op rt,lo(base)` form; blind to a split base and to pointer addressing;
 *       and it FALSE-POSITIVES on a same-low-half address (0x800B0BEE), which is
 *       why every candidate is re-resolved rather than counted.
 *
 *   (B) DATAFLOW scan -- linear constant propagation over lui/addiu/ori with $gp
 *       pinned to 0x80081D98, computing each load/store's effective address.
 *       Catches the split-base form; still blind to a pointer loaded from memory.
 *
 * The two are compared as SETS, never as counts: their counts legitimately differ
 * because each sees a form the other cannot, so asserting count equality would be
 * an inference dressed up as a structural check.  A pointer-register access remains
 * possible in principle and is NOT claimed against.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_d16_f03_static.c \
 *      -o /tmp/d16 && /tmp/d16
 *   /tmp/d16 --census ADDR | --callers ADDR | --disasm ADDR [--img BLOB] [--window N]
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { EXE_HEADER_SIZE = 0x800, EXE_LOAD_VA = 0x80010000u };
#define GP_CONST 0x80081D98u

#define BOSS_FLAG   0x80090BEEu   /* the D16/F03 "defeat flag" under test */
#define POWER_WORD  0x800A6590u   /* power-up bitfield (B06/B08)          */

struct image {
    const char *path;
    uint8_t    *buf;
    size_t      size;
    uint32_t    base;     /* VA of file offset 0 (after any header skip) */
    size_t      skip;     /* header bytes not mapped                     */
};

static struct image images[64];
static int n_images;

static uint32_t rd32(const struct image *im, size_t off)
{
    return (uint32_t)im->buf[off] | ((uint32_t)im->buf[off + 1] << 8) |
           ((uint32_t)im->buf[off + 2] << 16) | ((uint32_t)im->buf[off + 3] << 24);
}

static uint32_t va_of(const struct image *im, size_t off)
{
    return im->base + (uint32_t)(off - im->skip);
}

static int load_image(const char *path, uint32_t base, size_t skip, int required)
{
    FILE *f = fopen(path, "rb");
    long n;
    struct image *im;
    if (!f) {
        if (required) { perror(path); exit(2); }
        return 0;
    }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 0; }
    n = ftell(f);
    rewind(f);
    if (n <= (long)skip) { fclose(f); return 0; }
    im = &images[n_images];
    im->path = path;
    im->size = (size_t)n;
    im->base = base;
    im->skip = skip;
    im->buf  = malloc(im->size);
    if (!im->buf || fread(im->buf, 1, im->size, f) != im->size) {
        fprintf(stderr, "read %s\n", path);
        exit(2);
    }
    fclose(f);
    n_images++;
    return 1;
}

static const struct image *resident(void) { return &images[0]; }

static uint32_t exe_u32(uint32_t va)
{
    const struct image *im = resident();
    size_t off;
    if (va < EXE_LOAD_VA) { fprintf(stderr, "va below base\n"); exit(2); }
    off = EXE_HEADER_SIZE + (size_t)(va - EXE_LOAD_VA);
    if (off + 4 > im->size) { fprintf(stderr, "va outside image\n"); exit(2); }
    return rd32(im, off);
}

/* ---------------------------------------------------------------- disasm -- */

static const char *R[32] = {
    "zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6",
    "t7","s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp",
    "fp","ra"
};

static int is_load(uint32_t op)
{
    return op == 0x20 || op == 0x21 || op == 0x23 || op == 0x24 || op == 0x25;
}
static int is_store(uint32_t op) { return op == 0x28 || op == 0x29 || op == 0x2B; }
static int is_mem(uint32_t op)   { return is_load(op) || is_store(op); }

static const char *memname(uint32_t op)
{
    switch (op) {
    case 0x20: return "lb";  case 0x21: return "lh";  case 0x23: return "lw";
    case 0x24: return "lbu"; case 0x25: return "lhu"; case 0x28: return "sb";
    case 0x29: return "sh";  case 0x2B: return "sw";  default: return "??";
    }
}

static void dis(uint32_t w, uint32_t pc, char *out, size_t n)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
    uint32_t rd = (w >> 11) & 31, sa = (w >> 6) & 31, fn = w & 63;
    int16_t  s  = (int16_t)(w & 0xFFFF);
    uint32_t tgt = (pc + 4 + ((uint32_t)s << 2));

    if (w == 0) { snprintf(out, n, "nop"); return; }
    if (is_mem(op)) {
        snprintf(out, n, "%s %s,%d(%s)", memname(op), R[rt], s, R[rs]);
        return;
    }
    switch (op) {
    case 0x00:
        switch (fn) {
        case 0x00: snprintf(out, n, "sll %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x02: snprintf(out, n, "srl %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x03: snprintf(out, n, "sra %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x08: snprintf(out, n, "jr %s", R[rs]); return;
        case 0x09: snprintf(out, n, "jalr %s", R[rs]); return;
        case 0x20: case 0x21: snprintf(out, n, "addu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x22: case 0x23: snprintf(out, n, "subu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x24: snprintf(out, n, "and %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x25: snprintf(out, n, "or %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x2A: case 0x2B: snprintf(out, n, "slt %s,%s,%s", R[rd], R[rs], R[rt]); return;
        default: snprintf(out, n, "special.%02x", fn); return;
        }
    case 0x02: snprintf(out, n, "j 0x%08x", (pc & 0xF0000000u) | ((w & 0x3FFFFFF) << 2)); return;
    case 0x03: snprintf(out, n, "jal 0x%08x", (pc & 0xF0000000u) | ((w & 0x3FFFFFF) << 2)); return;
    case 0x04: snprintf(out, n, "beq %s,%s,0x%08x", R[rs], R[rt], tgt); return;
    case 0x05: snprintf(out, n, "bne %s,%s,0x%08x", R[rs], R[rt], tgt); return;
    case 0x06: snprintf(out, n, "blez %s,0x%08x", R[rs], tgt); return;
    case 0x07: snprintf(out, n, "bgtz %s,0x%08x", R[rs], tgt); return;
    case 0x01: snprintf(out, n, "%s %s,0x%08x", rt ? "bgez" : "bltz", R[rs], tgt); return;
    case 0x08: case 0x09: snprintf(out, n, "addiu %s,%s,%d", R[rt], R[rs], s); return;
    case 0x0A: case 0x0B: snprintf(out, n, "slti %s,%s,%d", R[rt], R[rs], s); return;
    case 0x0C: snprintf(out, n, "andi %s,%s,0x%x", R[rt], R[rs], w & 0xFFFF); return;
    case 0x0D: snprintf(out, n, "ori %s,%s,0x%x", R[rt], R[rs], w & 0xFFFF); return;
    case 0x0F: snprintf(out, n, "lui %s,0x%x", R[rt], w & 0xFFFF); return;
    default:   snprintf(out, n, "op%02x", op); return;
    }
}

/* -------------------------------------------------------------- censuses -- */

struct hit { uint32_t pc, word, addr; int store; const char *file; };

static struct hit hits[256];
static int n_hits;

/* (A) immediate-only scan.  Records PCs so the two censuses can be compared as
 * SETS rather than as counts -- the counts legitimately differ (each method
 * sees an addressing form the other cannot), so an equality check on counts
 * would be an inference dressed up as a structural assertion. */
struct immhit { uint32_t pc, word, resolved; int resolved_ok; const char *file; };
static struct immhit imm_pcs[256];
static int n_imm;

static int scan_immediate(uint32_t target)
{
    int count = 0;
    n_imm = 0;
    for (int i = 0; i < n_images; i++) {
        const struct image *im = &images[i];
        for (size_t off = im->skip; off + 4 <= im->size; off += 4) {
            uint32_t w = rd32(im, off), op = w >> 26;
            if (!is_mem(op)) continue;
            if ((w & 0xFFFF) != (target & 0xFFFF)) continue;
            if (n_imm < (int)(sizeof imm_pcs / sizeof imm_pcs[0])) {
                imm_pcs[n_imm].pc   = va_of(im, off);
                imm_pcs[n_imm].word = w;
                imm_pcs[n_imm].file = im->path;
                n_imm++;
            }
            count++;
        }
    }
    return count;
}

/* (B) dataflow scan */
static void invalidate_caller_saved(int *valid)
{
    static const int cs[] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,24,25,31};
    for (size_t k = 0; k < sizeof cs / sizeof cs[0]; k++) valid[cs[k]] = 0;
}

static int scan_dataflow(uint32_t target, int record)
{
    int count = 0;
    for (int i = 0; i < n_images; i++) {
        const struct image *im = &images[i];
        uint32_t val[32];
        int valid[32];
        memset(val, 0, sizeof val);
        memset(valid, 0, sizeof valid);
        val[28] = GP_CONST; valid[28] = 1;   /* $gp is a proven constant */
        val[0] = 0; valid[0] = 1;

        for (size_t off = im->skip; off + 4 <= im->size; off += 4) {
            uint32_t w = rd32(im, off);
            uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
            uint32_t rd = (w >> 11) & 31, fn = w & 63;
            int16_t  s  = (int16_t)(w & 0xFFFF);

            if (is_mem(op)) {
                if (valid[rs]) {
                    uint32_t addr = val[rs] + (uint32_t)(int32_t)s;
                    /* annotate any immediate-scan candidate at this PC with the
                     * address its base actually resolves to */
                    for (int q = 0; q < n_imm; q++)
                        if (imm_pcs[q].pc == va_of(im, off) &&
                            imm_pcs[q].file == im->path) {
                            imm_pcs[q].resolved = addr;
                            imm_pcs[q].resolved_ok = 1;
                        }
                    if (addr == target) {
                        if (record && n_hits < (int)(sizeof hits / sizeof hits[0])) {
                            hits[n_hits].pc    = va_of(im, off);
                            hits[n_hits].word  = w;
                            hits[n_hits].addr  = addr;
                            hits[n_hits].store = is_store(op);
                            hits[n_hits].file  = im->path;
                            n_hits++;
                        }
                        count++;
                    }
                }
                if (is_load(op)) { valid[rt] = 0; }
                continue;
            }
            switch (op) {
            case 0x0F: val[rt] = (w & 0xFFFF) << 16; valid[rt] = 1; break;
            case 0x08: case 0x09:
                if (valid[rs]) { val[rt] = val[rs] + (uint32_t)(int32_t)s; valid[rt] = 1; }
                else valid[rt] = 0;
                break;
            case 0x0D:
                if (valid[rs]) { val[rt] = val[rs] | (w & 0xFFFF); valid[rt] = 1; }
                else valid[rt] = 0;
                break;
            case 0x03:                       /* jal: clobbers caller-saved */
                invalidate_caller_saved(valid);
                break;
            case 0x00:
                if (fn == 0x08) {            /* jr: end of a flow */
                    memset(valid, 0, sizeof valid);
                    valid[28] = 1; valid[0] = 1;
                } else if (fn == 0x09) {
                    invalidate_caller_saved(valid);
                } else if (fn != 0x00 || rd != 0) {
                    valid[rd] = 0;
                }
                break;
            case 0x01: case 0x02: case 0x04: case 0x05: case 0x06: case 0x07:
                break;                       /* branches write nothing */
            default:
                valid[rt] = 0;               /* any other I-type writes rt */
                break;
            }
            valid[0] = 1; val[0] = 0;
        }
    }
    return count;
}

/* Report the SET difference between the two censuses.
 *
 * Returns the number of UNEXPLAINED immediate-scan candidates only.  A candidate
 * whose base the dataflow resolved to a DIFFERENT address is fully explained (it
 * is a false positive of the low-half match -- 0x800B0BEE collides with
 * 0x80090BEE) and is reported but not counted as a defect.  A candidate whose
 * base could not be resolved at all IS counted, because then neither method can
 * say what it touches.  A dataflow-only hit is the expected split-base or pointer
 * form and is never a defect. */
static int compare_censuses(void)
{
    int missed = 0;
    for (int i = 0; i < n_imm; i++) {
        int found = 0;
        char txt[96];
        for (int j = 0; j < n_hits; j++)
            if (hits[j].pc == imm_pcs[i].pc && hits[j].file == imm_pcs[i].file)
                { found = 1; break; }
        if (!found) {
            dis(imm_pcs[i].word, imm_pcs[i].pc, txt, sizeof txt);
            printf("  GAP: 0x%08" PRIx32 "  %08" PRIx32 "  %-22s %s\n"
                   "       (immediate scan only -- %s)\n",
                   imm_pcs[i].pc, imm_pcs[i].word, txt, imm_pcs[i].file,
                   imm_pcs[i].resolved_ok
                     ? "FALSE POSITIVE: base resolves elsewhere"
                     : "base register unresolved -- NOT confirmed either way");
            if (imm_pcs[i].resolved_ok)
                printf("       resolves to 0x%08" PRIx32 "\n", imm_pcs[i].resolved);
            if (!imm_pcs[i].resolved_ok)
                missed++;      /* only an UNRESOLVED base is a real gap */
        }
    }
    for (int j = 0; j < n_hits; j++) {
        int found = 0;
        for (int i = 0; i < n_imm; i++)
            if (hits[j].pc == imm_pcs[i].pc && hits[j].file == imm_pcs[i].file)
                { found = 1; break; }
        if (!found)
            printf("  (dataflow-only, split-base or pointer form: 0x%08" PRIx32 " %s)\n",
                   hits[j].pc, hits[j].file);
    }
    return missed;
}

/* Every jal to a target, across resident + overlays.  Also reports the
 * immediately-preceding argument setup so a constant flags argument is visible
 * without a second pass. */
static int scan_callers(uint32_t target)
{
    uint32_t enc = 0x0C000000u | ((target >> 2) & 0x03FFFFFFu);
    int n = 0;
    for (int i = 0; i < n_images; i++) {
        const struct image *im = &images[i];
        for (size_t off = im->skip; off + 4 <= im->size; off += 4) {
            if (rd32(im, off) != enc) continue;
            printf("  caller 0x%08" PRIx32 "  %s\n", va_of(im, off), im->path);
            for (size_t k = (off > im->skip + 0x2C) ? off - 0x2C : im->skip;
                 k <= off + 4 && k + 4 <= im->size; k += 4) {
                char txt[96];
                uint32_t w = rd32(im, k);
                dis(w, va_of(im, k), txt, sizeof txt);
                printf("      0x%08" PRIx32 "  %08" PRIx32 "  %s\n",
                       va_of(im, k), w, txt);
            }
            n++;
        }
    }
    return n;
}

static void disasm_window(const struct image *im, uint32_t from, uint32_t to,
                          uint32_t mark)
{
    for (uint32_t pc = from; pc <= to; pc += 4) {
        char txt[96];
        size_t off;
        uint32_t w;
        if (pc < im->base) continue;
        off = im->skip + (size_t)(pc - im->base);
        if (off + 4 > im->size) break;
        w = rd32(im, off);
        dis(w, pc, txt, sizeof txt);
        printf("  %s0x%08" PRIx32 "  %08" PRIx32 "  %s\n",
               pc == mark ? ">> " : "   ", pc, w, txt);
    }
}

/* ------------------------------------------------------------------ pins -- */

struct pin { const char *img; uint32_t va, word; const char *role; };

#define RES "SCUS_942.88"
#define OVL "LEVEL02/LEVEL.BIN"

static const struct pin pins[] = {
    /* --- the camera block's own base, proving 0x80090BEE is a FIELD of it ---- */
    {RES, 0x8004EA98u, 0x26100BECu, "selector: s0 = 0x80090BEC (phase), block+0x2C"},
    {RES, 0x8004EC60u, 0x2604FFD2u, "tail: a0 = s0-46 = 0x80090BC0 -> setpiece_actor_update"},
    {RES, 0x8004EC5Cu, 0x0C013766u, "tail: jal 0x8004DD98 setpiece_actor_update"},

    /* --- the only two writers, both from a caller-supplied argument ---------- */
    {RES, 0x8004DA7Cu, 0xA4300BEEu, "W1 sh s0,0x0bee(at)  flags := arg7  (0x8004D9E8)"},
    {RES, 0x8004DB44u, 0xA4290BEEu, "W2 sh t1,0x0bee(at)  flags := arg8  (0x8004DA94)"},
    {RES, 0x8004DA74u, 0xA4220BECu, "W1 also sets phase 0x80090BEC := 2"},
    {RES, 0x8004DB50u, 0xA4220BECu, "W2 also sets phase 0x80090BEC := 2"},

    /* --- bit 0x01 = cinematic camera ACTIVE ---------------------------------- */
    {RES, 0x8004EB0Cu, 0x94420BEEu, "case1: lhu flags"},
    {RES, 0x8004EB14u, 0x34420001u, "case1: ori 0x1   -- SET 'camera active'"},
    {RES, 0x8004EB1Cu, 0xA4220BEEu, "case1: store flags back"},
    {RES, 0x8004EB98u, 0x94420BEEu, "case3: lhu flags"},
    {RES, 0x8004EBA0u, 0x3043FFFEu, "case3: andi 0xfffe -- CLEAR 'camera active'"},
    {RES, 0x8004EBACu, 0xA4230BEEu, "case3: store flags back"},
    {RES, 0x8004EBF4u, 0x96020000u, "tail: lhu flags via s0 (pointer form)"},
    {RES, 0x8004EBFCu, 0x30420001u, "tail: andi 0x1 -- selects the camera SOURCE"},

    /* --- bit 0x02 = toggle power-word bit 0x04 for the duration -------------- */
    {RES, 0x8004EB40u, 0x94420BEEu, "case2: lhu flags"},
    {RES, 0x8004EB48u, 0x30420002u, "case2: andi 0x2"},
    {RES, 0x8004EB64u, 0x34420004u, "case2: ori 0x4 -> 0x800A6590 |= 0x04"},
    {RES, 0x8004EBA4u, 0x30420002u, "case3: andi 0x2"},
    {RES, 0x8004EBC8u, 0x3042FFFBu, "case3: andi 0xfffb -> 0x800A6590 &= ~0x04"},

    /* --- bit 0x01 swaps the HUD for cinematic letterboxing ------------------- */
    {RES, 0x8004F3D0u, 0x94420BEEu, "state machine site 1: lhu flags"},
    {RES, 0x8004F3D8u, 0x30420001u, "state machine site 1: andi 0x1"},
    {RES, 0x8004F3E4u, 0x0C0149BDu, "site 1 NOT set: jal 0x800526F4 hud_draw"},
    {RES, 0x8004F3F4u, 0x0C014D8Eu, "site 1 SET:     jal 0x80053638 letterbox quads"},
    {RES, 0x8004F6DCu, 0x94420BEEu, "state machine site 2: lhu flags"},
    {RES, 0x8004F6E4u, 0x30420001u, "state machine site 2: andi 0x1"},
    {RES, 0x8004F6F0u, 0x0C0149BDu, "site 2 NOT set: jal 0x800526F4 hud_draw"},
    {RES, 0x8004F700u, 0x0C014D8Eu, "site 2 SET:     jal 0x80053638 letterbox quads"},

    /* --- the resident telescope path also passes flags = 2 ------------------- */
    {RES, 0x8004D6F4u, 0x24030002u, "telescope setpiece: v1 = 2 (the flags argument)"},
    {RES, 0x8004D728u, 0xAFA30018u, "telescope setpiece: sw v1,24(sp) = arg7"},
    {RES, 0x8004D730u, 0x0C01367Au, "telescope setpiece: jal 0x8004D9E8"},

    /* --- COUNCIL CHAMBER: defeat gate, camera start, and the REAL exit ------- */
    {OVL, 0x800B4070u, 0x8442FE72u, "lh v0,[0x8009FE72] -- Thumper HP (0x8009FE04+0x6E)"},
    {OVL, 0x800B4078u, 0x28420015u, "slti v0,v0,21 -- defeat threshold HP <= 20"},
    {OVL, 0x800B4090u, 0x14400043u, "bne [0x800823A0],0 -- once-only guard"},
    {OVL, 0x800B4118u, 0x24020002u, "v0 = 2  -- the cinematic-camera FLAGS argument"},
    {OVL, 0x800B411Cu, 0xAFA20014u, "sw v0,20(sp) = arg8"},
    {OVL, 0x800B4138u, 0x0C0136A5u, "jal 0x8004DA94 -- start the cinematic camera"},
    {OVL, 0x800B4190u, 0xA42223A0u, "sh v0,[0x800823A0] -- *** THE LEVEL EXIT ***"},
};

int main(int argc, char **argv)
{
    uint32_t want_disasm = 0, window = 0x40, want_callers = 0, want_census = 0;
    const char *want_img = NULL;
    int rc = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--disasm") && i + 1 < argc)
            want_disasm = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--window") && i + 1 < argc)
            window = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--img") && i + 1 < argc)
            want_img = argv[++i];
        else if (!strcmp(argv[i], "--callers") && i + 1 < argc)
            want_callers = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--census") && i + 1 < argc)
            want_census = (uint32_t)strtoul(argv[++i], NULL, 0);
    }

    load_image("REBUILD/files/SCUS_942.88", EXE_LOAD_VA, EXE_HEADER_SIZE, 1);

    /* every overlay blob, so "resident-only" is a measured claim not an assumption */
    {
        static char paths[64][64];
        int k = 0;
        for (int lvl = 0; lvl <= 20 && k < 60; lvl++) {
            snprintf(paths[k], sizeof paths[k], "REBUILD/files/LEVEL%02d/LEVEL.BIN", lvl);
            if (load_image(paths[k], 0x800B39A0u, 0, 0)) k++;
            snprintf(paths[k], sizeof paths[k], "REBUILD/files/LEVEL%02d/LEVEL1.BIN", lvl);
            if (load_image(paths[k], 0x800B39A0u, 0, 0)) k++;
        }
        snprintf(paths[k], sizeof paths[k], "REBUILD/files/BITS/MEMORY.BIN");
        if (load_image(paths[k], 0x800B5788u, 0, 0)) k++;
    }
    printf("images loaded: %d (resident + %d overlays)\n\n", n_images, n_images - 1);

    if (want_census) {
        int imm, dfl;
        n_hits = 0;
        imm = scan_immediate(want_census);
        dfl = scan_dataflow(want_census, 1);
        printf("=== 0x%08" PRIx32 " access census ===\n", want_census);
        printf("  immediate scan: %d  |  dataflow scan: %d\n", imm, dfl);
        for (int i = 0; i < n_hits; i++) {
            char txt[96];
            dis(hits[i].word, hits[i].pc, txt, sizeof txt);
            printf("  %-5s 0x%08" PRIx32 "  %08" PRIx32 "  %-24s  %s\n",
                   hits[i].store ? "STORE" : "load", hits[i].pc, hits[i].word, txt,
                   hits[i].file);
        }
        compare_censuses();
        return 0;
    }

    if (want_callers) {
        printf("callers of 0x%08" PRIx32 ":\n", want_callers);
        printf("  %d found\n", scan_callers(want_callers));
        return 0;
    }

    if (want_disasm) {
        const struct image *im = resident();
        if (want_img) {
            im = NULL;
            for (int i = 0; i < n_images; i++)
                if (strstr(images[i].path, want_img)) { im = &images[i]; break; }
            if (!im) { fprintf(stderr, "no image matching %s\n", want_img); return 2; }
        }
        printf("disassembly around 0x%08" PRIx32 " in %s:\n", want_disasm, im->path);
        disasm_window(im, want_disasm - window, want_disasm + window, want_disasm);
        return 0;
    }

    /* ---- census of the boss flag ---- */
    {
        int imm, dfl;
        n_hits = 0;
        imm = scan_immediate(BOSS_FLAG);
        dfl = scan_dataflow(BOSS_FLAG, 1);
        printf("=== 0x%08" PRIx32 " access census ===\n", BOSS_FLAG);
        printf("  immediate scan: %d  |  dataflow scan: %d\n", imm, dfl);
        for (int i = 0; i < n_hits; i++) {
            char txt[96];
            dis(hits[i].word, hits[i].pc, txt, sizeof txt);
            printf("  %-5s 0x%08" PRIx32 "  %08" PRIx32 "  %-24s  %s\n",
                   hits[i].store ? "STORE" : "load", hits[i].pc, hits[i].word, txt,
                   hits[i].file);
        }
        if (compare_censuses() != 0) rc = 1;
        putchar('\n');
    }

    /* ---- census of the power word, to identify who reads bit 0x04 ---- */
    {
        int imm, dfl;
        n_hits = 0;
        imm = scan_immediate(POWER_WORD);
        dfl = scan_dataflow(POWER_WORD, 1);
        printf("=== 0x%08" PRIx32 " (power word) access census ===\n", POWER_WORD);
        printf("  immediate scan: %d  |  dataflow scan: %d\n", imm, dfl);
        for (int i = 0; i < n_hits; i++) {
            char txt[96], nxt[128];
            uint32_t follow = 0;
            dis(hits[i].word, hits[i].pc, txt, sizeof txt);
            nxt[0] = 0;
            /* for a load, show the next two instructions so the mask is visible */
            if (!hits[i].store) {
                for (int d = 1; d <= 3; d++) {
                    uint32_t w2;
                    char t2[96];
                    if (strcmp(hits[i].file, images[0].path) != 0) break;
                    w2 = exe_u32(hits[i].pc + 4u * (uint32_t)d);
                    dis(w2, hits[i].pc + 4u * (uint32_t)d, t2, sizeof t2);
                    if ((w2 >> 26) == 0x0C) {   /* andi -- the mask */
                        snprintf(nxt, sizeof nxt, "  [mask %s]", t2);
                        follow = 1;
                        break;
                    }
                }
            }
            (void)follow;
            printf("  %-5s 0x%08" PRIx32 "  %08" PRIx32 "  %-24s%s  %s\n",
                   hits[i].store ? "STORE" : "load", hits[i].pc, hits[i].word, txt,
                   nxt, hits[i].file);
        }
        if (compare_censuses() != 0) rc = 1;
        putchar('\n');
    }

    /* ---- instruction pins, resident AND overlay ---- */
    {
        size_t ok = 0, total = sizeof pins / sizeof pins[0];
        printf("=== instruction pins ===\n");
        for (size_t i = 0; i < total; i++) {
            const struct image *im = NULL;
            uint32_t got = 0;
            size_t off;
            int good = 0;
            for (int k = 0; k < n_images; k++)
                if (strstr(images[k].path, pins[i].img)) { im = &images[k]; break; }
            if (im && pins[i].va >= im->base) {
                off = im->skip + (size_t)(pins[i].va - im->base);
                if (off + 4 <= im->size) {
                    got = rd32(im, off);
                    good = (got == pins[i].word);
                }
            }
            ok += (size_t)good;
            printf("  %s %-18s 0x%08" PRIx32 "  want %08" PRIx32 "  got %08" PRIx32
                   "  %s\n", good ? "ok  " : "FAIL", pins[i].img, pins[i].va,
                   pins[i].word, got, pins[i].role);
        }
        printf("  %zu/%zu pins OK\n", ok, total);
        if (ok != total) rc = 1;
    }

    puts("");
    puts("D16/F03: 0x80090BEE is the cinematic-camera FLAGS field (block 0x80090BC0+0x2E),");
    puts("  not a Thumper defeat code. bit 0x01 = camera active (and swaps the HUD for");
    puts("  letterbox quads); bit 0x02 = hold 0x800A6590 bit 0x04, a cutscene SUPPRESSION");
    puts("  gate, for the duration. The value 2 is a caller argument, passed by the");
    puts("  resident telescope path and by several level overlays alike.");
    puts("  The Council Chamber LEVEL EXIT is [0x800823A0] = 1 at 0x800B4190 in");
    puts("  LEVEL02/LEVEL.BIN -- a different store, reached on HP <= 20, and no consumer");
    puts("  of 0x80090BEE participates in it.");

    return rc;
}
