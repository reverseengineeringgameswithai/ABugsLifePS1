---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Pass-3 decor records decoded (cull anchor + suppression).md
aliases:
  - "Finding - Pass-3 decor records decoded (cull anchor + suppression)"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Pass-3 decor records decoded (cull anchor + suppression).md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Pass-3_decor_records_decoded_(cull_anchor_+_suppression).md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Pass-3 decor records decoded (cull anchor + suppression)
type: finding
status: confirmed (live, phase-matched A/B); cold-boot bake untested
updated: 2026-07-02
confidence: CONFIRMED (format, culler, 2 suppression levers); LIKELY (backdrop-pass draw transform)
tags: [finding, leveldata, decor, pass3, hre-001, suppression, leveleditor]
---

# Pass-3 decor records decoded (cull anchor + suppression levers)

> Closes the [[LEVEL01 Level-Edit Punchlist]] §11 residual "pass-3 (140 records) position field
> undecoded" and delivers the HRE-001 source-side suppression path for this decor class.
> Live-proven on LEVEL01 (`SCUS-94288_8.sav`, isolated DuckStation port 23460, pristine v1.0).

## The format (the "undecoded position" was a parse misalignment)

The true pass-3 table in `LEVEL01\LEVEL.DAT` starts at **file `0x3AEC`** (not `0x3AFA`) — 140
records, stride 0x14, **identical field layout to pass-1**:

```
+0x00 s32 X   +0x04 s32 Y   +0x08 s32 Z     ; CULL-ANCHOR (file/placement frame, Y-up)
+0x0C u16 extent                            ; cull slack radius
+0x0E u16 flags                             ; 0x0001 ×85 · 0x0009 ×16 · 0x4009 ×39
+0x10 u32 src                               ; source-record file offset (RELOCATED to a RAM
                                            ;   pointer at load; -> AABB node + payload @+0x14)
```

All-`0x8000` **sentinel records** bracket the table at `0x3AD8` (leading) and `0x45DC` (trailing);
the runtime walker stops on `flags < 0` (s16). The historical parse (`p3base=0x3AFA`, "src @+2")
was shifted +0xE bytes: its src reads (`0x3AFA+i·0x14+2` = `0x3AEC+i·0x14+0x10`) were **exactly
each true record's src** — so the G27 census and instancing histogram were always right — but its
"position bytes" straddled two records, which is the whole reason the field looked undecodable.
`level_editor/scene_importer.py`'s `LevelProfile.p3base` should move to `0x3AEC` with pass-1-style
field offsets (not changed in this pass — operator WIP tree).

## Runtime: per-frame culler `FUNC_80014360` (bounds exact, ..0x80014500)

Each frame, the culler walks the (RAM-resident, DATbase `0x801607F8`) table and builds a
**visible-record pointer list at `0x80096EA8`** (entries = record base addresses, low bit = tag;
57 entries in the fixture view). Two gates per record:

1. **Enable bitmap** — bytes walking **down** from `0x800902C7`, MSB first:
   record *r* ↔ byte `0x800902C7 − (r>>3)`, mask `0x80 >> (r&7)`. All-1s in LEVEL01
   (18 bytes `0x800902B6..C7` for 140 records + pad). **Static after load — zero per-frame
   writers** (armed write-watch, 0 hits). Initializer not yet traced (BSS default or load-time).
2. **GTE frustum/distance cull** — `view = R·(pos − cam)`; view-Z window against the draw
   distance `[0x8008238C]>>2` and |X|/|Y| cone tests, each with ±extent slack.

Consumers of the visible list: `0x8001EAD8` and `0x8002074C` — two passes inside the unified
mesh builder (selected by flags bit `0x10`; flags bit `0x80` sets `gp+0x5FC = 3000`, an
LOD/fade-style var). They read the record's `flags`/`src` and draw the payload.

## The decisive empirical facts (phase-matched loadState A/B, 20-frame matched runs)

Skyline prop = record **#56** (file pos `(1887,-505,5488)`, ext 234, flags 1) — the only pass-3
prop visible in the `_8` fixture view (97×102 px box at display (372,108)):

| Perturbation | Result |
|---|---|
| clear its bitmap bit | **prop vanishes** (1369 px) |
| move record XYZ far away (30000³) | **prop vanishes** (same 1369 px box → cull-fail) |
| move record XYZ near/onto Flik | **zero pixels change** |
| extent → 0 | zero pixels change |

⇒ **Record XYZ is the CULL ANCHOR ONLY.** The drawn geometry's position is baked in the payload
(and/or drawn in a backdrop-pass transform) — unlike pass-1, where record XYZ is the draw anchor.
Corroboration: the prop's world position projects **behind the camera** with the full camera
transform, but rotation-only (parallax/backdrop) projection lands inside the observed pixel box.
Named residual: the exact draw transform (payload world-baked vs rotation-only backdrop pass).

## What this gives HRE-001 / Tier-3

- **Suppress any pass-3 decor prop at the source**: overwrite the record's cull-anchor XYZ with a
  far-away point — a **size-preserving 12-byte in-place edit in uncompressed LEVEL.DAT** (same
  edit class as the proven pass-1 coordinate edits; no relocation, no code cave). Per-prop or all-140.
- Live/cave alternative: clear enable-bitmap bytes `0x800902B6..C7` (works instantly live;
  needs a post-load cave write until the bitmap's initializer is found).
- Pass-3 props **cannot be relocated** via the record (cull anchor ≠ draw position) — moving them
  means editing payload vertices. For Tier-3 blank-slate levels suppression is what's needed anyway.
- Caveat: levers proven **live** on the loaded table; the disc-edit bake (cold-boot) is the same
  byte region as proven pass-1 disc edits but has not itself been cold-boot-tested yet.

## Telescope (kind 0x30) delete safety — risk reclassified (same session)

The `delete_type3f_entries.py` `RISK_CHECKPOINT` classification ("delete-unsafe telescopes") was
precautionary, never evidence-based. Test: deleted LEVEL01 telescope entries **68 & 69** (of
67/68/69) relocation-aware (`--allow-checkpoint`), rebuilt the disc
(`rebuild_with_patched_dat.py`, embedded-bytes verified), **cold-booted + movie-replayed to
LEVEL01** (`flik_to_level01_stall.mv.movie.json`):

- Level loads and plays: live type-0x3f table **70 → 68**, kind histogram correct
  (50 grain, 4 FLIK, 4 berries, 9 tokens, **1 telescope** @ entry 67), no parse corruption.
- Flik controllable (post-`movie.stopPlayback` input moved him −13844/+10871 over 40 frames);
  survived two fall-death + respawn cycles; no guest halt across 6200+ frames.
- Checkpoint flag `0x800824DC` normal (0); remaining telescope actor live (entry Y settled −2506
  vs record −1600 = actor-side write present).

**Verdict: kind-0x30 deletion is load/play-safe on LEVEL01.** The Tier-3 build can delete its 2
surplus telescopes instead of keeping them. Named residuals: (a) contact/hint interaction with the
*remaining* telescope not exercised (its area is a pit from above — teleport tests fall-die;
needs a natural approach or a nearby fixture); (b) level-completion regression untested.
Gotcha for repro: **stop movie playback before injecting controller state** — issuing
`setControllerState` while the finished movie was still attached killed the host process once.

## Repro

- Culler discovery: `accessLog.addWatch` read on DATbase+`0x3AFA+6` → PCs `0x8001441c/20/24/28`;
  `functionBounds 0x800143f0` → `0x80014360..0x80014500` exact; bitmap found in the preamble
  (`s0 = 0x800902C7`, `lb`+decrement).
- Bit↔record mapping proven by visible-list diff: clearing byte `0x800902C0` bit `0x80` removed
  exactly list entry `0x80164744` = DATbase+`0x3F4C` = record #56.
- Telescope disc: `delete_type3f_entries.py REBUILD/files/LEVEL01/LEVEL.DAT --delete-index 69
  --delete-index 68 --allow-checkpoint --write` → `rebuild_with_patched_dat.py` (restored the
  pristine tree after; embedded sha1 `d841930e…`).

## Related

[[LEVEL01 Level-Edit Punchlist]] §11 · [[Retail Gameplay Completeness Gap Audit]] HRE-001 ·
[[Tier 3 - Level Replacement Phases]] (Phase 2 telescope caveat, Phase 4 residual terrain) ·
[[Finding - DAT record holds decor instance world position]] (pass-1 contrast) ·
`src_re/pass3_backdrop_cull_80014360.c` · `src_re/world_render_dispatch.c`
