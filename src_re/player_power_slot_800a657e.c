/*
 * player_power_slot_800a657e.c
 *
 * Documentation-grade reconstruction of the player power slot at 0x800A657E —
 * the single signed halfword that carries BOTH B06 temporary invincibility and
 * B08 bubble shield, multiplexed by SIGN.
 * This file is not a build unit; the retail bytes remain authoritative.
 *
 * Evidence:
 *   analysis/phase4_b06_b08_powerups.json      (the authoritative row artifact)
 *   analysis/phase4_b06_b08_census_657e.json   (alias-aware whole-image site census)
 *   analysis/phase4_callee_writes.json         (memset-class writes a store census cannot see)
 *   analysis/phase4_b06_b08_writer_union.json  (runtime writer union, 3 fixtures)
 *   analysis/phase4_b06_oracle.json / phase4_b08_oracle.json (cold-boot lifecycles)
 *   analysis/phase4_b06_b08_lifecycle.json     (pause / persistence / scene transition)
 *   analysis/phase4_b06_b08_fixtures.json      (central hash pin for the fixtures)
 *   ObsidianVault/Canon/Systems/SYS_player_power_slot.md
 *
 * Confirmed resident paths (all re-verified against the pristine SCUS_942.88,
 * sha256 1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20):
 *   0x800588B0..0x800588D0  contact_pickup_walker  action 0x0C -> B06 grant := 400
 *   0x80058998..0x800589A8  contact_pickup_walker  action 0x2E -> B08 grant := -3
 *   0x80048640..0x80048654  player_vertical_update tick (blez guard, 1 per 2 frames)
 *   0x80049718..0x80049740  player_vertical_update CALL-SITE GATE on the damage handler
 *   0x8004A79C..0x8004A888  resident_level_transition_initiator = the player damage
 *                           handler: route, sign split, stagger guard, absorb, s1 clear,
 *                           and the protected true-health decrement
 *   0x80051EA0/0x80051EB0   harvester_equip_and_active_update equip moment (slot := 1)
 *   0x80051F60              harvester_equip_and_active_update per-frame slot := 1
 *   0x80051C3C..0x80051D00  effect_render_stage  NEGATIVE-slot shell render (B08)
 *   0x80055BC4..0x80055BE8  player_action_effects_update POSITIVE-slot effect 57 (B06)
 *   0x8005B268              respawn_transition_state_handler bulk player-block zero
 *   0x80046B68              level_load_player_spawn_writer -> memset(player, 0, 168)
 *   0x8005BDBC / 0x8005C6F0 / 0x8005C744 / 0x80059E44   the production chain
 *
 * SCOPE OF "COMPLETE BEHAVIOR" (DoD item 8). This file reconstructs the resolved
 * behavior OF THE SLOT: all 7 direct writers and all 7 readers enumerated by the
 * alias-aware census, plus the one callee-class writer, plus the production chain
 * that brings a power into existence. It does NOT reconstruct its host functions in
 * full — `player_vertical_update` alone is 6,004 B (0x80048138..0x800498AC) and only
 * its +0x7E/+0x7C tick block is modelled here. That boundary is deliberate and is
 * restated under "Bounded residuals".
 * Correction: this formerly said "all 8 writers" by including 0x8004AFB0. The
 * pristine pair at 0x8004AC70/0x8004AFB0 proves that store lands at player+0x82,
 * not this slot at player+0x7E; the old count was wrong.
 *
 * Bounded residuals:
 *   - BYTE/LAYOUT: none are outstanding, and none are bounded here, because this file
 *     is not compiled. Every function that touches the slot is carried by byte-matched
 *     hand-written assembly under asm/hand_written/, which is GITIGNORED (.gitignore:70).
 *     A "the bytes already match" claim must therefore cite tools/repro_inputs.sha256
 *     plus `tools/verify_repro_inputs.py --provision`, NOT the working tree — a clean
 *     checkout does not contain the assembly at all.
 *   - ALIASED-POINTER RESIDUAL: the census leaves 416 same-width accesses with an
 *     unresolved base across the 34 related functions, and 149 unresolved indirect
 *     calls. "Nothing else touches this slot" is UNPROVEN. NOTE: 0x8004AFB0 was long
 *     offered as the counterexample proving this class non-empty. That is RETRACTED —
 *     it writes player+0x82, not the slot (see below). No counterexample is currently
 *     known, which is NOT the same as the residual being empty.
 *     (Was 937, then 882 after $gp seeding — see the gp note below — then 416: the
 *     census's own `unresolved` list was never deduplicated by PC the way `hits` was,
 *     so a site revisited during the worklist's convergence was counted once per
 *     revisit, not once per site. 882 was real data with a 2x inflation baked in, not
 *     a wrong number pulled from nowhere. Same fix halved indirect calls 238 -> 149.)
 *   - $gp IS A PROVEN CONSTANT, worth 916 accesses. gp == 0x80081D98, established from
 *     the image alone: exactly one materialization (lui/addiu in stup1 at 0x8005F710);
 *     the only two other writes in code are `lw gp,0x68(sp)` epilogue restores, each
 *     matched by an `sw gp,0x68(sp)` prologue save at the same slot; the remaining 30
 *     apparent writes are data/string regions decoded as instructions. Every one of
 *     the 916 gp-relative accesses therefore has an exactly computable address, and
 *     NONE lands inside the player block 0x800A6500..0x800A65A8. A sound exclusion.
 *   - CALLEE DESTINATIONS ARE NOW FULLY ATTRIBUTED: all 26 call sites of the memset
 *     thunk resolve statically; 0 remain unresolved. The census previously reported
 *     0x8004DC40 as unattributed only because it kept the FIRST fixed-point round's
 *     record, before interprocedural argument propagation had run.
 *   - 0x8004AFB0 IS NOT PART OF THIS SUBSYSTEM (corrected 2026-08-01). It was modelled
 *     here as a knockdown clear of the power slot. It is not: fp = v1 + 4 at 0x8004AC70,
 *     so `sh zero, 0x7e(fp)` lands on player+0x82, four bytes past the slot. Measured
 *     fp = 0x800A6504 at the block entry, and a live 400-tick invincibility ticked
 *     straight through the clear untouched (381 -> 380 -> 379 across frame 5966).
 *     Two earlier errors cancelled each other here: the block was said never to execute
 *     (it does, at frame 5966) and then said to clear the slot (it does not).
 *   - TABLE A 0x80079E30 semantics are unresolved, and so is the
 *     contact-object RENDERER (and the VRAM/model source it consumes).
 *     The bubble's stack arg is 3
 *     (0x8005C704) and tableA[3] is twenty zero bytes, so the table is not indexed by
 *     that argument in the way once assumed.
 *   - The BIOS is outside every census tool in this repo. A BIOS scan finds zero
 *     `lui 0x800A` material, so the BIOS never forms the address — it receives it —
 *     but the writer set is complete only with respect to the GAME image.
 *
 * Correction carried by this file (see the report at the bottom of the header):
 *   analysis/phase4_b06_b08_powerups.json lists 0x80051C3C under
 *   `B06_invincibility.readers`. The branch at 0x80051C44 is `bgez a3, 0x80051D04`,
 *   so the guarded body runs only when the slot is NEGATIVE. 0x80051C3C is the
 *   BUBBLE's renderer, not the invincibility flash. The positive-slot visual is
 *   0x80055BC4 (effect 57). Modelled correctly below.
 */

#include "re_types.h"

/* --------------------------------------------------------------------------
 * The slot and its neighbours. Player block base 0x800A6500 (see MEM_800A6500).
 * re_types.h already declares this address as G_HARVESTER_STATE — a naming
 * artifact of C13 having reached it first. It is the shared power slot.
 * ----------------------------------------------------------------------- */
#define G_POWER_SLOT        (*(volatile int16_t *)0x800a657e)   /* +0x7E, SIGNED */
#define G_ACTION_LOCKOUT    (*(volatile int16_t *)0x800a657c)   /* +0x7C, sibling timer */
#define G_POWER_FLAGS_W     (*(volatile uint16_t *)0x800a6590)  /* +0x90, bitfield */
#define G_STAGGER_TIMER     (*(volatile int16_t *)0x800a6592)   /* +0x92, hit/stagger */
#define G_TRUE_HEALTH       (*(volatile int16_t *)0x800a6594)   /* +0x94, TRUE health */
#define G_REGION_CODE       (*(volatile int16_t *)0x800823a0)   /* per-sector region code */
#define G_BUBBLE_SHELL_RGB  ((const volatile uint8_t *)0x80078e55) /* indexed BACKWARD */

#define POWER_SLOT_ADDR         0x800a657eu
#define TRUE_HEALTH_ADDR        0x800a6594u
#define PLAYER_BLOCK_BASE       0x800a6500u

/* Sign multiplex. */
#define B06_INVINCIBILITY_TICKS  400   /* 0x800588BC / 0x800588C8, stored 0x800588D0 */
#define B08_BUBBLE_HITS          (-3)  /* 0x800589A0, stored 0x800589A8 */
#define HARVESTER_TRANSIENT      1     /* 0x80051EA0 and 0x80051F60 */

/* Neighbouring constants this subsystem reads or writes. */
#define STAGGER_REARM            (-30) /* 0x8004A80C materialises, 0x8004A814 stores */
#define REGION_NO_DAMAGE         5     /* 0x8004A7CC / 0x8004A7D0 */
#define PLAYER_BLOCK_CLEAR_LEN   168   /* 0x80046B6C, a2 to the memset thunk */
#define POWERFLAG_PER_ACTION     0x0002u /* transient ~2 frames; NOT a power */
#define POWERFLAG_SUPER_JUMP     0x0020u /* B09 — the one blue power that IS a bit */

/* Audio ids, each bound to its call sites by tools/census_sfx_callers.py. */
#define SFX_INVINCIBILITY_COLLECT   65   /* 0x800588C0 — EXACTLY ONE call site */
#define SFX_GENERIC_COLLECT       (-3)   /* 0x80058998 — FOUR sites; not bubble-specific */
#define SFX_CONTACT_INTERCEPTED     14   /* 0x8004A820 — ONE site, shared by both rows */
#define SFX_KNOCKDOWN             (-15)  /* 0x8004AF70, knockdown reaction */
#define EFFECT_INVINCIBILITY        57   /* 0x80055BE8 */

/* Production chain. */
#define CTOR_INVINCIBILITY      0x25u    /* (extra >> 12) + 0x23 with extra = 0x2000 */
#define CTOR_BUBBLE             0x1fu    /* (extra >> 12) + 0x1F with extra = 0x0000 */
#define ACTION_INVINCIBILITY    0x0cu    /* metaB[0x25] + 0x00 */
#define ACTION_BUBBLE           0x2eu    /* metaB[0x1F] + 0x00 */
#define G_PAIR_TABLE            0x8007a448u  /* stride 4: (u16 type, u16 extra) */
#define BLUE_COLOR_INDEX        1            /* orange 0, blue 1, green 2 */

extern void sfx_dispatch(int id);            /* 0x80050994 */
extern void play_sound(int id, int flags);   /* 0x8005044C */
extern void *memset_thunk(void *dst, int c, int n); /* 0x8005F7AC -> BIOS A0:0x2B */

/* --------------------------------------------------------------------------
 * The slot's own contract.
 *
 *   slot  > 0  B06 temporary invincibility, consumed by TIME
 *   slot  < 0  B08 bubble shield hit quota, consumed by HITS
 *   slot == 0  no power
 *   slot == 1  transient, written every ~2 frames by the grain harvester while
 *              power-flag bit 0x0080 is set (see SYS_grain_harvester)
 *
 * The linchpin is the tick's `blez` guard: it skips non-positive values, so a
 * bubble is time-invariant and an expiring invincibility lands EXACTLY on 0
 * rather than underflowing into a bubble.
 * ----------------------------------------------------------------------- */

/* ==========================================================================
 * GRANTS — contact_pickup_walker, reached via walker dispatch 0x8001B570.
 * ======================================================================= */

/*
 * Action 0x0C, handler 0x800588B0. `fp` is set once in the walker prologue:
 * 0x800586D4 addiu v0,0x800A6597 / 0x800586DC addiu fp,v0,-25 -> fp = 0x800A657E.
 *
 * The guard reads the CURRENT slot and only suppresses the collect sound. Both
 * arms materialise 400 (0x800588BC in the branch delay slot, 0x800588C8 on the
 * fall-through) and the store at 0x800588D0 sits in the delay slot of
 * `j 0x800589AC`, so it executes unconditionally. Capacity is a clamped REFRESH,
 * never additive — re-confirmed at runtime with the slot preset to 20000: the
 * store still wrote 400.
 */
static void contact_action_0x0c_grant_invincibility(void)
{
    const int16_t current = G_POWER_SLOT;      /* 0x800588B0  lh v0,0x0(fp) */

    if (current <= 0) {                        /* 0x800588B8  bgtz v0 -> 0x800588CC */
        sfx_dispatch(SFX_INVINCIBILITY_COLLECT); /* 0x800588C0  a0 = 65 */
    }
    G_POWER_SLOT = B06_INVINCIBILITY_TICKS;    /* 0x800588D0  sh v0,0x0(fp) */
}

/*
 * Action 0x2E, handler 0x80058998. No read of the prior value at all, so this is
 * likewise a clamped refresh: poking -1 immediately before the natural grant
 * yields -3, not -4.
 */
static void contact_action_0x2e_grant_bubble(void)
{
    sfx_dispatch(SFX_GENERIC_COLLECT);         /* 0x80058998  a0 = -3 */
    G_POWER_SLOT = B08_BUBBLE_HITS;            /* 0x800589A8  sh v0,0x657e(at) */
}

/*
 * The shared slot is LAST-WRITE-WINS across powers: because both grants are
 * unconditional stores, collecting a bubble while invincible discards the
 * invincibility, and vice versa.
 */

/* ==========================================================================
 * TICK — player_vertical_update (0x80048138..0x800498AC), s1 = player block.
 * ======================================================================= */

/*
 * 0x80048640..0x80048654. Cadence is 1 per 2 frames (measured: 400 tick writes
 * over ~800 frames; 15 ticks in 30 running frames).
 *
 * The blez guard is what makes the sign multiplex work: a NEGATIVE slot (a
 * bubble) is never touched here, so a bubble cannot expire with time, and a
 * positive slot cannot be driven below 0.
 *
 * The sibling lockout at +0x7C is decremented by the same routine
 * (0x80048658..0x8004866C) under the same guard shape; it is a short player
 * ACTION lockout, not a power, and is included only because it shares the block.
 */
static void player_vertical_update_tick_timers(void)
{
    const int16_t slot = G_POWER_SLOT;         /* 0x80048640  lh v0,0x7e(s1) */

    if (slot > 0) {                            /* 0x80048648  blez -> 0x80048658 */
        G_POWER_SLOT = (int16_t)(slot - 1);    /* 0x80048650 / 0x80048654 */
    }

    {
        const int16_t lockout = G_ACTION_LOCKOUT;  /* 0x80048658 */
        if (lockout > 0) {                         /* 0x80048660  blez */
            const int16_t next = (int16_t)(lockout - 1);
            G_ACTION_LOCKOUT = next;               /* 0x8004866C */
            if (next == 0) {                       /* 0x80048670 / 0x80048674 */
                G_POWER_FLAGS_W = 1;               /* 0x8004867C sh 1 -> +0x90 */
            }
        }
    }
}

/* ==========================================================================
 * CALL-SITE GATE — player_vertical_update, 0x80049718..0x80049740.
 * ======================================================================= */

/*
 * Invincibility is enforced in TWO places. This is the outer one: a non-zero slot
 * (of EITHER sign) skips the `jal 0x8004A700` entirely, so the damage handler is
 * never entered from this site. A non-zero stagger timer does the same.
 *
 * Returns non-zero when the damage call is suppressed before it happens.
 */
static int player_vertical_update_damage_call_is_gated(void)
{
    if (G_POWER_SLOT != 0) {                   /* 0x80049718 / 0x80049720  bne */
        return 1;
    }
    if (G_STAGGER_TIMER != 0) {                /* 0x80049728 / 0x80049730  bne */
        return 1;
    }
    return 0;                                  /* else 0x80049740  jal 0x8004A700 */
}

/* ==========================================================================
 * DAMAGE HANDLER 0x8004A700 — the inner enforcement.
 *
 * Six callers, enumerated statically and independently re-scanned here:
 *   0x800496B0, 0x80049740, 0x80049868  player_vertical_update
 *   0x8004B4A0                          actor_player_contact_resolver
 *   0x80058A48                          contact_pickup_walker
 *   0x8005C9F8                          seed_plant_mine_handler
 * ======================================================================= */

/*
 * CRITICAL, and the correction the prior revision of the artifact needed: the
 * branch at 0x8004A7B4 only ROUTES. What actually suppresses the health write is
 * register `s1` being cleared, tested by `0x8004A828 beq s1,zero`.
 *
 * `damage_enabled` below IS s1. Note that 0x8004A800 sits in the DELAY SLOT of
 * the stagger branch at 0x8004A7FC, so it retires damage on BOTH arms of that
 * test — the artifact's label "(already-staggered bubble)" reads as if it were
 * on one arm only.
 *
 * Returns s1 as it stands at 0x8004A828.
 */
static int player_damage_handler_interception(int damage_enabled)
{
    int16_t slot;

    G_POWER_FLAGS_W |= POWERFLAG_PER_ACTION;   /* 0x8004A79C / 0x8004A7A8 / 0x8004A7B0 */
    slot = G_POWER_SLOT;                       /* 0x8004A7A4  lh v1,0x657e(v1) */

    if (slot == 0) {                           /* 0x8004A7B4  bne v1,zero -> 0x8004A7D8 */
        const int16_t region = G_REGION_CODE;  /* 0x8004A7C0 */
        /* 0x8004A7C8 beq v1,s1 and 0x8004A7D0 bne v1,5: only region == s1 or the
         * no-damage region 5 divert into the interception block with a zero slot. */
        if (region != damage_enabled && region != REGION_NO_DAMAGE) {
            return damage_enabled;             /* -> 0x8004A828 with s1 INTACT */
        }
    }

    /* --- interception block, 0x8004A7D8 --- */
    slot = G_POWER_SLOT;                       /* 0x8004A7E0  lh v0,0x0(a0) */

    if (slot < 0) {                            /* 0x8004A7E8  bgez -> 0x8004A80C */
        const int16_t stagger = G_STAGGER_TIMER;   /* 0x8004A7F4 */

        damage_enabled = 0;                    /* 0x8004A800 — DELAY SLOT: both arms */

        if (stagger != 0) {                    /* 0x8004A7FC  bne -> 0x8004A81C */
            /* An already-staggered player does NOT consume a shield hit, and the
             * stagger timer is NOT re-armed. */
            play_sound(SFX_CONTACT_INTERCEPTED, 0);  /* 0x8004A820 */
            return damage_enabled;
        }
        G_POWER_SLOT = (int16_t)(slot + 1);    /* 0x8004A804 / 0x8004A808  toward 0 */
    }

    /* Reached by: a positive slot (invincible), the zero-slot region cases, and
     * the bubble path that consumed a hit. */
    G_STAGGER_TIMER = STAGGER_REARM;           /* 0x8004A80C materialises, 0x8004A814 stores */
    damage_enabled = 0;                        /* 0x8004A818 */
    play_sound(SFX_CONTACT_INTERCEPTED, 0);    /* 0x8004A820 */
    return damage_enabled;
}

/*
 * The protected write. 0x8004A888 is the ONLY instruction in the resident image
 * that decrements true health on a contact path; the other five writers of
 * 0x800A6594 are 0x80046C04 (spawn init), 0x80055124 (sfx glue), 0x80058890
 * (heal pickup, health += 1), 0x8005291C (results-screen clamp) and 0x8005B30C
 * (respawn restore). No overlay writes it either — three overlay accesses exist
 * and all are reads. So suppressing 0x8004A888 IS the whole of contact-damage
 * immunity.
 */
static int16_t player_damage_handler_apply(int damage_enabled, int16_t true_health)
{
    if (damage_enabled == 0) {                 /* 0x8004A828  beq s1,zero -> 0x8004AA10 */
        return true_health;
    }
    true_health = (int16_t)(true_health - 1);  /* 0x8004A880 */
    G_TRUE_HEALTH = true_health;               /* 0x8004A888  sh v1,0x6594(at) */
    /* 0x8004A890 bgez: a negative result falls into the death branch, which is
     * where this function's census name (resident_level_transition_initiator)
     * comes from — it stores 2 to the region code at 0x8004A8B4. That is a
     * secondary effect of one branch, not the function's purpose. */
    return true_health;
}

/* ==========================================================================
 * READERS THAT DO NOT WRITE — and they split cleanly along the sign.
 * ======================================================================= */

/*
 * effect_render_stage (0x80051B84), read at 0x80051C3C.
 *
 * 0x80051C44 `bgez a3, 0x80051D04` — the guarded body runs ONLY when the slot is
 * NEGATIVE. This is the BUBBLE's shell, not the invincibility flash.
 *
 * 0x80051C48/0x80051C4C form slot*3 and index BACKWARD from 0x80078E55, so the
 * colour triple for a quota of -n comes from 0x80078E55 - 3n:
 *
 *      slot -3 (3 hits left) -> 0x80078E4C = 80 80 80   brightest
 *      slot -2 (2 hits left) -> 0x80078E4F = 60 60 60
 *      slot -1 (1 hit  left) -> 0x80078E52 = 40 40 40   dimmest
 *      slot -4               -> 0x80078E49 = 00 00 00   (unreachable)
 *
 * The table is sized EXACTLY to the three-hit quota, which independently
 * corroborates that capacity is 3 and that the grant is a clamped refresh: no
 * writer ever drives the slot below -3, so 0x80078E49 is never read.
 *
 * The body then reads player XYZ (0x800A6500/6504/6508, Y biased by -8192),
 * mixes an animation byte at 0x800910AA against the table at 0x80074970, and
 * calls 0x80023544 (rot_average_project) with radius terms 270 and 300.
 */
static int bubble_shell_render(uint8_t rgb_out[3])
{
    const int16_t slot = G_POWER_SLOT;         /* 0x80051C3C  lh a3,0x657e(a3) */

    if (slot >= 0) {                           /* 0x80051C44  bgez -> 0x80051D04 */
        return 0;                              /* nothing drawn for B06 or for 0 */
    }
    rgb_out[0] = G_BUBBLE_SHELL_RGB[slot * 3 + 0];  /* 0x80051C78 */
    rgb_out[1] = G_BUBBLE_SHELL_RGB[slot * 3 + 1];  /* 0x80051C84 */
    rgb_out[2] = G_BUBBLE_SHELL_RGB[slot * 3 + 2];  /* 0x80051C90 */
    return 1;
}

/*
 * player_action_effects_update (0x80055644), read at 0x80055BC4. This is the
 * POSITIVE-slot consumer, i.e. the invincibility one — and it is the game itself
 * distinguishing a real invincibility from the harvester's transient 1: it
 * additionally requires the harvester bit to be CLEAR.
 */
static int invincibility_effect_id(void)
{
    if (G_POWER_SLOT <= 0) {                          /* 0x80055BC4 / 0x80055BCC blez */
        return 0;
    }
    if ((G_POWER_FLAGS_W & POWERUP_HARVESTER) != 0) { /* 0x80055BD8..0x80055BE4 andi 0x80 */
        return 0;
    }
    return EFFECT_INVINCIBILITY;                      /* 0x80055BE8  a3 = 57 */
}

/* ==========================================================================
 * THE HARVESTER'S USE OF THE SLOT — and why it is NOT invincibility.
 * ======================================================================= */

/*
 * 0x80051EA0 is the EQUIP moment: `sh v0,-0x4(s0)` with s0 = 0x800A6582, i.e. an
 * ALIASED write to 0x800A657E, paired with `ori 0x0080` into the flags word two
 * instructions later at 0x80051EB0. An immediate-form scan cannot see it; the
 * alias-aware census is what recovered it.
 */
static void harvester_equip_commit(void)
{
    G_POWER_SLOT = HARVESTER_TRANSIENT;        /* 0x80051EA0 */
    G_POWER_FLAGS_W |= POWERUP_HARVESTER;      /* 0x80051EB0 */
}

/* 0x80051F60, re-asserted every frame the harvester flag is set. The tick clears
 * it back to 0 on alternate frames, so the slot visibly oscillates 1 <-> 0. */
static void harvester_active_frame(void)
{
    G_POWER_SLOT = HARVESTER_TRANSIENT;        /* 0x80051F60 */
}

/*
 * The naive reading — "harvesting silently confers invincibility through the
 * shared slot" — is REFUTED. actor_player_contact_resolver tests the harvester
 * FLAG BIT at 0x8004B160 (`andi v0,0x80`) and branches away at 0x8004B164, long
 * before its `jal 0x8004A700` at 0x8004B4A0. Measured with execTrace over the
 * handler and all six call sites: with the harvester bit set the handler is
 * entered ZERO times from any site and health stays 4; without it, 3 entries all
 * reach 0x8004A888 and health goes 4 -> 1. Immunity while harvesting belongs to
 * the flags word, not to this slot.
 */

/* ==========================================================================
 * RESETS — three of them, and one is invisible to a store-site census.
 * ======================================================================= */

/*
 * 0x8005B268, respawn_transition_state_handler. One `sh zero` inside a bulk zero
 * of the player block (0x653C, 0x6540, 0x6544, 0x654C, 0x655C, 0x6574, 0x657A,
 * 0x657C, 0x657E, 0x6580, 0x6582, 0x6584, ...). It has NO data dependence on the
 * prior value, so observing it execute once proves the reset for ANY prior power
 * state.
 *
 * Note the asymmetry with the flags word: the same handler does `andi 0x0020` at
 * 0x8005B340, i.e. keeps ONLY super jump. B09 survives a respawn; B06/B08 do not.
 */
static void respawn_clear_power_slot(void)
{
    G_ACTION_LOCKOUT = 0;                      /* 0x8005B260 */
    G_POWER_SLOT = 0;                          /* 0x8005B268 */
    /* ... 0x6580, 0x6582, 0x6584 follow ... */
}

/*
 * 0x8004AFB0 — REMOVED FROM THIS RECONSTRUCTION (2026-08-01).
 *
 * This file previously modelled the knockdown reaction in actor_player_contact_resolver
 * as a clear of the power slot, with a `contact_knockdown_reaction()` function whose
 * body set G_POWER_SLOT = 0. That was wrong and the function is deleted rather than
 * corrected, because the site does not belong to this subsystem at all.
 *
 * `fp` is NOT the player block. 0x8004AC70 sets `addiu fp, v1, 4`, so every offset in
 * the block is shifted +4 relative to 0x800A6500:
 *
 *     0x8004AF4C  lw 0x2c(fp)   -> player+0x30
 *     0x8004AF2C  lbu 0x9f(fp)  -> player+0xA3
 *     0x8004AF5C  lh 0x7c(fp)   -> player+0x80
 *     0x8004AF6C  lh 0x84(fp)   -> player+0x88
 *     0x8004AFB0  sh 0x7e(fp)   -> player+0x82      <-- NOT the slot at player+0x7E
 *
 * The frame is internally consistent: 0x8004AFA8 `sh zero, 0x80(fp)` writes
 * 0x800A6584 = player+0x84, which is exactly the field the guard at 0x8004AEBC reads
 * absolutely (`lui 0x800a` / `lh 0x6584`). The block reads and writes the same field.
 *
 * Evidence: tools/phase4_knockdown_reachability.py (static) and
 * tools/phase4_knockdown_probe.py (runtime, with a desync self-check). Measured
 * fp = 0x800A6504; a live power poked to 400 survived the clear untouched.
 */

/*
 * 0x80046B68, level_load_player_spawn_writer. THE SCENE-TRANSITION CLEAR — and a
 * CALLEE write, which no store-site census can see by construction.
 *
 * The game reaches the BIOS through the PsyQ stub 0x8005F7AC
 * (`addiu t2,0xA0 / jr t2 / addiu t1,0x2B`), which is REGISTER-INDIRECT: scanning
 * for `jal 0x000000A0` / `jal 0x800000A0` returns zero resident sites. The THUNK
 * is called by ordinary jal, so its 26 call sites are enumerable, and ALL 26 now
 * resolve statically: 25 do not cover the slot, and this one does.
 *
 *   0x80046B68  level_load_player_spawn_writer  memset(0x800A6500, 0, 168)
 *       Its single caller is 0x8005BAA4 in gameplay_state_reset_cursor_seed, passing
 *       a0 = 0x800A6500 -- the player block. 168 bytes covers the whole block, so it
 *       clears the slot. Independently confirmed at runtime (watch the BIOS store PC,
 *       capture [ra,a0,a2], filter a0 == 0x800A657E -> ra = 0x80046B70 = call + 8).
 *
 *   0x8004DC40  respawn_collision_reset         memset(0x80095358, 0, 48)
 *       Both call sites (0x8005B34C, 0x8005BAB4) pass a0 = 0x80095358, the CAMERA
 *       block, not the player block. The write spans 0x80095358..0x80095388 and is
 *       PROVABLY DISJOINT from the slot. This was the "one unattributed callee
 *       destination" carried as a residual until 2026-08-01.
 *
 * Measured: 0xBFC02BB0 writes 0 to the slot on EVERY level load — it appears in
 * all three runtime writer-union fixtures, not just at a transition.
 */
static void level_load_player_spawn_clear(void *player_block)
{
    memset_thunk(player_block, 0, PLAYER_BLOCK_CLEAR_LEN);  /* 0x80046B68, a2 = 168 */
}

/* ==========================================================================
 * PRODUCTION CHAIN — how a power comes to exist. Every hop from the pristine EXE.
 *
 *   blue token (type-0x3f kind 0x2A, object id 0x17)
 *     -> counter 0x800A6599, packed (selected << 4 | max_available); PERSISTS
 *        across levels
 *     -> butt-slam a seed -> plant_spawn 0x8005BDBC
 *     -> pair table 0x8007A448[idx] -> (type, extra)
 *     -> plant slot 0x80090BF0 + n*0x30; type dispatch jr [0x8001B848 + (type-2)*4]
 *     -> the type handler calls spawn_drop/contact_alloc 0x80059E44 with the ctor
 *        in a3 and a mode in a STACK arg at 0x10(sp)
 *     -> metaB 0x8007941C[ctor] (stride 0x14); metaB + 0x00 = the ACTION ID
 *     -> walker dispatch jr [0x8001B570 + (action-2)*4] -> the grant above
 * ======================================================================= */

/*
 * 0x8005BE10..0x8005BE44. The counter byte's HIGH nibble is the selected tier;
 * the index is color*4 + tier - 1. The read is `lhu` at 0x8007A448 + idx*4 for
 * the type (0x8005BE88) and 0x8007A44A + idx*4 for the extra (0x8005BF2C), which
 * is stored to the plant slot at +0x00 and +0x2E respectively.
 */
static int blue_pair_index(int color, uint8_t counter_byte)
{
    return color * 4 + (counter_byte >> 4) - 1;
}

static uint16_t pair_table_type(int idx)
{
    return *(const uint16_t *)(G_PAIR_TABLE + (unsigned)idx * 4u);
}

static uint16_t pair_table_extra(int idx)
{
    return *(const uint16_t *)(G_PAIR_TABLE + (unsigned)idx * 4u + 2u);
}

/*
 * seed_plant_type7_handler 0x8005C744, ctor arithmetic at 0x8005C7D8/0x8005C7E0:
 * `sll a3,16 / sra a3,28 / addiu a3,0x23`, i.e. sign-extend(extra) >> 12, + 0x23.
 * seed_plant_type6_handler 0x8005C6F0 uses the same shift with + 0x1F
 * (0x8005C720..0x8005C72C) and passes stack arg 3 (0x8005C704).
 */
static int plant_type7_ctor(uint16_t extra)
{
    return (((int16_t)extra) >> 12) + 0x23;    /* extra 0x2000 -> 0x25 */
}

static int plant_type6_ctor(uint16_t extra)
{
    return (((int16_t)extra) >> 12) + 0x1f;    /* extra 0x0000 -> 0x1F */
}

/* spawn_drop 0x80059E44: s3 = a3 = the ctor (0x80059E4C), a3 is then reloaded
 * from the caller's stack arg (0x80059E50 lw a3,0x40(sp) == caller 0x10(sp)).
 * metaB at 0x80059F0C is indexed by the CTOR; table A 0x80079E30 at 0x80059EF4
 * is indexed by the STACK ARG. */
static uint16_t contact_action_id_for_ctor(int ctor)
{
    return *(const uint16_t *)(G_METADATA_TABLE + (unsigned)ctor * 0x14u);
}

/*
 * The two lanes this file is about, verified from the tables in the pristine EXE:
 *
 *   blue x1: pair[4] = type 7, extra 0x2000 -> ctor 0x25 -> metaB[0x25]+0 = 0x0C
 *            -> walker[0x0C] = 0x800588B0 -> B06 invincibility := 400
 *   blue x3: pair[6] = type 6, extra 0x0000 -> ctor 0x1F -> metaB[0x1F]+0 = 0x2E
 *            -> walker[0x2E] = 0x80058998 -> B08 bubble := -3
 *
 * The neighbouring tiers are a useful cross-check and are NOT this subsystem:
 *   blue x2: pair[5] = type 7, extra 0x3000 -> ctor 0x26 -> action 0x09 (B07 health)
 *   blue x4: pair[7] = type 7, extra 0x4000 -> ctor 0x27 -> action 0x0F (B09 super
 *            jump) — the one blue power that uses a 0x800A6590 BIT, POWERFLAG_SUPER_JUMP.
 *
 * Asset dependency: the plant BODY model comes from *(0x800A649C + type*4), a
 * per-level table filled at load. NULL => the plant functions but is INVISIBLE.
 * B06 needs PLANTS/PLANT07.ALL and B08 needs PLANTS/PLANT06.ALL.
 */
