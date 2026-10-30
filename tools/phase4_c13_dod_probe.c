#define _POSIX_C_SOURCE 200809L
#include <glob.h>
#include <inttypes.h>
#include <limits.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <zstd.h>

#define RAM_SIZE 0x200000u
#define PLAYER 0x0a6500u
#define HARVESTER_ACTOR 0x0a1dfcu
#define CONTACT_BASE 0x0b0d18u
#define CONTACT_STRIDE 0x38u
#define CONTACT_SLOTS 64u
#define MAX_EVENTS 64u
#define MAX_FLOW 2048u

typedef struct { const uint8_t *p, *end; const char *path; } Reader;
typedef struct {
    uint32_t first, last, slot, move_frames;
    int32_t first_xyz[3], last_xyz[3], prev_xyz[3];
    uint8_t target_minus_one, flags_ea, closed;
} GrainEvent;
typedef struct { uint32_t pc; uint64_t count; uint32_t frames; } Flow;

static uint8_t *dom[4];
static uint32_t dsz[4];
static uint64_t domain_hashes, changed_runs;
static uint32_t records, first_movie = UINT32_MAX, last_movie;
static uint32_t actor_id;
static int32_t actor_xyz[3];
static uint32_t actor_samples, actor_changes;
static uint8_t scene_id;
static uint32_t first_state_one = UINT32_MAX, first_flag = UINT32_MAX;
static uint32_t grain_count_rises;
static uint8_t prior_grain_count;
static int active_event[CONTACT_SLOTS];
static GrainEvent events[MAX_EVENTS];
static size_t event_count;
static Flow flows[MAX_FLOW];
static size_t flow_count;

static void die(const char *m, const char *p) {
    fprintf(stderr, "c13_dod_probe: %s%s%s\n", m, p ? ": " : "", p ? p : "");
    exit(1);
}
static void need(Reader *r, size_t n) {
    if ((size_t)(r->end - r->p) < n) die("truncated capsule chunk", r->path);
}
static uint8_t u8(Reader *r) { need(r, 1); return *r->p++; }
static uint16_t u16(Reader *r) {
    need(r, 2); uint16_t v = r->p[0] | ((uint16_t)r->p[1] << 8); r->p += 2; return v;
}
static uint32_t u32(Reader *r) {
    need(r, 4);
    uint32_t v = r->p[0] | ((uint32_t)r->p[1] << 8) |
                 ((uint32_t)r->p[2] << 16) | ((uint32_t)r->p[3] << 24);
    r->p += 4; return v;
}
static uint64_t u64(Reader *r) { uint64_t a = u32(r), b = u32(r); return a | (b << 32); }
static const uint8_t *take(Reader *r, size_t n) { need(r, n); const uint8_t *p = r->p; r->p += n; return p; }
static uint16_t rd16(const uint8_t *p) { return p[0] | ((uint16_t)p[1] << 8); }
static int16_t rd16s(const uint8_t *p) { return (int16_t)rd16(p); }
static uint32_t rd32(const uint8_t *p) {
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static int32_t rd32s(const uint8_t *p) { return (int32_t)rd32(p); }

static uint8_t *read_file(const char *path, size_t *size) {
    struct stat st;
    if (stat(path, &st) || st.st_size < 0) die("cannot stat", path);
    FILE *f = fopen(path, "rb");
    if (!f) die("cannot open", path);
    uint8_t *p = malloc((size_t)st.st_size + 1);
    if (!p) die("out of memory", NULL);
    if (fread(p, 1, (size_t)st.st_size, f) != (size_t)st.st_size) die("cannot read", path);
    fclose(f); p[st.st_size] = 0; *size = (size_t)st.st_size; return p;
}
static uint8_t *decompress(const char *path, size_t *size) {
    size_t src_size;
    uint8_t *src = read_file(path, &src_size);
    unsigned long long n = ZSTD_getFrameContentSize(src, src_size);
    if (n == ZSTD_CONTENTSIZE_ERROR || n == ZSTD_CONTENTSIZE_UNKNOWN || n > SIZE_MAX)
        die("invalid zstd frame size", path);
    uint8_t *dst = malloc((size_t)n);
    if (!dst) die("out of memory", NULL);
    size_t got = ZSTD_decompress(dst, (size_t)n, src, src_size);
    free(src);
    if (ZSTD_isError(got) || got != (size_t)n) die("zstd decode failed", path);
    *size = got; return dst;
}
static void sha256_hex(const char *path, char out[65]) {
    size_t n; uint8_t *p = read_file(path, &n), d[SHA256_DIGEST_LENGTH];
    SHA256(p, n, d); free(p);
    for (size_t i = 0; i < sizeof(d); i++) sprintf(out + i * 2, "%02x", d[i]);
    out[64] = 0;
}
static int in_c13_range(uint32_t pc) {
    return (pc >= 0x80051db4u && pc < 0x80052094u) ||
           (pc >= 0x80053814u && pc < 0x800547e0u) ||
           (pc >= 0x80054eacu && pc < 0x80055188u) ||
           (pc >= 0x800586b0u && pc < 0x80058af8u) ||
           (pc >= 0x8005a308u && pc < 0x8005b134u);
}
static void add_flow(uint32_t pc, uint64_t count) {
    if (!in_c13_range(pc)) return;
    for (size_t i = 0; i < flow_count; i++) {
        if (flows[i].pc == pc) { flows[i].count += count; flows[i].frames++; return; }
    }
    if (flow_count >= MAX_FLOW) die("too many flow entries", NULL);
    flows[flow_count++] = (Flow){pc, count, 1};
}
static void close_event(unsigned slot, uint32_t movie) {
    int i = active_event[slot];
    if (i < 0) return;
    events[i].last = movie;
    events[i].closed = 1;
    active_event[slot] = -1;
}
static void capture(uint32_t movie) {
    const uint8_t *ram = dom[1];
    if (!ram || dsz[1] != RAM_SIZE) die("RAM domain missing", NULL);
    if (first_movie == UINT32_MAX) first_movie = movie;
    last_movie = movie; records++;
    if (records == 1) scene_id = ram[0x082504u];

    uint32_t id = rd32(ram + HARVESTER_ACTOR);
    int32_t xyz[3] = {
        rd32s(ram + HARVESTER_ACTOR + 4),
        rd32s(ram + HARVESTER_ACTOR + 8),
        rd32s(ram + HARVESTER_ACTOR + 12)
    };
    if (!actor_samples) {
        actor_id = id;
        memcpy(actor_xyz, xyz, sizeof(xyz));
    } else if (id != actor_id || memcmp(actor_xyz, xyz, sizeof(xyz))) {
        actor_changes++;
    }
    actor_samples++;

    if (rd16s(ram + PLAYER + 0x7e) == 1 && first_state_one == UINT32_MAX) first_state_one = movie;
    if ((rd16(ram + PLAYER + 0x90) & 0x80) && first_flag == UINT32_MAX) first_flag = movie;
    uint8_t count = ram[PLAYER + 0xa1];
    if (records > 1 && count > prior_grain_count) grain_count_rises += count - prior_grain_count;
    prior_grain_count = count;

    for (unsigned slot = 0; slot < CONTACT_SLOTS; slot++) {
        const uint8_t *r = ram + CONTACT_BASE + slot * CONTACT_STRIDE;
        uint16_t action = rd16(r + 0x20);
        int16_t ttl = rd16s(r + 0x22);
        uint8_t flags = r[0x33];
        int is_grain = action == 0x14 && ttl > 0;
        if (!is_grain) { close_event(slot, movie); continue; }
        if (active_event[slot] < 0) {
            if (event_count >= MAX_EVENTS) die("too many grain events", NULL);
            GrainEvent *e = &events[event_count];
            memset(e, 0, sizeof(*e));
            e->first = e->last = movie; e->slot = slot;
            e->target_minus_one = rd32(r + 0x10) == 0xffffffffu;
            e->flags_ea = flags == 0xeau;
            for (int q = 0; q < 3; q++) {
                e->first_xyz[q] = e->last_xyz[q] = e->prev_xyz[q] = rd32s(r + q * 4);
            }
            active_event[slot] = (int)event_count++;
        } else {
            GrainEvent *e = &events[active_event[slot]];
            int moved = 0;
            for (int q = 0; q < 3; q++) {
                int32_t v = rd32s(r + q * 4);
                moved |= v != e->prev_xyz[q];
                e->prev_xyz[q] = e->last_xyz[q] = v;
            }
            e->move_frames += moved;
            e->last = movie;
            e->target_minus_one &= rd32(r + 0x10) == 0xffffffffu;
            e->flags_ea &= flags == 0xeau;
        }
    }
}
static void read_chunk(const char *path, uint32_t *mode_expected, uint32_t *regs_expected) {
    size_t n; uint8_t *raw = decompress(path, &n); Reader r = {raw, raw + n, path};
    if (memcmp(take(&r, 8), "DSTCAP01", 8) || u32(&r) != 1) die("capsule schema mismatch", path);
    uint32_t mode = u32(&r); (void)u64(&r); uint32_t regs = u32(&r);
    for (uint32_t i = 0; i < regs; i++) { uint16_t len = u16(&r); (void)take(&r, len); }
    if (*mode_expected == UINT32_MAX) { *mode_expected = mode; *regs_expected = regs; }
    else if (*mode_expected != mode || *regs_expected != regs) die("chunk schema drift", path);
    while (r.p < r.end) {
        if (u8(&r) != 1) die("bad record kind", path);
        (void)u64(&r); (void)u64(&r);
        uint32_t movie = u32(&r); (void)u32(&r); (void)u32(&r);
        for (uint32_t i = 0; i < regs; i++) (void)u32(&r);
        for (int q = 0; q < 3; q++) {
            uint32_t id = u32(&r), size = u32(&r), runs = u32(&r);
            const uint8_t *expected = take(&r, SHA256_DIGEST_LENGTH);
            if (id < 1 || id > 3) die("bad domain id", path);
            if (!dom[id]) { dom[id] = calloc(1, size); dsz[id] = size; }
            if (!dom[id] || dsz[id] != size) die("domain size drift", path);
            for (uint32_t j = 0; j < runs; j++) {
                uint32_t off = u32(&r), len = u32(&r);
                const uint8_t *data = take(&r, len);
                if ((uint64_t)off + len > size) die("domain delta overflow", path);
                memcpy(dom[id] + off, data, len); changed_runs++;
            }
            uint8_t actual[SHA256_DIGEST_LENGTH];
            SHA256(dom[id], size, actual);
            if (memcmp(actual, expected, sizeof(actual))) die("domain hash mismatch", path);
            domain_hashes++;
        }
        uint64_t block_count = u64(&r);
        for (uint64_t i = 0; i < block_count; i++) {
            uint32_t pc = u32(&r); uint64_t hits;
            if (mode == 2) { uint32_t instruction_count = u32(&r); (void)u64(&r); hits = instruction_count; }
            else if (mode == 1) hits = u64(&r);
            else if (mode == 0) hits = 0;
            else die("bad block mode", path);
            add_flow(pc, hits);
        }
        capture(movie);
    }
    free(raw);
}
static int cmp_flow(const void *a, const void *b) {
    uint32_t x = ((const Flow *)a)->pc, y = ((const Flow *)b)->pc;
    return x < y ? -1 : x > y;
}

typedef struct {
    const char *path;
    int total_records, type3f_records, grain_count, other_kinds, ok;
    char sha[65];
} DatSummary;
static void scan_dat(DatSummary *d) {
    size_t n; uint8_t *p = read_file(d->path, &n); sha256_hex(d->path, d->sha);
    if (n < 4) { free(p); return; }
    int32_t total = rd32s(p); size_t off = 4; d->total_records = total;
    for (int i = 0; i < total; i++) {
        if (off + 4 > n) { free(p); return; }
        uint16_t count = rd16(p + off); int16_t type = rd16s(p + off + 2);
        int64_t size;
        if (type < 0) {
            int32_t x = (int32_t)count * 3 + 1;
            int32_t words = (x + (x >> 31)) >> 1;
            size = (int64_t)words * 4 + 0x10;
        } else if (type == 0x3f) size = (int64_t)count * 0x10 + 4;
        else size = (int64_t)count * 12 + 4;
        if (size < 4 || off + (uint64_t)size > n) { free(p); return; }
        if (type == 0x3f) {
            d->type3f_records++;
            for (unsigned j = 0; j < count; j++) {
                uint8_t kind = p[off + 4 + j * 0x10 + 0x0c];
                if (kind == 0x14) d->grain_count++; else d->other_kinds++;
            }
        }
        off += (size_t)size;
    }
    d->ok = 1; free(p);
}
static const char *base_name(const char *p) { const char *s = strrchr(p, '/'); return s ? s + 1 : p; }
static int grain_for(const DatSummary *d, size_t n, const char *name) {
    for (size_t i = 0; i < n; i++) if (!strcmp(base_name(d[i].path), name)) return d[i].grain_count;
    return -1;
}

typedef struct { char names[32][96]; size_t count, actor35_count; } Census;
static Census scan_census(const char *path) {
    size_t n; char *p = (char *)read_file(path, &n); Census out = {0};
    char *levels = strstr(p, "\"levels\"");
    if (!levels || !(levels = strchr(levels, '{'))) die("cannot parse census levels", path);
    char *cur = levels + 1;
    while (*cur) {
        while (*cur && (*cur == ' ' || *cur == '\n' || *cur == '\r' || *cur == '\t' || *cur == ',')) cur++;
        if (*cur == '}') break;
        if (*cur != '"') die("bad census level key", path);
        char *end = strchr(cur + 1, '"'); if (!end) die("bad census string", path);
        size_t len = (size_t)(end - cur - 1); if (len >= sizeof(out.names[0])) len = sizeof(out.names[0]) - 1;
        char name[96] = {0}; memcpy(name, cur + 1, len);
        char *open = strchr(end, '{'); if (!open) die("bad census level object", path);
        int depth = 1; char *q = open + 1;
        while (*q && depth) { if (*q == '{') depth++; else if (*q == '}') depth--; q++; }
        if (depth) die("unterminated census level", path);
        out.count++;
        int has35 = 0;
        for (char *hit = open; (hit = strstr(hit, "\"id\": 35")) && hit < q; hit += 8) has35 = 1;
        if (has35 && out.actor35_count < 32) {
            strcpy(out.names[out.actor35_count++], name);
        }
        cur = q;
    }
    free(p); return out;
}

int main(int argc, char **argv) {
    if (argc < 6) {
        fprintf(stderr, "usage: %s CAPSULE_DIR PHASE1_CENSUS B06_POWERUPS CONFIG DAT...\n", argv[0]);
        return 2;
    }
    for (unsigned i = 0; i < CONTACT_SLOTS; i++) active_event[i] = -1;
    char pattern[PATH_MAX];
    if (snprintf(pattern, sizeof(pattern), "%s/chunks/*.tcap.zst", argv[1]) >= (int)sizeof(pattern))
        die("capsule path too long", argv[1]);
    glob_t g;
    if (glob(pattern, 0, NULL, &g) || !g.gl_pathc) die("no capsule chunks", pattern);
    uint32_t mode = UINT32_MAX, regs = 0;
    for (size_t i = 0; i < g.gl_pathc; i++) read_chunk(g.gl_pathv[i], &mode, &regs);
    for (unsigned i = 0; i < CONTACT_SLOTS; i++) close_event(i, last_movie);
    qsort(flows, flow_count, sizeof(flows[0]), cmp_flow);

    Census census = scan_census(argv[2]);
    size_t power_n; char *power = (char *)read_file(argv[3], &power_n);
    int frontier_open = strstr(power, "\"b06_b08_current_state\": \"OPEN.") != NULL;
    int frontier_251 = strstr(power, "251 same-width accesses") != NULL;
    int indirect_149 = strstr(power, "149 indirect calls") != NULL;
    int overlay_4967 = strstr(power, "4,967 overlay pointer-based accesses") != NULL;
    free(power);

    size_t dat_n = (size_t)(argc - 5);
    DatSummary *dat = calloc(dat_n, sizeof(*dat));
    if (!dat) die("out of memory", NULL);
    for (size_t i = 0; i < dat_n; i++) { dat[i].path = argv[i + 5]; scan_dat(&dat[i]); }
    static const char *stage_dat[15] = {
        "LEVEL01_LEVEL.DAT", "LEVEL03_LEVEL.DAT", "LEVEL02_LEVEL.DAT",
        "LEVEL06_LEVEL.DAT", "LEVEL10_LEVEL.DAT", "LEVEL01_LEVEL1.DAT",
        "LEVEL04_LEVEL.DAT", "LEVEL05_LEVEL.DAT", "LEVEL04_LEVEL1.DAT",
        "LEVEL07_LEVEL.DAT", "LEVEL02_LEVEL1.DAT", "LEVEL03_LEVEL1.DAT",
        "LEVEL09_LEVEL.DAT", "LEVEL08_LEVEL.DAT", "LEVEL05_LEVEL1.DAT"
    };
    static const uint8_t campaign_scene[16] = {
        17, 1, 3, 2, 6, 10, 11, 4, 5, 14, 7, 12, 13, 9, 8, 15
    };
    int fixture_stage = -1;
    for (int i = 1; i <= 15; i++) if (campaign_scene[i] == scene_id) fixture_stage = i;

    char census_sha[65], power_sha[65], config_sha[65];
    sha256_hex(argv[2], census_sha); sha256_hex(argv[3], power_sha); sha256_hex(argv[4], config_sha);
    printf("{\n");
    printf("  \"schema\":\"abl-phase4-c13-dod-probe-v1\",\n");
    printf("  \"capsule\":{\"directory\":\"%s\",\"chunks\":%zu,\"records\":%u,\"first_movie\":%u,\"last_movie\":%u,\"block_mode\":%u,\"register_count\":%u,\"domain_hashes_checked\":%" PRIu64 ",\"changed_runs\":%" PRIu64 "},\n",
           argv[1], g.gl_pathc, records, first_movie, last_movie, mode, regs, domain_hashes, changed_runs);
    printf("  \"fixture_identity\":{\"scene_id\":%u,\"campaign_stage\":%d,\"actor_id\":%u,\"actor_xyz_at_start\":[%d,%d,%d],\"actor_samples\":%u,\"actor_changed_samples\":%u,\"actor_position_is_runtime_mirrored\":true,\"first_state_one\":%u,\"first_flag_0x80\":%u},\n",
           scene_id, fixture_stage,
           actor_id, actor_xyz[0], actor_xyz[1], actor_xyz[2], actor_samples, actor_changes,
           first_state_one, first_flag);
    int all_target_minus_one = event_count > 0, all_flags_ea = event_count > 0;
    for (size_t i = 0; i < event_count; i++) {
        all_target_minus_one &= events[i].target_minus_one;
        all_flags_ea &= events[i].flags_ea;
    }
    printf("  \"grain_contacts\":{\"events\":%zu,\"counter_rises\":%u,\"all_target_minus_one\":%s,\"all_flags_0xea\":%s,\"events_detail\":[",
           event_count, grain_count_rises,
           all_target_minus_one ? "true" : "false", all_flags_ea ? "true" : "false");
    for (size_t i = 0; i < event_count; i++) {
        GrainEvent *e = &events[i];
        if (i) putchar(',');
        printf("{\"slot\":%u,\"first\":%u,\"last\":%u,\"move_frames\":%u,\"target_minus_one\":%s,\"flags_0xea\":%s,\"first_xyz\":[%d,%d,%d],\"last_xyz\":[%d,%d,%d]}",
               e->slot, e->first, e->last, e->move_frames,
               e->target_minus_one ? "true" : "false", e->flags_ea ? "true" : "false",
               e->first_xyz[0], e->first_xyz[1], e->first_xyz[2],
               e->last_xyz[0], e->last_xyz[1], e->last_xyz[2]);
    }
    printf("]},\n");
    printf("  \"passive_block_flow\":[");
    for (size_t i = 0; i < flow_count; i++) {
        if (i) putchar(',');
        printf("{\"pc\":\"0x%08x\",\"count\":%" PRIu64 ",\"frames\":%u}",
               flows[i].pc, flows[i].count, flows[i].frames);
    }
    printf("],\n");
    printf("  \"phase1_actor35_survey\":{\"sha256\":\"%s\",\"levels_surveyed\":%zu,\"observed_in\":[",
           census_sha, census.count);
    for (size_t i = 0; i < census.actor35_count; i++) {
        if (i) putchar(',');
        printf("\"%s\"", census.names[i]);
    }
    printf("]},\n");
    printf("  \"dat_survey\":{\"files\":%zu,\"rows\":[", dat_n);
    for (size_t i = 0; i < dat_n; i++) {
        if (i) putchar(',');
        printf("{\"file\":\"%s\",\"sha256\":\"%s\",\"parse_ok\":%s,\"records\":%d,\"type3f_records\":%d,\"grain_kind_0x14\":%d,\"other_type3f_kinds\":%d}",
               dat[i].path, dat[i].sha, dat[i].ok ? "true" : "false", dat[i].total_records,
               dat[i].type3f_records, dat[i].grain_count, dat[i].other_kinds);
    }
    printf("],\"campaign_stages\":[");
    for (int i = 0; i < 15; i++) {
        if (i) putchar(',');
        printf("{\"stage\":%d,\"dat\":\"%s\",\"grain_kind_0x14\":%d}",
               i + 1, stage_dat[i], grain_for(dat, dat_n, stage_dat[i]));
    }
    printf("]},\n");
    printf("  \"inherited_frontier\":{\"source_sha256\":\"%s\",\"state_open\":%s,\"same_width_251_present\":%s,\"indirect_calls_149_present\":%s,\"overlay_pointer_accesses_4967_present\":%s,\"complete_frontier_met\":false},\n",
           power_sha, frontier_open ? "true" : "false", frontier_251 ? "true" : "false",
           indirect_149 ? "true" : "false", overlay_4967 ? "true" : "false");
    printf("  \"machine_contract_sha256\":\"%s\"\n", config_sha);
    printf("}\n");
    free(dat); globfree(&g);
    for (int i = 1; i <= 3; i++) free(dom[i]);
    return 0;
}
