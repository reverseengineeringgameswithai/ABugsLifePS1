#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { PSX_EXE_HEADER = 0x800 };

typedef struct {
    uint32_t pc;
    uint32_t word;
    const char *role;
} Invariant;

static uint32_t read_u32le(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void fail(const char *message)
{
    fprintf(stderr, "phase4_a19_static: %s\n", message);
    exit(1);
}

static uint32_t word_at(const uint8_t *text, uint32_t load, uint32_t size,
                        uint32_t pc)
{
    if (pc < load || pc - load > size - 4)
        fail("requested PC lies outside the executable text");
    return read_u32le(text + pc - load);
}

static uint32_t jal_target(uint32_t pc, uint32_t word)
{
    return ((pc + 4) & 0xf0000000u) | ((word & 0x03ffffffu) << 2);
}

int main(int argc, char **argv)
{
    static const Invariant expected[] = {
        {0x800484b0, 0x30820001, "SELECT bit 0x0001 test"},
        {0x800484c4, 0x1040000b, "zero skips four pulse normalizers"},
        {0x800503fc, 0x84850000, "load signed pulse"},
        {0x80050404, 0x28a20c00, "test pulse below 0x0c00"},
        {0x80050410, 0x24021000, "load wrap endpoint 0x1000"},
        {0x80050418, 0x00431023, "mirror 0x1000-pulse"},
        {0x8005041c, 0x28a20401, "test pulse below 0x0401"},
        {0x80050424, 0x24020400, "load sustained plateau 0x0400"},
        {0x80050428, 0xa4820000, "store normalized pulse"},
        {0x80050438, 0x24020040, "load initial pulse step 0x0040"},
        {0x8005043c, 0xa4820000, "replace zero by 0x0040"},
        {0x8004f3e4, 0x0c0149bd, "gameplay calls HUD renderer"},
        {0x8004f3e8, 0x24040040, "HUD animation step is 0x0040"},
        {0x800526f4, 0x3c028008, "HUD entry"},
        {0x80052704, 0x00809821, "preserve animation step in s3"},
        {0x80052748, 0xa4220188, "force lives pulse for transition"},
        {0x80052750, 0xa422018c, "force grain pulse for transition"},
        {0x80052758, 0xa4220190, "force health pulse for transition"},
        {0x800528e0, 0xa4220188, "advance lives pulse"},
        {0x80052b9c, 0xa422018c, "advance grain pulse"}
    };
    static const uint32_t interesting_calls[] = {
        0x800503fcu, 0x800526f4u, 0x80025f54u, 0x800260f8u,
        0x80026588u, 0x80026df4u
    };

    if (argc != 2) {
        fprintf(stderr, "usage: %s REBUILD/files/SCUS_942.88\n", argv[0]);
        return 2;
    }

    FILE *input = fopen(argv[1], "rb");
    if (!input)
        fail("cannot open executable");
    if (fseek(input, 0, SEEK_END) != 0)
        fail("seek failed");
    long file_size = ftell(input);
    if (file_size < PSX_EXE_HEADER)
        fail("file is too small");
    rewind(input);
    uint8_t *file = malloc((size_t)file_size);
    if (!file || fread(file, 1, (size_t)file_size, input) != (size_t)file_size)
        fail("read failed");
    fclose(input);
    if (memcmp(file, "PS-X EXE", 8) != 0)
        fail("not a PS-X EXE");

    uint32_t load = read_u32le(file + 0x18);
    uint32_t text_size = read_u32le(file + 0x1c);
    if (text_size > (uint32_t)file_size - PSX_EXE_HEADER)
        fail("declared text exceeds file");
    const uint8_t *text = file + PSX_EXE_HEADER;
    unsigned mismatches = 0;

    printf("{\n  \"schema\":\"abl.phase4.a19.static.v1\",\n");
    printf("  \"load\":\"0x%08" PRIx32 "\",\n", load);
    printf("  \"text_bytes\":%" PRIu32 ",\n", text_size);
    printf("  \"invariants\":[\n");
    for (size_t i = 0; i < sizeof(expected) / sizeof(expected[0]); i++) {
        uint32_t actual = word_at(text, load, text_size, expected[i].pc);
        int match = actual == expected[i].word;
        mismatches += !match;
        printf("    {\"pc\":\"0x%08" PRIx32
               "\",\"word\":\"0x%08" PRIx32
               "\",\"expected\":\"0x%08" PRIx32
               "\",\"match\":%s,\"role\":\"%s\"}%s\n",
               expected[i].pc, actual, expected[i].word,
               match ? "true" : "false", expected[i].role,
               i + 1 == sizeof(expected) / sizeof(expected[0]) ? "" : ",");
    }

    printf("  ],\n  \"direct_call_counts\":{");
    for (size_t target = 0;
         target < sizeof(interesting_calls) / sizeof(interesting_calls[0]);
         target++) {
        uint64_t count = 0;
        for (uint32_t offset = 0; offset + 4 <= text_size; offset += 4) {
            uint32_t word = read_u32le(text + offset);
            uint32_t pc = load + offset;
            if ((word >> 26) == 3 && jal_target(pc, word) == interesting_calls[target])
                count++;
        }
        printf("%s\"0x%08" PRIx32 "\":%" PRIu64,
               target ? "," : "", interesting_calls[target], count);
    }
    printf("},\n  \"mismatches\":%u,\n", mismatches);
    printf("  \"classification\":\"SELECT bit -> four pulse normalizers -> HUD step\"\n}\n");
    free(file);
    return mismatches ? 1 : 0;
}
