/*
 * Primary exact target-domain prover for the frozen Phase-4 pilot.
 *
 * This is deliberately standalone: changing the accepted shared typed-state
 * analyser would stale protected F01 receipts on a NO-GO.  The proof walks
 * backwards over a delay-slot-correct predecessor graph, enumerates every
 * nearest reaching definition, recursively proves exact source constants, and
 * fails the entire site on any entry/call/load/unsupported path.  The separate
 * cross-check uses a forward finite-set fixpoint and shares no proof code.
 */

#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_IMAGES 64
#define MAX_VALUES 256

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

typedef struct { char *text; size_t len, cap; } Buf;

typedef struct {
    const uint32_t *code;
    size_t words;
    uint32_t start;
    uint8_t *reachable;
    uint8_t *active;
    int *pred_head, *pred_from, *pred_next;
    size_t edge_count;
} Context;

enum { EV_DEF = 1, EV_ENTRY = 2, EV_CALL = 3, EV_LOAD_DELAY = 4 };
typedef struct { int kind; size_t at; } Event;
typedef struct { Event *rows; size_t count, cap; } Events;

typedef struct {
    int ok;
    uint32_t value;
    char *json;
    int have_breaker;
    uint32_t breaker_pc, breaker_word;
    char reason[128];
} Uniform;

typedef struct {
    int verdict;
    uint32_t values[MAX_VALUES];
    size_t nvalues;
    long definition_occurrences, excluded_unreachable;
    char *json;
    int have_breaker;
    uint32_t breaker_pc, breaker_word;
    char reason[128];
} Domain;

static void fail(const char *message, const char *detail)
{
    fprintf(stderr, "target-exclusion prover: %s%s%s\n", message,
            detail ? ": " : "", detail ? detail : "");
    exit(2);
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void buf_init(Buf *buf)
{
    buf->cap = 256;
    buf->len = 0;
    buf->text = malloc(buf->cap);
    if (!buf->text) fail("out of memory", NULL);
    buf->text[0] = 0;
}

static void buf_add(Buf *buf, const char *fmt, ...)
{
    for (;;) {
        va_list ap;
        va_start(ap, fmt);
        int n = vsnprintf(buf->text + buf->len, buf->cap - buf->len, fmt, ap);
        va_end(ap);
        if (n < 0) fail("cannot format JSON", NULL);
        if ((size_t)n < buf->cap - buf->len) {
            buf->len += (size_t)n;
            return;
        }
        size_t need = buf->len + (size_t)n + 1;
        size_t cap = buf->cap;
        while (cap < need) cap *= 2;
        char *next = realloc(buf->text, cap);
        if (!next) fail("out of memory", NULL);
        buf->text = next;
        buf->cap = cap;
    }
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
    for (size_t i = 0; i < N_IMAGES; i++)
        if (strcmp(IMAGES[i].id, id) == 0) return &IMAGES[i];
    return NULL;
}

static void load_map(const char *path)
{
    FILE *f = fopen(path, "r");
    char id[64], rel[512], base_text[32];
    if (!f) fail("cannot open image map", path);
    while (fscanf(f, "%63s %511s %31s", id, rel, base_text) == 3) {
        char *end = NULL;
        unsigned long base;
        Image *im;
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
    for (int i = 0; i < 32; i++) if (strcmp(REGS[i], name) == 0) return i;
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

static int is_load(uint32_t w)
{
    uint32_t op = w >> 26;
    return op >= 0x20 && op <= 0x26;
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
            uint32_t target = ((pc + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2);
            if (target >= start && (target - start) / 4 < words)
                out[n++] = (target - start) / 4;
            return n;
        }
        {
            int32_t d = (int16_t)(w & 0xffffu);
            uint32_t target = pc + 4 + (uint32_t)(d * 4);
            if (target >= start && (target - start) / 4 < words)
                out[n++] = (target - start) / 4;
            if (!is_branch_likely(w) && i + 1 < words) out[n++] = i + 1;
        }
        return n;
    }
    if (is_terminator(code[i])) return 0;
    if (is_transfer(code[i])) {
        if (i + 1 < words) out[n++] = i + 1;
        /* A likely branch executes its delay slot only on the taken edge.
         * Its not-taken edge skips directly to PC+8.  Keeping that edge
         * distinct prevents a delay-slot definition from falsely dominating
         * both paths. */
        if (is_branch_likely(code[i]) && i + 2 < words) out[n++] = i + 2;
        return n;
    }
    if (i + 1 < words) out[n++] = i + 1;
    return n;
}

static void context_init(Context *ctx, const uint32_t *code, size_t words,
                         uint32_t start)
{
    memset(ctx, 0, sizeof *ctx);
    ctx->code = code;
    ctx->words = words;
    ctx->start = start;
    ctx->reachable = calloc(words ? words : 1, 1);
    ctx->active = calloc((words ? words : 1) * 32u, 1);
    ctx->pred_head = malloc((words ? words : 1) * sizeof *ctx->pred_head);
    ctx->pred_from = malloc((words * 2u + 1u) * sizeof *ctx->pred_from);
    ctx->pred_next = malloc((words * 2u + 1u) * sizeof *ctx->pred_next);
    if (!ctx->reachable || !ctx->active || !ctx->pred_head
        || !ctx->pred_from || !ctx->pred_next) fail("out of memory", NULL);
    for (size_t i = 0; i < words; i++) ctx->pred_head[i] = -1;
    if (!words) return;
    size_t *stack = malloc(words * sizeof *stack);
    if (!stack) fail("out of memory", NULL);
    size_t sp = 0;
    ctx->reachable[0] = 1;
    stack[sp++] = 0;
    while (sp) {
        size_t at = stack[--sp], succ[2];
        int n = successors(code, words, at, start, succ);
        for (int i = 0; i < n; i++) if (!ctx->reachable[succ[i]]) {
            ctx->reachable[succ[i]] = 1;
            stack[sp++] = succ[i];
        }
    }
    free(stack);
    for (size_t at = 0; at < words; at++) {
        if (!ctx->reachable[at]) continue;
        size_t succ[2];
        int n = successors(code, words, at, start, succ);
        for (int i = 0; i < n; i++) {
            if (!ctx->reachable[succ[i]] || ctx->edge_count >= words * 2u + 1u)
                fail("predecessor graph overflow", NULL);
            size_t edge = ctx->edge_count++;
            ctx->pred_from[edge] = (int)at;
            ctx->pred_next[edge] = ctx->pred_head[succ[i]];
            ctx->pred_head[succ[i]] = (int)edge;
        }
    }
}

static void context_free(Context *ctx)
{
    free(ctx->reachable); free(ctx->active);
    free(ctx->pred_head); free(ctx->pred_from); free(ctx->pred_next);
}

static void events_add(Events *events, int kind, size_t at)
{
    for (size_t i = 0; i < events->count; i++)
        if (events->rows[i].kind == kind && events->rows[i].at == at) return;
    if (events->count == events->cap) {
        size_t cap = events->cap ? events->cap * 2u : 8u;
        Event *rows = realloc(events->rows, cap * sizeof *rows);
        if (!rows) fail("out of memory", NULL);
        events->rows = rows;
        events->cap = cap;
    }
    events->rows[events->count++] = (Event){kind, at};
}

static Events reaching_events(const Context *ctx, int reg, size_t use)
{
    Events events = {0};
    uint8_t *seen = calloc(ctx->words ? ctx->words : 1, 1);
    size_t *stack = malloc((ctx->words ? ctx->words : 1) * sizeof *stack);
    if (!seen || !stack) fail("out of memory", NULL);
    size_t sp = 0;
    seen[use] = 1;
    stack[sp++] = use;
    while (sp) {
        size_t node = stack[--sp];
        if (node == 0) {
            events_add(&events, EV_ENTRY, use);
            continue;
        }
        for (int edge = ctx->pred_head[node]; edge >= 0;
             edge = ctx->pred_next[edge]) {
            size_t pred = (size_t)ctx->pred_from[edge];
            if (pred > 0 && is_call(ctx->code[pred - 1])) {
                events_add(&events, EV_CALL, pred - 1);
                continue;
            }
            if (def_reg(ctx->code[pred]) == reg) {
                if (node == use && is_load(ctx->code[pred]))
                    events_add(&events, EV_LOAD_DELAY, pred);
                else
                    events_add(&events, EV_DEF, pred);
                continue;
            }
            if (!seen[pred]) {
                seen[pred] = 1;
                stack[sp++] = pred;
            }
        }
    }
    free(seen); free(stack);
    return events;
}

static void uniform_breaker(Uniform *proof, uint32_t pc, uint32_t word,
                            const char *reason)
{
    if (proof->have_breaker) return;
    proof->have_breaker = 1;
    proof->breaker_pc = pc;
    proof->breaker_word = word;
    snprintf(proof->reason, sizeof proof->reason, "%s", reason);
}

static Uniform uniform_at(Context *ctx, int reg, size_t use, int depth);

static const char *operation_of(uint32_t word, int reg, int *source)
{
    uint32_t op = word >> 26, fn = word & 63u;
    int rs = (int)((word >> 21) & 31u), rt = (int)((word >> 16) & 31u);
    int rd = (int)((word >> 11) & 31u);
    *source = -1;
    if (def_reg(word) != reg) return NULL;
    if (op == 0x0f) return "lui_exact";
    if (op == 0x0d) { *source = rs; return "ori_exact"; }
    if (op == 0x0c) { *source = rs; return "andi_exact"; }
    if (op == 0x09) { *source = rs; return "addiu_exact_mod32"; }
    if (op == 0 && (fn == 0x20 || fn == 0x21 || fn == 0x25) && rd == reg) {
        if (rt == 0 && rs != 0) { *source = rs; return "register_copy_exact"; }
        if (rs == 0 && rt != 0) { *source = rt; return "register_copy_exact"; }
        return NULL;
    }
    if (op == 0 && (fn == 0x00 || fn == 0x02) && rd == reg) {
        *source = rt;
        return fn == 0 ? "sll_exact" : "srl_exact";
    }
    return NULL;
}

static Uniform evaluate_definition(Context *ctx, int reg, size_t at, int depth)
{
    Uniform out = {0};
    Buf json;
    buf_init(&json);
    uint32_t word = ctx->code[at], op = word >> 26, fn = word & 63u;
    uint32_t imm = word & 0xffffu;
    uint32_t pc = ctx->start + (uint32_t)(at * 4);
    int source = -1;
    const char *operation = operation_of(word, reg, &source);
    if (!operation) {
        const char *reason = is_load(word)
            ? "memory_load_requires_a_complete_value_invariant"
            : is_call(word)
              ? "call_link_or_result_not_an_exact_target_constant"
              : "definition_operation_not_in_exact_target_whitelist";
        uniform_breaker(&out, pc, word, reason);
        buf_add(&json, "{\"definition_pc\":\"0x%08x\","
                "\"definition_word\":\"0x%08x\",\"operation\":"
                "\"not_whitelisted\",\"proved\":false,\"failure\":\"%s\"}",
                pc, word, reason);
        out.json = json.text;
        return out;
    }
    if (op == 0x0f) {
        out.ok = 1;
        out.value = imm << 16;
        buf_add(&json, "{\"definition_pc\":\"0x%08x\","
                "\"definition_word\":\"0x%08x\",\"operation\":\"%s\","
                "\"proved\":true,\"value\":\"0x%08x\",\"inputs\":[]}",
                pc, word, operation, out.value);
        out.json = json.text;
        return out;
    }

    Uniform input;
    if (source == 0) {
        memset(&input, 0, sizeof input);
        input.ok = 1;
        input.value = 0;
        input.json = malloc(66);
        if (!input.json) fail("out of memory", NULL);
        snprintf(input.json, 66, "[{\"kind\":\"architectural_zero\",\"value\":\"0x00000000\"}]");
    } else {
        input = uniform_at(ctx, source, at, depth + 1);
    }
    if (!input.ok) {
        const char *reason = "source_constant_not_path_complete_or_evaluators_disagree";
        uniform_breaker(&out, pc, word, reason);
        buf_add(&json, "{\"definition_pc\":\"0x%08x\","
                "\"definition_word\":\"0x%08x\",\"operation\":\"%s\","
                "\"proved\":false,\"failure\":\"%s\","
                "\"inputs\":[{\"register\":\"%s\",\"proof\":%s}]}",
                pc, word, operation, reason, REGS[source], input.json);
        free(input.json);
        out.json = json.text;
        return out;
    }
    out.ok = 1;
    if (op == 0x0d) out.value = input.value | imm;
    else if (op == 0x0c) out.value = input.value & imm;
    else if (op == 0x09)
        out.value = input.value + (uint32_t)(int32_t)(int16_t)imm;
    else if (op == 0 && (fn == 0x20 || fn == 0x21 || fn == 0x25))
        out.value = input.value;
    else if (op == 0 && fn == 0x00)
        out.value = input.value << ((word >> 6) & 31u);
    else if (op == 0 && fn == 0x02)
        out.value = input.value >> ((word >> 6) & 31u);
    else {
        out.ok = 0;
        uniform_breaker(&out, pc, word, "internal_exact_target_operation_gap");
    }
    buf_add(&json, "{\"definition_pc\":\"0x%08x\","
            "\"definition_word\":\"0x%08x\",\"operation\":\"%s\","
            "\"proved\":%s,\"value\":%s\"0x%08x\"%s,"
            "\"inputs\":[{\"register\":\"%s\",\"proof\":%s}]}",
            pc, word, operation, out.ok ? "true" : "false",
            out.ok ? "" : "null,\"discarded_value\":",
            out.value, out.ok ? "" : "", REGS[source], input.json);
    free(input.json);
    out.json = json.text;
    return out;
}

static Uniform uniform_at(Context *ctx, int reg, size_t use, int depth)
{
    Uniform out = {0};
    Buf json;
    buf_init(&json);
    buf_add(&json, "[");
    uint32_t use_pc = ctx->start + (uint32_t)(use * 4);
    uint32_t use_word = use < ctx->words ? ctx->code[use] : 0;
    if (reg == 0) {
        out.ok = 1; out.value = 0;
        buf_add(&json, "{\"kind\":\"architectural_zero\",\"value\":\"0x00000000\"}]");
        out.json = json.text;
        return out;
    }
    if (depth > 64 || use >= ctx->words
        || ctx->active[(size_t)reg * ctx->words + use]) {
        uniform_breaker(&out, use_pc, use_word,
                        "cyclic_or_out_of_range_source_dependency");
        buf_add(&json, "{\"kind\":\"source_failure\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"failure\":\"%s\"}]",
                use_pc, use_word, out.reason);
        out.json = json.text;
        return out;
    }
    ctx->active[(size_t)reg * ctx->words + use] = 1;
    Events events = reaching_events(ctx, reg, use);
    int first = 1, have_value = 0;
    for (size_t i = 0; i < events.count; i++) {
        Event event = events.rows[i];
        if (!first) buf_add(&json, ",");
        first = 0;
        if (event.kind == EV_DEF) {
            Uniform one = evaluate_definition(ctx, reg, event.at, depth);
            buf_add(&json, "%s", one.json);
            if (!one.ok) {
                uniform_breaker(&out, one.breaker_pc, one.breaker_word, one.reason);
            } else if (!have_value) {
                out.value = one.value;
                have_value = 1;
            } else if (out.value != one.value) {
                uniform_breaker(&out, use_pc, use_word,
                                "source_constant_definitions_disagree");
            }
            free(one.json);
        } else {
            uint32_t pc = event.kind == EV_ENTRY ? use_pc
                         : ctx->start + (uint32_t)(event.at * 4);
            uint32_t word = event.kind == EV_ENTRY ? use_word : ctx->code[event.at];
            const char *reason = event.kind == EV_ENTRY
                ? "entry_path_without_definition"
                : event.kind == EV_CALL
                  ? "call_crossing_without_register_preservation_proof"
                  : "load_result_not_visible_to_immediate_successor";
            uniform_breaker(&out, pc, word, reason);
            buf_add(&json, "{\"kind\":\"%s\",\"pc\":\"0x%08x\","
                    "\"word\":\"0x%08x\",\"proved\":false,"
                    "\"failure\":\"%s\"}",
                    event.kind == EV_ENTRY ? "entry_path_without_definition"
                    : event.kind == EV_CALL ? "call_crossing" : "load_delay",
                    pc, word, reason);
        }
    }
    if (!events.count) {
        uniform_breaker(&out, use_pc, use_word, "no_reaching_definition");
        buf_add(&json, "{\"kind\":\"no_reaching_definition\","
                "\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                "\"failure\":\"%s\"}", use_pc, use_word, out.reason);
    }
    buf_add(&json, "]");
    out.ok = events.count > 0 && have_value && !out.have_breaker;
    out.json = json.text;
    free(events.rows);
    ctx->active[(size_t)reg * ctx->words + use] = 0;
    return out;
}

static int flows_to_use(const uint32_t *code, size_t words, uint32_t start,
                        size_t definition, int reg, size_t use)
{
    uint8_t *seen = calloc(words ? words : 1, 1);
    size_t *stack = malloc((words ? words : 1) * sizeof *stack);
    if (!seen || !stack) fail("out of memory", NULL);
    size_t sp = 0, succ[2];
    int n = successors(code, words, definition, start, succ);
    for (int i = 0; i < n; i++) {
        seen[succ[i]] = 1;
        stack[sp++] = succ[i];
    }
    int found = 0;
    while (sp && !found) {
        size_t at = stack[--sp];
        if (at == use) { found = 1; break; }
        if (def_reg(code[at]) == reg) continue;
        n = successors(code, words, at, start, succ);
        for (int i = 0; i < n; i++) if (!seen[succ[i]]) {
            seen[succ[i]] = 1;
            stack[sp++] = succ[i];
        }
    }
    free(seen); free(stack);
    return found;
}

static int value_compare(const void *a, const void *b)
{
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return x < y ? -1 : x != y;
}

static void domain_breaker(Domain *domain, uint32_t pc, uint32_t word,
                           const char *reason)
{
    if (domain->have_breaker) return;
    domain->have_breaker = 1;
    domain->breaker_pc = pc;
    domain->breaker_word = word;
    snprintf(domain->reason, sizeof domain->reason, "%s", reason);
}

static int domain_add(Domain *domain, uint32_t value)
{
    for (size_t i = 0; i < domain->nvalues; i++)
        if (domain->values[i] == value) return 1;
    if (domain->nvalues == MAX_VALUES) return 0;
    domain->values[domain->nvalues++] = value;
    return 1;
}

static Domain domain_at(Context *ctx, int reg, size_t use)
{
    Domain domain = {0};
    Buf json;
    buf_init(&json);
    buf_add(&json, "[");
    uint32_t use_pc = ctx->start + (uint32_t)(use * 4);
    uint32_t use_word = ctx->code[use];
    int first = 1;
    if (!ctx->reachable[use]) {
        domain_breaker(&domain, use_pc, use_word, "query_site_not_entry_reachable");
        buf_add(&json, "{\"kind\":\"query_failure\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"proved\":false,"
                "\"failure\":\"%s\"}", use_pc, use_word, domain.reason);
        first = 0;
    } else {
        Events events = reaching_events(ctx, reg, use);
        for (size_t i = 0; i < events.count; i++) {
            Event event = events.rows[i];
            if (!first) buf_add(&json, ",");
            first = 0;
            if (event.kind == EV_DEF) {
                Uniform one = evaluate_definition(ctx, reg, event.at, 0);
                domain.definition_occurrences++;
                buf_add(&json, "%s", one.json);
                if (!one.ok)
                    domain_breaker(&domain,
                                   ctx->start + (uint32_t)(event.at * 4),
                                   ctx->code[event.at],
                                   "source_constant_not_path_complete_or_evaluators_disagree");
                else if (!domain_add(&domain, one.value))
                    domain_breaker(&domain,
                                   ctx->start + (uint32_t)(event.at * 4),
                                   ctx->code[event.at],
                                   "exact_target_set_exceeds_256_values");
                free(one.json);
            } else {
                uint32_t pc = event.kind == EV_ENTRY ? use_pc
                             : ctx->start + (uint32_t)(event.at * 4);
                uint32_t word = event.kind == EV_ENTRY ? use_word : ctx->code[event.at];
                const char *reason = event.kind == EV_ENTRY
                    ? "entry_path_without_definition"
                    : event.kind == EV_CALL
                      ? "call_crossing_without_register_preservation_proof"
                      : "load_result_not_visible_to_immediate_successor";
                domain_breaker(&domain, pc, word, reason);
                buf_add(&json, "{\"kind\":\"%s\",\"pc\":\"0x%08x\","
                        "\"word\":\"0x%08x\",\"proved\":false,"
                        "\"failure\":\"%s\"}",
                        event.kind == EV_ENTRY ? "entry_path_without_definition"
                        : event.kind == EV_CALL ? "call_crossing" : "load_delay",
                        pc, word, reason);
            }
        }
        if (!events.count) {
            domain_breaker(&domain, use_pc, use_word, "no_reaching_definition");
            if (!first) buf_add(&json, ",");
            first = 0;
            buf_add(&json, "{\"kind\":\"no_reaching_definition\","
                    "\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                    "\"failure\":\"%s\"}", use_pc, use_word, domain.reason);
        }
        free(events.rows);
    }

    for (size_t i = 0; i < ctx->words; i++) {
        if (ctx->reachable[i] || def_reg(ctx->code[i]) != reg
            || !flows_to_use(ctx->code, ctx->words, ctx->start, i, reg, use)) continue;
        if (!first) buf_add(&json, ",");
        first = 0;
        buf_add(&json, "{\"definition_pc\":\"0x%08x\","
                "\"definition_word\":\"0x%08x\",\"proved\":false,"
                "\"excluded_from_domain\":true,"
                "\"reason\":\"definition_not_reachable_from_declared_entry\"}",
                ctx->start + (uint32_t)(i * 4), ctx->code[i]);
        domain.excluded_unreachable++;
    }
    buf_add(&json, "]");
    domain.verdict = ctx->reachable[use] && domain.definition_occurrences > 0
                  && !domain.have_breaker;
    if (domain.verdict)
        qsort(domain.values, domain.nvalues, sizeof domain.values[0], value_compare);
    else
        domain.nvalues = 0;
    domain.json = json.text;
    return domain;
}

static void emit_query(const char *spec, int first)
{
    char copy[320];
    char *image_id, *start_text, *end_text, *reg_text, *pc_text, *extra;
    char *parse_end = NULL;
    unsigned long parsed;
    uint32_t start, end, pc;
    int reg, got_reg;
    Image *im;
    size_t offset, words, use;
    uint32_t *code;

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
    im = find_image(image_id);
    if (reg < 0 || !im || end <= start || (end - start) % 4
        || start < im->base || pc < start || pc >= end || (pc - start) % 4)
        fail("query range/register invalid", spec);
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
    Context ctx;
    context_init(&ctx, code, words, start);
    Domain domain = domain_at(&ctx, reg, use);

    if (!first) printf(",\n");
    printf("  {\"target_domain_query\":true,\"image\":"); json_string(image_id);
    printf(",\"function\":\"0x%08x\",\"extent_end\":\"0x%08x\","
           "\"register\":", start, end); json_string(REGS[reg]);
    printf(",\"site_pc\":\"0x%08x\",\"site_word\":\"0x%08x\","
           "\"delay_slot_pc\":\"0x%08x\",\"delay_slot_word\":",
           pc, code[use], pc + 4);
    if (use + 1 < words) printf("\"0x%08x\"", code[use + 1]); else printf("null");
    printf(",\"scope\":\"all paths reachable from the declared extent entry; "
           "external interior-entry exclusion remains a separate consumer gate\","
           "\"whitelist\":[\"lui\",\"ori\",\"andi\",\"addiu_mod32\","
           "\"zero_operand_register_copy\",\"sll\",\"srl\"],"
           "\"reaching_definition_occurrence_count\":%ld,"
           "\"excluded_unreachable_definition_occurrence_count\":%ld,"
           "\"distinct_target_count\":%zu,\"targets\":[",
           domain.definition_occurrences, domain.excluded_unreachable,
           domain.verdict ? domain.nvalues : 0);
    if (domain.verdict) for (size_t i = 0; i < domain.nvalues; i++)
        printf("%s\"0x%08x\"", i ? "," : "", domain.values[i]);
    printf("],\"derivations\":%s,", domain.json);
    if (domain.have_breaker)
        printf("\"breaking_instruction\":{\"pc\":\"0x%08x\","
               "\"word\":\"0x%08x\",\"reason\":\"%s\"},",
               domain.breaker_pc, domain.breaker_word, domain.reason);
    else
        printf("\"breaking_instruction\":null,");
    printf("\"all_reaching_definitions_whitelisted\":%s,"
           "\"full_target_domain_complete\":%s,\"verdict\":%s}",
           domain.verdict ? "true" : "false", domain.verdict ? "true" : "false",
           domain.verdict ? "true" : "false");
    free(domain.json);
    context_free(&ctx);
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
    static const uint32_t INCOMING[] = { 0x02c00008, 0x00000000 };
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
        int verdict; size_t nvalues; uint32_t a, b, breaker;
    } cases[] = {
        { MULTI, 9, 7, 1, 2, 0x80011000, 0x80022000, 0 },
        { BYPASS, 6, 4, 0, 0, 0, 0, 0x02c00008 },
        { LOAD, 4, 2, 0, 0, 0, 0, 0x8c960000 },
        { DELAY, 5, 3, 1, 1, 0x80012340, 0, 0 },
        { INCOMING, 2, 0, 0, 0, 0, 0, 0x02c00008 },
        { ORDINARY_DELAY, 4, 2, 1, 1, 0x80010000, 0, 0 },
        { LIKELY_ANNUL, 4, 2, 0, 0, 0, 0, 0x02c00008 },
        { REGIMM_LINK, 5, 3, 0, 0, 0, 0, 0x04910001 },
        { COP_BRANCH, 4, 2, 1, 1, 0x80010000, 0, 0 },
    };
    int passed = 0;
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        Context ctx;
        context_init(&ctx, cases[i].code, cases[i].words, BASE);
        Domain d = domain_at(&ctx, 22, cases[i].use);
        int ok = d.verdict == cases[i].verdict && d.nvalues == cases[i].nvalues;
        if (d.verdict && d.nvalues) ok = ok && d.values[0] == cases[i].a;
        if (d.verdict && d.nvalues > 1) ok = ok && d.values[1] == cases[i].b;
        if (!d.verdict) ok = ok && d.have_breaker
                           && d.breaker_word == cases[i].breaker;
        if (ok) passed++;
        free(d.json);
        context_free(&ctx);
    }
    printf("{\"tool\":\"phase4_target_exclusion_prover\","
           "\"passed\":%d,\"total\":%zu,\"verdict\":%s}\n",
           passed, sizeof cases / sizeof cases[0],
           passed == (int)(sizeof cases / sizeof cases[0]) ? "true" : "false");
    return passed == (int)(sizeof cases / sizeof cases[0]) ? 0 : 1;
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return self_test();
    if (argc < 3) {
        fprintf(stderr, "usage: %s <image-map> IMAGE:START:END:REG:PC ...\n", argv[0]);
        return 2;
    }
    load_map(argv[1]);
    printf("{\"tool\":\"phase4_target_exclusion_prover\",\"queries\":[\n");
    for (int i = 2; i < argc; i++) emit_query(argv[i], i == 2);
    printf("\n ],\"query_count\":%d}\n", argc - 2);
    for (size_t i = 0; i < N_IMAGES; i++) free(IMAGES[i].bytes);
    return 0;
}
