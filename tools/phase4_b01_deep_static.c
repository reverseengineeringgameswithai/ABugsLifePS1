#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t le32(const unsigned char *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint32_t word_at(const unsigned char *exe, size_t size, uint32_t address) {
  const uint32_t load = 0x80010000u;
  size_t off = 0x800u + (size_t)(address - load);
  if (address < load || off + 4 > size) {
    fprintf(stderr, "address out of range: 0x%08x\n", address);
    exit(1);
  }
  return le32(exe + off);
}

static int is_conditional(uint32_t w) {
  uint32_t op = w >> 26;
  return op == 1 || op == 4 || op == 5 || op == 6 || op == 7;
}

static int is_load(uint32_t w) {
  uint32_t op = w >> 26;
  return op == 0x20 || op == 0x21 || op == 0x22 || op == 0x23 ||
         op == 0x24 || op == 0x25 || op == 0x26 || op == 0x30;
}

static int is_store(uint32_t w) {
  uint32_t op = w >> 26;
  return op == 0x28 || op == 0x29 || op == 0x2a || op == 0x2b ||
         op == 0x2e || op == 0x38;
}

static uint32_t branch_target(uint32_t pc, uint32_t w) {
  return pc + 4u + (uint32_t)((int32_t)(int16_t)w * 4);
}

static unsigned char *read_all(const char *path, size_t *size_out) {
  FILE *f = fopen(path, "rb");
  if (!f || fseek(f, 0, SEEK_END) != 0) exit(2);
  long end = ftell(f);
  if (end < 0 || fseek(f, 0, SEEK_SET) != 0) exit(2);
  size_t size = (size_t)end;
  unsigned char *data = malloc(size ? size : 1);
  if (!data || fread(data, 1, size, f) != size) exit(2);
  fclose(f);
  *size_out = size;
  return data;
}

static int extract_int(const char *line, const char *key, int *value) {
  const char *p = strstr(line, key);
  if (!p) return 0;
  p = strchr(p, ':');
  return p && sscanf(p + 1, "%d", value) == 1;
}

int main(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: %s SCUS_942.88 phase4_b01_capsule.json\n", argv[0]);
    return 2;
  }
  size_t exe_size = 0;
  unsigned char *exe = read_all(argv[1], &exe_size);
  if (exe_size < 0x800 || memcmp(exe, "PS-X EXE", 8) != 0) return 3;

  int conditional_before_sequence = 0;
  int vy_loads = 0, vy_stores = 0, eligibility_stores = 0, xyz_stores = 0;
  int state_reads = 0, state_writes = 0;
  int tail_vy_loads = 0, tail_vy_stores = 0;
  uint32_t tail_return = 0;
  for (uint32_t pc = 0x8005c5a8u; pc < 0x8005c628u; pc += 4) {
    uint32_t w = word_at(exe, exe_size, pc);
    if (is_conditional(w)) ++conditional_before_sequence;
  }
  for (uint32_t pc = 0x8005c548u; pc <= 0x8005c6ecu; pc += 4) {
    uint32_t w = word_at(exe, exe_size, pc);
    uint32_t rs = (w >> 21) & 31u;
    int16_t imm = (int16_t)w;
    if (is_load(w) && rs == 1 && (uint16_t)imm == 0x6530) ++vy_loads;
    if (is_store(w) && rs == 1 && (uint16_t)imm == 0x6530) ++vy_stores;
    if (is_store(w) && rs == 18 && (uint16_t)imm == 0x002e) ++eligibility_stores;
    if (is_store(w) && rs == 18 && (imm == 8 || imm == 12 || imm == 16)) ++xyz_stores;
    if (is_load(w) && rs == 1 && (uint16_t)imm >= 0x6530 && (uint16_t)imm <= 0x6588)
      ++state_reads;
    if (is_store(w) && rs == 1 && (uint16_t)imm >= 0x6530 && (uint16_t)imm <= 0x6588)
      ++state_writes;
  }
  for (uint32_t pc = 0x8005cce0u; pc <= 0x8005d200u; pc += 4) {
    uint32_t w = word_at(exe, exe_size, pc);
    uint32_t rs = (w >> 21) & 31u;
    int16_t imm = (int16_t)w;
    if (is_load(w) && rs == 1 && (uint16_t)imm == 0x6530) ++tail_vy_loads;
    if (is_store(w) && rs == 1 && (uint16_t)imm == 0x6530) ++tail_vy_stores;
    if (w == 0x03e00008u) {
      tail_return = pc;
      break;
    }
  }

  const uint32_t duplicate_target = branch_target(0x8005c63c,
                                                   word_at(exe, exe_size, 0x8005c63c));
  const uint32_t append_target = branch_target(0x8005c67c,
                                                word_at(exe, exe_size, 0x8005c67c));
  const uint32_t incomplete_target = branch_target(0x8005c6ac,
                                                    word_at(exe, exe_size, 0x8005c6ac));
  int anchors_ok =
      word_at(exe, exe_size, 0x8005c5f4) == 0x2402f300 &&
      word_at(exe, exe_size, 0x8005c5fc) == 0xac226530 &&
      word_at(exe, exe_size, 0x8005c624) == 0xa4226588 &&
      word_at(exe, exe_size, 0x8005c6d4) == 0x2402c000 &&
      word_at(exe, exe_size, 0x8005c6dc) == 0xac226530;
  if (!anchors_ok || conditional_before_sequence != 0 || vy_loads != 0 ||
      vy_stores != 2 || eligibility_stores != 0 || xyz_stores != 0 ||
      duplicate_target != 0x8005c548u || append_target != 0x8005c694u ||
      incomplete_target != 0x8005c6e8u || tail_return == 0 ||
      tail_vy_loads != 0 || tail_vy_stores != 0) {
    fprintf(stderr, "static invariant failure\n");
    return 4;
  }

  FILE *json = fopen(argv[2], "r");
  if (!json) return 5;
  int movie = -1, hits = 0, vy_before = 0, vy_after = 0, mode_after = 0;
  int contact = -1, timer = -1, action = -1;
  int bounce_movie[8], bounce_slot[8], bounce_in[8], bounce_hits[8];
  int recovery_movie[8], recovery_slot[8], recoveries = 0, bounces = 0;
  char line[512];
  while (fgets(line, sizeof(line), json)) {
    int value = 0;
    if (extract_int(line, "\"movie\"", &value)) {
      movie = value;
      hits = 0;
      vy_before = 0;
      vy_after = 0;
      mode_after = 0;
      contact = timer = action = -1;
    }
    if (extract_int(line, "\"handler_hits\"", &value)) hits = value;
    if (extract_int(line, "\"vy_before\"", &value)) vy_before = value;
    if (extract_int(line, "\"vy_after\"", &value)) vy_after = value;
    if (extract_int(line, "\"mode_after\"", &value)) mode_after = value;
    if (extract_int(line, "\"contact\"", &value)) contact = value;
    if (extract_int(line, "\"timer84\"", &value)) timer = value;
    if (extract_int(line, "\"action88\"", &value)) action = value;
    if (extract_int(line, "\"nearest_mushroom_slot\"", &value)) {
      if (vy_after == -3328 && bounces < 8) {
        bounce_movie[bounces] = movie;
        bounce_slot[bounces] = value;
        bounce_in[bounces] = vy_before;
        bounce_hits[bounces] = hits;
        if (mode_after != 5 || contact != 0 || timer != 0 || action != 3) return 6;
        ++bounces;
      } else if (vy_before == -3328 && vy_after == -3072 && mode_after == 6 && recoveries < 8) {
        recovery_movie[recoveries] = movie;
        recovery_slot[recoveries] = value;
        ++recoveries;
      }
    }
  }
  fclose(json);
  if (bounces != 4 || recoveries != 4) {
    fprintf(stderr, "event parser counts: bounces=%d recoveries=%d\n", bounces, recoveries);
    return 7;
  }
  int unique = 0, recovery_pairs = 0, positive_impacts = 0, deep_hits = 1;
  for (int i = 0; i < bounces; ++i) {
    int first = 1;
    for (int j = 0; j < i; ++j) if (bounce_slot[j] == bounce_slot[i]) first = 0;
    unique += first;
    positive_impacts += bounce_in[i] > 0;
    deep_hits &= bounce_hits[i] >= 21;
    for (int j = 0; j < recoveries; ++j) {
      if (recovery_slot[j] == bounce_slot[i] && recovery_movie[j] == bounce_movie[i] + 2)
        ++recovery_pairs;
    }
  }
  if (unique != 4 || positive_impacts != 4 || recovery_pairs != 4 || !deep_hits) return 8;

  printf("{\n");
  printf("  \"row\": \"B01_mushroom_trampoline\",\n");
  printf("  \"static_invariants\": {\"conditional_branches_between_eligibility_and_sequence\": %d, "
         "\"normal_stores_dominate_sequence\": true, \"player_vy_loads\": %d, "
         "\"player_vy_stores\": %d, \"eligibility_stores\": %d, "
         "\"plant_xyz_stores\": %d, \"player_state_reads\": %d, "
         "\"player_state_writes\": %d},\n",
         conditional_before_sequence, vy_loads, vy_stores, eligibility_stores,
         xyz_stores, state_reads, state_writes);
  printf("  \"branch_targets\": {\"duplicate_reset\": \"0x%08x\", "
         "\"append\": \"0x%08x\", \"incomplete_shared_tail\": \"0x%08x\"},\n",
         duplicate_target, append_target, incomplete_target);
  printf("  \"shared_effect_tail\": {\"entry\": \"0x8005cce0\", "
         "\"return\": \"0x%08x\", \"player_vy_loads\": %d, "
         "\"player_vy_stores\": %d, \"completion_override_survives_return\": true},\n",
         tail_return, tail_vy_loads, tail_vy_stores);
  printf("  \"capsule_invariants\": {\"bounces\": %d, \"unique_slots\": %d, "
         "\"positive_incoming_velocity\": %d, \"deep_handler_hits_each\": true, "
         "\"two_frame_recovery_pairs\": %d, \"two_frame_velocity\": -3072, "
         "\"mode_after_two_frames\": 6, \"implied_velocity_increment_per_frame\": 128},\n",
         bounces, unique, positive_impacts, recovery_pairs);
  printf("  \"contact_frames\": [%d, %d, %d, %d],\n",
         bounce_movie[0], bounce_movie[1], bounce_movie[2], bounce_movie[3]);
  printf("  \"contact_intervals\": [%d, %d, %d],\n",
         bounce_movie[1] - bounce_movie[0], bounce_movie[2] - bounce_movie[1],
         bounce_movie[3] - bounce_movie[2]);
  printf("  \"conclusion\": \"no hidden coefficient, one-shot eligibility clear, or plant-position mutation exists in the trampoline/reset region; all retained contacts share the same launch and two-frame recovery\"\n");
  printf("}\n");
  free(exe);
  return 0;
}
