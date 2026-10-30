---
kind: experiment
id: EXP_2026_08_02_phase4_e06_bounded_exhaustion
name: Phase 4 E06 contact-object-pool bounded exhaustion
status: complete
created: 2026-08-02
updated: 2026-08-02
confidence: high
---

# Phase 4 E06 contact-object-pool bounded exhaustion

## Question

Exhaust the high-value E06 contact-object-pool work using the accepted Phase 4
acceleration method: validate a retained capsule before any live replay, use C against
the resident ASM/EXE for the complete static frontier, and escalate to DuckStation only
for a named missing domain.

This pass is read-only. It did not launch DuckStation, mutate RAM, edit a movie or save,
or build or patch a disc.

## Scope

- Allocator capacity, selection, wrap, failure, and reuse.
- Construction metadata boundaries and producer call sites.
- Update/contact dispatch and billboard-render interfaces.
- Natural activation, retirement, reactivation, and cursor behavior.
- Honest Phase 4 status under the strict scorecard.

Non-scope: naming every decorative sprite, forcing a deliberately hanging 64/64 pool,
or replaying every level solely to repeat a shared resident mechanism.

## Static C investigation

`tools/phase4_e06_static.c` verifies the PS-X EXE layout, reads the resident tables
directly, and scans all 892 hand-written ASM files (100,425 instructions). It found 94
allocator call sites: 76 calls to `contact_alloc` (`0x80059E44`) and 18 calls to the
explicit constructor path (`0x8005A0E0`). Sixty-one sites reduce to literal constructor
IDs; 33 are bounded data/loop-derived producer sites rather than missing xrefs. Examples
already decoded in the ASM include `125 + (a3 & 3)`, `27 + global`, `83 + selector`, the
type-6 seed handler's `31 + packed_variant`, and the paired loop families in
`0x8005953C`.

### Corrected metadata boundaries

The address arithmetic is exact:

- Metadata B: `0x8007941C..0x80079E30`, stride `0x14`, exactly **129 rows**,
  constructor IDs `0..128`.
- Metadata A: `0x80079E30..0x8007A448`, stride `0x14`, exactly **78 rows**.

This supersedes the old `analysis/phase4_e06_ctortype_recipes.json` interpretation that
continued through constructor 199. That scan crossed from metadata B into metadata A
and then adjacent data; its rows 129 and above are not constructor recipes.

The walker table at `0x8001B570` has 117 entries for action IDs `2..118`; 15 differ
from the default target. The behavior/action namespace is separate from record
`+0x30`, the render-kind index. The descriptor table at `0x80096B98` is the previously
established 50-kind namespace (`0..49`), not a 128-entry action table. The capsule
boundary scan corroborates this: all 50 entries are stable RAM pointers, entries
`50..114` are zero, and `115..127` are adjacent unrelated pointer data.

### Capacity and failure

Both allocators pre-increment the shared cursor, wrap it modulo 64, and reject a
candidate only when `(record[0x33] & 0x80) != 0` and signed `record[0x22] != 0`.
There is no full-array escape. Therefore, if all 64 records satisfy that predicate,
allocation loops indefinitely. This is direct control-flow proof, not a runtime guess.

The condition was already behaviorally tested in Phase 2. The retained native A/B in
`analysis/phase2_capacity_hang_proof.json` shows a free-slot call returning
`0x800B1920`, while an all-64-occupied call timed out without returning to the trap.
Capacity non-return therefore has both static causal proof and native behavioral
confirmation; no repeat hang experiment is required.

## Retained-capsule investigation in C

The relevant retained capsule is `b06_invincibility_hits`, indexed by
`analysis/phase4_trace_capsule_set.json`. Its manifest is complete, has no capture
errors, and the central index records an exact independent-control match. The capsule
contains frame-boundary RAM/VRAM/SPU/registers plus passive block flow; it is not
every-cycle evidence.

`tools/phase4_e06_capsule.c` directly parses all 19 zstd chunks, reconstructs every
domain, and checks the embedded SHA-256 after every frame. Results:

| Measurement | Result |
|---|---:|
| frame records | 1,098 (`movie 0..1097`) |
| domain hash checks | 3,294, zero mismatches |
| `contact_alloc` entry blocks | 465 |
| explicit spawn-full entry blocks | 9 |
| walker / billboard-render entry blocks | 549 / 549 |
| occupied records | min 0, max 3 of 64 |
| walker-live records | min 0, max 2 of 64 |
| activation / retirement transitions | 14 / 13 |
| reactivations of a previously used slot | 1 |
| cursor changes | 465, each paired with one allocator entry in that frame |
| cursor wraps | 12 |
| descriptor changes | 0 of 50 |

Observation: natural construction, retirement, reuse, update, and rendering all occur
in the retained run. Observation: frame-boundary cursor movement correlates perfectly
with allocator entries in this capsule. Inference: the 12 wraps are consistent with the
statically proven round-robin cursor. They do not expose every intra-frame candidate
test, so the capsule is not used to overclaim instruction-exact skip attribution.

## Original interfaces

- `contact_alloc` / explicit spawn choose and initialize a `0x38` record from metadata.
- `contact_walker` scans 64 records, requiring signed TTL `> 0` and flags bit `0x02`
  before contact behavior.
- The action dispatcher covers IDs `2..118`, with a default handler plus 15 specialized
  entries.
- `contact_billboard_render` scans the same pool and maps record render-kind `+0x30`
  through the 50-entry descriptor table to `POLY_FT4` submission.
- Allocation occupancy, walker liveness, and render liveness are related but distinct
  predicates. Code using one predicate as a universal "active" bit is incorrect.

## Phase 4 scorecard

| Dimension | Status | Boundary |
|---|---|---|
| Original oracle | advanced, not met | Existing natural and Phase 2 stress evidence is not a dedicated full E06 oracle. |
| Complete frontier | advanced, not met | Resident allocator xrefs and tables are enumerated; not every overlay/data-derived producer is semantically named. |
| Typed state | advanced, not met | Base, count, stride, cursor, metadata bounds, action dispatch, render-kind table, and distinct liveness predicates are typed; remaining fields and reset ownership are not. |
| Lifecycle/capacity/reset | advanced, not met | Natural activate/retire/reactivate/wrap and static saturation behavior are closed; scene-reset breadth is not. |
| Original interfaces | advanced, not met | Constructor, walker, action dispatch, descriptor, and renderer interfaces join substantially; complete action side effects, overlay crossings, and asset initialization remain. |
| Campaign breadth | not met | One retained natural capsule is not all-stage breadth. |
| Cross-system contracts | advanced, not met | Pickup/power/seed producers are represented, not exhaustively campaigned here. |
| Source closure | advanced, not met | Semantic C decompiles and retained C analyzers exist; full matching-source closure is not claimed. |
| Durable evidence | advanced, not met | Hash-pinned capsule/static artifacts exist; no dedicated E06 behavioral scenario/gate was added. |

**Methodology correction: E06 remains `partial`; the allocator core is
bounded-exhausted, but the row's offline frontier remains open.** The strict scorecard
does not permit `solved`. One further C/offline batch can still materially improve the
overlay-producer, field-access, reset-writer, and dynamic-constructor frontiers. Moving
to another row is nevertheless valid because the accepted Phase 4 method discourages
repeatedly deepening one partial row while other high-ranked offline work remains.

Exact audit: `analysis/phase4_e06_methodology_audit.json`.

## Movie decision

No new Interpreter-mode movie is required now. Run the C/offline frontier batch and
inventory existing Interpreter cold-boot fixtures first. Request a recording only if a
named oracle, reset, transition, or exceptional-path assertion is absent from retained
evidence, or exact intra-frame attribution cannot be obtained statically. Old
CachedInterpreter movies remain poll-only.

## Reproduction and hashes

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_e06_static.c -o /tmp/phase4_e06_static -lcrypto
/tmp/phase4_e06_static ./SCUS_942.88 asm/hand_written/*.s

cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_e06_capsule.c -o /tmp/phase4_e06_capsule -lcrypto
/tmp/phase4_e06_capsule "$ABL_EXTERNAL_EVIDENCE/trace-capsules/Phase4/v2/b06_invincibility_hits"
```

| Object | SHA-256 |
|---|---|
| pristine `SCUS_942.88` | `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20` |
| capsule manifest | `492aa2134e8d4d4bc8b348cd0c6d16f757d9ac4e5e3134945b2c688132f18c11` |
| central capsule index | `569b3ebf073b2384c04edecbc54ca52d4f7a35a0387a02e9540e7a936509cc53` |
| `tools/phase4_e06_static.c` | `13ecd282fe8f15d8a8cb177007707b3f800dc1d393cb12fe33b8a6e5cbfbbcdb` |
| `analysis/phase4_e06_static.json` | `cae4da7e21a7ebe7f43c431d29f512034b5221ea25607ef7cb44b7bb52f2ac10` |
| `tools/phase4_e06_capsule.c` | `026403fdf22b5197c691b24cee1e34dd7d9be37e639befa998ba60f6cae11d9a` |
| `analysis/phase4_e06_capsule.json` | `5bb021b39f898cc0806779fcf053271f96d86e661e60d32c3d9c6ba4cc6ec2c0` |

## Links

[[SYS_contact_object_pool]] | [[Game Solving Campaign - Contact Object Pool]] |
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]] |
[[EXP_2026-07-18_phase4_trace_capsules]]
