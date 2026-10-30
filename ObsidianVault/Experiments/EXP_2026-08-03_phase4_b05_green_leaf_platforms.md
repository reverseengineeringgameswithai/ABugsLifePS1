# EXP 2026-08-03 - Phase 4 B05 green leaf platforms

## Question

Can Phase 4 row B05 be treated as a sufficiently substantiated Partial, and did the existing retained capsule leave any behaviorally important green-platform gap?

## Method

1. Validated the retained `A13__green_seed_levels` capsule before live replay.
2. Used `tools/phase4_b05_capsule.c` to decompress all 46 chunks, reconstruct all 2,714 frame boundaries, verify all 8,142 embedded RAM/VRAM/SPU-RAM hashes, and track green plant slots and player height.
3. Inspected pristine hand-written ASM for the spawner, plant walker, `0x8005CCE8` continuation, common `0x8005CD2C` loop, growth-contact reaction, and ordinary collision/Y-commit ownership.
4. Named the one missing runtime domain: the type-10 upper leaf was never occupied in the retained capsule.
5. Replayed the operator-recorded type-10 fixture under a fresh isolated DuckStation profile in pure Interpreter mode, with fast-forward and turbo disabled.
6. Captured the player block and plant pool at all 527 movie boundaries, then reduced the binary capture with `tools/phase4_b05_movie_reduce.c`.

This was a state-anchored runtime mechanic check, not a disc/code/asset modification, so cold boot was not required. No CPU instrumentation was armed for the geometry pass. The initial flight check used `debugger.resume` at normal speed; frame-boundary sampling followed only after that replay.

## Identity and preservation

- Repository revision: `873bba7c0cf8be24d4e28ed9551feefe84dfa222`
- DuckStation revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` with the external-debugger working tree dirty
- DuckStation binary SHA-256: `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`
- Config: `/tmp/duckstation-debugger-b05-tall-leaf`
- Port: `5685`
- Owned PID: `651648`, stopped through the isolated-instance launcher
- Retail cue SHA-256: `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`
- Retail BIN SHA-256: `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`
- Movie SHA-256: `0a97102b1afde084bd5c1d8ca7a25d8acf838b69a5dc1fef2fc0007bb6937b58`
- State SHA-256: `f0de53baaf29d92956910fbda21f1091b110c8e190c60ed392823c460b5e4293`
- Transient boundary capture SHA-256: `41c068d0cd27c0c505c4ee5a632f9a8d91f74cb687d57faf3d5c2d42842b0f52`

The state remounted its isolated cached cue. Its cue and BIN hashes exactly matched the pristine retail pair; media serial remained `SCUS-94288` and `cd_overlays_removed` remained zero.

Bulk movies, saves, capsule chunks, checkpoints, and the boundary capture remain external or under the operator's ignored movie tree. Only hashes, reducers, and conclusions are stored in the repository.

## Static ASM result

### Selection and dispatch

The green count law is 1 to type 4, 2 to type 10, 3 to type 9, and 4 to type 1. The spawner creates a `0x30`-byte slot in the pool at `0x80090BF0`. The walker at `0x8005BFBC` checks `extra_state` bit `0x04`, calls `player_sector_lookup` at `0x80038E48`, and dispatches by type.

`0x8005CCE8` is not a self-contained passive green handler. It is a short walker continuation into the common loop beginning at `0x8005CD2C`.

### Growth reaction

At `0x8005CF30..0x8005D0CC`, the reaction requires state 0, animation accumulator `0x00030000`, `extra_state & 0x04`, and quantized squared 3D distance below 900. Type 4 writes `VY=-3584`. Green types 1, 9, and 10 use the generic radial branch with `VY=-2048`; type 3/5's `VY=-3328` is unrelated to the green tier law.

### Mature support

Once mature, the leaf models enter the standard sector/collision and player Y-commit paths. Tier height is therefore asset-defined. There is no unresolved resident green-only height table to find in the executable.

## Retained capsule result

Capsule root: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/A13__green_seed_levels`

- Manifest SHA-256: `4b820e271795cf7a5f56168206e3d07f34ba5bc8285b6c5dc8c4210bac171695`
- Preservation tree SHA-256: `2a1583e7d26370d797bfed791da0a571727d7a53ad1af51aafc84774e63610a7`
- Complete, no error or truncation, independent control mismatches `{}`
- 689,809,935 instructions, 96,157,436 passive blocks, 46 chunks, 10 checkpoints
- All four green types observed
- Every tier sets `extra_state` bit `0x04` after 28 frames and reaches state 1 after 66 frames

Observed mature surface rises:

| Type | Green count | Observed stable rises above base |
|---:|---:|---|
| 4 | 1 | about 11,111 and 11,191 |
| 10 | 2 | upper surface not occupied in this capsule |
| 9 | 3 | about 5,572, 13,821, and 25,143 |
| 1 | 4 | about 8,684, 17,963, 27,159, and 36,501 |

## Type-10 movie result

The 527-frame version-4 movie reports `reproducible:true`, `armed_while_paused:false`, and `phase_delay_owed:false`. Speed state was exactly target 1.0, fast-forward false, turbo false.

The C reduction found:

- Type 10 stayed in slot 3, state 1, `extra_state=0x0007`.
- Plant base: `(-67461,-93178,-319006)`.
- Highest nearby rise: 28,105 world units at movie boundary 180.
- Stable upper hold: boundaries 192 through 437, 246 boundaries total.
- Player upper Y: `-115765`; collision floor Y: `-115634`.
- Stable surface rise above plant base: 22,587.
- Departure begins at boundary 422; the upper floor is gone by boundary 450.
- Lower-floor settling is visible from boundaries 492 through 526 at player `Y=-94888`.

The external boost should not be assigned to type 10: a type-5 slot is active in the fixture, and the movie contains a `VY=-3328` reset before the upper landing. Exact attribution of that already-understood helper impulse is outside B05. The evidence needed here is that the type-10 upper surface is reachable, sustains Flik, releases him when he leaves, and gives way to ordinary falling and lower-floor landing.

## Observation, inference, confirmation

- Observation: all four green types and their common maturity timing are present in a complete, control-exact capsule.
- Observation: type 10 supports a stable upper hold 22,587 units above its base for 246 frame boundaries, followed by departure and lower-floor landing.
- Static confirmation: the growth reaction contains explicit type-dependent VY writes; mature support belongs to the ordinary collision path.
- Inference: exact platform heights and ledges are properties of plant collision assets, not a resident executable height table.
- Negative boundary: no claim is made that type 10 supplies the movie's external boost.

## Disposition

B05 is `Partial`, but bounded-exhausted for Phase 4 and safe to move past. The remaining work would be exhaustive polygon/sector topology for every green plant asset or a redundant instruction trace of the already-owned ordinary collision commit. Both are high-cost, low-return detail and do not leave a behavioral or ownership ambiguity in the row.

No additional Interpreter movie is required.
