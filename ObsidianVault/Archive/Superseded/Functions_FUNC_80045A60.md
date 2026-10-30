---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80045A60.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80045A60.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80045A60_transition_finalizer_-_subsystem_reset.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80045A60 — transition finalizer / subsystem reset
type: function
address: 0x80045A60
confidence: CONFIRMED (flow); subsystem identity LIKELY
tags: [function, transition, finalizer, milestone6, gap-0035]
---
# FUNC_80045A60 — transition finalizer

> Called at the **end** of the transition orchestrator [[FUNC_8005222C]] (after the fade, before restoring `current_scene_id`). It clears a state flag bit and resets two higher-level subsystem managers. It is **not** player placement and **not** a camera reset. STATIC (`exe_read.py --disasm`).

| Field | Value |
|---|---|
| Bounds | `0x80045a60 … 0x80045aac` (19 instrs) |
| Role | transition **finalizer** (clear flag + subsystem reset) |
| Args | none used (builds a zeroed 4-byte local) |

## Decoded body
```
v0 = [gp+0x6e0] (= 0x80082478)
v0 &= 0xfffe ; [gp+0x6e0] = v0      ; clear bit0 of state flag 0x80082478
local[16..19] = 0                    ; zeroed 4-byte buffer
jal 0x8006dc90(&local)               ; subsystem manager A (→ 0x8006eda8)
jal 0x8006d8e8(9, 0, 0)              ; subsystem manager B (command 9)
return
```

## Role / classification
**Transition finalizer / subsystem reset.** Clears bit0 of the state flag `0x80082478`, then invokes two `0x8006dxxx` high-level subsystem managers (`0x8006dc90` with a zeroed buffer, `0x8006d8e8` with command `9,0,0`). Given the post-fade transition context, these are **LIKELY an audio/subsystem stop-or-reset** (the `0x8006dxxx` region is the high-level manager band). It does **NOT** write player position `0x800a6500/04/08`, camera, or `current_scene_id` (verified) — so it is a **completion/reset** step, not player relocation.

## Called by
- [[FUNC_8005222C]] @ `0x80052468` (no args; runs once the fade/resource loop completes).

## Confidence
- Control flow + flag clear `0x80082478` + the two subsystem calls — **CONFIRMED (decoded)**.
- "Audio/subsystem reset" identity of `0x8006dc90 / 0x8006d8e8` — **LIKELY** (region + call shape; not fully decoded).
- Not player placement / not camera — **CONFIRMED** (no such writes).

## Remaining unknowns
- Identity of `0x8006dc90` / `0x8006d8e8` (audio vs other manager) — decode if the transition's audio behavior matters.

## Related
[[FUNC_8005222C]] · [[Gameplay - Warp and Level Transition]] · `tools/exe_read.py`
