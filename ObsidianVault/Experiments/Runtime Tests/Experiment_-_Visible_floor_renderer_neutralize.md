---
kind: experiment
id: Experiment_-_Visible_floor_renderer_neutralize
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Visible floor renderer neutralize.md
aliases:
  - "Experiment - Visible floor renderer neutralize"
---

# Experiment — Which function renders the visible walkable floor (authoritative)

> Migrated from `ObsidianVault/Experiments/Experiment - Visible floor renderer neutralize.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — Which function renders the visible walkable floor (authoritative)

> Settles the long-flipping **f5/f10 (chunk-35 / `fcn.800172dc`) vs f13 (LEVEL.DAT / `fcn.80010000`)** question for the floor Flik stands on, via the live DuckStation API. **Result: f13.** Drives the correction of [[Finding - Visible terrain renderer]] and resolves the former single-source-evidence blocker for this claim.

**Confidence:** CONFIRMED (patch-verified, frame-matched, 7 scenes, visual + quantitative) · **Date:** 2026-06-18

## Method (reproducible)
- Per run: `emulator.loadState(S)` → `advanceFrames(10)` *(settle — the terrain renderer needs several frames to start firing)* → optionally patch a function entry to **`jr ra; nop`** (`wu32(addr,0x03e00008); wu32(addr+4,0)`) → `advanceFrames(4)` → `captureFrame`.
- **Frame-matched**: control and test both reload the same `S` and advance the same total frames → animation cancels (determinism control = **0.0%**).
- **Diff with PIL** on settled PNGs (per-pixel |Δ|>24), **not `emulator.diffFrames`** — diffFrames hit a capture/flush race (reported 62.7% where the settled-file compare was 1.6%; see [[API - visual diff]] gotcha).
- **Patch verified to work**: `execTrace` at `fcn.800172dc`'s internal rtpt `0x80017464` → **172 hits/4f unpatched → 0 patched**. The function genuinely runs and is genuinely neutralized.

## Results
| Neutralize | Visible Δ | Interpretation |
|---|---|---|
| **`fcn.800172dc`** (chunk-35) | **0.0%** in **7 scenes** | fires 172 quads/4f from buffer `0x8012xxxx` but **fully occluded → 0 visible px** |
| `fcn.800172dc` **+** `fcn.80010000` | 0.0% vs DAT-only | even with the DAT floor gone, 172dc adds nothing → truly invisible here |
| `fcn.80019934` | 1.6% (animation) | not the floor |
| **`fcn.80010000`** (LEVEL.DAT) | **44.5%**, lower-screen | **draws the visible pebbled floor**; removing it flattens it to a plain plane (`extracted/q_n10000.png`, overlay `q_n10000_ov.png`) |

Scenes swept (all 0% for 172dc): `operator_backup`, `terrain_collision_floor`, `_1`, `_5`, `_10`, `seed_closeup`, `greenitem_lvl9`.

## Conclusion (authoritative → f13)
- **The visible walkable floor is drawn by `fcn.80010000` from LEVEL.DAT** (matches [[Finding - Visible ground from DAT verts]] and the [[Canon Index|current Canon]] "foreground floor = FUNC_80010000" framing).
- **`fcn.800172dc` / chunk-35 is NOT the visible floor** — it renders a terrain layer that is **fully occluded** in all tested scenes. Its actual on-screen role (distant/background terrain visible only in some vista?) is a separate open question; it is **not** the surface Flik walks on.
- **Reconciliation of the prior flip:** the earlier "neutralizing `fcn.800172dc` flattened the pebble ground to a plain plane" observation is **reproduced by neutralizing `fcn.80010000`** — a function-address swap (`0x80010000` ↔ `0x800172dc`). The "X-shift of the buffer sheared the ground" claim (G30 R1) was likely similarly confounded/misattributed.
- **Findings store action:** `f5/f10` (chunk-35 = visible terrain) → should be **DISPROVEN/RETRACTED**; `f13` (LEVEL.DAT) → **CONFIRMED**. (Flagged for the operator to update `re_findings_backup.yaml`.)

## Fixtures / APIs
`SCUS-94288_operator_backup.sav`, `SCUS-94288_terrain_collision_floor.sav` (+5 more) · [[API - loadState]] · [[API - execution control]] · [[API - execTrace]] · [[API - gpu.readVramRect|captureFrame]] · [[Relaunching DuckStation]] (used to recover the server mid-experiment).

## Related
[[Finding - Visible terrain renderer]] · [[Finding - Visible ground from DAT verts]] · [[FUNC_80010000]] · [[FUNC_800172DC]] · [[MEM - Terrain vertex buffer 8012C1D0]]
