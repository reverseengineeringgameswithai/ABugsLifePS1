#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/evp.h>

typedef struct Bits {
  const uint8_t *p;
  const uint8_t *end;
  uint32_t state;
  unsigned carry;
  int error;
} Bits;

static uint32_t be32(const uint8_t *p) {
  return (uint32_t)p[3] | (uint32_t)p[2] << 8 |
         (uint32_t)p[1] << 16 | (uint32_t)p[0] << 24;
}

static uint32_t le32(const uint8_t *p) {
  return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
         (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static unsigned dp_bit(Bits *b) {
  b->state <<= 1;
  b->carry = (b->state >> 8) & 1u;
  b->state &= 0xffu;
  if (b->state == 0) {
    if (b->p == b->end) { b->error = 1; return 0; }
    b->state = (uint32_t)(*b->p++) * 2u + b->carry;
    b->carry = (b->state >> 8) & 1u;
  }
  return b->carry;
}

static int copy_byte(uint8_t **out, uint8_t *out_base, uint8_t *out_end,
                     const uint8_t **src, const uint8_t *src_end) {
  (void)out_base;
  if (*out == out_end || *src == src_end) return 0;
  *(*out)++ = *(*src)++;
  return 1;
}

static int depack(const uint8_t *block, size_t block_size,
                  uint8_t *out_base, size_t out_size) {
  const uint8_t *src;
  const uint8_t *src_end;
  uint8_t *out = out_base;
  uint8_t *out_end = out_base + out_size;
  Bits b;
  uint32_t length, offset;

  if (block_size < 15) return 0;
  src = block + 14;
  src_end = block + block_size;
  b.p = src + 1;
  b.end = src_end;
  b.state = (uint32_t)src[0] * 4u + 2u;
  b.carry = (b.state >> 8) & 1u;
  b.error = 0;

  for (;;) {
main_decode:
    b.state <<= 1;
    b.carry = (b.state >> 8) & 1u;
    if (!b.carry) {
      if (!copy_byte(&out, out_base, out_end, &b.p, b.end)) return 0;
      b.state <<= 1;
      b.carry = (b.state >> 8) & 1u;
      if (!b.carry) {
        if (!copy_byte(&out, out_base, out_end, &b.p, b.end)) return 0;
        goto main_decode;
      }
    }
    b.state &= 0xffu;
    if (b.state == 0) {
      if (b.p == b.end) return 0;
      b.state = (uint32_t)(*b.p++) * 2u + b.carry;
      b.carry = (b.state >> 8) & 1u;
      if (!b.carry) {
        if (!copy_byte(&out, out_base, out_end, &b.p, b.end)) return 0;
        goto main_decode;
      }
    }
    length = 2;
    offset = 0;
    if (!dp_bit(&b)) {
      length = length * 2u + dp_bit(&b);
      if (dp_bit(&b)) {
        length--;
        length = length * 2u + dp_bit(&b);
        if (length == 9) {
          unsigned words = 0;
          for (unsigned i = 0; i < 4; i++) words = words * 2u + dp_bit(&b);
          words += 2;
          for (unsigned i = 0; i <= words; i++) {
            for (unsigned j = 0; j < 4; j++) {
              if (!copy_byte(&out, out_base, out_end, &b.p, b.end)) return 0;
            }
          }
          continue;
        }
      }
    } else {
      if (!dp_bit(&b)) goto have_offset;
      length++;
      if (!dp_bit(&b)) goto decode_offset;
      if (b.p == b.end) return 0;
      length = *b.p++;
      if (length == 0) {
        length += 8;
        if (dp_bit(&b)) goto main_decode;
        return out == out_end && !b.error;
      }
      length += 8;
    }

decode_offset:
    if (!dp_bit(&b)) goto have_offset;
    offset = offset * 2u + dp_bit(&b);
    if (dp_bit(&b)) {
      offset = offset * 2u + dp_bit(&b);
      offset |= 4u;
      if (!dp_bit(&b)) offset = offset * 2u + dp_bit(&b);
    } else if (offset == 0) {
      offset = 1;
      offset = offset * 2u + dp_bit(&b);
    }
    offset = ((offset << 8) & 0xff00u) | (offset >> 8);

have_offset:
    if (b.p == b.end) return 0;
    offset = (offset & 0xff00u) | *b.p++;
    int64_t ref = (int64_t)(out - out_base) - (int64_t)offset - 1;
    for (uint32_t i = 0; i < length; i++, ref++) {
      if (out == out_end) return 0;
      *out++ = ref < 0 ? 0 : out_base[ref];
    }
    if (b.error) return 0;
  }
}

static uint8_t *read_file(const char *path, size_t *size) {
  FILE *f = fopen(path, "rb");
  uint8_t *data;
  long n;
  if (!f || fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 ||
      fseek(f, 0, SEEK_SET)) return NULL;
  data = malloc((size_t)n);
  if (!data || fread(data, 1, (size_t)n, f) != (size_t)n) {
    free(data); fclose(f); return NULL;
  }
  fclose(f); *size = (size_t)n; return data;
}

static void sha256_hex(const uint8_t *data, size_t size, char out[65]) {
  uint8_t digest[EVP_MAX_MD_SIZE];
  unsigned digest_size = 0;
  EVP_MD_CTX *ctx = EVP_MD_CTX_new();
  if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
      EVP_DigestUpdate(ctx, data, size) != 1 ||
      EVP_DigestFinal_ex(ctx, digest, &digest_size) != 1 || digest_size != 32) {
    fprintf(stderr, "SHA-256 failed\n"); exit(1);
  }
  EVP_MD_CTX_free(ctx);
  for (unsigned i = 0; i < digest_size; i++) sprintf(out + i * 2u, "%02x", digest[i]);
  out[64] = '\0';
}

static int scan_raw(const char *path, int comma, unsigned *match_out) {
  size_t size, off = 0;
  uint8_t *file = read_file(path, &size);
  unsigned chunk = 0, actor_tables = 0, matches = 0;
  char sha256[65];
  if (!file) { fprintf(stderr, "%s: %s\n", path, strerror(errno)); return 0; }
  sha256_hex(file, size, sha256);
  if (comma) puts(",");
  printf("    {\"path\":\"%s\",\"size\":%zu,\"sha256\":\"%s\",\"actor_table\":",
         path, size, sha256);
  while (off + 14 <= size) {
    uint32_t out_size = be32(file + off);
    uint32_t payload = be32(file + off + 4);
    size_t block_size = (size_t)payload + 14u;
    uint8_t *out;
    if (block_size > size - off || out_size == 0) break;
    out = calloc(out_size, 1);
    if (!out || !depack(file + off, block_size, out, out_size)) {
      fprintf(stderr, "%s chunk %u: depack failed (%u/%u)\n",
              path, chunk, out_size, payload);
      free(out); free(file); return 0;
    }
    if (out_size == 4u + 64u * 0x1cu && le32(out) == 0x23u) {
      uint32_t header_word = le32(out);
      uint32_t count = 64;
      if (actor_tables++) { fprintf(stderr, "%s: duplicate actor table\n", path); return 0; }
        printf("{\"chunk\":%u,\"header_word\":\"0x%08" PRIX32
               "\",\"record_count\":%u,\"harvester_records\":[",
               chunk, header_word, count);
        unsigned table_matches = 0;
        for (uint32_t i = 0; i < count; i++) {
          const uint8_t *r = out + 4u + i * 0x1cu;
          if (le32(r + 12) == 0x00002223u) {
            if (table_matches++) putchar(',');
            printf("{\"record\":%u,\"x\":%" PRId32 ",\"y\":%" PRId32
                   ",\"z\":%" PRId32 ",\"params\":[\"0x%08" PRIX32
                   "\",\"0x%08" PRIX32 "\",\"0x%08" PRIX32 "\"]}",
                   i, (int32_t)le32(r), (int32_t)le32(r+4),
                   (int32_t)le32(r+8), le32(r+16), le32(r+20), le32(r+24));
            matches++;
          }
        }
        printf("]}");
    }
    free(out); off += block_size; chunk++;
  }
  if (!actor_tables) printf("null");
  printf(",\"chunks\":%u,\"harvester_matches\":%u}", chunk, matches);
  *match_out = matches;
  free(file); return 1;
}

int main(int argc, char **argv) {
  int emitted = 0;
  unsigned total_matches = 0, matching_files = 0;
  if (argc < 2) return 2;
  puts("{\"schema\":\"phase4-c13-raw-applicability-v1\",\"target_type_word\":\"0x00002223\",\"files\":[");
  for (int i = 1; i < argc; i++) {
    unsigned matches = 0;
    if (!scan_raw(argv[i], emitted, &matches)) return 1;
    total_matches += matches;
    matching_files += matches != 0;
    emitted = 1;
  }
  printf("\n],\"files_scanned\":%d,\"matching_files\":%u,\"total_harvester_records\":%u}\n",
         argc - 1, matching_files, total_matches);
  return 0;
}
