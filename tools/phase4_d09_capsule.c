/* Phase 4 D09 offline trace-capsule analyzer. No emulator is launched. */
#define _POSIX_C_SOURCE 200809L
#include <glob.h>
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zstd.h>

enum { RAM_SIZE = 0x200000, MAX_EVENTS = 64, MAX_VM_IPS = 16 };
enum { REDBUG_ADDRESS = 0x800a095c, LIVE_TABLE = 0x80090748 };

typedef struct { const uint8_t *p; size_t n, off; } Buffer;
typedef struct {
    uint32_t frame, id, flags, vm_ip, backlink;
    int16_t hp, reaction, respawn_delay;
    int32_t x, y, z;
    int in_live_table;
} ActorState;
typedef struct { ActorState before, after; uint32_t flow_mask; } Event;

static void fail(const char *message)
{
    fprintf(stderr, "phase4_d09_capsule: %s\n", message);
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
    return (uint16_t)(p[0] | (uint16_t)p[1] << 8);
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
    return (uint16_t)(p[0] | (uint16_t)p[1] << 8);
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
    size_t input_size;
    uint8_t *input = read_file(path, &input_size);
    unsigned long long output_size = ZSTD_getFrameContentSize(input, input_size);
    if (output_size == ZSTD_CONTENTSIZE_ERROR ||
        output_size == ZSTD_CONTENTSIZE_UNKNOWN || output_size > SIZE_MAX)
        fail("invalid zstd frame size");
    uint8_t *output = xmalloc((size_t)output_size);
    size_t got = ZSTD_decompress(output, (size_t)output_size, input, input_size);
    free(input);
    if (ZSTD_isError(got) || got != (size_t)output_size)
        fail("zstd decode failed");
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

static size_t ram_offset(uint32_t address, size_t width)
{
    if (address < 0x80000000 || address - 0x80000000 > RAM_SIZE - width)
        fail("guest RAM address out of range");
    return (size_t)(address - 0x80000000);
}

static int table_contains(const uint8_t *ram, uint32_t address)
{
    size_t table = ram_offset(LIVE_TABLE, 64 * 4);
    for (size_t i = 0; i < 64; ++i)
        if (load_u32(ram + table + i * 4) == address)
            return 1;
    return 0;
}

static ActorState actor_state(const uint8_t *ram, uint32_t frame)
{
    size_t a = ram_offset(REDBUG_ADDRESS, 0x84);
    ActorState s = {0};
    s.frame = frame;
    s.id = load_u32(ram + a);
    s.x = (int32_t)load_u32(ram + a + 4);
    s.y = (int32_t)load_u32(ram + a + 8);
    s.z = (int32_t)load_u32(ram + a + 12);
    s.flags = load_u16(ram + a + 0x5c);
    s.respawn_delay = (int16_t)load_u16(ram + a + 0x62);
    s.reaction = (int16_t)load_u16(ram + a + 0x6c);
    s.hp = (int16_t)load_u16(ram + a + 0x6e);
    s.vm_ip = load_u32(ram + a + 0x70);
    s.backlink = load_u32(ram + a + 0x80);
    s.in_live_table = table_contains(ram, REDBUG_ADDRESS);
    return s;
}

static uint32_t flow_bit(uint32_t pc)
{
    static const uint32_t pcs[] = {
        0x8004c930, 0x8004c9ac, 0x8005905c,
        0x80059144, 0x80059154, 0x8005929c
    };
    for (size_t i = 0; i < sizeof(pcs) / sizeof(pcs[0]); ++i)
        if (pc == pcs[i]) return UINT32_C(1) << i;
    return 0;
}

static void print_state(const ActorState *s)
{
    printf("{\"frame\":%u,\"id\":%u,\"hp\":%d,\"flags\":\"0x%04x\","
           "\"reaction\":%d,\"respawn_delay\":%d,\"vm_ip\":\"0x%08x\","
           "\"position\":[%d,%d,%d],\"in_live_table\":%s}",
           s->frame, s->id, s->hp, s->flags, s->reaction, s->respawn_delay,
           s->vm_ip, s->x, s->y, s->z, s->in_live_table ? "true" : "false");
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s CAPSULE_DIRECTORY\n", argv[0]);
        return 2;
    }
    char pattern[4096];
    snprintf(pattern, sizeof(pattern), "%s/chunks/*.zst", argv[1]);
    glob_t paths = {0};
    if (glob(pattern, 0, NULL, &paths) != 0 || paths.gl_pathc == 0)
        fail("capsule has no chunks");

    uint8_t *domains[4] = {0};
    uint32_t domain_sizes[4] = {0};
    uint64_t records = 0, hash_checks = 0, hash_mismatches = 0;
    uint64_t flow_hits[6] = {0};
    uint32_t vm_ips[MAX_VM_IPS] = {0};
    size_t vm_ip_count = 0;
    Event events[MAX_EVENTS];
    size_t event_count = 0;
    ActorState initial = {0}, final = {0}, previous = {0};
    int have_previous = 0;
    uint64_t live_table_frames = 0, resistance_bit_frames = 0, chase_bit_frames = 0;

    for (size_t file_index = 0; file_index < paths.gl_pathc; ++file_index) {
        size_t raw_size;
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
                uint32_t id = get_u32(&b), size = get_u32(&b);
                uint32_t patch_count = get_u32(&b);
                const uint8_t *expected_hash = take(&b, 32);
                if (id < 1 || id > 3) fail("invalid domain id");
                if (!domains[id]) {
                    domains[id] = calloc(1, size);
                    if (!domains[id]) fail("out of memory");
                    domain_sizes[id] = size;
                } else if (domain_sizes[id] != size) {
                    fail("domain size changed");
                }
                for (uint32_t patch = 0; patch < patch_count; ++patch) {
                    uint32_t offset = get_u32(&b), length = get_u32(&b);
                    if (offset > size || length > size - offset)
                        fail("invalid domain patch");
                    memcpy(domains[id] + offset, take(&b, length), length);
                }
                ++hash_checks;
                if (!sha256_matches(domains[id], size, expected_hash))
                    ++hash_mismatches;
            }
            const uint8_t *ram = NULL;
            for (unsigned id = 1; id <= 3; ++id)
                if (domain_sizes[id] == RAM_SIZE) ram = domains[id];
            if (!ram) fail("capsule record has no RAM domain");
            ActorState current = actor_state(ram, movie_frame);
            if (current.id != 19) fail("pinned actor is not Redbug id 19");

            uint32_t event_flow_mask = 0;
            uint64_t flow_count = get_u64(&b);
            for (uint64_t i = 0; i < flow_count; ++i) {
                uint32_t pc = get_u32(&b);
                if (version == 2) (void)get_u32(&b);
                uint64_t weight = get_u64(&b);
                uint32_t bit = flow_bit(pc);
                event_flow_mask |= bit;
                for (unsigned k = 0; k < 6; ++k)
                    if (bit & (UINT32_C(1) << k)) flow_hits[k] += weight;
            }

            if (!have_previous) initial = current;
            if (have_previous &&
                (current.hp != previous.hp || current.flags != previous.flags)) {
                if (event_count >= MAX_EVENTS) fail("too many actor events");
                events[event_count++] = (Event){previous, current, event_flow_mask};
            }
            int known = 0;
            for (size_t i = 0; i < vm_ip_count; ++i)
                if (vm_ips[i] == current.vm_ip) known = 1;
            if (!known && vm_ip_count < MAX_VM_IPS) vm_ips[vm_ip_count++] = current.vm_ip;
            if (current.in_live_table) ++live_table_frames;
            if (current.flags & 0x40) ++resistance_bit_frames;
            if (current.flags & 0x02) ++chase_bit_frames;
            previous = final = current;
            have_previous = 1;
            ++records;
        }
        free(raw);
    }

    printf("{\n  \"schema\": \"abl.phase4.d09.capsule.v1\",\n");
    printf("  \"row\": \"D09_cockroaches_redbug\",\n");
    printf("  \"capsule\": {\"path\": \"%s\", \"boundary_records\": %" PRIu64
           ", \"hash_checks\": %" PRIu64 ", \"hash_mismatches\": %" PRIu64 "},\n",
           argv[1], records, hash_checks, hash_mismatches);
    printf("  \"actor_address\": \"0x%08x\",\n", REDBUG_ADDRESS);
    printf("  \"initial\": "); print_state(&initial); printf(",\n");
    printf("  \"final\": "); print_state(&final); printf(",\n");
    printf("  \"coverage\": {\"live_table_frames\": %" PRIu64
           ", \"berry_tough_bit_frames\": %" PRIu64
           ", \"chase_bit_frames\": %" PRIu64 "},\n",
           live_table_frames, resistance_bit_frames, chase_bit_frames);
    printf("  \"observed_vm_ips\": [");
    for (size_t i = 0; i < vm_ip_count; ++i)
        printf("%s\"0x%08x\"", i ? "," : "", vm_ips[i]);
    printf("],\n  \"events\": [\n");
    for (size_t i = 0; i < event_count; ++i) {
        printf("    {\"before\":"); print_state(&events[i].before);
        printf(",\"after\":"); print_state(&events[i].after);
        printf(",\"relevant_flow_mask\":\"0x%02x\"}%s\n",
               events[i].flow_mask, i + 1 == event_count ? "" : ",");
    }
    printf("  ],\n  \"relevant_block_weights\": {"
           "\"0x8004c930\":%" PRIu64 ",\"0x8004c9ac\":%" PRIu64
           ",\"0x8005905c\":%" PRIu64 ",\"0x80059144\":%" PRIu64
           ",\"0x80059154\":%" PRIu64 ",\"0x8005929c\":%" PRIu64 "},\n",
           flow_hits[0], flow_hits[1], flow_hits[2], flow_hits[3], flow_hits[4], flow_hits[5]);
    printf("  \"bounded_conclusion\": \"The retained movie covers two nonlethal Redbug hits and frame-boundary chase/resistance state. It does not contain the terminal hit and is not used to claim one.\"\n}\n");

    for (unsigned id = 1; id <= 3; ++id) free(domains[id]);
    globfree(&paths);
    return hash_mismatches ? 1 : 0;
}
