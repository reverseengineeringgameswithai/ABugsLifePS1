---
kind: experiment
id: EXP_2026-08-04_phase4_e16_registered_chunk_consumers
date: 2026-08-04
row: E16_streaming_overlays
status: solved
confidence: confirmed
systems: [SYS_registered_chunk_image_resources]
functions:
- FUNC_8003C8BC_level_texture_stage
- FUNC_8003C388_vram_upload_wait
memory:
- MEM_8009B4E8_registered_chunk_table_0x30_0x57
- MEM_8009C170_registered_chunk_table_0x28_0x2F
- MEM_800A6450_registered_chunk_table_0x58_0x5F
artifacts:
- analysis/phase4_e16_registered_chunks.json
- analysis/phase4_e16_table_read_watch.json
tools:
- tools/phase4_e16_table_consumers.c
- tools/mips_ea_window.c
- tools/phase4_e16_table_read_watch.py
- tools/phase4_e16_image_header.c
- tools/phase4_e16_registered_chunks.py
- tools/phase4_e16_decode_registered_image.py
gates: tests/test_phase4_e16_registered_chunks.py
---

# EXP 2026-08-04 — Who reads the LEVEL.RAW chunk pointer tables?

## The question

E16's own named next step. The LEVEL.RAW loader registers 46 chunks (subtype
markers `0x28..0x5F`) by pointer into three tables and never interprets them, so
their format belongs to whatever reads `TABLE[marker]`. Find those readers.

## What happened, in order

**1. A static scan said the tables are never read — confidently and wrongly.**

`tools/phase4_e16_table_consumers.c` matched every load/store whose displacement
equals a table's offset from a `lui`, with `lui 0x800A` confirmation. Result:
3 stores, 0 reads. I widened it — every `.BIN` on the tree (30 files) plus the
resident EXE, both the `addiu`/`ori` base-formation forms, and a check that the
32-bit table addresses never appear as *data* constants anywhere. Still 3 stores,
0 reads. I also argued `$gp`-relative access is impossible (`$gp` = 0x80081D98;
all three tables are >0x19000 away, outside a signed 16-bit displacement).

The single apparent hit in `FMV/FMV.BIN` is a data table of ascending addresses
(`0x800B6400, 0x6410, 0x6420, …`) whose low half collides; the upper half is
`0x800B`, not `0x800A`.

That is a thorough search. Its conclusion — "written but never read" — was false.

**2. A live watch found them immediately.**

`tools/phase4_e16_table_read_watch.py` armed `readwrite` watches on the three
windows and replayed `E02_FreshLoad_Clover` (from-boot, Interpreter, boot →
memory-card load → level select → Clover Forest), chosen because all 46 chunks
live in LEVEL00. Arming `readwrite` rather than `read` makes the loader's own
registration stores a **positive control** in the same run, so "no reads" could
never be reported from a run where nothing engaged.

**3. The first live run was mine to get wrong, and the control caught it.**

Run 1 watched `DISP_BASE..+160`. The registration stores never fired. The
control failed loudly instead of yielding a clean-looking negative — because the
slot is `DISP_BASE + marker*4` using the **raw** marker, so the occupied window
starts 192 bytes above the base. I had been watching 160 bytes entirely below
the table, where an unrelated global sits (read as an s16 triple at +0/+2/+4 by
`0x80060858`/`0x800608bc`/`0x80060928`).

Run 2, on the corrected windows: **234 writes, 30 reads, nothing dropped**, and
every table read by exactly one site.

**4. Why the static scan could never have worked.**

The consumers *index* the table:

```
lui  $at, 0x800A
addu $at, $at, index
lw   $v0, DISP($at)
```

so `DISP` is not the table base. The 0x30–0x57 reader uses `-19032`, just
outside the `[-19224, -19064]` window my scan derived from the base. This is a
general blind spot, so the disassembly window built to diagnose it
(`tools/mips_ea_window.c`) resolves and labels `[INDEXED]` effective addresses
for reuse.

**5. The consumers define the format.**

| table | reader | in function | reaches |
|---|---|---|---|
| 0x8009C210 | 0x8003c3c0 | `vram_upload_wait` 0x8003c388 | `LoadImage` 0x800628c0 |
| 0x8009B5A8 | 0x8003c920 | `level_texture_stage` 0x8003c8bc | `level_texture_upload` 0x8003cc58 |
| 0x800A65B0 | 0x8003c5ec | `vram_upload_wait` 0x8003c388 | `LoadImage` 0x800628c0 |

Two access patterns → two header families (full layouts in
[[SYS_registered_chunk_image_resources]]). Checking those consumer-derived laws
against the bytes: **46/46 exact**, 40 chunks at 8bpp, 3 at 4bpp, 3 at 16bpp.

**6. Rendered, to be sure.**

A size law can be satisfied by a wrong-but-consistent reading, so I decoded
several. Marker `0x30` is a menu icon (radio and music notes on a branch over a
green key colour); marker `0x43` is the memory-card UI text atlas — *"please
wait / load / save / exit / 1 block used / not an "a bug's life" save game /
press ○ to load"*; family-A marker `0x28` is the 320x256 title screen. The
palette is 256 × **RGB888** on disc, converted on upload. Renders are not
committed (copyrighted art); `tools/phase4_e16_decode_registered_image.py`
regenerates them.

## Corrections banked

- **My own correction was over-corrected.** Earlier the same day I replaced
  "all 74 unknown chunks are images" with "the 46 pointer-registered ones are
  NOT images — dimension-shaped u16s are not evidence when the code never reads
  them as one." The *reasoning* was sound and the conclusion was wrong: they are
  images, read by a later consumer, using exactly those dimension fields. "No
  interpreter **here**" is not "no interpreter." Recorded in
  `analysis/phase4_e16_chunk_census.json` under
  `REGISTERED_CHUNKS_RESOLVED_2026-08-04`.
- **`tools/launch_repro_playback.sh` printed a hardcoded "CachedInterpreter"** in
  its READY banner regardless of `--execution-mode`. In a launcher whose entire
  purpose is CPU-mode matching, a correct Interpreter launch reading back as the
  one mode that cannot be traced is a trap. Fixed to report `$EXEC_MODE`.

## What this does not settle

- ~~How the 4bpp/8bpp split reaches `level_texture_stage`~~ — **closed the same
  day.** It *does* read `+10`, at `0x8003cb54`, 0x298 bytes past the table fetch
  (which is why a short window missed it), and uses it to rewrite the VRAM rect
  width: `w>>1` for 8bpp, `(w+3)>>2` for 4bpp. My stated lead, `andi $v0,$v0,3`
  at `0x8003c954`, was **wrong** — that is an alignment test (`or $v0,$s0,$a2`
  then `andi 3`) choosing between a word copy and the `lwl`/`lwr` path. Also
  established on that pass: the rect at `0x80089848`, the pixel source
  `chunk + 12 + (palette_bytes & ~1)`, the 75% palette scaling with pure green
  (`R<5 && G>=250 && B<5`) preserved as the transparency key, and two CLUT
  uploads (normal + dimmed).
- **The `u32` at `+12` in family A** is unidentified.
- **The 0x58–0x5F table's window (`0x800A65B0..0x800A65CF`) lies inside the
  documented player-state block.** Only 4 chunks campaign-wide use those markers
  and all are in the frontend, so the uses are separated in time — but the
  overlap is recorded rather than explained.
- These are frontend resources; nothing here speaks to the 28 remaining
  previously-unclassified chunks (markers 0x20 and 0x26).

## Reproduce

```bash
python3 tools/phase4_e16_registered_chunks.py            # 46/46 size law
python3 tools/phase4_e16_table_read_watch.py --port 23471 # live consumers
python3 -m pytest tests/test_phase4_e16_registered_chunks.py
```
