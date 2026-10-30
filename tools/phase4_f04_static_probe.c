/*
 * phase4_f04_static_probe.c -- instruction-level static probe for Phase-4 row
 * F04_cliffside_canyon (Stage 4 "Cliffside Canyon": dandelion flight + bird hazard).
 *
 * WHY THIS EXISTS
 * ---------------
 * Two of F04's claims have only ever been asserted from prose or from a trace
 * summary's own labels, and one of them is the row's own named retained residual:
 *
 *   1. `tools/phase4_f04_route_analyzer.c` pinned six "exact sites" by comparing
 *      TEXT against the checked-in ASM listings, and it cannot run at all today --
 *      it opens the transient /tmp trace TSVs before it does anything else, and
 *      those were deleted with the 2026-08-04 session. So the row's static half has
 *      not been re-verifiable since the day it was written. This tool re-derives
 *      each site's EFFECTIVE ADDRESS by decoding the pristine executable's own
 *      instruction words and resolving the `lui` that forms the base register,
 *      instead of trusting a mnemonic string or a label in a trace.
 *
 *   2. D17 (and, by citation, F04) records that the power-flags bit 0x10 seen at
 *      the Cliffside death branch is "very likely uncharted Cliffside-overlay
 *      code" -- an inference, reached after an exhaustive check of the RESIDENT
 *      image found no such writer. The overlay half of that sentence was never
 *      measured. This tool decodes the Cliffside overlay pair itself.
 *
 * WHAT IT DOES
 * ------------
 * Given a plan file describing images, code ranges, probe sites and target
 * addresses (all of which the caller derives from pinned artifacts -- nothing here
 * is hard-coded), it performs a block-local constant-propagating decode of MIPS
 * R3000 and reports:
 *
 *   * for every SITE: the raw word, decoded mnemonic, base/target registers,
 *     signed offset and the RESOLVED absolute effective address;
 *   * for every access in a RANGE whose resolved effective address is in the
 *     TARGET set: pc, mnemonic, read/write, width, address, and -- for stores --
 *     the recovered value form. A store fed by an immediate reports `const`; a
 *     store fed by `ori`/`or` over a value loaded from the SAME address reports
 *     `rmw_or` with the exact set mask, which is what "writes bit 0x10" means at
 *     the instruction level; `andi` over such a load reports `rmw_and`.
 *
 * SOUNDNESS OF THE PROPAGATION
 * ----------------------------
 * Register facts are dropped at every branch/jump target inside the scanned range
 * (a join point), at the start of every range, and whenever a register is written
 * by anything the transfer function does not model. Constants therefore only ever
 * flow along straight-line code inside one basic block. This UNDER-reports (an
 * access whose base is formed across a join is left unresolved and simply is not
 * reported), which is the safe direction for a census used to bound a frontier:
 * every reported address is decoded, and the unresolved count is reported too so
 * the reader can see the bound rather than mistake the census for a total.
 *
 * PLAN FILE (TSV, '#' comments ignored)
 *   IMAGE  <id>  <path>  <va_base_hex>  <header_bytes>
 *   RANGE  <id>  <lo_hex>  <hi_hex>          # [lo,hi) virtual addresses, code
 *   SITE   <name>  <id>  <pc_hex>
 *   TARGET <name>  <addr_hex>
 *
 * Output: JSON on stdout. Exit 0 iff every SITE decoded to a resolved effective
 * address and every declared image/range was readable; non-zero otherwise, with
 * the reason on stderr. Silence is never success.
 *
 * Build:
 *   cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
 *      -o /tmp/abl-f04-probe/phase4_f04_static_probe tools/phase4_f04_static_probe.c
 */
#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_IMAGES   32
#define MAX_RANGES   4096
#define MAX_SITES    64
#define MAX_TARGETS  64
#define MAX_ACCESS   8192

static void die(const char *what, const char *detail)
{
    fprintf(stderr, "phase4_f04_static_probe: %s: %s\n", what, detail ? detail : "");
    exit(1);
}

/* ----------------------------------------------------------------- images -- */

typedef struct {
    char     id[48];
    char     path[512];
    uint32_t va_base;      /* virtual address of file offset 0 */
    uint32_t header_bytes; /* leading non-code bytes (code starts at va_base+this) */
    uint8_t *bytes;
    size_t   size;
} Image;

static Image images[MAX_IMAGES];
static int   n_images;

static Image *image_by_id(const char *id)
{
    for (int i = 0; i < n_images; i++)
        if (!strcmp(images[i].id, id)) return &images[i];
    return NULL;
}

static int image_word(const Image *im, uint32_t va, uint32_t *out)
{
    if (va < im->va_base) return 0;
    uint64_t off = (uint64_t)(va - im->va_base);
    if (off + 4 > im->size) return 0;
    const uint8_t *p = im->bytes + off;
    *out = (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
    return 1;
}

/* ------------------------------------------------------------------ plan --- */

typedef struct { char id[48]; uint32_t lo, hi; } Range;
typedef struct { char name[64]; char id[48]; uint32_t pc; int seen; } Site;
typedef struct { char name[64]; uint32_t addr; } Target;

static Range  ranges[MAX_RANGES];  static int n_ranges;
static Site   sites[MAX_SITES];    static int n_sites;
static Target targets[MAX_TARGETS]; static int n_targets;

static const char *target_name(uint32_t addr)
{
    for (int i = 0; i < n_targets; i++)
        if (targets[i].addr == addr) return targets[i].name;
    return NULL;
}

/* ------------------------------------------------------------ decode core -- */

#define OP(w)     ((w) >> 26)
#define RS(w)     (((w) >> 21) & 0x1F)
#define RT(w)     (((w) >> 16) & 0x1F)
#define RD(w)     (((w) >> 11) & 0x1F)
#define FUNCT(w)  ((w) & 0x3F)
#define IMM(w)    ((uint16_t)((w) & 0xFFFF))
#define SIMM(w)   ((int32_t)(int16_t)((w) & 0xFFFF))

static const char *mnemonic(uint32_t w)
{
    switch (OP(w)) {
    case 0x00:
        switch (FUNCT(w)) {
        case 0x08: return "jr";   case 0x09: return "jalr";
        case 0x21: return "addu"; case 0x25: return "or";
        case 0x24: return "and";  case 0x23: return "subu";
        case 0x00: return "sll";  case 0x02: return "srl";
        default:   return "r-type";
        }
    case 0x01: return "regimm";
    case 0x02: return "j";     case 0x03: return "jal";
    case 0x04: return "beq";   case 0x05: return "bne";
    case 0x06: return "blez";  case 0x07: return "bgtz";
    case 0x08: return "addi";  case 0x09: return "addiu";
    case 0x0A: return "slti";  case 0x0B: return "sltiu";
    case 0x0C: return "andi";  case 0x0D: return "ori";
    case 0x0E: return "xori";  case 0x0F: return "lui";
    case 0x20: return "lb";    case 0x21: return "lh";
    case 0x22: return "lwl";   case 0x23: return "lw";
    case 0x24: return "lbu";   case 0x25: return "lhu";
    case 0x26: return "lwr";
    case 0x28: return "sb";    case 0x29: return "sh";
    case 0x2A: return "swl";   case 0x2B: return "sw";
    case 0x2E: return "swr";
    default:   return "other";
    }
}

/* memory op classification: width in bytes, 1 = write, 0 = read, -1 = not a memop */
static int memop(uint32_t w, int *width, int *is_write)
{
    switch (OP(w)) {
    case 0x20: case 0x24: *width = 1; *is_write = 0; return 1;
    case 0x21: case 0x25: *width = 2; *is_write = 0; return 1;
    case 0x23:            *width = 4; *is_write = 0; return 1;
    case 0x28:            *width = 1; *is_write = 1; return 1;
    case 0x29:            *width = 2; *is_write = 1; return 1;
    case 0x2B:            *width = 4; *is_write = 1; return 1;
    default: return 0;
    }
}

/* Value provenance for the register a store writes from. */
typedef enum { V_NONE = 0, V_CONST, V_LOADED, V_RMW_OR, V_RMW_AND } VKind;

typedef struct {
    int      known;   /* register holds a decoded constant */
    uint32_t val;
    VKind    vkind;
    uint32_t vconst;  /* V_CONST value, or the mask for V_RMW_* */
    uint32_t vaddr;   /* V_LOADED / V_RMW_* : the address the value came from */
} RegState;

typedef struct {
    char     image[48];
    uint32_t pc;
    char     mnem[8];
    int      is_write;
    int      width;
    uint32_t addr;
    char     target[64];
    char     value_form[16];
    uint32_t value;
    uint32_t value_from;
} Access;

static Access accesses[MAX_ACCESS];
static int    n_accesses;

typedef struct {
    char     name[64];
    char     image[48];
    uint32_t pc;
    uint32_t word;
    char     mnem[8];
    int      resolved;
    int      is_write;
    int      width;
    uint32_t addr;
    int      rt;
    int      base;
    int32_t  offset;
} SiteResult;

static SiteResult site_results[MAX_SITES];
static int        n_site_results;

/* branch/jump target set for one range, used to drop facts at join points */
static uint32_t join_pcs[65536];
static int      n_joins;

static int is_join(uint32_t pc)
{
    for (int i = 0; i < n_joins; i++) if (join_pcs[i] == pc) return 1;
    return 0;
}

static void collect_joins(const Image *im, uint32_t lo, uint32_t hi)
{
    n_joins = 0;
    for (uint32_t pc = lo; pc < hi; pc += 4) {
        uint32_t w;
        if (!image_word(im, pc, &w)) break;
        uint32_t tgt = 0;
        int have = 0;
        switch (OP(w)) {
        case 0x01: case 0x04: case 0x05: case 0x06: case 0x07:
            tgt = (uint32_t)((int32_t)pc + 4 + (SIMM(w) << 2)); have = 1; break;
        case 0x02: case 0x03:
            tgt = ((pc + 4) & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2); have = 1; break;
        default: break;
        }
        if (have && tgt >= lo && tgt < hi && n_joins < (int)(sizeof join_pcs / sizeof *join_pcs))
            join_pcs[n_joins++] = tgt;
    }
}

static int unresolved_memops;   /* memops whose base register was not decoded */
static int total_memops;
static int total_instructions;

static void scan_range(const Image *im, const Range *r)
{
    RegState reg[32];
    memset(reg, 0, sizeof reg);
    reg[0].known = 1; reg[0].val = 0; reg[0].vkind = V_CONST; reg[0].vconst = 0;

    collect_joins(im, r->lo, r->hi);

    for (uint32_t pc = r->lo; pc < r->hi; pc += 4) {
        uint32_t w;
        if (!image_word(im, pc, &w)) {
            fprintf(stderr, "range %s 0x%08" PRIx32 "..0x%08" PRIx32
                            " runs past image %s\n", r->id, r->lo, r->hi, im->path);
            exit(1);
        }
        total_instructions++;

        if (pc != r->lo && is_join(pc)) {
            memset(reg, 0, sizeof reg);
            reg[0].known = 1; reg[0].vkind = V_CONST;
        }

        int width = 0, is_write = 0;
        int is_mem = memop(w, &width, &is_write);

        /* ---- record a SITE hit, resolved or not ---- */
        for (int s = 0; s < n_sites; s++) {
            if (sites[s].pc != pc || strcmp(sites[s].id, r->id)) continue;
            if (sites[s].seen) continue;
            sites[s].seen = 1;
            SiteResult *sr = &site_results[n_site_results++];
            memset(sr, 0, sizeof *sr);
            snprintf(sr->name, sizeof sr->name, "%.63s", sites[s].name);
            snprintf(sr->image, sizeof sr->image, "%.47s", im->id);
            snprintf(sr->mnem, sizeof sr->mnem, "%.7s", mnemonic(w));
            sr->pc = pc; sr->word = w;
            sr->is_write = is_mem ? is_write : -1;
            sr->width = is_mem ? width : 0;
            sr->rt = (int)RT(w); sr->base = (int)RS(w); sr->offset = SIMM(w);
            if (is_mem && reg[RS(w)].known) {
                sr->resolved = 1;
                sr->addr = reg[RS(w)].val + (uint32_t)SIMM(w);
            }
        }

        /* ---- record a targeted access ---- */
        if (is_mem) {
            total_memops++;
            if (!reg[RS(w)].known) {
                unresolved_memops++;
            } else {
                uint32_t ea = reg[RS(w)].val + (uint32_t)SIMM(w);
                const char *tn = target_name(ea);
                if (tn && n_accesses < MAX_ACCESS) {
                    Access *a = &accesses[n_accesses++];
                    memset(a, 0, sizeof *a);
                    snprintf(a->image, sizeof a->image, "%.47s", im->id);
                    snprintf(a->mnem, sizeof a->mnem, "%.7s", mnemonic(w));
                    snprintf(a->target, sizeof a->target, "%.63s", tn);
                    a->pc = pc; a->is_write = is_write; a->width = width; a->addr = ea;
                    if (is_write) {
                        RegState *v = &reg[RT(w)];
                        switch (v->vkind) {
                        case V_CONST:
                            snprintf(a->value_form, sizeof a->value_form, "const");
                            a->value = v->vconst; break;
                        case V_RMW_OR:
                            snprintf(a->value_form, sizeof a->value_form, "rmw_or");
                            a->value = v->vconst; a->value_from = v->vaddr; break;
                        case V_RMW_AND:
                            snprintf(a->value_form, sizeof a->value_form, "rmw_and");
                            a->value = v->vconst; a->value_from = v->vaddr; break;
                        case V_LOADED:
                            snprintf(a->value_form, sizeof a->value_form, "copy");
                            a->value_from = v->vaddr; break;
                        default:
                            snprintf(a->value_form, sizeof a->value_form, "unknown");
                            break;
                        }
                    } else {
                        snprintf(a->value_form, sizeof a->value_form, "n/a");
                    }
                }
            }
        }

        /* ---- transfer function ---- */
        uint32_t rt = RT(w), rs = RS(w), rd = RD(w);
        RegState nv;
        memset(&nv, 0, sizeof nv);

        switch (OP(w)) {
        case 0x0F: /* lui */
            nv.known = 1; nv.val = (uint32_t)IMM(w) << 16;
            nv.vkind = V_CONST; nv.vconst = nv.val;
            if (rt) reg[rt] = nv;
            break;
        case 0x0D: /* ori rt, rs, imm */
            if (reg[rs].known) { nv.known = 1; nv.val = reg[rs].val | IMM(w); }
            if (reg[rs].vkind == V_CONST) { nv.vkind = V_CONST; nv.vconst = reg[rs].vconst | IMM(w); }
            else if (reg[rs].vkind == V_LOADED) {
                nv.vkind = V_RMW_OR; nv.vconst = IMM(w); nv.vaddr = reg[rs].vaddr;
            }
            if (rt) reg[rt] = nv;
            break;
        case 0x0C: /* andi rt, rs, imm */
            if (reg[rs].known) { nv.known = 1; nv.val = reg[rs].val & IMM(w); }
            if (reg[rs].vkind == V_CONST) { nv.vkind = V_CONST; nv.vconst = reg[rs].vconst & IMM(w); }
            else if (reg[rs].vkind == V_LOADED) {
                nv.vkind = V_RMW_AND; nv.vconst = IMM(w); nv.vaddr = reg[rs].vaddr;
            }
            if (rt) reg[rt] = nv;
            break;
        case 0x08: case 0x09: /* addi / addiu */
            if (reg[rs].known) { nv.known = 1; nv.val = reg[rs].val + (uint32_t)SIMM(w); }
            if (reg[rs].vkind == V_CONST) {
                nv.vkind = V_CONST; nv.vconst = reg[rs].vconst + (uint32_t)SIMM(w);
            }
            if (rt) reg[rt] = nv;
            break;
        case 0x20: case 0x21: case 0x23: case 0x24: case 0x25: /* loads */
            if (reg[rs].known) {
                nv.vkind = V_LOADED; nv.vaddr = reg[rs].val + (uint32_t)SIMM(w);
            }
            if (rt) reg[rt] = nv;
            break;
        case 0x00: /* R-type */
            switch (FUNCT(w)) {
            case 0x21: /* addu rd, rs, rt */
                if (reg[rs].known && reg[rt].known) { nv.known = 1; nv.val = reg[rs].val + reg[rt].val; }
                if (reg[rs].vkind == V_CONST && reg[rt].vkind == V_CONST) {
                    nv.vkind = V_CONST; nv.vconst = reg[rs].vconst + reg[rt].vconst;
                } else if (reg[rs].vkind == V_LOADED && rt == 0) {
                    nv = reg[rs];  /* move */
                } else if (reg[rt].vkind == V_LOADED && rs == 0) {
                    nv = reg[rt];  /* move */
                }
                if (rd) reg[rd] = nv;
                break;
            case 0x25: /* or rd, rs, rt */
                if (reg[rs].known && reg[rt].known) { nv.known = 1; nv.val = reg[rs].val | reg[rt].val; }
                if (reg[rs].vkind == V_LOADED && reg[rt].vkind == V_CONST) {
                    nv.vkind = V_RMW_OR; nv.vconst = reg[rt].vconst; nv.vaddr = reg[rs].vaddr;
                } else if (reg[rt].vkind == V_LOADED && reg[rs].vkind == V_CONST) {
                    nv.vkind = V_RMW_OR; nv.vconst = reg[rs].vconst; nv.vaddr = reg[rt].vaddr;
                } else if (reg[rs].vkind == V_CONST && reg[rt].vkind == V_CONST) {
                    nv.vkind = V_CONST; nv.vconst = reg[rs].vconst | reg[rt].vconst;
                }
                if (rd) reg[rd] = nv;
                break;
            case 0x24: /* and rd, rs, rt */
                if (reg[rs].known && reg[rt].known) { nv.known = 1; nv.val = reg[rs].val & reg[rt].val; }
                if (rd) reg[rd] = nv;
                break;
            case 0x08: /* jr  -- no register written */
                break;
            case 0x09: /* jalr rd */
                if (rd) reg[rd] = nv;
                break;
            default:
                if (rd) reg[rd] = nv;
                break;
            }
            break;
        case 0x02: case 0x04: case 0x05: case 0x06: case 0x07: case 0x01:
            break; /* branches write nothing */
        case 0x03: /* jal clobbers $ra and, by ABI, the caller-saved set */
            reg[31] = nv;
            for (int c = 1; c <= 15; c++) reg[c] = nv;
            reg[24] = nv; reg[25] = nv;
            break;
        case 0x28: case 0x29: case 0x2A: case 0x2B: case 0x2E:
            break; /* stores write no register */
        default:
            if (rt) reg[rt] = nv;
            break;
        }
        reg[0].known = 1; reg[0].val = 0; reg[0].vkind = V_CONST; reg[0].vconst = 0;
    }
}

/* ------------------------------------------------------------------- plan -- */

static char *trim(char *s)
{
    while (*s && isspace((unsigned char)*s)) s++;
    char *e = s + strlen(s);
    while (e > s && isspace((unsigned char)e[-1])) *--e = 0;
    return s;
}

static void load_plan(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) die("cannot open plan", path);
    char line[1200];
    while (fgets(line, sizeof line, f)) {
        char *s = trim(line);
        if (!*s || *s == '#') continue;
        char kind[16] = {0};
        char *tab = strchr(s, '\t');
        if (!tab) die("plan line has no tab", s);
        size_t kl = (size_t)(tab - s);
        if (kl >= sizeof kind) die("plan kind too long", s);
        memcpy(kind, s, kl);
        char *rest = tab + 1;

        if (!strcmp(kind, "IMAGE")) {
            if (n_images >= MAX_IMAGES) die("too many images", NULL);
            Image *im = &images[n_images];
            char base[32] = {0}, hdr[32] = {0};
            if (sscanf(rest, "%47[^\t]\t%511[^\t]\t%31[^\t]\t%31s",
                       im->id, im->path, base, hdr) != 4)
                die("bad IMAGE line", rest);
            im->va_base = (uint32_t)strtoul(base, NULL, 0);
            im->header_bytes = (uint32_t)strtoul(hdr, NULL, 0);
            FILE *b = fopen(im->path, "rb");
            if (!b) die("cannot open image", im->path);
            fseek(b, 0, SEEK_END); long z = ftell(b); fseek(b, 0, SEEK_SET);
            if (z <= 0) die("empty image", im->path);
            im->bytes = malloc((size_t)z);
            if (!im->bytes || fread(im->bytes, 1, (size_t)z, b) != (size_t)z)
                die("cannot read image", im->path);
            im->size = (size_t)z;
            fclose(b);
            n_images++;
        } else if (!strcmp(kind, "RANGE")) {
            if (n_ranges >= MAX_RANGES) die("too many ranges", NULL);
            Range *r = &ranges[n_ranges];
            char lo[32] = {0}, hi[32] = {0};
            if (sscanf(rest, "%47[^\t]\t%31[^\t]\t%31s", r->id, lo, hi) != 3)
                die("bad RANGE line", rest);
            r->lo = (uint32_t)strtoul(lo, NULL, 0);
            r->hi = (uint32_t)strtoul(hi, NULL, 0);
            if (r->hi <= r->lo) die("RANGE hi <= lo", rest);
            n_ranges++;
        } else if (!strcmp(kind, "SITE")) {
            if (n_sites >= MAX_SITES) die("too many sites", NULL);
            Site *st = &sites[n_sites];
            char pc[32] = {0};
            if (sscanf(rest, "%63[^\t]\t%47[^\t]\t%31s", st->name, st->id, pc) != 3)
                die("bad SITE line", rest);
            st->pc = (uint32_t)strtoul(pc, NULL, 0);
            n_sites++;
        } else if (!strcmp(kind, "TARGET")) {
            if (n_targets >= MAX_TARGETS) die("too many targets", NULL);
            Target *t = &targets[n_targets];
            char ad[32] = {0};
            if (sscanf(rest, "%63[^\t]\t%31s", t->name, ad) != 2)
                die("bad TARGET line", rest);
            t->addr = (uint32_t)strtoul(ad, NULL, 0);
            n_targets++;
        } else {
            die("unknown plan kind", kind);
        }
    }
    fclose(f);
    if (!n_images) die("plan declares no IMAGE", path);
    if (!n_ranges) die("plan declares no RANGE", path);
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s PLAN.tsv\n", argv[0]);
        return 2;
    }
    load_plan(argv[1]);

    for (int i = 0; i < n_ranges; i++) {
        Image *im = image_by_id(ranges[i].id);
        if (!im) die("RANGE names an undeclared image", ranges[i].id);
        if (ranges[i].lo < im->va_base + im->header_bytes)
            die("RANGE starts inside the image header", ranges[i].id);
        scan_range(im, &ranges[i]);
    }

    int sites_unresolved = 0, sites_missing = 0;
    for (int i = 0; i < n_sites; i++) if (!sites[i].seen) sites_missing++;
    for (int i = 0; i < n_site_results; i++) if (!site_results[i].resolved) sites_unresolved++;

    printf("{\n");
    printf("  \"schema\": \"abl-phase4-f04-static-probe/1\",\n");
    printf("  \"images\": [\n");
    for (int i = 0; i < n_images; i++)
        printf("    {\"id\": \"%s\", \"path\": \"%s\", \"va_base\": \"0x%08" PRIX32
               "\", \"header_bytes\": %" PRIu32 ", \"size\": %zu}%s\n",
               images[i].id, images[i].path, images[i].va_base,
               images[i].header_bytes, images[i].size,
               i + 1 < n_images ? "," : "");
    printf("  ],\n");
    printf("  \"scan\": {\"ranges\": %d, \"instructions\": %d, \"memops\": %d, "
           "\"memops_with_unresolved_base\": %d},\n",
           n_ranges, total_instructions, total_memops, unresolved_memops);

    printf("  \"sites\": [\n");
    for (int i = 0; i < n_site_results; i++) {
        SiteResult *s = &site_results[i];
        char ea[24];
        if (s->resolved) snprintf(ea, sizeof ea, "\"0x%08" PRIX32 "\"", s->addr);
        else             snprintf(ea, sizeof ea, "null");
        printf("    {\"name\": \"%s\", \"image\": \"%s\", \"pc\": \"0x%08" PRIX32
               "\", \"word\": \"0x%08" PRIX32 "\", \"mnemonic\": \"%s\", "
               "\"is_store\": %d, \"width\": %d, \"rt\": %d, \"base_reg\": %d, "
               "\"offset\": %" PRId32 ", \"resolved\": %s, "
               "\"effective_address\": %s}%s\n",
               s->name, s->image, s->pc, s->word, s->mnem, s->is_write, s->width,
               s->rt, s->base, s->offset, s->resolved ? "true" : "false", ea,
               i + 1 < n_site_results ? "," : "");
    }
    printf("  ],\n");
    printf("  \"sites_declared\": %d, \"sites_found\": %d, \"sites_missing\": %d, "
           "\"sites_unresolved\": %d,\n", n_sites, n_site_results, sites_missing,
           sites_unresolved);

    printf("  \"target_accesses\": [\n");
    for (int i = 0; i < n_accesses; i++) {
        Access *a = &accesses[i];
        printf("    {\"image\": \"%s\", \"pc\": \"0x%08" PRIX32 "\", \"mnemonic\": \"%s\", "
               "\"access\": \"%s\", \"width\": %d, \"address\": \"0x%08" PRIX32 "\", "
               "\"target\": \"%s\", \"value_form\": \"%s\", \"value\": %" PRIu32 ", "
               "\"value_mask_hex\": \"0x%X\", \"value_from\": \"0x%08" PRIX32 "\"}%s\n",
               a->image, a->pc, a->mnem, a->is_write ? "write" : "read", a->width,
               a->addr, a->target, a->value_form, a->value, a->value, a->value_from,
               i + 1 < n_accesses ? "," : "");
    }
    printf("  ],\n");
    printf("  \"target_access_count\": %d\n", n_accesses);
    printf("}\n");

    if (sites_missing || sites_unresolved) {
        fprintf(stderr, "FAIL: %d site(s) not found in any range, %d site(s) whose base "
                        "register did not resolve\n", sites_missing, sites_unresolved);
        return 1;
    }
    return 0;
}
