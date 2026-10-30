---
kind: experiment
id: EXP_2026-07-13_phase3_iteration2_closure
name: Phase-3 iteration-2 evidence regeneration and closure reproduction
status: confirmed
created: 2026-07-13
updated: 2026-07-13
confidence: confirmed
source_state: original_game
artifacts:
  - analysis/phase3_evidence_inventory.json
  - analysis/phase3_coverage_matrix.json
  - analysis/phase3_contradictions.json
  - analysis/phase3_gate_audit.json
---

# EXP_2026-07-13_phase3_iteration2_closure

## Authority and isolation

All original-game observations used the pristine SCUS-94288 image pinned by
`tools/build_baselines.json`: CUE SHA-1
`25adb139e50ba28c2d9c1ecab4528e9cf004b1d5`, track SHA-1
`0bc1a29748d4bd608d076495d085e825574880d1`. Each retained live artifact records
the exact mounted path before and after hashing, the referenced save/movie hash,
a newly created absolute `/tmp` config, a dedicated port and token hash, the owned
PID, and successful owned-PID cleanup.

DuckStation revision was `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` with
the full dirty-source status retained in each artifact. The executed binary SHA-256
was `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.

| Artifact | Port | Isolated config | Result |
|---|---:|---|---|
| `phase3_semantic_lifetime.json` | 23631 | `/tmp/duckstation-phase3-i2-lifetime-8jY4Db` | 63 entries: 35 measured, 28 derived; cleanup verified |
| `phase3_camera_record.json` | 23632 | `/tmp/duckstation-phase3-i2-camera-rPShe9` | both camera triples shown to be derived outputs |
| `phase3_jalr_callbacks.json` | 23633 | `/tmp/duckstation-phase3-i2-jalr-ijVoxO` | 139 sites classified; 30 global slots sampled |
| `phase3_record_probe.json` | 23634 | `/tmp/duckstation-phase3-i2-records-vjA0Pr` | 42 anchors; occupancy predicates measured |
| `phase3_fn_ptr_fields.json` | 23635 | `/tmp/duckstation-phase3-i2-fnptr-khHUzd` | 42 anchors; actor `+0x7C` handlers bound |
| `phase3_render_descriptors.json` | 23636 | `/tmp/duckstation-phase3-i2-render-GhoFdF` | Historical iteration-2 interpretation; iteration 3 supersedes loader causality with exact post-load byte variance and an unresolved writer. |
| `phase3_sfx_interface.json` | 23637 | `/tmp/duckstation-phase3-i2-sfx-oldZ5G` | IDs -24..48; 27 distinct samples keyed |
| `phase3_unknown_fields.json` | 23638 | `/tmp/duckstation-phase3-i2-unknown-wHpNZB` | velocity/TTL findings reproduced |
| `phase3_spin_functional.json` | 23639 | `/tmp/duckstation-phase3-i2-spin-rerun-spprWy` | 193 complete trials; bounded negative only |
| `phase3_thud.json` | 23640 | `/tmp/duckstation-phase3-i2-thud-rerun-R9aJEJ` | id 0x24 and HP=0 retirement edge bound |
| `phase3_transition_reset.json` | 23645 | `/tmp/dsrepro-phase3-i2-transition-all-20260713a` | Training + 15 stages, 16/16 complete |

The transition run additionally pins the operator-owned 128-KiB memory-card seed in
`config/phase3_runtime_fixtures.yaml`, verifies the isolated copy, and uses the
timing-matched `tools/launch_repro_playback.sh` configuration. A generic launcher
did not replay these from-boot movies deterministically; that failed route was not
used as evidence.

## Observation, inference, confirmation

- Observation: the spin battery completed 193 real watch batches, exposed 102 writer
  PCs, saw state values only in the documented set, and found no unnamed writer.
  Inference: no distinct spin state/writer was found within that trigger space.
  Boundary: this does **not** disprove the external lead; the exact external input,
  context, and expected effect are still required.
- Observation: the Thud record carried id `0x24`, HP 50 at `+0x6E`, survived the
  HP=1 control, and retired at HP=0 through the observed mover updater. Causal
  confirmation is limited to identity and retirement, not the full encounter FSM.
- Observation: all 16 transition movies contained both target entry and exit, with
  an entry flip bracket no wider than 30 frames and a world-ready gap of 450..1170
  frames (median 540). The next load owns world-record overwrite; exit did not
  reclaim actor/plant/contact bytes.

## Static/local reconciliation

`analysis/phase3_coverage_matrix.json` recomputes WP1-WP9 from the low-level
artifacts. `analysis/phase3_contradictions.json` compares nine source classes in
eight rows; four are reconciled and four retain explicit bounded residuals.
`analysis/phase3_evidence_inventory.json` owns 27/27 generators and artifacts and
rejects missing provenance, unsafe default tokens, missing config arguments, stale
outputs, and silent generator/artifact omissions.

The independently built code-only diagnostic EXE has SHA-1
`5936596c576415847b3a7395599e993b36eb7906` and SHA-256
`991fc38c131fe1139df30e9719a222a06a140054f1f8ee46b6321bbd9c0e6808`.
The hook contract discharges all 15 declared hooks (5 direct, 10 against built
caves), with zero hard violations, refusals, stale-image matches, or unverified
caves.

## Reproduction commands

Static/local closure:

```bash
python3 tools/build_identity.py --verify
python3 tools/mechanics_baseline.py
python3 tools/knowledge_closure_audit.py --write
python3 tools/phase3_ownership_graph.py
python3 tools/phase3_xrefs.py
python3 tools/phase3_native_domains.py
python3 tools/phase3_dispatch_map.py
python3 tools/phase3_jr_tables.py
python3 tools/phase3_scene_asset_graph.py
python3 tools/phase3_overlay_map.py
python3 tools/phase3_record_types.py
python3 tools/phase3_call_graph.py
python3 tools/phase3_asset_provenance.py
python3 tools/phase3_contradictions.py
python3 tools/phase3_knowledge_audit.py
python3 tools/phase3_coverage_matrix.py
python3 tools/phase3_evidence_inventory.py
python3 tools/phase3_gate_audit.py
python3 mod/build.py --mods mod/mods_code_only.yaml --no-disc
python3 tools/phase3_hook_contract.py
python3 tools/run_safe_tests.py
```

The exact live commands, generator hashes, config paths, ports, token hashes,
anchors, timing/watch accounting, and cleanup results are in each artifact's
`run_provenance`; raw credentials are intentionally not retained.

## Clean-checkout validation

A newly created checkout of the candidate tree was provisioned only from the
centrally declared, hash-verified operator root `~/Downloads/ABL`.
Provisioning verified source and destination size/SHA-256 for 327 staged build
inputs (725,849,170 bytes) and 252 runtime fixtures (734,079,116 bytes); the
root pristine CUE/track pair was copied only after its pinned SHA-1 identity was
verified. None of these ignored external files is part of the commit.

The clean checkout reproduced these low-level results:

- `python3 tools/build_identity.py --verify`: PASS, 327/327 staged inputs.
- The complete static generator sequence above: 107 mechanics rows; 63 semantic
  entries; 36 native domains; 31 selectors; 234 indirect sites; 20 overlays;
  8 typed record views; 1,112 functions; 327 assets; 8 contradiction rows; and
  27/27 evidence generators/artifacts.
- `python3 mod/build.py --mods mod/mods_code_only.yaml --no-disc`: SHA-1
  `5936596c576415847b3a7395599e993b36eb7906`, SHA-256
  `991fc38c131fe1139df30e9719a222a06a140054f1f8ee46b6321bbd9c0e6808`.
- `python3 tools/phase3_hook_contract.py`: 15/15 hooks accounted, 5 direct and
  10 discharged; zero hard violations, refusals, or unverified caves.
- `python3 tools/run_safe_tests.py`: 335 passed, 27 deselected, zero skipped.
- The targeted Phase 1/2/3 local-media and freshness command below returned
  56 passed:

  ```bash
  python3 -m pytest -q tests/test_phase3_dispatch.py tests/test_phase3_records.py tests/test_phase3_scene_graph.py tests/test_phase3_overlay_map.py tests/test_knowledge_closure.py tests/test_mechanics_baseline.py tests/test_phase1_census.py tests/test_phase2_oracle.py tests/test_disc_provenance.py
  ```
- `python3 tools/phase3_gate_audit.py`: 5/5 predicates MET.
- `git diff --check` and `git status --short`: exit 0 with no output after
  deterministic regeneration.
