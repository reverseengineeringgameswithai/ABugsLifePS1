# Option C Phase 2 Report

Scope executed:

- Phase 2: unified fixed-size type-`0x3f` mover.

Scope not executed:

- No append/insertion wrapper.
- No ISO build.
- No relocation logic changes.
- No source-kind mutation.
- No checkpoint, unknown, or token-like movement by default.

## Tool

New tool:

- `tools/move_type3f_entry.py`

The mover uses the Phase 1 catalog implementation (`tools/catalog_type3f.py`) as its safety layer. It reads the input DAT, catalogs type-`0x3f` entries, selects entries by raw index or unambiguous decoded identity, applies fixed-size coordinate deltas, and verifies that only intended coordinate bytes changed.

## Conservative Defaults

- Dry-run by default.
- `--write` is required before any output DAT is written.
- `--out` is required with `--write`.
- In-place writes are refused.
- At least one of `--dx/--dy/--dz` must be nonzero.
- Source kind and unknown bytes `+0x0c..0x0f` are preserved.
- DAT size and top-level record structure must remain unchanged.
- Only selected X/Y/Z coordinate byte ranges may change.

## Selection

Supported selectors:

- `--entry N`
- `--entry N M K`
- `--entry N,M,K`
- `--identity TEXT`

Identity selection must resolve to exactly one catalog row. Ambiguous identity matches are refused and list candidate entries.

## Risk Gates

Default behavior refuses:

- checkpoint/trigger kind `0x30`
- token-like kinds `0x2c/0x2d`
- unknown or unsupported kinds, including observed cross-level kind `0x31`

Override flags:

- `--allow-checkpoint`
- `--allow-token-like`
- `--allow-unknown`

These flags only permit the selected risky category to pass the safety gate. They do not imply `--write`.

## Command Examples

Dry-run a safe grain move:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py \
  DAT/LEVEL01_LEVEL.DAT --entry 0 --dx 1 --dy -2 --dz 3
```

Write a copied DAT and Markdown patch report:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py \
  DAT/LEVEL01_LEVEL.DAT --entry 0 --dx 1 --dy -2 --dz 3 \
  --write --out /tmp/level01_entry0_move_test.DAT \
  --report /tmp/level01_entry0_move_test.md
```

Move by unambiguous identity:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py \
  DAT/LEVEL01_LEVEL.DAT --identity "FLIK F" --dy -1
```

Explicitly review a risky token-like entry without writing:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py \
  DAT/LEVEL02_LEVEL.DAT --entry 56 --dx 1 --allow-token-like
```

## Verification Performed

Syntax:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m py_compile tools/move_type3f_entry.py
```

Safe dry-run:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py \
  DAT/LEVEL01_LEVEL.DAT --entry 0 --dx 1 --dy -2 --dz 3
```

Result:

- selected entry `0`
- kind `0x14`
- old XYZ `(-8526, -3488, 4544)`
- new XYZ `(-8525, -3490, 4547)`
- no DAT written

Write-to-copy test:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py \
  DAT/LEVEL01_LEVEL.DAT --entry 0 --dx 1 --dy -2 --dz 3 \
  --write --out /tmp/level01_entry0_move_test.DAT \
  --report /tmp/level01_entry0_move_test.md
```

Result:

- wrote `/tmp/level01_entry0_move_test.DAT`
- size remained `332824` bytes
- report written to `/tmp/level01_entry0_move_test.md`
- follow-up catalog parse succeeded

Risk-gate checks:

- `DAT/LEVEL01_LEVEL.DAT --entry 67 --dx 1` refused kind `0x30`; requires `--allow-checkpoint`.
- `DAT/LEVEL02_LEVEL.DAT --entry 56 --dx 1` refused kind `0x2c`; requires `--allow-token-like`.
- `DAT/LEVEL02_LEVEL1.DAT --entry 65 --dx 1` refused kind `0x31`; requires `--allow-unknown`.
- Override dry-runs for `0x2c` and `0x31` succeeded without writing.

## Files Written

Intentional repository files:

- `tools/move_type3f_entry.py`
- `docs/TOOLING_OPTION_C_PHASE2_REPORT.md`

Temporary verification files:

- `/tmp/level01_entry0_move_test.DAT`
- `/tmp/level01_entry0_move_test.md`

## Unresolved Before Phase 3

- The mover does not append and does not adjust relocation-bearing offsets; Phase 3 remains responsible for insertion wrappers.
- Kind `0x31` remains unknown and requires `--allow-unknown`.
- Kinds `0x2c/0x2d` remain token-like but not LEVEL01 production-tested and require `--allow-token-like`.
- Checkpoint movement requires `--allow-checkpoint`; semantics are still not fully proven.
- The tool allows safe source-kind classes outside LEVEL01 by source-kind decode only; level-specific behavior remains unverified.
- Heavy additions still need later capacity analysis because the runtime `ContactRecord` array has 64 slots.
