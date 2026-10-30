---
kind: experiment
id: EXP_2026_07_14_phase3_ratchet_iteration4_current_live_freshness
status: reproduced
created: 2026-07-14
updated: 2026-07-14
confidence: high
related:
  - PLAYBOOK_game_solving_phase_3
  - DUCKSTATION_API_INDEX
  - EXP_2026_07_14_phase3_iteration10_hook_toolchain_closure
---

# Phase 3 ratchet iteration 4 — current live evidence freshness

## Trigger and authority

The iteration-3 fresh verifier rejected candidate
`a3595eb50a15c300c3c9eaf4a28bc5b148c29f3b`. Its clean clone reproduced the static,
build, fixture, hook, and gameplay predicates, but replaying the current live matrix
rewrote all twelve retained artifacts. Seven declarations still required the historical
release SHA-256 `bd55f9db...` although the declared path held `27d064bc...`; four
artifacts retained an older dirty-source identity; and the transition artifact treated
the timestamp/UUID-bearing snapshot-manifest digest as semantic. The inventory compared
artifacts only with those declarations, not with the actual current external fork and
binaries, so the high-level gate stayed green until a live command exposed the drift.

The acceptance contract SHA-256 is
`538666948ed9731e52fa657080a27f1b60f1b8ec931d79c0b22aa991698c7463`.
Every run below mounted only the hash-verified pristine retail CUE/BIN as original-game
authority. ALLMODS was not mounted or used as an oracle. Saves, movies, the BIOS,
memory-card seed, configs, tokens, and captures stayed external or under `/tmp`.

## Observation, inference, and causal confirmation

**Observation.** The retained artifacts' behavioral payloads reproduced, but their
source and executable provenance did not describe the current toolchain. During the
first repair replay an operator-owned untracked directory appeared in the external
DuckStation worktree, changing its status from 87 to 88 paths without changing the
203-method dispatcher. The newly strengthened join immediately reopened the eleven
regular artifacts already replayed against the 87-path identity. That work was not
accepted as current evidence; the operator directory was preserved untouched, the RPC
manifest was regenerated, and the complete matrix was replayed again.

**Inference.** A declaration cannot be authoritative merely because an artifact agrees
with it. The declaration, retained run, current source/support extraction, and bytes at
the declared executable path must all agree. Per-run snapshot path, sibling name, and
snapshot-manifest digest are audit data but not behavioral identity; the release support
tree digest and executable hash remain semantic and must still force a rewrite.

**Causal confirmation.** `tools/phase3_evidence_inventory.py` now derives normal and
release declarations from the retained RPC manifest, hashes the actual executable paths,
re-extracts the current fork on every inventory/gate run, and joins each retained live
artifact to the exact current RPC semantic/source/binary identity. Regular finalization
in `tools/live_session_provenance.py` independently checks the retained critical source,
docs, launcher/client, selected binary, revision, and dirty-status identity before it
banks that join. Path-scoped semantic normalization ignores only the immutable sibling
path and snapshot-manifest digest; it still treats the 207-file runtime-tree digest as
decisive. Focused tests falsify a stale retained status and prove that a changed runtime
tree rewrites evidence while an equal fresh snapshot preserves retained bytes.

## Current retained toolchain identity

- External revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`.
- Dirty status: 88 paths; SHA-256
  `1c1a325041c78e0545816a605a2dbc7c41a08549642d4f4b8289d9df87baf130`.
- Dispatcher SHA-256:
  `b1be4d512eae5c67608453adcbabb32e03612c3ead51856c41ab9c0d140f47be`.
- RPC census: 114 committed + 89 dirty-only - 0 removed = 203 methods; semantic
  manifest SHA-256
  `e2597de77dc56ff2dc4c4b9d2ff72b9abccb76b203a6d7d2c180aeba29fdd80b`.
- Normal binary SHA-256:
  `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
- Release binary SHA-256:
  `27d064bcbdfefadf91fd9401d158a2756dc6bbf6d52a0bb2d3a3dfad7129cb54`.
- Release support tree: 207 files, 102,191,973 bytes; manifest SHA-256
  `e2c7a483cf6722568edac54ff3e55689fc752aa0e11b34d7405ae585efaea3d0`.

The complete status path list and exact critical file/binary identities are retained in
`analysis/phase3_duckstation_rpc_manifest.json`; the operator-owned external directory
is identified by Git status but is neither imported nor committed here.

## Current pristine live reproduction

Each generator used a newly created absolute config directory, a dedicated loopback
port and redacted token, exact mounted-media verification, and its declared current
binary. The owned launcher reported no live pidfile after every regular run.

- Camera: 48 samples closed 0.1506 of the gap per frame; position/target pokes drifted
  -39,932/-45,425 and confirmed the record is derived.
- Indirect control: 139 `jalr` sites remained 99 global-slot, 36 struct-field, and 4
  reason-bounded unresolved sites across 30 global callback slots. The function-pointer
  aggregate accepted all 42 strict-pristine anchors, refused zero, and retained the
  actor `+0x7C` callback at rate 0.61 with nine handlers.
- Records/render: all 42 strict-pristine record and render anchors passed with zero
  refusals; 8 views account for 181/524 typed bytes. The render pointer table remained
  scene-invariant and only `+0x04,+0x06,+0x07,+0x08,+0x0A` varied by scene.
- Lifetimes/audio/boss: 63 lifetime entries remained 35 measured + 28 derived; the SFX
  sweep found 27 playable IDs and 27 distinct samples; Thud remained bound to boss id
  `0x24`, with HP 1 surviving and HP 0 retiring through the mover updater.
- Training/unknown fields: the strict-pristine scene-17 anchor reproduced SHA-256
  `d41c000504313cccfcf2920dd928ab864b27bf71e699b05a6c0b7d4e030a8795`; all promoted
  player/actor/contact velocity findings reproduced without converting other bytes into
  confirmed fields.
- A07: 193 trials saw 102 block-writer PCs and states `[0,1,2]`; ownership remained
  single, `bounded_negative=true`, and `disproven=false`.

The current immutable transition run used a fresh snapshot and verifier-owned executable
sibling. It measured **16/16 stages with zero skips**, a 450–1170-frame world-load gap
(median 540), and the same five session-owned fields: `enemy_permanence_quota`,
`grain_count`, `health_true`, `lives`, and `seed_counter_orange`. Finalization verified
the source, running inode, support tree, config, media, and exact PID; it stopped only
that PID with SIGTERM and removed only the owned sibling. The retained transition
artifact SHA-256 is
`ab4ccb86916ca206e09f917afd9c20f6814c21d4f1305e96995ce879f0d2bcc6`.

## Validation and clean-checkout reproduction

The source/evidence and computed-gate commits culminated in candidate
`833761726c123db302b9e1d1cc5ce9331607b7ed`, cloned with `git clone --no-local`
into `/tmp/phase3-i4-clean-R8cXoZ/repo`. An initial provisioning invocation was
accidentally run from the source worktree; the clone's immediate `build_identity.py`
check rejected all 327 absent staged files, and no criterion was credited. The command
was rerun from the clone itself:

```bash
python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL
python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL --verify-only
```

The first clone-local command copied exactly 1,262 centrally declared inputs. The
second verified 1,262/1,262: 3 pristine media, 327 pristine staged inputs, 63
non-pristine fixtures, 127 strict-pristine fixtures, 63 pristine-serial fixtures,
651 derived-retail assembly files, 3 derived-retail disassembly files, and 25
derived-retail metadata files. `tools/build_identity.py --verify` then passed 327/327.

The clean clone reproduced every mandatory and inventoried static/local generator:
107 mechanics with zero ownership gaps; 63 semantic entries; 234 indirect sites;
20 overlays; 327 assets; 1,112 functions; 15/15 scenes; 134 native domains; 8 record
views with 181/524 bytes typed; 12 contradiction rows with zero open; and WP1–WP9
MET. The pinned diagnostic build changed 1,195 EXE bytes and reproduced SHA-1
`5936596c576415847b3a7395599e993b36eb7906` and SHA-256
`991fc38c131fe1139df30e9719a222a06a140054f1f8ee46b6321bbd9c0e6808`.
Hook validation against that exact output returned 5 proven + 9 exact-confidence
discharges + 1 degraded recovered-extent row, with zero hard, unverified, owed, or
refused rows. Knowledge remained 19/19 with zero gaps; inventory remained 29/29
generators and 30/30 artifacts CLOSURE-READY; the five-bullet gate remained MET.

Serialized clean-clone suites:

- `python3 tools/run_safe_tests.py`: 385 passed, 30 deselected;
- `python3 -m pytest -q -m local_media`: 29 passed, 386 deselected;
- `python3 -m pytest -q tests/test_phase1_*.py tests/test_phase2_*.py`: 61 passed.

The clone then reran all twelve live commands with newly created absolute config
directories and dedicated ports. Every command printed `semantic replay matched` and
`retained bytes unchanged`, including all three 42-anchor aggregates, the 193-trial A07
run, and a new randomly named immutable transition snapshot. The transition again
measured 16/16 stages, the exact owned launcher reported no live pidfile, and the new
verifier sibling was absent after finalization. A final current-fork extraction returned
203 methods and 88 dirty paths; inventory was CLOSURE-READY and the gate MET.
`git diff --check` returned no errors and `git status --short` was empty after the
build, all deterministic regeneration, all suites, and all twelve live replays.

## Knowledge placement and residual

This note owns the stale-evidence diagnosis, failed 87-path intermediate replay,
current pristine runtime observations, and causal guards. Exact API/toolchain identity
is indexed in [[DuckStation_API_Index]]. No MOD-private hook or intended behavior
changed, and no runtime experiment was promoted to Canon beyond its existing bounded
claim.

The external debugger remains an explicit dirty toolchain. Any change to the current
revision, status identity, critical source/docs/client, either binary, or the release
support tree reopens the inventory and gate. A07 remains bounded-negative rather than
disproven; F09/D18, LEVEL10, callback ABI, actor vertical ownership, frontend lifecycle,
and the degraded recovered hook extent remain Phase-4 or bounded residuals.
