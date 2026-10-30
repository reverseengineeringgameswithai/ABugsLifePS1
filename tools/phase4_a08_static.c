
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { unsigned char *p; size_t n; } blob;

static uint16_t le16(const unsigned char *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}
static uint32_t le32(const unsigned char *p) {
    return (uint32_t)le16(p) | ((uint32_t)le16(p + 2) << 16);
}
static blob read_all(const char *path) {
    FILE *f = fopen(path, "rb");
    blob b = {0};
    long n;
    if (!f) { fprintf(stderr, "%s: %s\n", path, strerror(errno)); exit(2); }
    if (fseek(f, 0, SEEK_END) || (n = ftell(f)) < 0 || fseek(f, 0, SEEK_SET)) {
        fprintf(stderr, "%s: seek failed\n", path); exit(2);
    }
    b.p = malloc((size_t)n + 1);
    if (!b.p || fread(b.p, 1, (size_t)n, f) != (size_t)n) {
        fprintf(stderr, "%s: read failed\n", path); exit(2);
    }
    fclose(f);
    b.n = (size_t)n;
    b.p[b.n] = 0;
    return b;
}
static size_t exe_off(const blob *exe, uint32_t addr) {
    uint32_t load = le32(exe->p + 0x18);
    uint32_t size = le32(exe->p + 0x1c);
    uint64_t delta;
    if (addr < load) { fprintf(stderr, "address below load\n"); exit(2); }
    delta = (uint64_t)addr - load;
    if (delta + 4 > size || 0x800u + delta + 4 > exe->n) {
        fprintf(stderr, "address 0x%08" PRIx32 " out of EXE\n", addr); exit(2);
    }
    return 0x800u + (size_t)delta;
}
static uint32_t word_at(const blob *exe, uint32_t addr) {
    return le32(exe->p + exe_off(exe, addr));
}
static int ordered(const blob *b, const char *name,
                   const char *const *need, size_t count, int noisy) {
    const char *p = (const char *)b->p;
    for (size_t i = 0; i < count; i++) {
        p = strstr(p, need[i]);
        if (!p) {
            if (noisy) fprintf(stderr, "%s: missing ordered token: %s\n", name, need[i]);
            return 0;
        }
        p += strlen(need[i]);
    }
    return 1;
}
static int all_tokens(const blob *b, const char *name,
                      const char *const *need, size_t count, int noisy) {
    for (size_t i = 0; i < count; i++) {
        if (!strstr((const char *)b->p, need[i])) {
            if (noisy) fprintf(stderr, "%s: missing token: %s\n", name, need[i]);
            return 0;
        }
    }
    return 1;
}
static int require_word(const blob *exe, uint32_t addr, uint32_t expected,
                        const char *name) {
    uint32_t got = word_at(exe, addr);
    if (got != expected) {
        fprintf(stderr, "%s @0x%08" PRIx32 ": got 0x%08" PRIx32
                        ", expected 0x%08" PRIx32 "\n",
                name, addr, got, expected);
        return 0;
    }
    return 1;
}
static int16_t s16_at(const blob *exe, uint32_t addr) {
    return (int16_t)le16(exe->p + exe_off(exe, addr));
}
static uint8_t u8_at(const blob *exe, uint32_t addr) {
    return exe->p[exe_off(exe, addr)];
}

int main(int argc, char **argv) {
    const char *root = argc > 1 ? argv[1] : ".";
    char path[512];
    blob exe, dispatch, aim, spawn, update, homing, player;
    int ok = 1;
    int c_dispatch, c_aim, c_spawn, c_update, c_homing, c_player;
    static const char *const dispatch_need[] = {
        "lbu\t$v1,151($s0)", ".word 0x0c011b49",
        "addiu\t$s1,$zero,2", "addiu\t$s1,$zero,5",
        "addiu\t$s1,$zero,8", "addiu\t$s1,$zero,11",
        "addiu\t$s1,$zero,45", "addiu\t$t0,$zero,-2048",
        "addiu\t$v0,$v0,1", "sb\t$v0,150($s0)",
        "sw\t$v0,16($sp)", "sw\t$v0,24($sp)",
        "sw\t$s1,28($sp)", ".word 0x0c016838"
    };
    static const char *const aim_need[] = {
        "0x80046d88", "andi v0, v1, 1", "andi v0, v1, 0xa0",
        "0x80046e6c", "jal fcn.80060ae4", "0x80046e94",
        "0x80046ecc", "0x80046f28", "jal fcn.80060154",
        "0x80046f4c", "slti v0, s2, 0x1f", "0x80046f58",
        "0x80046f90", "jal fcn.80060ae4", "0x80046fb8",
        "jal fcn.80060154", "0x8004702c", "0x80047068"
    };
    static const char *const spawn_need[] = {
        "sw\t$a0,0($s0)", "sw\t$a1,4($s0)", "sw\t$a2,8($s0)",
        "sw\t$a3,12($s0)", "sw\t$t1,16($s0)", "sw\t$t2,20($s0)",
        "sw\t$t3,24($s0)", "lbu\t$v0,16($a1)", "sb\t$v0,51($s0)",
        "lhu\t$v0,2($a1)", "sh\t$v0,34($s0)"
    };
    static const char *const update_need[] = {
        "lh\t$v0,0($s0)", "addiu\t$v1,$v1,-1", "sh\t$v1,0($s0)",
        "andi\t$v0,$v0,0x8", "lw\t$v1,-18($s0)",
        ".word 0x0c0182b9", "sra\t$v1,$a2,2",
        "sw\t$v1,-10($s0)", "addiu\t$a1,$zero,1024",
        "addiu\t$a1,$zero,-1024", "sw\t$v0,-30($s0)",
        "sra\t$v1,$v1,19", "sw\t$v1,-22($s0)",
        "sra\t$v0,$v0,19", "sw\t$v0,-14($s0)",
        "addu\t$v0,$v0,$a0", "addu\t$v1,$v1,$a1",
        "sw\t$v0,-30($s0)", "sw\t$v1,-18($s0)",
        "addu\t$v0,$v0,$v1", "sw\t$v0,0($s3)",
        "addu\t$v1,$v1,$a0", "sw\t$v1,-26($s0)",
        "sh\t$zero,0($s0)", "lbu\t$v0,16($s0)",
        "andi\t$v0,$v0,0xa0", "sh\t$zero,0($s0)",
        "addiu\t$v0,$zero,-1", "sh\t$v0,0($s0)",
        ".word 0x0c01654f"
    };
    static const char *const homing_need[] = {
        "andi $v0, $v1, 1", "andi $v0, $v1, 0xa0",
        "sra  $v0, $v0, 5", "sra  $v0, $v0, 5",
        "addu $s1, $a0, $zero", "sw   $s1, 0x10($sp)",
        "addiu $v0, $zero, 0x30", ".word 0x0c016838",
        "addiu $v0, $zero, 0x10", ".word 0x0c016838",
        "addiu $v0, $zero, 0x44", ".word 0x0c016838",
        "sh   $v0, 0x22($s0)", "sh   $v0, 0x2c($s0)"
    };
    static const char *const player_need[] = {
        "lh\t$v1,134($s1)", "addiu\t$v0,$zero,10",
        "bne\t$v1,$v0,.L_8004909c", ".word 0x0c011c2b"
    };
    static const unsigned types[] = {2, 5, 8, 11, 16, 45, 48};
    static const unsigned cleanup_subtypes[] = {1, 2, 3, 4, 5, 8, 9};

    snprintf(path, sizeof(path), "%s/SCUS_942.88", root);
    exe = read_all(path);
    if (exe.n < 0x800 || memcmp(exe.p, "PS-X EXE", 8) != 0) {
        fprintf(stderr, "not a PS-X EXE\n"); return 2;
    }
#define LOAD(member, rel) do { snprintf(path, sizeof(path), "%s/%s", root, rel); member = read_all(path); } while (0)
    LOAD(dispatch, "asm/hand_written/800470ac_berry_throw_dispatch.s");
    LOAD(aim, "asm/nonmatchings/resident/80046d24.s");
    LOAD(spawn, "asm/hand_written/8005a0f0_contact_object_spawn.s");
    LOAD(update, "asm/hand_written/8005a308_berry_projectile_update.s");
    LOAD(homing, "asm/hand_written/8005743c_berry_homing_target_acquire.s");
    LOAD(player, "asm/hand_written/80048138_player_vertical_update.s");
#undef LOAD

    c_dispatch = ordered(&dispatch, "dispatch", dispatch_need, sizeof(dispatch_need)/sizeof(dispatch_need[0]), 1);
    c_aim = ordered(&aim, "aim", aim_need, sizeof(aim_need)/sizeof(aim_need[0]), 1);
    c_spawn = all_tokens(&spawn, "spawn", spawn_need, sizeof(spawn_need)/sizeof(spawn_need[0]), 1);
    c_update = all_tokens(&update, "update", update_need, sizeof(update_need)/sizeof(update_need[0]), 1);
    c_homing = all_tokens(&homing, "homing", homing_need, sizeof(homing_need)/sizeof(homing_need[0]), 1);
    c_player = ordered(&player, "player gate", player_need, sizeof(player_need)/sizeof(player_need[0]), 1);
    ok &= c_dispatch && c_aim && c_spawn && c_update && c_homing && c_player;
    ok &= require_word(&exe, 0x80047160u, 0x0c011b49u, "aim call");
    ok &= require_word(&exe, 0x80047170u, 0x92030097u, "equip read");
    ok &= require_word(&exe, 0x8004724cu, 0x0c016838u, "spawn call");
    ok &= require_word(&exe, 0x80049094u, 0x0c011c2bu, "state-10 throw call");

    printf("{\n");
    printf("  \"schema\": \"phase4_a08_static_v1\",\n");
    printf("  \"pristine_exe\": {\"load_address\": \"0x%08" PRIx32 "\", \"text_size\": %" PRIu32 "},\n",
           le32(exe.p + 0x18), le32(exe.p + 0x1c));
    printf("  \"asm_checks\": {\"dispatch\": %s, \"aim\": %s, \"spawn\": %s, \"update\": %s, \"homing\": %s, \"player_state_gate\": %s},\n",
           c_dispatch?"true":"false", c_aim?"true":"false", c_spawn?"true":"false",
           c_update?"true":"false", c_homing?"true":"false", c_player?"true":"false");
    printf("  \"dispatch_jump_table\": [\n");
    for (unsigned i = 0; i < 5; i++)
        printf("    {\"equip_index\": %u, \"target\": \"0x%08" PRIx32 "\"}%s\n",
               i, word_at(&exe, 0x8001b1c0u+i*4u), i==4?"":",");
    printf("  ],\n  \"parameter_rows\": [\n");
    for (size_t i = 0; i < sizeof(types)/sizeof(types[0]); i++) {
        uint32_t a = 0x8007941cu + types[i]*0x14u;
        printf("    {\"type\": %u, \"class\": %d, \"timer\": %d, \"model\": %d, \"k256\": %d, \"unk8\": %d, \"unka\": %d, \"sub_index\": %d, \"unke\": %d, \"flags\": %u}%s\n",
               types[i], s16_at(&exe,a), s16_at(&exe,a+2), s16_at(&exe,a+4),
               s16_at(&exe,a+6), s16_at(&exe,a+8), s16_at(&exe,a+10),
               s16_at(&exe,a+12), s16_at(&exe,a+14), u8_at(&exe,a+16),
               i+1==sizeof(types)/sizeof(types[0])?"":",");
    }
    printf("  ],\n  \"cleanup_dispatch\": [\n");
    for (size_t i = 0; i < sizeof(cleanup_subtypes)/sizeof(cleanup_subtypes[0]); i++) {
        unsigned sub = cleanup_subtypes[i];
        printf("    {\"sub_index\": %u, \"target\": \"0x%08" PRIx32 "\"}%s\n",
               sub, word_at(&exe, 0x8001b790u + (sub-1u)*4u),
               i+1==sizeof(cleanup_subtypes)/sizeof(cleanup_subtypes[0])?"":",");
    }
    printf("  ],\n");
    printf("  \"admission\": {\"input\": \"new Square edge (active-low bit 0x8000)\", \"writes_state\": 18, \"constructor_state\": 10, \"denied_when\": [\"action_state >= 7\", \"owned_throw_count >= 4\", \"player+0xa3 != 0\", \"carried_object_gate_0x800a657a != 0\", \"mode+0x88 in {8,10,13,17}\", \"latch+0x9e >= 12\", \"player+0x84 != 0\"]},\n");
    printf("  \"throw_law\": {\"spawn_offset\": {\"x\": \"player_x + (sin(heading+1024)>>2)\", \"y\": \"player_y-12800\", \"z\": \"player_z + (sin(heading+2048)>>2)\"}, \"straight_types\": [2,5,11], \"homing_primary_types\": [8,45], \"fallback\": {\"heading\": \"player_heading\", \"vel_y\": -2048}, \"spawn_velocity\": {\"vel_x\": \"3*(sin(heading)>>4)\", \"vel_z\": \"3*(sin(heading+1024)>>4)\", \"gravity\": 128}},\n");
    printf("  \"aim_law\": {\"eligible\": \"enemy state mask 0x1 set and mask 0xa0 clear\", \"selection\": \"nearest squared XZ distance inside heading cone\", \"lead_horizon\": \"min(floor(sqrt(distance2)/96),30)\", \"vertical_clamp\": {\"normal_min\": -3072, \"far_min\": -2560, \"max\": 1536}},\n");
    printf("  \"straight_recurrence\": {\"pos_x\": \"x+vx\", \"pos_y\": \"y+vy\", \"pos_z\": \"z+vz\", \"vel_y\": \"vy+gravity\"},\n");
    printf("  \"homing_law\": {\"turn\": \"heading += signed_quarter_error modulo 4096\", \"vertical_seek_clamp\": [-1024,1024], \"velocity_scale\": \"sin/8\", \"target_selection\": \"nearest valid target in XZ\"},\n");
    printf("  \"ownership_counter\": {\"address\": \"0x800a6596\", \"admission_limit\": 4, \"increment\": \"one per accepted throw at 0x800471dc\", \"straight_terminal_subtypes\": [1,2,4], \"homing_transfer\": {\"type8\": \"child16 or fallback subtype3\", \"type45\": \"child48 or fallback subtype8\"}, \"terminal_decrement_subtypes\": [1,2,3,4,8]},\n");
    printf("  \"retirement\": [\"timer_zero\", \"floor_intersection\", \"far_distance\", \"flags_without_0xa0\", \"target_hit_or_invalid\"],\n");
    printf("  \"cleanup_sequence\": \"timer 0 -> -1 -> 0 plus 0x8005953c\",\n");
    printf("  \"static_gate\": \"%s\"\n}\n", ok?"PASS":"FAIL");
    return ok?0:1;
}
