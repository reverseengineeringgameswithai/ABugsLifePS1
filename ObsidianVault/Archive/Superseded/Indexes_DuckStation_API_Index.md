---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Indexes/DuckStation API Index.md
aliases:
  - "DuckStation API Index"
  - "DuckStation API - Index"
migration_action: merge
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Indexes/DuckStation API Index.md`
- Replacement/current location: `ObsidianVault/Canon/Indexes/DuckStation_API_Index.md`
- Archive reason: Index material should be regenerated around Canon IDs.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: DuckStation API Index
type: index
updated: 2026-07-08
tags: [index, api, duckstation]
---

# DuckStation API Index

> Capability map of the DuckStation **external debugger** (JSON-RPC 2.0, single TCP port, WebSocket/raw). 38 feature notes. Connect/auth first; **re-arm non-halting instrumentation after every `loadState`**. Source: `~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md`, `~/duckstation/docs/external-debugger*.md`, client `~/duckstation/scripts/debugger-client/`.

> [!important] How to use this index (source-of-truth hierarchy)
> This index is a **map for orientation**, not the contract. Method names, param shapes, and behavior have drifted from the notes. Before depending on a call, verify down this chain: **index → detail note → client source `duckstation_debug_client.py` → the running emulator (final arbiter).** When the docs and the runtime disagreed this session, the runtime always won (`advanceFrames` param, `scatterWrite` shape). Verify a named method/flag still exists before recommending it.

## Connection & control
- [[API - connection and auth]] — transport, port 2346 (build-test 23460), authenticate, batch, errors
- [[API - execution control]] — pause/resume/step/runUntilAddress/advanceFrames/advanceToFrame/registers; `debugger.snapshot` for compact JSON RE state bundles
- [[API - advanceToFrame]] — turbo-backed fast-forward to an absolute emulator frame
- [[API - advanceUntil]] — advance one frame at a time until a condition
- [[API - trace.armWhen]] — wait for a condition, then clear/start selected trace/log systems
- [[API - controller input]] — scripted, frame-accurate input
- [[API - movie]] — record/replay controller input (TAS-style, deterministic); `movie.coverageToFrame` replays to a movie frame while returning exec-range distinct-PC coverage
- [[API - determinism]] — the reproducibility contract + CONFIRMED/LIKELY rubric
- [[API - crash diagnostics and logging]] — console log capture (50 MB rotating) + per-request logging for crash correlation
- [[API - crash safety and health events]] — 5000 ms core-call timeout (`-32005 core_unresponsive`) + pushed guestHalted / guestReset events

## Memory
- [[API - readArray]] — readArray/readStruct/readPointerChain/readCString/readMemory
- [[API - scatterRead]] · [[API - scatterWrite]] — non-contiguous batch read/write
- [[API - memoryScan]] — Cheat-Engine-style scanner
- [[API - code cache invalidation]] — writeMemory/writeU* auto-invalidate + invalidateCodeCache (live code patches take effect, no breakpoint toggle)

## Tracing (non-halting — re-arm after loadState)
- [[API - accessLog]] — read/write watches, instruction-attributed events, summaries, lastWriter/findFirstWrite
- [[API - addWatch]] — the shared watch model
- [[API - execTrace]] — PC + register/GTE capture, range traces, server-side hot-PC summaries, call/return edge analysis, and coverage-only movie-span range coverage
- [[API - exec range and access history]] — function/range execution trace + PC-scoped effective-address/recent access history
- [[API - transferLog]] — CD/DMA provenance (LBA → RAM)
- [[API - gp0Trace]] — GP0 display-list trace
- [[API - provenance.timeline]] — linked retained-log timeline across RAM, DMA/CD, CPU access, and VRAM uploads

## Disc
- [[API - CD overlay]] — substitute file/sector bytes read off the CD (no disc rebuild); persists across loadState
- [[API - media control]] — cold-boot from a disc (bootSystem) + eject/insert a different disc image (getMediaInfo/closeMedia/loadMedia); no CPU/RAM reset on swap; drops CD overlays

## GPU / GTE
- [[API - gpu.pickObject]] — screen pixel/region → GP0 draw(s), geometry, structured texture/CLUT/draw-mode, RAM/DMA pointer provenance
- [[API - gpu.readVramRect]] — VRAM rect read/write + status + CLUT; `gpu.vramWriteLog.get` plus `gpu.resolveVramProvenance` / `gpu.resolveClutProvenance` for retained upload provenance
- [[API - framebuffer capture]] — captureVramRect / frameSnapshot (deterministic, flip-race-free; displayed vs drawing buffer; png/rgba/raw16)
- [[API - decodeTexture]] — decode VRAM texture to image
- [[API - GTE state]] — decoded GTE/COP2 + PGXP
- [[API - camera transform]] — best-effort camera view/projection + position/orientation from the GTE (approximate)

## Frames & visual diff
- [[API - frame capture]] — captureFrame / video status
- [[API - frame hashing]] — perceptual/sha256 hash
- [[API - visual diff]] — diffFrames (pixel diff + bbox + score) — file-based; legacy for live frames
- [[API - in-memory frame diff]] — gpu.captureFrameSnapshot + diffCurrentFrame (RAM-to-RAM, race-free)
- [[API - snapshot bundle]] — atomic composite snapshot

## State, experiments, findings, symbols
- [[API - loadState]] · [[API - saveState]] — save-state API
- [[API - experiment runner]] — load→perturb→advance→diff (experiment.run / compareRuns)
- [[API - findings store]] — persistent YAML findings/fixtures (load-before-save!)
- [[API - symbols]] — labels/comments + import/export
- [[API - xrefs and function bounds]] — debugger.xrefsTo / functionBounds (find callers + function extent, no hand-scanning)

## ⚠️ Gotchas & known failures (learned the hard way, 2026-06)
Operational truths the per-feature notes don't model — each cost real time:
- ~~**`loadState` HARD-CRASHES the instance when a *different disc* is mounted**~~ **MOSTLY FIXED:** `loadState` now validates the disc by default and returns `-32006` with `error.data.expected/current` instead of crashing; `auto_select_disc:true` inserts the right disc. → [[API - loadState]] · [[API - media control]]
- **The RPC socket can BLOCK on a guest crash** — server-side now guards with a **5000 ms core-call timeout** (`-32005 core_unresponsive`) + a pushed `guestHalted` event, but still set `c.transport.sock.settimeout(...)` and reconnect-on-reset for a dead socket. → [[API - crash safety and health events]] · [[API - crash diagnostics and logging]]
- **`transferLog.get` still returns nothing from a post-load save state unless you re-arm and replay the load**, but
  **`transferLog.resolve {address}` now gives static RAM→disc/file provenance** for EXE-backed addresses immediately and
  for streamed assets whenever the transfer log captured the load. The old manual decompress+grep path is no longer the
  first resort. → [[API - transferLog]]
- **Teleporting the player far (RAM-poking position) drops into UNSTREAMED geometry** ("void" background) and can crash. Hold the position over several frames with try/except + reconnect; expect no clean visual far from where the level already streamed. Heavy repeated teleports destabilize the instance → relaunch + fresh movie per clean run.
- **Reach an EDITED-disc level from a COLD BOOT** (save states are on the pristine image — they don't show disc edits AND `loadState` crashes on a mismatched disc): `emulator.bootSystem {path, force:true}` (**`force:true` is required when a system is already loaded** — else `-32005 "A system is already loaded"`) → `movie.load` + `movie.startPlayback {load_start_state:true}` of a **`from_boot` movie** → `movie.advanceToFrame {frame:N}` (movie playback frame) or `advanceFrames {frames:N}` in chunks; when the task is "replay this movie while collecting which PCs in a range executed," use **`movie.coverageToFrame {frame:N,start,end}`** instead of client-side advance/summary/status loops. **Raw `advanceFrames`/`advanceToFrame` alone CANNOT pass the boot/menus — it injects NO controller input;** the movie supplies the boot→level button presses. For ABL: `flik_to_level01_stall.mv.movie.json` (from_boot, 4253 frames) reaches LEVEL01 / the **Tier-3 custom level at ~4500 advanced frames** (detect via Flik pos `0x800a6500` going non-zero; Tier-3 custom spawn = `197091,-266,492897`). **Detachment:** an instance launched via `launch_debugger_instance.sh` **survives** across later client tool-calls (it orphans the emulator with a bare `&` — verified alive across calls), so **no `setsid` needed**; only if you bypass the launcher and run `duckstation-qt` directly must you fully detach it (`setsid … </dev/null &`) or it dies with the parent shell.
- **Animated objects make naive `diffFrames` flag EVERYTHING.** Diff against a **phase-matched control** (reload + same frame count, no perturbation), not a fixed baseline. → [[API - visual diff]] · [[API - experiment runner]]
- **`captureFrame` can return before the PNG is flushed** → an immediate `diffFrames` reads a partial file (inflated diff). **Fix: use [[API - in-memory frame diff|gpu.captureFrameSnapshot + diffCurrentFrame]] (RAM-to-RAM, no PNG).** For file-based, settle a few frames or re-read with PIL. → [[API - frame capture]] · [[API - in-memory frame diff]]
- ~~**Movie has NO append/branch/edit.**~~ **NOW SUPPORTED** via the in-memory registry: `movie.store`/`append`/`branch`/`editFrame`/`activate`. `activate` fails while recording/playing, so edit before you play; still `movie.stopPlayback` before re-`movie.load`. **~~Digital buttons only (no analog).~~ Analog sticks now recorded too (format v3, 2026-06-26)** — buttons + `lx`/`ly`/`rx`/`ry`. → [[API - movie]]
- **Re-arm ALL non-halting instrumentation** (accessLog/execTrace/accessHistory/accessTrace/transferLog) after EVERY
  `loadState` — they don't survive it.
- **Access-log PC ambiguity is fixed in new builds:** events now carry `reported_pc` plus `instruction_pc`,
  `instruction_word`, `instruction`, and `width`. Use `instruction_pc` for writer/reader attribution; no more manual
  `pc` vs `pc-4` disassembly. `accessLog.summary` / `execTrace.summary` give hot-PC/frame counts without dumping huge JSON; `execTrace.analyze` adds call/return edges, unreturned calls, backward branches, and self-loop hints from retained range traces. **`movie.coverageToFrame` now handles long from-boot movie range coverage in one server-side call and returns `coverage.pcs` / `coverage.counts_by_pc`, avoiding socket-drop-prone chunk orchestration.** Use [[API - trace.armWhen]] to clear/start selected logs at a PC/memory/movie-frame milestone.
- **Shell footgun:** `pkill -f <name>` where `<name>` appears in the running script self-terminates the parent shell (exit 144). Match a more specific pattern.
- **✅ FIXED — live code patches now take effect (was: ran stale).** `writeMemory`/`writeU8/16/32` into *executing* guest code now **auto-invalidate** the covering recompiler block(s) and flush the emulated I-cache, so the new instruction runs on the next frame with **no breakpoint toggle** (response includes `code_invalidated`). Opt out with `{invalidate_code:false}`. New **`debugger.invalidateCodeCache {address?, length?}`** forces it manually (no range ⇒ all RAM blocks; returns `{invalidated, scope}`) — use after an `invalidate_code:false` / scatter / experiment-runner write. Verified on both the recompiler and the pure interpreter. See [[API - code cache invalidation]]. *(Old workaround — toggling an execute breakpoint — is no longer needed.)*
- **Reach for [[API - gpu.pickObject]] / `gpu.traceRegion` for screen→prim→builder, don't hand-roll OT walks.** `gpu.pickObject {x,y, all_contributors?}` maps a screen pixel to the final GP0 drawable with `gp0Index`, raw words, structured `texture`/`drawMode`, geometry (screen/GTE/UV rects), and `source.{ramAddress,vertexPointer,dmaSource,orderingTableEntry}`; `gpu.traceRegion {x,y,width,height}` returns all primitives touching a small screen box. For palette/texture replacement, follow with `gpu.vramWriteLog.get` for the upload timeline, `gpu.resolveVramProvenance {x,y,width,height}` / `gpu.resolveClutProvenance {x,y,entries}` for focused live rects, or [[API - provenance.timeline]] when you need the RAM/DMA/access/VRAM evidence in one sorted report; candidates include retained GP0 VRAM/CLUT uploads, texture-page/UV candidates, payload RAM ranges, transferLog event IDs, and possible CD provenance. (`gp0Trace` **does** capture DMA — `source:"dma"` — verified end-to-end; an earlier "returned 0" was a **static-screen** capture, not a bug: nothing was being drawn. `gp0Trace.get` now reports `dma_count`/`mmio_count` + a `warning`/`note` to diagnose this.)

## Call-shape corrections (verified at runtime — trust these over the notes)
- `emulator.advanceFrames {frames: N}` — param is **`frames`**, NOT `count`; it is a normal speed-limited frame-stepper. `emulator.advanceToFrame {frame:N}` targets an absolute emulator `status.frame` and temporarily enables turbo. (Wrong name silently throws → hangs loops.)
- **`advanceFrames` does NOT fast-forward** — it's a deterministic frame-STEPPER (`System::FrameStep`, `src/core/system.cpp`); it runs N frames through the normal `Execute`/`Throttle()` loop at the **current speed limiter (100% = realtime)**, it does not uncap. A long from-boot movie therefore plays at realtime (~60fps) and can take a minute of wall-clock — the emulator window visibly plays the intro at normal speed. To crunch it, call **`emulator.setTurbo {enabled:true}`** (uncapped; `target_speed:0`) or `emulator.setFastForward {enabled:true}` FIRST, then `advanceFrames` (measured ~5760 emu-fps vs ~60), and disable turbo when done. (2026-07-01.)
- `debugger.scatterWrite {writes:[ {address, hex} | {address, type, value} ], atomic?}` — raw form uses **`hex`** (little-endian bytes); typed form needs **both** `type` and `value`. `debugger.scatterRead {reads:[ {address,type} | {address,length} ]}`.
- xref search (find callers): a `jal target` instruction word = `(0x3<<26) | ((target>>2) & 0x03ffffff)`; scan the code region for that u32.
- Driver `tools/abl_dbg.py` class `D`: `adv(n)`, `rs32/ru32(a)`, `rmem(a,n)`, `call(method, params)`, plus `cap`/`load`. **API param is `frames`** inside `adv`.

## Isolated debugger instance — connection quick-start
The repeatable way to drive a clean instance without touching your own DuckStation:
- **Launch:** `scripts/debugger-client/launch_debugger_instance.sh start --disc "<X>.cue" --port 23460 --no-fastboot` → own config root `/tmp/duckstation-debugger`, token `debugger-1000`, BIOS read-only. Refuses to kill non-owned PIDs (so a stale crashed instance lingers — a fresh `start` still binds the port).
- **Stop:** `launch_debugger_instance.sh stop --config-dir /tmp/duckstation-debugger`.
- **Connect:** `DebuggerClient("127.0.0.1",23460,"ws").authenticate("debugger-1000")`; then `c.transport.sock.settimeout(30)` (avoids the hang-on-crash above).
- Your own game instance binds **2346**; the isolated build-test instance binds **23460** with a different token.
- ⚠️ **CONCURRENCY — never hard-code 23460 / `/tmp/duckstation-debugger*` when another agent may be running.** Two agents (or a background workflow) sharing the port collide: one launcher's `start` binds the port the other is using, and `stop --config-dir <shared>` tears down the *other* agent's instance mid-run. The symptom is a mid-session `ConnectionError: Connection closed while waiting for response` / dropped socket you did not cause. **Fix:** derive a UNIQUE port + config-dir per run, e.g. `PORT = 23460 + (os.getpid() % 1000)` and `CFG = f"/tmp/duckstation-debugger-{os.getpid()}"` (or a task-specific suffix like `-mesh`, `-regtest`). Always `stop` your *own* config-dir in a `finally`. Pick a distinct port for each concurrent harness (regression test, verify script, ad-hoc probe) so they can run side by side. If you inherit a drop mid-run, relaunch on a fresh port rather than reconnecting to the contended one.

## Top API gaps (updated 2026-07-06)
1. ~~**Static CD provenance**~~ — DONE: [[API - transferLog|transferLog.resolve]].
2. ~~**Guest function-call**~~ — DONE: [[API - execution control|debugger.callFunction]].
3. ~~**Animation-aware experiment diff**~~ — DONE: `experiment.run captureControl` → [[API - experiment runner]].
4. ~~**Reverse/retroactive watch**~~ — DONE: [[API - accessLog|accessLog.lastWriter / findFirstWrite]] (still needs a write watch armed at write time).
5. ~~**xref / function-boundary**~~ — DONE: [[API - xrefs and function bounds|debugger.xrefsTo / functionBounds]].
6. ~~**Function/range trace + PC-scoped effective-address trace**~~ — DONE: [[API - exec range and access history]].
7. ~~**Direct VRAM write/upload surface**~~ — DONE: `gpu.writeVramRect` in [[API - gpu.readVramRect]].
8. ~~**VRAM/CLUT provenance + screen-region primitive trace**~~ — DONE for live sessions: `gpu.vramWriteLog.get`, `gpu.resolveVramProvenance`, `gpu.resolveClutProvenance`, and `gpu.traceRegion` use the retained automatic VRAM write log / GP0 draw index and transferLog resolver. Includes frame/cycle, payload RAM ranges, and transferLog event IDs; not retrospective before the current session/state.
9. ~~**Conditional trace arming + linked provenance timeline**~~ — DONE as composable RPC helpers: [[API - trace.armWhen]] waits with `advanceUntil` predicates, then clears/starts requested logs; [[API - provenance.timeline]] sorts retained transfer/access/VRAM evidence for a RAM range and/or VRAM rect. Includes optional `disarm_condition`/`disarm_actions` for bounded capture windows.
10. ~~**Movie replay range coverage**~~ — DONE: `movie.coverageToFrame {frame,start,end,max_frames?,max_pcs?,filter?}` installs a temporary execTrace coverage-only range watch, turbo-replays active movie playback to the target frame, returns distinct PCs/counts, and removes the watch. This replaces fragile client chunk loops (`advanceToFrame` → `execTrace.summary` → `status`) for long movie coverage sweeps.
11. **Still missing / nice-to-have:** in-emulator transient debug overlay primitives. Current documented helper path is
   frame snapshots + `gpu.getCameraTransform` + external annotation, which is enough for Track-B research but not a
   native overlay.

## Tools / playbooks
- Python client + MCP bridge: `~/duckstation/scripts/debugger-client/` · driver `tools/abl_dbg.py`
- [[Playbook - Create a deterministic experiment]] · [[Playbook - Trace rendering ownership]] · [[Playbook - Trace collision resolution]]

## Related
[[Home]] · [[Tools Catalog]] · [[Playbooks]]
