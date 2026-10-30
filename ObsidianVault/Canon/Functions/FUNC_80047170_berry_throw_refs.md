---
kind: function
id: FUNC_80047170
aliases: [FUNC_80047170, 0x80047170]
address: 0x80047170
name: berry_throw_refs
status: static_seen
confidence: medium
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - src_re/berry_throw_80047170.c
src_paths:
  - src_re/berry_throw_80047170.c
patch_policy: unknown
---

# FUNC_80047170 - berry throw refs

## Purpose

Generated from C source coverage. The original-game behavior should be refined manually with call/read/write links.

## Known behavior

See the exact source excerpt below. Preserve `UNKNOWN`, `LIKELY`, and `TODO` labels from the source comments.

## Address / identity

- Address: `0x80047170`
- Name: `berry_throw_refs`
- Source path: `src_re/berry_throw_80047170.c`

## C source excerpt

Source: `src_re/berry_throw_80047170.c`

```c
/* ============================================================================
 * berry_throw_80047170.c — berry throw dispatch + spawner call ABI
 * ----------------------------------------------------------------------------
 * Live/mod-confirmed 2026-07-07 while restoring the Blackberry/Fastberry shot.
 * Complements src_re/berry_homing.c and mod/berry_projectile.h.
 *
 * THROW DISPATCH (0x80047170..0x800471e0)
 *   The equipped berry index at player+0x97 (global mirror 0x800a6597) is read
 *   and bounds-checked against the native 0..4 jump table at 0x8001b1c0:
 *     index 0 -> red     -> s1 = 2
 *     index 1 -> blue    -> s1 = 5
 *     index 2 -> homing  -> s1 = 8, with homing vertical setup
 *     index 3 -> gold    -> s1 = 11
 *     index 4 -> mega    -> s1 = 45, with homing vertical setup
 *
 * THROW CALL (0x800471e0..0x80047254)
 *   The shared tail computes an initial velocity from the current heading and
 *   calls contact_object_spawn at its full entry 0x8005a0e0:
 *
 *       a0 = spawn_x; a1 = spawn_y; a2 = spawn_z; a3 = vel_x;
 *       sp+0x10 = vel_y;
 *       sp+0x14 = vel_z;
 *       sp+0x18 = gravity;
 *       sp+0x1c = berry type/class s1;
 *
 *   The spawner copies those fields into the contact record and uses s1 to index
 *   the per-type table. The commonly-hooked 0x8005a0f0 address is mid-prologue,
 *   after the stack args have already been loaded into t1/t2/t3/t0.
 *
 * BLACKBERRY / FASTBERRY MOD IMPLICATION
 *   mod/patch.asm maps custom equip index 5 to native dispatch index 0, so the
 *   shot is a stock red-equivalent straight berry path. The spawner hook at
 *   contact_object_spawn+0x10 consumes a one-byte flag from the throw cave and doubles
 *   vel_x/vel_y/vel_z while quadrupling gravity, preserving the arc but halving flight time.
 *   Damage parity with red depends on two separate mechanisms:
 *     1) this throw cave must leave the spawned contact object's class/power as red
 *        (s1=2), which feeds the actor-local +0x6e hit-counter branch; and
 *     2) because the enemy damage code also reads equip index 0x800a6597 as an
 *        HP-column selector, the mod hooks the selector reads at 0x800590f0 and
 *        0x80059358 so index 5 behaves as red selector 0.
 *
 *   killing_spider.movie.json verification, 2026-07-07: forced equip index 5 on
 *   rebuilt ALLMODS hit the speed hook, stored s1=2 at 0x80047228, and drove spider
 *   id 9's local +0x6e counter 2->1 on the first hit, then 1->0->999 on the second.
 *   The permanent-kill quota 0x800a658e was not decremented, matching red.
 * ============================================================================ */

#include "re_types.h"

#define BERRY_THROW_EQUIP_READ       0x80047170u
#define BERRY_THROW_SHARED_TAIL      0x800471e0u
#define BERRY_THROW_SPAWN_CALL       0x8004724cu
#define BERRY_THROW_POWER_STORE      0x80047228u
#define BERRY_THROW_FAST_SPAWN_HOOK  0x8005a0f0u
#define BERRY_THROW_COUNTER_ALLOW    0x80049010u
#define CONTACT_OBJECT_SPAWN_FULL    0x8005a0e0u
#define CONTACT_OBJECT_SPAWN_HOOK    0x8005a0f0u

void berry_throw_refs(void)
{
    volatile unsigned refs = BERRY_THROW_EQUIP_READ ^ BERRY_THROW_SHARED_TAIL ^
        BERRY_THROW_SPAWN_CALL ^ BERRY_THROW_POWER_STORE ^
        BERRY_THROW_FAST_SPAWN_HOOK ^ BERRY_THROW_COUNTER_ALLOW ^
        CONTACT_OBJECT_SPAWN_FULL ^ CONTACT_OBJECT_SPAWN_HOOK;
    (void)refs;
}
```

## Evidence

- Source: `src_re/berry_throw_80047170.c`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Phase 4 A08 refinement (2026-08-03)

The function is no longer only a reference stub. C/static analysis confirms all five jump-table targets, the shared spawn ABI, and the split between ballistic-auto-aim types `2/5/11` and fixed-elevation homing primaries `8/45`.

The spawn position is player Y minus `12800` with heading-relative X/Z offsets. Initial X/Z velocity is `3*(sin/cos >>4)` and gravity is `128`. Types `2/5/11` consume heading and vertical velocity returned by `0x80046D24`; types `8/45` bypass it with `vy=-2048`. Each valid case increments player `+0x96` once before calling `0x8005A0E0`; the matching terminal cleanup lane later decrements it. Evidence: `analysis/phase4_a08_bounded_exhaustion.json`.
