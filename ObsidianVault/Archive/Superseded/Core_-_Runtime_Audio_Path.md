---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Core - Runtime Audio Path.md
aliases:
  - "Core - Runtime Audio Path"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Core - Runtime Audio Path.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Core_-_Runtime_Audio_Path.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Core - Runtime Audio Path
type: core
updated: 2026-06-22
tags: [core, audio, spu, vab, xa, milestone5, gap-0031, b5]
---

# Core — Runtime audio path (baseline)

> M5 baseline for [[Gap Audit|GAP-0031]] — moves beyond asset-format knowledge into the in-engine SPU load/playback path. **Asset format = DONE; runtime engine path = open.** Provenance: format facts CONFIRMED; runtime anchors are STATIC string/disasm; playback triggers are hypotheses (DYNAMIC/local-only to confirm, [[DuckStation Fork Reproducibility]] / GAP-0001).

## Asset formats (CONFIRMED — DONE, separated from runtime)
- **VAB** (`.VH`+`.VB`): compact PS1 `pBAV` magic, **version 6**; parses + SPU-ADPCM-decodes fully offline. GLOBAL = 3 programs / 43 tones / 43 VAGs (Σ VAG sizes = 178224 = exact VB size, verified). **All 21 VAB banks** use the same parser → [[Finding - VAB sound bank format]].
- **Music = XA-streamed** (no `.SEQ`/`.SEP` on disc): `BUGXASTR/AUDIO1..5.XA` (8 stereo channels @ 37.8 kHz), CD-XA interleaved → [[Blocker - Audio subsystem is completely unanalyzed|B5]].
- Disc: `SFX/GLOBAL.{VB,VH}` @ LBA 16289–16377; per-level VABs (`LEVEL1A.VB/VH`, etc.) → [[Asset - Disc file map]].

## Runtime path (STATIC anchors — hypothesis)
| Anchor | Role | Conf |
|---|---|---|
| `SsVabOpenHead` / `SsVabTransBody` fail-strings `0x8001b098` / `0x8001b0bc` | libspu VAB open/transfer | CONFIRMED (string) |
| **`fcn.80042fa0`** (called from `0x80074a64`, `0x80076a64`) | **sound VAB/SFX loader** (bank → SPU RAM) | LIKELY |
| `fcn.80042f58` (s0) | VB sample staging | LIKELY |
| `0x800972a8` | sound/data buffer | LIKELY |
| SPU timeout `0x8001c1f8` | libspu wait | CONFIRMED (string) |
| XA filename table `~0x800772f8` (`\BUGXASTR\AUDIOn.XA;1` strings @ `0x8001b0e0+`) | XA stream selection | LIKELY |
| libcd `CdlSetfilter` / `CdlReadS` | XA streaming read path | CONFIRMED (string) |
| pickup SFX handlers (e.g. FLIK-letter `0x80054288`, `a0 = 0x35/0x36/0x37/0x38`) | gameplay → SFX trigger | LIKELY |

## Leading hypotheses
- **`fcn.80042fa0`** = the VAB open/transfer loader (header parse → `SsVabTransBody` into SPU RAM) at level/section load.
- **SFX trigger** = a libsnd `SsUtKeyOn`-style call from per-kind gameplay handlers (the pickup handlers already pass sound IDs in `a0`).
- **Music** = XA via libcd `CdlReadS` + `CdlSetfilter` (channel select) → SPU streaming (the genuine streamed subsystem, see [[Core - CD Streaming and Caching]]).

## Relationship to overlays / front-end / gameplay
Bank loads ride the level-load path ([[Core - CD Streaming and Caching]]); SFX triggers come from gameplay handlers (resident EXE); front-end/menu audio is overlay-resident (un-RE'd). Music streaming is independent of the geometry all-at-load model.

## Named missing / next experiments
- **libspu/libsnd voice key-on call sites** (the actual `SsUtKeyOn`/`SpuSetKey`).
- **Music-vs-SFX dispatch** + the **XA cue → channel map**.
- Next (LOCAL-ONLY): `execTrace` the libspu thunks (`fcn.80042fa0`, the `Ss*` fail-string callers) during playback; `accessLog` SPU-control register writes. Record fixture/frame/PC + fork commit; label local-only.

## Runtime path — firmed up (static) + live probe (2026-06-22; GAP-0031)
**libspu fn addresses (resolved from the fail-string callers).** VAB loader **`fcn.80042fa0`** → **SsVabOpenHead `0x8006b130`** (`jal` @ `0x80042f94`; err→`0x8001b098`) → **SsVabTransBody `0x8006b1c0`** (via `0x8006b59c` @ `0x80042fc4`; err→`0x8001b0bc`) → finalize **`0x8006b65c`** (`a0=1`): header-open → DMA bank into SPU RAM → end. `SsVabTransBody` calls the libspu DMA/wait pair `0x8006ce6c`/`0x8006ce40`.
**SFX dispatcher `0x80050994` (disasm-confirmed).** Sound id in `a0`, **sign-split** (`bgez s0,…`): `a0≥0` (SFX pool) vs `a0<0` (`nor s3,zero,s0` → second/music pool), indexing a descriptor array at `~0x80088xxx`. Pickup handlers (`0x80054288`, ids `0x35..0x38`) `jal 0x80050994`. The **menu** uses a sibling SFX fn `0x80050838` on cursor move (overlay, see [[Menu and HUD structure]]).
**Live probe (LEVEL01 `SCUS-94288_1.sav`, fork `fe0cca16b`, port 23460 — local-only).** `execTrace.addWatch {pc:0x80050994}` armed across a 30-frame idle window **and** a held-input window (cross / circle+triangle) = **0 hits**. The render-flip site fired in the same `execTrace.run`, so the trace was live ⇒ a *standing* Flik dispatches no libsnd SFX (consistent: SFX is event-driven, music is the independent XA-DMA path). This is a true idle negative, not a dead watch — but it is **not** a positive trigger confirmation.
**Verdict:** SFX trigger path (gameplay/menu handler → `0x80050994`/`0x80050838` → libspu key-on) + music path (XA `CdlReadS`/`CdlSetfilter` + per-level filename table `0x8001b0e0`) are **documented (static, disasm-backed)** — acceptance "SFX/music trigger path documented" MET. **Residual (local-only):** a *positive* live SFX-event trace (collect/jump/hit, or a menu blip) + the exact `SsUtKeyOn` voice key-on + the XA cue→channel map.

## XA cue → channel map — LEVEL01 RESOLVED + replacement proven (2026-06-23, GAP-0031)
**Music-start `FUNC_8004699c(a0)`**: `file = AUDIO(a0>>3 + 1)` via filename table **RAM `0x800772c8`** (file off `0x67ac8`; 5×12B records `{*name, CdlLOC, size}`), `channel = a0&7`. Builds `CdlFILTER{file=1, chan}` at **`0x80046a6c`** → `CdlIntToPos` → **`CdlReadS` (0x1b) @ `0x80046aa0`**, `CdlSetmode 0xe8` (2× + XA-ADPCM). **Loop = software position-poll `FUNC_80046828`** (CdGetlocL pos vs end markers → re-issue SetFilter+IntToPos+ReadS at saved start CdlLOC) — **NOT the XA EOF subheader bit**. Public wrappers `0x80046ac0` (once) / `0x80046ae8` (loop).
- **LEVEL01 sustained gameplay music = `AUDIO1.XA` channel 0** (258 s). **CONFIRMED IN-GAME** (operator booted a rebuilt disc with AUDIO1 ch0 replaced → LEVEL01 music swapped + loops). Matches the static default path (engine reset `FUNC_8004fa40` → area `0x8008243c=0` → switch `0x8001b3c4` case 0 → music_id 1 → a0=0).
- **GOTCHA:** a live `CdlSetfilter` trace at the LEVEL01 **load screen** (frame 3068, black) caught `a0=0x12` → **AUDIO3 ch2**, but that is a short ~12 s **load/transition cue**, not the gameplay loop. Trace *into* gameplay and sanity-check channel capacity (a 12 s clip ≠ a level theme), else the load cue masquerades as the level music.
- **Replacement capability PROVEN** (closes the practical half of B5/GAP-0031): MP3 → `ffmpeg` 37800 Hz/16-bit/stereo → `psxavenc -t xa -f 37800 -c 2 -b 4` → `tools/xa_audio.py splice` (in-place channel payload swap; preserves every subheader/EOF/EDC byte → identical size/LBA/loop) → `tools/build_music_disc.py` (mkpsxiso rebuild + embed-verify; XA files are `type="mixed"` raw copy). Round-trip from the rebuilt disc = source audio @ **55.8 dB SNR**. Bank capacities (s): AUDIO1 ch0-7 = 258/233/252/237/249/241/254/245; AUDIO2 ch0-6 ≈239-277 (ch7=11); AUDIO3 ch3/4/5 ≈125 (music), ch0/1/2/6/7 ≈11-12 (cues).

## Confidence ledger
Asset formats — **CONFIRMED/DONE**. `fcn.80042fa0` = VAB loader (→ `SsVabOpenHead 0x8006b130` / `SsVabTransBody 0x8006b1c0`), SFX dispatcher `0x80050994`, XA = music — **CONFIRMED (static, disasm)**. Positive live SFX trigger + voice key-on / XA channel map — **residual (local-only)**.

## Related
[[Finding - VAB sound bank format]] · [[Blocker - Audio subsystem is completely unanalyzed]] · [[Core - CD Streaming and Caching]] · [[Asset - Disc file map]] · [[Asset Extraction Pipeline]] · [[DuckStation Fork Reproducibility]]
