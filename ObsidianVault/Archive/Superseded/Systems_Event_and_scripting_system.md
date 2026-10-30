---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Event and scripting system.md
aliases:
  - "Event and scripting system"
migration_action: split
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Event and scripting system.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Event_and_scripting_system.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Event and scripting system
type: system
confidence: interpreter IDENTIFIED (static, airtight) + live (runtime LOCAL-ONLY); full ISA + disc-origin OPEN
tags: [system, gameplay, events, scripting, interpreter, milestone6, gap-0033, gap-0034, b10]
updated: 2026-06-21
---

# Event & scripting system (GAP-0033) — the three lanes

> **Headline (2026-06-21):** the "authored event/trigger interpreter" GAP-0033 was hunting **EXISTS and is identified** — it is the **per-object mover/PATH bytecode VM [[FUNC_8004C13C]]**. The earlier hypothesis "no data-driven interpreter; events are overlay-code only" was **adversarially REFUTED** in this pass. ABL's event/trigger machinery is **three distinct lanes**; only the third is a true data-driven VM. All decode = static EXE-read (`tools/exe_read.py`); liveness = runtime **LOCAL-ONLY** ([[DuckStation Fork Reproducibility]] / GAP-0001).

## Lane 1 — per-scene update handlers (scene_id-dispatched CODE; NOT a VM)
- **Dispatcher [[Gameplay - Events and Triggers|FUNC_80054964]]**: `id = scene_id−1; bound < 17; jr [0x8001b4fc + id·4]` → 17 resident trampolines (`0x80054994 + id·0x10`, each `jal <overlay verb>; j 0x80054a9c`). Argument = **`a0 = current_scene_id [0x80082504]` only** (no object/param pointer; verbs reach state via absolute globals + the noise cursor). OOB scene_id just returns (no "UnHandled Callback" string — corrects the docs).
- The index is **scene_id, not a data byte** → this is a **jump table of CODE handlers**, one per level, **not** a bytecode interpreter. Each slot is a real function prologue **only in that scene's own overlay** (id1 ⇒ LEVEL01, id2 ⇒ LEVEL02, id3 ⇒ LEVEL03; the table is a UNION across the 17 level variants at base `0x800b39a0`).
- The LEVEL01 handler **`0x800b3bb8`** (scene-1) = a **timer+flag-gated spawn sequencer**: ticks timer `[0x800b402c]`; gates on `[0x800910a4]==0 && ([0x800a0ac0]&0x4001)==0x4001`; reads 3 noise bytes for spawn coordinate jitter; calls spawners `0x80059e44`/`0x80050d1c`; runs a proximity search (`[0x80096da4]` stride 0xc vs player `0x800a6500`). **No sub-opcode VM** (1 `jr` = epilogue, 0 `jalr`; the only `mult` are squared-distance terms). The *authored* part is the overlay CODE + fixed world-origin pointers; the *variation* is resident noise. → [[Gameplay - Events and Triggers]].

## Lane 2 — resident noise cursor `0x800822f4` / table `0x80017DB4` (param jitter; NOT opcodes)
- Seeded **once** by [[FUNC_8005B714]] (`0x8005b880`/`0x8005b900`) to the resident table `0x80017DB4` (~2052 B, entropy 7.91, mean 0x80). `0x80017DB4` is **referenced exactly once** in the whole image — consumers reach it only via the cursor pointer.
- An exhaustive scan of **all 66 cursor readers** found **zero** that use a cursor byte as a `jr`/`jalr` opcode index — every consumer uses bytes as **signed coordinate offsets `(b−0x80)<<4`** or **low-bit gate/variant scalars**. So this lane is a shared **PRNG/noise/dither** source, **not** a bytecode stream. → [[Gameplay - DAT Event Stream]] / [[Gameplay - Resident Event Stream]].
- **Runtime (LOCAL-ONLY):** at level02.sav play, `cursor = 0x80018034` (inside `[0x80017db4..0x800185b8]`), DATbase `[0x80082498]=0x8015e22c` valid, cursor advances **~1 byte / several frames** (not per-tick) ⇒ sporadic noise consumption, not a script PC. (Closes the prior open question "does the cursor really start at 0x80017DB4 at runtime".)

## Lane 3 — the AUTHORED bytecode interpreters (the real GAP-0033 answer)
### 3a. Per-object mover/PATH verb VM → [[FUNC_8004C13C]]
A textbook fetch/decode/dispatch/loop/persist-IP **bytecode interpreter**:
- Driven per-tick by the **mover-updater `0x8004d224`** (gameplay loop `0x8004ecd4` @ `0x8004f000`), which iterates the **mover-object array `0x8009f0d0..0x8009fd80`** and calls the VM on each (`0x8004d5e0 jal 0x8004c13c`, `a0 = object`).
- Per object: **program block = object[+0x80]** (s5), **instruction pointer = object[+0x70]** (s1). Inter-opcode **delay counters object[+0x60]/[+0x6c]** pace opcodes over time (the VM *waits* N frames between opcodes — why path-movers fetch slowly).
- **FETCH** `lhu opcode,0(s1)` (`0x8004c1ec`) → `+1` ⇒ **primary table index = stream_u16 + 1**; **bound `< 26`** (`0x8004c200`) → **`jr [0x8001b2f4 + idx·4]`** (`0x8004c220`). **LOOP** `bne s1,s7` (`0x8004c818`); **PERSIST IP** `sw s1,112(s0)` (`0x8004c834`); then a **phase-2 dispatch** `jr [0x8001b384 + (stream−5)·4]` (`0x8004c838`) applies heading-rotated motion toward target. Backward-jump opcode (`s1 −= op·2`) + conditional branch (op20) + predicates (op15/17/25→`s3`) ⇒ genuine control flow.
- **Full ISA decoded/bounded (0 unknown; 21 CONFIRMED + 5 LIKELY) → [[FUNC_8004C13C]]:** movement (op9 set-target-from-waypoint, op5/11 path nav, op4 random-walk via sine `0x80074970`), **waits** (op2/3, op3 reads noise cursor `0x800822f4`), **player-proximity TRIGGER** (op17: `dist²<op²` vs player `0x800a6500`), **conditional branch** (op20 on `s3`), **flags** (op13/16/22), **anim/params** (op14/23/24), and a **CALL opcode (op12 → `jr [0x8001b35c+(op-1)*4]`, 9 resident + overlay subs)** — the VM's native/overlay escape hatch (ties to Lane 1). Two RNG sources: `0x800822f4` (op3/4) + alt `0x800088f4` (op15).
- **Opcode 9 → `0x8004c46c`** = the path-follower (the `rec1` consumer `0x8004c400` of [[Finding - LEVEL.DAT records are object paths]], prior-runtime-proven). It reads the move-**target** from the LEVEL.DAT path waypoints (`object[+0x5e]` index, stride 0xc, `<<5`).
- **PROGRAM SOURCE = RESIDENT (corrected 2026-06-21):** the opcode **program** (IP `object[+0x70]`) is in the **resident EXE** — a 17-entry program-pointer table `0x80077af8` → programs `0x8007745c..0x800776ec`; the object IP is seeded to a program start. LEVEL.DAT supplies only opcode-9's **path waypoints** + the object spawn/selection. ⇒ edit a mover's *program* = EXE patch; edit its *path* = LEVEL.DAT. **(Refutes the prior "opcode stream in LEVEL.DAT" reading — only the waypoint DATA is on-disc.)**
- **Runtime (LOCAL-ONLY):** VM live in level04/06/07; **cold-boot LEVEL01 fixture** ([[Experiment - Mover VM cold boot opcode trace]]) captured a fresh stream — 2 movers (types 9/14) run a repeating `[op17 proximity][op9 set-target][op0 backjump→loop]`, IP resident `0x800775xx`, 124 fetches; static program dump byte-exact with runtime.

### 3b. Contact-action dispatch → [[FUNC_800586B0]]
A 2nd data-field `jr`-dispatch: `lhu action_id,−2(s2)` from a contact record → `bound < 117` → **`jr [0x8001b570 + (action−2)·4]`** (`0x8005882c`). Table `0x8001b570` (most actions → default `0x800589d4`; distinct `0x80058834/54/64/0x800588b0`). The authored **contact-trigger effect** lane (sounds/markers/counters; one action reaches the transition initiator [[FUNC_8004A700]]).

### Not an interpreter (ruled out)
- **Type-0x3f dispatch** ([[FUNC_80053814]]) is **value-compare based** (`lw` data-array `0x80078d84` indexed by the type byte + `beq`/`bne` chains, **no `jr`**). The 16-entry table `0x8001b424` has **0 xrefs** (dead / not a live `jr` table). So there is no third VM here.

## Dispatch-table map (the "callback id" tables)
| Table | Index source | Entries | Role | Kind |
|---|---|--:|---|---|
| `0x8001b4fc` | `scene_id` (1..17) | 17 | per-scene overlay update handlers (Lane 1) | CODE jr (not a VM) |
| `0x8001b2f4` | mover **opcode** (object[+0x70] stream, idx=stream+1) | 26 | mover/object-actor VM (Lane 3a) | **DATA-driven VM** |
| `0x8001b384` | phase-2 sub-opcode (idx=stream−5) | 16 | motion-mode dispatch (s6) | DATA-driven |
| `0x8001b35c` | opcode-12 operand (idx=op−1) | 9 | VM CALL → resident + overlay action subs | DATA-driven |
| `0x8001b570` | contact **action_id** (record field) | 117 (bound) | contact-action effects (Lane 3b) | **DATA-driven** |
| `0x8001b424` | — | 16 | type-0x3f candidate — **dead (0 xrefs)** | not used |

## GAP-0033 disposition — model COMPLETE (recommend Verified)
The acceptance bar (interpreter identified + ≥1 trigger decoded) is exceeded; the **full-closure** criteria are now met (2026-06-21):
- **Interpreter loop IDENTIFIED + fully modeled** (Lane 3a `FUNC_8004C13C`): all **26 primary opcodes decoded/bounded (0 unknown)**, phase-2 motion table + opcode-12 CALL sub-table enumerated, object field layout documented.
- **Multiple authored triggers decoded with reproducible evidence:** opcode 9 (path-follow → LEVEL.DAT waypoints, prior-runtime-proven), opcode 17 (**player-proximity trigger**), opcode 12 (overlay CALL), opcode 20 (conditional branch).
- **Fresh cold-boot opcode stream captured** ([[Experiment - Mover VM cold boot opcode trace]]) — LEVEL01 movers run `[op17][op9][op0-loop]` live; a non-transition authored trigger is reproducible from a documented route.
- **Disc origin resolved:** programs are **RESIDENT** (table `0x80077af8`); LEVEL.DAT supplies path waypoints + object selection.
- **Narrow residuals (follow-on, do not block closure):** 5 LIKELY opcodes (5/11/14/24/25) need full confirmation; the exact register-indexed program-selection seed site (object[+0x70] writer); the overlay-CALL targets' bodies (outside SCUS_942.88); the contact-action (Lane 3b) per-action effect map.

## Related
[[FUNC_8004C13C]] · [[Gameplay - Events and Triggers]] · [[Gameplay - DAT Event Stream]] · [[Gameplay - Resident Event Stream]] · [[Finding - LEVEL.DAT records are object paths]] · [[FUNC_800586B0]] · [[FUNC_8001CDC0]] · [[FUNC_8005B714]] · [[FUNC_80053814]] · [[Gameplay - Warp and Level Transition]] · [[Gap Audit]] · `tools/exe_read.py`
