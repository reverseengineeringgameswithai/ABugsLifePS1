---
kind: mod
id: MOD_training_pause_n_suppression
name: TRAINING pause N-cell suppression
status: composed_into_allmods_cold_boot_verified
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod
canon_dependencies:
  - Menu_and_HUD_structure
  - SYS_pickup_letter_spin_strips
src_paths:
  - tools/training_word_pickups.py
  - tests/test_training_word_pickups.py
evidence:
  - EXP_2026_07_11_training_pause_n_double_buffer_flash
---

# TRAINING pause N-cell suppression

## Change

`tools/training_word_pickups.py` keeps its RAW-resident helper at unused animation
table slot `0x35`, called only by the already scene-gated Training animation pump.
On ordinary Training ticks it only repairs the extra N/G descriptor CLUTs. When
START bit `0x0008` is latched at `0x80082488`, it additionally calls original
`ClearImage` (`0x80062790`) on:

`RECT {x=682, y=72, w=6, h=24}`

That rectangle is exactly extra tile `0x26`/N's 24x24 4bpp cell: page X 640 plus
`U168/4`, with six 16-bit VRAM words per row. RGB zero makes the N quad
transparent while the pause shell replays its two different stored phases.

The original Training uploader remains unchanged. On resume it uploads the next N
frame into the cell immediately, so normal in-world spinning returns without a
special restore hook.

## Regression boundary

- Scene `0x11` only; non-Training takes the native replay branch before loading
  slot `0x35`.
- START-input tick only; ordinary Training gameplay does not clear the cell.
- Only N's 6x24-word cell is cleared. Framebuffers, render contexts, pause input,
  native F/L/I/K tiles, G, HUD textures, and menu code are untouched.
- The existing RAW relocation and R3000 load-delay safeguards remain in place.
- No compiled MOD C cave owns this path; it is generated MIPS in the Python asset
  stager. Original-side behavior is documented separately in
  `src_re/world_render_dispatch.c` and the resolved ASM.

## Verification

- Focused suite: `pytest -q tests/test_training_word_pickups.py` -> `3 passed`.
- Rebuilt BIN SHA-256:
  `004d35550c9211375e1795452d880b89f33275fbc46522b0a8056cde2c00ce4b`.
- Cold-boot movie `ALLMODS_Training_Still.movie.json` reached scene `0x11` around
  frame 5905 with the disc-loaded slot-`0x35` blob calling `ClearImage`.
- N cell before pause: 160 nonzero bytes. During pause: 0/288 nonzero bytes.
- 128 verified one-frame advances: zero gold pixels in the N bounding box, one
  exact crop hash
  (`65b4d0d5b02ef7fb5e636ca75457f03f46400c0794e7ebdcd6c3492410e96ac6`),
  while the full screen produced 32 hashes—menu/presentation continued running.
- Pause capture SHA-256:
  `7e880329cbb6b7725a679046eea57c42223ff521a51c04a693dfaa4921762a2b`.
- START resumed gameplay; pause flag returned to zero and N restored to 141
  nonzero bytes. A second later pause alignment again produced zero N-region gold
  pixels for 64 frames.
- Consolidated BOOT/ALIVE/RENDER/WALK smoke gate: PASS; report SHA-256
  `7fc96a988e64da3ff7d269de936ba0403837e5527be3932e2f2474ffa479f864`.

Cause and corrected evidence:
[[EXP_2026-07-11_training_pause_n_double_buffer_flash]]. Superseded approach:
[[MOD_training_pause_framebuffer_sync]].
