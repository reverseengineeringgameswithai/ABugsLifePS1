---
kind: system
id: SYS_dandelion_glide
name: Dandelion glide
status: live_confirmed_bounded
confidence: confirmed_core
source_state: original_game
functions:
  - FUNC_80048138
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-08-02_phase4_b03_dandelion_capsule
  - EXP_2026-08-02_phase4_b03_dandelion_interpreter_trace
  - EXP_2026-08-02_phase4_b03_bounded_exhaustion
src_paths:
  - src_re/dandelion_glide_static_8005c818.c
  - src_re/dandelion_glide_state_80048138.c
---

# SYS_dandelion_glide

## Original behavior

Brown seed tier 3 selects plant type `8`; the resident behavior table maps that
type to `0x8005C818`. The mature selected-slot arm detaches carried state through
`0x80046CAC`, writes vertical velocity `-4096`, player state `5`, grounded `0`,
air timer `0`, animation/action `3`, and requests positional sound `15`.

A separate quantized XYZ sphere of radius `40`, centered at plant Y `-0x7400`,
writes signed latch `11` to `0x800A659E`. Harvester flag `0x80` blocks that
write. Selected-slot mismatch, missing slot bit `0x02`, a failed sphere test,
or the harvester flag are native negative conditions.

## Glide law and timing

Player update consumes latch `11`. While airborne it writes:

```text
velocity_y = velocity_y < 350 ? velocity_y + 256 : 350
```

It bypasses ordinary state-5-to-6 gravity and rejoins horizontal input at
`0x80048D90`. The Interpreter fixture confirms nonzero and changing VX/VZ while
the latch is active. The plant walker runs after player update, so a newly
written latch is consumed on the next gameplay update. Native collision writes
grounded `0x0101`; the following player update clears the latch.

The retained fixture timeline is: latch write movie frame `239`, first consume
`241`, first terminal `350` at `261`, native grounded write `717`, clear `719`.
There are 212 latch-active player updates and the movie ends grounded, idle,
zero-velocity, with latch zero.

## Presentation ownership

`0x80051B84` reads latch `11`, requires player action-lockout `0`, and submits
an overhead effect at player Y `-22528` through `0x80051C30 -> 0x80022FE0`
(`effect_mesh_transform`). `actor_skinned_update` independently maps latch `11`
to player animation `18` at `0x800568D4`.

Screenshots show the canopy during glide, still visible more than two movie
frames after latch clear, and absent no later than eleven movie frames after
clear. Static ownership of submission and animation is confirmed; the remaining
display tail is attributed only as a bounded scheduling/buffering inference,
not exact GPU causality.

Contact-pool kind `13` contains dandelion artwork, but the validated earlier
capsule contains no live kind-13 record during its type-8 plant trigger. It is
not the demonstrated carrier for this glide.

## Lifecycle and intersections

The retained ASM contains 19 direct accesses to `0x800A659E`: 15 absolute and
four typed `$s1+0x9E` player-relative sites, totaling ten reads and nine writes.
The only direct writer values are `0`, `11`, and `12`; there is no direct
decrement or timer writer.

Direct latch retirement occurs on grounded player update (`0x80048700`), level
transition (`0x8004A87C`), harvester activation (`0x80051EA4`), and respawn
(`0x8005B314`). State `12` is a separate contact/propeller state. The propeller
handler uses state `11` to admit its inner vertical band and applies
`velocity_y -= 512`, clamped to `-3072`; it clears state `12`, not state `11`.

The direct census is complete for 892 retained hand-written ASM files. It does
not prove the absence of indirect player-pointer or overlay aliases.

## Future-MOD consumption contract

- Treat `0x800A659E` as shared signed interaction state, not a dandelion-private
  Boolean.
- Preserve values `11` and `12` and the grounded/transition/respawn clears.
- Preserve update ordering: player consumes the prior tick's latch before the
  plant walker can refresh it.
- Preserve harvester exclusion and carried-state detachment.
- Preserve the independent effect-submission and player-animation consumers.
- Do not treat the contact kind-13 sprite as the type-8 plant carrier without
  separate placement evidence.

## Bounded exhaustion

The row's high-yield mechanism work is exhausted, but Phase 4 status remains
`partial`. Deferred work is the repository-wide indirect alias proof,
exhaustive per-stage/alternate-instance reachability, exact GPU timing of the
short display tail, and a native dandelion-to-propeller combination replay.
Those items should be revisited only when shared pointer-typing infrastructure
or a concrete MOD dependency makes them material. No cold boot is required for
the completed analysis because no disc, code, or asset changed.

## Evidence

- `analysis/phase4_b03_dandelion_static.json`
- `analysis/phase4_b03_dandelion_runtime.json`
- `config/phase4_b03_dandelion.yaml`
- [[EXP_2026-08-02_phase4_b03_dandelion_interpreter_trace]]
- [[EXP_2026-08-02_phase4_b03_bounded_exhaustion]]
