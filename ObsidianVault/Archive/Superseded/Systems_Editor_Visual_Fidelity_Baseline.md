---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Editor Visual Fidelity Baseline.md
aliases:
  - "Editor Visual Fidelity Baseline"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Editor Visual Fidelity Baseline.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Editor_Visual_Fidelity_Baseline.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Editor Visual Fidelity Baseline
type: system
status: active reference
updated: 2026-07-02
confidence: IMPLEMENTED-ARCHITECTURE / OFFLINE-PREVIEW-PARTIAL
tags: [system, editor, visual-fidelity, rcg-002]
---

# Editor Visual Fidelity Baseline

> `RCG-002` is closed as an architecture gap: the editor's 1:1 visual-fidelity path is the isolated DuckStation live view, not a full offline renderer recreation. Offline Blender/GL views remain useful authoring and regression previews, but exact retail presentation is delegated to the real game renderer.

## Decision

- **Canonical visual verifier:** `level_editor/live_view.py` + `level_editor/live_editor.py` drive an isolated DuckStation instance and stream the real framebuffer. This is 1:1 by construction and avoids reimplementing ABL's renderer.
- **Authoring surface:** Blender remains the practical editor for authored geometry/objects. DuckStation is the verifier/debugger, not the primary modeling UI.
- **Offline preview:** `level_editor/scene3d.py` and `render_capture.py` are bounded previews/harnesses. They are allowed to be approximate and must not be treated as the retail oracle.

## Static audit

| Check | Status | Anchor |
|---|---|---|
| `isolated_duckstation_renderer` | PASS | `level_editor/live_view.py` |
| `fast_vram_frame_stream` | PASS | `level_editor/live_view.py` |
| `live_qt_editor_loop` | PASS | `level_editor/live_editor.py` |
| `live_edit_preview` | PASS | `level_editor/live_view.py` |
| `disc_build_from_editor` | PASS | `level_editor/live_editor.py` |
| `offline_capture_harness` | PASS | `level_editor/render_capture.py` |
| `per_face_texture_pages` | PASS | `level_editor/scene_importer.py` |
| `offline_proxy_objects` | PASS | `level_editor/scene3d.py` |
| `blender_authoring_demoted_live_view_to_verifier` | PASS | `ObsidianVault/Systems/Blender-first ABL level editor.md` |
| `old_plan_records_architecture_pivot` | PASS | `ObsidianVault/Systems/LEVEL01 Editor Visual-Fidelity Plan.md` |

## What is solved

- The editor has a real-game visual path: isolated DuckStation launch, save load, frame capture via VRAM readback, `gpu.pickObject`, and bounded live RAM edit preview.
- The offline renderer has a harness for regression screenshots and several LEVEL01 correctness improvements: per-face texture-page handling, textured decor, nearest sampling, and no fake Lambert lighting.
- The Blender-first workflow explicitly demotes the live view to verifier/debugger and keeps authored level data in Blender/exporter files.

## Residuals moved out of RCG-002

- **Real pickup/actor visual polish in offline preview:** `RCG-008` plus material/transparency gaps below. `RCG-005` actor/model binding is closed by [[Actor model binding catalog]].
- **Exact per-draw CLUT/materials and transparency:** `RCG-013` and `RCG-014`.
- **All-level texture/page inventories:** `RCG-023`.
- **Camera modes beyond normal follow / telescope / cutscene / boss presentation:** `RCG-010`.
- **Sky/backdrop authoring and parallax:** `RCG-030`.

## Reproduction

```bash
python3 tools/editor_visual_fidelity_audit.py --json build/editor_visual_fidelity_audit.json --markdown 'ObsidianVault/Systems/Editor Visual Fidelity Baseline.md'
```

## Related

[[Retail Gameplay Completeness Gap Audit]] · [[LEVEL01 Editor Visual-Fidelity Plan]] · [[Blender-first ABL level editor]] · [[Campaign Level Coverage Matrix]] · `src_re/editor_visual_fidelity.c`
