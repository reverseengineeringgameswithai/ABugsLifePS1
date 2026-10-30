---
kind: system
id: SYS_overlays_and_runtime_loading
name: Overlays, compressed containers, and runtime-loaded chunks
aliases: [Executable and Overlays, Executable_and_Overlays]
status: live_confirmed
confidence: confirmed
updated: 2026-08-05
source_state: original_game
functions: []
memory: []
tables: []
constants: []
evidence:
  - EXP_2026-07-08_re_baseline_run
  - EXP_2026-07-08_function_census_v1
  - EXP_2026-07-08_boot_trace_baseline
  - EXP_2026-07-08_overlay_track
  - EXP_2026-07-09_overlay_coverage
src_paths: [docs/EXECUTABLE_AND_OVERLAYS.md, tools/decode_level_raw.py, tools/recompress_level_raw.py, tools/re_baseline.py, analysis/overlay_symbols.json, tools/trace_overlay_coverage.py]
---

# SYS_overlays_and_runtime_loading

## Purpose
Canon inventory of every runtime-loaded / compressed code-or-data container in the
game — the "overlays, compressed sections, runtime-loaded chunks" axis of the RE
basics. Deep dive tables (per-file LBA/size/SHA-1): `docs/EXECUTABLE_AND_OVERLAYS.md`.

## Confirmed behavior

### Code overlays — two fixed swap buffers
| Region | Base | Contents | Loader |
|---|---|---|---|
| **A** | `0x800B39A0` | per-level code `LEVEL0N\LEVEL[M].BIN` (20 files, header word +0, code +4; entry `level_overlay_init` = +0x4) | fcn.8003d620 (call 0x8003d638) |
| **B** | `0x800B5788` | `bits\memory.bin` (memcard/menu), `fmv\fmv.bin` (FMV player) | fcn.8003cf2c / 8003f5b8 / 8003e7c0 / 8003f504 |

Link-time-fixed jals ⇒ each buffer always loads at its fixed base; *contents* are
swapped per level/mode. Overlays share the resident `$gp = 0x80081D98`.
Static analysis recipe: r2 `-n -m <base>` on the blob (baked into
`tools/re_baseline.py --overlays`; 2026-07-08 run: 21 blobs, e.g. LEVEL01_LEVEL.BIN
4 functions, MEMORY.BIN 61 functions).

### Runtime residency is part of every overlay address

An address in Region A or B is not a complete code identity. Before naming,
breaking, disassembling, or tracing it, call `memory.getResidency` for the full
swap region and preserve:

- source file and load/file offset;
- runtime base and region size;
- source-slice and resident-memory SHA-256 values;
- `sourceMatchesResident`;
- load generation, timestamp, frame, and cycle; and
- the provenance basis/notes when identity is inferred or ambiguous.

Re-query immediately before execution and after the captured window. The
generation tuple plus resident-memory hash is the address-validity token. A
changed generation invalidates an address resolved against the earlier
occupant; a hash-only change records byte divergence under the same tracked load.
The generation and DMA-residency ledger are runtime-only debugger state: state
load/reset/media change invalidates them, and they are intentionally absent from
save-state serialization.

`sourceMatchesResident:false` means the bytes differ; it does **not** alone mean
the source identity is wrong. Region-A code can modify its own loaded bytes. An
exact recorded CD-DMA load can therefore retain a defensible source/file/base
identity after the resident hash diverges, while an untracked or ambiguous scan
cannot. Report the distinction instead of substituting a plausible overlay.

For static cross-overlay work, use `debugger.xrefsAcrossOverlays` with explicit
`source_file`, `file_offset`, `runtime_base`, `region_id`, and `load_generation`
for each image. It keeps same-address mutually exclusive overlays distinct,
propagates runtime bases, and recognizes bounded base-plus-offset and bitmask
references. Static references accelerate localization; the live residency check
still establishes which image actually executed.

### Compressed / streamed data containers
| Container | Codec | State |
|---|---|---|
| `LEVEL.RAW` (per level) | **Rob Northen PROPACK 2.29** LZ | codec SOLVED byte-exact both ways (`tools/decode_level_raw.py` / `recompress_level_raw.py`); chunk roles: see [[Asset - LEVEL.RAW Chunk Role Table]] |
| `LEVEL.DAT` (per level) | uncompressed (disc == RAM image) | direct edit; relocation rules in `docs/DAT_FORMAT_AND_RELOCATION.md` |
| `GFX/*.RAW` (loading screens) | same LZ container family | solved (`tools/loadscreen_edit.py`) |
| STR / XA (FMV, music) | standard MDEC/XA streams | replace pipeline solved (`tools/media_replace.py`) |

## Overlay code semantics (OVL campaign — o0–o3)
Overlay *mechanics* were known; the overlay *code* was the biggest un-understood mass (168/192 fns unnamed,
~91 KB). The OVL campaign added a per-`(overlay,address)` name store (`analysis/overlay_symbols.json`; overlays
share load addresses so `re_symbols.sym` can't name them) + runtime coverage ([[EXP_2026-07-09_overlay_coverage]]:
150 fns execute across the pristine movies; `overlay_naming_priority.json` ranks the rest). The census also gained an **overlay data-in-code detector** (a ≥32 B span with zero control-flow can't be a
function — it's a pointer table / embedded filename string / overlay header; the overlay analogue of the RCA a5
resident fix): **14 data regions** were split out of the code set (and 5 mislabeled seed-names removed).
**Overlay CODE fns 160, named 149 (93%)** (the strict jr-ra/jal detector split out further data regions);
every name evidence-gated. The 11 unnamed split into **5 covered-but-unnamed** (static/runtime RE — more runs
won't help) and **6 movie-blocked** (100% LEVEL01/04/05 completion runs + a Load/Save/Options menu-navigation
run); see [[Overlay Campaign Status]] + `analysis/overlay_naming_priority.json`.
- **Region-B (MEMORY.BIN) = the title/menu/save front-end** — see [[SYS_menu_and_frontend]] (44/69 fns run at
  boot; main-menu state, memcard cluster, save/load screens, sprite/menu draw all named).
- **Region-A (level overlays) = per-level gameplay handlers.** Each level's `_LEVEL`/`_LEVEL1` blob is
  `level_overlay_init` (entry `base+4`) + a few handlers that **orchestrate resident gameplay primitives** — e.g.
  LEVEL01's `level_spawn_region_handler` (`oriented_containment_range_test`→`spawn_drop`) and
  `level_actor_event_handler` (`atan2_heading`+`play_sound`+`spawn_drop`+`spawn_fx_object`). So the level-specific
  logic lives in the overlay while the shared verbs stay resident. This is the template for the LEVEL02–10 rollout.

## Unknowns
- LEVEL.RAW chunk inventory beyond the identified roles remains partly unmapped
  (tracked separately, not an overlay-mechanics gap).
- ~~LEVEL11–15 overlay extraction~~ **RESOLVED (u2 survey 2026-07-09): LEVEL11–15 do not exist on the disc**
  (the game ships 11 level directories; the later scenes reuse the Region-A buffer with existing blobs).
- 11 overlay code fns remain unnamed (ranked in `analysis/overlay_naming_priority.json`): 5 covered-but-unnamed (static/runtime RE) + 6 movie-blocked — see [[Overlay Campaign Status]].

## Evidence
- [[EXP_2026-07-08_re_baseline_run]] — per-overlay function counts regenerated.
- Supersedes archived [[Executable_and_Overlays]] (overlay half) and absorbs the
  mechanically-imported [[Asset - LEVEL.BIN and overlays]].
- Runtime overlay observations after 2026-08-05 must retain the
  `memory.getResidency` source/resident hashes and load generation in their
  evidence bundle; writer-PC evidence remains useful as an independent control.
