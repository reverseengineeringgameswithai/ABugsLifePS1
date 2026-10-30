---
kind: experiment
id: EXP_2026_07_10_blackberry_square_and_selector_regression
name: Blackberry square descriptor and native-selector regression
status: confirmed
date: 2026-07-10
confidence: confirmed
source_state: experiment
systems:
  - SYS_berry_pickup_render_descriptors
mods:
  - MOD_blackberry_net_new_berry
artifacts:
  - /tmp/blackberry-warp-bad.png
  - /tmp/blackberry-warp-grayscale.png
  - /tmp/blackberry-desc-6750.sav
---

# EXP_2026-07-10 Blackberry square and selector regression

## Question

Why does the ALLMODS Blackberry pickup render as an opaque square, and does comparison with the newly matched/decompiled original code expose other MOD regressions?

## Preflight and reproduction

- DuckStation fork: `~/duckstation`, revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` (dirty external-debugger worktree).
- DuckStation binary SHA-256: `08a4720d1afc40f31f6961d3bd21625b17a49463a9c3d18336144e0acc856eab`.
- Isolated config: `/tmp/duckstation-blackberry-square-20260710`; API port `23682`; separate token.
- Mounted image: `~/Downloads/ABL/build/ABL_ALLMODS.cue`; serial `SCUS-94288`.
- Starting ALLMODS BIN SHA-256: `b4e4cf73788f8a3d69b3f987471fa1f47df2e270585ddf8b6e7cec3ff50ad51b`.
- Input movie: `TRAINING_NPC_STAGES.movie.json`, SHA-256 `2b05a9758975a3dd983503a216e347b49a1b344ea9435954d2f325a29fe28f0d`, replayed from boot.
- Anchor: movie frame 6750 / emulator frame 6751, Training scene `0x11`, tutorial step 2. A transient save state was captured at `/tmp/blackberry-desc-6750.sav` only to make repeated A/B trials deterministic; it is not a repository artifact.

The live type-`0x3F` list was `0x8011F314`, count 67. Entry 66 at `0x8011F738` was the Blackberry: `(x,y,z)=(900,-50,148)`, kind `0x25`, active status `1`. A controlled player/camera warp reproduced the operator's exact square. Screenshot `/tmp/blackberry-warp-bad.png` SHA-256: `6a00fcef4ea4f4df7be79f85e607eddbe4e91a67a7c6c233538230af62663029`.

## Descriptor observations

The private live descriptor at `0x80081234` was:

`1d001f1f000000003f000000`

Its texture handle and CLUT were zero, and `U=0x3F`. `object_pointer_list[0x25]` at `0x80096C2C` correctly pointed to the private record, so the problem was descriptor content rather than pointer selection.

Native descriptors are zero-tailed on disc but loader-completed before use. A live native red descriptor was:

`1d001f1f0a00f03640000000`

This established texture handle `0x000A` and raspberry-cell `U=0x40`. The private pointer is installed later by the MOD's runtime repair, after the native fixup pass, so its zeros remain zeros.

Using the API texture decode and live descriptor perturbation:

- handle `0x000A`, red CLUT `0x36F0`, `U=0x40` removed the square and exposed the raspberry silhouette;
- handle `0x000A`, grayscale CLUT `0x3670`, `U=0x40` produced the intended dark purple/black Blackberry with transparent background.

The confirmed MOD descriptor is:

`1d001f1f0a00703640000000`

`gpu.pickObject` on the corrected sprite reported GP0 command `0x2C`, 4-bpp page `(640,0)`, CLUT `(768,217)` / raw `0x3670`, UV rectangle `U=64..95,V=0..31`, and modulation word `0x2C2B051A`. Screenshot `/tmp/blackberry-warp-grayscale.png` shows the corrected silhouette. The bad/fixed phase-matched frame diff localized to the pickup rectangle; the opaque square came from sampling CLUT `(0,0)`, whose palette index zero was not transparent.

## C/ASM comparison: second regression

The old MOD persisted custom equip index `5` in native global `0x800A6597` and remapped it only at damage reads `0x800590F0` and `0x80059358`. Expanded source coverage shows the byte is a native `0..4` column selector for five-wide table `0x80089938` in additional paths:

- mover initialization: `0x80049D14`, `0x80049D44`, `0x80049E3C`;
- proximity update: `0x8004B280`, `0x8004B4CC`, `0x8004B508`, `0x8004B5E0`;
- matched C `src/main/80057a94_spawn_drop_burst_effect.c`, read at `0x80057B18`;
- damage: `0x800590F0`, `0x80059358`.

Therefore index `5` aliases the first column of the next actor row and can cause subtle behavior, threshold, and flag regressions outside damage.

## Causal fixes

1. `mod/caves/blackberry.c` now owns the complete grayscale descriptor. The build extracts the dedicated section byte-exactly and rejects any value other than `1d001f1f0a00703640000000`.
2. The common berry-collection tail at `0x800542E4` now captures transient sentinel `5` into private MOD state, then normalizes `0x800A6597` to red `0` before returning.
3. Private bytes are `0x80081230` one-shot spawn flag, `0x80081231` persistent equipped flag, and `0x80081232` MOD-only effective index.
4. Throw/recolor/Training/gold-drop MOD consumers read private state. Gold-drop uses an equal-size build-time selection between Blackberry's effective mirror and the native selector, remaining correct when built alone without expanding its locked cave. The two damage-only selector caves were removed; original damage instructions were restored.
5. Native contact-object berry drops bypass the world-pickup tail, so exits `0x80058938` and `0x80058990` now clear Blackberry state and mirror the newly armed native index. This prevents a native dropped berry from retaining fast/recolored Blackberry behavior.

## Validation state

- Descriptor C section and consolidated EXE bytes match the confirmed 12-byte value.
- `tools/regress_custom_objects.py` passes.
- Both `python3 mod/build.py --mods mod/mods.yaml --no-disc --force` and the full disc build complete, including the Blackberry-gated Training assets and byte-for-byte embedded-file verification. After the separately documented throw-overlap correction, the final BIN SHA-256 is `8d53b890bc533f7d8b526c4b83a9916ed0916818e5d56326a46eb818d720ba23`; embedded EXE SHA-1 is `c850ca4e54dadeb9ca922a3fb5153ffd66d06df4`.
- A golddrop-only manifest build also completes, proving that the independent module no longer depends on Blackberry's mirror initialization.
- Cold boot of the rebuilt disc confirmed live descriptor `1d001f1f0a00703640000000` and `object_pointer_list[0x25] = 0x80081234`. The final render-cave revision produced `/tmp/blackberry-final-displayed.png` (SHA-256 `47006e405a9e61aaba12ef415860cb9a99b746d679d06c32e3bbfcc3540bda39`); `gpu.pickObject` reported CLUT `0x3670`, UV `64..95,0..31`, and color `0x2C2B051A`. Throw execution is validated separately in `EXP_2026_07_10_blackberry_throw_cave_overlap_crash`.
- Transient `/tmp` screenshots and save state remain uncommitted. The isolated debugger listener on port `23682` was stopped after validation.

## Separation rule

The native descriptor-loader ordering, five-column selector domain, and original consumer sites belong in Canon. Blackberry's private state layout, CLUT choice, hooks, and normalization policy belong in Mods. Runtime identities, perturbations, screenshots, and causal observations remain here in Experiments.
