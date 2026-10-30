#define _DEFAULT_SOURCE
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

enum { REG_N = 32, PATH_N = 4096, LINE_N = 1024, MAX_HITS = 4096 };

typedef struct {
  bool known;
  uint32_t value;
  bool has_base;
  uint32_t base;
  bool has_load;
  uint32_t load_addr;
  uint32_t and_mask;
  uint32_t or_mask;
} Val;

typedef struct {
  char path[PATH_N];
  uint32_t pc;
  char op[16];
  char text[LINE_N];
  uint32_t target;
  bool target_dynamic;
  uint32_t dynamic_base;
  bool source_known;
  uint32_t source_value;
  bool source_load;
  uint32_t source_load_addr;
  uint32_t source_and_mask;
  uint32_t source_or_mask;
} Hit;

static Hit hits[MAX_HITS];
static size_t hit_n;
static size_t file_n;
static size_t insn_n;

typedef struct {
  uint32_t pc;
  const char *role;
  bool found;
  bool word_read;
  uint32_t word;
  char path[PATH_N];
  char instruction[LINE_N];
} Anchor;

#define ANCHOR(addr, label) { (addr), (label), false, false, 0, {0}, {0} }

static Anchor anchors[] = {
  ANCHOR(0x80048654u, "positive_slot_tick"),
  ANCHOR(0x8004a90cu, "cross_clear_path_flags_base"),
  ANCHOR(0x8004a94cu, "cross_harvester_flag_clear"),
  ANCHOR(0x80051ea0u, "equip_state_set"),
  ANCHOR(0x80051eb0u, "equip_flag_set"),
  ANCHOR(0x80051f60u, "active_state_maintain"),
  ANCHOR(0x80053becu, "grain_harvester_flag_read"),
  ANCHOR(0x80053bf4u, "grain_harvester_bit_test"),
  ANCHOR(0x80053c20u, "grain_ctor_0x51_select"),
  ANCHOR(0x80053c40u, "grain_contact_alloc_call"),
  ANCHOR(0x80053c4cu, "grain_source_consumed_sentinel"),
  ANCHOR(0x80053c50u, "grain_target_minus_one_constant"),
  ANCHOR(0x80053c58u, "grain_target_player_minus_one"),
  ANCHOR(0x8005a350u, "contact_flags_load"),
  ANCHOR(0x8005a358u, "contact_homing_bit_test"),
  ANCHOR(0x8005a35cu, "contact_non_homing_branch"),
  ANCHOR(0x8005a370u, "contact_target_load"),
  ANCHOR(0x8005a378u, "contact_player_target_branch"),
  ANCHOR(0x8005a39cu, "contact_player_bearing_call"),
  ANCHOR(0x8005a4c8u, "contact_homing_y_write"),
  ANCHOR(0x8005a548u, "contact_motion_x_write"),
  ANCHOR(0x8005a56cu, "contact_motion_z_write"),
  ANCHOR(0x800589b8u, "grain_collection_handler_call"),
  ANCHOR(0x80054f80u, "grain_pickup_sfx_manager_call"),
  ANCHOR(0x80054f9cu, "grain_count_increment"),
  ANCHOR(0x8004b158u, "enemy_harvester_flag_read"),
  ANCHOR(0x8004b160u, "enemy_harvester_bit_test"),
  ANCHOR(0x8004b208u, "enemy_hp_998_write"),
};

static const char *reg_names[REG_N] = {
  "zero","at","v0","v1","a0","a1","a2","a3",
  "t0","t1","t2","t3","t4","t5","t6","t7",
  "s0","s1","s2","s3","s4","s5","s6","s7",
  "t8","t9","k0","k1","gp","sp","fp","ra"
};

static char *trim(char *s) {
  while (isspace((unsigned char)*s)) s++;
  char *end = s + strlen(s);
  while (end > s && isspace((unsigned char)end[-1])) *--end = 0;
  return s;
}

static void print_json_string(const char *s) {
  putchar('"');
  for (; *s; s++) {
    unsigned char c = (unsigned char)*s;
    if (c == '"' || c == '\\') printf("\\%c", c);
    else if (c == '\n') fputs("\\n", stdout);
    else if (c == '\r') fputs("\\r", stdout);
    else if (c == '\t') fputs("\\t", stdout);
    else if (c < 0x20) printf("\\u%04x", c);
    else putchar(c);
  }
  putchar('"');
}

static int reg_index(const char *s) {
  while (*s == '$' || isspace((unsigned char)*s)) s++;
  char name[16];
  size_t n = 0;
  while (*s && *s != ',' && *s != ')' && !isspace((unsigned char)*s) && n + 1 < sizeof(name))
    name[n++] = *s++;
  name[n] = 0;
  for (int i = 0; i < REG_N; i++)
    if (!strcmp(name, reg_names[i])) return i;
  if (!strcmp(name, "s8")) return 30;
  return -1;
}

static bool parse_i32(const char *s, int32_t *out) {
  while (isspace((unsigned char)*s)) s++;
  char *end = NULL;
  errno = 0;
  long long v = strtoll(s, &end, 0);
  if (errno || end == s) return false;
  *out = (int32_t)v;
  return true;
}

static int split_operands(char *s, char **out, int cap) {
  int n = 0;
  int depth = 0;
  char *start = s;
  for (char *p = s;; p++) {
    if (*p == '(') depth++;
    else if (*p == ')') depth--;
    bool at_end = (*p == 0);
    if ((*p == ',' && depth == 0) || at_end) {
      if (n < cap) {
        if (!at_end) *p = 0;
        out[n++] = trim(start);
      }
      if (at_end) break;
      start = p + 1;
    }
  }
  return n;
}

static bool parse_mem(char *s, int32_t *off, int *base) {
  char *lp = strchr(s, '(');
  char *rp = strchr(s, ')');
  if (!lp || !rp || rp < lp) return false;
  *lp = 0;
  *rp = 0;
  if (!parse_i32(trim(s), off)) return false;
  *base = reg_index(lp + 1);
  return *base >= 0;
}

static Val unknown_val(void) {
  Val v = {0};
  v.and_mask = 0xffffffffu;
  return v;
}

static Val const_val(uint32_t x) {
  Val v = unknown_val();
  v.known = true;
  v.value = x;
  return v;
}

static void add_hit(const char *path, uint32_t pc, const char *op, const char *text,
                    uint32_t target, bool dyn, uint32_t dyn_base, Val src) {
  if (hit_n == MAX_HITS) {
    fprintf(stderr, "hit capacity exceeded\n");
    exit(2);
  }
  Hit *h = &hits[hit_n++];
  snprintf(h->path, sizeof(h->path), "%s", path);
  h->pc = pc;
  snprintf(h->op, sizeof(h->op), "%s", op);
  snprintf(h->text, sizeof(h->text), "%s", text);
  h->target = target;
  h->target_dynamic = dyn;
  h->dynamic_base = dyn_base;
  h->source_known = src.known;
  h->source_value = src.value;
  h->source_load = src.has_load;
  h->source_load_addr = src.load_addr;
  h->source_and_mask = src.and_mask;
  h->source_or_mask = src.or_mask;
}

static void capture_anchor(const char *path, uint32_t pc, const char *instruction) {
  for (size_t i = 0; i < sizeof(anchors) / sizeof(anchors[0]); i++) {
    if (anchors[i].pc == pc && !anchors[i].found) {
      anchors[i].found = true;
      snprintf(anchors[i].path, sizeof(anchors[i].path), "%s", path);
      snprintf(anchors[i].instruction, sizeof(anchors[i].instruction), "%s", trim((char *)instruction));
    }
  }
}

static bool overlaps(uint32_t addr, unsigned width, uint32_t target, unsigned target_width) {
  return addr < target + target_width && target < addr + width;
}

static bool is_contact_xyz(uint32_t addr) {
  if (addr < 0x800b0d18u || addr >= 0x800b1b18u) return false;
  uint32_t member = (addr - 0x800b0d18u) % 0x38u;
  return member == 0 || member == 4 || member == 8;
}

static uint32_t base_from_filename(const char *path) {
  const char *name = strrchr(path, '/');
  name = name ? name + 1 : path;
  char hex[9] = {0};
  for (int i = 0; i < 8; i++) {
    if (!isxdigit((unsigned char)name[i])) return 0;
    hex[i] = name[i];
  }
  return (uint32_t)strtoul(hex, NULL, 16);
}

static void process_file(const char *path) {
  FILE *fp = fopen(path, "r");
  if (!fp) return;
  uint32_t pc = base_from_filename(path);
  if (!pc) {
    fclose(fp);
    return;
  }
  file_n++;
  Val r[REG_N];
  for (int i = 0; i < REG_N; i++) r[i] = unknown_val();
  r[0] = const_val(0);

  char raw[LINE_N];
  while (fgets(raw, sizeof(raw), fp)) {
    raw[strcspn(raw, "\r\n")] = 0;
    char original[LINE_N];
    snprintf(original, sizeof(original), "%s", raw);
    char *comment = strchr(raw, '#');
    if (comment) *comment = 0;
    char *line = trim(raw);
    if (!*line || strchr(line, ':')) continue;
    if (*line == '.' && strncmp(line, ".word", 5) != 0) continue;

    char op[16] = {0};
    size_t oi = 0;
    while (line[oi] && !isspace((unsigned char)line[oi]) && oi + 1 < sizeof(op)) {
      op[oi] = line[oi];
      oi++;
    }
    op[oi] = 0;
    char *argtext = trim(line + oi);
    bool is_word = !strcmp(op, ".word");
    if (is_word || !strcmp(op, "nop")) {
      capture_anchor(path, pc, original);
      pc += 4;
      insn_n++;
      continue;
    }

    char argbuf[LINE_N];
    snprintf(argbuf, sizeof(argbuf), "%s", argtext);
    char *a[4] = {0};
    int na = split_operands(argbuf, a, 4);
    uint32_t this_pc = pc;
    pc += 4;
    insn_n++;
    capture_anchor(path, this_pc, original);

    if (!strcmp(op, "lui") && na == 2) {
      int d = reg_index(a[0]);
      int32_t imm;
      if (d > 0 && parse_i32(a[1], &imm)) r[d] = const_val((uint32_t)imm << 16);
      continue;
    }

    if ((!strcmp(op, "addiu") || !strcmp(op, "addi")) && na == 3) {
      int d = reg_index(a[0]), s = reg_index(a[1]);
      int32_t imm;
      if (d > 0 && s >= 0 && parse_i32(a[2], &imm)) {
        Val v = r[s];
        if (v.known) v.value += (uint32_t)imm;
        if (v.has_base) v.base += (uint32_t)imm;
        r[d] = v;
      }
      continue;
    }

    if ((!strcmp(op, "ori") || !strcmp(op, "andi") || !strcmp(op, "xori")) && na == 3) {
      int d = reg_index(a[0]), s = reg_index(a[1]);
      int32_t imm_i;
      if (d > 0 && s >= 0 && parse_i32(a[2], &imm_i)) {
        uint32_t imm = (uint32_t)imm_i & 0xffffu;
        Val v = r[s];
        if (v.known) {
          if (!strcmp(op, "ori")) v.value |= imm;
          if (!strcmp(op, "andi")) v.value &= imm;
          if (!strcmp(op, "xori")) v.value ^= imm;
        }
        if (v.has_load) {
          if (!strcmp(op, "andi")) v.and_mask &= imm;
          if (!strcmp(op, "ori")) v.or_mask |= imm;
        }
        r[d] = v;
      }
      continue;
    }

    if ((!strcmp(op, "addu") || !strcmp(op, "or") || !strcmp(op, "and")) && na == 3) {
      int d = reg_index(a[0]), x = reg_index(a[1]), y = reg_index(a[2]);
      if (d > 0 && x >= 0 && y >= 0) {
        if (r[x].known && r[y].known) {
          uint32_t z = 0;
          if (!strcmp(op, "addu")) z = r[x].value + r[y].value;
          if (!strcmp(op, "or")) z = r[x].value | r[y].value;
          if (!strcmp(op, "and")) z = r[x].value & r[y].value;
          r[d] = const_val(z);
        } else if (!strcmp(op, "addu") && r[x].known) {
          r[d] = unknown_val();
          r[d].has_base = true;
          r[d].base = r[x].value;
        } else if (!strcmp(op, "addu") && r[y].known) {
          r[d] = unknown_val();
          r[d].has_base = true;
          r[d].base = r[y].value;
        } else if (!strcmp(op, "or") && y == 0) {
          r[d] = r[x];
        } else if (!strcmp(op, "or") && x == 0) {
          r[d] = r[y];
        } else {
          r[d] = unknown_val();
        }
      }
      continue;
    }

    if (!strcmp(op, "sll") && na == 3) {
      int d = reg_index(a[0]), s = reg_index(a[1]);
      int32_t sh;
      if (d > 0 && s >= 0 && parse_i32(a[2], &sh) && r[s].known)
        r[d] = const_val(r[s].value << (sh & 31));
      else if (d > 0)
        r[d] = unknown_val();
      continue;
    }

    bool is_load = !strcmp(op, "lw") || !strcmp(op, "lh") || !strcmp(op, "lhu") ||
                   !strcmp(op, "lb") || !strcmp(op, "lbu");
    if (is_load && na == 2) {
      int d = reg_index(a[0]), b;
      int32_t off;
      if (d > 0 && parse_mem(a[1], &off, &b)) {
        Val v = unknown_val();
        if (r[b].known) {
          v.has_load = true;
          v.load_addr = r[b].value + (uint32_t)off;
          if (!strcmp(op, "lh") || !strcmp(op, "lhu")) v.and_mask = 0xffffu;
          if (!strcmp(op, "lb") || !strcmp(op, "lbu")) v.and_mask = 0xffu;
        }
        r[d] = v;
      }
      continue;
    }

    bool is_store = !strcmp(op, "sw") || !strcmp(op, "sh") || !strcmp(op, "sb");
    if (is_store && na == 2) {
      int s = reg_index(a[0]), b;
      int32_t off;
      unsigned width = !strcmp(op, "sw") ? 4u : (!strcmp(op, "sh") ? 2u : 1u);
      if (s >= 0 && parse_mem(a[1], &off, &b)) {
        bool exact = r[b].known;
        uint32_t addr = exact ? r[b].value + (uint32_t)off : 0;
        bool dyn = r[b].has_base;
        uint32_t dyn_base = dyn ? r[b].base : 0;
        bool target_hit = exact &&
          (overlaps(addr, width, 0x800a657eu, 2) || overlaps(addr, width, 0x800a6590u, 4));
        bool contact_hit = (exact && is_contact_xyz(addr)) ||
          (dyn && dyn_base >= 0x800b0d18u &&
           dyn_base < 0x800b1b18u && (off == 0 || off == 4 || off == 8));
        if (target_hit || contact_hit)
          add_hit(path, this_pc, op, trim(original), addr, dyn, dyn_base, r[s]);
      }
      continue;
    }

    if (na > 0) {
      int d = reg_index(a[0]);
      if (d > 0 && strcmp(op, "beq") && strcmp(op, "bne") && strcmp(op, "j") &&
          strcmp(op, "jal") && strcmp(op, "jr") && strcmp(op, "mult") &&
          strcmp(op, "multu") && strcmp(op, "div") && strcmp(op, "divu"))
        r[d] = unknown_val();
    }
  }
  fclose(fp);
}

static void walk(const char *dir) {
  DIR *dp = opendir(dir);
  if (!dp) {
    perror(dir);
    exit(2);
  }
  struct dirent *de;
  while ((de = readdir(dp))) {
    if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
    char path[PATH_N];
    snprintf(path, sizeof(path), "%s/%s", dir, de->d_name);
    struct stat st;
    if (stat(path, &st)) continue;
    if (S_ISDIR(st.st_mode)) walk(path);
    else {
      size_t n = strlen(path);
      if (n > 2 && !strcmp(path + n - 2, ".s")) process_file(path);
    }
  }
  closedir(dp);
}

static const char *kind(const Hit *h) {
  if (!h->target_dynamic && is_contact_xyz(h->target))
    return "contact_position_writer";
  if (!h->target_dynamic && overlaps(h->target, !strcmp(h->op, "sw") ? 4 : (!strcmp(h->op, "sh") ? 2 : 1),
                                     0x800a657e, 2))
    return "power_slot_writer";
  if (!h->target_dynamic)
    return "power_flags_writer";
  return "contact_position_writer";
}

static size_t count_text(const char *path, const char *needle) {
  FILE *fp = fopen(path, "r");
  if (!fp) return 0;
  size_t count = 0;
  char line[LINE_N * 4];
  while (fgets(line, sizeof(line), fp)) {
    const char *p = line;
    while ((p = strstr(p, needle)) != NULL) {
      count++;
      p += strlen(needle);
    }
  }
  fclose(fp);
  return count;
}

static void read_pristine_words(const char *path) {
  FILE *fp = fopen(path, "rb");
  if (!fp) {
    perror(path);
    exit(2);
  }
  for (size_t i = 0; i < sizeof(anchors) / sizeof(anchors[0]); i++) {
    uint64_t off = 0x800ull + (uint64_t)anchors[i].pc - 0x80010000ull;
    unsigned char b[4];
    if (fseek(fp, (long)off, SEEK_SET) == 0 && fread(b, 1, sizeof(b), fp) == sizeof(b)) {
      anchors[i].word = (uint32_t)b[0] | ((uint32_t)b[1] << 8) |
                        ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
      anchors[i].word_read = true;
    }
  }
  fclose(fp);
}

int main(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "usage: %s asm_root capsule_analysis_json pristine_executable\n", argv[0]);
    return 2;
  }
  walk(argv[1]);
  read_pristine_words(argv[3]);
  printf("{\n  \"schema\":\"phase4_c13_asm_static_v1\",\n");
  printf("  \"files_scanned\":%zu,\n  \"instructions_scanned\":%zu,\n", file_n, insn_n);
  printf("  \"capsule_correlation\":{\"source_events\":%zu,\"ctor_action_0x14\":%zu,"
         "\"ctor_ttl_200\":%zu,\"ctor_flags_0xea\":%zu,"
         "\"exact_contact_chain_check\":%s},\n",
         count_text(argv[2], "\"source_index\":"),
         count_text(argv[2], "\"contact_action_id\": 20"),
         count_text(argv[2], "\"contact_initial_ttl\": 200"),
         count_text(argv[2], "\"contact_initial_flags\": 234"),
         count_text(argv[2], "\"source_events_construct_exact_grain_contacts\": true") == 1 ? "true" : "false");
  printf("  \"anchors\":[\n");
  for (size_t i = 0; i < sizeof(anchors) / sizeof(anchors[0]); i++) {
    Anchor *a = &anchors[i];
    printf("    {\"role\":\"%s\",\"pc\":\"0x%08" PRIx32 "\",\"found\":%s",
           a->role, a->pc, a->found ? "true" : "false");
    if (a->word_read) printf(",\"pristine_word\":\"0x%08" PRIx32 "\"", a->word);
    if (a->found) {
      fputs(",\"path\":", stdout);
      print_json_string(a->path);
      fputs(",\"instruction\":", stdout);
      print_json_string(a->instruction);
    }
    printf("}%s\n", i + 1 == sizeof(anchors) / sizeof(anchors[0]) ? "" : ",");
  }
  printf("  ],\n");
  printf("  \"candidates\":[\n");
  for (size_t i = 0; i < hit_n; i++) {
    const Hit *h = &hits[i];
    printf("    {\"kind\":\"%s\",\"pc\":\"0x%08" PRIx32 "\",\"path\":", kind(h), h->pc);
    print_json_string(h->path);
    fputs(",\"instruction\":", stdout);
    print_json_string(h->text);
    putchar(',');
    if (h->target_dynamic)
      printf("\"dynamic_base\":\"0x%08" PRIx32 "\",", h->dynamic_base);
    else
      printf("\"target\":\"0x%08" PRIx32 "\",", h->target);
    if (h->source_known)
      printf("\"source_constant\":\"0x%08" PRIx32 "\"", h->source_value);
    else if (h->source_load)
      printf("\"source_load\":\"0x%08" PRIx32 "\",\"and_mask\":\"0x%08" PRIx32
             "\",\"or_mask\":\"0x%08" PRIx32 "\"",
             h->source_load_addr, h->source_and_mask, h->source_or_mask);
    else
      printf("\"source\":\"unknown\"");
    printf("}%s\n", i + 1 == hit_n ? "" : ",");
  }
  printf("  ]\n}\n");
  return 0;
}
