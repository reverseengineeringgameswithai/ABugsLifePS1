---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Blender-first ABL level editor.md
aliases:
  - "Blender-first ABL level editor"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Blender-first ABL level editor.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Blender-first_ABL_level_editor.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

# Blender-first ABL level editor

**Status:** NEW architecture (2026-06-25). **Import side: WORKING.** Export + terrain/collision: planned.
Supersedes the in-game "live editor as primary editor" approach for *authoring* (the live DuckStation view is
kept, but **demoted to a 1:1 verifier/debugger**, not the editor). See also [[LEVEL01 Editor Visual-Fidelity Plan]]
(the live-editor work) and the auto-memory `editor-visual-fidelity-plan`.

## Why this architecture
Authoring terrain/objects by poking a running game is finicky (sparse vertices, timing, visibility, no
persistence/collision). The proven modding pattern — **SM64 decomp + Fast64** — is the opposite: **author the
whole scene in Blender, an exporter bakes it into the game's data, and the running game is just for
verification.** Fast64 works because SM64 is fully decompiled (every format documented). ABL is the **ROM-era /
Quad64 analogy**: we patch the disc's level files (`LEVEL.DAT` uncompressed, `LEVEL.RAW` compressed chunks) and
rebuild — no decomp — so an exporter is only as good as our format decode. Hence the **staged** plan below:
ship the decoded parts now, grow as RE lands.

## Three layers
1. **Blender = authoring surface.** Real 3D tool: place/move objects, sculpt terrain, organise in collections.
   The Blender scene (or its export text) becomes the **version-controllable level source** (decomp spirit).
2. **Exporter = the hard part = format knowledge.** Turns the Blender scene back into ABL's on-disc structures
   (type-0x3f object table, fcn.80010000 floor payloads, chunk-32 collision) and rebuilds the disc.
3. **DuckStation = verifier/debugger** (NOT editor). Two speeds: **fast** = poke the running isolated instance
   to preview the scene live (objects + terrain heights are live-pokeable); **authoritative** = build the disc
   + boot it. Plus debugger spot-checks (`gpu.pickObject`, RAM reads) that the export landed correctly.

## Pipeline + files (`tools/abl_blender/`)
```
LEVEL.DAT / LEVEL.RAW
   │  extract_level.py   (project venv; reuses level_editor/scene_importer.load_scene)
   ▼
build/level01_scene.json   (meshes: verts+faces+texpage+world-anchor; objects; seeds; exits; collision)
   │  import_to_blender.py   (Blender Python; reads ONLY the JSON — no project deps)
   ▼
build/level01.blend   (ABL_Terrain / ABL_Scenery / ABL_Objects / ABL_Seeds / ABL_Exits collections)
   │  [author in Blender — move/delete/duplicate object Empties]
   │  export_from_blender.py   (scene → object_edits.yaml: move/delete/append_new)   [DONE]
   ▼
build/object_edits.yaml
   │  mod/build.py --no-code --placements object_edits.yaml --placements-target files/LEVEL01/LEVEL.DAT --force
   ▼
build/ABL_modded.cue   →  verify in DuckStation (live-poke preview OR disc boot)
   (one-shot: tools/abl_blender/export_and_build.sh [build/level01.blend])
```
- **Blender install:** flatpak `org.blender.Blender` (5.1.2). One-time: `flatpak override --user
  org.blender.Blender --filesystem=home` (so it can read/write the project). Flatpak can only touch paths under
  home — render/save to `build/`, not the session scratchpad.
- Run import headless: `flatpak run org.blender.Blender --background --python
  tools/abl_blender/import_to_blender.py -- --scene <abs json> --out <abs blend>` (absolute paths).
- `_preview.py` = headless top-down Workbench render for sanity-checking (writes under home only).

## Coordinate mapping (game file-coords ↔ Blender, Z-up)
`bx = X/256 ; by = Z/256 ; bz = −Y/256` (in-game **−Y is up**; scale 1/256 → a ±10k level ≈ ±40 Blender units).
Every imported datablock carries its ABL source as custom props (`abl_type`, `abl_kind`, `abl_index`,
`abl_xyz`, `abl_source_offset`, `abl_anchor`, `abl_origin`, …) so the exporter inverts the mapping EXACTLY.
Mesh world vertex = `anchor (T_obj) + v_local` (floor, GAP-0023) or `instance + v_local` (decor copies).

## Staged roadmap
- **A. Import (DONE 2026-06-25):** LEVEL01 → Blender. Verified faithful (top-down render = recognisable level).
  217 meshes (208 faced), 70 object empties, 32 seeds, exit sector. Objects/seeds = Empties tagged by kind.
- **B. Object export (DONE 2026-06-25):** Blender object Empties → `object_edits.yaml` (move/delete/append_new)
  → `apply_level_placements` (PROVEN) → disc. `export_from_blender.py` diffs each Empty vs its imported
  `abl_xyz`; closest-to-original copy = the original (move), extra copies / unknown-index Empties = adds (handles
  Blender Shift+D duplicates), missing indices = deletes (descending). **Verified:** round-trip identity = 0 ops
  (lossless coords); a move+delete+duplicate edit produced the exact ops and built a valid disc (obj0 X +2000,
  obj1 removed 70→69, grain appended → 70). One-shot: `tools/abl_blender/export_and_build.sh`.
  Caveat: seeds use a separate build path (LEVEL.RAW chunk 31), not in this export yet.
- **C. Terrain height round-trip (DONE 2026-06-25):** sculpt anchor-mesh **heights** in Blender (locked
  topology), `export_terrain_from_blender.py` dumps each anchor payload's vertex Y (game v_local frame, keyed by
  DAT offset) → `terrain_heights.json`; `mod/build.py --terrain-heights` writes them SIZE-PRESERVING into the
  fcn.80010000 payloads (Y@ payload+4+i*0xc+2), applied BEFORE placements so relocations carry them. **Verified:**
  raised one tile +4.0 Blender Z → all 92 of its verts Δ=−1024 (exact), every other payload Δ=0 (no collateral);
  disc built. Textures untouched (only Y). Limits: reshape existing verts only (no new geometry); ANCHOR meshes
  only (instanced decor shares a payload → skipped); **collision NOT updated → sculpted hills are visual until
  Stage D**. Combined object+terrain build: `tools/abl_blender/export_and_build.sh`.
- **D. Collision — walkable terrain (DONE 2026-06-25, coarse v1):** `match_collision.py` maps each sculpted
  floor-vertex height delta to its NEAREST chunk-32 collision sector (by XZ) and shifts that sector's origin-Y
  by the average delta (1:1: terrain file ΔY == collision src ΔY, same sign). `build_blender_disc.py` builds the
  combined disc (LEVEL.DAT terrain+objects + recompressed LEVEL.RAW collision via `build_autolayout_disc.py`).
  RE this turn: Flik's floor Y is committed by the movement integrator (`0x80036cec`) from the collision
  (chunk-32), separate from the visual mesh. **Verified:** a raised tile → 15 sectors shifted by the exact ΔY;
  modded disc boots to LEVEL01 (recompressed collision loads); the patched collision IS in the live runtime
  table — 14 sectors differ by −32768 (=1024<<5). **Runtime sector layout decoded:** origin **X@+0x00, Y@+0x04,
  Z@+0x08** (stride 0x30 @0x800a7e48) — the earlier failed live poke used +0x0c, which is the *source* (chunk-32)
  layout; +0x04 is the *runtime* Y (unblocks a future live-collision preview). Limits: **coarse per-sector flat
  floor** (a smooth hill becomes stepped; true per-slope = plane regen, Stage E+); ANCHOR floor only; the final
  "watch Flik walk the hill" is the operator's boot-test of `build/ABL_modded.cue` (the chunk-32→footing 1:1 is
  already proven). Tools: `match_collision.py`, `edit_collision_sector.py`, `build_autolayout_disc.py`.
  **Boot-test (operator 2026-06-25):** raised floor IS walkable (`On_Elevated.sav` — Flik stands on raised
  collision ✓), but FALL-THROUGH near edges (`WalkUpToDie.sav`). Confirmed Stage D, NOT the Blender build (modded
  DAT diff = only the sculpt tile + leftover Stage-B object edits; visual mesh correct). Causes: (1) nearest-sector
  mapping spuriously raised sectors 1300-2000u from any sculpt vert → **fixed: `match_collision.py --max-dist`
  (default 1000)**; (2) deeper — collision sectors are SPARSE vs the visual mesh (~45/92 sculpt verts had no sector
  within 1000u → left pristine), so per-sector matching is inherently coarse and abrupt raises leave seams Flik
  falls through. Real fix = gentle sculpts + **Stage E per-plane collision generation**. (My Stage-C/D *test* sculpt
  tile @0x1b9f0, world X~2000-6500/Z~14000-18000, is baked into `build/ABL_modded.cue` — that's the raised floor.)
- **E. Per-triangle collision — ARCHITECTURALLY INFEASIBLE (investigated 2026-06-25).** ABL collision is NOT a
  triangle mesh. It is (1) a FLAT per-sector floor (origin-Y, coarse by design — what Flik stands on) plus (2) a
  TINY pool of oriented SWEPT planes (`FUNC_800345CC`) — **only 6 in all of LEVEL01**, sector-linked, manually
  authored, tested every-plane-per-frame. Planes can be walkable ramps (one is, up-dot 0.71), but generating
  dense per-triangle planes faces unknown converter/runtime capacity + per-frame perf + a real dead-end risk,
  and isn't how the engine works — the real game's terrain is per-sector-flat-floor + a few ramp planes.
  **Verdict: don't pursue dense per-triangle collision.** Realistic paths: **(A)** treat per-sector floor
  (Stage D) as the native terrain model + keep sculpts GENTLE/broad (matches the original game's style);
  **(B)** optionally author a FEW ramp planes for specific slopes (bounded RE: decode the sector→plane linkage
  in the 0x4c record + the converter's capacity). Separately, NEW visual geometry / chunk-35 walls write is
  still its own undecoded task.

## Path A — gentle terrain workflow (the native ABL model, DONE 2026-06-25)
ABL's floor is per-sector flat, so the achievable terrain model = **gentle, broad height changes** (the original
game's style), NOT sharp cliffs. `match_collision.py` is now **sector-centric with falloff**: each collision
sector samples sculpt-vertex deltas within `--radius` (default 2500, > sector spacing), distance-weighted, so
interior sectors get the full delta and edge sectors get a partial one → a gentle multi-step ramp instead of a
cliff. It also reports coverage (sculpt verts with no sector within radius = visual-only, no walkable floor).
**Proven:** a smooth dome sculpt → sector deltas grade −433…−23 (gentle, walkable); a flat slab → every sector
full delta (a cliff → fall-through). The lesson is the SCULPT: faithful in, faithful out.
**Workflow:** in Blender, sculpt the `ABL_Terrain` meshes with **Proportional Editing (O)** or **Sculpt-Mode
smooth brushes** for gradual slopes; avoid hard-edged selections/cliffs; keep edits over sector-covered ground
(heed the coverage report). Then `tools/abl_blender/export_and_build.sh` → boot. Per-sector collision follows
gentle terrain acceptably; abrupt terrain will fall-through (engine limit, not a bug).

**Safety report (`path_a_report.py`, run automatically by `build_blender_disc.py`)** — emits, before the build:
sectors changed (+ per-sector ΔY); **max EDIT-INDUCED adjacent step** = `|Δi−Δj|` between adjacent sectors (the
NEW seam = fall-through risk; NOT the absolute floor gap — the pristine level has big intentional cliffs);
coverage gaps (sculpt verts with no collision sector = visual-only); visual/collision mismatch (flat per-sector
floor vs the bumpy visual terrain in it); and a classification **ABL-safe | risky | visual-only** (visual-only
if >25% uncovered; risky if max step >700 file; else safe). Writes `build/path_a_report.json`.

**BOOT-TEST PASSED (2026-06-25).** Curated reproducible gentle dome (`make_test_sculpt.py`, peak 5.0 on tile
@0x1b9f0) → report = **ABL-safe** (max edit step 201 file / 6432 runtime, 0% coverage gaps, one mismatch warning
870 = Flik may sit slightly off the curved peak). Built the ISO + cold-booted in DuckStation (movie → LEVEL01,
Flik spawns on the dome) and drove a ~320-frame patrol: **Y stayed bounded (−20194..−7546), ZERO void frames,
lives unchanged → walkable, no fall-through** (vs the earlier uniform-slab build which fell through). Frame:
`build/dome_walk.png`. Confirms the gentle-terrain workflow + falloff matcher + report classification end-to-end.

## Known gaps / refinements
- **Terrain vs Scenery split is incomplete:** `scene_importer` flags only ~9–10 tiles as proven
  `ground_status`; the live execTrace of `fcn.80010000` finds ~12 floor tiles, and more walkable floor sits in
  ABL_Scenery. Refine the ground classification (or let the user tag meshes) so ABL_Terrain holds the full floor.
- **Textures are placeholder colours** in Blender (per-mesh `SceneMaterial.rgba`); real texpage→Blender-material
  baking is future. Not needed for height authoring (textures are preserved on export since only Y changes).
- **Enemies:** chasers are area-spawned (data-driven, editable per `enemy-chaser-spawn-areas`); could become
  Empties too in a later pass.
