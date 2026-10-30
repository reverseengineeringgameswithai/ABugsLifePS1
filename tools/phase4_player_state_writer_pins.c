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
  uint32_t store_pc;
  uint32_t store_word;
  uint32_t value_pc;
  uint32_t value_word;
  unsigned value;
} WriterPin;

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

static void pin_word(const uint8_t *image, size_t size, uint32_t pc,
                     uint32_t expected) {
  uint32_t actual = read_word(image, size, pc);
  if (actual != expected) {
    fprintf(stderr, "guard failed: pin 0x%08" PRIx32
            " expected 0x%08" PRIx32 " got 0x%08" PRIx32 "\n",
            pc, expected, actual);
    exit(2);
  }
}

int main(int argc, char **argv) {
  static const WriterPin writers[] = {
    {0x800486B4u, 0xA6220080u, 0x800486B0u, 0x24020005u, 5},
    {0x80048930u, 0xA6220080u, 0x8004892Cu, 0x24020005u, 5},
    {0x80048A50u, 0xA6230080u, 0x80048A4Cu, 0x24030001u, 1},
    {0x80048BDCu, 0xA6220080u, 0x80048BD4u, 0x24020001u, 1},
    {0x80048CBCu, 0xA6230080u, 0x80048CB0u, 0x24030004u, 4},
    {0x80048CFCu, 0xA6220080u, 0x80048CF4u, 0x24020003u, 3},
    {0x80048D10u, 0xA6200080u, 0, 0, 0},
    {0x80048D50u, 0xA6220080u, 0x80048D4Cu, 0x24020002u, 2},
    {0x80048D64u, 0xA6220080u, 0x80048D60u, 0x24020006u, 6},
    {0x80048E0Cu, 0xA6220080u, 0x80048E04u, 0x24020001u, 1},
    {0x8004A84Cu, 0xA4226580u, 0x8004A83Cu, 0x24020005u, 5},
    {0x8004AFA4u, 0xA7C2007Cu, 0x8004AFA0u, 0x24020005u, 5},
    {0x8004B044u, 0xA6E20054u, 0x8004B040u, 0x24020005u, 5},
    {0x8004B340u, 0xA6C20006u, 0x8004B33Cu, 0x24020005u, 5},
    {0x8005B270u, 0xA4206580u, 0, 0, 0},
    {0x8005C404u, 0xA4226580u, 0x8005C3FCu, 0x24020005u, 5},
    {0x8005C608u, 0xA4226580u, 0x8005C600u, 0x24020005u, 5},
    {0x8005C854u, 0xA4226580u, 0x8005C84Cu, 0x24020005u, 5},
    {0x8005D0B4u, 0xA4286580u, 0x8005D09Cu, 0x24080005u, 5},
  };
  size_t image_size;
  uint8_t *image;
  unsigned instruction_pins = 0;
  unsigned value_three_count = 0;

  require(argc <= 2, "usage: phase4_player_state_writer_pins [SCUS_942.88]");
  image = load_pristine(argc == 2 ? argv[1] : EXE_PATH, &image_size);
  for (size_t i = 0; i < sizeof writers / sizeof writers[0]; i++) {
    pin_word(image, image_size, writers[i].store_pc, writers[i].store_word);
    instruction_pins++;
    if (writers[i].value_pc != 0) {
      pin_word(image, image_size, writers[i].value_pc, writers[i].value_word);
      instruction_pins++;
    }
    if (writers[i].value == 3)
      value_three_count++;
  }
  require(value_three_count == 1, "resolved direct value-3 producer count");

  printf("{\n");
  printf("  \"pristine_exe_sha256\": \"%s\",\n", EXE_SHA256);
  printf("  \"instruction_pins\": %u,\n", instruction_pins);
  printf("  \"resolved_direct_writers\": %zu,\n",
         sizeof writers / sizeof writers[0]);
  printf("  \"resolved_direct_value_3_writers\": [\"0x80048CFC\"],\n");
  printf("  \"writer_pcs\": [");
  for (size_t i = 0; i < sizeof writers / sizeof writers[0]; i++)
    printf("%s\"0x%08" PRIX32 "\"", i ? ", " : "", writers[i].store_pc);
  printf("]\n}\n");
  free(image);
  return 0;
}
