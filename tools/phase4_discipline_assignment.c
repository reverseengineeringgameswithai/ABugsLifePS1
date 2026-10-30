#define _POSIX_C_SOURCE 200809L

/*
 * Mechanical Phase-4 indirect-site discipline assignment.
 *
 * This program owns every instruction-byte fact used by the Stage-0 freeze.
 * Python supplies only a hash-verified image manifest and the already-frozen
 * site IDs.  A declared kind/register mismatch is fatal.
 *
 * Usage:
 *   phase4_discipline_assignment --self-test
 *   phase4_discipline_assignment IMAGES.TXT SITE_ID...
 *
 * IMAGES.TXT lines are: IMAGE_ID PATH FILE_VA_BASE
 */

#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_IMAGES 64
#define MAX_ID 96
#define MAX_PATH 1024

typedef struct {
    char id[MAX_ID];
    char path[MAX_PATH];
    uint32_t base;
    uint8_t *bytes;
    size_t size;
} Image;

static Image images[MAX_IMAGES];
static size_t image_count;

static const char *const regs[32] = {
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"
};

static void die(const char *message)
{
    fprintf(stderr, "phase4_discipline_assignment: %s\n", message);
    exit(2);
}

static uint32_t read_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static Image *find_image(const char *id)
{
    size_t i;
    for (i = 0; i < image_count; i++)
        if (strcmp(images[i].id, id) == 0)
            return &images[i];
    return NULL;
}

static void load_images(const char *manifest)
{
    FILE *fp = fopen(manifest, "r");
    char line[1400];
    if (fp == NULL) {
        perror(manifest);
        exit(2);
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        Image *image;
        unsigned base;
        FILE *in;
        long length;
        if (line[0] == '#' || line[0] == '\n')
            continue;
        if (image_count >= MAX_IMAGES)
            die("too many images in manifest");
        image = &images[image_count];
        if (sscanf(line, "%95s %1023s %x", image->id, image->path, &base) != 3)
            die("malformed image-manifest line");
        image->base = (uint32_t)base;
        in = fopen(image->path, "rb");
        if (in == NULL) {
            perror(image->path);
            exit(2);
        }
        if (fseek(in, 0, SEEK_END) != 0)
            die("image seek failed");
        length = ftell(in);
        if (length < 0 || fseek(in, 0, SEEK_SET) != 0)
            die("image length failed");
        image->size = (size_t)length;
        image->bytes = malloc(image->size);
        if (image->bytes == NULL)
            die("image allocation failed");
        if (fread(image->bytes, 1, image->size, in) != image->size)
            die("short image read");
        fclose(in);
        image_count++;
    }
    fclose(fp);
    if (image_count == 0)
        die("empty image manifest");
}

static uint32_t word_at(Image *image, uint32_t pc, size_t *file_offset)
{
    uint64_t off;
    if (pc < image->base)
        die("site precedes image base");
    off = (uint64_t)pc - image->base;
    if (off + 4 > image->size)
        die("site exceeds image bytes");
    if ((off & 3U) != 0)
        die("site is not word aligned");
    *file_offset = (size_t)off;
    return read_le32(image->bytes + off);
}

static int self_test(void)
{
    struct Case {
        uint32_t word;
        const char *kind;
        const char *reg;
        const char *discipline;
    } cases[] = {
        {0x03e00008U, "jr",   "ra", "D1_return"},
        {0x02c00008U, "jr",   "s6", "D2_switch_computed"},
        {0x0040f809U, "jalr", "v0", "D3_pointer_dispatch"},
        {0x0140f809U, "jalr", "t2", "D3_pointer_dispatch"},
    };
    size_t i;
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        uint32_t w = cases[i].word;
        unsigned op = w >> 26;
        unsigned rs = (w >> 21) & 31U;
        unsigned funct = w & 63U;
        const char *kind = op == 0 && funct == 8 ? "jr" :
                           op == 0 && funct == 9 ? "jalr" : "invalid";
        const char *discipline = funct == 9 ? "D3_pointer_dispatch" :
                                 rs == 31 ? "D1_return" : "D2_switch_computed";
        if (strcmp(kind, cases[i].kind) != 0 ||
            strcmp(regs[rs], cases[i].reg) != 0 ||
            strcmp(discipline, cases[i].discipline) != 0)
            die("self-test mismatch");
    }
    printf("{\"tool\":\"phase4_discipline_assignment\","
           "\"passed\":4,\"total\":4,\"verdict\":true}\n");
    return 0;
}

int main(int argc, char **argv)
{
    int i;
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0)
        return self_test();
    if (argc < 3) {
        fprintf(stderr, "usage: %s IMAGES.TXT SITE_ID...\n", argv[0]);
        return 2;
    }
    load_images(argv[1]);
    printf("{\"tool\":\"phase4_discipline_assignment\",\"site_count\":%d,\"sites\":[", argc - 2);
    for (i = 2; i < argc; i++) {
        char id_copy[MAX_ID];
        char *image_id, *pc_text, *declared_kind, *declared_reg, *extra;
        char *save = NULL;
        Image *image;
        unsigned long parsed_pc;
        uint32_t pc, word, delay_word;
        size_t off, delay_off;
        unsigned op, rs, rd, funct;
        const char *kind, *discipline;

        if (strlen(argv[i]) >= sizeof(id_copy))
            die("site ID too long");
        strcpy(id_copy, argv[i]);
        image_id = strtok_r(id_copy, ":", &save);
        pc_text = strtok_r(NULL, ":", &save);
        declared_kind = strtok_r(NULL, ":", &save);
        declared_reg = strtok_r(NULL, ":", &save);
        extra = strtok_r(NULL, ":", &save);
        if (image_id == NULL || pc_text == NULL || declared_kind == NULL ||
            declared_reg == NULL || extra != NULL)
            die("malformed site ID");
        errno = 0;
        parsed_pc = strtoul(pc_text, NULL, 0);
        if (errno != 0 || parsed_pc > UINT32_MAX)
            die("invalid site PC");
        pc = (uint32_t)parsed_pc;
        image = find_image(image_id);
        if (image == NULL)
            die("site names an image absent from manifest");
        word = word_at(image, pc, &off);
        delay_word = word_at(image, pc + 4U, &delay_off);
        (void)delay_off;
        op = word >> 26;
        rs = (word >> 21) & 31U;
        rd = (word >> 11) & 31U;
        funct = word & 63U;
        if (op != 0 || (funct != 8 && funct != 9))
            die("site bytes do not decode as jr/jalr");
        kind = funct == 8 ? "jr" : "jalr";
        if (strcmp(kind, declared_kind) != 0 || strcmp(regs[rs], declared_reg) != 0)
            die("site ID disagrees with instruction bytes");
        if (funct == 8)
            discipline = rs == 31 ? "D1_return" : "D2_switch_computed";
        else
            discipline = "D3_pointer_dispatch";
        if (i != 2)
            putchar(',');
        printf("{\"id\":\"%s\",\"image\":\"%s\","
               "\"pc\":\"0x%08" PRIx32 "\",\"file_offset\":%zu,"
               "\"word\":\"0x%08" PRIx32 "\",\"delay_slot_pc\":\"0x%08" PRIx32 "\","
               "\"delay_slot_word\":\"0x%08" PRIx32 "\","
               "\"decoded_kind\":\"%s\",\"decoded_register\":\"%s\","
               "\"link_register\":%s,\"discipline\":\"%s\"}",
               argv[i], image_id, pc, off, word, pc + 4U, delay_word,
               kind, regs[rs], funct == 9 ? "\"ra\"" : "null", discipline);
        if (funct == 9 && rd != 31U)
            die("jalr site does not link through ra");
    }
    printf("]}\n");
    return 0;
}
