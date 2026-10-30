/*
 * Recompilable near-match seed for retail player_vertical_update @ 0x80048138.
 *
 * This is C-origin evidence, not the already-exact handwritten-ASM build unit.
 * It was recovered from the pristine instruction stream with m2c, then repaired
 * for load widths, computed table accesses, absolute globals, and the original
 * long-lived register roles. The retained compiler residual is measured by
 * tools/phase4_f01_source_closure.py; this file is not linked into the MOD.
 *
 * Block map (end-exclusive):
 *   80048138..800483b0  controller-history / spin recognition
 *   800483b0..80048514  movement parameters / status input
 *   80048514..80048b20  timers and special vertical modes
 *   80048b20..80048e9c  jump, dive, and landing transitions
 *   80048e9c..80049544  horizontal steering and velocity projection
 *   80049544..800498ac  collision, fall recovery, and epilogue
 */
typedef int s32; typedef unsigned int u32; typedef unsigned char u8; typedef signed char s8; typedef short s16; typedef unsigned short u16; typedef long s64; typedef unsigned long u64; typedef float f32;
#define NULL 0

/* Retail mixes $gp-relative and absolute globals even under the pinned -G0
 * contract. Express the five $gp-owned objects as C lvalues based on the ABI
 * global-pointer register; the neighbouring externs below remain absolute. */
register u8 *abl_gp asm ("$28");
#define g_8008229a (*(u16 *)(abl_gp + 0x502))
#define g_800823b0 (*(s16 *)(abl_gp + 0x618))
#define g_800823d4 (*(s32 *)(abl_gp + 0x63C))
#define g_80082434 (*(s32 *)(abl_gp + 0x69C))
#define g_800824d4 (*(s32 *)(abl_gp + 0x73C))
extern s16 g_80082488;
typedef struct SelectedActorA05 {
    char pad00[0x1c];
    s32 velocity_x;
    s32 velocity_y;
    s32 velocity_z;
    char pad28[0x34];
    u16 flags;
} SelectedActorA05;
extern s32 g_80082294;
extern s32 g_800822b4;
extern s32 g_8008237c;
extern s16 g_80082380;
extern s16 g_800823a0;
extern u16 g_80082412;
extern s32 g_8008246c;
extern s16 g_80082470;
extern s32 g_80082504;
extern u8 g_800910a3;
extern s32 g_800a1e04;
extern s32 g_800a1e1c;
extern s32 g_800a1e34;
extern s32 g_800a6500;
extern s32 g_800a6504;
extern s32 g_800a6508;
extern s32 g_800a6538;
extern s32 g_800a653c;
extern s32 g_800a6548;
extern s32 g_800a655c;
extern s16 g_800a657a;
extern s16 g_800a6588;
extern u16 g_800a6590;
extern s16 g_800a6594;
extern s16 g_800a659e;
extern u8 g_800a65a0;
extern s8 g_800a65a3;
extern s32 g_800b473c;
extern s16 g_80077304[];
extern u16 g_800894d0[];
typedef struct PlayerA05 {
    /* 0x00 */ s32 x;                            /* inferred */
    /* 0x04 */ s32 y;                            /* inferred */
    /* 0x08 */ s32 z;                            /* inferred */
    /* 0x0C */ char padC[4];
    /* 0x10 */ s32 previous_x;                           /* inferred */
    /* 0x14 */ s32 previous_y;                           /* inferred */
    /* 0x18 */ s32 previous_z;                           /* inferred */
    /* 0x1C */ char pad1C[4];
    /* 0x20 */ s32 heading;                           /* inferred */
    /* 0x24 */ char pad24[4];
    /* 0x28 */ s32 target_heading;                           /* inferred */
    /* 0x2C */ s32 velocity_x;                           /* inferred */
    /* 0x30 */ s32 velocity_y;                           /* inferred */
    /* 0x34 */ s32 velocity_z;                           /* inferred */
    /* 0x38 */ s32 forward_component;                           /* inferred */
    /* 0x3C */ s32 lateral_component;                           /* inferred */
    /* 0x40 */ char pad40[8];                       /* maybe part of unk3C[3]? */
    /* 0x48 */ s32 floor_y;                           /* inferred */
    /* 0x4C */ char pad4C[0x10];                    /* maybe part of unk48[5]? */
    /* 0x5C */ s32 selected_actor_offset;                           /* inferred */
    /* 0x60 */ char pad60[0x1A];                    /* maybe part of unk5C[7]? */
    /* 0x7A */ s16 action_timer;                           /* inferred */
    /* 0x7C */ s16 timer_7c;                           /* inferred */
    /* 0x7E */ s16 timer_7e;                           /* inferred */
    /* 0x80 */ u16 air_state;                           /* inferred */
    /* 0x82 */ s16 grounded;                           /* inferred */
    /* 0x84 */ s16 dive_phase;                           /* inferred */
    /* 0x86 */ s16 field_86;                  /* width known; semantics unknown */
    /* 0x88 */ s16 animation_selector;                           /* inferred */
    /* 0x8A */ char pad8A[2];
    /* 0x8C */ s16 indexed_attachment;                           /* inferred */
    /* 0x8E */ char pad8E[2];
    /* 0x90 */ u16 flags_90;                           /* inferred */
    /* 0x92 */ s16 timer_92;                           /* inferred */
    /* 0x94 */ char pad94[2];
    /* 0x96 */ u8 field_96;                   /* width known; semantics unknown */
    /* 0x97 */ u8 field_97;                   /* width known; semantics unknown */
    /* 0x98 */ char pad98[6];
    /* 0x9E */ s16 queued_action;                           /* inferred */
    /* 0xA0 */ char padA0[3];                       /* maybe part of unk9E[2]? */
    /* 0xA3 */ u8 seed_action_mode;                            /* inferred */
    /* 0xA4 */ char padA4[0xF];                     /* maybe part of unkA3[0x10]? */
} PlayerA05;                                         /* fields used through +0xA3 */

int sub_8003633c(PlayerA05 *, s32 *, s16 *, int);   /* extern */
s32 sub_80037a38(PlayerA05 *);                  /* extern */
int sub_800470ac(PlayerA05 *);                    /* extern */
int sub_80047284();                                   /* extern */
int sub_8004a700(int, int, int *, int);                       /* extern */
int sub_8005044c(int, int);                               /* extern */
int sub_80050994(int, int);                               /* extern */
int sub_80059e44(s32, s32, s32, int, s32);              /* extern */
int sub_8005a0e0(s32, s32, s32, s32, s32, s32, s32, s32); /* extern */
int sub_800370c8(s32, s32, s32, int);                   /* static */
s32 sub_80037dac(PlayerA05 *, s32 *);           /* static */
int sub_80041ac4(s32, s32);                           /* static */
int sub_80042428();                                   /* static */
int sub_80047ebc(s32 *);                              /* static */
int sub_8005f4ec(int);                                  /* static */

typedef struct PlayerVerticalCompilerFrame {
    s32 sp20;
    char pad04[4];
    s32 sp28;
    s32 sp2C;
    s32 sp30;
    char pad14[4];
    s32 sp38;
    char pad1C[4];
    s32 sp40;
    char pad24[4];
    s32 sp48;
    char pad2C[4];
    u16 sp50;
    char pad32[6];
    u16 sp58;
    char pad3A[0x26];
} PlayerVerticalCompilerFrame;

#define sp20 frame.sp20
#define sp28 frame.sp28
#define sp2C frame.sp2C
#define sp30 frame.sp30
#define sp38 frame.sp38
#define sp40 frame.sp40
#define sp48 frame.sp48
#define sp50 frame.sp50
#define sp58 frame.sp58

void player_vertical_update(PlayerA05 *player) {
    /* Exact retail stack map: the struct begins above the 16-byte outgoing
     * argument area and ends immediately before the callee-save block. */
    volatile PlayerVerticalCompilerFrame frame;
    register s32 init_t1 asm ("$9");
    s32 turn_cap;
    register s16 *var_a1 asm ("$5");
    register s16 *var_a2 asm ("$6");
    register s16 *history_base asm ("$7");
    s16 temp_a0_6;
    s16 temp_v0_10;
    s16 temp_v0_12;
    s16 temp_v0_16;
    s16 temp_v0_18;
    s16 temp_v0_7;
    s16 temp_v0_8;
    s16 temp_v0_9;
    s16 temp_v1_11;
    s16 temp_v1_3;
    s16 temp_v1_8;
    register s32 var_s2 asm ("$18"); /* original long-lived $s2 role */
    s32 temp_a0_10;
    s32 temp_a0_11;
    s32 temp_a0_12;
    s32 temp_a0_2;
    s32 temp_a0_7;
    s32 temp_a0_8;
    s32 temp_a0_9;
    s32 temp_a1;
    s32 temp_a1_2;
    s32 temp_a1_3;
    s32 temp_a1_4;
    s32 temp_a2;
    s32 temp_a3_2;
    s32 temp_s2;
    s32 temp_s3;
    s32 temp_s4;
    s32 temp_v0_11;
    s32 temp_v0_13;
    s32 temp_v0_14;
    s32 temp_v0_15;
    s32 temp_v0_17;
    s32 temp_v0_19;
    s32 temp_v0_20;
    s32 temp_v0_21;
    s32 temp_v0_22;
    s32 temp_v0_23;
    s32 temp_v1;
    s32 temp_v1_13;
    s32 temp_v1_14;
    s32 temp_v1_15;
    s32 temp_v1_16;
    s32 temp_v1_17;
    s32 temp_v1_2;
    s32 temp_v1_6;
    s32 temp_v1_9;
    register s32 var_a0 asm ("$4");
    s32 var_a0_2;
    s32 var_a0_3;
    register s32 var_s0 asm ("$16");
    s32 var_s0_2;
    s32 var_s2_3;
    s32 var_s2_4;
    s32 var_s2_5;
    s32 var_s2_6;
    register s32 var_s3 asm ("$19");
    s32 var_s3_2;
    s32 var_s4;
    register s32 var_s4_2 asm ("$20");
    register s32 var_s6 asm ("$22");
    register s32 var_s7 asm ("$23");
    s32 var_v0_11;
    s32 var_v0_12;
    s32 var_v0_13;
    s32 var_v0_14;
    s32 var_v0_15;
    s32 var_v0_16;
    s32 var_v0_18;
    s32 var_v0_4;
    s32 var_v0_5;
    s32 var_v0_6;
    s32 var_v0_7;
    s32 var_v0_8;
    s32 var_v0_9;
    s32 var_v1;
    s32 var_v1_2;
    u16 *var_s2_2;
    u16 temp_a0_3;
    u16 temp_a0_4;
    u16 temp_a3;
    u16 temp_v0_3;
    u16 temp_v1_10;
    u16 temp_v1_12;
    u16 temp_v1_4;
    u16 temp_v1_5;
    u16 temp_v1_7;
    u16 var_v0_10;
    u16 var_v0_17;
    u16 var_v0_2;
    register u32 var_s5 asm ("$21");
    u32 var_v0_3;
    u8 temp_a0_5;
    u8 temp_v1_18;
    SelectedActorA05 *temp_v0_6;

    var_s7 = 0;
    var_s5 = 0x700;
    init_t1 = 0x800;
    sp30 = init_t1;
    sp58 = 0;
    init_t1 = 0x50;
    sp38 = init_t1;
    var_s3 = -0xC00;
    if (player->flags_90 & 0x20) {
        var_s3 = -0xEC0;
    }
    init_t1 = 0x100;
    var_s6 = 0x40;
    {
        register s32 temp_a0 asm ("$4");
        register s32 previous_input asm ("$2");
        register s32 input_mask asm ("$3");
        register s32 history_index asm ("$2");
        register s32 history_offset asm ("$3");

        temp_a0 = g_80082488;
        previous_input = g_80082380;
        turn_cap = 0x400;
        sp40 = init_t1;
        sp50 = 0;
        sp48 = 0;
        input_mask = temp_a0;
        if ((temp_a0 != previous_input) &&
                ((previous_input = input_mask & 0xF0) != 0)) {
            if (temp_a0 == 0x20) {
                goto block_10;
            }
            if (temp_a0 >= 0x21) {
                goto block_check_40;
            }
            if (temp_a0 == 0x10) {
                goto block_10;
            }
            goto block_11;
block_check_40:
            if (temp_a0 == var_s6) {
                goto block_10;
            }
            if (temp_a0 != 0x80) {
                goto block_11;
            }
block_10:
            history_index = g_800823b0;
            temp_a0 = (u16) g_80082488;
            g_8008229a = 0U;
            history_offset = history_index * 2;
            history_index += 1;
            g_800823b0 = (s16) history_index;
            history_index = (s16) history_index;
            *(u16 *)((u8 *)g_800894d0 + history_offset) = (u16) temp_a0;
            history_index = history_index < 8;
            goto block_13;
        }
block_11:
        temp_v0_3 = g_8008229a + 1;
        g_8008229a = temp_v0_3;
        if ((s16) temp_v0_3 == 0x14) {
            history_index = g_800823b0;
            g_8008229a = 0U;
            history_offset = history_index * 2;
            history_index += 1;
            g_800823b0 = (s16) history_index;
            history_index = (s16) history_index;
            history_index = history_index < 8;
            *(u16 *)((u8 *)g_800894d0 + history_offset) = 0;
block_13:
            if (history_index == 0) {
                g_800823b0 = 0;
            }
        }
    }
    var_s2 = g_800823b0;
    var_a0 = 0;
    var_s0 = 0;
    var_a2 = g_80077304;
    history_base = (s16 *)g_800894d0;
    var_a1 = history_base + var_s2;
    do {
        if (*var_a1 == *var_a2) {
            var_a0 += 1;
        }
        var_s2 += 1;
        var_a1 += 1;
        if (var_s2 >= 8) {
            var_a1 = history_base;
            var_s2 = 0;
        }
        var_s0 += 1;
        var_a2 += 1;
    } while (var_s0 < 8);
    if ((var_a0 == 8) && !(g_800a6590 & 0x80)) {
        if (g_800a6588 != 0xD) {
            g_80082294 = 0x78;
        }
        temp_v1 = g_800a655c;
        if (temp_v1 > 0) {
            temp_v0_6 = (SelectedActorA05 *)(temp_v1 + 0x8009FD80);
            temp_v0_6->velocity_x = 0;
            temp_v0_6->velocity_y = 0;
            temp_v0_6->velocity_z = 0;
            temp_v0_6->flags = (u16) (temp_v0_6->flags & 0xFFBF);
        }
        sub_80041a74();
        g_800a657a = 0;
        g_800a655c = 0;
        g_800a65a3 = 0;
        g_800a6588 = 0xD;
        g_800a659e = 0;
    }
    if ((g_800a6548 - g_800a6504) < 0x400) {
        if (g_800a6588 == 0xD) {
            sp40 = 0x40;
        }
    } else {
        var_s6 = 0x80;
    }
    if (player->flags_90 & 0x40) {
        temp_a0_2 = player->floor_y - player->y;
        if (temp_a0_2 < 0x3000) {
            temp_v1_2 = player->velocity_y;
            if (temp_v1_2 >= -0x3FF) {
                if ((temp_v1_2 <= 0) || (var_s6 = 0x100, ((temp_a0_2 < 0x800) != 0))) {
                    var_s6 = 0x100;
                    var_s5 = 0x200;
                } else {
                    var_s5 = 0;
                }
            }
        }
    }
    if (g_80082504 != 8) {
        sub_80047284();
    }
    if (player->seed_action_mode != 0) {
        var_s5 = 0x480;
    }
    temp_a0_3 = (u16) g_80082488;
    if (temp_a0_3 & 0x300) {
        var_s5 = 0x300;
    }
    if (player->action_timer == 0xC) {
        var_s6 = 2;
        sp40 = 8;
        var_s5 = 0;
    }
    if (temp_a0_3 & 1) {
        sub_800503fc((void *)0x800B0188);
        sub_800503fc((void *)0x800B018C);
        sub_800503fc((void *)0x800B0190);
        sub_800503fc((void *)0x800B0194);
    }
    if (player->field_97 == 3) {
        sub_800503fc((void *)0x800B0198);
    }
    if ((g_80082470 != 0) && (g_800823a0 == 0) && (player->timer_92 > 0)) {
        player->timer_92 = 0x22;
    }
    temp_v1_3 = player->timer_92;
    player->flags_90 &= 0xFFFE;
    if (temp_v1_3 > 0) {
        player->timer_92 = temp_v1_3 - 1;
        if (player->grounded != 0) {
            player->flags_90 &= 0xFFFD;
        }
        temp_v1_4 = player->flags_90;
        if (temp_v1_4 & 2) {
            sp40 = 0;
            var_s6 = 0;
        }
        if ((g_800910a3 == 0) && (player->timer_92 < 0x23)) {
            player->flags_90 = temp_v1_4 | 1;
        }
    }
    temp_v0_7 = player->timer_92;
    if (temp_v0_7 < 0) {
        player->timer_92 = temp_v0_7 + 1;
        if (player->grounded != 0) {
            player->flags_90 &= 0xFFFD;
        }
        if (player->flags_90 & 2) {
            sp40 = 0;
            var_s6 = 0;
        }
    }
    temp_v1_5 = player->flags_90;
    if (temp_v1_5 & 0x80) {
        player->flags_90 = temp_v1_5 | 1;
        var_s5 = 0x300;
        var_s7 = 3;
    }
    temp_v0_8 = player->timer_7e;
    if (temp_v0_8 > 0) {
        player->timer_7e = temp_v0_8 - 1;
    }
    temp_v0_9 = player->timer_7c;
    if (temp_v0_9 > 0) {
        temp_v0_10 = temp_v0_9 - 1;
        player->timer_7c = temp_v0_10;
        if ((temp_v0_10 << 0x10) != 0) {
            player->flags_90 = 1;
            player->animation_selector = 0xA;
            player->velocity_x = 0;
            player->velocity_y = 0;
            player->velocity_z = 0;
            player->forward_component = 0;
            player->lateral_component = 0;
        } else {
            player->animation_selector = 0xA;
            player->air_state = 5;
            player->flags_90 = 0;
            player->grounded = 0;
            player->dive_phase = 0;
            player->velocity_y = -0x2000;
            sub_8005044c(0x27, 0);
            sub_8005044c(0x10, 0);
            goto block_76;
        }
    } else {
block_76:
        if (player->queued_action == 0xB) {
            var_s7 = 3;
            if (player->grounded != 0) {
                player->queued_action = 0;
                goto block_83;
            }
            temp_v1_6 = player->velocity_y;
            if (temp_v1_6 < 0x15E) {
                player->velocity_y = temp_v1_6 + 0x100;
            } else {
                player->velocity_y = 0x15E;
            }
            goto block_166;
        }
block_83:
        if ((player->queued_action == 0xC) && (player->velocity_y >= 0x201)) {
            player->velocity_y = 0x200;
        }
        if ((g_80082504 == 8) && (g_800a6594 >= 0)) {
            var_s5 = 0xA00 - ((s32) (player->floor_y - player->y) >> 5);
            g_80082488 = (s16) ((u16) g_80082488 & 0xF0FF);
            if (var_s5 >= 0xC01U) {
                var_s5 = 0x800;
            }
            sp30 = 0xF00;
            temp_v0_11 = g_800b473c;
            var_s6 = 0x20;
            sp40 = 0x100;
            if (temp_v0_11 == 0) {
                sp38 = 0x40;
            } else {
                sp38 = temp_v0_11;
                var_s5 = 0xF00;
            }
            var_s7 = -2;
            g_8008237c = 0x7FFF;
            temp_v0_12 = (u16) g_80082488 | 0x10;
            temp_a0_4 = g_80082412 | 0x10;
            g_80082412 = temp_a0_4;
            g_80082488 = temp_v0_12;
            g_80082488 = (s16) (temp_v0_12 & ~0x40);
            g_80082412 = (u16) (temp_a0_4 & ~0x40);
            var_s4 = 0x1000;
            if (temp_v0_12 & 0x4000) {
                var_s4 = 0xC000;
            }
            if (player->timer_92 >= 0x24) {
                var_s4 = 0xC000;
            }
            if ((player->floor_y - var_s4) < player->y) {
                temp_v0_13 = player->velocity_y - 0x180;
                player->velocity_y = temp_v0_13;
                if (temp_v0_13 < -0x600) {
                    player->velocity_y = -0x600;
                }
            } else {
                temp_v0_14 = player->velocity_y + 0x180;
                player->velocity_y = temp_v0_14;
                if (temp_v0_14 >= 0x601) {
                    player->velocity_y = 0x600;
                }
            }
            player->grounded = 0;
            player->animation_selector = 4;
            goto block_166;
        }
        if (player->indexed_attachment == 0) {
            temp_v1_7 = player->air_state;
            if (((u32) (temp_v1_7 - 1) < 2U) || ((s16) temp_v1_7 == 6)) {
                sub_80041ac4(0, 0);
            }
            if (player->indexed_attachment != 0) {
                goto block_109;
            }
            temp_a0_5 = player->seed_action_mode;
            if (temp_a0_5 != 0xE) {
                temp_v1_8 = (s16) player->air_state;
                var_s4_2 = player->velocity_y;
                if (temp_v1_8 == 4) {
                    sp48 = player->grounded != 0;
                }
                if (((u16) g_80082488 & 0x4000) && (temp_a0_5 == 0)) {
                    if ((temp_v1_8 != 1) && (temp_v1_8 < 4)) {
                        if (((player->grounded != 0) || (((player->floor_y - player->y) < 0x400) && (g_80082434 == 0))) && (player->animation_selector != 8)) {
                            var_s4_2 = var_s3;
                            player->air_state = 1;
                            player->grounded = 0;
                            player->animation_selector = 3;
                            if (player->flags_90 & 0x80) {
                                sub_8005f4ec(0x800A1DFC);
                                player->flags_90 &= 0xFF7E;
                                g_800a1e1c = -0x800;
                                temp_v1_9 = g_800a1e04 - 0x1000;
                                g_800a1e04 = temp_v1_9;
                                temp_v0_15 = player->floor_y;
                                g_800a1e34 = temp_v0_15;
                                if (temp_v0_15 < temp_v1_9) {
                                    g_800a1e34 = temp_v1_9;
                                }
                                sub_8004c10c((void *)0x800A1DFC, 2, 0x10);
                            }
                        } else if ((s16) player->air_state == 2) {
                            var_v0_2 = 3;
                            if ((player->floor_y - player->y) >= 0x2001) {
                                sub_8005044c(0x1B, 0);
                                player->dive_phase = 0xA;
                                player->air_state = 4;
                                if (player->velocity_y >= 0x101) {
                                    player->animation_selector = 7;
                                } else {
                                    player->animation_selector = 2;
                                }
                            } else {
                                goto block_160;
                            }
                        }
                    } else {
                        var_v0_2 = 5;
                        if (player->grounded == 0) {
                            if ((s16) player->air_state == 6) {
                                player->air_state = 3;
                            }
                        } else {
                            goto block_160;
                        }
                    }
                } else {
                    if (player->grounded != 0) {
                        player->air_state = 0;
                    }
                    if ((s16) player->air_state == 1) {
                        if (var_s4_2 < 0) {
                            var_v0_3 = (u32) var_s4_2 >> 0x1F;
                            if (var_s4_2 < -0x320) {
                                var_s4_2 += 0x180;
                                var_v0_3 = (u32) var_s4_2 >> 0x1F;
                            }
                            var_s4_2 = ((s32) (var_s4_2 + var_v0_3) >> 1) - 0x100;
                        }
                        player->air_state = 2;
                    }
                    var_v0_2 = 6;
                    if ((s16) player->air_state == 5) {
block_160:
                        player->air_state = var_v0_2;
                    }
                }
                var_v0_4 = var_s4_2 < 0x1001;
                if (player->grounded == 0) {
                    var_s4_2 += 0x100;
                    var_v0_4 = var_s4_2 < 0x1001;
                }
                if (var_v0_4 == 0) {
                    var_s4_2 = 0x1000;
                }
                player->velocity_y = var_s4_2;
            }
block_166:
            temp_a0_6 = player->dive_phase;
            if (temp_a0_6 > 0) {
                if (temp_a0_6 == 1) {
                    player->velocity_y = 0x1000;
                } else {
                    player->dive_phase = temp_a0_6 - 1;
                    player->velocity_y = 0;
                }
            }
            temp_v0_16 = player->dive_phase;
            if (temp_v0_16 < 0) {
                player->dive_phase = temp_v0_16 + 0x200;
            }
            if (sp48 == 1) {
                var_s0_2 = 0;
                var_s2_2 = (u16 *)0x80074970;
                player->dive_phase = -0x1800;
                player->action_timer = 0xC;
                player->velocity_y = 0;
                player->air_state = 1;
                do {
                    temp_a3 = *var_s2_2;
                    var_s2_2 += 0x400;
                    temp_v0_17 = var_s0_2 + 0x400;
                    var_s0_2 += 0x200;
                    sub_8005a0e0(player->x, player->y, player->z, (s32) (temp_a3 << 0x10) >> 0x14, 0, (s32) (*(s16 *)(0x80074970 + ((temp_v0_17 & 0xFFF) * 2)) << 0x10) >> 0x14, -0x10, 0xF);
                } while (var_s0_2 < 0x1000);
                sub_80059e44(player->x, player->y - 0x1000, player->z, 0x5B, 3);
                sub_8005044c(0x10, 0);
            }
            temp_v0_18 = g_800a657a;
            if (temp_v0_18 < 0) {
                g_800a657a = (s16) (temp_v0_18 + 1);
                var_s5 = 0;
            }
            if (g_800a657a > 0) {
                g_800a657a = (s16) (g_800a657a - 1);
            }
            if ((g_800a657a == 0xB) && ((u16) g_80082488 & 0x4000)) {
                if (g_800a6538 < 0x300) {
                    var_v0_5 = g_800a653c;
                    if (var_v0_5 < 0) {
                        var_v0_5 = 0 - var_v0_5;
                    }
                    if (var_v0_5 >= 0x300) {
                        goto block_186;
                    }
                } else {
block_186:
                    g_800a657a = 0xC;
                }
            }
            temp_v1_10 = (u16) g_80082488;
            if (temp_v1_10 & 0x300) {
                if (temp_v1_10 & 0x8000) {
                    if (!(g_80082380 & 0x8000) && (player->action_timer >= 0) && ((player->floor_y - player->y) < 0x400) && (player->selected_actor_offset == 0)) {
                        player->action_timer = -0x10;
                    }
                    goto block_194;
                }
            } else {
block_194:
                if ((g_80082488 & 0x8000) && !(g_80082380 & 0x8000) && (player->field_86 < 7) && ((u8) player->field_96 < 4U) && (player->seed_action_mode == 0) && (g_800a657a == 0)) {
                    temp_v1_11 = player->animation_selector;
                    if ((temp_v1_11 != 8) && (player->queued_action < 0xC) && (temp_v1_11 != 0xA) && (temp_v1_11 != 0xD) && (temp_v1_11 != 0x11) && (player->dive_phase == 0)) {
                        player->field_86 = 0x12;
                    }
                }
            }
            if (player->field_86 == 0xA) {
                sub_800470ac(player);
            }
            if (player->seed_action_mode == 0xD) {
                player->seed_action_mode = 0;
            }
            temp_v1_12 = (u16) g_80082488;
            if (temp_v1_12 & 0x400) {
                if (temp_v1_12 & 0x80) {
                    player->target_heading -= 0x20;
                }
                if ((u16) g_80082488 & 0x20) {
                    player->target_heading += 0x20;
                }
                player->target_heading &= 0xFFF;
            } else if (temp_v1_12 & 0xF0) {
                if (g_8008246c == 0) {
                    sp58 = 1;
                }
                sub_80047ebc(&sp20);
                var_s5 = (u32) ((s32) (var_s5 * sp20) >> 0xE);
            }
            if ((player->velocity_x == 0) && (player->velocity_z == 0) && ((u16) g_80082488 & 0xF0) && (var_s7 == 0)) {
                player->heading = player->target_heading;
            } else {
                if (var_s7 < 0) {
                    var_s2_3 = (s32) (0x800 - var_s5) >> 1;
                    var_s7 = 0 - var_s7;
                    if (var_s2_3 < 0) {
                        var_s2_3 = 0;
                    }
                    if (var_s2_3 >= 0x401) {
                        var_s2_3 = 0x400;
                    }
                    if ((u16) g_80082488 & 0x80) {
                        player->target_heading -= var_s2_3;
                    }
                    if ((u16) g_80082488 & 0x20) {
                        player->target_heading += var_s2_3;
                    }
                    player->target_heading &= 0xFFF;
                }
                var_s2_4 = 2;
                if (var_s7 != 0) {
                    var_s2_4 = var_s7;
                }
                temp_v1_13 = player->heading;
                temp_a0_7 = (temp_v1_13 - player->target_heading) & 0xFFF;
                if (temp_a0_7 >= 0x801) {
                    var_a0_2 = 0x1000 - temp_a0_7;
                    if (var_a0_2 > turn_cap) {
                        var_a0_2 = turn_cap;
                    }
                    var_v0_6 = temp_v1_13 + (var_a0_2 >> var_s2_4);
                } else {
                    var_v0_7 = temp_a0_7 >> var_s2_4;
                    if (temp_a0_7 > turn_cap) {
                        var_v0_7 = turn_cap >> var_s2_4;
                    }
                    var_v0_6 = temp_v1_13 - var_v0_7;
                }
                player->heading = var_v0_6;
                player->heading &= 0xFFF;
            }
            temp_v1_14 = player->heading;
            temp_a3_2 = player->velocity_x;
            temp_a1 = ((s32) ((s32) *(s16 *)(0x80074970 + (((0x1400 - temp_v1_14) & 0xFFF) * 2))) << 0x10) >> 0x12;
            temp_a2 = player->velocity_z;
            temp_a0_8 = ((s32) ((s32) *(s16 *)(0x80074970 + (((0x1000 - temp_v1_14) & 0xFFF) * 2))) << 0x10) >> 0x12;
            var_v0_8 = (temp_a3_2 * temp_a1) + (temp_a2 * temp_a0_8);
            if (var_v0_8 < 0) {
                var_v0_8 += 0xFFF;
            }
            var_s2_5 = var_v0_8 >> 0xC;
            var_v0_9 = (temp_a2 * temp_a1) - (temp_a3_2 * temp_a0_8);
            if (var_v0_9 < 0) {
                var_v0_9 += 0xFFF;
            }
            var_s3_2 = var_v0_9 >> 0xC;
            if (var_s2_5 < 0) {
                var_s2_5 += sp40;
                if (var_s2_5 > 0) {
                    var_s2_5 = 0;
                }
            } else if (var_s2_5 > 0) {
                var_s2_5 -= sp40;
                if (var_s2_5 < 0) {
                    var_s2_5 = 0;
                }
            }
            if (var_s3_2 < 0) {
                var_s3_2 += var_s6;
                if (var_s3_2 > 0) {
                    var_s3_2 = 0;
                }
            } else if (var_s3_2 > 0) {
                var_s3_2 -= var_s6;
                if (var_s3_2 < 0) {
                    var_s3_2 = 0;
                }
            }
            if ((s32) sp58 > 0) {
                var_v0_10 = sp58;
                if (var_s3_2 < (s32) var_s5) {
                    var_s3_2 += sp38 + var_s6;
                    goto block_265;
                }
            } else {
block_265:
                var_v0_10 = sp58;
            }
            var_v0_11 = (s32) var_s5 < var_s2_5;
            if ((s32) var_v0_10 < 0) {
                var_v0_11 = (s32) var_s5 < var_s2_5;
                if ((0 - var_s5) < var_s3_2) {
                    var_s3_2 -= sp38 + var_s6;
                    var_v0_11 = (s32) var_s5 < var_s2_5;
                }
            }
            temp_v1_15 = 0 - var_s5;
            if (var_v0_11 != 0) {
                var_s2_5 = (s32) var_s5;
            }
            if (var_s2_5 < temp_v1_15) {
                var_s2_5 = temp_v1_15;
            }
            var_v1 = 0 - sp30;
            if (sp30 < var_s3_2) {
                var_s3_2 = sp30;
                var_v1 = 0 - sp30;
            }
            if (var_s3_2 < var_v1) {
                var_s3_2 = var_v1;
            }
            if (g_80082504 == 8) {
                if ((var_s3_2 < 0) && (g_800823d4 >= 0)) {
                    var_s3_2 = -0x900;
                }
                g_800823d4 = var_s3_2;
            }
            temp_v1_16 = player->heading;
            player->forward_component = var_s3_2;
            player->lateral_component = var_s2_5;
            temp_a1_2 = (s32) (*(s16 *)(0x80074970 + (((temp_v1_16 + 0x400) & 0xFFF) * 2)) << 0x10) >> 0x12;
            temp_a0_9 = (s32) (*(s16 *)(0x80074970 + (temp_v1_16 * 2)) << 0x10) >> 0x12;
            var_v0_12 = (var_s2_5 * temp_a1_2) + (var_s3_2 * temp_a0_9);
            if (var_v0_12 < 0) {
                var_v0_12 += 0xFFF;
            }
            player->velocity_x = var_v0_12 >> 0xC;
            var_v0_13 = (var_s3_2 * temp_a1_2) - (var_s2_5 * temp_a0_9);
            if (var_v0_13 < 0) {
                var_v0_13 += 0xFFF;
            }
            player->velocity_z = var_v0_13 >> 0xC;
        } else {
block_109:
            player->air_state = 5;
            player->dive_phase = 0;
            player->action_timer = 0;
            sub_80047ebc(&sp20);
            temp_a1_3 = player->heading;
            temp_v1_17 = player->target_heading;
            temp_a0_10 = (temp_a1_3 - temp_v1_17) & 0xFFF;
            turn_cap = 0x80;
            if (temp_a0_10 >= 0x801) {
                var_a0_3 = 0x1000 - temp_a0_10;
                if (var_a0_3 < 0x601) {
                    if (var_a0_3 > turn_cap) {
                        var_a0_3 = turn_cap;
                    }
                    var_v0_14 = temp_a1_3 + (var_a0_3 >> 2);
                    goto block_119;
                }
                goto block_115;
            }
            if (temp_a0_10 >= 0x601) {
block_115:
                var_s2_6 = temp_v1_17;
            } else {
                var_v0_15 = temp_a0_10 >> 2;
                if (temp_a0_10 > turn_cap) {
                    var_v0_15 = turn_cap >> 2;
                }
                var_v0_14 = temp_a1_3 - var_v0_15;
block_119:
                temp_v0_19 = var_v0_14 & 0xFFF;
                player->heading = temp_v0_19;
                var_s2_6 = temp_v0_19;
            }
            sub_80041ac4((s32) (*(s16 *)(0x80074970 + (var_s2_6 * 2)) * 3) >> 0xB, (s32) (*(s16 *)(0x80074970 + (((var_s2_6 + 0x400) & 0xFFF) * 2)) * 3) >> 0xB);
            if (((u16) g_80082488 & 0x4000) && !((u16) g_80082380 & 0x4000)) {
                sub_80041a74();
                player->animation_selector = 3;
                player->air_state = 1;
                player->velocity_x *= 2;
                player->velocity_y -= 0x800;
                player->velocity_z *= 2;
            }
            temp_a0_11 = player->heading;
            temp_a1_4 = ((s32) ((s32) *(s16 *)(0x80074970 + (((0x1400 - temp_a0_11) & 0xFFF) * 2))) << 0x10) >> 0x12;
            temp_a0_12 = ((s32) ((s32) *(s16 *)(0x80074970 + (((0x1000 - temp_a0_11) & 0xFFF) * 2))) << 0x10) >> 0x12;
            var_v1_2 = (player->velocity_x * temp_a1_4) + (player->velocity_z * temp_a0_12);
            if (var_v1_2 < 0) {
                var_v1_2 += 0xFFF;
            }
            player->lateral_component = var_v1_2 >> 0xC;
            var_v0_16 = (player->velocity_z * temp_a1_4) - (player->velocity_x * temp_a0_12);
            if (var_v0_16 < 0) {
                var_v0_16 += 0xFFF;
            }
            player->forward_component = var_v0_16 >> 0xC;
        }
    }
    player->previous_x = player->x;
    player->previous_y = player->y;
    player->previous_z = player->z;
    temp_v0_20 = sub_80038f38(0, &player->grounded);
    sp28 = temp_v0_20;
    if ((player->velocity_x != 0) || (player->velocity_y != 0) || (player->velocity_z != 0) || (temp_v0_20 != 0)) {
        sub_8003df98(0, 0x80, 0);
        temp_s2 = player->velocity_x;
        temp_s4 = player->velocity_y;
        temp_s3 = player->velocity_z;
        sub_8003633c(player, &player->velocity_x, &player->grounded, 0);
        player->floor_y = sub_80037a38(player);
        g_80082434 = sub_80038f20();
        temp_v0_21 = sub_80037dac(player, &sp28);
        if ((temp_v0_21 < player->floor_y) && (temp_v0_21 != 0x80000000) && (temp_v0_21 >= player->y)) {
            player->floor_y = temp_v0_21;
            var_v0_17 = player->flags_90 | 0x40;
        } else {
            var_v0_17 = player->flags_90 & 0xFFBF;
        }
        player->flags_90 = var_v0_17;
        temp_v0_22 = sub_80038f38(0, &player->grounded);
        sp28 = temp_v0_22;
        if ((temp_v0_22 != 0) && (g_800823a0 == 0)) {
            switch (temp_v0_22) {                   /* irregular */
            case 1:
                sub_8004a700(0, 0, &sp2C, 1);
                sp50 = 1;
                break;
            case 2:
                g_800823a0 = 1;
                sp50 = 1;
block_308:
                g_80082470 = 0x17;
                sub_80050994(0x3A, 0);
                break;
            case 3:
                g_800823a0 = 1;
                goto block_308;
            case 4:
                if ((player->timer_7e == 0) && (player->timer_92 == 0)) {
                    sub_8004a700(0, 0, &sp2C, 0);
                }
                break;
            }
            if (sp50 != 0) {
                player->velocity_x = temp_s2;
                player->velocity_y = temp_s4;
                player->velocity_z = temp_s3;
                player->grounded = 0;
                player->x = player->previous_x + temp_s2;
                player->z = player->previous_z + temp_s3;
                player->y = player->previous_y + temp_s4;
            }
        }
        if (player->grounded != 0) {
            g_800824d4 = 0;
        }
        sub_8003df98(0, 0, 0x80);
        var_v0_18 = player->velocity_y;
        if (var_v0_18 < 0) {
            var_v0_18 = 0 - var_v0_18;
        }
        if (var_v0_18 < 2) {
            player->velocity_y = 0;
        }
    }
    sub_800370c8(g_800a6500, g_800a6548, g_800a6508, 0x64);
    if (((g_800822b4 + 0x2000) < g_800a6504) && (g_800823a0 == 0)) {
        temp_v0_23 = g_800824d4;
        if (temp_v0_23 <= 0) {
            temp_v1_18 = g_800a65a0;
            g_800824d4 = (s32) (temp_v0_23 + 1);
            if (temp_v1_18 < 9U) {
                g_800a65a0 = (u8) (temp_v1_18 + 1);
            }
        }
        sub_8004a700(0, 0, &sp2C, 2);
    }
    sub_80042428();
}

#undef sp20
#undef sp28
#undef sp2C
#undef sp30
#undef sp38
#undef sp40
#undef sp48
#undef sp50
#undef sp58
