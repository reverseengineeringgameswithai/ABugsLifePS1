/*
 * Phase 4 A13 plant-output selector static guard.
 *
 * This reads the hash-pinned pristine retail executable. Additional arguments
 * may be retail overlay BINs; they are scanned for direct selector references.
 *
 *   cc -std=c11 -O2 -Wall -Wextra -Werror \
 *      tools/phase4_a13_static.c -o /tmp/phase4_a13_static
 *   /tmp/phase4_a13_static REBUILD/files/SCUS_942.88 \
 *      $(find REBUILD/files -type f -name '*.BIN' -print)
 *
 * Expected SCUS_942.88 SHA-256:
 *   1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum {
    EXE_HEADER = 0x800,
    LOAD_VA = 0x80010000u,
    PLANT_TABLE = 0x8007a448u
};

static uint8_t *resident;
static size_t resident_size;

static uint16_t read_u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t read_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static size_t va_offset(uint32_t va)
{
    size_t offset;

    if (va < LOAD_VA) {
        fprintf(stderr, "address below load VA: %08x\n", va);
        exit(2);
    }
    offset = EXE_HEADER + (size_t)(va - LOAD_VA);
    if (offset + 4 > resident_size) {
        fprintf(stderr, "address outside executable: %08x\n", va);
        exit(2);
    }
    return offset;
}

static uint32_t read_word(uint32_t va)
{
    return read_u32(resident + va_offset(va));
}

static uint8_t cycle_selector(uint8_t old, int *accepted)
{
    unsigned next = old;
    const unsigned available = next & 7u;

    if (available < 2u) {
        *accepted = 0;
        return old;
    }
    *accepted = 1;
    next += 0x10u;
    if ((next & 7u) < (next >> 4)) {
        next = (next & 7u) + 0x10u;
    }
    return (uint8_t)next;
}

static uint8_t timeout_normalize(uint8_t old)
{
    const unsigned available = old & 0x0fu;
    return (uint8_t)((available << 4) + available);
}

static uint8_t pickup_upgrade(uint8_t old)
{
    const unsigned next = (old + 1u) & 7u;
    return (uint8_t)((next << 4) + next);
}

static int is_memory_op(unsigned op)
{
    return (op >= 0x20 && op <= 0x26) || (op >= 0x28 && op <= 0x2e);
}

static const char *memory_op_name(unsigned op)
{
    switch (op) {
    case 0x20: return "lb";
    case 0x21: return "lh";
    case 0x23: return "lw";
    case 0x24: return "lbu";
    case 0x25: return "lhu";
    case 0x28: return "sb";
    case 0x29: return "sh";
    case 0x2b: return "sw";
    default: return "?";
    }
}

static int has_nearby_800a_base(const uint8_t *bytes, size_t index,
                                unsigned base)
{
    const size_t first = index > 20 ? index - 20 : 0;

    for (size_t cursor = index; cursor-- > first;) {
        const uint32_t word = read_u32(bytes + cursor * 4);
        const unsigned op = word >> 26;
        const unsigned rs = (word >> 21) & 31u;
        const unsigned rt = (word >> 16) & 31u;
        const unsigned rd = (word >> 11) & 31u;

        if (op == 0x0f && rt == base && (uint16_t)word == 0x800a) {
            return 1;
        }
        if (op == 0 && (word & 63u) == 0x21 && rd == base) {
            for (size_t prior = cursor; prior-- > first;) {
                const uint32_t candidate = read_u32(bytes + prior * 4);
                if ((candidate >> 26) == 0x0f &&
                    (uint16_t)candidate == 0x800a) {
                    const unsigned candidate_rt = (candidate >> 16) & 31u;
                    if (candidate_rt == rs || candidate_rt == rt) {
                        return 1;
                    }
                }
            }
        }
    }
    return 0;
}

static void scan_file(const char *path)
{
    FILE *input = fopen(path, "rb");
    uint8_t *bytes;
    size_t size;
    int hits = 0;

    if (input == NULL) {
        return;
    }
    fseek(input, 0, SEEK_END);
    size = (size_t)ftell(input);
    rewind(input);
    bytes = malloc(size);
    if (bytes == NULL || fread(bytes, 1, size, input) != size) {
        fclose(input);
        free(bytes);
        return;
    }
    fclose(input);

    for (size_t offset = 0; offset + 4 <= size; offset += 4) {
        const uint32_t word = read_u32(bytes + offset);
        const unsigned op = word >> 26;
        const unsigned base = (word >> 21) & 31u;
        const uint16_t immediate = (uint16_t)word;

        if (is_memory_op(op) && immediate >= 0x6598 && immediate <= 0x659c &&
            has_nearby_800a_base(bytes, offset / 4, base)) {
            if (hits++ == 0) {
                printf("FILE %s\n", path);
            }
            printf("  off=%08zx op=%s base=r%u imm=%04x word=%08x\n",
                   offset, memory_op_name(op), base, immediate, word);
        }
        if (word >= 0x800a6598u && word <= 0x800a659cu) {
            if (hits++ == 0) {
                printf("FILE %s\n", path);
            }
            printf("  off=%08zx literal_pointer=%08x\n", offset, word);
        }
    }
    free(bytes);
}

int main(int argc, char **argv)
{
    static const struct {
        uint32_t pc;
        uint32_t expected;
        const char *meaning;
    } contracts[] = {
        {0x80047ae0, 0x94422488u, "current input read"},
        {0x80047ae8, 0x30424000u, "X bit test"},
        {0x80047af8, 0x94422380u, "previous input read"},
        {0x80047b00, 0x30424000u, "previous X bit test"},
        {0x80047b34, 0x90306598u, "indexed selector read"},
        {0x80047b3c, 0x32020007u, "availability low-three-bit mask"},
        {0x80047b40, 0x28420002u, "deny availability below two"},
        {0x80047b48, 0x26100010u, "advance selected nibble"},
        {0x80047b6c, 0xa0306598u, "indexed selector write"},
        {0x80047b8c, 0x2404fff0u, "event -16"},
        {0x80047b98, 0x24020078u, "timeout 120"},
        {0x8004759c, 0x3083000fu, "timeout availability mask"},
        {0x800475a4, 0x00438021u, "timeout selected=max rebuild"},
        {0x80046b68, 0x0c017debu, "level-load memset call"},
        {0x80046be8, 0x24020011u, "level-load brown default value"},
        {0x80046bec, 0xa2620098u, "level-load brown selector := 0x11"}
    };
    static const uint8_t expected_types[20] = {
        5, 3, 8, 2, 7, 7, 6, 7, 4, 10,
        9, 1, 6, 6, 6, 6, 14, 13, 11, 11
    };
    FILE *input;
    int mismatch = 0;
    unsigned accepted = 0;
    unsigned denied = 0;
    unsigned postcondition = 0;

    if (argc < 2) {
        fprintf(stderr, "usage: %s SCUS_942.88 [overlay.bin ...]\n", argv[0]);
        return 2;
    }
    input = fopen(argv[1], "rb");
    if (input == NULL) {
        perror(argv[1]);
        return 2;
    }
    fseek(input, 0, SEEK_END);
    resident_size = (size_t)ftell(input);
    rewind(input);
    resident = malloc(resident_size);
    if (resident == NULL ||
        fread(resident, 1, resident_size, input) != resident_size) {
        fprintf(stderr, "could not read executable\n");
        return 2;
    }
    fclose(input);

    for (size_t i = 0; i < sizeof(contracts) / sizeof(contracts[0]); i++) {
        const uint32_t actual = read_word(contracts[i].pc);
        const int ok = actual == contracts[i].expected;
        printf("contract pc=%08x actual=%08x expected=%08x ok=%d %s\n",
               contracts[i].pc, actual, contracts[i].expected, ok,
               contracts[i].meaning);
        mismatch |= !ok;
    }

    for (unsigned index = 0; index < 20; index++) {
        const uint32_t va = PLANT_TABLE + index * 4u;
        const size_t offset = va_offset(va);
        const unsigned type = read_u16(resident + offset);
        const unsigned extra = read_u16(resident + offset + 2);
        const int ok = type == expected_types[index];
        printf("plant index=%u color=%u selected=%u type=%u extra=%04x ok=%d\n",
               index, index / 4, index % 4 + 1, type, extra, ok);
        mismatch |= !ok;
    }

    for (unsigned old = 0; old < 256; old++) {
        int was_accepted;
        const uint8_t next = cycle_selector((uint8_t)old, &was_accepted);
        accepted += was_accepted;
        denied += !was_accepted;
        postcondition += was_accepted && (next >> 4) >= 1 &&
                         (next >> 4) <= (next & 7u);
    }
    printf("state_space accepted=%u denied=%u accepted_postcondition=%u\n",
           accepted, denied, postcondition);
    printf("examples 14->%02x 24->%02x 34->%02x 44->%02x "
           "deny11=%02x timeout14=%02x pickup14=%02x\n",
           cycle_selector(0x14, &(int){0}), cycle_selector(0x24, &(int){0}),
           cycle_selector(0x34, &(int){0}), cycle_selector(0x44, &(int){0}),
           cycle_selector(0x11, &(int){0}), timeout_normalize(0x14),
           pickup_upgrade(0x14));

    for (int i = 1; i < argc; i++) {
        scan_file(argv[i]);
    }
    free(resident);
    return mismatch ? 1 : 0;
}
