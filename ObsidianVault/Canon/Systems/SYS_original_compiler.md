---
kind: system
id: SYS_original_compiler
name: Original build compiler and matching flags
status: live_confirmed
confidence: confirmed
source_state: original_game
functions: [FUNC_80038F20]
memory: []
tables: []
constants: []
evidence:
  - EXP_2026-07-08_psyq_compiler_proof
  - EXP_2026-07-08_first_c_match
  - EXP_2026-07-08_psyq_signature_match
  - EXP_2026-07-08_c_decompilation_campaign_v1
  - EXP_2026-07-08_substrate_v2
src_paths: [config/segments.yml, tools/compiler_proof.py, tools/toolchain_manifest.json, analysis/compiler_attempts.json, docs/SUBSTRATE.md]
---

# SYS_original_compiler

## Purpose
Canon home for HOW `SCUS_942.88` was built — the exact compiler + flags whose
output is byte-identical to the shipped code. This is the substrate C-gate
condition 2 (see [[SYS_decomp_substrate]]); it makes C reimplementations
verifiable against the original, not just plausible.

## Confirmed toolchain
| Component | Value |
|---|---|
| Compiler | **GCC 2.7.2** (PsyQ 4.0/4.1-era; consistent with the PsyQ **4.0.0** signature id, [[EXP_2026-07-08_psyq_signature_match]]) |
| cc1 flags | `-O2 -G0 -mcpu=3000` |
| Assembler shim | maspsx `--dont-expand-li` (→ GNU as `-march=mips1 -mabi=32 -EL -G0`) |
| Pinned in | `config/segments.yml` `c_toolchain`; binaries hash-manifested in `tools/toolchain_manifest.json` (decompals/old-gcc 0.17, mkst/maspsx @42b862c) |

Pipeline: `cpp → cc1 -S → maspsx → as → ld @VA → objcopy` (`compile_at` in
`tools/substrate_common.py`). Absolute-addressed globals resolve at link via the
attempted entry's `externs:` map (`--defsym name=VA`).

## Evidence (byte-exact matches)
- **`SetPolyGT4` 0x80061D04** (SDK/libgpu) — pipeline proof.
- **`FUNC_80038F20` 0x80038F20** (game code, called from
  `player_vertical_update` 0x80048138) — the flags proof on Traveller's Tales
  code: `lui/lh` of a signed short at 0x80082402, `slti -0x2000`, `xori 1`.
- Both fold into the byte-splat image: `validate_build.py` PASS, rebuilt SHA-1
  `af43de22…`, 12 functions from source.

## Discriminators observed
- **`li` expansion** is the key SDK-level axis: cc1 emits `li`; maspsx default
  → `ori` (0x34), `--dont-expand-li` → GNU-as `addiu` (0x24) = the shipped form.
- **Optimization level = `-O2`** (resolved 2026-07-08): `FUNC_800457A0`
  (saved reg + stack local + retry loop) matches at `-O2` and **DIFFERS at
  `-O1`** (3 words) — the first function with enough register pressure to
  discriminate. `-O0` diverges hard everywhere. Evidence:
  [[EXP_2026-07-08_c_decompilation_campaign_v1]].
- **cc1 defers the addressing mode.** cc1 emits `lw reg, symbol` (not lui/lw
  or gp-relative); the assembler picks the mode. For an undefined extern global
  GNU-as emits absolute `lui`+`lw` — which matches the game's absolute-addressed
  globals (the majority). It does NOT reproduce the game's occasional
  **gp-relative** single-`lw` (`FUNC_80046B14` etc.): that needs a linker-script
  `_gp` + small-data placement (deferred to substrate v2 — see residuals).

## Scope / unknowns
- Proven on 2 functions. Library code (SetPolyGT4) and one game function agree
  on 2.7.2 — but the game may mix compilation units; 2.8.0/2.8.1 stay in the
  `tools/compiler_proof.py` sweep and every attempt is logged to
  `analysis/compiler_attempts.json` (no blind retest).
- **gp-relative functions deferred** (residual, substrate v2): the ~157
  gp-using functions (mostly `unknown`/libgcc-like) need a linker-script `_gp`
  + small-data section placement so GNU-as emits the single gp-relative `lw`
  instead of absolute `lui`+`lw`. `-G` at cc1 doesn't change emission (the
  assembler decides). Not blocking — game code is overwhelmingly absolute.

## Evidence
- [[EXP_2026-07-08_psyq_compiler_proof]] · [[EXP_2026-07-08_first_c_match]]
- Consumes [[SYS_decomp_substrate]] (build path) and the PsyQ-4.0.0 signature
  identification.
