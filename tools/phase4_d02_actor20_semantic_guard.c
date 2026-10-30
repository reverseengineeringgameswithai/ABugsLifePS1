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

typedef struct { uint32_t pc, word; } Insn;
typedef struct { uint32_t pc; unsigned count; const char *kind; } SiteCount;

static unsigned op(uint32_t w) { return w >> 26; }
static unsigned rs(uint32_t w) { return (w >> 21) & 31; }
static unsigned rt(uint32_t w) { return (w >> 16) & 31; }
static unsigned rd(uint32_t w) { return (w >> 11) & 31; }
static unsigned fn(uint32_t w) { return w & 63; }
static int16_t imm(uint32_t w) { return (int16_t)(w & 0xffff); }
static uint32_t branch_target(uint32_t pc, uint32_t w) {
  return pc + 4 + ((int32_t)imm(w) << 2);
}
static bool memop(uint32_t w, unsigned opcode, unsigned reg, int16_t offset, unsigned base) {
  return op(w) == opcode && rt(w) == reg && imm(w) == offset && rs(w) == base;
}
static void require(bool ok, const char *what) {
  if (!ok) { fprintf(stderr, "guard failed: %s\n", what); exit(2); }
}
static uint8_t *load_pristine(const char *path, size_t *size) {
  FILE *f = fopen(path, "rb");
  long n;
  uint8_t *data;
  uint8_t digest[SHA256_DIGEST_LENGTH];
  char hex[SHA256_DIGEST_LENGTH * 2 + 1];
  require(f != NULL, "open pristine executable");
  require(fseek(f, 0, SEEK_END) == 0, "seek pristine executable");
  n = ftell(f);
  require(n >= (long)EXE_HEADER_SIZE, "pristine executable size");
  rewind(f);
  data = malloc((size_t)n);
  require(data != NULL, "allocate pristine executable");
  require(fread(data, 1, (size_t)n, f) == (size_t)n, "read pristine executable");
  fclose(f);
  require(SHA256(data, (size_t)n, digest) != NULL, "hash pristine executable");
  for (size_t i = 0; i < SHA256_DIGEST_LENGTH; i++)
    sprintf(hex + i * 2, "%02x", digest[i]);
  hex[sizeof hex - 1] = '\0';
  require(strcmp(hex, EXE_SHA256) == 0, "pristine executable hash");
  *size = (size_t)n;
  return data;
}
static uint32_t image_word(const uint8_t *image, size_t size, uint32_t pc) {
  size_t offset;
  require(pc >= EXE_LOAD_VA, "instruction below executable load address");
  offset = EXE_HEADER_SIZE + (size_t)(pc - EXE_LOAD_VA);
  require(offset + 4 <= size, "instruction outside executable image");
  return (uint32_t)image[offset] | ((uint32_t)image[offset + 1] << 8) |
         ((uint32_t)image[offset + 2] << 16) | ((uint32_t)image[offset + 3] << 24);
}
static unsigned pin_image(const uint8_t *image, size_t size,
                          const Insn *pins, size_t count) {
  for (size_t i = 0; i < count; i++) {
    uint32_t actual = image_word(image, size, pins[i].pc);
    if (actual != pins[i].word) {
      fprintf(stderr, "guard failed: image pin 0x%08" PRIx32
              " expected 0x%08" PRIx32 " got 0x%08" PRIx32 "\n",
              pins[i].pc, pins[i].word, actual);
      exit(2);
    }
  }
  return (unsigned)count;
}
static int32_t gravity_step(int32_t vy) {
  int32_t next = vy + 0x100;
  return next > 0x1000 ? 0x1000 : next;
}

int main(int argc, char **argv) {
  enum { ZERO=0, V0=2, V1=3, S0=16, S1=17, S2=18, S6=22, T0=8 };
  size_t image_size;
  uint8_t *image;
  unsigned image_pins = 0;
  require(argc <= 2, "usage: phase4_d02_actor20_semantic_guard [SCUS_942.88]");
  image = load_pristine(argc == 2 ? argv[1] : EXE_PATH, &image_size);
  const Insn a[] = {
    {0x8004bf14,0x8e020020},{0x8004bf1c,0x24420100},{0x8004bf20,0xae020020},
    {0x8004bf24,0x8e020020},{0x8004bf2c,0x28421001},{0x8004bf30,0x14400002},
    {0x8004bf34,0x24021000},{0x8004bf38,0xae020020},{0x8004bfa4,0x8e020008},
    {0x8004bfa8,0x8e030020},{0x8004bfac,0x08013032},{0x8004bfb0,0x00431021}
  };
  const Insn b[] = {
    {0x8004cf34,0x8e020020},{0x8004cf3c,0x24420100},{0x8004cf40,0xae020020},
    {0x8004cf44,0x28421001},{0x8004cf48,0x14400002},{0x8004cf4c,0x24021000},
    {0x8004cf50,0xae020020},{0x8004cf54,0x8e020020},{0x8004cf5c,0x02221021},
    {0x8004cf60,0x00409021},{0x8004cf6c,0xae120008}
  };
  const Insn settle[] = {
    {0x8004c02c,0x8e020020},{0x8004c034,0x04410002},{0x8004c03c,0x00021023},
    {0x8004c040,0x28420002},{0x8004c044,0x10400002},{0x8004c04c,0xae000020}
  };
  const Insn clear_delay[] = {
    {0x8004d024,0x2ac20003},{0x8004d028,0x14400005},{0x8004d02c,0xae000020}
  };
  const Insn impulse[] = {
    {0x80049e00,0x14600002},{0x80049e04,0x2402f300},
    {0x80049e08,0x2402f4a0},{0x80049e0c,0xad020020}
  };

  image_pins += pin_image(image, image_size, a, sizeof a / sizeof a[0]);
  image_pins += pin_image(image, image_size, b, sizeof b / sizeof b[0]);
  image_pins += pin_image(image, image_size, settle, sizeof settle / sizeof settle[0]);
  image_pins += pin_image(image, image_size, clear_delay,
                          sizeof clear_delay / sizeof clear_delay[0]);
  image_pins += pin_image(image, image_size, impulse,
                          sizeof impulse / sizeof impulse[0]);

  require(memop(a[0].word,0x23,V0,0x20,S0),"A loads +0x20");
  require(op(a[1].word)==0x09 && rt(a[1].word)==V0 && rs(a[1].word)==V0 && imm(a[1].word)==0x100,"A gravity +0x100");
  require(memop(a[2].word,0x2b,V0,0x20,S0),"A stores +0x20");
  require(op(a[4].word)==0x0a && imm(a[4].word)==0x1001,"A cap comparison 0x1001");
  require(op(a[5].word)==0x05 && branch_target(a[5].pc,a[5].word)==0x8004bf3c,"A cap branch");
  require(op(a[6].word)==0x09 && rs(a[6].word)==ZERO && rt(a[6].word)==V0 && imm(a[6].word)==0x1000,"A cap constant");
  require(memop(a[7].word,0x2b,V0,0x20,S0),"A cap store");
  require(memop(a[8].word,0x23,V0,0x08,S0) && memop(a[9].word,0x23,V1,0x20,S0),"A loads y and vy");
  require(op(a[10].word)==0x02 && a[11].pc==a[10].pc+4,"A add is jump delay slot");
  require(op(a[11].word)==0 && fn(a[11].word)==0x21 && rd(a[11].word)==V0 && rs(a[11].word)==V0 && rt(a[11].word)==V1,"A y += vy");

  require(memop(b[0].word,0x23,V0,0x20,S0),"B loads +0x20");
  require(op(b[1].word)==0x09 && imm(b[1].word)==0x100,"B gravity +0x100");
  require(memop(b[2].word,0x2b,V0,0x20,S0),"B stores +0x20");
  require(op(b[3].word)==0x0a && imm(b[3].word)==0x1001,"B cap comparison");
  require(op(b[4].word)==0x05 && op(b[5].word)==0x09 && imm(b[5].word)==0x1000,"B cap branch/constant");
  require(memop(b[6].word,0x2b,V0,0x20,S0),"B cap store");
  require(memop(b[7].word,0x23,V0,0x20,S0),"B reloads vy");
  require(op(b[8].word)==0 && fn(b[8].word)==0x21 && rd(b[8].word)==V0 && rs(b[8].word)==S1 && rt(b[8].word)==V0,"B computed_y += vy");
  require(op(b[9].word)==0 && fn(b[9].word)==0x21 && rd(b[9].word)==S2,"B preserves integrated y");
  require(memop(b[10].word,0x2b,S2,0x08,S0),"B stores integrated actor y");

  require(memop(settle[0].word,0x23,V0,0x20,S0),"settle loads vy");
  require(op(settle[1].word)==0x01 && rt(settle[1].word)==1,"settle bgez sign test");
  require(op(settle[2].word)==0 && fn(settle[2].word)==0x23 && rd(settle[2].word)==V0 && rs(settle[2].word)==ZERO && rt(settle[2].word)==V0,"settle absolute value");
  require(op(settle[3].word)==0x0a && imm(settle[3].word)==2,"settle abs(vy) < 2");
  require(op(settle[4].word)==0x04 && branch_target(settle[4].pc,settle[4].word)==0x8004c050,"settle skips clear when not small");
  require(memop(settle[5].word,0x2b,ZERO,0x20,S0),"settle zero store");

  require(op(clear_delay[0].word)==0x0a && rs(clear_delay[0].word)==S6 && imm(clear_delay[0].word)==3,"path result comparison");
  require(op(clear_delay[1].word)==0x05 && branch_target(clear_delay[1].pc,clear_delay[1].word)==0x8004d040,"path result branch");
  require(clear_delay[2].pc==clear_delay[1].pc+4 && memop(clear_delay[2].word,0x2b,ZERO,0x20,S0),"D02C is unconditional branch-delay clear once path reached");

  require(op(impulse[0].word)==0x05 && impulse[1].pc==impulse[0].pc+4,"impulse branch and delay slot");
  require(op(impulse[1].word)==0x09 && imm(impulse[1].word)==-3328,"upward impulse -0xD00");
  require(op(impulse[2].word)==0x09 && imm(impulse[2].word)==-2912,"alternate impulse -0xB60");
  require(memop(impulse[3].word,0x2b,V0,0x20,T0),"impulse stores actor +0x20");

  const SiteCount writers[] = {
    {0x80035e3c,1,"vector_y_transform"},{0x80035fdc,2,"vector_y_transform"},
    {0x80049d90,1,"record_init_zero"},{0x80049e0c,1,"airborne_impulse"},
    {0x8004bf20,19,"gravity_a"},{0x8004c04c,1,"settle_clear"},
    {0x8004cf40,402,"gravity_b"},{0x8004d02c,386,"path_clear_delay_slot"}
  };
  const unsigned readers[] = {1,1,2,2,6,6,19,154,14,14,14,135,6,402,402};
  unsigned wc=0,rc=0; for(size_t i=0;i<sizeof writers/sizeof writers[0];i++)wc+=writers[i].count;
  for(size_t i=0;i<sizeof readers/sizeof readers[0];i++)rc+=readers[i];
  require(wc==813,"all 813 traced writes classified");
  require(rc==1178,"all 1178 traced reads classified");

  const int32_t probes[] = {-3328,-2912,-1536,-256,0,256,3840,4096,4352};
  printf("{\n  \"format\":\"phase4_d02_actor20_semantic_guard_v1\",\n");
  printf("  \"pristine_exe_sha256\":\"%s\",\n", EXE_SHA256);
  printf("  \"image_instruction_pins\":%u,\n", image_pins);
  printf("  \"guards\":{\"gravity_a\":true,\"gravity_b\":true,\"y_integration_a\":true,\"y_integration_b\":true,\"settle_clear\":true,\"delay_slot_clear\":true,\"signed_impulses\":true},\n");
  printf("  \"writer_accounting\":{\"classified\":%u,\"trace_total\":813,\"unclassified\":0,\"sites\":[",wc);
  for(size_t i=0;i<sizeof writers/sizeof writers[0];i++)printf("%s{\"pc\":\"0x%08"PRIx32"\",\"count\":%u,\"kind\":\"%s\"}",i?",":"",writers[i].pc,writers[i].count,writers[i].kind);
  printf("]},\n  \"reader_accounting\":{\"classified\":%u,\"trace_total\":1178,\"unclassified\":0},\n",rc);
  printf("  \"gravity_truth_table\":[");
  for(size_t i=0;i<sizeof probes/sizeof probes[0];i++)printf("%s{\"before\":%"PRId32",\"after\":%"PRId32"}",i?",":"",probes[i],gravity_step(probes[i]));
  printf("],\n  \"delay_slot_correction\":\"0x8004D02C executes for either outcome of the branch at 0x8004D028 once this path is reached\",\n");
  printf("  \"alternative_hypotheses\":{\"padding\":\"rejected\",\"target_or_extent\":\"rejected\",\"frame_boundary_delta_y\":\"rejected\",\"signed_velocity_y\":\"confirmed\"},\n");
  printf("  \"residual_unknowns\":[\"exact world-unit/fixed-point scale\",\"per-species update cadence outside observed handlers\"],\n");
  printf("  \"closure\":\"field semantics exhausted; residuals do not change ownership or behavior name\"\n}\n");
  free(image);
  return 0;
}
