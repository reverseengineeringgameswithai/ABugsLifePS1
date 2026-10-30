---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Geometry/Geometry pipeline.md
aliases:
  - "Geometry pipeline"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Geometry/Geometry pipeline.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Geometry pipeline
type: system
tags: [system, geometry, rendering, collision, pipeline]
---

# Geometry pipeline (visual + collision)

> The two parallel data-flows for level geometry. **They never meet** — editing one does not move the other ([[Finding - Visual is not collision]]).

## Visual flow (what you SEE)
```
LEVEL.DAT payloads ──┐
(Candidate A etc.)   │  [[FUNC_8001CDC0]] parse → trail/pass3 tables ([[MEM - Trail and pass3 tables]])
                     │  → [[FUNC_800224EC]] driver → [[FUNC_800140A0]] cull → [[MEM - Survivor lists]]
                     │  → [[FUNC_8001EA6C]]/[[FUNC_800206E8]] builders → [[FUNC_80010000]] emit (RTPS/RTPT/NCLIP) → GPU
                     │  ([[FUNC_80019934]] sub-emitter draws bulk foreground floor)
LEVEL.RAW chunk 35 ──┘  [[FUNC_8003A318]] load → [[FUNC_8001A1DC]] decompress → [[MEM - Terrain vertex buffer 8012C1D0]]
                        → [[FUNC_800172DC]] draws GP0 0x3C terrain quads
```

## Collision flow (what Flik STANDS ON)
```
LEVEL.RAW chunk 32 → [[FUNC_8001A1DC]] decompress → src 0x800F7BF8
   → [[FUNC_80030F60]] build [[MEM - Collision sector table 800A7E48]] (<<5) + [[MEM - Collision plane record]]
   → runtime sector AABB select → candidate list 0x8009c230
   → [[FUNC_800345CC]] resolve (swept plane clamp + skin) → [[FUNC_8003633C]] commit → player Y 0x800a6504
```

## Sky flow
GP0 0x02 background fill (NOT an image): table `0x800c1688` → cache [[MEM - Sky DRAWENV color cache 800771BC]] → [[FUNC_800639CC]] → GPU. See [[Finding - Sky is a GP0 background fill]].

## The key insight
Visual = LEVEL.DAT payloads (`fcn.80010000` — the visible floor) + LEVEL.RAW chunk 35 (occluded terrain-mesh layer); Collision = LEVEL.RAW chunk 32. Different files, different RAM, different code. To make Flik fall into a *visible* pit you must edit **both** levers in a matched way. See [[Finding - Visual is not collision]], [[Finding - Localized terrain edit]].

## Related
[[Geometry]] · [[Rendering]] · [[Collision]] · [[Playbook - Correlate rendering and collision]] · [[Playbook - Find geometry sources]]
