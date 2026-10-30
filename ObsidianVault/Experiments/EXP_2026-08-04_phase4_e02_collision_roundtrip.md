---
type: experiment
status: complete
date: 2026-08-04
system: collision sectors and planes
phase: 4
artifacts:
  - analysis/phase4_e02_collision_roundtrip.json
  - tools/phase4_e02_collision_roundtrip.c
  - tools/phase4_e02_collision_roundtrip.py
  - tests/test_phase4_e02_collision.py
fixtures:
  - movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json
  - movies/Phase4/Interpreter/D18_thud_fight.movie.json
---

# Phase 4 E02b: the all-level collision round trip, C-implemented

## Question

E02's second half: complete record semantics, wall/ledge/hazard coverage, and
the all-level source→runtime round trip (everything was LEVEL01-proven only).

## Method

A compiled C tool (`tools/phase4_e02_collision_roundtrip.c`, `-Werror`,
self-verifying against pristine data — the operator's C-for-ASM standing rule)
independently reimplements the decoded converter FUNC_80030F60 and diffs its
prediction field-by-field against the ACTUAL runtime sector table extracted
offline from each level save. The driver sweeps every level container,
needle-searches for a reference sector's origins, and accepts only a
zero-mismatch round trip with a clean block walk.

## Results

**All 16 scenes round-trip EXACTLY** — zero field mismatches, zero malformed
blocks, every plane accounted. Bindings and per-scene detail:
`analysis/phase4_e02_collision_roundtrip.json`.

Two container families carry collision source, and this matters for modding:

| family | example | block base |
|---|---|---|
| `LEVEL*.RAW` chunk 32 (compressed) | LEVEL01/LEVEL.RAW | container offset **8** |
| `*.ALL` terrain containers (uncompressed) | LEVEL07/TERRAIN.ALL | container offset **4** |

Record-semantics laws, campaign-proven:

- **Authored prefix / runtime tail.** Each runtime table = N authored source
  records (origins `<<5` verbatim) + a runtime-REGISTERED tail with degenerate
  origins (LEVEL01: 178 + 45). Containers hold ONLY the authored prefix. The
  count global `[0x800822A0]` counts both, and is incremented **151 times** by
  `0x800316C0` during the Clover Forest load — the registration loop.
- **Flat-sector block inheritance**: geometry sectors take the running block
  position; flat sectors inherit the MOST RECENT geometry sector's block start.
- **The +0x2C/+0x2E wording tension is resolved**: runtime +0x2E (region code)
  ← src +0x2C; runtime +0x2C ← src +0x14 (same field feeding runtime +0x0C).
- **Plane census (16 scenes)**: 58,555 planes in 16,653 groups — 52,518 floors
  (normal.y<0), 5,686 ceilings, 351 vertical walls; every normal unit-length
  within authoring rounding; every block walk lands exactly on its terminator.
  Authored/runtime split campaign-wide: 3,235 authored + 720 runtime-registered
  = 3,955 sectors.

**No runtime-built exceptions remain.** Bug Bar — the last hold-out — authors
exactly **ONE** sector (`LEVEL04/LEVEL1.RAW`); its other 45 are registered at
runtime, which is the numeric signature of
[[EXP_2026-08-02_phase4_e11_dynamic_geometry]]'s per-tick arena assembly.

## CORRECTION (2026-08-04, same day, via the operator's movie)

An earlier revision of this note and of `SYS`/registry text claimed **four**
scenes (city_square, bug_bar, clover_forest, the_tree) had collision tables
that were **"runtime-BUILT — not disc-verbatim anywhere"**. That was **wrong**,
and it was wrong for two compounding reasons of my own making:

1. **Search-scope error.** The sweep covered `.RAW` (decompressed), `.DAT` and
   `.BIN` — but never `.ALL`. Three of the four scenes keep their collision
   source in the uncompressed terrain containers `TERRAIN.ALL` / `TERR1.ALL`.
2. **Bounds bug.** The C tool required all *runtime* sectors to fit inside the
   container. Containers hold only the authored prefix (Clover: 138 authored
   vs 183 runtime), so the correct container was rejected as "not located"
   even once it was in scope.

The false claim was stated with confident negative phrasing ("exists NOWHERE on
disc verbatim") on the strength of a sweep whose scope I never justified. A
negative is only as strong as the completeness of its search, and I did not
establish that completeness before asserting it.

**How it was caught.** The operator recorded
`movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json` (from-boot v4,
5,562 frames, boot → memory-card load → Clover Forest). Replayed on Interpreter
(isolated instance, card seeded from a *copy* of the operator's card so menu
navigation matched), it reaches scene 7 with exactly 183 sectors and sector-0
origin −31136 — matching the census. Instrumenting the load then settled it
directly:

- Writers of runtime sector 0 are `0x80030F84..0x80030FF4` — **inside the
  known converter FUNC_80030F60**, not some separate builder. Region code is
  written at `0x80030F94` (`sh v0,0x7E76(at)` = table+0x2E) and the block
  pointer at `0x80030FC4` (`sw v0,0x7E58(at)` = table+0x10). The broad-phase
  AABB fields come from the parent at `0x80031670..0x800316B0`.
- Breakpointing `0x80030FA8` mid-load captured the converter's **source
  pointer `t1 = 0x801973F0`**, with container base `s6 = 0x8017A0A4`. Those
  bytes matched `/LEVEL07/TERRAIN.ALL` at file offset **119,628** — located by
  searching the raw disc image and mapping LBA 13205 back through the ISO
  directory. The container is loaded verbatim; sector-0's block pointer
  `0x8017A0A8` is container base + 4, which is where the `.ALL` block base
  came from.

So the mechanism was never exotic: **the same converter, a different container
family.** (At this point I still believed Bug Bar was a genuine runtime case —
see the second correction below.)

## Second finding: the kind→descriptor table writers (phase-3 residual)

The same load capture watched the contact-object kind→descriptor pointer table
`0x80096B98` (phase-3 `writer_attribution: unresolved`). It is written during
level load by **overlay-resident code**, four words per iteration:
`0x800B5BD0`, `0x800B5C04/0C08/0C0C/0C10`, and `0x800B39E8`,
`0x800B3A1C/3A20/3A24/3A28` — all in the 0x800B0000+ overlay window, none in
the resident EXE. That is why a resident-only search never found the writer.
Attribution to the specific overlay file is the named next step; this note
records the writer PCs, not the overlay identity.

## SECOND CORRECTION (2026-08-04, via the Thud-fight movie)

The section above originally ended with "only Bug Bar has no disc-verbatim
source". **Also wrong.** The operator pointed out that
`movies/Phase4/Interpreter/D18_thud_fight.movie.json` *is* the Thud fight
recorded on Interpreter — I had inferred from a chat message that it was a
second Clover run and never measured it. Replaying it: scene 14, 46 sectors,
pool slot 0 = actor id 36 at HP 50 falling to 0 — the fight, from boot,
through defeat. Because it loads Bug Bar from scratch, it also carried E02's
last residual.

Instrumenting that load showed Bug Bar's table is written by **the same
ordinary converter** (identical PC set to Clover's), and the converter's
source pointer `t1 = 0x800C5864` is filled by **`fcn.8001a1dc`, the LEVEL.RAW
decompressor** (stores at `0x8001A5E4..0x8001A674`) — i.e. ordinary compressed
disc data. Searching the DECOMPRESSED streams (my previous search had looked in
the raw disc image, where compressed data cannot appear verbatim) found it in
**`LEVEL04/LEVEL1.RAW` at decompressed offset 487,284**.

My tooling had rejected that container because the candidate pre-filter
required the first **four** source records to match the runtime table — and
Bug Bar authors only one. Relaxing the probe to the reference record closed
the campaign at **16/16**.

Two misses, one lesson each: a negative is only as strong as its search's
proven completeness (correction 1), and *inference from conversation is not
measurement* (correction 2) — I asserted the movie's contents twice without
replaying it.

## Open residuals (explicit)

- Which overlay file owns the descriptor writers above.
- `FUNC_8004A700` transition semantics (E02a's carry-over).

## Gates

`tests/test_phase4_e02_collision.py` — 7 tests: C tool compiles under
`-Werror`; 16 exact round trips with pinned container bindings; the block-base
family invariant (RAW→8, .ALL→4); every scene resolving to a container; the +0x2C law
on every authored sector; census totals + normal discipline; the
authored/runtime-tail split. All pass.

## Related

[[EXP_2026-08-03_phase4_e02_region_codes]] ·
[[MEM_800A7E48_Collision_sector_table_800A7E48]] ·
[[FUNC_80030F60_collision_sector-table_builder]] ·
[[EXP_2026-08-02_phase4_e11_dynamic_geometry]]
