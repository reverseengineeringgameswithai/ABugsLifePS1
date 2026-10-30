---
kind: experiment
id: Experiment_-_Tier3_native_FLIK_letter_relocation
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Tier3 native FLIK letter relocation.md
aliases:
  - "Experiment - Tier3 native FLIK letter relocation"
---

# Experiment - Tier3 native FLIK letter relocation

> Migrated from `ObsidianVault/Experiments/Experiment - Tier3 native FLIK letter relocation.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment - Tier3 native FLIK letter relocation

> **Result: PASS.** The LEVEL01 F/L/I/K letters are real native `type-0x3f` collectible objects, not just HUD
> glyph art. Relocating entries 50-53 onto the Tier-3 custom platform collected all four through the native pickup
> path and set the FLIK collected-set bitmask to `0x0f`.

## Patch

Moved the four existing native FLIK letter entries only; kinds stayed native.

| Entry | Letter | Kind | Old file coords | New file coords | New runtime coords |
|---:|---|---:|---|---|---|
| 50 | F | `0x10` | `(-8616,0,4601)` | `(6159,-8,15403)` | `(197088,-256,492896)` |
| 51 | L | `0x11` | `(455,-50,21860)` | `(6209,-8,15403)` | `(198688,-256,492896)` |
| 52 | I | `0x12` | `(-9436,-50,-1950)` | `(6259,-8,15403)` | `(200288,-256,492896)` |
| 53 | K | `0x13` | `(9490,-50,9583)` | `(6309,-8,15403)` | `(201888,-256,492896)` |

- Source DAT: `DAT/LEVEL01_LEVEL.DAT`
- Patched DAT: `build/gap_t3_3/LEVEL01_LEVEL_T3_NATIVE_FLIK_ALL.DAT`
- Temporary disc: `build/gap_t3_3/ABL_tier3_native_flik_all.cue`
- Disc hash: `build/gap_t3_3/ABL_tier3_native_flik_all.bin`
  `ab3ae5e05a3f1a6c1587d6ed3490d05f3019c23b21c48b87a234ce46da948b04`

## Runtime

DuckStation launched detached with `duckstation-qt -nogui -fastboot` against isolated configs.

- Binary: `~/duckstation/build-release/bin/duckstation-qt`
- Binary sha256: `2a4bd1655ec2f0c91f07aa089ed0b20d218ff157f110ec09ba3355507770a732`
- Movie: `flik_to_level01_stall.mv.movie.json`, from-boot, endpoint frame `4501`

## Evidence

Modified relocated-FLIK disc after movie playback:

- Media: `build/gap_t3_3/ABL_tier3_native_flik_all.cue`
- Scene: `1`
- Player: `(197091,-266,492897)`
- `COPIED` (`0x8007f300`): `1`
- FLIK bitmask (`0x800a65a2`): `15` / `0x0f`
- FLIK HUD pulse (`0x800b0194`): `1088` / `0x0440`
- FLIK/berry marker (`0x800a6597`): `0`
- Grain counter (`0x800a65a1`): `0`
- Seed counters (`0x800a6598..9a`): `[17, 0, 0]`
- Runtime `type-0x3f` record pointer: `0x801607fc`

The four relocated source entries were consumed, each with the native consumed-entry `y=0x80000000` sentinel and
unchanged kind bytes:

| Entry | Words after collection | Raw record |
|---:|---|---|
| 50 | `[6159, -2147483648, 15403, 16, 0, 89, 0]` | `0f180000000000802b3c000010005900` |
| 51 | `[6209, -2147483648, 15403, 17, 0, 82, 0]` | `41180000000000802b3c000011005200` |
| 52 | `[6259, -2147483648, 15403, 18, 0, 75, 0]` | `73180000000000802b3c000012004b00` |
| 53 | `[6309, -2147483648, 15403, 19, 0, 69, 0]` | `a5180000000000802b3c000013004500` |

Baseline render disc after the same movie:

- Media: `build/ABL_tier3_render.cue`
- Scene: `1`
- Player: `(197091,-266,492897)`
- `COPIED` (`0x8007f300`): `1`
- FLIK bitmask (`0x800a65a2`): `0`
- FLIK HUD pulse (`0x800b0194`): `0`
- Entries 50-53 remained unconsumed at their original LEVEL01 positions.

## Interpretation

Existing RE in `src_re/pickup_handlers_80054288_80054554.c` matches the live result: FLIK kinds `0x10..0x13`
set bits `0..3` in `0x800a65a2`. Existing HUD RE in `src_re/hud_800526f4.c` and [[Menu and HUD structure]] matches
the display side: the HUD/status panel reads the same collected-set bitmask.

2026-07-06 visual follow-up: `SPINNING_F/L/I/K.sav` isolated the in-world pickup letter faces. They are 24×24,
4bpp static face tiles on tpage `x=640,y=0`, CLUT `x=880,y=217`: F `(192,64)`, L `(216,64)`, I `(192,88)`,
K `(216,88)`. The pickup spin is the textured quad rotating/skewing, not a per-letter texture flipbook. Reference PNGs
and capture metadata are in `mod/glyphs/pickup_letters/`; see [[HUD letter glyphs and word swap]].

## Conclusion

GAP-T3-3 is solved. FLIK letters are a native collectible set with four objects and a bitmask result, not merely
spinning HUD glyphs. Tier-3 levels should use native `type-0x3f` entries 50-53 when they need the real FLIK-letter
set behavior; any texture/glyph swap work is visual only and separate from the mechanic.

## Related

[[Tier 3 - Custom Level Engine]] · [[LEVEL.DAT object pipeline]] · [[Menu and HUD structure]] ·
[[MEM - Type-0x3f placement record]] · [[Experiment - Tier3 native grain relocation]] ·
[[Experiment - Tier3 native seed token relocation]]
