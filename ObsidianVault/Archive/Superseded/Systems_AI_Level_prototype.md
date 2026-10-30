---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/AI Level prototype.md
aliases:
  - "AI Level prototype"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/AI Level prototype.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/AI_Level_prototype.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: AI Level prototype (ailevel)
type: project
updated: 2026-07-04
status: active prototype — bug-hunting playground
tags: [tier3, blender, custom-level, prototype, ailevel, playground]
---

# AI Level — the all-items Tier-3 prototype

> The full-fledged custom-level prototype built 2026-07-03 to exercise **every proven lever at
> once** and serve as the bug-hunting playground. Author in Blender, rebuild with the usual
> one-button pipeline. Conventions: [[Tier 3 - Blender Prefix Cheat Sheet]].
> **⏸ 2026-07-04: session paused — resume from [[AI Level - Session 2026-07-04 handoff]]**
> (current disc md5 09d1b80b…, fixed: launches/fall-through/artifacts/pebble-ground/stretch/20fps;
> open: creep-spot repro, emblem 24/24, VM triggers, prop art, budget ceilings).

## Files
| What | Where |
|---|---|
| Blender scene (edit this) | `build/ailevel.blend` |
| Reproducible generator | `tools/abl_blender/make_ailevel_prototype.py` (tracked) |
| Playable disc | `build/ABL_AILEVEL.cue` (+`.bin`) |
| Rebuild | `./tools/tier3_build_level.sh build/ailevel.blend` (or the zenity GUI) → copy `build/ABL_tier3_render.*` → `ABL_AILEVEL.*` |
| Exported lanes JSON (debug) | `build/ailevel.json` |

## Layout v6 (2026-07-03) — **TRUE FLIK SCALE**: 156 faces / 312 tris, multi-route, tiled walls
> Same LEVEL01 envelope + route graph as v4/v5, with every feature sized to the CHARACTER.
> **⚖ THE YARDSTICK (use for all future levels):** Flik is ~2.4 BU wide (engine `WALL_SKIN=1200` =
> half-width) and **~8-10 BU tall**; his jump rise is a FIXED **6.3 BU** (~0.7 body heights). So:
> features must be **LARGE IN PLAN** (pads 25×18 = 2-3 body heights across; islands/branch 16×12) and
> **SHALLOW IN RISE** (steps 2.5-3.5, **never > 5** — nothing jumpable is taller; taller = ramp).
> Landform heights: ridge/cliff 13, canyon walls 14 (leaning), perimeter rims 12, gates 9, baffles 6,
> mesa 5 (the jump-up maximum), shelf +5 over the terrace. Canyon widened to x ±16 for camera room.
> **🧱 WALL TILING RULE:** a tall wall as ONE quad smears its single 64-texel tile into stripes —
> `wall()` subdivides into ~15×10-BU cells (one tile per cell, like the floor grids). Each cell emits
> its own collision segment, so **MAXW was raised 64→128** (`mod/tier3_level_format.py`; the cave loop
> reads segments straight from the blob — no fixed buffer).
> Budgets used: 312 verts / 312 tris (caps 384/512), blob 18052 B (cap 19456).
> ⚠ SEAM RULE (v4): zones of UNEVEN width leave open fall-notches at their seams — the plaza is the
> rear garden's full width and every overhang edge gets a rim wall.

| # | Zone / route | Terrain | Contents |
|---|---|---|---|
| 1 | **Rear garden** (y −60..−10) | 5×2 grid, x −40..40, rimmed | grass rim · clover/stones · 2 grains |
| 2 | **Start plaza** (y −10..25) | 5×3 grid, **x −40..40** | `Spawn` @origin · **GATE walls** at y 25 (opening x −8..8) funnel into the field |
| 3 | **Main field** (y 25..95) | 10×5 grid, x −70..65 + 2 **baffle walls** (weave) | **spider** (−35,48) · 6-grain weave trail · grass/clover/stones/acorns · branch NW corner |
| 3a | **WEST RIDGE route** | ramp up (x −78..−70, y 28..40) → walkway x −90..−70 @z 2.5 → **bridge** (y 95..108) → ramp down into the canyon mouth; one-way cliff face to the field | **seedblue token** · 3 grains · ridge-top grass/leaf props |
| 3b | **MESA** (x 20..40, y 55..75, z 3) | jump-up island + west ramp | **`token`** + grain on top · stones at the base |
| 4 | **Canyon** (y 95..125) | floor + leaning walls, **west opening y 95..108** (ridge rejoin) + **east opening y 112..125** (island drop-in) | **worm ambush** (0,114) on the **gold-berry bait** · 2 grains |
| 4a | **EAST HOP ISLANDS route** | 3 pads (30,100,1.5)→(24,108,2.5)→(18,116,3) from the field NE corner, drop into the canyon north end | grain per island · **bee** (40,90) guards the approach |
| 5 | **Platform hop** (y 127..147) | 4 main pads @1.5/3/4.5/6 + **secret BRANCH** after pad 1: (−8,139,4.5)→(−17,147,6.5)→**SHELF** (−30..−19, y 149..159, z 9) | grain per main pad · **blueberry** pad 2 · **mosquito** overhead · shelf: **megaberry** + 2 grains, drop-off onto the terrace |
| 6 | **Terrace hub** (y 150..180, z 6) | 6×3 grid, rimmed L/R/N (opening = hill ramp) | **seedgreen** · **telescope** (0,176) · **greenberry** · 2 grains · **pill bug** guard · props |
| 7 | **Finish hill** (y 180..200, →z 9) | ramp + rimmed finish pad | **F-L-I-K letters** (y 193) · leaf tube · **`exit`** (0,197,9.6) |

**Dot route**: 20 legs on the MAIN path only (gate → field weave → canyon → pad climb → terrace → finish);
she can't take the platforming branches. **27 grains** total (HUD x/27) across every route.

**Native prop parking (new build step `[6p]`)**: at LEVEL01 scale the level overlaps the retail prop
field (the native fence/mushrooms showed inside the far zones). `build_tier3_render_disc.py` now sinks
every UNCLAIMED pass-1 record (434) + all pass-3 decor (140) to file Y +9000 (~288k below the world —
the proven move-far cull suppression, size-preserving). Authored props claim the first 50 pass-1
records and keep their coords. Opt-out: `TIER3_KEEP_NATIVE_PROPS=1`.

## Verified at cold boot (baseline for regressions, v6 2026-07-03)
- Blob header 312 verts / 312 tris; grass terminator −1 at the build-computed address (dynamic
  `T3_GRASS_TERM`; a different address every time the object count changes — working as designed).
- 38 type-0x3f entries (36 authored + 2 surplus telescopes); **grain HUD x/24**; enemy quota 00/**5**.
- Offline floor query validates every route surface (ridge −13266, mesa −5266 over field −266, isles
  −2766/−5266, pads −3266/−6766, branch −6766/−10266, shelf −15266 over terrace −10266, finish −13266);
  live probes stood Flik grounded on the gate plaza, widened canyon, pad 0, and the ridge walkway.
- **Scale reads right in captures**: canyon walls flank the worm ambush without texture smearing (cell
  tiling), the ridge reads as a real cliff-top path with the seedblue token, pads are 2-3 body-heights
  across. Enemy pile-ups during probing are teleport-aggro artifacts, not level bugs.
- **Walls hold** (v4 seam-notch walk pins Flik harmlessly); native props parked; backdrop + HUD intact.

## v6.3 prop + wall fixes (2026-07-03 evening)
- **Foliage/mushrooms restored** (operator: "no props"): two stacked engine bugs — pass-1 payload offsets
  are pristine-relative (now shifted by the count-control delta in `tier3_lanes`), and the per-frame grass
  terminator poke heads the PASS-1 PROP INSTANCE list, suppressing ALL props (now disabled whenever native
  props are parked — parking already removes native grass at source). MUSHROOM payload = `0x7030`.
- **Walls match the native cliff** (sampled via `gpu.pickObject` on the pristine wall): page 0x660,
  CLUT **0x3FFD**, 32×32 tile at (96,192), warm brown tint (NEUTRAL_TINT=0, per-face tints live).
- **Wall corners overlap ~1.5 BU** — segments don't block at their exact shared endpoint; butt-jointed
  corners leak walkers (live-caught escape). All rim/gate junctions now overlap.

## Chunk-35 OG-scenery removal — ❌ CLOSED as WRONG-TARGET (2026-07-04); OG visuals already gone
**Do NOT degenerate chunk 35 (or 34).** Two disc builds with the splice (per-prim-v0 AND
all-vertices-to-one-global) both **wedged the level load**: the loader's model converter
(`FUNC_8002958C`, weld loop `0x8002AD1C`) **welds vertices by position** (three `lh` compares at
rec+4/+6/+8, ±1 tolerance) against already-converted records and dead-halts (`j 0x8002ADD0`
self-jump) when a vertex has no match. The degenerate walker was also structurally wrong: chunk 35
is NOT `[cmd][n×8B vertices]` — it is a **sectioned master-mesh stream**: GP0 0x3C packets are
**12 words / 0x30 B** (`[col|cmd][xy][uv]`×4), plus u16 **index lists** and 3D **vertex pools**
(`x,y,z,0x0110`), so a byte3-scan stomps indices/pools/UVs.
- **Chunk pair 34/35 = the level's shared MODEL ARENA, not removable outer scenery.** Decompressed
  to `0x8012C1C4` (`02 01` header; data `0x8012C1D0`), then converted in place with runtime pointer
  links. The draw site `jal 0x800172DC @0x8001DF2C` (nodes `0x80089F58..`, node+0x20 → arena) also
  feeds **Flik's HEAD** (live NOP removed it, walls/backdrop unaffected). A live wholesale arena
  degenerate **blanked the entire scene** except the panorama — the earlier "one-shot proven safe"
  claim was wrong.
- **The OG visuals the operator reported (dark slabs / silhouettes / ribbons) were the pass-3
  lists + tp663 root — already removed** by the per-frame all-lists truncation. 4-direction sweep
  on the shipped build: no OG geometry anywhere; panorama rim (wanted) is the only native visual.
  The "tan cliff band" near the horizon is the chunk-29 **panorama**, not chunk 35 (it survives
  arena destruction).
- Codec exonerated along the way: `lz_encode_level_raw` streams decode **byte-exact in the game's
  own decompressor** (`debugger.callFunction 0x8001A1DC(a0=src,a1=dst)` → v0=size — callFunction on
  the decoder is a free codec oracle; use it before suspecting the encoder).
- `tools/tier3_lanes.py` keeps the (disabled) splice behind `SCENERY_STREAMS = ()` with the full
  post-mortem inline.
- Authored BRANCH/LEAFTUBE props removed (big models read as OG structures; the "root" in the operator's
  screenshot was our own branch prop — it survived the chunk-35 sink, proving its provenance).

## ✅ Props SOLVED: our own billboard renderer (2026-07-04, option B shipped)
Authored props are now rendered by OUR cave — no native decor pipeline involved, so they can never
vanish (walk-up persistence cold-boot verified). How it works:
- **Blob**: new BPROPS array after the UV block — `nbprops`, then per prop `{x, y, z, kind|size<<8}`
  (`mod/tier3_level_format.py` `bprop()`, `tier3_level.h` `LV_NBPROP/LV_BPROPS`).
- **Exporter**: `prop_*` empties → bprops; legacy `abl_payload` maps to a tile kind
  (grass/clover/leaf→0 plant, mushroom/big-berry→1 shroom, stone/acorn→2 rock); `abl_bprop`/`abl_size`
  override. The pass-1 lane is retired — ALL 484 native records are parked (X/Z+Y).
- **Tiles** (sampled live from VRAM page 0x660, 4bpp): plant = leaf (64,128)-(127,191) CLUT 0x3FF9
  (green on black; black = transparent → real cut-out), shroom = radial (192,192)-(255,255) CLUT
  0x3FF5, rock = pebbles (128,0)-(191,63) CLUT 0x3FFD. ⚠ tiles sampled on the PRISTINE boot may not
  be resident on the custom disc (the 0x6AF acorn art wasn't → black boxes → remapped to rock).
- **Emitter** (`tier3_otrender.c`): 2 GP0 0x24 tris per prop, base-anchored, height 2×size, depth via
  the same OT LUT as the floor — props composite correctly with the world.
- **Layout shift to fit**: GRAIN_SHIM/GRAIN_FN moved +0x800 (0x801F33F8/0x3400 — synced in BOTH asm
  files), RENDER_PAD 0x3400→0x3C00 (blob @0x801F3C00), render budget 0x27F8 (**only 24 B free**),
  NODE_MAX 448→416, scratch pack 0x801F8E00..0x801FE000, blob cap 0x801F8E00. Grain HUD hooks
  verified re-installed at the moved segment.
Cosmetic follow-ups: the shroom tile is a radial glow (find nicer art or author a tile into free
VRAM); a walk-through/tangible flag per prop = one wall segment when wanted.

## Props: cull gate — anchor hypothesis DISPROVEN (2026-07-04 late, superseded by the billboard renderer)
Anchor-follow (all 140 pass-3 anchors pinned to Flik per frame) did NOT fix the vanish-on-approach —
props got scarcer. The decor cull is NOT anchor-distance; leading theory = the native REGION-STREAMING
table (per-sector prop sets; garbage sector at custom coords → arbitrary appear/vanish). Reverted.
Next session, in order: **(B-full) own prop renderer** — author billboard tiles into free VRAM (proven
GPU-write path; source art via gpu.decodeTexture), props array in the blob (+scratch-layout shift for
budget), camera-facing quads cloned from the pickup-marker emitter; or (A-deep) decode the per-sector
prop-set table (execTrace the culler FUNC_80014360 against Flik's sector).

## Props: cull-group binding — earlier analysis (superseded above)
Operator-confirmed: authored props render as distant backdrop and DISAPPEAR on approach. Native decor
visibility keys on the PASS-3 GROUP ANCHOR distance, not the instance — our props still belong to
OG-anchored groups. Placement+model binding are solved; group binding is not. Next session:
**(B, recommended) render props in OUR cave as billboarded textured quads** (native VRAM tiles, blob
props array, optional wall segs for tangible ones) — bypasses native culling entirely; or (A) decode
the instance-to-group list ranges and relocate pass-3 anchors onto our clusters.

## ✅ 2026-07-04 playtest fixes (operator: launches / artifacts / deformed ground)
- **"Shot up in the air" FIXED — `NATIVE_DEEP` 40000 → 1,000,000** (`mod/caves/tier3_walls.c`).
  Root cause (per-frame FLOOR_PUB logging + execTrace): the native integrator `FUNC_8003633C`
  (internal path 0x80036CEC) GROUNDED Flik onto a native sector floor ~18–21k in the air. The
  suppression pokes sector **origin-Y** (0x800A7E48+4, 187 recs) but the sweep evaluates a **sloped
  per-sector plane** (slope data behind the record's data pointer into the chunk-32 pool); at 4x
  scale Flik walks 300–800k outside the OG polygons where `slope×distance` reaches −60k+ and
  overwhelms a 40000 base. Launch heights = OG hill heights (the fingerprint). Verified: all repro
  spots clean, jump intact, 938-frame wander clean.
- **Brown-rectangle artifacts FIXED — billboard tile audit** (`tier3_otrender.c` BPAGE/BCLUT/BU/BV).
  kind-2/3 used the page-0x660 **pebble FIELD** (seamless, opaque) → floating brown rectangles;
  kind-1 radial glow read as a light blob. Page 0x660 decoded on the custom disc = a 4×4 atlas;
  all kinds now use black-cutout tiles: leaf (64,128) · sprout stalk (64,64) green · dried stalk
  (64,64) brown · grass tuft (128,192). No mushroom/rock sprite is resident — revisit via VRAM
  upload if real art is wanted.
- **Deformed/blurry ground — SCOPED, not yet fixed**: one 32-px dirt tile stretched across 45k+
  unit faces (+ PS1 affine warp) = the smear. Proper fix = **GP0 E2 texture-window** per terrain
  node + wrapped UVs (subdivision is off the table: blob has 464 B free, MAXV 354/384, render
  .text 24 B free). Needs NODEW 8→10 + NODE_MAX cut + budget shift — its own session.
- **NEW / OPEN — resident mover-VM proximity triggers fire in the custom level**: crossing old
  LEVEL01 trigger spots played the Hopper FMV, the ant-colony FMV, and hint/camera input-locks
  (all observed live). Fix direction: gate VM op17/op12 (`FUNC_8004C13C`) when LEVEL01+T3LV via
  the runtime hook-install pattern. This also confounded the 24/24-grain emblem test (one 24/24
  state ended input-dead at pc 0xA0 — retest after trigger suppression).
- **v2 same-day correction — TRUE root cause + the shipped fixes**:
  - The warps are the native integrator's **revert-to-stack-snapshot** path (`FUNC_8003633C`,
    store at 0x80036CEC), NOT a floor value: warp height is ~independent of the origin-Y deepen
    (40000/300000 both launch; 1e6 makes Flik **fall through the floor** instead). Fixed with a
    **native-teleport guard** in `tier3_walls.c`: Y rising >4000 in one frame (real jumps max
    ~2816) with last-frame Y above the death plane → restore last-frame XYZ (`WPREVY`
    @0x801FE030). `NATIVE_DEEP` back to 40000. All 5 repro spots verified clean; jump/ramp intact.
  - **Ground smear**: shipped the **GP0 E2 texture-window** — terrain nodes are
    `[E2 set][tri][E2 clear]` (NODEW 10, NODE_MAX 332) + exporter wrapped repeat-UVs
    (≤7 repeats/face, ~13 BU/tile). Steep edge-on faces still streak (PS1 affine).
  - **Props v2**: page 0x660 has no usable sprite art besides the leaf (transparency = texel
    index 0; clut0 *displays* khaki — eyeballing decodes lies; census by raw nibble). All 4
    kinds → leaf cutouts (green/brown, per-kind sizes). Real mushroom/rock art = future VRAM
    upload.
  - Hopper FMV during tests = **game-over cutscene** (lives drained), not a VM trigger.
- **v3 (same day): PEBBLE GROUND + integrator corrections.**
  - Ground now shows the pristine-LEVEL01 **pebble cobbles**: the v2 window was folding the
    ground's 64×64 pebble tile (@(0,192) clut 0x3FFC — the mylevel recipe it already used!) onto
    the 32-px wall tile. Now per-CLUT windows (pebble mod-64 / wall dirt mod-32 / else clear) +
    the exporter wraps 64×64 rects too (≤4 repeats). Verified in-game.
  - **0x80036CD8 is the integrator's NORMAL position COMMIT, not a failure revert** — patching it
    froze all movement (reverted). The warps are garbage resolver outputs committed there; the
    walls-cave teleport guard remains the fix. `0x80035F24 is mid-function — never stomp it.`
    EXE patch offsets: `off = vaddr − 0x80010000 + 0x800` (ghidra's 0x8000F800 is wrong for
    file patching).
  - Operator's "can't run forward, berry flies through" spot did **not** reproduce on a fresh
    boot of this build (state-dependent; their session save kept for re-analysis). Candidate
    future kill-switch if it recurs: force the integrator's grounded-read (0x80036C38) to 0 →
    all movement resolves via the permissive airborne resolver (live-tested OK).
- **v4 (same day): ADAPTIVE NEAR-FIELD SUBDIVISION** (operator: "ground stretches when walking").
  PS1 affine warp scales with triangle size; pristine LEVEL01 = small polys. Export-side
  subdivision can't reach that density (blob/vert caps), so the render cave now splits NEAR
  terrain tris at draw time — view-space midpoint subdivision (perspective-correct), 2 passes
  (nearest vert <90k, then <40k; extent gate 30k; ≤16 sub-tris/tri) with zero blob cost.
  Layout shifted: render budget →0x2DF8, GRAIN →0x801F39F8/0x3A00, RENDER_PAD →0x3D00
  (blob @0x801F3D00, cap 20736 — **only 208 B free**). Verified: stable uniform pebbles in the
  near field while walking; physics suite clean (any residual native warp is a ≤1-frame flicker
  the teleport guard reverts).
- **v5 (same day): 30 FPS RESTORED, subdivision kept.** The v4 split defaults covered most of
  the visible field → 20fps. Retuned with live knobs (`0x801FE03C/40/44`) + a proper FPS
  instrument (display-flip counting via `crtc.vram_source_rect` X, one flip per game frame):
  at the worst scene (spawn vista, walking) OFF=30 / **26k/12k+gate120k=30** / 90k/40k=20 fps.
  Baked: split only GIANT sheets (extent ≥120k) near the camera — exactly the affine-stretch
  offenders — never the medium pad/wall cells. Verified ~30fps walking at spawn.
  Also fixed: the teleport guard's WPREVY collided with `DS_MUL_LIVE` @0x801FE030 (was silently
  forcing the linear depth-sort path since v3) — moved to 0x801FE038.
- Published: `build/ABL_AILEVEL.bin` (md5 09d1b80b…).

## Known quirks / bug leads (work list)
- [ ] A few authored props render as **bead-chain garbage** (payload model parsed with mismatched per-record aux bytes +0xC..0xF? investigate per-class record templates); one transient full-width green streak seen once.
- [ ] Objects can **peek over near walls** at some angles (depth-LUT bucket imprecision — known GTE-path deferral).
- [x] The **branch prop** renders huge across the view — v3 parks it on the far west field flank (−65,82), off the main sightline.
- [ ] `type-0x3f` count = authored+2 = the 2 **surplus native telescopes** (kind 0x30 is delete-unsafe). They sit at their ORIGINAL LEVEL01 coords (Z ≈ 667k / 117k) which the v3 level now overlaps — consider PARKING their XZ far outside the playfield (in-place move is proven-safe) if they cause stray telescope-view triggers.
- [ ] **Telescope hint view at scale**: during warp-probing, a telescope-style iris view engaged and panned the (now-empty) native landmark area; suspected trigger = warping near a telescope. Needs one clean playtest: walk into the authored telescope (0,176), confirm the hint view plays AND returns control in a custom level.
- [ ] **Red berry not placeable** on the LEVEL01 host (no native template) — by design; revisit if a template-crafting append path is added.
- [ ] Prop Y is authored at fixed heights — props on the terrace/finish needed manual z; a floor-snap export helper would remove the fiddling.
- [ ] Dot's platform-hop legs are straight lines (she flies) — check she doesn't clip through pads visually.
- [ ] Playtest checklist: trampoline-free traversal of the pads (jump ≈6.3k rise) · worm ambush triggers at the bait · gold berry permanence (quota 5→4) · telescope contact · FLIK letters collect · exit fires at the pad (careful: the exit sphere r=3k at (0,197) — don't wander in early).
- [ ] Perf: 294 tris + 50 props at LEVEL01 scale — spawn/field run held ~30fps in verification; watch grazing angles across the 155k-wide field (the known mode-2 texture-fill limit).

## How this was made (for the next level)
Terrain = subdivided grids with the **dirt material recipe** + per-face 0..1 UVs; steep quads auto-become walls; `blocker_*` boxes on open flanks. Props = `prop_NN` empties with `abl_payload` (semantically-known set: grass `0x5de0` · clover `0x5840` · stone `0x7680` · big berry `0x76d8` · acorn `0x5278` · branch `0x5220` · leaf `0x4ba8` · leaf tube `0x5260` — more in `build/pass1_palette/`). Enemies/pickups/route per the cheat sheet.

## Related
[[Tier 3 - Blender Prefix Cheat Sheet]] · [[Tier 3 - Blender Pipeline Plan]] · [[Prop and foliage catalog]] · [[Dot guide NPC]] · [[Enemy spawn architecture]]
