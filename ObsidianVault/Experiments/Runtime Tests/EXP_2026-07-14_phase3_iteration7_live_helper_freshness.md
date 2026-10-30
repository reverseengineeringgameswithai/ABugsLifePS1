---
kind: experiment
id: EXP_2026_07_14_phase3_iteration7_live_helper_freshness
status: reproduced
created: 2026-07-14
updated: 2026-07-14
confidence: high
related:
  - PLAYBOOK_game_solving_phase_3
  - EXP_2026_07_14_phase3_iteration6_clean_provision_replay
---

# Phase 3 iteration 7 — shared-helper freshness and complete live replay

## Trigger and authority

The iteration-6 fresh verifier found that 11 committed live artifacts retained
obsolete `tools/live_session_provenance.py` SHA-256 values (`0bdf7e8a...` or
`19798ecb...`) while the current helper was
`083719f77586d45f82b9a6550cc49388df1f6e0ca403b4a6c4fb18bc6f4070b4`.
`tools/phase3_evidence_inventory.py` still reported CLOSURE-READY and
`tools/phase3_gate_audit.py` still reported MET. A fresh camera replay changed
`analysis/phase3_camera_record.json`, adding the current helper hash, the central
save-fixture declaration, and hash verification of the state-embedded retail media.

The acceptance contract SHA-256 was
`538666948ed9731e52fa657080a27f1b60f1b8ec931d79c0b22aa991698c7463`.
Original-game authority was only the pristine retail CUE SHA-1
`25adb139e50ba28c2d9c1ecab4528e9cf004b1d5` and BIN SHA-1
`0bc1a29748d4bd608d076495d085e825574880d1`. ALLMODS was not used as a build or
behavioral input. The provisioner verified all 1,262 centrally declared checkout
inputs, and build identity verified all 327 pristine staged inputs before replay.

DuckStation source was revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` with its complete dirty status retained
in each artifact. The normal binary SHA-256 was
`ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`; the
release binary SHA-256 was
`bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.

## Observation, inference, and causal confirmation

**Observation.** Eleven live artifacts named an older helper even though their own
generator hashes were current. Six save-backed artifacts also predated the helper's
central fixture declaration and embedded-media hash fields. The inventory joined
retained evidence to the generator binary and mounted retail media, but not to the
shared Python helper that enforced those checks.

**Inference.** A generator-only freshness edge is insufficient when behavior-critical
validation lives in an imported helper. The artifact must name both source hashes and
must be replayed whenever either changes. Same-serial save metadata is also
insufficient because a MOD save can retain `SCUS-94288`.

**Causal confirmation.** The inventory now hashes
`tools/live_session_provenance.py` as a shared dependency for every live mode and
compares both retained source hashes. It independently requires each loaded save's
central fixture declaration plus complete embedded CUE/track hash results. The gate
checks the same helper/generator freshness for decisive evidence and reads save anchors
from `run_provenance.anchor` rather than the wrong document level. Falsification tests
replace a helper hash and remove state-media fields; both inventory and gate exit 1.
After fresh replay of all 11 invalidated artifacts, both tools return 0 and every gap
list is empty.

## Isolated live replay

Every row below used a newly created absolute `/tmp` config, dedicated loopback port
and ephemeral token, prelaunch and post-connect retail-media hashing, the declared
settings profile, pre-load `emulator.getStateInfo` where applicable, disc validation,
instrument re-arming after loads, and launcher-owned PID cleanup.

| Artifact | Port | Isolated config | Binary | Direct reproduced result |
|---|---:|---|---|---|
| `phase3_camera_record.json` | 25170 | `/tmp/duckstation-phase3-i7-camera-o2LyrJ` | release | 48 samples; follow 0.1506; both pokes overwritten |
| `phase3_jalr_callbacks.json` | 25171 | `/tmp/duckstation-phase3-i7-jalr-bYyXuM` | release | 139 sites; 30 global slots; 36 struct-field calls |
| `phase3_fn_ptr_fields.json` | 25172 | `/tmp/duckstation-phase3-i7-fnptr-1AyIxb` | normal | 42/42 strict-pristine anchors; actor `+0x7C`, 9 handlers |
| `phase3_render_descriptors.json` | 25173 | `/tmp/duckstation-phase3-i7-render-wW7GpE` | normal | 42/42 anchors; stable pointers; five varying offsets |
| `phase3_transition_reset.json` | 25174 | `/tmp/dsrepro-phase3-i7-transition-bgOV9A` | release/movie | 16/16; load gap 450–1170, median 540; exit does not reclaim world |
| `phase3_semantic_lifetime.json` | 25175 | `/tmp/duckstation-phase3-i7-lifetime-GevPQ0` | release | 63 entries: 35 measured, 28 derived |
| `phase3_sfx_interface.json` | 25176 | `/tmp/duckstation-phase3-i7-sfx-wtZkdY` | release | 27 playing IDs, 27 distinct samples; `v0` not success |
| `phase3_unknown_fields.json` | 25177 | `/tmp/duckstation-phase3-i7-unknown-aqOSnL` | release | player/contact/actor motion and TTL controls reproduced |
| `phase3_training_anchor_fixture.json` | 25178 | `/tmp/duckstation-phase3-i7-training-jYTi0f` | normal | scene-17 fixture verified at SHA-256 `d41c0005...8795` |
| `phase3_thud.json` | 25179 | `/tmp/duckstation-phase3-i7-thud-h1B5Hr` | release | id `0x24`, HP 50; HP=1 survives, HP=0 retires |
| `phase3_spin_functional.json` | 25180 | `/tmp/duckstation-phase3-i7-spin-xaqpmY` | release | 193 trials, 102 writer PCs, values `[0,1,2]`, bounded negative |

The retained artifact SHA-256 values, in the same order, are
`8b07d1d3a4e0f7a5cb731f1e6d4db6f427c50876fd021ea4c83dae85682732f4`,
`c6b2032cd1f26ef387e447cafe004fe41e49a237ba457e86f88bd17104f01850`,
`5165dbaaeb3fe4becd0d899a1f3cf9129e49be95bd5a790d00f9dea68e556afd`,
`4759d9552cc181169adbd3319520aa4625e8b1195d71bda007a21ae43e81e7b7`,
`46c3fd6fed956bd4c804ae91a59d7b5a8fae85b2c7c0228be4db92b19d7e5fc5`,
`2d8c44d4b66f438b9abb46e7d2a132d935dad31376d47187be85db4ee0e6fd74`,
`1985b89fdde5009a59a43ef460a09da7525104672e0059a83cc5a72a40716a13`,
`4163962ac151d2700dd03d656a473eda2a9618e0a9fb6ef1fff2c3ffab593e29`,
`c0a2d8288e33544cdc93eab5207b9ac6374861eb5d5a9892d66e91ef21ca641d`,
`83965e0f54d188f1a90de9a76eaab170d299cc38ab03c7472090fcca6c612e31`, and
`76940d5ed2b38b9221eab5d2f88ecb10f3561610f1a7821e133bee56797e27a2`.

The transition replay additionally verified the centrally declared 128-KiB card seed
SHA-256 `63c08f0143e7b714309de900905f22944ae07f1da881ce9aa3a0237a5dacf517`
and the isolated card copy. The full stage sweep used the `movie-replay-v1` profile
(CachedInterpreter, fast boot off, analog controller); every other run used
`isolated-defaults-v1`. All 11 artifacts record `cleanup.owned_pid_stopped=true`.

## Machine-layer results

Regeneration after the live runs reports 107/107 mechanic frontiers, 63 semantic
entries, 134 native-domain rows, 234 indirect sites, 20 overlays, eight record views
with 181/524-byte accounting, 1,112 functions, 327 assets, ten reconciled/bounded
contradictions, WP1–WP9 MET, and 19/19 findings finished. The diagnostic no-disc build
changed 1,195 EXE bytes and reproduced SHA-1
`5936596c576415847b3a7395599e993b36eb7906`; all 15 hooks were accounted (five
proven, ten discharged) with zero hard, owed, unverified, degraded, or refused rows.

Working-tree validation before the candidate commit:

- `python3 tools/run_safe_tests.py`: 371 passed, 28 deselected.
- `python3 -m pytest -m local_media -q`: 27 passed, 372 deselected.
- `python3 -m pytest -q tests/test_phase1_census.py tests/test_phase2_*.py`: 61 passed.
- `python3 tools/phase3_evidence_inventory.py`: 28/28 generators and artifacts,
  CLOSURE-READY, zero source dependency, environment, or save-origin gaps.
- `python3 tools/phase3_gate_audit.py`: WP1–WP9 and all five exit bullets MET.

## Clean-checkout reproduction

Candidate `831d8a2df1128ffaf974bacc48b7533e5c93eccb` was cloned with `git clone
--no-local --no-hardlinks` to `/tmp/phase3-i7-clean-831d8a2-XuAQ1k`. The guarded
provisioner copied and then independently verified 1,262/1,262 centrally declared
inputs from `~/Downloads/ABL`; build identity verified 327/327 pristine
staged inputs. Complete static/local regeneration preserved every retained artifact
byte-for-byte and left `git status --short` empty. The clean diagnostic build again
changed 1,195 EXE bytes, produced SHA-1
`5936596c576415847b3a7395599e993b36eb7906`, and accounted for all 15 hooks.

Clean-clone validation observed:

- `python3 tools/run_safe_tests.py`: 371 passed, 28 deselected.
- `python3 -m pytest -m local_media -q`: 27 passed, 372 deselected.
- `python3 -m pytest -q tests/test_phase1_census.py tests/test_phase2_*.py`: 61 passed.
- `python3 tools/validate_vault.py --check`: zero policy, schema, link, evidence-file,
  address, or alias errors.
- `python3 tools/phase3_gate_audit.py`: WP1–WP9 and all five bullets MET.

The verifier's original reproducer was then run once more from that clean clone using
fresh config `/tmp/duckstation-phase3-i7-clean-camera-5hMM4O`, port 25181, the pinned
release binary, and the provisioned pristine retail CUE/BIN. It reproduced the 0.1506
follow factor and both overwrite drifts, printed `semantic replay matched`, and left
`analysis/phase3_camera_record.json` at SHA-256
`8b07d1d3a4e0f7a5cb731f1e6d4db6f427c50876fd021ea4c83dae85682732f4`.
The generator stopped its owned PID, the config-scoped launcher reported not running,
and final `git status --short` remained empty.

No disc image, save, movie, memory card, capture, BIOS, token, credential, or generated
copyrighted output is committed.
