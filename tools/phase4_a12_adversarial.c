#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint8_t *p; size_t n; } Blob;
typedef struct {
    const uint8_t *c; size_t cn, pos;
    uint8_t *o; size_t on, cap;
    uint32_t state, carry;
    int error;
} Dec;

static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }
static uint32_t le32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }
static uint32_t be32(const uint8_t *p) { return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3]; }
static Blob load(const char *path) {
    FILE *f = fopen(path, "rb"); Blob b = {0}; long n;
    if (!f || fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) {
        fprintf(stderr, "open %s: %s\n", path, strerror(errno)); exit(2);
    }
    b.n = (size_t)n; b.p = malloc(b.n ? b.n : 1);
    if (!b.p || (b.n && fread(b.p, 1, b.n, f) != b.n)) exit(2);
    fclose(f); return b;
}
static uint8_t input(Dec *d) { if (d->pos >= d->cn) { d->error = 1; return 0; } return d->c[d->pos++]; }
static void output(Dec *d, uint8_t v) { if (d->on >= d->cap) { d->error = 1; return; } d->o[d->on++] = v; }
static void bit(Dec *d) {
    d->state *= 2; d->carry = (d->state >> 8) & 1; d->state &= 0xff;
    if (d->state == 0) { d->state = input(d); d->state = d->state * 2 + d->carry; d->carry = (d->state >> 8) & 1; }
}
static int depack(const uint8_t *c, size_t cn, uint8_t *out, size_t cap, size_t *got) {
    Dec d = {c, cn, 14, out, 0, cap, 0, 0, 0}; uint64_t steps = 0; uint32_t len, dist;
    d.carry = 1; d.state = input(&d); d.state = d.state * 2 + d.carry; d.state *= 2; d.carry = (d.state >> 8) & 1;
    for (;;) {
        if (++steps > 30000000 || d.error) return 0;
        d.state *= 2; d.carry = (d.state >> 8) & 1;
        if (!d.carry) {
            output(&d, input(&d)); d.state *= 2; d.carry = (d.state >> 8) & 1;
            if (!d.carry) { output(&d, input(&d)); continue; }
        }
        d.state &= 0xff;
        if (d.state == 0) {
            d.state = input(&d); d.state = d.state * 2 + d.carry; d.carry = (d.state >> 8) & 1;
            if (!d.carry) { output(&d, input(&d)); continue; }
        }
        len = 2; dist = 0; bit(&d);
        if (!d.carry) {
            bit(&d); len = len * 2 + d.carry; bit(&d);
            if (d.carry) {
                len--; bit(&d); len = len * 2 + d.carry;
                if (len == 9) {
                    len = 3; dist = 0; do { bit(&d); dist = dist * 2 + d.carry; } while (len--);
                    dist += 2; while ((int32_t)dist >= 0) { for (int q = 0; q < 4; q++) output(&d, input(&d)); dist--; }
                    continue;
                }
            }
        } else {
            bit(&d); if (d.carry) {
                len++; bit(&d); if (d.carry) {
                    len = input(&d); if (len == 0) { bit(&d); if (d.carry) continue; *got = d.on; return !d.error; }
                    len += 8;
                }
            } else goto have_distance;
        }
        bit(&d); if (!d.carry) goto have_distance;
        bit(&d); dist = dist * 2 + d.carry; bit(&d);
        if (d.carry) {
            bit(&d); dist = (dist * 2 + d.carry) | 4; bit(&d); if (!d.carry) { bit(&d); dist = dist * 2 + d.carry; }
        } else if (dist == 0) { dist++; bit(&d); dist = dist * 2 + d.carry; }
        dist = ((dist << 8) & 0xff00) | (dist >> 8);
have_distance:
        dist = input(&d) | (dist & 0xff00);
        { int64_t ref = (int64_t)d.on - (int64_t)dist - 1;
          for (uint32_t i = 0; i < len; i++) output(&d, ref + (int64_t)i < 0 ? 0 : d.o[ref + i]); }
    }
}

static int scan_dat(const char *path, unsigned totals[5]) {
    Blob b = load(path); size_t off = 4; unsigned local[5] = {0};
    if (b.n < 4) return 0;
    uint32_t groups = le32(b.p);
    for (uint32_t g = 0; g < groups; g++) {
        if (off + 4 > b.n) return 0;
        uint16_t count = le16(b.p + off); int16_t type = (int16_t)le16(b.p + off + 2); size_t stride;
        if (type < 0) stride = ((((size_t)count * 3 + 1) >> 1) << 2) + 0x10;
        else if (type == 0x3f) stride = (size_t)count * 0x10 + 4;
        else stride = (size_t)count * 0x0c + 4;
        if (stride > b.n - off) return 0;
        if (type == 0x3f) for (uint16_t i = 0; i < count; i++) {
            uint8_t kind = b.p[off + 4 + (size_t)i * 16 + 12];
            if (kind >= 0x29 && kind <= 0x2d) local[kind - 0x29]++;
        }
        off += stride;
    }
    printf("    {\"path\":\"%s\",\"tokens\":[%u,%u,%u,%u,%u],\"parsed_end\":%zu,\"size\":%zu}",
           path, local[0], local[1], local[2], local[3], local[4], off, b.n);
    for (int i = 0; i < 5; i++) totals[i] += local[i];
    free(b.p);
    return 1;
}

static int scan_raw(const char *path, unsigned color[256], unsigned def[256], unsigned *seeds, unsigned *mismatch) {
    Blob b = load(path); size_t off = 0; unsigned chunks = 0, tables = 0, local_seeds = 0, lc[256] = {0}, ld[256] = {0};
    while (off + 14 <= b.n) {
        uint32_t outn = be32(b.p + off), payload = be32(b.p + off + 4); size_t block = 14u + payload, got = 0;
        if (!outn || block > b.n - off) break;
        uint8_t *out = calloc(outn, 1);
        if (!out) exit(2);
        if (!depack(b.p + off, block, out, outn, &got) || got != outn) { free(out); free(b.p); return 0; }
        if (got >= 4 && le32(out) == 0x23 && (got - 4) % 28 == 0) {
            tables++; size_t nr = (got - 4) / 28;
            for (size_t i = 0; i < nr; i++) { const uint8_t *r = out + 4 + i * 28;
                if (r[12] == 11) { local_seeds++; lc[r[14]]++; ld[r[15]]++; color[r[14]]++; def[r[15]]++; (*seeds)++; if (r[14] != (r[15] & 0x0f)) (*mismatch)++; }
            }
        }
        free(out); off += block; chunks++;
    }
    printf("    {\"path\":\"%s\",\"chunks\":%u,\"actor_tables\":%u,\"seed_id11\":%u,\"colors\":{", path, chunks, tables, local_seeds);
    int first = 1; for (unsigned i = 0; i < 256; i++) if (lc[i]) { if (!first) putchar(','); printf("\"%u\":%u", i, lc[i]); first = 0; }
    printf("},\"defaults\":{"); first = 1; for (unsigned i = 0; i < 256; i++) if (ld[i]) { if (!first) putchar(','); printf("\"%u\":%u", i, ld[i]); first = 0; }
    printf("}}"); free(b.p); return 1;
}

static void scan_overlay(const char *path, unsigned *sb0e_total, unsigned *lbu0e_total) {
    Blob b = load(path); unsigned sb = 0, lbu = 0;
    for (size_t off = 0; off + 4 <= b.n; off += 4) {
        uint32_t w = le32(b.p + off); unsigned op = w >> 26; uint16_t imm = (uint16_t)w;
        if (op == 0x28 && imm == 0x000e) sb++;
        if (op == 0x24 && imm == 0x000e) lbu++;
    }
    printf("    {\"path\":\"%s\",\"sb_plus_0e\":%u,\"lbu_plus_0e\":%u}", path, sb, lbu);
    *sb0e_total += sb; *lbu0e_total += lbu; free(b.p);
}

int main(void) {
    glob_t g = {0}; unsigned token_total[5] = {0}, color[256] = {0}, def[256] = {0}, seeds = 0, mismatch = 0, sb = 0, lbu = 0; int first;
    puts("{\"schema\":\"abl.phase4.a12.adversarial.v1\",");
    glob("REBUILD/files/LEVEL*/LEVEL*.DAT", 0, NULL, &g); printf("  \"dat_files\":[\n"); first = 1;
    for (size_t i = 0; i < g.gl_pathc; i++) { if (!first) puts(","); if (!scan_dat(g.gl_pathv[i], token_total)) return 1; first = 0; }
    printf("\n  ],\"dat_file_count\":%zu,\"token_totals\":[%u,%u,%u,%u,%u],\n", g.gl_pathc, token_total[0], token_total[1], token_total[2], token_total[3], token_total[4]); globfree(&g);
    glob("REBUILD/files/LEVEL*/LEVEL*.RAW", 0, NULL, &g); printf("  \"raw_files\":[\n"); first = 1;
    for (size_t i = 0; i < g.gl_pathc; i++) { if (!first) puts(","); if (!scan_raw(g.gl_pathv[i], color, def, &seeds, &mismatch)) return 1; first = 0; }
    printf("\n  ],\"raw_file_count\":%zu,\"seed_total\":%u,\"seed_default_low_mismatches\":%u,\"seed_colors\":{", g.gl_pathc, seeds, mismatch); globfree(&g);
    first = 1; for (unsigned i = 0; i < 256; i++) if (color[i]) { if (!first) putchar(','); printf("\"%u\":%u", i, color[i]); first = 0; }
    printf("},\"seed_defaults\":{"); first = 1; for (unsigned i = 0; i < 256; i++) if (def[i]) { if (!first) putchar(','); printf("\"%u\":%u", i, def[i]); first = 0; }
    printf("},\n  \"overlay_files\":[\n");
    glob("REBUILD/files/LEVEL*/LEVEL*.BIN", 0, NULL, &g); first = 1;
    for (size_t i = 0; i < g.gl_pathc; i++) { if (!first) puts(","); scan_overlay(g.gl_pathv[i], &sb, &lbu); first = 0; }
    printf("\n  ],\"overlay_file_count\":%zu,\"overlay_sb_plus_0e_total\":%u,\"overlay_lbu_plus_0e_total\":%u\n}\n", g.gl_pathc, sb, lbu); globfree(&g); return 0;
}
