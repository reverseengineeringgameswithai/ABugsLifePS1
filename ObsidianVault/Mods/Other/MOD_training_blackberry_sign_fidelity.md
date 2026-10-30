---
kind: mod
id: MOD_training_blackberry_sign_fidelity
name: TRAINING blackberry sign fidelity profile
status: composed_into_allmods_cold_boot_verified
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod
canon_dependencies:
  - Training_board_sign_images
src_paths:
  - mod/mods.yaml
  - tools/training_board_edit.py
  - tools/training_tutorial_stager.py
  - tests/test_training_board_edit.py
evidence:
  - EXP_2026_07_11_training_blackberry_sign_fidelity
---

# TRAINING blackberry sign fidelity profile

## Change

The training sign converter now has a manifest-shaped
`image_to_tile_from_params` adapter. `training_tutorial_stager.py` uses it so an
individual sign can override quantizer settings without changing the safe
defaults for every other tutorial image.

The ALLMODS sign-2 entry supplies `bg_luma: 4`. The standard value remains 24
for signs 0-1 and 3-12. This retains the dark purple berry body from the saved
RGB image while keeping its black background mapped to board background index
12. The image is not cropped, recoloured, or replaced.

The board is a fixed-palette chalk surface, so the green source leaves are
expected to become blue-purple chalk. An attempted native-green-index profile
rendered those pixels nearly black and was deliberately discarded.

## Safety and regression coverage

- The override is local to manifest sign 2.
- Existing callers retain their old `bg_luma=24`, foreground index set 0-10,
  and background index 12.
- `tests/test_training_board_edit.py` proves a dark coloured foreground survives
  the opt-in low cutoff while the default profile still suppresses it, and
  proves default conversion still excludes indices 13-15.
- No guest C or ASM changed: the fault was entirely in the MOD asset conversion
  before compression and disc staging.

## Output

- Build command:
  `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`.
- BIN SHA-256:
  `2731aa2fd452d28836dc932620191ce145ba5674ba03decb43b5475b4cd2d94d`.
- CUE SHA-256:
  `07d1c83c0b87ab7f14b0c9e6dc988ab8f70fda58de76fe1b4cdc7f9e1f37bf8e`.
- Cold-boot verification and source-to-runtime evidence:
  [[EXP_2026-07-11_training_blackberry_sign_fidelity]].
