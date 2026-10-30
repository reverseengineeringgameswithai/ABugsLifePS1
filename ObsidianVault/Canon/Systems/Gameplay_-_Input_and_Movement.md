---
kind: system
id: Gameplay_-_Input_and_Movement
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_confirmed
confidence: confirmed
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Gameplay - Input and Movement.md
aliases:
  - "Gameplay - Input and Movement"
archived_source: ObsidianVault/Archive/Superseded/Gameplay_-_Input_and_Movement.md
patch_policy: unknown
---

# Gameplay_-_Input_and_Movement

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Gameplay - Input and Movement.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Gameplay — Input & Movement (GAP-0037 — input law decoded, static)
- Archived full source: `ObsidianVault/Archive/Superseded/Gameplay_-_Input_and_Movement.md`
- Migration action: `split`
- Migration confidence: `confirmed`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Gameplay — Input & Movement (GAP-0037 — input law decoded, static)`
- `## Player state structure (STATIC + DYNAMIC, CONFIRMED)`
- `## Movement integrator (CONFIRMED — DYNAMIC/local-only, G29)`
- `## libpad / input read site (LOCATED — static, EXE-read 2026-06-21, key sites spot-verified)`
- `## Input → movement law (CONFIRMED — static, EXE-read; pad-decode + Up + Left/Right independently spot-verified)`
- `## Runtime confirmation (LOCAL-ONLY — RAN 2026-06-21, isolated DuckStation port 23460 / `level02.sav`)`
- `## Confidence ledger`
- `## Next experiments / modding relevance`
- `## See also`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Gameplay_-_Input_and_Movement.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.

## Phase 4 A01 confirmation (2026-08-03)

The ordinary grounded movement chain is now promoted from the legacy source with new pristine-ASM and bounded runtime evidence. `FUNC_80047EBC` supplies camera-relative target heading and magnitude; `FUNC_80048138` converges actual heading, applies run/slow acceleration and decay, rotates the projected components into `player+0x2C/+0x34`, and calls `FUNC_8003633C` with position, velocity, and contact bytes. Normal slope following keeps contact `0x0101`; grounded animations are idle `22`, run `0`, and slow walk `29`; release decays the components to zero and returns animation to `22`.

Analog full-up and digital Up produced identical eight-frame XYZ under the verified `AnalogController`, with the game working word `0x0010`. This confirms they enter the same downstream movement law for that magnitude; it does not claim a complete analog response curve for every stick radius.

A01 is a substantiated `partial`, bounded-exhausted result. Exhaustive per-level collision/slope enumeration remains deferred. See [[EXP_2026-08-03_phase4_a01_move_run]], `src_re/move_run_80048138.c`, `tools/phase4_a01_static.c`, and `analysis/phase4_a01_move_run.json`.

## Phase 4 A02 closure via A01 synthesis (2026-08-03)

`A02_slow_walk`'s own named gap (walk gate, exact speed law, animation/lifecycle) is the
SAME `FUNC_80048138`/pad-word-`0x80082488` mechanism this page's own A01 section already
traces — not a separate system. The speed cap (`andi v0,a0,0x300` at `0x80048494`, selecting
input_cap `0x300` vs `0x700`) and the animation selector (`FUNC_800563D4`'s
`lhu v1,0x2488(v1)` at `0x80056474`, selecting animation `29`) are two independent readers of
the same pad bit — confirmed by a live counterfactual where Up+R2 held 8 frames matches plain
Up's velocity exactly (the slow cap hadn't been reached yet) while the animation switches
immediately. Turning/decay/release are shared code, not walk-specific. See
[[EXP_2026-08-03_phase4_a02_slow_walk]] and `analysis/phase4_a02_slow_walk.json`.
