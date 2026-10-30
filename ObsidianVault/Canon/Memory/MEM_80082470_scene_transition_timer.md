---
kind: memory
id: MEM_80082470
aliases:
  - MEM_80082470
  - "0x80082470"
  - scene_transition_timer
address: '0x80082470'
width: 2
name: scene_transition_timer
status: confirmed
confidence: confirmed
source_state: original_game
system:
  - Gameplay_-_Warp_and_Level_Transition
evidence:
  - EXP_2026-08-05_phase4_f01_objective_lifecycle
  - analysis/phase4_f01_objective_lifecycle.json
  - analysis/phase4_f01_runtime_lifecycle.json
patch_policy: callable
---

# MEM_80082470 — scene transition countdown timer

`s16` at `0x80082470` (`$gp + 0x6D8`). The deadline for
[[MEM_800823A0_scene_transition_request]]: the consumer at `0x8004FEEC` acts only
once the request is nonzero **and** this timer has reached 0.

## Decrement

Single decrementer at `0x800553F8`. Nominal cadence is **one decrement per 2
emulator frames** — the 30 Hz logic tick, not the 60 Hz frame. It is nominal, not
strict: the tick can slip a frame under load.

| run | decrements | frame-gap histogram |
|---|---:|---|
| LEVEL01 completion | 68 | `{2: 66, 1162: 1}` |
| LEVEL01 death + respawn | 105 | `{2: 95, 3: 9}` |

(The 1162-frame gap is the idle interval between one countdown expiring and the
next starting; the nine 3-frame gaps are slipped ticks during the death and
respawn sequence.)

## Initial values

30 writers across the resident image and the shipped overlays. Resident:

| value | writers |
|---:|---|
| 0 | `0x8005B890` |
| 23 | `0x80049704` (region codes 2 and 3), `0x8004AA00`, `0x8004F230`, `0x8004F298`, `0x8004F2FC`, `0x8004F6CC`, `0x8004F9FC` |
| 30 | `0x8004B3CC`, `0x800591E8` |
| 45 | `0x8004FE4C` (scene entry) |
| 60 | `0x8004A8C0` (death), `0x8005C6CC` |

Per-level overlays supply their own durations: 150, 400, 101, 20000, 300, 60, 30,
120, 70, 90 — see `analysis/phase4_f01_objective_lifecycle.json`.

⚠️ The store at `0x80049704` is reached from two predecessors (the code-2 and
code-3 arms). Both load `23` (`0x800496DC` and `0x800496FC` are both
`addiu v0, zero, 0x17`), so the merged value is `23` on either path; the static
census flags this site as join-crossed rather than reporting a linear constant.
