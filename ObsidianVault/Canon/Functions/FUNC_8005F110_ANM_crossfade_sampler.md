---
kind: function
id: FUNC_8005F110
aliases: [FUNC_8005F110, 0x8005F110]
address: '0x8005F110'
name: anm_animation_crossfade_keyframe_core
status: static_reversed
confidence: high
source_state: original_game
evidence:
  - analysis/naming/u5_anm_crossfade.json
patch_policy: safe_to_read
---

# FUNC_8005F110 - ANM crossfade sampler

`0x8005F110..0x8005F4EC` blends two animation sub-blocks into the runtime
bone-transform array at `0x80089F58` (84-byte records). It is the two-source
counterpart to the single-animation sampler at `0x8005EC94`.

For both inputs it derives the dense frame pointer using the decoded ANM
grammar:

`subblock + 0x0c + 2*n8 + n10 + 2*frame*n6`

The signed `s16` mapping lists begin at sub-block `+0x0c`; `-1`, `-2`, and
`-3` are control sentinels. For an active mapping, lanes `0/2/4` are linearly
interpolated into translation words at destination `+0/+4/+8`. Lanes
`6/8/10` are angles on a 4096-unit circle: the function wraps each delta to
`[-2048, 2048]` before interpolation and stores them at `+0x10/+0x12/+0x14`.

A per-mapping bit in the `n10` metadata region gates lanes `12/14/16`. When
present they are blended into destination `+0x18/+0x1a/+0x1c` and flag
`+0x1e` is set; otherwise that flag is cleared. This types the nine-value
transform tuple consumed by the runtime while leaving the artistic meaning of
the optional triplet open.
