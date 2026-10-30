---
title: "Phase 4 A15: uproot/discard plant"
date: 2026-08-03
tags: [phase4, reverse-engineering, plants, seeds]
status: complete
---

# Phase 4 A15: uproot/discard plant

## Conclusion

A15 is **bounded exhausted** for Phase 4. A new Square press selects a nearby,
mature plant whose `slot+0x2E` eligibility bit is set. The player path clears
that bit and raises the uproot bit while retaining the plant's backlink to the
same seed actor. The seed descends at the plant's X/Z. When the plant animation
command stream reaches its zero terminator, pristine instruction `0x8005CE2C`
clears `slot+0`, the engine's logical slot invalidation.

This is not full physical zeroing. The seed backlink and several slot fields
remain as inert residue after `slot+0 == 0`. No seed actor is destroyed or
created, the plant cursor does not decrement, and the global selection lanes do
not change. The seed source color byte does **not** remain set: it resets to `0`
at `0x80049DF4`. The exact result is therefore "same actor and selection, reset
source color," not "retained color and selection."

No new Interpreter movie is required. The accepted capsule supplies four
behavioral cycles. The state-anchored movie was used only to reach a narrow
pre-clear state without instrumentation; playback was stopped before arming
`accessLog` or `execTrace`, so its CachedInterpreter replay was never exposed
to an instrumentation-induced mode switch.

## Prior residuals and disposition

The prior row was Partial pending the teardown writer, color/selection fate,
object identity, and counter cleanup. All are now answered. This does not claim
that every visual plant animation was enumerated; all observed types converge
on the shared animation-command teardown path.

## Immutable inputs and retained evidence

| Item | Identity |
|---|---|
| Pristine executable | `REBUILD/files/SCUS_942.88`, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20` |
| Pristine retail cue | `Disney-Pixar A Bug's Life (v1.0).cue`, SHA-256 `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644` |
| Movie | `movies/Phase4/A13/blue_seed_levels.movie.json`, SHA-256 `79d0aa0d26bcd760316f6bf685bf781f571ec63806a09d78be84d36ab01b68e1` |
| Movie start state | `movies/Phase4/A13/blue_seed_levels.movie.sav`, SHA-256 `9198c8c3daa896813f0198ecb2a1b7068c7035116aed0aadbc1072ffdb01f5c3` |
| Retained capsule | `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/A13__blue_seed_levels` |
| Capsule manifest | SHA-256 `81053aba5b5ec9bb9e33fbb944fffd09d9df2ed95528ff8dafb931e042b7f17d` |
| DuckStation binary | SHA-256 `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899` |

The capsule manifest reports complete source and output, empty error,
`truncated=false`, and exact control/capsule cycle, frame, RAM, register, VRAM,
and SPU fingerprints. It contains 3,796 movie frames and 940,263,566 retired
instructions. Because it was captured in CachedInterpreter, it was used only
for offline frame-boundary and basic-block analysis.

## Accelerated offline result

The C capsule reducer `/tmp/phase4_a15_capsule.c` (SHA-256
`4399f63edd27844045deefd5dee0e262cd65ade9e2ce358dbfc96cd229035b65`)
produced `/tmp/phase4_a15_capsule.out` (SHA-256
`c9c9540ae3b9ac0f5c05c738d5160e57056a25ad9e6300339943dd21d92a1aaf`).
It found:

- four slot creations and four slot teardowns;
- teardown windows 750-765, 1695-1710, 2790-2805, and 3750-3765;
- plant types `7, 7, 6, 7` across those cycles;
- a constant count of three live type-11 seed actors;
- no RAM, VRAM, or SPU fingerprint mismatch.

The Phase-2 oracle supplies the action pairing: each teardown follows a Square
edge by 40-170 frames, the seed returns from exactly `+20480` above ground at
pinned X/Z, and plants persist for 300-600+ frames in negative windows without
an uproot input.

## Pristine ASM analysis in C

The first affine scan correctly isolated the slot writer but also contained a
rejected table of guessed direct-contract PCs. Those guessed contracts are not
evidence. The corrected targeted disassembler is
`/tmp/phase4_a15_disasm.c`, SHA-256
`02c43323af9f2d51a675d607350ecd20224f6a8edef1263b9829d79a6c5b6c45`;
its binary SHA-256 is
`53580b7a3679281772b15c52ce3fa99fcd8b8627bf58d87ce2ee11e614ab8e21`
and output SHA-256 is
`a144aded796822889b99c08d9f296c952eedb94d7ef26541a2615f597d3f2f3f`.
It re-verified the pristine EXE hash before decoding.

### Input admission and ownership handoff

`0x800478E8..0x80047A24` implements the uproot admission path:

```asm
800478E8  lh    v0,0x2488(v0)
800478F0  andi  v0,v0,0x8000
800478F4  beq   v0,zero,80047E90
80047900  lh    v0,0x2380(v0)
80047908  andi  v0,v0,0x8000
8004790C  bne   v0,zero,80047E90
...
80047930  lh    v0,0(s1)       ; occupied
80047940  lh    v0,2(s1)       ; mature animation gate
80047950  lhu   v0,0x2E(s1)
80047958  andi  v0,v0,2        ; eligible
...
80047A18  lw    v1,0x20(s1)    ; retain seed actor backlink
80047A1C  andi  v0,v0,0xFFFD   ; clear eligibility
80047A20  ori   v0,v0,0x0040   ; request uproot
80047A24  sh    v0,0x2E(s1)
```

The paired sampled input words establish a new-edge test for mask `0x8000`.
The movie/action pairing identifies that mask as Square. Candidate selection
also imposes nearest-plant, distance, and facing gates before the state write.

### Logical teardown

`0x8005CD2C` is the shared 20-slot animation interpreter. At an animation
boundary it reads the next command through `slot+0x1C`. A nonzero command
continues or loops; a zero command reaches this branch-delay-slot store:

```asm
8005CE04  lw    v1,0(v0)
8005CE0C  beq   v1,zero,8005CE28
8005CE10  sw    v1,0x18(s0)
8005CE28  j     8005CE8C
8005CE2C  sh    zero,0(s0)     ; logical slot invalidation
```

The inverse allocation boundary is `0x8005BE90` (type), `0x8005BF18` (seed
backlink), and `0x8005BF3C` (`slot+0x2E` initialization).

## Narrow live attribution

Two fresh absolute config directories and dedicated ports/tokens were used.
Each instance reported pristine `SCUS-94288`; only its owned PID was stopped.

### Run 1: state-field discovery

At movie frame 700, playback was stopped before instrumentation. During the
subsequent 120-frame Interpreter continuation:

- the same seed descended from Y `18455` to ground Y `-2028`;
- seed actor count remained three;
- source color changed `1 -> 0` via `0x80049DF4`;
- selector lanes remained `1144000000000000`;
- slot type did not clear, so this run is not teardown attribution.

Artifact `/tmp/phase4_a15_live.json` has SHA-256
`c70223ae75bc9c171c42c196daf3d032f4d4bc72e318f0dda75757271bf674ed`.
All 174 access events were retained without truncation.

### Run 2: exact clear boundary

The fixture was restarted and replayed without instrumentation to movie frame
745. Playback was stopped, a write-watch covered slot 0, and `execTrace`
watched `0x8005CE2C`. The 40-frame continuation produced:

- exactly one untruncated execution hit;
- registers `s0=0x80090BF0`, `v1=0`, `v0=0x8007A2AC`, and
  `ra=0x8004F018` at the store;
- exactly one matching type write from `0x8005CE2C`;
- slot type `7 -> 0` and animation pointer `0x8007A0BE -> 0`;
- seed backlink unchanged at `0x8009FE04` and seed count unchanged at three;
- cursor unchanged at one and selector unchanged at `1144000000000000`;
- source color/override unchanged at the already-reset `0/0`;
- `slot+0x2E` retained as residue (`0x2005`).

Artifact `/tmp/phase4_a15_live_v2.json` has SHA-256
`071a58fdb5fc25bd52690466c469cd5fe93e2ab5dc1eb53adb1f84e107a270d2`.
All 42 access events and the one execution event were retained with
`truncated=false`.

## Evidence classification

**Observed:** four Square-associated cycles return the same seed record to
ground; actor count does not change; color resets; selection and cursor do not;
only slot type becomes zero at final cleanup.

**Inferred from pristine control flow:** `slot+0` is the occupancy
discriminator, so residual backlink/state fields are inert after it is zero.
The shared command interpreter explains why distinct plant types converge on
one cleanup store.

**Causally confirmed:** `execTrace` captured the terminal instruction with
`s0` equal to the disappearing slot, and `accessLog` captured its type write in
the same run.

## Phase 4 disposition

A15 is Full and bounded exhausted. Enumerating every visual plant animation
would not change the shared admission, seed identity, reset/retention rules, or
teardown writer. Reopen only if another plant family is shown to bypass
`0x8005CD2C`, or a MOD changes the animation-command format or occupancy field.

See [[SYS_plant_uproot_discard]] and [[SYS_seed_carry_plant_lifecycle]].
