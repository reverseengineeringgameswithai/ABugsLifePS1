---
kind: experiment
id: EXP_2026-07-08_psyq_signature_match
name: Full PsyQ SDK library signature matching (ghidra_psx_ldr)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_executable_image]
fixtures: []
artifacts: [extracted/re_baseline/psyq_matches.csv, extracted/re_baseline/psyq_version.txt, extracted/re_baseline/psyq_headless.log]
---

# EXP_2026-07-08_psyq_signature_match - Full PsyQ library signature matching

## Question
Which PsyQ SDK version built `SCUS_942.88`, and which functions in it are SDK library
code (vs game code)?

## Method
`ghidra_psx_ldr` release 2026.07.02 (built for Ghidra 12.1.2) installed into the
Flatpak Ghidra; fresh headless project **ABLPsx** imported with its PsxLoader; the
"PsyQ Signatures" analyzer applied the shipped per-version signature sets; matches
exported by `ghidra/scripts/ExportPsyqMatches.java`; merged into the authoritative
map by `tools/merge_psyq_symbols.py` (hand names win; oracle gate). Exact commands:
`ghidra/README.md` § "PsyQ signature project".

## Observations
- **PsyQ version 4.0.0 auto-detected** from `Ps` library version markers in the
  binary (not the analyzer's 4.7.0 fallback). Consistent with the Oct-1998 master
  and the `(c) 1993-1997 Sony` string @ `0x8007FD00`.
- 797 functions named by signatures; **644 inside the EXE text image** (rest =
  synthetic GTE-macro helper segment, excluded). Library region starts at
  `__main = 0x8005F688`; full libc/libgpu/libgte/libetc/libsnd/libspu/libapi/kernel
  families laid out in natural source order.
- **Merge:** map 129 → **761 symbols**; 632 added, 1 placeholder upgraded
  (`FUNC_80060724` → `RotAverage4`), 9 conflicts kept the hand name (incl.
  `main_shell_state_machine@0x8004FA40`, which PsyQ independently identified as
  `main` — strong cross-validation).
- **ORACLE FINDING (hand-map correction):** the original oracle
  `0x8006B1C0 == SsVabTransBody` FAILED — and investigation proved the *signatures*
  right: PsyQ agrees exactly with the hand name `SsVabOpenHead@0x8006B130`, then lays
  out the whole libsnd family coherently (`SsVabOpenHeadSticky@b160`,
  `SsVabFakeHead@b190`, `SsVabOpenHeadWithMode@b1c0`, **`SsVabTransBody@0x8006B59C`**,
  `SsVabTransCompleted@b65c`). The old label at `0x8006B1C0` was a misidentification;
  corrected in `symbols/re_symbols.sym` 2026-07-08. Downstream mentions of
  "SsVabTransBody 0x8006B1C0" (e.g. SFX-replacement notes, `src_re/sfx_system.c`
  comments) refer to the function now named `SsVabOpenHeadWithMode`; the *behavioral*
  RE there is unaffected. New oracle = the agreement anchor `0x8006B130`.
- **Open review items** (hand names kept, likely library-internal): 
  `frame_render_driver@0x80062C70` (psyq: `PutDrawEnv`) and
  `gpu_present_drawotag_vsync@0x800646B8` (psyq: `_addque2`).

## Result
SUCCESS — full signature matching done; toolchain finding refined to **PsyQ 4.0.0**;
authoritative symbol map now carries the complete SDK library layer.

## Artifacts
`extracted/re_baseline/psyq_matches.csv` + `psyq_version.txt` + `psyq_headless.log`
(regenerable); `symbols/re_symbols.sym.bak` = pre-merge map.
