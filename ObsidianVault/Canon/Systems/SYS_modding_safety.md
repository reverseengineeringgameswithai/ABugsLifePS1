---
kind: system
id: SYS_modding_safety
created: 2026-07-09
updated: 2026-07-09
status: live_confirmed
confidence: confirmed
source_state: original_game
functions: []
memory: []
tables: []
constants: []
evidence: [EXP_2026-07-09_modding_safety_map]
src_paths: [tools/build_memory_map.py, tools/trace_ram_usage.py, analysis/memory_map.json, mod/build.py, mod/mods/registry.py]
patch_policy: safe_to_read
---

# SYS_modding_safety - runtime-proven cave/free memory map + build gate

## Purpose
Stop mod code/data caves from colliding with memory the game actually uses. The old cave allocator was a
hand-maintained blacklist (`mod/mods/registry.py` `FORBIDDEN_CODE_RANGES`) that only knew a hazard *after*
it crashed a build. This system adds a **machine-readable, runtime-proven used/free map** and gates the
build on it. See [[EXP_2026-07-09_modding_safety_map]] and `src_re/known_crash_cave_hazards.c`.

## The core hazard: static-zero ≠ runtime-free
An EXE region that reads zero on disc is NOT necessarily free — four classes bite: runtime-materialized
tables (`0x8007efe8`), level-load **memset workspace** (`0x8007fdc0`, wiped → reads zero *in gameplay*),
boot buffers (FMV `0x800814bc`), and gp-relative globals that happen to be zero (`0x80081cf0`, `0x80082030`).

## The map — `analysis/memory_map.json` (`tools/build_memory_map.py`)
Deterministic, metadata-only. Classifies the resident image `[0x80010000,0x80082200)` into non-overlapping
regions: `code / string / data_anchor / named_global / forbidden_known / written / candidate_free / data`.
- **`written`** = static-zero run that game code writes at runtime in ≥1 pristine state → USED (the class
  the static blacklist doesn't know).
- **`candidate_free`** = static-zero AND not game-written across all covered states → the
  `safe_cave_allowlist`. **COVERAGE-QUALIFIED, not proven-free** (see caveats).
- Current: 29 safe-cave runs = 2477 B idle across **175 pristine states**; both long-proven caves
  (`0x800810c0` blackberry, `0x8007f174` grain_hud) survive.

## How the map is built (`tools/trace_ram_usage.py`)
- **WRITTEN** = full-RAM **snapshot-diff** (readMemory ×2, no interpreter penalty) across all pristine
  states, PLUS a **`--memcheck` write-watch** pass (catches memset-of-zero / store-of-same-value that
  value-diff misses — it caught the `0x80081cf0` controller global).
- **Pristine only:** modded-disc saves have mod code installed *in the caves* and poison the map — excluded
  by an **EXE-code content gate** (compare the resident code region to pristine `SCUS_942.88`).
- Sources: 158 pristine save states + 16 from-boot level movies (`movies/go_to_end/LEVEL00-15`).

## The build gate (`mod/build.py`)
1. `FORBIDDEN_CODE_RANGES` (hand blacklist) — **hard floor, never removed**.
2. **Runtime gate:** reject any cave overlapping a map `written`/`executed` region. NOT `code` (the census
   over-marks inter-function padding as code via span-to-next — e.g. golddrop's proven `0x80078d84`).
3. `python mod/build.py --suggest-caves` — lists the coverage-qualified safe-cave runs.
All existing mods (blackberry / golddrop / grain_hud) pass; a cave in a runtime-written run is rejected.

## Rigor caveats (why "candidate_free" ≠ "proven free")
- Value snapshot-diff misses memset-of-zero (mitigated by `--memcheck` write-watch, but only on LEVEL01).
- **Event-transient** hazards (streaming/seed-plant/Training) may not fire in the covered states.
- **xref is a relocation aid, NOT a cave signal:** `xrefsTo`'s `lui`+`lo` pairs are heuristic and, over the
  zero cave-zone, dominated by false positives (the working grain_hud cave shows a "reference" on nearly
  every word). Use it only to find refs to a *real* global before relocating it, verifying each site.
→ Therefore the `FORBIDDEN_CODE_RANGES` floor stays, new caves get a margin + a boot-test, and free claims
are always qualified by coverage. Related: [[MEM_GLOBAL_MEMORY_MAP_Global_memory_map]] · [[SYS_executable_image]].
