---
kind: experiment
id: Experiment_-_Event_Sequencer_Trace
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: medium
legacy_source: ObsidianVault/Experiments/Experiment - Event Sequencer Trace.md
aliases:
  - "Experiment - Event Sequencer Trace"
---

# Experiment — Event Sequencer Trace (GAP-0033)

> Migrated from `ObsidianVault/Experiments/Experiment - Event Sequencer Trace.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — Event Sequencer Trace (GAP-0033)

> **Status: READY-TO-RUN — not executed this pass.** **UPDATE 2026-06-20:** static decode of the dispatch ([[Gameplay - Events and Triggers]] §Scene-handler dispatch) shows `fcn.80054964` is called with `a0 = current_scene_id` **every gameplay tick**, so the scene handler (LEVEL01 = the sequencer `0x800b3bb8`) is active in *normal* play. This **supersedes** the earlier "special shell-phase/in-encounter fixture" blocker — the trace needs only an **early-level save with an unexhausted script**, likely already obtainable. Operator-gated on the live fork (GAP-0001); no results are faked.

## Objective
Turn the statically-located scripted-spawn sequencer ([[Gameplay - Events and Triggers]]) into runtime evidence: observe the **script cursor advancing**, the **timer resetting**, and the **dispatcher executing** for **one opcode → one spawn**, and confirm seeds/pickups/warp share the cursor.

## Related
**Gap:** [[Gap Audit|GAP-0033]] (In Progress). **M6 notes:** [[Gameplay - Events and Triggers]] · [[Gameplay Systems Baseline]]. **Method:** [[Phase 4 - Reverse Engineering Operating Method|current RE operating method]] · [[API - determinism]].

## Hypothesis (exact, falsifiable)
The per-level event layer is a **bytecode script** interpreted in the Region-A overlay verb `0x800b3bb8` under `gameplay_state_machine fcn.8004ecd4`, where:
1. `[0x800822f4]` is the **program counter** — it **increments** (`lbu`, cursor++) as events fire;
2. each event reads packed coord bytes (`((b−0x80)<<4)`) + a type byte (`&3`) + a delay byte that **writes** `0x800b402c = byte + 0xc8` (the inter-event timer);
3. the **same `0x800822f4`** is read by the seed (ctors 0x7d–0x80) and grain (`fcn.80054eac`) handlers.

**Falsified if:** the cursor does not advance during scripted spawns, OR the timer write is unrelated to spawn cadence, OR seeds/pickups use a different cursor.

## Provenance / fork state (LOCAL-ONLY — GAP-0001)
Any result here is **local-only** on the dirty fork (`~/duckstation`, branch `external-debugger-control`, HEAD `296955321…-dirty`, no preserving remote) — see [[DuckStation Fork Reproducibility]]. Cite the fork commit + binary hash in any captured result; it is **not** off-machine reproducible until GAP-0001 closes.

## Addresses to watch (all source-verified)
| Addr | Role | Watch |
|---|---|---|
| `0x800822f4` | script-cursor / PC | WRITE + value (expect monotonic byte advance) |
| `0x800b402c` | inter-event timer (`= byte+0xc8`) | WRITE (expect resets on event) |
| `0x8008243c` | `main_shell_substate` (mod-6 dispatch) | value (confirm shell vs gameplay phase) |
| `0x80082504` | `current_scene_id` | value (which level/scene) |

## Functions to trace
| Fn | Role |
|---|---|
| `fcn.80054964` | callback dispatcher (table `0x8005494c`, ids 1..0x11) |
| `0x800b3bb8` | sequencer verb (LEVEL.BIN +0x218) |
| `0x800b3aec` | placement verb (+0x14c; clears timer, spawns 3× type-0x77) |
| `0x80042c70` / `0x80059e44` | resident spawner / place routine |
| `fcn.8004ecd4` | `gameplay_state_machine` (calls the dispatcher) |

## Procedure (turnkey, once a fixture exists)
1. **Fixture:** `loadState` the event-state fixture (see *Required fixture* below). `c.transport.sock.settimeout(30)` (CLAUDE.md — avoid hang on guest crash). Settle a few frames before arming watches.
2. **Arm watches (re-arm after every loadState):**
   `accessLog.addWatch 0x800822f4 (1 byte, WRITE)`, `accessLog.addWatch 0x800b402c (4 byte, WRITE)`.
3. **Arm traces:** `execTrace.addWatch 0x80054964`; `execTrace.addWatch 0x800b3bb8`.
4. `accessLog.run` / `execTrace.run` + `emulator.advanceFrames {frames: N}` across a known scripted spawn (a timed enemy wave / cutscene-style spawn).
5. **Collect:** `accessLog.get` (who wrote the cursor/timer + PC), `execTrace.get` (dispatcher hit sequence). Read cursor value before/after via `debugger` scalar read.
6. **Cross-check sharing:** repeat with a seed-plant + a grain pickup; confirm the **same `0x800822f4`** writer PCs.

## Expected observations (if hypothesis holds)
- `0x800822f4` writer = inside `fcn.80054964`/`0x800b3bb8`; value **increments** by the opcode length per event.
- `0x800b402c` written `= delay_byte + 0xc8` at each event; counts down between events.
- `fcn.80054964` hits with `callback id ∈ 1..0x11`; one hit precedes each spawn.
- Seed/grain handlers read (not write) the **same** cursor.

## Success criteria
≥1 opcode decoded end-to-end (cursor advance → spawn at the packed coords) **with** the timer reset observed — the GAP-0033 acceptance "interpreter loop identified with ≥1 trigger decoded."

## Failure criteria
Cursor static during spawns, OR dispatcher not hit, OR timer write uncorrelated → hypothesis falsified; record the actual writer/PC and revise the model (do **not** force-fit).

## Required fixture (REVISED 2026-06-20 — much less restrictive)
The scene handler runs **every gameplay tick** (dispatch keyed on `current_scene_id`), so the sequencer is active in *normal* play. Needed: a normal **in-level save EARLY in a level**, before its scripted spawns have fired, so cursor `0x800822f4` is **unexhausted**. No warp / shell-phase state required.
- **Acquisition:** capture a save right after a level loads (operator/interactive), **or** reuse an existing early-level save — first read `0x800822f4` / `0x800b402c` and `advanceFrames`; if the cursor advances, the save qualifies.
- A mid/late save may show an idle/exhausted cursor — try the earliest available.

## Fallback plan (if no fixture)
Stay plan-only (this note). Cheaper parallel runtime lane that needs **no** event-state fixture: [[Gameplay - Input and Movement]] (GAP-0037) — runs from any existing in-level save.

## What can be committed vs local-only
- **Committable (metadata):** this plan; decoded opcode *format* (field offsets/meanings); writer PCs as addresses; confidence notes.
- **Must stay local-only / NOT committed:** the save-state fixture, `accessLog`/`execTrace` dumps, screenshots, movies, RAM dumps ([[SYS_re_evidence_policy|evidence and preservation policy]]).

## See also
[[Gameplay - Events and Triggers]] · [[Gameplay Systems Baseline]] · [[API - accessLog]] · [[API - execTrace]] · [[API - loadState]] · [[API - experiment runner]] · [[Fixtures Index]] · [[DuckStation Fork Reproducibility]]
