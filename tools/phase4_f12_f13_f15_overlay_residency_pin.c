/* phase4_f12_f13_f15_overlay_residency_pin.c -- decide F12/F13/F15's overlay
 * identity, and their overlay-local state, from BYTES rather than from an
 * address.
 *
 * WHY THIS EXISTS
 * ---------------
 * SYSTEMIC DEFECT (a). Every per-level overlay in this game is CdRead-loaded to
 * the SAME virtual address (region A, 0x800B39A0). An address in that window
 * therefore names real content in almost every overlay image, and
 * analysis/phase3_ownership_graph.json stores no `image` field at all -- it
 * carries 0x800B39A0 as a bare state address with no owner. So every overlay
 * claim these three rows rest on is, as recorded, unfalsifiable:
 *
 *   F12_battle_arena     the D19 Molt session's guard-rollback writer, crowd
 *                        allocator call, defeat threshold and goal latch are
 *                        ALL overlay-local PCs in the 0x800B3xxx..0x800B4xxx
 *                        window;
 *   F13_anthill_two      the row records no overlay at all, while three
 *                        byte-matched C functions sit in the overlay the census
 *                        attributes to it;
 *   F15_canyon_showdown  the D20 Hopper session's on-screen health counter
 *                        (0x800B4BA8) and its one STILL_OPEN residual (the
 *                        overlay predicate at 0x800B3BD4) are both overlay-local.
 *
 * WHAT IT MEASURES, per (group x candidate image):
 *   1. AGREEMENT AT THE DECLARED BASE, byte-for-byte over min(file, region)
 *      bytes, reported raw AND over NON-TRIVIAL positions (both-zero excluded --
 *      counting zero-vs-zero padding flatters every low-entropy image).
 *   2. ANCHOR RESIDENCY AT ANY BASE. High-entropy 64-byte slices of the file are
 *      searched across all 2 MiB of RAM; >= 2 slices agreeing on one implied
 *      base is residency evidence, and the base is REPORTED, not assumed --
 *      that is what exposes a slice-matching false positive at a wandering base.
 *   3. Whether the image is the unique argmax of non-trivial agreement in EVERY
 *      RAM of the group AND has a stable anchor base equal to the declared one.
 *   One survivor is a file pin; more than one is a measured ambiguity that no
 *   artifact may paper over; zero means the claim under test is wrong.
 *
 * IT ALSO SIZES THE DEFECT INSTEAD OF ASSERTING IT. For every governing address
 * the caller supplies, the tool counts how many of the candidate images are
 * large enough to contain that offset at all (`images_containing_offset`) and,
 * for code addresses, decodes the word there in the pinned image and counts how
 * many other images carry the IDENTICAL word. "Ambiguous across 18 of 21 images"
 * is a measurement; "overlays share a base" is a slogan.
 *
 * IT READS THE SCENE ID OUT OF EVERY FIXTURE (the caller supplies the address
 * from the semantic registry, and never re-types it), because a fixture's NAME
 * is not evidence of the scene it holds -- one of these three rows declares a
 * fixture that is resident in a different stage's scene entirely.
 *
 * IT DECODES THE CAMPAIGN PROGRESSION TABLE from the pristine executable. The
 * ordinal -> scene mapping that routes each of these rows to a scene, and then
 * to an overlay, is currently a hand-typed Python list inside
 * tools/phase4_f_row_measured_census.py. Here it is read from the shipped bytes
 * and compared against the mapping a pinned artifact declares.
 *
 * No emulator is involved: RAM images come from the .sav containers via
 * tools/phase4_f08_save_ram.py. All byte and instruction decoding lives HERE, in
 * compiled C, per the project's standing rule.
 *
 * usage:
 *   phase4_f12_f13_f15_overlay_residency_pin OUT.json BASE_HEX REGION_LEN \
 *     --exe PATH:HEADER:LOADVA:SHA1 --progression ADDR:COUNT --scene-addr ADDR \
 *     --images FILE [FILE...] \
 *     --group LABEL --rams LABEL=PATH [LABEL=PATH...] \
 *       [--words ADDR[,ADDR...]] [--pcs ADDR[,ADDR...]] \
 *     [--group ...]
 * build:
 *   gcc -std=c11 -O2 -Wall -Wextra -Werror \
 *     tools/phase4_f12_f13_f15_overlay_residency_pin.c -o /tmp/f121315_pin -lcrypto
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
#define MAX_RAMS   8
#define MAX_IMAGES 64
#define MAX_GROUPS 8
#define MAX_ADDRS  96
#define MAX_ANCHOR 8
#define ANCHOR_LEN 64
#define ANCHOR_MIN_DISTINCT 32
#define MAX_DIFF_REPORT 96
#define MAX_PROGRESSION 32

struct ram {
    const char *label;
    const char *path;
    uint8_t *buf;
    long n;
    char sha256[65];
    uint32_t scene_id;
};

struct image {
    const char *path;
    uint8_t *buf;
    long n;
    char sha1[41];
    char sha256[65];
};

struct cell {
    long compared;
    long equal;
    long nontrivial;
    long nontrivial_equal;
    int anchors_used;
    int anchor_base_agreeing;
    uint32_t anchor_base;
    int anchor_base_valid;
    int distinct_anchor_bases;
};

struct group {
    const char *label;
    struct ram rams[MAX_RAMS];
    int nrams;
    uint32_t words[MAX_ADDRS];
    int nwords;
    uint32_t pcs[MAX_ADDRS];
    int npcs;
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

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

/* MIPS I primary opcodes, enough to say whether a word is a plausible
 * instruction and whether it is a load or a store. NULL = not decoded here. */
static const char *opname(uint32_t w, int *is_store, int *is_load)
{
    unsigned op = w >> 26;

    *is_store = 0;
    *is_load = 0;
    switch (op) {
    case 0x00: return w == 0 ? "nop" : "special";
    case 0x01: return "regimm";
    case 0x02: return "j";
    case 0x03: return "jal";
    case 0x04: return "beq";
    case 0x05: return "bne";
    case 0x06: return "blez";
    case 0x07: return "bgtz";
    case 0x08: return "addi";
    case 0x09: return "addiu";
    case 0x0a: return "slti";
    case 0x0b: return "sltiu";
    case 0x0c: return "andi";
    case 0x0d: return "ori";
    case 0x0e: return "xori";
    case 0x0f: return "lui";
    case 0x10: return "cop0";
    case 0x12: return "cop2";
    case 0x20: *is_load = 1; return "lb";
    case 0x21: *is_load = 1; return "lh";
    case 0x22: *is_load = 1; return "lwl";
    case 0x23: *is_load = 1; return "lw";
    case 0x24: *is_load = 1; return "lbu";
    case 0x25: *is_load = 1; return "lhu";
    case 0x26: *is_load = 1; return "lwr";
    case 0x28: *is_store = 1; return "sb";
    case 0x29: *is_store = 1; return "sh";
    case 0x2a: *is_store = 1; return "swl";
    case 0x2b: *is_store = 1; return "sw";
    case 0x2e: *is_store = 1; return "swr";
    case 0x32: *is_load = 1; return "lwc2";
    case 0x3a: *is_store = 1; return "swc2";
    default:   return NULL;
    }
}

/* Up to MAX_ANCHOR high-entropy slices, spread across the image. A padding or
 * repeated-pattern slice would match everywhere, so slices with fewer than
 * ANCHOR_MIN_DISTINCT distinct byte values are rejected outright. */
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

static int parse_addr_list(char *text, uint32_t *out, int cap)
{
    int n = 0;
    char *save = NULL, *tok = strtok_r(text, ",", &save);

    while (tok) {
        if (n >= cap) {
            fprintf(stderr, "too many addresses (max %d)\n", cap);
            exit(2);
        }
        out[n++] = (uint32_t)strtoul(tok, NULL, 16);
        tok = strtok_r(NULL, ",", &save);
    }
    return n;
}

int main(int argc, char **argv)
{
    struct image images[MAX_IMAGES];
    struct group groups[MAX_GROUPS];
    uint32_t base_va, region_off, scene_addr = 0, prog_addr = 0, exe_load_va = 0;
    long region_len, exe_header = 0, exe_n = 0;
    int nimages = 0, ngroups = 0, prog_count = 0, i, j, g;
    const char *exe_path = NULL, *exe_declared_sha1 = NULL;
    uint8_t *exe = NULL;
    char exe_sha1[41] = {0};
    FILE *out;
    int mode = 0;   /* 1 = images, 2 = rams */

    if (argc < 6) {
        fprintf(stderr,
                "usage: %s OUT.json BASE_HEX REGION_LEN --exe P:HDR:VA:SHA1 "
                "--progression ADDR:COUNT --scene-addr ADDR --images FILE... "
                "--group LABEL --rams L=P... [--words A,..] [--pcs A,..]...\n",
                argv[0]);
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
        if (!strcmp(argv[i], "--images")) {
            mode = 1;
            continue;
        }
        if (!strcmp(argv[i], "--rams")) {
            if (!ngroups) {
                fprintf(stderr, "--rams before any --group\n");
                return 2;
            }
            mode = 2;
            continue;
        }
        if (!strcmp(argv[i], "--group")) {
            if (++i >= argc) {
                fprintf(stderr, "--group needs a label\n");
                return 2;
            }
            if (ngroups >= MAX_GROUPS) {
                fprintf(stderr, "too many groups\n");
                return 2;
            }
            memset(&groups[ngroups], 0, sizeof groups[ngroups]);
            groups[ngroups].label = argv[i];
            ngroups++;
            mode = 0;
            continue;
        }
        if (!strcmp(argv[i], "--words") || !strcmp(argv[i], "--pcs")) {
            int words = !strcmp(argv[i], "--words");
            struct group *gp;
            if (!ngroups) {
                fprintf(stderr, "%s before any --group\n", argv[i]);
                return 2;
            }
            if (++i >= argc) {
                fprintf(stderr, "%s needs an address list\n", argv[i - 1]);
                return 2;
            }
            gp = &groups[ngroups - 1];
            if (words)
                gp->nwords = parse_addr_list(argv[i], gp->words, MAX_ADDRS);
            else
                gp->npcs = parse_addr_list(argv[i], gp->pcs, MAX_ADDRS);
            mode = 0;
            continue;
        }
        if (!strcmp(argv[i], "--scene-addr")) {
            if (++i >= argc) {
                fprintf(stderr, "--scene-addr needs an address\n");
                return 2;
            }
            scene_addr = (uint32_t)strtoul(argv[i], NULL, 16);
            mode = 0;
            continue;
        }
        if (!strcmp(argv[i], "--progression")) {
            char *colon;
            if (++i >= argc) {
                fprintf(stderr, "--progression needs ADDR:COUNT\n");
                return 2;
            }
            colon = strchr(argv[i], ':');
            if (!colon) {
                fprintf(stderr, "--progression must be ADDR:COUNT\n");
                return 2;
            }
            *colon = 0;
            prog_addr = (uint32_t)strtoul(argv[i], NULL, 16);
            prog_count = (int)strtol(colon + 1, NULL, 10);
            if (prog_count < 1 || prog_count > MAX_PROGRESSION) {
                fprintf(stderr, "--progression count out of range\n");
                return 2;
            }
            mode = 0;
            continue;
        }
        if (!strcmp(argv[i], "--exe")) {
            char *c1, *c2, *c3;
            if (++i >= argc) {
                fprintf(stderr, "--exe needs PATH:HEADER:LOADVA:SHA1\n");
                return 2;
            }
            c1 = strchr(argv[i], ':');
            c2 = c1 ? strchr(c1 + 1, ':') : NULL;
            c3 = c2 ? strchr(c2 + 1, ':') : NULL;
            if (!c1 || !c2 || !c3) {
                fprintf(stderr, "--exe must be PATH:HEADER:LOADVA:SHA1\n");
                return 2;
            }
            *c1 = *c2 = *c3 = 0;
            exe_path = argv[i];
            exe_header = strtol(c1 + 1, NULL, 10);
            exe_load_va = (uint32_t)strtoul(c2 + 1, NULL, 16);
            exe_declared_sha1 = c3 + 1;
            mode = 0;
            continue;
        }
        if (mode == 1) {
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
        } else if (mode == 2) {
            struct group *gp = &groups[ngroups - 1];
            char *eq = strchr(argv[i], '=');
            struct ram *r;
            if (!eq) {
                fprintf(stderr, "ram spec %s is not LABEL=PATH\n", argv[i]);
                return 2;
            }
            if (gp->nrams >= MAX_RAMS) {
                fprintf(stderr, "too many rams in group %s\n", gp->label);
                return 2;
            }
            *eq = 0;
            r = &gp->rams[gp->nrams];
            r->label = argv[i];
            r->path = eq + 1;
            r->buf = slurp(r->path, &r->n);
            if (r->n != (long)RAM_SIZE) {
                fprintf(stderr, "%s: expected a %u-byte RAM image, got %ld\n", r->path,
                        RAM_SIZE, r->n);
                return 2;
            }
            digest_hex(EVP_sha256(), r->buf, (size_t)r->n, r->sha256, 32);
            r->scene_id = scene_addr ? le32(r->buf + (scene_addr - RAM_VA)) : 0xFFFFFFFFu;
            gp->nrams++;
        } else {
            fprintf(stderr, "unexpected argument %s\n", argv[i]);
            return 2;
        }
    }
    if (!nimages || !ngroups) {
        fprintf(stderr, "need at least one image and one group\n");
        return 2;
    }
    for (g = 0; g < ngroups; g++)
        if (!groups[g].nrams) {
            fprintf(stderr, "group %s has no rams\n", groups[g].label);
            return 2;
        }
    if (!exe_path || !scene_addr || !prog_addr) {
        fprintf(stderr, "--exe, --scene-addr and --progression are all required\n");
        return 2;
    }
    exe = slurp(exe_path, &exe_n);
    digest_hex(EVP_sha1(), exe, (size_t)exe_n, exe_sha1, 20);

    out = fopen(argv[1], "w");
    if (!out) {
        perror(argv[1]);
        return 2;
    }

    fprintf(out, "{\n");
    fprintf(out,
            " \"_comment\": \"Which overlay FILE is resident in each of F12/F13/F15's "
            "own fixtures, decided from bytes; how ambiguous each governing address is "
            "across the candidate images; the scene id actually held by every fixture; "
            "and the campaign progression table read from the shipped executable. "
            "Regenerate: tools/phase4_f12_f13_f15_overlay_residency_pin.c\",\n");
    fprintf(out, " \"schema\": \"abl-phase4-f12-f13-f15-overlay-residency-pin/1\",\n");
    fprintf(out,
            " \"generated_by\": \"tools/phase4_f12_f13_f15_overlay_residency_pin.c\",\n");
    fprintf(out, " \"declared_load_base\": \"0x%08" PRIx32 "\",\n", base_va);
    fprintf(out, " \"region_length\": %ld,\n", region_len);
    fprintf(out, " \"scene_id_address\": \"0x%08" PRIx32 "\",\n", scene_addr);
    fprintf(out, " \"nontrivial_definition\": \"positions where NOT (ram_byte == 0 && "
                 "image_byte == 0); zero-vs-zero agreement is excluded because padding "
                 "otherwise flatters every low-entropy image\",\n");
    fprintf(out, " \"anchor_rule\": \"%d-byte slices with >= %d distinct byte values, up "
                 "to %d per image, searched across all %u bytes of main RAM; >= 2 slices "
                 "agreeing on one implied base is residency evidence\",\n",
            ANCHOR_LEN, ANCHOR_MIN_DISTINCT, MAX_ANCHOR, RAM_SIZE);

    /* the shipped executable, and the ordinal -> scene table inside it */
    fprintf(out, " \"executable\": {\"path\": \"%s\", \"size\": %ld, \"sha1\": \"%s\", "
                 "\"declared_sha1\": \"%s\", \"sha1_matches_declared\": %s, "
                 "\"header_bytes\": %ld, \"load_va\": \"0x%08" PRIx32 "\"},\n",
            exe_path, exe_n, exe_sha1, exe_declared_sha1,
            strcmp(exe_sha1, exe_declared_sha1) == 0 ? "true" : "false",
            exe_header, exe_load_va);
    fprintf(out, " \"campaign_progression_table\": {\"address\": \"0x%08" PRIx32 "\", "
                 "\"entry_count\": %d, \"ordinal_to_scene\": [",
            prog_addr, prog_count);
    for (i = 0; i < prog_count; i++) {
        long off = exe_header + (long)(prog_addr - exe_load_va) + 4 * i;
        if (off < 0 || off + 4 > exe_n) {
            fprintf(stderr, "progression entry %d falls outside the executable\n", i);
            return 2;
        }
        fprintf(out, "%s%" PRIu32, i ? ", " : "", le32(exe + off));
    }
    fprintf(out, "]},\n");

    fprintf(out, " \"images\": [\n");
    for (j = 0; j < nimages; j++)
        fprintf(out,
                "  {\"path\": \"%s\", \"size\": %ld, \"sha1\": \"%s\", \"sha256\": "
                "\"%s\"}%s\n",
                images[j].path, images[j].n, images[j].sha1, images[j].sha256,
                j + 1 == nimages ? "" : ",");
    fprintf(out, " ],\n \"images_scanned\": %d,\n \"groups\": [\n", nimages);

    for (g = 0; g < ngroups; g++) {
        struct group *gp = &groups[g];
        struct cell *cells = calloc((size_t)gp->nrams * (size_t)nimages, sizeof *cells);
        int *argmax_wins = calloc((size_t)nimages, sizeof *argmax_wins);
        int *stable_base = calloc((size_t)nimages, sizeof *stable_base);
        int pin_index = -1, pins = 0, n_argmax = 0, n_stable = 0;

        if (!cells || !argmax_wins || !stable_base) {
            fprintf(stderr, "oom\n");
            return 2;
        }

        for (i = 0; i < gp->nrams; i++) {
            for (j = 0; j < nimages; j++) {
                struct cell *c = &cells[(size_t)i * nimages + j];
                long anchors[MAX_ANCHOR];
                int na, a, nb = 0, best = 0;
                long cmp = images[j].n < region_len ? images[j].n : region_len;
                long k;
                uint32_t bases[MAX_ANCHOR * 8];
                int bcount[MAX_ANCHOR * 8];

                c->compared = cmp;
                for (k = 0; k < cmp; k++) {
                    uint8_t rb = gp->rams[i].buf[region_off + k], ib = images[j].buf[k];
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
                    const uint8_t *hay = gp->rams[i].buf;
                    size_t hayn = (size_t)gp->rams[i].n;
                    const uint8_t *hit = hay;
                    size_t remaining = hayn;
                    while (remaining >= ANCHOR_LEN) {
                        const uint8_t *p = memmem(hit, remaining,
                                                  images[j].buf + anchors[a], ANCHOR_LEN);
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
                for (a = 0; a < nb; a++)
                    if (bcount[a] > best) {
                        best = bcount[a];
                        c->anchor_base = bases[a];
                        c->anchor_base_valid = 1;
                    }
                c->anchor_base_agreeing = best;
            }
        }

        for (j = 0; j < nimages; j++) {
            stable_base[j] = 1;
            for (i = 0; i < gp->nrams; i++) {
                struct cell *c = &cells[(size_t)i * nimages + j];
                if (!(c->anchor_base_valid && c->anchor_base_agreeing >= 2 &&
                      c->anchor_base == base_va))
                    stable_base[j] = 0;
            }
        }
        for (i = 0; i < gp->nrams; i++) {
            double bestv = -1.0;
            int bestj = -1, ties = 0;
            for (j = 0; j < nimages; j++) {
                struct cell *c = &cells[(size_t)i * nimages + j];
                double v = c->nontrivial
                               ? (double)c->nontrivial_equal / (double)c->nontrivial
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
            if (argmax_wins[j] == gp->nrams)
                n_argmax++;
            if (stable_base[j])
                n_stable++;
            if (argmax_wins[j] == gp->nrams && stable_base[j]) {
                pins++;
                pin_index = j;
            }
        }

        fprintf(out, "  {\"label\": \"%s\",\n   \"rams\": [", gp->label);
        for (i = 0; i < gp->nrams; i++)
            fprintf(out,
                    "%s{\"label\": \"%s\", \"path\": \"%s\", \"sha256\": \"%s\", "
                    "\"scene_id\": %" PRIu32 "}",
                    i ? ", " : "", gp->rams[i].label, gp->rams[i].path,
                    gp->rams[i].sha256, gp->rams[i].scene_id);
        fprintf(out, "],\n   \"rams_scanned\": %d,\n", gp->nrams);
        {
            int same = 1;
            for (i = 1; i < gp->nrams; i++)
                if (gp->rams[i].scene_id != gp->rams[0].scene_id)
                    same = 0;
            fprintf(out, "   \"all_rams_same_scene_id\": %s,\n", same ? "true" : "false");
        }

        fprintf(out, "   \"per_image\": [\n");
        for (j = 0; j < nimages; j++) {
            fprintf(out,
                    "    {\"path\": \"%s\", \"argmax_in_rams\": %d, "
                    "\"stable_anchor_base_equals_declared\": %s, \"per_ram\": [",
                    images[j].path, argmax_wins[j], stable_base[j] ? "true" : "false");
            for (i = 0; i < gp->nrams; i++) {
                struct cell *c = &cells[(size_t)i * nimages + j];
                fprintf(out,
                        "%s{\"ram\": \"%s\", \"compared\": %ld, \"equal\": %ld, "
                        "\"nontrivial\": %ld, \"nontrivial_equal\": %ld, "
                        "\"nontrivial_pct\": %.2f, \"anchors\": %d, "
                        "\"anchor_bases_seen\": %d, \"anchor_base_agreeing\": %d, "
                        "\"anchor_base\": ",
                        i ? ", " : "", gp->rams[i].label, c->compared, c->equal,
                        c->nontrivial, c->nontrivial_equal,
                        c->nontrivial ? 100.0 * (double)c->nontrivial_equal /
                                            (double)c->nontrivial
                                      : 0.0,
                        c->anchors_used, c->distinct_anchor_bases,
                        c->anchor_base_agreeing);
                if (c->anchor_base_valid)
                    fprintf(out, "\"0x%08" PRIx32 "\"}", c->anchor_base);
                else
                    fprintf(out, "null}");
            }
            fprintf(out, "]}%s\n", j + 1 == nimages ? "" : ",");
        }
        fprintf(out, "   ],\n");
        fprintf(out, "   \"images_argmax_in_every_ram\": %d,\n", n_argmax);
        fprintf(out, "   \"images_with_stable_declared_base\": %d,\n", n_stable);
        fprintf(out, "   \"unique_pin\": %s,\n", pins == 1 ? "true" : "false");
        if (pins == 1) {
            fprintf(out, "   \"unique_pin_file\": \"%s\",\n", images[pin_index].path);
            fprintf(out, "   \"unique_pin_sha1\": \"%s\",\n", images[pin_index].sha1);
            fprintf(out, "   \"unique_pin_sha256\": \"%s\",\n", images[pin_index].sha256);
            fprintf(out, "   \"unique_pin_size\": %ld,\n", images[pin_index].n);
            fprintf(out, "   \"unique_pin_extent\": [\"0x%08" PRIx32 "\", \"0x%08" PRIx32
                         "\"],\n",
                    base_va, base_va + (uint32_t)images[pin_index].n);
        } else {
            fprintf(out, "   \"unique_pin_file\": null,\n   \"unique_pin_sha1\": null,\n"
                         "   \"unique_pin_sha256\": null,\n   \"unique_pin_size\": null,\n"
                         "   \"unique_pin_extent\": null,\n");
        }
        if (pins == 1) {
            struct cell *c0 = &cells[(size_t)0 * nimages + pin_index];
            double win = c0->nontrivial ? 100.0 * (double)c0->nontrivial_equal /
                                              (double)c0->nontrivial
                                        : 0.0;
            double second = -1.0;
            const char *second_path = NULL;
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
            fprintf(out, "   \"first_ram_pin_nontrivial_pct\": %.2f,\n", win);
            fprintf(out, "   \"first_ram_runner_up\": \"%s\",\n",
                    second_path ? second_path : "");
            fprintf(out, "   \"first_ram_runner_up_nontrivial_pct\": %.2f,\n", second);
        } else {
            fprintf(out, "   \"first_ram_pin_nontrivial_pct\": null,\n"
                         "   \"first_ram_runner_up\": null,\n"
                         "   \"first_ram_runner_up_nontrivial_pct\": null,\n");
        }

        /* cross-fixture diff -- only meaningful with two or more RAMs, and said
         * so rather than silently reporting zero difference from one sample. */
        {
            long diff_region = 0, diff_inside = 0, diff_outside = 0, reported = 0;
            long diff_words_ram = 0;
            long pin_extent = pins == 1 ? images[pin_index].n : 0;
            uint32_t k;

            fprintf(out, "   \"cross_fixture_diff\": {\"rams_compared\": %d, "
                         "\"meaningful\": %s,\n    \"_note\": \"region A is sized for the "
                         "LARGEST overlay, so most of the window is not this overlay; a "
                         "diff over the whole window cannot speak for this overlay's "
                         "state\",\n    \"differing_bytes_detail\": [",
                    gp->nrams, gp->nrams >= 2 ? "true" : "false");
            if (gp->nrams >= 2) {
                for (k = 0; k < (uint32_t)region_len; k++) {
                    uint8_t v0 = gp->rams[0].buf[region_off + k];
                    int differs = 0, inside;
                    for (i = 1; i < gp->nrams; i++)
                        if (gp->rams[i].buf[region_off + k] != v0)
                            differs = 1;
                    if (!differs)
                        continue;
                    diff_region++;
                    inside = (pin_extent && k < (uint32_t)pin_extent);
                    if (inside)
                        diff_inside++;
                    else
                        diff_outside++;
                    if (reported < MAX_DIFF_REPORT) {
                        fprintf(out,
                                "%s{\"addr\": \"0x%08" PRIx32 "\", \"offset\": %u, "
                                "\"inside_pinned_image\": %s, \"disc_image_byte\": ",
                                reported ? ", " : "", base_va + k, k,
                                inside ? "true" : "false");
                        if (inside)
                            fprintf(out, "%u", images[pin_index].buf[k]);
                        else
                            fprintf(out, "null");
                        fprintf(out, ", \"values\": [");
                        for (i = 0; i < gp->nrams; i++)
                            fprintf(out, "%s%u", i ? ", " : "",
                                    gp->rams[i].buf[region_off + k]);
                        fprintf(out, "]}");
                        reported++;
                    }
                }
                for (k = 0; k + 4 <= RAM_SIZE; k += 4) {
                    uint32_t w0 = le32(gp->rams[0].buf + k);
                    for (i = 1; i < gp->nrams; i++)
                        if (le32(gp->rams[i].buf + k) != w0) {
                            diff_words_ram++;
                            break;
                        }
                }
            }
            fprintf(out, "],\n    \"region_a_bytes\": %ld, \"region_a_differing_bytes\": "
                         "%ld, \"pinned_image_extent\": %ld, "
                         "\"region_a_differing_inside_pinned_image\": %ld, "
                         "\"region_a_differing_beyond_pinned_image\": %ld, "
                         "\"whole_ram_words\": %u, \"whole_ram_differing_words\": %ld, "
                         "\"differing_bytes_reported\": %ld},\n",
                    region_len, diff_region, pin_extent, diff_inside, diff_outside,
                    RAM_SIZE / 4, diff_words_ram, reported);
        }

        /* named state words supplied by the caller from pinned artifacts */
        {
            int varying = 0, inside = 0, zero_on_disc = 0, differs_from_disc = 0;
            fprintf(out, "   \"named_words\": [");
            for (i = 0; i < gp->nwords; i++) {
                uint32_t a = gp->words[i], off;
                int in_pin, k, varies = 0, in_range_images = 0, disc_known = 0;
                uint32_t v0 = 0, disc_value = 0;

                if (a < RAM_VA || a - RAM_VA + 4 > RAM_SIZE) {
                    fprintf(stderr, "word 0x%08" PRIx32 " outside main RAM\n", a);
                    return 2;
                }
                off = a - RAM_VA;
                for (j = 0; j < nimages; j++)
                    if (a >= base_va && (long)(a - base_va) + 4 <= images[j].n)
                        in_range_images++;
                in_pin = (pin_index >= 0 && a >= base_va &&
                          (long)(a - base_va) + 4 <= images[pin_index].n);
                if (in_pin)
                    inside++;
                fprintf(out,
                        "%s{\"addr\": \"0x%08" PRIx32 "\", \"inside_pinned_image\": %s, "
                        "\"images_containing_offset\": %d, \"disc_image_u32\": ",
                        i ? ", " : "", a, in_pin ? "true" : "false", in_range_images);
                if (in_pin) {
                    disc_value = le32(images[pin_index].buf + (a - base_va));
                    disc_known = 1;
                    fprintf(out, "%" PRIu32, disc_value);
                    if (disc_value == 0)
                        zero_on_disc++;
                } else {
                    fprintf(out, "null");
                }
                fprintf(out, ", \"values\": [");
                for (k = 0; k < gp->nrams; k++) {
                    uint32_t v = le32(gp->rams[k].buf + off);
                    if (k == 0)
                        v0 = v;
                    else if (v != v0)
                        varies = 1;
                    fprintf(out, "%s%" PRIu32, k ? ", " : "", v);
                }
                if (varies)
                    varying++;
                fprintf(out, "], \"varies_across_fixtures\": %s, "
                             "\"differs_from_disc_image\": ",
                        varies ? "true" : "false");
                if (disc_known) {
                    int any = 0;
                    for (k = 0; k < gp->nrams; k++)
                        if (le32(gp->rams[k].buf + off) != disc_value)
                            any = 1;
                    if (any)
                        differs_from_disc++;
                    fprintf(out, "%s}", any ? "true" : "false");
                } else {
                    fprintf(out, "null}");
                }
            }
            fprintf(out, "],\n   \"named_words_count\": %d, "
                         "\"named_words_inside_pinned_image\": %d, "
                         "\"named_words_zero_in_disc_image\": %d, "
                         "\"named_words_varying_across_fixtures\": %d, "
                         "\"named_words_differing_from_disc_image\": %d,\n",
                    gp->nwords, inside, zero_on_disc, varying, differs_from_disc);
        }

        /* governing code addresses: how ambiguous is each one, really? */
        {
            int inside = 0, decoded = 0, ambiguous_sum = 0;
            fprintf(out, "   \"governing_pcs\": [");
            for (i = 0; i < gp->npcs; i++) {
                uint32_t a = gp->pcs[i];
                int in_range_images = 0, same_word_images = 0, in_pin, is_store = 0,
                    is_load = 0;
                const char *nm = NULL;
                uint32_t w = 0;

                for (j = 0; j < nimages; j++)
                    if (a >= base_va && (long)(a - base_va) + 4 <= images[j].n)
                        in_range_images++;
                in_pin = (pin_index >= 0 && a >= base_va &&
                          (long)(a - base_va) + 4 <= images[pin_index].n);
                if (in_pin) {
                    inside++;
                    w = le32(images[pin_index].buf + (a - base_va));
                    nm = opname(w, &is_store, &is_load);
                    if (nm)
                        decoded++;
                    for (j = 0; j < nimages; j++)
                        if (a >= base_va && (long)(a - base_va) + 4 <= images[j].n &&
                            le32(images[j].buf + (a - base_va)) == w)
                            same_word_images++;
                }
                ambiguous_sum += in_range_images;
                fprintf(out,
                        "%s{\"pc\": \"0x%08" PRIx32 "\", \"inside_pinned_image\": %s, "
                        "\"images_containing_offset\": %d, \"word_in_pinned_image\": ",
                        i ? ", " : "", a, in_pin ? "true" : "false", in_range_images);
                if (in_pin) {
                    fprintf(out, "\"0x%08" PRIx32 "\", \"op\": %s%s%s, \"is_store\": %s, "
                                 "\"is_load\": %s, \"images_with_identical_word\": %d}",
                            w, nm ? "\"" : "", nm ? nm : "null", nm ? "\"" : "",
                            is_store ? "true" : "false", is_load ? "true" : "false",
                            same_word_images);
                } else {
                    fprintf(out, "null, \"op\": null, \"is_store\": null, \"is_load\": "
                                 "null, \"images_with_identical_word\": null}");
                }
            }
            fprintf(out, "],\n   \"governing_pcs_count\": %d, "
                         "\"governing_pcs_inside_pinned_image\": %d, "
                         "\"governing_pcs_decoding_to_an_instruction\": %d, "
                         "\"governing_pcs_mean_images_containing_offset\": %.2f,\n",
                    gp->npcs, inside, decoded,
                    gp->npcs ? (double)ambiguous_sum / (double)gp->npcs : 0.0);
        }

        fprintf(out, "   \"result\": \"%s\"}%s\n",
                pins == 1 ? "OVERLAY_RESIDENCY_PIN_UNIQUE"
                          : (pins == 0 ? "OVERLAY_RESIDENCY_PIN_NONE"
                                       : "OVERLAY_RESIDENCY_PIN_AMBIGUOUS"),
                g + 1 == ngroups ? "" : ",");

        printf("[%s] %d ram(s), scene_id", gp->label, gp->nrams);
        for (i = 0; i < gp->nrams; i++)
            printf(" %s=%" PRIu32, gp->rams[i].label, gp->rams[i].scene_id);
        printf(" -> %s\n", pins == 1 ? images[pin_index].path : "AMBIGUOUS/NONE");

        free(cells);
        free(argmax_wins);
        free(stable_base);
    }

    fprintf(out, " ],\n \"groups_scanned\": %d\n}\n", ngroups);
    fclose(out);
    printf("wrote %s (%d images, %d groups)\n", argv[1], nimages, ngroups);
    return 0;
}
