---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Toolchain Census.md
aliases:
  - "Toolchain Census"
migration_action: superseded
superseded_by:
  - Finding_-_Build_toolchain_and_PROPACK_provenance
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Toolchain Census.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Toolchain Census
type: reference
updated: 2026-06-22
tags: [reference, toolchain, testing, reproducibility, milestone2]
---

# Toolchain Census — analysis, build, and tests

> Milestone 2 census for [[Gap Audit|GAP-0016]], [[Gap Audit|GAP-0017]], and [[Gap Audit|GAP-0040]]. “Known version” is evidence-backed; unknowns are stated as **Not confirmed from current repo contents**. This note records tools and versions, not copyrighted inputs. Python dependencies are machine-pinned in `tools/requirements.txt`.

## Current census

| Tool | Purpose | Req. | Known version | Version evidence | Install / path expectation | Determinism notes | CI safe? | Copyrighted/local-only contact | Gaps · related files |
|---|---|:--:|---|---|---|---|:--:|---|---|
| Python | All tracked analysis/test scripts | Yes | Dev host + CI **3.14.5** | `python3 --version`; workflow input | `python3` on `PATH` | Safe suite avoids bytecode; direct and resolved test dependencies exact-pinned | Yes | None for safe suite; many operational tools read local disc derivatives | 0017/0040 · `pyproject.toml`, `tools/run_safe_tests.py` |
| pytest | Safe test runner | Yes | **9.1.1** | package index query, 2026-06-20 | `pip install -r tools/requirements.txt` | Exact pin; strict markers; default collection is `tests/` only | Yes | No | 0017/0040 · `tests/`, `.github/workflows/safe-tests.yml` |
| Pillow | Image/text patch helper | Conditional | **12.2.0** | locally installed package metadata | Python environment | Exact pin; image output still depends on explicit fonts/inputs | Yes for import | Relevant tools may read local extracted art | 0016 · `tools/patch_flik_word.py` |
| PsyMake | Original retail build driver | Historical | **1.11** | on-disc `STATE.RST` / build evidence summarized in [[Finding - Build toolchain and PROPACK provenance]] | Not installed or vendored | Evidence/provenance only; cannot reproduce original build yet | No | Evidence came from owner-local extracted disc files | 0016 · finding above |
| PsyQ / `ccpsx` | Original PS1 compiler and SDK | Historical / future decomp | **Not confirmed from current repo contents** | `[psyq]` and SDK strings identify family, not exact release | Not installed or vendored | Exact compiler/library objects remain unknown | No | Identification requires owner-local EXE/dev artifacts | 0016/0018/0021 · `docs/EXECUTABLE_AND_OVERLAYS.md` |
| PsyQ libraries | Symbol seeding/runtime APIs | Historical | `libcd`, `libgpu`, `libgte`, `libspu`, `libsnd`; `libpad` likely (not signature-confirmed); **linked libs dated ≥1997-03-28** | EXE embeds PsyQ RCS `$Id$` stamps: `sys.c` v1.129 (1996-12-25), `intr.c` v1.76 (1997-02-12), `bios.c` v1.86 (1997-03-28); "(c) 1993-1997 SCE" | Statically linked in owner-local executable | Dates the SDK to a 1997 PsyQ; per-object revisions still unknown | No | Owner-local executable only | 0016/0018 · [[Finding - Build toolchain and PROPACK provenance]] |
| PROPACK | Original LEVEL.RAW compression | Historical | **2.29** | on-disc build log summarized in the provenance finding | Not installed or vendored | Decoder is byte-exact; original encoder is unavailable; local encoder is literal-only | No | Original tool/evidence local-only; tracked minimal oracle is policy-approved | 0016/0024/0040 · `tools/decode_level_raw.py`, `recompress_level_raw.py` |
| `lbmbugs` | Original LBM/BGR asset packer | Historical | **2.0** | on-disc build log summarized in the provenance finding | Not installed or vendored | Invocation semantics partly unknown | No | Owner-local dev artifact evidence | 0016 · provenance finding |
| mkpsxiso / dumpsxiso | Disc extract and deterministic rebuild | Conditional | **2.20** / **2.20** | local `-h` banners; `docs/TOOLING.md` | Commands on `PATH`; dev host currently `/usr/local/bin/` | Unmodified rebuild proven byte-exact; never run in safe CI | No | Operates on owner-local disc/extracted tree | 0016 · `REBUILD/abl.xml`, `tools/rebuild_with_patched_dat.py` |
| jPSXdec | XA/STR inspection/extraction | Optional | **2.1-beta** | local directory name and existing project notes; CLI version was not headless-queryable | owner-local `jpsxdec_v2.1-beta/jpsxdec.jar`; Java required | Pin is documented, but binary is not vendored | No | Reads copyrighted disc media; outputs stay local | 0016 · [[Asset - Asset extraction recipe]] |
| Java | jPSXdec runtime / editor fallback | Optional | Dev host **25.0.3** | `java -version` | `java` on `PATH` | Not part of safe CI | No | Depends on invoked tool/input | 0016 · jPSXdec, editor notes |
| DuckStation fork | Live debugger, GPU, replay, emulator APIs | Optional / live evidence | HEAD **`296955321fd9375fa94692d96df788eccd708135`** plus an uncommitted layer | direct read-only audit; `tools/FORK_COMMIT.txt`; [[DuckStation Fork Reproducibility]] | `~/duckstation`; CMake/Ninja Release build; external source/spec not vendored | 114 RPC methods at HEAD + 27 dirty-only (re-verified 2026-06-21, `tools/duckstation_rpc_method_manifest.md`); **preserved 2026-06-21** as recoverable bundle/patch/untracked-archive + in-repo tag (byte-exact reconstruction); clean clone rebuilt → binary `fd4bf9ed…`; off-host copy pending | No | Requires BIOS, disc, saves, external source, and operator setup | 0001/0017/0040 · `tools/abl_dbg.py`, `tools/FORK_COMMIT.txt` |
| radare2 | MIPS static/overlay analysis and symbol consumer | Optional | **5.9.8** | local `r2 -v`; `docs/TOOLING.md`; [[Symbol Import Round Trip]] | `r2` on `PATH` | MIPS32 little-endian; `$gp=0x80081d98`; explicit overlay base/code offset required; generated flag script loaded all 85 labels | Tool itself yes; project analysis no | Symbol test needs only text; binary analysis reads owner-local executable/overlays | 0016/0018/0020 · [[Executable and Overlays]] |
| Ghidra | **Decompiler / cross-check layer** (secondary to r2+DuckStation; does NOT replace them) | **Configured (pilot, 2026-06-22)** | **12.1.2** (Flatpak `org.ghidra_sre.Ghidra`) | headless `analyzeHeadless` via `flatpak run`; project `ghidra/project/ABLPilot`; setup `ghidra/README.md`; verdict `ghidra/PILOT_REPORT.md` | Import `SCUS_942.88` as `MIPS:LE:32`, base `0x8000f800` (file 0x800→VA 0x80010000); `re_symbols.sym` applied via `ghidra/scripts/ABLPilot.java` — **`.sym` stays authoritative**, Ghidra consumes and never writes back; `$gp` context not yet set (gp-globals show `unaff_gp+off`) | `ghidra/project/ABLPilot` (in PWD) | Flatpak already has `filesystems=home;` → reads PWD, **no override needed**; GhidraMCP deliberately NOT configured | Reads owner-local executable | 0016/0018/0020 · `ghidra/PILOT_REPORT.md` |
| splat / objdiff | Future targeted decomp split and object diff | Future | **Not confirmed from current repo contents** | no config/install/version evidence found | Not installed or configured | Deferred pilot must pin versions before any claimed comparison | Not yet | Requires locally reproduced object/code inputs | 0016/0021 · [[Decompilation Pilot]] |
| PySide6 / moderngl / OpenGL / numpy | Local 3D editor and optional GPU tests | Optional | **Not confirmed from current tracked repo contents** | editor files currently exist only as unrelated worktree WIP | Isolated editor environment; do not install in safe CI | GPU/driver results are platform-sensitive | No (default) | Editor reads local DAT/RAW/assets | 0017 · [[ABL Level Editor]] |

## Test classes and runner

| Class | Default runner | CI | Inputs |
|---|---|:--:|---|
| Safe syntax/import, path portability, manifest integrity | `python tools/run_safe_tests.py` | Yes | tracked source/metadata only |
| Codec oracle + synthetic deterministic round-trip | same | Yes | two [[Preservation Policy\|policy-approved minimal codec oracles]] plus generated bytes |
| Existing DAT/rebuild regressions | invoke `tools/regress_*.py` explicitly | No | owner-local copyrighted DAT / extracted rebuild tree; some build temporary disc images |
| GPU/editor tests | run separately in the editor environment when that work is intentionally tracked | No | GPU/OpenGL + local editor inputs; no stable tracked headless path yet |
| DuckStation/live tests | explicit script invocation only | No | external fork, BIOS, disc, saves, emulator state/API |

Markers `gpu`, `live`, and `local_media` are registered in `pyproject.toml`; the safe runner excludes all three. The CI workflow has read-only repository permissions and never receives ROMs, BIOS, disc images, extracted assets, save states, emulator credentials, or absolute host paths.

## Test-like script inventory

| Files | Track | Classification / default |
|---|:--:|---|
| `tests/test_level_raw_codec.py`, `test_repro_manifest.py`, `test_tool_sanity.py`, `test_path_portability.py`, `test_symbol_map.py` | Tracked (M2/M3) | **Safe CI default**; tracked metadata, permitted oracle, synthetic bytes, and two temporary symbol consumer round-trips only |
| `tools/verify_repro_inputs.py` | Tracked | **Safe CI default**; verifies hashes of tracked policy-approved inputs; host save count is advisory |
| `tools/regress_type3f_insert.py`, `regress_validate_levels_phase6.py` | Tracked | Local-only: read owner-local `DAT/` inputs; temporary outputs only |
| `tools/regress_rebuild_with_patched_dat.py` | Tracked | Local-only: reads `DAT/` + extracted `REBUILD/`, invokes mkpsxiso, creates temporary disc outputs, and restores staging |
| `tools/patch_g6_render_sentinel_test.py`, `patch_g8_*_test.py`, `patch_g12_*_test.py` through `patch_g16_*_test.py`, `patch_g28_*_test.py` | Tracked | Experiment builders, **not unit tests**; require owner-local DAT and must never be auto-collected |
| `tools/test_overlay_stuck_seed.py`, `verify_seed_move_ingame.py`, `verify_stuck_seed_move.py` | Tracked | **Live opt-in only**; DuckStation fork + disc derivatives + save/emulator state |
| `tools/test_transform_math.py`, `test_camera_transform.py`, `test_trace_terrain_transform.py`, `test_spawn_ground_source.py` | Untracked user WIP | Not modified or included in CI. Apparently offline, but depend on other untracked work and are outside the M2 commit scope |
| `tools/verify_enemy_move.py`, `verify_chaser_move.py` | Untracked user WIP | Live opt-in; not modified or included in CI |
| `level_editor/test_scene_importer.py`, `test_scene3d.py`, `test_diag_spawn.py` | Untracked user WIP | Editor/GPU/local-input path; not modified or included in CI |

## Gap disposition after M2

- **GAP-0016 — ✅ Resolved (2026-06-22):** external versions + PsyQ library families recorded, and the linked PsyQ libraries are now **dated ≥1997-03-28** via embedded RCS `$Id$` stamps (`sys.c`/`intr.c`/`bios.c`; "(c) 1993-1997 SCE"). The lone residual — the exact `ccpsx`/gcc **compiler** revision (and per-object revisions) — is not EXE-stamped and is gated on the matching-decomp effort (GAP-0021, deferred).
- **GAP-0017 — ✅ Resolved (2026-06-22):** the pinned runner passes locally (**40**) and the safe CI workflow `.github/workflows/safe-tests.yml` is committed; `gpu`/`live`/`local_media` markers are isolated. Residual: an observed green run on GitHub (operator push; no remote yet) + optional headless-GL/live jobs.
- **GAP-0040 — ✅ Resolved (2026-06-22):** codec oracle + synthetic round-trips covered, and the live headline replay is now an opt-in `live`-marked, skip-guarded regression (`tests/test_live_replays.py` → `tools/trace_spawn_floor.py`, `ABL_LIVE` gate; excluded from safe CI). Residual (operator): re-run the other three replays from preserved state + copy preservation off-host.

## See also

[[Tools Catalog]] · [[Finding - Build toolchain and PROPACK provenance]] · [[Preservation Policy]] · [[CONTRIBUTING]] · [[Roadmap]] · `docs/TOOLING.md`
