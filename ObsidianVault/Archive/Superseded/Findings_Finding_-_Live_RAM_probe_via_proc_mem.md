---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Live RAM probe via proc mem.md
aliases:
  - "Finding - Live RAM probe via proc mem"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Live RAM probe via proc mem.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Live_RAM_probe_via_proc_mem.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Live RAM probe via proc mem
type: finding
confidence: CONFIRMED
gstep: G5.5 (era)
tags: [finding, tooling, method]
---

# Finding — Live guest-RAM probe via `/proc/<pid>/mem`

> The bootstrap technique used before the JSON-RPC debugger existed: read a running DuckStation's emulated PS1 RAM directly from the host.

**Confidence:** CONFIRMED · **Tool:** project memory `duckstation-live-ram-probe`

## Summary
DuckStation backs guest RAM with a host `memfd`; the guest physical address 0 maps to a known offset, so the host can read/parse live PS1 RAM through `/proc/<pid>/mem`. Used in G5.5 to corroborate parser structures (DATbase `0x801607f8`, trail `0x80161cfc`, pass-3 `0x801642e4`, counts) against the static model before the external-debugger API was available.

## Evidence
G5.5 Part A read live globals via this path and matched the static layout; later work migrated to the structured [[API - connection and auth|JSON-RPC debugger]] (port 2346).

## Related functions
[[FUNC_8001CDC0]] (parser structures it verified)

## Related memory structures
[[MEM - DAT runtime memory map]] · [[MEM - Parser output record]]

## Related experiments
[[Experiment - G5.5 dynamic watch]]

## Related fixtures / save states
n/a

## DuckStation APIs used
Superseded by [[API - connection and auth]] / [[API - readArray]] / [[API - accessLog]] (use the JSON-RPC debugger now; it's deterministic and re-armable).

## Next steps
Prefer the external-debugger API for anything new — it gives determinism, watchpoints, and the findings store.

## Source
Project memory `duckstation-live-ram-probe`; `src_re_geometry/geometry_g55_dynamic_watch.md`
