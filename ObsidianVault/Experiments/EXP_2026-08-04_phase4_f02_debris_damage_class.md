---
kind: experiment
id: EXP_2026-08-04_phase4_f02_debris_damage_class
row: F02_tunnels
created: 2026-08-04
status: closed
confidence: high
systems:
  - Contact object pool
  - Contact objects and drops
---

# F02 Tunnels — the falling-debris damage class

**Result: contact class `0x5A` is a decorative particle. It has NO damage, NO knockback,
and no player interaction of any kind.** It is drawn, moved, colour-faded and culled, and
it is structurally excluded from every gameplay consumer of the contact pool.

The row asked to "bind contact action class 0x5A to the handler that runs on player
contact, and say what it does". The answer is that **no handler runs on player contact**,
and the reason is a property of the class's metadata row, not an accident of the traced
run.

## The premise the row inherited was wrong twice

The previous attempt (`analysis/phase4_f02_contact_action_table.json`, now marked
superseded) failed for two independent reasons, and neither was the one it recorded.

**1. `0x8001B570` is the table, not a dispatcher function.** The prior run treated it as a
function and looked for the jump table at `0x8001B570 + 696` (the census function size) =
`0x8001B828`, found 21 plausible pointers followed by ASCII, and concluded "the 117-entry
table is unlocated". The disassembly reads `0x8001b570 .dword 0x80058834` — it is the
table itself, and Canon's own `FUNC_800586B0` page already said the walker "jump[s] through
word table `0x8001b570[idx]`". Counted in place it holds **exactly 117 in-text pointers
(action ids 2..118), terminated by a `0x00000000` word** — matching Canon's documented
count. What sits at `0x8001B828` is an unrelated pointer run belonging to other tables.

**2. `a3` is a ctorType, not an action id.** This is the deeper error, and it invalidated
the "three plausible bindings" the prior run produced. Per the confirmed Phase-3
decompilation `src_re/contact_alloc_80059e44.c`:

```
record = contact_alloc(x, y, z, ctorType = a3, stackArg = [sp+0x40])
record+0x20 (action_id) = metaB[ctorType] + 0x00      metaB = 0x8007941C, stride 0x14
```

So `0x5A` indexes **metadata table B**, and the action id is a *field of that row*.
Indexing the dispatch table by `0x5A` — or by `0x5A - 2` — reads an unrelated slot.

## The real chain

`tools/phase4_f02_debris_class_bind.c` (self-verifying against the pristine image; it
refuses rather than printing plausible addresses):

```
spawner a3 = 0x5A (ctorType)
  -> metaB row 0x80079B24 = 01 00 10 00 FB FF 00 04 C8 00 C8 00 00 00 02 00 20 60 30 00
       +0x00 action_id   = 1     -> rec+0x20
       +0x02 active_type = 16    -> rec+0x22
       +0x04 init24      = -5    -> negative: rec+0x22/+0x24 are re-randomised at alloc
       +0x07             = 4     -> rec+0x30  (animation frame count)
       +0x08 radius_add  = 200   -> rec+0x28
       +0x0F class       = 0     -> rec+0x2F
       +0x10 flags       = 0x20  -> rec+0x33
       +0x11..13         = 60 30 00  -> the fade colour source
```

`action_id = 1` gives walker index `(int16)(1-2) = -1`, which fails the walker's own
`(uint32_t)idx < 0x75` test and would fall to the default case — but the record never gets
that far, because the gates come first.

### Every consumer of the pool, and why `0x5A` reaches none of them

Eleven resident sites reference the pool base `0x800B0D18`. All eleven are accounted for.
Masks decoded from the image, not quoted:

| consumer | gate (PC) | decoded | ctor `0x5A` |
|---|---|---|---|
| `0x800586B0` contact_pickup_walker | `0x80058748` | `andi rec+0x33, 0x02` | **BLOCKED** |
| `0x80058AF8` contact_vs_actor | `0x80058C6C` | `andi rec+0x33, 0x04` | **BLOCKED** |
| `0x8005A308` record update (berry branch) | `0x8005A358` | `andi rec+0x33, 0x08` | **BLOCKED** |
| `0x8005A308` behaviour-class dispatch | `0x8005A8F4` | `sltiu (rec+0x2F - 1) < 0xE` | **BLOCKED** (class 0) |
| `0x8005CD2C` gameplay_effect_spawner | `0x8005D2B8` | `rec+0x2F == 5` | **BLOCKED** (class 0) |
| `0x80014844` contact_billboard_render | `0x800148E0` | `lbu rec+0x22; beqz` — **no flags test** | **RENDERED** |
| `0x80059E44` / `0x8005A0F0` | — | allocator / explicit ctor | creates it |
| `0x80057404` clear_gameplay_pool_on_reset | — | reset | clears it |

`flags = 0x20` has bits `0x01/0x02/0x04/0x08` all clear and `rec+0x2F = 0`, so the class is
excluded from every gameplay path by construction. The only consumers that touch it are the
renderer, the physics integrator, and the reset.

`rec+0x33` is written post-creation at exactly two sites (`0x800588AC`, `0x80058F74`), both
*inside* handlers that a record can only reach by having already passed a gate. A `0x5A`
record's flags therefore cannot change during its life.

### A second dispatch table, previously undocumented

The record updater has its own dispatch, independent of the walker's:

```
0x8005A8E8  lbu rec+0x2F ; idx = c - 1 ; if ((uint32_t)idx < 0xE) jr 0x8001B7F0[idx]
```

**`TABLE_8001B7F0`, 14 entries, indexed by `rec+0x2F - 1`.** This is the behaviour-class
dispatch — the route a *non-pickup* contact object would use to do anything. Class `0x00`
(95 of 129 ctor types, including `0x5A`) has no handler: index `-1` fails the unsigned range
test.

## What class 0x5A actually does

Only `contact_record_update` (`0x8005A308`) touches it. Per tick:

- **physics** — `rec+0x00/04/08 += rec+0x0c/10/14`, then `rec+0x10 += rec+0x18`. This is
  what proves table A's four outputs are velocity X/Y/Z plus a Y acceleration; the
  allocator's own header calls that "inferred, not proven". Table A row 22 (the spawner's
  stack argument) gives raw `31 / 3135 / 31 / 0` through decoder `0x800593E8` — **`accel_Y`
  decodes to 0, so the debris falls at constant speed rather than accelerating.**
- **lifetime** — `rec+0x22` decremented every tick (the store is in a branch delay slot, so
  it applies to *every* live record regardless of class). Initial value is randomised at
  allocation: `((rndbyte & 3) + 5) * 4` = **20..32 ticks**.
- **animation** — `rec+0x26` counts down from `rec+0x24` (5..8), stepping `rec+0x31` modulo
  `rec+0x30` (4 frames).
- **colour fade** — `rec+0x2E` is negative for this class, selecting the
  `>>5` / threshold-`0x20` arm: `rec+0x34/35/36 = (metaB+0x11/12/13 × rec+0x22) >> 5`, i.e.
  RGB ≈ (96, 48, 0) at full life fading to black. A brown/orange dust mote.
- **distance cull** — killed when squared distance from `[0x8009EC50/54/58]` exceeds
  `0x90000`.

Falling dirt from the tunnel ceiling. 33 fixed X positions, one constant spawn height,
respawned continuously — 717 allocations in one run.

## Corrections banked

**The spawner is not in a LEVEL02 overlay.** Overlay space is reused, so the recorded
`ra = 0x800B43F8` names an address, not a file. `tools/phase4_f02_overlay_spawner_pin.c`
scores every `OVL/*.BIN` against every plausible load base using the four overlay-space
callers the live run recorded (a 4-constraint match on 2 parameters):

```
1/4  OVL/LEVEL02_LEVEL1.BIN   base 0x800B39AC
4/4  OVL/LEVEL03_LEVEL.BIN    base 0x800B39A0   <== UNIQUE
1/4  OVL/LEVEL08_LEVEL.BIN    base 0x800B3994
```

At that base the call site reads `addiu a3,zero,0x5a` / `sw v0,16(sp)` (stackArg `0x16`) /
`jal 0x80059E44`, `ra = 0x800B43F8` — the static image and the live register agree.
`LEVEL02_LEVEL1.BIN` at its own best base has `a3 = 0x37` and a *variable* `a1`, which
contradicts the trace's constant `a1 = 0xE3A0`.

**`record+0x2E` sign mapping in `src_re/contact_alloc_80059e44.c` is inverted.** The
shipped code at `0x8005A088` is:

```
sel == 0 -> rec+0x2E = 0
sel == 1 -> rec+0x2E = +ctorType     (sb s3, in the bne delay slot)
else     -> rec+0x2E = -ctorType     (sb v0, v0 = negu s3)
```

The decompilation states the opposite. `metaB[0x5A]+0x0E = 2` → `rec+0x2E = 0xA6 = -0x5A`,
and the live pool shows exactly `0xA6`. **26 of 27** distinct `rec+0x2E` values observed
live reconcile against `metaB[∓value]` on both action id and flags; the 27th is `0x00`,
which is the `sel == 0` identity-erased case and matches many rows by construction.

This matters beyond bookkeeping: `rec+0x2E` is the only field that names a record's ctor
type at runtime, so it is what any live pool census must key on.

## Live verification

`tools/phase4_f02_debris_live_probe.py`, full replay of
`movies/Phase4/Interpreter/Any% Runs/LEVEL02_Tunnels.movie.json` (v4, `armed_while_paused`,
Interpreter, `reproducible: true`) at 60 Hz via `debugger.resume` + poll — never
`advanceToFrame`. Fresh instance per capture. 7,460 frames, 322 pool samples.

Instrumented **at the gate**: for each of the three flags gates, one execTrace watch on the
masking `andi` (capturing the raw flags and the record pointer) and one on the first
instruction reachable only on success. Passes are paired to their tests **by cycle**, not by
frame — the actor walker re-examines every slot once per actor and slots can be reallocated
mid-frame, so a `(frame, slot)` join manufactures false leaks (it produced exactly one, which
cycle-pairing dissolved).

| gate | bit | examined | flags-`0x20` examined | passed | leaks |
|---|---|---|---|---|---|
| pickup walker | `0x02` | 39,176 | 28,483 | 0 | 0 |
| contact-vs-actor | `0x04` | 117,760 | 96,186 | 1,054 | **0** |
| record update | `0x08` | 41,437 | 30,187 | 0 | 0 |

Nothing truncated; 0 unpairable passes.

- **1,254 live `ctor 0x5A` pool samples, every one with `flags = 0x20` and `rec+0x2F = 0`.**
- **154,856** examinations of flags-`0x20` records across the three gates; **zero** passed.
- Controls: debris spawner `0x800B43F0` fired **573** times, `a3 = 0x5A` on every one; the
  actor gate **passed 1,054 times**, demonstrating that a pass is detectable by this method.
- Player health `0x800A6594`: **5 writes in the entire run** — `0xBFC02BB4` (BIOS, ×2),
  `0x8004A88C` (×2), `0x80046C08` (×1). None on any contact-pool path.

## Residual — enumerated and bounded

1. **The `0x02` and `0x08` gates never passed for *any* class in this run.** Their negative
   for `0x5A` rests on the decoded mask plus the measured flags, not on a demonstrated pass.
   Bounded by the `0x04` gate, which passed 1,054 times under identical instrumentation — the
   method detects passes when they occur. Closing this needs a run containing a pickup
   collection and a live berry projectile.
2. **flags bits `0x10`, `0x20`, `0x40` have no located consumer.** `0x20` is set on 116/129
   rows, `0x40` on 68, `0x10` on 0 — `0x20` looks like a "row in use" marker rather than a
   behaviour bit, but that is inference. Debris carries `0x20` only.
3. **The consumer enumeration is scan-bounded.** The scan covers `lui`+`addiu`/`ori`/load/store
   base materialisation over resident text and found 11 sites. It initially found 10 and
   **missed the billboard renderer**, which uses `ori` — the scan was widened after that miss.
   A consumer reaching the pool through a *stored* pointer would still be missed. The LEVEL03
   overlay itself has **0** contact-array references.
4. **The colour/velocity decode is static-only.** The RGB ≈ (96,48,0) fade and the
   constant-fall-speed conclusion come from reading `0x8005A758`/`0x8005A824` and table A row
   22 through decoder `0x800593E8`; neither was sampled live.
5. **One level, one route.** Everything is measured on this single any% Tunnels movie. Class
   `0x5A` is used by other levels (`LEVEL10_LEVEL.BIN` has its own `a3 = 0x5A` call site) and
   those were not replayed. The *class* behaviour is level-independent because it is decided
   by `metaB[0x5A]`, which is resident data — but the claim "debris in Tunnels never damages"
   is bounded to this route.

## Artifacts

- `tools/phase4_f02_debris_class_bind.c` → `analysis/phase4_f02_debris_class_bind.json`
- `tools/phase4_f02_overlay_spawner_pin.c` → `analysis/phase4_f02_overlay_spawner_pin.json`
- `tools/phase4_f02_debris_live_probe.py` → `analysis/phase4_f02_debris_live_probe.json`
- superseded: `analysis/phase4_f02_contact_action_table.json`, `tools/phase4_f02_contact_action_table.c`
