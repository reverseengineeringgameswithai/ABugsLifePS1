---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Tier 3 - Custom Level Engine.md
aliases:
  - "Tier 3 - Custom Level Engine"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Tier 3 - Custom Level Engine.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Tier_3_-_Custom_Level_Engine.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

# Tier 3 — Custom Level Engine (hosted inside ABL)

**Status:** NEW major initiative (operator end-goal). **Phases 1–3 DONE; Phase 4 authoring pipeline DONE (4a+4d+4b); Track B v1 DONE (pragmatic visual cleanup).**
The cold-boot disc `build/ABL_tier3_render.cue` boots straight to a playable, visible, drivable custom level
(collision + render, no save state), **VERIFIED CRASH-STABLE (2026-06-27)** (1800 frames turning + jump +
butt-slam, no crash), AND a level can be **authored in Blender → one button → cold-boot disc**. Levels are now
**TEXTURED** (4b — reuse a real ABL VRAM texture, colour-tinted) with a **custom spawn** (3d — the Blender `Spawn`
empty places Flik). See the 2026-06-27 session logs at the bottom. Remaining: 4c manifold/perf checks, a
tracked sample `.blend`, and optional deeper identity-level object cleanup for the last tiny native fragments.

> **Phase 3b COLD-BOOT VISIBLE CUSTOM LEVEL — DONE (2026-06-26).** `build/ABL_tier3_render.cue` cold-boots → loads LEVEL01 → runs custom collision **AND renders the custom platforms** (green spawn / yellow ramp / magenta-across-gap), Flik composited on top, native terrain suppressed — **no save state**. The 400 B level blob rides in the LEVEL.DAT last-sector slack (DAT stays 163 sectors, LEVEL.RAW @3069 untouched); the 2.6 KB render image ships as its OWN disc file `\LEVEL01\TIER3.RND` (the disc is byte-packed, so it extends the trailing dummy), CD-loaded to 0x801E0000 at the first gameplay frame by the collision cave calling the game's by-name loader `FUNC_80046330` (via a tiny trampoline `tier3_load_render @0x8007F288`, from the SAFE player-update context — calling it from the DrawOTag stub faults). Render flags baked into the render cave. See the **3b.R steps** under Phase 3 + [[Finding - Tier-3 render disc-delivery]]. RESIDUAL polish (step 5): a few native OBJECTS (mosquito/mushroom) still draw, cyan platform C not seen. Bugs fixed earlier this session: (1) **boot hang** — the DrawOTag render stub took its stack-using path outside LEVEL01 (FMV/menu, where `sp` is invalid) → A(0x40) panic; fixed by gating the render path on `COPIED && DAT==LEVEL01` and keeping the reject path 100% stack-free (`mod/tier3_loader.asm`). (2) **"loading…" crash (DBE)** — enlarging the collision cave for the render-copy relocated `CAVE_C` to `0x800810E0`, which the **level loader uses during load** → memcpy `FUNC_8003ef70` overran → Data Bus Error → BIOS panic; fixed by reverting the cave to `CAVE_C 0x80081100 / FLOOR_PUB 0x800814B0 / tramp3 0x80081478`. **GOTCHA: the render code CANNOT ride in LEVEL.DAT or LEVEL.RAW (both LBA-full) nor any safe in-image zero-run → it needs its OWN new disc file loaded via `FUNC_80046330(name,dest)`.** Full delivery analysis: [[Finding - Tier-3 render disc-delivery]] + `src_re/file_loader_80046330.c`. Build: `tools/build_tier3_render_disc.py` (blob-only by default; `ABL_RENDER_IN_DAT` = old overrun path for experiments).
Distinct from the sector-based Blender editor ([[Blender-first ABL level editor]]) — that edits the *existing*
level; this **replaces the level subsystem** so users can author **entirely new levels** (new spawn, new
platforming, new look) in Blender, SM64-romhack / Fast64 style.

> **NEXT DIRECTION (operator, 2026-07-01): move from host-shell OVERLAY → TRUE custom level** — strip native
> LEVEL01 terrain/props/enemies/stray objects AT THE SOURCE (not per-frame suppress), keep only the host substrate
> (boot/loader/Flik/camera/HUD/object-system) + the sky backdrop. The **authoritative implementation & migration
> roadmap** (goal/non-goals, dependency map, phased plan with success criteria + rollback, evidence log, risks, and the
> Definition of Done — incl. the proof that render-side terrain/Flik separation is IMPOSSIBLE, so removal must be
> source-side) lives in **[[Tier 3 - Level Replacement Phases]]**. Keep THIS note focused on engine architecture; track
> migration status there.

## Vision
Operator wants Mario-64-hack-grade custom levels: arbitrary geometry, real 3D platforming (platforms, gaps,
walls, slopes, verticality), new spawn — built in Blender with relative ease. Textures may be reused.

## Why a custom engine (not native-format authoring)
ABL is a closed binary; its geometry/collision *write* formats are largely undecoded/blocked (chunk-35 walls,
fcn.80010000 mesh authoring) and its collision is per-sector-flat + ~6 swept planes (NOT a triangle mesh — see
[[Blender-first ABL level editor]] Stage E note). Decoding all native formats = years. The tractable route is
to **BYPASS them**: treat ABL as a HOST SHELL and inject our own level subsystem. We keep native: boot, Flik's
controller/animation, camera, HUD, audio, the (already-editable) object/pickup system. We replace: collision,
geometry render, level load.

**Both injection primitives are already proven in this project** (so this is engineering, not research):
- GPU primitive injection — drew our own polys into ABL's frame (auto-memory `abl-gpu-injection-starry`).
- Live code hooks — godmode/no-pickup/camera-freeze caves; the player floor-Y commit site (`0x80036cec`) traced.

## Architecture
- **Custom collision engine** (injected MIPS): triangle-mesh floor/wall query (raycast-down floor, swept walls,
  per-tri surface types). Hook the player world-resolution path so the controller reads OUR mesh.
- **Custom geometry renderer** (injected GPU): draw the level mesh, bypassing fcn.80010000/chunk-35.
- **Custom level loader**: level = mesh + collision tris + surface types + spawn + object list, shipped on disc.
- **Blender exporter** → the custom level format (the Fast64-like part; easy once the engine exists).
- **Host (native, kept):** boot, controller, camera, HUD, objects, audio.

## ROADMAP — remaining tracks (authoritative path forward, 2026-06-27)
The CORE engine is **DONE + committed + live-verified**: collision (floors, ramps, exact per-face wall planes),
textured in-world render, disc loader, cold-boot, custom spawn, death/respawn, and the Blender **one-mesh**
authoring pipeline (slope classifies floors vs walls). What remains is everything needed to make a custom level a
real, *playable, good-looking, big-enough* level. Five tracks, each scoped below. (This supersedes the older
"NEXT STEPS" list further down — there, items 1–3/5/6 are DONE, 4 = Track B, 7 = Track D.)

### Track A — Gameplay content (objects + goal): make a Tier-3 level PLAYABLE  ★ recommended next
- **Goal:** collectibles (grains), then a level-EXIT/goal, then enemies — living in the custom geometry, via the
  kept-native object/pickup system. Turns a walkable space into a *completable* level (the SM64-hack end-goal).
- **Approach (spike-first):**
  1. **Collectible spike:** place ONE native pickup at a CUSTOM-world position over our floor; confirm it renders +
     collects (HUD increments). Native pickups are LEVEL.DAT `type-0x3f` records ([[type3f-delete-cc5]],
     [[pass1-scenery-edit]]) in native coords; we anchor our level at the native spawn, so place near it.
     Collection is proximity-to-Flik (not floor-dependent), so it should "just work"; verify render + count.
  2. **Exit/goal:** the native level-exit is a per-sector REGION CODE in the collision sector table
     ([[level-exit-trigger-open-death-confound]]) — which we SUPPRESS (deepen sectors), so it won't fire. Add our
     OWN exit: an EXIT VOLUME in the blob + a cave check "Flik inside it → trigger complete" (set `0x800823a0=1`
     or call the native exit path). 
  3. **Enemies:** stretch (AI + spawn). Defer; ship collectibles + exit first.
- **Depends on:** nothing new. **Risk/effort:** MEDIUM–HIGH (each of objects-at-our-coords + custom exit is a
  spike; enemies = later). **Done-when:** a custom level where Flik collects grains (HUD counts) and reaches a goal
  that completes/exits the level.

### Track B — Visual cleanup ("step 4"): pure custom view
- **Status:** **v1 DONE (2026-06-27)** via pragmatic OT cleanup. The large residual native objects (leaf/right-side
  props/mosquito body) are suppressed while preserving Flik, HUD, and the Tier-3 mesh. A few tiny native model/effect
  fragments can still appear above Flik; the stricter gate that removes them also clips Flik, so deeper cleanup is
  deferred unless perfect purity is required.
- **Goal:** suppress residual native objects (mosquito/leaf/mushroom) + chunk-35 master-mesh walls so only the
  authored level, Flik, and HUD show.
- **Approach:** the GATEOFF terrain-suppress collapses native TERRAIN OT nodes but misses dynamic OBJECTS
  (interleaved with Flik in the OT; animation-dependent texpage/CLUT → no clean OT discriminator). v1 tightens the
  OT offset gate from `0x3000` to `0x1800` and collapses native effect command classes `GP0(2e)`/`GP0(3e)` in
  `mod/caves/tier3_otrender.c::suppress_terrain()`. Negative live tests: zeroing the actor render-list
  `0x80090748` did not remove the residual props; zeroing contact/object array `0x800b0d18` blacked the frame and is
  unsafe. A stricter `GATEOFF=0x1000` removed the last fragments but clipped Flik's body/arms, so `0x1800` is the
  validated cutoff.
- **Depends on:** Track A for authored-object replacement; now uses self-contained Track-A markers, not native object
  allowlisting. **Risk/effort:** MEDIUM for v1, HIGH for perfect identity-level cleanup. **Done-when:** v1 done-when
  met for the current authored level: large unauthored native props gone, Flik+HUD intact; perfect no-fragment purity
  remains a future RE task.

### Track C — Per-surface textures + Blender UVs
- **Goal:** per-face textures (not one tinted dirt tile) + UVs authored in Blender.
- **Approach:** the render cave already emits GP0 0x24 textured tris with planar UV through the clipper. Extend the
  tri record (or a material table) with per-face texpage/CLUT + per-vertex UVs; exporter reads Blender UV layer +
  material→texpage map; render uses them. Reusing native VRAM tiles = easy; uploading CUSTOM textures to free VRAM
  = the stretch.
- **Depends on:** nothing hard (self-contained render+format). **Risk/effort:** MEDIUM (native tiles low; custom
  VRAM higher). **Done-when:** a level with ≥2 distinct UV-mapped textures on different surfaces.

### Track D — Scale up (caps + triangle budget)
- **Goal:** levels bigger than the 64v/128t/32w test caps.
- **Approach:** (1) MEASURE the render OT-insert clipper's real per-frame triangle budget on the live disc (the old
  "NEXT STEPS" item 7); (2) raise `MAXV/MAXT/MAXW` + the cave scratch buffers (NODEBUF sizing) accordingly; (3) for
  big levels, add spatial culling (skip tris far from camera) — the collision floor/wall scans are O(n)/frame too.
- **Depends on:** nothing. **Risk/effort:** LOW–MEDIUM (measurement + constant/buffer bumps). **Done-when:** a
  ~200+-tri level cold-boots and runs without overrun/slowdown; caps documented.

### Track E — Feel polish (small, anytime)
- **Spawn heading:** apply the exported `LV_SPAWN` heading to Flik's facing in the spawn one-shot (find Flik's
  heading field; currently exported-but-unused).
- **Wall anim-pop:** now walls are proper velocity PROJECTIONS — re-check whether the walk anim still pops at a
  wall; soften if needed (earlier discussion).
- **Risk/effort:** LOW each.

### Recommended sequencing
**A (gameplay) is the priority** — it's the end-goal leap and builds on the now-solid geometry. Run **C (textures)**
and **D (scale)** alongside/after as lower-risk enhancers that make levels look and feel real. **B (cleanup)** comes
AFTER A (it needs the authored-object model to allowlist). **E** anytime. Net order: **A → C → D → B**, E opportunistic.

## OPEN GAPS — object population & true level-replace (operator review, 2026-06-28)
Captured from an operator design pass. Tackle one by one; these reframe Track A around the **native** object
system (not the cave) and pin the "replace vs hide" architecture question.

**Architecture clarification that frames all of these:** a Tier-3 disc keeps `LEVEL.DAT` byte-pristine and the
**native LEVEL01 fully loads and runs underneath** (`build_tier3_render_disc.py:47`). Our engine only (a)
**render-suppresses** native terrain at the ordering-table level and (b) **neutralizes** native collision per-frame
(overwrites the 187 sector floors to a deep Y + zeros the plane count). It does **NOT** remove native data from
memory — see GAP-T3-5. Consequence: **the real game objects (grain, telescopes, enemies, and whatever the FLIK
letters are) already spawn in a Tier-3 level** from native data — Track B even suppresses some as visual noise. So
"differentiated objects" is mostly a *native-object placement* job, not a cave-reimplementation job.

### GAP-T3-1 — Differentiated objects come from NATIVE objects, not cave markers
Track A v1 shipped **self-contained cave markers** (generic orange `Pickup` spheres → bump the grain counter; one
`Exit` volume). They are NOT typed — there is no grain-vs-token concept, and they are stand-ins, not the real objects.
**The richer path:** use the genuine native objects (already present), differentiated for free by their native kind
(grain = `type-0x3f` kind `0x14`; telescope = kind `0x30`; etc.) and *move* them onto the custom floor with the
native-edit tooling we already have ([[type3f-delete-cc5]], [[pass1-scenery-edit]], [[green-gem-investigation]]).
Real look, real behavior, real counters — no new object engine. **First step:** debugger inventory — boot the
existing render disc and list which native objects still spawn and *where they land* relative to the custom floor.
**Decision to make:** keep the cave markers for purely-custom collectibles, OR go native-object-only, OR support both.

**Static inventory pass (2026-06-28, Codex):** added `tools/tier3_native_object_inventory.py`, which joins the
byte-pristine native `DAT/LEVEL01_LEVEL.DAT` type-`0x3f` table with the current `build/tier3_level.bin` T3LV floor.
Result for the current render-disc blob: native source inventory is still the full LEVEL01 set — **70 entries**
(50 grain, 4 FLIK letters, 4 berries, 9 seed tokens, 3 telescopes) — but **0/70 currently sit over a custom-floor
triangle**. Nearest native objects to the authored mesh are entry 57 purple berry `(245152,-12800,534144)` inside the
overall mesh AABB but over a no-floor/gap region, entry 54 gold berry at ~54k XZ units from the mesh AABB, and grains
11–13 at ~60–65k. CSV artifact: `build/tier3_native_object_inventory.csv` (generated, not source). **Interpretation:**
native-object-only is viable architecturally but not automatic for the current sample level — the next real gameplay
step is to relocate existing native type-`0x3f` entries (start with one grain or seed token) onto the custom floor and
verify render + pickup/HUD. Cave markers should remain as prototype/self-contained fallback until that live relocation
test passes; then prefer native objects for differentiated collectibles/counters. **Runtime debugger inventory still
pending:** isolated DuckStation launch on this host repeatedly exited immediately after the helper's READY probe
(port `23471`/`23472`, config `/tmp/duckstation-abl-gap-t3-1*`; binary
`~/duckstation/build-release/bin/duckstation-qt` sha256
`2a4bd1655ec2f0c91f07aa089ed0b20d218ff157f110ec09ba3355507770a732`), so no live `0x800b0d18` contact-array
snapshot was captured in this pass.

**Live relocation spike (2026-06-28, Codex) — GAP-T3-1 v1 PASS:** using the detached `duckstation-qt -nogui`
process path, moved native grain entry `0` only (kind stayed `0x14`) to file coords `(6159,-8,15403)` =
runtime `(197088,-256,492896)` on the Tier-3 spawn platform. Temporary disc:
`build/gap_t3_1/ABL_tier3_native_grain0.cue` (`.bin` sha256
`4c80b50ff499b5a1ea283b37518e7a422d1bd1d97c3788f9b4d65d549080305a`). Same from-boot movie
`flik_to_level01_stall.mv.movie.json` (`4253` frames) reached scene 1 at player `(197091,-266,492897)`, `COPIED=1`.
Baseline `build/ABL_tier3_render.cue` ended with grain counter `0`; relocated-grain disc ended with native grain
counter `0x800a65a1 = 1`, and source entry 0 was consumed (`y=0x80000000` sentinel) while kind stayed native
`0x14`. See [[Experiment - Tier3 native grain relocation]]. **Decision:** native `type-0x3f` objects are the primary
path for differentiated Tier-3 collectibles/counters; cave pickup markers remain optional prototype/custom-only
fallback until removed from the sample format. Remaining seam: GAP-T3-6 still needs enemy/floor-following object
verification; this pass only proves native pickup proximity + counter behavior.

### GAP-T3-2 — Tokens / per-kind counters (powers up seed levels)
If we keep ANY cave-side collectibles, generalize the pickup record `[x,y,z,r]` → `[x,y,z,r,kind]` and `switch(kind)`
in both the render loop (`tier3_otrender.c`, per-kind tile/colour) and the collect loop (`tier3_walls.c`, per-kind
counter). Token count is the new behavior (operator: tokens power up the **seed** levels — distinct system,
[[seed-planting-system]]). Needs either a found native token-counter RAM address or a custom in-engine counter +
optional HUD (cf. the grain-total HUD cave, [[grain-hud-total-mod]]). **If we go native-object-only (GAP-T3-1), this
gap may dissolve** — native objects already carry their own kind + counters. Resolve GAP-T3-1 first.

**Live native-token spike (2026-06-28, Codex) — GAP-T3-2 PASS / dissolved into native path:** moved native seed-token
entry `63` only (kind stayed `0x29`, orange seed token) to file coords `(6159,-8,15403)` = runtime
`(197088,-256,492896)` on the Tier-3 spawn platform. Static check: over T3 floor tri `1`, floor Y `-266`, delta `+10`.
Temporary disc: `build/gap_t3_2/ABL_tier3_native_seed63.cue` (`.bin` sha256
`91b1db1a4dc43a7eefaf6fd6486567149b78fc34ba51751435192be19b583940`). Same from-boot movie
`flik_to_level01_stall.mv.movie.json` reached scene 1 at player `(197091,-266,492897)`, `COPIED=1`. Baseline
`build/ABL_tier3_render.cue` ended with orange seed counter `0x800a6598 = 0x11`; relocated-token disc ended with
orange seed counter `0x22`, blue/green still `0`, and entry 63 consumed (`y=0x80000000` sentinel) while kind stayed
native `0x29`. Existing RE says seed counters are packed as logical count `n` stored as `n*17`, so this is exactly
one native orange-token increment. See [[Experiment - Tier3 native seed token relocation]]. **Decision:** do NOT
generalize cave-side pickup records for normal tokens; use native `type-0x3f` seed tokens for per-kind counters. Keep
cave markers only for custom-only objects with no native equivalent.

### GAP-T3-3 — FLIK letters: are they a collectible SET? (RE task — operator wants this solved)
Unknown whether F/L/I/K are *collectible letter objects* in levels (collect all 4 → reward, a bitmask not a running
count) or purely the spinning **HUD glyph tiles** we've documented ([[flik-letters-are-glyphs]]). **First step:**
debugger pass on native LEVEL01 — look for letter-pickup objects + what they write on collection; check whether the
HUD "FLIK" word lights up per-letter as a collected-set indicator. Output decides whether this is an object class at
all. Do NOT design a letter mechanic until this is answered.

**Live native-FLIK spike (2026-06-28, Codex) — GAP-T3-3 PASS:** moved all four native FLIK letter entries onto the
Tier-3 spawn platform: entry `50` kind `0x10` (F) to `(6159,-8,15403)`, entry `51` kind `0x11` (L) to
`(6209,-8,15403)`, entry `52` kind `0x12` (I) to `(6259,-8,15403)`, and entry `53` kind `0x13` (K) to
`(6309,-8,15403)`. Temporary disc: `build/gap_t3_3/ABL_tier3_native_flik_all.cue` (`.bin` sha256
`ab3ae5e05a3f1a6c1587d6ed3490d05f3019c23b21c48b87a234ce46da948b04`). Same from-boot movie reached scene 1 at
player `(197091,-266,492897)`, `COPIED=1`. Baseline `build/ABL_tier3_render.cue` ended with FLIK bitmask
`0x800a65a2 = 0` and FLIK HUD pulse `0x800b0194 = 0`; relocated-FLIK disc ended with FLIK bitmask
`0x800a65a2 = 0x0f`, FLIK HUD pulse `0x800b0194 = 0x0440`, and all four entries consumed (`y=0x80000000`
sentinel) while kinds stayed native `0x10..0x13`. See [[Experiment - Tier3 native FLIK letter relocation]].
**Decision:** FLIK letters are real native `type-0x3f` collectible-set objects, not just HUD glyphs. Tier-3 should
use native entries 50-53 for real FLIK-letter set behavior; glyph/texture swaps are visual-only and separate.

### GAP-T3-4 — Enemies: relocate SPAWN only, no AI (operator-scoped) — ✅ RESOLVED for stationary enemies (2026-06-28)
Operator explicitly does **not** want native enemy AI cracked — only the ability to **move where they spawn**. That
is **already solved in the native-edit track**: chaser spawn AREAS are editable in `LEVEL.DAT`
([[enemy-chaser-spawn-areas]]); stationary enemy ANCHORS are editable ([[enemy-worm-is-popup-relocatable]]).

**RESOLVED (live, 2026-06-28) — stationary enemies are ANCHOR-PINNED (no gravity, no floor query), so they sit on
the custom floor wherever you place them; the GAP-T3-6 seam does NOT apply to them.** Evidence (isolated instance,
SCUS-94288):
1. *Mechanism (pristine disc + `worm.sav`):* worm struct = current pos `0x800a0c78` + two anchor copies
   `0x800a0c9c`/`0x800a0ca8` (X,Y,Z each). Wrote the anchor **60000 units UP into open air** (Y −81792→−141792, also
   +40000 X/Z) → worm jumped to the target and **held stable for 30 frames; it did NOT fall.** Position is fully
   data-driven from the anchor — no gravity, no floor query.
2. *In-context (Tier-3 render disc `build/ABL_tier3_render.cue`, cold-booted via the `flik_to_level01_stall` movie to
   ~4500 frames):* native object system is **alive in the custom level** (chaser slot `0x80095358`=(176947,−13073,
   472308) right by Flik; a native mushroom prop renders in-frame). Wrote the worm anchor to **(Flik.x+30000, Flik.y,
   Flik.z) = (227091, −266, 492897)** — i.e. onto the **custom spawn-slab floor (Y=−266)** — and it **held exactly for
   40 frames.** Frame captured (custom level renders: green slab / golden ramp / magenta gap / brown wall).

So for the operator's actual ask (move where stationary enemies spawn) Tier-3 is **GREEN**: set the anchor XYZ to a
point on the custom floor. Disc-permanent edit path = the native-edit tooling ([[enemy-worm-is-popup-relocatable]];
stationary records live in LEVEL.RAW chunk 31, compressed). **Remaining (lower priority):** CHASERS (bee/spider/
mosquito) home on Flik and overwrite their own position each frame, so they have no live-editable location — only the
spawn AREA record ([[enemy-chaser-spawn-areas]]); whether an aggroed chaser tracks Y to the custom floor is unverified
(its own AI, which the operator de-scoped). Method note: the cold-boot-to-edited-level recipe used here is now in the
DuckStation API Index ("Reach an EDITED-disc level from a COLD BOOT") + the debugger skill.

### GAP-T3-5 — TRUE level-replace (operator question: does our code REPLACE terrain in memory, or hide it?)
**Status (verified live 2026-06-28) — PARTIALLY DONE; corrects the earlier "validated but not baked" framing.** The
native **GROUND** geometry build is already **removed AND baked**: `fcn.80010000` → COPIED-gated stub @`0x8007F304`
(`mod/tier3_loader.asm`). Live-verified: COPIED=1 once LEVEL01's `TIER3.RND` loads, then the stub does `jr ra`
immediately → native DAT floor **not built**; Flik settles on the custom floor (Y=−266). The **turn-around crash is
fixed** (this build was the high-RAM flooder; the flood-over-render-code region `0x801d4000+` reads clean). So the
high-value half of "true replace" is DONE.

What I found probing the current shipped disc (`build/ABL_tier3_render.cue`, no pokes):
- **chunk-35 walls = still RAM-resident, but visually inert + tiny.** Buffer `0x8012c1d0` is **load-once** (zeroing it
  persists — no per-frame rebuild) and **read per-frame by `FUNC_800172DC`** (PCs `0x800173e0`/`0x8001782c`/
  `0x80017b50`). This **resolves the long-open "which fn submits chunk-35"** question: it's the chunk-35 *reader*, and
  live-neutering it (`jr ra` at entry) **KEEPS Flik** + no crash, so it is **NOT** the Flik-draw fn — the earlier
  "tension vs Flik-draw" is settled. It's only ~0x30 quads (~1.5 KB), already OT-render-suppressed, contributes nothing
  visible at the tested angle. Build-removing it = genuine but **tiny-ROI** (no crash, negligible RAM); its builder runs
  during level *load* (not catchable by a post-load watch).
- **The visible native CLUTTER is OBJECTS/decor, NOT terrain.** A clean fresh boot still shows a brown dirt mound +
  grass blades behind Flik. Decisive: with the chunk-35 buffer **zeroed AND `FUNC_800172DC` neutered**, that clutter was
  **unchanged** → it is not chunk-35. It's the native dynamic objects/decor (leaf/grass/mushroom) the GATEOFF
  OT-suppress misses — i.e. GAP-T3-1 / Track-B object territory (the deferred multi-session identity-level RE), NOT
  terrain-replace. And per the DECISION below we *keep* useful objects (grain/enemies), so the real goal there is
  *selective* decor suppression — genuinely hard.
- **Native COLLISION = neutralized per-frame, not removed** (the cave deepens sectors + zeros swept planes each frame).
  Fine for Flik; a large free-roam level may still want true collision removal.

**Net:** the high-value part of terrain-replace (ground build-removal + crash fix) is DONE/baked; the remainder is
either low-ROI (chunk-35 build-removal) or hard and partly in tension with keep-objects (selective decor suppression).
**Recommendation: GAP-T3-5 is effectively satisfied for the operator's goals — defer the remainder in favor of Phase 4
(authoring) unless strict "zero native bytes in RAM" purity is required.** It remains the **same lineage as the
(now-fixed) turn-around crash**. Evidence: session scratch `t35_*` probes; see "Phase 3c.2 …" + the 2026-06-27
crash-stable log below.

**DECISION (operator, 2026-06-28): replace the TERRAIN, not the LEVEL.** "Native terrain" ≠ "native level." The
target is: **replace** terrain geometry + collision (✅ goal + crash fix), **keep** the native object / camera / HUD /
controller substrate. Rationale: the operator wants real differentiated objects (grain/telescope/…) and to **relocate
enemy spawns WITHOUT cracking AI** (GAP-T3-4) — both REQUIRE the native object/enemy system to stay alive. Nuking the
whole native level forces hand-reimplementing every object class in the cave = the "rewrite the game" path the
operator rejected. So the precise boundary = neuter the geometry-**submit** functions ONLY (`fcn.80010000` ground +
chunk-35 walls), leave object spawn / camera / HUD / controller running. **Open risk:** the 3c history flagged native
terrain ↔ objects as somewhat ENTANGLED in the build path (see "3c — OT-filter cave built; native terrain/objects
proven ENTANGLED"), so a clean terrain nuke that keeps objects alive may need some native sector scaffolding
preserved — verify empirically when 3c.2 is baked (do objects survive the geometry-submit neuter?).

### GAP-T3-6 — The native-object ↔ custom-floor seam — ✅ RESOLVED with FLIK pin caveat (2026-06-29)
Cross-cutting concern behind GAP-T3-1/T3-4: would native objects (grain, enemies) need the **native floor/collision**
(which we deepen/suppress for Flik to −40000) to rest correctly over the custom Blender floor? **Empirical answer:
mostly no, with one important FLIK-letter caveat.** Grain collection, stationary enemies, and chasers do not need the
native floor; however authored FLIK letters can have their type-`0x3f` Y mutated by native runtime object state before
collection. Tier-3 now pins authored FLIK entries each gameplay frame until their native collected bit is set.
- (a) **Pickups** never query the floor — collection is proximity-to-Flik; GAP-T3-1 relocated a native grain onto the
  custom floor and it was collected (counter→1). **Caveat:** FLIK letters are also proximity collectibles, but their
  live entry Y drifted away from an authored elevated platform (`-321` → e.g. `-2362/-2828/-6305/-3093`) before
  collection. The exact native writer was not traced; the robust Tier-3 fix is per-frame FLIK slot pinning in
  `mod/caves/tier3_walls.c`, generated from `tools/build_tier3_render_disc.py`.
- (b) **Stationary enemies** are **anchor-pinned — no gravity, no floor query** (GAP-T3-4): a worm held exactly where
  placed on the custom floor (and even 60000 units up in open air).
- (c) **Aggroed chasers** (verified 2026-06-28, render disc): drove Flik with held-Up to **aggro** the live chaser
  (`0x80095358`; aggro gate `0x800a6538` 0→136→978) and walked the custom floor. The chaser **tracked Flik in XZ** and
  hovered at a **Flik-relative Y** (~−13073, i.e. ~12800 above grounded Flik) — its Y is **AI/Flik-relative, NOT
  floor-derived**; it **never sank toward the −40000 native floor** nor flew to the void. So even moving AI enemies are
  unaffected by the seam (they reference Flik, who is on the custom floor).

No native actor was found that derives Y from a per-frame floor/gravity query. **The seam is dissolved for tested
actors**, but authored FLIK letters need the data-pin bridge above so the native object path continues to render and
collect them at Blender coordinates. The only residual is a *hypothetical* gravity-driven ground actor, which has
**not been shown to exist** in LEVEL01.

**Suggested order (updated 2026-06-29):** ✅ GAP-T3-1 v1 (native pickup relocate+collect) DONE · ✅ GAP-T3-4
(stationary enemy spawn relocate onto custom floor) DONE · ✅ GAP-T3-6 (seam) resolved with FLIK pinning — grains/
stationary/aggroed-chasers are data/AI-driven; FLIK letters require per-frame authored-slot pinning · ✅ GAP-T3-5
(true-replace) high-value part DONE+baked (ground build-removed, crash fixed); remainder low-ROI/deferred · ✅ GAP-T3-3
(FLIK letters = real native type-0x3f collectible set, entries 50-53 → `0x0f` bitmask + HUD; Codex 2026-06-28, verified)
· ✅ GAP-T3-2 (per-kind counters dissolved into the native path — native seed token relocated, packed counter
`0x800a6598` +1 logical; Codex 2026-06-28, verified) → **the ENTIRE GAP-T3 object/replace series is now CLOSED**
(T3-1/2/3/4/5/6 all done). Next: **Phase 4 authoring** — design a real Blender level and INTEGRATE native-object
placement (grain/FLIK/token/telescope/enemy) into the same build (see "Phase 4 integration" note below). *Optional
later:* selective native-decor suppression (hard, Track-B/object RE).

### GAP-T3-7 — Level SIZE ceiling: a fixed global tri/vert budget does not scale to a real level (operator finding, 2026-07-04)
**Symptom:** operator building `mylevel.blend` hit `MAXV/MAXT` overrun repeatedly while doing completely normal
authoring — a degenerate collinear-vertex triangle (cross-product zero, `tri_normal()` divide-by-zero), then a UV-map
blob overrun (unused default Blender UV layers force a 12 B/tri UV table for the WHOLE mesh, `tier3_level_format.py`
`pack_blob`), then a Subdivide cuts-count misunderstanding (cuts=11 → a 49×49 grid, not 11×11, since Blender splits
each edge into cuts+1 segments), then a final 20-tri overrun from bloated 32-tri icosphere-style marker objects. All
four were fixed (see build log / chat 2026-07-04), and the level now builds — **but the operator then asked the
real question: they plan "hundreds more" small terrain planes across a bigger level, one per few seconds of Flik
walking. That does NOT fit, and no amount of authoring cleanup fixes it.**

**Root cause (architectural, not a bug):** Tier-3 today is a **single fixed-size resident blob** — the ENTIRE
level's geometry (verts+tris+walls+UVs+textures) loads into one small scratch-RAM window at once
(`BLOB_RAM=0x801F3D00 .. 0x801F8E00`, i.e. **20,736 B total, ~512 tris worth**), with **no streaming/paging/culling
by zone**. This is shared across the WHOLE level — terrain + every prop + every marker — for the entire play
session. "Hundreds of small planes" (even at 2 tris each) is 200-2000+ tris, several multiples over the ceiling,
regardless of how efficiently each individual plane is authored.

Even if the ceiling were raised again (Track D already did this once: 128v/256t → 384v/512t, 2026-06-28), the
2026-06-28 lag investigation (this same file, Track D section + "FRONTIER ANALYSIS") showed **fps falls
monotonically with on-screen tri count on real PS1 hardware** (30 fps @ 0 tris → 14 fps @ 308 tris, software
per-tri CPU clip). So a further-raised cap would still run badly at "hundreds of planes" scale — the ceiling isn't
arbitrary, it's tracking genuine PS1 CPU/GPU headroom.

**Three paths forward, increasing effort/scope:**
1. **Scope the level down to fit today's engine (no engine work).** Author ONE continuous coarse terrain mesh
   (~250-350 tris) sized to the WHOLE level footprint (grid resolution chosen by total area, not "one plane per
   encounter"), plus a handful of cheap (non-icosphere) markers/props. Matches Tier-3's actual design intent — a
   small hand-authored arena — not a sprawling multi-zone platformer.
2. **Raise `MAXV/MAXT/MAXW` again (Track D repeat).** Marginal: buys maybe 2x before the RAM window/lag ceiling
   bites again. Does not get anywhere near "hundreds of planes."
3. **Refactor for chunk streaming (real engine work).** Load/collide only the geometry near the player; swap
   per-zone blobs in/out as Flik crosses a boundary trigger — closer to how the native game itself streams
   regions, and to the SM64-hack-style end-goal in this doc's Vision. Needs: multiple per-zone blobs, a
   load/unload trigger system, and re-deriving the RAM budget PER CHUNK instead of once globally. This is the
   only path that scales to a genuinely large level, but it is a real refactor, not a cap bump.

**Recommended sequencing:** do (1) first to get a complete, playable small level end-to-end (spawn→grain→exit) —
already ~90% proven working. Decide on (3) only once the desired level size is concrete enough to size the
refactor. (2) alone is not worth doing in isolation given the lag ceiling.

**Status:** open design decision, not yet scheduled into a Track. Supersedes any assumption that Track D's cap
raise is sufficient for "big level" ambitions — it explicitly is not.

**VERIFIED + refined (2026-07-04, debunk pass against the code):** re-derived the exact numbers from
`tools/build_tier3_render_disc.py` + `mod/tier3_level_format.py` + `mod/caves/tier3_otrender.c`. The
core "single fixed blob, no streaming" claim is CONFIRMED, with these corrections/nuances:
- **Exact RAM window:** `BLOB_RAM = RENDER_RAM(0x801F0000) + RENDER_PAD(0x3D00) = 0x801F3D00`; hard assert
  ceiling `0x801F8E00` (per-frame projection scratch PVX). Blob budget = **0x5100 = 20,736 B**. Confirmed.
- **Byte costs:** vert 12 B, tri 28 B, wall 32 B, **per-tri UV +12 B applied to the WHOLE mesh** if ANY
  face is textured (`pack_blob`, `if any(u is not None …)`). MAXV=384 / MAXT=512 are NOT simultaneously
  reachable with walls+UVs — the 20,736 B window is the true binding limit, tighter than MAXT.
- **The last-built `mylevel` blob (one plane): 260 v / 383 tri / 17 wall = 19,056 B = 92 % of the window,
  75 % of MAXT.** Of that, **4,596 B (24 %) is a per-tri UV table that pays 12 B/tri for every planar face**
  — because the level has 2 textures, ALL 383 tris carry a UV entry. Untexture the planar faces (or an
  authoring pass that strips unused Blender UV layers) reclaims that 24 % for free.
- **Over-subdivision, not the engine, caused the immediate overrun.** A walkable "bumpy" plane reads fine at
  6×6–8×8 (72–128 tris); 383 tris for one plane is 3–4× over. Right-sizing + UV-strip drops one plane from
  ~19 KB to ~2–4 KB → today's window then holds a genuinely useful single continuous terrain, just not
  "hundreds of discrete encounters."
- **Culling ALREADY EXISTS** (FARZ distance cull + lateral screen-space cull + trivial-accept, `tier3_otrender.c`
  lines ~99-140). So the Track-D "fps falls with on-screen tri count" is about ON-SCREEN tris, and with
  culling `on-screen ≠ resident`. This is why **path (3) streaming genuinely works**: off-resident geometry
  isn't projected, off-screen resident geometry is culled — the render half of streaming is done; only RAM
  residence + a load/unload trigger + per-zone blobs are missing. The per-frame projection loop is O(resident
  verts) unconditional (`for i<nv … PVX[i]=…`), so streaming bounds CPU cost too.
- **New cheap lever (between paths 2 and 3): format densification.** verts/indices/normals all fit int16
  (indices <384, normals scaled to ±8000, coords may need int32) → a tri could be ~16 B vs 28 B and a vert
  ~6-8 B vs 12 B ≈ **~1.7× more geometry per KB**. Touches both caves' fixed-offset blob reads — moderate,
  bounded work; still does not reach "hundreds" alone but multiplies whatever the window holds.

**CPU→GTE RENDER REWORK ATTEMPTED (2026-07-04) — see [[Tier 3 - GTE Render Path]].** Moved the per-vertex
transform to the GTE (COP2), proven pixel-identical + cold-boots; also dropped the 4-plane software screen clip
for GPU hardware scissor (also pixel-identical). **Outcome: modest, not a step-change.** Measurement showed the
software TRANSFORM was never the bottleneck (~0.6% of the render hook); subdivision ~11%, screen-clip ~9%. The
per-triangle cost (~1,000-1,500 cyc/tri) is SPREAD across divides + depth-LUT + emit + near-clip + loop overhead
— no single silver bullet. Renderer caps ~several-hundred tris at 30fps. Reaching high density needs cumulative
per-stage optimisation (GTE projection + native otz + leaner emit ≈ 1.5-2×) OR a different architecture (native
GTE submitter / true-replace), not a transform swap. (Cycle numbers are approximate — stepOut methodology caveat
in the note.)

**PIVOT TAKEN (2026-07-05) → [[Tier 3 - Native Terrain Path]].** GAP-T3-7's "raise caps" answer is superseded:
author Blender terrain directly into the game's own GTE emitter `FUNC_80010000` (native density, ~810 polys@30fps).
M1 done (byte-exact payload codec `tools/native_mesh_codec.py`, 217/217 LEVEL01 payloads); M2 core done (authored
payload renders via the native emitter). Next: resize/relocation pipeline for arbitrary Blender topology.

### Phase 4 — integration: author geometry + native objects in ONE build — ✅ TOOLING DONE (2026-06-28)
The two halves were independently proven — (1) Blender-authored **GEOMETRY** → cold-boot disc (exporter + capstone),
and (2) native **OBJECT** population (GAP-T3-1/2/3/4) — and are now **unified into one pipeline**. A Blender empty
tagged with a native kind (by name `Grain`/`FlikF..K`/`Token`/`*Berry`/`Telescope`, or an `abl_kind` property) is
exported as a native `type-0x3f` placement and relocated onto the custom floor in the SAME disc build. **This is the
clean answer to the operator's original "how does the editor know this is a grain vs token vs FLIK letter":** the
empty's kind tag → a native record relocation (real model + handler + counter), distinct from the generic invisible
cave `Pickup` markers.

**What was built (all committed-pending in `tools/`):**
- `tools/tier3_native_objects.py` — NEW. `apply_placements(dat, placements)` relocates unused native entries of each
  kind onto runtime coords (file = round(rt/32)), **in-place / size-preserving**, with a per-kind budget guard +
  longest-prefix name→kind map (`Grain`→0x14, `FlikF..K`→0x10–13, `Token`/`SeedToken`→0x29, berries 0x21–24,
  `Telescope`→0x30). Also a standalone CLI.
- `tools/tier3_blender_export.py` — emits a `native_objects:[{kind,x,y,z}]` list (`native_kind_of()` reads
  `abl_kind` or the name prefix); kind-tagged empties no longer fall through to the `Pickup`/`Exit` branches.
- `tools/tier3_level_from_json.py` — writes a sidecar `build/tier3_native_objects.json` (or REMOVES a stale one when
  a level has no native objects).
- `tools/build_tier3_render_disc.py` — `[6n]` applies the sidecar to the staged `LEVEL.DAT` (gated to the
  `TIER3_KEEP_BLOB` Blender flow or an explicit `TIER3_NATIVE_OBJECTS` path; pristine DAT preserved for restore).
  It also generates `build/tier3_native_pin.h` for authored FLIK letters, because live runtime can mutate their Y
  before collection. The one-button `tools/tier3_build_level.sh` picks it up automatically (it already sets
  `TIER3_KEEP_BLOB`).

**Verified (2026-06-28):** unit-tested the apply + sidecar round-trip + over-budget guard; then a **full end-to-end
disc build** placed 3 grain + F/L/I/K + 1 seed token onto the sample level (`[6n]` fired, LEVEL.DAT 332824→332824,
sources restored). **Live boot of that integrated disc:** the FLIK letters **render in-world** (golden spinning
letters) and the placed objects collect — FLIK bitmask `0x800a65a2 = 0x0f`, seed counter `0x800a6598 = 0x22`, grain
counter climbed as Flik walked. Canonical bare `build/ABL_tier3_render.{bin,cue}` was rebuilt back to its pre-demo
hash (`868b8cb6…`) so the engine disc is unchanged. **AUTHORING GOTCHA found:** collection is proximity-based, so
objects within the catch radius of `Spawn` are grabbed on frame 1 (the demo's near-spawn letters auto-collected →
`0x0f` at level entry); keep collectibles a bit away from spawn. Docs: `tools/TIER3_AUTHORING.md` (native-object
convention + budgets + gotcha).

**Correction / hardening (2026-06-29):** a later manual Blender level placed FLIK letters on an elevated platform;
DuckStation showed entries 50-53 loaded correctly but their live Y drifted away from the platform before collection.
The integrated build now compiles generated FLIK pinning into `mod/caves/tier3_walls.c`: uncollected authored FLIK
slots are rewritten to their authored file coords every gameplay frame; once collected, the native bitmask stops the
pin and the consumed sentinel persists. The loaded cave layout moved to `FLOOR_FN=0x801F0900`, `RENDER_C=0x801F0C00`
with segment-budget assertions.

**Forward path now:** design a real Blender level and place kind-tagged empties → one-button
`tools/tier3_build_level.sh LEVEL.blend` → a fully-populated, playable, cold-boot custom level. Remaining future
items are unchanged: per-kind counters already work via native objects; optional selective native-decor suppression
(hard, Track-B/object RE); enemy placement uses the anchor/spawn-area edits (GAP-T3-4) rather than `type-0x3f`.

#### Phase 4b — EXACT OBJECT COUNT-CONTROL ✅ DONE + live-verified (2026-06-28)
Operator wanted to set the EXACT number of grains (45/31/… not the native 50) and add/remove freely. Built
`apply_objects_exact()` in `tools/tier3_native_objects.py`: per authored kind, **relocate** the matches + **delete**
the surplus (delete-safe kinds: grain `0x14`, berries `0x21-24`, seed tokens `0x29-2B`) + **append** net-new (cloned
from a native template so model/flags survive). FLIK letters (`0x10-13`) + telescope (`0x30`) are relocate-only
(delete-unsafe). Uses the proven relocation-aware delete/append (`tools/delete_type3f_entries.py` /
`insert_type3f_entries.py` / `dat_reloc.py`). Net-new capped at ~62 records (DAT must stay ≤163 sectors or it
overruns `LEVEL.RAW` @LBA3069 — build errors with a clear message). Un-authored native kinds are LEFT native +
warned (a future `exhaustive` mode would delete them). The disc build's `[6n]` step now computes the
count-controlled DAT early (size changes — delete shrinks/append grows) and the sector budget uses it; pristine DAT
preserved for restore. **Verified:** unit (45→45, 31→31, 30→30, 60→60 with cloned-flag appends, 250→cap-error);
full build (collectathon authors 8 grain → relocate 13, **delete 42**, DAT 332824→332152, ≤163 sectors); **live
boot** of the count-controlled disc cold-boots clean (Flik@spawn, COPIED=1 — relocation-aware delete didn't corrupt
the DAT) with the in-RAM type-0x3f table reading **28 total / 8 grain** exactly. **REMAINING (Phase 4c):** the HUD
"x/N" total + all-grain **emblem** still read the hardcoded 50, so they don't fire at the real count — wiring in the
dynamic cave `mod/caves/grain_emblem.c` is blocked on an EXE cave-space COLLISION (the grain cave + the Tier-3
collision cave both want `0x800810C0`); needs a free boot-safe EXE region. Level stays completable via the exit.

#### Phase 4c — original-texture fidelity investigation + Track-D budget raise (2026-06-28)
Operator goal: make custom floors look like the **original ground**, "locked to the terrain, not deforming."
Investigated thoroughly (3 explore agents + live POC) and reached an honest verdict.

**What works (kept):**
- **`abl_uv` material texel-rect** (`tools/tier3_blender_export.py::uv_rect_of_material`): a material can target a
  SPECIFIC sub-region `[u0,v0,w,h]` of its texture page, so a surface uses the exact native tile (e.g. the LEVEL01
  pebble ground). Lets you author with real textures, not just colour tints. Atlas reference:
  `captures/tier3_textures/atlas_0660_LABELED_uv32.png` (the LEVEL01 ground page `0x0660`; pebbles top-right/
  bottom-left, grass top-left w/ green clut `0x3ffb`, wood/bark bottom, rock bottom-right; tan clut `0x3ffc`).
- **The real spawn-ground tile** = page `0x0660`, clut `0x3ffc`, UV the bottom-left pebble patch `[0,192,63,63]`
  (found via multi-pick on the pristine disc). The renderer default `0x068d/0x3470` is a *different* (grass/dirt)
  native tile — not the pebble ground.
- **Track-D BUDGET RAISE (DONE + live-verified, stable):** `MAXV 128->256`, `MAXT 256->512`, `NODE_MAX 256->512`
  in `mod/caves/tier3_otrender.c` (PV buffers re-spaced to 0x400; NODEBUF 0x801F9400..0x801FD400); the shared
  gameplay scratch (`PREV-XYZ`/`PICKUP_MASK`/`EXIT_DONE`/`HEAD_DONE`) RELOCATED `0x801FB0xx`->`0x801FE0xx` across
  `tier3_otrender.c`/`tier3_walls.c`/`tier3_collision.c`/`tier3_level.h`; mirrored in `mod/tier3_level_format.py`.
  Verified: cold-boots, Flik spawns (COPIED=1), 200-frame roam no crash. ~2x geometry headroom.

**The honest ceiling (why "very close to native" was NOT reached):**
- The deformation is **PS1 affine texture warping** — the GPU interpolates UVs linearly in screen space IN
  HARDWARE (no perspective correction). Confirmed **PGXP cannot help** (it needs GTE-transformed vertices; our
  renderer does software projection and bypasses the GTE — and PGXP is emulator-only). So the ONLY lever is fine
  geometry, like the native ground (GTE + far finer subdivision + distance LOD).
- POC at the raised budget (15×15 pebble floor) is **stable and modestly better but still blocky/warped at grazing
  angles** vs the native terrain (captured side-by-side: `captures/tier3_textures/pebble_N15_roam_native_vs_custom.png`,
  `compare_N10_vs_N15.png`). Reaching native would need the FULL investment: much higher budget + frustum/distance
  CULLING + distance LOD + a GTE/perspective render path + Gouraud shading — weeks-class, hard PS1 ceiling.

**DECISION (operator, 2026-06-28): ACCEPT the stylized look.** Custom floors use correct native textures and are
playable, but look "custom," not native-smooth — the normal SM64-romhack reality. Kept the budget raise + `abl_uv`
feature; deferred culling/LOD/GTE/Gouraud. Full plan on file: `~/.claude/plans/delightful-kindling-stream.md`.

#### Phase 4d — REAL framerate lag found + distance-cull fix (2026-06-28)
**CORRECTION:** an earlier pass concluded "no perf lag" — that was WRONG (measured a non-grazing spot + used an
invalid proxy: uncapped host-time can't see PS1 logic frame-skip). Operator provided `lagging.sav` showing **Game: 20
FPS / Video: 60 FPS** at a grazing view on the landing. Re-measured correctly via the game's double-buffer
present-rate (count `gpu.getStatus` crtc.vram_source_rect toggles per N vsyncs = true game-fps):
- **At the laggy state: 20 fps.** Un-hooking our custom render (restore DrawOTag `0x80064618`) → **30 fps**, so the
  native baseline here is ~30 fps (the hidden level's own load) and **our textured floor drops it 30→20**.
- It's **GPU textured-FILL**, not prim count (only 426 prims, 141 ours) and not CPU: view-dependent (less floor in
  view → faster), and culling the floor recovered fps. The receding far floor fills a big textured band at grazing
  angles (PVZ of the floor verts here = 38765..93467).
- **FIX — distance culling** (`mod/caves/tier3_otrender.c`): drop tris whose 3 verts are all beyond `FARZ` (or all
  behind NEARZ), cheap view-Z test before clip+draw. `FARZ=60000` keeps the near floor, culls the far → **20→30 fps**
  (full recovery to the native baseline) at the laggy state, near floor intact. Trade-off: a far draw-distance
  cutoff (floor fades to sky at the horizon; tunable via FARZ, could add fog). Verified by live re-inject of the
  recompiled cave (fps changed 20→30 and varied with FARZ, so the I-cache flush took) — **recommend a cold-boot
  playtest to confirm in real-time.** Captures: `captures/tier3_textures/lag_before_20fps.png` /
  `lag_after_cull_30fps.png`. The remaining ~30 fps is the native baseline (true-replace territory, or ABL's own rate).

#### Phase 4e — CORRECTION: the lag is CPU-bound (software clip), NOT GPU fill (2026-06-28)
Operator's `before_lag.sav` + a short Right tap deterministically reproduces a **sustained 20 fps** at a near-grazing
corner on the landing — **on the cull build f890683a** (so the FARZ cull does NOT fix it). Diagnosed:
- The floor there is **entirely NEAR** (all vert PVZ < FARZ 60000) → the distance-cull is **inapplicable** (nothing
  to cull). Confirms the FARZ cull is far-grazing-only.
- **It's our render** (render-off → 30 fps; on → 20) with only **182 prims** — far below native's 708 at 30 fps.
- **DECISIVE TEST (re-inject finer blob, same floor shape → no collision desync):** NF=4 (148 tris) = 20 fps;
  **NF=6 (308 tris) = 14 fps**; render-off (0 tris) = 30 fps. **fps falls monotonically with TRIANGLE COUNT.**
- ⇒ **The bottleneck is the software renderer's per-triangle projection + Sutherland-Hodgman clip** (R3000 integer
  divides), NOT GPU textured fill. Codex's "GPU fill" label is **wrong**; my counter-argument #2 (CPU clip) holds.
  The earlier FARZ cull "worked" by reducing TRIANGLES-CLIPPED (CPU), not fill.

**Consequence — warp and lag are in DIRECT TENSION:** reducing affine warp means MORE triangles (subdivision), which
costs MORE CPU clip → MORE lag. So "finer subdivision" is the WRONG fix (verified: it made it worse). The levers:
1. **CULLING before the clip** (frustum/near/back-face, not just far) — fewer tris reach the expensive clip → recovers
   fps without changing geometry. Near-term mitigation; helps any view.
2. **A cheaper clipper** (reduce divides / early-out) — modest.
3. **GTE/COP2 hardware render path** — offload projection to the GTE coprocessor (near-free per-tri) → many tris with
   no CPU lag. This is the REAL fix that resolves warp AND fps together; large rearchitecture (deferred).
4. **Keep tri counts modest** (the current NF=4 balance) — accept some warp, stay ~30 fps.
Practical authoring rule for now: **lag scales with on-screen triangle count**, so keep levels within a triangle
budget; culling stretches it; the GTE path is needed for genuinely dense/fine geometry without slowdown.

#### Phase 4f — CULL-BEFORE-CLIP + TRIVIAL-ACCEPT (near-term lag fix, VERIFIED 2026-06-28)
The chosen near-term lever (not subdivision, not GTE): reduce how many tris reach the expensive software
projection/clip path, in `mod/caves/tier3_otrender.c` per-triangle loop. Two output-identical additions, both
gated on "all 3 verts in front of the near plane":
- **Lateral frustum cull (no divide):** drop a tri whose 3 verts are all off one screen edge, via a
  cross-multiplied test `H*v {<,>} (bound-OF)*vz` (no divide). Complements the existing near/far cull.
- **Trivial-accept fast path:** project the 3 corners; if all land on-screen, emit the tri DIRECTLY and skip
  BOTH the near-plane clip and the 4-plane Sutherland-Hodgman screen clip (the divide-heavy path). An in-front,
  on-screen tri is unchanged by either clip, so the output is byte-identical — it just avoids the work. This is
  the big win at grazing/near views where every floor tri is visible and was paying the full clipper for nothing.
Only tris straddling the near plane or a screen edge fall through to the full clipper.

**VERIFICATION (rigorous A/B, identical save state + inputs, only the cave code differs):** `before_lag.sav`
(Flik fixed at 280547,-10266,472105) → short Right tap → camera pans to the grazing angle → measure. The lag
is a PANNED-CAMERA condition (load-time camera = 30 fps; the tap pans to the grazing angle = 20 fps from +90f);
teleport/fresh-boot does NOT reproduce it (camera settles to a non-grazing follow angle = 30 fps on BOTH caves),
so the save state is the only faithful repro. Because a save freezes the loaded cave + the pad bump moved the
blob base, tested by SURGICALLY swapping the new code in: compiled the new `tier3_otrender.o` for the save's blob
base (0x801F2000), relocated it into the free 16 KB above the blob (0x801F4000), and repointed the loader STUB's
`jal RENDER_C` (0x8007F1F4: 0x0C07C2C0→0x0C07D000). Result:
- OLD cave: **20 fps** (from +90f) · NEW cave at the SAME state/inputs: **30 fps** throughout. Hook firing
  (SENT +1/frame), Flik identical, floor renders correctly (no geometry dropped — capture `swap_worst.png`).
Build cost: render image 8128→8880 B, so `RENDER_PAD` bumped 0x2000→0x2800 (blob→0x801F2800, still far below
scratch 0x801F8000); fresh-boot of the rebuilt disc (`ABL_tier3_render` sha ee5e0861) renders the level
correctly. **Authoring rule unchanged** (lag still scales with on-screen tri count) but the budget is now larger:
the cull/accept stretches how many tris stay at 30 fps. GTE path remains the only fix that removes the per-tri
cost entirely (deferred). Capture set: `newcave_corner_settled.png`, `swap_worst.png` (captures/, gitignored).

#### Phase 4g — REGRESSION PASS: cull/trivial-accept never drops valid geometry (2026-06-28, NEW BASELINE)
This optimized renderer is now the **baseline**. Regression goal: prove the lateral cull + trivial-accept never
drop valid geometry across camera-edge / near-plane / grazing / all-pan-direction views (NF=4, no subdivision).
- **Oracle = our EMITTED triangles, not pixels.** Pixel diffs are hopelessly confounded by Flik idle-anim, native
  props, and slow camera creep. Instead, compare the renderer's own output: the OT NODE BUFFER (0x801F9400),
  parsed into the active triangle list (the GP0 xy/uv/colour payload of each node, in emission order). OLD code
  (pre-cull, disc 0x801F0B00) vs NEW code (relocated to 0x801F4000, STUB `jal` toggled) at the SAME frozen pose.
- **Camera-creep trap (cost real time):** ABL's follow camera settles ASYMPTOTICALLY — after a pan it creeps
  <0.5px/frame for HUNDREDS of frames. A 2-frame "static" check passes while a 4-frame gap accumulates a 1px shift,
  which flips edge-vertex projections by ±1 and reads as a false geometry diff. FIX: settle **400 frames** and gate
  on the OLD output being **frozen across 4 consecutive reads** before comparing. (150f was NOT enough for pans.)
- **Stale-tail trap:** hashing the whole fixed-size node region flags leftover bytes from earlier higher-tri frames.
  Compare only ACTIVE nodes (nonzero payload), in order.
- **Bug found + fixed:** the lateral cull used an EXACT cross-multiply (`H*v > (bound-OF)*z`) but projection FLOORS
  via integer divide, so a vert just past the edge in exact math still projects ONTO the edge pixel → the strict
  cull dropped 1px-visible border slivers (11/21/75 tris at edge-heavy pan poses). FIX = `CULLM=2` px screen-space
  margin: a culled tri now has every vert >CULLM px beyond the edge (absorbs the ±1px floor/truncate error on both
  signs), so by convex hull it covers no on-screen pixel. Tris within CULLM px fall to the full clipper.
- **RESULT (12 poses, strict frozen gate): ALL CLEAN** — NEW emits byte-identical triangles to OLD everywhere
  (dropped=0, added=0). fps still 30 at the before_lag grazing-pan with the margin (margin cost is negligible —
  only a few edge tris reroute to the full clip). Final disc `ABL_tier3_render` sha **20c75b06** cold-boots +
  renders correctly. Harness: scratchpad `regress6.py` (node-list + frozen gate), `creepcheck.py` (creep proof).

**AUTHORING RULE (current engine baseline):** mesh-triangle editing IS viable for custom levels, BUT (1) the
on-screen **triangle count must be budgeted** — lag scales with it (software per-tri projection/clip on the R3000;
see Phase 4e/4f), and (2) the **optimized pre-clip culling path (lateral cull + trivial-accept + CULLM margin) is
MANDATORY** — it is the baseline renderer; do not regress to the always-full-clip path. Keep NF=4; do not add
auto-subdivision (it raises tri count → more lag, Phase 4d). The GTE render path is the only way to lift the budget
without the per-tri CPU cost (deferred).

#### Phase 4h — SECOND lag mode found: GPU TEXTURE-CACHE THRASH at grazing angles (2026-06-28)
`lag_v3.sav` (operator) exposes a residual lag the cull does NOT fix. Repro: load → very short LEFT tap → the
camera SLOW-DRIFTS (~4 s, the multi-hundred-frame creep) into a grazing angle → **sustained 20 fps** with Flik
STATIC and our prim count CONSTANT at 151. So it is NOT more geometry and NOT Flik moving — it is the per-frame
render cost rising as the camera reaches a grazing angle. Isolation ladder (all at the lag pose, via STUB-`jal`
redirect to relocated test caves on the save, blob@0x801F2800):
- **It's our render:** render ON = 20 · un-hooked (native only) = 30 · back ON = 20.
- **NOT the CPU clip:** a cave that does ALL projection/clip but emits ZERO nodes = **30** (clip is cheap here).
- **NOT raw pixel coverage / fill area:** a cave with the SAME textured tris but **constant UV** (every pixel
  samples ONE texel → cache-resident) = **30**, vs varied-UV textured = 20. Same triangles, same coverage, same
  pixel count — only texel-sampling locality differs. (The flat-shade `TEXTURED 0` test was INVALID — drew a near-
  blank frame, the known 5-word-node fragility; use the const-UV test instead, which keeps the valid 8-word format.)
⇒ **ROOT CAUSE = PS1 TEXTURE-CACHE THRASH.** Large affine-warped floor triangles at grazing angles sample a wide
texel swath with poor locality, blowing the PS1's ~2 KB texture cache → many misses → slow textured fill. The
native game avoids it with MANY SMALL textured tris (good locality) + GTE; our FEW BIG tris (NF=4) thrash. Captures:
`lagv3_worst.png` (textured 20 fps, note the far grazing slivers top-left), `lagv3_constuv.png` (same floor solid-
colour, 30 fps). The ground tile is already 4bpp (page 0x0660); a 64×64 4bpp tile is ~2 KB so it only just fits and
the grazing sampling pattern still thrashes within it.

**UPDATED PERFORMANCE MODEL — there are TWO distinct lag modes, pose-dependent:**
1. **CPU per-triangle clip** — scales with on-screen tri COUNT (before_lag case). Fixed by cull-before-clip +
   trivial-accept (Phase 4f). Subdivision makes this WORSE.
2. **GPU texture-cache thrash** — scales with per-tri texel-footprint = big affine tris at grazing (lag_v3 case).
   The cull can't touch it (same tris drawn). Subdivision would HELP this (smaller texel footprint per tri) — i.e.
   the two modes pull subdivision in OPPOSITE directions, so there is no global win without the GTE path.
Candidate fixes for mode 2 (tradeoffs, NOT yet chosen/implemented): (a) **selective const-UV / texture-LOD** —
collapse UV to a constant (cache-resident, proven 30 fps + valid render) for FAR/large-on-screen tris only, keeping
near-floor textured; cheap, keeps NF=4, no CPU cost, far floor becomes solid-colour (the far floor is streaky mess
anyway). (b) smaller/cache-resident ground tile. (c) flat-shade far (needs the fragile 5-word path fixed). (d) GTE
path. Recommend (a) as the next experiment if pursuing it.

#### Phase 4i — VERIFICATION PASS: selective const-UV / texture-LOD FAILS (2026-06-28)
Prototyped fix (a) on `lag_v3.sav` (relocated test caves @0x801F5000, STUB-`jal` toggle). **NEGATIVE result — the
selective approach does not work.** Swept many criteria; all stayed at **20 fps** except full-solid:
- **Depth-LOD** (collapse tris whose nearest corner > LOD_Z; LOD_Z 6000/12000/20000/30000): all **20 fps**. ⇒ the
  thrashers are NOT the far slivers — they are the **big NEAR floor tris** (large on-screen).
- **UV-mask to a tiny cache-resident tile** (mask &31 / &15 / **&7** = 8×8 texels = 64 B, trivially cache-resident):
  all **20 fps**. ⇒ it is NOT the texel working-set / cache size.
- **Span-collapse** (const-UV only tris with UV-span > 16): **20 fps** too.
- **Full const-UV everywhere** (zero UV gradient, whole floor solid): **30 fps** (the only thing that works).
KEY DISTINCTION: const-UV (all 3 corners EQUAL → zero gradient) = 30; `mask7` (corners differ within 0–7, tiny but
NONZERO gradient) = 20. So the cost is triggered by ANY nonzero UV gradient, not the texel range. And it is the
**hardware renderer** (instance + operator both default `Renderer=Automatic`; no `[GPU]` override), so NOT a host
software-renderer artifact — it is DuckStation's modeled **PS1 GPU fill timing** (real, renderer-independent). It
distributes across the whole textured floor (collapsing any subset leaves enough textured fill to stay at 20), so
ONLY a fully-solid floor recovers fps. ⇒ **There is no selective-const-UV subset that recovers fps while keeping
texture.** Fix (a) is dead.

REFRAMED root cause + real fixes: native draws the SAME camera at 30 fps with its floor (un-hook test) using MANY
SMALL textured tris; our FEW BIG textured tris (NF=4) blow the PS1 GPU fill-timing budget. So the genuine lever for
mode 2 is **SMALLER TRIANGLES (subdivision)** — the native approach — which ALSO fixes the affine warp, at a CPU-clip
cost (but mode-2 poses have CPU headroom: zero-emit = 30). This DIRECTLY CONFLICTS with the no-subdivision rule that
mode 1 (CPU-clip-bound) requires. Net: **no single static knob wins both modes** — subdivision helps fill/warp but
hurts clip; the cull helps clip but not fill. The only clean win for both is the **GTE render path** (hardware
projection → cheap small tris like native). Practical near-term options: accept ~20 fps at extreme grazing angles as
a known transient limit (only after the camera settles into a grazing pose); OR make NF a per-level knob (raise it
for open/grazing levels that are fill-bound, keep low for dense/CPU-bound ones); OR pursue the GTE path. Captures:
`lod_*.png`, `mask*.png`, `spancoll16.png` (all 20 fps, scratchpad).

**PRISTINE COMPARISON (does retail lag here too? NO):** booted the untouched retail disc `Disney-Pixar A Bug's
Life (v1.0).cue` and measured LEVEL01 directly — **solid 30 fps everywhere**: walking, turning, grazing the camera
in all directions, and the exact tap-then-settle pattern that drops OUR floor to 20 (no dips; the lone "10" was the
post-movie-boot transient, confirmed 30 after a 90f settle). So this lag is NOT authentic retail behaviour and NOT a
general PS1/engine limit — it is specifically our custom big-triangle textured floor exceeding the PS1 GPU
fill-timing budget that retail stays under via many small tris. CONCLUSION: treat as a documented, bounded, transient
known limitation of the current Tier-3 software renderer (grazing-angle only, custom levels only; not a correctness
bug). Real fix = GTE render path (small tris like native, also fixes warp); per-level NF is a partial lever that
trades against mode 1. Decision: accept + move on; revisit with the GTE path when pushing level density/fidelity.

#### Phase 4j — DRAW-DISTANCE FIX: `FARZ` 60000 -> 200000 (2026-06-30) — supersedes the 4d/4i `FARZ=60000` value
Operator bug "draw distance is poor / loads a few feet in front of Flik." The limiter was the **far distance cull**
`FARZ` (Phase 4d): a tri whose 3 verts are all beyond view-space-Z `FARZ` is dropped before clip+draw. Diagnosed live
on `draw_ditance_poorv2.sav` (NOTE: read the camera `C@0x1F800374` *at the render hook* via a breakpoint at
`0x8007F174` — a paused read of that scratchpad returns a stale/reused value): at the operator's pose `FARZ=60000`
culled **39 of 180 tris**, all on-screen in a thin horizon band, so the far ground/collectibles only appeared as Flik
walked toward them. **Raised `FARZ` to 200000** (`mod/caves/tier3_otrender.c`) — the authored level maxes at view-Z
~96000 so the whole level now always renders; the cull remains only as a far-horizon / `NODE_MAX` runaway guard.
**This is SAFE and does not reopen the 4d/4h/4i lag** because: (1) mode-2 grazing thrash is from the **big NEAR tris**,
not the far slivers the cull removed (Phase 4i finding); (2) mode-1 CPU clip is absorbed by the cull-before-clip +
trivial-accept path (Phase 4f); far tris in a normal follow view are small + fully on-screen -> trivial-accept ->
cheap. **Verified:** same-pose live A/B (horizon-band sky pixels 18713->8067 = far ground filled in, ~30 fps
unchanged) AND a full **cold-boot** of the rebuilt disc — 30 fps at spawn, walking, and a grazing-angle camera pan,
no wedge / no holes, jump stable. The `FARZ=60000` figure in Phase 4d/4e/4h/4i is now historical; the live value is
200000. (A 0-fps blip seen while LIVE-INJECTING the new render onto the old `lag_v3.sav` was an **I-cache artifact**
of the 6 KB code overwrite — identical emitted node count before/after proved FARZ wasn't the cause; cold-boot is
clean.) CAVEAT: a future very-large/dense level at a grazing angle could re-expose mode-2 fill at a larger radius —
then tune `FARZ` per-level or pursue the GTE path. See the fix entry in [[Tier 3 - Custom Level Bugs]] for full addresses/captures.

#### Phase 4k — OBJECT-VISIBILITY FIX: `suppress_terrain` was collapsing authored object prims (2026-06-30)
Operator bug "grains flicker on the left / F,L,I barely visible" (`draw_ditance_poorv3.sav`). The scene-pass
`suppress_terrain` (which hides the RAM-resident native LEVEL01 terrain every frame — it's built once at load and
the `fcn.80010000` stub only blocks a *rebuild*) was too broad: its **cmd-`0x2e`/`0x3e`** rule killed the FLIK
letters (native semi-transparent `0x2e` polys) and its **`offset > GATEOFF`** rule clipped the grains (native flat
`0x2c` quads) — and the grains' OT offset drifting across the gate in real time caused the **flicker** (real-time
only; deterministic frame-step shows them steady). Live OT walk + `gpu.pickObject` at the v3 pose established the
discriminator: native terrain = **GOURAUD-textured polys** (`0x3c`/`0x34`) + **sprites** (`0x65`); authored objects =
**FLAT polys** (grain `0x2c`, FLIK `0x2e`). Rewrote `suppress_terrain` to drop only `is_terrain_cmd()` (gouraud
poly `0x34-37`/`0x3c-3f` OR sprite/rect `0x60-7f`) at high offset and **spare flat object polys** — so `0x2c`/`0x2e`
are never collapsed at any offset (flicker gone by construction) and the letters survive. Offset gate kept (Flik the
character is gouraud too but built LOW). Verified by same-pose inject A/B (letters + grain render, terrain stays
hidden; fully disabling suppress floods native terrain back = suppress still required) and cold-boot (objects stable
across 8 frames, terrain hidden, draw distance intact). RESIDUAL (pre-existing, not from this change): LOW-offset
gouraud terrain still leaks at some angles — deferred Track-B work. Full detail in [[Tier 3 - Custom Level Bugs]].

#### Phase 4l — OBJECT OCCLUSION: hide authored objects buried below the custom floor (2026-06-30)
Operator bug "FLIK letters visible even underneath the ground" (`visible_through_ground.sav`). Because our ground is
a BACKDROP (background OT pass), the native scene objects always draw over it, so a below-floor letter is never hidden.
True occlusion on PS1 (no Z-buffer) needs our geometry **depth-sorted into the native scene OT** — the OT is a clean
1228-bucket array (`OTBASE=0x801e1500`, head=far end) BUT the native GTE→`otz` depth scale vs our software `PVZ` is
noisy/nonlinear (mis-sort corrupts the DMA chain), so depth-insertion is DEFERRED. Instead added **floor-driven
occlusion** in `mod/caves/tier3_otrender.c`: the scene pass reads each authored `type-0x3f` object, queries our floor
(`FLOOR_FN`/`tier3_floor_y`, topmost-surface via a very-high ref Y), and if it's buried (`ry>floorY+OCC_MARGIN`) with
the camera above the floor, builds a projected screen box; `suppress_terrain` collapses the object's flat/sprite render
prims inside any box (Flik is gouraud → spared). `RENDER_PAD` bumped `0x2800→0x2C00` for the code growth (blob→
`0x801F2C00`). Verified cold-boot ON vs `-DOCC_ON=0` baseline: buried letters hidden, resting grains + HUD kept.
GOTCHA: a RAM warp desyncs the follow camera (objects project "behind") — verify only via NORMAL (walked) gameplay.
LIMITATIONS: floor-height heuristic (grazing/edge buried objects can still peek); below-floor only (BEHIND-WALL
`visible_through_walls.sav` NOT handled — needs a wall raycast or the depth-sort); GTE/depth-sort remains the complete
fix (deferred). Full addresses/captures in [[Tier 3 - Custom Level Bugs]].

#### Phase 4m — PERF: amortize the occlusion floor query (fix the rotation lag) (2026-06-30)
Phase 4l's occlusion ran `tier3_floor_y` (an O(ntris) triangle scan) for EVERY on-screen `type-0x3f` object EVERY
frame → a 30→14fps regression while Flik rotates (repro `lag_walkingaround.movie.json`). Isolated decisively: render
un-hook → 30fps; FARZ sweep with fresh reloads → flat 13fps at all FARZ (so NOT the far ground / draw-distance change);
**neuter `FLOOR_FN` → 30fps** (the floor queries are the cost). The buried status is camera-independent + static, so it
is AMORTIZED: floor-check ONE object/frame (round-robin `OCC_CURSOR`), cache the buried bit in `OCC_MASK` (96 bits,
cleared by the collision spawn one-shot), and each frame only PROJECT the cached-buried objects. Net ~1 floor query/
frame (like the collision cave). Verified: cold-boot via the lag movie → **30fps throughout the rotation**, occlusion
still correct. (Side finding: a `FAST_FLOOR` const-UV experiment moved only 14→15fps → this lag is the CPU floor query,
NOT the Phase 4h/4i texture-cache thrash; FAST_FLOOR removed.) Full detail in the "lag" entry of [[Tier 3 - Custom Level Bugs]].

#### Phase 4n — DEPTH-SORTED RENDERER: real per-pixel occlusion, retires the fake-occlusion hacks (2026-06-30)
The all-or-nothing fake occlusion (Phase 4l–4m + the box/nearest-object/wall-ray follow-ups) hid whole objects, so
they popped in/out instead of being *partly* covered. Operator wanted the real thing (object slightly in the ground /
behind a wall is only PARTIALLY covered, per-pixel, like real life). Since PS1 has no Z-buffer that needs our geometry
DEPTH-SORTED into the game's ordering table. A spike proved the mechanism (splice a tri at a chosen bucket → the PS1
composites it per-pixel, crash-free). Then converted `mod/caves/tier3_otrender.c`: the render moved from the BACKGROUND
(backdrop) pass to the **SCENE** pass and now **splices each floor/wall/marker tri into `ot[bucket]`** (bucket from the
tri's avg view-Z: `(PVZ_avg·DS_MUL>>16)+DS_BASE`, `otbase=head−(OT_SIZE−1)·4`) instead of appending a flat backdrop.
`DS_MUL=978` calibrated live (the analytic GTE→otz map was too noisy). **[SUPERSEDED by Phase 4o: DS_MUL=978 was
mis-calibrated — see below.]** This DELETED the entire object-occlusion block
(nearest-object / wall-ray / round-robin floor query, `OCC_*`, `FLOOR_FN`) + the backdrop tail; `suppress_terrain` is
terrain-only again. **Verified:** `occlusion_issue.sav` pan = items gradually covered by the platform (per-pixel, no
pop); `items_visible` = behind-wall grains partly occluded, in-front items visible, 30fps; `grain_invisible` = grain
visible; cold-boot spawn = floor to horizon + Flik on floor + HUD intact; `lag_walkingaround` = 29–30fps (per-tri
splice is O(1)). This is the render the deferred "GTE path" was pointing at — minus the GTE (a tuned software
`bucket=f(PVZ)` was enough for depth ORDER). Full detail in the occlusion entry of [[Tier 3 - Custom Level Bugs]].

#### Phase 4o — DEPTH-SORT CALIBRATION: measured the game's OT curve; fixed "Flik cut by floor" + occlusion oddity (2026-06-30)
Operator reported two symptoms on the 4n renderer: (a) the occlusion **changes with viewing distance** as you walk up the
ramp ("oddity" — correct from the platform, off from below), and (b) **Flik's model is sheared flat by the floor** again
(a regression). Both were the SAME root cause: the depth-bucket **calibration was wrong**. Measured it directly instead of
by eye — broke at the render entry `RENDER_C @0x801F0C00` (camera valid there, `$a0`=scene OT), read the live camera
(C@`0x1F800374`, R@`0x80090FB0`; screen projection reproduced the game's within **1px**), then **screen-matched OT primitive
nodes to known objects** to read the GAME'S OWN bucket for each:

| object | view-Z (PVZ) | game OT bucket |
|---|---|---|
| near grain | 15629 | 445 |
| **Flik** | 28787 | **653** |
| F letter | 62660 | 852 |
| telescope | 106229 | 950 |

TWO findings: **(1)** the game's depth→bucket curve is **COMPRESSIVE** (steep near, flat far — ~0.016 buckets/unit near
Flik, ~0.0025 far), NOT linear; **(2)** the old `DS_MUL=978, DS_BASE=0` put our floor at Flik's depth in bucket **429**
while the game places **Flik at 653** — our floor sorted **224 buckets too NEAR**, so it drew OVER Flik (the "cut by floor")
and over-occluded.

**FIRST FIX (linear, `DS_MUL=251/DS_BASE=546`) removed the cut-out but the oddity REMAINED** — operator saved two more poses
(`occlusion_oddity_v2_1` / `v2_2`) showing the same straddling FLIK letters occluded differently. Re-measured at BOTH poses
and they fall on the **SAME curve** (e.g. PVZ≈62.7k → bkt 852/853 in both; ≈75k → 890/893), PROVING the game's OT depth is a
consistent function of view-Z — so it IS solvable. The linear fit was still off by up to **−66 buckets in the mid region
(PVZ 50–63k = exactly where the letters sit)** but only −11 near / −27 far; that VARYING error is the view-dependence.

**REAL FIX (2026-06-30): a piecewise-linear LOOKUP TABLE of the measured curve** — `ds_depth_bucket(PVZ)` in
`mod/caves/tier3_otrender.c` interpolates the 8 measured `(PVZ, game bucket)` breakpoints
`{15629:445, 28787:653, 39550:738, 51308:806, 62686:852, 75375:890, 93056:929, 106187:950}` (extrapolated past the ends),
matching the game within **~2 buckets at every depth** → our floor's depth field now EQUALS the game's everywhere →
occlusion is **view-INDEPENDENT** (oddity solved), and our floor at any object's depth ties that object's own bucket (object
draws on top since we PREPEND → nothing cut; the floor's nearer lip still occludes the parts behind it, per-pixel). The old
linear path is kept as a live-override fallback (`0x801FE030` nonzero → linear `DS_MUL`/`DS_BASE`, for debug). **Cold-boot
verified:** game bucket 679 at PVZ 32343 == the LUT prediction 681 (diff 2); our floor buckets now span **335→721** (min 335
≪ the linear floor of 546 — confirms the steep near-curve is applied, i.e. the LUT is live, not linear); Flik renders fully;
no wedge.

**WEDGE REGRESSION (hit + fixed during this work — important gotcha):** adding `ds_depth_bucket` as a normal function made
gcc emit it FIRST in `tier3_otrender.o`, so it landed at the object's start `0x801F0C00`. The **cold-boot loader
`mod/tier3_loader.asm` hard-jals the render entry at the FIXED address `0x801F0C00`** (it's assembled in the EXE-patch
context, which has no access to the `.o` symbols), so it called `ds_depth_bucket(OT_head)` → garbage "head" → **GPU DMA
wedge (DrawSync spin @0x80064a70, whole game frozen)**. `SENT@0x801E00DC` is an UNRELIABLE liveness check here — it sits in
the game's OT buffer region and gets clobbered (read 0 even while the hook runs). FIX: mark `ds_depth_bucket`
`static inline __attribute__((always_inline))` so no standalone function is emitted and `tier3_otrender_hook` stays first at
`0x801F0C00`. (Also switched the LIVE-inject trampoline `mod/tier3_otrender_live.asm` to `jal tier3_otrender_hook` by SYMBOL
— robust to any future reordering — but the disc uses the loader's fixed address, so the always_inline is the load-bearing
fix.) **Lesson: the render entry function MUST be first in `tier3_otrender.o`; verify `0x801F0C00` disassembles to the hook
(`lui …,0x8009` R-matrix load), not a helper, after any change that adds a top-level function.**

## NEXT STEPS (forward plan, as of 2026-06-27)
Ordered, actionable. Details: [[Finding - Tier-3 render disc-delivery]] (session log) + auto-memory
`tier3-render-disc-coldboot-hang`. The cold-boot level boots/plays in all CPU modes; the open blocker is the
turn-to-face-native-level crash, whose fix is validated and is also the level-replace goal.

1. ✅ **DONE (2026-06-27) — native floor build removal = the crash fix.** Baked a COPIED-gated static hook at
   `fcn.80010000` → `tier3_neuter_80010000` (stub @0x8007F304) that skips the native DAT floor build once the
   LEVEL01 render has loaded; boot/other-scenes keep their floor. (Codex authored the stub — correct logic incl.
   the load-delay slot — but placed it at 0x8007F350, overwriting the `tier3.rnd` filename tail → loader couldn't
   load; fixed by moving the stub to the free gap 0x8007F304.) VERIFIED (Cached Interp): loader fires
   (COPIED=1/T3LV), turning to face the native level no longer corrupts the render code — **crash gone**, custom
   platforms render. Static hook (no self-mod → no FlushCache needed), gated to LEVEL01. `mod/tier3_loader.asm`,
   disc rebuilt. TODO: confirm in pure Interpreter (operator's mode) with the tap-Left/wait-5s repro.
   - **Bake update (2026-06-27):** implemented in `mod/tier3_loader.asm`: `0x80010000` now jumps to a compact
     stub at `0x8007F350`. The stub replays the displaced prologue and rejoins at `0x80010008` until `COPIED`
     (`0x8007F300`) is set by the LEVEL01 `TIER3.RND` loader; after that, it returns immediately. This avoids
     blanking boot/load-time calls and keeps the stub inside the zero-run tail (36 B). `tools/build_tier3_render_disc.py`
     rebuilt `build/ABL_tier3_render.{bin,cue}` successfully; resident RAM and BIN byte checks confirmed the hook/stub.
     **✅ LIVE COLD-BOOT VERIFIED (2026-06-27) — NO turn-around crash.** See the session log
     "2026-06-27 — cold-boot disc VERIFIED crash-stable" below. The `flik_to_level01_stall` replay
     (`movie.startPlayback{load_start_state:true}`) reaches LEVEL01 spawn `(197091,−266,492897)`, COPIED=1,
     custom render visible, then **1800 frames of heavy all-direction turning ran with NO crash** (frame counter
     advancing, EPC never in render code, no fault ExcCode). The prior "stopped on a black load-tail / COPIED=0"
     reading was a **stale/desynced test**; the freshly-rebuilt disc cold-boots straight to the playable+visible
     custom level. (Methodology fix: the apparent crashes were detection false-positives — see the session log.)
2. **Audit the other hand-written asm for the same MIPS load-delay hazard** (loader_stub already fixed):
   `tier3_tramp`/`tramp3` in `mod/patch_tier3_collision.asm`, `otr_tramp` in `mod/tier3_otrender_live.asm`.
   Any `lw`→immediate-branch-using-the-loaded-reg fails in Interpreter + real hardware. C caves are safe (gcc).
   - **Audit update (2026-06-27):** checked the named asm paths. `tier3_tramp` has no load/branch hazard.
     `tramp3` already has an independent `lui t1,0x4000` between `lw FLOOR_PUB` and the `beq`, so the loaded
     `t0` is not consumed in the load-delay slot. `otr_tramp` restores registers and jumps to fixed code; no
     immediate branch consumes a just-loaded register. The newer `tier3_loader.asm` paths are also spaced:
     `loader_stub` has a `nop` after `lw COPIED`, `tier3_load_render` uses independent `lui` fillers after its
     loads, and the baked `fcn.80010000` neuter uses the displaced `addiu sp,-32` between `lw COPIED` and `bne`.
     **No code changes required for this audit.**
3. ✅ **DONE (2026-06-27) — butt-slam crash retest: NO crash.** On the cold-boot disc, grounded jump (Cross)
   raises Flik Y −266→−8522 and settles back to −266; **butt-slam (mid-air Cross) descends −8330→−266 and lands
   with NO fault** (EPC not in render code, no fault ExcCode). The infinite-jump fix (f1b76b0) holds (the 2nd
   mid-air X no-ops/lands, doesn't re-jump). So step 3's hypothesised "same render-overwrite root" is moot — the
   render is crash-stable. See the 2026-06-27 session log below.
   - **(historical) Retest update (2026-06-27, superseded): blocked before gameplay on the current rebuilt image.** Corrected the
     DuckStation workflow against [[DuckStation API Index]] + [[API - movie]]: the existing
     `flik_to_level01_stall` movie is `from_boot`, so replay must use `movie.startPlayback{load_start_state:true}`
     (power-cycle anchor), and `pc<0x10000`/`ExcCode 8` during boot is normal BIOS syscall transit, not by itself
     a crash. Using the repo driver (`tools/trace_initial_spawn.py recon`) reaches LEVEL01 spawn
     `(X=197091,Y=2733,Z=492897, scene=1)` at movie frame ~4200, but the current rebuilt disc then stays on a
     black load-tail: no hits at `tier3_tramp`/`tier3_collision_hook`/`tier3_load_render`, `COPIED=0`,
     `0x801F0000`/`0x801F0C00` empty, DrawOTag hook still original, while CDROM continues reading around LBA
     186429. A/B restoring the original `0x80010000` prologue live after EXE load still reaches the same
     pre-gameplay black tail, so this is **not proven to be caused by the baked `fcn.80010000` neuter**. Next
     action: fix/restore the cold-boot-to-playable-gameplay path first, then run the actual butt-slam test.
4. **Full native-level removal for a clean view (cosmetic, not crash):** also neuter the walls (chunk-35 submit
   fn — pin which fn; not `fcn.80010000`) + native objects (mosquito/mushroom/grain). Leaves only the custom level.
   - **Investigation 2026-06-27 — walls/terrain ALREADY gone; native OBJECTS need identity-level RE (multi-session).**
     Mapped the residual draws with `gpu.pickObject` on the cold-boot disc (anchor reload). The GATEOFF OT-offset
     suppress already removes BOTH foreground and background terrain/walls (sky-only behind the custom level), so
     "neuter chunk-35" is effectively done by the existing OT-filter. The remaining residue = a few native dynamic
     **objects** (mosquito, leaf, mushroom). **Cleanly dropping them while keeping Flik+HUD is NOT a quick OT
     filter** — proven by exhausting every cheap discriminator:
     - **Prim content (texpage/CLUT/GP0-cmd) is animation-dependent → not stable.** Same screen pixel on the
       mosquito read GP0(3c)/tpage 0x204 one frame and GP0(2e)/tpage 0x22a/different CLUT the next. Flik and the
       mosquito BOTH use the model path (3c/2e, tpage 0x204); the leaf and the HUD BOTH use the sprite path
       (2d, tpage 0x60a) — so texpage/cmd/CLUT can't separate keep-vs-drop.
     - **OT-offset ordering doesn't separate them either.** One frame: `orderingTableEntry` HUD `0x1e2858` < leaf
       `0x1e2894` < Flik `0x1e31d4` < mosquito `0x1e4ca0` — keep={HUD,Flik}, drop={leaf,mosquito} interleave, so
       no single offset threshold works (and the buffer is double-buffered `~0x1e2xxx`/`~0x1cdxxx`, addresses jump).
     - **Prims are DMA-ASSEMBLED, not CPU-built at the OT address.** A `write`-watch over the whole prim region
       (`0x801e1000+0x4400`, KSEG0 AND KSEG1 mirror, 4 frames) caught **0** writes, while the same watch on Flik's
       pos caught the integrator writes — so the per-object builder can't be found by watching the prim address
       (CPU access watches don't observe DMA; `transferLog` only does disc→RAM, not this RAM OT build).
     - **Object render source ≠ the AI/world position.** Poking the mosquito's chaser slot `0x80095358` (its AI pos,
       confirmed by read-watch: only `0x8004e5xx–0x8004ecxx` AI code reads it) to `9_000_000` did **NOT** move or
       remove the rendered mosquito — the renderer uses a separate per-object copy. So actor-pos poking won't hide
       objects either.
     ⇒ **The robust fix is identity/builder-level neutering** (find the CPU code that builds the object prim packets
     in their pre-DMA work buffer, or the actor-render dispatcher, and skip non-player actors — gated on
     COPIED+LEVEL01 like the floor neuter). Finding that requires more RE (locate the work buffer the OT is DMA'd
     from; the object update/render loop). This is a **multi-session task for a cosmetic gain**, so it is a poor ROI
     vs **Phase 4** (which is the actual end-goal authoring). Recommendation: defer step 4, proceed to Phase 4, and
     treat object-suppression as a known deferred integration item (it'll matter for every Tier-3 level since each
     hosts inside LEVEL01). Scripts: session run scratch (`t3_*` pick/watch probes).
5. ✅ **DONE — committed** the verified fixes: render relocations + load-delay loader fix + native-floor neuter in
   **`23ef438`** (builds on `a7176ec` cold-boot fixes + `de6ce7a` docs). Disc rebuilt at `build/ABL_tier3_render.cue`.

**IMMEDIATE NEXT (priority order, updated 2026-06-27):** crash-stability is now VERIFIED on the cold-boot disc
(turn-around ✅, butt-slam ✅ — session log below), so the open work is purely forward/cosmetic:
(a) **step 4** — neuter walls (chunk-35) + native objects (mosquito/leaf/mushroom still draw — the GATEOFF
terrain-suppress misses dynamic objects) for a fully clean custom view; (b) **Phase 4 — Blender exporter** to
author a *real* designed level (replace the hand-authored test geometry); (c) operator confirm in **pure
Interpreter** (the verification ran under the default isolated-instance CPU mode). steps 1/2/3 are ✅ DONE.
6. **Phase 4 — Blender exporter** (author custom geometry → blob), once the engine is crash-stable (steps 1–2).
   Start simple (flat + ramps); terrain detail later.
7. **Measure the render's real triangle budget** (software OT-insert clipper) to bound level design; if high
   fidelity (subtle terrain) is wanted, that likely needs the **GTE-hardware** render path (a bigger optimization).
   Do NOT decode native geometry formats — Tier-3 bypasses them by design; authoring is in Blender.

## FAST-FALL / BUTT-SLAM FLOOR-THROUGH + RESPAWN-LOOP — FIXED (2026-06-27)
Two user-reported bugs, both fast-vertical-movement not being caught:
- **Butt-slam / fast fall went THROUGH a platform** — the snap selected the floor by Flik's *current* Y, so
  a fast drop (gravity ~3200/frame) overshot far below a platform in one frame and the platform was no longer
  "near" -> he landed on the floor below (or fell through). FIX: track **PREVY** (`0x801F9608`) and select the
  floor by the HIGHEST point of his move this frame (`min(prevY, curY)`) -- i.e. where he was before the drop --
  so he lands on the floor he CROSSED. Verified: butt-slam apex −8458 → lands on A (−266), no pass-through.
- **Respawn death-loop** — the death-plane respawn set Flik's position but not his velocity, so he respawned
  still plunging and dropped through the floor → died → repeated. FIX: **reset FLIK_VY=0 on respawn** (and on the
  spawn warp, + init PREVY). Verified: fell (Y→23030) → respawned → settled at −266, no loop. (`mod/caves/tier3_collision.c`.)
- Open follow-up: butt-slamming WITH horizontal momentum keeps it through the airborne descent (~2700 u drift,
  decays to 0 on landing) — fine on big platforms, but can slide off the SMALL green wall-top. Options: enlarge
  the top, or zero horizontal velocity on a hard/slam landing.

## WALL SPEED-SLOWING (native feel) — DONE (2026-06-27)
The Tier-3 wall now **slows Flik's conserved speed** like the native game, instead of only clamping his position
(which let ABL keep building momentum -> he'd shoot off when turning away). Studied `wall.sav` on the pristine
disc: Flik's horizontal velocity is **VX@0x800A652C, VZ@0x800A6534** (= per-frame dX/dZ) and the **conserved
speed scalar is 0x800A6538** — open-space it builds to ~2000; pushing into a native wall it stays LOW (~50–320).
Replicated in `mod/caves/tier3_walls.c` via **velocity PROJECTION** (the authentic OG mechanism): when a wall
clamps Flik, the velocity component INTO the wall (the clamped/normal axis — VX if the X-face, VZ if the Z-face)
is **zeroed**, the TANGENTIAL component is kept, and the conserved speed `0x38` is set to the remaining tangential
magnitude. So Flik **slides along** the wall (tangential preserved) but builds **no momentum into** it, and is
~stuck pushing straight in (the steering curve gives the slide). Verified: pushing the Tier-3 wall, VX→0 and the
slide decays (e.g. realdZ 445→…→80, 0x38 settles ~70–80, vs building to ~2000 before); turning away peaks at only
~139 (no shoot-off — momentum wasn't stored); jump-onto-top + a 36-input jump soak still fine. (Logic runs 30 Hz
on 60 Hz video, so the velocity applies every other frame.) The earlier first cut just halved VX/VZ/SPD (uniform,
~82 creep); projection is the closer OG match (angle-dependent slide). Tunable: a tangential scale could change
the creep speed if a different feel is wanted.

## FINITE (JUMPABLE) WALLS + PLATFORM ON TOP + MULTI-FLOOR — DONE (2026-06-27)
**Flik can now jump over a wall and land on a green platform on top of it** (cold-boot disc, verified live: jump
apex Y −8522 → lands + STANDS on the top at Y=−4266; 48-input soak incl. jumps, no crash). Built on the wall
blocking below. New pieces:
- **Finite-height walls** (jumpable): the wall record gained Y bounds — now **6 int32** `xmin,zmin,xmax,zmax,
  ytop,ybot` (was 4); the wall query blocks Flik only when `ytop ≤ his Y ≤ ybot`, so jumping above `ytop` clears
  it. Authored in Blender from the `Wall*` object's **Z extent** (`mod/tier3_level_format.py`, `tools/tier3_blender_export.py`).
- **MULTI-FLOOR** floor query (overlapping platforms — a ledge on top of a wall): moved to its own CD-loaded
  function `mod/caves/tier3_floor.c::tier3_floor_y` pinned at **`0x801F0700`**, called by the collision cave via a
  function pointer (the multi-floor logic overflowed the budget-tight EXE cave; moving it kept the cave at
  `.text 0x110`). Rule: the **highest floor within `LAND_MARGIN` (2500) above Flik or below him** — catches a fast
  fall (gravity ~3200/frame would otherwise skip the snap window) onto a higher platform, while a ledge farther
  above is ignored (must jump). The **rising-snap was removed** (vy<0 no longer "grabs" overhead ledges → clean
  jump arcs; landing is the vy≥0 snap only). Layout: `WALL_FN 0x801F0100`, `FLOOR_FN 0x801F0700`, `RENDER_C
  0x801F0B00` in `TIER3.RND` (`RENDER_PAD 0x2000`, blob → `0x801F2000`).
- **Test level**: a finite wall (4 BU tall, X[+4000,+12000], Z±35000) + a GREEN platform on top (overhanging the
  near face by 2000 so Flik lands solidly on it, not on its edge). `mod/gen_tier3_level.py`.
- **Gotcha (cost time): a THIRD overlapping floor crashed the load.** Adding a red base-marker quad (so 3 floors
  — platform A, marker, top — overlap the footprint) reliably crashed at the cave's first activation (stack-smash
  → IBE). Two overlapping floors are fine; three crashed. ROOT not fully pinned (isolated by elimination); the red
  marker was dropped. Investigate before relying on 3+ overlapping floors.

## WALLS / BLOCKING — DONE (2026-06-27), via the budget refactor below
Custom **wall blocking** now works, authored in Blender (`Wall*`-named objects → XZ keep-out AABBs in the
blob). The collision-cave budget block (analysed below) was solved by **moving the per-frame native-suppression
loop AND the new wall query into the CD-loaded render region** (`mod/caves/tier3_walls.c` → `tier3_wall_resolve`
pinned at **`0x801F0100`** in `TIER3.RND`; `mod/tier3_otrender_live.asm` moved `RENDER_C`→`0x801F0400` to make
room). The collision cave just calls it (the `LV_MAGIC` gate already implies the region is loaded) — removing the
suppression loop freed more bytes than the call cost, so the cave SHRANK (`.text` 0x370→0x350). The wall query is
a **swept AABB** (clamp when the prev→current move crosses a face while overlapping the other axis + a
containment fallback; prev-XZ at `0x801F9600`) → Flik stops at the entry face and slides; **no tunneling** even at
full run speed. Blob: `NWALLS` in the header flags word's high 16 bits, AABBs (`xmin,zmin,xmax,zmax`) after the
tris (`mod/caves/tier3_level.h`, `mod/tier3_level_format.py`). **Verified live** on the cold-boot disc: a barrier
on platform A's +X half clamps Flik at its face (max X = the −X face, vs tunneling to 266182 before); soak of 48
direction-changes, no crash, collision intact. **Limits:** walls must be thick (≥~8000) + wide (cover Flik's
±~25000 steering curve) to be a real barrier (see TIER3_AUTHORING.md).

**VISIBLE wall (2026-06-27):** walls are collision-only (no drawn geometry). To confirm them by eye, a **red
floor patch over the wall footprint** is drawn via the proven blob-tri render path (`gen_tier3_level.py`) — Flik
visibly stops at its near edge (operator-facing confirmation; commit `0637095`). **Full 3D wall-box rendering was
attempted and REVERTED:** a render-cave pass that draws each AABB as 4 flat-red side faces (refactored the tri
emit into a shared `emit_view_tri` helper + a wall pass in `tier3_otrender.c`) **blanked the whole custom render**
when enabled. ISOLATED: with the wall pass disabled the platform renders fine (so the `emit_view_tri` refactor is
correct); it is **not** a stack overflow (sp@hook=0x80080bc8, ~6.6 KB headroom); the wall-draw pass itself
corrupts the render (root cause TBD — likely a malformed primitive from the tall near-camera wall geometry). Next
attempt: instrument the wall tris' projected coords / emit one fixed-screen wall tri to localise, or draw walls
as their own separate DMA pass. The blob now >514 B (red marker) so the in-image bake limit is a WARNING (render
disc ships TIER3.RND in high RAM; only the legacy collision disc cares).

## FRONTIER ANALYSIS (2026-06-27) — the collision-cave .text budget (SOLVED for walls; see above)
After Phase 4 (authoring) shipped, the next-most-valuable features are **walls/blocking**, a **level exit/goal**,
and **spawn heading**. All three need code in the COLLISION cave (the per-frame player-update hook that owns
Flik's position) — and that cave is **out of space**:
- The cave lives in a **verified loader-safe EXE zero-run of ~1032 B** (`0x800810bc..0x800814c4`), now FULLY
  packed: `FLOOR_PUB` + `CAVE_TRAMP(0x18)` + `tier3_collision` `.text(0x370)` + `tramp3(0x34)` + `FLOOR_PUB`.
  The build asserts `.text ≤ 0x378`; current is `0x370` → **8 bytes spare**.
- It **cannot grow**: below it (`0x80081000..0x800819c0`) is game code/data + our caves; above it
  (`0x80081a00..0x80082000` reads zero in the image but) is the **game's gp-relative globals** — `gp=0x80081d98`
  lives there, and `0x80082314`/`0x80082434`/`0x80082498` (swept-plane count / coyote gate / DAT base) are
  gp-relative globals the game writes. So that "zero" region is live BSS, not free.
- A wall loop (~60–100 B) or even a C **call-out** to a function in the CD-loaded high-RAM region (~32–48 B for
  the ptr-load + arg spill + `jalr`) both exceed the 8 B headroom.

**⇒ Walls/exit/heading require a cave-space refactor first.** Options (next session):
1. **Reclaim ~40–90 B in the collision cave** (e.g., shrink the per-frame native-suppression, or fold the
   spawn-warp/death paths) to fit an inline wall loop. Cheapest if achievable; the cave is already lean.
2. **Move the wall/exit logic into the CD-loaded render region** (`TIER3.RND` @0x801F0000 — has room) and call
   it from the collision cave via a function pointer, reclaiming just the ~32 B call-out cost. Gated on COPIED
   (the region isn't loaded until the first gameplay frame, which is also when walls start mattering).
3. **A second loader-safe EXE zero-run** for a wall cave — none found yet (the 0x80081a00+ region is gp-globals).
Git safety net: Phase 4 is committed (`6927eb5`), so a refactor attempt can revert cleanly.

**Visual side (per-surface textures, 4b "future") is also gated by texture availability.** Live VRAM survey
(2026-06-27): the **dirt tile** (`0x068d`/`0x3470`, 8bpp) is the one clean *tileable* 64×64 ground texture; the
**grass** is a **non-tiling atlas** (per-quad UVs scatter: (72–86,14–60), (12–30,134–157), (64–119,96–127)),
so it can't be planar-mapped. So per-surface variety needs either an atlas-UV authoring path (Blender UVs →
blob) or finding/identifying more tileable tiles — not a quick win. Current single tinted-dirt look stands.

## ROADMAP — all phases (spike-first; de-risk each pillar before building on it)
Legend: ✅ done · 🔜 next · ⬜ todo. Each phase has an **exit criterion** (the proof that lets us build on it).
Ordering is dependency-driven, not calendar. "Spike" = throwaway proof; "build" = the real, reusable version.

### Phase 1 — Collision spike (floor) ✅ PASSED 2026-06-24
**Goal:** prove ABL's controller accepts a custom floor fed through a hook (the riskiest unknown).
- ✅ find the player floor-resolution hook (integrator `FUNC_8003633C`, final Y-writer `0x80036d54`)
- ✅ inject a MIPS cave with a hardcoded 2-platforms+gap "mesh"; Flik walks platforms + falls in gap (live)
**Exit (met):** Flik walks a raised + a lowered platform and falls in the gap, all from native input/gravity.
Details in "Phase 1 — COLLISION SPIKE: PASSED" below. Sources: `mod/tier3_collision_spike.asm`,
`src_mod/tier3_collision_spike.c`.

### Phase 1.x — Collision engine completion (1a/1b/1c ✅ DONE 2026-06-24; 1d–1f next)
Turn the spike into a real collision backbone. Each is an incremental hook/extension of the cave.
- ✅ **1a Disc-permanent build** — collision cave built into the EXE via `mod/build.py` + the `0x80036d54`
  patch; **cold-booted from disc** (no live inject) and the mesh controls Flik's Y at runtime. See
  "Phase 1.x — 1a/1b/1c" below. Disc `build/ABL_tier3_collision.{bin,cue}`.
- ✅ **1b Real mesh query** — replaced the hardcoded rects with a **triangle-mesh** lookup over an in-RAM mesh
  (point-in-tri XZ + plane height), written in **C** (`mod/caves/tier3_collision.c`, compiled by gcc, the same
  pipeline as the grain cave). Flat heights exact at all tested points. (Linear scan over the tiny test mesh;
  the spatial grid is the scale-up step, deferred until tri counts grow — noted, not yet needed.)
- ✅ **1c Ramps/slopes** — the plane-height eval interpolates across a triangle; a sloped quad gives a graduated,
  walkable surface (live −90909→−89096→−87189; on-disc −90828→−89310→−87574), no stair-stepping.
- ✅ **1d Walls / blocking** — AABB keep-out boxes; the hook (running after the native XZ commit) pushes Flik
  out along the entry axis and writes the clamped X/Z back, so he stops at the wall and **slides** along it.
  Live: drove +X into a wall, X stopped at the face (never penetrated), Z kept moving (slide), floor held. See
  "Phase 1.x — 1d" below.
- 🟡 **1e Death plane + respawn** — DONE & PROVEN (Flik fell past the death plane and respawned at our custom
  spawn), BUT testing exposed the keystone issue below. Spawn + death-plane are now mesh data (`gen_tier3_mesh.py`),
  the cave warps Flik to spawn when his floor Y passes `TIER3_DEATH_Y`. See "Phase 1.x — 1e" below.
- 🟡 **1f Authoritative floor** — DONE (architecture) + a coupling finding. Re-hooked at the PLAYER's per-frame
  post-physics point (`0x800495d0`, right after the integrator returns for Flik; player call site `0x800495c8`,
  `s1`=`0x800a6500`) so the cave is authoritative, Flik-only, every frame — no grounded/airborne path bias. Model =
  CLAMP (floor is a minimum, not a snap): clamp Y up only when Flik is below the mesh floor, leave him alone above
  it — so **ABL's jump (X) and butt-slam still work** (verified: X jumps Flik 6336u up and lands back on our floor).
  FIXED the drift on platform A while driving; idle authority on every region. RESIDUAL: CLAMP keeps jump but
  **floats** on descending ramps / lower platforms because native gravity targets the *native* floor, not our mesh
  (a SNAP model tracks those but kills jump — neither is fully correct while the native floor exists). ⇒
  **full robustness is coupled to Phase 3c (native-level suppression)**: with no native floor, gravity falls Flik
  to OUR floor and the clamp catches him → jump *and* tracking both work. See "Phase 1.x — 1f" below.

### Phase 2 — Render spike (draw the world) ✅ CORE DONE (2a/2b/autonomous/CLIP/OT-insert; 2c textures left)
> **DONE 2026-06-25:** near-plane+screen CLIP (renders from any camera, gap-free), OT-INSERT render (drawn
> by the game's own DrawOTag DMA -> no side-DMA throttle, no buffer race, **depth=2d for free**: Flik
> composites over the platform), native scene suppressed. Flik visibly walks a real multi-feature custom
> level. Only **2c (textured tris)** remains. See the OT-insert + real-level sections below.
**Goal:** make the custom mesh VISIBLE in-world, aligned to the collision (so far it's invisible/numeric).
- ✅ **2a** draw GP0 triangles into the ABL frame — DONE 2026-06-25. Flat-shaded tris (GP0 `0x20` = color + 3
  packed `(y<<16)|x` verts) drawn into the live gameplay frame via the proven GPU-injection path. See
  "Phase 2 — 2a" below. Frame `build/spike2a_frozen.png`.
- ✅ **2b** camera alignment — DONE 2026-06-25. Found ABL's camera in RAM (rotation at the world-draw GTE +
  position `0x1F800374`); projected the collision mesh and it renders **in-world, perspective-correct** (green
  platform A, yellow ramp, cyan platform B on the ground around Flik). **Per-frame TRACKING confirmed** — drove
  Flik forward across 3 poses, the mesh stayed locked to world coords (platforms approach + pass, clip behind
  camera). See "Phase 2 — 2b" below. Frames `build/spike2b_mesh.png`, `spike2b_track_0/1/2.png`.
- ✅ **AUTONOMOUS in-cave per-frame render** — DONE 2026-06-25 (commit 838da50). The platform draws itself every
  frame with no host help (`mod/caves/tier3_render.c`, hook 0x80062d04, reads R@0x80090FB0 + C@0x1F800374,
  projects int32, DMAs to the back buffer). RE of the camera RAM block: `src_re/camera_transform_block.c`. See
  "Phase 2 — AUTONOMOUS" below. Frame `build/tier3_render_autonomous.png`.
- ⬜ **2c** textured triangles — reuse existing VRAM texture pages (texpage + UVs) so it doesn't look like flat polys.
- ⬜ **2d** depth/order (OT) — composite correctly with (or fully replace) native geometry; no z-fighting/overdraw.
**Exit (phase):** Flik visibly stands on drawn platforms and visibly falls into a drawn gap.

### Phase 3 — Level format + loader (ship a level) 🟢 (3a blob ✅, 3b collision cold-boot ✅, 3c suppress ✅; **3b.R render-on-disc = next (steps below)**, 3d spawn left)
> **2026-06-25:** 3a unified blob ✅; 3b collision baked on the cold-boot disc — now with a **REAL
> multi-feature level** (platform+ramp+raised+gap, `mod/gen_tier3_level.py`, 400 B ≤514, verified loading
> at boot) ✅; 3c native-terrain suppression ✅ (OT-filter zero-length collapse, sky+custom-level only).
> **2026-06-26:** the **cold-boot disc now boots → loads LEVEL01 → runs custom COLLISION** end-to-end and
> is user-tested through "Press X" (`build/ABL_tier3_render.cue`; blob in the LEVEL.DAT last-sector slack).
> Boot-hang + "loading…" DBE both fixed (see the status banner at the top + [[Finding - Tier-3 render disc-delivery]]).
> **Remaining: render ON the disc.** Render disc-delivery is now SCOPED: the ~2.8 KB cave can't append to
> LEVEL.DAT/LEVEL.RAW (both LBA-full) nor sit in-image (no safe zero-run ≥2784 B) → it needs its **own new
> disc file**, loaded by **`FUNC_80046330(name,dest)`** (the game's by-name `CdSearchFile` loader). Concrete
> steps in **3b.R** below. Today the visible render still ships as a live-inject SAVE STATE
> (`ABL_tier3_FULL.sav`); the cold-boot disc carries collision only. **3d spawn override** moot for this
> level (A is centred on the native spawn).
**Goal:** a level becomes DATA on disc that the engines load — no more hardcoded caves.
- ⬜ **3a** define the on-disc format: render mesh (verts/tris/UV/texpage) + collision tris + surface types +
  spawn (pos/heading) + object list + texture refs; versioned header; RAM-budget-aware layout.
- 🟢 **3b** loader — level BLOB reads from disc to RAM at level-load ✅ (rides in the LEVEL.DAT last-sector
  slack; collision engine reads it in place). **RENDER cave delivery = 3b.R below (the remaining work).**

#### 3b.R — render-on-disc delivery (new CD file via `FUNC_80046330`) — the steps to finish the visible cold-boot level
Why a new file: LEVEL.DAT (163 sec, full) and LEVEL.RAW (366 sec, full, **hardcoded LBA 3069**) have no append
room, and no in-image zero-run ≥2784 B is safe. So ship the render as its own raw file and load it by name.
Reuse `FUNC_80046330(a0=filename, a1=dest)` → uppercases name → `FUNC_80045FC4`→`CdSearchFile 0x8006f690` →
whole-file read to `dest` (NO decompress). RE: `src_re/file_loader_80046330.c`; analysis: [[Finding - Tier-3 render disc-delivery]].
1. ✅ **Pin the CdSearchFile name/path string (2026-06-26).** Broke at 0x80046330, read `a0` live: names are
   **full relative paths `dir\file.ext`** — lowercase, backslash, no leading slash, no `;1` (observed
   `fmv\fmv.bin`, `sfx\global.vh`, `bits\memory.bin`, `level00\level3.raw`). ⇒ name the file in `LEVEL01/` and
   load **`FUNC_80046330("level01\\tier3.rnd", 0x801E0000)`** (loader uppercases it). (getRegisters keys are lowercase.)
2. ✅ **Render file on the disc (2026-06-26).** `tools/build_tier3_render_disc.py` stages `cave_otrender.bin`
   as `\LEVEL01\TIER3.RND` (2 sectors) at LBA **313747** + shrinks the trailing `<dummy>` past it. GOTCHA:
   the disc is byte-packed (biggest free gap = 1 sector), so the file must EXTEND the disc at the (shrunk)
   trailing-dummy start; a far/out-of-order LBA *inside* the dummy left its data zeroed (verified byte-match
   once placed correctly). Blob stays in the DAT slack.
3. ✅ **Cave loads it at the first gameplay frame (2026-06-26).** The COLLISION cave (Flik-spawned gate)
   calls a tiny asm trampoline `tier3_load_render @0x8007F288` (loader-stub zero-run) → `FUNC_80046330(
   "level01\tier3.rnd", 0x801E0000)` + sets `COPIED`. GOTCHA: calling the loader from the **DrawOTag stub
   faults (A(0x40) panic)** — it mutates resource/CD globals mid-DMA-dispatch; the **player-update (cave)
   context is safe**. Render flags are baked into the render cave (no buffer). Trampoline keeps the cave in
   its 0x378 zero-run (.text 0x370).
4. ✅ **Render cold-boot VERIFIED (2026-06-26).** Cold boot → LEVEL01 → `COPIED=1`, TIER3.RND byte-matches at
   0x801E0000, render hook firing (SENT++), custom **green/yellow/magenta** platforms draw in-world, Flik
   composited on top, native terrain suppressed — **no save state** (`build/ABL_tier3_render.cue`).
5. 🟡 **Robustness / polish (open).** A few native OBJECTS (mosquito, mushroom) still draw — terrain-suppress
   GATEOFF misses them. Also: `COPIED` re-arm on level re-entry, missing-file → graceful no-render, and the
   cyan platform C (only green/yellow/magenta seen — check the mesh/clip).
**Exit (3b.R): ✅ cold boot → LEVEL01 → custom platforms VISIBLE + walkable, no save state.** (step-5 polish remains)
- 🟡 **3c** suppress native level — collision-suppression DONE + **self-contained in the cave** (no external pokes;
  A/ramp/gap-death/jump verified disc-ready); render-suppression ATTEMPTED but needs proper terrain-draw RE (the
  vault notes are wrong; `0x80010000`/`0x800172dc` don't blank it). See "3c update"/"3c render-suppression" below.
  See "Phase 3c" + "FLOOR-QUERY ROOT-CAUSED" below. Deepening the sector floor + zeroing the plane count makes flat
  platforms (A, B) track exactly. **The recurring "ramp float" is NOT a floor-query bug** — root-caused to the
  1f clamp model snapping only when Flik is *strictly below* the floor, so the walking-bob (Flik a few hundred
  units above the floor while driving) drifts; the query itself is correct (idle tracks; hit-index matches Python).
  Fix = **velocity-gated snap** (need ABL's jump/grounded state) — also makes native suppression unneeded for it.
  Render-blanking not started.
- ✅ **3d** spawn override — DONE 2026-06-27. The collision cave warps Flik to the blob's `LV_SPAWN` on the first
  gameplay frame (one-shot via `SPAWN_DONE` @`0x8007F2FC` — a verified-zero boot word in the loader zero-run;
  `0x800814A0` read garbage at boot and was wrong). The Blender exporter sets `LV_SPAWN` from the `Spawn` empty's
  position (geometry now anchored to the Blender WORLD origin, decoupled from the empty). Verified: a demo with the
  empty at Blender (8,8,0) cold-boots Flik to (205091,−266,500897) = native+(8000,0,8000), not native. Limit: keep
  the spawn near the native spawn (a far XZ warp drops into unstreamed void). Heading not yet applied (blob has no
  heading field). `mod/caves/tier3_collision.c`, `tools/tier3_blender_export.py`.
**Exit (phase):** boot → custom level loads from disc, renders + collides from data, Flik spawns in it.

### Phase 4 — Blender exporter (author with ease) ✅ (4a/4b/4c/4d done + sample + authoring guide)
**Goal:** the Fast64-like part — build a level in Blender, one button to playable disc. Easy once 1–3 exist.
> **DONE 2026-06-27 — Blender→playable cold-boot disc proven end-to-end.** Authored a DISTINCT level in
> Blender (red spawn / blue ramp / white top) and one-button-built a disc that cold-boots it: the new
> geometry renders (red/blue/white, blob magic=T3LV, 8 verts/6 tris — not the test 12/8) and collision
> works on it (drove +Z, climbed the blue ramp, Y −266→−2826). See the Phase-4 session log at the bottom.
- ✅ **4a** Blender scene → custom format. `tools/tier3_blender_export.py` (runs in Blender) reads MESH
  objects + a `Spawn` empty + per-face material colour → a level **JSON**; `tools/tier3_level_from_json.py`
  packs JSON → the **T3LV blob** through the shared **format authority** `mod/tier3_level_format.py` (now also
  used by `mod/gen_tier3_level.py` — verified byte-identical refactor). Coords map Blender (Z-up, spawn-empty
  relative, `scale` world-units/BU) → ABL world (−Y up, pinned to the LEVEL01 spawn). Winding auto-corrected.
  Surface tris only (no walls yet). Round-trip proven: a Blender clone of the test level → byte-identical blob.
- ✅ **4b** textured triangles — DONE 2026-06-27. The render cave now emits **GP0 0x24 textured tris** reusing a
  real loaded LEVEL01 VRAM texture (the native **dirt-ground tile**, 8bpp 64×64, `TEX_PAGE 0x068d` / `TEX_CLUT
  0x3470`, found live via `gpu.pickObject` on the un-suppressed terrain). **Planar UV** from world XZ
  (`u=(X>>6)&63, v=(Z>>6)&63` → ~one tile per 4096 units), **interpolated through the near/screen clipper** (added
  UV arrays + a full-precision `lerp_uv`). The blob's per-face colour becomes a **modulation tint**, so authored
  colours survive as tinted textures (green platform → green-tinted dirt). Verified live: platforms render
  textured + stable (600f turning, no crash, collision intact). `mod/caves/tier3_otrender.c` (`TEXTURED 1`;
  8-word nodes; `RENDER_PAD`→0x1000). Per-material/per-surface texture selection + Blender UVs = future.
- ✅ **4c** validation pass — caps (≤64 verts / ≤128 tris), spawn present, vertical-tri (wall) rejection, 514 B
  bake limit, **degenerate-tri**, **death-plane-below-geometry**, and a **spawn-over-floor guard** (a spawn over a
  gap death-loops — caught), plus near-cap perf `warnings()` (`mod/tier3_level_format.py::validate`/`warnings`).
  (Manifold/closed checks are N/A — a floor is an open surface, not a solid.)
- ✅ **Sample + authoring guide** — `tools/abl_blender/tier3_sample_level.py` (a TRACKED, text Blender script that
  regenerates a sample level: 4 platforms + ramp + gap + `Spawn` empty, showing both `abl_color` and Base-Color
  materials) and `tools/TIER3_AUTHORING.md` (conventions, coord map, scale, caps/limits, the TL;DR commands).
  Verified: the sample builds via the one-button pipeline and cold-boots into a textured, walkable level.
- ✅ **4d** one-button pipeline: `tools/tier3_build_level.sh LEVEL.blend [scale]` → Blender export → JSON → blob
  → `build_tier3_render_disc.py` (new `TIER3_KEEP_BLOB=1` opt-out bakes OUR blob instead of the test level) →
  `build/ABL_tier3_render.{bin,cue}`. Cold-boot verified.
**Exit (phase): ✅ a Blender-authored level boots and is walkable + visible.** (custom spawn = Phase 3d; 4b textures left)

### Phase 5 — Integration hardening (the long tail) ⬜
**Goal:** point every native subsystem that assumes the native world at the custom world, or disable it.
- ⬜ camera-vs-world collision (stop the camera clipping through custom geometry)
- ⬜ water/death planes (native ones gone → driven by our surface types, see 1e)
- ⬜ triggers + level-exit region codes (`[[level-exit-trigger-open-death-confound]]`) — author exits in our format
- ⬜ enemy collision/pathing on the custom floor (enemies currently read the native world)
- ⬜ object/pickup placement onto the custom floor (objects already editable; just need our floor under them)
**Exit (phase):** a custom level plays end-to-end (spawn → traverse → hazards → exit) with no native-world artifacts.

### Milestone M-CUSTOM-LEVEL — first fully-custom playable level (the MVP "done")
Authored entirely in Blender, built to disc, cold-booted: new geometry + new collision + new spawn + walkable +
visible + reaches an exit. This is the end-goal proof for the initiative; Tier-3 "works" when this ships.

**Current position:** Phase 1 ✅. Immediate next = Phase 1a (disc-permanent build) then 1b (real mesh query),
in parallel-ish with Phase 2a/2b (render spike) so we can SEE the mesh while extending collision.

## Honest risks (eyes-open; none currently believed fatal)
- **Integration long tail** = the real cost: every native subsystem that assumes the native world (camera
  collision, water/death planes, triggers, exit region codes, enemy collision/pathing) must be hooked/disabled.
- **R3000 perf** (33 MHz): triangle collision needs a spatial grid/BVH; fine for one player + few entities.
- **PS1 RAM** (2 MB): the level mesh + collision must fit.
- **Phase-1 kill-criterion:** if the controller is too entangled with the native world to accept a custom one
  via a hook, Tier 3 is in doubt — which is exactly why the collision spike is first.

## Phase 1 — COLLISION SPIKE: PASSED (2026-06-24)
**The controller accepts a custom world fed through a hook.** Live on `level01_lookingdown_flatground.sav`
(cc5 isolated instance), a hardcoded "mesh" of 2 platforms + a gap was injected and Flik was driven across it
with native input. Floor height came ENTIRELY from our cave; ABL kept owning X/Z movement, gravity, animation.

Single +X traverse (Y is 100% from the cave):

| frames | X | region | Flik Y |
|---|---|---|---|
| 8–64  | −18433 → 9783  | **A (raised)** | **−92578** held — walks across |
| 72–96 | 14746 → 28916  | **gap**        | −91965 → −67461 — **falls** |
| 104–128 | 33672 → 47735 | **B (lower)** | **−85578** held — lands + walks |

No crash, stayed in-level, full HP. Per-region spot-checks hit the platform heights EXACTLY.

### The hook (what worked, and the false start)
The movement integrator `FUNC_8003633C` writes Flik's Y up to 3× per frame:
- `0x80036380` gravity (`sw v0,4(s7)`, v0−=3200)
- `0x80036cec` collision commit (`sw v1,4(s7)` from `sp+0x1c`) — **first hook attempt**
- `0x80036d54` final adjust (`sw a0,4(s7)`, a0 = Y+3200) — **the winning hook**

Hooking the **commit (0x80036cec)** worked for the GAP and a LOWERED platform, but a RAISED platform snapped
back to the native floor — the post-commit step (`0x80036d54`) + gravity ran *after* our hook. Hooking the
**last writer (`0x80036d54`)** makes our cave the final word, so raised + lowered both hold. Its delay-slot
instr `0x80036d58 lui v0,0x800a` still runs (feeds `0x80036d5c`), so the cave must not clobber `$v0`.

- **Patch (1 word):** `0x80036d54` `sw a0,4(s7)` → `jal 0x800810c0` (`0x0c020430`).
- **Cave:** `0x800810c0` (verified-stable region, 200 B). Reads Flik X/Z from `0x800a6500`+0/+8, runs the
  custom floor test, writes Y to +4, `jr ra`. R3000 load-delay nop after the `lw`.
- **Sources:** cave = `mod/tier3_collision_spike.asm` (armips → `build/cave_spike.bin`); readable C reference =
  `src_mod/tier3_collision_spike.c` (MOD, not OG RE). Frames: `build/spike_A.png` / `spike_gap.png` / `spike_B.png`.

### What this proves / doesn't
- **Proves:** the host controller (input→XZ, gravity, animation) composes with an externally-supplied floor —
  the Tier-3 host/mod ownership split is real. This was the riskiest unknown; it's cleared.
- **Doesn't yet:** walls, ramps, surface-types (Phase 1.x); physics landing vs snap (cave snaps Y each frame —
  fine for a backbone); a real mesh query (Phase 3); disc-permanent build (live-injected, resets on loadState).

### Next
Phase 2 render spike — draw this same test mesh in-world via injected GPU, aligned to the collision (so the
platforms/gap are visible, not just numeric). Then disc-permanent build of the collision cave via mod/build.py.

## Phase 1.x — 1a/1b/1c collision engine (DONE 2026-06-24)
The spike's hardcoded rects became a **real, data-driven triangle-mesh collision engine, written in C**, and
**baked into a booting disc**.

**Toolchain finding (big):** `mod/build.py` compiles `mod/caves/*.c` with `mips64-linux-gnu-gcc` (freestanding
R3000 LE, soft-float, `-nostdlib`) and links them into the EXE zero-run via armips `.importobj` (same path as the
grain cave). So cave logic can be **C, not hand-MIPS**. The EXE is 471040 B → loaded image ends ~`0x800827c0`, so
the `0x800810c0` zero-run (~5.7 KB) is **inside the file = disc-writable**. Constraint kept: under `-nostdlib`,
64-bit multiply/divide pull `__muldi3`/`__divdi3` (not linked) — so the cave uses a widening 32×32→64 `mult`
(native, inlined) for the edge cross-products and a **32-bit** divide for plane height (mesh normals are
pre-scaled small). Verified the compiled `.o` exports only `tier3_collision_hook` + `tier3_tris`, no helpers.

**Files:** `mod/caves/tier3_collision.c` (the engine), `mod/caves/tier3_mesh.h` (generated mesh),
`mod/gen_tier3_mesh.py` (mesh generator — seeds the eventual Phase-3 format; verifies each normal reproduces its
triangle's vertices), `mod/patch_tier3_collision.asm` (disc hook), `mod/tier3_collision_live.asm` (live-inject
image). OG RE: `src_re/movement_integrator_8003633c.c`.

**Mesh format (per triangle, runtime world coords):** `v0(x,y,z), v1(x,z), v2(x,z), normal(nx,ny,nz)` (normal
pre-scaled so `max|comp|≈8000`). Floor query = point-in-triangle in XZ (3 edge sign tests, both windings) →
plane height `y = v0y − (nx·dx + nz·dz)/ny`. No triangle under Flik → gap (keep falling).

**1b — real mesh query (live, flatground save):** test mesh = flat platform A (Y −92578) → ramp → flat B1 →
**hole** → flat B2. Platform A read **−92578 at all 18 probe points** (X∈[−25000,5000] × Z∈{100000,190000,300000});
B1/B2 flats exact; the hole falls. Collision is now driven by mesh DATA, not code rects.

**1c — ramps/slopes:** the ramp quad (−92578→−85578 over X[10000,30000]) gave a graduated, walkable height
(−90909 → −89096 → −87189), i.e. a real slope, no stair-stepping.

**1a — disc-permanent + active on cold boot:** built `build/ABL_tier3_collision.{bin,cue}` (EXE embedded at LBA
23, sha1 `017d280b…`), cold-booted via the `flik_to_level01` movie. The hook is in the **booted EXE**
(`0x80036d54`=`j tier3_tramp`, `0x800810c0`=`jal tier3_collision_hook`) and the mesh controls Flik's Y at runtime
with **no live injection**: platform A −92578, ramp graduated (−90828→−89310→−87574), B2 −85578, hole falls.
Disc-build flow: temporarily swap `mod/patch_tier3_collision.asm` over `mod/patch.asm` (the operator's fast-berry
WIP is restored after), `python3 mod/build.py --force`, copy to tier3-named disc so it doesn't shadow the Path A
dome disc.

**Gotchas logged:** (1) first query right after injecting the hook reads the native floor once — **warm the hook
a few frames before measuring**. (2) Teleporting Flik ~600k units to an **unstreamed** area gives one garbage
frame (the native pre-hook collision reads unloaded sectors); settle in-area first. (3) The disc-booted LEVEL01
spawn is (196452,172615,493011), far from the test mesh (placed at the flatground coords) — for a clean
"spawn-on-platform" boot artifact, regenerate the mesh centered on the real spawn (deferred; runtime proof above
already confirms 1a). (4) A deep fall **auto-reset Flik to spawn** (no HP loss) — a useful native signal for 1e.

## Phase 1.x — 1d walls/blocking (DONE 2026-06-25)
Walls extend the SAME cave. The hook fires after the native XZ commit (`0x80036ce8`/`0x80036cf0`), so Flik's new
X/Z are already in his struct — the cave reads them, pushes him out of any wall, writes the clamped X/Z back, then
sets the floor Y. **Walls = AABB keep-out boxes** in XZ (`tier3_walls[]`, generated; full-height for now). On
penetration the cave clamps **only the axis Flik crossed** (decided from his previous frame's XZ, persisted in the
zero-run at `0x80081500`/`0x4`/`0x8`) → he stops at the wall face and **slides** along it (free wall-sliding).

**Live proof (cc5, flatground save):** wall keep-out `X[0,4000]`; drove +X into it — X climbed −10185→0 then **held at
0** for 50+ frames (never entered `(0,4000)`), while Z kept moving (200265→193616) = sliding, and Y stayed −92578.
Disc rebuilt with walls (`build/ABL_tier3_collision.{bin,cue}`, EXE sha1 `58ec5424…`, hook verified in the image;
cold-boot activation path is the one already proven in 1a). Source: `mod/caves/tier3_collision.c` (`wall_resolve`),
walls authored in `mod/gen_tier3_mesh.py`. Limits: full-height (ignores Y/wall-top — a tall ledge blocks at any
height); AABB only (arbitrary-angle walls from mesh tris = the general case, after the spatial grid).

## Phase 1.x — 1e death plane + respawn (DONE, + a keystone finding) 2026-06-25
Spawn point and a death-plane Y are now **mesh data** (`TIER3_SPAWN_X/Y/Z`, `TIER3_DEATH_Y` in
`gen_tier3_mesh.py` → header). The cave: after floor/walls, if Flik's floor Y has passed the death plane
(fell below all geometry) it warps him to the custom spawn (we own death/respawn — no native pit needed, which
LEVEL01 lacks anyway). **Proven:** walked Flik off platform B1's edge into the hole; he fell (Y −85578 → −50658)
and at the next frame (past `DEATH_Y=−50000`) **respawned at the custom spawn (−4667,−92578,200000)** instead of
the native deep-fall reset. Source: death check in `tier3_collision_hook` (`mod/caves/tier3_collision.c`).

### KEYSTONE FINDING (reprioritizes 1f)
Probing exposed that the collision hook is **grounded-biased**. The Y-resolution has two paths:
- **grounded:** collision commit `0x80036cec` → +3200 adjust `0x80036d54` (our hook) — works (1b/1c/1d solid).
- **airborne:** gravity `0x80036380` → `0x80036d30` → `0x80036d54`. Our hook is on it too, but when Flik catches
  air during sustained movement, native gravity wins on some frames and our floor isn't re-applied — so he can
  drift off a flat platform. The floor-query MATH is correct (verified a B1 interior point computes as inside →
  −85578); the gap is **authority**, not geometry. Also: the **native LEVEL01 floor is still present under our
  "gap"** (it catches Flik unless he's already moving fast off an edge) — native-level suppression is Phase 3c.
- **Native floor (sign) note:** −Y is up; the native catch (~−85720) sits *above* a deep death plane, so a
  teleport-into-gap lands on native floor and never reaches the plane. Walking off an edge builds the fall that
  does reach it (how 1e was proven).

**Fix (1f, now keystone):** hook the native **floor-VALUE** the integrator clamps against (replace the resolved
floor height with our mesh height) rather than overwriting Y on one writer. Then native gravity/jump/grounded
detection all run against our mesh — fixes the drift, preserves jumping, and hardens 1b–1e. Do 1f before more
features. (Disc not rebuilt for 1e — wait until 1f stabilises the engine.)

## Phase 1.x — 1f authoritative floor (DONE + coupling finding) 2026-06-25
**The keystone fix: stop fighting the integrator's internal grounded/airborne paths — hook ONCE PER FRAME after
the whole integrator runs, Flik-only.** `FUNC_8003633C` is a GENERIC integrator with 3 callers (`0x800495c8`
player, `0x8004c024` mover-VM/enemies, `0x8004e628` chaser AI) — so the old in-integrator hook (`0x80036d54`)
fired for every actor and was grounded-biased. New hook = `0x800495d0` (the player update `jal 0x80037a38` right
after the integrator returns; the player call site `0x800495c8` has `s1`=`0x800a6500`, `a2`=`s1+0x82`=Flik's
sector field). Trampoline replays that call, then runs our cave LAST → final authority.

**Model = CLAMP (floor is a minimum, NOT a snap).** ABL **does have a jump (X / Cross)** — and pressing X again
in the air does a **butt-slam** (a downward attack), both native moves that change Flik's Y. So a SNAP model is
WRONG: forcing Y to the floor every frame kills the jump (an early "no jump" reading was an artifact of testing
*with* the snap cave — corrected). The cave clamps Y up to the mesh floor **only when Flik is below it**; when he's
above (jumping, butt-slamming down before he lands, or mid-fall) he's left to native physics. **Verified: with the
clamp model, pressing X makes Flik rise 6336 units above the floor (−92578 → peak −98914) and land back on it.**
The butt-slam (downward) composes naturally — it drives Y down, the clamp catches it at the floor.

**Proven on clean ground:** platform A holds −92578 while driving (no drift); jump works (above); idle authority
on every region; the floor query is proven correct independently (a Python replica of the exact C logic returns
the right height for every in-bounds point; only a real hole returns gap).

**THE COUPLING (1f ⇔ 3c).** With the **native floor still present**, neither model is fully correct: SNAP tracks
descending ramps/lower platforms but kills jump; CLAMP keeps jump but **floats** on those surfaces — because the
clamp relies on native gravity to bring Flik down to a lower floor, and **native gravity targets the NATIVE floor,
not our mesh**, so on any surface where our floor sits above the native floor he settles on native ground (A,
where our floor is *below*… i.e. higher up than native, clamps fine; ramp/B float). The clean resolution is
**Phase 3c (suppress the native geometry/collision)**: with no native floor, native gravity falls Flik until OUR
clamp catches him — then jump **and** ramp/step tracking both work. So: **the clamp model is correct, and Phase 3c
is the prerequisite that unlocks its full tracking** (an alternative without 3c is the deeper "hook the native
floor-VALUE the resolver clamps against" so native physics runs against our mesh — heavier RE). Disc NOT rebuilt
for 1f (rebuild after 3c). Source: `mod/caves/tier3_collision.c` (clamp + `wall_resolve` + death), hook
`mod/patch_tier3_collision.asm` / `mod/tier3_collision_live.asm`.

## Phase 2 — 2a GPU triangle draw (DONE 2026-06-25)
**Custom flat-shaded triangles render into the ABL gameplay frame.** Reused the existing GPU-injection toolchain
(`tools/abl_starry.py` + `tools/abl_night_hook.py`): the debugger can't write VRAM/MMIO, so the PS1 CPU itself
issues GP0 via a **GPU DMA linked-list** (`build_linked_list` → ch2 `CHCR=0x01000401`). Added the **triangle
primitive: GP0 `0x20`** = `[ (0x20<<24)|colour, (y0<<16)|x0, (y1<<16)|x1, (y2<<16)|x2 ]` (verified — magenta/
green/blue tris drew correctly).

**Critical gotcha — buffer targeting.** ABL double-buffers in VRAM and the displayed buffer ALTERNATES; this save's
displayed rect (from `gpu.getStatus` → `crtc.vram_source_rect`) was **(512,264,1023,488)**. First attempts drew
into the *back* buffer (not the captured one) → nothing visible. Two working modes:
- **Frozen one-shot (used for 2a, deterministic):** `Starry.run_words` — read the live `vram_source_rect`, set
  `e3/e4=area`, `e5=(L,T)` offset, draw into the *displayed* buffer, mask IRQs + spin so no flip/re-render wipes
  it, then `captureFrame`. Perfect for screenshots/validation.
- **Per-frame persistent (for 2b+):** the `abl_night_hook` trampoline at `0x80062d04` (after the frame driver's
  render-OT) must target the **back** buffer (opposite of `[0x8008240c]`) so it flips to display next frame — that's
  how the mesh will persist + track the camera. Now that we know the rect alternates x0↔x512 (y264), back-buffer
  targeting can be done correctly.

**Next (2b):** project the collision-mesh triangles (world coords) through ABL's live camera (GTE /
`gpu.getCameraTransform`) and draw via the per-frame hook, so the platforms/ramp/gap render *where Flik walks*.
Source for the spike: inline in the session script; tris use the `abl_starry` helpers + the GP0-`0x20` builder.

## Phase 2 — 2b camera projection (DONE 2026-06-25) — the collision mesh renders IN-WORLD
**Solved by reusing prior camera RE** (`tools/trace_camera_transform.py` / `transform_math.py`). The camera =
two pieces, both readable in RAM:
- **Rotation R** (with the baked 1.6× zoom; det ≈ 1.598): the GTE `control.rotation_matrix.raw` captured at the
  **world-space draw `0x80010718`** (`fcn.80010000` post-RTPT — there the GTE rotation IS the pure world→view, no
  object rotation). Raw e.g. `[[91,0,-6553],[-2797,2988,-39],[2988,2797,41]]`.
- **Camera world position C** = the 3×s32 at scratchpad **`0x1F800374`** = `(-22773,-126648,202187)` (above + beside
  Flik, same Z — a plausible look-down follow-cam). (Sibling `0x1F8003B4` = the zoom matrix `diag(1.6,1,1)`.)

**Projection (matches the GTE's own `screen_xy_fifo` exactly):**
`view = R·(V − C)/4096 ; sx = H·view.x/view.z + OFX ; sy = H·view.y/view.z + OFY` with H=160, OFX=256, OFY=120.
Flik → `(258,183)` (centre-x, lower third — correct for the look-down cam).

**Result:** projected the collision mesh (A flat / ramp / B flat) and drew it via the 2a frozen one-shot — it
renders **in-world, perspective-correct**: green platform A in front, yellow ramp, cyan platform B receding to the
horizon, laid on the ground around Flik. **`build/spike2b_mesh.png`.** The world→screen pipeline is proven end to
end (collision-mesh world coords → ABL camera → on-screen, aligned).

**Per-frame TRACKING — confirmed (2026-06-25).** Drove Flik forward through 3 poses (X −4667→−697→9745); at each,
re-read the live camera (R at `0x80010718`, C at `0x1F800374`) and re-projected the **fixed world-coord** mesh. The
platforms stay glued to the world — they approach and pass as Flik walks, and quads clip out as they go behind the
camera. Frames `build/spike2b_track_0/1/2.png`. So the world→screen transform updates correctly every frame; the
mesh is locked to world space, not the screen.

**Remaining for full 2b (productization, not blocked):** the tracking demo re-projects host-side per pose (capture
camera → project in Python → frozen draw). The autonomous version does the RTPS **in the cave** each frame (reuse
`0x1F800374` + the world-draw R via the GTE) and draws via the 2a back-buffer hook — so it tracks live without host
intervention. The transform + projection + draw are all proven; this is wiring them into the per-frame cave.

## Phase 3c — native suppression (PARTIAL, 2026-06-25)
Goal: stop the native world fighting our collision (unblock 1f) + blank the native render. **Collision half
started; it surfaced the real remaining blocker.**

### 3c.2 — native geometry BUILD removal = the real fix + the level-replace goal (CURRENT WORK, 2026-06-26; APPROACH VALIDATED 2026-06-27)
**VALIDATED (live poke):** neutering `fcn.80010000` (the native DAT ground emitter) → `jr ra` kept the render
code intact across ~1440 frames of turning to face the native level — **NO crash**, native ground removed, Flik +
custom platforms + objects intact. So the build-removal strategy works; the ground (`fcn.80010000`) was the
primary high-RAM flooder. Remaining for a *fully* clean view: also neuter walls (chunk-35) + native objects
(cosmetic, not crash). TODO = bake the `fcn.80010000` neuter into the disc, GATED to LEVEL01 (EXE zero-run space
is tight for a gated stub; self-mod needs FlushCache on the real disc). Detection gotcha: pc<0x10000 ≠ crash
(normal BIOS syscall transit, ExcCode 8); real crash = render code corrupted / pc pinned / RI|DBE|AdEL.
**Why this is now the priority.** After the load-delay fix the cold-boot level plays — but **turning Flik to
face the full native level crashes** (RI exception, `COP0_EPC=0x801F0200` = our render code, overwritten with
OT/primitive data). Root cause: **the game's native geometry build floods ALL of high RAM** (sentinel scan:
every region `0x1b4000`–`0x1f8000` overwritten under a busy view) and writes right over our render code. There
is **NO free resident home in high RAM** under load, so "just relocate the render" does not work.

**Key realization (operator-led): the crash fix and the END GOAL are the same task.** Our current "suppression"
only collapses native terrain in the **ordering table AFTER the game already built + buffered every primitive** —
that buffering is what floods RAM, so it's a cosmetic mask, not removal. The real fix is to **stop the game
BUILDING the native geometry** (neuter the geometry-submit calls). That simultaneously: (a) stops the high-RAM
flood → our render code stays intact → **kills the turn-around crash** (and likely the butt-slam crash), and
(b) truly removes the native level → the clean full-custom view we want. So **build-level native-geometry removal
IS "replace the level."**

**We do NOT need to decode the native geometry FORMATS for this.** Tier-3 bypasses the formats by design. To
*remove* native geometry we only need the **submit functions** (function-level), which the G-series geometry work
already mostly identified: visible terrain/floor = **`fcn.80010000`** (DAT-backed, confirmed by edit→deform);
walls = chunk-35 (submit fn has some unresolved tension vs the Flik-draw fn — pin it). Custom terrain detail
(subtle bumps etc.) is later, authored in Blender, bounded by the renderer's (software-clipper) triangle budget —
NOT a prerequisite, and may need the GTE-hardware render path for high fidelity. Importing/replicating the native
terrain would need the format decode → only relevant to the *other* (sector-editor) track, skip it here.

**Plan:** (1) pin the COMPLETE set of native geometry-submit calls in LEVEL01 (write-watch who floods
`0x801F0000`; cross-ref `fcn.80010000` + walls) — neuter ONLY terrain/level geometry, keep Flik/objects/HUD/camera;
(2) re-measure high RAM quiets down around the render code + the turn-around crash is gone; (3) confirm
Flik/objects/HUD render intact. OPEN sub-question: is the flood the per-frame primitive BUILD (neuterable) or
streaming-on-look (harder)? The repro (small *turn*, then crash — no big movement) points to per-frame build.
This properly completes Phase 3c (build-level, not OT-cosmetic) and unblocks Phase 4 (Blender exporter).

**Native COLLISION suppression — works for FLAT surfaces.** Two native sources of the floor:
1. **Per-sector flat floor** = runtime sector table `0x800a7e48` (187 sectors, stride 0x30, origin-Y @+0x04,
   range −238496..10848). Set every sector's Y **below the whole mesh** (−80000) → native settles Flik below our
   floor → our clamp lifts him to the mesh. Result: flat platforms **A and B now track exactly** (B floated before).
2. **Swept planes** (ramps/walls) = `FUNC_800345CC`, count at `[gp+0x57c]` (gp `0x80081d98` → `0x80082314` = 6 in
   LEVEL01). Zeroed it — but that did NOT change the ramp (planes weren't catching Flik on our ramp).

### FLOOR-QUERY BUG ROOT-CAUSED **AND FIXED** (2026-06-25) — two bugs: a real overflow + the clamp model
**TL;DR:** found Flik's vertical velocity in RAM, root-caused the "ramp float" to **two** distinct bugs, fixed
both; the ramp now tracks perfectly. Cave updated (`mod/caves/tier3_collision.c`).

**Bug 1 — `edge_xz` 32-bit OVERFLOW (the real "floor-query bug").** The point-in-triangle cross-products are
~3e9, which overflow int32. The source used `(long long)(bx-ax)*(pz-az)` expecting a 64-bit widen, but the
compiler **truncated** it (objdump: 8 `mult` but only 6 `mfhi` — two products read `mflo` only). For ramp
triangle 3 the truncation flipped a cross-product's sign → false NO_FLOOR → Flik fell through the ramp. (Platform
A's products are even bigger but happened to wrap to the *correct* sign — which is why A worked and the ramp didn't,
masking the bug.) **Fix:** scale each delta `>>4` before multiplying (`((bx-ax)>>4)*((pz-az)>>4)…`) → products
~5e7, safely int32, no 64-bit / `__muldi3`, sign preserved. **Ramp now tracks exactly** (−92252→−86173 graduated).

**Bug 2 — the clamp model (also fixed): VELOCITY-GATED SNAP.** Found **Flik's vertical velocity at `0x800A6530`**
(captured a held-X jump: 0 grounded, negative rising, ~0 at apex, positive falling — tracks the Y-deltas). The old
clamp snapped only when Flik was *strictly below* the floor, so the walking-bob drifted; a plain margin-snap killed
the jump (bob vs jump-takeoff indistinguishable by height). The velocity disambiguates: **`vy>=0` (grounded/falling)
→ snap to floor (within `GROUND_MARGIN`); `vy<0` (rising) → leave Flik (jump plays).** Result: A walks tracked, the
jump rises the full 15744.

**Native suppression still required (Phase 3c) + a SIGN gotcha.** The velocity-snap only lands Flik on OUR floor if
the native floor is *below* our mesh (else native catches him above it and he floats). Deepen the sector table
(`0x800a7e48` +0x04) to below the whole mesh. **−Y is UP**, so "below the mesh" = MORE POSITIVE Y (e.g. −70000 for a
mesh at −85578..−92578) — I burned a cycle setting −120000 which is *above* the mesh and launched Flik upward.

**Verified together (edge_xz fix + velocity-snap + native −70000):** A −92578 tracked; ramp −92252→−86173 tracked
exactly (full descent, every point); **jump lands cleanly** (peak −97738 → settles −85578; the earlier "lands high"
was just too short a window — it descends over ~30 frames). Platform B2 tracks, the hole falls correctly. So
**residual 2 (jump landing) is RESOLVED.**

**Remaining residual (1): the ramp→B1 seam.** Crossing X=30000 (ramp→B1), Flik dips below B1 for a ~8000-unit strip
(X≈30000–38000) — the query returns NO_FLOOR there — then recovers and B1/B2 track. This is puzzling: the math says
B1's triangle 5 contains those points (all three edge tests positive after `>>4`), and the *ramp* triangle 3 — which
has the identical ~2.2e9 cross-product overflow profile — works fine after the `>>4` fix. So it's an unpinned
compiled edge case localised to that one quad/seam, not a structural model problem (A, ramp, B2, hole, jump, walls,
death all work). Logged as a known minor artifact. Cave now: `edge_xz` scaled `>>4`, `FLIK_VY` (0x800A6530),
`GROUND_MARGIN`, velocity-gated snap.

### (historical phrasing below kept for the record)
**Original framing (it's the clamp model, not the query) — partly right, but Bug 1 was also real:**
Instrumented the cave with a per-frame debug buffer logging the read XZ, hit-triangle index, height, and
Y-before/after-clamp, drove the ramp, and compared to a Python replica of the exact query. Findings:

1. **The floor QUERY is correct.** Idle, every surface tracks (A −92578, ramp graduated, B −85578); the cave's
   hit-triangle index matches the Python replica. So the "NO_FLOOR while driving" framing was wrong — the geometry
   query is fine. (Caveat: the debug ring buffer had an off-by-shift, so trust post-frame Flik-Y + idle-vs-driving
   behaviour + the hit-index, not the logged height column.)
2. **The float is the 1f CLAMP model.** It snaps Flik down to the floor only when he's *strictly below* it
   (`y > yf`). While **driving**, native physics keeps Flik a few hundred units **above** the floor (a walking
   "bob"), so the clamp skips and he drifts up — exactly the float. Flat B tracks (he settles below it); A/ramp
   float (he rides slightly above while walking).
3. **A ground-margin snap fixes walking but KILLS the jump.** Snapping when `y > yf − 3000` tracks walking, but the
   walking-bob and the jump *take-off* are both "slightly above the floor" — indistinguishable by HEIGHT alone.
   Tested: margin 3000 capped the jump at ~2300 (vs the real 6336) — Flik gets snapped back before he can rise.
4. ⇒ **The clean fix needs ABL's vertical VELOCITY / grounded-vs-jumping STATE**, not height: snap to the floor
   when grounded/falling, leave Flik alone when he's rising (a jump). That's a focused RE find (Flik's Y-velocity
   or the native grounded/jump flag — ABL already computes them for its own jump). With that, walking + descents
   track AND jump/butt-slam are preserved — no native suppression needed for it.
5. **Residual:** even margin-snap left the *early ramp* (X≈10000–20000, the A→ramp transition) floating one stretch
   → consistent with the cave reading a **transient mid-integration XZ** on a few frames there. Secondary to (4).

So Phase-3c native-COLLISION suppression is proven for flat surfaces, but the keystone for full tracking is the
**velocity-gated snap** (find Flik's jump/grounded state), which also removes the need to deepen the sector table.

**Operational notes (cost real time):** (1) `writeMemory` of ~9 KB at once **crashes the instance** — chunk large
writes (≤~1.5 KB worked). (2) cc5 destabilises after a long session of loadStates + frozen-spin draws — **relaunch
fresh** when calls start resetting the connection.

### 3c update (2026-06-25): native COLLISION suppression now SELF-CONTAINED in the cave
The cave does its own suppression each frame (`tier3_suppress_native`): zero the plane count (`0x80082314`) + set
all 187 sector floors to `NATIVE_DEEP`=−40000 (below the mesh AND below the death plane). **Verified with NO
external pokes** (cave + hook only): A tracks, ramp tracks the full descent, **gap → fall → respawn fires**, jump
works. So the collision engine is **disc-ready** (no live pokes needed on a booted disc). Known residual unchanged:
the ramp→B1 seam (Flik sinks through B1 ~X30000–38000). Committed.

### 3c render-suppression (blank native terrain): ATTEMPTED, needs proper RE
Goal: hide the native dirt so only the custom mesh shows. The vault's terrain-draw notes are **contradictory and
wrong here** — neutralising `fcn.80010000` (jr ra) did NOT remove the visible ground, and neutralising
`fcn.800172dc` changed nothing visible (and didn't drop Flik). So the real terrain draw is elsewhere. **Next:** use
`gp0Trace` to capture the display list and identify the terrain primitives (the big textured `GP0 0x3C`/`0x2C`
quads), then trace back to the emitting code to NOP it — or, simpler, have the custom render pass draw an opaque
full-cover background behind the mesh (but that also covers Flik unless drawn before his sprite). Deferred — it's a
focused terrain-draw RE, not a quick poke.

## Proven facts to build on
- Flik floor-Y committed by the movement integrator `FUNC_8003633C` (writers `0x80036384/0x80036cf0/0x80036d58`,
  commit `0x80036cec`); native floor source = collision (per-sector origin-Y + swept planes `FUNC_800345CC`).
- Code-cave + `armips` + disc-build pipeline (mod/build.py); GPU injection (starry-night).

## 2026-06-25 — Phase 1 collision DONE on a cold-boot disc (Flik walks the custom mesh at the real spawn)
**Result:** Flik cold-boots LEVEL01, spawns on, and walks a custom Tier-3 collision platform — `Y` pinned to the
custom floor while `X/Z` move freely. Disc `build/ABL_tier3_collision.{bin,cue}`.

**Root cause of the prior "stuck above the platform / death loop":** the test-mesh Y was simply wrong. The TRUE
LEVEL01 native spawn is **(197091, ~2734, 492897)** (verified by booting the *pristine* disc via the movie and
reading `0x800a6500`; the old 1a value Y=172615 was a misread). The platform sat at 162615 — ~160000 units away —
so the velocity-snap never engaged and the cave correctly left Flik on the native ground. Not a disruption, not a
real death loop.

**Fix:** `mod/gen_tier3_mesh.py` → `CX,CY,CZ = 197091,2734,492897`, `RAISE=3000` → platform A at `Y = CY−RAISE =
−266` (3000 above native ground; −Y is up). Cave already disc-fit (PREV scratch → `0x800814A0` inside the ~1033 B
zero-run; walls/native-suppression gated behind `TIER3_NWALLS`/`TIER3_SUPPRESS_NATIVE`; 720 B). Commit `5104623`.

**Fast-iteration loop (operator's idea):** boot the pristine disc to the spawn once → `emulator.saveState`; then
`loadState` + live-inject the 720 B cave at `0x800810C0` + write the one-word hook `0x08020430` (`j 0x800810C0`) at
`0x800495d0` → iterate with NO reboot. Confirmed live AND on the cold-boot disc.

**Nuance:** the hook sits on the movement integrator `FUNC_8003633C`, which the player runs only *when moving* → at
true idle the snap is skipped (Flik sits on native ground until the first step, then pops to −266). This also
explains the earlier "pauses right before walking up the hill." Keep `RAISE` modest so the first-step pop is small.

**Next:** smaller RAISE or an idle-snap for a seamless spawn; a gap/death walk-off demo; **Phase 2 render** so the
platform is actually visible (today it's an invisible floor over the native dirt).

## 2026-06-25 — Phase 2 render: custom platform is VISIBLE in-world (host-side per-frame)
**Result:** the corrected collision platform (flat, Y=−266) now **renders in-world as green ground** under Flik on a
cold-booted disc state — Flik (on the platform at −266) projects to screen-centre (256,199) and stands on the green.
Tool `tools/tier3_render_live.py` (commit `5253dac`). Frame `build/tier3_platform_visible.png`.

**Pipeline (host-side proof):** capture the live camera — R = `getGteState` `control.rotation_matrix` (decoded
floats; H=`projection_distance`, OFX/OFY=`screen_offset`) at a breakpoint on the world-draw `0x80010718`; C = 3×s32
@ `0x1F800374`. Tessellate the platform into a 12×12 grid, project (`view=R·(V−C); sx=H·vx/vz+OFX; sy=H·vy/vz+OFY`),
emit GP0 `0x20` flat tris for front-facing cells, draw via the `abl_starry` frozen one-shot.

**Key fix vs the 2a/2b spike:** *target the displayed buffer.* `run_words` freezes before the flip and the game's
draw offset points at the BACK buffer, so prepend `e3/e4/e5` (area + draw offset) = `crtc.vram_source_rect` (ABL
alternates the buffer origin (0,264)↔(512,264) per frame). Without it the tris land off-screen (invisible — the
first attempt showed only the native scene).

**Gotchas:** `run_words` corrupts instance state if run repeatedly (pc0 lands in a prior run's spin) and pre-driving
sends Flik flying — do ONE render per clean cold boot (a fresh movie boot already lands Flik at −266, no driving).

**Next (productization, not blocked):** autonomous IN-CAVE per-frame render — RTPS in the cave each frame (reuse the
world-draw R via the GTE + C @ `0x1F800374`) drawn through a per-frame back-buffer hook, so the platform persists in
live play / on the raw disc with no host intervention. Then 2c textures / 2d shading; smaller RAISE / idle-snap for
a seamless spawn.

## 2026-06-25 — Phase 2 AUTONOMOUS in-cave per-frame render (DONE)
**Result:** the custom platform now draws ITSELF every frame with **no host help** — it renders as in-world green
ground under Flik while the game runs normally. Cave `mod/caves/tier3_render.c` + trampoline
`mod/tier3_render_live.asm` + installer `tools/tier3_install_render.py`. Commit `838da50`. Frame
`build/tier3_render_autonomous.png`.

**How:** hooked per-frame at **0x80062d04** (after the frame driver's render-OT — the abl_night_hook site). Each
frame the C cave: (1) reads ABL's live camera from RAM — **R** (9× int16, /4096) @ `0x80090FB0` (verified to track
the camera) and **C** (3× s32) @ scratchpad `0x1F800374` — so no GTE/timing dependency; (2) projects the flat
platform in int32 fixed-point (deltas `>>4` before the R-multiply keep products+sums in int32 → no `__muldi3`;
perspective divide is native 32-bit → no `__divdi3`); (3) builds a GPU DMA linked-list and kicks ch2 after a
DrawSync of the game's OT DMA → draws into the current **back buffer**, redrawn every frame.

**Trampoline:** saves all caller-saved regs on the **stack** (NOT k0 — the frame driver uses k0; clobbering it froze
the game) around the C call, then replays the displaced `addiu a3,s2,14` and resumes at 0x80062d0c.

**Gotchas (each cost a build cycle):**
- Direct GP0-port writes **hang** while the game's GPU is in DMA mode (the cmd-ready bit never sets) → must draw via
  DMA linked-list.
- Drawing into **both** buffers tears (you write the front buffer mid-scanout) → single **back** buffer only
  (`[0x8008240C] & 0x20000`: bit set ⇒ displayed x0 ⇒ back x512, per abl_night_hook).
- Inheriting the game's draw offset (emitting no E5) draws nowhere visible → must set E5 to the back buffer.
- The boot movie **owns the controller** until ~150 settle frames (+ `movie.stopPlayback`/`clear`); the apparent
  "Flik frozen" was that, not the cave (proven by un-hooking — still frozen).

**Tracking:** the cave re-reads R/C and re-projects every frame, so the platform is world-locked (poking Flik
re-projects it correctly; the flat plane goes edge-on/thin when the camera looks near-horizontal).

**Next:** 2c textures / 2d shading; smaller RAISE / idle-snap for a seamless spawn; bake the render into the disc
(EXE-budget — the render cave is ~1.6 KB, too big for the 0x800810c0 zero-run, so it needs a larger free region or a
second cave slot, vs the live-RAM 0x801e0000 region used now).

## 2026-06-25 — Phase 3a: unified level blob (DONE)
**Result:** ONE binary level blob is now the single source of truth for BOTH caves — the collision floor query and
the renderer read the same triangles, so visuals + collision can never drift. Replaces the two separate hardcoded
meshes (old `gen_tier3_mesh.py`→`tier3_mesh.h` for collision; `#define` rectangle in `tier3_render.c` for render —
both removed). Commit `b34b4a8`. Frame `build/tier3_unified.png`.

**Blob** (`mod/gen_tier3_level.py` → `build/tier3_level.bin`, 81 verts / 128 tris, 4588 B; layout in
`mod/caves/tier3_level.h`, base **0x801D0000**):
- header @ +0x00 (8 words): magic `'T3LV'`, nverts, ntris, spawn x/y/z, death_y, flags
- verts  @ +0x20: x, y, z
- tris   @ +0x20 + nverts*12: i0, i1, i2, nx, ny, nz, color  (indices + precomputed plane normal + GP0 colour)

**Caves:** `tier3_collision.c` walks the blob's indexed triangles for the floor query (spawn + death-plane from the
header), guarded by an `LV_MAGIC` check so a disc with no blob loaded degrades safely (no custom floor, no crash).
`tier3_render.c` projects the blob's verts and draws its tris (per-tri colour). Installer
`tools/tier3_install_unified.py` writes the blob once and points both caves at it.

**Verified live on the disc:** Flik settles to the blob's platform Y (−266) via blob-collision AND the platform
renders from the same blob. Gotcha: editing the blob live vertex-by-vertex (81 round-trips) times out — write it in
512-B chunks.

**Next:** **3b** loader — read the blob from disc to RAM at level-load, or bake it into a resident region (the EXE
zero-run at 0x800810c0 is far too small for a ~4.6 KB blob, so this needs a real loader / a free RAM region claimed
at boot). **3c** render-suppression — blank the native terrain (still needs `gp0Trace` RE). Then Phase 4 (Blender
exporter) emits this blob.

## 2026-06-25 — Phase 3c render-suppression: INVESTIGATED (not yet solved)
**Goal:** blank the native terrain so a custom level looks fully custom. **Finding:** the entire 3D scene is drawn
by ONE DrawOTag-style call — `0x80062cfc jalr → 0x800646b8` — over a **64-bucket ordering table @ 0x801E1368**
(args a0=ctx, a1=OT, a2=0x40 count, a3=0x801E138C; same 0x801E1xxx region as the drawenv 0x801E134C / back-buffer
bit 0x20000). NOP'ing `0x80062cfc` blanks the WHOLE frame to sky-blue — terrain **and** objects **and** Flik all
vanish — so terrain + objects are interleaved by depth in one OT, not a separable draw call. RE in
`src_re/world_render_dispatch.c` (commit pending push).

**Ruled out** (the old "blank it" leads were wrong): early-return `fcn.80010000` / `fcn.800172dc`, and zeroing the
runtime mesh buffer `0x8012c000..0x80130000` — all leave the terrain intact. `gp0Trace` captures **nothing** (the
game renders via GPU DMA OT, not direct GP0 writes). The Tier-3 render hook `0x80062d04` composites *after* this
draw.

**Path to a clean solve (deferred — involved):** either (a) walk the 64 OT buckets and unlink the terrain
primitives (classify each by texpage: dirt vs sprite), or (b) find the static terrain OT-insert (built at level
load) and suppress it, leaving the per-frame object inserts. Next concrete step = an OT-walk + texpage
classification pass. All probe edits were reverted after each capture.

## Phase 3c — PLAN (2026-06-25) + execution
**Goal:** blank the native terrain (dirt/grass/walls) so only sky + the custom level + Flik/objects show. The whole
scene is one 64-bucket OT @ `0x801E1368` drawn by `0x800646b8` @ `0x80062cfc` (terrain + objects interleaved), so
the solve is surgical, not a single NOP. Plan:
1. **Map the OT** — walk the chain from the DrawOTag head, parse each primitive (tag len + GP0 words), tally by GP0
   command + active texpage (`E1`). Output = primitive inventory + the primitive-buffer location.
2. **Find the terrain builder** (preferred, option b) — `accessLog` write-watch the primitive buffer for one frame
   → the PCs that assemble terrain prims vs object prims → the terrain OT-insert function.
3. **Pick the discriminator** — texpage (dirt vs sprite) and/or builder PC and/or OT bucket range that cleanly
   separates terrain from objects.
4. **Prove suppression live** — unlink the terrain prims (or NOP the terrain builder); confirm terrain blanks while
   Flik/objects survive.
5. **Implement as a cave** — per-frame OT-filter (hook before `0x80062cfc`, unlink terrain) OR one-shot NOP of the
   terrain builder; co-exists with the Tier-3 render cave.
6. **Integrate + verify** — final look = sky + custom platform + Flik; commit + document.

### 3c execution status (2026-06-25) — render MAPPED, builder narrowed, clean blank NOT yet achieved
Did steps 1-2 of the plan. **Mapped:** DMA kick `0x80064618` (MADR=a0 → a0@entry = OT head), called per-frame for a
1-node drawenv OT (`0x801E1368`) + a **double-buffered scene OT** (`0x801E282C`/`0x801CD870`, ~2050 nodes, ~810
textured polys). **Finding that redirects the plan:** ~all 810 polys share **one texpage 0x8D** (terrain AND
objects) → texpage can't discriminate; need the builder PC. **Found a builder:** the loop `0x80013388..0x800135A8`
(52-byte textured-quad nodes, OT-link `sw t4,0(t9)` @ `0x8001358C`). **But** no suppression blanked the visible
dirt (early-return `0x80008E98` / `fcn.80010000` / `fcn.800172DC`, NOP `0x8001358C`, zero `0x8012C000`) → the
on-screen ground has another/additional build path. RE: `src_re/world_render_dispatch.c`. **Next:** correlate each
builder's emitted prim screen-XY to the visible ground (or bisect by zeroing prim coords) to find the dirt builder,
then NOP it. Multi-session research task; tooling (paused OT-walk + per-prim write-watch) is in place.

### 3c — OT-filter cave built; native terrain/objects proven ENTANGLED (2026-06-25)
Built a **reliable per-frame OT editor** (`mod/caves/tier3_otfilter.c` + `mod/tier3_otfilter_live.asm` →
`build/cave_otfilter.bin`; installer `tools/tier3_install_otfilter.py`; commit `63a14fe`): hooks the DrawOTag DMA
kick `0x80064618` (OT head in `a0`), walks the exact OT about to be drawn, and recolors/collapses chosen prims
every frame — sidesteps the double-buffer/captureFrame-timing confound that made host edits unverifiable.

**Result (settles 3c's core question):** native terrain and objects are **ENTANGLED**. Recoloring all `0x3C` prims
turns the WHOLE scene red — terrain, props, AND Flik are all gouraud-textured `0x3C` quads on texpage `0x8D`. A
screen-area threshold can't separate them (ground = many medium quads overlapping Flik's quad sizes; THRESH 900 →
all red, 6000 → almost none). So **texpage, GP0 command, and prim size all fail as discriminators** — the only clean
separator is the **builder function**. A terrain-only blank that preserves Flik needs **builder-level prim tagging**
(hook the terrain builder to mark its prims, then collapse marked prims via the OT-filter). The ground builder isn't
cleanly isolated yet (early-returning `0x800186f0` / `0x80013388`'s loop didn't blank it). The OT-filter tool +
write-watch tooling are in place for that next step.

### 3c SOLVED (2026-06-25) — native foreground terrain blanked, Flik + objects preserved
The OT-filter now suppresses the native FOREGROUND terrain while keeping Flik and the dynamic objects
(`build/tier3_terrain_blanked.png`; commit `159bc86`). Two findings unlocked it:

1. **PS1 INSTRUCTION CACHE (critical, project-wide gotcha):** patching the *hot* hook site `0x80064618`
   via `writeMemory` does NOT take effect — the CPU keeps running the **stale cached instruction**, which
   *silently defeated every earlier suppression test*. FIX: after writing the hook word, toggle an
   execute breakpoint at the address (add → resume-to-hit → remove) to force an I-cache re-fetch. (On a
   fresh boot the injected cave code itself isn't cached yet, so only the hook site needs flushing.)
2. **Discriminator = prim OFFSET in the scene OT.** texpage / GP0 command / prim size all fail (terrain +
   Flik are all gouraud-tex `0x3C` quads on texpage `0x8D`, overlapping sizes). But **dynamic objects
   (Flik, enemies, props) are built LOW in the prim buffer (~OT_head + 0x160..0x500) and the foreground
   terrain mesh HIGH (~OT_head + 0x6000+)**, so `GATEOFF` collapses only prims with `(addr-OT_head) > gate`.
   `GATEOFF 0x3000` = foreground terrain gone, Flik + objects fully intact.

`mod/caves/tier3_otfilter.c` (runtime flags MODE @0x801E00F0, ATHRSH @0x801E00F4, GATEOFF @0x801E00E0)
+ installer `tools/tier3_install_otfilter.py` (sets flags + does the I-cache flush). **Remaining:** the
background grass/horizon/wall is a SEPARATE draw layer/OT (blank via the same trick on that OT); and a
builder-tag would be more robust than the offset heuristic for a shipped disc.

## NEXT SCOPE — "Visible custom platform you can boot/load and play" (render-cave hardening) — 2026-06-25
**Goal / exit criterion:** a single shippable artifact (cold-boot disc OR save state) where you start the game,
reach LEVEL01, and **see Flik standing on the drawn custom platform and walk it** — collision + render together,
no debugger. Today collision ships (cold-boot disc `build/ABL_tier3_collision.cue`) and the render is *proven*
(`build/tier3_render_autonomous.png`) but the two aren't packaged into one boot/loadable artifact.

### Why it isn't shipped yet (the 3 blockers found this session)
1. **Render near-plane CULLING → gaps.** `mod/caves/tier3_render.c` drops any triangle with a vertex behind the
   camera (`vz<=0`). A platform CENTERED on Flik straddles the camera plane → big gaps; it only looks clean when
   the platform happens to extend in front of him.
2. **Render hook vs input.** Collision-only boots are drivable; adding the render hook (`0x80062d04`) leaves Flik
   unresponsive. Cause not isolated (frame-hook may disturb the input/frame path).
3. **Camera framing depends on cold-spawn.** The follow-cam only aims at the platform height (Y=−266) when Flik
   COLD-SPAWNS there; poking/walking him up leaves the camera aimed at the native ground → platform off-screen-top.

### Tasks (do in order; each independently verifiable with pickObject + a capture)
- [x] **T1 — Near-plane CLIP the render. DONE 2026-06-25** (see "T1+T2 session" below). `mod/caves/tier3_render.c`
      now does near-plane (view-space) **and** 4-edge screen (2D) Sutherland-Hodgman clipping in fixed-point (no
      `__muldi3`/`__divdi3`; shift-reduced intersection ratios). PROVEN correct: a host-side float replica + an
      in-cave VRAM scan both render the platform gap-free **from the cold-spawn straddle camera where the old
      whole-tri-cull drew NOTHING** (35782/78647 exact-green VRAM px).
- [~] **T2 — Render hook input-safe — RESOLVED (with a real nuance).** The earlier "0x80062d04 kills input" was the
      **boot-movie controller confound** (the movie owns the pad through the settle window) — with the hook installed
      from a movie-RELEASED anchor, Flik is fully drivable (verified, all 4 dirs). BUT a *screen-filling* render
      throttles game logic ~10x via emulated **GPU-FILL** time (the game loop is render-gated); the old cave only
      escaped it by drawing little. ⇒ the separate-DMA render has a fill ceiling; insert prims into the game's OWN OT.
- [ ] **T3 — Mesh that fits + scratch correctness.** Keep ≤49 verts/72 tris (GRID 6) so projection scratch fits the
      free BSS (PSX/PSY/PVZ ≥0x200 spacing — the 0x100-overlap bug is FIXED). Confirm no OT-region conflict.
- [ ] **T4 — Package a clean SAVE STATE (primary delivery).** On the PRISTINE disc: cold-context where the camera is
      already at −266 (drive Flik on so the follow-cam tracks, OR start from the collision disc's coldspawn), inject
      collision+render+fine-blob into free RAM, `saveState`. **Reload it fresh and verify visible + playable.**
- [ ] **T5 (optional) — Disc-bake the hardened cave.** If T1–T3 shrink the render enough OR via a disc-file loader
      to high RAM at level-load, bake render onto the cold-boot disc (the proper Phase-3b loader). Until then the
      save state is the delivery.

### Known-good substrate to build on (don't re-derive)
- Camera: R @ `0x80090FB0` (live, tracks), C @ scratchpad `0x1F800374`; projection `view=R·(V−C)/4096; sx=H·vx/vz+OFX`
  (H=160, OFX=256, OFY=120). Blob format + `TIER3_LEVEL_BASE` in `mod/caves/tier3_level.h`. In-gameplay gate =
  `[0x80082498]==0x801607F8`. Render draws into the back buffer (`[0x8008240C]&0x20000` selects it). I-cache: live
  code patches now auto-invalidate (no breakpoint-toggle). Builders/RE in `src_re/world_render_dispatch.c`.
- 3c (blank native terrain) is SHELVED — no render-side discriminator separates terrain from Flik; not required for
  this scope (the custom platform just draws on top of native terrain).

## T1+T2 session — near-plane+screen CLIP done, render-integration ceiling found (2026-06-25)
Drove the NEXT-SCOPE blockers on a fresh isolated instance (port 23470, cold-boot of
`build/ABL_tier3_collision.cue`), anchored at LEVEL01 via the `flik_to_level01_stall` movie + a saved state
(Flik cold-spawns on the custom collision platform at **Y=−266** — collision disc CONFIRMED working live).

**T2 — render hook is input-safe; "kills input" was the MOVIE confound.** Installed the render cave + hook
`0x80062d04` from the movie-RELEASED anchor and Flik drove in all 4 directions (Δ matches the no-hook baseline).
The prior "unresponsive" was the boot movie owning the controller through the ~150-frame settle window — the SAME
confound the autonomous-render gotcha already flagged. So the hook itself does not kill input.

**T1 — near-plane + screen clipping, DONE + PROVEN.** Old `tier3_render.c` culled any tri with a behind-camera
vertex (`vz<=0`); at the cold-spawn follow-cam the camera sits INSIDE the platform footprint (C≈(220111,−14480,
475112) within X[127k,267k]×Z[432k,552k]) so 3 of 9 blob verts are behind it → every tri touching them culled →
nothing drew (diagnosed by projecting the blob: verts 1/6/7 `vz<0`, vert 8 `vz` tiny → off-screen blow-up).
Rewrote the cave to clip: (a) NEAR plane in VIEW space (`vz>=NEARZ`, edge-split), then project, then (b) the 4
SCREEN edges in 2D (exact line intersections). All fixed-point — deltas `>>4` before multiplies, and clip-edge
ratios use a **shift-reduced** `frac=(num<<10)/den` (reduce num,den `<0x4000` first) so even ~1e6 far-off-screen
projected coords stay int32. No `__muldi3`/`__divdi3` pulled (verified `nm`). Validated three ways:
1. host-side float replica (scratch `proto_clip.py`, `abl_starry.run_words` frozen one-shot) → clean green platform
   under Flik at the straddle camera (`proto_clip.png`);
2. an exact integer replica of the cave math → 12 valid on-screen tris (e.g. `(60,239),(255,198),(0,181)`);
3. the in-cave version: WBUF/LBUF hold those exact tris and a well-formed DMA list, and a post-DMA breakpoint
   VRAM scan finds **35782** exact-platform-green px (0 before); both-buffer draw presents **78647** px in the
   live frame. The platform renders gap-free, world-locked. (NEARZ=64; PVX/PVY/PVZ `0x80083000/100/200`.)

**The render-integration ceiling (reframes the render path).** Two live issues, both about the *separate per-frame
DMA*, NOT the clipping:
- **GPU-FILL THROTTLE (~10x):** drawing the screen-filling platform stalls the game's render-gated main loop
  (held-Up over 30f: baseline 12552 → clip-cave 1329). Async DMA (drop the spin-wait) does NOT help → it's the
  emulated GPU FILL, not the CPU spin. The old cave only escaped it by drawing little/nothing (and the operator
  POKED Flik rather than driving, so never saw it). A big custom ground plane via a side DMA is fill-bound.
- **BUFFER PHASE:** the hook fires AFTER the flip, so a single-back-buffer draw lands in the *future-back* buffer
  (re-rendered before it displays) on a save-state anchor → green sits in VRAM but never presents. Drawing into
  BOTH buffers presents reliably but draws OVER Flik (no depth) and worsens the throttle. (On a fresh cold boot
  the phase aligned for the operator's `tier3_render_autonomous.png`; on a loaded state it doesn't.)
- **NO DEPTH:** the platform composites on top of the whole native scene (covers Flik) until Phase 2d / 3c.

**⇒ Reframed next step (supersedes T4 save-state-of-the-separate-DMA-render):** stop drawing via a separate
throttling DMA. **INSERT the clipped platform prims into the game's OWN ordering table** — reuse the 3c OT-filter
cave (`mod/caves/tier3_otfilter.c`, hook `0x80064618`, already walks/edits the live OT) to ADD our tris at the
right OT bucket. That removes the extra DMA (no fill throttle, no buffer-phase race) AND gives depth compositing
(platform behind Flik) for free. The clipping (T1) is the reusable front-end; the OT-insert is the new back-end.
Cave kept single-back-buffer + sync DMA (canonical, input-safe at light fill); both-buffer was a debug detour.

## OT-INSERT render — MILESTONE: Flik visibly stands on + walks the custom platform (2026-06-25)
Acted on the reframed render path from the T1+T2 session: stop drawing via a separate throttling DMA;
**INSERT the clipped platform prims into the game's OWN ordering table.** It works — the NEXT-SCOPE exit
criterion is met live: **Flik renders standing on the drawn custom green platform and walks it, drivable,
collision + render together** (frames `build/` reload capture; deliverable save state
`build/ABL_tier3_visible_otrender.sav`).

**Cave:** `mod/caves/tier3_otrender.c` + trampoline `mod/tier3_otrender_live.asm` → `build/cave_otrender.bin`;
installer `tools/tier3_install_otrender.py`. Same hook as the 3c OT-filter — the **DrawOTag DMA kick
`0x80064618`** (`a0` = OT head). Each frame the cave: (1) projects + NEAR/SCREEN clips the shared level blob
(the SAME proven fixed-point clipper as `tier3_render.c`); (2) builds each output tri as one OT NODE
(`tag=(4<<24)|next`, then GP0 `0x20` flat-tri words); (3) links the platform chain into the OT and **returns
the new head in v0**, which the trampoline writes back into the saved `a0` slot so the DMA's `MADR=a0`
(`0x80064638`) starts from our chain.

**Modes (runtime flags @ `0x801E00D0` MODE / `..D4` SUPPRESS / `..D8` GATEOFF / `..DC` sentinel):**
- **PREPEND (MODE=1, used):** platform drawn FIRST (background); the game's scene draws over it, so Flik +
  objects composite ON TOP → correct depth for free. Never walks the game's chain → no cycle risk.
- **SUPPRESS=1:** collapse native FOREGROUND terrain (the 3c GATEOFF offset gate, ported in) so the green
  platform becomes the visible GROUND instead of being hidden behind dirt. GATEOFF=0x3000.
- **APPEND (MODE=0): documented HAZARD — do not use.** Walking to the OT tail and appending makes the next
  frame's walk re-find our own nodes → `tail.next = node0` cycle → DrawOTag DMA infinite-loops → GAME HANGS
  (observed: pc stuck in 0x80064xxx, sentinel frozen at 4). Prepend sidesteps it.

**Why this is the right back-end (all the side-DMA problems gone):**
- **No throttle:** drawn by the game's own DMA, no separate DMA / DrawSync spin. Input is drivable
  (held-Up 30f ≈ 6800–8540 vs the side-DMA's throttled 1300; baseline ~11000 — the residual ~25-40% is the
  per-frame suppress + projection walk, optimisable).
- **No buffer-phase race:** our prims are in the game's buffer, so they present every frame (the side-DMA
  raced the flip on a loaded state).
- **Depth:** prepend + suppress puts the platform behind Flik with the dirt removed → Flik on top.

**Verified:** platform renders gap-free + WORLD-LOCKED across 3 walked/turned poses (Y pinned to −266 by the
disc collision the whole time); deliverable save state reloads to the milestone and stays drivable.

**Residuals (refinements, not blockers):** input ~25-40% slower (optimise the two per-frame OT walks / cache
the projection); the BACKGROUND grass/horizon band is a separate OT layer (untouched by GATEOFF) — suppress
it on its own OT for a fully-custom look; blob is the coarse GRID=2 flat platform (swap in a real level mesh);
the OT-insert cave is live-inject only (disc-bake needs the Phase-3b loader, like the render cave). Next:
optimise + finer mesh + background-layer suppress; then this becomes the render half of the shippable disc.

## OT-insert render — PERF: there is NO throttle (the "~25-40% slower" was a measurement artifact) + suppress optimised (2026-06-25)
Went to optimise the OT-insert render's apparent input throttle. **It does not exist.** Isolated the cost
with a debug skip-flag: full render, suppress-only, project+draw-only, and a PURE no-op hook ALL measured
the IDENTICAL Flik movement (16621 over 40 held-Up frames) -> the cost is not the cave body. Per-frame Flik
deltas show why: the game runs **30 Hz logic on 60 Hz video** (move, 0, move, 0, ...), and the hooked run is
the SAME movement sequence (299,281,264,250,...) merely **phase-shifted by ONE frame** from the live install.
Over a fixed window that one-frame offset reads as a deficit that shrinks as the window grows: ratio **0.88
@40f -> 0.98 @120f -> 1.0**. So the OT-insert render is **full game speed**; the earlier "~25-40% slower" /
"~12%" notes were wrong (a sampling artifact) -- corrected here and in `mod/caves/tier3_otrender.c`.

**Suppress optimised anyway (for scaling + cleaner output).** The terrain-suppress was ported from the 3c
OT-filter, which parsed every OT node's GP0 words to move each poly vertex off-screen. Replaced with a
**zero-length collapse**: for a terrain node (offset past GATEOFF) set its tag word-count to 0 (keep `next`)
so DrawOTag sends 0 words and skips it -- one classify + one conditional write per node, no per-vertex parse.
Scales cleanly as object/mesh counts grow (the per-node walk is the only O(N) left, and it measured free).
**Bonus:** dropping the whole node also removes the native BACKGROUND grass/horizon band (the per-vertex
move had left it), so the look is now **sky + custom green platform + Flik** -- fully custom, no native
geometry. Verified live: terrain (foreground AND background) gone, Flik renders intact + drivable + world-
locked, Y pinned -266. Removed the debug skip-flag (avoids an uninitialised-read footgun). Deliverable save
re-saved: `build/ABL_tier3_visible_otrender.sav`.

## REAL multi-feature level proven (engine works for an actual level, not a slab) — 2026-06-25
Authored a real **multi-feature test level** in the unified blob (`mod/gen_tier3_level.py`, rewritten
from the flat grid to hand-authored colour-coded quads) and verified the whole engine on it at once:
- **A** green flat slab (spawn) · **ramp** yellow (slope) · **C** cyan raised slab (top of ramp) · **B**
  magenta slab across a **GAP**. 12 verts / 8 tris / **400 bytes** (≤514 → still disc-bakeable into the
  in-image zero-run). Compact layout (H=15000) so features sit ~15-45k from spawn — a 40k-wide slab put
  them too far for the game's *curving digital steering* (Flik circled before arriving; not a wall).

**Collision — correct on every feature.** A Python replica of the cave's EXACT integer query (incl. the
`>>4` edge_xz) run on the live blob returns A=-266, ramp -3599→-10267, C=-20266, gap=NO_FLOOR. And LIVE:
Flik walks A flat (-266), then **walks UP the ramp** with Y interpolating the slope exactly (at X=222898,
ΔX=10807 onto the 0.4 ramp → Y=-4588, matches; climbed -266→-4806). So flats, slope interpolation, and the
unified blob all work on real geometry. (`build/` capture: Flik standing on the yellow ramp, tilted with
the slope, A green / C cyan / B magenta all visible behind/around him.)

**Render — all four features render together**, clipped + world-locked + depth-composited (Flik on top),
native scene fully suppressed (sky + custom level only). One blob feeds both collision and render, so they
cannot drift. Deliverable save state `build/ABL_tier3_richlevel.sav` (reloads to the level, drivable).

**Findings / limits surfaced:**
- **Probing by poking Flik's X/Z does NOT stick** (the integrator overwrites position each frame from
  velocity) — verify collision by DRIVING or by the Python-replica-on-live-blob method, not pokes.
- **Digital steering curves** (camera-relative heading rotates), so distant features are hard to reach in a
  straight line — keep test-level features within ~15-25k of spawn, or drive in short re-centred bursts.
- The custom collision overrides FLOOR Y only; Flik's XZ is still the native world. Within the native
  walkable area around spawn this is fine; a LARGE custom level would need native-XZ-collision suppression
  (Phase 5 integration) to roam freely — not hit here because the compact level fits the native area.
- Render stays live-inject; the 400-byte blob bakes into the cold-boot collision disc (collision cold-boots;
  render is the live half) -- rebuild via `tools/build_tier3_disc.py`.

## User playtest fixes — "stuck falling animation" ROOT-CAUSED + fixed (2026-06-25)
User play-tested the rich level (save states `ABL_looking_at_ramp_OG_Graphics.sav` / `texture_facing_ramp.sav`)
and reported: ramp/platform "pushes Flik back", and **jumping on the ramp leaves Flik stuck in a FALLING
animation** (he doesn't move, but flails as if falling), plus an **infinite jump** (X in mid-air re-jumps
instead of butt-slamming).

**ROOT CAUSE of the falling-animation (the main bug):** our post-physics clamp (`tier3_collision.c`) pinned
Flik's Y to the custom floor but **never told the game he landed**, so native gravity kept accumulating his
vertical velocity. Live trace: after a jump on the ramp, Flik's `vy` (@`0x800A6530`) ran away (1344→3904→…)
while X/Y/Z were held — so the game kept playing the falling animation, and the runaway `vy` would launch him
if he ever left a custom floor. The "pushed back / stuck" feeling was this same bug.

**FIX (committed `435452e`):** when the velocity-gated snap grounds Flik (`vy>=0` and within `GROUND_MARGIN`),
set `FLIK_VY = 0`. Verified live: jump on the ramp now rises, falls, and **settles with `vy`→0** (no runaway,
no stuck falling anim). **Delivered as live-inject save states** (work with the current disc, no rebuild,
existing saves stay valid): inject `build/cave_tier3.bin` (the fixed cave) over the baked cave @`0x800810C0` +
an I-cache flush, then `saveState` → `~/Downloads/ABL/ABL_tier3_VYFIX_facing_ramp.sav` and
`…_VYFIX_spawn.sav`.

**Still open (follow-ups):**
- **Infinite jump** — NOT fixed by the `vy` reset. It's gated by the game's own vertical **state machine**
  (player-struct halfwords @`+0x80/+0x82/+0x84`; per-frame `vy` updater @`0x80048d90`; the jump impulse goes
  through a STATE, not a direct `vy` write). Native-collision suppression (deepen sectors `0x800A7E48+0x04`→
  +40000, zero swept planes `0x80082314`) did NOT fix it (and didn't break the jump). Needs the jump-trigger
  grounded gate in the controller-X read path — deeper RE.
- **Native XZ collision still bounds the level** (a native plant stalk sits inside the ramp). Walking the ramp
  works (Flik climbs −266→−9k); zeroing swept planes didn't change the walk, so the "wall push" was mostly the
  falling-anim bug. A large free-roam level would still need native-XZ suppression.
- **Layout** — user wants the ramp IN FRONT of Flik at spawn. Spawn forward ≈ `(-X,+Z)`; the ramp is at `+X`
  (behind). Reorient `gen_tier3_level.py` toward the forward vector (curving digital steering makes straight-
  line nav fiddly — keep features close + wide).
- Colour legend (user read magenta as "red"): green=A spawn · yellow=ramp · cyan=C raised (ramp top) · magenta=B
  across the gap.

## Infinite mid-air jump FIXED (2026-06-25, commit f1b76b0)
User reported X-in-air re-jumping endlessly instead of butt-slamming. ROOT CAUSE (traced live): on our
custom floor the game's native grounded flag (`@0x800A6582`) is 0 even when Flik rests, so its GROUNDED
jump path never fires -- every jump goes through the mid-air **coyote** path, gated by
`[player+0x48] - Flik.Y < 1024` AND `[gp+0x69c] == 0`. Both come from the native floor-finder
(`0x800495dc`/`0x800495e4`), which is garbage/inconsistent over our floor, so the check passes in the air
too -> endless up-and-up.

**FIX:** a trampoline at the `[player+0x48]` store (`0x800495dc`) substitutes OUR floor.
`tier3_collision_hook` publishes the floor under Flik to `FLOOR_PUB` (`@0x800814B0`); the tramp, when over
our floor, writes `[player+0x48] = our floor Y` and `[gp+0x69c] = 0` (and skips the game's own
`0x800495e4` write). The coyote height check is then exact: grounded (`Y==floor` -> diff 0) jumps, mid-air
(`Y` far above -> diff > 1024) is blocked. Over a gap (`FLOOR_PUB == NO_FLOOR`) the native values stand.
(Freed the dead `PREV*` wall-resolve scratch for the tramp @`0x80081478`.) `mod/patch_tier3_collision.asm`.

**Verified (cold-boot disc):** repeated grounded jumps all work (apex −6602), the mid-air 2nd X no longer
re-jumps, walking/ramp/floor collision intact.

**KEY DEBUG LESSON:** live-injecting an updated cave OVER an already-cached cave runs the STALE code (the
emulated PS1 I-cache; `invalidateCodeCache` + a single trampoline-line breakpoint flush did NOT clear the
deeper function lines). Cave-LOGIC changes must be verified via a **cold-boot disc**, not a live re-inject.

**Residuals:** mid-air X currently no-ops (jump blocked) rather than butt-slamming; the gap still lands Flik
on the native floor instead of reaching the death plane (native-floor-in-gap coupling, pre-existing -> needs
native-collision suppression). Deliverables: `build/ABL_tier3_collision.{bin,cue}` (cold-boot, fix baked) +
`ABL_tier3_JUMPFIX.sav` (with render).

## Native-collision SUPPRESSION baked (free roaming + gap-respawn) — 2026-06-25 (commit 4753f96)
The custom floor overrode only Flik's Y; the native LEVEL01 world still owned collision, so a fall in one
of OUR gaps caught Flik on native ground (~+2595) instead of reaching our death plane (+29734) → no
respawn, and native walls could fight roaming.

**Fix (per-frame in `tier3_collision_hook`):** deepen every native sector floor (table `@0x800A7E48`,
187 × stride 0x30, origin-Y `@+0x04`) to **+40000** (−Y is up, so that's far below — past the death plane
`+29734`), and zero the **swept-plane count** (`@0x80082314`, native walls). 187 stores/frame, cheap, and
it fit the existing cave zero-run.

**Verified on a cold-boot disc (no save state, no live pokes):** Flik jumps, walks the custom floor freely,
and walking off a platform edge into a gap falls *past* the death plane (Y −266 → 26614 → …) and
**respawns at the level spawn**. The compact level keeps Flik in streamed sectors (no void-teleport crash).
(The swept-plane count was already 0 at the LEVEL01 spawn — the earlier "plant stalk in the ramp" was not a
swept-plane wall, so no extra wall-removal was needed there.)

**Deliverables now:**
- `build/ABL_tier3_collision.{bin,cue}` — cold-boots the full custom **COLLISION** (geometry + jump fix +
  free roaming + gap-respawn). Invisible (native visuals) — the render cave still has no boot-safe disc home.
- `ABL_tier3_FULL.sav` — that disc with the OT-insert render injected = **visible + playable** (suppression
  is baked into the disc, so only the render is live-injected). Load with the disc mounted.

Remaining: render-on-disc (needs the CD loader); butt-slam on mid-air X (user deferred).

## MILESTONE — RENDER-ON-DISC COLD-BOOTS (2026-06-26, commit a7176ec)

The visible custom level now **cold-boots from disc** (`build/ABL_tier3_render.{bin,cue}`) — collision +
render together, no save state, no live injection. This closes the long-standing "render is the live half"
gap. Three cold-boot bugs were root-caused and fixed (full detail + addresses in
[[Finding - Tier-3 render disc-delivery]] and auto-memory `tier3-render-disc-coldboot-hang`):

1. **Boot hang** — appending the blob to `LEVEL01/LEVEL.DAT` poisoned the native DAT parser's pointer at
   `0x8008239c` (writer `0x8001d384 sw v0,0x604(gp)`: `out_end−tail` read blob bytes → garbage
   `0x5f5afce0` vs pristine `0x801afba4`). Fix: blob no longer rides in LEVEL.DAT — it's bundled into the
   `TIER3.RND` CD file and loaded to high RAM. (`build_tier3_render_disc.py`)
2. **Loader self-skip** — the `fname` string overlapped the `COPIED` flag (`0x8007F300`) → `tier3_load_render`
   never loaded `TIER3.RND`. Fix: pin `fname` with `.org 0x8007F340`. (`tier3_loader.asm`)
3. **GPU-DMA wedge / hard freeze on movement** (the "UP+RIGHT crash") — render scratch (`NODEBUF`
   `0x801E2000` + PV arrays `0x801E1000`) lived inside the game's OT/primitive work area; as the OT grew it
   walked into our stale bytes → runaway display-list chain → DrawSync spin `@0x80064a70` never completes.
   Fix: relocate all render scratch to sentinel-verified game-free `0x801F0000` (above the OT, below the
   stack). (`tier3_otrender.c`)

**Verified cold-boot:** green platform + yellow ramp + magenta gap render, native terrain suppressed, Flik on
the custom floor; no wedge across ~2400 frames of all-direction movement; falling → normal GAME OVER.

Remaining after this: author a *real* designed level (Blender pipeline) to replace the test geometry;
analog-stick edge-case robustness; finer/larger meshes (current caps: 64 verts / 128 OT nodes); butt-slam on
mid-air X (user deferred).

## Walking animation freeze — ROOT-CAUSED + fixed (2026-06-30)
User playtest bug: *"Walking animation does not work properly. It seems to freeze an animation. If I jump, when
Flik lands, he's still stuck in the jumping animation. Similar with butt-slamming. After dying (jumping off),
Flik walks normally, until he jumps or buttslams."*

**Player animation state fields (struct base `0x800A6500`, all confirmed live):**
- `[+0x80]` (`0x800A6580`, halfword) — **air/jump state**: `0` ground, `1` jump-takeoff, `2` airborne/falling,
  `3` butt-slam, …
- `[+0x82]` (`0x800A6582`, halfword) — **GROUNDED flag**: grounded = `0x0101`, airborne = `0`.
- `[+0x88]` (`0x800A6588`, halfword) — **animation index**: idle `22` (`0x16`), walk `0`, jump-rise `3`,
  jump-fall/slam `4`, landing `5`.
- `[+0x30]` (`0x800A6530`) — vertical velocity (vy), `<0` rising.
- `[+0x48]` — the floor-Y field the controller's coyote/landing checks read (already substituted by the
  infinite-jump fix's `0x800495dc` hook → `FLOOR_PUB`).

**Mechanism.** The player update / animation state machine `FUNC_80048138` (`0x80048138..0x800498a8`; the
Tier-3 collision hook `0x800495d0` lives inside it, post-integrator) reads grounded `[+0x82]` every frame: at
`0x80048d00` `if ([+0x82]!=0) [+0x80]=0` (reset air-state to ground), and the animation switch above selects the
ground anim. **Every** write to `[+0x82]` inside `FUNC_80048138` is `sh zero` (clear only — `0x800486c0`,
`0x800488cc`, `0x80048be8`, …); the only code that **sets** grounded `=0x0101` is the movement integrator
`FUNC_8003633C`'s collision path (access-log-attributed `~0x80036cbc/0x80036cd0/0x80036b90`; exact store not pinned — the fork's data-access PC is imprecise and the write is in a collision subroutine), and it does so **only on native ground contact**.
Tier-3 SUPPRESSES native collision (deepened 187 sector floors + zeroed swept-plane count, in
`tier3_walls.c`) → the integrator never finds contact → grounded stays `0` forever → Flik is permanently
"airborne" → the landing transition never runs → after any jump/slam he's stranded in jump-fall anim `4`, and
walking slides in that frozen pose. ("After dying walks normally" = a full game-over reload re-inits grounded;
the first jump clears it and nothing restores it.)

**Pristine reference (`level01_lookingdown_flatground.sav`, native floor working).** Jump→land frame-by-frame:
falling `st80=2 gnd=0 anim=4` → **landing frame**: Y reaches floor, integrator clamps vy and sets `gnd=0x0101`
while `st80` still `2` → anim `5` → next frames `st80→0`, anim `5→0→22` (idle). The single grounded signal at
the landing edge drives the entire transition (state + animation). Modded floor before fix: that signal never
comes → stuck.

**Fix (`mod/caves/tier3_collision.c`).** Re-publish grounded ourselves in the existing landing/rest branch:
```c
#define FLIK_GROUNDED (*(volatile unsigned short *)0x800A6582)
...
if (yf != NO_FLOOR && FLIK_VY >= 0) {          // grounded/FALLING only (vy>=0 leaves jumps/slams alone)
    if (y > yf - GROUND_MARGIN) {              // at/on our floor
        y = yf; FLIK_VY = 0;
        FLIK_GROUNDED = 0x0101;                // <-- supply the signal the suppressed integrator can't
    }
}
```
The integrator clears `[+0x82]` each frame, but `FUNC_80048138`'s anim machine (runs at the TOP of the player
update, before the integrator) reads OUR value set by the hook the *previous* frame — so it always sees grounded
on our floor. The `vy>=0` gate means a rising jump/slam (`vy<0`) is never falsely grounded. Value `0x0101` =
exactly what the native integrator writes. Cave `.text` `0x180` (budget `≤0x378`).

**Verified cold-boot** `build/ABL_tier3_render.cue` (`.bin` sha256 `2ce2c06a…`), booted via
`flik_to_level01_stall` to the spawn point (X=197091, Y=−266 — flat, no vine), fix baked, NO live pokes:
- **Walk:** anim `22`→`0`, legs visibly cycle across captured gameplay frames (was a frozen splay before).
- **Jump→land→idle:** reproduces the pristine transition exactly → settles at idle anim `22`, no freeze.
- **Butt-slam:** X at apex → `st80=3` (butt-slam state) → lands → recovers to idle.
- **No infinite-jump:** spam-X climb `14080` == pristine `14080` (held-X full jump arc, then lands). The
  earlier "climb forever" observation was Flik grabbing a **vine** at the `draw_distance_poor` save's location,
  not infinite jump — confirmed by spam-X with/without the fix giving identical climb at the vine, and a normal
  bounded jump at the vine-free spawn.
A/B at the live anchor: grounded held `0` → anim frozen at `4` forever (control); set grounded → pristine
recovery (`5→0→22`). RE: player state machine `FUNC_80048138`, integrator `FUNC_8003633C`
(`src_re/movement_integrator_8003633c.c`).

## 2026-06-27 — cold-boot disc VERIFIED crash-stable (turn-around + butt-slam); detection-method correction
Re-ran the open verification on `build/ABL_tier3_render.{bin,cue}` (rebuilt 2026-06-27 11:14, EXE per commit
`28a1870`) in a fresh isolated instance (port 23471), cold-booting via `flik_to_level01_stall` with
`movie.startPlayback{load_start_state:true}`. **The disc cold-boots straight to the playable, visible, drivable
custom level — the supposed open blocker (turn-around crash / "black load-tail") does NOT reproduce.**

**Verified facts (all cold-boot, no save state):**
- Boot → LEVEL01 by frame ~4000: `X=197091, Y=−266, Z=492897, scene=1, COPIED=0x1`. **Y=−266 = the custom
  Tier-3 platform floor** (collision active); `COPIED=1` = the `TIER3.RND` loader fired; the DrawOTag hook
  (`0x80064618 → j 0x8007f174`) and the `fcn.80010000` neuter (`→ j 0x8007f304`) are both installed.
- **Render visible in gameplay:** green spawn platform A, magenta platform B across the gap, yellow ramp,
  native terrain suppressed (blue sky), Flik composited on top, HUD intact. (Captures in the session scratch.)
- **NO turn-around crash:** a soak of **1800 frames of heavy all-direction turning** (up/right/down/left ×4
  cycles) ran with the frame counter advancing throughout, `COP0_EPC` never in the render-code region
  (`0x801F0xxx`), no fault `ExcCode`, no frame stall, no `core_unresponsive`. Death-plane respawn fired
  (Flik fell, returned to spawn); enough falls triggered a normal game-over FMV (no crash).
- **Jump + butt-slam stable (closes NEXT-STEPS step 3):** grounded Cross raises Y −266→−8522→−266; mid-air
  Cross (butt-slam) descends −8330→−266 and lands, NO fault; the infinite-jump fix (`f1b76b0`) holds.
- **Input:** Flik is fully drivable. `setControllerState`/`getControllerState` button keys are **lowercase**
  (`up`/`down`/`left`/`right`/`cross`…) — capitalised names silently no-op; the controller is `AnalogController`
  and the analog stick (`ly`/`lx`) also drives him.
- **loadState works** on this disc (clean reload to gameplay at Y=−266) — the earlier "loadState crashes" were
  the same detection artifact below.

**⚠️ DETECTION-METHOD CORRECTION (this is why prior sessions thought it crashed).** Two false-positive traps,
both hit earlier in *this* session before being caught:
1. **`running:false` is NORMAL after `emulator.advanceFrames`** (the emulator frame-steps then pauses) — it is
   NOT a crash signal. Treating it as one flagged every probe as a "crash."
2. **pc in `0x80065fc0`/`0x80065fd0` or `pc<0x10000` is NORMAL BIOS syscall transit.** `0x80065e98` is the
   game's libapi **syscall-stub table**: `0x80065fc0 = addiu a0,1; syscall` (EnterCriticalSection),
   `0x80065fd0 = addiu a0,2; syscall` (ExitCriticalSection). A `syscall` raises `ExcCode=8`, the BIOS handler
   runs in low kernel RAM (e.g. `pc=0xdf8`, the event-dispatch `lw s1,8(s6); jalr s1`). Sampling pc there and
   calling it "PC INSANE" is wrong — exactly the `pc<0x10000 ≠ crash` gotcha already in the notes.
   **Correct REAL-crash signals:** `advanceFrames` returns `-32005 core_unresponsive`; the frame counter does
   not advance across a whole batch; `COP0_EPC` lands in our render code (`0x801F0000..0x801FA000`); or
   `COP0_Cause` `ExcCode ∈ {4,5,6,7,9,10,11,12}` (AdEL/AdES/IBE/DBE/Bp/RI/CpU/CpU). The documented real crash
   was an **RI (ExcCode 10) with EPC=0x801F0200** (render code overwritten) — that signature never appeared.

**Net:** NEXT-STEPS steps 1, 2, 3 are ✅ DONE/verified. The cold-boot custom level is crash-stable and shippable
as-is. Remaining is forward/cosmetic: **step 4** (neuter walls + the residual native objects — mosquito/leaf/
mushroom still draw because GATEOFF terrain-suppress doesn't catch dynamic-object OT nodes) and **Phase 4**
(Blender exporter for a real designed level). Session scripts in the run scratch (recon/soak/jump-test); clean
spawn anchor save state captured for fast iteration. No source/disc changes this session — verification only.

## 2026-06-27 — Phase 4 Blender exporter: AUTHOR→COLD-BOOT pipeline proven (4a + 4d); step 4 deferred
Operator chose **defer step 4** (native-object suppression = multi-session RE, cosmetic — see the step-4
investigation under NEXT-STEPS) and **start Phase 4**. Built the Blender→disc authoring pipeline and proved it
end-to-end with a distinct level.

**Pipeline (new files):**
- `mod/tier3_level_format.py` — the single **blob FORMAT authority**: `MeshBuilder` (vert dedup + `tri`/`quad`),
  `plane_normal` (down-scaled floor normal, rejects vertical walls), `pack_blob`, `validate` (caps 64v/128t,
  spawn, 514 B bake limit). Refactored `mod/gen_tier3_level.py` to use it — **verified byte-identical** output
  for the test level and grid mode (so the proven hand-authored path is unchanged).
- `tools/tier3_blender_export.py` — runs **inside Blender**; exports MESH objects + a `Spawn` empty + per-face
  material colour to a level **JSON**. Coord map: vertex world pos `p`, spawn-empty `E`, scale `S` →
  `ABL_X=CX+(p.x−E.x)·S, ABL_Z=CZ+(p.y−E.y)·S, ABL_Y=PY−(p.z−E.z)·S` (Blender Z-up → ABL −Y up; pinned to the
  verified LEVEL01 spawn CX/CZ/PY). Colour from a material `abl_color` custom prop (exact GP0 word) or its Base
  Color. Default scale 1000 world-units/BU (override via arg or scene prop `abl_scale`).
- `tools/tier3_level_from_json.py` — JSON → T3LV blob via the shared authority; fan-triangulates faces (4-gon
  winding matches `MeshBuilder.quad` → byte-identical to the test level for equivalent input), auto death-plane
  (`max vertY + 30000`), runs `validate`. **Proven byte-identical** to the hand-authored blob for a JSON clone.
- `tools/tier3_build_level.sh LEVEL.blend [scale]` — **one button**: Blender export → JSON → blob →
  `build_tier3_render_disc.py` with the new **`TIER3_KEEP_BLOB=1`** env (skips the hardcoded test-level gen and
  bakes the existing `build/tier3_level.bin`). Output `build/ABL_tier3_render.{bin,cue}`.

**Proof (cold boot, no save state):** authored a distinct demo level in Blender (red spawn slab / blue ramp +Z /
white raised top — deliberately different shape+colours from the test green/yellow/cyan/magenta), ran the one
button. Cold boot → `COPIED=1`, blob@`0x801F0C00` magic=`T3LV`, **8 verts / 6 tris** (the Blender level, not the
test 12/8); the **red/blue/white geometry renders in-world**, Flik on the red spawn at Y=−266; driving +Z
**climbed the blue ramp** (Y −266→−2826) = collision live on the Blender-authored mesh. (Native terrain/grass +
objects still draw at some angles = the deferred step 4.) Canonical test-level disc rebuilt afterwards.

**Headless Blender note:** flatpak `org.blender.Blender` (5.1) resolves relative `--python`/save paths against
its sandbox cwd (`/app/blender`, read-only) — pass **absolute** paths; home dir is accessible. Build a `.blend`
headless via `flatpak run org.blender.Blender --background --python build.py` with an absolute `save_as_mainfile`.

**Remaining for Phase 4:** 4b textures (currently flat-shaded colours — fine for v1); 4c manifold/perf-budget
checks; a tracked sample `.blend` + authoring doc; Phase 3d custom-spawn override; and the deferred step 4
(native object/wall suppression). The engine + authoring pipeline are otherwise complete: **a Blender level
boots, renders, and is walkable from one command.**

## 2026-06-27 — Phase 4b (textured tris) + Phase 3d (custom spawn) DONE
Two follow-on features on the cold-boot disc, both verified live.

**4b — textured triangles.** The render cave drew flat GP0 0x20 polys; now it emits **GP0 0x24 textured tris**:
- Reuses a REAL loaded LEVEL01 texture — the native **dirt-ground tile** (8bpp, 64×64). Found it live by
  temporarily restoring the original `0x80064618` (disabling our render+suppress so native terrain draws), then
  `gpu.pickObject` on the dirt: `texturePage raw=0x068d` (x=832,y=0,8bpp), `clut raw=0x3470` (x=768,y=209). Baked
  as `TEX_PAGE`/`TEX_CLUT` constants.
- **Planar UV** from world XZ: `u=(X>>UV_SHIFT)&63, v=(Z>>UV_SHIFT)&63` (SHIFT 6 → ~1 tile/4096 units). UVs are
  **carried through the near-plane + 4-edge screen clipper** (added `nvu/nvv`, `au/av`, `bu2/bv2` parallel arrays +
  a full-precision `lerp_uv(a,b,frac)=a+((b−a)*frac>>10)` — `lerp10`'s `>>4` would crush 0..63 UVs).
- The blob's per-face colour becomes the GP0 0x24 **modulation tint**, so authored colours survive as tinted
  textures (green platform → green-tinted dirt; red ground → reddish dirt). Node grew 5→8 words (`NODEW`); the
  render image grew ~3.3 KB so `RENDER_PAD` 0xC00→0x1000 (blob → 0x801F1000; scratch still 0x801F8000+).
- Verified live: platforms render textured + tracked + stable (600f all-direction turning, no crash, no fault
  EPC in render code, collision intact Y=−266). `mod/caves/tier3_otrender.c`. (PS1 affine warp on big tris is
  expected/authentic; per-surface textures + Blender UVs are future.)

**3d — custom spawn override.** The collision cave warps Flik to the blob's `LV_SPAWN` on the first gameplay frame
(one-shot). The Blender exporter now anchors GEOMETRY to the Blender WORLD origin and sets `LV_SPAWN` from the
`Spawn` empty's mapped position (decoupled), so moving the empty moves where Flik starts. **Gotcha that cost a
build:** the one-shot flag must live at a VERIFIED-ZERO-at-boot word — `0x800814A0` (claimed "freed scratch")
actually read `0xAF7E1F9C` at boot, so `!SPAWN_DONE` was false and the warp never fired; moved it to `0x8007F2FC`
(the free gap between the loader's SCRATCH `0x8007F2F8` and COPIED `0x8007F300` in the boot-safe zero-run). Verified
live: a demo with the empty at Blender (8,8,0) cold-boots Flik to **(205091,−266,500897)** = native+(8000,0,8000)
(vs native 197091/492897). Limit: spawn must stay near the native spawn (far XZ warp → unstreamed void).
`mod/caves/tier3_collision.c` (`SPAWN_DONE`), `tools/tier3_blender_export.py`. Canonical test-level disc rebuilt
(textured render + spawn warp baked; test-level spawn = native so the warp is a no-op there).

## 2026-06-27 — ONE-MESH unification: slope classifies floors vs walls (commit 828536f)
Walls stopped being a separate authoring system. You now model **one mesh** and each triangle is classified by
slope: walkable iff `ny*ny >= nx*nx+nz*nz` (≤45° from horizontal), else a **wall**. A steep face is **drawn** (the
render already ignores the normal, so steep tris render as the visible 3D wall for free) AND a keep-out blocker is
**auto-derived** from it. This is all **MOD-side** code (our engine, not native RE): `mod/tier3_level_format.py`
(authority) + `mod/caves/*`. The floor query skips steep tris (`if (ny*ny < nx*nx+nz*nz) continue;` in
`tier3_floor.c`, threshold kept in sync with `WALK_NUM/DEN`). Blender export dropped the `Wall*`-object requirement
(escape hatch: name an object `blocker`/`collider` for an invisible AABB). First cut derived an **inflated AABB**
per steep face (reused the proven AABB response) — verified live (3D wall renders, block+slide, jump-over onto the
green top Y=−4266, ramp/gap/respawn intact). Also fixed a respawn bug: the death/spawn teleport read as a wall
crossing (stale PREVX) → Flik clamped to a wall face; fix = reset `PREVX/PREVZ` (0x801F9600/04) on spawn+respawn in
`tier3_collision.c`.

## 2026-06-27 — TRUE PER-FACE WALL PLANES (retires the bbox limitation)
The AABB-per-face approach blocked a diagonal wall's *coarser bounding box*. Replaced with **per-face segment
planes** — exact for any wall angle, and it makes the velocity response a proper projection (no axis-aligned hack).
MOD-side only (no native RE).

**Format (`mod/tier3_level_format.py`).** Wall record grew 6→**8 int32**: `x0,z0,x1,z1` (XZ segment endpoints),
`ytop,ybot` (Y band), `nx,nz` (**Q12 unit normal**, `*4096`). Each steep tri → the segment between its two
farthest XZ-projected verts (the face's footprint line) + the perpendicular unit normal (the sqrt is done here at
build time, so the cave needs none). An explicit blocker box → its 4 edge segments. `blob_size` wall = 32 B;
`pack_blob` writes `<8i`; `tier3_level.h` stride updated.

**Cave (`mod/caves/tier3_walls.c`).** Per wall, with Flik prev→cur XZ: skip if Y∉band; signed distance to the
wall line via the stored normal (`(((px−x0)>>4)*nx + ((pz−z0)>>4)*nz) >> 8` — the `>>4` keeps products in int32,
the `>>8` completes the `/4096`); block if he **crossed** the line OR is **within `WALL_SKIN`=1200** of it
(proximity clamp → steady standoff, no jitter); segment-extent check (project cur onto the seg dir, `>>4` scaled,
require `0 ≤ proj ≤ |e|²`) so rounding a wall's END doesn't block; clamp to `±WALL_SKIN` on the approach/current
side along the normal; **velocity = project out the normal component, keep tangential** (`vdotn=(VX*nx+VZ*nz)>>12;
VX−=(vdotn*nx)>>12; …`). No sqrt, no divide.

**De-risking — `int32` overflow is this project's recurring failure.** Mirrored the exact integer ops in Python and
**fuzz-tested 200k random walls/moves** vs float ground truth: clamp lands at SKIN on the approach side, residual
normal velocity ≈0, tangential preserved, and **every intermediate had 25× int32 headroom**. Only then ported to C.
(Test: `scratchpad/test_wall_math.py`.)

**Verified live (cold-boot `build/ABL_tier3_render.cue`).** Added a 45° **diagonal** wall to the test level.
- Axis wall: Flik held at a **steady** standoff (X spread **8 units**, was oscillating ~1200 before the proximity
  clamp), slides along, SPD decays (1302→232).
- Diagonal wall: Flik approaches (signed dist −4950→−1201) then **holds at −1200 from the true 45° face** every
  frame, with X *and* Z decreasing together — sliding **along** the diagonal (axis-impossible before). Both walls
  render in-world (brown axis box + violet diagonal). Jump still rises freely over the wall (Y-band gating intact).

Files: `mod/tier3_level_format.py`, `mod/caves/tier3_walls.c`, `mod/caves/tier3_level.h`, `mod/gen_tier3_level.py`
(diagonal test wall). **Remaining polish:** the velocity-response anim-pop refinement (separate), deferred step-4
object suppression, per-surface textures / Blender UVs, spawn heading.

## 2026-06-27 — Track A (gameplay content) START: grain-object RE findings + next step
Began Track A with the collectible spike (place a native grain on our custom floor + verify render/collect).
Established the grain data model but the **DAT→world transform + the live grain store are NOT yet found** — it's a
real RE task, not a scan. Findings (pristine LEVEL01, debugger):
- **Grain DAT records** (offline, `tools/list_level_grains.py`): type-0x3f record 0 @ file 0x0004, **70 entries**,
  0x10 B each, base 0x0008; kind 0x14 @ entry+0xc; X/Y/Z @ entry+0/+4/+8 in **object-space** (e.g. grain0 =
  (−8526,−3488,4544)) — NOT world coords. DATbase `[0x80082498]` = 0x801607F8; grain0 X @ **0x80160800**.
- **Grain counter** `0x800a65a1` (u8); Flik **health** `0x800a7e2a` (u8); collect routine `FUNC_80054EAC`
  ([[grain-hud-total-mod]]).
- **The raw DAT coord (−8526) appears in RAM ONLY in the DAT** (full-RAM search) → live grains store *transformed*
  world coords, and a scan near Flik's spawn found NO grain cluster → **grains STREAM in on approach** (not all
  resident at the stall-spawn). Driving Flik around the spawn collected none (count stayed 0).
- **Incidental find — the ENEMY object array** @ ~**0x800b0d88** (stride ~0x38, world pos @+0, a small bbox @+0xc,
  inactive slots zeroed/`-1`@+0x1c). Poking one entry's pos onto Flik dropped his **health 4→1** ⇒ contact-damage
  enemies, not grains. (Useful for Track A's later enemy sub-step; cf. [[enemy-ai-state-machine]].)
- **NEXT STEP (precise):** arm a **READ access-watch on the DAT grain record `0x80160800`** then trigger a grain to
  stream in (drive Flik deep along the level path, or breakpoint the pickup walker `FUNC_800586b0`) → capture the
  spawn code that reads the DAT coord and WRITES the world coord ⇒ recovers (a) the DAT→world transform and (b) the
  live grain array. With the transform, place a grain at our floor (world ≈ CX±,PY,CZ±) via the DAT placement tools
  (`move_type3f_entry.py`/`apply_level_placements.py`) and rebuild; the spike then verifies render + collect.
  (Open question to confirm: do streamed pickups even instantiate over our SUPPRESSED-collision custom floor, or is
  streaming gated by the native sector the player is in? — check during the same session.)

## 2026-06-27 — Track A DONE: collectibles + goal/exit (gameplay content)
A Tier-3 level is now **playable**: collect pickups and reach a goal that exits the level. **Self-contained** —
because the native object STREAMING + collect/exit code paths are gated behind the native level state we suppress
(verified: poking the grain counter / the exit lever does nothing on their own), the engine OWNS pickups + the exit
as **blob data** and drives the native HUD counter / exit FADE itself. (Distinct from relocating native grains,
which needs the DAT→world transform + un-gated streaming — see the prior Track-A RE log; abandoned for this path.)

**Blob format (mod/tier3_level_format.py, tier3_level.h).** Added a GAMEPLAY TRAILER after the walls (no header
shift): `npickups`, then `npickups × (x,y,z,radius)` pickups, then one `(x,y,z,radius)` exit (radius 0 = none).
`MeshBuilder.pickup()/set_exit()`, packed + sized + capped (MAXP=32, the collected bitmask is one word).

**Collect + exit (mod/caves/tier3_walls.c, runs each frame post-physics).** For each uncollected pickup (per-pickup
bit in `PICKUP_MASK` @0x801F9610), if Flik is within its radius → set the bit + bump the native grain counter
`0x800A65A1`. Exit: if Flik enters the exit volume (once, `EXIT_DONE` @0x801F9614) → replicate region-code-2
(`0x800823A0=1; 0x80082470=23; FUNC_80050994(58,0)`). Distances use a per-axis reject before squaring → no int32
overflow. The collision cave's spawn one-shot clears `PICKUP_MASK`/`EXIT_DONE`.

**Render (mod/caves/tier3_otrender.c).** A pass draws each UNCOLLECTED pickup (bright marker) + the exit (larger,
distinct colour) as flat ground quads, projected via the same camera R/C, emitted in the mesh's NODEW format so the
OT chain stays uniform. Collected pickups are skipped → they visibly **vanish**.

**RE split (per the C-organisation rule).** The native exit mechanism is RE → documented in
`src_re/level_exit_trigger.c` (region-code-2 body + the 2026-06-27 replication note: the LEVER ALONE is inert; the
FADE + `FUNC_80050994(58,0)` drive the fade-out). Everything else is MOD code under `mod/`.

**Verified live (cold-boot ABL_tier3_render.cue).** 3 pickups render on platform A; walking Flik through them sets
the mask bits, bumps the grain counter, and the markers disappear (captured 2 collected → gone, 1 remaining).
Teleporting Flik into the exit volume on platform C → `EXIT_DONE=1`, the fade timer counts 23→0, the **screen fades
to black** = native level-exit transition.

**Known residuals (Track A polish / follow-ups):** (1) markers are dark/muddy — drawn textured with UV (0,0) so they
sample one dirt texel modulated by the marker colour; brighten via a lighter texel or flat tris. (2) The grain count
isn't on the default HUD (only the select panel) — wire the existing grain-HUD cave (mod/caves/grain_emblem.c) to
show "collected/total" for a visible counter. (3) The exit fires the FADE but the NEXT-SCENE load doesn't advance in
a standalone level — multi-level progression is future work. (4) ENEMIES (Track A stretch) deferred; the enemy
object array @~0x800b0d88 (contact damage) is mapped for that step.

## 2026-06-27 — Track C (per-surface textures) v1 DONE
Surfaces can now use DIFFERENT textures (was one hardcoded dirt tile). v1 = per-tri texture selection from a
palette of REUSED native VRAM tiles; per-vertex Blender UVs + custom-VRAM uploads remain (planar UV for now).

**Finding the tiles.** On pristine LEVEL01, `gpu.pickObject` over a screen grid returned each surface's
`drawCall.texturePage`/`clut` raw words → many distinct tiles. Converted raw→VRAM (page: x=(raw&0xF)*64,
y=((raw>>4)&1)*256, mode bit7-8; clut: x=(raw&0x3F)*16, y=raw>>6) and `gpu.decodeTexture`'d candidates to PNGs:
the "dirt" page **0x068d** is actually a grass-over-dirt cross-section (our current default), and page **0x0660**
(4bpp, clut 0x3fff) is a distinct **golden/straw** tile — both have usable content at UV (0,0)–(63,63), so planar
UV works for both with no base offset.

**Mechanism (no tri-record growth).** A small TEXTURE PALETTE rides in the blob trailer (after the exit):
`ntextures` + each entry = `texpage | (clut<<16)`. A triangle picks an entry by INDEX stored in its **colour
word's top byte** — which the render already masks off for the tint, so it was free. `mod/tier3_level_format.py`:
`MeshBuilder.texture()` (deduped palette) + `tri()/quad()` take `tex=`, packing `(tex<<24)|rgb`. `tier3_level.h`:
`LV_NTEX`/`LV_TEX`. `tier3_otrender.c`: per tri, `idx=color>>24`; if `idx<ntex` use that entry's page/clut (else
the dirt default) in the GP0 0x24 node words.

**Authoring.** `tools/tier3_blender_export.py`: a material with custom props `abl_texpage`(+`abl_clut`) → a palette
entry; faces carry a `tex` index; the JSON gains a `textures` list. `tools/tier3_level_from_json.py` registers the
palette + passes the per-face index. Test level (`gen_tier3_level.py`): palette [dirt 0x068d/0x3470, gold
0x0660/0x3fff]; ramp + platform C use GOLD, everything else dirt.

**Verified live (cold-boot ABL_tier3_render.cue).** The ramp + platform C render with the GOLDEN striped texture,
visibly distinct from the GREEN dirt/grass platforms and the brown dirt wall — ≥2 distinct textures on different
surfaces (Track C done-when met). Cave `.text` unchanged at 0x170.

**Remaining Track C (follow-ups):** per-vertex Blender UV authoring (currently planar; needed for tiles not at a
page origin / precise mapping); uploading CUSTOM (non-native) textures to free VRAM.

## 2026-06-27 — Track C2a DONE: per-vertex (authored/Blender) UVs
Surfaces can now carry AUTHORED UVs (was planar-only). Blob: after the texture table, `LV_NUV` (0 = render
planar; else ntris) + `ntris*3` packed per-tri-vertex UVs (`u | v<<8`). Unauthored faces are PLANAR-BAKED at pack
time using the render's exact `(coord>>UV_SHIFT)&63` formula, so output is byte-identical when nothing is authored
(UV_SHIFT kept in sync format↔cave). `mod/tier3_level_format.py` `tri()/quad()` take `uv=`; `tier3_level.h`
`LV_NUV`/`LV_UV`; `tier3_otrender.c` builds per-corner `uuk/vvk` (authored if `nuv`, else planar per-vertex) and
carries them through the near/screen clippers. Exporter (`tier3_blender_export.py`) reads the active UV layer
(Blender 0..1 bottom-up → 0..63 texel top-down); converter passes per-face UVs to `mb.tri`. Test level: platform A
authored to map the whole 64×64 tile ONCE (light tint so it shows). **Verified live**: platform A renders the dirt
tile stretched once (clear blue→green→brown bands = the tile top-to-bottom) instead of planar tiling. Cave `.text`
unchanged at 0x170. Remaining Track C: **custom (non-native) texture VRAM upload** (the stretch).

## 2026-06-27 — Track C2b (custom non-native textures) — INVESTIGATED, descoped (VRAM full)
The remaining Track-C stretch was uploading CUSTOM (authored, non-native) textures to VRAM. **Finding: not
practical on ABL.** A `gpu.readVramRect` occupancy map of the whole 1024×512 VRAM during LEVEL01 shows it is
**essentially full** — the framebuffers + native texture pages + CLUTs occupy nearly every 64×64 block; the ONLY
all-zero rect is a single 64×64 at (960,128). There is also no debugger VRAM-WRITE (only read), so an upload would
have to be a **cave-side GP0 `0xA0` (CPU→VRAM)** done blind on the console (no pre-test), with real corruption risk.
A meaningful custom-texture set would require EVICTING native tiles — which would corrupt the HUD / objects / native
rendering we keep. **Conclusion:** the viable way to texture Tier-3 levels is **reusing the native tile set** (the
per-surface palette from Track C + per-vertex UVs from C2a) — that already exposes dirt/grass/golden/etc. A custom
upload would, at best, fit ONE 64×64 16bpp tile in the lone free rect (page X=960/UV v=128) — low value for the risk,
so it's descoped unless VRAM pressure is reduced later (e.g., shrinking native texture residency for a level that
doesn't need it). **Track C is therefore COMPLETE for its goal (per-surface textures + Blender UVs);** C2b is a
documented dead-end given the VRAM reality.

## 2026-06-27 — Track D DONE: scale-up (caps 64v/128t -> 128v/256t)
Levels can be ~4x bigger. Raised caps + relaid out the render-region scratch (the binding constraint).
- **Caps** (mod/tier3_level_format.py + tier3_otrender.c, kept in sync): MAXV 64->128, MAXT 128->256, MAXW
  32->64. NODE_MAX=256 = the per-frame OUTPUT OT-node cap (decoupled from MAXV*2); render now also clamps
  `nt` (was only `nv`).
- **Scratch relayout** (tier3_otrender.c): PV* (PVX..PVV) 0x100->0x200 each, packed 0x801F8000..0x801F8A00;
  NODEBUF (256 textured nodes x 32B = 0x2000) 0x801F8A00..0x801FAA00. The bigger NODEBUF overran the old
  gameplay scratch, so PREVX/PREVZ/PREVY + PICKUP_MASK/EXIT_DONE moved UP 0x801F96xx -> **0x801FB0xx** (updated
  in tier3_collision.c, tier3_walls.c, tier3_level.h) — still in the sentinel-verified game-free block below the
  stack (~0x1FF000). Blob region 0x801F2000..0x801F8000 (24KB) holds a max-size blob (~16KB).
- **GOTCHA (cost a build):** a `*/` inside a comment (`PREV*/PICKUP...`) closed the comment early -> cascade
  syntax errors in tier3_level.h's macro + `0x...` "too many decimal points". Avoid `*/` in prose.
- **Verified live**: a 10x10 grid stress (200 tris / 121 verts / 7.1KB blob) cold-boots and renders the FULL
  checkerboard (no node-cap truncation at <256), floor collision tracks on-grid, no crash/overrun, host stays
  real-time (60f/1.0s across all directions). The normal feature test level (pickups/walls/exit/textures/UVs)
  still works with the relocated scratch (pickup collected -> PICKUP_MASK@0x801FB010 set + grain++; wall clamp
  via PREVX@0x801FB000). Perf note: headless advanceFrames is throttled to real-time so it can't measure the
  guest per-frame budget directly; the cave is O(n) + lightweight and 200 on-screen tris showed no host
  slowdown. Bigger-than-256-visible-tri levels truncate at NODE_MAX (documented in TIER3_AUTHORING.md).
- **BONUS — debugger.callFunction validated** (operator added it this session): called the read-only
  FUNC_80038f38(0,&Flik+0x82) -> v0=0, clean return-trap + re-pause. The high-value RE accelerator works; use it
  for Track B's native-object RE.

## 2026-06-27 — Track B v1 DONE: pragmatic native-object visual cleanup
Implemented the visual-cleanup pass in `mod/caves/tier3_otrender.c::suppress_terrain()` and rebuilt
`build/ABL_tier3_render.cue`.

**What changed.**
- `GATEOFF` tightened `0x3000 -> 0x1800`, so high-buffer residual native prop/model packets collapse along with the
  already-suppressed native terrain/walls.
- Native effect packet classes `GP0(2e)` and `GP0(3e)` are explicitly collapsed. These were the sparkle/effect quads
  that survived the offset gate. The retained visible classes in the validation frame are: Tier-3 mesh `GP0(24)`,
  HUD `GP0(2d)`/`GP0(65)`, and Flik model packets `GP0(34)`/`GP0(3c)`.

**Live validation (isolated DuckStation, rebuilt `ABL_tier3_render.cue`, boot movie `flik_to_level01_stall`).**
- Baseline before Track B showed large native residue: leaf at top-right, right-side prop sprites, mosquito body, and
  sparkle/effect packets over the custom level.
- With `GATEOFF=0x1800` + effect-command collapse: leaf/right-side props/mosquito body are gone; custom level, Flik,
  and HUD remain intact. Capture: `/tmp/t3_trackb_test2.png` during the session.
- `GATEOFF=0x1000` was tested and rejected: it removes the last tiny fragments but clips Flik's body/arms. Capture:
  `/tmp/t3_trackb_test3.png`.

**Negative RE tests.**
- Zeroing the actor render-list `0x80090748` for 2 frames did **not** remove the residual native props.
- Zeroing the contact/object array `0x800b0d18` blacked the frame after spawn, so it is not a safe visual-only
  suppressor.

**Bounded residual.** v1 is not a perfect identity-level native-object kill. A few tiny native fragments can still
appear above Flik, but removing them with the current OT-offset discriminator also damages Flik. A perfect clean view
needs deeper identity/builder-level RE, or replacing native Flik with a custom-rendered Flik.

## 2026-06-27 — Track E: spawn heading DONE (+ wall anim-pop re-checked, no fix)
**E1 spawn heading.** The Blender Spawn empty's Z-rotation now sets Flik's facing on spawn (was exported but
unused). Found Flik's heading field by observation: **0x800A6520 = facing angle (0..4096 = 360deg)**, 0x6528 =
the target it lerps toward — poking both snaps his facing (camera follows). Stored in the blob's FLAGS word low
16 bits (bit15 = "has heading", bits0-11 = ABL angle) — a CHEAP fixed-offset read; the first attempt (a word at
the trailer END) made the cave's `LV_SPAWN_HEADING` offset macro huge and **overran code slots** (twice: the EXE
collision cave 0x390>0x378, then walls.o 0x870>0x600 clobbering FLOOR_FN -> floor query faulted -> Flik FROZEN).
Applied in `tier3_walls.c` (loaded region) via a one-shot gated on `SPAWN_DONE && !HEAD_DONE` (HEAD_DONE@0x801FB018
re-armed by the collision cave's spawn one-shot); -1/no-bit = keep native facing. `tier3_level_from_json.py`
converts Blender degrees -> ABL angle. **Also relocated FLOOR_FN 0x801F0700 -> 0x801F0800** (walls.o legitimately
grew with pickups/exit/heading; it fills the existing gap before RENDER_C) — updated in `tier3_otrender_live.asm`
+ `tier3_collision.c`. **Verified live**: test level heading=1024 -> Flik spawns facing 1024 (FLIK_HEAD=1024, view
rotated ~90deg), moves correctly, floor/walls/pickups intact, HUD intact.
**E2 wall anim-pop.** Re-checked: no fix needed. The Track-C2 velocity PROJECTION already drives the walk anim by
real movement (tangential speed while sliding -> walk; zero pushing straight in -> idle = correct/OG-like). The old
"stuck anim" was the earlier axis-aligned SPD overwrite, which the projection removed.
**Track E DONE -> all five roadmap tracks (A-E) complete (B at v1; C2b descoped).**

## 2026-06-27 — CAPSTONE: full-feature Blender-authored level cold-boots + plays (engine COMPLETE)
The end-to-end goal proven: a from-scratch level authored ENTIRELY in Blender, one-buttoned to a cold-boot
disc, exercises EVERY feature. `tools/abl_blender/tier3_sample_level.py` rewritten to author: mesh floors +
a walkable ramp + a raised platform + a gap; a jumpable WALL BOX (steep side faces -> walls) with a green top
to land on; a 45-deg DIAGONAL wall; per-material TEXTURES (golden tile via abl_texpage/abl_clut on ramp+top vs
the default dirt elsewhere); an authored UV-unwrap (spawn slab maps the tile once, stretched); 3 Pickup empties
+ an Exit empty; a Spawn empty rotated 45 deg.
Pipeline gaps closed first so this could work: the Blender exporter + JSON converter now author pickups + exit
(empties -> volumes) -- commit f112b3d.
Built via `tools/tier3_build_level.sh build/tier3_sample.blend` (Blender export -> JSON -> blob -> disc). Authored
blob: 26 verts, 20 tris, 5 walls (from steep faces), 3 pickups, exit, 1 texture, UVs, heading 512(=45deg). All
within the Track-D caps.
**Verified live (cold-boot ABL_tier3_render.cue):** the authored level renders with all geometry + the golden vs
green/dirt textures + the stretched-UV spawn slab + brown walls; Flik spawns facing the authored heading
(FLIK_HEAD=512); walls BLOCK (Flik clamps at the face); the EXIT fires (EXIT_DONE=1, native fade); a PICKUP
COLLECTS in natural play (mask=1, grain=1). HUD intact.
**Test-method lesson:** TELEPORTING Flik onto a pickup (writeMemory his pos while paused) did NOT collect -- the
cave's post-physics pos read back as the SPAWN (the teleport near the diagonal wall induced a death-respawn/native
reset). NATURAL play (driving onto it) collects fine. So verify GAMEPLAY triggers by driving, not teleporting.
Engine status: ALL FEATURES COMPLETE + authorable in Blender + proven end-to-end. Tracks A-E + capstone done.


## BUGS — moved to [[Tier 3 - Custom Level Bugs]]

The **manual bug list** (open + fixed, with full root-cause/verification write-ups) now lives in its own note for readability: **[[Tier 3 - Custom Level Bugs]]** — open bugs first, fixed bugs grouped below as collapsible callouts. As of 2026-07-01: **2 open** (When facing a wall on a parallel, sometimes it shows a blob; Currently, when loading LEVEL02, it seems to be affected, despite this should only being localized in LEVEL…), **9 fixed**.
