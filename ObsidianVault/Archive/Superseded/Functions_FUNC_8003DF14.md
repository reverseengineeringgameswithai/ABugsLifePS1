---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8003DF14.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8003DF14.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8003DF14_modulo-offset_helper_(scroll-background_position).md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8003DF14 — modulo/offset helper (scroll/background position)
type: function
address: 0x8003DF14
confidence: CONFIRMED (math); LIKELY (scroll-offset purpose)
tags: [function, transition, helper, milestone6, gap-0035]
---
# FUNC_8003DF14 — wrap/offset helper (`x mod table[flag]`)

> A small leaf math helper, **not** a resource loader or scene selector. It computes a wrapped offset `a0 mod table[flag]` and stores it (plus `a1`) to two gp globals. Called by the transition orchestrator [[FUNC_8005222C]] `(0, −8)` to reset a scroll/background offset during the fade. STATIC (`exe_read.py --disasm`).

| Field | Value |
|---|---|
| Bounds | `0x8003df14 … 0x8003df98` (33 instrs, leaf — no callees) |
| Role | wrap/offset setter (`a0 mod divisor` → gp globals) |
| Args | `a0` = value, `a1` = secondary offset (orchestrator passes `0, −8`) |

## Decoded body
```
v0 = [gp+0x5c8]                       ; select flag
divisor = (v0==0) ? [0x800771b0] : [0x800771dc]   ; table in the background/recolor region
r = a0 % divisor                      ; (positive modulo; div-by-0 / overflow traps present)
[gp+0x3c0] (= 0x80082158) = r
[gp+0x3c4] (= 0x8008215c) = a1
```

## Role / classification
**Offset/wrap helper — NOT a loader, stage selector, or transition driver.** The divisor tables `0x800771b0/0x800771dc` sit in the background/sky-recolor region (cf. sky recolor levers `0x800771bc/c0/c4`), and the outputs `0x80082158/0x8008215c` are LIKELY **scroll/parallax/background-position** state. In the warp path it re-initialises that offset (to `0` / `−8`) as part of the screen transition. Does **not** touch `current_scene_id`, loader tables, file IDs, or player state.

## Called by
- [[FUNC_8005222C]] @ `0x80052308` with `(a0=0, a1=−8)`. (Other callers, if any, would reuse the same wrap math.)

## Confidence
- Math (`a0 mod table[flag]` → `0x80082158/215c`) — **CONFIRMED (decoded)**.
- "Scroll/background offset" purpose — **LIKELY** (inferred from the table region + write targets; not behavior-verified).

## Related
[[FUNC_8005222C]] · [[Gameplay - Warp and Level Transition]] · `tools/exe_read.py`
