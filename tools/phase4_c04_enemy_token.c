/* Phase 4 C04: enemy-token quota static closure.
 *
 * C-only offline verifier for the pristine executable, level overlays, and
 * BITS/MEMORY.BIN. It pins the constructor/death/results/goal evidence and
 * performs a linear constant-address census of direct accesses to 0x800A658E.
 * Pointer-indirect accesses whose base is loaded from RAM are outside this
 * census and are not claimed against.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_c04_enemy_token.c \
 *      -o /tmp/c04_enemy_token
 *   /tmp/c04_enemy_token
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_BASE 0x80010000u
#define EXE_SKIP 0x800u
#define OVL_BASE 0x800B39A0u
#define MEM_BASE 0x800B5788u
#define QUOTA    0x800A658Eu

struct image {
    char path[160];
    uint8_t *buf;
    size_t size, skip;
    uint32_t base;
};
static struct image images[64];
static size_t nimages;

struct pin {
    const char *path;
    uint32_t va, word;
    const char *role;
};

static const struct pin pins[] = {
    {"REBUILD/files/SCUS_942.88", 0x800498F8u, 0x94620000u, "resident death path A reads quota"},
    {"REBUILD/files/SCUS_942.88", 0x80049904u, 0xA4620000u, "resident death path A stores quota-1"},
    {"REBUILD/files/SCUS_942.88", 0x800592F4u, 0x94620000u, "resident death path B reads quota"},
    {"REBUILD/files/SCUS_942.88", 0x80059300u, 0xA4620000u, "resident death path B stores quota-1"},
    {"REBUILD/files/SCUS_942.88", 0x80052CC8u, 0x84A5658Eu, "HUD computes total-remaining"},
    {"REBUILD/files/SCUS_942.88", 0x8005BAA4u, 0x0C011AC8u, "scene reset calls quota constructor 0x80046B20"},
    {"REBUILD/files/SCUS_942.88", 0x8005BADCu, 0x8442658Eu, "scene reset reads rebuilt quota"},
    {"REBUILD/files/SCUS_942.88", 0x8005BAE4u, 0xAC222258u, "scene reset snapshots initial total at 0x80082258"},
    {"REBUILD/files/SCUS_942.88", 0x8004AE94u, 0x9623005Cu, "interaction path reads actor flags +0x5C"},
    {"REBUILD/files/SCUS_942.88", 0x8004B0C4u, 0x30620800u, "actor flag 0x0800 test"},
    {"REBUILD/files/SCUS_942.88", 0x8004B0C8u, 0x1440016Cu, "0x0800 set bypasses interaction/update tail"},

    {"REBUILD/files/BITS/MEMORY.BIN", 0x800B7E04u, 0x8442658Eu, "results entry reads quota"},
    {"REBUILD/files/BITS/MEMORY.BIN", 0x800B7E18u, 0xA420658Eu, "results entry clamps negative quota to zero"},
    {"REBUILD/files/BITS/MEMORY.BIN", 0x800B7E2Cu, 0x8463658Eu, "results target reads remaining"},
    {"REBUILD/files/BITS/MEMORY.BIN", 0x800B7E4Cu, 0x00431023u, "defeated = initial total - remaining"},
    {"REBUILD/files/BITS/MEMORY.BIN", 0x800B7F14u, 0x8442658Eu, "enemy bonus requires remaining == 0"},

    {"REBUILD/files/LEVEL01/LEVEL1.BIN", 0x800B3F50u, 0x00009021u, "Bird Nest progress edge starts s2=0"},
    {"REBUILD/files/LEVEL01/LEVEL1.BIN", 0x800B3FBCu, 0x24120001u, "matching progress edge sets s2=1"},
    {"REBUILD/files/LEVEL01/LEVEL1.BIN", 0x800B40A8u, 0x84620000u, "Bird Nest reads quota"},
    {"REBUILD/files/LEVEL01/LEVEL1.BIN", 0x800B40B0u, 0x14520009u, "cleanup requires quota == s2"},
    {"REBUILD/files/LEVEL01/LEVEL1.BIN", 0x800B40C4u, 0xA4600000u, "conditional quota cleanup to zero"},
    {"REBUILD/files/LEVEL01/LEVEL1.BIN", 0x800B4100u, 0xA42223A0u, "objective latch store is downstream of quota branch"},

    {"REBUILD/files/LEVEL02/LEVEL.BIN", 0x800B4078u, 0x28420015u, "boss completion threshold HP < 21"},
    {"REBUILD/files/LEVEL02/LEVEL.BIN", 0x800B4164u, 0xA420658Eu, "selector 3 boss path zeros quota"},
    {"REBUILD/files/LEVEL02/LEVEL.BIN", 0x800B4190u, 0xA42223A0u, "boss objective latch"},
    {"REBUILD/files/LEVEL02/LEVEL1.BIN", 0x800B3CA8u, 0x94830000u, "overlay batch path reads quota"},
    {"REBUILD/files/LEVEL02/LEVEL1.BIN", 0x800B3CDCu, 0x2463FFF9u, "overlay batch adjustment is -7"},
    {"REBUILD/files/LEVEL02/LEVEL1.BIN", 0x800B3CE0u, 0xA4830000u, "overlay stores adjusted quota"},
    {"REBUILD/files/LEVEL03/LEVEL1.BIN", 0x800B3E18u, 0x84620000u, "level 3 goal path reads quota"},
    {"REBUILD/files/LEVEL03/LEVEL1.BIN", 0x800B3E34u, 0xA4600000u, "level 3 conditional cleanup zero"},
    {"REBUILD/files/LEVEL04/LEVEL1.BIN", 0x800B3E4Cu, 0xA420658Eu, "level 4 conditional cleanup zero"},
    {"REBUILD/files/LEVEL05/LEVEL1.BIN", 0x800B3B74u, 0x95020000u, "level 5 overlay reads quota"},
    {"REBUILD/files/LEVEL05/LEVEL1.BIN", 0x800B3BA0u, 0x2442FFFFu, "level 5 overlay decrement"},
    {"REBUILD/files/LEVEL05/LEVEL1.BIN", 0x800B3BD0u, 0xA5020000u, "level 5 overlay stores quota-1"},
    {"REBUILD/files/LEVEL05/LEVEL1.BIN", 0x800B42B0u, 0xA420658Eu, "level 5 goal cleanup zero"},
    {"REBUILD/files/LEVEL08/LEVEL.BIN", 0x800B3B64u, 0x84830000u, "level 8 reads quota"},
    {"REBUILD/files/LEVEL08/LEVEL.BIN", 0x800B3B78u, 0xA4820000u, "level 8 normalizes 57 to 56"},
    {"REBUILD/files/LEVEL09/LEVEL.BIN", 0x800B3C48u, 0x94620000u, "level 9 overlay reads quota"},
    {"REBUILD/files/LEVEL09/LEVEL.BIN", 0x800B3C54u, 0x2442FFFFu, "level 9 overlay decrement"},
    {"REBUILD/files/LEVEL09/LEVEL.BIN", 0x800B3C58u, 0xA4620000u, "level 9 overlay stores quota-1"},
};

static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static int load_image(const char *path, uint32_t base, size_t skip, int required)
{
    FILE *f = fopen(path, "rb");
    long n;
    struct image *im;
    if (!f) {
        if (required) perror(path);
        return required ? -1 : 0;
    }
    if (fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0) { fclose(f); return -1; }
    rewind(f);
    if (nimages == sizeof images / sizeof images[0]) { fclose(f); return -1; }
    im = &images[nimages];
    snprintf(im->path, sizeof im->path, "%s", path);
    im->buf = malloc((size_t)n);
    im->size = (size_t)n;
    im->skip = skip;
    im->base = base;
    if (!im->buf || fread(im->buf, 1, im->size, f) != im->size) { fclose(f); return -1; }
    fclose(f);
    nimages++;
    return 1;
}

static struct image *find_image(const char *path)
{
    for (size_t i = 0; i < nimages; i++)
        if (!strcmp(images[i].path, path)) return &images[i];
    return NULL;
}

static int pin_all(void)
{
    size_t ok = 0, total = sizeof pins / sizeof pins[0];
    for (size_t i = 0; i < total; i++) {
        struct image *im = find_image(pins[i].path);
        uint32_t got = 0;
        int good = 0;
        if (im && pins[i].va >= im->base) {
            size_t off = im->skip + (size_t)(pins[i].va - im->base);
            if (off + 4 <= im->size) {
                got = rd32(im->buf + off);
                good = got == pins[i].word;
            }
        }
        ok += (size_t)good;
        printf("%s %08" PRIx32 " want %08" PRIx32 " got %08" PRIx32 "  %s\n",
               good ? "ok  " : "FAIL", pins[i].va, pins[i].word, got, pins[i].role);
    }
    printf("pins: %zu/%zu\n", ok, total);
    return ok == total ? 0 : 1;
}

static int quota_census(void)
{
    int total = 0;
    puts("\nDirect constant-address quota access census:");
    for (size_t k = 0; k < nimages; k++) {
        struct image *im = &images[k];
        uint32_t value[32] = {0};
        unsigned known[32] = {0};
        size_t clear_at = (size_t)-1;
        known[0] = 1;
        for (size_t off = im->skip, index = 0; off + 4 <= im->size; off += 4, index++) {
            uint32_t w = rd32(im->buf + off);
            unsigned op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
            unsigned rd = (w >> 11) & 31, fn = w & 63;
            int16_t imm = (int16_t)w;
            uint32_t pc = im->base + (uint32_t)(off - im->skip);
            if (index == clear_at) {
                memset(known, 0, sizeof known);
                known[0] = 1;
            }
            if (((op >= 32 && op <= 38) || (op >= 40 && op <= 46)) && known[rs]) {
                uint32_t ea = value[rs] + (int32_t)imm;
                if (ea == QUOTA) {
                    int store = op >= 40;
                    printf("  %-5s %08" PRIx32 "  %-34s %s\n",
                           store ? "STORE" : "load", pc, im->path,
                           store ? "quota writer" : "quota reader");
                    total++;
                }
            }
            if (op >= 32 && op <= 38) known[rt] = 0;
            else if (op == 15) { known[rt] = 1; value[rt] = (w & 0xffffu) << 16; }
            else if (op == 9 && known[rs]) { known[rt] = 1; value[rt] = value[rs] + (int32_t)imm; }
            else if (op == 13 && known[rs]) { known[rt] = 1; value[rt] = value[rs] | (w & 0xffffu); }
            else if (op == 0 && fn == 33 && known[rs] && known[rt]) {
                known[rd] = 1;
                value[rd] = value[rs] + value[rt];
            } else if (op == 0 && fn == 8) clear_at = index + 2;
            else if (op == 0 && rd) known[rd] = 0;
            else if (op >= 8 && op <= 14 && rt) known[rt] = 0;
            known[0] = 1;
            value[0] = 0;
        }
    }
    printf("direct accesses: %d (expected 26; constructor pointer writes are additional)\n", total);
    return total == 26 ? 0 : 1;
}

int main(void)
{
    char path[160];
    int rc = 0;
    if (load_image("REBUILD/files/SCUS_942.88", EXE_BASE, EXE_SKIP, 1) < 0) return 2;
    for (int level = 0; level <= 20; level++) {
        snprintf(path, sizeof path, "REBUILD/files/LEVEL%02d/LEVEL.BIN", level);
        if (load_image(path, OVL_BASE, 0, 0) < 0) return 2;
        snprintf(path, sizeof path, "REBUILD/files/LEVEL%02d/LEVEL1.BIN", level);
        if (load_image(path, OVL_BASE, 0, 0) < 0) return 2;
    }
    if (load_image("REBUILD/files/BITS/MEMORY.BIN", MEM_BASE, 0, 1) < 0) return 2;
    printf("images loaded: %zu\n\n", nimages);
    rc |= pin_all();
    rc |= quota_census();
    puts("\nC04 boundary: constructor/rebuild, initial-total snapshot, resident decrements,");
    puts("overlay adjustments, results evaluation, and representative objective cleanup");
    puts("are pinned. A campaign-wide live value census and a human-facing name for");
    puts("scene-data flag 0x0800 are bounded residuals, not missing mechanism edges.");
    for (size_t i = 0; i < nimages; i++) free(images[i].buf);
    return rc;
}
