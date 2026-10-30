---
node_type: experiment
title: "EXP — A07 spin / secret directional move bounded negative"
date: 2026-07-13
status: partial
result: bounded_negative
phase: 3
mechanic: A07_spin
tags: [phase3, bounded-negative, player-state, input]
---

# A07 "spin / secret directional move" — bounded negative

**Verdict: PARTIAL / EXTERNAL LEAD.** The static scan and runtime battery establish a
useful bounded negative, but they do **not** disprove the move. They observed no
distinct spin state or unknown writer routine; a kick-shaped branch inside a named
function, or a context outside the tested battery, remains possible.

## What A07 claims
A *special move* (a "spinning attack"-style secret move) triggered by a
rotational/directional input — a distinct, usable action, **not** the character
merely turning to face a direction. A distinct mode in `0x800A6580` would be one
implementation, but it is not required: the confirmed kick is a branch inside
`player_vertical_update` that writes timer `0x800A657A` without a distinct mode.
The experiment therefore watches the whole player block and treats its result as
coverage, not proof of non-existence.

## Method (bounded structural coverage via a write-watch)
The earlier "does rotation reach a state ordinary play can't" framing is too brittle
— the ordinary baseline is incomplete, and the player modes 5/6 (slide/handstand)
are rare 2-frame transients that a coarse battery never triggers, false-flagging as
"novel." The bounded structural probe is:

- Pristine media, `level01.sav` (scene 1), isolated instance.
- A **write-watch** (`accessLog`) on `0x800A6580` runs over an **exhaustive input
  battery** (193 trials): every single button; documented combos; **TRUE 8-way
  d-pad rotations** (simultaneous held diagonals via the RPC `buttons` array — a real
  analog-style rotation of the digital pad), both handedness, four speeds, {2,4}
  turns, from idle/air/moving, bare and with each action button held-during and
  tapped-trailing, plus long 16-turn continuous. The watch is re-armed after every
  `loadState` (it clears watches) and drained per-trial so no rare transient is
  truncated away.
- Record **every value** the state word takes and **every PC** that writes it.

## Result (`analysis/phase3_spin_functional.json`)
- **No undocumented value.** The state word only ever took documented player-mode
  values; nothing outside the known vocabulary `{0,1,2,4,5,6}`. No distinct spin
  **state was observed** under this battery.
- **A single mode-word owner.** Every mode-word writer PC resolves to
  `player_vertical_update` (`FUNC_80048138`, 0x80048138–0x800498AC). Block-wide writes
  resolved only to named player/movement/collision functions. No unknown writer routine
  was observed.
- The rare transient modes 5/6 (slide/handstand) seen while sampling are written by
  that **same** movement FSM — they are ordinary modes, not a spin move.

These observations do not close the lead. "Every observed writer is named" does not
exclude a spin-shaped branch inside one of those functions; the kick demonstrates
that exact architecture. The result only bounds what the tested inputs exposed.

## Evidence (committed, pinned)
- Runtime: `analysis/phase3_spin_functional.json` (save sha256-pinned).
- Static: `analysis/phase2_spin_disproof.json` (no directional-mask recognizer).
- Guard: `tests/test_phase3_spin_disproof.py` (the artifact must remain a bounded
  negative, record complete access-log accounting, and keep `A07_spin` as
  `external_lead`).

## Next evidence
Obtain the external source's exact input sequence, starting context, and expected
effect. Replay it on hash-verified pristine media with per-frame input/state capture;
if it reproduces, trace the responsible branch inside the named input/player
functions. Until then, preserve both existence and absence as unproven.

Canon result: [[SYS_a07_spin_external_lead]].

Related: [[MEM_800A6500]] · [[FUNC_80048138]]
