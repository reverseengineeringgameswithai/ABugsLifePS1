---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/ABL 3D Level Editor Roadmap.md
aliases:
  - "ABL 3D Level Editor Roadmap"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/ABL 3D Level Editor Roadmap.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/ABL_3D_Level_Editor_Roadmap.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: ABL 3D Level Editor Roadmap
type: system
updated: 2026-06-19
status: replanned for game-like scene editor
confidence: PLANNED
tags: [system, tooling, gui, leveleditor, 3d, roadmap, pyside6]
---

# ABL 3D Level Editor Roadmap

> Replanned target: the 3D editor should feel like viewing an actual *A Bug's Life* level in an external editor. The user should see scenery, floor/terrain, placed pickups/objects, and eventually collision/edit handles in one navigable 3D space. The current PySide6 3D pickup-marker view is useful as a diagnostic/prototype, but it is not the desired final 3D editing experience.

## Target Experience

The editor should eventually support:

- Load a level and render it as a 3D scene resembling the in-game space.
- Free camera movement through the level:
  - orbit/focus selected;
  - pan/zoom;
  - fly/free-roam camera.
- Visual context:
  - visible floor/scenery;
  - backdrop/sky where practical;
  - collectible/object placements;
  - separate collision overlay;
  - optional debug layer toggles.
- Direct editing in the 3D scene:
  - select pickups/objects;
  - move items with mouse/gizmo controls;
  - add/duplicate items;
  - adjust floor/terrain/collision only after those layers are safely mapped.
- Export edit plans and invoke patch/rebuild tooling explicitly.
- Never silently modify DAT, RAW, BIN, CUE, or rebuilt disc images.

## Current Implementation Status

Implemented in `level_editor/pyside_level_editor.py`:

- DAT type-`0x3f` parser.
- Level selector.
- 2D X/Z map.
- Item table and inspector.
- Edit-plan list and YAML export.
- 3D pickup-marker diagnostic viewport:
  - category-colored markers;
  - grid/axis context;
  - marker click selection;
  - edit-plan ghost previews.
- Error logging to `level_editor/logs/pyside_level_editor.log`.

Important correction:

- The current 3D marker viewport is **not** the real Phase 1 target anymore.
- It should be treated as a temporary spatial/debug view until the scene renderer exists.
- The next work should focus on rendering real level context, not adding more camera controls to a marker-only scene.
- Missing Phase 1 prerequisites are tracked in [[ABL 3D Phase 1 Gap Checklist]].

## Design Rules

1. The editor remains non-mutating by default.
2. Scene rendering and editing are separate:
   - first render enough world context to trust what the user sees;
   - then add selection/move tools.
3. Visual terrain and collision are separate layers because [[Finding - Visual is not collision]] is confirmed.
4. File coordinates remain the editor's internal authoritative coordinates until a layer documents otherwise.
5. Runtime coordinates are shown as `file << 5` when applicable.
6. Any permanent edit must route through explicit patch/rebuild tooling and produce a report.

## Known Source Layers

| Layer | Source | Current confidence | Editor role |
|-------|--------|--------------------|-------------|
| Pickups / collectibles | `LEVEL.DAT` type-`0x3f` | Confirmed editable | First editable object layer |
| Visible walkable ground | `LEVEL.DAT` payloads / [[Finding - Visible ground from DAT verts]] | Confirmed source, parser still needs editor extraction | Primary scene context |
| Candidate A visual terrain | [[Finding - Candidate A is DAT-backed visual terrain]] | Confirmed editable by experiment | Primary terrain/scenery target |
| Collision floor | `LEVEL.RAW` chunk 32 / [[MEM - Collision sector table 800A7E48]] | Confirmed physical layer | Separate overlay/edit layer |
| Terrain strip / persistent buffer | `LEVEL.RAW` chunk 35 / [[MEM - Terrain vertex buffer 8012C1D0]] | Solved but visually occluded in tests | Preview/debug layer, not sole floor source |
| Planting seeds | `LEVEL.RAW` chunk 31 / [[Seed planting system]] | Solved | Future editable object layer |
| Static overlay spawns | `LEVEL*.BIN` overlays | Partly solved | Future advanced object layer |
| Object/model assets | `*.ALL`, `*.ANM`, `GFX/*.RAW`, level texture data | Partly decoded | Needed for game-like visuals |

## Phase 0 — Renderer Direction Decision

> [!success] DECIDED + DONE (2026-06-20): **moderngl + QOpenGLWidget**. Chosen over QPainter (no real depth/textures, won't scale to a full textured level) and over PyOpenGL (more boilerplate). Decisive factor: moderngl gets a GL context **headlessly**, so the render pipeline is verifiable in CI (`test_scene3d.py`) before it ever hits a display. Minimal scene renders inside the PySide6 app; table/map/inspector still work; the QPainter marker view is retained as the legacy "3D Tools" tab. Exit criteria met.

Goal: choose the rendering architecture before expanding the current placeholder.

Decision points:

1. Keep PySide6 as the desktop shell.
2. Replace the QPainter-projected marker scene with a real 3D renderer.
3. Preferred route: PySide6 + OpenGL widget with a small scene renderer.
4. Candidate dependencies:
   - `PyOpenGL` or `moderngl` for rendering;
   - custom mesh buffers for decoded geometry;
   - Qt widgets for panels/menus/forms.
5. Avoid investing heavily in Qt3D unless it proves maintained and ergonomic enough for this use case.

Exit criteria:

- Renderer library chosen.
- Minimal OpenGL scene renders inside the PySide6 app.
- Existing table/map/inspector still work.
- Marker diagnostic view can be retired or moved behind a debug toggle.

## Phase 1 — Scene Data Inventory and Import

Goal: identify the minimum solved data needed to show a recognizable level scene.

> [!success] Exit criteria MET for LEVEL01 (2026-06-19)
> The importer produces a full LEVEL01 scene graph — **217 classified `fcn.80010000` mesh payloads** (floor/scenery/decor), **≈15.6k heuristic faces**, **placeholder materials**, **70 pickups**, **1 byte-confirmed collision plane** — every element source-traced, and missing bindings recorded as explicit issues. Pickups generalize to all 9 gameplay levels. Locked by `level_editor/test_scene_importer.py` (8/8). Remaining fidelity (face winding, textures, full collision, sky, other-level meshes) is tracked in [[ABL 3D Phase 1 Gap Checklist]] and is largely **DuckStation-gated**, not Phase 1 data-import work. Next: Phase 0/2 renderer to draw this data.

Current implementation slice:

- `level_editor/scene_importer.py` imports confirmed type-`0x3f` pickup placements for all gameplay levels.
- It surveys and imports **every** referenced LEVEL01 `fcn.80010000` payload (not just Candidate A), classified with provenance, via `import_meshes()` (ported from `tools/analyze_g27_floor_candidates.py`).
- It extracts heuristic triangle faces from the command stream and attaches placeholder materials.
- It imports the one byte-confirmed chunk-32 collision plane as a worked-example overlay.
- The importer records unresolved renderer/asset/collision/sky work as structured scene issues.
- The PySide6 app exposes the importer output in the `Scene Import` tab (meshes grouped by classification).
- `level_editor/test_scene_importer.py` regression-locks the LEVEL01 facts + cross-level resilience.
- The missing work remains tracked in [[ABL 3D Phase 1 Gap Checklist]].

Tasks:

1. Build a render-source inventory for LEVEL01:
   - visible floor/scenery from LEVEL.DAT;
   - candidate terrain/scenery meshes;
   - type-`0x3f` pickup coordinates;
   - collision floor/plane records;
   - sky/background color/table;
   - texture/model asset candidates.
2. Create normalized Python data models:
   - `SceneMesh`;
   - `SceneObject`;
   - `CollisionPlane`;
   - `PickupPlacement`;
   - `TextureRef` / placeholder material.
3. Import geometry as untextured or flat-colored meshes first.
4. Keep source provenance on every imported object:
   - file;
   - offset;
   - layer;
   - record index;
   - confidence.
5. Add a scene-load report panel/log.

Exit criteria:

- LEVEL01 produces a scene graph with at least floor/scenery mesh placeholders and pickup placements.
- Each rendered element can be traced back to its source file/offset/layer.
- Missing texture/model bindings are explicit, not hidden.

## Phase 2 — Game-Like Viewer MVP

> [!success] MVP DONE (2026-06-20): the **3D Scene** tab renders LEVEL01 as a navigable space. Free-fly + orbit + pan + zoom + frame-all camera; pick+drag editing wired (Phase 3). Now includes the **decor/foliage layer**: model-space decor placed at DAT record world positions (see [[Finding - DAT record holds decor instance world position]]) — **203 meshes + 348 decor instances + 70 pickups, ~32k tris** (up from a 14k sparse shell). Headless render confirms props sit coherently on the terrain among the collectibles.
>
> **Completeness correction (was over-optimistic):** the *other* candidate for more geometry — LEVEL.RAW **chunk 34 (master mesh) / chunk 35 (terrain)** — was investigated and is **DuckStation-gated, not static**: chunk 35 decodes to tiny **model-space** coords (needs the runtime model→world transform to place; only a narrow strip) and chunk 34 is a **structured model with internal offset tables** (undecoded) also in model space. So the static completeness win came from decor instancing, not those chunks. Remaining Phase 2 polish: sky (blocked), layer-toggle UI (`set_layer` exists). NOT yet textured (Phase 4).

Goal: make the 3D tab look like a level viewer, not a marker chart.

Tasks:

1. Render imported floor/scenery meshes in 3D.
2. Render pickups/objects as simple 3D proxies initially:
   - grain/token/berry/letter/telescope markers can remain stylized until real models are mapped;
   - proxies should sit in the real scene, not on an abstract grid.
3. Add sky/background approximation from known sky color/table data.
4. Add camera controls:
   - orbit selected;
   - pan;
   - zoom;
   - fit all;
   - focus selected;
   - free-roam/fly mode.
5. Add layer toggles:
   - visible scenery;
   - pickups;
   - collision overlay;
   - raw/debug geometry.
6. Keep the current 2D map and inspector synchronized with scene selection.

Exit criteria:

- A user can recognize the level space well enough to understand where pickups sit.
- Camera movement is usable without editing anything.
- Scene layer toggles make visual-vs-collision separation obvious.
- The old marker-only viewport is no longer the primary 3D view.

## Phase 3 — Object Picking and Pickup Editing

Goal: edit known pickup/object placements inside the real scene.

Tasks:

1. Implement ray-based selection against scene objects.
2. Add a move gizmo:
   - X axis;
   - Y axis;
   - Z axis;
   - X/Z plane move.
3. Add snap settings:
   - default snap step;
   - modifier for no-snap.
4. Convert mouse/gizmo movement into the existing edit-plan operations:
   - `move`;
   - `append_clone`;
   - `append_new`.
5. Do not mutate parsed source rows directly; preview operations remain separate until exported.
6. Keep visual ghost previews in the actual scene.

Exit criteria:

- Dragging a pickup in the 3D scene creates or updates a valid edit-plan operation.
- Exported YAML remains compatible with `tools/apply_level_placements.py`.
- Selection stays synchronized with table/map/inspector.

## Phase 4 — Asset Fidelity Pass

Goal: improve the scene from useful geometry to recognizable game content.

Tasks:

1. Map pickup kinds to renderable object proxies or decoded models.
2. Decode/apply texture references where the RE data is sufficient.
3. Add material fallbacks where texture binding is still unknown.
4. Add model/texture provenance to the inspector.
5. Document unsolved asset bindings directly in the scene report.

Exit criteria:

- Common pickups and major scenery read visually as game objects, not generic points.
- Unknown models/textures are visible as placeholders with source labels.
- The renderer remains useful even when fidelity is incomplete.

## Phase 5 — Collision and Floor Editing Prep

Goal: make floor/collision editing possible without conflating visual and physical layers.

Tasks:

1. Render visual floor/scenery and collision as separate overlays.
2. Add collision plane/sector inspection.
3. Add safe preview-only floor/collision adjustment tools:
   - local raise/lower;
   - paired visual/collision candidate edit;
   - before/after comparison.
4. Define dedicated edit-plan schemas for terrain/collision; do not overload pickup YAML.
5. Require tool/report support before writing any patched RAW/DAT output.

Exit criteria:

- User can inspect where visible floor and collision disagree.
- Editing tools are preview-only until the write path is explicit and verified.
- Every floor/collision edit candidate records affected source offsets.

## Phase 6 — Tool Execution Integration

Goal: run the existing patch/build tooling from the app without weakening safety.

Buttons/actions:

- Dry-run edit plan.
- Write patched DAT/RAW to explicit output files.
- Rebuild new BIN/CUE output.
- Open output folder.
- Show command/report output in the app.

Rules:

- Use subprocesses; do not reimplement mature patch/rebuild tools in GUI code.
- Refuse in-place edits.
- Require explicit output paths.
- Keep reports enabled by default.

Exit criteria:

- GUI can dry-run and display a report.
- GUI can produce patched output without touching source files.
- GUI can rebuild a new image through the existing pipeline.

## Phase 7 — Additional Editable Layers

Goal: add solved non-pickup systems once the scene renderer is trustworthy.

Candidate layers:

- Planting seeds from [[Seed planting system]].
- Overlay static spawns from `LEVEL*.BIN`.
- Sky color/table editing.
- HUD FLIK word glyph utility panel.

Rules:

- Each layer needs its own parser, provenance, preview, edit plan, and write-tool path.
- Layers with partial identity knowledge should be marked advanced/experimental.

## Immediate Next Step

Do **not** proceed with old Phase 2 camera controls on the marker-only viewport as the main path.

Next implementation should be:

1. Keep the current marker scene as a debug/temporary view.
2. Build the renderer/data-import foundation for real level scenery.
3. Start with untextured geometry if needed.
4. Only add polished camera controls after the viewport contains actual level context.

## Related

[[ABL Level Editor]] · [[Finding - Visible ground from DAT verts]] · [[Finding - Candidate A is DAT-backed visual terrain]] · [[Finding - Visual is not collision]] · [[MEM - Type-0x3f placement record]] · [[MEM - Collision sector table 800A7E48]] · [[Seed planting system]] · [[Geometry pipeline]]
