---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Preservation Policy.md
aliases:
  - "Preservation Policy"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Preservation Policy.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Preservation Policy
type: reference
updated: 2026-06-20
tags: [reference, legal, preservation, hygiene, b-policy]
---

# Preservation & Sharing Policy

> The single authoritative statement of **what may and may not be committed, shared, or distributed** from this project, and why. Resolves [[Gap Audit|GAP-0004]]. The rules are *practiced* via `.gitignore`; this note records the *policy* and rationale behind them. Linked from [[README]] · [[Project Index]] · [[CONTRIBUTING]].

## Legal posture
This project is **lawful preservation / educational reverse-engineering of a personally owned disc** of *Disney·Pixar A Bug's Life* (PS1, SCUS-94288, USA V1.0). It produces **original analysis** (notes, measurements, format specs) and **locally generated artifacts** (decompressed chunks, extracted media for study, save states). It does **not** redistribute the game, its assets, or any console firmware.

## What is NEVER committed or shared
| Class | Examples | Why |
|---|---|---|
| **Disc images** | `Disney-Pixar A Bug's Life (v1.0).bin/.cue`, any `.iso/.img/.chd` | Copyrighted game program + data. Reproduced locally from the owner's disc only. |
| **Extracted copyrighted assets** | `extracted/` (VAB/XA WAVs, FMV AVIs, GFX PNGs), ripped textures | Derivative copies of copyrighted audio/video/art. Kept local for study; regenerable from the owned disc (see [[Asset - Asset extraction recipe]]). |
| **Console firmware / BIOS** | any PS1 BIOS image | Copyrighted Sony firmware. Never in-repo; the isolated emulator uses a read-only BIOS the owner supplies. |
| **Extracted game code/data files** | `SCUS_942.88` (EXE), `LEVEL*.DAT/.RAW/.BIN`, `OVL/`, `DAT/`, `MEMORY.BIN` | Copyrighted program/level data. Reproduced locally from the disc. |
| **Save states & memory dumps** | `*.sav`, `*.mcr`, `*.state`, `*.ram` | Contain copyrighted RAM snapshots; also host-local and large. |
| **Rebuilt images** | `REBUILD/`, `BUILD/`, patched `*.bin/.cue` | Derivative full game images. |

## What IS shared (the project's actual product)
- **Analysis notes** — this Obsidian vault (`ObsidianVault/`), `docs/`, `src_re*/` markdown.
- **Reconstructed C / annotations** — `src_re/*.c`, `src_re_geometry/*.c` (original RE work; no copied game code).
- **Tools** — `tools/*.py`, `level_editor/` (original code that operates on the owner's local files).
- **Findings store** — `src_re_geometry/re_findings_backup.yaml`.
- **Provenance metadata** — hashes/checksums (CRC32/MD5/SHA-1), LBAs, offsets, format specs. *Facts about* the disc, not the disc.
- **Codec oracles** — `tools/raw_chunk0_*.bin` (small, force-added): a 24 KB compressed + 33 KB decompressed chunk pair used to validate the LZ codec. Minimal factual sample for research tracking; see the judgment note below.

> [!note] Minimal-sample judgment
> The codec oracle pair is a *small excerpt* retained only as a regression fixture for the decompressor. If ever in doubt about an excerpt's size/role, prefer **recording its hash** over committing the bytes. No full asset is committed.

## Reproducibility without distributing copyrighted material
Anyone with their **own** legally-obtained disc can reproduce the project: the disc reproduces byte-exact from `REBUILD/abl.xml` via `mkpsxiso` ([[Finding - Disc rebuild is byte-exact]]); `extracted/` regenerates via [[Asset - Asset extraction recipe]]; the codec dump regenerates via `tools/decode_level_raw.py`. None of that requires receiving copyrighted bytes from this repo. The remaining non-reproducible piece is the custom DuckStation fork ([[Gap Audit|GAP-0001]]).

## `.gitignore` mapping
The root `.gitignore` enforces this policy: `*.bin *.cue *.iso *.img *.chd *.sav *.mcr *.state *.ram`, `*.BIN`, `MEMORY.BIN`, `SCUS_942.88`, `DAT/ OVL/ REBUILD/ BUILD/`, `extracted/`, `*.log`, `tools/*.png`, `tools/LEVEL_*.RAW`. **Verification (2026-06-20):** `git ls-files` shows **0** tracked disc/BIOS/save artifacts (311 tracked files). Keep this true: never `git add -f` a copyrighted artifact.

## Do not
Do not include, in this repo or any shared note: ROM/BIOS acquisition instructions, cracks/DRM-circumvention, or full copyrighted asset dumps. Minimal factual metadata (hashes, offsets, sizes, format fields) for research tracking is fine.

## See also
[[CONTRIBUTING]] · [[Reproducibility Checklist]] · [[Asset - Disc image and rebuild]] · [[Asset - Asset extraction recipe]] · [[Roadmap]] · [[Gap Audit]]
