---
kind: function
id: FUNC_80059E44
aliases: [FUNC_80059E44, 0x80059e44, spawn_drop, ContactRecord_allocator]
address: 0x80059E44
name: spawn_drop
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
evidence:
  - EXP_2026-07-07_golddrop_pickup_verifier
  - EXP_2026-07-09_identity_reconciliation
src_paths:
  - src_re/contact_alloc_80059e44.c
patch_policy: callable
---

# FUNC_80059E44 - ContactRecord allocator

> **RCA a3 identity fix (2026-07-09):** Renamed ContactRecord_allocator -> **spawn_drop** (authoritative `re_symbols.sym`; the spawned drop is the gold-berry token, proven by [[EXP_2026-07-07_golddrop_pickup_verifier]]). Allocating the contact-array slot is its constructor sub-role.


## Purpose

Allocates the next free slot in the 64-entry contact array and fills it from coords + two metadata tables. The constructor half of pickup spawning.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80059E44.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x80059E44`
- Name: `ContactRecord_allocator`
- Original note: `ObsidianVault/Functions/FUNC_80059E44.md`
- Source path: `src_re/contact_alloc_80059e44.c`

## C source excerpt

Source: `src_re/contact_alloc_80059e44.c`

```c
/* ============================================================================
 * contact_alloc_80059e44.c  — contact record allocator/constructor [PHASE 3 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.80059e44  (size 668 bytes, 0x80059e44..0x8005a0e0)
 * CONFIDENCE       : CONFIRMED (cursor/wrap, slot search, coord write, both metadata tables,
 *                    full field fill, return). A couple of sub-values are LIKELY/UNKNOWN
 *                    (render-attr helper fcn.800593e8 output; the +0x24 script variant).
 * SOURCE NOTES     : docs/EXECUTABLE_AND_OVERLAYS.md (metadata table), docs/EXPERIMENT_LOG.md
 *                    (capacity/cursor), docs/DAT_FORMAT_AND_RELOCATION.md, r2 disasm.
 * KNOWN CALLERS    : fcn.80053814 (Phase 2): grain ctor 0x51/stackArg 3; generic 0x71/0x18;
 *                    kind-0x30 0x71/0x17. Also fcn.8005a0e0 (sibling w/ explicit transform args).
 * KNOWN CALLEES    : fcn.800593e8 (render-attr lookup: (nibble, value) -> attr word),
 *                    fcn.80024ddc (post-init step; a0 = new record).
 * KNOWN GLOBALS    : G_ALLOC_CURSOR(0x8008234c, wrap at 0x40), G_CONTACT_ARRAY(0x800b0d18,
 *                    64 * 0x38), metadata table B = G_METADATA_TABLE(0x8007941c, stride 0x14,
 *                    indexed by ctorType), table A = 0x80079e30 (stride 0x14, indexed by
 *                    stackArg; render attrs), 0x800822f4 (script cursor; +0x24 variant only).
 * UNRESOLVED       : fcn.800593e8 internals; table A (0x80079e30) full meaning; when metaB+0x04
 *                    is negative (the script-driven +0x22/+0x24 variant) — semantics UNKNOWN.
 *
 * ABI (CONFIRMED): record = contact_alloc(x, y, z, ctorType, stackArg).
 *   ctorType = a3 -> s3 ; stackArg = [sp+0x40] (caller's stack arg).
 *   x/y/z are RUNTIME coords (caller already <<5). ctorType picks metadata row B; stackArg
 *   picks render-attr row A. Returns the new ContactRecord*.
 * ============================================================================ */

#include "re_types.h"

#define LW(p)   (*(int32_t  *)(p))
#define LH(p)   (*(int16_t  *)(p))
#define LHU(p)  (*(uint16_t *)(p))
#define LBU(p)  (*(uint8_t  *)(p))
#define LB(p)   (*(int8_t   *)(p))
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))
#define SH(p,v) (*(uint16_t *)(p) = (uint16_t)(v))
#define SB(p,v) (*(uint8_t  *)(p) = (uint8_t)(v))

#define METADATA_A 0x80079e30u   /* table A: render attrs, stride 0x14, index = stackArg */
/* METADATA_B == G_METADATA_TABLE (0x8007941c), stride 0x14, index = ctorType */

extern int32_t fcn_800593e8(int32_t nibble, int32_t value); /* render-attr lookup (Phase: later) */
extern void    fcn_80024ddc(void *record);                  /* post-init (Phase: later) */

/*
 * fcn.80059e44 — allocate the next free slot in the 64-entry contact array and fill it
 * from coords + the ctorType (metadata B) and stackArg (render-attr A) rows.
 */
ContactRecord *contact_alloc(int32_t x, int32_t y, int32_t z, int ctorType, int stackArg)
{
    /* ---- find a free slot: advance cursor (wrap at 0x40), skip occupied slots ----
     * occupied := (record.flags & 0x80) && (record.active_type != 0)  (CONFIRMED) */
    int32_t slot;
    for (;;) {
        slot = LW(G_ALLOC_CURSOR) + 1;
        if (slot >= 0x40) slot = 0;          /* wrap (slti 0x40; reset to 0) */
        SW(G_ALLOC_CURSOR, slot);
        int32_t off = slot * 0x38;           /* v0*8 - v0 = *7; *8 = *0x38 */
        if (!(LBU(G_CONTACT_ARRAY + off + 0x33) & 0x80)) break;  /* slot free (flags bit7 clear) */
        if (LH(G_CONTACT_ARRAY + off + 0x22) == 0) break;        /* or inactive */
        /* else occupied -> keep searching. NOTE: no full-array escape (capacity hang risk). */
    }

    ContactRecord *rec = (ContactRecord *)(uintptr_t)(G_CONTACT_ARRAY + slot * 0x38); /* s1 */
    uint8_t *A = (uint8_t *)(uintptr_t)(METADATA_A     + stackArg * 0x14);            /* s0 = table A */
    uint8_t *B = (uint8_t *)(uintptr_t)(G_METADATA_TABLE + ctorType * 0x14);          /* s2 = table B */

    /* ---- coords (CONFIRMED +0/+4/+8) ---- */
    SW((uint8_t*)rec + 0x00, x);
    SW((uint8_t*)rec + 0x04, y);
    SW((uint8_t*)rec + 0x08, z);

    /* ---- render attrs +0x0c/+0x10/+0x14/+0x18 from table A[0] nibbles + A[4/8/c/10] ----
     * A[0] is a 4-nibble selector; each nibble + a value -> fcn.800593e8 -> attr word. LIKELY. */
    SW((uint8_t*)rec + 0x0c, fcn_800593e8((LW(A+0) & 0xf000) >> 12, LW(A + 0x04)));
    SW((uint8_t*)rec + 0x10, fcn_800593e8((LW(A+0) & 0x0f00) >>  8, LW(A + 0x08)));
    SW((uint8_t*)rec + 0x14, fcn_800593e8((LW(A+0) & 0x00f0) >>  4, LW(A + 0x0c)));
    SW((uint8_t*)rec + 0x18, fcn_800593e8((LW(A+0) & 0x000f)      , LW(A + 0x10)));

    SW((uint8_t*)rec + 0x1c, -1);          /* CONFIRMED init = -1 */
    SB((uint8_t*)rec + 0x32, 0x20);        /* CONFIRMED const 0x20 */
    SB((uint8_t*)rec + 0x33, LBU(B + 0x10)); /* CONFIRMED flags = metaB+0x10 */

    /* ---- fields from metadata B (index = ctorType) — CONFIRMED map ---- */
    SH((uint8_t*)rec + 0x20, LHU(B + 0x00)); /* action_id   = metaB+0x00 */
    SH((uint8_t*)rec + 0x22, LHU(B + 0x02)); /* active_type = metaB+0x02 (may be overwritten below) */
    SB((uint8_t*)rec + 0x30, LBU(B + 0x07)); /* +0x30 = metaB+0x07 */
    SB((uint8_t*)rec + 0x31, LBU(B + 0x06)); /* +0x31 = metaB+0x06 */

    /* +0x24 init value: if metaB+0x04 >= 0 use it directly; else a script-driven variant
     * that also recomputes +0x22 = (cursorByte&3 - metaB+0x04) * rec[+0x30]. (variant UNKNOWN) */
    if (LH(B + 0x04) >= 0) {
        SH((uint8_t*)rec + 0x24, LH(B + 0x04));
    } else {
        uint8_t *cur = (uint8_t *)(uintptr_t)LW(0x800822f4);     /* script cursor */
        SW(0x800822f4, (int32_t)(uintptr_t)(cur + 1));           /* cursor++ */
        int16_t v = (int16_t)((LBU(cur) & 3) - LHU(B + 0x04));
        SH((uint8_t*)rec + 0x24, v);
        SH((uint8_t*)rec + 0x22, (uint16_t)(v * LBU((uint8_t*)rec + 0x30))); /* overwrites active_type */
    }
    SH((uint8_t*)rec + 0x26, LHU((uint8_t*)rec + 0x24)); /* CONFIRMED +0x26 = copy of +0x24 */

    SB((uint8_t*)rec + 0x34, LBU(B + 0x11)); /* CONFIRMED +0x34 = metaB+0x11 */
    SB((uint8_t*)rec + 0x35, LBU(B + 0x12)); /* CONFIRMED +0x35 = metaB+0x12 */
    SB((uint8_t*)rec + 0x36, LBU(B + 0x13)); /* CONFIRMED +0x36 = metaB+0x13 */

    SH((uint8_t*)rec + 0x28, LHU(B + 0x08)); /* CONFIRMED radius_add = metaB+0x08 */
    SH((uint8_t*)rec + 0x2a, LHU(B + 0x0a)); /* CONFIRMED +0x2a = metaB+0x0a */
    SH((uint8_t*)rec + 0x2c, LHU(B + 0x0c)); /* CONFIRMED +0x2c = metaB+0x0c */
    SB((uint8_t*)rec + 0x2f, LBU(B + 0x0f)); /* CONFIRMED +0x2f = metaB+0x0f */

    /* +0x2e sign select from metaB+0x0e: 0 -> 0, 1 -> -ctorType, else -> +ctorType (CONFIRMED) */
    {
        int8_t sel = LB(B + 0x0e);
        if (sel == 0)      SB((uint8_t*)rec + 0x2e, 0);
        else if (sel == 1) SB((uint8_t*)rec + 0x2e, (uint8_t)(-ctorType));
        else               SB((uint8_t*)rec + 0x2e, (uint8_t)ctorType);
    }

    fcn_80024ddc(rec);   /* post-init */
    return rec;          /* CONFIRMED: returns the new record (v0 = s1) */
}

/* ----------------------------------------------------------------------------
 * PHASE 3 FINDINGS (fed back to re_types.h / docs):
 *  - CONFIRMED ABI: contact_alloc(x,y,z, ctorType=a3, stackArg=[sp+0x40]); returns record*.
 *    (Corrects the Phase-2 extern arg order: 4th = ctorType, 5th = stackArg.)
 *  - CONFIRMED allocator: cursor 0x8008234c pre-incremented, wraps at 0x40; skips slots where
 *    (flags&0x80 && active_type!=0). NO full-array escape => documented capacity hang risk.
 *  - CONFIRMED slot = 0x800b0d18 + slot*0x38.
 *  - CONFIRMED metadata B (0x8007941c, index ctorType) full field map (extends notes):
 *      +0x00->rec+0x20 action_id; +0x02->rec+0x22 active_type; +0x04->rec+0x24 init (or script
 *      variant); +0x06->rec+0x31; +0x07->rec+0x30; +0x08->rec+0x28 radius_add; +0x0a->rec+0x2a;
 *      +0x0c->rec+0x2c; +0x0e->rec+0x2e sign(ctorType); +0x0f->rec+0x2f; +0x10->rec+0x33 flags;
 *      +0x11/12/13->rec+0x34/35/36. rec+0x26 = copy of rec+0x24.
 *  - NEW: table A (0x80079e30, index stackArg) supplies render attrs rec+0x0c/0x10/0x14/0x18 via
 *    fcn.800593e8(nibble of A[0], A[+4/8/c/10]). LIKELY render/texture; A internals UNKNOWN.
 *  - CONFIRMED constants: rec+0x1c init -1; rec+0x32 = 0x20.
 *  - UNKNOWN: fcn.800593e8 math; the metaB+0x04<0 script-driven +0x22/+0x24 variant; rec+0x37.
 * ---------------------------------------------------------------------------- */
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80059E44.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80059E44.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80059E44.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
