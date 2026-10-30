/*
 * phase4_caller_domain_probe.c -- primary C implementation for the fixed
 * Phase-4 caller-domain pilot.
 *
 * This is deliberately sample-scoped.  The pilot returned NO-GO before the
 * Stage-B propagation specified for the shared analyser was authorized, so
 * retaining this probe separately avoids changing region_provenance.c (and
 * invalidating its full-corpus receipts) for machinery no consumer may use.
 * Python supplies only hash-pinned paths and identities; all instruction
 * decoding and byte probing remains compiled C.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *REGS[32] = {
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"
};

/* ================================================= caller-domain pilot ===
 *
 * The pilot asks a deliberately fail-closed question:
 * does a named function have an exhaustively enumerable incoming-edge set
 * across the resident image and the overlay that can coexist with it?
 *
 * Python supplies only a deterministic, hash-pinned manifest (image paths,
 * census extents, proved indirect edges, proved table byte ranges, and the
 * already-frozen site list).  All instruction decoding and byte probing stays
 * here in C. This mode is sample-scoped: an OPEN root stops transitive domain
 * propagation immediately, exactly as the work order requires.
 */

#define CD_MAX_IMAGES 64
#define CD_MAX_FUNCS 4096
#define CD_MAX_PROVED 4096
#define CD_MAX_TABLES 512
#define CD_MAX_SITES 64
#define CD_MAX_EDGES 4096

typedef struct {
    char id[64], path[512];
    uint32_t base, declared_size;
    uint8_t *bytes, *code_mask;
    size_t size;
} CDImage;

typedef struct {
    int image;
    uint32_t entry, end;
    char name[128];
} CDFunc;

typedef struct { int image; uint32_t pc, target; } CDProved;
typedef struct { int image; uint32_t lo, hi; } CDTable;

typedef enum { CD_CALLER = 1, CD_LOCAL = 2, CD_RETURN = 3 } CDMode;

typedef struct {
    CDMode mode;
    char stratum[32], id[192];
    int root_image, site_image, reg;
    uint32_t root_entry, root_end, site_pc, breaker_pc;
    int32_t offset;
    int width;
} CDSite;

typedef struct {
    int image, owner_func, reg;
    uint32_t pc;
    char kind[16];
} CDEdge;

typedef struct {
    CDImage images[CD_MAX_IMAGES]; int nimages;
    CDFunc funcs[CD_MAX_FUNCS]; int nfuncs;
    CDProved proved[CD_MAX_PROVED]; int nproved;
    CDTable tables[CD_MAX_TABLES]; int ntables;
    CDSite sites[CD_MAX_SITES]; int nsites;
    CDEdge edges[CD_MAX_EDGES]; int nedges;
} CDWorld;

static void cd_die(const char *what, const char *detail)
{
    fprintf(stderr, "caller-domain pilot: %s%s%s\n", what,
            detail ? ": " : "", detail ? detail : "");
    exit(2);
}

static int cd_image_index(const CDWorld *w, const char *id)
{
    for (int i = 0; i < w->nimages; i++)
        if (!strcmp(w->images[i].id, id)) return i;
    return -1;
}

static int cd_func_index(const CDWorld *w, int image, uint32_t entry)
{
    for (int i = 0; i < w->nfuncs; i++)
        if (w->funcs[i].image == image && w->funcs[i].entry == entry) return i;
    return -1;
}

static uint32_t cd_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t cd_word(const CDWorld *w, int image, uint32_t pc)
{
    const CDImage *im = &w->images[image];
    if (pc < im->base || (uint64_t)(pc - im->base) + 4 > im->size)
        cd_die("instruction outside image", im->id);
    return cd_le32(im->bytes + (pc - im->base));
}

static int cd_def_reg(uint32_t word)
{
    uint32_t op = word >> 26;
    if (op == 0) {
        uint32_t fn = word & 63;
        if (fn == 8) return -1;                         /* jr */
        if (fn == 9) return (word >> 11) & 31;          /* jalr link */
        if (fn == 12 || fn == 13) return -1;            /* syscall/break */
        return (word >> 11) & 31;
    }
    if (op == 2) return -1;
    if (op == 3) return 31;
    if ((op >= 4 && op <= 7) || op == 1 || op == 0x28 || op == 0x29 ||
        op == 0x2a || op == 0x2b || op == 0x2e)
        return -1;
    return (word >> 16) & 31;
}

static int cd_is_proved_pc(const CDWorld *w, int image, uint32_t pc)
{
    for (int i = 0; i < w->nproved; i++)
        if (w->proved[i].image == image && w->proved[i].pc == pc) return 1;
    return 0;
}

static int cd_bad_local_ra_definition(const CDWorld *w, const CDFunc *f)
{
    for (uint32_t pc = f->entry; pc + 4 <= f->end; pc += 4) {
        uint32_t x = cd_word(w, f->image, pc), op = x >> 26;
        if (cd_def_reg(x) != 31) continue;
        if (op == 3) continue;                            /* jal link */
        if (op == 0 && (x & 63) == 9) continue;          /* jalr link */
        if (op == 0x23 && ((x >> 21) & 31) == 29) continue; /* lw ra,sp */
        return 1;
    }
    return 0;
}

static int cd_images_can_coexist(const CDWorld *w, int source, int target)
{
    const char *s = w->images[source].id, *t = w->images[target].id;
    if (!strcmp(t, "SCUS_942_88")) return 1;
    if (!strcmp(s, "SCUS_942_88") || !strcmp(s, "MEMORY")) return 1;
    if (!strncmp(s, "LEVEL", 5) && !strncmp(t, "LEVEL", 5))
        return source == target;                         /* same swapped region */
    return source == target;
}

static int cd_edge_relevant(const CDWorld *w, const CDEdge *e, int root_image)
{
    return cd_images_can_coexist(w, e->image, root_image);
}

static int cd_table_byte(const CDWorld *w, int image, uint32_t va)
{
    for (int i = 0; i < w->ntables; i++)
        if (w->tables[i].image == image && va >= w->tables[i].lo &&
            va < w->tables[i].hi) return 1;
    return 0;
}

static void cd_json_string(const char *s)
{
    putchar('"');
    for (; *s; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') { putchar('\\'); putchar(c); }
        else if (c == '\n') fputs("\\n", stdout);
        else if (c == '\r') fputs("\\r", stdout);
        else if (c == '\t') fputs("\\t", stdout);
        else if (c < 0x20) printf("\\u%04x", c);
        else putchar(c);
    }
    putchar('"');
}

static void cd_read_manifest(const char *path, CDWorld *w)
{
    FILE *f = fopen(path, "r");
    if (!f) cd_die("cannot open manifest", path);
    char line[1400];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n') continue;
        char kind[32];
        if (sscanf(line, "%31s", kind) != 1) continue;
        if (!strcmp(kind, "VERSION")) {
            int version = 0;
            if (sscanf(line, "VERSION %d", &version) != 1 || version != 1)
                cd_die("unsupported manifest version", line);
        } else if (!strcmp(kind, "IMAGE")) {
            if (w->nimages >= CD_MAX_IMAGES) cd_die("too many images", NULL);
            CDImage *x = &w->images[w->nimages++]; unsigned base, size;
            if (sscanf(line, "IMAGE %63s %511s %x %u", x->id, x->path,
                       &base, &size) != 4) cd_die("bad IMAGE line", line);
            x->base = base; x->declared_size = size;
        } else if (!strcmp(kind, "FUNC")) {
            if (w->nfuncs >= CD_MAX_FUNCS) cd_die("too many functions", NULL);
            char image[64]; unsigned lo, hi; CDFunc *x = &w->funcs[w->nfuncs];
            if (sscanf(line, "FUNC %63s %x %x %127s", image, &lo, &hi,
                       x->name) != 4) cd_die("bad FUNC line", line);
            x->image = cd_image_index(w, image);
            if (x->image < 0) cd_die("FUNC names unknown image", image);
            x->entry = lo; x->end = hi; w->nfuncs++;
        } else if (!strcmp(kind, "PROVED")) {
            if (w->nproved >= CD_MAX_PROVED) cd_die("too many proved edges", NULL);
            char image[64]; unsigned pc, target;
            if (sscanf(line, "PROVED %63s %x %x", image, &pc, &target) != 3)
                cd_die("bad PROVED line", line);
            CDProved *x = &w->proved[w->nproved++];
            x->image = cd_image_index(w, image); x->pc = pc; x->target = target;
            if (x->image < 0) cd_die("PROVED names unknown image", image);
        } else if (!strcmp(kind, "TABLE")) {
            if (w->ntables >= CD_MAX_TABLES) cd_die("too many table ranges", NULL);
            char image[64]; unsigned lo, hi;
            if (sscanf(line, "TABLE %63s %x %x", image, &lo, &hi) != 3)
                cd_die("bad TABLE line", line);
            CDTable *x = &w->tables[w->ntables++];
            x->image = cd_image_index(w, image); x->lo = lo; x->hi = hi;
            if (x->image < 0 || hi <= lo) cd_die("invalid TABLE line", line);
        } else if (!strcmp(kind, "SITE")) {
            if (w->nsites >= CD_MAX_SITES) cd_die("too many sites", NULL);
            char mode[32], root_image[64], site_image[64];
            unsigned re, rh, spc, bpc; int off, width, reg;
            CDSite *x = &w->sites[w->nsites];
            if (sscanf(line,
                       "SITE %31s %31s %191s %63s %x %x %63s %x %d %d %d %x",
                       mode, x->stratum, x->id, root_image, &re, &rh,
                       site_image, &spc, &off, &width, &reg, &bpc) != 12)
                cd_die("bad SITE line", line);
            x->mode = !strcmp(mode, "CALLER") ? CD_CALLER :
                      !strcmp(mode, "LOCAL") ? CD_LOCAL :
                      !strcmp(mode, "RETURN") ? CD_RETURN : 0;
            x->root_image = cd_image_index(w, root_image);
            x->site_image = cd_image_index(w, site_image);
            x->root_entry = re; x->root_end = rh; x->site_pc = spc;
            x->offset = off; x->width = width; x->reg = reg; x->breaker_pc = bpc;
            if (!x->mode || x->root_image < 0 || x->site_image < 0)
                cd_die("SITE names invalid mode/image", line);
            w->nsites++;
        } else {
            cd_die("unknown manifest record", kind);
        }
    }
    fclose(f);

    for (int i = 0; i < w->nimages; i++) {
        CDImage *im = &w->images[i];
        FILE *g = fopen(im->path, "rb");
        if (!g) cd_die("cannot open image", im->path);
        if (fseek(g, 0, SEEK_END) || (im->size = (size_t)ftell(g)) == (size_t)-1 ||
            fseek(g, 0, SEEK_SET)) cd_die("cannot size image", im->path);
        if (im->size != im->declared_size) cd_die("image size differs from pin", im->id);
        im->bytes = malloc(im->size ? im->size : 1);
        im->code_mask = calloc(im->size ? im->size : 1, 1);
        if (!im->bytes || !im->code_mask) cd_die("out of memory", NULL);
        if (fread(im->bytes, 1, im->size, g) != im->size)
            cd_die("short image read", im->path);
        fclose(g);
    }
    for (int i = 0; i < w->nfuncs; i++) {
        CDFunc *fn = &w->funcs[i]; CDImage *im = &w->images[fn->image];
        if (fn->entry < im->base || fn->end < fn->entry ||
            (uint64_t)(fn->end - im->base) > im->size)
            cd_die("function outside image", fn->name);
        memset(im->code_mask + (fn->entry - im->base), 1, fn->end - fn->entry);
    }
}

static void cd_collect_edges(CDWorld *w)
{
    for (int fi = 0; fi < w->nfuncs; fi++) {
        CDFunc *f = &w->funcs[fi];
        int bad_ra = cd_bad_local_ra_definition(w, f);
        for (uint32_t pc = f->entry; pc + 4 <= f->end; pc += 4) {
            uint32_t x = cd_word(w, f->image, pc);
            if ((x >> 26) != 0) continue;
            int fn = x & 63, rs = (x >> 21) & 31;
            if (fn != 8 && fn != 9) continue;
            if (fn == 8 && rs == 31 && !bad_ra) continue; /* proved ordinary return shape */
            if (cd_is_proved_pc(w, f->image, pc)) continue;
            if (w->nedges >= CD_MAX_EDGES) cd_die("too many unproved edges", NULL);
            CDEdge *e = &w->edges[w->nedges++];
            e->image = f->image; e->owner_func = fi; e->pc = pc; e->reg = rs;
            snprintf(e->kind, sizeof e->kind, "%s", fn == 9 ? "jalr" : "jr");
        }
    }
}

static int cd_print_direct_callers(const CDWorld *w, int root_image, uint32_t entry)
{
    int first = 1, count = 0;
    putchar('[');
    for (int fi = 0; fi < w->nfuncs; fi++) {
        const CDFunc *f = &w->funcs[fi];
        if (!cd_images_can_coexist(w, f->image, root_image)) continue;
        for (uint32_t pc = f->entry; pc + 4 <= f->end; pc += 4) {
            uint32_t x = cd_word(w, f->image, pc), op = x >> 26;
            if (op != 2 && op != 3) continue;
            uint32_t target = ((pc + 4) & 0xf0000000u) | ((x & 0x03ffffffu) << 2);
            if (target != entry) continue;
            if (!strcmp(w->images[root_image].id, "SCUS_942_88") &&
                strcmp(w->images[f->image].id, "SCUS_942_88") && target >= 0x800b0000u)
                continue;
            printf("%s{\"image\":", first ? "" : ",");
            cd_json_string(w->images[f->image].id);
            printf(",\"pc\":\"0x%08x\",\"kind\":\"%s\",\"owner\":",
                   pc, op == 3 ? "jal" : "j");
            cd_json_string(f->name); putchar('}'); first = 0; count++;
        }
    }
    putchar(']');
    return count;
}

static int cd_print_proved_callers(const CDWorld *w, int root_image, uint32_t entry)
{
    int first = 1, count = 0; putchar('[');
    for (int i = 0; i < w->nproved; i++) {
        const CDProved *p = &w->proved[i];
        if (p->target != entry || !cd_images_can_coexist(w, p->image, root_image)) continue;
        printf("%s{\"image\":", first ? "" : ","); cd_json_string(w->images[p->image].id);
        printf(",\"pc\":\"0x%08x\",\"target\":\"0x%08x\"}", p->pc, p->target);
        first = 0; count++;
    }
    putchar(']'); return count;
}

static int cd_print_unproved_edges(const CDWorld *w, int root_image)
{
    int first = 1, count = 0; putchar('[');
    for (int i = 0; i < w->nedges; i++) {
        const CDEdge *e = &w->edges[i];
        if (!cd_edge_relevant(w, e, root_image)) continue;
        const CDFunc *owner = &w->funcs[e->owner_func];
        printf("%s{\"image\":", first ? "" : ","); cd_json_string(w->images[e->image].id);
        printf(",\"pc\":\"0x%08x\",\"kind\":\"%s\",\"register\":\"%s\",\"owner\":",
               e->pc, e->kind, REGS[e->reg]); cd_json_string(owner->name); putchar('}');
        first = 0; count++;
    }
    putchar(']'); return count;
}

static int cd_print_address_taken(const CDWorld *w, int root_image, uint32_t entry)
{
    int first = 1, count = 0; putchar('[');
    for (int ii = 0; ii < w->nimages; ii++) {
        const CDImage *im = &w->images[ii];
        if (!cd_images_can_coexist(w, ii, root_image)) continue;
        for (size_t off = 0; off + 4 <= im->size; off++) {
            if (im->code_mask[off] || cd_table_byte(w, ii, im->base + (uint32_t)off)) continue;
            if (cd_le32(im->bytes + off) != entry) continue;
            printf("%s{\"image\":", first ? "" : ","); cd_json_string(im->id);
            printf(",\"va\":\"0x%08x\",\"file_offset\":%zu,\"kind\":\"literal_data_word\"}",
                   im->base + (uint32_t)off, off);
            first = 0; count++;
        }
        for (int fi = 0; fi < w->nfuncs; fi++) {
            const CDFunc *f = &w->funcs[fi];
            if (f->image != ii) continue;
            for (uint32_t pc = f->entry; pc + 4 <= f->end; pc += 4) {
                uint32_t a = cd_word(w, ii, pc);
                if ((a >> 26) != 0x0f) continue;
                int r = (a >> 16) & 31;
                for (int step = 1; step <= 8 && pc + (uint32_t)step * 4 < f->end; step++) {
                    uint32_t qpc = pc + (uint32_t)step * 4, b = cd_word(w, ii, qpc);
                    uint32_t op = b >> 26; int rs = (b >> 21) & 31, rt = (b >> 16) & 31;
                    if ((op == 0x09 || op == 0x0d) && rs == r && rt == r) {
                        uint32_t v = (a & 0xffffu) << 16;
                        v = op == 0x09 ? v + (uint32_t)(int32_t)(int16_t)(b & 0xffffu)
                                       : v | (b & 0xffffu);
                        if (v == entry) {
                            printf("%s{\"image\":", first ? "" : ","); cd_json_string(im->id);
                            printf(",\"va\":\"0x%08x\",\"pair_end_pc\":\"0x%08x\","
                                   "\"kind\":\"lui_%s_materialization\"}",
                                   pc, qpc, op == 0x09 ? "addiu" : "ori");
                            first = 0; count++;
                        }
                        break;
                    }
                    if (cd_def_reg(b) == r) break;
                }
            }
        }
    }
    putchar(']'); return count;
}

static int cd_root_open(const CDWorld *w, int root_image, uint32_t entry)
{
    for (int i = 0; i < w->nedges; i++)
        if (cd_edge_relevant(w, &w->edges[i], root_image)) return 1;
    for (int ii = 0; ii < w->nimages; ii++) {
        const CDImage *im = &w->images[ii];
        if (!cd_images_can_coexist(w, ii, root_image)) continue;
        for (size_t off = 0; off + 4 <= im->size; off++)
            if (!im->code_mask[off] && !cd_table_byte(w, ii, im->base + (uint32_t)off) &&
                cd_le32(im->bytes + off) == entry) return 1;
        for (int fi = 0; fi < w->nfuncs; fi++) {
            const CDFunc *f = &w->funcs[fi]; if (f->image != ii) continue;
            for (uint32_t pc = f->entry; pc + 4 <= f->end; pc += 4) {
                uint32_t a = cd_word(w, ii, pc); if ((a >> 26) != 0x0f) continue;
                int r = (a >> 16) & 31;
                for (int step = 1; step <= 8 && pc + (uint32_t)step * 4 < f->end; step++) {
                    uint32_t b = cd_word(w, ii, pc + (uint32_t)step * 4), op = b >> 26;
                    int rs = (b >> 21) & 31, rt = (b >> 16) & 31;
                    if ((op == 0x09 || op == 0x0d) && rs == r && rt == r) {
                        uint32_t v = (a & 0xffffu) << 16;
                        v = op == 0x09 ? v + (uint32_t)(int32_t)(int16_t)(b & 0xffffu)
                                       : v | (b & 0xffffu);
                        if (v == entry) return 1;
                        break;
                    }
                    if (cd_def_reg(b) == r) break;
                }
            }
        }
    }
    return 0;
}

static const char *cd_local_wall(const CDWorld *w, const CDSite *s,
                                 uint32_t *word, uint32_t *aux_pc,
                                 uint32_t *aux_word)
{
    *word = cd_word(w, s->root_image, s->breaker_pc);
    *aux_pc = *aux_word = 0;
    uint32_t op = *word >> 26, rs = (*word >> 21) & 31;
    if (op == 0x21) return "local_signed_load_not_caller_argument";
    if (op == 0x23 && rs == 29) {
        for (uint32_t pc = s->root_entry; pc < s->breaker_pc; pc += 4) {
            uint32_t x = cd_word(w, s->root_image, pc);
            if ((x >> 26) == 0x09 && ((x >> 21) & 31) == 29 &&
                ((x >> 16) & 31) == 29 && (int16_t)(x & 0xffff) < 0) {
                int frame = -(int16_t)(x & 0xffff), slot = (int16_t)(*word & 0xffff);
                *aux_pc = pc; *aux_word = x;
                return slot < frame + 16 ? "local_frame_slot_not_stack_argument"
                                         : "stack_argument_domain_requires_closed_callers";
            }
        }
        return "stack_base_adjustment_unrecovered";
    }
    if (op == 0 && ((*word & 63) == 0 || (*word & 63) == 2 ||
                    (*word & 63) == 3 || (*word & 63) == 0x21))
        return "local_definition_replaces_argument_register";
    return "local_source_class_not_in_caller_domain_whitelist";
}

static const char *cd_return_wall(const CDWorld *w, const CDSite *s,
                                  uint32_t *word, uint32_t *aux_pc,
                                  uint32_t *aux_word)
{
    *aux_pc = *aux_word = 0;
    if (s->site_pc >= 4) {
        uint32_t call = cd_word(w, s->site_image, s->site_pc - 4);
        if ((call >> 26) == 3) {
            *word = call;
            return "delay_slot_pre_call_value_not_return_domain";
        }
    }
    *word = cd_word(w, s->root_image, s->breaker_pc);
    /* The three contact-spawn rows enter a four-word stack-argument shim and
     * fall through into contact_object_spawn.  Following that fallthrough is
     * mandatory, but its sole return copies s0 into v0.  s0 is not bounded by
     * the pilot whitelist, so the exact copy is the breaker. */
    if (((*word >> 26) == 0) && ((*word & 63) == 0x21) &&
        (((*word >> 11) & 31) == 2) && (((*word >> 21) & 31) == 16))
        return "return_value_depends_on_unproved_s0_after_fallthrough_entry";
    return "return_definition_not_in_domain_whitelist";
}

static int cd_caller_domain_self_test(void)
{
    uint32_t lh = 0x84840000u, sll = 0x00042080u, move = 0x02001021u;
    if ((lh >> 26) != 0x21 || cd_def_reg(lh) != 4) return 1;
    if ((sll >> 26) != 0 || (sll & 63) != 0 || cd_def_reg(sll) != 4) return 1;
    if ((move >> 26) != 0 || (move & 63) != 0x21 || cd_def_reg(move) != 2) return 1;
    uint32_t jal = 0x0c013043u;
    if ((jal >> 26) != 3 || cd_def_reg(jal) != 31) return 1;
    puts("{\"schema\":\"abl-phase4-caller-domain-c-selftest/1\","
         "\"passed\":4,\"failed\":0,\"verdict\":true}");
    return 0;
}

static int cd_caller_domain_pilot(const char *manifest)
{
    CDWorld w; memset(&w, 0, sizeof w);
    cd_read_manifest(manifest, &w);
    cd_collect_edges(&w);

    printf("{\n \"schema\":\"abl-phase4-caller-domain-c-probe/1\",\n"
           " \"universe\":{\"images\":%d,\"functions\":%d,"
           "\"proved_indirect_edges\":%d,\"proved_table_ranges\":%d,"
           "\"pilot_sites\":%d,\"unproved_indirect_edges\":%d},\n",
           w.nimages, w.nfuncs, w.nproved, w.ntables, w.nsites, w.nedges);

    printf(" \"closure_roots\":[");
    int rfirst = 1;
    for (int si = 0; si < w.nsites; si++) {
        CDSite *s = &w.sites[si]; if (s->mode != CD_CALLER) continue;
        int duplicate = 0;
        for (int j = 0; j < si; j++)
            if (w.sites[j].mode == CD_CALLER &&
                w.sites[j].root_image == s->root_image &&
                w.sites[j].root_entry == s->root_entry) duplicate = 1;
        if (duplicate) continue;
        int fi = cd_func_index(&w, s->root_image, s->root_entry);
        int open = cd_root_open(&w, s->root_image, s->root_entry);
        printf("%s{\"key\":", rfirst ? "" : ",");
        char key[128]; snprintf(key, sizeof key, "%s:0x%08x",
                                w.images[s->root_image].id, s->root_entry);
        cd_json_string(key); printf(",\"image\":"); cd_json_string(w.images[s->root_image].id);
        printf(",\"entry\":\"0x%08x\",\"end\":\"0x%08x\",\"name\":",
               s->root_entry, s->root_end);
        cd_json_string(fi >= 0 ? w.funcs[fi].name : "-");
        printf(",\"direct_callers\":"); int direct = cd_print_direct_callers(&w, s->root_image, s->root_entry);
        printf(",\"proved_indirect_callers\":"); int proved = cd_print_proved_callers(&w, s->root_image, s->root_entry);
        printf(",\"address_taken_outside_proved_tables\":"); int refs = cd_print_address_taken(&w, s->root_image, s->root_entry);
        printf(",\"relevant_unproved_indirect_edges\":"); int unproved = cd_print_unproved_edges(&w, s->root_image);
        printf(",\"counts\":{\"direct\":%d,\"proved_indirect\":%d,"
               "\"address_taken\":%d,\"unproved_indirect\":%d},"
               "\"classification\":\"%s\",\"transitive_depth_reached\":0,"
               "\"transitive_expansion\":\"%s\"}",
               direct, proved, refs, unproved, open ? "OPEN" : "CLOSED",
               open ? "stopped_at_open_root" : "root_closed_requires_stage_b");
        rfirst = 0;
    }
    printf("],\n \"sites\":[");
    int decided = 0, open_sites = 0;
    for (int i = 0; i < w.nsites; i++) {
        CDSite *s = &w.sites[i];
        printf("%s{\"id\":", i ? "," : ""); cd_json_string(s->id);
        printf(",\"stratum\":"); cd_json_string(s->stratum);
        printf(",\"mode\":\"%s\",", s->mode == CD_CALLER ? "caller" :
               s->mode == CD_LOCAL ? "local" : "return");
        if (s->mode == CD_CALLER) {
            int open = cd_root_open(&w, s->root_image, s->root_entry);
            char key[128]; snprintf(key, sizeof key, "%s:0x%08x",
                                    w.images[s->root_image].id, s->root_entry);
            printf("\"closure_root\":"); cd_json_string(key);
            printf(",\"decided\":false,\"domain_status\":\"ABSENT\","
                   "\"wall\":\"%s\"", open ? "open_caller_set_poison" :
                   "closed_subgraph_domain_propagation_required");
            if (open) open_sites++;
        } else {
            uint32_t word = 0, apc = 0, aword = 0;
            const char *wall = s->mode == CD_LOCAL
                ? cd_local_wall(&w, s, &word, &apc, &aword)
                : cd_return_wall(&w, s, &word, &apc, &aword);
            printf("\"decided\":false,\"domain_status\":\"ABSENT\","
                   "\"wall\":"); cd_json_string(wall);
            printf(",\"breaking_instruction\":{\"pc\":\"0x%08x\","
                   "\"word\":\"0x%08x\"}",
                   (s->mode == CD_RETURN && s->site_pc >= 4 &&
                    (cd_word(&w, s->site_image, s->site_pc - 4) >> 26) == 3)
                       ? s->site_pc - 4 : s->breaker_pc, word);
            if (apc) printf(",\"supporting_instruction\":{\"pc\":\"0x%08x\","
                            "\"word\":\"0x%08x\"}", apc, aword);
        }
        putchar('}');
    }
    printf("],\n \"derived_counts\":{\"decided\":%d,"
           "\"undecided\":%d,\"open_caller_set_poison\":%d},\n"
           " \"depth_cap\":3,\"widening_cap\":32,"
           "\"full_corpus_pass_performed\":false\n}\n",
           decided, w.nsites - decided, open_sites);

    for (int i = 0; i < w.nimages; i++) {
        free(w.images[i].bytes); free(w.images[i].code_mask);
    }
    return 0;
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--caller-domain-self-test"))
        return cd_caller_domain_self_test();
    if (argc == 3 && !strcmp(argv[1], "--caller-domain-pilot"))
        return cd_caller_domain_pilot(argv[2]);
    fprintf(stderr, "usage: %s --caller-domain-self-test | "
                    "--caller-domain-pilot MANIFEST\\n", argv[0]);
    return 2;
}
