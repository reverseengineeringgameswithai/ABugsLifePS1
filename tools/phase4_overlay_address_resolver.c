/* Shared overlay-address resolver: which IMAGE owns an overlay-space address?
 *
 * The defect (engineering-specs/phase4-overlay-va-collision-finding.md): every
 * per-level overlay is loaded at the same base, so an overlay VA does not identify
 * code. The derived knowledge bases key such addresses globally -- 255 records in
 * analysis/phase3_ownership_graph.json whose whole schema is {address, semantic_ids,
 * canon} -- so anything consuming them must pick an owner arbitrarily.
 *
 * Four separate row assessments each built a one-off probe for their own row. This is
 * the shared one. It answers two questions and refuses to guess at either:
 *
 *   containment  -- which pinned images physically contain this address at all
 *   pinning      -- given (address, expected_word) constraints, which image satisfies
 *                   ALL of them; unique or it reports ambiguity
 *
 * ⚠️ An address alone is ambiguous BY CONSTRUCTION. This tool exists to make that
 * explicit and to resolve it where constraints exist -- never to pick a plausible owner.
 *
 * Build: cc -std=c11 -O2 -Wall -Wextra -Werror -o /tmp/ovlres tools/phase4_overlay_address_resolver.c
 * Usage:
 *   ovlres --selftest
 *   ovlres --contain  <spec-file> <addr> [addr...]         containment per address
 *   ovlres --pin      <spec-file> <addr>=<word> [more...]  unique-image constraint solve
 * spec-file lines: <name> <path> <hexbase>
 * Output: JSON on stdout.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define MAXIMG 64
typedef struct { char name[64]; char path[512]; uint32_t base; unsigned char *buf; long size; } Img;

static uint32_t rd32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* Is w a plausible MIPS instruction? Deliberately weak: used only to annotate, never
 * to decide ownership. A "plausible" word in the wrong image is exactly the trap. */
static int plausible(uint32_t w) {
    uint32_t op = w >> 26;
    if (w == 0) return 1;                       /* nop */
    if (op == 0) return 1;                      /* SPECIAL */
    switch (op) {                               /* common encodings */
        case 0x01: case 0x02: case 0x03: case 0x04: case 0x05: case 0x06: case 0x07:
        case 0x08: case 0x09: case 0x0A: case 0x0B: case 0x0C: case 0x0D: case 0x0E:
        case 0x0F: case 0x10: case 0x11: case 0x12:
        case 0x20: case 0x21: case 0x23: case 0x24: case 0x25:
        case 0x28: case 0x29: case 0x2B: case 0x32: case 0x3A:
            return 1;
        default: return 0;
    }
}

static int load_spec(const char *spec, Img *im) {
    FILE *f = fopen(spec, "r");
    if (!f) { fprintf(stderr, "cannot open spec %s\n", spec); return -1; }
    int n = 0; char nm[64], pa[512]; unsigned long b;
    while (n < MAXIMG && fscanf(f, "%63s %511s %lx", nm, pa, &b) == 3) {
        FILE *g = fopen(pa, "rb");
        if (!g) { fprintf(stderr, "cannot open image %s\n", pa); fclose(f); return -1; }
        fseek(g, 0, SEEK_END); long sz = ftell(g); fseek(g, 0, SEEK_SET);
        unsigned char *buf = malloc((size_t)sz);
        if (!buf || fread(buf, 1, (size_t)sz, g) != (size_t)sz) {
            fprintf(stderr, "read %s\n", pa); fclose(g); fclose(f); return -1;
        }
        fclose(g);
        snprintf(im[n].name, sizeof im[n].name, "%s", nm);
        snprintf(im[n].path, sizeof im[n].path, "%s", pa);
        im[n].base = (uint32_t)b; im[n].buf = buf; im[n].size = sz;
        n++;
    }
    fclose(f);
    return n;
}

static int contains(const Img *m, uint32_t va, uint32_t *word) {
    if (va < m->base) return 0;
    long off = (long)(va - m->base);
    if (off + 4 > m->size) return 0;
    *word = rd32(m->buf + off);
    return 1;
}

static int selftest(void) {
    int bad = 0;
    if (!plausible(0x00000000u)) bad = 1;                 /* nop */
    if (!plausible(0x3C02800Bu)) bad = 1;                 /* lui  */
    if (!plausible(0xAC204A3Cu)) bad = 1;                 /* sw   */
    if (plausible(0xFFFFFFFFu)) bad = 1;                  /* not an opcode we accept */
    Img m; m.base = 0x800B39A0; unsigned char b[8] = {0x3C,0x02,0x00,0x80, 0,0,0,0};
    m.buf = b; m.size = 8; uint32_t w = 0;
    if (!contains(&m, 0x800B39A0u, &w) || w != 0x8000023Cu) {
        /* little-endian read of 3C 02 00 80 is 0x8000023C */
        printf("{\"selftest\":\"FAIL\",\"note\":\"contains/rd32\"}\n"); return 1;
    }
    if (contains(&m, 0x800B39A8u, &w)) bad = 1;           /* past end must not contain */
    if (contains(&m, 0x800B3990u, &w)) bad = 1;           /* before base must not contain */
    printf("{\"selftest\":\"%s\"}\n", bad ? "FAIL" : "PASS");
    return bad;
}

int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--selftest")) return selftest();
    if (argc < 4) { fprintf(stderr, "usage: %s --contain|--pin <spec> <args...>\n", argv[0]); return 2; }
    int mode_pin = !strcmp(argv[1], "--pin");
    Img im[MAXIMG];
    int n = load_spec(argv[2], im);
    if (n <= 0) return 2;

    if (!mode_pin) {
        printf("{\n \"mode\": \"containment\",\n \"images\": %d,\n \"addresses\": [\n", n);
        for (int a = 3; a < argc; a++) {
            uint32_t va = (uint32_t)strtoul(argv[a], NULL, 0);
            printf("  %s{\"address\": \"0x%08X\", \"containing_images\": [", a > 3 ? ",\n" : "", va);
            int first = 1, cnt = 0, plaus = 0;
            for (int i = 0; i < n; i++) {
                uint32_t w;
                if (contains(&im[i], va, &w)) {
                    cnt++; if (plausible(w)) plaus++;
                    printf("%s{\"image\": \"%s\", \"word\": \"0x%08X\", \"plausible_insn\": %s}",
                           first ? "" : ", ", im[i].name, w, plausible(w) ? "true" : "false");
                    first = 0;
                }
            }
            printf("], \"contained_by\": %d, \"plausible_in\": %d, \"unique\": %s}",
                   cnt, plaus, cnt == 1 ? "true" : "false");
        }
        printf("\n ]\n}\n");
        return 0;
    }

    /* --pin: every constraint addr=word must hold in the SAME image */
    int survivors = 0, sole = -1;
    printf("{\n \"mode\": \"pin\",\n \"images\": %d,\n \"constraints\": %d,\n \"per_image\": [\n",
           n, argc - 3);
    for (int i = 0; i < n; i++) {
        int ok = 1, matched = 0;
        for (int a = 3; a < argc && ok; a++) {
            char tmp[128]; snprintf(tmp, sizeof tmp, "%s", argv[a]);
            char *eq = strchr(tmp, '='); if (!eq) { fprintf(stderr, "bad constraint %s\n", tmp); return 2; }
            *eq = 0;
            uint32_t va = (uint32_t)strtoul(tmp, NULL, 0);
            uint32_t want = (uint32_t)strtoul(eq + 1, NULL, 0);
            uint32_t got;
            if (!contains(&im[i], va, &got) || got != want) ok = 0; else matched++;
        }
        printf("  %s{\"image\": \"%s\", \"satisfies_all\": %s, \"matched\": %d}",
               i ? ",\n" : "", im[i].name, ok ? "true" : "false", matched);
        if (ok) { survivors++; sole = i; }
    }
    printf("\n ],\n \"survivors\": %d,\n \"unique\": %s,\n \"image\": %s%s%s\n}\n",
           survivors, survivors == 1 ? "true" : "false",
           survivors == 1 ? "\"" : "", survivors == 1 ? im[sole].name : "null",
           survivors == 1 ? "\"" : "");
    return survivors == 1 ? 0 : 1;
}
