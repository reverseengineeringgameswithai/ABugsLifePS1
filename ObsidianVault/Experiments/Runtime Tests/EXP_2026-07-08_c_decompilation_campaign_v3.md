---
kind: experiment
id: EXP_2026-07-08_c_decompilation_campaign_v3
name: Decompilation campaign v3 — dynamically-guided volume push + runtime verification
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_function_census]
artifacts: [tools/decomp_candidates.py, tools/verify_function_runtime.py, config/segments.yml, analysis/decomp_progress.json]
---

# EXP_2026-07-08_c_decompilation_campaign_v3

## Question
Can the Phase-5 dynamic-coverage signal reprioritize matching toward runtime-confirmed
functions, and can the DuckStation debugger API verify function behavior at runtime — to push
the resident byte-match metric up from 8.05%?

## What changed
- **Ranker (6A):** `tools/decomp_candidates.py` now folds the `dynamic` discovery flag into the
  score (`+15` if runtime-confirmed), so Phase-5-executed functions outrank un-executed
  same-size leaves. The queue head became the highest-value named+executed leaves
  (SetTransMatrix, SetRotMatrix, AddPrim, VectorNormal, …). Determinism test stays green.
- **Match batch (6B, ongoing):** 8 small dynamic-confirmed library leaves byte-matched as
  hand-written asm (COP2 `ctc2`/`rtps`/etc. emitted as `.word`; local-only sources per the
  substrate preservation policy): `SetRotMatrix`, `SetTransMatrix`, `AddPrim`,
  `gte_camera_matrix_load`, `RotTransPers`, `_spu_FsetDelayW`, `_param`, `SetDefDispEnv`.
  **Resident matched 86 → 94 (8.05% → 8.8%; asm 10 → 18).** Rebuilt EXE SHA-1-identical
  (`af43de22…`); safe suite green.
- **Runtime verification (6E):** `tools/verify_function_runtime.py` wraps
  `functionBounds` + `xrefsTo` + `callFunction`. Demonstrated:
  - `SquareRoot0(0x100000) → v0 = 0x400` — confirms an **integer square root** (√1048576 = 1024).
  - `flag_ge_threshold(0) → v0 = 1` — clean return, one `jal` caller at 0x800495d8.

## Findings / caveats
- **functionBounds vs census boundary disagreement:** `functionBounds 0x80038f20` reports the
  containing function as `0x80038090..0x800390ec` (4192 B, `confidence:"exact"`, `mergedRegion:false`)
  — i.e. it treats several r2-census functions as one span. The 24-byte census unit
  (`flag_ge_threshold`, byte-matched + validated) is still correct; trust `functionBounds`
  `"exact"` only when the span is small AND matches the census. Recorded in [[DuckStation_API_Index]].
- **callFunction is a real invocation** (mutates state) — run on a throwaway isolated instance,
  after booting ~2000 frames so the resident EXE is loaded.

## Skip log (per the campaign skip rule)
- `0x8004c46c` `mover_vm_op9_set_target` — not a standalone function: a mover-VM jump-table arm
  that `blez`/`j`s outside its 16-byte range. Named, not match-shaped.
- `0x8006cd64` `SpuSetTransferMode` — carve truncated (branches/delay slots); deferred until the
  full disassembly is carved.

## 6B progress + 6C finding
- **6B:** resident matched **86 → 143 built / 142 census-counted (13.3%)** — 57 real functions as
  hand-written asm: GTE matrix loaders + transforms (`SetRotMatrix`, `SetTransMatrix`,
  `gte_camera_matrix_load`, `RotTransPers`, `SquareRoot0` — GTE-LZC integer sqrt, callFunction-
  verified), libgpu prim/env (`AddPrim`, `AddPrims`, `CatPrim`, `MargePrim`, `SetDef*Env`,
  `SetDrawTPage`, `SetPriority`, `get_ofs`, `get_mode`, `_cwc`, `_status`, `_param`), libspu
  (`SpuInitMalloc`, `_spu_FsetDelayW/R`, `_spu_FsetRXX`, `_spu_FgetRXXa`), libc `memmove`.
  (`_status` is byte-exact but in a merged census region so counts 110 not 111.) Still queued:
  `RotAverage4`/`CdPosToInt`/`InitGeom`/`LoadImage` + dozens more SDK leaves — 6B NOT fully closed.
- **6C:** matched NINETEEN REAL game-class functions (`token_descriptor_reskin` 0x8003e760 — seed/token
  sprite descriptor re-skin loop; `spawn_fx_object` 0x800503fc — range clamp; `nearest_pickup_finalize`
  0x80045678 — 8-entry pickup-table scan). More real game functions remain (`fmv_bin_load`,
  `setpiece_spawn_init`, `mosquito_species_callback`, …) — 6C NOT fully closed. All matches byte-exact (SHA-1 `af43de22…`); the seed-plant cluster stays deferred
  (fragments / large dispatchers, see below).
- **6C finding — seed-plant candidates are r2-split FRAGMENTS, not real functions.** The green
  passive handler `0x8005cce8` is a loop-tail/epilogue (`bnez` branches *backward* to 0x8005c0ac;
  new function starts at 0x8005cd2c); `seed_plant_type6/type7_handler` start `lw ...(s2)` using a
  callee-saved reg with no prologue (entered mid-function). The real seed-plant handlers are the
  large jr-table dispatchers. So the cluster has NO clean small committable-C leaves.
- **Ranker fix (6C-enabling):** `tools/decomp_candidates.py` now excludes **fragments** — a
  candidate whose conditional branch or plain `j` targets an address *before* its own start
  (r2 split the tail of a larger routine). Dropped 8 false candidates. A further refinement
  (flag "reads $s0–$s7/$fp before writing, no prologue") would catch the saved-reg-use fragments
  (type6/type7) too — deferred. Real committable-C game targets are the `prologue`-starting
  functions (`fmv_bin_load`, `setpiece_spawn_init`, `mosquito_species_callback`, …).

## Game-function track — CLOSE CRITERIA (decided 2026-07-08)
**TRACK CLOSED 2026-07-08** (clean real-target queue exhausted; 19 game functions matched). The open game-function byte-matching track **closes when the ranker queue holds no remaining
CLEAN real target** — i.e. every remaining `classification: game` candidate is a fragment
(backward-branch / saved-reg-before-write), a computed-jump/jr-table dispatcher, or oversized
with no clean linear byte-match path. Large-but-linear real prologue-starting functions stay IN
SCOPE while they exist. The track does **not** stay open for "broader exhaustion" of jr-table/
oversized dispatchers — those are a separate, ranker-excluded class, explicitly OUT of scope
(they'd need substrate work, not transcription). Rationale: "broader exhaustion" has no
well-defined finish line; the clean-real-target queue does.

## Continuation
- 6B: `memmove`/`SquareRoot0`/`RotAverage4` + more SPU/CD leaves via `decomp_candidates.py --top N`.
- 6C: committable C on the real prologue-starting game functions; optionally extend the fragment
  guard to saved-reg-use detection first.
- 6D: more overlay leaves via `build_overlay.py --candidates` (12 easy identified).

## Evidence / links
[[SYS_decomp_substrate]] · [[SYS_function_census]] · [[EXP_2026-07-08_trace_naming]] ·
[[EXP_2026-07-08_c_decompilation_campaign_v2]] · [[DuckStation_API_Index]].

> **Closed (2026-07-10):** superseded by campaign v4/v5 and the dc campaign (final **C = 287/913**, [[SYS_decomp_substrate]]).
