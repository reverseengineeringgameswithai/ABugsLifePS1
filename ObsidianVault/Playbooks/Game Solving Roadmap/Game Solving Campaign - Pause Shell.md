---
kind: playbook
id: PLAYBOOK_game_solving_campaign_pause_shell
name: Game Solving Campaign - Pause Shell
status: complete
created: 2026-07-18
updated: 2026-07-18
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Pause Shell

## Scope and decision

This completed child campaign covers Phase-1 row A18: pristine Start entry,
ordinary resume, gameplay-versus-presentation ownership, the pause-facing SPU
boundary, all gameplay contexts, Exit Level confirmation and frontend handoff.

E12 audio internals, E13 HUD/results, E14 persistence and E16 loading/overlays
remain separate rows. Their pause-facing boundaries are measured without
promoting their independent implementations into A18.

## Oracle, controls, and breadth

The oracle is hash-verified pristine retail media plus centrally declared
strict-pristine save anchors. All nineteen gameplay contexts enter and resume
pause in the same scene. The focused Tunnels control compares held Up while
active, paused and resumed. The audio-rich Riverbed Flight control compares
voice phases before, during and after pause.

Positive controls are Start entry/resume and Exit Level -> selected Yes.
Negative controls are active motion, paused held input, default No
confirmation, and zero player/HUD-update execution during pause.

## Frontier and lifecycle

- State owner: `0x8004ECD4..0x8004F477`.
- Presentation/menu owner: `0x8004F480..0x8004FA3F`.
- State: u16 action `0x80082488`, u16 flag `0x8008224E`.
- Entry/resume: `0x8004F3AC`, `0x8004F858`.
- Confirmed exit: `0x8004F9C0`, `0x8004F9E4`, `0x8004F9FC`.

Pause freezes player semantics and actor/contact/plant/camera owners while the
scene renderer, ordering table, GPU DMA and frame presentation continue. Audio
sustain voices release and restart across resume. Confirmed exit clears pause,
publishes transition 5/fade 23 and reaches frontend scene 0.

## Bounded residuals

- E12 owns general audio selection, mixing, voices and per-level music.
- E13/E14/E16 own HUD/results, persistence and loader/overlay internals.

These residuals do not intersect the reproduced A18 shell. Machine contract:
`config/phase4_pause.yaml`. Retained evidence:
`analysis/phase4_pause.json`. Original-game facts: [[SYS_pause_shell]].
Procedure and failed instrumentation:
[[EXP_2026-07-18_phase4_pause_shell]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
