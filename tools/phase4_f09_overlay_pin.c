/* phase4_f09_overlay_pin.c -- resolve F09's overlay-VA ambiguity by FILE.
 *
 * WHY THIS EXISTS
 * ---------------
 * Every level overlay in this game loads at the SAME virtual address
 * (0x800B39A0). A PC such as 0x800B3DB0 therefore names a real instruction in
 * ~18 different overlay images, and a census that resolves it by address alone
 * will pick whichever image it happened to enumerate first. F09's own semantic
 * ownership graph resolves the Bug Bar fight-lane PCs to LEVEL03_LEVEL1 /
 * LEVEL03_LEVEL, while the D18 fight-law artifacts resolve them to
 * LEVEL04/LEVEL1.BIN. Both cannot be right, and neither claim is checkable from
 * an address.
 *
 * This tool decides it from BYTES: given (instruction word, expected PC) pairs,
 * it scans every supplied image for the exact encodings, and reports which
 * images contain all of them exactly once AND yield ONE self-consistent load
 * base. A single surviving image is a campaign-wide unique file pin; more than
 * one is a measured ambiguity that no artifact may paper over.
 *
 * Instruction decoding lives here, in compiled C, per the project's standing
 * rule -- the caller passes encodings and never re-derives them by hand.
 *
 * usage: phase4_f09_overlay_pin OUT.json WORD:PC[,WORD:PC...] FILE [FILE...]
 * build: gcc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_f09_overlay_pin.c \
 *          -o /tmp/f09_overlay_pin -lcrypto
 */
#define _POSIX_C_SOURCE 200809L

#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_TARGETS 8
#define MAX_OFFSETS 64

struct target {
    uint32_t word;
    uint32_t pc;
};

struct match {
    unsigned count;
    long offsets[MAX_OFFSETS];
};

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

/* MIPS I load/store primary opcodes; NULL means "not a load/store". */
static const char *mem_opname(unsigned op)
{
    switch (op) {
    case 0x20: return "lb";
    case 0x21: return "lh";
    case 0x23: return "lw";
    case 0x24: return "lbu";
    case 0x25: return "lhu";
    case 0x28: return "sb";
    case 0x29: return "sh";
    case 0x2b: return "sw";
    default:   return NULL;
    }
}

static void sha256_hex(const uint8_t *buf, size_t n, char out[65])
{
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    uint8_t digest[32];
    unsigned len = 0;
    size_t i;

    if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
        EVP_DigestUpdate(ctx, buf, n) != 1 ||
        EVP_DigestFinal_ex(ctx, digest, &len) != 1 || len != 32) {
        fprintf(stderr, "sha256 failed\n");
        exit(2);
    }
    EVP_MD_CTX_free(ctx);
    for (i = 0; i < 32; i++)
        sprintf(out + i * 2, "%02x", digest[i]);
    out[64] = 0;
}

static uint8_t *slurp(const char *path, long *out_n)
{
    FILE *f = fopen(path, "rb");
    uint8_t *b;
    long n;

    if (!f) {
        perror(path);
        exit(2);
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        perror(path);
        exit(2);
    }
    n = ftell(f);
    rewind(f);
    if (n < 4) {
        fprintf(stderr, "%s: too small (%ld bytes)\n", path, n);
        exit(2);
    }
    b = malloc((size_t)n);
    if (!b || fread(b, 1, (size_t)n, f) != (size_t)n) {
        fprintf(stderr, "%s: read failed\n", path);
        exit(2);
    }
    fclose(f);
    *out_n = n;
    return b;
}

static int parse_targets(char *spec, struct target *t)
{
    int n = 0;
    char *save = NULL;
    char *tok = strtok_r(spec, ",", &save);

    while (tok) {
        char *colon = strchr(tok, ':');
        if (!colon) {
            fprintf(stderr, "target %s is not WORD:PC\n", tok);
            exit(2);
        }
        *colon = 0;
        if (n >= MAX_TARGETS) {
            fprintf(stderr, "too many targets (max %d)\n", MAX_TARGETS);
            exit(2);
        }
        t[n].word = (uint32_t)strtoul(tok, NULL, 16);
        t[n].pc = (uint32_t)strtoul(colon + 1, NULL, 16);
        n++;
        tok = strtok_r(NULL, ",", &save);
    }
    if (n == 0) {
        fprintf(stderr, "no targets given\n");
        exit(2);
    }
    return n;
}

int main(int argc, char **argv)
{
    struct target targets[MAX_TARGETS];
    int ntargets, nfiles, i, j;
    FILE *out;
    unsigned files_with_all = 0, files_consistent = 0;
    const char *pin_path = NULL;
    uint32_t pin_base = 0;

    if (argc < 4) {
        fprintf(stderr,
                "usage: %s OUT.json WORD:PC[,WORD:PC...] FILE [FILE...]\n",
                argv[0]);
        return 2;
    }
    ntargets = parse_targets(argv[2], targets);
    nfiles = argc - 3;

    out = fopen(argv[1], "w");
    if (!out) {
        perror(argv[1]);
        return 2;
    }

    fprintf(out, "{\n");
    fprintf(out, " \"_comment\": \"Which overlay FILE actually contains F09's "
                 "fight-lane instructions. Every level overlay loads at the same "
                 "VA, so a PC alone cannot name a file; these encodings can. "
                 "Regenerate: tools/phase4_f09_overlay_pin.c\",\n");
    fprintf(out, " \"schema\": \"abl-phase4-f09-overlay-pin/1\",\n");
    fprintf(out, " \"generated_by\": \"tools/phase4_f09_overlay_pin.c\",\n");
    fprintf(out, " \"targets\": [\n");
    for (i = 0; i < ntargets; i++) {
        uint32_t w = targets[i].word;
        unsigned op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        const char *name = mem_opname(op);
        fprintf(out,
                "  {\"word\": \"0x%08" PRIx32 "\", \"pc\": \"0x%08" PRIx32
                "\", \"op\": %s%s%s, \"rs\": %u, \"rt\": %u, "
                "\"imm\": \"0x%04" PRIx32 "\"}%s\n",
                w, targets[i].pc, name ? "\"" : "", name ? name : "null",
                name ? "\"" : "", rs, rt, w & 0xffff,
                i + 1 == ntargets ? "" : ",");
    }
    fprintf(out, " ],\n \"files\": [\n");

    for (j = 0; j < nfiles; j++) {
        const char *path = argv[3 + j];
        long n, off;
        uint8_t *buf = slurp(path, &n);
        char sha[65];
        struct match m[MAX_TARGETS];
        int all_unique = 1, base_consistent = 1;
        uint32_t base = 0;
        int have_base = 0;

        sha256_hex(buf, (size_t)n, sha);
        memset(m, 0, sizeof(m));
        for (off = 0; off + 4 <= n; off += 4) {
            uint32_t w = le32(buf + off);
            for (i = 0; i < ntargets; i++) {
                if (w != targets[i].word)
                    continue;
                if (m[i].count < MAX_OFFSETS)
                    m[i].offsets[m[i].count] = off;
                m[i].count++;
            }
        }
        for (i = 0; i < ntargets; i++) {
            if (m[i].count != 1) {
                all_unique = 0;
                continue;
            }
            uint32_t implied = targets[i].pc - (uint32_t)m[i].offsets[0];
            if (!have_base) {
                base = implied;
                have_base = 1;
            } else if (implied != base) {
                base_consistent = 0;
            }
        }
        if (!all_unique)
            base_consistent = 0;
        if (all_unique)
            files_with_all++;
        if (base_consistent) {
            files_consistent++;
            pin_path = path;
            pin_base = base;
        }

        fprintf(out,
                "  {\"path\": \"%s\", \"size\": %ld, \"sha256\": \"%s\",\n"
                "   \"matches\": [",
                path, n, sha);
        for (i = 0; i < ntargets; i++) {
            unsigned k;
            fprintf(out, "{\"word\": \"0x%08" PRIx32 "\", \"count\": %u, "
                         "\"offsets\": [",
                    targets[i].word, m[i].count);
            for (k = 0; k < m[i].count && k < MAX_OFFSETS; k++)
                fprintf(out, "%ld%s", m[i].offsets[k],
                        k + 1 == m[i].count ? "" : ", ");
            fprintf(out, "]}%s", i + 1 == ntargets ? "" : ", ");
        }
        fprintf(out, "],\n   \"all_targets_unique\": %s, "
                     "\"base_consistent\": %s, \"implied_load_base\": ",
                all_unique ? "true" : "false",
                base_consistent ? "true" : "false");
        if (base_consistent)
            fprintf(out, "\"0x%08" PRIx32 "\"}%s\n", base,
                    j + 1 == nfiles ? "" : ",");
        else
            fprintf(out, "null}%s\n", j + 1 == nfiles ? "" : ",");
        free(buf);
    }

    fprintf(out, " ],\n");
    fprintf(out, " \"files_scanned\": %d,\n", nfiles);
    fprintf(out, " \"files_containing_every_target_exactly_once\": %u,\n",
            files_with_all);
    fprintf(out, " \"files_with_one_consistent_load_base\": %u,\n",
            files_consistent);
    fprintf(out, " \"unique_pin\": %s,\n",
            files_consistent == 1 ? "true" : "false");
    if (files_consistent == 1) {
        fprintf(out, " \"unique_pin_file\": \"%s\",\n", pin_path);
        fprintf(out, " \"unique_pin_load_base\": \"0x%08" PRIx32 "\",\n",
                pin_base);
    } else {
        fprintf(out, " \"unique_pin_file\": null,\n");
        fprintf(out, " \"unique_pin_load_base\": null,\n");
    }
    fprintf(out, " \"result\": \"%s\"\n}\n",
            files_consistent == 1 ? "F09_OVERLAY_PIN_UNIQUE"
                                  : "F09_OVERLAY_PIN_AMBIGUOUS");
    fclose(out);

    printf("scanned %d images; %u contain every target exactly once; "
           "%u yield one consistent load base\n",
           nfiles, files_with_all, files_consistent);
    if (files_consistent == 1)
        printf("F09_OVERLAY_PIN_UNIQUE: %s @ base 0x%08" PRIx32 "\n", pin_path,
               pin_base);
    else
        printf("F09_OVERLAY_PIN_AMBIGUOUS: %u candidate images\n",
               files_consistent);
    return 0;
}
