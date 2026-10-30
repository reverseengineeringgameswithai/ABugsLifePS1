---
kind: experiment
id: EXP_2026-07-09_decomp_v5_bytepercent
aliases: [EXP_2026-07-09_decomp_v5_bytepercent, "decomp v5", "byte-% push"]
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_function_census]
artifacts: [config/segments.yml, tools/gen_handasm.py, tools/function_census.py, analysis/decomp_progress.json]
---

# EXP_2026-07-09_decomp_v5_bytepercent — hand-asm byte-% push 31.58 → 99.88 %

## Question
How far can the byte-exact rebuild metric go, and what actually blocks it?

## Method
`tools/gen_handasm.py` re-emits a function's original `SCUS_942.88` bytes as an assemblable `.s` (raw
immediates, `.word` for GTE/undecoded, no symbolic relocations → byte-exact by construction). Per function:
gen → add an `attempted:` entry in `config/segments.yml` → `tools/validate_build.py` (rebuilt EXE must equal
SHA-1 `af43de22…`). Batched with a guard (skip a range that contains another census function-start) and a
single-validate-per-batch banker with per-function isolation on failure.

## Findings
- **Data-in-code was inflating the denominator.** 10 symbol-only resident "functions" (16,052 B — the VM
  bytecode region `0x80077xxx`: `vm_ai_program_region`, `enemy_hit_program_ptr`, `contact_metadata_table_a/b`,
  `sky_clear_*`, `vm_program_pointer_table`; and the dispatch pools `0x8001B42C`/`0x8001B570`) have
  `discovery: symbol` only and no `jr ra` — they are DATA. Plus `_2MBYTE_OBJ_B4` (all-identical words). The
  census now reclassifies both classes `range_type:data` (same as the RCA a5 / overlay data detectors),
  shrinking the code denominator 417,020 → 400,952 (+1.27 pp free).
- **gen_handasm hardening:** `beq/bne/blez/bgtz/regimm` branches whose target is *outside* the function now
  fall back to raw `.word` (like the `j` case) instead of crashing — unblocked several functions.
- **Every resident function is hand-asm-matchable.** All 968 resident code functions now reconstruct
  byte-exact; **byte-% = 99.88 %** (the remaining 0.12 % is inter-function padding, not code). 0 deferred —
  even the v4-"deferred" over-merge/absorbing candidates (`0x8002B428`, `0x80058AF8`, `0x800498AC`) banked
  cleanly under the interior-start guard + SHA-1 gate.

## ⚠️ Byte-% is REBUILD coverage, NOT understanding
Of the 968 matched functions, **482 are unnamed `unknown`-class** — hand-asm byte *transcription* with no
semantics. Named/understood matched functions: **171 game** (147 asm + 24 C) + 308 sdk_psyq + 7 crt0/bios.
So 99.88 % byte-match coexists with ~50 % of matched functions still un-understood. **Do not read the byte
metric as "the game is decompiled/understood."** Real C decompilation of game functions remains blocked
(frame/regalloc without PsyQ headers — see `src/wip/`); understanding is tracked separately (named-function
count, `naming_priority.json`).

## Links
[[SYS_decomp_substrate]] · [[SYS_function_census]] · [[DuckStation_API_Index]].
