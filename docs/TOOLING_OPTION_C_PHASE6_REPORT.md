# Option C Phase 6 Report

Scope executed:

- Phase 6: cross-level non-mutating validation of type-`0x3f` placement DATs.

Scope not executed:

- No DAT/BIN/CUE mutation.
- No relocation logic rewrite.
- No per-level mutation workflow enabled.
- No new reverse engineering or decompilation.
- No changes to Phase 2-5 mutation behavior.

## Tool

New tool:

- `tools/validate_levels_phase6.py`

The tool sweeps the pristine extracted `DAT/LEVEL00..LEVEL10_LEVEL.DAT` files,
reuses the Phase 1 catalog decoder (`tools/catalog_type3f.py`) and the trusted
relocation scanner (`tools/dat_reloc.py`), and emits a cross-level report plus a
per-level warning list. It never writes DAT/BIN/CUE inputs; it only writes a CSV
and Markdown report (default `DAT/phase6_cross_level.csv` / `.md`), and supports
`--no-write` for a stdout-only run.

For each level it records:

- whether a type-`0x3f` placement record is present, and its offset;
- the type-`0x3f` entry count and its delta from the LEVEL01 baseline of 70;
- the relocation site count (relocation-bearing status);
- source kinds present, split into unknown, caution (`0x2c/0x2d/0x30`), and real
  berry (`0x21..0x24`) groups;
- the catalog warnings, plus a standing reminder that the confirmed identity map
  is LEVEL01-only.

## Example

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/validate_levels_phase6.py
PYTHONDONTWRITEBYTECODE=1 python tools/validate_levels_phase6.py --no-write
PYTHONDONTWRITEBYTECODE=1 python tools/validate_levels_phase6.py \
  'DAT/LEVEL0[1-3]_LEVEL.DAT' --csv /tmp/p6.csv --md /tmp/p6.md
```

## Cross-Level Findings

| file | type-0x3f | count | vs 70 | reloc sites | unknown | caution | berry |
|---|:--:|---:|:--:|---:|---|---|---|
| `LEVEL00_LEVEL.DAT` | no | - | n/a | n/a | - | - | - |
| `LEVEL01_LEVEL.DAT` | yes | 70 | baseline | 1248 | - | 0x30 | 0x21,0x22,0x23,0x24 |
| `LEVEL02_LEVEL.DAT` | yes | 60 | -10 | 400 | - | 0x2c | 0x23 |
| `LEVEL03_LEVEL.DAT` | yes | 69 | -1 | 989 | 0x31 | 0x2c,0x30 | 0x23 |
| `LEVEL04_LEVEL.DAT` | yes | 47 | -23 | 2346 | 0x31 | 0x2c,0x2d,0x30 | - |
| `LEVEL05_LEVEL.DAT` | yes | 74 | +4 | 2436 | 0x31 | 0x2c,0x30 | - |
| `LEVEL06_LEVEL.DAT` | yes | 60 | -10 | 1386 | - | - | 0x21,0x22 |
| `LEVEL07_LEVEL.DAT` | yes | 77 | +7 | 1586 | 0x31 | 0x2c,0x30 | 0x22 |
| `LEVEL08_LEVEL.DAT` | yes | 56 | -14 | 2002 | - | - | 0x22,0x23 |
| `LEVEL09_LEVEL.DAT` | yes | 74 | +4 | 1322 | 0x31 | 0x2d,0x30 | - |
| `LEVEL10_LEVEL.DAT` | yes | 74 | +4 | 1156 | 0x31 | 0x30 | 0x21,0x22,0x23,0x24 |

Key observations:

- **type-0x3f presence:** `LEVEL01..LEVEL10` all carry exactly one type-`0x3f`
  record at offset `0x4`. `LEVEL00_LEVEL.DAT` has none and is structurally
  different (94,044 bytes); it is a non-placement DAT and is out of scope for the
  placement tooling. The relocation walk does not apply to it and the tool
  records that as a non-applicable scan, not a failure.
- **relocation-bearing:** every placement-bearing level is relocation-bearing
  (400-2436 sites). This confirms the plan's rule that naive byte-shift append is
  unsafe on every real level; only the relocation-aware insertion path may be
  used.
- **unusual counts:** only LEVEL01 matches the baseline of 70. Counts range from
  47 (LEVEL04) to 77 (LEVEL07). The count is genuinely level-specific and the
  LEVEL01 70-entry map must not be assumed elsewhere.
- **unknown source kind `0x31`:** appears in LEVEL03, 04, 05, 07, 09, and 10. It
  is not in the known generic identity map and has no decoded handler evidence
  yet. Treat as UNKNOWN; do not move or clone it for production without
  per-level reverse-engineering evidence.
- **caution kinds:** `0x2c`/`0x2d` (token-like, not LEVEL01 production-tested)
  and `0x30` (checkpoint/trigger candidate) appear across most levels. LEVEL01
  itself has no `0x2c/0x2d`, so behavior of those kinds cannot be inferred from
  LEVEL01.
- **berry kinds:** real berries (`0x21..0x24`) appear in LEVEL01, 02, 03, 06, 07,
  08, and 10. These must keep their source kind and must never be used as
  sacrifice slots.

## Standing Cautions Before Per-Level Mutation

- The confirmed entry-index -> identity map is proven for LEVEL01 only. Every
  other level is decoded by source kind alone; do not apply LEVEL01 entry
  semantics elsewhere without per-level evidence.
- Review caution kinds (`0x2c`, `0x2d`, `0x30`) and the unknown kind (`0x31`)
  per level before any movement or append.
- Keep real berry kinds (`0x21..0x24`) intact.
- The `ContactRecord` 64-record runtime capacity remains a gameplay constraint
  for heavy additions on any level.
- Validate one level at a time after reviewing its warnings here; keep original
  discs and pristine extracted DATs read-only.

## Regression

New regression:

- `tools/regress_validate_levels_phase6.py`

It writes only under a temporary directory and verifies:

- `tools/validate_levels_phase6.py` compiles;
- `--no-write` produces no report files;
- a default run writes CSV and Markdown reports;
- known cross-level facts hold (LEVEL00 has no type-`0x3f`; LEVEL01 is baseline
  70 with 1248 relocation sites; LEVEL04 count is 47; the unknown kind `0x31`
  appears; the Markdown report carries the LEVEL01-only standing caution);
- no canonical input DAT is mutated by the run.

## Verification Performed

```bash
PYTHONDONTWRITEBYTECODE=1 python -m py_compile \
  tools/validate_levels_phase6.py \
  tools/regress_validate_levels_phase6.py
PYTHONDONTWRITEBYTECODE=1 python tools/validate_levels_phase6.py
PYTHONDONTWRITEBYTECODE=1 python tools/regress_validate_levels_phase6.py
```

Input DAT sha1 values were unchanged after the validation run (spot-checked
`DAT/LEVEL01_LEVEL.DAT` `b376cb506f437a1cda721fd13766ddbca7c6a247` and
`DAT/LEVEL05_LEVEL.DAT` `9d0700be6af04710694a6dd4d95901ad3ef87d6a`).

## Files Written

Intentional repository files:

- `tools/validate_levels_phase6.py`
- `tools/regress_validate_levels_phase6.py`
- `docs/TOOLING_OPTION_C_PHASE6_REPORT.md`
- `DAT/phase6_cross_level.csv`
- `DAT/phase6_cross_level.md`

## Unresolved / Future Work

- Source kind `0x31` is undecoded; identifying its handler is new reverse
  engineering and is out of Option C scope.
- Per-level entry-index identity maps (beyond LEVEL01) are not established; each
  level needs its own evidence before index-based mutation is safe.
- Checkpoint (`0x30`) and token-like (`0x2c/0x2d`) gameplay semantics remain
  unproven outside LEVEL01's tested paths.
