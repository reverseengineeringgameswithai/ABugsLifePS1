---
kind: experiment
id: Experiment_-_Persistent_nighttime_render_hook
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Persistent nighttime render hook.md
aliases:
  - "Experiment - Persistent nighttime render hook"
---

# Experiment — Persistent nighttime render hook

> Migrated from `ObsidianVault/Experiments/Experiment - Persistent nighttime render hook.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — Persistent nighttime render hook

**Goal:** turn the daytime scene into a flicker-free persistent night (big moon + stars + dark sky) matching `nighttime_want.png`.

**Fixture/state:** load `SCUS-94288_starry_night_workbench.sav` (clean daytime); result saved as `SCUS-94288_night_live.sav`.

**Tool:** `tools/abl_night_hook.py` — `Starry().reload_clean(); H.install(s)`.

## Procedure
1. `reload_clean()` loads the workbench and patches the sky cache `0x800771bc/c0/c4` → dark navy.
2. `install(s)`:
   - writes the **night OT** (linked-list of moon disc + 5 glow rings + maria + ~55 dim stars; ~811 GP0 words) at `0x801e0400`, with an E5 placeholder at `+0x14`;
   - writes the **trampoline** at `0x801e0000` and patches `0x80062d04` → `j 0x801e0000`;
   - neutralizes the haze routine **[[FUNC_8003E928]]** (`jr ra` at `0x8003e928`).
3. The hook each frame reads **[[MEM - OT output buffer pointer 8008240C]]**, rewrites the night-OT E5 to the **opposite (back) buffer**, then DMAs the night OT into it (DrawSync-bracketed).

## Result (CONFIRMED)
- Big bright full moon (craters + soft glow) upper-left, subtle stars, smooth dark sky; **scene + Flik render normally**.
- **No flicker** while Flik walks: 0 corrupt frames over 12 + an 18-frame walk; `vram_source_rect.left` ∈ {0,512} every frame.
- Persists through a save/load of `SCUS-94288_night_live.sav` (hook + code live in RAM).
- Screenshots: `starry_night_result/06_persistent_moon_static.png`, `07_persistent_moon_walking.png`.

## Key learnings
- **Flicker root cause + fix:** draw into the buffer **opposite** to `[0x8008240c]` (the back buffer), never the displayed one.
- **DMA size cap ≈ 1000 GP0 words** before the display flip corrupts; keep the OT compact (height-`step` disc rows).
- The haze must be removed at its source (FUNC_8003E928), not covered (it's DMA'd after the hook).

## Related
[[Finding - Persistent night render hook]] · [[FUNC_8003E928]] · [[MEM - OT output buffer pointer 8008240C]] · [[Finding - GPU primitive injection]]
