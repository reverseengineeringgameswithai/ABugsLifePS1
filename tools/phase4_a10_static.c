#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint32_t *words; size_t count; uint32_t base; } Image;
typedef struct { int known; uint32_t value; } Known;

static int writes_register(uint32_t word, int reg) {
    unsigned op = word >> 26, rt = (word >> 16) & 31, rd = (word >> 11) & 31;
    if (op == 0) {
        unsigned fn = word & 63;
        int alu = fn == 0 || fn == 2 || fn == 3 || fn == 4 || fn == 6 || fn == 7 ||
                  fn == 0x20 || fn == 0x21 || fn == 0x22 || fn == 0x23 ||
                  fn == 0x24 || fn == 0x25 || fn == 0x26 || fn == 0x27 ||
                  fn == 0x2a || fn == 0x2b;
        return alu && rd == (unsigned)reg;
    }
    if (op == 2 || op == 4 || op == 5 || op == 6 || op == 7 ||
        op == 0x28 || op == 0x29 || op == 0x2a || op == 0x2b || op == 0x2e)
        return 0;
    if (op == 3)
        return reg == 31;
    return rt == (unsigned)reg;
}

static Known evaluate(const Image *image, long at, int reg, int depth) {
    if (reg == 0) return (Known){1, 0};
    if (depth > 10) return (Known){0, 0};
    for (long i = at; i >= 0 && at - i < 40; i--) {
        uint32_t word = image->words[i];
        if (!writes_register(word, reg)) continue;
        unsigned op = word >> 26, rs = (word >> 21) & 31;
        unsigned rt = (word >> 16) & 31, rd = (word >> 11) & 31, fn = word & 63;
        int16_t simm = (int16_t)word;
        uint16_t uimm = (uint16_t)word;
        if (op == 0x0f && rt == (unsigned)reg)
            return (Known){1, (uint32_t)uimm << 16};
        if ((op == 0x08 || op == 0x09) && rt == (unsigned)reg) {
            Known a = evaluate(image, i - 1, rs, depth + 1);
            return a.known ? (Known){1, a.value + (int32_t)simm} : (Known){0, 0};
        }
        if (op == 0x0d && rt == (unsigned)reg) {
            Known a = evaluate(image, i - 1, rs, depth + 1);
            return a.known ? (Known){1, a.value | uimm} : (Known){0, 0};
        }
        if (op == 0 && rd == (unsigned)reg &&
            (fn == 0x20 || fn == 0x21 || fn == 0x23 || fn == 0x25)) {
            Known a = evaluate(image, i - 1, rs, depth + 1);
            Known b = evaluate(image, i - 1, rt, depth + 1);
            if (!a.known || !b.known) return (Known){0, 0};
            if (fn == 0x23) return (Known){1, a.value - b.value};
            if (fn == 0x25) return (Known){1, a.value | b.value};
            return (Known){1, a.value + b.value};
        }
        return (Known){0, 0};
    }
    return (Known){0, 0};
}

static int is_memory(unsigned op) {
    return op == 0x20 || op == 0x21 || op == 0x23 || op == 0x24 ||
           op == 0x25 || op == 0x28 || op == 0x29 || op == 0x2b;
}
static const char *memory_name(unsigned op) {
    switch (op) {
        case 0x20: return "lb"; case 0x21: return "lh"; case 0x23: return "lw";
        case 0x24: return "lbu"; case 0x25: return "lhu"; case 0x28: return "sb";
        case 0x29: return "sh"; case 0x2b: return "sw"; default: return "mem";
    }
}
static uint32_t read32(const uint8_t *p) { uint32_t value; memcpy(&value, p, 4); return value; }

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: %s PSX_EXE\n", argv[0]); return 2; }
    FILE *file = fopen(argv[1], "rb");
    if (!file) { perror(argv[1]); return 1; }
    fseek(file, 0, SEEK_END); long file_size = ftell(file); rewind(file);
    uint8_t *bytes = malloc((size_t)file_size);
    if (!bytes || fread(bytes, 1, (size_t)file_size, file) != (size_t)file_size) return 1;
    fclose(file);
    if (file_size < 0x800 || memcmp(bytes, "PS-X EXE", 8)) return 1;
    Image image = {.base = read32(bytes + 0x18)};
    uint32_t text_bytes = read32(bytes + 0x1c);
    if ((uint64_t)0x800 + text_bytes > (uint64_t)file_size) return 1;
    image.words = (uint32_t *)(bytes + 0x800);
    image.count = text_bytes / 4;
    const uint32_t targets[] = {0x800a65a3, 0x800a655c, 0x800a6580, 0x800a6582};
    printf("load=0x%08x bytes=%u instructions=%zu\n", image.base, text_bytes, image.count);
    for (size_t i = 0; i < image.count; i++) {
        uint32_t word = image.words[i]; unsigned op = word >> 26;
        if (!is_memory(op)) continue;
        unsigned base_reg = (word >> 21) & 31, value_reg = (word >> 16) & 31;
        Known base = evaluate(&image, (long)i - 1, base_reg, 0);
        if (!base.known) continue;
        uint32_t address = base.value + (int32_t)(int16_t)word;
        for (size_t t = 0; t < sizeof(targets) / sizeof(targets[0]); t++) {
            if (address != targets[t]) continue;
            uint32_t pc = image.base + (uint32_t)i * 4;
            printf("target=0x%08x pc=0x%08x %s r%u,%d(r%u) word=0x%08x\n",
                   address, pc, memory_name(op), value_reg, (int16_t)word, base_reg, word);
            size_t lo = i > 5 ? i - 5 : 0, hi = i + 6 < image.count ? i + 6 : image.count;
            for (size_t j = lo; j < hi; j++)
                printf("  %c 0x%08x 0x%08x\n", j == i ? '>' : ' ',
                       image.base + (uint32_t)j * 4, image.words[j]);
        }
    }
    free(bytes);
    return 0;
}
