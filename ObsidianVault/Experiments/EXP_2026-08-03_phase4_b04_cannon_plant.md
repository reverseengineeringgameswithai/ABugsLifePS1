---
kind: experiment
id: EXP_2026-08-03_phase4_b04_cannon_plant
date: 2026-08-03
status: complete_bounded
confidence: high
row: B04_cannon_plant
methods: [pristine_asm, c_static_analysis, retained_trace_capsule, offline_reconstruction]
---

# Phase 4 B04 - cannon plant launch

## Question

Close the high-yield B04 requirements: entry/contact, seated timing, launch vector and
source, air state, cannon-to-dandelion behavior, and landing. Escalate to DuckStation
only if the retained capsule lacks a named domain.

## Inputs and identity

- Pristine executable: `SCUS_942.88`, SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Movie: `movies/Phase4/B04_cannon_dandelion_combo.movie.json`, SHA-256
  `7028dbd49115a9fe181a2405fd7800af8f37a822adba06da256629ed1ac05d72`.
- Start state: `movies/Phase4/B04_cannon_dandelion_combo.movie.sav`, SHA-256
  `c3c0f69ce28e8d264b328d95231d40e5159922771e8150e7f4cf25ad6325a28e`.
- Capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B04_cannon_dandelion_combo`.
- Capsule manifest SHA-256:
  `41ff30733e08c5b4e070ea7ac2c7129ecc807d3c19aaf998f990fbf13b914e37`.
- Central preserved tree SHA-256:
  `7efb83f5e09186a8f93eec10336a490c20f86d57f4091dc6716d4bf225bb09b6`.
- Media identity in the manifest: pristine `SCUS-94288`, *Disney-Pixar A Bug's Life*.

## Capsule acceptance

The v2 capsule is complete, reports no error and no truncation, and covers 488 frame
boundaries (`164199..164686`), 121,909,399 instructions, and 17,209,424 passive block
events. Its independent control matches cycle, frame, registers, RAM, VRAM, SPU RAM,
and full-machine fingerprint exactly. The C reader verifies all nine preserved chunk
hashes and reconstructs all three frame domains while checking every stored SHA-256.

This is frame-boundary evidence with per-frame block counts, not an every-cycle trace.
The preserved run used the capsule's passive CachedInterpreter coverage path; no
`execTrace` claim is made and no live instrumentation was armed.

## C investigation

Executed during the investigation:

```bash
cc -O2 -Wall -Wextra /tmp/phase4_b04_probe.c -o /tmp/phase4_b04_probe -lcrypto -lzstd
/tmp/phase4_b04_probe ./SCUS_942.88 \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B04_cannon_dandelion_combo/chunks/000000-f164199-f164258.tcap.zst

cc -O2 -Wall -Wextra /tmp/phase4_b04_capsule.c -o /tmp/phase4_b04_capsule -lcrypto -lzstd
/tmp/phase4_b04_capsule \
  ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B04_cannon_dandelion_combo
```

Repository equivalents are `tools/phase4_b04_static.c` and
`tools/phase4_b04_capsule.c`.

## Observation

- The type-2 handler range executes throughout the mature-plant walk; movie frame `119`
  takes the long trigger path (7 retained blocks), changes plant state `1 -> 2`, and
  writes lockout `17`.
- From frames `119..151`, the timer appears as `17..1` on alternating movie frames.
  Player position is fixed and `vx/vy/vz` remain zero.
- Frame `153` is the first post-launch boundary: mode `6`, `vy=-7936`, player Y
  `-29786`. The seated Y immediately before launch is `-21850`.
- The apex is frame `215`, Y `-148826`, `vy=0`: rise `126976`.
- Ordinary descent reaches `vy=4096`. Latch `11` appears at frame `275`; frame `277`
  changes `vy` to `350`, which persists through frame `457` while lateral steering
  continues.
- Landing contact is frame `459`; frame `461` has grounded mode `0` and latch `0`.
- Cannon animation state returns `2 -> 1` at frame `191`.

## Static causal attribution

- `0x8005C110` owns eligibility, carry cleanup, plant animation/state, and the write of
  `17` to player `+0x7C`. It has no player-velocity or camera-struct store.
- `0x80048658..0x8004869C` decrements the timer and pins all velocity components to zero
  while seated.
- Timer expiry loads the fixed immediate `-8192` at `0x800486B8` and stores it to `vy`
  at `0x800486CC`. Same-update gravity explains the first boundary `-7936`; therefore
  the old `-7680` attribution was one physics tick late.
- Latch `11` selects `0x800486DC..0x80048728`, which applies `vy += 256` below `350`
  and otherwise clamps to `350`, then clears the latch when grounded.

## Inference boundary

The handler's return to ready state and lack of a permanent one-shot bit make repeat
entry structurally available, but this movie does not exercise a second entry. The
standard camera-follow mechanism remains active because neither cannon-specific path
writes the camera struct; exact transform samples were not required to identify the
physics contract.

## Closure decision

B04 remains **Partial**, but is a substantiated bounded partial and should be left now.
Every named high-yield mechanic is closed. Exact camera-transform attribution,
animation/SPU asset names, and an all-level cannon-instance census are low-return breadth
without a concrete MOD dependency. No Interpreter movie and no cold boot are required.

## Closure audit — 2026-08-04

Status: **Substantiated Partial / bounded-exhausted**.

The pristine opcode guard and retained-capsule reducer were rerun. The capsule reconstruction covered 488 frame boundaries across nine hash-verified chunks, with 266 cannon-handler blocks and 524 shared launch-case blocks. It reproduced contact, the 17-tick seated hold, fixed `(0,-8192,0)` launch seed, ordinary ballistic flight, dandelion latch `11`, sustained `vy=350`, and grounded latch reset.

The capsule reducer had a dormant summary-format defect: two obsolete vector arguments remained after the output changed to the literal `(0,-8192,0)`. Removing those dead arguments changed no analysis logic or evidence. The corrected reducer SHA-256 is `22d4ee2b0304a497692e115914af73353b86951c0db8b23997b425b74b9e911d`.

Machine-readable disposition: `analysis/phase4_b04_bounded_exhaustion.json` (`578fa7c910edd914c9e6ca5f09151fc57b299896c066a9eef62712714eab2bf4`). Remaining exact camera-transform, animation, SPU-name, and all-instance geometry work is explicitly low return and outside the behavioral bound.

Additional Interpreter movie required: **no**.
