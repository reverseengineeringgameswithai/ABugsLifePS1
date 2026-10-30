---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/ABL 3D Phase 1 Gap Checklist.md
aliases:
  - "ABL 3D Phase 1 Gap Checklist"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/ABL 3D Phase 1 Gap Checklist.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/ABL_3D_Phase_1_Gap_Checklist.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: ABL 3D Phase 1 Gap Checklist
type: system
updated: 2026-06-19
status: active checklist
confidence: MIXED
tags: [system, tooling, gui, leveleditor, 3d, checklist]
---

# ABL 3D Phase 1 Gap Checklist

> Checklist of what is still missing for the replanned Phase 1 scene importer. This exists to keep the editor honest: the goal is to import confirmed scene data with provenance, not to pretend the app already has a complete game-like renderer.

## Current Phase 1 Implementation Slice

- `level_editor/scene_importer.py` exists.
- It imports type-`0x3f` pickups as confirmed scene objects.
- **It now surveys and imports EVERY referenced `fcn.80010000` payload** (217 in LEVEL01), not just Candidate A — decoded to vertices, classified floor/scenery/decor, with instancing + per-record provenance. Survey logic ported from `tools/analyze_g27_floor_candidates.py`.
- **It extracts heuristic triangle faces** (≈15.6k in LEVEL01) from the confirmed command-stream vertex-offset layout (labelled `HEURISTIC` — winding not byte-confirmed).
- **It attaches a flat placeholder material** per mesh, keyed by classification.
- **It imports the one byte-confirmed collision plane** from LEVEL.RAW chunk 32 as a worked-example overlay record (`SceneGraph.collision`).
- It records remaining renderer/asset/collision/sky work as structured `SceneIssue` entries.
- It can print a classification summary or full JSON scene graph.
- The PySide6 app exposes this data in the `Scene Import` tab (meshes grouped by classification; confirmed/floor meshes + collision detailed).

## Missing Checklist

> Status updated 2026-06-19 after the static (no-DuckStation) importer pass. Items needing the running emulator to *confirm* (not guess) are tagged **DS-req**.

| Gap | Severity | Status | Notes / next step |
|-----|----------|--------|-------------------|
| Clean editor-side parser for all visible LEVEL.DAT scene/floor meshes | High | **Implemented** | `scene_importer.import_meshes()` walks all 217 referenced `fcn.80010000` payloads (pass-1 trailer + pass-3 reference records), decodes vertices, and classifies floor_terrain/scenery_surface/scenery_mesh/decor_prop via the G27 flatness+footprint+instancing tells. Per-mesh provenance (file/offset/instancing) preserved. |
| Primitive command stream to renderable triangles | High | **Partial (heuristic)** | `_extract_faces()` fan-triangulates runs of command-stream vertex-offset halfwords (multiple of 0x0c, < count*0x0c). Faces marked `HEURISTIC`. **DS-req:** exact operand layout/winding needs execTrace of jump table `0x8001036C` (type-0 case `0x8001046c`) + frame-diff validation. |
| Texture/material binding | High | **Partial (placeholder)** | Flat placeholder material per classification now attached (`SceneMaterial`). Real texture/CLUT binding still unresolved; also gated on the unknown vertex `attr` (vertex+0x8) role. **DS-req** for attr role + Region-A bpp/CLUT. |
| Real pickup/object model rendering | Medium | Missing | Type-`0x3f` objects have confirmed coordinates/kinds, but the app still needs proxy or real models for grain, tokens, berries, FLIK letters, and telescopes. |
| Full scenery asset mapping | High | Missing | `.ALL`, `.ANM`, `GFX/*.RAW`, and level texture data are only partly decoded for editor rendering. Need an asset import inventory. |
| Collision plane import/rendering | Medium | **Partial** | One byte-confirmed chunk-32 plane (`0x800D10E8` = chunk32+0xfa60, `live = 0x800C1688 + off`) decoded as an overlay record (32B: s16 normal @+0/2/4, s16 ref @+6/8/a; `|n|≈0x4000`). **DS-req:** full plane-array bounds come from the runtime sector table `0x800a7e48` (converter `FUNC_80030F60`) — dump it to enumerate all planes offline. |
| Renderer architecture | High | **Implemented (moderngl GPU)** | Phase 0/2 done: `level_editor/scene3d.py` (camera + assembly + moderngl Renderer) + `scene3d_view.py` (QOpenGLWidget free-cam viewport) render the level on the GPU. New **3D Scene** tab: fly cam (WASD+QE, RMB look), orbit/pan/zoom, ray-pick pickups, drag-to-move on the ground plane → emits `Operation.move` into the edit plan; selection syncs with table/inspector. Flat-shaded untextured (level *shape*, not skin); 26 model-space decor hidden (no per-instance transform). Verified headlessly on RTX 5090 standalone context (render-to-FBO + pick roundtrip, `test_scene3d.py` 4/4). Marker view retained as the legacy "3D Tools" tab. |
| LEVEL01-first limitation | Medium | **Partial (pickups general; meshes LEVEL01-only)** | Pickups now import for all **9 gameplay levels** (LEVEL01-10; LEVEL00 has none and loads gracefully). Mesh survey is `LevelProfile`-driven but only LEVEL01 is registered, and registering others is **not purely static**: the trail/p3/src/payload band offsets were runtime-derived, the DAT section chain isn't cleanly self-describing (LEVEL00 even starts with record-count 0 → different layout), and a self-validating linear band walk recovered only **209/218** LEVEL01 payloads — not authoritative. So per-level mesh profiles need runtime capture (**DS-req**) or deeper DAT-format RE. Collision overlay is gated to LEVEL01 (the cached decompressed dump is LEVEL01's). Verified by `level_editor/test_scene_importer.py`. |
| Scene provenance UI/report panel | Medium | Implemented | The PySide6 app now has a `Scene Import` tab fed by `level_editor/scene_importer.py`. |
| Sky/background import | Low | **Blocked (vault discrepancy)** | NOT imported — the vault sky finding claims chunk-32 offset 0 = RGB `31 59 db`, but offset 0 is the record header (`03 01 00 00 b6 b2 …`) and `31 59 db` does not occur anywhere in chunk 32 (it appears in chunk 29, a texture frame). **DS-req:** accessLog the sky copier (`0x8003b2b8/d8/f8` reading `s3=0x800c1688`) to capture the true read offset, then reconcile [[Finding - Sky color on-disk table]] vs [[MEM - Collision plane record]]. |

## Enough To Start?

Yes, enough to start Phase 1 as a provenance-first importer:

- Pickups are confirmed and editable.
- Candidate A / `fcn.80010000` payload format is documented enough to decode vertices.
- Visual-vs-collision separation is confirmed.
- Collision source direction is strong enough to plan a separate overlay.

### Static (no-DuckStation) pass done 2026-06-19

The importer now produces a full LEVEL01 scene graph: **217 classified mesh payloads**, **≈15.6k heuristic faces**, **placeholder materials**, **70 pickups**, and **1 worked-example collision plane** — every element source-traced. This satisfies the Phase 1 exit criteria (floor/scenery mesh placeholders + pickup placements, each traceable to file/offset/layer, with missing bindings explicit). What remains needs the running emulator and is tagged **DS-req** above.

Not enough for:

- faithful textured rendering (needs `attr` role + Region-A CLUT decode — **DS-req**);
- complete in-game object models;
- correct face winding (current faces are heuristic — **DS-req** execTrace);
- full collision plane enumeration (needs runtime sector table — **DS-req**);
- sky import (on-disk source unconfirmed — **DS-req**);
- all-level generalized scene rendering;
- safe floor/collision editing.

### DuckStation requirements surfaced by this pass

1. **Face winding/topology** — execTrace jump table `0x8001036C` (type-0 triangle `0x8001046c`) + frame-diff.
2. **Vertex `attr` role** (vertex+0x8) — execTrace `FUNC_80010000` / `gpu.readVramRect` correlation.
3. **Full collision planes** — dump sector table `0x800a7e48` (accessLog converter `FUNC_80030F60`).
4. **Sky on-disk offset** — accessLog copier `0x8003b2b8/d8/f8` (reconcile the `31 59 db` discrepancy).

## Related

[[ABL 3D Level Editor Roadmap]] · [[ABL Level Editor]] · [[MEM - fcn.80010000 mesh payload]] · [[Finding - Candidate A is DAT-backed visual terrain]] · [[Finding - Visible ground from DAT verts]] · [[Finding - Visual is not collision]] · [[MEM - Type-0x3f placement record]]
