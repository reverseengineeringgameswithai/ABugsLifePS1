---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/LEVEL01 Editor Visual-Fidelity Plan.md
aliases:
  - "LEVEL01 Editor Visual-Fidelity Plan"
migration_action: split
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/LEVEL01 Editor Visual-Fidelity Plan.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/LEVEL01_Editor_Visual-Fidelity_Plan.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: LEVEL01 Editor Visual-Fidelity Plan
type: plan
scope: level_editor 3D Scene viewport (appearance only)
status: OPEN — new track, 2026-06-24 (flight-checked 2026-06-24: claims verified vs code + a live mesh-page histogram; V1 root cause corrected, shader/sampling/transparency items added)
goal: the editor's 3D Scene must read 1:1 with in-game LEVEL01
---

# LEVEL01 Editor Visual-Fidelity Plan (make the 3D Scene look like the game)

> ## ⚡ ARCHITECTURE PIVOT (2026-06-24) — the 3D view is now the REAL GAME (emulator-backed)
> Operator feedback (gaps, corrupted tiles, mis-placed pickups, "missing" props, "doesn't look like the
> level") proved the **offline reconstruction can't reach 1:1** without RE-ing the game's entire renderer — a
> quagmire. **Decision: the editor's 3D view is now rendered by an isolated DuckStation** (the real game →
> 1:1 by definition); objects are identified with `gpu.pickObject`; edits apply as live RAM pokes (instant
> in-frame feedback) + the existing disc-rebuild tools. The offline V0–V9 below are **SUPERSEDED for the 3D
> view** (the offline 2D map + data/edit-plan stay useful). New code:
> - `level_editor/live_view.py` — headless engine: launches an isolated DuckStation, loads a LEVEL01 save,
>   navigates (drive Flik / nudge anchor, camera follows), `capture`, `pick`. **Built + validated.**
> - `level_editor/live_editor.py` — Qt window. **v2 (2026-06-24):** continuous ~15fps render loop +
>   **no-clip free-fly** (WASD horiz, R/F vert — Flik re-asserted each tick, camera follows) + fixed
>   click-pick (shows object RAM addr) + P=select nearest pickup / IJKL=move / B=build (proven disc pipeline).
>   **Built; renders real LEVEL01.** Known limit: **no free-look pan** — camera follows motion (free-look needs
>   the camera-update freeze RE, deferred: camera yaw is recomputed each frame, poking it reverts).
>
> **Phases:** P1 live view + navigation + pick **(DONE v1)** → P2 **editing (DONE v1):** `EditSession`
> (`live_view.py`) — select nearest pickup to the anchor (P), move (IJKL, accumulates), build the edited disc
> via the proven `mod/build.py` plan (B); engine validated headless (selects grain #3, emits correct move
> plan); pickups are load-baked so the move shows after rebuild+boot (live poke = preview only). Next:
> P2.5 instant edit for live-movable types (terrain/seeds/enemy anchors); auto-reload the edited disc. Then →
> P3 editing overlay (move/edit selected object
> via live pokes → see it move in-frame; queue disc edits) → P3 true free-cam (decouple from Flik via the
> camera struct `0x1f800374`) + multi-area entry via save states → P4 fold into the main editor as a tab.
> **Limits (honest):** snapshot-style nav (capture per move, not 60 fps); bounded to the streamed area around
> the anchor (far teleport = void/crash) — use save states as entry points; editing is overlay-on-frame.
> The V6/V1 offline texture work (below) is not wasted but is no longer the path to 1:1.


> **Why this exists.** The edit ladder ([[LEVEL01 Level-Edit Punchlist]] steps 1–12) is done and
> **in-game proven** — the editor *writes correct discs* (move/add/delete objects, sculpt terrain, edit
> collision, retarget spawn & exit). But the editor's **3D Scene preview looks nothing like LEVEL01**: a
> dirt-textured soup with grey blobs, floating slivers, and coloured proxy cubes. The whole point of the
> viewport is to **free-cam around the real level and edit objects/terrain/spawn/exit spatially against a
> faithful picture** — and right now it can't, because it doesn't look like the level. This note is the
> dedicated guideline + plan for closing that, tracked separately from the edit ladder.

## North star
Open LEVEL01 in the **3D Scene** tab and free-fly around a view that is **1:1 with the game**: the same
terrain landforms, every surface wearing its **real** texture (dirt/grass/bark/stone/foliage — not dirt
everywhere), props rendered as their **real models** in their real places, Flik present, framed like the
gameplay camera. Then moving an object / sculpting terrain / dragging the spawn or exit is done against a
picture that matches what the player will see.

## Guiding principles (the "guideline")
1. **Appearance only — never touch the write path.** Object/terrain/spawn/exit *functionality* is correct and
   proven; this track must not change a single byte the editor writes. Render ≠ edit. A visual hack that
   corrupts a placement or coordinate is a regression, full stop.
2. **Provenance-first, no fakes.** No invented geometry, no guessed textures painted to "look right." Every
   surface/texture/model must trace to real decoded LEVEL data. A correct-but-ugly render beats a pretty lie.
3. **Ground every fidelity claim against a real game frame.** Use the DuckStation debugger API
   (`gpu.readVramRect`, `gpu.decodeTexture`, `gpu.getCameraTransform`, `gp0Trace`, `captureFrame`) to get
   ground truth, then match the editor to it. Don't eyeball-tune in isolation.
4. **Reuse the API before brute-forcing** (project rule) — the texpage/CLUT/camera answers are in VRAM and the
   GP0 stream, not in a RAM guess.
5. **1:1 is the bar, measured.** "Looks roughly ok" is not the bar (see Acceptance).

## Acceptance criteria (how we know it's 1:1)
Pick N fixed **matched vantages** (e.g. spawn-facing-grain, the slope by sector 119, the exit approach). For
each, set the editor camera to the **same pose** the game uses there (eye/target/FOV from
`gpu.getCameraTransform` at that spot) and compare editor frame vs DuckStation frame:
- **Geometry:** major landforms / silhouette align; no stray/floating/degenerate faces.
- **Texturing:** every surface samples the **correct** page class (dirt = dirt, grass = grass, bark = bark,
  stone = stone, foliage = foliage). No dirt-for-all.
- **Objects:** the level's **prop/plant decor reads recognizably** (berries, plants, flowers, rocks, fences,
  structures — already-imported `fcn.80010000` decor, now textured), pickups render as their real models, Flik
  present — not grey blobs or proxy cubes, and in the right positions.
- **Shading:** vertex colours/lighting read like the flat-lit PS1 look (not over-bright / wrong hue).
- **Camera:** framing matches the gameplay follow-cam.
- **Measured:** a structural frame compare (`emulator.hashFrame`/`diffFrames` or `gpu.diffCurrentFrame`,
  region-scoped) passes a threshold, AND the human test holds: *"from this vantage, an observer matches the
  editor view to the game and identifies every major surface/prop correctly."*
- **Regression:** the matched-vantage set becomes a stored harness so fidelity can't silently rot.

## Current state — what's wrong and why (honest, code-grounded 2026-06-24)
From the operator screenshot (editor 3D Scene) vs the real LEVEL01:
| Defect (visible) | Root cause | Where |
|---|---|---|
| ~~Whole classes of props MISSING~~ **RESOLVED** — props (berry/plants/rock/fence/etc.) **are** already-imported `fcn.80010000` decor; they rendered **grey** (decor untextured), now textured. Only payload 0x2f700 truly missing. | decor texturing fix; G58 (V0) |
| **Everything wears dirt/cobble** (grass, stems, panels) | page IS decoded (`ctrl & 0x1F` → `LEVEL01_VRAM_PAGE_CHUNK`) but **only the mesh's FIRST batch page is used mesh-wide** → measured **124/191 textured meshes collapse to page 0 (dirt)**, 67 to real pages, 0 unmapped | `scene_importer.import_meshes` (`page_n` from `cmd_start` only), `_extract_faces` skips per-batch ctrl, `scene3d.mesh_page`; `match_page` is dead code |
| **Floating white slivers / fish-eye panels** | likely mis-textured thin foliage (page-0 dirt on grass) — may be FIXED BY V1; else degenerate/wrong-winding faces + no backface cull + wide FOV | `scene3d.assemble` face loop; `fcn.80010000` decode; **diagnose before assuming geometry** |
| **Grey blobs** (rocks, mushroom caps) | **26 `decor_prop` meshes are excluded from `TEXTURED_CLASSES`** → no page → flat grey placeholder | `scene3d.TEXTURED_CLASSES`; `scene_importer._placeholder_material` |
| **Coloured cubes** (pink/purple/yellow) | pickups render as **proxy cubes**, not real models | `scene3d._cube` pickup proxies; no model decode |
| **Over-bright / smoothed surfaces** | shader adds a **directional Lambert light the game doesn't have** + textures use **mipmaps/linear filtering** (PS1 = none/nearest) + modulation `tex*(0.5+0.5*color)` ≠ PS1 `tex×color` | `scene3d._FRAG` (`u_light` lambert), `Renderer.set_atlas` (`build_mipmaps`) |
| **No transparency** (grass/leaf/sprite edges opaque) | PS1 semi-transparency / black-as-transparent not implemented | `scene3d` opaque draw |
| **Camera doesn't frame like the game** | editor free-cam FOV/pose not matched to the gameplay cam | `scene3d.Camera`, `scene3d_view` |
| Black sky | background GP0 fill not drawn | (DEPRIORITIZED — operator does not care) |
Geometry *placement* is mostly right already (floor model→world VERIFIED, [[Gap Audit|GAP-0023]]) — to be
re-confirmed whole-scene at the matched vantages; the failure is **surfaces + objects + camera**, not where
things sit.

## Work breakdown
> Status legend: 🔴 open · 🟡 partial · ✅ done. All items are VIEW-ONLY (must not change the write path).
>
> **Execution order:** ~~**V6** (shader)~~ ✅ → ~~**V1 per-face pages** (`0x8000`-inherit + decor)~~ ✅
> **DONE + game-frame-validated 2026-06-24** → ~~**V0** (the "invisible" props)~~ ✅ **investigated — they were
> already-imported decor that rendered grey; fixed by decor texturing** (NOT a missing system; G58). **→ next:
> V_T** (transparency) → **V2** (cull) → **V4** (camera) → **V5** (real pickup/Flik models). Residuals:
> payload 0x2f700 (V0), per-draw CLUT/material (V1-secondary). Sky (V8) skipped.
>
> **Harness:** `level_editor/render_capture.py` renders LEVEL01 offscreen (standalone GL → PNG) at the spawn
> view (or `--eye/--target`, `--frame`) — the basis for the matched-vantage A/B compares.

### V0 — The "invisible" props 🟢 *(INVESTIGATED + mostly RESOLVED 2026-06-24 — NOT a missing geometry system)*
**Corrected finding (two earlier leads RETRACTED — see G58).** The operator's invisible objects (berry cluster,
thorn/leaf plants, flowers, boulder, stake fence, swing, structure) are **`fcn.80010000` meshes the editor
ALREADY IMPORTS** — NOT a new geometry format. Proof: write-watch the berry's render buffer → emitter PC
**0x80010a48 (inside `fcn.80010000`)**; `execTrace fcn.80010000` (`a0`=DAT payload) across all 7 prop frames
drew **58 payloads, 57 of them already in the editor's 217** (only DAT **0x2f700** is genuinely un-imported).
*(The `.VB`/`.VH` "vertex buffer" lead was wrong — those are VAB **audio** banks; and "renders past the DAT"
was just the per-frame GPU scratch buffer, not the source.)*
**Why they looked missing:** they're `decor_prop`, which rendered **flat grey** before today's decor-texturing
fix — a red berry looked like a grey blob. The berry = decor mesh `0x32c1c` @world (-5390,-3542,9839).
- ✅ **Decor texturing (V1-tertiary) — DONE:** props now render textured, not grey.
- 🔴 **Decode payload `0x2f700`** (+ its pass-1 flag-0x14 bridge) so the 1 missing prop imports (small).
- 🟡 **Prop material/colour fidelity** (the berry renders texture×vertex-colour, not the exact bright-red
  in-game material) → folds into V1-secondary (per-draw CLUT/material).
- **Operator action:** **restart the editor** (your session predated decor texturing) + navigate to the props.
- **Accept:** the berry/plants/rock/fence read recognizably at their world spots (matched-vantage vs the saves).
**Priority:** DOWNGRADED — this is ~98% already covered; not a major new track. The real remaining fidelity
levers stay V_T/V2/V4 + the colour/material residual.

### V1 — Per-FACE texture pages 🟢 *(DONE + game-frame-validated 2026-06-24)*
> **DONE.** Per-face page decode, validated against the real `gpu.captureFrame`. The decisive RE finding:
> the batch `ctrl` word's **bit 15 (`0x8000`) means "inherit the current page" (no switch)** — only a
> ctrl WITHOUT it sets the page. So the floor (Candidate A) is **page 0 (dirt) throughout**, matching the
> brown game floor; only **~12** meshes genuinely switch pages mid-stream (those now texture correctly
> per face). **Trap caught + reverted:** a first pass read `&0x1f` on every batch → painted the floor
> with the **blue** page 4 (page 4 is a blue/sky palette). RE:
> `src_re_geometry/geometry_g57_command_stream_texpage.md`; code `_extract_faces` (0x8000-inherit) /
> `scene3d.assemble`; test `test_per_face_texture_pages`. Net: floor + palette now read game-like; the
> big visual win was **V6**, V1 is the correctness layer (right pages, no blue).

**Flight-check correction:** the page binding is NOT a color heuristic and the textures ARE decoded — the
mechanism exists and is ~⅓ correct already. The command stream's batch ctrl word gives the VRAM page
(`page_n = ctrl & 0x1F`, page base X = n·64), mapped to a LEVEL.RAW chunk by `LEVEL01_VRAM_PAGE_CHUNK`
(pages 0–11, VRAM-matched 96–100% once at LEVEL01), then `scene3d.mesh_page` → atlas layer. Per-corner UVs
are already decoded. (`textures.match_page` is **dead code** — ignore/remove; it is not the binding.)
**(Superseded by the `0x8000`-inherit finding — kept for context.)** The earlier framing said "124/191
meshes collapse to page 0 / 174 multi-page." That over-counted: most "multi-page" batches were `0x8000`
*inherit* batches (same page), not switches. With the correct rule only ~12 meshes truly switch pages, and
the floor was always page 0 (dirt). So the original dirt look was mostly the **V6** issues (fake light /
smoothing), not a page-collapse; V1 fixes the genuine page switches + prevents the blue-floor mis-decode.
- ✅ **FIX (primary): per-FACE / per-batch page — DONE + GP0-validated.** `_extract_faces` is a `[ctrl][count]`
  batch parser returning per-face `face_pages`; `scene3d.assemble` uses `face_layers_for(mesh)`. gp0Trace
  confirmed the game draws pages 0-4 matching `ctrl & 0x1F`. (G57.)
- 🟡 **FIX (secondary): per-draw CLUT accuracy — now MINOR.** With the inherit rule the floor + most meshes
  use pages whose existing rips already decode fine, so the dirt-soup is gone. A per-page CLUT swap was
  **tested and reverted** (rendered purple): a page is sampled with **multiple** CLUTs per draw, the CLUT is
  **not** in the DAT command stream (render-time), and the look is `tex × vertex-colour` — so one-CLUT-per-page
  is lossy. A real fix needs the per-draw CLUT source RE'd; only affects the ~12 genuine multi-page meshes.
- ✅ **FIX (tertiary): texture the decor — DONE 2026-06-24.** Added `decor_prop` to `TEXTURED_CLASSES`; the 24
  decor meshes all have decoded UVs+pages (chunks 0/2/4), so the grey mushroom-cap/rock blobs now render
  textured (render-tested: clear win, no blue artifacts). Operator-confirmed editor screenshots look game-like.
- **Accept:** grass≠dirt, bark≠dirt, stone≠dirt; multi-page meshes textured per face ✅; page colours match a
  matched-vantage game frame; decor textured.

### V2 — Cull the garbage geometry 🔴  *(stop it looking broken)*
- Diagnose the floating white slivers & stretched panels: degenerate faces, wrong winding, bad UVs, or
  decode over-read in the `fcn.80010000` command stream. Add **backface culling**; drop degenerate/zero-area
  faces; fix winding so front faces show.
- **Accept:** no floating slivers; surfaces are solid and oriented correctly.

### V3 — Vertex attr / UV role confirmation 🟡
- Confirm the `fcn.80010000` vertex `+0x8` attr role (UV vs packed colour vs normal) so textures map with the
  correct UVs (current UVs are "batches of [4 offsets][4 UVs]" — validate against VRAM).  RE: `execTrace`
  `fcn.80010000` feeding GTE/GPU, or correlate attr vs the GP0 `0x3C` tiles via `gpu.readVramRect`.
- **Accept:** textured surfaces show the right texel mapping (no smear/swim) at a matched vantage.

### V4 — Camera follow-law / FOV 🔴  *(cheap, big readability gain)*
- Read the gameplay camera (`gpu.getCameraTransform` / the camera struct `0x1f800374`) at a few spots; give
  the editor a "match game cam" mode + correct default FOV so free-cam framing reads like gameplay. Also match
  the **4:3 / ~PS1 aspect** for the matched-vantage compare (the editor window is arbitrary aspect).
- **Accept:** a "game cam" preset reproduces the gameplay framing (pose + FOV + aspect) at a matched vantage.

### V5 — Real object models 🔴  *(replace the cubes/blobs)*
- **Pickups:** render the real sprite via the kind→descriptor render path (EXE descriptor table near
  `0x80096b98`; descriptor → VRAM sprite/CLUT) instead of proxy cubes (grain/berry/token/telescope/FLIK letters).
- **Flik + characters/enemies:** decode the character model format ([[Blocker - Character and plant model formats are unreversed|B-char/plant]]) to show Flik, NPCs and enemies.
- **Plants/seeds:** the plantable plants/seeds are a SEPARATE system from pickups (LEVEL.RAW chunk 31; see
  `tools/seed_table.py`) — show their real models (also covered by the character/plant-format blocker).
- **Decor props:** texture the inline decor payloads (shares V1's tertiary fix).
- **Accept:** pickups/Flik/plants/props read as their in-game models at correct positions.

### V_T — Semi-transparency / sprite alpha 🔴  *(cheap; fixes grass/leaf/sprite edges)*
- Foliage (grass blades, leaves) and sprite pickups use PS1 **semi-transparency** (the primitive/texpage
  semi-transparency bit) and **black=transparent** for sprite tiles; the editor draws everything opaque →
  solid blades and opaque sprite boxes. Add alpha-test / blended draw for the flagged surfaces (the
  semi-transparency bit comes free with the V1 `gp0Trace` pass).
- **Accept:** grass/leaf/sprite edges show correct transparency, not opaque slabs.

### V6 — Shading / lighting / sampling match ✅ *(DONE 2026-06-24 — pure editor, no RE)*
- ✅ **Removed the dynamic light.** `scene3d._FRAG` no longer applies the directional Lambert (`u_light`/
  `u_ambient` deleted from shader + `render()`); surfaces use the baked gouraud **vertex colours** directly.
  (Normal attribute dropped from the shader → marked padding in `_VAO_FMT`; still in the buffer for future use.)
- ✅ **Modulation → PS1 rule** `clamp(tex × v_color × 2.0, 0,1)` (0x80 = 1.0×) replacing the `0.5+0.5*v_color`
  floor. *(The ×2.0 is the textbook PS1 modulation; the EXACT per-draw modulation colour is confirmed in V1's
  gp0Trace pass — provisional but clearly more game-like.)*
- ✅ **Nearest sampling, no mipmaps** in `Renderer.set_atlas` (`filter = NEAREST,NEAREST`, dropped
  `build_mipmaps()`) → crisp PS1 texels.
- **Result (offscreen A/B at spawn, `render_capture.py`):** dirt reads warm/sunlit + crisp instead of dark/
  smoothed; flat baked look. 10/10 `test_scene3d.py` GL tests pass. (Restart the editor to see it.)
- **Residual:** exact modulation ×factor → pin in V1; untextured decor caps still grey → V1 tertiary.

### V7 — Rotated decor (M_obj) 🟡
- If any props are rotated in-game, recover `M_obj` (general `world = T_obj + M_obj·v`); LEVEL01 floor is
  translation-only (resolved), decor rotation is still open (§11.4). Only needed if a matched vantage shows a
  mis-oriented prop.

### V8 — Sky (DEPRIORITIZED) ⏸️
- Operator does not care about the black sky. Skip unless it ever blocks a matched-vantage compare.

### V9 — Animation / per-level / draw-distance (LATER)
- Animate movers/enemies in-view; generalise the fidelity beyond LEVEL01. Optionally mimic the game's
  draw-distance/fog (the game culls far geometry; the editor shows everything) if it hurts a matched compare.
  Out of scope until V1–V6 land.

## P2 — live editing + performance (DONE 2026-06-24)
Two findings, both shipped in `level_editor/live_view.py` + `live_editor.py`:

- **type-0x3f pickups are LIVE-MOVABLE (correction of "baked").** A read-watch on a grain's DAT record
  (`DATbase+entry_offset`, X@+0 / Z@+8) shows the per-frame pickup processor (readers `0x80025xxx`, plus
  `0x80053920`) reads it **~3×/frame** → poking X/Z relocates the pickup **on the next rendered frame**
  (proven: a grain placed at Flik's file-XZ rendered as a gold glow at his feet). The earlier "poking the DAT
  does nothing → baked" was a **bad-vantage artifact** (the grain was behind the big berry / off-screen).
  *Caveat:* dragging a pickup onto Flik triggers auto-grab (processor rewrites Y→`0x80000000` = collected) —
  preview-only, a state reload restores it.
- **~20 fps via VRAM readback.** `emulator.captureFrame` (PNG encode + file) = **77 ms/frame**;
  `gpu.readVramRect` over `crtc.vram_source_rect` (512×224, base64 `raw16le` = 1-5-5-5 BGR) = **1.9 ms** +
  ~0.2 ms numpy decode. `advanceFrames(1)` = **29 ms** (the real floor). So advance + VRAM ≈ 31 ms (~30 fps
  ceiling); `FPS_MS=50` gives a steady 20 fps. (`gpu.captureFrameSnapshot` = 0.8 ms but in-memory only, for
  diffing — not retrievable as pixels.) Engine now emits a `QImage` straight from the ndarray (no file I/O).
- **UX:** `EditSession.project/select_at/drag_screen` use a **Flik-relative world(file)→screen(px) affine**,
  calibrated on `big_berry` (heading 3818) by nudging a grain and reading its on-screen gold centroid
  (+400 fileX → screen (+7, −1); +400 fileZ → (+8.1, −5.6); offset taken at Flik's feet ≈ (278,170)px so the
  map tracks the no-clip cam). **Click a pickup to select; DRAG to move it live**; `B` builds the disc (the
  proven `mod/build.py` rebuild). The basis is oblique/ill-conditioned → per-event drag is clamped ±4000 file.
  *Limit:* the calibration is per-heading; non-`big_berry` saves are approximate until re-calibrated.

## Method / harness
1. From a DuckStation LEVEL01 frame at a chosen spot: `gpu.getCameraTransform` (pose), `captureFrame`
   (reference), `gpu.readVramRect`/`decodeTexture` (page truth), `gp0Trace` (per-draw texpage).
2. Set the editor camera to that pose; render; compare (`hashFrame`/`diffFrames`, region-scoped).
3. Iterate a work item until the matched-vantage compare passes; store the vantage in a fidelity harness.
4. Repeat across the N vantages. Keep all of it **read-only against the game**; the isolated instance only.

## Links
- Edit ladder + the §12 line this elevates: [[LEVEL01 Level-Edit Punchlist]] (visual-fidelity track).
- Renderer/import: `level_editor/scene3d.py`, `scene3d_view.py`, `scene_importer.py`, `textures.py`.
- Spatial truth (already solved): [[Gap Audit|GAP-0023]] (floor model→world); auto-memory
  `level-editor-inworld-spawn-plan`.
- Assets/RE: [[Blocker - Character and plant model formats are unreversed]],
  [[Blocker - Offline texture and font extraction is absent]], [[Core - Rendering OT and GPU Packets]];
  pickup render path = EXE descriptor table `0x80096b98` (auto-memory `pickup-render-kind-descriptor-table`).
- API: `ObsidianVault/Indexes/DuckStation API Index.md` (gpu.* / gp0Trace / camera).
