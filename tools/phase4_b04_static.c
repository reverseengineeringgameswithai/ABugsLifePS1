/* Phase 4 B04: pristine-SCUS opcode verifier for the cannon launch chain. */
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t u32le(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static unsigned char *read_file(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    unsigned char *data;
    long length;
    if (!f) { perror(path); exit(2); }
    if (fseek(f, 0, SEEK_END) || (length = ftell(f)) < 0) exit(2);
    rewind(f);
    data = malloc((size_t)length);
    if (!data || fread(data, 1, (size_t)length, f) != (size_t)length) exit(2);
    fclose(f);
    *size = (size_t)length;
    return data;
}

static void sha256_hex(const unsigned char *data, size_t size, char out[65])
{
    unsigned char digest[SHA256_DIGEST_LENGTH];
    SHA256(data, size, digest);
    for (unsigned i = 0; i < sizeof(digest); i++)
        sprintf(out + i * 2, "%02x", digest[i]);
    out[64] = '\0';
}

struct check { uint32_t pc, word; const char *meaning; };

static const struct check checks[] = {
    {0x8005c110, 0x169502f5, "selected-contact equality gate"},
    {0x8005c118, 0x86430002, "plant state read at slot+2"},
    {0x8005c120, 0x146202f1, "plant state must equal 1"},
    {0x8005c128, 0x9642002e, "plant maturity flags read at slot+0x2e"},
    {0x8005c130, 0x30420002, "maturity bit 0x2 test"},
    {0x8005c168, 0x96e20034, "contact-object trigger flags read"},
    {0x8005c170, 0x30420080, "trigger bit 0x80 test"},
    {0x8005c1a0, 0x3063ff7e, "clear trigger bits 0x81"},
    {0x8005c1fc, 0xa420657a, "clear player latch 0x800A657A"},
    {0x8005c204, 0xac20655c, "clear carried-actor pointer 0x800A655C"},
    {0x8005c20c, 0xa02065a3, "clear player byte 0x800A65A3"},
    {0x8005c230, 0xa6420002, "switch cannon plant animation/state"},
    {0x8005c244, 0x24020011, "load seated lockout count 17"},
    {0x8005c24c, 0xa422657c, "store lockout at player+0x7C"},
    {0x80048658, 0x8622007c, "shared player path reads lockout"},
    {0x8004866c, 0xa622007c, "decrement lockout once per physics update"},
    {0x80048688, 0xae20002c, "seated phase pins vx to zero"},
    {0x8004868c, 0xae200030, "seated phase pins vy to zero"},
    {0x80048690, 0xae200034, "seated phase pins vz to zero"},
    {0x800486b4, 0xa6220080, "expiry selects player mode 5"},
    {0x800486b8, 0x2402e000, "fixed launch seed -8192"},
    {0x800486cc, 0xae220030, "store launch seed at player+0x30"},
    {0x800486dc, 0x8623009e, "read plant/contact latch"},
    {0x800486e0, 0x2402000b, "dandelion latch value 11"},
    {0x8004870c, 0x2862015e, "airborne slow-fall compare against 350"},
    {0x80048714, 0x24620100, "slow-fall acceleration +256"},
    {0x80048720, 0x2402015e, "slow-fall terminal velocity 350"}
};

int main(int argc, char **argv)
{
    static const char pristine_sha[] =
        "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20";
    unsigned char *exe;
    size_t size;
    uint32_t load, text;
    char sha[65];
    if (argc != 2) {
        fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]);
        return 2;
    }
    exe = read_file(argv[1], &size);
    sha256_hex(exe, size, sha);
    if (strcmp(sha, pristine_sha) != 0) {
        fprintf(stderr, "refusing non-pristine executable: %s\n", sha);
        free(exe);
        return 3;
    }
    if (size < 0x800 || memcmp(exe, "PS-X EXE", 8) != 0) return 4;
    load = u32le(exe + 0x18);
    text = u32le(exe + 0x1c);
    for (size_t i = 0; i < sizeof(checks) / sizeof(checks[0]); i++) {
        uint64_t off = UINT64_C(0x800) + checks[i].pc - load;
        if (checks[i].pc < load || off + 4 > size || u32le(exe + off) != checks[i].word) {
            fprintf(stderr, "opcode mismatch at 0x%08" PRIx32 " (%s)\n",
                    checks[i].pc, checks[i].meaning);
            free(exe);
            return 5;
        }
    }
    printf("{\n");
    printf("  \"schema\": \"phase4-b04-static-v1\",\n");
    printf("  \"pristine_sha256\": \"%s\",\n", sha);
    printf("  \"psx_load_address\": \"0x%08" PRIx32 "\",\n", load);
    printf("  \"psx_text_bytes\": %" PRIu32 ",\n", text);
    printf("  \"opcode_checks\": %zu,\n", sizeof(checks) / sizeof(checks[0]));
    printf("  \"handler\": \"0x8005C110\",\n");
    printf("  \"launch_owner\": \"shared player path 0x80048658..0x800486D8\",\n");
    printf("  \"seated_ticks\": 17,\n");
    printf("  \"launch_seed\": [0, -8192, 0],\n");
    printf("  \"launch_source\": \"fixed immediate at 0x800486B8; no vector table\",\n");
    printf("  \"dandelion_latch\": 11,\n");
    printf("  \"dandelion_terminal_vy\": 350,\n");
    printf("  \"all_checks_passed\": true\n}\n");
    free(exe);
    return 0;
}
