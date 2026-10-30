#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/*
 * Offline retail-ASM contract scan for the A13 plant-output timeout gate.
 *
 * Usage:
 *   cc -O2 -std=c11 tools/phase4_a13_timeout_gate.c -o /tmp/phase4_a13_timeout_gate
 *   /tmp/phase4_a13_timeout_gate SCUS_942.88
 */

static const uint32_t k_load_va = 0x80010000u;
static const uint32_t k_exe_header = 0x800u;

typedef struct Contract {
  uint32_t pc;
  uint32_t word;
  const char *meaning;
} Contract;

static uint32_t read_le32(const unsigned char *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static const char *memory_op_name(unsigned op) {
  switch (op) {
    case 32: return "lb";
    case 33: return "lh";
    case 35: return "lw";
    case 36: return "lbu";
    case 37: return "lhu";
    case 40: return "sb";
    case 41: return "sh";
    case 43: return "sw";
    default: return "other";
  }
}

static int is_memory_op(unsigned op) {
  return op == 32 || op == 33 || op == 35 || op == 36 || op == 37 ||
         op == 40 || op == 41 || op == 43;
}

int main(int argc, char **argv) {
  static const Contract contracts[] = {
    {0x800472b8u, 0xaf800694u, "clear nearest-eligible-actor latch"},
    {0x8004736cu, 0xaf910694u, "store nearest scanned actor"},
    {0x80047398u, 0xaf820694u, "store direct-path actor"},
    {0x80047558u, 0x8f83070cu, "load plant-output timer"},
    {0x80047560u, 0x18600055u, "return when timer is inactive"},
    {0x80047568u, 0x8f820694u, "load nearest-eligible-actor latch"},
    {0x80047570u, 0x14400002u, "skip decrement while latch is nonzero"},
    {0x80047574u, 0x2462ffffu, "compute timer minus one in delay slot"},
    {0x80047578u, 0xaf82070cu, "commit timer decrement"},
    {0x80047584u, 0x1440004cu, "return until timer reaches zero"},
    {0x8004759cu, 0x3083000fu, "extract maximum available output"},
    {0x800475c0u, 0xa2300000u, "normalize selector to maximum"},
  };
  FILE *file;
  unsigned char *bytes;
  long size;
  unsigned failures = 0;
  unsigned owners = 0;

  if (argc != 2) {
    fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]);
    return 2;
  }

  file = fopen(argv[1], "rb");
  if (!file) {
    perror(argv[1]);
    return 1;
  }
  if (fseek(file, 0, SEEK_END) != 0 || (size = ftell(file)) < 0 ||
      fseek(file, 0, SEEK_SET) != 0) {
    fclose(file);
    return 1;
  }
  bytes = (unsigned char *)malloc((size_t)size);
  if (!bytes || fread(bytes, 1, (size_t)size, file) != (size_t)size) {
    free(bytes);
    fclose(file);
    return 1;
  }
  fclose(file);

  for (size_t i = 0; i < sizeof(contracts) / sizeof(contracts[0]); ++i) {
    uint32_t offset = k_exe_header + contracts[i].pc - k_load_va;
    uint32_t actual = 0;
    int ok = offset + 4u <= (uint32_t)size;
    if (ok)
      actual = read_le32(bytes + offset);
    ok = ok && actual == contracts[i].word;
    printf("contract pc=%08x actual=%08x expected=%08x ok=%d %s\n",
           contracts[i].pc, actual, contracts[i].word, ok,
           contracts[i].meaning);
    if (!ok)
      failures++;
  }

  puts("owners of gp+0x694 (runtime address 0x8008242c):");
  for (uint32_t offset = k_exe_header; offset + 4u <= (uint32_t)size;
       offset += 4u) {
    uint32_t word = read_le32(bytes + offset);
    unsigned op = word >> 26;
    unsigned base = (word >> 21) & 31u;
    unsigned rt = (word >> 16) & 31u;
    if (base == 28u && (word & 0xffffu) == 0x0694u && is_memory_op(op)) {
      printf("  pc=%08x word=%08x op=%s rt=r%u\n",
             k_load_va + offset - k_exe_header, word,
             memory_op_name(op), rt);
      owners++;
    }
  }
  printf("owner_count=%u contract_failures=%u\n", owners, failures);
  free(bytes);
  return failures == 0 && owners == 8 ? 0 : 1;
}
