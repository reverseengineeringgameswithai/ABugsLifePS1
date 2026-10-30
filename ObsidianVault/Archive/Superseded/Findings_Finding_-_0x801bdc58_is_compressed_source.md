---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - 0x801bdc58 is compressed source.md
aliases:
  - "Finding - 0x801bdc58 is compressed source"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - 0x801bdc58 is compressed source.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_0x801bdc58_is_compressed_source.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - 0x801bdc58 is compressed source
type: finding
confidence: RETRACTED
gstep: G26
tags: [finding, retraction, levelraw]
---

# Finding — `0x801bdc58` is compressed LEVEL.RAW source (RETRACTION)

> A worked-example of a corrected dead end. The address once believed to hold the "floor payload" is actually unwritten compressed source bytes.

**Confidence:** RETRACTED (the floor-payload claim) / CONFIRMED (the corrected interpretation) · **Established:** G26

## Summary
`[0x801bdc58] = 0x70d4001a`, which equals `LEVEL.RAW + 0xa81ac` (compressed bytes). A WRITE-watch on `0x801bdc58` got **0 hits** → it is never written, never a payload. This retracts the G17 "Candidate B / floor at `0x801bdc58`" premise (the `a0−4` formula was right, but the base was never count-validated), and with it the G18/G19/G22/G25 floor-location *chain* (though those steps' loader/codec facts still stand).

## Evidence
- Memory read at "Press X": `0x801bdc58` = `0x70d4001a` (an impossible vertex count).
- Re-disasm of [[FUNC_80010000]]: it reads count `[a0]`, advances `a0+=4`; the main path never rewrites `a0`, so `s5` reuse made the earlier base bogus.

## Related functions
[[FUNC_80010000]] · [[FUNC_8003A318]] · [[FUNC_8001A1DC]]

## Related memory structures
[[MEM - LEVEL.RAW chunk model]]

## Related experiments
n/a (live ground-truth read + WRITE-watch)

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - accessLog]] (WRITE-watch) · [[API - execTrace]]

## Next steps
New runbook = count-validate at EXEC `0x80010000` → led to [[Finding - Candidate A is DAT-backed visual terrain]].

## Source
`src_re_geometry/geometry_g26_floor_payload_reaudit.md`
