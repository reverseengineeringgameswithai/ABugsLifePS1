---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Tier 3 - Custom Level Bugs.md
aliases:
  - "Tier 3 - Custom Level Bugs"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Tier 3 - Custom Level Bugs.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Tier_3_-_Custom_Level_Bugs.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

Testing testing one two three

Manual bugs found by the operator when testing **new custom levels** in the Tier-3 engine (cold-boot `build/ABL_tier3_render.cue`). Split out of [[Tier 3 - Custom Level Engine]] (2026-07-01) so the engine note stays readable; **open bugs are listed first, fixed bugs are grouped below as collapsible ✅ callouts**. Each fix is DuckStation-verified — see the entry for root cause, the `mod/caves/*` C change, and how it was verified. Back to the engine note: [[Tier 3 - Custom Level Engine]].

Originally the `## 2026-06-28 — BUGS` section at the bottom of the engine note.

> [!bug] 🔴 OPEN — 0
> Nothing open. Everything is resolved (below).

## 🔴 Open bugs

*(none)*

> [!success] ✅ FIXED — 17
> All DuckStation-verified. Collapsed for legibility — click a title to expand the root cause + fix + verification.

## ✅ Fixed bugs

> [!success]- ✅ Hard CRASH to BIOS while roaming the LEVEL01-sized ailevel (operator instance, 2026-07-03)
> **Symptom:** playing `ABL_AILEVEL.cue` (the LEVEL01-sized v3), the game hard-crashed ~2 minutes in while
> Flik roamed the REAR GARDEN (behind the native spawn, Z≈466k). Emulator alive, guest halted.
>
> - **DIAGNOSED by probing the operator's own (crashed) instance** via its enabled debugger API (port 2346):
> guest parked at pc 0xA0 with t1=0x40 = **BIOS `SystemErrorUnresolvedException`**; COP0 CAUSE=0xf0000410 →
> **AdEL (address error on load) with BD=1**, BadVAddr **0x80420FDF** (misaligned), EPC **0x8007F310** = inside
> the Tier-3 **`fcn.80010000` neuter stub** — the faulting instruction is the branch DELAY SLOT
> `lw t7,0(a0)` at 0x8007F314.
> - **ROOT CAUSE:** the neuter stub replayed the native ground-builder's displaced prologue load in the gate
> branch's delay slot, so it **dereferenced a0 even when the call was neutered** (the code comment literally
> said "harmless on return"). Small levels never faulted because the native terrain-streaming caller always
> passed a valid pointer — but a LEVEL01-sized level extends **behind the native spawn**, and streaming a
> region back there makes the caller pass a **garbage pointer** → the "no-op" call still loaded from it → AdEL.
> - **WHY MY COLD-BOOT VERIFICATION MISSED IT:** the operator's instance runs **CachedInterpreter** (raises
> real alignment exceptions); the isolated debug instance runs the default recompiler with
> `RecompilerMemoryExceptions=false`, which **silently swallows misaligned loads** — the same call returns
> harmlessly there (A/B-verified live: old stub + `callFunction(0x80010000, a0=0x80420FDF)` = clean return on
> the isolated instance). Emulator-accuracy gotcha for all future engine verification.
> - **FIX:** restructured the stub (`mod/tier3_loader.asm` `tier3_neuter_80010000`): gate FIRST with a
> no-access delay slot; the displaced prologue (`addiu sp,-32` + `lw t7,0(a0)`) is replayed ONLY on the
> COPIED==0 native-resume path; the neutered path is `jr ra` with sp untouched and a0 never dereferenced
> (+ a load-delay nop). Still fits the f304..f340 gap (10 words). **Verified:** rebuilt disc cold-boots;
> `callFunction(0x80010000)` with a0 = 0x80420FDF / 0xF0000010 / 0 / 0xDEADBEEF all return cleanly with
> COPIED=1; extended rear-garden + full-level roam (incl. an edge fall + respawn) stable. asm:
> `mod/tier3_loader.asm`.

> [!success]- ✅ "Too many verts: 281 > MAXV 256" — failed_level.blend rejected by the engine cap
> **Symptom:** adding a few extra floors (failed_level.blend, 281 verts / 372 tris) fails the build with
> "This .blend is too big for the Tier-3 custom engine: too many verts: 281 > MAXV 256".
>
> - Goal to fix: import "failed_level.blend" (just a few extra floors).
>
> - **FIXED 2026-07-03 (cold-boot verified):** raised the engine vert cap **MAXV 256 → 384** (`mod/tier3_level_format.py`
> + `mod/caves/tier3_otrender.c`). The cap sizes the render's per-vertex scratch buffers, so the PV* pack was re-laid:
> each PV* now spans 384·4 = 0x600 (PVX 0x801F8000, PVY 0x801F8600, PVZ 0x801F8C00, PVU 0x801F9200, PVV 0x801F9800) and
> **NODEBUF moved 0x801F9400 → 0x801F9E00** (..0x801FDE00, still 0x200 below the gameplay scratch at 0x801FE000 and the
> stack). MAXT/NODE_MAX stay 512. The real ceiling behind MAXV is the **blob budget**: the T3LV blob loads at 0x801F3400
> and must end below PVX 0x801F8000 (max 0x4C00 = 19456 B) — now asserted by `build_tier3_render_disc.py` (failed_level's
> blob is 18640 B, fits). **Verified cold-boot** (`flik_to_level01_stall` movie): blob header reads nverts=281/ntris=372,
> spawn renders + collides, and Flik **stands grounded (0x0101) on a floor tri built entirely from verts ≥ 256** (the
> old cap) at (220424,−6933,474563) — renders and collides; roam + jump stable, no crash. C: `mod/caves/tier3_otrender.c`,
> `mod/tier3_level_format.py`, `tools/build_tier3_render_disc.py`, docs `tools/TIER3_AUTHORING.md`.

> [!success]- ✅ Token1/Token2/Telescope render far ABOVE their authored (ground-level) Blender position
> **Symptom:** in mylevel.blend the two seed tokens + telescope are authored at ground level, but in-game they sit far
> up in the air (tokens ~93k units, telescope ~48k units above the authored spot).
>
> - Goal to fix: tokens/telescope align with the Blender coords.
>
> - **ROOT CAUSE (live-diagnosed):** several type-0x3f kinds store only a near-zero/relative Y on disc (pristine LEVEL01
> DAT: telescopes Y=−50, tokens −50..−450, FLIK letters 0, **+0xE halfword = 0**) — the game computes their real Y at
> level load by a **native-collision floor snap**, and can re-snap a few frames into gameplay. In a Tier-3 level the
> native floor is the suppressed OLD terrain, so relocated tokens/telescope land at the old level's heights (tokens'
> entry Y drifted file −321 → −3248, a one-shot; live-verified). The **telescope is worse**: its handler (FUNC
> ~0x80053a20, kind==0x30) **re-derives entry.Y every other frame** as `Y = (s16)entry[+0xE] + sine_bob − 800` — the
> **hover BASE is the entry's +0xE halfword**, which the load snap set from the old terrain; pinning Y would
> flicker-fight the handler (it writes AFTER DrawOTag). Grains carry absolute on-disc Y and never drift.
> - **FIX:** extended the generated native pin (build/tier3_native_pin.h, now a compact **table + loop**) to three
> classes — FLIK letters (existing bitmask-gated rewrite), **berries/seed tokens 0x21-24/0x29-2B** (rewrite X/Y/Z each
> frame until the native consumed sentinel Y==0x80000000), and the **telescope 0x30** (rewrite X/Z + the hover base
> `entry+0xE = authored_fileY + 800`, so the native hover itself bobs around the authored height — bob preserved).
> The pin runs in the **render cave** (`mod/caves/tier3_otrender.c`, every frame), NOT the movement-gated player hook —
> a snap that lands while Flik idles is corrected within a frame (proved live: walls-cave pin missed an idle-time snap).
> **Verified cold-boot (mylevel):** tokens hold authored file Y=−321 through idle, telescope bobs −262..−367 around
> −321 with base 479; visual capture shows token + telescope ON the platform next to the FLIK letters; **collection
> safe** — walking into a token sets the sentinel + bumps the packed seed counter (0x800A6598: 0x11→0x22) and the pin
> never resurrects it. **GOTCHA fixed en route:** the pin table's `.rodata` initially overran the walls segment (armips
> `.org` silently let floor.o overwrite the last rows — the budget assert only counted `.text`); `build_tier3_render_disc.py`
> budgets now count **.text+.rodata+.data** for every cave. C: `mod/caves/tier3_otrender.c` (pin loop),
> `mod/caves/tier3_walls.c` (pin removed), `tools/build_tier3_render_disc.py` (table generator + seg_size).

> [!success]- ✅ Adding a token (copy/paste) makes the OLD native level reappear
> **Symptom:** old_data_loading.blend (= mylevel + one copy-pasted token) cold-boots with the old LEVEL01
> grass/decor visible again.
>
> - Goal to fix: old terrain must stay removed regardless of authored object count.
>
> - **ROOT CAUSE:** the render cave re-truncates the native grass source list every frame by writing −1 into a
> **hardcoded** address 0x80163F82 — but that terminator is **pass-3 record 0's +0xE halfword INSIDE the loaded
> LEVEL.DAT image** (pristine file offset 0x3AFA = pass-3 base 0x3AEC + 0xE), so its RAM address **shifts 16 B for
> every type-0x3f record the count-control adds or removes** before it. 0x80163F82 was only correct for mylevel's
> staged delta (−880 B, 13 authored objects); the extra token made the delta −864 → the terminator moved to
> 0x80163F92 → the poke missed (and wrote −1 into another record's bytes) → native grass returned. Same failure
> applies to ANY level whose object count differs from mylevel's (e.g. the ailevel prototype, delta −704).
> - **FIX:** the address is now **computed per build** from the final staged DAT — `T3_GRASS_TERM = 0x801607F8 +
> 0x3AFA + (len(staged_dat) − len(pristine_dat))`, passed as `-DT3_GRASS_TERM` to the caves, with a build-time
> assert that the staged bytes at the shifted offset still equal the pristine terminator (catches any future edit
> that resizes the DAT after the pass-3 region; lanes edits are size-preserving, checked). **Verified cold-boot
> (old_data_loading):** grass terminator −1 at the NEW address 0x80163F92 (old address untouched mid-record), spawn +
> full roam show the custom level only — no old grass/corn; all 3 tokens present and pinned at authored coords; grain
> collection + HUD still work. mylevel (−880) and failed_level rebuild to the same 0x80163F82 as before — no regression.
> C: `mod/caves/tier3_otrender.c` (`T3_GRASS_TERM`), `tools/build_tier3_render_disc.py` (computation + assert).

> [!success]- ✅ Flik is MISSING (whole model gone) — a Phase-4 dirt-terrain-list regression
> **Symptom:** In the custom LEVEL01, **Flik doesn't render at all** — he's alive (walks/jumps, HUD lives) but his model is
> absent (operator-spotted; `gpu.pickObject` at his spawn screen position = 0 gouraud prims).
>
> - Goal to fix: Flik must render (as before).
>
> - **FIXED 2026-07-01 (cold-boot verified):** a regression from **Phase 4's DIRT terrain lever**. Phase 4 baked a spawn
> one-shot that removed both gouraud terrain passes by emptying their render-list counts; the DIRT lever zeroed
> `[[0x800A6300]+6]` (the dispatch `0x8001d3cc` count). **Root cause:** that dispatch draws **Flik too** — the dirt terrain
> render is entangled with the player (same shared-render trap as the reverted Phase 3). Zeroing the count made the whole
> dispatch early-exit, dropping Flik. My Phase-4 "Flik-safe" check verified his *state* (grounded/walks/jumps), NOT his
> *model* — the exact mistake as Phase 3; and `grass_truncated.png` "proof" only exercised the GRASS lever, never the dirt
> one at cold-boot. **Diagnosis (decisive, live on the broken disc):** restoring the GRASS source → Flik still gone;
> restoring the DIRT count (→24) → **Flik reappears** (0→45 gouraud prims). **Fix:** removed the DIRT lever from the
> one-shot (`mod/caves/tier3_collision.c`), keeping only the **GRASS source-truncation lever** (verified Flik-safe). The
> grass (tp663) is source-removed; the DIRT (tp604) terrain stays (it can't be emptied without dropping Flik). **Verified
> cold-boot** (`.bin` sha256 `cbfff41c…`): Flik renders as a proper full ant (45 gouraud prims at spawn; 33 after
> roam+jump), grass gone (tp663=0), dirt back (tp604=17), no crash; LEVEL00 unaffected (COPIED=0, real spawn, native
> terrain). **LESSON (again):** ALWAYS verify Flik's *model* (pickObject/capture), not just his state, after a render
> change; and any terrain lever that shares a dispatch/submitter with the player is unsafe. C: `mod/caves/tier3_collision.c`.

> [!success]- ✅ Flik lands/stands on NOTHING (native collision leaks where our mesh is empty)
> **Symptom:** In the custom LEVEL01, Flik can stand or land on empty space that we don't render — it coincides with
> native terrain (e.g. beside a pristine seed). Movie `attempt_jumping_on_nothing`: he jumps toward an area with no
> custom floor and settles standing at Y=−2820 with `FLOOR_PUB=NO_FLOOR` and native grounded `0x800A6582=0x0101`.
>
> - Goal to fix: where the Blender mesh has no floor, Flik must NOT be able to stand — he falls/respawns.
>
> - **FIXED 2026-07-01 (cold-boot verified).** Render ≠ collision (see [[Collision.md|Collision]]): we removed the native
> terrain RENDER (`fcn.80010000` neuter + SUPPRESS-off) but native terrain COLLISION is a separate system still live. Our
> suppression (`tier3_walls.c`: deepen 187 sector origin-Y @0x800A7E48 + zero swept-plane count @gp+0x57c) is applied
> (verified sectors=40000, count=0) — but the integrator (`movement_integrator_8003633c.c`) runs **three** collision
> passes: `FUNC_80035F24` (sweep), `FUNC_800345CC` (swept planes), `FUNC_80035280` (alt). The latter two gate on the plane
> count we zero, but the **sweep `FUNC_80035F24` grounds Flik on a per-sector floor plane our two levers don't cover**, and
> native re-clamps it every frame. The sweep's floor plane was located (breakpoint at `0x80035f24`: `a3=0x80090560`,
> `[a3+4]=0x800c7678`, unit normal (4438,−15417,−3320) = up-facing floor), but suppressing every per-sector plane is broad.
> **Fix — falling off costs a LIFE + respawns:** in our cave (after the integrator), when native grounded Flik where our
> mesh is empty OR he fell past the death plane — `if ((yf==NO_FLOOR && FLIK_GROUNDED==0x0101) || y>LV_DEATHY) {
> if (FLIK_LIVES>0) FLIK_LIVES--; warp to LV_SPAWN; FLIK_HP=7; }` — decrement the life counter (0x800A65A0, the HUD lives)
> and respawn. **Discriminator** (from the movie): native grounded is 0 through the whole jump ARC (airborne) and 0x0101
> only when native catches him on the un-rendered floor, so it's inert during jumps and on our own floor (yf!=NO_FLOOR);
> fires once per fall (same-frame warp → back on our floor next frame). **Why not the native HP-death path:** setting HP=0
> (0x800A7E2A) from this post-integrator cave is seen too late — the native death-check races HP regen, so the kill was
> flaky; and a cave-driven fall FOUGHT the native respawn (Flik fell forever, life oscillated). A direct decrement + warp
> is reliable. **Verified cold-boot:** movie `attempt_jumping_on_nothing` → life 5→4 + respawn at spawn; gentle on-floor
> play (jump-in-place ×5, small walks) never loses a life; roaming off the edge correctly costs one. **Note:** respawns at
> **UPDATE 2026-07-01 (movie_v2):** upgraded to the REAL native fall-death — landing on un-rendered ground now keeps Flik
> FALLING (drive Y + force AIR_STATE=2) so the game's own fall-death fires: **fade-to-black + life loss + respawn**, same as
> a true pit. Verified movie_v2: both deaths fade, life 5→3 (one per death); normal on-floor play never false-triggers.
> C: `mod/caves/tier3_collision.c`.

> [!success]- ✅ Level BACKDROP missing (all blue) — suppress_terrain was eating it
> **Symptom:** In the custom LEVEL01, the native **backdrop** (far dirt-cliff walls + grass rim + distant grassy
> horizon behind the level) is missing — the level is a floating dirt island in all-blue sky. It only "populates"
> inconsistently after moving Flik forward. Operator: "the backdrop should always be rendered at the very back."
> (save `backdrop_issue`; ref images: bad = island in blue, good = walls+grass-rim+horizon behind our floor pit.)
>
> - Goal to fix: the native backdrop always renders, at the very back, at spawn and everywhere.
>
> - **FIXED 2026-07-01 (cold-boot verified):** `suppress_terrain()` (mod/caves/tier3_otrender.c) collapsed native
> gouraud terrain (`0x34`/`0x3c`) built at **HIGH OT offset** (`> GATEOFF 0x1800`). But that high-offset terrain
> **IS the backdrop** (the far walls/rim/horizon), not the near ground — so suppress was collapsing exactly what we
> want to keep, and its position-dependent offset gate is why it flickered in/out on movement. **Decisive test
> (live, at the blank save):** setting the whole render hook to passthrough (`RENDER_C` = `move v0,a0; jr ra`) made
> the backdrop appear **instantly at spawn** AND left the near area clean — because the NEAR native floor is already
> removed by the `fcn.80010000` neuter (mod/tier3_loader.asm). So `suppress_terrain` is now net-harmful (kills the
> wanted backdrop; the near "leak" it never caught is low-offset anyway). **Fix:** `#define SUPPRESS 0` — the native
> backdrop renders at its native far depth and our prepended floor draws in front. **Verified cold-boot** from
> `mylevel.blend`: backdrop (walls+grass-rim+horizon) present at spawn + through roam; **turn-around soak (8
> directions incl. the old flood-crash angle) kept the render code at 0x801F0C00 intact** (no crash — the flood
> crash is guarded by the `fcn.80010000` neuter, NOT suppress); foreground grass/corn still removed (separate source
> from the backdrop grass rim). C: `mod/caves/tier3_otrender.c` (`SUPPRESS`).

> [!success]- ✅ Native GRASS/corn reappears mid-level (one-shot truncation doesn't hold)
> **Symptom:** In the custom LEVEL01 render disc, the native **grass/corn** (tp663) — supposedly source-removed — **shows
> again** during play. Operator's `artifacts_showing.sav` (on the current render disc) has grass on screen with
> `SPAWN_DONE=1` and the grass terminator `[0x80163F82]=+1` (NOT truncated), while a fresh cold-boot of the same disc has
> `[0x80163F82]=-1` and no grass.
>
> - Goal to fix: grass stays removed for the whole level, including when Flik is idle.
>
> - **FIXED 2026-07-01 (cold-boot verified):** the grass truncation was a **spawn one-shot** in the collision cave
> (`mod/caves/tier3_collision.c`, `!SPAWN_DONE` block). The native loader **REBUILDS** the grass source list at
> `0x80163F74` on a discrete post-spawn event, overwriting the one-shot's `-1` → grass returns. Making it per-frame in the
> **collision** cave did NOT fix it: that hook (`0x800495d0`, the player post-physics point) is **MOVEMENT-GATED** — it fires
> only while Flik is being integrated, so it never re-truncates while Flik stands **idle** (proven behaviorally: forcing
> `term=+1` survived 5 idle frames but flipped to `-1` the moment Flik moved). **Fix:** moved the grass source-truncation
> `*(short*)0x80163F82 = -1` into the **RENDER cave** `tier3_otrender_hook` (`mod/caves/tier3_otrender.c`), which runs
> **every frame** (our floor always draws) and is already LEVEL01-gated. It runs at DrawOTag (post-scene-build), so a rebuild
> flashes grass for at most the **single** rebuild frame, then it's gone. **Verified cold-boot:** at spawn grass gone
> (`tp663=0`); forcing `term=+1` (rebuild sim) is corrected back to `-1` within **one idle frame**, grass stays 0; through
> roaming in all directions with a forced rebuild + 8 idle frames before each check, `term=-1`/`grass=0` every time, Flik's
> full-ant model intact, no crash. **Diagnosis note:** execTrace/accessLog *counts* were unreliable here (0 hits even on
> `0x80064618` DrawOTag which draws every frame) — the decisive evidence was **behavioral** (force value → advance → read).
> The DIRT (tp604) terrain is still deliberately kept (its count lever also drops Flik). C: `mod/caves/tier3_otrender.c`.

> [!success]- ✅ Flik's model is garbage (torso missing) — a Phase-3 terrain-stub regression
> **Symptom:** In the Tier-3 custom LEVEL01, Flik renders as a **headless/torsoless thin-limb figure** (thin blue arms +
> legs + antennae, no body) instead of the proper native ant — idle AND moving. Compared to pristine, "Flik is all garbage."
>
> - Goal to fix: Flik should look like the native ant (as in the earlier Tier-3 builds).
>
> - **FIXED 2026-07-01 (revert, cold-boot verified):** a **regression from the Phase-3 chunk-35 terrain stub**
> ([[Tier 3 - Level Replacement Phases]]). Phase 3 baked a COPIED-gated neuter of `FUNC_800172DC` (the resident chunk-35
> terrain submitter) to hide native terrain at source. **Root cause:** `FUNC_800172DC` is **NOT terrain-only** — it is one
> of ABL's generic GTE mesh submitters, **SHARED by terrain AND the player**, so stubbing it also dropped **Flik's body
> mesh** (his limbs are built by other submitters, so they remained → the thin-figure look). **Diagnosis (decisive A/B,
> live LEVEL01):** with our render hook OFF Flik was *still* garbage (ruling out our renderer); restoring `FUNC_800172DC`'s
> prologue at `0x800172DC` (`0x0801fcd0`→`0x3c021f80`) brought Flik's **torso back WHOLE**; re-applying the neuter removed
> it again. The Phase-3/Phase-1 "verification" was a **false pass** — it checked the terrain census + Flik's *state*
> (position/grounded), never his *model*, so the missing torso went unnoticed (the thin figure in the Phase-3 captures was
> misread as an animation pose). **Fix:** reverted the `FUNC_800172DC` hook + `tier3_neuter_172dc` + the `fname` move in
> `mod/tier3_loader.asm`; rebuilt `build/ABL_tier3_render.cue` (`.bin` sha256 `86b59297…` == the Phase-2 EXE). **Verified
> cold-boot:** Flik renders as the proper full ant (head/body/antennae/arms/legs), `COPIED=1`, `0x800172DC=0x3c021f80`
> (native), collision + spawn intact. **Trade-off:** the ~50% pose-dependent chunk-35 terrain suppression is gone; that
> terrain is instead removed the correct way via the **data-source path** (Phase 4 — empty a terrain render-LIST/source;
> NOTE: only the GRASS source-truncation is Flik-safe — the DIRT count lever ALSO drops Flik, see the entry above). **LESSON
> baked into the RE:** never render-side-stub a shared submitter, and ALWAYS verify Flik's *model* (capture), not just his
> state, after a render change. C/asm: `mod/tier3_loader.asm`; RE: `src_re/world_render_dispatch.c`.

> [!success]- ✅ LEVEL00 loads broken (flat void, Flik warped) — the engine leaked out of LEVEL01
> **Symptom:** Loading LEVEL00 on the Tier-3 disc is affected even though only LEVEL01 is meant to be modified. Repro: `LEVEL00_load.movie.json` (from-boot) → LEVEL00 renders as a **flat tan void with no terrain**, Flik warped to a wrong spot. Reference: same movie on the pristine disc.
>
> - Goal to fix (if required): LEVEL00 should load properly. If it's expected disregard this issue.
>
> - **FIXED 2026-07-01 (cold-boot DuckStation-verified):** the Tier-3 engine lives in the **RESIDENT EXE** (`SCUS_942.88`), which is shared by every level — so its hooks fire in LEVEL00/LEVEL02/… too, not just the custom LEVEL01. **Root cause:** the render-loader trampoline `tier3_load_render` (`0x8007F288`, `mod/tier3_loader.asm`) CD-loaded `level01\tier3.rnd` on the **first spawned-Flik frame of ANY level, with no level check**. In LEVEL00 that (a) set `COPIED=1` → the `fcn.80010000` neuter (statically hooked at `0x80010000`, gated only on `COPIED`) killed **LEVEL00's native ground build**, and (b) loaded the `T3LV` blob into `0x801F2C00` → `tier3_collision_hook` (gated only on `LV_MAGIC`) then **warped Flik to LEVEL01's custom spawn** and ran LEVEL01's mesh in LEVEL00. **Diagnosis (decisive), `LEVEL00_load.movie.json` to frame ~4100, tier3 vs pristine:** tier3 LEVEL00 = `COPIED=1`, `LV_MAGIC=0x564c3354`, Flik `(197091,-266,492897)` (= the LEVEL01 custom spawn), `@0x80010000=0x0801fcc1` (neuter hook); pristine LEVEL00 = `COPIED=0`, `LV_MAGIC=0`, Flik `(-22044,15860,-19597)` (LEVEL00's real spawn), `@0x80010000=0x23bdffe0` (native prologue). Both discs share `DATbase=0x8011cc50` for LEVEL00 (LEVEL01's is `0x801607F8`), confirming the level identity. **Fix — gate the engine strictly to LEVEL01** using the live `DAT_BASE` (`0x80082498`, == `0x801607F8` only in LEVEL01): (1) `mod/patch_tier3_collision.asm` — `tier3_tramp` now only routes to `tier3_load_render` when `DAT_BASE==LEVEL01`; other levels resume the player update with NO CD-load / NO DrawOTag-hook install / NO `COPIED` set. (2) `mod/caves/tier3_collision.c` — `tier3_collision_hook` bails out in any non-LEVEL01 level, publishing `FLOOR_PUB=NO_FLOOR` (so the `0x800495dc` jump-fix hook falls through to native) and clearing `COPIED=0` (so the `fcn.80010000` neuter stays inactive there **even after a prior LEVEL01 visit** — handles the LEVEL01→LEVEL00 transition, not just a direct boot — and the loader re-arms on the next real LEVEL01 entry). The DrawOTag render stub `loader_stub` already self-gated on `DAT==LEVEL01`, so no change there. **Verified (cold-boot, rebuilt `build/ABL_tier3_render.cue`, `TIER3_KEEP_BLOB=1`, operator's level preserved):** (a) `LEVEL00_load.movie.json` → LEVEL00 now `COPIED=0`, `LV_MAGIC=0`, Flik at the **real** spawn `(-22044,15860,-19597)`, native ground/terrain/tutorial-sign all render (matches pristine); (b) `flik_to_level01_stall.mv.movie.json` → LEVEL01 still `COPIED=1`, `LV_MAGIC=T3LV`, Flik at the custom spawn, custom textured floor + grains + HUD render as before — the gate correctly ALLOWS the engine in LEVEL01. C/asm: `mod/caves/tier3_collision.c` (`DAT_BASE`/`LEVEL01_DAT_BASE` gate), `mod/patch_tier3_collision.asm` (`tier3_tramp` LEVEL01 gate). **Fast-forward note:** `emulator.advanceFrames` is a deterministic frame-STEPPER (`System::FrameStep`), it does NOT uncap the speed limiter — frames play at the current emulation speed (100% = realtime). To fast-forward a from-boot movie, call `emulator.setTurbo {enabled:true}` (or `setFastForward`) first (measured ~5760 emu-fps vs ~60), then `advanceFrames`.

> [!success]- ✅ After starting and exiting a level, there is no longer a fade in or out
> **Symptom:** After starting and exiting a level there is no longer a fade in/out — the screen snaps between black and full-bright instead of the smooth fade the pristine image shows. Repro: `InAndOut.movie.json` on both the pristine and tier3 discs.
>
> - Goal to fix: it should look like the fade in/out on the pristine image.
>
> - **FIXED 2026-07-01 (cold-boot DuckStation-verified):** the in-gameplay screen fade is a **full-screen semi-transparent GP0 `0x62` rectangle** (mono, size 512×240, drawn LAST at the front OT bucket, semi-transparency **mode 2 = subtract**, color `(128−prog)*2` where `prog`=`[0x80082388]`); as `prog` drops 128→0 it subtracts more → the scene darkens to black. The **render cave's `suppress_terrain` (`mod/caves/tier3_otrender.c`) was COLLAPSING that fade rect.** Its `is_terrain_cmd()` classified **every** GP0 `0x60..0x7f` (rect/sprite) as native grass/plant/leaf decor to hide; the fade rect is `0x62` (in that range) and — being allocated at a HIGH prim address — passed the offset gate, so `suppress_terrain` set its tag length to 0 → the rect was never sent to the GPU → **no darkening** for either the level-start fade-in or the level-exit fade-out (both use the same `0x62` overlay). The fade STATE machine, the resident fade-rect builder (`FUNC @0x80028d74`, builds the 512×240 rect keyed on `[gp+0x5f0]`=`0x80082388`), and the fade color/timer (`[0x80082470]`) all ran correctly — only the draw was being dropped. **Diagnosis (decisive):** `gp0Trace` at a matched fade frame — pristine has the `0x62` rect (last command, `0x62909090` at prog 56); tier3 has **zero** `0x62`. Live-neutering `tier3_otrender_hook` made the `0x62` **reappear** (count 0→1, `0x62a8a8a8`), pinning the drop to `suppress_terrain`. (Earlier brightness-only A/B tests were misled by movie replay timing + double-buffering; the GP0-command trace is unambiguous.) **Fix:** `is_terrain_cmd()` now suppresses only **TEXTURED** sprites/rects (`cmd & 0x04`, i.e. `0x64..0x67`/`0x6c..0x6f`/`0x74..0x77`/`0x7c..0x7f` = the actual native decor) and **spares untextured mono rects** (`0x60/0x62/…`) — the fade overlay and any HUD letterbox bars. Native terrain (gouraud `0x3c`/`0x34`) and textured decor sprites (`0x65`) are still suppressed unchanged. **Verified:** (1) live inject of the recompiled render at `0x801F0C00` → `0x62` survives (`gp0Trace`), preceded by `0xe1000640` = STP mode 2, and the exit fade darkens frame-by-frame (prog 128→68: mean 99→26.5); (2) **cold-boot** of the rebuilt `build/ABL_tier3_render.cue` (`.bin` sha256 `ef254d95…`, `TIER3_KEEP_BLOB=1`, operator's level + native objects preserved) via `InAndOut.movie.json` → level-start fade-to-black is smooth (prog 122→0, mean 104→0) and the level-exit fade-out darkens progressively (prog 128→38, mean 99→6.7), closely matching pristine (pristine prog80→mean 24.8, fixed prog80→30.6). C: `mod/caves/tier3_otrender.c` `is_terrain_cmd()`. See [[Gameplay - Warp and Level Transition]] for the fade state machine (`0x80054aac/0x80054ad4`, lever `0x800823a0`, color `0x80082470`).

> [!success]- ✅ FLIK letters are not present when I attempt to grab them
> **Symptom:** FLIK letters are not present when I attempt to grab them. I confirmed their locations in Blender, but they are not collectible nor visible.
>
> - Goal to fix: be able to see FLIK letters on the platform.
>
> - **FIXED 2026-06-29 (DuckStation-verified):** authored FLIK entries were present in the type-`0x3f` table, but live RAM showed their Y drifting from the authored file coord `-321` to values like `-2362/-2828/-6305/-3093` before collection, leaving the letters away from the Blender platform. `tools/build_tier3_render_disc.py` now generates `build/tier3_native_pin.h` from the same native-object sidecar used for DAT relocation; `mod/caves/tier3_walls.c` pins authored FLIK slots 50-53 back to their authored X/Y/Z each gameplay frame until the native FLIK bit is set. On collection the pin stops, so the native consumed sentinel `Y=0x80000000` remains. Also moved the loaded cave layout to `WALL_FN=0x801F0100`, `FLOOR_FN=0x801F0900`, `RENDER_C=0x801F0C00` after the pin grew `tier3_walls.o` to `0x760`; build assertions now guard the segment budgets.
>
> - Evidence: cold-booted rebuilt `build/ABL_tier3_render.cue` in DuckStation, replayed `flik_to_level01_stall.mv.movie.json` to frame 4254, media path verified. Live entries 50-53 stayed at `(7315,-321,15122)`, `(7472,-321,15309)`, `(7628,-321,15497)`, `(7784,-321,15684)`, kinds `0x10..0x13`, status `1`. Warping Flik onto each letter and advancing frames set `0x800A65A2 = 0x0f`; all four entries then had `Y=0x80000000`.

> [!success]- ✅ Grains leave behind some weird texture residue alongside them
> **Symptom:** Grains leave behind some weird texture residue alongside them.
>
> - Goal to fix: remove the texture so that it's only grains visible.
>
> - **FIXED 2026-06-30 (DuckStation-verified):** the "residue" was **Blender viewport-marker geometry leaking into the level floor mesh**, NOT a render bug and NOT the native grains. In `mylevel.blend` each grain is an EMPTY (`Grain1..6` → correct native type-0x3f placement), but the operator had also added per-grain **`GrainVisual.GrainN.0/1/2` MESH icons** (3 crossed 2000u quads each, tagged custom prop `abl_type='grain_visual'`) just to SEE the invisible empties. `tools/tier3_blender_export.py` didn't honor that tag, so those 18 marker quads (+ the `GrainVisual_Source` template) fell through to the geometry path and baked into `faces` → our render cave drew them as dirt-textured squares **at every grain, persisting after collection** (static floor geometry, not the collectible). Diagnosed via `gpu.pickObject` (squares = native/our-mesh prims at the grain XZ) + offline `build/mylevel.json` analysis (18 faces clustered on the 6 grain positions, color `0x20CCCCCC`) + headless Blender object dump (the `abl_type='grain_visual'` meshes). **Fix:** the export now SKIPS any object whose `abl_type` custom property contains `"visual"` (viewport-only helper) — neither floor geometry nor a placement. Re-ran `tools/tier3_build_level.sh build/mylevel.blend`: faces 109→90 (markers gone), 13 native placements intact, grain-position faces 19→1 (only the legit wide platform). Cold-booted `build/ABL_tier3_render.cue` → grain platform renders clean, no square grid; grains still placed + HUD counts. (NOTE: a separate, still-open artifact = a few **surplus/unauthored native LEVEL01 collectibles** — 44 extra grains + berries/seeds the build can't delete because deleting before the FLIK slots would renumber the FLIK pin — float at their original LEVEL01 coords in the custom void. That's a different bug from the GrainVisual squares.)

> [!success]- ✅ Current ground texture sits on top of almost everything: Flik, the seed power in the bottom right, the star…
> **Symptom:** Current ground texture sits on top of almost everything: Flik, the seed power in the bottom right, the start menu, grains, FLIK letters, etc..
>
> - Goal to fix: Ground must be set to the background but still in front of the real background drop (which is a blue colour at the moment)
>
> - **FIXED 2026-06-30 (DuckStation-verified):** the custom ground is now a true BACKDROP — it draws in front of the blue sky but behind the entire native scene (Flik, objects, HUD/seed-power). **Root cause:** the DrawOTag DMA kick `0x80064618` fires for SEVERAL OT chains per displayed frame (live `execTrace` on the hook entry `0x8007F174`, capture `a0`): a BACKGROUND chain drawn FIRST whose head is a populated env+sky node (tag length≠0, e.g. heads `0x801e1368`/`0x801cc3ac`, 1 node = E3/E4/E5+`GP0(02)` sky fill), then the SCENE chain whose head is an empty ClearOTagR bucket (tag length==0, heads `0x801cd870`/`0x801e282c`, ~1200-1600 nodes) holding native terrain + Flik + objects + the HUD/seed-power overlay. `mod/caves/tier3_otrender.c` PREPENDED our textured ground into the **scene** chain. Even though that put it behind Flik (live-confirmed: `a0`=NODEBUF `0x801F9400` at the MADR store `0x80064638` → DMA starts from our ground → Flik on top), the seed-power overlay and other elements draw in a layer our scene-pass ground ended up in front of, so the **bottom-right HUD mushroom was covered** (clean same-state A/B on `artifacts_2.sav`: native hook → mushroom visible; our hook → dirt). `suppress_terrain` was ruled out (scene max OT offset `0x17a4` < GATEOFF `0x1801`, no `0x2e/0x3e` prims → it collapses nothing here). **Fix:** discriminate the pass by the head node's tag length and render our ground/markers ONLY in the BACKGROUND pass, APPENDED after the sky node (cheap, cycle-free — the bg chain is 1 node and our chain terminates); the SCENE pass now does `suppress_terrain` ONLY (no ground). So the sky fills first, our ground draws over it, then the whole native scene composites on top. `MODE`/prepend/append-to-scene removed. **Verified:** cold-booted the rebuilt `build/ABL_tier3_render.cue` (`.bin` sha256 `70b3bf54…`) via `flik_to_level01_stall.mv.movie.json` — at spawn AND at a grazing angle (Flik warped to the FLIK-letters platform) the ground renders as a backdrop, Flik is fully on top, and the **HUD seed-power mushroom is restored** (bottom-right); `gpu.pickObject` at the HUD pixel returns a scene prim (`0x001e29xx`) on top, not our NODEBUF ground. Roam test (Down/jump/Up/butt-slam) stayed stable (`pc` in user RAM, `DAT`=`0x801607f8`, SENT incrementing, collision intact). **Note:** the separate "objects float in the air with dirt texture" artifact (gold FLIK letter / berries) is NOT this bug — it is present in the NATIVE render too (those are surplus/unauthored native LEVEL01 collectibles left at original coords; build `[6n]` warns "may float in the void"). The "ground over the start menu" symptom also does not recur: the pause menu is drawn by a path that does NOT call our hook (live: SENT delta 0 while paused), and the bg-pass backdrop stays behind it regardless.

> [!success]- ✅ Walking animation does not work properly
> **Symptom:** Walking animation does not work properly. It seems to freeze an animation. If I jump, when Flik lands, he's still stuck in the jumping animation. Similar with butt-slaming, doesn't buttslam properly like the pristine image)
>
> - Additional note: after dying (jumping off), Flik walks normally, until he jumps or buttslams
>
> - Goal to fix: Flik must be able to move, and move like he did in the pristine image, and buttslaming is functional like the pristine image (pressing X after jumping via X)
>
> - **FIXED 2026-06-30 (cold-boot DuckStation-verified):** the player **GROUNDED flag** `[player+0x82]` (halfword, grounded=`0x0101`) was never re-set on our custom floor, so Flik was permanently "airborne" and his animation state machine never ran the landing transition. **Root cause:** the movement integrator `FUNC_8003633C`'s collision path (grounded SET access-log-attributed `~0x80036cbc/0x80036cd0/0x80036b90`; exact store not pinned, see body) sets `[player+0x82]=0x0101` ONLY when **native collision** reports ground contact — but Tier-3 SUPPRESSES native collision (deepened sectors + zeroed swept planes in `tier3_walls.c`), so the integrator finds no contact and grounded stays `0` forever. The player update `FUNC_80048138` reads grounded each frame: when set it resets the air-state `[player+0x80]=0` and lets the landing transition run (jump-fall anim `4` → landing anim `5` → idle anim `22` / walk anim `0`); when clear, every `sh ...,0x82(s1)` in that function only ever *clears* it (the SET lives solely in the suppressed integrator). So after any jump/butt-slam Flik was stranded in the jump-fall pose and walking slid in that frozen pose. (The "after dying Flik walks normally until he jumps" clue = a full GAME-OVER reload re-inits the struct grounded; the first jump clears it and it never comes back.) **Fix:** `mod/caves/tier3_collision.c` now re-publishes the grounded flag itself — `FLIK_GROUNDED = 0x0101` inside the existing landing/rest branch (`yf != NO_FLOOR && FLIK_VY >= 0 && y > yf - GROUND_MARGIN`), supplying the exact signal the suppressed integrator can't. The `vy>=0` gate leaves jumps/butt-slams (rising, `vy<0`) untouched; the integrator clears the flag each frame but `FUNC_80048138` reads OUR value (set the prior frame, before the integrator runs). Value `0x0101` matches what the native integrator writes (verified live on the pristine disc: idle grounded = `0x0101`). **Verified (cold-boot `build/ABL_tier3_render.cue`, `.bin` sha256 `2ce2c06a…`, movie `flik_to_level01_stall` to spawn, NO live pokes):** (1) **walk** cycles (legs step; anim `22`→`0`, gameplay frames captured), (2) **jump→land→idle** reproduces the exact pristine transition (anim `22`→`3`→`4`→land sets grounded→st80→0→anim `5`→`22`), (3) **butt-slam** (X at apex) engages st80=`3` then lands+recovers to idle, (4) **no infinite-jump** — spam-X climb `14080` == pristine `14080` (held-X full jump arc, then lands; not unbounded). Live A/B before fix: with grounded held 0 the anim freezes forever at `4` (control), setting grounded reproduces the pristine recovery. RE evidence: pristine landing trace on `level01_lookingdown_flatground.sav`. See [[#Walking animation freeze — ROOT-CAUSED + fixed (2026-06-30)]].

> [!success]- ✅ Draw distance is poor at the moment
> **Symptom:** Draw distance is poor at the moment. Load draw_distance_poor.sav for a better view, the ground, collectibles, objects, etc, are not very visible. You have to walk up and it loads about a few feet in front of Flik.
>
> - Goal to fix: should be able see far in front of Flik, akin to the original game.
>
> - **FIXED 2026-06-30 (cold-boot DuckStation-verified):** the limiter was the render cave's **distance cull `FARZ=60000`** in `mod/caves/tier3_otrender.c` (a tri whose 3 verts are all beyond view-space-Z `FARZ` is dropped before clip+draw). Measured live on `draw_ditance_poorv2.sav` (the operator's v2 save; the original `draw_distance_poor.sav` predates the current level rebuild) at the true render-hook camera (broke at the DrawOTag hook `0x8007F174` to read the live camera `R@0x80090FB0` + `C@0x1F800374` — reading `C` while paused gives a *stale/reused* scratchpad value, so the breakpoint capture is mandatory): `FARZ=60000` culled **39 of the level's 180 tris**, all on-screen in a thin horizon band (screen X159–343, Y121–138) — i.e. the far ground/collectibles only "loaded" as Flik walked toward them. **Fix:** raised `FARZ` `60000 -> 200000` (the authored sample maxes at view-Z ~96000, so the whole level now always renders; the cull stays only as a far-horizon / `NODE_MAX` runaway guard for very large open levels). Safe because the residual grazing lag (Phase 4h/4i, mode-2 PS1 texture-cache thrash) is caused by the **big NEAR floor tris, not the far slivers**, and the CPU per-tri clip cost (mode-1) is already absorbed by the cull-before-clip + trivial-accept path. **Verified:** (1) same-pose live A/B on the v2 save (inject the recompiled render segment at `0x801F0C00`): the horizon band's blue-sky pixels dropped **18713 -> 8067** — the far ground now fills ~10.6k px that were sky — at **~30 fps unchanged** (captures `band_before/after.png`); (2) **cold-boot of the rebuilt `build/ABL_tier3_render.cue`** (`TIER3_KEEP_BLOB=1` rebuild, operator's 180-tri level preserved, native objects intact) via `flik_to_level01_stall.mv.movie.json` to spawn: ground renders to the horizon, **30 fps at spawn, walking, AND a hard camera-pan to a grazing angle** (no wedge, no triangular holes, jump stable, `SENT` hook-counter incrementing throughout). NOTE: a transient **0-fps reading on the OLD dense `lag_v3.sav` was an I-cache inject artifact** (the live 6 KB code overwrite corrupted one frame's OT node → GPU DrawSync wedge), NOT a real FARZ effect — confirmed by the emitted node count being **identical (151) before/after** the inject; the gold-standard cold-boot has a clean I-cache and shows no such issue. CAVEAT (honest): a *future* very-large/dense level viewed at a grazing angle could re-expose mode-2 grazing fill at a larger radius (the accepted known limit); tune `FARZ` per-level or pursue the GTE render path if that arises.

> [!success]- ✅ Objects render poorly: with `draw_ditance_poorv3.sav` the **grains flicker on the left** and the **F/L/I le…
> **Symptom:** Objects render poorly: with `draw_ditance_poorv3.sav` the **grains flicker on the left** and the **F/L/I letters are barely visible** (flickering, less often than the grains).
>
> - Goal to fix: the grain and the letters must be **always visible** (with draw distance still good).
>
> - **FIXED 2026-06-30 (cold-boot DuckStation-verified):** root cause was the render cave's **`suppress_terrain`** (scene-pass native-terrain hider in `mod/caves/tier3_otrender.c`) **collapsing the authored OBJECT prims, not just terrain.** The native LEVEL01 terrain is built ONCE at level-load and stays RAM-resident (the `fcn.80010000` stub only prevents a *rebuild*, per GAP-T3-5), so `suppress_terrain` must collapse its OT nodes every frame — but its two rules were too broad: (a) the blanket **drop-cmd-`0x2e`/`0x3e`** rule killed the **FLIK letters**, which the native renderer draws as semi-transparent flat polys (GP0 `0x2e`); (b) the **`offset > GATEOFF(0x1800)`** rule clipped the **grains**, drawn as flat textured quads (GP0 `0x2c`) — and as their per-frame OT offset drifted across the gate in real time they **FLICKERED** (frame-step is deterministic so my static captures showed them steady — the flicker is real-time only, matching the report). Diagnosed via a live OT walk at the v3 pose + `gpu.pickObject`: native terrain mesh = **GOURAUD-textured polys** (`0x3c`×91 quads, `0x34`×21 tris) and native decor = **sprites** (`0x65`×27), whereas grain=`0x2c` (clut `0x3677`) and FLIK letter=`0x2e` (clut `0x3672`) are **FLAT** polys. **Fix:** rewrote `suppress_terrain` to drop ONLY terrain-class prims — `is_terrain_cmd()` = GOURAUD-textured polygon (`0x34-37`/`0x3c-3f`) OR sprite/rect (`0x60-7f`) — and **spare flat object polys** (`0x2c` grain, `0x2e` letter, our `0x24` ground). The offset gate is kept (Flik the *character* is also gouraud but built LOW in the OT, so only HIGH-offset gouraud = terrain). Because `0x2c`/`0x2e` are now classed non-terrain, they are **never collapsed regardless of OT offset** → the offset-crossing flicker is eliminated by construction, and the cmd-`0x2e` letter-kill is gone. **Verified:** (1) same-pose live A/B inject on the v3 save: with the refined cave the **FLIK letters render clearly** (gold "L I K" + sparkles) and the **grain** shows, while the **native dirt/grass terrain stays hidden** (disabling suppress entirely, by contrast, floods the whole native terrain back — proving suppress is still required); (2) **cold-boot of the rebuilt `build/ABL_tier3_render.cue`** (`TIER3_KEEP_BLOB=1`, level + native objects preserved): walked Flik to the letters platform and captured 8 consecutive frames — grains + "K" letter **stably visible every frame** (gold-pixel count 20k-22k, no drops), terrain hidden, draw distance still good. RESIDUAL (pre-existing, NOT caused by this fix — same behavior as the old suppress): native terrain that happens to be at **LOW OT offset** at certain camera angles (verified gouraud `0x3c`/`0x34` via `gpu.pickObject`) leaks through the offset gate (a green grass sliver / brown dirt wedge), because low-offset gouraud is indistinguishable from Flik by the current discriminator. That is the deferred Track-B / true-terrain-replace RE work (build-remove the terrain *submitter*, or a clut-based discriminator), out of scope for the grain/letter visibility ask.

> [!success]- ✅ Objects (FLIK letters, and potentially others) are **fully visible even when they are underneath the ground…
> **Symptom:** Objects (FLIK letters, and potentially others) are **fully visible even when they are underneath the ground** — they should be occluded by the custom floor. Saves: `visible_through_ground.sav` (newer build, letters lowered below the ground) and `visible_through_walls.sav` (older build).
>
> - Goal to fix: an object below/behind the custom geometry must be hidden by it.
>
> - **FIXED (below-ground case) 2026-06-30 (cold-boot DuckStation-verified):** root cause is architectural — our custom ground is a **BACKDROP** (drawn in the background OT pass), so the native renderer always composites the scene objects ON TOP of it; a FLIK letter authored below the floor still draws over the ground. PS1 has **no Z-buffer**, so true occlusion needs our geometry **depth-sorted into the native scene OT** — investigated and found feasible-but-risky: the scene OT is a clean 1228-entry bucket array (`OTBASE=0x801e1500`, head=far) but the native GTE→`otz` depth scale vs our software `PVZ` is **noisy/nonlinear** (a mis-sort corrupts the DMA chain), so depth-insertion was deferred. Instead implemented **geometry-driven occlusion** using our exact floor knowledge: in `mod/caves/tier3_otrender.c` the scene pass now reads every authored `type-0x3f` object, queries our floor (`FLOOR_FN`/`tier3_floor_y` with a very-high reference Y = topmost surface), and if the object is **buried** (`ry > floorY + OCC_MARGIN`, `OCC_MARGIN=2000`) with the **camera above the floor**, projects it and adds a screen box; `suppress_terrain` then collapses the object's render prims (flat textured polys / sprites `0x2c/0x2e/0x24/0x26/0x64/0x65`; Flik is GOURAUD so never matched) inside any box. (`RENDER_PAD` bumped `0x2800→0x2C00` for the extra code; blob→`0x801F2C00`.) **Verified (cold-boot, occlusion ON vs a `-DOCC_ON=0` baseline disc, same fixed walk):** at the buried-letters area the live classifier confirms the 4 grains RESTING on the floor (`ry≈floorY`) are kept and the buried letters L/I/K (`ry−floorY ≈ +7500..8800`) are flagged occlude; the ON frame shows the **buried letters hidden** with the resting grains + HUD intact, while the OFF frame shows the letters poking through the ground. KEY DIAGNOSIS GOTCHA: a RAM **warp** of Flik desyncs the follow camera (scratchpad C ends up *at* the object → everything projects "behind camera"), so verify occlusion only in NORMAL gameplay (walked), where the cave's camera matches the native object projection within ~8px. **LIMITATIONS (honest):** (1) this is a **floor-height heuristic, not a true view-ray raycast**, so at grazing angles or near a ground EDGE a buried object can still peek through; (2) it only handles **below-floor** occlusion — objects **behind a WALL** (`visible_through_walls.sav`) are NOT handled (would need a wall-segment raycast against `LV_WALLS`, or the deferred depth-sort); (3) the screen-box (`OCC_R=9000` world radius) can over/under-cover at extreme projection mismatch. The general, complete fix remains the **GTE-render / depth-sorted-OT path** (also fixes affine warp + the low-offset terrain leak), deferred. **PERF FOLLOW-UP: the first occlusion implementation ran the O(ntris) floor query for EVERY on-screen object EVERY frame → a severe FPS regression while rotating (see the "lag" BUGS entry below); fixed by amortizing to 1 query/frame (Phase 4m).**
>
> - **STRADDLE FOLLOW-UP — FIXED 2026-06-30 (movie `items_visible.movie.json`, cold-boot verified):** operator clarified the real case — the F/L/I/K letters are placed **straddling** the floor/platform edge (anchor **454–1734 ABOVE** the floor, but the glyph body extends BELOW it → "half-and-half"), and poke through the geometry. The original `OCC_MARGIN=2000` only caught objects whose ANCHOR is ≥2000 **below** the floor, so a straddling object was never flagged (`OCC_MASK=0`). **Fix:** `OCC_MARGIN` `2000 → -2000` (a NEGATIVE margin = occlude an object whose anchor is up to 2000 **above** the floor too, i.e. "not entirely above it"), and `OCC_R 9000→11000` (bigger box, less projection-mismatch peek). **Verified on the operator's movie:** at the final frame the 4 straddling letters now flag occlude (`OCC_MASK` bits 50–53 set) and are **hidden** (were poking through the platform side), while the **rotation lag stays fixed (29–30fps)** — the amortized 1-query/frame keeps it fast despite more objects flagged. **CAVEATS:** (a) PS1 has no Z-buffer so this is **all-or-nothing per object** — the WHOLE straddling object is hidden, not just its sub-floor part (true partial "half-and-half" still needs the deferred GTE depth-sort path); (b) the negative margin also hides any collectible placed **within ~2000 units above the floor**, so place collectibles you want visible higher than that; (c) **surplus/unauthored native objects floating in the VOID** (`NO_FLOOR` — the 44 extra grains/berries/seeds the build can't delete) are NOT occludable (no floor under them) and remain visible — a separate build/cleanup issue, not occlusion.
>
> - **OVER-OCCLUSION + WALL-OCCLUSION FOLLOW-UP — FIXED 2026-06-30 (`grain_invisible_until_right.sav` + `items_visible.movie.json`, cold-boot verified):** two coupled defects surfaced from the straddle fix. (1) **Over-occlusion:** the screen-BOX (`OCC_R`) collapsed EVERY object-class prim inside a buried object's box, so a VISIBLE grain sitting on-screen next to a buried letter was wrongly hidden (`grain_invisible_until_right.sav`: grain gone until you tap right and the camera slides the box off it). **Fix:** replaced the box with **NEAREST-OBJECT ATTRIBUTION** — project ALL on-screen authored objects into `ox/oy` with a per-object `obur` occluded flag, and in `suppress_terrain` match each object prim to its NEAREST object, collapsing it ONLY when that nearest object is occluded (`OCC_THRESH=50`px bounds "belongs to"). A grain prim is nearest its own visible grain → kept; a buried letter prim is nearest the buried letter → dropped. (2) **Wall occlusion:** with the box gone, grains tucked BEHIND a platform's side wall showed through (the floor query skips steep wall tris, so `behind_wall` objects that are ABOVE the floor were never flagged). **Fix:** added a cheap **per-frame wall ray-test** — the camera→object XZ ray crossing a level wall segment (`LV_WALLS`) while the object's Y is in that wall's `[ytop,ybot]` band ⇒ occluded; `obur = cached-below-floor-bit OR behind-wall`. Camera-dependent (correctly re-evaluated each frame) and cheap (~nwalls×on-screen-objects ray tests, no O(ntris) scan). **Verified:** in `items_visible` the behind-wall grain cluster is now HIDDEN while the in-front above-floor "F" stays visible; from the `grain_invisible` angle the SAME grains (not behind a wall there) are correctly VISIBLE; buried letters stay occluded; and the **rotation lag movie still runs 30fps** (both the nearest-object match and the wall ray-test are cheap). Net: `OCC_R`→`OCC_THRESH`, `OCC_MAX 24→40` (now an object list, not a box list); handles below-floor + behind-wall occlusion without over-hiding neighbours. (Still all-or-nothing per object — partial "half-and-half" remains the GTE-path job.)
>
> - **PARTIAL OCCLUSION = requires the GTE render path (probed + confirmed 2026-06-30, `occlusion_issue.sav`).** Operator wants the REAL behaviour: an object slightly in the ground or partly behind a wall should be **partially** covered (per-pixel, gradual as the camera pans), like real life — not pop fully in/out. That is impossible with the current fake-occlusion (collapse whole object prims) because PS1 has no Z-buffer and our renderer software-projects our geometry as a flat BACKDROP with NO depth relationship to the game's GTE-drawn objects. The correct fix is to **depth-sort our floor/wall triangles into the game's ordering table** (insert each tri at its `ot[otz]` bucket) so the hardware draws a wall's pixels over only the overlapping part of an object behind it. **Probed the cheaper software depth-sort and it is NOT viable:** the map from our software `PVZ` to the native GTE `otz` bucket is too noisy/nonlinear to calibrate (measured (PVZ,otz) pairs at the occlusion pose fit `otz≈-0.008·PVZ+1297` with **residuals ±340 buckets** out of 1228 — several PVZ values map to wildly different otz). So correct depth needs the object projected through the **GTE (COP2 RTPS)** like the native renderer, which returns the exact `OTZ` — i.e. the deferred **GTE render path** (also fixes the affine texture warp). Scope: a substantial core-renderer rewrite (GTE setup with the game's camera R/TR + projection H, per-vertex RTPS → screen+OTZ, near-clip, `ot[OTZ]` splice via the confirmed `OTBASE=head-(1228-1)*4` / size-1228 bucket array). Recommend a SPIKE first (prove GTE depth + one-tri insert composites correctly vs one object) before committing, so the working all-or-nothing occlusion + lag fixes aren't put at risk.
>
> - **DEPTH-SORT SPIKE — SUCCESS (2026-06-30, `occlusion_issue.sav`).** Proved the core mechanism before the full rewrite. Added a `#ifdef SPIKE` block in `mod/caves/tier3_otrender.c` that splices ONE flat quad into the SCENE OT at a live-tunable bucket (`0x801FE030`), `bucket_addr = (head&0x1FFFFF) − 1227·4 + bkt·4`, node = GP0 `0x28` (5 words), spliced via `node.next = bucket.next; bucket.next = node`. Injected on the save and swept the bucket: **near bucket (300)** → the quad draws IN FRONT of Flik's body + ground (behind HUD/"F"); **far bucket (1150)** → Flik and a grain draw OVER the quad — **per-pixel where they overlap** (Flik's body composites on top, quad shows around him). So: (a) OT splice is **crash-free** (SENT keeps incrementing), (b) the bucket controls depth ordering, (c) compositing is **per-pixel** = the real partial occlusion the operator wants. Screenshots `spike_300.png`/`spike_1150.png`. GTE facts gathered for the real impl: `getGteState` → `OTZ = ZSF3(≈333)·(SZ1+SZ2+SZ3)>>12`, `screen_offset=(256,120)` (== our OFX/OFY), camera R at `0x80090FB0`, OT size 1228. **REMAINING for the full render (de-risked, substantial):** compute the correct bucket per triangle — either GTE COP2 RTPT (exact, but needs the game's coordinate scale + s16 vertex handling) or an empirically-tuned software `bucket=f(PVZ)` map — then build the textured floor/wall tris, insert ALL of them at their depths, and retire the backdrop + the fake object-occlusion (nearest-object/wall-ray) hacks. Mechanism proven; the calibration + render conversion is the next chunk.
>
> - **DEPTH-SORTED RENDERER — DONE 2026-06-30 (`occlusion_issue.sav` + all occlusion movies/saves, cold-boot verified). This REPLACES all the fake-occlusion hacks with real per-pixel occlusion.** Converted `mod/caves/tier3_otrender.c` from the flat BACKDROP to a depth-sorted renderer: the render now runs in the **SCENE pass** (was background), and each floor/wall/marker triangle is **spliced into the scene ordering table at its own depth bucket** (`bucket = (PVZ_avg·DS_MUL>>16)+DS_BASE`, `otbase = head−(OT_SIZE−1)·4`, `node.next = ot[bucket].next; ot[bucket].next = node`) instead of appended as a backdrop. The PS1's back-to-front DrawOTag then composites our geometry **per-pixel** with the native objects. **Calibration:** the GTE/software `otz` map is too noisy to derive analytically, so `DS_MUL` was made **live-tunable (0x801FE030/34)** and tuned visually on `occlusion_issue.sav` — `DS_MUL=978 (≈65536/67)`, `DS_BASE=0` lands our floor in the same bucket as objects resting on it; baked as `#define`. **Removed (superseded by the depth-sort):** the whole nearest-object / wall-ray / round-robin-floor-query object-occlusion block, the `OCC_*`/`FLOOR_FN` helpers, the backdrop-append tail, and the SPIKE; `suppress_terrain` slimmed back to terrain-only. **Verified end-to-end:** (a) `occlusion_issue.sav` pan → items are **GRADUALLY covered** by the platform edge as the camera moves (per-pixel, not popping) — exactly the operator's ask; (b) `items_visible` final → the behind-wall grain cluster is **partially occluded** by the platform, in-front "F" stays visible, **30fps**; (c) `grain_invisible_until_right.sav` → grain **visible** (no more box over-occlusion); (d) cold-boot spawn → floor renders to the horizon (draw distance intact), objects depth-composited with Flik, HUD intact, Flik on floor (Y=−266, no fall — depth-sort is render-only); (e) `lag_walkingaround` rotation → **29–30fps** (per-tri bucket splice is O(1); no floor query). Straddling FLIK letters are now only partly covered where they dip below the floor, and objects behind walls are covered only where the wall overlaps them — real occlusion. **Tuning note:** if a future level sits at a very different depth, re-tune `DS_MUL` (bigger = geometry sorts farther back = less occlusion). Retired concepts kept only as history above.
>
> - **CALIBRATION FIX — "Flik cut by floor" + view-dependent occlusion oddity (2026-06-30, `occlusion_oddity.sav` reported; cold-boot verified).** The 4n renderer above shipped with `DS_MUL=978, DS_BASE=0` **tuned by eye**, which was wrong. Operator reported: (a) occlusion **changes as you walk up the ramp** (right from the platform, off from below), (b) **Flik sheared flat by the floor** again. Both = the same mis-calibration. **Measured the game's real OT** (broke at render entry `RENDER_C @0x801F0C00`; read live camera C@`0x1F800374`/R@`0x80090FB0` — screen projection reproduced the game within **1px**; screen-matched OT nodes to objects to read the game's own bucket): near-grain PVZ 15629→bkt 445, **Flik 28787→653**, F-letter 62660→852, telescope 106229→950. **Findings:** (1) the game's depth→bucket curve is **COMPRESSIVE / non-linear** (steep near, flat far) so a linear splice can't match every depth — that's the irreducible "oddity"; (2) `978/0` put our floor at Flik's depth in bucket **429** vs the game's Flik at **653** → floor **224 buckets too near** → drew over Flik (cut) + over-occluded. **Fix v1 (linear `DS_MUL=251/DS_BASE=546`) killed the cut-out but the oddity persisted** (operator saved `occlusion_oddity_v2_1/2`). **Fix v2 = a piecewise-linear LUT of the measured curve** (`ds_depth_bucket()` over 8 `(PVZ,bucket)` breakpoints): the two poses proved the game OT is a consistent `f(PVZ)`, so matching that curve makes occlusion **view-independent**. Cold-boot verified: game bucket 679 == LUT-pred 681 (diff 2) at PVZ 32343; our floor buckets span 335→721 (min ≪ 546 linear floor ⇒ LUT live); Flik full; no wedge. **Wedge gotcha:** `ds_depth_bucket` as a standalone fn landed at `0x801F0C00` (the loader's hard-jal render entry) → GPU DMA wedge; fixed with `always_inline` so `tier3_otrender_hook` stays first. `SENT@0x801E00DC` is unreliable (clobbered by the game OT). C: `mod/caves/tier3_otrender.c` (LUT + `ds_depth_bucket` + linear-override fallback), `mod/tier3_otrender_live.asm` (symbol jal). Full detail: Phase 4o.

> [!success]- ✅ Lag: when Flik is **rotating in place** the framerate drops **very low** (~14fps). Repro movie: `lag_walkin…
> **Symptom:** Lag: when Flik is **rotating in place** the framerate drops **very low** (~14fps). Repro movie: `lag_walkingaround.movie.json` (from-boot; ends with Flik rotating at spawn).
>
> - Goal to fix: keep the framerate up while rotating.
>
> - **FIXED 2026-06-30 (cold-boot DuckStation-verified):** this was a **regression from the object-occlusion fix above** (operator hint: "started when you fixed the previous bug"). The occlusion scanned all authored `type-0x3f` objects and ran the **`tier3_floor_y` floor query — an O(ntris)=O(180) triangle scan — for EVERY on-screen object EVERY frame**; at spawn many objects are on-screen, so the per-frame floor-query cost dropped the render from 30→14fps. **Decisively isolated:** un-hooking our render → 30fps (so it's our render); a full FARZ sweep with **fresh reloads** held **13fps at every FARZ** (15000…200000) → FARZ-/draw-distance-INDEPENDENT, the far ground is not the cost; **neutering `FLOOR_FN` (return NO_FLOOR) → 30fps** → the floor queries ARE the cost. (An earlier "FARZ→3393 = 29fps" reading was the **camera settling** out of the grazing angle after the movie stopped, not FARZ; and a `FAST_FLOOR` const-UV experiment only moved 14→15fps → it is NOT texture-cache thrash here, it's the CPU floor queries.) **Fix:** the buried status is **camera-independent + static**, so AMORTIZE it — floor-check **ONE object per frame** (round-robin `OCC_CURSOR`) and cache its buried bit in `OCC_MASK` (96 bits, `mod/caves/tier3_level.h`); each frame only **project the cached-buried objects** (cheap, no floor query). Cleared by the collision cave's spawn one-shot (`mod/caves/tier3_collision.c`). The cached buried test is now purely static (dropped the per-frame `Cy<fy` camera guard so it can't flicker across frames). **Verified:** cold-boot of the rebuilt `build/ABL_tier3_render.cue` via `lag_walkingaround.movie.json` → **30fps throughout the rotation** (was 14–15); occlusion still correct (the 4 buried FLIK letters keep `buried_bit=1`, resting grains stay visible). Net cost is now ~1 floor query/frame (same as the collision cave's own query). NOTE: the floor-occlusion's camera-mismatch limitation (a buried letter can still peek at some poses) is unchanged by this perf fix — see the occlusion entry's LIMITATIONS.

> [!success]- ✅ Sometimes the ground has triangular holes in it
> **Symptom:** Sometimes the ground has triangular holes in it. See "ground_incomplete.sav" and "ground_incomplete_2.sav". It seems to happen if I'm looking at it at an angle and happens close to the edge of the screen
>
> - Goal to fix: ground should be rendered fully properly no matter what angle.
>
> - **FIXED 2026-07-01 (cold-boot DuckStation-verified):** the holes were thin **triangular cracks** where our software clipper met a **screen boundary**, letting the blue sky show through the ground. **Root cause:** the fixed-point 2D screen-edge clip in `mod/caves/tier3_otrender.c` used `lerp10()` for the boundary-intersection X/Y, whose `((b-a)>>4)*frac>>6` **pre-shift throws away the low 4 bits of the *screen-space* delta**. Two adjacent tris share a 3D edge that crosses a screen edge and clip it in OPPOSITE winding order, so the asymmetric rounding lands the two triangles' boundary vertex on DIFFERENT pixels (measured on `ground_incomplete.sav`: the shared edge idx9↔idx14 crossing the bottom edge `y=239` clipped to **x=270** for one tri vs **x=271** for its neighbour — true value **274.8**, i.e. both wrong AND disagreeing) → a sliver that is zero-width at the shared far vertex and ~1px at the boundary = a **triangular** hole; worst at grazing angles (many floor tris overhang a screen edge → many boundary clips) and only near the screen edge (exactly the reported symptom). The `>>4` pre-shift exists only to keep the multiply inside int32 for the LARGE view-space near-plane clip; it is pure precision loss for the small screen-space deltas. **Fix:** `lerp10()` now uses the FULL-PRECISION `(b-a)*frac>>10` (same fraction, no lost bits) whenever `|b-a| <= ~1M` (always true for screen coords), keeping the coarse `>>4` path ONLY for very large view deltas (off-screen, sub-pixel irrelevant). Full precision is also **direction-symmetric** (`frac10` keeps `|num|<|den|` so `fracA+fracB==1024` exactly): the same edge clips to **x=274 in BOTH winding directions** → crack closes. **Verified:** (1) offline replica of the exact fixed-point clipper on both saves' live camera (broke at render entry `0x801F0C00`, read `R@0x80090FB0` + `C@0x1F800374`) + a coverage rasterizer correlated against the actual frame → visible sky-crack pixels went `6 → 0` (gi1); (2) **live A/B injection** of the recompiled render at `0x801F0C00` on `ground_incomplete.sav` + `ground_incomplete_2.sav` with a **matched-frame control** (same save, same 5-frame advance, no inject) — the control still shows the triangular slivers, the injected fix shows solid ground; (3) **cold-boot** of the rebuilt `build/ABL_tier3_render.cue` (`.bin` sha256 `8ab8b928…`, `TIER3_KEEP_BLOB=1`, operator's 180-tri level + native objects preserved) via `flik_to_level01_stall.mv.movie.json` → spawn + roam to grazing angles render solid ground with no triangular holes, Flik on floor (`Y=−266`, grounded `0x0101`), `SENT` incrementing, collision intact. **RESIDUAL (honest, far smaller):** a faint sub-pixel seam can remain on the very bottom row (near-plane clip / mesh T-junctions between grid rows) and the PS1 GPU's own fill-rule can drop the odd 1px along a shared edge — neither is the reported "triangular hole near the screen edge"; the fully seam-free path is the deferred GTE render (same deferral as the occlusion/affine-warp work). RE/fix: `mod/caves/tier3_otrender.c` `lerp10()`.

