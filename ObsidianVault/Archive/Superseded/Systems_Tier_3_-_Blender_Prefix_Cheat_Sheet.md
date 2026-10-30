---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Tier 3 - Blender Prefix Cheat Sheet.md
aliases:
  - "Tier 3 - Blender Prefix Cheat Sheet"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Tier 3 - Blender Prefix Cheat Sheet.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Tier_3_-_Blender_Prefix_Cheat_Sheet.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Tier 3 - Blender Prefix Cheat Sheet
type: reference
updated: 2026-07-03
tags: [reference, tier3, blender, cheatsheet, prefixes, authoring]
---

# Tier-3 Blender cheat sheet — object naming prefixes

> Quick reference for authoring a Tier-3 custom level in Blender. Name-prefix matching is
> **case-insensitive** and ignores Blender's `.001` suffixes. Build with the usual one-button
> pipeline: `tools/tier3_build_gui.sh` (or `tools/tier3_build_level.sh LEVEL.blend [scale]`).

## Geometry (MESH objects)
| What                      | How                                              | Notes                                                                              |
| ------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------- |
| **Floor / ramps / walls** | any mesh — no prefix needed                      | slope-classified: near-flat = walkable floor; steep (>~45°) = wall + auto keep-out |
| **Invisible blocker**     | mesh named `blocker*` / `collider*`              | XZ keep-out AABB from its bounds; not drawn                                        |
| Textures | material custom props `abl_texpage`+`abl_clut`+`abl_color`+`abl_uv` | **known-good dirt recipe** (mylevel.blend): `abl_color 545292416`, `abl_texpage 1632`, `abl_clut 16380` ground / `16370` darker wall, `abl_uv [0,192,63,63]` / `[128,192,63,63]`; meshes UV-mapped 0..1 per face. No material = flat grey |

## Markers (EMPTY objects)
| Prefix | Lane | Extra data |
|---|---|---|
| `spawn` | Flik's spawn (one) | keep near the Blender world origin |
| `pickup*` | generic collectible volume | radius = empty display size × scale (min 2000) |
| `exit*` / `goal*` | level goal volume | radius = display size × scale (min 3000) |
| `grain*`, `token*`, `telescope*`, `flikF/L/I/K*` | **native type-0x3f pickups** | kind by name prefix or `abl_kind` custom prop (full table: NATIVE_KIND in `tools/tier3_blender_export.py`) |
| **berries** — see the table below | berry pickups | longest prefix wins; bare `berry*` = green/homing |
| **`prop*`** | **pass-1 prop** (visual decor) | custom prop **`abl_payload`** = the model — use the **`disk_payload`** value from `build/pass1_palette/palette.json` (browse the thumbnails to pick) |
| **`enemy_<name>*`** | **live enemy** (chunk-31 actor) | names: `enemy_spider` · `enemy_worm` · `enemy_pill` · `enemy_bee` · `enemy_mosquito` (LEVEL01-resident only), or custom prop `abl_type_word`. Behavior params auto-copied from a donor; the permanent-kill quota auto-derives from your enemy count |
| **`dot_00`, `dot_01`, …** | **Dot's guide route** | sorted by name; she advances a leg only while Flik is within ~38k units, waits forever otherwise; the route **tail-pads** so she **parks at your last point**; **her actor is auto-added** at `dot_00` — just place the empties |

## Berry pickup names (type-0x3f kinds)
| Empty name prefix | Berry | Kind | Effect (decoded) |
|---|---|---|---|
| `redberry*` | red | `0x20` | ⚠️ **not placeable on the LEVEL01 host** (no native template to clone — red is Flik's default anyway) |
| `greenberry*` / `homingberry*` / `berry*` | green / homing | `0x21` | locks the nearest valid enemy (RCG-031) |
| `goldberry*` | gold | `0x22` | **permanent kills** (decrements the enemy quota) |
| `blueberry*` / `superberry*` | blue / super | `0x23` | stronger straight throw |
| `purpleberry*` / `megaberry*` / `megahomingberry*` | purple / **mega homing** | `0x24` | homing + strongest (not permanent) |

Or set the exact kind yourself with an `abl_kind` custom property (e.g. `0x24`) on any Empty — it always wins over the name.

## Rules of thumb
- **Scale**: 1 Blender unit = 1000 ABL world units by default (override: 2nd arg / scene prop `abl_scale`). Blender Z-up → ABL −Y-up is handled by the exporter.
- **Props have no collision** — solidity comes from your geometry/blockers (native design: visuals ≠ collision).
- **Dot route Y** must be terrain-plausible (she flies straight at each waypoint — no floor snap) and legs shouldn't be ultra-short.
- **Enemies**: only LEVEL01-resident species spawn correctly (models must be loaded on the host level).
- `abl_type` custom prop containing "visual" = Blender-only helper, never exported.

## Where things come from (deep dives)
[[Tier 3 - Blender Pipeline Plan]] · [[Prop and foliage catalog]] (props/payloads) · [[Dot guide NPC]] (route law) · [[Enemy spawn architecture]] (actors/quota) · [[Level manifest round-trip]] (native LEVEL01 editing path)

## Prototype
`build/ailevel.blend` (generator: `tools/abl_blender/make_ailevel_prototype.py`, disc `build/ABL_AILEVEL.cue`) — the full-fledged all-items gauntlet (~115k units, native-dirt textured): start plaza (grass-stalk rim, clover/stones/acorns) → main field (spider + bee, grain trail) → canyon (textured walls, worm ambush + gold-berry bait) → 4-platform hop (mosquito overhead, blue/mega berries, per-platform grain) → raised terrace (tokens, telescope, green berry, pill-bug guard) → finish hill (FLIK letters, exit) — 16-leg Dot route end-to-end. Cold-boot verified: 6 actors live, quota 5, dynamic grain HUD x/12.
