---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Symbols/Symbols Index.md
aliases:
  - "Symbols Index"
migration_action: merge
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Symbols/Symbols Index.md`
- Replacement/current location: `ObsidianVault/Canon/Indexes/Symbols_Index.md`
- Archive reason: Index material should be regenerated around Canon IDs.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Symbols Index
type: index
updated: 2026-06-17
tags: [index, symbols, addresses]
---

# Symbols Index

> Flat address → name → note table. `$gp = 0x80081d98`. Sourced from `src_re/re_types.h`, the decompiled C, and the G-series live traces. Use this to go from a raw address (e.g. from a debugger trace) to the right note. Functions have [[Functions Index|FUNC_ notes]]; structures have [[Memory Structures]] notes.

## Functions (key)
| Address | Name / role | Note |
|---------|-------------|------|
| `0x80010000` | per-object mesh draw / payload emitter | [[FUNC_80010000]] |
| `0x80017b98` | GTE rotation-matrix setup | [[FUNC_80017B98]] |
| `0x8001a1dc` | LEVEL.RAW LZSS decompressor | [[FUNC_8001A1DC]] |
| `0x8001cdc0` | DAT parser / relocator | [[FUNC_8001CDC0]] |
| `0x8001dfe4` | scene-geometry draw dispatcher (5 emitters) | [[FUNC_8001DFE4]] |
| `0x8001ea6c` | survivor-list primitive builder #1 | [[FUNC_8001EA6C]] |
| `0x80019934` | bulk-ground sub-emitter | [[FUNC_80019934]] |
| `0x800140a0` | GTE trail-cull transform | [[FUNC_800140A0]] |
| `0x800172dc` | shared `.ALL`/mesh renderer (terrain occluded; not the visible floor) | [[FUNC_800172DC]] |
| `0x800206e8` | survivor-list primitive builder #2 | [[FUNC_800206E8]] |
| `0x800224ec` | scene/render driver | [[FUNC_800224EC]] |
| `0x80025084` | oriented containment/range test | [[FUNC_80025084]] |
| `0x80030f60` | collision sector-table builder | [[FUNC_80030F60]] |
| `0x8003633c` | player movement+collision integrator (Y writer) | [[FUNC_8003633C]] |
| `0x80036cec` | (PC) player-Y commit store | [[FUNC_8003633C]] |
| `0x800345cc` | collision resolver | [[FUNC_800345CC]] |
| `0x8003a318` | high-heap loader + RAW per-chunk decompress | [[FUNC_8003A318]] |
| `0x8003cf2c` | resource-ID dispatcher / DAT-load caller | [[FUNC_8003CF2C]] |
| `0x80046330` | universal file loader | [[FUNC_80046330]] |
| `0x800526f4` | HUD draw | [[FUNC_800526F4]] |
| `0x80053814` | type-0x3f construct + contact-action dispatch | [[FUNC_80053814]] |
| `0x80054eac` | grain pickup handler | [[FUNC_80054EAC]] |
| `0x80059e44` | ContactRecord allocator | [[FUNC_80059E44]] |
| `0x80060724` | libgte RotTransPers transform leaf bank | [[FUNC_80060724]] |
| `0x800586b0` | contact / pickup walker | [[FUNC_800586B0]] |
| `0x800639cc` | DRAWENV GP0 background-fill builder | [[FUNC_800639CC]] |
| `0x8005b134` | player-pos / Region-A overlay dispatcher (superseded claim) | [[FUNC_8005B134]] |
| `0x8004fa40` | main shell state machine | [[Systems]] |
| `0x8004ecd4` | gameplay state machine | [[Systems]] |

## DAT parser / geometry globals
| Address | Name | Note |
|---------|------|------|
| `0x80082498` | G_DAT_BASE_PTR (DATbase = `0x801607f8`) | [[MEM - DAT runtime memory map]] |
| `0x80096da0` | dynamic DAT type-pointer table | [[MEM - Type-0x3f placement record]] |
| `0x80096e9c` | type-0x3f record pointer | [[MEM - Type-0x3f placement record]] |
| `0x800824ac` | G_TRAIL_BLOCK_PTR (`0x80161cfc`) | [[MEM - Trail and pass3 tables]] |
| `0x80082508` | G_PASS3_BASE_PTR (`0x801642e4`) | [[MEM - Trail and pass3 tables]] |
| `0x80082338` | G_PASS2_BASE_PTR (empty) | [[MEM - Trail and pass3 tables]] |
| `0x800822f0` | G_DAT_ENTRY_COUNTER (624) | — |
| `0x800901c8` | render body-field gating bitmask | [[MEM - Trail and pass3 tables]] |
| `0x80096ea8` / `0x8009e338` | LIST_A / LIST_B survivor lists | [[MEM - Survivor lists]] |
| `0x8008240c` | GPU/OT output buffer ptr (gp+0x674) | [[MEM - Survivor lists]] |
| `0x80089528` | matrix LUT | — |
| `0x1f800374` / `0x1f800384` / `0x1f8003b4` | camera / view vector / view matrix scratch | — |

## Contact / pickup globals
| Address | Name | Note |
|---------|------|------|
| `0x800b0d18` | ContactRecord array (64×0x38) | [[MEM - Contact array 800B0D18]] |
| `0x8008234c` | alloc cursor (wrap 0x40) | [[MEM - Contact array 800B0D18]] |
| `0x8007941c` / `0x80079e30` | metadata table B / table A | [[MEM - Contact array 800B0D18]] |
| `0x8001b42c` / `0x8001b570` | source-side / walker dispatch tables | [[FUNC_80053814]] / [[FUNC_800586B0]] |
| `0x8009c870` | visual sprite-object pool (8×0x344) | [[Rendering]] |

## Player / progress globals
| Address | Name | Note |
|---------|------|------|
| `0x800a6500/04/08` | player X / Y / Z | [[MEM - Player state 800A6500]] |
| `0x800a652c` | velocity / delta | [[MEM - Player state 800A6500]] |
| `0x800a6597` | berry/FLIK marker | [[MEM - Player state 800A6500]] |
| `0x800a6598/99/9a` | seed counters | [[MEM - Player state 800A6500]] |
| `0x800a65a1` | grain count (HUD mirror) | [[MEM - Player state 800A6500]] |
| `0x800a65a2` | FLIK bitmask | [[MEM - Player state 800A6500]] |

## Collision / LEVEL.RAW globals
| Address | Name | Note |
|---------|------|------|
| `0x80115aac` | LEVEL.RAW compressed load base (size `0xb6be4`) | [[MEM - LEVEL.RAW chunk model]] |
| `0x800a7e48` | collision sector table (223×0x30) | [[MEM - Collision sector table 800A7E48]] |
| `0x800aa128` | player sector record (sec186) | [[Finding - Collision lever sector186]] |
| `~0x800D0xxx` | collision plane records (32-byte) | [[MEM - Collision plane record]] |
| `0x800c1690` | collision plane block | [[MEM - Collision plane record]] |
| `0x800c1688` | on-disk sky color table | [[MEM - Sky DRAWENV color cache 800771BC]] |
| `0x8009c230` | per-frame collision candidate list | [[MEM - Collision sector table 800A7E48]] |

## Rendering / sky globals
| Address | Name | Note |
|---------|------|------|
| `0x8012c1d0`–`0x8012e784` | visible terrain vertex buffer | [[MEM - Terrain vertex buffer 8012C1D0]] |
| `0x800771bc/c0/c4` | sky clear-color cache (R/G/B) | [[MEM - Sky DRAWENV color cache 800771BC]] |

## Overlays / scene machine
| Address | Name | Note |
|---------|------|------|
| `0x800b39a0` | Region A overlay base (LEVEL.BIN) | [[Asset - LEVEL.BIN and overlays]] |
| `0x800b5788` | Region B overlay base (MEMORY.BIN/FMV) | [[Asset - LEVEL.BIN and overlays]] |
| `0x800823a0` | master game state | [[Systems]] |
| `0x8008243c` | main-shell substate index (mod 6) | [[Systems]] |
| `0x80082504` | current scene id | [[Systems]] |

## Symbol import/export
The M3 reviewed baseline is [[Symbol Map Baseline]] with machine-readable `symbols/re_symbols.sym`. Validate with `python3 tools/validate_symbol_map.py`; [[Symbol Import Round Trip]] records the fork-compatible CSV and r2 consumer proof, while [[API - symbols]] documents optional live import. This index remains the broad navigation table; the baseline records per-symbol confidence/import guidance. The findings store (`re_findings.yaml`) holds address-tagged findings — see [[API - findings store]].
