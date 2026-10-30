---
kind: experiment
id: Experiment_-_Tier3_native_grain_relocation
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Tier3 native grain relocation.md
aliases:
  - "Experiment - Tier3 native grain relocation"
---

# Experiment — Tier3 native grain relocation

> Migrated from `ObsidianVault/Experiments/Experiment - Tier3 native grain relocation.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — Tier3 native grain relocation

> **Result: PASS.** A real native LEVEL01 `type-0x3f` grain relocated onto the Tier-3 custom platform is constructed
> and collected by the native pickup/HUD path on the cold-boot Tier-3 render disc. Baseline same movie/disc path keeps
> grain count `0`; relocated-grain disc reaches the same spawn with grain count `1`.

## Patch

Moved existing native grain entry `0` only; kind stayed `0x14`.

- Source DAT: `DAT/LEVEL01_LEVEL.DAT`
- Patched DAT: `build/gap_t3_1/LEVEL01_LEVEL_T3_NATIVE_GRAIN0.DAT`
- File coords: `(-8526,-3488,4544)` → `(6159,-8,15403)`
- Runtime coords: `(-272832,-111616,145408)` → `(197088,-256,492896)`
- Custom floor at spawn platform: player reached `(197091,-266,492897)`, so the relocated grain is effectively on
  the custom floor/spawn point.
- Temporary disc: `build/gap_t3_1/ABL_tier3_native_grain0.cue`
- Disc hash: `build/gap_t3_1/ABL_tier3_native_grain0.bin`
  `4c80b50ff499b5a1ea283b37518e7a422d1bd1d97c3788f9b4d65d549080305a`

## Runtime

DuckStation was launched detached with `duckstation-qt -nogui -fastboot` against an isolated config; the standard GUI
launcher path had exited after the READY probe, but `-nogui` stayed API-drivable once detached with `setsid`.

- Fork/binary: `~/duckstation/build-release/bin/duckstation-qt`
- Binary sha256: `2a4bd1655ec2f0c91f07aa089ed0b20d218ff157f110ec09ba3355507770a732`
- Movie: `flik_to_level01_stall.mv.movie.json`, from-boot, `4253` frames
- Modified-disc endpoint: port `23474`, token `gap-t3-1-live`, config `/tmp/duckstation-abl-gap-t3-1-live`
- Baseline endpoint: port `23475`, token `gap-t3-1-baseline`, config `/tmp/duckstation-abl-gap-t3-1-baseline`

## Evidence

Modified relocated-grain disc after movie playback:

- Media: `build/gap_t3_1/ABL_tier3_native_grain0.cue`
- Scene: `1`
- Player: `(197091,-266,492897)`
- `COPIED` (`0x8007f300`): `1` (Tier-3 render/level blob loaded)
- Grain counter (`0x800a65a1`): `1`
- Runtime `type-0x3f` record pointer: `0x801607fc`
- Entry 0 at `ptr+4`: `x=6159`, `y=0x80000000` sentinel after pickup consumption, `z=15403`, kind unchanged `0x14`

Baseline render disc after the same movie playback:

- Media: `build/ABL_tier3_render.cue`
- Scene: `1`
- Player: `(197091,-266,492897)`
- `COPIED` (`0x8007f300`): `1`
- Grain counter (`0x800a65a1`): `0`

## Conclusion

For GAP-T3-1, native-object-only is viable for differentiated pickups/counters at least for grains: native
`type-0x3f` object identity/behavior survives in Tier 3 when the object is placed onto the custom authored world.
Keep cave pickup markers only as prototype/fallback/custom-only markers; use native `type-0x3f` objects as the primary
path for real differentiated collectibles. This does **not** solve GAP-T3-6 for enemies/floor-following objects.

## Related

[[Tier 3 - Custom Level Engine]] · [[LEVEL.DAT object pipeline]] · [[MEM - Type-0x3f placement record]] ·
[[Experiment - Pickup kind-swap]]
