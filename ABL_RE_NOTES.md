# A Bug's Life (SCUS-94288) — RE Notes (canonical index)

Lawful preservation/educational analysis of an **owned disc**. Target is the boot
executable and per-level data only; no game assets are redistributed. All edits are made to
copies; the original image `Disney-Pixar A Bug's Life (v1.0).bin/.cue` is treated as read-only.

This file is the **source-of-truth summary + index**. Detailed material lives in `docs/`.
History/dead-ends are preserved in the experiment log, not here.

## Documentation map
| Doc | Contents |
|-----|----------|
| [docs/DAT_FORMAT_AND_RELOCATION.md](docs/DAT_FORMAT_AND_RELOCATION.md) | `.DAT` record format, parser `fcn.8001cdc0`, dynamic type table `0x80096da0`, baked-offset relocation model, why naive append fails / relocation-aware append works, `tools/dat_reloc.py`, confirmed append milestone. |
| [docs/LEVEL01_TYPE3F_MAP.md](docs/LEVEL01_TYPE3F_MAP.md) | LEVEL01 type-`0x3f` entry ranges, confirmed source-kind map, berry warning. |
| [docs/COORDINATE_MODDING.md](docs/COORDINATE_MODDING.md) | Entry coord layout, runtime `<<5` rule, axis/auto-collect notes, grain/FLIK/token/berry move workflows, patch examples. |
| [docs/EXECUTABLE_AND_OVERLAYS.md](docs/EXECUTABLE_AND_OVERLAYS.md) | `SCUS_942.88` facts, memory map, main-shell state machine, Region A/B overlays, `LEVEL01\LEVEL.BIN`, sprite-object pool, resident pickup functions, globals/strings/BIOS thunks. |
| [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md) | Chronological history; superseded hypotheses (clearly marked) + confirmed root cause. |
| [docs/TOOLING.md](docs/TOOLING.md) | dumpsxiso/mkpsxiso workflow, workspace paths, build/verify checklist, all `tools/` scripts. |
| [docs/DECOMPILATION_PLAN.md](docs/DECOMPILATION_PLAN.md) | Incremental hand-decompilation plan (phases 1–6), `src_re/` scaffold, conventions, review checklist. |
| [docs/LEVEL_OBJECT_PIPELINE.md](docs/LEVEL_OBJECT_PIPELINE.md) | Consolidated LEVEL/DAT type-`0x3f` object pipeline from parser through constructor, contact walker, handlers, and HUD. |
| [docs/TOOLING_OPTION_C_PLAN.md](docs/TOOLING_OPTION_C_PLAN.md) | Phased Option C plan for generalized catalog, movement, relocation-aware insertion, specs, rebuild integration, and cross-level validation. |
| [docs/GEOMETRY_RE_PLAN.md](docs/GEOMETRY_RE_PLAN.md) | Phased research plan (G1–G6) for LEVEL01 geometry creation from `LEVEL01/LEVEL.DAT`: post-`0x3f` records, relocation tables, parser geometry output, runtime buffers, and render/collision consumers. Scaffold in `src_re_geometry/`. |

## Current high-confidence conclusions
- **DAT pickups are coordinate-moddable** via fixed-size type-`0x3f` entry edits; **runtime coord = file coord `<< 5`**; entry layout `+0=X +4=Y +8=Z` (s32 LE), `+0xc=kind`. More-negative Y = up.
- **True net-new entry injection works** with the relocation-aware tool. The earlier black-screen was **stale internal DAT baked offsets** after a naive `+0x10` shift — *not* a count cap, token logic, or pool limit. Confirmed in-game: `ABL_ADD_TOKEN0X29_NEAR64_RELOC_TEST` (entry 70, kind 0x29, `(4928,-50,-3655)`).
- **LEVEL01 special berries fully mapped** (kinds 0x21..0x24); each is coordinate-movable with kind preserved.
- Engine architecture (overlays Region A `0x800b39a0` / Region B `0x800b5788`, main shell `fcn.8004fa40`, sprite pool `0x8009c870`, contact walker `fcn.800586b0`, array `0x800b0d18`) is mapped — see exec doc.

## Production rules
- **Append/insert:** use **`tools/dat_reloc.py`** (relocation-aware). It fixes the 1248 internal baked offsets when records shift.
- **Move a pickup:** use `tools/patch_level_entry.py --entries N --dx/--dy/--dz` (in-place, preserves kind, no count/shift).
- Rebuild via `mkpsxiso`; **restore** `REBUILD/files/LEVEL01/LEVEL.DAT` from `.orig` after every build; keep the original image pristine. Full checklist in [docs/TOOLING.md](docs/TOOLING.md).
- Keep Y moves moderate (final runtime Y ≳ -21000) to avoid weak-Y auto-collect; lean on horizontal for visibility.

## Known-safe workflows (all in-game verified)
- Grain (0x14), FLIK letters (0x10..0x13), seed tokens (0x29/0x2a/0x2b), and special berries (0x21..0x24): single-entry coordinate moves. See [docs/COORDINATE_MODDING.md](docs/COORDINATE_MODDING.md).
- Relocation-aware true append of a new token. See [docs/DAT_FORMAT_AND_RELOCATION.md](docs/DAT_FORMAT_AND_RELOCATION.md).

## Warnings / do-not-use
- **Do NOT use naive byte-shift append** (`tools/add_level_entry.py`) on LEVEL01 — it leaves stale baked offsets → black screen after "Press X". Obsolete; superseded by `tools/dat_reloc.py`.
- **Do NOT overwrite/repurpose entries 54..57** (kinds 0x21..0x24) — they back real special berries; changing their kind deletes a berry. Only edit X/Y/Z. Fixed-count marker sacrifice is obsolete (diagnostic only).
- **Do NOT change a pickup's source kind** to relocate it — kind selects the item/model.

## Latest confirmed item maps (LEVEL01 type-0x3f)
Entry ranges: grain `0..49` · FLIK letters `50..53` · special berries `54..57` · seed tokens `58..66` · checkpoint/trigger `67..69`. Source kinds:

| kind | item | kind | item |
|-----:|------|-----:|------|
| 0x10 | FLIK **F** | 0x21 | **Green Berry / Homing Berry** (entry 56) |
| 0x11 | FLIK **L** | 0x22 | **Gold Berry** (entry 54) |
| 0x12 | FLIK **I** | 0x23 | **Blueberry / Superberry** (entry 55) |
| 0x13 | FLIK **K** | 0x24 | **Purple Berry / Mega Homing Berry** (entry 57) |
| 0x14 | grain (50) | 0x29 | orange/red seed token |
| 0x30 | checkpoint/trigger | 0x2a / 0x2b | blue / green seed token |

Full detail + handlers/counters in [docs/LEVEL01_TYPE3F_MAP.md](docs/LEVEL01_TYPE3F_MAP.md).

## Key constants (quick reference)
- Pristine `DAT/LEVEL01_LEVEL.DAT` sha1 `b376cb506f437a1cda721fd13766ddbca7c6a247`, 332824 B; type-0x3f at file `0x4` (70 entries, `0x10` each, start `0x8`).
- `LEVEL01/LEVEL.DAT` at image LBA **2906**; rebuilt image `738285744` B.
- DAT base (runtime) `[0x80082498]`; type-0x3f pointer `0x80096e9c`; grain count `0x800a65a1`; berry marker `0x800a6597`; seed counters `0x800a6598..0x659a`; contact array `0x800b0d18` (64×0x38).
