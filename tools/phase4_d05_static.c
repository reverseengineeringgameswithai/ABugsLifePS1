/* D05 pristine-ASM guard and call-flow extractor. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LOAD_ADDR 0x80010000u
#define EXE_HEADER 0x800u
#define REINIT_ADDR 0x80049c30u

static uint32_t read_le32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t word_at(const unsigned char *image, size_t size, uint32_t va)
{
    size_t off;

    if (va < LOAD_ADDR) {
        fprintf(stderr, "address below load base: %08x\n", va);
        exit(2);
    }
    off = EXE_HEADER + (size_t)(va - LOAD_ADDR);
    if (off + 4 > size) {
        fprintf(stderr, "address outside executable: %08x\n", va);
        exit(2);
    }
    return read_le32(image + off);
}

static int is_jal_to(uint32_t pc, uint32_t insn, uint32_t target)
{
    uint32_t decoded;

    if ((insn >> 26) != 3)
        return 0;
    decoded = ((pc + 4) & 0xf0000000u) | ((insn & 0x03ffffffu) << 2);
    return decoded == target;
}

static int is_mem_offset(uint32_t insn, unsigned op, uint16_t offset)
{
    return (insn >> 26) == op && (uint16_t)insn == offset;
}

static int is_biased_mem_offset(uint32_t insn, unsigned op,
                                int base_bias, int field_offset)
{
    return (insn >> 26) == op &&
           (int)(int16_t)insn - base_bias == field_offset;
}

static int require(int condition, const char *message)
{
    if (!condition)
        fprintf(stderr, "D05 guard failed: %s\n", message);
    return condition;
}

int main(int argc, char **argv)
{
    FILE *fp;
    unsigned char *image;
    long length;
    size_t size;
    uint32_t pc;
    uint32_t callers[8];
    unsigned caller_count = 0;
    int ok = 1;

    if (argc != 2) {
        fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]);
        return 2;
    }
    fp = fopen(argv[1], "rb");
    if (!fp) {
        fprintf(stderr, "%s: %s\n", argv[1], strerror(errno));
        return 2;
    }
    if (fseek(fp, 0, SEEK_END) != 0 || (length = ftell(fp)) < 0 ||
        fseek(fp, 0, SEEK_SET) != 0) {
        fprintf(stderr, "could not size executable\n");
        fclose(fp);
        return 2;
    }
    size = (size_t)length;
    image = malloc(size);
    if (!image || fread(image, 1, size, fp) != size) {
        fprintf(stderr, "could not read executable\n");
        free(image);
        fclose(fp);
        return 2;
    }
    fclose(fp);

    for (pc = LOAD_ADDR; EXE_HEADER + (size_t)(pc - LOAD_ADDR) + 4 <= size;
         pc += 4) {
        if (is_jal_to(pc, word_at(image, size, pc), REINIT_ADDR) &&
            caller_count < sizeof callers / sizeof callers[0])
            callers[caller_count++] = pc;
    }

    ok &= require(word_at(image, size, 0x80049c2c) == 0,
                  "0x80049c2c must be padding, not the reinitializer entry");
    ok &= require(caller_count == 2, "reinitializer must have two direct callers");
    ok &= require(caller_count >= 2 && callers[0] == 0x8004a664 &&
                  callers[1] == 0x8004d3f0,
                  "unexpected reinitializer caller set");
    /* The scheduler forms 0x800a0000+slot; actor base is that value-0x280. */
    ok &= require(is_biased_mem_offset(word_at(image, size, 0x8004d294),
                                       0x21, -0x280, 0x006e),
                  "scheduler HP load at 0x8004d294 changed");
    ok &= require((word_at(image, size, 0x8004d29c) >> 26) == 0x06,
                  "scheduler HP BLEZ at 0x8004d29c changed");
    ok &= require(is_biased_mem_offset(word_at(image, size, 0x8004d398),
                                       0x21, -0x280, 0x0062),
                  "KO respawn-delay load at 0x8004d398 changed");
    ok &= require(is_jal_to(0x8004d3bc, word_at(image, size, 0x8004d3bc),
                            0x80025084),
                  "spawn visibility call at 0x8004d3bc changed");
    ok &= require(is_jal_to(0x8004d3f0, word_at(image, size, 0x8004d3f0),
                            REINIT_ADDR),
                  "runtime reinitializer call at 0x8004d3f0 changed");
    ok &= require(is_mem_offset(word_at(image, size, 0x80049ca0), 0x29, 0x006e),
                  "HP restore store at 0x80049ca0 changed");
    ok &= require(is_mem_offset(word_at(image, size, 0x80049cc0), 0x29, 0x0062),
                  "respawn-delay seed store at 0x80049cc0 changed");

    if (ok) {
        printf("D05 pristine ASM verified\n");
        printf("reinitializer entry: 0x80049c30\n");
        printf("direct callers: 0x%08x 0x%08x\n", callers[0], callers[1]);
        printf("runtime path: HP<=0 -> +0x62 delay -> 0x80025084 off-screen test -> reinit\n");
    }
    free(image);
    return ok ? 0 : 1;
}
