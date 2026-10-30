---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Enemy relocation method.md
aliases:
  - "Enemy relocation method"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Enemy relocation method.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Enemy_relocation_method.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Enemy relocation method
type: system
tags: [enemy, spawn, relocation, method, playbook]
updated: 2026-06-19
---

# Enemy relocation method

> How to figure out how to move ANY ABL enemy, one at a time. Proven on the bee (`bee.sav`). Tool: `tools/enemy_mover.py`. Enemy relocation is **type-dependent** — there is no single edit that moves every enemy; you must classify each one first.

## TL;DR — enemies are not a generic spawn table
Enemy actors are driven by a **hardcoded per-level dispatcher** (e.g. bee dispatcher/state-machine `0x8004ea8c`, body `0x8004ebec+`): each enemy has a **fixed actor slot** (bee = `0x80095358`, hardcoded into the dispatcher) and a per-enemy **state machine + active flag** (bee state `0x80090bec`, flag `0x80090bee` bit0). There is no editable "enemy at XYZ" record like [[Finding - type-0x3f pickups]]; placement is in code/data depending on enemy type.

## The 4-step method (`tools/enemy_mover.py <save> <bx0> <by0> <bx1> <by1>`)

1. **IDENTIFY the runtime render-position** — crash-robust **force-and-frame-diff binary search**. Capture a baseline; force candidate world-position triplets (scanned from `0x80090000..0x800c0000`, near-camera) off-screen 8 frames; the address whose force makes the enemy **vanish from its screen bbox** is the render position. Copies / AI buffers do NOT move the render, so they're filtered out automatically. (Bee → `0x80095358`; the same-valued `0x8009ec50`/`0x800b0220` are dead buffers — this is the trap that wrecks naive poking.)
2. **CLASSIFY** — teleport Flik far (`0x800a6500`), re-read the render-pos:
   - tracks Flik ⇒ **CHASER** (player-relative): **no editable location**. Knobs are code-only (chase offset/radius immediates, activation timing).
   - independent ⇒ **STATIONARY / PATROL**: relocatable by editing its position/path record on disc (the proven [[LEVEL.DAT object pipeline]] / pickup / seed / rec1 path-mover technique → [[enemy-and-object-movers]]).
3. **TRACE the writer** — `accessLog` write-watch the render-pos → writer PC; disassemble; follow operands:
   - reads `0x800a6500/6504` (Flik) ⇒ chaser (confirmed for bee: lerp `0x8004e8a4` toward target set by AI `0x8004e320` from Flik±sine `0x80074970`).
   - reads a CD-loaded data buffer ⇒ data-driven, editable → find the file+offset (cf. [[LEVEL.RAW codec]]).
   - computed from angle/radius immediates ⇒ procedural (bee spawn-init `0x8004da40`) → patch code.
4. **RELOCATE + VERIFY** — stationary: edit record + rebuild ([[Finding - File loading is by-name]] makes it layout-safe), reload + frame-diff to confirm. Chaser/procedural: patch the EXE immediate(s); verify the spawn/offset moved.

## Worked example: the bee (CHASER — not relocatable)
Render-pos `0x80095358`; CLASSIFY = CHASER (target = Flik.pos ± sine); spawn is **scripted+procedural** (state machine sequenced by counter `0x800824dc` + flag `0x80082388`; spawn-init `0x8004da40` computes position from a sine-table angle/radius, writes globals `0x80090bc4/bd0/bd4`). Conclusion: **no XYZ to edit** — the bee is defined entirely relative to the player; you can live-force it (`bee_moved.png`) or patch its offset/spawn code, but it always homes on Flik. Full detail: memory `enemy-bee-is-flik-chaser`.

## To do the next enemy
Give a save with the target enemy clearly on screen + its screen bbox → run `enemy_mover.py` → it prints render-pos, chaser/stationary verdict, and the writer PC. Then follow step 4 for that type.

## Related
[[enemy-and-object-movers]] · [[LEVEL.DAT object pipeline]] · [[Systems]] · [[API - accessLog]] · [[API - visual diff]] · [[API - execTrace]]
