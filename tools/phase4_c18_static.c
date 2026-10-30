/*
 * Phase 4 C18 Bonus Challenge Entry static gate.
 *
 * Build and run:
 *   cc -O2 -Wall -Wextra -o /tmp/phase4_c18_static \
 *      tools/phase4_c18_static.c -lcrypto
 *   /tmp/phase4_c18_static SCUS_942.88 REBUILD/files/LEVEL06/LEVEL1.BIN \
 *      > analysis/phase4_c18_bonus_entry.json
 */
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RETAIL_SHA256 \
    "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"
#define BONUS_OVERLAY_SHA256 \
    "4ea72fd6caaddb287d8eef2086c3b66a74191b6c36ddbeb7feaa1fbf5c8db172"
#define OVERLAY_BASE 0x800b39a0u

struct blob {
    uint8_t *data;
    size_t size;
};

struct executable {
    struct blob file;
    uint32_t load_address;
    uint32_t text_size;
};

struct target_record {
    int32_t x, y, z, auxiliary;
};

static uint16_t read_le16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t read_le32(const uint8_t *p)
{
    return (uint32_t)read_le16(p) | ((uint32_t)read_le16(p + 2) << 16);
}

static int32_t read_le32s(const uint8_t *p)
{
    return (int32_t)read_le32(p);
}

static void fail(const char *message)
{
    fprintf(stderr, "phase4_c18_static: %s\n", message);
    exit(1);
}

static struct blob read_blob(const char *path)
{
    struct blob blob = {0};
    FILE *fp = fopen(path, "rb");
    long length;

    if (!fp || fseek(fp, 0, SEEK_END) != 0 || (length = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0)
        fail("cannot open input");
    blob.size = (size_t)length;
    blob.data = malloc(blob.size ? blob.size : 1);
    if (!blob.data || fread(blob.data, 1, blob.size, fp) != blob.size)
        fail("cannot read input");
    fclose(fp);
    return blob;
}

static struct executable read_executable(const char *path)
{
    struct executable exe = {0};

    exe.file = read_blob(path);
    if (exe.file.size < 0x800 || memcmp(exe.file.data, "PS-X EXE", 8) != 0)
        fail("input is not a PS-X EXE");
    exe.load_address = read_le32(exe.file.data + 0x18);
    exe.text_size = read_le32(exe.file.data + 0x1c);
    return exe;
}

static const uint8_t *pointer_at(const struct executable *exe,
                                 uint32_t address, size_t length)
{
    uint64_t delta;

    if (address < exe->load_address)
        fail("address precedes executable load address");
    delta = (uint64_t)address - exe->load_address;
    if (delta + length > exe->text_size ||
        0x800 + delta + length > exe->file.size)
        fail("address outside executable text");
    return exe->file.data + 0x800 + (size_t)delta;
}

static uint32_t instruction_at(const struct executable *exe, uint32_t address)
{
    return read_le32(pointer_at(exe, address, 4));
}

static uint32_t overlay_word(const struct blob *overlay, uint32_t address)
{
    uint64_t offset;

    if (address < OVERLAY_BASE)
        fail("overlay address precedes load base");
    offset = (uint64_t)address - OVERLAY_BASE;
    if (offset + 4 > overlay->size)
        fail("overlay address outside image");
    return read_le32(overlay->data + (size_t)offset);
}

static void sha256_hex(const uint8_t *data, size_t size, char out[65])
{
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    uint8_t digest[32];
    unsigned int digest_size = 0;
    size_t i;

    if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
        EVP_DigestUpdate(ctx, data, size) != 1 ||
        EVP_DigestFinal_ex(ctx, digest, &digest_size) != 1 ||
        digest_size != sizeof(digest))
        fail("SHA-256 failure");
    EVP_MD_CTX_free(ctx);
    for (i = 0; i < sizeof(digest); ++i)
        sprintf(out + i * 2, "%02x", digest[i]);
    out[64] = '\0';
}

static uint32_t jump_target(uint32_t pc, uint32_t instruction)
{
    return ((pc + 4) & 0xf0000000u) |
           ((instruction & 0x03ffffffu) << 2);
}

static void check_word(const struct executable *exe, uint32_t address,
                       uint32_t expected, const char *name,
                       unsigned *anchors)
{
    uint32_t actual = instruction_at(exe, address);
    if (actual != expected) {
        fprintf(stderr, "resident anchor mismatch at 0x%08" PRIx32
                        " (%s): 0x%08" PRIx32 " != 0x%08" PRIx32 "\n",
                address, name, actual, expected);
        exit(1);
    }
    ++*anchors;
}

static void check_overlay_word(const struct blob *overlay, uint32_t address,
                               uint32_t expected, const char *name,
                               unsigned *anchors)
{
    uint32_t actual = overlay_word(overlay, address);
    if (actual != expected) {
        fprintf(stderr, "overlay anchor mismatch at 0x%08" PRIx32
                        " (%s): 0x%08" PRIx32 " != 0x%08" PRIx32 "\n",
                address, name, actual, expected);
        exit(1);
    }
    ++*anchors;
}

static void check_call(const struct executable *exe, uint32_t pc,
                       uint32_t target, const char *name,
                       unsigned *anchors)
{
    uint32_t insn = instruction_at(exe, pc);
    if ((insn >> 26) != 3 || jump_target(pc, insn) != target) {
        fprintf(stderr, "resident call mismatch at 0x%08" PRIx32
                        " (%s)\n", pc, name);
        exit(1);
    }
    ++*anchors;
}

static uint32_t find_sequence(const struct executable *exe,
                              uint32_t begin, uint32_t end,
                              const uint32_t *sequence, size_t count)
{
    uint32_t pc;
    for (pc = begin; pc + count * 4 <= end; pc += 4) {
        size_t i;
        for (i = 0; i < count; ++i)
            if (instruction_at(exe, pc + (uint32_t)i * 4) != sequence[i])
                break;
        if (i == count)
            return pc;
    }
    return 0;
}

static unsigned count_immediate(const struct executable *exe,
                                uint32_t begin, uint32_t end,
                                uint16_t immediate)
{
    uint32_t pc;
    unsigned count = 0;
    for (pc = begin; pc < end; pc += 4)
        if ((uint16_t)instruction_at(exe, pc) == immediate)
            ++count;
    return count;
}

static unsigned count_slti_bound(const struct executable *exe,
                                 uint32_t begin, uint32_t end,
                                 uint16_t bound)
{
    uint32_t pc;
    unsigned count = 0;
    for (pc = begin; pc < end; pc += 4) {
        uint32_t insn = instruction_at(exe, pc);
        unsigned opcode = insn >> 26;
        if ((opcode == 0x0a || opcode == 0x0b) &&
            (uint16_t)insn == bound)
            ++count;
    }
    return count;
}

static unsigned count_resource_stores_blob(const uint8_t *data, size_t size)
{
    size_t offset;
    unsigned count = 0;
    for (offset = 0; offset + 4 <= size; offset += 4) {
        uint32_t insn = read_le32(data + offset);
        unsigned opcode = insn >> 26;
        uint16_t immediate = (uint16_t)insn;
        int store = opcode == 0x28 || opcode == 0x29 || opcode == 0x2b;
        if (store && (immediate == 0x6594 || immediate == 0x65a0 ||
                      immediate == 0x65a1))
            ++count;
    }
    return count;
}

static unsigned count_resource_stores_exe(const struct executable *exe,
                                          uint32_t begin, uint32_t end)
{
    uint32_t pc;
    unsigned count = 0;
    for (pc = begin; pc < end; pc += 4) {
        uint32_t insn = instruction_at(exe, pc);
        unsigned opcode = insn >> 26;
        uint16_t immediate = (uint16_t)insn;
        int store = opcode == 0x28 || opcode == 0x29 || opcode == 0x2b;
        if (store && (immediate == 0x6594 || immediate == 0x65a0 ||
                      immediate == 0x65a1))
            ++count;
    }
    return count;
}

static void check_all_orders(unsigned *orders_checked,
                             unsigned *aborts_checked)
{
    static const uint8_t bits[3] = {0x02, 0x01, 0x04};
    unsigned a, b, c;

    *orders_checked = 0;
    *aborts_checked = 0;
    for (a = 0; a < 3; ++a) {
        for (b = 0; b < 3; ++b) {
            uint8_t committed = 0;
            unsigned selector = 0;
            unsigned order[3];
            if (b == a)
                continue;
            c = 3 - a - b;
            order[0] = a;
            order[1] = b;
            order[2] = c;
            for (unsigned step = 0; step < 3; ++step) {
                uint8_t tentative = committed | bits[order[step]];
                uint8_t rollback = (uint8_t)((tentative >> 4) * 17);
                uint8_t success = (uint8_t)((tentative & 0x0f) * 17);
                unsigned movie_id = selector + 42;
                if (rollback != committed)
                    fail("abort rollback state model failed");
                if (movie_id != 42 + step)
                    fail("completion-order movie model failed");
                ++*aborts_checked;
                committed = success;
                ++selector;
            }
            if (committed != 0x77 || selector != 3)
                fail("challenge-order final-state model failed");
            ++*orders_checked;
        }
    }
    if (*orders_checked != 6 || *aborts_checked != 18)
        fail("challenge permutation census failed");
}

int main(int argc, char **argv)
{
    static const uint32_t commit_sequence[] = {
        0x3063000f, 0x00031100, 0x00431021, 0xa0e20000,
        0x3c01800a, 0xa026b88a, 0x0c00f9f0, 0x24840029
    };
    static const uint32_t rollback_sequence[] = {
        0x3c04800a, 0x2484b889, 0x90830000, 0x00000000,
        0x00031902, 0x00031100, 0x00431021
    };
    static const struct target_record expected_targets[3] = {
        {-13187, -70036, -22421, -70036},
        {-22349, -79705,  48945,  18380},
        {157232, -42406,   5891, -42406}
    };
    struct target_record targets[3];
    struct executable exe;
    struct blob overlay;
    char exe_sha[65], overlay_sha[65];
    uint32_t commit_pc, rollback_pc;
    unsigned anchors = 0;
    unsigned save_base_refs, save_loop_bounds;
    unsigned resource_stores;
    unsigned orders_checked, aborts_checked;
    unsigned i;

    if (argc != 3) {
        fprintf(stderr, "usage: %s SCUS_942.88 LEVEL06/LEVEL1.BIN\n",
                argv[0]);
        return 2;
    }
    exe = read_executable(argv[1]);
    overlay = read_blob(argv[2]);
    sha256_hex(exe.file.data, exe.file.size, exe_sha);
    sha256_hex(overlay.data, overlay.size, overlay_sha);
    if (strcmp(exe_sha, RETAIL_SHA256) != 0)
        fail("pristine executable hash mismatch");
    if (strcmp(overlay_sha, BONUS_OVERLAY_SHA256) != 0)
        fail("pristine LEVEL06/LEVEL1.BIN hash mismatch");

    /* Bonus 1: qualifying butt-slam interaction, no fixed challenge scene. */
    check_word(&exe, 0x8004b36c, 0x30820020,
               "Bonus 1 earned guard", &anchors);
    check_word(&exe, 0x8004b374, 0x24020010,
               "Bonus 1 scene-0x10 exclusion", &anchors);
    check_word(&exe, 0x8004b3a8, 0xaf8304a4,
               "Bonus 1 fifth-step counter", &anchors);
    check_word(&exe, 0x8004b3b4, 0xa0a20000,
               "Bonus 1 tentative bit", &anchors);
    check_word(&exe, 0x8004b3c0, 0xa42223a0,
               "Bonus 1 transition mode 6", &anchors);
    check_word(&exe, 0x8004b3cc, 0xa4222470,
               "Bonus 1 fade 30", &anchors);
    check_word(&exe, 0x8004b3d0, 0xaf8004a4,
               "Bonus 1 success reset", &anchors);

    /* Bonus 2: any qualifying mature type-5 mushroom, scene 0x10 excluded. */
    check_word(&exe, 0x8005c04c, 0x10620007,
               "Bonus 2 scene-0x10 exclusion", &anchors);
    check_word(&exe, 0x8005c060, 0x30420010,
               "Bonus 2 earned guard", &anchors);
    if ((instruction_at(&exe, 0x8005c54c) >> 26) != 0x28 ||
        (instruction_at(&exe, 0x8005c580) >> 26) != 0x28)
        fail("Bonus 2 duplicate-reset or distinct-append byte store changed");
    anchors += 2;
    check_word(&exe, 0x8005c6b8, 0xa42223a0,
               "Bonus 2 transition mode 6", &anchors);
    check_word(&exe, 0x8005c6cc, 0xa4222470,
               "Bonus 2 fade 60", &anchors);
    check_word(&exe, 0x8005c6dc, 0xac226530,
               "Bonus 2 completion launch", &anchors);
    check_word(&exe, 0x8005c6e4, 0xa0830000,
               "Bonus 2 tentative bit", &anchors);

    /* Bonus 3: blue class-0 actor-15 kills; selector/miss resets. */
    check_word(&exe, 0x80058b00, 0x90636597,
               "Bonus 3 blue selector", &anchors);
    check_word(&exe, 0x80058b34, 0xaf8004a8,
               "Bonus 3 wrong-selector reset", &anchors);
    check_word(&exe, 0x8005916c, 0x9222002c,
               "Bonus 3 damage class", &anchors);
    check_word(&exe, 0x8005917c, 0x8e430000,
               "Bonus 3 actor id", &anchors);
    check_word(&exe, 0x80059198, 0x30820040,
               "Bonus 3 earned guard", &anchors);
    check_word(&exe, 0x800591c0, 0xaf8304a8,
               "Bonus 3 fifth-step counter", &anchors);
    check_word(&exe, 0x800591d0, 0xa022b889,
               "Bonus 3 tentative bit", &anchors);
    check_word(&exe, 0x800591dc, 0xa42223a0,
               "Bonus 3 transition mode 6", &anchors);
    check_word(&exe, 0x800591e8, 0xa4222470,
               "Bonus 3 fade 30", &anchors);
    check_word(&exe, 0x800591ec, 0xaf8004a8,
               "Bonus 3 success reset", &anchors);
    check_word(&exe, 0x80059a0c, 0xaf8004a8,
               "Bonus 3 missed-shot reset", &anchors);

    /* Transition 6 sets the one-shot scene override to scene 0x10. */
    check_word(&exe, 0x80050224, 0x24020006,
               "bonus handoff mode compare", &anchors);
    check_word(&exe, 0x80050230, 0xaf8204c4,
               "bonus scene override arm", &anchors);
    check_word(&exe, 0x8004fde4, 0xac222504,
               "scene override writes scene 0x10", &anchors);

    /* Successful wrapper return commits low bits and advances ordinal. */
    commit_pc = find_sequence(&exe, 0x8004ff90, 0x8004ffe0,
                              commit_sequence,
                              sizeof(commit_sequence) /
                              sizeof(commit_sequence[0]));
    if (!commit_pc)
        fail("bonus successful-commit sequence not found");
    anchors += sizeof(commit_sequence) / sizeof(commit_sequence[0]);
    check_call(&exe, commit_pc + 24, 0x8003e7c0,
               "bonus reward movie dispatch", &anchors);
    rollback_pc = find_sequence(&exe, 0x8004ffe0, 0x80050000,
                                rollback_sequence,
                                sizeof(rollback_sequence) /
                                sizeof(rollback_sequence[0]));
    if (!rollback_pc || instruction_at(&exe, rollback_pc + 32) != 0xa0820000)
        fail("bonus non-success rollback sequence not found");
    anchors += sizeof(rollback_sequence) / sizeof(rollback_sequence[0]) + 1;

    /* Scene 0x10 shared LEVEL06/LEVEL1 overlay and its exact goal law. */
    check_overlay_word(&overlay, 0x800b3b38, 0x90a5b88a,
                       "bonus ordinal initialization", &anchors);
    check_overlay_word(&overlay, 0x800b3b54, 0x14a2000f,
                       "ordinal 2 setup branch", &anchors);
    check_overlay_word(&overlay, 0x800b3b94, 0x10a20022,
                       "ordinal 1 setup branch", &anchors);
    check_overlay_word(&overlay, 0x800b3c20, 0x10a20019,
                       "ordinal 2 alternate setup branch", &anchors);
    check_overlay_word(&overlay, 0x800b3c9c, 0x9084b88a,
                       "bonus target ordinal", &anchors);
    check_overlay_word(&overlay, 0x800b3cc4, 0x00042100,
                       "16-byte target stride", &anchors);
    check_overlay_word(&overlay, 0x800b3cd0, 0x8c314070,
                       "target X", &anchors);
    check_overlay_word(&overlay, 0x800b3cec, 0x8c324074,
                       "target Y", &anchors);
    check_overlay_word(&overlay, 0x800b3d10, 0x8c304078,
                       "target Z", &anchors);
    check_overlay_word(&overlay, 0x800b3d3c, 0x8c34407c,
                       "target auxiliary coordinate", &anchors);
    check_overlay_word(&overlay, 0x800b3eb8, 0x8c426500,
                       "player X", &anchors);
    check_overlay_word(&overlay, 0x800b3ed0, 0x8c426504,
                       "player Y", &anchors);
    check_overlay_word(&overlay, 0x800b3ee8, 0x8c426508,
                       "player Z", &anchors);
    check_overlay_word(&overlay, 0x800b3f08, 0x28420640,
                       "goal distance-squared threshold", &anchors);
    check_overlay_word(&overlay, 0x800b3f18, 0xa42223a0,
                       "goal transition mode 1", &anchors);
    check_overlay_word(&overlay, 0x800b3f24, 0xa4222470,
                       "goal fade 30", &anchors);

    for (i = 0; i < 3; ++i) {
        const uint8_t *p = overlay.data + (0x800b4070 - OVERLAY_BASE) + i * 16;
        targets[i].x = read_le32s(p);
        targets[i].y = read_le32s(p + 4);
        targets[i].z = read_le32s(p + 8);
        targets[i].auxiliary = read_le32s(p + 12);
        if (memcmp(&targets[i], &expected_targets[i], sizeof(targets[i])) != 0)
            fail("bonus target-coordinate table mismatch");
    }

    save_base_refs = count_immediate(&exe, 0x80055478, 0x800556a0, 0xb878);
    save_loop_bounds = count_slti_bound(&exe, 0x80055478, 0x800556a0, 19);
    if (save_base_refs < 2 || save_loop_bounds < 2)
        fail("19-byte save block persistence boundary mismatch");
    resource_stores = count_resource_stores_blob(overlay.data, overlay.size) +
                      count_resource_stores_exe(&exe, 0x8004ff90, 0x80050004);
    if (resource_stores != 0)
        fail("bonus goal/reward path unexpectedly writes health/lives/grain");

    check_all_orders(&orders_checked, &aborts_checked);

    printf("{\n");
    printf("  \"schema\": \"phase4_c18_static_v1\",\n");
    printf("  \"row\": \"C18_bonus_entry\",\n");
    printf("  \"identity\": {\"serial\": \"SCUS-94288\", "
           "\"pristine_exe_sha256\": \"%s\", "
           "\"bonus_overlay\": \"LEVEL06/LEVEL1.BIN\", "
           "\"bonus_overlay_sha256\": \"%s\", "
           "\"bonus_overlay_bytes\": %zu},\n",
           exe_sha, overlay_sha, overlay.size);
    printf("  \"anchors_checked\": %u,\n", anchors);
    printf("  \"triggers\": [\n");
    printf("    {\"condition\": \"five qualifying butt-slammable interactions\", "
           "\"tentative_bit\": \"0x02\", \"earned_guard\": \"0x20\", "
           "\"hardcoded_stage\": false, \"scene_0x10_excluded\": true},\n");
    printf("    {\"condition\": \"five distinct mature type-5 mushroom contacts; duplicate restarts chain\", "
           "\"tentative_bit\": \"0x01\", \"earned_guard\": \"0x10\", "
           "\"hardcoded_stage\": false, \"scene_0x10_excluded\": true},\n");
    printf("    {\"condition\": \"five blue class-0 lethal contacts against actor id 15; wrong selector or miss resets streak\", "
           "\"tentative_bit\": \"0x04\", \"earned_guard\": \"0x40\", "
           "\"hardcoded_stage\": false, \"scene_0x10_excluded\": false}\n");
    printf("  ],\n");
    printf("  \"entry_handoff\": {\"transition_mode\": 6, "
           "\"scene_override\": \"0x10\", "
           "\"tentative_flags_address\": \"0x8009b889\"},\n");
    printf("  \"bonus_stage\": {\n");
    printf("    \"selector_address\": \"0x8009b88a\",\n");
    printf("    \"selector_role\": \"successful-bonus completion ordinal and scene-0x10 variant index\",\n");
    printf("    \"targets\": [\n");
    for (i = 0; i < 3; ++i)
        printf("      {\"ordinal\": %u, \"x\": %" PRId32
               ", \"y\": %" PRId32 ", \"z\": %" PRId32
               ", \"auxiliary\": %" PRId32 "}%s\n",
               i, targets[i].x, targets[i].y, targets[i].z,
               targets[i].auxiliary, i == 2 ? "" : ",");
    printf("    ],\n");
    printf("    \"coordinate_scale_shift\": 8, "
           "\"goal_distance_squared_lt\": 1600, "
           "\"success_transition_mode\": 1, \"success_fade\": 30\n");
    printf("  },\n");
    printf("  \"transaction\": {\"success\": "
           "\"flags=(flags&0x0f)*17; selector++; movie_id=old_selector+42\", "
           "\"non_success\": \"flags=(flags>>4)*17; selector unchanged; no movie\", "
           "\"commit_sequence_pc\": \"0x%08" PRIx32 "\", "
           "\"rollback_sequence_pc\": \"0x%08" PRIx32 "\"},\n",
           commit_pc, rollback_pc);
    printf("  \"order_exhaustion\": {\"challenge_orders_checked\": %u, "
           "\"abort_points_checked\": %u, "
           "\"movie_ids_by_completion_ordinal\": [42,43,44], "
           "\"final_flags_all_orders\": \"0x77\", "
           "\"final_selector_all_orders\": 3},\n",
           orders_checked, aborts_checked);
    printf("  \"reward\": {\"movie_unlock_committed_in_high_nibble\": true, "
           "\"health_lives_grain_store_count\": %u, "
           "\"resource_reward\": false},\n", resource_stores);
    printf("  \"persistence\": {\"save_block_base\": \"0x8009b878\", "
           "\"save_block_bytes\": 19, \"bonus_flags_offset\": 17, "
           "\"bonus_selector_offset\": 18, \"serializer_deserializer_base_refs\": %u, "
           "\"serializer_deserializer_loop_bounds\": %u},\n",
           save_base_refs, save_loop_bounds);
    printf("  \"result\": \"C18_RESIDENT_OVERLAY_STATIC_PASS\"\n");
    printf("}\n");

    free(overlay.data);
    free(exe.file.data);
    return 0;
}
