---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Replay headline experiments.md
aliases:
  - "Playbook - Replay headline experiments"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Replay headline experiments.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Replay headline experiments
type: playbook
date: 2026-06-21
gaps: [GAP-0040, GAP-0001, GAP-0038]
tags: [playbook, determinism, replay, m7, verification]
---
# Playbook — Replay headline experiments

> Turn a headline finding into a **one-command** replay over the custom DuckStation API, so it can be re-checked on demand (GAP-0040) without committing copyrighted media. The pattern behind `tools/trace_spawn_floor.py`.

## When to use
A finding is `CONFIRMED` but rides a manual, hard-to-reproduce session. Convert it to a tracked script that authenticates, **asserts the game serial**, loads a named fixture, captures minimal evidence, and prints a self-checking verdict.

## Preconditions
- Isolated instance up (never the operator's own DuckStation):
  `~/duckstation/scripts/debugger-client/launch_debugger_instance.sh start --disc "<pristine>.cue" --port 23460 --no-fastboot`
  → token `debugger-1000`, config `/tmp/duckstation-debugger`.
- A fixture (`.sav` or `.movie.json`) that reaches the state. **Do not commit it** — name it + its frame in the note (evidence rubric).

## The pattern (what every replay script does)
1. **Connect + harden:** `DebuggerClient("127.0.0.1",23460,"ws").authenticate("debugger-1000")`, then `c.transport.sock.settimeout(60)` — the socket hangs forever on a guest crash otherwise.
2. **Assert identity:** `debugger.status` → refuse unless `game_serial == "SCUS-94288"`. (Never drive an unknown instance.)
3. **Reach the state:** `emulator.loadState {path, pause_after_load:true}` **or** `movie.load` + `movie.startPlayback {load_start_state:true}`; then `emulator.advanceFrames {frames:N}` (param is **`frames`**, capped 600/call — chunk it) to settle a coherent frame; `debugger.pause`.
4. **Re-arm watches AFTER load** — `loadState` clears `accessLog`/`execTrace`/`transferLog`; for gated captures, prefer `trace.armWhen` so logs start only at the milestone. `accessLog.lastWriter` returns nothing until a write-watch has been armed and a frame advanced.
5. **Capture minimal evidence:** `debugger.snapshot`, `gpu.pickObject {x,y}` or `gpu.traceRegion {x,y,width,height}` (native CRTC pixels — see `gpu.getStatus.crtc`), `accessLog.addWatch`/`get` + `accessLog.summary`, `execTrace.addWatch {capture:[<gpr names>]}` (capture takes **register names**, not "regs") + `execTrace.summary`/`execTrace.analyze`, `emulator.captureFrame {path:/tmp/...}` (write to `/tmp`, never the repo).
6. **Self-check verdict:** assert the expected region/PC and exit non-zero on mismatch, so a re-run that *re-flips* the headline is loud.

## Resilience gotchas (cost real time)
- A long `advanceFrames` from cold boot drops the WebSocket ("Connection closed while waiting for response") even though the advance **completes** server-side — chunk advances (~120) and **reconnect** (new client + re-auth) reading the live `frame` to resume; movie playback survives reconnection (no reset/loadState).
- `stop_on_hit` halts at a coarse boundary, not the exact store PC — use a non-stop `accessLog` watch + `accessLog.get`, and prefer each event's `instruction_pc` / `instruction` fields over the compatibility `pc` field.
- Heavy repeated pokes destabilize the guest → relaunch + a fresh fixture per clean run.
- Pick a stable **interior** pixel away from primitive edges; a bluish ant ≠ the brown floor (check `pixel.rgba`).

## Reference implementation
`tools/trace_spawn_floor.py` — replays [[Experiment - Spawn-floor render source]] (GAP-0011): asserts serial, loads `SCUS-94288_1.sav`, picks the floor, write-watches the packet, classifies every `fcn.80010000` source, prints a CONFIRMED/NOT verdict. Ships no media; host-portable via `DUCKSTATION_DIR`/`ABL_SAVESTATES` + `--port/--token/--save`.

## Reproducibility ceiling
These replay on the **operator's** machine only until the fork + fixtures are preserved off-machine and hash-pinned (**GAP-0001/0002**). A replay script makes a finding *re-runnable*; it does not by itself make it *third-party-reproducible*.

## Related
[[API - determinism]] · [[API - experiment runner]] · [[API - movie]] · [[API - advanceUntil]] · [[API - trace.armWhen]] · [[API - gpu.pickObject]] · [[API - accessLog]] · [[API - provenance.timeline]] · [[Playbook - Verify a hypothesis]] · [[Experiment - Spawn-floor render source]] · [[Verification - M7 Headline Recheck]] · [[Fixtures Index]]
