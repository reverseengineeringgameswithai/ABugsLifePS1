---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Consolidated mod build manifest.md
aliases:
  - "Consolidated mod build manifest"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Consolidated mod build manifest.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Consolidated_mod_build_manifest.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Consolidated mod build (mods.yaml manifest)
type: system
confidence: CONFIRMED (built + cold-boot verified 3 mods coexisting, 2026-07-04)
tags: [system, mod, build, manifest, disc, code-cave, blackberry, fastberry, golddrop, grain, training]
updated: 2026-07-07
---
# One disc, many mods — the `mods.yaml` manifest

> [!warning] Patch safety Canon
> This note is still useful for the manifest build, but patch-safety decisions should route through [[HOOK_forbidden_patch_ranges]]. Current Gold Berry token behavior is curated in [[MOD_gold_berry_token_drop]], and current Blackberry behavior is curated in [[MOD_blackberry_net_new_berry]]. Do not reuse older `0x8007EFE8`, `0x80049958`, `0x80081058..0x800810A4`, or `0x80082030..0x8008203C` assumptions outside their documented hazard context.

> Replaces the ~15 one-off `build_*_disc.py` / `patch_*.asm` scripts (each built its own
> disc from pristine, so mods couldn't stack and clobbered shared files). Now: list the
> mods you want in `mod/mods.yaml`, run one command, get one disc.

```
python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force
```

## Two lanes (`mod/mods/registry.py`)
- **`code_mods`** — EXE code-caves. Every selected mod patches **one copy** of `SCUS_942.88`
  by name in a single armips pass. Each registry entry gives its `.asm` include, its C caves,
  and its cave region `[base, base+span)`. `build.py` **asserts the regions are disjoint**
  (engine hook addresses are already disjoint across the mods).
- **`asset_mods`** — per-file **size-preserving** edits, layered onto **one working copy per
  target file** (never re-derived from pristine mid-build), then a **single mkpsxiso** + LBA
  verify. Each tool is `stage(pristine_bytes, params) -> patched_bytes`.

The old tail (stage → mkpsxiso → restore → verify embed) is now `finish_build()`, shared by
the legacy and manifest paths.

## Cave-region allocation (the real consolidation problem)
The standalone mods each hard-coded base **`0x800810C0`** (the one README-blessed zero-run),
so combining them overlapped. Fix = a small allocator over **live-verified boot-safe zero-runs**
(all-zero during active gameplay, 2026-07-04):

| Mod | Base | Span | Note |
|---|---|---|---|
| `blackberry` | `0x800810C0` | ~0x360 | Legacy manifest key; `mod/patch.asm` implements Blackberry/Fastberry and owns most of the 0x409 run |
| `golddrop` | `0x80081100` + `0x80078D84` | death ~0x90, pickup ~0x80 total | compact death hook in the Blackberry speed→throw gap; pickup path inlined at `0x80078D84..0x80078E04` |
| `grain_hud` | `0x8007F174` | ~0x1E4 | rebased → `mod/mods/grain_emblem.asm` |
| `training_word_pickups` | `0x800811BC` nop, `0x800811C0`, `0x800813AC`, `0x80081430`, `0x80081488`, `0x80081580` | delay slot + 0x50 + 0x54 + ~0x60 + 0x20 + 0x40 | asset stager patches SCUS gates/helper for Training `TRAINING` pickups |
| `training_tutorial` step-2 blackberry gate | `0x8007F0D8`, `0x8007F930` | 0x40 + 0x24 | asset stager patches SCUS for the custom step-2 voice+pickup gate; step wait block in `LEVEL07/LEVEL1.BIN` jumps to the EXE gate |

⚠️ **Avoid `0x800B4A30`, `0x8007EFE8..0x8007F0D8`, `0x8007F130..0x8007F16F`, `0x8007FBC8`, `0x8007FD58`,
`0x80081058..0x800810A4`, `0x80081858`, `0x80081CF0`, and `0x800821FC`** — live runtime buffers/state
(Training/HUD/RNG/pause/input), zero at boot or in the static file but written in play. The
`0x8007EFE8` gold-drop version corrupted the resident table used by `0x800616e0`, producing an
invalid byte write to `0x910A0000` at `PC=0x80061788` (`COP0_EPC=0x80061784`). The
`0x8007F130` helper version clobbered `0x8007F16C`, which Training later read through code around
`0x800616C0`, causing an invalid word read crash. The `0x800B4A30` step-2 gate version crashed
with `PC=0x000000A0`, `COP0_EPC=0x800B4A34` because Training had runtime data there. Verify any
new cave region with a live read *during gameplay* (must be zero) before allocating.

## Known crash: `0x8007EFE8` is not slack
2026-07-07 ALLMODS crash root cause: `golddrop` placed its death hook at `0x8007EFE8`.
DuckStation halted with `PC=0x000000A0`; console log showed `Invalid byte write at address
0x910A0000, value 0x00000055, pc 0x80061788` and COP0 reported `EPC=0x80061784`. Disassembly
of `0x800616e0` shows it materializes `0x8007EFE8` as a table base, indexes records by `0x30`,
then writes through pointers loaded from those records. Cave instructions in that table poisoned
the pointer.

Guardrails now in tree:
- `mod/mods/registry.py` has `FORBIDDEN_CODE_RANGES` and rejects code-mod ranges overlapping
  `0x8007EFE8..0x8007F0D8`.
- `src_re/known_crash_cave_hazards.c` records the crash signature and other cave hazards for
  Codex/Claude-style future passes.
- `golddrop` moved to `0x80081100..0x80081190`, the real gap between Blackberry `CAVE_SPEED`
  and `CAVE_THROW`; its pickup path is inlined at `0x80078D84..0x80078E04`.
- `mod/mods/registry.py` also rejects the live-zeroed `0x80081058..0x800810A4` helper range and
  native descriptor `0x80082030..0x8008203C`.

Step-2 blackberry gate fix, 2026-07-07: `training_tutorial` appends a hidden kind-`0x25` pickup
and gates step 2 on both voice completion and `0x800A6597 == 5`. The broken build jumped from
`LEVEL07/LEVEL1.BIN` into `0x800B4A30`; the fixed build jumps to `0x8007F0D8`, with the reveal
shim at `0x8007F930`. Current rebuilt `build/ABL_ALLMODS.bin` SHA-256:
`3f001b4c385831183d211446caa2e2ba26553f84b55d27b40ea22249a400e688`. Isolated DuckStation
advanced to frame `12000`; live cave bytes survived, and the restored Blackberry/Fastberry
throw/speed/color path was traced in scene `0x01`.

## Verified (cold boot of `build/ABL_ALLMODS.cue`, isolated instance)
Booted clean (no crash → rebased caves are boot-safe); all three installed & disjoint in RAM:
- golddrop hook `0x800592A4 → J 0x80081100`; grain HUD `0x80052b40 → J 0x8007f314`;
  grain emblem `0x80055008 → J 0x8007f338`; Blackberry throw `0x80047170 → J 0x80081190`,
  spawner speed hook `0x8005a0f0 → J 0x800810c0`, and power hook `0x80047228 → J 0x800813b0`.
- Caves populated; Blackberry private descriptor `0x80081234` present; native descriptor
  `0x80082030` preserved; grain threshold `sltiu ...,30`.
- Final EXE embedded byte-exact at LBA 23, SHA-1 `24e025a3c58baab15d193a18ad960a274c727f4b`;
  code lane patched EXE changed 926 bytes before the Training asset lane layered its SCUS caves.
- Runtime throw probe: forcing equip index `5` and pressing Square hit `CAVE_THROW` once,
  `CAVE_SPEED` nine times, and the contact-object color store wrote `0x2c2b051a`.

## Adding a mod
- **Code mod:** author `mod/mods/<name>.asm` (self-contained, base-relative to a boot-safe run)
  + optional `mod/caves/<name>.c`; add an entry to `registry.CODE_MODS`; list it in `mods.yaml`.
- **Asset mod:** implement `stage_patch(pristine_bytes, params) -> patched_bytes` (size-preserving)
  in a `tools/*` module; register in `registry.ASSET_MODS` with its target file; list in `mods.yaml`.

## Size-changing assets
Size-changing asset edits (RAW growth, `LEVEL.DAT` append/delete) route through the autolayout
LBA reflow. This is now used by Training board images, FLIK emblem replacements, and
`training_word_pickups` (`LEVEL07/LEVEL1.DAT` grows from 62 to 66 type-0x3f entries).

## Training pickup word
`training_word_pickups` is a multi-file asset stager. It targets the user-facing Training level
(LEVEL00 / scene `0x11`) but edits the in-world pickup files stored under the retail `LEVEL07`
folder:
- `LEVEL07/LEVEL1.DAT`: original entries 50-53 become T/R/A/I; appended entries 62-65 become
  N/I/N/G.
- `LEVEL07/LEVEL.RAW` chunk 11 and `LEVEL07/LEVEL1.RAW` chunk 12: generated 24x24 T/R/A/N/G face
  tiles are written into unused pickup-atlas UVs for reference, and native-style 8-frame spin
  strips are baked into rows T/R/A/I/N/G = `0x68/0x80/0x98/0xb0/0xc8/0xe0`.
- `SCUS_942.88`: scene-gated collection/visual/compare hooks keep all non-Training FLIK logic at
  the native four-bit `0x0f` gate; an animated helper at `0x800813ac` supplies per-entry/per-frame
  UVs to the projector hook using VSync counter `0x8007fccc`. Helper descriptor/row data lives at
  `0x80081580`. Final cave map: throw return delay-slot nop `0x800811bc`, collection
  `0x800811c0`, visual helper `0x800813ac`, visual gate
  `0x80081430`, compare `0x80081488`, helper data `0x80081580`.

Do not use `LEVEL07/LEVEL1.BIN` `0x800B4A30..0x800B4A90` for this helper. That range looks like
end slack in the raw file, but the Training tutorial engine uses it as runtime state; `0x800B4A50`
is the per-step timer. An earlier draft that wrote there reproduced the Training blank-screen
failure after pressing X.

Also do not use resident `0x8007FBC8` for the Training visual gate. It looked zero in the EXE image
but was overwritten during Training scene load (`0x00000100`, `0x02000400`, ... live at the hook
target), so the projector hook jumped into data and hit the null trap. Moving the visual gate to
the Blackberry/Fastberry tail at `0x80081430` fixed the load.

Also do not use resident `0x8007F130..0x8007F16F` for the visual helper. The helper's UV table
overlapped live retail word `0x8007F16C`; a later Training read around `0x800616C0` used that
clobbered value and crashed. The fixed helper data is at `0x80081580`, with descriptor/table offsets
`+0x24`/`+0x30`; the stale `+0x2c`/`+0x38` offsets produced horizontal colored-band glyphs.

Also do not put Training collection code at `0x800811BC`. Blackberry `CAVE_THROW` returns with
`j 0x80047178` at `0x800811B8`, so MIPS executes `0x800811BC` as that jump's delay slot. The
old collection cave began with `lbu v0,0(s3)` there and crashed berry throws in the throw-register
context. The fixed build leaves `0x800811BC` as `nop` and starts a compact 0x50-byte collection cave
at `0x800811C0`; entries 50-53 use the native F/L/I/K bit already carried in `a0`, while entries
62-65 use `a0 << 4`.

The first custom-glyph visual pass also failed because the native F/L/I/K slots are not merely
static 24x24 texture cells. During gameplay the engine repeatedly uploads narrow `6x24` VRAM
rectangles into the physical cells behind those UVs; the reused native I looked right only because
it reused a live-updated native slot. Custom static UVs like `(192,112)` and `(192,136)` sampled
unrelated flower/background texels. The fix is to bake native-looking 8-frame strips and have the
helper compute `u = ((0x8007fccc >> 3) & 7) * 24`, then choose the row from the `TRAINING` row table.
The helper needs explicit R3000 load-delay `nop`s after both `lw` and `lbu`; without them it used a
stale row value and selected the wrong strip.

The next visual probe found the strip rows were written one RAW chunk late. The live full-page upload
to VRAM `x=640,y=0,width=64,height=256` matches `LEVEL07/LEVEL.RAW` chunk 11 and
`LEVEL07/LEVEL1.RAW` chunk 12; chunks 12/13 are not the pickup page. Save states such as
`visual_FLIK_garbage.sav` preserve their captured VRAM, so use a cold boot/movie replay to verify
texture-source fixes.

Build verification on 2026-07-06: `python3 mod/build.py --mods mod/mods.yaml --out
build/ABL_ALLMODS --force` completed, `mkpsxiso` rebuilt the auto-layout disc, and the builder
verified every staged file embedded in `build/ABL_ALLMODS.bin`. Output bin SHA-256:
`6a3a1a5579a41f2f12ae9121d0d277c209b31ff8d6b979bd9841ccd0e67743ea`. Isolated DuckStation movie
verification reached Training scene `0x11` at normal gameplay PC `0x8004fea4`; legacy `blackberry_throw_test.movie.json`
hit `CAVE_THROW` at frame 4688, stepped through `0x800811B8/0x800811BC`, and returned to
`0x80047190` instead of the old `PC=0x000000a0` null trap.

## GUI — ABL Mod Studio (`tools/mod_studio_gui.py`)
`python3 tools/mod_studio_gui.py` — a Tkinter front-end to this manifest. **UX (chosen
2026-07-04):** a global **Gameplay mods** section (checkboxes for `registry.CODE_MODS`) +
a **level selector** with **category panels** (Signs & Voice / Music / SFX). Signs & Voice
uses **paired rows** — each board state = `[sign image] + [NPC voice clip]` side by side —
matching the training-board workflow (swap the picture and the line it triggers together).
- Reads/writes `mod/mods.yaml` (Load/Save); **Build disc ▶** runs `mod/build.py --mods`,
  streaming output to the log. **Extract current sign (live)** calls `training_board_edit.py`.
- **Status badges** per panel: gameplay mods = *builds now*; asset panels whose stager isn't
  registered in `ASSET_MODS` = *saved to manifest (stager pending)* and are **skipped at build
  with a log note** (never a silent no-op). Panels light up as each stager lands.
- Why level-selector-panels over 15 level tabs: scales without tab explosion and keeps the
  sign↔voice pairing on one screen. Manifest gains `asset_mods[].level` + `params` for this.
- **Organized by IN-GAME level, not disc folder.** Retail folder labels do not always match the
  user-facing level label. Training is scene `0x11` / LEVEL00 in menus and notes, while several
  in-world Training resources used by current mods live under `LEVEL07` (`LEVEL07/LEVEL1.RAW`,
  `LEVEL07/LEVEL1.BIN`, and the pickup table/atlas files). The Anthill/LEVEL01 routes remain
  separate.

## Related
[[HUD letter glyphs and word swap]] · `mod/README.md` · `mod/build.py` · `mod/mods/registry.py` ·
memory [[mod-golddrop-on-nongold-kill]] · [[berry-equip-throw-arm-chain]] · [[grain-hud-total-mod]]
