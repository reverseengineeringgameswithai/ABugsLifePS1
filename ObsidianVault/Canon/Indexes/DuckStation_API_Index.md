---
kind: index
id: DUCKSTATION_API_INDEX
aliases:
  - DuckStation API Index
  - DuckStation Fork Reproducibility
  - Relaunching DuckStation
  - API - accessLog
  - API - execTrace
  - API - gpu.readVramRect
  - API - visual diff
  - API - execution control
  - API - CD overlay
  - API - connection and auth
  - API - determinism
  - API - experiment runner
  - API - gp0Trace
  - API - gpu.pickObject
  - API - loadState
  - API - movie
  - API - readArray
  - API - addWatch
  - API - controller input
  - API - findings store
  - API - frame capture
  - API - saveState
  - API - scatterWrite
created: 2026-07-08
updated: 2026-08-05
status: generated
updated_by: duckstation_api_safety_contract_refresh
supersedes: ObsidianVault/Archive/Superseded/Indexes_DuckStation_API_Index.md
authoritative_method_list: tools/duckstation_rpc_method_manifest.md
machine_manifest: analysis/phase3_duckstation_rpc_manifest.json
method_count: 220
source_revision: fe0cca16b85e09a304cfde3c39669ce8c0adb8f5
source_status_sha256: 0ae8b03d3a31322c13a2ce60429a8f4460affed1a9131349b66243d17cda55ac
dispatcher_sha256: bf4d76fe14b8a8d783f24cb5fa33e46d5a5a1c1b9f3219b9d6c2b46b1aa28023
release_binary_sha256: 2ddaad7b1fdbca78110e3a871fd15496923e03be470d2e08e356a006b460dcf4
release_runtime_tree_sha256: e2c7a483cf6722568edac54ff3e55689fc752aa0e11b34d7405ae585efaea3d0
---

# DuckStation API Index

Orientation for the custom DuckStation external-debugger JSON-RPC API used for
SCUS-94288 reverse engineering. The exact current surface is **220 dispatched
methods: 114 at fork HEAD plus 106 dirty-only, with zero removed**. It is derived
from the balanced `KnownMethods`/`IsKnownMethod` allow-list at fork revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, not copied from prose or counted
across the whole dispatcher.

The generated census counts the **220 methods in `KnownMethods`**. Runtime
`debugger.capabilities` additionally describes the connection-only
`debugger.authenticate` method, so its `method_count` is **221**; this is an
intentional scope difference, not manifest drift.

The authoritative generated method list is
`tools/duckstation_rpc_method_manifest.md`; its machine representation and exact
source/docs/client/launcher/binary hashes are in
`analysis/phase3_duckstation_rpc_manifest.json`. The current dispatcher SHA-256
is `bf4d76fe14b8a8d783f24cb5fa33e46d5a5a1c1b9f3219b9d6c2b46b1aa28023`,
and the complete 106-path dirty status hashes to
`0ae8b03d3a31322c13a2ce60429a8f4460affed1a9131349b66243d17cda55ac`.
The final release binary hashes to
`2ddaad7b1fdbca78110e3a871fd15496923e03be470d2e08e356a006b460dcf4`;
its 207-file support tree hashes to
`e2c7a483cf6722568edac54ff3e55689fc752aa0e11b34d7405ae585efaea3d0`.
The old 141-method GAP-0001 snapshot at revision `296955321` and the 191-method
iteration-9 snapshot remain historical reproducibility evidence. The current
manifest is the source/binary authority for new Phase 3 replays.

## Operating boundary

- Verify method names, parameter shapes, limits, flags, and behavior against the
  current `~/duckstation/docs/external-debugger*.md`, client, dispatcher, and
  running binary before each live session. This index is a map, not the runtime
  specification.
- Start every run in a new absolute config directory with its own loopback port
  and token. Query status plus `emulator.getMediaInfo`, hash the mounted CUE and
  tracks, inspect states with `emulator.getStateInfo` before loading, keep disc
  validation enabled, re-arm traces after every load, and stop only the PID owned
  by that config directory.
- Pin timing-sensitive settings and distinguish cold-boot/movie evidence from
  save-state evidence. A state is appropriate only for a narrow runtime question
  after embedded and mounted media identity are verified.
- Pause before coherent multi-domain inspection. Use `capture.atomic` when CPU,
  RAM, GPU, movie, SPU, and retained trace evidence must describe one instant.

## Correctness-critical API contracts (2026-08-05)

- The RPC boundary is **additive-only**. Existing response members retain their
  meaning; new callers should consume the richer fields without assuming older
  clients have been migrated. The new residency, movie-coordinate, stop-result,
  and execution-mode state is debugger runtime state only. It is deliberately
  excluded from save-state serialization and does not change `SAVE_STATE_VERSION`.
- Query `debugger.capabilities` instead of maintaining a concurrency allow-list.
  Every method advertises `scenario_execution_policy` as `exclusive`,
  `observation`, `batch_control`, or `connection_control`, and the response's
  `scenario_execution_gate` describes the runtime-only fail-fast gate. While an
  asynchronous scenario worker owns the gate for one job, a concurrent direct
  `exclusive` call fails immediately with `-32005`; its `error.data` has
  `reason:"scenario_execution_busy"`, the requested `method`,
  `policy:"exclusive"`, `retryable:true`, and `runtime_only:true`. Observation calls and
  `scenario.getBatch`, `scenario.cancelBatch`, and `scenario.resumeBatch` remain
  responsive. `scenario.runBatch` itself is `batch_control` and returns promptly;
  workers still serialize on the one emulation core. Authentication is independent,
  and every newly known method defaults fail-safe to `exclusive` until explicitly
  classified. Gate ownership is never save-state data.
- Before resolving or executing an address in a swap region, call
  `memory.getResidency` for the complete region. Record the source file and file
  offset, runtime base and size, source/resident hashes, `sourceMatchesResident`,
  and load generation/timestamp. Treat the generation tuple plus
  `resident_memory_hash` as the address-validity token. Re-read it immediately
  before a breakpoint or trace; re-resolve if the generation changes, and treat
  a hash-only change as resident-byte divergence under the same tracked load.
  `sourceMatchesResident:false` proves byte divergence, not necessarily wrong
  identity: self-modifying overlays can retain exact load provenance while no
  longer matching the source slice. Missing/ambiguous provenance is not evidence
  for any overlay identity.
- `movie.status` now reports both coordinate systems:
  `anchor_emulator_frame`, `current_movie_frame`, `current_emulator_frame`,
  `movie_to_emulator_offset`, `movie_to_emulator_offset_basis`,
  `mapped_anchor_emulator_frame`, `anchor_to_mapped_frame_delta`,
  `phase_correction_pending`, and `phase_correction_consumed_at`. The legacy
  anchor is the playback-arm/setup boundary; the offset maps a movie sample to
  its effective emulator frame. A delta of `0` is aligned and `1` carries the
  movie's one-frame correction, so anchor `9238` and mapped anchor/offset `9239`
  at movie frame zero are consistent rather than interchangeable. Store these
  fields with every frame-labelled claim. Prefer `movie.loadAndArm`: it stages the movie and start frame, rejects
  active movie work, verifies optional media, and preflights movie/start-state
  serial, metadata, size, and optional hash before mutation. It then
  pauses/snapshots and loads the anchor. Because a save-state load can replace the
  mounted image, it re-verifies `expected_media` after that load and before trace
  clearing, phase execution, or arming; a mismatch enters cleanup. Success reports
  `media_after_start_state` and `media_changed_during_setup`. It then
  clears/initializes trace and breakpoint state, consumes a pending correction
  when requested, installs new watches and breakpoints, and returns paused at one
  defined frame/cycle/phase boundary. Its
  `atomic:true` means
  `atomic_scope:"serialized_request_to_paused_arm_boundary"`, not full rollback;
  require `transactional_rollback:false` and inspect
  `error.data.failure_cleanup`. After a state-driven swap, require its separate
  `media_identity_restored:true`; `machine_state_restored:true` alone does not
  prove that the pre-request disc path was restored.
- New path-anchored recordings hash the start-state file before the optional load
  and persist `sha256`, `sha256_provenance:"recording_start"`,
  `sha256_backfilled:false`, and normalized `sha256_origin:"recording"`. The 123
  pre-existing ABL state-anchored fixtures were backfilled on 2026-08-05 and
  deliberately retain `sha256_backfilled:true` / `sha256_origin:"backfill"`:
  those hashes detect later disk drift but are not recording-time attestations.
  `movie.startRecording.params.start_state` is the absolute path string itself,
  never `{"path":...}`. Omitted, null, or empty remains an unanchored recording;
  any other JSON type fails `-32602` before core/movie/reset mutation. Relative,
  missing, or non-loadable string paths remain semantic `-32006` errors.
  Direct `movie.startPlayback {load_start_state:true}` now compares a valid
  recorded digest before state load or playback mutation. Require top-level
  `hash_verified:true` and `start_state_binding.verification:"verified"`; a
  mismatch is `-32006` with `mutation_performed:false`. `unbound`,
  `not_requested`, from-boot `not_applicable`, and malformed
  `invalid_metadata` are distinct non-verified outcomes. `evidence.captureBundle`
  never writes/backfills movie metadata; when a digest is already embedded it
  reuses that expected value, so the bundle alone is not a fresh match proof.
- Every bounded execution request advertised by
  `debugger.capabilities.schema_coverage.structured_execution_stop_result_methods`
  must be judged by its additive `execution` result, not by successful RPC
  return. Require `execution.completed:true`; otherwise use
  `execution.advanced_frames`, `execution.end_frame`, `execution.stop_reason`, and
  `execution.stop_details` as the actual endpoint. Breakpoint, watchpoint, movie completion,
  halt, exception, timeout, pause, and external interruption are legitimate early
  stops. Legacy top-level `frames_advanced`/`framesAdvanced` fields may retain
  their historical requested-count or movie-coordinate-delta meaning; they are
  not substitutes for measured `execution.advanced_frames`.

  This contract now explicitly includes `debugger.stepInstruction`,
  `debugger.stepOver`, `debugger.stepOut`, `debugger.advanceFrame`, and
  `debugger.runUntilAddress`. Those five preserve their legacy immediate
  top-level status fields and add `end_status`, `execution`, and top-level
  `completed`/`stop_reason`/`stop_details` aliases. Use `end_status` for the
  post-operation snapshot. Use the normal-speed `movie.resumeUntilMovieFrame`
  when real-time/interpreter timing is part of the claim.
- `movie.traceToFrame` also preserves compatibility predicates. In each
  `control`/`instrumented` signature, `movie_frame` remains the legacy
  `playback_index`; use `current_movie_frame` for the explicit mapped coordinate.
  `comparison.same_frame` still compares emulator frame plus playback index, and
  `comparison.cycle_neutral` remains the legacy RAM/register/cycle/`same_frame`
  predicate. Coordinate-aware evidence must additionally require
  `comparison.same_movie_coordinate`, `comparison.same_phase`,
  `comparison.coordinate_neutral`, and `comparison.comparison_valid` to all be
  true; `comparison_valid` is an alias of `coordinate_neutral`, not a trace-
  completeness proof. Also require both mapped `current_movie_frame` values when
  the claim needs coordinates, both replay execution results to be complete, and
  every bounded coverage snapshot to report `truncated:false` with a declared
  range that covers the claim.
- `debugger.status.execution_mode` separates configured, effective, and last
  dispatched CPU modes, reports `transition_pending`, gives override
  reasons/subsystems, and retains a bounded frame/cycle history. Record
  `history_total`, `history_retained`, `history_capacity`, `history_dropped`,
  `history_truncated`, and every retained entry's monotonic `sequence`. To prove
  an evidence interval, prefer a beginning snapshot with
  `transition_pending:false` and `last_dispatch == effective == <required mode>`.
  Retain beginning/end totals and show that every sequence from the beginning
  total plus one through the ending total is present and contiguous, inspecting
  every `to` mode. An ending total below the beginning total means the CPU runtime
  restarted and invalidates the interval. Require the ending `transition_pending:false` and
  `last_dispatch == <required mode>`. If the beginning was pending, the first new
  entry must connect its `last_dispatch` to its `effective` mode. A globally
  truncated ring is acceptable only when that complete interval-specific sequence
  remains retained. History records actual effective-mode changes only: an
  override-subsystem change which leaves the mode unchanged needs separate live/
  boundary `override_subsystems` evidence. Final mode strings alone never prove
  how the window executed.
- Prefer `debugger.scatterRead {atomic:true}` for evidence reads, or set
  `invalidValuePolicy` to `omit`, `null`, or `error`. Never consume a legacy
  numeric value from an item whose `valid` bit is false.
- `trace.assert` turns retained or normalized traces into executable evidence:
  hit/no-hit counts, first/last times, register or captured-memory values, event
  order, signed frame/cycle deltas, and truncation requirements. Add bounded
  pre-instruction RAM samples with `execTrace.addWatch`/`addRangeWatch`
  `capture_memory:[{address,width}]` when assertions need memory-at-hit rather
  than a later read.
- `debugger.xrefsAcrossOverlays` preserves overlay identity while resolving
  runtime/source targets and base-plus-offset/mask references. Use
  `evidence.captureBundle` for the audit envelope and `trace.export` for JSONL or
  TSV. Keep exported traces, states, media, movies, screenshots, and bundle
  payloads outside Git; retain hashes and preservation metadata in ABL.
- Use movie input primitives for intent-labelled work:
  `movie.findInputEdges`, `movie.resumeUntilInputEdge`, persistent
  `movie.setBookmark`/`listBookmarks`, and bounded `movie.timingSweep`. A timing
  sweep creates registered variants; each variant still needs a deterministic
  replay and complete `trace.assert`/scenario predicate before it supports a
  conclusion.

## Reach for the narrowest API

| Question | Current surface |
|---|---|
| What led to a visible failure? | Arm `reverse.start` before the window, then use `reverse.step` / `reverse.seek`. |
| What called or was touched by a function? | `functionTrace.*`, `execTrace.*`, symbols, and `debugger.xrefsTo`. |
| Who read or wrote this state? | `accessLog.*`; use instruction-attributed PCs and prove totals/pagination/truncation. |
| Which guest code produced this drawable? | `gpu.causality.*`, `gpu.pickObject`, `gpu.traceRegion`, and VRAM/CLUT provenance helpers. |
| Where did RAM/VRAM data originate? | `transferLog.*`, `gpu.vramWriteLog.*`, and `provenance.timeline`. |
| Which overlay occupies this runtime region, and did it change? | `memory.getResidency`; pin its source identity, resident hash, and load generation before and after the observation. |
| Which overlay contains a static reference? | `debugger.xrefsAcrossOverlays` with explicit overlay source/base/generation identities. |
| Does a movie's current state file match its recorded binding? | `movie.startPlayback {load_start_state:true}` and require `hash_verified:true` plus `start_state_binding.verification:"verified"`. |
| Did a requested advance actually reach its target? | Inspect the structured execution result (`completed`, `stop_reason`, `stop_details`). |
| Do retained events satisfy the claimed relationship? | `trace.assert`, including a non-truncation assertion and hit/order/delta/value predicates. |
| Preserve one auditable run? | `evidence.captureBundle` plus machine-readable `trace.export`, written outside Git. |
| Is logic tied to emulated audio? | `spu.status`, `spu.trace.*`, `spu.events.get`, and `spu.provenance.get`. |
| Reach an edited-disc scene reproducibly? | Cold boot plus `movie.*` and fixed-frame/timing assertions; do not substitute a pristine save. |

## High-cost gotchas

- **Movie replay + CPU tracing: record the movie on `Interpreter`.** Arming any
  CPU-level instrumentation (`accessLog` watches, `execTrace`, breakpoints) forces
  `CPUExecutionMode::Interpreter` — `CPU::CheckForExecutionModeChange` in
  `src/core/cpu_core.cpp`, *"Currently, any breakpoints require the interpreter"*.
  A movie recorded on `CachedInterpreter` therefore desyncs the instant anything is
  armed. Recorded and replayed on `Interpreter`, arming is provably free. See
  [[EXP_interpreter_recorded_movies_survive_full_instrumentation]].
- **Halting breakpoints do not desync an Interpreter replay, but they stop the core
  MID-FRAME**, so any snapshot taken while halted is a mid-frame snapshot and will
  not match a clean run. A successful advance RPC is not target completion: require
  `execution.completed:true`, or treat its structured `stop_reason` and exact
  breakpoint/watchpoint details as the actual endpoint.
- **State-anchored movies historically replayed one frame out of phase while still
  reporting reproducible.** Do not infer alignment from `reproducible`. Use
  `movie.loadAndArm`, preserve its phase policy/result, and require the mapping and
  `phase_correction_*` audit fields from `movie.status`. The correction belongs to
  legacy v1 movies or movies recorded while paused; merely arming playback paused
  does not create it. The historical diagnosis
  remains in [[EXP_2026-08-01_savestate_movie_arm_phase_desync]].
- **`movie.advanceToFrame` is NOT equivalent to 60 Hz playback** for anything
  phase-sensitive: the same movie gave 0 vs 401 timer writes in the two regimes.
  Verify with `debugger.resume` + polling, not frame stepping.
- ⚠️⚠️ **A PC watch is an ADDRESS watch, not a code watch.** On a **from-boot** movie
  the game EXE is not resident for roughly the first 1,000 frames, so an
  `execTrace` PC watch faithfully records executions of whatever else occupies that
  address during boot. Measured 2026-08-10: a watch on `0x8004FF48` reported **327**
  hits, of which **326** were pre-load — `debugger.readMemory` gives
  `[0x8004FF48] = 0x00000000` at movie frames 300 and 700, and `jal 0x80045A60`
  only by frame 1200. **Give every watch a `capture_memory` entry reading the
  instruction word at its own PC and count an event only when it matches the
  pristine image**; that removes the noise at source rather than filtering it after.
  Also scope counts by `cycle` to the event that caused them — a whole-run total
  spans unrelated phases. State-anchored movies are immune (the EXE is resident at
  the anchor), as are pure memory write-watches. See
  [[EXP_2026-08-10_phase4_f01_original_oracle]].
- `emulator.advanceFrames` takes `frames`, not `count`.
- Reverse history and every retained trace are bounded; they prove only the armed
  window. A zero-hit result outside a justified complete window is not absence.
- `emulator.loadState` clears non-halting instrumentation. Load first, verify
  media, then re-arm watches/traces.
- Data-access callbacks report the pre-access value; use `new_value` only where
  supported and independently read the post-value when it matters.
- `gpu.pickObject` uses native CRTC coordinates. GPU causality and SPU provenance
  must be armed before the render/audio event.
- `spu.events.get` completion is emulated voice completion, not host-speaker drain.
- A successful RPC transport result does not prove each scatter item or write was
  applied. Use atomic/fail-safe scatter modes and inspect the aggregate and
  per-item validity/application fields.

## Freshness and provenance

Regenerate the machine and Markdown layers with:

`python3 tools/phase3_duckstation_rpc_manifest.py`

Verify them without rewriting against the exact local fork with:

`python3 tools/phase3_duckstation_rpc_manifest.py --check`

The safe guard recomputes list/set/count consistency, deterministic Markdown, and
this Canon linkage. The executable Phase-3 gate and local-media guard both
re-extract the current fork and check the revision, complete dirty status,
dispatcher/docs/client/launcher hashes, both Phase 3 binaries, and all 220
methods. Long replays create a read-only verifier-owned executable sibling in the
canonical application directory, copy the pinned client/launcher under `/tmp`, and
verify the independently pinned runtime-support tree before and after replay. See
[[EXP_2026-07-14_phase3_iteration10_hook_toolchain_closure]].

The superseded pre-revamp index is retained at
`ObsidianVault/Archive/Superseded/Indexes_DuckStation_API_Index.md`; it must not be
used as current authority.
