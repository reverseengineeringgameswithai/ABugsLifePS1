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
  static const Pin writers[] = {
    {0x80048654u, 0xA622007Eu}, {0x8004A808u, 0xA4820000u},
    {0x80051EA0u, 0xA602FFFCu}, {0x80051F60u, 0xA422657Eu},
    {0x800588D0u, 0xA7C20000u}, {0x800589A8u, 0xA422657Eu},
    {0x8005B268u, 0xA420657Eu},
  };
  static const Pin readers[] = {
    {0x80048640u, 0x8622007Eu}, {0x80049718u, 0x8622007Eu},
    {0x8004A7A4u, 0x8463657Eu}, {0x8004A7E0u, 0x84820000u},
    {0x80051C3Cu, 0x84E7657Eu}, {0x80055BC4u, 0x8442657Eu},
    {0x800588B0u, 0x87C20000u},
  };
  static const Pin false_writer[] = {
    {0x8004AC18u, 0x3C03800Au}, /* lui v1,0x800a */
    {0x8004AC1Cu, 0x24636500u}, /* addiu v1,v1,0x6500 */
    {0x8004AC70u, 0x247E0004u}, /* addiu fp,v1,4 */
    {0x8004AFB0u, 0xA7C0007Eu}, /* sh zero,0x7e(fp) */
  };
  static const Pin health[] = {
    {0x80046C04u, 0xA6620094u}, {0x8004A844u, 0x94636594u},
    {0x8004A888u, 0xA4236594u}, {0x8004F0E0u, 0x04400003u},
    {0x8004F0E8u, 0x0C012AFDu}, {0x8005291Cu, 0xA4620000u},
    {0x80055124u, 0xA4226594u}, {0x80058890u, 0xA4620000u},
    {0x8005B30Cu, 0xA4226594u},
  };
  size_t image_size;
  uint8_t *image;
  unsigned pins = 0;

  require(argc <= 2, "usage: phase4_power_slot_writer_guard [SCUS_942.88]");
  image = load_pristine(argc == 2 ? argv[1] : EXE_PATH, &image_size);
  pins += check_pins(image, image_size, writers,
                     sizeof writers / sizeof writers[0]);
  pins += check_pins(image, image_size, readers,
                     sizeof readers / sizeof readers[0]);
  pins += check_pins(image, image_size, false_writer,
                     sizeof false_writer / sizeof false_writer[0]);
  pins += check_pins(image, image_size, health,
                     sizeof health / sizeof health[0]);

  require(0x6500u + 4u + 0x7Eu == 0x6582u,
          "knockdown store effective address offset");
  printf("{\n");
  printf("  \"pristine_exe_sha256\": \"%s\",\n", EXE_SHA256);
  printf("  \"instruction_pins\": %u,\n", pins);
  printf("  \"resolved_direct_writers\": 7,\n");
  printf("  \"resolved_direct_readers\": 7,\n");
  printf("  \"resolved_health_writers\": 6,\n");
  printf("  \"health_damage_decrement_pc\": \"0x8004A888\",\n");
  printf("  \"health_alive_check_branch_pc\": \"0x8004F0E0\",\n");
  printf("  \"retracted_writer\": {\"pc\": \"0x8004AFB0\", "
         "\"base_delta\": 4, \"effective_player_offset\": \"0x82\", "
         "\"targets_power_slot\": false}\n");
  printf("}\n");
  free(image);
  return 0;
}
