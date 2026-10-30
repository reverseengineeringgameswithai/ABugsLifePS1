/* Phase 4 E11 offline MIPS census. Run from the repository root. */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define OVERLAY_BASE 0x800B39A0u
#define SHARED_VERTEX 0x8012C1D0u

struct input {
    const char *tag;
    const char *path;
};

static const struct input overlays[] = {
    {"L01_LEVEL", "REBUILD/files/LEVEL01/LEVEL.BIN"},
    {"L01_LEVEL1", "REBUILD/files/LEVEL01/LEVEL1.BIN"},
    {"L02_LEVEL", "REBUILD/files/LEVEL02/LEVEL.BIN"},
    {"L02_LEVEL1", "REBUILD/files/LEVEL02/LEVEL1.BIN"},
    {"L03_LEVEL", "REBUILD/files/LEVEL03/LEVEL.BIN"},
    {"L03_LEVEL1", "REBUILD/files/LEVEL03/LEVEL1.BIN"},
    {"L04_LEVEL", "REBUILD/files/LEVEL04/LEVEL.BIN"},
    {"L04_LEVEL1", "REBUILD/files/LEVEL04/LEVEL1.BIN"},
    {"L05_LEVEL", "REBUILD/files/LEVEL05/LEVEL.BIN"},
    {"L05_LEVEL1", "REBUILD/files/LEVEL05/LEVEL1.BIN"},
    {"L06_LEVEL", "REBUILD/files/LEVEL06/LEVEL.BIN"},
    {"L06_LEVEL1", "REBUILD/files/LEVEL06/LEVEL1.BIN"},
    {"L07_LEVEL", "REBUILD/files/LEVEL07/LEVEL.BIN"},
    {"L07_LEVEL1", "REBUILD/files/LEVEL07/LEVEL1.BIN"},
    {"L08_LEVEL", "REBUILD/files/LEVEL08/LEVEL.BIN"},
    {"L08_LEVEL1", "REBUILD/files/LEVEL08/LEVEL1.BIN"},
    {"L09_LEVEL", "REBUILD/files/LEVEL09/LEVEL.BIN"},
    {"L09_LEVEL1", "REBUILD/files/LEVEL09/LEVEL1.BIN"},
    {"L10_LEVEL", "REBUILD/files/LEVEL10/LEVEL.BIN"}
};

static uint16_t le16(const unsigned char *p)
{
    return (uint16_t)p[0] | (uint16_t)p[1] << 8;
}

static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static unsigned char *load(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    long n;
    unsigned char *data;

    if (!f || fseek(f, 0, SEEK_END) != 0 || (n = ftell(f)) < 0 ||
        fseek(f, 0, SEEK_SET) != 0) {
        fprintf(stderr, "cannot open %s\n", path);
        exit(2);
    }
    data = malloc((size_t)n);
    if (!data || fread(data, 1, (size_t)n, f) != (size_t)n) {
        fprintf(stderr, "cannot read %s\n", path);
        exit(2);
    }
    fclose(f);
    *size = (size_t)n;
    return data;
}

static const char *focus(uint32_t target)
{
    switch (target) {
    case 0x80029030u: return "scaled_rotation";
    case 0x800292DCu: return "rotation_apply";
    case 0x80029508u: return "pass2_transform";
    case 0x80049C30u: return "mover_init";
    case 0x8004B940u: return "mover_update";
    case 0x8004C10Cu: return "actor_state_set";
    case 0x8004A700u: return "player_damage";
    default: return NULL;
    }
}

static unsigned direct_shared_materializations(const unsigned char *data,
                                               size_t size)
{
    unsigned hits = 0;
    size_t i;

    for (i = 0; i + 36 <= size; i += 4) {
        uint32_t first = le32(data + i);
        unsigned op = first >> 26;
        unsigned reg = (first >> 16) & 31;
        size_t j;

        if (op != 0x0f || reg == 0)
            continue;
        for (j = i + 4; j <= i + 32 && j + 4 <= size; j += 4) {
            uint32_t next = le32(data + j);
            unsigned nop = next >> 26;
            unsigned rs = (next >> 21) & 31;
            unsigned rt = (next >> 16) & 31;
            uint16_t imm = (uint16_t)next;

            if (rs != reg || rt != reg)
                continue;
            if ((uint16_t)first == 0x8013 && nop == 0x09 &&
                imm == 0xc1d0)
                hits++;
            if ((uint16_t)first == 0x8012 && nop == 0x0d &&
                imm == 0xc1d0)
                hits++;
        }
    }
    return hits;
}

static void scan_overlay(const struct input *in, unsigned totals[7],
                         unsigned *shared_hits)
{
    size_t size;
    unsigned char *data = load(in->path, &size);
    size_t off;

    *shared_hits += direct_shared_materializations(data, size);
    for (off = 0; off + 4 <= size; off += 4) {
        uint32_t pc = OVERLAY_BASE + (uint32_t)off;
        uint32_t word = le32(data + off);
        uint32_t target;
        const char *name;
        unsigned slot;

        if ((word >> 26) != 3)
            continue;
        target = ((pc + 4) & 0xf0000000u) | ((word & 0x03ffffffu) << 2);
        name = focus(target);
        if (!name)
            continue;
        slot = target == 0x80029030u ? 0 : target == 0x800292DCu ? 1 :
               target == 0x80029508u ? 2 : target == 0x80049C30u ? 3 :
               target == 0x8004B940u ? 4 : target == 0x8004C10Cu ? 5 : 6;
        totals[slot]++;
        printf("CALL %-11s pc=0x%08" PRIX32 " target=0x%08" PRIX32
               " %s\n", in->tag, pc, target, name);
    }
    free(data);
}

static void dump_bug_bar_tables(void)
{
    size_t size;
    unsigned char *data = load("REBUILD/files/LEVEL04/LEVEL1.BIN", &size);
    size_t rotation = 0x800B4BECu - OVERLAY_BASE;
    size_t limits = 0x800B4C00u - OVERLAY_BASE;
    size_t targets = 0x800B4C24u - OVERLAY_BASE;
    unsigned i;

    if (targets + 16 > size) {
        fputs("Bug Bar tables outside overlay\n", stderr);
        exit(2);
    }
    fputs("ROTATION_DELTAS", stdout);
    for (i = 0; i < 10; i++)
        printf(" %d", (int16_t)le16(data + rotation + i * 2));
    fputs("\nPATH_LIMITS", stdout);
    for (i = 0; i < 6; i++)
        printf(" %d", (int16_t)le16(data + limits + i * 2));
    fputs("\nCONTROLLER_TARGETS", stdout);
    for (i = 0; i < 4; i++)
        printf(" %" PRId32, (int32_t)le32(data + targets + i * 4));
    putchar('\n');
    free(data);
}

static void check_actor_state_leaf(void)
{
    static const uint32_t expected[] = {
        0x00063080u, 0xac850044u, 0x3c018007u, 0x00260821u,
        0x8c227e28u, 0x00000000u, 0xac82004cu, 0x90420000u,
        0x00000000u, 0x00021400u, 0x03e00008u, 0xac820040u
    };
    size_t size;
    unsigned char *exe = load("REBUILD/files/SCUS_942.88", &size);
    uint32_t base;
    size_t off;
    unsigned i;
    int exact = 1;

    if (size < 0x800 || memcmp(exe, "PS-X EXE", 8) != 0) {
        fputs("bad resident executable\n", stderr);
        exit(2);
    }
    base = le32(exe + 0x18);
    off = 0x800u + (0x8004C10Cu - base);
    for (i = 0; i < sizeof(expected) / sizeof(expected[0]); i++)
        if (off + i * 4 + 4 > size || le32(exe + off + i * 4) != expected[i])
            exact = 0;
    printf("ACTOR_STATE_LEAF exact=%s writes=+0x44,+0x4C,+0x40\n",
           exact ? "yes" : "no");
    free(exe);
}

int main(void)
{
    unsigned totals[7] = {0};
    unsigned shared_hits = 0;
    size_t i;

    for (i = 0; i < sizeof(overlays) / sizeof(overlays[0]); i++)
        scan_overlay(&overlays[i], totals, &shared_hits);
    dump_bug_bar_tables();
    check_actor_state_leaf();
    printf("TOTALS scaled_rotation=%u rotation_apply=%u pass2_transform=%u "
           "mover_init=%u mover_update=%u actor_state_set=%u player_damage=%u\n",
           totals[0], totals[1], totals[2], totals[3], totals[4], totals[5],
           totals[6]);
    printf("DIRECT_SHARED_VERTEX_MATERIALIZATIONS address=0x%08X count=%u\n",
           SHARED_VERTEX, shared_hits);
    return 0;
}
