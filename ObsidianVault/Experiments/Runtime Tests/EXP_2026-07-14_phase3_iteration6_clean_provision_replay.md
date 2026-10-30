---
kind: experiment
id: EXP_2026_07_14_phase3_iteration6_clean_provision_replay
status: reproduced
created: 2026-07-14
updated: 2026-07-14
confidence: high
superseded_by: EXP_2026_07_14_phase3_iteration7_live_helper_freshness
related:
  - PLAYBOOK_game_solving_phase_3
  - EXP_2026_07_14_phase3_iteration5_strict_pristine_training_anchor
---

# Phase 3 iteration 6 — clean-provision replay durability

> [!warning] Iteration-7 correction
> The byte-stable 42-anchor record-probe result in this note remains valid, but the
> fresh verifier rejected the broader Phase-3 closure claim: 11 other live artifacts
> retained obsolete shared-helper hashes and the inventory did not detect them. The
> complete dependency guard and live replay are in
> [[EXP_2026-07-14_phase3_iteration7_live_helper_freshness]].

## Trigger and authority

The iteration-5 verifier found that a newly provisioned checkout rewrote
`analysis/phase3_record_probe.json` even though the centrally pinned save bytes and
all observations were unchanged. The acceptance contract used for this correction has
SHA-256 `538666948ed9731e52fa657080a27f1b60f1b8ec931d79c0b22aa991698c7463`.
Original-game authority remained the pristine retail CUE SHA-1
`25adb139e50ba28c2d9c1ecab4528e9cf004b1d5` and BIN SHA-1
`0bc1a29748d4bd608d076495d085e825574880d1`; ALLMODS was not used as an input.

The live replay used external-debugger fork revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` and the normal debugger binary at
`~/duckstation/build/bin/duckstation-qt`, SHA-256
`ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
The release/replay binary remains separately declared at SHA-256
`bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.

No save, movie, disc image, memory card, BIOS, capture, token, or generated image is
committed. The provisioner imported only centrally declared, hash-verified external
inputs from `~/Downloads/ABL`; those bytes remained ignored.

## Observation, inference, and causal confirmation

**Observation.** `emulator.getStateInfo` returned a different `timestamp` after a
byte-identical save was copied into the clean checkout. Its fixture SHA-256, size,
state format/version, serial, embedded retail media, and every sampled record value
were unchanged. The changing number was the copied file's host filesystem mtime.

**Inference.** That host mtime is launch/provision provenance, not emulated semantic
state. Treating it as an observation made a deterministic replay depend on when the
operator fixture happened to be copied.

**Causal confirmation.** `tools/live_session_provenance.py` now excludes only the
`timestamp` key from the semantic comparison. A focused guard provisions identical
bytes with a deliberately different mtime and proves that the retained evidence bytes
do not change. SHA-256, size, state version, retail media, and observations remain in
the semantic comparison. Then an actual newly provisioned clone repeated the live
42-anchor aggregate: the tool printed `semantic replay matched ... retained bytes
unchanged`, and `analysis/phase3_record_probe.json` remained SHA-256
`445478ec1dfd2a6d187a800a551695b4130b05631399c947d59ae9f88b7f7c68` before and
after the run.

## Complete live-environment declaration

The verifier also found that the Phase-3 evidence inventory named generator commands
but omitted the exact launcher, DuckStation binary, retail media, and timing settings
needed to reproduce them. `analysis/phase3_evidence_inventory.json` now declares, for
every live mode:

- the configuration-scoped launcher command with explicit config, port, token,
  binary, and disc arguments;
- the exact normal or release binary path and SHA-256;
- the pristine CUE and track paths, SHA-1 pins, and `tools/build_baselines.json` as
  their pin source;
- an executable settings-verification command and either the
  `isolated-defaults-v1` or `movie-replay-v1` profile.

`tools/verify_live_session_environment.py` checks the binary hash, loopback debugger
binding/port, and the effective execution mode, overclock, CD speed, rewind, runahead,
region, and RAM settings. Omitted generic-launcher values are accepted only as defaults
of the exact hash-pinned binary; conflicting explicit overrides fail. The movie profile
additionally pins cached-interpreter, fast-boot, and controller requirements. Inventory
closure now fails on an incomplete declaration or when retained live evidence names a
different binary or retail-media pin.

## Clean-checkout reproduction

Machine/source commit `218da0883ea0e28d96cc46bf4c3aea5a9c64114c` was cloned with
`git clone --no-local` into `/tmp/phase3-i6-clean-eDoR5Q`. External inputs were
introduced only through:

```bash
python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL
python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL --verify-only
python3 tools/build_identity.py --verify
```

The first command copied exactly 1,262 centrally declared inputs; the second verified
all 1,262 in place; build identity verified 327/327 pristine staged inputs. The live
probe used fresh config `/tmp/duckstation-phase3-i6-clean-record-B3sIMI`, dedicated
port 24881, an ephemeral token, the pinned normal binary, and the provisioned pristine
CUE. Before probing, this command passed and printed the full effective profile:

```bash
python3 tools/verify_live_session_environment.py \
  --config-dir /tmp/duckstation-phase3-i6-clean-record-B3sIMI --port 24881 \
  --binary ~/duckstation/build/bin/duckstation-qt \
  --binary-sha256 ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9 \
  --profile isolated-defaults-v1
```

`python3 tools/phase3_record_types.py --probe` accepted 42/42 strict-pristine anchors,
rejected zero, retained the 181/524-byte typed-record accounting, measured contact
occupancy at 4/64 and actor occupancy at 40/40, and preserved the artifact bytes. The
generator stopped its owned PID; the same configuration-scoped launcher then reported
`not running`.

The inventory-declared static/local generators reproduced 107 mechanics with zero
ownership gaps, 234 indirect sites, 20 overlays, 8 typed records, 15 scenes, 327 assets,
1,112 functions, 134 native domains, 4 reconciled plus 6 bounded contradictions, and
WP1-WP9 MET. `tools/phase3_evidence_inventory.py` reported 28/28 generators and
28/28 artifacts closure-ready; both new environment-gap lists were empty.
`tools/phase3_knowledge_audit.py` reported 19/19 findings finished, and
`tools/phase3_gate_audit.py` recomputed all five exit bullets as MET.

The pristine-based diagnostic build and contract checks were then reproduced:

```bash
python3 mod/build.py --mods mod/mods_code_only.yaml --no-disc
python3 tools/phase3_hook_contract.py
python3 tools/phase3_gate_audit.py
```

The build changed 1,195 EXE bytes and produced patched EXE SHA-1
`5936596c576415847b3a7395599e993b36eb7906`. Hook validation accounted for all 15
hooks (5 proven, 10 discharged) with zero degraded, cave-unverified, hard, owed, or
refused rows and a matching image pin. The gate remained MET.

Final serialized validation in that clone observed:

- `python3 tools/run_safe_tests.py`: 369 passed, 28 deselected;
- `python3 -m pytest -m local_media -q`: 27 passed, 370 deselected;
- `python3 -m pytest -q tests/test_phase1_census.py tests/test_phase2_*.py`: 61 passed;
- `python3 tools/validate_vault.py --check`: zero dangling links, evidence-policy
  errors, dead evidence files, duplicate addresses, missing aliases, or schema errors.

Deterministic regeneration and all validation left `git status --short` empty. The
remaining architecture residuals and confidence bounds are unchanged from
[[EXP_2026-07-14_phase3_iteration5_strict_pristine_training_anchor]]; this iteration
repairs replay durability and environmental completeness, not those semantic bounds.
