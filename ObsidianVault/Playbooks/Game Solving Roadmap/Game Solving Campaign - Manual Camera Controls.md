---
kind: playbook
id: PLAYBOOK_game_solving_campaign_manual_camera_controls
name: Game Solving Campaign - Manual Camera Controls
status: complete
created: 2026-07-15
updated: 2026-07-15
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Manual Camera Controls

## Scope and decision

This completed child campaign covers Phase-1 row A17: pristine L1 reset/look,
R1 lock, simultaneous precedence, L1 directional variants, typed state,
HUD readers, all gameplay contexts, pause/release/respawn reset, and cold boot.

E04 camera collision/rendering and F14 flight-camera internals retain separate
rows. Their A17-facing exceptional behavior is bounded without promoting their
implementation into the manual selector.

## Oracle, controls, and breadth

The from-boot LEVEL01 movie has two one-button branches over frames
8103..8162. At the frozen pre-edit checkpoint, unedited/L1/R1 camera bytes and
cycles match. L1 ends in mode 2 and R1 in mode 3 with distinct output.

From the same strict-pristine save, neutral remains mode 0 and static. L1/R1
select 2/3; L1+R1 selects 2. L1+Up/Down select vertical 32768/4096, Down drives
orbit bias toward 12288, and Left/Right produce signed +16/-16 pitch steps.
Release restores 0/900/12288/0 and drains the high-byte timer.

All 19 gameplay anchors are classified: 17 standard 2/3 contexts, Bug Bar
L1-only 2/0, and Riverbed Flight manual-disabled 0/0. Bonus 2 selects R1 mode 3
without a timing-matched 16-frame output divergence.

## Frontier, state, and lifecycle

- Owner/reset/HUD: `0x8004DF18`, `0x8004DC0C`, `0x800526FC`.
- Selector: s32 `0x80082220`, domain 0/2/3; L1 has precedence.
- Camera: one `0x60`-byte record at `0x80095358`; position/target are derived.
- Globals: orbit bias `0x80082280:s32`, vertical target `0x80082460:s32`,
  neutral step `0x800822A8:s32`, pitch step `0x80082474:s16`.

Pause freezes camera and blocks held L1 until resume. Native same-scene respawn
resets armed mode 2/distance 612 to mode 0/distance 900, then permits L1
re-entry. All state is transient runtime state.

## Bounded residuals

- E04 owns collision geometry, derived-output consumption and render ordering.
- F14 owns the Riverbed Flight alternate camera implementation.

Neither intersects the completed A17 selector and applicability law. Machine
contract: `config/phase4_camera_controls.yaml`. Retained evidence:
`analysis/phase4_camera_controls.json`. Original-game facts:
[[SYS_manual_camera_controls]]. Procedure and failed hypotheses:
[[EXP_2026-07-15_phase4_manual_camera_controls]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
