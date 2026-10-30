#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_EVENTS = 12000, REG_COUNT = 12, INITIAL_FRAME = 21677 };

typedef struct {
  unsigned watch_id;
  uint32_t pc;
  uint64_t frame;
  uint64_t cycle;
  uint32_t r[REG_COUNT];
} ExecEvent;

typedef struct {
  uint64_t frame;
  uint64_t cycle;
  uint32_t pc;
  uint32_t old_value;
  uint32_t new_value;
  unsigned width;
} CarryEvent;

static uint64_t parse_u64(const char *s) {
  char *end = NULL;
  errno = 0;
  uint64_t value = strtoull(s, &end, 0);
  if (errno || end == s)
    return 0;
  return value;
}

static int split_tabs(char *line, char **field, int max_fields) {
  int n = 0;
  char *p = line;
  while (n < max_fields) {
    field[n++] = p;
    char *tab = strchr(p, '\t');
    if (!tab)
      break;
    *tab = '\0';
    p = tab + 1;
  }
  if (n > 0)
    field[n - 1][strcspn(field[n - 1], "\r\n")] = '\0';
  return n;
}

static int64_t input_index(uint64_t emulator_frame) {
  return (int64_t)emulator_frame - INITIAL_FRAME - 1;
}

static size_t load_exec(const char *path, ExecEvent *events) {
  FILE *fp = fopen(path, "r");
  if (!fp) {
    perror(path);
    exit(2);
  }
  char line[2048];
  size_t count = 0;
  if (!fgets(line, sizeof(line), fp)) {
    fclose(fp);
    return 0;
  }
  while (fgets(line, sizeof(line), fp)) {
    char *f[16];
    if (split_tabs(line, f, 16) != 16)
      continue;
    if (count == MAX_EVENTS) {
      fprintf(stderr, "exec event capacity exceeded\n");
      exit(2);
    }
    ExecEvent *e = &events[count++];
    e->watch_id = (unsigned)parse_u64(f[0]);
    e->pc = (uint32_t)parse_u64(f[1]);
    e->frame = parse_u64(f[2]);
    e->cycle = parse_u64(f[3]);
    for (int i = 0; i < REG_COUNT; i++)
      e->r[i] = (uint32_t)parse_u64(f[i + 4]);
  }
  fclose(fp);
  return count;
}

static size_t load_carry(const char *path, CarryEvent *events) {
  FILE *fp = fopen(path, "r");
  if (!fp) {
    perror(path);
    exit(2);
  }
  char line[2048];
  size_t count = 0;
  if (!fgets(line, sizeof(line), fp)) {
    fclose(fp);
    return 0;
  }
  while (fgets(line, sizeof(line), fp)) {
    char *f[8];
    if (split_tabs(line, f, 8) != 8)
      continue;
    if (count == MAX_EVENTS) {
      fprintf(stderr, "carry event capacity exceeded\n");
      exit(2);
    }
    CarryEvent *e = &events[count++];
    e->frame = parse_u64(f[0]);
    e->cycle = parse_u64(f[1]);
    e->pc = (uint32_t)parse_u64(f[2]);
    e->old_value = (uint32_t)parse_u64(f[3]);
    e->new_value = (uint32_t)parse_u64(f[4]);
    e->width = (unsigned)parse_u64(f[5]);
  }
  fclose(fp);
  return count;
}

static size_t collect_watch(const ExecEvent *events, size_t count, unsigned watch_id,
                            const ExecEvent **out) {
  size_t n = 0;
  for (size_t i = 0; i < count; i++)
    if (events[i].watch_id == watch_id)
      out[n++] = &events[i];
  return n;
}

static bool paired_by_frame(const ExecEvent **a, size_t na, const ExecEvent **b, size_t nb) {
  if (na != nb)
    return false;
  for (size_t i = 0; i < na; i++)
    if (a[i]->frame != b[i]->frame)
      return false;
  return true;
}

static void print_segments(const ExecEvent **events, size_t count) {
  bool first = true;
  size_t start = 0;
  for (size_t i = 1; i <= count; i++) {
    bool boundary = (i == count) || (events[i]->frame > events[i - 1]->frame + 12);
    if (!boundary)
      continue;
    if (!first)
      printf(",");
    first = false;
    printf("{\"first_emulator_frame\":%" PRIu64
           ",\"last_emulator_frame\":%" PRIu64
           ",\"first_movie_input\":%" PRId64
           ",\"last_movie_input\":%" PRId64
           ",\"events\":%zu}",
           events[start]->frame, events[i - 1]->frame,
           input_index(events[start]->frame), input_index(events[i - 1]->frame),
           i - start);
    start = i;
  }
}

static const char *carry_kind(uint32_t pc) {
  switch (pc) {
    case 0x80047ce8u: return "manual_throw_release";
    case 0x80047858u: return "pickup";
    case 0x80046d04u: return "propeller_detach_helper";
    default: return "other";
  }
}

int main(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: %s exec_events.tsv carry_writes.tsv\n", argv[0]);
    return 2;
  }

  ExecEvent exec[MAX_EVENTS];
  CarryEvent carry[MAX_EVENTS];
  const size_t exec_count = load_exec(argv[1], exec);
  const size_t carry_count = load_carry(argv[2], carry);

  size_t watch_counts[10] = {0};
  for (size_t i = 0; i < exec_count; i++)
    if (exec[i].watch_id < 10)
      watch_counts[exec[i].watch_id]++;

  const ExecEvent *detach[MAX_EVENTS], *player_store[MAX_EVENTS], *clamp[MAX_EVENTS];
  const ExecEvent *actor_store[MAX_EVENTS], *actor_clear[MAX_EVENTS];
  size_t nd = collect_watch(exec, exec_count, 4, detach);
  size_t np = collect_watch(exec, exec_count, 5, player_store);
  size_t nc = collect_watch(exec, exec_count, 6, clamp);
  size_t nas = collect_watch(exec, exec_count, 8, actor_store);
  size_t nac = collect_watch(exec, exec_count, 9, actor_clear);

  bool detach_player_pair = paired_by_frame(detach, nd, player_store, np);
  bool actor_clear_pair = paired_by_frame(actor_store, nas, actor_clear, nac);
  if (actor_clear_pair) {
    for (size_t i = 0; i < nas; i++)
      if (actor_store[i]->r[6] != actor_clear[i]->r[6])
        actor_clear_pair = false;
  }

  bool clamp_exact = true;
  for (size_t i = 0; i < nc; i++)
    if ((int32_t)clamp[i]->r[4] != -3072)
      clamp_exact = false;

  bool player_radius_ptr = true;
  for (size_t i = 0; i < exec_count; i++)
    if (exec[i].watch_id == 3 && exec[i].r[1] != 0x800a6500u)
      player_radius_ptr = false;

  bool actor_radius_ptr = true;
  for (size_t i = 0; i < exec_count; i++)
    if (exec[i].watch_id == 7 && exec[i].r[1] != exec[i].r[6] + 4u)
      actor_radius_ptr = false;

  int32_t player_min = INT32_MAX, player_max = INT32_MIN;
  for (size_t i = 0; i < np; i++) {
    int32_t value = (int32_t)player_store[i]->r[0];
    if (value < player_min) player_min = value;
    if (value > player_max) player_max = value;
  }

  uint32_t actors[64];
  size_t actor_n = 0;
  for (size_t i = 0; i < nas; i++) {
    uint32_t actor = actor_store[i]->r[6];
    size_t j = 0;
    while (j < actor_n && actors[j] != actor) j++;
    if (j == actor_n)
      actors[actor_n++] = actor;
  }

  size_t manual_count = 0, pickup_count = 0, helper_count = 0;
  size_t changed_count = 0, ordinary_approach_writes = 0;
  for (size_t i = 0; i < carry_count; i++) {
    if (carry[i].pc == 0x80047ce8u) manual_count++;
    if (carry[i].pc == 0x80047858u) pickup_count++;
    if (carry[i].pc == 0x80046d04u) helper_count++;
    int64_t mi = input_index(carry[i].frame);
    if (mi >= 86 && mi <= 190) ordinary_approach_writes++;
    if (carry[i].old_value != carry[i].new_value) changed_count++;
  }

  printf("{\n");
  printf("  \"format\": \"phase4_b02_runtime_reduction_v1\",\n");
  printf("  \"anchor\": {\"initial_emulator_frame\": %d, "
         "\"phase_delay_frames\": 1, \"movie_frames\": 1123},\n", INITIAL_FRAME);
  printf("  \"event_counts\": {"
         "\"radius200\": %zu, \"player_radius40\": %zu, "
         "\"detach_call\": %zu, \"player_vy_store\": %zu, "
         "\"player_clamp_store\": %zu, \"actor_radius40\": %zu, "
         "\"actor_vy_store\": %zu, \"actor_flag_clear\": %zu, "
         "\"carry_writes\": %zu},\n",
         watch_counts[2], watch_counts[3], watch_counts[4], watch_counts[5],
         watch_counts[6], watch_counts[7], watch_counts[8], watch_counts[9],
         carry_count);
  printf("  \"invariants\": {"
         "\"detach_and_player_store_pair_by_frame\": %s, "
         "\"actor_store_and_clear_pair_by_frame_and_pointer\": %s, "
         "\"all_clamps_store_minus_3072\": %s, "
         "\"player_radius_pointer_is_0x800a6500\": %s, "
         "\"actor_radius_pointer_is_actor_plus_4\": %s, "
         "\"carry_writes_during_movie_inputs_86_through_190\": %zu},\n",
         detach_player_pair ? "true" : "false",
         actor_clear_pair ? "true" : "false",
         clamp_exact ? "true" : "false",
         player_radius_ptr ? "true" : "false",
         actor_radius_ptr ? "true" : "false",
         ordinary_approach_writes);
  printf("  \"carry_writer_counts\": {"
         "\"manual_throw_release_0x80047ce8\": %zu, "
         "\"pickup_0x80047858\": %zu, "
         "\"propeller_detach_helper_0x80046d04\": %zu, "
         "\"state_changing_writes\": %zu},\n",
         manual_count, pickup_count, helper_count, changed_count);
  printf("  \"carry_state_changes\": [");
  bool first = true;
  for (size_t i = 0; i < carry_count; i++) {
    if (carry[i].old_value == carry[i].new_value)
      continue;
    if (!first) printf(",");
    first = false;
    printf("{\"kind\":\"%s\",\"instruction_pc\":\"0x%08" PRIx32
           "\",\"emulator_frame\":%" PRIu64 ",\"movie_input\":%" PRId64
           ",\"cycle\":%" PRIu64 ",\"old\":%" PRIu32 ",\"new\":%" PRIu32 "}",
           carry_kind(carry[i].pc), carry[i].pc, carry[i].frame,
           input_index(carry[i].frame), carry[i].cycle,
           carry[i].old_value, carry[i].new_value);
  }
  printf("],\n");

  printf("  \"player_lift\": {\"events\":%zu,\"new_vy_min\":%" PRId32
         ",\"new_vy_max\":%" PRId32 ",\"clamp_events\":%zu,\"segments\":[",
         np, np ? player_min : 0, np ? player_max : 0, nc);
  print_segments(player_store, np);
  printf("]},\n");

  printf("  \"actor_lift\": {\"events\":%zu,\"actors\":[", nas);
  for (size_t a = 0; a < actor_n; a++) {
    const ExecEvent *group[MAX_EVENTS];
    size_t gn = 0;
    int32_t min_v = INT32_MAX, max_v = INT32_MIN;
    for (size_t i = 0; i < nas; i++) {
      if (actor_store[i]->r[6] != actors[a])
        continue;
      group[gn++] = actor_store[i];
      int32_t value = (int32_t)actor_store[i]->r[4];
      if (value < min_v) min_v = value;
      if (value > max_v) max_v = value;
    }
    if (a) printf(",");
    printf("{\"pointer\":\"0x%08" PRIx32 "\",\"actor_offset\":%" PRIu32
           ",\"events\":%zu,\"new_vy_min\":%" PRId32
           ",\"new_vy_max\":%" PRId32 ",\"segments\":[",
           actors[a], actors[a] - 0x8009fd80u, gn, min_v, max_v);
    print_segments(group, gn);
    printf("]}");
  }
  printf("]}\n");
  printf("}\n");
  return 0;
}
