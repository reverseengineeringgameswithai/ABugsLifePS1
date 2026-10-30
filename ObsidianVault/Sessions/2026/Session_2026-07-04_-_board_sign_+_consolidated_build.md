---
kind: session
id: Session_2026-07-04_-_board_sign_+_consolidated_build
created: 2026-07-08
updated: 2026-07-08
date: 2026-07-04
status: legacy_imported
legacy_source: ObsidianVault/Systems/Session 2026-07-04 - board sign + consolidated build.md
aliases:
  - "Session 2026-07-04 - board sign + consolidated build"
---

# Session 2026-07-04 — training-board "sign" RE + one-disc mod consolidation

> Migrated from `ObsidianVault/Systems/Session 2026-07-04 - board sign + consolidated build.md` during the 2026-07-08 vault completion pass. Reason: Chronological/handoff note; keep as history, not Canon.

# Session 2026-07-04 — training-board "sign" RE + one-disc mod consolidation

> [!warning] Historical cave map
> This session predates the 2026-07-07 Gold Berry token crash fix. The listed `golddrop` placement at `0x8007EFE8` and hook at `0x80049958` are superseded and unsafe. Current records: [[MOD_gold_berry_token_drop]], [[HOOK_800592A4_golddrop_death_tail]], [[HOOK_forbidden_patch_ranges]], and the archived [wrong-hypothesis record](../../Archive/Wrong%20Hypotheses/WHYPE_gold_drop_type34_and_80049958.md).

> Two deliverables. (1) Answered whether the tutorial ant's chalkboard "sign" is a glyph or an
> image — it's an IMAGE — and located it for extract/replace. (2) Built a manifest-driven
> consolidated disc build and folded in three mods, cold-boot verified coexisting.

## Deliverable 1 — the chalkboard sign is an IMAGE (not glyphs)
Full detail: [[Training board sign images]] · RE `src_re/training_board_sign.c`.
- Probed the live session (read-only): `gpu.pickObject` on the board → **GP0(0x3c) textured
  quad**, texpage (320,0) **4bpp**, CLUT (784,229), tile **UV u:64-127 v:0-63**. Decoding VRAM
  page (320,0) revealed the whole **tutorial atlas** ("x6" bug, "x1" berries, mushrooms, seeds,
  green gems, "Exit"). The count number is **baked into the tile pixels**, not HUD glyphs.
- Disc source: **LEVEL01/LEVEL.RAW, decompressed ~0x98650, logical chunk 32** (load base
  0x800c1690) — confirmed by matching the live RAM staging buffer to the decompressed file.
- **Extract works today:** `tools/training_board_edit.py extract-tile|extract-atlas -o X.png`.
- **Replace = scoped follow-up** (NOT shipped as a stager): chunk 32 is ~237 KB, recompress
  ~1.02x can exceed its fixed-LBA sector slot → needs in-budget recompress or autolayout reflow;
  and the tile's byte extent inside the collision-sharing chunk must be mapped to avoid corruption.

## Deliverable 2 — one disc, many mods (`mods.yaml`)
Full detail: [[Consolidated mod build manifest]] · [[Consolidated_mod_build_manifest|consolidated build manifest]].
- New: `mod/build.py --mods mod/mods.yaml` — `code_mods` lane (all caves → one SCUS, **disjoint
  cave-region assertion**) + `asset_mods` lane (size-preserving, layered per file, one mkpsxiso).
  Registry `mod/mods/registry.py`; shared tail `finish_build()`.
- **Cave allocator** was the crux: blackberry, golddrop, grain all hard-coded `0x800810C0`.
  Live-verified two more boot-safe zero-runs; rebased **golddrop→0x8007EFE8**
  (`mod/mods/golddrop.asm`), **grain_hud→0x8007F174** (`mod/mods/grain_emblem.asm`); blackberry
  stays at `0x800810C0` (`mod/patch.asm`). ⚠️ avoid 0x8007FD58 / 0x800821FC (live buffers).
- **Built + verified:** `build/ABL_ALLMODS.cue` — EXE byte-exact at LBA 23 (794 B changed);
  isolated cold boot clean; all hooks jump to disjoint caves (golddrop 0x80049958→0x8007efe8,
  grain 0x80052b40→0x8007f314 & 0x80055008→0x8007f338, blackberry 0x8005a0f0→0x800810c0 &
  0x80047170→0x80081190). training_board left `asset_mods: []` pending replace plumbing.

## Files touched
- New: `src_re/training_board_sign.c`, `tools/training_board_edit.py`, `mod/mods/registry.py`,
  `mod/mods/golddrop.asm`, `mod/mods/grain_emblem.asm`, `mod/mods.yaml`.
- Edited: `mod/build.py` (`--mods`, `build_patched_exe_from_mods`, `run_asset_lane`,
  `finish_build`, `run_manifest`).
- Vault: [[Training board sign images]], [[Consolidated mod build manifest]], this note.
- Nothing committed; operator's port-2346 session only read from; isolated instance stopped.

## Resume-here / next options
- Finish training-board **replace**: map the tile's byte extent in chunk 32 + solve the
  sector budget (in-place vs autolayout), then add `stage_patch()` + register in ASSET_MODS.
- Fold more existing mods into `mods.yaml` (music/SFX/FMV are size-preserving → good asset-lane
  candidates; each needs a `stage_patch` wrapper + registry entry).
