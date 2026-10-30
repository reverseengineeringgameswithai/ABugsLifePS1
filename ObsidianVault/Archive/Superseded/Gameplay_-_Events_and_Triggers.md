---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Gameplay - Events and Triggers.md
aliases:
  - "Gameplay - Events and Triggers"
migration_action: split
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Gameplay - Events and Triggers.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Gameplay_-_Events_and_Triggers.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gameplay - Events and Triggers
type: core
updated: 2026-06-20
tags: [core, gameplay, events, scripting, milestone6, gap-0033, b10]
---

# Gameplay — Events & Triggers (GAP-0033 baseline)

> M6 keystone lane ([[Gap Audit|GAP-0033]]) — the per-level **scripted-spawn / event sequencer**. It is **statically located** but **not yet dynamically traced** (the interpreter loop runs only from states no current save reaches). This note consolidates the static anchors + the fixture/experiment to decode it. **Provenance:** STATIC = `SCUS_942.88` disasm (`docs/EXECUTABLE_AND_OVERLAYS.md` L159–208, L399–407, L553–556) + Findings; **DYNAMIC = local-only** ([[DuckStation Fork Reproducibility]] / GAP-0001). Upstream of GAP-0034 (PATH/AI), GAP-0035 (warp), and the gated LEVEL.DAT records.

> [!warning] MODEL CORRECTED (2026-06-20) — `0x800822f4` is the **resident PRNG/noise cursor**, NOT an event-script program counter.
> It is seeded once by [[FUNC_8005B714]] (scene-init) to a resident pseudo-random table `0x80017DB4`; consumers read its bytes as zero-mean coordinate offsets `((byte−0x80)<<4)` and low-bit type/delay selectors ([[Gameplay - Resident Event Stream]], [[Gameplay - Resident Noise and Ctor 0x71]]). The "bytecode script / PC" framing below is **superseded**: the spawns it drives are **noise-jittered**, not authored-scripted, and the cursor's data is **not** in LEVEL.DAT/overlay. The genuine static anchors (overlay verb `0x800b3bb8`, callback dispatcher `fcn.80054964` ids 1..0x11, timer `0x800b402c`, spawners `0x80042c70`/`0x80059e44`) remain valid; only the **"cursor = authored-script PC"** reading is corrected. ~~The real event/trigger interpreter remains UNFOUND~~ **→ INTERPRETER FOUND 2026-06-21: it is the per-object mover/PATH bytecode VM [[FUNC_8004C13C]] (table `0x8001b2f4`, IP=object[+0x70], program=object[+0x80], opcode 9 = LEVEL.DAT path-follow), a lane SEPARATE from both this noise cursor and the scene dispatcher. Full three-lane model + tables → [[Event and scripting system]].** The `fcn.80054964` "callback ids 1..0x11" are the 17 **scene_id** handlers (Lane 1, code not VM); this noise cursor is Lane 2; the authored VM is Lane 3.

## The sequencer (STATIC — documented "timed scripted-spawn/event sequencer")
- **Entry:** Region-A overlay verb **`0x800b3bb8`** (LEVEL01\LEVEL.BIN `+0x218`, 924 B), reached via **callback dispatcher `fcn.80054964`** (jump table `@0x8005494c`, default "UnHandled Callback Occured", callback ids `1..0x11`) called from **`gameplay_state_machine` `fcn.8004ecd4`**. ⇒ **event/callback-driven, not per-frame.**
- **Byte cursor `[0x800822f4]`** — read sequentially (`lbu`, cursor++). *(CORRECTED: the resident PRNG/noise cursor — see banner above; not an authored-script PC.)*
- **Opcode shape (observed):** 3 bytes → packed coords `((b − 0x80) << 4)` → `0x80059e44` (place/spawn); then a **type byte** (`& 3`) + a **delay byte** → resets countdown timer **`0x800b402c = byte + 0xc8`**.
- **Sibling placement verb `0x800b3aec`** (`+0x14c`): clears `0x800b402c` and spawns 3× **type-0x77** via resident spawner **`0x80042c70`** (slot table `0x8009c870`, 8×0x344).

**Leading hypothesis (SUPERSEDED 2026-06-20 → [[Gameplay - Resident Event Stream]]):** ~~a per-level bytecode script with `0x800822f4` as the PC~~ — the cursor is the resident noise table, so the "coord/type/delay opcode" bytes are **noise-derived jitter/variation**, not authored script. The callback/timer mechanism (overlay `+0x218`, `0x800b402c`, spawners `0x80042c70`/`0x80059e44`) is real, but it is **fed by noise**. Triggers appear **proximity-gated** (nearest-object search over `[0x80096da4]`, stride `0xc`, vs player `0x800a6500/6508`).

## Scene-handler dispatch (STATIC — enumerated from the EXE binary, 2026-06-20)
> Read directly from `SCUS_942.88` via `tools/exe_read.py` — reliable, reproducible, **not** disassembler-dependent. **Corrects the docs.**

**Dispatch site (CONFIRMED):** the gameplay state machine `fcn.8004ecd4` at **`0x8004f038`** calls `fcn.80054964` with **`a0 = current_scene_id` (`[0x80082504]`)** — decoded `lui a0,0x8008; lw a0,0x2504(a0); jal 0x80054964`. It sits in a straight-line per-tick update run (immediately after the type-0x3f pickup dispatch [[FUNC_80053814]] at `0x8004f028`) ⇒ **LIKELY invoked every gameplay tick** for the active scene.

**Dispatcher `fcn.80054964` (CONFIRMED, decoded):** `id = a0 − 1`; bound `id < 0x11` (17, else "UnHandled Callback Occured"); `jr [0x8001b4fc + id·4]`. **The real `jr` table base is `0x8001b4fc`** (17 entries) — *the docs' "jump table @0x8005494c" is wrong; `0x8005494c` is padding/epilogue before the function.* Index is **1-based** (`current_scene_id` ∈ 1..0x11; scene-id values per table `0x80077fa0`).

**The 17 per-scene handler verbs** (table `0x8001b4fc` → trampoline at `0x80054994+` → `jal` a Region-A overlay verb in LEVEL01\LEVEL.BIN, base `0x800b39a0`):

| scene id | overlay verb | LEVEL.BIN off | note |
|--:|---|--:|---|
| 1 | **`0x800b3bb8`** | +0x218 | **the scripted-spawn sequencer** (below) |
| 2 | `0x800b3b84` | +0x1e4 | |
| 3 | `0x800b3e88` | +0x4e8 | |
| 4 | `0x800b3f3c` | +0x59c | |
| 5 | `0x800b3d78` | +0x3d8 | |
| 6 | `0x800b3bbc` | +0x21c | = sequencer+4 (alt entry) |
| 7 | `0x800b42ac` | +0x90c | |
| 8 | `0x800b3c74` | +0x2d4 | |
| 9 | `0x800b3de8` | +0x448 | |
| 10 | `0x800b3c1c` | +0x27c | |
| 11 | `0x800b3b58` | +0x1b8 | |
| 12 | `0x800b3f00` | +0x560 | |
| 13 | `0x800b3b2c` | +0x18c | |
| 14 | `0x800b3c70` | +0x2d0 | |
| 15 | `0x800b3c04` | +0x264 | |
| 16 | `0x800b3c98` | +0x2f8 | |
| 17 | `0x800b3f48` | +0x5a8 | |

**Implications (RE):**
- This is the **per-scene event/update-handler dispatch** — `current_scene_id` selects which overlay verb runs as that scene's handler. For LEVEL01 (scene 1) that handler **is** the sequencer (`0x800b3bb8`).
- **Direct GAP-0035 link:** the warp lever sets `current_scene_id` ([[Finding - Level-warp mechanism]]); `0x80082504` is exactly the value that selects this scene handler — warp and event-dispatch share one global.
- **REVISES the fixture requirement (below):** the scene handler runs during *normal* gameplay, so the sequencer + cursor `0x800822f4` + timer `0x800b402c` are active in ordinary play — a **normal in-level save with an unexhausted script** should suffice to observe cursor/timer activity; no special shell-phase state is required. (To confirm at runtime — local-only.)
- Single static caller + dynamic `a0` ⇒ *which* scene handler fires is purely `current_scene_id`-driven (data, not a static immediate).
- **Confidence:** dispatch decode + table + verb enumeration = **CONFIRMED (static, EXE-read)**; "runs every gameplay tick" = **LIKELY** (in the SM's update sequence; enclosing-state gating not fully traced); per-verb behaviour beyond scene-1 = **Unknown**.

## Level-exit / transition trigger chain (GAP-0033, decoded 2026-06-21)
> One per-scene overlay verb's level-exit path is now **decoded end-to-end** (static EXE+overlay-read + a runtime correction, LOCAL-ONLY GAP-0001). Detail + evidence: [[Experiment - In-game warp trigger]] Pass-3, [[FUNC_8004A700]], [[FUNC_8004ABF4]].

**The three "transition initiators" `0x800496d8/a8b4/b3c0` are `sh [0x800823a0]` STORE-PCs, not functions** (`--store-ea 0x800823a0` = 16 writers). Their enclosing functions: **`0x80048138`** (type 1), **`0x8004a700`** (type 2 — [[FUNC_8004A700]]), **`0x8004abf4`** (type 6 — [[FUNC_8004ABF4]]). No overlay or EXE site `jal`s the store-PCs (they are mid-function).

**An overlay verb DOES call a resident initiator — PROVEN (was inferred).** `0x8004a700` (type 2) is `jal`'d from overlay scene verbs: **`0x800b3e94`** (LEVEL06\LEVEL.BIN = the scene-3 table verb `0x800b3e88`+0xc) and **`0x800b4ae0`** (LEVEL04\LEVEL1.BIN). The scene-3 verb `0x800b3e88` (an **interior case-label** of the overlay's main handler) calls `FUNC_8004A700(a2=&sp16, **a3=3**)` then sets `[0x800823a0]=2`+fade `[0x80082470]=60`. **`a3` = an explicit destination/mode** (LEVEL06=3, LEVEL04=0); the type-2 overlay path **carries a destination**.

**Native (resident) level-exit for normal levels = a per-tick state machine, not a one-shot** (runtime-corrected): the gameplay update path at **`0x8004f0e8`** calls `0x8004abf4` iff `[0x800a657c]==0 && [0x800a6594]≥0` — but runtime shows that gate is **OPEN during normal play** and `0x8004abf4` runs **every tick** (so those fields are a *transitions-allowed* precondition, **not** the trigger). `0x8004abf4` operates on the active-special-actor `[0x80090748]` (NULL mid-level → early-exit) and contains the type-6 **commit countdown `[0x8008223c]`→5** (gated by `[0x8009b889]&0x20==0 && scene_id!=16`), dormant in normal play.

**Destination is shell-resolved; type-6 carries none.** `0x8004abf4` writes only `[0x80082444]`,`[0x800823a0]=6`,`[0x80082470]=30`. The shell SM resolves the destination at `0x8004fda0`: `dest = scene_table[ [0x8008245c] ]` (`@0x80077fa0`), or **forced to scene 16** when `[0x8008225c]!=0` (the map/results override; `scene_table[16]=0xffffffff`). `[0x8008245c]` is written **only by the shell SM (7 sites)** — never by gameplay/overlay ⇒ destination selection is a **shell-phase** act. This is why a forced `[0x800823a0]=6` mid-gameplay lands on invalid scene 16 (GAP-0035 residual).

**Chain (one decoded path):** overlay verb interior case `0x800b3e88` → `FUNC_8004A700(a3=dest)` *(type-2)* **OR** live exit-actor `[0x80090748]` → per-tick `0x8004abf4` countdown `[0x8008223c]`→5 *(type-6)* → set `[0x800823a0]` + fade → fade handler (`0x8004f230`-region) → gate `[0x8008224e]` flips → shell SM → destination select (`0x8004fda0`) + orchestrator [[FUNC_8005222C]] resource-load → scene-init [[FUNC_8005B714]] → spawn [[FUNC_80046B20]]. **This is distinct from the scripted-spawn sequencer below** (that is the scene-*update* verb; the *exit* path is the type-2/6 initiators).

## Known event/state variables
| Address | Role | Source |
|---|---|---|
| `0x800822f4` | **resident PRNG/noise cursor** (seeded to `0x80017DB4`; NOT an event PC — [[Gameplay - Resident Event Stream]]) | pickup/contact constructors + grain handler |
| `0x800b402c` | inter-event countdown timer (`= byte + 0xc8`) | sequencer verb |
| `fcn.80054964` | callback dispatcher (ids 1..0x11, table `0x8005494c`) | overlay verb path |
| `0x800b3bb8` / `0x800b3aec` | sequencer verb / placement verb (Region-A overlay) | LEVEL.BIN +0x218 / +0x14c |
| `0x80042c70` / `0x80059e44` | resident spawner / place routine (slots `0x8009c870`) | spawn path |
| `0x8004ECD4` | `gameplay_state_machine` (calls the dispatcher) | sym + disasm |
| `0x800823A0` / `0x80082504` / `0x8008243c` | `master_game_state` / `current_scene_id` / `main_shell_substate` | sym (state ledger) |

## Script cursor `0x800822f4` — byte-stream model + seeding (STATIC, EXE-read 2026-06-20)
> [!warning] SEEDING RESOLVED + RENAMED (2026-06-20). The "no resident base-seed → LEVEL.DAT/overlay source" claims in this section are **wrong**. There **is** a resident seed: [[FUNC_8005B714]] @ `0x8005b900` sets `cursor = 0x80017DB4` (a resident pseudo-random table), once per scene-init. The byte stream is **resident noise**, not LEVEL.DAT and not an authored script. Authoritative model: [[Gameplay - Resident Event Stream]] + [[Gameplay - Resident Noise and Ctor 0x71]]. The candidate `0x80055390` "rewind" guess below is also superseded. Text retained for history.

> `tools/exe_read.py --xref 0x800822f4` (gp-relative + absolute scanner) + instruction decode.

**CONFIRMED: `0x800822f4` is a shared sequential byte-stream READ cursor (a pointer).** The universal idiom at all **105 resident writer sites** is:
```
lui v1,0x8008 ; lw v1,0x22f4(v1)   ; v1 = cursor (pointer to current byte)
addiu v0,v1,N                       ; advance by N (N = 1/2/3/...)
lui at,0x8008 ; sw v0,0x22f4(at)    ; cursor += N   (post-increment)
lbu a?,0x0(v1)                      ; read the byte AT the old cursor
```
Read/incremented across `0x80028xxx`–`0x8005cxxx` — the DAT-parse + pickup/seed/object/event-handler code (**66 readers, 105 increment-writers**). The event sequencer (`0x800b3bb8`) reads 3 coord + type + delay bytes from this same cursor. It is **`G_DAT_ENTRY_COUNTER`(`0x800822f0`)+4** — part of the DAT-runtime globals cluster. ⇒ the cursor is **not event-only**; it is the project's **shared level-data byte-stream reader**.

**Seeding (initialization to a base) — NOT in the resident image.** All 105 resident writers are *increments* (`cursor += N`); **none sets the cursor to a fresh stream base** (verified by exhaustive xref + decode). The seed is therefore one of:
- (a) **an overlay** (Region-A `LEVEL.BIN` / Region-B code) — outside `SCUS_942.88`, not scannable with this tool;
- (b) **indirect / struct-block init** (e.g. the DAT parser [[FUNC_8001CDC0]] writes the whole `0x800822xx` globals via a base-pointer `sw rX,off(ptr)` — invisible to an absolute-`0x8008` scan);
- (c) a `cursor = base ± K` site just outside the increment idiom — one candidate is `0x80055390` (`cursor = v1 − 1500`, a backward seek/rewind).

**On-disc source (LIKELY, not yet proven):** the consumers are the **DAT-object / pickup / seed constructors** and the cursor lives in the **DAT-runtime globals** → the byte stream is **most likely embedded in LEVEL.DAT** (per-object parameter/command bytes following the object records; ties to [[Finding - LEVEL.DAT records are object paths]] / B10 and [[Asset - LEVEL.DAT]]). A LEVEL.RAW chunk is the alternative — undetermined. **Full source analysis** (parser families, DATbase = loaded LEVEL.DAT buffer, exhaustive no-resident-seed proof, LEVEL.DAT favored HIGH): → **[[Gameplay - DAT Event Stream]]**.

**Confidence:** byte-stream cursor + 105-site increment idiom = **CONFIRMED (static)**; no-resident-seed = **CONFIRMED (static, exhaustive xref)**; overlay/indirect seed + LEVEL.DAT source = **LIKELY (inference)**.

**Precise next RE question:** *which instruction first sets `0x800822f4` to a base pointer at level load, and what does that base point at?* → static: disassemble the `LEVEL.BIN` overlay (Region-A) + check [[FUNC_8001CDC0]] for an indirect `sw rX,4(ptr)`; or runtime (local-only): `accessLog.lastWriter` / write-watch `0x800822f4` across a fresh level load to capture the seeding PC + value. See [[MEM - Event System Globals]].

## Seed / pickup / warp relationships (the "common wall")
The **same cursor `0x800822f4`** is read by:
- **Seeds** — planting ctors 0x7d–0x80 consume per-piece bytes from it ([[Seed planting system]]).
- **Pickups** — grain handler `fcn.80054eac` reads it; type-0x3f dispatch [[FUNC_80053814]] → contact walker [[FUNC_800586B0]] (`0x800b0d18`).
- **Warp** — the load-substate case of the same shell SM (`[0x8008243c]=5`, [[Finding - Level-warp mechanism]]).
- **Gated LEVEL.DAT records** — negative/path records (rec1 consumer `0x8004c400`, waypoints `<<5`) are runtime-event-gated; only rec1 was live-traced ([[Finding - LEVEL.DAT records are object paths]]).

⇒ This is why GAP-0033 is **the common wall behind GAP-0029 / 0034 / 0035** — they all reduce to entering this script/callback machinery.

## What's missing (updated 2026-06-21)
- ~~The authored event/trigger interpreter~~ **— FOUND (2026-06-21): the mover/PATH bytecode VM [[FUNC_8004C13C]]** ([[Event and scripting system]] Lane 3). Remaining follow-on: the full 26-opcode ISA (only opcode 9 = path-follow decoded) and the heap seed site that fills object[+0x70]/[+0x80] from a LEVEL.DAT record on object creation (the [[FUNC_8001CDC0]] parse/init path).
- **Cursor seeding:** ~~where `0x800822f4` is initialized~~ **— RESOLVED: sole seed `0x8005b900` in [[FUNC_8005B714]] → resident noise table `0x80017DB4`** ([[Gameplay - DAT Event Stream]]); runtime-confirmed this pass (cursor reads inside the `0x80017DB4` region during play). The cursor is **noise/param (Lane 2)**, not the authored interpreter.
- **Opcode → effect** confirmed at runtime (the cursor/timer trace — now reachable from a normal early-level save, see [[Experiment - Event Sequencer Trace]]).
- **Per-verb behaviour for scenes 2–17** (only scene-1 = the sequencer is detailed); the proximity-gate exact compare.
- *(Resolved this pass, static: the dispatch mechanism, the real jump-table address `0x8001b4fc`, the 17-verb handler map, and that the dispatch index = `current_scene_id`.)*

## Dynamic evidence
**None yet — local-only and unreached.** Every save is mid-gameplay; the callback/sequencer path is never entered, so no `execTrace`/`accessLog` capture exists. Any future capture is **local-only** (dirty fork, GAP-0001) until reproduced. The full, turnkey trace is specified and **ready-to-run** in **[[Experiment - Event Sequencer Trace]]** — it is blocked only on obtaining the event-state fixture (below), not on analysis. *(Addresses below re-verified 2026-06-20 as source-supported across ≥5 docs/notes each; not provisional.)*

## Fixture requirement (REVISED 2026-06-20)
The scene handler runs **every gameplay tick** (per the dispatch above), so the sequencer is active in *normal* play — the earlier "special shell-phase / in-encounter" framing is **superseded**. What's actually needed is a normal **in-level save with an *unexhausted* script** (cursor `0x800822f4` not yet run past the level's events): the per-tick handler will then advance the cursor + reset the timer as events fire. Target a save **early in a level** (before scripted spawns trigger); a late save may show an idle/exhausted cursor. This is far more obtainable than previously documented — it does **not** require the warp or a shell-phase state.

## Next experiment plan (local-only — cite fork commit `296955321`)
1. **Get the fixture:** capture a save during a known scripted moment (a timed enemy wave / cutscene-style spawn), or reach a fresh level via the warp (GAP-0035).
2. `accessLog` **write-watch** `0x800822f4` (PC advance) + `0x800b402c` (timer reset) across the event.
3. `execTrace` `fcn.80054964` (dispatcher) + the `+0x218` verb `0x800b3bb8` → capture **one opcode → one spawn** (the ≥1-trigger-decoded acceptance bar).
4. Map callback ids `1..0x11` (table `0x8005494c`) to verbs.
5. Record fixture/frame/PC/observed-output + fork state per [[DuckStation Fork Reproducibility]]; label local-only.

## Relationship to M4/M5 findings
Spawned objects are placed in **world space** → depends on the unresolved **chunk-34 world-origin** (GAP-0023, [[Asset - Chunk 34 Master Mesh]]); editor preview of spawn positions depends on the **camera follow-law** (GAP-0028, [[Core - Camera and Projection]]); event-gated CD loads tie to [[Core - CD Streaming and Caching]] (GAP-0029).

## Related
[[Experiment - Event Sequencer Trace]] · [[Gameplay Systems Baseline]] · [[Seed planting system]] · [[Finding - LEVEL.DAT records are object paths]] · [[Finding - Level-warp mechanism]] · [[FUNC_80053814]] · [[FUNC_800586B0]] · [[MEM - Player state 800A6500]] · [[Core - CD Streaming and Caching]] · [[Asset - Chunk 34 Master Mesh]] · [[DuckStation Fork Reproducibility]]
