/* Independent Stage-A implementation for the four-root address-taken pilot.
 *
 * It intentionally shares no source with phase4_address_taken_pilot.c.  The
 * only question it answers is the fixed Stage-A occurrence set: every aligned
 * literal word equal to a root and every code-range lui/addiu or lui/ori
 * materialisation of that root.  The Python driver compares exact tuples, not
 * merely totals, and fails closed on any disagreement.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define XI_MAX 64
#define XR_MAX 4096
#define XT_MAX 16
#define XO_MAX 16384

typedef struct {
    char label[64], filename[512];
    uint32_t origin, expected;
    unsigned char *raw, *executable;
    size_t length;
} XI;

typedef struct { int image; uint32_t first, after; int executable; } XR;
typedef struct { int image; uint32_t entry; } XT;

typedef struct {
    int target, image, form;
    uint32_t at, second;
} XO;

typedef struct {
    XI image[XI_MAX]; int images;
    XR range[XR_MAX]; int ranges;
    XT target[XT_MAX]; int targets;
    XO found[XO_MAX]; int found_count;
} XW;

static void fail(const char *why, const char *detail)
{
    fprintf(stderr, "address-taken independent sweep: %s%s%s\n", why,
            detail ? ": " : "", detail ? detail : "");
    exit(2);
}

static uint32_t get32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static int image_number(const XW *w, const char *name)
{
    int i;
    for (i = 0; i < w->images; i++)
        if (!strcmp(w->image[i].label, name)) return i;
    return -1;
}

static int destination(uint32_t insn)
{
    uint32_t op = insn >> 26, fn;
    if (op == 0u) {
        fn = insn & 63u;
        if (fn == 8u || fn == 12u || fn == 13u) return -1;
        return (int)((insn >> 11) & 31u);
    }
    if (op == 2u) return -1;
    if (op == 3u) return 31;
    if (op == 1u || (op >= 4u && op <= 7u) ||
        op == 0x28u || op == 0x29u || op == 0x2au ||
        op == 0x2bu || op == 0x2eu) return -1;
    return (int)((insn >> 16) & 31u);
}

static void read_input(const char *name, XW *w)
{
    FILE *f = fopen(name, "r"); char line[1600], tag[32];
    if (!f) fail("cannot open manifest", name);
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n' || sscanf(line, "%31s", tag) != 1)
            continue;
        if (!strcmp(tag, "VERSION") || !strcmp(tag, "TABLE") ||
            !strcmp(tag, "PROVED")) continue;
        if (!strcmp(tag, "IMAGE")) {
            XI *x; unsigned base, size; char ignored[64];
            if (w->images >= XI_MAX) fail("too many images", NULL);
            x = &w->image[w->images++];
            if (sscanf(line, "IMAGE %63s %511s %x %u %63s", x->label,
                       x->filename, &base, &size, ignored) != 5)
                fail("bad IMAGE", line);
            x->origin = base; x->expected = size;
        } else if (!strcmp(tag, "RANGE")) {
            XR *r; char image[64], kind[32], ignored[160]; unsigned lo, hi;
            if (w->ranges >= XR_MAX) fail("too many ranges", NULL);
            if (sscanf(line, "RANGE %63s %x %x %31s %159s", image, &lo,
                       &hi, kind, ignored) != 5) fail("bad RANGE", line);
            r = &w->range[w->ranges++]; r->image = image_number(w, image);
            r->first = lo; r->after = hi;
            r->executable = !strcmp(kind, "code") || !strcmp(kind, "thunk");
            if (r->image < 0 || hi <= lo) fail("invalid RANGE", line);
        } else if (!strcmp(tag, "ROOT")) {
            XT *t; char image[64], witness_image[64]; unsigned entry, witness;
            if (w->targets >= XT_MAX) fail("too many targets", NULL);
            if (sscanf(line, "ROOT %63s %x %63s %x", image, &entry,
                       witness_image, &witness) != 4) fail("bad ROOT", line);
            (void)witness_image; (void)witness;
            t = &w->target[w->targets++]; t->image = image_number(w, image);
            t->entry = entry; if (t->image < 0) fail("unknown ROOT image", image);
        } else fail("unknown record", tag);
    }
    fclose(f);

    for (int i = 0; i < w->images; i++) {
        XI *x = &w->image[i]; FILE *g = fopen(x->filename, "rb"); long n;
        if (!g) fail("cannot open image", x->filename);
        if (fseek(g, 0, SEEK_END) || (n = ftell(g)) < 0 || fseek(g, 0, SEEK_SET))
            fail("cannot size image", x->filename);
        x->length = (size_t)n;
        if (x->length != x->expected) fail("image size mismatch", x->label);
        x->raw = malloc(x->length ? x->length : 1);
        x->executable = calloc(x->length ? x->length : 1, 1);
        if (!x->raw || !x->executable) fail("out of memory", NULL);
        if (fread(x->raw, 1, x->length, g) != x->length)
            fail("short image read", x->filename);
        fclose(g);
    }
    for (int i = 0; i < w->ranges; i++) {
        XR *r = &w->range[i]; XI *x = &w->image[r->image];
        if (r->first < x->origin || r->after < r->first ||
            (uint64_t)(r->after - x->origin) > x->length)
            fail("range outside image", x->label);
        if (r->executable)
            memset(x->executable + r->first - x->origin, 1, r->after - r->first);
    }
}

static int duplicate(const XW *w, const XO *o)
{
    for (int i = 0; i < w->found_count; i++) {
        const XO *p = &w->found[i];
        if (p->target == o->target && p->image == o->image && p->form == o->form &&
            p->at == o->at && p->second == o->second) return 1;
    }
    return 0;
}

static void remember(XW *w, int target, int image, int form,
                     uint32_t at, uint32_t second)
{
    XO o; o.target = target; o.image = image; o.form = form;
    o.at = at; o.second = second;
    if (duplicate(w, &o)) return;
    if (w->found_count >= XO_MAX) fail("too many occurrences", NULL);
    w->found[w->found_count++] = o;
}

static void sweep(XW *w)
{
    for (int t = 0; t < w->targets; t++) {
        for (int i = 0; i < w->images; i++) {
            XI *x = &w->image[i];
            for (size_t off = 0; off + 4 <= x->length; off += 4)
                if (get32(x->raw + off) == w->target[t].entry)
                    remember(w, t, i, 1, x->origin + (uint32_t)off, 0);
            for (size_t off = 0; off + 4 <= x->length; off += 4) {
                uint32_t first = get32(x->raw + off); int reg;
                if (!x->executable[off] || (first >> 26) != 0x0fu) continue;
                reg = (int)((first >> 16) & 31u);
                for (int gap = 1; gap <= 8; gap++) {
                    size_t q = off + (size_t)gap * 4; uint32_t second, op, made;
                    int rs, rt;
                    if (q + 4 > x->length || !x->executable[q]) break;
                    second = get32(x->raw + q); op = second >> 26;
                    rs = (int)((second >> 21) & 31u);
                    rt = (int)((second >> 16) & 31u);
                    if ((op == 0x09u || op == 0x0du) && rs == reg && rt == reg) {
                        made = (first & 0xffffu) << 16;
                        if (op == 0x09u)
                            made += (uint32_t)(int32_t)(int16_t)(second & 0xffffu);
                        else made |= second & 0xffffu;
                        if (made == w->target[t].entry)
                            remember(w, t, i, op == 0x09u ? 2 : 3,
                                     x->origin + (uint32_t)off,
                                     x->origin + (uint32_t)q);
                        break;
                    }
                    if (destination(second) == reg) break;
                }
            }
        }
    }
}

static void quote(const char *s)
{
    putchar('"');
    while (*s) { if (*s == '"' || *s == '\\') putchar('\\'); putchar(*s++); }
    putchar('"');
}

static const char *form_name(int form)
{
    return form == 1 ? "aligned_literal_word" :
           form == 2 ? "lui_addiu_materialization" : "lui_ori_materialization";
}

static int run(const char *manifest)
{
    XW w; memset(&w, 0, sizeof w); read_input(manifest, &w); sweep(&w);
    printf("{\n \"schema\":\"abl-phase4-address-taken-independent-c/1\",\n"
           " \"roots\":[");
    for (int t = 0; t < w.targets; t++) {
        char key[128]; int first = 1, count = 0;
        snprintf(key, sizeof key, "%s:0x%08x", w.image[w.target[t].image].label,
                 w.target[t].entry);
        printf("%s{\"key\":", t ? "," : ""); quote(key);
        printf(",\"occurrences\":[");
        for (int i = 0; i < w.found_count; i++) {
            XO *o = &w.found[i]; if (o->target != t) continue;
            printf("%s{\"image\":", first ? "" : ","); quote(w.image[o->image].label);
            printf(",\"va\":\"0x%08x\",\"kind\":", o->at); quote(form_name(o->form));
            if (o->second) printf(",\"pair_end_pc\":\"0x%08x\"", o->second);
            putchar('}'); first = 0; count++;
        }
        printf("],\"occurrence_count\":%d}", count);
    }
    printf("],\n \"aligned_word_rule\":\"file offsets divisible by four\"\n}\n");
    for (int i = 0; i < w.images; i++) {
        free(w.image[i].raw); free(w.image[i].executable);
    }
    return 0;
}

static int selftest(void)
{
    uint32_t literal = 0x800b3f08u;
    uint32_t lui = 0x3c01800bu;
    uint32_t addiu = 0x24213f08u;
    uint32_t ori = 0x34213f08u;
    int passed = 0;
    if (get32((const unsigned char *)"\x08\x3f\x0b\x80") == literal) passed++; else return 1;
    if (((lui & 0xffffu) << 16) + (uint32_t)(int32_t)(int16_t)(addiu & 0xffffu)
        == literal) passed++; else return 1;
    if (((lui & 0xffffu) << 16 | (ori & 0xffffu)) == literal) passed++; else return 1;
    if (destination(0x00400008u) == -1 && destination(addiu) == 1) passed++; else return 1;
    printf("{\"schema\":\"abl-phase4-address-taken-independent-selftest/1\","
           "\"passed\":%d,\"failed\":0,\"verdict\":true}\n", passed);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--self-test")) return selftest();
    if (argc == 2) return run(argv[1]);
    fprintf(stderr, "usage: %s MANIFEST | --self-test\n", argv[0]);
    return 2;
}
