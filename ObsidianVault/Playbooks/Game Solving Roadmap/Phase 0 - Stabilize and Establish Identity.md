---
kind: playbook
id: PLAYBOOK_game_solving_phase_0
name: Phase 0 - Stabilize and Establish Identity
status: complete
created: 2026-07-11
updated: 2026-07-12
confidence: high
parent: PLAYBOOK_game_solving_roadmap
previous: null
next: PLAYBOOK_game_solving_phase_1
depends_on: []
---

# Phase 0 - Stabilize and Establish Identity

**Navigation:** [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]] · Start of roadmap · [[Phase 1 - Build the Original-Game Behavioral Oracle|Next phase]]

## Purpose

Create a reproducible foundation before changing more behavior. Every later result
must name the exact source state, enabled modules, executable, disc, movie, emulator,
and media identity that produced it.

The hash-verified pristine retail image is the sole build base. ALLMODS and every other
MOD image are read-only historical/comparison artifacts and must never receive another
patch.

## Scope

- Preserve and inventory existing operator WIP without resetting unrelated files.
- Identify and hash-pin the pristine source image; separately identify last-known-good
  ALLMODS and diagnostic artifacts as read-only evidence.
- Record the exact enabled-module set for every integration artifact.
- Build each experiment and module combination by copying pristine to a new output and
  applying the selected changes once.
- Make the consolidated build reproducible from an explicit input manifest.
- Separate generated discs, saves, captures, movies, tokens, and copyrighted assets
  from source changes.
- Define supported and unsupported module combinations instead of treating every
  combination as implicitly valid.

## Work packages

- [x] Produce a WIP inventory grouped by source, generated artifact, local media, and
  experiment evidence. — `tools/phase0_inventory.py` → `analysis/phase0_wip_inventory.json`.
- [x] Record pristine and known-good executable/disc hashes and their provenance. —
  `tools/build_baselines.json` (pins) + `tools/disc_provenance.json` (Redump-verified,
  re-verified PASS 2026-07-11).
- [x] Add a build guard that rejects ALLMODS, MOD images, and prior derivatives as
  source inputs and verifies the pristine hash before staging changes. —
  `tools/build_identity.py` + guard calls in `mod/build.py` (input pins, protected
  outputs); negative-tested.
- [x] Define a machine-readable build-input and enabled-module manifest. — every disc
  build now emits `<out>.build_manifest.json` (schema `abl-build-manifest/1`).
- [x] Prove two clean builds from identical declared inputs produce identical payloads.
  — PHASE0_REPRO_A/B: identical `.bin` sha256; see Evidence.
- [x] Define artifact naming so diagnostic and release builds cannot be confused. —
  `--profile` ⇄ `*_REL` suffix binding enforced by `mod/build.py`.
- [x] Record the supported module-combination matrix and explicit exclusions. —
  `mod/module_matrix.yaml`, enforced by `mod/build.py --mods` (override:
  `--allow-unsupported`, diagnostic-only).
- [x] Confirm that normal-user DuckStation state is never used by automated runs. —
  audit 2026-07-11, see Evidence.

## Required evidence

- Source revision and dirty-state summary.
- Build command, input manifest, module list, and toolchain versions.
- Executable, BIN/CUE, movie, and fixture hashes.
- DuckStation revision, isolated config identity, serial, and media title.
- Rebuild comparison proving deterministic output or documenting every permitted
  nondeterministic field.

## Exit gate

Two clean builds from the same declared inputs produce the same executable and disc
payload hashes, and every reported regression can name the precise artifact and module
combination on which it occurred.

## Handoff to Phase 1

Phase 1 receives the pinned immutable pristine artifact, read-only historical MOD
evidence, supported module matrix, timing profile, verified movies, and artifact
identity schema.

## Progress record

| Work package | Status | Evidence |
|---|---|---|
| WIP inventory | **done 2026-07-11** | `analysis/phase0_wip_inventory.json` @ git `0aa0fac` (408 dirty status lines): source 4,819 files / 57 MB · generated 11,715 / 177 GB · local media 2,526 / 20 GB · experiment evidence 659 / 862 MB · 13 residual `other` paths recorded for review |
| Hash-pinned baselines | **done 2026-07-11** | `tools/build_baselines.json`: 327 staged inputs (725,849,170 B) pinned sha256; pristine media pins duplicated from Redump-verified `tools/disc_provenance.json` (`re_baseline.py --provenance` PASS 2026-07-11); ALLMODS bin/cue pinned as read-only evidence (`fea978e5…`, 738,746,736 B) |
| Pristine-only input guard | **done 2026-07-11** | `tools/build_identity.py` + `mod/build.py` (`read_staged_pristine`, `guard_staged_and_outputs`); 5 negative tests PASS: corrupted staged EXE refused, ALLMODS overwrite refused, `_REL`⇄`--profile` mismatches refused (×2), unsupported combo refused. **Live catch:** staging tree WAS contaminated — `REBUILD/files/LEVEL01/LEVEL.DAT` carried 24,105 modded bytes (from +0x1568; disc LBA 2908–2971); contaminated copy preserved at `build/LEVEL01_LEVEL.DAT.contaminated-2026-07-11` (sha256 `c2ed8f34…`), pristine bytes (`786b7a96…`) restored from the retail image, full-disc rebuild then reproduced the Redump image byte-exactly (sha1 `0bc1a297…`, 0/313,897 sectors differ) |
| Build-input manifest | **done 2026-07-11** | `<out>.build_manifest.json` per build (schema `abl-build-manifest/1`): git head+dirty summary, argv, module set + matrix combination, per-file pristine/patched sha256 + LBA, toolchain (armips v0.11.0, MKPSXISO 2.20, mips64 gcc 16.1.1, python 3.14.5, fork pin `29695532`), output sha256 |
| Reproducible build | **done 2026-07-11** | `analysis/phase0/PHASE0_REPRO_{A,B}.build_manifest.json` (committed copies of the emitted manifests): two clean `--mods mod/mods.yaml` builds → identical `.bin` sha256 `fea978e5…` (738,746,736 B) and identical patched-EXE sha256 `8d876121…`; `.cue` differs ONLY by its embedded bin filename (the one permitted output-name-derived field). Cross-check: output is bit-identical to the retained known-good `build/ABL_ALLMODS.bin` |
| Module matrix | **done 2026-07-11** | `mod/module_matrix.yaml`: 6 supported combinations (allmods-2026-07, code-mods-only, 4 singles) + 3 exclusion classes; enforced in `run_manifest` before any lane runs |
| Artifact naming | **done 2026-07-11** | diagnostic (default) vs release: `--profile release` ⇔ basename `*_REL`, mutually enforced; profile recorded in the build manifest |
| DuckStation isolation audit | **done 2026-07-11** | All automated launch paths route through `tools/launch_repro_playback.sh` or the fork `launch_debugger_instance.sh`: both force `XDG_CONFIG_HOME`/`XDG_RUNTIME_DIR` into isolated config dirs (`/tmp/dsrepro*`, `/tmp/duckstation-debugger`, or per-run `mkdtemp` in `tools/ps1_scenario.py`), write their own `settings.ini`, and stop only the pid in `$CONFIG_DIR/instance.pid`. User-profile touchpoints are read-only (BIOS dir) or project-owned (`~/.cache/abl/abl_card_seed.mcd`). The only user-profile launches are two operator zenity GUIs (`tools/abl_blender/{tier3_build_gui,import_to_game_gui}.sh`) behind explicit "Boot it" confirmation — interactive operator acceptance, not automated runs |

## Exit gate result — PASSED 2026-07-11

Two clean builds from the same declared inputs (`mod/mods.yaml`, pinned staging tree)
produced the same disc payload sha256 and the same patched-executable sha256; the cue's
embedded output filename is the single documented output-name-derived field. Every new
build emits a manifest naming its exact source revision, dirty state, inputs, module
combination, toolchain, and output identity — so any regression reported against such an
artifact names its precise provenance. Historical artifacts predating this phase carry no
manifest and remain read-only evidence per the pristine-image-authority rule.

Safe test suite after the changes: 165 passed, 1 deselected (`-m "not live"`;
`analysis/memory_map.json` was re-synced to its current inputs — pre-existing drift in
`functions.json`/`re_symbols.sym`/`registry.py` from earlier campaigns, caught by
`test_memory_map.py::test_regeneration_is_identical`).

## Hardening after external review (2026-07-11, second pass)

A second-opinion review (Codex) rated the first pass ~90%: the guard verified only
actively patched files, `--write` trusted the tree it pinned, manifests did not hash
dirty build-critical sources (several of which were uncommitted), and the guard tests
were manual. All four are closed:

1. **Full-tree pre-build verify** — `guard_staged_and_outputs` now calls
   `build_identity.verify_tree()`: every one of the 327 pins is checked (contaminated,
   missing, AND unpinned-extra files all fail) before mkpsxiso runs, because the disc
   embeds the whole tree, not just the files a build patches. Cost ≈ 0.5 s.
2. **`--write` cannot bless contamination** — pinning now REQUIRES the mechanical
   proof: mkpsxiso-rebuild from `REBUILD/abl.xml` must reproduce the Redump sha1
   (`0bc1a297…`) byte-exactly before any pins are written (verified live: proof PASS,
   pins unchanged). Escape hatch only via `ABL_UNSAFE_SKIP_REBUILD_PROOF=1` with a loud
   warning.
3. **Build-source closure hashed + committed** — manifests now carry
   `inputs.build_sources`: sha256 of the exact asm modules, caves, `registry.py`,
   `hook_caves.yaml`, `module_matrix.yaml`, stager tools, and every file referenced by
   asset params (external wavs/PNGs/terrain DATs included — 38 files for the ALLMODS
   set). The previously uncommitted build-critical code sources (registry, hook_caves,
   caves, module asm, stagers, patch/symbols asm, mods.yaml) are committed; personal
   media and game-derived images stay uncommitted by policy, pinned by hash only. Dirty
   summary cap raised 200→1000 (current tree: 408).
4. **Guard regression tests committed** — `tests/test_build_identity.py` (10 tests, in
   the safe suite): pin coverage, tamper rejection, unpinned-target rejection,
   full-tree intruder detection, pristine-pass, protected outputs, naming⇄profile
   binding, matrix gate + override marking. Safe suite: **175 passed**.

Re-proof after hardening: a fresh ALLMODS build (`PHASE0_REPRO_C`, manifest copied to
`analysis/phase0/`) passed the full-tree guard and produced the same `.bin` sha256
`fea978e5…` as A/B and the retained known-good ALLMODS.

Residual (accepted, documented): a build manifest pins the identity of external media
inputs (voice wavs under `~/AI/…`, custom sign/emblem PNGs) but the repo does
not contain them; losing those files would make the exact ALLMODS asset lane
unreproducible even though every hash to detect that is recorded. Off-host durability of
personal inputs is operator-owned (same policy as the DuckStation fork preservation set).

## Retroactive knowledge-closure audit — 2026-07-12

**Result:** the behavioral/build gate remains closed; knowledge closure is **partial**
under the roadmap's new eight-part definition. Identity, pristine-only staging,
full-tree verification, source hashes, module policy, and build manifests are banked
and executable. `tools/build_identity.py --verify` passed for all 327 staged inputs.

The audit added `analysis/phase0_2_knowledge_closure.yaml`, its generated report,
the central external preservation set, and guards in `tests/test_knowledge_closure.py`.
The known `tools/glyph_spin_native.py` dependency is tracked (commit `20f98c6`) and
both tracked consumers are named mechanically. The original audit found four other
tracked tools importing untracked local modules:
`build_terrain_collision_disc.py` → `native_collision_from_heightfield.py`,
`tier3_native_objects.py` → `tier3_native_object_inventory.py`, and
`training_tutorial_stager.py` → `patch_training_overlay.py` plus
`training_board_edit.py`.

Phase 3 iteration 3 closed that source gap without importing media: the four
non-copyrighted modules and their training-board guard were centrally declared with
source path, byte size, SHA-256, and media class, then committed byte-for-byte.
`tools/knowledge_closure_audit.py` now recomputes both the tracked-import scan and the
provisioned-source pins. The current report has zero untracked imports and zero source
pin errors; deleting or changing one of those files reopens the low-level dependency.

Accepted external dependencies remain the owner-supplied retail image, DuckStation
fork/binary, era toolchains, and hash-pinned operator/copyrighted inputs. Their bytes
remain outside Git. Exact current inventory, source-import blockers, classifications,
and supersession state are generated in
`analysis/phase0_2_knowledge_closure_report.json`. Strict mode still exits nonzero on
the retained historical Phase 0-2 `partial` labels; the concrete source, fixture-pin,
address-promotion, and matrix blocker lists themselves are empty.

Validation at audit close: working-tree `tools/run_safe_tests.py` → **265 passed,
27 deselected**; detached clean worktree at `b945893` plus the declared fixture set
and pinned pristine EXE → **222 passed, 4 media skips, 27 deselected**; clean archive
Phase-0..2 slice → **81 passed, 4 media skips, 9 deselected**.
`tools/build_identity.py --verify` → **327/327 PASS**;
`tools/knowledge_closure_audit.py --write` initially reported four declared
untracked-source imports. The Phase 3 iteration-3 regeneration supersedes that count:
zero matrix errors, zero missing fixture pins, zero source/import errors, and zero
unpromoted confirmed addresses. The strict audit correctly exits nonzero only because
the historical phase labels remain partial.
