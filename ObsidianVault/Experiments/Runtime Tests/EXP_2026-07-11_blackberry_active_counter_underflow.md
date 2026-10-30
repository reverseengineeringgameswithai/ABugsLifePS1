---
kind: experiment
id: EXP_2026_07_11_blackberry_active_counter_underflow
name: Blackberry pickup active-counter underflow and Square lockout
status: confirmed_fixed
date: 2026-07-11
confidence: confirmed
source_state: experiment
systems:
  - SYS_berry_projectile_and_homing
mods:
  - MOD_blackberry_net_new_berry
artifacts:
  - build/ABL_ALLMODS_smoke.json
  - tools/scenarios/duckstation/blackberry_pickup_preserves_active_counter.yaml
  - /tmp/abl-ps1-report-blackberry-active-counter/blackberry_pickup_preserves_active_counter.json
---

# EXP_2026-07-11 Blackberry active-counter underflow

## Question

Why can Flik throw briefly after collecting the Training Blackberry and then
lose Square throws permanently, even without pausing?

## Preflight

- ABL revision: `e6402e8717f56df37b47405f6423aad0882ed502` with the operator's existing dirty worktree preserved.
- DuckStation fork revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, dirty external-debugger worktree.
- DuckStation binary SHA-256: `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
- Timing-matched scenario binary SHA-256: `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.
- Isolated debugger config: `/tmp/duckstation-debugger-blackberry-0711`, port `23988`; the user's port `2346` was not touched.
- Pre-fix ALLMODS BIN SHA-256: `004d35550c9211375e1795452d880b89f33275fbc46522b0a8056cde2c00ce4b`.
- Movies used for Training anchors: `TRAINING_NPC_STAGES.movie.json` SHA-256 `2b05a9758975a3dd983503a216e347b49a1b344ea9435954d2f325a29fe28f0d` and `ALLMODS_COLLECTING_TRAINING.movie.json` SHA-256 `fbc0ef077f5bcbd3f384e8d0a0f55871b47101d20e8db8481394c35b1a3615b7`.

The checkout documents the new `functionTrace.start` API, but the selected
runtime binary returned `Unknown method`. The experiment therefore used the
available non-halting `accessLog` and `execTrace` APIs. This availability check
is why the result does not claim function-trace evidence.

## Resolved-assembly ownership chain

The original instructions establish one owner pair for `0x800A6596`:

1. `0x80048FFC` reads player `+0x96`; `sltiu` at `0x80049004` and the branch at `0x80049008` reject counts `>=4`.
2. The shared throw tail increments the byte at `0x800471E0`.
3. Projectile-retirement cases decrement the same byte; the observed straight-berry case stored at `0x800595CC`.

Original berry pickup cases change selector `0x800A6597` but do not clear
`0x800A6596`. The MOD arm cave violated that contract with
`sb zero,0x6596(at)` at `0x8008121C`.

## Atomic causal sequence

A cold Training sequence collected and equipped the Blackberry. Normal
post-pickup throws alone were healthy: repeated throws incremented at
`0x800471E0`, retired at `0x800595CC`, and returned the count to zero.

The exact bad arm-store effect was then applied while a real thrown Blackberry
was live:

| Event | Emulator frame | Active count | Evidence |
|---|---:|---:|---|
| Real throw becomes live | 6848 | 1 | throw-tail access log |
| Model the arm cave's exact store | 6848 | 0 | write `00` to `0x800A6596` |
| Real projectile retires | 6880 | 255 | guest store PC `0x800595CC` decremented zero |
| Next Square attempt | 6923 | 255 | zero hits at `0x800470AC` |

This proves the lockout is the original unsigned `<4` gate responding correctly
to corrupted ownership state. It is not a pause-input regression, and the fix
must not bypass the gate.

## Fix

`mod/patch.asm` replaces only the arm cave's `0x8008121C` store with `nop`.
The cave still writes sentinel `5`, the common normalizer still captures private
Blackberry state, and all throw/spawn/retirement behavior remains original apart
from the established fast-physics flag.

The rebuilt live prefix at `0x80081210` is
`050002240a80013c976522a000000000`. `mod/build.py` now verifies these bytes,
and `tests/test_blackberry_build_guards.py` rejects the former
`966520a0` (`sb zero,0x6596(at)`) word.

## Validation

- Focused Blackberry plus Training regressions: `7 passed`.
- Complete `mod/mods.yaml` build passed all 13 embedded-file checks.
- Rebuilt ALLMODS BIN SHA-256: `eb9b1f93bbc10f7ba604ae20a67ab6532e4d2f92910dc0ae27619dcc2b635b6e`.
- Patched pre-asset EXE SHA-1: `a7c5dc43768890515d371fb92e8c4d8717dd2d31`.
- On a cold boot of the rebuilt image, private Blackberry state was armed with native selector `0`; eight Square taps produced eight hits at native dispatch `0x800470AC` and eight hits at fast-physics apply `0x800810DC`. Sixteen counter writes paired the eight throws with eight retirements, no retirement observed zero, and final count was `0`.
- Declarative scenario `blackberry_pickup_preserves_active_counter` cold-booted
  ALLMODS, waited on the actual reveal transition (`entry Y == -50`), seeded one
  outstanding native owner, and moved all three player-position mirrors to the
  revealed pickup. The real arm/normalizer path set private equipped `1`,
  effective index `5`, kept native selector `0`, and preserved active count `1`.
  This is the behavioral assertion that the former store fails. Scenario report
  SHA-256: `64e62d8116163581adeba4589ae64e15b36d605e17ee0c06ab2043b5efdc2c27`;
  the isolated PID-scoped cleanup passed.
- `mod/smoke_test.py --disc build/ABL_ALLMODS.cue` passed BOOT, ALIVE, RENDER, and WALK. Report SHA-256: `69261c9df054a518dfef467f11d3e8a27a3bc18360f6a884e9362d333035c2c2`.
- `tools/run_safe_tests.py` passed `124` tests (`7` explicitly deselected), and
  `tools/validate_mod_layout.py` accepted the `blackberry,golddrop,grain_hud`
  declarations plus the 954-byte consolidated EXE delta.

The consolidated image changed the old fixed-frame player-sector anchor. The
final eight-throw check therefore armed the private equip bytes directly, while
the separate declarative scenario proves a fresh automated walk-over pickup by
triggering on the reveal state instead of a hardcoded frame. The causal pre-fix
experiment used the real cave store value and a real native projectile retirement.

## Separation rule

The active-count read/compare, throw increment, retirement decrement, and
original pickup non-write belong in Canon. The Blackberry arm cave and its
post-assembly signature belong in Mods. Movie anchors, perturbation, runtime
PCs, hashes, and validation results remain in this Experiment.
