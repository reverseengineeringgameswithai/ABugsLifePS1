---
kind: system
id: SYS_executable_image
name: Boot executable image (PS-X EXE) — format, load map, code/data separation
status: live_confirmed
confidence: confirmed
source_state: original_game
functions: []
memory: [MEM_GLOBAL_MEMORY_MAP]
tables: []
constants: []
evidence:
  - EXP_2026-07-08_re_baseline_run
  - EXP_2026-07-08_psyq_signature_match
  - EXP_2026-07-08_function_census_v1
  - EXP_2026-07-09_modding_safety_map
src_paths: [docs/EXECUTABLE_AND_OVERLAYS.md, tools/exe_read.py, tools/re_baseline.py, symbols/re_symbols.sym, ghidra/README.md]
---

# SYS_executable_image

## Purpose
Canon home for the RE-basics facts about `SCUS_942.88`: platform, CPU, executable
format, load/base address, section map, and the state of code-vs-data separation and
function-boundary recovery. Deep dive: `docs/EXECUTABLE_AND_OVERLAYS.md`. Runtime
address axis: [[MEM_GLOBAL_MEMORY_MAP_Global_memory_map]].

## Confirmed behavior

### Platform / format / load map
| Fact | Value |
|---|---|
| Platform | Sony PlayStation (PS1) |
| CPU | MIPS R3000A, little-endian, 32-bit (+GTE/COP2) |
| Format | **PS-X EXE** (`PS-X EXE` magic), file 471,040 B |
| Load | file offset `0x800` → VA **`0x80010000`**, text size `0x72800` (header+text = exact file size) |
| VA↔file | `offset = (va − 0x80010000) + 0x800` (`tools/exe_read.py`) |
| Entry PC | `0x8005F690` |
| Runtime `$gp` | `0x80081D98` (r2 `anal.gp`; header gp field 0) |
| Initial SP | `0x801FFFF0` |
| `.bss` | `0x80082200–0x800B399F`, zero-cleared at startup (not in file) |
| Ghidra bases | ABLPilot: BinaryLoader `0x8000f800`; ABLPsx: PsxLoader (header-driven) |

### Code vs data separation (started; regenerable numbers)
From `tools/re_baseline.py --disasm --codemap` (2026-07-08): **837 r2 functions** cover
**79.4%** of the text image as code, strings **5.3%**; last function ends `0x8008219c`
(data tail `0x80082200..0x80082800` ≈ gp window). Known data anchors: berry-throw jump
table `0x8001b1c0`, mover-VM opcode table ptr `0x8001b2f4`, gp-relative globals window
around `0x80081d98`, PsyQ copyright string `0x8007fd00`.

### Function boundaries + library labeling (PsyQ 4.0.0)
- Merged function inventory (r2 ∪ symbol map ∪ PsyQ signatures): **1,170 addresses,
  687 named** — regenerate via `tools/re_baseline.py --inventory`.
- **PsyQ SDK version 4.0.0** auto-detected from `Ps` lib markers; **644 library
  functions identified** by full signature matching (libc/libgpu/libgte/libetc/
  libsnd/libspu/libapi/kernel) and merged into `symbols/re_symbols.sym`
  (129 → 761 entries) — see [[EXP_2026-07-08_psyq_signature_match]].
- **Library region:** `0x8005F688` (`__main`) … end of text = PsyQ SDK code;
  game code occupies `0x80010000–0x8005F688`.
- Authority: `symbols/re_symbols.sym` is THE symbol map (validated/strictly sorted);
  Ghidra and r2 consume it, never write it back.

## Unknowns
- ~15% of the text image is neither r2-function-covered nor string data (jump tables,
  rodata, alignment) — separation is a lower bound, refine per-investigation.
- Two hand names sit inside the library region and need review against PsyQ layout:
  `frame_render_driver@0x80062C70` (psyq: PutDrawEnv) and
  `gpu_present_drawotag_vsync@0x800646B8` (psyq: _addque2). Hand names kept pending
  live re-check.

## Evidence
- [[EXP_2026-07-08_re_baseline_run]] — header parse asserts, disasm/codemap counts.
- [[EXP_2026-07-08_psyq_signature_match]] — version detection, match counts, oracle,
  and the SsVab mislabel correction.
- Supersedes archived [[Executable_and_Overlays]] (EXE half) and
  [[Symbol_Map_Baseline]] / [[Blocker_-_Symbol_recovery_has_no_authoritative_map]].
