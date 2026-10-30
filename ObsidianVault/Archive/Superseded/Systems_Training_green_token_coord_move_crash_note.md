---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Training green token coord move crash note.md
aliases:
  - "Training green token coord move crash note"
migration_action: split
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Training green token coord move crash note.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Training_green_token_coord_move_crash_note.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

# Training green token coord move crash note

Date: 2026-07-07

## Summary

The black-screen build happened because the first attempt treated a coordinate-only request as a full manifest rebuild. It reran the Training word-pickup asset path and rebuilt multiple Training files instead of changing only the first green token's type-0x3f source coordinate.

For this class of request, do not rebuild `ABL_ALLMODS` and do not rerun the Training word-pickup workflow. Use a known-working image as the source and patch only the embedded `LEVEL07/LEVEL1.DAT` x-coordinate.

## What Went Wrong

Bad/superseded image, preserved only for crash provenance:

- `build/ABL_GREEN_TOKEN_RIGHT_BROKEN_MANIFEST_REBUILD.bin`
- `build/ABL_GREEN_TOKEN_RIGHT_BROKEN_MANIFEST_REBUILD.cue`

That image was built from `build/green_token_right.mods.yaml` through:

```sh
python3 mod/build.py --mods build/green_token_right.mods.yaml --out build/ABL_GREEN_TOKEN_RIGHT --force
```

This was too broad. The build staged EXE, Training RAW/BIN/DAT, Training audio, menu/result emblem files, and Anthill emblem files. It also used the current WIP Training word-pickup stager. The user observed a black screen when loading Training from this image.

The key rule: moving the first green tutorial token does not require touching the EXE, RAW art, panel code, audio, sign images, or type-0x3f count. It is just a coordinate edit to the first kind-`0x2B` Training token.

## Crash Class

Training is sensitive to `LEVEL07/LEVEL1.DAT` size/layout changes. The word-pickup tool now carries the same warning in code: growing this DAT by a tail blob previously shifted following data in RAM and crashed Training with a break-7 divide-by-zero at `0x8003F060`.

Even if a current WIP stager has moved that panel blob elsewhere, it is still the wrong tool for a coordinate-only token move. Rerunning the full stager changes too many files and can introduce unrelated Training-load failures.

## Correct Fix

Fixed image:

- `build/ABL_GREEN_TOKEN_RIGHT.bin`
- `build/ABL_GREEN_TOKEN_RIGHT.cue`
- `build/ABL_GREEN_TOKEN_RIGHT_FIXED.bin`
- `build/ABL_GREEN_TOKEN_RIGHT_FIXED.cue`

`ABL_GREEN_TOKEN_RIGHT_FIXED` and `ABL_GREEN_TOKEN_RIGHT` have identical BIN contents. The fixed image was copied from the then-working `build/ABL_ALLMODS.bin` and patched in place.

- Source `ABL_ALLMODS.bin` SHA-256 at patch time: `f290d3b2effd5a91969374f2a4160867c369931ab75204546c94cfb32ae2952f`
- Patched BIN SHA-256: `f2786fba653ed9b38017ef0472a951d55978f9f68a9c076fdc11d4e1682900ee`
- Main CUE SHA-256 (`ABL_GREEN_TOKEN_RIGHT.cue`): `2998e665c9ce8b398c894b77ae95258f9c2da8aec08c891491affc6f4bb086d9`
- Alias CUE SHA-256 (`ABL_GREEN_TOKEN_RIGHT_FIXED.cue`): `9d7993cb3a268ce61e04024d46186d116e9bc05004f8f9f6531bed7d2b06c385`

The only binary differences from the source image are two bytes at raw disc offsets:

- `0x01BFD540`
- `0x01BFD541`

Those two bytes encode the s32 x-coordinate change:

- source entry: `LEVEL07/LEVEL1.DAT` type-0x3f entry 56, kind low byte `0x2B`
- file coordinate: x `-1197 -> -597`
- y/z unchanged: `-50 / 148`

## Verification

Offline verification:

- Embedded `LEVEL07/LEVEL1.DAT` still parses.
- Type-0x3f count remains `66`.
- Entry 56 readback: kind `0x2B`, x/y/z `-597/-50/148`.
- Fixed BIN differs from source `ABL_ALLMODS.bin` by exactly two bytes.

DuckStation verification:

- Isolated config: `/tmp/duckstation-debugger-green-token-fixed`
- Port/token: `23623` / `green-token-fixed`
- Disc: `~/Downloads/ABL/build/ABL_GREEN_TOKEN_RIGHT_FIXED.cue`
- Movie: `TRAINING_NPC_STAGES.movie.json`, from boot, playback reproducible.
- At movie frame 3900/4500, scene id remained `0x11` (Training).
- Live cached first kind-`0x2B` pointer: `0x8011F54C`.
- Live token x readback: `-597`.
- Frame 4500 screenshot was normal Training gameplay, not black.

## Future Rule

For a Training tutorial token coordinate move:

1. Start from the known-working image the user wants to preserve.
2. Resolve the embedded `LEVEL07/LEVEL1.DAT` LBA/size for that exact image.
3. Validate type-0x3f entry 56 is the first kind-`0x2B` token before patching.
4. Patch only the coordinate bytes.
5. Verify the new image differs from the source image only at the coordinate bytes.
6. Cold-boot with the Training movie before handing it back.

Do not route this through the full ALLMODS workflow or `training_word_pickups` unless the user explicitly asks to rebuild that whole subsystem.

## Related

[[Training NPC progression]] · [[Training board sign images]] · `src_re/training_tutorial_progression.c` · `tools/training_word_pickups.py`
