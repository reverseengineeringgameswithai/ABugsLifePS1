/* Independent minimal implementation for the fixed Phase-4 caller-domain
 * pilot. It intentionally shares no code with the primary C probe.
 *
 * This cross-check answers only the pilot's deciding facts:
 *   - does a caller-dependent root coexist with at least one unproved jr/jalr;
 *   - is a purported caller source actually a local signed load, local frame
 *     slot, or local arithmetic definition;
 *   - is a purported return use in the call's delay slot, or does the followed
 *     fallthrough return copy an unproved saved register?
 *
 * It is deliberately less featureful than the primary implementation.  Any
 * disagreement fails the Python consumer closed.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define X_IMAGES 64
#define X_FUNCS 4096
#define X_PROVED 4096
#define X_SITES 64

typedef struct {
    char id[64], path[512];
    uint32_t base, expected_size;
    uint8_t *data;
    size_t size;
} XImage;

typedef struct { int image; uint32_t lo, hi; char name[128]; } XFunc;
typedef struct { int image; uint32_t pc; } XProved;

typedef struct {
    char mode[16], stratum[32], id[192];
    int root_image, site_image, reg;
    uint32_t root_lo, root_hi, site_pc, breaker_pc;
    int offset, width;
} XSite;

typedef struct {
    XImage images[X_IMAGES]; int ni;
    XFunc funcs[X_FUNCS]; int nf;
    XProved proved[X_PROVED]; int np;
    XSite sites[X_SITES]; int ns;
} XWorld;

static void xdie(const char *why, const char *detail)
{
    fprintf(stderr, "caller-domain crosscheck: %s%s%s\n", why,
            detail ? ": " : "", detail ? detail : "");
    exit(2);
}

static int image_id(const XWorld *w, const char *id)
{
    for (int i = 0; i < w->ni; i++) if (!strcmp(w->images[i].id, id)) return i;
    return -1;
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t word_at(const XWorld *w, int im, uint32_t pc)
{
    const XImage *x = &w->images[im];
    if (pc < x->base || (uint64_t)(pc - x->base) + 4 > x->size)
        xdie("pc outside image", x->id);
    return le32(x->data + pc - x->base);
}

static int coexist(const XWorld *w, int src, int dst)
{
    const char *s = w->images[src].id, *d = w->images[dst].id;
    if (!strcmp(d, "SCUS_942_88")) return 1;
    if (!strcmp(s, "SCUS_942_88") || !strcmp(s, "MEMORY")) return 1;
    if (!strncmp(s, "LEVEL", 5) && !strncmp(d, "LEVEL", 5)) return src == dst;
    return src == dst;
}

static int proved(const XWorld *w, int im, uint32_t pc)
{
    for (int i = 0; i < w->np; i++)
        if (w->proved[i].image == im && w->proved[i].pc == pc) return 1;
    return 0;
}

static void read_manifest(const char *path, XWorld *w)
{
    FILE *f = fopen(path, "r"); if (!f) xdie("cannot open manifest", path);
    char line[1400], tag[32];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n' || sscanf(line, "%31s", tag) != 1) continue;
        if (!strcmp(tag, "VERSION") || !strcmp(tag, "TABLE")) continue;
        if (!strcmp(tag, "IMAGE")) {
            if (w->ni >= X_IMAGES) xdie("too many images", NULL);
            XImage *x = &w->images[w->ni++]; unsigned b, n;
            if (sscanf(line, "IMAGE %63s %511s %x %u", x->id, x->path, &b, &n) != 4)
                xdie("bad IMAGE", line);
            x->base = b; x->expected_size = n;
        } else if (!strcmp(tag, "FUNC")) {
            if (w->nf >= X_FUNCS) xdie("too many funcs", NULL);
            char im[64]; unsigned lo, hi; XFunc *x = &w->funcs[w->nf];
            if (sscanf(line, "FUNC %63s %x %x %127s", im, &lo, &hi, x->name) != 4)
                xdie("bad FUNC", line);
            x->image = image_id(w, im); x->lo = lo; x->hi = hi;
            if (x->image < 0) xdie("unknown FUNC image", im);
            w->nf++;
        } else if (!strcmp(tag, "PROVED")) {
            if (w->np >= X_PROVED) xdie("too many proved edges", NULL);
            char im[64]; unsigned pc, ignored;
            if (sscanf(line, "PROVED %63s %x %x", im, &pc, &ignored) != 3)
                xdie("bad PROVED", line);
            XProved *x = &w->proved[w->np++]; x->image = image_id(w, im); x->pc = pc;
            if (x->image < 0) xdie("unknown PROVED image", im);
        } else if (!strcmp(tag, "SITE")) {
            if (w->ns >= X_SITES) xdie("too many sites", NULL);
            char ri[64], si[64]; unsigned lo, hi, pc, bp; XSite *x = &w->sites[w->ns];
            if (sscanf(line,
                       "SITE %15s %31s %191s %63s %x %x %63s %x %d %d %d %x",
                       x->mode, x->stratum, x->id, ri, &lo, &hi, si, &pc,
                       &x->offset, &x->width, &x->reg, &bp) != 12)
                xdie("bad SITE", line);
            x->root_image = image_id(w, ri); x->site_image = image_id(w, si);
            x->root_lo = lo; x->root_hi = hi; x->site_pc = pc; x->breaker_pc = bp;
            if (x->root_image < 0 || x->site_image < 0) xdie("unknown SITE image", line);
            w->ns++;
        } else xdie("unknown record", tag);
    }
    fclose(f);
    for (int i = 0; i < w->ni; i++) {
        XImage *x = &w->images[i]; FILE *g = fopen(x->path, "rb");
        if (!g) xdie("cannot open image", x->path);
        if (fseek(g, 0, SEEK_END)) xdie("seek failed", x->path);
        long n = ftell(g); if (n < 0 || fseek(g, 0, SEEK_SET)) xdie("size failed", x->path);
        x->size = (size_t)n;
        if (x->size != x->expected_size) xdie("image size drift", x->id);
        x->data = malloc(x->size ? x->size : 1); if (!x->data) xdie("oom", NULL);
        if (fread(x->data, 1, x->size, g) != x->size) xdie("short read", x->path);
        fclose(g);
    }
}

static int first_unproved_indirect(const XWorld *w, int root_image,
                                   int *out_image, uint32_t *out_pc)
{
    for (int fi = 0; fi < w->nf; fi++) {
        const XFunc *f = &w->funcs[fi]; if (!coexist(w, f->image, root_image)) continue;
        for (uint32_t pc = f->lo; pc + 4 <= f->hi; pc += 4) {
            uint32_t x = word_at(w, f->image, pc);
            if ((x >> 26) != 0) continue;
            int fn = x & 63, rs = (x >> 21) & 31;
            if (fn != 8 && fn != 9) continue;
            if (fn == 8 && rs == 31) continue;             /* independent simplification */
            if (proved(w, f->image, pc)) continue;
            *out_image = f->image; *out_pc = pc; return 1;
        }
    }
    return 0;
}

static const char *local_wall(const XWorld *w, const XSite *s,
                              uint32_t *pc, uint32_t *word)
{
    *pc = s->breaker_pc; *word = word_at(w, s->root_image, *pc);
    uint32_t op = *word >> 26, rs = (*word >> 21) & 31;
    if (op == 0x21) return "local_signed_load_not_caller_argument";
    if (op == 0x23 && rs == 29) {
        int slot = (int16_t)(*word & 0xffff);
        for (uint32_t q = s->root_lo; q < *pc; q += 4) {
            uint32_t z = word_at(w, s->root_image, q);
            if ((z >> 26) == 0x09 && ((z >> 21) & 31) == 29 &&
                ((z >> 16) & 31) == 29 && (int16_t)(z & 0xffff) < 0) {
                int frame = -(int16_t)(z & 0xffff);
                return slot < frame + 16 ? "local_frame_slot_not_stack_argument"
                                         : "stack_argument_domain_requires_closed_callers";
            }
        }
        return "stack_base_adjustment_unrecovered";
    }
    if (op == 0) return "local_definition_replaces_argument_register";
    return "local_source_class_not_in_caller_domain_whitelist";
}

static const char *return_wall(const XWorld *w, const XSite *s,
                               uint32_t *pc, uint32_t *word)
{
    if (s->site_pc >= 4) {
        uint32_t x = word_at(w, s->site_image, s->site_pc - 4);
        if ((x >> 26) == 3) {
            *pc = s->site_pc - 4; *word = x;
            return "delay_slot_pre_call_value_not_return_domain";
        }
    }
    *pc = s->breaker_pc; *word = word_at(w, s->root_image, *pc);
    if (((*word >> 26) == 0) && ((*word & 63) == 0x21) &&
        (((*word >> 11) & 31) == 2) && (((*word >> 21) & 31) == 16))
        return "return_value_depends_on_unproved_s0_after_fallthrough_entry";
    return "return_definition_not_in_domain_whitelist";
}

static void jstr(const char *s)
{
    putchar('"'); for (; *s; s++) { if (*s == '"' || *s == '\\') putchar('\\'); putchar(*s); }
    putchar('"');
}

static int selftest(void)
{
    uint32_t jr = 0x00400008u, ret = 0x03e00008u, jal = 0x0c013043u;
    if ((jr >> 26) || (jr & 63) != 8 || ((jr >> 21) & 31) != 2) return 1;
    if ((ret >> 26) || (ret & 63) != 8 || ((ret >> 21) & 31) != 31) return 1;
    if ((jal >> 26) != 3) return 1;
    puts("{\"schema\":\"abl-phase4-caller-domain-crosscheck-selftest/1\","
         "\"passed\":3,\"failed\":0,\"verdict\":true}");
    return 0;
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--self-test")) return selftest();
    if (argc != 2) {
        fprintf(stderr, "usage: %s MANIFEST | --self-test\n", argv[0]); return 2;
    }
    XWorld w; memset(&w, 0, sizeof w); read_manifest(argv[1], &w);
    printf("{\n \"schema\":\"abl-phase4-caller-domain-independent-c/1\",\n"
           " \"sites\":[");
    for (int i = 0; i < w.ns; i++) {
        XSite *s = &w.sites[i]; const char *wall; uint32_t pc = 0, word = 0;
        int witness_image = -1; uint32_t witness_pc = 0;
        if (!strcmp(s->mode, "CALLER")) {
            if (first_unproved_indirect(&w, s->root_image, &witness_image, &witness_pc))
                wall = "open_caller_set_poison";
            else wall = "closed_subgraph_domain_propagation_required";
        } else if (!strcmp(s->mode, "LOCAL")) wall = local_wall(&w, s, &pc, &word);
        else wall = return_wall(&w, s, &pc, &word);
        printf("%s{\"id\":", i ? "," : ""); jstr(s->id);
        printf(",\"decided\":false,\"wall\":"); jstr(wall);
        if (witness_image >= 0) {
            printf(",\"independent_witness\":{\"image\":"); jstr(w.images[witness_image].id);
            printf(",\"pc\":\"0x%08x\"}", witness_pc);
        } else if (pc) {
            printf(",\"independent_breaker\":{\"pc\":\"0x%08x\","
                   "\"word\":\"0x%08x\"}", pc, word);
        }
        putchar('}');
    }
    printf("],\n \"pilot_sites\":%d,\"depth_cap\":3\n}\n", w.ns);
    for (int i = 0; i < w.ni; i++) free(w.images[i].data);
    return 0;
}
