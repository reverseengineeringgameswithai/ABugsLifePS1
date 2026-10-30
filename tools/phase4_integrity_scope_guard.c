#include <inttypes.h>
#include <openssl/sha.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_PATH "REBUILD/files/SCUS_942.88"
#define EXE_LOAD_VA 0x80010000u
#define EXE_HEADER_SIZE 0x800u
#define EXE_SHA256 "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"
#define GP_VALUE 0x80081D98u

typedef struct {
  uint32_t pc;
  uint32_t word;
  const char *purpose;
} Pin;

static void require(bool condition, const char *message) {
  if (!condition) {
    fprintf(stderr, "guard failed: %s\n", message);
    exit(2);
  }
}

static uint8_t *load_pristine(const char *path, size_t *size) {
  FILE *file = fopen(path, "rb");
  long length;
  uint8_t *data;
  uint8_t digest[SHA256_DIGEST_LENGTH];
  char hex[SHA256_DIGEST_LENGTH * 2 + 1];

  require(file != NULL, "open pristine executable");
  require(fseek(file, 0, SEEK_END) == 0, "seek pristine executable");
  length = ftell(file);
  require(length >= (long)EXE_HEADER_SIZE, "pristine executable size");
  rewind(file);
  data = malloc((size_t)length);
  require(data != NULL, "allocate pristine executable");
  require(fread(data, 1, (size_t)length, file) == (size_t)length,
          "read pristine executable");
  fclose(file);
  require(SHA256(data, (size_t)length, digest) != NULL,
          "hash pristine executable");
  for (size_t i = 0; i < SHA256_DIGEST_LENGTH; i++)
    sprintf(hex + i * 2, "%02x", digest[i]);
  hex[sizeof hex - 1] = '\0';
  require(strcmp(hex, EXE_SHA256) == 0, "pristine executable hash");
  *size = (size_t)length;
  return data;
}

static uint32_t read_word(const uint8_t *image, size_t size, uint32_t pc) {
  size_t offset;
  require(pc >= EXE_LOAD_VA, "pin below executable load address");
  offset = EXE_HEADER_SIZE + (size_t)(pc - EXE_LOAD_VA);
  require(offset + 4 <= size, "pin outside executable image");
  return (uint32_t)image[offset] | ((uint32_t)image[offset + 1] << 8) |
         ((uint32_t)image[offset + 2] << 16) |
         ((uint32_t)image[offset + 3] << 24);
}

static unsigned pin_all(const uint8_t *image, size_t size,
                        const Pin *pins, size_t count) {
  for (size_t i = 0; i < count; i++) {
    uint32_t actual = read_word(image, size, pins[i].pc);
    if (actual != pins[i].word) {
      fprintf(stderr,
              "guard failed: 0x%08" PRIx32 " (%s) expected 0x%08" PRIx32
              " got 0x%08" PRIx32 "\n",
              pins[i].pc, pins[i].purpose, pins[i].word, actual);
      exit(2);
    }
  }
  return (unsigned)count;
}

int main(int argc, char **argv) {
  static const Pin grounded[] = {
    {0x8004EF70u, 0x3C10800Au, "player-base high half"},
    {0x8004EF74u, 0x26106590u, "s0 = 0x800A6590"},
    {0x8004EFD8u, 0x0C01204Eu, "call player update"},
    {0x8004EFDCu, 0x2604FF70u, "delay slot a0 = 0x800A6500"},
    {0x80048140u, 0x00808821u, "player update s1 = a0"},
    {0x800495B0u, 0x02202021u, "integrator a0 = player"},
    {0x800495B4u, 0x2625002Cu, "integrator a1 = player+0x2C"},
    {0x800495B8u, 0x26260082u, "integrator a2 = player+0x82"},
    {0x800495C8u, 0x0C00D8CFu, "call 0x8003633C"},
    {0x8003636Cu, 0xAFA60028u, "save a2 contact pointer"},
    {0x80036B84u, 0x8FB60028u, "load saved contact pointer"},
    {0x80036B90u, 0x8FB60030u, "old alleged PC is a load"},
    {0x80036BECu, 0x24110001u, "s1 = 1"},
    {0x80036C98u, 0x10E2000Au, "a3 == 2 selects clear arm"},
    {0x80036CA0u, 0x12110003u, "s0 == 1 selects set arm"},
    {0x80036CA8u, 0x14F10006u, "a3 != 1 selects clear arm"},
    {0x80036CB0u, 0x8FB60028u, "reload player+0x82 pointer"},
    {0x80036CB8u, 0xA2D10000u, "store byte 1 at player+0x82"},
    {0x80036CBCu, 0x0800DB34u, "old alleged PC is a jump"},
    {0x80036CC0u, 0xA2D10001u, "delay-slot byte 1 at player+0x83"},
    {0x80036CCCu, 0xA2C00001u, "alternate arm clears byte 1"},
    {0x80036CD0u, 0x1CE0FFD2u, "old alleged PC is a branch"},
  };
  static const Pin arena[] = {
    {0x8003C2ECu, 0x3C02801Du, "arena value high half"},
    {0x8003C2F0u, 0x2442C390u, "arena value = 0x801CC390"},
    {0x8003C2F4u, 0xAF8204A0u, "resolved direct arena writer"},
    {0x800313B4u, 0x3C028008u, "direct arena reader high half"},
    {0x800313B8u, 0x8C422238u, "resolved direct arena reader"},
    {0x8003D5D8u, 0x8F8204A0u, "resolved gp-relative arena reader"},
  };
  static const Pin contact[] = {
    {0x800586B8u, 0x3C13800Bu, "walker pool high half"},
    {0x800586BCu, 0x26730D18u, "walker s3 = pool"},
    {0x80058714u, 0x26720022u, "walker s2 = record+0x22"},
    {0x80058740u, 0x92420011u, "walker reads record+0x33"},
    {0x80058748u, 0x30420002u, "walker flag bit 2 gate"},
    {0x800588A4u, 0x24020060u, "walker replacement flags"},
    {0x800588ACu, 0xA2420011u, "walker writes record+0x33"},
    {0x80058A04u, 0x26520038u, "walker record stride"},
    {0x80058A14u, 0x26730038u, "walker pool stride"},
    {0x80058BECu, 0x3C15800Bu, "actor-contact pool high half"},
    {0x80058BF0u, 0x26B50D18u, "actor-contact s5 = pool"},
    {0x80058BF4u, 0x26B10008u, "actor-contact s1 = record+8"},
    {0x80058C64u, 0x9222002Bu, "actor-contact reads record+0x33"},
    {0x80058C6Cu, 0x30420004u, "actor-contact flag bit 4 gate"},
    {0x80058C78u, 0x8622001Au, "actor-contact reads record+0x22"},
    {0x80058C80u, 0x1840017Fu, "actor-contact lifetime gate"},
    {0x80058E3Cu, 0x26310038u, "actor-contact record stride A"},
    {0x80058F70u, 0x240200E1u, "actor-contact replacement flags"},
    {0x80058F74u, 0xA222002Bu, "actor-contact writes record+0x33"},
    {0x80059058u, 0x26310038u, "actor-contact record stride B"},
    {0x80059280u, 0x26310038u, "actor-contact record stride C"},
  };
  size_t image_size;
  uint8_t *image;
  unsigned count = 0;

  require(argc <= 2, "usage: phase4_integrity_scope_guard [SCUS_942.88]");
  image = load_pristine(argc == 2 ? argv[1] : EXE_PATH, &image_size);
  count += pin_all(image, image_size, grounded,
                   sizeof grounded / sizeof grounded[0]);
  count += pin_all(image, image_size, arena, sizeof arena / sizeof arena[0]);
  count += pin_all(image, image_size, contact,
                   sizeof contact / sizeof contact[0]);

  require(0x800A6590u - 0x90u == 0x800A6500u,
          "player caller delay-slot base derivation");
  require(0x800A6500u + 0x82u == 0x800A6582u,
          "grounded pointer effective address");
  require(GP_VALUE + 0x4A0u == 0x80082238u,
          "gp-relative arena effective address");
  require(0x801D0000u + (uint32_t)(int32_t)(int16_t)0xC390u == 0x801CC390u,
          "arena limit value materialization");
  require(0x800B0D18u + 0x22u + 0x11u == 0x800B0D4Bu,
          "walker record+0x33 effective address");
  require(0x800B0D18u + 8u + 0x2Bu == 0x800B0D4Bu,
          "actor-contact record+0x33 effective address");

  printf("{\n");
  printf("  \"pristine_exe_sha256\": \"%s\",\n", EXE_SHA256);
  printf("  \"instruction_pins\": %u,\n", count);
  printf("  \"grounded_player_call\": {\"producer_pcs\": "
         "[\"0x80036CB8\", \"0x80036CC0\"], "
         "\"value\": \"0x0101\", \"global_exclusivity\": false},\n");
  printf("  \"arena_limit\": {\"resolved_writers\": [\"0x8003C2F4\"], "
         "\"resolved_readers\": [\"0x800313B8\", \"0x8003D5D8\"], "
         "\"value\": \"0x801CC390\"},\n");
  printf("  \"contact_flag\": {\"currently_resolved_post_creation_stores\": "
         "[\"0x800588AC\", \"0x80058F74\"], "
         "\"complete_census\": false}\n");
  printf("}\n");
  free(image);
  return 0;
}
