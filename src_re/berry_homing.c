/* ============================================================================
 * berry_homing.c — homing/mega berry target acquisition + seek
 * ----------------------------------------------------------------------------
 * RCG-031 ("Homing berry target acquisition"). Live-traced 2026-07-03 (isolated
 * DuckStation, SCUS-94288, homing_berry.sav): threw a homing berry, breakpointed
 * the spawner, and disassembled the caller that chooses the target.
 * Complements [[Berry projectile and homing]] (the seek math + param table).
 *
 * SUMMARY: a homing/mega throw spawns a primary berry (type 8/45). When that
 * primary reaches its subtype cleanup transition, FUNC_8005743C ACQUIRES the
 * NEAREST valid enemy and spawns a homing PROJECTILE (type 16/48) carrying that
 * enemy as its target. The projectile updater (berry_projectile_update
 * 0x8005a308) then steers toward that one target.
 *
 * ---------------------------------------------------------------------------
 * ACQUISITION — FUNC_8005743C (0x8005743c..0x8005761c)
 * ---------------------------------------------------------------------------
 *   a0 = the primary berry contact object (s0); a1 = a mode selector (s2, 1/2 →
 *   how many homers to spawn). It scans the damageable-object pointer table and
 *   picks the closest targetable enemy in XZ:
 *
 *       best = NULL; bestDist2 = 0x7fffffff;
 *       for (p = 0x80090748; *p != NULL; p++) {            // damageable table
 *           enemy = *p;
 *           st = enemy[+0x5c];                             // state word
 *           if (!(st & 0x0001)) continue;                  // must be targetable
 *           if (st & 0x00a0) continue;                     // skip already-hit/dead (0x80|0x20)
 *           dx = (berry.x - enemy[+0x4]) >> 5;             // XZ only, Y ignored
 *           dz = (berry.z - enemy[+0xc]) >> 5;
 *           d2 = dx*dx + dz*dz;
 *           if (d2 < bestDist2) { best = enemy; bestDist2 = d2; }
 *       }
 *       if (best) spawn_homing_projectile(target = best);  // else no homer this frame
 *
 *   The chosen `best` (a POINTER to the enemy struct) is passed to the projectile
 *   spawner (contact_object_spawn 0x8005a0e0) in the t1 arg slot → lands in the
 *   projectile's record at +0x10 (the target field). Straight berries (red/blue/
 *   gold) lack the homing bit and never run this — they fly the throw vector.
 *
 * ---------------------------------------------------------------------------
 * SEEK — berry_projectile_update 0x8005a308 (per the homing-record branch)
 * ---------------------------------------------------------------------------
 *   For a record with the homing bit (+0x33 & 0x8):
 *     target = record[+0x10];                              // -1 => none (aim off Flik)
 *     if (target != -1) {
 *         // read the target's LIVE world position from its transform/bone table
 *         pos = *(short*)(target[+0x74] + target[+0x44]*16 + ...);
 *         if (target[+0x6e] == 0 || (target[+0x5c] & 0x0880))  // dead/invalid
 *             record[+0x22] = 1;                           // -> expire the berry
 *         bearing = atan2_heading(pos - berry);            // 0x80060ae4
 *         heading += (bearing - heading) & 0xfff) >> 2;    // rate-limited turn
 *     }
 *   velocity is rebuilt from the sin table by heading each tick (fixed >>3 scale).
 *   No child-updater path calls FUNC_8005743C again: target loss retires the
 *   projectile through the normal timer/cleanup path rather than retargeting it.
 *
 * NOTE: acquisition is by the BERRY's current position (starts at Flik), nearest in
 * XZ — which is why homing can pass a berry-tough enemy (e.g. the worm) when a nearer
 * targetable enemy wins the scan.
 *
 * VERIFICATION (2026-07-03, 5 saves): an independent Python replica of this scan
 * matched the game's chosen target 4/4 where the acquisition ran — homing_berry,
 * mega_homing_berry, spider_walking (all → id 9, the nearest) and mosquito (→ id 10,
 * NOT id 9, because id 9 was ~9x farther — proving it is genuinely nearest-based, not
 * a fixed pick). FILTER proven to drive selection: invalidating the nearest enemy at
 * the scan entry (clear +0x5c bit 0x1 / set the hit bit) made the game switch to the
 * next-nearest VALID enemy (id 9 -> id 10), matching the model. (worm.sav did not
 * spawn a homer — no valid target engaged that throw.)
 *
 * BLACKBERRY NOTE (2026-07-07): the active Blackberry/Fastberry maps equip index
 * 5 to the native red straight-throw path and speeds the spawned contact record;
 * it intentionally does not enter this homing acquisition path.
 * ============================================================================ */

#include "re_types.h"

#define G_DAMAGEABLE_PTR_TABLE 0x80090748u  /* 64 * u32 enemy pointers, NULL-terminated scan */
#define BERRY_TARGET_OFF       0x10         /* homing projectile record: target enemy pointer  */
#define BERRY_HOMING_BIT       0x8          /* record +0x33 bit 0x8 = homing (seek) enabled     */
#define ENEMY_STATE_OFF        0x5c         /* +0x5c: bit 0x1 = targetable; bits 0xa0 = hit/dead */
#define ATAN2_HEADING          0x80060ae4u

/* Reference so the constants read as used under -Wall. */
void berry_homing_refs(void)
{
    volatile unsigned t = G_DAMAGEABLE_PTR_TABLE ^ (BERRY_TARGET_OFF + BERRY_HOMING_BIT + ENEMY_STATE_OFF);
    (void)t;
}
