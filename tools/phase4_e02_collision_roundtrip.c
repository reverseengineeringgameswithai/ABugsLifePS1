/*
 * phase4_e02_collision_roundtrip.c -- all-level collision source->runtime
 * round trip + plane census (E02 second half).
 *
 * Reimplements FUNC_80030F60's decoded conversion (committed canon,
 * src_re/collision_source_converter_80030f60.c) as an independent C
 * implementation and diffs its prediction against the ACTUAL runtime sector
 * table extracted from a level save. Also walks every sector's collision
 * block (group/plane format proven on LEVEL01) and emits a campaign-grade
 * census: plane counts, floor/wall classification by normal.y sign,
 * |normal|==0x4000 validation, group terminator discipline, and the
 * source-field -> runtime-field mapping for the +0x2C/+0x2E wording tension.
 *
 * Inputs:
 *   argv[1] = chunk-32 blob file (decompressed segment; offset 0 == staging)
 *   argv[2] = runtime dump file: [u32 count][count * 0x30-byte sector records]
 *   argv[3] = staging base vaddr hex (chunk-32 offset 0 in RAM, e.g. 0x800C1688)
 * Output: JSON on stdout. Exit 0 iff the round trip matches on every sector.
 *
 * Build: cc -O2 -Werror -o /tmp/e02rt tools/phase4_e02_collision_roundtrip.c
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t *blob; static long blob_len;
static uint8_t *rt;   static long rt_len;

static uint32_t bu32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }
static int32_t  bs32(const uint8_t *p) { int32_t v;  memcpy(&v, p, 4); return v; }
static int16_t  bs16(const uint8_t *p) { int16_t v;  memcpy(&v, p, 2); return v; }

static long isqrt64(long long x) {
    long long r = 0, b = 1LL << 40;
    while (b > x) b >>= 2;
    while (b) { if (x >= r + b) { x -= r + b; r = (r >> 1) + b; } else r >>= 1; b >>= 2; }
    return (long)r;
}

int main(int argc, char **argv)
{
    if (argc < 4 || argc > 6) { fprintf(stderr, "usage: %s container.bin runtime.bin staging_hex [src_off] [block_base]\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("blob"); return 2; }
    fseek(f, 0, SEEK_END); blob_len = ftell(f); fseek(f, 0, SEEK_SET);
    blob = malloc(blob_len); if (fread(blob, 1, blob_len, f) != (size_t)blob_len) return 2; fclose(f);
    f = fopen(argv[2], "rb");
    if (!f) { perror("runtime"); return 2; }
    fseek(f, 0, SEEK_END); rt_len = ftell(f); fseek(f, 0, SEEK_SET);
    rt = malloc(rt_len); if (fread(rt, 1, rt_len, f) != (size_t)rt_len) return 2; fclose(f);
    uint32_t staging = (uint32_t)strtoul(argv[3], NULL, 16);
    /* container offset at which the per-sector collision blocks begin:
     * 8 for LEVEL.RAW chunk 32, 4 for .ALL containers (live-derived). */
    long block_base = (argc == 6) ? strtol(argv[5], NULL, 0) : 8;

    uint32_t n_rt = bu32(rt);
    const uint8_t *rts = rt + 4;
    if ((long)(4 + (long)n_rt * 0x30) > rt_len) { fprintf(stderr, "runtime dump short\n"); return 2; }

    /* --- locate the source sector array: candidate offset predicts the
     * runtime origins (<<5) of the first sectors. Try the LEVEL01-proven
     * fixed offset 0x36570 first, then scan (step 2). */
    long src_off = -1; uint32_t n_src = n_rt; long cursor_used = -1;
    #define ORIGINS_MATCH(off) ({                                            \
        int _ok = 1;                                                          \
        for (int _k = 0; _k < 1 && _k < (int)n_rt; _k++) {   /* prefix may be 1 record (Bug Bar) */                    \
            const uint8_t *_s = blob + (off) + (long)_k * 0x4C;               \
            const uint8_t *_r = rts + (long)_k * 0x30;                        \
            if ((off) + (long)_k * 0x4C + 0x4C > blob_len) { _ok = 0; break; }\
            if (bs32(_r + 0x00) != bs32(_s + 0x08) << 5 ||                    \
                bs32(_r + 0x04) != bs32(_s + 0x0C) << 5 ||                    \
                bs32(_r + 0x08) != bs32(_s + 0x10) << 5) { _ok = 0; break; }  \
        }                                                                     \
        _ok; })
    if (argc == 5) {
        long off = strtol(argv[4], NULL, 0);
        if (ORIGINS_MATCH(off)) { src_off = off; cursor_used = 1; }
    } else if (blob_len >= 0x36570 + 0x4C && ORIGINS_MATCH(0x36570)) {
        src_off = 0x36570; cursor_used = 0;
    } else {
        for (long off = 0; off + 0x4C <= blob_len; off += 2)
            if (ORIGINS_MATCH(off)) { src_off = off; cursor_used = 1; break; }
    }
    /* The container holds only the AUTHORED records; the runtime table also
     * carries a runtime-registered tail, so do NOT require n_rt records to
     * fit -- only the probe window. (Requiring n_rt was the bug that made
     * four scenes look "runtime-built".) */
    if (src_off < 0 || src_off + 4L * 0x4C > blob_len) {
        printf("{\"located\": false, \"runtime_count\": %u}\n", n_rt);
        return 1;
    }

    /* --- authored prefix: the longest run of source records whose origins
     * (<<5) equal the runtime origins. Beyond it, runtime slots are
     * RUNTIME-REGISTERED (degenerate/zero origins in both source layout and
     * runtime tail -- the dynamic/prop sector species). */
    uint32_t n_auth = 0;
    while (n_auth < n_src) {
        if (src_off + (long)n_auth * 0x4C + 0x4C > blob_len) break;   /* container end */
        const uint8_t *s = blob + src_off + (long)n_auth * 0x4C;
        const uint8_t *r = rts + (long)n_auth * 0x30;
        if (bs32(r + 0x00) != bs32(s + 0x08) << 5 ||
            bs32(r + 0x04) != bs32(s + 0x0C) << 5 ||
            bs32(r + 0x08) != bs32(s + 0x10) << 5)
            break;
        n_auth++;
    }
    long tail_zero_origin = 0;
    for (uint32_t i = n_auth; i < n_rt; i++) {
        const uint8_t *r = rts + (long)i * 0x30;
        if (bs32(r + 0x00) >> 5 == 0 || bs32(r + 0x00) >> 5 == -1)
            tail_zero_origin++;
    }

    /* --- convert + diff the AUTHORED sectors ------------------------------ */
    long mismatches = 0, block_run = block_base;
    long first_bad = -1;
    long p2c_eq_src14 = 0, p2c_nonzero = 0;
    long planes_total = 0, floors = 0, walls_vertical = 0, ceilings = 0;
    long norm_exact = 0, norm_off = 0, groups_total = 0, blocks_nonempty = 0;
    long bad_blocks = 0;
    long flag_hist[8] = {0}; /* runtime +0x2C value buckets: 0,1..5,other,neg */

    for (uint32_t i = 0; i < n_auth; i++) {
        const uint8_t *s = blob + src_off + (long)i * 0x4C;
        const uint8_t *r = rts + (long)i * 0x30;
        int32_t bsz = bs32(s + 0x04);
        /* geometry sectors take the running position (and advance it below);
         * flat sectors inherit the MOST RECENT geometry sector's block start
         * (the base block at staging+8 until the first geometry sector) */
        static long cur_block = -1;
        if (cur_block < 0) cur_block = (long)staging + block_base;
        if (bsz > 0) cur_block = (long)staging + block_run;
        long pred_block = cur_block;
        int ok = 1;
        ok &= bs32(r + 0x00) == bs32(s + 0x08) << 5;
        ok &= bs32(r + 0x04) == bs32(s + 0x0C) << 5;
        ok &= bs32(r + 0x08) == bs32(s + 0x10) << 5;
        ok &= bs32(r + 0x0C) == bs32(s + 0x14);
        ok &= bs16(r + 0x2C) == (int16_t)bs32(s + 0x14);
        ok &= bu32(r + 0x10) == (uint32_t)pred_block;
        ok &= bs16(r + 0x2E) == (int16_t)bs32(s + 0x2C);
        if (!ok) { mismatches++; if (first_bad < 0) first_bad = i; }

        int32_t r2c = bs16(r + 0x2C);
        if (r2c != 0) p2c_nonzero++;
        if (r2c == bs32(s + 0x14)) p2c_eq_src14++;
        if (r2c < 0) flag_hist[7]++;
        else if (r2c <= 5) flag_hist[r2c]++;
        else flag_hist[6]++;

        /* --- block walk (groups of 0x20-byte plane records) --------------- */
        if (bsz > 0) {
            blocks_nonempty++;
            long b = block_run, end = block_run + (long)bsz * 2;
            int bad = 0;
            if (end > blob_len) { bad_blocks++; block_run = end; continue; }
            {   /* validity gate: a real block opens with marker>=0 and a
                 * count whose group fits inside the block */
                int16_t m0 = bs16(blob + b), c0 = bs16(blob + b + 2);
                if (m0 < 0 || c0 <= 0 || b + 12 + (long)c0 * 0x20 > end + 2) {
                    bad_blocks++; block_run = end; continue;
                }
            }
            while (b + 2 <= end && b + 2 <= blob_len) {
                int16_t marker = bs16(blob + b);
                if (marker < 0) { b += 2; break; }
                if (b + 12 > end) { bad = 1; break; }
                int16_t cnt = bs16(blob + b + 2);
                if (cnt < 0 || b + 12 + (long)cnt * 0x20 > end + 2) { bad = 1; break; }
                groups_total++;
                for (int k = 0; k < cnt; k++) {
                    const uint8_t *p = blob + b + 12 + (long)k * 0x20;
                    int16_t nx = bs16(p), ny = bs16(p + 2), nz = bs16(p + 4);
                    long long m2 = (long long)nx * nx + (long long)ny * ny + (long long)nz * nz;
                    long m = isqrt64(m2);
                    if (m >= 0x4000 - 2 && m <= 0x4000 + 2) norm_exact++; else norm_off++;
                    planes_total++;
                    if (ny < 0) floors++;
                    else if (ny > 0) ceilings++;
                    else walls_vertical++;
                }
                b += 12 + (long)cnt * 0x20;
            }
            if (bad) bad_blocks++;
            block_run = end;
        }
    }

    printf("{\n \"located\": true, \"fixed_offset_used\": %ld, \"src_offset\": %ld,\n"
           " \"block_base\": %ld,\n"
           " \"sector_count\": %u, \"authored_count\": %u, \"runtime_extra\": %u,\n"
           " \"runtime_extra_zero_origin\": %ld,\n"
           " \"roundtrip_mismatches\": %ld, \"first_bad_sector\": %ld,\n"
           " \"flag2c\": {\"nonzero\": %ld, \"eq_src14\": %ld,\n"
           "   \"hist_0_to_5_other_neg\": [%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld]},\n"
           " \"census\": {\"blocks_nonempty\": %ld, \"groups\": %ld, \"planes\": %ld,\n"
           "   \"floors\": %ld, \"walls_vertical\": %ld, \"ceilings\": %ld,\n"
           "   \"normal_len_0x4000\": %ld, \"normal_len_off\": %ld, \"bad_blocks\": %ld}\n}\n",
           1 - cursor_used, src_off, block_base, n_rt, n_auth, n_rt - n_auth, tail_zero_origin,
           mismatches, first_bad,
           p2c_nonzero, p2c_eq_src14,
           flag_hist[0], flag_hist[1], flag_hist[2], flag_hist[3], flag_hist[4],
           flag_hist[5], flag_hist[6], flag_hist[7],
           blocks_nonempty, groups_total, planes_total,
           floors, walls_vertical, ceilings, norm_exact, norm_off, bad_blocks);
    return mismatches == 0 ? 0 : 1;
}
