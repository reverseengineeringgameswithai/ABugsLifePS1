---
kind: system
id: SYS_contact_object_pool
name: Contact object pool
status: confirmed
created: 2026-08-02
updated: 2026-08-04
confidence: high
evidence:
  - EXP_2026-08-02_phase4_e06_bounded_exhaustion
  - EXP_2026-08-04_phase4_f02_debris_damage_class
  - tools/phase4_f02_debris_class_bind.c
  - analysis/phase4_f02_debris_class_bind.json
  - analysis/phase4_f02_debris_live_probe.json
---

# Contact object pool

The resident contact-object substrate is a fixed pool at `0x800B0D18` containing 64
records of `0x38` bytes. A shared cursor at `0x8008234C` drives round-robin selection.

## Allocation

`contact_alloc` (`0x80059E44`) and the explicit constructor path
(`0x8005A0E0`) pre-increment the cursor and wrap it modulo 64. A candidate is rejected
only when flags byte `record+0x33` has bit `0x80` and signed halfword
`record+0x22` is nonzero. Otherwise the allocator may overwrite it.

There is no full-pool escape. If all 64 records meet the rejection predicate, the
allocator cannot return. Static control flow proves this, and the earlier retained
Phase 2 native A/B independently confirms it: the free-slot `debugger.callFunction`
returned `0x800B1920`; the all-64-occupied call did not return before the guest-call
timeout. See `analysis/phase2_capacity_hang_proof.json`.

## Construction metadata

- Metadata B is `0x8007941C..0x80079E30`, stride `0x14`, exactly 129 rows for
  constructor IDs `0..128`.
- Metadata A is `0x80079E30..0x8007A448`, stride `0x14`, exactly 78 rows.
- The older E06 scan through constructor 199 crossed these boundaries. Its apparent
  rows above 128 are not metadata-B constructor recipes.
- Resident ASM contains 94 allocator call sites: 76 ordinary and 18 explicit.
  Literal IDs resolve at 61 sites; the remaining 33 compute IDs from bounded loop or
  object state.

## Update and contact dispatch

`contact_walker` (`0x800586B0`) scans all 64 slots. Its contact gate is signed
`record+0x22 > 0` plus flags bit `0x02`. The action dispatcher at `0x8001B570` has 117
entries for action IDs `2..118`; 15 use specialized targets and the rest use the
default path. (Both counts re-measured 2026-08-04: 117 in-text pointers ending at a
`0x00000000` terminator, 15 specialized entries over 14 distinct targets.)

The allocator's occupied predicate and the walker's live predicate are not equivalent.
Code must not collapse them into one universal active flag.

### The pool has six consumers, each with its own gate

The walker is one of six. Which consumers a record can reach is decided entirely by its
metadata-B row, so it is a **static property of the ctor type**. Masks below are decoded
from the image by `tools/phase4_f02_debris_class_bind.c`:

| consumer | gate PC | gate |
|---|---|---|
| `0x800586B0` contact_pickup_walker | `0x80058748` | `record+0x22 > 0` && `record+0x33 & 0x02` |
| `0x80058AF8` contact_vs_actor | `0x80058C6C` | `record+0x33 & 0x04` && `record+0x22 > 0` |
| `0x8005A308` record update — berry branch | `0x8005A358` | `record+0x33 & 0x08` |
| `0x8005A308` record update — behaviour class | `0x8005A8F4` | `(uint32_t)(record+0x2F - 1) < 0xE` |
| `0x8005CD2C` gameplay_effect_spawner | `0x8005D2B8` | `record+0x2F == 5` |
| `0x80014844` contact_billboard_render | `0x800148E0` | `record+0x22 != 0` — **no flags test** |

Eleven resident sites reference the pool base; the remainder are the allocator
(`0x80059E44`), the explicit constructor (`0x8005A0F0`) and the reset
(`0x80057404`). ⚠️ An enumeration scan must accept **both** base-materialisation idioms —
`lui`+`addiu` (the walkers) and `lui`+`ori` (the renderer) — or it silently undercounts.

Two post-construction stores to `record+0x33` are currently resolved and pinned:
`0x800588AC` and `0x80058F74`. Both are *inside* handlers a record can only reach by
having already passed a gate. A record whose flags exclude it from every resolved gate
cannot acquire a flag at either of those sites. The general scan retains unresolved-base
and indirect-call residuals, so this is not a complete field-aware writer census.

**Correction history (2026-08-04 audit):** “written after creation at exactly two
sites” promoted the two resolved sites into closure. The sites and their base provenance
remain pinned; the exact global count and absolute “can never acquire one” conclusion are
retracted.

**flags bit map** (`metaB+0x10` → `record+0x33`), across the 129 metadata-B rows:

| bit | consumer | rows |
|---|---|---|
| `0x01` | ground-collision branch in the updater (`0x8005A5A8`) | 31 |
| `0x02` | pickup-walker gate | 30 |
| `0x04` | contact-vs-actor gate | 17 |
| `0x08` | berry-projectile branch in the updater | 4 |
| `0x10` | no consumer located | 0 |
| `0x20` | no consumer located — set on 116 rows, likely a "row in use" marker | 116 |
| `0x40` | no consumer located | 68 |
| `0x80` | occupied marker, tested by the allocator | 50 |

### The updater is not berry-specific

`0x8005A308` (census name `berry_projectile_update`) is the **general per-frame contact-record
update**. Its `record+0x22` decrement sits in a branch delay slot and therefore applies to
*every* live record; the berry behaviour is only the `flags & 0x08` branch. It also owns the
position integration (`pos += vel`, `vel_Y += accel_Y`), the animation stepper, the colour
fade, the distance cull, and the second dispatch table
[[TABLE_8001B7F0_contact_behaviour_class_dispatch]].

The position integration is what proves metadata table A's four outputs
(`record+0x0C/0x10/0x14/0x18`) are velocity X/Y/Z plus a Y acceleration — a reading
`src_re/contact_alloc_80059e44.c` had marked "inferred, not proven".

### record+0x2E identifies the ctor type at runtime

`record+0x2E` is the only field that names a live record's ctor type, so a pool census must
key on it. From `0x8005A088` in the allocator:

```
sel = metaB[ctorType] + 0x0E
sel == 0 -> record+0x2E = 0            (identity erased)
sel == 1 -> record+0x2E = +ctorType
else     -> record+0x2E = -ctorType    (stored as a byte, so ctor 0x5A reads 0xA6)
```

⚠️ `src_re/contact_alloc_80059e44.c` documents the `sel == 1` and `else` arms the **other way
round**. The image and a live pool census agree on the mapping above: 26 of 27 distinct
`record+0x2E` values observed live reconcile against `metaB[∓value]` on both action id and
flags, the 27th being the `sel == 0` identity-erased case.

## Rendering

`contact_billboard_render` (`0x80014844`) scans the same 64 records and submits
screen-aligned `POLY_FT4` sprites. Record byte `+0x30` is the render-kind index into the
50-entry descriptor table at `0x80096B98` (`kind 0..49`). It is separate from the
behavior/action namespace, which reaches action 118 in the walker table and action 123
in constructor metadata.

The retained B06 capsule held all 50 descriptor pointers stable for 1,098 frames.
Entries immediately after the table are zero padding before unrelated pointer data;
they are not extra render kinds.

## Natural lifecycle evidence

The hash-verified retained capsule observed 465 ordinary allocations, 9 explicit spawn
entries, 14 activation transitions, 13 retirements, one reactivation of a previously
used slot, and 12 cursor wraps. Walker and renderer entries each occurred in 549
frames. Occupancy peaked at 3/64, so this evidence covers ordinary lifecycle and reuse,
not saturation.

Frame-boundary cursor changes correlated one-for-one with allocator entries. Exact
intra-frame candidate attribution still requires instruction-level instrumentation;
the static allocator loop supplies the capacity/failure proof without that escalation.

## Evidence boundary

These allocator-core mechanics are confirmed. The Phase 4 E06 row remains `partial`
because strict
closure also requires a dedicated oracle, broader stage/reset coverage, cross-system
campaign breadth, matching-source closure, and a dedicated durable behavioral gate.
The allocator core is bounded-exhausted. The row's offline frontier remains open for
overlay/data-derived producers, complete field/reset writers, and action side effects;
exhaustive decorative naming remains lower priority.

## Evidence

[[EXP_2026-08-02_phase4_e06_bounded_exhaustion]] |
[[SYS_contact_objects_and_drops]] |
[[Game Solving Campaign - Contact Object Pool]] |
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]]
