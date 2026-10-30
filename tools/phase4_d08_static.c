/*
 * Phase 4 D08 Horsefly static closure guard.
 *
 * This reads the hash-pinned pristine PS-X EXE directly.  It rejects any
 * derivative image and verifies the exact instructions/data that implement
 * the Horsefly callback, contact reaction, berry damage, and generic KO tail.
 *
 * Build:
 *   cc -std=c11 -O2 -Wall -Wextra tools/phase4_d08_static.c \
 *      -lcrypto -o /tmp/phase4_d08_static
 * Run:
 *   /tmp/phase4_d08_static SCUS_942.88
 */

#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_SHA256 "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"

struct word_check {
  uint32_t address;
  uint32_t word;
  const char *meaning;
};

static const struct word_check checks[] = {
    {0x8004a14c, 0x8c850004, "callback loads actor from wrapper+4"},
    {0x8004a154, 0x8ca20044, "callback loads actor+0x44 state"},
    {0x8004a15c, 0x28420002, "callback tests state below two"},
    {0x8004a164, 0x24040028, "callback selects sound id 40"},
    {0x8004a168, 0x0c014113, "callback calls positional sound routine 0x8005044c"},
    {0x8004a16c, 0x24a50004, "callback passes actor position"},
    {0x8004b650, 0xa622006c, "ordinary actor contact stores reaction 15 at +0x6c"},
    {0x80058df4, 0x9642005c, "projectile gate loads actor flags +0x5c"},
    {0x80058dfc, 0x30420040, "projectile gate isolates resistance bit 0x40"},
    {0x80058e00, 0x1440011f, "resistant branch rejects projectile class"},
    {0x80058ed4, 0x24020014, "accepted projectile selects reaction 20"},
    {0x80058ed8, 0xa642006c, "accepted projectile stores reaction at +0x6c"},
    {0x8005905c, 0x8642006e, "damage dispatch loads signed HP +0x6e"},
    {0x80059074, 0x9223002c, "damage dispatch loads projectile marker +0x2c"},
    {0x80059094, 0x106a0013, "marker 1 selects minus 99"},
    {0x80059098, 0x2482ff9d, "minus 99 arithmetic"},
    {0x800590a4, 0x2402007f, "marker 127 comparison"},
    {0x800590a8, 0x10620009, "marker 127 selects minus 4"},
    {0x800590ac, 0x24020080, "marker 128 comparison"},
    {0x800590b0, 0x1062000c, "marker 128 selects minus 3"},
    {0x800590b4, 0x2482fffd, "minus 3 arithmetic"},
    {0x800590c4, 0x2482fffe, "marker 0 selects minus 2"},
    {0x800590cc, 0x2482fffe, "marker 12 selects minus 2"},
    {0x800590d4, 0x2482fffc, "marker 127 selects minus 4 arithmetic"},
    {0x800590e0, 0x2442ffff, "default marker selects minus 1"},
    {0x800590e4, 0xa642006e, "damage dispatch stores new HP +0x6e"},
    {0x8005914c, 0x34420002, "eligible damaged actor gains chase bit 0x2"},
    {0x80059150, 0xa642005c, "chase flags store at +0x5c"},
    {0x80059154, 0x8642006e, "post-hit path reloads signed HP"},
    {0x8005915c, 0x1c40002f, "positive HP bypasses KO tail"},
    {0x8005929c, 0x12e0003a, "death class zero bypasses KO state"},
    {0x800592a0, 0x240203e7, "KO sentinel is 999"},
    {0x800592a8, 0xa642006e, "KO tail stores HP sentinel at +0x6e"},
    {0x800592ac, 0xa6400060, "KO tail clears actor +0x60"},
    {0x800592b0, 0x34630880, "KO tail adds flags 0x880"},
    {0x800592b4, 0x3063fffd, "KO tail clears flags bit 0x2"},
    {0x800592b8, 0xa643005c, "KO tail stores flags at +0x5c"},
    {0x800592c0, 0x8c427b2c, "KO tail loads shared stop-program pointer"},
    {0x800592c8, 0xae420070, "KO tail redirects mover VM +0x70"},
    {0x800592cc, 0x2ae20002, "death class below two test"},
    {0x800592d0, 0x1440001b, "class one bypasses quota/drop-effect block"},
    {0x80059300, 0xa4620000, "class >=2 decrements enemy quota"},
    {0x80059340, 0x0c01262b, "KO tail calls actor retirement routine 0x800498ac"},
    {0x80059344, 0x24050001, "retirement call uses mode one"},
};

static const uint8_t fly_wander[] = {
    0x16, 0x00, 0xc0, 0xff, 0xc0, 0xff, /* set_byte_params[-64,-64] */
    0x0d, 0x00, 0x00, 0x00, 0x02, 0x00, /* anim_clip_load[0,2] */
    0x02, 0x00, 0x3f, 0x00, 0x20, 0x00, /* wait_random[63,32] */
    0x03, 0x00,                         /* random_dir_step */
    0x05, 0x00,                         /* park_seek */
    0xff, 0xff, 0x05, 0x00,             /* jump_back[5] */
    0x00, 0x00,                         /* park_end */
};

static const uint8_t defeated_stop_loop[] = {
    0x07, 0x00,             /* park_arrive_stop */
    0xff, 0xff, 0x01, 0x00, /* jump_back[1] -> 0x800776ac */
};

static uint32_t le32(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void fatal(const char *message) {
  fprintf(stderr, "phase4_d08_static: %s\n", message);
  exit(1);
}

static void sha256_hex(const uint8_t *data, size_t size, char out[65]) {
  unsigned char digest[SHA256_DIGEST_LENGTH];
  static const char digits[] = "0123456789abcdef";
  SHA256(data, size, digest);
  for (size_t i = 0; i < sizeof(digest); i++) {
    out[i * 2] = digits[digest[i] >> 4];
    out[i * 2 + 1] = digits[digest[i] & 15];
  }
  out[64] = '\0';
}

static size_t file_offset(uint32_t load_address, size_t file_size,
                          uint32_t address, size_t width) {
  if (address < load_address)
    fatal("guest address precedes executable load address");
  size_t offset = 0x800u + (size_t)(address - load_address);
  if (offset > file_size || width > file_size - offset)
    fatal("guest address lies outside executable payload");
  return offset;
}

int main(int argc, char **argv) {
  if (argc != 2) {
    fprintf(stderr, "usage: %s /path/to/pristine/SCUS_942.88\n", argv[0]);
    return 2;
  }

  FILE *fp = fopen(argv[1], "rb");
  if (!fp)
    fatal("cannot open executable");
  if (fseek(fp, 0, SEEK_END) != 0)
    fatal("cannot seek executable");
  long signed_size = ftell(fp);
  if (signed_size < 0 || fseek(fp, 0, SEEK_SET) != 0)
    fatal("cannot size executable");
  size_t size = (size_t)signed_size;
  uint8_t *data = malloc(size);
  if (!data || fread(data, 1, size, fp) != size)
    fatal("cannot read executable");
  fclose(fp);

  char hash[65];
  sha256_hex(data, size, hash);
  if (strcmp(hash, EXPECTED_SHA256) != 0)
    fatal("input is not the hash-pinned pristine executable");
  if (size < 0x800 || memcmp(data, "PS-X EXE", 8) != 0)
    fatal("invalid PS-X EXE header");

  uint32_t load_address = le32(data + 0x18);
  uint32_t payload_size = le32(data + 0x1c);
  if (load_address != 0x80010000 || payload_size != 0x00072800)
    fatal("unexpected executable mapping");

  for (size_t i = 0; i < sizeof(checks) / sizeof(checks[0]); i++) {
    size_t off = file_offset(load_address, size, checks[i].address, 4);
    if (le32(data + off) != checks[i].word) {
      fprintf(stderr, "mismatch at 0x%08" PRIx32 " (%s)\n",
              checks[i].address, checks[i].meaning);
      return 1;
    }
  }

  size_t wander_off = file_offset(load_address, size, 0x800776d0,
                                  sizeof(fly_wander));
  size_t stop_off = file_offset(load_address, size, 0x800776ac,
                                sizeof(defeated_stop_loop));
  size_t pointer_off = file_offset(load_address, size, 0x80077b2c, 4);
  if (memcmp(data + wander_off, fly_wander, sizeof(fly_wander)) != 0)
    fatal("Horsefly wander bytecode differs");
  if (memcmp(data + stop_off, defeated_stop_loop,
             sizeof(defeated_stop_loop)) != 0)
    fatal("defeated stop bytecode differs");
  if (le32(data + pointer_off) != 0x800776ac)
    fatal("shared defeated-program pointer differs");

  printf("{\n");
  printf("  \"schema\": \"abl-phase4-d08-static-v1\",\n");
  printf("  \"row\": \"D08_flies\",\n");
  printf("  \"status\": \"verified\",\n");
  printf("  \"input\": {\"path\": \"%s\", \"sha256\": \"%s\", "
         "\"load_address\": \"0x%08" PRIx32 "\", \"payload_size\": %" PRIu32 "},\n",
         argv[1], hash, load_address, payload_size);
  printf("  \"instruction_checks\": %zu,\n",
         sizeof(checks) / sizeof(checks[0]));
  printf("  \"identity\": {\"actor_id\": 6, \"wander_program\": \"0x800776d0\", "
         "\"contact_callback\": \"0x8004a144\"},\n");
  printf("  \"wander_program\": [\"set_byte_params[-64,-64]\", "
         "\"anim_clip_load[0,2]\", \"wait_random[63,32]\", "
         "\"random_dir_step\", \"park_seek\", \"jump_back[5]\"],\n");
  printf("  \"family_attack_result\": \"no proximity, call_native, chase, or projectile opcode in the Horsefly program; ordinary body contact is the attack\",\n");
  printf("  \"damage_dispatch\": {\"marker_0\": -2, \"marker_1\": -99, "
         "\"marker_12\": -2, \"marker_127\": -4, "
         "\"marker_128\": -3, \"default\": -1, "
         "\"reaction_ticks\": 20},\n");
  printf("  \"temporary_ko\": {\"hp_sentinel\": 999, "
         "\"flags_or\": \"0x0880\", \"flags_clear\": \"0x0002\", "
         "\"stop_program\": \"0x800776ac\", "
         "\"stop_loop\": [\"park_arrive_stop\", \"jump_back[1]\"], "
         "\"retirement_call\": \"0x800498ac(actor,1)\"},\n");
  printf("  \"class_boundary\": \"death class 1 bypasses the class>=2 effect/quota block at 0x800592d8..0x8005933c\"\n");
  printf("}\n");
  free(data);
  return 0;
}
