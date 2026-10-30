---
kind: experiment
id: EXP_2026-07-09_modding_safety_map
name: Modding-safety memory map — runtime-proven used/free + reference map
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_executable_image, SYS_function_census]
artifacts: [tools/build_memory_map.py, tools/trace_ram_usage.py, analysis/memory_map.json, tests/test_memory_map.py]
---

# EXP_2026-07-09_modding_safety_map

## Question
Mod caves keep colliding with memory that reads zero on disc but is live at runtime. Cave allocation is a
hand-maintained blacklist (`mod/mods/registry.py` `FORBIDDEN_CODE_RANGES`) with no runtime dimension. Can we
build a rigorous machine-readable **used-vs-free** map (with runtime liveness) that the build gates on, and
does the runtime method actually re-derive the known hazards?

## m1 — static layer (`analysis/memory_map.json`)
`tools/build_memory_map.py` classifies the resident image `[0x80010000,0x80082200)` into non-overlapping
regions (code / string / data_anchor / named_global / **forbidden_known** / **candidate_free** / data),
metadata-only + deterministic. 806 regions; **39 candidate-free zero-runs = 3433 B** (static, pending
runtime); all 6 `FORBIDDEN_CODE_RANGES` captured (forbidden outranks the census's span-to-next "code"
mislabel of gp-globals). Both proven-safe caves (`0x800810c0`, `0x8007f174`) correctly show `candidate_free`.
`tests/test_memory_map.py` (7, safe suite) incl. THE invariant: candidate_free never overlaps forbidden.

## m2 — runtime-liveness method PROVEN (`tools/trace_ram_usage.py --validate`)
Two write signals: value **snapshot-diff** (breadth, no interpreter penalty) MISSES memset-to-zero of
already-zero bytes; **`accessLog` write-watches** catch every store incl. zero-writes (cave zone
`[0x8007EFE8,0x80082200)` ~13 KB fits ≤64×256 B watches).

**Decisive refinement — filter by writer PC.** A first pass flagged the *safe* caves as "written" too;
those were the **BIOS/CD loader populating the EXE image at load** (harmlessly writing the mod's own bytes
into the cave), not game code clobbering it. Keeping only writes whose **writer PC is game code**
(`0x80010000–0x800B39A0`) separated hazard from harmless:
- **Safe caves `0x800810c0` + `0x8007f174`: CLEAN** (0 game-code writes) — correctly free.
- **Forbidden exercised in a boot→LEVEL01 stall-movie: WRITTEN ✓** — `0x8007fdc0` memset workspace
  (**3616 B, the biggest hazard — value-diff would MISS this**), FMV boot buffer `0x800814bc`, helper
  `0x80081058`.
- **3 forbidden NOT flagged** by the idle movie: `0x8007efe8` (level/enemy **streaming** table),
  `0x8007f130` (**Training** state), `0x80082030` (**seed-plant** descriptor) — all **event-transient**,
  not steady-state (also absent across bee/spider/mosquito/level04/acorn idle samples).

## Finding (shapes the whole campaign's rigor)
1. The write-watch + game-PC-filter method reliably distinguishes runtime-live hazards from harmless
   loader writes, and catches the memset-of-zero class that value-diff cannot.
2. **Some hazards are event-transient** (streaming transition, Training, seed plant) — coverage that only
   idles in states will miss them. Therefore: (a) m3 must **drive transitions/actions**, not just sample;
   (b) the runtime map can **never PROVE a region free** (an untriggered transient may lurk) → the hand
   `FORBIDDEN_CODE_RANGES` **stays a hard floor**, and every free claim is **coverage-qualified**, never
   absolute. This validates the plan's conservative design.

## m3 — exhaustive pristine-state sweep (runtime-folded map)
Snapshot-diff the EXE+BSS window across **158 pristine save states + 16 pristine from-boot level movies
(LEVEL00-15)**. **Modded-disc saves poison the map** (mod code is installed IN the caves) → excluded
rigorously by an **EXE-code content gate** (compare the resident code region to pristine `SCUS_942.88`;
**55 modded saves excluded** — the gate even caught `ABL_looking_at_ramp_OG_Graphics.sav`, which *looked*
pristine by name). Fold: candidate_free written by game code in any pristine state → `written` (8
eliminated); survivors coverage-qualified. **m3b memset pass** (`--memcheck`): write-watch the survivors
through boot→LEVEL01 caught **2 more that value-diff missed** — incl. `0x80081cf0`, a known controller
gp-global written with the *same value* (invisible to value-diff). **Result: 29 safe-cave runs = 2477 B
idle across 175 pristine states; both proven caves (`0x800810c0`, `0x8007f174`) survive.**

## m4 — xref is a RELOCATION aid, NOT a cave-safety signal (finding)
`debugger.xrefsTo` catches jal/j/branch + `lui`+`lo` constant-address pairs. But the `lui`+`lo` pairs are
heuristic ("probable"), and over the zero cave-zone they are **dominated by false positives**: the
proven-good `grain_hud` cave (`0x8007f174`) shows a "reference" on nearly every word. Folding xref into
cave classification would **wrongly reject the working caves**. Conclusion: cave free/used is decided by
the **WRITTEN + EXECUTED** signals only; xref is reserved for **relocation** (query refs to a *real*
global you intend to move, then verify each `from` site by disassembly).

## m5 — build gate + Canon
Wire `mod/build.py` cave check to gate on the map's USED set (written/executed/forbidden) as an additional
check, keeping `FORBIDDEN_CODE_RANGES` as a **hard floor**; `--suggest-caves` lists the 29 survivors with
their coverage qualification. `SYS_modding_safety` + extend `MEM_GLOBAL_MEMORY_MAP`.

## Evidence / links
[[SYS_executable_image]] · [[DuckStation_API_Index]] · `src_re/known_crash_cave_hazards.c` ·
`mod/mods/registry.py`.
