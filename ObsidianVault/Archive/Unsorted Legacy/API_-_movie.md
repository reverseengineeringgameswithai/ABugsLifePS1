---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - movie.md
aliases:
  - "API - movie"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - movie.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - movie
type: api
category: Execution control
tags: [api, duckstation, movie, input, tas, determinism]
---
# API — movie (input recording / playback)

> Record the effective per-frame controller input and replay it frame-by-frame (a minimal TAS movie). The deterministic way to capture and reproduce a whole input sequence, not just one hold.

> [!success] Updated 2026-06-26: **analog input now recorded** (format **v3**). Each frame stores all 16 buttons (incl. `l3`/`r3`) **and** the analog stick axes (`lx`/`ly`/`rx`/`ry`, 0..255, 128=centre — the effective DualShock/analog-pad bytes the pad latched); replay applies them directly. Older digital-only v1/v2 files still load (axes default to centre). Rumble and the analog-mode toggle press are NOT recorded — the toggle rides in the pinned start state. **verify in `~/duckstation` before relying on analog replay.**

> [!success] Updated 2026-06-18: **GUI record crash FIXED** + new **record-from-boot** mode (API + GUI). Live-validated: from-boot record→save→load→replay is **bit-exact** (8 KB RAM @ `0x80080000` hash match) on SCUS-94288.

## Anchors (how a movie is made reproducible)
1. **Save state** — `start_state` + `load_start_state` (bit-exact from that state).
2. **From boot** — `from_boot:true`: power-cycle (`debugger.reset`) and record from frame 0; no save state, replay re-boots. The "record from power-on" mode other emulators have. Reproducible from a cold boot of the same disc + pinned settings.
3. **Current state** — neither (records from wherever the emulator is).

## Methods & syntax
- **`movie.startRecording {ports=[0], start_state?, load_start_state?=true, from_boot?=false, notes?}`** — `start_state`+`load_start_state` loads that save state first (aborts if the load fails) and binds it; **`from_boot:true`** (mutually exclusive with `start_state`, else `-32006`) resets the console and records from boot; else records from the current state. Clears any previous movie.
- **`movie.stopRecording`** → status (`frame_count`); movie kept in memory.
- **`movie.save {path, overwrite?=false, notes?}`** / **`movie.load {path}`** — JSON file (absolute path; parent must exist; no overwrite unless asked). `start_state.from_boot` round-trips.
- **`movie.startPlayback {start_frame?=0, load_start_state?=false}`** — `load_start_state` restores the recorded anchor first (`reproducible:true`): loads the start state, or **power-cycles** for a `from_boot` movie; primes the first sample.
- **`movie.advanceToFrame {frame, max_frames?=100000}`** — requires active playback; temporarily enables turbo speed control and advances the movie `playback_index` to the requested 0-based movie frame by advancing the emulator and consuming every intervening input sample. `frame == frame_count` advances to the end and stops playback. Backward/out-of-range targets are rejected. Client: `movie-advance-to-frame --target-frame N`.
- **`movie.stopPlayback`** (releases recorded buttons) · **`movie.status`** · **`movie.clear`** (only when idle).
- **GUI:** Tools ▸ *Record Input Movie...* (save-state anchor), *Record Input Movie from Boot...* (boot anchor), *Play Input Movie...*.

## (new) In-memory movie registry — store / branch / edit
> [!success] (new) Movies now have **append / branch / per-frame edit** — the [[DuckStation API Index]] "no append/branch/edit" footgun is retired. A keyed in-memory **registry** holds movies (`movieId` like `mov1`); `rerecord_count` is tracked; edited movies **replay deterministically**.
- **`movie.store {}`** → snapshots the current loaded/recorded movie into the registry → `{movieId, ...}`. **`movie.list`** / **`movie.get {movieId}`** / **`movie.remove {movieId}`** manage entries.
- **`movie.append {movieId, inputs}`** — append frames (per-frame port input maps) to the end of a registry movie.
- **`movie.branch {movieId, fromFrame}`** → a **new** movie keeping `[0, fromFrame)` of the source; the original is left intact (returns `{movieId, branchedFrom, fromFrame, ...}`). The clean way to fork a run at a decision point.
- **`movie.editFrame {movieId, frame, input}`** — overwrite a single frame's input (port input map). The TAS-style frame edit.
- **Per-frame `input` shape:** `{ "<port>": { "<button>": bool, …, "lx"/"ly"/"rx"/"ry": 0..255 } }` — analog axes are optional and default to 128 (centre); omitted/`false` buttons are released. Unknown button/axis names and out-of-range axes are rejected.
- **`movie.activate {movieId}`** — load a registry movie as the **active** in-memory movie (then `movie.startPlayback` / `movie.save` it). **Fails while recording or playing** (`-32005`-style) — stop first.

## Best use in ABL RE
Capture a reproducible Flik input run once (e.g. walk to a spot + jump), then replay it deterministically before/around an experiment so the setup is identical every time — the superset of [[API - controller input]] + fixed [[API - execution control|advanceFrames]] / [[API - advanceToFrame|advanceToFrame]] for [[API - determinism]]. Anchor the movie to a [[Save States Index|save state]] via `start_state` so playback is bit-exact.

## Common mistakes / gotchas
- **Records the EFFECTIVE state** (after override), not the request — for buttons **and** analog sticks (v3). Replay drives the recorded axis bytes directly, so it bypasses host deadzone/sensitivity/inversion and reproduces the latched values regardless of the replayer's pad config. Analog mode itself is captured by the pinned start state, not the movie — replay from the anchor, or the sticks won't be read.
- Reproducible **only** from the recorded start state with pinned settings (Rewind/Run-ahead off) — see [[API - determinism]]. CPU+RAM are bit-exact; audio/CD-async timing are not.
- A foreign `loadState` (debugger **or** GUI/hotkey), a console **reset**, game unload, or server stop **stops** an in-flight movie (data kept) so it can't desync.
- Recording and playback are mutually exclusive. During playback the movie **overrides** [[API - controller input|injected input]] for the recorded ports. Generic `emulator.advanceToFrame` also works during playback when targeting an absolute emulator frame. Both `advanceToFrame` helpers temporarily enable turbo; use `movie.advanceToFrame` for a movie playback frame.
- ~~No editor, no rerecord/branching.~~ **Now supported** via the in-memory registry (`movie.append`/`branch`/`editFrame`) above — but those operate on **registry** movies, and `movie.activate` **fails during active recording/playback**, so edit *before* you play.
- **Fixed bug (2026-06-18):** the GUI Tools-menu record/play handlers crashed (`std::bad_alloc`/heap corruption) because they marshalled to the core thread **non-blocking** (`Host::RunOnCoreThread` defaults `block=false`) while capturing stack locals by reference → use-after-free. Fix: pass `block=true`. The API path was unaffected (it already blocks).

## ABL examples
Record `record-input-movie --state <SCUS-94288 sav> --movie /tmp/flik.movie.json --direction right --frames 60`, then `play-input-movie --movie /tmp/flik.movie.json --load-start-state` or `movie-start-playback --load-start-state` + `movie-advance-to-frame --target-frame 60` — verified bit-exact (registers + input-sensitive RAM `0x80080000`) on the SCUS-94288 disc.

## Related
[[API - controller input]] · [[API - advanceToFrame]] · [[API - determinism]] · [[API - loadState]] · [[API - saveState]] · [[API - experiment runner]] · [[API - execution control]] · [[Save States Index]]

Source: ~/duckstation/docs/external-debugger-movie.md (+ EXTERNAL_DEBUGGER_CONTROL.md, docs/external-debugger.md §5)
