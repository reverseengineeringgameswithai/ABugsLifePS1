#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint16_t u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void fail(const char *message)
{
    fprintf(stderr, "phase4_d12_closure: %s\n", message);
    exit(2);
}

static uint8_t *load_file(const char *path, size_t *size)
{
    FILE *file = fopen(path, "rb");
    uint8_t *data;
    long length;

    if (file == NULL) {
        perror(path);
        exit(2);
    }
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET) != 0) {
        fail("could not size executable");
    }
    *size = (size_t)length;
    data = malloc(*size);
    if (data == NULL || fread(data, 1, *size, file) != *size) {
        fail("could not read executable");
    }
    fclose(file);
    return data;
}

static const uint8_t *at(const uint8_t *exe, size_t size,
                         uint32_t address, size_t width)
{
    uint32_t base = u32(exe + 0x18);
    uint32_t text_size = u32(exe + 0x1c);
    uint64_t relative;

    if (address < base) {
        fail("virtual address precedes executable text");
    }
    relative = (uint64_t)address - base;
    if (relative + width > text_size || 0x800u + relative + width > size) {
        fail("virtual address is outside executable text");
    }
    return exe + 0x800u + relative;
}

static void expect_word(const uint8_t *exe, size_t size,
                        uint32_t pc, uint32_t expected, const char *meaning)
{
    uint32_t actual = u32(at(exe, size, pc, 4));

    printf("PIN pc=%08x word=%08x expected=%08x ok=%s meaning=%s\n",
           pc, actual, expected, actual == expected ? "yes" : "NO", meaning);
    if (actual != expected) {
        exit(3);
    }
}

static void expect_bytes(const uint8_t *exe, size_t size, uint32_t address,
                         const uint8_t *expected, size_t width, const char *meaning)
{
    const uint8_t *actual = at(exe, size, address, width);

    printf("ROW address=%08x bytes=", address);
    for (size_t i = 0; i < width; ++i) {
        printf("%02x", actual[i]);
    }
    printf(" ok=%s meaning=%s\n",
           memcmp(actual, expected, width) == 0 ? "yes" : "NO", meaning);
    if (memcmp(actual, expected, width) != 0) {
        exit(3);
    }
}

static uint32_t jump_target(uint32_t pc, uint32_t instruction)
{
    return ((pc + 4) & 0xf0000000u) |
           ((instruction & 0x03ffffffu) << 2);
}

static unsigned count_word(const uint8_t *exe, size_t size,
                           uint32_t first, uint32_t end, uint32_t wanted)
{
    unsigned count = 0;

    for (uint32_t pc = first; pc < end; pc += 4) {
        if (u32(at(exe, size, pc, 4)) == wanted) {
            ++count;
        }
    }
    return count;
}

int main(int argc, char **argv)
{
    static const uint8_t constructor_21[20] = {
        0x05, 0x00, 0x23, 0x00, 0x64, 0x00, 0x00, 0x01, 0x3c, 0x00,
        0x3c, 0x00, 0x06, 0x00, 0x00, 0x00, 0x60, 0x50, 0x40, 0x30
    };
    static const uint8_t constructor_22[20] = {
        0x06, 0x00, 0x28, 0x00, 0x64, 0x00, 0x00, 0x01, 0x46, 0x00,
        0x46, 0x00, 0x06, 0x00, 0x00, 0x00, 0x60, 0x40, 0x30, 0x20
    };
    static const uint8_t constructor_23[20] = {
        0x05, 0x00, 0x37, 0x00, 0x64, 0x00, 0x00, 0x01, 0x50, 0x00,
        0x50, 0x00, 0x06, 0x00, 0x00, 0x00, 0x60, 0x60, 0x40, 0x20
    };
    static const uint8_t constructor_56[20] = {
        0x00, 0x00, 0x01, 0x00, 0x64, 0x00, 0x00, 0x01, 0xd0, 0x07,
        0xd0, 0x07, 0x00, 0x00, 0x00, 0x06, 0xe4, 0x7f, 0x00, 0x00
    };
    uint32_t xrefs[3] = {0, 0, 0};
    unsigned xref_count = 0;
    uint8_t *exe;
    size_t size;
    uint32_t base;
    uint32_t text_size;
    const uint8_t *mine;

    if (argc != 2) {
        fprintf(stderr, "usage: %s REBUILD/files/SCUS_942.88\n", argv[0]);
        return 2;
    }
    exe = load_file(argv[1], &size);
    if (size < 0x800 || memcmp(exe, "PS-X EXE", 8) != 0) {
        fail("input is not a PS-X EXE");
    }

    expect_bytes(exe, size, 0x800795c0, constructor_21, sizeof(constructor_21),
                 "worm burst constructor 21, action 5");
    expect_bytes(exe, size, 0x800795d4, constructor_22, sizeof(constructor_22),
                 "worm burst constructor 22, action 6");
    expect_bytes(exe, size, 0x800795e8, constructor_23, sizeof(constructor_23),
                 "worm burst constructor 23, action 5");

    expect_word(exe, size, 0x800586c4, 0x0000b021,
                "contact walker initializes damage selector s6 to zero");
    expect_word(exe, size, 0x80058814, 0x00008821,
                "contact walker initializes sound/argument s1 to zero");
    expect_word(exe, size, 0x800589d4, 0x2410000c,
                "default action handler selects terminal countdown 12");
    expect_word(exe, size, 0x80058a18, 0x24020001,
                "player-damage tail requires s6 equal to one");
    expect_word(exe, size, 0x80058a1c, 0x16c2000c,
                "default s6 zero branches around player damage");
    expect_word(exe, size, 0x80058a48, 0x0c0129c0,
                "guarded player-damage call targets 0x8004A700");
    if (count_word(exe, size, 0x800589d4, 0x80058a54, 0x24160001) != 0) {
        fail("default contact block unexpectedly arms player damage");
    }

    base = u32(exe + 0x18);
    text_size = u32(exe + 0x1c);
    for (uint32_t pc = base; pc + 4 <= base + text_size; pc += 4) {
        uint32_t instruction = u32(at(exe, size, pc, 4));
        if ((instruction >> 26) == 3 &&
            jump_target(pc, instruction) == 0x80049c30) {
            if (xref_count < 3) {
                xrefs[xref_count] = pc;
            }
            ++xref_count;
        }
    }
    printf("REINIT_XREFS count=%u pcs=", xref_count);
    for (unsigned i = 0; i < xref_count && i < 3; ++i) {
        printf("%s%08x", i == 0 ? "" : ",", xrefs[i]);
    }
    putchar('\n');
    if (xref_count != 2 || xrefs[0] != 0x8004a664 || xrefs[1] != 0x8004d3f0) {
        fail("reinitializer direct-call set changed");
    }

    expect_word(exe, size, 0x8004d3bc, 0x0c009421,
                "dead-actor gate calls camera containment predicate 0x80025084");
    expect_word(exe, size, 0x8004d3c4, 0x14400012,
                "inside containment suppresses reinitialization");
    expect_word(exe, size, 0x8004d3f0, 0x0c01270c,
                "outside containment calls actor reinitializer 0x80049C30");
    expect_word(exe, size, 0x8004d400, 0x28421388,
                "reinit delay decrement is gated below sentinel 5000");
    expect_word(exe, size, 0x8004d40c, 0xa6420062,
                "reinit delay is actor halfword +0x62, not +0x4A");
    if (count_word(exe, size, 0x80049c30, 0x80049e80, 0x91230011) != 1 ||
        count_word(exe, size, 0x80049c30, 0x80049e80, 0xa5030062) != 1) {
        fail("spawn descriptor +0x11 to actor +0x62 delay copy changed");
    }

    expect_bytes(exe, size, 0x8007987c, constructor_56, sizeof(constructor_56),
                 "Mine Plant blast constructor 56");
    mine = at(exe, size, 0x8007987c, sizeof(constructor_56));
    if ((int16_t)u16(mine + 0x0c) != 0 || mine[0x0f] != 6) {
        fail("Mine Plant class/permanence tuple changed");
    }
    expect_word(exe, size, 0x80058f00, 0x9222002c,
                "berry-tough gate reads contact damage class");
    expect_word(exe, size, 0x80058f08, 0x144a0054,
                "class other than one enters ordinary damage dispatch");
    expect_word(exe, size, 0x800590c0, 0x08016439,
                "damage class zero selects the common HP store");
    expect_word(exe, size, 0x800590c4, 0x2482fffe,
                "damage class zero subtracts two local HP");
    expect_word(exe, size, 0x80059208, 0x14620002,
                "hit marker byte is compared with Mine Plant value six");
    expect_word(exe, size, 0x80059210, 0x36f70002,
                "lethal Mine Plant hit sets permanent-death bit");

    puts("VERDICT spawned kinds 21/22/23 use the non-damaging default contact path");
    puts("VERDICT reinit caller=0x8004D3F0 gate=outside_camera_containment delay=actor+0x62");
    puts("VERDICT one Mine Plant blast applies -2 HP to worm 8->6; permanence waits for lethality");
    free(exe);
    return 0;
}
