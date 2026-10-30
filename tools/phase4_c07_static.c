/*
 * Phase 4 C07 Blue/Super Berry static evidence gate.
 *
 * Reads only the hash-pinned pristine retail executable. It distinguishes the
 * constructor type from the record class, compares blue against red byte for
 * byte, and verifies resistance, damage, and permanence control flow.
 *
 * Build and run:
 *   cc -O2 -Wall -Wextra -o /tmp/phase4_c07_static \
 *      tools/phase4_c07_static.c -lcrypto
 *   /tmp/phase4_c07_static SCUS_942.88
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
    fprintf(stderr, "phase4_c07_static: %s\n", message);
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

static size_t executable_offset(const struct executable *exe, uint32_t address)
{
    uint64_t delta;

    if (address < exe->load_address)
        fail("address precedes executable load address");
    delta = (uint64_t)address - exe->load_address;
    if (delta + 4 > exe->text_size || 0x800 + delta + 4 > exe->size)
        fail("address is outside executable text");
    return 0x800 + (size_t)delta;
}

static uint32_t instruction_at(const struct executable *exe, uint32_t address)
{
    return read_le32(exe->data + executable_offset(exe, address));
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

int main(int argc, char **argv)
{
    static const struct anchor anchors[] = {
        {0x800471b0, 0x24110005, "equip index 1 selects constructor type 5"},
        {0x800542c0, 0x24020001, "blue pickup selector value"},
        {0x800542c8, 0xa0226597, "blue pickup selector store"},
        {0x800542d0, 0x24040035, "blue pickup sound"},
        {0x8005a190, 0x00081080, "constructor type times 20"},
        {0x8005a2a4, 0x94a2000c, "load connection class"},
        {0x8005a2ac, 0xa602002c, "store connection class"},
        {0x8005a268, 0x90a20011, "load damage byte"},
        {0x8005a270, 0xa2020034, "store damage byte"},
        {0x80058ee4, 0x30420040, "enemy berry-tough bit test"},
        {0x80058ef0, 0x86220024, "biased connection-class read"},
        {0x80058f00, 0x9222002c, "biased alternate-class read"},
        {0x80059074, 0x9223002c, "biased damage-byte read"},
        {0x8005908c, 0x1060000c, "damage byte zero branch"},
        {0x800590c4, 0x2482fffe, "damage delta minus two"},
        {0x800590e4, 0xa642006e, "enemy local-counter store"},
        {0x800591f0, 0x86230024, "permanence-class read"},
        {0x80059200, 0x92230027, "secondary permanence read"},
        {0x80059218, 0x36f70001, "temporary-hit bit"},
        {0x800592cc, 0x2ae20002, "permanent threshold"}
    };
    const uint32_t table = 0x8007941c;
    const uint32_t red_address = table + 2 * 0x14;
    const uint32_t blue_address = table + 5 * 0x14;
    struct executable exe;
    const uint8_t *red;
    const uint8_t *blue;
    char sha[65];
    size_t differences = 0;
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

    red = exe.data + executable_offset(&exe, red_address);
    blue = exe.data + executable_offset(&exe, blue_address);
    if (read_le16(blue + 0x00) != 2 || read_le16(blue + 0x02) != 100 ||
        read_le16(blue + 0x04) != 110 || read_le16(blue + 0x0c) != 2 ||
        blue[0x0f] != 1 || blue[0x10] != 0xe5 || blue[0x11] != 0 ||
        blue[0x12] != 0x20 || blue[0x13] != 0x80)
        fail("blue parameter row mismatch");
    for (i = 0; i < 0x14; ++i)
        if (red[i] != blue[i])
            ++differences;
    if (differences != 4 || red[0x0c] != 1 || red[0x11] != 0x70 ||
        red[0x12] != 0x12 || red[0x13] != 0x00)
        fail("red/blue difference set mismatch");

    printf("{\n");
    printf("  \"schema\": \"phase4_c07_static_v1\",\n");
    printf("  \"pristine_exe_sha256\": \"%s\",\n", sha);
    printf("  \"anchors_checked\": %zu,\n",
           sizeof(anchors) / sizeof(anchors[0]));
    printf("  \"blue_parameter_row\": {\"address\": \"0x%08" PRIx32
           "\", \"constructor_type\": 5, \"record_class\": 2, "
           "\"timer\": 100, \"model_or_marker\": 110, "
           "\"connection_class\": 2, \"damage_byte\": 0, "
           "\"flags\": 229, \"presentation_bytes\": [32,128]},\n",
           blue_address);
    printf("  \"red_blue_differences\": {\"count\": 4, "
           "\"offsets\": [12,17,18,19]},\n");
    printf("  \"trajectory_result\": \"timer, model, physical fields, and "
           "flags are identical to red\",\n");
    printf("  \"resistance_result\": \"class 2 and damage byte 0 both bypass "
           "the class-1 reaction-only comparisons\",\n");
    printf("  \"damage_result\": \"damage byte 0 selects exact -2 delta for "
           "ordinary and berry-tough actors\",\n");
    printf("  \"defeat_result\": \"temporary; class 2 is not permanent class "
           "11 and secondary marker 1 is not 6\",\n");
    printf("  \"result\": \"C07_STATIC_CORE_PASS\"\n");
    printf("}\n");
    free(exe.data);
    return 0;
}
