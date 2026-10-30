#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { EXE_HEADER = 0x800, EXE_BASE = 0x80010000u, OVL_BASE = 0x800b5788u };

typedef struct { uint8_t *p; size_t n; } Image;

static Image load(const char *path) {
    Image im = {0};
    FILE *f = fopen(path, "rb");
    long n;
    if (!f || fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) {
        perror(path); exit(2);
    }
    im.n = (size_t)n;
    im.p = malloc(im.n);
    if (!im.p || fread(im.p, 1, im.n, f) != im.n) { fprintf(stderr, "short read: %s\n", path); exit(2); }
    fclose(f);
    return im;
}

static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t word(const Image *im, uint32_t va, uint32_t base, size_t header) {
    size_t off;
    if (va < base) { fprintf(stderr, "VA below base: %08" PRIx32 "\n", va); exit(2); }
    off = header + (size_t)(va - base);
    if (off + 4 > im->n) { fprintf(stderr, "VA outside image: %08" PRIx32 "\n", va); exit(2); }
    return le32(im->p + off);
}

static unsigned count_imm(const Image *im, uint32_t lo, uint32_t hi, uint32_t base,
                          size_t header, uint16_t imm) {
    unsigned n = 0;
    for (uint32_t pc = lo; pc < hi; pc += 4)
        if ((word(im, pc, base, header) & 0xffffu) == imm) ++n;
    return n;
}

static unsigned count_jal(const Image *im, uint32_t lo, uint32_t hi, uint32_t base,
                          size_t header, uint32_t target) {
    unsigned n = 0;
    uint32_t want = 0x0c000000u | ((target & 0x0fffffffu) >> 2);
    for (uint32_t pc = lo; pc < hi; pc += 4)
        if (word(im, pc, base, header) == want) ++n;
    return n;
}

static int pin(const Image *im, uint32_t va, uint32_t want, uint32_t base,
               size_t header, const char *name) {
    uint32_t got = word(im, va, base, header);
    printf("%s pc=%08" PRIx32 " want=%08" PRIx32 " got=%08" PRIx32 " %s\n",
           got == want ? "OK" : "FAIL", va, want, got, name);
    return got != want;
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s SCUS_942.88 BITS/MEMORY.BIN\n", argv[0]);
        return 2;
    }
    Image exe = load(argv[1]), ovl = load(argv[2]);
    int bad = 0;

    struct P { uint32_t va, w; const char *name; } pins[] = {
        {0x80051d08, 0x24843988, "marker FLIK source"},
        {0x80051d34, 0x30c60002, "marker FLIK bit 2"},
        {0x80051d3c, 0x24840b68, "marker enemy source"},
        {0x80051d68, 0x30c60004, "marker enemy bit 4"},
        {0x80051d70, 0x24840b80, "marker grain source"},
        {0x80051d9c, 0x30c60001, "marker grain bit 1"},

        {0x800b7e58, 0x24020032, "results grain == 50"},
        {0x800b7e7c, 0x30620001, "results grain tests bit 1"},
        {0x800b7e94, 0x34620001, "results grain sets bit 1"},
        {0x800b7eb4, 0x906365a2, "results reads FLIK mask"},
        {0x800b7eb8, 0x2402000f, "results FLIK == 0x0f"},
        {0x800b7edc, 0x30620002, "results FLIK tests bit 2"},
        {0x800b7ef4, 0x34620002, "results FLIK sets bit 2"},
        {0x800b7f14, 0x8442658e, "results reads enemy remaining"},
        {0x800b7f3c, 0x30620004, "results enemies test bit 4"},
        {0x800b7f54, 0x34620004, "results enemies sets bit 4"},
        {0x800b7eac, 0xac2923e4, "newly-earned save flag"},
    };
    for (size_t i = 0; i < sizeof pins / sizeof pins[0]; ++i) {
        int overlay = pins[i].va >= OVL_BASE;
        bad |= pin(overlay ? &ovl : &exe, pins[i].va, pins[i].w,
                   overlay ? OVL_BASE : EXE_BASE, overlay ? 0 : EXE_HEADER, pins[i].name);
    }

    unsigned movie_array = count_imm(&exe, 0x800502c4, 0x8005044c, EXE_BASE, EXE_HEADER, 0xb878);
    unsigned movie_seven = count_imm(&exe, 0x800502c4, 0x8005044c, EXE_BASE, EXE_HEADER, 7);
    unsigned serializer_array = count_imm(&exe, 0x80055478, 0x80055538, EXE_BASE, EXE_HEADER, 0xb878);
    unsigned deserializer_array = count_imm(&exe, 0x80055538, 0x80055620, EXE_BASE, EXE_HEADER, 0xb878);
    unsigned save_ser = count_jal(&ovl, 0x800b8acc, 0x800b8b60, OVL_BASE, 0, 0x80055478);
    unsigned save_des = count_jal(&ovl, 0x800b8acc, 0x800b8b60, OVL_BASE, 0, 0x80055538);

    unsigned flag_loads = 0;
    for (size_t off = 0; off + 4 <= ovl.n; off += 4) {
        uint32_t w = le32(ovl.p + off), op = w >> 26;
        if ((w & 0xffffu) == 0x23e4u && (op == 0x20 || op == 0x21 || op == 0x23 ||
                                         op == 0x24 || op == 0x25)) ++flag_loads;
    }

    printf("CHAIN movie_consumer_array_refs=%u movie_consumer_imm7=%u\n", movie_array, movie_seven);
    printf("CHAIN serializer_array_refs=%u deserializer_array_refs=%u\n",
           serializer_array, deserializer_array);
    printf("CHAIN save_trigger_loads=%u save_calls_serializer=%u save_calls_deserializer=%u\n",
           flag_loads, save_ser, save_des);
    printf("CHAIN bit_union=0x%02x expected_full=0x07\n", 1 | 2 | 4);

    bad |= movie_array == 0 || movie_seven == 0;
    bad |= serializer_array == 0 || deserializer_array == 0;
    bad |= flag_loads != 1 || save_ser != 1 || save_des != 1;
    free(exe.p); free(ovl.p);
    printf("C05_CLOSURE %s\n", bad ? "FAIL" : "PASS");
    return bad ? 1 : 0;
}
