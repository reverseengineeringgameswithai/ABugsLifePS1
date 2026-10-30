---
kind: index
id: RE_BASELINE_INDEX
name: RE basics baseline — reproducibility index
aliases: [Symbols Index, Symbol Map Baseline, Symbol_Map_Baseline, Tools Catalog]
---

# RE Baseline Index

How to regenerate the project's entire static-analysis floor from a clean checkout +
the owner's disc. One command: `python tools/re_baseline.py --all` → untracked
`extracted/re_baseline/` (report.json/report.md hold the quotable counts; listings of
the copyrighted binary are NEVER committed).

## The RE-basics checklist → Canon homes
| Basics item | Canon home | Regeneration |
|---|---|---|
| Game version + hashes | [[SYS_game_identity_and_provenance]] | `re_baseline.py --provenance` vs `tools/disc_provenance.json`; guarded by `tests/test_disc_provenance.py` |
| Platform / CPU / format / load address / sections | [[SYS_executable_image]] | `re_baseline.py --exe` (asserts vs PS-X EXE header) |
| Static disassembly | [[SYS_executable_image]] | `re_baseline.py --disasm` (r2 5.9.8 psxexe plugin, `anal.gp=0x80081d98`) |
| Code vs data separation | [[SYS_executable_image]] | `re_baseline.py --codemap` |
| Function boundaries | [[SYS_function_census]] (canonical) + [[SYS_executable_image]] + [[Address Index]] | `re_baseline.py --all` then `tools/function_census.py` → COMMITTED `analysis/functions.json` (+`.csv`, `code_coverage.md`); legacy `function_inventory.csv` kept for compatibility |
| Libraries / compiler patterns | [[SYS_executable_image]] + [[Finding - Build toolchain and PROPACK provenance]] | ghidra ABLPsx PsyQ signatures (recipe in `ghidra/README.md`) → `tools/merge_psyq_symbols.py` |
| Overlays / compressed chunks | [[SYS_overlays_and_runtime_loading]] | `re_baseline.py --overlays` |
| Reproducible scripts/notes | this index | `tools/re_baseline.py`, `ghidra/README.md`, `docs/TOOLING.md` |

## Authority chain
`symbols/re_symbols.sym` is the ONE authoritative symbol map (validate:
`tools/validate_symbol_map.py`; export: `tools/symbol_roundtrip.py`). r2 and both
Ghidra projects (ABLPilot decompiler cross-check, ABLPsx PsyQ signatures) consume it
or feed it through explicit merge tools — never write it directly.

## Evidence
[[EXP_2026-07-08_re_baseline_run]] · [[EXP_2026-07-08_psyq_signature_match]] ·
[[EXP_2026-07-08_function_census_v1]] · [[EXP_2026-07-08_redump_datfile_check]] ·
session [[Session_2026-07-08_-_RE_basics_baseline]]
