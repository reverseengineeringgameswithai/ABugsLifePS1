---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80053814.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80053814.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80053814_type-0x3f_construct_+_contact-action_dispatch.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80053814 — type-0x3f construct + contact-action dispatch
type: function
address: 0x80053814
confidence: CONFIRMED
tags: [function, pickup, type3f, dat]
---
# FUNC_80053814 — type-0x3f per-entry construct + contact-action dispatch

> Iterates the type-0x3f record, constructs each pickup's runtime entity, and fires its contact pickup action via a jump table. The behavioral half of the pickup pipeline.

| Field | Value |
|-------|-------|
| Address | 0x80053814 (size 4092 B, …0x80054810) |
| Source file | `src_re/source3f_dispatch_80053814.c` (`source3f_dispatch`) |
| Confidence | CONFIRMED top-level structure, eligibility gate, 3 construct paths, jump table |

## Purpose
For each eligible type-0x3f entry: CONSTRUCT its entity (grain ctor `0x51`, generic `0x71`, telescope path) via [[FUNC_80059E44]], and/or fire its contact ACTION via jump table `0x8001b42c` (index `kind-0x10`). Eligibility: `entry.Y != 0x80000000` sentinel AND `status(+0x0d)==1`. Distance gates: generic construct ≤0x3d08f, grain construct ≤0x15f8f, contact action <0x9c4.

## Arguments / Returns
none (reads globals). Internally `a1` = type-0x3f ptr (`0x80096e9c`), `a0` = player-pos base (`0x800a6500`). Returns void.

## Calls (callees)
- [[FUNC_80059E44]] — contact alloc (grain 0x51/3, generic 0x71/0x18).
- [[FUNC_80054EAC]] — grain handler (kind 0x14, via jr table).
- `fcn.80057620` (telescope construct), `fcn.8005044c`, `fcn.80045678`, sounds `fcn.8005721c/800571e0`.
- Per-kind handlers via jr table `0x8001b42c` (FLIK `0x80053d04…`, berry `0x80054288…`, token `0x800542f4…`, telescope `0x80054554`).

## Called by (callers)
- `fcn.8004ecd4` @ `0x8004f028` (sole direct caller).

## Globals & structures touched
- [[MEM - Type-0x3f placement record]] (`0x80096e9c`) · [[MEM - Player state 800A6500]] · berry marker `0x800a6597` · seed counters `0x800a6598..` · jr table `0x8001b42c`.

## Evidence & confidence notes
CONFIRMED structure + 3 construct paths + jump table; kind-0x30/0x31 animated-construct inner math LIKELY/TODO. The kind→item map is in [[Symbols Index]]; berries 54–57 must not have their kind changed ([[Finding - Type-0x3f pickups are coordinate-moddable]]).

## Related
- Findings: [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Finding - Relocation-aware DAT append]]
- Functions: [[FUNC_8001CDC0]] · [[FUNC_80059E44]] · [[FUNC_800586B0]] · [[FUNC_80054EAC]] · [[FUNC_800526F4]]
- System: [[LEVEL.DAT object pipeline]] · Memory: [[MEM - Contact array 800B0D18]]
- Source docs: `src_re/source3f_dispatch_80053814.c`, `docs/LEVEL_OBJECT_PIPELINE.md`
