# ABL reverse-engineering — working instructions

This project reverse-engineers/mods Disney·Pixar **"A Bug's Life" (PS1, SCUS-94288)** by driving **DuckStation via its CUSTOM external-debugger JSON-RPC API**. Persistent findings live in the auto-memory and `ObsidianVault/`.

## ⚡ REACH FOR THE DUCKSTATION API BEFORE BRUTE-FORCING
DuckStation here has a large **custom debugger API you will NOT know from training** (VRAM, GTE, object-picking, frame-diff, tracing, movie, experiment runner, …). The #1 recurring failure is defaulting to RAM-poking/brute force and forgetting these exist. **Before brute-forcing, check whether an API feature fits.** Full reference (orientation only — verify calls against the running emulator): `ObsidianVault/Canon/Indexes/DuckStation_API_Index.md`.

**Symptom → reach for:**
- *"Which RAM object is this on-screen thing?"* → **gpu.readVramRect / gpu.pickObject / GTE state / decodeTexture / frame-diff** — NOT a RAM brute-force search. (Frame-diffing an **animated** object needs a *phase-matched control* run, else it flags everything.)
- *"Which overlay is resident / where did these RAM bytes come from?"* → **memory.getResidency** first; bind the
  `(residency_epoch,load_generation,residency_revision,resident_memory_hash)` token at resolution and stop. Use
  **transferLog** for supporting live-load history, not current-residency identity.
- *"Did my edit change the screen / did it work?"* → **captureFrame + diffFrames** (settle a few frames first — capture→diff flush race).
- *"Reproduce a setup / reach a level from a cold boot of an edited disc"* → **movie + advanceFrames** (`flik_to_level01_stall.mv.movie.json` replays boot→LEVEL01; save states are on the pristine image so they DON'T show disc edits).
- *"Read / watch / scan memory"* → readArray, fail-safe `scatterRead` (`atomic:true` or
  `invalidValuePolicy:"omit"|"null"|"error"`), scatterWrite, accessLog (write-watch = who wrote this), execTrace,
  memoryScan.
- *"Load → perturb → advance → diff"* → experiment.run.

## ⚡ 2026-08-04 API correctness gates

- Start by pinning `debugger.capabilities`: 220 dispatched methods; runtime capabilities reports 221 including
  `debugger.authenticate`. Preserve source dirty-state and running-binary hashes.
- Use `movie.loadAndArm` for movie experiments. It preflights movie/media/start state before mutation, then re-verifies
  `expected_media` after the state load (states can replace the mounted path) before clearing traces or executing;
  preserve `media_after_start_state`/`media_changed_during_setup`. It consumes a requested pending phase correction
  before arming observers and returns a named paused boundary. Require
  `atomic_scope:"serialized_request_to_paused_arm_boundary"` and `transactional_rollback:false`; on failure inspect
  `error.data.failure_cleanup` and re-establish anything not restored. After a state-driven disc swap require
  `media_identity_restored:true`; machine-state restoration alone is not mount restoration.
- New state-anchored recordings persist a recording-start SHA-256 with
  `sha256_origin:"recording"`; ABL's 123 existing anchored fixtures were
  backfilled on 2026-08-05 and remain explicitly `sha256_origin:"backfill"`.
  Pass `movie.startRecording.start_state` as the absolute path string itself,
  never as `{"path":...}`; a non-null non-string must fail `-32602` before any
  movie/reset mutation.
  For direct replay, pass `load_start_state:true` and require
  `hash_verified:true` plus `start_state_binding.verification:"verified"`.
  Mismatch or malformed metadata fails before mutation. `evidence.captureBundle`
  is non-mutating and does not backfill a movie; its state hash is not a
  substitute for this comparison proof.
- `movie.status` returns anchor/current movie and emulator frames, their offset,
  `movie_to_emulator_offset_basis`, `mapped_anchor_emulator_frame`,
  `anchor_to_mapped_frame_delta`, and pending/consumed phase metadata. The
  legacy anchor is the playback-arm/setup boundary; the offset maps
  sample-effective frames. Delta `0` is aligned and `1` is correction-bearing,
  so anchor and offset are not interchangeable. Never label an observation with
  an unqualified frame number.
- For every bounded method advertised in `schema_coverage.structured_execution_stop_result_methods`, require
  `execution.completed:true`. Actual early-stop progress is `execution.advanced_frames`; legacy top-level
  `frames_advanced`/`framesAdvanced` retains its historical requested-count or movie-coordinate-delta meaning. The five
  legacy debugger controls (`stepInstruction`, `stepOver`, `stepOut`, `advanceFrame`, `runUntilAddress`) preserve their
  immediate top-level status and add the actual stopped snapshot as `end_status`.
- Preserve `debugger.status.execution_mode` across the evidence window, including `history_total`, retained/capacity,
  dropped/truncated, `transition_pending`, and each entry's monotonic `sequence`; final mode strings alone prove
  nothing about an interval.
- `debugger.capabilities.methods.<name>.scenario_execution_policy` is authoritative. While an async batch owns the
  runtime-only gate, an exclusive direct call fails fast with `-32005`/`scenario_execution_busy`; observation and
  get/cancel/resume batch calls remain responsive. New methods default fail-safe to exclusive.
- `movie.traceToFrame` keeps legacy `movie_frame`=`playback_index` and legacy `same_frame`/`cycle_neutral` predicates.
  Coordinate-aware evidence requires `current_movie_frame`, `same_movie_coordinate`, `same_phase`,
  `coordinate_neutral`, and `comparison_valid`.
- Runtime residency generations, movie anchors/phase audit, execution-mode history, and gate ownership are never
  serialized and do not change `SAVE_STATE_VERSION`.

## Isolated instance (never touch the user's own DuckStation)
Use `scripts/debugger-client/launch_debugger_instance.sh start` with a fresh absolute `--config-dir`, dedicated
loopback `--port`, and dedicated `--token` for every live run. Verify `emulator.getMediaInfo` after connecting and stop
only the PID whose ownership the launcher proves from that config directory. Driver: `tools/abl_dbg.py`; authenticated
RPC calls have structured core-unresponsive failures, but clients should still use a finite transport timeout.

## ⚡ MOVIE REPLAY + CPU TRACING — record the movie on `Interpreter`
**VERDICT: `Interpreter` has NO known desyncing issues.** Ten runs / five movies /
four levels / ~35 bn cycles, from-boot and state-anchored, through FMV and XA
streaming, with the event ring overflowed — every armed run byte-identical to
clean, **final cycle delta exactly 0** every time. Trace freely. The desync
belongs to `CachedInterpreter`, and it is silent (`reproducible: true`, no error).

Arming ANY CPU-level instrumentation (`accessLog` watches, `execTrace`,
`debugger.addBreakpoint`) forces `CPUExecutionMode::Interpreter` — see
`CPU::CheckForExecutionModeChange` in `src/core/cpu_core.cpp`: *"Currently, any
breakpoints require the interpreter."* A movie recorded on **CachedInterpreter**
therefore **desyncs the instant anything is armed**, silently: the game drifts
off-script, the awaited event never fires, and the capture looks plausible but
empty. That is the real cause of the long-standing "traces come back empty"
problem — NOT a bug in execTrace.

- **Record and replay on `Interpreter`** for anything you may want to trace. Then
  arming requests the mode already in use, nothing switches, and instrumentation
  is free — ⚠️ **established under `movie.advanceToFrame` only; not yet re-proven
  at 60 Hz** (see the arm-phase section below for why the two regimes differ): clean vs fully-armed replay of a 7,984-frame movie was
  byte-identical — full 2 MiB RAM sha256 equal at all 32 sample points, **final
  cycle delta exactly 0** — while logging 13,870 access + 10,000 exec events.
  `tools/launch_repro_playback.sh --execution-mode Interpreter`.
- **The existing CachedInterpreter movies stay valid for POLL-ONLY work** (the
  Phase-2 oracle, completion oracle). They can never be traced. Re-record on
  `Interpreter` per level when you need to trace that level.
- The old **arm-late ritual is obsolete** on Interpreter-recorded movies; you can
  arm at frame 0, which also closes the boot shadow.
- **NON-HALTING instrumentation is completely free** on an Interpreter-recorded
  movie — `accessLog` watches, `execTrace`, `accessHistory`, `transferLog`, even
  with the 200k event ring deliberately overflowed (`truncated: true`). Proven
  across 5 movies / 4 levels, from-boot and state-anchored, through intro+outro
  FMV and sustained XA streaming, ~35 bn cycles, every run byte-identical.
- **HALTING breakpoints** (`debugger.addBreakpoint`) do NOT desync the run either
  (cycle delta 0 over 2,659 hits) — but they stop the core MID-FRAME, so a
  snapshot taken while halted is a mid-frame snapshot and won't match a clean run.
  Resume to a frame boundary before sampling. The on-screen flicker between whole
  and partially-drawn frames is exactly this, and is harmless.
  ⚠️ `movie.advanceToFrame` returns a normal RPC response when a halting
  breakpoint stops it early. Require `execution.completed:true`; otherwise inspect `stop_reason`, exact
  `stop_details`, and `execution.advanced_frames` or you will compare different frames and invent a desync.
  ⚠️ `movie.advanceToFrame` takes a movie coordinate even for a state-anchored movie. Preserve the returned
  movie/emulator coordinates and mapping rather than performing an implicit conversion.
- **Unaffected by all of this** (no CPU hook, safe during any replay):
  `transferLog`, all GPU/VRAM/frame-diff/pickObject tooling, `memoryScan`,
  `readArray`/`scatterRead`, register/GTE reads, save/load state.
- Evidence + scope limits: `ObsidianVault/Experiments/EXP_2026-07-31_interpreter_movies_survive_instrumentation.md`.

## ⚡ SAVE-STATE MOVIES: ARM-PHASE DESYNC (one frame) — PROVEN 2026-08-01
A state-anchored movie can replay exactly ONE FRAME out of phase with how it was
recorded, and it fails SILENTLY: `reproducible` still reports true, no error, the
run just drifts off-script. Cause is in the fork's own `src/core/input_movie.cpp`:
the phase fixup at :324 only fires when `GetFrameNumber() == s_arm_frame && ...
Mode::Playing`, i.e. only when arming happened inside a RUNNING FrameDone. The
comment at :33 states the other case — *"When armed while paused, the first
callback belongs to the next frame."* Recording deliberately falls through
(*"omitting it shifts the entire movie one frame early on replay"*).

- **PROVEN on `movies/b06_desync_test.movie.json`**: as-recorded it desyncs (Flik
  never collects the invincibility — 0 writes to the timer 0x800A657E). With the
  input stream shifted **+1 frame later**, the grant fires at frame 8282 with
  value 400 and the run matches what the operator recorded. Operator confirmed
  visually; the grant is the objective marker.
- ✅ **FIXED IN THE FORK 2026-08-01 (movie format v4)**: `StartRecording` now
  records the arm phase as `armed_while_paused`; `StartPlayback` inserts the one
  neutral frame itself when it is set. **New recordings are self-correcting.**
  `movie.status` reports `movie_version` / `armed_while_paused` /
  `phase_delay_owed` so the correction is visible instead of silent.
  ⚠️ Requires the rebuilt `duckstation-qt` (re-touches the Phase-3 binary pins).
- **FIX AN EXISTING BROKEN MOVIE**: `tools/rephase_movie.py IN OUT --tag-arm-phase`
  (preferred — sets the flag, frames untouched) or `--shift +1` (rewrites the
  stream; works on pre-v4 builds). Never overwrites.
- ⚠️ **DO NOT blanket-tag the movie corpus.** Most existing movies replay
  correctly as-is (Phase-2 oracle: 701 comparisons, 0 mismatch) — "fixing" those
  breaks them. Correct only a movie shown to be one frame early.
- Verified on the rebuilt binary at 60 Hz: untagged → `phase_delay_owed: false`,
  0 grants (byte-for-byte today's behaviour, so no existing fixture moves);
  tagged → `phase_delay_owed: true`, grant at frame 8282 value 400, 401 timer
  writes — identical to the externally-rephased movie. Operator confirmed both
  visually (first desyncs, second does not).
- ⚠️ **`movie.advanceToFrame` IS NOT EQUIVALENT TO 60 Hz PLAYBACK.** The same LATE
  movie showed 0 timer writes under advanceToFrame and 401 at 60 Hz. advanceToFrame
  does not drive frames through the same PumpMessages→poll→OnFrameDone path, so the
  arm-phase fixup lands differently. **Verify anything phase-sensitive at 60 Hz**
  (`debugger.resume` + poll), not with frame stepping.
- The movie format records neither the CPU mode nor the arm phase nor the start
  state's sha256 (`sha256: null`) — three unverified bindings, all of which fail
  silently. Prefer new filenames; never overwrite a `.sav` another movie declares.

## Gotchas (cost real time — see API Index "Gotchas" section)
- `emulator.advanceFrames` param is **`frames`**, not `count`.
- `loadState` **hard-crashes** when a *different disc* is mounted than the state was made on — match the disc first.
- **Re-arm** watches (accessLog/execTrace/transferLog) after every `loadState`.
- Teleporting the player far drops into **unstreamed "void"** geometry and can crash; heavy repeated pokes destabilize the instance → relaunch + fresh movie per clean run.
- Build edited discs to a **separate** output file; keep `Disney-Pixar A Bug's Life (v1.0).bin/.cue` pristine. LEVEL.DAT is uncompressed (disc==RAM); LEVEL.RAW is compressed (codec in `tools/decode_level_raw.py`/`recompress_level_raw.py`).
