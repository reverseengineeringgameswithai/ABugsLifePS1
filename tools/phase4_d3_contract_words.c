#define _POSIX_C_SOURCE 200809L

/*
 * Independent byte reader for the Phase-4 D3 contract pilot.
 *
 * Python owns hashes, set arithmetic, and promotion policy.  This program
 * owns the instruction words and the two small local decodes used by the
 * contract assessment: SetDumpFnt's constant cell publication and the
 * frontend dispatch table's guarded address calculation.
 *
 * Usage:
 *   phase4_d3_contract_words --self-test
 *   phase4_d3_contract_words SCUS_PATH SCUS_BASE MEMORY_PATH MEMORY_BASE
 */

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    const char *path;
    uint32_t base;
    uint8_t *bytes;
    size_t size;
} Image;

typedef struct {
    const char *id;
    uint32_t source_pc;
    uint32_t source_word;
    uint32_t site_pc;
    uint32_t site_word;
    uint32_t delay_word;
    const char *source_kind;
} Site;

static const Site SITES[] = {
    {"SCUS_942_88:0x80061ae4:jalr:v0", 0x80061ad8U, 0x8c42fbc4U, 0x80061ae4U, 0x0040f809U, 0xafa30010U, "shared_cell_load"},
    {"SCUS_942_88:0x80061b24:jalr:v0", 0x80061b1cU, 0x8c42fbc4U, 0x80061b24U, 0x0040f809U, 0x00063182U, "shared_cell_load"},
    {"SCUS_942_88:0x80061fac:jalr:v1", 0x80061fa0U, 0x8c63fbc4U, 0x80061facU, 0x0060f809U, 0xafa20010U, "shared_cell_load"},
    {"SCUS_942_88:0x80061fcc:jalr:v0", 0x80061fc0U, 0x8c42fbc4U, 0x80061fccU, 0x0040f809U, 0x00000000U, "shared_cell_load"},
    {"SCUS_942_88:0x80061ff4:jalr:v1", 0x80061fe8U, 0x8c63fbc4U, 0x80061ff4U, 0x0060f809U, 0xafa20010U, "shared_cell_load"},
    {"SCUS_942_88:0x80062010:jalr:v0", 0x80062004U, 0x8c42fbc4U, 0x80062010U, 0x0040f809U, 0x00000000U, "shared_cell_load"},
    {"SCUS_942_88:0x8006202c:jalr:v0", 0x80062020U, 0x8c42fbc4U, 0x8006202cU, 0x0040f809U, 0x00000000U, "shared_cell_load"},
    {"SCUS_942_88:0x80062074:jalr:t0", 0x80062044U, 0x8d08fbc4U, 0x80062074U, 0x0100f809U, 0xafa30010U, "shared_cell_load"},
    {"SCUS_942_88:0x8004d1e8:jalr:v0", 0x8004d1e0U, 0x8e02007cU, 0x8004d1e8U, 0x0040f809U, 0x27a40018U, "object_field_load"},
    {"SCUS_942_88:0x80060c78:jalr:t2", 0x80060c74U, 0x240a00b0U, 0x80060c78U, 0x0140f809U, 0x24090056U, "bios_immediate"},
    {"SCUS_942_88:0x800620c0:jalr:v1", 0x800620b4U, 0x8c63fbc4U, 0x800620c0U, 0x0060f809U, 0xafa20010U, "shared_cell_load"},
    {"SCUS_942_88:0x800620e8:jalr:v1", 0x800620dcU, 0x8c63fbc4U, 0x800620e8U, 0x0060f809U, 0xafa20010U, "shared_cell_load"},
};

static void die(const char *message)
{
    fprintf(stderr, "phase4_d3_contract_words: %s\n", message);
    exit(2);
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t parse_u32(const char *text)
{
    char *end = NULL;
    unsigned long value;
    errno = 0;
    value = strtoul(text, &end, 0);
    if (errno || end == text || *end || value > UINT32_MAX)
        die("invalid image base");
    return (uint32_t)value;
}

static void load_image(Image *image, const char *path, uint32_t base)
{
    FILE *file = fopen(path, "rb");
    long length;
    if (file == NULL)
        die("cannot open image");
    if (fseek(file, 0, SEEK_END) || (length = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET))
        die("cannot size image");
    image->bytes = malloc((size_t)length ? (size_t)length : 1U);
    if (image->bytes == NULL)
        die("out of memory");
    if (length && fread(image->bytes, 1, (size_t)length, file) != (size_t)length)
        die("short image read");
    if (fclose(file))
        die("cannot close image");
    image->path = path;
    image->base = base;
    image->size = (size_t)length;
}

static uint32_t word_at(const Image *image, uint32_t pc)
{
    uint64_t offset;
    if (pc < image->base)
        die("PC precedes image base");
    offset = (uint64_t)pc - image->base;
    if ((offset & 3U) || offset + 4U > image->size)
        die("PC outside image or unaligned");
    return le32(image->bytes + offset);
}

static int32_t simm16(uint32_t word)
{
    return (int16_t)(word & 0xffffU);
}

static uint32_t lui_addiu(uint32_t lui, uint32_t addiu)
{
    return (lui << 16) + (uint32_t)simm16(addiu);
}

static int self_test(void)
{
    if (lui_addiu(0x8006U, 0x1668U) != 0x80061668U)
        die("lui/addiu self-test failed");
    if (lui_addiu(0x8008U, 0xfbc4U) != 0x8007fbc4U)
        die("signed low-half self-test failed");
    if (((0x0040f809U >> 21) & 31U) != 2U ||
        (0x0040f809U & 63U) != 9U)
        die("jalr self-test failed");
    if (((0x2c820008U >> 26) != 11U) ||
        (0x2c820008U & 0xffffU) != 8U)
        die("sltiu self-test failed");
    printf("{\"tool\":\"phase4_d3_contract_words\","
           "\"passed\":4,\"total\":4,\"verdict\":true}\n");
    return 0;
}

int main(int argc, char **argv)
{
    Image scus = {0}, memory = {0};
    uint32_t writer_words[6];
    uint32_t frontend_words[12];
    uint32_t handler, cell, table;
    size_t i;

    if (argc == 2 && strcmp(argv[1], "--self-test") == 0)
        return self_test();
    if (argc != 5) {
        fprintf(stderr, "usage: %s SCUS_PATH SCUS_BASE MEMORY_PATH MEMORY_BASE\n", argv[0]);
        return 2;
    }
    load_image(&scus, argv[1], parse_u32(argv[2]));
    load_image(&memory, argv[3], parse_u32(argv[4]));

    for (i = 0; i < sizeof(SITES) / sizeof(SITES[0]); i++) {
        const Site *site = &SITES[i];
        uint32_t source = word_at(&scus, site->source_pc);
        uint32_t jump = word_at(&scus, site->site_pc);
        uint32_t delay = word_at(&scus, site->site_pc + 4U);
        unsigned source_dst = (source >> 16) & 31U;
        unsigned jump_src = (jump >> 21) & 31U;
        if (source != site->source_word || jump != site->site_word ||
            delay != site->delay_word)
            die("frozen site/source word mismatch");
        if ((jump >> 26) != 0U || (jump & 63U) != 9U ||
            ((jump >> 11) & 31U) != 31U || source_dst != jump_src)
            die("site/source register relation mismatch");
    }

    for (i = 0; i < 6; i++)
        writer_words[i] = word_at(&scus, 0x80060fd4U + (uint32_t)(i * 4U));
    if (writer_words[0] != 0x3c028006U || writer_words[1] != 0x24421668U ||
        writer_words[2] != 0x3c018008U || writer_words[3] != 0xac24f16cU ||
        writer_words[4] != 0x3c018008U || writer_words[5] != 0xac22fbc4U)
        die("SetDumpFnt sequence mismatch");
    handler = lui_addiu(writer_words[0] & 0xffffU, writer_words[1] & 0xffffU);
    cell = lui_addiu(writer_words[4] & 0xffffU, writer_words[5] & 0xffffU);

    for (i = 0; i < 12; i++)
        frontend_words[i] = word_at(&memory, 0x800b96e4U + (uint32_t)(i * 4U));
    if (frontend_words[2] != 0x2c820008U || frontend_words[3] != 0x1040003dU ||
        frontend_words[5] != 0x00041080U || frontend_words[6] != 0x3c01800bU ||
        frontend_words[7] != 0x00220821U || frontend_words[8] != 0x8c2257b4U ||
        frontend_words[10] != 0x00400008U)
        die("frontend guarded table sequence mismatch");
    table = lui_addiu(frontend_words[6] & 0xffffU, frontend_words[8] & 0xffffU);

    printf("{\"tool\":\"phase4_d3_contract_words\",\"site_count\":%zu,\"sites\":[",
           sizeof(SITES) / sizeof(SITES[0]));
    for (i = 0; i < sizeof(SITES) / sizeof(SITES[0]); i++) {
        const Site *site = &SITES[i];
        if (i) putchar(',');
        printf("{\"id\":\"%s\",\"source_kind\":\"%s\","
               "\"source_pc\":\"0x%08" PRIx32 "\","
               "\"source_word\":\"0x%08" PRIx32 "\","
               "\"site_pc\":\"0x%08" PRIx32 "\","
               "\"site_word\":\"0x%08" PRIx32 "\","
               "\"delay_word\":\"0x%08" PRIx32 "\"}",
               site->id, site->source_kind, site->source_pc, site->source_word,
               site->site_pc, site->site_word, site->delay_word);
    }
    printf("],\"known_direct_writer\":{\"entry\":\"0x80060fb4\","
           "\"definition_pc\":\"0x80060fd4\","
           "\"definition_word\":\"0x%08" PRIx32 "\","
           "\"low_definition_pc\":\"0x80060fd8\","
           "\"low_definition_word\":\"0x%08" PRIx32 "\","
           "\"store_pc\":\"0x80060fe8\","
           "\"store_word\":\"0x%08" PRIx32 "\","
           "\"derived_value\":\"0x%08" PRIx32 "\","
           "\"derived_address\":\"0x%08" PRIx32 "\"},",
           writer_words[0], writer_words[1], writer_words[5], handler, cell);
    printf("\"frontend_dispatch\":{\"site\":\"MEMORY:0x800b970c:jr:v0\","
           "\"guard_pc\":\"0x800b96ec\",\"guard_word\":\"0x%08" PRIx32 "\","
           "\"branch_pc\":\"0x800b96f0\",\"branch_word\":\"0x%08" PRIx32 "\","
           "\"load_pc\":\"0x800b9704\",\"load_word\":\"0x%08" PRIx32 "\","
           "\"site_word\":\"0x%08" PRIx32 "\",\"index_min\":0,\"index_max\":7,"
           "\"stride\":4,\"table_start\":\"0x%08" PRIx32 "\","
           "\"table_end\":\"0x%08" PRIx32 "\",\"slots\":[",
           frontend_words[2], frontend_words[3], frontend_words[8],
           frontend_words[10], table, table + 32U);
    for (i = 0; i < 8; i++) {
        uint32_t slot = table + (uint32_t)(i * 4U);
        if (i) putchar(',');
        printf("{\"index\":%zu,\"address\":\"0x%08" PRIx32 "\","
               "\"pristine_value\":\"0x%08" PRIx32 "\"}",
               i, slot, word_at(&memory, slot));
    }
    printf("]}}\n");
    free(scus.bytes);
    free(memory.bytes);
    return 0;
}
