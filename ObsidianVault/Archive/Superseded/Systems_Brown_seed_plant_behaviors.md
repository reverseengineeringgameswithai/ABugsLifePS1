---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Brown seed plant behaviors.md
aliases:
  - "Brown seed plant behaviors"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Brown seed plant behaviors.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Brown_seed_plant_behaviors.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Brown seed plant behaviors
type: system
updated: 2026-07-03
confidence: CONFIRMED (deterministic movie, all four tiers; live-measured physics)
tags: [system, seed, plant, brown, trampoline, propeller, dandelion, cannon, gameplay]
---

# Brown seed plant behaviors — completely solved

> Decoded 2026-07-03 from the operator's **`brown_seed_levels.movie.json`** (one window per token
> tier: 47500–47923 mushroom · 48143–48615 propeller · 48880–49400 dandelion · 49415–49798 cannon).
> Extends [[Seed plant output binding]] (which mapped *which* plant grows) with the three missing
> pieces: **how the seed cracks open, what each plant does for Flik, and the carry/discard
> lifecycle**. RE source: `src_re/brown_seed_plants.c`.

## 1. How the seed is cracked open (same chain at all four tiers)
**Input**: Flik **jumps (X) and butt-slams onto the seed** (X pressed ~50 frames before every crack in the movie). The chain:
1. **Slam contact** → PC `0x8004af80` writes `0x00010000` into **`seed_actor+0x6c`** — the one-shot crack trigger (fired at 47577/48151/48903/49415, once per tier).
2. The actor manager (`0x8004d494`) steps `+0x6c` ~10 times over ~20 frames = the **crack-open animation**; seed flags `+0x5c` drop the pickup bit (`0x4031 → 0x31`).
3. ~20 frames after the slam, the plant spawner `FUNC_8005BDBC` allocates a **plant slot** (20×0x30 @`0x80090BF0`, `slot+0x20` backlinks the seed) with the type from the `(color,count)` table `0x8007A448`.

Observed spawns (brown counts 1→4): slot10 **type 5** @47598 · slot11 **type 3** @48174 · slot12 **type 8** @48924 · slot13 **type 2** @49437 — exactly the documented matrix. **The seed actor is reusable** — the same actor (`0x800a0854`) was carried, cracked, and regenerated across all four windows.

## 2. What each tier does for Flik (live-measured physics)
Flik vy = `0x800A6530` (−Y up; gravity = `0x80048d90`, +0x100/physics-tick).

| Tier | Plant (type/handler) | Mechanism | Measured |
|---|---|---|---|
| 1 | **Mushroom trampoline** (5, `0x8005C58C`) | On landing on the cap, handler (@`0x8005c600`) sets the bounce: **vy ≈ −3328** | rise ~**28k** units; retriggers every landing (infinite bounce) |
| 2 | **Propeller plant** (3, `0x8005C258`) | Handler writes vy **directly every tick** (@`0x8005c428/58`) with an **accelerating ramp** (−0x1C0, then −0x100 steeper/tick) | sustained powered lift, ~**44k** |
| 3 | **Dandelion** (8, `0x8005C818`) | One **attach** write (@`0x8005c84c`) hooks Flik to the tuft → **carried/glide** | gentle, ~**14.6k** |
| 4 | **Cannon plant** (2, `0x8005C110`) | Two phases: **seated** — vy **pinned to 0** by `0x80048690` every tick (Flik in the barrel); **fire** — one impulse **vy = −7680**, then ballistic | rise ~**120k** (≈4× the trampoline) |

## 3. Carry + discard (the seed lifecycle)
- **Pick up**: walking onto the seed → flags `0x4031 → 0x4039` (transient) → **`0x4071`: bit `0x40` = CARRIED**. While carried, the seed is **position-locked to Flik** at a fixed offset (~(−1092, +4096, −46)).
- **Discard**: on release the carry bit clears (`0x4071 → 0x4031`) and the seed is **placed at rest at the drop point instantly** — its position is constant from the release frame (verified at 3 releases: 48072/48705/48825; Flik's distance grows while the seed stays put). **No toss arc, no bounce, anim field `+0x44` stays 0** — the visible "toss" is *Flik's* put-down animation; the seed itself has no discard physics and is immediately crackable again where dropped.

## Notes / residuals
- The handler internals for the *other* lanes (blue direct-effects, purple/type-6 berry spawns, shooters) were already mapped at the dispatch level in [[Seed plant output binding]]; this note's crack/carry/discard chain applies to all crackable seeds (the chain is seed-side, not lane-side) — only the per-tier physics here are brown-specific.
- The slam-contact fn containing `0x8004af80` (which detects Flik's butt-slam over the seed) hasn't been boundary-mapped; the trigger write is pinned.
- ~~Plant slot lifetime/expiry~~ — **SOLVED 2026-07-03** → [[Blue seed plant behaviors]] §Plant expiry: slot `+0x2e` lifecycle `0x05 grow → 0x07 mature → |0x40 WILT (one-shot setter `0x8005cecc`) → ~100f wilt anim → slot freed`; age accumulators `+0x1a` (~+52/frame); measured lifetimes mushroom ~327f / propeller ~444f / dandelion ~477f. Per-type lifetime constants residual.

## Related
[[Seed plant output binding]] · [[Seed planting system]] · [[Retail Gameplay Completeness Gap Audit]] RCG-004 · `src_re/brown_seed_plants.c` · `src_re/plant_spawn_8005bdbc.c`
