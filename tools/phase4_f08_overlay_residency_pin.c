/* phase4_f08_overlay_residency_pin.c -- settle F08's overlay identity from BYTES.
 *
 * WHY THIS EXISTS
 * ---------------
 * Every per-level overlay in this game loads at the SAME virtual address
 * (region A, 0x800B39A0). An address in that window therefore names real
 * content in ~19 of the 20 overlay images, and any census that resolves it by
 * ADDRESS alone picks whichever image it enumerated first. F09 hit this on the
 * code side (tools/phase4_f09_overlay_pin.c). F08's exposure is the RESIDENCY
 * side: its whole corrected binding rests on the claim
 *
 *     "OVL/LEVEL05_LEVEL.BIN is the image resident at 0x800B39A0 in all five
 *      F08 fixtures, at 99.14% over 1862 non-trivial bytes vs 5.53% for
 *      LEVEL10_LEVEL.BIN"
 *
 * -- a number that appears only as prose in analysis/phase4_f08_scene_binding.json.
 * No committed tool produces it, so it cannot be re-derived, and the artifact
 * itself warns that LEVEL09_LEVEL1.BIN slice-matches as a FALSE POSITIVE at a
 * wandering base. A claim whose discriminator is "base stability" must be
 * measured with the base, not asserted.
 *
 * WHAT IT MEASURES, per (RAM image x candidate file):
 *   1. AGREEMENT AT THE DECLARED BASE. Byte-for-byte over min(file, region)
 *      bytes, reported raw AND over NON-TRIVIAL positions (both-zero positions
 *      excluded -- counting zero-vs-zero padding is the documented trap that
 *      first inflated this very number).
 *   2. ANCHOR RESIDENCY AT ANY BASE. High-entropy 64-byte slices of the file are
 *      searched across the whole 2 MiB RAM; >=2 slices agreeing on one implied
 *      base is residency evidence, and the implied base is REPORTED rather than
 *      assumed -- that is what exposes a wandering false positive.
 *   3. Whether the file is the unique argmax of non-trivial agreement at the
 *      declared base, in EVERY supplied RAM image.
 * A file pins the row only if it wins (3) and its stable anchor base equals the
 * declared base in every RAM. One survivor is a unique pin; more than one is a
 * measured ambiguity no artifact may paper over.
 *
 * IT ALSO MEASURES THE ROW'S HEADLINE NEGATIVE. The row claims "region A differs
 * in only 4 bytes of 7,656 across the five per-performer fixtures, so the
 * objective state is not in the overlay's static data". That number is likewise
 * prose. This tool recomputes the cross-fixture diff over region A AND over the
 * whole 2 MiB, and splits region A's differing bytes into those INSIDE the
 * pinned image's extent and those beyond it -- because region A is sized for the
 * largest overlay, so most of the window is not this overlay at all and a diff
 * over the whole window says nothing about "the overlay's static data".
 *
 * No emulator is involved: the RAM images come from the .sav containers via
 * tools/phase4_f08_save_ram.py. Byte-level decoding lives here, in compiled C,
 * per the project's standing rule.
 *
 * FINALLY it reads named WORDS. The caller supplies addresses it derived from a
 * pinned artifact (here: the overlay-local globals declared by the one
 * byte-matched C source in this overlay) and gets each word's value in every
 * fixture plus its value in the disc image, so "initialized at runtime" and
 * "static data" are told apart by measurement. The caller never re-types the
 * addresses; drift between the source and this scan is then detectable.
 *
 * usage: phase4_f08_overlay_residency_pin OUT.json BASE_HEX REGION_LEN \
 *          --rams LABEL=PATH [LABEL=PATH...] --images FILE [FILE...] \
 *          [--words ADDR[,ADDR...]]
 * build: gcc -std=c11 -O2 -Wall -Wextra -Werror \
 *          tools/phase4_f08_overlay_residency_pin.c -o /tmp/f08_pin -lcrypto
 */
#define _GNU_SOURCE

#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RAM_SIZE   (2u * 1024u * 1024u)
#define RAM_VA     0x80000000u
#define MAX_RAMS   16
#define MAX_IMAGES 64
#define MAX_ANCHOR 8
#define ANCHOR_LEN 64
#define ANCHOR_MIN_DISTINCT 32
#define MAX_DIFF_REPORT 64

struct ram {
    const char *label;
    const char *path;
    uint8_t *buf;
    long n;
    char sha256[65];
};

struct image {
    const char *path;
    uint8_t *buf;
    long n;
    char sha1[41];
    char sha256[65];
};

/* per (ram, image) result */
struct cell {
    long compared;          /* bytes compared at the declared base */
    long equal;             /* equal bytes, raw */
    long nontrivial;        /* positions where NOT (ram==0 && img==0) */
    long nontrivial_equal;
    int anchors_used;
    int anchor_base_agreeing;   /* how many anchors agree on the best base */
    uint32_t anchor_base;       /* implied load base of the best-supported hit */
    int anchor_base_valid;
    int distinct_anchor_bases;
};

static void digest_hex(const EVP_MD *md, const uint8_t *b, size_t n, char *out,
                       unsigned outbytes)
{
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    uint8_t d[64];
    unsigned len = 0, i;

    if (!ctx || EVP_DigestInit_ex(ctx, md, NULL) != 1 ||
        EVP_DigestUpdate(ctx, b, n) != 1 || EVP_DigestFinal_ex(ctx, d, &len) != 1 ||
        len != outbytes) {
        fprintf(stderr, "digest failed\n");
        exit(2);
    }
    EVP_MD_CTX_free(ctx);
    for (i = 0; i < outbytes; i++)
        sprintf(out + i * 2, "%02x", d[i]);
    out[outbytes * 2] = 0;
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
    if (n <= 0) {
        fprintf(stderr, "%s: empty\n", path);
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

/* Pick up to MAX_ANCHOR high-entropy slices, spread across the image. A slice of
 * padding or of a repeated pattern would match everywhere, so slices with fewer
 * than ANCHOR_MIN_DISTINCT distinct byte values are rejected outright. */
static int pick_anchors(const struct image *im, long *offs)
{
    int found = 0;
    long stride, o;

    if (im->n < ANCHOR_LEN)
        return 0;
    stride = (im->n - ANCHOR_LEN) / MAX_ANCHOR;
    if (stride < 4)
        stride = 4;
    for (o = 0; o + ANCHOR_LEN <= im->n && found < MAX_ANCHOR; o += stride) {
        long probe;
        for (probe = o; probe + ANCHOR_LEN <= im->n && probe < o + stride; probe += 4) {
            int seen[256] = {0}, distinct = 0, k;
            for (k = 0; k < ANCHOR_LEN; k++) {
                int c = im->buf[probe + k];
                if (!seen[c]) {
                    seen[c] = 1;
                    distinct++;
                }
            }
            if (distinct >= ANCHOR_MIN_DISTINCT) {
                offs[found++] = probe;
                break;
            }
        }
    }
    return found;
}

int main(int argc, char **argv)
{
    struct ram rams[MAX_RAMS];
    struct image images[MAX_IMAGES];
    uint32_t words[MAX_DIFF_REPORT];
    int nwords = 0;
    int nrams = 0, nimages = 0, i, j, mode = 0;
    uint32_t base_va, region_off;
    long region_len;
    FILE *out;
    struct cell *cells;
    int *argmax_wins, *stable_base;
    int pin_index = -1, pins = 0;

    if (argc < 6) {
        fprintf(stderr, "usage: %s OUT.json BASE_HEX REGION_LEN --rams LABEL=PATH... "
                        "--images FILE...\n", argv[0]);
        return 2;
    }
    base_va = (uint32_t)strtoul(argv[2], NULL, 16);
    region_len = strtol(argv[3], NULL, 10);
    if (base_va < RAM_VA || region_len <= 0) {
        fprintf(stderr, "bad base/region\n");
        return 2;
    }
    region_off = base_va - RAM_VA;
    if (region_off + (uint32_t)region_len > RAM_SIZE) {
        fprintf(stderr, "region does not fit in main RAM\n");
        return 2;
    }

    for (i = 4; i < argc; i++) {
        if (!strcmp(argv[i], "--rams")) {
            mode = 1;
            continue;
        }
        if (!strcmp(argv[i], "--images")) {
            mode = 2;
            continue;
        }
        if (!strcmp(argv[i], "--words")) {
            mode = 3;
            continue;
        }
        if (mode == 3) {
            char *save = NULL, *tok = strtok_r(argv[i], ",", &save);
            while (tok) {
                if (nwords >= MAX_DIFF_REPORT) {
                    fprintf(stderr, "too many words\n");
                    return 2;
                }
                words[nwords++] = (uint32_t)strtoul(tok, NULL, 16);
                tok = strtok_r(NULL, ",", &save);
            }
            continue;
        }
        if (mode == 1) {
            char *eq = strchr(argv[i], '=');
            if (!eq) {
                fprintf(stderr, "ram spec %s is not LABEL=PATH\n", argv[i]);
                return 2;
            }
            if (nrams >= MAX_RAMS) {
                fprintf(stderr, "too many rams\n");
                return 2;
            }
            *eq = 0;
            rams[nrams].label = argv[i];
            rams[nrams].path = eq + 1;
            rams[nrams].buf = slurp(rams[nrams].path, &rams[nrams].n);
            if (rams[nrams].n != (long)RAM_SIZE) {
                fprintf(stderr, "%s: expected a %u-byte RAM image, got %ld\n",
                        rams[nrams].path, RAM_SIZE, rams[nrams].n);
                return 2;
            }
            digest_hex(EVP_sha256(), rams[nrams].buf, (size_t)rams[nrams].n,
                       rams[nrams].sha256, 32);
            nrams++;
        } else if (mode == 2) {
            if (nimages >= MAX_IMAGES) {
                fprintf(stderr, "too many images\n");
                return 2;
            }
            images[nimages].path = argv[i];
            images[nimages].buf = slurp(argv[i], &images[nimages].n);
            digest_hex(EVP_sha1(), images[nimages].buf, (size_t)images[nimages].n,
                       images[nimages].sha1, 20);
            digest_hex(EVP_sha256(), images[nimages].buf, (size_t)images[nimages].n,
                       images[nimages].sha256, 32);
            nimages++;
        } else {
            fprintf(stderr, "unexpected argument %s before --rams/--images\n", argv[i]);
            return 2;
        }
    }
    if (nrams == 0 || nimages == 0) {
        fprintf(stderr, "need at least one ram and one image\n");
        return 2;
    }

    cells = calloc((size_t)nrams * (size_t)nimages, sizeof *cells);
    argmax_wins = calloc((size_t)nimages, sizeof *argmax_wins);
    stable_base = calloc((size_t)nimages, sizeof *stable_base);
    if (!cells || !argmax_wins || !stable_base) {
        fprintf(stderr, "oom\n");
        return 2;
    }

    for (i = 0; i < nrams; i++) {
        for (j = 0; j < nimages; j++) {
            struct cell *c = &cells[(size_t)i * nimages + j];
            long anchors[MAX_ANCHOR];
            int na, a;
            long cmp = images[j].n < region_len ? images[j].n : region_len;
            long k;
            uint32_t bases[MAX_ANCHOR * 8];
            int bcount[MAX_ANCHOR * 8];
            int nb = 0, best = 0;

            c->compared = cmp;
            for (k = 0; k < cmp; k++) {
                uint8_t rb = rams[i].buf[region_off + k], ib = images[j].buf[k];
                if (rb == ib)
                    c->equal++;
                if (!(rb == 0 && ib == 0)) {
                    c->nontrivial++;
                    if (rb == ib)
                        c->nontrivial_equal++;
                }
            }

            na = pick_anchors(&images[j], anchors);
            c->anchors_used = na;
            for (a = 0; a < na; a++) {
                const uint8_t *hay = rams[i].buf;
                size_t hayn = (size_t)rams[i].n;
                const uint8_t *hit = hay;
                size_t remaining = hayn;
                while (remaining >= ANCHOR_LEN) {
                    const uint8_t *p = memmem(hit, remaining, images[j].buf + anchors[a],
                                              ANCHOR_LEN);
                    uint32_t implied;
                    int b;
                    if (!p)
                        break;
                    implied = (uint32_t)(RAM_VA + (uint32_t)(p - hay) -
                                         (uint32_t)anchors[a]);
                    for (b = 0; b < nb; b++)
                        if (bases[b] == implied)
                            break;
                    if (b == nb && nb < (int)(sizeof bases / sizeof bases[0])) {
                        bases[nb] = implied;
                        bcount[nb] = 0;
                        nb++;
                    }
                    if (b < (int)(sizeof bases / sizeof bases[0]))
                        bcount[b]++;
                    remaining = hayn - (size_t)(p + 1 - hay);
                    hit = p + 1;
                }
            }
            c->distinct_anchor_bases = nb;
            for (a = 0; a < nb; a++) {
                if (bcount[a] > best) {
                    best = bcount[a];
                    c->anchor_base = bases[a];
                    c->anchor_base_valid = 1;
                }
            }
            c->anchor_base_agreeing = best;
        }
    }

    /* argmax of non-trivial agreement, per RAM; and anchor-base stability */
    for (j = 0; j < nimages; j++) {
        stable_base[j] = 1;
        for (i = 0; i < nrams; i++) {
            struct cell *c = &cells[(size_t)i * nimages + j];
            if (!(c->anchor_base_valid && c->anchor_base_agreeing >= 2 &&
                  c->anchor_base == base_va))
                stable_base[j] = 0;
        }
    }
    for (i = 0; i < nrams; i++) {
        double bestv = -1.0;
        int bestj = -1, ties = 0;
        for (j = 0; j < nimages; j++) {
            struct cell *c = &cells[(size_t)i * nimages + j];
            double v = c->nontrivial ? (double)c->nontrivial_equal / (double)c->nontrivial
                                     : -1.0;
            if (v > bestv) {
                bestv = v;
                bestj = j;
                ties = 1;
            } else if (v == bestv) {
                ties++;
            }
        }
        if (bestj >= 0 && ties == 1)
            argmax_wins[bestj]++;
    }
    for (j = 0; j < nimages; j++) {
        if (argmax_wins[j] == nrams && stable_base[j]) {
            pins++;
            pin_index = j;
        }
    }

    out = fopen(argv[1], "w");
    if (!out) {
        perror(argv[1]);
        return 2;
    }
    fprintf(out, "{\n");
    fprintf(out,
            " \"_comment\": \"Which overlay FILE is resident at region A in F08's "
            "fixtures, decided from bytes rather than from an address. Every level "
            "overlay loads at the same VA, so the VA cannot name a file. Also "
            "recomputes the cross-fixture diff the F08 row states as prose. "
            "Regenerate: tools/phase4_f08_overlay_residency_pin.c\",\n");
    fprintf(out, " \"schema\": \"abl-phase4-f08-overlay-residency-pin/1\",\n");
    fprintf(out, " \"generated_by\": \"tools/phase4_f08_overlay_residency_pin.c\",\n");
    fprintf(out, " \"declared_load_base\": \"0x%08" PRIx32 "\",\n", base_va);
    fprintf(out, " \"region_length\": %ld,\n", region_len);
    fprintf(out, " \"nontrivial_definition\": \"positions where NOT (ram_byte == 0 "
                 "&& image_byte == 0); zero-vs-zero agreement is excluded because "
                 "padding otherwise flatters every low-entropy image\",\n");
    fprintf(out, " \"anchor_rule\": \"%d-byte slices with >= %d distinct byte values, "
                 "up to %d per image, searched across all %u bytes of main RAM; >= 2 "
                 "slices agreeing on one implied base is residency evidence\",\n",
            ANCHOR_LEN, ANCHOR_MIN_DISTINCT, MAX_ANCHOR, RAM_SIZE);

    fprintf(out, " \"rams\": [\n");
    for (i = 0; i < nrams; i++)
        fprintf(out, "  {\"label\": \"%s\", \"path\": \"%s\", \"sha256\": \"%s\"}%s\n",
                rams[i].label, rams[i].path, rams[i].sha256, i + 1 == nrams ? "" : ",");
    fprintf(out, " ],\n \"images\": [\n");
    for (j = 0; j < nimages; j++) {
        fprintf(out,
                "  {\"path\": \"%s\", \"size\": %ld, \"sha1\": \"%s\", "
                "\"sha256\": \"%s\",\n   \"argmax_in_rams\": %d, "
                "\"stable_anchor_base_equals_declared\": %s,\n   \"per_ram\": [",
                images[j].path, images[j].n, images[j].sha1, images[j].sha256,
                argmax_wins[j], stable_base[j] ? "true" : "false");
        for (i = 0; i < nrams; i++) {
            struct cell *c = &cells[(size_t)i * nimages + j];
            fprintf(out,
                    "%s{\"ram\": \"%s\", \"compared\": %ld, \"equal\": %ld, "
                    "\"nontrivial\": %ld, \"nontrivial_equal\": %ld, "
                    "\"nontrivial_pct\": %.2f, \"anchors\": %d, "
                    "\"anchor_bases_seen\": %d, \"anchor_base_agreeing\": %d, "
                    "\"anchor_base\": ",
                    i ? ", " : "", rams[i].label, c->compared, c->equal, c->nontrivial,
                    c->nontrivial_equal,
                    c->nontrivial ? 100.0 * (double)c->nontrivial_equal /
                                    (double)c->nontrivial
                                  : 0.0,
                    c->anchors_used, c->distinct_anchor_bases, c->anchor_base_agreeing);
            if (c->anchor_base_valid)
                fprintf(out, "\"0x%08" PRIx32 "\"}", c->anchor_base);
            else
                fprintf(out, "null}");
        }
        fprintf(out, "]}%s\n", j + 1 == nimages ? "" : ",");
    }
    fprintf(out, " ],\n");
    {
        int n_argmax = 0, n_stable = 0;
        for (j = 0; j < nimages; j++) {
            if (argmax_wins[j] == nrams)
                n_argmax++;
            if (stable_base[j])
                n_stable++;
        }
        fprintf(out, " \"images_scanned\": %d,\n", nimages);
        fprintf(out, " \"rams_scanned\": %d,\n", nrams);
        fprintf(out, " \"images_argmax_in_every_ram\": %d,\n", n_argmax);
        fprintf(out, " \"images_with_stable_declared_base\": %d,\n", n_stable);
    }
    fprintf(out, " \"unique_pin\": %s,\n", pins == 1 ? "true" : "false");
    if (pins == 1) {
        fprintf(out, " \"unique_pin_file\": \"%s\",\n", images[pin_index].path);
        fprintf(out, " \"unique_pin_sha1\": \"%s\",\n", images[pin_index].sha1);
        fprintf(out, " \"unique_pin_sha256\": \"%s\",\n", images[pin_index].sha256);
        fprintf(out, " \"unique_pin_size\": %ld,\n", images[pin_index].n);
    } else {
        fprintf(out, " \"unique_pin_file\": null,\n \"unique_pin_sha1\": null,\n"
                     " \"unique_pin_sha256\": null,\n \"unique_pin_size\": null,\n");
    }

    /* runner-up, measured, so "unique" is not a bare adjective */
    if (pins == 1) {
        double win = 0.0, second = -1.0;
        const char *second_path = NULL;
        struct cell *c0 = &cells[(size_t)0 * nimages + pin_index];
        win = c0->nontrivial ? 100.0 * (double)c0->nontrivial_equal / (double)c0->nontrivial
                             : 0.0;
        for (j = 0; j < nimages; j++) {
            struct cell *c = &cells[(size_t)0 * nimages + j];
            double v = c->nontrivial ? 100.0 * (double)c->nontrivial_equal /
                                       (double)c->nontrivial
                                     : 0.0;
            if (j != pin_index && v > second) {
                second = v;
                second_path = images[j].path;
            }
        }
        fprintf(out, " \"first_ram_pin_nontrivial_pct\": %.2f,\n", win);
        fprintf(out, " \"first_ram_runner_up\": \"%s\",\n",
                second_path ? second_path : "");
        fprintf(out, " \"first_ram_runner_up_nontrivial_pct\": %.2f,\n", second);
    }

    /* cross-fixture diff: region A, the pinned extent, and all of RAM */
    {
        long diff_region = 0, diff_inside = 0, diff_outside = 0;
        long diff_words_ram = 0;
        long reported = 0;
        long pin_extent = pins == 1 ? images[pin_index].n : 0;
        uint32_t k;

        fprintf(out, " \"cross_fixture_diff\": {\n");
        fprintf(out, "  \"_note\": \"region A is sized for the LARGEST overlay, so most "
                     "of the window is not this overlay; a diff over the whole window "
                     "cannot speak for 'the overlay's static data'\",\n");
        fprintf(out, "  \"region_a_differing_bytes_detail\": [");
        for (k = 0; k < (uint32_t)region_len; k++) {
            uint8_t v0 = rams[0].buf[region_off + k];
            int differs = 0;
            for (i = 1; i < nrams; i++)
                if (rams[i].buf[region_off + k] != v0)
                    differs = 1;
            if (!differs)
                continue;
            diff_region++;
            if (pin_extent && k < (uint32_t)pin_extent)
                diff_inside++;
            else
                diff_outside++;
            if (reported < MAX_DIFF_REPORT) {
                int inside = (pin_extent && k < (uint32_t)pin_extent);
                fprintf(out, "%s{\"addr\": \"0x%08" PRIx32 "\", \"offset\": %u, "
                             "\"inside_pinned_image\": %s, \"disc_image_byte\": ",
                        reported ? ", " : "", base_va + k, k, inside ? "true" : "false");
                if (inside)
                    fprintf(out, "%u", images[pin_index].buf[k]);
                else
                    fprintf(out, "null");
                fprintf(out, ", \"matches_disc_image_in_any_fixture\": ");
                {
                    int any = 0;
                    if (inside)
                        for (i = 0; i < nrams; i++)
                            if (rams[i].buf[region_off + k] == images[pin_index].buf[k])
                                any = 1;
                    fprintf(out, "%s", inside ? (any ? "true" : "false") : "null");
                }
                fprintf(out, ", \"values\": [");
                for (i = 0; i < nrams; i++)
                    fprintf(out, "%s%u", i ? ", " : "", rams[i].buf[region_off + k]);
                fprintf(out, "]}");
                reported++;
            }
        }
        fprintf(out, "],\n");
        for (k = 0; k + 4 <= RAM_SIZE; k += 4) {
            uint32_t w0;
            int differs = 0;
            memcpy(&w0, rams[0].buf + k, 4);
            for (i = 1; i < nrams; i++) {
                uint32_t w;
                memcpy(&w, rams[i].buf + k, 4);
                if (w != w0) {
                    differs = 1;
                    break;
                }
            }
            if (differs)
                diff_words_ram++;
        }
        fprintf(out, "  \"rams_compared\": %d,\n", nrams);
        fprintf(out, "  \"region_a_bytes\": %ld,\n", region_len);
        fprintf(out, "  \"region_a_differing_bytes\": %ld,\n", diff_region);
        fprintf(out, "  \"pinned_image_extent\": %ld,\n", pin_extent);
        fprintf(out, "  \"region_a_differing_inside_pinned_image\": %ld,\n", diff_inside);
        fprintf(out, "  \"region_a_differing_beyond_pinned_image\": %ld,\n", diff_outside);
        fprintf(out, "  \"whole_ram_words\": %u,\n", RAM_SIZE / 4);
        fprintf(out, "  \"whole_ram_differing_words\": %ld,\n", diff_words_ram);
        fprintf(out, "  \"differing_bytes_reported\": %ld\n", reported);
        fprintf(out, " },\n");
    }

    /* The row's other prose claim: "the five saves are not a cumulative
     * progression (no subset-chain mask found in resident RAM)". A cumulative
     * objective mask would show up as a word whose five fixture values order
     * into a bitwise SUBSET CHAIN. That is testable exactly, so test it rather
     * than restate it -- and report the strict one-bit-per-step form separately,
     * since that is the shape "five performers, one bit each" would take. */
    if (nrams >= 2) {
        long chain32 = 0, strict32 = 0, chain16 = 0, strict16 = 0;
        long reported = 0;
        uint32_t k;

        fprintf(out, " \"subset_chain_search\": {\n");
        fprintf(out, "  \"_note\": \"a cumulative per-performer mask must order into a "
                     "bitwise subset chain across the fixtures; 'strict' additionally "
                     "requires exactly one new bit per step\",\n");
        fprintf(out, "  \"hits\": [");
        for (k = 0; k + 4 <= RAM_SIZE; k += 4) {
            uint32_t v32[MAX_RAMS], v16[MAX_RAMS];
            int w, allsame32 = 1, allsame16 = 1, ok32 = 1, ok16 = 1;
            int s32 = 1, s16 = 1;

            for (i = 0; i < nrams; i++) {
                memcpy(&v32[i], rams[i].buf + k, 4);
                v16[i] = v32[i] & 0xFFFFu;
                if (v32[i] != v32[0])
                    allsame32 = 0;
                if (v16[i] != v16[0])
                    allsame16 = 0;
            }
            /* insertion sort by popcount */
            for (w = 1; w < nrams; w++) {
                uint32_t a32 = v32[w], a16 = v16[w];
                int p = w - 1;
                while (p >= 0 && __builtin_popcount(v32[p]) > __builtin_popcount(a32)) {
                    v32[p + 1] = v32[p];
                    p--;
                }
                v32[p + 1] = a32;
                p = w - 1;
                while (p >= 0 && __builtin_popcount(v16[p]) > __builtin_popcount(a16)) {
                    v16[p + 1] = v16[p];
                    p--;
                }
                v16[p + 1] = a16;
            }
            for (i = 0; i + 1 < nrams; i++) {
                if ((v32[i] & v32[i + 1]) != v32[i])
                    ok32 = 0;
                if (__builtin_popcount(v32[i + 1]) != __builtin_popcount(v32[i]) + 1)
                    s32 = 0;
                if ((v16[i] & v16[i + 1]) != v16[i])
                    ok16 = 0;
                if (__builtin_popcount(v16[i + 1]) != __builtin_popcount(v16[i]) + 1)
                    s16 = 0;
            }
            if (!allsame32 && ok32) {
                chain32++;
                if (s32) {
                    strict32++;
                    if (reported < MAX_DIFF_REPORT) {
                        fprintf(out, "%s{\"addr\": \"0x%08" PRIx32 "\", \"width\": 32, "
                                     "\"values\": [",
                                reported ? ", " : "", RAM_VA + k);
                        for (i = 0; i < nrams; i++) {
                            uint32_t v;
                            memcpy(&v, rams[i].buf + k, 4);
                            fprintf(out, "%s\"0x%08" PRIx32 "\"", i ? ", " : "", v);
                        }
                        fprintf(out, "]}");
                        reported++;
                    }
                }
            }
            if (!allsame16 && ok16) {
                chain16++;
                if (s16)
                    strict16++;
            }
        }
        fprintf(out, "],\n");
        fprintf(out, "  \"u32_subset_chains\": %ld,\n", chain32);
        fprintf(out, "  \"u32_strict_one_bit_per_step_chains\": %ld,\n", strict32);
        fprintf(out, "  \"u16_subset_chains\": %ld,\n", chain16);
        fprintf(out, "  \"u16_strict_one_bit_per_step_chains\": %ld,\n", strict16);
        fprintf(out, "  \"hits_reported\": %ld\n", reported);
        fprintf(out, " },\n");
    }

    /* named words, supplied by the caller from a pinned artifact */
    {
        int varying = 0, inside = 0, zero_on_disc = 0;
        fprintf(out, " \"named_words\": [");
        for (i = 0; i < nwords; i++) {
            uint32_t a = words[i], off;
            int in_pin, k, varies = 0;
            uint32_t v0 = 0;

            if (a < RAM_VA || a - RAM_VA + 4 > RAM_SIZE) {
                fprintf(stderr, "word 0x%08" PRIx32 " outside main RAM\n", a);
                return 2;
            }
            off = a - RAM_VA;
            in_pin = (pin_index >= 0 && a >= base_va &&
                      a + 4 <= base_va + (uint32_t)images[pin_index].n);
            if (in_pin)
                inside++;
            fprintf(out, "%s{\"addr\": \"0x%08" PRIx32 "\", "
                         "\"inside_pinned_image\": %s, \"disc_image_u32\": ",
                    i ? ", " : "", a, in_pin ? "true" : "false");
            if (in_pin) {
                uint32_t dv;
                memcpy(&dv, images[pin_index].buf + (a - base_va), 4);
                fprintf(out, "%u", dv);
                if (dv == 0)
                    zero_on_disc++;
            } else {
                fprintf(out, "null");
            }
            fprintf(out, ", \"values\": [");
            for (k = 0; k < nrams; k++) {
                uint32_t v;
                memcpy(&v, rams[k].buf + off, 4);
                if (k == 0)
                    v0 = v;
                else if (v != v0)
                    varies = 1;
                fprintf(out, "%s%u", k ? ", " : "", v);
            }
            if (varies)
                varying++;
            fprintf(out, "], \"varies_across_fixtures\": %s}",
                    varies ? "true" : "false");
        }
        fprintf(out, "],\n");
        fprintf(out, " \"named_words_count\": %d,\n", nwords);
        fprintf(out, " \"named_words_inside_pinned_image\": %d,\n", inside);
        fprintf(out, " \"named_words_zero_in_disc_image\": %d,\n", zero_on_disc);
        fprintf(out, " \"named_words_varying_across_fixtures\": %d,\n", varying);
    }

    fprintf(out, " \"result\": \"%s\"\n}\n",
            pins == 1 ? "F08_OVERLAY_RESIDENCY_PIN_UNIQUE"
                      : "F08_OVERLAY_RESIDENCY_PIN_AMBIGUOUS");
    fclose(out);

    printf("scanned %d images against %d RAM images at 0x%08" PRIx32 "\n", nimages,
           nrams, base_va);
    if (pins == 1)
        printf("F08_OVERLAY_RESIDENCY_PIN_UNIQUE: %s\n", images[pin_index].path);
    else
        printf("F08_OVERLAY_RESIDENCY_PIN_AMBIGUOUS: %d surviving images\n", pins);
    return 0;
}
