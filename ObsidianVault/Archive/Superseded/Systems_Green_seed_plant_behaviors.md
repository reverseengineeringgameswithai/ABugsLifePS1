---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Green seed plant behaviors.md
aliases:
  - "Green seed plant behaviors"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Green seed plant behaviors.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Green_seed_plant_behaviors.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Green seed plant behaviors
type: system
updated: 2026-07-03
confidence: CONFIRMED (deterministic movie; slot read-watch + writer-PC attribution)
tags: [system, seed, plant, green, platform, climbing, collision, gameplay]
---

# Green seed plant behaviors — solved (platforms & climbers)

> Decoded 2026-07-03 from the operator's **`green_seed_levels.movie.json`** (windows: 121531–121896
> small leaf · 122143–122547 taller leaf · 122809–123381 three-leaf climber · 123427–124032 rose).
> Companion to [[Brown seed plant behaviors]] / [[Blue seed plant behaviors]].
> RE source: `src_re/green_seed_plants.c`.

## Crack + spawns
Identical **X-butt-slam crack** (X pressed 38–60f before every spawn). Spawns matched the `(green,count)` matrix exactly: **type 4** (small leaf) → **type 10** (taller leaf) → **type 9** (three-leaf climber) → **type 1** (rose climber). Notably **type 1 loaded and grew fine here** — the "type 1 not in the model set" caveat is LEVEL01-specific, not global.

## The mechanism — passive COLLISION, not dispatcher verbs
All four types route to the **passive handler `FUNC_8005CCE8`**. A live read-watch on the active plant slot during a hang shows this handler **reading the slot every frame** (PCs `0x8005cd8c…0x8005d220`, fields `+0x0/+0x2/+0x4/+0x6/+0x14/+0x26/+0x2e`), testing Flik against the plant's geometry and feeding the result into the **standard player collision path**:
- standing on a leaf top and hanging on a stem both show the **ordinary grounded Y-commit writers** (`0x80036384/0x80036cf0/0x80036d58` — the movement-integrator family) and the ordinary **landing** writers (`0x80035e40/0x80035fe0`) at attach;
- there is **no special vy writer** for green (unlike the propeller/cannon).

⇒ **a green plant is a dynamic floor/grab surface injected into normal collision.** (Relevant to Tier-3: this is the native precedent for runtime-injected collision surfaces.)

## Climbing law — a ladder of jumps, not a climb mode
The "climb" is **jump-and-grab**: Flik jumps (normal impulse, ordinary gravity decay via `0x80048d90`), and on contact with the stem he **grabs — treated as grounded** (vy held 0, Y frozen ~27+ frames, gravity suspended by the normal integrator), then jumps again from the hang point. Measured tops: three-leaf **~24.9k**, rose **~38.6k** above ground.

## Platforms, heights, lifetimes
- Small leaf (4): top ~**2.8k** (a brief 9-frame stand captured).
- Taller leaf (10): ~**4.3k** reached at jump apex only — as the operator noted, it isn't reachable without a mushroom boost, so top-standing wasn't exercised. **No redo needed**: the spawn/geometry are verified and the stand mechanism is proven identical via G1 + the climbers' hangs (same collision path).
- **Lifetimes** (standard wilt chain, [[Blue seed plant behaviors]] §expiry): type 4 ~348f · type 10 ~381f · **type 9 ~543f · type 1 ~555f** — climbers persist noticeably longer than platforms.

## Residuals
- The plant geometry law inside `FUNC_8005CCE8` (stem radius/leaf disc extents per type — the slot fields it reads are pinned, the shape math isn't decompiled).
- Whether grabbing mid-stem is quantized (leaf rungs) or continuous.
- Purple/yellow lanes (same movie method).

## Related
[[Brown seed plant behaviors]] · [[Blue seed plant behaviors]] · [[Seed plant output binding]] · [[Tier 3 - Custom Level Engine]] (native dynamic-collision precedent) · `src_re/green_seed_plants.c`
