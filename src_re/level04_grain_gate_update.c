/*
 * level04_grain_gate_update.c -- City Entrance native grain doors (semantic RE)
 *
 * Documentation only; not a build input.  The exact pristine function occupies
 * 0x800B3D84..0x800B3F37 and byte-matches REBUILD/files/LEVEL04/LEVEL.BIN at
 * file offset 0x3E4 (load base 0x800B39A0).  Phase-4 evidence and opcode guards
 * live in tools/phase4_grain_gates.py and analysis/phase4_grain_gates.json.
 */

#include "re_types.h"

#define GRAIN_COUNT       (*(volatile uint8_t *)0x800A65A1)
#define DENIAL_COUNTDOWN  (*(volatile int32_t *)0x800B456C)
#define GATE_STATE        ((volatile int32_t *)0x800B4570)

extern int player_near_gate_800524b8(const void *player, const int32_t *xz,
                                     int radius);
extern void gate_open_feedback_80038ee8(int gate_index);
extern void play_sfx_80050c40(int sfx_id, int argument);
extern uint8_t next_gate_cooldown_byte_800822f4(void);
/* Exact semantic core of 0x800B3D84.  Geometry arguments and the three fixed
 * call-site positions are retained in the machine artifact/schema rather than
 * disguised behind guessed names here. */
void city_grain_gate_update_partial(int gate_index, int player_is_near)
{
    int threshold = 10 * (gate_index + 1);
    int state = GATE_STATE[gate_index];

    if (state == -1 && player_is_near) {
        if ((int)GRAIN_COUNT >= threshold) {
            GATE_STATE[gate_index] = 32;
            gate_open_feedback_80038ee8(gate_index);
        } else if (DENIAL_COUNTDOWN == 0) {
            DENIAL_COUNTDOWN = next_gate_cooldown_byte_800822f4() + 60;
            play_sfx_80050c40(76, 0);
        }
    }

    state = GATE_STATE[gate_index];
    if (state > 0) {
        state -= 1;
        GATE_STATE[gate_index] = state;
        /* Retail applies two fixed-axis 0x800292DC geometry handoffs here.
         * Their call-site arguments are retained in disassembly evidence; this
         * bounded semantic file does not invent higher-level parameter names. */
    }
}
