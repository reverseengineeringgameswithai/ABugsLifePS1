---
kind: experiment
id: EXP_2026-07-13_phase3_iteration3_closure
name: Phase-3 iteration-3 verifier repair and direct closure reproduction
status: confirmed
created: 2026-07-13
updated: 2026-07-13
confidence: confirmed
source_state: original_game
superseded_by: EXP_2026-07-14_phase3_iteration4_durability_closure
artifacts:
  - analysis/phase0_2_knowledge_closure_report.json
  - analysis/phase3_native_domains.json
  - analysis/phase3_render_descriptors.json
  - analysis/phase3_evidence_inventory.json
  - analysis/phase3_coverage_matrix.json
  - analysis/phase3_contradictions.json
  - analysis/phase3_gate_audit.json
---

# EXP_2026-07-13_phase3_iteration3_closure

> [!warning] Durability correction
> The iteration-3 live observations remain evidence, but its clean-checkout closure
> claim was invalidated by a fresh verifier. The corrected source/fixture closure and
> complete local-media reproduction are in
> [[EXP_2026-07-14_phase3_iteration4_durability_closure]].

## Scope and authority

Iteration 3 independently reproduced the Phase 3 acceptance contract and repaired
the low-level defects found by the verifier. Original-game observations used only
the hash-verified pristine SCUS-94288 retail image. ALLMODS was not a build or
observation base. Every live run used a new absolute `/tmp` config, a dedicated
loopback port/token, mounted-media verification, and exact launcher-owned PID
cleanup.

DuckStation revision was
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; the executed release binary was
`~/duckstation/build-release/bin/duckstation-qt`, SHA-256
`bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.
The fork's complete dirty-source status is retained in each live artifact rather
than summarized away.

## Repairs forced by low-level evidence

- The four tracked-to-untracked Python imports were closed by centrally declaring
  their operator-root source path, size, SHA-256, and noncopyrighted media class,
  then committing exact bytes plus the training-board guard. The current audit has
  zero import gaps and zero provisioned-source pin errors.
- Thud retirement stores `0x8004D270` and `0x8004D43C` are typed interior code
  sites in `config/confirmed_sites.yaml`; they are not callable ABIs.
- Every save-backed Phase 3 live generator now calls
  `emulator.getStateInfo` before `loadState`, rejects invalid/foreign serials,
  and banks the inspection result.
- Live evidence writes compare semantic content, so fresh ports, tokens, PIDs,
  timestamps, and config/worktree paths do not dirty a checkout. A fresh camera
  replay retained SHA-256
  `5134309f5abd905f0d9efbf5fcb31d98c3b3495626a953b0f74e77e564842605`
  byte-for-byte.
- WP3 no longer lets `semantic_state.yaml` certify its own universe. The generated
  134-row join contains 36 independently scoped campaign-state scalars, 62 typed
  record fields, and all 36 decoded bounded dispatch selectors. Bidirectional scope
  omissions and stale retained output fail the guard.
- The render census now reports only what its snapshots prove: pointers are stable;
  target bytes `+00,+02,+03,+04,+06,+07,+08,+09,+0A` are scene-dependent; only
  `+01,+05,+0B` are invariant. Writer attribution remains a structured bounded
  residual. No loader-writer claim is inferred from save-state snapshots.
- A07 and Thud original-game facts now have Canon pages; the knowledge audit rejects
  an Experiments path used as a finding's Canon authority.

## Live reproduction

All retained artifacts record the exact command, generator/helper hashes, pristine
media identity, fixture hashes, timing, config, token hash, binary/fork identity,
and cleanup.

| Artifact | Port | Isolated config | Direct result |
|---|---:|---|---|
| `phase3_semantic_lifetime.json` | 24643 | `/tmp/duckstation-phase3-i3-lifetime-PMgTR9` | 63 entries: 35 measured, 28 derived |
| `phase3_camera_record.json` | 24645 | `/tmp/duckstation-phase3-i3-release-camera-9ClFrw` | both camera triples remain derived outputs |
| `phase3_jalr_callbacks.json` | 24646 | `/tmp/duckstation-phase3-i3-release-jalr-E7lYvp` | 139 sites, 30 global slots |
| `phase3_record_probe.json` | 24647 | `/tmp/duckstation-phase3-i3-release-records-fdorTg` | 42/42 pre-inspected anchors |
| `phase3_fn_ptr_fields.json` | 24648 | `/tmp/duckstation-phase3-i3-release-fnptr-YqGWG3` | 42 anchors; actor `+0x7C` callback field |
| `phase3_render_descriptors.json` | 24649 | `/tmp/duckstation-phase3-i3-release-render-hO9sRL` | exact nine varying/three invariant offsets |
| `phase3_sfx_interface.json` | 24639 | `/tmp/duckstation-phase3-i3-sfx-release-0Jr8q4` | 27 playing IDs, 27 distinct samples |
| `phase3_unknown_fields.json` | 24640 | `/tmp/duckstation-phase3-i3-unknown-sA95pF` | player/actor/contact motion and TTL laws |
| `phase3_spin_functional.json` | 24641 | `/tmp/duckstation-phase3-i3-spin-8GRcIA` | 193 complete trials; bounded negative, not disproof |
| `phase3_thud.json` | 24642 | `/tmp/duckstation-phase3-i3-thud-KaC1U5` | id 0x24; HP=1 survives; HP=0 retires |
| `phase3_transition_reset.json` | 24644 | `/tmp/dsrepro-phase3-i3-transition-all-WIoQqQ` | 16/16 timing-matched transitions |

Spin returned all 139,084 logged writes across 193 batches with zero truncation,
total drift, cap saturation, or incomplete page. It observed only state values
`0,1,2`, 102 owning-block writer PCs, and no unnamed writer. This is a bounded
negative over the tested trigger space; the external lead is not disproven.

Thud's HP=1 control survived and HP=0 retired the id-`0x24` record through
`mover_updater`. The complete 30-event write log attributes the active-bit and
live-table retirement stores. This confirms identity/retirement, not the whole
encounter state machine.

The timing-matched transition run verified the pinned 128-KiB card seed and isolated
copy, then measured Training plus all 15 campaign stages. Load gaps were 450–1170
frames (median 540). `enemy_permanence_quota`, `grain_count`, `health_true`,
`lives`, and `seed_counter_orange` were session-owned in every stage. Exit itself
did not reclaim world bytes; the next load owned their overwrite.

## Failed routes retained

The first camera replay used the older `build/bin` executable and reached cleanup,
but the helper omitted the non-default binary path when invoking the launcher stop.
The launcher correctly refused. PID 382627 was stopped only after its executable and
open descriptor under the exact isolated config were verified. The helper now passes
the observed binary path and its owned-PID guard test passes.

The older binary also lacked the documented `spu.status` RPC, so the first SFX run
failed with JSON-RPC `-32601` and its wrapper stopped only the owned PID. The
release binary implements the documented SPU method; the retained SFX reproduction
uses that binary. Neither failed route was accepted as evidence.

## Machine-layer closure

Fresh regeneration reports:

- 107 mechanics; 106 address-bound; 88/88 named functions and 166/166 state
  references owned;
- 63 semantic entries with xref/lifetime coverage;
- 134 independently joined domain rows and zero universe errors;
- 234 indirect sites: 95 `jr`, 139 `jalr`; 20 overlays;
- 8 record views and 181/524 explicitly typed bytes;
- 1,112 functions, 327 hash-verified staged assets, and 9 contradiction rows
  (4 reconciled, 5 explicitly bounded, 0 open);
- 27/27 generators and artifacts with zero provenance or pre-load-inspection gaps;
- 15 hook contracts: 5 proven outright, 10 discharged against the pinned built
  image, zero hard violations, refusals, owed modules, or unverified caves.

`analysis/phase3_gate_audit.json` recomputes WP1-WP9, upstream durability,
decisive evidence, and all five exit bullets. Every predicate is met without
consuming a retained high-level verdict.

## Reproduction order

```bash
python3 tools/build_identity.py --verify
python3 tools/mechanics_baseline.py
python3 tools/knowledge_closure_audit.py --write
python3 tools/phase3_ownership_graph.py
python3 tools/phase3_xrefs.py
python3 tools/phase3_dispatch_map.py
python3 tools/phase3_jr_tables.py
python3 tools/phase3_native_domains.py
python3 tools/phase3_scene_asset_graph.py
python3 tools/phase3_overlay_map.py
python3 tools/phase3_record_types.py
python3 tools/phase3_call_graph.py
python3 tools/phase3_asset_provenance.py
python3 mod/build.py --mods mod/mods_code_only.yaml --no-disc
python3 tools/phase3_hook_contract.py
python3 tools/phase3_contradictions.py
python3 tools/phase3_knowledge_audit.py
python3 tools/phase3_coverage_matrix.py
python3 tools/phase3_evidence_inventory.py
python3 tools/phase3_gate_audit.py
```

The exact live commands are retained in the eleven live artifacts; raw tokens are
redacted and only token hashes remain.

## Working-tree validation

- `python3 tools/build_identity.py --verify`: 327/327 staged inputs PASS.
- `python3 mod/build.py --mods mod/mods_code_only.yaml --no-disc`: patched EXE
  SHA-1 `5936596c576415847b3a7395599e993b36eb7906`, SHA-256
  `991fc38c131fe1139df30e9719a222a06a140054f1f8ee46b6321bbd9c0e6808`.
- `python3 tools/phase3_hook_contract.py`: 15/15 accounted, zero hard
  violations/refusals/unverified/owed.
- `python3 tools/run_safe_tests.py`: 349 passed, 27 deselected.
- Targeted freshness, upstream, semantic-state, contradiction, coverage, inventory,
  and gate tests: 42 passed.
- `python3 tools/phase3_gate_audit.py`: exit 0; all five bullets MET, WP1-WP9
  MET, evidence inventory fresh/closure-ready, decisive evidence MET, and concrete
  upstream durability blocker lists empty.

## Clean-checkout reproduction

A newly created detached checkout of candidate
`b91ded6b6c759846075eeee3d674199d3c179ca7` was provisioned only from the
centrally declared operator root `~/Downloads/ABL`. Source and destination
size/hash checks covered 327 staged inputs (725,849,170 bytes), 252 runtime fixtures
(734,079,116 bytes), and the pristine CUE, track, and root executable. These ignored
copyrighted/operator bytes were not committed.

The clean checkout directly reproduced:

- the complete static generation order above: 107 mechanics, 63 semantic entries,
  134 independent domain rows, 234 indirect sites, 20 overlays, 8 record views,
  1,112 functions, 327 staged assets, 9 contradiction rows, 19/19 finished findings,
  and 27/27 generator/artifact inventory closure;
- the code-only diagnostic build with the same SHA-1/SHA-256 and all 15 hook
  contracts accounted with zero hard violations;
- `python3 tools/phase3_gate_audit.py`: exit 0, all WP1-WP9 and five exit bullets
  MET, concrete upstream blockers empty;
- `python3 tools/run_safe_tests.py`: 349 passed, 27 deselected, zero skipped after
  the separately declared root executable was provisioned;
- the targeted local-media Phase 1/2/3 freshness slice: 6 passed, 67 deselected;
- `git diff --check` and `git status --short`: exit 0 with no output after all
  deterministic regeneration, build, gate, and test commands.
