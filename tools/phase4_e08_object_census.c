/*
 * phase4_e08_object_census.c -- per-level object census for E08
 * (props, movers, switches, gates).
 *
 * Walks a LEVEL*.DAT exactly as the retail parser does and enumerates every
 * placement record, deriving each table's base rather than assuming LEVEL01's
 * constants:
 *
 *   top-level records  (0x8001CE8C..0x8001CF1C): count at +0, then per record
 *                      {u16 cnt, s16 typ}; size = 4+cnt*0x10 for typ 0x3f,
 *                      4+cnt*0xC for other non-negative typ, else
 *                      (((3*cnt+1)>>1)<<2)+0x10. Type 0x3F is the
 *                      contact-object/pickup family (kind byte per entry).
 *   trailing advance   (0x8001CF20..0x8001CF30): w=[s2]; s2 += (w<<7)+4.
 *   PASS 1             stride-0x14 placement table at that base; walk while
 *                      s16[rec+0xE] >= 0. Fields: s32 X,Y,Z (file scale,
 *                      world = <<5), u16 flags @+0xE (bit3 0x8 selects the
 *                      payload path, bit5 0x20 gates an extra field),
 *                      u32 payload @+0x10 (the live-proven model selector).
 *   PASS 2             stride-4 pointer array immediately after pass 1;
 *                      n = u32[p2]; entries at p2+4+4*i for i in 0..n.
 *                      This is MESH/SCALE registration, not placement.
 *   PASS 3             stride-0x14 table after pass 2, same shape as pass 1;
 *                      XYZ is a CULL ANCHOR rather than a position.
 *
 * Self-verifying: with --check the tool asserts the committed LEVEL01 anchors
 * (pass-1 base 0x1504, pass-3 base 0x3AEC, 484 pass-1 records, 484 distinct
 * pass-1 payloads) and fails loudly if the walk drifts. NOTE: the count 484 is
 * what the committed tool (tools/edit_pass1_records.py pass1_count) reports;
 * prop_decor_catalog.c's prose "500+ records" is a loose approximation.
 *
 * Build: cc -O2 -Werror -o /tmp/e08 tools/phase4_e08_object_census.c
 * Usage: /tmp/e08 <LEVEL.DAT> [--check]
 * Output: JSON on stdout.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t *d; static long dlen;

static uint32_t u32(long o) { uint32_t v; memcpy(&v, d + o, 4); return v; }
static uint16_t u16(long o) { uint16_t v; memcpy(&v, d + o, 2); return v; }
static int16_t  s16(long o) { int16_t  v; memcpy(&v, d + o, 2); return v; }
static int32_t  s32(long o) { int32_t  v; memcpy(&v, d + o, 4); return v; }
static int ok(long o, long n) { return o >= 0 && o + n <= dlen; }

#define MAXPAY 4096
static uint32_t pay[MAXPAY]; static int npay;
static int add_payload(uint32_t p)
{
    for (int i = 0; i < npay; i++) if (pay[i] == p) return 0;
    if (npay < MAXPAY) pay[npay++] = p;
    return 1;
}

static long record_size(long off)
{
    uint16_t cnt = u16(off);
    int16_t typ = s16(off + 2);
    if (typ >= 0) return (typ == 0x3f) ? (4 + (long)cnt * 0x10) : (4 + (long)cnt * 0xC);
    return ((((long)3 * cnt + 1) >> 1) << 2) + 0x10;
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s LEVEL.DAT [--check]\n", argv[0]); return 2; }
    int check = (argc > 2 && !strcmp(argv[2], "--check"));
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END); dlen = ftell(f); fseek(f, 0, SEEK_SET);
    d = malloc(dlen);
    if (!d || fread(d, 1, dlen, f) != (size_t)dlen) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);

    /* ---- top-level records, incl. the type-0x3F contact-object family ---- */
    uint32_t nrec = u32(0);
    long s2 = 4;
    long t3f_entries = 0, t3f_tables = 0, other_tables = 0, neg_tables = 0;
    long kind_hist[256]; memset(kind_hist, 0, sizeof kind_hist);
    if (nrec > 4096) { printf("{\"ok\":false,\"why\":\"record count %u\"}\n", nrec); return 1; }
    for (uint32_t i = 0; i < nrec; i++) {
        if (!ok(s2, 4)) { printf("{\"ok\":false,\"why\":\"record walk OOB\"}\n"); return 1; }
        uint16_t cnt = u16(s2); int16_t typ = s16(s2 + 2);
        if (typ == 0x3f) {
            t3f_tables++;
            for (uint16_t k = 0; k < cnt; k++) {
                long e = s2 + 4 + (long)k * 0x10;
                if (!ok(e, 0x10)) break;
                kind_hist[d[e + 0x0C] & 0xFF]++;  /* kind byte @ entry+0x0C
                                                  * (tools/catalog_type3f.py); XYZ are
                                                  * s32 @ +0/4/8, world = <<5 */
                t3f_entries++;
            }
        } else if (typ >= 0) other_tables++;
        else neg_tables++;
        s2 += record_size(s2);
    }
    if (!ok(s2, 4)) { printf("{\"ok\":false,\"why\":\"trailing advance OOB\"}\n"); return 1; }
    uint32_t w = u32(s2);
    s2 += ((long)w << 7) + 4;
    long pass1_base = s2;

    /* ---- PASS 1 ---- */
    long p1 = 0, p1_bit3 = 0, p1_bit5 = 0, p1_nullpay = 0;
    long rec = pass1_base;
    while (ok(rec + 0xE, 2) && s16(rec + 0xE) >= 0) {
        uint16_t fl = u16(rec + 0xE);
        if (fl & 0x8)  p1_bit3++;
        if (fl & 0x20) p1_bit5++;
        uint32_t pp = ok(rec + 0x10, 4) ? u32(rec + 0x10) : 0;
        if (!pp) p1_nullpay++; else add_payload(pp);
        p1++; rec += 0x14;
        if (p1 > 20000) break;
    }
    int p1_distinct = npay;
    long p2_base = rec + 0x14;      /* terminator record consumed */

    /* ---- PASS 2 (pointer array; registration, not placement) ---- */
    /* n is SIGNED: LEVEL01 stores 0xFFFFFFFF (-1) here, i.e. an EMPTY pass-2
     * whose end sentinel IS this word, so pass 3 begins at p2_base+4. Reading
     * it unsigned makes the whole tail unparseable. */
    long p2n = ok(p2_base, 4) ? (long)s32(p2_base) : -2;
    long p2_nonnull = 0, p3_base = -1;
    if (p2n >= -1 && p2n < 20000) {
        for (long i = 0; i <= p2n; i++) {
            long a = p2_base + 4 + 4 * i;
            if (!ok(a, 4)) break;
            if (u32(a) != 0) p2_nonnull++;
        }
        p3_base = p2_base + 4 + 4 * (p2n + 1);
    }

    /* ---- PASS 3 (cull anchors) ---- */
    long p3 = 0, p3_bit3 = 0;
    npay = 0;
    if (p3_base > 0) {
        rec = p3_base;
        while (ok(rec + 0xE, 2) && s16(rec + 0xE) >= 0) {
            uint16_t fl = u16(rec + 0xE);
            if (fl & 0x8) p3_bit3++;
            uint32_t pp = ok(rec + 0x10, 4) ? u32(rec + 0x10) : 0;
            if (pp) add_payload(pp);
            p3++; rec += 0x14;
            if (p3 > 20000) break;
        }
    }
    int p3_distinct = npay;

    if (check) {
        int bad = 0;
        if (pass1_base != 0x1504) { fprintf(stderr, "CHECK pass1_base %#lx != 0x1504\n", pass1_base); bad = 1; }
        if (p3_base != 0x3AEC)    { fprintf(stderr, "CHECK pass3_base %#lx != 0x3AEC\n", p3_base); bad = 1; }
        if (p1 != 484)            { fprintf(stderr, "CHECK pass1 count %ld != 484\n", p1); bad = 1; }
        if (p1_distinct != 484)   { fprintf(stderr, "CHECK distinct payloads %d != 484\n", p1_distinct); bad = 1; }
        if (bad) return 1;
        fprintf(stderr, "LEVEL01 anchors OK\n");
    }

    printf("{\n \"file\": \"%s\",\n \"size\": %ld,\n \"top_level_records\": %u,\n"
           " \"type3f_tables\": %ld,\n \"type3f_entries\": %ld,\n"
           " \"other_tables\": %ld,\n \"terrain_tables\": %ld,\n"
           " \"pass1_base\": \"0x%lx\",\n \"pass1_records\": %ld,\n"
           " \"pass1_distinct_payloads\": %d,\n \"pass1_flag_bit3\": %ld,\n"
           " \"pass1_flag_bit5\": %ld,\n \"pass1_null_payload\": %ld,\n"
           " \"pass2_base\": \"0x%lx\",\n \"pass2_entries\": %ld,\n \"pass2_nonnull\": %ld,\n"
           " \"pass3_base\": \"0x%lx\",\n \"pass3_records\": %ld,\n"
           " \"pass3_distinct_payloads\": %d,\n \"pass3_flag_bit3\": %ld,\n"
           " \"type3f_kind_histogram\": {",
           argv[1], dlen, nrec, t3f_tables, t3f_entries, other_tables, neg_tables,
           pass1_base, p1, p1_distinct, p1_bit3, p1_bit5, p1_nullpay,
           p2_base, p2n < 0 ? -1 : p2n + 1, p2_nonnull,
           p3_base, p3, p3_distinct, p3_bit3);
    int first = 1;
    for (int k = 0; k < 256; k++)
        if (kind_hist[k]) { printf("%s\"0x%02x\": %ld", first ? "" : ", ", k, kind_hist[k]); first = 0; }
    printf("}\n}\n");
    return 0;
}
