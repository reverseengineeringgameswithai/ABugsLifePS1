---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/ABL Level Editor.md
aliases:
  - "ABL Level Editor"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/ABL Level Editor.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/ABL_Level_Editor.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: ABL Level Editor
type: system
updated: 2026-06-19
status: PySide6 prototype; 3D plan replanned for game-like scene editor
confidence: IMPLEMENTED
tags: [system, tooling, gui, leveleditor, dat, pickup]
---

# ABL Level Editor

> Standalone GUI front-end for the current level-editing workflow. It lives outside the RE source/docs at `level_editor/` and does not mutate DAT/BIN/CUE files.

## Current implementation
- Primary implementation track: `level_editor/pyside_level_editor.py`, launched by `./level_editor/run_pyside_level_editor.sh`.
- PySide6 dependency file: `level_editor/requirements-pyside.txt`.
- PySide6 local venv: `level_editor/.venv` (installed 2026-06-19).
- PySide6 desktop launcher: `level_editor/ABL PySide Level Editor.desktop`.
- Current runnable fallback: `level_editor/AblLevelEditor.java`, launched by `./level_editor/run_level_editor.sh`.
- Desktop launcher: `level_editor/ABL Level Editor.desktop`.
- Runtime model: PySide6 desktop app replacing the Java prototype. The Java app remains as a fallback until the PySide6 dependency is installed.
- Previous browser prototype: `level_editor/index.html` with `level_editor/app.js` and `level_editor/styles.css` remains for reference, but is not the primary app.
- Optional older prototype: `level_editor/abl_level_editor.py` (Tkinter), but local `python3` currently lacks `tkinter`.
- Documentation: `level_editor/README.md`.

## What it edits today
The first version targets the shipped **Pickup/DAT track**:

- Load a `LEVEL*.DAT` file through a desktop file chooser.
- Change levels from a selector populated from `DAT/LEVEL*_LEVEL*.DAT` / `DAT/LEVEL*_LEVEL1.DAT`.
- Parse type-`0x3f` level items in the desktop app.
- Display a top-down X/Z map, item table, and inspector.
- Show a level summary with item counts, coordinate bounds, edit-plan size, and pickup-height cautions.
- Browse solved RE layers from LEVEL.RAW and LEVEL.BIN with source/status/details.
- Add coordinate moves for existing items to an edit plan.
- Add relocation-aware duplicate/new-item specs (`append_clone`, `append_new`) for existing CLI tooling.
- **Delete an existing item** ("Delete Selected from Level"; queues a relocation-aware `delete` op — CC5).
  Risky kinds (FLIK letters, telescope) prompt for confirmation; deletes are exported descending so they
  apply correctly against the original numbering. In-game verified (grains 70→60 booted & parsed).
- **Type a HUD word** ("HUD Word (FLIK)" field + "Build HUD-Word Disc"; §7). Validates a 4-letter word against
  the available glyph art (`mod/glyphs/letters/<L>.png`, currently A F I K L T) and runs
  `tools/build_flik_word_disc.py` (patch LEVEL.RAW/LEVEL1.RAW glyphs → auto-layout rebuild). In-game verified
  ("TAKA" rendered with spin). Separate from the type-0x3f edit plan (it's a LEVEL.RAW texture build).
- **Add a net-new object** (CC6). The add-item dropdown is fed from the **custom-object registry**
  `mod/custom_objects/*.json` (via `tools/custom_objects.py`) — currently **"Blackberry (net-new berry)"**
  (kind 0x25). Queuing one appends a type-0x3f kind-0x25 row (per-op `allow_unknown`) and prefills its default
  position; because the registry marks it `requires_code`, "Build Modded Disc" automatically builds **with**
  code (`mod/patch.asm` caves + render descriptor) instead of data-only. One disc bundles placement + caves +
  descriptor. In-game verified (picked up → equip 0x05, thrown). Add more custom pickups by dropping a registry
  JSON + its caves in `mod/patch.asm`.
- Add items from user-facing choices: grain, FLIK letters, seed-token colors, berry types, telescope / hint device, or a custom type id.
- Jump directly to an item by number.
- Copy selected-item XYZ, or selected-item XYZ plus the current move offset, into the add-item form before adding a new item to the plan.
- Preview planned moves, duplicates, and new items on the map before export.
- Export YAML edit-plan specs intended for `tools/apply_level_placements.py`.
- Show decoded type-`0x3f` pickups in the 3D tab as category-colored markers with grid/axis context.
- Keep 3D marker selection synchronized with the item table, 2D map, and inspector.
- Preview planned moves, duplicates, and new items in 3D as ghost markers and source-to-target lines.
- Prepare later 3D editing with orbit/select/move/place/measure modes, pickup/seed/terrain/collision/spawn layer toggles, and gizmo-prep fields.

The GUI's default is non-mutating (exports operation specs; never edits the pristine disc), **but it now also
has an explicit build action** — see [[LEVEL01 Level-Edit Punchlist#Cross-cutting blockers (affect several elements)|CC1]].
**Build Modded Disc** (File menu + "Build Disc" toolbar button → `_build_disc`) exports the current edit plan
and runs `mod/build.py --no-code --placements <plan> --placements-target files/<LEVELxx>/LEVEL.DAT --force`
asynchronously: apply (`tools/apply_level_placements.py`) → stage into `REBUILD/files` → mkpsxiso →
restore-to-pristine → verify the patched DAT is embedded at its LBA. Output `build/ABL_modded.bin/.cue`; the
pristine `Disney-Pixar A Bug's Life (v1.0).bin/.cue` is never touched. The GUI build is **data-only**
(`--no-code`, type-0x3f); EXE code-caves (spawn) and LEVEL.RAW edits (FLIK-word, collision, seeds) still go
through the CLI. Guarded by `tools/regress_editor_build_path.py`.

## PySide6 migration status
- Implemented: DAT parser, level selector, item table, 2D map, inspector, summary panel, edit-plan list, move/duplicate/new-item actions, visual edit-plan preview, and YAML export.
- Implemented: diagnostic 3D pickup-marker scene, including marker rendering, selection sync, pickup layer toggle behavior, and edit-plan ghost previews.
- Implemented: 3D tools panel. It remains prep work for camera controls and gizmo editing; no scene mutation is wired yet.
- Implemented: `--check` parser mode works without PySide6 installed.
- Implemented: GUI error logging to `level_editor/logs/pyside_level_editor.log`; load/export failure dialogs point to that log for traceback investigation.
- Implemented: Phase 1 scene importer slice in `level_editor/scene_importer.py`; it imports confirmed pickups and LEVEL01 Candidate A vertex data, then reports unresolved scene/asset/collision gaps in the PySide6 `Scene Import` tab.
- Replanned: the real 3D editor target is now a game-like level viewer/editor with scenery, terrain/floor, objects, collision overlays, free camera, and direct 3D editing. The marker scene is not sufficient as the main 3D path. See [[ABL 3D Level Editor Roadmap]].
- Dependency: opening the GUI requires PySide6. This workspace has it installed in `level_editor/.venv`. Recreate with:
  - `python3 -m venv level_editor/.venv`
  - `level_editor/.venv/bin/python -m pip install -r level_editor/requirements-pyside.txt`
  - `./level_editor/run_pyside_level_editor.sh`

## Solved layers shown in the prototype
| Layer | Source | Editor status |
|-------|--------|---------------|
| Pickups / collectibles | `LEVEL.DAT` type-`0x3f` | Editable now via move/add spec queue |
| Planting seeds | `LEVEL.RAW` chunk 31 | Solved; future editable layer |
| Collision floor | `LEVEL.RAW` chunk 32 | Solved; future editable layer |
| Sky color | `LEVEL.RAW` chunk 32 | Solved; future editable layer |
| Visible terrain strip | `LEVEL.RAW` chunk 35 | Solved; future editable layer |
| HUD FLIK word glyphs | `LEVEL01/LEVEL.RAW` + `LEVEL01/LEVEL1.RAW` | Solved; future utility panel |
| Overlay static spawns | `LEVEL*.BIN` overlays, including `LEVEL01/LEVEL.BIN` | Solved; future advanced layer |
| Overlay entity init table | `LEVEL*.BIN` Region A overlays | Documented; inspect only |

## RE facts baked into the UI
- [[MEM - Type-0x3f placement record]] entries are 0x10 bytes: `+0x00` X, `+0x04` Y, `+0x08` Z, `+0x0c` kind.
- Runtime coordinate rule: file coordinate `<< 5`.
- More-negative Y is up.
- Pickup comfort-band caution: final runtime Y more negative than roughly `-21000` is flagged because the vault's type-`0x3f` finding showed unreliable collection around that band.
- Entries 54..57 are real berries; move only X/Y/Z, never repurpose the type id.
- Type id `0x30` is labeled **telescope / hint device** per the vault correction, not checkpoint.
- True append/insert must go through the relocation-aware route from [[Finding - Relocation-aware DAT append]].

## Out of scope for the first scaffold
- Planting seeds are not type-`0x3f` seed tokens. They belong to [[Seed planting system]] and the LEVEL.RAW chunk-31 workflow.
- Visual terrain and collision are separate editor layers because [[Finding - Visual is not collision]] is settled.
- Free-roam 3D editing is planned for the non-prototype editor. The PySide6 app currently has a diagnostic marker scene, but the desired target is a real level scene viewer with scenery/floor/object context before adding polished camera and gizmo work. See [[ABL 3D Level Editor Roadmap]].
- ~~The GUI does not currently launch `tools/apply_level_placements.py`, rebuild images, or boot DuckStation.~~
  **Updated 2026-06-23 (CC1 done):** the GUI now *does* launch `apply_level_placements.py` and rebuild the
  image via `mod/build.py` (Build Modded Disc). It still does **not auto-boot DuckStation** (the success
  dialog tells the operator to boot the disc) — that remains out of scope.

## Next editor milestones
1. Choose and wire the real 3D renderer path for the PySide6 app.
2. Build scene data import for visible floor/scenery, pickup placements, and collision preview sources.
3. Render LEVEL01 as an actual scene with untextured/placeholder geometry first.
4. Add camera controls once real scene context exists.
5. Add ray picking and a move gizmo that produces the existing `move`/`append_clone`/`append_new` edit-plan operations.
6. ~~Add dry-run/build actions that shell out to existing tools while preserving the current non-mutating default.~~ **✅ DONE 2026-06-23 (CC1)** — "Build Modded Disc" shells out to `mod/build.py`; default stays export-only until the operator clicks build.
7. Add seed, collision/floor, and overlay-spawn editing only after their render/import/write paths are explicit.

## Related
[[LEVEL01 Level-Edit Punchlist]] · [[ABL 3D Level Editor Roadmap]] · [[ABL 3D Phase 1 Gap Checklist]] · [[LEVEL.DAT object pipeline]] · [[MEM - Type-0x3f placement record]] · [[Tools Catalog]] · [[Seed planting system]] · [[Geometry pipeline]]
