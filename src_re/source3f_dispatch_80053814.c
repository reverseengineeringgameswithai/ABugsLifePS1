/* RCA a4 (2026-07-09): SUPERSEDED for build purposes — 0x80053814 is byte-matched in the
   shipping build as asm/hand_written/80053814_source3f_dispatch.s (config/segments.yml `attempted`;
   validate_build.py SHA-1 PASS). This src_re file is documentation-grade pseudocode,
   retained for its analysis/comments; it is NOT the build unit. */
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
 *                    fcn.80057620 (ordinary-pickup burst/finalize; 0x30/0x31 bypass it), fcn.8005044c
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
 *   0x31    -> 0x800545a0  : at Y==restY-112, Y--, result -10, sound/event -3
 *   all other indices (0x15..0x19,0x25..0x28,0x2e,0x2f) -> 0x800545cc (default: s1=-2, next)
 *
 * FLIK5 mod proof (2026-07-05): true append of a duplicate native F (kind 0x10)
 * as entry 70 works with the relocation-aware DAT append path. The EXE patch
 * special-cases s4 == type3f_record+4+70*0x10 in the F handler to set bit 0x10,
 * then changes completion compares from 0x0f to 0x1f. This proved the FLIK gate
 * can require more than four letters without a type-0x3f count/pool cap.
 * ============================================================================ */

#include "re_types.h"

/* MIPS access helpers (same convention as dat_parser_8001cdc0.c) */
#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LBU(p)  (*(uint8_t  *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))

/* callees (decompiled in later phases / out of Phase-2 scope) */
extern void *contact_alloc(int x, int y, int z, int ctorType, int stackArg); /* fcn.80059e44 (ABI confirmed Phase 3) */
extern void  fcn_80057620(int x, int y, int z);                              /* ordinary-pickup burst/finalize */
extern void  fcn_8005044c(int s1_result, void *coords /*sp+0x18*/);          /* post-pickup bookkeeping */
extern int   fcn_80045678(void *progress /*0x800a6500*/);                    /* nearest-pickup finalize */
extern void  fcn_8005721c(int a0, int a1);
extern void  fcn_800571e0(int a0, int a1);
/* Per-kind ACTION handlers (Phase 5). Dispatched via jr table 0x8001b42c; each returns the
 * post-loop result code left in s1 (e.g. -2 default, -3, FLIK/berry/token specific). */
extern int   pickup_action_dispatch(uint8_t kind, void *entry /*s4*/, int *s1_io);

#define Y_SENTINEL_CONSUMED  0x80000000   /* entry.Y set to this once constructed/consumed */
#define DIST_GATE_GENERIC    0x3d08f      /* generic 0x71 construct: require dist <= this */
#define DIST_GATE_GRAIN      0x15f8f      /* grain 0x51 construct:   require dist <= this */
#define DIST_GATE_CONTACT    0x9c4        /* contact-action dispatch: require dist <  this */

/*
 * fcn.80053814 — iterate the type-0x3f record; for each eligible entry within range,
 * CONSTRUCT its runtime entity (grain/FLIK/berry/token/telescope) and/or fire its
 * contact pickup ACTION. Tracks the nearest eligible entry for post-loop finalize.
 */
void source3f_dispatch(void)
{
    uint8_t *rec = (uint8_t *)(uintptr_t)LW(G_TYPE3F_PTR); /* a1 = type-0x3f record ptr */
    uint8_t *progress = (uint8_t *)0x800a6500;             /* a0 = progress/player-pos base */

    int32_t fp = 0;          /* count of kind-0x30 entries seen so far (index into 0x800910f7) */
    int32_t s1 = 0;          /* post-loop result code (set by default/handlers) */
    int32_t cnt31 = 0;       /* [sp+0x58] one-based ordinal of kind-0x31 entries */
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

            /* ---- kind 0x31: ordinal proximity emitter ----
             * Exact shipping path 0x800539a0..0x80053a18: require
             * (restY-currentY)>=113, dist<=0x3d08f and phase byte 0x800910a2==0,
             * then construct ctor=(83+one-based ordinal), metadata-A row 21, at
             * {X, Y-160, Z}<<5. Retail ctor rows 84..88 share action/type/lifetime
             * fields and differ in their trailing RGB-shaped triplets. */
            if (kind == 0x31) {
                int16_t restY = LH(s2 + 0xa);
                if (restY - entryY >= 113 && dist <= DIST_GATE_GENERIC
                    && LBU(0x800910a2) == 0) {
                    contact_alloc(LW(s4) << 5, (entryY - 160) << 5, LW(s2 + 4) << 5,
                                  /*ctor*/cnt31 + 83, /*stackArg*/21);
                }
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
             * Tier-3 note (2026-06-29): DuckStation verification on authored elevated FLIK letters showed
             * type-0x3f entries 50-53 loaded with correct X/Y/Z and status=1, then their live Y drifted
             * before collection (e.g. authored file Y -321 became -2362/-2828/-6305/-3093). The exact
             * writer was not attributed in this RE pass; it may be construct/runtime object state outside
             * this decompiled block. Tier-3 therefore pins authored FLIK entries each gameplay frame until
             * the native collected bit is set, preserving native collection while preventing pre-collection
             * drift. */
            if (kind < 0x30 && kind != 0x14 && dist <= DIST_GATE_GENERIC
                && (kind & 3) == LBU(0x800910a4)) {
                uint8_t *cur = (uint8_t *)(uintptr_t)LW(0x800822f4);   /* script cursor */
                int32_t bx = LBU(cur + 0), by = LBU(cur + 1), bz = LBU(cur + 2);
                SW(0x800822f4, (int32_t)(uintptr_t)(cur + 3));         /* cursor += 3 */
                int32_t ax = (LW(s4)     << 5) + ((bx - 0x80) << 4);
                int32_t ay = (LW(s2)     << 5) + ((by - 0x80) << 4);
                int32_t az = (LW(s2 + 4) << 5) + ((bz - 0x80) << 4);
                contact_alloc(ax, ay, az, /*ctor*/0x71, /*stackArg*/0x18);
            }

            /* ---- GRAIN CONSTRUCT (ctor 0x51) ----
             * (0x80053bf8) requires grain-enable flag (0x800a6590 & 0x80), kind==0x14,
             * dist<=0x15f8f. Coords = entry.{X,Y,Z}<<5. Then consume entry + mark record. */
            if ((LHU(0x800a6590) & 0x80) && kind == 0x14) {
                if (dist <= DIST_GATE_GRAIN) {
                    void *r = contact_alloc(LW(s4) << 5, LW(s2) << 5, LW(s2 + 4) << 5,
                                            /*ctor*/0x51, /*stackArg*/3);
                    SW(s2, Y_SENTINEL_CONSUMED);   /* entry.Y = sentinel (consumed) */
                    SW((uint8_t *)r + 0x10, -1);   /* record+0x10 = -1 */
                }
                goto next;                          /* grain path returns to loop (j 0x800545d0) */
            }

            /* ---- CONTACT ACTIONS (player very close: dist < 0x9c4) ---- */
            if (dist < DIST_GATE_CONTACT) {
                /* stack coords for handlers (sp+0x18/1c/20 = X/Y/Z<<5) */
                /* Ordinary pickup burst/finalize. The shipping sltiu range check
                 * deliberately makes kinds 0x30 and 0x31 bypass this path. */
                if (kind != 0x30 && kind != 0x31) {
                    fcn_80057620(LW(s4) << 5, LW(s2) << 5, LW(s2 + 4) << 5);
                    SW(s2, Y_SENTINEL_CONSUMED);
                }
                /* per-kind ACTION dispatch: jr 0x8001b42c[kind-0x10] for kind in [0x10,0x31].
                 * Bodies are Phase 5; they set s1 to the post-loop result code. */
                if ((uint8_t)(kind - 0x10) < 0x22) {
                    s1 = pickup_action_dispatch(kind, s4, &s1);  /* jr v0 @0x80053cfc */
                } else {
                    s1 = -2;                                     /* default 0x800545cc */
                }
            }

        next:
            s2 += 0x10; s4 += 0x10; s5++;
        } while (s5 < count);
    }

    /* ===================================================================
     * POST-LOOP FINALIZE (0x800545e8..0x80054808) — SUMMARY (peripheral to Phase 2)
     *  - if (s1 != 0) fcn.8005044c(s1, &coords)            // post-pickup bookkeeping
     *  - r = fcn.80045678(progress)                        // nearest-pickup finalize
     *    if (!r) fcn.8005721c(8,0x1e); else nothing; fcn.800571e0(4,0x1e)  // sounds
     *  - if (LBU(G_BERRY_MARKER) != oldMarker): run berry-marker-change handler
     *    (0x80054628.., reads table 0x80090000-0x66c8 = 0x80089938[marker]) — details Phase 5.
     * =================================================================== */
}

/* ----------------------------------------------------------------------------
 * PHASE 2 FINDINGS (feed back to docs / re_types.h):
 *  - CONFIRMED: this single function is BOTH the per-entry constructor AND the contact-action
 *    dispatcher. Per entry: eligibility (Y!=0x80000000 sentinel AND status+0x0d==1), distance²
 *    (axes>>3), nearest-eligible tracking (allow table 0x80078d84[kind]).
 *  - CONFIRMED construct paths: grain kind 0x14 -> ctor 0x51 (coords<<5, dist<=0x15f8f, gated by
 *    0x800a6590&0x80), marks entry.Y=0x80000000 + record+0x10=-1; generic visible (FLIK/berry/
 *    token, kind<0x30 && !=0x14) -> ctor 0x71 (coords<<5 + 3 script-byte offsets from 0x800822f4,
 *    dist<=0x3d08f, phase gate (kind&3)==[0x800910a4]); kind 0x31 -> ctor
 *    83+ordinal / metadata-A row 21 under its rest-height and alternating-phase gates.
 *  - CONFIRMED contact dispatch: jr table 0x8001b42c, index kind-0x10 (kinds 0x10..0x31), only when
 *    dist<0x9c4. Targets enumerated in header; bodies = Phase 5.
 *  - CONFIRMED: kinds 0x10..0x13 = FLIK (set collected bits 1/2/4/8); 0x21..0x24 = berries
 *    (G_BERRY_MARKER 2/3/1/4 + sounds 0x36/0x38/0x35/0x37); 0x29..0x2b = seed tokens;
 *    0x30 = DEWDROP TELESCOPE / hint-view trigger (bobs every frame; camera interaction on contact).
 *  - FLIK5 MOD RESULT (2026-07-05): appending another kind-0x10 F as entry 70 is safe when the
 *    F handler, not the descriptor table, distinguishes it. Descriptor-table spoofing a fake F kind
 *    corrupted the top-left Flik-head HUD icon, so avoid that path.
 *  - TIER-3 CAVEAT (2026-06-29): FLIK entries are real native collectibles, but authored FLIK letters left
 *    in the world can have live Y mutated before pickup. Runtime collection still works once Flik reaches
 *    the pinned coords (`0x800a65a2` -> `0x0f`, entries -> consumed sentinel). Exact native Y writer remains
 *    TODO if a future pure-data fix is desired.
 *  - NEW globals to consider for re_types.h: 0x800822f4 (script cursor), 0x800910a4 (construct phase),
 *    0x800a6590 (grain-enable flags), 0x80078d84 (kind allow table). Left as raw addrs pending
 *    a dedicated consumer decompile (do not over-name).
 *  - RESOLVED this session: kind-0x30 inner math = the gem BOB (entry.Y rewritten each frame =
 *    lh[entry+0xe] rest-height + ((s16)sinTable[0x80074970 + (0x800910aa<<8)] >> 8) - 800; writer
 *    @0x80053a88). The gem is rendered live from the record by fcn.800253e8 (see
 *    pickup_projector_800253e8.c) — so editing record X/Z moves it (persists); Y is bob-owned.
 *  - RESOLVED: kind-0x31 inner construct math and exact-height action. Remaining presentation
 *    residual: the on-screen identity/timing of metadata variants 84..88 and any indirect writer
 *    that can make the retail Y=-600/restY=0 records reach the action's restY-112 threshold.
 *  - LIKELY/TODO: post-loop marker-change handler.
 * ---------------------------------------------------------------------------- */
