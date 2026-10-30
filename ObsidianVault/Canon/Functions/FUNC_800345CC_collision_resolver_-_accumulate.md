---
kind: function
id: FUNC_800345CC
aliases: [FUNC_800345CC, 0x800345cc]
address: 0x800345CC
name: collision_resolver_-_accumulate
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
  - src_re/collision_plane_resolver_800345cc.c
patch_policy: unknown
---

# FUNC_800345CC - collision resolver - accumulate

## Purpose

Iterates the per-frame collision-candidate list and accumulates the resolved position that the integrator commits. Where "floor height" is computed as a swept plane clamp.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_800345CC.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x800345CC`
- Name: `collision_resolver_-_accumulate`
- Original note: `ObsidianVault/Functions/FUNC_800345CC.md`
- Source path: `src_re/collision_plane_resolver_800345cc.c`

## C source excerpt

Source: `src_re/collision_plane_resolver_800345cc.c`

```c
/* ============================================================================
 * collision_plane_resolver_800345cc.c — oriented wall/slope plane collision [DECODED]
 * ----------------------------------------------------------------------------
 * Punchlist §2.2 "editing individual planes (for slopes/walls)" — DECODED 2026-06-24
 * (isolated DuckStation, pristine v1.0, LEVEL01; disasm + live read of the plane pool).
 *
 * HEADLINE
 *   Besides the flat per-sector floor (sector table 0x800a7e48 origin-Y, edited by
 *   tools/edit_collision_sector.py), LEVEL collision has a small set of ORIENTED
 *   PLANES — the walls/slopes. `FUNC_800345CC` is the SWEPT collision resolver: it
 *   tests Flik's movement segment against every plane and, where the segment crosses
 *   one, computes the contact point. LEVEL01 has exactly **6** planes (count
 *   [gp+0x57c]=6), on sectors 119 and 166.
 *
 * THE PLANE RECORD (0x20 bytes, in LEVEL.RAW chunk 32; same record import_collision
 * documented). All fields s16:
 *   +0x00 normal.x   +0x02 normal.y   +0x04 normal.z     // |normal| == 0x4000 (fixed-point 1.0)
 *   +0x06 ref.x      +0x08 ref.y      +0x0a ref.z        // a point on the plane (sector-local)
 *   +0x0c.. additional fields (poly extent / deltas, also read by FUNC_80038090's
 *           point-in-polygon region test)
 *   => normal = plane orientation (tilt a wall/slope); ref = a point on it (move it).
 *
 * RUNTIME INDIRECTION (built by the converter FUNC_80030F60 from chunk 32; re-armed
 * every level load — the planes are scattered, NOT a contiguous array, so they are
 * located via these tables, not by offline scan):
 *   count            = *(s32*)(gp + 0x57c)             // 6 in LEVEL01
 *   plane_ptr[i]     = *(u32*)(0x8009c230 + i*4)       // -> a plane record (chunk-32 + 0x800C1688)
 *   plane_sector[i]  = *(s16*)(0x80091718 + i*2)       // the sector the plane belongs to
 *   sector_origin    = SECTOR_TABLE[sector] (0x800a7e48, stride 0x30, X/Y/Z @ +0/4/8)
 *   LEVEL01 plane chunk-32 offsets (live-probed): 0x1c420, 0x1cc30, 0x1cc50, 0x1cc70,
 *                                                 0x303f8, 0x30418 (sectors 119,119,119,119,166,166)
 *
 * THE RESOLVER (FUNC_800345CC, decoded) — for each plane, swept test of the player's
 * movement segment (endpoints p0,p1 in args; made sector-relative via sector_origin):
 *     d0 = (normal . (p0 - (ref<<5))) >> 14;      // signed distance, endpoint 0
 *     d1 = (normal . (p1 - (ref<<5))) >> 14;      // signed distance, endpoint 1
 *     if (d0 >= 0) continue;                       // p0 not behind the plane -> no hit
 *     if (d1 <  0) continue;                       // p1 not in front -> no crossing
 *     span = d1 - d0;
 *     // intersection = p + (d1/span)*segment  (the >>14 uses normal == 0x4000 unit)
 *     contact = p + segment * d1 / span;          // clamp Flik to the plane surface
 *   The winner's contact point is committed (with sector_origin re-added) by
 *   FUNC_8003633C to the player. (ref is stored <<5-scaled; normal is the 0x4000 unit.)
 *
 * EDITING A PLANE (§2.2 lever)
 *   - Tilt a wall/slope:  edit normal (+0x00/+0x02/+0x04), keeping |normal| ~ 0x4000.
 *   - Move a wall/slope:  edit ref   (+0x06/+0x08/+0x0a) (sector-local, value is <<5 at use).
 *   - Disable a plane:    zero the normal (degenerate -> the swept test never crosses).
 *   Tools: tools/probe_collision_planes.py (live: list offset/sector/normal/ref) ->
 *          tools/edit_collision_plane.py (offline: edit a plane by chunk-32 offset ->
 *          recompress chunk 32 -> splice) -> tools/build_autolayout_disc.py.
 *   The chunk-32 recompress+auto-layout rebuild path is already in-game proven (§2/§6,§10).
 *
 * VERIFICATION STATUS
 *   - Structure + resolver: CONFIRMED (disasm + live read of all 6 planes via the arrays).
 *   - Live poke of the 6 planes while Flik STOOD STILL did NOT move his Y — expected:
 *     these are swept wall/slope planes, only active when his movement segment crosses
 *     one; in the test save he was on flat floor (the sector-origin lever), not on a plane.
 *   - A live in-game demonstration of a plane EDIT needs Flik moving through a specific
 *     plane's polygon; deferred (teleport-to-spot is death-from-falling-confounded — see
 *     proximity_updater_8004abf4.c / the §10 method note). The byte edit + rebuild are
 *     round-trip verified offline.
 *
 * RELATED: edit_collision_sector.py (flat floor origin-Y), G29 collision source,
 *          FUNC_80030F60 (converter), FUNC_8003633C (committer), FUNC_80038090
 *          (point-in-polygon region/trigger test over the same 6 records),
 *          level_exit_trigger.c (sector region code, a different field).
 * ============================================================================ */

#include "re_types.h"

#define PLANE_COUNT_GP_OFF   0x57c          /* *(s32*)(gp + 0x57c) */
#define PLANE_PTR_ARRAY      0x8009c230     /* u32 per plane -> record */
#define PLANE_SECTOR_ARRAY   0x80091718     /* s16 per plane -> sector index */
#define SECTOR_TABLE_BASE    0x800a7e48
#define SECTOR_STRIDE        0x30
#define COLLISION_LIVE_BASE  0x800C1688     /* chunk 32 decompresses here */
#define NORMAL_ONE           0x4000         /* fixed-point 1.0 ; dot >> 14 normalizes */

typedef struct {            /* oriented plane record, 0x20 bytes, in chunk 32 */
    s16 nx, ny, nz;         /* +0x00 normal (|n| == 0x4000) */
    s16 rx, ry, rz;         /* +0x06 ref point on the plane (sector-local) */
    s16 ext[5];             /* +0x0c polygon extent / deltas (region test) */
} Plane;

/* dot(normal, p - ref<<5) >> 14 : signed distance of point p from the plane. */
static s32 plane_dist(const Plane *pl, s32 px, s32 py, s32 pz)
{
    s32 dx = px - ((s32)pl->rx << 5);
    s32 dy = py - ((s32)pl->ry << 5);
    s32 dz = pz - ((s32)pl->rz << 5);
    return (pl->nx * dx + pl->ny * dy + pl->nz * dz) >> 14;
}

/*
 * FUNC_800345CC (slice) — swept test of the movement segment [p0..p1] against every
 * plane; the first plane the segment crosses (p0 behind, p1 in front) yields the
 * contact point, which FUNC_8003633C commits to the player. p0/p1 are passed
 * sector-relative (caller subtracts SECTOR_TABLE[sector] origin first).
 */
int resolve_plane_collision_800345cc(s32 p0[3], s32 p1[3], s32 out_contact[3])
{
    int count = *(volatile s32 *)/* gp-rel */ (0 + PLANE_COUNT_GP_OFF);  /* = *(gp+0x57c) */
    for (int i = 0; i < count; i++) {
        const Plane *pl = (const Plane *)(*(volatile u32 *)(PLANE_PTR_ARRAY + i * 4));

        s32 d0 = plane_dist(pl, p0[0], p0[1], p0[2]);
        s32 d1 = plane_dist(pl, p1[0], p1[1], p1[2]);
        if (d0 >= 0)            /* start not behind the plane */
            continue;
        if (d1 < 0)             /* end not in front -> no crossing */
            continue;

        s32 span = d1 - d0;     /* segment crosses the plane */
        for (int k = 0; k < 3; k++)
            out_contact[k] = p0[k] + (p1[k] - p0[k]) * d1 / span;  /* clamp to surface */
        return i;               /* hit plane i */
    }
    return -1;                  /* no plane crossed -> flat sector floor applies */
}
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_800345CC.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_800345CC.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_800345CC.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

