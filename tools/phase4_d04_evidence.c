#include <openssl/evp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  const char *path;
  const char *sha;
  const char *need1;
  const char *need2;
  unsigned char *data;
  size_t size;
} Evidence;

static void fail(const char *message, const char *path) {
  fprintf(stderr, "phase4_d04_evidence: %s: %s\n", message, path);
  exit(1);
}

static unsigned char *read_all(const char *path, size_t *size_out) {
  FILE *f = fopen(path, "rb");
  if (!f || fseek(f, 0, SEEK_END) != 0) fail("cannot open", path);
  long end = ftell(f);
  if (end < 0 || fseek(f, 0, SEEK_SET) != 0) fail("cannot size", path);
  size_t size = (size_t)end;
  unsigned char *data = malloc(size + 1);
  if (!data || fread(data, 1, size, f) != size) fail("cannot read", path);
  fclose(f);
  data[size] = '\0';
  *size_out = size;
  return data;
}

static void sha256_hex(const unsigned char *data, size_t size, char out[65]) {
  EVP_MD_CTX *ctx = EVP_MD_CTX_new();
  unsigned char digest[32];
  unsigned int n = 0;
  if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
      EVP_DigestUpdate(ctx, data, size) != 1 ||
      EVP_DigestFinal_ex(ctx, digest, &n) != 1 || n != 32) exit(2);
  EVP_MD_CTX_free(ctx);
  for (size_t i = 0; i < 32; ++i) sprintf(out + i * 2, "%02x", digest[i]);
  out[64] = '\0';
}

int main(void) {
  Evidence evidence[] = {
    {"analysis/phase4_d12_worm_id40.json",
     "be8a60aafd07bc0b2543c772344dab1b07c5c02a43b0aafa5e54fa2a20abbedd",
     "blue/homing -2, gold -4, mega -3", "gates ONLY the red class", NULL, 0},
    {"analysis/phase4_d13_shell_bug_armor.json",
     "51ad51bb93c9843e88511fd52fc846e58dd4191e1a0734842db203333c81ce3c",
     "red (equip 0, class 2)", "every other native throw class", NULL, 0},
    {"analysis/phase4_d07_mosquitoes.json",
     "796b044b37d26d02b088f34866d16de81755c7aeb6605cc4ceac57a6736df612",
     "berry contact damages the mosquito", "collision/damage handler", NULL, 0},
    {"analysis/phase4_d09_redbug_identity.json",
     "1a45d3bf839f17fdf4b371571669fbdb6575540f2d1a393e45d56155b49cef4b",
     "blue/super berry", "Damage was -2 HP per hit", NULL, 0},
    {"src_re/enemy_death_permanence.c",
     "602f659817da81afbf028c6c9bf4d772b2e0b40f6ba27791474b8099791b6b7f",
     "Gold 3/3 permanent", "Cross-checked on spider + mosquito", NULL, 0}
  };
  for (size_t i = 0; i < sizeof(evidence) / sizeof(evidence[0]); ++i) {
    char sha[65];
    evidence[i].data = read_all(evidence[i].path, &evidence[i].size);
    sha256_hex(evidence[i].data, evidence[i].size, sha);
    if (strcmp(sha, evidence[i].sha) != 0) fail("hash mismatch", evidence[i].path);
    if (!strstr((char *)evidence[i].data, evidence[i].need1) ||
        !strstr((char *)evidence[i].data, evidence[i].need2))
      fail("semantic anchor missing", evidence[i].path);
  }

  printf("{\n");
  printf("  \"row\": \"D04_berry_immunity_matrix\",\n");
  printf("  \"validated_inputs\": %zu,\n", sizeof(evidence) / sizeof(evidence[0]));
  printf("  \"runtime_coverage\": {\n");
  printf("    \"berry_tough\": {\"shell_bug\":\"five_of_five\","
         "\"worm_id40\":\"five_of_five\",\"wall_worm\":\"four_clean_plus_red_connectivity_caveat\"},\n");
  printf("    \"ordinary\": {\"spider\":\"red_counter_plus_gold_vs_nongold_campaign\","
         "\"mosquito\":\"berry_damage_plus_gold_vs_nongold_campaign\","
         "\"redbug\":\"blue_minus2\"}\n");
  printf("  },\n");
  printf("  \"class_matrix\": [\n");
  printf("    {\"resistance_state\":\"ordinary_damageable\",\"red\":\"temporary damage\","
         "\"blue\":\"temporary damage\",\"homing\":\"temporary damage\","
         "\"gold\":\"permanent defeat\",\"mega\":\"temporary damage\"},\n");
  printf("    {\"resistance_state\":\"flags_0x40_berry_tough\",\"red\":\"reaction only; zero damage\","
         "\"blue\":\"-2 temporary damage\",\"homing\":\"-2 temporary damage\","
         "\"gold\":\"-4 damage plus permanent defeat\",\"mega\":\"-3 temporary damage\"}\n");
  printf("  ],\n");
  printf("  \"scope_guards\": [\n");
  printf("    \"flags bit 0x40 is a runtime state and can be VM-managed; do not label every species permanently immune\",\n");
  printf("    \"boss defeat floors and overlay FSMs remain boss-row behavior even when the resident damage delta is shared\",\n");
  printf("    \"the 64x5 side table is not an immunity or kill oracle\"\n");
  printf("  ],\n");
  printf("  \"uncovered_breadth\": \"a replayable five-berry movie for every named family is absent; current evidence closes the resistance law but not exhaustive presentation breadth\"\n");
  printf("}\n");
  for (size_t i = 0; i < sizeof(evidence) / sizeof(evidence[0]); ++i) free(evidence[i].data);
  return 0;
}
