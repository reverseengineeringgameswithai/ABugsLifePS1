---
kind: system
id: SYS_player_action_state_laws
name: Player action and state laws (state word, kick, slide, handstand, swing)
status: live_confirmed
confidence: confirmed
source_state: original_game
memory:
  - MEM_800A6500
evidence:
  - EXP_2026-07-12_phase2_behavioral_oracle
  - analysis/phase2_action_behavior.json
  - analysis/phase2_buttslide_oracle.json
  - analysis/phase2_seed_action_controls.json
src_paths:
  - tools/phase2_action_behavior.py
  - tools/phase2_seed_action_controls.py
---

# SYS_player_action_state_laws

Every law here has a **behavioural positive/negative pair** on pristine media —
an input that produces the effect and a control that does not. Derived during the
Phase-2 oracle build ([[Phase 2 - Build the Pristine Whole-Game Behavioral Oracle]]).

## The state word — `0x800A6580` (u16)

This is the real player state selector. Observed domain:

| Value | Meaning |
|---|---|
| 0 | grounded / idle |
| 1 | airborne |
| 2 | swing-release launch |
| **3** | **exit from the handstand dismount** — added 2026-08-04, see below |
| 4 | slam / dive — **double-tap exclusive** (a single jump never reaches it) |
| 5 | shared: landing/skid **and** swing-attached |
| 6 | handstand dismount |

### State 3 — the domain was incomplete (added 2026-08-04)

This table previously listed six values and omitted **3**. It occurs: a full traced run of scene 12
(`F11_the_tree`) took **`{0,1,2,3,4,5,6}`** across 2,997 writes to the state word.

**Among 19 statically resolved direct writers, 3 has one producer:
`0x80048CFC`, reached only when the current state is 6:**

```
0x80048CE0  bne  v0,zero,0x80048D64   ; v0 != 0 -> state := 6 (the dismount hop)
0x80048CE8  lh   v1,0x80(s1)          ; current state
0x80048CF0  bne  v1,6,0x80048D68      ; not in state 6 -> skip
0x80048CF4  v0 = 3
0x80048CFC  sh   v0,0x80(s1)          ; state := 3
```

So 3 and 6 are a pair on the same predicate: while it holds the state is **6**, and when it stops
holding, state 6 becomes **3**. Read 3 as *the exit from the dismount*, not as an independent action.

Naming it more precisely than that belongs to [[#Handstand|A10 handstand]], which owns the handstand and already
binds "dismount hop = state word == 6".

**Correction history.** An earlier revision called the ten entries below the
"Complete writer map." That was wrong: they are complete only within
`player_vertical_update`. A general `census_address.py` pass resolves nine additional
direct writers elsewhere in the resident executable.

Resolved writers inside `player_vertical_update`:

| PC | state written |
|---|---|
| `0x800486B4`, `0x80048930` | 5 |
| `0x80048A50`, `0x80048BDC`, `0x80048E0C` | 1 |
| `0x80048CBC` | 4 |
| **`0x80048CFC`** | **3** |
| `0x80048D10` | 0 |
| `0x80048D50` | 2 |
| `0x80048D64` | 6 |

Additional statically resolved direct writers:

| PC | state written |
|---|---|
| `0x8004A84C`, `0x8004AFA4`, `0x8004B044`, `0x8004B340` | 5 |
| `0x8005B270` | 0 |
| `0x8005C404`, `0x8005C608`, `0x8005C854`, `0x8005D0B4` | 5 |

This is a resolved-direct map, not an absolute writer closure. The general census
still reports 12,956 unresolved-base accesses (424 same-width sites in related
functions) and 149 unresolved indirect calls. It supports "sole value-3 producer
among resolved direct writers," not "the only possible producer."

⚠️ **Two invalid discriminators — do not reuse.** `0x800A6542/46` is an
*animation frame counter* pair (it cycles 0..8 while idle; walk = (6,7), slide =
(11,12)) — it is **not** a state id. And a live actor's chunk-31 record mutates on
its own, so record deltas alone prove nothing.

Companion fields: grounded `0x800A6582` (0 while airborne/mounted/attached),
floor Y `0x800A6548`, prev-tick position mirror `0x800A6510`.

## Kick — branch `0x80048F4C`, timer `0x800A657A`

The kick fires at `0x80048F4C`, which writes **−16** into the kick timer
`0x800A657A`. Every gate must hold:

1. pad `0x80082488` & `0x0300` — **L2 or R2 held**, and
2. pad `0x80082488` & `0x8000` — **Square**, and
3. prev-pad `0x80082380` shows Square is a **fresh press** (an *edge*), and
4. `player+0x7A >= 0` (not already kicking), and
5. grounded: `|Y − floorY| < 1024`, and
6. `player+0x5C == 0`.

⚠️ **Input-injection gotcha (this cost a whole review round).**
`setControllerState` *holds* a button — a held button never produces a press
**edge**, so edge-gated actions never fire and look like they "don't exist". Hold
the modifier first, **then** press. An earlier "the kick doesn't exist" disproof
was entirely this bug. (Related fact: **berries are infinite** — there is no ammo
gating anywhere.)

## Buttslide / slam — `0` → `1` (air) → `4` (slam) → `5` (ground slide)

Double-tap X produces the full chain; a single jump reaches `1` but **never** `4`.
Slide animation pair `0x800A6542/46` = (11,12).

## Handstand

Mounted on a seed: position frozen for >100 frames with grounded
`0x800A6582 == 0`. Dismount sets state `0x800A6580 == 6`. Negative control:
standing *beside* the seed with no Square keeps grounded == 1.

## Swinging (vines / webs)

- **Grab** = hold **toward** the vine (direction) **+ Cross** → sustained state
  `5` with grounded `0`, and a pendulum oscillation in Y. Cross alone, or no
  input, never attaches. (An earlier grab attempt failed purely because it did
  not hold *toward* the vine.)
- **Release** = Cross while attached → leaves state 5 (through launch state 2)
  and lands grounded. The idle control keeps swinging indefinitely.

## Camera and status

The camera struct `0x80095358` provably moves under L1 and is static under no
input; R1 differs from move-only. Select opens a panel that is a distinct
frame-hash from the identical no-Select window.

## Bounded negative — spin remains an external lead

The earlier absolute “there is no spin move” claim is superseded. The retained
procedure did not reproduce its own six-cluster inventory: the implemented
pristine-EXE scan finds four direct clusters of ANDI direction-mask tests. None
is itself evidence of a spin recognizer, but that only rules out this narrow
implementation family. It cannot exclude table-driven, analog, overlay, or
differently encoded recognition. `analysis/phase2_spin_disproof.json` is now
generated by `tools/phase2_spin_disproof.py`; registry row A07 is an explicit
external lead pending an exact input sequence and pristine runtime test.

## A03 Cross hold/release refinement (2026-08-03)

State 1 is specifically the Cross-held jump phase; crossing the apex does not by
itself leave state 1. Releasing Cross changes state 1 to state 2 and cuts the
remaining upward velocity through the signed half-velocity path. Landing is
published by the collision integrator as grounded 0x0101, requests animation 5,
then returns through state 0 to idle animation 22.

The normal height curve is not strictly monotonic at its final sample: release
at held tick 11 reaches 17024 units, while holding through tick 12 reaches
16896. See [[EXP_2026-08-03_phase4_a03_jump]].

## A03 ceiling-contact law (confirmed 2026-08-03)

For a held jump, the normal full-height recurrence remains 16,896 position units after its entry displacement. When the upward segment crosses an accepted dominant-positive-Y terrain plane and the polygon test retains that plane, the collision response truncates ascent. The natural Anthill control/case measured 16,896 versus 10,880, followed by descent and landing. The retained ceiling was plane 0x800f1d04, sector 166, normal [-777, 16363, -288], with d_start=219 and d_end=-1827. See analysis/phase4_a03_ceiling_movie_v2.json.
