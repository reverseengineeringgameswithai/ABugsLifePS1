/* phase4_f06_f14_overlay_pin.c -- settle F06/F14 overlay-VA ambiguity by FILE.
 *
 * WHY THIS EXISTS
 * ---------------
 * Every per-level overlay in this game loads at the SAME virtual address
 * (0x800B39A0). A PC such as 0x800B3F8C therefore decodes to a real instruction
 * in 18 of the 20 censused overlay images, so any artifact that names an
 * overlay FILE from an ADDRESS is guessing. F09 hit this exact defect and
 * settled it from bytes (tools/phase4_f09_overlay_pin.c); this tool is the same
 * idea generalised, because F06 and F14 carry different KINDS of independent
 * evidence about what should be at their addresses:
 *
 *   F06_birdnest  -- the D17 defeat trace attributes each overlay writer PC to
 *                    the exact ADDRESS it wrote, and the typed record registry
 *                    gives that field's WIDTH. Two NECESSARY conditions follow
 *                    for the true writer, both derived from runtime observation
 *                    and never from the candidate file:
 *                      N1  the word at that PC is a store of exactly that width;
 *                      N2  IF that store is the PsyQ absolute-address idiom
 *                          (`lui $at,hi` / `sX rt,lo($at)`, base register $1),
 *                          THEN its immediate is the low half of the written
 *                          address.
 *                    N2 is a CONDITIONAL, not a demand that the writer be
 *                    absolute-form: a register-pointer writer satisfies it
 *                    vacuously, so the test cannot be tuned to force a pin.
 *                    Spec kind `S`.
 *   F14_riverbed_flight -- the C15 respawn-writer catalog records literal
 *                    instruction ENCODINGS for the LEVEL08 safe/live-tuple
 *                    initializer, and the C16 flight-death run verified a
 *                    108-byte RUNTIME slice hash at 0x800B3AE8 against pristine
 *                    media. Both are file-independent. Spec kinds `W` and `H`.
 *
 * A single surviving image is a file pin; more than one is a measured ambiguity
 * that no artifact may paper over; zero means the claim under test is wrong.
 *
 * Instruction decoding lives HERE, in compiled C, per the project's standing
 * rule -- the caller passes addresses, widths, immediates and hashes, and never
 * decodes a word by hand.
 *
 * usage: phase4_f06_f14_overlay_pin OUT.json LABEL BASE SPEC[,SPEC...] FILE [FILE...]
 *   SPEC := W=word:pc            exact instruction word, expected at runtime pc
 *         | S=pc:width:target    store of `width` bytes at file offset
 *                                (pc - BASE) that wrote runtime address
 *                                `target` (N1 + N2 above)
 *         | H=sha256:len:addr    aligned window hashing to sha256, expected to
 *                                live at runtime address `addr`
 * build: gcc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_f06_f14_overlay_pin.c \
 *          -o /tmp/f06_f14_overlay_pin -lcrypto
 */
#define _POSIX_C_SOURCE 200809L

#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_SPECS 16
#define MAX_HITS 64

enum spec_kind { SPEC_WORD, SPEC_STORE, SPEC_HASH };

struct spec {
    enum spec_kind kind;
    uint32_t word;      /* SPEC_WORD */
    uint32_t pc;        /* SPEC_WORD / SPEC_STORE / SPEC_HASH runtime address */
    unsigned width;     /* SPEC_STORE store width in bytes */
    uint32_t target;    /* SPEC_STORE runtime address the PC was seen writing */
    char sha[65];       /* SPEC_HASH */
    long len;           /* SPEC_HASH window length */
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

/* Store width in bytes for a primary opcode, or 0 if it is not a store. */
static unsigned store_width(unsigned op)
{
    switch (op) {
    case 0x28: return 1;
    case 0x29: return 2;
    case 0x2b: return 4;
    default:   return 0;
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

static void lower(char *s)
{
    for (; *s; s++)
        if (*s >= 'A' && *s <= 'Z')
            *s += 32;
}

static int parse_specs(char *text, struct spec *out)
{
    int n = 0;
    char *save = NULL;
    char *tok = strtok_r(text, ",", &save);

    while (tok) {
        struct spec s;
        memset(&s, 0, sizeof(s));
        if (n >= MAX_SPECS) {
            fprintf(stderr, "too many specs (max %d)\n", MAX_SPECS);
            exit(2);
        }
        if (strncmp(tok, "W=", 2) == 0) {
            char *a = tok + 2, *colon = strchr(a, ':');
            if (!colon) {
                fprintf(stderr, "W spec %s is not W=word:pc\n", tok);
                exit(2);
            }
            *colon = 0;
            s.kind = SPEC_WORD;
            s.word = (uint32_t)strtoul(a, NULL, 16);
            s.pc = (uint32_t)strtoul(colon + 1, NULL, 16);
        } else if (strncmp(tok, "S=", 2) == 0) {
            char *a = tok + 2;
            char *c1 = strchr(a, ':');
            char *c2 = c1 ? strchr(c1 + 1, ':') : NULL;
            if (!c1 || !c2) {
                fprintf(stderr, "S spec %s is not S=pc:width:target\n", tok);
                exit(2);
            }
            *c1 = 0;
            *c2 = 0;
            s.kind = SPEC_STORE;
            s.pc = (uint32_t)strtoul(a, NULL, 16);
            s.width = (unsigned)strtoul(c1 + 1, NULL, 10);
            s.target = (uint32_t)strtoul(c2 + 1, NULL, 16);
            if (s.width != 1 && s.width != 2 && s.width != 4) {
                fprintf(stderr, "S spec %s: width must be 1, 2 or 4\n", a);
                exit(2);
            }
        } else if (strncmp(tok, "H=", 2) == 0) {
            char *a = tok + 2;
            char *c1 = strchr(a, ':');
            char *c2 = c1 ? strchr(c1 + 1, ':') : NULL;
            if (!c1 || !c2 || (size_t)(c1 - a) != 64) {
                fprintf(stderr, "H spec %s is not H=sha256:len:addr\n", tok);
                exit(2);
            }
            *c1 = 0;
            *c2 = 0;
            s.kind = SPEC_HASH;
            memcpy(s.sha, a, 64);
            s.sha[64] = 0;
            lower(s.sha);
            s.len = strtol(c1 + 1, NULL, 10);
            s.pc = (uint32_t)strtoul(c2 + 1, NULL, 16);
            if (s.len < 4 || (s.len & 3)) {
                fprintf(stderr, "H spec: len must be a multiple of 4 and >= 4\n");
                exit(2);
            }
        } else {
            fprintf(stderr, "spec %s must start with W=, S= or H=\n", tok);
            exit(2);
        }
        out[n++] = s;
        tok = strtok_r(NULL, ",", &save);
    }
    if (n == 0) {
        fprintf(stderr, "no specs given\n");
        exit(2);
    }
    return n;
}

int main(int argc, char **argv)
{
    struct spec specs[MAX_SPECS];
    int nspecs, nfiles, i, j;
    FILE *out;
    const char *label;
    uint32_t load_base;
    unsigned files_ok = 0, files_base_consistent = 0;
    const char *pin_path = NULL;
    uint32_t pin_base = 0;
    int any_derived_base = 0;

    if (argc < 6) {
        fprintf(stderr,
                "usage: %s OUT.json LABEL BASE SPEC[,SPEC...] FILE [FILE...]\n"
                "  SPEC := W=word:pc | S=pc:width:imm | H=sha256:len:addr\n",
                argv[0]);
        return 2;
    }
    label = argv[2];
    load_base = (uint32_t)strtoul(argv[3], NULL, 16);
    nspecs = parse_specs(argv[4], specs);
    nfiles = argc - 5;

    for (i = 0; i < nspecs; i++)
        if (specs[i].kind != SPEC_STORE)
            any_derived_base = 1;

    out = fopen(argv[1], "w");
    if (!out) {
        perror(argv[1]);
        return 2;
    }

    fprintf(out, "{\n");
    fprintf(out,
            " \"_comment\": \"Which overlay FILE actually contains this row's "
            "governing instructions. Every level overlay loads at the same VA, "
            "so a PC alone cannot name a file; encodings, store shapes and "
            "runtime slice hashes can. Regenerate: "
            "tools/phase4_f06_f14_overlay_pin.c\",\n");
    fprintf(out, " \"schema\": \"abl-phase4-f06-f14-overlay-pin/1\",\n");
    fprintf(out, " \"generated_by\": \"tools/phase4_f06_f14_overlay_pin.c\",\n");
    fprintf(out, " \"label\": \"%s\",\n", label);
    fprintf(out, " \"assumed_load_base\": \"0x%08" PRIx32 "\",\n", load_base);
    fprintf(out, " \"base_is_derived_from_evidence\": %s,\n",
            any_derived_base ? "true" : "false");
    fprintf(out, " \"specs\": [\n");
    for (i = 0; i < nspecs; i++) {
        const struct spec *s = &specs[i];
        if (s->kind == SPEC_WORD) {
            unsigned op = s->word >> 26;
            const char *nm = mem_opname(op);
            fprintf(out,
                    "  {\"kind\": \"word\", \"word\": \"0x%08" PRIx32 "\", "
                    "\"pc\": \"0x%08" PRIx32 "\", \"op\": %s%s%s, \"rs\": %u, "
                    "\"rt\": %u, \"imm\": \"0x%04" PRIx32 "\"}%s\n",
                    s->word, s->pc, nm ? "\"" : "", nm ? nm : "null",
                    nm ? "\"" : "", (s->word >> 21) & 31, (s->word >> 16) & 31,
                    s->word & 0xffff, i + 1 == nspecs ? "" : ",");
        } else if (s->kind == SPEC_STORE) {
            fprintf(out,
                    "  {\"kind\": \"store_shape\", \"pc\": \"0x%08" PRIx32 "\", "
                    "\"observed_write_width\": %u, "
                    "\"observed_write_target\": \"0x%08" PRIx32 "\", "
                    "\"absolute_form_imm_must_be\": \"0x%04" PRIx32 "\", "
                    "\"file_offset\": %" PRId32 "}%s\n",
                    s->pc, s->width, s->target, s->target & 0xffff,
                    (int32_t)(s->pc - load_base), i + 1 == nspecs ? "" : ",");
        } else {
            fprintf(out,
                    "  {\"kind\": \"slice_hash\", \"sha256\": \"%s\", "
                    "\"length\": %ld, \"runtime_address\": \"0x%08" PRIx32
                    "\"}%s\n",
                    s->sha, s->len, s->pc, i + 1 == nspecs ? "" : ",");
        }
    }
    fprintf(out, " ],\n \"files\": [\n");

    for (j = 0; j < nfiles; j++) {
        const char *path = argv[5 + j];
        long n, off;
        uint8_t *buf = slurp(path, &n);
        char sha[65];
        int all_ok = 1, base_consistent = 1, have_base = 0;
        uint32_t base = 0;

        sha256_hex(buf, (size_t)n, sha);
        fprintf(out,
                "  {\"path\": \"%s\", \"size\": %ld, \"sha256\": \"%s\",\n"
                "   \"spec_results\": [",
                path, n, sha);

        for (i = 0; i < nspecs; i++) {
            const struct spec *s = &specs[i];
            unsigned hits = 0;
            long hit_off[MAX_HITS];
            int ok = 0;

            if (s->kind == SPEC_WORD) {
                for (off = 0; off + 4 <= n; off += 4)
                    if (le32(buf + off) == s->word) {
                        if (hits < MAX_HITS)
                            hit_off[hits] = off;
                        hits++;
                    }
                ok = (hits == 1);
                fprintf(out,
                        "{\"kind\": \"word\", \"pc\": \"0x%08" PRIx32 "\", "
                        "\"occurrences\": %u, \"satisfied\": %s",
                        s->pc, hits, ok ? "true" : "false");
                if (ok) {
                    uint32_t implied = s->pc - (uint32_t)hit_off[0];
                    fprintf(out, ", \"file_offset\": %ld, "
                                 "\"implied_load_base\": \"0x%08" PRIx32 "\"",
                            hit_off[0], implied);
                    if (!have_base) {
                        base = implied;
                        have_base = 1;
                    } else if (implied != base) {
                        base_consistent = 0;
                    }
                }
                fprintf(out, "}");
            } else if (s->kind == SPEC_STORE) {
                long fo = (long)(int32_t)(s->pc - load_base);
                unsigned op = 0, w = 0, imm = 0, rs = 0;
                int in_range = (fo >= 0 && fo + 4 <= n);
                const char *nm = NULL;
                if (in_range) {
                    uint32_t word = le32(buf + fo);
                    int n1, n2;
                    op = word >> 26;
                    rs = (word >> 21) & 31;
                    nm = mem_opname(op);
                    w = store_width(op);
                    imm = word & 0xffff;
                    /* N1: a store of exactly the observed write width.        */
                    n1 = (w == s->width);
                    /* N2: absolute ($at-based) stores must carry the low half
                     * of the address the PC was observed writing; a register-
                     * pointer store satisfies this vacuously.                 */
                    n2 = (rs != 1) || (imm == (s->target & 0xffff));
                    ok = n1 && n2;
                    fprintf(out,
                            "{\"kind\": \"store_shape\", \"pc\": \"0x%08" PRIx32
                            "\", \"in_range\": true, \"word\": \"0x%08" PRIx32
                            "\", \"op\": %s%s%s, \"rs\": %u, \"imm\": "
                            "\"0x%04x\", \"absolute_form\": %s, \"n1_width\": "
                            "%s, \"n2_absolute_target\": %s, \"satisfied\": %s",
                            s->pc, word, nm ? "\"" : "", nm ? nm : "null",
                            nm ? "\"" : "", rs, imm,
                            rs == 1 ? "true" : "false", n1 ? "true" : "false",
                            n2 ? "true" : "false", ok ? "true" : "false");
                    fprintf(out, "}");
                } else {
                    ok = 0;
                    fprintf(out,
                            "{\"kind\": \"store_shape\", \"pc\": \"0x%08" PRIx32
                            "\", \"in_range\": false, \"satisfied\": false}",
                            s->pc);
                }
            } else {
                char win[65];
                for (off = 0; off + s->len <= n; off += 4) {
                    sha256_hex(buf + off, (size_t)s->len, win);
                    if (strcmp(win, s->sha) == 0) {
                        if (hits < MAX_HITS)
                            hit_off[hits] = off;
                        hits++;
                    }
                }
                ok = (hits == 1);
                fprintf(out,
                        "{\"kind\": \"slice_hash\", \"length\": %ld, "
                        "\"occurrences\": %u, \"satisfied\": %s",
                        s->len, hits, ok ? "true" : "false");
                if (ok) {
                    uint32_t implied = s->pc - (uint32_t)hit_off[0];
                    fprintf(out, ", \"file_offset\": %ld, "
                                 "\"implied_load_base\": \"0x%08" PRIx32 "\"",
                            hit_off[0], implied);
                    if (!have_base) {
                        base = implied;
                        have_base = 1;
                    } else if (implied != base) {
                        base_consistent = 0;
                    }
                }
                fprintf(out, "}");
            }
            if (!ok)
                all_ok = 0;
            if (i + 1 != nspecs)
                fprintf(out, ", ");
        }

        if (!all_ok)
            base_consistent = 0;
        if (all_ok)
            files_ok++;
        if (all_ok && base_consistent) {
            files_base_consistent++;
            pin_path = path;
            pin_base = have_base ? base : load_base;
        }

        fprintf(out, "],\n   \"all_specs_satisfied\": %s, "
                     "\"base_consistent\": %s, \"implied_load_base\": ",
                all_ok ? "true" : "false",
                base_consistent ? "true" : "false");
        if (all_ok && base_consistent && have_base)
            fprintf(out, "\"0x%08" PRIx32 "\"}%s\n", base,
                    j + 1 == nfiles ? "" : ",");
        else if (all_ok && base_consistent)
            fprintf(out, "\"0x%08" PRIx32 "\"}%s\n", load_base,
                    j + 1 == nfiles ? "" : ",");
        else
            fprintf(out, "null}%s\n", j + 1 == nfiles ? "" : ",");
        free(buf);
    }

    fprintf(out, " ],\n");
    fprintf(out, " \"files_scanned\": %d,\n", nfiles);
    fprintf(out, " \"files_satisfying_every_spec\": %u,\n", files_ok);
    fprintf(out, " \"files_with_one_consistent_load_base\": %u,\n",
            files_base_consistent);
    fprintf(out, " \"unique_pin\": %s,\n",
            files_base_consistent == 1 ? "true" : "false");
    if (files_base_consistent == 1) {
        fprintf(out, " \"unique_pin_file\": \"%s\",\n", pin_path);
        fprintf(out, " \"unique_pin_load_base\": \"0x%08" PRIx32 "\",\n",
                pin_base);
    } else {
        fprintf(out, " \"unique_pin_file\": null,\n");
        fprintf(out, " \"unique_pin_load_base\": null,\n");
    }
    fprintf(out, " \"result\": \"%s\"\n}\n",
            files_base_consistent == 1 ? "OVERLAY_PIN_UNIQUE"
                                       : (files_base_consistent == 0
                                              ? "OVERLAY_PIN_NONE"
                                              : "OVERLAY_PIN_AMBIGUOUS"));
    fclose(out);

    printf("[%s] scanned %d images; %u satisfy every spec; %u yield one "
           "consistent load base\n",
           label, nfiles, files_ok, files_base_consistent);
    if (files_base_consistent == 1)
        printf("OVERLAY_PIN_UNIQUE: %s @ base 0x%08" PRIx32 "\n", pin_path,
               pin_base);
    else
        printf("OVERLAY_PIN_%s: %u candidate images\n",
               files_base_consistent ? "AMBIGUOUS" : "NONE",
               files_base_consistent);
    return 0;
}
