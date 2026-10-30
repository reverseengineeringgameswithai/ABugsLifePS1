---
kind: experiment
id: EXP_2026-07-10_mod_smoke_gate
name: mod/smoke_test.py — automated regression smoke gate for modded discs
status: success
confidence: confirmed
source_state: evidence
validates: []
fixtures:
  - flik_to_level01_stall.mv.movie.json
artifacts:
  - mod/smoke_test.py
  - tools/launch_repro_playback.sh
---

# EXP_2026-07-10_mod_smoke_gate

## Question
With the dc campaign closed and the project pivoted to modding (see
[[SYS_decomp_substrate]] "Campaign CLOSED"), the regression story needs an automated
pre-flight: can a single command cold-boot a modded disc and mechanically catch the
dominant regression classes — disc wedges at load, corrupted loaders, a dead renderer,
broken player state/physics — **without** false-positiving on intentional mods
(visual/level/asset changes must pass)?

## Method
Built `mod/smoke_test.py`. It launches an ISOLATED DuckStation via
`tools/launch_repro_playback.sh` (determinism-matched CachedInterpreter config +
seeded memcard — required for 1:1 replay of the boot movie) on its **own config dir
`/tmp/dsrepro-smoke` and port 23465** so it never clashes with an interactive 23460
instance, replays `flik_to_level01_stall.mv.movie.json` under turbo, then asserts:

- **BOOT** — Flik world X (`0x800a6500`) > 50000, i.e. the movie landed in LEVEL01
  (retry loop: up to 75 × 300 frames; same proven check as
  `tools/test_terrain_pipeline.py`).
- **ALIVE** — health `0x800a7e2a` (s16) in 1..7 and lives `0x800a65a0` in 0..99
  (addresses per [[SYS_player]]).
- **RENDER** — the frame is *animating*: `gpu.captureFrameSnapshot` → advance 30
  frames → `gpu.diffCurrentFrame` must report changed pixels. Deliberately **no
  pristine-frame compare**, so intentional visual mods pass; only a wedged or black
  renderer fails. Degrades to SKIP if the snapshot RPC is unavailable.
- **WALK** — hold Up for 8×8 frames: Flik must move (>15000 XZ) and never cross the
  death plane (Y > 200000) — catches collision/physics regressions.

Artifacts per run: `<disc>_smoke.png` (frame capture, for human inspection) and
`<disc>_smoke.json` (machine-readable results). Exit 0 iff every check passes.
ALIVE/RENDER/WALK are skipped (not failed) when BOOT fails, so the report stays honest
about what was actually exercised.

## Findings (validation, 2026-07-10)
Three-way validation, all as predicted:

| Disc | Result |
| --- | --- |
| Pristine `Disney-Pixar A Bug's Life (v1.0).cue` | **PASS** — BOOT (flik_x 197091), ALIVE (5 HP / 5 lives), RENDER (479k px animating), WALK (moved 136895, no plunge) |
| `build/ABL_ALLMODS.cue` (consolidated mod disc) | **PASS** — same checks; the frame artifact shows the visibly modded world (sculpted terrain, re-textures), confirming the right disc was mounted and that visual mods do NOT trip the gate |
| Negative control (pristine copy, 32 EXE sectors corrupted at LBA 27+) | **FAIL** — BOOT FAIL (flik_x 0), ALIVE/RENDER/WALK SKIP, exit 1 |

The identical flik_x/moved values across passing discs are expected: the repro config
makes the movie replay deterministic, so the checks measure the same timeline.

## Conclusion
`mod/smoke_test.py --disc <X>.cue` (or `--build` to run `mod/build.py --mods` first)
is the standard pre-flight for **every** modded disc build. A FAIL means a real
regression in boot/load/render/physics; debugging then proceeds with the DuckStation
debugger API, and if the fault lands in un-decompiled code,
`tools/dc_m2c_seed.py --save <addr>` produces a readable C seed of that function on
demand. Gotcha: a failing BOOT burns the full retry loop (~2–4 min under turbo) —
that is normal, not a hang.
