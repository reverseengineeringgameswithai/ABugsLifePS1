---
kind: experiment
id: EXP_2026_07_14_phase3_iteration10_hook_toolchain_closure
status: reproduced
created: 2026-07-14
updated: 2026-07-14
confidence: high
related:
  - PLAYBOOK_game_solving_phase_3
  - DUCKSTATION_API_INDEX
  - EXP_2026_07_14_phase3_iteration9_rpc_manifest_freshness
---

# Phase 3 iteration 10 — hook confidence and immutable toolchain replay

## Trigger and authority

The iteration-2 fresh verifier rejected the green Phase-3 gate for four concrete
reasons. The generated hook summary hid degraded recovered-extent confidence;
the roadmap hub contradicted the Phase-3 note about continuation checking; the gate
did not itself compare the retained RPC manifest with the current external fork; and
an all-stage replay failed at finalization after its canonical executable was replaced
in place. The acceptance contract SHA-256 is
`538666948ed9731e52fa657080a27f1b60f1b8ec931d79c0b22aa991698c7463`.

This experiment uses the hash-verified pristine retail CUE/BIN as original-game
authority. ALLMODS was neither mounted nor used as an oracle. The memory card needed
to reproduce the existing from-boot movies remains external, centrally declared in
`config/phase3_runtime_fixtures.yaml`, and hash-pinned to
`63c08f0143e7b714309de900905f22944ae07f1da881ce9aa3a0237a5dacf517`.

## Observation, inference, and causal confirmation

**Hook observation.** `blackberry:terrain_emitter_color` has top-level status
`degraded`; its CFG liveness confidence and post-build discharge confidence are both
`degraded` with reason `recovered_extent`. The built cave has no hard finding and its
declared live-register writes are accounted, but the recovered containing-function
extent is not exact.

**Hook inference.** A clean post-build accounting result does not upgrade the input
liveness boundary. This is one degraded accounted row, not an exact-confidence
discharge.

**Hook causal confirmation.** `tools/phase3_hook_contract.py` now orders confidence
before the discharged status during aggregation. Regeneration reports 5 proven,
9 exact-confidence discharged, 1 degraded, and zero unverified, owed, refused, or hard
violations. The focused guard explicitly asserts the terrain row and falsifies unsafe
fixtures. `tools/phase3_contradictions.py` also requires this same raw confidence in
the hook artifact, finding registry, hub, and Phase-3 note.

**Toolchain observation.** The prior long replay's running inode retained the selected
bytes, but `/proc/<pid>/exe` ended in `(deleted)` after the mutable canonical path was
replaced. A byte-identical executable copied to a private `/tmp` runtime tree then
stalled during Qt startup before opening the debugger endpoint. The exact canonical
binary opened the endpoint normally.

**Toolchain inference.** The replay needs an independent executable inode without
changing Qt's application directory. Copying the executable alone is insufficient if
the application directory moves; copying it beside the canonical executable preserves
resource discovery. The remaining libraries/resources must have their own before/after
identity so a support-tree change cannot pass unnoticed.

**Toolchain causal confirmation.** `tools/live_toolchain_snapshot.py` first re-extracts
the current fork and compares it with the retained RPC manifest. It creates a unique,
exclusive, read-only executable sibling in `build-release/bin`, privately copies the
hash-pinned launcher/client under `/tmp`, and pins 207 release support files separately.
The sibling opened RPC and mounted `SCUS-94288`; exact config/PID/path/hash validation
then stopped it with SIGTERM and removed only that sibling. Unit and local-media tests
mutate private bytes and external identity to prove rejection.

## Current retained toolchain identity

- External revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`.
- Dirty status: 87 paths; SHA-256
  `bb9ad177f836cd45546a5e487fc3cdf8731c44b04eaaaeb37f522cca655eee7d`.
- Dispatcher SHA-256:
  `b1be4d512eae5c67608453adcbabb32e03612c3ead51856c41ab9c0d140f47be`.
- Release binary SHA-256:
  `27d064bcbdfefadf91fd9401d158a2756dc6bbf6d52a0bb2d3a3dfad7129cb54`.
- Release support tree: 207 files, 102,191,973 bytes; manifest SHA-256
  `e2c7a483cf6722568edac54ff3e55689fc752aa0e11b34d7405ae585efaea3d0`.
- RPC census: 114 committed + 89 dirty-only - 0 removed = 203 current methods.

The first successful 16-stage snapshot replay used an intermediate binary
`a04a6dc3cf181ca864bd78aad36617b49902fa3cf1201a73eb3242d2fdb3b84a`.
The post-run current-fork guard correctly rejected closure because the dispatcher and
canonical binary changed during that replay. No predicate was weakened: a second fresh
snapshot replay used the current identity above.

## Current all-stage reproduction

The replay used a newly created config
`/tmp/dsrepro-phase3-i10-transition-current`, dedicated loopback port `23479`, a
redacted per-run token, and snapshot control directory
`/tmp/duckstation-phase3-i10-transition-current`. Before the run:

- `python3 tools/build_identity.py --verify` passed 327/327 staged pristine pins;
- `tools/verify_live_session_environment.py --profile movie-replay-v1` verified
  CachedInterpreter, normal CD speed, no rewind/runahead/overclock/8MB RAM, analog
  controller, and `PatchFastBoot=false`;
- the launcher used `-fastboot` only to establish RPC, after which each from-boot
  movie power-cycled through `movie.startPlayback(load_start_state=true)` before
  evidence frame zero;
- `emulator.getMediaInfo` plus the pristine build pins verified the mounted CUE and
  referenced track before observations.

`python3 tools/phase3_transition_reset.py --all ... --toolchain-snapshot <manifest>`
measured **16/16 stages with zero skips**. The load gap remained 450–1170 frames
(median 540), and the five session-owned fields remained
`enemy_permanence_quota`, `grain_count`, `health_true`, `lives`, and
`seed_counter_orange`. Finalization verified the running inode hash, immutable snapshot,
source dependencies, runtime support tree, settings/config ownership, and pristine
media; it stopped only the exact owned PID with SIGTERM and removed the exact owned
sibling. `analysis/phase3_transition_reset.json` SHA-256 is
`efb53981856cbdfd8f9fce5b6ec98a0e2726ed7b10d4087b3c47ffc538506a3f`.
An immediate `phase3_duckstation_rpc_manifest.py --check` returned FRESH for 203
methods and 87 dirty paths.

## Safe, local-media, and clean-checkout validation

The source/evidence commit `ff420817ddfe116e4188bef04d0dd2bc980c50b3` was cloned
with `git clone --no-local` into `/tmp/phase3-i10-clean-jkdxem`. The first clone
attempt stopped on the user filesystem quota rather than being reported as a pass;
old task-owned clean-checkout clones under `/tmp` were removed, and the proof was
restarted from a newly created directory.

Only the central provisioner introduced external bytes:

`python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL`

It copied exactly 1,262 declared inputs. A second invocation with `--verify-only`
verified 1,262/1,262: 3 pristine media, 327 pristine staged inputs, 63 non-pristine
fixtures, 127 strict-pristine fixtures, 63 pristine-serial fixtures, 651 derived-retail
assembly files, 3 derived-retail disassembly files, and 25 derived-retail metadata
files. `tools/build_identity.py --verify` independently passed 327/327 staged pins.

The clean clone then reproduced:

- `mod/build.py --mods mod/mods_code_only.yaml --no-disc`: 1,195 changed EXE bytes,
  output SHA-1 `5936596c576415847b3a7395599e993b36eb7906`;
- all mandatory and inventoried static/local Phase-3 generators: 107 mechanics with
  zero ownership gaps, 63 semantic entries, 234 indirect sites, 20 overlays, 327
  assets, 1,112 functions, 15/15 scenes, 134 native domains, 8 record views with
  181/524 bytes typed, and 12 contradiction rows with zero open;
- hook contracts: 5 proven + 9 exact-confidence discharged + 1 degraded, with the
  built image pin matched and no hard/unverified/owed/refused rows;
- the exact external check: 203 methods, 87 dirty paths, FRESH;
- knowledge: 19/19 findings finished with zero gaps; inventory: 29/29 generators and
  30/30 artifacts, closure-ready; Phase-3 gate: WP1-WP9 and all five bullets MET;
- `python3 tools/run_safe_tests.py`: 382 passed, 30 expected deselections;
- `python3 -m pytest -q -m local_media`: 29 passed, 383 deselected;
- `python3 -m pytest -q tests/test_phase1_*.py tests/test_phase2_*.py`: 61 passed.

`git diff --check` returned no errors, and `git status --short` was empty after the
build, every deterministic regeneration, and both test suites. The final results-only
note commit was also cloned from scratch and rechecked; it changes no generator,
schema, manifest, retained machine artifact, or behavioral claim.

## Knowledge placement and residual

The runtime failure, failed relocation hypothesis, causal test, replay, and cleanup
belong here in Experiments. Exact debugger operating guidance and source identity are
linked from [[DuckStation_API_Index]]. Hook intent and continuation consumption remain
MOD-private; this experiment does not turn the diagnostic image into original-game
authority.

The only hook-confidence residual is exact recovery of the original containing
function for `terrain_emitter_color`; until independent code identity supplies it,
the row must stay degraded. Any future external dispatcher, source dependency,
release binary, or support-tree change reopens the current-fork gate and requires a
new exact snapshot replay for decisive transition evidence.
