---
kind: experiment
id: EXP_2026-07-26_phase4_fmv_menu_owner_control_falsified
date: 2026-07-26
phase: 4
campaign: fmv_playback
row: E15_fmv
status: falsified_control
confidence: high
source_state: original_game
artifact: analysis/phase4_fmv_menu_owner_coverage.json
---

# Phase 4 FMV menu-owner control falsification

Date: 2026-07-26

## Scope and claim

Closure debt selected only `fmv_playback` / `E15_fmv`, with `lifecycle` first
unmet and the live lane binding. The predeclared claim was that both centrally
provisioned from-boot Menu-Navigation recordings execute at least one of the
three known boot FMV callers and none of the six statically reconstructed
non-boot callers over their faithful spans. A non-boot hit would falsify that
claim; no boot-positive hit or a divergent endpoint control would make a
zero-hit result inadmissible.

The experiment falsified its control predicate. It does **not** establish the
natural-route exclusion claim and promotes no roadmap dimension.

## Offline and static narrowing

The ordered Phase-4 machine layers were regenerated before selection:

```text
tools/phase4_trace_capsules.py --write --check
PASS: 55/55 capsules, 3391058326 external bytes

tools/phase4_offline_queue.py --movie-root "$PWD/movies" --write --check
PASS: 107 rows; complete=16 open=91 offline_ready=0 offline_partial=42 live_required=0 no_capsule=65

tools/phase4_derived_index.py --write --check
PASS: 9 external indexes covering 34 rows

tools/phase4_closure_debt.py --write --check
PASS: 107 rows; 16 complete; 148 dimensions met; selected=fmv_playback
```

Two closed `abl-phase4-offline-query/1` receipts bounded the complete from-boot
input spans and centrally pinned movie identities:

- Menu v1 receipt
  `2d069dd315191d2f624bdd27c0a7c75cc58c146083a4c3b8b1ca61fecb9de743`;
- Menu v2 receipt
  `cb9554940b9b1b7a74c7b8ff4b6010c17fd72070a302669b83ffbd4c448f9528`.

The existing `fmv-lifecycle-v2` derived index, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`,
covers neither menu hash. Static reconstruction still reports 47 selectors,
40 manifest cases and exactly nine resident direct callers: three boot
positives and six non-boot candidates.

## Live result

Four fresh isolated profiles used dedicated loopback ports and ephemeral
tokens. Each run verified current debugger capabilities, mounted pristine
SCUS-94288 media, the exact CUE/track hashes, a bounded two-job atomic batch,
complete result-bearing polling, and typed stop plus confirmation for its one
owned PID. No token was retained.

The closed `abl-phase4-live-run-receipt/2` identities are:

- Menu v1 passive:
  `a038c3a09df21197cdf6a28c080dbea464bccda3cf862b886c704e2207038c41`;
- Menu v1 precise:
  `eda61517391fa5cbfd14e196fe80d489e97221d2d791dcf6893f7896b02dff9e`;
- Menu v2 passive:
  `fe5276d3a5ee9cdc5cb11760e1e0df7577bf397996fe95dfe0773bd1629e5234`;
- Menu v2 precise:
  `a2e0e5d937907eedeba6c35242515a84b7c021cf7472b33a3a10888a58f6c93b`.

Both precise traces were complete and untruncated. Each observed
`boot_dlogo`, `boot_title` and `boot_intro` once and observed zero events for
`bonus_clip_sequence`, `game_over_lose`, `finale_lev15c`,
`completed_level_b`, `all_levels_complete_lev15d` and
`level_a_reset_handoff`.

Those zeros are not admissible negative evidence:

- Menu v1's passive repeat matched every captured endpoint domain, but its
  precise arms ended one cycle apart and differed in CPU, selected-memory and
  GPU captures.
- Menu v2's passive repeat already ended one cycle apart with a different CPU
  capture. Its precise arms also ended one cycle apart and differed in CPU,
  selected-memory and GPU captures.
- Every captured movie status reported `reproducible=false`, despite retaining
  a from-boot start declaration. That status is preserved rather than
  interpreted away.

All four receipts pass the strict v2 structural validator when joined to the
executed after-ledger. That local schema check is not an independent verifier
promotion. The controller must still hash-consume every investigator receipt.

## Authoritative banking and falsifier

`config/phase4_fmv_menu_owner_coverage.yaml` pins all four receipts and all four
preserved full batch results.
`tools/phase4_fmv_menu_owner_coverage.py --write --check` re-reads those
external bytes, recomputes hit counts, endpoint equality and CPU/memory/GPU/
SPU/movie hashes, verifies mounted-media/debugger/cleanup identities, and
generates `analysis/phase4_fmv_menu_owner_coverage.json`.

Its explicit falsifier is:

```text
predicate: every passive and precise same-anchor endpoint is equal
outcome: falsified
endpoint-control failures: 3 of 4 receipts
```

Mutation tests reject a hidden non-boot hit, rewritten endpoint equality,
trace truncation and media-identity drift. The tracked artifact keeps
`observed_nonboot_zero_promoted=false` and `dimension_promoted=false`.

## Handoff

Do not repeat the split boot-PC versus non-boot-PC full-span experiment. The
next autonomous E15 experiment must change decomposition: one internally
phase-neutral nine-PC observer per movie, whose debugger-native
uninstrumented/instrumented comparison must match before any route exclusion
is considered. Preserve a wider passive prelude and retain exact PC/register
coverage. If that design becomes admissible and remains zero, proceed to the
already scheduled bounded synthetic-selector lifecycle control without
calling it natural route ownership.

No Canon behavior or MOD-private state was promoted.
