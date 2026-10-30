# Option C Phase 3 Report

Scope executed:

- Phase 3: safe user-facing relocation-aware type-`0x3f` append wrapper.

Scope not executed:

- No relocation logic rewrite.
- No ISO build.
- No Phase 2 mover behavior changes.
- No DAT mutation unless `--write --out` is provided.

## Tool

New tool:

- `tools/insert_type3f_entries.py`

This is a wrapper around the trusted `tools/dat_reloc.py` relocation engine. It builds requested 0x10-byte type-`0x3f` entries, then calls `dat_reloc.build_reloc_insert()` for each append step using the current end of the type-`0x3f` record as the insertion point.

The wrapper does not reimplement the relocation scan or fix-up logic.

## Supported Append Forms

Append clone:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py \
  DAT/LEVEL01_LEVEL.DAT --append-clone 64:512:0:0
```

Append new from structured args:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py \
  DAT/LEVEL01_LEVEL.DAT --append-new 0x29:4928:-50:-3655
```

Append explicit 16-byte entry hex:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py \
  DAT/LEVEL01_LEVEL.DAT --entry-bytes 40130000ceffffffb9f1ffff29000000
```

Multi-entry append in one operation:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py \
  DAT/LEVEL01_LEVEL.DAT \
  --append-clone 64:512:0:0 \
  --append-new 0x2a:5000:-50:-3600 \
  --entry-bytes 40130000ceffffffb9f1ffff29000000
```

Write a copied DAT and report:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py \
  DAT/LEVEL01_LEVEL.DAT \
  --append-clone 64:512:0:0 \
  --append-new 0x2a:5000:-50:-3600 \
  --entry-bytes 40130000ceffffffb9f1ffff29000000 \
  --write --out /tmp/level01_type3f_multi_append_test.DAT \
  --report /tmp/level01_type3f_multi_append_test.md
```

Compatibility forms are also supported:

- `--clone-entry N --dx DX --dy DY --dz DZ`
- `--kind KIND --x X --y Y --z Z [--unk0d B --unk0e B --unk0f B]`

## Conservative Defaults

- Dry-run by default.
- `--write` is required to write a DAT.
- `--out` is required with `--write`.
- In-place output is refused.
- Every appended entry must be exactly 16 bytes.
- Risky appended kinds require explicit override flags:
  - kind `0x30` requires `--allow-checkpoint`
  - kinds `0x2c/0x2d` require `--allow-token-like`
  - unknown/unsupported kinds, including `0x31`, require `--allow-unknown`
- Output size must be input size plus `0x10 * appended_count`.
- Type-`0x3f` count must increase by exactly appended count.
- Existing type-`0x3f` entries must remain byte-identical.
- Appended entry bytes must match requested bytes exactly.
- Each append step must report relocation fields processed by `tools/dat_reloc.py`.
- Each append step must report at least one bumped relocation field.
- Final relocation-site scan count must match the per-step relocation report count.

## Verification Performed

Syntax:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m py_compile tools/insert_type3f_entries.py
```

Regression command:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/regress_type3f_insert.py
```

The regression script writes only to a temporary directory. It checks:

- compile validity;
- invalid short explicit-entry hex fails with a nonzero exit;
- checkpoint append without `--allow-checkpoint` fails with a nonzero exit;
- multi-entry dry-run succeeds without writing a DAT;
- multi-entry write-to-temp succeeds with expected output size and report fields.

Single-entry dry-runs:

- clone append from entry `64` with `dx=512`
- structured append-new kind `0x29`
- explicit 16-byte hex append

All produced:

- old count `70`
- new count `71`
- size `332824 -> 332840`
- relocation fields `1248`, bumped `1248`
- no DAT written

Multi-entry dry-run:

- append clone `64:512:0:0`
- append new `0x2a:5000:-50:-3600`
- append explicit bytes `40130000ceffffffb9f1ffff29000000`

Result:

- old count `70`
- new count `73`
- size `332824 -> 332872`
- step insert offsets `0x468`, `0x478`, `0x488`
- each step processed `1248` relocation fields, bumped `1248`, and rescanned `1248`
- no DAT written

Write-to-copy test:

- wrote `/tmp/level01_type3f_multi_append_test.DAT`
- wrote report `/tmp/level01_type3f_multi_append_test.md`
- output catalog parsed as type-`0x3f` count `73`
- independent byte check passed:
  - file size is original + `0x30`
  - count is `73`
  - original 70 type-`0x3f` entries are byte-identical
  - appended entries 70/71/72 match requested bytes
- `tools/dat_reloc.py --scan` on the output still found `1248` relocation sites.
- `tools/regress_type3f_insert.py` passed.

## Files Written

Intentional repository files:

- `tools/insert_type3f_entries.py`
- `tools/regress_type3f_insert.py`
- `docs/TOOLING_OPTION_C_PHASE3_REPORT.md`

Temporary verification files:

- `/tmp/level01_type3f_multi_append_test.DAT`
- `/tmp/level01_type3f_multi_append_test.md`

## Unresolved Before Phase 4

- This tool appends to the end of the single type-`0x3f` record; arbitrary insertion position is not exposed.
- Relocation-aware behavior remains delegated to `tools/dat_reloc.py`.
- Rebuild/image staging remains Phase 5.
- Declarative placement specs remain Phase 4.
- Runtime `ContactRecord` capacity remains a gameplay constraint for heavy additions.
