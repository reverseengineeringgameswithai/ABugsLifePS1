---
kind: function
id: FUNC_80024DDC
aliases:
- FUNC_80024DDC
- 2147634652
- '0x80024ddc'
- contact_record_post_init
address: '0x80024ddc'
name: contact-record_post-init_(state_byte_+0x37)
status: byte_matched
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
- EXP_2026-07-08_c_decompilation_campaign_v1
- EXP_2026-07-10_c_conversion_at_scale
src_paths:
- src/main/80024ddc_contact_record_post_init.c
patch_policy: unknown
---

# FUNC_80024DDC - contact-record post-init (state byte +0x37)

## Purpose

The "post-init" called at the tail of contact allocation ([[FUNC_80059E44]]). **It is trivial: it sets a single state byte `rec+0x37` from the record's flags. It does NOT register a render callback, an update-list entry, or GPU/sprite data** — so it does not make the ctor-0x71 contact entity visible. Evidence for the "ctor-0x71 = contact/logic, not rendered" verdict in [[Gameplay - Resident Noise and Ctor 0x71]]. STATIC (`exe_read.py --disasm`).

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80024DDC.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x80024DDC`
- Name: `contact-record_post-init_(state_byte_+0x37)`
- Original note: `ObsidianVault/Functions/FUNC_80024DDC.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80024DDC.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80024DDC.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80024DDC.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

