/*
 * Phase 4 C11 Seed Tokens resident-mechanics and authored-data gate.
 *
 * Build and run:
 *   cc -O2 -Wall -Wextra -o /tmp/phase4_c11_static \
 *      tools/phase4_c11_static.c -lcrypto
 *   /tmp/phase4_c11_static SCUS_942.88 REBUILD/files \
 *      > analysis/phase4_c11_seed_tokens.json
 */
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RETAIL_SHA256 \
    "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"

struct blob {
    uint8_t *data;
    size_t size;
};

struct executable {
    struct blob file;
    uint32_t load_address;
    uint32_t text_size;
};

struct token_kind {
    uint8_t kind;
    const char *color;
    uint32_t entry;
    uint32_t store_pc;
    uint16_t lane;
    uint8_t object_id;
    uint32_t store_word;
};

struct level_expectation {
    const char *directory;
    unsigned counts[5];
};

struct level_result {
    int has_table;
    size_t table_offset;
    uint16_t entry_count;
    unsigned counts[5];
    char sha256[65];
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
    fprintf(stderr, "phase4_c11_static: %s\n", message);
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
        fail("address is outside executable text");
    return exe->file.data + 0x800 + (size_t)delta;
}

static uint32_t instruction_at(const struct executable *exe, uint32_t address)
{
    return read_le32(pointer_at(exe, address, 4));
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

static int is_call_to(const struct executable *exe, uint32_t pc,
                      uint32_t target)
{
    uint32_t instruction = instruction_at(exe, pc);
    return (instruction >> 26) == 3 && jump_target(pc, instruction) == target;
}

static void check_word(const struct executable *exe, uint32_t address,
                       uint32_t expected, const char *name,
                       unsigned *anchors)
{
    uint32_t actual = instruction_at(exe, address);

    if (actual != expected) {
        fprintf(stderr, "anchor mismatch at 0x%08" PRIx32 " (%s): "
                        "0x%08" PRIx32 " != 0x%08" PRIx32 "\n",
                address, name, actual, expected);
        exit(1);
    }
    ++*anchors;
}

static void check_call(const struct executable *exe, uint32_t pc,
                       uint32_t target, const char *name,
                       unsigned *anchors)
{
    if (!is_call_to(exe, pc, target)) {
        fprintf(stderr, "call mismatch at 0x%08" PRIx32 " (%s)\n",
                pc, name);
        exit(1);
    }
    ++*anchors;
}

static int window_has_word(const struct executable *exe, uint32_t begin,
                           uint32_t end, uint32_t expected)
{
    uint32_t pc;
    for (pc = begin; pc < end; pc += 4)
        if (instruction_at(exe, pc) == expected)
            return 1;
    return 0;
}

static int window_has_call(const struct executable *exe, uint32_t begin,
                           uint32_t end, uint32_t target)
{
    uint32_t pc;
    for (pc = begin; pc < end; pc += 4)
        if (is_call_to(exe, pc, target))
            return 1;
    return 0;
}

static void check_pack_window(const struct executable *exe, uint32_t begin,
                              uint32_t end)
{
    uint32_t pc;
    int saw_mask = 0, saw_shift = 0, saw_add = 0;

    for (pc = begin; pc <= end; pc += 4) {
        uint32_t insn = instruction_at(exe, pc);
        unsigned opcode = insn >> 26;
        unsigned funct = insn & 0x3f;
        unsigned shift = (insn >> 6) & 0x1f;
        if (opcode == 0x0c && (insn & 0xffff) == 7)
            saw_mask = 1;
        if (opcode == 0 && funct == 0 && shift == 4)
            saw_shift = 1;
        if (opcode == 0 && funct == 0x21)
            saw_add = 1;
    }
    if (!saw_mask || !saw_shift || !saw_add)
        fail("token handler no longer implements ((old+1)&7)*17");
}

static unsigned count_word_range(const struct executable *exe,
                                 uint32_t begin, uint32_t end,
                                 uint32_t word)
{
    uint32_t pc;
    unsigned count = 0;
    for (pc = begin; pc < end; pc += 4)
        if (instruction_at(exe, pc) == word)
            ++count;
    return count;
}

static unsigned count_lane_immediates(const struct executable *exe,
                                      uint32_t begin, uint32_t end)
{
    uint32_t pc;
    unsigned count = 0;
    for (pc = begin; pc < end; pc += 4) {
        uint32_t insn = instruction_at(exe, pc);
        uint16_t imm = (uint16_t)insn;
        if (imm >= 0x6598 && imm <= 0x659c)
            ++count;
    }
    return count;
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

static void count_target_references(const struct executable *exe,
                                    uint32_t target,
                                    unsigned *calls, unsigned *literals)
{
    uint32_t pc;
    *calls = 0;
    *literals = 0;
    for (pc = exe->load_address;
         pc + 4 <= exe->load_address + exe->text_size; pc += 4) {
        uint32_t word = instruction_at(exe, pc);
        if (((word >> 26) == 2 || (word >> 26) == 3) &&
            jump_target(pc, word) == target)
            ++*calls;
        if (word == target)
            ++*literals;
    }
}

static int valid_source3f_table(const uint8_t *data, size_t size,
                                size_t offset, uint16_t *entry_count,
                                unsigned counts[5])
{
    const uint8_t *entry;
    unsigned i;

    if (offset + 8 > size || read_le16(data + offset + 2) != 0x003f)
        return 0;
    *entry_count = read_le16(data + offset);
    if (!*entry_count || *entry_count > 4096 ||
        offset + 4u + (size_t)*entry_count * 16u > size)
        return 0;
    memset(counts, 0, 5 * sizeof(*counts));
    entry = data + offset + 4;
    for (i = 0; i < *entry_count; ++i, entry += 16) {
        int32_t x = read_le32s(entry);
        int32_t y = read_le32s(entry + 4);
        int32_t z = read_le32s(entry + 8);
        uint8_t kind = entry[12];
        int known_kind = (kind >= 0x10 && kind <= 0x14) ||
                         (kind >= 0x20 && kind <= 0x24) ||
                         (kind >= 0x29 && kind <= 0x31);
        if (!known_kind || entry[13] > 1 ||
            x < -10000000 || x > 10000000 ||
            y < -10000000 || y > 10000000 ||
            z < -10000000 || z > 10000000)
            return 0;
        if (kind >= 0x29 && kind <= 0x2d)
            ++counts[kind - 0x29];
    }
    return 1;
}

static struct level_result inspect_level(const char *root,
                                         const struct level_expectation *expect)
{
    struct level_result result = {0};
    struct blob dat;
    char path[1024];
    size_t offset;
    unsigned hits = 0;

    if (snprintf(path, sizeof(path), "%s/%s/LEVEL.DAT", root,
                 expect->directory) >= (int)sizeof(path))
        fail("LEVEL.DAT path is too long");
    dat = read_blob(path);
    sha256_hex(dat.data, dat.size, result.sha256);
    for (offset = 0; offset + 8 <= dat.size; offset += 2) {
        uint16_t entries;
        unsigned counts[5];
        if (!valid_source3f_table(dat.data, dat.size, offset,
                                  &entries, counts))
            continue;
        ++hits;
        result.has_table = 1;
        result.table_offset = offset;
        result.entry_count = entries;
        memcpy(result.counts, counts, sizeof(result.counts));
    }
    free(dat.data);
    if (hits > 1)
        fail("multiple plausible source-0x3f tables in one LEVEL.DAT");
    if (memcmp(result.counts, expect->counts, sizeof(result.counts)) != 0)
        fail("authored seed-token census mismatch");
    if (!strcmp(expect->directory, "LEVEL00") && hits != 0)
        fail("training unexpectedly gained a source-0x3f table");
    if (strcmp(expect->directory, "LEVEL00") && hits != 1)
        fail("campaign LEVEL.DAT lost its source-0x3f table");
    return result;
}

int main(int argc, char **argv)
{
    static const struct token_kind tokens[] = {
        {0x29, "brown_orange", 0x800542f4, 0x8005431c, 0x6598, 0x16,
         0xa2020000},
        {0x2a, "blue",         0x8005433c, 0x80054364, 0x6599, 0x17,
         0xa0236599},
        {0x2b, "green",        0x800543b8, 0x800543e0, 0x659a, 0x19,
         0xa023659a},
        {0x2c, "purple",       0x80054434, 0x8005445c, 0x659b, 0x18,
         0xa023659b},
        {0x2d, "yellow",       0x800544d0, 0x800544f8, 0x659c, 0x2f,
         0xa023659c}
    };
    static const struct level_expectation levels[] = {
        {"LEVEL00", {0,0,0,0,0}},
        {"LEVEL01", {3,3,3,0,0}},
        {"LEVEL02", {0,0,0,4,0}},
        {"LEVEL03", {0,0,2,4,0}},
        {"LEVEL04", {0,1,4,4,2}},
        {"LEVEL05", {1,4,2,4,0}},
        {"LEVEL06", {2,0,2,0,0}},
        {"LEVEL07", {3,3,2,2,0}},
        {"LEVEL08", {0,0,0,0,0}},
        {"LEVEL09", {1,4,4,0,3}},
        {"LEVEL10", {1,3,4,0,0}}
    };
    static const unsigned campaign_directory[15] = {
        1,3,2,6,10,1,4,5,4,7,2,3,9,8,5
    };
    static const uint8_t nonbrown_object_ids[4] = {0x17,0x19,0x18,0x2f};
    struct level_result level_results[11];
    struct executable exe;
    char exe_sha[65];
    unsigned totals[5] = {0};
    unsigned anchors = 0;
    unsigned helper_calls, helper_literals;
    unsigned serializer_lane_refs, serializer_unlock_refs;
    unsigned registry_reset_stores;
    unsigned i, j;

    if (argc != 3) {
        fprintf(stderr, "usage: %s SCUS_942.88 REBUILD/files\n", argv[0]);
        return 2;
    }
    exe = read_executable(argv[1]);
    sha256_hex(exe.file.data, exe.file.size, exe_sha);
    if (strcmp(exe_sha, RETAIL_SHA256) != 0)
        fail("pristine executable hash mismatch");

    for (i = 0; i < sizeof(tokens) / sizeof(tokens[0]); ++i) {
        uint32_t table_entry = 0x8001b42c + (tokens[i].kind - 0x10) * 4;
        uint32_t actual_target = read_le32(pointer_at(&exe, table_entry, 4));
        if (actual_target != tokens[i].entry)
            fail("seed-token jump-table binding mismatch");
        ++anchors;
        check_word(&exe, tokens[i].store_pc, tokens[i].store_word,
                   "packed lane store", &anchors);
        check_pack_window(&exe, tokens[i].entry, tokens[i].store_pc);
        if (!window_has_call(&exe, tokens[i].entry,
                             i + 1 < sizeof(tokens) / sizeof(tokens[0])
                                 ? tokens[i + 1].entry : 0x80054544,
                             0x8003e760))
            fail("token handler lost plant-output reskin call");
    }
    if (memcmp(pointer_at(&exe, 0x80078e90, sizeof(nonbrown_object_ids)),
               nonbrown_object_ids, sizeof(nonbrown_object_ids)) != 0)
        fail("non-brown output-object table mismatch");
    ++anchors;
    check_word(&exe, 0x80054324, 0x24040016,
               "brown output object id", &anchors);

    check_word(&exe, 0x80053c5c, 0x2a0209c4,
               "contact squared-distance threshold", &anchors);
    check_call(&exe, 0x80053cc4, 0x80057620,
               "pickup contact burst", &anchors);
    check_word(&exe, 0x80053ccc, 0x3c028000,
               "retirement sentinel high word", &anchors);
    check_word(&exe, 0x80053cd0, 0xae420000,
               "runtime source Y retirement", &anchors);
    check_call(&exe, 0x80054318, 0x80050994,
               "brown feedback dispatch", &anchors);
    check_call(&exe, 0x80054544, 0x80050994,
               "non-brown feedback dispatch", &anchors);
    check_call(&exe, 0x800545f0, 0x8005044c,
               "common coordinate feedback dispatch", &anchors);
    check_word(&exe, 0x800544c4, 0xa4220196,
               "non-brown registry append", &anchors);

    check_word(&exe, 0x8005b9a8, 0x3c10800a,
               "gameplay-state base high word", &anchors);
    check_word(&exe, 0x8005b9ac, 0x26106500,
               "gameplay-state base low word", &anchors);
    check_word(&exe, 0x8005b9b0, 0x02002021,
               "gameplay-state base call argument", &anchors);
    check_call(&exe, 0x8005baa4, 0x80046b20,
               "level-load player-state writer", &anchors);
    check_word(&exe, 0x80046b28, 0x00809821,
               "writer preserves gameplay-state base", &anchors);
    check_call(&exe, 0x80046b68, 0x8005f7ac,
               "168-byte gameplay-state clear", &anchors);
    check_word(&exe, 0x80046b6c, 0x240600a8,
               "gameplay-state clear length", &anchors);
    check_word(&exe, 0x80046bec, 0xa2620098,
               "brown tier one at gameplay-state plus 0x98", &anchors);
    registry_reset_stores = count_word_range(&exe, 0x8005b714,
                                              0x8005c000, 0xa4200196);
    if (registry_reset_stores != 1)
        fail("non-brown registry reset-store census mismatch");

    check_word(&exe, 0x80052fa4, 0x3c01800a,
               "HUD lane base", &anchors);
    check_word(&exe, 0x80052fa8, 0x00360821,
               "HUD selected color-lane index", &anchors);
    check_word(&exe, 0x80052fac, 0x90226598,
               "HUD packed lane read", &anchors);
    check_word(&exe, 0x8005310c, 0x33d6000f,
               "HUD next registry nibble", &anchors);

    serializer_lane_refs =
        count_lane_immediates(&exe, 0x80055478, 0x800556a0);
    serializer_unlock_refs =
        count_immediate(&exe, 0x80055478, 0x800556a0, 0xb878);
    if (serializer_lane_refs != 0 || serializer_unlock_refs < 2)
        fail("memory-card serialization boundary mismatch");

    count_target_references(&exe, 0x80053754,
                            &helper_calls, &helper_literals);
    if (helper_calls != 0 || helper_literals != 0)
        fail("latent generic upgrade helper gained a resident owner");

    for (i = 0; i < 256; ++i) {
        unsigned tier = (i + 1) & 7;
        unsigned packed = (tier << 4) + tier;
        if ((packed >> 4) != tier || (packed & 0xf) != tier)
            fail("packed-tier exhaustive state check failed");
    }

    for (i = 0; i < sizeof(levels) / sizeof(levels[0]); ++i) {
        level_results[i] = inspect_level(argv[2], &levels[i]);
        for (j = 0; j < 5; ++j)
            totals[j] += level_results[i].counts[j];
        if (1 + level_results[i].counts[0] > 4)
            fail("authored brown tier exceeds natural domain");
        for (j = 1; j < 5; ++j)
            if (level_results[i].counts[j] > 4)
                fail("authored non-brown tier exceeds natural domain");
    }
    if (totals[0] != 11 || totals[1] != 18 || totals[2] != 23 ||
        totals[3] != 18 || totals[4] != 5)
        fail("whole-game token totals mismatch");

    printf("{\n");
    printf("  \"schema\": \"phase4_c11_static_v2\",\n");
    printf("  \"row\": \"C11_seed_tokens\",\n");
    printf("  \"identity\": {\"serial\": \"SCUS-94288\", "
           "\"pristine_exe_sha256\": \"%s\"},\n", exe_sha);
    printf("  \"anchors_checked\": %u,\n", anchors);
    printf("  \"handler_binding\": [\n");
    for (i = 0; i < sizeof(tokens) / sizeof(tokens[0]); ++i) {
        printf("    {\"kind\": \"0x%02x\", \"color\": \"%s\", "
               "\"entry\": \"0x%08" PRIx32 "\", "
               "\"store_pc\": \"0x%08" PRIx32 "\", "
               "\"packed_lane\": \"0x800a%04x\", "
               "\"output_object_id\": \"0x%02x\"}%s\n",
               tokens[i].kind, tokens[i].color, tokens[i].entry,
               tokens[i].store_pc, tokens[i].lane, tokens[i].object_id,
               i + 1 == sizeof(tokens) / sizeof(tokens[0]) ? "" : ",");
    }
    printf("  ],\n");
    printf("  \"pickup_transaction\": {\"distance_squared_lt\": 2500, "
           "\"source_retirement_field\": \"runtime_y\", "
           "\"source_retirement_sentinel\": \"0x80000000\", "
           "\"tier_update\": \"n=(old+1)&7; packed=(n<<4)|n\", "
           "\"one_shot_until_source_reload\": true},\n");
    printf("  \"feedback\": {\"handler_event\": -3, "
           "\"handler_dispatch\": \"0x80050994\", "
           "\"coordinate_dispatch\": \"0x8005044c\", "
           "\"exact_gpu_spu_presentation_closed\": false},\n");
    printf("  \"registry\": {\"address\": \"0x800b0196\", "
           "\"contents\": \"ordered first-unlock non-brown lane indices\", "
           "\"values\": {\"blue\":1,\"green\":2,\"purple\":3,\"yellow\":4}, "
           "\"append_only_on_tier_one\": true, "
           "\"reset_store_count\": %u},\n", registry_reset_stores);
    printf("  \"hud\": {\"first_lane\": 0, "
           "\"subsequent_lanes_from_registry_nibbles\": true, "
           "\"displayed_tier_source\": \"packed_lane_high_nibble\"},\n");
    printf("  \"lifecycle\": {\"level_load_clear_base\": \"0x800a6500\", "
           "\"level_load_clear_bytes\": 168, "
           "\"level_load_initial_brown\": \"0x11\", "
           "\"ordinary_respawn_packed_lanes_preserved\": true, "
           "\"memory_card_serializes_packed_lanes\": false, "
           "\"serializer_unlock_array\": \"0x8009b878\", "
           "\"serializer_unlock_base_refs\": %u},\n",
           serializer_unlock_refs);
    printf("  \"authored_availability\": {\n");
    printf("    \"levels\": [\n");
    for (i = 0; i < sizeof(levels) / sizeof(levels[0]); ++i) {
        printf("      {\"directory\": \"%s\", \"source3f_table\": %s, "
               "\"table_offset\": ", levels[i].directory,
               level_results[i].has_table ? "true" : "false");
        if (level_results[i].has_table)
            printf("\"0x%zx\"", level_results[i].table_offset);
        else
            printf("null");
        printf(", \"entries\": %u, \"brown\": %u, \"blue\": %u, "
               "\"green\": %u, \"purple\": %u, \"yellow\": %u, "
               "\"sha256\": \"%s\"}%s\n",
               level_results[i].entry_count,
               level_results[i].counts[0], level_results[i].counts[1],
               level_results[i].counts[2], level_results[i].counts[3],
               level_results[i].counts[4], level_results[i].sha256,
               i + 1 == sizeof(levels) / sizeof(levels[0]) ? "" : ",");
    }
    printf("    ],\n");
    printf("    \"campaign_stage_directory_map\": [\n");
    for (i = 0; i < 15; ++i) {
        unsigned d = campaign_directory[i];
        printf("      {\"stage\": %u, \"directory\": \"LEVEL%02u\", "
               "\"brown\": %u, \"blue\": %u, \"green\": %u, "
               "\"purple\": %u, \"yellow\": %u}%s\n",
               i + 1, d, level_results[d].counts[0],
               level_results[d].counts[1], level_results[d].counts[2],
               level_results[d].counts[3], level_results[d].counts[4],
               i == 14 ? "" : ",");
    }
    printf("    ],\n");
    printf("    \"unique_directory_totals\": {\"brown\": %u, "
           "\"blue\": %u, \"green\": %u, \"purple\": %u, "
           "\"yellow\": %u, \"all\": %u},\n",
           totals[0], totals[1], totals[2], totals[3], totals[4],
           totals[0] + totals[1] + totals[2] + totals[3] + totals[4]);
    printf("    \"retail_authored_max_tier\": 4, "
           "\"modulo_wrap_reachable_in_retail\": false\n");
    printf("  },\n");
    printf("  \"latent_helper_0x80053754\": {\"direct_jump_or_call_refs\": %u, "
           "\"literal_pointer_refs\": %u, "
           "\"classification\": \"unowned_generic_upgrade_helper_not_x_cycle\"},\n",
           helper_calls, helper_literals);
    printf("  \"exhaustive_math_states_checked\": 256,\n");
    printf("  \"result\": \"C11_RESIDENT_AND_AUTHORED_STATIC_PASS\"\n");
    printf("}\n");

    free(exe.file.data);
    return 0;
}
