---
kind: mod
id: MOD_allmods_slowwalk_animation_restore
name: ALLMODS slow-walk animation restoration
status: composed_into_allmods_smoke_verified
created: 2026-07-10
updated: 2026-07-10
confidence: confirmed
source_state: mod
canon_dependencies:
  - Gameplay_-_Input_and_Movement
  - FUNC_80048138
  - MEM_8012C1D0
src_paths:
  - tools/g3_bigland_stager.py
  - tools/build_g3_native.py
  - tools/regress_g3_native_authoring.py
  - mod/caves/tier3_collision.c
  - src_re/player_update_80048138.c
evidence:
  - EXP_2026_07_10_allmods_slowwalk_animation_regression
---

# ALLMODS slow-walk animation restoration

## Change

Bigland no longer enables the historical P54 `suppress_bulk_mesh` runtime
clear. The builder retains that option only as an explicitly unsafe negative
differential. Shipping terrain hard replacement continues to use named,
size-preserving DAT/RAW edits.

No original input, locomotion, or animation-selection instruction was patched.
The solved assembly already implements the correct L2/R2 behavior, and the bad
build reached animation 29 with a progressing phase. This MOD restores the
memory-lifetime contract required by the original renderer.

## Guard

`test_shipping_bigland_preserves_player_animation_workspace` verifies:

- safe runtime bytes omit the historical `0x8012C1D0` clear-loop signature;
- an explicit unsafe differential still contains it for reproducibility;
- the shipping stager cannot silently re-enable `suppress_bulk_mesh=True`.

The C-side Tier-3 collision commentary records the same ownership rule: custom
collision may write only its named buffers, and terrain suppression must not
blanket-clear unowned post-load RAM.

## Output

- test cue: `build/ABL_ALLMODS.cue`;
- BIN SHA-256:
  `1c49482fc496549134aa82804ce6ffe2fac59513745a1a1b0fe473a409e7a113`;
- runtime report SHA-256:
  `6dd3db925740b6032448a2d7693ef1ed00e2807c83330bee46a2edd951a0607d`;
- overlay runtime: `0x800B4030..0x800B4320`, 752 bytes;
- cold-boot BOOT/ALIVE/RENDER/WALK smoke: pass.

Cold-boot the cue when testing. A save state recorded against the old image can
restore the already-cleared RAM and conceal the fix.
