---
kind: experiment
id: EXP_2026_07_10_bigland_oddities_hard_replacement
name: Bigland oddities — marker tint and residual native terrain hard replacement
status: confirmed_with_collision_scope_limit
created: 2026-07-10
updated: 2026-07-10
confidence: confirmed
source_state: re
related:
  - MOD_g3_native_anchor_alignment
  - SYS_render_collision_source_separation
---

# Bigland oddities — marker tint and residual native terrain hard replacement

## Question and fixtures

The operator supplied two states recorded against `build/ABL_ALLMODS.cue`:

- `bigland_oddity_1.sav`, SHA-256
  `4956e562f65aa89e3a9a32d84d8c14c631e2f261504a5b2bcce4be5ab128a7b4`;
- `bigland_oddity_2.sav`, SHA-256
  `e92f7ee96187e66e1385fa2ff9eeab42e01e8e35a8ebc089edea2e9ec23878a1`.

Both identify `SCUS-94288` and the composed ALLMODS media. Oddity 1 showed a
cyan/green floor patch. Oddity 2 showed large original LEVEL01 mounds, walls, and
detached strips over the authored pebble field even though those shapes were not
walkable.

## Cause

### Oddity 1

The source profile intentionally gave the P11 marker a native-floor tint with
color `0xf0d040`. `style_marker_floor_tint` applied that color to the overlapping
floor primitive; PS1 modulation rendered it cyan/green. This was authored MOD
metadata, not random VRAM state or a GTE/collision fault.

### Oddity 2

GPU picks on the original save identified the visible mound packets as native
`GP0(3c)` textured quads with varied stock colors/UVs. Source inspection then
matched them to the twelve node-registered native payloads outside the canonical
floor set. The P63 command deliberately used `P57_FLOORS_ONLY=1`, so
`regenerate_floor(... all_nodes=False)` rebuilt thirty floor payloads and retained
those twelve wall/cliff/dirt-band payloads unchanged. Their collision was already
absent or unreachable; this was a visual-source residual.

## Causal A/B and baked result

The P64 candidate changed only the relevant variables:

1. omit marker floor styling while retaining the marker AABB/flag;
2. collapse every vertex of each non-floor terrain payload to the payload's first
   vertex, preserving payload size, relocation, and node-table structure;
3. sink outside-region and undecodable chunk-32 collision records to runtime Y
   above 60,000 (build sink value `800000`).

A live DAT-range A/B first verified causality. Oddity 1's colored patch disappeared;
oddity 2's mounds, walls, and detached strips disappeared. This live mutation was
used only as bounded visual evidence: the oddity-2 instance later reached PC
`0x00001000`, consistent with rewriting active terrain/cache data in place.

The assets were then baked and composed from a fresh disc:

- terrain DAT SHA-256 `47c6b507fd1e41f97de7f977bad4eebcdafae5cc9c67e12226df26052ec09b5d`;
- collision RAW SHA-256 `a406a72d21b1ae6a8c1cd2b3597d4a4cfc743a0be47c8bc5bb9ec3dea8de0d79`;
- `build/ABL_ALLMODS.bin` SHA-256
  `dd78c90e5a2ae5d9dc945a9dabca2ea667c1662a6fc91c5491a97f94cd1eab42`.

Fresh boot with `flik_to_level01_stall.mv.movie.json` passed BOOT, ALIVE, RENDER,
and WALK. The player reached X `197088`; the 64-frame movement sample covered
`139734` runtime XZ units with Y `-12923..-12732`. The smoke frame SHA-256 is
`c2b2d82bb4b3c6729433187c7749fed535535bd13a01d0930d4ad3b7ddd52bea`.

Bounded cold-boot coordinate warps produced:

- `build/ABL_ALLMODS_oddity_1_fixed_coldboot.png`, SHA-256
  `17f422d763d5032c8831a8edde850fad73d12a37e26a232a9d71242234371232`:
  coherent pebbles, no marker tint;
- `build/ABL_ALLMODS_oddity_2_fixed_coldboot.png`, SHA-256
  `7487f379c21331a02b3ab7749ea0ff60d44683c504442305b7df4f2eb74fd36e`:
  no stock mounds/walls/detached strips.

The oddity-2 raw teleport remained healthy at PC `0x8004fea4` after 23 frames but
eventually destabilized after 128 frames. That is not used as a disc-stability
claim because a coordinate poke bypasses normal spatial/cache traversal. The real
cold-boot movement smoke above is the stability gate.

## GPU check of the exposed tan band

The tan band visible after removing the old mound is not another hidden stock mesh.
At frame 4408, `gpu.pickObject` at native pixel `(160,178)` selected the same neutral
authored `GP0(3c)` floor style (`0x808080`, CLUT `0x3ffc`) drawn over the ordinary
`GP0(60)` background fill. Adjacent pebble pixels resolve to the same authored
floor family. It is therefore a low-detail part of the authored floor/background
composition, not the twelve removed terrain payloads.

## Collision scope

The corrected chunk-32 offline report is
`build/g3_native_p64_hardreplace_collision_coverage.json` (SHA-256
`c4c4ce367fe9b95c5bbd4bc865474255a5c61e3e813e505a89fb9722d910eda2`):

- 85 authored blocks added on pristine-flat sectors;
- 86 old blocks replaced with authored blocks;
- 7 outside-region records sunk;
- 11 undecodable relocation-region records sunk;
- zero active old/unclean decoded floor footprints;
- 13,853/15,617 sample nodes covered by decoded authored planes (88.7%).

Conclusion: P64 removes the two reported visual oddities and disables or replaces
stock chunk-32 collision. It does **not** yet prove an arbitrary complete collision
world: 1,764 sampled nodes remain uncovered, and chunk 33/non-floor runtime collision
sources are outside this audit. Keep that remaining collision work in RE/Experiments;
the shipped hard-replacement switches and assets belong in MOD notes.

## Debugger identity and cleanup

- DuckStation fork `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`;
- debugger binary SHA-256
  `08a4720d1afc40f31f6961d3bd21625b17a49463a9c3d18336144e0acc856eab`;
- project HEAD `e6402e8717f56df37b47405f6423aad0882ed502`;
- isolated configs `/tmp/dsrepro-oddities-p64` and
  `/tmp/dsrepro-oddity2-pick`, ports `23466`, token `debugger-1000`;
- all owned instances stopped; controller state, movie playback, and turbo cleared.
