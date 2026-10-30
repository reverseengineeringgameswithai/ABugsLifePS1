/* RCA a4 (2026-07-09): SUPERSEDED for build purposes — 0x80014360 is byte-matched in the
   shipping build as asm/hand_written/80014360_pass3_backdrop_cull.s (config/segments.yml `attempted`;
   validate_build.py SHA-1 PASS). This src_re file is documentation-grade pseudocode,
   retained for its analysis/comments; it is NOT the build unit. */
/* ============================================================================
 * pass3_backdrop_cull_80014360.c — pass-3 decor record culler [HRE-001 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESSES : FUNC_80014360 (bounds 0x80014360..0x80014500, functionBounds
 *                      confidence "exact"). Visible-list consumers: 0x8001EAD8 and
 *                      0x8002074C (two passes inside the unified mesh builder,
 *                      see world_render_dispatch.c).
 * CONFIDENCE         : CONFIRMED record layout, enable bitmap, cull output list,
 *                      cull-anchor-vs-draw-position split (live phase-matched A/B).
 *                      GTE cull constants CONFIRMED from disasm; the caller's
 *                      matrix/camera args (a1/a2 structs) not field-mapped.
 * SOURCE NOTES       : ObsidianVault/Findings/Finding - Pass-3 decor records
 *                      decoded (cull anchor + suppression).md; r2 + live disasm.
 * KNOWN CALLERS      : per-frame render dispatch (reads every rendered frame;
 *                      exact call site not traced).
 * UNRESOLVED         : enable-bitmap initializer (static post-load, all-1s in
 *                      LEVEL01; no per-frame writers); the draw transform for
 *                      pass-3 payloads (world-baked vs rotation-only backdrop
 *                      pass — record anchor projects behind the camera yet the
 *                      prop renders); a1/a2 argument struct layouts.
 *
 * IMPORTANT CONTEXT:
 *   Pass-3 records (LEVEL01 LEVEL.DAT, TRUE base file 0x3AEC, 140 × 0x14, same
 *   field layout as pass-1: {s32 X,Y,Z; u16 extent; u16 flags; u32 src}) are
 *   CULL VOLUMES, not draw anchors. Moving a record's XYZ does NOT move the
 *   drawn prop (0-pixel A/B); moving it far away CULLS the prop (= source-side
 *   suppression, a size-preserving 12-byte uncompressed-DAT edit). The historical
 *   "p3base=0x3AFA, src@+2" parse was misaligned +0xE bytes — its src reads were
 *   accidentally correct, its "position" reads straddled records (the origin of
 *   the "undecoded position field" myth). Sentinel all-0x8000 records bracket the
 *   table at 0x3AD8 and 0x45DC; the walker stops on flags<0 (s16).
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LB(p)   (*(int8_t   *)(p))

#define G_DATBASE            0x801607F8u /* LEVEL.DAT load base (LEVEL01) */
#define P3_TABLE_FILE_OFF    0x3AECu     /* TRUE pass-3 table base (140 records) */
#define G_P3_ENABLE_BITMAP   0x800902C7u /* bytes walk DOWN from here, MSB first:
                                          * record r -> byte (this - (r>>3)), mask 0x80>>(r&7).
                                          * Static after load (no per-frame writers); all-1s
                                          * in LEVEL01. Clearing a bit suppresses that prop. */
#define G_P3_VISIBLE_LIST    0x80096EA8u /* out: record-base ptrs (low bit = tag) */
#define G_DRAW_DISTANCE      0x8008238Cu /* >>2 = far window used by the cull */

/* Pass-3 record — IDENTICAL layout to the pass-1 trailer records, but different
 * semantics: XYZ is the cull anchor only (pass-1 XYZ is the draw anchor). */
typedef struct {
    int32_t  x, y, z;     /* +0x00 cull anchor, file/placement frame (Y-up) */
    uint16_t extent;      /* +0x0C cull slack radius */
    uint16_t flags;       /* +0x0E 0x0001/0x0009/0x4009 seen; bit15 = SENTINEL;
                           *       bit4 selects which builder pass consumes it;
                           *       bit7 -> consumer sets gp+0x5FC = 3000 (LOD/fade) */
    uint32_t src;         /* +0x10 source-record ptr (file offset on disc, RELOCATED
                           *       to a RAM pointer at load; -> AABB scalars + payload
                           *       ptr @src+0x14 into the payload band) */
} Pass3Record;

/* FUNC_80014360 — per-frame pass-3 culler.
 * Registers (from disasm): a0 = record cursor, a1 = 3x3 rotation rows (ctc2 rt),
 * a2 = camera position (t5/t6/t7), a3 = output cursor (G_P3_VISIBLE_LIST),
 * s0 = enable-bitmap byte cursor (walks DOWN from G_P3_ENABLE_BITMAP),
 * s2 = [G_DRAW_DISTANCE]>>2, s4 = bit mask (128 -> 1), v0 = visible count.
 * Returns (count | flags<<16-ish in v0/v1 packing; not fully mapped). */
int pass3_backdrop_cull_80014360(Pass3Record *rec, const int16_t rot[3][3],
                                 const int32_t cam[3])
{
    uint8_t  *bitmap = (uint8_t *)G_P3_ENABLE_BITMAP;
    uint32_t **out   = (uint32_t **)G_P3_VISIBLE_LIST;
    int32_t   far_w  = LW(G_DRAW_DISTANCE) >> 2;
    int       count  = 0;
    int       mask   = 0;      /* forces a bitmap byte fetch on entry */
    int       bits   = 0;

    for (;;) {
        if (rec->flags & 0x8000) break;          /* sentinel terminator (bltz on s16) */

        if (mask == 0) {                          /* refill: next byte DOWNWARD */
            mask = 128;
            bits = LB(bitmap);
            bitmap--;
        }
        int enabled = bits & mask;
        mask >>= 1;
        if (!enabled) { rec++; continue; }        /* SUPPRESSION LEVER #1 */

        /* GTE: view = rot * (anchor - cam); mac1/2/3 = view X/Y/Z */
        int32_t dx = rec->x - cam[0];
        int32_t dy = rec->y - cam[1];
        int32_t dz = rec->z - cam[2];
        int32_t vx = (rot[0][0]*dx + rot[0][1]*dy + rot[0][2]*dz) >> 12;
        int32_t vy = (rot[1][0]*dx + rot[1][1]*dy + rot[1][2]*dz) >> 12;
        int32_t vz = (rot[2][0]*dx + rot[2][1]*dy + rot[2][2]*dz) >> 12;
        int32_t ext = (int16_t)rec->extent;

        /* Z window with +/-extent slack (SUPPRESSION LEVER #2: an anchor moved
         * far away fails here and the prop is not drawn) */
        if (ext <= 0) {
            if (vz + (-ext) < 0) { rec++; continue; }
        } else {
            if (vz - (far_w - ext) < 0) { rec++; continue; }
        }
        /* |X| cone: |vx| <= vz + ext */
        int32_t ax = vx < 0 ? -vx : vx;
        if ((vz + ext) - ax < 0) { rec++; continue; }
        /* |Y| cone: |vy| <= (3*vz)>>2 + ext */
        int32_t ay = vy < 0 ? -vy : vy;
        if ((((vz + vz + vz) >> 2) + ext) - ay < 0) { rec++; continue; }

        *(*out)++ = (uint32_t)(uintptr_t)rec;     /* visible: append record ptr */
        count++;
        rec++;
    }
    return count;
}

/* ----------------------------------------------------------------------------
 * EMPIRICAL FACTS (phase-matched loadState A/B, LEVEL01 fixture, 2026-07-02):
 *  - Clearing record #56's bitmap bit removed its skyline prop (1369 px).
 *  - Moving record #56's anchor to (30000,30000,30000) removed the SAME pixels
 *    (cull-fail) -> source-side suppression = a 12-byte in-place DAT edit.
 *  - Moving the anchor NEAR the camera/player changed ZERO pixels -> the record
 *    does NOT position the drawn mesh (payload-baked / backdrop-pass transform).
 *  - extent=0 changed nothing (slack only).
 *  - Visible-list diff pinned bit<->record mapping exactly (entry 0x80164744 =
 *    DATbase+0x3F4C = record #56 with table base 0x3AEC).
 * TELESCOPE NOTE (same session): deleting type-0x3f kind-0x30 entries 68/69
 * (relocation-aware) cold-boots and plays fine (70->68 entries, histogram
 * correct, Flik controllable, death/respawn OK) -> the delete-unsafe
 * classification in delete_type3f_entries.py is precautionary, not structural;
 * remaining residual = telescope CONTACT interaction on an edited disc.
 * ---------------------------------------------------------------------------- */

/* ----------------------------------------------------------------------------
 * P54b (2026-07-07) — the enable BITMAP is the DEFINITIVE suppression lever;
 * parked anchors are NOT sufficient for the rotation-only class. The baked
 * fixture models (tree trunk / branches / grass blades) render even with ALL
 * 140 pass-3 anchors parked to (-20000,9000,-20000): their cull behaves
 * rotation-only (the documented "anchor projects behind the camera yet the
 * prop renders" quirk). Clearing the whole bitmap (0x800902B6..0x800902C7,
 * bytes walk DOWN from G_P3_ENABLE_BITMAP) removes the class instantly and
 * leaves Flik/Dot/enemies/HUD and the native floor untouched (live-proven,
 * 240+ frames). Track-B custom levels bake this as a one-shot clear in the
 * level-gated P11 cave (RAM-only -> menu-safe, rebuilt on any level load):
 * build_g3_native.py --park-nonfloor-nodes installs it alongside the node/
 * record parking. See docs/G3_NATIVE_P54B_AUTHORED_WORLD_VISUALS.md.
 * ---------------------------------------------------------------------------- */
