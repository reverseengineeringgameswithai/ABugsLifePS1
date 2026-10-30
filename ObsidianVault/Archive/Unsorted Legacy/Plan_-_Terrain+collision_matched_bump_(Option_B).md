---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Geometry/Plan - Terrain+collision matched bump (Option B).md
aliases:
  - "Plan - Terrain+collision matched bump (Option B)"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Geometry/Plan - Terrain+collision matched bump (Option B).md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Plan - Terrain+collision matched bump (Option B)
type: plan
status: IN PROGRESS (G33)
confidence: mixed
tags: [plan, terrain, collision, leveleditor, optionB, g33]
updated: 2026-06-18
---

# Plan — Permanent matched terrain+collision bump ("hand in hand")

> [!success] **Step 6 update (2026-06-24): both disc-edit levers PROVEN; blocker #8 closed.** Visible terrain
> sculpt (`tools/sculpt_terrain.py`, LEVEL.DAT vertex-Y brush) → **36% visible deform** in-game; permanent
> collision edit (`tools/edit_collision_sector.py`, chunk-32 sector origin-Y → recompress → splice →
> `tools/build_autolayout_disc.py`) → **Flik's footing moved exactly −8000**. The ballooned LEVEL.RAW BOOTS, so
> #8's size-neutral patch is NOT needed (auto-layout rebuild + by-name loading suffices). **LOCALIZED match
> now SOLVED too (2026-06-24):** `tools/probe_collision_sector.py` binary-searches all chunk-32 sectors to find
> the resolver's SELECTED floor (spawn = sec99) where XZ-proximity failed; and the calibration is **1:1 in
> src/node units** (terrain node-frame == runtime÷32 == collision src-frame — no empirical 1450). PROOF: a
> matched bump (terrain payload + sec99, both Δ −500) made **Flik ride up ~15869 ≈ 16000** onto the raised
> visible floor. Residual: walls (new geometry), GUI brush, offline XZ→sector map. NOTE: the 223-sector array
> spans chunk 32→33 (189 in chunk 32). See [[LEVEL01 Level-Edit Punchlist]] §1a/§2.

> [!warning] **M7 correction (2026-06-21):** the **visible** floor lever is **LEVEL.DAT / [[FUNC_80010000]]** (Candidate A), *not* chunk 35 — the chunk-35 mesh renders **occluded** ([[Gap Audit|GAP-0011]]). Read "terrain (chunk 35)" below as the *occluded* terrain layer; for a **visible** bump, edit the DAT payload. The collision lever (chunk 32) is unchanged.

> Goal: a localized, PERMANENT (on-disc) floor change where the **terrain layer (chunk 35, occluded)** and the
> **collision (chunk 32)** move together, so Flik visibly steps up/down onto a solid, visible bump.
> Builds on the proven [[Finding - LEVEL.RAW is compressed|LEVEL.RAW codec]] + seed disc-edit pipeline.

## 🏛️ Editor architecture — terrain source choice + matched collision (G33b synthesis)
There are **two visible-floor sources** in LEVEL01 and they are NOT equivalent for editing:

| | LEVEL.RAW **chunk 35** | LEVEL.DAT **Candidate A/B/C** |
|---|---|---|
| Coordinate space | **model-space** (need GTE transform / screen-localize to target by world XZ) | **world-space** (G27) — index directly by world XZ |
| Compressed on disk | yes (large, inside LEVEL.RAW) | **no** — vertex bytes directly patchable |
| Permanent edit | balloons on recompress (#8) → needs size-neutral patch | **same-size in place** (G28, operator-confirmed) |
| Visible effect | subtle / rendering-limited (G30) | the actual dramatic floor deform (G28) |
| Drawn by | [[FUNC_800172DC]] (rtpt `0x80017464`) | [[FUNC_80010000]] |

**⇒ For a level editor, prefer DAT Candidate A/B/C as the terrain target:** it's world-space (so it **joins
to collision by world XZ with no coordinate gymnastics**), uncompressed (permanence = a plain byte patch),
and it's the layer that visibly deforms. Chunk 35 is the fallback for regions A/B/C don't cover.

**Matched-edit recipe (both world-space):** at a chosen world XZ, find Candidate-A verts + the chunk-32
collision sector(s); for a raise ΔW → terrain vertex `−= ΔW`, collision src origin-Y `−= ΔW≫5` (subtract = up).

**Three remaining gates (ranked):**
1. ~~Permanent collision edits~~ **→ LARGELY RESOLVED (G34):** the game loads files **by name**, resolving
   LBAs from a disc-read directory table (`0x80086c00`, BSS), so **LBA shifts are tolerated**
   ([[Finding - File loading is by-name (LBA-shift tolerant)]]). ⇒ permanent edits = **recompress chunk +
   rebuild**, even for large chunks 32/35 — no size-neutral patch / provenance rewrite needed. The balloon
   (#8) only constrains the `cd.overlay` live-iteration path, not the rebuild. *Final confirm: one boot-test
   of an LBA-shifting rebuild (expected to pass).*
2. **Per-region floor-source map** — probe which renderer draws the floor at a clicked spot (`fcn.80010000`
   DAT vs `fcn.800172dc` chunk-35). Pieces exist; coverage map not built.
3. **Robust collision-sector pick** — `0x8009C230` candidate list worked in openground, missed at `_1`; for
   reliability read the resolver's *selected* plane ([[FUNC_800345CC]]), not just the candidate set.

## What's already CONFIRMED (G33)
- **Collision lever works, ~1:1, controlled.** Jump-in-place test (terrain held constant): runtime sector
  origin-Y (`0x800A7E48 + i*0x30 + 4`) edited `−8000` → Flik Y `−85924 → −93715` (Δ −7791). Screenshot
  `tools/flik_above_terrain.png`. **Sign: more-negative Y = UP; subtract origin-Y to raise Flik.**
- **Resolver only runs when Flik MOVES** — passive frame-advance does nothing; needs walk/jump (operator-driven).
- Coordinate spaces: collision sectors = **world space**; terrain buffer `0x8012C1D0` verts = **model space**
  (e.g. quad 138 `(1498,−1782,62167)` vs Flik world `(3065,−85924,215520)` → rotation, not a simple scale).

## Recovery / environment
- DuckStation: `~/duckstation/build-release/bin/duckstation-qt-logged` ; relaunch with the game arg:
  `"~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue"`. Debugger binds port 2346.
- Work save: `~/.local/share/duckstation/savestates/SCUS-94288_terrain_collision_floor.sav` (=copy of `_1`).
- Client: `cd ~/Downloads/ABL/tools && python3 -c "from abl_dbg import D; d=D()"`.
- ⚠️ **Bulk `writeMemory` and `pressButton` CRASH the debugger link** — use per-word writes; `debugger.resume`
  to un-pause after a crash; reload the save to restore state.

## ✅ Blocker #1 RESOLVED (G33) — on-disk collision lever fully mapped
The runtime sector table `0x800A7E48` (223 × 0x30) is built by converter `0x80030F60` from a **source
record array in LEVEL.RAW chunk 32**:
- **Source array** starts at **global decompressed offset `0xcd248`** (chunk-32 local **`0x36570`**) in
  `tools/LEVEL_RAW_decompressed/LEVEL.RAW.decompressed`. **Stride `0x4c`**; src record `i` ↔ runtime sector `i`.
- **Record layout:** `+0x00,+0x04` = header words; **`+0x08/+0x0c/+0x10` = origin (X,Y,Z) ≫5** (int32);
  then zeros (planes live in a *separate* structure, not in this record).
- **Converter just copies `src ≪5`** into the runtime origin (verified: sec0 src Y `−3761` ≪5 = runtime
  `−120352`; sec1 src `(−204,−2043,−13854)` at record+0x4c ✓). It does **not** recompute origin from planes.
- **Origin-Y is the additive floor base; plane refpoints are relative (small int16).** The runtime test moved
  Flik 1:1 by editing origin-Y alone (planes untouched), so a **permanent** edit of `src+0xc` shifts the floor
  the same way — **no plane editing required.**

**Permanent collision-floor edit recipe:** to set sector `i`'s floor to world-Y `W`, write `W≫5` (int32)
at dump offset `0xcd248 + i*0x4c + 0xc`, recompress chunk 32, splice, rebuild. (More-negative = up.)

## ✅ Blocker #2 RESOLVED (G33) — model↔world scale calibrated
Captured the terrain renderer's transform via `execTrace` at `FUNC_800172DC` rtpt **`0x80017464`**
(`capture: gte.RT_0..RT_4, gte.TRX/TRY/TRZ, gte.V0_XY, gte.V0_Z, gte.SXY2`; `a1=0x8012c1d0` confirms it's
the terrain buffer). Decoded the model→view matrix (RT regs are 4.12 fixed, packed 2/word):
```
model->view = [ -1.5491  +0.0520  +0.3940 ]
              [ +0.0049  +0.9934  -0.1108 ]
              [ -0.2493  -0.1055  -0.9622 ]
```
The GTE **camera rotation is orthonormal**, so each **column norm = the model→world scale** for that model
axis (camera-invariant — true for any frame):
- **model-Y: |col| = 1.000, view-Y component +0.993 → terrain HEIGHT axis, world-scale 1.0.**
- model-X |col| 1.569, model-Z |col| 1.046 (horizontal, non-uniform — irrelevant for a vertical bump).

**Matched-edit calibration:** for a world floor change **ΔW**:
- collision src origin-Y (chunk 32, record `+0xc`) `+= ΔW≫5`  (per blocker #1)
- terrain vertex model-Y (chunk 35, high16 of vert words `+0x04/+0x0c/+0x14/+0x1c`) `+= ΔW`
- → **terrain Δ = 32 × collision-src Δ, same direction.** (Terrain-Y *sign* vs world-up = blocker #7,
  one confirming test; scale is camera-invariant so stable.) Method: `execTrace` is read-class (safe);
  forces the interpreter, so `removeWatch` when done; re-arm after any `loadState`.

## ✅ Blockers #3 & #4 RESOLVED (G33) — exact sector + clamp set via the candidate list
The floor resolver [[FUNC_8003633C]] (commits player-Y at `0x80036cec`) **runs even when Flik is idle**
(~3 hits / 5 frames) — so its inputs are readable without operator movement. Its per-position **candidate
plane list** lives at **`0x8009C230`** (≈44 entries, dup'd; here 28 unique). Map each plane → owning sector
via the sector `+0x10` block ranges (largest `blkptr ≤ plane_addr`).

**#4 — exact sector:** the candidate planes for Flik's spawn belong to sectors
**`{87, 89, 96, 97, 105, 106, 124, 126, 171}`**. The *winner* (his actual floor) = the candidate sector
whose origin-Y is nearest **below** Flik → **sec124** (origin −87520, Flik −85924). To target any other
spot: position Flik there, read `0x8009C230`, re-map. (No need to isolate the single winner — see #3.)

**#3 — neighbor-clamping:** the resolver blends across all candidate planes, so a single-sector edit gets
diluted. **Fix: edit the entire candidate-sector set together** by the same ΔW — every plane the resolver
could pick moves consistently, so there is nothing left to clamp against. On-disk targets (chunk 32,
`0xcd248 + sec*0x4c + 0xc`, value `≪5`): sec87 `0xcec28`, sec89 `0xcecc0`, sec96 `0xceed4`, sec97 `0xcef20`,
sec105 `0xcf180`, sec106 `0xcf1cc`, sec124 `0xcf724`, sec126 `0xcf7bc`, sec171 `0xd0518`.
> ⚠️ Caveat: origin-Y moves the **whole sector** (floor *and* its wall planes); the candidate set also
> contains wall planes (horizontal normals, e.g. sec106 plane normal `(1,3,−3575)`). For a vertical floor
> bump that's acceptable (the local block rises together), but it is **not** a pure floor-only lever.

## ✅ LIVE matched bump ACHIEVED (G33b, openground) + location-dependence found
**Success in `SCUS-94288_g30_openground.sav`:** raised the 86 chunk-35 floor quads (model-Y `−8000`) **and**
the 4 collision candidate sectors `[103,104,125,169]` (origin-Y `−8000`), then drove Flik's jump
(`setControllerState cross`). **Flik rose −7859 (~the full −8000, ~1:1) and stayed grounded on the raised
floor** (not floating) — terrain + collision moved *together*. Frame pixel-diff baseline→matched = **42.4%**
changed (`og_match_0.png` / `og_match_1.png`). This is the "hand in hand" proof.

**Key corrections to earlier assumptions:**
1. **⚠️ SUPERSEDED (M7, 2026-06-21):** this read *"Terrain (chunk-35) edits DO register — just subtle"*
   (pixel-diff 4.28%; openground terrain-only 1.75%, floor region). The later 7-scene neutralize
   ([[Experiment - Visible floor renderer neutralize]]) found chunk-35 renders **occluded** (~0 visible px)
   and the "visible terrain deform" was a `0x80010000`↔`0x800172dc` address swap — the **visible** floor
   lever is LEVEL.DAT / [[FUNC_80010000]] ([[Gap Audit|GAP-0011]]). The big 42.4% in the matched run is
   mostly Flik+camera rising (collision).
2. **Localized collision is location-dependent:** the candidate-set lever worked in **openground** (Flik
   `−7859`) but **failed at `_1`** (`+222`). So `0x8009C230` → sectors is reliable in some spots, not others
   — at `_1` the resolver's *selected* plane differs from the candidate set (needs a [[FUNC_800345CC]] trace).
3. **Visible-floor source is location-dependent** (level-editor requirement, per operator): some regions =
   LEVEL.RAW chunk 35, others = LEVEL.DAT Candidate A/B/C ([[Finding - Candidate A is DAT-backed visual terrain]]); **collision is uniformly chunk 32**. An editor needs a per-region "which renderer draws this
   floor" probe (`fcn.800172dc`/chunk-35 vs `fcn.80010000`/DAT) to target the right source.
4. **Tooling:** `scatterWrite` caps ~24 items/call (chunk it); after `loadState` the terrain renderer needs
   ~several settle frames before `execTrace` catches it (`run(1)` right after load → 0 hits). DuckStation
   **crashed once** during the contrast run — relaunch: `duckstation-qt-logged "<game>.cue"` (port 2346).

## ✅ Keystone + #5/#6/#7 RESOLVED, #8 PARTIAL (G33b)

### Terrain spatial localization (keystone) ✅
`execTrace` at `0x80017464` (RTPT) with `capture:["a1","gte.SXY0","gte.SXY1","gte.SXY2"]`:
- **`a1` walks the terrain buffer** `0x8012C1D0`→`0x8012E744` — `a1 − 0x8012C1D0` = the quad's **chunk-35
  local offset** (directly editable).
- **SXY = the quad's screen position** (1 RTPT lag; RTPT batches 3 verts so refine pairing for per-quad use).
- The 86 floor quads render as a **narrow center strip** (screenX 221–275, screenY 133–219). **Floor right in
  front of Flik = highest-screenY quads: buffer offsets `0x01c4, 0x031c, 0x028c, 0x02ec, 0x034c, 0x02bc, …`**
  Each quad 0x30; vertex model-Y = high16 of words at `+0x04/+0x0c/+0x14/+0x1c`.

### #5 tooling ✅ — robust APIs
- **Input:** `emulator.setControllerState {buttons:{cross:true}}` + `emulator.advanceFrames {frames}` (re-applied
  each frame; confirmed Flik jump, Y span 6510). `clearControllerState` to release. Buttons:
  `up/down/left/right cross/circle/square/triangle l1/r1/l2/r2 start/select`. **Avoid `pressButton`** (crashed link).
- **Batch writes:** `debugger.scatterWrite {writes:[{address,type,value}]}` (worked). **Avoid one giant `writeMemory`**.

### #6 disc-overlay ✅ — `cd.*` already exists (no rebuild loop)
`cd.overlayFile {path:"LEVEL01/LEVEL.RAW", hex}` → resolves to LBA 3069 and **substitutes the bytes the game
reads off CD, live, without rebuilding or swapping**; **persists across loadState** (install once, reload to
iterate). Also `overrideSectors`, `clearOverlay(s)`, `listOverlays`. **Iteration loop = patch bytes →
`cd.overlayFile` → loadState pre-level → walk Flik.** ⚠️ Replacement must NOT exceed the file's on-disc
sector span (`-32602`) — same size limit as #8.

### #7 terrain-Y sign ✅ (analytical)
From #2's matrix, model-Y → view-Y `+0.993`; PS1 screen-Y increases downward → **+model-Y = down, −model-Y =
up**. Same convention as world/collision: **subtract to raise, add to lower.** (Empirical single-quad confirm
was inconclusive because RTPT transforms 3 verts/call, so the a1↔SXY pairing needs refining — minor follow-up.)

### #8 two-chunk rebuild ⚠️ PARTIAL — the one real remaining task
Splicing two edited chunks is mechanical, BUT **full literal-recompression balloons large chunks**: chunk 32
`182287→~241696` (+59 KB), chunk 35 `6948→~13841` (+7 KB) → **+32 sectors**. That exceeds **both** the disc
LBA budget *and* the `cd.overlay` sector-span limit (LEVEL.RAW has only ~**1820 B** headroom inside its 366
sectors). **So large collision/terrain edits MUST be size-neutral (in-place minimal-patch of the few changed
compressed bytes).** The provenance tracker for that is currently **broken** (output/prov misaligned 23860 vs
33548, and offsets wrong — only 20/2000 literal bytes match) → **rewriting it is the remaining blocker.**
Small edits (≤1820 B growth, e.g. seeds) already work via rebuild or overlay.

## Blocker status table
| # | Blocker | Status | Notes |
|---|---------|--------|-------|
| 1 | On-disk collision lever: chunk-32 source format + origin-vs-plane | **✅ RESOLVED (G33)** | Lever = chunk-32 sector-src record `+0xc` (origin-Y, `<<5`). See "Blocker #1 RESOLVED" below. |
| 2 | Model↔world SCALE calibration | **✅ RESOLVED (G33)** | Terrain height = model-Y; model→world Y-scale = **1.000** (camera-invariant). See "Blocker #2 RESOLVED" below. |
| — | Terrain spatial localization (keystone) | **✅ RESOLVED (G33b)** | execTrace `0x80017464`: `a1` = buffer offset (= chunk-35 local), SXY = screen pos. Floor-ahead quads identified. See below. |
| 3 | Collision neighbor-clamping | **✅ RESOLVED (G33)** | Clamp set = the candidate-plane sectors in `0x8009C230`; edit them all together. See below. |
| 4 | Pin exact sector for a target spot | **✅ RESOLVED (G33)** | Candidate list `0x8009C230` → owning sectors; readable idle. See below. |
| 5 | Tooling: input + bulk-write crash the link | **✅ RESOLVED (G33b)** | Use `emulator.setControllerState`+`advanceFrames` (input) and `debugger.scatterWrite` (batch). Crashes were from `pressButton`/giant `writeMemory`. |
| 6 | Disc-boot iteration loop | **✅ RESOLVED (G33b)** | `cd.overlayFile` ALREADY EXISTS — overlay `LEVEL01/LEVEL.RAW` live (LBA 3069), persists across loadState. No rebuild needed. |
| 7 | Terrain model-Y sign | **✅ RESOLVED (G33b, analytical)** | Subtract model-Y to raise (model-Y→view-Y +0.993, screen-Y down). Empirical single-quad confirm pending (RTPT-batch a1↔SXY alignment). |
| 8 | Two-chunk rebuild (32+35) | **⚠️ PARTIAL (G33b)** | Splice works, but literal-recompress balloons large chunks **+32 sectors** > both LBA budget AND `cd.overlay` span limit → large edits **must be size-neutral** → needs provenance rewrite. See below. |

## Recommended order
5 (tooling, cheap, unblocks live tests) → 1 (make-or-break data) → 2 + localization (same trace) →
3,4 (physics) → 7,8 (mop-up); adopt 6 for fast iteration.

## Related
[[MEM - Collision sector table 800A7E48]] · [[MEM - Terrain vertex buffer 8012C1D0]] ·
[[Finding - Localized terrain edit]] · [[Finding - Collision on-disk source is chunk 32]] ·
[[Finding - LEVEL.RAW is compressed]] · [[FUNC_800172DC]] · [[FUNC_8003633C]]
