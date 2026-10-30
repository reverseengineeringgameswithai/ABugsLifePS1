---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8005EC94.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8005EC94.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8005EC94_ANM_animation_player_(keyframe_core).md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8005EC94 — .ANM animation player (keyframe core)
address: 0x8005EC94
type: function
confidence: CONFIRMED
tags: [function, animation, anm, models, b7]
---
# FUNC_8005EC94 — `.ANM` animation player (keyframe core)

> Plays a character's `.ANM` animation: walks the active animation sub-block's frames and decodes its **bitmask-compressed channel keyframes**, producing the per-frame pose. Identified live (no operator) while driving Flik forward → [[Finding - Character ALL model format]].

| Field | Value |
|-------|-------|
| Address | `0x8005EC94`–`0x8005F0F4` (core) |
| Confidence | CONFIRMED (2765 reads of the active `.ANM` block while Flik-Y moved; deterministic) |

## Purpose
Decodes a `.ANM` animation sub-block (see [[Asset - Character and plant models]]):
- Reads the sub-block header — frame count (`+2`, masked `0x7fff` at `0x8005ed84`), channel counts (`+4/+6/+8`), frame-time table (stride 6).
- Per frame, reads a **mask byte** and tests **one bit per channel** (`0x8005f028`: `lbu` → `srav v0,v0,v1; andi v0,1`); for each set bit it loads an `s16` channel value (`lh 0xc(t)` at `0x8005f048`) and applies it. ⇒ sparse keyframes (only changed channels stored), interpolated across the frame-time table.

## Called by / related
- **Pointer-table accessor** `0x8001da94`–`0x8001dfa0` — dereferences the `.ANM` header offset table (`+0x4/+0x6`) to locate the active animation sub-block (the header is relocated to absolute pointers at load).
- Drives the model rendered by [[FUNC_800172DC]] (the `.ALL` primitive list).

## Globals & structures
- `FLICK.ANM` resident at `0x800ff984` (relocated pointer table → per-animation sub-blocks; `hdr_u16[1]` = animation count = 40 for FLICK).

## Channel → bone binding (resolved)
Each channel drives **one bone's rotation** (skeletal, not vertex morph). The channel decodes to **3 s16** (keyframe `+0xc/+0xe/+0x10`), interpolated `cur + ((next−cur)·t2>>16)` (`t2` = 0.16 frac), written to **`bone[i]+0x18/0x1a/0x1c`** (`+0x1e=1`) in the 84-byte-per-bone skeleton [[MEM - Skeleton bone transform 8008A1F8]] (FLICK = 24 bones). The bitmask gates which bones update per keyframe.

## Residuals
- **Skinning**: how the posed skeleton transforms the `.ALL` vertices (GTE matrix build + vertex weights).

## Related
- Findings: [[Finding - Character ALL model format]] · Assets: [[Asset - Character and plant models]] · Functions: [[FUNC_800172DC]] · Blocker: [[Blocker - Character and plant model formats are unreversed]]
