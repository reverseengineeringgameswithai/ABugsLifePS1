---
kind: experiment
id: EXP_2026-07-10_m2c_seed_pipeline
name: m2c-seeded C-conversion pipeline (dc-9/dc-10) — automate the branchy-grind seed; CLOSED with the dc campaign at C=287
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate]
fixtures: []
artifacts: [tools/dc_m2c_seed.py, tools/dc_m2c_sdk_sigs.py, tools/dc_permute.py, tools/dc_bank_c.py, analysis/psyq_sdk_sigs.json, analysis/dc_deferred.json, analysis/asm_to_c_queue.json]
---

# EXP_2026-07-10_m2c_seed_pipeline

## Question
The readable-C campaign stands at **275 / 913** resident functions. A wall census of the 638 remaining
`.s` put the **achievable ceiling near 515 / 913 (~56%)** — ~398 are genuine walls (BIOS thunks, GTE/COP2,
regalloc floor, mis-splits) and **240 are convertible**, but only **19 are clean/first-try**; the other
**221 are the branchy/`mult` grind** where recovering control flow by hand is the slow step. The manual
levers (hand-author → `dc_permute` → `dc_bank_c`) are proven but human-in-the-loop per function. Can the
**m2c** (mips-to-c) decompiler auto-generate the seed — recovering the control flow *and* the exact global
addresses — so the grind pool converts at scale instead of one function at a time?

## Method
Built **`tools/dc_m2c_seed.py`**: drive m2c (`-t mips-gcc-c`, `--globals used`) on a function's hand-asm,
normalize the output into the byte-splat substrate's conventions, and score it with `dc_permute.score`
(compile via the pinned GCC 2.7.2 toolchain + 4-byte word-diff vs retail). A `--batch` mode sweeps the
unattempted-convertible pool and tallies `match / near / wrong_size / m2c_fail` plus a `struct_access`
flag. Seeds that land are closable by `tools/dc_permute.py` and verified/SHA-1-gated by `dc_bank_c.py` —
the same gate every hand match passes, so a bad seed can never enter the build.

Three input-fidelity bugs were found and fixed to feed m2c correctly:
1. **`.word`-encoded calls** — our `.s` encode cross-function `jal` as `.word 0x… # jal 0xADDR` (needed
   for the byte-exact rebuild). m2c reads `.word` as *data* and truncated every call-containing function
   at its first call (a 216 B function decompiled to 16 B). Fix: translate back to `jal sub_<addr>` so
   m2c follows the call graph. (2856 such calls across the pool — the single biggest blocker.)
2. **Multi-part functions** — 27 functions are assembled from a main `.s` + `parts:` in `segments.yml`;
   only the first part was being fed. Fix: concatenate all parts in address order.
3. **`?` placeholder mis-classified as failure** — m2c emits `?` as the *unknown-type* placeholder for
   undeclared externs; the pipeline wrongly treated any `?` as a decompile failure. Fix: keep the output
   and concretize `? foo(` → `int foo(` and `(? (**)…)` → `(int (**)…)`.

## Findings

**m2c recovers exactly the two things that cost the most by hand — control flow and correct addresses.**
`get_mode` (0x80063a08) decompiled to a source structurally identical to the hand seed and scoring the
**same 9w**, *with the global address `0x8007FBC8` already correct* — the very sign-extended address I had
to fix by hand in the manual pass. After the `.word`-jal fix, branchy call-heavy functions
(`sub_800737b8`) decompile with full control flow and resolved call targets.

**But raw auto-match yield is ~0.** Over the full **309** unattempted-convertible functions (after all
three fixes): `match 0 · near 1 (50w) · wrong_size 308 · m2c_fail 0`. Every function now decompiles; almost
none byte-matches. The dominant cause is structural:

- **Struct-pointer argument access → lost load width (255 / 309 flagged `struct_access`).** m2c renders a
  pointer-arg field as `argN->unkHEX`, where the field name carries the *offset* but not the *width* — a
  word store (`arg0->unk14 = 0x80073610`) and a byte store (`arg0->unk46 = 1`) are indistinguishable in
  the emitted C, so the compiled bytes (sb vs sw, and the resulting size) don't match. `--no-unk-inference`
  and typing the arg as `u8*` do **not** stop the struct-ification; `--dump-typemap` only covers
  context-declared types, so the inferred widths are not surfaced by any single-pass option.
- The **non-struct remainder** is still wrong-size from signature/type-inference imperfections (arg count,
  return type, argument sign-extension) — `get_mode` matched the manual seed only because m2c happened to
  infer its signature exactly.

## Conclusion
The pipeline is **built and validated as a decompiler front-end**, and the input-fidelity fixes are real
wins (m2c is now fed correct, call-complete assembly). But **m2c is a per-function accelerator, not a
push-button batch auto-banker.** Its value is recovering control flow + addresses + call targets — the
hard part of the branchy grind — which a human then finishes (widths, signature). Full automation needs a
**width-recovery layer** (infer field widths via a struct round-trip through m2c's own inference, or from
cast/magnitude context) before the 221-function grind pool converts unattended. Even with that layer, the
ceiling is unchanged: ~44% of functions (regalloc floor, BIOS thunks, GTE, mis-splits) stay `.s` by nature.

**Net:** no single hidden blocker gates progress; the remaining work is a width-recovery layer (engineering,
not research) plus the irreducible per-function walls. Reusable artifact: `tools/dc_m2c_seed.py`
(`--batch <class>` to re-measure yield; single-addr to inspect a seed with `--emit`). See
[[SYS_decomp_substrate]] and the campaign memory `dc-c-decompilation-at-scale`.

## Width-recovery layer (built, 2026-07-10)
Implemented the width-recovery round-trip and three companion normalizations in `dc_m2c_seed.py`:
1. **Struct-inference round-trip** — pass 1 collects each pointer-arg's accessed offsets; a generated
   context declares that arg as `struct { char unk_0[SIZE]; }` (inferrable space); pass 2 makes m2c emit
   the struct **with correct field widths** (`s32 unk14` vs `u8 unk46`). This is the width recovery.
2. **Global function-pointer call** — `*(T (**)(SIG))0xADDR(args)` mis-parses under GCC 2.7.2 (the call
   binds before the deref); wrap it `(*(…)0xADDR)(args)`.
3. **Global element-type backfill** — m2c prints a reused global-pointer store as `**(void *)0xADDR`
   (illegal); restore the element type from the address's first typed use.
4. **Literal-address anchoring** — m2c inlines raw addresses, so GCC CSEs a base across repeated uses (1
   instruction short vs retail, which reloads per use). Rewriting `**(T **)0xADDR`→`(*g_addr)` and
   `*(T *)0xADDR`→`g_addr` (with `extern` decls) restores retail's per-use load.

**Result — the layer works.** `CD_vol` (a banked struct function) now auto-reproduces at **0w**; the
previously-unattempted dispatcher `sub_80072f8c` auto-seeded to **3w**, and a one-line callee-signature
hand-fix (2-arg calls m2c inferred as 1-arg) closed it to **0w → banked** (C 275→276) — the **first
conversion delivered by the pipeline**, and a clean demonstration of the intended accelerator workflow
(`--save` a seed → finish the signature → bank).

**But batch auto-yield is still low** (`match 0 · near 2` on the 309 unattempted, up from `near 1`). The
width layer moves clean struct functions to compilable/near, but the harder unattempted pool has a
**long tail of residuals**: callee-signature inference (2-arg vs 1-arg, as in `sub_80072f8c`), further
un-normalized m2c idioms that `cc1`-error on the larger functions, and huge functions m2c only partially
decompiles. Each is a per-function finish, not an auto-bank.

## Conclusion (updated)
The width-recovery layer is **built and validated** — struct functions now decompile with correct field
widths and compile, and the pipeline delivered its first bank (`sub_80072f8c`). Its proven role is a
**strong per-function accelerator**: `dc_m2c_seed.py --save <addr>` yields a structurally-correct,
address-correct, width-correct seed that a human finishes (usually just callee signatures) and banks
through the SHA-1 gate — materially faster than hand-authoring the control flow from scratch, especially
on branchy/dispatch functions. Fully unattended batch banking would need signature inference + the idiom
long tail closed; the ~44% wall fraction is unchanged regardless.

## Expedite research (web survey, 2026-07-10)
Surveyed how the PS1 decomp community accelerates *accurate* matching (m2c is the shared decompiler; our
byte-for-byte SHA-1 gate already guarantees accuracy — the question is speed). Key prior art:
- **Signature/type context is the standard accelerator.** Mature projects (Castlevania SOTN `sotn-decomp`,
  `mgs_reversing` + `FoxdieTeam/psyq_sdk`, `nix-decomp-psx`, `mkst/esa`) feed m2c a `--context` of PsyQ SDK
  prototypes + struct types so it stops guessing callee arg-counts and struct field widths per call. This
  is exactly our #1 finishing bottleneck.
- **Open, cleanroom-safe SDK headers exist** — `PSn00bSDK`/`libpsn00b` (Lameguy64) and `PsyCross`
  (OpenDriver2) reimplement the PsyQ APIs (libgpu/libspu/libcd/libgte) with the same signatures under open
  licenses. Usable as an m2c context for the ~135 SDK functions **without** touching copyrighted Sony
  headers (and function prototypes are interface facts regardless).
- **m2c cross-function type inference** — decompiling a function *together with its callees* lets m2c infer
  callee signatures from their bodies (we currently decompile one at a time).
- **`decomp-permuter-psyq`** (twevs) — a PsyQ-tuned fork of the permuter, better at the regalloc residuals
  where our `dc_permute` plateaus (e.g. `_SpuInit` 5w).
- Matching harnesses: `asm-differ`/`objdiff`/`decomp.me` for interactive diffing (we already have the
  stricter static SHA-1 gate, so these are optional).

**Implemented the highest-value, cleanroom-safe lever: a signature context from our OWN banked source.**
`_signature_context()` emits `<ret> sub_<hex>(<args>);` (types coarsened to void*/int — only the ABI shape
matters to the caller) for every `src/main/*.c`, keyed by the `sub_<hex>` name m2c sees. **Proof:**
`sub_80072f8c` now auto-matches **0w with no hand-editing** (was 3w + a manual 2-arg callee fix). The
effect **compounds** — each newly-banked function adds its signature, so more callers auto-resolve as the
campaign proceeds.

## Expedite levers built (dc-10)
Built the layered levers from the research; **all cleanroom (our own source / coarsened interface facts —
no external headers, structs, or code in the tree)**:
- **Lever #2 — cross-function inference:** `run_m2c()` appends each unbanked (still-`.s`) depth-1 callee's
  asm to the m2c input, so m2c infers the callee's signature from its body (covers internal/game callees the
  banked-signature context can't).
- **Lever #1 — SDK prototype context:** `tools/dc_m2c_sdk_sigs.py` → `analysis/psyq_sdk_sigs.json` holds
  **coarsened** (pointer-vs-scalar only) signatures for 22 well-known public PsyQ functions, cross-checked
  against open PSn00bSDK/PsyCross. `_signature_context()` emits `<ret> sub_<hex>(...)` for any pool function
  whose census name matches. Struct **layouts still come from our binary round-trip** — the map carries no
  layouts.
- Cheap normalizer fixes: `#define NULL 0`; broadened `?` type coverage.

**Honest yield (`--batch all`, 308 fns): before → after both levers:** `match 0→1`, `near 2→2`,
`size 18→19`, `cc_error 288→286`. **The batch barely moved** — because it is dominated by **compile
errors (286)**, not signatures. The remaining cc_error tail is hard m2c idioms: **computed struct pointers**
(`(v + 0x80090000)->unkHEX` — m2c uses `->` on an int sum), void\* global derefs, and `saved_reg_*`
artifacts — an open-ended normalization tail, not worth exhaustively chasing.

**Where the levers DO pay off: the per-function grind, not the batch metric.** The one new auto-match
(`_SsTrapIntrVSync`, 0x80067f20 — SEQ VSync trap, now banked, **C 276→277**) landed purely from the
signature context; and every function that *does* compile now finishes with fewer hand-fixes (correct
callee arg-counts). The effect compounds as banking proceeds.

## Next
- **Grind with `dc_m2c_seed.py --save <addr>`** on the ~20 compiling worklist candidates (0w → small
  word-diff → small size-delta): finish the 1–2-instruction residuals (fn-ptr call codegen, address
  literals, strides) → permuter-close `near` ones → bank. Defer regalloc walls (`_SpuInit` 5w) and the
  cc_error idiom tail.
- **Lever #3 (evaluated — not worth building):** as a proxy, ran the upstream decomp-permuter (the same
  34-pass randomizer `decomp-permuter-psyq` forks) on `_SpuInit` 5w — it **plateaued at 5w, no crack**. The
  PsyQ fork uses the identical randomizer, so it won't resolve this residual class (loop-setup ordering /
  regalloc floor) readably. Decision: do **not** clone/integrate it.

## Grind results (dc-10 execution, 2026-07-10)
Worked the closeness worklist end-to-end: **21 candidates → 10 banked (C 277→287), 9 deferred/walled
with notes, worklist floored at 5** (`_SpuInit` 6w regalloc, `sub_80043184` 16w regalloc, `_drs`,
`sub_8003f3b4`, `collision_point_in_poly`).

**Banked** (all 0w, SHA-1-gated): `SetDefDrawEnv`, `_SsInit`, `FntLoad`, `sub_800709ac`, `StGetBackloc`
(healed 8B+88B mis-split), `CdInit`, `CdReadBreak`, `_otc`, `boot_subsystem_init` (0w first try),
`sub_80055db0`.

**TOOLCHAIN DISCOVERY — maspsx `--expand-div`:** retail variable-division guards
(`bne divisor,0; break 7` + `-1/0x80000000` overflow `break 6`) come from ASPSX's div macro expansion.
Added `--expand-div` to the global `c_toolchain.maspsx_args` (SHA-1 re-verified byte-identical — a no-op
for all prior banks, required for any div-bearing C). `compiler_proof` grid, `dc_permute`, `dc_m2c_seed`
synced. `sub_80055db0` = first div-bearing banked C.

**New authoring levers proven this pass** (each closed a function):
- *Returned-temp tail stores + cross-jump if-arm stores* — `SetDefDrawEnv`: `r = env; r->f = …; return r;`
  reproduces `$v0`-based tail stores; each if-arm storing the same field lets GCC cross-jump-merge the store.
- *Address-giv counter* — `_SsInit` loop 3: `slot = base + i * 16` blocks `check_dbra_loop` down-count
  reversal AND strength-reduces to the +0x40 walking pointer; a plain walking pointer gets the counter
  reversed (slti dropped).
- *Shared counters with role swap* — `_SsInit`: one function-scope `i`/`j` pair reused across loops, roles
  swapped in loop 3, reproduces retail regalloc; block-scoped counters break it (and let the scheduler fill
  a delay slot retail leaves as nop, via the WAR hazard on the shared counter reg).
- *Cross-call base pointer* — `FntLoad`: base held in a local across two calls forces the third
  callee-saved reg + `base + 512` addressing.
- *volatile store target* — `sub_800709ac`/`CdReadBreak`: keeps a flag store out of a call's delay slot /
  pins store-before-load order.
- *goto-retry loop* — `CdInit`: a structured loop hoists comparison constants into saved regs; the goto
  loop (no LOOP notes → no invariant motion) rematerializes them like retail. Plus if/else with a single
  return joining at the common epilogue.
- *Held flag pointer* — `CdReadBreak`: `flags = &g_80081c10` in a saved reg, re-read through it.
- *Plain temp to pin association* — `_otc`: `ofs = n*4 - 4;` stops GCC folding the −4 into the base operand.
- *Struct-local dead stores* — `get_tw`-class: a local struct's field writes hit the stack (no SRA in
  GCC 2.7.2) while CSE reuses the register values — recovers `Δ-32`-style dead-store gaps.
- *K&R short params* — `sub_80043184`: unprototyped defs re-extend `a0–a3` shorts (sll/sra ×4); an s16
  callee return assigned to an `s32` local extends once (K&R return promotion = no re-extension at return).

**The residual wall class = phantom register copies / allocation order.** Four functions (`_dws`, `_drs`,
`sub_80073578`, `sub_80043184`) reach exact size at 16–117w but retail keeps register copies GCC now
copy-propagates away (clamp-limit copies, raw-arg copies masked late) or allocates `$t`-regs in a different
pseudo order — invariant under temp/var splits, decl order, param reuse, and the permuter. `sub_80072eb8`
and `get_tw` add a *block-layout* variant (return-0 stub placement, OR-chain canonicalization). These are
the honest next frontier; a targeted allocation-order lever (or accepting them as walls) decides the last
~5 SDK stragglers.

**Other walls confirmed:** `sub_80071ccc`/`sub_80071d04` load their fn-pointer *above the prologue* — not
GCC 2.7.2 C codegen (assembly-authored or foreign toolchain); `sub_8003f3b4` = 18 switch case bodies
mis-split from a jr-table parent (needs parent identification, not standalone conversion). All deferrals
recorded in `analysis/dc_deferred.json`.
