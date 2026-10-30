---
kind: experiment
id: EXP_2026-07-08_first_matched_functions
name: First byte-matched functions through the substrate
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_function_census]
fixtures: []
artifacts: ["asm/hand_written/*.s (local-only, pinned in tools/repro_inputs.sha256)", "build/substrate/build_manifest.json (regenerable)"]
---

# EXP_2026-07-08_first_matched_functions

## Question
Can the byte-splat substrate rebuild `SCUS_942.88` with real functions coming
from hand-written assembly, byte-identically?

## Method
10 functions selected from the census by the docs/SUBSTRATE.md criteria
(bios_thunk class, then small gp-free leaves), hand-written from the r2
reference listings into `asm/hand_written/`, registered in
`config/segments.yml`, then `build_psx_exe.py` → `asmdiff.py` →
`validate_build.py`.

## Observations
- **10/10 MATCH on the first build**; rebuilt image SHA-1 `af43de22…` ==
  original ⇒ whole-image validate PASS with 96 bytes of the EXE now coming
  from source:
  | fn | va | size |
  |---|---|---|
  | InitHeap (A0:0x39) | 0x80065EEC | 12 |
  | strcat (A0:0x15) | 0x8005F74C | 12 |
  | strcpy (A0:0x19) | 0x8005F76C | 12 |
  | strlen (A0:0x1B) | 0x8005F77C | 12 |
  | memcpy (A0:0x2A) | 0x8005F79C | 12 |
  | rand (A0:0x2F) | 0x8005F7BC | 12 |
  | __main | 0x8005F688 | 8 |
  | GetClut | 0x80061A84 | 24 |
  | TermPrim | 0x80061C10 | 24 |
  | GetTPage | 0x80061A48 | 60 |
- GNU as flag set locked: `-march=mips1 -mabi=32 -EL -no-pad-sections -G0`
  with `.set noreorder/.set noat`; two toolchain traps fixed en route:
  `ld` needs `-m elf32ltsmip` (64-bit-default BFD), and gas's 2**4 alignment
  on empty sections pads the merged output section — `SUBALIGN(4)` in
  `config/linker.ld` fixes it (caught by the synthetic round-trip test).
- Census extents were exact for all 10 (start/end straight from
  `analysis/functions.json`; segments↔census consistency is test-enforced).

## Conclusion
The substrate works end-to-end. C-gate condition 1 (≥10 matched) is met the
same day the scaffold landed; condition 2 (original-compiler proof) remains
open by design. Next matches should sample LARGER leaves (branch-bearing,
0x40–0x100 B) to shake out reorder/idiom traps before any C attempt.
