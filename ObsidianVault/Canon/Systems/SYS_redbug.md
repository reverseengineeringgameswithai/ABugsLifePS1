---
type: canon
status: substantiated-partial-bounded
system: Redbug / manual cockroach
phase4_row: D09
updated: 2026-08-04
---

# Redbug (`id=19`)

The manual's cockroach is the resident actor named Redbug, actor ID 19. A
campaign-wide disc census found six placements, all in scene 5 / `LEVEL05`, all
using the same type-word/program variant. Program-table entry 12 selects the
pure wander loop at `0x80077690`.

## Combat and chase

- The retained D09 fixture starts at HP 6 and records two accepted `-2` hits,
  ending at HP 2. It does not contain the terminal hit.
- Redbug carries actor flag `0x40` throughout the retained fixture. The shared
  projectile handler treats that as the berry-tough class: the red connecting
  form takes the reaction-only branch; admitted blue/homing/gold/mega classes
  use the shared damage tail.
- An eligible landed hit sets actor flag `0x02` at `0x8005914C`.
- The shared motion phase reads only bit `0x02` at `0x8004C930`. While the actor
  is in a parked mode below 3 and inside its chase radius, its goal is replaced
  with Flik's position. The observed motion is an approach/retreat stand-off,
  not a contact charge.
- Bit `0x1000` is not present in Redbug's mover bytecode and is not read by the
  chase gate. Treating it as the persistent pursuit latch was unsupported; its
  exact shared-state label is not required to explain Redbug pursuit.

## Defeat and return

The ordinary temporary-KO lane writes HP 999, adds flags `0x0880`, clears chase
bit `0x02`, redirects the mover VM to the shared stop loop, and calls
`0x800498AC(actor,1)`. It bypasses the permanent effect/quota block, explaining
why the gold-defeat quota does not move on the recorded ordinary damage lane.

After the independent actor `+0x62` delay expires, the shared scheduler calls
`0x80049C30` once the fixed spawn is off-screen (or flag `0x10` bypasses that
visibility predicate). The actor is rebuilt from its spawn template. This is
why waiting beside a defeated Redbug does not reproduce its return, whereas
walking far enough away does.

## Evidence and boundary

- [[EXP_2026-08-04_phase4_d09_bounded_exhaustion]]
- `analysis/phase4_d09_static_closure.json`
- `analysis/phase4_d09_capsule_closure.json`
- `tools/phase4_d09_static.c`
- `tools/phase4_d09_capsule.c`
- `src_re/redbug_actor_id19.c`

D09 is substantiated partial and bounded-exhausted. Replaying all six
data-identical placements, naming the exact animation/audio assets, and assigning
a decorative semantic name to generic flag `0x1000` are low-return breadth. The
retained movie is old CachedInterpreter evidence and remains poll/capsule-only;
do not arm live CPU instrumentation against it.
