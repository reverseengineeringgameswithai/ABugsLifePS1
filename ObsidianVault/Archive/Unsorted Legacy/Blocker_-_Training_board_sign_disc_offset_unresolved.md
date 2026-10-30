---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Training board sign disc offset unresolved.md
aliases:
  - "Blocker - Training board sign disc offset unresolved"
migration_action: archive
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Training board sign disc offset unresolved.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Training board sign disc byte offset unresolved
type: blocker
status: CLOSED — RESOLVED 2026-07-05
updated: 2026-07-05
tags: [blocker, training, texture, sign, re, session-handoff]
---

# ✅ RESOLVED 2026-07-05

The board sign pictures are **tile-major 64x64 4bpp tiles** in **`LEVEL07/LEVEL1.RAW`,
chunk 29**, first tile at decompressed offset **0x8B7C8** (sign *k* at `0x8B7C8 + k*2048`).
The board displays **sign 0**. Proof: each disc tile == the live VRAM board tile byte-for-byte
except the ~165-byte runtime "×N" digit overlay (rows 16-47, cols 48-63). A *row-major* copy of
the same art also lives at chunk 6 / 0x2D554 (Region-A texture page feeding the static (320,0)
texpage) — editing THAT does NOT change the board; use chunk 29. Injection proven in-game:
`tools/training_board_edit.py replace --image X --sign N` → auto-layout reflow disc
(chunk grows, so NOT size-preserving; ships via `build_autolayout_disc.py`). Quantise to the
blue-grey CLUT ramp (indices 0-12); the 3 green entries speckle non-green art.

**Follow-up (open):** raise the new sign as a NEW objective ~3s after the injected NPC
monologue, as a mods.yaml toggle — needs board sign-change/objective state-machine RE +
XA-voice-end detection. See [[Training board sign images]] / `src_re/training_board_sign.c`.

The full original investigation trail below is retained for reference (many dead ends were
because the atlas was searched *row-major*, but the board uses the *tile-major* chunk-29 copy).

---

# Training board sign — exact on-disc byte offset UNRESOLVED (historical)

> Goal: replace the tutorial ant's chalkboard sign image (paired with a custom NPC voice
> line) via the ABL Mod Studio. Blocked on: **we cannot yet locate this specific tile's
> pixel data on disc**, despite extensive static + live investigation. This note is the
> full resume-here record — read before trying again, so dead ends aren't re-walked.

## What's SOLID (re-confirmed fresh, 2026-07-04, on a brand-new isolated instance)
- **Training is its own in-game level**, `current_scene_id = 17`, genuinely distinct from
  the Anthill/Level 1 (`scene 1`) — confirmed by the literal **"Training Level... loading..."**
  screen. The operator was right to insist on this; earlier framing that conflated them was
  wrong and has been corrected in [[Training board sign images]] and the mod studio ([[Consolidated mod build manifest]]).
- **Draw source** (`gpu.pickObject` on the live board, reconfirmed on a fresh boot):
  `GP0(0x3c)` textured quad, texpage VRAM `(320,0)` mode 0 (**4bpp**), CLUT `(784,229)`,
  tile UV **`u:64-127, v:0-63`** → VRAM absolute `(336,0)`, 64×64. `tools/training_board_edit.py
  extract-tile` reliably pulls the CURRENT on-screen tile from this — extraction is proven
  and safe to use today.
- **Reaching Training from cold boot**: `LEVEL00_load.movie.json` (4162 frames, `from_boot:true`)
  → play to completion (it naturally stops around frame ~5500) → lands settled in Training
  with the board on screen. (Despite the filename, this is the correct movie — don't be
  thrown by "LEVEL00"; scene 17 loads mid-movie around frame 3501-3900.)

## Dead ends — DO NOT re-try these without a new angle
1. **`LEVEL01/LEVEL.RAW` decompressed offset `0x98650`** (my original claim, now RETRACTED).
   Rendering the bytes there with the known CLUT produces pure noise. The earlier "confirming"
   signature match was a false positive from a too-short (16-byte), background-dominated
   signature — this data is mostly one repeated nibble (background), so short signatures
   collide constantly across a 1.27 MB file. **Any future signature-based search MUST use a
   32+ byte, verified-high-entropy window**, tested with a full-block byte-exact compare
   before trusting a "hit."
2. **`GFX/TRAINING.RAW`** — DOES get loaded during the Training level-load window (confirmed
   via `transferLog` CD-read provenance), but its two real chunks are NOT our tile:
   - chunk 0 (33548 B decompressed) = the "loading... ⊗ start" prompt overlay (confirmed by
     rendering it with the proven **Region-A texture-page format**: `+0x00 u32 id, +0x04 u16 W,
     u16 H, +0x08 u16 clut_bytes(=768), u16 flag, +0x0c CLUT (256×RGB 3B), +0x30c pixels`
     — see [[Finding - Region-A texture format decoded]]).
   - chunk 1 (163856 B decompressed) = the 320×256 16bpp full-screen backdrop (per
     [[loadscreen_edit.py]]'s documented format; 163840 pixel bytes + 16 B header matches exactly).
3. **Exhaustive Region-A-shaped chunk scan** — every `.RAW` file's chunks with decompressed
   size 33548 or 17164 (the two known "texture page" sizes), decoded with the confirmed format
   above, searched for our tile's signature at the correct `+0x30c` pixel offset, **0 hits**.
   So this tile is either NOT stored in the standard Region-A texture-page format, or not in
   any currently-decompressed `.RAW` file at all.
4. **Nibble-swap / tight-packed (32 B/row, no VRAM padding) hypotheses** — tried both, and
   their nibble-swapped variants, against the full decompressed content of every `.RAW` file
   plus the EXE. **0 hits.**
5. **`transferLog.resolve`** on every RAM address we found associated with this tile (the
   post-decompression staging buffer `~0x800b5a9c`, the decompression-loop src/dst
   `0x800b5daa`/`0x800b5e3f`) — always returns `resolved:false, "no covering load-map segment,
   decompression record, or DMA/CD-ROM history"`. This fork's `transferLog` does not track
   the game's own SOFTWARE (CPU-side) LZ decompression, only raw CD→RAM DMA. Don't expect
   `resolve` to work on any address downstream of the game's custom codec.
6. **GP0-register write breakpoint** (`debugger.addBreakpoint {address:"0x1f801810", type:"write"}`)
   — does NOT reliably trap the real GP0 port on this fork/build. It paused, but the trapping
   instruction (verified via disassembly at both `status.pc` AND `COP0_EPC`) was an unrelated
   RAM-to-RAM copy loop inside the LZ decompressor (`~0x8001a600`, near the known codec entry
   `0x8001A1DC`), not a GP0 write. **Do not trust this breakpoint address on this fork without
   independently re-verifying it traps a real MMIO write first.**
7. **`LUI rt,0x1f80` + `ORI rt,rt,0x1810` literal-pair grep** across the whole EXE — 156 raw
   `LUI ...,0x1f80` sites (shared with many other `0x1f801xxx` hardware registers) but **zero**
   paired with an `0x1810` low-half within the next 6 instructions. The GP0 port address is
   very likely accessed via a **resident pointer/global**, not re-constructed inline — a future
   attempt should look for a LOADED pointer (e.g. `lw t9, N(gp)` or a fixed resident global)
   instead of an inline literal.

## What DID work, mechanically (reusable technique, just aimed at the wrong data so far)
- **`transferLog.start` + periodic `gp0Trace.get`+`clear` while advancing in small (~100-frame)
  chunks** during full movie replay from boot — this successfully caught the real
  `GP0(0xA0)` LoadImage commands: a full-atlas upload at **frame 3707** `(x=320,y=0,w=64,h=256)`
  and a per-tile update at **frame 3866** `(x=336,y=0,w=16,h=64)` plus a nested
  `(x=348,y=16,w=4,h=32)` update — **the nested update strongly suggests the "×N" digit is a
  SEPARATE, smaller stamp on top of a static bug silhouette**, i.e. this tile may NOT be one
  fully pre-baked static image after all (revises the earlier `src_re/training_board_sign.c`
  claim that the count is "baked into the pixels" — that claim was based only on visual
  inspection of one static VRAM read, not on how it's assembled). **Worth re-examining**:
  extract tiles for several different board states (different ×N counts) and diff them — if
  only a small sub-region changes, that confirms a separate digit stamp, narrowing where a
  REPLACE would need to write.
- **Identifying distinct CD-read "runs"** from `transferLog.get` (channel `CDROM`, 2048-byte
  DMA bursts, grouping by contiguous destination address) then **grepping the raw `.bin` disc
  image directly** for a captured RAM sample, cross-referenced against `REBUILD/abl.xml`'s
  `offs=` LBA table — this DEFINITIVELY identifies which named file was loaded in a given
  frame window (proved `LEVEL00/TERRAIN.ALL`, `GFX/TRAINING.RAW`, `CHARS2/HSPIDER.ANM`,
  `GFX/CIRCUS.RAW`, `LEVEL01/LEVEL1A.VH`/`.VB` all load in this same window). **This is a
  solid, reusable method** — just needs to be pointed at the RIGHT moment (right around
  frame 3707/3866, not the broader 3400-3465 window that only caught loading-screen assets).

## Recommended next angle (not yet tried)
1. **Diff multiple board states first** (per the nested-update finding above) — extract-tile
   for 2-3 different ×N counts via `tools/training_board_edit.py`, byte-diff the results. If
   only a small region differs, the STATIC part (bug silhouette) is what actually needs
   finding on disc for a picture swap, and the digit can stay a separate (possibly HUD-glyph)
   concern — this could simplify the whole problem.
2. **Narrow the CD-read hunt to immediately before frame 3707 and 3866 specifically** (not the
   broader window that only caught the loading screen) — re-run the "distinct runs + disc grep"
   method from a fresh replay, watching CDROM events in tighter windows like [3690,3710] and
   [3850,3870] specifically (the first attempt at [3670,3715] found zero CD reads, meaning
   the data was ALREADY resident by then — so the real load happens EARLIER; bisect backward
   from there, e.g. check [3500,3700]).
3. **Find the resident GP0-port pointer** (a loaded global, not an inline literal) via
   `xrefsTo`/disassembly around confirmed GPU-adjacent code (e.g. near `0x800105f0` or
   `0x80014a70`, the known thrown-berry OT emitters, or near `0x80010000`/`0x800172dc`, the
   known mesh/floor emitters) — these already push primitives through the GPU and may reveal
   the shared port-access pattern this game actually uses.

## Related
[[Training board sign images]] (the RE finding, corrected) · [[Consolidated mod build manifest]]
(Mod Studio UX + status badges) · `tools/training_board_edit.py` (extract works; replace
pending this blocker) · `src_re/training_board_sign.c` (needs a revision pass once the
digit-vs-silhouette question above is settled) · [[Finding - Region-A texture format decoded]]
