/* ============================================================================
 * prop_decor_catalog.c — prop/foliage classes, hitbox model, payload-swap lever
 * ----------------------------------------------------------------------------
 * Survey 2026-07-03 over 13 operator fixtures (foliage/mushrooms/fences/stones/
 * acorns/clover/leaf/thorn/barrier/tree+swings/big berry/offering stone).
 * Vault: [[Prop and foliage catalog]] (screenshots in Assets/prop_catalog/).
 *
 * ---------------------------------------------------------------------------
 * DECOR CLASSES (who renders a prop)
 * ---------------------------------------------------------------------------
 *  PASS-1 instances  — LEVEL.DAT table @ trailing base (LEVEL01 file 0x1504),
 *    stride 0x14: {s32 X,Y,Z (FILE scale; world = <<5), +0xc ?, +0x10 payload
 *    ptr (baked file-offset -> relocated at load; runtime = 0x801bxxxx)}.
 *    500+ records in LEVEL01. Fixtures matched: big_berry #117, acorn #214/
 *    #209, clover #420, huge_stone #431, tree-complex parts #87/#44,
 *    foliage-stalk #407.
 *  PASS-3 decor      — same shape @ file 0x3AEC; XYZ = CULL ANCHOR
 *    (suppression levers known). Fixture: weird_structure #139/#136.
 *  TERRAIN-BAKED     — geometry inside the DAT terrain payloads (fcn.80010000):
 *    mushroom clusters, wooden fence lines, thornplant, barrier, ground leaf,
 *    offering stone + RAMP (ramps = terrain mesh + sector slope collision),
 *    and the boundary grass-blade rim (chunk-35 family). NOT individually
 *    placeable records.
 *
 * ---------------------------------------------------------------------------
 * THE PAYLOAD-SWAP LEVER (NEW, live-proven 2026-07-03)
 * ---------------------------------------------------------------------------
 *  Swapping two pass-1 records' +0x10 payload pointers AT RUNTIME re-renders
 *  the props immediately (acorn -> rolled-leaf tube in front of Flik; 9.04%
 *  of the frame changed). The renderer consumes the pointer per frame.
 *  => pass-1 = a general prop-placement system: POSITION (+0/4/8, proven
 *  earlier) and MODEL (+0x10, proven now) are both data-driven. On disc the
 *  field is a relocation site (dat_reloc handles it).
 *
 * ---------------------------------------------------------------------------
 * HITBOX MODEL
 * ---------------------------------------------------------------------------
 *  No prop carries its own collision. Solidity = chunk-32 sector collision
 *  planes placed along the visuals (visual != collision, reconfirmed):
 *    blocked  : big_berry (walk 2.7k), wooden fence (~10k), boundary foliage
 *               (~9-11k = the level-edge planes)
 *    walkable : mushrooms (15-18k), thornplant (35-49k), leaf, clover
 *  Tier-3 equivalence: place visuals freely; add tier3_collision AABB walls
 *  where solidity is wanted (mirrors the native design exactly).
 *
 * ANIMATION / SWINGS (RESOLVED 2026-07-03, on_swing.sav):
 *   Swinging is a PLAYER MODE: player mode field 0x800a6580 = 5 while riding
 *   (0 on ground; the same enum the cannon/seed modes use). Flik's position is
 *   pendulum-driven THROUGH THE STANDARD INTEGRATOR (sole X writer 0x80036d20,
 *   the movement-integrator family; oscillation ~18k Z amplitude observed).
 *   The swing prop itself is passive decor; attach = contact -> mode 5.
 *   Residual: the pendulum pivot/params data source.
 *
 * PASS-2 (RESOLVED 2026-07-03): G_PASS2_BASE_PTR (-> datbase+0x3ae8) marks the
 *   END SENTINEL (0xFFFFFFFF) of the pass-2 region; pass-2 is the MESH/SCALE
 *   REGISTRATION pass (payload ptrs + 0x8000 fixed-point scale halfwords;
 *   parser deref chain [R+0x10]/[s4+0x18], output table @0x80091210) — NOT a
 *   placement table, which is why no per-prop pass-2 records exist. Pass-3
 *   placements begin right after at +0x3aec (the earlier scan base was right).
 *
 * PALETTE (tools/dump_pass1_palette.py, run 2026-07-03): 484 distinct pass-1
 *   payload pointers on LEVEL01, and EVERY one is content-unique (per-instance
 *   baked mesh blobs) -> the visual thumbnails are the dedupe/pick mechanism;
 *   multiple records may share one blob (the swap POC did). Output:
 *   build/pass1_palette/{payload_*.png, palette.json, model_groups.json}.
 * ============================================================================ */

#include "re_types.h"

#define PASS1_FILE_BASE_L01   0x1504   /* stride 0x14; XYZ file<<5; +0x10 payload */
#define PASS3_FILE_BASE_L01   0x3AEC   /* same shape; XYZ = cull anchor            */
#define PASS1_PAYLOAD_OFF     0x10     /* SWAPPABLE (live-proven) model selector   */
#define PASS1_STRIDE          0x14

void prop_decor_catalog_refs(void)
{
    volatile int t = PASS1_FILE_BASE_L01 + PASS3_FILE_BASE_L01 +
                     PASS1_PAYLOAD_OFF + PASS1_STRIDE;
    (void)t;
}
