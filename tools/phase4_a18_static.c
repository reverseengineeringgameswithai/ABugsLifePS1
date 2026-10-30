/* Phase 4 A18 pause-shell static analyzer.
 *
 * Reads the hash-verified pristine PS-X EXE and reports the pause flag census,
 * entry/resume/exit instruction contract, and the direct-call difference
 * between gameplay and the pause renderer. It never writes the input image.
 *
 * Build and run:
 *   cc -std=c11 -O2 -Wall -Wextra -Werror \
 *      tools/phase4_a18_static.c -o /tmp/phase4_a18_static
 *   /tmp/phase4_a18_static REBUILD/files/SCUS_942.88
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_EDGES = 256 };

typedef struct {
    uint32_t target;
    unsigned count;
} Edge;

typedef struct {
    Edge edge[MAX_EDGES];
    size_t count;
} EdgeSet;

typedef struct {
    uint32_t pc;
    uint32_t expected;
    const char *role;
} Check;

static uint32_t read_u32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static size_t image_offset(uint32_t va)
{
    return 0x800u + (size_t)(va - 0x80010000u);
}

static uint32_t word_at(const unsigned char *image, size_t size, uint32_t va)
{
    size_t offset = image_offset(va);
    if (va < 0x80010000u || offset + 4 > size) {
        fprintf(stderr, "address outside executable: 0x%08x\n", va);
        exit(10);
    }
    return read_u32(image + offset);
}

static void add_edge(EdgeSet *set, uint32_t target)
{
    size_t i;
    for (i = 0; i < set->count; ++i) {
        if (set->edge[i].target == target) {
            set->edge[i].count++;
            return;
        }
    }
    if (set->count == MAX_EDGES) {
        fprintf(stderr, "edge set overflow\n");
        exit(11);
    }
    set->edge[set->count].target = target;
    set->edge[set->count].count = 1;
    set->count++;
}

static int contains(const EdgeSet *set, uint32_t target)
{
    size_t i;
    for (i = 0; i < set->count; ++i)
        if (set->edge[i].target == target)
            return 1;
    return 0;
}

static int edge_compare(const void *a, const void *b)
{
    const Edge *left = a;
    const Edge *right = b;
    return left->target < right->target ? -1 : left->target > right->target;
}

static EdgeSet collect_calls(const unsigned char *image, size_t size,
                             uint32_t lo, uint32_t hi,
                             unsigned *jalr_count, unsigned *jr_count)
{
    EdgeSet set = {{0}, 0};
    uint32_t pc;
    *jalr_count = 0;
    *jr_count = 0;
    for (pc = lo; pc < hi; pc += 4) {
        uint32_t word = word_at(image, size, pc);
        if ((word >> 26) == 3) {
            uint32_t target = ((pc + 4) & 0xf0000000u) |
                              ((word & 0x03ffffffu) << 2);
            add_edge(&set, target);
        } else if ((word >> 26) == 0 && (word & 63u) == 9u) {
            (*jalr_count)++;
        } else if ((word >> 26) == 0 && (word & 63u) == 8u) {
            (*jr_count)++;
        }
    }
    qsort(set.edge, set.count, sizeof(set.edge[0]), edge_compare);
    return set;
}

static void show_edges(const char *label, const EdgeSet *primary,
                       const EdgeSet *other, int want_in_other)
{
    size_t i;
    printf("[%s]\n", label);
    for (i = 0; i < primary->count; ++i) {
        int in_other = other && contains(other, primary->edge[i].target);
        if (!other || in_other == want_in_other)
            printf("target=0x%08x calls=%u\n", primary->edge[i].target,
                   primary->edge[i].count);
    }
}

static int is_memory_op(unsigned op)
{
    return op == 0x20 || op == 0x21 || op == 0x23 || op == 0x24 ||
           op == 0x25 || op == 0x28 || op == 0x29 || op == 0x2b;
}

static void pause_flag_census(const unsigned char *image, size_t size)
{
    size_t offset;
    puts("[direct pause-flag accesses imm=0x224e]");
    for (offset = 0x800; offset + 4 <= size; offset += 4) {
        uint32_t word = read_u32(image + offset);
        unsigned op = word >> 26;
        if (is_memory_op(op) && (uint16_t)word == 0x224e) {
            printf("pc=0x%08x word=0x%08x op=0x%x base=r%u rt=r%u\n",
                   0x80010000u + (uint32_t)(offset - 0x800), word, op,
                   (word >> 21) & 31u, (word >> 16) & 31u);
        }
    }
}

int main(int argc, char **argv)
{
    static const Check checks[] = {
        {0x8004f314u, 0x30420008u, "current START test"},
        {0x8004f32cu, 0x30420008u, "previous START test"},
        {0x8004f344u, 0x1040000bu, "0x800822F8 gate"},
        {0x8004f36cu, 0x14620015u, "shell-state 3 gate"},
        {0x8004f380u, 0x14620010u, "mode 0x80 gate"},
        {0x8004f3acu, 0xa422224eu, "pause := 1"},
        {0x8004f7e8u, 0x30624000u, "Cross confirm test"},
        {0x8004f7f0u, 0x30620008u, "START confirm test"},
        {0x8004f858u, 0xa420224eu, "resume pause := 0"},
        {0x8004f884u, 0xaf820724u, "open exit confirmation"},
        {0x8004f9c0u, 0xa420224eu, "exit pause := 0"},
        {0x8004f9e4u, 0xa42223a0u, "exit shell state := 5"},
        {0x8004f9fcu, 0xa4222470u, "exit transition timer := 23"},
        {0x8004fa1cu, 0xa4620000u, "exit player flags |= 4"},
        {0x8004febcu, 0x8442224eu, "outer pause dispatch read"},
        {0x8004feccu, 0x0c013b35u, "outer gameplay call"},
        {0x8004fedcu, 0x0c013d1eu, "outer pause-render call"},
        {0x80069658u, 0xac2265a8u, "_SsVmFlush cursor store"}
    };
    FILE *file;
    long length;
    unsigned char *image;
    size_t i;
    unsigned gameplay_jalr, gameplay_jr, pause_jalr, pause_jr;
    EdgeSet gameplay;
    EdgeSet pause;

    if (argc != 2) {
        fprintf(stderr, "usage: %s PSX_EXE\n", argv[0]);
        return 2;
    }
    file = fopen(argv[1], "rb");
    if (!file)
        return 3;
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return 4;
    }
    image = malloc((size_t)length);
    if (!image || fread(image, 1, (size_t)length, file) != (size_t)length) {
        fclose(file);
        free(image);
        return 5;
    }
    fclose(file);
    if (length < 0x800 || memcmp(image, "PS-X EXE", 8) != 0) {
        free(image);
        return 6;
    }

    puts("A18 pause-shell static evidence");
    for (i = 0; i < sizeof(checks) / sizeof(checks[0]); ++i) {
        uint32_t actual = word_at(image, (size_t)length, checks[i].pc);
        printf("pc=0x%08x expected=0x%08x actual=0x%08x %s role=%s\n",
               checks[i].pc, checks[i].expected, actual,
               actual == checks[i].expected ? "PASS" : "FAIL", checks[i].role);
        if (actual != checks[i].expected) {
            free(image);
            return 7;
        }
    }
    pause_flag_census(image, (size_t)length);
    gameplay = collect_calls(image, (size_t)length, 0x8004ecd4u,
                             0x8004f478u, &gameplay_jalr, &gameplay_jr);
    pause = collect_calls(image, (size_t)length, 0x8004f480u,
                         0x8004fa40u, &pause_jalr, &pause_jr);
    printf("gameplay unique_jal=%zu jalr=%u jr=%u\n", gameplay.count,
           gameplay_jalr, gameplay_jr);
    printf("pause unique_jal=%zu jalr=%u jr=%u\n", pause.count,
           pause_jalr, pause_jr);
    show_edges("pause direct calls", &pause, NULL, 0);
    show_edges("gameplay-only direct calls", &gameplay, &pause, 0);
    show_edges("shared direct calls", &gameplay, &pause, 1);
    free(image);
    return 0;
}
