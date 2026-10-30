---
kind: experiment
id: EXP_2026-08-03_phase4_d14_wasps_dragonflies
status: complete
source_state: original_game
system: [SYS_wasps_and_dragonflies, SYS_enemy_ai]
row: D14_wasps_dragonflies
---

# Phase 4 D14: wasps and dragonflies

## Verdict

**D14 is bounded exhausted and can be moved past. No Interpreter movie is required for the current row.**

The named gaps were flight navigation, sting/contact behavior, and homing targetability. Static analysis now owns each family program and the exact target filter. Interpreter save-state runs add the missing live domains: dragonfly movement, target-table membership, bee contact transition, native strike execution, and causal player health loss.

## Method and escalation

The Phase 4 capsule manifest was queried first with compiled C. It contained 50 capsule entries and no D14, dragonfly, or wasp identity. Live escalation was therefore justified for actor flags, frame-boundary movement, exact VM writes, and instruction-attributed contact execution.

This was a narrow runtime experiment, not a disc/code/asset change. Hash-pinned save states were therefore the correct anchor; cold-boot reproduction was not required.

The owned instance used:

- Config: `/tmp/abl-d14-live-20260803-1`
- Port/token: `23530` / `d14-20260803`
- Mode: explicit `[CPU] ExecutionMode=Interpreter`
- Media: SCUS-94288, pristine retail cue
- DuckStation revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`
- Binary SHA-256: `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`
- Cleanup: PID 178870 stopped through the same config-scoped launcher

The repro launcher printed a stale literal saying CachedInterpreter, but the generated settings were read directly and contained `ExecutionMode=Interpreter`. No movie playback was used.

## Fixture identity

| Fixture | SHA-256 |
|---|---|
| `dragonfly.sav` | `2b84be04cdd60b3b848bce011aaf64d6a8cfb4d481d3bf22eabb02f388877fb3` |
| `dragonfly_2.sav` | `8a6a976fa6d77d04fcf68384595d02a9c922b2cbf12bce96a48520c4ac18a93c` |
| `bee.sav` | `2cfe892546b1e7ed04f9b3bcb6c957e7230ead06c36cacd03be36ddc3cf75b5b` |
| `bee_1_homing.sav` | `b34addb0b67257b9d670b18037a1183df76dd9cc92930a771c7db5d19a1df504` |
| `bee_2_homing.sav` | `a648ec992f4c6af46921428442087f7db1ed91cca5385e61e5563f06bd705068` |

Every state reported valid, version 84, title `Disney-Pixar A Bug's Life`, and serial SCUS-94288 before loading.

## Static C analysis

`tools/phase4_d14_static.c` reads the PS-X EXE header, maps the pristine executable, decodes signed mover-VM words with `index = raw + 1`, verifies the five homing-filter words, disassembles the opcode-18 contact transition, and inventories every `+0x5C -> andi 1` candidate.

Reproduction:

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror \
  -o /tmp/phase4_d14_static tools/phase4_d14_static.c
/tmp/phase4_d14_static SCUS_942.88
```

Pinned executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

Tool hashes:

| Artifact | SHA-256 |
|---|---|
| C source | `27c8b1979c736e2deddd9032439b94db8f28923094d3e461488b34dbd6aeeafa` |
| compiled binary | `10eda7c889ec708697645d6d959428db016794ee6c8832f93832acd594cfaf2f` |
| output | `25e751c30fd7c9d320c17f78aa84fc01364af04df431689b2cbd1b405f8ea950` |

### Dragonfly program

The exact `0x8007755C..0x80077578` program is:

- set byte parameters `(64, 65472)`
- load animation `(1,2)`
- random wait `(63,32)`
- random direction step
- park/seek at `0x80077570`
- jump back to `0x80077568`

There is no dragonfly strike section. Actor ID 34 uses callback `0x8004A20C`. Byte-level disassembly shows that callback only calls `0x8005044C` with id 42 and the actor X coordinate plus 4; it adds no dragonfly-specific sting state.

### Wasp/internal bee program

The WASP asset family is represented by the game's internal bee program and live actor ID 13, callback `0x8004A144`.

The exact `0x80077578..0x800775C8` program:

- installs flags `0x6`
- performs random flight
- parks on opcode 18 at `0x80077592`
- on contact, enters `0x80077598`
- clears chase bit `0x2`, changes animation, waits 5, and parks at arrival
- calls native subroutine 2 at `0x80057920`
- changes animation again, waits 15, and loops

The shared opcode-18 contact gate loads squared threshold `0x9C3F`. At `0x8004CA10` it adds 6 to actor `+0x70`; `0x8004CA18` stores the new VM pointer. This is the static owner of `0x77592 -> 0x77598`.

### Homing target filter

The exact target gate is:

- `0x8005747C`: `lhu` actor `+0x5C`
- `0x80057484`: require bit `0x1`
- `0x8005748C/90`: reject bits `0xA0`
- remaining acquisition ranks X/Z distance; Y is ignored

The image-wide simple pattern census found three `+0x5C -> andi 1` candidates, including the homing owner at `0x8005747C`. This is a complete census for that exact instruction shape, not every possible semantic flag read.

## Runtime observations

### Family bindings

- Dragonfly: actor ID 34, callback `0x8004A20C`, VM `0x8007755C..0x80077578`.
- Wasp/internal bee: actor ID 13, callback `0x8004A144`, VM `0x80077578..0x800775C8`.

### Dragonfly navigation

From `dragonfly_2.sav`, the active targetable ID-34 actor at `0x800A0098` remained parked at VM `0x80077570` while moving over 120 frames:

```text
delta = (+4704, 0, -9842)
flags = 0x4005 -> 0x4005
VM    = 0x80077570 -> 0x80077570
```

Three other ID-34 instances were inactive at their program entry and did not move in this bounded window. The conclusion is deliberately per-state: the active dragonfly executes continuous X/Z flight under the random-direction/seek loop; dormant instances do not prove global motion.

### Bee contact and strike causality

The no-input control from `bee.sav` ran 600 frames. The active ID-13 bee stayed at `0x80077592`, its VM pointer was written 300 times without truncation, and neither `0x80057920` nor the strike transition executed.

A four-direction 60-frame probe found that Up reduced Flik's X/Z distance to the bee. The causal run then reloaded `bee.sav`, armed the actor `+0x70` write watch and `execTrace` at `0x80057920`, held Up for 60 frames, released, and traced 120 frames.

Exact non-equal VM writes:

```text
25934  0x8004C834  0x80077592 -> 0x80077594
25936  0x8004C834  0x80077594 -> 0x80077592
25958  0x8004CA18  0x80077592 -> 0x80077598  contact branch
25960  0x8004C834  0x80077598 -> 0x800775A8
25972  0x8004C834  0x800775A8 -> 0x800775AA
25974  0x8004C834  0x800775AA -> 0x800775B0
25992  0x8004D03C  0x800775B0 -> 0x800775B2
25994  0x8004C834  0x800775B2 -> 0x800775C0
```

At frame 25994, `execTrace` recorded one non-truncated hit at native strike `0x80057920` with `a0 = s0 = 0x800A0098` and `s1 = 0x800775B2`. Flik health changed `4 -> 3`. This connects approach, opcode-18 contact, the ID-13 bee VM, native strike, and damage in one deterministic replay.

### Targetability positive and negative states

`dragonfly_2.sav` exposes ID 34 at `0x800A0098` with flags `0x4005` in the live damageable table. `dragonfly.sav` independently has targetable ID-34 instances with flags `0x4007`.

The two bee homing fixtures form an eligibility control:

- `bee_1_homing.sav`: `0x80090748 -> 0x800A0098`, ID 13 slot 6, flags `0x4007`.
- `bee_2_homing.sav`: slot 6 becomes `0x1006`, loses bit `0x1`, and is absent; `0x80090748` instead points to targetable ID 13 slot 3 at `0x8009FF0C`, flags `0x4007`.

The live table switch agrees exactly with the byte-verified filter. A Square probe from `dragonfly_2.sav` did not execute `0x8005743C..0x80057620`; this only shows that the fixture did not trigger/equip that throw and is not treated as negative dragonfly evidence.

## Observation, inference, and confirmation

**Observation:** exact VM words distinguish a wander-only dragonfly program from the bee opcode-18 strike program. Live actors bind ID 34 and ID 13 to those regions. Targetable and non-targetable flags match live table membership.

**Inference:** the row's “wasp” terminology corresponds to the internal bee family associated with `WASP.ALL`; the live runtime names the program bee. Dragonfly has no species-specific sting path; any further collision reaction is shared enemy-contact behavior.

**Causal confirmation:** controlled Up input drives ID 13 across the exact `0x8004CA18` contact transition, executes `0x80057920` with the same actor pointer, and reduces health by one. The targetability filter itself is byte-verified and the eligibility table switches when bit `0x1` switches.

## Closure against D14 requirements

| Requirement | Result |
|---|---|
| Flight navigation | Closed: exact VM loops plus live active dragonfly delta; bee random-flight/contact path decoded. |
| Sting/contact behavior | Closed: bee contact-to-native-strike-to-health chain; dragonfly program has no strike section and callback is sound-only. |
| Targetability | Closed: exact `+0x5C` filter, positive dragonfly/bee entries, and negative bee eligibility switch. |
| Family identity | Closed: ID 34/`0x8004A20C`/dragonfly VM and ID 13/`0x8004A144`/bee VM. |
| Missing-domain escalation | Closed: no capsule; isolated Interpreter state runs supplied the named missing domains. |

Further visual animation recording would add presentation evidence but no missing control-flow, state, target-filter, or damage-domain fact. That is minimal return and is not required for D14 closure.

## Evidence preservation

The machine-readable summary and all transient hashes are in `analysis/phase4_d14_wasps_dragonflies.json`. Bulk debugger responses remain under `/tmp`; no save, movie, disc, capture, or token artifact was added to the repository.
