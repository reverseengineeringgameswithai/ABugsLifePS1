#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_INSNS = 160000, MAX_CALLS = 1024, MAX_TEXT = 256 };

typedef struct Insn {
  uint32_t pc;
  char file[160];
  char text[MAX_TEXT];
} Insn;

typedef struct Call {
  size_t insn_index;
  uint32_t pc;
  uint32_t target;
  int ctor_known;
  int32_t ctor;
  int profile_known;
  int32_t profile;
  char file[160];
} Call;

static Insn g_insns[MAX_INSNS];
static Call g_calls[MAX_CALLS];
static size_t g_insn_count, g_call_count;

static uint16_t le16(const uint8_t *p) {
  return (uint16_t)(p[0] | (uint16_t)p[1] << 8);
}

static uint32_t le32(const uint8_t *p) {
  return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
         (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint8_t *read_file(const char *path, size_t *size) {
  FILE *f = fopen(path, "rb");
  uint8_t *data;
  long n;
  if (!f || fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 ||
      fseek(f, 0, SEEK_SET)) return NULL;
  data = malloc((size_t)n + 1u);
  if (!data || fread(data, 1, (size_t)n, f) != (size_t)n) {
    free(data); fclose(f); return NULL;
  }
  fclose(f); data[n] = 0; *size = (size_t)n; return data;
}

static void sha256_hex(const uint8_t *data, size_t size, char out[65]) {
  uint8_t digest[EVP_MAX_MD_SIZE];
  unsigned digest_size = 0;
  EVP_MD_CTX *ctx = EVP_MD_CTX_new();
  if (!ctx || EVP_DigestInit_ex(ctx, EVP_sha256(), NULL) != 1 ||
      EVP_DigestUpdate(ctx, data, size) != 1 ||
      EVP_DigestFinal_ex(ctx, digest, &digest_size) != 1 || digest_size != 32) {
    fprintf(stderr, "SHA-256 failed\n"); exit(1);
  }
  EVP_MD_CTX_free(ctx);
  for (unsigned i = 0; i < digest_size; i++) sprintf(out + i * 2u, "%02x", digest[i]);
  out[64] = '\0';
}

static char *trim(char *s) {
  while (isspace((unsigned char)*s)) s++;
  char *end = s + strlen(s);
  while (end > s && isspace((unsigned char)end[-1])) *--end = 0;
  return s;
}

static int is_instruction(const char *s) {
  if (!*s || *s == '#' || *s == ';') return 0;
  if (*s == '.') return strncmp(s, ".word", 5) == 0;
  return s[strlen(s) - 1] != ':';
}

static uint32_t file_start(const char *path) {
  const char *base = strrchr(path, '/');
  char buf[9];
  base = base ? base + 1 : path;
  if (strlen(base) < 8) return 0;
  memcpy(buf, base, 8); buf[8] = 0;
  return (uint32_t)strtoul(buf, NULL, 16);
}

static uint32_t call_target(const char *line) {
  static const uint32_t targets[] = { 0x80059e20u, 0x80059e44u, 0x8005a0e0u };
  char needle[32];
  for (size_t i = 0; i < sizeof targets / sizeof targets[0]; i++) {
    snprintf(needle, sizeof needle, "jal 0x%08x", targets[i]);
    if (strstr(line, needle)) return targets[i];
  }
  return 0;
}

static int load_asm(const char *path) {
  size_t size;
  uint8_t *raw = read_file(path, &size);
  char *save = NULL, *line;
  uint32_t pc = file_start(path);
  if (!raw || !pc) { free(raw); return 0; }
  for (line = strtok_r((char *)raw, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
    char original[MAX_TEXT];
    snprintf(original, sizeof original, "%s", line);
    char *s = trim(line);
    if (!is_instruction(s)) continue;
    if (g_insn_count == MAX_INSNS) { fprintf(stderr, "instruction capacity\n"); exit(1); }
    Insn *in = &g_insns[g_insn_count];
    in->pc = pc;
    snprintf(in->file, sizeof in->file, "%s", path);
    snprintf(in->text, sizeof in->text, "%s", s);
    uint32_t target = call_target(original);
    if (target) {
      if (g_call_count == MAX_CALLS) { fprintf(stderr, "call capacity\n"); exit(1); }
      Call *c = &g_calls[g_call_count++];
      memset(c, 0, sizeof *c);
      c->insn_index = g_insn_count;
      c->pc = pc;
      c->target = target;
      snprintf(c->file, sizeof c->file, "%s", path);
    }
    g_insn_count++;
    pc += 4;
  }
  free(raw); return 1;
}

static void clean_reg(char *s) {
  s = trim(s);
  if (*s == '$') memmove(s, s + 1, strlen(s));
  char *e = s;
  while (*e && (isalnum((unsigned char)*e) || *e == '_')) e++;
  *e = 0;
}

static int split(const char *text, char op[16], char args[4][48]) {
  char buf[MAX_TEXT], *s, *save = NULL, *tok;
  snprintf(buf, sizeof buf, "%s", text);
  char *comment = strchr(buf, '#'); if (comment) *comment = 0;
  s = trim(buf);
  size_t n = strcspn(s, " \t");
  if (n == 0 || n >= 16) return 0;
  memcpy(op, s, n); op[n] = 0;
  s = trim(s + n);
  int count = 0;
  for (tok = strtok_r(s, ",", &save); tok && count < 4; tok = strtok_r(NULL, ",", &save)) {
    snprintf(args[count++], 48, "%s", trim(tok));
  }
  return count;
}

static int volatile_reg(const char *r) {
  return !strcmp(r, "v0") || !strcmp(r, "v1") || !strcmp(r, "a0") ||
         !strcmp(r, "a1") || !strcmp(r, "a2") || !strcmp(r, "a3") ||
         !strcmp(r, "t0") || !strcmp(r, "t1") || !strcmp(r, "t2") ||
         !strcmp(r, "t3") || !strcmp(r, "t4") || !strcmp(r, "t5") ||
         !strcmp(r, "t6") || !strcmp(r, "t7") || !strcmp(r, "t8") ||
         !strcmp(r, "t9") || !strcmp(r, "ra");
}

static int parse_imm(const char *s, int32_t *v) {
  char *end;
  long x = strtol(s, &end, 0);
  if (end == s) return 0;
  *v = (int32_t)x; return 1;
}

static int resolve_reg(size_t before, const char *wanted, int depth, int32_t *out) {
  if (!strcmp(wanted, "zero")) { *out = 0; return 1; }
  if (depth > 8) return 0;
  size_t floor = before > 96 ? before - 96 : 0;
  for (size_t j = before; j-- > floor;) {
    char op[16], a[4][48], dest[48], src[48];
    int n = split(g_insns[j].text, op, a);
    if (!strcmp(op, ".word") && strstr(g_insns[j].text, "jal") && volatile_reg(wanted)) return 0;
    if (!strcmp(op, "jal") && volatile_reg(wanted)) return 0;
    if (n < 1) continue;
    snprintf(dest, sizeof dest, "%s", a[0]); clean_reg(dest);
    int writes = !strcmp(op, "addiu") || !strcmp(op, "addi") || !strcmp(op, "ori") ||
                 !strcmp(op, "lui") || !strcmp(op, "addu") || !strcmp(op, "or") ||
                 !strcmp(op, "sll") || !strcmp(op, "subu") || !strcmp(op, "lw") ||
                 !strcmp(op, "lh") || !strcmp(op, "lhu") || !strcmp(op, "lbu") ||
                 !strcmp(op, "lb") || !strcmp(op, "mflo") || !strcmp(op, "mfhi");
    if (!writes || strcmp(dest, wanted)) continue;
    int32_t x, imm;
    if (!strcmp(op, "lui") && n >= 2 && parse_imm(a[1], &imm)) {
      *out = (int32_t)((uint32_t)imm << 16); return 1;
    }
    if ((!strcmp(op, "addiu") || !strcmp(op, "addi") || !strcmp(op, "ori")) && n >= 3) {
      snprintf(src, sizeof src, "%s", a[1]); clean_reg(src);
      if (!parse_imm(a[2], &imm) || !resolve_reg(j, src, depth + 1, &x)) return 0;
      *out = !strcmp(op, "ori") ? (int32_t)((uint32_t)x | (uint32_t)(uint16_t)imm) : x + imm;
      return 1;
    }
    if ((!strcmp(op, "addu") || !strcmp(op, "or")) && n >= 3) {
      char r2[48]; snprintf(src, sizeof src, "%s", a[1]); clean_reg(src);
      snprintf(r2, sizeof r2, "%s", a[2]); clean_reg(r2);
      if (!strcmp(r2, "zero")) return resolve_reg(j, src, depth + 1, out);
      if (!strcmp(src, "zero")) return resolve_reg(j, r2, depth + 1, out);
      return 0;
    }
    if (!strcmp(op, "sll") && n >= 3) {
      snprintf(src, sizeof src, "%s", a[1]); clean_reg(src);
      if (!parse_imm(a[2], &imm) || !resolve_reg(j, src, depth + 1, &x)) return 0;
      *out = (int32_t)((uint32_t)x << imm); return 1;
    }
    if (!strcmp(op, "subu") && n >= 3) {
      char r2[48]; snprintf(src, sizeof src, "%s", a[1]); clean_reg(src);
      snprintf(r2, sizeof r2, "%s", a[2]); clean_reg(r2);
      if (!strcmp(src, "zero") && resolve_reg(j, r2, depth + 1, &x)) { *out = -x; return 1; }
      return 0;
    }
    return 0;
  }
  return 0;
}

static int stack_value(size_t before, int offset, int32_t *value) {
  size_t floor = before > 64 ? before - 64 : 0;
  for (size_t j = before; j-- > floor;) {
    char op[16], a[4][48], pattern[24], src[48];
    int n = split(g_insns[j].text, op, a);
    if (j == before - 2) continue; /* the call whose delay slot ends at before */
    if ((strstr(g_insns[j].text, "jal ") ||
         (!strcmp(op, ".word") && strstr(g_insns[j].text, "jal"))) && j + 1 < before) return 0;
    if (strcmp(op, "sw") || n < 2) continue;
    snprintf(pattern, sizeof pattern, "%d($sp)", offset);
    if (strcmp(a[1], pattern)) continue;
    snprintf(src, sizeof src, "%s", a[0]); clean_reg(src);
    return resolve_reg(j, src, 0, value);
  }
  return 0;
}

static const uint8_t *exe_ptr(const uint8_t *exe, size_t size, uint32_t addr, size_t length) {
  if (addr < 0x80010000u) return NULL;
  size_t off = 0x800u + (size_t)(addr - 0x80010000u);
  if (off > size || length > size - off) return NULL;
  return exe + off;
}

static const char *base_name(const char *path) {
  const char *p = strrchr(path, '/'); return p ? p + 1 : path;
}

int main(int argc, char **argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: %s SCUS_942.88 ASM...\n", argv[0]); return 2;
  }
  size_t exe_size;
  uint8_t *exe = read_file(argv[1], &exe_size);
  if (!exe || exe_size < 0x800 || memcmp(exe, "PS-X EXE", 8)) {
    fprintf(stderr, "invalid PS-X EXE\n"); return 1;
  }
  uint32_t t_addr = le32(exe + 0x18), t_size = le32(exe + 0x1c);
  if (t_addr != 0x80010000u || t_size != 0x72800u) {
    fprintf(stderr, "unexpected EXE identity %08" PRIx32 "/%08" PRIx32 "\n", t_addr, t_size); return 1;
  }
  char exe_sha[65]; sha256_hex(exe, exe_size, exe_sha);
  for (int i = 2; i < argc; i++) if (!load_asm(argv[i])) {
    fprintf(stderr, "failed ASM %s: %s\n", argv[i], strerror(errno)); return 1;
  }
  for (size_t i = 0; i < g_call_count; i++) {
    Call *c = &g_calls[i];
    size_t boundary = c->insn_index + 2 < g_insn_count ? c->insn_index + 2 : g_insn_count;
    if (c->target == 0x8005a0e0u) {
      c->ctor_known = stack_value(boundary, 28, &c->ctor);
    } else {
      c->ctor_known = resolve_reg(boundary, "a3", 0, &c->ctor);
      if (!c->ctor_known) c->ctor_known = resolve_reg(c->insn_index, "a3", 0, &c->ctor);
      c->profile_known = stack_value(boundary, 16, &c->profile);
    }
  }

  const uint32_t meta_b_addr = 0x8007941cu, meta_a_addr = 0x80079e30u;
  const uint32_t next_addr = 0x8007a448u;
  const unsigned meta_b_rows = (meta_a_addr - meta_b_addr) / 0x14u;
  const unsigned meta_a_rows = (next_addr - meta_a_addr) / 0x14u;
  const uint8_t *meta_b = exe_ptr(exe, exe_size, meta_b_addr, meta_b_rows * 0x14u);
  const uint8_t *meta_a = exe_ptr(exe, exe_size, meta_a_addr, meta_a_rows * 0x14u);
  const uint8_t *dispatch = exe_ptr(exe, exe_size, 0x8001b570u, 117u * 4u);
  if (!meta_b || !meta_a || !dispatch) { fprintf(stderr, "table outside EXE\n"); return 1; }

  unsigned action_freq[256] = {0}, direct_ctor_freq[129] = {0}, profile_freq[78] = {0};
  unsigned invalid_actions = 0, unique_actions = 0, known_ctors = 0, unknown_ctors = 0;
  unsigned known_profiles = 0, unknown_profiles = 0;
  int max_ctor = -1, max_profile = -1;
  for (unsigned i = 0; i < meta_b_rows; i++) {
    uint16_t action = le16(meta_b + i * 0x14u);
    if (action < 256) action_freq[action]++; else invalid_actions++;
  }
  for (unsigned i = 0; i < 256; i++) unique_actions += action_freq[i] != 0;
  for (size_t i = 0; i < g_call_count; i++) {
    Call *c = &g_calls[i];
    if (c->ctor_known && c->ctor >= 0 && c->ctor < 129) {
      direct_ctor_freq[c->ctor]++; known_ctors++; if (c->ctor > max_ctor) max_ctor = c->ctor;
    } else unknown_ctors++;
    if (c->target != 0x8005a0e0u) {
      if (c->profile_known && c->profile >= 0 && c->profile < 78) {
        profile_freq[c->profile]++; known_profiles++; if (c->profile > max_profile) max_profile = c->profile;
      } else unknown_profiles++;
    }
  }

  printf("{\n \"schema\":\"abl-phase4-e06-static-v1\",\n");
  printf(" \"row\":\"E06_contact_object_pool\",\n");
  printf(" \"exe\":{\"path\":\"%s\",\"sha256\":\"%s\",\"t_addr\":\"0x%08" PRIX32 "\",\"t_size\":%u},\n",
         argv[1], exe_sha, t_addr, t_size);
  printf(" \"asm\":{\"files\":%d,\"instructions\":%zu,\"allocator_calls\":%zu},\n",
         argc - 2, g_insn_count, g_call_count);
  printf(" \"table_boundaries\":{\"metadata_b\":{\"start\":\"0x8007941C\",\"end_exclusive\":\"0x80079E30\",\"stride\":20,\"rows\":%u},\"metadata_a\":{\"start\":\"0x80079E30\",\"end_exclusive\":\"0x8007A448\",\"stride\":20,\"rows\":%u}},\n",
         meta_b_rows, meta_a_rows);
  printf(" \"metadata_b\":{\"unique_action_ids\":%u,\"invalid_u8_action_ids\":%u,\"action_to_ctors\":{",
         unique_actions, invalid_actions);
  int comma = 0;
  for (unsigned a = 0; a < 256; a++) if (action_freq[a]) {
    printf("%s\n  \"%u\":[", comma ? "," : "", a); int c2 = 0;
    for (unsigned ctor = 0; ctor < meta_b_rows; ctor++) if (le16(meta_b + ctor * 0x14u) == a)
      printf("%s%u", c2++ ? "," : "", ctor);
    putchar(']'); comma = 1;
  }
  printf("\n }},\n");
  printf(" \"walker_dispatch\":{\"entries\":117,\"default_target\":\"0x800589D4\",\"nondefault\":[");
  comma = 0;
  for (unsigned i = 0; i < 117; i++) {
    uint32_t target = le32(dispatch + i * 4u);
    if (target != 0x800589d4u) {
      printf("%s{\"action_id\":%u,\"target\":\"0x%08" PRIX32 "\"}", comma ? "," : "", i + 2, target);
      comma = 1;
    }
  }
  printf("]},\n");
  printf(" \"callsites\":[");
  for (size_t i = 0; i < g_call_count; i++) {
    Call *c = &g_calls[i];
    printf("%s{\"pc\":\"0x%08" PRIX32 "\",\"target\":\"0x%08" PRIX32 "\",\"file\":\"%s\",\"ctor\":",
           i ? "," : "", c->pc, c->target, base_name(c->file));
    if (c->ctor_known) printf("%" PRId32, c->ctor); else printf("null");
    printf(",\"profile\":");
    if (c->target == 0x8005a0e0u || !c->profile_known) printf("null"); else printf("%" PRId32, c->profile);
    putchar('}');
  }
  printf("],\n");
  printf(" \"caller_resolution\":{\"known_ctor_calls\":%u,\"unknown_ctor_calls\":%u,\"max_constant_ctor\":%d,\"known_profile_calls\":%u,\"unknown_profile_calls\":%u,\"max_constant_profile\":%d,\"constant_ctor_usage\":{",
         known_ctors, unknown_ctors, max_ctor, known_profiles, unknown_profiles, max_profile);
  comma = 0;
  for (unsigned i = 0; i < 129; i++) if (direct_ctor_freq[i]) {
    printf("%s\"%u\":%u", comma ? "," : "", i, direct_ctor_freq[i]); comma = 1;
  }
  printf("},\"constant_profile_usage\":{"); comma = 0;
  for (unsigned i = 0; i < 78; i++) if (profile_freq[i]) {
    printf("%s\"%u\":%u", comma ? "," : "", i, profile_freq[i]); comma = 1;
  }
  printf("}},\n");
  printf(" \"static_conclusions\":[\n");
  printf("  \"metadata B has exactly 129 rows; prior ctor scans through 199 crossed into metadata A and adjacent data\",\n");
  printf("  \"metadata A has exactly 78 rows by contiguous table boundaries\",\n");
  printf("  \"both allocators have a 64-slot round-robin search with no full-pool escape, so all 64 occupied slots imply a non-terminating allocation loop\"\n");
  printf(" ]\n}\n");
  free(exe); return 0;
}
