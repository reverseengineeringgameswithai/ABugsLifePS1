---
kind: experiment
id: EXP_2026_07_11_custom_color_renderer_live_register_regression
status: confirmed
confidence: confirmed
date: 2026-07-11
systems:
  - SYS_berry_projectile_and_homing
  - SYS_render_collision_source_separation
mods:
  - MOD_blackberry_net_new_berry
---

# Custom-color renderer live-register regression

## Trigger

Operator testing of the post-spread ALLMODS disc showed missing floors, transparent
walls, blue holes through world geometry, and no visible thrown berries. The supplied
screenshot was inspected from `/tmp/codex-clipboard-jGjZAT.png`.

## Identity

- Repository HEAD: `0aa0fac392bb3bd781c502b71e42346cb0a2738b` (dirty WIP preserved).
- DuckStation fork: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`.
- Launched binary SHA-256:
  `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.
- Media serial/title: `SCUS-94288`, Disney-Pixar A Bug's Life.
- Reproduction: cold-boot v3 LEVEL01 movie, effective Whiteberry index 6 written
  at movie frame 5000, execute breakpoint at post-emitter `0x80014A78`.

## Observation

The combined color hook used `t8` as its terrain/contact selector and `t9` as its
color-table pointer.

Resolved ASM proves both are live across the hook sites:

- terrain emitter resumes at `0x800105F8`, stores `t8` into packet `+0x2c` at
  `0x80010604`, and dereferences `t9` at `0x8001060C`;
- contact emitter resumes at `0x80014A78`, writes through the current record
  iterator `t8` at `0x80014A90`, decrements loop count `t9` at `0x80014A94`, and
  advances `t8 += 0x38` in the branch delay at `0x80014A9C`.

Cold-boot pre-fix capture at the first emitted contact packet observed:

- `PC=0x80014A78`;
- `t8=1` instead of a contact-record address;
- `t9=0x80080000` instead of the bounded loop count.

Report: `/tmp/abl-contact-renderer-pre-fix-4/contact_renderer_iterator_preserved.json`,
SHA-256 `ad77acb75adfe1fbc2c456bb8f9c457df0a3f19dcef8f44499000dc378c8b596`.

## Inference

The color itself was not responsible. Returning with the renderer's iterator and
loop state replaced caused subsequent terrain/contact packets to be written from
invalid state, directly explaining both missing geometry and invisible projectiles.

## Patch

`CAVE_THROW_COLOR` no longer writes `t8` or `t9`.

- Each hook keeps its original second instruction in the jump delay slot.
- The common cave identifies the path from `s7`: terrain's exact hook uses positive
  scratchpad `0x1F800000`; the contact hook uses a negative KSEG RAM packet pointer.
- `a3` is used only as temporary table addressing. It is dead after both exact hook
  sites: the terrain loop defines it again at `0x80010504` before its next use, and
  the contact tail never reads it again.
- The original files under `asm/hand_written/` remain untouched.

## Causal confirmation

The same cold-boot scenario now passes at the first emitted contact packet:

- `t8=0x800B1098` (inside the 64-slot contact array);
- `t9=48` (sane remaining loop count).

It then stops on an emitted Whiteberry packet and confirms:

- `v1=0x2CFFFFFF`;
- `t8` remains inside `0x800B0D18..0x800B1B17`;
- `t9` remains within `1..64`.

Scenario: `tools/scenarios/duckstation/contact_renderer_iterator_preserved.yaml`.
Post-fix report SHA-256:
`a893816d86d33e5d93ade955c6042f8d92cdf55376b5b9cd476ec39a50f46411`.

A frame captured during the White spread window visibly contains the wall and
textured floor packets and was stored transiently at
`/tmp/abl-ps1-scenario-qsh1n8l8/evidence/whiteberry_spread_frame.png`, SHA-256
`2613a423f637e6fa9fbd6965703272d1fcdb568419ac148caf2596745d76c8f5`.

## Regression controls

- White side spawns and `active_count 6 -> 0`: passed,
  report SHA-256 `f575c34dab5c8e1d17173871fe629d675feab48adb2e31db923298c42a08ea28`.
- Blackberry `vy=-4096`, gravity `512`: passed,
  report SHA-256 `a4f295d3b78cc081196724361061364796125f76c5b413a0ccf1c29faf3d2815`.
- Native red: passed,
  report SHA-256 `0fd60afbecbf2fba922d086bd32bf1c11d73c05ea5d8820c50ff4f24d4aceee0`.
- SPU/audio control: passed,
  report SHA-256 `78610cdd83772f6e629f9406f4e5409e0adebc045967bce7641f5ba5d49fa4bd`.
- Six visible Training tokens: passed,
  report SHA-256 `50d6ffd2a0c66fd12c1dd1ee656766354a1e4ed26f9547ec847037bb3878098d`.

Final disc BIN SHA-256:
`fea978e542c7b7d3867bb73752ddd1ce857b08e399d2828559de49037d3fc835`.

