# Option C Phase 0 / Phase 1 Report

Scope executed:

- Phase 0: audit current tools and assumptions.
- Phase 1: create a unified non-mutating type-`0x3f` catalog tool.

Scope not executed:

- No DAT/BIN/CUE mutation.
- No ISO builds.
- No fixed-size mover implementation.
- No append/insertion wrapper implementation.
- No relocation logic changes.
- No new reverse engineering.

## Phase 0 Tool Audit

| Tool | Current role | Safe use now | Unsafe / obsolete use | Phase 2+ disposition |
|------|--------------|--------------|------------------------|----------------------|
| `tools/patch_level_entry.py` | General fixed-size coordinate patcher for existing type-`0x3f` entries. | Known-working reference for coordinate-only moves on copied DATs. | Mutating; not part of Phase 0/1 runs. Does not select by decoded identity. | Supersede with unified mover in Phase 2. |
| `tools/patch_level_grain.py` | Older grain-specific Y mover. | Historical/reference and narrow grain workflow. | Mutating and grain-only. | Diagnostic/reference after Phase 2. |
| `tools/list_level_pickups.py` | Read-only pickup/source-kind listing. | Diagnostic reference for kind labels and counters. | Older labels call `0x21..0x24` FLIK trigger/marker actions; current docs identify them as berries/power-ups. | Superseded for catalog use by `tools/catalog_type3f.py`. |
| `tools/dat_reloc.py` | Relocation-aware scan and append/insert engine. | Trusted low-level relocation engine; scan mode is diagnostic. | Mutation modes are Phase 3+, not Phase 0/1. | Preserve and wrap later; do not replace. |
| `tools/add_level_entry.py` | Naive type-`0x3f` clone append. | Historical reference only. | Unsafe for relocation-bearing DATs; leaves stale baked offsets. | Keep obsolete; do not use for production. |
| `tools/list_level_grains.py` | Read-only grain listing and patch-byte suggestions. | Diagnostic only. | Grain-only and patch-suggestion oriented. | Superseded by unified catalog for object inventory. |
| `tools/list_level_flik.py` | Read-only listing for older FLIK/marker candidates. | Historical diagnostic. | Uses stale `0x21..0x24` FLIK-marker framing. | Superseded by unified catalog. |
| `tools/nearby_level_entries.py` | Read-only spatial-neighbor helper. | Diagnostic for proximity review. | Has a heuristic all-record mode; not an identity catalog. | Keep diagnostic; may inform later warnings. |
| `tools/catalog_level_grains.py` | Cross-level grain CSV/Markdown catalog. | Diagnostic/reference for report writing patterns. | Grain-only. | Superseded by unified catalog for type-`0x3f`. |
| `tools/build_markers_54_55_57.py` | Historical fixed-count marker-sacrifice builder. | Historical only. | Obsolete production path; entries `54..57` are real berries. | Do not use for production. |
| `tools/compare_level01_rams.py` and other RAM/state helpers | Runtime diagnostic helpers. | Out of scope for Option C Phase 0/1 cataloging. | Not DAT placement tools. | Leave unchanged. |

## Phase 1 Catalog Tool

New tool:

- `tools/catalog_type3f.py`

It is non-mutating and writes only report files. Required output columns are present in the CSV:

- file
- top-level DAT record offset
- raw entry index
- entry offset
- X/Y/Z
- source kind
- decoded identity
- movement-safe status
- known warnings
- runtime X/Y/Z
- notes

The tool decodes the confirmed LEVEL01 map exactly for `DAT/LEVEL01_LEVEL.DAT`. For other files, it decodes by known source-kind behavior and marks the result as level-specific / unverified in notes.

## Command Examples

Validate pristine LEVEL01 and write a focused report:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/catalog_type3f.py \
  DAT/LEVEL01_LEVEL.DAT \
  --validate-level01 \
  --csv DAT/type3f_catalog_level01.csv \
  --md DAT/type3f_catalog_level01.md
```

Catalog the available DAT corpus:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/catalog_type3f.py \
  'DAT/LEVEL*_LEVEL*.DAT' \
  --validate-level01 \
  --csv DAT/type3f_catalog.csv \
  --md DAT/type3f_catalog.md
```

Print only summary without writing reports:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/catalog_type3f.py \
  'DAT/LEVEL*_LEVEL*.DAT' \
  --no-write
```

## Catalog Outputs Written

- `DAT/type3f_catalog.csv`
- `DAT/type3f_catalog.md`
- `DAT/type3f_catalog_level01.csv`
- `DAT/type3f_catalog_level01.md`

The full corpus CSV contains 3661 type-`0x3f` entries across 55 files with entries. Files with no type-`0x3f` record are represented in the Markdown summary.

## LEVEL01 Validation

`DAT/LEVEL01_LEVEL.DAT` passed the confirmed 70-entry map:

- type-`0x3f` record offset: `0x000004`
- entry count: `70`
- entries `0..49`: kind `0x14`
- entries `50..53`: kinds `0x10..0x13`
- entries `54..57`: kinds `0x22,0x23,0x21,0x24`
- entries `58..66`: kinds `0x29..0x2b` in the confirmed token arrangement
- entries `67..69`: kind `0x30`

Catalog cautions still apply:

- `0x30` checkpoint/trigger semantics are not fully proven.
- `0x21..0x24` are real berries/power-ups and must preserve kind.

## Cross-Level Summary

Available baseline-style DAT files:

| file | type-`0x3f` entries | source kinds seen |
|------|--------------------:|-------------------|
| `DAT/LEVEL00_LEVEL.DAT` | 0 | - |
| `DAT/LEVEL01_LEVEL.DAT` | 70 | `0x10,0x11,0x12,0x13,0x14,0x21,0x22,0x23,0x24,0x29,0x2a,0x2b,0x30` |
| `DAT/LEVEL01_LEVEL1.DAT` | 62 | `0x10,0x11,0x12,0x13,0x14,0x22,0x23,0x2a,0x2d` |
| `DAT/LEVEL02_LEVEL.DAT` | 60 | `0x10,0x11,0x12,0x13,0x14,0x23,0x2c` |
| `DAT/LEVEL02_LEVEL1.DAT` | 70 | `0x10,0x11,0x12,0x13,0x14,0x22,0x23,0x29,0x2b,0x30,0x31` |
| `DAT/LEVEL03_LEVEL.DAT` | 69 | `0x10,0x11,0x12,0x13,0x14,0x23,0x2b,0x2c,0x30,0x31` |
| `DAT/LEVEL03_LEVEL1.DAT` | 61 | `0x10,0x11,0x12,0x13,0x14,0x2b,0x2c` |
| `DAT/LEVEL04_LEVEL.DAT` | 47 | `0x10,0x11,0x12,0x13,0x14,0x2a,0x2b,0x2c,0x2d,0x30,0x31` |
| `DAT/LEVEL04_LEVEL1.DAT` | 6 | `0x10,0x11,0x12,0x13,0x22,0x23` |
| `DAT/LEVEL05_LEVEL.DAT` | 74 | `0x10,0x11,0x12,0x13,0x14,0x29,0x2a,0x2b,0x2c,0x30,0x31` |
| `DAT/LEVEL05_LEVEL1.DAT` | 69 | `0x10,0x11,0x12,0x13,0x14,0x22,0x23,0x29,0x2a,0x30,0x31` |
| `DAT/LEVEL06_LEVEL.DAT` | 60 | `0x10,0x11,0x12,0x13,0x14,0x21,0x22,0x29,0x2b` |
| `DAT/LEVEL06_LEVEL1.DAT` | 7 | `0x29,0x2b` |
| `DAT/LEVEL07_LEVEL.DAT` | 77 | `0x10,0x11,0x12,0x13,0x14,0x22,0x29,0x2a,0x2b,0x2c,0x30,0x31` |
| `DAT/LEVEL07_LEVEL1.DAT` | 62 | `0x10,0x11,0x12,0x13,0x14,0x23,0x2b,0x2c` |
| `DAT/LEVEL08_LEVEL.DAT` | 56 | `0x10,0x11,0x12,0x13,0x14,0x22,0x23` |
| `DAT/LEVEL08_LEVEL1.DAT` | 0 | - |
| `DAT/LEVEL09_LEVEL.DAT` | 74 | `0x10,0x11,0x12,0x13,0x14,0x29,0x2a,0x2b,0x2d,0x30,0x31` |
| `DAT/LEVEL10_LEVEL.DAT` | 74 | `0x10,0x11,0x12,0x13,0x14,0x21,0x22,0x23,0x24,0x29,0x2a,0x2b,0x30,0x31` |

The broader `DAT/LEVEL*_LEVEL*.DAT` run also includes many LEVEL01 experiment/test DATs already present in the workspace. Those are included in the generated corpus reports but should not be treated as pristine level baselines.

## Unresolved Assumptions Before Phase 2

- Source-kind `0x31` appears in cross-level catalogs but is not yet named in the unified identity map.
- Source kinds `0x2c/0x2d` are token-like in handler code but not LEVEL01 production-tested.
- Checkpoint/trigger movement remains risky because only first-fire behavior is confirmed.
- Movement-safe labels outside LEVEL01 are source-kind based; level-specific identity is explicitly unverified.
- Relocation-bearing DAT identification remains a later validation concern; Phase 1 did not change or rescan relocation logic.
- The 64-record runtime `ContactRecord` capacity still constrains heavy object additions in later phases.
- Weak-Y contact math still makes large vertical moves risky.

## Stale-Doc Warnings Carried Forward

- `docs/DAT_FORMAT_AND_RELOCATION.md` still contains an older "awaiting in-game result" append note before the later confirmed append section.
- `docs/COORDINATE_MODDING.md` still contains an older note that FLIK letter spawn coords are not mapped, superseded by later FLIK mapping and phase outputs.
