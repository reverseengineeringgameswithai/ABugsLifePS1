---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Indexes/Functions Index.md
aliases:
  - "Functions Index"
migration_action: merge
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Indexes/Functions Index.md`
- Replacement/current location: `ObsidianVault/Canon/Indexes/Functions_Index.md`
- Archive reason: Index material should be regenerated around Canon IDs.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Functions Index
type: index
updated: 2026-06-21
tags: [index, function]
---

# Functions Index

> Encyclopedia of the important routines. 35 documented functions, grouped by subsystem. Addresses are KSEG0; `$gp = 0x80081d98`. Minor helpers are listed inline at the bottom.

## DAT object pipeline
| Function | Role |
|----------|------|
| [[FUNC_8001CDC0]] | DAT parser / relocator (1248 sites, 3 passes) |
| [[FUNC_8004C13C]] | **mover/PATH bytecode VM** (GAP-0033 interpreter; opcode table `0x8001b2f4`, IP=object[+0x70], opcode 9 = LEVEL.DAT path-follow) |
| [[FUNC_80053814]] | type-0x3f construct + contact-action dispatch |
| [[FUNC_80059E44]] | ContactRecord allocator |
| [[FUNC_80024DDC]] | ContactRecord post-init (sets state byte +0x37; trivial, no render/update reg) |
| [[FUNC_800586B0]] | contact / pickup proximity walker |
| [[FUNC_80054EAC]] | grain pickup handler |
| [[FUNC_80054C90]] | checkpoint-save (live pos → respawn anchor `0x800a6550`) |
| [[FUNC_800526F4]] | HUD draw |

## Loaders & decompression
| Function | Role |
|----------|------|
| [[FUNC_8003CF2C]] | resource-ID dispatcher / DAT-load caller |
| [[FUNC_80046330]] | universal file loader |
| [[FUNC_8003A318]] | high-heap loader + LEVEL.RAW decompress orchestrator |
| [[FUNC_8005222C]] | **level-transition orchestrator** (load globals + fade + reset; scene_id 19→0→target) |
| [[FUNC_8003DF14]] | transition scroll/offset helper (`x mod table[flag]`) |
| [[FUNC_80045A60]] | transition finalizer (clear flag `0x80082478` + subsystem reset) |
| [[FUNC_8004A700]] | **type-2 transition initiator** (overlay-callable; `a3`=destination; manages exit-counter `0x800a6594`) |
| [[FUNC_8004ABF4]] | **type-6 per-tick transition updater** (gate `0x8004f0e8`; actor `0x80090748`; countdown `0x8008223c`→5) |
| [[FUNC_8001A1DC]] | LEVEL.RAW LZSS decompressor (codec gate) |

## Render pipeline
| Function | Role |
|----------|------|
| [[FUNC_800224EC]] | scene / render driver |
| [[FUNC_800140A0]] | GTE trail-cull transform (terrain-gate reader) |
| [[FUNC_8001DFE4]] | scene-geometry draw dispatcher (5 emitters) |
| [[FUNC_800172DC]] | shared `.ALL`/mesh renderer (terrain occluded; not the visible floor) |
| [[FUNC_8001EA6C]] | survivor-list primitive builder #1 |
| [[FUNC_800206E8]] | survivor-list primitive builder #2 |
| [[FUNC_80010000]] | per-object mesh draw / payload emitter |
| [[FUNC_80019934]] | bulk-ground sub-emitter |
| [[FUNC_80060724]] | libgte transform leaf bank (missed render layer) |
| [[FUNC_800639CC]] | DRAWENV GP0 0x02 background-fill (sky) builder |
| [[FUNC_80017B98]] | GTE rotation-matrix setup |
| [[FUNC_8003E928]] | horizon / sky-strip ("haze") draw — `jr ra` disable lever |

## Collision / physics
| Function | Role |
|----------|------|
| [[FUNC_8003633C]] | player movement + collision integrator (Y writer) |
| [[FUNC_800345CC]] | collision resolver / accumulate |
| [[FUNC_80030F60]] | collision sector-table builder |
| [[FUNC_80025084]] | oriented containment / range test (wall/ledge candidate) |
| [[FUNC_8005B134]] | overlay state dispatcher; **tail = player respawn placement** (anchor→live pos) |
| [[FUNC_8005B714]] | gameplay-state reset; **sole seed of byte-stream cursor** `0x800822f4` = `0x80017DB4` |

## Minor helpers (no dedicated note)
`fcn.8004ecd4` gameplay state machine (calls 80053814/800586b0/800526f4) · `fcn.80035f24` collision sweep · `fcn.80032610` point-in-face · `fcn.800593e8` render-attr lookup · `fcn.80024ddc` contact post-init · `fcn.8004d224` caller of 80025084 · `fcn.80046618` level-filename builder · `fcn.8003d620` Region-A overlay loader · `fcn.8003f5b8` overlay_init_loader · `fcn.80060284`/`0x800602e0` GTE per-point leaf · `fcn.8004fa40` main shell state machine · `fcn.8003f938` object render loop · `fcn.80042c70` object spawner. Full call graph in the decompiled-C digest / `src_re*/`.

## Related
[[Symbols Index]] · [[Findings Index]] · [[Geometry pipeline]] · [[LEVEL.DAT object pipeline]] · [[Home]]
