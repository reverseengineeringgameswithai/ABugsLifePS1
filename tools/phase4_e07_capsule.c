#define _POSIX_C_SOURCE 200809L

#include <glob.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RAM_SIZE 0x200000u
#define OP_TABLE_OFFSET 0x1b2f4u
#define CALL_TABLE_OFFSET 0x1b35cu
#define PROGRAM_LO 0x7745cu
#define PROGRAM_HI 0x77af8u
#define PROGRAM_TABLE_OFFSET 0x77af8u
#define VM_INIT 0x8004c10cu
#define VM_INTERPRETER 0x8004c13cu
#define VM_MOTION 0x8004c8acu
#define SCAN_LO 0x80000u
#define SCAN_HI 0xc0000u
#define SCAN_WORDS ((SCAN_HI - SCAN_LO) / 4u)

typedef struct { uint8_t *data; size_t size, at; } Reader;
typedef struct { uint8_t *data; uint32_t size; } Domain;
typedef struct {
    uint64_t hits;
    uint64_t changed_into_or_out;
    uint32_t first_value;
    uint32_t last_value;
    bool ever;
} Location;

static const uint16_t ADVANCE[26] = {
    4, 2, 4, 6, 2, 2, 2, 2, 2, 4, 2, 4, 4,
    6, 6, 4, 4, 4, 2, 2, 4, 2, 2, 6, 4, 2
};

static const char *NAMES[26] = {
    "jump_back", "park_end", "wait", "wait_random", "random_dir_step",
    "path_next_waypoint", "park_seek", "park_arrive_test", "park_arrive_stop",
    "branch_if_s3", "park_path", "seek_path_endpoint", "call_native",
    "flags_mask", "anim_clip_load", "cond_noise_mask", "chase_radius_scratch",
    "player_proximity", "park_seek18", "park19", "branch_fwd_if_s3",
    "park21", "done_disable", "set_byte_params", "call_play_sound",
    "cond_powerup_flag"
};

static void die(const char *message) {
    fprintf(stderr, "phase4_e07_capsule: %s\n", message);
    exit(1);
}

static const uint8_t *take(Reader *r, size_t n) {
    if (n > r->size - r->at) die("truncated chunk");
    const uint8_t *p = r->data + r->at;
    r->at += n;
    return p;
}

static uint8_t u8(Reader *r) { return take(r, 1)[0]; }
static uint16_t u16(Reader *r) {
    const uint8_t *p = take(r, 2);
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}
static uint32_t u32(Reader *r) {
    const uint8_t *p = take(r, 4);
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint64_t u64(Reader *r) { uint64_t a = u32(r), b = u32(r); return a | (b << 32); }
static uint32_t load32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint16_t load16(const uint8_t *p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }

static uint8_t *decompress(const char *path, size_t *size_out) {
    char command[4096];
    if (snprintf(command, sizeof(command), "zstd -q -d -c '%s'", path) >= (int)sizeof(command))
        die("chunk path too long");
    FILE *pipe = popen(command, "r");
    if (!pipe) die("cannot start zstd");
    size_t cap = 1u << 20, size = 0;
    uint8_t *data = malloc(cap);
    if (!data) die("out of memory");
    for (;;) {
        if (size == cap) {
            cap *= 2;
            uint8_t *grown = realloc(data, cap);
            if (!grown) die("out of memory");
            data = grown;
        }
        size_t got = fread(data + size, 1, cap - size, pipe);
        size += got;
        if (!got) {
            if (ferror(pipe)) die("zstd read failed");
            break;
        }
    }
    if (pclose(pipe) != 0) die("zstd failed");
    *size_out = size;
    return data;
}

static bool hash_ok(const uint8_t *data, size_t size, const uint8_t *expected) {
    uint8_t actual[SHA256_DIGEST_LENGTH];
    SHA256(data, size, actual);
    return memcmp(actual, expected, sizeof(actual)) == 0;
}

static bool program_pointer(uint32_t value) {
    uint32_t p = value & 0x1fffffffu;
    return p >= PROGRAM_LO && p < PROGRAM_HI && (p & 1u) == 0;
}

static uint32_t resolve_stub(const uint8_t *ram, uint32_t stub) {
    uint32_t p = stub & 0x1fffffffu;
    if (p + 4 > RAM_SIZE) return stub;
    uint32_t word = load32(ram + p);
    unsigned opcode = word >> 26;
    if (opcode == 2 || opcode == 3)
        return 0x80000000u | ((word & 0x03ffffffu) << 2);
    return stub;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s CAPSULE_DIRECTORY\n", argv[0]);
        return 2;
    }
    char pattern[4096];
    if (snprintf(pattern, sizeof(pattern), "%s/chunks/*.tcap.zst", argv[1]) >= (int)sizeof(pattern))
        die("capsule path too long");
    glob_t paths = {0};
    if (glob(pattern, 0, NULL, &paths) != 0 || paths.gl_pathc == 0)
        die("no chunks");

    Domain domains[4] = {{0}};
    uint32_t handlers[26] = {0}, stubs[9] = {0}, call_targets[9] = {0};
    uint64_t handler_blocks[26] = {0}, handler_frames[26] = {0};
    uint64_t stub_blocks[9] = {0}, call_target_blocks[9] = {0};
    uint64_t opcode_ip_frames[26] = {0};
    bool valid_ip[(PROGRAM_HI - PROGRAM_LO) / 2u];
    memset(valid_ip, 0, sizeof(valid_ip));
    bool observed_ip[(PROGRAM_HI - PROGRAM_LO) / 2u];
    memset(observed_ip, 0, sizeof(observed_ip));
    Location *locations = calloc(SCAN_WORDS, sizeof(*locations));
    uint32_t *previous_words = calloc(SCAN_WORDS, sizeof(*previous_words));
    if (!locations || !previous_words) die("out of memory");

    bool initialized = false, have_previous = false;
    uint64_t records = 0, hash_mismatches = 0, flow_items = 0, flow_instructions = 0;
    uint64_t interpreter_blocks = 0, interpreter_frames = 0;
    uint64_t init_blocks = 0, init_frames = 0, motion_blocks = 0, motion_frames = 0;
    uint32_t min_ip_refs = UINT32_MAX, max_ip_refs = 0, max_ip_refs_movie = 0;
    uint64_t first_frame = 0, last_frame = 0;
    uint32_t first_movie = 0, last_movie = 0;

    for (size_t chunk = 0; chunk < paths.gl_pathc; ++chunk) {
        size_t raw_size = 0;
        uint8_t *raw = decompress(paths.gl_pathv[chunk], &raw_size);
        Reader r = {raw, raw_size, 0};
        if (memcmp(take(&r, 8), "DSTCAP01", 8) != 0) die("bad magic");
        if (u32(&r) != 1) die("unsupported schema");
        uint32_t mode = u32(&r);
        (void)u64(&r);
        uint32_t register_count = u32(&r);
        for (uint32_t i = 0; i < register_count; ++i) (void)take(&r, u16(&r));

        while (r.at < r.size) {
            if (u8(&r) != 1) die("unknown record tag");
            uint64_t frame = u64(&r);
            (void)u64(&r);
            uint32_t movie = u32(&r);
            (void)u32(&r); (void)u32(&r);
            (void)take(&r, (size_t)register_count * 4u);
            for (unsigned d = 0; d < 3; ++d) {
                uint32_t id = u32(&r), size = u32(&r), runs = u32(&r);
                const uint8_t *expected = take(&r, SHA256_DIGEST_LENGTH);
                if (id < 1 || id > 3) die("bad domain");
                Domain *domain = &domains[id];
                if (!domain->data) {
                    domain->data = calloc(1, size);
                    domain->size = size;
                }
                if (!domain->data || domain->size != size) die("domain size changed");
                for (uint32_t run = 0; run < runs; ++run) {
                    uint32_t offset = u32(&r), length = u32(&r);
                    if (offset > size || length > size - offset) die("bad delta");
                    memcpy(domain->data + offset, take(&r, length), length);
                }
                if (!hash_ok(domain->data, domain->size, expected)) ++hash_mismatches;
            }
            uint8_t *ram = domains[1].data;
            if (!ram || domains[1].size != RAM_SIZE) die("unexpected RAM size");
            if (!initialized) {
                for (unsigned i = 0; i < 26; ++i)
                    handlers[i] = load32(ram + OP_TABLE_OFFSET + i * 4u);
                for (unsigned i = 0; i < 9; ++i) {
                    stubs[i] = load32(ram + CALL_TABLE_OFFSET + i * 4u);
                    call_targets[i] = resolve_stub(ram, stubs[i]);
                }
                uint32_t starts[64];
                size_t count = 0;
                while (count < 64) {
                    uint32_t value = load32(ram + PROGRAM_TABLE_OFFSET + count * 4u);
                    if (!program_pointer(value)) break;
                    starts[count++] = value & 0x1fffffffu;
                }
                for (size_t i = 0; i < count; ++i) {
                    uint32_t start = starts[i];
                    uint32_t end = i + 1 < count ? starts[i + 1] : PROGRAM_HI;
                    for (uint32_t ip = start; ip < end;) {
                        int index = (int)(int16_t)load16(ram + ip) + 1;
                        if (index < 0 || index >= 26) break;
                        valid_ip[(ip - PROGRAM_LO) / 2u] = true;
                        ip += ADVANCE[index];
                    }
                }
                initialized = true;
            }

            uint64_t count = u64(&r);
            flow_items += count;
            bool frame_handler[26] = {0}, frame_interpreter = false, frame_init = false, frame_motion = false;
            for (uint64_t i = 0; i < count; ++i) {
                uint32_t pc = u32(&r);
                uint64_t instructions;
                if (mode == 2) { instructions = u32(&r); (void)u64(&r); }
                else if (mode == 1) instructions = u64(&r);
                else die("unsupported flow mode");
                flow_instructions += instructions;
                if (pc == VM_INTERPRETER) { ++interpreter_blocks; frame_interpreter = true; }
                if (pc == VM_INIT) { ++init_blocks; frame_init = true; }
                if (pc == VM_MOTION) { ++motion_blocks; frame_motion = true; }
                for (unsigned h = 0; h < 26; ++h) {
                    if (pc == handlers[h]) { ++handler_blocks[h]; frame_handler[h] = true; }
                }
                for (unsigned c = 0; c < 9; ++c) {
                    if (pc == stubs[c]) ++stub_blocks[c];
                    if (pc == call_targets[c]) ++call_target_blocks[c];
                }
            }
            interpreter_frames += frame_interpreter;
            init_frames += frame_init;
            motion_frames += frame_motion;
            for (unsigned h = 0; h < 26; ++h) handler_frames[h] += frame_handler[h];

            uint32_t ip_refs = 0;
            bool frame_opcode[26] = {0};
            for (uint32_t word_index = 0; word_index < SCAN_WORDS; ++word_index) {
                uint32_t value = load32(ram + SCAN_LO + word_index * 4u);
                uint32_t physical = value & 0x1fffffffu;
                bool valid = physical >= PROGRAM_LO && physical < PROGRAM_HI &&
                             valid_ip[(physical - PROGRAM_LO) / 2u];
                Location *location = &locations[word_index];
                if (valid) {
                    ++ip_refs;
                    ++location->hits;
                    observed_ip[(physical - PROGRAM_LO) / 2u] = true;
                    int index = (int)(int16_t)load16(ram + physical) + 1;
                    if (index >= 0 && index < 26) frame_opcode[index] = true;
                    if (!location->ever) location->first_value = value;
                    location->last_value = value;
                    location->ever = true;
                }
                if (have_previous && value != previous_words[word_index]) {
                    uint32_t prev_phys = previous_words[word_index] & 0x1fffffffu;
                    bool prev_valid = prev_phys >= PROGRAM_LO && prev_phys < PROGRAM_HI &&
                                      valid_ip[(prev_phys - PROGRAM_LO) / 2u];
                    if (valid || prev_valid) ++location->changed_into_or_out;
                }
                previous_words[word_index] = value;
            }
            for (unsigned op = 0; op < 26; ++op) opcode_ip_frames[op] += frame_opcode[op];
            if (ip_refs < min_ip_refs) min_ip_refs = ip_refs;
            if (ip_refs > max_ip_refs) { max_ip_refs = ip_refs; max_ip_refs_movie = movie; }
            if (!records) { first_frame = frame; first_movie = movie; }
            last_frame = frame; last_movie = movie;
            ++records;
            have_previous = true;
        }
        free(raw);
    }

    uint32_t observed_ips = 0, location_count = 0, changing_locations = 0;
    for (size_t i = 0; i < sizeof(observed_ip); ++i) observed_ips += observed_ip[i];
    for (uint32_t i = 0; i < SCAN_WORDS; ++i) {
        location_count += locations[i].ever;
        changing_locations += locations[i].changed_into_or_out != 0;
    }
    uint32_t stride84_start = 0, stride84_count = 0;
    for (uint32_t i = 0; i < SCAN_WORDS; ++i) {
        if (!locations[i].ever) continue;
        uint32_t count = 1;
        uint32_t next = i + 0x84u / 4u;
        while (next < SCAN_WORDS && locations[next].ever) {
            ++count;
            next += 0x84u / 4u;
        }
        if (count > stride84_count) {
            stride84_count = count;
            stride84_start = 0x80000000u + SCAN_LO + i * 4u;
        }
    }
    const char *id = strrchr(argv[1], '/'); id = id ? id + 1 : argv[1];
    printf("{\n");
    printf("  \"schema\": \"abl-phase4-e07-capsule-v1\",\n");
    printf("  \"row\": \"E07_event_vm\",\n");
    printf("  \"capsule_id\": \"%s\",\n", id);
    printf("  \"chunks\": %zu, \"records\": %" PRIu64 ",\n", paths.gl_pathc, records);
    printf("  \"frame_span\": {\"emulator_first\": %" PRIu64 ", \"emulator_last\": %" PRIu64 ", \"movie_first\": %u, \"movie_last\": %u},\n",
           first_frame, last_frame, first_movie, last_movie);
    printf("  \"integrity\": {\"domain_hash_checks\": %" PRIu64 ", \"hash_mismatches\": %" PRIu64 "},\n", records * 3u, hash_mismatches);
    printf("  \"flow\": {\"items\": %" PRIu64 ", \"instructions\": %" PRIu64 ", \"vm_init_blocks\": %" PRIu64 ", \"vm_init_frames\": %" PRIu64 ", \"interpreter_blocks\": %" PRIu64 ", \"interpreter_frames\": %" PRIu64 ", \"motion_blocks\": %" PRIu64 ", \"motion_frames\": %" PRIu64 "},\n",
           flow_items, flow_instructions, init_blocks, init_frames, interpreter_blocks,
           interpreter_frames, motion_blocks, motion_frames);
    printf("  \"handlers\": [\n");
    for (unsigned i = 0; i < 26; ++i)
    {
        unsigned aliases = 0;
        for (unsigned j = 0; j < 26; ++j) aliases += handlers[j] == handlers[i];
        printf("    {\"index\": %u, \"name\": \"%s\", \"target\": \"0x%08x\", \"target_aliases\": %u, \"target_blocks\": %" PRIu64 ", \"target_frames\": %" PRIu64 "}%s\n",
               i, NAMES[i], handlers[i], aliases, handler_blocks[i], handler_frames[i], i == 25 ? "" : ",");
    }
    printf("  ],\n");
    printf("  \"call_slots\": [\n");
    for (unsigned i = 0; i < 9; ++i)
        printf("    {\"slot\": %u, \"stub\": \"0x%08x\", \"target\": \"0x%08x\", \"stub_blocks\": %" PRIu64 ", \"target_address_blocks_not_call_attributed\": %" PRIu64 "}%s\n",
               i + 1, stubs[i], call_targets[i], stub_blocks[i], call_target_blocks[i], i == 8 ? "" : ",");
    printf("  ],\n");
    printf("  \"runtime_ip_state\": {\"scan_range\": \"0x80080000..0x800c0000\", \"valid_instruction_ips_observed\": %u, \"candidate_locations\": %u, \"changing_candidate_locations\": %u, \"references_per_frame_min\": %u, \"references_per_frame_max\": %u, \"max_movie_frame\": %u, \"dominant_stride_sequence\": {\"ip_field_start\": \"0x%08x\", \"stride\": 132, \"observed_slots\": %u, \"actor_base_inferred_from_ip_offset_112\": \"0x%08x\"}, \"opcode_frames\": [\n",
           observed_ips, location_count, changing_locations, min_ip_refs, max_ip_refs, max_ip_refs_movie,
           stride84_start, stride84_count, stride84_start - 112u);
    for (unsigned i = 0; i < 26; ++i)
        printf("    {\"index\": %u, \"name\": \"%s\", \"frames\": %" PRIu64 "}%s\n",
               i, NAMES[i], opcode_ip_frames[i], i == 25 ? "" : ",");
    printf("  ], \"locations\": [\n");
    bool first = true;
    for (uint32_t i = 0; i < SCAN_WORDS; ++i) {
        if (!locations[i].ever) continue;
        printf("%s    {\"address\": \"0x%08x\", \"frames_valid\": %" PRIu64 ", \"transitions\": %" PRIu64 ", \"first_ip\": \"0x%08x\", \"last_ip\": \"0x%08x\"}",
               first ? "" : ",\n", 0x80000000u + SCAN_LO + i * 4u,
               locations[i].hits, locations[i].changed_into_or_out,
               locations[i].first_value, locations[i].last_value);
        first = false;
    }
    printf("\n  ]}\n");
    printf("}\n");

    for (unsigned i = 1; i <= 3; ++i) free(domains[i].data);
    free(locations); free(previous_words); globfree(&paths);
    return hash_mismatches ? 1 : 0;
}
