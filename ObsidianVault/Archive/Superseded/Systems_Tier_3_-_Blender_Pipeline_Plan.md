---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Tier 3 - Blender Pipeline Plan.md
aliases:
  - "Tier 3 - Blender Pipeline Plan"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Tier 3 - Blender Pipeline Plan.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Tier_3_-_Blender_Pipeline_Plan.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Tier 3 - Blender Pipeline Plan
type: plan
updated: 2026-07-03
status: active plan
tags: [plan, tier3, blender, custom-level, props, dot, enemies, collision, pipeline]
---

# Tier-3 Blender pipeline — implementation plan (post-2026-07-03 levers)

> Turns the newly-proven levers (Dot reroute · chunk-31 enemy placement · pass-1 prop
> position+payload · seed/plant system · exit relocation · prop/collision decoupling) into a
> concrete plan to finish the custom-level pipeline. Builds on [[Tier 3 - Custom Level Engine]]
> (collision/render engine — done through 3c-collision) and [[Blender-first ABL level editor]]
> (import working, object export proven). **No re-proving of solved levers.**

## 0. Architecture principle (settled by this week's RE)
The native game itself decouples **visuals** (pass-1/3 records, terrain payloads) from **collision**
(sector planes) from **actors** (chunk-31 records) from **routes** (DAT waypoint records). Tier-3
mirrors it: Blender authors each lane separately; one builder script stages them all into one disc.

## 1. Blender → disc export design (one manifest, five lanes)

Blender add-on exports **one `level_manifest.json`** (schema: `mod/tier3_level_schema.json`) from
tagged collections; `mod/build_tier3_level.py` (new, wraps the existing builders) consumes it.

| Lane | Blender authoring | Export → disc target | Status of write path |
|---|---|---|---|
| **Terrain + walls + death-plane (collision)** | the level mesh (`T3_Collision` collection) + wall boxes + a death-plane empty | existing TIER3.RND format (`mod/tier3_level_format.py` → `build_tier3_render_disc.py`) | ✅ proven (engine done) |
| **Visible geometry** | `T3_Visual` mesh (UV'd against native VRAM atlas) | TIER3.RND render mesh | ✅ proven (2a/2b; textures/depth = 2c/2d residual) |
| **Props** | Empties in `T3_Props`, custom prop `payload` (from the palette, §3.1) | **pass-1 records**: XYZ = world/32, `+0x10` = payload file-offset via `dat_reloc` | ✅ position + payload-swap proven; builder glue = new |
| **Enemies & seeds** | Empties in `T3_Actors`, custom prop `type_word` (low byte = enemy id) | **chunk-31 records** (decompress → write XYZ/type → `recompress_level_raw`) | ✅ relocate proven (ABL_SPIDER_MOVE); **add-new = to test** (free zero slots exist) |
| **Dot route** | a polyline/curve `T3_DotRoute` (≤104 points; last point repeated to fill = she parks at goal) | DAT waypoint record @`+0x468` (s32 file coords, stride 0xc) | ✅ reroute proven (ABL_DOT_REROUTE2); design rules: terrain-plausible Y, legs not ultra-short |
| **Pickups/tokens/exit** | Empties in `T3_Pickups` (kind byte); exit = pick a collision sector → region code 2 | `apply_level_placements` (type-0x3f) — proven; exit sector edit — proven | ✅ both proven |

**Export conventions:** world = Blender units × scale-factor (documented in the schema); Y sign flip
(−Y up in ABL); all placement coords quantized to ×32 (file scale) where the lane needs it.

## 2. Documentation to update (as the work lands)
- [[Tier 3 - Custom Level Engine]] — add the four new pillars (props/actors/route/exit) to the phase list; mark collision/render status current.
- [[Blender-first ABL level editor]] — the export spec §1 table + collection-naming conventions.
- [[Prop and foliage catalog]] — append the payload palette (§3.1) when dumped.
- [[Dot guide NPC]] — add "custom-level checklist" (model residency validation, §5.5).
- `mod/README.md` — `build_tier3_level.py` usage.
- Memory: pipeline status entry once the POC ships.

## 3. Helper scripts / schema stubs to add
1. **`tools/dump_pass1_palette.py`** — the enabler for prop picking: for each distinct pass-1 payload
   in LEVEL01 (500+ records → ~dozens of distinct payloads): spawn/teleport-view it (or payload-swap
   onto a fixed record in front of a fixed camera save), `captureFrame`, emit
   `palette/{payload_offset}.png` + `palette.json` (payload → thumbnail + source records). One
   isolated-instance batch run.
2. **`mod/tier3_level_schema.json`** — the manifest schema (stub added with this plan).
3. ~~**`mod/build_tier3_level.py`**~~ — **✅ BUILT + PROVEN 2026-07-03** → [[Level manifest round-trip]]:
   manifest → DAT/chunk-31 patch → disc; LEVEL01 re-created byte-identically (DAT) and cold-boot
   verified 8/8. Extractor: `tools/extract_level_manifest.py`. Remaining in this item: the TIER3.RND
   custom-geometry lane hookup + count-changing pickup edits (apply_level_placements integration).
4. ~~Blender add-on export operator~~ — **✅ BUILT INTO THE EXISTING EXPORTER (2026-07-03)**, prefix-based
   (matching the exporter's existing `spawn*/pickup*/exit*/blocker*` conventions), and **cold-boot proven
   end-to-end** through the unchanged one-button pipeline (`tier3_build_gui.sh` → `tier3_build_level.sh`):

   | Name prefix (Empty) | Lane | Data |
   |---|---|---|
   | `prop*` | pass-1 prop | custom prop **`abl_payload`** = DISK payload offset (`build/pass1_palette/palette.json` → `disk_payload`; thumbnails = the picker) |
   | `enemy_<name>*` | chunk-31 actor | name (`enemy_spider/worm/pill/bee/mosquito`) or custom prop `abl_type_word`; donor params auto-copied |
   | `dot_00, dot_01, …` | Dot guide route | sorted by name; tail-padded (she parks at the last point); **her actor is auto-added** at wp0 |

   Plumbing: `tools/tier3_blender_export.py` (new lanes in the JSON) → `tools/tier3_lanes.py` (applies
   them post-suppression: props claim pass-1 records in the STAGED dat; actors rebuild chunk 31 with
   donor params, quota auto-derives; Dot route patched at the walked offset) → `build_tier3_render_disc.py`
   (env `TIER3_LANES_JSON`, stages+restores LEVEL.RAW alongside LEVEL.DAT). **Verified**: build/lane_test.blend
   → disc → cold boot → 4/4 RAM checks (props at authored pos+payload; wp0/wp3 exact; live actors = the
   authored spider + Dot only; ENEMIES-REMAINING auto-derived to 1).
   ⚠️ Payload currency: use `disk_payload` from palette.json (runtime offsets differ — the original keys).

## 4. Next proof-of-concept: "Playground v1" (one disc, all levers)
Host on LEVEL01 (Tier-3 standard). Contents — each item exercises one proven lever end-to-end
**through the new manifest/builder path**:
1. Custom collision + visual mesh (existing Tier-3 level as base).
2. **3 props** placed via pass-1 records with chosen payloads (e.g. big berry, leaf tube, stone).
3. **2 enemies**: relocate the spider record onto the custom ground; **add one NEW record** in a
   free chunk-31 slot (the untested lever — kill criterion: it spawns + behaves).
4. **Dot** rerouted spawn → the custom goal, tail-parked at the exit (also validates her
   model/anim on a Tier-3 disc, §5.5).
5. **Exit**: relocate the sector-177 region code under the goal platform.
6. **5 grain + 1 berry pickup** via placements (HUD total already dynamic — HRE-012).
Verify: cold-boot movie → RAM checks per lane + a played traversal (movie or manual).
**Definition of done:** boot → follow Dot across custom ground past props → kill/avoid enemies →
collect grain → exit fires.

## 5. Still to solve (ranked)
| # | Item | Why it matters | Approach | Size |
|---|---|---|---|---|
| 5.1 | ~~Prop payload palette~~ | **✅ DONE 2026-07-03** — 484 thumbnails in `build/pass1_palette/` (all content-unique per-instance blobs) | tool committed | — |
| 5.2 | ~~Enemy ADD-new record~~ | **✅ PROVEN 2026-07-03** (`ABL_ENEMY_ADD`: new spider spawned, chased; quota auto-derived 21→22) | done ahead of the POC | — |
| 5.3 | **Dot model/anim on a Tier-3 disc** | guide must render/animate on custom ground | included in POC (§4.4); fallback: keep her LEVEL01-resident assets (host level = LEVEL01, so expected fine) | S (validation) |
| 5.4 | ~~Pass-2 table layout~~ | **✅ RESOLVED 2026-07-03** — pass-2 = mesh/scale registration (not placements); see [[Prop and foliage catalog]] | — | — |
| 5.5 | ~~Swing behavior~~ | **✅ RESOLVED 2026-07-03** — player mode 5 @`0x800a6580`, integrator-driven pendulum; pivot-source residual | — | — |
| 5.6 | **Baked decor offsets** (mushroom clusters, fence lines in terrain payloads) | only needed to *individually* edit baked decor | defer — Tier-3 recreates such looks as quads; revisit only if native-terrain hybrid levels demand it | L — deprioritized |
| 5.7 | **Native render suppression (3c-render)** | fully custom visuals need native terrain blanked | the known gp0Trace approach (identify terrain prims → blank) — pre-existing blocker, unchanged | M/L |
| 5.8 | **2c textures / 2d depth polish** | visual quality | existing Tier-3 render residuals | M |

## Sequencing
**Week 1:** §3.2 schema + §3.1 palette dump + §3.3 builder skeleton (DAT lanes only) → **Week 2:**
Blender export operator + Playground v1 build/iterate (incl. 5.2/5.3) → **then:** 5.4/5.5
opportunistically; 5.7/5.8 as the visual-polish track.

## Related
[[Tier 3 - Custom Level Engine]] · [[Blender-first ABL level editor]] · [[Prop and foliage catalog]] · [[Dot guide NPC]] · [[Enemy spawn architecture]] · [[Seed plant output binding]] · `mod/tier3_level_schema.json`
