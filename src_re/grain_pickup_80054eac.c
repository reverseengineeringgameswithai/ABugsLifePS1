/* Semantic reconstruction of pristine SCUS-94288 0x80054EAC..0x80055188.
 * This is analysis documentation, not patch code. Exact addresses and branch
 * evidence are recorded in EXP_2026-08-03_phase4_c01_grain_pickup.md. */

#include <stdbool.h>
#include <stdint.h>

typedef struct C01GrainState {
    uint8_t grain_count;       /* 0x800A65A1 */
    uint16_t player_flags;     /* 0x800A6590 */
    int16_t true_health;       /* 0x800A6594; exact-50 writes 4 */
    uint16_t hud_reward;       /* 0x800B0188 */
    uint16_t hud_grain;        /* 0x800B018C */
    uint16_t hud_aux;          /* 0x800B0190 */
    uint8_t scene_id;          /* 0x80082504 */
    uint32_t game_state;       /* 0x800823A0 */
    int32_t player_x;
    int32_t player_y;
    int32_t player_z;
    int32_t player_field_48;
} C01GrainState;

typedef struct C01EffectSeed {
    int32_t x;
    int32_t y;
    int32_t z;
    int32_t player_field_48;
    int32_t scale;
} C01EffectSeed;

static uint16_t pulse_halfword(uint16_t value)
{
    if (value >= 3072u)
        return (uint16_t)(4096u - value);
    if (value >= 1025u)
        return 1024u;
    if (value == 0u)
        return 64u;
    return value;
}

/* The caller owns source/contact retirement. This function owns the count,
 * HUD pulse, optional pre-effect gate, and the exact-50 reward branch. */
bool grain_pickup_80054eac(C01GrainState *s, C01EffectSeed *reward_effect)
{
    s->hud_grain = pulse_halfword(s->hud_grain);
    s->grain_count = (uint8_t)(s->grain_count + 1u);

    if (s->grain_count != 50u)
        return false;

    reward_effect->x = s->player_x;
    reward_effect->y = s->player_y;
    reward_effect->z = s->player_z;
    reward_effect->player_field_48 = s->player_field_48;
    reward_effect->scale = 1024;

    /* Pristine reachable branch after the -11 sound/event request. */
    s->true_health = 4;
    s->hud_reward = pulse_halfword(s->hud_reward);
    s->hud_aux = pulse_halfword(s->hud_aux);
    return true;
}

/* Optional pre-effect gate, executed before the count update in the original:
 *
 *   (first_script_byte & 0x0f) == 0
 *   && scene_id != 0x11
 *   && game_state != 2
 *   && !(player_flags & 4)
 *   && gp_relative_0x6b4 == 0
 *   && FUNC_80045678(player_base) == 0
 *
 * A second script byte selects the variant passed to FUNC_80044D28. The
 * retained C01 capsule did not execute the final pre-effect spawn call.
 */
