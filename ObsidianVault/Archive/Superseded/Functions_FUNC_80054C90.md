---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80054C90.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80054C90.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80054C90_checkpoint-save_(live_position_-_respawn_anchor).md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80054C90 — checkpoint-save (live position → respawn anchor)
type: function
address: 0x80054C90
confidence: CONFIRMED (flow); checkpoint-trigger semantics LIKELY
tags: [function, player, spawn, checkpoint, milestone6, gap-0035]
---
# FUNC_80054C90 — checkpoint-save (snapshots live pos → respawn anchor)

> Per-frame gameplay routine that, when a distance test passes, **copies the live player position into the respawn anchor** `0x800a6550/54/58` and sets a checkpoint flag. It is the *save* half of the checkpoint/respawn pair ([[Gameplay - Player Spawn and Placement]]); the *restore* half is [[FUNC_8005B134]]'s tail. STATIC (`exe_read.py --disasm`).

| Field | Value |
|---|---|
| Bounds | `0x80054c90 … ~0x80054ea4` |
| Role | checkpoint-save (live position → respawn anchor) |
| Caller | `0x8004f020` — gameplay state machine `fcn.8004ecd4` (per frame) |

## Decoded behaviour
- Iterates the **64-entry × 0x84** object array (the seed/checkpoint records, base ~`0x800a0014`): `t0 = 0..63`, pointers `+= 0x84` per step.
- Each step does a **distance test** (`mult v0,v0; … slt v0,v0,v1; bne → skip` @ `0x80054e14..e24`).
- When the test passes, **snapshots the live player position into the anchor**:
```
v1,a0,a1 = [0x800a6500/04/08]            ; live player X/Y/Z
[0x800a6550] = v1 ; [0x800a6554] = a0 ; [0x800a6558] = a1   ; anchor (writers 0x80054e70/e78/e80)
[0x800a6578] = [0x800a6520]              ; (sh, aux field)
[0x800a6590] |= 0x8                      ; set checkpoint flag bit3
```

## Role / classification
**Checkpoint / respawn-anchor save.** It does **not** move the player (it reads live pos, writes the anchor). The anchor it writes is exactly what [[FUNC_8005B134]]'s respawn tail later restores into the live position. The 64×0x84 array + per-record distance gate ⇒ "save the current position as the respawn point when near a checkpoint trigger" (the precise trigger record is LIKELY a seed/checkpoint object — not fully pinned).

## Globals touched
- **Reads** live player pos `0x800a6500/04/08`. **Writes** respawn anchor `0x800a6550/54/58`, `0x800a6578`, flag `0x800a6590` (bit3). See [[MEM - Player state 800A6500]].

## Confidence
- Live→anchor copy + flag set + per-frame caller — **CONFIRMED (decoded)**.
- "Checkpoint near a trigger record" semantics — **LIKELY** (array+distance gate; exact trigger TBD).

## Related
[[Gameplay - Player Spawn and Placement]] · [[FUNC_8005B134]] · [[FUNC_8003633C]] · [[MEM - Player state 800A6500]] · `tools/exe_read.py`
