---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation/API wishlist - analysis fast-tracking.md
aliases:
  - "API wishlist - analysis fast-tracking"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation/API wishlist - analysis fast-tracking.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API wishlist - analysis fast-tracking
type: reference
tags: [duckstation, api, tooling, wishlist]
updated: 2026-07-06
---

> [!important] CORRECTION (2026-07-06): more recurring analysis gaps are now closed/partially closed.
> - **Instruction-attributed access logs** → `accessLog.get` events now include `reported_pc`, `instruction_pc`, `instruction_word`, `instruction`, and `width`; use `instruction_pc` instead of manual `pc`/`pc-4` attribution. `accessLog.summary` / `execTrace.summary` give hot-PC/frame aggregates.
> - **Screen-region primitive trace** → `gpu.traceRegion {x,y,width,height}`.
> - **Live VRAM/CLUT provenance** → `gpu.vramWriteLog.get`, `gpu.resolveVramProvenance`, and `gpu.resolveClutProvenance`, backed by the retained automatic VRAM write log plus `transferLog.resolve` / transferLog event IDs when a DMA payload RAM address is known. Not retrospective before the current session/state.
>
> [!important] CORRECTION (2026-06-27): the last two high-value debugger gaps here are now closed too.
> - **Guest function-call** → **`debugger.callFunction {address, a0..a3, timeout}`**. It jumps into a guest
>   subroutine while paused, uses the current paused PC as the return trap, and returns `v0`/`v1` when the callee
>   comes back.
> - **Static CD provenance** → **`transferLog.resolve {address}`**. It resolves RAM→disc/file provenance at any time
>   (incl. post-load save states for EXE-backed addresses, and for streamed assets when the transfer log captured the
>   load).
> - **#1 disc-change** → superseded by **`cd.overlayFile {path,hex}`** (overlay `LEVEL01/LEVEL.RAW` live, no
>   rebuild/swap, persists across loadState). Better than disc-change. Also `cd.overrideSectors`, `listOverlays`.
> - **#2 world→screen projection** → buildable from **`debugger.getGteState`** (decoded rotation matrix +
>   translation) + **`execTrace`** capturing `gte.SXY*` at a draw PC (used this to localize terrain in G33b).
> - **Input** ("crashed the link") → that was misuse of `pressButton`; **`emulator.setControllerState` +
>   `advanceFrames`** is the robust path, and analog stick axes are injectable now too. Bulk writes →
>   **`debugger.scatterWrite`**, not one giant `writeMemory`.
> So the only genuinely missing niceties from this note are secondary ones such as a typed struct-array helper or a
> direct VRAM-write surface. The rest below is historical.

# DuckStation external-debugger API — gaps that slowed the seed write-path work (G32)

Ranked by how much each would have fast-tracked the decompress→edit→recompress→rebuild→verify loop.
Concrete origin: each cost real round-trips during the [[Seed planting system]] disc-edit proof.

## 1. Disc change / boot-image API  ⭐ biggest bottleneck
`emulator.changeDisc(path)` (± `reset`) or `emulator.bootImage(path)`.
- **Why:** the debugger can't mount the rebuilt `.bin`, so EVERY iteration needed a manual operator boot.
  3+ human round-trips this session, two of them just to discover I'd moved the wrong seed.
- **Payoff:** turns the whole pipeline into one unattended loop — and lets me *auto-bisect* (rebuild N
  variants, boot each, read the result) to map record→seed without guessing.

## 2. World→screen projection from live GTE/camera state  ⭐ would have prevented the wrong-seed detour
`gpu.projectWorld(x,y,z) -> {sx, sy, onScreen}` (or `object.screenRect`) using the current GTE matrices.
- **Why:** this session's core failure mode was "seed moved but off-camera," which is **indistinguishable
  from "didn't move"** without a human looking. I burned two rebuilds on a seed sitting in a far zone.
- **Payoff:** self-confirm a move landed in view; instantly classify off-screen vs not-moved vs wrong-object.

## 3. Frame capture paired with (2)
Capture exists (`d.cap`), but pairing it with the projection (crop to / mark the expected screen pos)
would make visual self-verification reliable instead of operator-dependent.

## 4. Typed struct-array readback  (minor)
`readStructArray(base, stride, count, layout) -> [dict]`.
- **Why:** I read the 26-element base array (`0x800a0014 + n·0x84`) and 31-element record array field by
  field. Works, but it's boilerplate + many small reads. A layout-aware bulk read is faster and clearer.

## 5. CD named-file read  (minor)
`cd.readFile("LEVEL01/LEVEL.RAW") -> bytes`.
- **Why:** correlating live decompressed RAM to on-disc bytes meant going through `REBUILD/files` staging
  + manual chunk-header parsing. A direct named read simplifies the live↔disc mapping.

## Already present and sufficient
accessLog · execTrace · transferLog · gp0Trace · memoryScan · gpu.readVramRect · readArray ·
experiment.run · findings store · loadState/saveState · controller/pressButton · capture.

## Related
[[DuckStation API Index]] · [[Seed planting system]] · [[Finding - LEVEL.RAW is compressed]]
