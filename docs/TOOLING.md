# Tooling & Build Workflow — A Bug's Life (SCUS-94288)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)

Owned-disc preservation/educational work only. Build/verify workflow, workspace paths, and the Python tools.

## Pinned analysis and test environment
- Machine-readable Python dependencies: `tools/requirements.txt` (`Pillow==12.2.0`, `pytest==9.1.1`).
- Full external-tool/version/CI-safety census: `ObsidianVault/Toolchain Census.md`.
- Safe checks (no ROM, BIOS, extracted assets, saves, emulator, or GPU):
  ```
  python3 -m pip install -r tools/requirements.txt
  python3 tools/run_safe_tests.py
  ```
- GitHub Actions runs the same safe suite plus `tools/verify_repro_inputs.py`. Existing
  `tools/regress_*.py`, editor/GPU checks, and DuckStation live scripts remain explicit local runs
  because they require owner-supplied copyrighted inputs, an OpenGL environment, or the external fork.
- M3 symbol baseline: `symbols/re_symbols.sym`; validate its sorted, unique DuckStation
  `AAAAAAAA label` format with `python3 tools/validate_symbol_map.py`. Overlay analysis must
  use the file's documented load base and skip its four-byte module header; see
  `ObsidianVault/Executable and Overlays.md`.
- Reproducible symbol consumers: `python3 tools/symbol_roundtrip.py --format duckstation-csv
  --output /tmp/abl-re-symbols.csv` or `--format r2 --output /tmp/abl-re-symbols.r2`. Both
  reparse and compare all address/name pairs; the safe suite covers them.

## Image extract / rebuild (dumpsxiso / mkpsxiso)
- Tools: `/usr/local/bin/dumpsxiso`, `/usr/local/bin/mkpsxiso` (both 2.20).
- One-time extract of the workspace from the original image:
  ```
  dumpsxiso -x REBUILD/files -s REBUILD/abl.xml -l "Disney-Pixar A Bug's Life (v1.0).cue"
  ```
- Rebuild an image after staging a patched file:
  ```
  mkpsxiso -y -o OUTPUT.bin -c OUTPUT.cue REBUILD/abl.xml
  ```
- cue track is `MODE2/2352`; rebuilt image size is `738285744` bytes (313897 sectors).

## Workspace paths
- Original image (PRISTINE, never overwrite): `Disney-Pixar A Bug's Life (v1.0).bin/.cue` (mtime Apr 15 2012).
- Extracted/staged tree: `REBUILD/files/...`; manifest `REBUILD/abl.xml`.
- Staged LEVEL01 DAT (edited per build): `REBUILD/files/LEVEL01/LEVEL.DAT`
  with pristine backup `REBUILD/files/LEVEL01/LEVEL.DAT.orig`.
- Pristine extracted DAT for tooling input: `DAT/LEVEL01_LEVEL.DAT`
  (sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`, 332824 B). Patched DATs live under `DAT/`.
- `LEVEL01/LEVEL.DAT` is at LBA **2906** in the image (sector-aware: 2352-byte sectors, user data at +24, 2048/sector).

## Build & rebuild rules
1. Produce the patched DAT under `DAT/` from pristine input with a tool below.
2. Copy it over `REBUILD/files/LEVEL01/LEVEL.DAT`.
3. `mkpsxiso` to a freshly named `.bin/.cue`.
4. **Restore** `REBUILD/files/LEVEL01/LEVEL.DAT` from `LEVEL.DAT.orig` after every build.
5. Never modify the original `Disney-Pixar A Bug's Life (v1.0).bin/.cue`.

## Verification checklist (per build)
1. Output DAT size == pristine input size (in-place edits) — or input+`0x10*k` for relocation-aware append.
2. Type-`0x3f` count correct (70 for in-place; +k for append).
3. Only the intended entry/entries changed (others byte-identical).
4. Intended X/Y/Z/kind as planned.
5. Later records unchanged/unshifted (in-place) — or correctly shifted+relocated (append).
6. Embedded `LEVEL01/LEVEL.DAT` (LBA 2906, sector-aware) sha1 == patched DAT.
7. Original DAT + original image still pristine; staged workspace DAT restored.

## Python tools (`tools/`)
- `tools/list_level_grains.py` — parse type-0x3f, list source-kind `0x14` grain entries, suggest Y patch bytes.
- `tools/catalog_type3f.py` — **non-mutating unified type-0x3f catalog** across DAT files; writes CSV/Markdown reports with decoded identity, movement-safe status, warnings, and runtime coords.
- `tools/move_type3f_entry.py` — **conservative fixed-size type-0x3f mover**; dry-run by default, writes only with `--write --out`, preserves kind/unknown bytes, and blocks risky categories without explicit override flags.
- `tools/insert_type3f_entries.py` — **safe relocation-aware type-0x3f append wrapper** around `tools/dat_reloc.py`; dry-run by default, supports clone/new/hex multi-entry append, writes only with `--write --out`.
- `tools/apply_level_placements.py` — **declarative type-0x3f placement spec runner**; dry-run by default, composes move/append operations in memory, writes only with `--write --out`.
- `tools/rebuild_with_patched_dat.py` — **rebuild integration wrapper**; dry-run by default, temporarily stages an already-patched DAT into `REBUILD/files`, runs `mkpsxiso`, verifies embedded bytes, and restores the staged workspace file.
- `tools/regress_type3f_insert.py` — short Phase 3 append-wrapper regression checks; writes only to a temporary directory.
- `tools/regress_rebuild_with_patched_dat.py` — short Phase 5 rebuild-wrapper regression checks; writes image outputs only to a temporary directory and restores staged DAT bytes.
- `tools/patch_level_grain.py` — patch one grain by grain index (`--grain N --dy ... --out ...`); kind-checked.
- `tools/patch_level_entry.py` — **general single/multi entry coordinate move** (`--entries N --dx/--dy/--dz
  --out`); preserves kind. Primary tool for grain/FLIK/token/berry moves. See [COORDINATE_MODDING.md](COORDINATE_MODDING.md).
- `tools/list_level_pickups.py` — census of type-0x3f pickups by kind (grain/FLIK/berry/token/checkpoint).
- `tools/list_level_flik.py`, `tools/nearby_level_entries.py`, `tools/catalog_level_grains.py` — discovery helpers.
- `tools/build_markers_54_55_57.py` — one-off diagnostic builder (historical; marker-sacrifice, obsolete route).
- `tools/dat_reloc.py` — **PRODUCTION append/insertion tool** (see below).

### `tools/catalog_type3f.py` — unified type-0x3f catalog (NON-MUTATING)
Phase 1 of Option C. Reads DAT files and writes report files only; it does not mutate DAT/BIN/CUE data.

Examples:
```
PYTHONDONTWRITEBYTECODE=1 python tools/catalog_type3f.py DAT/LEVEL01_LEVEL.DAT --validate-level01 \
  --csv DAT/type3f_catalog_level01.csv --md DAT/type3f_catalog_level01.md
PYTHONDONTWRITEBYTECODE=1 python tools/catalog_type3f.py 'DAT/LEVEL*_LEVEL*.DAT' --validate-level01 \
  --csv DAT/type3f_catalog.csv --md DAT/type3f_catalog.md
```

Outputs from the Phase 0/1 run:
- `DAT/type3f_catalog.csv`
- `DAT/type3f_catalog.md`
- `DAT/type3f_catalog_level01.csv`
- `DAT/type3f_catalog_level01.md`

See [TOOLING_OPTION_C_PHASE0_1_REPORT.md](TOOLING_OPTION_C_PHASE0_1_REPORT.md).

### `tools/move_type3f_entry.py` — fixed-size type-0x3f mover
Phase 2 of Option C. Moves existing type-`0x3f` entries by coordinate deltas only. It does not append, change source kind, rebuild images, or touch relocation logic.

Conservative defaults:
- dry-run unless `--write` is provided;
- `--out` required with `--write`;
- in-place writes refused;
- kind/unknown bytes preserved;
- checkpoints (`0x30`), token-like `0x2c/0x2d`, and unknown kinds require explicit override flags.

Examples:
```
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py DAT/LEVEL01_LEVEL.DAT --entry 0 --dx 1 --dy -2 --dz 3
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py DAT/LEVEL01_LEVEL.DAT --identity "FLIK F" --dy -1
PYTHONDONTWRITEBYTECODE=1 python tools/move_type3f_entry.py DAT/LEVEL01_LEVEL.DAT --entry 0 --dx 1 --dy -2 --dz 3 \
  --write --out /tmp/level01_entry0_move_test.DAT --report /tmp/level01_entry0_move_test.md
```

See [TOOLING_OPTION_C_PHASE2_REPORT.md](TOOLING_OPTION_C_PHASE2_REPORT.md).

### `tools/insert_type3f_entries.py` — relocation-aware type-0x3f append wrapper
Phase 3 of Option C. Builds one or more 0x10-byte type-`0x3f` entries and delegates relocation-aware insertion to `tools/dat_reloc.py`. It does not rewrite relocation logic, build ISOs, or mutate DATs unless `--write --out` is provided.

Examples:
```
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py DAT/LEVEL01_LEVEL.DAT --append-clone 64:512:0:0
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py DAT/LEVEL01_LEVEL.DAT --append-new 0x29:4928:-50:-3655
PYTHONDONTWRITEBYTECODE=1 python tools/insert_type3f_entries.py DAT/LEVEL01_LEVEL.DAT \
  --append-clone 64:512:0:0 --append-new 0x2a:5000:-50:-3600 \
  --entry-bytes 40130000ceffffffb9f1ffff29000000 \
  --write --out /tmp/level01_type3f_multi_append_test.DAT \
  --report /tmp/level01_type3f_multi_append_test.md
```

See [TOOLING_OPTION_C_PHASE3_REPORT.md](TOOLING_OPTION_C_PHASE3_REPORT.md).

Regression:
```
PYTHONDONTWRITEBYTECODE=1 python tools/regress_type3f_insert.py
```

### `tools/apply_level_placements.py` — declarative placement spec runner
Phase 4 of Option C. Applies a small YAML-like or JSON placement spec with `move`, `append_clone`, `append_new`, and `entry_bytes` operations. It composes the Phase 2 mover and Phase 3 append wrapper in memory. It does not stage rebuild files, build ISOs, or write DATs unless `--write --out` is provided.

Example spec:
```
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

Examples:
```
PYTHONDONTWRITEBYTECODE=1 python tools/apply_level_placements.py /tmp/level01_phase4_spec.yaml
PYTHONDONTWRITEBYTECODE=1 python tools/apply_level_placements.py /tmp/level01_phase4_spec.yaml \
  --write --out /tmp/level01_phase4_spec_test.DAT \
  --report /tmp/level01_phase4_spec_test.md
```

See [TOOLING_OPTION_C_PHASE4_REPORT.md](TOOLING_OPTION_C_PHASE4_REPORT.md).

### `tools/rebuild_with_patched_dat.py` — rebuild integration wrapper
Phase 5 of Option C. Stages an already-patched DAT into `REBUILD/files`, runs
`mkpsxiso`, verifies that the rebuilt MODE2/2352 image embeds the exact patched
bytes, and restores the staged workspace file. It does not patch DAT contents.

Dry-run:
```
PYTHONDONTWRITEBYTECODE=1 python tools/rebuild_with_patched_dat.py \
  --patched-dat /tmp/level01_phase4_spec_test.DAT \
  --out-bin /tmp/level01_phase5_rebuild.bin \
  --out-cue /tmp/level01_phase5_rebuild.cue
```

Write and verify:
```
PYTHONDONTWRITEBYTECODE=1 python tools/rebuild_with_patched_dat.py \
  --patched-dat /tmp/level01_phase4_spec_test.DAT \
  --target files/LEVEL01/LEVEL.DAT \
  --out-bin /tmp/level01_phase5_rebuild.bin \
  --out-cue /tmp/level01_phase5_rebuild.cue \
  --write --report /tmp/level01_phase5_rebuild.md
```

Regression:
```
PYTHONDONTWRITEBYTECODE=1 python tools/regress_rebuild_with_patched_dat.py
```

See [TOOLING_OPTION_C_PHASE5_REPORT.md](TOOLING_OPTION_C_PHASE5_REPORT.md).

### ⚠ `tools/add_level_entry.py` — OBSOLETE for LEVEL01 append
Naive byte-shift append (insert entry, bump count, shift later records) **without** fixing the DAT's internal
baked file offsets. **Not production-safe** for relocation-bearing DATs (LEVEL01): the rebuilt level reaches
"Press X" then black-screens. Kept only for historical/diagnostic reference. Use `tools/dat_reloc.py` instead.

### `tools/dat_reloc.py` — relocation-aware append/insertion (PRODUCTION)
Reproduces the parser `fcn.8001cdc0` relocation walk and fixes every internal baked file offset when records
shift. See [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md) for the model.
Prefer `tools/insert_type3f_entries.py` for user-facing type-`0x3f` append workflows; keep `tools/dat_reloc.py`
as the trusted low-level relocation engine.
- **Scan mode:** `python3 tools/dat_reloc.py DAT/LEVEL01_LEVEL.DAT --scan` — lists all relocation sites
  (LEVEL01: 1248 = 968 pass-1 + 280 pass-3; pass-2 empty).
- **Append by clone:** `python3 tools/dat_reloc.py DAT/LEVEL01_LEVEL.DAT --clone-entry N [--dx/--dy/--dz] --out OUT.DAT`
- **Append by raw bytes:** `python3 tools/dat_reloc.py DAT/LEVEL01_LEVEL.DAT --entry-bytes <32 hex> --out OUT.DAT`
- **Verification expectations:** output size = input + `0x10` per inserted entry; type-0x3f count +k; entries
  before insert point byte-identical (except count); each relocated field `new = old + 0x10*k`, in-bounds,
  same logical shifted data; re-scan of output yields the same site set shifted by the insert delta.

## Original-image preservation rules
- Treat `Disney-Pixar A Bug's Life (v1.0).bin/.cue` as read-only ground truth; verify its embedded DAT stays
  `b376cb50…` after work. All edits go to copies under `DAT/` and freshly-named output images.

## radare2 / disassembly
## Tooling
- radare2 5.9.8 installed locally. Reproduce with:
  `r2 -q -e asm.arch=mips -e asm.bits=32 -e cfg.bigendian=false -e anal.gp=0x80081d98 -c aaa SCUS_942.88`
- `iso_probe.py` (repo root) re-extracts header facts read-only.
- For overlay disassembly, see the r2 recipe in [EXECUTABLE_AND_OVERLAYS.md](EXECUTABLE_AND_OVERLAYS.md)
  ("Manual overlay load"). Host `rasm2` mis-decodes MIPS — use r2 with explicit arch flags.

---

**Related docs:** [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md) · [COORDINATE_MODDING.md](COORDINATE_MODDING.md) · [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)
