---
kind: experiment
id: EXP_2026-07-08_first_c_match
name: First game-code function matched from C
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_original_compiler, SYS_decomp_substrate, SYS_function_census]
fixtures: []
artifacts: [src/main/80038f20_flag_ge_threshold.c, analysis/compiler_attempts.json]
---

# EXP_2026-07-08_first_c_match

## Question
Does the pinned PsyQ-era compiler match a real **game** function (not just SDK
library code) byte-for-byte from C?

## Method
Candidate `FUNC_80038F20` (24 B, called from `player_vertical_update`
0x80048138): `lui v0,0x8008; lh v0,0x2402(v0); nop; slti v0,-0x2000; jr ra;
xori v0,1`. Clean-room C (`return !(g_80082402 < -0x2000)`), the absolute global
resolved at link via the entry's `externs: {g_80082402: 0x80082402}`
(`--defsym`). Swept with `tools/compiler_proof.py`, then registered in
`config/segments.yml attempted` and built.

## Observations
- **MATCH** with the pinned toolchain (GCC 2.7.2 `-O2 -G0 -mcpu=3000` + maspsx
  `--dont-expand-li`): result `3c028008 84422402 00000000 2842e000 03e00008
  38420001` == target, exactly. cc1 emitted `lh $2,g_80082402` (absolute under
  -G0); maspsx expanded to `lui`+`lh`; `slt $2,$2,-8192` = the `slti`.
- Byte-splat image: `validate_build.py` PASS, **12 functions from source
  (10 asm + 2 C)**, rebuilt SHA-1 `af43de22…`.
- Census now carries `match: c` on this record (and `match: asm`/`c` across all
  12), so the inventory distinguishes asm-matched / C-matched / SDK-library /
  unknown-game / dynamically-confirmed functions.
- `g_80082402` kept address-anchored only — its field meaning is UNKNOWN (no
  evidence yet); no semantics invented.

## Conclusion
The substrate C-gate is fully **OPEN** ([[SYS_decomp_substrate]]): a real
Traveller's Tales function is now reconstructed from verifiable C. Future C
decompilation proceeds one registered, census-exact, byte-matching function at
a time — no broad decompilation. Compiler identity: [[SYS_original_compiler]].
