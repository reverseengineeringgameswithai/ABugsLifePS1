---
kind: system
id: SYS_kick_attack
name: Ordinary kick attack
status: confirmed
updated: 2026-07-15
confidence: confirmed
evidence:
  - EXP_2026-07-15_phase4_kick_attack
---

# Ordinary kick attack

The pristine ordinary kick is a resident action/contact chain. The player
update recognizes an L2-or-R2 plus fresh-Square chord and arms a signed timer;
the actor-animation owner consumes the timer for animation; the resident
proximity updater consumes it with current actor geometry and flags.

## Original-game facts

- `0x80048F44` reads decoded action word `0x80082488`. At least one shoulder
  bit in mask `0x0300` and Square bit `0x8000` are required.
- `0x80048F64` reads previous pad word `0x80082380`; Square must be clear there.
  Square alone, a shoulder alone, and Square held before the shoulder do not arm
  the attack.
- Eligibility also requires the shared signed timer at player `+0x7A` to be
  nonnegative, signed `(floor_y - y) < 1024`, and player `+0x5C == 0`. The exact
  distance 1024 rejects while 1023 accepts. Riverbed Flight is airborne outside
  the ordinary path and remains timer 0/animation 4 under the chord.
- `0x80048FB4` writes `-16` to timer `0x800A657A`. While negative,
  `0x80048EB8` adds one per native player update until zero; a fresh chord then
  arms again. A negative-timer retry cannot restart the countdown.
- This timer is shared signed action state, not a pure `-16..0` kick-only field.
  `0x80048F3C` can write positive 12 for another action and `0x80048ED4`
  decrements positive values. Only a negative value activates ordinary kick
  contact through this timer predicate.
- In the resident actor-animation owner, a negative timer selects animation 1
  at `0x80056718`. Exact timer `-16` clears player animation phase `+0x44` at
  `0x80056924`.

Resident proximity updater `0x8004ABF4..0x8004B6AB` walks compact live actor
pointer table `0x80090748`. Its contact shape comes from the actor's current
16-byte animation-frame geometry at `actor+0x74 + 16*(actor+0x44)`, transformed
by actor heading through the resident 12-bit lookup table at `0x80074970`.

For a matched ordinary contact, negative kick timer makes the attack predicate
true. Current actor flags then bound the generic response:

- flag `0x20`: separate actor path, not ordinary kick damage;
- flag `0x800`: ordinary proximity response suppressed;
- flag `0x80`: response state 15, with the ordinary state-30 branch suppressed;
- otherwise: kick writes actor response 30 at `0x8004B5D8` and player animation
  30 at `0x8004B644`; matched neutral contact instead writes actor response 15
  and damages the player.

Actor ID is not the classifier in this generic resident branch. Across the
distinct active `(actor id, flags)` classes present at the retained moments in
Training, stages 1–15, and bonuses 1–3, all 28 matched the static flag law: 20
ordinary state-30 classes, three `0x80` response-only classes, two `0x20`
classes, and three `0x800`-suppressed classes. This is an active-moment class
matrix, not a full authored enemy or boss roster.

All instruction words and region hashes were re-read from hash-pinned pristine
`SCUS_942.88`. ALLMODS was not used as original-game authority. The machine
contract is `config/phase4_kick.yaml`; retained evidence is
`analysis/phase4_kick.json`.

## Lifecycle and boundaries

Pause freezes position, kick timer, and animation; resume restarts recovery.
Native same-scene death/respawn changed an established nonzero timer precondition
11 to zero, decremented lives, restored health 4, and accepted a fresh R2+Square
kick. Static clear writers also cover scene load, resident action reset,
transition, and plant/cannon takeover.

A04 owns the ordinary input, timer, animation, and generic resident contact law.
Enemy-family AI, berry immunity, death/respawn, permanence/quotas, boss or
overlay-special contacts, E02 geometry, and F14 flight motion retain their own
registered rows. No A04-private allocation or serialized progression exists.

See [[EXP_2026-07-15_phase4_kick_attack]],
[[Game Solving Campaign - Kick Attack]], and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
