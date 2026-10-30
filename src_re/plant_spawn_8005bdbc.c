/* RCA a4 (2026-07-09): SUPERSEDED for build purposes — 0x8005bdbc is byte-matched in the
   shipping build as asm/hand_written/8005bdbc_plant_spawn.s (config/segments.yml `attempted`;
   validate_build.py SHA-1 PASS). This src_re file is documentation-grade pseudocode,
   retained for its analysis/comments; it is NOT the build unit. */
/* ============================================================================
 * plant_spawn_8005bdbc.c — seed→plant spawner + plant slot machinery [HRE-004 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESSES : fcn.8005bdbc (plant spawner, bounds 0x8005bdbc..0x8005bfb8,
 *                      functionBounds confidence "exact"); fcn.8003e760 (token
 *                      descriptor re-skin); plant behavior walker 0x8005bfbc..
 *                      (jump table 0x8001b848, types 2..14); plant renderer slot
 *                      read at 0x80021354..0x800213c8.
 * CONFIDENCE         : CONFIRMED selection law, type/extra table, slot layout,
 *                      model-table binding, override byte (all live-verified on
 *                      LEVEL01 fixture SCUS-94288_8.sav, 20/20 matrix combos).
 *                      Type-6/7 handler bodies partially decoded (labelled).
 * SOURCE NOTES       : ObsidianVault/Systems/Seed plant output binding.md,
 *                      Seed planting system.md, r2 disasm (MIPS LE, EXE base
 *                      file_off = vaddr - 0x8000f800).
 * KNOWN CALLERS      : 0x8004d4e0 (seed actor update — natural jump-on-seed path,
 *                      after the sink timer expires), 0x8005bd58 (local wrapper).
 * KNOWN CALLEES      : contact_alloc 0x80059e44 (type-6 berry/shield spawn, seed
 *                      sink dirt puffs).
 * KNOWN GLOBALS      : see #defines. Token counters 0x800a6598..9c are CONTIGUOUS,
 *                      one byte per lane (kinds 0x29..0x2d), stored as n*17.
 * UNRESOLVED         : purple-lane ctor 0x20..0x23 -> berry kind/marker map (table
 *                      B 0x8007941c rows 0x1f..0x23 undecoded); per-level plant
 *                      model manifest source on disc; scene-0x11 special seed path.
 *
 * IMPORTANT CONTEXT:
 *   fcn.8003e760 (called on token PICKUP) does NOT choose the plant — it only
 *   re-skins the pickup sprite descriptor. The plant is chosen at PLANT time
 *   (jump-on-seed) by fcn.8005bdbc from the seed record's color byte + the lane
 *   counter, or from a per-seed override byte. Models bind 1:1: type N renders
 *   PLANTNN.ALL (per-level table 0x800a649c; NULL = model not loaded in this
 *   level -> functioning but invisible actor).
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LBU(p)  (*(uint8_t  *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))
#define SH(p,v) (*(uint16_t *)(p) = (uint16_t)(v))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))

#define G_SCENE_ID            0x80082504u
#define G_SEED_COUNTERS       0x800a6598u /* [5] lanes: 0x29 orange,0x2a blue,0x2b green,0x2c,0x2d */
#define G_PLANT_TYPE_TABLE    0x8007a448u /* [20] {u16 type, u16 extra}, idx = color*4+count-1 */
#define G_PLANT_DATA_TABLE    0x8007a40cu /* [15] ptr -> growth-anim script per type (0 = none) */
#define G_PLANT_SLOTS         0x80090bf0u /* [20] stride 0x30 */
#define G_PLANT_SLOT_CURSOR   0x800822b8u /* next slot, wraps at 0x14, skips occupied */
#define G_PLANT_MODEL_TABLE   0x800a649cu /* [15] per-LEVEL model ptrs; type N -> PLANTNN.ALL image */
#define G_PLANT_BEHAV_TABLE   0x8001b848u /* [13] handlers, index type-2 (see list at bottom) */
#define G_PLANT_NAME_TABLE    0x8001baf8u /* "plants\plant01".."plants2\plant14", stride 0x10 */
#define G_OBJ_DESC_LIST       0x80096b98u /* object_pointer_list: kind -> render descriptor */

/* PlantSlot — 0x30 bytes @ G_PLANT_SLOTS + n*0x30 (CONFIRMED field map) */
typedef struct {
    int16_t  type;        /* +0x00  0 = free; 1..14 = plant type (== PLANTxx.ALL number) */
    int16_t  data_w2;     /* +0x02  word2 of the type's data block */
    int32_t  anim_hi;     /* +0x04  first byte of anim seq << 16 */
    int32_t  x, y, z;     /* +0x08  y = seed.y - (rooted ? 0x4800 : 0x4000)  (-Y up) */
    int32_t  zero_14;     /* +0x14 */
    uint8_t *anim_seq;    /* +0x18  frame-sequence ptr (0x8007a0b0-family) */
    uint8_t *data_cursor; /* +0x1c  walks the type data block */
    void    *seed_actor;  /* +0x20  back-pointer to the seed base struct */
    int16_t  zero_24;     /* +0x24 */
    int16_t  data_w0;     /* +0x26  word0 of the type's data block */
    int16_t  zero_28, zero_2a, zero_2c;
    uint16_t extra_state; /* +0x2e  table `extra` | runtime bits (bit2 mature/visible,
                           *        bit3 berry-spawned-once, low bits growth phase) */
} PlantSlot;

extern ContactRecord *contact_alloc(int32_t x, int32_t y, int32_t z, int ctorType, int stackArg);

/* ----------------------------------------------------------------------------
 * fcn.8003e760 — token pickup visual re-skin (kinds 0x29..0x2d handlers).
 * objIndex per lane: 0x29->0x16 (hardcoded), 0x2a..0x2d -> table 0x80078e90
 * = {0x17,0x19,0x18,0x2f}. Writes level into the sprite descriptor only:
 * a 4x4 texture-atlas selector (even bytes +8..+0x12 = U | level<<6; the odd
 * bytes carry the lane row 0x00/0x40/0x80/0xc0). Does NOT touch plant state.
 * ---------------------------------------------------------------------------- */
void fcn_8003e760(int objIndex, int level)
{
    uint8_t *desc = (uint8_t *)(uintptr_t)LW(G_OBJ_DESC_LIST + objIndex * 4);
    SH(desc + 6, (LHU(desc + 6) & 0xfffcu) + level);
    for (int off = 8; off < 0x14; off += 2) {
        SB(desc + off, (LBU(desc + off) & 0x3f) | (level << 6));
    }
}

/* ----------------------------------------------------------------------------
 * fcn.8005bdbc — plant spawner. a0 = seed actor (base struct, stride 0x84 array
 * at 0x800a0014). Natural caller = seed actor update 0x8004d4e0, invoked when
 * the jump-on-seed sink state (+0x5c bit 0x20, timer +0x6c, Y+=0x800/frame with
 * dirt-puff contact_alloc ctor [0x800910a3]+0x1b) expires. Also sets the seed's
 * re-plant cooldown (+0x62 = 0x2710) and writes the seed position back to its
 * record when record[+0xd]==0 (caller side).
 * ---------------------------------------------------------------------------- */
void plant_spawn_8005bdbc(uint8_t *seed)
{
    /* Special case: scene 0x11 with actor 0x8009fe04 -> clear 0x8009fe66, no plant. */
    if (LW(G_SCENE_ID) == 0x11 && seed == (uint8_t *)0x8009fe04u) {
        SH(0x8009fe66u, 0);
        return;
    }

    uint8_t *record  = (uint8_t *)(uintptr_t)LW(seed + 0x80); /* runtime copy of the
                                            LEVEL.RAW chunk-31 seed record; meta maps 1:1
                                            (file +0xe = color, +0xf = override) */
    int      override = LBU(record + 0xf);
    int      idx;
    if (override != 0) {
        idx = (override & 0xf) * 4 + (override >> 4);     /* low nib = color, high = count-1 */
    } else {
        int color = LBU(record + 0xe);                    /* 0..4 */
        int count = LBU(G_SEED_COUNTERS + color) >> 4;    /* stored n*17 -> n */
        idx = color * 4 + count - 1;                      /* 0..19 */
    }

    int y_lift = (LW(seed + 0x40) < 3) ? 0x1000 : 0x800;  /* +0x40==3 = rooted/stuck seed */

    int slot_i = LW(G_PLANT_SLOT_CURSOR);
    PlantSlot *slot = (PlantSlot *)(G_PLANT_SLOTS + slot_i * 0x30);

    slot->type = LH(G_PLANT_TYPE_TABLE + idx * 4);
    slot->x = LW(seed + 0x4);
    slot->y = LW(seed + 0x8) + (y_lift - 0x5000);         /* 0x4000/0x4800 above the seed */
    slot->z = LW(seed + 0xc);
    slot->zero_14 = 0;

    uint8_t *data = (uint8_t *)(uintptr_t)LW(G_PLANT_DATA_TABLE + slot->type * 4);
    slot->data_cursor = data + 12;                        /* consumes 3 words: */
    slot->data_w0   = (int16_t)LW(data);                  /*   word0 -> +0x26 */
    slot->anim_seq  = (uint8_t *)(uintptr_t)LW(data + 4); /*   word1 -> +0x18 */
    slot->data_w2   = (int16_t)LW(data + 8);              /*   word2 -> +0x02 */
    slot->zero_24   = 0;
    slot->anim_hi   = LBU(slot->anim_seq) << 16;
    slot->seed_actor = seed;
    slot->zero_28 = slot->zero_2a = slot->zero_2c = 0;
    slot->extra_state = LHU(G_PLANT_TYPE_TABLE + idx * 4 + 2);  /* `extra` halfword */

    if (LH(seed + 0x62) != 0) SH(seed + 0x62, 0x2710);    /* re-plant cooldown */

    /* advance cursor mod 0x14, skipping occupied slots */
    do {
        slot_i = LW(G_PLANT_SLOT_CURSOR) + 1;
        if (slot_i >= 0x14) slot_i = 0;
        SW(G_PLANT_SLOT_CURSOR, slot_i);
    } while (LH(G_PLANT_SLOTS + slot_i * 0x30) != 0);
}

/* ----------------------------------------------------------------------------
 * Plant behavior walker 0x8005bfbc — iterates the 20 slots; when a slot is
 * mature (extra_state & 4) and 2 <= type <= 14, dispatches jr via
 * G_PLANT_BEHAV_TABLE[type-2]:
 *   type  2 0x8005c110 cannon launch        type  3 0x8005c258 propeller lift
 *   type  5 0x8005c58c trampoline bounce    type  6 0x8005c6f0 berry/shield (below)
 *   type  7 0x8005c744 direct effect fruit  type  8 0x8005c818 dandelion
 *   type 11 0x8005c918 mine                 type 13 0x8005ca24 purple-berry shooter
 *   type 14 0x8005ca7c blue-berry shooter   types 4/9/10/12 -> 0x8005cce8 passive
 * ---------------------------------------------------------------------------- */

/* type-6 handler 0x8005c6f0 (CONFIRMED): berry-cluster / bubble-shield plant.
 * Once mature ((+0x2c flags & 0xA0000) == 0x20000), spawns ONE contact object:
 *   ctor 0x1f       = bubble shield        (extra 0x0000, blue x3)
 *   ctor 0x20..0x23 = berry grants         (extra 0x1000..0x4000, purple lane)
 * then latches extra_state bit3 so it fires once. ctor -> berry kind map = OPEN. */
void plant_type6_mature_8005c6f0(PlantSlot *slot)
{
    if ((LW((uint8_t *)slot + 0x2c) & 0xA0000) != 0x20000) return;
    contact_alloc(slot->x, slot->y - 0x1400, slot->z,
                  ((int16_t)(slot->extra_state) >> 12) + 0x1f, 3);
    slot->extra_state |= 8;
}

/* type-7 handler 0x8005c744 (PARTIAL): direct-effect fruit plant. Gates on
 * slot->data_w2 == 2 && slot->anim_hi == 0x80000; extra selects the effect:
 * 0x2000 invincibility, 0x3000 health, 0x4000 super jump (0x8005c764+ checks
 * extra & 0x4000 first; body/SFX detail undecoded). */

/* ----------------------------------------------------------------------------
 * Renderer slot read 0x80021354..: for each slot with type != 0, model =
 * LW(G_PLANT_MODEL_TABLE + type*4) — per-LEVEL table, NULL when the level's
 * manifest didn't load that PLANTxx file (LEVEL01 loads types 2..10 only, in
 * memory order 5,7,4,10,9,3,8,2,6). Model file identity CONFIRMED: each RAM
 * region is [type header + anim block + PLANTNN.ALL image] and images chain
 * end-to-end (image end + 8 = next type header).
 *
 * HRE-004 MATRIX (G_PLANT_TYPE_TABLE, live-verified 20/20):
 *   lane 0 brown : 5 mushroom, 3 propeller, 8 dandelion, 2 cannon
 *   lane 1 blue  : 7/0x2000 invinc, 7/0x3000 health, 6/0x0 shield, 7/0x4000 superjump
 *   lane 2 green : 4 leaf, 10 tall leaf, 9 3-leaf climber, 1 rose climber
 *   lane 3 purple: 6/0x4000, 6/0x2000, 6/0x1000, 6/0x3000 (berry grants)
 *   lane 4 yellow: 14 blue shooter, 13 purple shooter, 11 mine, 11 mine (dup)
 * Type 12 (PLANT12.ALL) is reachable ONLY via the record override byte.
 * ---------------------------------------------------------------------------- */
