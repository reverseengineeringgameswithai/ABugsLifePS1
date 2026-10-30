---
kind: experiment
id: EXP_2026-08-04_phase4_e16_resource_lifetime
date: 2026-08-04
row: E16_streaming_overlays
status: solved
confidence: confirmed
systems: [SYS_registered_chunk_image_resources]
functions:
- FUNC_8003A318_high-heap_loader_+_LEVEL.RAW_decompress_orchestrator
- FUNC_8003C8BC_level_texture_stage
memory:
- MEM_8009B4E8_registered_chunk_table_0x30_0x57
- MEM_8009C170_registered_chunk_table_0x28_0x2F
- MEM_800A6450_registered_chunk_table_0x58_0x5F
artifacts:
- analysis/phase4_e16_resource_lifetime.json
tools:
- tools/phase4_e16_resource_lifetime.py
gates: tests/test_phase4_e16_registered_chunks.py
---

# EXP 2026-08-04 — Resource ownership and lifetime for the registered chunk tables

## The question

E16's `missing` field lists **"resource ownership + lifetimes"** as untouched.
The registered-chunk tables are the sharpest place to ask it: they hold raw RAM
pointers into decompressed chunk storage with no refcount, no size and no owner
field, so their lifetime is entirely a property of *who zeroes them and when*.

Concretely: **when the game leaves the frontend for a gameplay level, are the
frontend's registered pointers cleared, or left pointing into memory the next
load reuses?**

## Method

Replay `E02_FreshLoad_Clover` (from-boot, Interpreter — boot → memory-card load →
level select → Clover Forest, so it *crosses a load boundary*) with `readwrite`
watches on the three occupied table windows, **and** snapshot the raw table
contents every 200 frames.

Events alone cannot answer this: a slot that is populated and then never touched
again produces no further events, which is indistinguishable from a slot that was
never populated. The periodic snapshots give the occupancy timeline; the events
give the writers.

## Result — an ownership asymmetry

```
frame   populated slots   scene
  800         0            624
 2000         2              0
 3600        38              0     <- frontend fully loaded
 4800        36              7     <- Clover Forest; only 2 slots released
 5400        36              7
```

The loader's init zeroes the **0x28–0x2F** and **0x58–0x5F** tables on every load
(`0x8003a3bc`, `0x8003a3c0`). **Nothing clears the 0x30–0x57 table.** All 36 of
its frontend registrations survive into gameplay.

## Result — the survivors are genuinely dangling

"Survives" is not yet "dangling", so the pointers were validated rather than
assumed. A chunk's subtype marker is a `u32` at its own offset 0, so a surviving
slot whose target still reads back the marker it was registered under is
*stale but intact*; one that does not points at reused memory.

**0 of 36 read back their marker. All 36 are overwritten.** They point into
`0x800BE670 .. 0x80181E44` — the high heap — which the gameplay load has filled
with its own data (`0x865a0000`, `0x006e6e6e`, `0xfee8fe6d`, …).

## What this means

Retail is safe **only because nothing calls the upload path for markers
0x30–0x57 outside the frontend**. The safety is positional, not structural:
there is no validity check anywhere on the path. `level_texture_stage(marker)`
would happily fetch a dangling pointer, read a garbage `u16` width/height/
palette_bytes out of gameplay data, and hand the result to `LoadImage` — a
VRAM DMA sized by those garbage fields.

**For modding this is a live hazard.** Any mod that reuses the frontend's image
upload path during gameplay — a natural thing to want for custom HUD or menu art
— must re-register the chunk first, because the table still looks populated.

## Scope limits

- One movie, one transition (frontend → Clover Forest). Whether a
  *gameplay → gameplay* transition behaves the same is **not tested**.
- Whether the 2 slots that *were* released are released deliberately or as a
  side effect of the other two tables' clear is not established; they belong to
  the tables the loader does clear.
- The heap allocator itself (where chunk storage comes from, whether it is a bump
  allocator reset per load) is **not** characterised here — only the observable
  fact that the region is reused.

## Reproduce

```bash
python3 tools/phase4_e16_resource_lifetime.py --port 23472
python3 -m pytest tests/test_phase4_e16_registered_chunks.py
```

## Related

- [[EXP_2026-08-04_phase4_e16_registered_chunk_consumers]] — who reads the tables
- [[SYS_registered_chunk_image_resources]]
