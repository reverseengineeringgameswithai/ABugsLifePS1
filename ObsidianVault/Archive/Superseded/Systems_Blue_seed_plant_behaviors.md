---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Blue seed plant behaviors.md
aliases:
  - "Blue seed plant behaviors"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

> [!warning] CORRECTED 2026-08-01
> The tier→flag-bit table in this note is **wrong on two of three bits**.
> `0x02` is a transient ~2-frame per-action flag (set by the damage handler `0x8004A7B0`,
> cleared at `0x80048600`), **not** invincibility. `0x08` is the **checkpoint** marker set by
> `checkpoint_save`, **not** the bubble shield. Only `0x20` = super jump survives.
> **Invincibility and the bubble shield use the slot `0x800A657E`, not a flag bit** —
> `0x800588D0` writes +400 and `0x800589A8` writes −3. An alias-aware census of all 26
> writers of `0x800A6590` finds **none** in `0x8005C000–0x8005D000`, so the type-7/type-6
> plant handlers never touch the flags word; they spawn a contact object and *collecting it*
> grants the power. See [[SYS_player_power_slot]].


- Original path: `ObsidianVault/Systems/Blue seed plant behaviors.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Blue_seed_plant_behaviors.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blue seed plant behaviors
type: system
updated: 2026-07-03
confidence: CONFIRMED (deterministic movie, all four tiers; flags/impulses live-measured)
tags: [system, seed, plant, blue, invincibility, health, bubble-shield, super-jump, gameplay]
---

# Blue seed plant behaviors — solved (+ plant expiry)

> Decoded 2026-07-03 from the operator's **`blue_seed_levels.movie.json`** (windows: 110581–111234
> invincibility · 111470–112184 health · 112491–113272 bubble shield · 113414–114254 super jump).
> Companion to [[Brown seed plant behaviors]]. RE source: `src_re/blue_seed_plants.c`.

## Crack-open — identical to brown (movie-verified)
X pressed 40–60 frames before every spawn = the **butt-slam crack** ([[Brown seed plant behaviors]] chain: `0x8004af80` → seed`+0x6c` → `FUNC_8005BDBC`). Spawned slots match the `(blue,count)` table rows exactly: type **7/0x2000 → 7/0x3000 → 6/0x0000 → 7/0x4000**.

## What each tier does for Flik — the power-up status word `0x800A6590`
The type-7 handler (`0x8005C744`) applies **direct effects** as bits in the player **power-up status word `0x800A6590`** (u32; per-frame maintainers `0x80048564/0x80054cb8/0x80047aa4/0x80049640/0x80054e94`):

| Tier | Effect | Observed |
|---|---|---|
| 1 | **Invincibility** | **bit `0x02`** set; countdown packed in the word's upper bytes (0xFF pulse decaying); active ~105 frames in the movie |
| 2 | **Health refill** | restores health (retail: full). ⚠️ the TRUE health store was **not** isolated — `0x800a7e28` **and** `0x800a7e2a` are both HUD leaf-pulse **animation** fields (sole writers `0x8005266c`/`0x80052680`/`0x800526dc`); the real health variable stays a named residual (→ RCG-021) |
| 3 | **Bubble shield** | handler `0x8005C6F0` spawns the shield contact object (ctor `0x1F`); **bit `0x08`** while shielded; the three 0xFF upper-byte pulses during the window are LIKELY the absorbed-hit i-frames (manual: 3 hits) |
| 4 | **Super jump** | **bit `0x20`**; jump impulse **vy = −3520 vs normal −2816 (+25%)**, seen on 3 jumps |

## Plant expiry — how a plant "disappears" (all lanes)
Slot lifecycle in `slot+0x2e` (low byte; the `0x20xx` high byte is the render family, maintained by `0x800216fc/0x800217bc/0x80021c00`):

```
spawn 0x05 (growing) → 0x07 (MATURE; bit 0x4 = dispatcher-active, gates the handlers)
      → |= 0x40 WILT (ONE-SHOT setter 0x8005cecc) → ~100 f wilt animation → slot freed
```
Slot init writer = `0x8005bf40`. The slot carries **age accumulators** (`+0x1a` family, ~+52/frame) read by the expiry decision. **Measured lifetimes** (spawn → freed): brown mushroom ~327f · propeller ~444f · dandelion ~477f · blue invincibility ~633f. Per-type lifetime constants remain a residual (mechanism/wilt-bit/setter pinned). This answers the earlier open question in [[Brown seed plant behaviors]].

## Residuals
- The TRUE health variable + the heal write site (the movie's heal ran through it, but both known "health" addresses are HUD animation) — the sharpest remaining RCG-021 item.
- Invincibility/shield countdown law (tick rate, packed-byte layout in `0x800A6590+2/+3`).
- Per-type plant lifetime constants; the shield 3-hit counter location.
- Green/purple/yellow lanes' fine detail (same movie method applies).

## Related
[[Brown seed plant behaviors]] · [[Seed plant output binding]] · [[Seed planting system]] · [[Retail Gameplay Completeness Gap Audit]] RCG-004/RCG-021 · `src_re/blue_seed_plants.c`
