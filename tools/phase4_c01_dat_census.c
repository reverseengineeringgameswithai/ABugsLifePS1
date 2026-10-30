#define _XOPEN_SOURCE 700
#include <errno.h>
#include <ftw.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static unsigned files_seen, tables_seen, total_entries, total_grain, total_live_grain;

static uint16_t le16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static int32_t le32s(const uint8_t *p) {
    uint32_t v = (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
                 ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
    return (int32_t)v;
}

static int known_kind(uint8_t kind) {
    return (kind >= 0x10 && kind <= 0x14) ||
           (kind >= 0x20 && kind <= 0x24) ||
           (kind >= 0x29 && kind <= 0x31);
}

static int valid_table(const uint8_t *file, size_t size, size_t header_off,
                       uint16_t *count_out, unsigned *grain_out, unsigned *live_out) {
    if (header_off + 8 > size || le16(file + header_off + 2) != 0x3f) return 0;
    uint16_t count = le16(file + header_off);
    if (count == 0 || count > 4096 || header_off + 4u + (size_t)count * 16u > size) return 0;
    unsigned grain = 0, live = 0;
    const uint8_t *entries = file + header_off + 4;
    for (unsigned i = 0; i < count; ++i) {
        const uint8_t *e = entries + i * 16u;
        int32_t x = le32s(e), y = le32s(e + 4), z = le32s(e + 8);
        if (!known_kind(e[12]) || e[13] > 1 ||
            x < -10000000 || x > 10000000 ||
            y < -10000000 || y > 10000000 ||
            z < -10000000 || z > 10000000) return 0;
        if (e[12] == 0x14) { ++grain; if (e[13] == 1) ++live; }
    }
    *count_out = count;
    *grain_out = grain;
    *live_out = live;
    return 1;
}

static int digest_file(FILE *fp, char out[65]) {
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    unsigned char buf[65536], digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    size_t n;
    if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1) return -1;
    rewind(fp);
    while ((n = fread(buf, 1, sizeof(buf), fp)) != 0)
        if (EVP_DigestUpdate(ctx, buf, n) != 1) return -1;
    if (ferror(fp) || EVP_DigestFinal_ex(ctx, digest, &digest_len) != 1) return -1;
    EVP_MD_CTX_free(ctx);
    for (unsigned i = 0; i < digest_len; ++i) sprintf(out + i * 2, "%02x", digest[i]);
    out[digest_len * 2] = '\0';
    return 0;
}

static int visit(const char *path, const struct stat *st, int type, struct FTW *ftw) {
    (void)ftw;
    if (type != FTW_F || strcmp(strrchr(path, '/') ? strrchr(path, '/') + 1 : path, "LEVEL.DAT") != 0)
        return 0;
    ++files_seen;
    FILE *fp = fopen(path, "rb");
    if (!fp) { fprintf(stderr, "%s: %s\n", path, strerror(errno)); return 1; }
    if (st->st_size < 8) { fprintf(stderr, "%s: too short\n", path); fclose(fp); return 1; }
    uint8_t *file = malloc((size_t)st->st_size);
    if (!file || fread(file, 1, (size_t)st->st_size, fp) != (size_t)st->st_size) {
        free(file); fclose(fp); return 1;
    }
    size_t table_off = 0;
    uint16_t count = 0;
    unsigned grain = 0, live = 0;
    int found = 0;
    for (size_t off = 0; off + 8 <= (size_t)st->st_size; off += 2) {
        uint16_t candidate_count;
        unsigned candidate_grain, candidate_live;
        if (!valid_table(file, (size_t)st->st_size, off, &candidate_count,
                         &candidate_grain, &candidate_live)) continue;
        if (found) {
            fprintf(stderr, "%s: multiple structurally valid type3f tables\n", path);
            free(file); fclose(fp); return 1;
        }
        found = 1;
        table_off = off;
        count = candidate_count;
        grain = candidate_grain;
        live = candidate_live;
    }
    char sha[65];
    if (digest_file(fp, sha) != 0) { fprintf(stderr, "%s: sha256 failed\n", path); free(file); fclose(fp); return 1; }
    if (found) {
        printf("%s type3f_offset=0x%zx entries=%u grain=%u source_status1=%u source_status_not1=%u sha256=%s\n",
               path, table_off, count, grain, live, grain - live, sha);
        ++tables_seen;
        total_entries += count;
        total_grain += grain;
        total_live_grain += live;
    } else {
        printf("%s type3f=absent grain=0 sha256=%s\n", path, sha);
    }
    free(file);
    fclose(fp);
    return 0;
}

int main(int argc, char **argv) {
    const char *root = argc > 1 ? argv[1] : "REBUILD/files";
    if (nftw(root, visit, 16, FTW_PHYS) != 0) return 1;
    printf("TOTAL level_dat_files=%u valid_type3f_tables=%u entries=%u grain=%u source_status1=%u source_status_not1=%u\n",
           files_seen, tables_seen, total_entries, total_grain, total_live_grain,
           total_grain - total_live_grain);
    return files_seen == 0;
}
