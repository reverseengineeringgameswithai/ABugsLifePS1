---
kind: experiment
id: EXP_2026-07-08_c_decompilation_campaign_v2
name: C decompilation campaign v2 (ranker volume grind)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_function_census]
fixtures: []
artifacts: [analysis/decomp_progress.json, analysis/decomp_candidates.json, config/segments.yml]
---

# EXP_2026-07-08_c_decompilation_campaign_v2

## Question
Can the proven substrate ([[SYS_decomp_substrate]]) be ground at volume off the
`tools/decomp_candidates.py` ranker queue — a 30–60 function batch of the
C1–C5-proven classes — while keeping the rebuilt EXE SHA-1-identical?

## Method
Phase 1 of the v2 plan: balanced SDK + game/unknown leaves. For each candidate,
disassemble (`exe_read.disasm_one`), write a clean-room `src/main/*.c`, register
under `config/segments.yml` `attempted:`, gate on `tools/asmdiff.py` per-function
then `build_psx_exe.py` + `validate_build.py` (SHA-1). Absolute globals resolved
by auto-defsym address-anchored `g_<hex>` names (no hand-listed externs).

## Observations
- **Matched 27 → 75** (+48 C functions across 4 sub-batches); 10 asm + 65 C.
  `decomp_progress.json`: **2.53% → 7.02%** of 1,068 resident functions.
  `validate_build.py` SHA-1 `af43de22…` PASS at every step (byte-splat).
- **Classes matched** (all twins of C1–C5-proven patterns):
  - libgpu primitive initializers (len@+3, code@+7): SetPoly{F3,FT3,G3,GT3,F4,G4,FT4},
    SetSprt{,8,16}, SetTile{,1,8,16}, SetLine{F2,G2}; and SetLine{F3,G3,F4,G4}
    which additionally write the 0x55555555 line-strip terminator word.
  - absolute-global getters (lbu/lhu/lw): CdStatus, CdMode, CdLastCom, CheckCallback,
    GetGraphType, GetGraphDebug.
  - global swaps (fetch-old, store-a0): CdReadyCallback, CdSyncCallback, CdSetDebug,
    CdReadCallback (two-lui form); CdReadMode (la form, volatile).
  - 1-callee wrappers (auto-defsym callee by census name): CdMix, CdGetSector,
    CdDataSync, CdReady (return manipulation), and with fixed leading/trailing args
    CdDataCallback→DMACallback, CdGetToc→CdGetToc2, SpuSetNoiseVoice→_SpuSetAnyVoice.
  - misc leaves: setter (CD_set_test_parmnum), address-of (CdLastPos), pointer-deref
    read/swap (GetIntrMask, SetIntrMask), double-deref (_status), array index/write
    (_getctl, _ctl), conditional array store (setIntrVSync), bit-twiddle (NextPrim,
    IsEndPrim).
- **Reusable idioms discovered:**
  - **`volatile` suppresses delay-slot store-fill**: SetIntrMask (0x80065550) and
    CdReadMode (0x80070880) only matched after marking the pointer/target `volatile`,
    which stops GCC filling the `jr ra` delay slot with the store.
  - **commutative-compare operand order**: setIntrVSync matched only when the C
    compare operands were swapped (`val != tbl[i]`) to mirror the original `beq`.

## Skips (fail-cheap rule, ≤2 attempts)
- `0x800720DC` (fetch-and-clear) — original **fills** the `jr` delay slot with the
  store; `-O2` won't for the natural form, `volatile` moves it the wrong way.
- `memclr` ×3 (0x80065AB8/BF0/E98) + `memset_2` (0x800651A4) — original emits an
  **empty 8-byte stack frame** + an explicit down-counter; mismatches at every opt
  level (-O0/-O1/-O2), so the original source form differs from the natural loop.
  Would need the exact source shape (per-TU opt/local); deferred.
- **Internal-`j` class** — SetSemiTrans, SetShadeTex, CdComstr, CdIntstr all match
  **except one word: an absolute `j` to a local label** (if/else merge, bounds-check
  default). The per-function substrate link does NOT rebase the R_MIPS_26 target to
  `__va` (it resolves against the default load base 0x80010000). This is a genuine
  **substrate limitation in the same family as jr-tables** → feed to Phase 3
  (substrate v2): fix by assembling/linking the section at its true VA so local
  `j`/`jal` R_MIPS_26 relocations resolve correctly. See [[SYS_decomp_substrate]].

## Result
Substrate scales at volume on the proven classes; the cheap leaf/getter/setter/
swap/wrapper/prim-init classes are effectively exhausted at the current substrate
capability. What remains needs substrate v2 (internal-`j` R_MIPS_26, per-TU opt,
gp-relative, jr-tables). Per-function Canon notes set to `status: byte_matched` via
`tools/gen_matched_canon_notes.py --evidence EXP_2026-07-08_c_decompilation_campaign_v2`;
v1 notes left untouched. See [[SYS_decomp_substrate]].
