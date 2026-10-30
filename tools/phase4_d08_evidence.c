/*
 * Phase 4 D08 retained/live evidence reducer.
 *
 * Inputs are normalized, transient TSV projections of the accepted capsule,
 * Phase-1 census, and the bounded post-movie trace.  Their hashes are pinned
 * below so this program cannot silently analyze a different projection.
 */

#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_SNAPSHOTS 32

struct snapshot {
  long frame;
  uint8_t bytes[132];
};

static const char *expected_hashes[] = {
    "9ab2269b3f2f3d6f8e95be681a97e610d639e33a8be66f12210ac3d9cadba7a9",
    "1aca727e15883a7af8b66e105e659f7d08c9a7202cd64f8e5b24601595c12f33",
    "5d59e8362cee7da356c682b16709fa672424025b833e01a233e19cfec29c641d",
    "5fb7e2c102021fdb5adfdebcd5a3f1ddc1bf1b32942e9e4e78f2d4add797da1e",
    "c8b576bd099d7b4a04732526731238da45a289afd69dd82d40615e5f64d7acfd",
};

static void fatal(const char *message) {
  fprintf(stderr, "phase4_d08_evidence: %s\n", message);
  exit(1);
}

static uint16_t le16(const uint8_t *p) {
  return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t le32(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int nibble(int c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

static void decode_hex(const char *text, uint8_t *out, size_t size) {
  for (size_t i = 0; i < size; i++) {
    int hi = nibble((unsigned char)text[i * 2]);
    int lo = nibble((unsigned char)text[i * 2 + 1]);
    if (hi < 0 || lo < 0)
      fatal("invalid snapshot hex");
    out[i] = (uint8_t)((hi << 4) | lo);
  }
  if (text[size * 2] != '\0' && text[size * 2] != '\n')
    fatal("snapshot has unexpected length");
}

static void hash_file(const char *path, char out[65]) {
  FILE *fp = fopen(path, "rb");
  if (!fp) fatal("cannot open input");
  SHA256_CTX ctx;
  unsigned char digest[SHA256_DIGEST_LENGTH];
  static const char digits[] = "0123456789abcdef";
  SHA256_Init(&ctx);
  uint8_t buffer[16384];
  size_t got;
  while ((got = fread(buffer, 1, sizeof(buffer), fp)) != 0)
    SHA256_Update(&ctx, buffer, got);
  if (ferror(fp)) fatal("cannot read input");
  fclose(fp);
  SHA256_Final(digest, &ctx);
  for (size_t i = 0; i < sizeof(digest); i++) {
    out[i * 2] = digits[digest[i] >> 4];
    out[i * 2 + 1] = digits[digest[i] & 15];
  }
  out[64] = '\0';
}

static struct snapshot *find_snapshot(struct snapshot *items, size_t count,
                                      long frame) {
  for (size_t i = 0; i < count; i++)
    if (items[i].frame == frame) return &items[i];
  fatal("required capsule frame is absent");
  return NULL;
}

static void require_state(struct snapshot *items, size_t count, long frame,
                          uint16_t reaction, uint16_t hp) {
  struct snapshot *s = find_snapshot(items, count, frame);
  if (le32(s->bytes) != 6 || le16(s->bytes + 0x6c) != reaction ||
      le16(s->bytes + 0x6e) != hp ||
      le32(s->bytes + 0x7c) != 0x8004a144)
    fatal("capsule state assertion failed");
}

static int hotspot_seen(const char *path, long wanted_frame,
                        const char *wanted_pc, unsigned wanted_count) {
  FILE *fp = fopen(path, "r");
  if (!fp) fatal("cannot open hotspot TSV");
  char line[256], pc[32];
  long frame;
  unsigned count;
  int found = 0;
  while (fgets(line, sizeof(line), fp)) {
    if (sscanf(line, "%ld\t%31s\t%u", &frame, pc, &count) == 3 &&
        frame == wanted_frame && !strcmp(pc, wanted_pc) &&
        count == wanted_count)
      found = 1;
  }
  fclose(fp);
  return found;
}

int main(int argc, char **argv) {
  if (argc != 6) {
    fprintf(stderr, "usage: %s snapshots.tsv hotspots.tsv census.tsv live_exec.tsv live_access.tsv\n", argv[0]);
    return 2;
  }

  for (int i = 0; i < 5; i++) {
    char hash[65];
    hash_file(argv[i + 1], hash);
    if (strcmp(hash, expected_hashes[i]) != 0)
      fatal("normalized evidence hash mismatch");
  }

  FILE *fp = fopen(argv[1], "r");
  if (!fp) fatal("cannot open capsule snapshots");
  struct snapshot snapshots[MAX_SNAPSHOTS];
  size_t snapshot_count = 0;
  char line[1024], hex[300];
  while (fgets(line, sizeof(line), fp)) {
    if (snapshot_count == MAX_SNAPSHOTS)
      fatal("too many snapshots");
    if (sscanf(line, "%ld\t%299s", &snapshots[snapshot_count].frame, hex) != 2)
      fatal("malformed snapshot TSV");
    decode_hex(hex, snapshots[snapshot_count].bytes,
               sizeof(snapshots[snapshot_count].bytes));
    snapshot_count++;
  }
  fclose(fp);
  if (snapshot_count != 10) fatal("unexpected snapshot count");

  require_state(snapshots, snapshot_count, 0, 0, 8);
  require_state(snapshots, snapshot_count, 190, 15, 8);
  require_state(snapshots, snapshot_count, 218, 1, 8);
  require_state(snapshots, snapshot_count, 220, 1, 8);
  require_state(snapshots, snapshot_count, 400, 1, 8);
  require_state(snapshots, snapshot_count, 426, 20, 6);
  require_state(snapshots, snapshot_count, 472, 20, 4);
  require_state(snapshots, snapshot_count, 500, 6, 4);
  require_state(snapshots, snapshot_count, 510, 1, 4);
  require_state(snapshots, snapshot_count, 554, 0, 4);
  if (le32(find_snapshot(snapshots, snapshot_count, 0)->bytes + 0x70) !=
          0x800776e4)
    fatal("target is not parked in Horsefly wander program");

  if (!hotspot_seen(argv[2], 190, "0x8004b650", 1) ||
      !hotspot_seen(argv[2], 426, "0x800590e4", 1) ||
      !hotspot_seen(argv[2], 472, "0x800590e4", 1))
    fatal("required capsule hotspot missing");

  fp = fopen(argv[3], "r");
  if (!fp) fatal("cannot open census TSV");
  unsigned riverbed = 0, entrance = 0, square = 0, total = 0;
  char stage[64], addr[32], p4c[32], p50[32], p70[32], p74[32], p7c[32], p80[32];
  int index;
  while (fgets(line, sizeof(line), fp)) {
    if (sscanf(line, "%63[^\t]\t%d\t%31s\t%31s\t%31s\t%31s\t%31s\t%31s\t%31s",
               stage, &index, addr, p4c, p50, p70, p74, p7c, p80) != 9)
      fatal("malformed census TSV");
    (void)index; (void)addr; (void)p4c; (void)p80;
    if (strcmp(p50, "0x80000000") || strcmp(p7c, "0x8004a144"))
      fatal("Horsefly census callback/profile diverges");
    if (strcmp(p70, "0x800776d0") && strcmp(p70, "0x800776e4"))
      fatal("Horsefly census mover program diverges");
    if (!strcmp(stage, "stage05_riverbed_run")) {
      riverbed++;
      if (strcmp(p74, "0x80137b4c")) fatal("Riverbed pose pointer diverges");
    } else if (!strcmp(stage, "stage07_city_entrance")) {
      entrance++;
      if (strcmp(p74, "0x8010f798")) fatal("City Entrance pose pointer diverges");
    } else if (!strcmp(stage, "stage08_city_square")) {
      square++;
      if (strcmp(p74, "0x800cf480")) fatal("City Square pose pointer diverges");
    } else {
      fatal("unexpected Horsefly stage in census");
    }
    total++;
  }
  fclose(fp);
  if (total != 22 || riverbed != 4 || entrance != 9 || square != 9)
    fatal("Horsefly campaign census count differs");

  fp = fopen(argv[4], "r");
  if (!fp) fatal("cannot open live exec TSV");
  unsigned exec_events = 0, hp_store_hits = 0, death_hits = 0;
  int lethal_hp = 0, sentinel = 0, stop_redirect = 0, class_one = 1;
  char pc[32], s2[32], v0[32], v1[32], s1[32], s7[32];
  long frame;
  while (fgets(line, sizeof(line), fp)) {
    if (sscanf(line, "%ld\t%31s\t%31s\t%31s\t%31s\t%31s\t%31s",
               &frame, pc, s2, v0, v1, s1, s7) != 7)
      fatal("malformed live exec TSV");
    (void)v1; (void)s1;
    if (strcmp(s2, "0x800a032c")) fatal("trace escaped target actor");
    exec_events++;
    if (!strcmp(pc, "0x800590e4")) {
      hp_store_hits++;
      if (frame == 117886 && !strcmp(v0, "0x00000000")) lethal_hp = 1;
    }
    if (!strcmp(pc, "0x800592a8") && frame == 117886 &&
        !strcmp(v0, "0x000003e7")) sentinel = 1;
    if (!strcmp(pc, "0x800592c8") && frame == 117886 &&
        !strcmp(v0, "0x800776ac")) stop_redirect = 1;
    if (!strcmp(pc, "0x800592a8") || !strcmp(pc, "0x800592ac") ||
        !strcmp(pc, "0x800592b0") || !strcmp(pc, "0x800592b4") ||
        !strcmp(pc, "0x800592b8") || !strcmp(pc, "0x800592c8")) {
      death_hits++;
      if (strcmp(s7, "0x00000001")) class_one = 0;
    }
  }
  fclose(fp);
  if (exec_events != 10 || hp_store_hits != 2 || death_hits != 6 ||
      !lethal_hp || !sentinel || !stop_redirect || !class_one)
    fatal("live death trace assertion failed");

  fp = fopen(argv[5], "r");
  if (!fp) fatal("cannot open live access TSV");
  int hp_two = 0, hp_zero = 0, hp_999 = 0, vm_stop = 0;
  unsigned counter_writes = 0;
  char address[32], writer[32], new_value[32];
  while (fgets(line, sizeof(line), fp)) {
    if (sscanf(line, "%ld\t%31s\t%31s\t%31s",
               &frame, address, writer, new_value) != 4)
      fatal("malformed live access TSV");
    if (!strcmp(address, "0x800a658e")) counter_writes++;
    if (frame == 117706 && !strcmp(address, "0x800a039a") &&
        !strcmp(writer, "0x800590e4") && !strcmp(new_value, "0x00000002")) hp_two = 1;
    if (frame == 117886 && !strcmp(address, "0x800a039a") &&
        !strcmp(writer, "0x800590e4") && !strcmp(new_value, "0x00000000")) hp_zero = 1;
    if (frame == 117886 && !strcmp(address, "0x800a039a") &&
        !strcmp(writer, "0x800592a8") && !strcmp(new_value, "0x000003e7")) hp_999 = 1;
    if (frame == 117886 && !strcmp(address, "0x800a039c") &&
        !strcmp(writer, "0x800592c8") && !strcmp(new_value, "0x800776ac")) vm_stop = 1;
  }
  fclose(fp);
  if (!hp_two || !hp_zero || !hp_999 || !vm_stop || counter_writes != 0)
    fatal("live access trace assertion failed");

  printf("{\n");
  printf("  \"schema\": \"abl-phase4-d08-evidence-v1\",\n");
  printf("  \"row\": \"D08_flies\",\n");
  printf("  \"status\": \"substantiated_partial_bounded_exhausted\",\n");
  printf("  \"normalized_input_sha256\": {\"capsule_snapshots\": \"%s\", "
         "\"capsule_hotspots\": \"%s\", \"census\": \"%s\", "
         "\"live_exec\": \"%s\", \"live_access\": \"%s\"},\n",
         expected_hashes[0], expected_hashes[1], expected_hashes[2],
         expected_hashes[3], expected_hashes[4]);
  printf("  \"capsule\": {\"frames_checked\": %zu, "
         "\"contact_frame\": 190, \"berry_hit_frames\": [426, 472], "
         "\"hp_path\": [8, 6, 4], \"contact_reaction\": 15, "
         "\"berry_reaction\": 20, \"hotspot_checks\": 3},\n",
         snapshot_count);
  printf("  \"campaign_census\": {\"total\": %u, "
         "\"stage05_riverbed_run\": %u, \"stage07_city_entrance\": %u, "
         "\"stage08_city_square\": %u, "
         "\"behavioral_program_divergence\": false, "
         "\"callback_divergence\": false, \"pose_pointer_varies_by_level\": true},\n",
         total, riverbed, entrance, square);
  printf("  \"live_continuation\": {\"target\": \"0x800a032c\", "
         "\"hp_path\": [4, 2, 0, 999], \"lethal_frame\": 117886, "
         "\"stop_program\": \"0x800776ac\", \"death_class\": 1, "
         "\"exact_exec_events\": %u, \"exec_truncated\": false, "
         "\"access_truncated\": false, \"enemy_counter_writes\": %u},\n",
         exec_events, counter_writes);
  printf("  \"conclusion\": \"Horsefly id 6 is a wander/contact enemy with shared berry damage and class-one temporary-KO lifecycle; the three named levels differ in pose data, not family mechanics\",\n");
  printf("  \"bounded_residuals\": [\"per-berry visual presentation\", "
         "\"gold-kill effect presentation\", \"per-instance respawn timing\", "
         "\"animation and audio identity\"]\n");
  printf("}\n");
  return 0;
}
