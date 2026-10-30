# Option C Phase 5 Report

Scope executed:

- Phase 5: rebuild integration wrapper for already-patched DAT files.

Scope not executed:

- No new DAT patching behavior.
- No relocation logic rewrite.
- No cross-level validation.
- No changes to Phase 2, Phase 3, or Phase 4 mutation behavior.
- No workspace DAT/BIN/CUE output was kept from verification.

## Tool

New tool:

- `tools/rebuild_with_patched_dat.py`

The tool accepts an already patched DAT, temporarily stages it over a target
file in `REBUILD/files`, runs `mkpsxiso`, verifies that the rebuilt image embeds
the exact patched bytes, and restores the staged workspace file before exiting.

Dry-run is the default. Rebuild output is written only with `--write` and
explicit `--out-bin` / `--out-cue` paths.

## Example

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/rebuild_with_patched_dat.py \
  --patched-dat /tmp/level01_phase4_spec_test.DAT \
  --target files/LEVEL01/LEVEL.DAT \
  --out-bin /tmp/level01_phase5_rebuild.bin \
  --out-cue /tmp/level01_phase5_rebuild.cue \
  --write \
  --report /tmp/level01_phase5_rebuild.md
```

Conservative defaults:

- dry-run unless `--write` is provided;
- output BIN/CUE paths are required;
- existing output BIN/CUE files are refused unless `--force-output` is used;
- optional `--expected-sha1` can pin the patched DAT input;
- the XML `offs` value is used as the target LBA;
- embedded verification reads MODE2/2352 sector user data (`+24`, `2048`
  bytes per sector) and compares it byte-for-byte with the patched DAT;
- the staged file is restored from its original bytes in a `finally` block.

## Regression

New regression:

- `tools/regress_rebuild_with_patched_dat.py`

The regression writes only under a temporary directory for patched DAT and image
outputs. It temporarily stages `REBUILD/files/LEVEL01/LEVEL.DAT` through the
Phase 5 wrapper, then checks that the staged file hash matches its pre-run hash.

It verifies:

- `tools/rebuild_with_patched_dat.py` compiles;
- dry-run does not write image outputs;
- a known-good patched DAT produced by `tools/apply_level_placements.py` can be
  staged and rebuilt;
- embedded `LEVEL01/LEVEL.DAT` bytes in the rebuilt BIN match the patched DAT;
- a Markdown rebuild report is written;
- `REBUILD/files/LEVEL01/LEVEL.DAT` is restored after the rebuild.

## Verification Performed

Syntax:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m py_compile \
  tools/rebuild_with_patched_dat.py \
  tools/regress_rebuild_with_patched_dat.py \
  tools/apply_level_placements.py \
  tools/insert_type3f_entries.py \
  tools/regress_type3f_insert.py
```

Phase 3 regression:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/regress_type3f_insert.py
```

Phase 5 regression:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/regress_rebuild_with_patched_dat.py
```

Explicit `/tmp` verification:

1. Built `/tmp/level01_phase5_spec_test.DAT` from a Phase 4 spec with one move,
   one clone append, and one structured append-new.
2. Ran `tools/rebuild_with_patched_dat.py` in dry-run mode and confirmed it did
   not stage or build.
3. Ran `tools/rebuild_with_patched_dat.py --write` with `--expected-sha1` for
   `/tmp/level01_phase5_spec_test.DAT`.
4. `mkpsxiso` produced `/tmp/level01_phase5_rebuild.bin` and
   `/tmp/level01_phase5_rebuild.cue`.
5. Embedded `LEVEL01/LEVEL.DAT` verification passed at LBA `2906`; embedded
   sha1 matched patched DAT sha1
   `f01cb3de74ce5069e7fa008e995c1f668ed93fca`.
6. Post-run hashes matched pristine:
   `DAT/LEVEL01_LEVEL.DAT`,
   `REBUILD/files/LEVEL01/LEVEL.DAT`, and
   `REBUILD/files/LEVEL01/LEVEL.DAT.orig` all sha1
   `b376cb506f437a1cda721fd13766ddbca7c6a247`.
7. Catalog parse of `/tmp/level01_phase5_spec_test.DAT` reported type-`0x3f`
   count `72`.
8. Relocation scan of `/tmp/level01_phase5_spec_test.DAT` reported `1248`
   relocation sites.

## Files Written

Intentional repository files:

- `tools/rebuild_with_patched_dat.py`
- `tools/regress_rebuild_with_patched_dat.py`
- `docs/TOOLING_OPTION_C_PHASE5_REPORT.md`

Temporary verification files:

- `/tmp/level01_phase5_spec.yaml`
- `/tmp/level01_phase5_spec_test.DAT`
- `/tmp/level01_phase5_spec_test.md`
- `/tmp/level01_phase5_rebuild.bin`
- `/tmp/level01_phase5_rebuild.cue`
- `/tmp/level01_phase5_rebuild.md`
- `/tmp/level01_phase5_rebuild_dry_run.md`

## Unresolved Before Phase 6

- Cross-level validation remains Phase 6.
- Phase 5 only stages explicit already-patched DATs; it does not decide whether
  a patch is gameplay-safe.
- Runtime `ContactRecord` capacity remains a gameplay constraint for heavy
  additions.
