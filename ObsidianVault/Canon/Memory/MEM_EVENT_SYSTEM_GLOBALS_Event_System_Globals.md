---
kind: memory
id: MEM_EVENT_SYSTEM_GLOBALS
aliases: [MEM_EVENT_SYSTEM_GLOBALS, "MEM - Event System Globals"]
address: multiple
name: Event_System_Globals
status: static_seen
confidence: confirmed
source_state: original_game
system: []
read_by: []
written_by: []
related_structs: []
evidence: []
src_paths: []
patch_policy: safe_to_read
---

# MEM_EVENT_SYSTEM_GLOBALS - Event System Globals

## Purpose

The RAM globals + dispatch tables behind the per-scene event/update system and warp ([[Gameplay - Events and Triggers]], [[Gameplay - Warp and Level Transition]]). All **static, EXE-read** (`tools/exe_read.py` on `SCUS_942.88`) unless noted; runtime confirmation is local-only ([[DuckStation Fork Reproducibility]] / GAP-0001).

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - Event System Globals
type: memory-structure
confidence: CONFIRMED
tags: [memory, gameplay, events, scripting, warp, milestone6, gap-0033, gap-0035]
---

# MEM — Event-system globals

> The RAM globals + dispatch tables behind the per-scene event/update system and warp ([[Gameplay - Events and Triggers]], [[Gameplay - Warp and Level Transition]]). All **static, EXE-read** (`tools/exe_read.py` on `SCUS_942.88`) unless noted; runtime confirmation is local-only ([[DuckStation Fork Reproducibility]] / GAP-0001).

## Globals
| Addr | Name / role | Writers | Readers | Conf |
|---|---|---|---|---|
| `0x80082504` | **`current_scene_id`** — selects scene handler **and** drives resource loads | shell-SM `0x8004fd0c` (via table `0x80077fa0`), warp-orch `0x8005222c` (`0x80052274/314/474`), loader `0x8003f524` | dispatch caller `0x8004f034`; loaders `0x8003axxx`; +many | CONFIRMED |
| `0x800822f4` | **shared PRNG/noise byte cursor** (pointer; `cursor += N`, byte at old cursor) | **seeded ONCE** `0x8005b900` ([[FUNC_8005B714]]) = `0x80017DB4` (resident noise table, [[Gameplay - Resident Event Stream]]); +104 resident & +10 overlay **increment** sites | 66 resident + overlay sequencer `0x800b3bb8` | CONFIRMED: walks resident pseudo-random table (coord-offset/variant source), NOT a script |
| `0x800822f0` | `G_DAT_ENTRY_COUNTER` (adjacent; same DAT-runtime cluster) | DAT parse path | — | from sym |
| `0x800822fc` | loaded-stage / `[gp+0x564]` (warp) | warp/load path | warp orchestrator | LIKELY ([[Finding - Level-warp mechanism]]) |
| `0x800b402c` | **event timer** (overlay-local; `= delay_byte + 0xc8`, ticks down) | sequencer `0x800b3bb8` (set), placement verb `0x800b3aec` (clear) | sequencer | CONFIRMED (static, doc) |

## Dispatch tables / functions
| Addr | Role | Conf |
|---|---|---|
| `0x80054964` | **scene-handler dispatcher**: `id=a0−1`; bound `<0x11`; `jr [0x8001b4fc + id·4]` | CONFIRMED (decoded) |
| **`0x8001b4fc`** | **scene-handler jump table** (17 one-based entries → trampolines → Region-A overlay verbs) | CONFIRMED |
| `0x8004f038` | sole dispatch caller (in `gameplay_state_machine fcn.8004ecd4`), `a0 = current_scene_id`, per-tick | CONFIRMED |
| `0x800b3bb8` | **scene-1 handler = scripted-spawn sequencer** (Region-A `LEVEL.BIN +0x218`) | CONFIRMED (static) |
| `0x80077fa0` | scene-id table `{0x11,1,3,2,6,0xa,0xb,4}` (shell-SM selection → scene_id) | from doc |
| `0x80042c70` / `0x80059e44` | resident object spawner / place routine (sequencer targets) | CONFIRMED (doc) |
| `0x80082498` | `G_DAT_BASE_PTR` — loaded LEVEL.DAT buffer; the cursor's universe; set once at `0x8003d4ac` | CONFIRMED (EXE-read) |
| `0x8001afb0` | per-stage resource-loader dispatch table ([[FUNC_8003CF2C]], 17 entries `0x8003cfc4…0x8003d1bc`) | CONFIRMED (EXE-read) |
| `0x8001cf3c/cf60/d2f4` | DAT parser [[FUNC_8001CDC0]] writes `G_DAT_ENTRY_COUNTER` (init 0, ++ per record); does **not** seed the cursor | CONFIRMED (EXE-read) |
| `0x8005b900` | **cursor seed** ([[FUNC_8005B714]] state-reset, entry `0x8005b70c`): `cursor = 0x80017DB4` (resident noise table) — the only seed; called from shell SM `0x8004fa40` @ `0x8004fdf0` with `a0=current_scene_id` (scene-init, init-once guard `0x800822f8`) | CONFIRMED (EXE-read) |

## Corrections (this work)
- The scene-handler `jr` table is **`0x8001b4fc`** — the docs' "`0x8005494c`" is padding before the dispatcher (EXE-read).
- `0x800822f4` is **not** an event-only cursor — it is the **shared byte-stream reader** (105 resident + 10 overlay sites); the event sequencer is one consumer among many.
- **CORRECTION (2026-06-20):** the earlier "no resident base-seed → seed in LEVEL.BIN overlay" is **wrong**. The cursor is seeded **once, in the resident EXE**, by [[FUNC_8005B714]] @ `0x8005b900` to a **resident table `0x80017DB4`** (not `DATbase+K`, not the overlay). Exhaustive proof + the data-source correction → [[Gameplay - DAT Event Stream]].

## Modding relevance
- `current_scene_id` is the single lever that re-points both the scene handler and resource loading → the heart of warp/level-transition mods ([[Gameplay - Warp and Level Transition]]).
- The byte-stream cursor + its (unfound) seed are the key to a **level-event editor** — once the on-disc script source is located, scripted spawns/timed events become editable.

## Related
[[Gameplay - Events and Triggers]] · [[Gameplay - Warp and Level Transition]] · [[Finding - Level-warp mechanism]] · [[FUNC_8001CDC0]] · [[FUNC_8003CF2C]] · [[Asset - LEVEL.DAT]] · [[MEM - Global memory map]] · [[DuckStation Fork Reproducibility]] · `tools/exe_read.py`


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Event System Globals.md`
- Migration status: copy-first Canon seed.
