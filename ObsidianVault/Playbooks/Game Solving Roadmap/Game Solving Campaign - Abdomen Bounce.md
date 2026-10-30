---
kind: playbook
id: PLAYBOOK_game_solving_campaign_abdomen_bounce
name: Game Solving Campaign - Abdomen Bounce
status: complete
created: 2026-07-15
updated: 2026-07-15
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Abdomen Bounce

## Scope and decision

This completed child campaign covers Phase-1 row A05: ordinary pristine
second-Cross recognition, the exact near-floor/high-slam state split, high-slam
timer and animation, resident target response, expired-impact rebound/reset,
the Bonus-1 consecutive-stomp chain, and action lifecycle.

A06 downhill slide is now completed by its own campaign. E02/E05 collision and animation internals, enemy-family
HP/death/respawn/permanence, boss/overlay contacts, and Riverbed Flight motion
retain their own rows. They cannot dilute or inflate A05.

## Oracle, controls, and breadth

The pinned from-boot LEVEL01 movie contains a first Cross at frames 8350..8377
and second Cross at 8380..8408. Control and in-memory edited branches had equal
player fields, whole-block hash, cycle, and emulator frame before the edit.
Removing only the second Cross left state 2/aux 0 at movie frame 8384; the
control entered state 4/animation 7/aux 8 and later hit terrain with Bonus-1
streak still 0.

Direct valid-field controls isolate the signed distance boundary. State 2 plus
Cross at `(floor_y-y)=8192` selects state 3 without arming the aux field. At
8193 it selects state 4; the writer arms 10 and the first retained post-update
sample is 9. All 18 ordinary gameplay anchors reproduce state 4/aux 9. Riverbed
Flight is the explicit negative: state 0, animation 4, aux 0.

The operator abdomen-slam save begins in state 4/aux 1/animation 7. The pinned
Bonus-1 movie supplies the natural contact chain: streak 1 by frame 128, 4 by
750, then fifth-stomp latch 6/unlock bit 2/scene 0x10 and streak reset by 1250.

## Frontier, state, and lifecycle

- Input/player owner: resident `0x80048138..0x800498AB`; decisive second-Cross
  branch `0x80048C6C..0x80048DB8`.
- Contact owner: resident `0x8004ABF4..0x8004B6AB`; bounded abdomen-response
  slice `0x8004B2AC..0x8004B3D0`.
- State: player `+0x30` velocity, `+0x48` floor Y, `+0x80` shared action state,
  `+0x82` grounded, context-reused s16 `+0x84`, `+0x88` animation; actor s16
  response fields `+0x54/+0x58/+0x6C`; Bonus-1 u32 streak `0x8008223C`.
- Geometry: two strict squared-distance gates use actor center offsets and its
  current rotated 16-byte animation-frame bounds, with a 250-unit margin.

Qualifying impact writes actor state -20 and `+0x54/+0x58=4096`. Aux 1 is an
accepted stomp and can increment the Bonus-1 streak. Aux 0 writes player
velocity -1536, state 5, grounded 0, animation 3, and resets the streak; the
same native update produced observed velocity -1024 after gravity.

Pause freezes the action fields and resume restarts countdown. In the retained
same-timeline death control, fatal contact began, aux was marked 7, native
respawn changed it to 0 and lives 5 to 4, and a fresh double Cross—without a
state reload—entered state 4/aux 9. No A05-private allocation or serialized
state exists. `config/phase4_abdomen_bounce.yaml` is the reusable typed contract.

## Bounded residuals

- The completed A06 campaign owns timer-12 slide continuation; E02/E05 own
  internal collision and animation-asset behavior.
- Enemy-family and boss owners determine family HP, death, respawn,
  permanence, quotas, and special contacts. A05 proves only the generic native
  target response and the paired player-health outcomes.
- F14 owns Flight motion despite consuming the same physical Cross button.

None intersects the completed generic A05 action/contact/Bonus-1 law. Evidence
and failed hypotheses: [[EXP_2026-07-15_phase4_abdomen_bounce]]. Original-game
facts: [[SYS_abdomen_bounce]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
