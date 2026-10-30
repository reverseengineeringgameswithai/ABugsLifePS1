---
kind: experiment
id: Experiment_-_Tier3_native_seed_token_relocation
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Tier3 native seed token relocation.md
aliases:
  - "Experiment - Tier3 native seed token relocation"
---

# Experiment — Tier3 native seed token relocation

> Migrated from `ObsidianVault/Experiments/Experiment - Tier3 native seed token relocation.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — Tier3 native seed token relocation

> **Result: PASS.** A real native LEVEL01 orange seed token (`type-0x3f` kind `0x29`) relocated onto the Tier-3
> custom platform is collected through the native token handler and advances the native packed orange seed counter.
> This closes GAP-T3-2 without adding cave-side typed collectible code.

## Patch

Moved existing native seed-token entry `63` only; kind stayed `0x29`.

- Source DAT: `DAT/LEVEL01_LEVEL.DAT`
- Patched DAT: `build/gap_t3_2/LEVEL01_LEVEL_T3_NATIVE_SEED63.DAT`
- File coords: `(-2131,-250,-10028)` → `(6159,-8,15403)`
- Runtime coords: `(-68192,-8000,-320896)` → `(197088,-256,492896)`
- Static custom-floor check: runtime `(197088,-256,492896)` sits over T3 floor tri `1`, floor Y `-266`, delta `+10`.
- Temporary disc: `build/gap_t3_2/ABL_tier3_native_seed63.cue`
- Disc hash: `build/gap_t3_2/ABL_tier3_native_seed63.bin`
  `91b1db1a4dc43a7eefaf6fd6486567149b78fc34ba51751435192be19b583940`

## Runtime

DuckStation launched detached with `duckstation-qt -nogui -fastboot` against isolated configs.

- Binary: `~/duckstation/build-release/bin/duckstation-qt`
- Binary sha256: `2a4bd1655ec2f0c91f07aa089ed0b20d218ff157f110ec09ba3355507770a732`
- Movie: `flik_to_level01_stall.mv.movie.json`, from-boot, `4253` frames
- Modified-disc endpoint: port `23476`, token `gap-t3-2-seed`
- Baseline endpoint: port `23477`, token `gap-t3-2-base`

## Evidence

Modified relocated-token disc after movie playback:

- Media: `build/gap_t3_2/ABL_tier3_native_seed63.cue`
- Scene: `1`
- Player: `(197091,-266,492897)`
- `COPIED` (`0x8007f300`): `1`
- Grain counter (`0x800a65a1`): `0`
- Seed counters: orange `0x800a6598 = 0x22`, blue `0x800a6599 = 0`, green `0x800a659a = 0`
- Runtime `type-0x3f` record pointer: `0x801607fc`
- Entry 63 at `ptr+4+63*0x10`: `x=6159`, `y=0x80000000` sentinel after pickup consumption, `z=15403`,
  kind unchanged `0x29`

Baseline render disc after same movie playback:

- Media: `build/ABL_tier3_render.cue`
- Scene: `1`
- Player: `(197091,-266,492897)`
- `COPIED` (`0x8007f300`): `1`
- Grain counter (`0x800a65a1`): `0`
- Seed counters: orange `0x800a6598 = 0x11`, blue `0x800a6599 = 0`, green `0x800a659a = 0`

## Interpretation

The orange counter is packed, not a plain decimal count. Existing RE in `src_re/pickup_handlers_80054288_80054554.c`
documents the native handler: logical count `n = (old + 1) & 7` is stored as `n * 17`, so `0x11` is logical 1 and
`0x22` is logical 2. The relocated seed token advanced the native counter by exactly one logical token and consumed
the source entry.

## Conclusion

GAP-T3-2 resolves via the native object path: Tier-3 levels should use native `type-0x3f` seed-token objects
(`0x29/0x2a/0x2b`) for per-kind token counters. Cave-side typed collectible work is unnecessary for the primary
design unless the engine later needs a custom-only collectible class that has no native equivalent.

## Related

[[Tier 3 - Custom Level Engine]] · [[Seed planting system]] · [[LEVEL.DAT object pipeline]] ·
[[MEM - Type-0x3f placement record]] · [[Experiment - Tier3 native grain relocation]]
