---
type: experiment
status: complete
date: 2026-08-04
system: D09 cockroach / Redbug bounded exhaustion
phase: 4
artifacts:
  - analysis/phase4_d09_static_closure.json
  - analysis/phase4_d09_capsule_closure.json
  - tools/phase4_d09_static.c
  - tools/phase4_d09_capsule.c
---

# Phase 4 D09 Redbug bounded exhaustion

## Question

Can the older D09 0/9 scorecard be advanced to a defensible move-on point using
the retained capsule, later shared enemy closure, and pristine C/ASM analysis,
without replaying its CachedInterpreter-era movie under instrumentation?

## Capsule-first control

The retained `v3/D09_cockroach_contact_kill` capsule was accepted before any live
replay. Its manifest is complete/untruncated, pins the movie and state hashes, pins
the DuckStation binary/source state, and reports an exact control fingerprint match
for RAM, VRAM, SPU RAM, registers, full machine state, frame, and cycle. Manifest
SHA-256 is `fc80e5e10ad68dc4744ab61b3e91214bf9cd24393ac83b02d5abe3454ea4b78d`;
the referenced collection manifest SHA-256 is
`be545ed322878f47a55dd38e8e354bd2afcd0c36f43ae5c3716196a1bbb7da2b`.

`tools/phase4_d09_capsule.c` independently reconstructs all frame boundaries and
checks every embedded RAM/VRAM/SPU hash. It intentionally bounds the movie to what
it contains: two nonlethal hits, not the later manual terminal hit. This old movie
was captured under CachedInterpreter and remains capsule/poll-only evidence.

## Pristine executable closure

`tools/phase4_d09_static.c` rejects any executable except pristine retail SHA-256
`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
It verifies Redbug's ID-19/program-12 binding, exact wander bytecode, shared
resistance/damage and chase gates, temporary-KO tail, retirement interface, and
off-screen respawn reinitializer. It also emits an executable-wide candidate census
of every load/store using structure offset `+0x5C` rather than treating one known
writer as a complete frontier.

The old immunity gap is now bounded by D04 plus the capsule: Redbug carries bit
`0x40`, placing it in the berry-tough class. The red connecting form takes the
reaction-only branch; admitted non-red classes use the common damage switch. The
old quota contradiction is closed by the class-1 KO branch, which bypasses the
permanent effect/quota block. A nearby contact-object `action_id=1` is therefore
not promoted into a Redbug reward-drop claim.

The old `0x1000` hypothesis is narrowed decisively: Redbug's own program contains
neither a flag operation nor literal `0x1000`, and the actual pursuit gate reads
only bit `0x02`. The occasional `0x1000` transition is generic shared actor state,
not the causal Redbug pursuit latch. Exact decorative naming of that bit is left
open because it cannot change the established trigger or movement law.

## Updated disposition

**Substantiated partial, bounded-exhausted.** Identity, complete placement/variant
scope, typed state, accepted damage, resistance class, chase setter and consumer,
temporary KO, quota boundary, retirement, and off-screen respawn are now connected
to pristine instructions and durable C gates. Replaying all six data-identical
placements, exact animation/SPU/GPU presentation, a standalone movie containing the
third hit, and naming generic bit `0x1000` remain strict-Full breadth with minimal
mechanical return. No new Interpreter movie is required for D09.

## Commands

```bash
cc -std=c11 -O2 -Wall -Wextra tools/phase4_d09_static.c -lcrypto -o /tmp/phase4_d09_static
/tmp/phase4_d09_static SCUS_942.88 > analysis/phase4_d09_static_closure.json

cc -std=c11 -O2 -Wall -Wextra tools/phase4_d09_capsule.c -lzstd -lcrypto -o /tmp/phase4_d09_capsule
/tmp/phase4_d09_capsule ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/D09_cockroach_contact_kill > analysis/phase4_d09_capsule_closure.json
```
