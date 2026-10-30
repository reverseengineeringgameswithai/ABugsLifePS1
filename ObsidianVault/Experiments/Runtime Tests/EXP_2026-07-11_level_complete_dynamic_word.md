---
kind: experiment
id: EXP_2026-07-11_level_complete_dynamic_word
created: 2026-07-11
updated: 2026-07-11
status: verified
confidence: high
systems:
  - SYS_level_results_screen
---

# EXP_2026-07-11 - LEVEL COMPLETE dynamic objective word

## Question

Why did leaving LEVEL01 show Training's word, and can LEVEL COMPLETE render the originating level's ordered spelling in the same staggered style as SELECT?

## Identity and isolation

- Project: `~/Downloads/ABL`, HEAD `e6402e8717f56df37b47405f6423aad0882ed502`; operator WIP was preserved.
- DuckStation external-debugger fork: `~/duckstation`, HEAD `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, with the recorded dirty API worktree.
- Executable: `~/duckstation/build-release/bin/duckstation-qt`, SHA-256 `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.
- Isolated config: `/tmp/duckstation-debugger-abl-result-dynamic-fixed4-20260711`, WebSocket port `23816`, token `abl-result-dynamic-fixed4-20260711`.
- Final disc: `build/ABL_ALLMODS_RESULT_DYNAMIC.cue/.bin`; BIN SHA-256 `5712274c55c58feb2d8d5bc598fe6d67d5ebb930052b89b2c6054a08e5abc055`.
- Embedded verification from `mod/build.py`: `BITS/MEMORY.BIN` SHA-1 `d862a6220aeeace6405b65a482251d21212b2d98`; `LEVEL00/LEVEL2.RAW` SHA-1 `2d9f2930152babb20bcf577fcf4d4ee582ddeee4`.
- Timing: launcher defaults, CPU 100%, default CD read/seek, rewind/run-ahead off, fast boot; both inputs start from cold boot.

## Inputs and bounded shortcuts

- LEVEL01 anchor: `flik_to_level01_stall.mv.movie.json`, SHA-256 `fa2e81925fbad56af07081fbfe6980f2789a0dd72e6b63b13f9e7b5fc23ed264`, advanced to movie frame 4252 / emulator frame 4257. Scene read `0x80082504 == 1`. The known transition latch `writeU16(0x800823A0,1)` was used, then 800 frames were advanced. This proves the result branch from a cold-boot LEVEL01 anchor, but the latch write is a transition shortcut rather than a natural exit-sector replay.
- Training anchor: `ALLMODS_COLLECTING_TRAINING.movie.json`, SHA-256 `fbc0ef077f5bcbd3f384e8d0a0f55871b47101d20e8db8481394c35b1a3615b7`, advanced to movie frame 8000. The current build reaches Training (`scene == 0x11`) but the historical movie no longer performs its old collection route, so playback was stopped, progress `0x800A65A2` was set to `0xFF`, and the same transition latch was used. This is a controlled Training-branch check, not a natural collection claim.

## Findings

1. `current_scene_id` becomes zero on the result overlay for both origins. A result-time scene comparison cannot distinguish Training from LEVEL01.
2. The HUD hook now stores the origin selector at `0x800813E8`: LEVEL01 read `0`; Training read `0x11` before teardown and retained `0x11` after `current_scene_id` became zero.
3. The result gate at `0x800B80A8` selected RAW blob tile `0x36` for LEVEL01 and `0x37` for Training. Training `execTrace` at `0x800B80C4` captured `a0=0x37`, `v0=v1=0x11`, `s6=s7=8`.
4. Ordered tables at `0x800B824A` were `38 39 3a 3b` (`FLIK`) followed by `28 29 2a 2b 26 2b 26 27` (`TRAINING`). The Training state bytes at `0x800B8248..49` were `08 08`; LEVEL01 displayed denominator 4.
5. GP0 tracing showed the retail result frame uses texture pages `0/4/6/a/b/d`. The generated word descriptors use private page `0x0f`, one 24x24 cell per displayed slot. Temporarily redirected source object pointers are restored after their draw.
6. Negative controls mattered: result-time pickup cells overlapped the digit atlas, and one shared private cell made all slots sample the final upload. Per-slot private descriptors fixed both failures.

## Visual result

- LEVEL01: `/tmp/abl-dynamic-flik-private-slots.png`, SHA-256 `648b96ec0b562f380b05a41931ce1ceb46fe0b50265800e6f0ed138b178f8c50` — four staggered glyphs spell `FLIK`; counter is `0/4`; headings/digits/medals remain intact.
- Training: `/tmp/abl-dynamic-training-private-slots.png`, SHA-256 `279d594c6791dad4e9a91cb892ad308629b9ee2bff658fe4eebda6daa099e908` — eight staggered glyphs follow the GUI table and display `TRAINING`; objective counter is `8/8`.

## Static regression

`pytest -q tests/test_training_word_pickups.py` -> `11 passed`. The tests cover origin persistence instructions, blob dispatch, bounded 4/8-bit popcounts, ordered tables, private descriptor layout, temporary pointer restoration, medal-cave separation, and preservation of the solved retail row reference.

## Conclusion

Verified for the current two word definitions: LEVEL COMPLETE no longer bakes Training globally. It retains the originating word selector and renders the staged spelling order with the same independently spinning presentation model used by SELECT.

