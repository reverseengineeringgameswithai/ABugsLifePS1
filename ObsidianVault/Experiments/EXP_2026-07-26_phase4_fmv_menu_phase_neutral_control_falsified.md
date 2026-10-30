---
kind: experiment
id: EXP_2026-07-26_phase4_fmv_menu_phase_neutral_control_falsified
date: 2026-07-26
phase: 4
campaign: fmv_playback
row: E15_fmv
status: falsified_control
confidence: high
source_state: original_game
artifact: analysis/phase4_fmv_menu_phase_neutral_live.json
---

# Phase 4 FMV native menu-owner control falsification

## Scope and claim

Closure debt selected only `fmv_playback` / `E15_fmv`, with `lifecycle` first
unmet and the live lane binding. The exact claim was that one native
`movie.traceToFrame` observer per centrally provisioned Menu recording would
be internally phase neutral, hit all three boot controls and hit none of the
six reconstructed non-boot caller PCs. Any endpoint inequality, missed boot
control, non-boot hit, truncation or receipt join failure was the explicit
falsifier.

The falsifier fired in both movies. No natural owner, route exclusion,
selector identity or roadmap dimension is promoted.

## Offline and static narrowing

The ordered machine layers were regenerated before selection. The central
capsule set passes at 55/55 capsules and 3,391,058,326 external bytes. The
107-row queue reports 16 complete, 91 open, zero `offline_ready`, 42
`offline_partial`, zero `live_required` and 65 `no_capsule`. The closure-debt
ledger retains 148 met dimensions and selects only E15.

The retained `fmv-lifecycle-v2` derived index, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`,
contains no record for either Menu hash. Current iteration offline receipt
`5820a478e6c3605cc1b563815a33d88b84593f7e1abab743282b840ad97324c6`
re-executes the tracked reader and retains that exact zero-count answer.
Prior central receipts establish complete from-boot spans of 7,793 and 7,362
input samples. Static reconstruction passes with 47 selectors, 40 manifest
cases and exactly nine resident direct caller sites.

## Live result

Four fresh isolated debugger profiles used ports 24931 through 24934 and
ephemeral tokens. Each run verified current capabilities, pristine
SCUS-94288 mounted media, one bounded two-job atomic batch, complete
command/result joins and typed stop plus confirmation for its owned PID.
The closed v2 receipt SHA-256 identities are:

- Menu v1 passive prelude:
  `dfc6a0f8412c31ad09ec6d0136b79ca0475718361af1a3879f96e354c3fcd28e`;
- Menu v1 precise native observer:
  `d7cace350e5766e294044db059e296cf3d1f6cbd8ca0b79e9928e785ff0be5d7`;
- Menu v2 passive prelude:
  `549bfac34554c22f2a6a7145fb71eee399df14f3937b0fc0e363c5ac5eddd06c`;
- Menu v2 precise native observer:
  `bbd22c78c8ae279cfe0d5d9566eeb9c79e3802eca18527af2069c803c7d6431f`.

Both native observers completed without truncation. Each reports 327 hits for
all three boot PCs and 326 hits for bare PCs `0x800500D8` and `0x80050284`;
the other four non-boot PCs remain zero. These are cached-interpreter passive
block-coverage counts. They do not carry selector registers or establish that
the resident game-over/finale owner code occupied the address, so they are
retained as address-reuse observations only.

Both direct native comparisons keep cycle, frame and registers equal but
change RAM:

- v1 control `876f21bd…cc59`, observed `589d98ef…30f1`;
- v2 control `cf3f2e69…00e4e`, observed `6ebe75c0…13a30`.

Therefore `cycle_neutral=false` for both. The independent v1 atomic repeat is
equal in every captured domain; v2's atomic repeat is one cycle apart with a
different CPU capture. Every movie status remains `reproducible=false`.

## Authoritative banking and falsifier

`config/phase4_fmv_menu_phase_neutral_result.yaml` pins all four plans,
receipts and preserved batch results.
`tools/phase4_fmv_menu_phase_neutral_result.py --write --check` re-reads the
external evidence, revalidates plan/media/debugger/prelude/cleanup identities,
recomputes atomic equality and invokes the native result validator to
rederive all nine counts and endpoint comparisons. It generates
`analysis/phase4_fmv_menu_phase_neutral_live.json`.

The retained falsifier is:

```text
predicate: each native observer is endpoint-neutral, hits all three boot
           controls and hits no non-boot candidate
outcome: falsified
reasons: native_endpoint_divergence, nonboot_owner_hit
failing precise receipts: 2 of 2
```

Mutation tests reject changed RAM equality, truncated coverage, altered direct
params, rewritten atomic equality and pristine-media drift. The claim boundary
keeps `dimension_promoted=false`, `natural_owner_calls_promoted=false` and
`address_reuse_hits_promoted=false`.

## Handoff

Do not replay the complete Menu fixtures for another bare-PC exclusion label.
The next lane is static: reconstruct a residency-qualified code-identity
boundary for shared addresses `0x800500D8` and `0x80050284`, then specify one
bounded synthetic selector lifecycle control at the confirmed resident loader
interface. Any later live experiment must capture selector, mode, caller and
resident-code identity and must not claim natural Menu ownership.

No Canon behavior or MOD-private state was promoted.
