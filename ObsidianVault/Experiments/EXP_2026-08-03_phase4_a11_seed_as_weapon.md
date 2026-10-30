---
kind: experiment
id: EXP_2026-08-03_phase4_a11_seed_as_weapon
name: Phase 4 A11 Seed as Weapon Bounded Exhaustion
status: complete
date: 2026-08-03
system: SYS_seed_as_weapon
row: A11_seed_as_weapon
---

# Phase 4 A11 Seed as Weapon Bounded Exhaustion

## Decision

**Status: `partial`, high-value row-specific work exhausted; move on.** No new
DuckStation run or Interpreter movie is required. The relevant retained capsule answers
the RAM and passive-flow questions, pristine resident ASM answers the writer/frontier
questions, and the Phase 2 no-press run remains the negative control.

## Evidence identity

The accepted capsule is external at
`a10-a11-v2-20260719/seed_as_enemy`. Its manifest SHA-256 is
`84b553e7a1712076b80ead43a452fd4638f2661e03adf419fc386a554f4a854a`.
The movie is `movies/seed_as_enemy.movie.json`, SHA-256
`6073e177ef57b485bec83c8afdd7b7a7650fd15ee589991fdbf9138b0f4ba915`; its state SHA-256
is `772d9e49507cc0565314fb1a6d3bfb54b79af2b3f405aa48712e7dd26bf2944b`.

The capsule is complete, has no error, contains 462 frame boundaries, 115,244,526
instructions, and 16,860,106 blocks. All 1,386 reconstructed RAM/VRAM/SPU hashes pass,
and its final full-machine fingerprint matches the independent control. It is legacy
CachedInterpreter evidence, so only retained frame-boundary state and passive block
flow are used. The committed preservation link is
`analysis/phase4_a10_a11_capsule_preservation.json`.

The native static scanner used the pinned PS-X executable
`REBUILD/files/SCUS_942.88`, SHA-256
`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

## Observation

| Event | Movie frame | State |
|---|---:|---|
| Pickup Square edge | 58 | Carry offset still zero |
| Carry attach | 61 | Seed `0x800A07D0`, carry mode `8` |
| Drop Square edge | 327 | Seed held in mode `12` |
| Detach | 329 | Carry offset and mode clear; seed becomes ballistic |
| Target contact | 349 | Actor `0x8009FD80`, id `9`, `+0x6C 0 -> -20`; HP stays `2` |
| Seed settles | 369 | Seed motion reaches zero and seed remains live |
| Target unlink | 389 | `+0x6C -1 -> 0`, HP becomes zero, live pointer removed, id remains `9` |

The negative no-press control in `analysis/phase2_final_action_pairs.json` keeps the
carry attached and produces no hit, knockback write, or target removal.

## C capsule reconstruction

`tools/phase4_a11_capsule.c` reconstructs all three retained domains, validates each
frame hash, follows the selected seed record and dynamic target record, and reduces the
passive block map. At impact it observes the carried/contact-kind-4 blocks
`0x80058DE4 -> 0x80058DF4 -> 0x80058E08 -> 0x80058E10`; the alternate dropped-object
block `0x8004B2AC` has zero hits.

The target reaction is not HP damage. HP remains `2` for all 20 reaction ticks while
`+0x6C` advances `-20, -19, ... -1`. The terminal unlink at frame `389` zeros HP as a
lifecycle effect. Because target `+0x62` is nonzero, terminal retirement preserves ID
`9`, matching a temporary KO that can later be reinstantiated by the shared enemy
lifecycle.

The seed is deflected at the contact. Its stored motion changes from
`(977,2560,306)` to `(979,271,994)`, decays to zero at frame `369`, and remains a live
id-`11` actor through frame `461`. The older Phase 2 phrase "landing frame" conflated
contact with final settling; the retained frame-boundary evidence separates them.

## C pristine-ASM investigation

`tools/phase4_a11_static.c` reads the PS-X EXE directly, verifies its SHA-256, decodes
both contact arms, and scans the resident payload for the `-20 -> actor+0x6C` pattern.
There are exactly two writers:

| Variant | Constant | Store | Gate |
|---|---:|---:|---|
| Alternate dropped-object | `0x8004B2CC` | `0x8004B2D0` | Collision subtype `+0x0A < 2` |
| Contact kind 4, executed | `0x80058E14` | `0x80058E18` | Contact `+0x27 == 4`, actor flag `0x40` clear |

Both share the actor prefilter: flags `0x20/0x80` clear and nonnegative existing
`+0x6C`. Neither arm writes actor HP at `+0x6E`. Both initialize reaction
`+0x54/+0x58 = 4096`, spawn the eight-object impact burst through `0x80057F44`, and
dispatch cue `17`. `src_re/seed_as_weapon_80058af8_8004abf4.c` records this reusable
law without pretending to be compiler-matching source.

## Phase 4 scorecard

| # | Closure metric | State | Bounded result |
|---|---|---|---|
| 1 | Original oracle | advanced | Natural pickup/drop/contact/settle/unlink plus retained no-press control |
| 2 | Complete frontier | advanced | Both resident writers, executed arm, guards, reaction, burst, and terminal interface decoded |
| 3 | Typed state | met | Carry selector/mode, seed position/motion/flags/HP, target flags/reaction/HP/permanence/live membership typed |
| 4 | Lifecycle | advanced | Pickup, carry, release, contact, seed settling, KO countdown, and unlink covered; later respawn deferred |
| 5 | Original interfaces | advanced | Input, carry release, contact walker, reaction fields, VFX/SFX, and actor retirement bound |
| 6 | Campaign breadth | deferred | Natural id-9 spider plus exact generic flag predicate; all enemy families not executed |
| 7 | Cross-system | advanced | Controller -> seed physics -> actor collision -> reaction/VFX/audio -> enemy lifecycle confirmed |
| 8 | Source closure | met | Semantic C, compiled capsule reducer, and compiled pristine-ASM scanner added |
| 9 | Durable evidence | advanced | Hash-pinned capsule/movie/state, committed preservation manifest, analysis artifact, Canon, and experiment |

## Exit boundary

The row stays `partial` because every enemy family, the alternate subtype arm, exact
per-model pose timing, and later respawn were not executed. Those are explicit breadth
or presentation residuals, not uncertainty about how the demonstrated mechanic works.
Request an Interpreter movie only if one of those named residuals becomes active.

