---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Indexes/Findings Index.md
aliases:
  - "Findings Index"
migration_action: merge
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Indexes/Findings Index.md`
- Replacement/current location: `ObsidianVault/Canon/Indexes/Findings_Index.md`
- Archive reason: Index material should be regenerated around Canon IDs.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Findings Index
type: index
updated: 2026-06-17
tags: [index, finding]
---

# Findings Index

> All 28 findings, grouped by topic. Confidence is CONFIRMED unless noted. The settled-facts digest is [[Confirmed Knowledge]]; beliefs/dead-ends are in [[Hypotheses]].

## Rendering / visible terrain
- [[Finding - Visible terrain renderer]] — `fcn.800172dc` + buffer `0x8012c1d0`
- [[Finding - Terrain on-disk source is chunk 35]]
- [[Finding - Visible ground from DAT verts]] — bulk foreground floor
- [[Finding - Candidate A is DAT-backed visual terrain]]
- [[Finding - fcn.80010000 payload format]]
- [[Finding - Payload vertex edits are visible]]
- [[Finding - 0x356bc is a wall not floor]]
- [[Finding - entry24 is a culling row]]
- [[Finding - Trail flag gates terrain render]]
- [[Finding - Two parser source-record formats]]

## Collision / physics
- [[Finding - Visual is not collision]] (central)
- [[Finding - Collision sector table]]
- [[Finding - Collision on-disk source is chunk 32]]
- [[Finding - Collision is planes not scalar]]
- [[Finding - Collision lever sector186]]
- [[Finding - Collision RAM edit moves footing 1to1]]
- [[Finding - Player Y writer FUNC_3633C]]
- [[Finding - No static collision consumer]] (CONFIRMED-negative)

## Sky / GPU
- [[Finding - Sky is a GP0 background fill]]
- [[Finding - Sky color on-disk table]]
- [[Finding - GPU primitive injection]]
- [[Finding - Persistent night render hook]] — flicker-free per-frame night (big moon, haze removed)

## Assets / loading
- [[Finding - Floor resource is LEVEL.RAW]]
- [[Finding - LEVEL.RAW is compressed]] (LZ codec gate)
- [[Finding - 0x801bdc58 is compressed source]] (RETRACTED premise)

## Pickups / DAT modding (shipped in-game)
- [[Finding - Type-0x3f pickups are coordinate-moddable]]
- [[Finding - Relocation-aware DAT append]]

## Method / tooling
- [[Finding - Localized terrain edit]]
- [[Finding - Live RAM probe via proc mem]]

## Related
[[Confirmed Knowledge]] · [[Hypotheses]] · [[Functions Index]] · [[Experiments Index]] · [[Home]]
