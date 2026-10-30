---
name: duckstation-external-debugger
description: Safely operate the local DuckStation external-debugger fork for isolated, reproducible PS1 reverse-engineering experiments. Use for debugger API connection, game and fixture verification, resident-overlay provenance, memory inspection or perturbation, execution control, breakpoints, access/exec traces, save states, input movies, GPU/frame capture, symbols, trace assertions, and evidence collection.
---

# DuckStation External Debugger

## Purpose

Use the local DuckStation external-debugger fork/API to run isolated, reproducible PS1 reverse-engineering experiments. Keep conclusions bounded to captured evidence and leave the operator's normal emulator profile and project WIP untouched.

## Source of truth

- Treat this Skill as an operating guide, not an API specification. A grouped method-index snapshot is included below so you reach past CPU/RAM, but it is a discoverability aid, **not** authoritative. Start with `ObsidianVault/Canon/Indexes/DuckStation_API_Index.md` and `tools/duckstation_rpc_method_manifest.md`, then verify syntax/limits in `~/duckstation` source, docs, client, and runtime. At the 2026-08-05 draft refresh the post-auth dispatcher allow-list exposed **220 methods (114 committed + 106 dirty-only)**; `debugger.capabilities.method_count` is **221** because its callable inventory also includes the pre-auth `debugger.authenticate` method. Re-extract whenever the source state changes.
- Before every session, verify exact method names, parameter schemas, flags, limits, client commands, and current behavior in `~/duckstation`.
- Start with `~/duckstation/docs/external-debugger.md`, the specialized `docs/external-debugger-*.md` files, and `scripts/debugger-client/README.md`; confirm uncertain behavior in `duckstation_debug_client.py`, the RPC dispatch/service source, and the running emulator.
- The fork may contain uncommitted API work. Record the source revision/status and binary hash when they affect reproducibility. Never assume the checked-out commit alone describes the running binary.
- Use the most recent canonical Obsidian note for project workflow, but never let a note override live method syntax or runtime behavior.
- **Mod/patch regression triage:** when the task is diagnosing a regression in a modded build (rather than de-novo RE), check the project vault/memory for a regression-triage playbook FIRST (projects typically maintain one: an automated smoke gate, a provable-baseline build diff, then a step ladder that ends at this debugger) and enter at the step the playbook indicates. The debugger is usually step 3+ — after the automated gate and the baseline diff have localized the failure class — not the starting point, and raw memory inspection is not the first move.
- Mark any behavior not verified in `~/duckstation` as: **verify in `~/duckstation` before use**.

## Correctness-critical extensions (2026-08-05)

- The RPC boundary is additive-only. Existing response members retain their
  compatibility meaning; consume new fields without rewriting old response
  shapes. Residency generations, movie phase audit fields, and execution-mode
  history are runtime-only debugger state. They are intentionally excluded from
  save-state serialization and must not trigger a `SAVE_STATE_VERSION` bump.
- Read each method's
  `debugger.capabilities.methods.<name>.scenario_execution_policy`; never keep a
  client-side policy list. An asynchronous scenario batch owns a runtime-only
  execution gate. A concurrent `exclusive` call fails fast with code `-32005`
  and `error.data` fields `reason:"scenario_execution_busy"`, `method`,
  `policy:"exclusive"`, `retryable:true`, and `runtime_only:true`. Observation
  and batch-control calls remain responsive (use `scenario.getBatch`,
  `scenario.cancelBatch`, or `scenario.resumeBatch` to manage the owner),
  `debugger.authenticate` is connection control, and every unclassified method
  defaults fail-safe to `exclusive`. Gate ownership is never serialized.
- Before using any address in a swap region, call `memory.getResidency` for the
  complete region. Record source file/load offset, runtime base/size,
  source/resident hashes, `sourceMatchesResident`, and load
  generation/timestamp/frame/cycle. Treat the generation tuple plus resident
  hash as the validity token; re-query immediately before execution, re-resolve
  a changed generation, and record hash-only divergence. A false match may be legitimate self-modification
  when exact load provenance retains source identity; missing/ambiguous
  provenance is not an identity.
- Prefer `movie.loadAndArm` for deterministic movie setup. It stages the movie
  and start frame, rejects active movie work, verifies optional media, and
  preflights movie/start-state serial, metadata, size, and optional hash before
  mutation. It then pauses/snapshots, loads the anchor, re-verifies
  `expected_media` before any trace clearing, phase execution, or arming, clears
  or initializes trace/breakpoint state, consumes a pending correction when
  requested, arms new watches/breakpoints, and returns paused at a defined
  boundary. A state can replace mounted media: preserve
  `media_after_start_state` and `media_changed_during_setup`, and treat a
  post-load mismatch as a setup failure that enters
  `error.data.failure_cleanup`. Treat
  `atomic:true` as `atomic_scope:"serialized_request_to_paused_arm_boundary"`,
  not full rollback; require `transactional_rollback:false` and inspect
  `error.data.failure_cleanup`. After a state-driven swap require cleanup's
  `media_identity_restored:true`; `machine_state_restored:true` is insufficient.
  Preserve `anchor_emulator_frame`, `current_movie_frame`,
  `current_emulator_frame`, `movie_to_emulator_offset`,
  `movie_to_emulator_offset_basis`, `mapped_anchor_emulator_frame`,
  `anchor_to_mapped_frame_delta`,
  `phase_correction_pending`, and `phase_correction_consumed_at` from
  `movie.status`. The legacy anchor is the playback-arm/setup boundary, while
  the offset's `movie_sample_effective_frame` basis maps a sample to the frame on
  which it takes effect. Delta `0` is aligned and `1` is correction-bearing;
  preserve the delta instead of treating the anchor and offset as interchangeable.
- For `movie.traceToFrame`, `control.movie_frame` and
  `instrumented.movie_frame` deliberately remain the legacy `playback_index`;
  use `current_movie_frame` for the mapped coordinate. Likewise,
  `comparison.same_frame` and `comparison.cycle_neutral` retain legacy
  emulator-frame/playback-index predicates. Accept coordinate-aware evidence
  only when additive `same_movie_coordinate`, `same_phase`,
  `coordinate_neutral`, and `comparison_valid` establish the strict comparison.
- A successful execution RPC is not proof the target was reached. Require the
  structured result's `execution.completed:true`; use
  `execution.advanced_frames`, `execution.end_frame`, `execution.stop_reason`,
  and `execution.stop_details` as the measured endpoint. Never reinterpret a
  compatibility counter: `emulator.advanceToFrame.frames_advanced`,
  `experiment.run.frames_advanced`, scenario result `run.frames_advanced`,
  animation result `control.framesAdvanced`/`perturbed.framesAdvanced`,
  `movie.advanceToFrame.frames_advanced`, and
  `movie.coverageToFrame.frames_advanced` retain their requested-count or
  coordinate-delta meaning. Use
  `movie.resumeUntilMovieFrame` when normal-speed/throttled behavior is part of
  the claim and retain the `movieCompleted` terminal coordinates/hashes.
- The five legacy bounded controls—`debugger.stepInstruction`,
  `debugger.stepOver`, `debugger.stepOut`, `debugger.runUntilAddress`, and
  `debugger.advanceFrame`—retain their historical immediate top-level status
  fields and add `end_status`, `execution`, `completed`, `stop_reason`, and
  `stop_details`. Use `end_status` for the post-operation snapshot; the inherited
  top-level status is not that snapshot.
- Persist `debugger.status.execution_mode`: configured/effective/last-dispatch
  modes, `transition_pending`, override reason/subsystem, and bounded history.
  `effective` is required for the next dispatch while `last_dispatch` is what ran
  most recently. Retain `history_total`, `history_retained`, `history_capacity`
  (currently 64), `history_dropped`, `history_truncated`, and each entry's
  monotonic runtime-only `sequence`, modes, frame/cycle, reason, and override
  subsystems. Prove the complete begin/end sequence interval remains retained
  (or require `history_truncated:false`); configured or final Interpreter alone
  cannot prove the mode throughout a trace.
- Evidence scatter reads use `atomic:true` or explicit
  `invalidValuePolicy:"omit"|"null"|"error"`. Never consume a legacy numeric
  value whose per-item `valid` field is false.
- Use `trace.assert` for hit/no-hit, first/last, register or memory-at-hit,
  ordering, signed frame/cycle delta, and non-truncation claims. Opt into bounded
  `execTrace` `capture_memory:[{address,width}]` when the assertion needs RAM as
  it existed before the instruction; a later read is not equivalent.
- Use `debugger.xrefsAcrossOverlays` with explicit source/base/region/generation
  identities; static localization never replaces live residency verification.
  Use `evidence.captureBundle` and JSONL/TSV `trace.export` for auditable output,
  but keep traces, states, movies, media, screenshots, and bundle payloads
  outside Git.
- Prefer intent-labelled input primitives—`movie.findInputEdges`,
  `movie.resumeUntilInputEdge`, bookmarks, and bounded `movie.timingSweep`—over
  naked frame constants. Sweep variants require deterministic replay, a complete
  relational/non-truncation assertion, and a control before they support a
  conclusion.

## Required preflight

- [ ] If working in a project repository, record `git rev-parse HEAD` and `git status --short`; preserve all operator WIP and avoid unrelated edits.
- [ ] Inspect `git -C ~/duckstation status --short`, its revision, and the executable selected by the launcher. Hash the executable when practical.
- [ ] Choose a dedicated absolute config directory, port, and token. Never use the operator's normal DuckStation config/profile.
- [ ] Record whether the isolated instance was reused or recreated. Prefer recreation for clean experiments.
- [ ] Verify the requested disc/fixture/movie exists locally. Record canonical local paths and SHA-256 hashes where practical.
- [ ] Verify the disc/image identity before tracing: query `debugger.status` and, when available, `emulator.getMediaInfo`; check serial/title/path and image hash rather than trusting a filename.
- [ ] Query `debugger.capabilities`; record its 221-entry callable inventory, source/binary identity, per-method scenario policy, and runtime-only gate contract.
- [ ] Inspect a save with `emulator.getStateInfo` before loading. Keep load-state disc validation enabled unless the operator explicitly accepts the risk.
- [ ] Pin timing-sensitive settings: CPU overclock, CD read/seek speed, region/BIOS, rewind, and run-ahead. Use scripted input and fixed frame counts.
- [ ] Record the debugger port, config path, transport, fork revision/status, disc, fixture/movie, hashes, and whether the run starts from a save state or cold boot.

## Isolated instance lifecycle

Set explicit values rather than relying on a previous session:

```bash
DUCK="$HOME/duckstation"
CFG="/tmp/duckstation-debugger-<experiment>"
PORT=<dedicated-port>
TOKEN=<local-token>

"$DUCK/scripts/debugger-client/launch_debugger_instance.sh" status --config-dir "$CFG"
"$DUCK/scripts/debugger-client/launch_debugger_instance.sh" stop --config-dir "$CFG"
"$DUCK/scripts/debugger-client/launch_debugger_instance.sh" start \
  --config-dir "$CFG" --port "$PORT" --token "$TOKEN" --disc "/abs/game.cue"
```

- Stop a stale instance only through the launcher and the same config directory. The launcher verifies ownership before killing its PID; never use broad `pkill` patterns.
- A launcher that backgrounds the emulator and then exits leaves it **orphaned but alive** — it persists across later client/tool calls (verify with a fresh `debugger.status` rather than assuming it died and relaunching needlessly). Only when you bypass the launcher and start the binary directly from an automation harness must you **fully detach** it (own session via `setsid`, stdin from `/dev/null`, output redirected) so it is not killed when the spawning shell or process group is torn down.
- If intentionally reusing an instance, query status/media and clear old instrumentation, controller holds, movie playback, fast-forward/turbo, and relevant session-scoped stores first.
- Authenticate each new connection before any other RPC. Prefer WebSocket when asynchronous events or larger requests matter.
- Set a finite client socket timeout and reconnect/re-authenticate after a dropped connection. A long frame advance may finish server-side even if the client disconnects; query live status before repeating it.
- At completion, clear watches/breakpoints and injected input, stop movie activity and speed overrides, then stop the isolated instance with the same `--config-dir`. Record cleanup success.
- Never silently fall back to the normal emulator profile, default user-data directory, or an already-running personal instance.

## Common workflows

Use the bundled client for convenience, or call verified JSON-RPC methods directly:

```bash
CLIENT="$HOME/duckstation/scripts/debugger-client/duckstation_debug_client.py"
python3 "$CLIENT" --host 127.0.0.1 --port "$PORT" --token "$TOKEN" <command>
python3 "$CLIENT" --host 127.0.0.1 --port "$PORT" --token "$TOKEN" \
  <method> --params '<json>'
```

### Identity and coherent capture

1. Call `debugger.capabilities`; verify the 220-method post-auth dispatcher / 221-entry callable census and inspect each method's scenario policy.
2. Call `debugger.status`; verify `game_serial`, `game_title`, `game_path`, frame, paused/running state, and execution-mode audit.
3. Call `emulator.getMediaInfo` if the current docs/runtime expose it.
4. Pause before multi-call CPU/RAM/GPU inspection. A single structured/scatter call is internally coherent, but unrelated reads while running can form a torn snapshot.
5. Use `emulator.captureSnapshotBundle` when documented and an atomic composite capture is needed.

### Memory read and write

- Read with verified `debugger.readU8/U16/U32`, `readMemory`, `readStruct`, `readArray`, `readPointerChain`, or `scatterRead` calls. PS1 multi-byte values are little-endian.
- Write only with an explicit experiment hypothesis and rollback path. Prefer typed `writeU*`, raw `writeMemory`, or `scatterWrite` with `atomic:true` when partial application would corrupt a structure.
- Pause for coherent mutation. Capture before/after bytes and reload the fixture to undo RAM writes.
- Validate per-item `valid`, `ok`, `written`, and `applied` fields; do not infer success from a successful transport response.

### Execution control and breakpoints

- Pause before `stepInstruction`, `stepOver`, `stepOut`, `runUntilAddress`, or register writes.
- Use `emulator.advanceFrames {"frames": N}` for deterministic fixed-frame movement; verify the current parameter name before use and chunk long advances when necessary. `advanceFrames` advances emulated time but **injects no controller input** — to cross menus/intros or cold-boot into a playable state, drive input via movie playback (a `from_boot` movie) or scripted `pressButton`/`setControllerState`, then advance. Detect arrival from state (a known RAM field going live), not a fixed sleep. This frame-advance path is the deterministic "fast-forward"; prefer it over GUI fast-forward/turbo for reproducible endpoints.
- Require `execution.completed:true` for bounded work and read measured progress from `execution.advanced_frames`, never from a legacy requested-count alias. For the five legacy debugger controls, use additive `end_status` as the post-operation status.
- Respect the capability-declared scenario policy. Exclusive calls fail fast rather than waiting when the runtime-only batch gate is owned; observation and batch-control calls stay available for inspection/cancellation.
- Use `debugger.addBreakpoint` for halting execute/read/write breakpoints and manage the returned ID. List and remove breakpoints explicitly after capture.
- Use `execTrace.addWatch` for non-halting PC/register capture when supported. Re-arm it after every state load.
- Any CPU breakpoint/watch can force the interpreter and slow emulation substantially; scope it narrowly and remove it promptly.

### Access log and watchpoints

```json
{"method":"accessLog.addWatch","params":{"address":"<address>","length":4,"type":"write","max_events":10000,"stop_on_hit":false}}
{"method":"accessLog.run","params":{"frames":<bounded-count>}}
{"method":"accessLog.get","params":{"watch_id":<id>,"offset":0,"limit":10000}}
{"method":"accessLog.clear","params":{}}
```

- Arm a watch before the event. `lastWriter`/`findFirstWrite`, if present, query retained write events; they are not retrospective without an armed write watch.
- A data-access callback fires before the access. For reads, `value` is the value about to be read; for writes, it is the old/pre-write value. `new_value` is only a decoder aid for supported aligned stores and is absent for partial stores.
- Current fork source passes an already-advanced PC to data-breakpoint callbacks. Observed access-log PCs can therefore be **store/load instruction + 4**. Disassemble both reported `pc` and `pc-4`, confirm the effective address and store/load width, and correlate with `execTrace` or single-step evidence before naming a true writer/reader. Treat decoded `new_value` as non-authoritative until that instruction-level check and a post-write memory read agree.
- `stop_on_hit` requests a pause at a later safe point; it is not an exact-instruction stop. Use the recorded event PC for attribution.
- CPU access watches do not observe DMA writes. Use `transferLog` for live CD/DMA provenance.
- Watches are bounded and can truncate. Record `hit_count`, `total`, `truncated`, limits, frame/cycle window, and filters.
- Access/exec watches are cleared on game unload, debugger-server stop, and `emulator.loadState`; transfer logging is also cleared/disabled on load. Load first, optionally settle one controlled frame when the canonical workflow requires it, then re-arm.

### Save states and movies

- Use absolute paths. Inspect with `emulator.getStateInfo`, verify mounted media, then call `emulator.loadState` with `pause_after_load:true` and disc validation enabled.
- On disc mismatch, stop and report the structured error. Do not disable validation or auto-select another disc without recording the choice and verifying the resulting media identity.
- Treat a named save state plus pinned settings, scripted input, and fixed frame count as the normal deterministic anchor.
- If `movie.*` exists, load/record/play only through verified schemas. Prefer playback with the recorded start anchor; record `movie.status.reproducible` when available.
- Pass `movie.startRecording.params.start_state` as the absolute path string itself, never as `{"path":...}`. Omitted,
  null, or empty is the legacy unanchored form; any other JSON type must fail `-32602` before movie/reset mutation.
- A path-anchored recording persists a recording-start SHA-256 and provenance. For direct `movie.startPlayback {load_start_state:true}`, require `hash_verified:true` and `start_state_binding.verification:"verified"`; treat `unbound`, `not_requested`, from-boot `not_applicable`, and malformed `invalid_metadata` as distinct non-verified outcomes. A mismatch raises **`-32006`** with `mutation_performed:false`, `load_attempted:false` and `anchor_mutation_attempted:false` — it refuses before touching the machine, on `movie.startPlayback` and `movie.loadAndArm` alike (the latter reports `failure_cleanup.phase:"start_state_hash_preflight"`). Do not treat a caught `-32006` as a failed run: nothing ran. `evidence.captureBundle` never writes/backfills movie metadata and is not itself a fresh match proof when it reuses an embedded expected digest.
- For `movie.traceToFrame`, treat `movie_frame`, `same_frame`, and `cycle_neutral` as legacy compatibility fields; require the explicit mapped coordinate and strict comparison fields for new evidence.
- Movies record all 16 buttons **and** the analog stick axes (format v3; older digital-only v1/v2 files still load). Rumble output and the analog-mode toggle press are not recorded — the latter rides in the pinned start state. A load/reset/unload/server stop can terminate active movie recording/playback. **verify the recorded format/scope in `~/duckstation` before relying on analog replay.**
- After any load, re-arm non-halting instrumentation. Controller holds and user breakpoints may persist; query and clear them deliberately.

### Screenshots, GPU picking, and symbols

- Use `emulator.captureFrame`, `gpu.captureFrameSnapshot`/`gpu.diffCurrentFrame`, or `gpu.pickObject` only when they are present in current docs/runtime.
- Prefer in-memory frame snapshots for live diffs; file capture can race filesystem visibility. Treat screenshots as corroboration, not sole proof of CPU/RAM claims.
- `gpu.pickObject` coordinates are native CRTC pixels, not window/upscaled coordinates. Pause and inspect current CRTC geometry first.
- Use `debugger.importSymbols`/`exportSymbols` only when documented. Use absolute paths, record format and merge/replace behavior, and preserve the existing symbol store before replacement.

## Full API method index (snapshot; verify the 220-method dispatcher / 221-method capability census)

> **Discoverability aid, not the authoritative spec.** Verify exact names, params, flags, and limits in `~/duckstation/docs/external-debugger*.md` and the running binary each session — the fork carries uncommitted API WIP and the surface drifts (this index reflects the 220 methods in the post-auth dispatcher allow-list; `debugger.capabilities` reports 221 callable entries because it also includes `debugger.authenticate`). Re-extract when the fork changes. **The point of this index: reach for the tool that fits — especially the ⚑ GPU / VRAM / GTE / object-picking / frame-diff methods — instead of defaulting to CPU/RAM brute force.** Most calls need a loaded system + `debugger.pause` for a coherent read; `debugger.authenticate` runs first.

### ⚑ Reach past CPU/RAM — which tool for which question
- **"Which overlay owns this address right now?"** → `memory.getResidency`, pin its source/resident hashes and load generation, then re-query before execution.
- **"Did the requested run actually reach its target?"** → inspect structured `completed`, `stop_reason`, and `stop_details`; RPC return alone is insufficient.
- **"Does the retained trace prove the relationship?"** → `trace.assert`, including a non-truncation assertion and any hit/order/delta/value predicates.
- **"Which RAM object is this on-screen thing?"** → `gpu.pickObject {x,y}` (screen pixel → drawable + `source.ramAddress`/`vertexPointer`), then `accessLog`/`execTrace`. Backups: `gpu.readVramRect`/`gpu.decodeTexture`, `debugger.getGteState`, `gpu.captureFrameSnapshot`+`gpu.diffCurrentFrame`. **Animated** object → `experiment.run` `captureControl` (phase-matched control), NOT a raw force-and-diff.
- **"Where did this RAM data come from on disc?"** → `transferLog.resolve {address}` (or `transferLog.start` → advance → `transferLog.get`).
- **"Did my edit change the screen?"** → `gpu.captureFrameSnapshot` → perturb → `gpu.diffCurrentFrame` (in-memory; settle a few frames first).
- **"Who wrote this byte?"** → `accessLog.addWatch type:write` BEFORE the write, then `accessLog.lastWriter`/`findFirstWrite`.
- **"Reach a level from a cold boot of an edited disc"** → `movie.*` + `emulator.advanceFrames` (save states are on the pristine image; they won't show disc edits).
- **"Does this function do X / does this trigger fire / what does it return?"** → `debugger.callFunction {address,a0..a3}` (pause first) — invoke it directly and read `v0`, instead of building a cave + rebuilding to test the hypothesis.

### Identity / status
`debugger.authenticate {token}` (first) · `debugger.capabilities` (221-entry callable inventory, per-method scenario policy, schemas, source/binary identity) · `debugger.status` (pc/sp/frame/cycle + serial/title/mode audit) · `emulator.getVideoStatus` (no game needed) · `emulator.getMediaInfo` · `emulator.getStateInfo {path}` (metadata WITHOUT loading) · `emulator.getSpeed` · `emulator.getCdromState` · `emulator.getDmaState`.

### Execution control & breakpoints
`debugger.pause`/`resume`/`reset` · `stepInstruction`/`stepOver`/`stepOut` (need pause) · `runUntilAddress {address}` · `advanceFrame` (one frame) · `emulator.advanceFrames {frames}` **(NOT `count`)** or `{seconds}` · `emulator.advanceUntil` · `debugger.addBreakpoint {address,type:execute|read|write|readwrite,enabled,temporary}` · `removeBreakpoint`/`updateBreakpoint`/`enableBreakpoint`/`disableBreakpoint {id}` · `listBreakpoints`/`clearBreakpoints`.
- ⚑ **`debugger.callFunction {address, a0?,a1?,a2?,a3?, timeout?}`** (**needs pause**) — INVOKE a guest subroutine and read its return. Loads `a0..a3`, points `ra` at the current paused PC (the return trap), jumps to `address`, runs until it returns there, then re-pauses → `{v0, v0_hex, v1, return_address, stopped_at, status}`. `timeout` ms (default 5000, max 60000); if it stops elsewhere first the call fails with `reason:"stopped_elsewhere"`. **The RE accelerator** — test what a function does / whether a trigger fires WITHOUT building a cave (verified live: read-only `FUNC_80038f38(0,&Flik+0x82)`→`v0=0`, clean re-pause). Side-effecting calls really run (mutate state/VRAM/scene), so treat them like a real invocation.

### Registers / disassembly / stack
`debugger.getRegisters` (GPRs, pc/hi/lo, COP0, 67 raw GTE `gte_*`) · `getRegister`/`setRegister {name[,value]}` · `disassemble {address,count}` · `getStack {count}`.

### Memory read/write (CPU/RAM)
`readMemory {address,length}` / `writeMemory {address,hex|base64,invalidate_code?}` · `readU8/U16/U32` / `writeU8/U16/U32 {address,value,invalidate_code?}` · `readStruct {base,fields[]}` · `readArray {base,count,stride,fields[]}` (count≤4096) · `readPointerChain {base,offsets[],type}` · `readCString {address,max_length}` · `scatterRead {reads[],atomic?,invalidValuePolicy?}` · `scatterWrite {writes[],atomic}` · ⚑ `memory.getResidency {region:{address|base,size|length},source?}` · ⚑ `invalidateCodeCache {address?,length?}`. **Live code patches take effect immediately:** `writeMemory`/`writeU*` into executing code auto-invalidate the recompiler block + emulated I-cache (default `invalidate_code:true`; response `code_invalidated`) — no breakpoint-toggle workaround. `invalidateCodeCache` (no range ⇒ all RAM) forces it after an `invalidate_code:false`/scatter/experiment write.

### Symbols / xrefs / function bounds
`getSymbols` / `resolveSymbol {address|name}` · `addLabel`/`addComment`/`getComments` · `importSymbols`/`exportSymbols {path,format,merge}` · `xrefsTo {address}` · ⚑ `xrefsAcrossOverlays {overlays[],target}` · `functionBounds {address}` → `{functionStart,functionEnd,confidence,cleanEnd,mergedRegion,spanBytes,...}`. **Trust only `confidence:"exact"` (clean terminator + ≤8 KiB span) as a single function;** `confidence:"low"` + `mergedRegion:true` means the span merged several routines (supply symbols or query a narrower address).

### Watches — non-halting (RE-ARM after every loadState)
- **accessLog** (who read/wrote): `addWatch {address,length,type,...}` · `removeWatch`/`clear` · `get {watch_id,offset,limit}` · `run {frames}` · `lastWriter {address}` · `findFirstWrite {address,since,until}`.
- **execTrace** (which PCs + regs/memory; can capture `gte.*`): `addWatch {pc,capture[],capture_memory?:[{address,width}],...}` / `addRangeWatch {start,end,capture[],capture_memory?,...}` · `removeWatch`/`clear`/`get`/`run`.
- **transferLog** (DMA-block + CD-sector provenance): `start`/`stop`/`clear` · `get {offset,limit,filter}` · `resolve {address}` (RAM addr → disc file/LBA/offset).
- **memoryScan** (unknown-value RAM search): `start {type,mode,value,range}` · `refine {mode[,value]}` (changed/increased/decreased/exact…) · `results` · `clear`.

### ⚑ GPU / VRAM / object-picking / frame-diff
⚑ `gpu.readVramRect {x,y,width,height}` (≤512×512, raw 16-bit LE) · ⚑ `gpu.captureVramRect {x,y,width,height,format?}` and ⚑ `gpu.frameSnapshot {buffer?=displayed|drawing|by_rect,rect?,format?}` (deterministic, **flip-race-free**; `format` png|rgba|raw16; paused ⇒ byte-identical repeats) · ⚑ `gpu.decodeTexture {x,y,w,h,bpp,output_path,clut_x,clut_y,mask_black}` → PNG · ⚑ `gpu.getClut` · ⚑ `gpu.pickObject {x,y,all_contributors}` (→ drawable + RAM/vertex addr + geometry) · ⚑ `gpu.captureFrameSnapshot` (in-memory) · ⚑ `gpu.diffCurrentFrame {against,region,threshold}` · `gpu.listFrameSnapshots`/`clearFrameSnapshot` · `gpu.getStatus` (GPUSTAT, draw mode, CRTC) · ⚑ `gpu.getCameraTransform` (view/projection + camera basis).

### ⚑ GTE / COP2 / PGXP
⚑ `debugger.getGteState` (DECODED GTE matrices /4096, screen offset, FIFOs) · ⚑ `debugger.getPgxpData {include_gpr,include_gte}` (sub-pixel float X/Y/Z; needs PGXP). Raw GTE regs are in `getRegisters` (`gte_*`).

### GP0 display-list trace
`gp0Trace.start {max_entries,max_params}` · `stop`/`clear`/`get {offset,limit,clear}` → entries + `dma_count`/`mmio_count` + `warning?`/`note?`. DMA capture is verified (block + linked-list/OT). **`total:0` = nothing drawn (static screen) or armed mid-frame** (sequence: `start → clear → advanceFrames` *while drawing* `→ get`); **`dma_count:0` = scene renders via MMIO** (2D/menus), not a bug — capture during 3D for `source:"dma"`.

### Frame capture / hashing (file-based)
`emulator.captureFrame {path}` · `captureSnapshotBundle` (atomic composite) · `hashFrame {path,region,hash:ahash|dhash|sha256}` · `diffFrames {a,b,region,...}` (prefer `gpu.diffCurrentFrame` for live).

### Controller input
`getControllerState`/`setControllerState`/`clearControllerState {port,buttons,analog}` · `pressButton {button|buttons,frames|seconds,port,release_after}`. `setControllerState` takes `buttons {name:bool}` and/or `analog {lx/ly/rx/ry:0..255, 128=centre}` (analog needs an AnalogController; held axes re-apply each frame like held buttons, driven directly past host deadzone/sensitivity); `getControllerState` reports held axes in `analog`/`analog_held`.

### Save state / media control
`saveState`/`loadState {path,...}` (loadState `validate_disc` defaults true — mismatched disc CRASHES; clears non-halting watches) · `bootSystem {path,fast_boot,start_paused,force}` (cold boot) · `loadMedia {path}` (warm swap) · `closeMedia` · `setFastForward`/`setTurbo {enabled}`.

### CD file/sector overlay (test edited assets without rebuilding the disc)
`cd.overlayFile {path,base64|hex}` · `cd.overrideSectors {lba,...}` · `clearOverlay`/`clearSectorOverride`/`clearOverlays` · `listOverlays`.

### Experiment runner (load → perturb → advance → diff)
`experiment.run` (baseline → perturb `memory_writes`/`controller`/`watches` → advance → diff; `captureControl:true`+`diff` = phase-matched animation-cancelling frame diff) · `compareRuns {from_state,run_a,run_b}` · `warpAndSettle {writes,frames,inputs,untilStable,capture}` · `diffMemory`/`diffRegisters`.

### Assertions and portable evidence
⚑ `trace.assert {source|trace,assertions[]}` · ⚑ `trace.export {format:jsonl|tsv,...}` · ⚑ `evidence.captureBundle {residencies?,cleanup_after?,...}`. Keep exported payloads outside Git.

### Movie / input recording & playback
`movie.startRecording {ports,start_state,load_start_state,from_boot,notes}` · `stopRecording`/`save`/`load {path}` · `startPlayback {start_frame,load_start_state}` · ⚑ `loadAndArm` · `advanceToFrame`/`resumeUntilMovieFrame` · ⚑ `traceToFrame` · `stopPlayback`/`status`/`clear` · ⚑ `findInputEdges`/`resumeUntilInputEdge` · ⚑ `setBookmark`/`removeBookmark`/`listBookmarks` · ⚑ `timingSweep` · `store`/`list`/`get`/`remove {movieId}` · `append`/`branch`/`editFrame`/`activate` (TAS rerecord). Per-frame `input` is `{ "<port>": { "<button>": bool, …, "lx"/"ly"/"rx"/"ry": 0..255 } }` — analog axes optional, default 128 (centre). `status` returns explicit movie/emulator mapping and phase audit fields.
**Caveats:** `start_state` is a path string, not an object. `anchor_emulator_frame` is the playback-arm boundary;
`movie_to_emulator_offset` maps sample-effective frames, and the additive mapped-anchor/delta fields expose their phase
relationship. The correction belongs to legacy v1 or recording-armed-while-paused movies, not every playback armed
paused. Movies record all 16 buttons **and** the analog stick axes (format v3; older v1/v2 files were digital-only —
`version` tells you which); rumble and the analog-mode toggle press are NOT recorded (the toggle rides in the pinned
start state); recordings can be **truncated** (verify the input span — last non-neutral frame vs total — before trusting
a replay); a load/reset can terminate playback.

### Findings & fixtures store (persistent RE notebook → `re_findings.yaml`)
`findings.upsert`/`get`/`delete`/`list` · `findings.save`/`load {path}` (**load FIRST — save overwrites**) · `fixtures.add`/`get`/`list` · `fixtures.load {id,pause_after_load}`.

### Async events (WebSocket/TCP push) & error codes
Not methods — a **push channel** you subscribe to instead of polling. Server emits: `paused` · `resumed` · `breakpointHit` (payload: `pc`,`sp`,`breakpoint_id` + status snapshot) · `stepComplete` · `gameLoaded` · `gameUnloaded` · `emulatorStopped` · `registerChanged` · `memoryChanged` · `guestHalted` (crash: `reason`,`pc`,`diagnostics{…}`,`status`) · `guestReset` · `log`. Use these to **wait on a breakpoint/crash** rather than busy-polling status. **Crash-safe RPC:** every core-thread call has a **5000 ms timeout**; a halted/looping guest returns structured error `-32005` (`core_unresponsive`) instead of hanging, usually followed by a `guestHalted` event — treat the guest as dead (relaunch), don't retry blindly. A method needing a paused system returns `-32002` while running (read methods work running but pause-first for coherence).

**Top gotchas:** `advanceFrames` param is `frames` not `count`; `loadState` hard-crashes on a mismatched disc and **clears all non-halting watches** (re-arm `accessLog`/`execTrace`/`transferLog`/`gp0Trace` after every load); raw GTE regs are in `getRegisters` (`gte_*`) while `getGteState`/`getPgxpData` are the decoded views.

**Additional correctness gates:** RPC completion is not requested-advance completion—check structured `completed`/`stop_reason`; an overlay address is invalid without current residency/generation; a movie frame is ambiguous without mapping/phase audit, including the mapped-anchor delta; `movie.startRecording.start_state` is never a metadata object; configured mode is not the effective-mode timeline; never consume `scatterRead` data with `valid:false`.

## Reproducible experiment pattern

1. Verify emulator, media, fixture/movie, settings, hashes, configured/effective mode, and required overlay residency.
2. Prefer `movie.loadAndArm` for movie work; otherwise load the fixture or cold boot, pause, and explicitly initialize traces.
3. Re-arm instrumentation after the load.
4. Capture the baseline.
5. Change one variable using scripted input or a bounded memory/register write.
6. Advance a fixed number of frames and require `completed:true`; otherwise use the structured stop as the endpoint.
7. Capture the same fields, residency generation, movie/emulator mapping, phase fields, and mode history; compare against a no-perturbation control from the same anchor.
8. Repeat when claiming causality. Prefer `experiment.run`/`experiment.compareRuns` only after verifying their current schema.
9. Clear instrumentation/input and stop the isolated instance.

CPU registers, PC, main RAM, scratchpad, GTE/COP0, and save-state contents are the strongest deterministic evidence. Displayed frames may vary slightly; audio and asynchronous CD scheduling are not bit-exact. A single observation supports at most a bounded correlation, not a causal conclusion.

## Evidence standard

For every capture, record:

- exact client command or JSON-RPC method and parameters;
- address/range, access type, width, watch/breakpoint ID, limits, and filters;
- reported PC plus instruction-level confirmation, including the `pc-4` check for data accesses;
- old/pre-access value, decoded candidate new value, and independently read post-value where relevant;
- frame, tick/cycle/counter, paused state, and truncation status when available;
- structured `execution` completion/measured count/stop details separately from legacy aliases; residency identity/hashes/generation and pre/post check for overlay addresses; movie coordinate/phase mapping; and a complete retained execution-mode sequence interval;
- mounted disc serial/title/path and disc/image hash;
- fixture/save/movie path, anchor type, frame count, input script, and hashes;
- debugger config path, port, transport, fork revision/status, binary hash, and reused/recreated instance state;
- replay command or complete reproduction steps, cleanup result, and the smallest conclusion supported by the data.

Distinguish observation, inference, and causal confirmation. Record negative results with the armed range, time window, and truncation status; zero hits outside a justified capture window do not prove no access exists.

## Safety and legal hygiene

- Do not commit disc images, BIOS files, extracted game assets, RAM dumps, or credentials/tokens.
- Do not commit save states unless project policy explicitly allows it.
- Do not commit screenshots, movies containing copyrighted content, or generated copyrighted outputs unless project policy explicitly allows it.
- Prefer hashes and canonical local paths in notes over copying binary artifacts into the repository.
- Write transient captures to an isolated temporary directory, not the source tree. Check project policy and `git status` before preserving any artifact.
- Do not overwrite the operator's disc, fixture, movie, config, symbols, or findings store. Create explicit experiment copies when mutation is required.

## Failure handling

- If API docs and Obsidian notes disagree, use `~/duckstation` docs/source/runtime for method syntax and the most recent canonical Obsidian note for project workflow.
- If a method is missing or fails, record the exact command/request, complete error, transport, port, config path, fork revision/status, running binary, mounted media, and expected behavior.
- Do not invent or rename methods. Search the current docs, client parser, RPC dispatch, and service implementation.
- On timeout/disconnect, reconnect and query status before retrying a state-changing command.
- On guest crash or inconsistent results, preserve logs, stop the owned isolated instance, recreate it, re-verify media/fixture/settings, and rerun from the anchor.
- Never silently use non-isolated config, disable disc validation, widen a destructive write, or continue after identity verification fails.

## Do not put in this Skill

Exclude project findings, discovered addresses, current experiment or milestone status, active blockers, current commit hashes, game-specific conclusions, and volatile function discoveries. Keep game/project-specific examples outside this Skill; any future example must be clearly non-normative and must not become operating truth. (The generic **API method index** above is the debugger's own method surface — not game findings — and is intentionally included for tool discoverability; refresh it by re-extracting from `~/duckstation` when the fork changes. Game-specific addresses/findings still stay out.)

## Example usage prompt

> Use the DuckStation External Debugger Skill. Check `~/duckstation` for exact API details. Start an isolated debugger instance, verify game identity, run the requested trace, record commands/hashes/PCs/values, stop the instance, and keep conclusions bounded to evidence.
