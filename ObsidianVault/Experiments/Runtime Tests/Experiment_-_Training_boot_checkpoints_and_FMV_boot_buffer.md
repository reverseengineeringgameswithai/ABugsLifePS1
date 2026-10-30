---
kind: experiment
id: Experiment_-_Training_boot_checkpoints_and_FMV_boot_buffer
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: medium
legacy_source: ObsidianVault/Experiments/Experiment - Training boot checkpoints and FMV boot buffer.md
aliases:
  - "Experiment - Training boot checkpoints and FMV boot buffer"
---

# Training boot checkpoints + the FMV boot-buffer cave trap

> Migrated from `ObsidianVault/Experiments/Experiment - Training boot checkpoints and FMV boot buffer.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Training boot checkpoints + the FMV boot-buffer cave trap

## Why this exists
`build/ABL_ALLMODS` was hanging at the PlayStation/intro-FMV logo and never
reaching a level. This note records (1) a **pristine boot→Training reference
playthrough with checkpoints** for future desync debugging, and (2) the
**root cause + fix** of the boot hang.

## Reference: pristine + Training movie checkpoints
Movie `collecting_FLIK_LEVELTRAINING.movie.json` (from-boot, 9299 frames) on the
**pristine** `Disney-Pixar A Bug's Life (v1.0).cue`, isolated DuckStation
(port 23460). Scene id lives at **`0x80082504`**; type-0x3f record ptr at
`0x80096E9C` (nonzero once a level's objects are resident); heartbeat =
`0x800A7E28` (16-frame HUD spin counter, advances every frame while alive).

| frame | scene `0x80082504` | CD lba | drive | meaning |
|---:|---|---:|---|---|
| 31 | 0x0 | 0 | Idle | BIOS/boot |
| 184 | 0x270 | 0 | Idle | uninitialised scene word (pre-game) |
| 934 | 0x0 | 403 | Idle | logos / menu path |
| 3334 | 0x11 | 264853 | SeekingLogical | **Training reached** |
| ~4121 | 0x11 | — | — | Training fully resident (rec ptr live, letters uploaded) |

Verified image: Flik + instructor in the Training level, WELCOME BACK sign.

**Cold-boot CD signature (no input):** boots via lba 0→166→403, reads a short
FMV probe at LEV1A.STR+88 (pc `0x80065210`), then streams the real intro from
lba ~292000 and proceeds. A disc that instead parks **Idle at LEV1A.STR+145**
(e.g. pristine 16526 / ALLMODS 16640) and never advances is HUNG — this is the
"stuck at the PlayStation logo" symptom.

**Deterministic repro of the hang:** advance the cold boot in big chunks
(`emulator.advanceFrames {frames:870}` ×3 ≈ real time). Small chunked advances
race differently and can mask it. Pristine + NOWORD boot (reach lba ~293000);
a disc with the bug parks at the FMV +145.

## Root cause of the boot hang (FIXED 2026-07-07)
The intro-FMV / boot player (pc `0x8006Bxxx`, table base read at `0x8006D308`)
uses **`0x800814BC..0x8008152F` as a ZERO-INITIALISED work buffer during cold
boot** — it reads cells it did not itself write and expects 0. Mapped live by
read/write-watching the whole `0x800810C0..0x80081800` span across a NOWORD cold
boot; the boot-touched words were exactly `0x800814BC..0x800814C7`,
`0x800814D4..0x800814D7`, `0x800814DC..0x8008152F`.

The Whiteberry berry module (`mod/patch.asm`) stops at `0x800813F0`, so it never
touches this buffer → pristine and NOWORD boot fine. The `training_word_pickups`
**visual-gate cave was at `0x80081478` and spilled into `0x800814BC`**; the FMV
player then read the cave's MIPS words as garbage buffer state and the streaming
loop hung. Isolation proof: an EXE-only build (my caves, pristine RAW/DAT — same
disc layout as booting NOWORD) reproduced the hang deterministically, and
live-reverting the hook/cave region let it boot. This is unrelated to disc
growth or the FMV's shifted LBA (moving the FMV earlier still hung; NOWORD which
is also reflowed boots).

**Fix:** move the visual gate to `0x80081460` (ends at `0x800814AC`, clear of
the buffer) and add a hard build assertion `FMV_BOOT_BUFFER = (0x800814BC,
0x80081530)` in `patch_exe()` — every `claim()` now refuses any cave overlapping
it, so this trap can't recur. Rebuilt `build/ABL_ALLMODS.bin` boots 3/3 (big
chunk) reaching lba ~293439, movie reaches Training and LEVEL01, and a whiteberry
thrown in LEVEL01 flies (38 frames of motion) with the game staying alive.

## Cave-placement rule (generalised)
The `0x800810C0` "boot-safe zero-run" is **only boot-safe up to `0x800814BB`**.
`0x800814BC..0x8008152F` is an FMV/boot work buffer (zero at rest, used at boot),
and `0x80081530..0x80081579` is a resident FMV data table (non-zero, leave intact).
`0x8008157A..0x800815C4` is a boot-untouched zero run. Any resident cave in the
buffer/table hangs the disc at the logo. Full boot-touched map (NOWORD cold boot,
128-byte read+write watches over 0x800810C0..0x80081800): ONLY `0x800814BC..C7`,
`0x800814D4..D7`, `0x800814DC..0x8008152F`.

## 8-slot SELECT panel placed with this map (2026-07-07)
The full 8-letter SELECT panel needs more draw code than any contiguous safe EXE
gap. Solution: the draw code rides a **RAW type-0x22 chunk** (tile 0x34,
`build_panel_blob`, position-independent) reached via anim_table[0x34] = unlimited
room ("more room for glyphs"). A **scene-gated** 15-word gate sits in the
`0x8008157C` zero run (above the buffer+table); GATE_DATA moved to `0x8008126C`
(below the buffer).

2026-07-07 center-align correction: the gate is now reached from first-letter hook
`0x80052D98`, not the old tail hook `0x80052EF4`. In Training it skips the native
4-slot row and draws all 8 slots at `x=0x48+i*0x18`, placing `TRAINING` between
the Flik head and the top-right leaf. Outside Training the gate replays the two
displaced `lui/lbu` instructions and returns to `0x80052DA0`, so the original
4-letter placements remain unchanged; the tail at `0x80052EF4` is pristine again.
Verified with `build/ABL_ALLMODS.bin` SHA-256
`88e6da6bb1c05b9167155409c878992a2ac48f5662e64451c9c25d68119cfa4b`:
Training SELECT capture `/tmp/training_select_left2_after.png` (SHA-256
`ddeba6ad99dc3efd9d14e76b29d3d971f829ad93d633e3c338c73a81d4961b8`), LEVEL01 4-slot
control `/tmp/level01_select_4slot_left2build_check.png` (SHA-256
`40458f123950b4e2cbcd59db5aab3c418ce4552d6f91571f5684ff1ce625fad6`). The completion token still fires at
0xff through the compare cave and retail reward path fcn_8005044c(-0xb).

## Related
[[Experiment - Training TRAINING follow-up bugs]] · [[Consolidated mod build manifest]] ·
`tools/training_word_pickups.py` (FMV_BOOT_BUFFER assertion) · `mod/patch.asm`
