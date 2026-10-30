# Option C Phase 4 Report

Scope executed:

- Phase 4: declarative placement spec runner for type-`0x3f` object placement.

Scope not executed:

- No ISO build.
- No rebuild staging.
- No relocation logic rewrite.
- No Phase 2 mover behavior changes.
- No workspace DAT/BIN/CUE mutation.

## Tool

New tool:

- `tools/apply_level_placements.py`

The tool accepts a small YAML-like or JSON placement spec, applies operations in
order in memory, and writes a DAT only when both `--write` and `--out` are
provided. Dry-run is the default.

The implementation uses the Phase 2 mover verification functions for fixed-size
coordinate moves and the Phase 3 append wrapper functions for relocation-aware
appends. It does not duplicate or replace `tools/dat_reloc.py` relocation logic.

## Supported Operations

Move existing entry:

```yaml
operations:
  - op: move
    entry: 56
    dx: 512
    dy: -256
    dz: 0
```

Append clone:

```yaml
operations:
  - op: append_clone
    clone_entry: 64
    dx: 512
    dy: 0
    dz: 0
```

Append new structured entry:

```yaml
operations:
  - op: append_new
    kind: 0x29
    x: 4928
    y: -50
    z: -3655
```

Append explicit 16-byte entry:

```yaml
operations:
  - op: entry_bytes
    entry_bytes: 40130000ceffffffb9f1ffff29000000
```

Risk overrides are available globally on the command line, or per operation in
the spec:

- `allow_checkpoint: true`
- `allow_token_like: true`
- `allow_unknown: true`

## Example

```yaml
level: LEVEL01
source_dat: DAT/LEVEL01_LEVEL.DAT
operations:
  - op: move
    entry: 56
    dx: 1
    dy: 0
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
  - op: entry_bytes
    entry_bytes: 40130000ceffffffb9f1ffff29000000
```

Dry-run:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/apply_level_placements.py /tmp/level01_phase4_spec.yaml
```

Write a copied DAT and report:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/apply_level_placements.py /tmp/level01_phase4_spec.yaml \
  --write --out /tmp/level01_phase4_spec_test.DAT \
  --report /tmp/level01_phase4_spec_test.md
```

## Verification Performed

Syntax:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m py_compile \
  tools/insert_type3f_entries.py \
  tools/regress_type3f_insert.py \
  tools/apply_level_placements.py
```

Phase 3 hardening regression:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/regress_type3f_insert.py
```

Phase 4 dry-run on the example spec:

- move entry `56` by `dx=1`;
- append clone of entry `64`;
- append structured kind `0x29`;
- append explicit 16-byte kind `0x29` entry;
- no DAT written.

Phase 4 write-to-copy test:

- wrote `/tmp/level01_phase4_spec_test.DAT`;
- wrote `/tmp/level01_phase4_spec_test.md`;
- final size `332872`;
- type-`0x3f` count `70 -> 73`;
- catalog parse of copied DAT reported type-`0x3f` count `73`;
- relocation scan of copied DAT reported `1248` relocation sites.

## Files Written

Intentional repository files:

- `tools/apply_level_placements.py`
- `docs/TOOLING_OPTION_C_PHASE4_REPORT.md`

Related Phase 3 hardening files:

- `tools/insert_type3f_entries.py`
- `tools/regress_type3f_insert.py`
- `docs/TOOLING_OPTION_C_PHASE3_REPORT.md`

Temporary verification files:

- `/tmp/level01_phase4_spec.yaml`
- `/tmp/level01_phase4_spec_test.DAT`
- `/tmp/level01_phase4_spec_test.md`

## Unresolved Before Phase 5

- The spec runner does not stage files into `REBUILD/files`.
- The spec runner does not run `mkpsxiso`.
- Embedded image verification remains Phase 5.
- Cross-level production use still needs level-by-level catalog review.
- Runtime `ContactRecord` capacity remains a gameplay constraint for heavy additions.
