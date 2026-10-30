---
kind: experiment
id: Experiment_-_Training_in-world_TRAINING_pickup_word
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: medium
legacy_source: ObsidianVault/Experiments/Experiment - Training in-world TRAINING pickup word.md
aliases:
  - "Experiment - Training in-world TRAINING pickup word"
---

# Experiment — Training in-world `TRAINING` pickup word

> Migrated from `ObsidianVault/Experiments/Experiment - Training in-world TRAINING pickup word.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — Training in-world `TRAINING` pickup word

Goal: replace the Training in-world FLIK pickup sequence with `TRAINING`, including new
T/R/A/N/G glyphs that match the solved gold F/L/I/K pickup letters.

## Scope
- User-facing target: **Training / LEVEL00**, scene id `0x11`.
- Retail disc files touched for the in-world pickup objects: `LEVEL07/LEVEL1.DAT`,
  `LEVEL07/LEVEL.RAW`, and `LEVEL07/LEVEL1.RAW`, plus resident `SCUS_942.88` hooks
  and the `BITS/MEMORY.BIN` result-screen row-2 renderer.
- This is not the Anthill/LEVEL01 SELECT-panel word strip and does not patch the LEVEL01 HUD word.

## Implementation
- Tool: `tools/training_word_pickups.py`, registered as manifest asset mod `training_word_pickups`.
- Art: `tools/generate_training_pickup_letters.py` generates
  `mod/glyphs/pickup_letters/training/{T,R,A,N,G,I}.png` plus
  `TRAINING_atlas_preview.png`. `I` is copied from the solved native pickup tile; T/R/A/N/G are
  hand-built gold/extruded stroke glyphs, then quantized to the native gold CLUT. The stager also
  synthesizes 8-frame 24x24 spin strips for `T/R/A/I/N/G` in the Training pickup page.
- Texture source chunks: `LEVEL07/LEVEL.RAW` chunk 11 and `LEVEL07/LEVEL1.RAW` chunk 12. A prior
  build patched chunks 12/13, which produced correct-looking offline strip previews but did not
  affect the live pickup page uploaded to VRAM `x=640,y=0`.
- Atlas UVs:

| Letter | UV |
|---|---:|
| T | `192,112` |
| R | `216,112` |
| A | `192,136` |
| I | `192,88` |
| N | `216,136` |
| G | `192,160` |

- Type-0x3f placement:

| Entry | Letter | Kind | XYZ |
|---:|---|---:|---|
| 50 | T | `0x10` | `-2733,-50,5061` |
| 51 | R | `0x11` | `-1833,-50,5061` |
| 52 | A | `0x12` | `-933,-50,5061` |
| 53 | I | `0x13` | `-33,-50,5061` |
| 62 | N | `0x10` | `867,-50,5061` |
| 63 | I | `0x11` | `1767,-50,5061` |
| 64 | N | `0x12` | `2667,-50,5061` |
| 65 | G | `0x13` | `3567,-50,5061` |

Entries 54-61 remain the stock Training triggers/seeds.

## Code hooks
- Collection cave `0x800811C0`: scene-gated to Training; entries 50-53 set bits 0..3, entries
  62-65 set bits 4..7. Non-Training handlers keep their native bit from the hook delay slot.
- Compare cave `0x800812B8`: returns completion mask `0xff` for Training, `0x0f` elsewhere,
  and preserves the original incomplete-branch semantics.
- Extra-letter anim pump `0x800813F0`: scene-gated to Training; pumps appended tiles
  `0x26/0x27` through native `upload_anim_frame 0x80026DF4` and stamps their CLUTs golden.
- Projector visual gate `0x80081460`: Training-only entry-index gate for entries 62-65.
- Slot descriptor pointer data `0x8008126C`: four pointers for Training entries 62-65.
- SELECT panel gate `0x8008157C`: Training-only first-letter gate reached from hook
  `0x80052D98`. It jumps through `anim_table[0x34]` to RAW-resident draw code for the full
  centered 8-slot row; outside Training it replays the displaced native `lui/lbu` and returns
  to `0x80052DA0`, preserving the normal 4-letter panel positions.
- LEVEL COMPLETE row patch in `BITS/MEMORY.BIN`: `0x800B80A8..0x800B8258` is replaced
  with an 8-slot loop using the same tile ids as the in-level/SELECT word. The row
  computes popcount inline, not through a table at `0x800BE444` (that address is
  Flik's Journey vine/leaf data and must not be overwritten). Slot tile table
  `0x800B8250` holds `10 11 12 13 26 13 26 27`; medal word-length paths at
  `0x800B8380`/`0x800B8388` jump to helpers at `0x800B81FC`/`0x800B8214`.
- Result-screen spin-strip staging: the result overlay clears the Training level's
  in-level anim records, so the stager appends the TRAINING type-`0x22` strip records
  to `LEVEL00/LEVEL2.RAW`. The row calls native `upload_anim_frame 0x80026DF4` before
  choosing the lit or dim draw path for each slot, and stamps descriptors `0x26/0x27`
  to golden CLUT `0x3677` so the extra N/G letters match the native gold letters.

Rejected cave locations:
- `LEVEL07/LEVEL1.BIN` `0x800B4A30`: overlaps Training tutorial state including timer
  `0x800B4A50`; caused the blank-screen failure after pressing X on Training load.
- Resident `0x8007FBC8`: looks usable in the boot EXE image, but is overwritten during Training
  scene load. The visual hook jumped into data (`0x00000100`, `0x02000400`, ...), producing the
  null-trap crash at `PC=0x000000a0`.
- Resident `0x8007F130..0x8007F16F`: the helper/table version placed here clobbered live retail
  state at `0x8007F16C`. Training later read that word through code around `0x800616C0`, causing
  `COP0_EPC=0x800616E0` / invalid word read at `0xA421988C`.
- Resident `0x800811BC`: this is blackberry `CAVE_THROW`'s return delay slot (`0x800811B8`
  jumps back to `0x80047178`). The old collection cave began there and berry throws executed its
  first instruction in throw-register context, causing the null-trap crash. Keep `0x800811BC` as
  `nop`; the compact collection cave starts at `0x800811C0` and ends at `0x80081210`.

Bug fix note:
- After compacting the helper to nine instructions, the descriptor and UV table live at helper
  `+0x24` and `+0x30`. Keeping the old `+0x2c` / `+0x38` offsets made the projector read the wrong
  descriptor/table bytes and rendered the pickup faces as horizontal colored bands.
- The next static-UV build still looked wrong: live VRAM evidence showed native F/L/I/K slots get
  repeated 6x24 `LoadImage` uploads for the spin, while the new custom UVs only sampled static
  flower/background texels. Fix: bake 8-frame strips into `LEVEL07/LEVEL.RAW` chunk 11 and
  `LEVEL07/LEVEL1.RAW` chunk 12, then have the helper choose the current frame from `0x8007FCCC`.
- The animated helper needs explicit R3000 load-delay nops after `lw` and `lbu`; without them the
  descriptor reused stale `t2/t3` and selected bogus V rows.
- `visual_FLIK_garbage.sav` is a stale-VRAM reproduction anchor, not a fixed-build visual proof:
  save states restore their captured VRAM page. Use a cold boot/movie replay to verify disc-streamed
  texture changes.

## Verification
- Dry stager output produced patched `SCUS_942.88`, `LEVEL07/LEVEL1.DAT`, `LEVEL07/LEVEL.RAW`,
  and `LEVEL07/LEVEL1.RAW`.
- Static/live checks confirmed the scene-gated compare, collection, and visual descriptor caves
  survive Training scene load at their final addresses.
- Patched DAT lists 66 type-0x3f entries with the intended word entries and unchanged entries
  54-61. Live scene `0x11` readback showed entries 50-53 and 62-65 present with the intended
  X/Z/kind values.
- Full consolidated build command completed:
  `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`.
- Builder embedded-file verification passed for `SCUS_942.88`, `LEVEL07/LEVEL1.DAT`,
  `LEVEL07/LEVEL.RAW`, `LEVEL07/LEVEL1.RAW`, and the other selected manifest assets.
- Output disc after the 2026-07-06 glyph-art refresh and blackberry projectile colour-tail fix:
  `build/ABL_ALLMODS.cue` / `build/ABL_ALLMODS.bin`, bin SHA-256
  `f64f26222ad7011198a31a74cae66c330b3b9e8448d80d95dbbe24020a106a5e`.
- Isolated DuckStation verification on 2026-07-06 used `collecting_FLIK_LEVELTRAINING.movie.json`
  from cold boot against `build/ABL_ALLMODS.cue`. The prior bad build halted at `PC=0x000000a0`
  by frame 4001. The fixed build reached scene `0x11` and remained in normal gameplay at
  `PC=0x8004fea4` through frames 5005, 7001, and 9001. Captures:
  `/tmp/training_word_fix/frame_5005.png`, `/tmp/training_word_fix/frame_7000.png`,
  `/tmp/training_word_fix/frame_9000.png`.
- Follow-up crash/glyph probe on 2026-07-06 found two bugs in the prior build: the `0x8007F130`
  helper-table collision described above, and the stale helper descriptor/table offsets that caused
  banded glyphs. The rebuilt helper map at that point was collection `0x800811C0`, visual gate
  `0x80081430`, compare `0x80081488`, helper `0x80081580`; later boot/berry fixes moved the
  current hooks, see the Code hooks section above.
- Follow-up static-glyph probe found the remaining visual issue: T/R/A/N/G were pointed at static
  UV cells, but the native letter slots animate by repeated small VRAM uploads. The then-current
  helper map was collection `0x800811C0`, animated helper `0x800813AC`, visual gate `0x80081430`,
  compare `0x80081488`, helper data `0x80081580`; later boot/berry fixes moved the current hooks.
  Cold-boot movie reached Training frame 9009 at
  `PC=0x8004FEA4`; live descriptor readback at `0x80081588` held `u=0x30,v=0xE0`, proving the
  helper selected the baked G strip row rather than the old flower/background UV.
- Follow-up `visual_FLIK_garbage.sav` probe found the strip rows were first written one chunk late.
  Cold-boot VRAM upload at `x=640,y=0,width=64,height=256` matched the common pickup page source
  at `LEVEL07/LEVEL.RAW` chunk 11 / `LEVEL07/LEVEL1.RAW` chunk 12, not chunks 12/13. After moving
  `RAW_TARGETS`, cold-boot frame 4001 showed the live decoded page contains the T/R/A/I/N/G strips;
  rows `0x80..0xe0` matched the embedded page exactly, and row `0x68` differed only where native
  runtime uploads touch the same page.
- Follow-up berry-throw crash probe found `COP0_EPC=0x800811B8` with `0x800811BC` executing the
  collection cave as the return-jump delay slot from blackberry `CAVE_THROW`. The 2026-07-06 fix
  leaves `0x800811BC` as `nop`, starts collection at `0x800811C0`, and compacts the collection logic
  to 0x50 bytes by using native `a0` for entries 50-53 and `a0 << 4` for entries 62-65. Isolated
  `blackberry_throw_test.movie.json` hit `CAVE_THROW` at frame 4688 and stepped back to
  `0x80047190`; resuming returned to normal gameplay PC `0x8004FEA4`.
- 2026-07-06 final glyph refresh: rebuilt from `tools/generate_training_pickup_letters.py`, then
  cold-booted the rebuilt disc in isolated DuckStation (`/tmp/duckstation-debugger-training-word-berry-677289`,
  port `23991`) with `collecting_FLIK_LEVELTRAINING.movie.json`. Movie playback reached scene `0x11`
  at frame 9304 on `build/ABL_ALLMODS.cue`; the game stayed valid in Training. Direct VRAM decode of
  the loaded pickup page proved the final strips are resident:
  `gpu.decodeTexture` rows `(640,104)`, `(640,128)`, `(640,152)`, `(640,176)`, `(640,200)`,
  `(640,224)`, each `192x24`, `bpp=4`, CLUT `(880,217)`, produced
  `/tmp/training_strip_{T,R,A,I,N,G}.png`. Contact sheet
  `/tmp/training_vram_strips_contact.jpg` shows all T/R/A/I/N/G flipbook rows. The cold-boot camera
  path did not reproduce the operator save state's exact on-screen word framing without loading that
  save state, but the disc-streamed VRAM atlas/strip data was verified from a cold boot.
- Visual framing gotcha: after teleporting Flik to the word, also set facing/heading mirrors
  `0x800A6520`, `0x800A6528`, and `0x800A6578`. The cold-boot movie left Flik turned away from the
  wall, so the camera settled on the wrong side. Rotating by 180 degrees from the current `0x0770`
  to `0x0F70` made Flik face the wall and brought the letters back into view. Verified anchor:
  player/render/anchor `(x=0,y=5314,z=85672)`, heading `0x0F70`, advance 180 frames; capture
  `/tmp/isolated_training_final_facing_wall.png` at frame 12321 showed Flik facing the wall with
  the Training letters visible.
- 2026-07-06 live-window correction: the operator's normal DuckStation on port `2346` was still
  running old RAM code (`0x80047254` contained the native throw-sound tail, not the rebuilt
  `j 0x80081158` hook), but it was positioned near the Training word with headings
  `0x005c/0x005c/0x005c`. Writing the same anchor `(x=0,y=5314,z=85672)`, all three heading
  mirrors `0x0F70`, and zeroing movement words `0x800A652C..0x800A6540`, then advancing 180
  frames, made Flik face the wall in the live window. Capture:
  `/tmp/live_training_facing_wall.png`.
- 2026-07-06 final rebuilt-disc verification: isolated DuckStation
  `/tmp/duckstation-debugger-training-word-final`, port `23992`, token `training-word-final`,
  booted `build/ABL_ALLMODS.cue` with `ABL_ALLMODS.bin` SHA-256
  `f64f26222ad7011198a31a74cae66c330b3b9e8448d80d95dbbe24020a106a5e`. The current hook readback
  at `0x80047254` was `j 0x80081158`, proving the rebuilt resident code was loaded. Movie
  `collecting_FLIK_LEVELTRAINING.movie.json` (SHA-256
  `ad2bd05c18521ad885fe82c3bf448270390bbca2b426c8ce7f0565a14ac16df9`) reached Training at
  frame 9299. Re-applying the wall-facing anchor and advancing 180 frames produced
  `/tmp/isolated_training_facing_wall_final.png`, with Flik facing the wall and the generated
  Training letters visible above it.
- 2026-07-07 SELECT-centering follow-up: `tools/training_word_pickups.py` moved the SELECT
  panel from tail-only extension (`slots 4-7` after native slots 0-3) to a Training-only
  full-row replacement at first-letter hook `0x80052D98`. The 8-letter row uses
  `x=0x48+i*0x18`; non-Training still uses retail `x=0x70+i*0x18`. Rebuilt
  `build/ABL_ALLMODS.bin` SHA-256
  `88e6da6bb1c05b9167155409c878992a2ac48f5662e64451c9c25d68119cfa4b`.
  Isolated DuckStation verification used
  `allmods_training_letters_mismatch_movie.movie.json` (SHA-256
  `b195bad0b662ac88b42fc57aa7911567d095959cf63b44f4494e909896cd3cd1`) to reach Training
  scene `0x11`, held SELECT for 90 frames, and captured
  `/tmp/training_select_left2_after.png` (SHA-256
  `ddeba6ad99dc3efd9d14e76b29d3d971f829ad93d633e3c338c73a81d4961b8`), with `TRAINING`
  placed between the Flik head and the top-right leaf after the second follow-up left nudge.
  A LEVEL01 control capture `/tmp/level01_select_4slot_left2build_check.png` (SHA-256
  `40458f123950b4e2cbcd59db5aab3c418ce4552d6f91571f5684ff1ce625fad6`) preserved the native 4-slot placement.
- 2026-07-07 LEVEL COMPLETE follow-up: `tools/training_word_pickups.py` now stages
  `BITS/MEMORY.BIN` and `LEVEL00/LEVEL2.RAW` so the result screen row pumps the same
  spinning TRAINING strip visuals and counts to `8/8`.
  Rebuilt `build/ABL_ALLMODS.bin` SHA-256
  `fe11deabc6b84a94c6a00d28081a34f6669c48d4e473dc46e7cf0a0b132bdc2a`; staged
  `build/training_word_BITS_MEMORY.BIN` SHA-256
  `f8d447f30877987edbf5e0d58f2c79a8656ba449faf87199d8ccd1c6021ec276`;
  staged `build/training_word_LEVEL00_LEVEL2.RAW` SHA-256
  `cc5937ae9de1f466e26c367a72180b96f7b379b31b496fe2d22e9e1d4ae54afe`.
  Isolated DuckStation config `/tmp/duckstation-debugger-training-dim-spin-final`,
  port `23727`, movie `ALLMODS_COLLECTING_TRAINING.movie.json` SHA-256
  `fbc0ef077f5bcbd3f384e8d0a0f55871b47101d20e8db8481394c35b1a3615b7`: fast-forward
  to frame `7218` stayed reproducible, reached scene `0x11`, and had progress byte
  `0x800A65A2=0xff`; frames `8000..8300` also stayed reproducible in the result
  window. Final result layout is `X = 8 + i*10` for letter slots and
  `X = 8 + wordLen*10 + 88` for the counter; for TRAINING, trace at row resume
  `0x800B8258` captured `s0=0xB0`, `s7=8`, and `s6` rising to `8`, while
  trace at count-cap compare `0x800B853C` captured final `s6=8,v0=8,s7=8`.
  Captures `/tmp/traindimfinal/result_8000.png` and
  `/tmp/traindimfinal/result_8300.png` show the tighter spinning TRAINING row
  clear of the capped `8/8` counter; SHA-256 values
  `ae2557573bf5dd02cfc6c474724bdae05c8b4faf95faae5f64c5b3242cecca0d` and
  `8211d6577cf54e3c651e477e85b37355eae7960c23dbbb84318e1526bb8ffb78`.
  Forced-uncollected visual check at result frame `8000` wrote `0x800A65A2=0x00`;
  captures `/tmp/traindimspin/dim_a.png`, `dim_b.png`, and `dim_c.png` show the
  dim TRAINING row changing spin phase rather than freezing.
  Front-end Start-spam capture `/tmp/traindimfront/front_359.png` SHA-256
  `d8ab3579f8cff4588c8401844c4919716d17ef69035a734775192ba0d5a78f4e` shows
  Flik's Journey with the vine/level path visible.

## Related
[[Experiment - Training TRAINING follow-up bugs]] · [[HUD letter glyphs and word swap]] · [[Experiment - FLIK5 five-letter token gate]] ·
[[MEM - Type-0x3f placement record]] · `src_re/pickup_projector_800253e8.c` ·
`src_re/pickup_handlers_80054288_80054554.c`
