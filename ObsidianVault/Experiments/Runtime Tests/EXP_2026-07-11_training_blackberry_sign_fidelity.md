---
kind: experiment
id: EXP_2026_07_11_training_blackberry_sign_fidelity
name: TRAINING blackberry sign source-to-board fidelity
status: confirmed_fixed
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mixed_original_and_mod_experiment
related:
  - Training_board_sign_images
  - MOD_training_blackberry_sign_fidelity
  - MOD_training_board_sign
---

# TRAINING blackberry sign source-to-board fidelity

## Question

Why does custom sign 2 look like a sparse blue-purple splat instead of the saved
blackberry artwork?

## Reproduction identity

- Project revision at preflight: `e6402e8717f56df37b47405f6423aad0882ed502`
  with unrelated operator WIP preserved.
- Saved source: `custom_signs/blackberry.png`, 1254x1254 true-colour RGB,
  SHA-256 `67a3a986f873b6040e5ff558d872c27deb85f45090d3edc1adf73c64428ff73a`.
- Pre-fix ALLMODS BIN SHA-256:
  `e5459d17dfd59b6a70d77125c3ee8cb6a0e0b9fb40b5ff3472072410129f6401`.
- Movie: `movies/ALLMODS_Training_Still.movie.json`, from-boot, 6994 frames,
  SHA-256 `5cff3e9e28af7964cec0c3b5190cca70b960ad3c0cff2bd1f5c741579def0c3c`.
- DuckStation fork revision:
  `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` plus its preserved debugger WIP;
  binary SHA-256
  `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
- Isolated config `/tmp/duckstation-debugger-blackberry-sign-audit`, port
  `23985`, with a per-session localhost token that was not preserved.

The movie was loaded from a cold boot, advanced to playback frame 5904, and
checked at emulator frame 5905. `0x80082504 == 0x11` confirmed the TRAINING
scene. Captures remained under `/tmp`.

## Source/stager/runtime comparison

The saved PNG is intact: it contains a dark purple, many-lobed blackberry and
green leaves on a nearly black background. It has no alpha channel. The bad
appearance is therefore not present in the authored asset.

`tools/training_board_edit.py` resizes the full image to 64x64 and quantizes it
to the board's native 4-bpp chalk palette. Its general-purpose profile classifies
resized pixels below luma 24 as board background index 12. That profile is safe
for the brighter grayscale signs, but the blackberry's body is intentionally
very dark. Before the fix it retained only 254 foreground pixels and classified
3842/4096 pixels as background. Most berry bodies vanished; isolated highlights
and the brighter leaf shape remained.

The pre-fix manifest-generated tile and the live VRAM decode at
`(336,0), 64x64, 4bpp, CLUT (784,229)` agreed visually. The live decode PNG
hashed to `c429f85d8ecd447c07e3c88552d9405a00ef29e57ed7fa4f83bf62565e8fdc23`;
the full frame hashed to
`c6b388b3a818892be825abcb5043611e07148549d7ba3bf4b75ea8251d839f27`.
This closes off decompression, tile selection, runtime upload, and ASM as causes.

## Rejected green-palette experiment

An intermediate A/B mapped chromatically green source pixels to indices 13-15,
which are green in the CLUT used by the extraction helper. The VRAM decode then
showed green leaves, but the actual subtractive/chalkboard presentation rendered
them nearly black. That experiment was rejected and is not in the final build.
The sign is intentionally a monochrome chalk rendition in game; fidelity here
means preserving the source silhouette and berry structure, not its RGB colours.

## Final result

Sign 2 now opts into luma cutoff 4 while all other signs retain the default 24.
The source scale and framing are unchanged. The final tile has 683 foreground
pixels and 3413 background pixels; its packed 2048-byte SHA-256 is
`522d9e2892ad467523be55fd3eaf3fc03bc0fc9d1fa8cf46ca53dc5a8bc5dc81`.

Cold-boot movie playback shows a readable blackberry: connected dark berry
bodies, individual highlights, and the original leaf silhouette in the board's
blue-purple chalk treatment. Final transient hashes:

- live VRAM decode:
  `c4f6e93138ad0aae7f96e84f698f4b2a8745bdc895db7c382a1016be6dff90d5`;
- full emulator frame 5905:
  `a1c6e2d5e6486c1ce879c519765d21ddf52c4f3cb0b115a40840ea9adb0de00b`.

No screenshot, save state, RAM dump, token, or game asset was added to the
repository.
