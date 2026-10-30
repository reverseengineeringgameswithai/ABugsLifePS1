---
kind: experiment
id: EXP_2026_07_14_phase3_ratchet_iteration6_training_anchor_lifecycle
status: reproduced
created: 2026-07-14
updated: 2026-07-14
confidence: high
related:
  - PLAYBOOK_game_solving_phase_3
  - EXP_2026_07_14_phase3_iteration5_strict_pristine_training_anchor
  - EXP_2026_07_14_phase3_ratchet_iteration4_current_live_freshness
---

# Phase 3 ratchet iteration 6 — deterministic Training anchor and owned lifecycle

## Trigger

The fresh verifier rejected two attractive durability claims under the green Phase-3
gate. `tools/phase3_training_anchor_fixture.py` checked that the pinned Training save
existed and loaded, but did not replay the from-boot movie to regenerate it. Its
retained artifact had no `playback_generation`, so no executable predicate connected
the save pin to the movie. Separately, the external launcher could inspect `$!` before
`setsid` completed its `exec`, delete the PID file, and report startup failure while
the exact isolated DuckStation process remained alive. Cleanup then had no durable
owner to stop.

These are harness and provenance defects. They do not change an original-game fact,
so this evidence belongs in Experiments rather than Canon. No MOD-private state or
intended delta changed.

## Authority and isolation

Every replay mounted only the hash-verified retail media:

- CUE SHA-1 `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5`;
- BIN SHA-1 `0bc1a29748d4bd608d076495d085e825574880d1`;
- serial `SCUS-94288` and title `Disney-Pixar A Bug's Life`;
- DuckStation external-debugger fork revision
  `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, 203 RPC methods, 88 dirty paths;
- normal binary SHA-256
  `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`;
- release binary SHA-256
  `27d064bcbdfefadf91fd9401d158a2756dc6bbf6d52a0bb2d3a3dfad7129cb54`.

Runs used newly created absolute directories under `/tmp`, distinct loopback ports,
ephemeral tokens retained only as hashes, and config-owned PID cleanup. Mounted-media
identity and the pristine CUE/BIN hashes were checked after connecting. ALLMODS was not
used as an authority or build input. Saves, movies, discs, BIOS, cards, captures,
tokens, and generated disc images remain external and uncommitted.

## Observation, inference, causal confirmation

Observation: calling `movie.startPlayback` and `movie.advanceToFrame` while the guest
was running allowed host scheduling to consume frames between the calls. The old
nominal target of 6900 therefore did not describe the retained emulator-frame-6905
save boundary. Pausing before playback made the initial and advance-start indices both
zero. Advancing to playback index 6904 then produced emulator frame 6905, cycle
3909055795, PC `0x8004FEA4`, scene 17, and a 2,152,414-byte candidate with SHA-256
`d41c000504313cccfcf2920dd928ab864b27bf71e699b05a6c0b7d4e030a8795`.

Inference: the retained save was originally created at that deterministic guest/movie
boundary even though the historical recipe named 6900. This inference is bounded to
the exact movie, fork, retail media, and recorded boundary.

Causal confirmation: two independent pause-first reproductions generated the same
size and SHA-256 as the central external fixture. The final generator invocation in
`/tmp/duckstation-phase3-i6c-training-GWoWR5` on port 25782 regenerated a fresh
transient candidate, byte-matched the provisioned fixture, loaded it with disc
validation, observed scene 17, stopped playback, and stopped only PID 1895129. The
artifact explicitly records `candidate_generated_in_this_run=true`, both zero start
indices, the exact frame/cycle/PC, generated hash/size, central-pin equality, and
`owned_pid_stopped=true`.

## Lifecycle repair and falsification

`tools/launch_phase3_debugger.py` wraps the external launcher without broad process
selection. Startup-race recovery requires exactly one process whose executable equals
the requested binary, whose `XDG_CONFIG_HOME` and `XDG_RUNTIME_DIR` equal the fresh
config, and whose open descriptors prove config ownership. It then requires three
stable authenticated API probes before restoring the PID file. A failed API start may
stop only that exact recovered owner; multiple, foreign, or incompletely proved owners
are refused. Stop delegates to the external config/PID guard and waits for the PID to
be reaped; a `Z` or `X` state is correctly classified as dead.

`tests/test_launch_phase3_debugger.py` exercises exact-owner recovery, wrong-XDG
rejection, and zombie completion. Inventory and gate mutation tests remove or falsify
Training playback-generation evidence and require both closure layers to open. The
inventory independently compares the observed playback index, emulator frame, cycle,
PC, movie length, generated hash/size, fixture hash/size, and candidate-generation
flag rather than trusting a hand-authored pass field.

## Complete current live replay

After the final provenance and launcher-helper bytes were stable, all twelve Phase-3
live artifacts were replayed on the pristine media:

- camera output: 0.1506 median gap-closing fraction across 48 moved ticks;
- `jalr`: all 139 sites classified as 99 global-slot, 36 struct-field, or four
  reason-bounded unresolved uses; 30 global slots inspected live;
- record/function-pointer/render aggregates: 42/42 strict-pristine anchors and zero
  refused; eight record views retain 181/524 typed-byte accounting; actor `+0x7C`
  remains a called callback field with 60.8% hit rate across 1,286 instances and nine
  handlers; render variance remains exactly offsets `+04,+06,+07,+08,+0A`;
- state lifetimes: 63 entries, 35 measured live and 28 derived;
- SFX: 27 playable IDs and 27 distinct samples over the `-24..48` scan;
- Thud: id `0x24`, HP 50 at `+0x6E`; HP 1 survives and HP 0 retires it through
  `mover_updater`;
- A07: 193 trials, state values `[0,1,2]`, zero unnamed whole-player-block writer PCs,
  single state-word owner, and a bounded negative rather than disproof;
- transitions: 16/16 routes measured, zero skipped, 450–1170-frame load gap with
  median 540, and exact owned-PID/private-binary cleanup;
- Training: pause-first index 6904 exactly regenerates the central frame-6905 fixture;
- unknown-field motion/TTL observations reproduced without promoting the actor-Y
  residual.

The transition run used an immutable private release-binary sibling and a 207-file
support-tree snapshot. Finalization verified the exact running inode, fork source,
support tree, mounted pristine media, stopped only the owned PID, and removed only the
private sibling.

## Machine-layer result and residuals

The new contradiction row
`training_fixture_pin_vs_actual_cold_boot_regeneration` makes the old existence-only
claim executable. The regenerated 13-row ledger reports six reconciled, seven bounded,
and zero open rows. WP1–WP9 and all five exit bullets still recompute MET from low-level
evidence. No Phase-3 semantic conclusion was weakened.

Carried residuals are unchanged: A07 remains an external lead, F09/D18 remain partial,
the callback ABI and actor vertical ownership remain unknown, and post-load render
variance still does not identify its writer. No operator-only input is needed for this
repair.

## Reproduction commands

The executable command shape is centrally declared in
`tools/phase3_evidence_inventory.py`. For Training, start the normal pinned binary with
`tools/launch_phase3_debugger.py` in a new absolute config, then run:

```text
python3 tools/phase3_training_anchor_fixture.py --output phase3_pristine_training_gameplay_i5.sav --port <unique-port> --token <ephemeral-token> --config-dir </tmp/fresh-config> --instance-state recreated
```

The retained artifact redacts the token and banks exact command, config, port, source,
binary, helper, fixture, media, timing, observation, and cleanup identities. Static,
safe-suite, local-media, and clean-checkout results follow.

## Exact validation results

The source/evidence candidate `6ff42c6fa0e73fbb5596bf3e19e74d3e4e1b52cd`
was clean before validation. Every command below exited 0:

- `git diff --check` produced no output.
- `python3 tools/build_identity.py --verify` verified 327/327 staged pins.
- `python3 tools/knowledge_closure_audit.py --write` reported 932 preservation
  fixtures and zero missing pins, untracked imports, source-pin errors, local-media
  errors, local-manifest errors, unpromoted addresses, or matrix errors.
- `python3 tools/phase3_knowledge_audit.py` recomputed 19/19 findings FINISHED with
  zero gaps.
- `python3 tools/phase3_gate_audit.py` recomputed WP1–WP9, the evidence inventory,
  upstream durability, decisive provenance, and all five exit bullets MET.
- The mandatory generator commands
  `phase3_ownership_graph.py`, `phase3_xrefs.py`, `phase3_dispatch_map.py`,
  `phase3_jr_tables.py`, `phase3_overlay_map.py`, `phase3_record_types.py`, and
  `phase3_hook_contract.py` reproduced 107 mechanics with zero gaps; 15,971 loads,
  10,586 stores, and zero real writer contradictions; 234 indirect sites; 36 decoded
  `jr` tables with 869 entries; 20 overlays; 8 record views with 181/524 bytes typed;
  and 15 hooks as 5 proven + 9 exact discharges + 1 degraded with zero hard,
  unverified, owed, or refused rows.
- The remaining inventoried static/local commands
  `phase3_asset_provenance.py`, `phase3_call_graph.py`,
  `phase3_coverage_matrix.py`, `phase3_contradictions.py`,
  `phase3_duckstation_rpc_manifest.py --check`,
  `phase3_evidence_inventory.py`, `phase3_jalr_callbacks.py --no-live`,
  `phase3_native_domains.py`, and `phase3_scene_asset_graph.py` reproduced 327 assets
  in 12 roles with zero hash gaps; 1,112 functions; WP1–WP9 MET; 13 contradictions
  as 6 reconciled + 7 bounded + 0 open; the current 203-method/88-dirty-path fork;
  29/29 generators and 30/30 artifacts closure-ready; 139 `jalr` sites; 134 native
  domains with zero independent errors; and 15/15 scenes with zero gaps.
- `python3 mod/build.py --mods mod/mods_code_only.yaml --no-disc` reproduced 1,195
  changed EXE bytes, SHA-1 `5936596c576415847b3a7395599e993b36eb7906`,
  and SHA-256
  `991fc38c131fe1139df30e9719a222a06a140054f1f8ee46b6321bbd9c0e6808`.
- `python3 tools/run_safe_tests.py` passed 394 tests with 30 expected deselections.
- `python3 -m pytest -q -m local_media` passed 29 tests with 395 deselections.
- `python3 -m pytest -q tests/test_phase1_*.py tests/test_phase2_*.py` passed 61.
- `python3 tools/validate_vault.py --check` reported zero active dangling-link,
  evidence-policy, evidence-deadfile, duplicate-address, missing-alias, or schema
  errors.

The clean-checkout proof used
`git clone --no-local . /tmp/phase3-i6-clean-a-j5xngv/repo` at the same candidate.
Only this central provision command introduced external bytes:

```text
python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL
```

It copied exactly 1,262 declared inputs. The same command with `--verify-only`
verified 1,262/1,262: 3 pristine-media, 327 pristine-staged, 63 non-pristine, 127
strict-pristine, 63 pristine-serial, 651 derived-retail assembly, 3 derived-retail
disassembly, and 25 derived-retail metadata inputs. The clone repeated every
static/local/build command and hash above, the 394-test safe suite, 29 local-media
tests, 61 Phase-1/2 tests, and the vault check with the same results.

Each of the twelve live commands was then run in its own newly created absolute
config with a dedicated port, a redacted ephemeral token, the declared pinned binary,
and verified retail media. All printed `semantic replay matched` and retained their
committed artifact bytes. The generic launcher race occurred naturally in the camera
and function-pointer lanes; exact-owner recovery succeeded for only the proved config
PID and both runs cleaned up. The Training lane regenerated the transient candidate
and exact-matched the central hash/size. The immutable transition lane used
`/tmp/duckstation-phase3-i6-clean-transition-7WvrFg`, port 25811, and the verified
movie-replay profile; it measured 16/16 stages, zero skips, and the 450–1170-frame
load gap. Its current private sibling and PID file were absent afterward, and a scoped
search found zero Phase-3 clean-replay PID files.

Finally, `python3 tools/phase3_evidence_inventory.py` remained CLOSURE-READY,
`python3 tools/phase3_gate_audit.py` remained MET, `git diff --check` produced no
output, and `git status --short` remained empty after all deterministic and live
regeneration. This note is a results-only documentation update; the resulting exact
commit is re-cloned and rechecked before the ratchet decision.
