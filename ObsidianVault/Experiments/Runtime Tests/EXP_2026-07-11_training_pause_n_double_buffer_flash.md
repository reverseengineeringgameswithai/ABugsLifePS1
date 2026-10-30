---
kind: experiment
id: EXP_2026_07_11_training_pause_n_double_buffer_flash
name: TRAINING pause N double-buffer flash
status: corrected_retest_confirmed
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: original_game_boundary_with_mod_ab
systems:
  - Menu_and_HUD_structure
  - SYS_pickup_letter_spin_strips
evidence:
  - asm/hand_written/80039a70_frame_present.s
  - asm/hand_written/80052574_hud_anim_driver.s
  - asm/hand_written/80062790_ClearImage.s
  - asm/hand_written/80062988_MoveImage.s
  - movies/ALLMODS_Training_Still.movie.json
  - src_re/world_render_dispatch.c
---

# TRAINING pause N double-buffer flash

## Question

Why does the gold `N` in the in-world TRAINING pickup word flash behind the
START menu, and is the letter still being animated or drawn while paused?

## Reproduction identity

- Project revision: `e6402e8717f56df37b47405f6423aad0882ed502` with existing
  operator WIP preserved.
- DuckStation fork revision:
  `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, dirty external-debugger tree.
- Debugger binary: `~/duckstation/build/bin/duckstation-qt`, SHA-256
  `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
- Corrected isolated config `/tmp/duckstation-debugger-training-n-flash-regression`, port `23987`,
  localhost WebSocket transport, dedicated local token.
- Cold-boot input movie `movies/ALLMODS_Training_Still.movie.json`, version 3,
  6994 frames, SHA-256
  `5cff3e9e28af7964cec0c3b5190cca70b960ad3c0cff2bd1f5c741579def0c3c`.
- Pre-fix ALLMODS BIN SHA-256:
  `2731aa2fd452d28836dc932620191ce145ba5674ba03decb43b5475b4cd2d94d`.

The corrected run cold-booted the movie to the screenshot range around frame 5900. Runtime scene
`0x80082504` was `0x11` (Training). START was injected for two frames.

## Observations

1. The pause menu alternates CRTC sources `(0,264)` and `(512,264)` and their
   resident render contexts every two emulator frames.
2. The HUD animation driver (`0x80052574`) and Training cave (`0x800813F0`) record
   zero hits while the game's pause flag `0x8008224E` is 1.
3. Contrary to the first pass, original `frame_present` (`0x80039A70`),
   `DrawOTag` (`0x80062BFC`), and DMA kick `0x80064618` do execute in pause. At
   frame 6246 the background and scene heads were `0x801CC3AC` and `0x801CD870`.
   The next context supplies their `0x801E...` partners.
4. `gpu.pickObject` on the visible N identified a GP0(2D) quad using golden CLUT
   `(880,217)`, 4bpp page `(640,0)`, and UV `(168,72)..(191,95)`—exactly extra
   tile `0x26`'s 24x24 cell. One captured source packet was `0x001CD878`.
5. Therefore pause is not advancing the N uploader; it is replaying two already
   built scene OTs that retained different N phases.

## Verification correction

The earlier “byte-identical paused frames” result was invalid. Its capture loop
used the unsupported CLI command `advance-frame` under `--quiet`; the emulator
frame counter did not advance. Re-running with the documented
`advance-frames --frames 1` reproduced the flash continuously and showed the two
OT paths above. The one-time `MoveImage` prototype is superseded because the next
OT replay reintroduces its stored phase.

Two post-present framebuffer-copy prototypes were also rejected: inserting
`MoveImage` around the original GPU synchronization path stalled guest progress.
They were debugger-only RAM experiments and were never added to the build.

## Causal replacement A/B

On the final Training tick where input latch `0x80082488` contains START bit
`0x0008`, clear only N's 4bpp VRAM cell:
`RECT {x=682,y=72,w=6,h=24}`. `x=682` is page 640 plus `U168/4`; six 16-bit VRAM
words cover 24 four-bit texels. Original `ClearImage` (`0x80062790`) with RGB zero
makes the replayed N quad transparent. The regular Training uploader restores the
cell on the first gameplay tick after resume.

Live prototype and rebuilt-disc results agreed:

- before pause the N cell contained 160 nonzero bytes;
- during pause all 288 bytes were zero;
- across 128 correctly advanced pause frames, the N bounding box had zero gold
  pixels and one exact RGBA crop hash, while the full screen had 32 hashes (the
  menu/presentation loop was not frozen);
- START resumed gameplay, pause flag returned to zero, and the cell restored to
  141 nonzero bytes (SHA-256
  `66d3f57607d2fa8a1e4c3341125c1c68a102fc8eb8cee75331abe81bef2410ac`);
- a second later pause alignment again had zero gold pixels across 64 frames.

## Conclusion

The `N` uploader is stopped during pause, but the original shell keeps replaying
two scene OTs containing different N phases. The narrow stable mitigation is to
make only N's texture cell transparent for the pause interval, not to interfere
with framebuffer presentation. Current implementation:
[[MOD_training_pause_n_suppression]]. Superseded one-time copy history:
[[MOD_training_pause_framebuffer_sync]].

No screenshots, game assets, RAM dumps, disc images, or credentials are stored
in the vault; capture paths above are transient evidence only.
