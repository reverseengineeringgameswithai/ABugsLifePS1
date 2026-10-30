#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  uint32_t address;
  uint32_t word;
  const char *meaning;
} Anchor;

static void fail(const char *message) {
  fprintf(stderr, "phase4_b01_static: %s\n", message);
  exit(1);
}

static uint32_t le32(const unsigned char *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static unsigned char *read_file(const char *path, size_t *size_out) {
  FILE *file = fopen(path, "rb");
  if (!file) fail("cannot open input");
  if (fseek(file, 0, SEEK_END) != 0) fail("cannot seek input");
  long end = ftell(file);
  if (end < 0 || fseek(file, 0, SEEK_SET) != 0) fail("cannot size input");
  size_t size = (size_t)end;
  unsigned char *data = malloc(size ? size : 1);
  if (!data || fread(data, 1, size, file) != size) fail("cannot read input");
  fclose(file);
  *size_out = size;
  return data;
}

static void sha256_hex(const unsigned char *data, size_t size, char out[65]) {
  unsigned char digest[EVP_MAX_MD_SIZE];
  unsigned int digest_size = 0;
  EVP_MD_CTX *ctx = EVP_MD_CTX_new();
  if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
      EVP_DigestUpdate(ctx, data, size) != 1 ||
      EVP_DigestFinal_ex(ctx, digest, &digest_size) != 1 || digest_size != 32) {
    fail("SHA-256 failure");
  }
  EVP_MD_CTX_free(ctx);
  for (size_t i = 0; i < 32; ++i) sprintf(out + i * 2, "%02x", digest[i]);
  out[64] = '\0';
}

static uint32_t mapped_word(const unsigned char *exe, size_t exe_size,
                            uint32_t load_address, uint32_t address) {
  if (address < load_address) fail("address precedes executable load address");
  size_t offset = 0x800u + (size_t)(address - load_address);
  if (offset + 4 > exe_size) fail("address lies outside executable payload");
  return le32(exe + offset);
}

int main(int argc, char **argv) {
  const char *exe_path = argc > 1 ? argv[1] : "SCUS_942.88";
  const char *asm_path = argc > 2 ? argv[2] :
      "asm/hand_written/8005c58c_seed_plant_trampoline_handler.s";
  const char *expected_exe =
      "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20";
  const char *expected_asm =
      "ffe0c5327644cd6ff3bea1269c924d82786263aa38bc69c0b0c2c495cc7bf9ab";
  const Anchor anchors[] = {
    {0x8005c58c, 0x169501d6, "contact identity gate"},
    {0x8005c594, 0x9642002e, "load plant extra_state"},
    {0x8005c59c, 0x30420002, "require extra_state bit 1"},
    {0x8005c5a0, 0x104001d1, "reject ineligible plant"},
    {0x8005c5f4, 0x2402f300, "constant normal impulse -3328"},
    {0x8005c5fc, 0xac226530, "write player vertical velocity"},
    {0x8005c600, 0x24020005, "constant mode 5"},
    {0x8005c608, 0xa4226580, "write player mode"},
    {0x8005c60c, 0x24020003, "constant action 3"},
    {0x8005c614, 0xa4206582, "clear contact"},
    {0x8005c61c, 0xa4206584, "clear timer"},
    {0x8005c624, 0xa4226588, "write action"},
    {0x8005c63c, 0x1054ffc2, "duplicate identity branches to reset"},
    {0x8005c548, 0x240200ff, "reset sentinel -1"},
    {0x8005c54c, 0xa39404b0, "reset sequence head to identity"},
    {0x8005c554, 0xa0222249, "reset sequence slot 1"},
    {0x8005c55c, 0xa022224a, "reset sequence slot 2"},
    {0x8005c564, 0xa022224b, "reset sequence slot 3"},
    {0x8005c56c, 0xa022224c, "reset sequence slot 4"},
    {0x8005c580, 0xa0342248, "store first identity"},
    {0x8005c65c, 0x24020071, "progress command base 113"},
    {0x8005c660, 0xaf8206ac, "write progress command"},
    {0x8005c67c, 0x10430005, "append at first -1 sentinel"},
    {0x8005c6a0, 0x24020076, "five-filled command 118"},
    {0x8005c6ac, 0x1462000e, "branch unless five are filled"},
    {0x8005c6b0, 0x24020006, "transition value 6"},
    {0x8005c6b8, 0xa42223a0, "write transition latch"},
    {0x8005c6bc, 0x2402003c, "fade timer 60"},
    {0x8005c6cc, 0xa4222470, "write fade timer"},
    {0x8005c6d4, 0x2402c000, "completion impulse -16384"},
    {0x8005c6dc, 0xac226530, "override player vertical velocity"},
    {0x8005c6e0, 0x34630001, "set bonus bit"},
    {0x8005c6e4, 0xa0830000, "write bonus flags"},
    {0x8005c6e8, 0x08017338, "jump to shared effect tail"},
    {0x8005c6ec, 0x2404000f, "effect identifier 15"}
  };

  size_t exe_size = 0, asm_size = 0;
  unsigned char *exe = read_file(exe_path, &exe_size);
  unsigned char *asm_text = read_file(asm_path, &asm_size);
  char exe_sha[65], asm_sha[65];
  sha256_hex(exe, exe_size, exe_sha);
  sha256_hex(asm_text, asm_size, asm_sha);
  if (exe_size < 0x800 || memcmp(exe, "PS-X EXE", 8) != 0)
    fail("input is not a PS-X EXE");
  if (strcmp(exe_sha, expected_exe) != 0) fail("pristine executable hash mismatch");
  if (strcmp(asm_sha, expected_asm) != 0) fail("handler ASM hash mismatch");
  uint32_t load_address = le32(exe + 0x18);
  uint32_t payload_size = le32(exe + 0x1c);
  if (load_address != 0x80010000 || payload_size != 0x00072800)
    fail("unexpected executable mapping");
  if (mapped_word(exe, exe_size, load_address, 0x8001b854) != 0x8005c58c)
    fail("type-5 dispatch target mismatch");
  for (size_t i = 0; i < sizeof(anchors) / sizeof(anchors[0]); ++i) {
    if (mapped_word(exe, exe_size, load_address, anchors[i].address) != anchors[i].word) {
      fprintf(stderr, "anchor mismatch at 0x%08x (%s)\n",
              anchors[i].address, anchors[i].meaning);
      return 1;
    }
  }

  printf("{\n");
  printf("  \"row\": \"B01_mushroom_trampoline\",\n");
  printf("  \"inputs\": {\"exe_sha256\": \"%s\", \"asm_sha256\": \"%s\"},\n",
         exe_sha, asm_sha);
  printf("  \"validation\": {\"ps_x_exe\": true, \"load_address\": \"0x%08x\", "
         "\"payload_size\": %u, \"type5_dispatch\": \"0x8005c58c\", "
         "\"opcode_anchors_checked\": %zu},\n", load_address, payload_size,
         sizeof(anchors) / sizeof(anchors[0]));
  printf("  \"qualification\": {\"walker_requires_mature_bit\": true, "
         "\"handler_requires_contact_identity\": true, \"handler_requires_extra_state_bit_1\": true},\n");
  printf("  \"normal_bounce\": {\"operation\": \"fixed_assignment\", "
         "\"vertical_velocity\": -3328, \"mode\": 5, \"contact\": 0, "
         "\"timer\": 0, \"action\": 3},\n");
  printf("  \"chain_rule\": {\"per_qualifying_contact\": true, "
         "\"incoming_velocity_read_by_impulse_path\": false, "
         "\"duplicate_still_bounces_before_sequence_reset\": true, "
         "\"distinct_identities_append_to_five_byte_sequence\": true, "
         "\"progress_command\": \"113_plus_filled_count\"},\n");
  printf("  \"completion\": {\"distinct_count\": 5, \"vertical_velocity_override\": -16384, "
         "\"transition\": 6, \"fade_timer\": 60, \"bonus_flag_or\": 1},\n");
  printf("  \"effect\": {\"shared_tail\": \"0x8005cce0\", \"identifier\": 15},\n");
  printf("  \"conclusion\": \"normal mushroom chaining reuses one fixed impulse law; "
         "the five-distinct completion launch is a separate override\"\n");
  printf("}\n");
  free(asm_text);
  free(exe);
  return 0;
}
