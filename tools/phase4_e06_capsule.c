#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RAM_SIZE 0x200000u
#define POOL_OFFSET 0x0b0d18u
#define POOL_COUNT 64u
#define RECORD_SIZE 0x38u
#define CURSOR_OFFSET 0x08234cu
#define DESCRIPTOR_TABLE_OFFSET 0x096b98u
#define DESCRIPTOR_COUNT 50u
#define DESCRIPTOR_BOUNDARY_COUNT 128u

typedef struct {
    uint8_t *data;
    size_t size;
    size_t at;
} Reader;

typedef struct {
    uint8_t *data;
    uint32_t size;
} Domain;

typedef struct {
    uint32_t pc;
    const char *name;
    uint64_t blocks;
    uint64_t instructions;
} FlowTarget;

static const char MAGIC[8] = {'D', 'S', 'T', 'C', 'A', 'P', '0', '1'};

static void die(const char *message) {
    fprintf(stderr, "phase4_e06_capsule: %s\n", message);
    exit(1);
}

static void die_path(const char *message, const char *path) {
    fprintf(stderr, "phase4_e06_capsule: %s: %s\n", message, path);
    exit(1);
}

static const uint8_t *take(Reader *r, size_t size) {
    if (size > r->size - r->at)
        die("truncated capsule chunk");
    const uint8_t *result = r->data + r->at;
    r->at += size;
    return result;
}

static uint8_t read_u8(Reader *r) {
    return take(r, 1)[0];
}

static uint16_t read_u16(Reader *r) {
    const uint8_t *p = take(r, 2);
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t read_u32(Reader *r) {
    const uint8_t *p = take(r, 4);
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint64_t read_u64(Reader *r) {
    uint64_t lo = read_u32(r);
    uint64_t hi = read_u32(r);
    return lo | (hi << 32);
}

static uint32_t load_u32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int16_t load_s16(const uint8_t *p) {
    return (int16_t)(uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint8_t *decompress(const char *path, size_t *size_out) {
    char command[4096];
    if (snprintf(command, sizeof(command), "zstd -q -d -c '%s'", path) >= (int)sizeof(command))
        die_path("chunk path is too long", path);
    FILE *pipe = popen(command, "r");
    if (!pipe)
        die_path("cannot start zstd", path);
    size_t capacity = 1u << 20;
    size_t size = 0;
    uint8_t *data = malloc(capacity);
    if (!data)
        die("out of memory");
    for (;;) {
        if (size == capacity) {
            capacity *= 2;
            uint8_t *grown = realloc(data, capacity);
            if (!grown)
                die("out of memory");
            data = grown;
        }
        size_t got = fread(data + size, 1, capacity - size, pipe);
        size += got;
        if (got == 0) {
            if (ferror(pipe))
                die_path("failed reading zstd output", path);
            break;
        }
    }
    if (pclose(pipe) != 0)
        die_path("zstd failed", path);
    *size_out = size;
    return data;
}

static bool digest_equal(const uint8_t *data, size_t size, const uint8_t expected[SHA256_DIGEST_LENGTH]) {
    uint8_t actual[SHA256_DIGEST_LENGTH];
    SHA256(data, size, actual);
    return memcmp(actual, expected, sizeof(actual)) == 0;
}

static bool occupied(const uint8_t *record) {
    return (record[0x33] & 0x80u) != 0 && load_s16(record + 0x22) != 0;
}

static bool walker_live(const uint8_t *record) {
    return (record[0x33] & 0x02u) != 0 && load_s16(record + 0x22) > 0;
}

static bool ram_pointer(uint32_t value) {
    uint32_t physical = value & 0x1fffffffu;
    return physical < RAM_SIZE && (value & 0x80000000u) != 0;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s CAPSULE_DIRECTORY\n", argv[0]);
        return 2;
    }
    const char *capsule_id = strrchr(argv[1], '/');
    capsule_id = capsule_id ? capsule_id + 1 : argv[1];

    char pattern[4096];
    if (snprintf(pattern, sizeof(pattern), "%s/chunks/*.tcap.zst", argv[1]) >= (int)sizeof(pattern))
        die("capsule path is too long");
    glob_t paths = {0};
    if (glob(pattern, 0, NULL, &paths) != 0 || paths.gl_pathc == 0)
        die("no capsule chunks found");

    Domain domains[4] = {{0}};
    FlowTarget targets[] = {
        {0x80059e44u, "contact_alloc", 0, 0},
        {0x8005a0e0u, "contact_spawn_full", 0, 0},
        {0x8005a0f0u, "contact_spawn_wrapper", 0, 0},
        {0x800586b0u, "contact_walker", 0, 0},
        {0x80014844u, "contact_billboard_render", 0, 0},
    };
    const size_t target_count = sizeof(targets) / sizeof(targets[0]);

    uint64_t records = 0;
    uint64_t flow_items = 0;
    uint64_t flow_instructions = 0;
    uint64_t hash_mismatches = 0;
    uint64_t first_frame = 0, last_frame = 0;
    uint32_t first_movie = 0, last_movie = 0;
    bool have_frame = false;

    bool previous_occupied[POOL_COUNT] = {0};
    int16_t previous_ttl[POOL_COUNT] = {0};
    bool ever_occupied[POOL_COUNT] = {0};
    uint64_t activations = 0, retirements = 0, reactivations = 0, ttl_refreshes = 0;
    uint32_t min_occupied = UINT32_MAX, max_occupied = 0;
    uint32_t min_walker_live = UINT32_MAX, max_walker_live = 0;
    uint32_t max_occupied_movie = 0, max_walker_movie = 0;

    bool have_cursor = false;
    uint32_t previous_cursor = 0, cursor_initial = 0, cursor_final = 0;
    uint64_t cursor_changes = 0, cursor_steps = 0, cursor_wraps = 0, cursor_bad_values = 0;
    uint64_t cursor_single_steps = 0, cursor_multi_steps = 0, cursor_stationary = 0;
    uint64_t cursor_prior_target_free = 0, cursor_prior_target_occupied = 0;
    uint64_t cursor_prior_busy_candidates = 0, cursor_prior_free_candidates = 0;
    uint64_t cursor_alloc_correlated = 0, cursor_alloc_without_change = 0, cursor_change_without_alloc = 0;

    uint32_t descriptor_initial[DESCRIPTOR_COUNT] = {0};
    uint32_t descriptor_changes[DESCRIPTOR_COUNT] = {0};
    uint32_t descriptor_boundary_initial[DESCRIPTOR_BOUNDARY_COUNT] = {0};
    uint32_t descriptor_boundary_changes[DESCRIPTOR_BOUNDARY_COUNT] = {0};
    bool have_descriptors = false;

    uint64_t byte_hist[8][256] = {{0}};

    for (size_t chunk_index = 0; chunk_index < paths.gl_pathc; ++chunk_index) {
        size_t raw_size = 0;
        uint8_t *raw = decompress(paths.gl_pathv[chunk_index], &raw_size);
        Reader r = {raw, raw_size, 0};
        if (memcmp(take(&r, 8), MAGIC, 8) != 0)
            die_path("bad capsule magic", paths.gl_pathv[chunk_index]);
        if (read_u32(&r) != 1)
            die_path("unsupported capsule schema", paths.gl_pathv[chunk_index]);
        uint32_t mode = read_u32(&r);
        (void)read_u64(&r);
        uint32_t register_count = read_u32(&r);
        for (uint32_t i = 0; i < register_count; ++i)
            (void)take(&r, read_u16(&r));

        while (r.at < r.size) {
            if (read_u8(&r) != 1)
                die_path("unknown capsule record tag", paths.gl_pathv[chunk_index]);
            uint64_t frame = read_u64(&r);
            (void)read_u64(&r);
            uint32_t movie_frame = read_u32(&r);
            (void)read_u32(&r);
            (void)read_u32(&r);
            (void)take(&r, (size_t)register_count * 4u);

            for (unsigned domain_number = 0; domain_number < 3; ++domain_number) {
                uint32_t id = read_u32(&r);
                uint32_t size = read_u32(&r);
                uint32_t run_count = read_u32(&r);
                const uint8_t *expected = take(&r, SHA256_DIGEST_LENGTH);
                if (id < 1 || id > 3)
                    die("unknown capsule domain");
                Domain *domain = &domains[id];
                if (!domain->data) {
                    domain->data = calloc(1, size);
                    domain->size = size;
                }
                if (!domain->data || domain->size != size)
                    die("capsule domain size changed");
                for (uint32_t run = 0; run < run_count; ++run) {
                    uint32_t offset = read_u32(&r);
                    uint32_t length = read_u32(&r);
                    if (offset > size || length > size - offset)
                        die("out-of-range capsule delta");
                    memcpy(domain->data + offset, take(&r, length), length);
                }
                if (!digest_equal(domain->data, domain->size, expected))
                    ++hash_mismatches;
            }

            uint64_t count = read_u64(&r);
            uint64_t frame_alloc_blocks = 0;
            flow_items += count;
            for (uint64_t i = 0; i < count; ++i) {
                uint32_t pc = read_u32(&r);
                uint64_t instructions;
                if (mode == 2) {
                    instructions = read_u32(&r);
                    (void)read_u64(&r);
                } else if (mode == 1) {
                    instructions = read_u64(&r);
                } else if (mode == 0) {
                    die("flow count present in mode zero");
                } else {
                    die("unsupported flow mode");
                }
                flow_instructions += instructions;
                for (size_t target = 0; target < target_count; ++target) {
                    if (pc == targets[target].pc) {
                        ++targets[target].blocks;
                        targets[target].instructions += instructions;
                        if (targets[target].pc == 0x80059e44u)
                            ++frame_alloc_blocks;
                    }
                }
            }

            Domain *ram = &domains[1];
            if (!ram->data || ram->size != RAM_SIZE)
                die("unexpected RAM domain size");
            const uint8_t *pool = ram->data + POOL_OFFSET;
            uint32_t current_cursor = load_u32(ram->data + CURSOR_OFFSET);
            if (!have_cursor) {
                cursor_initial = current_cursor;
                have_cursor = true;
            } else if (current_cursor < POOL_COUNT && previous_cursor < POOL_COUNT) {
                uint32_t delta = (current_cursor - previous_cursor) & (POOL_COUNT - 1u);
                if (delta == 0) {
                    ++cursor_stationary;
                    cursor_alloc_without_change += frame_alloc_blocks;
                } else {
                    ++cursor_changes;
                    cursor_steps += delta;
                    if (delta == 1)
                        ++cursor_single_steps;
                    else
                        ++cursor_multi_steps;
                    if (current_cursor < previous_cursor)
                        ++cursor_wraps;
                    if (frame_alloc_blocks == 1)
                        ++cursor_alloc_correlated;
                    else if (frame_alloc_blocks == 0)
                        ++cursor_change_without_alloc;
                    for (uint32_t step = 1; step <= delta; ++step) {
                        uint32_t candidate = (previous_cursor + step) & (POOL_COUNT - 1u);
                        if (previous_occupied[candidate])
                            ++cursor_prior_busy_candidates;
                        else
                            ++cursor_prior_free_candidates;
                    }
                    if (previous_occupied[current_cursor])
                        ++cursor_prior_target_occupied;
                    else
                        ++cursor_prior_target_free;
                }
            } else {
                ++cursor_bad_values;
            }
            previous_cursor = current_cursor;
            cursor_final = current_cursor;

            uint32_t occupied_count = 0, walker_count = 0;
            for (uint32_t slot = 0; slot < POOL_COUNT; ++slot) {
                const uint8_t *record = pool + slot * RECORD_SIZE;
                bool is_occupied = occupied(record);
                bool is_walker_live = walker_live(record);
                int16_t ttl = load_s16(record + 0x22);
                occupied_count += is_occupied;
                walker_count += is_walker_live;
                if (have_frame) {
                    if (!previous_occupied[slot] && is_occupied) {
                        ++activations;
                        if (ever_occupied[slot])
                            ++reactivations;
                    } else if (previous_occupied[slot] && !is_occupied) {
                        ++retirements;
                    } else if (previous_occupied[slot] && is_occupied && ttl > previous_ttl[slot] + 1) {
                        ++ttl_refreshes;
                    }
                }
                if (is_occupied)
                    ever_occupied[slot] = true;
                previous_occupied[slot] = is_occupied;
                previous_ttl[slot] = ttl;
                if (is_occupied) {
                    for (unsigned offset = 0; offset < 8; ++offset)
                        ++byte_hist[offset][record[0x2c + offset]];
                }
            }
            if (occupied_count < min_occupied)
                min_occupied = occupied_count;
            if (occupied_count > max_occupied) {
                max_occupied = occupied_count;
                max_occupied_movie = movie_frame;
            }
            if (walker_count < min_walker_live)
                min_walker_live = walker_count;
            if (walker_count > max_walker_live) {
                max_walker_live = walker_count;
                max_walker_movie = movie_frame;
            }

            const uint8_t *descriptor_table = ram->data + DESCRIPTOR_TABLE_OFFSET;
            for (uint32_t i = 0; i < DESCRIPTOR_BOUNDARY_COUNT; ++i) {
                uint32_t value = load_u32(descriptor_table + i * 4u);
                if (!have_descriptors)
                    descriptor_boundary_initial[i] = value;
                else if (value != descriptor_boundary_initial[i])
                    ++descriptor_boundary_changes[i];
                if (i < DESCRIPTOR_COUNT) {
                    if (!have_descriptors)
                        descriptor_initial[i] = value;
                    else if (value != descriptor_initial[i])
                        ++descriptor_changes[i];
                }
            }
            have_descriptors = true;

            if (!have_frame) {
                first_frame = frame;
                first_movie = movie_frame;
                have_frame = true;
            }
            last_frame = frame;
            last_movie = movie_frame;
            ++records;
        }
        free(raw);
    }

    uint32_t descriptors_nonzero = 0, descriptors_ram = 0, descriptors_changed = 0;
    for (uint32_t i = 0; i < DESCRIPTOR_COUNT; ++i) {
        descriptors_nonzero += descriptor_initial[i] != 0;
        descriptors_ram += ram_pointer(descriptor_initial[i]);
        descriptors_changed += descriptor_changes[i] != 0;
    }
    uint32_t padding_50_114_zero = 0, adjacent_115_127_ram = 0, boundary_changed = 0;
    for (uint32_t i = 50; i <= 114; ++i)
        padding_50_114_zero += descriptor_boundary_initial[i] == 0;
    for (uint32_t i = 115; i < DESCRIPTOR_BOUNDARY_COUNT; ++i)
        adjacent_115_127_ram += ram_pointer(descriptor_boundary_initial[i]);
    for (uint32_t i = 0; i < DESCRIPTOR_BOUNDARY_COUNT; ++i)
        boundary_changed += descriptor_boundary_changes[i] != 0;
    uint32_t slots_ever_occupied = 0;
    for (uint32_t i = 0; i < POOL_COUNT; ++i)
        slots_ever_occupied += ever_occupied[i];

    printf("{\n");
    printf("  \"schema\": \"abl-phase4-e06-capsule-analysis-v1\",\n");
    printf("  \"capsule_id\": \"%s\",\n", capsule_id);
    printf("  \"chunks\": %zu,\n", paths.gl_pathc);
    printf("  \"records\": %" PRIu64 ",\n", records);
    printf("  \"frame_span\": {\"emulator_first\": %" PRIu64 ", \"emulator_last\": %" PRIu64 ", \"movie_first\": %u, \"movie_last\": %u},\n",
           first_frame, last_frame, first_movie, last_movie);
    printf("  \"integrity\": {\"domain_hash_checks\": %" PRIu64 ", \"hash_mismatches\": %" PRIu64 "},\n",
           records * 3u, hash_mismatches);
    printf("  \"flow\": {\"items\": %" PRIu64 ", \"instructions\": %" PRIu64 ", \"targets\": [\n",
           flow_items, flow_instructions);
    for (size_t i = 0; i < target_count; ++i) {
        printf("    {\"name\": \"%s\", \"pc\": \"0x%08x\", \"blocks\": %" PRIu64 ", \"block_instructions\": %" PRIu64 "}%s\n",
               targets[i].name, targets[i].pc, targets[i].blocks, targets[i].instructions,
               i + 1 == target_count ? "" : ",");
    }
    printf("  ]},\n");
    printf("  \"pool\": {\"base\": \"0x800b0d18\", \"slots\": 64, \"stride\": 56, ");
    printf("\"occupied_min\": %u, \"occupied_max\": %u, \"occupied_max_movie_frame\": %u, ", min_occupied, max_occupied, max_occupied_movie);
    printf("\"walker_live_min\": %u, \"walker_live_max\": %u, \"walker_live_max_movie_frame\": %u, ", min_walker_live, max_walker_live, max_walker_movie);
    printf("\"activations\": %" PRIu64 ", \"retirements\": %" PRIu64 ", \"reactivations\": %" PRIu64 ", \"ttl_refreshes\": %" PRIu64 ", \"slots_ever_occupied\": %u},\n",
           activations, retirements, reactivations, ttl_refreshes, slots_ever_occupied);
    printf("  \"cursor\": {\"address\": \"0x8008234c\", \"initial\": %u, \"final\": %u, ", cursor_initial, cursor_final);
    printf("\"change_frames\": %" PRIu64 ", \"modulo_steps\": %" PRIu64 ", \"single_step_frames\": %" PRIu64 ", \"multi_step_frames\": %" PRIu64 ", ",
           cursor_changes, cursor_steps, cursor_single_steps, cursor_multi_steps);
    printf("\"stationary_frames\": %" PRIu64 ", \"wraps\": %" PRIu64 ", \"bad_values\": %" PRIu64 ", ", cursor_stationary, cursor_wraps, cursor_bad_values);
    printf("\"prior_target_occupied\": %" PRIu64 ", \"prior_target_free\": %" PRIu64 ", ", cursor_prior_target_occupied, cursor_prior_target_free);
    printf("\"prior_busy_candidates\": %" PRIu64 ", \"prior_free_candidates\": %" PRIu64 ", ", cursor_prior_busy_candidates, cursor_prior_free_candidates);
    printf("\"single_allocator_entry_and_cursor_change\": %" PRIu64 ", \"allocator_entries_without_cursor_change\": %" PRIu64 ", \"cursor_changes_without_allocator_entry\": %" PRIu64 "},\n",
           cursor_alloc_correlated, cursor_alloc_without_change, cursor_change_without_alloc);
    printf("  \"descriptor_boundary\": {\"verified_entries\": 50, \"scan_entries\": 128, \"zero_entries_50_through_114\": %u, \"ram_pointers_115_through_127\": %u, \"changed_entries_0_through_127\": %u},\n",
           padding_50_114_zero, adjacent_115_127_ram, boundary_changed);
    printf("  \"descriptor_table\": {\"address\": \"0x80096b98\", \"entries_examined\": 50, \"nonzero\": %u, \"ram_pointers\": %u, \"changed_entries\": %u, \"entries\": [\n",
           descriptors_nonzero, descriptors_ram, descriptors_changed);
    for (uint32_t i = 0; i < DESCRIPTOR_COUNT; ++i) {
        printf("    {\"kind\": %u, \"pointer\": \"0x%08x\", \"ram_pointer\": %s, \"change_frames\": %u}%s\n",
               i, descriptor_initial[i], ram_pointer(descriptor_initial[i]) ? "true" : "false", descriptor_changes[i],
               i + 1 == DESCRIPTOR_COUNT ? "" : ",");
    }
    printf("  ]},\n");
    printf("  \"occupied_record_byte_histograms\": {\n");
    for (unsigned offset = 0; offset < 8; ++offset) {
        printf("    \"0x%02x\": {", 0x2c + offset);
        bool first = true;
        for (unsigned value = 0; value < 256; ++value) {
            if (byte_hist[offset][value] == 0)
                continue;
            printf("%s\"%u\": %" PRIu64, first ? "" : ", ", value, byte_hist[offset][value]);
            first = false;
        }
        printf("}%s\n", offset == 7 ? "" : ",");
    }
    printf("  }\n");
    printf("}\n");

    for (unsigned i = 1; i <= 3; ++i)
        free(domains[i].data);
    globfree(&paths);
    return hash_mismatches == 0 ? 0 : 1;
}
