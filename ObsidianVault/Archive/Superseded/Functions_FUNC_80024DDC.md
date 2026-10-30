---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80024DDC.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80024DDC.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80024DDC_contact-record_post-init_(state_byte_+0x37).md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80024DDC — contact-record post-init (state byte +0x37)
type: function
address: 0x80024DDC
confidence: CONFIRMED (decoded)
tags: [function, contact, pickup, post-init, milestone6]
---
# FUNC_80024DDC — contact-record post-init helper

> The "post-init" called at the tail of contact allocation ([[FUNC_80059E44]]). **It is trivial: it sets a single state byte `rec+0x37` from the record's flags. It does NOT register a render callback, an update-list entry, or GPU/sprite data** — so it does not make the ctor-0x71 contact entity visible. Evidence for the "ctor-0x71 = contact/logic, not rendered" verdict in [[Gameplay - Resident Noise and Ctor 0x71]]. STATIC (`exe_read.py --disasm`).

| Field | Value |
|---|---|
| Address | `0x80024DDC` (8 instrs, `…0x80024dfc jr ra`; next fn @ `0x80024e04`) |
| Role | shared contact-record **post-init** (one state-byte setter) |
| Confidence | CONFIRMED (fully decoded) |

## Decoded body
```
lbu   v0, 0x33(a0)        ; v0 = rec.flags (+0x33)
li    v1, 0x2c
sb    v1, 0x37(a0)        ; rec+0x37 = 0x2c        (default)
andi  v0, v0, 0x60
beq   v0, 0x60 -> ret     ; if (flags & 0x60) == 0x60, keep 0x2c
sb    0x2e, 0x37(a0)      ; else rec+0x37 = 0x2e
jr ra
```
⇒ **`rec+0x37 = ((flags & 0x60) == 0x60) ? 0x2c : 0x2e`.** No other writes; no calls.

## Arguments / Returns
`a0` = pointer to the freshly-built contact record (in array `0x800b0d18`). Returns void.

## Calls (callees)
- **none.**

## Called by (callers)
- `jal` from **`0x8005a0b4`** (tail of [[FUNC_80059E44]] contact_alloc), **`0x8005a2e8`**, **`0x8005b060`** (two more contact-construction/state sites). Not stored as a function pointer anywhere (0 word-refs) — a plain shared helper, not a vtable entry.

## Globals & structures touched
- Writes only `rec+0x37` of a [[MEM - Contact array 800B0D18]] record (reads `rec+0x33` flags).

## Classification
**Generic post-init field-setter.** Not render registration, not update-list insertion, not contact/collision registration (the slot + radius/flags are already set by [[FUNC_80059E44]]); it merely finalizes one state byte. Consistent with the contact array being a logic/proximity structure, not a render list.

## Related
[[Gameplay - Resident Noise and Ctor 0x71]] · [[FUNC_80059E44]] · [[FUNC_800586B0]] · [[MEM - Contact array 800B0D18]] · `tools/exe_read.py`
