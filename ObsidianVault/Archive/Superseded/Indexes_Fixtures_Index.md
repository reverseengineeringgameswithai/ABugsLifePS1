---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Indexes/Fixtures Index.md
aliases:
  - "Fixtures Index"
migration_action: merge
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Indexes/Fixtures Index.md`
- Replacement/current location: `ObsidianVault/Canon/Indexes/Fixtures_Index.md`
- Archive reason: Index material should be regenerated around Canon IDs.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Fixtures Index
type: index
updated: 2026-06-17
tags: [index, fixture, savestate]
---

# Fixtures Index

A *fixture* = a save state with a documented, reproducible purpose. Load with [[API - loadState]] and **settle one frame before [[API - addWatch]]**. Full raw catalog (incl. scratch slots) in [[Save States Index]].

| Fixture | Save state | Game state | Used by |
|---------|-----------|------------|---------|
| [[Fixture - g30 openground]] | `SCUS-94288_g30_openground.sav` | Flik on flat open walkable dirt; player sector **sec186**; R6 edit spot | [[G30 - Terrain render source]], [[G29 - Collision source]], all terrain/collision findings |
| [[Fixture - g30 openfloor]] | `SCUS-94288_g30_openfloor.sav` | Flik on big open pebbled floor (Z≈217790); clean visible-ground view ⚠️ walk-forward spawns enemy+fence | [[Finding - Visible ground from DAT verts]], [[Experiment - G28 Candidate A floor Y]] |
| [[Fixture - night starry]] | `SCUS-94288_night_starry.sav` | Result: sky turned to starry night via GPU injection (frozen-frame) | [[Finding - GPU primitive injection]], [[Experiment - Starry night sky injection]] |
| [[Fixture - night live]] | `SCUS-94288_night_live.sav` | **Persistent playable night** — big moon + stars via per-frame back-buffer hook, haze off, flicker-free | [[Finding - Persistent night render hook]], [[Experiment - Persistent nighttime render hook]] |
| [[Fixture - starry night workbench]] | `SCUS-94288_starry_night_workbench.sav` | Working bench for the starry-night injection | [[Experiment - Starry night sky injection]], [[Experiment - Persistent nighttime render hook]] |

## Headline replay fixtures (hash-pinned — GAP-0002 / GAP-0040)
These are the **local-only, non-committable** inputs the committed one-command replay tools load. Each is identity-pinned by SHA-256 in **`tools/fixtures.sha256`** (verified by `tests/test_fixtures_manifest.py`, advisory: skip-if-absent / fail-on-drift). The **bytes are never committed** ([[Preservation Policy]]); only the hash is. This is the *hash-pinned* half of the GAP-0002 acceptance bar.

| Role | Local path (convention) | Replay tool | SHA-256 (first 16) | Regeneration |
|---|---|---|---|---|
| spawn-floor LEVEL01 | `$ABL_SAVESTATES/SCUS-94288_1.sav` | `tools/trace_spawn_floor.py`; G29 arms via `--save` | `8fefa61e7c40205f` | from-boot movie `flik_to_level01_stall.mv.movie.json` → settle at spawn → save (UNKNOWN exact frame) |
| G29 Pass-3 (both arms) | shares `SCUS-94288_1.sav` **or** `--movie` from-boot | `tools/trace_g29_pass3_arm_a.py` / `_arm_b.py` | (shares spawn-floor) | same as spawn-floor; arm B also needs disc `--disc` |
| LEVEL02 floor (tool default) | `$ABL_SAVESTATES/SCUS-94288_3.sav` | `tools/trace_level02_floor.py` (default `--save`) | `0fb035bff1c53d63` | cold boot → warp/play to scene 3 → save (UNKNOWN exact route) |
| LEVEL02 floor (experiment evidence) | `level02.sav` (repo root) | `tools/trace_level02_floor.py --save level02.sav` | `9c4cd968151e8c2f` | as above; **this** is the byte the [[Experiment - LEVEL02 floor source]] evidence used |
| from-boot movie LEVEL01 | `flik_to_level01_stall.mv.movie.json` (repo root) | G29 arms `--movie`; boot→LEVEL01 replay | `a8b87ffedcc63051` | recorded input movie (boot→LEVEL01 stall); see [[API - movie]] |
| pristine disc | `Disney-Pixar A Bug's Life (v1.0).cue` (+`.bin`) | all replays `--disc` | `463102187c2ada6a` (.cue) | owner's V1.0 dump only; cross-check [[Checksum Manifest]] (CRC32 `607704bb`) |

**Fixture-identity residual (GAP-0002):** `trace_level02_floor.py` defaults to `SCUS-94288_3.sav` (`0fb035bf…`) while the [[Experiment - LEVEL02 floor source]] evidence used `level02.sav` (`9c4cd968…`) — both are scene-3 LEVEL02 states but **differ in bytes**. Until the two are reconciled, pass `--save` explicitly to pin the exact one; the experiment's canonical byte is `level02.sav`.

**Preserved harness identity (GAP-0001):** the DuckStation fork (`296955321…`), clean-built binary (`fd4bf9ed…`), and disc are pinned in `tools/FORK_COMMIT.txt`; not duplicated here.

### Why these are not committed
Save states, the disc image, and the from-boot movie are copyrighted or contain copyrighted game memory ([[Preservation Policy]]). `.sav`/`.cue`/`.bin`/`.movie.json` are gitignored and a test (`tests/test_no_forbidden_artifacts.py`) fails the build if one is ever tracked. The committable artifact is the **hash**.

### Verify / regenerate
- Verify all present fixtures: `python3 -m pytest tests/test_fixtures_manifest.py` (advisory) or by hand `sha256sum "$ABL_SAVESTATES/SCUS-94288_1.sav"` vs `tools/fixtures.sha256`.
- Regeneration of `.sav` fixtures from a cold boot is **not yet fully scripted** (the exact frame/route for each is UNKNOWN) — tracked under [[Gap Audit|GAP-0040]] (boot→scene movies). Hash-pinning satisfies GAP-0002 today; scripted regeneration is the GAP-0040 follow-on.

## How fixtures relate
- Fixtures ↔ Save States: each fixture wraps one `.sav` (see [[Save States Index]]).
- Fixtures ↔ Experiments: an [[Experiments Index|experiment]] names the fixture it loads.
- Fixtures ↔ Findings: a finding cites the fixture that reproduces its evidence.
- Source of truth: `fixtures:` block in `src_re_geometry/re_findings_backup.yaml`.

## Related
[[Home]] · [[Save States Index]] · [[Experiments Index]] · [[API - loadState]]
