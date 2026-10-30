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

typedef struct {
  uint32_t pc;
  uint32_t word;
} Pin;

static void fail(const char *message) {
  fprintf(stderr, "guard failed: %s\n", message);
  exit(2);
}

static void require(bool condition, const char *message) {
  if (!condition)
    fail(message);
}

static uint8_t *load_pristine(const char *path, size_t *size) {
  FILE *file = fopen(path, "rb");
  long length;
  uint8_t *data;
  uint8_t digest[SHA256_DIGEST_LENGTH];
  char hex[SHA256_DIGEST_LENGTH * 2 + 1];

  require(file != NULL, "open executable");
  require(fseek(file, 0, SEEK_END) == 0, "seek executable");
  length = ftell(file);
  require(length >= (long)EXE_HEADER_SIZE, "executable size");
  rewind(file);
  data = malloc((size_t)length);
  require(data != NULL, "allocate executable");
  require(fread(data, 1, (size_t)length, file) == (size_t)length,
          "read executable");
  fclose(file);

  require(SHA256(data, (size_t)length, digest) != NULL, "hash executable");
  for (size_t i = 0; i < SHA256_DIGEST_LENGTH; i++)
    sprintf(hex + i * 2, "%02x", digest[i]);
  hex[sizeof hex - 1] = '\0';
  require(strcmp(hex, EXE_SHA256) == 0, "pristine executable hash");
  *size = (size_t)length;
  return data;
}

static uint32_t read_word(const uint8_t *image, size_t size, uint32_t pc) {
  size_t offset;
  require(pc >= EXE_LOAD_VA, "pin below load address");
  offset = EXE_HEADER_SIZE + (size_t)(pc - EXE_LOAD_VA);
  require(offset + 4 <= size, "pin outside executable");
  return (uint32_t)image[offset] | ((uint32_t)image[offset + 1] << 8) |
         ((uint32_t)image[offset + 2] << 16) |
         ((uint32_t)image[offset + 3] << 24);
}

static unsigned check_pins(const uint8_t *image, size_t size,
                           const Pin *pins, size_t count) {
  for (size_t i = 0; i < count; i++) {
    uint32_t actual = read_word(image, size, pins[i].pc);
    if (actual != pins[i].word) {
      fprintf(stderr, "guard failed: pin 0x%08" PRIx32
              " expected 0x%08" PRIx32 " got 0x%08" PRIx32 "\n",
              pins[i].pc, pins[i].word, actual);
      exit(2);
    }
  }
  return (unsigned)count;
}

int main(int argc, char **argv) {
  static const Pin startup[] = {
    {0x8005F690u, 0x3C028008u}, {0x8005F694u, 0x24422200u},
    {0x8005F698u, 0x3C03800Bu}, {0x8005F69Cu, 0x246339A0u},
    {0x8005F6A0u, 0xAC400000u}, {0x8005F6A4u, 0x24420004u},
    {0x8005F6A8u, 0x0043082Bu}, {0x8005F6ACu, 0x1420FFFCu},
    {0x8005F6B0u, 0x00000000u},
  };
  static const Pin per_load[] = {
    {0x8003A398u, 0x3C05800Au}, {0x8003A39Cu, 0x24A565B0u},
    {0x8003A3A0u, 0x3C04800Au}, {0x8003A3A4u, 0x2484C210u},
    {0x8003A3B8u, 0xAC800000u}, {0x8003A3BCu, 0xACA00000u},
    {0x8003A3C0u, 0x24A50004u}, {0x8003A3C4u, 0x24630001u},
    {0x8003A3C8u, 0x28620008u}, {0x8003A3CCu, 0x1440FFFAu},
    {0x8003A3D0u, 0x24840004u},
  };
  const uint32_t startup_lo = 0x80082200u;
  const uint32_t startup_hi = 0x800B39A0u;
  const uint32_t table_lo = 0x8009B5A8u;
  const uint32_t table_hi = 0x8009B648u;
  const uint32_t sibling_a = 0x8009C210u;
  const uint32_t sibling_b = 0x800A65B0u;
  size_t image_size;
  uint8_t *image;
  unsigned pins = 0;

  require(argc <= 2, "usage: phase4_e16_table_lifetime_guard [SCUS_942.88]");
  image = load_pristine(argc == 2 ? argv[1] : EXE_PATH, &image_size);
  pins += check_pins(image, image_size, startup,
                     sizeof startup / sizeof startup[0]);
  pins += check_pins(image, image_size, per_load,
                     sizeof per_load / sizeof per_load[0]);

  require(startup_lo <= table_lo && table_hi <= startup_hi,
          "0x30..0x57 table outside startup clear");
  require(table_lo != sibling_a && table_lo != sibling_b,
          "target table incorrectly treated as per-load sibling");

  printf("{\n");
  printf("  \"pristine_exe_sha256\": \"%s\",\n", EXE_SHA256);
  printf("  \"instruction_pins\": %u,\n", pins);
  printf("  \"startup_clear\": {\"store_pc\": \"0x8005F6A0\", "
         "\"lo\": \"0x%08" PRIX32 "\", \"hi_exclusive\": \"0x%08" PRIX32
         "\", \"words\": %" PRIu32 "},\n",
         startup_lo, startup_hi, (startup_hi - startup_lo) / 4u);
  printf("  \"target_table\": {\"lo\": \"0x%08" PRIX32
         "\", \"hi_exclusive\": \"0x%08" PRIX32
         "\", \"startup_cleared\": true, \"per_load_cleared\": false},\n",
         table_lo, table_hi);
  printf("  \"per_load_sibling_resets\": [\"0x%08" PRIX32
         "\", \"0x%08" PRIX32 "\"]\n", sibling_a, sibling_b);
  printf("}\n");
  free(image);
  return 0;
}
