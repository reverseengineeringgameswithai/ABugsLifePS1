---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Campaign Level Coverage Matrix.md
aliases:
  - "Campaign Level Coverage Matrix"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Campaign Level Coverage Matrix.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Campaign_Level_Coverage_Matrix.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Campaign Level Coverage Matrix
type: system
status: active reference
updated: 2026-07-02
confidence: STATIC-COMPLETE / RUNTIME-PARTIAL
tags: [system, campaign, levels, retail-completeness, rcg-001]
---

# Campaign Level Coverage Matrix

> Static campaign-wide inventory generated from `REBUILD/files/LEVEL00..LEVEL10` by `tools/campaign_level_inventory.py`. This closes the `RCG-001` inventory gap: every retail stage now has a directory/overlay/resource profile, and every level directory has a DAT/RAW/object-sidecar summary. Objective semantics are intentionally marked as residual runtime work.

## Scene / stage map

Source: resident filename table `0x8001ad0c`, already documented in [[Finding - Level-warp mechanism]].

| Stage | Directory | Overlay stem | Static profile |
|---:|---|---|---|
| 1 | `LEVEL01` | `LEVEL1A` | DAT: LEVEL.DAT, LEVEL1.DAT, LEVEL2.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 2 | `LEVEL03` | `LEVEL1B` | DAT: LEVEL.DAT, LEVEL1.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 3 | `LEVEL02` | `LEVEL1C` | DAT: LEVEL.DAT, LEVEL1.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 4 | `LEVEL06` | `LEVEL2A` | DAT: LEVEL.DAT, LEVEL1.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 5 | `LEVEL10` | `LEVEL2B` | DAT: LEVEL.DAT; RAW: LEVEL.RAW |
| 6 | `LEVEL01` | `LEVEL2C` | DAT: LEVEL.DAT, LEVEL1.DAT, LEVEL2.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 7 | `LEVEL04` | `LEVEL3A` | DAT: LEVEL.DAT, LEVEL1.DAT, LEVEL4.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 8 | `LEVEL05` | `LEVEL3B` | DAT: LEVEL.DAT, LEVEL1.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 9 | `LEVEL04` | `LEVEL3C` | DAT: LEVEL.DAT, LEVEL1.DAT, LEVEL4.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 10 | `LEVEL07` | `LEVEL4A` | DAT: LEVEL.DAT, LEVEL1.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 11 | `LEVEL02` | `LEVEL4B` | DAT: LEVEL.DAT, LEVEL1.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 12 | `LEVEL03` | `LEVEL4C` | DAT: LEVEL.DAT, LEVEL1.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 13 | `LEVEL09` | `LEVEL5A` | DAT: LEVEL.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 14 | `LEVEL08` | `LEVEL5B` | DAT: LEVEL.DAT, LEVEL1.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |
| 15 | `LEVEL05` | `LEVEL5C` | DAT: LEVEL.DAT, LEVEL1.DAT; RAW: LEVEL.RAW, LEVEL1.RAW |

## Level directory profiles

| Dir | Stages | DAT files | Primary type-0x3f kinds | RAW chunks | Sidecars |
|---|---|---|---|---|---|
| `LEVEL00` | (dev/unmapped) | LEVEL.DAT 0 recs [] | - | LEVEL.RAW: 47 chunks / 1200596 B, largest 46=82700 B<br>LEVEL1.RAW: 2 chunks / 197404 B, largest 1=131088 B<br>LEVEL2.RAW: 6 chunks / 266824 B, largest 0=66316 B<br>LEVEL3.RAW: 3 chunks / 394028 B, largest 1=163856 B<br>LEVEL4.RAW: 19 chunks / 868636 B, largest 7=245776 B | LEVEL.BIN, TERRAIN.ALL |
| `LEVEL01` | 1:LEVEL1A, 6:LEVEL2C | LEVEL.DAT 11 recs [-0x7:1, -0x6:1, -0x5:1, -0x4:1, -0x3:1, -0x2:1, 0x1:1, 0xb:1, 0xc:1, 0xd:1, 0x3f:1]<br>LEVEL1.DAT 1 recs [0x3f:1]<br>LEVEL2.DAT 12 recs [-0xb:1, -0xa:1, -0x9:1, -0x8:1, -0x7:1, -0x6:1, -0x5:1, -0x4:1, -0x3:1, -0x2:1, 0x1:1, 0x3f:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=50, 0x21 green-berry=1, 0x22 gold-berry=1, 0x23 blueberry=1, 0x24 purple-berry=1, 0x29 seed-orange=3, 0x2a seed-blue=3, 0x2b seed-green=3, 0x30 telescope=3 | LEVEL.RAW: 69 chunks / 1269304 B, largest 32=236944 B<br>LEVEL1.RAW: 52 chunks / 943436 B, largest 31=213098 B | LEVEL.BIN, LEVEL1.BIN, TERR1.ALL, TERRAIN.ALL, LEVEL1A.VB, LEVEL1A.VH, LEVEL2C.VB, LEVEL2C.VH |
| `LEVEL02` | 3:LEVEL1C, 11:LEVEL4B | LEVEL.DAT 2 recs [0x1:1, 0x3f:1]<br>LEVEL1.DAT 4 recs [0x1:1, 0xb:1, 0xc:1, 0x3f:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=50, 0x23 blueberry=2, 0x2c seed-token-2c=4 | LEVEL.RAW: 45 chunks / 915036 B, largest 30=182342 B<br>LEVEL1.RAW: 67 chunks / 869632 B, largest 29=37648 B | LEVEL.BIN, LEVEL1.BIN, TERR1.ALL, TERRAIN.ALL, LEVEL1C.VB, LEVEL1C.VH, LEVEL4B.VB, LEVEL4B.VH, LEVEL4BC.VB, LEVEL4BC.VH |
| `LEVEL03` | 2:LEVEL1B, 12:LEVEL4C | LEVEL.DAT 6 recs [0x1:1, 0x2:1, 0x9:1, 0xb:1, 0xc:1, 0x3f:1]<br>LEVEL1.DAT 1 recs [0x3f:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=50, 0x23 blueberry=2, 0x2b seed-green=2, 0x2c seed-token-2c=4, 0x30 telescope=2, 0x31 animated-construct=5 | LEVEL.RAW: 55 chunks / 1145914 B, largest 28=268372 B<br>LEVEL1.RAW: 50 chunks / 914474 B, largest 33=182342 B | LEVEL.BIN, LEVEL1.BIN, TERR1.ALL, TERRAIN.ALL, LEVEL1B.VB, LEVEL1B.VH, LEVEL4C.VB, LEVEL4C.VH |
| `LEVEL04` | 7:LEVEL3A, 9:LEVEL3C | LEVEL.DAT 11 recs [0x1:1, 0x2:1, 0x3:1, 0x4:1, 0x5:1, 0x6:1, 0x9:1, 0xb:1, 0xc:1, 0xd:1, 0x3f:1]<br>LEVEL1.DAT 7 recs [0x0:1, 0x1:1, 0x2:1, 0x3:1, 0x4:1, 0x5:1, 0x3f:1]<br>LEVEL4.DAT 7 recs [0x0:1, 0x1:1, 0x2:1, 0x3:1, 0x4:1, 0x5:1, 0x3f:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=24, 0x2a seed-blue=1, 0x2b seed-green=4, 0x2c seed-token-2c=4, 0x2d seed-token-2d=2, 0x30 telescope=3, 0x31 animated-construct=5 | LEVEL.RAW: 65 chunks / 1043926 B, largest 31=201516 B<br>LEVEL1.RAW: 35 chunks / 763536 B, largest 29=213098 B | LEVEL.BIN, LEVEL1.BIN, TERR1.ALL, TERRAIN.ALL, LEVEL3A.VB, LEVEL3A.VH, LEVEL3AC.VB, LEVEL3AC.VH, LEVEL3C.VB, LEVEL3C.VH |
| `LEVEL05` | 8:LEVEL3B, 15:LEVEL5C | LEVEL.DAT 5 recs [0xb:1, 0xc:1, 0xd:1, 0xe:1, 0x3f:1]<br>LEVEL1.DAT 4 recs [0x1:1, 0xb:1, 0xc:1, 0x3f:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=50, 0x29 seed-orange=1, 0x2a seed-blue=4, 0x2b seed-green=2, 0x2c seed-token-2c=4, 0x30 telescope=4, 0x31 animated-construct=5 | LEVEL.RAW: 63 chunks / 921972 B, largest 0=33548 B<br>LEVEL1.RAW: 52 chunks / 1174576 B, largest 31=198000 B | LEVEL.BIN, LEVEL1.BIN, TERR1.ALL, TERRAIN.ALL, LEVEL3B.VB, LEVEL3B.VH, LEVEL3BC.VB, LEVEL3BC.VH, LEVEL5C.VB, LEVEL5C.VH, LEVEL5CC.VB, LEVEL5CC.VH |
| `LEVEL06` | 4:LEVEL2A | LEVEL.DAT 1 recs [0x3f:1]<br>LEVEL1.DAT 1 recs [0x3f:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=50, 0x21 green-berry=1, 0x22 gold-berry=1, 0x29 seed-orange=2, 0x2b seed-green=2 | LEVEL.RAW: 51 chunks / 1108232 B, largest 32=213098 B<br>LEVEL1.RAW: 63 chunks / 1008422 B, largest 32=182342 B | LEVEL.BIN, LEVEL1.BIN, TERR1.ALL, TERRAIN.ALL, LEVEL2A.VB, LEVEL2A.VH |
| `LEVEL07` | 10:LEVEL4A | LEVEL.DAT 8 recs [0x1:1, 0xb:1, 0xc:1, 0xd:1, 0xe:1, 0xf:1, 0x10:1, 0x3f:1]<br>LEVEL1.DAT 2 recs [0xb:1, 0x3f:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=50, 0x22 gold-berry=2, 0x29 seed-orange=3, 0x2a seed-blue=3, 0x2b seed-green=2, 0x2c seed-token-2c=2, 0x30 telescope=6, 0x31 animated-construct=5 | LEVEL.RAW: 70 chunks / 1006142 B, largest 50=56704 B<br>LEVEL1.RAW: 50 chunks / 980876 B, largest 35=182342 B | LEVEL.BIN, LEVEL1.BIN, TERR1.ALL, TERRAIN.ALL, LEVEL4A.VB, LEVEL4A.VH, LEVEL4AC.VB, LEVEL4AC.VH |
| `LEVEL08` | 14:LEVEL5B | LEVEL.DAT 2 recs [0x1:1, 0x3f:1]<br>LEVEL1.DAT 2 recs [0x1:1, 0x2:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=50, 0x22 gold-berry=1, 0x23 blueberry=1 | LEVEL.RAW: 52 chunks / 1230770 B, largest 31=202632 B<br>LEVEL1.RAW: 12 chunks / 419236 B, largest 1=66316 B | LEVEL.BIN, LEVEL1.BIN, TERRAIN.ALL, LEVEL5B.VB, LEVEL5B.VH |
| `LEVEL09` | 13:LEVEL5A | LEVEL.DAT 6 recs [-0x4:1, 0x1:1, 0xb:1, 0xc:1, 0xd:1, 0x3f:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=50, 0x29 seed-orange=1, 0x2a seed-blue=4, 0x2b seed-green=4, 0x2d seed-token-2d=3, 0x30 telescope=3, 0x31 animated-construct=5 | LEVEL.RAW: 73 chunks / 1166854 B, largest 31=207544 B<br>LEVEL1.RAW: 17 chunks / 2785552 B, largest 0=163856 B | LEVEL.BIN, LEVEL1.BIN, TERRAIN.ALL, LEVEL5A.VB, LEVEL5A.VH |
| `LEVEL10` | 5:LEVEL2B | LEVEL.DAT 7 recs [0x1:1, 0x9:1, 0xb:1, 0xc:1, 0xd:1, 0xe:1, 0x3f:1] | 0x10 FLIK-F=1, 0x11 FLIK-L=1, 0x12 FLIK-I=1, 0x13 FLIK-K=1, 0x14 grain=50, 0x21 green-berry=1, 0x22 gold-berry=1, 0x23 blueberry=1, 0x24 purple-berry=1, 0x29 seed-orange=1, 0x2a seed-blue=3, 0x2b seed-green=4, 0x30 telescope=4, 0x31 animated-construct=4 | LEVEL.RAW: 70 chunks / 1237726 B, largest 33=213098 B | LEVEL.BIN, TERRAIN.ALL, LEVEL2B.VB, LEVEL2B.VH |

## Coverage status

- **Complete static coverage:** all `LEVEL00..LEVEL10` directories, all `*.DAT`, all `*.RAW`, all level overlays, VAB sidecars, and terrain model sidecars are inventoried.
- **Object coverage:** all primary `type-0x3f` pickup/object tables are counted by kind across the campaign; unknown kinds remain visible as explicit `?` labels instead of hidden assumptions.
- **Geometry/collision coverage:** RAW container chunk counts, decompressed sizes, texture-frame chunks, and largest chunks are known for each level; exact collision/floor role indices remain per-level follow-up work.
- **Runtime coverage inherited:** fixed-address runtime structures have already been live-confirmed for LEVEL02/03/04/05 in [[Finding - Level formats generalize, content is per-level]].
- **Residual:** objective semantics, exits/boss triggers, per-overlay verb meanings, and per-level editor material profiles still belong to `RCG-003`, `RCG-006`, `RCG-007`, and `RCG-009`; they are no longer part of the broad campaign-coverage gap.

## Reproduction

```bash
python3 tools/campaign_level_inventory.py --root REBUILD/files --json build/campaign_level_inventory.json --markdown 'ObsidianVault/Systems/Campaign Level Coverage Matrix.md'
```

## Related

[[Retail Gameplay Completeness Gap Audit]] · [[Finding - Level formats generalize, content is per-level]] · [[Finding - Level-warp mechanism]] · [[Asset - LEVEL.DAT]] · [[Asset - LEVEL.RAW]] · [[Asset - LEVEL.BIN and overlays]] · `src_re/campaign_level_coverage.c`
