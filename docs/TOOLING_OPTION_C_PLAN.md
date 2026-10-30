# Tooling Option C Plan

Option C means generalizing tooling for multi-entry insertion and object placement. The goal is not to build everything in one pass. The implementation should be phased, testable, and conservative.

## Purpose

Create a safe tooling path for cataloging, moving, appending, and eventually scripting LEVEL/DAT type-`0x3f` object placement across levels.

This plan builds on the reconstructed pipeline in [docs/LEVEL_OBJECT_PIPELINE.md](LEVEL_OBJECT_PIPELINE.md), especially:

- Type-`0x3f` entry layout.
- Runtime coordinate rule: file coordinate `<< 5`.
- Source-kind identity map.
- Relocation-aware append requirement.
- Runtime contact capacity and weak-Y contact behavior.

## Non-Goals

- Do not build ISOs as part of the planning phases.
- Do not patch DAT/BIN/CUE files during audit/catalog phases.
- Do not modify existing tools until the specific implementation phase starts.
- Do not start new reverse engineering.
- Do not decompile more functions.
- Do not change source data.
- Do not replace `tools/dat_reloc.py` as the trusted low-level relocation engine.
- Do not introduce a production naive-append path.

## Current Tool Inventory

| Tool | Current role | Option C disposition |
|------|--------------|----------------------|
| `tools/patch_level_entry.py` | Fixed-size type-`0x3f` entry coordinate patcher by entry index. | Keep as known-working reference; likely superseded by unified mover. |
| `tools/patch_level_grain.py` | Older grain-specific mover. | Likely obsolete for production once unified mover exists; retain as historical/reference until replaced. |
| `tools/list_level_pickups.py` | Lists decoded pickup-like entries. | Keep diagnostic; likely input/reference for unified catalog. |
| `tools/dat_reloc.py` | Trusted relocation-aware DAT append/rebuild engine. | Preserve as low-level engine; wrap it rather than replacing it. |
| `tools/add_level_entry.py` | Naive append path that shifts bytes without fixing baked offsets. | Obsolete/unsafe for relocation-bearing DATs; do not use for production. |
| `tools/list_level_grains.py` | Grain-specific listing. | Diagnostic only once unified catalog exists. |
| `tools/list_level_flik.py` | FLIK-specific listing. | Diagnostic only once unified catalog exists. |
| `tools/nearby_level_entries.py` | Proximity helper for existing entries. | Keep diagnostic; may inform catalog warnings. |
| `tools/catalog_level_grains.py` | Cross-level grain catalog helper. | Keep diagnostic/reference for cross-level catalog behavior. |
| `tools/build_markers_54_55_57.py` | Historical marker/sacrifice workflow. | Obsolete for production; entries `54..57` are real berries. |

Option C Phase 0 should verify this table against the repository before any implementation work.

## Phased Roadmap

### Option C Phase 0: Audit Current Tools And Assumptions

Status: complete. See [docs/TOOLING_OPTION_C_PHASE0_1_REPORT.md](TOOLING_OPTION_C_PHASE0_1_REPORT.md).

Goal: inventory current scripts and their limitations.

Include:

- `tools/patch_level_entry.py`
- `tools/patch_level_grain.py`
- `tools/list_level_pickups.py`
- `tools/dat_reloc.py`
- append/add-entry scripts, especially unsafe naive append paths
- scripts that should remain diagnostic only
- scripts that are obsolete or unsafe for production

Deliverable later: a short tool audit table with status, safe use, unsafe use, and replacement path.

No mutation in this phase.

### Option C Phase 1: Unified Type-0x3f Catalog Tool

Status: complete. Implemented `tools/catalog_type3f.py` and generated:

- `DAT/type3f_catalog.csv`
- `DAT/type3f_catalog.md`
- `DAT/type3f_catalog_level01.csv`
- `DAT/type3f_catalog_level01.md`

See [docs/TOOLING_OPTION_C_PHASE0_1_REPORT.md](TOOLING_OPTION_C_PHASE0_1_REPORT.md).

Goal: create or upgrade a catalog tool that lists all type-`0x3f` entries with decoded identity.

Required output columns:

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

Requirements:

- Work across all extracted `DAT/LEVEL*_LEVEL*.DAT` files, not just LEVEL01.
- Decode known LEVEL01 identities where evidence exists.
- Mark level-specific or uncertain identities with `LIKELY`, `UNKNOWN`, or `TODO`.
- Warn on kinds `0x2c/0x2d`, checkpoint kinds, unusual counts, and entries whose movement could affect production assumptions.
- No mutation in this phase.

### Option C Phase 2: Unified Fixed-Size Mover

Status: complete. Implemented `tools/move_type3f_entry.py`.

See [docs/TOOLING_OPTION_C_PHASE2_REPORT.md](TOOLING_OPTION_C_PHASE2_REPORT.md).

Goal: create one safe tool for moving existing type-`0x3f` entries.

Features:

- Select by file plus raw entry index.
- Select by decoded identity only when unambiguous.
- Apply `dx/dy/dz`.
- Preserve source kind.
- Make no size changes.
- Verify only intended coordinate bytes changed.
- Print before/after bytes.
- Optionally emit a patch report.

This replaces ad hoc one-off entry patching while preserving the fixed-size safety model.

### Option C Phase 3: Relocation-Aware Append / Multi-Entry Insertion Wrapper

Status: complete. Implemented `tools/insert_type3f_entries.py`.

See [docs/TOOLING_OPTION_C_PHASE3_REPORT.md](TOOLING_OPTION_C_PHASE3_REPORT.md).

Goal: generalize `tools/dat_reloc.py` into a safer user-facing insertion workflow.

Features:

- Append one or more type-`0x3f` entries.
- Clone an existing entry with deltas.
- Append from explicit 0x10-byte entry bytes.
- Append from structured args:
  - kind
  - X/Y/Z
  - optional unknown bytes `+0x0d..0x0f`
- Update internal DAT relocation offsets.
- Verify all old entries remain byte-identical except expected shifted relocation fields.
- Verify relocation fields were updated.
- Verify embedded image after rebuild if requested.

Must preserve:

- `tools/dat_reloc.py` as the trusted low-level relocation engine.
- No naive append path for production.

### Option C Phase 4: Declarative Placement Spec

Status: complete. Implemented `tools/apply_level_placements.py`.

See [docs/TOOLING_OPTION_C_PHASE4_REPORT.md](TOOLING_OPTION_C_PHASE4_REPORT.md).

Goal: support a small human-editable placement spec file.

Example:

```yaml
level: LEVEL01
source_dat: DAT/LEVEL01_LEVEL.DAT
operations:
  - op: move
    entry: 56
    dx: 512
    dy: -256
    dz: 0
  - op: append_clone
    clone_entry: 64
    dx: 512
    dy: 0
    dz: 0
  - op: append_new
    kind: 0x29
    x: 4928
    y: -50
    z: -3655
```

This phase should come only after Phases 1-3 are stable. The spec runner should call the catalog, mover, and insertion wrapper instead of duplicating low-level DAT logic.

### Option C Phase 5: Rebuild Integration

Status: complete. Implemented `tools/rebuild_with_patched_dat.py`.

See [docs/TOOLING_OPTION_C_PHASE5_REPORT.md](TOOLING_OPTION_C_PHASE5_REPORT.md).

Goal: optional wrapper to stage patched DATs into `REBUILD/files`, run `mkpsxiso`, verify embedded files, and restore workspace.

Do not implement until patching tools are stable. This phase should be a wrapper around proven file mutation tools, not a place to introduce new DAT patching behavior.

### Option C Phase 6: Cross-Level Validation

Status: complete. Implemented `tools/validate_levels_phase6.py`.

See [docs/TOOLING_OPTION_C_PHASE6_REPORT.md](TOOLING_OPTION_C_PHASE6_REPORT.md).

Goal: run catalog plus non-mutating validation across levels first, then test one level at a time.

Must include:

- Identify which levels have type-`0x3f`.
- Identify relocation-bearing DATs.
- Identify unusual counts.
- Avoid assuming the LEVEL01 mapping applies blindly to every level without evidence.
- Record level-specific warnings before enabling mutation workflows.

## Data Safety Rules

- Treat original disc images and pristine extracted DATs as read-only baselines.
- For fixed-size moves, change only `x/y/z` fields unless an implementation phase explicitly allows more.
- Preserve source kind for existing pickups.
- Never use naive byte-shift append on relocation-bearing DATs.
- Use relocation-aware append/insertion only through the trusted relocation engine.
- Keep entries `54..57` as real berry entries; do not use them as sacrifice slots.
- Keep uncertainty visible in tool output.
- Do not silently apply LEVEL01 identity assumptions to other levels.

## Verification Rules

Every mutating phase after Phase 1 should verify:

- Input file hash or size when practical.
- Type-`0x3f` record offset and count before mutation.
- Intended entry offsets.
- Before/after bytes for changed entries.
- That source kind is preserved unless intentionally creating a new entry.
- That fixed-size moves changed only coordinate bytes.
- That append/insertion increased count and size as expected.
- That old entries remain byte-identical after append/insertion, apart from relocation fields that must change.
- That relocation fields were adjusted by the expected delta.
- That rebuilt/staged embedded files match expected patched bytes if rebuild integration is requested.

## Test Strategy

Phase 0:

- Read scripts and document current behavior.
- No file mutation.

Phase 1:

- Run catalog against all extracted `DAT/LEVEL*_LEVEL*.DAT`.
- Compare LEVEL01 output against [docs/LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md).
- Add fixture-style checks for known LEVEL01 entries if the tool structure supports tests.

Phase 2:

- Use a temporary copy only.
- Move one known entry by small deltas.
- Verify only 12 coordinate bytes changed.
- Verify kind and unknown bytes are unchanged.
- Verify catalog before/after reports expected runtime coordinates.

Phase 3:

- Use a temporary copy only.
- Append one cloned entry and one explicit new entry.
- Verify count, size, old entries, and relocation deltas.
- Compare relocation behavior against `tools/dat_reloc.py`.

Phase 4:

- Parse a declarative spec without mutation first.
- Then apply to temporary copies and compare output to equivalent Phase 2/3 commands.

Phase 5:

- Stage only known-good patched DATs.
- Verify embedded bytes after rebuild.
- Restore workspace after each run.

Phase 6:

- Start non-mutating across all levels.
- Test one level at a time after catalog warnings are reviewed.

## Proposed Command Examples

Phase 0 audit examples:

```bash
python tools/list_level_pickups.py DAT/LEVEL01_LEVEL.DAT
python tools/list_level_grains.py DAT/LEVEL01_LEVEL.DAT
```

Phase 1 catalog examples:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/catalog_type3f.py DAT/LEVEL01_LEVEL.DAT --validate-level01 \
  --csv DAT/type3f_catalog_level01.csv --md DAT/type3f_catalog_level01.md
PYTHONDONTWRITEBYTECODE=1 python tools/catalog_type3f.py 'DAT/LEVEL*_LEVEL*.DAT' --validate-level01 \
  --csv DAT/type3f_catalog.csv --md DAT/type3f_catalog.md
PYTHONDONTWRITEBYTECODE=1 python tools/catalog_type3f.py 'DAT/LEVEL*_LEVEL*.DAT' --no-write
```

Phase 2 mover examples:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py DAT/LEVEL01_LEVEL.DAT --entry 56 --dx 512 --dy -256 --dz 0
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py DAT/LEVEL01_LEVEL.DAT --identity "FLIK F" --dy -1
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py DAT/LEVEL01_LEVEL.DAT --entry 56 --dx 512 --dy -256 --dz 0 \
  --write --out /tmp/level01_entry56_move_test.DAT
```

Phase 3 insertion examples:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py DAT/LEVEL01_LEVEL.DAT --append-clone 64:512:0:0
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py DAT/LEVEL01_LEVEL.DAT --append-new 0x29:4928:-50:-3655
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py DAT/LEVEL01_LEVEL.DAT \
  --append-clone 64:512:0:0 --append-new 0x2a:5000:-50:-3600 \
  --entry-bytes 40130000ceffffffb9f1ffff29000000 \
  --write --out /tmp/level01_type3f_multi_append_test.DAT
```

Phase 4 spec example:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/apply_level_placements.py placements/level01_tokens.yaml
PYTHONDONTWRITEBYTECODE=1 python tools/apply_level_placements.py placements/level01_tokens.yaml \
  --write --out /tmp/level01_placements_test.DAT \
  --report /tmp/level01_placements_test.md
```

Phase 6 cross-level validation examples:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/validate_levels_phase6.py
PYTHONDONTWRITEBYTECODE=1 python tools/validate_levels_phase6.py --no-write
PYTHONDONTWRITEBYTECODE=1 python tools/regress_validate_levels_phase6.py
```

## Known Risks

- Relocation-bearing DATs: byte shifts require relocation repair.
- Weak-Y auto-collect: Y is underweighted in contact math, so large vertical moves can still collect.
- 64-contact-record capacity: runtime contact array is fixed at 64 records and allocator has no full-array escape.
- Phase gate `(kind & 3)`: generic visible construction is gated by `[0x800910a4]`.
- Level-specific source-kind differences: LEVEL01 mapping is proven for LEVEL01, not every level.
- Unknown `0x2c/0x2d`: handlers are token-like, but they are not production-tested in LEVEL01.
- Checkpoint semantics are not fully proven beyond the first-fire path.
- Unknown bytes `+0x0d..0x0f` must be preserved for clones and explicit about defaults for new entries.

## Recommended Immediate Next Implementation Prompt

```text
Execute Option C Phase 0 / Phase 1 only.

Read docs/LEVEL_OBJECT_PIPELINE.md, docs/TOOLING_OPTION_C_PLAN.md,
docs/TOOLING.md, docs/LEVEL01_TYPE3F_MAP.md, and the current tools first.

Do not mutate DAT/BIN/CUE files.
Do not build ISOs.
Do not modify tools outside the Phase 0/1 catalog scope.

Deliver:
1. Tool audit table.
2. Unified non-mutating type-0x3f catalog tool or upgrade.
3. LEVEL01 catalog output checked against docs/LEVEL01_TYPE3F_MAP.md.
4. Cross-level non-mutating summary for DAT/LEVEL*_LEVEL*.DAT.
5. Warnings and unresolved assumptions before Phase 2.
```
