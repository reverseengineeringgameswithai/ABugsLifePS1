---
kind: function
id: FUNC_80053814
aliases: [FUNC_80053814, 0x80053814]
address: 0x80053814
name: type-0x3f_construct_+_contact-action_dispatch
status: static_seen
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: []
src_paths:
  - src_re/source3f_dispatch_80053814.c
patch_policy: unknown
---

# FUNC_80053814 - type-0x3f construct + contact-action dispatch

## Purpose

Iterates the type-0x3f record, constructs each pickup's runtime entity, and fires its contact pickup action via a jump table. The behavioral half of the pickup pipeline.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80053814.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x80053814`
- Name: `type-0x3f_construct_+_contact-action_dispatch`
- Original note: `ObsidianVault/Functions/FUNC_80053814.md`
- Source path: `src_re/source3f_dispatch_80053814.c`

## C source excerpt

Source: `src_re/source3f_dispatch_80053814.c`

```c
/* ============================================================================
 * source3f_dispatch_80053814.c  — type-0x3f per-entry pickup pass  [PHASE 2 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.80053814  (size 4092 bytes, 0x80053814..0x80054810)
 * CONFIDENCE       : CONFIRMED top-level structure (loop, eligibility gate, the 3 construct
 *                    paths, contact-action jump table). Per-kind ACTION handler BODIES
 *                    (jr-table targets) are DECOMPiled in Phase 5 (pickup_handlers_*); here
 *                    they are dispatched with confirmed targets + one-line effects. A few
 *                    inner construct maths are LIKELY (labelled).
 * SOURCE NOTES     : docs/LEVEL01_TYPE3F_MAP.md, docs/COORDINATE_MODDING.md,
 *                    docs/EXPERIMENT_LOG.md, docs/DAT_FORMAT_AND_RELOCATION.md, r2 disasm.
 * KNOWN CALLERS    : fcn.8004ecd4 @0x8004f028 (sole direct caller).
 * KNOWN CALLEES    : fcn.80059e44 (contact alloc/construct; ctor 0x51 grain, 0x71 generic),
 *                    fcn.80057620 (telescope contact effect, kind 0x30/0x31), fcn.8005044c
 *                    (post-pickup bookkeeping), fcn.80045678 (nearest-pickup finalize),
 *                    fcn.8005721c / fcn.800571e0 (sound/event), + per-kind handlers via
 *                    jump table 0x8001b42c (see DISPATCH below).
 * KNOWN GLOBALS    : G_TYPE3F_PTR(0x80096e9c) record ptr; G_PLAYER_X/Y/Z(0x800a6500/04/08);
 *                    G_BERRY_MARKER(0x800a6597); 0x800a6590 (grain-enable flags, &0x80);
 *                    0x800822f4 (level script-byte cursor); 0x800910a4 (construct phase byte,
 *                    gates generic 0x71 by (kind&3)); 0x800910f7+fp (kind-0x30 per-gem consume
 *                    gate); 0x800910aa (GLOBAL bob phase counter, indexes sin table); 0x80078d84
 *                    [kind] (nearest-search allow table); 0x80074970 (sin table; kind-0x30 BOB,
 *                    CONFIRMED); ENTRY+0x0e lh = per-gem rest height (bob base); jump 0x8001b42c.
 * UNRESOLVED       : construct phase byte 0x800910a4 vs 0x800910f7; nearest-search allow table
 *                    0x80078d84 contents; full post-loop finalize.
 *                    RESOLVED this session: kind-0x30 "animated-construct inner math" = the gem
 *                    BOB: entry.Y = lh[entry+0xe] + ((s16)sinTable[0x800910aa] >> 8) - 800.
 *
 * ENTRY LAYOUT (Type3FEntry, 0x10 bytes; see re_types.h):
 *   +0x00 X, +0x04 Y, +0x08 Z (s32, file units), +0x0c kind, +0x0d status byte.
 *   In this fn the cursor regs are: s4 = entry base (+0); s2 = entry base + 4. Hence
 *   [s4]=X, [s2]=Y, [s2+4]=Z, lbu[s2+8]=kind(+0x0c), lbu[s2+9]=status(+0x0d), lh[s2+0xa]=+0x0e.
 *
 * DISPATCH (CONFIRMED jump table 0x8001b42c, index = kind-0x10, only when player within
 * contact range dist < 0x9c4). Targets / confirmed effects (bodies = Phase 5):
 *   0x10 F  -> 0x80053d04  : ori collected-bitmask |=1  (+ F-anomalous extra logic)
 *   0x11 L  -> 0x80053e64  : |=2
 *   0x12 I  -> 0x80053fc0  : |=4
 *   0x13 K  -> 0x8005411c  : |=8
 *   0x14 gr -> 0x80054278  : grain pickup action (-> fcn.80054eac, grain_count++)
 *   0x20    -> 0x80054288  : G_BERRY_MARKER=0, sound -3
 *   0x21    -> 0x80054298  : G_BERRY_MARKER=2, sound 0x36   (Green/Homing berry)
 *   0x22    -> 0x800542ac  : G_BERRY_MARKER=3, sound 0x38   (Gold berry)
 *   0x23    -> 0x800542c0  : G_BERRY_MARKER=1, sound 0x35   (Blue/Super berry)
 *   0x24    -> 0x800542d4  : G_BERRY_MARKER=4, sound 0x37   (Purple/Mega-Homing berry)
 *   0x29    -> 0x800542f4  : seed token, ctr 0x800a6598, powered obj 0x16  (orange)
 *   0x2a    -> 0x8005433c  : seed token, ctr 0x800a6599, obj 0x17          (blue)
 *   0x2b    -> 0x800543b8  : seed token, ctr 0x800a659a, obj 0x19          (green)
 *   0x2c    -> 0x80054434  : seed token (obj from table 0x80078e90)
 *   0x2d    -> 0x800544d0  : seed token
 *   0x30    -> 0x80054554  : DEWDROP TELESCOPE / hint-view activation. Saves its ordinal
 *                            to 0x800823cc, sets 0x800824dc, and clears player velocity/grounded
 *                            state while the camera interaction takes ownership. It is not a
 *                            respawn object. Rendered live from the record by fcn.800253e8.
 *   0x31    -> 0x800545a0  : (kind-0x31 action)
 *   all other indices (0x15..0x19,0x25..0x28,0x2e,0x2f) -> 0x800545cc (default: s1=-2, next)
 *
 * FLIK5 mod proof (2026-07-05): true append of a duplicate native F (kind 0x10)
 * as entry 70 works with the relocation-aware DAT append path. The EXE patch
 * special-cases s4 == type3f_record+4+70*0x10 in the F handler to set bit 0x10,
 * then changes completion compares from 0x0f to 0x1f. This proved the FLIK gate
 * can require more than four letters without a type-0x3f count/pool cap.
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
void source3f_dispatch(void)
{
    uint8_t *rec = (uint8_t *)(uintptr_t)LW(G_TYPE3F_PTR); /* a1 = type-0x3f record ptr */
    uint8_t *progress = (uint8_t *)0x800a6500;             /* a0 = progress/player-pos base */

    int32_t fp = 0;          /* count of kind-0x30 entries seen so far (index into 0x800910f7) */
    int32_t s1 = 0;          /* post-loop result code (set by default/handlers) */
    int32_t cnt31 = 0;       /* [sp+0x58] count of kind-0x31 entries */
    int32_t mindist = 0x7fffffff;     /* [sp+0x50] nearest-eligible distance² */
    void   *near_entry = 0;           /* [sp+0x60] nearest-eligible entry (s4) */

    /* player position (>>5 into entry/file units); note the -0xe6 Y bias here (NOT the
     * walker's -0x1cc0 — this is a different, construct/contact pass). */
    int32_t pX  =  LW(progress + 0x00) >> 5;            /* [sp+0x30] */
    int32_t pYb = (LW(progress + 0x04) >> 5) - 0xe6;    /* [sp+0x38] */
    int32_t pZ  =  LW(progress + 0x08) >> 5;            /* [sp+0x40] */
    uint8_t oldMarker = LBU(G_BERRY_MARKER);            /* [sp+0x48] */

    int32_t count = LHU(rec);                           /* [sp+0x28] entry count */
    uint8_t *s4 = rec + 4;                              /* entry[0] base (+0 = X) */
    uint8_t *s2 = rec + 8;                              /* entry[0] + 4 */

    if (count != 0) {
        int32_t s5 = 0;
        do {
            uint8_t kind = LBU(s2 + 8);                 /* entry.kind (+0x0c) */
            if (kind == 0x30) fp++;
            if (kind == 0x31) cnt31++;

            int32_t entryY = LW(s2);                    /* entry.Y (+0x04) */
            if ((uint32_t)entryY == Y_SENTINEL_CONSUMED) goto next; /* already consumed */
            if (LBU(s2 + 9) != 1)                       goto next; /* status (+0x0d) must == 1 */

            /* distance² to player, axes >>3 after subtract (CONFIRMED) */
            int32_t dx = (pX  - LW(s4))     >> 3;
            int32_t dy = (pYb - entryY)     >> 3;
            int32_t dz = (pZ  - LW(s2 + 4)) >> 3;
            int32_t dist = dx*dx + dy*dy + dz*dz;       /* s0 */

            /* nearest-eligible tracking, gated by per-kind allow table 0x80078d84[kind]
             * (table CONTENTS / exact per-kind meaning: UNKNOWN — left raw) */
            if (dist < mindist && LW(0x80078d84 + kind*4) != 0) {
                mindist = dist; near_entry = s4;
            }

            /* ---- kind 0x31: animated construct (ctor 0x71) ----
             * Gated by status [s2+0xa] proximity (slti +0x71) and dist <= 0x3d08f; consumes
             * 3 script bytes from [0x800822f4] as coord offsets; LIKELY animation logic. */
            if (kind == 0x31) {
                /* (0x800539a0..0x80053a24) detailed math LIKELY — see Phase 5 / TODO. */
            }

            /* ---- kind 0x30: GREEN FLOATING SPARKLY GEM — per-frame BOB + visible construct ----
             * (0x80053a24..0x80053b24)  [CONFIRMED this session — see INV note / 0x80053a88 writer]
             * kind 0x30 is the bobbing green gem the player sees (LEVEL01 entries 67/68/69). It is
             * Its contact ACTION (0x80054554) enters the telescope/hint-view camera interaction:
             * it latches the telescope ordinal and clears player motion. These are not respawn writes.
             *
             * This dispatch is the per-frame pickup pass, so this block re-derives the gem's Y
             * EVERY frame = the visible bob. CONFIRMED live: entry67 Y @0x80160c34 oscillates
             * (-2444..-2552..), written at 0x80053a88 (the branch-delay slot of the dist test, so
             * the write always lands once in the animate path). X/Z are NOT touched here (static;
             * that is why a live X/Z edit of the record moves the gem and persists). */
            if (kind == 0x30) {
                /* per-gem consume gate (0x800910f7[fp], fp = #kind-0x30 entries seen so far) */
                if (LBU(0x800910f7 + fp) != 0) { SW(s2, Y_SENTINEL_CONSUMED); goto next; }

                /* BOB: entry.Y = restHeight(entry+0xe) + (sineAmplitude - 800).
                 *   restHeight : per-gem signed halfword at entry+0x0e  (lh [s2+0xa])
                 *   sineAmpl   : top signed byte of sin table 0x80074970 indexed by the GLOBAL
                 *                bob phase counter 0x800910aa (stride 0x100 -> <<8), i.e.
                 *                ((int16_t)LHU(0x80074970 + (phase<<8))) >> 8 */
                int16_t  restY    = LH(s2 + 0xa);                                  /* entry+0x0e */
                uint16_t sineWord = LHU(0x80074970 + (LBU(0x800910aa) << 8));      /* sin @ phase */
                int32_t  bob      = ((int16_t)sineWord >> 8) - 800;
                SW(s2, restY + bob);                                              /* entry.Y bobs */

                /* construct/refresh the visible animated entity (ctor 0x71) only when near AND
                 * the construct-phase byte is clear (0x80053a8c..0x80053b24). */
                if (dist <= DIST_GATE_GENERIC && LBU(0x800910a4) == 0) {
                    /* contact_alloc(LW(s4)<<5, entry.Y, entry.Z, ctor=0x71, ...) — Phase 5 */
                }
                /* falls through (skips the kind<0x30 generic construct; reaches grain/contact) */
            }

            /* ---- GENERIC VISIBLE CONSTRUCT (ctor 0x71): FLIK/berry/token ----
             * (0x80053b24) requires kind<0x30, kind!=0x14, dist<=0x3d08f, and phase gate
             * (kind & 3) == LBU(0x800910a4) [construct-phase byte; exact meaning UNKNOWN].
             * Coords = entry.{X,Y,Z}<<5 + script-byte offsets.
             *
/* Full source is in the listed source path. */
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80053814.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80053814.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80053814.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
