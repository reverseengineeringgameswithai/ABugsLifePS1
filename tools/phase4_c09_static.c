/*
 * Phase 4 C09 Purple/Mega Homing Berry differential static gate.
 *
 * Reads only the hash-pinned pristine retail executable and proves the exact
 * differences from C08 green: table bytes, constructor handoff, kinematics,
 * damage, target loss, permanence, and terminal ownership.
 *
 * Build and run:
 *   cc -O2 -Wall -Wextra -o /tmp/phase4_c09_static \
 *      tools/phase4_c09_static.c -lcrypto
 *   /tmp/phase4_c09_static SCUS_942.88
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
    fprintf(stderr, "phase4_c09_static: %s\n", message);
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

static uint32_t jal_target(uint32_t pc, uint32_t instruction)
{
    return ((pc + 4) & 0xf0000000u) |
           ((instruction & 0x03ffffffu) << 2);
}

static int differences_match(const uint8_t *left, const uint8_t *right)
{
    static const uint8_t expected[] = {4, 12, 15, 17, 18, 19};
    size_t found = 0;
    size_t i;

    for (i = 0; i < 0x14; ++i) {
        if (left[i] == right[i])
            continue;
        if (found >= sizeof(expected) || i != expected[found])
            return 0;
        ++found;
    }
    return found == sizeof(expected);
}

int main(int argc, char **argv)
{
    static const struct anchor anchors[] = {
        {0x80047170, 0x92030097, "equipped berry selector"},
        {0x800471b8, 0x24110008, "green primary type"},
        {0x800471c8, 0x2411002d, "mega primary type"},
        {0x800471cc, 0x2408f800, "shared primary vertical velocity"},
        {0x80047228, 0xafb1001c, "constructor type argument"},
        {0x8004724c, 0x0c016838, "shared primary spawn call"},
        {0x8005751c, 0x24020030, "mega child type 48"},
        {0x80057520, 0xafb10010, "mega selected target argument"},
        {0x80057528, 0xafa2001c, "mega child type argument"},
        {0x80057538, 0x0c016838, "mega child spawn call"},
        {0x800575d4, 0xa6020022, "no-target timer 80 store"},
        {0x800575d8, 0x24020008, "mega fallback subtype 8"},
        {0x800575dc, 0xa602002c, "mega fallback subtype store"},
        {0x8005984c, 0x3c03800a, "subtype 8 counter high half"},
        {0x80059850, 0x24636596, "owned-throw counter address"},
        {0x8005985c, 0x2442ffff, "subtype 8 counter decrement"},
        {0x80059860, 0xa0620000, "subtype 8 counter store"},
        {0x8005989c, 0x0c015d0f, "subtype 9 acquisition call"},
        {0x800598a0, 0x00002821, "mega acquisition mode zero"},
        {0x8005a268, 0x90a20011, "damage selector row load"},
        {0x8005a270, 0xa2020034, "damage selector record store"},
        {0x8005a274, 0x90a20012, "presentation byte zero load"},
        {0x8005a27c, 0xa2020035, "presentation byte zero store"},
        {0x8005a280, 0x90a20013, "presentation byte one load"},
        {0x8005a288, 0xa2020036, "presentation byte one store"},
        {0x8005a2a4, 0x94a2000c, "connection subtype load"},
        {0x8005a2ac, 0xa602002c, "connection subtype store"},
        {0x8005a2b0, 0x90a2000f, "secondary kind load"},
        {0x8005a2b8, 0xa202002f, "secondary kind store"},
        {0x8005a2bc, 0x80a3000e, "orientation selector byte load"},
        {0x8005a350, 0x92020011, "homing flags load"},
        {0x8005a358, 0x30420008, "homing flag test"},
        {0x8005a45c, 0x00061883, "quarter angular error"},
        {0x8005a4e8, 0x00031cc3, "fixed sine velocity scale"},
        {0x8005a3e0, 0x10800006, "zero target counter expires child"},
        {0x8005a3f0, 0x30420880, "target invalid-state mask"},
        {0x8005a3fc, 0x24020001, "expiry staging value one"},
        {0x8005a400, 0xa6020000, "expiry timer store"},
        {0x80058ee4, 0x30420040, "berry-tough bit test"},
        {0x80058ef0, 0x86220024, "connection-class read"},
        {0x80059074, 0x9223002c, "damage selector read"},
        {0x800590b4, 0x2482fffd, "mega damage delta minus three"},
        {0x800591f0, 0x86230024, "permanence-class read"},
        {0x80059200, 0x92230027, "secondary permanence read"},
        {0x80059218, 0x36f70001, "temporary-hit bit"},
        {0x800592cc, 0x2ae20002, "permanent threshold"}
    };
    static const uint8_t green_primary_expected[0x14] = {
        0x02,0x00,0x08,0x00,0x7b,0x00,0x00,0x01,0x32,0x00,
        0x32,0x00,0x05,0x00,0x00,0x0c,0xe5,0x0c,0x60,0x00
    };
    static const uint8_t mega_primary_expected[0x14] = {
        0x02,0x00,0x08,0x00,0x7c,0x00,0x00,0x01,0x32,0x00,
        0x32,0x00,0x09,0x00,0x00,0x0d,0xe5,0x80,0x20,0x80
    };
    static const uint8_t green_child_expected[0x14] = {
        0x02,0x00,0x64,0x00,0x7b,0x00,0x00,0x01,0x32,0x00,
        0x32,0x00,0x03,0x00,0x00,0x0c,0xed,0x0c,0x60,0x00
    };
    static const uint8_t mega_child_expected[0x14] = {
        0x02,0x00,0x64,0x00,0x7c,0x00,0x00,0x01,0x32,0x00,
        0x32,0x00,0x08,0x00,0x00,0x0d,0xed,0x80,0x20,0x80
    };
    static const uint32_t acquire_callers[] = {
        0x80059730, 0x8005989c, 0x80059a1c
    };
    const uint32_t table = 0x8007941c;
    const uint32_t cleanup_table = 0x8001b790;
    const uint8_t *green_primary;
    const uint8_t *mega_primary;
    const uint8_t *green_child;
    const uint8_t *mega_child;
    struct executable exe;
    char sha[65];
    size_t acquire_count = 0;
    size_t updater_acquire_count = 0;
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

    green_primary = pointer_at(&exe, table + 8 * 0x14, 0x14);
    mega_primary = pointer_at(&exe, table + 45 * 0x14, 0x14);
    green_child = pointer_at(&exe, table + 16 * 0x14, 0x14);
    mega_child = pointer_at(&exe, table + 48 * 0x14, 0x14);
    if (memcmp(green_primary, green_primary_expected, 0x14) != 0 ||
        memcmp(mega_primary, mega_primary_expected, 0x14) != 0 ||
        memcmp(green_child, green_child_expected, 0x14) != 0 ||
        memcmp(mega_child, mega_child_expected, 0x14) != 0)
        fail("green/mega parameter row mismatch");
    if (!differences_match(green_primary, mega_primary) ||
        !differences_match(green_child, mega_child))
        fail("green/mega difference set mismatch");
    if (read_le32(pointer_at(&exe, cleanup_table + 7 * 4, 4)) != 0x80059848 ||
        read_le32(pointer_at(&exe, cleanup_table + 8 * 4, 4)) != 0x80059898)
        fail("subtype 8/9 cleanup binding mismatch");

    /* Mode 0 and mode 1 child-spawn blocks differ only in ctor type 48 vs 16. */
    for (i = 0; i < 14; ++i) {
        uint32_t mega_word = instruction_at(&exe, 0x80057508 + (uint32_t)i * 4);
        uint32_t green_word = instruction_at(&exe, 0x8005754c + (uint32_t)i * 4);
        if (i == 5) {
            if (mega_word != 0x24020030 || green_word != 0x24020010)
                fail("child constructor type differential mismatch");
        } else if (mega_word != green_word) {
            fail("child spawn argument blocks differ beyond constructor type");
        }
    }

    for (i = 0; i + 4 <= exe.text_size; i += 4) {
        uint32_t pc = exe.load_address + (uint32_t)i;
        uint32_t instruction = read_le32(exe.data + 0x800 + i);
        if ((instruction >> 26) == 3 &&
            jal_target(pc, instruction) == 0x8005743c) {
            if (acquire_count >= 3 || pc != acquire_callers[acquire_count])
                fail("unexpected acquisition caller set or ordering");
            ++acquire_count;
            if (pc >= 0x8005a308 && pc < 0x8005b128)
                ++updater_acquire_count;
        }
    }
    if (acquire_count != 3 || updater_acquire_count != 0)
        fail("acquisition xref count mismatch");

    printf("{\n");
    printf("  \"schema\": \"phase4_c09_static_v1\",\n");
    printf("  \"row\": \"C09_mega_homing_berry\",\n");
    printf("  \"pristine_exe_sha256\": \"%s\",\n", sha);
    printf("  \"anchors_checked\": %zu,\n",
           sizeof(anchors) / sizeof(anchors[0]));
    printf("  \"dispatch\": {\"equip_index\": 4, \"primary_type\": 45, "
           "\"primary_timer\": 8, \"primary_subtype\": 9, "
           "\"acquisition_mode\": 0},\n");
    printf("  \"handoff\": {\"child_type\": 48, \"child_timer\": 100, "
           "\"child_subtype\": 8, \"no_target_timer\": 80, "
           "\"no_target_subtype\": 8},\n");
    printf("  \"green_mega_row_difference_offsets\": [4,12,15,17,18,19],\n");
    printf("  \"mega_row_values\": {\"model\": 124, "
           "\"secondary_kind\": 13, \"orientation_selector\": 0, "
           "\"damage_selector\": 128, \"presentation_bytes\": [32,128]},\n");
    printf("  \"kinematics_vs_green\": {\"primary_launch\": \"identical\", "
           "\"acquisition\": \"identical\", \"turn_rate\": \"identical\", "
           "\"vertical_seek_clamp\": \"identical [-1024,1024]\", "
           "\"velocity_scale\": \"identical sine/8\", "
           "\"primary_lifetime\": \"identical 8\", "
           "\"child_lifetime\": \"identical 100\", "
           "\"speed_result\": \"not faster\"},\n");
    printf("  \"damage_vs_green\": {\"green_selector\": 12, "
           "\"green_delta\": -2, \"mega_selector\": 128, "
           "\"mega_delta\": -3, \"berry_tough\": \"damaging\", "
           "\"permanence\": \"temporary\"},\n");
    printf("  \"target_loss\": {\"invalid_mask\": 2176, "
           "\"expiry_timer\": 1, \"reacquisition_calls_in_updater\": 0, "
           "\"result\": \"same retire-without-retarget law as green\"},\n");
    printf("  \"ownership\": {\"primary_subtype\": 9, "
           "\"terminal_subtype\": 8, \"counter\": \"0x800a6596\", "
           "\"terminal_decrement\": 1},\n");
    printf("  \"result\": \"C09_STATIC_DIFFERENTIAL_PASS\"\n");
    printf("}\n");
    free(exe.data);
    return 0;
}
