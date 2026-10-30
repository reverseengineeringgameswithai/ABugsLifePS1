/*
 * Phase 4 D06 grasshopper static evidence extractor.
 *
 * This intentionally reads only the hash-pinned retail executable and the
 * raw LEVEL03 resident overlay.  It does not patch either input.
 *
 * Build:
 *   cc -O2 -Wall -Wextra -o /tmp/phase4_d06_static \
 *      tools/phase4_d06_static.c -lcrypto
 * Run:
 *   /tmp/phase4_d06_static SCUS_942.88 REBUILD/files/LEVEL03/LEVEL.BIN
 */

#include <errno.h>
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_RAM_BASE UINT32_C(0x8000f800)
#define EXE_FILE_BASE UINT32_C(0x00000800)
#define OVERLAY_BASE UINT32_C(0x800b39a0)

static const char *const EXE_SHA256 =
    "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20";
static const char *const OVERLAY_SHA256 =
    "fef7bd2a72c5c293b2f164ba1ca195f45c0843c5f19e52cbfdb48fd14fbc59a1";

struct blob {
    uint8_t *data;
    size_t size;
};

static uint16_t le16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static struct blob read_blob(const char *path)
{
    struct blob b = {0};
    FILE *fp = fopen(path, "rb");
    long length;

    if (!fp) {
        fprintf(stderr, "%s: %s\n", path, strerror(errno));
        exit(2);
    }
    if (fseek(fp, 0, SEEK_END) != 0 || (length = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0) {
        fprintf(stderr, "%s: cannot determine length\n", path);
        exit(2);
    }
    b.size = (size_t)length;
    b.data = malloc(b.size ? b.size : 1);
    if (!b.data || fread(b.data, 1, b.size, fp) != b.size) {
        fprintf(stderr, "%s: cannot read file\n", path);
        exit(2);
    }
    fclose(fp);
    return b;
}

static void sha256_hex(const struct blob *b, char out[65])
{
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int length = 0;
    size_t i;

    if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
        EVP_DigestUpdate(ctx, b->data, b->size) != 1 ||
        EVP_DigestFinal_ex(ctx, digest, &length) != 1 || length != 32) {
        fprintf(stderr, "SHA-256 failure\n");
        exit(2);
    }
    EVP_MD_CTX_free(ctx);
    for (i = 0; i < length; ++i)
        sprintf(out + i * 2, "%02x", digest[i]);
    out[64] = '\0';
}

static const uint8_t *exe_at(const struct blob *b, uint32_t address, size_t length)
{
    uint64_t offset;

    if (address < EXE_RAM_BASE) {
        fprintf(stderr, "invalid executable address %08" PRIx32 "\n", address);
        exit(2);
    }
    offset = (uint64_t)(address - EXE_RAM_BASE) + EXE_FILE_BASE;
    if (offset + length > b->size) {
        fprintf(stderr, "executable address %08" PRIx32 " is outside input\n", address);
        exit(2);
    }
    return b->data + offset;
}

static const uint8_t *overlay_at(const struct blob *b, uint32_t address, size_t length)
{
    uint64_t offset;

    if (address < OVERLAY_BASE) {
        fprintf(stderr, "invalid overlay address %08" PRIx32 "\n", address);
        exit(2);
    }
    offset = address - OVERLAY_BASE;
    if (offset + length > b->size) {
        fprintf(stderr, "overlay address %08" PRIx32 " is outside input\n", address);
        exit(2);
    }
    return b->data + offset;
}

static uint32_t jal_target(uint32_t pc, uint32_t instruction)
{
    return ((pc + 4) & UINT32_C(0xf0000000)) |
           ((instruction & UINT32_C(0x03ffffff)) << 2);
}

static void require_hash(const char *label, const struct blob *b, const char *expected)
{
    char actual[65];
    sha256_hex(b, actual);
    if (strcmp(actual, expected) != 0) {
        fprintf(stderr, "%s SHA-256 mismatch\nexpected %s\nactual   %s\n",
                label, expected, actual);
        exit(1);
    }
    printf("%s_sha256=%s\n", label, actual);
}

static void require_u32(const char *label, uint32_t address, uint32_t actual,
                        uint32_t expected)
{
    if (actual != expected) {
        fprintf(stderr, "%s at %08" PRIx32 ": expected %08" PRIx32
                        ", found %08" PRIx32 "\n",
                label, address, expected, actual);
        exit(1);
    }
    printf("%s=%08" PRIx32 "\n", label, actual);
}

int main(int argc, char **argv)
{
    static const uint16_t expected_program[] = {
        0x0016, 0x0020, 0xffc0, 0x000b, 0x0003, 0x000d, 0x0001,
        0x0002, 0x0006, 0x0015, 0x000d, 0x0000, 0x0001, 0x0002,
        0x003f, 0x0020, 0x0003, 0x0005, 0xffff, 0x0005
    };
    const uint32_t program_table = UINT32_C(0x80077af8);
    const uint32_t program_address = UINT32_C(0x8007760c);
    const uint32_t selector_call = UINT32_C(0x8004c5f4);
    const uint32_t native_address = UINT32_C(0x800b3d78);
    const uint32_t native_calls[] = {
        UINT32_C(0x800b3db8), UINT32_C(0x800b3e2c), UINT32_C(0x800b3e60)
    };
    const uint32_t expected_calls[] = {
        UINT32_C(0x80060ae4), UINT32_C(0x80059e44), UINT32_C(0x8005044c)
    };
    struct blob exe, overlay;
    const uint8_t *p;
    size_t i;

    if (argc != 3) {
        fprintf(stderr, "usage: %s SCUS_942.88 LEVEL03/LEVEL.BIN\n", argv[0]);
        return 2;
    }
    exe = read_blob(argv[1]);
    overlay = read_blob(argv[2]);
    require_hash("retail_exe", &exe, EXE_SHA256);
    require_hash("level03_overlay", &overlay, OVERLAY_SHA256);

    p = exe_at(&exe, program_table + 8 * 4, 4);
    require_u32("grasshopper_program_pointer", program_table + 8 * 4,
                le32(p), program_address);
    p = exe_at(&exe, program_address, sizeof(expected_program));
    for (i = 0; i < sizeof(expected_program) / sizeof(expected_program[0]); ++i) {
        if (le16(p + i * 2) != expected_program[i]) {
            fprintf(stderr, "program word %zu mismatch\n", i);
            return 1;
        }
    }
    printf("program8_words=20 first=%04x arrival=%04x native=%04x park=%04x\n",
           expected_program[0], expected_program[8], expected_program[9],
           expected_program[17]);

    require_u32("vm_program_load", UINT32_C(0x8004c17c),
                le32(exe_at(&exe, UINT32_C(0x8004c17c), 4)), UINT32_C(0x8e110070));
    require_u32("vm_opcode_fetch", UINT32_C(0x8004c1ec),
                le32(exe_at(&exe, UINT32_C(0x8004c1ec), 4)), UINT32_C(0x96220000));
    require_u32("vm_program_commit", UINT32_C(0x8004c834),
                le32(exe_at(&exe, UINT32_C(0x8004c834), 4)), UINT32_C(0xae110070));
    require_u32("arrival_program_advance", UINT32_C(0x8004d03c),
                le32(exe_at(&exe, UINT32_C(0x8004d03c), 4)), UINT32_C(0xae020070));

    p = exe_at(&exe, selector_call, 4);
    require_u32("selector3_native_jal", selector_call, jal_target(selector_call, le32(p)),
                native_address);
    require_u32("native_prologue", native_address,
                le32(overlay_at(&overlay, native_address, 4)), UINT32_C(0x27bdffd0));
    for (i = 0; i < sizeof(native_calls) / sizeof(native_calls[0]); ++i) {
        uint32_t instruction = le32(overlay_at(&overlay, native_calls[i], 4));
        require_u32("native_direct_callee", native_calls[i],
                    jal_target(native_calls[i], instruction), expected_calls[i]);
    }
    require_u32("native_return", UINT32_C(0x800b3e80),
                le32(overlay_at(&overlay, UINT32_C(0x800b3e80), 4)),
                UINT32_C(0x03e00008));

    printf("family_binding=actor_id_15 spawn_word_080f program_index_8\n");
    printf("native_extent=800b3d78..800b3e84 instructions=68\n");
    printf("result=all_static_D06_anchors_match\n");
    free(exe.data);
    free(overlay.data);
    return 0;
}
