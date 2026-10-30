/*
 * Phase 4 C08 Green/Homing Berry static evidence gate.
 *
 * Reads only the hash-pinned pristine retail executable. It verifies the
 * one-shot primary-to-child transition, target scan and tie law, absence of
 * child retargeting, invalid-target retirement, collision payload, and owned
 * projectile cleanup.
 *
 * Build and run:
 *   cc -O2 -Wall -Wextra -o /tmp/phase4_c08_static \
 *      tools/phase4_c08_static.c -lcrypto
 *   /tmp/phase4_c08_static SCUS_942.88
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
    fprintf(stderr, "phase4_c08_static: %s\n", message);
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

int main(int argc, char **argv)
{
    static const struct anchor anchors[] = {
        {0x8005745c, 0x3c028009, "damageable table high half"},
        {0x80057460, 0x24420748, "damageable table low half"},
        {0x8005747c, 0x9483005c, "candidate state load"},
        {0x80057484, 0x30620001, "targetable bit filter"},
        {0x8005748c, 0x306200a0, "already-hit/dead filter"},
        {0x800574a8, 0x00021143, "X distance shift by five"},
        {0x800574c0, 0x00021143, "Z distance shift by five"},
        {0x800574d0, 0x00e3102a, "strict best-less-than-new tie test"},
        {0x80057560, 0x24020010, "mode one child type 16"},
        {0x80057564, 0xafb10010, "selected target argument"},
        {0x8005756c, 0xafa2001c, "child type argument"},
        {0x8005757c, 0x0c016838, "child spawn call"},
        {0x800575d4, 0xa6020022, "no-target timer 80 store"},
        {0x800575ec, 0x24020003, "mode one fallback subtype 3"},
        {0x800575f0, 0xa602002c, "fallback subtype store"},
        {0x8005a3d0, 0x8e220044, "target transform index load"},
        {0x8005a3d8, 0x8624006e, "target local counter load"},
        {0x8005a3e0, 0x10800006, "zero target counter expires child"},
        {0x8005a3e8, 0x9622005c, "target state load"},
        {0x8005a3f0, 0x30420880, "target invalid-state mask"},
        {0x8005a3f4, 0x10400003, "valid target bypasses expiry write"},
        {0x8005a3fc, 0x24020001, "expiry staging value one"},
        {0x8005a400, 0xa6020000, "expiry timer store"},
        {0x80058ee4, 0x30420040, "berry-tough bit test"},
        {0x80058ef0, 0x86220024, "biased connection-class read"},
        {0x80059074, 0x9223002c, "biased damage-byte read"},
        {0x800590c4, 0x2482fffe, "damage delta minus two"},
        {0x800591f0, 0x86230024, "permanence-class read"},
        {0x80059200, 0x92230027, "secondary permanence read"},
        {0x80059218, 0x36f70001, "temporary-hit bit"},
        {0x800592cc, 0x2ae20002, "permanent threshold"},
        {0x80059654, 0x3c03800a, "subtype 3 counter high half"},
        {0x80059658, 0x24636596, "owned-throw counter address"},
        {0x80059664, 0x2442ffff, "owned-throw counter decrement"},
        {0x80059668, 0xa0620000, "owned-throw counter store"},
        {0x80059730, 0x0c015d0f, "subtype 5 acquisition call"},
        {0x80059734, 0x24050001, "green mode selector one"},
        {0x8005b0e8, 0x0c01654f, "terminal cleanup dispatch"}
    };
    static const uint8_t primary_expected[0x14] = {
        0x02,0x00,0x08,0x00,0x7b,0x00,0x00,0x01,0x32,0x00,
        0x32,0x00,0x05,0x00,0x00,0x0c,0xe5,0x0c,0x60,0x00
    };
    static const uint8_t child_expected[0x14] = {
        0x02,0x00,0x64,0x00,0x7b,0x00,0x00,0x01,0x32,0x00,
        0x32,0x00,0x03,0x00,0x00,0x0c,0xed,0x0c,0x60,0x00
    };
    static const uint32_t acquire_callers[3] = {
        0x80059730, 0x8005989c, 0x80059a1c
    };
    const uint32_t parameter_table = 0x8007941c;
    const uint32_t cleanup_table = 0x8001b790;
    struct executable exe;
    char sha[65];
    size_t anchors_checked = 0;
    size_t selector_count = 0;
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
        ++anchors_checked;
    }

    if (memcmp(pointer_at(&exe, parameter_table + 8 * 0x14, 0x14),
               primary_expected, 0x14) != 0)
        fail("green primary parameter row mismatch");
    if (memcmp(pointer_at(&exe, parameter_table + 16 * 0x14, 0x14),
               child_expected, 0x14) != 0)
        fail("green child parameter row mismatch");
    if (read_le32(pointer_at(&exe, cleanup_table + 2 * 4, 4)) != 0x80059650 ||
        read_le32(pointer_at(&exe, cleanup_table + 4 * 4, 4)) != 0x8005972c)
        fail("subtype 3/5 cleanup jump-table binding mismatch");

    for (i = 0; i + 4 <= exe.text_size; i += 4) {
        uint32_t pc = exe.load_address + (uint32_t)i;
        uint32_t instruction = read_le32(exe.data + 0x800 + i);
        if (pc >= 0x80047170 && pc < 0x800471e0 &&
            instruction == 0x24110008)
            ++selector_count;
        if ((instruction >> 26) == 3 &&
            jal_target(pc, instruction) == 0x8005743c) {
            if (acquire_count >= 3 || pc != acquire_callers[acquire_count])
                fail("unexpected acquisition caller set or ordering");
            ++acquire_count;
            if (pc >= 0x8005a308 && pc < 0x8005b128)
                ++updater_acquire_count;
        }
    }
    if (selector_count != 1)
        fail("equip index 2 constructor selector was not unique");
    if (acquire_count != 3 || updater_acquire_count != 0)
        fail("acquisition xref count mismatch");

    printf("{\n");
    printf("  \"schema\": \"phase4_c08_static_v1\",\n");
    printf("  \"row\": \"C08_green_homing_berry\",\n");
    printf("  \"pristine_exe_sha256\": \"%s\",\n", sha);
    printf("  \"anchors_checked\": %zu,\n", anchors_checked);
    printf("  \"equip_dispatch\": {\"equip_index\": 2, "
           "\"primary_type\": 8, \"selector_instruction_count\": 1},\n");
    printf("  \"primary_row\": {\"address\": \"0x800794bc\", "
           "\"timer\": 8, \"model\": 123, \"subtype\": 5, "
           "\"flags\": 229, \"damage_byte\": 12},\n");
    printf("  \"acquisition\": {\"entry\": \"0x8005743c\", "
           "\"caller\": \"subtype 5 cleanup at 0x80059730\", "
           "\"mode\": 1, \"table\": \"0x80090748\", "
           "\"termination\": \"first NULL pointer\", "
           "\"required_state_mask\": 1, \"excluded_state_mask\": 160, "
           "\"axes\": \"XZ only\", \"coordinate_shift\": 5, "
           "\"range_cutoff\": null, "
           "\"tie_law\": \"equal distance replaces the earlier candidate\"},\n");
    printf("  \"handoff\": {\"selected_target_stack_offset\": 16, "
           "\"child_type\": 16, \"child_target_record_offset\": 16, "
           "\"no_target_timer\": 80, \"no_target_subtype\": 3},\n");
    printf("  \"child_row\": {\"address\": \"0x8007955c\", "
           "\"timer\": 100, \"model\": 123, \"subtype\": 3, "
           "\"flags\": 237, \"homing_bit\": 8, "
           "\"damage_byte\": 12},\n");
    printf("  \"target_loss\": {\"counter_zero_expires\": true, "
           "\"invalid_state_mask\": 2176, \"expiry_timer\": 1, "
           "\"reacquisition_calls_in_child_updater\": 0, "
           "\"result\": \"retire without retarget\"},\n");
    printf("  \"collision\": {\"connection_class\": 3, "
           "\"damage_byte\": 12, \"exact_local_counter_delta\": -2, "
           "\"berry_tough_result\": \"damaging, not reaction-only\", "
           "\"defeat_permanence\": \"temporary\"},\n");
    printf("  \"ownership\": {\"primary_subtype\": 5, "
           "\"terminal_child_subtype\": 3, "
           "\"counter\": \"0x800a6596\", "
           "\"terminal_decrement\": 1},\n");
    printf("  \"acquisition_direct_callers\": "
           "[\"0x80059730\",\"0x8005989c\",\"0x80059a1c\"],\n");
    printf("  \"result\": \"C08_STATIC_CORE_PASS\"\n");
    printf("}\n");
    free(exe.data);
    return 0;
}
