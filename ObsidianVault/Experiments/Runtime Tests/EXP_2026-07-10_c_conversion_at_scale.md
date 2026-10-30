---
kind: experiment
id: EXP_2026-07-10_c_conversion_at_scale
name: C-conversion at scale (dc-6) — autonomous agent-verified decompilation to readable C
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_function_census]
fixtures: []
artifacts: [tools/dc_bank_c.py, tools/compiler_proof.py, tools/asm_to_c_candidates.py, config/segments.yml, analysis/compiler_attempts.json]
---

# EXP_2026-07-10_c_conversion_at_scale

## Question
The resident EXE is byte-complete (98.2%) and fully named (unknown = 0), but only 99 of 913 functions
were readable C — the other 814 were byte-exact hand-asm transcription (the open `game_code_c_complete`
gate). The queue (`analysis/asm_to_c_queue.json`) held **576 C-convertible** functions (314 game + 262
SDK). Can they be converted to **byte-exact readable C** autonomously, at scale, with zero user input?

## Method (autonomous, agent-verified — hands-off)
Purely static compile-and-byte-compare (no emulator). Per batch: fan out ~4 general-purpose agents,
each assigned ~12 functions (game-first, smallest-first). Each agent reads the `.s` + census context +
the proven levers, hand-authors readable C, and **self-verifies with `tools/compiler_proof.py`**
(GCC 2.7.2 `-O2 -G0 -mcpu=3000` + maspsx, byte-compare) until `-> MATCH`. The main loop **re-proves +
banks** each match through `tools/dc_bank_c.py` (flips `segments.yml` `.s→.c`, rebuilds, **validates
SHA-1 `af43de22…`**, auto-reverts a bad one) — an agent literally cannot ship wrong bytes. Misses stay
`.s` with the attempt logged. Stop rule: drain the pool or the trailing match-rate falls below ~25%.
Each converted fn's Canon `FUNC_` page is regenerated (`tools/gen_matched_canon_notes.py`). Vault
philosophy honored: C is authored from the disassembly + the runtime-confirmed names + clean-room PsyQ
profiles; **no invented semantics** — undeterminable field meanings are flagged `UNKNOWN` in the source,
the byte-match is the proof.

## Levers (proven — the reusable toolkit)
From the prior `dc` campaign: `g_<hex>`/`sub_<hex>` auto-anchors, callees by census name, `small_data`
gp path, delay-slot early-return, `andi` 16-bit clear, far-global-`>8-bytes` for absolute under `-G8`,
`(void*)0xADDR`→`extern T[]`. **New this campaign (dc-6a batch 1):**
- **reserved-but-empty stack frame** → `char scratch[N]; (void)scratch;` or `volatile int scratch[N]`
  (reproduces `addiu sp,-N … addiu sp,N` with no body stores — beats the "empty-but-framed stub" wall).
- **`$v0`-input non-ABI callback tail** (fall-through continuation reading a pointer left in `$v0`) →
  `register T *p asm("$2"); p->slotN();` (beats the "incoming-$v0" ABI wall).
- **post-store global reload** (retail re-reads a global after writing it) → declare it `volatile`.

## Walls (auto-deferred, never forced)
Beyond the queue-excluded cop2/GTE·syscall·tail-`j`: **regalloc/scheduling divergence** (GCC coalesces a
returned pointer into `$v0` where retail keeps it in `$a0`), **mis-split boundaries** (a fragment reading
uninitialized registers — belongs to a neighbor), **`$ra`-from-`$a3` trampolines**, and
**branch-materialized booleans** the pinned compiler folds to `return x&1`. These stay hand-asm with the
attempt logged in `analysis/compiler_attempts.json`.

## Result (running)
**Batch 1 (dc-6a): 48 smallest game fns → 38 byte-exact C conversions (79% match), resident C 99 → 137.**
SHA-1 held through every bank; 110 safe tests green. 10 deferred (regalloc / mis-split / near-match);
several recoverable with the new levers on retry. Campaign continues game-first then SDK twins until the
pool drains or the match-rate floors. See [[SYS_decomp_substrate]] · [[SYS_function_census]].

**In-session continuation (2026-07-10, NO subagents — per user): resident C 181 → 232.** Drained the
tractable game-plain remainder, then pivoted to dc-6c **SDK/PsyQ library twins** (the small game pool was
down to walls). Game wins: 4 spawn-burst variants, `get_current_actor_xyz` (pointer-to-global base-reg
lever), the 4 plane-projection vec fns (`/1024`,`/2048` + `>>17` reproduce the branchy signed-div idiom;
short-typed siblings frame naturally), `vram_clear_framebuffers` (libgpu ClearImage RECT sequence),
`vm_native_aimed_drop_spawn` + `spawn_drop_burst_effect` (cycling burst + aim-angle branch; **inline
p-relative flag access** avoids an extra saved reg; **reorder a store before the call** to fill its delay
slot). SDK wins (~40): mem/Cd/Spu/Pad/libgpu twins via jal-wrapper + `(ret==0)` sltiu return, GP0 prim
builders, `count-to-(-1)` fill loop (reproduces the reserved frame), hw-reg via **integer-literal cast**
(lui+ori, not symbol lui+offset), short-cast wrappers, bit-pack (`GetTPage`), branch-sense inversion
(`MargePrim` test-and-early-return).

**New WALL classes found this pass (auto-deferred, `analysis/dc_deferred.json`):** (1) **trailing global
store not moved into the `jr` delay slot** — our maspsx won't split a `lui…/sw` pair across the return
the way retail's assembler did (`setRC2wait`, `pad_vsync_latch_consume`, `_spu_FsetDelay{W,R}`,
`_padInitDirSeq`); (2) **mask-constant / address-temp register naming** GCC assigns opposite to retail
(`AddPrim`, `AddPrims`, `StopRCnt`); (3) **spurious `arg→vN` register copy** retail emits that GCC elides
(`SetDefDispEnv`); (4) **1w commutative-`or` operand order** (`SetDrawTPage`); plus the earlier
regalloc/scheduling/large-branchy/`$v0`-input/`ra`-in-`a3`/noise-cursor walls. Match-rate stayed well
above the 25% floor throughout.

**Second push (2026-07-10 cont.): resident C 241 → 263.** Recovered several near-misses with newly-proven
levers and kept mining SDK: **unsigned-cast for `sltiu` range guards** + **in-range-as-main-path branch
structure** + **off-first address arithmetic** cracked the `SsUt*`/`SsVabClose` volume/close family
(`SsUtGetDetVVol`, `SsUtSetDetVVol`, `SsUtKeyOffV`, `SsVabClose`); **integer-literal cast for a held hardware
base**; **vtable fn-ptr call via `(void**)+idx`** (`DrawPrim`, `LoadImage`, `StoreImage`, `DumpTPage`,
`DumpClut`, `pad_mode_check`); the `SetDraw*` prim-builder family (`SetDrawArea`, `SetDrawMode`,
`SetDrawLoad`); memcpy-from-global returners (`GetDrawEnv`/`GetDispEnv`); `StClearRing`, `cd_read`,
`rcnt_interrupt_remove`, `CD_initintr`, `startIntrVSync`, `SpuRead`, `SetGraphDebug`, `SpuInitMalloc`,
`SsSetMVol` (padded on-stack command struct for the frame size). **The readily-convertible pool is now
substantially exhausted** — 79 confirmed walls logged. Remaining ~148 SDK + ~190 game are the hard tail:
large multi-call/fn-ptr inits (`rcnt_interrupt_install`, `MoveImage`, `LoadTPage`), the branchy GPU
`get_*` family (`get_ofs/get_mode/get_dx/get_tw/get_cs/get_ce`), magic-constant divisions
(`SsUtGetVVol`, `note2pitch`, `StFreeRing`, `CdPosToInt`), `*176`-chain `Ss` functions, and the
delay-slot/regalloc toolchain walls. Each further match now costs several authoring iterations.

**Third push (2026-07-10 cont.): resident C 263 → 265** (`VSyncCallback`, `vmNoiseOff`) after a full scan
found only **2** remaining functions with a simple-matchable shape — confirming the readily-convertible
pool is drained.

## Toolchain-unlock investigation (2026-07-10) — CONCLUSION: no safe systematic unlock exists
Prompted to invest in whole-family unlocks before more per-function grinding, I probed the two candidates
and **ruled both out with evidence**:

1. **maspsx delay-slot fill (the "trailing store into `jr` delay" wall).** Dumped the cc1→maspsx pipeline:
   cc1 emits a **bare `j $31`** in reorder mode when the trailing store needs a `lui/sw` pair, and maspsx
   correctly nops it (matching retail). But a scan of all 265 banked `.c` found **300 bare-branch nops
   across 204/265 functions, all matching retail with a `nop` delay** — so retail's aspsx *mostly did not
   fill* jr/branch delays either. `setRC2wait` (retail `lui $at; jr $ra; sw …($at)` — store split into the
   delay) is a **rare exception**, not the rule; an identical construct in banked `advance_parse_cursor`
   (`sw sym; jr; nop`) matches *without* a fill. A "fill the delay slot" maspsx change would therefore
   **break the 204 correctly-nop functions**, and no clean rule distinguishes the fill-cases from the
   nop-cases. **A validation signal keyed on filled delay slots flagged 85/187 KNOWN-matched compiled-C
   functions** (e.g. `spawn_drop_burst_type4`, `actor_turn_toward_player`) — proving GCC-compiled C *also*
   routinely fills delays (loop back-edges, `noreorder` blocks), so filled delays are **not** a hand-asm
   marker and cannot be used to bulk-classify or bulk-fix. **Verdict: unsafe, would corrupt ~half the
   banked work; abandoned.**
2. **Branch-layout match (the `get_*` family).** GCC's basic-block ordering is deterministic per source;
   the divergence is a per-function C-reconstruction problem (already tried condition-inversion on `get_ofs`
   with no effect), not a compiler flag or toolchain pass. **Verdict: no systematic fix; per-function only.**

**Net:** the remaining walls are genuine **per-function GCC-scheduling / source-reconstruction** problems
(and some are likely original hand-written PsyQ asm), not a fixable toolchain gap. There is no shortcut;
further progress is individual reverse-engineering at ~15–20% first-pass yield. The investigation's main
value is a **hard negative result** that prevented a change which would have shattered the byte-identical
build. Resident C stands at **265 / 913** (byte-% unchanged at 98.2%).

## Getting past the scheduling wall — the PERMUTER (tools/dc_permute.py) — WORKS
The scheduling near-misses (2–8w) are a **search** problem, not an impossibility: retail was compiled from
*some* C by *this* compiler, so a byte-identical source provably exists. The decomp-community fix is a
**permuter** — hill-climb semantics-preserving source rewrites, compile each through the real toolchain,
score the byte-diff, converge on the shape GCC schedules identically. We already had the scorer
(`compile_at` + word-diff), so I built `tools/dc_permute.py`: transforms = statement reorder, commutative
operand swap, call-arg/RHS hoist-to-temp, and **block-hoist** (`PREV; f(A,B);` → `{int _a=A,_b=B; PREV;
f(_a,_b);}`), driven by simulated-annealing acceptance + periodic restart-from-best. **It found the
`scene_config_apply` match fully automatically (4w→0w at iter 41)** — the winning rewrite hoists the call
args into a block scope *between* the two scalar stores, exactly the schedule retail emitted. Resident C
**265 → 267** (`_SsVmGetSeqVol` via the held-pointer lever + `scene_config_apply` via the permuter).
**Limits/next:** the minimal transform set cracked the arg-hoist class but not `_SsSndReplay` (base-vs-index
emission, one expression) or `_SsVmGetSeqLVol` (store-vs-table order) — those need the fuller decomp-permuter
transform set (~40: address-split `&a[i]`↔`a+i`, type/cast variation, reassociation, loop-form changes) and
optionally an `m2c` (mips_to_c) seed. The path is proven; scaling it is a tooling investment, not new RE.

## dc-7 Phase 1 — AST permuter built (pycparser); reach and hard limit characterised
Upgraded `tools/dc_permute.py` to **AST transforms** (pycparser 2.22): commutative-swap, reassociation,
address-form `&a[i]`↔`a+i`, `if`-invert-and-swap, statement reorder, scoped/block-top temp hoist, block-hoist,
temp-inline — with simulated-annealing + 2-transform steps. Correctness is enforced by *compile+byte-score*
(a type-wrong transform just fails → discarded), so the set can be liberal. **What it cracks:** the
statement-shape / arg-hoist class — it re-derives `scene_config_apply` in ~5–12 iters, and makes real
progress on branch-layout (`get_ofs` **13w→7w** via `if`-invert) and expression-form (`SetDrawTPage`
**5w→1w** via commutative-swap). **The hard limit:** pure **register-allocation naming** residuals — which
register holds which value — do NOT fall to this transform set even under heavy search: `SetDrawTPage`'s
final **1w** (an `or rs,rt` operand-register order) survived **8 seeds × 4000 iters = 32k attempts**;
`StopRCnt` (3w), `AddPrim` (7w) likewise plateau. Register-naming is set by GCC's allocator from live-range
timing that our shape transforms don't perturb enough. **Conclusion:** the self-contained permuter closes
statement/expression/branch *shape* near-misses but not the *regalloc-naming* tail — which is most of the
remaining ≤9w backlog. Breaking those needs the upstream **decomp-permuter** (its ~40 transforms include
variable-reuse / decl-order / cast-insertion that shift live ranges) + `m2c` seeds — the plan's Phase-3
stretch. `dc_permute.py` stays a reusable asset for the shape class; seeds live in `analysis/dc_permuter_seeds/`.

## dc-7 Phase 3 — upstream permuter integrated; register-naming walls are a READABILITY floor
Integrated simonlindholm/**decomp-permuter** (cloned to `~/abl-toolchain/decomp-permuter`, `pip install toml`):
reused only its **randomizer** (34 passes: variable reuse/rename, type variation, cast/comma no-ops,
decl-order) driven by OUR scorer via `tools/dc_permute_upstream.py` (`Candidate.from_source → randomize_ast
→ get_source`, annealed on `compile_at` byte-diff; round-trip verified: an un-randomized seed re-scores
identically). **It works and it breaks the wall:** chaining self-contained→2w-seed→long upstream run
**cracked `AddPrim`** — a 7w register-naming wall neither permuter closed in short runs — to a verified 0w
MATCH. **But the match is irreducibly tangled:** the winning source is ~40 dead `new_var` assignments +
`x^0`/`(0,y)`/`do{}while(0)` junk; a shrinker (`tools/dc_shrink.py`: inline single-use temps, drop
unused/empty, fold no-ops, re-scoring each reduction) only strips the *truly* dead parts (3259→2556 chars,
still MATCH) — the rest is **load-bearing for the exact register allocation** (removing it → mismatch). The
essential logic is byte-for-byte my clean 2-statement `AddPrim`, but neither that (7w) nor the structural
insight it suggested (read `*ot` once → **14w, worse**) matches. **So for the register-naming class, a
byte-exact source EXISTS but only in an unreadable machine-tangled form — no readable C produces those
bytes.** These walls are a genuine **readability floor**, not merely a search problem: banking permuter
output would raise the raw C-count but ship unreadable, machine-generated C against the campaign's
readable-byte-exact-C goal. **Recommendation: hold at 267 readable functions;** the ~15-20 regalloc-naming
residuals stay `.s`. Phase-3 tools (`dc_permute_upstream.py`, `dc_shrink.py`) are committed reusable assets;
the shape-class permuter (`dc_permute.py`) remains the productive path for future near-misses.

> **Closed (2026-07-10):** superseded by the dc-9/dc-10 m2c pipeline work; the campaign CLOSED at **C = 287/913**. See [[EXP_2026-07-10_m2c_seed_pipeline]] and [[SYS_decomp_substrate]] "Campaign CLOSED".
