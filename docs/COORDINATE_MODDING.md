# Coordinate Modding — A Bug's Life LEVEL01 pickups

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)

How to move LEVEL01 pickups by editing type-`0x3f` entry coordinates in `LEVEL01\LEVEL.DAT` (fixed-size, in-place; no append/count-change/record-shift). For the DAT structure and true append see [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md); for the full entry/source-kind map see [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md); chronological tests are in [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md).

## Entry coordinate layout (type-0x3f, 0x10 bytes/entry)
- `+0x00` = X (s32 LE)
- `+0x04` = Y (s32 LE)
- `+0x08` = Z (s32 LE)
- `+0x0c` = source kind (u32 LE)
- Entry N file offset = `0x0008 + N*0x10`; X@+0, Y@+4, Z@+8, kind@+0xc.

## Runtime coordinate rule
- **runtime coordinate = file coordinate << 5** (×32). E.g. file `dy -512` → runtime `-16384`; file `dx +1024` → runtime `+32768`.

## Axis notes
- **More negative Y = upward.** Horizontal (X/Z) are full-weight in the contact test; Y is underweighted (×0x100 vs ×0x300 ≈ ⅓), which is the source of the *auto-collect* pathology on large up-moves.

## Safe movement guidance
- Avoid huge Y moves. Use moderate `dy` (e.g. -128 to -512 file units). Keep final runtime Y roughly ≥ -21000 to avoid auto-collect from a distance.
- Lean on horizontal (dx/dz) for visibility; they don't trigger the weak-Y auto-collect.
- Already-high pickups can be pushed out of render range by up-moves → verify with a horizontal-only move.
- **For berries: preserve the source kind** (only edit X/Y/Z). Changing a berry's kind deletes/replaces the berry. See warning in [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md).

## Command pattern (single-entry coordinate move)
```
python3 tools/patch_level_entry.py DAT/LEVEL01_LEVEL.DAT --entries <N> --dx <dx> --dy <dy> --dz <dz> \
    --out DAT/<OUT>.DAT      # preserves kind; only edits X/Y/Z of entry N
```
Then rebuild the image per [TOOLING.md](TOOLING.md). Worked examples (byte diffs, deltas, results) follow and in [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md).

## Confirmed movement workflows (all in-game verified)
- **Grain** (kind 0x14): file-based Y/X/Z patch; e.g. entry 0 `dy -512` raised one grain (jump to collect).
- **FLIK letters** (0x10=F, 0x11=L, 0x12=I, 0x13=K): single-letter `dy -128` safe; F also moved on X and Z.
- **Seed tokens** (0x29 orange, 0x2a blue, 0x2b green): dx/dz up to ±1024, dy down to ~-512 safe.
- **Special berries** (0x21..0x24): single-entry X/Y/Z move, kind preserved (mapping table below).

## Grain coordinate modding (recipes, scripts, cross-level catalog)
First file-based "move grain upward" recipe:
- Target file: `LEVEL01\LEVEL.DAT`
- Target grain: type-`0x3f` entry index 0 at file offset `0x0008`
- Vertical axis: Y; upward = decrease Y.
- Patch the Y s32 at file offset `0x000c`.
- Original Y bytes: `60 f2 ff ff` (`-3488`, runtime `-111616`)
- Suggested small upward edit: subtract `0x40` in file units (runtime delta `-0x800` / -2048)
- New Y value: `-3552` = `0xfffff220`
- Patched Y bytes: `20 f2 ff ff`
- Full entry after patch:
  `b2 de ff ff 20 f2 ff ff c0 11 00 00 14 00 00 00`
- Disc-image reinsertion warning: PS1 images using raw Mode2/2352 sectors generally need proper
  sector handling and EDC/ECC regeneration or a PS1-aware rebuild/reinsert tool. Do not byte-patch a
  raw image blindly unless the tool preserves/regenerates sector metadata correctly.

Repeatable patch-table tooling:
- Script: `tools/list_level_grains.py`
- Usage:
  `python tools/list_level_grains.py /path/to/LEVEL.DAT`
- The script parses DAT records using the `fcn.8001cdc0` size rules, finds type-`0x3f` records, prints
  every source-kind `0x14` grain entry, and suggests the `Y - 0x40` upward patch bytes.
- `--all` also prints non-grain entries in the type-`0x3f` record.

LEVEL01 `LEVEL.DAT` type-`0x3f` patch-table summary:
- Type-`0x3f` record count: 1
- Type-`0x3f` record file offset: `0x0004`
- Entry count in that record: `0x46` = 70
- Source-kind `0x14` entries: 50, matching the expected 50 grain count.
- Non-`0x14` entries: 20; not part of the confirmed grain constructor path.
- Grain entries occupy indices 0..49 in this LEVEL01 file. Y patch offset = `0x000c + index*0x10`.

First 10 LEVEL01 grain patch rows:
| idx | entry off | Y off | X | Y | Z | orig Y bytes | patched Y bytes |
|---:|---:|---:|---:|---:|---:|---|---|
| 0 | `0x000008` | `0x00000c` | -8526 | -3488 | 4544 | `60 f2 ff ff` | `20 f2 ff ff` |
| 1 | `0x000018` | `0x00001c` | -9241 | -2829 | 4799 | `f3 f4 ff ff` | `b3 f4 ff ff` |
| 2 | `0x000028` | `0x00002c` | -8832 | -2841 | 5795 | `e7 f4 ff ff` | `a7 f4 ff ff` |
| 3 | `0x000038` | `0x00003c` | -7709 | -3254 | 5335 | `4a f3 ff ff` | `0a f3 ff ff` |
| 4 | `0x000048` | `0x00004c` | -8194 | -3145 | 3829 | `b7 f3 ff ff` | `77 f3 ff ff` |
| 5 | `0x000058` | `0x00005c` | -9215 | -2775 | 4288 | `29 f5 ff ff` | `e9 f4 ff ff` |
| 6 | `0x000068` | `0x00006c` | -2682 | -3313 | 852 | `0f f3 ff ff` | `cf f2 ff ff` |
| 7 | `0x000078` | `0x00007c` | -5508 | -4207 | 972 | `91 ef ff ff` | `51 ef ff ff` |
| 8 | `0x000088` | `0x00008c` | 1252 | -4217 | 9906 | `87 ef ff ff` | `47 ef ff ff` |
| 9 | `0x000098` | `0x00009c` | 1789 | -4270 | 9932 | `52 ef ff ff` | `12 ef ff ff` |

Use the script for the complete 50-row patch table.

Rebuilt grain-test image:
- Tools present: `/usr/local/bin/dumpsxiso`, `/usr/local/bin/mkpsxiso` (both 2.20).
- Dump command:
  `dumpsxiso -x REBUILD/files -s REBUILD/abl.xml -l "Disney-Pixar A Bug's Life (v1.0).cue"`
- Patched only dumped workspace file:
  - backup: `REBUILD/files/LEVEL01/LEVEL.DAT.orig`
  - patched workspace file: `REBUILD/files/LEVEL01/LEVEL.DAT`
  - source patch file: `DAT/LEVEL01_LEVEL_GRAIN0_UP.DAT`
- Build command:
  `mkpsxiso -y -o ABL_GRAIN_TEST.bin -c ABL_GRAIN_TEST.cue REBUILD/abl.xml`
- Output:
  - `ABL_GRAIN_TEST.bin`
  - `ABL_GRAIN_TEST.cue`
- Verification:
  - original image `LEVEL01/LEVEL.DAT;1` at LBA 2906, file `+0x000c` = `60 f2 ff ff`
  - rebuilt image `LEVEL01/LEVEL.DAT;1` at LBA 2906, file `+0x000c` = `20 f2 ff ff`
  - cue track is `MODE2/2352`
  - original `Disney-Pixar A Bug's Life (v1.0).bin/.cue` were not overwritten.

Big visual grain-test image:
- Reason: the first `Y - 0x40` file-unit test was not visually obvious in-game.
- Input DAT: `DAT/LEVEL01_LEVEL.DAT` (original extracted DAT, not the small-patch DAT).
- Big patched DAT: `DAT/LEVEL01_LEVEL_GRAIN0_UP_BIG.DAT`
- Patch:
  - target entry: LEVEL01 type-`0x3f` grain entry index 0
  - Y file offset: `0x000c`
  - original Y: `-3488`, bytes `60 f2 ff ff`
  - big-test Y: `-4512`, bytes `60 ee ff ff`
  - file delta: `-1024`
  - runtime delta: `-32768` because runtime coordinates are file coordinates `<< 5`
- Build command:
  `mkpsxiso -y -o ABL_GRAIN_BIG_TEST.bin -c ABL_GRAIN_BIG_TEST.cue REBUILD/abl.xml`
- Output:
  - `ABL_GRAIN_BIG_TEST.bin`
  - `ABL_GRAIN_BIG_TEST.cue`
- Verification:
  - original extracted DAT `DAT/LEVEL01_LEVEL.DAT` at `+0x000c` remained `60 f2 ff ff`
  - big patched DAT at `+0x000c` = `60 ee ff ff`, same file size as original
  - original image `LEVEL01/LEVEL.DAT;1` at LBA 2906, file `+0x000c` = `60 f2 ff ff`
  - small-test image `ABL_GRAIN_TEST.bin` at file `+0x000c` = `20 f2 ff ff`
  - big-test image `ABL_GRAIN_BIG_TEST.bin` at file `+0x000c` = `60 ee ff ff`
- In-game verification:
  - `ABL_GRAIN_BIG_TEST` booted successfully.
  - The patched LEVEL01 grain appeared high in the air.
  - Result: one grain visibly moved upward in-game.
  - Conclusion: `LEVEL01\LEVEL.DAT` type-`0x3f`, source-kind `0x14` entries are confirmed grain
    placement records, and the file-based DAT coordinate patch pipeline works.

Reusable grain patcher:
- Script: `tools/patch_level_grain.py`
- List grains:
  `python tools/patch_level_grain.py DAT/LEVEL01_LEVEL.DAT --list`
- Patch one grain by grain index:
  `python tools/patch_level_grain.py DAT/LEVEL01_LEVEL.DAT --grain 0 --dy -512 --out DAT/LEVEL01_LEVEL_GRAIN0_UP_MEDIUM.DAT`
- Safety behavior:
  - selects by source-kind `0x14` grain index, not raw entry index
  - requires `--out` unless `--in-place` is explicitly provided
  - verifies selected entry is source-kind `0x14`
  - verifies output size matches input
  - verifies non-in-place input remains unchanged
- Medium test DAT:
  - input: `DAT/LEVEL01_LEVEL.DAT`
  - output: `DAT/LEVEL01_LEVEL_GRAIN0_UP_MEDIUM.DAT`
  - grain index: 0, raw entry index: 0
  - entry offset: `0x000008`, Y offset: `0x00000c`
  - original XYZ: `-8526 -3488 4544`
  - new XYZ: `-8526 -4000 4544`
  - original Y bytes: `60 f2 ff ff`
  - patched Y bytes: `60 f0 ff ff`
  - file delta: `-512`
  - runtime delta: `-16384`

Medium visual grain-test image:
- Purpose: a playable test between the subtle `Y - 0x40` patch and the verified big visual patch.
- Input DAT: `DAT/LEVEL01_LEVEL_GRAIN0_UP_MEDIUM.DAT`
- Rebuild workspace target replaced: `REBUILD/files/LEVEL01/LEVEL.DAT`
- Build command:
  `mkpsxiso -y -o ABL_GRAIN_MEDIUM_TEST.bin -c ABL_GRAIN_MEDIUM_TEST.cue REBUILD/abl.xml`
- Output:
  - `ABL_GRAIN_MEDIUM_TEST.bin`
  - `ABL_GRAIN_MEDIUM_TEST.cue`
- Verification:
  - original extracted DAT `DAT/LEVEL01_LEVEL.DAT` at `+0x000c` remained `60 f2 ff ff`
  - medium patched DAT at `+0x000c` = `60 f0 ff ff`, same file size as original (`332824`)
  - original image `LEVEL01/LEVEL.DAT;1` at LBA 2906, file `+0x000c` = `60 f2 ff ff`
  - medium image `ABL_GRAIN_MEDIUM_TEST.bin` at LBA 2906, file `+0x000c` = `60 f0 ff ff`
  - image size is `738285744` bytes, matching the original rebuilt/test image size.
- In-game verification:
  - `ABL_GRAIN_MEDIUM_TEST.cue` booted successfully in emulator.
  - The patched LEVEL01 grain moved upward by a playable/moderate amount.
  - Walking underneath did not collect it.
  - Jumping collected it.
  - Grain counter increased by 1.
  - No crash/load issue reported.
- Result: Task A, "make a playable grain-position mod", is COMPLETE for a single LEVEL01 grain.

Cross-level grain coordinate catalog:
- Script: `tools/catalog_level_grains.py`
- Normalized extracted DAT copies live under `DAT/` as `LEVEL##_LEVEL.DAT` and `LEVEL##_LEVEL1.DAT`.
  `DAT/LEVEL01_LEVEL.DAT` is kept as the original extracted file; the medium-patched rebuild
  workspace file was not copied over it.
- Catalog command:
  `python tools/catalog_level_grains.py 'DAT/LEVEL[0-9][0-9]_LEVEL.DAT' 'DAT/LEVEL[0-9][0-9]_LEVEL1.DAT' --csv DAT/grain_coordinate_catalog.csv --md DAT/grain_coordinate_catalog.md`
- Outputs:
  - CSV: `DAT/grain_coordinate_catalog.csv`
  - Markdown: `DAT/grain_coordinate_catalog.md`
- CSV columns:
  `file,dat_record_offset,grain_index,raw_entry_index,entry_offset,y_offset,x,y,z,source_kind,orig_y_bytes,patch_y_minus_0x40_bytes`
- Per-file source-kind `0x14` grain counts:
  - `DAT/LEVEL00_LEVEL.DAT`: 0; no type-`0x3f` record.
  - `DAT/LEVEL01_LEVEL.DAT`: 50.
  - `DAT/LEVEL01_LEVEL1.DAT`: 50.
  - `DAT/LEVEL02_LEVEL.DAT`: 50.
  - `DAT/LEVEL02_LEVEL1.DAT`: 50.
  - `DAT/LEVEL03_LEVEL.DAT`: 50.
  - `DAT/LEVEL03_LEVEL1.DAT`: 50.
  - `DAT/LEVEL04_LEVEL.DAT`: 24; fewer than the expected 50.
  - `DAT/LEVEL04_LEVEL1.DAT`: 0; type-`0x3f` exists but has no source-kind `0x14` entries.
  - `DAT/LEVEL05_LEVEL.DAT`: 50.
  - `DAT/LEVEL05_LEVEL1.DAT`: 50.
  - `DAT/LEVEL06_LEVEL.DAT`: 50.
  - `DAT/LEVEL06_LEVEL1.DAT`: 0; type-`0x3f` exists but has no source-kind `0x14` entries.
  - `DAT/LEVEL07_LEVEL.DAT`: 50.
  - `DAT/LEVEL07_LEVEL1.DAT`: 50.
  - `DAT/LEVEL08_LEVEL.DAT`: 50.
  - `DAT/LEVEL08_LEVEL1.DAT`: 0; no type-`0x3f` record.
  - `DAT/LEVEL09_LEVEL.DAT`: 50.
  - `DAT/LEVEL10_LEVEL.DAT`: 50.
- Total cataloged source-kind `0x14` grain rows: 724.
- Result: Task B, "generate cross-level grain coordinate tables", is COMPLETE.
- Anomalies / caveats:
  - Several type-`0x3f` records also contain non-`0x14` source kinds; these are not confirmed grain
    entries and should not be patched as grain placements without more constructor-path evidence.
  - `LEVEL04_LEVEL.DAT`, `LEVEL04_LEVEL1.DAT`, `LEVEL06_LEVEL1.DAT`, and `LEVEL08_LEVEL1.DAT` do not
    expose 50 source-kind `0x14` rows in this catalog. Possible explanations include level variants,
    split/alternate placement data, or nonstandard grain generation for those scenes.
- Deferred: do not investigate the LEVEL00/LEVEL04/LEVEL06/LEVEL08 grain-count anomalies yet.
- Next mod target: move to FLIK-letter coordinate mapping and find a first FLIK coordinate patch path.

### Mod implications
- Immediate RAM-state mods now possible (owned-disc testing in emulator):
  - grain: poke the progress-struct grain field (HUD mirror at 0x800a65a1) — find writer first.
  - FLIK: set the collected flag (record+0x1b) of any of the 4 records to mark a letter collected.
- COORDINATE mod for grain now has a file path through `LEVEL0N\LEVEL[M].DAT` type-`0x3f` entries.
  FLIK letter spawn coords are still not mapped. This remains distinct from the visual sprite pool
  (`0x8009c870`).


## FLIK COORDINATE MODDING — CONFIRMED ✅
DAT type-0x3f source kinds 0x10..0x13 (= F/L/I/K) are the visible FLIK letters and are coordinate-
moddable via the same file-patch pipeline as grain. All confirmed in-game (single-letter, small deltas):
| letter | kind | LEVEL01 entry | test image | delta | result |
|---|---|---|---|---|---|
| K | 0x13 | 53 | ABL_FLIK_K_SMALL_TEST | dy -128 (rt -4096) | passed; only K moved, no auto-collect |
| I | 0x12 | 52 | ABL_FLIK_KIND12_SMALL_TEST | dy -128 | passed; only I moved |
| L | 0x11 | 51 | ABL_FLIK_KIND11_SMALL_TEST | dy -128 | passed; only L moved |
| F | 0x10 | 50 | ABL_FLIK_F_TINY_TEST / _MORE | dy -64 / dy -256 | passed; F moved, 4/4 |
| F | 0x10 | 50 | ABL_FLIK_F_SIDE_TEST / _Z_SIDE / _Z_SIDE_UP | dx+512 / dz+512 / dy-256+dz+512 | passed; F⟂grain, 4/4 |
- Method: patch DAT entry+0x4 (Y), +0x0 (X), +0x8 (Z); runtime = file<<5; tool `tools/patch_level_entry.py`.
- Caveat: contact walker underweights Y (×0x100 vs ×0x300) → keep Y deltas small (the all-letter
  `dy -2048`/rt -65536 broke things). F (0x10) has extra logic but tolerates small/moderate moves.
- Note: horizontal-only F moves make F appear lower in-game (visual/runtime grounding, NOT a Y data
  change) — correctable with a small explicit `dy` up. (Exact images/deltas/results above are the record.)


### SEED-POWER TOKEN SYSTEM — CONFIRMED (LEVEL01, all three kinds) ✅
ABL_SEEDTOKEN_KIND2B_UPSIDE_BIG_TEST passed in-game (user): "The green token moved. Collectable. UI
changed. No other movement." → kind 0x2b = GREEN seed token. Coordinate movement confirmed for all
three LEVEL01 seed-token kinds; each updates its own seed-power meter on pickup; no unrelated movement.
Build details (0x2b): DAT `DAT/LEVEL01_LEVEL_SEEDTOKEN_KIND2B_UPSIDE_BIG.DAT`, image
`ABL_SEEDTOKEN_KIND2B_UPSIDE_BIG_TEST.bin/.cue`, entry 58, X -1772→-748 (`14 f9 ff ff`→`14 fd ff ff`,
dx +1024, rt +32768), Y -150→-662 (`6a ff ff ff`→`6a fd ff ff`, dy -512, rt -16384), Z unchanged -10407
(`59 d7 ff ff`); grain/FLIK/other tokens/checkpoints unchanged.

Confirmed seed-token mapping (LEVEL01, DAT type-0x3f, entry layout +0/+4/+8 = X/Y/Z<<5, +0xc = kind):
| kind | color  | entries  | handler     | counter      | powered obj | coord confirmed |
|------|--------|----------|-------------|--------------|-------------|-----------------|
| 0x29 | orange | 63/64/65 | 0x800542f4  | 0x800a6598   | 0x16        | yes, entry 63   |
| 0x2a | blue   | 60/61/66 | 0x8005433c  | 0x800a6599   | 0x17        | yes, entry 60   |
| 0x2b | green  | 58/59/62 | 0x800543b8  | 0x800a659a   | 0x19        | yes, entry 58   |
Power-up routine fcn.8003e760(objIndex, level) progressively powers the seed object; HUD meters drawn by
fcn.800526f4 loop @0x80052fa4 reading 0x800a6598+i. Mod-safe deltas (in-game verified): horizontal
dx/dz up to ±1024 (rt ±32768) fine; vertical dy down to -512 (rt -16384, grain-MEDIUM magnitude) with no
auto-collect; avoid extreme Y (rt -65536 broke FLIK). Literal in-game token NAME still UNKNOWN.

Solved pickup systems (all DAT type-0x3f, coordinate-moddable, runtime = file<<5):
| pickup system | source kind(s) | coord confirmed | state/HUD            | notes                    |
|---------------|----------------|-----------------|----------------------|--------------------------|
| grain         | 0x14           | yes             | 0x800a65a1 (count/50)| count pickup             |
| FLIK          | 0x10..0x13     | yes             | FLIK bit/progress, 0x800a6597 | letters F/L/I/K   |
| seed tokens   | 0x29..0x2b     | yes             | 0x800a6598..0x659a   | orange/blue/green tokens |
(0x21..0x24 = FLIK trigger/markers, not visible; 0x30 = checkpoint/trigger candidate, not a token.)


## ✅ SPECIAL BERRY / POWER-UP MAPPING COMPLETE — LEVEL01
All four special-berry/power-up pickups in LEVEL01\LEVEL.DAT (type-0x3f source kinds 0x21..0x24) are now
mapped and individually confirmed coordinate-movable in-game:

| entry | kind | marker (`0x800a6597`) | sound | **berry / power-up (CONFIRMED in-game)** |
|------:|-----:|----------------------:|------:|------------------------------------------|
| 56 | 0x21 | 2 | 0x36 | **Green Berry / Homing Berry** |
| 54 | 0x22 | 3 | 0x38 | **Gold Berry** |
| 55 | 0x23 | 1 | 0x35 | **Blueberry / Superberry** |
| 57 | 0x24 | 4 | 0x37 | **Purple Berry / Mega Homing Berry** |

Facts established:
- **All four berry kinds 0x21..0x24 are coordinate-editable** via fixed-size type-0x3f entry edits
  (same pipeline as grain 0x14 / FLIK 0x10..0x13 / seed tokens 0x29..0x2b). No append, no count change, no
  record shift — single-entry in-place X/Y/Z patch.
- **Runtime coordinates = file coordinates << 5.** The entry-56 move was `dx +1024, dy -512` (file units) →
  runtime deltas `+32768`, `-16384`. (General rule for all these pickups; entry layout +0=X +4=Y +8=Z,
  s32 LE; kind byte at +0xc.)
- **Source kind MUST be preserved.** Changing a berry's kind does NOT relocate it — it deletes/replaces the
  associated berry behavior. The earlier marker-sacrifice test (54/55/57 → 0x29) proved this by removing the
  Gold / Blueberry / Mega-Homing berries from the level. The `0x800a6597` marker write is the berry's effect
  trigger; the visible berry model is selected by the kind.
- **WARNING (still in force): entries 54..57 are NOT safe sacrificial slots for unrelated objects.** They
  back real special berry / power-up pickups (kinds 0x21..0x24). Overwriting their kind removes a berry.
  For adding NEW objects, use relocation-aware true append (`tools/dat_reloc.py`), not berry-slot sacrifice.

Remaining uncertainty: the in-game *display names* are the user's identification (Disney/Pixar A Bug's Life
power-up berries); the engine has no berry-name strings at these handlers, so the name↔kind binding rests on
the in-game observations (all four now individually confirmed by moving one entry per ISO). The marker
value's downstream gameplay effect (homing vs gold vs super vs mega-homing behavior) lives in the overlay /
marker consumer and was not separately disassembled — not needed for coordinate modding.


---

**Related docs:** [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md) · [LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md) · [TOOLING.md](TOOLING.md) · [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)
