---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_800586B0.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_800586B0.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_800586B0_contact_-_pickup_walker.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_800586B0 — contact / pickup walker
type: function
address: 0x800586B0
confidence: CONFIRMED
tags: [function, pickup, contact]
---
# FUNC_800586B0 — contact / pickup proximity walker

> Scans the 64-entry contact array and fires a pickup's action when Flik is within its radius. This is PICKUP proximity — **not** world floor collision.

| Field | Value |
|-------|-------|
| Address | 0x800586B0 (size 580 B, …0x80058AF4) |
| Source file | `src_re/contact_walker_800586b0.c` (`contact_walker`) |
| Confidence | CONFIRMED loop/gates/distance/radius/dispatch |

## Purpose
Walks [[MEM - Contact array 800B0D18]]; for each live record computes a weak-Y distance and, if inside the radius, dispatches the record's action via table `0x8001b570[action_id-2]`. Math: `dx=((pX-rx)*0x300)>>13`, `dy=((pY-ry)*0x100)>>13`, `dz=((pZ-rz)*0x300)>>13`; contact if `dx²+dy²+dz² < (0x12c+radius_add)²`. Live gate: `lh rec+0x22 > 0 AND (lbu rec+0x33 & 2)`. The ⅓ Y weight is why tall up-moves auto-collect (the height-band rule).

## Arguments / Returns
none (reads globals; player Y biased `−0x1cc0`). Returns void.

## Calls (callees)
- per-action cases via table `0x8001b570`; `fcn.800503fc`, `fcn.8005044c`, `fcn.80050994` (sound/event), [[FUNC_80054EAC]] (grain case 0x14), `fcn.8004a700`.

## Called by (callers)
- `fcn.8004ecd4` @ `0x8004f074`.

## Globals & structures touched
- [[MEM - Contact array 800B0D18]] · [[MEM - Player state 800A6500]] · berry marker `0x800a6597` · walker dispatch `0x8001b570`.

## Evidence & confidence notes
CONFIRMED math + dispatch. Excluded as the floor-collision path in G29 (it is pickup proximity, weak-Y). Action-case bodies summarized in the decompiled source.

## Related
- Findings: [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Finding - No static collision consumer]]
- Functions: [[FUNC_80053814]] · [[FUNC_80059E44]] · [[FUNC_80054EAC]]
- Memory: [[MEM - Contact array 800B0D18]] · System: [[LEVEL.DAT object pipeline]] · [[Physics]]
- Source docs: `src_re/contact_walker_800586b0.c`
