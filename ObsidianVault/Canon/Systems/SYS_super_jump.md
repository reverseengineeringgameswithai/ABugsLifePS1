---
tags: [canon, player, powerup, super-jump, b09]
status: substantiated-partial
---

# Super jump

## Confirmed retail behavior

Blue x4 grants the super-jump state by setting bit `0x20` in the shared player flag halfword at `0x800A6590` (`player+0x90`). The grant plays sound 75.

The vertical update tests that bit at `0x80048184..0x80048190`. It selects the normal literal `-3072` or the super literal `-3776`; controlled runtime takeoff values are `-1344` and `-1696`, respectively, under shared `+256` gravity.

## Acquisition binding

```text
blue x4: type 7, extra 0x4000
constructor 0x27
contact action 0x0F
handler 0x800588D4
setter 0x800588F8: flags |= 0x20
```

An already-owned tier-4 plant tests `0x20` at `0x8005C77C` and substitutes constructor 59 rather than granting the power again.

## Companion behavior

`0x80055C74` uses the bit during upward mode-1 motion to enable a constructor-61 contact/effect spawn at Flik's position. Two level overlays also test the bit to suppress repeated sound-75 acquisition calls.

## Lifetime

Once obtained, super jump is permanent for the remainder of Flik's time in the current level. It ends when the level ends, Flik exits the stage, or a game over ends the level session. Ordinary jumping does not consume it. Checkpoint bookkeeping, all overlay writers, and the respawn-transition normalizer preserve it; the normalizer at `0x8005B330..0x8005B340` explicitly retains only `0x20` from the shared flag word.

The shared `player+0x7C` action-lockout code contains two structural overwrites: `0x8004867C` writes flag value `1`, and `0x800486BC` writes `0`. Their presence does not establish reachability after acquisition. They must not be cited as cancelling an obtained super jump. Exact reachability reconciliation and level-boundary reset attribution are pending the separate Item-2 tool owned by another agent.

## Evidence

- `analysis/phase4_b09_closure_20260804.json`
- `analysis/phase4_b09_super_jump_velocity.json`
- [[EXP_2026-08-04_phase4_b09_bounded_exhaustion]]
- Retained capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/B09_super_jump_comparison`

## Phase 4 B09 disposition (2026-08-04)

B09 is paused as **Substantiated Partial / bounded-exhausted for the current workstream**. Acquisition and in-level persistence are established. Exact attribution of the level-exit/game-over/stage-leave reset boundary remains delegated to the separate Item-2 tool effort and is not being duplicated here. This supersedes any local wording that called the row simply open or implied that ordinary action-lockout stores cancel an acquired Super Jump.
