/* phase4_f05_f07_stage_identity_pin.c -- decide, FROM BYTES, which scene and
 * which overlay FILE two thin F rows actually own.
 *
 * WHY THIS EXISTS
 * ---------------
 * F05_riverbed_run and F07_city_entrance are the thinnest F rows: both are
 * `external_lead`, both declare `missing: "Implementation unresolved."`, and the
 * only analysis artifact either cites is a SHARED one (the F08 scene-asset
 * binding). Before any assessment may say anything at all about their code or
 * state, three things have to be settled by measurement, because each has
 * already produced a wrong published claim in this repository:
 *
 *  1. STAGE ORDINAL != SCENE ID. The baseline's `stages` field is an ORDINAL.
 *     The campaign progression table at 0x80077FA0 maps ordinal -> scene id.
 *     Twelve rows once quoted the wrong asset because they conflated an ordinal,
 *     a scene id and a disc-directory number. So the table is DECODED here from
 *     the pristine executable rather than restated.
 *
 *  2. EVERY PER-LEVEL OVERLAY LOADS AT THE SAME VA (region A, 0x800B39A0). An
 *     address in that window names real content in almost every overlay image,
 *     so an address-only attribution picks whichever image was enumerated first.
 *     This tool decides residency from bytes: agreement at the declared base
 *     over NON-TRIVIAL positions (zero-vs-zero excluded), plus anchor residency
 *     at ANY base with the implied base REPORTED, so a slice-matching false
 *     positive at a wandering base cannot be mistaken for the resident image.
 *
 *  3. A CLAIM ABOUT AN OVERLAY-LOCAL ADDRESS MADE BY ANOTHER ROW IS NOT
 *     EVIDENCE FOR THIS ROW UNTIL THE IMAGE IS PINNED. `--claim` takes ranges
 *     another artifact attributes to this stage and reports, per range, whether
 *     it lies inside the pinned image's extent and whether the RAM bytes equal
 *     the pinned disc image's bytes there. That converts "an address in the
 *     shared window" into "these bytes, in this file, resident in this fixture".
 *
 * It also reads the scene id straight out of each fixture's RAM, so the row's
 * declared fixtures are proved to BE that stage instead of being assumed from
 * their file names -- the file names use stage numbering while disc directories
 * and overlay images use scene numbering, and the two disagree for 14 of 16
 * stages.
 *
 * No emulator is involved. RAM images come from the .sav containers via
 * tools/phase4_f08_save_ram.py. All byte and instruction decoding lives here,
 * in compiled C, per the project's standing rule.
 *
 * usage:
 *   phase4_f05_f07_stage_identity_pin OUT.json \
 *     --row-id ID --stage-ordinal N --declared-scene N \
 *     --exe PATH --scene-table 0xADDR --scene-table-count N \
 *     --jump-table 0xADDR --jump-table-count N \
 *     --string-table 0xADDR --string-stride N --string-count N --bank-index N \
 *     --code-pc 0xADDR [--code-pc 0xADDR ...] \
 *     --scene-id-addr 0xADDR --scene-slot-addr 0xADDR \
 *     --base 0xADDR --region-len N \
 *     --rams LABEL=PATH [LABEL=PATH ...] --images FILE [FILE ...] \
 *     [--words 0xADDR[,0xADDR...]] [--claim NAME=0xSTART:0xEND ...]
 * build:
 *   gcc -std=c11 -O2 -Wall -Wextra -Werror \
 *     tools/phase4_f05_f07_stage_identity_pin.c -o /tmp/f0507_pin -lcrypto
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
#define EXE_HEADER 2048u
#define MAX_RAMS   16
#define MAX_IMAGES 64
#define MAX_ANCHOR 8
#define ANCHOR_LEN 64
#define ANCHOR_MIN_DISTINCT 32
#define MAX_WORDS  64
#define MAX_CLAIMS 32
#define MAX_PCS    32
#define MAX_TABLE  64
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

struct claim {
    const char *name;
    uint32_t start;
    uint32_t end;
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

/* ------------------------------------------------------------------ */
/* the pristine executable: VA <-> file offset, and a small MIPS decoder */
/* ------------------------------------------------------------------ */

struct exe {
    uint8_t *buf;
    long n;
    uint32_t load_addr;
    char sha1[41];
    char sha256[65];
};

static const uint8_t *exe_at(const struct exe *e, uint32_t va, uint32_t len)
{
    uint32_t off;

    if (va < e->load_addr)
        return NULL;
    off = EXE_HEADER + (va - e->load_addr);
    if ((long)off + (long)len > e->n)
        return NULL;
    return e->buf + off;
}

static uint32_t exe_u32(const struct exe *e, uint32_t va)
{
    const uint8_t *p = exe_at(e, va, 4);
    uint32_t v;

    if (!p) {
        fprintf(stderr, "0x%08" PRIx32 " is outside the executable image\n", va);
        exit(2);
    }
    memcpy(&v, p, 4);
    return v;
}

/* Decode only what this tool has to be able to name. Anything else is reported
 * by its raw fields, never guessed: a wrong mnemonic in an evidence artifact is
 * worse than no mnemonic. */
static void mips_decode(uint32_t w, char *out, size_t outn)
{
    unsigned op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
    unsigned rd = (w >> 11) & 31, sh = (w >> 6) & 31, fn = w & 63;
    int16_t simm = (int16_t)(w & 0xFFFF);
    unsigned uimm = w & 0xFFFF;

    switch (op) {
    case 0x00:
        if (w == 0) {
            snprintf(out, outn, "nop");
        } else if (fn == 0x08) {
            snprintf(out, outn, "jr $%u", rs);
        } else if (fn == 0x09) {
            snprintf(out, outn, "jalr $%u, $%u", rd, rs);
        } else if (fn == 0x21) {
            snprintf(out, outn, "addu $%u, $%u, $%u", rd, rs, rt);
        } else if (fn == 0x23) {
            snprintf(out, outn, "subu $%u, $%u, $%u", rd, rs, rt);
        } else if (fn == 0x00) {
            snprintf(out, outn, "sll $%u, $%u, %u", rd, rt, sh);
        } else if (fn == 0x02) {
            snprintf(out, outn, "srl $%u, $%u, %u", rd, rt, sh);
        } else if (fn == 0x25) {
            snprintf(out, outn, "or $%u, $%u, $%u", rd, rs, rt);
        } else if (fn == 0x24) {
            snprintf(out, outn, "and $%u, $%u, $%u", rd, rs, rt);
        } else {
            snprintf(out, outn, "special fn=0x%02x rs=%u rt=%u rd=%u", fn, rs, rt, rd);
        }
        break;
    case 0x02: snprintf(out, outn, "j 0x%08" PRIx32, (w & 0x03FFFFFFu) << 2); break;
    case 0x03: snprintf(out, outn, "jal 0x%08" PRIx32, (w & 0x03FFFFFFu) << 2); break;
    case 0x04: snprintf(out, outn, "beq $%u, $%u, %d", rs, rt, simm); break;
    case 0x05: snprintf(out, outn, "bne $%u, $%u, %d", rs, rt, simm); break;
    case 0x08: snprintf(out, outn, "addi $%u, $%u, %d", rt, rs, simm); break;
    case 0x09: snprintf(out, outn, "addiu $%u, $%u, %d", rt, rs, simm); break;
    case 0x0A: snprintf(out, outn, "slti $%u, $%u, %d", rt, rs, simm); break;
    case 0x0B: snprintf(out, outn, "sltiu $%u, $%u, %d", rt, rs, simm); break;
    case 0x0C: snprintf(out, outn, "andi $%u, $%u, 0x%04x", rt, rs, uimm); break;
    case 0x0D: snprintf(out, outn, "ori $%u, $%u, 0x%04x", rt, rs, uimm); break;
    case 0x0F: snprintf(out, outn, "lui $%u, 0x%04x", rt, uimm); break;
    case 0x23: snprintf(out, outn, "lw $%u, %d($%u)", rt, simm, rs); break;
    case 0x2B: snprintf(out, outn, "sw $%u, %d($%u)", rt, simm, rs); break;
    default:   snprintf(out, outn, "op=0x%02x rs=%u rt=%u imm=0x%04x", op, rs, rt, uimm);
    }
}

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

static void json_escape(const char *s, char *out, size_t outn)
{
    size_t o = 0;
    for (; *s && o + 7 < outn; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') {
            out[o++] = '\\';
            out[o++] = (char)c;
        } else if (c >= 0x20 && c < 0x7F) {
            out[o++] = (char)c;
        } else {
            o += (size_t)snprintf(out + o, outn - o, "\\u%04x", c);
        }
    }
    out[o] = 0;
}

static uint32_t hex_arg(const char *s)
{
    return (uint32_t)strtoul(s, NULL, 0);
}

int main(int argc, char **argv)
{
    struct ram rams[MAX_RAMS];
    struct image images[MAX_IMAGES];
    struct claim claims[MAX_CLAIMS];
    uint32_t words[MAX_WORDS], code_pcs[MAX_PCS];
    struct exe exe = {0};
    const char *out_path = NULL, *row_id = "", *exe_path = NULL;
    long stage_ordinal = -1, declared_scene = -1, bank_index = -1;
    uint32_t scene_table = 0, jump_table = 0, string_table = 0;
    long scene_table_count = 0, jump_table_count = 0, string_stride = 0,
         string_count = 0;
    uint32_t scene_id_addr = 0, scene_slot_addr = 0, base_va = 0, region_off;
    long region_len = 0;
    int nrams = 0, nimages = 0, nwords = 0, nclaims = 0, npcs = 0;
    int i, j, mode = 0;
    FILE *out;
    struct cell *cells;
    int *argmax_wins, *stable_base;
    int pin_index = -1, pins = 0;
    long pin_extent = 0;

    if (argc < 3) {
        fprintf(stderr, "usage: %s OUT.json --row-id ID ... (see file header)\n",
                argv[0]);
        return 2;
    }
    out_path = argv[1];

    for (i = 2; i < argc; i++) {
        const char *a = argv[i];
#define NEXT() (++i < argc ? argv[i] : (fprintf(stderr, "%s needs a value\n", a), exit(2), ""))
        if (!strcmp(a, "--rams")) { mode = 1; continue; }
        if (!strcmp(a, "--images")) { mode = 2; continue; }
        if (!strcmp(a, "--words")) { mode = 3; continue; }
        if (!strcmp(a, "--claim")) { mode = 4; continue; }
        if (a[0] == '-' && a[1] == '-') {
            mode = 0;
            if (!strcmp(a, "--row-id")) row_id = NEXT();
            else if (!strcmp(a, "--stage-ordinal")) stage_ordinal = strtol(NEXT(), NULL, 0);
            else if (!strcmp(a, "--declared-scene")) declared_scene = strtol(NEXT(), NULL, 0);
            else if (!strcmp(a, "--exe")) exe_path = NEXT();
            else if (!strcmp(a, "--scene-table")) scene_table = hex_arg(NEXT());
            else if (!strcmp(a, "--scene-table-count")) scene_table_count = strtol(NEXT(), NULL, 0);
            else if (!strcmp(a, "--jump-table")) jump_table = hex_arg(NEXT());
            else if (!strcmp(a, "--jump-table-count")) jump_table_count = strtol(NEXT(), NULL, 0);
            else if (!strcmp(a, "--string-table")) string_table = hex_arg(NEXT());
            else if (!strcmp(a, "--string-stride")) string_stride = strtol(NEXT(), NULL, 0);
            else if (!strcmp(a, "--string-count")) string_count = strtol(NEXT(), NULL, 0);
            else if (!strcmp(a, "--bank-index")) bank_index = strtol(NEXT(), NULL, 0);
            else if (!strcmp(a, "--scene-id-addr")) scene_id_addr = hex_arg(NEXT());
            else if (!strcmp(a, "--scene-slot-addr")) scene_slot_addr = hex_arg(NEXT());
            else if (!strcmp(a, "--base")) base_va = hex_arg(NEXT());
            else if (!strcmp(a, "--region-len")) region_len = strtol(NEXT(), NULL, 0);
            else if (!strcmp(a, "--code-pc")) {
                if (npcs >= MAX_PCS) { fprintf(stderr, "too many --code-pc\n"); return 2; }
                code_pcs[npcs++] = hex_arg(NEXT());
            } else {
                fprintf(stderr, "unknown option %s\n", a);
                return 2;
            }
            continue;
        }
        if (mode == 1) {
            char *eq = strchr(argv[i], '=');
            if (!eq) { fprintf(stderr, "ram spec %s is not LABEL=PATH\n", argv[i]); return 2; }
            if (nrams >= MAX_RAMS) { fprintf(stderr, "too many rams\n"); return 2; }
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
            if (nimages >= MAX_IMAGES) { fprintf(stderr, "too many images\n"); return 2; }
            images[nimages].path = argv[i];
            images[nimages].buf = slurp(argv[i], &images[nimages].n);
            digest_hex(EVP_sha1(), images[nimages].buf, (size_t)images[nimages].n,
                       images[nimages].sha1, 20);
            digest_hex(EVP_sha256(), images[nimages].buf, (size_t)images[nimages].n,
                       images[nimages].sha256, 32);
            nimages++;
        } else if (mode == 3) {
            char *save = NULL, *tok = strtok_r(argv[i], ",", &save);
            while (tok) {
                if (nwords >= MAX_WORDS) { fprintf(stderr, "too many words\n"); return 2; }
                words[nwords++] = hex_arg(tok);
                tok = strtok_r(NULL, ",", &save);
            }
        } else if (mode == 4) {
            char *eq = strchr(argv[i], '='), *colon;
            if (!eq) { fprintf(stderr, "claim %s is not NAME=START:END\n", argv[i]); return 2; }
            *eq = 0;
            colon = strchr(eq + 1, ':');
            if (!colon) { fprintf(stderr, "claim %s is not NAME=START:END\n", argv[i]); return 2; }
            *colon = 0;
            if (nclaims >= MAX_CLAIMS) { fprintf(stderr, "too many claims\n"); return 2; }
            claims[nclaims].name = argv[i];
            claims[nclaims].start = hex_arg(eq + 1);
            claims[nclaims].end = hex_arg(colon + 1);
            if (claims[nclaims].end <= claims[nclaims].start) {
                fprintf(stderr, "claim %s has end <= start\n", argv[i]);
                return 2;
            }
            nclaims++;
        } else {
            fprintf(stderr, "unexpected argument %s\n", argv[i]);
            return 2;
        }
#undef NEXT
    }

    if (!exe_path || !nrams || !nimages || !base_va || region_len <= 0) {
        fprintf(stderr, "need --exe, --base, --region-len, >=1 ram and >=1 image\n");
        return 2;
    }
    if (base_va < RAM_VA) { fprintf(stderr, "bad base\n"); return 2; }
    region_off = base_va - RAM_VA;
    if (region_off + (uint32_t)region_len > RAM_SIZE) {
        fprintf(stderr, "region does not fit in main RAM\n");
        return 2;
    }
    if (scene_table_count > MAX_TABLE || jump_table_count > MAX_TABLE) {
        fprintf(stderr, "table count too large\n");
        return 2;
    }

    exe.buf = slurp(exe_path, &exe.n);
    if (exe.n < (long)EXE_HEADER + 4) { fprintf(stderr, "exe too small\n"); return 2; }
    memcpy(&exe.load_addr, exe.buf + 0x18, 4);
    digest_hex(EVP_sha1(), exe.buf, (size_t)exe.n, exe.sha1, 20);
    digest_hex(EVP_sha256(), exe.buf, (size_t)exe.n, exe.sha256, 32);

    cells = calloc((size_t)nrams * (size_t)nimages, sizeof *cells);
    argmax_wins = calloc((size_t)nimages, sizeof *argmax_wins);
    stable_base = calloc((size_t)nimages, sizeof *stable_base);
    if (!cells || !argmax_wins || !stable_base) { fprintf(stderr, "oom\n"); return 2; }

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
            if (v > bestv) { bestv = v; bestj = j; ties = 1; }
            else if (v == bestv) { ties++; }
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
    if (pins == 1)
        pin_extent = images[pin_index].n;

    out = fopen(out_path, "w");
    if (!out) { perror(out_path); return 2; }

    fprintf(out, "{\n");
    fprintf(out,
            " \"_comment\": \"Stage identity for one thin F row, decided from bytes: "
            "ordinal->scene from the campaign progression table, the level-data "
            "arithmetic decoded from the pristine executable, the scene id read out "
            "of each fixture's RAM, and the resident overlay FILE pinned against "
            "every candidate image (every per-level overlay loads at the same VA, so "
            "an address cannot name a file). Regenerate: "
            "tools/phase4_f05_f07_stage_identity_pin.c\",\n");
    fprintf(out, " \"schema\": \"abl-phase4-f05-f07-stage-identity-pin/1\",\n");
    fprintf(out, " \"generated_by\": \"tools/phase4_f05_f07_stage_identity_pin.c\",\n");
    fprintf(out, " \"row_id\": \"%s\",\n", row_id);
    fprintf(out, " \"stage_ordinal\": %ld,\n", stage_ordinal);
    fprintf(out, " \"declared_scene_id\": %ld,\n", declared_scene);
    fprintf(out, " \"executable\": {\"path\": \"%s\", \"size\": %ld, \"sha1\": \"%s\", "
                 "\"sha256\": \"%s\", \"load_addr\": \"0x%08" PRIx32 "\"},\n",
            exe_path, exe.n, exe.sha1, exe.sha256, exe.load_addr);

    /* 1. ordinal -> scene, decoded */
    {
        long scene_at_ordinal = -1;
        fprintf(out, " \"campaign_progression_table\": {\"address\": \"0x%08" PRIx32 "\", "
                     "\"count\": %ld, \"scenes\": [", scene_table, scene_table_count);
        for (i = 0; i < scene_table_count; i++) {
            uint32_t v = exe_u32(&exe, scene_table + 4u * (uint32_t)i);
            fprintf(out, "%s%" PRIu32, i ? ", " : "", v);
            if (i == stage_ordinal)
                scene_at_ordinal = (long)v;
        }
        fprintf(out, "],\n  \"scene_at_this_stage_ordinal\": %ld,\n", scene_at_ordinal);
        fprintf(out, "  \"matches_declared_scene\": %s},\n",
                scene_at_ordinal == declared_scene ? "true" : "false");
    }

    /* 2. the instructions the shared binding artifact pins */
    fprintf(out, " \"decoded_instructions\": [");
    for (i = 0; i < npcs; i++) {
        uint32_t w = exe_u32(&exe, code_pcs[i]);
        char dis[96], esc[256];
        mips_decode(w, dis, sizeof dis);
        json_escape(dis, esc, sizeof esc);
        fprintf(out, "%s{\"pc\": \"0x%08" PRIx32 "\", \"word\": \"0x%08" PRIx32 "\", "
                     "\"decoded\": \"%s\"}", i ? ", " : "", code_pcs[i], w, esc);
    }
    fprintf(out, "],\n");

    /* 3. dispatcher jump table + the sound-bank string this row reaches */
    fprintf(out, " \"jump_table\": {\"address\": \"0x%08" PRIx32 "\", \"count\": %ld, "
                 "\"entries\": [", jump_table, jump_table_count);
    for (i = 0; i < jump_table_count; i++) {
        uint32_t v = exe_u32(&exe, jump_table + 4u * (uint32_t)i);
        fprintf(out, "%s\"0x%08" PRIx32 "\"", i ? ", " : "", v);
    }
    fprintf(out, "],\n  \"entry_for_declared_scene\": ");
    if (declared_scene >= 1 && declared_scene <= jump_table_count)
        fprintf(out, "\"0x%08" PRIx32 "\"",
                exe_u32(&exe, jump_table + 4u * (uint32_t)(declared_scene - 1)));
    else
        fprintf(out, "null");
    fprintf(out, ",\n  \"distinct_entries\": ");
    {
        uint32_t seen[MAX_TABLE];
        int ns = 0, k;
        for (i = 0; i < jump_table_count; i++) {
            uint32_t v = exe_u32(&exe, jump_table + 4u * (uint32_t)i);
            for (k = 0; k < ns; k++)
                if (seen[k] == v)
                    break;
            if (k == ns && ns < MAX_TABLE)
                seen[ns++] = v;
        }
        fprintf(out, "%d},\n", ns);
    }

    fprintf(out, " \"sound_bank_string_table\": {\"address\": \"0x%08" PRIx32 "\", "
                 "\"stride\": %ld, \"count\": %ld, \"bank_index_for_this_scene\": %ld, "
                 "\"prefix_for_this_scene\": ",
            string_table, string_stride, string_count, bank_index);
    if (string_table && bank_index >= 0 && bank_index < string_count) {
        const uint8_t *p = exe_at(&exe, string_table +
                                        (uint32_t)(bank_index * string_stride),
                                  (uint32_t)string_stride);
        char raw[MAX_TABLE], esc[256];
        long k;
        if (!p) { fprintf(stderr, "string table outside image\n"); return 2; }
        for (k = 0; k < string_stride && k < (long)sizeof raw - 1 && p[k]; k++)
            raw[k] = (char)p[k];
        raw[k] = 0;
        json_escape(raw, esc, sizeof esc);
        fprintf(out, "\"%s\"", esc);
    } else {
        fprintf(out, "null");
    }
    fprintf(out, "},\n");

    /* 4. the fixtures: is each one really this scene? */
    fprintf(out, " \"rams\": [\n");
    for (i = 0; i < nrams; i++) {
        uint32_t sid = 0, slot = 0;
        int slot_ok = 0;
        long table_scene = -1;
        memcpy(&sid, rams[i].buf + (scene_id_addr - RAM_VA), 4);
        if (scene_slot_addr) {
            memcpy(&slot, rams[i].buf + (scene_slot_addr - RAM_VA), 2);
            slot &= 0xFFFFu;
            if ((long)slot < scene_table_count) {
                table_scene = (long)exe_u32(&exe, scene_table + 4u * slot);
                slot_ok = (table_scene == (long)sid);
            }
        }
        fprintf(out, "  {\"label\": \"%s\", \"path\": \"%s\", \"sha256\": \"%s\", "
                     "\"scene_id\": %" PRIu32 ", \"scene_id_matches_declared\": %s, "
                     "\"scene_slot_index\": %" PRIu32 ", "
                     "\"progression_table_at_slot\": %ld, "
                     "\"slot_resolves_to_scene_id\": %s}%s\n",
                rams[i].label, rams[i].path, rams[i].sha256, sid,
                (long)sid == declared_scene ? "true" : "false", slot, table_scene,
                slot_ok ? "true" : "false", i + 1 == nrams ? "" : ",");
    }
    fprintf(out, " ],\n");

    /* 5. which overlay FILE is resident */
    fprintf(out, " \"declared_load_base\": \"0x%08" PRIx32 "\",\n", base_va);
    fprintf(out, " \"region_length\": %ld,\n", region_len);
    fprintf(out, " \"nontrivial_definition\": \"positions where NOT (ram_byte == 0 && "
                 "image_byte == 0); zero-vs-zero agreement is excluded because padding "
                 "otherwise flatters every low-entropy image\",\n");
    fprintf(out, " \"anchor_rule\": \"%d-byte slices with >= %d distinct byte values, up "
                 "to %d per image, searched across all %u bytes of main RAM; >= 2 slices "
                 "agreeing on one implied base is residency evidence\",\n",
            ANCHOR_LEN, ANCHOR_MIN_DISTINCT, MAX_ANCHOR, RAM_SIZE);
    fprintf(out, " \"images\": [\n");
    for (j = 0; j < nimages; j++) {
        fprintf(out, "  {\"path\": \"%s\", \"size\": %ld, \"sha1\": \"%s\", "
                     "\"sha256\": \"%s\",\n   \"argmax_in_rams\": %d, "
                     "\"stable_anchor_base_equals_declared\": %s,\n   \"per_ram\": [",
                images[j].path, images[j].n, images[j].sha1, images[j].sha256,
                argmax_wins[j], stable_base[j] ? "true" : "false");
        for (i = 0; i < nrams; i++) {
            struct cell *c = &cells[(size_t)i * nimages + j];
            fprintf(out, "%s{\"ram\": \"%s\", \"compared\": %ld, \"equal\": %ld, "
                         "\"nontrivial\": %ld, \"nontrivial_equal\": %ld, "
                         "\"nontrivial_pct\": %.2f, \"anchors\": %d, "
                         "\"anchor_bases_seen\": %d, \"anchor_base_agreeing\": %d, "
                         "\"anchor_base\": ",
                    i ? ", " : "", rams[i].label, c->compared, c->equal, c->nontrivial,
                    c->nontrivial_equal,
                    c->nontrivial ? 100.0 * (double)c->nontrivial_equal /
                                    (double)c->nontrivial : 0.0,
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
            if (argmax_wins[j] == nrams) n_argmax++;
            if (stable_base[j]) n_stable++;
        }
        fprintf(out, " \"images_scanned\": %d,\n", nimages);
        fprintf(out, " \"rams_scanned\": %d,\n", nrams);
        fprintf(out, " \"images_argmax_in_every_ram\": %d,\n", n_argmax);
        fprintf(out, " \"images_with_stable_declared_base\": %d,\n", n_stable);
    }
    fprintf(out, " \"unique_pin\": %s,\n", pins == 1 ? "true" : "false");
    if (pins == 1) {
        double win, second = -1.0;
        const char *second_path = NULL;
        struct cell *c0 = &cells[pin_index];
        win = c0->nontrivial ? 100.0 * (double)c0->nontrivial_equal /
                               (double)c0->nontrivial : 0.0;
        for (j = 0; j < nimages; j++) {
            struct cell *c = &cells[j];
            double v = c->nontrivial ? 100.0 * (double)c->nontrivial_equal /
                                       (double)c->nontrivial : 0.0;
            if (j != pin_index && v > second) { second = v; second_path = images[j].path; }
        }
        fprintf(out, " \"unique_pin_file\": \"%s\",\n", images[pin_index].path);
        fprintf(out, " \"unique_pin_sha1\": \"%s\",\n", images[pin_index].sha1);
        fprintf(out, " \"unique_pin_sha256\": \"%s\",\n", images[pin_index].sha256);
        fprintf(out, " \"unique_pin_size\": %ld,\n", pin_extent);
        fprintf(out, " \"pinned_extent\": [\"0x%08" PRIx32 "\", \"0x%08" PRIx32 "\"],\n",
                base_va, base_va + (uint32_t)pin_extent);
        fprintf(out, " \"first_ram_pin_nontrivial_pct\": %.2f,\n", win);
        fprintf(out, " \"first_ram_runner_up\": \"%s\",\n", second_path ? second_path : "");
        fprintf(out, " \"first_ram_runner_up_nontrivial_pct\": %.2f,\n", second);
    } else {
        fprintf(out, " \"unique_pin_file\": null,\n \"unique_pin_sha1\": null,\n"
                     " \"unique_pin_sha256\": null,\n \"unique_pin_size\": null,\n"
                     " \"pinned_extent\": null,\n \"first_ram_pin_nontrivial_pct\": null,\n"
                     " \"first_ram_runner_up\": null,\n"
                     " \"first_ram_runner_up_nontrivial_pct\": null,\n");
    }

    /* 6. cross-fixture diff, split at the pinned image's real extent */
    {
        long diff_region = 0, diff_inside = 0, diff_outside = 0, diff_words_ram = 0;
        long reported = 0;
        uint32_t k;

        fprintf(out, " \"cross_fixture_diff\": {\n");
        fprintf(out, "  \"_note\": \"region A is sized for the LARGEST overlay, so most of "
                     "the window is not this overlay; a diff over the whole window cannot "
                     "speak for 'this overlay's state'\",\n");
        fprintf(out, "  \"differing_inside_pinned_image_detail\": [");
        for (k = 0; k < (uint32_t)region_len; k++) {
            uint8_t v0 = rams[0].buf[region_off + k];
            int differs = 0, inside;
            for (i = 1; i < nrams; i++)
                if (rams[i].buf[region_off + k] != v0)
                    differs = 1;
            if (!differs)
                continue;
            diff_region++;
            inside = (pin_extent && k < (uint32_t)pin_extent);
            if (inside) diff_inside++; else diff_outside++;
            if (inside && reported < MAX_DIFF_REPORT) {
                fprintf(out, "%s{\"addr\": \"0x%08" PRIx32 "\", \"offset\": %u, "
                             "\"disc_image_byte\": %u, \"values\": [",
                        reported ? ", " : "", base_va + k, k,
                        images[pin_index].buf[k]);
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
                if (w != w0) { differs = 1; break; }
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

    /* 7. named overlay-local words supplied by the caller from a pinned artifact */
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
                      a + 4 <= base_va + (uint32_t)pin_extent);
            if (in_pin) inside++;
            fprintf(out, "%s{\"addr\": \"0x%08" PRIx32 "\", \"inside_pinned_image\": %s, "
                         "\"disc_image_u32\": ",
                    i ? ", " : "", a, in_pin ? "true" : "false");
            if (in_pin) {
                uint32_t dv;
                memcpy(&dv, images[pin_index].buf + (a - base_va), 4);
                fprintf(out, "%" PRIu32, dv);
                if (dv == 0) zero_on_disc++;
            } else {
                fprintf(out, "null");
            }
            fprintf(out, ", \"values\": [");
            for (k = 0; k < nrams; k++) {
                uint32_t v;
                memcpy(&v, rams[k].buf + off, 4);
                if (k == 0) v0 = v; else if (v != v0) varies = 1;
                fprintf(out, "%s%" PRIu32, k ? ", " : "", v);
            }
            if (varies) varying++;
            fprintf(out, "], \"varies_across_fixtures\": %s}", varies ? "true" : "false");
        }
        fprintf(out, "],\n");
        fprintf(out, " \"named_words_count\": %d,\n", nwords);
        fprintf(out, " \"named_words_inside_pinned_image\": %d,\n", inside);
        fprintf(out, " \"named_words_zero_in_disc_image\": %d,\n", zero_on_disc);
        fprintf(out, " \"named_words_varying_across_fixtures\": %d,\n", varying);
    }

    /* 8. claimed ranges: is another artifact's overlay-local claim really THIS file? */
    {
        int confirmed = 0;
        fprintf(out, " \"claimed_ranges\": [");
        for (i = 0; i < nclaims; i++) {
            uint32_t s = claims[i].start, e = claims[i].end;
            int in_pin = (pin_index >= 0 && s >= base_va &&
                          e <= base_va + (uint32_t)pin_extent);
            long len = (long)(e - s);
            long ram_equal_all = 1, differing_first = 0;
            char esc[128];

            if (s < RAM_VA || (long)(e - RAM_VA) > (long)RAM_SIZE) {
                fprintf(stderr, "claim %s outside main RAM\n", claims[i].name);
                return 2;
            }
            if (in_pin) {
                int r;
                long k;
                for (r = 0; r < nrams; r++) {
                    for (k = 0; k < len; k++) {
                        uint8_t rb = rams[r].buf[(s - RAM_VA) + (uint32_t)k];
                        uint8_t db = images[pin_index].buf[(s - base_va) + (uint32_t)k];
                        if (rb != db) {
                            ram_equal_all = 0;
                            if (r == 0) differing_first++;
                        }
                    }
                }
                if (ram_equal_all) confirmed++;
            } else {
                ram_equal_all = 0;
            }
            json_escape(claims[i].name, esc, sizeof esc);
            fprintf(out, "%s{\"name\": \"%s\", \"start\": \"0x%08" PRIx32 "\", "
                         "\"end\": \"0x%08" PRIx32 "\", \"bytes\": %ld, "
                         "\"inside_pinned_image_extent\": %s, "
                         "\"ram_equals_pinned_disc_image_in_every_fixture\": %s, "
                         "\"differing_bytes_first_fixture\": %ld}",
                    i ? ", " : "", esc, s, e, len, in_pin ? "true" : "false",
                    (in_pin && ram_equal_all) ? "true" : "false", differing_first);
        }
        fprintf(out, "],\n");
        fprintf(out, " \"claimed_ranges_count\": %d,\n", nclaims);
        fprintf(out, " \"claimed_ranges_confirmed_in_pinned_image\": %d,\n", confirmed);
    }

    fprintf(out, " \"result\": \"%s\"\n}\n",
            pins == 1 ? "STAGE_IDENTITY_PIN_UNIQUE" : "STAGE_IDENTITY_PIN_AMBIGUOUS");
    fclose(out);

    printf("%s: scanned %d images x %d rams at 0x%08" PRIx32 " -> %s\n", row_id,
           nimages, nrams, base_va,
           pins == 1 ? images[pin_index].path : "AMBIGUOUS");
    return 0;
}
