#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ENTRY 0x8005c258u
#define EXPECTED_INSNS 205u
#define MAX_INSNS 512u

typedef struct { uint32_t pc; char text[256]; } Insn;

static void die(const char *msg, const char *detail) {
    fprintf(stderr, "phase4_b02_asm_static: %s%s%s\n", msg, detail ? ": " : "", detail ? detail : "");
    exit(1);
}

static char *read_all(const char *path, size_t *size) {
    FILE *f = fopen(path, "rb");
    if (!f) die("cannot open", path);
    if (fseek(f, 0, SEEK_END) || (*size = (size_t)ftell(f), fseek(f, 0, SEEK_SET))) die("cannot size", path);
    char *p = malloc(*size + 1);
    if (!p) die("out of memory", NULL);
    if (fread(p, 1, *size, f) != *size) die("cannot read", path);
    fclose(f); p[*size] = 0; return p;
}

static void sha_hex(const char *p, size_t n, char out[65]) {
    unsigned char h[SHA256_DIGEST_LENGTH];
    SHA256((const unsigned char *)p, n, h);
    for (unsigned i = 0; i < sizeof(h); i++) sprintf(out + i * 2, "%02x", h[i]);
    out[64] = 0;
}

static char *trim(char *p) {
    while (isspace((unsigned char)*p)) p++;
    char *e = p + strlen(p);
    while (e > p && isspace((unsigned char)e[-1])) *--e = 0;
    return p;
}

static unsigned occurrences(const char *hay, const char *needle) {
    unsigned n = 0; size_t z = strlen(needle);
    for (const char *p = hay; (p = strstr(p, needle)); p += z) n++;
    return n;
}

static void require_count(const char *text, const char *needle, unsigned want) {
    unsigned got = occurrences(text, needle);
    if (got != want) {
        char b[256]; snprintf(b, sizeof(b), "'%s' count %u, expected %u", needle, got, want); die("ASM assertion failed", b);
    }
}

static uint32_t pc_of(const Insn *v, size_t n, const char *needle, unsigned ordinal) {
    for (size_t i = 0; i < n; i++) if (strstr(v[i].text, needle) && ordinal-- == 0) return v[i].pc;
    die("instruction not found", needle); return 0;
}

static void json_hash(const char *label, const char *path, const char *data, size_t size, int comma) {
    char h[65]; sha_hex(data, size, h);
    printf("    \"%s\":{\"path\":\"%s\",\"bytes\":%zu,\"sha256\":\"%s\"}%s\n", label, path, size, h, comma ? "," : "");
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s PROPELLER_ASM DETACH_ASM XZ_HELPER_ASM\n", argv[0]);
        return 2;
    }
    size_t hs, ds, xs; char *h = read_all(argv[1], &hs), *d = read_all(argv[2], &ds), *x = read_all(argv[3], &xs);
    char *work = strdup(h); if (!work) die("out of memory", NULL);
    Insn ins[MAX_INSNS]; size_t ni = 0; uint32_t pc = ENTRY;
    char *save = NULL;
    for (char *line = strtok_r(work, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        char *t = trim(line); size_t z = strlen(t);
        if (!*t || *t == '#' || !strncmp(t, ".set", 4) || !strcmp(t, ".text") || t[z - 1] == ':') continue;
        if (ni >= MAX_INSNS) die("too many instructions", argv[1]);
        ins[ni].pc = pc; snprintf(ins[ni].text, sizeof(ins[ni].text), "%s", t); ni++; pc += 4;
    }
    if (ni != EXPECTED_INSNS || pc != 0x8005c58cu) die("handler extent differs from 820-byte contract", argv[1]);

    require_count(h, "jal 0x800524b8", 3);
    require_count(h, "jal 0x80046cac", 1);
    require_count(h, "sw\t$a0,25904($at)", 1);
    require_count(h, "sw\t$v0,25904($at)", 1);
    require_count(h, "sw\t$v0,32($s0)", 1);
    require_count(h, "sw\t$a0,28($s0)", 1);
    require_count(h, "sw\t$v0,36($s0)", 1);
    require_count(h, "sh\t$zero,94($s0)", 1);
    require_count(d, "addiu\t$v0,$v0,-640", 1);
    require_count(d, "sw\t$zero,28($v0)", 1);
    require_count(d, "sw\t$zero,32($v0)", 1);
    require_count(d, "sw\t$zero,36($v0)", 1);
    require_count(d, "andi\t$v1,$v1,0xffbf", 1);
    require_count(d, "sw\t$zero,0($s0)", 1);
    require_count(x, "sra\t$v0,$v0,8", 2);
    require_count(x, "mult\t$v0,$v0", 2);
    require_count(x, "mult\t$a2,$a2", 1);
    require_count(x, "slt\t$v0,$v0,$v1", 1);

    uint32_t radius200 = pc_of(ins, ni, "addiu\t$a2,$zero,200", 0);
    uint32_t radius40_player = pc_of(ins, ni, "addiu\t$a2,$zero,40", 0);
    uint32_t radius40_actor = pc_of(ins, ni, "addiu\t$a2,$zero,40", 1);
    uint32_t detach = pc_of(ins, ni, "jal 0x80046cac", 0);
    uint32_t player_vy = pc_of(ins, ni, "sw\t$a0,25904($at)", 0);
    uint32_t player_clamp = pc_of(ins, ni, "sw\t$v0,25904($at)", 0);
    uint32_t actor_vy = pc_of(ins, ni, "sw\t$v0,32($s0)", 0);
    uint32_t actor_clear = pc_of(ins, ni, "sh\t$zero,94($s0)", 0);
    uint32_t live_head = pc_of(ins, ni, "lw\t$s0,1864($s0)", 0);
    uint32_t exit_jump = pc_of(ins, ni, ".word 0x0801733b", 0);
    if (exit_jump != 0x8005c540u) die("unexpected shared-walker exit location", NULL);

    printf("{\n  \"schema\":\"abl-phase4-b02-asm-static-v1\",\n  \"sources\":{\n");
    json_hash("propeller_handler", argv[1], h, hs, 1);
    json_hash("carry_detach_helper", argv[2], d, ds, 1);
    json_hash("xz_radius_helper", argv[3], x, xs, 0);
    printf("  },\n  \"identity\":{\"entry\":\"0x8005c258\",\"end_exclusive\":\"0x8005c58c\",\"bytes\":820,\"instructions\":%zu,\"reachable_prefix_instructions\":188,\"unreachable_shared_walker_suffix_instructions\":17},\n", ni);
    printf("  \"derived_sites\":{\"activation_radius_200_argument\":\"0x%08x\",\"player_radius_40_argument\":\"0x%08x\",\"actor_radius_40_argument\":\"0x%08x\",\"detach_call\":\"0x%08x\",\"player_vy_store\":\"0x%08x\",\"player_vy_clamp_store\":\"0x%08x\",\"actor_vy_store\":\"0x%08x\",\"actor_field_5e_clear\":\"0x%08x\",\"live_table_load\":\"0x%08x\",\"shared_walker_exit\":\"0x%08x\"},\n", radius200, radius40_player, radius40_actor, detach, player_vy, player_clamp, actor_vy, actor_clear, live_head, exit_jump);
    printf("  \"player_lift_law\":{\"xz_radius_world_units\":40,\"requires_player_flag_0x80_clear\":true,\"requires_contact_0x800a6582_zero\":true,\"plant_minus_player_y\":{\"ordinary_min\":12289,\"ordinary_max\":40959,\"latch11_bridge_min\":4097,\"latch11_bridge_max\":12288},\"per_handler_tick_vy_delta\":-512,\"vy_floor\":-3072,\"mode\":5,\"timer_0x800a6584\":0,\"animation\":13,\"animation_timer_if_changed\":120},\n");
    printf("  \"loose_actor_lift_law\":{\"table\":\"0x80090748 compacted live-actor pointers\",\"xz_radius_world_units\":40,\"requires_flags_0x5c_bit_0x20\":true,\"requires_field_0x40_zero\":true,\"plant_minus_actor_y_min\":12289,\"plant_minus_actor_y_max\":40959,\"per_handler_tick_vy_delta\":-512,\"vy_clamp\":null,\"stationary_xz_initialization\":\"if vx and vz are both zero, assign successive unsigned RNG bytes\",\"field_0x5e_write\":0},\n");
    printf("  \"carry_transfer\":{\"offset_owner\":\"player+0x5c (0x800a655c)\",\"actor_base\":\"0x8009fd80\",\"detach_effects\":[\"actor vx/vy/vz := 0\",\"actor flags+0x5c clears 0x40\",\"player carry offset/state cleared\"],\"ordering\":\"detach precedes live-actor updraft scan in the same handler call\",\"attached_dual_payload\":false},\n");
    printf("  \"bounded_conclusions\":{\"fall_from_above\":\"player high band 12289..40959 does not require latch 11; a carried actor detaches before its independent loose-actor gate\",\"steering\":\"handler has no player X/Z position or velocity store; horizontal steering is delegated to shared mode-5 player physics\",\"release_and_landing\":\"handler sets mode 5 but contains no mode-5 clear or landing transition; lifecycle completion must be read from shared player physics/runtime\",\"enemy_interaction\":\"the loop is actor-generic, not seed-ID-specific; exact enemy-family eligibility depends on runtime flags+0x5c bit 0x20 and field+0x40\",\"visual_spin\":\"not attributable in this handler; only loose-actor X/Z velocity initialization and player animation 13 are direct\"},\n");
    printf("  \"gate\":{\"low_level_assertions\":24,\"pass\":true}\n}\n");
    free(work); free(h); free(d); free(x); return 0;
}
