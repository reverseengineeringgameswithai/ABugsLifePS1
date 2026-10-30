/* ============================================================================
 * enemy_drops.c — enemy death drops (health leaf) + berry-pickup drop machinery
 * ----------------------------------------------------------------------------
 * Supports the "gold-berry drop on non-gold kill" mod (mod/patch_golddrop.asm).
 * CONFIDENCE : CONFIRMED live (isolated DuckStation, SCUS-94288, health_drop.sav
 *              + spider_walking.sav). Method: breakpoints on the death-anim handler
 *              and the drop-spawn fn; plus 2026-07-07 operator confirmation that the
 *              mod's type-120 floor glyph is walk-collectible and increments the
 *              bottom gold-defeat counter.
 *
 * ---------------------------------------------------------------------------
 * spawn_drop / generic contact-object spawner — 0x80059e44
 * ---------------------------------------------------------------------------
 *   void spawn_drop(int x, int y, int z, int type, int extra);   // extra passed at [sp+0x10]
 *   - Allocates a contact object (round-robin cursor 0x8008234c, array 0x800b0d18,
 *     stride 0x38, 64 slots; skips "protected" slots).
 *   - type  indexes contact_metadata_table_b (0x8007941c, stride 20): the record's
 *     action_id (+0x20), model, timer, flags come from table_b[type].
 *   - extra indexes contact_metadata_table_a (0x80079e30, stride 20): the initial
 *     scatter velocity (built via 0x800593e8 from nibble fields) so the drop "pops out".
 *   Also the general effects/particles spawner (called constantly with many types).
 *
 * ---------------------------------------------------------------------------
 * The one-shot-per-death drop roll — death-anim handler fcn.800498ac
 * ---------------------------------------------------------------------------
 * The health-leaf random drop lives at 0x8004999c..0x80049a18 (runs ONCE per enemy
 * death; s0 = the dying enemy, pos at +0x4/+0x8/+0xc):
 *     if ([0x800a6594] < 4) {                         // per-level drops-so-far cap
 *         rng = *(*[0x800822f4])++;                    // script-cursor entropy byte
 *         if ((rng & ((2 << [0x800a6594]) - 1)) == 0   // 1/2,1/4,1/8,1/16 (rarer per drop)
 *             && !(enemy[+0x5c] & 0x40)) {             // skip berry-TOUGH enemies
 *             spawn_drop(enemy_x, enemy_y - 0x1000, enemy_z, 38, 13);  // 38 = health leaf
 *         }
 *     }
 * The current gold-drop mod does NOT hook this per-frame death-animation updater.
 * A forced-drop trace showed 0x80049958 can run six times for one spider death,
 * minting duplicate tokens. The mod now hooks the one-shot contact-vs-actor
 * hit/death tail at 0x800592A4 and spawns a collectible type-120 spinning
 * gold-kill glyph tagged with the enemy pointer.
 *
 * ---------------------------------------------------------------------------
 * DROP TYPES (contact_metadata_table_b[type].action_id = collect behaviour)
 * ---------------------------------------------------------------------------
 *   type 34 -> action_id 34 : ARM GOLD  (walker handler 0x80058954: equip=3)
 *   type 33 -> action_id 33 : arm homing (0x80058940: equip=2)
 *   type 32 -> action_id 36 : arm mega   (0x80058978: equip=4)
 *   type 35 -> action_id 35 : arm equip=s7 (0x80058968)
 *   type 38  -> action_id   9 : health leaf (0x80058864: heals; SFX 62)
 *   type 120 -> action_id 123 : spinning gold-kill glyph; native permanent-kill visual
 *   (types 32-35 model 240 = the berry-icon pickups; 38 model 210 = leaf)
 *
 * ---------------------------------------------------------------------------
 * COLLECT DISPATCH — walker fcn.800586b0, table contact_action_dispatch 0x8001b570
 * ---------------------------------------------------------------------------
 * When Flik overlaps a drop, the walker dispatches by action_id: idx = action_id - 2,
 * jr [0x8001b570 + idx*4]. The berry-arm handlers all do `sb <idx>, 0x6597(0x800a)`
 * (equip index) + a pickup SFX. A literal type-34 drop, on contact, ARMS GOLD -> the
 * player then permanently kills enemies (see enemy_death_permanence.c / RCG-022).
 * The gold-drop mod intentionally avoids that path: it uses type 120/action 123 and
 * a default-branch pickup hook so walking over the glyph credits the tagged enemy
 * directly instead of replacing Flik's equipped berries.
 *
 * ---------------------------------------------------------------------------
 * DROP LIFECYCLE / BEHAVIOUR (live-verified 2026-07-03; mod update 2026-07-07)
 * ---------------------------------------------------------------------------
 *   - HEALTH LEAF: the retail drop roll runs in the death-anim drop section and is
 *     capped by [0x800a6594] < 4 with rarer per-drop odds: 1/(2<<count).
 *   - GOLD-DROP MOD: the current roll runs at 0x800592A4, the one-shot hit/death
 *     tail. It is per-berry gated and emits one tagged type-120 spinning glyph;
 *     collecting it pulses the misc/gold counter, decrements 0x800a658e, and
 *     finalizes that enemy through the native permanent-kill cleanup shape. The
 *     bottom counter advances because HUD code displays total enemies minus
 *     enemies remaining: LW(0x80082258) - LH(0x800a658e).
 *   - DROP LIFETIME: a spawned drop is a contact object whose record +0x22 timer counts down
 *     ~1 per 2 display frames from ~229 -> despawns after ~229 ticks (~7-8 s) if not collected.
 *   - PICKUP RADIUS is generous (the walker's 0x12c + rec[+0x28]); a drop spawned right on
 *     Flik is auto-vacuumed the same/next frame.
 *   - CHASER RESPAWN (relevant to farming drops): chasers are area-spawned (spawn-area records
 *     in LEVEL.DAT). A killed chaser did NOT respawn in place / on a timer over ~12 s of local
 *     movement; respawn requires re-arming the spawn area (leave the region and return). This
 *     is base-game behaviour, orthogonal to the drop roll.
 * ============================================================================ */

#include "re_types.h"

#define SPAWN_DROP            0x80059e44u
#define CONTACT_META_B        0x8007941cu  /* [type]  stride 20: action_id/model/flags */
#define CONTACT_META_A        0x80079e30u  /* [extra] stride 20: scatter velocity      */
#define CONTACT_ARRAY         0x800b0d18u
#define DEATHANIM_HANDLER     0x800498acu
#define WALKER_ACTION_DISPATCH 0x8001b570u /* jr [+ (action_id-2)*4] */
#define G_EQUIP_INDEX         0x800a6597u  /* red0 blue1 homing2 gold3 mega4 blackberry5 */
#define G_DROPS_SO_FAR        0x800a6594u  /* health-leaf per-level cap/rarity counter   */
#define G_RNG_CURSOR          0x800822f4u  /* script cursor ptr; *ptr = entropy byte     */

enum DropType {
    DROP_ARM_MEGA   = 32,
    DROP_ARM_HOMING = 33,
    DROP_ARM_GOLD   = 34,   /* literal gold-berry pickup: collect -> equip gold */
    DROP_ARM_EQUIPS7= 35,
    DROP_HEALTH_LEAF= 38,
    DROP_GOLD_KILL_GLYPH = 120, /* mod drop: walk over -> credit tagged enemy */
};

enum DropAction {
    ACTION_GOLD_KILL_GLYPH = 123, /* type-120 default-branch action guarded by the mod */
};

/* Reference so the header's constants read as "used" in a -Wall build. */
void enemy_drops_refs(void)
{
    volatile int t = DROP_ARM_GOLD + DROP_HEALTH_LEAF +
        DROP_GOLD_KILL_GLYPH + ACTION_GOLD_KILL_GLYPH;
    (void)t;
}
