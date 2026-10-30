---
title: Kick action
category: player-action
status: confirmed-bounded
game: pristine-retail
updated: 2026-08-03
---

# Kick action

## Confirmed original-game behavior

The kick has two distinct stages that must not be conflated. Immediate player-body
contact changes actor reaction state without writing enemy HP. Several updates later,
ctor109 supplies contact action class 1 to the generic enemy hit tail, where an eligible
target receives `HP - 99`. That is an effective instant kill for ordinary enemies below
100 HP, but it is not an unconditional kill across special actors.

## Admission and recovery

`0x80048F4C..0x80048FB4` admits a kick when all of these are true:

- L2 or R2 is held in current pad word `0x80082488` (`& 0x0300`).
- Square is down now and was up in previous pad word `0x80082380` (`& 0x8000`).
- Signed action timer player `+0x7A` is nonnegative.
- The player is grounded within the native 1024-unit test.
- Player field `+0x5C` is zero.

Admission stores `-16` to the signed action timer. The update at
`0x80048EA4..0x80048ED4` moves either sign one unit toward zero, so the native
duration invariant is 16 gameplay updates. It should not be relabeled as a fixed
number of video frames without scene-specific cadence evidence.

## Animation and effects

`FUNC_800563D4_actor_skinned_update` maps a negative action timer to animation 1.
At the initial `-16`, it also clears the animation-frame accumulator at
`0x800A6514`.

`FUNC_80055654` emits the visible/contact effect objects only while animation 1
has timer `-7..-2`. Constructor 109 is emitted on all six updates; constructor
108 is additionally emitted at `-7`. Their metadata maps to action IDs 1 and 0,
respectively. Their default contact-walker retirement shows they are effect/contact
objects, not HP-damage projectiles.

## Actor contact geometry

Kick contact is a branch of `FUNC_8004ABF4_proximity_updater`; it does not own a
separate long-range hitbox. The shared body-contact path applies:

- Actor collision center from actor position plus signed offsets `+0x64/+0x66/+0x68`.
- Player collision center with Y bias `-7360`.
- Broad radius from signed actor `+0x6A + 250`, after coordinate scaling by 32.
- The actor's state-indexed, rotated/model-specific ellipsoid descriptor.
- A forward-half-plane check, approximately `+/-1024` in the 12-bit angle domain.
- A negative kick timer and player animation other than 11, 12, or 30.

## Reaction classes

A successful kick branch at `0x8004B450` sets actor flag `0x1000` and bypasses
the normal player-damage call at `0x8004B4A0`.

For an ordinary target, the branch stores 30 to actor knockback field `+0x6C`,
may set chase flag `0x2`, and stores player impact animation 30. Actor flag
`0x80` is not kick immunity: it selects a reduced reaction that stores 15 to
actor `+0x6C` and skips the full knockback/player-impact stores.

Actor HP is signed halfword `+0x6E`. The immediate body-contact reaction does not
write it. The lookup rooted at `0x80089938` affects the optional chase flag in that
body-reaction path, not the later contact-object damage rules.

## Kick damage and instant-kill rule

The ctor109 effect emitted during timer `-7..-2` maps to contact action class 1.
`FUNC_80058AF8` applies these gates and effects:

- Actor flags `0x20` or `0x80` reject contact-object processing at `0x80058B54`.
- A negative actor knockback field also rejects processing at `0x80058B68`.
- Accepted effect geometry writes knockback 20 at `0x80058ED8`.
- Actor flag `0x40` plus kick action class 1 selects the special branch through `0x80058EE8..0x80058F10`, bypassing HP dispatch.
- Without that special branch, action class 1 selects `HP - 99` at `0x80059094` and stores it at `0x800590E4`.
- A lethal result reaches the native death tail, which writes 999 at `0x800592A8` before later lifecycle handling.

Therefore "kick instant-kills" is a useful ordinary-enemy description, not the exact
native law. The native law is a 99-HP attack after eligibility and special-reaction
gates.

## Worm exception

Movie `A04_kick_worm_contanct.movie.json` targets worm actor ID 40 at
`0x800A0C74`. Six Square presses produced four admitted kicks and three confirmed
effect contacts. Each natural contact wrote knockback 20, reached the flag-`0x40`
special branch with action class 1, and left HP at 8. Flag `0x80` was dynamic and
caused some earlier prefilter rejections; persistent `0x40` was decisive on the
contacts that reached the late branch.

A runtime-only control changed only the mask instruction at `0x80058EE4` from
`andi v0,v0,0x40` to an `andi` mask of zero. The next synchronized contact reached
the HP dispatcher with HP 8 and stored `-91` (`8 - 99`), followed by the death tail.
The pinned save restored the original instruction before the isolated instance was
stopped. This causally confirms the worm's flag-`0x40` kick immunity.

## Evidence boundary

The v4 Interpreter movie `A04_kick_contact.movie.json` naturally executes the
kick but narrowly misses actor 39's broad sphere. That is preserved as negative
evidence. A paused X-only causal control, preserving Y/Z/facing/animation and the
enemy record, crosses the collision boundary and confirms the ordinary reaction.
A second control changing only target flag `0x80` confirms the reduced branch.

The bounded mechanic is sufficiently resolved to move on after this correction.
Remaining work is a campaign-wide census of species using flags `0x20`, `0x40`, or
`0x80`, rare targets with at least 100 HP, semantic naming of `0x80089938`, and
optional cadence breadth. These are campaign breadth, not unknown kick laws.

## Durable evidence

- [[EXP_2026-08-03_phase4_a04_kick]]
- `analysis/phase4_a04_kick.json`
- `analysis/phase4_a04_kick_worm.json`
- `src_re/kick_action_80048e9c_and_contact.c`
- `analysis/mechanics_baseline.yaml` row `A04_kick`
