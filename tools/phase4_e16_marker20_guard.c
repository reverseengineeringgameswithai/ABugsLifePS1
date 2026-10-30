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

int main(int argc, char **argv) {
  static const Pin pins[] = {
    {0x8003ADA4u, 0x24020020u}, /* marker == 0x20 */
    {0x8003ADA8u, 0x16820111u}, /* other marker -> other arm */
    {0x8003AE14u, 0x3C058421u},
    {0x8003AE20u, 0x96630010u}, /* first RGB555 pixel */
    {0x8003AE24u, 0x34A50843u}, /* multiplier = 0x84210843 */
    {0x8003AE28u, 0x3063001Fu}, /* red */
    {0x8003AE50u, 0xAC2371BCu},
    {0x8003AE6Cu, 0x3063001Fu}, /* green */
    {0x8003AE94u, 0xAC2371C0u},
    {0x8003AEB0u, 0x3042001Fu}, /* blue */
    {0x8003AEE4u, 0xAC2271C4u},
  };
  size_t image_size;
  uint8_t *image;

  require(argc <= 2, "usage: phase4_e16_marker20_guard [SCUS_942.88]");
  image = load_pristine(argc == 2 ? argv[1] : EXE_PATH, &image_size);
  for (size_t i = 0; i < sizeof pins / sizeof pins[0]; i++) {
    uint32_t actual = read_word(image, image_size, pins[i].pc);
    if (actual != pins[i].word) {
      fprintf(stderr, "guard failed: pin 0x%08" PRIx32
              " expected 0x%08" PRIx32 " got 0x%08" PRIx32 "\n",
              pins[i].pc, pins[i].word, actual);
      return 2;
    }
  }

  printf("{\n");
  printf("  \"pristine_exe_sha256\": \"%s\",\n", EXE_SHA256);
  printf("  \"instruction_pins\": %zu,\n", sizeof pins / sizeof pins[0]);
  printf("  \"marker\": \"0x20\",\n");
  printf("  \"rgb555_source_offset\": 16,\n");
  printf("  \"scale_multiplier\": \"0x84210843\",\n");
  printf("  \"cache_addresses\": [\"0x800771BC\", \"0x800771C0\", \"0x800771C4\"]\n");
  printf("}\n");
  free(image);
  return 0;
}
