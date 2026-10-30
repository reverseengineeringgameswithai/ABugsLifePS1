---
kind: experiment
id: EXP_2026-07-08_psyq_compiler_proof
name: PsyQ compiler + flag matrix proof
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_original_compiler, SYS_decomp_substrate]
fixtures: []
artifacts: [analysis/compiler_attempts.json, tools/compiler_proof.py, src/main/80061d04_SetPolyGT4.c]
---

# EXP_2026-07-08_psyq_compiler_proof

## Question
Which compiler + flags reproduce the shipped code byte-for-byte, and can the
substrate compile one known function from C to prove it?

## Method
Acquired the era toolchain (decompals/old-gcc 0.17 PSX cc1/cpp for GCC
2.7.2/2.8.0/2.8.1 — 32-bit i386 static, run natively on Fedora 44; mkst/maspsx
@42b862c). `tools/compiler_proof.py` sweeps (compiler × {-O0..-O3} × {-G0,-G8} ×
{maspsx --dont-expand-li / default / --expand-li}) for a candidate C source,
byte-compares each build against the original, and logs every attempt to
`analysis/compiler_attempts.json`. Candidate: `SetPolyGT4` (0x80061D04, libgpu),
clean-room C (no Sony header).

## Observations
- **72-combo sweep, 18 matches / 54 misses / 0 errors** recorded.
- **Winner: GCC 2.7.2 `-O2 -G0 -mcpu=3000` + maspsx `--dont-expand-li`**
  (pinned in `config/segments.yml c_toolchain`).
- Discriminator: the `li` expansion axis — cc1 emits `li $2,12`; maspsx default
  → `ori` (word `0x3402000c`), `--dont-expand-li` → GNU-as `addiu`
  (`0x2402000c`) = the shipped byte. `-O0` diverges (15 words, stack spills);
  `-O1/-O2/-O3` all match this trivial function.
- The C entry builds into the byte-splat image byte-exact:
  `validate_build.py` PASS, 11 functions from source, rebuilt SHA-1 `af43de22…`.

## Conclusion
The compiler question (substrate C-gate condition 2) is answered and pinned;
the C pipeline is proven end-to-end. The game-code confirmation is in
[[EXP_2026-07-08_first_c_match]]. Canon: [[SYS_original_compiler]].
