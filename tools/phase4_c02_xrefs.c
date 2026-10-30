#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int target(uint32_t a, const char **name) {
    if (a == 0x800a65a0u) { *name = "bonus_byte"; return 1; }
    if (a == 0x800a65a1u) { *name = "grain_count"; return 1; }
    if (a == 0x800a6594u) { *name = "reward_latch"; return 1; }
    if (a == 0x800a7e2au) { *name = "health"; return 1; }
    if (a >= 0x800b0188u && a <= 0x800b0191u) { *name = "reward_hud"; return 1; }
    if (a >= 0x80090b80u && a <= 0x80090b93u) { *name = "reward_effect"; return 1; }
    return 0;
}

static const char *memop(unsigned op) {
    switch (op) {
    case 0x20: return "lb"; case 0x21: return "lh"; case 0x23: return "lw";
    case 0x24: return "lbu"; case 0x25: return "lhu";
    case 0x28: return "sb"; case 0x29: return "sh"; case 0x2b: return "sw";
    default: return NULL;
    }
}

int main(int argc, char **argv) {
    const char *path = argc > 1 ? argv[1] : "REBUILD/files/SCUS_942.88";
    FILE *fp = fopen(path, "rb");
    if (!fp) { fprintf(stderr, "%s: %s\n", path, strerror(errno)); return 1; }
    if (fseek(fp, 0, SEEK_END) != 0) return 1;
    long file_len = ftell(fp);
    if (file_len < 0x800 || fseek(fp, 0, SEEK_SET) != 0) return 1;
    uint8_t *file = malloc((size_t)file_len);
    if (!file || fread(file, 1, (size_t)file_len, fp) != (size_t)file_len) return 1;
    fclose(fp);
    if (memcmp(file, "PS-X EXE", 8) != 0) { fprintf(stderr, "not PS-X EXE\n"); return 1; }
    uint32_t load = le32(file + 0x18), text_size = le32(file + 0x1c);
    if ((uint64_t)0x800 + text_size > (uint64_t)file_len) return 1;

    uint32_t value[32] = {0};
    unsigned known[32] = {0};
    unsigned hits = 0;
    for (uint32_t off = 0; off + 4 <= text_size; off += 4) {
        uint32_t w = le32(file + 0x800 + off), pc = load + off;
        unsigned op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int16_t simm = (int16_t)w;
        const char *m = memop(op);
        if (m && known[rs]) {
            uint32_t ea = value[rs] + (int32_t)simm;
            const char *name;
            if (target(ea, &name)) {
                printf("%s pc=0x%08" PRIx32 " op=%s addr=0x%08" PRIx32
                       " width=%u word=%08" PRIx32 " base=r%u data=r%u\n",
                       name, pc, m, ea,
                       (op == 0x20 || op == 0x24 || op == 0x28) ? 1u :
                       (op == 0x21 || op == 0x25 || op == 0x29) ? 2u : 4u,
                       w, rs, rt);
                ++hits;
            }
        }

        if (op == 0x0f) {
            known[rt] = 1;
            value[rt] = (uint32_t)(w & 0xffffu) << 16;
        } else if ((op == 0x09 || op == 0x08) && known[rs]) {
            known[rt] = 1;
            value[rt] = value[rs] + (int32_t)simm;
        } else if (op == 0x0d && known[rs]) {
            known[rt] = 1;
            value[rt] = value[rs] | (w & 0xffffu);
        } else if (m) {
            if (op <= 0x25) known[rt] = 0;
        } else if (op == 0 && (w & 0x3fu) == 0x21u) {
            unsigned rd = (w >> 11) & 31, rtv = (w >> 16) & 31;
            if (known[rs] && rtv == 0) { known[rd] = 1; value[rd] = value[rs]; }
            else if (known[rtv] && rs == 0) { known[rd] = 1; value[rd] = value[rtv]; }
            else known[rd] = 0;
        } else if (op == 0 && ((w >> 11) & 31) != 0) {
            known[(w >> 11) & 31] = 0;
        } else if (op != 0x02 && op != 0x03 && op != 0x04 && op != 0x05 &&
                   op != 0x06 && op != 0x07 && op != 0x01 && rt != 0) {
            known[rt] = 0;
        }
        known[0] = 1; value[0] = 0;
    }
    printf("summary hits=%u load=0x%08" PRIx32 " text_size=%" PRIu32 "\n", hits, load, text_size);
    free(file);
    return 0;
}
