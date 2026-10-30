#include <errno.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_HEADER 0x800u
#define EXPECTED_T_ADDR 0x80010000u
#define EXPECTED_T_SIZE 0x72800u
#define OP_TABLE 0x8001b2f4u
#define CALL_TABLE 0x8001b35cu
#define PROGRAM_REGION_LO 0x8007745cu
#define PROGRAM_REGION_HI 0x80077af8u
#define PROGRAM_POINTER_TABLE 0x80077af8u
#define VM_INIT 0x8004c10cu
#define VM_INTERPRETER 0x8004c13cu
#define VM_CLUSTER_END 0x8004caa4u
#define MAX_PROGRAM_POINTERS 64u
#define MAX_PROGRAMS 64u
#define MAX_PROGRAM_INSNS 1024u
#define MAX_FIELDS 256u

typedef struct {
    uint8_t *bytes;
    size_t size;
    uint32_t t_addr;
    uint32_t t_size;
} Exe;

typedef struct {
    int16_t offset;
    uint64_t load8, load16, load32;
    uint64_t store8, store16, store32;
} Field;

typedef struct {
    uint32_t ip;
    int16_t raw;
    uint8_t index;
    uint16_t advance;
    uint16_t operands[2];
    uint8_t operand_count;
    uint32_t branch_target;
    uint8_t call_slot;
    uint32_t call_target;
} VmInsn;

typedef struct {
    uint32_t start;
    uint32_t end;
    VmInsn insns[MAX_PROGRAM_INSNS];
    size_t count;
    bool invalid;
    bool loop_target_outside;
} Program;

static const char *SEMANTICS[26] = {
    "jump_back", "park_end", "wait", "wait_random", "random_dir_step",
    "path_next_waypoint", "park_seek", "park_arrive_test", "park_arrive_stop",
    "branch_if_s3", "park_path", "seek_path_endpoint", "call_native",
    "flags_mask", "anim_clip_load", "cond_noise_mask", "chase_radius_scratch",
    "player_proximity", "park_seek18", "park19", "branch_fwd_if_s3",
    "park21", "done_disable", "set_byte_params", "call_play_sound",
    "cond_powerup_flag"
};

static const uint16_t ADVANCE[26] = {
    4, 2, 4, 6, 2, 2, 2, 2, 2, 4, 2, 4, 4,
    6, 6, 4, 4, 4, 2, 2, 4, 2, 2, 6, 4, 2
};

static void die(const char *message) {
    fprintf(stderr, "phase4_e07_static: %s\n", message);
    exit(1);
}

static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint16_t le16(const uint8_t *p) {
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint8_t *read_file(const char *path, size_t *size_out) {
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        fprintf(stderr, "phase4_e07_static: cannot open %s: %s\n", path, strerror(errno));
        exit(1);
    }
    if (fseek(fp, 0, SEEK_END) != 0)
        die("fseek failed");
    long end = ftell(fp);
    if (end < 0)
        die("ftell failed");
    rewind(fp);
    uint8_t *bytes = malloc((size_t)end ? (size_t)end : 1u);
    if (!bytes)
        die("out of memory");
    if ((size_t)end && fread(bytes, 1, (size_t)end, fp) != (size_t)end)
        die("short read");
    fclose(fp);
    *size_out = (size_t)end;
    return bytes;
}

static Exe load_exe(const char *path) {
    Exe exe = {0};
    exe.bytes = read_file(path, &exe.size);
    if (exe.size < EXE_HEADER || memcmp(exe.bytes, "PS-X EXE", 8) != 0)
        die("input is not a PS-X EXE");
    exe.t_addr = le32(exe.bytes + 0x18);
    exe.t_size = le32(exe.bytes + 0x1c);
    if (exe.t_addr != EXPECTED_T_ADDR || exe.t_size != EXPECTED_T_SIZE)
        die("unexpected pristine executable layout");
    if ((uint64_t)EXE_HEADER + exe.t_size > exe.size)
        die("truncated PS-X EXE payload");
    return exe;
}

static const uint8_t *va_ptr(const Exe *exe, uint32_t va, size_t length) {
    if (va < exe->t_addr || (uint64_t)va + length > (uint64_t)exe->t_addr + exe->t_size)
        die("virtual address outside executable payload");
    return exe->bytes + EXE_HEADER + (va - exe->t_addr);
}

static uint32_t exe_u32(const Exe *exe, uint32_t va) {
    return le32(va_ptr(exe, va, 4));
}

static uint16_t exe_u16(const Exe *exe, uint32_t va) {
    return le16(va_ptr(exe, va, 2));
}

static int cmp_u32(const void *left, const void *right) {
    uint32_t a = *(const uint32_t *)left;
    uint32_t b = *(const uint32_t *)right;
    return (a > b) - (a < b);
}

static bool valid_program_pointer(uint32_t value) {
    return value >= PROGRAM_REGION_LO && value < PROGRAM_REGION_HI && (value & 1u) == 0;
}

static uint32_t jump_target(uint32_t pc, uint32_t word) {
    return ((pc + 4u) & 0xf0000000u) | ((word & 0x03ffffffu) << 2);
}

static Field *field_for(Field fields[MAX_FIELDS], size_t *count, int16_t offset) {
    for (size_t i = 0; i < *count; ++i) {
        if (fields[i].offset == offset)
            return &fields[i];
    }
    if (*count == MAX_FIELDS)
        die("too many field offsets");
    Field *field = &fields[(*count)++];
    memset(field, 0, sizeof(*field));
    field->offset = offset;
    return field;
}

static int cmp_field(const void *left, const void *right) {
    const Field *a = left;
    const Field *b = right;
    return (a->offset > b->offset) - (a->offset < b->offset);
}

static void census_fields(const Exe *exe, unsigned base_register,
                          Field fields[MAX_FIELDS], size_t *field_count) {
    for (uint32_t pc = VM_INIT; pc < VM_CLUSTER_END; pc += 4) {
        uint32_t word = exe_u32(exe, pc);
        unsigned opcode = word >> 26;
        unsigned rs = (word >> 21) & 31u;
        if (rs != base_register)
            continue;
        int16_t offset = (int16_t)(word & 0xffffu);
        Field *field = NULL;
        switch (opcode) {
        case 0x20: case 0x24:
            field = field_for(fields, field_count, offset); ++field->load8; break;
        case 0x21: case 0x25:
            field = field_for(fields, field_count, offset); ++field->load16; break;
        case 0x23:
            field = field_for(fields, field_count, offset); ++field->load32; break;
        case 0x28:
            field = field_for(fields, field_count, offset); ++field->store8; break;
        case 0x29:
            field = field_for(fields, field_count, offset); ++field->store16; break;
        case 0x2b:
            field = field_for(fields, field_count, offset); ++field->store32; break;
        default:
            break;
        }
    }
    qsort(fields, *field_count, sizeof(fields[0]), cmp_field);
}

static uint32_t resolve_call_stub(const Exe *exe, uint32_t stub) {
    uint32_t word = exe_u32(exe, stub);
    unsigned opcode = word >> 26;
    if (opcode == 2 || opcode == 3)
        return jump_target(stub, word);
    return stub;
}

static Program decode_program(const Exe *exe, uint32_t start, uint32_t end,
                              const uint32_t call_targets[9], uint64_t usage[26],
                              uint64_t call_usage[9]) {
    Program program = {.start = start, .end = end};
    uint32_t ip = start;
    bool seen[(PROGRAM_REGION_HI - PROGRAM_REGION_LO) / 2] = {0};
    while (ip < end && ip < PROGRAM_REGION_HI) {
        size_t seen_index = (ip - PROGRAM_REGION_LO) / 2u;
        if (seen_index >= sizeof(seen) || seen[seen_index])
            break;
        seen[seen_index] = true;
        if (program.count == MAX_PROGRAM_INSNS)
            die("too many bytecode instructions");
        VmInsn *insn = &program.insns[program.count++];
        memset(insn, 0, sizeof(*insn));
        insn->ip = ip;
        insn->raw = (int16_t)exe_u16(exe, ip);
        int index = (int)insn->raw + 1;
        if (index < 0 || index >= 26) {
            program.invalid = true;
            break;
        }
        insn->index = (uint8_t)index;
        insn->advance = ADVANCE[index];
        insn->operand_count = (uint8_t)((insn->advance - 2u) / 2u);
        if (insn->operand_count > 2)
            die("unsupported bytecode operand count");
        for (unsigned i = 0; i < insn->operand_count; ++i)
            insn->operands[i] = exe_u16(exe, ip + 2u + i * 2u);
        ++usage[index];
        if (index == 0 && insn->operand_count) {
            int16_t delta = (int16_t)insn->operands[0];
            insn->branch_target = ip - (uint32_t)((int32_t)delta * 2);
        } else if ((index == 9 || index == 20) && insn->operand_count) {
            insn->branch_target = ip + (uint32_t)insn->operands[0] * 2u;
        }
        if (insn->branch_target &&
            (insn->branch_target < start || insn->branch_target >= end))
            program.loop_target_outside = true;
        if (index == 12 && insn->operand_count) {
            unsigned slot = insn->operands[0];
            if (slot >= 1 && slot <= 9) {
                insn->call_slot = (uint8_t)slot;
                insn->call_target = call_targets[slot - 1];
                ++call_usage[slot - 1];
            } else {
                program.invalid = true;
            }
        }
        ip += insn->advance;
    }
    return program;
}

static void sha256_hex(const uint8_t *bytes, size_t size, char out[65]) {
    uint8_t digest[SHA256_DIGEST_LENGTH];
    static const char HEX[] = "0123456789abcdef";
    SHA256(bytes, size, digest);
    for (size_t i = 0; i < sizeof(digest); ++i) {
        out[i * 2] = HEX[digest[i] >> 4];
        out[i * 2 + 1] = HEX[digest[i] & 15u];
    }
    out[64] = '\0';
}

static const char *base_name(const char *path) {
    const char *slash = strrchr(path, '/');
    return slash ? slash + 1 : path;
}

static size_t scan_jal(const uint8_t *bytes, size_t size, uint32_t target,
                       uint32_t *offsets, size_t capacity) {
    size_t count = 0;
    uint32_t encoded = 0x0c000000u | ((target >> 2) & 0x03ffffffu);
    for (size_t offset = 0; offset + 4 <= size; offset += 4) {
        if (le32(bytes + offset) != encoded)
            continue;
        if (count < capacity)
            offsets[count] = (uint32_t)offset;
        ++count;
    }
    return count;
}

static void print_fields(const char *name, unsigned reg, const Field *fields, size_t count) {
    printf("    \"%s\": {\"base_register\": \"$%u\", \"fields\": [\n", name, reg);
    for (size_t i = 0; i < count; ++i) {
        const Field *f = &fields[i];
        printf("      {\"offset\": %d, \"load8\": %" PRIu64 ", \"load16\": %" PRIu64
               ", \"load32\": %" PRIu64 ", \"store8\": %" PRIu64
               ", \"store16\": %" PRIu64 ", \"store32\": %" PRIu64 "}%s\n",
               f->offset, f->load8, f->load16, f->load32,
               f->store8, f->store16, f->store32, i + 1 == count ? "" : ",");
    }
    printf("    ]}");
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s SCUS_942.88 [LEVEL_OVERLAY.BIN ...]\n", argv[0]);
        return 2;
    }
    Exe exe = load_exe(argv[1]);
    char exe_hash[65];
    sha256_hex(exe.bytes, exe.size, exe_hash);

    uint32_t handlers[26];
    uint32_t call_stubs[9], call_targets[9];
    for (unsigned i = 0; i < 26; ++i)
        handlers[i] = exe_u32(&exe, OP_TABLE + i * 4u);
    for (unsigned i = 0; i < 9; ++i) {
        call_stubs[i] = exe_u32(&exe, CALL_TABLE + i * 4u);
        call_targets[i] = resolve_call_stub(&exe, call_stubs[i]);
    }

    uint32_t pointer_entries[MAX_PROGRAM_POINTERS];
    size_t pointer_count = 0;
    while (pointer_count < MAX_PROGRAM_POINTERS) {
        uint32_t value = exe_u32(&exe, PROGRAM_POINTER_TABLE + (uint32_t)pointer_count * 4u);
        if (!valid_program_pointer(value))
            break;
        pointer_entries[pointer_count++] = value;
    }
    uint32_t starts[MAX_PROGRAMS];
    size_t program_count = 0;
    for (size_t i = 0; i < pointer_count; ++i) {
        bool duplicate = false;
        for (size_t j = 0; j < program_count; ++j)
            duplicate |= starts[j] == pointer_entries[i];
        if (!duplicate)
            starts[program_count++] = pointer_entries[i];
    }
    qsort(starts, program_count, sizeof(starts[0]), cmp_u32);

    uint64_t opcode_usage[26] = {0};
    uint64_t call_usage[9] = {0};
    Program programs[MAX_PROGRAMS];
    for (size_t i = 0; i < program_count; ++i) {
        uint32_t end = i + 1 < program_count ? starts[i + 1] : PROGRAM_REGION_HI;
        programs[i] = decode_program(&exe, starts[i], end, call_targets,
                                     opcode_usage, call_usage);
    }

    Field actor_fields[MAX_FIELDS] = {{0}}, metadata_fields[MAX_FIELDS] = {{0}}, ip_fields[MAX_FIELDS] = {{0}};
    size_t actor_count = 0, metadata_count = 0, ip_count = 0;
    census_fields(&exe, 16, actor_fields, &actor_count);
    census_fields(&exe, 21, metadata_fields, &metadata_count);
    census_fields(&exe, 17, ip_fields, &ip_count);

    const uint8_t *payload = exe.bytes + EXE_HEADER;
    uint32_t resident_init_offsets[256], resident_interpreter_offsets[256];
    size_t resident_init_candidates = scan_jal(payload, exe.t_size, VM_INIT,
                                               resident_init_offsets, 256);
    size_t resident_interpreter_candidates = scan_jal(payload, exe.t_size, VM_INTERPRETER,
                                                      resident_interpreter_offsets, 256);

    printf("{\n");
    printf("  \"schema\": \"abl-phase4-e07-static-v1\",\n");
    printf("  \"row\": \"E07_event_vm\",\n");
    printf("  \"exe\": {\"sha256\": \"%s\", \"t_addr\": \"0x%08x\", \"t_size\": %u},\n",
           exe_hash, exe.t_addr, exe.t_size);
    printf("  \"interpreter\": {\"address\": \"0x8004c13c\", \"opcode_table\": \"0x8001b2f4\", \"entries\": 26, \"handlers\": [\n");
    for (unsigned i = 0; i < 26; ++i) {
        printf("    {\"index\": %u, \"stream_opcode\": %d, \"name\": \"%s\", \"target\": \"0x%08x\", \"advance\": %u, \"program_uses\": %" PRIu64 "}%s\n",
               i, (int)i - 1, SEMANTICS[i], handlers[i], ADVANCE[i], opcode_usage[i],
               i == 25 ? "" : ",");
    }
    printf("  ]},\n");
    printf("  \"call_subtable\": {\"address\": \"0x8001b35c\", \"entries\": [\n");
    for (unsigned i = 0; i < 9; ++i) {
        printf("    {\"slot\": %u, \"stub\": \"0x%08x\", \"target\": \"0x%08x\", \"target_class\": \"%s\", \"program_uses\": %" PRIu64 "}%s\n",
               i + 1, call_stubs[i], call_targets[i],
               call_targets[i] >= 0x800b0000u ? "level_overlay" : "resident",
               call_usage[i], i == 8 ? "" : ",");
    }
    printf("  ]},\n");
    uint32_t pointer_table_end = PROGRAM_POINTER_TABLE + (uint32_t)pointer_count * 4u;
    printf("  \"program_pointer_table\": {\"address\": \"0x80077af8\", \"end_exclusive\": \"0x%08x\", \"consecutive_entries\": %zu, \"unique_programs\": %zu, \"first_non_program_word\": \"0x%08x\", \"entries\": [",
           pointer_table_end, pointer_count, program_count, exe_u32(&exe, pointer_table_end));
    for (size_t i = 0; i < pointer_count; ++i)
        printf("%s\"0x%08x\"", i ? ", " : "", pointer_entries[i]);
    printf("]},\n");
    printf("  \"programs\": [\n");
    for (size_t p = 0; p < program_count; ++p) {
        const Program *program = &programs[p];
        printf("    {\"entry\": \"0x%08x\", \"end_exclusive\": \"0x%08x\", \"instruction_count\": %zu, \"invalid\": %s, \"branch_outside_program\": %s, \"instructions\": [\n",
               program->start, program->end, program->count,
               program->invalid ? "true" : "false",
               program->loop_target_outside ? "true" : "false");
        for (size_t i = 0; i < program->count; ++i) {
            const VmInsn *insn = &program->insns[i];
            printf("      {\"ip\": \"0x%08x\", \"index\": %u, \"stream_opcode\": %d, \"name\": \"%s\", \"operands\": [",
                   insn->ip, insn->index, insn->raw, SEMANTICS[insn->index]);
            for (unsigned operand = 0; operand < insn->operand_count; ++operand)
                printf("%s%u", operand ? ", " : "", insn->operands[operand]);
            printf("]");
            if (insn->branch_target)
                printf(", \"branch_target\": \"0x%08x\"", insn->branch_target);
            if (insn->call_slot)
                printf(", \"call_slot\": %u, \"call_target\": \"0x%08x\"", insn->call_slot, insn->call_target);
            printf("}%s\n", i + 1 == program->count ? "" : ",");
        }
        printf("    ]}%s\n", p + 1 == program_count ? "" : ",");
    }
    printf("  ],\n");
    printf("  \"field_access_census\": {\n");
    print_fields("actor_s0", 16, actor_fields, actor_count); printf(",\n");
    print_fields("program_metadata_s5", 21, metadata_fields, metadata_count); printf(",\n");
    print_fields("bytecode_ip_s1", 17, ip_fields, ip_count); printf("\n  },\n");
    printf("  \"direct_jal_opcode_candidates\": {\"resident_vm_init\": {\"count\": %zu, \"pcs\": [", resident_init_candidates);
    for (size_t i = 0; i < resident_init_candidates && i < 256; ++i)
        printf("%s\"0x%08x\"", i ? ", " : "", exe.t_addr + resident_init_offsets[i]);
    printf("]}, \"resident_interpreter\": {\"count\": %zu, \"pcs\": [", resident_interpreter_candidates);
    for (size_t i = 0; i < resident_interpreter_candidates && i < 256; ++i)
        printf("%s\"0x%08x\"", i ? ", " : "", exe.t_addr + resident_interpreter_offsets[i]);
    printf("]}, \"overlays\": [\n");
    for (int arg = 2; arg < argc; ++arg) {
        size_t size = 0;
        uint8_t *bytes = read_file(argv[arg], &size);
        char hash[65];
        uint32_t init_offsets[256], interpreter_offsets[256];
        size_t init_count = scan_jal(bytes, size, VM_INIT, init_offsets, 256);
        size_t interpreter_count = scan_jal(bytes, size, VM_INTERPRETER, interpreter_offsets, 256);
        sha256_hex(bytes, size, hash);
        printf("    {\"file\": \"%s\", \"size\": %zu, \"sha256\": \"%s\", \"vm_init_offsets\": [",
               base_name(argv[arg]), size, hash);
        for (size_t i = 0; i < init_count && i < 256; ++i)
            printf("%s%u", i ? ", " : "", init_offsets[i]);
        printf("], \"interpreter_offsets\": [");
        for (size_t i = 0; i < interpreter_count && i < 256; ++i)
            printf("%s%u", i ? ", " : "", interpreter_offsets[i]);
        printf("]}%s\n", arg + 1 == argc ? "" : ",");
        free(bytes);
    }
    printf("  ]}\n");
    printf("}\n");

    free(exe.bytes);
    return 0;
}
