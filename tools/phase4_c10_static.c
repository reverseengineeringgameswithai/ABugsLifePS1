/*
 * Phase 4 C10 Gold Berry resident-mechanics static gate.
 *
 * Build and run:
 *   cc -O2 -Wall -Wextra -o /tmp/phase4_c10_static \
 *      tools/phase4_c10_static.c -lcrypto
 *   /tmp/phase4_c10_static SCUS_942.88
 */
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RETAIL_SHA256 \
    "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"

struct executable {
    uint8_t *data;
    size_t size;
    uint32_t load_address;
    uint32_t text_size;
};

struct anchor {
    uint32_t address;
    uint32_t instruction;
    const char *name;
};

static uint16_t read_le16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t read_le32(const uint8_t *p)
{
    return (uint32_t)read_le16(p) | ((uint32_t)read_le16(p + 2) << 16);
}

static void fail(const char *message)
{
    fprintf(stderr, "phase4_c10_static: %s\n", message);
    exit(1);
}

static struct executable read_executable(const char *path)
{
    struct executable exe = {0};
    FILE *fp = fopen(path, "rb");
    long length;

    if (!fp || fseek(fp, 0, SEEK_END) != 0 || (length = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0)
        fail("cannot open executable");
    exe.size = (size_t)length;
    exe.data = malloc(exe.size ? exe.size : 1);
    if (!exe.data || fread(exe.data, 1, exe.size, fp) != exe.size)
        fail("cannot read executable");
    fclose(fp);
    if (exe.size < 0x800 || memcmp(exe.data, "PS-X EXE", 8) != 0)
        fail("input is not a PS-X EXE");
    exe.load_address = read_le32(exe.data + 0x18);
    exe.text_size = read_le32(exe.data + 0x1c);
    return exe;
}

static const uint8_t *pointer_at(const struct executable *exe,
                                 uint32_t address, size_t length)
{
    uint64_t delta;

    if (address < exe->load_address)
        fail("address precedes executable load address");
    delta = (uint64_t)address - exe->load_address;
    if (delta + length > exe->text_size || 0x800 + delta + length > exe->size)
        fail("address is outside executable text");
    return exe->data + 0x800 + (size_t)delta;
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
        EVP_DigestFinal_ex(ctx, digest, &digest_size) != 1 || digest_size != 32)
        fail("SHA-256 failure");
    EVP_MD_CTX_free(ctx);
    for (i = 0; i < 32; ++i)
        sprintf(out + i * 2, "%02x", digest[i]);
    out[64] = '\0';
}

static uint32_t jump_target(uint32_t pc, uint32_t instruction)
{
    return ((pc + 4) & 0xf0000000u) |
           ((instruction & 0x03ffffffu) << 2);
}

static void check_calls(const struct executable *exe, uint32_t begin,
                        uint32_t end, const uint32_t *expected,
                        size_t expected_count)
{
    uint32_t pc;
    size_t found = 0;

    for (pc = begin; pc < end; pc += 4) {
        uint32_t instruction = instruction_at(exe, pc);
        if ((instruction >> 26) != 3)
            continue;
        if (found >= expected_count ||
            jump_target(pc, instruction) != expected[found])
            fail("unexpected call in Gold cleanup block");
        ++found;
    }
    if (found != expected_count)
        fail("missing call in Gold cleanup block");
}

int main(int argc, char **argv)
{
    static const struct anchor anchors[] = {
        {0x800471c4, 0x2411000b, "equip 3 selects type 11"},
        {0x80047228, 0xafb1001c, "constructor type argument"},
        {0x8004724c, 0x0c016838, "straight spawn call"},
        {0x80058e88, 0x080163a9, "subtype 4 collision rewrite"},
        {0x80058e8c, 0x2402000b, "rewrite marker 11"},
        {0x80058ea8, 0x240a0001, "impact timer one"},
        {0x80058eac, 0xa62a001a, "impact timer store"},
        {0x80058ee4, 0x30420040, "berry-tough bit"},
        {0x80058ef0, 0x86220024, "reaction class read"},
        {0x80059074, 0x9223002c, "damage selector read"},
        {0x800590d4, 0x2482fffc, "exact minus four"},
        {0x800591f0, 0x86230024, "permanence marker read"},
        {0x800591f4, 0x2402000b, "Gold marker constant"},
        {0x800591f8, 0x10620005, "Gold marker compare"},
        {0x80059200, 0x92230027, "secondary permanence read"},
        {0x80059210, 0x36f70002, "permanent outcome bit"},
        {0x80059218, 0x36f70001, "temporary outcome bit"},
        {0x800592a8, 0xa642006e, "lethal sentinel store"},
        {0x800592cc, 0x2ae20002, "permanent threshold"},
        {0x800592f4, 0x94620000, "quota load"},
        {0x800592fc, 0x2442ffff, "quota decrement"},
        {0x80059300, 0xa4620000, "quota store"},
        {0x80046c2c, 0x8c22fd80, "actor id read"},
        {0x80046c4c, 0x304208a0, "quota exclusion mask"},
        {0x80046c58, 0x9662008e, "quota load"},
        {0x80046c60, 0x24420001, "quota increment"},
        {0x80046c64, 0xa662008e, "quota store"},
        {0x80046c6c, 0x29220040, "64 actor slots"},
        {0x800596a8, 0x24636596, "subtype 4 owned count"},
        {0x800596b4, 0x2442ffff, "subtype 4 decrement"},
        {0x800596b8, 0xa0620000, "subtype 4 store"},
        {0x800596d4, 0x0c016791, "subtype 4 burst"},
        {0x800596dc, 0x2a020010, "subtype 4 burst count"},
        {0x80059920, 0x24636596, "subtype 11 owned count"},
        {0x8005992c, 0x2442ffff, "subtype 11 decrement"},
        {0x80059930, 0xa0620000, "subtype 11 store"},
        {0x8005994c, 0x0c016791, "subtype 11 burst"},
        {0x80059954, 0x2a020010, "subtype 11 burst count"},
        {0x8005a268, 0x90a20011, "row selector load"},
        {0x8005a270, 0xa2020034, "record selector store"},
        {0x8005a2a4, 0x94a2000c, "row subtype load"},
        {0x8005a2ac, 0xa602002c, "record subtype store"},
        {0x8005a2b0, 0x90a2000f, "row secondary load"},
        {0x8005a2b8, 0xa202002f, "record secondary store"}
    };
    static const uint8_t gold_row_expected[0x14] = {
        0x02,0x00,0x64,0x00,0x6e,0x00,0x00,0x01,0x32,0x00,
        0x32,0x00,0x04,0x00,0x00,0x01,0xe5,0x7f,0x60,0x00
    };
    static const uint8_t burst_12_expected[0x14] = {
        0x03,0x00,0x24,0x00,0xfc,0xff,0x00,0x06,0xc8,0x00,
        0xc8,0x00,0x00,0x00,0x02,0x00,0x40,0x00,0x18,0x60
    };
    static const uint8_t burst_13_expected[0x14] = {
        0x03,0x00,0x1e,0x00,0xfd,0xff,0x00,0x06,0xc8,0x00,
        0xc8,0x00,0x00,0x00,0x02,0x00,0x20,0x40,0x3a,0x00
    };
    static const uint32_t initial_calls[] = {
        0x80059e44, 0x80051358, 0x8005044c
    };
    static const uint32_t impact_calls[] = {0x80059e44, 0x80051358};
    const uint32_t metadata = 0x8007941c;
    const uint32_t rewrite_table = 0x8001b748;
    const uint32_t cleanup_table = 0x8001b790;
    const uint8_t *gold_row;
    const uint8_t *burst_12;
    const uint8_t *burst_13;
    struct executable exe;
    char sha[65];
    size_t i;

    if (argc != 2) {
        fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]);
        return 2;
    }
    exe = read_executable(argv[1]);
    sha256_hex(exe.data, exe.size, sha);
    if (strcmp(sha, RETAIL_SHA256) != 0)
        fail("pristine executable hash mismatch");
    for (i = 0; i < sizeof(anchors) / sizeof(anchors[0]); ++i) {
        uint32_t actual = instruction_at(&exe, anchors[i].address);
        if (actual != anchors[i].instruction) {
            fprintf(stderr, "anchor mismatch at 0x%08" PRIx32 " (%s): "
                            "0x%08" PRIx32 " != 0x%08" PRIx32 "\n",
                    anchors[i].address, anchors[i].name, actual,
                    anchors[i].instruction);
            return 1;
        }
    }
    gold_row = pointer_at(&exe, metadata + 11 * 0x14, 0x14);
    burst_12 = pointer_at(&exe, metadata + 12 * 0x14, 0x14);
    burst_13 = pointer_at(&exe, metadata + 13 * 0x14, 0x14);
    if (memcmp(gold_row, gold_row_expected, 0x14) != 0 ||
        memcmp(burst_12, burst_12_expected, 0x14) != 0 ||
        memcmp(burst_13, burst_13_expected, 0x14) != 0)
        fail("Gold or burst metadata row mismatch");
    if (read_le32(pointer_at(&exe, rewrite_table + 2 * 4, 4)) != 0x80058e88 ||
        read_le32(pointer_at(&exe, cleanup_table + 3 * 4, 4)) != 0x800596a0 ||
        read_le32(pointer_at(&exe, cleanup_table + 10 * 4, 4)) != 0x80059918)
        fail("Gold dispatch binding mismatch");
    check_calls(&exe, 0x800596a0, 0x8005972c, initial_calls,
                sizeof(initial_calls) / sizeof(initial_calls[0]));
    check_calls(&exe, 0x80059918, 0x80059984, impact_calls,
                sizeof(impact_calls) / sizeof(impact_calls[0]));
    if ((burst_12[0x10] & 0x80) || (burst_13[0x10] & 0x80) ||
        read_le16(burst_12) != 3 || read_le16(burst_13) != 3)
        fail("burst records unexpectedly enter projectile action lane");

    printf("{\n");
    printf("  \"schema\": \"phase4_c10_static_v1\",\n");
    printf("  \"row\": \"C10_gold_berry\",\n");
    printf("  \"pristine_exe_sha256\": \"%s\",\n", sha);
    printf("  \"anchors_checked\": %zu,\n", sizeof(anchors) / sizeof(anchors[0]));
    printf("  \"dispatch\": {\"equip_index\": 3, \"type\": 11, \"action_id\": 2, \"timer\": 100, \"initial_subtype\": 4, \"trajectory\": \"shared lead-adjusted straight ballistic\"},\n");
    printf("  \"collision\": {\"initial_subtype\": 4, \"impact_subtype\": 11, \"impact_timer\": 1, \"damage_selector\": 127, \"damage_delta\": -4, \"scope\": \"single contacted actor\"},\n");
    printf("  \"permanence\": {\"gate\": \"lethal and impact subtype 11\", \"nonlethal_quota_write\": false, \"lethal_sentinel\": 999, \"quota\": \"0x800a658e\", \"quota_delta\": -1, \"zero_result\": \"all-defeated event\"},\n");
    printf("  \"eligibility\": {\"load_slots\": 64, \"empty_id_excluded\": true, \"load_state_exclusion_mask\": 2208, \"contact_state_exclusion_mask\": 160, \"berry_tough_bit_64_excluded\": false},\n");
    printf("  \"cleanup\": {\"timeout_subtype\": 4, \"impact_subtype\": 11, \"owned_counter\": \"0x800a6596\", \"decrement_each_terminal_lane\": 1, \"burst_records\": 16, \"burst_ctor_types\": [12,13], \"burst_action_id\": 3, \"burst_projectile_bit_128\": false, \"radial_damage\": false},\n");
    printf("  \"result\": \"C10_RESIDENT_STATIC_PASS\"\n");
    printf("}\n");
    free(exe.data);
    return 0;
}
