/*
 * Phase 4 D19: decode the crowd projectile constructor and berry-arm handler
 * directly from the pristine retail executable.
 *
 * Usage:
 *   cc -std=c11 -O2 -Wall -Wextra -Werror \
 *      tools/phase4_d19_type71_static.c -o /tmp/phase4_d19_type71_static
 *   /tmp/phase4_d19_type71_static REBUILD/files/SCUS_942.88
 *
 * Expected input SHA-256:
 *   1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum {
    EXE_HEADER_SIZE = 0x800,
    EXE_LOAD_VA = 0x80010000u,
    CONTACT_METADATA = 0x8007941cu,
    CONTACT_METADATA_STRIDE = 0x14,
    CONTACT_ACTION_DISPATCH = 0x8001b570u,
    TYPE_PLAYER_THROWN_RED = 2,
    TYPE_CROWD_RED_PICKUP = 71,
    ACTION_CROWD_RED_PICKUP = 32,
    ACTION_CROWD_RED_HANDLER = 0x800588fcu,
    ACTION_CROWD_RED_EQUIP_STORE = 0x80058934u
};

static uint8_t *image;
static size_t image_size;

static size_t file_offset(uint32_t va)
{
    size_t offset;

    if (va < EXE_LOAD_VA) {
        fprintf(stderr, "address below load VA: %08x\n", va);
        exit(2);
    }
    offset = EXE_HEADER_SIZE + (size_t)(va - EXE_LOAD_VA);
    if (offset + 4 > image_size) {
        fprintf(stderr, "address outside executable: %08x\n", va);
        exit(2);
    }
    return offset;
}

static uint16_t read_u16(uint32_t va)
{
    const size_t offset = file_offset(va);
    return (uint16_t)(image[offset] | ((uint16_t)image[offset + 1] << 8));
}

static uint32_t read_u32(uint32_t va)
{
    const size_t offset = file_offset(va);
    return (uint32_t)image[offset] |
           ((uint32_t)image[offset + 1] << 8) |
           ((uint32_t)image[offset + 2] << 16) |
           ((uint32_t)image[offset + 3] << 24);
}

static uint32_t row_address(unsigned type)
{
    return CONTACT_METADATA + type * CONTACT_METADATA_STRIDE;
}

static uint32_t action_handler(unsigned action)
{
    return read_u32(CONTACT_ACTION_DISPATCH + (action - 2u) * 4u);
}

int main(int argc, char **argv)
{
    FILE *input;
    uint32_t row71;
    unsigned action71;
    uint32_t handler71;
    uint32_t equip_store;

    if (argc != 2) {
        fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]);
        return 2;
    }
    input = fopen(argv[1], "rb");
    if (input == NULL) {
        perror(argv[1]);
        return 2;
    }
    if (fseek(input, 0, SEEK_END) != 0) {
        return 2;
    }
    image_size = (size_t)ftell(input);
    rewind(input);
    image = malloc(image_size);
    if (image == NULL || fread(image, 1, image_size, input) != image_size) {
        fprintf(stderr, "could not read executable\n");
        return 2;
    }
    fclose(input);

    row71 = row_address(TYPE_CROWD_RED_PICKUP);
    action71 = read_u16(row71);
    handler71 = action_handler(action71);
    equip_store = read_u32(ACTION_CROWD_RED_EQUIP_STORE);

    printf("player_thrown_red_type=%u action=%u\n",
           TYPE_PLAYER_THROWN_RED, read_u16(row_address(TYPE_PLAYER_THROWN_RED)));
    printf("crowd_type=%u row=%08x action=%u handler=%08x model=%d\n",
           TYPE_CROWD_RED_PICKUP, row71, action71, handler71,
           (int16_t)read_u16(row71 + 4));
    printf("equip_store_pc=%08x instruction=%08x target=800a6597 value=0\n",
           ACTION_CROWD_RED_EQUIP_STORE, equip_store);

    free(image);
    if (action71 != ACTION_CROWD_RED_PICKUP ||
        handler71 != ACTION_CROWD_RED_HANDLER || equip_store != 0xa0206597u) {
        fprintf(stderr, "D19 type-71 contract mismatch\n");
        return 1;
    }
    return 0;
}
