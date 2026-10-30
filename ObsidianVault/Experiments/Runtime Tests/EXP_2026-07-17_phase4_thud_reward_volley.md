---
kind: experiment
id: EXP_2026-07-17_phase4_thud_reward_volley
date: 2026-07-17
status: reproduced_partial
confidence: confirmed
source_state: original_game
evidence: [analysis/phase4_thud_volley.json, config/phase4_thud.yaml]
---

# Phase 4 — Thud natural reward volleys and countdown-selected variant

## Question and fixture selection

Can the existing complete pristine Thud recording bind another distinct reward
variant and the natural recorded-fight frequency without requesting new operator
input?

The mandatory recursive census found 110 files under `movies/Phase4` and 147
files in the broader movie tree. No Thud pair exists in the Phase-4 subtree.
The sole relevant pair remains root `thud_boss_movie.movie.json/.sav`: movie
SHA-256 `70e5988852315924e7eba7f8ba23632545ad329878e3e5b8a59de91955bcddaa`,
4113 frames / format v1, and save SHA-256
`789d9b601d592748af934c162513e91f1e63a8d2bbe8ce2cb3b9c16876b32a99`.
It was already centrally declared, pristine-classified and provisioned. Fresh
load-free inspection and mounted CUE/BIN hashing verified pristine
`SCUS-94288`; the filename and JSON serial were not treated as media proof.

## Observation

Nine passive `movie.traceToFrame` pairs retained complete, untruncated and
cycle-neutral coverage. Settled targets reproduce:

| target | phase counter | grain | cumulative `0x800B3FF0` calls |
|---:|---:|---:|---:|
| 994 | 1 | 0 | 10 |
| 1336 | 2 | 0 | 20 |
| 1736 | 3 | 0 | 30 |
| 2154 | 4 | 4 | 40 |
| 2548 | 5 | 8 | 50 |
| 2964 | 6 | 12 | 60 |
| 3334 | 7 | 14 | 70 |
| 3754 | 8 | 14 | 70 |
| 4113 | 8 | 14 | 70 |

The final cumulative instruction counts are exact: countdown store
`0x800B3F24` 70, equality-to-five path `0x800B3F34` 7, general path
`0x800B3F7C` 63, allocator and sound calls `0x800B3FF0/0x800B3FFC` 70 each,
resident action-20 tail/grain store `0x800589B8/0x80054F9C` 14 each, and
resident action-9 handler/health store `0x80058864/0x80058890` four each. At
the terminal boundary neither action 9 nor action 20 remains active.

The first natural action-9 collection lies between passive movie targets 1432
and 1433 (post-step playback indices 1431 and 1432). Both traces are complete,
untruncated and independently cycle/RAM/register-neutral:

| field | target 1432 | target 1433 |
|---|---:|---:|
| true health `0x800A6594` | 2 | 3 |
| cumulative `0x80058864` handler calls | 0 | 1 |
| cumulative `0x80058890` health stores | 0 | 1 |
| slot 47 action / TTL | 9 / 62 | 9 / 1 |
| player XYZ | `[129553,3520,-11004]` | `[128414,3201,-12523]` |

The action-9 record retains position `[126549,-348,-14770]`, radius 100,
state 7 and flags 226 across the boundary. Its 56-byte pristine resident
handler at `0x80058864` hashes to
`e89382b9e86e29907d3cee300e6c7b706884bd20f352f2ff217c06e6f799f849`.
Exact words bind state 7 (`0x80058864`), health load (`0x80058880`), increment
(`0x80058888`) and store (`0x80058890`).

The exact 308-byte / 77-instruction save-owned continuation at
`0x800B3ED4..0x800B4004` hashes to
`10992dee6815d74e6b89109980f16d6c60f0230d94f52f0730b7e217d30badba`.
It matches neither staged LEVEL08 candidate and supplies no general Region-A
identity.

## Inference

Each of the seven recorded reset suffixes emits ten reward contacts. The
general branch supplies nine action-20 grain contacts and the countdown-five
branch supplies one action-9 contact. Action 20's grain semantics were already
causally bound through the resident dispatch. The action-9 trace, static
handler and exact health store now prove four natural true-health increments
in this replay. The first bounded effect is exactly +1, from 2 to 3. This does
not establish a universal collection/drop rate, behavior across the full
health domain, or a complete Thud attack policy.

## Causal confirmation and rejected timing hypothesis

Both matched branches reset through cycle-neutral tracing to target 970 with
identical full RAM, registers, emulator/movie frame, cycle, PC, SP, scene,
counter, countdown and grain. The mutation changes only u32 countdown
`0x800B4CB4` from 9 to 6; because only the low byte differs, the RAM diff has
one address. The next native iteration produces:

- control: countdown 8, slot 17 action/TTL/state `20/200/24`;
- mutation: countdown 5, slot 17 action/TTL/state/class `9/200/-42/128`.

Both endpoints have the same emulator/movie frame, PC and SP. The mutation
uses exactly one fewer CPU cycle. An initial generator guard expected cycle
equality and rejected two exploratory attempts; a focused replay measured the
stable -1 delta before the source-fresh run encoded that exact predicate. The
control is causal evidence with a bounded cycle divergence, not a cycle-neutral
branch.

## Retained result and validation

The source-fresh command was:

```text
python3 tools/phase4_thud_volley.py --port 20542 --token '<redacted>' --config-dir /tmp/abl-phase4-i32-thud-action9-final-20542 --instance-state recreated
```

It produced `analysis/phase4_thud_volley.json` SHA-256 `bbdb01df6ba4e925b7eb54bce993c10b0fe4f9e1a45005a68ee45ab5075cc287`,
reverified pristine mounted/save media and stopped only its owned PID
2198546. Focused guards pass 8/8.

The declarative read-only
`pristine_thud_action9_natural_pickup.yaml` replay ran in fresh config
`/tmp/abl-ps1-scenario-rfe5givt`, passed 14/14 assertions and stopped only
PID 2198781. Its transient JSON report SHA-256 is
`6604de6923dcfae7c20cb3f0f05977070e421ac18d5c750213669ba89208c776`.
No report, movie, save, disc, BIOS, token, capture or other copyrighted bytes
are committed.

Iteration 33 added the same Thud pair as a centrally declared C16 consumer,
changing the exact fixture-manifest source dependency without changing the
volley evidence. A fresh isolated replay reproduced every retained outcome;
the current artifact SHA-256 is
`f2e2d41fdfdb4f24e4d585775aec0b93c1a820f55f007ce5a07140a6369918eb`
and only owned PID 2424641 was stopped.

## Boundary

This closes the complete recording's seven-by-ten reward-volley frequency, the
63/7 branch split, 14 natural action-20 grain pickups, one causal countdown-
selected action-9 variant and four natural action-9 health increments. It does
not establish universal reward/collection/drop rates, the full health domain,
other attack sources, complete damage or phase policy, named visual/audio
ownership, initialization, retry, persistence, breadth or failure paths. D18
and F09 remain partial/open.
