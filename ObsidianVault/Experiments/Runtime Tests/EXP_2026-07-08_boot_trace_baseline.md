---
kind: experiment
id: EXP_2026-07-08_boot_trace_baseline
name: Boot→LEVEL01 load/execution trace baseline
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_function_census, SYS_overlays_and_runtime_loading]
fixtures: [from-boot-movie-level01]
artifacts: [analysis/traces/boot_trace.json, analysis/traces/overlay_loads.json, analysis/traces/function_hits.csv, tools/trace_boot_baseline.py]
---

# EXP_2026-07-08_boot_trace_baseline

## Question
Move overlays and the load pipeline from static inventory to runtime-proven
load/execution evidence: which files land where, who requests them, and which
census functions actually execute during boot→LEVEL01?

## Method
`tools/trace_boot_baseline.py` on the isolated DuckStation instance (port
23460, pristine disc, fork `fe0cca16b`): replay the pinned from-boot movie
(`flik_to_level01_stall.mv.movie.json`, 4,253 input frames) with bounded
non-halting instrumentation — 62 execTrace watches (11 resident anchors with
register capture + the 51-target resident→overlay entry surface from the
census), 3 accessLog write watches on the shell/scene globals, and transferLog
with per-window `transferLog.resolve` on 6 known load destinations.

## Key API findings (recorded for reuse)
- `transferLog.resolve` requires the **physical** address form (`0x00xxxxxx`);
  KSEG0 (`0x80xxxxxx`) silently resolves to nothing — DMA targets are logged
  physically.
- The 100k-event transferLog ring churns fast under XA streaming; resolving
  once per 60-frame window (not at the end) is what keeps load-time provenance
  alive. Resolutions are recorded as a HISTORY because the same RAM is reused
  (FMV stream buffer → loading-screen backdrop → level payload).
- TWO frame clocks: execTrace/accessLog event `frame` fields use the
  emulator's absolute counter; it does not reset with movie playback
  (`frame_base_absolute` in the artifact converts).

## Observations (headlines; full data in the artifacts)
- **Disc provenance resolved for all 6 watched destinations**, with address-
  reuse histories — e.g. Region B (`0x800B5788`) serves as the FMV stream
  buffer (`FMV/FMV.BIN`), then `CHARS/FLICK.ANM`, then level-load staging;
  the LEVEL01 payload phase lands `LEVEL01/LEVEL.RAW` / `LEVEL.DAT` /
  `LEVEL1A.VB` into the documented windows.
- **124 decompressor calls** (`FUNC_8001A1DC`) captured with src/dst/ra —
  every one during the LEVEL01 load requested from `ra=0x8003a4ec`, the
  LEVEL.RAW subtype dispatch (independent confirmation of the old B9
  dispatch identification).
- The overlay entry surface shows **40 of 51 union entry offsets executed**
  during boot→LEVEL01 with first-exec frames — per-variant liveness the
  static census could only over-approximate.
- Scene/state globals: `current_scene_id`/`scene_select_index` write
  sequences captured with writer PCs (feeds the state-machine timeline).
- `function_hits.csv` feeds `tools/function_census.py` as the `dynamic`
  discovery signal (census regenerated with dynamic-confirmed entries).

## Conclusion
The load pipeline is now runtime-evidenced end-to-end for boot→LEVEL01, and
the census carries live execution confirmation. Chunk-level join in
[[EXP_2026-07-08_chunk_load_evidence]].
