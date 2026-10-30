#define _POSIX_C_SOURCE 200809L
#include <glob.h>
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zstd.h>

enum { RAM_SIZE = 0x200000, MAX_EVENTS = 16 };

typedef struct { const uint8_t *p; size_t n, off; } Buffer;
typedef struct {
    int valid;
    uint32_t movie_frame;
    int16_t health, timer, power, state, ground, air, animation;
    int32_t vx, vy, vz;
} Snapshot;
typedef struct {
    uint32_t movie_frame;
    int16_t before, after, timer, power, state, ground, air, animation;
    int32_t vx, vy, vz, previous_vx, previous_vy, previous_vz;
} HealthEvent;
typedef struct {
    const char *path;
    uint64_t records, hash_checks, hash_mismatches;
    int16_t min_health, max_health, min_timer, max_timer;
    uint32_t timer_start, timer_end;
    unsigned positive_ticks, negative_ticks, nonmonotonic_steps;
    HealthEvent events[MAX_EVENTS];
    size_t event_count;
} Result;

static void fail(const char *message)
{
    fprintf(stderr, "phase4_d03_capsule: %s\n", message);
    exit(2);
}

static void *xmalloc(size_t n)
{
    void *p = malloc(n ? n : 1);
    if (!p) fail("out of memory");
    return p;
}

static const uint8_t *take(Buffer *b, size_t n)
{
    if (n > b->n - b->off) fail("truncated capsule record");
    const uint8_t *p = b->p + b->off;
    b->off += n;
    return p;
}

static uint8_t get_u8(Buffer *b) { return *take(b, 1); }
static uint16_t get_u16(Buffer *b)
{
    const uint8_t *p = take(b, 2);
    return (uint16_t)(p[0] | p[1] << 8);
}
static uint32_t get_u32(Buffer *b)
{
    const uint8_t *p = take(b, 4);
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint64_t get_u64(Buffer *b)
{
    uint64_t lo = get_u32(b), hi = get_u32(b);
    return lo | hi << 32;
}
static uint16_t load_u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | p[1] << 8);
}
static uint32_t load_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint8_t *read_file(const char *path, size_t *size_out)
{
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    if (fseek(f, 0, SEEK_END) != 0) fail("cannot seek input");
    long end = ftell(f);
    if (end < 0 || fseek(f, 0, SEEK_SET) != 0) fail("cannot size input");
    size_t size = (size_t)end;
    uint8_t *data = xmalloc(size);
    if (fread(data, 1, size, f) != size) fail("cannot read input");
    fclose(f);
    *size_out = size;
    return data;
}

static uint8_t *decompress_file(const char *path, size_t *size_out)
{
    size_t input_size = 0;
    uint8_t *input = read_file(path, &input_size);
    unsigned long long size = ZSTD_getFrameContentSize(input, input_size);
    if (size == ZSTD_CONTENTSIZE_ERROR || size == ZSTD_CONTENTSIZE_UNKNOWN ||
        size > SIZE_MAX) fail("invalid zstd frame size");
    uint8_t *output = xmalloc((size_t)size);
    size_t got = ZSTD_decompress(output, (size_t)size, input, input_size);
    free(input);
    if (ZSTD_isError(got) || got != (size_t)size) fail("zstd decode failed");
    *size_out = got;
    return output;
}

static int sha256_matches(const uint8_t *data, size_t size,
                          const uint8_t expected[32])
{
    uint8_t digest[32];
    size_t digest_size = 0;
    if (!EVP_Q_digest(NULL, "SHA256", NULL, data, size,
                      digest, &digest_size) || digest_size != 32)
        fail("SHA-256 failed");
    return memcmp(digest, expected, 32) == 0;
}

static Snapshot snapshot(const uint8_t *ram, uint32_t movie_frame)
{
    Snapshot s = { .valid = 1, .movie_frame = movie_frame };
    s.vx = (int32_t)load_u32(ram + 0xa652c);
    s.vy = (int32_t)load_u32(ram + 0xa6530);
    s.vz = (int32_t)load_u32(ram + 0xa6534);
    s.power = (int16_t)load_u16(ram + 0xa657e);
    s.state = (int16_t)load_u16(ram + 0xa6580);
    s.ground = (int16_t)load_u16(ram + 0xa6582);
    s.air = (int16_t)load_u16(ram + 0xa6584);
    s.animation = (int16_t)load_u16(ram + 0xa6588);
    s.timer = (int16_t)load_u16(ram + 0xa6592);
    s.health = (int16_t)load_u16(ram + 0xa6594);
    return s;
}

static Result analyze(const char *directory)
{
    Result result = {
        .path = directory,
        .min_health = INT16_MAX, .max_health = INT16_MIN,
        .min_timer = INT16_MAX, .max_timer = INT16_MIN,
        .timer_start = UINT32_MAX, .timer_end = UINT32_MAX
    };
    char pattern[4096];
    snprintf(pattern, sizeof(pattern), "%s/chunks/*.zst", directory);
    glob_t paths = {0};
    if (glob(pattern, 0, NULL, &paths) != 0 || paths.gl_pathc == 0)
        fail("capsule has no chunks");

    uint8_t *domains[4] = {0};
    uint32_t domain_sizes[4] = {0};
    Snapshot previous = {0};
    for (size_t file_index = 0; file_index < paths.gl_pathc; ++file_index) {
        size_t raw_size = 0;
        uint8_t *raw = decompress_file(paths.gl_pathv[file_index], &raw_size);
        Buffer b = { raw, raw_size, 0 };
        if (memcmp(take(&b, 8), "DSTCAP01", 8) != 0) fail("bad capsule magic");
        uint32_t version = get_u32(&b);
        if (version < 1 || version > 2) fail("unsupported capsule version");
        (void)get_u32(&b);
        (void)get_u64(&b);
        uint32_t register_count = get_u32(&b);
        for (uint32_t i = 0; i < register_count; ++i) {
            uint16_t length = get_u16(&b);
            (void)take(&b, length);
        }

        while (b.off < b.n) {
            if (get_u8(&b) != 1) fail("unexpected capsule tag");
            (void)get_u64(&b);
            (void)get_u64(&b);
            uint32_t movie_frame = get_u32(&b);
            (void)get_u32(&b);
            (void)get_u32(&b);
            (void)take(&b, (size_t)register_count * 4);
            for (unsigned domain_index = 0; domain_index < 3; ++domain_index) {
                uint32_t id = get_u32(&b);
                uint32_t size = get_u32(&b);
                uint32_t patch_count = get_u32(&b);
                const uint8_t *expected_hash = take(&b, 32);
                if (id < 1 || id > 3) fail("invalid domain id");
                if (!domains[id]) {
                    domains[id] = calloc(1, size);
                    if (!domains[id]) fail("out of memory");
                    domain_sizes[id] = size;
                }
                for (uint32_t patch = 0; patch < patch_count; ++patch) {
                    uint32_t offset = get_u32(&b), length = get_u32(&b);
                    if (offset > size || length > size - offset)
                        fail("invalid domain patch");
                    memcpy(domains[id] + offset, take(&b, length), length);
                }
                result.hash_checks++;
                if (!sha256_matches(domains[id], size, expected_hash))
                    result.hash_mismatches++;
            }

            const uint8_t *ram = NULL;
            for (unsigned id = 1; id <= 3; ++id)
                if (domain_sizes[id] == RAM_SIZE) ram = domains[id];
            if (!ram) fail("capsule record has no RAM domain");
            Snapshot current = snapshot(ram, movie_frame);
            if (current.health < result.min_health) result.min_health = current.health;
            if (current.health > result.max_health) result.max_health = current.health;
            if (current.timer < result.min_timer) result.min_timer = current.timer;
            if (current.timer > result.max_timer) result.max_timer = current.timer;
            if (previous.valid) {
                if (current.health != previous.health) {
                    if (result.event_count >= MAX_EVENTS) fail("too many health events");
                    HealthEvent *e = &result.events[result.event_count++];
                    *e = (HealthEvent){
                        current.movie_frame, previous.health, current.health,
                        current.timer, current.power, current.state,
                        current.ground, current.air, current.animation,
                        current.vx, current.vy, current.vz,
                        previous.vx, previous.vy, previous.vz
                    };
                }
                if (previous.timer == 0 && current.timer != 0 &&
                    result.timer_start == UINT32_MAX)
                    result.timer_start = current.movie_frame;
                if (previous.timer != 0 && current.timer == 0 &&
                    result.timer_end == UINT32_MAX)
                    result.timer_end = current.movie_frame;
                if (previous.timer > 0 && current.timer >= 0) {
                    if (current.timer < previous.timer)
                        result.positive_ticks += (unsigned)(previous.timer - current.timer);
                    else if (current.timer != previous.timer)
                        result.nonmonotonic_steps++;
                }
                if (previous.timer < 0 && current.timer <= 0) {
                    if (current.timer > previous.timer)
                        result.negative_ticks += (unsigned)(current.timer - previous.timer);
                    else if (current.timer != previous.timer)
                        result.nonmonotonic_steps++;
                }
            }
            previous = current;

            uint64_t flow_count = get_u64(&b);
            for (uint64_t i = 0; i < flow_count; ++i) {
                (void)get_u32(&b);
                if (version == 2) {
                    (void)get_u32(&b);
                    (void)get_u64(&b);
                } else {
                    (void)get_u64(&b);
                }
            }
            result.records++;
        }
        free(raw);
    }
    for (unsigned id = 1; id <= 3; ++id) free(domains[id]);
    globfree(&paths);
    return result;
}

static void print_optional_frame(uint32_t frame)
{
    if (frame == UINT32_MAX) printf("null"); else printf("%u", frame);
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s CAPSULE...\n", argv[0]);
        return 2;
    }
    printf("{\n  \"schema\": \"abl.phase4.d03.capsule.v1\",\n");
    printf("  \"capsules\": [\n");
    uint64_t total_records = 0, total_checks = 0, total_bad = 0;
    size_t total_events = 0;
    for (int i = 1; i < argc; ++i) {
        Result r = analyze(argv[i]);
        total_records += r.records;
        total_checks += r.hash_checks;
        total_bad += r.hash_mismatches;
        total_events += r.event_count;
        printf("    {\"path\":\"%s\",\"boundary_records\":%" PRIu64
               ",\"hash_checks\":%" PRIu64 ",\"hash_mismatches\":%" PRIu64
               ",\"health_range\":[%d,%d],\"timer_range\":[%d,%d],"
               "\"timer_start_movie_frame\":",
               r.path, r.records, r.hash_checks, r.hash_mismatches,
               r.min_health, r.max_health, r.min_timer, r.max_timer);
        print_optional_frame(r.timer_start);
        printf(",\"timer_end_movie_frame\":");
        print_optional_frame(r.timer_end);
        printf(",\"positive_ticks\":%u,\"negative_ticks\":%u,"
               "\"nonmonotonic_steps\":%u,\"health_events\":[",
               r.positive_ticks, r.negative_ticks, r.nonmonotonic_steps);
        for (size_t e = 0; e < r.event_count; ++e) {
            const HealthEvent *h = &r.events[e];
            if (e) putchar(',');
            printf("{\"movie_frame\":%u,\"before\":%d,\"after\":%d,"
                   "\"timer\":%d,\"power\":%d,\"state\":%d,"
                   "\"ground\":%d,\"air\":%d,\"animation\":%d,"
                   "\"velocity\":[%d,%d,%d],\"previous_velocity\":[%d,%d,%d]}",
                   h->movie_frame, h->before, h->after, h->timer, h->power,
                   h->state, h->ground, h->air, h->animation,
                   h->vx, h->vy, h->vz,
                   h->previous_vx, h->previous_vy, h->previous_vz);
        }
        printf("]}%s\n", i + 1 == argc ? "" : ",");
    }
    printf("  ],\n  \"totals\": {\"boundary_records\":%" PRIu64
           ",\"hash_checks\":%" PRIu64 ",\"hash_mismatches\":%" PRIu64
           ",\"health_events\":%zu}\n}\n",
           total_records, total_checks, total_bad, total_events);
    return total_bad ? 1 : 0;
}
