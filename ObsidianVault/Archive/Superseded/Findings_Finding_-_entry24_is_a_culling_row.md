---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - entry24 is a culling row.md
aliases:
  - "Finding - entry24 is a culling row"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - entry24 is a culling row.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_entry24_is_a_culling_row.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - entry24 is a culling row
type: finding
confidence: CONFIRMED
gstep: G7/G9
tags: [finding, rendering, geometry]
---

# Finding — DAT entry24 is a culling/range row, not mesh position

> Explains why the G8 entry24 edits read correctly but produced no visible change: that row feeds visibility culling, not vertex positions.

**Confidence:** CONFIRMED · **Established:** G7 (reads) → G9 (role)

## Summary
The DAT entry24 body row (`DAT 0x16e4/16e8/16ec/16f0`, runtime `0x80161edc`) is read by the render cull pass [[FUNC_800140A0]] after the per-entry visibility gate (bitmask `0x800901c8`). Its `(+0x00,+0x04,+0x08)` form a view-relative vector fed to GTE SQR/MVMVA; `+0x0c` is an extent/range term. In the tested state it passes one reject (`0x80014280`) but **rejects** at `0x800142b0` → it never reaches a list-write → it's a culling/bounds row.

## Evidence
G7 read-watches hit the predicted body PCs; G9 single-stepping showed the reject branch taken (no survivor-list write). G8 builds edited these fields with CPU-confirmed reads but no visible effect — consistent with a cull row.

## Related functions
[[FUNC_800140A0]] · [[FUNC_800224EC]]

## Related memory structures
[[MEM - Trail and pass3 tables]]

## Related experiments
[[Experiment - G8 entry24 body edits]]

## Related fixtures / save states
n/a (disc builds + live single-step)

## DuckStation APIs used
[[API - accessLog]] · [[API - execTrace]]

## Next steps
FLAGGED: runtime `s3` value at `+0x00` differed from the static value (possible runtime-rewrite of the row) — would gate static edits; unresolved.

## Source
`src_re_geometry/geometry_g9_entry24_dataflow.md`, `geometry_g55_dynamic_watch.md`
