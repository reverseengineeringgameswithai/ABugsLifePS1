---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Prop and foliage catalog.md
aliases:
  - "Prop and foliage catalog"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Prop and foliage catalog.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Prop_and_foliage_catalog.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Prop and foliage catalog (Tier-3 leverage)
type: system
updated: 2026-07-03
confidence: SURVEY (13 fixtures) + one NEW live-proven lever (pass-1 payload swap)
tags: [system, props, foliage, decor, pass1, pass3, terrain, tier3, blender, hitbox]
---

# Prop & foliage catalog — 13 fixtures surveyed + the payload-swap lever

> From the operator's 13 fresh save states (2026-07-03). Per fixture: visual (screenshots in
> `Assets/prop_catalog/`), data class, hitbox verdict, animation notes — and the **Tier-3/Blender
> leverage**, including a **NEW live-proven lever: pass-1 payload swapping** (re-skin any pass-1
> prop position with any other prop's model). RE: `src_re/prop_decor_catalog.c`.

## The headline lever (NEW, live-proven)
**Pass-1 records = `(X,Y,Z, payload-ptr)` and BOTH halves are editable.** Position edits/deletes were
already proven ([[Pass-1 scenery edit]]); today: **swapped two records' payload pointers live → the
acorn in front of Flik re-rendered as a rolled-leaf tube** (9% frame change; `swap_before/after.jpg`).
The renderer consumes the pointer per frame. On disc, `+0x10` is a baked file-offset relocation site →
the existing `dat_reloc` machinery is the write path. ⇒ **pass-1 is a general prop-placement system:
choose position AND model per record.**

## Catalog

| Fixture | Visual | Class | Hitbox (probe) | Notes |
|---|---|---|---|---|
| `mushrooms` | pale mushroom cluster on walkable dirt (`mushrooms.jpg`) | **terrain-baked** (no pass-1/3/chunk-31 record nearby) | walk mostly free (15–18k) — decorative, no blocking | the *plant* trampoline mushroom is a different thing (seed plant type 5) |
| `foliage` | the **level-boundary grass-blade wall** + dirt cliff (`foliage.jpg`) | boundary rim (terrain/chunk-35 family; one pass-1 stalk #407 nearby) | walk STOPS ~9–11k = **boundary collision planes** | this is the "foliage boundary" — visual rim + separate planes |
| `wooden_fence` | twig-fence line on a mound (`wooden_fence.jpg`) | **terrain-baked** | blocked ~10k — planes along the fence line | enclosure boundary |
| `big_berry` | giant berry prop | **pass-1 #117** | HARD block (walk 2.7k) — dense local planes | solid decor |
| `acorn` | acorns on the trail (`acorn.jpg`) | **pass-1 #214/#209** | free | the payload-swap POC subject |
| `clover, flowers` | tall clover + flowers (`clover_flowers.jpg`) | **pass-1 #420** area | free | canopy decor |
| `weird_structure` | (`weird_structure.jpg`) | **pass-3 #139/#136** | free-ish | pass-3 = cull-anchored decor ([[Finding - Pass-3 decor records decoded (cull anchor + suppression)]]) |
| `huge_stone` | large stone (`huge_stone.jpg`) | **pass-1 #431** | area-dependent | |
| `offering_stone_and_ramp` | stone + walkable ramp (`offering_stone_and_ramp.jpg`) | **terrain-baked** (ramp = terrain geometry + sector slope collision) | ramp walkable | ramps live in the collision sector data, not props |
| `leaf` | ground leaf (`leaf.jpg`) | terrain-baked (a pass-1 #79 15k off) | free | |
| `thornplant` | thorn plant (`thornplant.jpg`) | **terrain-baked** | free (35–49k walks) | visual hazard? no block in probe |
| `unknown_name_barrier` | barrier structure (`unknown_name_barrier.jpg`) | **terrain-baked** | partial (25–30k) | |
| `tree_complex_holding_swings` | fallen branch + big leaves + hanging swings (`tree_complex_holding_swings.jpg`) | **pass-1 #87/#44** (branch/leaf parts) + swings | branch overhead — no block at ground | **swings: no moving actor found while idle** → they animate when ridden (player-state driven) or GPU-side; `on_swing.sav` exists for a deeper dig (residual) |

## Hitboxes — the architectural verdict
**No prop carries its own hitbox.** Solidity comes from the **chunk-32 sector collision planes**
placed alongside the visuals (the project's visual≠collision headline, reconfirmed here: big_berry/
fence/boundary block; mushrooms/thorn/leaf walk free). Empirical probes: 90-frame directional walks.

## Tier-3 / Blender leverage
1. **Pass-1 prop library (READY)**: author prop positions in Blender → write pass-1 records
   (file-scale = world/32; payload ptr selects the MODEL — swap-proven). LEVEL01 carries 500+
   records = a large reusable library (acorns, leaf tubes, berries, stones, branch pieces, clover…).
   Next step: dump the payload→model gallery (render/screenshot each payload) to give Blender a
   pickable palette.
2. **Pass-3 decor**: same record shape, cull-anchored — usable for skyline/far decor; suppression
   levers already exist (HRE-001).
3. **Terrain-baked decor (fence lines, mushroom clusters, thorn, boundary grass)**: NOT individually
   placeable today — for custom levels either keep native terrain as backdrop or suppress it; recreate
   such props as Tier-3 textured quads (grass-blade rim is a good candidate — simple repeating quads).
4. **Hitboxes**: decoupled by design — Tier-3 already owns collision (`tier3_collision` AABB walls);
   place visual props freely and add walls only where solidity is wanted. This matches the native
   architecture exactly.
5. **Boundaries**: the native "foliage boundary" = rim visuals + boundary planes; the Tier-3
   equivalent = death-plane/walls (already built) + a rim visual (quads or kept-native backdrop).

## Residuals — 2026-07-03 closeout pass
- ~~Payload→model catalog~~ **✅ DUMPED** — `tools/dump_pass1_palette.py` → `build/pass1_palette/` (**484 payloads, each content-UNIQUE** = per-instance baked mesh blobs; the thumbnails are the pick/dedupe mechanism; multiple records can share one blob per the swap POC).
- ~~Swing animation driver~~ **✅ RESOLVED** (`on_swing.sav`): swinging = **player MODE 5** (`0x800a6580`; 0 on ground) — Flik is pendulum-driven **through the standard integrator** (sole X writer `0x80036d20`; ~18k Z amplitude). The swing prop is passive decor; attach = contact → mode 5. Residual: the pendulum pivot/params source.
- ~~Pass-2 layout~~ **✅ RESOLVED**: `G_PASS2_BASE_PTR` (→`datbase+0x3ae8`) marks pass-2's **end sentinel** — pass-2 is the **mesh/scale registration pass** (payload ptrs + `0x8000` fixed-point scale halfwords; parser chain `[R+0x10]/[s4+0x18]`, output `@0x80091210`), NOT a placement table (hence no per-prop records). Pass-3 placements begin at `+0x3aec` (the survey's base was correct).
- Terrain-baked prop geometry offsets inside DAT payloads — still deferred (Tier-3 recreates those looks as quads).

## Related
[[Pass-1 scenery edit]] · [[Finding - Pass-3 decor records decoded (cull anchor + suppression)]] · [[Tier 3 - Custom Level Engine]] · [[Blender-first ABL level editor]] · [[Retail Gameplay Completeness Gap Audit]] RCG-017/018 · `src_re/prop_decor_catalog.c`
