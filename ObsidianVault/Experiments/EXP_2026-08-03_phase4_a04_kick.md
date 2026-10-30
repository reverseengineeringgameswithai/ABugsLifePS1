---
title: Phase 4 A04 kick bounded exhaustion
date: 2026-08-03
status: complete-bounded
row: A04_kick
---

# Phase 4 A04 kick bounded exhaustion

## Question

Resolve the remaining A04 kick fields: recovery and animation timing, effective
contact volume, whether a kick damages enemy HP, reaction classes, and whether
another Interpreter movie is required before moving on.

## Evidence identity

- Retail serial: `SCUS-94288`.
- Resident executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Mounted CUE SHA-256: `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`.
- Mounted BIN SHA-256: `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`.
- New movie: `movies/Phase4/Interpreter/A04_kick_contact.movie.json`.
- Movie SHA-256: `6f166a6e342aaa1c1c52cd3ca19ab35c32aed7eb75fa6c7d0a3ea46bdbc35877`.
- Paired SAV SHA-256: `dab6ec09dd7e351ed82b9ddd7981627d3932451e787efceba58fc7196372983d`.
- Movie format/mode: v4, Interpreter, state anchored, 319 input frames.
- DuckStation binary SHA-256: `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`.
- Fork revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` (dirty worktree recorded; binary hash is authoritative).
- Isolated config: `/tmp/duckstation-a04-kick-20260803-1`, port `24304`, token `a04-kick-20260803-1`.

## Capsule-first check

The retained capsule at
`~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/kick`
was checked before replay. Manifest SHA-256 is
`b3b42f451f3447c3f30fdd7f78549e520a3c89c16bb056585b11f56214db9fed`.
It reports complete capture, no truncation/error, and equal clean/control final
fingerprints. Its source movie contains five kicks in empty space, so it answers
the action-timing questions but lacks the actor-contact domain. That named gap
justified the isolated live replay.

## Static ASM investigation with C reducers

The resident executable was queried by `/tmp/a04_static.c`, compiled as
`/tmp/a04_static`. Source, binary, and output SHA-256 values are:

- Source: `6d6a287eefc9f7ce96ab95d8cdeeb661a64d307f2025c0e69f4147cd9b73ac55`.
- Binary: `d8d5e569037b0a87200588a80eaa6f4516b8648050b514366533329f3aea63b9`.
- Output: `24a6c8125f75a421c9806b2fd00f726a0b7a4512dc924d051f258a812a16fc75`.

The C pass decoded the input/timer interval at `0x80048EA4..0x80048FB4`,
animation selection in `0x800563D4`, effect emission in `0x80055654`, and the
kick-specific path through `FUNC_8004ABF4_proximity_updater`.

Static conclusions:

- The fresh L2/R2 plus Square admission stores signed timer `-16`.
- The timer moves one unit toward zero per gameplay update.
- Negative timer selects animation 1; initial `-16` clears its frame accumulator.
- Timers `-7..-2` emit ctor109; `-7` additionally emits ctor108.
- Kick contact reuses actor body collision plus a forward-half-plane gate.
- The success path changes flags/knockback/animation but has no actor-HP store.
- Flag `0x80` selects a reduced reaction, not full immunity.

A durable readable reconstruction is banked in
`src_re/kick_action_80048e9c_and_contact.c`.

## Natural movie observation

The full movie was replayed clean and with execution tracing at normal speed.
Both runs ended on emulator frame 30952 at cycle 17524557977. The exact equality
is the flight check that instrumentation did not change execution mode or desync
this v4 Interpreter fixture.

Observed events:

- Kick arm: emulator frame 30743.
- ctor108: frame 30788.
- ctor109: frames 30788, 30793, 30798, 30803, 30808, and 30813.
- Kick-contact success branch: zero hits.
- Target: actor ID 39 at `0x800A011C`, flags `0x4005`, HP 8.

The movie is a natural near miss, not a connecting-kick oracle. At timer `-11`
and animation 1, the C geometry reducer measured scaled delta `(545,120,-64)`,
radius 525, squared distance 315521, and squared radius 275625. It misses the
broad sphere by 39896 squared units before the model ellipsoid is considered.
Screenshot `/tmp/a04_kick_contact_frame.png` has SHA-256
`3773a29d09d8e4de564b1316aa788ca5f4ff82e923b51321333bea22f61fb972`.

## Causal positive control

The movie was replayed through input index 97 and stopped. While paused, only
player X was changed to `-35000`; player Y/Z, facing, animation, and the entire
enemy record were preserved. A fresh R2+Square then crossed the contact boundary.

Results:

- Kick-contact PC `0x8004B450` executed twice at timer `-16` then `-15`.
- Actor flags changed `0x4005 -> 0x5005 -> 0x5007`.
- Actor knockback `+0x6C` became 30.
- Player impact animation became 30.
- Normal player-damage call `0x8004B4A0` had zero hits.
- Actor HP `+0x6E` remained 8, with zero targeted HP writes.

This control covered only timer `-16/-15`, before ctor109's later `-7..-2` effect
window. It proves that the immediate body-contact branch does not write HP; it does
not classify the later kick-effect attack.

The execution summary SHA-256 is
`1e862eba8ca0a5717c53cc7f3f8f23677e7a59a9b7712984b862420d4726a653`;
the access summary SHA-256 is
`0ab386516dd5493bf3172a51a566c47e58ac6bc54108be5a586eb9a0f0e5b380`.

## Reaction-class A/B control

The positive control was repeated after changing only target flags
`0x4005 -> 0x4085`. Contact still executed twice and the normal player-damage
call remained absent. The full knockback-30 and player-animation-30 stores had
zero hits; reduced knockback-15 store `0x8004B650` executed twice. HP remained 8
with zero HP writes.

The execution summary SHA-256 is
`44026924a1d72ed74008981efd360682b09ba05816f452fde0da3e9e6dcf89b9`;
the access summary SHA-256 is
`9bdfe74f86d81231d37ff8c5c0399673630928761005bc0a02d7b4ead6aee2e4`.

## Rejected control

An earlier intervention placed player X/Y/Z at the actor center. It triggered
ordinary body contact with the kick selector false and reached the player-damage
call. Because it changed multiple spatial dimensions and tested a different
branch, it is rejected as kick evidence rather than silently folded into the
result. Its execution/access summary hashes are
`8bf8c6730f95b678fb8faa7acd68cf7026e875ef3e8d216391bf09ea66660216` and
`9f48289a7f0616b155eb048ae7f3474dfba0cc7325c5865384edb09a1720b523`.

## Worm correction and downstream damage trace

The follow-up fixture `movies/Phase4/Interpreter/A04_kick_worm_contanct.movie.json`
is a v4 Interpreter movie with 353 input frames. Movie and SAV SHA-256 values are
`6fa11751ae055831a5323e1eee554217b1e1c2a26edfce2d0aa8eddd2eb2adb2` and
`587cc42c410e6d06c62742b1e598f7ff688df8d3b534549f9024e47c99e93e35`.
Its six Square presses yielded four admitted kicks.

The target was worm ID 40 at `0x800A0C74`, starting with flags `0x48C5` and HP 8.
The natural replay produced three confirmed kick-effect contacts. Each wrote
knockback 20 at `0x80058ED8`, observed masked flag value `0x40` at `0x80058EE8`,
reached the action-class-1 special branch at `0x80058F10`, and never reached the
HP dispatcher. HP remained 8. Dynamic flag `0x80` also rejected 13 of 92 generic
actor iterations, but the persistent flag `0x40` was the discriminator on actual
contacts.

Static ASM/C reconstruction corrected the damage law: ctor109 is action class 1,
and an eligible target reaches `HP - 99` at `0x80059094/0x800590E4`. A runtime-only
control masked flag `0x40` to zero at `0x80058EE4` after the first natural contact.
The next synchronized contact entered the HP dispatcher with HP 8, stored `-91`,
then reached the death tail at `0x800592A8`. The original instruction
`0x30420040` was restored from the pinned save before shutdown.

This retracts the broad earlier statement that kicks do not damage enemy HP. Only
the immediate body-contact branch is non-damaging. The delayed ctor109 effect is a
99-HP attack, effectively an instant kill for ordinary sub-100-HP enemies. Worms
use the flag-`0x40` special branch to consume it without HP loss.

Structured evidence and artifact hashes are in `analysis/phase4_a04_kick_worm.json`.

## Corrected conclusion and Phase 4 disposition

Observation: the supplied movie performs the action and narrowly misses actor 39.

Inference from static flow: the native kick first performs a directional body-contact
reaction, then emits action-class-1 contact objects that normally subtract 99 HP.

Causal confirmation: the X-only and flag-`0x80` controls distinguish the immediate
body reactions. The worm movie plus the mask-zero control distinguish delayed
action-class damage from the flag-`0x40` special bypass.

A04 remains `partial` under the roadmap's strict all-context definition, but it is
a substantiated partial at bounded exhaustion. Input admission, action/recovery,
animation/effects, geometry, normal/reduced reactions, 99-HP damage, death handoff,
and worm immunity are pinned. The remaining cross-species flag census, rare >=100-HP
targets, table naming, and per-scene cadence offer minimal return and do not block
moving on. No additional Interpreter movie is currently required.

## Links

- [[SYS_kick_action]]
- [[Phase 4 - Solve Every Gameplay and Engine Subsystem]]
- `analysis/phase4_a04_kick.json`
