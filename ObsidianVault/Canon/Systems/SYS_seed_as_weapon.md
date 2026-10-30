---
kind: canon
id: SYS_seed_as_weapon
name: Seed as Weapon
status: partial
confidence: high
source_state: original_game
updated: 2026-08-03
evidence:
  - EXP_2026-08-03_phase4_a11_seed_as_weapon
  - analysis/phase4_a11_seed_as_weapon.json
  - analysis/phase4_a10_a11_capsule_preservation.json
---

# Seed as Weapon

## Confirmed original behavior

Square releases a carried movable seed. In the retained A11 fixture, the release
commits at movie frame `329`, the seed contacts spider-chaser actor id `9` at frame
`349`, and the seed settles at frame `369`. The seed record remains live and unchanged
through the end of the 462-frame capsule, so the attack does not consume the seed.

The target does not take ordinary HP damage. Its HP at `+0x6E` stays `2` while the
contact arm writes `-20` to reaction/knockback `+0x6C`. That field advances by one on
each 30 Hz actor tick. When it reaches zero at movie frame `389`, the generic terminal
path sets HP to zero and unlinks the actor from the live table. Actor ID `9` remains in
the record because permanence field `+0x62` is nonzero. This is an HP-bypassing
temporary KO, not direct damage and not a permanent kill.

## Executed contact arm

Passive block flow at the impact enters `contact_vs_actor_handler` through
`0x80058DE4`, `0x80058DF4`, `0x80058E08`, and `0x80058E10`. Pristine executable words
at `0x80058E14/18` load `-20` and store it to actor `+0x6C`. The branch requires
contact kind `4` and rejects actor flag `0x40`. The handler's shared prefilter also
rejects actor flags `0x20/0x80` and any actor already carrying negative `+0x6C`.

There is no species-ID switch in this hit arm. Eligibility is therefore a runtime
contact/flag predicate after geometric admission, not a hard-coded enemy list. The
natural fixture proves spider chaser id `9`, flags `0x4011`. It does not prove every
authored enemy family reaches the same contact variant.

The executable contains exactly one static twin: `0x8004B2CC/D0`, selected by a
different collision record whose subtype halfword is below `2`. That arm is not
executed by the A11 fixture. Although the seed is physically detached at impact, its
contact remains kind `4`; "carried-contact arm" names the contact variant rather than
the carry state at the moment of collision.

## Seed and presentation outcome

At contact, seed motion changes from `(977,2560,306)` to `(979,271,994)` and then
decays to `(0,0,0)` at `(76495,-17302,544652)`. The seed remains actor id `11`, HP `1`,
and present in the live list through movie frame `461`.

The hit arm writes target reaction components `+0x54/+0x58 = 4096`, enters the
eight-object impact-burst routine at `0x80057F44`, and dispatches cue `17` through
`0x8005044C`. It does not store an animation ID. Exact per-model pose timing remains a
bounded presentation residual; the reusable reaction, burst, cue, and unlink
interfaces are known.

## Scope boundary

A11 is a substantiated, bounded-exhausted `partial`. A new Interpreter movie is useful
only for a named enemy family, the alternate collision subtype, exact rendered pose
timing, or post-KO respawn. Exhaustively throwing a seed at every authored enemy is
low-return campaign breadth and is not required before moving to another row.

