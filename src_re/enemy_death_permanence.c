/* ============================================================================
 * enemy_death_permanence.c — enemy hit -> death/despawn + gold-berry permanence
 * ----------------------------------------------------------------------------
 * RCG-022 ("Permanent enemy death rules"). Resolves the [[Berry projectile and
 * homing]] residual "Floor/death is unresolved" and the audit gap
 * "full enemy death/despawn state is not [understood]".
 *
 * ORIGINAL ADDRESS : the death/permanence logic lives INSIDE
 *                    contact_vs_actor_handler (fcn.80058af8). The local enemy
 *                    hit-counter branch starts at 0x8005905c; the final
 *                    hit/death/permanence tail is 0x8005929c..0x800593b0.
 * CONFIDENCE       : CONFIRMED live (isolated DuckStation, SCUS-94288).
 *                    Method: breakpoints on the gate/destroy sites while throwing
 *                    each berry class at a chaser. Gold 3/3 permanent; mega/homing/
 *                    blue 3/3 non-permanent. Cross-checked on spider + mosquito.
 * FIXTURES         : spider_walking.sav, mosquito.sav (chasers = homing targets,
 *                    so mega/homing auto-connect; gold aimed by holding a direction
 *                    to keep Flik moving so the chaser closes in). worm.sav is the
 *                    berry-TOUGH mover-VM enemy (+0x5c bit 0x40) but is NOT a homing
 *                    target and did not auto-connect; earthworm likewise stationary.
 * USER-CONFIRMED   : "spider takes one gold berry to kill"; "mega/homing/blue does
 *                    not decrement [the counter] — that is normal behaviour".
 * 2026-07-07 TRACE : killing_spider.movie.json on pristine and rebuilt ALLMODS:
 *                    red and forced Blackberry/Fastberry both drove spider id 9's
 *                    local +0x6e counter 2->1 on hit 1, then 1->0->999 on hit 2.
 *                    Quota 0x800a658e was unchanged; Blackberry still hit the 2x
 *                    speed / 4x gravity hook and used red throw class s1=2.
 * GOLD-DROP LOCK  : 2026-07-07 operator confirmation: the gold-drop mod's
 *                    type-120 floor glyph is walk-collectible. Its pickup hook
 *                    decrements this same quota, so the bottom gold-defeat
 *                    counter advances without Flik equipping a literal gold berry.
 *
 * ---------------------------------------------------------------------------
 * THE GLOBAL "ENEMIES-REMAINING" COUNTER  (the permanence ledger)
 * ---------------------------------------------------------------------------
 *   G_ENEMIES_REMAINING = 0x800a658e  (u16, per level).
 *   Live: spider_walking.sav = 21, earthworm.sav = 50.
 *   A GOLD kill decrements it by 1. mega/homing/blue/red do NOT touch it.
 *   When it reaches 0, the destroy block calls fcn.8005182c(0x80090b68)
 *   (the all-enemies-permanently-defeated event/reward). => this counter is the
 *   permanent-kill quota; gold berries (and, likely, the yellow Mine Plant — see
 *   the +0x27==6 branch below) are the only things that spend it.
 *   The Gold-berry drop mod also spends this ledger on pickup of a tagged type-120
 *   glyph. HUD displays LW(0x80082258) - LH(0x800a658e), so decrementing this
 *   value increments the visible bottom gold-defeat counter.
 *
 * ---------------------------------------------------------------------------
 * THE HIT-PROCESSING TAIL (per struck enemy s2, per contact object s1)
 * ---------------------------------------------------------------------------
 * Reached when a contact object (berry / berry sub-object) overlaps a damageable
 * enemy (from the 0x80090748 pointer table, up to 64 slots). s7 = hit-strength
 * accumulator (init 0). The permanence decision is the value of s7:
 *
 *   LOCAL HIT COUNTER / TOUGH DAMAGE BRANCH @0x8005905c:
 *       hp = lh 0x6e(s2)
 *       if hp >= 100 -> skip this decrement lane (999 marker is exempt)
 *       cls = lbu 0x2c(s1)          ; contact-record damage class byte
 *       cls 0,12 -> hp -= 2
 *       cls 1    -> hp -= 99
 *       cls 127  -> hp -= 4
 *       cls 128  -> hp -= 3
 *       default  -> hp -= 1
 *       sh hp,0x6e(s2) @0x800590e4
 *       if hp > 0 -> spawn small hit feedback and return; no death tail yet.
 *       if hp <=0 -> fall through to the hit/death tail below.
 *
 *   IMPORTANT: enemy+0x6e is not only a death marker. For actors such as the
 *   spider in killing_spider.movie.json it is a pre-death local counter (starts
 *   at 2). Only after the counter reaches zero does the final tail write 999.
 *
 *   PERMANENCE GATE @0x800591f0:
 *       lh  v1, 0x24(s1)              ; hit-record field
 *       beq v1, 11 -> 0x80059210      ; == 11  -> s7 |= 2   (PERMANENT)   <-- GOLD
 *       lbu v1, 0x27(s1)
 *       bne v1, 6  -> 0x80059214      ; != 6   -> s7 |= 1   (temporary)
 *                    0x80059210: s7 |= 2         ; == 6  -> also PERMANENT (LIKELY Mine Plant)
 *                    0x80059218: s7 |= 1         ; (delay slot; both bits may end set)
 *
 *   NOTE ON THE "==11" INPUT: for a straight GOLD throw the connecting contact
 *   object at s1 carries +0x24 == 11 (gold's throw class). The PRIMARY thrown-berry
 *   record instead carries +0x24 == model (110 basic / 123 homing / 124 mega) and
 *   never 11, which is why mega/homing/blue never satisfy the gate. Empirically the
 *   s7|=2 branch (0x80059210) fires for gold ONLY (3/3) and never for the others.
 *
 *   HIT APPLIED @0x8005929c.. (runs after the local counter reaches <=0, or for
 *   contacts that bypass the local-counter wait):
 *       sh   999, 0x6e(s2)           ; +0x6e = 999   HIT MARKER (death-anim trigger)
 *       sh   0,   0x60(s2)           ; +0x60 = 0
 *       lhu  v1,  0x5c(s2)
 *       ori  v1,  0x0880             ; set recoil/hit bits 0x880
 *       andi v1,  0xfffd             ; clear "alive/active" bit 0x2
 *       sh   v1,  0x5c(s2)
 *       lw   v0,  [enemy_hit_program_ptr 0x80077b2c]
 *       sw   v0,  0x70(s2)           ; +0x70 mover-VM program -> the HIT/DEATH program
 *
 *   PERMANENT-DESTROY BLOCK @0x800592cc (ONLY if s7 >= 2, i.e. bit 0x2):
 *       slti v0, s7, 2 ; bne -> 0x80059340        ; s7<2 skips the whole block
 *       jal  0x800503fc(0x800b0198)               ; spawn destroy FX
 *       sh   0, 0x62(s2)                          ; +0x62 = 0
 *       [0x800a658e] -= 1  @0x80059300            ; DECREMENT the quota  <-- the lever
 *       if ([0x800a658e]==0) jal 0x8005182c(0x80090b68) ; all-defeated event
 *       jal  0x80059e44(x=+0x4, y=+0x8, z=+0xc, a3=120)  ; spawn death pickup/particles
 *
 *   FINALISE @0x80059340 (both paths):
 *       jal  0x800498ac(s2, 1)       ; enemy per-frame update / death-anim advance
 *                                    ; (its own +0x6e==998 branch @0x800498cc also
 *                                    ;  spawns FX + decrements 0x800a658e — the
 *                                    ;  animated tail of the destroy)
 *   Then the legacy "-2 HP" side-table write @0x80059384 (enemy_hp_table 0x80089938,
 *   selector = equip index 0x800a6597; floors at 33, so it never reaches 0 and is NOT
 *   the kill). This is separate from the local +0x6e counter branch above.
 *
 * ---------------------------------------------------------------------------
 * OBSERVED AFTERMATH (spider chaser id 9, ~180 frames post-hit)
 * ---------------------------------------------------------------------------
 *   MEGA (temporary): +0x6e=999 held ~60f, +0x5c=0x4890, +0x70 swapped;
 *                     ~90f later removed from the 0x80090748 table; id LEFT = 9;
 *                     G_ENEMIES_REMAINING unchanged (21). Enemy is knocked out but
 *                     the quota still "owes" it -> the spawner may bring it back.
 *   GOLD  (permanent): identical recoil, but G_ENEMIES_REMAINING decremented AT the
 *                     hit (21->20), and ~90f later the enemy struct's +0x00 id is
 *                     ZEROED (slot fully retired). One gold berry == one permanent kill.
 *   RED / BLACKBERRY (spider movie): local +0x6e counter 2->1 on first hit, then
 *                     1->0 and final 999 marker on the second hit. No quota decrement.
 *
 * ---------------------------------------------------------------------------
 * ENEMY STRUCT DEATH FIELDS (chaser/mover actor)
 * ---------------------------------------------------------------------------
 *   +0x00  id            (u32; ZEROED on permanent destroy)
 *   +0x04/+0x08/+0x0c    world pos (death FX/pickup spawned here)
 *   +0x5c  state word    bit 0x40 = berry-TOUGH (worm); bits 0x880 = recoil/hit;
 *                        bit 0x2 = alive/active (cleared on hit);
 *                        bits 0xa0 (0x80|0x20) = already-hit -> handler skip @0x80058b54
 *   +0x60/+0x62          cleared on hit / destroy
 *   +0x6e  local hit counter before death on some actors; final tail writes 999
 *                        as death-anim trigger; 998 = delayed-destroy handoff in
 *                        fcn.800498ac
 *   +0x70  program ptr   swapped to the hit/death program from 0x80077b2c on hit
 * ============================================================================ */

#include "re_types.h"

#define G_ENEMIES_REMAINING     0x800a658eu  /* u16 permanent-kill quota (per level) */
#define G_ENEMY_HIT_PROGRAM_PTR 0x80077b2cu  /* mover-VM "got hit / die" program */
#define G_DAMAGEABLE_PTR_TABLE  0x80090748u  /* 64 * u32 enemy pointers */
#define G_ENEMY_HP_TABLE        0x80089938u  /* 5-byte HP records; NOT the kill path  */
#define G_BERRY_EQUIP_INDEX      0x800a6597u /* red0 blue1 homing2 gold3 mega4         */
#define ALL_DEFEATED_EVENT       0x8005182cu /* called with 0x80090b68 when quota==0   */
#define ENEMY_UPDATE_DEATHANIM   0x800498acu /* fcn(enemy, flags); +0x6e==998 tail     */
#define BERRY_TOUGH_DAMAGE_DISPATCH 0x8005905cu /* local +0x6e counter branch          */
#define ENEMY_HIT_COUNTER_STORE  0x800590e4u /* sh new local counter value             */
#define ENEMY_LOCAL_HIT_COUNTER_OFF 0x6e     /* counter first, 999 marker after death  */
#define HIT_RECORD_DAMAGE_CLASS_OFF 0x2c     /* contact record class byte in branch    */

/* s7 hit-strength bits set in contact_vs_actor_handler's per-enemy tail. */
#define HIT_TEMPORARY  0x1  /* mega/homing/blue/red: knock out, quota untouched   */
#define HIT_PERMANENT  0x2  /* GOLD (and LIKELY Mine Plant): decrements the quota  */

/* Pseudo-code of the permanence gate + destroy block (see header for the exact
 * MIPS). `hit_rec` = the connecting contact object (s1); `enemy` = struck actor (s2). */
static int enemy_hit_strength(const uint8_t *hit_rec)
{
    /* +0x24 == 11 is gold's connecting-object marker; +0x27 == 6 is the second
     * permanent lane (unverified: LIKELY the yellow Mine Plant, retail "same effect
     * class as Gold Berry; permanently eliminates enemies"). Anything else = temp. */
    int16_t f24 = *(const int16_t *)(hit_rec + 0x24);
    uint8_t f27 = hit_rec[0x27];
    if (f24 == 11 || f27 == 6) return HIT_PERMANENT | HIT_TEMPORARY;
    return HIT_TEMPORARY;
}

static int berry_actor_damage_delta(uint8_t damage_class)
{
    switch (damage_class) {
    case 0:
    case 12:
        return -2;
    case 1:
        return -99;
    case 127:
        return -4;
    case 128:
        return -3;
    default:
        return -1;
    }
}

static int apply_enemy_local_hit_counter(uint8_t *enemy, const uint8_t *hit_rec)
{
    int16_t hp = *(int16_t *)(enemy + ENEMY_LOCAL_HIT_COUNTER_OFF);
    if (hp >= 100) {
        return hp; /* 999 death marker and other high sentinels are exempt. */
    }

    hp = (int16_t)(hp + berry_actor_damage_delta(hit_rec[HIT_RECORD_DAMAGE_CLASS_OFF]));
    *(int16_t *)(enemy + ENEMY_LOCAL_HIT_COUNTER_OFF) = hp;
    return hp; /* hp > 0 waits for another hit; hp <= 0 enters the 999 tail. */
}

static void apply_enemy_hit(uint8_t *enemy, int s7)
{
    *(uint16_t *)(enemy + 0x6e) = 999;                 /* death-anim trigger */
    *(uint16_t *)(enemy + 0x60) = 0;
    uint16_t st = *(uint16_t *)(enemy + 0x5c);
    st |= 0x0880;                                      /* recoil/hit bits    */
    st &= (uint16_t)~0x0002;                           /* clear alive bit    */
    *(uint16_t *)(enemy + 0x5c) = st;
    *(uint32_t *)(enemy + 0x70) = *(uint32_t *)G_ENEMY_HIT_PROGRAM_PTR;

    if (s7 >= HIT_PERMANENT) {
        /* PERMANENT: spend one from the quota; fire the all-defeated event at 0. */
        /* spawn_destroy_fx(0x800b0198);  ((void(*)(void*))0x800503fc) */
        *(uint16_t *)(enemy + 0x62) = 0;
        uint16_t *quota = (uint16_t *)G_ENEMIES_REMAINING;
        if (--(*quota) == 0) {
            /* ((void(*)(void*))ALL_DEFEATED_EVENT)((void*)0x80090b68); */
        }
        /* spawn_death_pickup(enemy_x, enemy_y, enemy_z, 120);  0x80059e44 */
    }
    /* ((void(*)(void*,int))ENEMY_UPDATE_DEATHANIM)(enemy, 1);  finalises for both */
}

/* Referencing the helpers so a -Wunused build stays quiet; this file is a
 * documentation/decompilation artifact, not linked into the mod. */
void enemy_death_permanence_refs(void)
{
    (void)enemy_hit_strength;
    (void)berry_actor_damage_delta;
    (void)apply_enemy_local_hit_counter;
    (void)apply_enemy_hit;
}
