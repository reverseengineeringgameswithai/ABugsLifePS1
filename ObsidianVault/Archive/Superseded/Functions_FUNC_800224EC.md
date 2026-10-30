---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_800224EC.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_800224EC.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_800224EC_scene_-_render_driver.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_800224EC — scene / render driver
type: function
address: 0x800224EC
confidence: CONFIRMED
tags: [function, rendering, geometry, driver]
---
# FUNC_800224EC — scene / render driver (geometry consumer)

> The per-scene/per-frame render driver. Reads the parser geometry pointers, sets up a camera matrix, runs the cull→build→emit pipeline. The top of the visible-geometry render chain (NOT collision).

| Field | Value |
|-------|-------|
| Address | 0x800224EC (size 900) |
| Source file | `src_re_geometry/geometry_render_consumers.c` (G4) |
| Confidence | CONFIRMED render driver reading parser geometry |

## Purpose
Reads `G_TRAIL_BLOCK_PTR` (`0x800824ac`, = DATbase+0x1504) and `G_PASS3_BASE_PTR` (`0x80082508`, = DATbase+0x3aec); dispatches geometry through GTE transform helpers under a camera matrix, then runs the object render/build loop. In G30, the branch selector `[0x800a6588]` picks scene path A (`0x8004f428`) / B (`0x8004f448`).

## Arguments / Returns
Scene/frame context (not formalized). Void.

## Calls (callees)
- [[FUNC_80017B98]] (GTE matrix setup) ×2
- [[FUNC_800140A0]] (trail cull), `fcn.80014360` (pass-3 cull analog), `fcn.800146e0` (libgte camera-matrix leaf)
- `fcn.8003f938` (object render/projection loop)
- [[FUNC_8001EA6C]] / [[FUNC_800206E8]] (primitive builders)
- [[FUNC_8001DFE4]] (scene-geometry dispatcher; G30 path)

## Called by (callers)
- `0x8004f428` / `0x8004f448` / `0x8004f718` (scene/gameplay state path near `fcn.8004ecd4`).

## Globals & structures touched
- `0x800824ac` trail ptr, `0x80082508` pass-3 ptr (see [[MEM - Trail and pass3 tables]]); view scratch `0x1f8003b4`/`0x1f800384`, camera `0x1f800374`; loop count `0x80082440`.

## Evidence & confidence notes
G4 identified it by gp-relative ref scan of the 5 parser globals. G6: patching DAT+0x1526 via this path removes most visible terrain ([[Finding - Trail flag gates terrain render]]).

## Related
- Functions: [[FUNC_800140A0]] · [[FUNC_8001DFE4]] · [[FUNC_8001EA6C]] · [[FUNC_800206E8]] · [[FUNC_80017B98]]
- Findings: [[Finding - Trail flag gates terrain render]] · [[Finding - No static collision consumer]]
- Hubs: [[Rendering]] · Source docs: `src_re_geometry/geometry_render_consumers.c`, `geometry_notes.md`
