---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Indexes/Experiments Index.md
aliases:
  - "Experiments Index"
migration_action: merge
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Indexes/Experiments Index.md`
- Replacement/current location: `ObsidianVault/Canon/Indexes/Experiments_Index.md`
- Archive reason: Index material should be regenerated around Canon IDs.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Experiments Index
type: index
updated: 2026-07-05
tags: [index, experiment]
---

# Experiments Index

> Reproducible experiments. Disc-build experiments use targeted patch/build tools; live experiments use the DuckStation debugger against a [[Fixtures Index|fixture]]. ✅ = produced a visible in-game change.

## Geometry — disc builds (vertex/field edits)
| Experiment | What | Result |
|------------|------|--------|
| [[Experiment - G6 render sentinel]] | DAT+0x1526 trail flag → ff ff | ✅ terrain render mostly gone, collision intact |
| [[Experiment - G8 entry24 body edits]] | entry24 +0x04/+0x08 body fields | read-confirmed, no visual |
| [[Experiment - G12 source vec]] | entry29 source vec[0] +1024 | read-confirmed, no visual |
| [[Experiment - G13 payload v0]] | entry29 payload v0.y +512 | read-confirmed, no visual |
| [[Experiment - G14 payload vertex grass]] | entry29 v14.y −1024 | ✅ first visible payload-vertex deform (grass) |
| [[Experiment - G15 runtime payload vertex]] | payload 0x10180 v46.y −1024 | read-confirmed, no visual |
| [[Experiment - G16 emitted payload vertex wall]] | payload 0x356bc v10.y −1024 | ✅ visible wall deform |
| [[Experiment - G28 Candidate A floor Y]] | Candidate A v16.y +1024 | ✅ visible terrain deform; collision unaffected |

## Geometry / collision — live debugger (RAM, no disc)
| Experiment | What | Result |
|------------|------|--------|
| [[Experiment - G5.5 dynamic watch]] | read/exec watches on parser geometry | confirmed render-stage flag reads |
| [[Experiment - G29 collision lever validation]] | sector-origin Y edits | ✅ Flik footing scales ~1:1 |
| [[Experiment - G30 localized terrain edit]] | terrain buffer Y/X-shift | ✅ ground rises / shears |
| [[Experiment - G30 sky recolor]] | sky cache RGB patch | ✅ sky turns red/green |

## Sky / GPU injection
| Experiment | What | Result |
|------------|------|--------|
| [[Experiment - Starry night sky injection]] | inject GPU DMA linked-list | ✅ daytime → starry night |
| [[Experiment - Persistent nighttime render hook]] | per-frame back-buffer hook; moon+stars; haze off | ✅ flicker-free persistent night |

## Pickups / DAT
| Experiment | What | Result |
|------------|------|--------|
| [[Experiment - DAT relocation-aware append]] | add new entry 70 (token) | ✅ extra token visible & collectible |
| [[Experiment - FLIK5 five-letter token gate]] | append duplicate F and patch mask 0x0f→0x1f | ✅ SELECT shows FLIKF; token/progress advances only after 5 letters |
| [[Experiment - FLIK emblem image replacement]] | replace FLIK completion emblem image | confirmed: live `gpu.pickObject` source identified; build path patches both RAW copies |

## Related
[[Fixtures Index]] · [[Save States Index]] · [[Tools Catalog]] · [[API - experiment runner]] · [[Findings Index]] · [[Home]]
