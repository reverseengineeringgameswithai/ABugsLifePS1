#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zstd.h>

enum { RAM_SIZE = 0x200000, POSITION_JUMP = 12000 };

typedef struct {
    const uint8_t *data;
    size_t size;
    size_t offset;
} Buffer;

typedef struct {
    uint64_t emulator_frame;
    uint32_t movie_frame;
    int32_t x, y, z;
    int32_t safe_x, safe_y, safe_z;
    int16_t health;
    int16_t damage_timer;
    uint8_t lives;
    uint16_t power_flags;
    uint32_t scene;
} State;

static void die(const char *message)
{
    fprintf(stderr, "phase4_e10_capsule: %s\n", message);
    exit(2);
}

static void *allocate(size_t size)
{
    void *result = malloc(size ? size : 1);
    if (!result)
        die("out of memory");
    return result;
}

static const uint8_t *take(Buffer *buffer, size_t size)
{
    const uint8_t *result;
    if (size > buffer->size - buffer->offset)
        die("truncated capsule record");
    result = buffer->data + buffer->offset;
    buffer->offset += size;
    return result;
}

static uint8_t get_u8(Buffer *buffer)
{
    return *take(buffer, 1);
}

static uint16_t get_u16(Buffer *buffer)
{
    const uint8_t *p = take(buffer, 2);
    return (uint16_t)(p[0] | p[1] << 8);
}

static uint32_t get_u32(Buffer *buffer)
{
    const uint8_t *p = take(buffer, 4);
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint64_t get_u64(Buffer *buffer)
{
    uint64_t low = get_u32(buffer);
    uint64_t high = get_u32(buffer);
    return low | (high << 32);
}

static uint16_t ram_u16(const uint8_t *ram, size_t offset)
{
    return (uint16_t)(ram[offset] | ram[offset + 1] << 8);
}

static uint32_t ram_u32(const uint8_t *ram, size_t offset)
{
    return (uint32_t)ram[offset] | (uint32_t)ram[offset + 1] << 8 |
           (uint32_t)ram[offset + 2] << 16 |
           (uint32_t)ram[offset + 3] << 24;
}

static uint8_t *read_file(const char *path, size_t *size)
{
    FILE *file = fopen(path, "rb");
    long length;
    uint8_t *data;
    if (!file) {
        fprintf(stderr, "%s: %s\n", path, strerror(errno));
        exit(2);
    }
    if (fseek(file, 0, SEEK_END) || (length = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET))
        die("file seek failed");
    data = allocate((size_t)length);
    if (fread(data, 1, (size_t)length, file) != (size_t)length)
        die("file read failed");
    fclose(file);
    *size = (size_t)length;
    return data;
}

static uint8_t *decompress_file(const char *path, size_t *size)
{
    size_t input_size;
    uint8_t *input = read_file(path, &input_size);
    unsigned long long output_size =
        ZSTD_getFrameContentSize(input, input_size);
    uint8_t *output;
    size_t actual;
    if (output_size == ZSTD_CONTENTSIZE_ERROR ||
        output_size == ZSTD_CONTENTSIZE_UNKNOWN ||
        output_size > SIZE_MAX)
        die("invalid zstd frame");
    output = allocate((size_t)output_size);
    actual = ZSTD_decompress(output, (size_t)output_size, input, input_size);
    free(input);
    if (ZSTD_isError(actual) || actual != (size_t)output_size)
        die("zstd decompression failed");
    *size = actual;
    return output;
}

static int sha256_matches(const uint8_t *data, size_t size,
                          const uint8_t expected[32])
{
    uint8_t actual[32];
    size_t actual_size = 0;
    if (!EVP_Q_digest(NULL, "SHA256", NULL, data, size,
                      actual, &actual_size) ||
        actual_size != sizeof(actual))
        die("SHA-256 failed");
    return memcmp(actual, expected, sizeof(actual)) == 0;
}

static State read_state(const uint8_t *ram, uint64_t emulator_frame,
                        uint32_t movie_frame)
{
    State state = {0};
    state.emulator_frame = emulator_frame;
    state.movie_frame = movie_frame;
    state.x = (int32_t)ram_u32(ram, 0xa6500);
    state.y = (int32_t)ram_u32(ram, 0xa6504);
    state.z = (int32_t)ram_u32(ram, 0xa6508);
    state.safe_x = (int32_t)ram_u32(ram, 0xa6550);
    state.safe_y = (int32_t)ram_u32(ram, 0xa6554);
    state.safe_z = (int32_t)ram_u32(ram, 0xa6558);
    state.power_flags = ram_u16(ram, 0xa6590);
    state.damage_timer = (int16_t)ram_u16(ram, 0xa6592);
    state.health = (int16_t)ram_u16(ram, 0xa6594);
    state.lives = ram[0xa65a0];
    state.scene = ram_u32(ram, 0x82504);
    return state;
}

static int64_t absolute64(int64_t value)
{
    return value < 0 ? -value : value;
}

static int position_jumped(const State *before, const State *after)
{
    return absolute64((int64_t)after->x - before->x) > POSITION_JUMP ||
           absolute64((int64_t)after->y - before->y) > POSITION_JUMP ||
           absolute64((int64_t)after->z - before->z) > POSITION_JUMP;
}

static void print_state(const char *prefix, const State *state)
{
    printf("%s movie=%u emulator=%" PRIu64
           " xyz=(%d,%d,%d) safe=(%d,%d,%d)"
           " health=%d lives=%u flags=0x%04x timer=%d scene=%u\n",
           prefix, state->movie_frame, state->emulator_frame,
           state->x, state->y, state->z,
           state->safe_x, state->safe_y, state->safe_z,
           state->health, state->lives, state->power_flags,
           state->damage_timer, state->scene);
}

static int flow_is_relevant(uint32_t pc)
{
    return (pc >= 0x80049500 && pc < 0x80049900) ||
           (pc >= 0x8004a700 && pc < 0x8004aa34) ||
           (pc >= 0x8004abf4 && pc < 0x8004b6dc) ||
           (pc >= 0x800586b0 && pc < 0x80058af8) ||
           (pc >= 0x8005b100 && pc < 0x8005b450) ||
           (pc >= 0x8004dc0c && pc < 0x8004dd00);
}

static void analyze(const char *label, const char *directory,
                    uint32_t expected_event)
{
    char pattern[4096];
    glob_t chunks = {0};
    uint8_t *domains[4] = {0};
    uint32_t domain_sizes[4] = {0};
    uint64_t records = 0, hash_checks = 0, hash_mismatches = 0;
    uint64_t flow_items = 0, flow_instructions = 0;
    unsigned health_changes = 0, lives_changes = 0, jumps = 0;
    State first = {0}, previous = {0}, final = {0};

    if (snprintf(pattern, sizeof(pattern), "%s/chunks/*.zst", directory) >=
        (int)sizeof(pattern))
        die("capsule path too long");
    if (glob(pattern, 0, NULL, &chunks) || !chunks.gl_pathc)
        die("no capsule chunks");

    printf("=== %s ===\n", label);
    for (size_t file_index = 0; file_index < chunks.gl_pathc; file_index++) {
        size_t raw_size;
        uint8_t *raw = decompress_file(chunks.gl_pathv[file_index], &raw_size);
        Buffer buffer = {raw, raw_size, 0};
        uint32_t version, register_count;

        if (memcmp(take(&buffer, 8), "DSTCAP01", 8))
            die("bad capsule magic");
        version = get_u32(&buffer);
        if (version < 1 || version > 2)
            die("unsupported capsule version");
        (void)get_u32(&buffer);
        (void)get_u64(&buffer);
        register_count = get_u32(&buffer);
        for (uint32_t i = 0; i < register_count; i++) {
            uint16_t length = get_u16(&buffer);
            (void)take(&buffer, length);
        }

        while (buffer.offset < buffer.size) {
            uint64_t emulator_frame;
            uint32_t movie_frame;
            uint8_t *ram = NULL;
            State current;
            uint64_t flow_count;

            if (get_u8(&buffer) != 1)
                die("bad frame record tag");
            emulator_frame = get_u64(&buffer);
            (void)get_u64(&buffer);
            movie_frame = get_u32(&buffer);
            (void)get_u32(&buffer);
            (void)get_u32(&buffer);
            (void)take(&buffer, (size_t)register_count * 4);

            for (unsigned domain_index = 0; domain_index < 3;
                 domain_index++) {
                uint32_t id = get_u32(&buffer);
                uint32_t size = get_u32(&buffer);
                uint32_t patch_count = get_u32(&buffer);
                const uint8_t *expected_hash = take(&buffer, 32);
                if (id < 1 || id > 3)
                    die("bad domain id");
                if (!domains[id]) {
                    domains[id] = calloc(1, size);
                    domain_sizes[id] = size;
                    if (!domains[id])
                        die("domain allocation failed");
                } else if (domain_sizes[id] != size) {
                    die("domain size changed");
                }
                for (uint32_t patch = 0; patch < patch_count; patch++) {
                    uint32_t offset = get_u32(&buffer);
                    uint32_t length = get_u32(&buffer);
                    if (offset > size || length > size - offset)
                        die("bad domain patch");
                    memcpy(domains[id] + offset, take(&buffer, length), length);
                }
                hash_checks++;
                if (!sha256_matches(domains[id], size, expected_hash))
                    hash_mismatches++;
            }

            for (unsigned id = 1; id <= 3; id++)
                if (domain_sizes[id] == RAM_SIZE)
                    ram = domains[id];
            if (!ram)
                die("RAM domain absent");
            current = read_state(ram, emulator_frame, movie_frame);

            if (!records) {
                first = current;
            } else {
                int changed = 0;
                if (current.health != previous.health) {
                    health_changes++;
                    changed = 1;
                }
                if (current.lives != previous.lives) {
                    lives_changes++;
                    changed = 1;
                }
                if (position_jumped(&previous, &current)) {
                    jumps++;
                    changed = 1;
                }
                if (changed) {
                    print_state("before", &previous);
                    print_state("after ", &current);
                }
            }

            flow_count = get_u64(&buffer);
            for (uint64_t flow = 0; flow < flow_count; flow++) {
                uint32_t pc = get_u32(&buffer);
                uint64_t count;
                if (version == 2) {
                    count = get_u32(&buffer);
                    (void)get_u64(&buffer);
                } else {
                    count = get_u64(&buffer);
                }
                flow_items++;
                flow_instructions += count;
                if (movie_frame == expected_event && flow_is_relevant(pc))
                    printf("event_flow pc=0x%08x count=%" PRIu64 "\n",
                           pc, count);
            }

            previous = current;
            final = current;
            records++;
        }
        free(raw);
    }

    print_state("initial", &first);
    print_state("final  ", &final);
    printf("summary records=%" PRIu64 " hash_checks=%" PRIu64
           " hash_mismatches=%" PRIu64 " flow_items=%" PRIu64
           " flow_instructions=%" PRIu64
           " health_changes=%u lives_changes=%u position_jumps=%u\n",
           records, hash_checks, hash_mismatches, flow_items,
           flow_instructions, health_changes, lives_changes, jumps);

    for (unsigned id = 1; id <= 3; id++)
        free(domains[id]);
    globfree(&chunks);
}

int main(int argc, char **argv)
{
    if (argc < 4 || (argc - 1) % 3) {
        fprintf(stderr,
                "usage: %s LABEL CAPSULE_DIR EXPECTED_EVENT [...]\n",
                argv[0]);
        return 2;
    }
    for (int argument = 1; argument < argc; argument += 3)
        analyze(argv[argument], argv[argument + 1],
                (uint32_t)strtoul(argv[argument + 2], NULL, 0));
    return 0;
}
