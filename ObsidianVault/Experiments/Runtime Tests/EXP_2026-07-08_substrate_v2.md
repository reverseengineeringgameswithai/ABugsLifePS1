---
kind: experiment
id: EXP_2026-07-08_substrate_v2
name: Substrate v2 — internal-j / gp-relative / jr-table (v2 phase 3)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_original_compiler]
fixtures: []
artifacts: [tools/substrate_common.py, config/linker.ld, config/segments.yml, tests/test_substrate.py]
---

# EXP_2026-07-08_substrate_v2

## Question
Can the three deferred hard classes — gp-relative, switch/jr-table, and the
internal-`j` limitation surfaced in [[EXP_2026-07-08_c_decompilation_campaign_v2]]
— be unblocked with minimal, non-regressing substrate changes, and proven?

## Method
Diagnose in isolation (compile → `objdump -dr` relocations → link → inspect),
change the linker/toolchain path, gate every change so all 80 prior matches stay
SHA-1-identical, then match real functions per class.

## Observations
- **Root cause of the internal-`j` bug** (not what it looked like): the section was
  linked at the **0x80010000 default, not `__va`**. `--defsym __va` never reaches the
  linker-script `DEFINED(__va)?__va:default` ternary. Every prior match survived only
  because it is position-independent — a local `j` is the first case that reads its
  own section base. Fix = `ld --section-start=.out=<va>`.
  - **internal-`j` class RESOLVED — 4 byte-exact**: SetSemiTrans (0x80061C28),
    SetShadeTex (0x80061C50), CdComstr (0x8006D810), CdIntstr (0x8006D844). The last
    two also required the default string referenced as an **address-anchored symbol**
    (la `%hi/%lo`, sign-adjusted) not a raw `(char*)` constant (`lui/ori`).
- **gp-relative RESOLVED — 2 byte-exact**: `0x80046B14` (`g & 1`, gp+0x6E0),
  `0x80045D5C` (`g = 1`, gp+0x6EC). Recipe: per-entry `small_data: true` → cc1 + `as`
  at `-G8` (so `lw $2,sym` macros expand to `%gprel`/R_MIPS_GPREL16) + link `_gp`
  (top-level `gp: 0x80081D98`). Opt-in; `-G0` entries unchanged.
- **switch/jr-table mechanism PROVEN (synthetic)**: with `.rdata*` added to the
  linker script + `--section-start`, a C `switch`'s inline jump table places correctly
  and its R_MIPS_32 `.word $Ln` entries resolve to the exact case-label VAs
  (`80060024, 80060034, …`); `jr v0` dispatch verified end-to-end.

## Remaining constraint (honest)
Real game switch dispatchers keep their jump tables in a **shared rodata pool at a
fixed address** separate from the function (e.g. table @0x8001B778 for the switch at
0x800593E8, placed BEFORE it), so a C `switch` (inline table) yields a different
`lw table(at)` offset. Byte-matching one needs the table pinned at its pooled address
(external data blob) or a function whose table is adjacent. Census extents on switch
dispatchers are also frequently mis-split (default target beyond the recorded end).
This is a data-placement concern, not a linking one — the substrate now handles the
linking.

## Result
matched 80 → 86 (7.49% → 8.05%); SHA-1 `af43de22…` PASS throughout. Substrate
changes: `tools/substrate_common.py` (section-start, small_data/_gp threading),
`config/linker.ld` (`.rdata*`), `config/segments.yml` (`gp:` + `small_data:` entries).
Guards: `tests/test_substrate.py` `test_synthetic_internal_j_rebased_to_va` +
`test_synthetic_gp_relative`. Canon notes for the 6 set to `byte_matched`.
See [[SYS_decomp_substrate]].
