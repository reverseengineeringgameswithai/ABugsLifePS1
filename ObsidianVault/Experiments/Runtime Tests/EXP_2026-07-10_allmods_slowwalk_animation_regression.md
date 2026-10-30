---
kind: experiment
id: EXP_2026_07_10_allmods_slowwalk_animation_regression
name: ALLMODS L2/R2 slow-walk animation regression
status: confirmed_fixed
created: 2026-07-10
updated: 2026-07-10
confidence: confirmed
source_state: mixed_original_and_mod_experiment
related:
  - Gameplay_-_Input_and_Movement
  - FUNC_80048138
  - MEM_8012C1D0
  - MOD_allmods_slowwalk_animation_restore
  - PLAYBOOK_mod_regression_troubleshooting
---

# ALLMODS L2/R2 slow-walk animation regression

## Question

In ALLMODS, holding L2 or R2 while walking correctly reduced Flik's movement
speed, but his visible animation appeared static. Was the original slow-walk
logic patched incorrectly, or did a later MOD operation damage its render data?

## Original-game contract from solved assembly

- `asm/hand_written/80048138_player_vertical_update.s`, label
  `.L_80048488`: read `0x80082488`, mask `0x0300`, set `s5=768`.
- `asm/nonmatchings/resident/800563d4.s`, `0x800566CC`: read the same word,
  mask `0x0300`, select animation `0x1D` (29); otherwise select walk `0`.
- OG and ALLMODS embedded EXE bytes are identical at both functions and around
  the player animation descriptor table. This excludes an input/state-machine
  code patch as the cause.

## Reproduction

Cold-boot OG and ALLMODS used the same from-boot fixture
`flik_to_level01_stall.mv.movie.json` (SHA-256
`fa2e81925fbad56af07081fbfe6980f2789a0dd72e6b63b13f9e7b5fc23ed264`).
Fixed 60-frame input cases began from equivalent gameplay anchors.

| Case | OG movement | bad ALLMODS movement | Working buttons | Animation result |
|---|---:|---:|---|---|
| Up | 49,918 | 51,048 | `0x0010` | `22 -> 0` |
| Up+L2 | 30,200 | 30,398 | `0x0110` | `22 -> 29`, phase advances |
| Up+R2 | 30,200 | 30,398 | `0x0210` | `22 -> 29`, phase advances |

Analog Up+L2 and a separate Training-level run produced the same original
state-machine result. The regression was therefore downstream of input decode,
movement throttling, animation selection, and phase advancement.

## Causal differential

Bigland's former P54 runtime enabled `suppress_bulk_mesh=True`, which zeroed
`0x8012C1D0..0x8012E784` once after load:

- OG range: 8,100 nonzero bytes; SHA-256
  `f0351ab725430d45a835d024315a81a42bbc976248357242f2836a96efa820a9`;
- bad ALLMODS range: 0 nonzero bytes; SHA-256
  `cb09ff889f39b098eb801120abcd333af443f6c5852cda8170d25f06a1985cd0`;
- an OG pointer census found 30 pointers into the range, confirming shared live
  ownership, but not proving that every pointer is an animation descriptor.

Removing only that clear produced a fixed build whose Up+L2 movement remained
30,398, buttons remained `0x0110`, animation remained `22 -> 29`, and phase had
the same 31-value progression. The preserved range contained 7,321 nonzero
bytes. At matched frames, bad and fixed screenshots had identical backgrounds;
the only changed pixels bounded Flik. Frame 5 was byte-identical before the pose
transition, while frames 10–40 differed only around the character.

Bounded conclusion: the blanket clear destroyed data needed for Flik's rendered
pose. The precise mixed layout/lifetime of this shared workspace remains partly
unreversed; no stronger ownership claim is required for the fix.

## Fix and regression guard

- Shipping Bigland now passes `suppress_bulk_mesh=False`.
- The unsafe CLI option remains only for historical differential reproduction
  and emits an explicit warning.
- Stock terrain removal remains the P64 size-preserving DAT non-floor payload
  collapse plus RAW collision sinking; no shared-RAM terrain clear is used.
- `tools/regress_g3_native_authoring.py` checks the destructive
  `li t6,0x8012C1D0` signature is absent from the safe runtime and shipping stager.

Rebuilt `build/ABL_ALLMODS.bin` SHA-256:
`1c49482fc496549134aa82804ce6ffe2fac59513745a1a1b0fe473a409e7a113`.
The cold-boot BOOT/ALIVE/RENDER/WALK smoke gate passed. A bounded cold-boot warp
to the oddity-2 coordinates still showed no original mounds, walls, or detached
strips, so preserving the workspace did not undo P64 hard replacement.

## Reproducibility and cleanup

- DuckStation fork `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`;
- debugger binary SHA-256
  `08a4720d1afc40f31f6961d3bd21625b17a49463a9c3d18336144e0acc856eab`;
- project HEAD `e6402e8717f56df37b47405f6423aad0882ed502`, dirty operator worktree preserved;
- all owned isolated instances stopped; the operator instance was not touched.
