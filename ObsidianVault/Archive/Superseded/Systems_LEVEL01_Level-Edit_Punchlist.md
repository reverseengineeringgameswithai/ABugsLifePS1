---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/LEVEL01 Level-Edit Punchlist.md
aliases:
  - "LEVEL01 Level-Edit Punchlist"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/LEVEL01 Level-Edit Punchlist.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/LEVEL01_Level-Edit_Punchlist.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: LEVEL01 Level-Edit Punchlist
type: system
status: working punchlist — tackle one item at a time
confidence: SYNTHESIS (2026-06-23, cross-verified against Gap Audit / Blockers / Geometry / placement notes)
updated: 2026-06-23
tags: [system, leveleditor, level01, punchlist, gaps, blockers, terrain, collision, placement]
---

# LEVEL01 Level-Edit Punchlist

> **Purpose.** One consolidated, honest gap/blocker list for *fully* editing LEVEL01: the ground (and its
> collision), and the placement of every object — enemies, berries, tokens, grains, FLIK letters,
> telescopes, the player spawn, and the level exit. Built to be worked **one item at a time**.
> Source of truth for evidence stays in [[Gap Audit]] / [[Blockers]] / [[Geometry pipeline]] / the per-system
> notes linked below; this note is the *editing-capability* cross-cut.

## Status legend
- ✅ **PROVEN** — disc-edit relocation/edit tested in-game on a rebuilt (or live-overlaid) disc.
- 🟢 **READY** — mechanism + on-disc lever confirmed; edit path exists but the *specific* operation (e.g. one operator boot-test, or wiring a CLI tool) is the only thing left.
- 🟡 **PARTIAL** — core decoded; a named residual blocks the clean/general/permanent path.
- 🔴 **OPEN** — the editable source/lever itself is not yet located.

## Scope — operator-requested editor features (2026-06-23)
The level editor must, for LEVEL01, let the operator:
1. **Net-new grains** — *add and remove* grains to raise/lower the count (not just move). → §6 + **CC5**
2. **Type a new "FLIK" word** (e.g. ATTA) for the HUD + in-world spinning glyph letters. → §7
3. **Add / remove berries**, including the **net-new blackberry** that doesn't exist in the retail game. → §4 + **CC6**
4. **Sculpt the floor by mouse-drag** — hills, walls, varied terrain. → §1 (+ §2 collision)
5. **Add / remove / move scenery objects** — mushrooms, fences, rocks, misc props. → **§11 (new)**

Items 1–3 are close (the *relocation/art* halves are proven; the new work is **delete** + **net-new-kind
composition** + **GUI wiring**). Items 4–5 are the heavy lifts (interactive vertex sculpt + wall geometry;
decor placement/rotation/catalog).

**Two independent axes.** §1–§11 are the **edit-capability** axis (can we *change* a thing on disc).
**§12 is the *visual-fidelity* axis** — "fly through LEVEL01 and have it look ~1:1 like the game." You can
edit without 1:1 visuals and vice-versa, but the operator's goal needs **both**: §12 covers textures, real
object models, sky, lighting, animation, and camera/projection match.

## TL;DR — what's editable today vs. what's left
| Element / capability | Source | Status | The one thing blocking "done" |
|---|---|---|---|
| **Grains — move** | LEVEL.DAT type-0x3f entries 0–49 (kind 0x14) | ✅ PROVEN | — (HUD total + dynamic all-grain emblem also done, commit `6c9445c`) |
| **Grains — ADD (count up)** | append type-0x3f kind-0x14 | ✅ PROVEN | append path proven; emblem auto-tracks live count |
| **Grains/berries/tokens — REMOVE (count down)** | delete a type-0x3f record | ✅ PROVEN | — (CC5 done: `delete_type3f_entries.py` + editor "Delete Selected"; in-game 70→60 grains booted & parsed) |
| **Berries — move/add existing** | LEVEL.DAT type-0x3f entries 54–57 | ✅ PROVEN | — |
| **Berries — net-new (blackberry)** | type-0x3f entry **+** EXE code-caves | ✅ PROVEN | CC6 done: editor dropdown "Blackberry (net-new berry)" → composed code+data build; in-game picked up (equip 0x05) + thrown |
| **FLIK word (type a 4-letter word)** | glyph art in LEVEL.RAW/LEVEL1.RAW | ✅ PROVEN | GUI field + `build_flik_word_disc.py` done; in-game "TAKA" rendered w/ spin. Letters limited to art (A F I K L T); non-4-letter OPEN |
| **Seed tokens** | LEVEL.DAT type-0x3f entries 58–66 | ✅ PROVEN (move/append/delete/kind-swap) | — (kind-swap in-game tested 2026-06-24: entry 63 0x29→0x2b) |
| **Telescopes** | LEVEL.DAT type-0x3f entries 67–69 (kind 0x30) | ✅ PROVEN | — (relocation in-game tested 2026-06-24: entry 67 → X 3372; RISK flag is confirm-only) |
| **Ground — raise/lower (hills/pits)** | LEVEL.DAT (Candidate A/B/C, [[FUNC_80010000]]) | ✅ PROVEN | `sculpt_terrain.py` height brush + `floor_source_map.py` (spot-driven `--at-runtime-xz`); in-game 33–36% deform. Residual: mouse-drag GUI |
| **Walls** | **LEVEL.RAW chunk-35 master mesh** ([[FUNC_800172DC]]) | 🟡 live-editable | RE'd step 11: walls = chunk-35 (not DAT floor); live poke of buffer `0x8012c1d0` reshapes the wall (43%). Permanent on-disc blocked on the master-mesh vertex/command decode |
| **Ground — new geometry / new faces** | mesh payload (add faces) | 🔴 OPEN | adding vertical faces = new geometry + byte-confirmed winding (jump table 0x8001036C) |
| **Ground — collision (permanent)** | LEVEL.RAW chunk 32 (sector table `0x800A7E48`) | ✅ PROVEN | `edit_collision_sector.py`; in-game disc edit moved Flik 1:1 (−8000). Residual: reliable LOCALIZED sector pick (FUNC_800345CC) for a matched *hill* |
| **Scenery objects — MOVE / REMOVE** | LEVEL.DAT pass-1 records (`0x1504`, stride 0x14) | ✅ PROVEN | `tools/edit_pass1_records.py` move/set/delete (relocation-aware); in-game verified (set #20 coords loaded, delete → 483 records). Residual: pass-3 (6 props) position undecoded |
| **Scenery objects — ADD net-new** | new pass-1 record → mesh payload | 🔴 OPEN | no object→asset catalog; net-new decor record injection unproven |
| **Scenery objects — ROTATE** | per-instance `M_obj` | 🔴 OPEN | rotation/scale matrix source undecoded (translation-only today) |
| **Enemies/objects — patrol (mover-VM)** | LEVEL.DAT rec1 @ 0x468 (type 1, 104 waypoints) | ✅ PROVEN | `edit_dat_coord_record.py`; in-game moving rec1 relocated a mover object (10.73% frame change) |
| **Enemies — stationary anchor** | compressed RAW chunk-31-class record | 🟡 PARTIAL | live-proven movable; compressed-chunk disc-edit not yet wired/tested |
| **Enemies — chaser spawn areas** | LEVEL.DAT records 0x94c/0xa10/0xad4 (types 11/12/13) | ✅ PROVEN editable | `edit_dat_coord_record.py`; spawn fn 0x8004d698 reads them (traced). Chase itself is Flik-relative (N/A by design) |
| **Player spawn** | resident EXE table `0x80077314` (`SCUS_942.88` +0x67b14) | ✅ PROVEN | initial spawn solved; checkpoint *respawn* anchor is runtime-computed |
| **Level exit point** | **not located on disc** | 🔴 OPEN | the exit *trigger position* (where Flik stands) is undecoded |

> This table is the **edit-capability** axis. For the **"looks ~1:1 in the editor"** axis (textures, real
> object models, sky, camera match, animation), see **§12**.

---

## 1. Ground geometry — VISUAL surface
**Data:** the visible walkable floor is **LEVEL.DAT payloads drawn by [[FUNC_80010000]]** (Candidate A/B/C;
world-space; *uncompressed* on disc — a plain byte patch). NOT chunk-34/35 — that mesh layer renders
**occluded** ([[Gap Audit|GAP-0011]] / [[G30 - Terrain render source]]).
**Status: ✅ PROVEN as a sculpt tool (2026-06-24, step 6).** `tools/sculpt_terrain.py` applies a height brush
(center + radius + falloff) to a payload's vertex-Y (size-preserving byte patch). **In-game: a mound on the
under-Flik tile (payload 0x1b9f0) → dramatic visible deform (36% frame change).** Vertex layout: stride 0xc,
**Y@+2** (G28 lever `v16 Y @ 0x18992`). Offline placement formula `world = T_obj + v_local` from the LEVEL.DAT
node array (LEVEL01 @ `0x45f0`, stride `0x18`; `T_obj`@+0/4/8, payload@+0x14) is 3-way verified (disk == runtime == formula).

**Remaining gaps**
1. ~~Per-region floor-source map~~ **✅ DONE (2026-06-24, step 9)** — `tools/floor_source_map.py` builds the
   coverage map (30 floor payloads → world XZ footprint via `world = T_obj + v_local`) and answers "which
   payload draws a clicked XZ." Validated: Flik's spawn (live runtime XZ ÷32) → payload `0x1b9f0` (the proven
   under-Flik tile). Wired into `sculpt_terrain.py --at-runtime-xz X:Z` (auto-picks the payload + centers the
   brush) — end-to-end verified: a spot-driven sculpt at spawn → 33.69% visible deform. (Chunk-35 occluded
   fallback: a query outside all DAT footprints returns "none" → that region is the chunk-35 layer.)
2. **Rotated-mesh `M_obj`** — for the FLOOR this is a **non-issue** (the translation-only `world = T_obj +
   v_local` map correctly predicts every floor payload's coverage incl. the under-Flik tile, so LEVEL01 floor
   tiles are unrotated). Per-instance rotation/scale may still apply to some **decor** props (§11.4) — undecoded there.
3. **Photogenic localized pit** is rendering-limited (camera-follows-Y, uniform pebble texture, bottom-clip
   at 512×224). The deform *is* real; making it *dramatic* needs GTE-calibrated localization (P1 in [[Open Questions]]).

**To close:** build the per-region source probe; capture the GTE transform (`execTrace` the emitter) to
recover `M_obj`. **Tools:** `tools/analyze_g27_floor_candidates.py`, `level_editor/scene_importer.py`.

### 1a. Drag-to-sculpt (hills, walls, varied terrain) — operator req. #4
**Status: 🟢 height-only sculpt DONE as a CLI brush (2026-06-24, step 6, in-game verified); mouse-drag GUI +
walls + reliable localized collision remain.** What shipped this step:
- **Terrain height brush — `tools/sculpt_terrain.py`** (`--center-vertex`/`--center-xz`, `--radius`,
  `--delta`, `--falloff smooth|linear|flat`): edits a floor payload's vertex-Y (stride 0xc, **Y@+2**;
  +Y=down/pit, −Y=up/hill) as a size-preserving byte patch (the G28 lever, generalized to a falloff brush;
  works on any FUNC_80010000 payload via `--payload-off`). **In-game: a strong mound on the under-Flik tile
  (payload 0x1b9f0) booted to a dramatic visible deform — 36% of the frame / 58% of the floor region changed.**
- **Collision disc-edit — `tools/edit_collision_sector.py`** (chunk-32 sector origin-Y; `--sector`/`--near-xz`,
  `--delta-y` runtime or `--src-delta-y`): decompress chunk 32 → edit → recompress → splice → auto-layout
  rebuild (`tools/build_autolayout_disc.py`; the ballooned LEVEL.RAW boots — de-risked by §7). **In-game:
  raising all chunk-32 sectors by runtime −8000 raised Flik's footing by exactly −8000 (Y −8565 → −16565,
  same XZ) — the permanent disc collision edit moves Flik 1:1.** (NOTE: the 223-sector array spans chunk 32
  into chunk 33; this tool edits the 189 sectors in chunk 32.)

Remaining gaps for full *mouse-drag* sculpting:
1. **Interactive vertex pick/brush in the GUI** — `scene3d.py` ray-picks *pickups*, not terrain vertices; the
   brush is CLI-only today (needs a viewport vertex/brush selection model).
2. **WALLS = a separate render layer (chunk-35), 🟡 live-editable; permanent + new-faces still open.**
   RE'd in step 11 ([[G56 - Wall chunk-35]] / `src_re_geometry/geometry_g56_wall_chunk35.md`): the visible
   **walls (darker dirt) are the chunk-35 terrain master mesh** drawn by [[FUNC_800172DC]] (GP0(3c)), NOT the
   DAT floor (lighter ground). **Live edit works** — poking the runtime terrain buffer `0x8012c1d0` (0x30
   quads, Y high16 @ +4/+0xc/+0x14/+0x1c; −Y=up, scale 1.0) reshaped the wall (43% of the turned frame).
   **Permanent (on-disc) is blocked:** decompressed chunk-35 is a **master mesh** (header marker `02 01`,
   count `0x16`@+0xa, then a **vertex+command stream** — not fixed quads), so a blanket quad-stride edit
   corrupts command bytes → **crashes the level load** (a single aligned vertex edit boots fine). ⇒ permanent
   wall edits need the **master-mesh vertex/command decode** (the chunk-34/35 gap). Adding *new* vertical
   faces (the original §1a.2 framing) is a further step on top of that.
3. ~~Reliable LOCALIZED auto-matched collision~~ **✅ DONE (2026-06-24, in-game)** — a localized matched bump
   now works: terrain raised + collision raised at one spot, **Flik rode up ~15869 ≈ the 16000 target** onto
   the raised visible floor. Closed both sub-gaps: (a) **selected sector** found by a live poke-probe
   (`tools/probe_collision_sector.py` — pokes each candidate sector's runtime origin-Y, watches which moves
   Flik; spawn floor = **sec99**, confirmed −6000 poke → Flik −5952 ~1:1), and (b) the **calibration** =
   terrain node-frame == runtime÷32 == collision src-frame, so **terrain-local-ΔY = collision-src-ΔY (1:1,
   both = ΔY_runtime≫5)** — no empirical 1450 fudge needed. Recipe: `probe_collision_sector` → sector S;
   `sculpt_terrain --payload-off <tile> --delta -D`; `edit_collision_sector --sector S --src-delta-y -D`;
   `build_autolayout_disc` both. Residual: the probe is a LIVE step (no offline world-XZ→sector map yet), and
   the bump is per-sector-flat (slopes/walls still §1a.2).
4. **Per-region source** ✅ DONE (`floor_source_map.py`, step 9 — `sculpt_terrain.py --at-runtime-xz` auto-picks
   the right payload). `M_obj` rotation is a non-issue for floor (translation-only verified); may remain for decor (§11.4).

## 2. Ground geometry — COLLISION
**Data:** **LEVEL.RAW chunk 32** → converter [[FUNC_80030F60]] builds the sector table `0x800A7E48`
(223 sectors × 0x30) `<<5` from a source record array (decompressed global offset `0xcd248`, stride `0x4c`;
origin X/Y/Z at +0x08/+0x0c/+0x10). Resolver [[FUNC_800345CC]] → committed by [[FUNC_8003633C]] to player-Y
`0x800a6504`. Full chain CONFIRMED ([[G29 - Collision source]]).
**Status: ✅ PERMANENT disc edit PROVEN (2026-06-24, step 6).** On-disk lever = chunk-32 src record `+0xc`
(`<<5`, more-negative = up). Tool **`tools/edit_collision_sector.py`** (decompress chunk 32 → edit sector
origin-Y → recompress → splice) + auto-layout rebuild. **In-game: raising all chunk-32 sectors by runtime
−8000 raised Flik's footing by exactly −8000** (Y −8565 → −16565 on an identical walk vs pristine) — the
permanent disc edit moves Flik 1:1, and the ballooned LEVEL.RAW (+58 KB) **boots** (closes the §2.3 rebuild
residual). RAM-verified: the converter [[FUNC_80030F60]] rebuilds `0x800A7E48` from the patched chunk.

**Remaining gaps**
1. ~~Location-dependent sector pick~~ **✅ SOLVED (2026-06-24)** via `tools/probe_collision_sector.py`: a LIVE
   **binary-search** poke-probe over all 189 chunk-32 sectors (poke a group's runtime origin-Y → nudge Flik →
   the group that moves him contains his floor) reliably finds the resolver's selected sector (spawn = **sec99**,
   −6000 poke → Flik −5952 ~1:1). Offline XZ-proximity was unreliable (sector origins are reference points, not
   centers). Residual: this is a *live* probe — no offline world-XZ→sector map yet.
2. ~~Sector origin moves the WHOLE sector; editing individual planes is not done~~ **✅ DONE 2026-06-24 (§2.2).**
   The walls/slopes are **oriented PLANE records** (0x20 B in chunk 32: s16 normal @+0/2/4 with |n|=0x4000, s16
   ref @+6/8/a), resolved by the **swept** collision fn [[FUNC_800345CC]] (`dist=(normal·(p−ref<<5))>>14`,
   segment-crossing → clamp; committed by [[FUNC_8003633C]]). LEVEL01 has **6** planes (count `[gp+0x57c]`) on
   sectors 119 & 166, all in chunk 32. Located via runtime tables `0x8009c230`(ptr)/`0x80091718`(sector) →
   live tool **`tools/probe_collision_planes.py`**; edited offline by chunk-32 offset (tilt normal / move ref /
   disable) with **`tools/edit_collision_plane.py`** (recompress+splice, round-trip verified). **LIVE-VERIFIED
   in-game:** an A/B walk from `level01_end_of_stage.sav` with the planes disabled (zeroed normals) vs on made
   Flik's path diverge at the crossing (dY 1461, max |Δpath| 2128) — the planes are real editable collision.
   RE: `src_re/collision_plane_resolver_800345cc.c`; regression `tools/regress_collision_plane.py`.
3. **The 223-sector array spans chunk 32 → chunk 33** (only 189 sectors are in chunk 32; the tool edits those;
   sectors 189–222 need chunk-33 handling — minor extension).
4. ~~Permanent edit / recompress balloon~~ **✅ RESOLVED** — the ballooned chunk-32 LEVEL.RAW rebuilds and
   boots via the auto-layout manifest (by-name loading tolerates the LBA shift); no size-neutral patch needed.

**To close:** ~~(1) execTrace FUNC_800345CC; (2) plane-level edit recipe; (3) boot-test ballooned rebuild~~
**✅ ALL DONE (2026-06-24).** (1) resolver decoded + planes live-probed; (2) recipe + tools
`probe_collision_planes.py`/`edit_collision_plane.py`; (3) ballooned chunk-32 rebuild proven (§2/§6/§10).
**Only minor residual:** gap 3 — the SECTOR origin/region tools are chunk-32-only, so sectors **189–222 (in
chunk 33)** aren't editable yet (all 6 *planes* and the exit/spawn sectors are in chunk 32, so this is
peripheral). **Tools:** `tools/probe_collision_planes.py`, `tools/edit_collision_plane.py`,
`tools/edit_collision_sector.py`, `tools/decode_level_raw.py`, `tools/recompress_level_raw.py`.

## 3. Enemies
**Data + behaviour:** [[Enemy AI state machine]] + [[Enemy relocation method]]. Relocation is **type-dependent**.
- **Stationary (worm, pill beetle):** relocatable by editing the **anchor** record (worm `0x800a0c9c`
  rec@`0x80094d64`; pill-beetle `0x800a0144`); on disc the placement is in a compressed level placement
  file (RAW chunk-31-class). **Status: 🟡 PARTIAL** — live-proven; disc-edit needs decompress + edit X/Z + rebuild.
- **Patrol / mover-VM** (`FUNC_8004C13C` op9): path waypoints = **LEVEL.DAT top-level rec1 @ `0x468`
  (type 1, 104 × `(X,Y,Z)` stride 0xc, file<<5)**; programs RESIDENT (table `0x80077af8`).
  **Status: ✅ PROVEN disc-edit (2026-06-24, step 7).** Tool **`tools/edit_dat_coord_record.py`**
  (`--record 0x468 --move/--set-entry`, size-preserving, uncompressed). **In-game: translating rec1 by
  +6000 X relocated a visible mover object (the flying bug at spawn vanished from its spot, 10.73% frame
  change) + RAM-verified the waypoints loaded** — disc-confirms the live-proven [[event-interpreter-mover-vm]].
- **Chasers (bee/mosquito/spider):** post-aggro position is **Flik-relative AI** (`FUNC_8004DF18`
  @ `0x80095358`) → no editable chase location. BUT they spawn from **data-driven AREA records** at
  `0x94c/0xa10/0xad4` (top-level types 11/12/13; **header + 16 `(X,Y,Z)` waypoints**, spawn pos derived from
  WP0/WP1; the prior "two points" = that deriving pair). Spawn fn `0x8004d698` reads them via ptr table
  `0x80096dc8` ([[enemy-chaser-spawn-areas]], traced + a move built/verified `ABL_CHASER_MOVE`).
  **Status: ✅ PROVEN editable** — `tools/edit_dat_coord_record.py --record 0x94c/0xa10/0xad4`; RAM-verified
  the edited records load. (Spawn is state-machine-gated, so it's not read per-frame — moving a zone onto
  Flik's idle spawn did NOT force an immediate spawn in my window; that's expected, not a refutation.)
- **Stationary (worm, pill beetle):** anchor record in a **compressed** RAW chunk-31-class file. **Status:
  🟡 PARTIAL** — live-proven relocatable; disc-edit needs decompress + edit X/Z + recompress (the chunk
  codec + `build_autolayout_disc.py` exist; per-enemy discs were built ad-hoc in
  [[enemy-worm-is-popup-relocatable]] but not via a clean reusable tool yet).

**Remaining gaps**
1. **Stationary-anchor disc-edit via a clean tool** (compressed chunk) — the mover-VM + chaser-area records
   (uncompressed DAT) now have `edit_dat_coord_record.py`; the compressed anchors still rely on ad-hoc edits.
2. **Per-enemy runtime identification** (which of zones 11/12/13 = bee vs mosquito vs spider) is still manual;
   no static roster map.

**To close:** wire + test the stationary-anchor compressed-chunk edit through a reusable tool. **Tools:**
`tools/edit_dat_coord_record.py` (mover waypoints + chaser areas), `tools/rebuild_with_patched_dat.py`,
`tools/decode_level_raw.py`/`recompress_level_raw.py` (compressed anchors).

## 4. Berries (add / remove, incl. net-new blackberry) — operator req. #3
**Data:** LEVEL.DAT type-0x3f entries **54–57** (X/Y/Z @ +0/+4/+8, kind @ +0xc).
- **Move existing:** ✅ PROVEN — moves collected correctly on a rebuilt disc.
- **Add (more berries):** ✅ PROVEN — relocation-aware append (`insert_type3f_entries.py` / `append_new`).
- **Remove (fewer berries):** ✅ PROVEN (2026-06-23, CC5) — `tools/delete_type3f_entries.py` (relocation-aware
  record delete) + the editor's "Delete Selected from Level"; same engine in-game-verified on grains (70→60).
- **Net-new blackberry** (a berry kind absent from retail): ✅ DONE (2026-06-24, CC6, in-game verified). The
  editor's add-item dropdown now offers **"Blackberry (net-new berry)"** (from the registry
  `mod/custom_objects/blackberry.json`); queuing it appends a type-0x3f **kind 0x25** placement (marked
  `allow_unknown` per-op) and, because the registry flags it `requires_code`, the editor's "Build Modded Disc"
  builds **WITH code** (drops `--no-code` → `mod/patch.asm` caves get applied). One disc bundles
  placement + EXE caves + render descriptor. **In-game:** the composed disc booted LEVEL01 (count 70→71,
  entry 70 = kind 0x25), Flik **picked it up → equip index 0x05** (arm cave), and **throwing spawned
  projectiles** in the contact-object array (throw cave). See [[Berry projectile and homing]] /
  [[berry-equip-throw-arm-chain]] for the behaviour RE.

**Remaining gaps:** none for the blackberry — relocation + move + add + delete (CC5) + net-new composition
(CC6) are all done. **Tools:** `tools/move_type3f_entry.py`, `insert_type3f_entries.py`,
`delete_type3f_entries.py`, `apply_level_placements.py`, `mod/patch.asm` (blackberry caves).

## 5. Seed tokens (collectible)
**Data:** LEVEL.DAT type-0x3f entries **58–66** (kinds 0x29/0x2a/0x2b). **Status: ✅ PROVEN** for move +
relocation-aware append + **kind-swap (2026-06-24, in-game)**: a `set_entry` swap of entry 63 (0x29→0x2b)
booted LEVEL01 and RAM read entry 63 = **kind 0x2b** (only 63 changed; 62/64 unchanged), count 70, level
stable — clears the "assumed safe" caveat. Also delete (CC5) applies to tokens. (Note: the *plantable* seeds
are a SEPARATE system — [[Seed planting system]], LEVEL.RAW chunk 31 — already solved for live-move + disc-edit.)

## 6. Grains (net-new — raise/lower the count) — operator req. #1
**Data:** LEVEL.DAT type-0x3f entries **0–49** (kind 0x14).
- **Move:** ✅ PROVEN — placement moves collect correctly.
- **Add (count up):** ✅ PROVEN — relocation-aware append of new kind-0x14 entries. Crucially the
  **HUD "collected/total" + all-grain emblem are already DYNAMIC** (commit `6c9445c`,
  [[Grain emblem and HUD total mod]]) — they count the level's live kind-0x14 total, so adding grains
  **auto-updates** the target and the emblem trigger. No hardcoded "30/50" to chase.
- **Remove (count down):** ✅ PROVEN (2026-06-23, CC5) — `delete_type3f_entries.py` / editor "Delete Selected".
  **In-game verified:** a disc deleting grains 40–49 (count 70→60) booted to LEVEL01 and the parser loaded
  **40 live kind-0x14 records**; the dynamic emblem/HUD track the lower total automatically. This supersedes
  the grain30 `set_entry`→inert workaround (only needed while delete didn't exist).

**Remaining gap:** none for grains — add + move + delete + dynamic counter are all done.
**Tools:** `tools/list_level_grains.py`, `catalog_level_grains.py`, `patch_level_grain.py`,
`insert_type3f_entries.py`, `delete_type3f_entries.py`, `apply_level_placements.py`.

## 7. FLIK letters + "type a new word" — operator req. #2
**Data (placement):** LEVEL.DAT type-0x3f entries **50–53** (kinds 0x10–0x13 = F/L/I/K). Relocation
**✅ PROVEN** (clustered, booted, all 4 collected).
**Data (the word / glyph art):** the letters are **glyph sprite-tiles** (0x10–0x13), 24×23 4-bit golden
sprites that spin 360°. The word = a **texture edit**, not text ([[HUD letter glyphs and word swap]] /
[[flik-letters-are-glyphs]]). Pipeline is **shipped + verified in-game (FLIK→ATTA, spin intact)**:
`mod/glyphs/flik_word.h` (`#define FLIK_WORD "ATTA"`) → `tools/glyph_assets.py` (image→glyph + spin synth) →
`tools/patch_flik_word.py` (writes both LEVEL.RAW + LEVEL1.RAW). The same glyph tiles drive both the SELECT
HUD panel **and** the in-world spinning letters, so one edit updates both.
**Status: ✅ DONE (2026-06-24, in-game verified).** The **"type a word" GUI feature** is wired and tested:
1. **GUI wiring — DONE.** The editor has a **"HUD Word (FLIK)"** field + **"Build HUD-Word Disc"** button
   (`pyside_level_editor._build_word_disc`). It validates the word and runs **`tools/build_flik_word_disc.py`**,
   which patches LEVEL.RAW + LEVEL1.RAW glyphs (`patch_flik_word.py`) and rebuilds the disc. Because the
   recompressed RAW **balloons** (+13 KB each, B14/CC2), this build uses the **size-tolerant auto-layout**
   manifest `REBUILD/abl_autolayout.xml` (not the fixed-LBA `abl.xml`); it self-verifies the patched LEVEL.RAW
   is embedded at its recomputed LBA. **In-game verified:** a "TAKA" disc booted LEVEL01 and the SELECT-hold
   HUD panel rendered **T·A·K·A** in gold with the spin animation intact (panel = `draw_flik_bit_panel`, pulse
   `0x800b0194`; only fires in live gameplay, not the start-menu pause).
2. **Exactly 4 letters** — the HUD panel has **4 fixed slots** (tiles 0x10–0x13); the GUI enforces a 4-letter
   word. Variable-length words remain OPEN (would need HUD draw-code changes).
3. **Letter art set** — the GUI restricts input to letters that have native gold art
   (`glyph_assets.available_letters()` = currently **A F I K L T**). Other A–Z would fall back to an unverified
   font glyph, so they're rejected until a `mod/glyphs/letters/<L>.png` is supplied (then auto-available).

**Remaining gaps:** none for the constrained feature — the variable-length and full-A–Z-art items are
explicit out-of-scope follow-ons. **Tools:** `tools/build_flik_word_disc.py`, `tools/patch_flik_word.py`,
`tools/glyph_assets.py`, regression `tools/regress_flik_word.py`.

## 8. Telescopes (green gems / hint device)
**Data:** LEVEL.DAT type-0x3f entries **67–69**, kind **0x30** (= the telescope/hint device; NOT a
checkpoint — [[green-gem-investigation]]). **Status: ✅ PROVEN (2026-06-24, in-game).** Relocation boot-tested:
a disc moving entry 67 by dx +4000 (`move` op + `allow_checkpoint`) booted LEVEL01 and RAM read the telescope
loaded at the **moved X = 3372** (= −628 + 4000), kind 0x30 intact, count 70, level stable. The
`RISK_CHECKPOINT` flag is **conservative-only** (relocation is load-safe); keep it as a confirm-prompt, not a
hard block. NOTE: the loader recomputes pickup **Y** from terrain height (the −50 file Y is a placeholder) —
**X/Z are the editable placement**, Y is not. The hint-reveal *behaviour* is shell-side and not
placement-editable (out of scope for relocation).

## 9. Player spawn point
**Data:** initial spawn = [[FUNC_80046B20]]`(player, scene_id)`, coords from the **resident EXE table
`0x80077314 + scene_id*12`** (`SCUS_942.88` file offset `0x67b14`; word0→X, word1→Z, word2→heading, Y
computed). NOT LEVEL.DAT (refuted by write-watch — [[gap0035-initial-spawn]]). **Status: ✅ PROVEN** — warp
landings to scenes 3/6/2/4 live-confirmed; edit = patch EXE table + rebuild.
**Remaining gap:** the **checkpoint respawn anchor** (`0x800a6550/54/58`, updated by `FUNC_80054c90`) is
**runtime-computed** from proximity to seed/checkpoint records — not directly disc-editable. Affects
*respawn-after-death*, not the level-entry spawn.

## 10. End-of-level point / level exit  ✅ **SOLVED (2026-06-24, step 12)**
**What's decoded:** the transition *logic* end-to-end — type-2 initiator [[FUNC_8004A700]] / type-6 initiator
`FUNC_8004ABF4` set the transition lever `[0x800823a0]`; the shell SM resolves the destination from scene
table `0x80077fa0` indexed by `[0x8008245c]` ([[Gameplay - Warp and Level Transition]]). In-game level→level
*handoff* is **terminal-by-design** (the destination index is shell-only-writable) — [[Gap Audit|GAP-0035]] 0035B.

**✅ The exit TRIGGER POSITION is FOUND (live-confirmed via the operator save `level01_end_of_stage.sav`).**
The level exit is a **per-sector REGION CODE in the COLLISION sector table** — *not* a pickup/telescope/DAT
record. RE C: `src_re/level_exit_trigger.c`.
- **Where Flik must stand:** **collision sector 177** — the *only* LEVEL01 sector tagged with region-code **2**
  (origin runtime `(-163008,-169888,-124832)`). Walk into it → exit.
- **Mechanism:** `FUNC_80048138` (scene/exit handler) calls **`FUNC_80038f38(0, &Flik[+0x82])`**, which returns
  `SECTOR_TABLE[Flik.current_sector] + 0x2e` (the region code) **iff the gate byte `[Flik+0x82]==1`**; current
  sector = `[0x80090560]`, table `0x800a7e48` stride `0x30`. `FUNC_80048138` switches on the code: **code 2 →
  `[0x800823a0]=1`** (type-1 exit) + fade `[0x80082470]=23` + level-complete SFX `FUNC_80050994(58)`. (Codes
  1/3/4 = other transition kinds used by other levels.)
- **Disc source (offline-located, byte-confirmed):** the region code is **static, baked in LEVEL.RAW chunk 32**.
  Sector source records: chunk-32 decompressed local `0x36570` (global `0xCD248`), stride `0x4c`; origin XYZ
  @ `+0x08/+0x0c/+0x10` (= runtime `>>5`); **REGION CODE @ `+0x2c` (word) → runtime `+0x2e`**. Sector-177 record
  @ local `0x36570 + 177*0x4c` (global `0xD06D4`): origin `(-5094,-5309,-3901)` == runtime`>>5`, `+0x2c = 2`,
  **unique among the 189 real records**. ⇒ editable/relocatable with `tools/edit_collision_sector.py` (same
  chunk-32 records, proven in-game) + `tools/build_autolayout_disc.py`.
- **In-game proof (legitimate walk-in, NOT teleport):** held forward from the at-exit save → lever `0→1`
  (writer PC `0x800496dc`, the type-1 store in `FUNC_80048138`) in sector 177 → **level torn down**
  (`active[0x800822f8] 1→0`, `scene 1→0`), Flik did **not** respawn at spawn. The post-teardown stall at
  scene=0 is the known GAP-0035B limit (next-level *load* needs shell-phase destination/resource sequencing).

**Earlier wrong lead (retained as a method note):** `FUNC_8004ABF4` (type-6 proximity to moving actor
`[0x80090748]`) was pursued and **ruled out** — teleporting Flik onto it set `[0x800823a0]=2`, but that was a
**death-from-falling respawn** (Flik fell off non-floor geometry → respawn at spawn), not the exit. **Method
trap:** teleport-to-a-guessed-XZ is confounded by death-from-falling; "Flik reaches X ⇒ lever set" is not exit
evidence. The operator's at-exit *save state* is what sidestepped it. See `src_re/proximity_updater_8004abf4.c`.

**✅ Disc-edit RELOCATION proven in-game (2026-06-24).** Tool **`tools/edit_sector_region_code.py`**
(`--list`/`--set I:CODE`/`--clear I`, recompress chunk 32 + splice) moved the exit code-2 from sector 177 → 108,
rebuilt via `tools/build_autolayout_disc.py`. Cold-boot of the edited disc: runtime sector table now reads
`[108]+0x2e=2`, `[177]+0x2e=0` (game read the edit off disc); the **same forward-walk that is inert on pristine
(99→108, lever stays 0) ends the level on the edit** (lever→1 at sector 108, scene 1→0, active 1→0). So the
chunk-32 `+0x2c` region code **is** the disc-source exit trigger and is fully relocatable. §10 closed to the
"in-game proven on disc" bar. **Operator-confirmed (2026-06-24):** read Flik's live sector from the operator's
own DuckStation (read-only, debugger API port 2346) → set that sector's code 2 → disc `ABL_EXIT_AT_FLIK` →
operator booted it and the level ended right where Flik was standing (sector 154). Arbitrary live-probed exit
placement works in-game.

**✅ Wired into the level-editor GUI (2026-06-24).** New "Level-exit triggers" layer: `scene_importer.import_exits`
enumerates all 189 chunk-32 sectors + region codes; the **3D Scene** tab renders them as clickable markers
(current exit = red) under a "Show level-exit sectors" toggle; clicking a sector + "Set selected sector as exit"
→ "Build Exit Disc" runs `tools/edit_sector_region_code.py` (clear old + set new) + `tools/build_autolayout_disc.py`.
Tests: `test_scene_importer.test_level01_exits`, `test_scene3d.test_exit_markers_and_pick` (pass). Files:
`level_editor/scene_importer.py`, `scene3d.py`, `scene3d_view.py`, `pyside_level_editor.py`.

## 11. Scenery objects — mushrooms, fences, rocks, props (add / remove / move) — operator req. #5
**Data:** static decor/props are **model-space mesh payloads** ([[FUNC_80010000]]) placed by **LEVEL.DAT
pass-1 instance records** — table at file **`0x1504`, 484 records, stride `0x14`**: world position s32 X/Y/Z
@ +0/+4/+8 (Y-up placement frame), extent @ +0x0c, flags @ +0x0e (bit3 selects the payload bridge
`src+0x14` vs `src+0x1c`), source-record ptr @ +0x10 → payload. Each record = one instance; the mesh is
drawn at `record_pos + local_vertex`. The editor already **renders** this layer (203 meshes + **348 decor
instances**, [[Finding - DAT record holds decor instance world position]]).

**Status by operation:**
- **MOVE existing prop:** ✅ PROVEN (2026-06-24, step 5, in-game). Write tool **`tools/edit_pass1_records.py`**
  (`--list`/`--move I:DX:DY:DZ`/`--set I:X:Y:Z`) edits X/Y/Z at pass-1 `+0/+4/+8` in place — **size-preserving,
  no relocation** (coordinates aren't baked offsets). In-game: a disc that `--set` record 20 to
  `(11111,22222,33333)` booted LEVEL01 and RAM read pass-1 #20 = those exact coords, level stable. Build via
  `rebuild_with_patched_dat.py --target files/LEVEL01/LEVEL.DAT`. **Visual control confirmed (step 9):**
  translating ALL 484 pass-1 positions +60000 X changed **61% of the spawn frame** in-game (pure translation →
  also confirms translation-only placement). NOTE: an *individual* instance only moves the *visible* prop if
  that instance is in the camera frustum and at a sane (negative) decor Y — a couple of single-record tests at
  off-screen XZ / wrong Y showed 0% (the mechanism is fine; the picks weren't in view). ~~**Residual:** the
  **6 props placed only via the pass-3 table** (file `0x3afa`, 140 records) have an **undecoded position field**.~~
  **RESOLVED 2026-07-02** → [[Finding - Pass-3 decor records decoded (cull anchor + suppression)]]: the true
  pass-3 table base is **`0x3AEC`** (the `0x3afa` parse was +0xE misaligned — src reads were accidentally
  correct); records have the **same layout as pass-1** (`{s32 X,Y,Z; u16 extent; u16 flags; u32 src}`), BUT
  pass-3 XYZ is a **CULL ANCHOR only** — moving it does not move the drawn prop (0-px A/B); moving it far
  suppresses the prop (source-side delete lever, 12-byte in-place DAT edit). Per-frame culler
  `FUNC_80014360` + enable bitmap `0x800902C7`↓ (2nd suppression lever, live). Pass-3 props are therefore
  suppressible but not record-relocatable (draw position is payload-baked / backdrop-pass).
- **REMOVE prop:** ✅ PROVEN (2026-06-24, step 5, in-game). Same tool (`--delete-index I`, repeatable,
  high-index-first) removes a pass-1 record via the new general engine **`dat_reloc.build_reloc_delete_bytes`**
  (relocation-aware mid-structure delete: shifts the region after up 0x14, bumps every baked offset pointing
  past by −0x14, drops the record's own in-record pointer site). The mesh **payload is left in place**
  (orphaned, harmless — assets may be shared); this removes the *instance*, not the asset. In-game: deleting
  one record booted with **483 pass-1 records** (was 484), survivors' X/Y/Z byte-identical, level stable.
  Offline-proven at first/mid/last index + multi-delete (`tools/regress_pass1_records.py`).
- **ADD net-new prop:** 🟡 catalog DONE (2026-06-24, step 9); injection still OPEN. (a) **Object catalog ✅** —
  `tools/catalog_scenery.py` enumerates the decor table: **484 pass-1 instances → 152 distinct meshes**
  (21 multi-instanced; top mesh `0x2d460` ×93), each with vtx/local-bbox + a **geometric shape class**
  (flat / tall-upright / long-fence / blocky-rock). **Correction:** these decor meshes are **inline
  FUNC_80010000 payloads in LEVEL.DAT, NOT `.ALL`/`.ANM` files** — so semantic "mushroom/fence/rock" naming
  needs a visual pass per mesh (the catalog gives a stable payload id + geometric class to label). 2 records
  (flags 0x14 → payload `0x2f700`) don't decode (minor anomaly). (b) **net-new injection still OPEN** — adding
  an instance needs a new node entry (+ a payload copy if the mesh isn't present), with correct relocation
  (`build_reloc_insert_bytes`-style); each pass-1 record references a UNIQUE payload via its own node entry, so
  a true new instance is a multi-region insert — unbuilt. (§11 close item 5.)
- **ROTATE prop:** ✅ RESOLVED-as-finding (2026-06-24, step 9) — **there is no per-instance rotation matrix.**
  The pass-1 record (0x14 B) is fully accounted (pos+extent+flags+nodeptr) and its node/source record holds an
  **AABB** (two ±scalar triples), not a 3×3 transform. So decor placement is **translation-only**; a prop's
  orientation is baked into its payload vertices (to re-orient, edit the mesh). Closes GAP-0023's "rotated-mesh
  `M_obj`" for placement: it isn't parameterized.

**Mushrooms — note the ambiguity:** some "mushrooms" are **grown plants from the [[Seed planting system]]**
(LEVEL.RAW chunk 31 — a *separate*, partly-editable system), not static DAT decor. Decide per-object which
system a given mushroom belongs to before editing.

**To close (ranked):** (1) a pass-1 **move/delete** write tool with relocation (reuse `dat_reloc.py`);
(2) decode the **pass-3** position field (place the last 6 props); (3) build an **object catalog** (label
payloads as mushroom/fence/rock — likely via the `.ALL`/`.ANM` model names, [[Blocker - Character and plant model formats are unreversed|B7]]);
(4) decode `M_obj` (rotation); (5) prove **net-new decor injection** on a rebuilt disc.
**Refs:** `level_editor/scene_importer.py` (`survey_instances`/`survey_node_anchors`), `tools/analyze_g27_floor_candidates.py`,
`tools/dat_reloc.py`, [[Gap Audit|GAP-0023]], [[Asset - Chunk 34 Master Mesh]].

---

## 12. Visual fidelity — fly through LEVEL01 ~1:1 (the "looks like the game" axis)
The 3D Scene tab (`level_editor/scene3d.py` + `scene3d_view.py`, moderngl) already renders LEVEL01 as a
**navigable space** with the right *shape* (217 mesh payloads, ~32k tris, 348 decor instances, 70 pickups,
each source-traced). That's enough to **edit**; it is **not yet ~1:1** to look at. Gaps below are the
*rendering* axis, ranked by visual impact for "close to 1:1." Most are **implementable offline** from the
existing vault decode; a few need a DuckStation trace (**DS-req**). The editor stays the front end — none of
this changes the on-disc edit levers in §1–§11.

| Dimension | Editor TODAY | Gap to ~1:1 | Effort / gate |
|---|---|---|---|
| **Textures / CLUT** | shader **has** an atlas sampler + per-face UVs + a live-derived texture-page→chunk map, but **falls back to one dirt page for everything**; CLUT confirmed for the **floor only**; ripped pages exist locally (`level_editor/ripped_textures/`, local-only) | bind each mesh's real texture page + decode all scenery/wall CLUTs; clarify the vertex **`attr`** role | **Biggest visual win.** Partly offline; full CLUT + `attr` role = **DS-req** ([[Gap Audit|GAP-0027]], B7) |
| **Real object models** | pickups = colored **proxy cubes**; FLIK/enemies/plant-decor characters **not drawn** | import `.ALL` mesh + per-primitive vertex colours; map type/kind → asset | format **decoded** ([[Asset - Character and plant models]], B7); **no importer yet** — offline, high effort |
| **Sky / background** | dark-grey clear colour, **no sky** | game sky = flat **GP0 0x02 fill** (recolourable) → render a flat/gradient backdrop in the level's sky RGB | trivial; exact on-disk source has a known **discrepancy** (Phase-1 checklist; [[Finding - Sky is a GP0 background fill]]) |
| **Camera / projection** | generic **free-fly, 70° FOV** GL perspective | match the game's **512×224 GTE projection** (FOV/aspect) + optional "game-view" toggle using the decoded follow-law | follow-law **decoded** ([[Gap Audit|GAP-0028]]) but **not wired**; world-origin Y still empirical (`1450`, [[Gap Audit|GAP-0023]]) |
| **Geometry completeness** | floor/scenery/decor imported; **chunk-34/35 master mesh NOT imported** (model-space, needs runtime transform); some decor instances capped | import the master mesh + place all instances | DS-req model→world ([[Gap Audit|GAP-0023]]) |
| **Face winding** | faces mostly decoded from the cmd-stream; **~100 meshes fall back to FAN** (winding unconfirmed); no backface cull (hides the error) | byte-confirm winding so nothing renders inside-out | **DS-req** execTrace jump table `0x8001036C` + frame-diff |
| **Lighting / shading** | Lambert diffuse + ambient + per-vertex colour | confirm flat-vs-gouraud + the real vertex-colour/normal source (tied to `attr`) | **DS-req** (`attr` role) |
| **Animation** | **static** — spinning FLIK glyphs, plants, water, enemies all frozen | `.ANM` 24-bone skeletal playback + skinning | format **decoded**; skinning + animator **missing** — long tail, OK to defer for "close to 1:1" |
| **Coordinate frame / scale** | placement frame (Y-up) correct, payload frame handled, per-mesh node anchors used | confirm world-origin Y (drop empirical `1450`) + rotated-mesh `M_obj` | [[Gap Audit|GAP-0023]] residual |
| **LEVEL01-only** | pickups load on all 9 levels; **meshes render LEVEL01-only** | per-level mesh profiles | static RE incomplete (209/218 recovered) or **DS-req** capture |

**Fidelity track — ranked for "close to 1:1" (cheap/high-impact first):**
1. **Sky clear-colour / backdrop** — trivial; instantly reads as "outdoors."
2. **Real textures** — bind per-mesh texture page + CLUTs (ripped pages already exist locally). The single
   biggest jump from "mock-up" to "the game."
3. **Camera FOV/aspect match** (512×224) + optional **follow-law "game view"** toggle.
4. **World-origin Y confirm** (drop the empirical `1450`) so meshes sit at the exact height.
5. **Real object models** (`.ALL`/`.ANM` importer + type→asset map) — recognizable pickups/characters.
6. **Face-winding + shading confirm** (DS-req) — removes inside-out faces / wrong smoothing.
7. **Animation** (`.ANM` playback) and **per-level profiles** — the long tail; defer for a *first* ~1:1 LEVEL01.

> **Shortcut worth noting:** `gp0Trace` can capture the game's **actual** per-frame GP0 command stream
> (exact primitives + texpages + colours) from a live frame ([[Core - Rendering OT and GPU Packets]]). That's
> a ground-truth oracle to validate the editor's geometry/texture/winding against — and a fallback "show me
> the real frame" reference if offline reconstruction stalls.

---

## Cross-cutting blockers (affect several elements)
- **CC1 — Editor write/build path. ✅ DONE (2026-06-23, verified end-to-end).** The PySide editor's
  **"Build Modded Disc"** action (File menu + toolbar, `pyside_level_editor._build_disc`) now exports the
  current edit plan and runs **`mod/build.py --no-code --placements <plan> --placements-target
  files/<LEVELxx>/LEVEL.DAT --force`** asynchronously (`QProcess`): it applies the plan via
  `tools/apply_level_placements.py`, stages the patched DAT into `REBUILD/files`, runs **mkpsxiso**, restores
  the staged source to pristine, and **verifies the patched DAT is embedded at its LBA**. Output =
  `build/ABL_modded.bin/.cue`; the pristine disc is never touched. **All proven type-0x3f elements are now
  one-click** (grains/berries/tokens/telescope move + add). Verified: a size-preserving grain move built a
  738 MB disc, embed-verify passed (LBA 2906), staged source restored. Guarded by regression test
  **`tools/regress_editor_build_path.py`** (editor YAML/target contract + `build.py --no-disc` apply, no ISO).
  **Residuals (own items, NOT CC1):** the GUI build is **data-only** (`--no-code`), so it does *not* yet wire
  (a) **EXE/code-cave** edits like the player-spawn table (§9) — those need CLI `mod/build.py` without
  `--no-code`; (b) **LEVEL.RAW** edits — the **FLIK-word** glyph swap (§7, `patch_flik_word.py`), collision
  (§2), seeds — which need recompress (CC2); (c) **auto-boot DuckStation** (the dialog points the operator to
  boot the disc). Those are tracked in §7/§9 and CC2/CC3, not here.
- **CC2 — LEVEL.RAW recompressor balloons (~1.4×). ✅ RESOLVED for modding (2026-06-24, step 10).** Decode is
  byte-exact across all 69 chunks; the encoder is literal-only (round-trips, balloons). Two prior "open" items
  settled: (1) **provenance tracker FIXED** — `decode_level_raw`'s `prov` now aligns 1:1 with the output
  (236944/236944 on chunk 32; main-path literals were missing); (2) **size-neutral minimal-patch is NOT a safe
  capability** — a literal byte can be an LZ **match source**, so patching one compressed byte propagates
  (>1 decoded byte changes), AND structured data (e.g. collision sector origin-Y) is largely match-output
  (not literal-backed) anyway. ⇒ **robust compressed-chunk edits MUST recompress**, and the balloon is handled
  by the **auto-layout rebuild** (`tools/build_autolayout_disc.py`, by-name LBA-tolerant). A true
  PROPACK-equivalent match-emitting encoder (to eliminate the balloon, enable `cd.overlay` live) remains a
  **deferred optimization** — non-blocking, since auto-layout works. Regression `tools/regress_level_raw_codec.py`.
- **CC3 — LBA-shift rebuild that grows LEVEL.RAW. ✅ CONFIRMED (2026-06-24).** A chunk-32 recompress (LEVEL.RAW
  +58 KB) → auto-layout rebuild → **boots LEVEL01 and the game reads the edit** (runtime collision sector table
  `0x800A7E48` reflects the patched origin-Y; also step-6 collision moved Flik 1:1, step-3 FLIK glyphs rendered).
  By-name file loading tolerates the LBA shift ([[Finding - File loading is by-name (LBA-shift tolerant)]]).
- **CC4 — type-0x3f Y comfort-band.** Final runtime Y more negative than ~−21000 risks unreliable
  collection / auto-grab; clamp placed Y ([[ABL Level Editor]] RE facts).
- <a id="CC5"></a>**CC5 — type-0x3f DELETE/REMOVE operation. ✅ DONE (2026-06-23, in-game verified).**
  Implemented the inverse of the append engine: `dat_reloc.build_reloc_delete` removes a 0x10-byte entry,
  **decrements the count**, and bumps every baked file-offset that points past the removed bytes by −0x10
  (1248/1248 sites on LEVEL01). User-facing wrapper **`tools/delete_type3f_entries.py`** (dry-run default,
  `--delete-index` repeatable, applied **high-index-first**, risk-gated: FLIK letters `--allow-flik-letter`,
  telescope `--allow-checkpoint`, token-like/unknown flags). Spec-runner **`delete` op** added to
  `tools/apply_level_placements.py`, and the editor exposes **"Delete Selected from Level"** (queues
  `Operation.delete`; `_build_yaml` emits non-deletes first then deletes descending so stored indices stay
  valid). **Proofs:** byte-exact round-trip `delete(append(X)) == X`; deleting any index 0..69 re-parses;
  regression `tools/regress_type3f_delete.py`. **In-game (acceptance):** a data-only disc deleting grains
  40–49 (count 70→60) booted via the LEVEL01 movie and the parser loaded it cleanly — RAM type-0x3f record at
  `0x801607fc` read **count 60, type 0x3f, 40× kind-0x14** (other kinds intact), Flik in-world, gameplay
  rendered. Since the dynamic HUD/emblem count kind-0x14 live (commit `6c9445c`), the lower total auto-tracks
  — this **supersedes** the old grain30 `set_entry`→inert-kind workaround (which only existed because delete
  didn't). **Residual (own item, not CC5):** pass-1 *decor* record delete (§11) still needs its own tool.
- <a id="CC6"></a>**CC6 — Net-new object KINDS bundled (placement + code + descriptor). ✅ DONE (2026-06-24,
  in-game verified).** Net-new = a pickup KIND absent from retail (the **blackberry**, kind 0x25; future
  custom pickups) — **NOT** new grains/tokens (existing kinds, plain append) or enemies (separate system §3).
  Closed with a **custom-object registry** `mod/custom_objects/*.json` (loader `tools/custom_objects.py`):
  each entry declares `kind`, `label`, `requires_code`, `placement_op`, default position. The editor loads it
  into the add-item dropdown ("Blackberry (net-new berry)"); queuing one appends a type-0x3f kind-0x25 row
  (marked `allow_unknown` **per-op**, so the risk gate still blocks *un*registered unknown kinds) and, because
  it's `requires_code`, the editor's "Build Modded Disc" **drops `--no-code`** so `mod/build.py` applies
  `mod/patch.asm` (equip/throw/arm/speed/power/recolour caves + the private kind-0x25 render descriptor at 0x80081234)
  — one disc bundles placement + EXE caves + descriptor. **In-game (composed editor build):** booted LEVEL01
  (count 70→71, entry 70 = kind 0x25), pickup → **equip index 0x05** (arm cave), throw → projectiles spawned.
  Behaviour RE: [[berry-equip-throw-arm-chain]], [[pickup-render-kind-descriptor-table]]. Regression
  `tools/regress_custom_objects.py`. Free kinds remain limited (low kinds 0x15–0x20/0x25–0x28/0x2e/0x2f
  repurposable; throw jump-table NOT extendable) — to add another custom pickup, drop a registry JSON + its
  caves in `mod/patch.asm`.

## Recommended order (cheap → hard)
1. ~~**CC1** — wire the editor's build/apply path~~ **✅ DONE 2026-06-23** (verified end-to-end + regression
   test). The proven **type-0x3f** elements (grains/berries/tokens/telescope move+add) are now one-click via
   the editor's "Build Modded Disc" button. FLIK-word (RAW) and player-spawn (EXE) one-click are *follow-on*
   under §7/§9 (the data-only `--no-code` GUI build doesn't touch RAW/EXE yet). **→ CC5 also done; next: step 3.**
2. ~~**CC5 — record delete**~~ **✅ DONE 2026-06-23** (in-game verified: grains 70→60 booted, parser read 40
   live grain records). type-0x3f deletion now lowers grain/berry/token counts via `delete_type3f_entries.py`
   + the editor's "Delete Selected from Level". *Decor* (pass-1) deletion remains under §11. **→ next: step 3.**
3. ~~**FLIK "type a word" GUI (§7)** + **Telescope test (§8)** + **token kind-swap test (§5)**~~ **✅ DONE
   2026-06-24** (all three in-game verified): editor "Build HUD-Word Disc" rendered "TAKA" w/ spin; telescope
   move (entry 67 → X 3372) load-safe; token kind-swap (entry 63 0x29→0x2b) load-safe. Letters limited to
   shipped art (A F I K L T). **→ next: CC6 (net-new-kind composition).**
4. ~~**CC6 — net-new-kind composition**~~ **✅ DONE 2026-06-24** (in-game verified): editor dropdown
   "Blackberry (net-new berry)" → composed code+data build → booted, picked up (equip 0x05), thrown. Registry
   `mod/custom_objects/*.json` + `tools/custom_objects.py`. New grains/tokens (existing kinds) and enemies
   (§3) are NOT CC6. **→ next: §11 scenery move/delete tool.**
5. ~~**Scenery move/delete tool (§11.1–2)**~~ **✅ DONE 2026-06-24** (in-game verified): `tools/edit_pass1_records.py`
   (move/set/delete pass-1 prop records, relocation-aware) + `dat_reloc.build_reloc_delete_bytes`; set #20
   coords loaded & delete → 483 records on a booted disc. Residual: pass-3 (6 props) position field, ROTATE
   (`M_obj`), ADD-net-new decor, and editor GUI selection of scenery (§11.3–5). **→ next: ground height-sculpt (§1a).**
6. ~~**Ground height-sculpt (§1a)**~~ **✅ DONE 2026-06-24 — including the localized matched bump.**
   `sculpt_terrain.py` (height brush → 36% visible deform) + `edit_collision_sector.py` (disc collision →
   Flik footing 1:1) + `probe_collision_sector.py` (binary-search finds the selected sector, e.g. sec99) +
   `build_autolayout_disc.py`. **LOCALIZED matched bump VERIFIED in-game:** terrain + sec99 raised together →
   **Flik rode up ~15869 ≈ the 16000 target** onto the raised visible floor. Calibration solved:
   terrain-local-ΔY = collision-src-ΔY (1:1, both = ΔY_runtime≫5; node-frame == runtime÷32 == src-frame — no
   empirical 1450). Residual = mouse-drag GUI brush, walls (new geometry §1a.2), offline world-XZ→sector map.
   **→ next: step 7 (enemy spawn-area / anchor disc-edit tool, §3).**
7. ~~**Enemy spawn-area / anchor disc-edit tool (§3)**~~ **✅ DONE 2026-06-24 (uncompressed records).**
   `tools/edit_dat_coord_record.py` wires the reusable disc-edit for the uncompressed LEVEL.DAT coord records:
   **mover-VM patrol waypoints (rec1 @ 0x468) — in-game CONFIRMED** (translating relocated a visible mover
   object, 10.73% frame change) and the **chaser spawn-area records (0x94c/0xa10/0xad4, types 11/12/13)** —
   editable + load-verified (spawn fn 0x8004d698 reads them, per traced [[enemy-chaser-spawn-areas]]).
   Residual: the **stationary-enemy anchor** is in a *compressed* chunk — still ad-hoc, no clean tool yet.
   **→ next: step 8 (collision reliability §2.1 — already done via `probe_collision_sector.py`; or step 9
   general placement / scenery catalog).**
8. ~~**Collision reliability (§2.1) + plane-level edits (§2.2)**~~ **✅ DONE 2026-06-24.** §2.1 via
   `probe_collision_sector.py` (earlier). §2.2: decoded the swept plane resolver [[FUNC_800345CC]] + the
   oriented-plane records (normal/ref, 6 in LEVEL01 on sectors 119/166); tools `probe_collision_planes.py`
   (live list) + `edit_collision_plane.py` (offline tilt/move/disable, round-trip verified) +
   `regress_collision_plane.py`. **Live-verified** (A/B walk: disabling planes diverged Flik's path). RE
   `src_re/collision_plane_resolver_800345cc.c`. Minor residual: chunk-33 sectors 189–222 (peripheral).
9. ~~**Ground per-region source map + `M_obj` (§1); scenery object catalog + `M_obj` rotation (§11.3–4)**~~
   **✅ DONE 2026-06-24.** Floor: `tools/floor_source_map.py` (world XZ → floor payload, 30 payloads) +
   `sculpt_terrain.py --at-runtime-xz` (spot-driven, 33.69% deform). Scenery: `tools/catalog_scenery.py`
   (484 instances → 152 meshes, geometric classes; decor meshes are inline payloads, not `.ALL`/`.ANM`).
   **`M_obj` rotation = RESOLVED-as-finding: no per-instance rotation matrix anywhere** (floor & decor are
   translation-only; node record = AABB, not a transform). Confirmed pass-1 controls visible decor (61% when
   all translated). **Remaining (own items):** semantic prop naming (visual pass), net-new decor INJECTION
   (§11 item 5), pass-3 position field (6 props), walls/GUI brush. **→ next: step 10 (CC2/CC3 permanent
   compressed-chunk rebuild) or step 12 (end-of-level trigger §10).**
10. ~~**CC2/CC3** — permanent compressed-chunk rebuild confirm~~ **✅ DONE 2026-06-24.** CC3 confirmed
    (ballooned chunk-32 LEVEL.RAW → auto-layout rebuild → boots LEVEL01, game reads the edit). CC2 resolved
    for modding: provenance tracker fixed; size-neutral patch shown unsafe (literals are LZ match sources) →
    recompress is required, balloon handled by auto-layout. Match-emitting encoder = deferred optimization.
    Codec regression `tools/regress_level_raw_codec.py`. **→ next: step 11 (walls/new-geometry + net-new decor
    injection) or step 12 (end-of-level trigger §10).**
11. **Walls / new geometry (§1a.2) + net-new decor injection (§11.5).** *Walls investigated (2026-06-24,
    [[G56 - Wall chunk-35]]):* walls = **chunk-35 master mesh** ([[FUNC_800172DC]], GP0(3c)), distinct from the
    DAT-floor ground; **live-editable** (buffer `0x8012c1d0` poke reshapes the wall 43%), transform recovered
    (scale 1.0, −Y up). **Permanent wall edit BLOCKED** on the master-mesh vertex/command-stream decode (a
    blanket on-disc edit crashes the load; one aligned vertex is fine). *Still OPEN:* the master-mesh decode,
    new vertical FACES, and **net-new decor injection** (new node entry + pass-1 record / payload, multi-region
    relocation). **→ next: continue the master-mesh decode, or step 12 (end-of-level trigger §10).**
12. **End-of-level trigger position (§10)** — ✅ **SOLVED 2026-06-24** via the operator save
    `level01_end_of_stage.sav`. The exit = a **collision-sector region code**: sector 177 (the only LEVEL01
    sector tagged code 2 at `SECTOR_TABLE+0x2e`); `FUNC_80038f38`→`FUNC_80048138` fires the type-1 exit
    (`[0x800823a0]=1`) when Flik enters it. Disc source = LEVEL.RAW chunk-32 record 177 `+0x2c=2` (global
    0xD06D4). Live-confirmed (walk-in → level teardown, no respawn). See §10 + `src_re/level_exit_trigger.c`.

**In parallel — the visual-fidelity track (§12)** runs independently of the edit ladder above (it changes how
the editor *looks*, not what it writes). **→ Now a dedicated guideline + plan: [[LEVEL01 Editor Visual-Fidelity Plan]]**
(goal: the 3D Scene must read **1:1 with in-game LEVEL01**). Execution order there: **shader fixes (delete the
fake light, nearest sampling — cheap) → per-FACE textures (the #1 win) → transparency → cull garbage → camera
→ real models**; sky deprioritised. (Flight-checked 2026-06-24: the dirt-soup is per-mesh-single-page
collapsing 124/191 meshes to dirt, NOT undecoded textures.) The edit ladder being done + in-game proven, this
is the active forward track for the editor.

## Related
[[ABL Level Editor]] · [[ABL 3D Level Editor Roadmap]] · [[ABL 3D Phase 1 Gap Checklist]] ·
[[Geometry pipeline]] · [[G29 - Collision source]] · [[G30 - Terrain render source]] ·
[[Plan - Terrain+collision matched bump (Option B)]] · [[Enemy AI state machine]] · [[Enemy relocation method]] ·
[[Seed planting system]] · [[Gameplay - Warp and Level Transition]] · [[Gap Audit]] · [[Blockers]] ·
[[Indexes/Gap Priorities|Gap Priorities]]
