#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Conservative PS-X EXE static-ASM probe for the Phase 4 prerequisite gate.
 *
 * This program deliberately reports three different universes:
 *   - every byte in the loaded text image, partitioned by typed extents/gaps;
 *   - every aligned word with an architecturally valid jr/jalr encoding;
 *   - instructions reached from typed code/thunk entries using direct CFG edges.
 *
 * It does not claim that a code-extent candidate is executable, and it does not
 * follow unresolved indirect targets.  The Python compiler preserves those
 * limitations in the generated verdict.
 */

typedef struct {
    uint32_t start;
    uint32_t end;
    char type[16];
    char name[192];
    uint32_t reached_words;
} Extent;

typedef struct {
    uint32_t *items;
    size_t count;
    size_t capacity;
} Queue;

static unsigned char *g_image;
static size_t g_image_size;
static uint32_t g_load_base;
static uint32_t g_text_size;
static Extent *g_extents;
static size_t g_extent_count;
static unsigned char *g_flow;
static Queue g_queue;

enum {
    FLOW_SEEN = 1,
    FLOW_QUEUED = 2
};

static void die(const char *message)
{
    fprintf(stderr, "phase4_static_asm_probe: %s\n", message);
    exit(2);
}

static void die_errno(const char *message)
{
    fprintf(stderr, "phase4_static_asm_probe: %s: %s\n", message,
            strerror(errno));
    exit(2);
}

static void *xrealloc(void *ptr, size_t size)
{
    void *next = realloc(ptr, size);
    if (next == NULL)
        die_errno("realloc");
    return next;
}

static uint32_t read_le32(const unsigned char *bytes)
{
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static int extent_compare(const void *left, const void *right)
{
    const Extent *a = left;
    const Extent *b = right;
    if (a->start < b->start)
        return -1;
    if (a->start > b->start)
        return 1;
    return 0;
}

static int is_executable_type(const char *type)
{
    return strcmp(type, "code") == 0 || strcmp(type, "thunk") == 0;
}

static int owner_index(uint32_t pc)
{
    size_t low = 0;
    size_t high = g_extent_count;
    while (low < high) {
        size_t middle = low + (high - low) / 2;
        Extent *extent = &g_extents[middle];
        if (pc < extent->start) {
            high = middle;
        } else if (pc >= extent->end) {
            low = middle + 1;
        } else {
            return (int)middle;
        }
    }
    return -1;
}

static int image_word(uint32_t pc, uint32_t *word)
{
    uint32_t delta;
    size_t offset;
    if (pc < g_load_base)
        return 0;
    delta = pc - g_load_base;
    if (delta > g_text_size || g_text_size - delta < 4)
        return 0;
    offset = (size_t)0x800 + delta;
    if (offset > g_image_size || g_image_size - offset < 4)
        return 0;
    *word = read_le32(g_image + offset);
    return 1;
}

static int is_jr(uint32_t word)
{
    return (word >> 26) == 0 && (word & 0x001fffffU) == 8;
}

static int is_jalr(uint32_t word)
{
    /* rt and shamt are reserved zero; rd is intentionally unconstrained. */
    return (word >> 26) == 0 && (word & 0x001f07ffU) == 9;
}

static int is_conditional_branch(uint32_t word)
{
    unsigned op = word >> 26;
    unsigned rs = (word >> 21) & 31;
    if (op == 1 || (op >= 4 && op <= 7) ||
        (op >= 0x14 && op <= 0x17))
        return 1;
    return op >= 0x10 && op <= 0x13 && rs == 8;
}

static int is_terminating_special(uint32_t word)
{
    unsigned op = word >> 26;
    unsigned function = word & 63;
    return op == 0 && (function == 12 || function == 13);
}

static int writes_register(uint32_t word, unsigned reg)
{
    unsigned op = word >> 26;
    unsigned rt = (word >> 16) & 31;
    unsigned rd = (word >> 11) & 31;
    unsigned function = word & 63;

    if (reg == 0)
        return 0;
    if (op == 0) {
        switch (function) {
        case 8:  /* jr */
        case 12: /* syscall */
        case 13: /* break */
        case 16: /* mfhi writes rd, handled below */
        case 18: /* mflo writes rd, handled below */
            break;
        case 9:  /* jalr writes rd */
            return rd == reg;
        case 17: /* mthi */
        case 19: /* mtlo */
        case 24: /* mult */
        case 25: /* multu */
        case 26: /* div */
        case 27: /* divu */
            return 0;
        default:
            return rd == reg;
        }
        return (function == 16 || function == 18) && rd == reg;
    }
    if (op == 1 || op == 2 || op == 3 || (op >= 4 && op <= 7) ||
        (op >= 0x14 && op <= 0x17) || (op >= 0x28 && op <= 0x2f))
        return 0;
    return rt == reg;
}

static const char *definition_kind(uint32_t word)
{
    unsigned op = word >> 26;
    unsigned function = word & 63;
    if (op == 0) {
        if (function == 16 || function == 18)
            return "special_register";
        if (function == 9)
            return "link_register";
        return "arithmetic";
    }
    if (op == 15)
        return "constant_high";
    if (op == 8 || op == 9 || op == 12 || op == 13 || op == 14)
        return "immediate";
    if (op >= 0x20 && op <= 0x26)
        return "memory_load";
    if (op >= 0x10 && op <= 0x13)
        return "coprocessor";
    return "other_write";
}

static int find_last_definition(uint32_t pc, unsigned reg, uint32_t *def_pc,
                                uint32_t *def_word)
{
    int owner = owner_index(pc);
    uint32_t lower;
    uint32_t cursor;
    unsigned steps = 0;
    if (reg == 0 || owner < 0)
        return 0;
    lower = g_extents[owner].start;
    cursor = pc;
    while (cursor >= lower + 4 && steps < 128) {
        uint32_t word;
        cursor -= 4;
        steps++;
        if (!image_word(cursor, &word))
            break;
        if (writes_register(word, reg)) {
            *def_pc = cursor;
            *def_word = word;
            return 1;
        }
    }
    return 0;
}

static int resolve_linear_constant(uint32_t pc, unsigned reg, unsigned depth,
                                   uint32_t *value)
{
    uint32_t def_pc;
    uint32_t word;
    unsigned op;
    unsigned rs;
    unsigned rt;
    unsigned rd;
    unsigned function;
    uint32_t left;
    uint32_t right;

    if (reg == 0) {
        *value = 0;
        return 1;
    }
    if (depth > 12 || !find_last_definition(pc, reg, &def_pc, &word))
        return 0;
    op = word >> 26;
    rs = (word >> 21) & 31;
    rt = (word >> 16) & 31;
    rd = (word >> 11) & 31;
    function = word & 63;
    (void)rt;
    (void)rd;

    if (op == 15) {
        *value = (word & 0xffffU) << 16;
        return 1;
    }
    if (op == 8 || op == 9) {
        if (!resolve_linear_constant(def_pc, rs, depth + 1, &left))
            return 0;
        *value = left + (uint32_t)(int32_t)(int16_t)word;
        return 1;
    }
    if (op == 12 || op == 13 || op == 14) {
        if (!resolve_linear_constant(def_pc, rs, depth + 1, &left))
            return 0;
        if (op == 12)
            *value = left & (word & 0xffffU);
        else if (op == 13)
            *value = left | (word & 0xffffU);
        else
            *value = left ^ (word & 0xffffU);
        return 1;
    }
    if (op != 0)
        return 0;

    if (function == 0 || function == 2 || function == 3) {
        unsigned source = (word >> 16) & 31;
        unsigned shift = (word >> 6) & 31;
        if (!resolve_linear_constant(def_pc, source, depth + 1, &left))
            return 0;
        if (function == 0)
            *value = left << shift;
        else if (function == 2)
            *value = left >> shift;
        else
            *value = (uint32_t)((int32_t)left >> shift);
        return 1;
    }
    if (function == 32 || function == 33 || function == 34 ||
        function == 35 || function == 36 || function == 37 ||
        function == 38 || function == 39) {
        unsigned a = (word >> 21) & 31;
        unsigned b = (word >> 16) & 31;
        if (!resolve_linear_constant(def_pc, a, depth + 1, &left) ||
            !resolve_linear_constant(def_pc, b, depth + 1, &right))
            return 0;
        switch (function) {
        case 32:
        case 33:
            *value = left + right;
            break;
        case 34:
        case 35:
            *value = left - right;
            break;
        case 36:
            *value = left & right;
            break;
        case 37:
            *value = left | right;
            break;
        case 38:
            *value = left ^ right;
            break;
        default:
            *value = ~(left | right);
            break;
        }
        return 1;
    }
    return 0;
}

static void queue_push(uint32_t pc, int require_same_owner, int source_owner)
{
    uint32_t index;
    int owner;
    if (pc < g_load_base || pc - g_load_base >= g_text_size ||
        ((pc - g_load_base) & 3) != 0)
        return;
    owner = owner_index(pc);
    if (owner < 0 || !is_executable_type(g_extents[owner].type))
        return;
    if (require_same_owner && owner != source_owner)
        return;
    index = (pc - g_load_base) / 4;
    g_flow[index] |= FLOW_SEEN;
    if (g_flow[index] & FLOW_QUEUED)
        return;
    g_flow[index] |= FLOW_QUEUED;
    if (g_queue.count == g_queue.capacity) {
        g_queue.capacity = g_queue.capacity ? g_queue.capacity * 2 : 4096;
        g_queue.items = xrealloc(g_queue.items,
                                 g_queue.capacity * sizeof(*g_queue.items));
    }
    g_queue.items[g_queue.count++] = pc;
}

static void mark_delay(uint32_t pc, int source_owner)
{
    uint32_t index;
    int owner;
    if (pc < g_load_base || pc - g_load_base >= g_text_size ||
        ((pc - g_load_base) & 3) != 0)
        return;
    owner = owner_index(pc);
    if (owner != source_owner || owner < 0 ||
        !is_executable_type(g_extents[owner].type))
        return;
    index = (pc - g_load_base) / 4;
    g_flow[index] |= FLOW_SEEN;
}

static void run_direct_cfg(void)
{
    size_t cursor = 0;
    size_t i;
    for (i = 0; i < g_extent_count; i++) {
        if (is_executable_type(g_extents[i].type))
            queue_push(g_extents[i].start, 0, -1);
    }

    while (cursor < g_queue.count) {
        uint32_t pc = g_queue.items[cursor++];
        uint32_t word;
        unsigned op;
        int owner = owner_index(pc);
        if (owner < 0 || !image_word(pc, &word))
            continue;
        op = word >> 26;

        if (is_jr(word) || is_jalr(word)) {
            mark_delay(pc + 4, owner);
            if (is_jalr(word))
                queue_push(pc + 8, 1, owner);
            continue;
        }
        if (op == 2 || op == 3) {
            uint32_t target = ((pc + 4) & 0xf0000000U) |
                              ((word & 0x03ffffffU) << 2);
            mark_delay(pc + 4, owner);
            queue_push(target, 0, owner);
            if (op == 3)
                queue_push(pc + 8, 1, owner);
            continue;
        }
        if (is_conditional_branch(word)) {
            int32_t displacement = (int32_t)(int16_t)word * 4;
            uint32_t target = pc + 4 + (uint32_t)displacement;
            mark_delay(pc + 4, owner);
            queue_push(target, 0, owner);
            queue_push(pc + 8, 1, owner);
            continue;
        }
        if (is_terminating_special(word))
            continue;
        queue_push(pc + 4, 1, owner);
    }

    for (i = 0; i < g_extent_count; i++) {
        uint32_t pc;
        for (pc = g_extents[i].start; pc < g_extents[i].end; pc += 4) {
            if (pc >= g_load_base && pc - g_load_base < g_text_size &&
                (g_flow[(pc - g_load_base) / 4] & FLOW_SEEN))
                g_extents[i].reached_words++;
        }
    }
}

static void load_extents(const char *path)
{
    FILE *file = fopen(path, "r");
    char line[512];
    size_t capacity = 0;
    size_t i;
    if (file == NULL)
        die_errno("open extent TSV");
    while (fgets(line, sizeof(line), file) != NULL) {
        Extent item;
        unsigned start;
        unsigned end;
        int fields;
        if (line[0] == '#' || line[0] == '\n')
            continue;
        memset(&item, 0, sizeof(item));
        fields = sscanf(line, "%x\t%x\t%15[^\t]\t%191[^\n]", &start, &end,
                        item.type, item.name);
        if (fields != 4)
            die("malformed extent TSV row");
        item.start = start;
        item.end = end;
        if (item.start >= item.end || (item.start & 3) || (item.end & 3))
            die("invalid or unaligned extent");
        if (g_extent_count == capacity) {
            capacity = capacity ? capacity * 2 : 1024;
            g_extents = xrealloc(g_extents, capacity * sizeof(*g_extents));
        }
        g_extents[g_extent_count++] = item;
    }
    if (ferror(file))
        die_errno("read extent TSV");
    fclose(file);
    qsort(g_extents, g_extent_count, sizeof(*g_extents), extent_compare);
    for (i = 0; i < g_extent_count; i++) {
        if (g_extents[i].start < g_load_base ||
            g_extents[i].end > g_load_base + g_text_size)
            die("extent outside loaded text image");
        if (i && g_extents[i].start < g_extents[i - 1].end)
            die("overlapping extents");
    }
}

static void load_image(const char *path)
{
    FILE *file = fopen(path, "rb");
    long size;
    if (file == NULL)
        die_errno("open image");
    if (fseek(file, 0, SEEK_END) != 0)
        die_errno("seek image");
    size = ftell(file);
    if (size < 0)
        die_errno("size image");
    rewind(file);
    g_image_size = (size_t)size;
    g_image = malloc(g_image_size);
    if (g_image == NULL)
        die_errno("allocate image");
    if (fread(g_image, 1, g_image_size, file) != g_image_size)
        die_errno("read image");
    fclose(file);
    if (g_image_size < 0x800 || memcmp(g_image, "PS-X EXE", 8) != 0)
        die("input is not a PS-X EXE");
    g_load_base = read_le32(g_image + 0x18);
    g_text_size = read_le32(g_image + 0x1c);
    if ((g_load_base & 3) || (g_text_size & 3) ||
        g_image_size < (size_t)0x800 + g_text_size)
        die("invalid PS-X EXE load range");
    g_flow = calloc(g_text_size / 4, 1);
    if (g_flow == NULL)
        die_errno("allocate CFG bitmap");
}

static void emit_tsv(void)
{
    size_t i;
    uint32_t cursor = g_load_base;
    uint64_t claimed_bytes = 0;
    uint64_t gap_bytes = 0;
    unsigned nonreturn_candidates = 0;
    unsigned return_candidates = 0;
    unsigned typed_nonreturn_candidates = 0;
    unsigned reachable_nonreturn_candidates = 0;

    printf("meta\t0x%08x\t%u\t%zu\n", g_load_base, g_text_size,
           g_image_size);
    for (i = 0; i < g_extent_count; i++) {
        Extent *extent = &g_extents[i];
        if (cursor < extent->start) {
            printf("gap\t0x%08x\t0x%08x\n", cursor, extent->start);
            gap_bytes += extent->start - cursor;
        }
        printf("extent\t%zu\t0x%08x\t0x%08x\t%s\t%s\t%u\t%u\n", i,
               extent->start, extent->end, extent->type, extent->name,
               extent->reached_words, (extent->end - extent->start) / 4);
        claimed_bytes += extent->end - extent->start;
        cursor = extent->end;
    }
    if (cursor < g_load_base + g_text_size) {
        printf("gap\t0x%08x\t0x%08x\n", cursor,
               g_load_base + g_text_size);
        gap_bytes += g_load_base + g_text_size - cursor;
    }

    for (cursor = g_load_base; cursor < g_load_base + g_text_size;
         cursor += 4) {
        uint32_t word;
        unsigned reg;
        const char *kind;
        int owner;
        const char *owner_type;
        const char *owner_name;
        int reachable;
        uint32_t def_pc = 0;
        uint32_t def_word = 0;
        const char *def_kind;
        int def_base_reg = -1;
        int def_offset = 0;
        uint32_t constant = 0;
        int constant_known;

        if (!image_word(cursor, &word))
            die("internal image range error");
        if (is_jr(word)) {
            reg = (word >> 21) & 31;
            if (reg == 31) {
                kind = "jr_return";
                return_candidates++;
            } else {
                kind = "jr";
                nonreturn_candidates++;
            }
        } else if (is_jalr(word)) {
            reg = (word >> 21) & 31;
            kind = "jalr";
            nonreturn_candidates++;
        } else {
            continue;
        }

        owner = owner_index(cursor);
        owner_type = owner >= 0 ? g_extents[owner].type : "unclaimed";
        owner_name = owner >= 0 ? g_extents[owner].name : "-";
        reachable = !!(g_flow[(cursor - g_load_base) / 4] & FLOW_SEEN);
        if (strcmp(kind, "jr_return") != 0 && owner >= 0 &&
            is_executable_type(owner_type)) {
            typed_nonreturn_candidates++;
            if (reachable)
                reachable_nonreturn_candidates++;
        }

        if (reg == 0) {
            def_kind = "zero_register";
            constant_known = 1;
            constant = 0;
        } else if (find_last_definition(cursor, reg, &def_pc, &def_word)) {
            unsigned op = def_word >> 26;
            def_kind = definition_kind(def_word);
            if (op >= 0x20 && op <= 0x26) {
                def_base_reg = (int)((def_word >> 21) & 31);
                def_offset = (int)(int16_t)def_word;
            }
            constant_known = resolve_linear_constant(cursor, reg, 0,
                                                     &constant);
        } else {
            def_kind = "register_input";
            constant_known = 0;
        }

        printf("candidate\t0x%08x\t%s\t%u\t%d\t%s\t%s\t%d\t",
               cursor, kind, reg, owner, owner_type, owner_name, reachable);
        if (def_pc)
            printf("0x%08x\t%s\t%d\t%d\t", def_pc, def_kind,
                   def_base_reg, def_offset);
        else
            printf("-\t%s\t%d\t%d\t", def_kind, def_base_reg,
                   def_offset);
        if (constant_known)
            printf("0x%08x\n", constant);
        else
            printf("-\n");
    }

    printf("summary\t%llu\t%llu\t%u\t%u\t%u\t%u\t%zu\n",
           (unsigned long long)claimed_bytes,
           (unsigned long long)gap_bytes,
           nonreturn_candidates, return_candidates,
           typed_nonreturn_candidates, reachable_nonreturn_candidates,
           g_queue.count);
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: %s PSX_EXE EXTENTS_TSV\n", argv[0]);
        return 2;
    }
    load_image(argv[1]);
    load_extents(argv[2]);
    run_direct_cfg();
    emit_tsv();
    free(g_queue.items);
    free(g_flow);
    free(g_extents);
    free(g_image);
    return 0;
}
