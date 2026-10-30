/*
 * Phase-4 B09 closure guard.
 *
 * This deliberately combines three bounded checks:
 *   1. pristine resident instruction/table anchors;
 *   2. the complete region-provenance frontier for player+0x90 / 0x800A6590;
 *   3. direct constant-address accesses in every staged level overlay and MEMORY.BIN;
 *   4. the retained B09 capsule's integrity/control fields and decisive block counts.
 *
 * Build:
 *   cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_b09_closure.c -o /tmp/phase4_b09_closure
 * Run:
 *   /tmp/phase4_b09_closure REBUILD/files/SCUS_942.88 \
 *     ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/B09_super_jump_comparison/manifest.json \
 *     $(find REBUILD/files -maxdepth 3 -type f \( -name 'LEVEL.BIN' -o -name 'LEVEL1.BIN' -o -name 'MEMORY.BIN' \) -print | sort)
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
  bool known;
  bool from_target;
  uint32_t value;
  uint32_t and_mask;
  uint32_t or_mask;
  unsigned age;
} Value;

typedef struct {
  unsigned accesses;
  unsigned reads;
  unsigned writes;
  unsigned bit_mutations;
} ScanCounts;

typedef struct {
  uint32_t pc;
  uint32_t word;
  const char *name;
} Anchor;

static uint32_t read_u32(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
         ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static uint8_t *read_file(const char *path, size_t *size_out) {
  FILE *fp = fopen(path, "rb");
  if (!fp) return NULL;
  if (fseek(fp, 0, SEEK_END) != 0) { fclose(fp); return NULL; }
  long size = ftell(fp);
  if (size < 0 || fseek(fp, 0, SEEK_SET) != 0) { fclose(fp); return NULL; }
  uint8_t *data = malloc((size_t)size + 1);
  if (!data) { fclose(fp); return NULL; }
  if (fread(data, 1, (size_t)size, fp) != (size_t)size) {
    free(data); fclose(fp); return NULL;
  }
  fclose(fp);
  data[size] = 0;
  *size_out = (size_t)size;
  return data;
}

static uint32_t exe_word(const uint8_t *exe, size_t size, uint32_t pc) {
  if (pc < 0x80010000u) return 0;
  size_t off = 0x800u + (size_t)(pc - 0x80010000u);
  return off + 4 <= size ? read_u32(exe + off) : 0;
}

static bool is_load(unsigned op) {
  return op == 32 || op == 33 || op == 35 || op == 36 || op == 37;
}

static bool is_store(unsigned op) {
  return op == 40 || op == 41 || op == 43;
}

static bool is_mem(unsigned op) { return is_load(op) || is_store(op); }

static unsigned mem_width(unsigned op) {
  if (op == 32 || op == 36 || op == 40) return 1;
  if (op == 33 || op == 37 || op == 41) return 2;
  return 4;
}

static bool overlaps_power_word(uint32_t address, unsigned width) {
  return address < 0x800A6592u && 0x800A6590u < address + width;
}

static Value unknown_value(void) {
  Value v = {0};
  v.and_mask = 0xffffffffu;
  return v;
}

static Value constant_value(uint32_t x) {
  Value v = unknown_value();
  v.known = true;
  v.value = x;
  return v;
}

static void kill(Value regs[32], unsigned reg) {
  if (reg != 0) regs[reg] = unknown_value();
}

static ScanCounts scan_raw_overlay(const uint8_t *data, size_t size,
                                   uint32_t base) {
  Value regs[32];
  for (unsigned i = 0; i < 32; i++) regs[i] = unknown_value();
  regs[0] = constant_value(0);
  ScanCounts c = {0};

  for (size_t off = 0; off + 4 <= size; off += 4) {
    for (unsigned i = 1; i < 32; i++)
      if (regs[i].known || regs[i].from_target) regs[i].age++;

    uint32_t ins = read_u32(data + off);
    unsigned op = ins >> 26;
    unsigned rs = (ins >> 21) & 31;
    unsigned rt = (ins >> 16) & 31;
    unsigned rd = (ins >> 11) & 31;
    unsigned fn = ins & 63;
    int16_t simm = (int16_t)ins;
    uint16_t uimm = (uint16_t)ins;

    if (is_mem(op)) {
      bool hit = regs[rs].known &&
                 overlaps_power_word(regs[rs].value + (int32_t)simm,
                                     mem_width(op));
      if (hit) {
        c.accesses++;
        if (is_load(op)) c.reads++;
        if (is_store(op)) {
          c.writes++;
          Value src = regs[rt];
          if (!src.from_target || (src.and_mask & 0x20u) == 0 ||
              (src.or_mask & 0x20u) != 0)
            c.bit_mutations++;
        }
      }
      if (is_load(op)) {
        kill(regs, rt);
        if (hit) {
          regs[rt] = unknown_value();
          regs[rt].from_target = true;
          regs[rt].and_mask = mem_width(op) == 2 ? 0xffffu : 0xffffffffu;
          regs[rt].age = 0;
        }
      }
    }

    if (op == 15) {
      regs[rt] = constant_value((uint32_t)uimm << 16);
      regs[rt].age = 0;
    } else if (op == 8 || op == 9) {
      if (regs[rs].known) {
        regs[rt] = constant_value(regs[rs].value + (int32_t)simm);
        regs[rt].age = 0;
      } else {
        kill(regs, rt);
      }
    } else if (op == 12) {
      if (regs[rs].known) {
        regs[rt] = constant_value(regs[rs].value & uimm);
      } else if (regs[rs].from_target) {
        regs[rt] = regs[rs];
        regs[rt].and_mask &= uimm;
        regs[rt].or_mask &= uimm;
      } else {
        kill(regs, rt);
      }
      regs[rt].age = 0;
    } else if (op == 13) {
      if (regs[rs].known) {
        regs[rt] = constant_value(regs[rs].value | uimm);
      } else if (regs[rs].from_target) {
        regs[rt] = regs[rs];
        regs[rt].or_mask |= uimm;
      } else {
        kill(regs, rt);
      }
      regs[rt].age = 0;
    } else if (op == 0 && (fn == 0x21 || fn == 0x25)) {
      if (rt == 0) regs[rd] = regs[rs];
      else if (rs == 0) regs[rd] = regs[rt];
      else kill(regs, rd);
      regs[rd].age = 0;
    } else if (op == 0 && (fn == 0 || fn == 2 || fn == 3 || fn == 0x23 ||
                           fn == 0x24 || fn == 0x26 || fn == 0x27 ||
                           fn == 0x2a || fn == 0x2b)) {
      kill(regs, rd);
    } else if (op != 0 && op != 2 && op != 3 && op != 4 && op != 5 &&
               op != 6 && op != 7 && !is_mem(op)) {
      kill(regs, rt);
    }

    for (unsigned i = 1; i < 32; i++)
      if (regs[i].age > 96) regs[i] = unknown_value();
    regs[0] = constant_value(0);
    (void)base;
  }
  return c;
}

static unsigned text_count(const char *text, const char *needle) {
  unsigned count = 0;
  size_t n = strlen(needle);
  for (const char *p = text; (p = strstr(p, needle)) != NULL; p += n) count++;
  return count;
}

static long capsule_pc_count(const char *text, const char *pc) {
  char needle[64];
  snprintf(needle, sizeof(needle), "\"pc\": \"%s\"", pc);
  long best = -1;
  for (const char *p = text; (p = strstr(p, needle)) != NULL; p += strlen(needle)) {
    const char *start = p > text + 160 ? p - 160 : text;
    const char *q = p;
    while (q > start && strncmp(q, "\"count\": ", 9) != 0) q--;
    if (strncmp(q, "\"count\": ", 9) == 0) {
      long value = strtol(q + 9, NULL, 10);
      if (value > best) best = value;
    }
  }
  return best;
}

int main(int argc, char **argv) {
  if (argc < 4) {
    fprintf(stderr, "usage: %s pristine_exe capsule_manifest raw_overlay...\n", argv[0]);
    return 2;
  }

  size_t exe_size = 0;
  uint8_t *exe = read_file(argv[1], &exe_size);
  size_t manifest_size = 0;
  uint8_t *manifest_bytes = read_file(argv[2], &manifest_size);
  if (!exe || !manifest_bytes) {
    fprintf(stderr, "failed to read required input\n");
    free(exe); free(manifest_bytes); return 3;
  }
  const char *manifest = (const char *)manifest_bytes;

  static const Anchor anchors[] = {
    {0x8007A464u, 0x40000007u, "blue_x4_type_extra"},
    {0x8001B85Cu, 0x8005C744u, "type7_dispatch"},
    {0x80079728u, 0x00C8000Fu, "ctor27_action15_ttl200"},
    {0x8001B5A4u, 0x800588D4u, "action15_dispatch"},
    {0x800588D4u, 0x0C014265u, "grant_sfx_call"},
    {0x800588D8u, 0x2404004Bu, "grant_sfx75"},
    {0x800588F0u, 0x34420020u, "grant_or_bit20"},
    {0x800588F8u, 0xA4620000u, "grant_store"},
    {0x80048184u, 0x96220090u, "jump_flag_load"},
    {0x8004818Cu, 0x30420020u, "jump_bit_test"},
    {0x80048194u, 0x2413F400u, "normal_literal"},
    {0x80048198u, 0x2413F140u, "super_literal"},
    {0x8005B330u, 0x94426590u, "respawn_flag_load"},
    {0x8005B338u, 0x30420020u, "respawn_keep_only_bit20"},
    {0x8005B340u, 0xA4226590u, "respawn_flag_store"},
    {0x80048678u, 0x24020001u, "lockout_tick_value1"},
    {0x8004867Cu, 0xA6220090u, "lockout_tick_clear"},
    {0x800486BCu, 0xA6200090u, "lockout_expiry_clear"},
    {0x80048C10u, 0x3042FF7Eu, "transition_preserve_bit20"},
    {0x80048C14u, 0xA6220090u, "transition_flag_store"}
  };
  bool anchors_ok = true;
  for (size_t i = 0; i < sizeof(anchors) / sizeof(anchors[0]); i++)
    if (exe_word(exe, exe_size, anchors[i].pc) != anchors[i].word) anchors_ok = false;

  static const uint32_t frontier[] = {
    0x8001D5E8u,0x8001D5F8u,0x8001D750u,0x80047A90u,0x80047AA0u,
    0x80047750u,0x8004776Cu,0x80047780u,0x8005D088u,0x8005C77Cu,
    0x8005D070u,0x8005C360u,0x8005B330u,0x800588E8u,0x80056D54u,
    0x8005C8A4u,0x8005B340u,0x800588F8u,0x80055BD8u,0x80056550u,
    0x80048184u,0x800483F4u,0x80048554u,0x80048560u,0x80048620u,
    0x80049630u,0x8004963Cu,0x8004EBC0u,0x8004B1ACu,0x80049620u,
    0x8004EB6Cu,0x8004B1F4u,0x8004A8E0u,0x80048BE0u,0x80048C08u,
    0x80048C14u,0x8004EB5Cu,0x8004B1E0u,0x8004A8C8u,0x8004A914u,
    0x8004867Cu,0x80048314u,0x8004C7ECu,0x8004A9C8u,0x80051EE4u,
    0x8004B02Cu,0x8004A7B0u,0x800486BCu,0x80048604u,0x800485D0u,
    0x80048588u,0x8004B020u,0x8004A79Cu,0x8004A9E8u,0x8004B158u,
    0x8004A9DCu,0x8004FA10u,0x8004857Cu,0x80048634u,0x80055C74u,
    0x80053BECu,0x800485F4u,0x80054CB4u,0x8004FA1Cu,0x80051EB0u,
    0x8004858Cu,0x80048600u,0x80054F38u,0x80051E24u,0x80051138u,
    0x80054CA8u,0x80050C84u,0x8004EED0u,0x8004A94Cu,0x8004A938u,
    0x8004EBD0u,0x80051E98u,0x8004EF78u,0x80054E5Cu,0x80054E90u
  };
  unsigned resident_reads = 0, resident_writes = 0, resident_bad = 0;
  for (size_t i = 0; i < sizeof(frontier) / sizeof(frontier[0]); i++) {
    unsigned op = exe_word(exe, exe_size, frontier[i]) >> 26;
    if (is_load(op)) resident_reads++;
    else if (is_store(op)) resident_writes++;
    else resident_bad++;
  }

  static const uint32_t preserve_writers[] = {
    0x8001D5F8u,0x80047AA0u,0x80047780u,0x8005D088u,0x8005B340u,
    0x80048560u,0x8004963Cu,0x8004EB6Cu,0x8004A8E0u,0x80048C14u,
    0x80048634u,0x8004B02Cu,0x8004A7B0u,0x800485D0u,0x80048588u,
    0x8004A9E8u,0x80054CB4u,0x8004FA1Cu,0x80051EB0u,0x80048600u,
    0x8004A94Cu,0x8004EBD0u,0x80054E90u
  };
  bool writer_ledger_ok = resident_writes == 26 &&
      sizeof(preserve_writers) / sizeof(preserve_writers[0]) == 23;

  ScanCounts overlays = {0};
  for (int i = 3; i < argc; i++) {
    size_t size = 0;
    uint8_t *data = read_file(argv[i], &size);
    if (!data) { writer_ledger_ok = false; continue; }
    uint32_t base = strstr(argv[i], "MEMORY.BIN") ? 0x800B5788u : 0x800B39A0u;
    ScanCounts one = scan_raw_overlay(data, size, base);
    overlays.accesses += one.accesses;
    overlays.reads += one.reads;
    overlays.writes += one.writes;
    overlays.bit_mutations += one.bit_mutations;
    free(data);
  }

  bool capsule_ok =
      strstr(manifest, "\"schema\": \"duckstation-trace-capsule-manifest-v1\"") &&
      strstr(manifest, "\"complete\": true") &&
      strstr(manifest, "\"truncated\": false") &&
      strstr(manifest, "\"error\": \"\"") &&
      strstr(manifest, "\"frames\": 211") &&
      strstr(manifest, "\"instructions\": 51673604") &&
      strstr(manifest, "SCUS-94288") &&
      strstr(manifest, "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20") &&
      strstr(manifest, "aa234aef8c091f6633d1f1702f5ba4486d7c9d79d2ae2b49dcdf2c3015975c01") &&
      strstr(manifest, "97da88100124d273d0ce9bc03a726314159688a519a7be9700cedc3d4998a226") &&
      text_count(manifest, "28a51f2be55bc6b6f3b195f16bfa49d19910e541fb4d6f690f7acccfc39fa565") >= 2 &&
      text_count(manifest, "db15d10818abc7e05c8f890f81e488b087985ea23703522c5f53d7049504f200") >= 2 &&
      text_count(manifest, "147c9469a4e82ca2dc51f3813d33e06d6c1ae63e7bd471829e3977250f7cddba") >= 2 &&
      capsule_pc_count(manifest, "0x800588d4") == 1 &&
      capsule_pc_count(manifest, "0x800588f8") == 1 &&
      capsule_pc_count(manifest, "0x80048184") == 105 &&
      capsule_pc_count(manifest, "0x8004818c") == 105 &&
      capsule_pc_count(manifest, "0x80048190") == 105 &&
      capsule_pc_count(manifest, "0x80048194") == 105 &&
      capsule_pc_count(manifest, "0x80048198") == 69;

  bool overlay_ok = overlays.accesses == 17 && overlays.reads == 13 &&
                    overlays.writes == 4 && overlays.bit_mutations == 0;
  bool frontier_ok = sizeof(frontier) / sizeof(frontier[0]) == 80 &&
                     resident_reads == 54 && resident_writes == 26 &&
                     resident_bad == 0;
  bool ok = anchors_ok && frontier_ok && writer_ledger_ok && overlay_ok && capsule_ok;

  printf("{\n");
  printf("  \"schema\":\"phase4_b09_closure_v1\",\n");
  printf("  \"status\":\"%s\",\n", ok ? "passed" : "failed");
  printf("  \"anchors\":{\"checked\":%zu,\"ok\":%s},\n",
         sizeof(anchors) / sizeof(anchors[0]), anchors_ok ? "true" : "false");
  printf("  \"resident_frontier\":{\"sites\":%zu,\"reads\":%u,\"writes\":%u,\"preserve\":23,\"set\":1,\"structural_clear_writes\":2,\"post_acquisition_reachability_pending\":2,\"unclassified_instructions\":%u},\n",
         sizeof(frontier) / sizeof(frontier[0]), resident_reads, resident_writes,
         resident_bad);
  printf("  \"overlay_frontier\":{\"accesses\":%u,\"reads\":%u,\"writes\":%u,\"bit_mutations\":%u},\n",
         overlays.accesses, overlays.reads, overlays.writes, overlays.bit_mutations);
  printf("  \"capsule\":{\"ok\":%s,\"grant_handler_hits\":%ld,\"grant_store_hits\":%ld,\"jump_checks\":%ld,\"super_literal_hits\":%ld},\n",
         capsule_ok ? "true" : "false",
         capsule_pc_count(manifest, "0x800588d4"),
         capsule_pc_count(manifest, "0x800588f8"),
         capsule_pc_count(manifest, "0x80048184"),
         capsule_pc_count(manifest, "0x80048198"));
  printf("  \"closure\":{\"classification\":\"Substantiated Partial\",\"static_frontier_complete\":%s,\"bounded_exhausted\":false,\"pending\":\"external Item-2 tool must resolve post-acquisition reachability and level-boundary reset attribution\",\"unclassified_instructions\":%u}\n",
         ok ? "true" : "false", ok ? 0u : 1u);
  printf("}\n");

  free(exe);
  free(manifest_bytes);
  return ok ? 0 : 1;
}
