---
kind: system
id: SYS_grain_harvester
name: Grain harvester equipment, attraction, and enemy contact
status: partial
confidence: confirmed
source_state: original_game
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-07-30_phase4_c13_grain_harvester
  - analysis/phase4_c13_harvester.json
  - analysis/phase4_c13_harvester_live.json
src_paths:
  - src_re/grain_harvester_80051db4.c
  - config/phase4_c13_harvester.yaml
  - tools/phase4_c13_harvester.py
  - tools/phase4_c13_harvester_live.py
patch_policy: safe_to_read
---

# SYS_grain_harvester

## Confirmed pristine behavior

The C13 recording is a LEVEL01 pristine-retail fixture. Square is pressed at
movie frame 80; the native state changes at frame 83, and the first visual equip
motion is around frame 87. The state is:

- `0x800A657E` (`s16`) = `1` while equipped and `0` after disengagement;
- `0x800A6590` bit `0x0080` = harvester enable;
- authored harvester actor id `0x23` at `0x800A1DFC` in this fixture.

The entry path is `0x80051DB4..0x80052090`. It requires a fresh Square edge,
actor id `0x23`, grounded/proximity and idle gates. Stores at `0x80051EA0` and
`0x80051EB0` set the state and bit; `0x80051F60` maintains state `1`.

## Grain attraction law

`FUNC_80053814` reads the same `0x0080` bit at `0x80053BEC/0x80053BF4`.
For a type-`0x3f` source of kind `0x14`, it evaluates:

`sum((((player_file_xyz, with Y - 0xE6) - source_xyz) >> 3)^2)) <= 0x15F8F`

Passing sources become ctor-`0x51` contact records and their source Y is set to
`0x80000000`. Nine complete source → contact → grain-counter chains reproduce
in the retained movie. Engine activation occurs at frames
`161,177,197,227,261,431,453,481,505`; the visible first/last attraction
reported by the operator follows the engine activation by at most eight frames.

This is distinct from ordinary direct grain pickup: grain does not converge
toward Flik unless the harvester is equipped.

## Disengagement and enemy contact

An uninstrumented Cross press from the shared movie-end anchor changes
`0x800A657E` from `1` to `0` and clears bit `0x80`.

Remaining equipped gives a causal enemy-contact pair on the same pristine
anchor. The LEVEL01 bee (id `13`, record `0x8009FF0C`) changes HP `4 → 998` at
`+136` frames, then is retired from the live table at `+222`. Immediate Cross
disengagement leaves that same record at HP `4`, id `13`, and live at both
checkpoints. `FUNC_8004ABF4` reads bit `0x80` at `0x8004B158/160` and its
special branch writes the delayed-destroy sentinel `998` at `0x8004B204/208`.

## MOD consumption contract

A future harvester MOD may read:

- state `0x800A657E`;
- equipment/contact enable bit `0x800A6590 & 0x0080`;
- the kind-`0x14` source gate and ctor-`0x51` construction path;
- the HP-`998` permanent-retirement handoff.

It must not assume every enemy family is eligible, every stage authors a
harvester, or that state/bit writes alone reproduce rendering and animation.
Patch only a pristine-derived output and validate attraction, direct pickup,
enemy contact, disengagement, audio, and presentation with cold-boot controls.

The authoritative typed Phase-4 machine representation is
`config/phase4_c13_harvester.yaml`. These fields are deliberately not added as
new entries to Phase 3's closed semantic-lifetime registry until that retained
live experiment can be regenerated on pristine media. Likewise, player
`+0x7E` is not promoted into the Phase-3 record layout by hand because its
unknown-byte census predates this finding.

## Bounded residuals

- exact per-frame writer that steers ctor-`0x51` contacts;
- exact Cross clearing writer PC (the live access logger suppresses this
  edge-gated action; the state-based trace replay also failed to advance);
- eligible-enemy/immunity breadth and all applicable levels;
- render, animation, audio, reset, and persistence ownership.

See [[EXP_2026-07-30_phase4_c13_grain_harvester]] and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].

## 2026-08-02 bounded-exhaustion addendum

The exact grain mover is the shared contact updater, not the ctor or pickup walker.
`FUNC_80053814` stores contact target `-1` at `0x80053C58`; ctor flags `0xEA`
select homing bit `0x08`. The updater selects player targeting and writes Y/X/Z at
`0x8005A4C8`, `0x8005A548`, and `0x8005A56C`.

Cross disengagement has split ownership. `0x8004A94C` stores
`0x800A6590 & 0xFF7E`, clearing bit `0x80`. The active writer at `0x80051F60`
therefore stops refreshing slot value `1`, and the normal positive-slot tick at
`0x80048654` writes `1 - 1 = 0`. `0x8004A808` is not the harvester clear; it is
reachable only on the negative-slot damage path.

Action `0x14` collection calls the shared SFX manager at `0x80054F80` when its
guards pass and increments the grain counter at `0x80054F9C`. Respawn/reset clears
the slot at `0x8005B268` and clears the harvester bit through the retention mask at
`0x8005B340`.

The harvester enemy sub-branch has no actor-id whitelist. It inherits eligibility
from common resolver/contact/actor-flag gates, then reads bit `0x80` at
`0x8004B158/0x8004B160` and writes HP `998` at `0x8004B208`. Only the LEVEL01
id-13 bee has a retained matched behavioral control, so do not generalize permanence
to every enemy family without a named fixture.

C13 is **partial, high-yield row-specific work exhausted**. Exhaustive all-level, enemy-family,
animation/asset, and save-load breadth is deferred. See
[[EXP_2026-08-02_phase4_c13_bounded_exhaustion]] and
`analysis/phase4_c13_asm_static.json`.

## Phase 4 closure boundary - 2026-08-02

The confirmed original-game semantics above remain Canon. Campaign status does
not: C13 is partial, with high-yield row-specific work exhausted, not solved.

C RAW analysis surveyed all 15 active scene resources and found the harvester
placement in scene IDs 1,3,5,7,10,12 (operator levels
1,2,5,8,10,11). Each is record 63 with type word 0x00002223 and identical
non-position parameters. This closes static applicability, not behavioral
breadth. The retained natural fixture represents one placement. The complete
pointer frontier and exact render/animation/SPU interfaces remain open as
recorded in analysis/phase4_c13_dod_scorecard.json.
