---
kind: experiment
id: EXP_2026_07_11_training_auto_advance_counter_flash
name: TRAINING auto-advance cached objective counter flash
status: confirmed_fixed
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mixed_original_and_mod_experiment
related:
  - Training_NPC_progression
  - Training_board_sign_images
  - MOD_training_auto_advance_counter_flash_fix
---

# TRAINING auto-advance cached objective counter flash

## Question

Why does the customized TRAINING instructor board briefly show retail objective
digits `6` and `3` even though manifest steps 0-2 are voice-driven rather than
count-driven?

## Reproduction identity

- Project revision at preflight: `e6402e8717f56df37b47405f6423aad0882ed502`
  with unrelated operator WIP preserved.
- Pre-fix `build/ABL_ALLMODS.bin` SHA-256:
  `370c873f28b3c716a6512a4927d5461946495bff930dedbda77175318e1beca9`.
- Movie: `movies/ALLMODS_Training_Still.movie.json`, v3 from-boot, 6994 frames,
  SHA-256 `5cff3e9e28af7964cec0c3b5190cca70b960ad3c0cff2bd1f5c741579def0c3c`.
- Media identity from `emulator.getMediaInfo`: `SCUS-94288`,
  `Disney-Pixar A Bug's Life`, mounted from the absolute ALLMODS cue path.
- DuckStation fork revision:
  `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` plus the recorded dirty debugger
  layer; binary SHA-256
  `08a4720d1afc40f31f6961d3bd21625b17a49463a9c3d18336144e0acc856eab`.
- Isolated config `/tmp/duckstation-debugger-training-counter-fix`, port `23983`,
  with a per-session localhost token that was not preserved; recreated for
  final-disc verification.

The replay was loaded with `movie.load`, started with
`movie.startPlayback {start_frame:0,load_start_state:true}`, and advanced with
`movie.advanceToFrame`. Captures were written only under `/tmp`.

## Observation

Pre-fix frames sampled every two frames over 5080-5180 show `6` on the newly
raised custom step-1 sign from frame 5132 through at least 5148; it is absent by
5156. Pre-fix frames sampled every four frames over 5820-6020 show `3` from 5900
through 5920; it is absent at 5924.

Representative transient frame hashes:

- `5132` with `6`:
  `2e061de4426a07b20d7cff7b9a1390337aff872980c5bd049d036dd539527706`;
- `5904` with `3`:
  `a7f4152746ff6810f9a8430fc2a5c7922067cbeb8c62fadbbd1b74975ae8eb49`.

Runtime disassembly bounded the cause:

- incoming step 1 at `0x800B4058` and step 2 at `0x800B40F0` both call
  `0x800B3B54(step, -1)`, which correctly requests no digit;
- the common advance tail at `0x800B47A8` still executes
  `addiu v0,zero,30`, then stores it to `0x800B4A50` at `0x800B47B0`;
- helper `0x800B3F00` calls `0x800B3B54` at the animation's artwork-swap
  boundary with retail default counts (`5` for steps 0-1, `2` for steps 2-3);
- the state machine does not enter the incoming handler while this shared timer
  is nonzero.

The digit is therefore not coming from the customized objective logic. It is the
next sign's cached retail digit becoming visible during the original 30-tick
inter-step hold, before the incoming MOD handler can replace it with the blank
variant.

## Superseded zero-wait A/B

A live code-cache-invalidated prototype changed `0x800B47A8` to call a 36-byte
selector shim at `0x800B4080`. The shim returned zero wait ticks for outgoing
steps 0 and 1 (mask `0x0003`) and 30 for every other outgoing step. No `6` was
visible in any sampled frame across 5080-5180, and no `3` was visible across
5820-5960.

The same patch was then generated through the normal manifest build and verified
from a new cold boot, without RAM writes. Runtime disassembly on that disc showed:

```text
0x800B47A8  jal   0x800B4080
0x800B47B0  sw    v0,0x4A50(at)
0x800B4088  addiu v1,zero,3
```

The rebuilt-disc capture sweeps again contained no objective numerals. Matching
blank frames `5132` and `5904` hash to
`dec4ddbcfe5947868fb5b610e54b988f0cd57c01a6e058258408d2f9b17a0efc`
and `edbd71acc275ee82158a485735333f3666c2ef84d359eab07e9c96b2d469dc9c`.

That build fixed the numeral symptom but introduced an animation regression:
because the incoming handler ran immediately, Sign B replaced Sign A while the
board was still lowering. Representative movie frame 5096 on that build hashes
to `0b828183cd470e50244369ac825efd40d06d23e475b2271e6e35fc04b68a7f6e`.
Its BIN SHA-256 was
`c74f1c7ffc5f58767a835b25e3e3f1a7c066520b0c7d50d91e724294fec27c37`;
both that implementation and image are superseded.

## Phase-correct A/B

The final prototype restored the unmodified 30-tick timer and instead hooked the
retail default-count logic at `0x800B3F18`. Its selector at `0x800B4080` receives
the incoming step in `a0`, returns `a1=-1` for manifest auto steps 1 and 2 (mask
`0x0006`), and reproduces retail `5/2/0` counts otherwise.

Bounded execution trace over emulator frames 5001-5201 recorded:

- frame 5084: `0x80045A60` began the step-0 transition;
- frame 5150: the original `0x800B3F00` path entered the selector with `a0=1`;
- the immediately following `0x800B3B54` call had `a0=1, a1=-1`.

Cold-boot frame sweeps on the rebuilt disc showed Sign A throughout the lowering
motion, Sign B only on the upward motion, and no objective numeral. The same
ordering and blank counter were confirmed for the step-1 -> step-2 transition.
Representative corrected frames hash as follows:

- frame 5096, Sign A still lowering:
  `d2be9f4086550dd3679aa28258cb4f8d6980ad5837d669ab9140bd10363913d0`;
- frame 5132, blank Sign B rising:
  `dec4ddbcfe5947868fb5b610e54b988f0cd57c01a6e058258408d2f9b17a0efc`;
- second transition frame 5848, Sign B retained while lowering:
  `05395432b882eaf53b493c7ad3d21cda52cdf98c65d05b385bdbda7b241b88f4`.

Final bounded conclusion: the timer is part of the correct animation cadence and
must remain. The correct patch changes only the count at the original
bottom-of-travel sign-selection call.

## Final output and cleanup

- Build command:
  `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`.
- Final BIN SHA-256:
  `e5459d17dfd59b6a70d77125c3ee8cb6a0e0b9fb40b5ff3472072410129f6401`.
- CUE SHA-256:
  `07d1c83c0b87ab7f14b0c9e6dc988ab8f70fda58de76fe1b4cdc7f9e1f37bf8e`.
- No movie, screenshot, save state, RAM dump, token, or game asset was added to
  the repository; evidence captures remained transient under `/tmp`.
