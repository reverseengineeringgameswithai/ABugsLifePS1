---
kind: struct
id: STRUCT_dat_geometry_records
created: 2026-07-08
updated: 2026-07-08
status: static_seen
confidence: medium
source_state: original_game_reference_or_mod_reference
src_paths:
  - src_re_geometry/dat_geometry_records.c
address: 0x8001cdc0
patch_policy: safe_to_read
---

# STRUCT_dat_geometry_records - dat geometry records

## Purpose

This page closes the migration source-coverage gap for `src_re_geometry/dat_geometry_records.c`. It records the symbol `ParserOutputRecord20` and links the C reference into the structured vault.

- Address if known: `0x8001cdc0`
- Coverage comments: original address header: (no new function) — annotates the geometry-relevant parts of; structs: ParserOutputRecord20, ParserSrcRec18_NonBit3, ParserSrcRec20_Bit3


## C source excerpt

Source: `src_re_geometry/dat_geometry_records.c`

```c
/* ============================================================================
 * dat_geometry_records.c  —  Parser geometry-output model        [PHASE G2 — ANALYZED 2026-06-13]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : (no new function) — annotates the geometry-relevant parts of
 *                    fcn.8001cdc0 (DAT parser/relocator, 0x8001cdc0..0x8001d3cc),
 *                    already DECOMPILED in src_re/dat_parser_8001cdc0.c (Phase 1).
 *                    DO NOT redo that decompile here; this file extracts/annotates
 *                    only the parts that CREATE geometry-facing runtime records.
 * CONFIDENCE       : Two source-record formats (0x18 non-bit3 / 0x20 bit3) and the 0x20-byte
 *                    pass-1 output record are CONFIRMED by byte inspection + the Phase-1 body
 *                    (G2). Field ROLES (what pos/ptr mean to a consumer) are UNKNOWN until G4/G5.
 *                    C body = ANNOTATION ONLY (no executable change).
 * SOURCE NOTES     : src_re/dat_parser_8001cdc0.c (Phase 1, CONFIRMED),
 *                    src_re_geometry/level01_dat_geometry_inventory.md (G1 reloc inventory),
 *                    G2 byte inspection of DAT/LEVEL01_LEVEL.DAT (read-only),
 *                    docs/DAT_FORMAT_AND_RELOCATION.md, docs/GEOMETRY_RE_PLAN.md (G2).
 * KNOWN CALLERS    : fcn.8003cf2c @0x8003d568 (level/resource loader) -> dat_parse_relocate;
 *                    caller advances its output buffer pointer by the return value (count<<5).
 * KNOWN CALLEES    : fcn.80017b98 (GTE rotation-matrix setup; relocates nothing) CONFIRMED;
 *                    fcn.8003eec8 (epilogue finalize) CONFIRMED.
 * KNOWN GLOBALS    : G_DAT_BASE_PTR(0x80082498), G_TRAIL_BLOCK_PTR(0x800824ac),
 *                    G_PASS2_BASE_PTR(0x80082338), G_PASS3_BASE_PTR(0x80082508),
 *                    G_DAT_ENTRY_COUNTER(0x800822f0); pass-2 table 0x80091210..(empty LEVEL01).
 * UNRESOLVED       : (a) consumer/role of the pass-1 output buffer and the pass-3 relocated records
 *                    (G4/G5); (b) meaning of source +0x12 (non-bit3) and +0x18 (bit3) scalars;
 *                    (c) whether out+0x12..0x17 / out+0x1c..0x1f are written by fcn.80017b98
 *                    (not decompiled — out of G2 scope); (d) the payload-band contents.
 *
 * ============================================================================
 * G2 RESOLUTION — the G1 "0x18 stride vs [s0+0x1c]" conflict (CONFIRMED)
 * --------------------------------------------------------------------
 * There are TWO source-record formats, selected per table entry by flag bit3 (0x8):
 *   - NON-BIT3 source record = 0x18 bytes. Relocated pointer at +0x14 (SITE B/H). Never reads +0x1c.
 *   - BIT3     source record = 0x20 bytes. Relocated pointer at +0x1c (SITE D/I). Has a scale triple.
 * Evidence (LEVEL01, read-only):
 *   - non-bit3 unique source ptrs: 174 (pass1) + 85 (pass3); dominant sorted stride = 0x18.
 *   - bit3     unique source ptrs: 310 (pass1) + 55 (pass3); dominant sorted stride = 0x20.
 *   - first non-bit3 run is exactly 0x18-contiguous: 0x45f0,0x4608,0x4620,0x4638,0x4650,0x4668,0x4680.
 *   - flag 0x20 (extra-pointer gate; SITE C/E) is NEVER set in LEVEL01 -> no +0x18/+0x20 relocation.
 * So neither format reads past its own bounds; the 0x18 stride was measured over non-bit3 records
 * only. The two formats are interleaved in sub-blocks but each contiguous run is single-format.
 * The shared prefix is { s32 vec[3] @+0x00 ; s16 angle[3] @+0x0c }; they diverge after +0x12.
 *
 * ============================================================================
 * PASS 1 — geometry constructor (CONFIRMED, from Phase-1 body)
 * -----------------------------------------------------------
 * For each pass-1 table entry (stride 0x14 @ 0x1512.., while lh[s3] >= 0):
 *   s0 = DATbase + [s3+2]                 ; SITE A  (relocate source ptr)
 *   fcn.80017b98(s0+0xc, out)             ; build 3x3 rotation matrix from angle[3] into out+0..+0x10
 *   if (flags & 8):  // bit3 / 0x20-byte source
 *       relocate [s0+0x1c]                ; SITE D  (-> payload band)
 *       scale matrix: out[col] *= scale_j (=[s0+0x12/0x14/0x16]); elem=(elem*scale)>>12 (rtz)
 *   else:            // non-bit3 / 0x18-byte source
 *       relocate [s0+0x14]                ; SITE B  (-> payload band); no matrix scaling
 *   [out+0x18] = s0                       ; output record links back to its (relocated) source
 *   [s3+2]     = out                      ; table entry repointed to the runtime output record
 *   out += 0x20 ; count++                 ; one 0x20-byte output record per entry
 * Output buffer base = DATbase + arg2. Return value = count<<5 (= total output bytes).
 *
 * PASS 3 — relocation only (CONFIRMED, from Phase-1 body)
 * ------------------------------------------------------
 * Second stride-0x14 table (140 entries @ 0x3afa..). Per entry:
 *   s0 = DATbase + [a0+2]                 ; SITE G  (relocate source ptr)
 *   if (flags & 8): relocate [s0+0x1c]    ; SITE I        else: relocate [s0+0x14]  ; SITE H
 * Pass 3 does NOT call fcn.80017b98, does NOT scale, does NOT build 0x20-byte output records, and
 * does NOT write the DATbase+arg2 buffer. It only relocates baked pointers in place, leaving the
 * source records for a different (direct) consumer to read. (Pass-3 source records are byte-identical
 * in SHAPE to pass-1 source records; only the parser's treatment differs. Do NOT merge their
 * downstream semantics without consumer evidence — G4/G5.)
 *
 * PASS 2 — empty in LEVEL01 ([p2]=-1). Not modeled here.
 * ============================================================================ */

#include "../src_re/re_types.h"

/* ---- CANDIDATE structs (local to G2; NOT promoted to re_types.h) ----
 * Names are deliberately neutral. No mesh/vertex/triangle/collision/floor/wall naming: there is no
 * consumer evidence for those roles yet. `vec`/`angle`/`scale` reflect CONFIRMED parser USE only:
 *   - angle[3]  is CONFIRMED fed to the rotation-matrix setup fcn.80017b98.
 *   - scale[3]  is CONFIRMED used to scale the matrix (12-bit fixed point; 0x1000 == 1.0).
 *   - vec[3]    is three s32 of coordinate-like magnitude; ROLE UNKNOWN (position-shaped).
 */

/* Non-bit3 source record (flag bit 0x8 clear). sizeof = 0x18 (CONFIRMED stride). */
typedef struct ParserSrcRec18_NonBit3 {
    int32_t  vec[3];     /* +0x00  CONFIRMED three s32 (coordinate-like; role UNKNOWN) */
    int16_t  angle[3];   /* +0x0c  CONFIRMED rotation inputs -> fcn.80017b98 (often 0,0,0) */
    int16_t  unk12;      /* +0x12  CONFIRMED present; NOT used by parser on this path; role UNKNOWN */
    uint32_t ptr14;      /* +0x14  CONFIRMED relocated pointer (SITE B/H) -> payload band */
} ParserSrcRec18_NonBit3;            /* sizeof = 0x18 CONFIRMED */

/* Bit3 source record (flag bit 0x8 set). sizeof = 0x20 (CONFIRMED stride). */
typedef struct ParserSrcRec20_Bit3 {
    int32_t  vec[3];     /* +0x00  CONFIRMED three s32 (coordinate-like; role UNKNOWN) */
    int16_t  angle[3];   /* +0x0c  CONFIRMED rotation inputs -> fcn.80017b98 */
    int16_t  scale[3];   /* +0x12  CONFIRMED per-axis matrix scale (12.4 fixed; 0x1000=1.0) */
    uint32_t unk18;      /* +0x18  CONFIRMED present; NOT relocated (flag 0x20 never set); role UNKNOWN */
    uint32_t ptr1c;      /* +0x1c  CONFIRMED relocated pointer (SITE D/I) -> payload band */
} ParserSrcRec20_Bit3;               /* sizeof = 0x20 CONFIRMED */

/* Pass-1 runtime output record written to DATbase+arg2. sizeof = 0x20 (CONFIRMED stride). */
typedef struct ParserOutputRecord20 {
    int16_t  rot[9];     /* +0x00..+0x11  CONFIRMED 3x3 rotation matrix (bit3: scaled in place) */
    uint8_t  unk12[6];   /* +0x12..+0x17  UNKNOWN (maybe written by fcn.80017b98; not decompiled) */
    void    *src;        /* +0x18         CONFIRMED -> source record (relocated s0) */
    uint32_t unk1c;      /* +0x1c         UNKNOWN (not written by the visible parser code) */
} ParserOutputRecord20;              /* sizeof = 0x20 CONFIRMED */

/* NOTE (LIKELY, flagged): the {rot[9] @0, ptr @0x18} shape resembles a PsyQ MATRIX
 * ({short m[3][3]; long t[3];}, 0x20 bytes) but storing the source pointer at +0x18 would overwrite
 * MATRIX.t[1]; so this is probably NOT a live PsyQ MATRIX used for translation. Treat +0x12..+0x17
 * and +0x1c..+0x1f as UNKNOWN until a consumer (G4/G5) is found. */

/*
 * G2 OBSERVED SAMPLES (CONFIRMED bytes; for reference, not promoted):
 *   non-bit3 s0=0x4680: vec=(-8192,-8192,-8192) angle=(0,0,0) unk12=-16376 ptr14=0xb32c
 *   bit3     s0=0x4e00: vec=(4693,-4312,-665)   angle=(471,927,3705) scale=(4096,4096,4096)
 *                       unk18=0xce00 ptr1c=0x3703c
 *   pass3 nb s0=0x7d00: vec=(8192,-8192,-8192)  angle=(0,0,0) unk12=0x0400 ptr14=0x46e98
 *
 * G2 OPEN ITEMS handed to G3/G4/G5:
 *  [ ] Resolve arg2 (read fcn.8003cf2c) for the concrete resident base of the output buffer (G3).
 *  [ ] Identify the consumer of ParserOutputRecord20 (matrix path) — render or collision? (G4/G5)
 *  [ ] Identify the consumer of the pass-3 relocated source records (direct path) — separate from
 *      the pass-1 consumer until proven otherwise.
 *  [ ] Decode the payload-band targets of ptr14/ptr1c (0x8bd8..0x4f32c).
 *  [ ] Meaning of non-bit3 +0x12 and bit3 +0x18 scalars.
 *  [ ] Do NOT promote any field to re_types.h until confirmed across parser AND a consumer.
 */
```
