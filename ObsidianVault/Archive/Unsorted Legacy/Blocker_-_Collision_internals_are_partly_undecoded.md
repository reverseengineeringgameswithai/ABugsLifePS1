---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Collision internals are partly undecoded.md
aliases:
  - "Blocker - Collision internals are partly undecoded"
migration_action: archive
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Collision internals are partly undecoded.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Collision internals are partly undecoded
type: blocker
id: B18
severity: LOW
category: collision
confidence: CONFIRMED
tags: [blocker, medium, collision, pathing]
updated: 2026-06-22
---

# 🟡 B18 — Collision provenance, resolution math, and AI pathing are partly undecoded

> The visual≠collision *headline* is established, but the collision subsystem's internals are not: the writer story has competing accounts, the byte→record map is not byte-precise, several resolution-math branches are TODO, and the AI/nav `PATH*.BIN` data — on the project's own roadmap — is undecoded.

> [!check] Update (2026-06-18, B18) — **byte-precise chunk-32 map DONE + provenance reconciled.** The live plane `0x800D10E8` byte-matches the offline-decompressed chunk 32 at off `0xfa60`, and the whole chunk maps **linearly** to live base `0x800C1688` (verified on 2 planes + the header). ⇒ **planes are raw decompressor output** (G29 §2.9 correct; the converter builds the *sector table* `0x800a7e48`, not the planes) — the `0x800F7xxx`/`0x800D0xxx`/`0x800a7e48` confusion is resolved. Permanent collision edits are now byte-precise: `chunk32_off = live − 0x800C1688` → [[MEM - Collision plane record]]. **Residual:** resolver math (no-contact branch / slide-re-test / point-in-face) + `PATH*.BIN` decode. **Severity → Low.**

> [!check] **Update (2026-06-18) — resolver math advanced (live trace); PATH loader is scenario-gated.**
> **(b) Resolver math — decoded the live chain + the no-contact branch.** On the gameplay state the per-frame containment test is **`0x800322a0`** (point-in-face): reads a face/vertex table at `0x80090868`–`0x8009087c` (world-space s32 coords; count at `gp+0x5cc`), args are stack pointers to the test-point xyz + output, and it computes edge-vector differences + calls vector helper **`0x800602b0`**. Walking, the resolver **`0x800345cc` fires (29×/60f) and the no-contact branch `0x80035210` fires (28×)** — both reachable and deterministic. **No-contact branch fully decoded:** when no face contains the player, the resolver applies the **raw movement delta unmodified** — `pos.x += Δx; pos.y += Δy; pos.z += Δz` (`s3`=Δ as 3×s16, `s5`=player pos as 3×s32), returning status **0** (vs. the contact path which snaps to face height via `sw v1,0(t5)` and returns status **2**). So "no contact" = free move, no footing snap. **Residual:** the slide/re-test iteration and `wall 0x80025084` (0 hits on open ground — needs a wall scenario), plus the full point-in-face inner loop + `0x800602b0`.
> **(a) `PATH*.BIN` loader — SCENARIO-GATED (not reachable from current states).** RAM search for PATH01.BIN's content found it **absent in both the post-load and active-gameplay states**, and the filename template `CD\PAD\PATH00.BIN` (`0x80078ea4`) saw **0 touches during the level load** (still reads `PATH00`). ⇒ the nav graph is **loaded on-demand for specific AI encounters**, not at level load — the same scenario-gating wall as the negative-record/warp consumers. The on-disc format has clear flag bits (`0x8000`/`0x8010`/`0x4010`), so it is **not** plain 3×u16 coords; precise node/adjacency decode still needs the loader, which requires a save state inside an AI/pathing encounter. Deferred (gated, not blocked-by-tooling).

> [!check] **Update (2026-06-18) — wall/ledge math DECODED (reached the fence scenario).** The `openfloor` fixture spawns an enemy **+ fence** when walking forward; driving Flik into the fence (via injected input — no operator) made **`wall 0x80025084` fire 108×** (0 on open ground). Decoded `fcn.80025084` = **oriented-plane containment with a collision radius**: per wall edge it computes the **3D dot product** `dist = Σ_i ((player_pos[i] << 5) − edge_point[i]) · normal[i]` (player pos `[a1+0x80]→[+0/4/8]`, edge point `[a2+0/4/8]`, edge normals at `0x8009?fbc/fbe/fc0`), normalizes `dist >>= 17`, and tests `dist > −radius` (radius = s16 at `a1+0x6a`) ⇒ penetrating → push back/slide. The edge record is looked up via `[a1+0]` → table `0x800a6300`. Fixture saved → **`SCUS-94288_fence_wall.sav`** (holding ↑ re-fires the wall path). ⇒ collision-math residuals now decoded: **floor (point-in-face `0x800322a0`) + no-contact (free move `0x80035210`) + wall/ledge (oriented-plane `0x80025084`)** → [[FUNC_80025084]].
> **PATH is NOT enemy AI (decisive, 2026-06-18).** Tested **~10 enemy types** (openfloor BADBUG/MOS/WASP/DOT/BADWORM + 5 operator saves spider/mosquito/worm/bee/pill_bug) — **no `PATH*.BIN` content and no built `PATHnn.BIN` filename ever appears in RAM**, and the `CD\PAD\PATH00.BIN` template is never modified. The 5 operator saves all share an **identical model roster** ⇒ same LEVEL01 section (redundant coverage). Static hunt: the "%s: path level (%d) error" loader is **`0x8006f6a0`** — a **generic `\`-separated-path CD file loader** (no direct `jal` callers ⇒ called **indirectly / overlay-dispatched**); the PATH-specific filename construction is not in the main EXE text. ⇒ `PATH*.BIN` is a **"path-level" subsystem** (indices `01-05,12,13`) gated behind a trigger **absent from LEVEL01's normal flow** — likely a per-specific-stage mechanic. **Next bet:** early saves in **LEVEL02–05** (the stages that *have* their own PATH files) may load PATH at stage start. Otherwise low-value vs effort.
>
> **PATH SHELVED (2026-06-18) — confirmed not loaded at LEVEL02–05 start either.** Operator start-saves for LEVEL02/03/04/05 (the stages with dedicated `PATH02–05` files) show **no PATH content / no built filename** in RAM at stage start. ⇒ `PATH*.BIN` is **not loaded at level start, not enemy-triggered, and absent from normal early gameplay across 5 levels** — it's either a deep mid-level/scripted trigger or effectively unused. **Recommendation: shelved** (niche, overlay-gated, low mod-value vs effort). Re-open only if a specific in-game path-following section is identified.
>
> **PATH hunt EXHAUSTED (2026-06-18).** Checked PATH residency at the start of **12 stages** (`level02`–`level13`, incl. stages `0xd`/`9` which would use `PATH12`/`PATH13`, the largest files) + ~10 enemy encounters + level-load — **PATH content appears in RAM in NONE of them**. `PATH*.BIN` is conclusively **not loaded at any stage start, by any enemy, or in normal early gameplay**. It is dead/leftover data or a very deep scripted trigger. **Definitively shelved** — no further save-hunting warranted.

> [!check] **Update (2026-07-07) — collision grid-builder + arena scratch windows DECODED (P51 root fix).** The load-time grid/list builder `FUNC_800313A8` carves five per-sector scratch arrays below the hard-coded arena limit `[0x80082238]=0x801CC390` (sole writer `0x8003C2F4`); grown chunk-32 layouts let those writes poison live render nodes — the root cause of the entire Track-B P18–P50 replacement fault chain. Fixed by a 5-word EXE patch (`--p51-scratch-pack`), unlocking the full authored collision world (P52). Full RE `src_re/collision_grid_builder_800313a8.c`; [[Tier 3 - Native Terrain Path]] P51/P52.

> [!check] **Slide resolution decoded (2026-06-18) — B18 collision math complete.** `fcn.80025084` treats each wall as an oriented **segment** (normal `0x8009?fbc/fbe/fc0` + tangent `0x80090fb0/fb2/fb4`): `tangential = dot(delta, tangent) >>17` = position along the wall; collision = within `radius` perpendicular AND within the segment span tangentially; **resolution corrects the normal (stop) and preserves the tangential (slide)**; caller `fcn.8004d224` iterates over walls (re-test). ⇒ **all collision math decoded**: floor (`0x800322a0`), no-contact (`0x80035210`), wall+slide (`0x80025084`). Only `PATH*.BIN` remains (shelved).

**Severity:** ~~Medium~~ → **Low** (chunk-32 map + full resolver math incl. slide decoded; only the shelved PATH residual) · **Impact:** Medium · **Likelihood:** Low · **Confidence:** CONFIRMED · **Difficulty:** Medium–High

## Audit reconciliation (2026-06-22)
Frontmatter (`MEDIUM`) disagreed with the body (`Low` / "math complete") — reconciled to **LOW**. **TRUE STATUS = PARTIALLY ADDRESSED (near-closed).** Verified:
- **Chunk-32 byte-precise map** done.
- **Full floor + wall + slide resolver math decoded** (point-in-face `0x800322a0`, no-contact `0x80035210`, oriented-plane wall/slide `0x80025084`).
- **Floor live-edit-validated in RAM** — a sector-104 origin-Y edit moved Flik's footing ~1:1.
- **Collision source = LEVEL.RAW decompressed** (provenance via `fcn.8001a1dc`).
- **Wall/ledge `FUNC_80025084` runtime-confirmed** (fence scenario, 108 fires).
- **Generalized to LEVEL02** via GAP-0039.

Re-scoped to the single **SHELVED** residual: **`PATH*.BIN` nav-graph format UNDECODED** (loader scenario-gated / possibly-dead, exhaustively hunted across 12 stage starts + ~10 encounters) + minor resolver inner-loop TODOs (`0x800322a0` point-in-face inner loop, `0x800602b0`, multi-plane slide iteration, record tail `s0+0x18`). **Keep OPEN** (PATH unresolved), but read as "near-closed, one shelved residual."

## What is known (evidence)
- **Provenance unreconciled.** G29 §2.9 says the `0x800D0xxx` plane records are written *directly by the decompressor* [[FUNC_8001A1DC]]; G30 §18.1 / finding `f11` say the sector table [[MEM - Collision sector table 800A7E48|0x800a7e48]] is *built by a converter at* `0x80030xxx` ([[FUNC_80030F60]]). The relationship between `0x800F7xxx` (Pass-2 candidate region), `0x800D0xxx` (planes), and `0x800a7e48` (sector table) is a working hypothesis — ">1 pass writes overlapping dest regions," so the offline chunk-32 byte→record map is **not byte-precise** (~`0xb3c` drift).
- **Math residuals (Open Questions P2).** The no-contact branch `0x80035210`, the slide/re-test iteration, the point-in-face internals `0x800322a0`, and the remaining record tail bytes (`s0+0x18…`) are all TODO ([[FUNC_800345CC]]).
- **Wall/ledge + AI pathing.** `fcn.80025084` (oriented containment, Pass-5) was never exercised. `PAD/PATH01–05,12,13.BIN` (7 nav graphs, 16 B–1344 B) — **structure characterized offline (2026-06-18):** small **grid-coordinate u16 node records**, `0xffff`-terminated (e.g. `PATH02` = 2 nodes `(0,24,8)`/`(3,0,18)`; coords 0–144 = grid indices, not world units). The **precise node/adjacency format needs the loader** (`%s: path level` site) → DuckStation-gated, deferred.

## Why it matters
- A permanent collision edit (decompress chunk 32 → edit → recompress) needs an **exact** byte→record map; editing the wrong overlapping region would corrupt collision. AI/navigation behavior is entirely untouched.

## Dependencies
- **Depends on:** [[Blocker - Analysis methods have systematic blind spots|B19]] (overlapping-writer attribution needs a sharper method). **Related:** [[Blocker - LEVEL.RAW chunk inventory is mostly unidentified|B9]] · [[Blocker - Byte-exact disc reproduction is unproven|B4]]. **Related assumption:** A9.

## Research opportunity (direction only)
- Decompressing chunk 32 offline and content-matching the live `0x800D10E8` record would locate the exact plane bytes; reconciling the three regions into one pinned pipeline would make collision edits byte-precise; `PATH*.BIN` is decodable against the EXE's path loader (the `%s: path level` error site). (Direction only.)

## Evidence & sources
- vault: [[FUNC_80030F60]] · [[FUNC_800345CC]] · [[FUNC_8001A1DC]] · [[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]] · [[Finding - Collision on-disk source is chunk 32]] · [[G29 - Collision source]] · [[Open Questions]]
- corpus: `src_re_geometry/geometry_g29_collision_source_plan.md` (§2.9–2.13), `geometry_g30_terrain_render_source_plan.md` (§18.1)
- See also: [[Blockers]] · [[Risk Matrix]]
