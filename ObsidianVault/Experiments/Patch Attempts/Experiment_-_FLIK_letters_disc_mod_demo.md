---
kind: experiment
id: Experiment_-_FLIK_letters_disc_mod_demo
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - FLIK letters disc mod demo.md
aliases:
  - "Experiment - FLIK letters disc mod demo"
---

# Experiment — FLIK letters disc-mod demo (end-to-end, verified)

> Migrated from `ObsidianVault/Experiments/Experiment - FLIK letters disc mod demo.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — FLIK letters disc-mod demo (end-to-end, verified)

> **Capstone demo (2026-06-18):** edit → byte-exact disc rebuild → boot the patched disc → the change is live. Moved LEVEL01's 4 scattered FLIK-letter pickups into a visible cluster, rebuilt the full disc, and confirmed in-game from the rebuilt image. Proves the whole RE→mod pipeline as one artifact.

## The edit
LEVEL01.DAT type-0x3f entries **50–53** (kinds 0x10/0x11/0x12/0x13 = F/L/I/K), X/Y/Z only (kinds untouched) → [[MEM - Type-0x3f placement record]]:
| Letter | Was (X,Y,Z) | Now |
|---|---|---|
| F (50) | (−8616, 0, 4601) | (−8616, −50, 4601) |
| L (51) | (455, −50, 21860) | (−8566, −50, 4601) |
| I (52) | (−9436, −50, −1950) | (−8516, −50, 4601) |
| K (53) | (9490, −50, 9583) | (−8466, −50, 4601) |
Lined up along +X at the F's original valid spot (file coords; runtime = `<<5`).

## Rebuild — byte-exact except the patch
`mkpsxiso REBUILD/abl.xml` → `mkpsxiso.bin` (738,285,744 B, 313,897 sectors — identical size). `cmp` vs the pristine master: **only 170 bytes differ**, all within one DAT sector (~LBA 2906) = the 48 coordinate bytes + that MODE2/2352 sector's regenerated EDC/ECC. Source DAT restored to pristine after. Confirms [[Finding - Disc rebuild is byte-exact]] holds for a real content edit.

## Verification — live, from the rebuilt disc
- **`cd.overlayFile` did NOT work here** ([[API - CD overlay]], untested feature): overlaying the patched LEVEL.DAT sector reported `served_count=0` — the game's DAT read path isn't caught by the `ProcessDataSector` hook. Noted as a real limitation.
- **Save-state-repoint method WORKED** (new, reusable): DuckStation save states **embed the disc path** (uncompressed header, here at offset 216, 62 bytes, followed by the zstd state magic `28 b5 …`). Copied the pre-load state `SCUS-94288_2.sav`, swapped the embedded path to a **same-length** `.cue` pointing at `mkpsxiso.bin`, loaded it (→ mounts the patched disc), advanced through the LEVEL01 load. **All 4 FLIK letters loaded at the clustered coords** (L/I/K moved from their scattered Z to Z=4601). The level rendered "Welcome to Ant Island" and played (`flik_demo3.png`, Flik on the pebbled ground) — all from the rebuilt image.

## Reusable method (verify a rebuilt disc without an operator boot)
1. Rebuild the patched BIN/CUE; `cmp` vs master to confirm localized diff.
2. Make a same-length `.cue` (in `mkpsxiso.bin`'s dir) and **byte-replace the disc path** in a copy of a *pre-load* save state (the embedded path is plaintext before the zstd blob; same length ⇒ no checksum/length break).
3. `loadState` the repointed copy → mounts the patched disc; advance through the level load → reads the patched content. (Plain `loadState` of the original state re-mounts the **original** disc, masking the patch — that's the trap this avoids.)

## Artifacts
- Patched disc: `REBUILD/mkpsxiso.bin` + `.cue` · repoint cue `REBUILD/flik_demo_patched_disc__.cue` · repointed state `SCUS-94288_2_FLIKDISC.sav` · frames `flik_demo{,2,3}.png`.

## Related
- [[MEM - Type-0x3f placement record]] · [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Finding - Disc rebuild is byte-exact]] · [[API - CD overlay]] · [[FUNC_8001CDC0]] · [[FUNC_80053814]]
