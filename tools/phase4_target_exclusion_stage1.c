/*
 * phase4_target_exclusion_stage1.c -- byte-level control-transfer attestor
 * for the target-exclusion Stage-0/1 freeze.
 *
 * Python owns immutable identities and selection.  This C program owns the
 * instruction facts: it reads each named image byte range, decodes the
 * requested jr/jalr, checks the target register, and records the delay slot.
 * A mismatch is fatal; a data word can therefore never enter the frozen code
 * universe merely because Python labelled it as an indirect transfer.
 */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_IMAGES 64

static const char *REGS[32] = {
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"
};

typedef struct {
    char id[64];
    char path[512];
    uint32_t base;
    uint8_t *bytes;
    size_t size;
} Image;

static Image IMAGES[MAX_IMAGES];
static size_t N_IMAGES;

static void fail(const char *message, const char *detail)
{
    fprintf(stderr, "target-exclusion stage1: %s%s%s\n", message,
            detail ? ": " : "", detail ? detail : "");
    exit(2);
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint8_t *slurp(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    uint8_t *out;
    long n;
    if (!f) fail("cannot open image", path);
    if (fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 || fseek(f, 0, SEEK_SET))
        fail("cannot size image", path);
    out = malloc((size_t)n ? (size_t)n : 1u);
    if (!out) fail("out of memory", NULL);
    if (n && fread(out, 1, (size_t)n, f) != (size_t)n)
        fail("cannot read image", path);
    if (fclose(f)) fail("cannot close image", path);
    *size = (size_t)n;
    return out;
}

static void json_string(const char *s)
{
    putchar('"');
    for (; *s; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') printf("\\%c", c);
        else if (c < 0x20) printf("\\u%04x", c);
        else putchar(c);
    }
    putchar('"');
}

static Image *find_image(const char *id)
{
    size_t i;
    for (i = 0; i < N_IMAGES; i++)
        if (strcmp(IMAGES[i].id, id) == 0) return &IMAGES[i];
    return NULL;
}

static void load_map(const char *path)
{
    FILE *f = fopen(path, "r");
    char id[64], rel[512], base_text[32];
    if (!f) fail("cannot open image map", path);
    while (fscanf(f, "%63s %511s %31s", id, rel, base_text) == 3) {
        Image *im;
        char *end = NULL;
        unsigned long base;
        if (N_IMAGES == MAX_IMAGES) fail("image map too large", path);
        if (find_image(id)) fail("duplicate image id", id);
        errno = 0;
        base = strtoul(base_text, &end, 0);
        if (errno || !end || *end || base > UINT32_MAX)
            fail("bad image base", base_text);
        im = &IMAGES[N_IMAGES++];
        snprintf(im->id, sizeof im->id, "%s", id);
        snprintf(im->path, sizeof im->path, "%s", rel);
        im->base = (uint32_t)base;
        im->bytes = slurp(rel, &im->size);
    }
    if (ferror(f) || fclose(f)) fail("cannot read image map", path);
    if (!N_IMAGES) fail("empty image map", path);
}

static int reg_index(const char *name)
{
    int i;
    for (i = 0; i < 32; i++) if (strcmp(REGS[i], name) == 0) return i;
    return -1;
}

static int decode_indirect(uint32_t word, const char **kind, int *reg)
{
    unsigned op = word >> 26;
    unsigned fn = word & 63u;
    if (op != 0 || (fn != 8u && fn != 9u)) return 0;
    *kind = fn == 8u ? "jr" : "jalr";
    *reg = (int)((word >> 21) & 31u);
    return 1;
}

static void emit_site(const char *spec, int first)
{
    char copy[256];
    char *image_id, *pc_text, *want_kind, *want_reg, *extra;
    char *end = NULL;
    unsigned long value;
    Image *im;
    size_t offset;
    uint32_t word, delay;
    const char *got_kind = NULL;
    int got_reg = -1, expected_reg;

    snprintf(copy, sizeof copy, "%s", spec);
    image_id = strtok(copy, ":");
    pc_text = strtok(NULL, ":");
    want_kind = strtok(NULL, ":");
    want_reg = strtok(NULL, ":");
    extra = strtok(NULL, ":");
    if (!image_id || !pc_text || !want_kind || !want_reg || extra)
        fail("bad site id", spec);
    errno = 0;
    value = strtoul(pc_text, &end, 0);
    if (errno || !end || *end || value > UINT32_MAX)
        fail("bad site pc", spec);
    expected_reg = reg_index(want_reg);
    if (expected_reg < 0) fail("bad site register", spec);
    im = find_image(image_id);
    if (!im) fail("unknown image", image_id);
    if ((uint32_t)value < im->base) fail("site precedes image", spec);
    offset = (size_t)((uint32_t)value - im->base);
    if (offset > im->size || im->size - offset < 8u)
        fail("site or delay slot outside image", spec);
    word = le32(im->bytes + offset);
    delay = le32(im->bytes + offset + 4u);
    if (!decode_indirect(word, &got_kind, &got_reg))
        fail("site word is not jr/jalr", spec);
    if (strcmp(got_kind, want_kind) || got_reg != expected_reg)
        fail("decoded kind/register differs from site id", spec);

    if (!first) printf(",\n");
    printf("  {\"id\":"); json_string(spec);
    printf(",\"image\":"); json_string(image_id);
    printf(",\"pc\":\"0x%08lx\",\"file_offset\":%zu", value, offset);
    printf(",\"word\":\"0x%08x\",\"decoded_kind\":", word);
    json_string(got_kind);
    printf(",\"decoded_register\":"); json_string(REGS[got_reg]);
    printf(",\"delay_slot_pc\":\"0x%08x\",\"delay_slot_word\":\"0x%08x\"}",
           (uint32_t)value + 4u, delay);
}

static int self_test(void)
{
    const struct { uint32_t word; int ok; const char *kind; int reg; } cases[] = {
        { 0x03e00008u, 1, "jr", 31 },
        { 0x0040f809u, 1, "jalr", 2 },
        { 0x00400008u, 1, "jr", 2 },
        { 0x00000000u, 0, NULL, -1 },
        { 0x08004000u, 0, NULL, -1 },
        { 0x0040000cu, 0, NULL, -1 },
    };
    size_t i;
    int passed = 0;
    for (i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        const char *kind = NULL;
        int reg = -1;
        int ok = decode_indirect(cases[i].word, &kind, &reg);
        if (ok != cases[i].ok) continue;
        if (ok && (strcmp(kind, cases[i].kind) || reg != cases[i].reg)) continue;
        passed++;
    }
    printf("{\"tool\":\"phase4_target_exclusion_stage1\","
           "\"passed\":%d,\"total\":%zu,\"verdict\":%s}\n",
           passed, sizeof cases / sizeof cases[0],
           passed == (int)(sizeof cases / sizeof cases[0]) ? "true" : "false");
    return passed == (int)(sizeof cases / sizeof cases[0]) ? 0 : 1;
}

int main(int argc, char **argv)
{
    int i;
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return self_test();
    if (argc < 3) {
        fprintf(stderr, "usage: %s <image-map> IMAGE:PC:jr|jalr:REG ...\n", argv[0]);
        return 2;
    }
    load_map(argv[1]);
    printf("{\"tool\":\"phase4_target_exclusion_stage1\",\"sites\":[\n");
    for (i = 2; i < argc; i++) emit_site(argv[i], i == 2);
    printf("\n ],\"site_count\":%d}\n", argc - 2);
    for (i = 0; i < (int)N_IMAGES; i++) free(IMAGES[i].bytes);
    return 0;
}
