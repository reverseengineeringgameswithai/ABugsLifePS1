---
kind: system
id: Tier_3_-_Native_Terrain_Path
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Tier 3 - Native Terrain Path.md
aliases:
  - "Tier 3 - Native Terrain Path"
archived_source: ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Native_Terrain_Path.md
patch_policy: unknown
---

# Tier_3_-_Native_Terrain_Path

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Tier 3 - Native Terrain Path.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Tier 3 — Native Terrain Path (author Blender terrain into `FUNC_80010000`)
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Native_Terrain_Path.md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## ⚠️ The native floor is culled PER PAYLOAD — this is what makes authored ground flicker

Operator-reported symptom: authored ground disappears and reappears as the camera turns, with sky
visible through the floor. Measured cause (2026-08-11): an authored 3,550 x 5,200 arena is drawn by
**three** payloads, so ~6,000,000 square units of ground rest on each one, and a single cull drops a
slab that size.

| payload | anchor (T_obj) | drawn footprint |
|---|---|---|
| `0x051418` | (8192, 24576) | x[1499,6935] z[17419,22875] |
| `0x052630` | (8192, 8192) | x[1587,6900] z[13553,18483] |
| `0x054660` | (8192, 8192) | x[1596,6991] z[8099,14539] |

Two compounding facts:

1. **Only 2–4 payload bboxes overlap any arena of that size** — a payload renders only over its own
   bbox (P57) and `park_offarea_floor` parks the rest. Same law that caps level extent.
2. **Anchors sit far from the geometry they draw** — `0x052630` is anchored ~5,500 units from what
   it renders. Pristine survives this because 30 payloads are drawing and something near the camera
   is always in range; with 3 there is no fallback.

**Lever not yet tested:** `tools/reanchor_floor_payloads.py` moves each anchor onto its own geometry
centroid and subtracts the same offset from every local vertex, so world positions are bit-identical
and only the culled anchor moves (size-preserving). ⚠️ P55 recorded that editing a node's `T_obj`
breaks the unified mesh chain — that was for PARKING nodes far off-field, but the risk is real.

**Separate rule discovered on the way (candidate, untested):** authored relief wavelength should be
several times the collision tile pitch. A scene at wavelength 1600 against a ~600 pitch dropped Flik
through the floor; the working hills build used 2200. Under ~3 samples per wave the collision cannot
follow the drawn relief and the two surfaces diverge.

Evidence: `docs/PAYLOAD_CULL_AND_REANCHOR.md`, `docs/HILLY_TERRAIN_PROOF.md`.

## ⚡⚡ The WALL/CLIFF layer IS this path (2026-08-11, live-measured)

LEVEL01's cliffs are drawn by **`FUNC_80010000`** — the same emitter, from the same LEVEL.DAT node
payloads, that this pipeline already authors. **There is no separate un-authorable wall layer.**

Measured on the pristine disc (`tools/probe_wall_layer.py`, `docs/WALL_LAYER_IDENTIFIED.md`):

- `gpu.pickObject` over the cliff and the floor returns the SAME draw class — `GP0(3c)` quad,
  texture page (0,0) — differing only in CLUT: **(976,255) = 0x3FFD on the cliff**, **(960,255) =
  0x3FFC on the floor**. That is Track A's recorded `0x3FFC ground / 0x3FFD wall` pair, confirmed
  live.
- An `accessLog` write-watch on an actual wall packet (`0x801e8cec`) reports writer PCs
  `0x80010574/5f8/604/608/674/678` — all inside `FUNC_80010000`.
- ⚠️ `gpu.traceCausality` is NOT the tool for this: on a DMA-submitted draw it names only the
  DrawOTag kick (`0x80064658`, stack ending at `0x80039a70` frame-present), never the builder.

**Consequence:** the "cliff material" residual on the authored-cliff work is a CLUT problem, not a
geometry-location problem. The authored cliff wore the ground palette; LEVEL01's cliffs wear the
wall palette. What selects the CLUT inside `FUNC_80010000` is the open question — first candidate is
the batch `ctrl` word's unexplained bits 8–9 (`0x60/0x64/0x160/0x164/0x260/0x264`, where `ctrl&0x1f`
is the documented page).

## Authored payload MATERIAL — what a native payload can and cannot reach (2026-08-11)

> ⛔ **SUPERSEDED the same day.** The claim that "the wall CLUT is unreachable from a payload"
> was inferred from `geometry_g57` and is **wrong**. `FUNC_80010000` computes
> `clut = base + (U >> 6) + 4 * (V >> 6)` at `0x80010628..0x80010640` — the CLUT is DERIVED FROM THE
> UVs, which ARE in the command stream. Picking the wall texture cell automatically picks the wall
> CLUT, so an authored payload reaches cliff material with no extra field. Verified on all 2,923
> pristine prims (zero exceptions) and live: the authored arena disc renders 131 picks on
> `clut(976,255)` = 0x3FFD. See [[FUNC_80010000_per-object_mesh_draw_-_payload_emitter]].

Curated Canon, measured on the pristine LEVEL01 DAT.

**A `FUNC_80010000` payload's material levers are exactly TEXTURE CELL x PER-VERTEX COLOUR.**
The CLUT is *not* in the DAT command stream — it is render-time state
(`src_re_geometry/geometry_g57_command_stream_texpage.md`), and the look is
`texture x vertex-colour`. So a payload cannot select the wall CLUT (`0x3FFD`) that gives
LEVEL01's cliffs their red-brown; it can only pick a different cell on the page it is given.

**The game's own cliff cell is `U[64,127] V[192,255]`.** The 12 `pay<0x10000` payloads spend
50.0% of their 900 primitives on it against 41.8% on the dirt cell `U[0,63] V[192,255]`; the 30
floor payloads invert that (62.6% / 18.7%). Their vertex colours run darker than the floor's
(median luminance 101 vs 116). `native_terrain_export.harvest_wall_style()` harvests both.

⚠️ **CORRECTION — the 12 `pay<0x10000` payloads are NOT vertical cliffs.** Measured by real face
normal: 599 prims below 30 deg, 280 at 30-60, 21 at 60-75, **zero above 75**. Across all 42
pristine payloads only 6 of 2,923 prims exceed 75 deg. They are terrain skirts. The dark
reddish-brown cliff in `build/PRISTINE_CLIFF_REFERENCE.png` is **LEVEL.RAW chunk 35**, the terrain
master mesh drawn by `FUNC_800172DC` as GP0(3c) — a separate layer (see the `walls-are-chunk35`
finding). Do not cite those payloads as evidence that the native path draws vertical geometry.

**The native path DOES draw near-vertical geometry** — just prove it with an authored payload, not
with a pristine one. `build/ABL_ARENA_CLIFF_LOW` renders 133 wall prims above the steep threshold
through `FUNC_80010000`, cold-booted and gated.

**Stretch is a subdivision problem.** One quad spanning a whole wall stretches a single 64x64 cell
over the entire face (the "streaky tan curtain"). Refining *across* the band subdivides the face
*vertically*; authored wall quads then measure 482-591 file units per edge against the pristine
payload median of ~506.

Evidence: `docs/G3_NATIVE_AUTHORED_CLIFF_WALLS.md`, `tests/test_cliff_walls.py`.

## Legacy Heading Index

- `# Tier 3 — Native Terrain Path (author Blender terrain into `FUNC_80010000`)`
- `## Native payload format (the exporter target)`
- `## M1 — byte-exact codec DONE (2026-07-05)`
- `## M2 core — authored geometry renders through the native GTE path PROVEN (2026-07-05)`
- `## Architecture facts (from the 3-agent investigation)`
- `## Reuse map`
- `## M2 core CONFIRMED on the operator's LIVE instance (2026-07-05)`
- `## M3 core — WHOLE-FLOOR custom native terrain WORKS (2026-07-05)`
- `## M2b — resize/relocation VALIDATED IN-GAME (2026-07-05)`
- `## M2b — resize/relocation pipeline BUILT + Python-validated (2026-07-05)`
- `## Roadmap — PIVOT COMPLETE end-to-end (2026-07-05)`
- `## P43 Track-B stable pattern pack (2026-07-06)`
- `## P44 Track-B pattern router (2026-07-07)`
- `## P45 Track-B stress matrix (2026-07-07)`
- `## P46 Track-B collision frontier (2026-07-07)`
- `## P47 Track-B replacement envelope (2026-07-07)`
- `## P48 guarded sector-92 re-entry (2026-07-07)`
- `## P49 render-driver active-record provenance (2026-07-07)`
- `## P50 guarded sector-92 swap envelope (2026-07-07)`
- `## ⭐ P51 — grid-builder scratch-window pack: the P18–P50 ROOT FIX (2026-07-07)`
- `## ⭐ P52 — FULL AUTHORED COLLISION WORLD + Blender demo (2026-07-07)`
- `## P54 — invisible-terrain root cause + original-level visual cleanup (2026-07-07)`
- `## P54b — terrain over the collision + surgical scenery removal (2026-07-07, operator-corrected)`
- `## P55 — aligned uneven pebble terrain + the parking regression (2026-07-07)`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Tier_3_-_Native_Terrain_Path.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.
