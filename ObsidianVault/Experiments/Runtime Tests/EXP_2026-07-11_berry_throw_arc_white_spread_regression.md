---
kind: experiment
id: EXP_2026_07_11_berry_throw_arc_white_spread_regression
status: confirmed
confidence: confirmed
date: 2026-07-11
systems:
  - SYS_berry_projectile_and_homing
mods:
  - MOD_blackberry_net_new_berry
  - MOD_training_six_level_purple_seed_ladder
---

# Berry throw arc and White spread regression

## Question

Why did Flik's berry launch downward or disappear in ALLMODS, and can Black keep
2x velocity/4x gravity while White regains the prior spread without restoring the
active-counter underflow?

## Environment and identity

- Repository HEAD: `0aa0fac392bb3bd781c502b71e42346cb0a2738b` (dirty operator WIP preserved).
- DuckStation fork: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, dirty external-debugger tree.
- Launched binary SHA-256: `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.
- Final disc: `build/ABL_ALLMODS.cue`, serial `SCUS-94288`.
- Final BIN SHA-256 after the renderer live-register fix:
  `fea978e542c7b7d3867bb73752ddd1ce857b08e399d2828559de49037d3fc835`.
- CUE SHA-256: `07d1c83c0b87ab7f14b0c9e6dc988ab8f70fda58de76fe1b4cdc7f9e1f37bf8e`.
- All behavioral runs used fresh absolute config directories, dedicated loopback
  ports/tokens, from-boot v3 movies, verified media identity, and PID-scoped cleanup.

## Observation before patch

At the resolved contact spawner hook `0x8005A0F0`, ALLMODS Training's native-red
throw arrived with `t1=5`, `t3=128` at movie frame 4837. A forced Blackberry run
in LEVEL01 repeated the same `t1=5` input; the existing speed cave correctly made
it `t1=10`, `t3=512`. The mod was therefore multiplying a degenerate downward
input, not failing to apply its 2x/4x arithmetic.

A pristine cold boot with a manual no-target Square press reached the same spawner
with the stock ballistic values `t1=-2048`, `t3=128`. The solved helper at
`0x80046D24` also uses `-2048` when no target is selected.

The old Whiteberry EXE contained the intended three-way geometry but also patched
the throw gate to clear `0x800A6596`. That byte is native live-projectile ownership;
later retirement can decrement the cleared byte to `255`, explaining disappearing
shots and permanent Square rejection.

## Inference

The causal chain was:

1. a near-zero/downward target-helper result reached straight-berry dispatch;
2. Blackberry faithfully doubled that malformed velocity and quadrupled gravity;
3. the older White prototype compounded lifetime bugs by resetting the native count.

The resolved source ASM itself did not need editing. A MOD-only dispatch hook can
restore the known stock launch, and a post-primary wrapper can recreate White's two
side records while adding exactly two owners.

## Patch

- `CAVE_THROW` now writes the stock straight launch `t0=-2048` before native
  dispatch. Homing/mega still pass through their native downstream setup.
- Blackberry alone raises `NEWBERRY_FLAG`; the existing spawner hook produces
  `vel_y=-4096` and gravity `512` along with 2x X/Z velocity.
- `0x8004724C` now jumps to a wrapper in `0x800812B8..0x80081320`. It calls the
  native primary spawner, then for effective White index 6 creates:
  - left: `vx-vz/4`, `vz+vx/4`;
  - right: `vx+vz/4`, `vz-vx/4`.
- White adds `2` to `player+0x96`; the primary's native increment remains intact
  and all three records retain native retirement.
- Terrain/contact color hooks now share an `ra`-preserving cave. The original ASM
  under `asm/hand_written/` remains untouched.
- No code or data was placed in audio/DMA candidate `0x80080E94..0x80080EAC` or
  FMV work buffer `0x800814BC..0x80081530`.

## Causal confirmation

`tools/scenarios/duckstation/blackberry_ballistic_speed.yaml` cold-booted LEVEL01,
forced effective index 5, and halted after the speed transform:

- `t1 = 0xFFFFF000` (`-4096`);
- `t3 = 512`;
- one-shot flag consumed to `0`;
- native selector remained red `0`.

Report: `/tmp/abl-blackberry-ballistic-scenario/blackberry_ballistic_speed.json`,
SHA-256 `5457ece60e7156d971b74561165a84acacdbb2ece41309a96054e2e8b3dde829`.

`tools/scenarios/duckstation/whiteberry_spread_balanced.yaml` cold-booted LEVEL01,
forced effective index 6, and reached both side-spawn call sites twice by movie
frame 5400. Active count was `6`, not `255`; after throw input stopped and 1000
frames elapsed, all spread records retired and the count returned to `0`.

Report: `/tmp/abl-whiteberry-spread-scenario/whiteberry_spread_balanced.json`,
SHA-256 `64473872f358205e22519693a6610369bfa10c58739720f6604fb3eb5061f8bd`.

Controls:

- native red: `PASSED`, report SHA-256
  `c6e179fe875f69f2d3526b5903dc91575e99798137c862e3f96efa0f4623e86f`;
- Training six visible tokens: `PASSED`, report SHA-256
  `124ba82d3e19b46a7c4ae3461d6a4dcd699fc501e648337f0985a2f73299df9b`;
- SPU/audio regression: `PASSED`, 350 untruncated events, all voices ended,
  hazard words pristine; report SHA-256
  `1dcd66d43abd9b2f48d7df2f8681e6aebc4bb15ea165d29429e84d9760b990a1`.
- Safe suite: `159 passed, 7 deselected`.
- Hook/cave validator: `1195` changed code-module bytes, all within `44`
  declared ranges.

Post-validation renderer addendum: the first combined color implementation
clobbered live emitter registers `t8/t9`. See
`EXP_2026_07_11_custom_color_renderer_live_register_regression` for the resolved
ASM proof, pre/post cold-boot captures, and corrected final hashes.

## Remaining operator validation

The actual six-tier seed growth/collection path still needs the requested hardware-
equivalent operator test. The scenarios causally validate the resolved throw modes,
projectile ownership, Training token presence, native red control, and audio safety.
