---
kind: system
id: SYS_default_circle_input_absence
name: Default Circle input absence
status: confirmed
updated: 2026-07-14
confidence: confirmed
evidence:
  - EXP_2026-07-14_phase4_default_circle_absence
---

# Default Circle input absence

In the pristine PS1 game, raw Circle has no gameplay action under native controller
profile 0. This is a default-profile boundary, not a claim that Circle is globally
inert: native profile 1 maps Circle to the decoded Square action bit.

## Original-game facts

- Raw pad word `0x80082412` uses `0x2000` for Circle.
- Resident decoder `0x80051294..0x80051358` copies only raw low bits selected by
  `0x0FFF`, then compares three profile-table masks and synthesizes action bits
  `0x4000`, `0x8000`, and `0x1000` in `0x80082488`.
- The eight-entry table at `0x80078C28` is six bytes per profile. Profile 0 contains
  masks `0x4000/0x8000/0x1000`, so Circle matches none. Profile 1 contains
  `0x4000/0x2000/0x1000`, so Circle sets action `0x8000`.
- The main-shell writer at `0x8004FAF0` resets selector `0x8009EC7D` to zero. The
  resident selector readers are `0x800512A0` and `0x80055338`.

These statements come from hash-verified `SCUS_942.88` bytes, not ALLMODS. The exact
decoder words, decoder and table hashes, profile rows, and provenance are retained in
`analysis/phase4_circle_absence.json`; the reusable machine contract is
`config/phase4_input_actions.yaml`.

## Pristine runtime confirmation

An isolated DuckStation sweep reloaded every one of the 42 strict-pristine Phase-2
stage, completion, and progress anchors. For each anchor it compared timing-matched
neutral and Circle-held branches under profile 0. All 42 observed raw Circle, all 42
kept the same decoded action word, and all 42 had identical retained player/camera
blocks and typed outcome fields after release.

The instruction-attributed negative control wrote decoded action `0x0000` under
profile 0. The positive control changed only the valid native selector to profile 1
and wrote `0x8000` from instruction `0x80051318`. Neither access trace truncated.

## Boundary and reuse contract

Frontend remapping, selector persistence, and exceptional menu paths remain work for
the HUD/frontend campaign. They do not negate the profile-0 absence and are not
silently promoted to solved here. A future MOD assigning Circle must explicitly own
its action state, initialization/reset/retirement, readers and writers, capacity,
residency, and player/animation/camera/audio/collision consumers; it must not assume
Circle is unused under every native profile.

See [[EXP_2026-07-14_phase4_default_circle_absence]] and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
