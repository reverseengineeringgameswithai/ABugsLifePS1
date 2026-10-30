---
kind: experiment
id: EXP_2026_07_14_phase4_iteration4_current_toolchain_refresh
status: reproduced
created: 2026-07-14
updated: 2026-07-15
confidence: high
related:
  - PLAYBOOK_game_solving_phase_3
  - PLAYBOOK_game_solving_phase_4
  - EXP_2026-07-14_phase4_run_locomotion
---

# Phase 4 iteration 4 — current-toolchain live refresh

## Trigger and authority

The iteration-3 feedback correctly rejected the inherited Phase-3 freshness join:
retained live evidence named release binary SHA-256
`27d064084d5513eb888c30d34408c2f8a20348addb70028a3be24cf91b01b82f`, while the
current external-debugger release binary is
`c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`.
The high-level Phase-3 gate was therefore not evidence of freshness.

Original-game authority for every replay was the hash-verified pristine retail CUE
SHA-1 `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5` and track SHA-1
`0bc1a29748d4bd608d076495d085e825574880d1`. The pristine executable SHA-256 was
`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
ALLMODS was not a build, media, save, or behavioral input. The acceptance-contract
SHA-256 was `1d0d15387b2692145cf1668f4d0e8f9cc783c0c8bb2df1eaebb4bc4776541729`.

The replay identity was DuckStation source revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, complete status hash
`1c1a325041c78e0545816a605a2dbc7c41a08549642d4f4b8289d9df87baf130`,
203 RPC methods, RPC semantic SHA-256
`0f3e6a032a81318afaacbddf5512dd75d0e4fbcda0f4be91d1142acc83f15ed4`,
normal binary SHA-256
`ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`,
and the release hash above.

## Isolation and causal refresh

Each row used a newly created absolute `/tmp` config, a dedicated loopback port and
ephemeral token, connected-media identity verification, and the declared settings
profile. Save-backed runs inspected the save and its embedded media before loading;
instrumentation was armed after load. Cleanup stopped only the PID owned by that
config. The transition run additionally copied the release runtime into an immutable
private sibling, verified its snapshot manifest, and removed only that sibling.

This is causal confirmation of the freshness diagnosis: all twelve Phase-3 live
generators and all three completed/reviewed Phase-4 live campaigns were rerun on the
current binary/API identity. Their regenerated artifacts now pass the low-level
source, environment, mounted-media, save-origin, and owned-cleanup joins. The old
binary hash is retained only in historical experiment notes.

## Reproduced live matrix

| Artifact | Port and fresh config | Direct reproduced result | SHA-256 |
|---|---|---|---|
| `phase3_fn_ptr_fields.json` | 25401, `/tmp/abl-phase4-i4-fnptr-2620529` | 42/42 strict-pristine anchors; actor `+0x7C` callback field retained | `d3a532047f8423306abf756e69d9b31cafd01a422138fdb4b47cd10a3aa41801` |
| `phase3_render_descriptors.json` | 25403, `/tmp/abl-phase4-i4-render-2620529` | 42/42 anchors; stable pointers and bounded post-load varying bytes | `95bd74ba4ce9685b41af48be0f9913bbe7c51c77b74c37c0c68c8538037f53e1` |
| `phase3_training_anchor_fixture.json` | 25404, `/tmp/abl-phase4-i4-training-2620934` | deterministic scene-17 pristine fixture bytes reproduced | `eedf87ab94ff3b9c5d5537865a067e0477b6a43026b28aae9bb043ae67209edc` |
| `phase3_camera_record.json` | 25405, `/tmp/abl-phase4-i4-camera-2621099` | 48 samples; 0.1506 follow factor; both pokes overwritten | `871c9123dbee3a903095778e152efb872d12010f7374a1dd769527df750f52d6` |
| `phase3_jalr_callbacks.json` | 25406, `/tmp/abl-phase4-i4-jalr-2621099` | all 139 `jalr` sites remain bounded | `1d5a41a971417219e754655c3313791749872cee866513f24f7262647e80abd4` |
| `phase3_sfx_interface.json` | 25408, `/tmp/abl-phase4-i4-sfx-2621099` | 27 playable IDs key 27 distinct samples | `5e7616919d67d54faf361925353ea60ff13e1c1ff55a793cdb3a5a94a66afecf` |
| `phase3_spin_functional.json` | 25409, `/tmp/abl-phase4-i4-spin-2621099` | 193-trial A07 bounded negative retained, not promoted to disproof | `a9cee67bfaaacf3cad27ed624a9d8281b3729fb700c18392aa2ccd4c776c84c2` |
| `phase3_thud.json` | 25410, `/tmp/abl-phase4-i4-thud-2621099` | Thud id `0x24`; HP-zero retirement edge reproduced | `1155f1b4c088c209e318b6a35e41f3e51c6121ebb4fef586774b4f9b2b0b5a5f` |
| `phase3_unknown_fields.json` | 25411, `/tmp/abl-phase4-i4-unknown-2621099` | player/contact/actor motion and TTL controls reproduced | `fde8229176a35865d4551dea78b1478ade1072db2a7a0bfa210d2827e2fd45a1` |
| `phase3_transition_reset.json` | 25412, `/tmp/abl-phase4-i4-transition-2623556` | 16/16 stages, no skips; load gap 450–1170 frames, median 540 | `9306816ac329405cece47574e63803f322bf96a980236d1163cf5da54e2bbb3f` |
| `phase4_circle_absence.json` | 25413, `/tmp/abl-phase4-i4-circle-2630860` | A20 default Circle reviewed absence reproduced | `c96af4d2cbfe5089c5157ddbdff10c856bbbf53e71958a35b27d45c3ea490076` |
| `phase4_slow_walk.json` | 25414, `/tmp/abl-phase4-i4-slowwalk-2631801` | A02 19-anchor slow-walk campaign reproduced | `adb3a0b219bdc7dc0e8d39cd191e423464e7c8a01167d78be8f6602eb96d062e` |
| `phase4_run_locomotion.json` | 25421, `/tmp/abl-phase4-i4-run-campaign4-2984332` | A01 controller, breadth, lifecycle, trace, and cold-boot counterfactual reproduced | `96e22099965c4df517b06d798b62c29fd0128e99ec0507b4e33653a7a9d4d7d2` |
| `phase3_record_probe.json` | 25422, `/tmp/abl-phase4-i4-record-probe2-2984332` | 42 strict-pristine anchors; 193/524 typed-byte schema reconciled | `063dc33c9f3e5d85f2636c3f3b0ccbf74ad5c06a798d752c47fabd7b2edc642c` |
| `phase3_semantic_lifetime.json` | 25423, `/tmp/abl-phase4-i4-semantic2-2984332` | 68/68 entries: 39 measured, 29 derived; RAM 54, ROM 13, overlay 1 | `9d5ae734747966aabee9cd3be86145051f55e68157faef3da27d3aea7354aca3` |

Every retained artifact reports `cleanup.owned_pid_stopped=true`; every launcher stop
returned zero. The transition artifact also reports private-binary removal and exact
snapshot verification. No save, movie, memory card, capture, BIOS, token, credential,
or generated disc is committed.

## Machine reconciliation

After A01 added the four heading/local-component semantic entries, the machine layers
recompute 107/107 address-bound mechanics, 68 semantic lifetime entries, 141 native
domains, 193/524 typed record bytes, 19/19 finished findings, WP1–WP9 met, and a
13-row contradiction ledger with 6 reconciled, 7 bounded, and 0 open. These are
dependency-health results, not a Phase-4 closure claim: the Phase-4 scorecard remains
3/107 complete or reviewed rows and 104 open.

## Working-tree and clean-checkout validation

The tested working tree passed `python3 tools/run_safe_tests.py` with 421 passed and
31 deselected, and `python3 -m pytest -q -m local_media` with 30 passed and 422
deselected. `python3 tools/build_identity.py --verify` matched 327/327 staged inputs.
The code-only no-disc build changed 1,195 EXE bytes and reproduced SHA-1
`5936596c576415847b3a7395599e993b36eb7906`; the hook audit accounted 5 proven,
9 cave-discharged, and 1 recovered/undecoded degraded contract with zero unverified,
hard, or refused rows. Vault validation reported zero policy, schema, link,
dead-evidence, address, or alias errors.

A no-local/no-hardlinks clone of candidate
`d917ad8f4c9a4a98a645602dc61e1e43140b13c9` was created at
`~/Downloads/ABL-phase4-ratchet/cleanchecks/phase4-i4-clean-d917ad8-2984332`.
The guarded provisioner copied 1,262/1,262 centrally declared inputs from
`~/Downloads/ABL`, then independently verified 1,262/1,262. Build identity
again matched 327/327. The no-disc diagnostic build was deliberately run before the
safe suite because the deterministic hook-contract regeneration requires its pinned,
ignored patched EXE; an initial pre-build run failed exactly that ordering guard and
was superseded.

With the required order restored, the clean clone reproduced the same build/hash and
hook counts, 421 safe passes, 30 local-media passes, and the zero-error Vault audit.
The low-level Phase-4 tools recomputed 12/12 ranked families, structurally ready
inventories, 3/107 completed or reviewed rows, 104 open rows, WP1/WP6 met, WP2-WP5
open, and all four exit predicates false. Every non-closure prerequisite was true,
and final `git status --short` was empty. A first attempt under `/tmp` was rejected by
the host's disk quota while copying the retail BIN; the incomplete clone was removed
and no result from it was accepted.
