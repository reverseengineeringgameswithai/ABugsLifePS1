---
kind: playbook
id: PLAYBOOK_game_solving_campaign_run_locomotion
name: Game Solving Campaign - Run Locomotion
status: complete
created: 2026-07-14
updated: 2026-07-14
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Run Locomotion

## Scope and decision

This completed child campaign covers Phase-1 row A01: ordinary pristine
horizontal locomotion from decoded D-pad/analog input through desired heading,
turning, signed local components, world velocity proposal, collision
consumption, run animation, and relevant lifecycle paths.

Jump, bounce, slide, swing, slow walk, Riverbed Flight, and E02 resolver
internals retain their own rows. They cannot dilute or inflate A01.

## Oracle, controls, and breadth

The original oracle is the pinned from-boot LEVEL01 movie. Control and in-memory
edited branches were identical before frame 8103; removing only Up through frame
8162 changed the forward component from 472 to 0.

The breadth oracle covers Training, stages 1–15, and bonuses 1–3. All 18
ordinary anchors moved relative to neutral and selected animation 0. Riverbed
Flight remained identical with animation 4. Controls cover all D-pad directions,
full/half/deadzone analog, acceleration/release/re-entry, turning, pause/resume,
and native same-scene death/respawn.

## Frontier, state, and lifecycle

- Input helper: `0x80047EBC..0x80048137`, direction mask `0x00F0`, analog
  deadzone 6144, cap 16384.
- Horizontal controller: `0x800490B0..0x80049543`; heading/input heading at
  player `+0x20/+0x28`; signed forward/lateral components at `+0x38/+0x3C`;
  world velocity at `+0x2C/+0x34`.
- Collision interface: `0x8003633C`, resolved X/Z commits
  `0x80036CE8/0x80036CF0`. Velocity remains a proposal.
- Animation consumer: resident actor path, ordinary animation 0.

No A01-private pool, callback, overlay field, capacity, or serialized state
exists. One resident player block is reused. Release decays components to zero;
pause freezes them; resume and native respawn re-read current input; scene load
reinitializes world fields while resident owners persist.

The helper/player bodies are byte-matched handwritten ASM build units.
`src_re/player_update_80048138.c` is documentation-grade and omits the horizontal
body. `config/phase4_run_locomotion.yaml` is the reusable typed contract.

## Bounded residuals

- Action-specific vertical/special motion remains with A03/A05/A06/A16/F14.
- E02 owns resolver geometry, walls, ledges, and penetration internals. A01
  proves only that velocity proposals are consumed and may be adjusted.

Neither boundary intersects the completed ordinary horizontal controller.
Evidence and failed hypotheses: [[EXP_2026-07-14_phase4_run_locomotion]].
Original-game facts: [[SYS_run_locomotion_controller]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
