# Ghidra decompiler/cross-check pilot — report

**Date:** 2026-06-22
**Scope:** Stand up a headless Ghidra project for `SCUS_942.88`, import the authoritative
`symbols/re_symbols.sym`, decompile a small sample of known functions, and decide whether
Ghidra earns a place as a **decompiler / cross-check layer** alongside the existing
radare2 + DuckStation workflow.

**Verdict: KEEP IT.** Ghidra adds clear, complementary value (readable C for functions the
manual pass left partly TODO). It does **not** replace anything — radare2 + DuckStation remain
primary, and `re_symbols.sym` remains the single source of truth.

---

## What was set up (all inside the project PWD)

```
ghidra/
  project/            Ghidra headless project "ABLPilot" (SCUS_942.88 imported + analyzed)
  scripts/ABLPilot.java   symbol-import + sample-decompile post-script (Java GhidraScript)
  out/                decompiled C samples + headless logs
  README.md           how to re-run
  PILOT_REPORT.md     this file
```

- **Ghidra**: 12.1.2, installed as Flatpak `org.ghidra_sre.Ghidra`. Already had `filesystems=home;`,
  so it can read the project dir **with no `flatpak override`** (none was applied).
- **Import**: Raw Binary loader, `MIPS:LE:32:default`, base address **`0x8000f800`** so that
  file offset `0x800` lands at VA `0x80010000` (per `docs/EXECUTABLE_AND_OVERLAYS.md`).
- **Symbols**: `ABLPilot.java` read all 104 `re_symbols.sym` entries →
  **103 labels applied, 34 matched to auto-discovered functions, 9 functions created.**
  The `.sym` file is read-only input; Ghidra never writes back to it.

## Sample decompiled (3 functions with hand-written `.c` to compare against)

| Addr | Name | Hand-written ref | Ghidra result |
|---|---|---|---|
| `0x800526F4` | HUD draw | `src_re/hud_800526f4.c` | 378 lines C; **matches** confirmed model |
| `0x8001CDC0` | DAT parser | `src_re/dat_parser_8001cdc0.c` | 205 lines C |
| `0x80053814` | type-0x3f dispatch | `src_re/source3f_dispatch_80053814.c` | 467 lines C |

## Findings

**1. Agreement with the manual analysis (high confidence boost).**
On `0x800526F4`, Ghidra independently reproduced the operator's confirmed HUD model: the pulse
halfwords `0x800b0188/18c/190/194/198`, the grain latch `0x800a65a0`, the FLIK record pointers
`0x800a0220/0430/0a60/0d78` with the `+0x1b` collected flag, and the seed-counter loop. Two tools
arriving at the same structure independently is exactly the cross-check value we wanted.

**2. Ghidra resolved what the manual pass deferred.**
`hud_800526f4.c` explicitly marks the scene-specific panels after `0x80053264` as
"summarized UNKNOWN/TODO". Ghidra fully decompiled them — the `current_scene_id` switch
(scenes 2/5/7/0xb/0xc/0xd/0xe/0xf) is laid out as concrete C. This is net-new readable detail.

**3. Imported symbol names flow into the decompiler.**
Because the `.sym` labels were applied first, the C output reads with project names
(`current_scene_id`, `master_game_state`, `grain_count_hud_mirror`, `flik_bitmask`,
`seed_counter_0`, …) instead of raw addresses — so Ghidra output is directly comparable to the
hand-written files without a translation step.

**4. `$gp`-relative globals — RESOLVED 2026-07-08.**
`ghidra/scripts/SetGpAndExport.java` sets the MIPS `gp` register context to `0x80081D98`
(matching r2 `anal.gp`) over the text range and re-analyzes. Before/after on the three pilot
samples: `unaff_gp` occurrences 28 → **0** in `ghidra_8001cdc0*.c` (the other two were already
0). Resolved globals verified against ground truth: `current_scene_id` (0x80082504) appears BY
NAME, `grain_count_hud_mirror` (0x800A65A1) in the HUD sample, pass-2 table `DAT_80091210` and
scene-gated `DAT_8008238C` (= gp+0x5f4) match `src_re/dat_parser_8001cdc0.c`. The same run
exports `extracted/re_baseline/ghidra_functions.csv` (699 text-range functions), which
`tools/re_baseline.py --inventory` and `tools/function_census.py` fold in as the `ghidra`
signal. Evidence: vault [[EXP_2026-07-08_ghidra_gp_context]].
CAVEAT: Ghidra global-variable recovery is trusted ONLY where this before/after check or a
spot-verification covered it; treat any other recovered global as unverified until checked.

## Decision & boundaries

- **Keep Ghidra as a decompiler / cross-check layer.** Use it to (a) get readable C for
  functions still in raw-asm/manual state, and (b) independently validate r2-derived findings.
- **radare2 + DuckStation stay primary.** No existing notes, scripts, or r2 tooling were changed.
- **`re_symbols.sym` stays authoritative.** Ghidra consumes it; if they ever disagree, the `.sym`
  file (and live DuckStation evidence) wins. Re-import after `.sym` changes — do not hand-edit
  symbols inside the Ghidra DB as a source of truth.
- **GhidraMCP: not configured** (per constraint). This pilot is headless decompile only.

## Follow-ups (optional, not done here)

1. ~~Set Ghidra MIPS `gp = 0x80081d98` register context~~ DONE 2026-07-08 (SetGpAndExport.java).
2. A small re-sync script to re-apply `re_symbols.sym` after it changes (rerun `ABLPilot.java`).
3. Only if the cross-check proves routinely useful: revisit GhidraMCP for in-editor queries.
