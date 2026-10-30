---
kind: experiment
id: EXP_2026_07_14_phase3_iteration8_render_replay_durability
status: reproduced
created: 2026-07-14
updated: 2026-07-14
confidence: high
related:
  - PLAYBOOK_game_solving_phase_3
  - EXP_2026_07_14_phase3_iteration7_live_helper_freshness
---

# Phase 3 iteration 8 — render replay and dirty-evidence durability

## Trigger and authority

The recovery verifier rejected iteration 7 at candidate
`778aca482eea591dbb0ed8e51557ccdd241d9183`. In a fresh checkout,
`tools/phase3_render_descriptors.py` reproduced the same 42-anchor observations but
rewrote `analysis/phase3_render_descriptors.json`: descriptor ids were integer mapping
keys in the live Python document and string keys after JSON reload. The inventory and
gate then still reported CLOSURE-READY/MET while that decisive artifact and the
inventory artifact were modified.

The acceptance contract SHA-256 was
`538666948ed9731e52fa657080a27f1b60f1b8ec931d79c0b22aa991698c7463`.
Only the pristine retail CUE SHA-1
`25adb139e50ba28c2d9c1ecab4528e9cf004b1d5` and BIN SHA-1
`0bc1a29748d4bd608d076495d085e825574880d1` were used as original-game authority.
The guarded provisioner copied and then reverified all 1,262 centrally declared
external inputs from `~/Downloads/ABL`; build identity verified 327/327
staged retail inputs. ALLMODS was not used as a build base or behavioral oracle.

## Observation, inference, and causal confirmation

**Observation.** The retained JSON and replay held identical descriptor pointers and
bytes, but Python compared integer keys from the fresh `per_anchor.descriptors`
mapping with string keys decoded from retained JSON. Separately,
`phase3_evidence_inventory.py` computed no Git tracked-input predicate, so a rewritten
decisive artifact did not reopen either closure layer.

**Inference.** Live evidence must be compared in the same data model that is written
to disk. Closure also needs a predicate over tracked upstream inputs, not only content
joins inside the retained JSON. The two self-regenerating audit outputs must remain
excluded from that predicate so a failed audit can rewrite its verdict and later
recover after the falsified input is restored; both retain their independent semantic
freshness comparisons.

**Causal confirmation.** `write_render_evidence` now JSON-round-trips the completed
render document before calling the shared semantic writer. A focused regression writes
integer descriptor keys, reloads the retained JSON, replays the same integer-keyed
document, and proves the second call returns false with byte-identical output.
`phase3_evidence_inventory.py` now derives `tracked_input_mutations` from `git diff
HEAD`, excludes only `analysis/phase3_evidence_inventory.json` and
`analysis/phase3_gate_audit.json`, and requires the list to be empty for
`closure_ready`. An adversarial test mutates the tracked render artifact and proves
both inventory and gate exit 1, then restores the artifact and proves both recover.

The shared `tools/live_session_provenance.py` bytes did not change, so this repair did
not invalidate unrelated retained live evidence. The render generator itself changed
and was therefore replayed before any machine summary was regenerated.

## Isolated live replay

The worktree replay used the newly created config
`/tmp/abl-phase3-i8-render-20260714-23583`, dedicated loopback port `23583`, and the
normal DuckStation binary SHA-256
`ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
DuckStation source was revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; its complete dirty status is retained in
the evidence. Current source exposed 191 RPC methods and confirmed the exact
`debugger.status`, `debugger.readMemory`, `emulator.getMediaInfo`,
`emulator.getStateInfo`, and `emulator.loadState` schemas before use.

`tools/verify_live_session_environment.py` reproduced `isolated-defaults-v1`:
Recompiler, 1x CPU, 1x CD read/seek, rewind off, runahead 0, Auto region, and 2-MiB
RAM. Post-connect status and media RPCs returned `SCUS-94288`,
`Disney-Pixar A Bug's Life`, and the exact provisioned pristine CUE. Every save was
inspected before load, disc validation remained enabled, and all 42 requested anchors
were accepted as strict pristine.

Direct command:

`python3 tools/phase3_render_descriptors.py --port 23583 --token <redacted> --config-dir /tmp/abl-phase3-i8-render-20260714-23583 --instance-state recreated`

Observed result: 42 accepted anchors, zero refusals, scene-invariant 50-entry pointer
table, and the same scene-dependent offsets `+0x04,+0x06,+0x07,+0x08,+0x0A`.
All retained pointer/descriptor and aggregate observation fields equalled the prior
artifact. The refreshed artifact SHA-256 is
`d08c5917e05b9f76b2cee789877b5ea95c024fd5c4f472697a305130f59b2c3b`.
The generator stopped owned PID `1190542`; the config-scoped launcher reported not
running and `/proc/1190542` was absent.

## Machine layers and validation

Regeneration preserved 19/19 finished findings, 107/107 bounded mechanic frontiers,
63 semantic entries, 134 native-domain rows, all 234 indirect sites, 20 overlays,
eight record views with 181/524-byte accounting, 1,112 functions, 327 assets, and ten
reconciled/bounded contradiction rows. WP1-WP9 and all five exit bullets recomputed
MET. The code-only build changed 1,195 EXE bytes and reproduced SHA-1
`5936596c576415847b3a7395599e993b36eb7906` and SHA-256
`991fc38c131fe1139df30e9719a222a06a140054f1f8ee46b6321bbd9c0e6808`;
five hook contracts were proven outright and ten discharged, with zero owed,
unverified, degraded, refused, or hard-violation rows.

Worktree validation:

- `python3 tools/run_safe_tests.py`: 373 passed, 28 deselected.
- `python3 -m pytest -q -m local_media`: 27 passed, 374 deselected.
- `python3 -m pytest -q tests/test_phase1_*.py tests/test_phase2_*.py`: 61 passed.
- `python3 tools/validate_vault.py`: zero dangling-link, evidence-policy,
  evidence-deadfile, duplicate-address, missing-alias, or schema errors.
- `python3 tools/phase3_evidence_inventory.py`: 28/28 generators and artifacts,
  CLOSURE-READY, `tracked_input_mutations=[]`.
- `python3 tools/phase3_gate_audit.py`: WP1-WP9 and all five bullets MET.

## Fresh-checkout replay of the verifier's failure

Implementation candidate `1626afaa946925a6030117923b8cd4b49ab45c57` was cloned
detached to `/tmp/phase3-i8-pre-doc-proof-1626afa`. The provisioner copied and then
verified 1,262/1,262 inputs; build identity verified 327/327. A newly created isolated
config `/tmp/abl-phase3-i8-pre-doc-render-23584`, port `23584`, mounted the provisioned
pristine CUE on the pinned normal binary. The same render command printed
`semantic replay matched`, reproduced all 42 anchors and the five varying offsets,
and left the retained artifact at SHA-256
`d08c5917e05b9f76b2cee789877b5ea95c024fd5c4f472697a305130f59b2c3b`.

The clean clone then rebuilt the code-only image with both expected hashes,
discharged all 15 hook rows, regenerated inventory and gate as CLOSURE-READY/MET, and
ended with empty `git status --short`. The generator stopped owned PID `1229645`; the
config launcher reported not running and `/proc/1229645` was absent.

Iteration 7's semantic architecture and live observations remain valid, but its
clean-replay durability claim is superseded by this correction. No disc image, save,
movie, capture, BIOS, memory card, token, credential, or generated copyrighted output
is committed.
