/* Who can enter the finalizer block 0x8004FF14..0x8004FF50?
 *
 * The F01 original-oracle replay observed 0x8004FF48 (`jal 0x80045A60`, the transition
 * finalizer) executing 326 times during the frontend while 0x8004FF14 and 0x8004FF28 --
 * both on the only straight-line path to it -- executed ZERO times. Control therefore
 * entered that block by some path other than the guarded fall-through.
 *
 * This probe answers the static half exactly: over every supplied image, decode every
 * MIPS branch/jump and report each one whose DIRECT target lands inside the block, plus
 * the count of indirect (jr/jalr) sites that a direct scan cannot resolve.
 *
 * Compiled C owns instruction decoding here (operator standing rule); Python owns
 * identity and pinning. No disassembly text is parsed.
 *
 * Build: cc -std=c11 -O2 -Wall -Wextra -Werror -o /tmp/f01_entry tools/phase4_f01_finalizer_entry_probe.c
 * Usage: f01_entry --selftest
 *        f01_entry LO HI <path>:<va_base> [<path>:<va_base> ...]
 * Output: JSON on stdout.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef struct { uint32_t va; uint32_t word; uint32_t target; const char *kind; } Hit;

static uint32_t rd32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* Decode a direct branch/jump target. Returns 1 and sets tgt and kind, else 0.
 * Indirect (jr/jalr) sets kind and returns 2 with no target. */
static int direct_target(uint32_t va, uint32_t w, uint32_t *tgt, const char **kind) {
    uint32_t op = w >> 26;
    uint32_t rt = (w >> 16) & 0x1F;
    int16_t  simm = (int16_t)(w & 0xFFFF);
    if (op == 0x00) {                       /* SPECIAL */
        uint32_t fn = w & 0x3F;
        if (fn == 0x08) { *kind = "jr";   return 2; }
        if (fn == 0x09) { *kind = "jalr"; return 2; }
        return 0;
    }
    if (op == 0x02 || op == 0x03) {         /* j / jal */
        *tgt = (va & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2);
        *kind = (op == 0x02) ? "j" : "jal";
        return 1;
    }
    /* beq/bne/blez/bgtz, and REGIMM bltz/bgez/bltzal/bgezal */
    if (op == 0x04 || op == 0x05 || op == 0x06 || op == 0x07 || op == 0x01) {
        *tgt = va + 4 + ((int32_t)simm * 4);
        if (op == 0x01) *kind = (rt & 1) ? "bgez" : "bltz";
        else if (op == 0x04) *kind = "beq";
        else if (op == 0x05) *kind = "bne";
        else if (op == 0x06) *kind = "blez";
        else *kind = "bgtz";
        return 1;
    }
    return 0;
}

static int selftest(void) {
    uint32_t t; const char *k; int rc; int bad = 0;
    /* jal 0x80045A60 encoded at 0x8004FF48 == 0x0C011698 */
    rc = direct_target(0x8004FF48u, 0x0C011698u, &t, &k);
    if (rc != 1 || t != 0x80045A60u || strcmp(k, "jal")) { printf("selftest jal FAIL %u %08x %s\n", rc, t, k); bad = 1; }
    /* beq v1,v0,0x8004FF50 at 0x8004FF30 == 0x10620007 */
    rc = direct_target(0x8004FF30u, 0x10620007u, &t, &k);
    if (rc != 1 || t != 0x8004FF50u || strcmp(k, "beq")) { printf("selftest beq FAIL %u %08x %s\n", rc, t, k); bad = 1; }
    /* bnez v0,0x8004FF50 at 0x8004FF40 == 0x14400003 */
    rc = direct_target(0x8004FF40u, 0x14400003u, &t, &k);
    if (rc != 1 || t != 0x8004FF50u || strcmp(k, "bne")) { printf("selftest bne FAIL %u %08x %s\n", rc, t, k); bad = 1; }
    /* jr $ra == 0x03E00008 -> indirect */
    rc = direct_target(0x80000000u, 0x03E00008u, &t, &k);
    if (rc != 2 || strcmp(k, "jr")) { printf("selftest jr FAIL %u %s\n", rc, k); bad = 1; }
    /* a non-branch must not decode */
    rc = direct_target(0x80000000u, 0x00000000u, &t, &k);
    if (rc != 0) { printf("selftest nop FAIL %d\n", rc); bad = 1; }
    printf("{\"selftest\":\"%s\"}\n", bad ? "FAIL" : "PASS");
    return bad;
}

int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--selftest")) return selftest();
    if (argc < 4) { fprintf(stderr, "usage: %s LO HI <path>:<va_base> ...\n", argv[0]); return 2; }
    uint32_t lo = (uint32_t)strtoul(argv[1], NULL, 0);
    uint32_t hi = (uint32_t)strtoul(argv[2], NULL, 0);

    Hit hits[512]; size_t nhits = 0;
    unsigned long long indirect = 0, scanned = 0; size_t images = 0;

    printf("{\n \"block\": {\"lo\": \"0x%08x\", \"hi\": \"0x%08x\"},\n \"images\": [\n", lo, hi);
    for (int i = 3; i < argc; i++) {
        char spec[4096]; snprintf(spec, sizeof spec, "%s", argv[i]);
        char *colon = strrchr(spec, ':');
        if (!colon) { fprintf(stderr, "bad spec %s\n", spec); return 2; }
        *colon = 0;
        uint32_t base = (uint32_t)strtoul(colon + 1, NULL, 0);
        FILE *f = fopen(spec, "rb");
        if (!f) { fprintf(stderr, "cannot open %s\n", spec); return 2; }
        fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
        unsigned char *buf = malloc((size_t)sz);
        if (!buf || fread(buf, 1, (size_t)sz, f) != (size_t)sz) { fprintf(stderr, "read %s\n", spec); return 2; }
        fclose(f);
        long start = 0;
        /* PS-EXE: 0x800-byte header, text VA at +0x18 */
        if (sz > 0x800 && !memcmp(buf, "PS-X EXE", 8)) { base = rd32(buf + 0x18); start = 0x800; }
        unsigned long long im_ind = 0; size_t im_hits = 0;
        for (long o = start; o + 4 <= sz; o += 4) {
            uint32_t va = base + (uint32_t)(o - start);
            uint32_t w = rd32(buf + o); uint32_t t = 0; const char *k = NULL;
            int rc = direct_target(va, w, &t, &k);
            scanned++;
            if (rc == 2) { indirect++; im_ind++; }
            else if (rc == 1 && t >= lo && t < hi) {
                if (nhits < sizeof hits / sizeof hits[0]) { hits[nhits++] = (Hit){va, w, t, k}; }
                im_hits++;
            }
        }
        printf("  %s{\"path\": \"%s\", \"va_base\": \"0x%08x\", \"words\": %ld, "
               "\"direct_entries_into_block\": %zu, \"indirect_sites\": %llu}",
               images ? ",\n" : "", spec, base, (sz - start) / 4, im_hits, im_ind);
        images++;
        free(buf);
    }
    printf("\n ],\n \"direct_entries\": [\n");
    for (size_t i = 0; i < nhits; i++)
        printf("  %s{\"from\": \"0x%08x\", \"word\": \"0x%08x\", \"kind\": \"%s\", \"target\": \"0x%08x\"}",
               i ? ",\n" : "", hits[i].va, hits[i].word, hits[i].kind, hits[i].target);
    printf("\n ],\n \"direct_entry_count\": %zu,\n \"indirect_sites_total\": %llu,\n"
           " \"words_scanned\": %llu,\n \"images_scanned\": %zu,\n"
           " \"note\": \"A direct-target scan cannot resolve jr/jalr. Zero direct entries "
           "means the observed entry is indirect or via a target this scan's image set does not contain.\"\n}\n",
           nhits, indirect, scanned, images);
    return 0;
}
