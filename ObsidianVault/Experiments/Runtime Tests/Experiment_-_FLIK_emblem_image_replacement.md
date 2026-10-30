---
kind: experiment
id: Experiment_-_FLIK_emblem_image_replacement
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - FLIK emblem image replacement.md
aliases:
  - "Experiment - FLIK emblem image replacement"
---

# Experiment — FLIK emblem image replacement

> Migrated from `ObsidianVault/Experiments/Experiment - FLIK emblem image replacement.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — FLIK emblem image replacement

## Result
Implemented an offline mod path for replacing the **FLIK completion emblem** image with a user-supplied picture.

The patch targets are:
- Training (`LEVEL00`): `LEVEL00/LEVEL.RAW` logical texture chunk **3**, rect **x=64, y=96, w=64, h=80**
- `LEVEL01/LEVEL.RAW`: logical texture chunk **13**
- `LEVEL01/LEVEL1.RAW`: logical texture chunk **12**
- in the LEVEL01 files: 4bpp page, 256x256, runtime FLIK emblem tile rect **x=64, y=0, w=64, h=64**
- Shared menu/Journey copies (manual RE experiment only; not emitted by the GUI):
  - `LEVEL00/LEVEL.RAW` chunk **3** and `LEVEL00/LEVEL2.RAW` chunk **1**
  - LEVEL COMPLETE large coin rect **x=64, y=128, w=64, h=64**, CLUT slot **9**
  - Flik's Journey tiny coin spin frames rects **x=0, y=192, w=24, h=24**,
    **x=64, y=192, w=24, h=24**, and **x=112, y=192, w=24, h=24**, CLUT slot **13**

2026-07-06 `collecting_flik.sav` retest confirmed this is best treated as a **level-local glyph/tile replacement**:
the visible emblem is a `GP0(2c)` textured quad sampling one 4bpp atlas tile, not a global FLIK model.

Live DuckStation `gpu.pickObject` on the user's still frame resolved the visible top emblem primitive:
- command: `GP0(2c)` textured quad
- texture page: `raw=0x066b`, VRAM page **x=704,y=0**
- CLUT: `raw=0x35f1`, **x=784,y=215**
- UVs: **64..127 / 0..63**

Important correction: the visible emblem looks silver on screen, but the sampled texture tile is the gold-looking FLIK tile in the static texture-page decode; the runtime CLUT recolors it silver. The earlier static-silver target (`LEVEL.RAW` chunk 12 / `LEVEL1.RAW` chunk 11, rect `128,192,64,64`) is not the primary top emblem face and left the old `FLIK` text visible.

Patching only `LEVEL.RAW` is also insufficient. The GUI saves both manifest entries from one image picker so `LEVEL.RAW` and `LEVEL1.RAW` are staged together.

Training correction: the Mod Studio level key `training` is **LEVEL00**, not LEVEL01. A failed retest still showed the old emblem because the first stager/registry path was hardcoded to `LEVEL01`. Training's FLIK badge is visible in static decode of `LEVEL00/LEVEL.RAW` chunk 3 on the same page as the `load/save`, `movie clips`, and `training` menu text. The middle FLIK badge spans the 64x80 area at `x=64,y=96`; the lower 16 pixels carry the `FLIK` label, so a 64x64-only patch leaves the label visible.

2026-07-06 Training correction: Training's FLIK badge target is enabled again.
The recompressor still expands `LEVEL00/LEVEL.RAW` chunk 3, but the Training entry crash
was isolated to the stale `training_tutorial` EXE cave path, not the emblem RAW edit.
The active manifest now patches Training through a single `flik_emblem` entry targeting
`LEVEL00/LEVEL.RAW`.

## Implementation
Tool: `tools/flik_emblem_edit.py`

Behavior:
- reads a PNG/JPG/etc.
- resizes it to the mapped target rect (`64x80` for Training, `64x64` for Anthill)
- quantizes opaque pixels to 4bpp
- for Anthill/LEVEL01, writes a replacement 15-colour palette into the same
  on-disc CLUT slot used by the runtime draw (`slot 1` -> live CLUT `784,215`)
- for Training/LEVEL00, uses the currently mapped page palette; the badge is
  preserved behind transparent pixels, and writes a replacement CLUT for the visible
  spawned coin tile at `64,128,64,64`
- maps transparent pixels to index 0, stored on disc as the native green-key
  palette entry
- recompresses only the touched LEVEL.RAW chunk
- emits size-changed `LEVEL00/LEVEL.RAW` for Training or size-changed
  `LEVEL01/LEVEL.RAW` and `LEVEL01/LEVEL1.RAW` files for Anthill

Manifest integration:
- `mod/mods/registry.py` registers asset tools `flik_emblem`, `flik_emblem_level1`,
  and the manual/experimental `flik_menu_result_emblems_level2` shared-menu stager
- `mod/build.py --mods` now detects size-changing staged files and switches to `REBUILD/abl_autolayout.xml`
- `tools/mod_studio_gui.py` exposes a **FLIK emblem image** picker in the Word Emblem tab.
  Training uploads emit `LEVEL00/LEVEL.RAW` for the menu/badge source,
  `LEVEL07/LEVEL.RAW` plus `LEVEL07/LEVEL1.RAW` for the actual in-game spawned coin, and
  `LEVEL00/LEVEL2.RAW` for the Training LEVEL COMPLETE coin. Anthill uploads emit the
  level-local `LEVEL01/LEVEL.RAW` and `LEVEL01/LEVEL1.RAW` entries. Unsupported levels
  remain disabled until their source tiles are mapped.

Example manifest entry:
```yaml
- tool: flik_emblem
  level: training
  target: LEVEL00/LEVEL.RAW
  params:
    image: /path/to/training_emblem.png
    target: LEVEL00/LEVEL.RAW
- tool: flik_emblem_training_result
  level: training
  target: LEVEL00/LEVEL2.RAW
  params:
    image: /path/to/training_emblem.png
    target: LEVEL00/LEVEL2.RAW
    patch_palette: false
    preserve_transparent: true
- tool: flik_emblem_training_ingame
  level: training
  target: LEVEL07/LEVEL.RAW
  params:
    image: /path/to/training_emblem.png
    target: LEVEL07/LEVEL.RAW
- tool: flik_emblem_training_ingame
  level: training
  target: LEVEL07/LEVEL1.RAW
  params:
    image: /path/to/training_emblem.png
    target: LEVEL07/LEVEL1.RAW
- tool: flik_emblem
  level: anthill
  params:
    image: /path/to/custom_emblem.png
- tool: flik_emblem_level1
  level: anthill
  params:
    image: /path/to/custom_emblem.png
```

## Verification
Offline:
- `python3 -m py_compile tools/flik_emblem_edit.py tools/mod_studio_gui.py mod/build.py`
- `python3 tools/flik_emblem_edit.py /tmp/flik_emblem_test.png --stage-out /tmp/LEVEL01_LEVEL_RAW_flik_emblem_test.RAW`
  - round-tripped the recompressed chunk
  - `LEVEL01/LEVEL.RAW` size changed `747748 -> 767587`
- single-file dry run: `python3 mod/build.py --mods /tmp/flik_emblem_mods.yaml --no-code --out build/ABL_FLIK_EMBLEM_DRY --force`
  - switched to auto-layout
  - verified patched `LEVEL01/LEVEL.RAW` embedded at recomputed LBA 3069
- two-file fix build: `python3 mod/build.py --mods /tmp/flik_emblem_both.yaml --no-code --out build/ABL_FLIK_EMBLEM_BOTH_TEST --force`
  - verified patched `LEVEL01/LEVEL.RAW` embedded at LBA 3069
  - verified patched `LEVEL01/LEVEL1.RAW` embedded at LBA 3499
- corrected-source ALLMODS retest: `python3 mod/build.py --mods build/flik_emblem_retest.yaml --out build/ABL_ALLMODS --force`
  - full `mod/mods.yaml` was blocked by missing `custom_signs/og_signs/og_sign_13.png` through `15.png`, so the retest manifest kept the code mods plus the two emblem entries
  - embedded `LEVEL01/LEVEL.RAW` at LBA 3069 matches `flik_emblem_edit.stage_patch()` for chunk 13 rect `64,0,64,64`
  - embedded `LEVEL01/LEVEL1.RAW` at LBA 3499 matches `stage_patch_level1()` for chunk 12 rect `64,0,64,64`
- Training retest after LEVEL00 correction: same focused build path, now routing `level: training` to `LEVEL00/LEVEL.RAW`
  - `flik_emblem_level1` is skipped for Training because Training uses `LEVEL00/LEVEL.RAW` for this emblem
  - rendered preview of chunk 3 shows the `64,96,64,80` FLIK badge region replaced by `~/Downloads/ABL/custom_signs/blackberry.png`
  - embedded `LEVEL00/LEVEL.RAW` at LBA 2339 matches `flik_emblem_edit.stage_patch(..., _target='LEVEL00/LEVEL.RAW')` exactly (`427083` bytes)

Live DuckStation:
- Existing user instance on port `2346`, mounted `build/ABL_ALLMODS.cue`.
- `gpu.pickObject --x 260 --y 80 --all-contributors` on the still frame identified the final visible emblem contributor as the GP0(2c) quad above.
- This overturned the static-silver assumption: the asset source is the gold-looking page, rendered silver by CLUT `784,215`.

### 2026-07-06 LEVEL01 glyph retest
Goal: replace only the Anthill/LEVEL01 completion emblem without affecting Training or other level FLIK emblems.

Runtime evidence:
- Fixture: `~/Downloads/ABL/collecting_flik.sav`, sha256 `ef7eb5136af0f04dd00fc1cbd57c5a8e3b61ad88a1f1c7e3a66a7e716992887a`
- Mounted pristine disc: `~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue`, serial `SCUS-94288`
- DuckStation fork: `~/duckstation` rev `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, binary sha256 `65e04297fa58f00d04b8d67672a6a1ace08794d028cb2f86b5ac889fde29a5bf`
- Isolated debugger: config `/tmp/duckstation-debugger-flik-emblem-23620`, port `23620`, token `flik-emblem-23620`
- Repro: load state with `pause_after_load:true`, hold `UP`, advance `60` frames, clear input, stay paused. Frame capture `/tmp/flik_paused_collect60.png` shows the silver FLIK emblem.
- `gpu.pickObject {x:235,y:150,all_contributors:true}` on the paused frame resolves the final visible contributor to `GP0(2c)`, tpage `x=704,y=0 raw=0x066b`, CLUT `x=784,y=215 raw=0x35f1`, UV `64..127 / 0..63`, packet RAM `0x001ceea4`.
- Picking the emblem center (`x=260,y=150`) can report Flik-body overdraw as the top contributor; use a clean pixel on the left/right face to identify the emblem tile itself.

Workflow fix:
- Added `flik_emblem_edit.LEVEL_TARGETS` as the level-to-source-file map:
  - `training` -> `LEVEL00/LEVEL.RAW`
  - `anthill` -> `LEVEL01/LEVEL.RAW` plus `LEVEL01/LEVEL1.RAW`
- `mod/build.py` now uses that map. Unsupported levels no longer silently fall back to LEVEL01; they are skipped with a clear message.
- `tools/mod_studio_gui.py` now disables the FLIK emblem picker on levels without a mapped source tile, preventing accidental Anthill edits when another level is selected.
- Active manifest `mod/mods.yaml` now includes Anthill entries for generated glyph `~/Downloads/ABL/custom_signs/flik_emblem_level01_random_glyph.png`.

Build verification:
- Focused no-code build:
  `python3 mod/build.py --mods build/flik_emblem_level01_random_glyph.yaml --no-code --out build/ABL_FLIK_EMBLEM_LEVEL01_GLYPH --force`
  - `LEVEL01/LEVEL.RAW` embedded at LBA `3069`, `767027` bytes, sha1 `fb0bfc51d459b9cf3f8a484034d64053c72388eb`
  - `LEVEL01/LEVEL1.RAW` embedded at LBA `3499`, `560479` bytes, sha1 `d4533029eb90aab6d040d6f05c7301ad4317aa61`
- Superseded active all-mods build from before the Training-load fix:
  `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`
  - `LEVEL00/LEVEL.RAW` embedded at LBA `2339`, sha1 `9d0dc4857f6a735eb4e7168b3eab881ffe3e7dd4`
  - `LEVEL01/LEVEL.RAW` embedded at LBA `3082`, sha1 `fb0bfc51d459b9cf3f8a484034d64053c72388eb`
  - `LEVEL01/LEVEL1.RAW` embedded at LBA `3512`, sha1 `d4533029eb90aab6d040d6f05c7301ad4317aa61`

### 2026-07-06 colour/alpha fix
User retest showed the replacement shape but still rendered as black/white/silver with an opaque dark square. Root cause:
the first `flik_emblem_edit.py` path only changed the 4bpp texel indices. It quantized through the wrong palette
(`slot 0`) and did not write the runtime CLUT used by the visible GP0 quad.

Evidence:
- User save: `~/.local/share/duckstation/savestates/SCUS-94288_1.sav`
  - valid for `~/Downloads/ABL/build/ABL_ALLMODS.cue`
  - loaded paused on isolated debugger port `23710`
- Live `gpu.readVramRect {x:784,y:215,width:16,height:1}` before the fix read the native silver palette:
  index 0 black, then white/grey-blue ramp (`ffff`, `fbde`, `f37b`, ...).
- Static decompression maps that live palette to `LEVEL01/LEVEL.RAW` chunk 13 palette `slot 1`
  (`LEVEL1.RAW` chunk 12, also `slot 1`). Entries 1..15 match the live CLUT after RGB888->BGR555;
  entry 0 is the transparent key.
- `gpu.writeVramRect` transiently writing the generated palette to live VRAM at `784,215`, followed by
  `gpu.decodeTexture {x:704,y:0,width:256,height:256,bpp:4,clut_x:784,clut_y:215}`, produced a coloured
  decoded texture at `/tmp/flik_allmods_tex_after_custom_clut.png`. This proves the hardware path is not limited
  to grayscale; the disc asset must patch the palette too.

Fix:
- `tools/flik_emblem_edit.py` now records `clut_slot: 1` for both Anthill targets.
- The stager derives a replacement 15-colour palette from the source image and writes it into that slot.
- Alpha below threshold maps to texel index 0 by default for CLUT-patched targets, avoiding the previous opaque
  dark background block.
- New `ABL_ALLMODS` rebuild:
  - `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`
  - `LEVEL01/LEVEL.RAW` embedded at LBA `3082`, sha1 `b967f10d9daa770161bbaa19c097cb2bfdd2bcb9`
  - `LEVEL01/LEVEL1.RAW` embedded at LBA `3512`, sha1 `619862904f040910269de1349020619a3110aba1`
  - `build/ABL_ALLMODS.bin` sha256 `5706e41e30cf3b46869044ea1037af2ef400f0d7231b54d3c61857e20b021c23`

Follow-up alpha correction from user retest:
- Writing palette entry 0 as RGB black still produced a visible black square. Native texture pages store index 0 as
  chroma green (`0,255,0`) on disc; the loader converts that key to transparent VRAM colour.
- `tools/flik_emblem_edit.py` now keeps slot-1 entry 0 as green-key and quantizes opaque pixels only to indices 1..15.
- Rebuilt `ABL_ALLMODS` again:
  - `LEVEL01/LEVEL.RAW` embedded at LBA `3082`, sha1 `9180170d868928d009357b8409430760a6a729cf`
  - `LEVEL01/LEVEL1.RAW` embedded at LBA `3512`, sha1 `3f25853b3e5d0e8d3edca55f68816c9f26af55cd`
  - `build/ABL_ALLMODS.bin` sha256 `d9270d93fa5c1f55fe51ed288b14e2fb90a4b855fcb125fe28b8abd7a9b10d8d`

Important validation caveat: `collecting_flik.sav` is already inside LEVEL01 with the old texture state resident. It is excellent for screen-to-glyph RE and final-letter timing, but a rebuilt-disc visual proof still needs a cold-boot/from-boot route into LEVEL01; loading this save directly does not force the game to re-read the edited LEVEL01 RAW files.

### 2026-07-06 from-boot movie, result screen, and Flik's Journey follow-up

Fixture:
- Movie: `~/Downloads/ABL/collecting_FLIK_LEVEL01.movie.json`, sha256 `04874b8f214a8a3adc12afbbbd49a7961017fb323f5f5e297ae23fab14884fd4`
- Repro command pattern: load movie, `movie.startPlayback {"load_start_state":true}`, then `movie.advanceToFrame {"frame":9000}`. The API parameter is `frame`, not `target_frame`.
- The movie was recorded from boot, but after the later ALLMODS rebuild it desyncs on the
  current image/config: clean playback at movie frame `9000` remains in LEVEL01 gameplay near
  a large wall. This is a route/build desync, independent of the failed FLIK result hook
  attempts. The user's `_1.sav` still confirms the final-letter timing: holding `UP` changed
  the progress mask from `0x0b` to `0x0f` after 60 frames in the isolated instance.

Current stable build result:
- `mod/mods.yaml` includes Anthill `flik_emblem` and `flik_emblem_level1` entries for `~/Downloads/ABL/custom_signs/flik_emblem_level01_random_glyph.png`.
- `mod/mods.yaml` no longer includes `flik_menu_result_emblems_level2`. The active
  ALLMODS cue therefore does not patch the `LEVEL00/LEVEL2.RAW` shared Journey/menu copy.
  This keeps the supported upload path level-specific for Anthill instead of changing a
  shared menu atlas tile used outside LEVEL01.
- `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force` succeeds.
- Rebuild after removing the automatic shared-menu patch:
  - build manifest asset list: `training_tutorial`, `flik_emblem`, `flik_emblem_level1`
  - `LEVEL00/LEVEL.RAW` remains at LBA `2339`, `400632` bytes
  - `LEVEL00/LEVEL2.RAW` remains at LBA `2580`, `95276` bytes; it is not staged by this build
  - `LEVEL01/LEVEL.RAW` embedded at LBA `3069`, `786866` bytes, sha1 `5a643a543facc9fd85d41677f1cf4266c6654cff`
  - `LEVEL01/LEVEL1.RAW` embedded at LBA `3509`, `580318` bytes, sha1 `7a60ec0e30731a545447837e26bf2a27ddb8ae8e`
  - Training tutorial overlay `LEVEL07/LEVEL1.BIN` embedded at LBA `12429`, `4336` bytes, sha1 `7d55b9fe5e5774eb637fbb971d8d7be751cb588e`
  - EXE embedded sha1 `20348c10ef3db1e11c2dd921ff64c355d10719ff`
  - `build/ABL_ALLMODS.bin` sha256 `3011ba454666347736765aab56dcca1e71bc2b03147ce9490d8326c57c8d726f`

Training load regression fix:
- Repro: boot active ALLMODS, use the from-boot movie to reach Flik's Journey frame `3300`,
  press `X` to select Training, wait for the Training loading screen's `X start` prompt,
  then press `X` again. Before the fix the active build hung/crashed on this entry path.
- Control build with the same code mods and Anthill emblem but without `training_tutorial`
  entered Training gameplay, isolating the regression to `training_tutorial`.
- Root cause: `tools/patch_training_overlay.py` still emitted the older EXE cave jump even
  though the RE notes documented the safer verified design: leave the stock step-0 audio
  start alone and rewrite only the `LEVEL07/LEVEL1.BIN` advance half in-place.
- Fix: `tools/patch_training_overlay.py` now writes a 40-byte in-place patch at
  `0x800B4000` / file offset `0x660`; `tools/training_tutorial_stager.py` no longer stages
  `SCUS_942.88` for Training unless the bytes actually change.
- Verification: active `build/ABL_ALLMODS.cue` enters Training gameplay after the loading
  prompt. Captures: `/tmp/training_smoke_allmods_fixed/after_start_2400.png` and
  `/tmp/training_smoke_allmods_fixed/after_start_3600.png`.

Training emblem re-enable and GUI wiring:
- Active manifest now includes a Training-specific emblem entry:
  `~/Downloads/ABL/custom_signs/flik_emblem_training_test3_glyph.png` ->
  `LEVEL00/LEVEL.RAW`, `LEVEL07/LEVEL.RAW`, and `LEVEL07/LEVEL1.RAW`. The Anthill entry remains
  `~/Downloads/ABL/custom_signs/flik_emblem_level01_random_glyph.png` ->
  `LEVEL01/LEVEL.RAW` plus `LEVEL01/LEVEL1.RAW`, so Training and LEVEL01 use different
  source images and different RAW targets.
- `tools/flik_emblem_edit.py` maps `LEVEL_TARGETS["training"]` to
  `("LEVEL00/LEVEL.RAW",)`. `tools/mod_studio_gui.py` reads that map and saves a single
  `flik_emblem` manifest entry with explicit `target: LEVEL00/LEVEL.RAW`.
- Static preview of the patched Training badge was written to
  `/tmp/training_level00_coin_patch_preview.png`; the separate result-screen copy was
  previewed at `/tmp/training_level2_result_coin_patch_preview.png`. Later palette
  work changed the Training result copy to the same palette-constrained path as the
  in-game spawned coin; see the 2026-07-06 regression note below.
- Correction from the resaved `_1.sav`: the actual Training in-game spawned coin
  is on the live collectibles texture page, not the earlier static-atlas candidate.
  The visible old silver FLIK token decodes from VRAM page `tpage x=704,y=0` with
  CLUT `x=1008,y=253`. Raw VRAM-nibble comparison against every decompressed RAW page
  maps the full visible X/FLIK strip exactly to `LEVEL07/LEVEL.RAW` chunk `12`,
  rect `0,0,128,64`, and `LEVEL07/LEVEL1.RAW` chunk `13`, rect `0,0,128,64`.
  The FLIK tile is the right half: rect `64,0,64,64`. Follow-up CLUT inspection
  showed the visible gameplay primitive uses the blue/silver runtime CLUT at
  VRAM `x=1008,y=253`, sourced from the prior companion page's slot `4`:
  `LEVEL07/LEVEL.RAW` chunk `11` and `LEVEL07/LEVEL1.RAW` chunk `12`. The previous
  `chunk 12`, rect `128,192,64,64` patch was a false match and left the old in-game
  emblem visible.
- Rebuild command: `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`
  - `LEVEL00/LEVEL.RAW` embedded at LBA `2339`, `427083` bytes, sha1 `b876005f91be3145534a2546dcdb7963b2004d8d`
  - `LEVEL00/LEVEL2.RAW` embedded at LBA `2593`, `121727` bytes, sha1 `7637a6986e7c6351da9a5eb7e1c54e5551b59e8e`
  - `LEVEL07/LEVEL1.RAW` embedded at LBA `12515`, `580327` bytes, sha1 `ebb30db3041f8aaac2dbdea8e25cce386830615a`
  - `LEVEL01/LEVEL.RAW` embedded at LBA `3095`, `786866` bytes, sha1 `5a643a543facc9fd85d41677f1cf4266c6654cff`
  - `LEVEL01/LEVEL1.RAW` embedded at LBA `3535`, `580318` bytes, sha1 `7a60ec0e30731a545447837e26bf2a27ddb8ae8e`
  - `LEVEL07/LEVEL1.BIN` embedded at LBA `12455`, `4336` bytes, sha1 `7d55b9fe5e5774eb637fbb971d8d7be751cb588e`
  - `build/ABL_ALLMODS.bin` sha256 `3124e745191f640a26e7b312ca299218c48e2bf031479c984e6980c2c605569b`
- Runtime smoke test used isolated DuckStation config
  `/tmp/duckstation-debugger-flik-training-23845`, separate runtime dir
  `/tmp/duckstation-runtime-flik-training-23845`, port `23845`, token
  `flik-training-23845`, disc `~/Downloads/ABL/build/ABL_ALLMODS.cue`.
  Movie `~/Downloads/ABL/collecting_FLIK_LEVEL01.movie.json` reached the
  Training selector at frame `3305`; pressing `X`, waiting for the Training `X start`
  screen, pressing `X` again, and advancing to frame `10821` entered gameplay without
  the reported crash. Captures:
  `/tmp/training_allmods_23845/selector_3300.png`,
  `/tmp/training_allmods_23845/start_prompt_candidate.png`,
  `/tmp/training_allmods_23845/gameplay_after_x.png`.
- Follow-up Training movie from the operator:
  `~/Downloads/ABL/collecting_FLIK_LEVELTRAINING.movie.json`, sha256
  `ad2bd05c18521ad885fe82c3bf448270390bbca2b426c8ce7f0565a14ac16df9`, verified
  the current rebuilt image still loads Training to frame `7634` via movie playback.
  The movie stayed in gameplay through frame `9298` on the current build, so it did not
  provide a fresh result-screen `gpu.pickObject`; the visible old coin in the user
  screenshots matches the already identified `LEVEL00/LEVEL2.RAW` result copy and the
  separate CLUT-backed `64,128,64,64` coin tile.
- User confirmed the LEVEL COMPLETE coin was fixed, but the in-game Training coin still
  showed the old FLIK emblem. Loading the resaved `_1.sav` against `ABL_ALLMODS` kept
  the old token visible and allowed a live VRAM page decode. The corrected
  `flik_emblem_training_ingame` stager now targets both `LEVEL07/LEVEL.RAW` chunk `12`
  and `LEVEL07/LEVEL1.RAW` chunk `13`, rect `64,0,64,64`. A later attempt to patch
  the gameplay CLUT source at `LEVEL07/LEVEL.RAW` chunk `11` /
  `LEVEL07/LEVEL1.RAW` chunk `12`, slot `4`, was reverted because that CLUT is shared
  with Flik head/HUD portrait art.
- Teleport verification for the Training collection route was run against the same
  current ALLMODS image. Isolated DuckStation config:
  `/tmp/duckstation-debugger-training-emblem-teleport2`, runtime dir:
  `/tmp/duckstation-debugger-training-emblem-teleport2/runtime`, port `23861`,
  token `debugger-training-emblem2`, binary sha256 `65e04297fa58f00d04b8d67672a6a1ace08794d028cb2f86b5ac889fde29a5bf`,
  disc `build/ABL_ALLMODS.cue` / bin sha256
  `3124e745191f640a26e7b312ca299218c48e2bf031479c984e6980c2c605569b`.
  The from-boot Training movie was used only to enter scene `0x11`; live at frame
  `4205`: `DAT_BASE=0x8011cc50`, type-`0x3f` table pointer `0x8011cc54`, entries start
  `0x8011cc58`, FLIK mask `[0x800A65A2]=0`.
- Training hides part of the letter set before the tutorial unlocks it. Live entries
  50-53 initially had F/L status `0`, I/K status `1`, with Y values displaced from
  the disk coordinates. For the deterministic test, entries 50-53 in RAM were forced
  to the `LEVEL07_LEVEL1.DAT` disk coords and `status=1`, preserving kind and trailing
  bytes:
  - F entry 50 `0x8011cf78`: `(-2733,-50,5061)`, kind `0x10`
  - L entry 51 `0x8011cf88`: `(4821,-50,2773)`, kind `0x11`
  - I entry 52 `0x8011cf98`: `(3205,-50,-4510)`, kind `0x12`
  - K entry 53 `0x8011cfa8`: `(-5366,-50,-3184)`, kind `0x13`
  Teleporting Flik to each exact runtime coordinate (`file << 5`) and advancing
  20 frames collected the native letters in order: mask `0x00 -> 0x01 -> 0x03 ->
  0x07 -> 0x0f`. All four entries ended with the native consumed sentinel
  `Y=0x80000000` and `status=0`. Captures:
  `/tmp/training_teleport_before.png`, `/tmp/training_teleport_after_50.png` through
  `/tmp/training_teleport_after_53.png`, `/tmp/training_teleport_final.png`,
  `/tmp/training_teleport_select.png`.

Result-screen RE (earlier shared-page hypothesis retained for provenance):
- `gpu.pickObject` on the LEVEL COMPLETE silver FLIK coin at native `(270,125)`:
  - final visible sprite: `GP0(65) sprite`
  - packet RAM: `0x801E2A38`
  - raw words: `65400040 006400F0 3F798040 00400040`
  - texture page: `x=640,y=256,mode=0,raw=0x061a`
  - UV origin: `(64,128)`, size `64x64`
  - CLUT: `x=912,y=253`
- User retest later confirmed the LEVEL01 level-ending screen is correct through the
  level-local `LEVEL01/LEVEL.RAW` / `LEVEL01/LEVEL1.RAW` edits. The shared-page result
  path is not part of the active build because it is not level-specific.
- The LEVEL01-local custom glyph remains resident on the result screen at VRAM `x=720,y=0`, CLUT `x=784,y=215`. A debugger-only `gpu.writeVramRect` copy from that source to result destination `x=656,y=384`, plus CLUT copy to `x=912,y=253`, decodes correctly as the custom glyph. This proves the desired visual is technically possible, but it needs a safe result-screen-only runtime hook.

Flik's Journey level-select RE:
- Earlier candidate pick at movie frame `9834`, on a tiny FLIK-like coin at native `(270,27)`:
  - final visible sprite: `GP0(65) sprite`
  - packet RAM: `0x801CD8EC`
  - raw words: `650006C4 00140100 3E7DC040 00180018`
  - texture page: `x=640,y=256,mode=0,raw=0x061a`
  - UV origin: `(64,192)`, size `24x24`
  - CLUT: `x=976,y=249`
- Follow-up with `collecting_FLIK_LEVEL01.movie.json` and `collecting_flik.sav` did not
  anchor the exact post-completion Flik's Journey selector token frame on the current build:
  the movie reaches Anthill gameplay and the save-state route stays in gameplay. Treat the
  constants above as candidate evidence until re-picked on the confirmed selector token.
- The menu icon is a separate pre-scaled 24x24 sprite/flipbook, not a 3D model. A VRAM
  rectangle copy cannot scale the 64x64 LEVEL01 glyph down to 24x24, so the Journey token
  needs either pre-scaled per-level source tiles plus a UV selector hook, or a different
  draw/asset path.

Unsafe hook attempts, not shipped:
- `mod/mods/flik_result_emblem_experimental.asm` records the failed constants/hook site.
- Attempt 1: DAT-base-only hook at GPU linked-list DMA start copied the glyph every LEVEL01 frame. This visibly corrupted gameplay with a vertical custom-glyph texture strip.
- Attempt 2: DAT-base + result-packet signature gate avoided the broad copy but crashed/black-screened the guest by frame `9000`.
- `flik_result_emblem` is intentionally not registered in `mod/mods/registry.py` and not present in `mod/mods.yaml`.

Shared asset stager retained but no longer auto-shipped:
- `tools/flik_emblem_edit.py` now has `stage_patch_menu_result()` for the large result coin
  and the three observed 24x24 Flik's Journey spin-frame tiles.
- `tools/flik_emblem_edit.py` also has `stage_patch_training_result()` for only the
  Training LEVEL COMPLETE coin in `LEVEL00/LEVEL2.RAW`; unlike the shared-menu stager, it
  does not edit the tiny Journey spin-frame tiles.
- `stage_patch_training_ingame()` patches only the actual Training in-game coin in the
  LEVEL07 Training atlases: `LEVEL07/LEVEL.RAW` chunk 12 and `LEVEL07/LEVEL1.RAW`
  chunk 13, rect `64,0,64,64`. It deliberately does not patch the shared runtime
  CLUT used by the visible primitive.
- `mod/mods/registry.py` registers `flik_menu_result_emblems_level2`
  (`LEVEL00/LEVEL2.RAW`) for explicit experiments. The `LEVEL00/LEVEL.RAW` helper remains
  present for manual RE experiments only; the GUI/manifest does not emit either shared
  menu target automatically.
- Decoded staged preview `/tmp/flik_menu_result_patched_preview.png` shows the custom glyph
  in the shared large result tile and all three tiny Journey spin-frame tiles.

Final Training in-game verification, 2026-07-06:
- Correct source attribution used `gpu.readVramRect` on live `tpage x=704,y=0`, converting
  the 32x64 raw16 block into a 128x64 4bpp nibble strip. Exact zero-difference matches
  included the Training atlas copies `LEVEL07/LEVEL.RAW` chunk `12`, rect `0,0,128,64`,
  and `LEVEL07/LEVEL1.RAW` chunk `13`, rect `0,0,128,64`; the right half is the FLIK
  token tile.
- `tools/flik_emblem_edit.py` now patches both Training in-game atlas copies at
  rect `64,0,64,64`; `tools/mod_studio_gui.py`
  emits both `flik_emblem_training_ingame` manifest entries from the single Training
  emblem picker.
- Final rebuild command:
  `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`
  - `build/ABL_ALLMODS.bin` sha256 `e58b4745f61522de6f8fef5c6a9ce43cb75d24f0576e53f4b50f11596fb68655`
  - `LEVEL07/LEVEL.RAW` embedded at LBA `12200`, `539687` bytes, sha1 `203e1a2d18a6de1b3f716e75f754324f7f6bc85f`
  - `LEVEL07/LEVEL1.RAW` embedded at LBA `12524`, `579767` bytes, sha1 `0738a23720d58ab55954c234d68929bc0cdee85f`
- Live verification used isolated DuckStation port `23870`, config
  `/tmp/duckstation-debugger-training-emblem-livepick`, disc `build/ABL_ALLMODS.cue`,
  movie `collecting_FLIK_LEVELTRAINING.movie.json` only to enter Training gameplay,
  then forced F/L/I/K type-`0x3f` records 50-53 visible and teleported Flik to each
  coordinate while anchoring position and zeroing velocity before and after every
  frame advance. Native mask advanced `0x00 -> 0x01 -> 0x03 -> 0x07 -> 0x0f`.
- Paused verification frame: `/tmp/training_live_final_open/paused_after_anchored_collection.png`
  at emulator frame `4239`. Live texture decode:
  `/tmp/training_live_final_open/live_t704_clut1008_253_tile.png`, showing the `X`
  token unchanged and the FLIK token slot replaced by the Training hourglass glyph.

Training in-game colour regression/fix, 2026-07-06:
- User retest showed the in-game Training emblem shape was correct, but still rendered through
  the blue/silver gameplay token palette, while the LEVEL COMPLETE coin used the red/yellow
  Training palette.
- Live `gpu.readVramRect` at `x=1008,y=253` proved the gameplay primitive uses the original
  blue/silver CLUT row. Matching that CLUT back to decompressed pages found the source at
  `LEVEL07/LEVEL.RAW` chunk `11` slot `4` and `LEVEL07/LEVEL1.RAW` chunk `12` slot `4`.
- Patching that CLUT source made the in-game token warm/red but also recoloured Flik's
  head/HUD portrait. That experiment was reverted. Cold-boot VRAM after the revert read
  the original grayscale row again:
  `eb5a def7 dad6 d6b5 d294 ce73 ca52 c631 c210 bdef b9ce b9ce b5ad b18c ad6b a94a`.
- Current asset-only fix: leave the shared gameplay CLUT untouched, and make the Training
  LEVEL COMPLETE coin use `patch_palette:false` so it is palette-constrained like the
  in-game spawned coin. `tools/mod_studio_gui.py` now emits this flag for Training, and
  `stage_patch_training_result()` defaults to it.
- Rebuild after the revert/consistency fix:
  `python3 -m py_compile tools/flik_emblem_edit.py tools/mod_studio_gui.py mod/build.py`
  and `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`
  - `build/ABL_ALLMODS.bin` sha256 `4bee23f22027b396a4233c2278384de8bd4c8a8c430fcbea0cd611b46818f4d0`
  - `LEVEL00/LEVEL2.RAW` embedded at LBA `2593`, `121727` bytes, sha1 `4692ba933c557bcc1025796aac86551231ca2c0c`
  - `LEVEL07/LEVEL.RAW` embedded at LBA `12200`, `539687` bytes, sha1 `bbfa1e596ae6028b6a330bb3a87aaae78a0b628a`
  - `LEVEL07/LEVEL1.RAW` embedded at LBA `12524`, `579767` bytes, sha1 `4272fd84f8bd51dfd76f0051f413b852f20f1179`
- Cold-boot verification on isolated DuckStation port `23913` with a private config/runtime
  entered Training via `collecting_FLIK_LEVELTRAINING.movie.json` to frame `4205`.
  Capture `/tmp/training_final_build_start.png` shows Flik's head back to the normal
  blue palette. Live `gpu.readVramRect {x:1008,y:253,width:16,height:1}` read the
  original grayscale CLUT row above. Live `gpu.decodeTexture` of `tpage x=704,y=0`,
  CLUT `1008,253`, wrote `/tmp/training_final_build_t704_clut1008_253.png`, showing
  the Training atlas with the right-hand FLIK token replaced and the neighboring X token
  still on the original shared palette.
- Result-copy static verification rendered
  `/tmp/training_result_palette_constrained_preview.png` from the exact
  `stage_patch_training_result()` params; it now uses the native result palette instead
  of the red/yellow custom CLUT, matching the in-game palette-constrained treatment.
- Full-colour Training in-game parity remains a runtime RE task: the draw primitive needs
  a FLIK-only CLUT redirect or a duplicated per-token CLUT/draw source, not a shared RAW
  CLUT edit.

Training clean-token correction, 2026-07-06:
- User retest showed the previous palette-constrained build was worse in two ways:
  the in-game spawned token had a filled dark rectangle around the emblem, and the
  result/status coin still showed remnants of the original `FLIK` face. Root cause:
  the uploaded Training test PNG was sparse/transparent, while the in-game stager had
  `preserve_transparent:false`; transparent source pixels were quantized into visible
  dark texels. Changing only to `preserve_transparent:true` preserved the original
  `FLIK` lettering behind the transparent gaps, so the source art itself also needed
  to cover the coin face.
- New Training-only test asset:
  `~/Downloads/ABL/custom_signs/flik_emblem_training_clean_coin.png`,
  sha256 `43dcca6289851bfc5d3ce6d52a1df752c9dd8758c39bf360920401b16e623c71`.
  It is a silver-friendly opaque coin-face glyph inside a transparent outer boundary.
  This covers the old `FLIK` text while preserving the sprite's native edge pixels.
- Code changes:
  - `stage_patch_training_ingame()` now forces `preserve_transparent:true` and still
    forces `patch_palette:false` to avoid the shared Flik-head CLUT regression.
  - `tools/mod_studio_gui.py` emits `preserve_transparent:true` for both
    `flik_emblem_training_ingame` entries.
  - `image_to_emblem_indices()` now square-crops taller uploads before resizing to
    64x64 token targets, so a 64x80 Training badge upload is not vertically squashed
    into the spawned/result coin copies.
  - `mod/mods.yaml` now points Training emblem entries to
    `flik_emblem_training_clean_coin.png`.
- Final rebuild:
  `python3 -m py_compile tools/flik_emblem_edit.py tools/mod_studio_gui.py mod/build.py`
  and `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`
  - `build/ABL_ALLMODS.bin` sha256 `631405da33f4c582ef9fcbb948a04ba7ebdae3279db413267ce545263d0a3b21`
  - `LEVEL00/LEVEL.RAW` embedded at LBA `2339`, sha1 `838133b96ffc103aeb84e87bc7ff4ebcee221d06`
  - `LEVEL00/LEVEL2.RAW` embedded at LBA `2593`, sha1 `51c49790387fb14d0099bd48d783bd58a13c7534`
  - `LEVEL07/LEVEL.RAW` embedded at LBA `12200`, sha1 `b5e6e769ca410e3b3d9524d15d41d35df6b9359b`
  - `LEVEL07/LEVEL1.RAW` embedded at LBA `12524`, sha1 `e647bff5561af221eecd5c4634d14296aebf7258`
- Cold-boot Training verification used isolated DuckStation config
  `/tmp/duckstation-debugger-training-clean-519975`, port `23931`, token
  `debugger-training-clean`, disc `build/ABL_ALLMODS.cue`. The movie
  `collecting_FLIK_LEVELTRAINING.movie.json` was used only to enter Training at
  frame `4205`; then entries 50-53 were moved to Flik's current position and forced
  visible. This kept the camera stable while using the native pickup path:
  `[0x800A65A2]` became `0x0f`, and all four entries received the consumed
  `Y=0x80000000` sentinel.
- In-game spawned-token proof:
  `/tmp/training_clean_token_stable_final.png`. The frame shows the clean replacement
  coin with no black rectangle and no old `FLIK` face; Flik's head remains normal blue.
  Live source decode:
  `/tmp/training_clean_live_t704_clut1008_253.png`; live CLUT `1008,253` remained the
  original shared grayscale row.
- Training result-screen proof:
  after the native collection test, writing the known transition latch
  `0x800823A0=1` reached the level-complete screen by frame `5431`. Capture:
  `/tmp/training_clean_force_latch_480.png`. The result screen shows `4/4` with the
  same clean replacement coin. This is a controlled verification shortcut; the live
  scan found only Training sector `24:code3`, and anchoring Flik there did not write
  the transition latch over 180 frames, so the actual Training exit/objective trigger
  remains separate RE work.

Current Training upload state, 2026-07-06:
- User confirmed the GUI-driven custom Training emblem works together for the in-game
  spawned token and LEVEL COMPLETE result coin.
- Active manifest entries now point the single Training upload to
  `~/Downloads/ABL/custom_emblems/TRAINING.png` for all Training copies:
  `LEVEL00/LEVEL.RAW`, `LEVEL07/LEVEL.RAW`, `LEVEL07/LEVEL1.RAW`, and
  `LEVEL00/LEVEL2.RAW`.
- `custom_emblems/TRAINING.png` is RGBA `1254x1254`, has real alpha
  (`A` extrema `(0,255)`), and sha256
  `69c0a16c251b1bed5203f4905252581d9007bbc381f9f3ece5c210bd6ef4e0a7`.
  The former green key background was converted to transparency before use.
- `tools/mod_studio_gui.py` emits the Training-specific fan-out from one picker:
  `flik_emblem` for `LEVEL00/LEVEL.RAW`, two `flik_emblem_training_ingame`
  entries with `preserve_transparent:true`, and `flik_emblem_training_result`
  with `patch_palette:false` plus `preserve_transparent:true`.
- GUI picker bug fixed: the FLIK emblem entry now captures the same `StringVar`
  used by the visible Entry widget, and manifest loading updates the existing
  variable instead of replacing it. Uppercase image extensions are accepted.
- No new runtime MOD C hook is shipped for Training. The delivered MOD path is the
  Python asset-stager/manifest path; the RE source note
  `src_re/flik_emblem_results_menu.c` documents the live ownership and why the
  shared Training gameplay CLUT must not be patched.

Scope caveat: the explicit shared stager is not a LEVEL01-only runtime solution and can
affect any UI that samples those same shared FLIK coin tiles. It is not part of the active
ALLMODS manifest. A strictly level-specific Journey selector still needs a safe hook point
that chooses per-level pre-scaled frames at draw time.

## Related
[[HUD letter glyphs and word swap]] · [[Experiment - FLIK5 five-letter token gate]] · [[Menu and HUD structure]] · `tools/flik_emblem_edit.py`
