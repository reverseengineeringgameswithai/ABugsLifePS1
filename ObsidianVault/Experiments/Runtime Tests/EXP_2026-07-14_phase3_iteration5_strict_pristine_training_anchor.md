---
kind: experiment
id: EXP_2026_07_14_phase3_iteration5_strict_pristine_training_anchor
status: reproduced
created: 2026-07-14
updated: 2026-07-14
confidence: high
related:
  - PLAYBOOK_game_solving_phase_3
  - SYS_record_layouts_and_lifetimes
---

# Phase 3 iteration 5 — strict-pristine Training anchor correction

## Trigger and identity

Iteration-4 aggregate evidence claimed 42 pristine anchors, but all three Phase-3
breadth artifacts included `collecting_FLIK_LEVELTRAINING.movie.sav` (SHA-256
`8d49193ceaf5c0b2de6f97df1a7c54716322a6276c24b4508810f965eb634400`).
The non-mutating `emulator.getStateInfo` result names `ABL_ALLMODS.cue` as that
state's embedded media. A matching `SCUS-94288` serial was therefore insufficient:
this state is MOD comparison evidence, not original-game authority.

The retail authority used throughout the correction was:

- cue SHA-1 `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5`;
- BIN SHA-1 `0bc1a29748d4bd608d076495d085e825574880d1`;
- external-debugger fork revision
  `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, with its dirty source state
  retained in each live artifact;
- normal debugger binary SHA-256
  `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`;
- replay/SPU binary SHA-256
  `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`;
- replay card seed SHA-256
  `63c08f0143e7b714309de900905f22944ae07f1da881ce9aa3a0237a5dacf517`.

No save, movie, disc image, card, BIOS, capture, or credential is committed by this
experiment. The central fixture manifest contains hashes and preservation metadata;
the operator-owned bytes remain external/ignored.

## Replacement recipe

`collecting_FLIK_LEVELTRAINING.movie.json` is a version-3, 9,299-frame from-boot
movie with SHA-256
`ad2bd05c18521ad885fe82c3bf448270390bbca2b426c8ce7f0565a14ac16df9`.
This experiment originally described the boundary as target movie frame 6900 and
save at emulator frame 6905. Ratchet iteration 6 proved that the separate start and
advance RPCs raced while the guest was running. The executable replacement recipe is
now: pause first, start at index 0, advance from index 0 to playback index 6904, require
emulator frame 6905, then save. That recipe reproduces the same external fixture,
`phase3_pristine_training_gameplay_i5.sav`, size 2,152,414, SHA-256
`d41c000504313cccfcf2920dd928ab864b27bf71e699b05a6c0b7d4e030a8795`.
`tools/phase3_training_anchor_fixture.py` independently verifies its central pin,
embedded pristine media, serial, and scene 17 before use and regenerates a transient
candidate on every invocation. See
[[EXP_2026-07-14_phase3_ratchet_iteration6_training_anchor_lifecycle]] for the
superseding causal evidence and current artifact identity.

Generation used `/tmp/duckstation-phase3-i5-training-fixture-377QRX`, port 24753;
independent verification used `/tmp/duckstation-phase3-i5-training-verify-gG0uHl`,
port 24755. Both owned PIDs were stopped through their configuration-scoped launcher.

## Observation

Before regeneration, the strict-origin audit directly reported three contradictory
aggregates and opened both the knowledge and exit gates. After replacement:

- `phase3_record_probe.json`, `phase3_fn_ptr_fields.json`, and
  `phase3_render_descriptors.json` each accept 42/42 centrally declared
  strict-pristine anchors, retain 42 pre-load inspections, and reject zero;
- contact allocation occupancy peaks at 4/64, leaving 60 slots headroom;
- `actor_record +0x7C` points to a censused entry point in 60.8% of 1,286 sampled
  live actors, across nine handlers, and the jalr census calls that exact offset;
- render-descriptor pointers remain scene-invariant, but strict-pristine target-byte
  variation is exactly `+0x04,+0x06,+0x07,+0x08,+0x0A`; invariant bytes are
  `+0x00,+0x01,+0x02,+0x03,+0x05,+0x09,+0x0B`.

The four former changes at `+0x00,+0x02,+0x03,+0x09` disappear when the ALLMODS
state is removed. This is the decisive observation; it supersedes the old
nine-varying-byte original-game claim.

The updated pristine Training roster also produces a real contact death at actor
record index 7/id 9, raising the all-stage death matrix from 14/16 to 15/16. Its
paused displayed frame is deterministic with SHA-256 beginning `6a36a9e458ff`, and
its contact-pool census has five typed slots.

## Replay-profile failure and causal correction

An intentionally retained failed run used the generic debugger launcher. It could
not call `spu.status` with the stale non-release binary. A second failed collector
used the SPU-capable binary but loaded save states before a from-boot movie; the
restored embedded memory card desynchronized the movie, and allocator wraps collapsed
from five to zero. Both are harness failures, not original-game findings.

The collectors now require `validate_repro_config`, run movie lanes before any
`loadState`, and pause immediately after `movie.startPlayback`. A fresh diagnostic
without that pause observed four uncounted frames before the first sample. With the
pause, two seven-frame sequences at movie frames 5000..5600 were byte-identical and
matched the historical hashes. The final residual run reported deterministic=true,
seven distinct frames, 19/19 deterministic audio anchors, and the expected natural
Bug Bar game-over. The final pool run restored five valid allocator wraps.

## Inference and bounded residuals

It is safe to infer that the four removed descriptor-byte differences were introduced
by the MOD state, because the only aggregate membership change was replacement of the
centrally rejected ALLMODS-origin state and all 42 accepted states independently prove
strict pristine origin. Cross-anchor snapshots still do **not** identify the writer of
the five genuinely scene-dependent bytes; cold-boot or transition write attribution
remains required before naming a loader.

The same freshness review also corrected an unrelated attractive claim: the retained
actor-motion artifact uses one Level01 actor for 40 frames and does not retain rejected
Y candidates. It confirms X/Z fields but cannot prove that all actors lack a stored Y
velocity. `+0x20` remains unknown pending a multi-family vertical-motion artifact.

## Reproduction commands

The decisive collectors were run in fresh absolute configs with unique ports and
ephemeral tokens (tokens redacted in retained provenance):

- Phase-1 census: `/tmp/duckstation-phase3-i5-phase1-census-Jp9Xmn`, 24756;
- Phase-2 baseline: `/tmp/duckstation-phase3-i5-phase2-baseline-4tF5rt`, 24757;
- final death matrix: `/tmp/duckstation-phase3-i5-death-final-FYDTHo`, 24776;
- final residual replay: `/tmp/dsrepro-phase3-i5-residuals-final-0lVztZ`, 24767;
- final pool/arc replay: `/tmp/dsrepro-phase3-i5-pool-final-FTufKl`, 24768;
- full pristine comparison: `/tmp/dsrepro-phase3-i5-compare-f5pk1G`, 24769;
- record aggregate: `/tmp/duckstation-phase3-i5-records-rerun-wn9UgP`, 24773;
- function-pointer aggregate: `/tmp/duckstation-phase3-i5-fnptr-final-bRgaLN`, 24774;
- render aggregate: `/tmp/duckstation-phase3-i5-render-final-UX3bdx`, 24775.

The full comparison directly passed 696 low-level comparisons across 42 anchors and
16 movies with zero mismatches and 42 strict state inspections. Artifact hashes after
the final runs were:

- record probe: `8c96a23eae16048911f699dbc936c527115c8a9dc0d5cb55a0ed367be01db2be`;
- function pointers: `f1bc063be6a74fb048a951706ba94aa92252e9b8bea55adbac15cb5f5d3a36b7`;
- render descriptors: `21adf4c362d331e09279a016033bb4dff20ced75b747c780fcf37d2d64689628`;
- comparison report: `7faf90efb61056430e2821537d00aef623e94394f913108571f4710b71cd1f05`.

## Final validation and clean-checkout correction

The implementation worktree reproduced the pinned code-only image with SHA-256
`991fc38c131fe1139df30e9719a222a06a140054f1f8ee46b6321bbd9c0e6808` and
1,195 changed bytes. `python3 tools/phase3_hook_contract.py` then reported 15
declared hooks: 5 proven, 10 discharged, and zero degraded, cave-unverified, hard,
owed, or refused rows. `python3 tools/run_safe_tests.py` exited 0 with 365 passed and
28 deselected; `python3 -m pytest -m local_media -q` exited 0 with 27 passed and 366
deselected; and `python3 -m pytest -q tests/test_phase1_census.py
tests/test_phase2_*.py` exited 0 with 61 passed.

The first committed-candidate clone at `/tmp/phase3-i5-clean-1114c73` was useful
negative evidence. Provision and every gate/test passed, but deterministic knowledge
regeneration left one tracked line dirty: the fixture graph had not yet named
`tools/phase3_contradictions.py` as an indirect consumer of `level01.sav`. The root
machine layer was regenerated and committed; the dirty clone was not accepted as
durability proof.

The final candidate is reproduced in a newly cloned `/tmp/phase3-i5-final-clean` using
only this command to import external bytes:

```bash
python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL
```

It exits 0 for exactly 1,262 centrally declared inputs: 3 pristine-media files, 327
pristine staged inputs, 63 non-pristine comparison-only fixtures, 127 pristine
fixtures, 63 pristine-serial fixtures, 651 derived retail assembly inputs, 3 derived
retail disassemblies, and 25 derived retail metadata files. A second invocation with
`--verify-only` verifies all 1,262 bytesets in place.

From that clone, the inventory-declared static/local generators, knowledge closure,
WP1-WP9 coverage, ten-row contradiction ledger, five-bullet gate, code-only build,
hook validation, safe suite, local-media suite, and affected Phase-1/2 subset all exit
0 with the same counts and hashes above. `git diff --check`, `git diff --exit-code`,
`git diff --cached --exit-code`, and `git status --short` are empty after deterministic
regeneration; the provisioned copyrighted/operator-owned inputs remain ignored and
uncommitted. Retained live artifacts are accepted only because their executable guards
recompute semantic freshness and the inventory proves complete run provenance,
pre-load state inspections, strict-pristine origins, fixture pins, fork/binary identity,
and owned-PID cleanup.
