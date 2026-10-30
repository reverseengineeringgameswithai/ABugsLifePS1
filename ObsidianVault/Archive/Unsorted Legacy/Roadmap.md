---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Roadmap.md
aliases:
  - "Roadmap"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Roadmap.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Roadmap
type: plan
updated: 2026-06-25
last_audited: 2026-06-21
next_review: 2026-07-04
tags: [plan, roadmap, dashboard, control-document]
---

# 🗺️ Project Roadmap — A Bug's Life (PS1, SCUS-94288) RE

> The top-level **control document** for the project: status, prioritized milestones, a traceable backlog, evidence standards, taxonomies, a risk register, and a concrete near-term plan. It sits above the existing self-audit layer ([[Blockers]] · [[Risk Matrix]] · [[Assumptions Register]] · [[Remediation Plan]] · [[Open Questions]]) and the detailed **[[Gap Audit]]** (GAP-0001…GAP-0043). Every milestone item traces to ≥1 gap.
>
> **Why this file, here:** the vault had **no project-level roadmap** — only the editor-scoped [[ABL 3D Level Editor Roadmap]] (now folded under M6). Placed at the vault root beside [[Home]]/[[README]]/[[Tools Catalog]] (the other root-level control notes). Nothing was archived because nothing was replaced (GAP-0041).
>
> **Last audited:** 2026-06-21 · **Next review:** 2026-07-04

---

> [!success] Milestone 0 — COMPLETE except GAP-0001 (then operator-gated; **GAP-0001 since Resolved on host 2026-06-21**) · 2026-06-20 · committed `0d6b0af`
> Hygiene & reproducibility executed end-to-end — full record in **[[Milestone 0 Completion]]**. [[DuckStation Fork Reproducibility]] now ties the local fork, 114 committed RPC calls, 27 dirty-only calls, build setup, API-note map, and binary/spec hashes to HEAD `296955321`. **GAP-0001 was then open** (34 modified + 16 untracked, no preserving remote); it is now **✅ Resolved on host (2026-06-21)** — the fork is preserved as a verified recoverable bundle/patchset + tag, an independent clone rebuilt `duckstation-qt`, and the spawn-floor headline replays from that clean-built binary; only an off-host copy remains. M3 is complete for the modding-grade baseline without depending on live-fork reproducibility.

> [!success] M0–M8 — COMPLETE / baselined · 2026-06-21 · HEAD `d2fe61b`
> The full **M0–M8 roadmap frame is complete and the clean tracked base is self-consistent** (M8 closeout `d2fe61b`). **M8 closure does not close the project** — the next workstream is the **Post-M8 — next roadmap frame** at the end of §3 (an evidence-ranked, gap-tied backlog). The former top risk **[[Gap Audit|GAP-0001]] is now ✅ Resolved on host (2026-06-21)** — the private DuckStation fork is preserved as a verified recoverable bundle/patchset + tag, a clean clone rebuilt `duckstation-qt`, and a headline replays from it; the lone residual is an operator off-host copy. Open work remains on reproducibility hardening (GAP-0002 findings/fixtures ✅ Resolved on host 2026-06-21 — two-layer findings guard + hash-pinned fixtures; GAP-0001 off-host copy = residual), generality (GAP-0039), format/editor depth (GAP-0023), behavior/subsystems (GAP-0034 + audio/FMV/menu/save), and optional decompilation (GAP-0021).

> [!todo] M9 — TIER 3: Custom Level Engine (NEW major initiative · operator end-goal · 2026-06-25 · Phase 1 ✅ PASSED 2026-06-24)
> End-goal: **SM64-romhack / Fast64-style entirely-new levels** (new spawn, new platforming, new look) authored in **Blender**. Native geometry/collision *write* formats are years-deep (chunk-35 walls blocked; collision = per-sector-flat + ~6 swept planes, NOT a triangle mesh), so the route is to **BYPASS** them: **ABL = HOST SHELL** (keeps boot, Flik controller/gravity/jump/input/animation, camera, HUD, audio, objects); a **custom injected subsystem OWNS** the visual level mesh, triangle floor/wall collision, floor-height-under-Flik, wall-blocking, and gap detection. Both injection primitives already proven here (GPU primitive injection + live code hooks). **Distinct from the sector-based [[Blender-first ABL level editor]] (Tier 1/2 — edits the *existing* level); Tier 3 *replaces* the level subsystem.** Plan/phases: [[Tier 3 - Custom Level Engine]]. Spike-first: **Phase 1 collision spike ✅ PASSED (2026-06-24)** — injected a MIPS collision cave (hardcoded 2 platforms + a gap) hooking the integrator's final Flik-Y writer (`0x80036d54`→`jal 0x800810c0`); live, Flik walked the raised + lowered platforms (Y held at our heights) and fell in the gap, all from native input/gravity — **the controller accepts a custom world via the hook (kill-criterion cleared).** Sources `mod/tier3_collision_spike.asm` + `src_mod/tier3_collision_spike.c`. **Phase 1.x 1a/1b/1c ✅ DONE (2026-06-24):** spike rects → a real DATA-DRIVEN TRIANGLE-MESH collision engine in **C** (`mod/caves/tier3_collision.c`, compiled by `mips64-linux-gnu-gcc` via `mod/build.py` — caves can be C, not hand-MIPS), baked into a cold-**booting** disc (`build/ABL_tier3_collision.cue`): flat floors exact, ramps interpolate a walkable slope, gaps fall — verified live AND on the booted disc; OG RE `src_re/movement_integrator_8003633c.c`. **1d walls ✅ DONE (2026-06-25):** AABB keep-out boxes — the cave clamps the crossed axis (prev-XZ persisted in the zero-run) so Flik stops at the wall and slides along it (live-proven; `wall_resolve` in `mod/caves/tier3_collision.c`). **1e death-plane+respawn ✅ DONE (2026-06-25):** spawn+death-plane are mesh data; the cave warps Flik to the custom spawn when his floor Y passes the plane (proven by walking off an edge → fell → respawned). **KEYSTONE finding:** the `0x80036d54` hook is the *grounded* floor-writer; airborne frames can bypass it (Flik can drift off a flat platform) — floor math is correct, the gap is *authority*. **1f authoritative floor ✅ DONE (architecture) 2026-06-25 + coupling finding:** the integrator `FUNC_8003633C` is GENERIC (3 callers), so re-hooked at the PLAYER's per-frame post-physics point (`0x800495d0`, after the integrator returns) → cave is authoritative, Flik-only, every frame; **CLAMP model** (floor is a minimum, not a snap — ABL HAS a jump on X, and X-in-air = butt-slam; verified the clamp preserves the jump: X raises Flik 6336u and lands on our floor). Fixed the drift on platform A while driving + idle authority everywhere. **Residual finding:** the clamp floats on descending ramps/lower platforms because native gravity targets the *native* floor, not our mesh ⇒ **Phase 3c (native-level suppression) is a PREREQUISITE — with no native floor, gravity falls Flik to OUR floor and the clamp catches him, so jump AND tracking both work** — so 3c moves up. **Phase 2a GPU triangle draw ✅ DONE (2026-06-25):** custom flat-shaded triangles (GP0 `0x20`) render into the ABL gameplay frame via the reused `abl_starry`/`abl_night_hook` GPU-DMA injection — proving the render pillar. Gotcha: the displayed VRAM buffer alternates (read `gpu.getStatus`→`crtc.vram_source_rect`); the frozen one-shot is deterministic (frame `build/spike2a_frozen.png`). **Phase 2b (camera projection) ✅ DONE (2026-06-25) — the collision mesh renders IN-WORLD.** Found ABL's camera in RAM (reused the prior camera RE): rotation `R` = the GTE `control.rotation_matrix` captured at the world-space draw `0x80010718` (pure world→view there); camera world position = the 3×s32 at scratchpad `0x1F800374`. `view = R·(V−C)/4096; sx=H·vx/vz+256; sy=H·vy/vz+120` reproduces the GTE's own `screen_xy_fifo`. Projected the collision mesh and drew it via the 2a path → renders perspective-correct in-world (green platform A / yellow ramp / cyan B on the ground around Flik, `build/spike2b_mesh.png`). **Per-frame tracking confirmed** — drove Flik forward through 3 poses, the mesh stayed world-locked (platforms approach + pass, clip behind camera; `build/spike2b_track_0/1/2.png`). Remaining (not blocked): autonomous in-cave re-projection + 2c textures / 2d depth. **Phase 3c native suppression PARTIAL (2026-06-25):** deepening the runtime sector floor (`0x800a7e48`) + zeroing the plane count (`[gp+0x57c]`) makes flat platforms (A, B) track exactly — but the ramp floats. **Root-caused (2026-06-25): NOT a floor-query bug** (the query is correct — idle tracks every surface, the cave's hit-triangle matches the Python replica) **and not native coupling** — it's the 1f clamp snapping only when Flik is *strictly below* the floor, so the walking-bob (Flik a few hundred units above the floor while driving) drifts. A ground-margin snap fixes walking but kills the jump (bob vs jump-takeoff are indistinguishable by height). **ROOT-CAUSED + FIXED (2026-06-25):** turned out to be TWO bugs — (1) a real **int32 overflow** in the point-in-triangle `edge_xz` (the compiler truncated the `(long long)` widen of the ~3e9 cross-products, flipping a sign on ramp triangle 3 → false NO_FLOOR; platform A's bigger products wrapped to the right sign by luck, masking it) — fixed by scaling deltas `>>4`; (2) the clamp model → **velocity-gated snap** using **Flik's vertical velocity at `0x800A6530`** (snap when grounded/falling, leave when rising). Verified: A tracks, ramp `−92252→−86173` graduated, jump rises the full 15744. Still needs the native floor pushed below the mesh (3c; sign gotcha: −Y is up so "below" = more positive). Jump landing resolved (descends ~30 frames then settles exactly on the floor). **3c collision suppression is now SELF-CONTAINED in the cave** (zeros the plane count + deepens all sector floors below the mesh/death-plane each frame) — verified with NO external pokes (A/ramp/gap-death/jump all work), so the collision engine is disc-ready. **3c render-suppression attempted but blocked** — the vault's terrain-draw notes are wrong (`0x80010000`/`0x800172dc` don't blank it); needs a `gp0Trace`-based identification of the terrain primitives. Remaining residual: the ramp→B1 seam (unpinned compiled edge case in one quad). Next = render-blank via gp0Trace, disc-build at the real spawn, per-frame render tracking, 2c/2d. Then → format/loader → Blender exporter → integration hardening. Honest risk: integration long tail + R3000 perf + 2 MB RAM. Traces to GAP-0023 (editor/format depth).

## 1. Project status summary

**What this is.** A reverse-engineering + modding project for *Disney·Pixar A Bug's Life* (PS1, **SCUS-94288**, hash-verified **USA V1.0**), driven through a **custom DuckStation external-debugger JSON-RPC API**. Findings live in this Obsidian vault + a machine-readable findings store.

**Maturity — measured against two yardsticks (this is the crux, GAP-0043):**

| Yardstick | Maturity | One-line |
|---|---|---|
| **Modding-grade behavioral RE** (the project's *declared* goal) | **Strong / largely succeeding** | LEVEL01 pickup/DAT modding **shipped in-game**; geometry render-vs-collision **answered**; codec **decoded**; sky/night/GPU-injection done; an end-to-end edit→rebuild→boot demo is proven. |
| **Preservation / matching decompilation / full asset pipeline** (the harder yardstick the user's audit + the project's own [[Blockers]] scorecard use) | **Early-stage / not third-party-reproducible** | ~3–5% decompiled into C; **no build/diff substrate**; whole engine subsystems unmapped; verification rides one private emulator fork. |

> [!success] Charter — DECIDED 2026-06-20: modding-grade goal, **decomp-forward** method
> The **goal is modding-grade** behavioral RE + LEVEL01+ modding. The owner invests in **targeted decompilation infrastructure when it improves modding reliability, editor accuracy, rebuild safety, or behavior verification** — not as preservation for its own sake. This supersedes [[Remediation Plan]] §4a's blanket "B1 won't-do": the symbol map and overlay baseline are active enabling work, while compile/diff work remains evidence- and payoff-gated. The full-RE scorecard is kept only as a harder-yardstick progress gauge. Byte-identical matching is optional and is never required without a direct modding benefit.

**What is known (high-confidence, multi-evidence — see [[Confirmed Knowledge]]):**
- **Visual terrain ≠ collision** — different files/RAM/code (the headline; but see *blocked*).
- Collision floor = LEVEL.RAW **chunk 32** sector-table planes; player-Y writer [[FUNC_8003633C]]; RAM edits move footing ~1:1.
- **LEVEL.RAW codec = RNC PROPACK 2.29**; decoder **byte-exact** (validated all 69 chunks).
- Type-0x3f pickups coordinate-moddable + new entries injectable (relocation-aware).
- Disc rebuild (unpatched) is **byte-exact** (0/313,897 sectors).
- Toolchain/provenance: Traveller's Tales · PsyQ + PsyMake 1.11 · PROPACK 2.29 · USA V1.0.
- Asset **formats** decoded/extracted: LEVEL.DAT (all 11 records), `.ALL`/`.ANM` models+anim, VAB, XA, STR/MDEC, GFX/BGR; text is image-baked (no font store).

**What is unknown (see [[Open Questions]] + [[Gap Audit]]):** per-object mesh-consumer trace (GAP-0022 — all 69 chunk *roles* now classified) + chunk-34 master mesh + model→world transform (GAP-0023); camera follow-law (GAP-0028); the scripting/event-trigger system (GAP-0033); enemy AI behavior + PATH nav-graph (GAP-0034); ~~runtime audio/FMV/menu/save paths (GAP-0031/0032/0036)~~ **decoded 2026-06-22** (SFX/libspu/XA, FMV.BIN manifest sequence, menu-nav + save in the MEMORY.BIN overlay — closed-with-residual); deep overlay internals (GAP-0020); and, for the optional preservation yardstick, most matching decompilation (GAP-0021).

**What appears blocked:**
- **Verification reproducibility** — bus-factor-1 on a private DuckStation fork with host-local saves (GAP-0001/0002, B2). *Everything dynamic depends on this.* **GAP-0001 resolved on host 2026-06-21** (fork preserved + clean-clone replay); B2 fully retires once the preservation set is copied off-host.
- **The central headline** — visual≠collision now meets its bar: **two independent confirmations** (spawn-area source separation [[Experiment - Spawn-floor render source]] + the **G29 Pass-3 pristine-vs-patched counterfactual, both arms run 2026-06-21**). A phase-matched pristine-vs-G28 differential differs in **only the visual-edit halfword**; the collision sector-table hash, resolver path, player-Y writer, and Flik's footing are byte-identical (GAP-0038 → Verified; [[Experiment - G29 Pass-3 differential]]). The findings store is now **reconciled** — f13 is the **sole CONFIRMED** visible-floor answer with M7 evidence refs (GAP-0008 → Resolved 2026-06-21). The chunk-34 "spawn ≠ DAT" contradiction is **RESOLVED 2026-06-21 (M7)**: the visible spawn floor **is** DAT (`fcn.80010000`, sources file `0x15dec..0x2f59c`); chunk-34/35 is the occluded/collision-adjacent layer (GAP-0011 → Verified). The headline now also holds **per-pixel on LEVEL02** (scene 3): the floor under Flik is DAT via `fcn.80010000` (shared leaf `0x80019xxx`, caller `ra` inside `fcn.80010000`), collision separate (GAP-0039; [[Experiment - LEVEL02 floor source]]).
- **Byte-exact compressed-asset rebuild** — only a *literal* recompressor exists (GAP-0024, B14).
- **Decompilation** — no compile/diff substrate yet (GAP-0021, B1); M3 finalized a behavioral scaffold and evidence-backed deferral. Resume only for a concrete modding payoff.

**Highest risk:** (1) loss of the single host → verification collapse (B2); (2) the navigation layer ([[Risk Matrix]], findings store) **was stale/self-contradictory** — now **reconciled** (M7/M8: GAP-0007/0008 Resolved, store → f13 sole CONFIRMED); B11 stays a standing *re-accrual* risk (🟢 Low) absent the [[CONTRIBUTING]] per-status discipline; (3) headline fragility (GAP-0038, B3).

---

## 2. Gap audit summary

Condensed view of **[[Gap Audit]]** (full per-gap detail there). Owner/status use the §7 taxonomy.

| Gap      | Area            | Description                                                             | Evidence (vault)                              |  Impact  | Pri | Owner / Status                         | Next action                                    |
| -------- | --------------- | ----------------------------------------------------------------------- | --------------------------------------------- | :------: | :-: | -------------------------------------- | ---------------------------------------------- |
| GAP-0001 | Reproducibility | Fork preserved (bundle+patch+tag, byte-exact), clean-clone rebuilt, headline replayed | [[DuckStation Fork Reproducibility]]          | Critical | P0  | ✅ Resolved on host 2026-06-21 (off-host copy = residual) | Copy preservation set off-host (operator)      |
| GAP-0002 | Reproducibility | Untracked inputs; findings-store overwrite hazard                       | [[Reproducibility Checklist]] · [[Fixtures Index]] | Critical | P0  | ✅ Resolved on host 2026-06-21          | Reconcile LEVEL02 fixture name (→ GAP-0040)     |
| GAP-0003 | Reproducibility | Host paths removed from tracked tools; pinned deps manifest             | `tools/_env.py` · `tools/requirements.txt`    |   High   | P1  | _ / ✅ Resolved (2026-06-21)            | Promote WIP tools to `_env.py` when tracked    |
| GAP-0004 | Legal hygiene   | Preservation/sharing policy consolidated + linked                       | [[Preservation Policy]]                       |   Med    | P2  | _ / ✅ Resolved (2026-06-22)            | — (note exists, linked, `.gitignore` refs it) |
| GAP-0005 | Asset pipeline  | VAB+GFX extractors committed + `SHA256SUMS` (1879, verified)            | [[Asset Extraction Pipeline]]                 |   Med    | P2  | _ / ✅ Resolved (2026-06-22)            | — (XA/FMV via pinned jpsxdec, by design)       |
| GAP-0006 | Hygiene         | Build artifacts/scratch in `tools/`                                     | `tools/*.png/*.RAW`                           |   Low    | P3  | _ / ✅ Resolved 06-22 (stale; oracles only, artifacts gitignored) | Move to ignored `out/`                         |
| GAP-0007 | Doc integrity   | Risk Matrix current-tier column exists (M0); M7-refreshed + statuses reconciled (M8) | [[Risk Matrix]]                  |   High   | P1  | _ / ✅ Resolved (M8 2026-06-21)        | Sustain via [[CONTRIBUTING]] update rule       |
| GAP-0008 | Doc integrity   | Findings store: f13 now SOLE CONFIRMED floor answer (RESOLVED M7)        | `re_findings_backup.yaml`                     |   High   | P1  | _ / ✅ Resolved (M7 2026-06-21)        | — (f13 sole CONFIRMED + evidence refs)         |
| GAP-0009 | Doc integrity   | Occlusion caveat now across all clean notes (Home/findings/G30/exp)      | [[Home]]                                      |   Med    | P2  | _ / ✅ Resolved (M8 2026-06-21)        | chunk-34 reconciled; editor-note = operator residual     |
| GAP-0010 | Doc integrity   | `fcn.800172dc`/`0x8012c1d0` reframed shared mesh renderer (titles+indexes) | [[FUNC_800172DC]]                           |   Med    | P2  | _ / ✅ Resolved (M8 2026-06-21)        | filenames kept for wikilink stability          |
| GAP-0011 | Geometry        | RESOLVED: spawn floor = DAT (`fcn.80010000`); chunk-34/35 = occluded   | [[Experiment - Spawn-floor render source]]    |   High   | P1  | _ / **Verified** (M7 2026-06-21)       | — (f13 made sole-CONFIRMED; GAP-0008 done)      |
| GAP-0012 | Doc integrity   | Tools Catalog re-counted 85 on disk (61T+24U); CI-safe/host-path tagged | [[Tools Catalog]]                             |   Med    | P2  | _ / ✅ Resolved (M8 2026-06-21)        | Sustain on tool add/remove                     |
| GAP-0013 | Doc integrity   | Editor README "mutation not wired" stale                                | `level_editor/README.md`                      |   Low    | P3  | _ / ✅ Resolved 06-22 (README already distinguishes the two tabs) | Update README                                  |
| GAP-0014 | Provenance      | Checksum manifest + release id — DONE (M1)                              | [[Checksum Manifest]]                         |   Med    | P2  | _ / ✅ Done (M1)                       | Formal redump.org datfile match (residual)     |
| GAP-0015 | Disc layout     | Narrative disc/file map — DONE (M1)                                     | [[Asset - Disc file map]]                     |   Low    | P3  | _ / ✅ Done (M1)                       | —                                              |
| GAP-0016 | Toolchain       | Census + tool pins; PsyQ libs dated ≥1997-03-28 (EXE RCS `$Id$`)        | [[Toolchain Census]]                          |   Med    | P2  | _ / ✅ Resolved (2026-06-22)            | Exact `ccpsx` compiler = GAP-0021 (deferred)   |
| GAP-0017 | Testing         | Safe CI committed (`safe-tests.yml`) + 40 passed; GPU/live isolated     | `.github/workflows/safe-tests.yml`            |   Med    | P2  | _ / ✅ Resolved (2026-06-22)            | Operator push to observe GitHub-green; opt-in GL/live |
| GAP-0018 | Symbols         | 85-label baseline validates and round-trips into fork CSV/r2            | [[Symbol Import Round Trip]]                  |   Med    | P2  | _ / Verified                           | Optional live fork corroboration               |
| GAP-0019 | Memory map      | Consolidated address axis                                               | [[MEM - Global memory map]]                   |   Low    | P3  | _ / Verified                           | Capture remaining heap/SP unknowns             |
| GAP-0020 | Binary          | Region A/B baseline meets acceptance (multiple overlays behavior-mapped) | [[Executable and Overlays]]                   |   Med    | P2  | _ / ✅ Resolved (2026-06-22)            | Per-module enumeration on subsystem demand; residency = live |
| GAP-0021 | Decompilation   | Behavioral pilot finalized; compile/diff substrate deferred (payoff-gated) | [[Decompilation Pilot]]                       |   High   | P1  | _ / Deferred — payoff-gated (2026-06-21) | Return only with pinned tools + named modding payoff |
| GAP-0022 | Level format    | 69/69 chunk roles classified (M4)                                       | [[Asset - LEVEL.RAW Chunk Role Table]]        |   High   | P1  | _ / ✅ Verified (M4)                   | Per-object mesh consumer trace (residual)      |
| GAP-0023 | Level format    | Floor model→world RESOLVED: offline `world=T_obj+v_local` from LEVEL.DAT node array | [[Asset - Chunk 34 Master Mesh]] · `analyze_g27_floor_candidates.py` |   High   | P1  | _ / ✅ Resolved for floor (2026-06-22)  | Apply editor fix; rotated-mesh M_obj for general meshes |
| GAP-0024 | Compression     | Size-budget rebuild strategy decided (M4)                              | [[Asset - PROPACK Rebuild Strategy]]          |   Med    | P2  | _ / ✅ Verified (M4)                   | Byte-exact PROPACK encoder (optional)          |
| GAP-0025 | Build-repro     | Oversize LBA-shift reflow booted + loaded LEVEL01 (by-name tolerant)    | [[Asset - LBA Shift Rebuild Proof]]           |   Med    | P2  | _ / ✅ Resolved (2026-06-22)            | Optional: commit a reflow builder tool         |
| GAP-0026 | Asset           | `.ALL`/`.ANM` fine grammar                                              | [[Asset - ALL ANM Format Grammar]]            |   Low    | P3  | _ / ✅ Resolved 06-22 (round-trip exporter `tools/parse_all_anm.py` — .ALL 78/78 + .ANM 58/58 byte-exact) | residual: field-type the .ALL non-primitive spans |
| GAP-0027 | Textures        | GFX CLUT bounded (M4); embedded subset exact                           | [[Asset - GFX CLUT Exactness]]                |   Low    | P3  | _ / ✅ Resolved 06-22 (CLUT in LEVEL01/LEVEL.RAW; 14/16 exact) | Trace CLUT upload source                       |
| GAP-0028 | Camera          | Follow-law DECODED + validated (`fcn.8004df18`; boom + smoothing k=1/8) | [[Core - Camera and Projection]]              |   Med    | P2  | _ / ✅ Resolved follow-law (2026-06-22) | Closed-form heading/pitch + RT→GTE for byte-exact pixels |
| GAP-0029 | CD streaming    | Loader chain + by-name + all-at-load geometry confirmed (model documented) | [[Core - CD Streaming and Caching]]           |   Med    | P2  | _ / ✅ Resolved (2026-06-22)            | Mid-level-streaming existence = event-gated (GAP-0033) |
| GAP-0030 | Rendering       | OT/packet/flip consolidated (M5, static)                               | [[Core - Rendering OT and GPU Packets]]       |   Low    | P3  | _ / ✅ Resolved 06-22 static+live (OT=DMA list; flip 0x80062cfc→0x800646b8) | Document DMA-submit/flip site                  |
| GAP-0031 | Audio           | Runtime SPU anchors documented (M5, static)                           | [[Core - Runtime Audio Path]]                 |   Low    | P3  | _ / ✅ Resolved 06-22 static (SFX 0x80050994 + libspu SsVab* + XA music) | `execTrace` libspu voices                      |
| GAP-0032 | Video           | FMV/MDEC trigger baseline (M5, static)                                 | [[Core - FMV and MDEC Playback]]              |   Low    | P3  | _ / ✅ Resolved 06-22 static (FMV.BIN 25-entry manifest seq + loader 0x8003e7c0) | Trace MDEC call site                           |
| GAP-0033 | Scripting       | **VM fully modeled** (M6): object-actor bytecode VM [[FUNC_8004C13C]]; 26 opcodes + cold-boot stream 2026-06-21 | [[Event and scripting system]]      |   Med    | P2  | _ / **Verified** (narrow residuals)    | Confirm 5 LIKELY ops + program-seed + overlay-CALL bodies |
| GAP-0034 | AI              | **Behavior DECODED, cross-level** (2026-06-22): regular enemies scenes 1/3/4/5/6/10 = chaser `FUNC_8004DF18` or mover-VM `FUNC_8004C13C` (no new AI fns); BIRD boss bespoke (`FUNC_8004DD98`); HOPPER+THUMPER = chaser-AI fights; **Thumper PARTIAL** (actor+Y-law+defeat-chain decoded; HP/throw/berry in boss overlay=open); `FUNC_8004DD98`=scripted finale; THUD untested | [[Enemy AI state machine]] |   Med    | P2  | _ / **✅ Behavior decoded** (cross-level; Hopper/Thumper bosses PARTIAL — combat in overlay) | map Thumper boss overlay (`transferLog.resolve 0x800b4138`); Hopper defeat-save; Thud re-test; PATH decider |
| GAP-0035 | Gameplay        | **SPLIT**: 0035A arch Verified; 0035B clean in-game handoff Blocked (shell fixture) | [[Experiment - In-game warp trigger]]  |   Low    | P3  | _ / 0035A Verified / 0035B terminal-by-design (reframe ADOPTED 06-22) | 0035B needs an authored shell-phase event-state fixture |
| GAP-0036 | UI/save         | Menu/save state machine undecoded                                       | [[Menu and HUD structure]]                    |   Low    | P3  | _ / ✅ Resolved 06-22 static (menu-nav 0x800B687C + save in MEMORY.BIN overlay) | Trace menu substate                            |
| GAP-0037 | Player          | Player block + integrator mapped (M6); libpad provisional              | [[Gameplay - Input and Movement]]             |   Low    | P3  | _ / In Progress (M6)                   | Locate libpad; map input→velocity              |
| GAP-0038 | Epistemic       | Central headline: 2nd angle + G29 Pass-3 counterfactual (both arms) done                              | [[Experiment - G29 Pass-3 differential]]      |   High   | P1  | _ / Verified (M7 2026-06-21)            | Optional: 2nd edit/scene to harden generality  |
| GAP-0039 | Generality      | Deep chunk+collision map on a non-LEVEL01 level (LEVEL02=L03, motion-validated) + floor 11/11 | [[Experiment - LEVEL02 floor source]]         |   Med    | P2  | _ / ✅ Resolved (2026-06-22)            | Optional: collision beyond LEVEL02; live counterfactual |
| GAP-0040 | Testing         | Codec covered; 4 headline replays landed (spawn-floor + G29 A/B + LEVEL02) | `tools/trace_spawn_floor.py`; `tools/trace_g29_pass3_arm_a.py`; `tools/trace_g29_pass3_arm_b.py`; `tools/trace_level02_floor.py` |   Med | P2 | _ / ✅ Resolved (2026-06-22) — opt-in `live` replay test added | Re-run the other 3 from preserved state; copy off-host (operator) |
| GAP-0041 | Governance      | Roadmap = top-level control doc; linked from Home/Index (acceptance met) | (this file)                                  |   High   | P1  | _ / ✅ Resolved (maintained)           | Refresh Last-audited/Next-review each cycle    |
| GAP-0042 | Governance      | CONTRIBUTING exists (M0) + M8-hardened: skill guide, update rule, preservation | [[CONTRIBUTING]]                       |   Med    | P2  | _ / ✅ Resolved (M8 2026-06-21)        | Adopt status taxonomy in task lines            |
| GAP-0043 | Governance      | Charter recorded + legacy scorecard reconciled (labeled optional gauge) | [[Blockers]] charter banner · [[Risk Matrix]] |   High   | P1  | _ / ✅ Resolved (2026-06-21)            | Cosmetic: charter-link the remaining B-notes    |

`*` / `⚖️` = scope-gated on GAP-0043.

---

## 3. Prioritized milestones

> Milestone groups M0–M8 per the audit's standard frame. Each maps existing project work + new gaps. `⚖️` marks scope-gated (preservation-only) deliverables.

### Milestone 0 — Project Hygiene & Reproducibility  ⏳ *immediate*
- **Goal:** Make every existing result reproducible by a second machine/person, and make the navigation layer tell the truth.
- **Why it matters:** B2 + B11 are the cross-cutting roots under *everything*; they are also the cheapest high-value work (mostly ops + doc reconciliation, no new RE).
- **Deliverables:** vendored/pinned fork + off-machine remote; portable tool paths + `requirements.txt`; reconciled [[Risk Matrix]]; corrected findings store; `Preservation Policy.md`; reproducible asset-extraction manifest.
- **Dependencies:** none (this unblocks the rest).
- **Tasks:** GAP-0001, GAP-0002, GAP-0003, GAP-0004, GAP-0005, GAP-0006, GAP-0007, GAP-0008, GAP-0009, GAP-0010, GAP-0012, GAP-0013, GAP-0041, GAP-0042, GAP-0043.
- **Acceptance:** a clean clone on a 2nd machine reproduces ≥1 headline experiment end-to-end; [[Risk Matrix]] tier == each note's current tier; findings store has exactly one CONFIRMED visible-floor answer; charter (GAP-0043) recorded.
- **Risks:** doc-reconciliation edits touch RE artifacts (findings YAML) — schedule as a deliberate operator pass, not ad-hoc.
- **Related:** [[Reproducibility Checklist]] · [[Remediation Plan]] Phase 2.
- **Open questions:** none blocking — this is execution.

### Milestone 1 — Source Media Identification & Disc/File Map  ✅ *(deliverables done 2026-06-20)*
> [!success] Done: [[Checksum Manifest]] (disc CRC32 `607704bb` / MD5 `2c3861a3…` / SHA-1 `0bc1a297…` + release metadata: V1.0 NTSC-U, Traveller's Tales, 1998-11-01) and [[Asset - Disc file map]] (26 dirs / 321 files, full LBA geography). Residual (non-blocking): a formal redump.org datfile cross-check.
- **Goal:** Pin provenance to the preservation standard and publish a navigable disc map.
- **Why it matters:** Provenance (A1) underwrites every static offset + the byte-exact rebuild; onboarding needs a readable file map.
- **Deliverables:** `Checksum Manifest.md` (Redump id + hashes); `Asset - Disc file map.md` (from `abl.xml`); explicit PAL/proto scope statement.
- **Dependencies:** none.
- **Tasks:** GAP-0014 ✅, GAP-0015 ✅.
- **Acceptance:** ✅ manifest records disc/EXE CRC32+MD5+SHA-1 + release identity ([[Checksum Manifest]]); ✅ disc-map covers all 26 directories with roles ([[Asset - Disc file map]]). *(Open: formal Redump datfile match.)*
- **Risks:** master `.bin` may not match a Redump entry exactly → escalates B12.
- **Related:** [[Checksum Manifest]] · [[Asset - Disc file map]] · [[Finding - Disc rebuild is byte-exact]] · [[Asset - Disc image and rebuild]] · `REBUILD/abl.xml`.
- **Open questions:** OQ disc/filesystem group. *(M1 deliverables complete 2026-06-20; see the callout above.)*

### Milestone 2 — Toolchain & Analysis Environment ✅ *(deliverables committed `779849e`)*
> [!success] Complete baseline (2026-06-20): [[Toolchain Census]], exact Python pins, safe pytest runner/tests, and CI workflow. Residual exact-PsyQ/GPU/live items remain tracked evidence gaps rather than blockers to M3.
- **Goal:** Pin and document the analysis + build environment so outputs are deterministic.
- **Why it matters:** Determinism (A2) + cheap symbol seeding (library identification) + protecting the trusted DAT/codec tools.
- **Deliverables:** PsyQ/library census; pinned `mkpsxiso`/`jpsxdec`; `pytest` + CI-safe tests including codec/symbol round-trips; headless GL remains optional for GPU tests.
- **Dependencies:** M0 (path portability).
- **Tasks:** GAP-0016, GAP-0017, GAP-0040.
- **Acceptance:** ✅ safe pytest suite green locally and CI workflow defined; ✅ external tools/version evidence + known library families recorded; 🟡 first hosted CI run, exact PsyQ/library object revisions, GPU path, and live replay remain.
- **Risks:** GL-in-CI fiddly → keep GPU tests opt-in.
- **Related:** [[Toolchain Census]] · [[Tools Catalog]] · [[Finding - Build toolchain and PROPACK provenance]] · `docs/TOOLING.md`.
- **Open questions:** OQ tooling group.

### Milestone 3 — Executable Load Map & Symbol Baseline ✅ *(complete for modding-grade baseline)*
> [!success] Complete for modding-grade baseline (2026-06-20): [[MEM - Global memory map]] is complete; [[Symbol Map Baseline]] + `symbols/re_symbols.sym` persist 85 reviewed labels and [[Symbol Import Round Trip]] proves fork-compatible CSV plus actual r2 consumption; [[Executable and Overlays]] records the complete known file/region inventory and three LEVEL01 functions; [[Decompilation Pilot]] finalizes the evidence-backed `0x8001CDC0` scaffold/deferral.
- **Goal:** A consolidated memory/symbol/overlay baseline plus an explicit targeted-decomp decision that reduces downstream modding risk without forcing matching decompilation.
- **Why it matters:** Most *unfound* logic (camera, events, AI, menu) is overlay-resident; a symbol map is the substrate for any matching.
- **Deliverables:** `MEM - Global memory map.md`; validated/consumed `re_symbols.sym`; complete known overlay metadata + ≥1 behavior-enumerated overlay; a targeted decomp scaffold or concrete evidence-backed deferral.
- **Dependencies:** M0, M2; **GAP-0043 decision**.
- **Tasks:** GAP-0019, GAP-0018, GAP-0020, GAP-0021.
- **Acceptance:** ✅ global memory map; ✅ 85-label symbol map round-trips through DuckStation-compatible CSV and loads into r2; ✅ complete known overlay inventory + one behavior-mapped overlay; ✅ targeted decomp candidate, boundary/ABI/oracle/build plan, and explicit compile/objdiff deferral. Deep overlay RE, live fork corroboration, and matching compilation are later opt-in work.
- **Risks:** r2 boundary errors (A3) propagate naming; matching is open-ended effort.
- **Related:** [[Symbols Index]] · `docs/EXECUTABLE_AND_OVERLAYS.md` · `docs/DECOMPILATION_PLAN.md`.
- **Open questions:** OQ executable/binary group.

### Milestone 4 — File Format & Asset Pipeline  🟢 *(Baseline complete / sufficient for M5; carry-forward items remain — 2026-06-20)*
> [!success] M4 done: [[Asset - LEVEL.RAW Chunk Role Table]] (**69/69** classified, reproducible) · [[Asset - Chunk 34 Master Mesh]] (def+payload baseline, world-origin = the one missing transform var) · [[Asset - PROPACK Rebuild Strategy]] (size-budget rule) · [[Asset - LBA Shift Rebuild Proof]] (in-slack proven + per-file budget) · [[Asset - ALL ANM Format Grammar]] · [[Asset - GFX CLUT Exactness]] (bounded) · [[Asset Extraction Pipeline]]. Residuals: per-object mesh consumer trace, chunk-34 world-origin + sub-mesh schema, oversize-edit boot (local-only), `extract_vab.py`.
- **Goal:** Move LEVEL.RAW from a region taxonomy to a per-chunk role table; make compressed edits preservation-safe.
- **Why it matters:** Gates permanent terrain/collision/seed disc edits **and** the geometry editor; resolves the chunk-34 contradiction.
- **Deliverables:** 69-chunk (subtype→consumer→role) table; chunk-34 mesh decode + model→world transform; PROPACK-equivalent encoder *or* a documented size-budget rule; an LBA-shift rebuild proof; committed asset extractors.
- **Dependencies:** M0 (harness), M2.
- **Tasks:** GAP-0022, GAP-0023, GAP-0024, GAP-0025, GAP-0026, GAP-0027, GAP-0005.
- **Acceptance:** ✅ 69/69 chunks classified (≥80% target met); ✅ chunk-34 decoded to intermediate form + missing transform var named; ✅ compressed edit within-budget path documented + boots (seed case). *(Residual: oversize-edit boot is local-only.)*
- **Risks:** PROPACK encoder may be non-trivial → fall back to size-budget editing.
- **Related:** [[MEM - LEVEL.RAW chunk inventory]] · [[Finding - LEVEL.RAW is compressed]] · [[Asset - Character and plant models]].
- **Open questions:** OQ compression + assets groups.

### Milestone 5 — Core Engine Systems  🟢 *(baseline established 2026-06-20)*
> [!success] M5 baselines: [[Core - Camera and Projection]] · [[Core - Rendering OT and GPU Packets]] · [[Core - CD Streaming and Caching]] · [[Core - Runtime Audio Path]] · [[Core - FMV and MDEC Playback]]. GAP-0028/0029/0030/0031/0032 → **In Progress** (static baselines done; dynamic confirmation is local-only, GAP-0001). **Carry-forward:** GAP-0023 chunk-34 world-origin gates exact camera/projection.
- **Goal:** Fill the SOLID-adjacent partials: camera follow-law, OT/flip, CD streaming, runtime audio/FMV.
- **Why it matters:** Unblocks the photogenic pit + night skybox (camera scale) and completes the engine model.
- **Deliverables:** camera follow-law + projection calibration; OT + frame-flip notes; a streaming/caching model (or confirmed all-at-load); SPU + FMV trigger notes.
- **Dependencies:** M0, M3 (overlays for camera/audio/FMV).
- **Tasks:** GAP-0028, GAP-0029, GAP-0030, GAP-0031, GAP-0032.
- **Acceptance:** predict on-screen pixel of a known world point within tolerance; OT + streaming documented with evidence.
- **Risks:** much lives in overlays (depends on M3); audio/FMV are low priority.
- **Related:** [[Camera]] · [[Rendering]] · [[API - camera transform]] · [[API - transferLog]].
- **Open questions:** OQ rendering + audio/video groups; [[Open Questions]] P1 #2, P-enh #17.

### Milestone 6 — Gameplay Systems  🟢 *(scoped 2026-06-20; 4/4 acceptance clauses met 2026-06-21 — the editor seed path closed the binding residual)*
> [!note] M6 started (scoped): [[Gameplay Systems Baseline]] + [[Gameplay - Events and Triggers]] (GAP-0033). The timed scripted-spawn **sequencer is statically located** (cursor `0x800822f4` / dispatcher `fcn.80054964` / verb `0x800b3bb8` / timer `0x800b402c`); interpreter trace + GAP-0034/0036 need the **event-state / shell-phase fixture** (local-only, GAP-0001). Carry-forward: GAP-0023 world-origin, GAP-0028 camera.
> [!success] M6 GAP-0033 — EVENT INTERPRETER FULLY MODELED → Verified (2026-06-21): the authored event/trigger interpreter is the **per-object "object actor" bytecode VM [[FUNC_8004C13C]]** — fetch `lhu` opcode from object[+0x70] stream → `jr [0x8001b2f4+op*4]` → loop → persist IP. **All 26 opcodes decoded/bounded (0 unknown)** + phase-2 motion table + opcode-12 CALL sub-table + object layout; primitives = movement (op9 set-target ← LEVEL.DAT waypoints, op4 random-walk), waits, **player-proximity TRIGGER (op17)**, conditional branch (op20), and a **native+overlay CALL (op12)**. **Cold-boot LEVEL01 fixture** ([[Experiment - Mover VM cold boot opcode trace]]) captured a fresh live stream (`[op17][op9][op0-loop]`). **Program source = RESIDENT** (table `0x80077af8`), not LEVEL.DAT. ABL's events are **three lanes** ([[Event and scripting system]]): (1) per-scene CODE handlers (`0x80054964` scene_id dispatch, NOT a VM), (2) resident **noise** cursor `0x800822f4`/`0x80017DB4` (param jitter, NOT opcodes), (3) the **VM** + contact-action `jr`-dispatch ([[FUNC_800586B0]]). The prior "no interpreter exists" hypothesis was REFUTED. Narrow residuals: 5 LIKELY opcodes (5/11/14/24/25) + the program-selection seed + overlay-CALL bodies.
> [!success] M6 GAP-0035 — RUNTIME-CONFIRMED (2026-06-21): player **spawn + non-LEVEL01 warp landing** = [[FUNC_80046B20]]`(player, scene_id)` ← resident EXE table `0x80077314` ([[Experiment - Initial spawn write-watch]] / [[Experiment - Warp landing diversion]], landings to scene 3/6/2/4 clean). In-game warp **trigger LEVER captured** = transition-state `[0x800823a0]`=6 → scene-init, via overlay scene verbs (dispatcher `0x80054964`); orchestrator [[FUNC_8005222C]] is shell-only/downstream ([[Experiment - In-game warp trigger]]). **Overlay verb DECODED (Pass-3, 2026-06-21):** the type-2 initiator [[FUNC_8004A700]] is `jal`'d by overlay scene verbs (e.g. scene-3 `0x800b3e88` → `a3=destination`, PROVEN); type-6 [[FUNC_8004ABF4]] is a per-tick countdown carrying no destination; destination is shell-resolved at `0x8004fda0`. **Residual:** a clean in-game level→level landing stays blocked on the **shell-phase destination index + orchestrator resource sequencing** (a gameplay-side lever poke → scene-16 crash) = GAP-0033.
> [!success] M6 RESIDUALS PASS (2026-06-21): **GAP-0034 PATH decided** ✅ — `PATH*.BIN` is *reference-live* (EXE filename `\PAD\PATH00.BIN` @`0x80078ea4` + loader `0x8006f6a0`, 0 absolute xrefs ⇒ overlay-dispatched; 7 files on disc) but *runtime-dead/scenario-gated* (0 touches across 12 stages + ~10 enemies) → **PARTIAL**, decisive next-experiment named. **GAP-0037 input→movement DECODED** ✅ (static + runtime-confirmed local-only): pad-poll wrapper `0x8003a2dc`→read `0x80039c34`→raw `0x80082412`→decode `0x800512a0`→word `0x80082488`→Left/Right `0x80/0x20`→heading, Up/Down/R1 `0x10/0x40/0x800`→speed→GTE→velocity `0x800a652c`→[[FUNC_8003633C]]; live: holding Up → velX=332 + motion. **GAP-0036 baseline** — shell substate sequencer decoded (table `0x8001b3c4`, 6 handlers latch dest-index `0x8008245c`={1,11,2,7,12}, substate-5→[[FUNC_8005222C]]), which also **corroborates GAP-0035B's "shell-only destination" terminal model**; menu-nav cursor + save/memcard remain the residual. **GAP-0033 docs corrected** (the stale "opcode stream in LEVEL.DAT" line refuted; LIKELY-opcode count fixed 6→5). **Editor M6 clause — SEED EDIT PATH LANDED ✅** (see the editor-clause callout below).
> [!success] M6 EDITOR SEED CLAUSE — CHUNK-31 SEED EDIT PATH LANDED (2026-06-21): the level editor's plantable-seed layer (LEVEL.RAW **chunk 31**, content marker `0x23`, 0x1c-byte records: s32 X/Y/Z @+0/4/8 + 16 metadata bytes) is now **read + edit + export** end-to-end. `tools/seed_table.py` = the typed parser/serializer (schema CONFIRMED against the two operator-proven LEVEL01 seeds — rec #19 stuck, rec #26 start) plus a chunk read/splice wrapper over the **existing** codec (`decode_level_raw` / `recompress_level_raw`, no parallel codec). `tools/apply_seed_edits.py` = a declarative spec runner mirroring the pickup `apply_level_placements.py` but with a **DEDICATED** schema (per the editor-roadmap rule "don't overload pickup YAML"); disc rebuild reuses `rebuild_with_patched_dat.py --target files/LEVEL01/LEVEL.RAW`. A live dry-run+write on the real LEVEL.RAW reproduced the **G32 +1242 B** in-slack edit (chunk-31 re-parse OK, within the 366-sector budget). The editor data model (`scene_importer.import_seeds`, editor WIP) reads **32 active** seeds with file+runtime coords (metadata preserved). Tests: `tests/test_seed_table.py` (10, synthetic, CI-safe) + seed read locked in the importer test. Terrain/collision preview stay **real-sourced but PARTIAL** (carry-forward gaps). ⇒ the editor seed/preview clause flips ⛔ BLOCKED → ✅.
- **Goal:** Decode the event/scripting layer and the AI/nav subsystem; reach non-LEVEL01 states; ship the editor's next tier.
- **Why it matters:** The event layer is the common wall behind AI, warp, gated records, and streaming; the editor is the project's flagship deliverable.
- **Deliverables:** an event/trigger model + ≥1 decoded trigger; a PATH decision (dead vs decoded); a successful live warp + shell-phase fixture; menu/save + input→movement notes; editor advanced from *pickup planner* → seed/terrain layers (per [[ABL 3D Level Editor Roadmap]]).
- **Dependencies:** M0, M3, M4 (chunk roles for terrain editing), an event-state fixture.
- **Tasks:** GAP-0033, GAP-0034, GAP-0035, GAP-0036, GAP-0037, plus the editor sub-roadmap.
- **Acceptance:** event interpreter **fully modeled → Verified** ✅ (GAP-0033: object-actor VM [[FUNC_8004C13C]], 26 opcodes + cold-boot stream — 2026-06-21); PATH role **decided with evidence** ✅ (object-motion lane = VM opcode-9; `PATH*.BIN` = **PARTIAL — reference-live (EXE filename `\PAD\PATH00.BIN` + loader `0x8006f6a0`) / runtime-dead-scenario-gated**, decisive next-experiment named — GAP-0034); a warp lands without crash ✅ (GAP-0035A arch Verified: cold-boot diversion → scene 3/6/2/4 clean; 0035B clean in-game handoff **Blocked by design** — destination index `0x8008245c` is shell-only-writable, [[Menu and HUD structure]] §4a); **input→movement decoded + runtime-confirmed** ✅ (GAP-0037: pad-poll `0x8003a2dc`→decode `0x800512a0`→heading/speed→GTE→velocity→integrator); **menu/shell substate sequencer decoded** (GAP-0036 baseline; menu-nav + save residual); **editor edits seeds and previews terrain/collision from real chunk data — ✅ MET** (seed read/edit/export LANDED: `tools/seed_table.py` typed chunk-31 parser/editor + `tools/apply_seed_edits.py` spec runner reuse the proven LZ codec; 10 synthetic round-trip tests + a live demo reproduce the G32 in-game proof, +1242 B within the 366-sector budget; the editor model reads 32 active seeds. Terrain preview = **real decoded data** — 217 `fcn.80010000` DAT mesh payloads incl. CONFIRMED Candidate A — fidelity PARTIAL on chunk-34/35 spawn terrain (GAP-0023 world-origin); collision preview = **real chunk-32 plane**, full-array enumeration PARTIAL pending the DuckStation sector-table dump `0x800a7e48` (GAP-0001)). **⇒ M6 = 4 of 4 acceptance clauses met → M6 COMPLETE; residual *fidelity* (terrain transform GAP-0023, full collision GAP-0001, in-game level→level handoff 0035B blocked-by-design) carried forward as separate gaps, NOT M6 blockers.**
- **Risks:** event-gated content needs a fixture that has never been captured (GAP-0033) — the binding constraint.
- **Related:** [[Systems]] · [[Enemy relocation method]] · [[ABL 3D Level Editor Roadmap]] · [[ABL 3D Phase 1 Gap Checklist]].
- **Open questions:** OQ gameplay-systems group; [[Open Questions]] P4–P5, enhancement #16.

### Milestone 7 — Verification, Testing & Matching  🟡 *(started 2026-06-21)*
> [!note] M7 started — first pass 2026-06-21 → [[Verification - M7 Headline Recheck]]
> **GAP-0011 RESOLVED (Verified):** the LEVEL01 **spawn-area** visible floor is **LEVEL.DAT** (`fcn.80010000`, source file `0x15dec..0x2f59c`), **not** chunk-34/35; the chunk-34 "spawn ≠ DAT" contradiction is reconciled (chunk-34/35 = occluded/collision layer) — [[Experiment - Spawn-floor render source]], replayable via `tools/trace_spawn_floor.py`. **GAP-0038 → Verified:** a 2nd independent angle (source separation) **plus the G29 Pass-3 pristine-vs-patched counterfactual (both arms, 2026-06-21)**. The missing `ABL_G28_CANDIDATE_A_FLOOR_Y_TEST.bin` was rebuilt locally (`tools/rebuild_with_patched_dat.py --write`, embedded-verified) and traced via `tools/trace_g29_pass3_arm_b.py`; a phase-matched pristine-vs-G28 differential differs in **only the visual-edit halfword** while the collision sector-table hash, resolver path, player-Y writer, and footing trajectory are byte-identical — [[Experiment - G29 Pass-3 differential]]. This is also a headline replay for **GAP-0040** (now **four**: spawn-floor, G29 Arm A/B, LEVEL02-floor). **GAP-0008 → Resolved (2026-06-21):** the findings store now has **f13 as the sole CONFIRMED** visible-floor answer with M7 evidence refs (f5/f10 already Superseded; f4/f8 stale caveats corrected; surgical edit, no `findings.save`). **GAP-0039 → LEVEL02 floor CONFIRMED per-pixel (2026-06-21):** the floor under Flik on scene 3 is DAT via `fcn.80010000` (shared leaf `0x80019xxx`; leaf caller `ra` 40/40 inside `fcn.80010000`; `fcn.80010000` `a0` 16/16 DAT), collision separate — [[Experiment - LEVEL02 floor source]], replayable via `tools/trace_level02_floor.py`. This **corrects** the first-pass single-frame artifact (`fcn.800172dc`=0): robustly **both** renderers are active, but the floor *specifically* is the DAT driver. All-stage generality remains **LIKELY** (one stage per-pixel; no LEVEL02 counterfactual). All dynamic work is local-only (**GAP-0001**). Matching (GAP-0021) untouched (scope-gated).
- **Goal:** Raise the headlines to the project's own CONFIRMED bar; prove generality; *(preservation)* stand up matching.
- **Why it matters:** The flagship result does not yet meet ≥2-independent-methods (B3); generality is argued not proven (B8).
- **Deliverables:** G29 Pass-3 differential run; a 2nd independent visual-floor edit; the chunk-34/floor reconciliation; a deep trace on ≥1 non-LEVEL01 level; replayable headline experiments via [[API - experiment runner]]; *(preservation ⚖️)* an `objdiff` matching workflow.
- **Dependencies:** M0, M3 ⚖️, M4.
- **Tasks:** GAP-0038, GAP-0011, GAP-0039, GAP-0040, GAP-0021 ⚖️.
- **Acceptance:** visual≠collision corroborated by ≥2 independent experiments; ≥1 non-LEVEL01 deep map; headlines replay from a script.
- **Risks:** re-running may *re-flip* a headline — that is the point; budget for it.
- **Related:** [[Finding - Visual is not collision]] · [[Experiment - G29 collision lever validation]] · [[Playbook - Verify a hypothesis]].
- **Open questions:** OQ documentation + executable groups.

### Milestone 8 — Documentation Hardening & Release-Readiness  🟢 *(COMPLETE 2026-06-21 — clean tracked base self-consistent; reproducibility residual is GAP-0001 only)*
> [!note] M8 started — first pass 2026-06-21 (documentation hardening; no live-debugger work required)
> Reconciled the stale-status debt this milestone exists to kill. **GAP-0042** — [[CONTRIBUTING]] already existed (M0) and is now hardened: added the required-reading **`.claude/skills/duckstation-external-debugger/SKILL.md`** live-debugger guide, the operator-gated dynamic-evidence rule (until GAP-0001), a per-status **control-doc update rule**, and a fuller preservation enumeration (saves/memcards/screenshots/traces → hash, don't commit). **GAP-0012** — [[Tools Catalog]] re-counted from disk **74 → 85** (61 tracked + 24 untracked) with CI-safe (57/28) + host-path (0 `/home`) classification and the 8 missing M7/M3 tools cataloged. **GAP-0007** — [[Risk Matrix]] current-tier table **refreshed for the M7 outcomes** (B3 Major→Medium, B8/B11 annotated) and its stale "In Progress" status reconciled (the current-tier column has existed since M0). **GAP-0041** — this [[Roadmap]] confirmed as the maintained top-level control doc (linked from [[Home]] + [[Project Index]]). Swept M7-spillover staleness from [[Home]] + [[Glossary]] (the GAP-0011/0008/0038 resolutions). All edits are doc-only; operator WIP untouched; reproducibility ceiling (GAP-0001) unchanged.
>
> [!note] M8 second pass — 2026-06-21 (GAP-0009/0010 stale-claim sweep; documentation-only)
> Finished the M7/old-model stale-claim sweep across the **clean tracked** base. **GAP-0009 → Resolved:** every note that called chunk-35/`fcn.800172dc` the visible floor now carries the occlusion caveat + f13 link — [[Home]] (pass 1), the two terrain Findings (already caveated), plus newly-caveated [[G30 - Terrain render source]] and [[Experiment - G30 localized terrain edit]] (their un-caveated "VISIBLE terrain deform" CONFIRMED claims marked **SUPERSEDED**, preserving the valid edit-method + DAT-floor lever). **GAP-0010 → Resolved:** [[FUNC_800172DC]] + [[MEM - Terrain vertex buffer 8012C1D0]] retitled/reframed as the **shared `.ALL`/mesh renderer + shared vertex buffer** (terrain = one occluded client), and the control-doc labels in [[Symbols Index]] + [[Functions Index]] updated; filenames retained for wikilink stability (documented as legacy). Also corrected the "still single-source" line in [[Gameplay Systems Baseline]]. **M8 stays 🟡 In Progress (NOT closed):** the clean tracked base is self-consistent, but (1) the **untracked** chunk-34 WIP note `Finding - Chunk 34 master mesh structure` still asserts the M7-refuted "spawn ground = chunk 34/35" and is **operator-owned** → [[Gap Audit|GAP-0011]] residual (leave for operator); (2) 23 operator-WIP tracked notes are uncommitted/unswept; (3) the X-shear↔occlusion *physics* reconciliation is open (local-only, GAP-0001). Acceptance "no CONFIRMED note contradicts another" cannot be certified across operator WIP.
>
> [!success] M8 CLOSED — final closeout pass (2026-06-21; documentation-only, no live debugger)
> The three blockers the second pass left open are resolved. **(1) Clean-base sweep completed honestly** — the prior "GAP-0009 Resolved" was *premature* (it had grepped only the literal phrase "visible terrain renderer"). A broad re-grep found **~13 additional clean tracked notes** still presenting chunk-35 as the visible surface — [[Asset - LEVEL.RAW]], the two chunk-inventory tables ([[MEM - LEVEL.RAW chunk inventory]] / [[MEM - LEVEL.RAW chunk model]]), [[FUNC_8001DFE4]], [[Home]]'s "visual≠collision" line, [[Geometry pipeline]], [[Playbook - Correlate rendering and collision]], [[Core - Camera and Projection]], [[Finding - LEVEL.RAW is compressed]], [[Plan - Terrain+collision matched bump (Option B)]], [[Blockers]], [[Memory Structures]], [[HYP - visual equals collision]] — **all now caveated** (chunk-35 = occluded; visible floor = LEVEL.DAT/[[FUNC_80010000]], f13). **(2) The untracked chunk-34 WIP note is reconciled** ([[Finding - Chunk 34 master mesh structure]]: SUPERSEDED banner + editor coverage-gap reframe; valid structural RE preserved) and committed. **(3) B11/B3 got M7/M8 resolution banners** for their stale present-tense conflict descriptions. **The 23 operator-WIP tracked notes were swept** — clean of stale floor claims (their edits are API-doc expansion). A final tight re-grep shows **no clean tracked note asserts chunk-35 as the visible surface**; the sole remaining instance is the untracked operator note [[ABL Level Editor]] (out of authorized scope). **M8 ≠ project completion** — [[Gap Audit|GAP-0001]] (reproducibility), GAP-0039/0040 (generality / regression), and the decomp track stay open; the X-shear↔occlusion *physics* reconciliation remains a local-only item under GAP-0001 (tracked in [[FUNC_800172DC]] / [[MEM - Terrain vertex buffer 8012C1D0]]).
- **Goal:** A self-consistent, navigable, contributor-ready knowledge base.
- **Why it matters:** B11 is a standing tax; bus-factor-1 (B2) makes onboarding a real mitigation.
- **Deliverables:** keep [[Risk Matrix]]/findings store/Home reconciled; `CONTRIBUTING.md`; this [[Roadmap]] + [[Gap Audit]] + [[Project Index]] + [[Glossary]] maintained; stale-note sweep convention.
- **Dependencies:** rolling; pairs with every milestone's doc deliverables.
- **Tasks:** GAP-0042, GAP-0007 (sustained), GAP-0012, GAP-0041, GAP-0009, GAP-0010; quarterly stale-sweep.
- **Acceptance:** no CONFIRMED note contradicts another ✅; contribution guide exists ✅; control docs carry current Last-audited/Next-review ✅ — **MET 2026-06-21** (clean tracked base; reproducibility residual = GAP-0001).
- **Risks:** doc debt re-accrues fast during active RE → enforce a per-experiment "update the index" step.
- **Related:** [[README]] · [[_Canonical Links]] · [[Blocker - Project documentation is stale and contradictory]].
- **Open questions:** OQ documentation group.

### 🔜 Post-M8 — next roadmap frame (backlog)

> [!summary] Where the project stands after M8
> **M0–M8 is complete and baselined** (clean tracked base self-consistent; M8 closeout `d2fe61b`, 2026-06-21). This is a **baseline, not a finish line** — substantial RE remains. The groups below are the **next frame**: an evidence-ranked backlog, every line tied to an open [[Gap Audit]] gap. This planning pass starts **no new broad RE**; it makes the next workstream explicit and prioritized. Kept as a **post-M8 backlog** (not a numbered M9) until the owner picks up a group and promotes it to a formal milestone. This frame **supersedes §10's M0-era 2-week near-term plan** (now largely executed).

**Recommended next workstream — GAP-0001 RESOLVED on this host (2026-06-21); next is the off-host copy + GAP-0002.** GAP-0001 (the prior top risk) is now closed against its acceptance set: the dirty fork is exported as a **verified recoverable bundle + patchset + untracked archive** (reconstructs the operator source byte-exact, 57/57 files) with an in-repo **tag**; an **independent clone rebuilt `duckstation-qt`**; and the **spawn-floor headline replays from that clean-built binary** (`tools/trace_spawn_floor.py`, exit 0, via the dirty-only `gpu.pickObject`). The headlines (visual≠collision, spawn-floor = DAT, LEVEL02 floor, the mover/object-actor VM, the input→movement law) now rest on a **recoverable** harness, not a single dirty binary. **One residual, operator-only:** replicate the preservation set **off-host** (push to a private remote or copy off-machine; `origin` is upstream, no credentials assumed) — that final step fully retires bus-factor-1 ([[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]]). With GAP-0001 met, the next P0 move is **GAP-0002** (guard the findings store + hash-pin fixtures), then **Format / editor depth** (GAP-0023). Full evidence chain: [[DuckStation Fork Reproducibility]] §"GAP-0001 closure".

| Group | Theme | Gaps | Pri | Status | First action |
|---|---|---|:--:|---|---|
| **P0 Reproducibility** | Preserve the fork; close evidence-loss hazards; one headline replay off-machine | GAP-0001 ✅, GAP-0002, GAP-0040 | P0 | GAP-0001 ✅ Resolved on host (2026-06-21); GAP-0002/0040 In Progress | **Done:** export fork (bundle+patch+tag), clean-clone rebuild, replay spawn-floor. **Next:** off-host copy (operator) → hash-pin fixtures (GAP-0002) |
| **Generality** | Prove the headlines beyond LEVEL01 / LEVEL02-scene-3 | GAP-0039 | P2 | In Progress | Deep chunk+collision map on LEVEL02/03; optional LEVEL02 visual-edit counterfactual |
| **Format / editor depth** | Finish chunk-34 model→world; clear the editor's stale label | GAP-0023 (+ editor stale-label residual) | P1 | In Progress | `execTrace@0x80017464`; reframe the untracked [[ABL Level Editor]] chunk-35 label (operator) |
| **Behavior / subsystems** | Enemy AI/PATH; audio/FMV/menu+save runtime paths | GAP-0034, GAP-0031, GAP-0032, GAP-0036 | P2–P3 | Enemy AI ✅ cross-level decoded (Hopper/Thumper bosses PARTIAL — combat bookkeeping overlay-resident); **audio/FMV/menu+save ✅ Resolved 2026-06-22** (closed-with-residual) | map Thumper boss overlay (`transferLog.resolve 0x800b4138`); Hopper defeat-save; Thud re-test; `PATH*.BIN` decider; audio/FMV/menu residuals = positive live SFX trace, MDEC overlay site, live save write-watch |
| **Optional decompilation** ⚖️ | Matching / compile-diff substrate (scope-gated on GAP-0043) | GAP-0021 | P1 | Deferred | Resume only with a pinned toolchain **and** a concrete modding payoff |

**Acceptance for the GAP-0001 pass — MET 2026-06-21** (mirrors [[DuckStation Fork Reproducibility]] "Exact closure conditions"); the only unmet sub-condition is physical off-host storage (operator):
1. ✅ **Preserve/export the fork source** — 34 modified + 16 untracked (23 files) exported as bundle + tracked patch + untracked archive; clone+patch+extract reconstructs the operator source **byte-exact (57/57 files)**.
2. ✅ **Identify clean vs dirty API methods** — 114 committed (@ `296955321`) vs 27 dirty-only re-verified (0 removed) and pinned per-layer in `tools/duckstation_rpc_method_manifest.md`.
3. ✅ **Create a recoverable bundle / patchset / tag** — done (bundle `72aa9fb0…` + patch `d0b29800…` + archive `c9279b28…` + in-repo tag `abl-gap0001-fork-296955321`). ⚠️ **stored on-host only** — off-machine copy is the lone residual (`origin` is upstream; no credentials assumed).
4. ✅ **Document exact build steps** — CMake/Ninja + clang + vendored Qt6 pack → `duckstation-qt`; executed in the clean clone (binary `fd4bf9ed…`).
5. ✅ **Document API skill usage** — `.claude/skills/duckstation-external-debugger/SKILL.md` recorded as the required live-debugger entry point.
6. ✅ **Reproduce ≥1 headline experiment** from the clean clone — `tools/trace_spawn_floor.py`, exit 0; fork commit/tag, clean binary hash, disc hash `46310218…`, fixture `SCUS-94288_1.sav`, request, and verdict all recorded.
7. ✅ **Keep copyrighted / local-only fixtures out of the repo** — only hashes/paths/method-names committed; bundle/patch/archive/disc/`.sav`/binaries never committed (per [[Preservation Policy]] / [[CONTRIBUTING]]).

> [!note] Operator-WIP residual (not a tracked regression)
> The untracked operator note [[ABL Level Editor]] still labels LEVEL.RAW **chunk 35** "Visible terrain strip." The clean tracked base is already correct (chunk-35 / `fcn.800172dc` = occluded shared mesh; the visible floor = LEVEL.DAT / [[FUNC_80010000]] / f13 — GAP-0009/0010 Resolved). This is **operator-owned WIP outside the M8 tracked closeout**, *not* a reopened GAP-0009 — fold the fix in when that editor note is intentionally tracked (it belongs to the *Format / editor depth* group above).

Re-prioritize and refresh *Last audited / Next review* when a group is promoted to a milestone.

---

## 4. Task backlog (Obsidian-native)

> Checkbox tasks, prioritized. Each carries Priority / Area / Depends / Evidence / Done-when. Promote to a milestone when picked up.

#### P0 — unblock safe/reproducible work
- [~] Preserve the reviewed DuckStation fork state (on-host DONE 2026-06-21; **off-host copy = operator residual**)
  - Priority: P0 · Area: Reproducibility · Depends: operator remote/credentials (for the off-host step only) · Evidence: [[DuckStation Fork Reproducibility]] §"GAP-0001 closure" · Done when: ✅ dirty layer exported (bundle+patch+archive, byte-exact) + ✅ in-repo tag + ✅ clean clone rebuilt + ✅ clone reproduces `trace_spawn_floor.py`; ⬜ preservation set replicated off-host (GAP-0001)
- [ ] Guard the findings store against overwrite + hash-pin the fixture set
  - Priority: P0 · Area: Reproducibility · Depends: — · Evidence: `re_findings_backup.yaml`, [[Reproducibility Checklist]] · Done when: store has a tamper-evident checksum; every [[Fixtures Index]] entry is regenerable/hashed (GAP-0002)
- [x] Record the **scope charter** (preservation Yes/No) in §1 of this roadmap (✅ 2026-06-21)
  - Priority: P0-adjacent (P1) · Area: Governance · Depends: — · Evidence: [[Remediation Plan]] §4a vs [[Risk Matrix]] · Done when: charter stated; scorecard scope reconciled (GAP-0043) — **MET** (charter in §1; [[Blockers]] scorecard relabeled optional gauge; B1 won't-do→deferred)

#### P1 — unblock major analysis progress
- [x] Add a "current tier" column to [[Risk Matrix]]; reconcile [[Blockers]] severity list (✅ column since M0; M7-refreshed + stale statuses reconciled — M8 2026-06-21)
  - Priority: P1 · Area: Doc integrity · Depends: — · Evidence: Matrix vs Remediation log · Done when: Matrix tier == note tier for all 20 (GAP-0007)
- [x] Correct the findings store: f13 sole CONFIRMED + evidence refs (✅ M7 2026-06-21)
  - f5/f10 were already Superseded; cleared the stale "not-yet-validated" caveats on f13/f8, added f13's 4 M7 evidence refs. Surgical edit (no `findings.save`). Exactly one CONFIRMED visible-floor answer (GAP-0008 Resolved)
- [ ] Pick + trace the **spawn-area** floor → reconcile chunk-34 vs DAT-floor
  - Priority: P1 · Area: Geometry · Depends: GAP-0001 · Evidence: [[Finding - Chunk 34 master mesh structure]] vs [[Finding - Candidate A is DAT-backed visual terrain]] · Done when: one evidenced note names the spawn-floor source (GAP-0011)
- [x] Complete **G29 Pass-3 Arm B** (✅ 2026-06-21); optional residual: a 2nd independent visible-floor edit/scene
  - Arm A ✅ + Arm B ✅ — G28 BIN rebuilt locally (`tools/rebuild_with_patched_dat.py --write`) and traced (`tools/trace_g29_pass3_arm_b.py`); phase-matched pristine-vs-G28 differs only in the visual halfword
  - Priority: P1 · Area: Epistemic · Depends: GAP-0001 · Evidence: B3, [[Experiment - G29 Pass-3 differential]] · Done when: pristine/patched collision traces match while the visual edit remains visible (GAP-0038) — **MET**
- [ ] Build the 66/69 LEVEL.RAW chunk role table (subtype→consumer→role)
  - Priority: P1 · Area: Level format · Depends: GAP-0001 · Evidence: [[MEM - LEVEL.RAW chunk inventory]] · Done when: ≥80% chunks have a confirmed consumer+role (GAP-0022)
- [~] Finish chunk-34 decode + model→world transform — **✅ Resolved for the floor (2026-06-22)**: offline `world = T_obj + v_local` read from the LEVEL.DAT node array (@`0x45f0`, stride `0x18`; `T_obj`@+0/4/8, payload@+0x14); 3-way disk==runtime==formula + cross-level static (L04/L05). chunk-34 = not-drawn.
  - Priority: P1 · Area: Level format · Depends: — · Evidence: live GTE 3-way + static DAT files; `tools/analyze_g27_floor_candidates.py` · Done when: terrain verts project within tolerance (GAP-0023) — **MET**. Editor fix = `scene3d.py` `world=T_obj+v` (drop 1450/Y-flip) + `scene_importer` node-anchor source. Residuals: rotated-mesh `M_obj`, decor Y-flip, cross-level live provenance.
- [x] Make host-hardcoded tools portable + add `tools/requirements.txt` (✅ 2026-06-21)
  - Priority: P1 · Area: Reproducibility · Depends: — · Evidence: `tools/_env.py`, `tests/test_path_portability.py` · Done when: 0 hardcoded paths in tracked tools; one-command provisioning (GAP-0003) — **MET**

#### P2 — important, non-blocking
- [x] Regenerate [[Tools Catalog]] from disk (85 tools: 61T+24U; CI-safe 57/28; 0 `/home` paths) — GAP-0012 *(M8 2026-06-21)*
- [x] `Preservation Policy.md` (what may/may not be shared) — GAP-0004 *(✅ 2026-06-22: exists + linked Index/README/Home + `.gitignore` names it)*
- [x] `Checksum Manifest.md` + release id; PAL/proto scope — GAP-0014 *(M1; residual: formal redump.org datfile match)*
- [x] `pytest` + safe CI + codec round-trip; keep GPU/live paths isolated — GAP-0017 ✅, GAP-0040 ✅ *(2026-06-22: `safe-tests.yml` committed + 40 passed; opt-in `live` replay test `tests/test_live_replays.py`; residual = operator GitHub-green + re-run replays off-host)*
- [x] Tool/library census; pin known `mkpsxiso`/`jpsxdec`/Python deps — GAP-0016 *(✅ 2026-06-22: + PsyQ libs dated ≥1997-03-28 via EXE RCS `$Id$`; exact `ccpsx` compiler = GAP-0021-gated)*
- [x] Commit reproducible asset extractors + output-hash manifest — GAP-0005 *(✅ 2026-06-22: `tools/extract_vab.py` 1771/1771 byte-match + `extracted/SHA256SUMS` 1879 verified; GFX via `decode_level_raw.py`; XA/FMV pinned-jpsxdec recipe)*
- [x] Establish complete known overlay metadata baseline + enumerate base Region-A LEVEL01; deep LEVEL1/Region B work deferred — GAP-0020 *(✅ Resolved 2026-06-22: M3 baseline meets acceptance — multiple overlays behavior-mapped)*
- [~] Camera follow-law + projection calibration — GAP-0028 *(✅ 2026-06-22: follow-law decoded + validated — `fcn.8004df18`, boom `dist=900`×32 / `HEIGHT=12288`, smoothing k=1/8; residual = closed-form heading/pitch + RT→GTE projection for byte-exact pixels)*
- [ ] Capture an event-state fixture; identify the event/trigger interpreter — GAP-0033
- [ ] Decide PATH (dead vs decode); document — GAP-0034
- [x] Deep-trace LEVEL02/03 (generality) — GAP-0039 *(✅ 2026-06-22: LEVEL02(=L03) deep chunk+collision map — collision source-correlated + motion-validated; floor format 11/11 gameplay levels; sub-types decoded)*
- [x] PROPACK rebuild strategy: size-budget rule documented — GAP-0024 *(M4; byte-exact encoder optional)*
- [ ] Prove an LBA-shifting edit boots + loads in-level — GAP-0025
- [x] `symbols/re_symbols.sym` + confidence/source baseline + DuckStation-CSV/r2 round-trip — GAP-0018
- [x] `CONTRIBUTING.md` + per-task owner/status convention — GAP-0042 *(exists since M0; M8-hardened 2026-06-21: skill guide + update rule + preservation)*

#### P3 — cleanup / nice-to-have
- [x] ~~Move `tools/` build artifacts to ignored `out/`; drop `_step3.py`~~ — GAP-0006 **✅ Resolved 2026-06-22** (already clean: tracked = source + 2 hash-pinned oracles; artifacts gitignored; `_step3.py` untracked)
- [x] ~~Update `level_editor/README.md`~~ — GAP-0013 **✅ Resolved 2026-06-22** (README line 57 already distinguishes the working 3D-Scene tab; status was stale)
- [x] `MEM - Global memory map.md` with per-claim confidence and explicit unknowns — GAP-0019
- [x] Narrative `Asset - Disc file map.md` from `abl.xml` — GAP-0015 *(M1)*
- [x] GFX CLUT exactness — GAP-0027 **✅ Resolved 2026-06-22** (floor CLUT in LEVEL01/LEVEL.RAW; deterministic RGB888→BGR555, 14/16 exact); [x] `.ALL`/`.ANM` fine grammar — GAP-0026 **✅ Resolved 2026-06-22** (round-trip exporter `tools/parse_all_anm.py`: .ALL 78/78 + .ANM 58/58 byte-exact; residual = field-typing the .ALL non-primitive spans)
- [x] OT/flip note; runtime audio + FMV triggers — GAP-0030/0031/0032 **✅ Resolved 2026-06-22** (OT=DMA list + flip `0x800646b8`; SFX `0x80050994`+libspu+XA; FMV.BIN manifest sequence — each with a named residual)
- [x] Live warp — GAP-0035 **terminal reframe adopted** (0035A Verified / 0035B terminal-by-design); input→movement baselined — GAP-0037; menu/save — GAP-0036 **✅ Resolved 2026-06-22** (menu-nav `0x800B687C` + save in MEMORY.BIN overlay)

---

## 5. Traceability

Every milestone item maps to ≥1 gap (and most to an existing blocker). Forward map:

| Milestone | Gaps (→ Blockers) |
|---|---|
| M0 | GAP-0001/2/3 (B2) · 0004 · 0005 (B5/6/20) · 0006 · 0007/8/9/10/12/13 (B11) · 0041/0042/0043 (B1) |
| M1 | GAP-0014 (B12) · 0015 (B8) |
| M2 | GAP-0016 (B13) · 0017/0040 (B19) |
| M3 | GAP-0019 (B16) · 0018 (B15) · 0020 (B17) · 0021 (B1) |
| M4 | GAP-0022/0023 (B9) · 0024 (B14) · 0025 (B4) · 0026 (B7) · 0027 (B20) · 0005 |
| M5 | GAP-0028 · 0029 (B8) · 0030 · 0031 (B5) · 0032 (B6) |
| M6 | GAP-0033 (B10) · 0034 (B18) · 0035 (B8) · 0036 · 0037 + editor sub-roadmap |
| M7 | GAP-0038 (B3) · 0011 · 0039 (B8) · 0040 · 0021 ⚖️ (B1) |
| M8 | GAP-0042 · 0007/0012 (B11) · 0041 |

Reverse map (gap → where worked): every GAP-000N appears in exactly one primary milestone above (a few cross-cutting doc gaps recur in M8). The full per-gap detail, with acceptance criteria, is in **[[Gap Audit]]**.

---

## 6. Evidence standards

Adopt the vault's existing rubric ([[API - determinism]]) as the *recording* standard. Every claim that enters [[Confirmed Knowledge]], a `Finding -`, or the findings store must record:

- **Claim** — one sentence, falsifiable.
- **File path(s)** — vault note + source artifact (`docs/…`, `src_re*/…`, `tools/…`, `REBUILD/…`).
- **Offset / address** — file offset and/or RAM address (and chunk# for LEVEL.RAW).
- **Tool + version** — e.g. DuckStation fork `296955321`, `mkpsxiso 2.20`, `jpsxdec v2.1-beta`, r2 `anal.gp=0x80081d98`, the `tools/*.py` used.
- **Command run** — the exact invocation / API call (`experiment.run …`, `accessLog.addWatch …`).
- **Observed output** — the concrete result (sector diff count, px diff bbox, watch hits, hash).
- **Confidence** — `CONFIRMED` (reproducible **and** causal: counterfactual or ≥2 independent methods) · `LIKELY` · `INVESTIGATING` · `UNKNOWN` · `DISPROVEN`/`SUPERSEDED`. A single uncontrolled snapshot is at most `LIKELY`; *screenshots corroborate, they do not prove*.
- **Date** — absolute (ISO).
- **Related notes** — wikilinks to Functions/MEM/Experiments/Fixtures/API touched.

**Reproducibility minimum:** name the **fixture** (save state / movie) and the **frame count**; settle after `loadState` before `addWatch`; for animated subjects use a **phase-matched control**. A finding without a fixture + command is `INVESTIGATING`, not `CONFIRMED`.

---

## 7. Status taxonomy

| Status | Meaning |
|---|---|
| **Unknown** | Not investigated; no evidence either way. |
| **Needs Evidence** | Hypothesis/claim exists but lacks reproducible/causal proof (≤ `LIKELY`). |
| **In Progress** | Actively being worked; partial evidence. |
| **Blocked** | Cannot proceed until a dependency (often a fixture or the fork) is resolved. |
| **Verified** | Meets the §6 `CONFIRMED` bar (reproducible **and** causal). |
| **Superseded** | Replaced/retracted by later evidence; kept for history (link the replacement). |

---

## 8. Priority taxonomy

| Pri | Meaning |
|---|---|
| **P0** | Blocks safe/reproducible work (e.g. verification reproducibility, evidence-loss hazards). Do first. |
| **P1** | Blocks major analysis progress (headline integrity, codec/chunk roles, the scope charter). |
| **P2** | Important but not blocking (provenance, toolchain pinning, engine-system breadth). |
| **P3** | Cleanup / nice-to-have (naming, narrative maps, cosmetic format residuals). |

---

## 9. Risk register

| Risk | Likelihood | Impact | Mitigation | Related gap |
|---|:--:|:--:|---|---|
| Loss of the single host / private fork → verification collapse | Medium | Critical | Vendor fork + off-machine remote + hashed fixtures (M0) | GAP-0001/0002 (B2) |
| Findings store / Risk Matrix silently misrepresent state | High | High | Reconcile + add "current tier"; single CONFIRMED per question (M0/M8) | GAP-0007/0008 (B11) |
| Central headline (visual≠collision) re-flips under scrutiny | Medium | High | Run G29 Pass-3 + 2nd edit before building on it (M7) | GAP-0038/0011 (B3) |
| Master `.bin` not a faithful Redump dump → offsets/rebuild subtly wrong | Low | Critical | Match Redump id; checksum manifest (M1) | GAP-0014 (B12) |
| Literal recompressor blocks preservation-grade rebuilds; oversize edits shift LBAs | Medium | Medium | PROPACK encoder or size-budget rule; LBA-shift proof (M4) | GAP-0024/0025 (B14/B4) |
| Decompilation never reaches matching (if preservation adopted) | Medium | High* | Decide charter; splat pilot on one function (M3/M7) | GAP-0021 (B1) ⚖️ |
| Event-gated content (AI/warp/streaming) unreachable from any saved state | High | Medium | Capture an event-state fixture (the binding constraint) | GAP-0033/0034 (B10/B18) |
| r2 auto-boundaries/`$gp` wrong → cascading misnaming | Low | Medium | Persisted symbol map + spot re-verification (M3) | GAP-0018/0020 (B15/B17) |
| Tool/catalog drift hides the real toolchain from a contributor | High | Low | Regenerate catalog; CI; CONTRIBUTING (M2/M8) | GAP-0012/0042 |
| Doc debt re-accrues during active RE | High | Medium | Per-experiment "update index" step; quarterly sweep | GAP-0007 (B11) |

`*` impact only under a preservation charter (GAP-0043).

---

## 10. Near-term plan (2 weeks → next review 2026-07-04)

> Front-loaded on the cross-cutting roots (B2 reproducibility + B11 doc integrity) because they are the cheapest, highest-leverage work and they make every later result trustworthy. Mostly offline/ops + already-built harness — no new RE risk in week 1. Grouped, not rigidly daily.

**Week 1 — Reproducibility & truth-in-docs (M0; offline/ops)**
1. ✅ **GAP-0043 follow-through** (2026-06-21) — charter decided + legacy preservation-weighted scorecard reconciled (relabeled optional gauge; B1 won't-do→deferred); modding-grade goal unchanged.
2. **GAP-0001/0002** — vendor + pin the fork; push to an off-machine remote; hash-pin the fixture set; add the findings-store overwrite guard.
3. ✅ **GAP-0003** (2026-06-21) — env pattern via `tools/_env.py` across tracked tools (0 host literals); `tools/requirements.txt` pinned; portability test covers `tools/`+`tests/`.
4. **GAP-0007** — add the "current tier" column to [[Risk Matrix]]; reconcile [[Blockers]]'s severity list.
5. **GAP-0012 / GAP-0041 / GAP-0042** — regenerate [[Tools Catalog]] (69 tools); confirm this [[Roadmap]] is linked from [[Home]]; stub `CONTRIBUTING.md`.

**Week 2 — Headline integrity & format depth (M7/M4; uses the existing harness)**
6. **GAP-0008 + GAP-0009/0010** — once the harness is reproducible, correct the findings store (f5/f10 → Superseded) and propagate the occlusion caveat + the "shared mesh renderer" renaming.
7. **GAP-0011 + GAP-0038** — spawn-area pick/trace ✅; G29 Pass-3 **Arm A ✅ + Arm B ✅ (2026-06-21)**. *The flagship counterfactual ran and held: the visual edit perturbs nothing on the collision side.* Optional next: a 2nd visible-floor edit/scene to harden generality.
8. **GAP-0022 (start)** — begin the per-chunk consumer trace for the highest-value unmapped LEVEL.RAW chunks (incl. chunk 34, feeding GAP-0023).

**Exit check (2026-07-04):** a 2nd machine reproduces one headline; [[Risk Matrix]] tells the truth; the findings store has one floor answer; the spawn-floor source is named with pick+trace evidence; G29 Pass-3 has run. Update Last-audited/Next-review and re-prioritize.

---

## 11. Obsidian usability

- **Discovery hub:** [[Home]] (dashboard) · **Control hub:** [[Project Index]] (this roadmap, Gap Audit, Open Questions, Glossary, evidence logs).
- **Tags:** `#roadmap` `#gap-audit` for the control docs; reuse existing `#dashboard` `#blockers` `#due-diligence`.
- **Backlinks:** this note links every milestone to its gaps, blockers, Findings, Functions, MEM, API, and Playbook notes; use Obsidian backlinks to navigate up from any note to its milestone.
- **Maintenance:** register new notes in [[_Canonical Links]]; refresh `Last audited` / `Next review` each cycle; keep one CONFIRMED answer per question (M8).

## See also
[[Gap Audit]] · [[Project Index]] · [[Open Questions]] · [[Glossary]] · [[Blockers]] · [[Risk Matrix]] · [[Assumptions Register]] · [[Remediation Plan]] · [[Confirmed Knowledge]] · [[ABL 3D Level Editor Roadmap]] · [[Home]]
