#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint32_t pc, word; const char *label; } Anchor;

static void fail(const char *message) {
  fprintf(stderr, "phase4_d04_static: %s\n", message);
  exit(1);
}

static uint32_t le32(const unsigned char *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t iword(unsigned op, unsigned rs, unsigned rt, int imm) {
  return (op << 26) | (rs << 21) | (rt << 16) | (uint16_t)imm;
}

static uint32_t jword(unsigned op, uint32_t address) {
  return (op << 26) | ((address >> 2) & 0x03ffffffu);
}

static uint32_t branch_target(uint32_t pc, uint32_t word) {
  return pc + 4u + (uint32_t)((int32_t)(int16_t)word * 4);
}

static unsigned char *read_all(const char *path, size_t *size_out) {
  FILE *f = fopen(path, "rb");
  if (!f || fseek(f, 0, SEEK_END) != 0) fail("cannot open input");
  long end = ftell(f);
  if (end < 0 || fseek(f, 0, SEEK_SET) != 0) fail("cannot size input");
  size_t size = (size_t)end;
  unsigned char *data = malloc(size ? size : 1);
  if (!data || fread(data, 1, size, f) != size) fail("cannot read input");
  fclose(f);
  *size_out = size;
  return data;
}

static void sha256_hex(const unsigned char *data, size_t size, char out[65]) {
  EVP_MD_CTX *ctx = EVP_MD_CTX_new();
  unsigned char digest[32];
  unsigned int n = 0;
  if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
      EVP_DigestUpdate(ctx, data, size) != 1 ||
      EVP_DigestFinal_ex(ctx, digest, &n) != 1 || n != 32) fail("SHA-256 failed");
  EVP_MD_CTX_free(ctx);
  for (size_t i = 0; i < 32; ++i) sprintf(out + i * 2, "%02x", digest[i]);
  out[64] = '\0';
}

static uint32_t word_at(const unsigned char *exe, size_t size, uint32_t pc) {
  size_t off = 0x800u + (size_t)(pc - 0x80010000u);
  if (pc < 0x80010000u || off + 4 > size) fail("PC outside executable");
  return le32(exe + off);
}

int main(int argc, char **argv) {
  const char *path = argc > 1 ? argv[1] : "SCUS_942.88";
  const char *expected_sha =
      "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20";
  size_t size = 0;
  unsigned char *exe = read_all(path, &size);
  char sha[65];
  sha256_hex(exe, size, sha);
  if (size < 0x800 || memcmp(exe, "PS-X EXE", 8) != 0 ||
      le32(exe + 0x18) != 0x80010000u || strcmp(sha, expected_sha) != 0)
    fail("pristine executable identity mismatch");

  const Anchor anchors[] = {
    {0x80047170, iword(0x24, 16, 3, 151), "equipped berry selector"},
    {0x800471a4, iword(0x09, 0, 17, 2), "red throw class"},
    {0x800471b0, iword(0x09, 0, 17, 5), "blue throw class"},
    {0x800471b8, iword(0x09, 0, 17, 8), "homing throw class"},
    {0x800471c4, iword(0x09, 0, 17, 11), "gold throw class"},
    {0x800471c8, iword(0x09, 0, 17, 45), "mega throw class"},
    {0x80058edc, iword(0x25, 18, 2, 0x5c), "load enemy flags"},
    {0x80058ee4, iword(0x0c, 2, 2, 0x40), "berry-tough mask"},
    {0x80058ee8, iword(0x04, 2, 0, 92), "ordinary actor to common damage"},
    {0x80058ef0, iword(0x21, 17, 2, 0x24), "load connecting field 24"},
    {0x80058ef8, iword(0x04, 2, 10, 5), "field24 one to reaction-only"},
    {0x80058f00, iword(0x24, 17, 2, 0x2c), "load connecting field 2c"},
    {0x80058f08, iword(0x05, 2, 10, 84), "non-one subtype to common damage"},
    {0x80059054, jword(0x02, 0x80059284), "reaction-only skips damage and death"},
    {0x8005905c, iword(0x21, 18, 2, 0x6e), "load enemy local counter"},
    {0x80059068, iword(0x0a, 2, 2, 100), "sentinel cutoff"},
    {0x80059074, iword(0x24, 17, 3, 0x2c), "load damage subtype"},
    {0x80059098, iword(0x09, 4, 2, -99), "subtype one delta"},
    {0x800590b4, iword(0x09, 4, 2, -3), "subtype 128 delta"},
    {0x800590c4, iword(0x09, 4, 2, -2), "subtype zero delta"},
    {0x800590cc, iword(0x09, 4, 2, -2), "subtype 12 delta"},
    {0x800590d4, iword(0x09, 4, 2, -4), "subtype 127 delta"},
    {0x800590e0, iword(0x09, 2, 2, -1), "default subtype delta"},
    {0x800590e4, iword(0x29, 18, 2, 0x6e), "store local counter"},
    {0x800591f0, iword(0x21, 17, 3, 0x24), "load permanence field 24"},
    {0x800591f4, iword(0x09, 0, 2, 11), "gold marker"},
    {0x80059200, iword(0x24, 17, 3, 0x27), "load secondary permanence kind"},
    {0x80059210, iword(0x0d, 23, 23, 2), "set permanent bit"},
    {0x80059218, iword(0x0d, 23, 23, 1), "set temporary bit"},
    {0x800592a8, iword(0x29, 18, 2, 0x6e), "write death marker 999"},
    {0x800592cc, iword(0x0a, 23, 2, 2), "permanent threshold"},
    {0x800592f4, iword(0x25, 3, 2, 0), "load permanent quota"},
    {0x80059300, iword(0x29, 3, 2, 0), "decrement permanent quota"},
    {0x80059358, iword(0x24, 3, 3, 0x6597), "load side-table berry column"},
    {0x80059374, iword(0x0b, 3, 2, 33), "side-table floor guard"},
    {0x80059380, iword(0x09, 3, 2, -2), "side-table decrement"}
  };
  for (size_t i = 0; i < sizeof(anchors) / sizeof(anchors[0]); ++i) {
    uint32_t got = word_at(exe, size, anchors[i].pc);
    if (got != anchors[i].word) {
      fprintf(stderr, "anchor mismatch at 0x%08x (%s): %08x != %08x\n",
              anchors[i].pc, anchors[i].label, got, anchors[i].word);
      return 1;
    }
  }
  if (branch_target(0x80058ee8, word_at(exe, size, 0x80058ee8)) != 0x8005905c ||
      branch_target(0x80058ef8, word_at(exe, size, 0x80058ef8)) != 0x80058f10 ||
      branch_target(0x80058f08, word_at(exe, size, 0x80058f08)) != 0x8005905c)
    fail("berry-tough branch target mismatch");

  printf("{\n");
  printf("  \"row\": \"D04_berry_immunity_matrix\",\n");
  printf("  \"input\": {\"exe_sha256\": \"%s\", \"anchors_checked\": %zu},\n",
         sha, sizeof(anchors) / sizeof(anchors[0]));
  printf("  \"native_throw_classes\": {\"red\":2,\"blue\":5,\"homing\":8,\"gold\":11,\"mega\":45},\n");
  printf("  \"resistance_gate\": {\"enemy_field\": \"+0x5c\", \"mask\": \"0x40\", "
         "\"ordinary_target\": \"0x8005905c\", \"tough_reaction_only_when\": "
         "[\"hit+0x24 == 1\",\"hit+0x2c == 1\"], "
         "\"reaction_only_exit\": \"0x80059284\"},\n");
  printf("  \"damage_subtype_deltas\": {\"0\":-2,\"1\":-99,\"12\":-2,\"127\":-4,\"128\":-3,\"default\":-1},\n");
  printf("  \"permanence\": {\"hit_field24_gold\":11,\"hit_field27_secondary\":6,"
         "\"permanent_bit\":2,\"temporary_bit\":1,\"quota\":\"0x800a658e\"},\n");
  printf("  \"side_table\": {\"base\":\"0x80089938\",\"shape\":\"64x5\","
         "\"selector\":\"0x800a6597\",\"decrement\":-2,\"floor_guard\":33,"
         "\"is_kill_or_immunity_oracle\":false},\n");
  printf("  \"structural_classes\": [\n");
  printf("    {\"class\":\"ordinary_damageable\",\"all_native_berries_reach_common_damage\":true,\"gold_only_native_permanent\":true},\n");
  printf("    {\"class\":\"berry_tough_0x40\",\"red_connecting_form_reaction_only\":true,\"other_native_berries_reach_common_damage\":true}\n");
  printf("  ],\n");
  printf("  \"conclusion\": \"D04 immunity is a class gate, not a five-step strength threshold; species outcome breadth depends on membership in the ordinary or bit-0x40 class\"\n");
  printf("}\n");
  free(exe);
  return 0;
}
