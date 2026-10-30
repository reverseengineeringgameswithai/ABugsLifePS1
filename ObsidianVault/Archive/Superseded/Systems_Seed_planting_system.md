---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Seed planting system.md
aliases:
  - "Seed planting system"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Seed planting system.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Seed_planting_system.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Seed planting system
type: system
status: runtime mapped; on-disk source = COMPRESSED level data (editor needs LZ codec)
confidence: CONFIRMED (runtime), CONFIRMED (separate from type-0x3f), LIKELY (on-disk compressed)
tags: [system, seed, planting, gameplay, leveldata, leveleditor]
---

# Seed planting system

> The interactive "seeds" Flik plants — a SEPARATE object/placement system from the type-0x3f
> pickups (grain/FLIK/berries/tokens/gems). This is why none of the pickup records ever matched a
> seed. Reverse-engineered while finding how to relocate a seed for a level editor.

## What a seed IS (operator-confirmed gameplay)
A seed is **not a collectible reward** — it is a **reusable planting point**. Flik can:
- **carry** it, **recolor** it with collected seed tokens, and **activate** it by **jumping on it** to
  **grow a plant**.
- The plant grown depends on the seed's **current colour** + the **number of matching seed tokens**
  collected in that level.
- Plants give **traversal** (mushrooms, leaf platforms, dandelions, cannons), **combat** (berry
  shooters, mines), or **power-ups** (shield, health, invincibility, stronger berries).
There are **multiple seeds per level**, at fixed world locations, that **"pop out of the ground"
(with gravity) when Flik enters their vicinity**.

## Runtime structures (CONFIRMED)
- **Per-seed base struct** (one per seed; the spawner selects the active one via `LW(gp+0x694)`):
  `+0x04/+0x08/+0x0c` = seed world **X/Y/Z** (runtime; file = `>>5`). Examples:
  seed A `0x800a0ae8` = `(197888,…,560800)` (LEVEL01 start-area seed);
  seed B `0x800a07d0` = `(-35145,…,516491)` (a different LEVEL01 seed).
- **LIVE MOVE HANDLE:** edit the active seed's base `+0x04` (X) / `+0x0c` (Z) — **no per-frame
  writer, persists across save/reload**. (Y bobs/falls under gravity, so it's reasserted.) Demonstrated
  in-emulator: LEVEL01 start seed slid far-right → centre by editing `0x800a0aec`.
- **Spawner** `fcn @caller 0x8004753c` (loop around `0x800474e0`): when Flik is near, pops the seed's
  pieces via `contact_alloc` with **ctors 0x7d–0x80**, position = `base[+4/8/c] + (scriptByte−0x80)<<5`,
  consuming per-piece bytes from the **level-script cursor `0x800822f4`** (same cursor the type-0x3f
  pass uses). Gates on `0x800910a3` / `0x800a655c`.
- **Loader** `fcn @0x80049c40..` : at level load, copies a source record `t1` into the base struct:
  `base+0x4 = SRC[0]<<5` (X), `base+0x8 = SRC[4]<<5` (Y), `base+0xc = SRC[8]<<5` (Z), plus
  id/flags at `+0xd/+0x10/+0x11/+0x12`. Runtime source tables sit in the **`0x80094a38–0x8009511c`**
  region.

## On-disk source — COMPRESSED (the level-editor finding)
- The seed placement is in **`LEVEL01\LEVEL.DAT`**, but in a **different, COMPRESSED section** from the
  type-0x3f pickups (those are uncompressed at file `0x4–0x448` and directly patchable).
- **Proof:** the seed's clean coords (`6184,111,17525` file / `197888,3552,560800` runtime) do **NOT**
  appear anywhere in `LEVEL.DAT` as a plain int32 triple/pair. They exist only in **RAM after
  decompression**. The runtime table head (`0x80094a38`) is written by a **BIOS memcpy (`0xbfc02bb4`)
  driven by `0x8003b92c`**, which lives in the **level-load/decompression path** (near the known LZ
  decompressor `fcn.8003a318` / `fcn.8001a1dc`).
- **Editor implication:** unlike pickups, a level editor must **decompress the LEVEL.DAT seed section,
  edit the seed record (X/Y/Z file coords), recompress** — i.e. it needs the project's **LZ codec
  (G24)**. The plain `6184` found at `LEVEL.DAT 0x4a9e4` is **coincidental/geometry**, not the record.

## On-disk seed table — DECODED (LEVEL.RAW chunk 31) ✅ G32
The seed source table is **LEVEL.RAW chunk 31** (0-indexed; `decomp_off 0x965d4`, word0 1796). Full
decompressed dump cached at `tools/LEVEL_RAW_decompressed/` (+ `chunk_index.json`).
- **Array of 0x1c-byte (28) records**, starting at chunk-local `0x4`, **31 active** (#0–#30; rest zero-padded).
- Record layout: `+0x00` X · `+0x04` Y · `+0x08` Z (int32 **file** coords; runtime = `<<5`) · `+0x0c..0x1b`
  16 metadata bytes (id/colour/flags). Loader `0x80049c40` copies XYZ`<<5` into the base struct.
- **Meta bytes decoded (2026-07-02, HRE-004)**: `+0x0e` = **seed colour lane** (0..4 = brown/blue/
  green/purple/yellow token lanes) and `+0x0f` = **plant OVERRIDE byte** (`(count−1)<<4 | colour`;
  nonzero forces a specific plant regardless of tokens — live-confirmed via runtime poke). Both map
  1:1 into the runtime record (`seed_actor+0x80`, verified records #19/#26), so per-seed colour and
  forced plant are **disc-editable** with this same chunk-31 pipeline. Full selection chain
  (spawner `FUNC_8005BDBC`, type table `0x8007A448`, PLANTNN.ALL binding): [[Seed plant output binding]].
- **Runtime base structs** are a parallel array: `0x800a0014 + n·0x84` (stride 0x84), one per spawned seed.
  Map base→record by coordinate (base file = runtime`>>5`, ± physics/spawn-offset jitter).
- **Stuck/rooted seeds** (base `+0x40 == 3`, can't-carry): records **#19/#21/#22/#23/#24**
  (locals `0x218/0x250/0x26c/0x288/0x2a4`) — they carry the `0b 03 … 64 38 00 19 00` metadata signature
  that crackable seeds lack. ⚠️ Several other base structs show garbage `+0x40` (e.g. 294912) until
  initialised — trust `+0x40==3` only, and **identify the seed in the player's view by Flik's position**
  (`0x800a6500` X/+4 Y/+8 Z, file = `>>5`), not by flag alone.

### ✅ In-game write-path PROVEN for BOTH seed kinds (G32, operator-confirmed)
- **Crackable** start seed (record #26, local 0x2dc) — moved X 6184→3000 → `ABL_SEED_MOVE_TEST.bin`, seen in-game.
- **Stuck** seed beside Flik (record #19, local 0x218 → base #14 `0x800a074c`) — moved (4837,−2325,2813)→
  (1000,−2325,2813) → `ABL_STUCK_SEED_TEST.bin`. Confirmed first by **live base-struct nudge** (the
  `+0x4` handle still works on rooted seeds), then committed to the file and **operator-booted from the
  rebuilt disc → seed found relocated (permanent, off-disc) ✅**. A stuck seed renders as a multi-piece
  cluster (spawner ctors 0x7d–0x80), which can read as "three seeds in one spot."
- ⚠️ Lesson: the first two stuck-seed attempts moved the wrong seed (a far-zone one, Z≈13395), invisible
  from spawn. **Always pin the in-view seed via Flik's position `0x800a6500` first**, then map to a record.
- Pipeline (layout-safe, LBA 3069 unchanged): decompress chunk 31 → edit record → `recompress_level_raw.compress_chunk`
  → splice → `tools/rebuild_with_patched_dat.py --target files/LEVEL01/LEVEL.RAW`. Verify: `tools/verify_stuck_seed_move.py`.

## Not to be confused with
- **type-0x3f pickups** ([[MEM - Type-0x3f placement record]]): grain/FLIK/berries/**seed tokens**
  (the colour items, kinds 0x29/0x2a/0x2b) / **gems** (kind 0x30). The recolour TOKENS are type-0x3f;
  the **planting SEEDS are this separate system**.
- **Tier-3 note:** [[Experiment - Tier3 native seed token relocation]] confirmed that a native orange seed token
  moved onto the Tier-3 custom floor still advances the native packed token counter (`0x800a6598`: `0x11`→`0x22`).
  So Tier-3 token counters should use native type-0x3f token objects, not cave-side generic pickup markers.
- ⚠️ Session note: an earlier attempt mistakenly moved **type-0x3f entry 57** (a "purple berry",
  kind 0x24 — the small magenta diamond) thinking it was the seed. The seed is the brown object that
  pops from the ground; its handle is the base struct above.

## Save states (operator)
`_seed_prelevel` (=_2, before load) · `_seed_start` (=_9, start, seed far-right) ·
`_seed_closeup` (=_8, Flik next to seed A) · `_seed2_closeup` (=_5, Flik next to seed B) ·
`_10` = seed A moved toward centre (live-edit demo).

## Functions
spawner caller `0x8004753c` (ctors 0x7d–0x80) · loader `0x80049c40` · base ptr `gp+0x694` ·
script cursor `0x800822f4` · decompress path `0x8003b92c` / [[FUNC_8001A1DC]] / `fcn.8003a318`.

## Next steps
- To make seed moves **permanent / editor-ready**: decompress the LEVEL.DAT seed section with the LZ
  codec, locate the seed record by its (now-known) coords, edit X/Y/Z, recompress + rebuild, verify.
- Map the exact compressed-section offset (transfer-log the CD source of `0x80094a38`).

## Related
[[Systems]] · [[Home]] · [[MEM - Type-0x3f placement record]] · [[LEVEL.DAT object pipeline]] ·
[[Finding - LEVEL.RAW is compressed]] (the codec gate for the seed editor; ground truth captured = G31) ·
[[Asset - LEVEL.RAW]] · [[Asset - LEVEL.DAT]]
- Decompilation: `src_re/source3f_dispatch_80053814.c` (pickup pass, distinct from seeds),
  `src_re/pickup_projector_800253e8.c`; codec runbook `src_re_geometry/geometry_g24_level_raw_decompressor.md` (§G31).
