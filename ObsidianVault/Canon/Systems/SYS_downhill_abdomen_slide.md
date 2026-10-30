# Downhill abdomen slide

## Scope

This note binds Phase 4 row `A06_downhill_slide` to the pristine resident player update. It distinguishes the ordinary held-Cross slide from a separate `player+0x8C` contact-projector fast path.

## Confirmed state and fields

- Player base: `0x800A6500`.
- Position and motion fields are updated in the resident player slice; horizontal/vertical motion includes `+0x2C`, `+0x30`, and `+0x34`.
- Current and target heading: `+0x20` and `+0x28`.
- Projected motion used by slide maintenance: `+0x38` and `+0x3C`.
- Slide-maintenance timer: `+0x7A`; action state: `+0x80`; grounded flag: `+0x82`; dive phase: `+0x84`.
- Desired animation selector: `+0x88`; latched selector: `+0x8A`.
- `+0x8C` can hold a terrain/contact slot index plus one. Zero is the no-slot value, but ordinary A06 sliding does not require this field to become nonzero.

## Admission

The ordinary dive sequence does not contain a slope-angle predicate. State `2` tests vertical floor/position separation before entering state `4`. With Cross held, eligible state `4` or later reaches the grounded check at `0x80048CD8`; grounded processing commits state `5` at `0x80048D64`.

Observed ordinary sequence in both v4 fixtures is `0 -> 1 -> 2 -> 4 -> 5`, with a transient recovery write during landing before stable state `5`.

## Held-input latch and release

`0x80048B5C..0x80048B6C` tests current Cross state.

- Cross held plus grounded state `4` or later writes state `5` at `0x80048D64`.
- Cross released routes to `0x80048D00`; when grounded, `0x80048D10` clears the action state to `0`.
- Ordinary state `5` is not advanced to `6` merely because `player+0x8C` is zero.
- If ungrounded, this block does not perform the grounded release clear; airborne release remains a named edge case rather than part of the confirmed grounded rule.

The two Interpreter fixtures independently show first release followed by state `0` one movie frame later. The long-hold fixture keeps the coarse state `5` through terrain-driven get-up because Cross remains held, then clears it after the later release.

State `5` is not, by itself, proof that Flik remains visibly sliding.

## Terrain-driven slide termination

The ordinary route maintains visible sliding with timer and projected-motion fields:

- `+0x7A` is normally rearmed to `12` while Cross is held and either `+0x38 >= 0x300` or `abs(+0x3C) >= 0x300`.
- The check occurs after timer decrement reaches `11`. If both values are below threshold, `0x80048F3C` is skipped and the timer continues toward zero.
- Desired animation `+0x88` is `0x1C` at timer `12`, recovery `0x06` while the timer remains positive below `12`, and the ordinary fallback when it reaches zero.
- `0x800569AC` copies the desired selector into latched selector `+0x8A` and resets animation progress on changes.

In the long-hold fixture, prior values `+0x38 = 0x2FE` and `+0x3C = 0` cause the rearm miss at movie frame `543`. Selector `0x1C -> 0x06` begins get-up while Cross remains held; the timer reaches zero and selector `0x06 -> 0x00` at frame `565`. Flik is upright by playback frame `568`. Cross is not released until frame `596`.

Terrain therefore can end the visible slide without Cross release. The later release clears the separate coarse action latch.

## Ordinary steering

The ordinary route uses the shared resident heading system:

- `0x80047EBC` writes a camera/analog-derived target heading to `player+0x28`.
- Digital left/right subtract or add `0x20` from the target at `0x800490D0` and `0x80049100`, followed by 12-bit wrapping.
- `0x80049240..0x800492A8` moves current heading `+0x20` toward target `+0x28` using wrapped error, a cap, and a state-selected right shift.
- The default ordinary parameters are cap `0x400` and shift `2`, yielding a default maximum correction of `0x100` per update. Other resident states can select different parameters.

The steering fixture holds left for 68 frames and right for 59 frames during stable state `5`, with both target and current heading changing. Exact trajectories still depend on shared movement integration and collision data; no universal slope-only friction recurrence exists.

## Separate contact-projector fast path

`0x80041AC4` can publish a contact slot at `player+0x8C`. When nonzero, `0x800488D8..0x80048A70` enters a separate state-5 surface-projector path with its own `0x80` heading cap and new-Cross jump branch.

This path is real but is not the ordinary slide observed in A06. Both A06 movies recorded zero `+0x8C` writes, and the steering replay produced zero execution hits at its entry, steering, projector, and new-Cross exit PCs while the slide was visibly active.

## Offensive contact class

The slide shares the established phase-0 abdomen contact resolver for offensive actor contact. That resolver applies actor event `4` plus knockback/drop reaction without a direct actor-HP write in the resolver, then applies player rebound handling. It is not the kick action's generic direct-damage path.

## Evidence and limits

- Static guard: `tools/phase4_a06_static.c`.
- Reconstruction: `src_re/downhill_slide_80048138.c`.
- Structured result: `analysis/phase4_a06_downhill_slide.json`.
- Runtime experiment: [[EXP_2026-08-03_phase4_a06_downhill_slide]].
- Steering movie SHA-256: `0d96c41768ad190e902312cdc78e8b88705ae8d83c78c56ddaf6809060d0ff4b`.
- Long-hold movie SHA-256: `2e51e56ec40089c5137f29e021be03edd119299d56569edd8afc36d16867717a`.

The row is `substantiated` and `bounded_exhausted`. Terrain termination, recovery timing, and the later release-latch clear are all confirmed. Named obstacle or airborne-release behavior can be studied later, but exhaustive surface enumeration is not required for Phase 4 closure.
