---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Enemy AI movement programs.md
aliases:
  - "Enemy AI movement programs"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Enemy AI movement programs.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Enemy_AI_movement_programs.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Enemy AI movement programs
type: system
updated: 2026-07-03
confidence: CONFIRMED (static program disasm + 18-save behavioral sweep + falsification)
tags: [system, enemy, ai, movement, aggro, mover-vm, chase, gap-0034]
---

# Enemy AI movement programs (per-enemy, decoded)

> The per-enemy AI movement decode (2026-07-03), replacing the camera-contaminated model in
> [[Enemy AI state machine]]. Every regular enemy is driven by the **mover-VM [[FUNC_8004C13C]]**;
> its "AI" is a small **resident bytecode program** (region `0x8007745c..0x80077af6`, per-actor IP
> at `actor+0x70`). Disassembled all 14 enemies' programs (ISA from GAP-0033), swept 18 saves
> behaviorally, and **falsified the chase gate live**. RE source: `src_re/enemy_ai_programs.c`.
> Operator ground truth confirmed: *"some of them have aggro, some do not."*

## Aggro exists at THREE levels

| Level | Mechanism | Where |
|---|---|---|
| **CHASE** | GLOBAL feature of the VM motion phase (`0x8004c8ac`+): if actor flags `+0x5c` **bit `0x2`** set and Flik within a per-object radius (op16 scratch: 1000/400 units), the motion goal is swapped to **Flik's live position** (Y−2048) | shared code, per-actor flag |
| **PROXIMITY TRIGGER** | `op17`: `s3 = dist(Flik) < R` + an `op9` branch reacting (advance path / jump to strike) | per-program, radius = operand |
| **CONTACT RING** | actor parked on op17/op18 with `dist²(Flik) < 0x9c3f` (~200 units) → `IP += 6` = jump into its **strike section** | motion phase |

**Falsification (live):** suppressing bit `0x2` each frame on the chasing spider flipped pursuit
**+0.93 → −0.89** (distance −2931 → +10331). The bit is set dynamically on aggro; clearing it kills the chase.

## Per-enemy program taxonomy (all 14 disassembled)

**A) Wander + chase** — loop `[op3 wait rnd(0..63)+32][op4 random-direction step][PARK seek-target]`; chase via the global bit-0x2 gate:
`spider` (prog `0x80077470`), `dragonfly` (`0x8007755c`), `bee` (`0x80077578`, parks on **op18** → contact-ring strike), `earthworm` (`0x800775c8`), `huge_spider` (`0x80077674` — on a platform; Flik must jump up, X+UP, to engage), `Redbug` (`0x80077690`), `Horsefly` (`0x800776d0`), `shell_bug`/`canyon_bug` (`0x800776ec` — **two-speed wander**: op16 chase-radius 0x3e8→fast / 0x190→slow, switched by an op15 noise coin-flip; canyon_bug has extra path sections @`0x77850`+ with op20 branches + CALL sub5).

**B) Path-patrol + proximity** — loop `[op5 next waypoint][PARK][op17 dist<1200][op9 if s3 → advance]`: the actor only progresses along its LEVEL.DAT waypoint path **while Flik is within 1200**, else it parks:
~~`mosquito`~~ **DOT the guide NPC** (prog `0x800775e4`) — **CORRECTION 2026-07-03** → [[Dot guide NPC]]: the sweep's id-14 "mosquito" actor was Dot (targetable-bit clear, friendly guide); the real mosquito enemy = the **id-10 chaser** (the one Thumper throws). The proximity-gated path program is her GUIDE law (advance only while Flik near).

**C) Ambush/popup (the "no aggro movement" enemies — stationary)** — loop `[anim][op13 flags][wait][PARK arrive+stop][op17 dist<R][op9 → STRIKE]`; STRIKE = `flags|=0x40` (**the berry-tough bit — VM-managed!**), `op12 CALL sub8` (native strike), strike anim, loop:
`worm` (section `0x800779f6`, **radius 700**), `wall_worm` (`0x80077a58`, **radius 1200**), `pill_bug` (`0x8007799c` — gated by **op25 global-flag**, not proximity; curl/uncurl via helper(27)). Their op13 masks leave bit 0x2 **clear** → the global chase never engages = stationary.

**D) Native-assisted** — `grasshopper` (prog `0x8007760c`): tiny `[op23][op12 CALL sub3][anim][PARK arrive-test][op22 DONE]` — target set natively; chases via the global gate while parked.

## Behavioral sweep (18 saves, pursuit = mean cos(step, dir→Flik))
Chase episodes live: spider **+0.93**, huge_spider +0.83, grasshopper +0.78, dragonfly_2 +0.72, canyon_bug +0.64, Horsefly/Redbug closed 16–20k. **Stationary (zero movement)**: worm, pill_bug, wall_worm. bee/mosquito/earthworm/shell_bug: patrol/wander dominates (chase is state/proximity-dependent). Enemies are **state machines** — a 60-frame window catches whichever state is active, which is why single-window classification wobbles.

## The motion phase (how movement executes)
Programs **park** on a motion opcode (phase-2 mode = stream−5); each frame the motion-apply (`0x8004c8ac`) advances position toward the target `+0x34/38/3c` at fixed speed `s4 = program[+0x14]<<4`, heading-rotated via the sine table. Arrive-test: `dist² < s4²` → `IP += 2` (program continues). The chase gate and contact ring (above) are embedded here.

## Modding levers (documented only — no mod built; these are EXE data edits)
- **op17 aggro radii**: worm 700 @`0x80077a0a`, wall_worm 1200 @`0x80077a72`, Dot-guide follow radius 1200 @`0x80077600` (u16 operands).
- **op16 chase radii** (0x3e8/0x190 in the `0x776ec` program); **op2/op3 waits** = patrol cadence.
- **flags bit `0x2`** = chase on/off (live-proven lever); **program table `0x80077af8`** = swap an enemy's whole AI.

## Residuals
- Who SETS bit 0x2 on aggro (a native sub via op12, or the record param words) — the gate itself is proven, the setter isn't pinned.
- op4's random-step distribution (leash-to-anchor?), exact op16-scratch→radius scaling, CALL sub bodies (sub3/5/7/8), op25's global flag identity (pill trigger).
- Per-level program seeding (which record field selects the program) — the known GAP-0033 residual.

## Related
[[FUNC_8004C13C]] · [[Enemy spawn architecture]] · [[Enemy death and permanence]] · [[Enemy AI state machine]] (superseded chaser model) · [[Event and scripting system]] · [[Retail Gameplay Completeness Gap Audit]] RCG-006
