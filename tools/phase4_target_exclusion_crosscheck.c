/*
 * Independent Stage-2 cross-check for the frozen target-exclusion pilot.
 *
 * This implementation does not share the primary verifier's backwards
 * reaching-definition or constant evaluators.  It reads the image bytes and
 * performs a forward finite-set dataflow to each named jr/jalr.  UNKNOWN is
 * absorbing at joins, definitions kill the incoming state, and finite sets
 * widen to UNKNOWN rather than truncate.  Delay slots are explicit CFG nodes.
 */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_IMAGES 64
#define MAX_VALUES 64

static const char *REGS[32] = {
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"
};

typedef struct {
    char id[64], path[512];
    uint32_t base;
    uint8_t *bytes;
    size_t size;
} Image;

static Image IMAGES[MAX_IMAGES];
static size_t N_IMAGES;

enum { ST_BOTTOM = 0, ST_EXACT = 1, ST_UNKNOWN = 2 };
enum {
    WHY_ENTRY = 1u << 0,
    WHY_REGISTER_COPY = 1u << 1,
    WHY_LOAD = 1u << 2,
    WHY_CALL = 1u << 3,
    WHY_UNSUPPORTED = 1u << 4,
    WHY_WIDENED = 1u << 5
};

typedef struct {
    int kind;
    uint32_t values[MAX_VALUES];
    size_t nvalues;
    unsigned why;
} State;

typedef struct {
    int reached, exact;
    uint32_t values[MAX_VALUES];
    size_t nvalues;
    unsigned why;
} Result;

static void fail(const char *message, const char *detail)
{
    fprintf(stderr, "target-exclusion crosscheck: %s%s%s\n", message,
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
    long n;
    uint8_t *bytes;
    if (!f) fail("cannot open image", path);
    if (fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 || fseek(f, 0, SEEK_SET))
        fail("cannot size image", path);
    bytes = malloc((size_t)n ? (size_t)n : 1u);
    if (!bytes) fail("out of memory", NULL);
    if (n && fread(bytes, 1, (size_t)n, f) != (size_t)n)
        fail("cannot read image", path);
    if (fclose(f)) fail("cannot close image", path);
    *size = (size_t)n;
    return bytes;
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
        if (N_IMAGES == MAX_IMAGES) fail("too many images", path);
        if (find_image(id)) fail("duplicate image", id);
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

static int reg_index(const char *name)
{
    int i;
    for (i = 0; i < 32; i++) if (strcmp(REGS[i], name) == 0) return i;
    return -1;
}

static int is_transfer(uint32_t w)
{
    uint32_t op = w >> 26, fn = w & 63u;
    uint32_t rs = (w >> 21) & 31u, rt = (w >> 16) & 31u;
    int regimm = op == 1 && (rt <= 3 || (rt >= 0x10 && rt <= 0x13));
    int cop_branch = op >= 0x10 && op <= 0x13 && rs == 8 && rt <= 3;
    return op == 2 || op == 3 || regimm || (op >= 4 && op <= 7)
        || (op >= 0x14 && op <= 0x17)
        || cop_branch
        || (op == 0 && (fn == 8 || fn == 9));
}

static int is_branch_likely(uint32_t w)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31u;
    uint32_t rt = (w >> 16) & 31u;
    return (op >= 0x14 && op <= 0x17)
        || (op == 1 && (rt == 2 || rt == 3 || rt == 0x12 || rt == 0x13))
        || (op >= 0x10 && op <= 0x13 && rs == 8 && (rt == 2 || rt == 3));
}

static int is_call(uint32_t w)
{
    uint32_t op = w >> 26, rt = (w >> 16) & 31u;
    return op == 3 || (op == 0 && (w & 63u) == 9)
        || (op == 1 && rt >= 0x10 && rt <= 0x13);
}

static int is_terminator(uint32_t w)
{
    uint32_t op = w >> 26, fn = w & 63u;
    uint32_t rs = (w >> 21) & 31u, rt = (w >> 16) & 31u;
    if (op == 0 && (fn == 0x0c || fn == 0x0d)) return 1;
    if (op == 1 && !(rt <= 3 || (rt >= 0x10 && rt <= 0x13))) return 1;
    if ((op == 6 || op == 7) && rt != 0) return 1;
    if (op >= 0x10 && op <= 0x13 && rs == 8 && rt > 3) return 1;
    return 0;
}

static int def_reg(uint32_t w)
{
    uint32_t op = w >> 26, fn = w & 63u;
    int rt = (int)((w >> 16) & 31u), rd = (int)((w >> 11) & 31u);
    if (op == 0) {
        if (fn == 8 || fn == 0x0c || fn == 0x0d || fn == 0x18 || fn == 0x19
            || fn == 0x1a || fn == 0x1b || fn == 0x11 || fn == 0x13) return -1;
        if (fn == 9) return rd ? rd : -1;
        return rd ? rd : -1;
    }
    if (op == 3) return 31;
    if (op == 1 && rt >= 0x10 && rt <= 0x13) return 31;
    if ((op >= 8 && op <= 15) || (op >= 0x20 && op <= 0x26))
        return rt ? rt : -1;
    if (op >= 0x10 && op <= 0x13) {
        uint32_t rs = (w >> 21) & 31u;
        return (rs == 0 || rs == 2) && rt ? rt : -1;
    }
    return -1;
}

static int successors(const uint32_t *code, size_t words, size_t i,
                      uint32_t start, size_t out[2])
{
    int n = 0;
    if (i > 0 && is_transfer(code[i - 1])) {
        uint32_t w = code[i - 1], op = w >> 26;
        uint32_t pc = start + (uint32_t)((i - 1) * 4);
        if (op == 0 && (w & 63u) == 8) return 0;
        if (is_call(w)) {
            if (i + 1 < words) out[n++] = i + 1;
            return n;
        }
        if (op == 2) {
            uint32_t t = ((pc + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2);
            if (t >= start && (t - start) / 4 < words) out[n++] = (t - start) / 4;
            return n;
        }
        {
            int32_t d = (int16_t)(w & 0xffffu);
            uint32_t t = pc + 4 + (uint32_t)(d * 4);
            if (t >= start && (t - start) / 4 < words) out[n++] = (t - start) / 4;
            if (!is_branch_likely(w) && i + 1 < words) out[n++] = i + 1;
        }
        return n;
    }
    if (is_terminator(code[i])) return 0;
    if (is_transfer(code[i])) {
        if (i + 1 < words) out[n++] = i + 1;
        if (is_branch_likely(code[i]) && i + 2 < words) out[n++] = i + 2;
        return n;
    }
    if (i + 1 < words) out[n++] = i + 1;
    return n;
}

static int value_compare(const void *a, const void *b)
{
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return x < y ? -1 : x != y;
}

static State exact_one(uint32_t value)
{
    State out = {ST_EXACT, {0}, 1, 0};
    out.values[0] = value;
    return out;
}

static State unknown(unsigned why)
{
    State out = {ST_UNKNOWN, {0}, 0, why};
    return out;
}

static int state_equal(const State *a, const State *b)
{
    return a->kind == b->kind && a->nvalues == b->nvalues && a->why == b->why
        && !memcmp(a->values, b->values, a->nvalues * sizeof a->values[0]);
}

static State merge_state(State a, State b)
{
    if (a.kind == ST_BOTTOM) return b;
    if (b.kind == ST_BOTTOM) return a;
    if (a.kind == ST_UNKNOWN || b.kind == ST_UNKNOWN)
        return unknown(a.why | b.why);
    State out = a;
    for (size_t i = 0; i < b.nvalues; i++) {
        size_t j;
        for (j = 0; j < out.nvalues; j++)
            if (out.values[j] == b.values[i]) break;
        if (j != out.nvalues) continue;
        if (out.nvalues == MAX_VALUES) return unknown(WHY_WIDENED);
        out.values[out.nvalues++] = b.values[i];
    }
    qsort(out.values, out.nvalues, sizeof out.values[0], value_compare);
    return out;
}

static State map_values(State in, uint32_t op, uint32_t imm, uint32_t sh)
{
    if (in.kind != ST_EXACT) return in;
    for (size_t i = 0; i < in.nvalues; i++) {
        if (op == 0x0d) in.values[i] |= imm;
        else if (op == 0x0c) in.values[i] &= imm;
        else if (op == 0x09)
            in.values[i] += (uint32_t)(int32_t)(int16_t)imm;
        else if (op == 0x100) in.values[i] <<= sh;
        else if (op == 0x102) in.values[i] >>= sh;
    }
    qsort(in.values, in.nvalues, sizeof in.values[0], value_compare);
    return in;
}

static State execute(uint32_t w, int reg, State in)
{
    if (def_reg(w) != reg) return in;
    uint32_t op = w >> 26, fn = w & 63u, imm = w & 0xffffu;
    int rs = (int)((w >> 21) & 31u), rt = (int)((w >> 16) & 31u);
    if (op == 0x0f) return exact_one(imm << 16);
    if (op == 0x0d || op == 0x0c || op == 0x09) {
        State source = rs == 0 ? exact_one(0) : rs == reg ? in : unknown(WHY_UNSUPPORTED);
        return map_values(source, op, imm, 0);
    }
    if (op == 0 && (fn == 0x20 || fn == 0x21 || fn == 0x25)) {
        int source = -1;
        if (rt == 0 && rs != 0) source = rs;
        if (rs == 0 && rt != 0) source = rt;
        if (source == reg) return in;
        return unknown(WHY_REGISTER_COPY);
    }
    if (op == 0 && (fn == 0x00 || fn == 0x02)) {
        State source = rt == 0 ? exact_one(0) : rt == reg ? in : unknown(WHY_UNSUPPORTED);
        return map_values(source, fn == 0 ? 0x100u : 0x102u, 0, (w >> 6) & 31u);
    }
    if (op >= 0x20 && op <= 0x26) return unknown(WHY_LOAD);
    return unknown(WHY_UNSUPPORTED);
}

static Result evaluate(const uint32_t *code, size_t words, uint32_t start,
                       int reg, size_t use)
{
    Result result = {0};
    if (!words || use >= words) return result;
    State *states = calloc(words, sizeof *states);
    uint8_t *queued = calloc(words, 1);
    size_t queue_cap = words * 256u + 1u;
    size_t *queue = malloc(queue_cap * sizeof *queue);
    if (!states || !queued || !queue) fail("out of memory", NULL);
    size_t head = 0, tail = 0;
    states[0] = unknown(WHY_ENTRY);
    queue[tail++] = 0;
    queued[0] = 1;
    while (head < tail) {
        size_t i = queue[head++];
        queued[i] = 0;
        State out = execute(code[i], reg, states[i]);
        /* A call owns execution after its delay slot.  The independent pass
         * assumes no ABI preservation: absent an interprocedural proof, any
         * queried register may return changed. */
        if (i > 0 && is_call(code[i - 1])) out = unknown(out.why | WHY_CALL);
        size_t succ[2];
        int n = successors(code, words, i, start, succ);
        for (int k = 0; k < n; k++) {
            State merged = merge_state(states[succ[k]], out);
            if (!state_equal(&merged, &states[succ[k]])) {
                states[succ[k]] = merged;
                if (!queued[succ[k]]) {
                    if (tail == queue_cap) fail("dataflow queue did not converge", NULL);
                    queue[tail++] = succ[k];
                    queued[succ[k]] = 1;
                }
            }
        }
    }
    if (states[use].kind != ST_BOTTOM) {
        result.reached = 1;
        result.exact = states[use].kind == ST_EXACT;
        result.nvalues = result.exact ? states[use].nvalues : 0;
        result.why = states[use].why;
        memcpy(result.values, states[use].values,
               result.nvalues * sizeof result.values[0]);
    }
    free(states); free(queued); free(queue);
    return result;
}

static const char *classification(const Result *result, int reg)
{
    if (result->exact) return "computed";
    if (reg == 31 && (result->why & WHY_REGISTER_COPY))
        return "register_provenance";
    if (reg == 31) return "return_like_unproved_incoming_ra";
    return "unclassified_forward_state";
}

static void emit_reasons(unsigned why)
{
    int first = 1;
    struct { unsigned bit; const char *name; } rows[] = {
        { WHY_ENTRY, "entry_value" },
        { WHY_REGISTER_COPY, "register_copy_source_untracked" },
        { WHY_LOAD, "memory_load_without_value_invariant" },
        { WHY_CALL, "call_crossing_without_register_preservation_proof" },
        { WHY_UNSUPPORTED, "unsupported_definition" },
        { WHY_WIDENED, "finite_set_cap_exceeded" },
    };
    putchar('[');
    for (size_t i = 0; i < sizeof rows / sizeof rows[0]; i++) {
        if (!(why & rows[i].bit)) continue;
        printf("%s", first ? "" : ",");
        json_string(rows[i].name);
        first = 0;
    }
    putchar(']');
}

static void emit_query(const char *spec, int first)
{
    char copy[320];
    char *image_id, *start_text, *end_text, *reg_text, *pc_text, *extra;
    char *parse_end = NULL;
    uint32_t start, end, pc;
    unsigned long parsed;
    int reg, got_reg;
    Image *im;
    size_t offset, words, use;
    uint32_t *code;
    const char *kind;

    snprintf(copy, sizeof copy, "%s", spec);
    image_id = strtok(copy, ":");
    start_text = strtok(NULL, ":");
    end_text = strtok(NULL, ":");
    reg_text = strtok(NULL, ":");
    pc_text = strtok(NULL, ":");
    extra = strtok(NULL, ":");
    if (!image_id || !start_text || !end_text || !reg_text || !pc_text || extra)
        fail("bad query", spec);
    errno = 0; parsed = strtoul(start_text, &parse_end, 0);
    if (errno || !parse_end || *parse_end || parsed > UINT32_MAX) fail("bad start", spec);
    start = (uint32_t)parsed;
    errno = 0; parsed = strtoul(end_text, &parse_end, 0);
    if (errno || !parse_end || *parse_end || parsed > UINT32_MAX) fail("bad end", spec);
    end = (uint32_t)parsed;
    errno = 0; parsed = strtoul(pc_text, &parse_end, 0);
    if (errno || !parse_end || *parse_end || parsed > UINT32_MAX) fail("bad pc", spec);
    pc = (uint32_t)parsed;
    reg = reg_index(reg_text);
    if (reg < 0) fail("bad register", spec);
    im = find_image(image_id);
    if (!im || end <= start || (end - start) % 4 || start < im->base
        || pc < start || pc >= end || (pc - start) % 4)
        fail("query range invalid", spec);
    offset = start - im->base;
    words = (end - start) / 4;
    if (offset > im->size || words * 4 > im->size - offset)
        fail("query extent outside image", spec);
    code = malloc(words * sizeof *code);
    if (!code) fail("out of memory", NULL);
    for (size_t i = 0; i < words; i++) code[i] = le32(im->bytes + offset + i * 4);
    use = (pc - start) / 4;
    if ((code[use] >> 26) != 0 || ((code[use] & 63u) != 8 && (code[use] & 63u) != 9))
        fail("query site is not jr/jalr", spec);
    got_reg = (int)((code[use] >> 21) & 31u);
    if (got_reg != reg) fail("query register differs from bytes", spec);
    kind = (code[use] & 63u) == 8 ? "jr" : "jalr";
    Result result = evaluate(code, words, start, reg, use);

    if (!first) printf(",\n");
    printf("  {\"query\":"); json_string(spec);
    printf(",\"image\":"); json_string(image_id);
    printf(",\"site_pc\":\"0x%08x\",\"site_word\":\"0x%08x\","
           "\"kind\":", pc, code[use]); json_string(kind);
    printf(",\"register\":"); json_string(REGS[reg]);
    printf(",\"classification\":"); json_string(classification(&result, reg));
    printf(",\"entry_reached\":%s,\"full_target_domain_complete\":%s,"
           "\"targets\":[", result.reached ? "true" : "false",
           result.exact ? "true" : "false");
    for (size_t i = 0; i < result.nvalues; i++)
        printf("%s\"0x%08x\"", i ? "," : "", result.values[i]);
    printf("],\"unknown_reasons\":"); emit_reasons(result.why);
    printf(",\"algorithm\":\"independent forward finite-set fixpoint from image bytes\"}");
    free(code);
}

static int self_test(void)
{
    const uint32_t BASE = 0x80010000u;
    static const uint32_t MULTI[] = {
        0x10800004, 0x00000000, 0x3c168001, 0x08004007, 0x36d61000,
        0x3c168002, 0x36d62000, 0x02c00008, 0x00000000,
    };
    static const uint32_t BYPASS[] = {
        0x14800003, 0x00000000, 0x3c168001, 0x36d61000,
        0x02c00008, 0x00000000,
    };
    static const uint32_t LOAD[] = {
        0x8c960000, 0x00000000, 0x02c00008, 0x00000000,
    };
    static const uint32_t DELAY[] = {
        0x3c168001, 0x08004003, 0x36d62340, 0x02c00008, 0x00000000,
    };
    static const uint32_t ORDINARY_DELAY[] = {
        0x10850001, 0x3c168001, 0x02c00008, 0x00000000,
    };
    static const uint32_t LIKELY_ANNUL[] = {
        0x50850001, 0x3c168001, 0x02c00008, 0x00000000,
    };
    static const uint32_t REGIMM_LINK[] = {
        0x3c168001, 0x04910001, 0x00000000, 0x02c00008, 0x00000000,
    };
    static const uint32_t COP_BRANCH[] = {
        0x49010001, 0x3c168001, 0x02c00008, 0x00000000,
    };
    struct {
        const uint32_t *code; size_t words, use;
        int exact; size_t nvalues; uint32_t a, b; unsigned why;
    } cases[] = {
        { MULTI, 9, 7, 1, 2, 0x80011000, 0x80022000, 0 },
        { BYPASS, 6, 4, 0, 0, 0, 0, WHY_ENTRY },
        { LOAD, 4, 2, 0, 0, 0, 0, WHY_LOAD },
        { DELAY, 5, 3, 1, 1, 0x80012340, 0, 0 },
        { ORDINARY_DELAY, 4, 2, 1, 1, 0x80010000, 0, 0 },
        { LIKELY_ANNUL, 4, 2, 0, 0, 0, 0, WHY_ENTRY },
        { REGIMM_LINK, 5, 3, 0, 0, 0, 0, WHY_CALL },
        { COP_BRANCH, 4, 2, 1, 1, 0x80010000, 0, 0 },
    };
    int passed = 0;
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        Result r = evaluate(cases[i].code, cases[i].words, BASE, 22, cases[i].use);
        int ok = r.exact == cases[i].exact && r.nvalues == cases[i].nvalues;
        if (r.exact && r.nvalues) ok = ok && r.values[0] == cases[i].a;
        if (r.exact && r.nvalues > 1) ok = ok && r.values[1] == cases[i].b;
        if (!r.exact) ok = ok && (r.why & cases[i].why) == cases[i].why;
        if (ok) passed++;
    }
    printf("{\"tool\":\"phase4_target_exclusion_crosscheck\","
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
        fprintf(stderr, "usage: %s <image-map> IMAGE:START:END:REG:PC ...\n", argv[0]);
        return 2;
    }
    load_map(argv[1]);
    printf("{\"tool\":\"phase4_target_exclusion_crosscheck\",\"queries\":[\n");
    for (i = 2; i < argc; i++) emit_query(argv[i], i == 2);
    printf("\n ],\"query_count\":%d}\n", argc - 2);
    for (i = 0; i < (int)N_IMAGES; i++) free(IMAGES[i].bytes);
    return 0;
}
