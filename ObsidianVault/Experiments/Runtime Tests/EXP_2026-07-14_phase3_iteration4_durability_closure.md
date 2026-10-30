---
kind: experiment
id: EXP_2026-07-14_phase3_iteration4_durability_closure
name: Phase-3 iteration-4 clean-checkout durability closure
status: confirmed
created: 2026-07-14
updated: 2026-07-14
confidence: confirmed
source_state: original_game
artifacts:
  - analysis/phase0_2_external_fixture_set.json
  - analysis/phase0_2_knowledge_closure_report.json
  - analysis/phase3_evidence_inventory.json
  - analysis/phase3_jalr_callbacks.json
  - analysis/phase3_coverage_matrix.json
  - analysis/phase3_gate_audit.json
---

# EXP_2026-07-14_phase3_iteration4_durability_closure

## Why iteration 3 was not sufficient

The iteration-3 architecture result remained sound, but its clean-checkout claim was
not. A fresh verifier exposed local-only dependencies that the retained high-level
audits did not reject:

- `extracted/re_baseline/functions.json` and `strings.json` were absent;
- 651 assembly sources consumed by `config/segments.yml` were absent and treated as
  optional;
- overlay builds consumed unpinned `OVL/` extraction copies rather than the pristine
  staged tree;
- deterministic decomp, memory-map, and Phase-2 A07 artifacts had drifted;
- `phase3_jalr_callbacks.py --no-live` erased the live handler map while the gate and
  knowledge audit could continue to report green.

The iteration-3 clean-checkout counts and candidate named in
[[EXP_2026-07-13_phase3_iteration3_closure]] are therefore superseded by this direct
reproduction. The earlier live architecture observations remain evidence; only its
durability/closure claim is superseded.

## Source and fixture closure

`analysis/phase0_2_knowledge_closure.yaml` now declares the two derived r2 metadata
files and three Canon-referenced disassembly listings by source, size, SHA-256, media
class, generator, and consumer. `tools/repro_inputs.sha256` pins all 651 derived
assembly inputs named by `config/segments.yml`. All remain ignored and outside Git.
The remaining 23 census/memory-map inputs (resident signature CSVs, code/data map,
and all 20 overlay function listings) are pinned in
`tools/re_baseline_inputs.sha256`. The function census consumes overlay bytes only
from the pristine staging tree and records every blob/listing hash in its output.

`tools/provision_clean_checkout_inputs.py` constructs one fail-closed plan from
`tools/build_baselines.json`, the knowledge matrix, and
`analysis/phase0_2_external_fixture_set.json`. It verifies the operator source before
copying, verifies the destination afterward, and refuses to overwrite a mismatched
destination. The exact plan is:

| Class | Files |
|---|---:|
| Pristine media | 3 |
| Pristine staged inputs | 327 |
| Runtime saves/movies | 252 |
| Derived assembly | 651 |
| Derived r2/analysis metadata | 25 |
| Canon-referenced derived disassembly | 3 |
| **Total** | **1,261** |

The generated external preservation set contains 931 entries (the 252 runtime
fixtures plus 679 retail-derived inputs). Its audit reports zero missing pins,
untracked imports, source-pin errors, local-media errors, manifest errors, unpromoted
addresses, or matrix errors. Missing inputs are failures, never skips.

Overlay manifests now open only `REBUILD/files/LEVEL*/LEVEL*.BIN` and
`REBUILD/files/BITS/MEMORY.BIN`, whose 327-file pristine identity is independently
pinned. `OVL/` and root `MEMORY.BIN` copies are not authorities or build dependencies.

## Fresh live evidence

Only the live artifact whose generator changed was rerun. The run used DuckStation
revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, release binary SHA-256
`bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`, isolated
config `/tmp/duckstation-phase3-i4-jalr-iOE3l8`, port `24760`, and a fresh token whose
hash—not value—is retained in `analysis/phase3_jalr_callbacks.json`.

After connection, the tool verified the mounted CUE and referenced track against
`tools/build_baselines.json`, inspected `level01.sav` before loading it with disc
validation enabled, settled ten frames, and read all 30 callback slots. Result:
139 `jalr` sites (99 global-slot uses, 36 struct-field calls, 4 reason-bounded
unresolved), with 30/30 global handlers retained. It stopped only launcher-owned PID
`532142`; launcher status then reported no live pidfile. Static `--no-live` replay now
requires the same slot universe, pristine executable pin, complete handler map, and run
provenance, and preserves the artifact byte-for-byte.

The other ten live artifacts were reproduced in iteration 3 and their complete
generator/helper/media/fixture/config/binary/fork/cleanup provenance remains banked.
Iteration 4 did not change those generators or claims; inventory and guard tests prove
their schemas, pins, state inspections, and live provenance remain complete.

## Machine-layer reproduction

The exact static/local order was:

```bash
python3 tools/build_identity.py --verify
python3 tools/phase3_ownership_graph.py
python3 tools/phase3_xrefs.py
python3 tools/phase3_dispatch_map.py
python3 tools/phase3_jr_tables.py
python3 tools/phase3_jalr_callbacks.py --no-live
python3 tools/phase3_overlay_map.py
python3 tools/phase3_record_types.py
python3 tools/phase3_scene_asset_graph.py
python3 tools/phase3_asset_provenance.py
python3 tools/phase3_call_graph.py
python3 tools/phase3_native_domains.py
python3 mod/build.py --mods mod/mods_code_only.yaml --no-disc
python3 tools/phase3_hook_contract.py
python3 tools/phase3_contradictions.py
python3 tools/phase3_coverage_matrix.py
python3 tools/knowledge_closure_audit.py --write
python3 tools/phase3_evidence_inventory.py
python3 tools/phase3_knowledge_audit.py
python3 tools/phase3_gate_audit.py
```

Direct results: 327/327 staged inputs; 107 mechanics with zero ownership gaps;
63 semantic entries; 134 native-domain rows; 234 indirect sites; 20 overlays;
8 record views with 181/524 typed bytes and explicit accounting for the remainder;
1,112 functions; 327 asset-provenance rows; WP1-WP9 MET; 19/19 findings finished;
27/27 generators and artifacts inventoried; and all five exit bullets MET. The
diagnostic build reproduced patched executable SHA-256
`991fc38c131fe1139df30e9719a222a06a140054f1f8ee46b6321bbd9c0e6808`; the hook
audit found 5 contracts proven outright and 10 discharged against that image, with
zero degraded, unverified, hard-violation, owed, or refused rows.

Validation results:

- `python3 tools/run_safe_tests.py`: 356 passed, 28 deselected, exit 0.
- `python3 -m pytest -q -m local_media`: 27 passed, 357 deselected, exit 0.
- affected Phase-1/2 freshness and bounded-A07 slice: 39 passed, exit 0.
- `python3 tools/validate_vault.py --check`: zero dangling, evidence-policy,
  evidence-deadfile, duplicate-address, missing-alias, or schema regressions.
- `git diff --check`: exit 0.

## Clean-checkout acceptance

A new checkout of the final candidate was provisioned by the 1,261-row plan above
from `~/Downloads/ABL`; no undeclared local copy was used. It reproduced
the static/local generators, the pinned code-only image and hook contracts, the
356-test safe suite, the complete 27-test local-media suite, knowledge audit, WP1-WP9,
and the five-bullet gate without skips caused by missing fixtures. Retained JALR live
evidence replayed byte-for-byte. Deterministic regeneration left no tracked diff;
`git status --short` was empty after excluding only ignored external media and build
outputs.

This closes the Phase-3 durability defect. It does not promote A07 beyond an
`external_lead`, solve F09/D18, characterize every callback ABI, or begin Phase 4.
