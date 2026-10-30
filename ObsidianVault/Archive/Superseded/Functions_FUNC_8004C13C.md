---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8004C13C.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8004C13C.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8004C13C_unnamed.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8004C13C
type: function
addr: 0x8004c13c
confidence: CONFIRMED (bytecode VM; full ISA decoded/bounded, static + runtime LOCAL-ONLY)
tags: [function, gameplay, events, scripting, interpreter, path, mover, milestone6, gap-0033, gap-0034]
updated: 2026-06-21
---

# FUNC_8004C13C — per-object "object actor" bytecode VM (the GAP-0033 interpreter)

> **The authored event/trigger interpreter** [[Gap Audit|GAP-0033]] was hunting. A fetch/decode/
> dispatch/loop/persist-IP **bytecode VM** that runs a per-object opcode program to drive object
> motion, path-following, **player-proximity triggers**, conditional branches, and **native/overlay
> calls**. Decoded static (`tools/exe_read.py`) + cold-boot LEVEL01 runtime (**LOCAL-ONLY**, GAP-0001).
> System context: [[Event and scripting system]]. ISA decode hardened 2026-06-21.

## How it runs
Per gameplay tick the **mover-updater `0x8004d224`** (gameplay loop `0x8004ecd4` @ `0x8004f000`) iterates
the **mover-object array `0x8009f0d0..0x8009fd80`** and `jal 0x8004c13c` per qualifying object (`a0=object`, `0x8004d5e0`).

## Interpreter core
```
0x8004c144  s0 = object (a0)
0x8004c178  s5 = object[+0x80]      ; PROGRAM/DATA block (operand base; +0x14=step<<4 -> s4)
0x8004c17c  s1 = object[+0x70]      ; INSTRUCTION POINTER (into a RESIDENT program)
0x8004c1a0  object[+0x6c]-- if >0   ; wait counter A
0x8004c1cc  object[+0x60]--; bgez -> 0x8004c834 persist & EXIT (yield, still waiting) ; wait B
0x8004c1ec  FETCH lhu v0,0(s1); v0+=1  -> PRIMARY TABLE INDEX = stream_u16 + 1
0x8004c200  bound <26; s7=s1; jr [0x8001b2f4 + idx*4]   ; DISPATCH on data
   ... handler advances s1 by its operand width, j 0x8004c818 ...
0x8004c818  bne s1,s7,0x8004c1ec     ; loop while IP advanced; else fall to epilogue
0x8004c834  sw s1,112(s0)            ; PERSIST IP -> object[+0x70]
0x8004c838  SECOND DISPATCH: lhu v0,0(s1); v0-=5; bound<16; jr [0x8001b384 + idx*4]  (phase-2 motion)
```
IP persisted across frames; inter-opcode **waits** (object[+0x60]/[+0x6c]) pace the program over time.
**Two RNG sources**: primary noise cursor `0x800822f4` (opcodes 3/4) + alt cursor `0x800088f4` (opcode 15).

## Per-object field layout (decoded)
| off | field | off | field |
|--|--|--|--|
| +0x00 | type/id (LEVEL01: 9, 14 seen) | +0x44/48/49/4c | anim/param (op14/23) |
| +0x04/08/0c | position X/Y/Z | +0x50 | state/done flag (`=0x80000000` by op22) |
| +0x14 | heading (motion rotation) | +0x5c | flags (op13 masks; bit3 = path-set sel) |
| +0x1c/+0x24 | velocity components | +0x5e | path **waypoint index** (op5/9/11) |
| +0x28/+0x30 | accumulator pt (proximity branch) | +0x60 | **wait counter B** (u16; op2/3 set) |
| +0x34/38/3c | move **TARGET** X/Y/Z (op9 sets) | +0x6c | wait counter A (s16) |
| | | +0x70 | **IP** (resident program addr) |
| | | +0x80 | program/data block ptr |

## ISA — primary opcode table `0x8001b2f4` (26 slots; index = stream_u16 + 1)
| idx | handler | adv | role | conf |
|--:|---|--:|---|---|
| 0 | 0x8004c808 | jump | **backward jump** `s1 -= op*2` (loop) | CONFIRMED |
| 1,6,7,8,10,18,19,21 | 0x8004c818 | — | **terminator** (end movement loop → phase-2) | CONFIRMED |
| 2 | 0x8004c228 | +4 | set **wait** `object[+0x60]=op` | CONFIRMED |
| 3 | 0x8004c238 | +6 | **randomized wait** `=(noise&op1)+op2` (reads cursor 0x800822f4) | CONFIRMED |
| 4 | 0x8004c278 | +2 | **random-direction step** (2 noise bytes → sine table 0x80074970 → ±target) | CONFIRMED |
| 5 | 0x8004c32c | +2 | advance to next **path waypoint** → target (wrap+accumulate) | LIKELY |
| 9 | 0x8004c46c | +? | **set move-target from path waypoint** (`object[+0x5e]` idx into path array `[0x80096da0+…]`, stride 0xc, `<<5`) | CONFIRMED |
| 11 | 0x8004c47c | +4 | **seek/teleport to path endpoint** (snaps position+target) | LIKELY |
| 12 | 0x8004c59c | +4 | **CALL** `jr [0x8001b35c+(op-1)*4]` (9 subs, resident **+ overlay**) | CONFIRMED |
| 13 | 0x8004c664 | +6 | **flag mask** `flags[+0x5c]=(f&op1)\|op2` | CONFIRMED |
| 14 | 0x8004c68c | +6 | load **anim/clip descriptor** (op2 → table `0x80077e28`) | LIKELY |
| 15 | 0x8004c6cc | +4 | **conditional** `s3=((altcursor&op1)==0)` (reads 0x800088f4) | CONFIRMED |
| 16 | 0x8004c6fc | +4 | set program scratch `program[+0x1b]=op1>>4` | CONFIRMED |
| 17 | 0x8004c710 | +4 | **player-proximity TRIGGER** `s3=(dist²<op²)` (reads player 0x800a6500/08) | CONFIRMED |
| 20 | 0x8004c76c | +4 | **conditional forward branch** (if `s3`: `s1 += op1*2-2`) | CONFIRMED |
| 22 | 0x8004c790 | +2 | set **done/disable** `object[+0x50]=0x80000000` | CONFIRMED |
| 23 | 0x8004c7a0 | +6 | set byte params `[+0x48]/[+0x49]` | CONFIRMED |
| 24 | 0x8004c7bc | +4 | **call helper** `0x8005044c(op1, &pos)` | LIKELY |
| 25 | 0x8004c7d4 | +2 | conditional from global flag `0x800a6590/96` → `s3` | LIKELY |

**Status: 0 unknown** — all 26 slots resolve to a handler with grounded advance + primary effect (**21 CONFIRMED, 5 LIKELY** — the 5 LIKELY are opcodes 5/11/14/24/25, below).
- **CALL sub-table `0x8001b35c`** (op12, 9 entries): resident subs `0x80057a94/920/c74/b84` (object/sub-array updates, flag/Z state-change) + **overlay** subs `0x800b3d78/b70/bd4/dc8/f00` (level-specific behaviour; slot 4 returns a predicate). The VM's "invoke native action" escape hatch — ties the VM to per-scene overlay code ([[Event and scripting system]] Lane 1).
- **Phase-2 table `0x8001b384`** (16 entries, idx = stream−5): mode-setters `s6 ∈ {0..4}` → motion-apply at `0x8004c8ac` (heading-rotated fixed-speed `s4` advance of position toward target via sine table; embedded player-proximity branch). `s6`: 0=hold, 1=integrate-toward-target, 2=arrive-test, 3=arrive+disable, 4=brief-wait.

**Classification (inference from the opcode set):** a domain-specific **"object actor" VM** — movement/animation primitives + **conditional control flow** (predicates op15/17/25→`s3`, branch op20, loop op0) + a **native/overlay CALL** (op12). More than a path-follower; less than a general ISA (no arbitrary-memory arithmetic, no general registers/stack — all "variables" are fixed object/program fields). The **player-proximity (op17) + branch (op20) + CALL (op12)** combination is what makes it a genuine event/trigger interpreter.

## Program source = RESIDENT (corrects the prior "LEVEL.DAT opcode stream" claim)
**The bytecode PROGRAM is in the resident EXE**, not LEVEL.DAT (runtime-confirmed). A **17-entry resident
program-pointer table `0x80077af8`** → programs in `0x8007745c..0x800776ec`; the per-object IP
(`object[+0x70]`) is seeded to a program start (register-indexed — table has 0 absolute xrefs). LEVEL.DAT
supplies opcode-9's **path waypoints** ([[Finding - LEVEL.DAT records are object paths]]) + the object
spawn record (which selects program + path). ⇒ **editing a mover's *program* = EXE patch; editing its
*path* = LEVEL.DAT edit.** (Prior note said the opcode stream was in LEVEL.DAT — refuted; only the
waypoint DATA is.)

## Runtime evidence (RUNTIME-LOCAL-ONLY, GAP-0001)
- VM enters during gameplay (level04/06/07: 2-3 entries/5f; mid-level movers caught in inter-opcode wait).
- **Cold-boot LEVEL01 fixture** (movie `flik_to_level01_stall` → frame ~4260, scene_id=1): 2 active movers
  (types 9, 14), IPs **resident** (`0x80077490`, `0x800775fe`), running a repeating program
  `[op9 set-target][op17 player-proximity][op10 term][op0 backjump −10 → loop]` — 124 opcode fetches
  captured. Byte-exact static program dump at `0x800775fc` matches the runtime stream. → [[Experiment - Mover VM cold boot opcode trace]].

## Confidence
- VM structure / dispatch / persist-IP / object layout / 26-opcode ISA (0 unknown) — **CONFIRMED (static-exe)**.
- Program source = resident table 0x80077af8 (not LEVEL.DAT); LEVEL01 movers run op9/17 live — **CONFIRMED (runtime LOCAL-ONLY)**.
- 5 opcodes (5/11/14/24/25) + the exact program-selection seed site + overlay-CALL bodies — **LIKELY / OPEN (narrow follow-on)**. Promotion to CONFIRMED needs either full static decompilation of each handler's operand semantics or a runtime fixture that exercises them — the cold-boot LEVEL01 stream only fired op9/op17/op10/op0, so op5/11/14/24/25 stay LIKELY (non-blocking residual under GAP-0033's met acceptance bar).

## Related
[[Event and scripting system]] · [[Experiment - Mover VM cold boot opcode trace]] · [[Finding - LEVEL.DAT records are object paths]] · [[FUNC_8001CDC0]] · [[FUNC_800586B0]] · [[Gameplay - Events and Triggers]] · [[Gameplay - DAT Event Stream]] · [[Enemy relocation method]] · `tools/exe_read.py`
