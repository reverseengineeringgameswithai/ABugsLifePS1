---
kind: experiment
id: Experiment_-_Training_TRAINING_follow-up_bugs
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: medium
legacy_source: ObsidianVault/Experiments/Experiment - Training TRAINING follow-up bugs.md
aliases:
  - "Experiment - Training TRAINING follow-up bugs"
---

# Training TRAINING follow-up bugs — ALL RESOLVED (2026-07-06)

> Migrated from `ObsidianVault/Experiments/Experiment - Training TRAINING follow-up bugs.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Training TRAINING follow-up bugs — ALL RESOLVED (2026-07-06)

Original bug list (kept for history) and their resolutions. Current result-screen
fix disc: `build/ABL_ALLMODS.bin` sha256
`fe11deabc6b84a94c6a00d28081a34f6669c48d4e473dc46e7cf0a0b132bdc2a`.
Earlier final disc:
`build/ABL_ALLMODS.bin` sha256 `f290d3b2...` (cold-boot verified in isolated
DuckStation, manual menu navigation — input movies desync across disc-layout
changes and one desynced replay soft-locked into attract mode; navigate by
polling scene id `0x80082504` instead).

## 1. SELECT HUD still only shows FLIK → FIXED
- Panel now draws 8 slots reading bits 0..7 of `0x800A65A2`. The first attempt
  appended slots 4-7 at `x=0xD0+n*0x18` from the FLIK5-proven tail hook
  `0x80052EF4`; that spelled `TRAINING`, but the word was not centered because
  slots 0-3 had already drawn at the retail 4-letter positions.
- 2026-07-07 center-align fix: the Training word now hooks the first SELECT-letter
  bitmask load at `0x80052D98`, scene-gates on Training (`0x11`), and jumps to a
  RAW-resident blob that draws **all 8 slots** at `x=0x48+i*0x18`. Outside
  Training the gate replays the displaced `lui/lbu` and returns to `0x80052DA0`,
  so the original 4-letter row stays at `0x70,0x88,0xA0,0xB8`.
- The panel blob is **position-independent code riding a RAW type-0x22 chunk**
  under unused tile 0x34: the generic chunk loader (`0x8003B830`) registers its
  payload in `anim_table[0x80089638+0xD0]`; the Training-gated dynamic gate at
  `0x8008157C` jumps through that pointer (+4 past the w/h header).
- Panel pulse-latch compare `0x80052D74` scene-gated via branch-preserving cave
  `0x800810F8` (mask 0xff in Training / 0x0f elsewhere).
- Mod Studio GUI: Training tab now has an "In-world pickup word (8 letters)"
  field (validates via `training_word_pickups.plan_word`; round-trips
  mods.yaml `training_word_pickups.params.word`).

## 2. Emblem popped up on EVERY letter → FIXED
- Root cause: the old `jal COMPARE_CAVE; nop` at
  `0x80053D74/0x80053ED0/0x8005402C/0x80054188` replaced BOTH the mask-load
  `addiu v0,zero,0x0f` AND the completion branch `bne v1,v0,0x800545bc` — the
  branch was gone, so every collection fell into the completion/emblem path.
- Fix: compare cave `0x80081488` now does compare AND branch: complete →
  `jr ra` (falls into completion at site+8), incomplete → `j 0x800545BC` with
  the pristine delay-slot `addiu s1,zero,-2` replicated. Scene-gated masks
  0xff (Training) / 0x0f (native).

## 3. Letters looked garbage vs native → FIXED
- Native letters are 16-frame voxel-extruded spins (24×24, depth ≈5, mirrored
  back view, per-frame brightness modulation), stored per letter as RAW
  type-0x22 chunks `{magic 0x22, tile, w,h}` + 16×0x120 frames
  (LEVEL07/LEVEL.RAW ch14-17 = F/L/I/K, LEVEL1.RAW ch15-18) and pumped into
  VRAM cells every other frame by the HUD anim driver `0x80052574`
  (`upload_anim_frame 0x80026DF4`, spin-phase stagger 2 per letter).
- New generator `tools/glyph_spin_native.py`: voxel-extrusion renderer
  validated frame-by-frame against the native F strip (widths match exactly);
  letterforms at native metrics (≤16 px wide, ~4 px strokes, golden CLUT
  indices ~9-12 with left-dark bevel). `I` reuses the native strip verbatim.
- T/R/A/I replace the native F/L/I/K strips (fully native pipeline); N and G
  ride new kinds 0x26/0x27: appended 0x22 chunks auto-register their anim
  records; EXE descriptors `0x80082024`/`0x80082018` (blackberry kind-0x25
  precedent) point at pristine-empty page cells (168,72)/(24,96); a
  Training-gated pump cave at `0x800813B0` (hooked over the tile-0x14 setup at
  `0x800525E4`) calls the native uploader for tiles 0x26/0x27 with phases
  ctr-8 / ctr-14.
- GOTCHA: the level loader REFILLS each kind descriptor's CLUT halfword (+6)
  at scene load (0x3676/0x3674 observed) — a chained stamp cave `0x80081590`
  rewrites both to golden `0x3677` every frame.

## 4. Berry throwing bugged (vanish ~0.5 s, intangible) → FIXED
- Root cause: `VIS_HELPER_CAVE` was placed at `0x800813AC` = the **delay slot
  of blackberry CAVE_TCOLOR2's return jump** (`j 0x80014a78` @ 0x800813A8).
  Every drawn contact object executed the helper's first word `lui t1,0x8008`
  inside the contact-object emitter, so `sb t1,0x32(t8)` at `0x80014A90`
  stored 0 instead of 0x21 — clearing the record's alive flag (+0x32 bit
  0x20). The updater kills any projectile with `flags & 0xa0 == 0`
  (`sh zero` @ 0x8005A754): berries froze ~2 frames after throw and despawned.
- Fix: caves start at `0x800813B0`; `0x800813AC` stays nop (same failure class
  as the earlier 0x800811BC collision — **always measure armips cave extents
  including the final delay-slot nop**).
- Verified live: red berry record (`0x800B0F80`) flew 70 frames with flags
  0x21, counter ticking 0x63→0, natural expiry.

## 5. Sacrificed animation artifacts (sparkle/butt-slide/roots) → FIXED
- Root cause: the old tool baked 8-frame strips + static tiles over rows
  96..248 of the pickup page (LEVEL.RAW ch11 / LEVEL1.RAW ch12), which is
  almost fully occupied by native art.
- Fix: page chunks are no longer touched at all (letters animate via cell
  uploads, not page bakes). Cold boot: page rows 96..248 are byte-identical to
  pristine except the runtime-upload zones (G cell rows 96-119, native anim
  uploads at 112-127). Grain sparkles visible in-game again.

## Hard-won placement lessons (this session)
- `0x8007FDC0..0x80080BE0` reads all-zero during gameplay **because the game
  clears it as a workspace at load** — EXE-baked code there is WIPED. Never
  bake caves there.
- **Growing LEVEL07/LEVEL1.DAT is fatal**: +336 B of tail blob shifted
  whatever follows the DAT in RAM → break-7 divide-by-zero at `0x8003F060`
  within seconds of Training load. (LEVEL01 LEVEL.DAT tolerated tier-3
  appends; LEVEL07/LEVEL1.DAT does not.) RAW chunk growth IS tolerated.
- The RAW type-0x22 chunk loader is a general-purpose blob loader: any chunk
  registers `anim_table[tile] = payload+8`. Unused tile ids give you
  auto-registered, relocation-safe pointers to arbitrary data/code.

## Verification (final build, cold boot, isolated DuckStation port 23460)
- Training scene 0x11 reached by scripted menu navigation; stable 600+ frames
  plus panel-forced soak; attract/FMV/menu path healthy (PC-in-kernel during
  FMV is normal, not a crash).
- anim[0x26]/[0x27]/[0x34] registered; desc CLUTs stamped 0x3677; N/G VRAM
  cells (682,72)/(646,96) animating; SELECT panel shows TRAINING (bright
  gold collected / dimmed uncollected via bits); in-world word visible on the
  ledge wall; captures in the session scratchpad.
- NOTE: `SPINNING_*.sav` and `collecting_FLIK_LEVELTRAINING.movie.json` are
  stale against the new layout (states restore old RAM/VRAM; movies desync).
  Re-record after play-testing this build.

## 2026-07-07 SELECT centering verification
- Rebuilt command: `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`.
- Output disc: `build/ABL_ALLMODS.bin` SHA-256
  `88e6da6bb1c05b9167155409c878992a2ac48f5662e64451c9c25d68119cfa4b`.
- Static patched EXE check: `0x80052D98` = `j 0x8008157C`; `0x80052EF4`
  reverted to native `lui v1,0x800b` / `addiu v1,v1,0x194`; gate `0x8008157C`
  resumes non-Training at `0x80052DA0`.
- Isolated DuckStation: config `/tmp/duckstation-debugger-training-select-left2`,
  port `23975`, token `training-select-left2`, binary
  `~/duckstation/build-release/bin/duckstation-qt` SHA-256
  `5538e0e0ca198b54f184ba5650e9a708ef4faf79b47180e49430e912fcc35448`.
  Mounted media verified as `~/Downloads/ABL/build/ABL_ALLMODS.cue`
  (`SCUS-94288`, A Bug's Life).
- Training movie `allmods_training_letters_mismatch_movie.movie.json` SHA-256
  `b195bad0b662ac88b42fc57aa7911567d095959cf63b44f4494e909896cd3cd1`,
  from boot, advanced to final frame with `movie.advanceToFrame`, reached scene
  `0x11`. Holding SELECT for 90 frames produced
  `/tmp/training_select_left2_after.png` (SHA-256
  `ddeba6ad99dc3efd9d14e76b29d3d971f829ad93d633e3c338c73a81d4961b8`):
  `TRAINING` sits between the Flik head and the top-right leaf after the
  second follow-up 8-pixel left nudge (`x=0x48+i*0x18`).
- Non-Training control: `flik_to_level01_stall.mv.movie.json` SHA-256
  `fa2e81925fbad56af07081fbfe6980f2789a0dd72e6b63b13f9e7b5fc23ed264`
  reached scene `0x1`; holding SELECT for 90 frames produced
  `/tmp/level01_select_4slot_left2build_check.png` (SHA-256
  `40458f123950b4e2cbcd59db5aab3c418ce4552d6f91571f5684ff1ce625fad6`),
  showing the unchanged native 4-slot row.

## 2026-07-07 LEVEL COMPLETE counter/glyph row verification
- Root cause: the result-screen row still used the old 4-slot row and the retail
  raw-byte count table in `BITS/MEMORY.BIN`; with Training's `0xff` progress byte,
  the old table could feed garbage count targets and make the counter continue upward.
- Fix: `tools/training_word_pickups.py` patches `BITS/MEMORY.BIN` row
  `0x800B80A8..0x800B8258` with a compact 8-slot renderer. It computes the
  collected-letter popcount inline, stores that dynamic count target at
  `0x800B8248`, reads the staged active word length from `0x800B8249`, stores the
  active tile ids at `0x800B8250`, and makes the row-2 medal checks use dynamic
  `s7` instead of literal `4`. `0x800BE444` is not a table/scratch site: Flik's
  Journey uses that region for the visible vine/leaf path, and overwriting it
  removed the vine.
- Follow-up visual fix: the result screen had been drawing static tile cells.
  `training_word_pickups.py` now also stages the TRAINING type-`0x22` spin-strip
  records into `LEVEL00/LEVEL2.RAW`; the row pumps every slot through native
  `upload_anim_frame 0x80026DF4` before branching to the lit or dim draw path,
  and stamps extra descriptors `0x26/0x27` to golden CLUT `0x3677` at result time.
- Verification build: `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`;
  `build/ABL_ALLMODS.bin` SHA-256
  `fe11deabc6b84a94c6a00d28081a34f6669c48d4e473dc46e7cf0a0b132bdc2a`.
- Movie `ALLMODS_COLLECTING_TRAINING.movie.json` SHA-256
  `fbc0ef077f5bcbd3f384e8d0a0f55871b47101d20e8db8481394c35b1a3615b7` stayed
  reproducible through frame `8300`; frame `7218` landed in Training scene `0x11`
  with `0x800A65A2=0xff`, and frame `8000` was the result overlay.
- Final layout: row `X = 8 + i*10`; counter `X = 8 + wordLen*10 + 88`, so
  TRAINING uses counter base `176` without hardcoding the count target or total.
- `execTrace` at row resume `0x800B8258`: 776 hits, first frame 7525
  `s0=0xB0,s6=0,s7=8`, last frame 8300 `s0=0xB0,s6=8,s7=8`.
  `execTrace` at count-cap compare `0x800B853C`: 640 hits, final frame 8300
  `s6=8,v0=8,s7=8`, proving the counter stops at `8`.
- Result frame `8000`: `anim_table[0x10]`, `anim_table[0x26]`, and `anim_table[0x27]`
  were nonzero; descriptors `0x10,0x11,0x12,0x13,0x26,0x27` all carried CLUT
  `0x3677`.
- Captures `/tmp/traindimfinal/result_8000.png` and
  `/tmp/traindimfinal/result_8300.png` show staggered spinning TRAINING
  letters tightened left of the capped `8/8` counter. Frame SHA-256 values:
  `8000=ae2557573bf5dd02cfc6c474724bdae05c8b4faf95faae5f64c5b3242cecca0d`,
  `8300=8211d6577cf54e3c651e477e85b37355eae7960c23dbbb84318e1526bb8ffb78`.
- Forced-uncollected visual check after reaching result frame `8000` wrote
  `0x800A65A2=0x00`; result state bytes became `00 08`, and captures
  `/tmp/traindimspin/dim_a.png`, `dim_b.png`, and `dim_c.png` show the dim
  TRAINING row changing spin phase instead of freezing. SHA-256 values:
  `4668ae0a4547269e24b7494b0f5fceed34f7276b94bb8801b87110bf10c44436`,
  `913942ee28b9535d47ab9e61c0cb7be1d175772b115f44d4fc4dd7590535743f`,
  `3a86ca8a84d05f675f0811cbd8ccf42bdb34aa34118811562b44c77eba2f92f4`.
- Front-end Start-spam check after the final build used isolated config
  `/tmp/duckstation-debugger-training-dim-front`, port `23728`; capture
  `/tmp/traindimfront/front_359.png` SHA-256
  `d8ab3579f8cff4588c8401844c4919716d17ef69035a734775192ba0d5a78f4e` shows
  Flik's Journey with the vine/level path visible.

## Related
[[Experiment - Training in-world TRAINING pickup word]] ·
[[HUD letter glyphs and word swap]] · `tools/training_word_pickups.py` ·
`tools/glyph_spin_native.py` · `src_re/hud_800526f4.c` ·
`src_re/pickup_handlers_80054288_80054554.c`
