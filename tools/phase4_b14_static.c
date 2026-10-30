#define _POSIX_C_SOURCE 200809L

#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LOAD_BIAS 0x8000f800u
#define META_B 0x8007941cu
#define META_A 0x80079e30u
#define EXPECTED_SIZE 471040u
#define EXPECTED_SHA256 "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"

typedef struct {
    uint16_t action;
    uint16_t active;
    int16_t init;
    uint8_t b6;
    uint8_t b7;
    int16_t radius_add;
    int16_t field_2a;
    int16_t state;
    uint8_t sign;
    uint8_t b2f;
    uint8_t flags;
    uint8_t r;
    uint8_t g;
    uint8_t b;
} Meta;

static uint8_t *g_exe;
static size_t g_size;
static unsigned g_failures;

static void fail(const char *what)
{
    fprintf(stderr, "phase4_b14_static: %s\n", what);
    g_failures++;
}

static uint8_t *slurp(const char *path)
{
    FILE *f = fopen(path, "rb");
    long size;
    uint8_t *p;

    if (!f) {
        perror(path);
        exit(2);
    }
    if (fseek(f, 0, SEEK_END) != 0 || (size = ftell(f)) < 0) {
        fail("cannot size executable");
        exit(2);
    }
    rewind(f);
    p = malloc((size_t)size);
    if (!p || fread(p, 1, (size_t)size, f) != (size_t)size) {
        fail("cannot read executable");
        exit(2);
    }
    fclose(f);
    g_size = (size_t)size;
    return p;
}

static uint16_t u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static int16_t s16(const uint8_t *p)
{
    return (int16_t)u16(p);
}

static uint32_t u32(const uint8_t *p)
{
    return p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static int32_t s32(const uint8_t *p)
{
    return (int32_t)u32(p);
}

static uint32_t off(uint32_t address)
{
    return address - LOAD_BIAS;
}

static uint32_t word(uint32_t address)
{
    uint32_t o = off(address);
    if ((uint64_t)o + 4 > g_size) {
        fail("address outside executable");
        return 0;
    }
    return u32(g_exe + o);
}

static Meta meta(unsigned ctor)
{
    const uint8_t *p = g_exe + off(META_B + ctor * 0x14u);
    Meta m;
    m.action = u16(p + 0x00);
    m.active = u16(p + 0x02);
    m.init = s16(p + 0x04);
    m.b6 = p[0x06];
    m.b7 = p[0x07];
    m.radius_add = s16(p + 0x08);
    m.field_2a = s16(p + 0x0a);
    m.state = s16(p + 0x0c);
    m.sign = p[0x0e];
    m.b2f = p[0x0f];
    m.flags = p[0x10];
    m.r = p[0x11];
    m.g = p[0x12];
    m.b = p[0x13];
    return m;
}

static void expect_word(uint32_t address, uint32_t expected, const char *what)
{
    if (word(address) != expected)
        fail(what);
}

static void expect_meta(unsigned ctor, uint16_t action, uint16_t active,
                        int16_t init, int16_t radius, int16_t state,
                        uint8_t flags)
{
    Meta m = meta(ctor);
    if (m.action != action || m.active != active || m.init != init ||
        m.radius_add != radius || m.state != state || m.flags != flags)
        fail("contact metadata row mismatch");
}

int main(int argc, char **argv)
{
    uint8_t digest[SHA256_DIGEST_LENGTH];
    char hex[SHA256_DIGEST_LENGTH * 2 + 1];
    const uint8_t *a6;
    unsigned ctor59_immediates = 0;
    uint32_t ctor59_sites[4] = {0};
    Meta m59;

    if (argc != 2) {
        fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]);
        return 2;
    }
    g_exe = slurp(argv[1]);
    if (g_size != EXPECTED_SIZE)
        fail("unexpected executable size");
    SHA256(g_exe, g_size, digest);
    for (unsigned i = 0; i < SHA256_DIGEST_LENGTH; i++)
        sprintf(hex + i * 2, "%02x", digest[i]);
    hex[64] = 0;
    if (strcmp(hex, EXPECTED_SHA256) != 0)
        fail("executable is not the pinned pristine image");

    expect_meta(31, 46, 230, 240, 1, 7, 0x82);
    expect_meta(37, 12, 200, 2, 100, -41, 0x83);
    expect_meta(38, 9, 200, 210, 100, -42, 0xe3);
    expect_meta(39, 15, 200, 210, 100, -43, 0xa3);
    expect_meta(59, 8, 200, 210, 100, -60, 0xe3);

    a6 = g_exe + off(META_A + 6 * 0x14u);
    if (u32(a6) != 0x00001510u || s32(a6 + 4) != 255 ||
        s32(a6 + 8) != 5183 || s32(a6 + 12) != 255 ||
        s32(a6 + 16) != 128)
        fail("table-A profile 6 mismatch");

    /* Type 6: ctor=(extra>>12)+31, profile 3, then one-shot latch bit 3. */
    expect_word(0x8005c728u, 0x0c016791u, "type-6 allocator call moved");
    expect_word(0x8005c72cu, 0x24e7001fu, "type-6 ctor base changed");
    expect_word(0x8005c738u, 0x34420008u, "type-6 one-shot latch changed");

    /* Type 7: RNG low-two-bit branch or the tier-4 forced fallback selects 59. */
    expect_word(0x8005c7b0u, 0x30420003u, "type-7 RNG mask changed");
    expect_word(0x8005c7e4u, 0x2407003bu, "type-7 ctor-59 selection changed");
    expect_word(0x8005c800u, 0x0c016791u, "type-7 allocator call moved");
    expect_word(0x8005c808u, 0x0c015e78u, "type-7 radial helper call moved");

    /* Action 8 dispatches to 0x80058854, which selects damage state 0x13. */
    if (word(0x8001b588u) != 0x80058854u)
        fail("action-8 dispatch target changed");
    expect_word(0x80058854u, 0x24160001u, "action-8 damage latch changed");
    expect_word(0x80058858u, 0x24100013u, "action-8 impact state changed");

    /* Generic motion/retirement: integrate, test terrain, retire, emit effect. */
    expect_word(0x8005a358u, 0x30420008u, "homing flag mask changed");
    expect_word(0x8005a518u, 0x8e42ffe2u, "ballistic Y load changed");
    expect_word(0x8005a5a8u, 0x30420001u, "terrain-contact flag mask changed");
    expect_word(0x8005b0e8u, 0x0c01654fu, "retirement effect call moved");
    expect_word(0x8005957cu, 0x00073823u, "negative-state effect selector changed");

    for (uint32_t o = 0x800; (uint64_t)o + 4 <= g_size; o += 4) {
        uint32_t insn = u32(g_exe + o);
        uint32_t op = insn >> 26;
        uint32_t rs = (insn >> 21) & 31;
        uint32_t rt = (insn >> 16) & 31;
        if ((op == 9 || op == 13) && rs == 0 && rt == 7 &&
            (insn & 0xffffu) == 59) {
            if (ctor59_immediates < 4)
                ctor59_sites[ctor59_immediates] = LOAD_BIAS + o;
            ctor59_immediates++;
        }
    }
    if (ctor59_immediates != 2 || ctor59_sites[0] != 0x8005c78cu ||
        ctor59_sites[1] != 0x8005c7e4u)
        fail("constructor 59 has an unexpected producer site");

    m59 = meta(59);
    printf("{\n");
    printf("  \"exe_sha256\": \"%s\",\n", hex);
    printf("  \"pristine\": %s,\n", strcmp(hex, EXPECTED_SHA256) ? "false" : "true");
    printf("  \"constructor59_immediate_sites\": [\"0x%08x\", \"0x%08x\"],\n",
           ctor59_sites[0], ctor59_sites[1]);
    printf("  \"type6_can_select_59\": false,\n");
    printf("  \"type7_rng_spike_fraction\": \"1/4\",\n");
    printf("  \"constructor59\": {\"action\": %u, \"logic_lifetime\": %u, "
           "\"contact_radius\": %d, \"state\": %d, \"flags\": \"0x%02x\"},\n",
           m59.action, m59.active, 300 + m59.radius_add, m59.state, m59.flags);
    printf("  \"profile6\": {\"vx_min\": -1016, \"vx_max\": 1024, "
           "\"vy_min\": -2560, \"vy_max\": -2056, "
           "\"vz_min\": -1016, \"vz_max\": 1024, \"ay\": 128},\n");
    printf("  \"guard_failures\": %u\n", g_failures);
    printf("}\n");
    free(g_exe);
    return g_failures ? 3 : 0;
}
