---
kind: experiment
id: EXP_2026-07-08_overlay_track
name: Overlay decompilation track (v2 phase 4)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_overlays_and_runtime_loading, SYS_function_census]
fixtures: []
artifacts: [config/overlays.yml, tools/build_overlay.py, analysis/overlay_decomp_progress.json, tests/test_overlays.py]
---

# EXP_2026-07-08_overlay_track

## Question
Can the byte-splat substrate be extended to the game's OVERLAYS (192 fns / 20
`OVL/*.BIN` images) as a SEPARATE track — its own manifest, metric, ranker, and
build/validate path — without polluting the resident 8.05% metric, and is it real
(one proof match)?

## Method
Overlays are standalone code images CdRead-loaded at fixed VAs (Region A
`0x800B39A0` per-level LEVEL*.BIN, Region B `0x800B5788` MEMORY.BIN), sharing the
resident `$gp` and calling resident engine fns. VA = base + file_offset; LEVEL*.BIN
carry a 4-byte ID word at +0 (code at +4). Build reuses the resident substrate v2
pipeline (`--section-start`, `_gp`) at the overlay VA, splicing into a copy of the
blob and requiring the rebuilt blob to be SHA-1-identical.

## Observations
- **Separate infrastructure stood up** (all additive; resident substrate untouched):
  - `config/overlays.yml` — region bases + gp + per-overlay `{blob, sha1, base, attempted}`.
  - `tools/build_overlay.py` — build+validate (`[STEM]`), metric (`--progress`),
    and a **separate ranker** (`--candidates` — small complete cop2-free unmatched leaves).
  - `analysis/overlay_decomp_progress.json` — metric over the 184 overlay CODE fns
    (kept out of `analysis/decomp_progress.json`).
  - `tests/test_overlays.py` — manifest/census consistency (CI-safe) + build-validate
    (local_media).
- **Proof match**: `LEVEL02_LEVEL @ 0x800B3B70` (`level02_set_state_60`:
  `*(int*)0x800B4950 = 60`) compiles byte-exact to `OVL/LEVEL02_LEVEL.BIN`; rebuilt
  blob SHA-1 `6eecee68…` PASS. `[[FUNC_800B3B70]]`.
- **Census caveat surfaced**: the `4B level_overlay_init` records are the `"LEVE"`/
  `"leve"` ID string (data), not code — noted in `docs/EXECUTABLE_AND_OVERLAYS.md`.

## Result
Overlay track is real and separate: matched 1 / 184 overlay code fns (0.54%), resident
metric unchanged at 86 / 1068 (8.05%). Future overlay campaigns documented in
`docs/EXECUTABLE_AND_OVERLAYS.md`. `OVL/*.BIN` are gitignored owner media, so the
track is local_media-gated (like the resident EXE). See [[SYS_decomp_substrate]],
[[SYS_overlays_and_runtime_loading]].
