---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Persistent night render hook.md
aliases:
  - "Finding - Persistent night render hook"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Persistent night render hook.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Persistent_night_render_hook.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Persistent night render hook
type: finding
confidence: CONFIRMED
gstep: n/a (starry-night, persistent)
tags: [finding, rendering, gpu, injection, sky, hook, double-buffer]
---

# Finding — Persistent night render hook (flicker-free, big moon, no haze)

> A per-frame code hook turns the daytime scene into a **persistent nighttime level** that survives gameplay (Flik walking) with **no flicker**: a big bright full moon + subtle stars over a smooth dark sky. Supersedes the one-shot overlay of [[Finding - GPU primitive injection]]. Target look = `nighttime_want.png`.

**Confidence:** CONFIRMED (built + observed live + walking, 0 corrupt frames) · **Tool:** `tools/abl_night_hook.py` · **State:** `SCUS-94288_night_live.sav`

## The three problems and their fixes
1. **Dark sky (persistent):** patch the per-level sky-color cache `0x800771bc/c0/c4` → dark navy (see [[Finding - Sky is a GP0 background fill]] / [[MEM - Sky DRAWENV color cache 800771BC]]).
2. **Bright horizon HAZE band:** it's drawn by **[[FUNC_8003E928]]** (the horizon-strip routine, called once/frame from `0x80039b24`; it tiles textured rects across the screen, stepping by the value at `0x800771b0`). Neutralize it with `jr ra ; nop` at its entry → smooth dark sky. (Side effect: also removes the dirt-wall backdrop it draws.)
3. **Moon/stars + the FLICKER:** inject a per-frame trampoline that DMAs a "night OT" (GP0 linked-list of moon disc + glow rings + maria + dim stars) into the **back buffer**.

## The hook (flicker fix is the key insight)
- **Hook site:** trampoline at **`0x80062d04`** (`addiu a3,s2,14`, raw `0x2647000e`) in the frame driver, returns to `0x80062d0c`. Runs each frame BEFORE the main scene OT is DMA'd.
- **Back-buffer targeting:** read **[[MEM - OT output buffer pointer 8008240C]]**. At this hook `[0x8008240c] == the DISPLAYED drawenv` and the *fresh* scene is always in the **opposite** (back) buffer. Env `0x801e134c` (bit `0x20000` set) ⇒ displayed=x0 ⇒ back=x512; env `0x801cc390` ⇒ back=x0. The hook reads `[0x8008240c]`, tests `0x20000`, and rewrites the night OT's **E5 draw-offset word** (at `NIGHT_OT+0x14`) to the back buffer (`E5` x=0 or 512, y=264). Drawing into the *back* buffer (single buffer, never the displayed one) ⇒ **no flicker, no scene-drop**, and it flips to display next.
- Mechanism inside the hook: `DrawSync` (poll D2_CHCR `0xBF8010A8` bit24) → kick our linked-list GPU DMA (`MADR=0x001e0400`, `CHCR=0x01000401`) → DrawSync → restore. The two drawenvs alternate each render (30 fps); the hook is 60 fps but the `[0x8008240c]`-relative targeting makes it deterministic.

## Gotchas (CONFIRMED)
- **DMA-size limit ≈ 1000 words:** a night OT > ~1000 GP0 words corrupts the game's display (the long DMA blocks the CPU and breaks the frame's display-flip timing; symptom: `vram_source_rect.left` reads 256, scene drops). 932 words OK, 1022 CORRUPT. Keep the OT small (final ≈ 811 words; draw discs as height-`step` rows, not 1px rows).
- The moon/stars are drawn BEFORE the main scene OT DMA, so they only survive where the scene doesn't overdraw them (the clear sky, y<66). A flat cover **band** at the haze row does NOT survive (the haze/scene OT is DMA'd after the hook) — that's why the haze is removed at its source ([[FUNC_8003E928]]) instead of covered.
- `setRegister("pc")` can't redirect (fetch uses `g_state.npc`); MMIO/VRAM aren't writable by the debugger — all drawing is via injected MIPS + GPU DMA. See project memory `abl-gpu-injection-starry`.

## Evidence
Before/after/walking screenshots in `~/Downloads/ABL/starry_night_result/` (`01_before_daytime.png`, `06_persistent_moon_static.png`, `07_persistent_moon_walking.png`). Reference target `nighttime_want.png`.

## Related
[[FUNC_8003E928]] · [[FUNC_800639CC]] · [[MEM - OT output buffer pointer 8008240C]] · [[MEM - Sky DRAWENV color cache 800771BC]] · [[Finding - Sky is a GP0 background fill]] · [[Finding - GPU primitive injection]] · [[Experiment - Persistent nighttime render hook]] · [[API - execTrace]] · [[API - gpu.readVramRect]]

## Source
Tool `tools/abl_night_hook.py`; project memory `abl-gpu-injection-starry`; live RE this session (G-night).
