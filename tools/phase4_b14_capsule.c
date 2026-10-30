#define _POSIX_C_SOURCE 200809L

#include <glob.h>
#include <inttypes.h>
#include <limits.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zstd.h>

typedef struct { const uint8_t *p, *e; } Reader;
typedef struct { uint8_t *p; uint32_t n; } Domain;
typedef struct {
    int active;
    uint32_t born;
    int16_t last_timer;
    int16_t last_state;
} SpikeTrack;

static unsigned failures;

static void fail(const char *s)
{
    fprintf(stderr, "phase4_b14_capsule: %s\n", s);
    failures++;
}

static void fatal(const char *s)
{
    fail(s);
    exit(2);
}

static void need(Reader *r, size_t n)
{
    if ((size_t)(r->e - r->p) < n)
        fatal("truncated capsule");
}

static const uint8_t *take(Reader *r, size_t n)
{
    const uint8_t *p;
    need(r, n);
    p = r->p;
    r->p += n;
    return p;
}

static uint8_t q8(Reader *r) { return *take(r, 1); }
static uint16_t q16(Reader *r)
{
    const uint8_t *p = take(r, 2);
    return p[0] | ((uint16_t)p[1] << 8);
}
static uint32_t q32(Reader *r)
{
    const uint8_t *p = take(r, 4);
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}
static uint64_t q64(Reader *r)
{
    uint64_t lo = q32(r), hi = q32(r);
    return lo | (hi << 32);
}

static uint8_t *slurp(const char *path, size_t *n)
{
    FILE *f = fopen(path, "rb");
    long z;
    uint8_t *p;
    if (!f) {
        perror(path);
        exit(2);
    }
    if (fseek(f, 0, SEEK_END) != 0 || (z = ftell(f)) < 0)
        fatal("cannot size file");
    rewind(f);
    p = malloc((size_t)z);
    if (!p || fread(p, 1, (size_t)z, f) != (size_t)z)
        fatal("cannot read file");
    fclose(f);
    *n = (size_t)z;
    return p;
}

static uint16_t u16(const uint8_t *p)
{
    return p[0] | ((uint16_t)p[1] << 8);
}
static int16_t s16(const uint8_t *p) { return (int16_t)u16(p); }
static uint32_t u32(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}
static int32_t s32(const uint8_t *p) { return (int32_t)u32(p); }

static int kind(const uint8_t *p)
{
    uint16_t action = u16(p + 0x20);
    int16_t state = s16(p + 0x2c);
    uint8_t flags = p[0x33];
    if (action == 46 && state == 7 && (flags & 0x82) == 0x82) return 31;
    if (action == 12 && state == -41 && (flags & 0x83) == 0x83) return 37;
    if (action == 9 && state == -42 && (flags & 0xe3) == 0xe3) return 38;
    if (action == 15 && state == -43 && (flags & 0xa3) == 0xa3) return 39;
    if (action == 8 && state == -60 && s16(p + 0x28) == 100 &&
        (flags & 0xe3) == 0xe3) return 59;
    if (action == 8 && state == 19 && (flags & 0xe2) == 0xe2) return 60;
    return -1;
}

static int live(const uint8_t *p)
{
    return s16(p + 0x22) > 0;
}

static void expect_events(const char *name, const uint32_t *got, unsigned n,
                          const uint32_t *want, unsigned wn)
{
    if (n != wn || memcmp(got, want, wn * sizeof(*want)) != 0) {
        fprintf(stderr, "%s mismatch: got", name);
        for (unsigned i = 0; i < n; i++) fprintf(stderr, " %u", got[i]);
        fputc('\n', stderr);
        failures++;
    }
}

int main(int argc, char **argv)
{
    glob_t paths = {0};
    char pattern[PATH_MAX];
    Domain domain[4] = {{0}};
    char **register_names = NULL;
    uint32_t register_count = 0, block_mode = 0;
    uint8_t previous_contact[64][0x38] = {{0}};
    uint8_t previous_plant[20][0x30] = {{0}};
    SpikeTrack spikes[64] = {{0}};
    uint32_t plant_birth[4] = {0}, plant_type[4] = {0};
    uint32_t e31[4] = {0}, e37[8] = {0}, e38[4] = {0}, e39[4] = {0};
    uint32_t e59[8] = {0}, e60[8] = {0}, spike_ages[8] = {0};
    unsigned np = 0, n31 = 0, n37 = 0, n38 = 0, n39 = 0, n59 = 0, n60 = 0, na = 0;
    int32_t vx_min = INT32_MAX, vx_max = INT32_MIN;
    int32_t vy_min = INT32_MAX, vy_max = INT32_MIN;
    int32_t vz_min = INT32_MAX, vz_max = INT32_MIN;
    uint64_t frames = 0, hashes = 0, blocks = 0;
    uint64_t type6_blocks = 0, type7_blocks = 0, alloc_blocks = 0, radial_blocks = 0;

    static const uint32_t want_plants[] = {120, 1030, 2074, 2950};
    static const uint32_t want_types[] = {7, 7, 6, 7};
    static const uint32_t want31[] = {2102};
    static const uint32_t want37[] = {314, 482, 650};
    static const uint32_t want38[] = {1392};
    static const uint32_t want39[] = {3144};
    static const uint32_t want59[] = {1224, 1560, 3312, 3480, 3648};
    static const uint32_t want60[] = {1304, 1642, 3396, 3560, 3734};
    static const uint32_t want_ages[] = {80, 82, 84, 80, 86};

    if (argc != 2) {
        fprintf(stderr, "usage: %s CAPSULE_DIRECTORY\n", argv[0]);
        return 2;
    }
    snprintf(pattern, sizeof(pattern), "%s/chunks/*.tcap.zst", argv[1]);
    if (glob(pattern, 0, NULL, &paths) != 0)
        fatal("no capsule chunks");

    for (size_t fi = 0; fi < paths.gl_pathc; fi++) {
        size_t compressed_size;
        uint8_t *compressed = slurp(paths.gl_pathv[fi], &compressed_size);
        unsigned long long raw_size = ZSTD_getFrameContentSize(compressed, compressed_size);
        uint8_t *raw;
        size_t decoded;
        Reader r;

        if (raw_size == ZSTD_CONTENTSIZE_ERROR || raw_size == ZSTD_CONTENTSIZE_UNKNOWN)
            fatal("invalid zstd frame size");
        raw = malloc((size_t)raw_size);
        decoded = ZSTD_decompress(raw, (size_t)raw_size, compressed, compressed_size);
        free(compressed);
        if (ZSTD_isError(decoded) || decoded != (size_t)raw_size)
            fatal("zstd decode failed");
        r.p = raw;
        r.e = raw + decoded;
        if (memcmp(take(&r, 8), "DSTCAP01", 8) != 0 || q32(&r) != 1)
            fatal("unsupported capsule schema");
        {
            uint32_t bm = q32(&r);
            uint32_t n;
            (void)q64(&r);
            n = q32(&r);
            if (!register_names) {
                block_mode = bm;
                register_count = n;
                register_names = calloc(n, sizeof(*register_names));
                for (uint32_t i = 0; i < n; i++) {
                    uint16_t z = q16(&r);
                    register_names[i] = calloc((size_t)z + 1, 1);
                    memcpy(register_names[i], take(&r, z), z);
                }
            } else {
                if (bm != block_mode || n != register_count)
                    fatal("capsule schema drift");
                for (uint32_t i = 0; i < n; i++) {
                    uint16_t z = q16(&r);
                    if (strlen(register_names[i]) != z ||
                        memcmp(register_names[i], take(&r, z), z) != 0)
                        fatal("register schema drift");
                }
            }
        }

        while (r.p < r.e) {
            uint64_t emulator_frame;
            uint32_t movie_frame;
            if (q8(&r) != 1) fatal("record tag mismatch");
            emulator_frame = q64(&r);
            (void)emulator_frame;
            (void)q64(&r);
            movie_frame = q32(&r);
            (void)q32(&r);
            (void)q32(&r);
            for (uint32_t i = 0; i < register_count; i++) (void)q32(&r);

            for (unsigned q = 0; q < 3; q++) {
                uint32_t id = q32(&r), size = q32(&r), runs = q32(&r);
                const uint8_t *wanted_hash = take(&r, SHA256_DIGEST_LENGTH);
                uint8_t actual_hash[SHA256_DIGEST_LENGTH];
                if (id < 1 || id > 3) fatal("invalid domain id");
                if (!domain[id].p) {
                    domain[id].p = calloc(1, size);
                    domain[id].n = size;
                }
                if (domain[id].n != size) fatal("domain size drift");
                for (uint32_t j = 0; j < runs; j++) {
                    uint32_t offset = q32(&r), length = q32(&r);
                    if ((uint64_t)offset + length > size) fatal("domain delta out of range");
                    memcpy(domain[id].p + offset, take(&r, length), length);
                }
                SHA256(domain[id].p, size, actual_hash);
                if (memcmp(actual_hash, wanted_hash, sizeof(actual_hash)) != 0)
                    fatal("frame-domain hash mismatch");
                hashes++;
            }

            for (unsigned i = 0; i < 20; i++) {
                uint8_t *p = domain[1].p + ((0x80090bf0u + i * 0x30u) & 0x1fffff);
                int16_t t = s16(p), pt = s16(previous_plant[i]);
                if ((t == 6 || t == 7) && t != pt && np < 4) {
                    plant_birth[np] = movie_frame;
                    plant_type[np] = (uint32_t)t;
                    np++;
                }
                memcpy(previous_plant[i], p, 0x30);
            }

            for (unsigned i = 0; i < 64; i++) {
                uint8_t *p = domain[1].p + ((0x800b0d18u + i * 0x38u) & 0x1fffff);
                int k = kind(p), pk = kind(previous_contact[i]);
                int now = live(p), was = live(previous_contact[i]);
                if (now && (!was || k != pk)) {
                    if (k == 31 && n31 < 4) e31[n31++] = movie_frame;
                    if (k == 37 && n37 < 8) e37[n37++] = movie_frame;
                    if (k == 38 && n38 < 4) e38[n38++] = movie_frame;
                    if (k == 39 && n39 < 4) e39[n39++] = movie_frame;
                    if (k == 59 && n59 < 8) {
                        int32_t vx = s32(p + 0x0c), vy = s32(p + 0x10), vz = s32(p + 0x14);
                        e59[n59++] = movie_frame;
                        if (vx < vx_min) vx_min = vx;
                        if (vx > vx_max) vx_max = vx;
                        if (vy < vy_min) vy_min = vy;
                        if (vy > vy_max) vy_max = vy;
                        if (vz < vz_min) vz_min = vz;
                        if (vz > vz_max) vz_max = vz;
                        if (s32(p + 0x18) != 128) fail("constructor-59 acceleration changed");
                        spikes[i].active = 1;
                        spikes[i].born = movie_frame;
                    }
                    if (k == 60 && n60 < 8) e60[n60++] = movie_frame;
                }
                if (spikes[i].active) {
                    if (!(k == 59 && now)) {
                        if (na < 8) spike_ages[na++] = movie_frame - spikes[i].born;
                        if (spikes[i].last_state == 19 || spikes[i].last_timer <= 1)
                            fail("fixture spike did not retire on terrain/world contact");
                        spikes[i].active = 0;
                    } else {
                        spikes[i].last_timer = s16(p + 0x22);
                        spikes[i].last_state = s16(p + 0x2c);
                    }
                }
                memcpy(previous_contact[i], p, 0x38);
            }

            {
                uint64_t count = q64(&r);
                for (uint64_t i = 0; i < count; i++) {
                    uint32_t pc = q32(&r);
                    uint64_t hits = q64(&r);
                    blocks += hits;
                    if (pc >= 0x8005c6f0u && pc < 0x8005c744u) type6_blocks += hits;
                    if (pc >= 0x8005c744u && pc < 0x8005c818u) type7_blocks += hits;
                    if (pc >= 0x80059e44u && pc < 0x8005a0e0u) alloc_blocks += hits;
                    if (pc >= 0x800579e0u && pc < 0x80057a94u) radial_blocks += hits;
                }
            }
            frames++;
        }
        free(raw);
    }

    expect_events("plant births", plant_birth, np, want_plants, 4);
    expect_events("plant types", plant_type, np, want_types, 4);
    expect_events("constructor 31", e31, n31, want31, 1);
    expect_events("constructor 37", e37, n37, want37, 3);
    expect_events("constructor 38", e38, n38, want38, 1);
    expect_events("constructor 39", e39, n39, want39, 1);
    expect_events("constructor 59", e59, n59, want59, 5);
    expect_events("constructor 60", e60, n60, want60, 5);
    expect_events("spike ages", spike_ages, na, want_ages, 5);
    if (frames != 3796 || hashes != 11388 || block_mode != 1 ||
        type6_blocks != 361 || type7_blocks != 1471 ||
        alloc_blocks != 42174 || radial_blocks != 170)
        fail("capsule totals or block-flow coverage changed");

    printf("{\n");
    printf("  \"records\": %" PRIu64 ",\n", frames);
    printf("  \"verified_domain_hashes\": %" PRIu64 ",\n", hashes);
    printf("  \"all_domain_hashes_match\": true,\n");
    printf("  \"plant_birth_frames\": [120, 1030, 2074, 2950],\n");
    printf("  \"tier1_outputs\": {\"constructor37\": [314, 482, 650], \"constructor59\": []},\n");
    printf("  \"tier2_outputs\": {\"constructor38\": [1392], \"constructor59\": [1224, 1560]},\n");
    printf("  \"tier3_outputs\": {\"constructor31\": [2102], \"constructor59\": []},\n");
    printf("  \"tier4_outputs\": {\"constructor39\": [3144], \"constructor59\": [3312, 3480, 3648]},\n");
    printf("  \"type7_first_fire_delay_frames\": 194,\n");
    printf("  \"type7_repeat_period_frames\": 168,\n");
    printf("  \"type6_one_shot_delay_frames\": 28,\n");
    printf("  \"observed_spike_velocity\": {\"vx\": [%d, %d], \"vy\": [%d, %d], \"vz\": [%d, %d], \"ay\": 128},\n",
           vx_min, vx_max, vy_min, vy_max, vz_min, vz_max);
    printf("  \"spike_terrain_retirement_ages\": [80, 82, 84, 80, 86],\n");
    printf("  \"constructor60_impact_effects\": 5,\n");
    printf("  \"block_hits\": {\"type6\": %" PRIu64 ", \"type7\": %" PRIu64
           ", \"allocator\": %" PRIu64 ", \"radial_helper\": %" PRIu64 "},\n",
           type6_blocks, type7_blocks, alloc_blocks, radial_blocks);
    printf("  \"guard_failures\": %u\n", failures);
    printf("}\n");
    return failures ? 3 : 0;
}
