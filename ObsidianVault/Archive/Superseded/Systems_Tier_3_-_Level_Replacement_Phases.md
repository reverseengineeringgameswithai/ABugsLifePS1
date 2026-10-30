---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Tier 3 - Level Replacement Phases.md
aliases:
  - "Tier 3 - Level Replacement Phases"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Tier 3 - Level Replacement Phases.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Tier_3_-_Level_Replacement_Phases.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Tier 3 - Level Replacement Phases
type: migration-roadmap
status: living
created: 2026-07-01
updated: 2026-07-01
tags: [tier3, roadmap, migration, level-replacement]
---

# Tier 3 — Level Replacement Phases

**Authoritative, LIVING implementation & migration roadmap** for transitioning the Tier-3 custom level from the current
**host-shell OVERLAY** (native LEVEL01 runs underneath; we hide/neutralize it per-frame) to a **TRUE custom LEVEL01**
(native runtime is a thin host; all authored CONTENT is ours). Engine *architecture* itself stays documented in
[[Tier 3 - Custom Level Engine]]; THIS note owns the migration plan, phase status, evidence, risks, and Definition of
Done. Update this note as phases progress (check the boxes, append to the Evidence Log, revise Open Questions).

Related bug fixed en route: [[Tier 3 - Custom Level Bugs]] (2026-07-01 LEVEL00 leak). Content-edit tooling:
[[pass1-scenery-edit]], [[type3f-delete-cc5]], [[enemy-chaser-spawn-areas]]. Geometry leads: [[abl-geometry-g55-state]].

**STATUS AT A GLANCE (2026-07-01):** Phase 0 ✅ · Phase 1 ✅ · Phase 2 ✅ · Phase 3 ❌ reverted (chunk-35 stub `FUNC_800172DC`
also draws Flik — worked around, not needed) · Phase 4 ✅ reframed (grass removed; the DIRT we couldn't strip is now the
KEPT backdrop, not a target) · Phase 5 ✅ done (suppress disabled → backdrop restored; DoD re-verified). **Net: the
migration goal is met** — custom floor + authored objects over the native far backdrop, foreground terrain/grass/surplus
removed, Flik/HUD/boot intact, crash-stable. Build with `tools/tier3_build_level.sh build/mylevel.blend`. Remaining polish
(NON-blocking): the faint low-OT native-terrain streak at extreme grazing angles; a future authored-material pass
(`NEUTRAL_TINT 0`) for per-surface textures; optional bake-out of the per-frame collision neutralize.

---

## 1. Project goal & non-goals

### Goal
Make the **Blender-authored level the PRIMARY source of truth** for LEVEL01: custom floor/terrain/geometry + authored
collectibles are what the player sees and interacts with. Native LEVEL01 terrain, props, enemies, and stray objects are
**removed or bypassed at their DATA SOURCE**, not merely per-frame suppressed. Only *intentionally retained* native
pieces (the sky/backdrop) remain visible. Result: no OG geometry flickering through; a clean, fully custom level.

### Non-goals (explicit — do NOT do these)
- **NOT** reimplementing Flik's controller/animation, the camera, the HUD, the boot/loader, or the object/pickup
  system. Those are the *host substrate* we deliberately keep (SM64-romhack model). Re-writing them = "rewrite the game",
  the path the project rejected.
- **NOT** a render-side "terrain vs Flik" discriminator — PROVEN impossible (see §2). Do not re-attempt it.
- **NOT** decoding the full native geometry/collision *authoring* formats. We bypass them; at most we NULL native
  terrain payloads at the data source (a deletion, not a format decode).
- **NOT** a custom object/collectible engine. Authored collectibles ride the native `type-0x3f` object system.
- **NOT** touching pristine game files permanently — every build stages edits then restores pristine (see Rollback).

---

## 2. Current architecture & its proven limitations

**Current model = host-shell overlay.** The native LEVEL01 fully loads and runs. `LEVEL.DAT` is byte-pristine except
relocated objects. On top of the running native level we inject (all in the resident EXE + a CD-loaded render blob):
- **Custom collision** (`mod/caves/tier3_collision.c` + `tier3_walls.c`) — our Blender triangle mesh owns Flik's
  floor/walls; native collision is *neutralized per-frame* (187 sector floors deepened + swept planes zeroed).
- **Custom render** (`mod/caves/tier3_otrender.c`) — hooks the DrawOTag DMA kick `0x80064618` each frame, reads the
  live native camera (`R@0x80090FB0`, `C@0x1F800374`), software-projects our tris and **depth-sorts each into the game's
  ordering table** (per-pixel composite with Flik/objects), then runs `suppress_terrain()` to hide native terrain.
- **Native ground build** (`fcn.80010000`) — build-stubbed at load (LEVEL01+COPIED-gated, `mod/tier3_loader.asm`).
- **Sky backdrop** — preserved (renderer leaves the background OT pass alone).

### Proven limitation (the crux — why OG content flickers)
`src_re/world_render_dispatch.c` records an **exhaustive, fixed-tools RE effort** that reached a hard NEGATIVE:
> ABL draws **terrain, Flik, and objects through ONE unified, dynamically-listed, double-buffered mesh renderer**
> (`fcn.80010000` + `0x800186F0`). **No render-side discriminator separates terrain from Flik** — ruled out: texpage,
> GP0 command, primitive size, OT offset, builder PC, mesh-pointer (`a0`) range, and per-object struct fields. The
> per-object list is rebuilt each frame at different addresses with no "is-terrain" flag.

So `suppress_terrain` is necessarily a **heuristic** ("collapse gouraud/textured nodes built *high* in the OT"). A
heuristic on an inseparable list mis-fires at some camera angles → native geometry drifts across the offset gate and
**flickers in/out** (operator-reported). **This cannot be fully fixed render-side.** The clean route is source-side.

---

## 3. Target architecture

**Thin native host + custom PLAY-FIELD over the native BACKDROP.** Keep the host substrate; the Blender level supplies the
playable geometry (via our render+collision) and ALL objects (via `type-0x3f` relocate/delete/append). **REVISED
2026-07-01 (Phase 5):** the original "remove ALL native terrain" was wrong — the operator WANTS the native far backdrop
(dirt-cliff walls + grass rim + distant grassy horizon). So the split is by DISTANCE, not "native vs custom":
- Native **NEAR ground**: removed — `fcn.80010000` (the near DAT floor + the RAM-flood source) is neutered at load; OUR
  floor owns the play area on top.
- Native **FAR backdrop** (walls/rim/horizon): **KEPT** — it always renders at its native far depth, behind our floor.
  This is native gouraud terrain; we deliberately do NOT suppress it.
- Native **foreground grass/corn** (tall blades, `tp663` @ `0x80163F74`): removed every frame in the render cave (separate
  source from the backdrop grass rim, which stays).
- Native **objects**: only the authored/relocated collectibles exist in `LEVEL.DAT`; decor/enemies/stray records deleted
  at build time (Phase 2).
- Native **collision**: our mesh owns Flik; keep the cheap per-frame neutralize.
- `suppress_terrain` heuristic: **DISABLED (`SUPPRESS 0`)** — it was collapsing the wanted backdrop (high-OT-offset =
  far = backdrop). Not needed for the near ground (the `fcn.80010000` neuter handles that).
- Custom-floor look: `NEUTRAL_TINT` (render cave) drops the blob's per-face colour so surfaces read as real dirt (the
  texture) instead of the authored/debug tint; `NEUTRAL_TINT 0` restores per-face colour for a future authored-material pass.
- Kept native: boot/loader, Flik controller+anim, camera, HUD, object/pickup SYSTEM, sky + far terrain backdrop.

Endgame render path (optional, separate): the **GTE depth-sorted renderer** (deferred in [[Tier 3 - Custom Level Engine]])
would also fix affine warp + perfect occlusion, but is NOT required for level replacement.

---

## 4. Dependency map — must remain vs. removable at source

### MUST REMAIN (engine depends on it — the intended host substrate)
| Subsystem | Why it can't go |
|---|---|
| Boot + level loader | Loads LEVEL01, produces the frame we hook. Removing = reimplement loading. |
| Flik controller + animation | We override only floor-Y/walls (Phase 1f). Removing = reimplement the character. |
| Camera | The custom renderer READS it (`R@0x80090FB0`, `C@0x1F800374`) to project geometry. |
| HUD | Grains/lives/seed-power/FLIK word (operator keeps). |
| Native object/pickup SYSTEM | Authored collectibles ARE native `type-0x3f` objects relocated onto the custom floor. |
| Sky backdrop | Retained by choice; already preserved (background-pass skip). |

### REMOVABLE AT SOURCE NOW (separable; mostly existing tooling)
| Native content | Removal method | Status |
|---|---|---|
| Near ground mesh (`fcn.80010000` DAT build) | Load-time stub | ✅ done |
| Decor props (mushroom/grass/leaf) | Delete LEVEL.DAT records (`edit_pass1_records.py` / `delete_type3f_entries.py`) | 🟢 tooling exists |
| Enemies (mosquito/bee/spider) | Delete/disable spawn records (chaser areas / stationary anchors) | 🟢 tooling exists |
| Stray/surplus collectibles (~44 floating) | Build-delete surplus (`tier3_native_objects.apply_objects_exact`; solve FLIK-pin ordering) | 🟢 tooling exists |
| Chunk-35 background terrain (grass/wall sliver) | ~~Stub `FUNC_800172DC`~~ — REVERTED: that fn also draws Flik's body | 🔴 abandoned (not needed; kept as backdrop) |

### HARD PIECE (only if residual after the above)
Near-terrain leaking after object deletions + chunk-35 stub ⇒ **null the DAT/RAW terrain mesh payloads at build time**
(DAT-backed payloads "A–E" identified, [[abl-geometry-g55-state]]; Candidate A = DAT 0x188cc). Data-source nulling CAN
separate terrain from Flik (Flik is the separately-spawned player, not a DAT payload). Bounded native-format work; verify
loader/objects survive before baking.

---

## 5. Phased implementation plan (success criteria + rollback)

> **Global rollback contract:** `tools/build_tier3_render_disc.py` STAGES edits into `REBUILD/files/*` then RESTORES
> pristine in a `finally` block (asserts restore). So pristine game files are never permanently mutated; a bad build
> only affects `build/ABL_tier3_render.{bin,cue}`. Per-phase rollback = revert the specific `mod/` or tool change (git)
> + rebuild. Record the canonical `.bin` sha256 at each green phase so regressions are detectable. Keep the last-known-good
> disc hash in the Evidence Log.

### Phase 0 — LEVEL00 leak fix (engine was leaking OUT of LEVEL01)  ✅ DONE (2026-07-01)
Gate the engine strictly to LEVEL01 so it never activates in LEVEL00/02/…. See [[Tier 3 - Custom Level Bugs]].
- **Success:** LEVEL00 cold-boots identical to pristine; LEVEL01 unchanged. ✅ verified.

### Phase 1 — EVIDENCE PASS: classify what actually leaks  ✅ DONE (2026-07-01)
Booted `build/ABL_tier3_render.cue`, reached LEVEL01 (movie + turbo), panned to a grazing angle, `gpu.pickObject`
grid-census + matched-frame A/B (native CRTC 512×224). **Leak inventory (grazing pose):**

| On-screen class | GP0 signature | Source | Removal | Keep? |
|---|---|---|---|---|
| Our custom floor | `GP0(24)` tri, texpage `0x660`, clut `0x3ffc`, ram in NODEBUF `0x1F9400+` | our render | — | ✅ keep |
| Authored collectibles | `GP0(2c)` clut `0x3677` (grain), `GP0(2e)` clut `0x3672` (FLIK), `GP0(2d)` clut `0x3770` — in native OT | native object system (relocated) | — | ✅ keep |
| **Native TERRAIN** | `GP0(3c)`/`GP0(34)` gouraud-textured, texpage `0x604`, clut `0x3a70..0x3a78`, native OT ram `0x1cd/0x1ce/0x1e2/0x1e3xxx` | ≥2 builders | **Phase 3 (partial) + Phase 4** | ❌ remove |
| **Native DECOR / floating objects** | `GP0(60)` sprites (no texpage), `GP0(3e)`, + surplus collectibles (`0x2c/0x2e` clut `0x367x`) floating in the sky at original coords | native decor + surplus `type-0x3f` | **Phase 2** | ❌ remove |

**Decisive matched-frame A/B (`loadState` + 3-frame advance; chunk-35 stub = live `jr ra` at `FUNC_800172DC`):**
NAT_TERRAIN **19 → 10** hits; OUR_FLOOR (407→410) + AUTH_COLLECT (29→30) unchanged. ⇒ **chunk-35 (`FUNC_800172DC`) is
~HALF the terrain leak — a clean, safe partial win.** The other half is a DIFFERENT builder: `fcn.80010000` is already
stubbed (`@0x80010000=0x0801fcc1`, `COPIED=1`, confirmed), so it is NOT the residual source; a second terrain builder
(candidate: background builder `0x80017480` / shared mesh `0x800186F0`, or a DAT terrain-payload path) remains for Phase 4.
- **Conclusion:** the flicker = **native terrain (gouraud) + floating surplus/decor objects**, NOT one source. Phase 2
  (delete floating/decor objects) and Phase 3 (chunk-35 stub, ~50% terrain) are independent clean wins; Phase 4 closes the
  rest. Our floor + authored collectibles are safe throughout. Captures: `phase1_graze*.png`, `final_*.png` (scratch,
  gitignored). Harness: scratchpad `phase1_*.py` (pickObject census + matched A/B).
- **Rollback:** none (read-only; the chunk-35 stub was live-only + reverted).

### Phase 2 — Object source-removal (biggest, low-risk win)  ✅ DONE (2026-07-01)
Deleted all un-authored / surplus native `type-0x3f` collectibles from `LEVEL.DAT` at build time. Implemented an
`exhaustive=True` mode in `tools/tier3_native_objects.py::apply_objects_exact` (deletes pre-FLIK surplus + un-authored
delete-safe kinds, not just warns) and rewired `tools/build_tier3_render_disc.py` to compute the count-controlled DAT
EARLY and generate the FLIK pin header from the POST-DELETE DAT (so the renumbered FLIK entries are pinned correctly).
Default-on for the Blender flow; `TIER3_KEEP_SURPLUS=1` reverts.
- **Result (build):** 55 surplus deleted (44 grains + 4 berries + 6 green/blue seeds + 1 orange seed), DAT 332824→331944
  B (still 163 sectors, LEVEL.RAW untouched). Remaining type-3f = 15: 6 authored grains + 4 FLIK + 2 seed + 3 telescope.
- **Cold-boot verified** (`build/ABL_tier3_render.cue`, `.bin` sha256 `86b59297…`, movie `flik_to_level01_stall`):
  live type-3f COUNT = **15** (was 70). FLIK letters renumbered 50-53 → **6-9** and **still collect** — warped Flik onto
  letter F → bitmask `0x800A65A2` 0x0→**0x1**, `pc` in user RAM (no crash). The floating-blob mass is GONE vs the Phase-1
  grazing frame; the 2 gold objects still visible on the left are **authored grains** (idx 0-1, operator placed them
  elevated Y≈-21k), not surplus. Our floor + authored collectibles + HUD intact.
- **Success criteria:** ✅ surplus objects gone, authored collectibles render + collect, HUD intact, Flik on floor, no
  crash. Captures `phase2_graze.png`; harness `phase2_*.py` (scratch).
- **RESIDUAL:** 2 delete-UNSAFE surplus **telescopes** (kind `0x30`, idx 13-14) still float far off — `0x30` is excluded
  from `DELETE_SAFE` (native hint system may key on it; unverified). Small + bounded; deferred (test telescope-delete
  safety before enabling). NOTE: native DECOR props (mushroom, `GP0(60)` sprites) are NOT `type-0x3f` — if any remain
  visible they're a separate pass-1-scenery delete (Phase 2b, `tools/edit_pass1_records.py`), tracked separately.
- **Rollback:** `TIER3_KEEP_SURPLUS=1` env, or revert the two tool edits; pristine DAT restore guarantees no permanent
  file change.

### Phase 3 — Chunk-35 terrain source-removal  ❌ REVERTED (2026-07-01) — FUNC_800172DC also draws FLIK
> **REVERTED — the stub broke Flik.** `FUNC_800172DC` is **NOT terrain-only**: it is one of ABL's generic GTE mesh
> submitters, SHARED by terrain AND the player. Stubbing it (to hide chunk-35) also removed **Flik's body mesh** — Flik
> rendered as a headless/torsoless thin-limb figure (operator-reported "Flik is all garbage"). Decisive A/B: live-restoring
> `FUNC_800172DC` (`0x800172DC`→`0x3c021f80`) brought Flik's torso back WHOLE; re-applying the neuter removed it again.
> Phase 1's "19→10 while KEEPING Flik" was a false pass — it checked the terrain census + Flik's *state* (pos/grounded),
> not his *model*, so the missing torso went unnoticed (and the thin figure in the Phase 3 captures was misread as an
> animation pose). **Lesson:** render-side stubbing of a shared submitter is exactly the intractable path this file warns
> about; terrain removal MUST be data-source (Phase 4 — empty the terrain render-LIST counts, which leaves the shared
> submitters intact for Flik; verified: the DIRT-list poke keeps Flik's model whole). **Reverted** the hook +
> `tier3_neuter_172dc` + the `fname` move in `mod/tier3_loader.asm`; rebuilt disc `86b59297…` (== the Phase-2 EXE), Flik
> whole again on cold-boot. See [[Tier 3 - Custom Level Bugs]] "Flik model garbage".

**HISTORICAL (superseded — the stub worked mechanically but broke Flik; kept for the RE trail):** original Phase 3 —
Baked a COPIED-gated neuter for `FUNC_800172DC` (the resident `SCUS_942.88` per-frame chunk-35 terrain submitter),
mirroring the `fcn.80010000` neuter, in `mod/tier3_loader.asm`. Hook at `0x800172DC` → `tier3_neuter_172dc` @`0x8007F340`
(replays the `lui v0,0x1f80` prologue on the run-normally path; `jr ra` when `COPIED=1`). Moved `fname`
`0x8007F340`→`0x8007F328` to free contiguous room in the boot-safe loader zero-run. `transferLog.resolve` confirmed
`FUNC_800172DC` is **resident EXE** (fileOffset 31452), so it's shared by all levels and the COPIED gate is required.
- **Verified (cold-boot `build/ABL_tier3_render.cue`, `.bin` sha256 `c5fe4d99…`):**
  - **LEVEL01 (`COPIED=1`):** `execTrace` on the body `0x800172E4` = **0 hits** (chunk-35 submit suppressed at source);
    forcing `COPIED=0` → 16 hits (runs) — deterministic proof the neuter works. Matched A/B at a fixed grazing pose
    (toggle hook live) = **identical** → NO regression (removing chunk-35 reveals nothing behind it). Floor + collectibles
    + Flik on floor (`Y=-266`) intact, no crash, hook `@0x800172DC = 0x0801fcd0`.
  - **LEVEL00 (`COPIED=0`):** renders identically to pristine (full terrain, tutorial blackboard) — the gate holds; the
    neuter's non-COPIED path runs `FUNC_800172DC` normally. Same COPIED mechanism as the Phase-0-verified `fcn.80010000`.
- **HONEST caveat:** chunk-35's VISIBLE contribution is **pose-dependent** — ~half the terrain at the Phase-1 grazing
  pose (19→10), but ZERO at other poses where the grass/sand cliffs (the **2nd builder**, Phase 4) dominate. Both builders
  emit gouraud texpage `0x604`, so a census can't split them per-pose. Phase 3 is a correct, safe, source-level removal of
  the chunk-35 half; the bigger visible win is Phase 4. Captures `phase3_graze.png`, `phase3_lvl00.png`; harness
  `phase3_*.py` (scratch).
- **Rollback:** remove the `0x800172DC` hook + `tier3_neuter_172dc` (and restore `fname` @`0x8007F340`); rebuild.

### Phase 4 — Residual terrain builders  ✅ RESOLVED-BY-REFRAME (2026-07-01) — GRASS removed; DIRT is now the KEPT backdrop, not a target
> **UPDATE 2026-07-01 (Phase 5 reframe):** the "remove the DIRT terrain" goal is **retired**, not failed. The near dirt is
> already gone (the `fcn.80010000` neuter + our floor on top); the FAR dirt (walls/rim/horizon) is the **backdrop the
> operator wants kept** (§3/§5). So "DIRT can't be data-source-removed without dropping Flik" no longer blocks the DoD — we
> are not trying to remove it. **GRASS mechanism also changed:** the source-truncation moved from the collision cave's
> SPAWN_DONE one-shot to the RENDER cave `tier3_otrender_hook` (EVERY frame) — the one-shot didn't survive the game's
> discrete post-spawn rebuild of the grass list while Flik idled. See [[Tier 3 - Custom Level Bugs]].
> **HISTORICAL (below): the DIRT-removal investigation — kept for the RE trail, but no longer a goal.**
> **CORRECTION (2026-07-01): the DIRT lever is NOT Flik-safe — it dropped Flik.** The earlier "both passes done" below was
> wrong. Cold-boot on the both-levers disc: **Flik didn't render at all** (operator-spotted). Diagnosed live — restoring
> the GRASS source left Flik gone; restoring the DIRT count (`[[0x800A6300]+6]`→24) brought Flik back (0→45 gouraud prims).
> So dispatch `0x8001d3cc` **draws Flik too**; zeroing its count early-exits the whole pass (same shared-render trap as the
> reverted Phase 3). My "Flik-safe" PoC checked his *state* (grounded/walk/jump), not his *model* — the recurring mistake.
> **FIX:** the baked one-shot (`mod/caves/tier3_collision.c`) now applies ONLY the **GRASS source-truncation** (Flik-safe);
> the DIRT count lever is removed. Cold-boot verified (`.bin` `cbfff41c…`): **grass gone (tp663=0), DIRT stays (tp604=17),
> Flik whole** (45 prims spawn / 33 after roam+jump), LEVEL00 unaffected. **DIRT terrain removal is OPEN** — needs a
> Flik-separable lever (e.g. null only the terrain objects' mesh ptrs in the `0x800A6300` list while keeping the count so
> Flik's draw survives — unverified), or the GTE render path. See [[Tier 3 - Custom Level Bugs]] "Flik is MISSING".

**HISTORICAL (the DIRT half is WRONG — see correction above):** original Phase 4 "DONE" —
> **DONE — data-source terrain removal baked into the LEVEL01 spawn one-shot.** Both native gouraud terrain passes are
> emptied at their render LISTS (leaving ABL's SHARED GTE submitters intact for Flik):
> - **DIRT** (tp `0x604`): `*(u16*)([0x800A6300]+6) = 0` (render-list count).
> - **GRASS** (tp `0x663`): `*(s16*)0x80163F82 = -1` — truncate the source list at `0x80163F74` so the GTE culler
>   `FUNC_80014360` returns 0 visible grass. (The grass count is COMPUTED per-frame from a sentinel-terminated source
>   list — `lh [a0+0xe]; bltz→exit` — NOT a stored word, so the lever is the source terminator, not a count.)
>
> Both levers persist (built once at load), so a single one-shot in `mod/caves/tier3_collision.c` (SPAWN_DONE, already
> DAT_BASE-gated to LEVEL01) suffices. **Cold-boot verified** (`build/ABL_tier3_render.cue`, `.bin` sha256 `04d7a25f…`):
> gouraud terrain hits (604/663) = **0 at spawn, grazing, AND after roam+jump** (stays gone); Flik grounded on the custom
> floor, walks + jumps, no crash; Flik's **model whole** (verified live with both levers = a proper full ant, and the
> levers don't touch the shared submitter that Phase 3 broke). **SURVEY:** these are the ONLY two gouraud terrain
> texpages; no third gouraud pass. **RESIDUALS (separate, not gouraud terrain):** (1) a faint **background horizon band**
> (grass strip + dirt wall) = native env/sprites (the kept backdrop or a sprite layer, `obj/other` class) — minor; (2)
> removing terrain reveals more **native decor/objects** behind it (Track-B object cleanup); (3) **Flik's feet clip into
> the custom floor** — a PRE-EXISTING depth-sort limitation (our floor draws over his feet at equal depth, no Z-buffer;
> render-OFF shows clean native feet), NOT a Phase-0..4 regression; fixable by tuning `DS_MUL` (trade-off vs occlusion).
> C: `mod/caves/tier3_collision.c` (SPAWN_DONE terrain-list one-shot). Historical investigation below.

**HISTORICAL (superseded by the DONE bake above; kept for the RE trail):** original Phase 4 — render-side BLOCKED, data-source PoC (2026-07-01)
Traced the terrain left after Phases 2–3 (with `fcn.80010000` + `FUNC_800172DC` both stubbed, verified 0 body hits).
- **Builders pinned** (pickObject → accessLog write-watch on the OT node):
  - **dirt** (gouraud `GP0(3c/34)`, texpage `0x604`, clut `0x3a7x`): writer `0x80014ce8` in **`FUNC_80014b04`** (a sibling
    GTE terrain submitter, entry byte-identical to `FUNC_800172DC`), called from the world-render dispatch
    `0x8001d3cc..0x8001dfe0` (EXACT) at `0x8001dcbc`.
  - **grass/mound** (gouraud `GP0(3c)`, texpage `0x663`, clut `0x3e7x`): writer `0x80013700` in fn `0x80013108..0x8001409c` (EXACT).
  - the "sand cliffs" a grazing view shows are **our floor** (`GP0(24)` tp `0x660`, NODEBUF) — not a leak.
- **Terrain data IS separable from Flik:** over 40 breakpoint hits at `0x80014ce8`, the mesh ptr `a1` was ALWAYS in the
  decompressed-LEVEL.RAW terrain region `0x8012c64c..0x8012e5cc`, NEVER Flik's CHARS model region.
- **BUT render-side neutering is INTRACTABLE** (re-confirms `world_render_dispatch.c`): naive `jr ra` at `FUNC_80014b04`
  / the grass fn / the dispatch either **destabilized the guest** (pc→`0x00000df8`/`0x1a44`) or left terrain **unchanged**
  (multiple tangled builders/paths); the dispatch `0x8001d3cc` reads `Flik.X` at entry (world/Flik-coupled). Per-builder
  EXE stubs are unsafe + incomplete. **NOT shipped — no broken bake** (disc stays the Phase-3 build `c5fe4d99…`).
- **DATA-SOURCE RE + PoC DONE (2026-07-01) — approach SAFE + validated (runtime-only, nothing baked).** Correcting the
  earlier guess: `[0x80082424]=0x801cc554` is the **OT** the terrain links into (ClearOTagR reversed list), and
  `[0x8008240c]=0x801cc390` is the GPU **draw-env** — NOT the mesh list. Terrain is drawn from **per-object render lists,
  one per pass**, each with its own count:
  - **DIRT** (tp `0x604`, `FUNC_80014b04`) — dispatch `0x8001d3cc..0x8001dfe0` (EXACT) walks an 84-byte-stride object
    array; loop bound `count = (u16)[[0x800a6300]+6]` (live P=`0x800ff984`, count 24). Each `[obj+0x20]` = a LEVEL.RAW
    terrain mesh ptr (`0x8012xxxx`) — **all 24 terrain, none Flik**. **LEVER (proven): write 0 to `[[0x800a6300]+6]`**
    (built once at load, persists) → builder store `0x80014ce8` drops **24→0 hits**, tp604 dirt gone, TERRAIN 154→107.
  - **GRASS/MOUND** (tp `0x663`, builder `0x80013700` in fn `0x80013108`) — SEPARATE dispatch `0x800206e8..0x800212f8`
    (EXACT), called from `0x800228c0` (a0=array `0x80096ea8`, a1=count`=s0`=18). Loop bound is register `s7=a1`.
    **Count source traced (2026-07-01):** `s0 = v0 & 0xffff` at `0x80022888`, where `v0` = RETURN of `jal 0x80014360`.
    **`FUNC_80014360` (`0x80014360..0x80014500`, EXACT) is a GTE cull/build** — transforms the grass SOURCE by the camera
    matrix, WRITES the visible grass into array `0x80096ea8`, and RETURNS the count. So the grass count is **computed
    per-frame from a source list, NOT a stored word** like dirt. Data-source lever = the grass SOURCE's count (inside
    `FUNC_80014360`; not yet pinned), or force `a1=0`/`s0=0` at the dispatch entry `0x800206e8` (`blez s7` skips). Flik
    drawn by **neither** dispatch.
  - **PoC verified SAFE:** zeroing the DIRT count each frame at a grazing pose removed the tp604 dirt with **full
    integrity** — Flik **walked** (Up 30f → moved, `grounded=0x0101`) and **jumped** (`vy=1088`), collision held on the
    custom floor, loader stable (`COPIED=1`, DAT correct, no crash), type-3f = **15** throughout; renderers untouched.
    Validates the data-source approach (vs render-side `jr ra` which crashed). Captures `p4b_FINAL_*.png`; harness `p4b_*.py`.
- **REMAINING for full removal:** empty EACH dispatch's list — DIRT lever done; GRASS needs its count source (`s0` in
  `0x800228xx`) pinned to memory (or force `a1=0` at `0x800206e8`); then survey for further passes. **Eventual mod:** zero
  these counts from the collision cave's LEVEL01 SPAWN one-shot (DIRT persists → one-shot; GRASS may need per-frame).
- **Success criteria (unchanged):** no native terrain on a full LEVEL01 roam; Flik + authored objects + HUD intact;
  cold-boot stable.
- **Rollback:** N/A (nothing baked this phase; runtime PoC + findings only).

### Phase 5 — Retire the heuristic + finalize  ✅ DONE (2026-07-01)
**`suppress_terrain` DISABLED (`SUPPRESS 0`)** — and the reason inverts the original plan. Phase 5 assumed suppress would
be retired because "native terrain is source-removed, nothing left to hide but the sky." In reality suppress was
**collapsing the wanted BACKDROP**: it dropped native gouraud terrain at HIGH OT offset, but that high-offset terrain is
the far dirt-cliff walls + grass rim + distant grassy horizon — the intended environment, not near clutter. Operator
confirmed they WANT that backdrop ("it should always render at the very back"). So the architecture shifted from *remove
ALL native terrain* to **remove NEAR terrain (our floor owns it), KEEP the FAR backdrop** — see revised §3. Disabling
suppress restores the backdrop at its native far depth; our prepended floor draws in front. The `fcn.80010000` neuter (not
suppress) is what guards the turn-around flood crash, so this is crash-safe.
- **Success criteria:** ✅ §8 DoD re-verified cold-boot (below); ✅ `suppress_terrain` disabled; ✅ docs updated (this note
  + [[Tier 3 - Custom Level Bugs]] + memory).
- **Rollback:** `#define SUPPRESS 1` restores the old collapse (code kept).
- **DoD VERIFICATION (2026-07-01, cold-boot `build/ABL_tier3_render.cue` from `mylevel.blend`, `.bin` sha256 `fc924e21…`,
  movie `flik_to_level01_stall` → spawn → walk → jump → grazing pan):** (1) near ground = OUR floor (`GP0(24)` ×233 spawn /
  ×168 grazing) vs ~14–15 native `tp604` = the kept backdrop; (2) authored collectibles render + collect (grain HUD 00→02
  during roam); (3) backdrop present at spawn AND grazing (walls/rim/horizon); (4) Flik's MODEL intact (36 gouraud prims at
  his center — checked model, not just state); (5) jump works (Y −266→−7370); (6) stable — render code `0x801F0C00` stayed
  `0x3c028009` across the whole roam incl. the old flood-crash angle, frames advanced, no fault; (7) foreground grass/corn
  gone. Captures `dod_spawn.png` / `dod_graze.png`.

---

## 6. Evidence log
Append each investigation/RE finding with date, method, and the disc/state it was taken on. Newest first.

- **2026-07-01 — Phase 5 DONE + DoD re-verified: backdrop restored by disabling suppress; level built from mylevel.blend.**
  (1) BACKDROP: `suppress_terrain` was collapsing native gouraud terrain at HIGH OT offset = the far backdrop (walls/rim/
  horizon). Decisive live test at `backdrop_issue.sav`: `RENDER_C@0x801F0C00` → passthrough (`move v0,a0; jr ra`) made the
  backdrop appear instantly at spawn with a clean near area (near floor already gone via the `fcn.80010000` neuter) →
  suppress is net-harmful → `#define SUPPRESS 0`. Turn-around soak (8 dirs) kept render code intact = crash-safe (neuter,
  not suppress, guards the flood). (2) NEUTRAL_TINT: the ground looked like debug-colour blocks because the disc had been
  rebuilt with plain `build_tier3_render_disc.py` (bakes the hardcoded TEST level + overwrites `build/tier3_level.bin`);
  rebuilt from `mylevel.blend` via `tier3_build_level.sh` and set `NEUTRAL_TINT 0x808080` so the dirt texture reads through
  the per-face colour. (3) GRASS hold: moved `tp663`@`0x80163F82=-1` from the collision-cave one-shot to the render cave
  (every frame) — collision hook `0x800495d0` is movement-gated (0 firings idle, proven behaviorally), so the one-shot was
  overwritten by the game's discrete grass-list rebuild while idle. DoD cold-boot (`.bin` sha256 `fc924e21…`): all 10 items
  pass (see §8). Captures `dod_spawn.png`/`dod_graze.png`, `bd_fixed_spawn.png`, `mylevel_neutral.png`.

- **2026-07-01 — Phase 4 DIRT format-preserving patch: CONCEPT VALIDATED (Flik survives!), cold-boot bake unresolved.**
  Decoded `FUNC_80014b04`'s mesh = a GP0 prim STREAM (prims read at `[a1+0]`=cmd; terminator = `(cmd & 0x3c000000)==0`;
  verts in `[a1+4..a1+0x2f]`). The format-preserving no-op = keep every command word (stream length/count/terminator +
  per-prim OT structure preserved) but ZERO each prim's 44 vertex bytes → degenerate/culled no-op. **LIVE PoC (settled
  state): patch objects 0..count-2, spare the LAST object (=Flik) → dirt tp604 28→3 and FLIK'S MODEL IS INTACT (full ant).
  So Flik survives a correct format-preserving patch — the key question answered YES.** Flik = object count-1 (clean
  bisection; this patch is linear, unlike OT-corrupting mesh[0]=0). **BUT the cold-boot BAKE failed** (per-frame then
  one-shot both broke Flik + crashed `pc→0x1a44`): the prims are NOT all 48 B → the fixed-48 stride DESYNCS (obj22
  over-ran into Flik's mesh; mitigated with a hard `a1+0x30<=flik-mesh` bound), and the parse is NON-IDEMPOTENT
  (mitigated with a one-shot flag) — yet cold-boot still broke Flik identically (a cold-boot-vs-settled difference not
  cracked). REVERTED to the grass-only bake (`cbfff41c`, Flik whole). Remaining: a correct VARIABLE-PRIM-SIZE decoder +
  reliable cold-boot Flik-object ID, or the GTE render path. `src_re/world_render_dispatch.c`; harness `p7_*.py`.
- **2026-07-01 — Phase 4 DIRT-pass RE: mesh-null lever CORRUPTS the OT; dirt is inseparable from Flik.** Enumerated the
  `[0x800A6300]` list (24 static LEVEL.RAW terrain objects, base `0x8008a054` stride 84, mesh `[obj+0x20]`; none animate).
  `FUNC_80014b04` parses each mesh as a GP0 prim stream, exiting when `(word & 0x3c000000)==0` (mesh[0]=0 = terminator).
  Flik's body is gouraud **texpage 0x604 — same as dirt** — in the same `0x8012xxxx` work region (indistinguishable). PoC
  (null the 24 terrain meshes, keep count) FAILS non-linearly: nulling either 12-obj half leaves Flik's body box unchanged
  (94), but nulling all 24 drops it to 12 (Flik broken) → the zeroed objects leave dangling OT nodes that corrupt the
  shared scene-OT chain, dropping Flik. Conclusion: dirt is inseparable from Flik via this lever; only the GTE render path
  can remove it cleanly. Kept the safe grass-only bake (`cbfff41c`, Flik whole). See `src_re/world_render_dispatch.c`.
- **2026-07-01 — Phase 4 DONE: both gouraud terrain passes source-removed + baked.** Grass lever found: `FUNC_80014360`
  (grass GTE culler) iterates a sentinel-terminated source at `0x80163F74` (`lh [a0+0xe]; bltz→exit`) and returns the
  visible count; truncating it (`[0x80163F74+0xe]`=-1) → grass tp663 100→0. Both levers (dirt count `[[0x800A6300]+6]`=0
  + grass source truncate) persist (built once at load), baked into the SPAWN_DONE one-shot in `tier3_collision.c`.
  Cold-boot (`04d7a25f…`): gouraud terrain=0 at spawn/graze/roam+jump, Flik whole + walks/jumps, no crash. Survey: only
  2 gouraud passes. Residuals: bg horizon band (env/sprites), revealed native decor, depth-sort foot clip (pre-existing).
- **2026-07-01 — Phase 3 REVERTED (broke Flik) + grass count traced.** Operator reported Flik = garbage. A/B: restoring
  `FUNC_800172DC` (`0x800172DC`→`0x3c021f80`) → Flik's torso WHOLE; re-applying the Phase-3 neuter → torso gone. So
  `FUNC_800172DC` is a Flik-SHARED submitter, not terrain-only; Phase 3 reverted (disc `86b59297…` == Phase-2 EXE, Flik
  whole cold-boot). Confirmed the DIRT-list data-source poke keeps Flik's MODEL whole (unlike the function stub). Grass
  count source traced: `s0=v0&0xffff` ← `jal 0x80014360` (GTE cull/build that returns the count) → computed per-frame,
  not a stored word. See [[Tier 3 - Custom Level Bugs]].
- **2026-07-01 — Phase 4 data-source RE + PoC (DIRT list emptied, SAFE).** Terrain = multi-dispatch: DIRT dispatch
  `0x8001d3cc`, count `(u16)[[0x800a6300]+6]`=24, all objects LEVEL.RAW terrain (`[obj+0x20]`=`0x8012xxxx`); GRASS
  dispatch `0x800206e8` (count=arg `s0`, array `0x80096ea8`). Zeroing the DIRT count (built once, persists) → builder
  `0x80014ce8` 24→0, tp604 dirt gone (census 154→107), Flik walked+jumped, collision/loader/type-3f(15) all intact,
  renderers untouched. Validates data-source approach. Full removal needs each dispatch's count emptied (GRASS next).
- **2026-07-01 — Phase 4 residual-terrain builders investigated (render-side BLOCKED, data-source DEFERRED).**
  pickObject→accessLog write-watch pinned the leftover terrain: dirt `0x80014ce8` in `FUNC_80014b04`, grass `0x80013700`
  in fn `0x80013108`, called by dispatch `0x8001d3cc` (EXACT). Mesh ptrs all in LEVEL.RAW `0x8012c64c..0x8012e5cc`
  (terrain-only, Flik separate). Naive `jr ra` neuter crashed the guest (pc→`0xdf8`) or didn't reduce terrain →
  render-side stubbing intractable (multiple tangled builders; dispatch reads Flik.X). Deferred to data-source
  mesh-list nulling (`[0x80082424]=0x801cc554`). Nothing baked (disc stays `c5fe4d99…`). Harness `p4_*.py`.
- **2026-07-02 — HRE-012 dynamic grain HUD/emblem INTEGRATED (runtime-install, zero in-image cave).**
  The grain30 mod's cave region `0x800810C0` belongs to the collision cave, and NO other in-image zero-run is
  boot-safe (`0x8007FD55` = live buffer; `0x8007EFE6` = a dormant zero-init table the game polls from
  `0x800616xx` — readwrite-watch verified). Solution: `mod/caves/tier3_grain.c` rides TIER3.RND (grain segment
  @`0x801F2C00`, shim @`0x801F2BF8`; RENDER_PAD 0x2C00→0x3400, blob→`0x801F3400`) and `tier3_load_render`
  installs the 3 EXE hooks at the first gameplay frame (HUD `j` @`0x80052B40`→pause-gated tramp; emblem gate
  `j` @`0x80055008`; reveal threshold `sltiu` @`0x80052AC0` re-encoded with the LIVE total). Cold-boot verified:
  boot→movie→custom LEVEL01, SELECT panel draws **"00/50"**, roam + stall/pause clean. **TWO GOTCHAS**:
  (1) execute freshly-CD-loaded code only AFTER a FlushCache (stale i-cache → A(0x40));
  (2) **BIOS FlushCache A(0x44) called FROM the freshly-loaded RND code chain panics the fork's RECOMPILER**
  (bisected: byte-identical write + C-side flush = jump-to-−1 AdEL panic EPC=0xFFFFFFFF; write without flush =
  clean; interpreter mode never crashes) — keep every flush INLINE in the in-image loader. Pause flag found:
  `0x8008224E` (1 = pause menu, 0 = gameplay AND SELECT panel). Residuals: non-50 cold-boot demo via an
  authored sidecar level; emblem full-fire live test; hooks persist if LEVEL01 is exited (no working exit today).
- **2026-07-01 — Phase 3 chunk-35 terrain source-removal DONE.** Baked COPIED-gated `FUNC_800172DC` neuter
  (`mod/tier3_loader.asm`). `transferLog.resolve`: FUNC_800172DC = resident EXE (fileOffset 31452). Cold-boot verified:
  LEVEL01 body `0x800172E4` execTrace 0 hits at COPIED=1 (16 at COPIED=0), matched A/B identical (no regression), floor +
  collectibles + Flik intact; LEVEL00 terrain renders identical to pristine (gate holds). Caveat: chunk-35's visible
  share is pose-dependent (~half at the Phase-1 grazing pose, zero elsewhere where the 2nd builder's grass/sand dominate).
  Disc sha256 `c5fe4d99…`.
- **2026-07-01 — Phase 2 object source-removal DONE.** `apply_objects_exact(exhaustive=True)` + pin-from-post-delete-DAT.
  55 surplus type-0x3f deleted at build time (DAT 332824→331944). Cold-boot: live type-3f 70→15, FLIK renumbered 50-53→6-9
  and still collects (bitmask 0x0→0x1 on collecting F), no crash, floor + authored collectibles intact. Residual: 2
  delete-unsafe surplus telescopes. Disc sha256 `86b59297…`.
  **UPDATE 2026-07-02 — telescope delete-safety REFUTED as a blocker**: deleted kind-0x30 entries 68/69 from
  pristine LEVEL01 DAT (`--allow-checkpoint`), rebuilt + cold-booted + movie-replayed to LEVEL01: table 70→68,
  histogram correct (1 telescope left, bobbing), Flik controllable, fall-death/respawn OK, checkpoint flag normal,
  no guest halt (6200+ frames). The 2 surplus Tier-3 telescopes can be deleted at build time. Residuals: contact/hint
  interaction with a remaining telescope + level-completion regression untested. Gotcha: `movie.stopPlayback` BEFORE
  `setControllerState` (skipping it killed the host process once). Details:
  [[Finding - Pass-3 decor records decoded (cull anchor + suppression)]] §telescope.
- **2026-07-01 — Phase 1 evidence pass DONE.** `build/ABL_tier3_render.cue`, LEVEL01 grazing pose (`gpu.pickObject`
  grid-census + matched-frame `loadState` A/B). Leak = native TERRAIN (`GP0(3c/34)` gouraud, texpage `0x604`, clut
  `0x3a7x`) + floating DECOR/surplus objects (`GP0(60)` sprites + surplus collectibles at orig coords). Our floor
  (`GP0(24)` tp `0x660`) + authored collectibles (`GP0(2c/2e/2d)` clut `0x367x`) render correctly. Chunk-35
  `FUNC_800172DC` live-stub → terrain 19→10 (≈half), floor + collectibles unchanged; residual terrain is a 2nd builder
  (fcn.80010000 already stubbed, ruled out). See §5 Phase 1 table.
- **2026-07-01 — Phase 0 done + LEVEL00 leak root-caused.** `LEVEL00_load.movie.json` on tier3 vs pristine:
  tier3 LEVEL00 had `COPIED=1 / LV_MAGIC=T3LV / Flik warped to (197091,-266,492897)`; pristine `COPIED=0 / LV_MAGIC=0 /
  Flik (-22044,15860,-19597)`. Cause: `tier3_load_render` loaded `level01\tier3.rnd` in every level. Fixed by LEVEL01
  gate. Post-fix: LEVEL00 renders native terrain/tutorial-sign correctly; LEVEL01 custom level still renders + collision
  works. Details: [[Tier 3 - Custom Level Bugs]].
- **(historical) Render-side terrain/Flik inseparability — PROVEN NEGATIVE.** `src_re/world_render_dispatch.c`
  (2026-06-25 multi-pass RE + fixed-tools CORRECTION + object-type-field hunt): terrain, Flik, objects share one unified
  mesh renderer; no discriminator (texpage/GP0/size/OT-offset/builder-PC/`a0`-range/struct-field) separates them.
  Background/scene pass split by head tag length; sky backdrop preserved (2026-06-30).
- **(historical) GAP-T3-5** ([[Tier 3 - Custom Level Engine]]): `fcn.80010000` ground build removed+baked; chunk-35
  `FUNC_800172DC` neuter keeps Flik + no crash (small ~0x30 quads); visible native clutter is OBJECTS/decor, not chunk-35.

*(Phase 1 findings will be appended here.)*

---

## 7. Open questions, risks & remaining RE tasks
- **A (Phase 1, ANSWERED 2026-07-01):** the flicker is BOTH — native gouraud terrain AND floating decor/surplus objects.
  Chunk-35 stub removes ~half the terrain; a **2nd terrain builder** produces the rest ⇒ Phase 4 IS needed.
- **Q (Phase 4):** WHICH builder makes the residual ~10 terrain hits (fcn.80010000 ruled out — already stubbed)?
  Candidates: background builder `0x80017480`, shared mesh assembler `0x800186F0`, or a DAT terrain-payload path fed to
  the generic dispatch. Method: pickObject a residual-terrain prim → `accessLog` write-watch its OT node → builder PC
  (per `world_render_dispatch.c`'s pickObject→writer technique), then stub/null at the source.
- **Q (Phase 2):** FLIK-pin renumber ordering — deleting surplus `type-0x3f` before the pinned FLIK slots renumbers
  them. Fix: compute the pin indices AFTER deletes, or delete only entries after the FLIK slots. Verify the pin still
  hits the right entries live.
- **Risk (Phase 4):** the loader/parser or object dispatch may reference the DAT terrain payloads; nulling them could
  desync the parser (cf. the cold-boot DAT-parser poisoning already seen). Mitigate: edit one payload → cold-boot →
  verify Flik + objects + no `0x8008239c`-style parser corruption before nulling all.
- **Risk (enemies):** deleting an enemy that a script/event references (mover-VM, [[event-interpreter-mover-vm]]) could
  leave a dangling reference. Prefer disabling spawn over deleting the actor if a live test shows instability.
- **Risk (DAT sector budget):** deletes shrink DAT (safe); any appends must keep DAT ≤163 sectors (else overruns
  `LEVEL.RAW` @LBA 3069). The build already asserts this.
- **RE task (Phase 4, if needed):** confirm which DAT node-array payloads are terrain vs prop/decor (payloads A–E in
  [[abl-geometry-g55-state]]); the "A–E" split exists but only Candidate A is confirmed floor-visual.
- **Open:** the separate wall-render "blob" bug ([[Tier 3 - Custom Level Bugs]] open) — track independently; not a
  blocker for level replacement.

---

## 8. Definition of Done — true custom LEVEL01
**REVISED 2026-07-01** (backdrop is KEPT, not removed — see §3). All must hold on a **cold-boot** of
`build/ABL_tier3_render.cue` (no save states, no live pokes), across a full roam (spawn → walk → jump/butt-slam → hard
camera pan to grazing angles):
1. **NEAR ground = our floor** — no native dirt ground under/over the play field; OUR floor owns it. ✅ (GP0 0x24 ×233
   spawn / ×168 grazing vs ~15 native tp604 = the kept backdrop).
2. **No native decor/enemies/stray objects** — only Blender-authored geometry + authored collectibles render (Phase 2
   deleted 55 surplus; 2 delete-unsafe telescopes left). ✅ (with the noted telescope caveat).
3. **Backdrop present at the VERY BACK** — native far terrain (dirt walls + grass rim + distant grassy horizon) + sky,
   always, at spawn and every angle. ✅ (Phase 5 fix; verified spawn + grazing).
4. **Authored collectibles work** — grains/FLIK letters/telescopes/seed tokens render at Blender coords, collect, drive
   HUD. ✅ (grain HUD 00→02 during roam).
5. **Host substrate intact** — Flik controller/animation (MODEL, not just state: 36 gouraud prims), camera, HUD, boot,
   jump (Y −266→−7370). ✅
6. **Stable** — no crash over a long roam incl. the old flood-crash grazing angle (render code `0x801F0C00` stayed
   `0x3c028009`, frames advanced). ✅  *(precise fps not re-measured; no new per-frame terrain scan — suppress is OFF.)*
7. **`suppress_terrain` disabled** (`SUPPRESS 0`) — the near ground is clean via the `fcn.80010000` neuter, and the
   backdrop is intentionally kept. ✅
8. **Foreground grass/corn removed** — every-frame render-cave truncation of `tp663` @ `0x80163F74` (backdrop grass rim is
   a separate source, stays). ✅
9. **Other levels unaffected** — LEVEL00/02/… still cold-boot identical to pristine (Phase 0 gate: DAT_BASE≠LEVEL01 →
   engine + neuter + render all inert). ✅ (Phase 0; not re-run this pass).
10. **Reproducible** — canonical `.bin` sha256 `fc924e21…`; build restores pristine EXE + LEVEL.DAT; plan/evidence updated
   here. Build via `tools/tier3_build_level.sh build/mylevel.blend` (NOT plain `build_tier3_render_disc.py`, which bakes
   the debug test level).
