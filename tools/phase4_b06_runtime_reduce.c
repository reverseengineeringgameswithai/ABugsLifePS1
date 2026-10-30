/*
 * Reduce the targeted B06 Interpreter trace without Python.
 *
 * Inputs are the two end-of-replay summaries, seven execTrace pages, and two
 * accessLog pages captured under /tmp. The reducer rejects desync, truncation,
 * an altered hit census, or an altered writer census. It emits both the compact
 * machine artifact and the Obsidian experiment note.
 */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint32_t state[8];
    uint64_t bits;
    uint8_t block[64];
    size_t used;
} Sha256;

typedef struct {
    const char *path;
    char *data;
    size_t size;
    char sha256[65];
} Input;

static uint32_t rotr32(uint32_t x, unsigned n)
{
    return (x >> n) | (x << (32u - n));
}

static void sha256_transform(Sha256 *ctx, const uint8_t block[64])
{
    static const uint32_t k[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    uint32_t w[64];
    uint32_t a, b, c, d, e, f, g, h;
    unsigned i;

    for (i = 0; i < 16; i++) {
        const uint8_t *p = block + i * 4u;
        w[i] = ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
               ((uint32_t)p[2] << 8) | p[3];
    }
    for (; i < 64; i++) {
        uint32_t s0 = rotr32(w[i - 15], 7) ^ rotr32(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = rotr32(w[i - 2], 17) ^ rotr32(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = ctx->state[0]; b = ctx->state[1]; c = ctx->state[2]; d = ctx->state[3];
    e = ctx->state[4]; f = ctx->state[5]; g = ctx->state[6]; h = ctx->state[7];
    for (i = 0; i < 64; i++) {
        uint32_t s1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
        uint32_t ch = (e & f) ^ (~e & g);
        uint32_t t1 = h + s1 + ch + k[i] + w[i];
        uint32_t s0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2 = s0 + maj;
        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }
    ctx->state[0] += a; ctx->state[1] += b; ctx->state[2] += c; ctx->state[3] += d;
    ctx->state[4] += e; ctx->state[5] += f; ctx->state[6] += g; ctx->state[7] += h;
}

static void sha256_init(Sha256 *ctx)
{
    static const uint32_t initial[8] = {
        0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
        0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19
    };
    memcpy(ctx->state, initial, sizeof(initial));
    ctx->bits = 0;
    ctx->used = 0;
}

static void sha256_update(Sha256 *ctx, const uint8_t *data, size_t size)
{
    ctx->bits += (uint64_t)size * 8u;
    while (size != 0) {
        size_t take = 64u - ctx->used;
        if (take > size)
            take = size;
        memcpy(ctx->block + ctx->used, data, take);
        ctx->used += take;
        data += take;
        size -= take;
        if (ctx->used == 64u) {
            sha256_transform(ctx, ctx->block);
            ctx->used = 0;
        }
    }
}

static void sha256_final(Sha256 *ctx, char output[65])
{
    uint8_t digest[32];
    unsigned i;

    ctx->block[ctx->used++] = 0x80;
    if (ctx->used > 56u) {
        memset(ctx->block + ctx->used, 0, 64u - ctx->used);
        sha256_transform(ctx, ctx->block);
        ctx->used = 0;
    }
    memset(ctx->block + ctx->used, 0, 56u - ctx->used);
    for (i = 0; i < 8; i++)
        ctx->block[63u - i] = (uint8_t)(ctx->bits >> (i * 8u));
    sha256_transform(ctx, ctx->block);
    for (i = 0; i < 8; i++) {
        digest[i * 4u] = (uint8_t)(ctx->state[i] >> 24);
        digest[i * 4u + 1u] = (uint8_t)(ctx->state[i] >> 16);
        digest[i * 4u + 2u] = (uint8_t)(ctx->state[i] >> 8);
        digest[i * 4u + 3u] = (uint8_t)ctx->state[i];
    }
    for (i = 0; i < 32; i++)
        sprintf(output + i * 2u, "%02x", digest[i]);
    output[64] = '\0';
}

static void die(const char *message)
{
    fprintf(stderr, "phase4_b06_runtime_reduce: %s\n", message);
    exit(1);
}

static void load_input(Input *input)
{
    FILE *file = fopen(input->path, "rb");
    long size;
    Sha256 sha;

    if (file == NULL) {
        perror(input->path);
        exit(2);
    }
    fseek(file, 0, SEEK_END);
    size = ftell(file);
    rewind(file);
    if (size < 0)
        die("input size failed");
    input->size = (size_t)size;
    input->data = malloc(input->size + 1u);
    if (input->data == NULL || fread(input->data, 1, input->size, file) != input->size)
        die("input read failed");
    fclose(file);
    input->data[input->size] = '\0';
    sha256_init(&sha);
    sha256_update(&sha, (const uint8_t *)input->data, input->size);
    sha256_final(&sha, input->sha256);
}

static const char *after_key(const char *start, const char *key)
{
    const char *found = strstr(start, key);
    const char *colon;
    if (found == NULL)
        return NULL;
    colon = strchr(found + strlen(key), ':');
    if (colon == NULL)
        return NULL;
    colon++;
    while (*colon == ' ' || *colon == '\n' || *colon == '\t' || *colon == '\r')
        colon++;
    return colon;
}

static uint64_t json_u64(const char *start, const char *key)
{
    const char *value = after_key(start, key);
    char *end;
    uint64_t result;
    if (value == NULL)
        die("missing numeric JSON key");
    result = strtoull(value, &end, 0);
    if (end == value)
        die("invalid numeric JSON value");
    return result;
}

static int json_bool(const char *start, const char *key)
{
    const char *value = after_key(start, key);
    if (value == NULL)
        die("missing boolean JSON key");
    if (strncmp(value, "true", 4) == 0)
        return 1;
    if (strncmp(value, "false", 5) == 0)
        return 0;
    die("invalid boolean JSON value");
    return 0;
}

static void json_string(const char *start, const char *key, char *out, size_t out_size)
{
    const char *value = after_key(start, key);
    const char *end;
    size_t length;
    if (value == NULL || *value != '"')
        die("missing string JSON key");
    value++;
    end = strchr(value, '"');
    if (end == NULL)
        die("unterminated JSON string");
    length = (size_t)(end - value);
    if (length + 1u > out_size)
        die("JSON string too long");
    memcpy(out, value, length);
    out[length] = '\0';
}

static size_t count_text(const char *text, const char *needle)
{
    size_t count = 0;
    size_t length = strlen(needle);
    while ((text = strstr(text, needle)) != NULL) {
        count++;
        text += length;
    }
    return count;
}

static int states_equal(const char *a, const char *b)
{
    const char *pa = strstr(a, "\"state\"");
    const char *pb = strstr(b, "\"state\"");
    unsigned compared = 0;
    if (pa == NULL || pb == NULL)
        die("missing state section");
    while (compared < 3) {
        char ha[1024];
        char hb[1024];
        pa = strstr(pa, "\"hex\"");
        pb = strstr(pb, "\"hex\"");
        if (pa == NULL || pb == NULL)
            die("missing state hex field");
        json_string(pa, "\"hex\"", ha, sizeof(ha));
        json_string(pb, "\"hex\"", hb, sizeof(hb));
        if (strcmp(ha, hb) != 0)
            return 0;
        pa += 5;
        pb += 5;
        compared++;
    }
    return 1;
}

static uint64_t summary_status_u64(const char *json, const char *key)
{
    const char *status = strstr(json, "\"status\"");
    if (status == NULL)
        die("missing summary status");
    return json_u64(status, key);
}

static void summary_status_string(const char *json, const char *key, char *out, size_t size)
{
    const char *status = strstr(json, "\"status\"");
    if (status == NULL)
        die("missing summary status");
    json_string(status, key, out, size);
}

static void write_json_string(FILE *file, const char *text)
{
    fputc('"', file);
    while (*text != '\0') {
        if (*text == '"' || *text == '\\')
            fputc('\\', file);
        fputc(*text++, file);
    }
    fputc('"', file);
}

int main(int argc, char **argv)
{
    Input inputs[11];
    const uint64_t expected_exec[7] = {0, 0, 0, 0, 1, 625, 1};
    uint64_t exec_totals[7];
    uint64_t access_totals[2];
    uint64_t clean_frame, trace_frame, clean_cycle, trace_cycle;
    char clean_pc[32], trace_pc[32];
    int state_match;
    size_t i;
    FILE *json;
    FILE *note;

    if (argc != 14) {
        fprintf(stderr,
                "usage: %s CLEAN TRACE EXEC1..EXEC7 ACCESS1 ACCESS2 OUT_JSON OUT_NOTE\n",
                argv[0]);
        return 2;
    }
    for (i = 0; i < 11; i++) {
        inputs[i].path = argv[i + 1];
        load_input(&inputs[i]);
    }

    clean_frame = summary_status_u64(inputs[0].data, "\"frame\"");
    trace_frame = summary_status_u64(inputs[1].data, "\"frame\"");
    clean_cycle = summary_status_u64(inputs[0].data, "\"cycle\"");
    trace_cycle = summary_status_u64(inputs[1].data, "\"cycle\"");
    summary_status_string(inputs[0].data, "\"pc\"", clean_pc, sizeof(clean_pc));
    summary_status_string(inputs[1].data, "\"pc\"", trace_pc, sizeof(trace_pc));
    state_match = states_equal(inputs[0].data, inputs[1].data);
    if (clean_frame != trace_frame || clean_cycle != trace_cycle ||
        strcmp(clean_pc, trace_pc) != 0 || !state_match)
        die("instrumented replay diverged from control");

    for (i = 0; i < 7; i++) {
        exec_totals[i] = json_u64(inputs[i + 2].data, "\"total\"");
        if (json_bool(inputs[i + 2].data, "\"truncated\"") ||
            exec_totals[i] != expected_exec[i])
            die("execTrace census mismatch or truncation");
    }
    for (i = 0; i < 2; i++) {
        access_totals[i] = json_u64(inputs[i + 9].data, "\"total\"");
        if (json_bool(inputs[i + 9].data, "\"truncated\""))
            die("accessLog truncated");
    }
    if (access_totals[0] != 401 || access_totals[1] != 1)
        die("accessLog census mismatch");
    if (count_text(inputs[9].data, "\"instruction_pc\": \"0x80048654\"") != 400 ||
        count_text(inputs[9].data, "\"instruction_pc\": \"0x800588d0\"") != 1 ||
        count_text(inputs[10].data, "\"instruction_pc\": \"0x8004a888\"") != 1)
        die("writer attribution mismatch");
    if (count_text(inputs[7].data, "\"v0\": \"0x800a0000\"") != 625)
        die("positive-slot visual base mismatch");

    json = fopen(argv[12], "w");
    if (json == NULL) {
        perror(argv[12]);
        return 2;
    }
    fprintf(json, "{\n");
    fprintf(json, "  \"schema\": \"phase4-b06-interpreter-local-v1\",\n");
    fprintf(json, "  \"row\": \"B06_invincibility\",\n");
    fprintf(json, "  \"status\": \"accepted_bounded_runtime_evidence_static_frontier_open\",\n");
    fprintf(json, "  \"movie\": {\"path\": \"movies/Phase4/Interpreter/B06_invincibility_lifecycle.movie.json\", \"sha256\": \"cce2866f28a8e3fa7c153af446b30c9f745e0377f70ce929d220fe542cb654cf\", \"version\": 4, \"frames\": 1242, \"reproducible\": true},\n");
    fprintf(json, "  \"control_match\": {\"frame\": %" PRIu64 ", \"cycle\": %" PRIu64 ", \"pc\": \"%s\", \"player_and_input_state_equal\": true},\n",
            clean_frame, clean_cycle, clean_pc);
    fprintf(json, "  \"exec_hits\": {\"0x80048E30\": 0, \"0x80055874\": 0, \"0x80055CF4\": 0, \"0x80055D14\": 0, \"0x800588D0\": 1, \"0x80055BC4\": 625, \"0x8004A888\": 1, \"truncated\": false},\n");
    fprintf(json, "  \"writes\": {\"power_slot_total\": 401, \"grant_0x800588D0\": 1, \"tick_0x80048654\": 400, \"health_0x8004A888\": 1, \"truncated\": false},\n");
    fprintf(json, "  \"interpretation\": {\"ordinary_b06_lifecycle_uses_known_paths_only\": true, \"four_local_candidates_executed\": false, \"runtime_absence_is_static_disjointness\": false, \"strict_frontier_closed\": false},\n");
    fprintf(json, "  \"input_hashes\": [\n");
    for (i = 0; i < 11; i++) {
        fprintf(json, "    {\"path\": ");
        write_json_string(json, inputs[i].path);
        fprintf(json, ", \"bytes\": %zu, \"sha256\": \"%s\"}%s\n",
                inputs[i].size, inputs[i].sha256, i + 1u == 11u ? "" : ",");
    }
    fprintf(json, "  ],\n");
    fprintf(json, "  \"disposition\": \"B06 remains Partial/Open; no further Interpreter movie can close the remaining static frontier\"\n");
    fprintf(json, "}\n");
    fclose(json);

    note = fopen(argv[13], "w");
    if (note == NULL) {
        perror(argv[13]);
        return 2;
    }
    fprintf(note,
        "---\n"
        "type: experiment\n"
        "id: EXP_2026-08-04_phase4_b06_interpreter_local_residual\n"
        "created: 2026-08-04\n"
        "status: completed\n"
        "phase4_row: B06_invincibility\n"
        "row_status: partial_open\n"
        "---\n\n"
        "# Phase 4 B06 Interpreter local-residual trace\n\n"
        "## Result\n\n"
        "The operator's version-4 Interpreter movie was useful and replayed with no instrumentation desync. The clean and traced normal-speed runs ended at the same emulator frame `%" PRIu64 "`, cycle `%" PRIu64 "`, PC `%s`, and identical 168-byte player plus adjacent input-state fingerprint. The movie was reproducible and neither trace ring truncated.\n\n"
        "The four local static residual PCs did not execute anywhere in the complete natural B06 lifecycle:\n\n"
        "```text\n"
        "0x80048E30  0 hits\n"
        "0x80055874  0 hits\n"
        "0x80055CF4  0 hits\n"
        "0x80055D14  0 hits\n"
        "```\n\n"
        "This is a bounded negative for ordinary B06 behavior, not a proof that those instructions can never alias the slot on another path.\n\n"
        "## Positive lifecycle evidence\n\n"
        "- `0x800588D0` executed once and wrote the natural value 400.\n"
        "- `0x80048654` performed exactly 400 two-byte countdown writes.\n"
        "- `0x80055BC4` executed 625 times with base register `v0 = 0x800A0000`, confirming the positive-slot visual test.\n"
        "- `0x8004A888` executed once after expiry and wrote health `3 -> 2`.\n"
        "- Active-period contacts produced no health write; the only health write was the intended post-expiry control.\n\n"
        "## Provenance\n\n"
        "- Movie: `movies/Phase4/Interpreter/B06_invincibility_lifecycle.movie.json`, SHA-256 `cce2866f28a8e3fa7c153af446b30c9f745e0377f70ce929d220fe542cb654cf`.\n"
        "- Start state SHA-256: `4127047a1469ad01b742a8ec3eb53e835dc52b116dbf6c3dab5bade6f04639ec`.\n"
        "- DuckStation binary SHA-256: `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`.\n"
        "- Mounted media: pristine `SCUS-94288`, zero overlays.\n"
        "- Isolated config: `/tmp/duckstation-b06-local-20260804-01`, port `24451`; owned PID `2233529` stopped through the config-scoped launcher.\n"
        "- Raw transient evidence and its hashes are inventoried in `analysis/phase4_b06_runtime_local_20260804.json`.\n"
        "- Reducer: `tools/phase4_b06_runtime_reduce.c`.\n\n"
        "## Disposition\n\n"
        "B06 remains **Partial/Open**. The movie closes the runtime question: none of the four residual instructions belongs to the ordinary grant, active visual, protection, expiry, or post-expiry damage path. It does not close the remaining static intersection frontier. Another B06 Interpreter movie would repeat known paths and cannot prove unexecuted-path absence; further closure work is C/ASM interprocedural analysis.\n\n"
        "Related: [[EXP_2026-08-04_phase4_b06_static_frontier_continuation]], [[EXP_2026-08-01_phase4_b06_b08_power_slot]], and [[SYS_player_power_slot]].\n",
        clean_frame, clean_cycle, clean_pc);
    fclose(note);

    printf("B06 RUNTIME REDUCE PASS: control frame=%" PRIu64 " cycle=%" PRIu64
           " local=0/4 grant=1 visual=625 slot_writes=401 health_writes=1\n",
           clean_frame, clean_cycle);
    for (i = 0; i < 11; i++)
        free(inputs[i].data);
    return 0;
}
