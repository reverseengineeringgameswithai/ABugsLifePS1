---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Tier 3 - Native Terrain Path.md
aliases:
  - "Tier 3 - Native Terrain Path"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Tier 3 - Native Terrain Path.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Tier_3_-_Native_Terrain_Path.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

# Tier 3 — Native Terrain Path (author Blender terrain into `FUNC_80010000`)

**The architecture pivot.** After the bolt-on software-OT renderer hit a *measured* hard ceiling (~700 tris @
30 fps — full analysis in [[Tier 3 - GTE Render Path]]), Tier-3 pivots to authoring custom terrain **into the
game's OWN GTE mesh renderer `FUNC_80010000`**, which already draws native LEVEL01's ~810 textured polys/frame at
30 fps. Instead of our CPU drawing a separate blob, we write Blender geometry into the native mesh payloads the
game already GTE-draws → inherit native speed, density, culling, and registration. This is an **exporter**
problem, not a new renderer. Plan: `~/.claude/plans/steady-stargazing-coral.md`. Auto-memory:
`tier3-native-terrain-pivot`. Supersedes GAP-T3-7's "raise caps" idea (see [[Tier 3 - Custom Level Engine]]).

> **⭐ 2026-07-07 BREAKTHROUGH — read "P51" + "P52" below first.** The entire P18–P50 collision-replacement fault
> chain was ONE bug (the grid-builder scratch windows below arena limit `0x801CC390` poisoning render structures in
> grown layouts), fixed by a 5-word EXE patch (`--p51-scratch-pack`). The full replacement envelope incl. 91+92
> passes unguarded, and `--replace-all-blocks` (P52) authors ALL corridor block sectors from the Blender surface —
> zero retained footprints, cold-boot goal, end-to-end Blender demo. Blender custom levels are no longer gated on
> the constrained P30 route contract for collision.

## Native payload format (the exporter target)

Full RE lives in [[FUNC_80010000]], [[MEM - fcn.80010000 mesh payload]], `src_re_geometry/geometry_g11_payload_format.md`
and `src_re_geometry/geometry_g57_command_stream_texpage.md`. Summary (now **codec-proven byte-exact**, below):

```
u32 vertexCount
Vertex[count]              stride 0x0c: s16 x,y,z ; s16 pad ; u32 attr   (object-local, GTE-transformed at runtime, ±32767)
command stream: repeat until u32 0xFFFFFFFF:
   batch = [u16 ctrl][u16 prim_count] then prim_count x { u16 v0,v1,v2,v3 ; u16 uv0..uv3 }
     v* = vertex BYTE offsets (= idx*0x0c) ; uv = lo:U hi:V (0..255) ; quad (v0,v1,v2,v3) -> 2 tris (v0,v1,v2)+(v0,v2,v3)
```
- `ctrl & 0x1f` = GP0 VRAM texpage; `ctrl & 0x8000` = **inherit** current page (don't switch). CLUT is render-time
  (not in the stream). Capacity ≈ **5461 verts/payload** (u16 byte-offset limit); native uses **~25–200 v/payload**.
- **Placement** = the node array @ DAT `0x45f0` (stride `0x18`: `s32 Tx,Ty,Tz` + marker `0xC0080000` @+0x10 +
  payload file-offset @+0x14). `world = T_obj + v_local`. Read by `tools/floor_source_map.py` `node_anchors()`.
  Native floor = **~30 payloads** (node array) of **482 total**; Candidate A @ DAT `0x188cc` (83 v, T_obj=(-8192,-8192,-8192)).

## M1 — byte-exact codec DONE (2026-07-05)

`tools/native_mesh_codec.py` — a **structured** codec (verts + `Batch`/`RawWord` command-stream tokens, handles
no-terminator payloads) that is the exact inverse of `level_editor/scene_importer.py` `_extract_faces`/`decode_payload`
(which is lossy: it triangulates + tracks page inheritance, so it can't rebuild bytes). **Round-trip
decode→encode→bytes-compare = 217/217 LEVEL01 payloads byte-identical** (all 30 floor payloads exact). This proves
the format is fully understood, so authoring into it is a solved-forward encode, not RE. Node enumeration via
`floor_source_map.node_anchors()`; the height-only ancestor is `tools/sculpt_terrain.py`.

## M2 core — authored geometry renders through the native GTE path PROVEN (2026-07-05)

On the **pristine disc** + native LEVEL01 (`level01_lookingdown_flatground.sav` @ repo root; Candidate A runtime =
DATbase `0x801607f8` + `0x188cc` = **`0x801790c4`**): decoded live Candidate A → byte-exact + matches disc DAT;
edited vertex Y through the codec (size-preserving) → poked back → **the frame changed while the CPU was paused
INSIDE `FUNC_80010000`** (pc `0x80010740`). So the native emitter draws our authored geometry. ⇒ **size-preserving
vertex authoring into native terrain already works** (Blender-height bumps at native density/fps, today).

**GOTCHA — edits can deform ground NOT directly in-view** (operator-confirmed, historic issue): a payload's world
footprint may sit off to the side of the current camera, so a bump looks subtle in-frame even though it rendered.
This is why collapsing Candidate A alone barely changed the centered view — its footprint is elsewhere (NOT a
failure; consistent with the G28 sculpt_terrain visible-deform proof). To demo dramatically, pick the payload
UNDER the camera via `sculpt_terrain.resolve_at_xz` (runtime XZ >> 5 → `floor_source_map.query`).

**GOTCHA — instance instability:** collapsing ~10 payloads in one run RESET the guest (Sony boot logo). Heavy
repeated pokes destabilize the isolated emulator — keep pokes-per-run low, relaunch fresh (CLAUDE.md gotcha).

## Architecture facts (from the 3-agent investigation)

- **No streaming, no LOD.** Terrain is all-loaded-at-level-entry, then per-frame GTE frustum-culled
  (`FUNC_800140A0` / `FUNC_80014360` cone tests); density is *authored*. "Region streaming" is a *refuted* theory
  (0 EXEC hits). Draw driver = `FUNC_800224EC` → builders `FUNC_8001EA6C`/`FUNC_800206E8` → `FUNC_80010000`
  (24×/frame, one per DIRT object at `[0x800a6300]`).
- **A payload is INERT until REGISTERED** — a pass-1/pass-3 source record (relocated `[+0x14]`/`[+0x1c]` pointer)
  must point at it AND it must survive the culler into a survivor list. So **replace existing floor payloads**
  (inherit registration) for the MVP; net-new payloads need node entries + `tools/dat_reloc.py` relocation.
- **Collision is a SEPARATE layer** — LEVEL.RAW **chunk 32** (compressed): flat per-sector floor
  (`tools/edit_collision_sector.py`, 223 recs stride `0x4c`, origin-Y @+0xc, runtime=src<<5) + oriented planes
  (`tools/edit_collision_plane.py`, `0x20` recs). Per-sector flat → smooth hills read as **stepped**; true
  per-slope walkable collision needs a NEW plane-emitter (not built; ref `geometry_g29_collision_source_plan.md`).
  Bridge: `tools/abl_blender/match_collision.py`. Codec: `decode_level_raw.py` / `recompress_level_raw.py`.
- **Two-renderer caveat (watch-item):** the agents conflicted on whether `FUNC_80010000` draws the whole visible
  floor or discrete tiles (a bulk-"dirt" renderer `fcn.800172dc` from decompressed LEVEL.RAW `0x8012c1d0` also
  exists). The project's established finding ([[abl-geometry-g55-state]] memory, G28 sculpt proof) is
  **`FUNC_80010000` = the visible walkable terrain**; the off-view-footprint gotcha explains the ambiguous
  single-payload collapse test. Confirm which payloads own the main walkable expanse when authoring a full level.

## Reuse map

- Decode (exists): `scene_importer.decode_payload`/`_extract_faces`, `tools/abl_blender/extract_level.py`,
  `import_to_blender.py`. Encode (NEW): `tools/native_mesh_codec.py`. Placement/relocation: `dat_reloc.py`,
  `floor_source_map.py`. Authoring conventions to crib: `tools/tier3_blender_export.py`. Collision: §above.

## M2 core CONFIRMED on the operator's LIVE instance (2026-07-05)

Raising all 30 floor payloads ~8000 up made the NEAR pebbly floor VANISH (far backdrop shows through) — seen live
on the operator's own DuckStation via a READ-ONLY debugger-API probe (port 2346; token in `~/.local/share/
duckstation/settings.ini [ExternalDebugger]`; method [[duckstation-live-ram-probe]]). ⇒ **`FUNC_80010000` payloads
ARE the visible walkable floor — pivot target confirmed.** Earlier "no change" tests were two confounds: (1)
off-view payload footprints, (2) capturing frames too eagerly → STALE pre-edit frames. **Methodology fix (adopt
next session):** frame-advance + settle several frames BEFORE capture (capture/flush race); verify by cold-boot +
walking Flik from spawn, not a fixed save state. Visual and collision are independent (long-established) — editing
only the visual leaves original collision intact.

## M3 core — WHOLE-FLOOR custom native terrain WORKS (2026-07-05)

`tools/native_terrain_export.py` — `regenerate_floor(dat, height_fn, n)` replaces ALL ~30 native floor payloads
with n×n grids over each payload's own world footprint, Y sampled from a global `height_fn`, dirt-textured
(`build_grid_payload` reuses the M2b texturing: `DIRT_UV` U[0,63]V[192,255], texpage `0x0060`, per-vertex colour
`0x808080`), placed in each payload's local frame (keeps T_obj → level layout/regions intact). Injected via
`native_dat_inject.inject_many` (append+repoint each), disc via `build_autolayout_disc.py`. **Cold-boot (disc
`build/ABL_native_m3`, n=6, DAT 332→368 KB) renders the ENTIRE floor as rolling custom pebbly-dirt hills at native
density, drawn by native `FUNC_80010000`, no crash.** ⇒ native-density custom terrain authoring is PROVEN. VISUAL
ONLY — collision unchanged (Flik walks the original flat collision until M4).

**M3 DONE — real Blender input validated (2026-07-05):** `tools/abl_blender/export_terrain_heightfield.py`
(Blender headless flatpak; real g2b/b2g conventions) authors a terrain over the floor footprint, builds a REAL
Blender mesh, emits a game-coord heightfield-DELTA JSON. `native_terrain_export.py --heightfield` bilinearly
samples it (added to each payload's base Y). Cold-boot (disc `build/ABL_native_blender`) renders the distinctive
Blender shape (central dome + diagonal ridge) via native `FUNC_80010000` — ridge clearly visible, distinct from
the demo hills. **Blender→native path complete.** FLATPAK GOTCHA: ABSOLUTE paths for the Blender script + --out.
Later refinement: full-mesh (arbitrary-topology) Blender export vs the heightfield. M4 collision is next.

## M2b — resize/relocation VALIDATED IN-GAME (2026-07-05)

Cold-boot of a reflow disc with an appended RESIZED payload works end-to-end. Grew the SPAWN floor tile
(payload `0x1b9f0`, covers spawn node XZ 6159,15403) 92→169 v via `native_dat_inject.inject_append` →
`build/terrain_resize.DAT` → `tools/build_autolayout_disc.py` (mkpsxiso reflow, LEVEL.DAT@LBA2906) → cold-boot
(movie `flik_to_level01_stall`, gameplay ~frame 4265). CONFIRMED: loads clean (no RAM clobber), reloc site
resolved (`[DATB+0x4904]=DATB+0x51418`), payload RESIDENT (169 v @DATB+0x51418), and DRAWN by native
`FUNC_80010000` as proper pebbly dirt with authored bumps (disc `build/ABL_native_resize`).

**TEXTURING SOLVED (essential for M3):** native tris = **texture × per-vertex GOURAUD COLOR** = the `Vertex.attr`
@+0x8 field (24-bit RGB; dirt ~0x606870). `attr=0` → BLACK; use `0x808080` (neutral = full-bright texture) or a
shade colour. The dirt tile = UV `U[0,63] V[192,255]` on texpage `0x0060` (page 0) — planar UVs sample a black
texel region. ⇒ `attr` is per-vertex colour, no longer "unknown".

## M2b — resize/relocation pipeline BUILT + Python-validated (2026-07-05)

`tools/native_dat_inject.py` — injects a payload BIGGER than its native slot (for arbitrary Blender topology).
**APPEND at EOF + repoint the payload's relocation-site value** (P1.B `[s0+0x14]`, from `dat_reloc.scan_sites`).
At load the parser relocates it (`+= DATbase`) and the render survivor list — built AT LOAD — picks up the resized
payload; no shifting, no re-relocating the other 1,248 sites, no new relocation sites (command-stream vertex refs
are relative byte-offsets). **Self-test:** grew Candidate A 83→166 v (1964→2960 B), appended, repointed — only the
3 pointer bytes changed, rest byte-identical, appended payload decodes. KEY LESSON: a *runtime* RAM repoint does
NOT work (survivor list cached at level load) — the repoint MUST be in the DAT bytes before load (disc build /
`cd.overlayFile`).

## Roadmap — PIVOT COMPLETE end-to-end (2026-07-05)

- **M1 DONE** — byte-exact codec (`tools/native_mesh_codec.py`, 217/217).
- **M2 DONE** — authored + RESIZED payload renders via native `FUNC_80010000` (cold-boot; `tools/native_dat_inject.py`
  append+repoint; texturing solved).
- **M3 DONE** — Blender→native: `tools/abl_blender/export_terrain_heightfield.py` (real Blender mesh + g2b/b2g) →
  `tools/native_terrain_export.py --heightfield` regenerates all 30 floor payloads → native GTE render.
- **M4 — collision, "move both together"** (2026-07-05): traversal test found visual+collision (SEPARATE systems)
  diverged (~16-28k, Flik stuck) because they used different bases. FIX: drive BOTH by `original+delta` —
  `tools/native_terrain_export.py --displace` (size-preserving Y+=delta, matches collision's delta-shift EXACTLY).
  Disc `build/ABL_native_m4b`: Flik now stands ON the surface. RESIDUAL = **per-sector-flat STEPPING** (step-walls
  block Flik; terraced look) — the fundamental per-sector limit. Collision can only be delta-SHIFTED (SETTING
  absolute origin-Y broke sectors). **The exact fix = the per-face PLANE-EMITTER (next):** emit chunk-32 `0x20`-byte
  planes (normal+ref, resolved by `FUNC_800345CC` against a per-frame candidate list) from the SAME terrain mesh.
  **RE GAP CLOSED (2026-07-05, `src_re/collision_source_converter_80030f60.c`):** decoded converter `FUNC_80030F60`
  — planes live inside per-sector collision-mesh BLOCKS (verts+polys+planes+`0x12345678` relocation), referenced by
  runtime sector `+0x10`; candidate list `0x8009c230` rebuilt per-frame by AABB-select. **The emitter is a full
  block-synthesis, not a plane append — substantial;** remaining decode = block header counts + `ext[5]` poly-extent
  / point-in-face use. **PRAGMATIC:** per-sector-flat floor (`--displace`) is adequate for GENTLE terrain (223
  sectors = fine granularity); reserve the full emitter for steep slopes/walls.

**Remaining refinements:** full terrain walkthrough (across the dome/ridge); true smooth-slope collision
(plane-emitter, `geometry_g29_collision_source_plan.md`); full-mesh arbitrary-topology Blender export (vs
heightfield); reclaim dead payload space (currently append-only). **API tools to use going forward:**
`setTurbo` before `advanceFrames`, `gpu.frameSnapshot`/`diffCurrentFrame` (race-free), `gpu.pickObject`,
`bootSystem{force:true}` (per operator reminder — I'd been underusing these).

## P43 Track-B stable pattern pack (2026-07-06)

P43 packages four constrained Track-B collision-island examples on top of the P30/P31/P36/P42 workflow:
`gentle_plateaus`, `s_elevation`, `soft_ridge`, and `boundary_probe`. All four pass P31 preflight and P30 cold-boot
marker/goal validation with `RENDER_C=0`, native `FUNC_80010000>0`, no plunge, and sink-outside `7/7`.

Designer takeaway: the reliable space is still a bounded heightfield route close to the proven movie corridor.
Mild plateaus, shallow S-turns, and broad ridge texture are stable when marker/goal placement stays aligned. This is
not arbitrary topology, walls, caves, stacked floors, free-roam, object collision, retile, broad replacement,
chunk-35, or `0x604` cleanup. P43 templates are examples only; P11 remains the frozen baseline and P30 remains the
practical authoring baseline.

The bolt-on `mod/caves/tier3_otrender.c` is **frozen** (see [[Tier 3 - GTE Render Path]]), not extended.
Diagnostic artifact: `level01_NATIVE_FLOOR_BUMPED.sav` (repo root) = all-30-floor-payloads-raised state (pristine disc).

## P44 Track-B pattern router (2026-07-07)

P44 adds `tools/g3_native_pattern_router.py` and `docs/G3_NATIVE_P44_PATTERN_ROUTER.md` so designers choose by intent
first, then validate. It routes conservative edits to P30, wide-island edits to P36, mild elevation to P42 retune A,
plateau/S-turn/ridge references to P43 patterns, `boundary_probe` to probe-only, and P33/P39 misses to diagnostic
study. It preserves P43 cold-boot evidence and the dedicated-harness caveat; no engine behavior, defaults, walls,
free-roam, retile, broad replacement, chunk-35, or `0x604` claims changed.

## P45 Track-B stress matrix (2026-07-07)

P45 adds `tools/g3_native_stress_matrix.py` and `docs/G3_NATIVE_P45_STRESS_MATRIX.md` to measure edit envelopes after
P44 template routing. It generates evidence-only probes under `build/g3_native_p45_stress_templates/` for tighter
triggers, wider route offsets, and larger height/ridge amplitudes, then classifies them as green/yellow/stress-limit
or reject based on preflight and cold-boot evidence. It does not create new start templates and does not change engine
behavior, defaults, walls, free-roam, retile, broad replacement, chunk-35, or `0x604` claims.

## P46 Track-B collision frontier (2026-07-07)

P46 preserves P44 and turns the older P17 route-replacement proof into a repeatable collision-frontier runner:
`tools/g3_native_collision_frontier.py`. The proved replacement seed is the five route-used block sectors
`[93, 99, 100, 107, 108]`, built from the same platform-ramp fixture with no sink-outside, no retile, and no P24
guard.

Cold-boot evidence in `build/g3_native_p46_collision_frontier_report.json` is pass: marker frame `4410`, goal frame
`4490`, `RENDER_C=0`, `FUNC_80010000=673`, no plunge, `replaced_authored_block=5`, control targets replaced
`[93, 99, 100, 107, 108]`, retained route blocks `[]`, and route responses only from `replaced_authored_block`
sectors `[99, 100]`.

P46 remains opt-in collision evidence. It does not promote replacement sectors to P30/P43 defaults and does not claim
full authored collision, walls, objects, free-roam, retile, sink-outside, chunk-35, or `0x604` cleanup.

## P47 Track-B replacement envelope (2026-07-07)

P47 preserves P46 and expands the same cold-boot fixture to the validated prefix07 replacement envelope:
`[0, 73, 87, 88, 89, 90, 91, 93, 99, 100, 107, 108]`. Sector `92` remains excluded because the known
`0,73,92` interaction is the stale render/cull workspace fault diagnosed in P20-P24; guarded sector-92 re-entry is a
separate future milestone, not part of P47.

Evidence in `build/g3_native_p47_replacement_envelope_report.json` is pass: marker frame `4410`, goal frame `4490`,
`RENDER_C=0`, `FUNC_80010000=500`, no plunge, `replaced_authored_block=12`, flattened old-footprint blocks reduced
to `74`, retained route blocks `[]`, and active route response statuses only `{'replaced_authored_block': 6}`.
`build/g3_native_p47_p46_preservation_manifest.json` records P46 preserved with
`build/p46_collision_frontier.patch` SHA-256 `c4b30b1503c6cbc1e644d836d4b4f83426880c80a09a9f341f70e630dc0f1f59`.

P47 is still opt-in frontier evidence, not a designer default. P30 remains the practical authoring baseline and P43
remains examples. During validation, P11 and P30 cold-boot checks should be run sequentially because both stage shared
disc files; parallel runs can collide on `SCUS_942.88`.

## P48 guarded sector-92 re-entry (2026-07-07)

P48 is the next collision-frontier milestone after P47. It preserves the P47 prefix07 envelope, installs the opt-in
P24 stale-render guard, and tests sector `92` only in that guarded context. The guarded P47 control passes with skip
counter `0`; the P47+92 probe is rejected because Flik stalls at spawn before the P24 key-65 guard runs.

Control acceptance remains cold-boot marker/goal, `RENDER_C=0`, `FUNC_80010000>0`, no plunge, no retained route
blocks, and strict route-response mapping through built RAW plane pointers rather than candidate-list fallback. The
probe evidence shows `replaced_authored_block=13`, marker reached, no plunge, `FUNC_80010000=0`, no goal, P24 skip
counter `0`, and zero player-floor liveness counts, so sector `92` remains outside the usable envelope even with the
P24 guard.

P48 does not claim guarded or unguarded sector `92`, does not promote the P24 guard or replacement sectors to defaults,
and does not claim broad replacement, full authored collision, walls, objects, free-roam, retile, sink-outside,
chunk-35, or `0x604` cleanup.

## P49 render-driver active-record provenance (2026-07-07)

P49 preserves P48 and ties the guarded P47+92 stall back to the P27 render-driver helper trace. The P48 full probe
matches the P27 full replacement frontier `[0,73,87,88,89,90,91,92,93,99,100,107,108]`; the nearest pass is the
same set minus sector `91`.

Evidence in `build/g3_native_p49_render_driver_record_report.json` is pass: the failing full set reaches
`0x800224ec`, calls `0x8003efc8`, never returns to `0x80022608`, never reaches `0x8002262c`, `0x8001ea6c`, or
`FUNC_80010000`, and hits the `0x8003f290/298/2a0/2bc` loop caps. The nearest pass returns to dispatch and reaches
`FUNC_80010000`. The active-record divergence is preserved: pointer at `0x8003efe4` is fail `0x801c561c` vs pass
`0x801c411c`; span at `0x8003eff4` is fail `0xfff94040` vs pass `0x0000000f`.

P49 is a collision-frontier diagnostic, not a fix. It does not claim the writer/source of the bad active record, does
not admit sector `92`, and does not promote the P24 guard, replacement sectors, retile, sink-outside, broad
replacement, walls, objects, free-roam, chunk-35 cleanup, or `0x604` cleanup.

## P50 guarded sector-92 swap envelope (2026-07-07)

P50 preserves P49, then proves one new collision capability beyond P30/P43/P49: sector `92` can be admitted in a
guarded swap envelope only when sector `91` is omitted. The full set
`[0,73,87,88,89,90,91,92,93,99,100,107,108]` remains a negative control: cold boot reaches marker frame `4410` but
not goal, with `RENDER_C=0`, `FUNC_80010000=0`, P24 skip counter `0`, and no plunge.

The accepted swap envelope is `[0,73,87,88,89,90,92,93,99,100,107,108]`. Evidence in
`build/g3_native_p50_workspace_envelope_report.json` is pass: marker frame `4410`, goal frame `4490`, `RENDER_C=0`,
`FUNC_80010000=413`, P24 skip counter exactly `1`, no plunge, sector `92` included, sector `91` excluded,
`replaced_authored_block=12`, and retained route blocks `[]`. This is a guarded capability, not an unguarded/no-skip
sector-92 pass.

P50 keeps the workspace provenance boundary: P23 explains the older key-65 payload-holder slot, P49 preserves the
active-record divergence, and the active-record writer/source remains unresolved. Do not promote sector `92`, the P24
guard, replacement sectors, retile, sink-outside, broad replacement, walls, objects, free-roam, chunk-35 cleanup, or
`0x604` cleanup to defaults from this milestone.

## ⭐ P51 — grid-builder scratch-window pack: the P18–P50 ROOT FIX (2026-07-07)

**The entire P18–P50 replacement-layout fault chain was ONE bug, now identified and fixed.** The load-time collision
grid/list builder `FUNC_800313A8` (called from the load finalizer `0x8003D5A4`, AFTER render nodes are built) carves
five per-sector scratch arrays at fixed offsets below the **arena-limit global `[0x80082238]`** — a hard-coded
constant **`0x801CC390`** written only at `0x8003C2F4`. Pristine scratch window = `[limit-0x9000, limit)` at `0x2000`
spacing; pristine levels end below it. A grown chunk-32 pushes live render nodes/records INTO the window, and the
builder's bounds writes poison them: the P20 key-65 bus error (`0x801C362C := 0xFFFABFA0`, maxZ stripe), the P27/P49
helper-loop span (`0x801C561C := 0xFFF94040`, minZ stripe), and every "combination-dependent" P18/P25/P26 pass/fail
set (which structure lands in a written stripe). The game's own overflow check (`0x8003D5D8`, error flag `gp+0x754`)
guards the LIMIT only, not the windows.

**Fix:** pack the five window offsets `0x2000 → 0x800` spacing (floor `limit-0x9000 → limit-0x2800`, +26 KB safe
headroom, 512 sectors/array vs LEVEL01's 223) — a **5-word EXE patch**, `build_g3_native.py --p51-scratch-pack`
(`apply_p51_scratch_window_pack`, strict original-word verification). `0x1000` spacing is NOT enough (13-sector
envelope's record top crosses `limit-0x5000`); `0x800` clears every validated layout. First proven by RAM hot-patch
at frame ~1080 on the failing P50 disc, then baked.

**Validated (cold boot, no P24 guard):** the full 13-sector envelope `[0,73,87,88,89,90,91,92,93,99,100,107,108]` —
the P48/P49/P50 "blocked before native GTE" impossibility — **PASSES** (exact spawn, marker f4410, goal f4490,
`RENDER_C=0`, `FUNC_80010000=673`, no plunge; disc `build/ABL_g3native_p51_full_envelope`). Minimal-fail `[0,73,92]`
+seed also passes. 2×2 matrix closed: neither=fail (P19), guard-only=fail (P48), **pack-only=PASS**. The P24 guard,
sector-92 exclusion, and P50 guarded-swap envelope are **obsolete as constraints**. P11 baseline without the flag is
byte-identical (staged EXE sha `185861a9…`). RE: `src_re/collision_grid_builder_800313a8.c`;
doc `docs/G3_NATIVE_P51_SCRATCH_WINDOW_PACK.md`.

## ⭐ P52 — FULL AUTHORED COLLISION WORLD + Blender demo (2026-07-07)

P51's headroom unlocks authoring the whole corridor collision from the Blender surface:
`build_g3_native.py --planes --corridor --replace-all-blocks --replace-tile-n 8 --p51-scratch-pack` replaces **all 86
selected block sectors** with fresh authored mesh blocks on top of the 85 authored flat-sector add-blocks →
**171/189 chunk-32 sectors fully authored, `flattened_old_block_retained_footprints = 0`** — the P15
`not_a_clean_authored_collision_world` verdict closes. At `tile_n=8` the world chunk-32 decompresses SMALLER than
pristine (`0x386F0` vs `0x39D90`) — strictly safe layout (`tile_n=16` balloons +522 KB; don't).

**Runtime proof:** cold boot, Flik spawns exactly, walks the authored world, marker + **goal fire** (~f4470); render
live mid-walk (`build/p52_world_walk_*.png`). **End-to-end Blender demo on a fresh scene** (new heightfield rise 384,
moved marker/goal, material `0x7a5c8c`): scene gate → full-world build → cold-boot goal = PASS
(`build/ABL_g3native_p52_demo`). Coverage: `build/g3_native_p52_full_world_collision_coverage.json`.

**⚠ Validation-methodology caveat:** world-scale discs are instrumentation-timing sensitive — arming `execTrace`
watches near load/spawn (as `validate_g3_native_movie.py` does) can trip the P26/P27 render-driver record race on the
SAME byte-identical `.bin` that completes goal under a lightweight flag-probe driver (verified both ways,
reproducible). Rule: validate `--replace-all-blocks` discs with captureFrame liveness + runtime flag probes; arm
`execTrace` only on envelope-class (≤13-sector) discs. The uninstrumented game is unaffected. Boundaries: corridor
scope; 11 malformed sectors `178..188` + 7 outside-region keep old collision; walls/arbitrary topology still open;
chunk-34/35 visuals parked; lane is opt-in, P11/P30 defaults untouched.
Doc `docs/G3_NATIVE_P52_FULL_AUTHORED_COLLISION_WORLD.md`.

## P54 — invisible-terrain root cause + original-level visual cleanup (2026-07-07)

Operator ran bigland and reported (1) no visible terrain along the collision and (2) original-LEVEL01 artifacts.
Both root-caused; two new menu-safe levers landed. Doc `docs/G3_NATIVE_P54_VISUAL_WORLD_CLEANUP.md`.

**(1) Authoring SCALE.** The visual pipeline was byte-correct (every DAT vertex exactly `base+dy/32`, max err 1.0
file) — but bigland's relief (`dy=[-1219,728]` ≈ 60 file units) was ~20× too small vs game scale (**Flik = ~3200
runtime tall**; original floor spans ~110k runtime). `g3_native_p53_bigland_scene.py --relief-scale 12` →
`dy=[-14667,8304]`, terrain clearly visible. **Designer rule: author heights in multiples of Flik (3200 runtime).**

**(2) ⚠ DOCTRINE CORRECTION — the visible ground is TWO renderers.** pickObject census + live A/B neuters prove:
the f13 finding ("chunk-35/`FUNC_800172DC` fully occluded; visible floor = payloads") holds **only for pristine
geometry** — the payload floor exactly covers the chunk-35 mass. An authored world MOVES the payload floor,
exposing the original-shaped chunk-35 ground mass = most of the "original level" look (plus the 0x68D panorama
band incl. painted berries, and the baked fixture models). Census: panorama = GP0(65) `0x68D`/CLUT `0x3470`;
bulk ground = `FUNC_800172DC` ← buffer `0x8012C1D0` (chunk 35); authored floor = GP0(3C) `0x660`; fixtures
(twig/tree/branches/grass/mushroom/leaf) = GP0(2C/2D) atlas `0x60A` CLUTs `0x3672/74/76`, packet pool
`0x801e28xx` — a separate model pass. `FUNC_80014B04` stub re-confirmed Flik-shared (bits of Flik vanish).

**New levers (both cold-boot baked, menu-safe):** `--blank-backdrop` = fill the chunk-29 panorama image with its
own sky index (pixels only — the palette's 0x300 region holds non-color bytes; `backdrop_edit` rules);
`--suppress-bulk-mesh` = the P11 cave (DAT-marker-gated) one-shot zeroes chunk-35 buffer `0x8012C1D0..0x8012E784`
at level init — level-local RAM, sidesteps the chunk-35 structural-edit load wedge, live-proven stable 240+ frames
(Flik/enemies/HUD use other buffers in gameplay). Result: flat sky + no original ground + authored relief visible
(`build/p54_clean_spawn.png`/`p54_clean_walk.png`).

**Remaining (next milestones):** (a) **authored floor VISUAL coverage** — payloads tile only the original floor
footprints; with bulk suppressed, off-footprint ground reads as void over solid collision → upgrade the M3
`regenerate_floor` lane with expanded/tiled footprints so the authored visual owns the whole playfield (this is
the true fix for "terrain along the collision"); (b) the baked fixture model pass (find its chunk-34 arena
directory; not in chunk-35 tail `0x8012E784..0x80131000`); (c) thin strip remnants at the old panorama height.

## P54b — terrain over the collision + surgical scenery removal (2026-07-07, operator-corrected)

Operator corrections to P54: keep the backdrop horizon; remove the in-level terrain masses (`terrain.png`) but not
Dot/characters; and the authored terrain still wasn't visible over the collision. All three landed
(doc `docs/G3_NATIVE_P54B_AUTHORED_WORLD_VISUALS.md`; verified `build/p54b_*.png`):

- **⭐ `--regen-visual N` — the authored floor now COVERS the whole play box.** `native_terrain_export.
  regenerate_floor_tiled`: disjoint one-rect-per-payload tiling of the play box, N×N grid each, greedy
  nearest-rect matching, **in-place injection when the new payload fits the old slot** (26/30 at n=6, +4.7 KB DAT).
  ⚠ Append-everything at n=8 grew +60 KB and wedged the LOAD (arena-limit class) — keep DAT growth small.
  Verified: ground under Flik at spawn/mid/16k-unit NW roam, no falls.
- **Census corrected:** the pebbly "ridge" masses = a **second panorama image** (128×128 @ RAW full+`0x39550`;
  LEVEL01 has ≥2 zone panoramas) → new `--blank-far-terrain` blanks only it, the 128×96 grass horizon stays. The
  tree trunk/branch/grass cluster = **pass-3 baked fixtures with rotation-only cull — parked anchors do NOT
  suppress them**; the working lever is clearing the pass-3 enable bitmap (`0x800902B6..C7`), baked into the P11
  cave (level-gated RAM, menu-safe; tree vanishes, Flik/Dot/enemies intact). Wall/cliff bands = the 12 non-floor
  node payloads → `--park-nonfloor-nodes`. Negative results recorded: emitter/dispatcher stubs, chunk-34 zero
  (breaks Flik), chunk-35 tail, `[gp+0x404]`=0 — none remove the tree class.
- Residual polish: mushroom-class small props; regen-tile texture fidelity; one rotation-only prop corner.

## P55 — aligned uneven pebble terrain + the parking regression (2026-07-07)

**Uneven ground = SOLVED + quantified:** walking Flik from the field up the 12k ridge, |feet − authored surface|
median **105 runtime units (~3% of Flik)**, 50–142 through the whole climb — visual/collision align by shared-source
construction; flat is just the degenerate case. Pebble material = `DIRT_UV`+texpage `0x0060`+**neutral `0x808080`**
(scene tints wash it out; generator now defaults neutral; VRAM decode `build/p55_dirt_3ff3.png` confirms art).
`--coverage-margin 2000` closed the near-NW collision seam (one far-NW seam remains at file ~(-2250,18450)).

**⚠ REGRESSION found+fixed: `--park-nonfloor-nodes` silently killed ALL native floor rendering** (grid pickObject
census: zero 0x660 quads in every P54b regen build; collision was fine, masking it). Bisect: parking EITHER the 12
wall node T_objs OR their pass-1 records breaks the floor chain (suspected culler s32-overflow/chain truncation) —
flag shelved (env bisects `P54_PARK_NODES_ONLY`/`P54_PARK_RECORDS_ONLY`/`P54_REGEN_M3` kept for study); tree/fixture
removal decoupled to **`--suppress-pass3-bitmap`** (proven safe). Also fixed: `regenerate_floor_tiled` re-anchors
node T_obj + registering record to each rect center BEFORE injection (anchors at original footprints CULL the
relocated geometry; must use pre-inject offsets). Canonical command + designer rules:
`docs/G3_NATIVE_P55_ALIGNED_PEBBLE_TERRAIN.md`. Remaining: GP0(60) ground-fill band stomp (static packets — the
midfield cover), far-NW seam, first-12-node chain root-cause.

## P55b — near-field pebble investigation (2026-07-07, operator follow-up)

Three fixes + one precise gap (`docs/G3_NATIVE_P55_ALIGNED_PEBBLE_TERRAIN.md` addendum):
**(1) Frame bug:** node-registrant pass-1 records are **FILE-frame** (±10k, extents = payload-bbox scale) — the P55
re-anchor wrote `<<5` values → nearly all regen payloads CULLED (the operator's missing floor). Fixed (+ extents =
rect half-diagonal); `P54_NO_REANCHOR=1` = the empirically safest mode today. **(2) Node-registrant structures are
chain-critical:** ANY modification (node T_obj, record XYZ/extent in any frame, even in-place vertex collapse of a
wall payload) breaks the unified mesh chain → ~60 garbage GP0(60) sprites = the "smooth ground" that masked
everything. Walls/cliffs therefore stay visible for now (= the "old terrain" behind the camera, east of spawn).
**(3) Fill bands rebuild PER ZONE** → `--stomp-fill-bands` = P11-cave periodic sweep (every 8th gated frame,
counter `0x8007F314`, scan `0x801D0000..0x801E9000`, y<400 only; bottom fills = engine near-clip cover, kept).
Result: authored relief renders TEXTURED mid-field (`build/p55b_walk_crop.png`). **REMAINING GAP (the real one):**
the closest quad row can't draw (PS1 1023px primitive limit; density budget capped at n≈9-10, n=12 = +126KB DAT =
arena wedge/black-screen) — the original game covers exactly this with the fine chunk-35 near-mesh. Next milestone:
**author the near-field INTO the chunk-35 buffer 0x8012C1D0** (0x30-stride quad format decoded) from the Blender
surface, reusing the engine's own near-field renderer instead of zeroing it.

## P56 — walls absorbed into the floor; near-field constraint decoded (2026-07-07)

**Walls/artifacts SOLVED via payload replacement** (the one safe edit class): `regenerate_floor_tiled` tiles ALL 42
node payloads (`node_anchors(pay_lo=0x8000)`) — the 12 wall/cliff payloads become floor tiles (5×9 rects, ~560-file
quads, n=8, +30KB DAT). The ~60-garbage-GP0(60) mystery = the WALLS' OWN quads re-projecting degenerately when
parked/collapsed (rebuilt per frame — not chain corruption); replacement avoids it entirely. East view verified:
dark wall masses gone; the "floating orange block" = a BERRY PICKUP (gameplay, not an artifact); cliff band = the
kept horizon backdrop. Alignment re-verified: median 104 runtime units up the whole ridge.
**Hard ceilings measured:** DATbase+DAT < P51 window bottom `0x801C9B90` → max DAT +72KB (n=10/+86KB and n=12/+126KB
wedge the load, init never fires). **Chunk-35 decoded one level deeper:** it is a MODEL ARENA of local-coordinate
meshes placed by instances (live decode: buffer head = a ~50-unit gray pebble-prop model) — the original near-field
ground = many instanced ground-chunk meshes. Near-field authoring = the instance/transform-list RE (next milestone);
until then the nearest band renders as the engine's flat near-clip cover.

## ⭐ P57 — PRISTINE PEBBLE GROUND ON CUSTOM COLLISION: SOLVED (2026-07-07)

**Flik walks on pristine-style pebble terrain driven by the Blender surface** (`build/p57_ship_*.png`; 4/4 ground
picks = 0x660 floor quads; zero falls). Three keys, each experiment-proven: **(1) style transplant** —
`harvest_floor_style` + `build_grid_payload_styled` copy real (batch-ctrl, uv4) pairs + 24-bit gouraud attrs from
the pristine floor (ctrl carries page+CLUT selection beyond &0x1F; ~48×48 windows, per-quad rotation, attrs
0x50-0x7C); **(2) placement law** — a payload renders ONLY over its OWN original bbox (anchors/records untouched);
every relocation scheme is pre-culled (morph experiment: same bytes at own bbox=renders, elsewhere=culled);
**(3) the tan ground-fill sprite overdraws the floor**, rebuilt per frame → permanently unlinked
(`--suppress-ground-fill`, nop AddPrim @0x8003DA90). **Budget measured:** ≤~1100 quads/frame total (30×n6=1080 ✓,
1188/1512 ✗ — candidate mechanism 0xBB8 reset @0x8001EB04→gp+0x5FC). **Walls untouchable in ALL directions**
(park/collapse/replace/re-anchor each kills the chain) → stay original border cliffs. Ship config + diagnostic
hygiene (init-magic wait + settle; crops not raw screenshots; picks can be won by invisible overlays):
`docs/G3_NATIVE_P57_PRISTINE_GROUND_TRANSPLANT.md`.

## P53 — one-mesh contract confirmed; free-roam coverage = the honest frontier (2026-07-07)

**One Blender mesh drives BOTH terrain and collision by construction** — `surface_json` → `flatten_floor` visual +
the P52 authored collision world; designers never author collision separately. Proven on a **large test level**
(`tools/abl_blender/g3_native_p53_bigland_scene.py`: 97×161 heightfield over the whole 22k×40k floor footprint —
rolling hills, 900-unit ridge, valley trench, two mesas, `dy=[-1219,728]`): cold-boots, renders, walks live
(`build/p53_lane_*.png`).

**Free-roam finding:** true off-script wandering (manual `pressButton` after `movie.stopPlayback` — the first
non-recorded driving on these discs) finds **coverage seams**: authored collision covers original-footprint unions
(±`--coverage-margin`, new flag) + flat tiles, NOT the full field. Decisive pristine A/B: pristine walks NW from
spawn to (1675,18832); the authored world falls at (2931,17929) — seams are introduced, not original topology.
Mechanism: original sector flat BASES sit ABOVE the authored surface → un-tiled spots are death holes, not potholes.
Fix attempts preserved: `--base-to-surface` **FAILED** (3rd confirmation of the absolute-origin-set wall);
`--seamless-world` (Voronoi cell-quads per sector, `heightfield_collision.cells_block`) is structurally valid —
records verifiably cover the fall points — but the runtime does NOT resolve them; needs a resolver single-step
session (next milestone). **Practical contract today: route-class levels on/near the covered band are fully
validated; unconstrained free-roam is the open frontier.** All recorded-movie "moved+goal" proofs to date ran the
operator's recorded inputs — P53's manual driving is the new, stricter test class.
Doc `docs/G3_NATIVE_P53_FREE_ROAM_COVERAGE.md`.

---

## Overnight collision push (2026-07-05) — critical FRAME fix + Phase A/B

**⚠ CRITICAL BUG FOUND + FIXED — collision frame-scale (delta/32).** The M4 collision was shifting the chunk-32
sector origin-Y by the raw game-unit heightfield delta. But the terrain payload VERTICES are GAME units
(`world_y = T_obj + v_local`, Flik's frame), while the collision **origin-Y is FILE frame** and the converter
`<<5`'s it at runtime. So a game-unit delta added to origin-Y is amplified **×32** at runtime — collision moved 32×
the visual; Flik stood ~`delta*32` too high and free-fell through the giant phantom sector steps. **Proof:** at
spawn gentle Flik settled +4070 above pristine, and 127(delta)`<<5` = 4064. **FIX (`native_collision_from_heightfield.py`):**
shift origin-Y by `round(delta/32.0)` so the runtime floor moves the SAME game-unit delta as the visual. The visual
`--displace` (game units) was always correct; only collision was wrong. This makes the whole per-sector pipeline usable.

**Phase A — per-sector v1 VALIDATED on gentle terrain (after the fix).** Gentle heightfield
(`export_terrain_heightfield.py --gentle`, ~±660 game-unit rolling bumps) → `--displace` DAT + fixed collision →
cold-boot walk from spawn (turbo movie + `pressButton` + monitor Flik XYZ 0x800a6500/04/08). Result: **Flik walks the
gentle Blender bumps smoothly** — vs pristine on the same path, samples match within ±500 game units; walking Right
(medY=292, 32k units, no fall) and Left (69k units, no fall) traverse cleanly (screenshot: Flik on the sloped pebbly
bank). Falls happen ONLY into LEVEL01's ORIGINAL steep valleys (plane-resolved sectors ~119/166), where per-sector-FLAT
collision can't reproduce the sloped floor and Flik tunnels through. **DECISION: per-sector v1 is ACCEPTABLE for
subtle/gentle native-density terrain (the real goal — a new Blender level would be gentle throughout).** Disc
`build/ABL_native_gentle`.

**Phase B — plane-block RE substantially closed (`src_re/collision_source_converter_80030f60.c`).** Parsed sec-119's
block (chunk-32 0x1bf90, 5956 B): it's a **DENSE oriented-plane collision MESH** (~150-185 planes), NOT flat+few. The
old "6 planes" = the per-frame AABB candidate list near Flik. Plane record CONFIRMED `0x20` B: `normal[3]`(|n|=0x4000)
+ `ref[3]` + `ext[10]`; records **cross-reference** each other (shared ref/edge coords) = an INDEXED mesh. The block
is NOT a simple `[marker][count]` array (walk fails; plane runs at half-record-offset alignments separated by
headers). **Emitter feasibility (honest):** a general emitter for arbitrary terrain needs decoding the indexed-mesh
layout + the AABB→candidate-array selection + `ext[10]` region semantics + the `0x12345678` relocation — a large,
high-risk block-synthesis. **Counterweight:** v1 (per-sector-flat, fixed) already walks gentle terrain, so the
plane-emitter is a STEEP-terrain enhancement, not a blocker to authoring gentle custom levels. → operator decision.

**SHIPPED v1 — one-command pipeline (operator decision 2026-07-05: "ship v1, defer emitter").** Per-sector-flat
collision (delta/32-fixed) is the adopted collision for GENTLE custom Blender levels; the plane-emitter is parked.
Single entry point: **`tools/build_gentle_terrain_disc.py`** — `--gentle` (Blender demo bumps) or `--heightfield <json>`
→ displaced native-floor DAT + delta/32-fixed collision RAW + auto-layout disc, in ONE command. Byte-verified equal
to the in-game-validated `build/ABL_native_gentle`. Keep authored terrain gentle (steep slopes step under
per-sector-flat; that's the deferred emitter's job).

---

## Plane-emitter resumed — collision-block format FULLY DECODED + validated (2026-07-06)

Resumed the deferred smooth/steep-terrain collision work. The chunk-32 per-sector collision **BLOCK** is now fully
reversed (live disasm of candidate-builder `FUNC_80037320` + floor resolver `FUNC_80038090`; byte-exact codec
`tools/native_collision_mesh_codec.py`; authoritative detail in `src_re/collision_source_converter_80030f60.c`
"FULLY DECODED FORMAT" + B4 + SEMANTICS).

- **BLOCK** = groups `[s16 marker≥0][s16 count][s16 aabb minX,extX,minZ,extZ][count × 0x20-B records]`, terminated by
  a marker<0 header. **RECORD** (0x20 B): `normal[3]` (|n|=0x4000, `normal.y<0` = floor) + `V0/ref[3]` + edge deltas
  `dV1/dV2/dV3` (XZ, +0xc..+0x17) + footprint AABB (+0x18..+0x1f). Verified: sec-119 = 16 groups / 180 planes, parse
  lands exactly at block end; codec round-trips byte-exact.
- **Broad-phase auto-derived at load** from record footprints (spatial grid `0x800b2540`, sector AABB, Y-bounds) — the
  emitter need not author it. Relocation `0x12345678` only in a special end region (not normal blocks). Block ptr =
  implicit running-sum of `src+0x04`×2. Chunk 32 = length-prefixed sub-arrays (resize touches that prefix).
- **SEMANTIC (in-game proven):** floor planes are the **sub-sector SLOPE floor** — they override the flat origin-Y
  ONLY where Flik's XZ is inside a floor-triangle footprint (steep/valley); flat origin-Y is the floor elsewhere. So
  planes are exactly the lever for smooth STEEP terrain; per-sector-flat stays the gentle base.
- **TOOL + VALIDATION:** `tools/emit_collision_reheight.py` — SIZE-PRESERVING re-height of an existing block's planes
  (`--raise-runtime` or `--heightfield`), no resize/relocation/grid-rebuild (126 LEVEL01 sectors own a block).
  Confirmed live (ref.y delta exact) and validated by walking Flik spawn→valley over re-heighted sec 107/108: a
  uniform +5000 stopped his descent then fell off the raised island edge (expected); a **continuous** heightfield
  re-height (gentle ±660 AND steep 4× ±2640) let him descend+climb the valley **smoothly**, floor deviation scaling
  ~linearly with amplitude (step-9 vs pristine: gentle Δ167, steep Δ732 ≈ 4×), no stepping/fall. → "simple slope →
  steeper hill/ridge, Flik walks it without stepping" milestone **DONE**.
- **REMAINING (next):** add-block resize (planes for currently-FLAT sectors) via the chunk-32 length-prefix resize +
  sector-array shift; fix `--all-blocks` decode (one sector truncates); tie plane collision to the Blender visual mesh
  in `build_gentle_terrain_disc.py` so authored steep terrain gets matching planes.

---

## C2 — add-block resize (planes for currently-flat sectors), 2026-07-06

Extends the plane-emitter to give a **currently-flat** sector its own collision block. `tools/emit_collision_addblock.py`.

- **RESIZE MECHANISM — validated in-game (cold boot).** The block region is exactly full and the sector-array offset
  is derived from the length prefix at chunk-32 `+0x04`. To add a block: insert its bytes at the sector's running-sum
  position, bump the `+0x04` prefix, append the relocated 189-sector array tail. Sectors 189–222 (all flat) live in
  chunk 33, which the loader places **contiguously after** the grown chunk 32. Proof: a disc with chunk 32 grown
  +372 B (a copied block added to a flat sector) cold-boots clean, Flik spawns + walks the pristine path (the level
  base pointer at `0x80082498` just shifts by +372). So the loader is **not** fixed-address — resizing chunk 32 is safe.
- **BLOCK OWNERSHIP — decoded + verified.** `block_size` (`+0x04`) alone does not make a sector own a block; the
  marker is src sector **`+0x4a`** (converter `bne [+0x4a],1,block-path` at `0x80030e9c`): `+0x4a==1` = flat
  (descriptor-copy path), `+0x4a==0` = block sector. Setting a flat sector's `+0x4a=0` + `block_size` + inserting the
  block makes it **own** the block — verified live (runtime sector `+0x10` points at the inserted block; its X-AABB is
  computed correctly from the record footprint).
- **REMAINING blocker (well-scoped).** The per-record **footprint Z encoding** (`rec+0x1e/0x1f`) is not yet exactly
  reproduced. The grid-builder computes `minZ = V0.z + rec[0x1e]*64`, `maxZ = V0.z + rec[0x1e]*64 + rec[0x1f]*4096`,
  but that doesn't fit real records (`rec[0x1f]=8` on a triangle of Z-extent ~619 would give +32768), so a synthesized
  block gets a garbage Z-AABB and isn't reliably broad-phase-selected. Decode this Z packing (compare real records'
  `rec+0x1c/0x1e/0x1f` vs their `V0.z + dV.z` triangle Z range) to finish C2. The X footprint (`rec+0x18/0x1a`) is
  already correct. The size-preserving **reheight** path (`emit_collision_reheight.py`) remains the fully-working
  emitter for the 126 sectors that already own a block.

### C2 footprint-Z decode + broad-phase selection (2026-07-06)

Focused on the remaining footprint-Z blocker and validated as far as broad-phase selection.

- **Footprint encoding DECODED (byte-exact vs real records).** X = `rec+0x18` minX / `rec+0x1a` extX (s16). Z:
  fine-test (candidate builder, the test that gates selection) extent = `rec+0x1f`*64, `minZ = V0.z + rec+0x1e*64`;
  the grid-builder over-inflates Z to `rec+0x1f`*4096 (coarse). `rec+0x1c` is read by neither → 0 is valid. The
  codec's `Plane.from_fields` already reproduces `rec+0x1e/0x1f` byte-exact — the footprint-Z "blocker" was really a
  **scale** issue: real records use SMALL footprints (`rec+0x1f`≈6–19, extZ≈400–1200); a block **tiles** its area
  with many small triangles. One oversized quad (`rec+0x1f`≈78) inflates the grid AABB ~10× and breaks the grid-cell
  assignment.
- **Broad-phase selection ACHIEVED.** With a realistic tiled footprint covering the sector origin, a from-scratch
  flat-sector block (`+0x4a=0` + inserted block) IS selected in-game — verified live: sec 77 appears in the candidate
  sector array `0x80091718`, and its candidate record at `0x8009c230` has the correct normal/ref.
- **Also decoded (validation byproducts):** real FLOOR triangles are wound **clockwise** (`(V1−V0)×(V2−V0)<0`) and
  are tilted (normal ≈ terrain face); the point-in-polygon floor test needs CW winding. **`−Y` is up** (spawn Y
  +2734; walking up the slope → Y more negative; free-fall → Y increases); a floor plane catches a falling Flik only
  when it is **above** him (more negative Y).
- **Remaining last step.** Reliably co-locating, on Flik's path, grid-cell **selection** + point-in-poly
  **containment** + the plane on the correct floor-side. The grid-cell assignment is very sensitive to the block's
  footprint extent (small tiling changes flip whether the sector is selected along a path) and isn't fully modeled
  yet; teleport-poking doesn't engage gravity (must drive via walk input). Next: decode the grid-cell builder loop
  (`@0x80031c00`, fills `0x800b2540` from sector AABBs). The **reheight** path remains the fully-working emitter for
  the 126 sectors that already own a block.

### C2 grid-cell builder decoded; selection of a synthesized block still blocked (2026-07-07)

Decoded the grid-cell builder (`FUNC @0x800313a8..0x8003229c`) — the broad-phase the candidate builder reads:

- **Pass 1:** write each sector's world AABB to the runtime table `0x800a7e48` (`+0x14/+0x1c` min, `+0x24/+0x28`
  ext = origin + footprint-bounds`<<5`; Z-max uses `rec+0x1f*4096`, over-inflated but normal). `gp+0x508` counts.
- **Pass 2:** overall collision bounds over all sector AABBs.
- **Grid:** `step = sqrt(Xspan·Zspan·10/N)`, `gridW=ceil(Xspan/step)`, `gridH=ceil(Zspan/step)` (LEVEL01: N=223,
  step≈209500, ~20 populated cells). Cell entries `@0x800b2540` (stride `0x14`: first_slot, count, minX, minZ, extX,
  extZ); member sector indices `@0x800a2388`; a cell's AABB = union of its members; sectors bin to a cell by position.
- **Candidate builder:** phase-1 gathers sectors from cells whose AABB contains Flik(±4096) into scratchpad
  `0x1f800000`; phase-2 iterates them, per-sector AABB gate (`0x800374ac`) + flag (`+0x2c` nonzero <100), then the
  per-record footprint fine test → candidate list `0x8009c230`.

**Still blocked (root cause unisolated).** A synthesized flat-sector block is *systematically* excluded from
selection. Verified (execTrace + continuous-walk): sec 77 **is** in Flik's grid cell, **is** iterated by phase-2, its
AABB gate **passes** by hand-calc, and its runtime record shows **no anomalous field** vs a working sector (108) —
yet it never enters the candidate list (0/24 samples walking squarely over its tiles) while real sectors 107/108 are
selected every frame. **Gotcha that cost time:** the builder runs *during movement*, so the candidate list is stale
on static frames — sample Y/candidates while walking, in small increments from spawn (poke-teleport doesn't engage
gravity). Closing this needs **live single-step** (halting breakpoint at `0x800374ac`), not execTrace — likely the
add-block path doesn't populate a structure pass-1/gather reads (the `+0x48` descriptor / `+0x4a` path). Everything
else is proven: resize (+cold-boot), ownership (`+0x4a=0`), footprint encoding, CW winding, `−Y`-up sign. The
**reheight** path remains the fully-working emitter for the 126 sectors that already own a block.

### C2 BREAKTHROUGH — player vs enemy collision list (2026-07-08)

Single-stepping the actual gate (per request) revealed the whole prior "sec 77 not selected" saga was **reading the
wrong candidate list**:

- **`FUNC_80037320`** (the candidate builder with the `0x800374ac` per-sector gate) is the **enemy/entity** collision
  builder — 8 callers, all enemy-AI/projectile (`0x8004ce80`, `0x8004cf94`, …), invoked with **entity** positions,
  never Flik's (single-step showed arg = enemy XZ). The shared arrays (`gp+0x57c` / `0x8009c230` / `0x80091718`) are
  overwritten per entity, so every candidate-list read all along was some enemy's.
- **The player floor is `FUNC_8003633C`** (`0x8003633c..0x8003731c`): self-contained — resets `gp+0x57c`, builds its
  **own** candidate list with Flik's position, then `jal FUNC_800345CC` (swept resolver) + `jal 0x80035280`, and
  writes Flik.Y (writers `0x80036384/cf0/d58`, found via an accessLog write-watch on `0x800a6504`).
- **Sec 77 IS in the PLAYER's candidate list** — breaking at `0x800368d8` and reading while Flik walks over the tile:
  `secs=[44,44,44,77,100,100,…]`. So resize + ownership (`+0x4a=0`) + footprint + grid membership **all work
  end-to-end** for the player; the from-scratch block **is** selected. This supersedes the earlier
  "systematically excluded" note (that was the enemy list).

**Remaining (precisely isolated):** the synthesized plane is a candidate but doesn't **set** Flik's floor. Drop tests
over the tile: normal `(0,−0x4000,0)` → Flik falls *through* −8000 to the flat floor (~+2000); normal `(0,+0x4000,0)`
→ free-falls past everything. So `FUNC_800345CC` doesn't register a synthesized plane the way it does real 107/108
(which reheight proved catch Flik). **Next:** single-step `FUNC_800345CC` (`0x800345cc`) for Flik crossing a sec-77
tile vs a real plane — capture normal/ref/d0/d1 + branches and diff the loaded record fields (read the resolver, don't
guess the normal). **Physics note:** a floor plane only acts when Flik's *motion crosses* it (swept); it does not lift
a standing Flik onto a higher plane. The flat per-sector origin-Y is the default surface; planes add slopes/steps that
moving Flik crosses — which is why the valley reheight works but a flat spawn-area plane doesn't change a level walk.

### C2 COMPLETE — synthesized block catches Flik, validated in-game (2026-07-09)

The synthesized flat-sector collision block **works end-to-end**: cold-booted, Flik lands on it and stands.

- **The player swept resolver is `FUNC @0x80035280`** (`0x80035280..0x80035f20`) — *not* `0x800345cc` (that's a
  collision dispatcher). Found via an accessLog read-watch on the synthesized plane record (reader = `0x80035408`).
  It iterates the player candidate list (sector `0x80091718[i]`, plane ptr `0x8009c230[i]`), makes Flik's segment
  sector-relative, and per plane: `normal = s0+0/2/4`, `ref = s0+6/8/a` (`<<5`); `d1 = (normal·(p1−ref<<5))>>14`
  (skip if ≥0), `d0` likewise (skip if <0); **crossing iff `d0≥0 AND d1<0`** (segment from the +normal side to the
  −normal side), contact committed to Flik.Y (`0x80036cf0/d58`). A floor = normal points up (−Y): p0 above → p1
  below = Flik falling **onto** the floor.
- **No plane-record discriminator — the emitter is correct as-is.** Proof: normal `(0,−0x4000,0)` + CW winding,
  plane Y=−4992; teleport Flik above the tile and let him fall — he is **caught at Y=−5251** (= plane + his ~256
  stand height) and stays there **stable for 32+ frames**, floating ~7800 units above the flat floor on the
  from-scratch block, then walks off the tile edge. Screenshot: Flik standing elevated.
- **Why the multi-day struggle** (none were emitter bugs): (1) the candidate list I kept reading is the **enemy**
  builder's (`FUNC_80037320`, 8 enemy-AI callers, overwritten per entity) — the player floor is `FUNC_8003633C`
  which builds its own list, and sec 77 *is* in it; (2) **physics** — a floor plane only acts when Flik's motion
  *crosses* it from the +normal side (he must fall/descend onto it); it does not lift a standing/walking Flik onto a
  higher plane, and a plane below the flat floor is ignored (that's why the valley reheight of real slopes worked
  but a flat spawn-area plane did nothing during a walk); (3) one earlier drop used a +Y normal, and "confirming"
  reads used the enemy list.

**Full C2 pipeline — all proven:** chunk-32 resize (grow block region + bump length prefix + relocate array;
cold-boots) → ownership (`+0x4a=0`) → footprint encoding → CW-wound floor tris → grid membership (player selects it)
→ swept resolver catches Flik. `tools/emit_collision_addblock.py` + `native_collision_mesh_codec` are correct as-is.
To make Flik **walk** a from-scratch slope (not just land on a flat plane), author the tiles as a ramp/steps his
path descends across — exactly like a real slope block. The `reheight` path already does this for the 126 sectors
that own a block.

### Practical Blender collision pipeline — built + validated (2026-07-10)

Turned the C2 add-block emitter into the working Blender collision pipeline. One heightfield (same source as the
visual mesh) → a cold-boot disc whose LEVEL01 collision matches the terrain, choosing the mechanism by physics.

**Tools**
- `tools/heightfield_collision.py` — `mesh_block()` / `quad_record()`: synthesize a tilted floor-quad collision mesh
  from a world height function. Quads match the C2-validated winding (V0→TL→TR→BR, deltas `[(0,dz),(dx,dz),(dx,0)]`,
  normal up ny<0). **Frame:** vertex Y = `surface_runtime>>5` (ABSOLUTE — the swept resolver's floor = `ref.y<<5`,
  it does NOT add origin.y; X/Z are sector-local/origin-relative for the footprint).
- `tools/build_terrain_collision_disc.py` — one-command pipeline: displace visual (`native_terrain_export`) +
  origin-Y walk collision (`native_collision_from_heightfield`) + optional `--reheight` (block sectors, caveat) +
  `--platform SECTOR:RAISE` add-block fall features (`emit_collision_addblock` + `mesh_block`) + disc build.

**Mechanism by physics** (all validated in-game):
- **WALK** = per-sector origin-Y shift (`+delta/32`). Primary walkable-terrain mechanism: Flik's standing floor is
  the flat origin-Y, fine at 223 sectors. Add-block plane sits ON TOP of it and only engages when Flik's motion
  CROSSES it (a fall/descent) — it does NOT let him walk UP onto a raised plane. So walkable slopes = modify the
  existing collision (origin-Y / reheight), not add on top.
- **SLOPES on block sectors** = `reheight` (caveat: ref.y sign is `-delta/32`, opposite origin-Y; verify per sector).
- **FALL / net-new** = `add-block` synthesized floor mesh.

**Validation (`build/ABL_terrain_full`, ramp heightfield + platform in flat sector 77):**
- WALK: cold-boot, Flik walks the custom ramp/ridge terrain (spawn Y 1326 vs pristine 2734; walks spawn→−18054,
  max per-segment dY 7110, no fall-through). Visual (displaced native floor) shows the ramp; Flik stands on it.
- FALL: teleport Flik above the sec-77 add-block platform (target floor −9328) — he falls and is caught, hovering
  ~−9000 (floor + stand height), stable 30+ frames, on the from-scratch synthesized block.

### Pipeline polish — stable authoring workflow (2026-07-05)

Hardened the pipeline into a repeatable workflow; **no new RE**, but the frame question is settled and two bugs fixed.

**Reheight sign unified.** `emit_collision_reheight.py` now uses `ref.y += delta/32`, the SAME direction as the flat
floor's origin-Y `+= delta/32` and the visual displace `v.y += delta`. Because a plane's floor = `ref.y<<5`
ABSOLUTE (the swept resolver does NOT add origin.y — C2), shifting a block sector's origin-Y moves its flat base but
leaves its oriented planes behind, so **reheight is the correct COMPLEMENT** for block-owning sectors (not the
double-shift the old caveat feared). Still `--reheight`-off-by-default pending per-sector in-game confirmation.

**`--all-blocks` decode guard.** `native_collision_mesh_codec.decode_block()` now raises `ValueError` when a group
overruns its block, so the chunk-32 **relocation region** (`0x12345678` magic @`0x35830`+, sectors **178–188**) is
no longer mis-parsed into short records. The reheight driver skips those sectors instead of corrupting them.

**Regression harness — `tools/test_terrain_pipeline.py`** (one command: build fixed ramp+platform disc → launch
isolated instance → validate → stop). Four checks, all **PASS** deterministically:
- **VISUAL** — displaced DAT + shifted RAW differ from pristine, disc cold-boots to gameplay.
- **WALK** — Flik walks the custom ramp from spawn, no fall-through, Y bounded.
- **PLATFORM** — the add-block plane is SELECTED as a live PLAYER candidate (`FUNC_8003633C` list `gp+0x57c` /
  `0x80091718`) when Flik's XZ is over it. Candidate lists read `[77,77,100,…]` for 5/6 frames — the whole
  add-block chain (resize + ownership `+0x4a=0` + footprint + grid membership) works.

**Why PLATFORM replaced a teleport-catch.** The swept CATCH is C2-proven, but auto-testing it by teleporting Flik
onto the plane is **flaky**: the physics can snap him to the pristine floor in one frame, and — **operator-confirmed**
— if the resolved plane floor sits UNDERNEATH the drop point he falls straight through (the swept test only fires
when his motion crosses the plane from the +normal side). The FRAME is not the culprit (floor = `ref.y<<5` absolute,
two C2 catch tests). So the harness validates candidacy (broad-phase is XZ-only → robust to / needs no Y drop) and
leaves the catch itself C2-proven. **Authoring rule:** teleport Flik carefully — a plane resolved below the drop =
fall-through. See `src_re/collision_source_converter_80030f60.c` "C2-POLISH".

### Richer authoring — arbitrary-topology visual mesh export (2026-07-05)

First richer-authoring upgrade past the heightfield pipeline. The heightfield path (`native_terrain_export --displace`
/ `regenerate_floor`) can only BUMP the game's existing floor footprints (keeps each payload's grid topology); this
adds authoring a genuinely NEW shape — any Blender mesh (arbitrary verts + tri/quad faces) encoded into one native
`FUNC_80010000` payload. **Purely additive**: the heightfield/collision pipeline and its regression harness
(`tools/test_terrain_pipeline.py`) are untouched and still PASS.

**Tools**
- `tools/native_mesh_authoring.py` — `mesh_to_payload(verts_world, faces, tobj)` encodes an arbitrary mesh into a
  native payload (reuses `native_mesh_codec` Payload/Batch/Prim); `inject_mesh()` appends+repoints it into a chosen
  floor payload (default the largest-footprint one) via `native_dat_inject`. CLI: `--demo` (built-in pyramid, no
  Blender) or `--mesh <json>`. Conventions: faces oriented UP (geometric normal −Y, the floor emitter's draw
  direction); a triangle encodes as a quad with a degenerate 4th vertex; single texpage/tile-UV per call
  (per-material batching = follow-on). Cap ~5461 verts/payload (u16 vertex byte offset).
- `tools/abl_blender/export_mesh.py` — Blender headless: export a mesh object's verts+faces as the mesh JSON in game
  world coords (shared `b2g` convention; ngons fan-triangulated). Author in Blender → export → `--mesh` → disc.
- `tools/verify_mesh_authoring.py` — reproducible cold-boot proof (concurrency-safe unique port/config-dir).

**Validation**
- OFFLINE: `--selftest` — for a grid input, `mesh_to_payload` produces the SAME rendered triangles as the
  in-game-proven `build_grid_payload` (grid-equivalence, so a surface mesh renders on the proven path); the demo
  pyramid round-trips + injects append-only (all pre-EOF diffs inside the 4-byte reloc field).
- IN-GAME (cold boot, `build/ABL_mesh_demo`): the target payload's NODE in guest RAM has its relocated pointer
  (node+0x14) pointing at bytes IDENTICAL to the authored pyramid (node @0x80164f50 → payload @0x801b1c10,
  vertexCount 5). Since these node payloads ARE the native floor the renderer draws (M2/M3), the arbitrary mesh is
  resident and drawn by `FUNC_80010000`. NOTE (learned): payloads relocate INDEPENDENTLY per node (no single global
  DATbase+file_off) and many nodes share a T_obj — verify via the node's relocated pointer, not a computed DATbase.
- REGRESSION: `tools/test_terrain_pipeline.py` still PASS (VISUAL/WALK/PLATFORM).

**Scope / next.** VISUAL ONLY — collision is the separate chunk-32 layer, so an authored mesh is not walkable until
paired with matching collision (heightfield sampling / plane emitter). Follow-ons: per-material texpage batching
(the encoder already supports multi-batch), multi-payload chunking for meshes >~5461 verts, dead-payload reclamation.

### New-level POC — spawn-area replacement (2026-07-05)

First "new level" proof-of-concept: replace the spawn-area visual terrain + collision with an authored
platform→ramp→platform and prove authored geometry (not OG) carries Flik. Tool: `tools/build_poc_newlevel.py`
(disc `build/ABL_poc_newlevel`). Driver findings below.

**FRAME MODEL nailed (decisive).** `render_runtime = node_world << 5` (uniform ×32, XYZ). Proven by replacing the
spawn payload with a flat mesh at node-Y=93 → it renders exactly at Flik's feet (2976 = 93<<5; spawn 2734). So the
native-payload frame = Flik/runtime frame >> 5 = the collision STORED frame. **A visual vertex Y and its matching
collision plane `ref.y` are both `runtime_Y >> 5`** — author both from one surface in the runtime>>5 frame and
they align. Spawn facts: Flik (197091,2734,492897); file XZ (6159,15403); covering payload `0x1b9f0`; stands on
collision sectors **100 (BLOCK) + 77 (flat)**.

**WHAT PASSED (validated cold boot):**
- VISUAL — the spawn floor payload `0x1b9f0` is replaced by an authored platform→ramp→platform mesh drawn by the
  native GTE emitter. Screenshot: Flik standing on the authored dirt floor.
- COLLISION carries Flik at the AUTHORED height — he rests + walks a stretch of platform A at **Y≈4064**, the
  authored surface (PA=4500), **NOT the OG spawn height 2734**. So authored collision, not OG, holds him (OG
  heights overwritten). Mechanism: keep the OG sectors' catching plane STRUCTURES, replace their HEIGHTS (flat:
  origin-Y = surf>>5; block: each plane → horizontal normal + ref.y = surf>>5).

**WHAT BLOCKED IT (why this is a POC, not the full level — gates expansion):**
- The overwrite-heights mechanism only covers **OG-walkable XZ**. An authored footprint that extends past the OG
  floor has **coverage gaps** → the full ramp traverse plunges at the first gap (Flik walks platform A ~9k units,
  then hits a gap where OG had no plane at that XZ and falls through).
- The clean fix — a complete NEW tiling via **add-block** (`emit_collision_addblock` + `heightfield_collision.mesh_block`) —
  **SELECTS** as a player candidate but does **NOT catch a naturally-falling Flik**. Reheighted ORIGINAL block
  planes catch; a flat sector CONVERTED to a block does not. `+0x4a=0` and `+0x48=-1` (the source fields that
  distinguish block from flat) do **not** fix it — the discriminator is a load-time runtime-structure build.
  ⚠️ Method note: writing Flik's position words FREEZES him (zeroes velocity) — the old "C2 catch" evidence was a
  teleport artifact; only a natural fall/walk tests the resolver. See
  `src_re/collision_source_converter_80030f60.c` "ADD-BLOCK CATCH".

**Decision (per the task gate):** do NOT expand to full-level replacement yet. The prerequisite is fixing add-block
catch — single-step the player floor resolver `FUNC@0x80035280` with Flik falling onto an add-block plane and diff
the per-plane branch inputs / runtime sector fields against an original block sector that catches.

### Add-block catch — resolver single-step (2026-07-05)

Disassembled + live-traced the player swept resolver `FUNC@0x80035280` during a NATURAL fall (Cross = jump; no
teleport — position writes only move the render pos and the physics sim snaps them back, confirming the operator's
warning). Two findings, one fixed:

**ROOT CAUSE #1 — floor formula (PROVEN + FIXED).** The resolver computes `plane_floor_runtime = ref.y<<5 +
origin.y<<5` — it SUBTRACTS the runtime sector origin `0x800a7e48[sector]` from Flik before the normal-dot, so
origin.y **is** added (the earlier "ref.y<<5 absolute" was a teleport-freeze artifact). Measured: sector 77
origin.y=−3328, my plane ref.y=140 → effective floor `140<<5−3328 = 1152`, which sits ABOVE Flik's spawn (2734), so
he never crosses down and falls through. **Fix:** `ref.y = surf>>5 − origin_file.y` (patched
`heightfield_collision.mesh_block` and the POC block-overwrite). Verified: block planes now CATCH. This also
explains the POC "coverage gaps" — block planes at `ref.y<<5` (no origin) landed at wildly wrong floors (sector
100: −45888) and never caught, so only the flat sectors held Flik.

**FINDING #2 — the resolver runs in a PHYSICS-position frame, not the render pos `0x800a6504`.** Its `a1`/`s5` arg
points at a stack buffer holding Flik's physics position; `a0`/`s3` is the per-frame movement delta. Physics Y leads
render Y by a large, non-constant amount during motion (physics −64 vs render 1792 mid-fall) and they converge at
rest. So collision authored to match RENDER heights is mis-placed in the PHYSICS frame, letting OG planes catch Flik
first during motion.

**RESIDUAL (open).** Even with the correct floor + OG neutralized, a from-scratch add-block did not catch a fast
boot-fall. Selection works, the plane is read correctly, the floor is correct — remaining suspects: the physics↔render
frame offset (calibrate before setting ref.y) and fast-fall tunneling vs the plane's point-in-poly footprint. Next:
an isolated jump-down onto an add-block (repeatable) + single-step `d0(@0x800354b4)`/`d1(@0x80035464)`/point-in-poly
for sector 77 in the physics frame. Full detail: `src_re/collision_source_converter_80030f60.c` "ADD-BLOCK CATCH —
RESOLVER SINGLE-STEP".

### Add-block catch — isolated single-step (2026-07-05, cont.)

Built a repeatable, teleport-free crossing (Cross = jump onto a sec-77 add-block with OG dropped below it) and
traced the full swept resolver `FUNC@0x80035280`: `d1(@0x80035464) → d0(@0x800354b4) → point-in-poly(jal 0x80032610
@0x80035644) → keep-nearest(@0x800356a4) → RESPONSE(@0x8003573c)`. The response is a **partial push-back**, not a
snap: `displacement = delta·(d0>>3)/((d0>>3) − ((d1−192)>>3))` — for a **deep** first-crossing (fast fall, `d1`
large-negative) the fraction is tiny, so Flik is only nudged and keeps sinking.

Live: sector 77 **crosses** (`d1=−1518, d0=82`), **passes point-in-poly**, and **is recorded as the sole best
crossing** — yet no catch. **Key result: an *original* block sector reheighted flat to 5000 fails the same fast fall
→ this is not a converted/add-block bug.** In every neutralize configuration Flik reliably rests on whatever sectors
were left deep (~10234) and passes through anything placed at 5000 (flat *or* block), pointing at a **physics-side
mechanic** (spawn-snap / velocity / safety-floor), not the plane emitter. Strong confounds remain (per-sector XZ
coverage — Flik's spawn XZ is owned by block sector 100 — plus the physics-vs-render frame), so the final
catch-reliability discriminator is **not** cleanly isolated.

**Conclusion:** root cause #1 (floor formula `ref.y = surf>>5 − origin.y`) is proven, fixed, and necessary; the
block-plane *catch* is entangled with the physics integrator, not a further emitter field — so per the directive,
**no more emitter changes**. Next lives in the integrator (accessLog write-watch the physics-pos buffer `[s5]` during
a fall to find where velocity/grounded-state is set, and whether a kill/safety floor forces the ~10234 rest);
otherwise keep authored walkable floors on the flat per-sector origin-Y path (`native_collision_from_heightfield` —
the game's own ground mechanism). Full detail: `src_re/collision_source_converter_80030f60.c` "ADD-BLOCK CATCH —
ISOLATED SINGLE-STEP".

### Flat-floor / origin-Y consolidation — platform→ramp→platform POC (2026-07-05)

Parked the add-block/physics-integrator investigation and consolidated the STABLE flat-floor path into a POC:
`tools/build_poc_flatramp.py` authors a platform→ramp→platform heightfield through the proven pipeline
(`build_terrain_collision_disc`: displaced visual + per-sector origin-Y collision, `--reheight` optional, **no
add-block**); `tools/validate_poc_flatramp.py` cold-boots and walks Flik.

**Validated (cold boot):** the disc boots, Flik spawns stable (Y~2734, origin-Y-only leaves the spawn block sector
untouched), and he **walks the authored terrain smoothly with no fall-through** (validator PASS) — the stable
origin-Y floor carries him, no add-block needed.

**Limits found (why a *clean, distinct* platform→ramp→platform is NOT demonstrable on LEVEL01):**
1. The op is a **DELTA shift, not an absolute set** — it modifies LEVEL01's existing (non-flat) terrain; it cannot
   flatten it into clean level platforms (an absolute origin-Y set is interpreted *relatively* by the converter and
   breaks the sectors).
2. **LEVEL01's own terrain dominates:** walking +Z from spawn climbs a ~25 000-unit original hill (confirmed
   identical on the pristine disc), which dwarfs any *walkable*-scale delta (per-sector-flat must stay gentle,
   ~2000 over a wide span, or inter-sector steps get too big and Flik falls through).
3. **Enemies + walls confound long walks** — a spider chaser near spawn (operator-flagged) plus walls caused the
   chaotic falls in the first long-walk attempt; a short near-spawn walk is smooth and plunge-free.

**Conclusion / recommendation:** the stable flat-floor/origin-Y path **works** (Flik walks authored terrain from
cold boot, no add-block), but a **clean** platform→ramp→platform layout needs a **flat base with no original
hills/enemies** — the **Tier-3 custom level** (authored-from-scratch terrain), not LEVEL01. Build the clean layout
there next; only return to the add-block / physics-integrator investigation if the flat/origin-Y path cannot express
the layout on the Tier-3 base either.

### Full-replacement attempt on LEVEL01 — blockers + scaffolding (2026-07-05)

Acceptance target moved to **full level replacement** (not modifying LEVEL01). Built `tools/build_poc_replacement.py`
to neutralize the test-area confounds and author a platform→ramp→platform on the stable path (enemies removed +
displaced visual + origin-Y/reheight collision, no add-block). **Result: LEVEL01 is NOT a viable base for a clean
full replacement**, confirmed by four independent, measured blockers:

1. **Can't flatten (delta-only).** origin-Y and reheight are DELTA shifts. An absolute origin-Y set / block→flat
   convert (`+0x4a=1`) **loads for a single sector** (verified: sector 100 → flat, level boots, Flik Y=2734) but
   **CRASHES when applied to the whole test region** (Flik Y reads back as a garbage pointer) — the flat/descriptor
   path can't take the whole neighborhood converted at once. So the terrain shape can only be *shifted*, not
   flattened into clean platforms.
2. **Original terrain dominates.** Walking +Z from spawn climbs a **~25 000-unit original hill** (identical on the
   pristine disc), which dwarfs any walkable-scale authored delta (~2000 — per-sector-flat must stay gentle or the
   inter-sector steps get too big and Flik falls through). The authored ramp is invisible under the hill.
3. **Reheight shifts the spawn.** Reheight samples the delta at each sector's **origin**, and the spawn *block*
   sector (100) has its origin in the ramp region, so Flik spawns at ~4718 instead of 2734 — platform A isn't clean
   at spawn.
4. **Enemies only partially removable.** Moving the 3 chaser spawn AREAS (`edit_dat_coord_record.py` records
   0x94c/0xa10/0xad4, +800000) relocates the bee/mosquito/spider, but LEVEL01 still spawns **static (chunk-31)
   enemies** — the enemy pointer table `0x80090748` still holds 4–6 actors near spawn.

**Original systems still relied on as SCAFFOLDING (what full replacement would still need to own):** the level
LOADER (LEVEL.DAT/RAW load + reflow), the collision **sector GRID / broad-phase**, the **spawn mechanic + resident
EXE spawn table** (`0x80077314+scene_id*12`), the **collision base SHAPE** (delta preserves LEVEL01's hills), the
**static chunk-31 enemy set**, the **render path** (`FUNC_80010000`), and everything outside the small test area.

**Conclusion / decision:** the stable flat-floor/origin-Y path **cannot express a clean full-replacement layout on
LEVEL01** — not because of the add-block catch, but because LEVEL01's terrain (hills), collision structure (mixed
flat/block sectors that won't flatten at scale), spawn coupling, and static enemies can't be neutralized via
delta-only edits. The correct base for full replacement is the **Tier-3 custom level** (authored-from-scratch, flat
base, no original hills/enemies) — [[tier3-custom-level-engine]] / build_tier3_render_disc. `build_poc_replacement.py`
+ `build_poc_flatramp.py` are the reusable stable-path authoring substrate to point at that base. Returning to the
add-block / physics-integrator investigation is still NOT warranted — the blocker here is the LEVEL01 base, not the
catch mechanism.

### Platform→ramp→platform on the Tier-3 custom base — SUCCESS (2026-07-05)

Moved the platform→ramp→platform POC off LEVEL01 onto the **Tier-3 custom-level base** (the goal is full
replacement, and LEVEL01 can't be flattened — see the previous section). The Tier-3 pipeline
(`tier3_blender_export` → `tier3_level_from_json` → `build_tier3_render_disc`, one-button `tier3_build_level.sh`)
already suppresses the OG terrain/collision and cold-boots an authored-from-scratch level, so the layout is authored
as a **Blender mesh** (`tools/abl_blender/tier3_flatramp_level.py`) — same *concept* as the LEVEL01 heightfield
pieces, different sink.

**Authored:** platform A (spawn, flat) → a gentle ramp (RISE 10 BU / RUN 40 BU, slope 0.25 < jump) → platform B
(raised), all textured with the **reused LEVEL01 pebble-dirt** tile (`abl_texpage=0x660, abl_clut=0x3FFC,
abl_uv=[0,192,63,63]` = the render cave's `E2_WIN_PEBBLE` window; neutral GP0 modulation `0x20808080`), plus a
**perimeter wall** (`abl_clut=0x3FFD` wall tile, steep → auto-classified as a wall) so Flik can't walk off into the
death pit (operator flagged the fall-off).

**Validated (cold boot, `build/ABL_tier3_render.cue`, `tools/validate_tier3_flatramp.py` PASS):** Flik spawns on
platform A (Y ≈ −266, the authored pebble floor — screenshot: clean pebbles, no OG hills in the play area), walks
the authored ramp with his Y climbing smoothly to **−10266** (exactly the 10 BU RISE), stands on platform B, and is
**bounded by the walls (no plunge)** across a 30-step walk. He traverses the AUTHORED visual terrain + collision +
reused LEVEL01 ground textures with **no reliance on LEVEL01's original hills/collision/enemies**.

**Texture-residency assumption:** the reused pebble/wall tiles live in the LEVEL01 terrain atlas (VRAM page 0x660,
cluts 0x3FFC/0x3FFD @ v=192). The Tier-3 build keeps LEVEL.RAW UNTOUCHED and boots through LEVEL01's loader, so that
atlas is resident and the authored surfaces render with genuine LEVEL01 ground/wall pebbles.

**Original systems still relied on as SCAFFOLDING:** LEVEL01's LOADER + resident EXE + the Tier-3
collision-suppression / render / walls CAVES; the far BACKDROP PANORAMA (chunk-29 grass/cliff/sky horizon — cosmetic,
behind the level); the native SPAWN anchor (origin → LEVEL01 spawn floor); and the VRAM texture ATLAS.

**Limits:** geometry within ~±150 BU of the origin (native streaming); ≤ ~45° = floor / steeper = wall; the Tier-3
blob/vert budgets; a platform edge with no wall = death-plane fall. **Conclusion:** the stable authoring path DOES
support a clean full-replacement platform→ramp→platform — on the Tier-3 custom base, exactly as predicted. The
add-block / physics-integrator investigation stays parked (never needed for this).

### ARCHITECTURE AUDIT — "Tier-3" is two tracks (2026-07-05)

"Tier-3" is overloaded. There are TWO independent rendering tracks; the platform→ramp→platform POC uses TRACK A.

| Aspect | **Track A — OT/cave CPU renderer** | **Track B — native GTE FUNC_80010000** |
|---|---|---|
| Files/tools | `mod/caves/tier3_otrender.c`, `mod/tier3_otrender_live.asm`, `mod/tier3_loader.asm`, `mod/tier3_level_format.py`, `tools/tier3_blender_export.py`, `tier3_level_from_json.py`, `build_tier3_render_disc.py`, `tier3_build_level.sh` (one-button + the Fedora GUI) | `tools/native_terrain_export.py`, `native_mesh_codec.py`, `native_dat_inject.py`, `native_mesh_authoring.py`, `native_collision_from_heightfield.py`, `build_autolayout_disc.py` |
| Renderer entry | DrawOTag DMA-kick hook **`0x80064618`** → render cave `0x801F0000` → `RENDER_C 0x801F0C00` (`tier3_otrender_hook`): CPU **fixed-point** project+clip the level blob's tris, insert GP0 flat-tri **OT NODES** (node buf `0x801FAC00..0x801FE000`) into the game's OT; the game's DrawOTag DMA draws them. Gate: `COPIED 0x8007F300`. | **`FUNC_80010000 @0x80010000`** — the game's own **hardware GTE** mesh emitter, drawing the LEVEL.DAT floor node-array payloads (`T_obj + v_local`, GTE-transformed) every frame. |
| Collision | `mod/caves/tier3_walls.c` (`WALL_FN 0x801F0100`) — per-face SEGMENT planes auto-derived from steep mesh tris + **native-collision suppression** (sink native sector floors) + `tier3_floor.c` multi-floor query; hosted in the CD-loaded render region. **WORKS** (walkable). | The game's native **chunk-32 sectors** (origin-Y flat + oriented planes via swept resolver `FUNC@0x80035280`). Walkable-catch is the **UNSOLVED** add-block/physics-integrator problem (parked). |
| Texture source | Reused LEVEL01 VRAM tiles via GP0 texpage/CLUT in the OT nodes (page 0x660, CLUT 0x3FFC ground / 0x3FFD wall); `LEVEL.RAW` untouched → atlas resident. | Native payload per-vertex GOURAUD + UV/texpage (`attr`, dirt UV[0,63]V[192,255] texpage 0x0060). Same atlas. |
| Status | **WORKING end-to-end** — cold-boot, walkable, textured (AILEVEL + the flat-ramp POC). | RENDER **proven** (M2/M3: authored payloads draw via GTE); walkable COLLISION **not solved** → no end-to-end walkable custom level. |
| Tri / perf | CPU-capped: `MAXV 384 / MAXT 512`, **~700 tris @ 30fps**; fixed-point project/clip is the bottleneck. | Native GTE density — ~810 polys/frame @30fps baseline, thousands feasible (cap ~5461 v/payload × many payloads). **The point of Track B.** |
| POC uses it? | **YES** — `build/tier3_flatramp.blend` → this pipeline. | **NO.** |

**PROOF that `build/tier3_flatramp.blend` renders via Track A (`tier3_otrender.c`), NOT `FUNC_80010000`** (2026-07-05,
`scratchpad/prove_renderer.py`): (1) `gpu.pickObject` on the pebble terrain → `dmaSource=0x801FAD98`, inside the OT
cave's NODE BUFFER (`0x801FAC00..0x801FE000`). (2) `execTrace`: `RENDER_C 0x801F0C00` runs 6×/6 frames (every frame).
(3) DECISIVE DISABLE: zeroing the render gate `COPIED 0x8007F300` makes the flat pebble platform **vanish** and the
**original LEVEL01 terrain reappear** (screenshots `build/proof_disabled.png` vs `proof_before.png`) — i.e. the OT
cave draws my terrain, and `FUNC_80010000` (105 hits/6f) is drawing the *original* LEVEL01 terrain underneath, just
covered by my prepended OT platform. **So Track A "replacement" is OVERDRAW, not removal.**

**RELABEL:** the flat-ramp POC (`tier3_flatramp_level.py`, `build/ABL_tier3_render.cue`) is a **CPU-OT-renderer
BASELINE ONLY**. It is NOT the GTE-native level-replacement goal and must not be treated as completion of it.

### Smallest next POC for the ACTUAL goal (GTE-native), scoped 2026-07-05

Goal: platform→ramp→platform whose VISUALS render through `FUNC_80010000` (Track B), reusing the most reliable
collision. Do NOT resume broad level building first. Phases (each gated + proven before the next):
- **G1 — GTE RENDER PROOF (render only, no collision claim).** Regenerate the native floor payloads as the
  platform→ramp→platform mesh (`native_terrain_export`/`native_mesh_authoring`, reusing the dirt UV/texpage/attr
  from the audit), build a cold-boot disc (`build_autolayout_disc`), and **prove via `gpu.pickObject` that the
  terrain's drawn primitive comes from a LEVEL.DAT native payload (NOT the `0x801FAC00..` OT node buffer)** and that
  `RENDER_C` is absent/unhooked. This confirms the authored shape draws through the native GTE emitter end-to-end.
- **G2 — RELIABLE COLLISION on the GTE terrain.** Add walkable collision WITHOUT the unsolved native-plane catch:
  first choice = **port the Track-A walls-cave per-face-plane collision** (`tier3_walls.c`, already proven walkable)
  onto the G1 terrain (collision is renderer-independent — it reads the mesh, not the OT nodes); fallback =
  per-sector origin-Y for flat parts. Validate Flik traverses A→ramp→B and prove (pickObject) the terrain is GTE-drawn.
- **G3 — remove the OVERDRAW dependence.** With Track B drawing the terrain natively, retire the OT overdraw so the
  authored terrain is the real native floor (not a cover), and confirm the original LEVEL01 terrain is gone (not
  merely hidden). Only then is it a true GTE-native replacement.

### OFFICIAL PATH FORWARD (canonical, 2026-07-05)

> Repo-facing mirror: **`docs/TIER3_RENDERER_TRACKS.md`** (read before touching any Tier-3 render/level code).
> The two-track table above is the reference; this is the committed plan. Supersedes the earlier informal
> "Smallest next POC" list.

**Track labels (locked):** **Track A = OT/cave CPU renderer = CPU BASELINE ONLY** (not the final architecture, not
GTE completion). **Track B = native GTE `FUNC_80010000` = TARGET ARCHITECTURE.**
- Track A — *still useful for:* a fast walkable baseline/smoke-test, authoring-workflow shakeout, and the known-good
  **collision source** (`tier3_walls.c` per-face planes) that Track B reuses.
- Track B — *why target:* native GTE density/fps (thousands of tris vs Track A's ~700 cap), native depth/cull for
  free, and a **true replacement** (authored terrain IS the native floor — no overdraw / no original hiding under).

**Goal:** a Blender-authored replacement level whose visual terrain renders through native GTE/`FUNC_80010000`,
reuses LEVEL01 texture assets where practical, and has reliable walkable collision.

**Non-goals (for now):** don't treat `tier3_otrender.c`/`RENDER_C` output as GTE completion; don't expand the CPU OT
renderer into the final level system; don't resume broad native add-block physics unless the chosen collision path
requires it; don't call the CPU flat-ramp POC a GTE-native success.

**Milestones (gated):**
- **G1 — Render-only native GTE proof: ✅ DONE (2026-07-05).** `tools/build_g1_gte_terrain.py` +
  `tools/validate_g1_gte.py` PROVE it: RENDER_C(0x801F0C00 Track-A OT)=0 hits, FUNC_80010000(0x80010000 GTE)=99
  hits/6f, terrain `pickObject` source not in the OT node buffer (0x1FAC00..0x1FE000). Render-only, no collision
  claim; shape is base+delta (clean spatial layout is G3). Original: author platform→ramp→platform as native LEVEL.DAT payloads, disable/bypass
  the CPU OT cave, cold-boot, prove by instrumentation (`pickObject` source = a LEVEL.DAT native payload not the
  `0x801FAC00..` OT node buffer; `RENDER_C 0x801F0C00` absent; `FUNC_80010000` draws it) that the native emitter
  draws the authored mesh.
- **G2 — Collision strategy: ✅ DONE (2026-07-05).** `build/ABL_g2` (`build_poc_flatramp.py` = GTE `displace`
  visual + origin-Y collision, no OT cave); `tools/validate_g2_gte.py` PROVES GTE-rendered (RENDER_C 0,
  FUNC_80010000 100/6f, source not in OT buffer) AND walkable (moved 186k, no plunge). Evaluated the walls-cave
  port (feasible, moderate-high — Tier-3 collision blob + native GTE payloads from the same mesh, render off);
  chose ORIGIN-Y — the matching tool for a heightfield (same heightfield → GTE displace visual + origin-Y
  collision, M4-matched, proven, zero integration). Walls-cave deferred to when walls/steep faces are needed (G3/G4).
  Original: attach reliable walkable collision to the GTE terrain — first evaluate porting the
  Track-A walls-cave per-face collision over the GTE mesh; fallback to native origin-Y/reheight or (last resort)
  resumed add-block research only if necessary.
- **G3 — Replacement-level proof: ✅ DONE (2026-07-05).** `tools/build_g3_full.py` → `build/ABL_g3full`: native GTE
  floor FLATTENED to platform A → ramp → platform B matching the walls-cave collision; cold-boot proven RENDER_C 0,
  FUNC_80010000 101, spawn −266, Flik walks flat pebble A→ramp→B (climb 10000, no plunge). See the **"G3 —
  Replacement-level proof (2026-07-05)"** section below for the two halves (decoupling + flatten) and the union.
  Original: neutralize original LEVEL01 visual+collision reliance in the play area (keep only loader/texture/spawn
  scaffolding); validate Flik traverses A→ramp→B on GTE-rendered terrain + matching collision.
- **G4 — Authoring workflow:** reproducible Blender→build→validate from a clean checkout, with documented texture
  settings, slope limits, wall/collision rules, and regression tests.

---

## G3 — Replacement-level proof (2026-07-05)

G3 needs the play area to render authored terrain through the **native GTE** path AND carry **matching walkable
collision**, with the original neutralized. Two capabilities were missing; both are now **cold-boot proven
independently**, and the honest status is that **uniting them in one disc is blocked by a known tooling seam**, not
a runtime unknown.

### (a) Decouple GTE render from the walls-cave collision — the `TIER3_GTE_FLOOR` flag  ✅ PROVEN
The Track-A loader `tier3_load_render` (`mod/tier3_loader.asm`) did THREE coupled things: load `TIER3.RND`
(walls-cave collision + spawn), install the DrawOTag hook `0x80064618` (CPU OT cave draws), and **neuter
`FUNC_80010000`** (native floor suppressed). `TIER3_INSTALL_HOOK` (patch_tier3_collision.asm) gated the whole load,
so the old "render-off" switch `ABL_NO_RENDER_HOOK` also killed collision + spawn (observed: spawn reverted to the
native 2734, Flik on the original hill).

**Fix:** new build flag **`TIER3_GTE_FLOOR`** (env `ABL_TIER3_GTE_FLOOR=1` → `build_tier3_render_disc.py` passes
`-equ TIER3_GTE_FLOOR 1` to armips). It keeps `TIER3_INSTALL_HOOK=1` (RND load = collision + spawn) but wraps BOTH
(i) the DrawOTag hook install and (ii) the `FUNC_80010000` neuter in `.if TIER3_GTE_FLOOR == 0`. Result: walls-cave
collision + custom spawn run, the CPU OT cave never draws, and the **native GTE emitter draws the floor**.

**Proof — `build/ABL_g3` (`ABL_TIER3_GTE_FLOOR=1`, flat-ramp lanes, cold boot):** spawn=(197091,**−266**,492897)
= the flat-ramp spawn (RND loaded + warped); **RENDER_C(0x801F0C00)=0** (OT cave off); **FUNC_80010000=105**
(native emitter un-neutered/active); walk +X **climbed 10000** (the ramp RISE) to platform B, **no plunge** → Flik
traverses **platform A → ramp → platform B on the authored walls-cave collision**, GTE-rendered, no OT. No high-RAM
crash (the native-floor-rebuild-floods-high-RAM risk did not materialize). *Visual caveat:* in this build the native
GTE floor is un-neutered but **un-regenerated**, so it draws the ORIGINAL LEVEL01 hills — collision is authored, the
visual is not yet.

### (b) FLATTEN the native GTE floor into clean absolute platforms  ✅ PROVEN
`build_poc_flatramp.py`'s own RESULT/LIMITS block documented that the delta paths (`displace_floor` /
`native_collision_from_heightfield`) **cannot flatten** LEVEL01's hills — they only shift them — so a clean
platform→ramp→platform "needs a FLAT BASE… i.e. the Tier-3 custom level, not LEVEL01." But `build_grid_payload`
takes an **arbitrary `height_fn`**, so `regenerate_floor` with an **ABSOLUTE** height function rewrites every floor
payload's surface to a chosen absolute Y, **erasing the original relief**. New tool: **`tools/build_g3_flatten.py`**
(platform A at the spawn payload's base Y=−497; ramp; platform B raised to Y=−2997; `regenerate_floor` n=6 over all
30 floor payloads → `build_autolayout_disc`, NO OT cave).

**Proof — `build/ABL_g3flat` (`tools/validate_g3_flatten.py`, cold boot):** **RENDER_C=0**, **FUNC_80010000=99**,
terrain `pickObject` source in the native DMA region (0x1EC0A0 / 0x1E3C18), **not** the OT node buffer
(0x1FAC00..0x1FE000). Screenshot `build/g3flat_spawn.png` shows a **clean flat platform A** (foreground) + a
**distinct raised flat platform B** band + ramp — the original rolling pebble hills are gone. This is the "flatten"
capability the delta path could not reach, done through the native GTE emitter.

### The remaining step — MATCHED union (documented seam, not an unknown)
To get flat visual **and** matching flat collision in ONE disc:
- **Walls-cave collision (b's flat visual + a's decoupling):** blocked by `build_tier3_render_disc.py`'s
  grass-terminator offset math (line ~244): it assumes all resizing **shifts** offset 0x3AFA by `len(staged)-len(dat)`,
  but `regenerate_floor` **appends at EOF** (0x3AFA does NOT move) → the assert fails. `displace_floor` is
  size-preserving (compatible) but delta-only (can't flatten). **Path:** either make `build_tier3_render_disc` read
  the regenerated DAT as its `dat` reference (append is at EOF, so 0x3AFA is unshifted relative to the regenerated
  base and only the object-relocation delta applies — needs verifying `apply_objects_exact`'s EOF append/repoint
  doesn't collide with `inject_many`'s), or teach the offset model to separate the EOF-append delta from the
  content-shift delta.
- **Origin-Y collision matched to the absolute flatten:** `native_collision_from_heightfield` is delta-based and a
  big flatten delta (erasing a ~25k hill) makes big inter-sector steps Flik falls through — exactly
  `build_poc_flatramp`'s documented failure. Reinforces its conclusion: a **flat authored base** (Tier-3 custom
  level) makes BOTH halves clean; on LEVEL01 the walls-cave IS the clean flat collision, so the union is the
  offset-math fix above.

**Net:** the GTE-render target architecture is proven end-to-end in pieces — GTE floor + reliable authored collision
+ traversal (a), and a clean flat authored GTE visual (b). Closing G3 = the offset-math union (a mechanical build
seam), the natural entry into G4's authoring workflow. Tools: `tools/build_g3_flatten.py`,
`tools/validate_g3_flatten.py`, `build/ABL_g3` (decoupling), `build/ABL_g3flat` (flatten). asm/build flag:
`TIER3_GTE_FLOOR` in `mod/tier3_loader.asm` + `tools/build_tier3_render_disc.py`.

### G3 CLOSED — the matched union (2026-07-05)
The real union blocker was NOT the grass-terminator offset math but the **fixed disc layout**: `build_tier3_render_disc`
embeds LEVEL.DAT with LEVEL.RAW at hardcoded LBA 3069, so LEVEL.DAT must stay **≤163 sectors**; `regenerate_floor`
appends ~35 KB (→180 sectors) and overruns LEVEL.RAW. **Fix — a SIZE-PRESERVING flatten:** `native_terrain_export.flatten_floor`
SETS each existing floor-payload vertex Y to the absolute platform height (no denser grid → no DAT growth → fits 163
sectors AND leaves 0x3AFA unshifted), unlike `displace_floor` (delta-only, can't flatten) or `regenerate_floor`
(denser, +KB). Wired into `build_tier3_render_disc` via **`ABL_TIER3_FLATTEN_JSON`** (spec `{axis,a0,a1,ya,yb}`, file
frame). One-command build: **`tools/build_g3_full.py`** — derives the flatten spec from the SAME flat-ramp Blender
geometry that authored the collision (spawn + platform A / ramp Blender X 20..60 BU rise 10 BU, 1 BU = 1000 ABL,
node/file = runtime/32) so visual and collision share one source, then builds with `ABL_TIER3_GTE_FLOOR=1` +
`ABL_TIER3_FLATTEN_JSON`.

**Proof — `build/ABL_g3full` (scratchpad check_g3full, cold boot):** RENDER_C(0x801F0C00)=0, FUNC_80010000=101,
spawn=(197091,**−266**,492897), walk climbed **10000** (the 10 BU ramp rise) to platform B, no plunge. `build/g3full_spawn.png`:
Flik stands on a **clean flat pebble platform A** (feet on the surface — the flatten height matches the walls-cave
collision), the original LEVEL01 hills gone in the play area, floor drawn by the native GTE emitter. So the play area
renders authored terrain through native GTE with matching authored collision and Flik traverses A→ramp→B — **G3 done.**
**Residual (cosmetic → G4):** the flatten touches ALL floor payloads, so a few off-play-area payloads that were
vertical/side geometry flatten into visible background diagonal planes (the known "floating chunk" glitch); restrict
the flatten to play-footprint payloads (bbox filter in `flatten_floor`) in the G4 authoring pass.

### G3 native-frame pivot — Flik stands on the GTE floor he sees (2026-07-05)
The walls-cave collision (adopted at G3 for clean flat collision) held Flik in a DIFFERENT frame than the native
GTE floor, so flattening the visual to match it never converged (floating floor — live-poke calibration showed the
native floor payloads don't share a consistent render height when flattened; some sit at feet, others float).
**Pivot:** derive BOTH layers from ONE heightfield (the proven G2 pipeline `build_terrain_collision_disc`):
VISUAL = `displace_floor` (per-vertex Y += delta), COLLISION = `native_collision_from_heightfield` (per-sector
origin-Y += delta/32). Same delta → **alignment is by construction, no absolute frame needed.** A FLATTENING delta
(`target_platform - base_y`) inside a box around the play area (delta=0 native beyond) reads flat; native spawn
lands Flik on platform A (target A = base_y@spawn). Tools: **`tools/build_g3_native.py`** + `validate_g3_native.py`.

**VALIDATED (build/ABL_g3native, cold boot):** spawn Y=3598 (native floor, NOT walls-cave −266), RENDER_C(OT)=0,
FUNC_80010000 active, Flik walks flat platform A → ramp → raised platform B (climb 7436) with NO plunge — he stands
on exactly the floor he sees (screenshots: feet planted on the pebble, no floating band). Scenery suppressed:
pass-1 (442) + pass-3 (140) parked, floor-registering pass-1 records spared (42), 27/30 off-play-area node floor
payloads parked.

**KEY FINDING — the remaining LEVEL01 look is NOT the node floor.** The background hills + the mushroom/acorn/leaf
fixtures survive parking ALL off-area node-array (FUNC_80010000) payloads → they are a SEPARATE terrain system
(chunk-34/35 bulk terrain / terrain-baked class, [[walls-are-chunk35]]), which is load-wedging to edit. So the
authored PLAY AREA (flattened node floor + matched collision, walkable, aligned) is clean; stripping the surrounding
chunk-35 terrain + baked fixtures for a fully clean full-frame read is the riskier next step. Floor could also be
flatter (displace flattens to per-payload MEAN, not perfectly planar — the per-face plane path would sharpen it).

### OFFICIAL validation = operator's full-level movie (2026-07-05)
Validation path is now **`tools/validate_g3_native_movie.py`** replaying the operator's **`g3native_movie.movie.json`**
(from-boot, 6296 frames, recorded against build/ABL_g3native) — a **beginning→end-of-level traversal**.

**CONFIRMED over the whole movie:**
- **RENDER_C (Track-A OT 0x801F0C00) = 0** — the CPU OT renderer stays disabled the entire run.
- **FUNC_80010000 (native GTE 0x80010000) = 6033 hits** — the native emitter draws every frame.
- No plunge into void (Flik never falls through).

**DOCUMENTED MISMATCH — the movie traverses the WHOLE level; the build replaces only a small spawn patch.**
Flik spawns in the authored flat patch (frame ~4380, X≈192329 Y≈3387) but LEAVES it within ~80 frames (by frame
4620 he is already outside the ±3600-world flatten box) and walks the entire level to X≈−186758, Y≈−201469. So ~99%
of the movie plays on **un-replaced LEVEL01**, where (operator-confirmed):
1. **The OLD collision is still there.** Flik walks LEVEL01's original hilly collision. Even inside the coordinate
   box his Y climbs to −26840 by frame 4460, because `build_g3_native` origin-Y-flattens only FLAT sectors — the
   BLOCK sectors keep their oriented planes (no `--reheight`), so their collision stays hilly.
2. **The farther terrain rendering is still present.** The chunk-34/35 bulk terrain (hills) draws across the level;
   the flattened play-area node floor appears as floating sheets in the distance once Flik leaves the patch
   (g3nm_08/end frames). Feet track whatever Flik is on — the ORIGINAL surface (old collision matches old visual
   there), NOT the authored floor.

**Consequence for scope.** To make the full movie path read as an authored replacement, the replacement must cover
the WHOLE traversal, not the spawn box: (a) COLLISION — flatten/author across the level INCLUDING block-sector
reheight (`build_terrain_collision_disc --reheight` / a plane path), not just flat-sector origin-Y; (b) VISUAL —
strip/replace the chunk-34/35 bulk terrain across the level. This validation therefore CONFIRMS the chunk-35 work is
the required next scope, and that it is WHOLE-LEVEL (not merely "background"). Renderer decoupling (RENDER_C off,
GTE on) is proven solid; the gap is coverage of the play surface, not the renderer.

### Corridor collision coverage + block-sector reheight (2026-07-05)
Expanded the GTE-native replacement collision from the spawn patch to the WHOLE native-floor footprint (the entire
g3native movie traversal): `tools/build_g3_native.py --corridor` flattens the footprint to one flat height (RISE=0)
via origin-Y (flat sectors) + **`--reheight` (block-owning sectors' oriented planes)** so block sectors no longer
carry Flik on LEVEL01's original hilly planes. Build reheighted **93 block-owning sectors** (sectors 178-188 skipped
= the chunk-32 relocation region).

**Movie validation (`validate_g3_native_movie.py`), Flik's max hill-climb along the traversal:**
- pristine LEVEL01 hilly collision: **−201469**
- corridor ±12500 box + reheight: **−117910** (~40% less)
- **full-footprint corridor + reheight: −96655 (~52% less)** — RENDER_C(OT)=0, FUNC_80010000 active, no plunge.
Coverage helps progressively, so the expansion + block reheight measurably reduce how much LEVEL01's hilly collision
carries Flik.

**RESIDUAL (not truly flat) — the per-sector-flat limit.** A short controlled walk near spawn still climbs ~7860.
Root cause: both the origin-Y shift and the reheight derive their delta from `target − base_y(VISUAL)`, where base_y
is the per-payload MEAN of the visual floor — NOT each collision sector's actual origin-Y. So sectors don't all land
on the exact target (residual = (sy·32 − base_y)/32 per sector). Also documented in
native_collision_from_heightfield: "per-sector-flat collision CANNOT match a per-vertex mesh." To reach TRULY flat:
(a) set each sector's origin-Y + planes to an ABSOLUTE target from its ACTUAL origin (prior finding: absolute origin-Y
set "broke the sectors" for a VARYING target — but a UNIFORM flat target is untested and may behave), or (b) the
per-face plane-emitter (parked). Renderer decoupling remains solid; the gap is collision FLATNESS, not coverage.

### Truly-flat collision via absolute set — FAILED (confirms the plane-emitter is required, 2026-07-05)
To remove the corridor's per-sector-flat residual, tried `build_g3_native.py --corridor --flat-abs`: SET every
corridor sector's origin-Y AND every block plane's ref.y to a uniform target (139 file ≈ spawn floor), absolute (not
the delta shift). **Movie-validated result: it BREAKS the sectors** — Flik falls through to Y≈140000 (deep below the
intended floor), plunged=True, FAIL. This reproduces the prior finding (native_collision_from_heightfield: "SETTING
origin-Y to an absolute height broke the sectors") and proves it holds even for a UNIFORM flat target. **Conclusion:
truly-flat collision on LEVEL01 is NOT reachable by an absolute sector set — it requires the per-face PLANE-EMITTER
(parked, large).** The `--flat-abs` code is kept as evidence but must not be used; the working path is the
DELTA-based `--corridor` (52% hilliness reduction, RENDER_C=0, GTE active, no plunge).

**Net state of block-sector collision coverage.** Delivered: corridor coverage across the whole footprint + 93
block-sector reheights → Flik's hill-climbing along the movie roughly HALVED (−201469 → −96655) and he no longer
plunges, while renderer decoupling stays perfect. NOT delivered: truly flat (residual ~7860 near spawn) — that is
now proven to need the plane-emitter, not a tweak. The chunk-34/35 visual strip remains parked as instructed.

### Per-face plane-emitter — WALKING VALIDATED (2026-07-05)
Committed to the per-face plane-emitter (the corridor/reheight ceiling was proven: ~52% flatter, absolute-set breaks).
**`tools/emit_floor_planes.py`** generates chunk-32 collision from an authored floor SURFACE: FLAT play-patch sectors
get a from-scratch per-face mesh block (`heightfield_collision.mesh_block` + `emit_collision_addblock`, run
sequentially over 15 sectors); BLOCK sectors get their planes reheighted toward the same surface (14 sectors). Pair
with the displace-flattened DAT; build via `build_autolayout_disc`.

**The open question — does Flik WALK per-face planes (or do they only fall-catch)? — is answered YES:**
- **Flat de-risk** (surface = flat 2144 rt): controlled +X walk climbs **5031 vs 7860** for origin-Y/reheight →
  per-face planes carry a WALKING Flik, FLATTER than origin-Y, no fall-through, feet aligned with the visible floor.
- **Ramp** (platform A → +X ramp → platform B raised 4000 rt): **Flik WALKS UP the ramp, climb 3522 ≈ the 4000 rise**,
  no plunge. So walking UP a per-face slope works (not just descending) — the capability the reheight ceiling lacked.

**Remaining (well-defined, not blockers):** (1) VISUAL match — the ramp test reused a FLAT displace DAT so the GTE
floor floats above Flik at platform B; regenerate the visual to the SAME platform→ramp→platform profile (frame-match
the collision surface). (2) BLOCK sectors still reheight (delta, imperfect) — a block-REPLACE resize (per-face mesh
into existing-block sectors, not just add-to-flat) removes the residual. (3) extend over the whole g3native movie
corridor + validate via `validate_g3_native_movie.py`. Chunk-34/35 visual strip stays PARKED until collision fully
carries Flik. src_re: collision_source_converter_80030f60.c "PER-FACE PLANE-EMITTER — WALKING VALIDATED".

### Per-face emitter + MATCHED visual: A→ramp→B and the full movie corridor (2026-07-05)
`build_g3_native.py --planes` pairs the per-face collision (`emit_floor_planes`) with a GTE visual regenerated from
the SAME surface. **FRAME KEY:** the visual payload frame renders ×32 in runtime (node<<5; flat-aligned pair base_y
−497 ↔ collision runtime 2144), so the VISUAL rise = collision_rise/32.
- **A→ramp→B** (`--planes`): platform A visual+collision COINCIDE (Flik stands on the visible floor); Flik WALKS UP
  the ramp (climb ~3522 ≈ rise). Residual: the raised platform-B transition shows a floating GTE "sheet" — displace
  flattens each payload to its MEAN, so a height step reads as a sheet edge (displace-to-mean, not collision).
- **FULL CORRIDOR** (`--planes --corridor --rise 0`): 85 flat sectors get per-face blocks + 86 block sectors
  reheighted across the whole movie path. **Movie-validated: RENDER_C(OT)=0, FUNC_80010000 active (5124), NO plunge,
  Flik walks the full traversal aligned with the floor under his feet. Max hill-climb −201469 (pristine) → −96655
  (origin-Y+reheight) → −37727 (per-face) = ~81% flatter.** Per-face planes on FLAT sectors (vs origin-Y) are the win.

**Remaining (well-defined):** (1) block sectors still delta-reheight — a block-REPLACE per-face mesh finishes them;
(2) displace-to-mean sheet artifacts at height transitions — per-vertex visual match, or accept flat corridors; (3)
chunk-34/35 bulk terrain (twig/hills) still draws — PARKED per instruction until collision fully carries Flik.

### Block-REPLACE narrow gate — mechanism works, SELECTION does not (2026-07-05)
Gated per instruction: replace ONE block sector's collision with a per-face mesh, prove Flik walks it, THEN scale.
`emit_collision_addblock.replace_block()` mirrors add_block for an existing-block sector (splice new bytes, adjust
chunk-32 +0x04 length prefix + sector block_size). **STRUCTURE VERIFIED** — resizes, recompress round-trips,
cold-boots (sector 99: 4460→816 B). **But the gate FAILS in-game:** replacing sector 99 (covers Flik's spawn) with a
per-face mesh at the flatten surface → Flik FALLS THROUGH, at any tiling density (4×4…16×16); REHEIGHTING the same
sector catches him fine. The mesh is valid (add_block to FLAT sectors catches Flik, C2) — the gap is that replacing a
BLOCK sector leaves the sector-record state that REGISTERS the block for candidate SELECTION stale: reheight keeps the
pristine footprints + sector AABB (@0x800a7e48 from +0x14/1c/24/28) + reverse-map (+0x1e/+0x48), while replace_block
only rewrites +0x04 → the new block is present but NOT selected into Flik's candidate list (FUNC_8003633C).
**NEXT:** update the target sector's footprint AABB (+0x14/1c/24/28) + reverse-map (+0x1e/+0x48) to the new mesh's
extent so the grid builder selects it — OR keep the reheight path (already 81% flatter, Flik walks the movie). **Gate
NOT passed → replace NOT scaled.** Chunk-34/35 visual strip stays PARKED. src_re: collision_source_converter_80030f60.c.

---

# ▲ CURRENT SITUATION & FORWARD PLAN (2026-07-05) — read this first

> Consolidated snapshot after the plane-emitter / block-collision work. Supersedes the running status in the older
> sections above where they conflict (esp. the block-REPLACE entry — see the CORRECTION in "Open problem" below).

## Where we are — the GTE-native replacement, end to end

The goal (docs/TIER3_RENDERER_TRACKS.md): a Blender-authored replacement whose terrain renders through the **native
GTE** path (`FUNC_80010000`), reuses LEVEL01 textures, and has **reliable walkable collision that carries Flik**.

**Proven / working (all cold-boot + movie-validated):**
- **Renderer decoupled.** The CPU OT cave (`RENDER_C 0x801F0C00`) is OFF the entire traversal; the native GTE
  emitter draws every frame. Movie run: RENDER_C=0, FUNC_80010000 active, no plunge.
- **Native-frame collision (the pivot).** Visual + collision come from ONE heightfield (`build_g3_native.py`), so
  Flik stands on the floor he sees — no absolute-frame guessing. Frame key: visual payload renders **×32** in
  runtime (`node<<5`; flat-aligned pair base_y −497 ↔ collision 2144), so a visual rise = collision_rise/32.
- **Per-face plane-emitter carries a WALKING Flik** (`tools/emit_floor_planes.py`): flat sectors get from-scratch
  per-face mesh blocks (`mesh_block` + `emit_collision_addblock`), block sectors reheighted. Flik walks flat AND
  up a ramp (A→ramp→B, climb ≈ rise). Per-face on flat sectors is the big win over origin-Y.
- **Full movie corridor.** `build_g3_native.py --planes --corridor --rise 0` = the current build (`build/ABL_g3native`).
  Official validation = replay the operator's `g3native_movie.movie.json` via `tools/validate_g3_native_movie.py`.
  Result: **Flik walks the whole beginning→end traversal, aligned, no plunge; hill-climb −201469 (pristine) →
  −37727 (per-face) = ~81% flatter.**

**Parked (deliberately, per operator instruction):** chunk-34/35 **bulk terrain** (the twig/hills in the background)
and the **displace-to-mean visual sheets** at height transitions. These stay parked until block collision is fully
authored — the background is still LEVEL01's, but Flik walks authored collision.

## Open problem — block sectors are REHEIGHTED, not fully AUTHORED-flat

The 81% is the ceiling of the **delta-reheight** path: block sectors keep their intra-sector plane RELIEF (shifted,
not flattened). To finish, block sectors must be **authored flat** (planes set to a uniform floor).

**CORRECTION to the "Block-REPLACE — SELECTION does not" section above:** a runtime probe (0x800a7e48+99·0x30) of
the failing build showed the replaced/flattened sector **IS registered + selected** — valid block ptr, AABB covers
spawn, flag=6, and Flik is caught at spawn. **Selection was never the problem.** The two real walls:
1. A **grid replace** makes big-footprint quads (fp.extX ~293 file) that break the *fine* per-record candidate select
   while moving (pristine uses many SMALL footprints). Fixed by `emit_collision_reheight.flatten_block` — SET the
   existing planes' ref.y to a uniform floor, KEEPING their footprints (size-preserving).
2. **Seam discontinuity.** Flattening ONE sector to a uniform height while neighbours are delta-reheighted (varied)
   makes a step at the sector boundary Flik falls through. So the **one-sector gate is confounded by construction** —
   authored-flat and reheight can't meet at a seam. A valid flatten needs a CONSISTENT surface across all sectors.

Tools that WORK structurally (resize/roundtrip/boot, or size-preserving): `emit_collision_addblock.replace_block`,
`emit_collision_reheight.flatten_block`.

## Forward plan — milestones

- **P1 — Whole-region consistent flatten: ✅ ROUTE VALIDATED / ❌ NOT CLEAN REPLACEMENT (2026-07-06).** The current
  build flattens all selected block sectors with `flatten_block` and authors flat sectors to a matched surface, so
  the movie route carries Flik with no plunge, RENDER_C=0, and GTE active. Correction: this keeps LEVEL01's native
  block-sector X/Z footprints. It proves the constrained authored route, not deletion/replacement of all old
  collision or arbitrary free-roam collision.
- **P2 — Background cleanup: ✅ CLOSED TO SAFE SOURCE BOUNDARY / ❌ HORIZON STUB NOT BASELINE-SAFE (2026-07-06).**
  The separable RAW-backed 0x663 grass/mound pass is suppressed on disc. The EXE-backed 0x68D horizon/backdrop stub
  is A/B-only because manual boot proved `FUNC_8003E928` is menu-shared and breaks the level-select backdrop. This
  does **not** claim the risky structural chunk-35 edit path is solved; blanket chunk-35 edits still wedge loads,
  and the small 0x604 dirt hard path remains outside the safe P2 bake.
- **P3 — Visual polish: ✅ DONE (2026-07-06).** Kill the displace-to-mean "sheet" artifacts by making the native
  `FUNC_80010000` floor visual an absolute per-vertex surface set (`native_terrain_export.flatten_floor`) instead of
  a per-payload mean displacement. *Gate passed:* no retained native-floor relief/sheets in the movie build; all 30
  floor payloads / 2775 vertices sit exactly on the authored surface.
- **P4 — Author-from-Blender loop: ✅ DONE (2026-07-06).** A Blender scene now exports a G3-native profile, the
  wrapper builds the P1-P3 pairing, and the official movie validator runs from the same command. Gate passed on
  `build/tier3_flatramp.blend` using the default flat full-movie corridor profile.
- **P5 — Blender heightfield surface authoring: ✅ DONE FOR GENTLE HEIGHTFIELDS (2026-07-06).** The P4 wrapper now
  exports a Blender mesh grid to `surface_json`; `build_g3_native.py --surface-json` drives both the P3 absolute
  native visual and the P1 block/per-face collision from that non-flat surface. Gate passed on
  `build/g3_native_heightfield.blend` (`dy=[-196,256]` runtime), full movie, no plunge.
- **P6 — Hard residual visual cleanup: ✅ CLOSED TO SAFE BOUNDARY (2026-07-06).** Rechecked the hard residuals
  after P5. The safe baked suppressors remain verified; structural chunk-35 and the 0x604 dirt hard path remain
  not-baked because prior RE still says they are load-wedging or Flik-shared/incomplete.
- **P7 — Authoring polish/regressions: ✅ DONE (2026-07-06).** Added pure-Python regression checks for surface JSON
  frame mapping, wrapper command construction, and no silent Track-A / `--displace-visual` fallback.
- **P8 — Track-B Blender level scene contract: ✅ DONE (2026-07-06).** The heightfield scene now exports
  `level_meta` with `Spawn` and `Goal` empties in game coordinates, so the `.blend` carries terrain + basic level
  intent rather than just a surface patch.
- **P9 — Offline walkability gate: ✅ DONE (2026-07-06).** Added `tools/validate_g3_native_scene.py`, wired into the
  wrapper with `--check-scene`; it proves spawn/goal are on the surface and connected by a gentle grid path before
  building/running DuckStation.
- **P10 — Native material/style authoring: ✅ DONE (2026-07-06).** Blender material/object props now export native
  floor style (`color`, `uv`, optional texpage controls), and `native_terrain_export.style_floor` applies them
  size-preserving to the `FUNC_80010000` payloads.
- **P11 — Runtime spawn/goal integration: ✅ DONE (2026-07-06).** `level_meta.spawn` now drives a resident
  player-update hook that places Flik at the authored Blender spawn on cold boot; `level_meta.goal` now drives a
  simple in-game XZ AABB goal trigger that sets a validation flag and replicates the LEVEL01 type-1 exit body
  (`0x800823A0=1`, fade color `23`, `FUNC_80050994(58,0)`). Gate passed on the P11 Blender scene: exact spawn
  at `(197088,5344,492896)` and goal detected at frame ~5610. Follow-up stress test from a fresh worktree also
  passed after an intentional `.blend` edit: heightfield `dy=[-428,388]`, moved spawn `(6415,15147)`, moved goal
  `(-6900,-5300)`, material `0x4f8f64`, exact runtime spawn `(205280,5408,484704)`, goal detected, `RENDER_C=0`,
  `FUNC_80010000=3961`, no plunge.
- **P12 — One Blender-authored marker trigger: ✅ DONE (2026-07-06).** The Track-B exporter now accepts one optional
  non-visible `Marker`/`G3Marker` Empty. `build_g3_native.py` folds it into the existing player-update resident hook
  as a simple X/Z AABB trigger that sets marker flag `0x8007F308`; the wrapper automatically validates it with
  `--expect-marker` when present. Gate passed on `build/g3_native_marker_scene.blend`: marker file-space
  `(1340,14233)`, runtime AABB `(42880,455456)` radius `40960`, marker fired at frame ~4570, goal still fired at
  frame ~5610, `RENDER_C=0`, `FUNC_80010000=4035`, no plunge. This is a trigger volume only, not a visible native
  object or collectible counter path.
- **P13 — Visible marker indicator: ✅ DONE (2026-07-06).** P13 keeps the P12 invisible marker flag behavior and adds
  the smallest safe Track-B visual: `level_meta.marker.visual.kind=native_floor_tint`, generated from the same
  Blender `Marker`/`G3Marker` Empty. `native_terrain_export.style_marker_floor_tint` recolors existing
  `FUNC_80010000` floor primitives around the marker, size-preserving; it does not append a mesh, create a native
  type-`0x3f` object, or touch collision. Gate passed on the same marker fixture: 4 floor payloads, 42 native floor
  primitives, 72 vertices tinted, marker flag still fired at frame ~4570, goal still fired at frame ~5610,
  `RENDER_C=0`, `FUNC_80010000=4035`, no plunge. Current limitation: the visible patch is coarse and can bleed to
  nearby floor because it follows native primitive/vertex sharing.
- **P14 — Deliberate platform/ramp/platform validation fixture: ✅ DONE (2026-07-06).** Added
  `tools/abl_blender/g3_native_platform_ramp_scene.py`, which generates a P11-P13 heightfield scene rather than a new
  engine feature: platform A at the authored spawn `(6159,15403, dy=0)`, a short ramp marker
  `(4300,15670, dy=-245)`, and platform B/goal `(2418,15939, dy=-512)`. The cold-boot gate passed:
  offline scene path `12` nodes, surface `dy=[-512,0]`, max adjacent runtime step `76`, marker visual 6 payloads /
  107 native floor primitives / 174 vertices tinted, exact spawn `(197088,5344,492896)`, marker at frame ~4410,
  goal at frame ~4490, `RENDER_C=0`, `FUNC_80010000=668`, no plunge. Caveat: the ramp segment is deliberately
  short and aligned to the movie-stable lane; this validates the current Blender heightfield author loop, not
  arbitrary topology.

**Historical fallback:** the reheight corridor (81% flatter, Flik walks the whole movie) remains a useful comparison
build, but P1's whole-region `flatten_blocks=True` path is now the validated default.

**Key files:** `build_g3_native.py` (`--planes --corridor`, `--level-meta-json`), `emit_floor_planes.py`,
`emit_collision_reheight.py`
(`reheight_block`/`flatten_block`), `emit_collision_addblock.py` (`add_block`/`replace_block`),
`heightfield_collision.py` (`mesh_block`), `validate_g3_native_movie.py`. src_re:
`collision_source_converter_80030f60.c`, `player_update_80048138.c`, `level_exit_trigger.c`. Repo doc:
`docs/TIER3_RENDERER_TRACKS.md`.

## P1/P2 update (2026-07-06)

**P1 whole-region flatten is now a validated build path.** The one-sector seam confound is bypassed by flattening all
selected block sectors consistently: `tools/emit_floor_planes.py` gained `flatten_blocks=True`, and
`tools/build_g3_native.py` exposes it as `--flatten-blocks`. This uses `emit_collision_reheight.flatten_block` to set
existing block planes to the surface while keeping native small footprints.

Canonical current build (P3 absolute visual is now the default planes-mode visual; pass `--displace-visual` only for
legacy A/B comparisons):

```bash
python3 tools/build_g3_native.py --planes --corridor --rise 0 --flatten-blocks --suppress-grass --out build/ABL_g3native
```

Build output: 85 flat sectors got per-face mesh blocks; 86 block sectors were flattened; sectors 178-188 still skip
as malformed relocation-region blocks. Official movie validation on `build/ABL_g3native.cue`:
`RENDER_C(OT)=0`, `FUNC_80010000=7303`, no plunge, Flik Y range `[-11681,5216]`. This is materially flatter than
the prior per-face/reheight corridor (`-37727` min Y) while keeping native GTE rendering active and the CPU OT
renderer off.

**P2 safe slice completed: the 0x663 grass/mound pass is source-suppressed on disc.** Runtime probing corrected the
older DAT-relative hypothesis. Writing `DAT+0x378A` did not affect runtime `0x80163F82`; a cold-boot access watch
showed `FUNC_8001A1DC` builds the live source table from `LEVEL.RAW`. The effective row is in decompressed RAW
chunk 66 local `0x134` (current emitted RAW full-decomp offset `0x1395B6`; pristine `0x1330C6`). `--suppress-grass`
now searches that exact decompressed row after collision emission, sets row `+0x0E` to `-1`, recompresses only chunk
66, and verifies the decoder round-trip before staging.

**P2 second slice downgraded: the 0x68D horizon/backdrop sprite layer can be suppressed in A/B builds, but is not
baseline-safe.**
`FUNC_8003E928` is the confirmed chunk-29 panorama/haze tile builder (`GP0(65)`, texpage `0x68D`, CLUT `0x3470`).
For the movie-path gameplay view, `--suppress-horizon` patches the resident EXE at `FUNC_8003E928` /
`SCUS_942.88+0x2F128` from `addiu sp,sp,-88; lw v1,0x404(gp)` to `jr ra; nop`, and does not touch `FUNC_80010000` or
Flik. Manual boot later proved this same global function also affects the level-select/menu backdrop, so the patch is
now opt-in only and excluded from normal Blender/manual-playable builds.

Evidence:
- On-disk verification: `build/ABL_g3native_collision.RAW` has chunk 66 local `0x134` sentinel `-1`.
- Runtime verification: baked build reads `0x80163F82 = 0xFFFF`.
- `gpu.pickObject` at the former top-right 0x663 location `(450,30)` at movie frame ~5300 returns background.
- Runtime verification: A/B baked build reads `0x8003E928 = 08 00 E0 03 00 00 00 00` (`jr ra; nop`).
- `gpu.pickObject` at former 0x68D points `(310,82)` and `(300,105)` at movie frame ~5300 returns background.
- A deterministic A/B of live `FUNC_80014B04 -> jr ra; nop` trims, but does not cleanly remove, the residual 0x604
  dirt samples (2 grid hits -> 1) and was not baked.

Hashes for the validated default build:
- `build/ABL_g3native.cue`: `ae55fdb235f6281a0e14e749c10121191aad9879af4fd957154146680f595ea6`
- `build/ABL_g3native.bin`: `fb0e1656b709f39ba9039d4cf97143ddb1e18646264974169fca92b7c3a72907`
- `build/ABL_g3native_SCUS_942.88`: `5d58da1776987853afbfd0e8b10940c0b5424e6a71eac350b30648dd0d2b7b1e`
- `build/ABL_g3native_collision.RAW`: `ca5e48b436ae5f1480031f634e5ddd2ff379b361e4e3c270401e84c48dfee1c2`
- `build/ABL_g3native_terrain.DAT`: `2b75a4f2936d0f5589c4dd80cb1f1eed88c48f56feb7fc1f7450ee4dfb722392`
- `g3native_movie.movie.json`: `a311e6247537e206cd9056e18c915d6c3f08145ed189e118aac8b49ae3f81bbf`

**P2 closure boundary.** The separable RAW-backed 0x663 source row is baked out. The EXE-backed 0x68D
horizon/backdrop tile builder is A/B-suppressible but not baseline-safe because it is menu-shared. Remaining visible
0x660/0x663 quads in the P2 pick grid are written
by `FUNC_80010000`, the target native GTE floor emitter, so they move to P3 visual-authoring cleanup rather than P2
suppression. The small 0x604 dirt residue is the known `FUNC_80014B04` path; prior render/list levers are
Flik-shared or cold-boot-unsafe, and the fresh live A/B still does not cleanly remove it. Structural chunk-35 disc
edits remain load-wedging territory; do not blanket-edit them.

## P3 update (2026-07-06)

**P3 visual polish is now a validated build path.** `tools/build_g3_native.py --planes` no longer emits the native
visual through the legacy `displace_floor` path by default. It now builds the GTE floor with
`native_terrain_export.flatten_floor`: each native `FUNC_80010000` payload vertex gets an absolute world Y from the
same authored platform/ramp surface used by collision. The old displace-to-mean path remains available as
`--displace-visual` for regression/A-B evidence only.

For the canonical flat movie corridor (`--corridor --rise 0`), this means every native floor payload is a true flat
authored sheet at `world_y=-497`, not "LEVEL01 relief shifted to each payload's mean." Offline geometry proof on
`build/ABL_g3native_terrain.DAT`: 30 floor payloads / 2775 vertices; `max_payload_y_range_after=0` (pristine max was
3461); `max_abs_error_to_target_after=0`. Stats artifact: `build/p3_abs_geometry_stats.json`.

Official movie validation on the P3 build:
- command: `python3 tools/validate_g3_native_movie.py --shot-prefix g3nm_p3abs`
- result: `RENDER_C(OT)=0`, `FUNC_80010000=7303`, no plunge, Flik Y range `[-11681,5216]`
- screenshots: `build/g3nm_p3abs_*.png`
- debugger: DuckStation fork `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, launcher binary
  `build-release/bin/duckstation-qt` sha256 `3f4b981dda0f09ea3ef1e9ebc8319e3ab89424b3051dc9adb3212c8337993952`

Runtime pick evidence at the validator frame-5300 anchor is in `build/p3_abs_pick_validator_f5300.json` and
`build/p3_abs_pick_census_f5300.json`: the former 0x68D points `(300,105)` / `(310,82)` and upper-right sample
`(450,30)` return background at that anchor; the 0x68D backdrop layer remains absent. The broad bottom-of-frame floor
samples are dominated by a GP0(60) sprite layer in that view, so the geometry proof above is the stronger P3 evidence
for the native floor shape.

**P3 closure boundary.** This closes the displace-to-mean native-floor sheet problem for the current flat authored
corridor. It does not claim chunk-35 structural terrain removal or the small 0x604 dirt hard path; those remain
outside P3. P4 below closes the reproducible Blender profile authoring loop for this validated surface.

## P4 update (2026-07-06)

**P4 is closed for the current validated G3-native profile loop.** Added:
- `tools/abl_blender/export_g3_native_profile.py` — runs inside Blender and exports a JSON profile for the current
  G3-native build path.
- `tools/build_g3_native_from_blender.py` — project-side wrapper:
  `.blend -> g3_native_profile.json -> build_g3_native.py -> validate_g3_native_movie.py`.

Validation command:

```bash
python3 tools/build_g3_native_from_blender.py build/tier3_flatramp.blend --validate --shot-prefix g3nm_p4loop
```

Exported profile: `build/g3_native_profile.json` (`corridor=true`, `rise=0`, `pa_rt=2144`, `flatten_blocks=true`,
`suppress_grass=true`, `suppress_horizon=false`, `displace_visual=false`). Report artifact:
`build/g3_native_author_report.json`. Source `.blend` hash:
`779654f370884a572d03d874d80837711385ea0fcd2ec86f322121673f0f2cd3`.

Movie validation result from the wrapper: `RENDER_C(OT)=0`, `FUNC_80010000=7293`, no plunge, Flik Y range
`[-9122,5216]`; 12 screenshots written as `build/g3nm_p4loop_*.png`. Built artifact hashes match the P3 canonical
disc: bin `fb0e1656b709f39ba9039d4cf97143ddb1e18646264974169fca92b7c3a72907`, terrain DAT
`2b75a4f2936d0f5589c4dd80cb1f1eed88c48f56feb7fc1f7450ee4dfb722392`, collision RAW
`ca5e48b436ae5f1480031f634e5ddd2ff379b361e4e3c270401e84c48dfee1c2`, staged EXE
`5d58da1776987853afbfd0e8b10940c0b5424e6a71eac350b30648dd0d2b7b1e`.

**P4 closure boundary.** This closes the reproducible Blender profile -> build -> validate loop for the flat
full-movie G3-native corridor. It does not yet mean arbitrary Blender sculpted terrain has matching block-sector
collision across the movie. That is the next authoring expansion, not part of the closed P4 gate.

## P5/P6/P7 update (2026-07-06)

**P5 is closed for Blender-authored gentle heightfields.** New/changed tooling:
- `tools/abl_blender/g3_native_heightfield_scene.py` — creates the validated P5 fixture scene with a real editable
  `G3NativeHeightfield` mesh. The mesh uses `bx=game_x/256`, `by=game_z/256`, `bz=-runtime_delta_y/256`.
- `tools/abl_blender/export_g3_native_profile.py` — when scene prop `abl_g3_surface=heightfield`, exports the mesh
  grid to a runtime-delta `surface_json`.
- `tools/build_g3_native_from_blender.py` — passes `surface_json` through to `build_g3_native.py`.
- `tools/build_g3_native.py --surface-json` — loads `runtime_delta_y`, `file_delta_y`, or `absolute_file_y` grids.
  Runtime-delta mode maps visual file Y as `base_y + dy/32` and collision as `pa_rt + dy`, preserving the P3/P4
  `base_y=-497 ↔ collision=2144` anchor and the native visual x32 quirk.

Validation command:

```bash
flatpak run org.blender.Blender --background --python ~/Downloads/ABL/tools/abl_blender/g3_native_heightfield_scene.py -- \
  ~/Downloads/ABL/build/g3_native_heightfield.blend --amp-runtime 256 --nx 32 --nz 64
python3 tools/build_g3_native_from_blender.py build/g3_native_heightfield.blend --validate \
  --shot-prefix g3nm_p5height --profile build/g3_native_p5_profile.json \
  --surface-out build/g3_native_p5_surface.json --report build/g3_native_p5_report.json
```

P5 surface: `build/g3_native_p5_surface.json`, mode `runtime_delta_y`, grid `33x65`, runtime `dy=[-196,256]`.
Movie validation: `RENDER_C(OT)=0`, `FUNC_80010000=7293`, no plunge, Flik Y range `[-10017,5374]`, screenshots
`build/g3nm_p5height_*.png`. Report artifact: `build/g3_native_p5_report.json`. Hashes:
- source blend `build/g3_native_heightfield.blend`: `2f23a951dab3917307a31462bfcca568f881689c6d59742bcef0ad0e7c6cd111`
- surface JSON: `b68fba1446f015ce9b92479924c7d3d98e15fb414de366f0d7737b8c8c94fa23`
- built bin: `e64805aa48d715f83e8e1dd0bd04b27c87d894864031442a7ad74fc9dbbefd79`
- terrain DAT: `ed289284fe6c45b18978fae29765b9a17c9a0ac081af15b21a75202e7caac81c`
- collision RAW: `457bac9aafbdf5f7d0d25d24d7c3d23e4ca6c28138f35d2bc1596c4d78faba1b`

**P5 closure boundary.** This is a validated non-flat heightfield path, not arbitrary topology. It does not yet cover
vertical walls, overhangs, multi-payload arbitrary authored meshes, or steep surfaces whose block-sector seams exceed
the gentle-heightfield regime.

**P6 is closed to the safe boundary after a fresh current-build check.** New tool:
`tools/report_g3_native_residuals.py`. It verifies the two safe P2 suppressors on the P5 build and writes
`build/g3_native_p6_residual_report.json`. Results:
- RAW chunk 66 local `0x134+0x0e` sentinel is `-1` (0x663 grass/mound source suppressed).
- `FUNC_8003E928` staged EXE bytes at `SCUS_942.88+0x2F128` are `08 00 E0 03 00 00 00 00` (`jr ra; nop`).
- Hard residuals not baked: chunk-34/35 structural terrain (load-wedging structural edits) and texpage-0x604 dirt
  via `FUNC_80014B04` (prior deterministic live A/B only reduced samples 2→1; render/list levers are Flik-shared).

**P7 is closed for offline authoring regressions.** New tool: `tools/regress_g3_native_authoring.py`.
It verifies:
- `runtime_delta_y` surface JSON maps to visual `dy/32` and collision `dy`.
- the wrapper command contains `--planes`, `--surface-json`, `--flatten-blocks`, and safe suppressors.
- the wrapper does not silently add `--displace-visual` or reference Track-A/Tier-3 OT tooling.

Verification run:

```bash
python3 -m py_compile tools/build_g3_native.py tools/build_g3_native_from_blender.py \
  tools/abl_blender/export_g3_native_profile.py tools/abl_blender/g3_native_heightfield_scene.py \
  tools/report_g3_native_residuals.py tools/regress_g3_native_authoring.py
python3 tools/report_g3_native_residuals.py --report build/g3_native_p6_residual_report.json \
  --author-report build/g3_native_p5_report.json
python3 tools/regress_g3_native_authoring.py
```

## P8/P9/P10 update (2026-07-06)

This pass moved the work from "terrain patch" toward a constrained, usable Track-B custom-level scene. It does not
pretend arbitrary topology is solved; it makes the proven heightfield path authorable as a level-like Blender scene.

**P8 scene contract.** `tools/abl_blender/export_g3_native_profile.py` now exports `level_meta`:
- `Spawn` / `G3Spawn` empty -> `{x,z,runtime_delta_y,radius}`
- `Goal` / `G3Goal` / `Exit` empty -> `{x,z,runtime_delta_y,radius}`
- coordinate convention remains `bx=game_x/256`, `by=game_z/256`, `bz=-runtime_delta_y/256`

`tools/abl_blender/g3_native_heightfield_scene.py` now creates a fixture with a real `G3NativeHeightfield` mesh,
`Spawn`, `Goal`, and a native material property block.

**P9 offline authoring gate.** New tool: `tools/validate_g3_native_scene.py`. It reads a profile + surface JSON and
fails before disc build if:
- the surface is missing,
- spawn/goal are missing or outside the surface footprint,
- no grid path exists from spawn to goal under the allowed adjacent runtime step (`--max-step`, default 512).

`tools/build_g3_native_from_blender.py --check-scene` runs that gate between Blender export and disc build, and writes
`scene_report` into the author report.

**P10 native material/style controls.** New/changed tooling:
- `tools/native_terrain_export.py::style_floor()` — size-preserving native floor style pass. It can set vertex
  `attr` color, quad UVs, low texpage bits, or full `texpage_ctrl` without payload growth or relocation.
- `tools/abl_blender/export_g3_native_profile.py` reads `abl_g3_color`, `abl_g3_uv`, `abl_g3_texpage`, and
  `abl_g3_texpage_ctrl` from the heightfield object or its active material and writes them to `surface_json`.
- `tools/build_g3_native.py --surface-json` applies that material block after the P3 absolute height set.

Integrated validation command:

```bash
flatpak run org.blender.Blender --background --python ~/Downloads/ABL/tools/abl_blender/g3_native_heightfield_scene.py -- \
  ~/Downloads/ABL/build/g3_native_level_scene.blend --amp-runtime 256 --nx 32 --nz 64
python3 tools/build_g3_native_from_blender.py build/g3_native_level_scene.blend --check-scene --validate \
  --shot-prefix g3nm_p8p10 --profile build/g3_native_p8_profile.json \
  --surface-out build/g3_native_p8_surface.json --scene-report build/g3_native_p8_scene_report.json \
  --report build/g3_native_p8_author_report.json
```

Results:
- scene gate: PASS, path nodes `63`, `dy=[-196,256]`, max adjacent runtime step `20`, material present in fixture.
- build: 30 native floor payloads absolute-heighted and styled (`color=0x88705c`, UVs `0xc03f,0xc000,0xff00,0xff3f`)
  size-preserving; 85 flat sectors got per-face blocks; 86 block sectors flattened.
- movie validation: `RENDER_C(OT)=0`, `FUNC_80010000=7299`, no plunge, Flik Y range `[-11553,5373]`, screenshots
  `build/g3nm_p8p10_*.png`.
- P6 residual check on the same build: `build/g3_native_p8_residual_report.json`, status `closed_to_safe_boundary`.

Hashes:
- source blend `build/g3_native_level_scene.blend`: `46bf8faf3bce720d683219f8f38e65a60354ce38610288852749abf003681ca9`
- surface JSON: `9e54c667a37fcd0191c7e8d115bb228fc1c1eeb46bfb70364147747c0ecfd556`
- scene report: `5ab07645066bfcd0d21ad05201d837e00cc2f6f5c891b13d424f666427bda3c1`
- built bin: `9f7eaf9656f0ba10133ffc67748d5f058ab2bf4718afede5be3d9d4787688d5d`
- terrain DAT: `c2ed8f34158470148ef79d96ea74d7fa44035aa7ecf7c261b1cf32293016e71a`
- collision RAW: `457bac9aafbdf5f7d0d25d24d7c3d23e4ca6c28138f35d2bc1596c4d78faba1b`

**P8-P10 closure boundary.** This is now a constrained Track-B Blender custom-level vertical slice:
heightfield terrain + spawn/goal metadata + offline path gate + native material styling + full-movie runtime proof.
P11 closes the runtime spawn/goal half below. This still does not implement arbitrary mesh collision,
walls/overhangs, custom object placement, or the chunk-35/0x604 hard residual breakthrough.

## P11 update (2026-07-06)

P11 turns the P8 `level_meta` metadata into actual gameplay behavior for the G3-native Track-B build.
It is now frozen as the baseline Blender custom-level slice. Use `templates/g3_native_p11_baseline.blend` as the
editable template and `tools/g3_native_p11_build_validate.sh <blend>` as the single build/boot/reach-goal workflow.
The exact authoring contract is in `docs/G3_NATIVE_P11_BASELINE.md`.

**Runtime hook.** `tools/build_g3_native.py --level-meta-json <profile>` now composes an EXE patch with the P2
horizon suppressor instead of overwriting it. The patch replaces the player-update post-integrator call site
`0x800495D0` with a jump to the resident cave at `0x800810C0`, replays the displaced `jal 0x80037A38`, then applies:

- spawn-once from `level_meta.spawn`: file-space X/Z are written to Flik as runtime `<<5`; Y is
  `pa_rt + runtime_delta_y + 3200`, matching the movement-integrator body offset.
- goal trigger from `level_meta.goal`: simple runtime XZ AABB using the exported radius; on hit it sets a P11
  `goal_flag` and replicates the LEVEL01 type-1 exit body (`0x800823A0=1`, `0x80082470=23`,
  `FUNC_80050994(58,0)`).
- LEVEL01 gate by loaded DAT marker words, not exact `DAT_BASE`. Live P11 autolayout proved `DAT_BASE` was
  `0x80166CE8`, while older notes used `0x801607F8`; exact-base gating missed the hook. The stable markers are
  `DAT+0=0x0000000B`, `DAT+4=0x003F0046`, `DAT+0x4600=0xC0080000`. Do not compare relocated fields such as
  `DAT+0x4604`; runtime relocation changed that payload offset into an absolute pointer.
- P11 flags use `0x8007F2FC`/`0x8007F300`/`0x8007F304` (`init`, `goal`, magic `0x47335031`). The validator ignores
  dirty boot values unless the magic is present.

**Validation.** `tools/validate_g3_native_movie.py` now accepts `--runtime-patch-report` and `--expect-goal`.
`tools/build_g3_native_from_blender.py --validate` passes those automatically when the runtime patch report exists.

Validated command:

```bash
python3 tools/build_g3_native_from_blender.py build/g3_native_level_scene.blend --check-scene --validate \
  --shot-prefix g3nm_p11_spawn_goal --profile build/g3_native_p11_profile.json \
  --surface-out build/g3_native_p11_surface.json --scene-report build/g3_native_p11_scene_report.json \
  --report build/g3_native_p11_author_report.json
```

Results:
- scene gate: PASS, path nodes `55`, `dy=[-196,256]`, max adjacent runtime step `20`.
- runtime patch: cave `0x800810C0..0x800812D4`, goal flag `0x8007F300`.
- cold-boot replay: runtime spawn hook at frame ~4330 wrote exact expected Flik position
  `(197088,5344,492896)`, `magic=0x47335031`.
- traversal to authored goal: runtime goal hook at frame ~5610 with Flik at `(-243502,-9089,-186817)`.
- renderer criteria: `RENDER_C(OT)=0`, `FUNC_80010000=4035`, no plunge; runtime spawn PASS; runtime goal PASS.

Hashes:
- baseline template `templates/g3_native_p11_baseline.blend`:
  `74af6732c61c6e34ffe3f4b63fe8256603fd9f7358893beb693880f6ac8ee3f8`
- profile JSON: `4fc51f72aa6ec10b1c305ec5da2dbad9349ad1fb5b5fdcd45a818145a4baf17a`
- surface JSON: `7808ad9443f834b9147bcf97f645d03a3b6589fad834d5ab78ed6a8b61129c76`
- scene report: `53571a89f23fa4f752fc9a1080a7d722cea607fea52b42bb867788551d374d5b`
- runtime patch report: `dc765fc5894330db69d15b879a3d95e0137fd84e8e155848984b9c0834459b4d`
- staged EXE: `185861a9b8fa0c57e408f9a82f4d9f7ec39810914336f55fcb5f4868085676ef`
- built bin: `7e0ca3f5bf7df808f9a16fd179c5de40520761ed523f0398003680c053f8b93b`
- effective horizon suppressor: `false`; `FUNC_8003E928` remains original prologue `27bdffa8 8f830404`
- terrain DAT: `2d45bcb2a42d17ac7b5f42898596d706234377d3fc58c9020930dc4d9d9ee8bb`
- collision RAW: `8b8b871554b49b432071e98910a87b88fcb6dbf2ed4507b2e098b772f66cf69c`

**Menu-safe rebuild verification (2026-07-06).** After the horizon suppressor regression fix, reran
`tools/g3_native_p11_build_validate.sh templates/g3_native_p11_baseline.blend` in the current workspace. Result: PASS,
built bin hash `7e0ca3f5bf7df808f9a16fd179c5de40520761ed523f0398003680c053f8b93b`, cue hash
`ae55fdb235f6281a0e14e749c10121191aad9879af4fd957154146680f595ea6`, staged EXE hash
`185861a9b8fa0c57e408f9a82f4d9f7ec39810914336f55fcb5f4868085676ef`, and `FUNC_8003E928` remained original prologue
`27bdffa8 8f830404`. Report JSON hashes are path-sensitive because they include absolute paths.

**Stress edit verification (2026-07-06).** Before starting new feature work, P11 was stress-tested from a fresh
detached worktree at `71f212f`. The source tree was clean before mutation; the full ignored `REBUILD/` extraction
was copied locally because `build_autolayout_disc.py` runs `mkpsxiso` against the full
`REBUILD/abl_autolayout.xml` manifest. The test intentionally edited only P11-authored data in
`templates/g3_native_p11_baseline.blend`:

- heightfield wave changed; exported surface `dy=[-428,388]`, max adjacent runtime step `30`.
- `Spawn` moved to file-space `(6415,15147)`, `runtime_delta_y=64`.
- `Goal` moved to file-space `(-6900,-5300)`, `runtime_delta_y=-137`.
- material color changed to `0x4f8f64`.

Validation command:

```bash
G3NATIVE_SHOT_PREFIX=g3nm_p11_stress tools/g3_native_p11_build_validate.sh templates/g3_native_p11_baseline.blend
```

Result: PASS. Offline scene gate found a 52-node walkable path. Runtime spawn hook wrote exact Flik position
`(205280,5408,484704)` at frame ~4330. Runtime goal hook fired at frame ~5610. Renderer criteria passed:
`RENDER_C(OT)=0`, `FUNC_80010000=3961`, no plunge. Stress build hashes:

- edited template: `ebe1da5ac45fcf8a76afcf5fe5972576ce19c942d1e89116ac395f34c34b6771`
- surface JSON: `65fa391f8b7258cd49181bacb0ea191580d7ae1717a44256714670fbf83da009`
- runtime patch report: `fd11a70a96bea86cda3241c422a91ac7b034b4148cac515efcc55ab2165437f1`
- built bin: `662693d8cc7067e514a1416a9c173520d2c1267de4949bcf538c62785c853fbe`
- terrain DAT: `feccd146ea95d3154d20f13a0fddbb0eb6dae48cea56ea6c4face80374e43fca`
- collision RAW: `1cf38ec02f4776e25f751bee669d9953e15c2df3bd395ab166b70526bf6bb275`
- screenshots: `build/g3nm_p11_stress_01_f4410.png` through `build/g3nm_p11_stress_07_f5450.png`

Clean-source packaging lesson: the P11 path must track its Python helper sources (`floor_source_map.py`,
`native_mesh_codec.py`, `edit_collision_sector.py`, `native_dat_inject.py`, `build_autolayout_disc.py`) but must not
commit game-derived local inputs under `REBUILD/`, `DAT/`, or generated build/screenshots.

**P12 marker-trigger verification (2026-07-06).** Added one optional Blender-authored marker trigger without starting
the broader native collectible/object path. Implementation:

- `tools/abl_blender/export_g3_native_profile.py` exports `level_meta.marker` from one Empty named `Marker` or
  `G3Marker`.
- `tools/validate_g3_native_scene.py` rejects a marker outside the heightfield footprint.
- `tools/build_g3_native.py` allocates `marker_flag=0x8007F308` and adds a non-visible X/Z AABB check to the existing
  resident player-update hook at `0x800495D0`.
- `tools/build_g3_native_from_blender.py --validate` adds `--expect-marker` automatically when the runtime patch
  report contains a marker, and `tools/validate_g3_native_movie.py` fails unless the marker flag is observed.

Authoring rule: add one Empty named `Marker` or `G3Marker`; location uses the same P11 coordinates
(`X=game_x/256`, `Y=game_z/256`, `Z=-runtime_delta_y/256`), and `empty_display_size * 256` is the file-space trigger
radius. The marker does not draw and does not affect native pickup counters.

Validation fixture: `build/g3_native_marker_scene.blend` was made from the P11 baseline template with one marker at
file-space `(1340,14233)`, display size `5.0`, exported radius `1280`. Command:

```bash
python3 tools/build_g3_native_from_blender.py build/g3_native_marker_scene.blend --check-scene --validate \
  --shot-prefix g3nm_p12_marker --profile build/g3_native_marker_profile.json \
  --surface-out build/g3_native_marker_surface.json --scene-report build/g3_native_marker_scene_report.json \
  --report build/g3_native_marker_author_report.json --out build/ABL_g3native_marker
```

Result: PASS. The unchanged P11 baseline command was run immediately before and also passed. Marker runtime proof:

- marker runtime AABB: `(42880,455456)`, radius `40960`, flag `0x8007F308`
- marker hook fired at frame ~4570 with Flik `(34330,-9795,464956)`
- goal hook fired at frame ~5610
- renderer criteria: `RENDER_C(OT)=0`, `FUNC_80010000=4035`, no plunge
- runtime spawn / marker / goal criteria: PASS

Hashes:

- marker source blend: `1a81a823b56f04a38dfd5aac05dce1e69f7fd6bc76b18c0f5d9ba6dd3d34fc6a`
- marker profile JSON: `195d971cb9f2ad2df2ef4711aa2efa1c4195df4c0a718dda952b6387c5458c9a`
- marker runtime patch report: `006e1af90e71147e700f9b7076c991c47b3a0331aaa6e17cda3bf742bd764868`
- marker built bin: `b06c5fa8823de2193851a57504e14660b17db4a2696bef2c3e7e5a36cfe17259`
- screenshots: `build/g3nm_p12_marker_01_f4410.png` through `build/g3nm_p12_marker_07_f5450.png`

**P13 visible marker-indicator verification (2026-07-06).** Built on P12 by making the authored marker visible as a
native floor-tint indicator while keeping the existing invisible trigger flag as the runtime truth.

Implementation:

- `tools/abl_blender/export_g3_native_profile.py` now exports `level_meta.marker.visual` by default:
  `kind=native_floor_tint`, default color `0x40e0ff`, radius equal to the marker Empty radius.
- Marker Empty custom props: `abl_g3_marker_color` overrides the tint color; `abl_g3_marker_visual=false` preserves
  the P12 invisible-only trigger.
- `tools/native_terrain_export.py::style_marker_floor_tint` decodes native floor payloads, finds primitives whose
  X/Z bbox overlaps the marker AABB, and recolors only their vertex attrs. Topology, UVs, texpage, payload size, and
  node relocation are unchanged.
- `tools/build_g3_native.py` applies that DAT pass after the global material pass and writes the visual report into
  the existing runtime patch report.
- `tools/validate_g3_native_movie.py` prints the DAT visual report, requires at least one tinted primitive when a
  marker visual exists, and captures a marker-frame screenshot when the marker flag fires.

Validation command:

```bash
python3 tools/build_g3_native_from_blender.py build/g3_native_marker_scene.blend --check-scene --validate \
  --shot-prefix g3nm_p13_marker_visual --profile build/g3_native_marker_profile.json \
  --surface-out build/g3_native_marker_surface.json --scene-report build/g3_native_marker_scene_report.json \
  --report build/g3_native_marker_author_report.json --out build/ABL_g3native_marker
```

Result: PASS. The unchanged P11 baseline command was run immediately before and also passed. Runtime proof:

- marker visual report: 4 payloads, 42 native floor primitives, 72 vertices tinted, `fallback_nearest=false`
- marker runtime AABB: `(42880,455456)`, radius `40960`, flag `0x8007F308`
- marker hook fired at frame ~4570 with Flik `(34330,-9795,464956)`
- marker-frame screenshot: `build/g3nm_p13_marker_visual_marker_f4570.png`
- goal hook fired at frame ~5610
- renderer criteria: `RENDER_C(OT)=0`, `FUNC_80010000=4035`, no plunge
- runtime spawn / marker visual / marker trigger / goal criteria: PASS

Hashes:

- marker profile JSON: `a8069e4326e69f91294a904d1dd3e923c70b8407874e6aa2b1ae44985bfe5317`
- marker runtime patch report: `5c6ba1384f853c9737c79f67325bd1c0faf96a1a3d2ef1bbc519d4cc6bdd0903`
- marker built bin: `9089fe48f0745cf623788596c13aa20edfd76c5c5c2c1299ba0dd7e4c1315479`
- marker-frame screenshot: `199ad184944b7ff61cfc27682340f380af14bf41427e783e3a96fffbc70cfd64`

Current limitation: this is a floor tint, not a separate prop mesh or native collectible. The footprint is governed
by native floor primitive granularity and vertex sharing, so it can be visibly larger than the trigger AABB. The
P12 marker flag remains the authoritative in-game trigger signal.

**P14 platform/ramp/platform validation (2026-07-06).** Added a deliberately authored Track-B heightfield validation
scene generator and proved it through the current P11-P13 workflow.

Generator:

- `tools/abl_blender/g3_native_platform_ramp_scene.py`
- coordinate convention remains `bx=X/256`, `by=Z/256`, `bz=-runtime_delta_y/256`
- final fixture parameters: `--rise-runtime 512 --goal-x 2418 --goal-z 15939 --marker-x 4300 --marker-z 15670
  --marker-size 10 --nx 64 --nz 128 --material-color 0x4f8f64 --marker-color 0xf0d040`

Validation command:

```bash
flatpak run org.blender.Blender --background \
  --python ~/Downloads/ABL/tools/abl_blender/g3_native_platform_ramp_scene.py -- \
  ~/Downloads/ABL/build/g3_native_platform_ramp_scene.blend \
  --rise-runtime 512 --goal-x 2418 --goal-z 15939 --marker-x 4300 --marker-z 15670 \
  --marker-size 10 --nx 64 --nz 128 --material-color 0x4f8f64 --marker-color 0xf0d040

python3 tools/build_g3_native_from_blender.py build/g3_native_platform_ramp_scene.blend --check-scene --validate \
  --shot-prefix g3nm_p14_platform_ramp --profile build/g3_native_platform_ramp_profile.json \
  --surface-out build/g3_native_platform_ramp_surface.json \
  --scene-report build/g3_native_platform_ramp_scene_report.json \
  --report build/g3_native_platform_ramp_author_report.json --out build/ABL_g3native_platform_ramp
```

Result: PASS.

- authored surface: `65x129`, `dy=[-512,0]`, max adjacent runtime step `76`, material `0x4f8f64`
- platform A spawn: file `(6159,15403)`, `runtime_delta_y=0`; runtime exact `(197088,5344,492896)`
- ramp marker: file `(4300,15670)`, `runtime_delta_y=-245`, radius `2560`, tint `0xf0d040`; marker fired at
  frame ~4410, screenshot `build/g3nm_p14_platform_ramp_marker_f4410.png`
- platform B goal: file `(2418,15939)`, `runtime_delta_y=-512`; goal fired at frame ~4490
- marker visual report: 6 payloads, 107 native floor primitives, 174 vertices tinted, `fallback_nearest=false`
- renderer criteria: `RENDER_C(OT)=0`, `FUNC_80010000=668`, no plunge

Hashes:

- source blend: `d98270fabdea6089fbedd0047c0737f412d48bc24e8842f91b491c19dc35f9ce`
- surface JSON: `e15baf4aee7e26d69ab63060a12876eed4be263d3be62eb934632c5e24547fe9`
- runtime patch report: `6043d4e1d6f0c1d116fa915213ac98d7cdd475977ed3452a8d049dbe3971128d`
- built bin: `0fef90056f8dee2d2c27e7c5e3c79cd4f55be1e35d07e8a8cb172ab0261a3f59`
- marker-frame screenshot: `e1cdde3eff49f73cadc7797d1e2207c4035d39662f2633e17f294430fbdb24a7`
- effective horizon suppressor: `false`; `FUNC_8003E928` remains original prologue `27bdffa8 8f830404`

Important caveat: two larger/original-route ramp attempts were rejected before this passing fixture because the
stock replay drifted off the authored goal, and one late-drift run eventually plunged after missing the goal. The
passing fixture intentionally uses a short, movie-stable ramp lane. Do not generalize this to arbitrary long ramps or
arbitrary topology yet.

## Future P candidates

- **P15 — Arbitrary topology / steep terrain.** Extend past gentle heightfields into authored meshes with walls,
  overhang rejection, multi-payload chunking, and collision rules for steep surfaces.
- **P16 — Separate visible native objects / collectibles.** Promote the marker floor-tint path into real type-`0x3f`
  relocation or append for visible pickups/objects, with counter-safe validation.
- **P17 — Residual hard-path breakthrough.** Only revisit chunk-35/0x604 if a new source-level, Flik-separable,
  cold-boot-safe edit is found; do not blanket-edit chunk-35.

## P14 regression correction — horizon suppressor is not baseline-safe (2026-07-06)

Manual boot screenshots exposed a regression in the P2/P14 build contract: `--suppress-horizon` globally stubs
`FUNC_8003E928`, and that function is also used by the level-select/menu backdrop. The brown/missing level-select
background is therefore caused by our EXE patch, not by native GTE terrain authoring.

Corrected rule:

- keep `--suppress-grass` as the safe P2 source-level suppressor;
- keep `--suppress-horizon` available only as an explicit A/B experiment;
- the Blender one-command wrapper ignores profile `suppress_horizon=true` unless
  `--allow-global-horizon-suppressor` is supplied;
- generated P11/P14 scenes now write `abl_g3_suppress_horizon=false`;
- author reports include `profile_requested_suppress_horizon`, `global_horizon_suppressor_allowed`, and
  `effective_suppress_horizon`.

This reopens/downgrades the old "P2 closed" wording: P2 is closed for safe grass/mound source suppression and for
movie-path A/B evidence, but the horizon/backdrop EXE stub is not safe for manual/playable Track-B discs until it is
runtime-gated to LEVEL01 gameplay or replaced by a source-level edit that leaves menu backdrops alone.

## P15 collision residual correction — old LEVEL01 collision is bounded, not solved (2026-07-06)

Manual play exposed a second overstatement: the P11-P14 Track-B slice does **not** yet own a clean authored collision
world. It owns a validated authored route over LEVEL01's chunk-32 sector structure.

What the current working path actually does:

- Flat selected chunk-32 sectors get new authored per-face mesh blocks (`heightfield_collision.mesh_block` +
  `emit_collision_addblock.add_block`).
- Existing selected block sectors are flattened/reheighted in place (`emit_collision_reheight.flatten_block`), which
  keeps LEVEL01's native small X/Z plane footprints so the fine candidate selector still works while Flik moves.
- Selected malformed/non-mesh relocation-region block sectors `178..188` are skipped by the current decoder/emitter.
- Chunk-33 and other runtime collision sources are outside this Track-B chunk-32 emitter path.

New audit tool: `tools/report_g3_native_collision_coverage.py`. It compares pristine `REBUILD/files/LEVEL01/LEVEL.RAW`
against the built `build/ABL_g3native_collision.RAW`, accounts for the relocated sector-array offset after `add_block`,
and labels each chunk-32 sector as authored added-block, flattened retained-footprint block, skipped malformed block,
sunk outside-region sector, or untouched old collision. It is an offline source audit; DuckStation validation is still
required for physics.

P14 retile experiment (FAILED, not baseline):

```bash
python3 tools/build_g3_native.py --planes --out build/ABL_g3native_platform_ramp_retile \
  --pa-rt 2144 --rise 0 --corridor --retile-blocks --suppress-grass \
  --surface-json build/g3_native_platform_ramp_surface.json \
  --level-meta-json build/g3_native_platform_ramp_profile.json

python3 tools/validate_g3_native_movie.py --cue build/ABL_g3native_platform_ramp_retile.cue \
  --shot-prefix g3nm_p14_retile \
  --runtime-patch-report build/ABL_g3native_platform_ramp_retile_runtime_patch.json \
  --expect-goal --expect-marker
```

Build result: 85 flat sectors got mesh blocks; 86 block sectors were RETILED; sectors `178..188` skipped. Runtime
result: FAILED goal. Flik stayed pinned at spawn `(197088,5344,492896)`; renderer checks still passed
(`RENDER_C=0`, `FUNC_80010000=69`, no plunge), but traversal did not happen. Conclusion: size-preserving footprint
retile is structurally useful evidence but cannot replace `flatten_block` yet.

P14 sink-outside experiment (PASS, partial mitigation only):

```bash
python3 tools/build_g3_native.py --planes --out build/ABL_g3native_platform_ramp_sink \
  --pa-rt 2144 --rise 0 --corridor --flatten-blocks --sink-outside-collision 200000 \
  --suppress-grass --surface-json build/g3_native_platform_ramp_surface.json \
  --level-meta-json build/g3_native_platform_ramp_profile.json

python3 tools/validate_g3_native_movie.py --cue build/ABL_g3native_platform_ramp_sink.cue \
  --shot-prefix g3nm_p14_sink \
  --runtime-patch-report build/ABL_g3native_platform_ramp_sink_runtime_patch.json \
  --expect-goal --expect-marker
```

Runtime result: PASS. Exact spawn `(197088,5344,492896)`, marker fired frame ~4410 at
`(172150,5183,487712)`, goal fired frame ~4490 at `(101842,27229,490689)`, `RENDER_C=0`,
`FUNC_80010000=672`, no plunge. P2 residual check on this build is still closed to the safe boundary:
grass/mound source suppressed, horizon stub off.

Current sink-audit artifact hashes:

- `build/ABL_g3native_platform_ramp_sink.bin`:
  `0c81c211ee6996a097a8492b8661b7840b4becce98956335adc975323c82aad1`
- `build/ABL_g3native_platform_ramp_sink.cue`:
  `58f78077c6158389540f37fa1d487bf01c9ebfc99a6c70f5c72e5b87327f4c40`
- runtime patch report:
  `ba4cd111565d5e32652960e5c82ccbeed606099be79e96f3f8d394dc3eba8d9e`
- collision coverage report:
  `9cc25dc81ab6c2975fcfeb2dca4fbf0eaf4b5ec5d7af5bcd1da7161d0b44a344`
- residual report:
  `2cc60763c7086bf45d008396b8676a6a2f959c804f3393d5fb57f1588d5632dc`

Coverage report for the passing sink build:

```bash
python3 tools/report_g3_native_collision_coverage.py \
  --built-raw build/ABL_g3native_collision.RAW \
  --profile build/g3_native_platform_ramp_profile.json \
  --report build/g3_native_platform_ramp_sink_collision_coverage.json
```

Result status: `not_a_clean_authored_collision_world`.

- `authored_added_block_on_pristine_flat_sector`: 85
- `flattened_old_block_retained_footprints`: 86
- `selected_malformed_block_left_as_old_collision`: 11 (`178..188`)
- `sunk_outside_author_region`: 7
- surface nodes covered by added authored blocks only: `0.277`
- surface nodes covered by added or flattened retained-footprint blocks: `0.586`

Correct conclusion: the sink build reduces off-route stock floor catches and keeps the authored P14 route working,
but it does not remove the old selected block footprints that make arbitrary Blender collision unreliable. The next
real collision frontier is either (a) make retiled/replaced block footprints walkable in-game, or (b) move Track-A's
known-good per-face collision logic over the GTE-authored heightfield/mesh while keeping Track-B rendering.

## P16 collision selector correction — replacement works locally; retile is the bad path (2026-07-06)

P16 focused only on chunk-32 Track-B collision. No Track-A renderer, no chunk-35/0x604/object work, and no baseline
promotion of `--retile-blocks` or `--sink-outside-collision`.

New opt-in tooling:

- `tools/build_g3_native.py --retile-sector N`
- `tools/build_g3_native.py --replace-sector N`
- `tools/trace_g3_native_collision_selector.py`
- per-disc build snapshots: `<out>_collision.RAW`, `<out>_terrain.DAT`, `<out>_SCUS_942.88`

The older "replacement is rejected by selection" diagnosis is superseded. With per-disc RAW traces and cold-boot
movies:

- control P14/P15 build still passes: exact spawn `(197088,5344,492896)`, marker frame ~4410, goal frame ~4490,
  `RENDER_C=0`, `FUNC_80010000=672`, no plunge.
- `--retile-sector 100` passes and reaches `response_8003573c` for sector 100.
- `--retile-sector 99` is the minimal bad retile case: it passes sector-99 d1/d0 and reaches response at frame 4355,
  then Flik is thrown off-route by frame 4360 (`Z=468202` versus control `Z=492984`).
- control sector 99 is selected but point-in-poly rejects target planes (`point_in_poly_rejection`), so the native
  retained footprint correctly avoids catching the spawn route there.
- `--replace-sector 99`, `--replace-sector 100`, and paired
  `--replace-sector 99 --replace-sector 100` all pass cold-boot traversal, marker, and goal with native GTE active.
- all-sector `--retile-blocks` still fails pinned at spawn; trace status for sector 100 is
  `candidate_not_iterated_by_80035280` because sector 100 appears in sampled candidates but no d1/d0/PIP/response
  events fire after spawn.

P16 conclusion: native block replacement is not globally rejected by the selector. The current blocker is the
size-preserving retile path, which preserves old group/record layout while filling new X/Z cells and can turn a
candidate that should be rejected at point-in-poly into an active response. Size-changing `replace_block` with a
fresh `heightfield_collision.mesh_block` is locally walkable for the spawn pair sectors 99/100, but remains opt-in
until expanded sector-by-sector with cold-boot traversal.

Evidence doc: `docs/G3_NATIVE_P16_COLLISION_SELECTOR.md`.

## P17 route-scale collision replacement — validated for the movie route (2026-07-06)

P17 scaled P16's local `--replace-sector` success to the retained block-sector footprints actually used by the
validated platform/ramp spawn -> marker -> goal route. This is still collision-only: old LEVEL01 visual terrain or
backdrop residuals are separate and are not collision proof.

New route evidence tool: `tools/trace_g3_native_route_sectors.py`. It cold-boots an isolated DuckStation instance,
replays the movie, maps runtime candidate plane pointers back to built chunk-32 sectors using the runtime sector
table, and emits route candidate/response sectors plus replacement targets. `tools/report_g3_native_collision_coverage.py`
now distinguishes size-changing `replaced_authored_block` from unsafe size-preserving retile.

Control build:

```bash
python3 tools/build_g3_native.py --planes --out build/ABL_g3native_p17_control \
  --pa-rt 2144 --rise 0 --corridor --flatten-blocks --suppress-grass \
  --surface-json build/g3_native_platform_ramp_surface.json \
  --level-meta-json build/g3_native_platform_ramp_profile.json
```

Control trace result:

- route retained replacement targets: `93, 99, 100, 107, 108`
- response sectors among those targets: `93, 99, 100`
- malformed route sectors: none

Expansion was one sector at a time using repeated `--replace-sector` flags, never retile or sink-outside:

- seed `99,100`: PASS
- add `108`: PASS
- add `93`: PASS
- final add `107`: PASS

Final build:

```bash
python3 tools/build_g3_native.py --planes --out build/ABL_g3native_p17_route_final \
  --pa-rt 2144 --rise 0 --corridor --flatten-blocks \
  --replace-sector 99 --replace-sector 100 --replace-sector 108 --replace-sector 93 --replace-sector 107 \
  --suppress-grass \
  --surface-json build/g3_native_platform_ramp_surface.json \
  --level-meta-json build/g3_native_platform_ramp_profile.json
```

Final validation: exact spawn `(197088,5344,492896)`, marker frame ~4410, goal frame ~4490 at
`(100658,24875,490713)`, `RENDER_C=0`, `FUNC_80010000=673`, no plunge, stayed inside the flatten play-box.

Final provenance:

- control replacement targets: `[93, 99, 100, 107, 108]`
- control targets replaced in final: `[93, 99, 100, 107, 108]`
- final retained route block sectors: `[]`
- final malformed route sectors: `[]`
- final candidate original-block sectors: `[99, 100, 107, 108]`
- final candidate added-flat sectors: `[29, 44, 45, 76, 77]`
- final response sectors: `[99, 100]`

Coverage on `build/ABL_g3native_p17_route_final_collision.RAW`: 85 authored added flat sectors, 5 replaced authored
block sectors, 81 remaining flattened retained-footprint block sectors outside this route proof, 11 malformed
selected sectors `178..188`, 7 untouched old outside-region block sectors.

Boundary: P17 validates route-scale replacement for the current movie route, not arbitrary free roam and not a clean
global collision world. The next collision frontier is expanding replacement beyond route-used sectors and handling
malformed/non-mesh sectors if they become relevant to a new route.

Evidence doc: `docs/G3_NATIVE_P17_ROUTE_COLLISION_REPLACEMENT.md`.

## P18 authored-area collision provenance sweep — blocked on replacement interaction (2026-07-06)

P18 preserved the P17 route-scale replacement result, added runtime collision provenance classification, and attempted
to expand `replace_block` beyond P17's route sectors. It did **not** produce a full authored-area replacement build.

New tracer behavior: `tools/trace_g3_native_route_sectors.py --p18-provenance --coverage-report ...` cold-boots the
disc, replays the movie, samples Flik XYZ and the player candidate list (`gp+0x57c`, `0x8009c230`, `0x80091718`),
maps response plane pointers back to chunk-32 sectors, classifies them with the coverage report, and explicitly marks
frames with no swept response as `no_swept_plane_response_observed`. Screenshots and old visible LEVEL01 terrain are
not collision evidence.

Runtime provenance facts:

- flattened control reports retained route sectors `[93, 99, 100, 107, 108]` and retained responses on `[93, 99, 100]`
- P17-final reports retained route sectors `[]` and only `replaced_authored_block` responses on `[99, 100]`
- best passing P18 expansion is `build/ABL_g3native_p18_bisect_b01_prefix_07.cue` with replacements
  `[0, 73, 87, 88, 89, 90, 91, 93, 99, 100, 107, 108]`

Sweep blocker:

- full B01 prefix `[0,73,87,88,89,90,91,92]` plus the P17 seed fails
- sector `92` alone with the P17 seed passes
- reduced failing interaction is `[0,73,92]` plus the P17 seed `[93,99,100,107,108]`
- `92+0` passes and `92+73` passes; `92+0+73` fails

Minimal failing disc: `build/ABL_g3native_p18_bisect_b01_interact_t02_0_73.cue`
(`.bin` hash `09533ee2140f8259bbda3ecc653a75a88efd609e5c547206488acdfa672445c0`). In the failing trace Flik remains
at `(197088,5344,492896)` from frame `4335` through `6530`; the sampled candidate list exists, but `d1/d0/PIP`,
`response_8003573c`, and `player_y_commit_80036cec` all have zero events after spawn. So this is an upstream
movement/update stall before `FUNC_80035280` iterates planes, not a retained old-collision response.

Evidence:

- `build/g3_native_p18_p17_preservation_manifest.json`
- `build/g3_native_p18_control_provenance.json`
- `build/g3_native_p18_p17final_provenance.json`
- `build/g3_native_p18_bisect_b01_results.json`
- `build/g3_native_p18_bisect_b01_interaction_results.json`
- `build/g3_native_p18_first_blocker_report.json`
- `docs/G3_NATIVE_P18_COLLISION_PROVENANCE_SWEEP.md`

P11 baseline still passes after the P18 tool changes. Baseline defaults remain unchanged; `--replace-sector-list`,
`--replace-sector`, retile flags, and sink-outside remain opt-in experiments.

## P19 minimal interaction movement-stall diagnosis — blocker moved upstream of collision (2026-07-06)

P19 added `tools/trace_g3_native_movement_stall.py` and compared the required cold-boot/movie matrix:

- P17 seed `[93,99,100,107,108]`
- P18 best prefix seed + `[0,73,87,88,89,90,91]`
- sector `92` alone with the P17 seed
- immediate control seed + `[0,73]`
- minimal failing interaction seed + `[0,73,92]`

Trace command:

```bash
python3 tools/trace_g3_native_movement_stall.py --trace-frames 90 --sample-every 1 --range-watch
```

Outcome B: trace-backed blocker, no fix promoted. The first divergent invariant is
`player_update_80048138_not_running`. In all four passing controls the movie playback index advances `4332 -> 4421`,
Flik first moves at movie frame `4360`, `FUNC_80048138=20`, player integrator call site `0x800495c8=6`,
`FUNC_8003633C` entry/tail `24/20`, candidate reset `0x800363b4=24`, candidate append `0x800368e8=158`,
`FUNC_80035280=5`, d1/d0 `89/38`, response `2`, player-Y commit `11`, and candidate-list writes total `7299`.

In the failing `0,73,92` interaction, the authored spawn still applies and movie playback still advances
`4332 -> 4421`, but Flik remains exactly `(197088,5344,492896)`, `FUNC_80048138=0`, `0x800495c8=0`,
`0x800495d0=0`, `FUNC_8003633C` entry/tail `0/0`, candidate reset/append `0`, `FUNC_80035F24=0`, `FUNC_800345CC=0`,
`FUNC_80035280=0`, d1/d0/PIP/response/player-Y commit all `0`, and candidate-list writes are `0`.
The relevant runtime sector-table entries are stable before/after the trace; in the failing interaction the `gp` and
candidate-list memory-window hashes also stay unchanged after spawn, so P19 did not find a candidate-list overflow or
sector-table stomp in the post-spawn window.

Therefore P18's sampled candidate sectors `[44,45,77,99,107,108]` in the failing build are stale, not current
selector proof. The replacement interaction is not failing because the native swept resolver rejects sector 92 during
movement; it fails earlier because the normal player update tick stops after spawn while movie playback continues.

Evidence:

- `docs/G3_NATIVE_P19_MOVEMENT_STALL_DIAGNOSIS.md`
- `build/g3_native_p19_movement_stall_comparison.json`
- `build/g3_native_p19_minimal_fail_0_73_92_trace.json`
- passing control traces `build/g3_native_p19_{p17_seed,prefix07,sector092_alone,seed_0_73_control}_trace.json`

Guard validations after P19 tooling: P11 one-command baseline passed from `templates/g3_native_p11_baseline.blend`;
P17 final and P18 best prefix both still pass marker+goal with `RENDER_C=0`, `FUNC_80010000>0`, and no plunge.

Next collision work should trace the gameplay/update scheduler or mode globals that decide whether `FUNC_80048138`
runs after spawn in the `0,73,92` build. Do not resume expanding replacement sectors until that upstream gate is
understood.

**P20 player-update scheduler diagnosis — blocker moved to render/cull exception (2026-07-06).** Added
`tools/trace_g3_native_update_scheduler.py` and compared the P20 cold-boot/movie matrix: P17 seed
`[93,99,100,107,108]`, P18 prefix07 seed+`[0,73,87,88,89,90,91]`, sector `92` alone, immediate control
seed+`[0,73]`, and failing seed+`[0,73,92]`.

Outcome B, no fix promoted. Static JAL scan corrected the direct `FUNC_80048138` caller to `0x8004EFD8`
(`ra=0x8004EFE0`); the older watched `0x8004F7D8` PC is not the player-update call site. In all passing controls
the post-spawn scheduler path is normal: top/gameplay loop re-enters, `0x8004EFD8` and `FUNC_80048138` both hit
`39`, the integrator hits `62`, Flik moves from the authored spawn, `RENDER_C=0`, and native GTE remains active.

In the failing `0,73,92` interaction, the P11 spawn still applies exactly at `(197088,5344,492896)` and movie
playback still advances, but no post-spawn top loop, gameplay loop, player-update call site, `FUNC_80048138`, or
integrator hits occur. The gameplay shell gate stays `0`, transition lever stays `0`, and scene id stays `1`.
Post-spawn PC samples are BIOS/low exception only. COP0 reports `CAUSE=0x41c`, exception code `7` (data bus error),
`EPC=0x8001EB3C`, `BadVAddr=0`; live disassembly at `0x8001EB3C` is `lw v0,0(s2)` in the render/cull object
traversal path. The last normal gameplay-loop render region is around `0x8004F448`, calling `FUNC_800224EC` with
`a0=0x8009EC50` after the player-update region.

Therefore P20 moves the blocker from "why does the scheduler skip the player update?" to "why does the minimal
replacement interaction corrupt or expose a render/cull object/list pointer before the next scheduler tick?" Do not
resume broad collision replacement until that render/cull pointer provenance is understood. Evidence:
`docs/G3_NATIVE_P20_PLAYER_UPDATE_SCHEDULER.md`,
`build/g3_native_p20_scheduler_comparison.json`, and per-case
`build/g3_native_p20_*_scheduler_trace.json`. P11 one-command baseline still passes from
`templates/g3_native_p11_baseline.blend`.

**P21 render/cull pointer provenance — bad object/list payload pointer isolated (2026-07-06).** Added
`tools/trace_g3_native_render_cull_fault.py` and compared the P21 cold-boot/movie matrix: seed+`[0,73]`, failing
seed+`[0,73,92]`, sector `92` alone, P17 seed, and P18 prefix07. This uses a layered flight recorder: cheap
per-frame spine, range watches around `0x8001EA6C..0x800206B0` and `0x800224EC..0x80022900`, static discovery after
the level overlay is loaded, and heavy dumps/source-slot watches only around the fault.

Outcome B, no fix promoted. The P20 data-bus exception at `0x8001EB3C` is now pinned to the render/cull object field
feeding `s2`:

```asm
0x8001EAF4  lw s0,0x10(a1)
0x8001EAFC  lw s2,0x18(s0)
0x8001EB3C  lw v0,0x0(s2)
```

In the failing seed+`[0,73,92]` trace, dispatch key `65` reaches `0x8001EB3C` with
`a1=0x80173130`, `[a1+0x10]=0x801c3614`, and `[s0+0x18 @ 0x801c362c]=0xfffabfa0`, outside PS1 RAM. The immediate
control seed+`[0,73]` reaches the same dispatch key with `[s0+0x18 @ 0x801c1678]=0x801741e0`, a readable native
payload/node pointer. The other passing controls also load valid main-RAM `s2` values:
sector-92-alone `0x80171e4c`, P17 seed `0x80170598`, P18 prefix07 `0x801791d4`. A post-arm write watch on the
failing source slot `0x801c362c` recorded zero writes before the fault, so the bad value is already present when
render/cull consumes the node.

An early long watch produced writer leads at reported PCs `0x8001d1b8`, `0x800319a4`, and `0x80031a68`; because
accessLog write events report the pre-write value and PCs may be instruction+4, the instruction candidates are
`0x8001d1b4 sw s0,0(s1)`, `0x800319a0 sw s7,0(t9)`, and `0x80031a64 sw v0,0(a2)`. Treat these as builder leads,
not final writer proof. The collision correlation remains: adding sector `92` expands decompressed chunk-32 by
6324 bytes and shifts later block data, but the immediate failure is a poisoned render object/list field, not
`FUNC_80035280` rejecting a floor plane.

Evidence: `docs/G3_NATIVE_P21_RENDER_CULL_POINTER_PROVENANCE.md`,
`build/g3_native_p21_render_cull_comparison.json`,
`build/g3_native_p21_pointer_provenance_report.json`, and per-case
`build/g3_native_p21_{seed_0_73_control,minimal_fail_0_73_92,sector092_alone,p17_seed,prefix07}_flight.json`.
P11 baseline is still required as the guard before resuming any replacement work. Next: trace the render object/list
builder that fills `s0+0x18`; do not continue broad sector replacement until that builder path is understood.

**P22 render node-builder provenance — collision grid builder overwrites the render/cull source slot (2026-07-06).**
Added `tools/trace_g3_native_render_node_builder.py` and ran the layered P22 workflow: preserve P21, offline byte
search, node/list comparison with live adjacent windows, temporal narrowing, focused writer trace, replacement-data
correlation, and final report. Outcome is trace-backed; no fix or baseline flag was promoted.

The exact bad value is not present in scanned media/artifacts: no little-endian `0xfffabfa0`, no big-endian
diagnostic variant, and no failing node/dispatch prefixes in the built `.bin`, `_collision.RAW`, decompressed chunk
32, `_terrain.DAT`, `_SCUS_942.88`, runtime patch JSON, or P21 flight snapshots. Temporal narrowing over the failing
seed+`[0,73,92]` build proves `[0x801c362c]` is still a valid main-RAM pointer (`0x80175b84`) at movie frame `4282`,
then becomes `0xfffabfa0` at frame `4283`. The seed+`[0,73]` and sector-92-alone controls keep valid analogous
payload pointers through the same frame window.

Focused access/exec tracing captured the writer:

```asm
0x80031A64  sw v0,0(a2)
```

At the bad store, `a2=0x801c362c` and `v0=0xfffabfa0`. The caller context (`ra=0x80031890`) places this in the
collision grid/list builder range `0x800313a8..0x8003229c`, not in render/cull itself. The register set also shows
`t4=0x800a9d98`, runtime sector-table entry 167 (`0x800a7e48 + 167*0x30`), so this is grid/bounds data being written
into the range later consumed by render/cull dispatch key 65 as `[s0+0x18]`.

Replacement correlation remains important but no longer explains the fault as a floor-selector problem. Adding
sector `92` to seed+`[0,73]` grows decompressed chunk 32 by `6324` bytes (`1884` retained old block -> `8208`
authored replacement for sector 92) and shifts later block data by the same amount. The immediate crash, however, is
an in-RAM ownership/layout collision: collision grid/list builder output overwrites `0x801c3614..0x801c3688`, and
render/cull later interprets it as an object payload-holder. Evidence:
`docs/G3_NATIVE_P22_RENDER_NODE_BUILDER_PROVENANCE.md`,
`build/g3_native_p22_builder_provenance_report.json`, and
`build/g3_native_p22_focused_writer_trace.json`.

Next: P23 should inspect the destination-range allocation/limits in the collision grid/list builder
`0x800313a8..0x8003229c`, especially `0x800319a0 sw s7,0(t9)` and `0x80031a64 sw v0,0(a2)`. Do not resume broad
sector replacement until we know why the failing chunk-32 replacement layout lets that builder write into a render/cull
source range.

**P23 collision grid-builder destination diagnosis (2026-07-06).** `tools/trace_g3_native_collision_grid_builder.py`
traced all five P23 cold-boot/movie cases and proved the failing `0x801c362c` write is inside the collision
grid/list builder's intended output range. The live formula is `t9 = base + s1`, `a2 = t9`, `element_index=s1/4`;
for seed+`[0,73,92]`, the dominant base is `0x801c3390`, and the builder range overlaps the render/cull node
`0x801c3614..0x801c3688`. `v0=0xfffabfa0` is a legitimate signed max-Z/grid bound derived from runtime sector
entry 167, not a payload pointer. P24 should target the workspace lifetime/layout collision, not sector footprint
authoring as the first fix. Evidence: `docs/G3_NATIVE_P23_COLLISION_GRID_BUILDER_DESTINATION.md`,
`build/g3_native_p23_destination_bounds_report.json`.

P24_RENDER_STALE_NODE_LIFETIME_2026_07_06
P24 render stale-node lifetime fix (2026-07-06). The seed+[0,73,92] crash is a stale render/cull key-65 payload-holder slot (`0x801c362c`) after collision-builder workspace reuse. An opt-in `--p24-stale-render-guard` hook skips only invalid non-main-RAM payload pointers at `0x8001eb3c` and counts skips at `0x8007f30c`. Default P11/P17/P18 behavior is unchanged.

P30_PRACTICAL_AUTHORING_BASELINE_2026_07_06
P30 packages the validated P29 Track-B collision-island path into a designer baseline: `templates/g3_native_p30_collision_island_baseline.blend` plus `tools/g3_native_p30_build_validate.sh`. The supported shape remains a constrained heightfield route with mild ramps, at least one turn, spawn, marker, goal, and `abl_g3_sink_outside_collision=200000`. Validation requires cold-boot marker+goal, `RENDER_C=0`, `FUNC_80010000>0`, no plunge, P25A acceptance against P11, and `p24_skip_counter=0` because the P24 guard is not promoted. It is still not walls, arbitrary topology, stacked floors, free-roam, retile, or full old-collision replacement.

P33_DESIGNER_ITERATION_PACK_2026_07_06
P33 validates repeatability of the P30/P31/P32 designer workflow with multiple constrained Track-B collision-island variants. `s_route` and `plateau_ramp` pass P31 preflight, cold-boot marker+goal, `RENDER_C=0`, `FUNC_80010000>0`, no plunge, and dedicated P25A harness scenarios with `p24_skip_counter=0`. `wide_island` passes preflight and renderer safety but misses marker/goal at runtime, so it is retained as a failed wider-footprint pattern. Evidence: `docs/G3_NATIVE_P33_DESIGNER_ITERATION_PACK.md`, `build/g3_native_p33_iteration_pack_comparison.json`, and `build/g3_native_p33_iteration_pack_summary.md`.

P34_ROUTE_TUNING_DIAGNOSTICS_2026_07_06
P34 adds `tools/report_g3_native_route_tuning.py`, a designer-facing diagnostic that parses existing cold-boot validation logs, runtime patch trigger AABBs, profile metadata, and harness summaries. It reports marker/goal hit frames for passing variants and nearest sampled miss distances for failures. For P33 `wide_island`, the run is renderer-safe (`RENDER_C=0`, `FUNC_80010000>0`, no plunge) but misses marker by `150494` runtime units and goal by `211779`, so the issue is runtime route/trigger alignment rather than engine fallback.

P35_WIDE_ISLAND_RUNTIME_RETUNE_2026_07_06
P35 applies the P34 diagnosis to the failed P33 `wide_island` variant. `tools/abl_blender/g3_native_p35_wide_island_retune_scene.py` generates `retune_a` and `retune_b`; both pass P31 preflight and the P30 cold-boot workflow. `retune_a` keeps the P33 wide marker/goal positions, changes the route/heightfield envelope, and reaches marker frame `4570` plus goal frame `4890` with `RENDER_C=0`, `FUNC_80010000=1800`, no plunge, outside sectors sunk `7/7`, and P30 harness `accepted_fix`. This remains workflow authoring only: no engine behavior/default changes, no retile, no broad replacement, and no wall/object support.

P36_WIDE_ISLAND_EXAMPLE_2026_07_06
P36 consolidates P35 `retune_a` as `templates/g3_native_p36_wide_island_example.blend`, a documented wider-island Track-B example only. It preserves the P35 result but does not replace P11/P30 as baselines and does not promote sink-outside, the P24 guard, replacement-sector flags, retile, or broad replacement to defaults. Runtime proof remains cold-boot marker+goal with `RENDER_C=0`, `FUNC_80010000>0`, no plunge, and collision island `7/7`.

P38_DESIGNER_WORKFLOW_HARDENING_2026_07_06
P38 adds the Track-B template catalog, template-choice guardrail, and one-command designer check wrapper. It repairs the missing P37 validation-matrix evidence with `build/g3_native_p38_validation_matrix.json` and direct P11/P30/P36 runtime summaries. This is workflow/reporting only: no engine behavior, gameplay behavior, defaults, retile, broad replacement, wall/object support, or free-roam claims changed.

P39_CONTROLLED_EXAMPLE_EXPANSION_2026_07_06
P39 attempts two new constrained Track-B collision-island examples. `templates/g3_native_p39_curved_route_example.blend` passes preflight, cold-boot marker frame `4570`, goal frame `4890`, `RENDER_C=0`, `FUNC_80010000=1801`, no plunge, island `7/7`, and P25A `accepted_fix`. `templates/g3_native_p39_gentle_elevation_example.blend` passes preflight and renderer safety but misses marker/goal, so it is preserved as `route_tuning_needed`. No engine behavior, defaults, retile, broad replacement, wall/object support, or free-roam claims changed.

P40_RUNTIME_ARTIFACT_SCHEMA_FREEZE_2026_07_06
P40 adds schema vocabulary, artifact inventory, normalization, compatibility audit, and regression coverage for Track-B workflow reports. It preserves known classifications: P11 frozen baseline, P30 practical baseline, P36 canonical example, P39 curved route passing example, and P39 gentle elevation route-tuning-needed. This is schema/tooling only and changes no engine behavior, gameplay behavior, defaults, retile, broad replacement, wall/object support, or free-roam claims.

P41_TRACK_B_AUTHORING_RELEASE_PACK_2026_07_06
P41 packages the constrained Track-B collision-island workflow into `docs/G3_NATIVE_TRACK_B_AUTHORING_RELEASE.md`, `tools/g3_native_release_audit.py`, `tools/g3_native_release_manifest.py`, and `tools/g3_native_release_check.py`. It preserves P11/P30/P36/P39 safety and normalized classifications, and changes no engine behavior, gameplay behavior, defaults, retile, broad replacement, wall/object support, or free-roam claims.

P42_GENTLE_ELEVATION_RETUNE_2026_07_06
P42 retunes the P39 gentle-elevation `route_tuning_needed` case into passing examples generated by `tools/abl_blender/g3_native_p42_gentle_elevation_retune_scene.py`. `retune_a` is the documented mild elevation-transition reference: preflight passes, marker frame `4570`, goal frame `4890`, `RENDER_C=0`, `FUNC_80010000=1801`, no plunge, island `7/7`, and P25A `accepted_fix`. The original P39 gentle-elevation scene remains preserved as the route-tuning failure; no engine behavior/defaults, retile, broad replacement, wall/object support, or free-roam claims changed.

## P58 — native density, the two render states, and the near-field law (2026-07-07)

The operator's persisting "blue floor while walking / terrain visible when
jumping" was root-caused as THREE stacked facts (full detail:
`docs/G3_NATIVE_P58_NATIVE_DENSITY_AND_RENDER_MODES.md`):

1. **Adaptive native density (landed).** Pristine floor payloads are n≈8–11
   grids (~470–650 file/quad); our uniform `--regen-visual 6` under-sampled the
   big payloads. `P58_ADAPTIVE_N=1` picks, per payload, the largest n whose
   styled grid FITS the original byte slot → native pitch, 29/30 in place,
   +1.2 KB DAT. At the operator's blue-floor spot the authored floor now scores
   **5/6 ground picks — identical to pristine at the same spot** ([[Finding - Candidate A is DAT-backed visual terrain]]).
2. **The stall-state confound (verification law).** After `movie.stopPlayback`
   (or any warp-guard teleport) the game renders floors far more generously
   than WALKED gameplay; two taps of walking collapses near coverage. All
   P54b–P57 "pebbles verified" screenshots were stall-state artifacts. Any
   visual claim must be measured while walking (blue-fraction metric).
3. **The near-field law.** In gameplay state a quad near the camera projects
   >1023 px and the GPU rejects it; at native density the passing band starts
   ~2 quads out. Pristine covers the near band with the tan GP0(60) fill bands
   plus the chunk-35 fine instanced meshes ([[Chunk 34 and 35 - shared model arena]]).
   Payload density cannot close this within the DAT ceiling (+72 KB).

**Ship config now:** fills ON (no `--suppress-ground-fill`), no union sink,
adaptive density, P11-cave **fall-rescue** (Y>100000 → warp to spawn; the
engine has NO kill plane — deep pits are softlocks). Walked 9-leg roam:
9/9 stops 0.0% blue in the lower screen, 0 unrescued falls. The walking game
shows continuous dirt ground everywhere; the near band is smooth tan (fill)
rather than pebbled.

**Dead ends (do not retry):** union-sink via deep surface wrap (P51-class
render poisoning), sector-origin sink (invisible in-corridor pits + no kill
plane → softlock), camera-raise poke (no effect), restoring/forcing the
DAT+0x380 zone-flag band (derived state; bit 0x100 toggles per zone crossing).

**Next milestone — pebbled near-field:** camera-centered dynamic carpet via the
proven [[Tier 3 - GTE Render Path]] (~12×8 quads of ~200-file dirt tiles,
decimated heightfield in the TIER3 blob, ~192 tris ≈ 250k cyc), or the native
route: chunk-35 instance re-height — instance array stride 0x54 @0x80089F58
mapped (src_re/scenery_instance_array_8001dea0.c) but static placement encoding
still unknown (zone-baked packets suspected; bake routine unfound).

## P59 — walk-plane lift (2026-07-07, operator's idea)

Raising Flik's walk plane relative to the drawn ground (implemented as a
visual-only drop, `P59_VISUAL_DROP=4000` rt — spawn/props/rescue untouched)
pushes the camera far enough from the floor quads that the NEAR rows pass the
GPU size-reject **during real walking**: feet-row ground picks 0/6 → 2-3/6,
lower-screen blue stays 0.0%. Fills must stay ON (without them the mid band is
48-60% void); drop 8000 over-shoots (0/6 — don't raise further). Ship config =
P58 canonical + `P59_VISUAL_DROP=4000`. Near band now shows REAL pebble
texture underfoot while walking; mid band remains tan fill until the chunk-35
/ Tier-3 carpet milestone.
