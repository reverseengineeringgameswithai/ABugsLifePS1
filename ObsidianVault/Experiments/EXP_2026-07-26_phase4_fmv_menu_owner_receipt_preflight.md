# Phase 4 FMV menu-owner receipt preflight

Date: 2026-07-26

## Scope

The selected campaign remained `fmv_playback`, with only `E15_fmv` active and
`lifecycle` the first unmet policy-ordered dimension. The exact claim remains:
both centrally declared from-boot Menu-Navigation recordings execute at least
one of the three resident boot FMV callers and none of the six reconstructed
nonboot callers over their complete input spans. Any nonboot caller hit, no
boot-positive hit, truncation, or unmatched terminal control falsifies that
claim.

No DuckStation process was launched in this iteration. Preflight found that the
planned collector could not produce an admissible live receipt: exact PC
coverage uses `execTrace.run`, which the binding v2 method classifies as
precise, but the planned escalation called it passive and did not name the
strictly wider passive prelude required in the same iteration. The method
metrics layer also rejected a second receipt using the same escalation ID,
which made one predeclared multi-fixture escalation unable to retain its
mandatory prelude/precise pairs.

## Retained offline evidence

Before reconsidering live work, the tracked offline reader queried the current
16,060,589-byte `fmv-lifecycle-v2` index, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`.
Both central menu-movie hashes have exact occurrence count zero:

- `Menu-Navigation.movie.json`:
  `e908f2cfeac94bc66cf30f9afc22cb73331007d03fed74618a15be9c78c6400c`;
- `Menu-Navigation.movie_v2.json`:
  `8a49d28b441170d84993259cd6ca12eac6be6f56d9caa1ae7475f5b3c17cd271`.

The closed `abl-phase4-offline-query/1` receipt is external at
`iteration-1-receipts/offline-fmv-index-menu-coverage.receipt.json`, SHA-256
`5820a478e6c3605cc1b563815a33d88b84593f7e1abab743282b840ad97324c6`.
Its output SHA-256 is
`7d280901605fc468072fae5cc9c1125060307a9c6a0ee55231aaf153231703c5`;
the preservation manifest SHA-256 is
`42a0d2923c4d56e7416eb9d1ed6ca640c9206af38db2646b5d5cd5c180ead5c5`.
Independent receipt replay returned the same bytes and `PASS: offline query`.

## Machine repair

`config/phase4_live_escalations.yaml` now carries an
`abl-phase4-live-receipt-plan/1` plan for four receipts: one uninstrumented
passive prelude and one precise owner-coverage receipt for each menu movie.
Each precise capture is one emulator frame narrower than its same-anchor
prelude, uses `scenario.runBatch`, and retains the central pristine-class movie
hash. `tools/phase4_live_escalations.py` rejects observer/precision mismatch,
missing or non-passive preludes, non-wider windows, noncentral movie pins and
non-atomic plans.

`tools/phase4_method_metrics.py` now admits several distinct semantic receipts
under one predeclared escalation within one iteration. It still rejects a
duplicate semantic experiment and any reuse of that escalation in a later
iteration. This makes the multi-anchor plan compatible with the mandatory
prelude rule without allowing retrospective or semantic reruns.

Focused validation:

```text
python3 tools/phase4_live_escalations.py --check
PASS: 17 live escalation entries

python3 -m pytest -q tests/test_phase4_offline_queue.py tests/test_phase4_method_metrics.py
50 passed
```

## Result and handoff

This iteration establishes no new original-game behavior and promotes no
roadmap dimension. It closes a method-admissibility defect before launch and
leaves one exact autonomous next action: execute the four typed receipts from
fresh isolated profiles, retain the required identity/batch/cleanup evidence,
and stop at localization if any nonboot PC hits. The synthetic-selector
fallback remains later than these two central fixture leads.
