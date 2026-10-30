/* re_types.h — shared types/constants for A Bug's Life (SCUS-94288) hand-decompilation.
 *
 * SCOPE: only structs/fields/constants already SUPPORTED BY NOTES are declared here.
 *        Do NOT add speculative fields. Promote an `unkNN` to a named field ONLY when
 *        a decompiled function gives evidence (then update this file + the plan).
 *
 * Confidence markers used in comments: CONFIRMED / LIKELY / UNKNOWN / TODO.
 * Source of truth: ../ABL_RE_NOTES.md and ../docs/*.md.
 *
 * MIPS notes that callers must preserve when filling bodies:
 *   - lb/lh = sign-extended; lbu/lhu = zero-extended.
 *   - halfword/byte struct fields are real (do not widen silently).
 *   - GP-relative globals: gp = 0x80081d98 (runtime); [gp+off] == absolute 0x80081d98+off.
 *   - pointer-relative writes (e.g. value += DATbase; store back) are RELOCATIONS, model them as such.
 */
#ifndef ABL_RE_TYPES_H
#define ABL_RE_TYPES_H

#include <stdint.h>

/* ===========================================================================
 * DAT type-0x3f placement entry (0x10 bytes). CONFIRMED layout.
 * File offset of entry N within the type-0x3f record = 0x0008 + N*0x10.
 * Runtime world coord = file coord << 5 (CONFIRMED).
 * `kind` is the discriminator at +0x0c (low byte). The parser/dispatch read it
 * variously as byte or word; the meaningful value is the low byte (see enum below).
 * ===========================================================================*/
typedef struct Type3FEntry {
    int32_t x;          /* +0x00  CONFIRMED  X (runtime = x<<5) */
    int32_t y;          /* +0x04  CONFIRMED  Y (runtime = y<<5; more-negative = up) */
    int32_t z;          /* +0x08  CONFIRMED  Z (runtime = z<<5) */
    uint8_t kind;       /* +0x0c  CONFIRMED  source kind (see enum Type3FKind) */
    uint8_t onscreen;   /* +0x0d  CONFIRMED on-screen/eligibility flag: projector fcn.800253e8 sets
                         *        =1 when in view (else 0); source3f_dispatch requires ==1 to be live */
    int8_t  bob_base_lo;/* +0x0e  CONFIRMED (kind 0x30 gem): low byte of the s16 rest-height the bob
                         *        adds the sine to each frame (lh[entry+0x0e]); other kinds: unused */
    int8_t  bob_base_hi;/* +0x0f  (high byte of the +0x0e bob-base halfword) */
} Type3FEntry;          /* sizeof = 0x10 CONFIRMED */

/* ===========================================================================
 * Runtime contact/pickup record. Array base 0x800b0d18, 64 records, stride 0x38.
 * CONFIRMED fields: x/y/z (+0/4/8), action_id (+0x20), active_type (+0x22),
 * radius_add (+0x28), flags (+0x33). Other ranges left as unk (see metadata-table
 * fill in contact_alloc_80059e44.c; promote when a body confirms them).
 * ===========================================================================*/
/* Field map mostly CONFIRMED by Phase 3 (fcn.80059e44). Metadata table B = 0x8007941c[ctorType]
 * fills +0x20/+0x22/+0x24/+0x28/+0x2a/+0x2c/+0x2e/+0x2f/+0x30/+0x31/+0x33/+0x34/+0x35/+0x36;
 * render attrs +0x0c..+0x18 come from table A = 0x80079e30[stackArg] via fcn.800593e8. */
typedef struct ContactRecord {
    int32_t  x;            /* +0x00  CONFIRMED runtime X (file<<5) */
    int32_t  y;            /* +0x04  CONFIRMED runtime Y */
    int32_t  z;            /* +0x08  CONFIRMED runtime Z */
    int32_t  render_attr[4];/* +0x0c..+0x1b  LIKELY render/texture attrs (fcn.800593e8 from table A) */
    int32_t  unk1c;        /* +0x1c  CONFIRMED init = -1 */
    uint16_t action_id;    /* +0x20  CONFIRMED walker dispatch id (lhu, -2 -> table 0x8001b570) = metaB+0 */
    int16_t  active_type;  /* +0x22  CONFIRMED live gate (>0) = metaB+2 (or script-derived variant) */
    int16_t  init_val;     /* +0x24  CONFIRMED metaB+4 (or script-derived) */
    int16_t  init_val_copy;/* +0x26  CONFIRMED = copy of +0x24 */
    int16_t  radius_add;   /* +0x28  CONFIRMED contact radius addend (radius = 0x12c + radius_add) = metaB+8 */
    int16_t  unk2a;        /* +0x2a  CONFIRMED = metaB+0x0a */
    int16_t  unk2c;        /* +0x2c  CONFIRMED = metaB+0x0c (grain discriminator: 22 for ctor 0x51) */
    int8_t   unk2e;        /* +0x2e  CONFIRMED 0 / -ctorType / +ctorType per metaB+0x0e */
    uint8_t  unk2f;        /* +0x2f  CONFIRMED = metaB+0x0f */
    uint8_t  unk30;        /* +0x30  CONFIRMED = metaB+0x07 */
    uint8_t  unk31;        /* +0x31  CONFIRMED = metaB+0x06 */
    uint8_t  unk32;        /* +0x32  CONFIRMED const 0x20 */
    uint8_t  flags;        /* +0x33  CONFIRMED bit1(0x2)=enabled gate; bit7(0x80)=alloc-occupied = metaB+0x10 */
    uint8_t  unk34;        /* +0x34  CONFIRMED = metaB+0x11 */
    uint8_t  unk35;        /* +0x35  CONFIRMED = metaB+0x12 */
    uint8_t  unk36;        /* +0x36  CONFIRMED = metaB+0x13 */
    uint8_t  unk37;        /* +0x37  UNKNOWN */
} ContactRecord;           /* sizeof = 0x38 CONFIRMED */

/* ===========================================================================
 * Confirmed type-0x3f source kinds (LEVEL01, all in-game verified).
 * ===========================================================================*/
enum Type3FKind {
    KIND_FLIK_F                   = 0x10, /* CONFIRMED visible FLIK letter F (entry 50) */
    KIND_FLIK_L                   = 0x11, /* CONFIRMED FLIK L (entry 51) */
    KIND_FLIK_I                   = 0x12, /* CONFIRMED FLIK I (entry 52) */
    KIND_FLIK_K                   = 0x13, /* CONFIRMED FLIK K (entry 53) */
    KIND_GRAIN                    = 0x14, /* CONFIRMED grain (entries 0..49; HUD /50) */
    KIND_BERRY_GREEN_HOMING       = 0x21, /* CONFIRMED Green Berry / Homing Berry (entry 56) */
    KIND_BERRY_GOLD               = 0x22, /* CONFIRMED Gold Berry (entry 54) */
    KIND_BERRY_BLUE_SUPER         = 0x23, /* CONFIRMED Blueberry / Superberry (entry 55) */
    KIND_BERRY_PURPLE_MEGA_HOMING = 0x24, /* CONFIRMED Purple / Mega Homing Berry (entry 57) */
    KIND_TOKEN_ORANGE             = 0x29, /* CONFIRMED orange/red seed token (entries 63/64/65) */
    KIND_TOKEN_BLUE               = 0x2a, /* CONFIRMED blue seed token (entries 60/61/66) */
    KIND_TOKEN_GREEN              = 0x2b, /* CONFIRMED green seed token (entries 58/59/62) */
    KIND_GREEN_GEM                = 0x30, /* CONFIRMED green floating sparkly GEM (entries 67/68/69):
                                           * bobs every frame (source3f_dispatch kind-0x30 block,
                                           * Y = bob_base[+0xe] + sine - 800); rendered live from the
                                           * record by fcn.800253e8; its contact action doubles as a
                                           * telescope/hint-view trigger (clears player velocity on activation). Move via
                                           * record X/Z edit (live or DAT+rebuild); see INV note. */
};

/* ===========================================================================
 * Confirmed absolute global addresses (runtime RAM). gp = 0x80081d98.
 * Declared as comments/macros for reference; do not treat as C lvalues yet.
 * ===========================================================================*/
#define G_DAT_BASE_PTR     0x80082498u /* CONFIRMED [gp+0x700] = loaded DAT base pointer */
#define G_TYPE_TABLE       0x80096da0u /* CONFIRMED dynamic type-pointer table base (slot = type*4) */
#define G_TYPE3F_PTR       0x80096e9cu /* CONFIRMED = G_TYPE_TABLE + 0x3f*4 (type-0x3f record ptr) */
/* --- parser internals (CONFIRMED via Phase 1 fcn.8001cdc0) --- */
#define G_DAT_ENTRY_COUNTER 0x800822f0u /* CONFIRMED [gp+0x558] pass1+pass3 entry counter; retval = <<5 */
#define G_TRAIL_BLOCK_PTR   0x800824acu /* CONFIRMED [gp+0x714] trailing relocation-block ptr */
#define G_PASS2_BASE_PTR    0x80082338u /* CONFIRMED [gp+0x5a0] pass-2 structure base ptr */
#define G_PASS3_BASE_PTR    0x80082508u /* CONFIRMED [gp+0x770] pass-3 structure base ptr */
#define G_ALLOC_CURSOR     0x8008234cu /* CONFIRMED 64-slot contact alloc cursor (wraps at 0x40) */
#define G_CONTACT_ARRAY    0x800b0d18u /* CONFIRMED contact record array (64 * 0x38) */
#define G_METADATA_TABLE   0x8007941cu /* CONFIRMED constructor metadata table (stride 0x14) */
#define G_PLAYER_X         0x800a6500u /* CONFIRMED player/ref X (walker) */
#define G_PLAYER_Y         0x800a6504u /* CONFIRMED player/ref Y (walker subtracts 0x1cc0) */
#define G_PLAYER_Z         0x800a6508u /* CONFIRMED player/ref Z */
#define G_HARVESTER_STATE  0x800a657eu /* CONFIRMED s16: 0 unequipped, 1 equipped (C13 LEVEL01) */
#define G_POWERUP_FLAGS    0x800a6590u /* CONFIRMED player power/equipment bitfield */
#define POWERUP_HARVESTER  0x0080u     /* CONFIRMED harvester attraction/contact-kill enable */
#define G_BERRY_MARKER     0x800a6597u /* CONFIRMED berry/FLIK marker byte (set 1..4) */
#define G_PLANT_OUTPUT_BROWN  0x800a6598u /* packed selected-high / maximum-low */
#define G_PLANT_OUTPUT_BLUE   0x800a6599u
#define G_PLANT_OUTPUT_GREEN  0x800a659au
#define G_PLANT_OUTPUT_PURPLE 0x800a659bu
#define G_PLANT_OUTPUT_YELLOW 0x800a659cu
#define G_SEED_CTR_ORANGE G_PLANT_OUTPUT_BROWN /* compatibility aliases */
#define G_SEED_CTR_BLUE   G_PLANT_OUTPUT_BLUE
#define G_SEED_CTR_GREEN  G_PLANT_OUTPUT_GREEN
#define G_GRAIN_COUNT      0x800a65a1u /* CONFIRMED grain count byte (target 0x32 = 50); HUD mirror */
#define G_FLIK_PROGRESS_BITS 0x800a65a2u /* CONFIRMED HUD FLIK collected-bit display, bits 0..3 */
#define G_WALKER_DISPATCH  0x8001b570u /* CONFIRMED contact-walker jump table (index = action_id-2) */
#define G_GRAIN_TARGET     0x32        /* CONFIRMED grain target count (50) */
#define CONTACT_RADIUS_BASE 0x12c      /* CONFIRMED base contact radius (300); total = base + radius_add */

#endif /* ABL_RE_TYPES_H */
