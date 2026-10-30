---
kind: playbook
id: PLAYBOOK_game_solving_campaign_berry_throw
name: Game Solving Campaign - Berry Throw
status: complete
created: 2026-07-15
updated: 2026-07-15
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Berry Throw

## Scope and decision

This completed child campaign covers Phase-1 row A08: pristine ordinary
fresh-Square admission, windup/dispatch, all five equipped selectors, aim split,
spawn ABI/SFX, descriptor and contact-pool ownership, straight integration,
homing/mega primary-secondary acquisition, pause, retirement, ordinary gameplay
breadth, and same-scene respawn.

D04 and enemy-family damage/immunity/death/permanence, E05 render and asset
decoding, shooter-object projectiles, plant grants, boss/stage-special outcomes,
and MOD-private Blackberry/Fastberry behavior retain separate rows and owners.

## Oracle, controls, and breadth

Pinned pristine bytes bind a fresh Square edge to windup 18 and dispatch at 10.
Exact stable boundaries admit in-flight 3 and gate `+0x9E` 11, but reject 4 and
12. Nonzero special mode, shared timer, and vertical aux reject. Clearing a
blocker while Square remains held does not queue a throw; release/repress does.

Selector-only controls produce primary types 2/5/8/11/45. Red, blue, and gold
enter the ordinary aim helper; homing and mega skip it and use heading with VY
-2048. The timing-matched from-boot branch adds only Square, matches player
fields/block/cycle/frame before the edit, arms at frame 8563, and spawns red type
2 with SFX 2 at 8607. Control spawns nothing.

Nineteen strict-pristine anchors cover Training, stages 1–15, and three bonuses.
Eighteen spawn, including Riverbed Flight. Bonus 2 Mushrooms is the sampled
negative and remains bounded to its observed context.

## Frontier, state, capacity, and lifecycle

- Player owner: resident gate `0x80048FB8..0x8004909C`; windup s16 `+0x86`,
  in-flight u8 `+0x96`, selector u8 `+0x97`, shared context gates, and animation.
- Dispatch owner: resident `0x800470AC..0x80047284`; selector read at interior
  site `0x80047170`, aim helper `0x80046D24`, and native type jump table.
- Pool owner: allocator `0x8005A0E0`, 64 records × `0x38` at `0x800B0D18`,
  cursor `0x8008234C`, descriptor table `0x8007941C`.
- Update owner: resident `0x8005A308..0x8005B12C`; position/velocity/gravity,
  TTL, type, flags, target, render fields, and cleanup handoffs.

The allocator performs a round-robin free-slot search and has no full-pool
escape. Position consumes current velocity, then VY adds 128 and TTL decrements.
Types 8/45 acquire with modes 1/0 and allocate distinct secondaries 16/48.
Targets come from `0x80090748`, require bit `0x1` set and `0xA0` clear, and are
ranked by squared XZ distance.

Pause freezes an active record and resume advances it. Cleanup returns each
in-flight unit once. Native same-scene respawn clears marked windup/in-flight
5/3 to 0/0 and permits a fresh throw. Scene transitions replace transient player,
pool/cursor, target, and actor-table state; A08 has no serialized progression.

## Bounded residuals

- D04 and D-family rows own per-family immunity, HP, death, respawn, permanence,
  quotas, and drops after consuming an A08 contact record.
- E05 owns model/animation/render asset decoding; A08 binds descriptor fields
  and handoff only.
- Shooter plants, bosses, and stage-special paths may share pool/update substrate
  but retain their input, ownership, target, and outcome laws.
- F14 owns Flight movement while the measured Flight context still admits A08.

None intersects the completed ordinary input/dispatch/projectile lifecycle.
Machine contract: `config/phase4_berry_throw.yaml`. Retained evidence:
`analysis/phase4_berry_throw.json`. Original facts:
[[SYS_berry_projectile_and_homing]]. Procedure and failed hypotheses:
[[EXP_2026-07-15_phase4_berry_throw]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
