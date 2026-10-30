/*
 * Phase 4 B06 invincibility static-frontier guard.
 *
 * This is intentionally row-specific. It reads the pristine PS-X EXE, the
 * resident function map, and the reconciled power-slot residual produced by
 * phase4_region_provenance_report.py. It then:
 *
 *   - decodes the complete blue-x1 seed/plant/contact dispatch chain;
 *   - verifies key grant/tick/damage/effect/reset instructions;
 *   - enumerates every direct caller of the shared damage handler;
 *   - classifies all 251 unresolved halfword accesses by owner/op/base;
 *   - partitions the 29 candidates in B06's shared direct owners into 25
 *     locally discharged sites and four explicitly retained local residuals.
 *
 * It does not claim that the remaining 222 cross-system candidates are
 * disjoint. That is the strict Phase 4 frontier still preventing closure.
 *
 * Build and run:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror \
 *      tools/phase4_b06_frontier.c -o /tmp/phase4_b06_frontier
 *   /tmp/phase4_b06_frontier \
 *      REBUILD/files/SCUS_942.88 \
 *      analysis/functions_resident.txt \
 *      analysis/phase4_region_provenance.json \
 *      analysis/phase4_b06_frontier_20260804.json
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FUNCS 2048
#define MAX_PCS 512
#define MAX_GROUPS 512

typedef struct {
    uint32_t address;
    uint32_t size;
    char name[96];
} Function;

typedef struct {
    char owner[96];
    char operation[8];
    char base[8];
    unsigned count;
} Group;

typedef struct {
    uint32_t address;
    uint32_t word;
} Anchor;

static const char *const k_registers[32] = {
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"
};

static const char *const k_row_local_owners[] = {
    "player_vertical_update",
    "effect_render_stage",
    "player_action_effects_update"
};

/* Exact sites whose local address family is disjoint from 0x800A657E. */
static const uint32_t k_local_discharged[] = {
    /* Direction ring and reference table. */
    0x8004823c, 0x80048290, 0x800482c4, 0x800482c8,
    /* Carried-actor record at 0x8009FD80 + actor_offset, stride 0x84. */
    0x80048364, 0x80048378,
    /* Bounded 0x80074970 angle/trig-table lookups. */
    0x800489cc, 0x800489f0, 0x80048a90, 0x80048abc,
    0x800492c8, 0x800492f8, 0x800494c8, 0x800494e8,
    0x80051be4, 0x80051bf0, 0x80051cc0,
    0x80055938, 0x80055944, 0x80055950, 0x80055980,
    0x80055a04, 0x80055a10, 0x80055a1c, 0x80055a4c
};

/* Kept open rather than promoted from a local pattern alone. */
static const uint32_t k_local_remaining[] = {
    0x80048e30, /* saved-base lookup; likely trig table, entry proof retained */
    0x80055874, /* saved-base lookup; likely trig table, entry proof retained */
    0x80055cf4, /* returned effect record +0x28 */
    0x80055d14  /* returned effect record +0x2A */
};

static const Anchor k_anchors[] = {
    {0x80048640, 0x8622007e}, /* lh v0,+0x7E(s1) */
    {0x80048654, 0xa622007e}, /* sh v0,+0x7E(s1) */
    {0x80049718, 0x8622007e}, /* outer damage-call gate */
    {0x80049740, 0x0c0129c0}, /* jal 0x8004A700 */
    {0x8004a7a4, 0x8463657e}, /* inner slot read */
    {0x8004a7e0, 0x84820000}, /* sign-specific slot read */
    {0x8004a808, 0xa4820000}, /* bubble consume, not B06 */
    {0x8004a888, 0xa4236594}, /* protected health decrement */
    {0x80055bc4, 0x8442657e}, /* positive-slot visual consumer */
    {0x80055be8, 0x24070039}, /* effect ID 57 */
    {0x8005882c, 0x00400008}, /* jr v0 walker dispatch */
    {0x800588b0, 0x87c20000}, /* current slot read */
    {0x800588bc, 0x24020190}, /* 400 on sound arm */
    {0x800588c0, 0x0c014265}, /* collect-sound dispatch */
    {0x800588c8, 0x24020190}, /* 400 on silent refresh */
    {0x800588d0, 0xa7c20000}, /* unconditional grant store */
    {0x8005b268, 0xa420657e}  /* respawn clear */
};

static uint8_t *g_image;
static size_t g_image_size;
static uint32_t g_load_address;
static uint32_t g_load_size;
static Function g_functions[MAX_FUNCS];
static unsigned g_function_count;

static uint32_t read_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint16_t read_le16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static const uint8_t *image_at(uint32_t address, size_t length)
{
    uint64_t end = (uint64_t)address + length;
    if (address < g_load_address || end > (uint64_t)g_load_address + g_load_size) {
        fprintf(stderr, "address outside executable: 0x%08X\n", address);
        exit(2);
    }
    return g_image + 0x800u + (address - g_load_address);
}

static uint32_t read_word(uint32_t address)
{
    return read_le32(image_at(address, 4));
}

static uint16_t read_half(uint32_t address)
{
    return read_le16(image_at(address, 2));
}

static const Function *function_owner(uint32_t address)
{
    const Function *best = NULL;
    unsigned i;

    for (i = 0; i < g_function_count && g_functions[i].address <= address; i++)
        best = &g_functions[i];
    if (best == NULL)
        return NULL;
    if (best->size != 0 && address >= best->address + best->size)
        return NULL;
    return best;
}

static const char *memory_operation(unsigned op)
{
    switch (op) {
    case 0x21: return "lh";
    case 0x25: return "lhu";
    case 0x29: return "sh";
    default: return "?";
    }
}

static uint32_t jal_target(uint32_t pc, uint32_t instruction)
{
    return ((pc + 4u) & 0xf0000000u) |
           ((instruction & 0x03ffffffu) << 2);
}

static int group_compare(const void *left, const void *right)
{
    const Group *a = left;
    const Group *b = right;
    int c;

    if (a->count != b->count)
        return a->count < b->count ? 1 : -1;
    c = strcmp(a->owner, b->owner);
    if (c != 0)
        return c;
    c = strcmp(a->operation, b->operation);
    if (c != 0)
        return c;
    return strcmp(a->base, b->base);
}

static int u32_contains(const uint32_t *values, size_t count, uint32_t value)
{
    size_t i;
    for (i = 0; i < count; i++) {
        if (values[i] == value)
            return 1;
    }
    return 0;
}

static int is_row_local_owner(const char *name)
{
    size_t i;
    for (i = 0; i < sizeof(k_row_local_owners) / sizeof(k_row_local_owners[0]); i++) {
        if (strcmp(name, k_row_local_owners[i]) == 0)
            return 1;
    }
    return 0;
}

static void load_executable(const char *path)
{
    FILE *file = fopen(path, "rb");
    long size;

    if (file == NULL) {
        perror(path);
        exit(2);
    }
    fseek(file, 0, SEEK_END);
    size = ftell(file);
    rewind(file);
    if (size < 0x800) {
        fprintf(stderr, "%s: too small for PS-X EXE\n", path);
        exit(2);
    }
    g_image_size = (size_t)size;
    g_image = malloc(g_image_size);
    if (g_image == NULL || fread(g_image, 1, g_image_size, file) != g_image_size) {
        fprintf(stderr, "%s: read failed\n", path);
        exit(2);
    }
    fclose(file);

    if (memcmp(g_image, "PS-X EXE", 8) != 0) {
        fprintf(stderr, "%s: invalid PS-X EXE header\n", path);
        exit(2);
    }
    g_load_address = read_le32(g_image + 0x18);
    g_load_size = read_le32(g_image + 0x1c);
    if (g_load_address != 0x80010000u ||
        g_load_size > g_image_size - 0x800u) {
        fprintf(stderr, "%s: unexpected executable mapping\n", path);
        exit(2);
    }
}

static void load_functions(const char *path)
{
    FILE *file = fopen(path, "r");
    char line[256];

    if (file == NULL) {
        perror(path);
        exit(2);
    }
    while (fgets(line, sizeof(line), file) != NULL) {
        unsigned address;
        unsigned size;
        char name[96];

        if (sscanf(line, "0x%x %u %95s", &address, &size, name) == 3) {
            Function *function;
            if (g_function_count == MAX_FUNCS) {
                fprintf(stderr, "too many functions\n");
                exit(2);
            }
            function = &g_functions[g_function_count++];
            function->address = address;
            function->size = size;
            snprintf(function->name, sizeof(function->name), "%s", name);
        }
    }
    fclose(file);
}

static unsigned load_residual_pcs(const char *path, uint32_t pcs[MAX_PCS])
{
    FILE *file = fopen(path, "rb");
    char *json;
    char *cursor;
    char *end;
    long size;
    unsigned count = 0;

    if (file == NULL) {
        perror(path);
        exit(2);
    }
    fseek(file, 0, SEEK_END);
    size = ftell(file);
    rewind(file);
    json = malloc((size_t)size + 1u);
    if (json == NULL || fread(json, 1, (size_t)size, file) != (size_t)size) {
        fprintf(stderr, "%s: read failed\n", path);
        exit(2);
    }
    fclose(file);
    json[size] = '\0';

    cursor = strstr(json, "\"still_open_pcs\"");
    if (cursor == NULL || (cursor = strchr(cursor, '[')) == NULL ||
        (end = strchr(cursor, ']')) == NULL) {
        fprintf(stderr, "%s: still_open_pcs array not found\n", path);
        exit(2);
    }
    while ((cursor = strstr(cursor, "0x")) != NULL && cursor < end) {
        unsigned value;
        if (sscanf(cursor, "0x%x", &value) != 1 || count == MAX_PCS) {
            fprintf(stderr, "%s: invalid residual PC list\n", path);
            exit(2);
        }
        pcs[count++] = value;
        cursor += 2;
    }
    free(json);
    return count;
}

static void write_pc_array(FILE *file, const uint32_t *values, size_t count)
{
    size_t i;
    fputs("[", file);
    for (i = 0; i < count; i++)
        fprintf(file, "%s\"0x%08X\"", i == 0 ? "" : ", ", values[i]);
    fputs("]", file);
}

int main(int argc, char **argv)
{
    uint32_t pcs[MAX_PCS];
    unsigned pc_count;
    Group groups[MAX_GROUPS];
    unsigned group_count = 0;
    unsigned reads = 0;
    unsigned writes = 0;
    unsigned row_local = 0;
    unsigned row_local_partitioned = 0;
    uint32_t callers[16];
    unsigned caller_count = 0;
    unsigned i;
    FILE *output;

    uint16_t type;
    uint16_t extra;
    int ctor;
    uint16_t action;
    uint32_t plant_handler;
    uint32_t grant_handler;

    if (argc != 5) {
        fprintf(stderr, "usage: %s EXE FUNCTIONS REGION_JSON OUT_JSON\n", argv[0]);
        return 2;
    }

    load_executable(argv[1]);
    load_functions(argv[2]);
    pc_count = load_residual_pcs(argv[3], pcs);

    for (i = 0; i < sizeof(k_anchors) / sizeof(k_anchors[0]); i++) {
        uint32_t actual = read_word(k_anchors[i].address);
        if (actual != k_anchors[i].word) {
            fprintf(stderr, "anchor mismatch at 0x%08X: %08X != %08X\n",
                    k_anchors[i].address, actual, k_anchors[i].word);
            return 1;
        }
    }

    type = read_half(0x8007a458);
    extra = read_half(0x8007a45a);
    ctor = ((int16_t)extra >> 12) + 0x23;
    plant_handler = read_word(0x8001b848u + (uint32_t)(type - 2u) * 4u);
    action = read_half(0x8007941cu + (uint32_t)ctor * 0x14u);
    grant_handler = read_word(0x8001b570u + (uint32_t)(action - 2u) * 4u);
    if (type != 7 || extra != 0x2000 || ctor != 0x25 || action != 0x0c ||
        plant_handler != 0x8005c744 || grant_handler != 0x800588b0) {
        fprintf(stderr, "B06 production-chain mismatch\n");
        return 1;
    }

    for (i = 0; i < pc_count; i++) {
        uint32_t instruction = read_word(pcs[i]);
        unsigned op = instruction >> 26;
        unsigned rs = (instruction >> 21) & 31u;
        const Function *function = function_owner(pcs[i]);
        const char *owner_name = function == NULL ? "?" : function->name;
        const char *operation = memory_operation(op);
        unsigned group;
        int classified_local;

        if (strcmp(operation, "?") == 0) {
            fprintf(stderr, "non-halfword residual at 0x%08X\n", pcs[i]);
            return 1;
        }
        if (op == 0x29)
            writes++;
        else
            reads++;

        classified_local =
            u32_contains(k_local_discharged,
                         sizeof(k_local_discharged) / sizeof(k_local_discharged[0]),
                         pcs[i]) ||
            u32_contains(k_local_remaining,
                         sizeof(k_local_remaining) / sizeof(k_local_remaining[0]),
                         pcs[i]);
        if (is_row_local_owner(owner_name)) {
            row_local++;
            if (classified_local)
                row_local_partitioned++;
        } else if (classified_local) {
            fprintf(stderr, "local classification escaped owner set: 0x%08X\n", pcs[i]);
            return 1;
        }

        for (group = 0; group < group_count; group++) {
            if (strcmp(groups[group].owner, owner_name) == 0 &&
                strcmp(groups[group].operation, operation) == 0 &&
                strcmp(groups[group].base, k_registers[rs]) == 0)
                break;
        }
        if (group == group_count) {
            Group *new_group;
            if (group_count == MAX_GROUPS) {
                fprintf(stderr, "too many groups\n");
                return 2;
            }
            new_group = &groups[group_count++];
            snprintf(new_group->owner, sizeof(new_group->owner), "%s", owner_name);
            snprintf(new_group->operation, sizeof(new_group->operation), "%s", operation);
            snprintf(new_group->base, sizeof(new_group->base), "%s", k_registers[rs]);
            new_group->count = 0;
        }
        groups[group].count++;
    }

    if (pc_count != 251 || reads != 192 || writes != 59 ||
        row_local != 29 || row_local_partitioned != 29 || group_count != 79) {
        fprintf(stderr,
                "stale frontier: total=%u reads=%u writes=%u local=%u partitioned=%u groups=%u\n",
                pc_count, reads, writes, row_local, row_local_partitioned, group_count);
        return 1;
    }

    for (uint32_t pc = g_load_address;
         pc + 4u <= g_load_address + g_load_size;
         pc += 4u) {
        uint32_t instruction = read_word(pc);
        if ((instruction >> 26) == 3u && jal_target(pc, instruction) == 0x8004a700u) {
            if (caller_count == sizeof(callers) / sizeof(callers[0]))
                return 2;
            callers[caller_count++] = pc;
        }
    }
    if (caller_count != 6) {
        fprintf(stderr, "unexpected damage-handler caller count: %u\n", caller_count);
        return 1;
    }

    qsort(groups, group_count, sizeof(groups[0]), group_compare);
    output = fopen(argv[4], "w");
    if (output == NULL) {
        perror(argv[4]);
        return 2;
    }
    fprintf(output, "{\n");
    fprintf(output, "  \"schema\": \"phase4-b06-frontier-v1\",\n");
    fprintf(output, "  \"row\": \"B06_invincibility\",\n");
    fprintf(output, "  \"status\": \"partial_open_static_frontier_narrowed\",\n");
    fprintf(output, "  \"pristine_exe\": {\"load_address\": \"0x%08X\", \"load_size\": %u, \"anchors_checked\": %zu},\n",
            g_load_address, g_load_size, sizeof(k_anchors) / sizeof(k_anchors[0]));
    fprintf(output, "  \"production_chain\": {\"pair_index\": 4, \"type\": %u, \"extra\": \"0x%04X\", \"plant_handler\": \"0x%08X\", \"ctor\": %d, \"action\": \"0x%X\", \"grant_handler\": \"0x%08X\"},\n",
            type, extra, plant_handler, ctor, action, grant_handler);
    fprintf(output, "  \"damage_handler\": {\"address\": \"0x8004A700\", \"direct_callers\": ");
    write_pc_array(output, callers, caller_count);
    fprintf(output, "},\n");
    fprintf(output, "  \"reconciled_residual\": {\"total\": %u, \"reads\": %u, \"writes\": %u, \"groups\": %u, \"row_local_shared_owner_candidates\": %u, \"cross_system_candidates\": %u},\n",
            pc_count, reads, writes, group_count, row_local, pc_count - row_local);
    fprintf(output, "  \"local_static_partition\": {\n");
    fprintf(output, "    \"discharged_count\": %zu,\n",
            sizeof(k_local_discharged) / sizeof(k_local_discharged[0]));
    fprintf(output, "    \"discharged_pcs\": ");
    write_pc_array(output, k_local_discharged,
                   sizeof(k_local_discharged) / sizeof(k_local_discharged[0]));
    fprintf(output, ",\n    \"remaining_count\": %zu,\n",
            sizeof(k_local_remaining) / sizeof(k_local_remaining[0]));
    fprintf(output, "    \"remaining_pcs\": ");
    write_pc_array(output, k_local_remaining,
                   sizeof(k_local_remaining) / sizeof(k_local_remaining[0]));
    fprintf(output, "\n  },\n");
    fprintf(output, "  \"groups\": [\n");
    for (i = 0; i < group_count; i++) {
        fprintf(output,
                "    {\"count\": %u, \"owner\": \"%s\", \"operation\": \"%s\", \"base\": \"%s\"}%s\n",
                groups[i].count, groups[i].owner, groups[i].operation,
                groups[i].base, i + 1 == group_count ? "" : ",");
    }
    fprintf(output, "  ],\n");
    fprintf(output, "  \"closure\": {\"strict_full\": false, \"bounded_exhausted\": false, \"reason\": \"four row-local and 222 cross-system potential intersections remain; the referenced canonical frontier compiler is absent\"}\n");
    fprintf(output, "}\n");
    fclose(output);

    printf("B06 C FRONTIER PASS: anchors=%zu residual=%u reads=%u writes=%u groups=%u local=%u discharged=%zu remaining=%zu cross_system=%u callers=%u\n",
           sizeof(k_anchors) / sizeof(k_anchors[0]), pc_count, reads, writes,
           group_count, row_local,
           sizeof(k_local_discharged) / sizeof(k_local_discharged[0]),
           sizeof(k_local_remaining) / sizeof(k_local_remaining[0]),
           pc_count - row_local, caller_count);

    free(g_image);
    return 0;
}
