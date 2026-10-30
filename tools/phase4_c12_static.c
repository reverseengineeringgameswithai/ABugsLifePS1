/*
 * Phase 4 C12 health-leaf static analyzer.
 *
 * Reads the hash-pinned pristine PS-X EXE directly.  It does not mutate the
 * image.  Hash verification remains an explicit prerequisite because this
 * small tool intentionally contains no cryptographic implementation.
 *
 * Usage:
 *   cc -std=c11 -O2 -Wall -Wextra -Werror \
 *      tools/phase4_c12_static.c -o /tmp/phase4_c12_static
 *   /tmp/phase4_c12_static REBUILD/files/SCUS_942.88
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    PSX_HEADER_SIZE = 0x800,
    RETAIL_LOAD_ADDRESS = 0x80010000u,
    CONTACT_META_TABLE = 0x8007941cu,
    CONTACT_META_STRIDE = 0x14u,
    CONTACT_ACTION_TABLE = 0x8001b570u,
    PROJECTILE_EFFECT_TABLE = 0x8001b790u
};

static uint16_t read_u16(const unsigned char *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t read_u32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static size_t image_offset(uint32_t va)
{
    return PSX_HEADER_SIZE + (size_t)(va - RETAIL_LOAD_ADDRESS);
}

static uint32_t word_at(const unsigned char *image, size_t size, uint32_t va)
{
    size_t offset = image_offset(va);
    if (va < RETAIL_LOAD_ADDRESS || offset + 4 > size) {
        fprintf(stderr, "address outside executable: 0x%08x\n", va);
        exit(10);
    }
    return read_u32(image + offset);
}

static void dump_metadata(const unsigned char *image, size_t size, unsigned row)
{
    uint32_t va = CONTACT_META_TABLE + row * CONTACT_META_STRIDE;
    size_t offset = image_offset(va);
    const unsigned char *p;
    unsigned i;

    if (offset + CONTACT_META_STRIDE > size) {
        fprintf(stderr, "metadata row outside executable: %u\n", row);
        exit(11);
    }
    p = image + offset;
    printf("metadata row=%u va=0x%08x bytes=", row, va);
    for (i = 0; i < CONTACT_META_STRIDE; ++i)
        printf("%02x", p[i]);
    putchar('\n');
    printf("  action=%u ttl=%d field04=%d field06=%d radius_add=%d "
           "field0a=%d effect=%d sign_select=%d field0f=%u "
           "flags=0x%02x tint=%u,%u,%u\n",
           read_u16(p), (int16_t)read_u16(p + 2),
           (int16_t)read_u16(p + 4), (int16_t)read_u16(p + 6),
           (int16_t)read_u16(p + 8), (int16_t)read_u16(p + 10),
           (int16_t)read_u16(p + 12), (int8_t)p[14], p[15], p[16],
           p[17], p[18], p[19]);
}

static void dump_control_words(const unsigned char *image, size_t size)
{
    static const struct {
        uint32_t pc;
        const char *role;
    } sites[] = {
        {0x800499a0u, "generic drop: load true health"},
        {0x800499a8u, "generic drop: health < 4 gate"},
        {0x800499bcu, "generic drop: health-indexed RNG mask"},
        {0x800499e8u, "generic drop: enemy flag load"},
        {0x80049a10u, "generic drop: allocate ctor 38"},
        {0x80058864u, "leaf pickup handler entry"},
        {0x8005887cu, "leaf pickup: load true health"},
        {0x80058890u, "leaf pickup: store health + 1"},
        {0x800589e0u, "pickup tail: state 7"},
        {0x800589e4u, "pickup tail: ttl 1"},
        {0x80059d78u, "effect 23 entry"},
        {0x80059d98u, "effect 23: load true health"},
        {0x80059decu, "effect 23: allocate ctor 38"},
        {0x80055124u, "50-grain reward health refill"},
        {0x8005b30cu, "player initialization health refill"}
    };
    size_t i;

    puts("selected pristine instruction words:");
    for (i = 0; i < sizeof sites / sizeof sites[0]; ++i)
        printf("  pc=0x%08x word=0x%08x role=%s\n", sites[i].pc,
               word_at(image, size, sites[i].pc), sites[i].role);
}

static void census_health_immediates(const unsigned char *image, size_t size)
{
    size_t offset;

    puts("direct signed-health immediate census (imm=0x6594):");
    for (offset = PSX_HEADER_SIZE; offset + 4 <= size; offset += 4) {
        uint32_t word = read_u32(image + offset);
        unsigned op = word >> 26;
        if ((word & 0xffffu) != 0x6594u)
            continue;
        if (op == 0x21 || op == 0x25 || op == 0x29) {
            uint32_t pc = RETAIL_LOAD_ADDRESS +
                          (uint32_t)(offset - PSX_HEADER_SIZE);
            const char *name = op == 0x21 ? "lh" : op == 0x25 ? "lhu" : "sh";
            printf("  pc=0x%08x word=0x%08x op=%s base=r%u rt=r%u\n",
                   pc, word, name, (word >> 21) & 31u, (word >> 16) & 31u);
        }
    }
}

int main(int argc, char **argv)
{
    static const unsigned char row38_signature[CONTACT_META_STRIDE] = {
        0x09, 0x00, 0xc8, 0x00, 0xd2, 0x00, 0x00, 0x01,
        0x64, 0x00, 0x64, 0x00, 0xd6, 0xff, 0x00, 0x00,
        0xe3, 0x80, 0x80, 0x80
    };
    FILE *file;
    long length;
    unsigned char *image;
    size_t row38_offset;
    unsigned health;
    uint32_t action50_slot, effect23_slot;

    if (argc != 2) {
        fprintf(stderr, "usage: %s PSX_EXE\n", argv[0]);
        return 2;
    }
    file = fopen(argv[1], "rb");
    if (!file) {
        perror(argv[1]);
        return 3;
    }
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return 4;
    }
    image = malloc((size_t)length);
    if (!image || fread(image, 1, (size_t)length, file) != (size_t)length) {
        fclose(file);
        free(image);
        return 5;
    }
    fclose(file);
    if ((size_t)length < PSX_HEADER_SIZE ||
        memcmp(image, "PS-X EXE", 8) != 0) {
        fprintf(stderr, "not a PS-X EXE\n");
        free(image);
        return 6;
    }

    row38_offset = image_offset(CONTACT_META_TABLE + 38u * CONTACT_META_STRIDE);
    if (row38_offset + CONTACT_META_STRIDE > (size_t)length ||
        memcmp(image + row38_offset, row38_signature,
               CONTACT_META_STRIDE) != 0) {
        fprintf(stderr, "pristine C12 row-38 signature mismatch\n");
        free(image);
        return 7;
    }

    puts("C12 health-leaf static evidence");
    dump_metadata(image, (size_t)length, 38);
    dump_metadata(image, (size_t)length, 50);
    puts("generic enemy-death leaf odds when health < 4:");
    for (health = 0; health < 4; ++health)
        printf("  health=%u mask=0x%x probability=1/%u\n", health,
               (2u << health) - 1u, 2u << health);

    action50_slot = CONTACT_ACTION_TABLE + (50u - 2u) * 4u;
    effect23_slot = PROJECTILE_EFFECT_TABLE + (23u - 1u) * 4u;
    printf("ctor50 action slot=0x%08x target=0x%08x\n", action50_slot,
           word_at(image, (size_t)length, action50_slot));
    printf("effect23 slot=0x%08x target=0x%08x\n", effect23_slot,
           word_at(image, (size_t)length, effect23_slot));
    dump_control_words(image, (size_t)length);
    census_health_immediates(image, (size_t)length);

    free(image);
    return 0;
}
