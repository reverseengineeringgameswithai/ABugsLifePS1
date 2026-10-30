---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation Fork Reproducibility.md
aliases:
  - "DuckStation Fork Reproducibility"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation Fork Reproducibility.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: DuckStation Fork Reproducibility
type: reference
updated: 2026-06-20
tags: [reference, duckstation, reproducibility, debugger, gap-0001]
---

# DuckStation fork reproducibility

> Evidence chain for [[Gap Audit|GAP-0001]]. **Status: Resolved on this host (2026-06-21) — preservation executed; byte-exact reconstruction, clean-clone rebuild, and a headline replay are all demonstrated. Lone residual: replicate the preservation set off-host (operator-only).** The fork source (committed HEAD **plus** the dirty layer) is now captured as a verified, recoverable **bundle + patchset + untracked archive** with an in-repo **tag**; an independent clone rebuilt `duckstation-qt`; and `tools/trace_spawn_floor.py` reproduced its headline verdict from that clean-built binary. The earlier blocker (no preserving remote, dirty tree) is retired except for moving the artifacts off the operator's machine — `origin` is upstream DuckStation, so a private remote/credentials remain an operator action.

## GAP-0001 closure — executed 2026-06-21

The preservation recipes below are no longer hypothetical; they were run, and the result was verified end-to-end. Nothing copyrighted or local-only entered the repo (only hashes/paths/method-names are recorded). The operator fork worktree was **not** modified (still 34 modified + 16 untracked); the only change in `~/duckstation` is a non-destructive lightweight tag.

**1 — Preservation set** (in `~/duckstation-fork-preservation/`, outside both repos; sizes/hashes pinned):

| Artifact | Captures | SHA-256 |
|---|---|---|
| `duckstation-external-debugger-control.bundle` (175 MB) | committed history (`bundle verify` OK; complete history; `external-debugger-control` → `296955321`) | `72aa9fb08b45bf1ff3aa38bd2d5973a1d2044cc4472cf4f17f1016f29e602195` |
| `working-tree-tracked.patch` (382 KB) | 34 tracked modifications vs HEAD (`git diff --binary`) | `d0b29800476250f800205cf0a0b2e417b8530f9cedfe9e94abcb0d8fcd7a2af8` |
| `untracked-source.tar.gz` (31 KB) | 23 untracked source/test/launcher files | `c9279b282c377d2dfeab7974eacce269bddecf41e50ac36c378fa715ba7b3f76` |

In-repo anchor tag (non-destructive): `abl-gap0001-fork-296955321` → `296955321…` in `~/duckstation`.

**2 — Reconstruction verified byte-exact.** An independent clone of the bundle + `git apply` of the patch + extraction of the archive reproduces the operator's running source **byte-identical across all 57 changed files (0 mismatch)** — tracked dispatch/service/GPU/system/cdrom plus all seven dirty-only modules, the client, and the launcher. So the committed-vs-dirty split is now pinned to recoverable artifacts, not just a dirty tree.

**3 — Clean clone rebuilt `duckstation-qt`.** Build host: Fedora Linux, CMake 4.3.0 + Ninja, clang/clang++ 22.1.7, vendored Qt6/OpenGL/Vulkan/Wayland dependency pack (`dep/prebuilt/linux-x64`, gitignored, 208 MB — symlinked into the clone, not re-vendored). Exact steps (reproducible from any clean clone of the preserved state):

```bash
git clone duckstation-external-debugger-control.bundle abl-fork-build
cd abl-fork-build && git checkout external-debugger-control      # HEAD = 296955321
git apply /path/to/working-tree-tracked.patch                    # dirty tracked layer
tar -xzf /path/to/untracked-source.tar.gz                        # dirty untracked layer
ln -s <owned-duckstation>/dep/prebuilt/linux-x64 dep/prebuilt/linux-x64   # build dep, owner-supplied
cmake -B build-release -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
cmake --build build-release --target duckstation-qt
```

Clean-built binary SHA-256 `fd4bf9edc05a39641584b72b589c8d10f16539aec5bb47cca973f61b29bbefbb` (the operator's dirty build was `796965d7…`; the binaries differ but the source is byte-identical — a clean build is not bit-reproducible here, which is expected and not required).

**4 — Headline replay reproduced from the clean-built binary.** `tools/trace_spawn_floor.py` (the [[Experiment - Spawn-floor render source]] / GAP-0011 headline) was run via the isolated launcher pointed at the clean-built binary (`--binary …/abl-fork-build/build-release/bin/duckstation-qt`), the pristine disc (`SCUS-94288`, `.cue` SHA-256 `463102187c…`), and fixture `SCUS-94288_1.sav`. Result **PASS (exit 0)**: spawn-floor packet writer = `fcn.80010000` (CONFIRMED), `a0` 20/20 in DAT (file span `0x15dec..0x2f59c`), `fcn.800172dc` 0 calls, collision table `0x800a7e48` separate → visible floor = LEVEL.DAT, visual ≠ collision. The replay uses `gpu.pickObject`, a **dirty-only** method — so committed HEAD alone is insufficient and the dirty layer is genuinely required. Instance stopped cleanly afterward (`stop` killed only its own PID).

**5 — Required operator guide:** `.claude/skills/duckstation-external-debugger/SKILL.md` is the entry point for any live-debugger work (isolated config/port/token, identity verification, re-arm-after-load, evidence standard).

**Method/source pin:** see `tools/duckstation_rpc_method_manifest.md` (114 committed @ `296955321` + 27 dirty-only, each layer tied to its recoverable artifact; the replay's method→layer table).

**Lone residual (operator-only):** copy `~/duckstation-fork-preservation/` off-host and/or push `external-debugger-control` + the tag to a private remote. Not autonomously possible — `origin` is upstream stenzek (must not push there) and no credentials were assumed. Until then, the recoverable mechanism exists and is verified but lives on the same disk as the fork, so single-host loss is the remaining (now-trivial-to-close) exposure for [[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]].

## Fork identity observed 2026-06-20

| Field | Evidence |
|---|---|
| Local location | `~/duckstation` (`~/duckstation` on this host) |
| Git repository | Yes |
| Branch | `external-debugger-control`; no configured upstream |
| HEAD | `296955321fd9375fa94692d96df788eccd708135` |
| Describe | `preview-65-g296955321-dirty` |
| Base/upstream | merge-base with local `origin/master`: `1cce275db36dba5b992fafeb59e8560929a19e60`; custom HEAD is 65 commits ahead |
| Remote | `origin = https://github.com/stenzek/duckstation.git` (upstream project only) |
| Recoverability | No remote branch or tag contains `296955321`; the custom branch is local-only |
| Worktree | **Dirty:** 34 modified tracked paths + 16 untracked status entries (**23 files** when `src/core-tests/` is expanded; corrected 2026-06-21 from the earlier "24") |
| Build system | CMake + Ninja; Release; clang/clang++; IPO enabled; in-tree/prebuilt Qt6 dependency pack |
| Built binary | `build-release/bin/duckstation-qt`, 35,755,264 B, SHA-256 `796965d722b6c2c5d135f4c3e457e68e16f20cab632c3ab2ef43b3708f8c6501` |
| Build SCM record | `296955321…`, branch `external-debugger-control`, `0.1-11520-g296955321-dirty` |

The object for `debuggerrpc.cpp` is newer than its source and the binary is newer than that object, so the local binary was built from a dirty tree close to the inspected source. This is useful local evidence, **not** a recoverable source revision: uncommitted bytes and untracked files have no Git identity.

Rechecked read-only during M3 finish-up on 2026-06-20: branch, HEAD, remote, describe string, and dirty counts are unchanged from the first M3 audit.

## Current dirty-file inventory

Modified tracked paths (34):

`EXTERNAL_DEBUGGER_CONTROL.md`; `docs/external-debugger-experiment-runner.md`; `docs/external-debugger-movie.md`; `docs/external-debugger.md`; `scripts/debugger-client/README.md`; `scripts/debugger-client/duckstation_debug_client.py`; `scripts/debugger-client/mcp_bridge.py`; `src/CMakeLists.txt`; `src/core/CMakeLists.txt`; `src/core/cdrom.cpp`; `src/core/cdrom.h`; `src/core/core.vcxproj`; `src/core/core.vcxproj.filters`; `src/core/debugger_control_service.cpp`; `src/core/debugger_control_service.h`; `src/core/gpu.cpp`; `src/core/gpu.h`; `src/core/gpu_backend.cpp`; `src/core/gpu_backend.h`; `src/core/input_movie.h`; `src/core/system.cpp`; `src/core/system.h`; `src/core/system_private.h`; `src/duckstation-qt/debuggerrpc.cpp`; `src/duckstation-qt/debuggerrpc.h`; `src/duckstation-qt/debuggerserver.cpp`; `src/duckstation-qt/debuggerserver.h`; `src/duckstation-qt/input_movie_file.cpp`; `src/duckstation-qt/input_movie_file.h`; `src/duckstation-qt/mainwindow.cpp`; `src/duckstation-qt/mainwindow.h`; `src/duckstation-qt/mainwindow.ui`; `src/duckstation-qt/qthost.cpp`; `src/duckstation-regtest/regtest_host.cpp`.

Untracked files (23; 16 status entries — Git collapses the test directory into one default status entry; the archived `untracked-source.tar.gz` contains exactly these 23):

`scripts/debugger-client/launch_debugger_instance.sh`; `src/core-tests/CMakeLists.txt`; `src/core-tests/cd_provenance_tests.cpp`; `src/core-tests/code_analysis_tests.cpp`; `src/core-tests/frame_diff_tests.cpp`; `src/core-tests/gpu_object_picker_tests.cpp`; `src/core-tests/gte_camera_tests.cpp`; `src/core-tests/movie_edit_tests.cpp`; `src/core-tests/write_index_tests.cpp`; `src/core/cd_provenance.{h,cpp}`; `src/core/code_analysis.{h,cpp}`; `src/core/frame_diff.{h,cpp}`; `src/core/gpu_object_picker.{h,cpp}`; `src/core/gte_camera.{h,cpp}`; `src/core/movie_edit.{h,cpp}`; `src/core/write_index.{h,cpp}`.

API-relevant dirty files are therefore still present: the RPC/service/server/client/docs paths plus the seven untracked implementation module pairs and their eight test sources. Nothing under `~/duckstation` was modified by M3.

## Source, build, and setup evidence

- Core service: `src/core/debugger_control_service.{h,cpp}`.
- JSON-RPC dispatch: `src/duckstation-qt/debuggerrpc.{h,cpp}`.
- WebSocket/raw-TCP server and authentication: `src/duckstation-qt/debuggerserver.{h,cpp}`.
- Settings UI: `src/duckstation-qt/externaldebuggersettingswidget.*` plus main-window integration.
- Client/MCP: `scripts/debugger-client/duckstation_debug_client.py`, `mcp_bridge.py`, `README.md`.
- Primary contracts: `EXTERNAL_DEBUGGER_CONTROL.md`, `docs/external-debugger.md`, `docs/external-debugger-determinism.md`, `docs/external-debugger-experiment-runner.md`, `docs/external-debugger-movie.md`.
- Dirty-only implementation modules include `code_analysis`, `cd_provenance`, `frame_diff`, `gpu_object_picker`, `gte_camera`, `movie_edit`, and `write_index`, with corresponding untracked core tests.
- Build recipe recorded by the fork: configure using CMake/Ninja and the dependency pack, then `cmake --build build-release --target duckstation-qt`. The external debugger adds no separate third-party library beyond the fork's Qt/core dependencies.
- Runtime defaults: disabled, loopback `127.0.0.1`, port `2346`, token authentication. The isolated launcher uses a separate config/port and reuses the operator's BIOS read-only; the launcher itself is currently untracked.

## API evidence in this vault

The API is **not undocumented**. [[DuckStation API Index]] maps 35 feature notes, backed by individual `API - …` notes and [[Playbook - Create a deterministic experiment]]. Important groups already present:

- connection/auth, execution control, registers, disassembly, breakpoints, save/load state, controller input;
- structured/scatter memory reads, writes, and `memoryScan`;
- `accessLog`, `execTrace`, `transferLog`, `gp0Trace`, CD overlays;
- GPU/VRAM, texture decode, GTE/PGXP, frame capture/hash/diff, snapshot bundles;
- findings/fixtures, symbols, deterministic experiments, and input movies;
- worktree-era notes for media control, camera transform, `gpu.pickObject`, in-memory frame diff, xrefs/function bounds, and crash-safety events.

Related navigation/evidence notes inspected: [[Reproducibility Checklist]], [[Fixtures Index]], [[Toolchain Census]], [[Tools Catalog]], [[Confirmed Knowledge]], [[Gap Audit]], [[Roadmap]], and the experiment/finding notes cited from the API index. The API index and several API notes currently contain unrelated user WIP and were deliberately left untouched by this task.

## Method boundary: committed vs dirty-only

> Re-verified 2026-06-21 by diffing the dispatch table in the working tree against `git show HEAD:…debuggerrpc.cpp`: **114 at HEAD, 27 dirty-only, 0 removed** — unchanged from the prior audit. The full per-method list with each method's recoverable layer is now pinned in `tools/duckstation_rpc_method_manifest.md`.

Direct inspection of the dispatch table found **114 methods at committed HEAD**:

- `debugger.*`: status/pause/resume/reset/step/run/advance, registers, disassembly, memory scalar/block/structured/scatter operations, breakpoints, stack, labels/comments/symbol import/export, PGXP, and GTE state.
- `emulator.*`: save/load/state info, controller injection, frame advance/until, frame capture/video/hash/file diff/snapshot bundle, CD-ROM and DMA state.
- `memoryScan.*`: start/refine/results/clear.
- `accessLog.*`: add/remove/clear/get/run.
- `execTrace.*`: add/remove/clear/get/run.
- `gp0Trace.*`: start/stop/get/clear.
- `transferLog.*`: start/stop/get/clear.
- `cd.*`: overlay file/sectors, clear/list overlays.
- `gpu.*`: status, VRAM rect, CLUT, texture decode.
- `findings.*`, `fixtures.*`: persistent RE evidence and fixtures.
- `experiment.*`: run, compare runs, memory/register diffs.
- `movie.*`: record/play/save/load/status/clear.

The current dirty source dispatches **27 additional methods not present at HEAD**:

`accessLog.findFirstWrite`, `accessLog.lastWriter`, `debugger.functionBounds`, `debugger.xrefsTo`, `emulator.bootSystem`, `emulator.closeMedia`, `emulator.getMediaInfo`, `emulator.getSpeed`, `emulator.loadMedia`, `emulator.setFastForward`, `emulator.setTurbo`, `experiment.warpAndSettle`, `gpu.captureFrameSnapshot`, `gpu.clearFrameSnapshot`, `gpu.diffCurrentFrame`, `gpu.getCameraTransform`, `gpu.listFrameSnapshots`, `gpu.pickObject`, `movie.activate`, `movie.append`, `movie.branch`, `movie.editFrame`, `movie.get`, `movie.list`, `movie.remove`, `movie.store`, `transferLog.resolve`.

Therefore vault notes describing those 27 methods are tied to the **current dirty worktree/binary**, not solely to commit `296955321`. Representative untracked WIP notes are `API - gpu.pickObject`, `API - camera transform`, `API - xrefs and function bounds`, `API - in-memory frame diff`, and `API - media control`; tracked-but-dirty notes add sections to [[API - accessLog]], [[API - transferLog]], [[API - experiment runner]], and [[API - movie]]. These WIP files were inspected but not staged or modified.

## Evidence levels

### Confirmed directly from the fork

- repository/branch/HEAD/remote/status/build configuration above;
- committed and dirty-only method lists from `debuggerrpc.cpp`;
- API implementation/doc/client paths;
- current binary hash and dirty SCM version;
- build target and local dependency assumptions.

### Confirmed only from documentation or prior notes

- the fork docs report live validation of transports, auth, deterministic experiments, findings/fixtures, traces, CD overlays, movies, and later worktree features;
- vault experiment notes report ABL-specific use of these calls.

Those validation claims were inspected but **not re-run in this task**. They remain local-only because the fork state, BIOS, disc, and save-state fixtures are not independently recoverable.

### Not confirmed from current repo contents

- an off-machine copy of the custom commit series;
- a remote branch/tag containing custom HEAD;
- a commit containing the 34 modified and 16 untracked worktree entries;
- the exact source tree used for every historical ABL dynamic finding;
- a clean-clone build and representative replay on a second machine;
- redistributable BIOS/disc/save fixtures (intentionally prohibited).

## M3 dependency boundary

- **Reproducible without the fork:** PS-X header/load map facts recorded as metadata; `symbols/re_symbols.sym` validation; DuckStation-compatible CSV parse round-trip; actual r2 consumption of the generated 85-label flag script; overlay LBA/size/hash inventory and static r2 commands.
- **Owner-local but independently repeatable:** re-hashing/disassembling the ignored executable and overlay files from a matching legally dumped image.
- **Local-only dynamic evidence:** prior debugger/API traces, live symbol import/export, scene→overlay residency, and runtime function-bound checks. These must cite this dirty fork state and cannot be called off-machine reproducible.

M3 completion for the modding-grade baseline does not close GAP-0001. It deliberately avoids making live-fork availability a prerequisite for the tracked static/symbol baseline.

## Reproduction path for a second machine

> Steps 1, 3, and 5 were **executed on this host 2026-06-21** (export → clean clone build → headline replay), proving the path works; see **GAP-0001 closure** above. Step 2 (off-host remote) is the lone operator residual. The numbered list is retained as the canonical second-*machine* recipe.

1. Operator commits or patch-exports the dirty fork layer, including the untracked implementation/tests, after reviewing scope.
2. Operator creates a private or otherwise appropriate fork remote and pushes `external-debugger-control`; tag the verified build source.
3. On a second machine: clone that preserving remote, check out the exact tag/commit, obtain DuckStation's documented dependency pack, configure CMake/Ninja, and build `duckstation-qt`.
4. Enable the loopback/token server or use the isolated launcher; never distribute BIOS/disc/save inputs.
5. With locally owned inputs, run a representative closed experiment from [[Playbook - Create a deterministic experiment]] and record fork commit, binary hash, game hash, fixture identity, settings, request, and observed result.
6. Update `tools/FORK_COMMIT.txt` to the clean verified commit and re-run `tools/verify_repro_inputs.py --write` intentionally.

## Local-only preservation recipes (EXECUTED 2026-06-21)

These were run; the produced artifacts and hashes are pinned in **GAP-0001 closure** above. They remain the reproducible recipe (paths shown as used):

```bash
# Preserve committed custom history (DONE -> 72aa9fb0…):
git -C ~/duckstation bundle create ~/duckstation-fork-preservation/duckstation-external-debugger-control.bundle external-debugger-control

# Preserve the dirty tracked layer (DONE -> d0b29800…):
git -C ~/duckstation diff --binary HEAD > ~/duckstation-fork-preservation/working-tree-tracked.patch

# Preserve the untracked layer as a usable archive, not just a name list (DONE -> c9279b28…):
git -C ~/duckstation ls-files --others --exclude-standard -z \
  | tar --null -C ~/duckstation -czf ~/duckstation-fork-preservation/untracked-source.tar.gz -T -

# Non-destructive in-repo anchor for the committed HEAD (DONE):
git -C ~/duckstation tag abl-gap0001-fork-296955321 296955321fd9375fa94692d96df788eccd708135

# STILL OPERATOR-ONLY — replicate off-host (no credentials assumed; origin is upstream):
#   copy ~/duckstation-fork-preservation off-machine, OR
git -C ~/duckstation remote add preservation <PRIVATE_OR_APPROPRIATE_REMOTE_URL>
git -C ~/duckstation push -u preservation external-debugger-control abl-gap0001-fork-296955321
```

Per policy, the bundle/patch/archive are **not** committed into this ABL repo (large source + would vendor the emulator). This repo records only their hashes/paths, the method manifest, and the build/replay steps. Do not add a bundle, full source copy, BIOS, disc, or save state here without an explicit preservation/licensing decision.

## Exact closure conditions

The acceptance set is **MET on this host (2026-06-21)**: ✅ dirty work exported (bundle + patch + untracked archive, byte-exact reconstruction verified); ✅ custom history captured in a recoverable bundle/patchset + in-repo tag; ✅ clean clone builds `duckstation-qt`; ✅ API contract pinned to commit `296955321` + dirty layer (method manifest); ✅ one representative ABL experiment (`tools/trace_spawn_floor.py`) reproduces from the clean-built binary and documented local inputs. **The one condition not yet satisfied is physical off-host storage** — the recoverable mechanism exists and is verified, but every copy is on the operator's machine. Pushing to a private remote (or copying the set off-machine) requires operator credentials/ownership and is the lone residual; it does not require any further analysis.

## Related

[[DuckStation API Index]] · [[API - connection and auth]] · [[API - determinism]] · [[API - experiment runner]] · [[API - symbols]] · [[Fixtures Index]] · [[Reproducibility Checklist]] · [[Toolchain Census]] · `tools/FORK_COMMIT.txt` · `tools/abl_dbg.py`
