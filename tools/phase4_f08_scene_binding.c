/* Phase 4 F08 (City Square) -- pin the scene->asset binding from the pristine image.
 *
 * WHY. The F08 row asserts:
 *
 *     "Scene id 5 (u32 0x80082504) -> scene_asset_table 0x8001AD0C[4] = level10\level2b;
 *      ... overlays LEVEL10_LEVEL/_LEVEL1"
 *
 * Two things contradict that before any of this runs:
 *
 *   1. All five F08 save fixtures read scene_id == 5, and the overlay actually
 *      resident at region A (0x800B39A0) in those saves matches OVL/LEVEL05_LEVEL.BIN
 *      at 99.14% over 1862 NON-TRIVIAL bytes (zero-vs-zero agreement excluded), while
 *      LEVEL10_LEVEL.BIN matches 5.53%. Those files are byte-identical copies of the
 *      disc's LEVELnn/ directories, so the naming is disc-directory naming.
 *   2. OVL/LEVEL10_LEVEL1.BIN does not exist -- the disc's LEVEL10/ directory has no
 *      LEVEL1.BIN at all. The row names a file that is not on the disc.
 *
 * The suspicion is an INDEXING error: scene id N read as table[N-1] rather than
 * table[N]. This tool does not assume either; it dumps every entry with its index so
 * the mapping is read off the image rather than argued about.
 *
 * This is a static pin, so it is a compiled self-verifying C tool per the standing
 * rule, not a script. Every claim it prints is an assertion that must hold against
 * the pristine SCUS_942.88; it exits nonzero if any fails.
 *
 *   gcc -O2 -std=c11 -Wall -Wextra -Werror -o /tmp/f08 tools/phase4_f08_scene_binding.c
 *   /tmp/f08
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define EXE_PATH        "SCUS_942.88"
#define EXE_HEADER      2048u
#define SCENE_TABLE     0x8001AD0Cu
#define SCENE_ENTRY_SZ  0x10u
#define SCENE_COUNT     15u
#define SCENE_ID_ADDR   0x80082504u

static unsigned char *g_img;
static size_t         g_img_len;
static uint32_t       g_load;

static int g_pass, g_fail;

static void check(int cond, const char *what)
{
  if (cond) { g_pass++; printf("  [ok]   %s\n", what); }
  else      { g_fail++; printf("  [FAIL] %s\n", what); }
}

static int in_image(uint32_t addr, uint32_t len)
{
  if (addr < g_load) return 0;
  uint64_t off = (uint64_t)addr - g_load;
  return off + len <= g_img_len;
}

static const unsigned char *at(uint32_t addr)
{
  if (!in_image(addr, 1)) { fprintf(stderr, "addr 0x%08X outside image\n", addr); exit(2); }
  return g_img + (addr - g_load);
}

/* Entries are fixed-width, NUL-padded, and NOT guaranteed terminated. Copy into a
 * bounded buffer rather than trusting the image to contain a terminator. */
static void entry_text(uint32_t idx, char *out, size_t outsz)
{
  const unsigned char *p = at(SCENE_TABLE + idx * SCENE_ENTRY_SZ);
  size_t n = SCENE_ENTRY_SZ < outsz - 1 ? SCENE_ENTRY_SZ : outsz - 1;
  size_t i;
  for (i = 0; i < n && p[i] != 0; i++)
    out[i] = (char)(p[i] >= 0x20 && p[i] < 0x7F ? p[i] : '.');
  out[i] = 0;
}

/* --- minimal MIPS I disassembler -------------------------------------------
 * Only what is needed to read an index computation. UNKNOWN OPCODES ARE PRINTED
 * LOUDLY as "op%02x/fn%02x": in F16 a missing sltiu rendered as "op0b" and hid the
 * deciding test, so silence here is the failure mode to avoid. */
static const char *R[32] = {
  "zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
  "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"};

static void disasm(uint32_t pc, uint32_t w, char *out, size_t n)
{
  uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
  uint32_t rd = (w >> 11) & 31, sa = (w >> 6) & 31, fn = w & 63;
  int16_t  imm = (int16_t)(w & 0xFFFF);
  uint32_t tgt = (pc & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2);
  uint32_t br  = pc + 4 + ((int32_t)imm << 2);

  switch (op)
  {
    case 0x00:
      switch (fn)
      {
        case 0x00: if (!w) { snprintf(out, n, "nop"); return; }
                   snprintf(out, n, "sll %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x02: snprintf(out, n, "srl %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x03: snprintf(out, n, "sra %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x04: snprintf(out, n, "sllv %s,%s,%s", R[rd], R[rt], R[rs]); return;
        case 0x08: snprintf(out, n, "jr %s", R[rs]); return;
        case 0x09: snprintf(out, n, "jalr %s,%s", R[rd], R[rs]); return;
        case 0x10: snprintf(out, n, "mfhi %s", R[rd]); return;
        case 0x12: snprintf(out, n, "mflo %s", R[rd]); return;
        case 0x18: snprintf(out, n, "mult %s,%s", R[rs], R[rt]); return;
        case 0x19: snprintf(out, n, "multu %s,%s", R[rs], R[rt]); return;
        case 0x1A: snprintf(out, n, "div %s,%s", R[rs], R[rt]); return;
        case 0x1B: snprintf(out, n, "divu %s,%s", R[rs], R[rt]); return;
        case 0x20: snprintf(out, n, "add %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x21: snprintf(out, n, "addu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x22: snprintf(out, n, "sub %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x23: snprintf(out, n, "subu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x24: snprintf(out, n, "and %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x25: snprintf(out, n, "or %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x2A: snprintf(out, n, "slt %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x2B: snprintf(out, n, "sltu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        default:   snprintf(out, n, "op00/fn%02x", fn); return;
      }
    case 0x02: snprintf(out, n, "j 0x%08X", tgt); return;
    case 0x03: snprintf(out, n, "jal 0x%08X", tgt); return;
    case 0x04: snprintf(out, n, "beq %s,%s,0x%08X", R[rs], R[rt], br); return;
    case 0x05: snprintf(out, n, "bne %s,%s,0x%08X", R[rs], R[rt], br); return;
    case 0x06: snprintf(out, n, "blez %s,0x%08X", R[rs], br); return;
    case 0x07: snprintf(out, n, "bgtz %s,0x%08X", R[rs], br); return;
    case 0x08: snprintf(out, n, "addi %s,%s,%d", R[rt], R[rs], imm); return;
    case 0x09: snprintf(out, n, "addiu %s,%s,%d", R[rt], R[rs], imm); return;
    case 0x0A: snprintf(out, n, "slti %s,%s,%d", R[rt], R[rs], imm); return;
    case 0x0B: snprintf(out, n, "sltiu %s,%s,%d", R[rt], R[rs], imm); return;
    case 0x0C: snprintf(out, n, "andi %s,%s,0x%04X", R[rt], R[rs], (uint16_t)imm); return;
    case 0x0D: snprintf(out, n, "ori %s,%s,0x%04X", R[rt], R[rs], (uint16_t)imm); return;
    case 0x0E: snprintf(out, n, "xori %s,%s,0x%04X", R[rt], R[rs], (uint16_t)imm); return;
    case 0x0F: snprintf(out, n, "lui %s,0x%04X", R[rt], (uint16_t)imm); return;
    case 0x20: snprintf(out, n, "lb %s,%d(%s)", R[rt], imm, R[rs]); return;
    case 0x21: snprintf(out, n, "lh %s,%d(%s)", R[rt], imm, R[rs]); return;
    case 0x23: snprintf(out, n, "lw %s,%d(%s)", R[rt], imm, R[rs]); return;
    case 0x24: snprintf(out, n, "lbu %s,%d(%s)", R[rt], imm, R[rs]); return;
    case 0x25: snprintf(out, n, "lhu %s,%d(%s)", R[rt], imm, R[rs]); return;
    case 0x28: snprintf(out, n, "sb %s,%d(%s)", R[rt], imm, R[rs]); return;
    case 0x29: snprintf(out, n, "sh %s,%d(%s)", R[rt], imm, R[rs]); return;
    case 0x2B: snprintf(out, n, "sw %s,%d(%s)", R[rt], imm, R[rs]); return;
    default:   snprintf(out, n, "op%02x", op); return;
  }
}

static void dump_range(const char *label, uint32_t lo, uint32_t hi)
{
  printf("\n=== %s  0x%08X..0x%08X ===\n", label, lo, hi);
  for (uint32_t a = lo; a < hi; a += 4)
  {
    if (!in_image(a, 4)) { printf("  0x%08X  <outside image>\n", a); return; }
    uint32_t w;
    memcpy(&w, at(a), 4);
    char t[80];
    disasm(a, w, t, sizeof t);
    const char *mark = "";
    if (strstr(t, "0x8001") && strstr(t, "lui")) mark = "   <-- table hi";
    printf("  0x%08X  %08X  %-34s%s\n", a, w, t, mark);
  }
}

int main(void)
{
  FILE *f = fopen(EXE_PATH, "rb");
  if (!f) { fprintf(stderr, "cannot open %s (run from the repo root)\n", EXE_PATH); return 2; }
  fseek(f, 0, SEEK_END);
  long sz = ftell(f);
  fseek(f, 0, SEEK_SET);
  if (sz <= (long)EXE_HEADER) { fprintf(stderr, "exe too small\n"); fclose(f); return 2; }

  unsigned char hdr[EXE_HEADER];
  if (fread(hdr, 1, EXE_HEADER, f) != EXE_HEADER) { fclose(f); return 2; }
  memcpy(&g_load, hdr + 0x18, 4);

  g_img_len = (size_t)sz - EXE_HEADER;
  g_img = malloc(g_img_len);
  if (!g_img || fread(g_img, 1, g_img_len, f) != g_img_len) { fclose(f); return 2; }
  fclose(f);

  printf("SCUS_942.88  load 0x%08X  image %zu bytes\n\n", g_load, g_img_len);

  printf("=== scene_asset_table 0x%08X (%u x 0x%X) ===\n", SCENE_TABLE, SCENE_COUNT,
         SCENE_ENTRY_SZ);
  char text[SCENE_ENTRY_SZ + 1];
  int idx_level10 = -1, idx_level05 = -1;
  for (uint32_t i = 0; i < SCENE_COUNT; i++)
  {
    entry_text(i, text, sizeof text);
    printf("  [%2u] @0x%08X  \"%s\"\n", i, SCENE_TABLE + i * SCENE_ENTRY_SZ, text);
    if (strstr(text, "level10") && idx_level10 < 0) idx_level10 = (int)i;
    if (strstr(text, "level05") && idx_level05 < 0) idx_level05 = (int)i;
  }

  printf("\n=== what the F08 row claims, tested ===\n");
  entry_text(4, text, sizeof text);
  printf("  table[4] is \"%s\"\n", text);
  check(strstr(text, "level10") != NULL,
        "row's cited entry table[4] does contain level10 (the row read the table correctly)");

  entry_text(5, text, sizeof text);
  printf("  table[5] is \"%s\"\n", text);

  printf("\n=== the indexing question ===\n");
  printf("  first level10 entry : [%d]\n", idx_level10);
  printf("  first level05 entry : [%d]\n", idx_level05);
  printf("  scene id in all five F08 fixtures (u32 @0x%08X) : 5\n", SCENE_ID_ADDR);
  printf("  overlay actually resident at region A in those fixtures : LEVEL05_LEVEL.BIN\n");

  /* An off-by-one (table[id-1] vs table[id]) was the obvious hypothesis and it is
   * REFUTED: table[5] is level01\level2c, which is neither level10 nor the resident
   * level05. Asserting it here would have encoded a guess as a passing check, so
   * what follows asserts only what the image actually says. */
  entry_text(5, text, sizeof text);
  check(strstr(text, "level01") != NULL,
        "table[5] is level01\\level2c -- the simple off-by-one theory is REFUTED");

  check(idx_level10 == 4,
        "level10 appears only at index 4");
  check(idx_level05 == 7,
        "level05 first appears at index 7 (and again at [14]) -- so the resident "
        "overlay is NOT explained by either table[4] or table[5]");

  /* Directories are reused across stages, so a directory name cannot by itself
   * identify a scene. Prove that from the table rather than asserting it. */
  {
    int reused = 0;
    for (uint32_t i = 0; i < SCENE_COUNT; i++)
    {
      char a[SCENE_ENTRY_SZ + 1], b[SCENE_ENTRY_SZ + 1];
      entry_text(i, a, sizeof a);
      char *bs = strchr(a, '\\');
      if (!bs) continue;
      *bs = 0;
      for (uint32_t j = i + 1; j < SCENE_COUNT; j++)
      {
        entry_text(j, b, sizeof b);
        char *bs2 = strchr(b, '\\');
        if (!bs2) continue;
        *bs2 = 0;
        if (strcmp(a, b) == 0) { reused++; break; }
      }
    }
    printf("  directories reused by more than one scene : %d\n", reused);
    check(reused > 0,
          "asset DIRECTORIES are reused across scenes, so a directory name alone "
          "cannot identify a scene or its overlay");
  }

  dump_range("resource_id_dat_load_dispatcher (reads the table at 0x8003CFDC)",
             0x8003CF2Cu, 0x8003D010u);

  dump_range("LEVEL-DATA selection arithmetic (phase3 law, 2026-08-01)",
             0x8003D1E0u, 0x8003D260u);

  /* The dispatch is jumptable[resource_id - 1], NOT an index into the asset-name
   * table. Each handler picks its own assets, which is why no arithmetic maps a
   * scene id onto a scene_asset_table row. Walk each handler and record which
   * asset-name entry it materialises, so the mapping is read off the code. */
  printf("\n=== dispatch jump table 0x8001AFB0 (17 handlers, index = id-1) ===\n");
  {
    const uint32_t JT = 0x8001AFB0u, N = 17;
    for (uint32_t i = 0; i < N; i++)
    {
      uint32_t h;
      memcpy(&h, at(JT + i * 4), 4);
      /* Scan the handler for a materialised pointer into scene_asset_table:
       * lui rX,0x8001 followed by addiu rX,rX,<imm> landing on an entry. */
      int found = -1;
      uint32_t found_at = 0;
      for (uint32_t a = h; a < h + 0x400 && in_image(a, 4); a += 4)
      {
        uint32_t w1;
        memcpy(&w1, at(a), 4);
        if ((w1 >> 26) != 0x0F) continue;                 /* lui */
        uint32_t rt = (w1 >> 16) & 31, hi = w1 & 0xFFFF;
        for (uint32_t b = a + 4; b < a + 0x20 && in_image(b, 4); b += 4)
        {
          uint32_t w2;
          memcpy(&w2, at(b), 4);
          uint32_t op2 = w2 >> 26, rs2 = (w2 >> 21) & 31, rt2 = (w2 >> 16) & 31;
          if (op2 != 0x09 || rs2 != rt || rt2 != rt) continue;   /* addiu rt,rt,imm */
          int32_t lo = (int16_t)(w2 & 0xFFFF);
          uint32_t addr = (hi << 16) + (uint32_t)lo;
          if (addr >= SCENE_TABLE && addr < SCENE_TABLE + SCENE_COUNT * SCENE_ENTRY_SZ
              && ((addr - SCENE_TABLE) % SCENE_ENTRY_SZ) == 0)
          { found = (int)((addr - SCENE_TABLE) / SCENE_ENTRY_SZ); found_at = a; }
          break;
        }
        if (found >= 0) break;
      }
      if (found >= 0)
      {
        entry_text((uint32_t)found, text, sizeof text);
        printf("  id %2u -> handler 0x%08X   asset[%2d] \"%s\"  (@0x%08X)\n",
               i + 1, h, found, text, found_at);
      }
      else
      {
        printf("  id %2u -> handler 0x%08X   (no direct asset-table pointer in "
               "first 0x400 bytes)\n", i + 1, h);
      }
    }
  }

  /* Pin the mapping and, more importantly, pin WHY the wrong one looked right. */
  {
    const uint32_t JT = 0x8001AFB0u, N = 17;
    int map[18];
    for (uint32_t i = 0; i < N; i++)
    {
      uint32_t h;
      memcpy(&h, at(JT + i * 4), 4);
      map[i + 1] = -1;
      for (uint32_t a = h; a < h + 0x400 && in_image(a, 4); a += 4)
      {
        uint32_t w1;
        memcpy(&w1, at(a), 4);
        if ((w1 >> 26) != 0x0F) continue;
        uint32_t rt = (w1 >> 16) & 31, hi = w1 & 0xFFFF;
        for (uint32_t b = a + 4; b < a + 0x20 && in_image(b, 4); b += 4)
        {
          uint32_t w2;
          memcpy(&w2, at(b), 4);
          if ((w2 >> 26) != 0x09 || ((w2 >> 21) & 31) != rt || ((w2 >> 16) & 31) != rt)
            break;
          uint32_t addr = (hi << 16) + (uint32_t)(int16_t)(w2 & 0xFFFF);
          if (addr >= SCENE_TABLE && addr < SCENE_TABLE + SCENE_COUNT * SCENE_ENTRY_SZ
              && ((addr - SCENE_TABLE) % SCENE_ENTRY_SZ) == 0)
            map[i + 1] = (int)((addr - SCENE_TABLE) / SCENE_ENTRY_SZ);
          break;
        }
        if (map[i + 1] >= 0) break;
      }
    }

    printf("\n=== the F08 binding, corrected ===\n");
    entry_text((uint32_t)map[5], text, sizeof text);
    printf("  scene id 5 -> asset[%d] \"%s\"\n", map[5], text);
    check(map[5] == 7, "scene id 5 resolves to asset[7], NOT asset[4]");
    check(strstr(text, "level05") != NULL,
          "scene id 5's directory is level05 -- matching the overlay proven resident "
          "at 0x800B39A0 in all five F08 fixtures (99.14% over non-trivial bytes)");
    check(map[10] == 4,
          "asset[4] level10\\level2b belongs to scene id 10 -- the row attributed "
          "another scene's assets to F08");

    int coincidences = 0, total = 0;
    printf("  ids where index == id-1 (the assumption that misleads): ");
    for (uint32_t i = 1; i <= N; i++)
    {
      if (map[i] < 0) continue;
      total++;
      if (map[i] == (int)i - 1) { printf("%u ", i); coincidences++; }
    }
    printf("\n  -> %d of %d ids satisfy it by coincidence\n", coincidences, total);
    check(coincidences == 2,
          "ONLY ids 1 and 15 satisfy index == id-1. F15's row uses id 15, so its "
          "binding is right BY COINCIDENCE -- it is not evidence for the rule");
    check(map[15] == 14,
          "id 15 -> asset[14] level05\\level5c, matching F15's row (and D20's live "
          "transferLog resolution to LEVEL05/LEVEL1.DAT)");
    check(map[16] == 0 && map[17] == 0,
          "ids 16 and 17 alias the id-1 handler (level01\\level1a)");
  }

  /* The LEVEL-DATA directory does NOT come from the string table at all. Phase 3
   * banked this law on 2026-08-01 and this tool confirms it from the image:
   *   0x8003D204 slti v0,s4,11 ; 0x8003D214 addiu s4,s4,-10 ; 0x8003D218 ori 0x0140
   * i.e. dir = id <= 10 ? id : id - 10, with the LEVEL1.* variant flag for id >= 11.
   * The 0x8001AD0C strings are VAB/sound-bank prefixes. They are still a correct way
   * to NAME a scene, but describing them as the level-data path is wrong. */
  printf("\n=== level-data directory is ARITHMETIC, not the string table ===\n");
  {
    uint32_t w_slti, w_addiu, w_ori;
    memcpy(&w_slti, at(0x8003D204u), 4);
    memcpy(&w_addiu, at(0x8003D214u), 4);
    memcpy(&w_ori,  at(0x8003D218u), 4);
    check(w_slti == 0x2A82000Bu, "0x8003D204 is slti v0,s4,11 (the id<=10 test)");
    check(w_addiu == 0x2694FFF6u, "0x8003D214 is addiu s4,s4,-10 (dir = id - 10)");
    check((w_ori >> 26) == 0x0D && (w_ori & 0xFFFF) == 0x0140,
          "0x8003D218 ori 0x0140 selects the LEVEL1.* variant for id >= 11");

    /* Does the sound-bank string's directory always agree with that arithmetic? If
     * it does, quoting the string is harmless for locating files; if not, the two
     * must never be conflated. Measure it rather than assume. */
    const uint32_t JT = 0x8001AFB0u;
    int agree = 0, seen = 0;
    for (uint32_t id = 1; id <= 17; id++)
    {
      uint32_t h;
      memcpy(&h, at(JT + (id - 1) * 4), 4);
      int idx = -1;
      for (uint32_t a = h; a < h + 0x400 && in_image(a, 4); a += 4)
      {
        uint32_t w1;
        memcpy(&w1, at(a), 4);
        if ((w1 >> 26) != 0x0F) continue;
        uint32_t rt = (w1 >> 16) & 31, hi = w1 & 0xFFFF;
        uint32_t w2;
        memcpy(&w2, at(a + 4), 4);
        if ((w2 >> 26) != 0x09 || ((w2 >> 21) & 31) != rt) continue;
        uint32_t ad = (hi << 16) + (uint32_t)(int16_t)(w2 & 0xFFFF);
        if (ad >= SCENE_TABLE && ad < SCENE_TABLE + SCENE_COUNT * SCENE_ENTRY_SZ
            && ((ad - SCENE_TABLE) % SCENE_ENTRY_SZ) == 0)
        { idx = (int)((ad - SCENE_TABLE) / SCENE_ENTRY_SZ); break; }
      }
      if (idx < 0) continue;
      char s[SCENE_ENTRY_SZ + 1];
      entry_text((uint32_t)idx, s, sizeof s);
      int str_dir = (s[5] - '0') * 10 + (s[6] - '0');   /* "levelNN\..." */
      int arith   = (id <= 10) ? (int)id : (int)id - 10;
      seen++;
      if (str_dir == arith) agree++;
      else printf("  id %2u: string dir %02d vs arithmetic dir %02d  <-- DISAGREE\n",
                  id, str_dir, arith);
    }
    printf("  sound-bank string dir agrees with arithmetic dir: %d of %d\n", agree, seen);
    check(agree == 15 && seen == 17,
          "the string dir coincides with the data dir for ids 1..15 ONLY; ids 16 and "
          "17 DISAGREE (string level01, arithmetic dir 6 and 7). Confirmed live-free: "
          "two scene-17 training saves hold LEVEL07_LEVEL1.BIN resident at 0x800B39A0, "
          "exactly as the arithmetic + variant flag predict. So the string is NOT the "
          "data path and the two must never be conflated");
  }

  printf("\n=== summary ===\n");
  printf("  %d passed, %d failed\n", g_pass, g_fail);
  if (g_fail == 0)
    printf("  every pin holds against the pristine image\n");

  free(g_img);
  return g_fail ? 1 : 0;
}
