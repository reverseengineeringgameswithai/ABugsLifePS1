---
kind: experiment
id: EXP_2026-07-08_substrate_v3
name: Substrate v3 — size-cap removal / gp scaling / jr-table dispatchers (capability-first)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_function_census]
fixtures: []
artifacts: [tools/decomp_candidates.py, tools/function_census.py, analysis/extent_overrides.json, config/segments.yml, analysis/decomp_progress.json]
---

# EXP_2026-07-08_substrate_v3

## Question
The metric is 13.8% by function but only ~2.6% by code *bytes* — the matched set is
small leaves. 81% of unmatched code bytes live in the 224 functions the ranker excludes
as >0x200 / gp / jr-table. Can each excluded class be unlocked and *proven* on real code,
so the byte-% has a path up? Capability-first: prove all three with a proof batch each,
leave the volume grind as documented continuation (mirrors how substrate v2 was landed).

## Method
Per class: quantify the excluded bucket in the ranker, verify extents
(`debugger.functionBounds` / r2 boundary re-check) before treating a large span as one
function, match the *smallest* verified members as hand-asm via the existing loop
(author → `segments.yml attempted:` → `build_psx_exe.py && validate_build.py` SHA-1 PASS →
`function_census.py` → `run_safe_tests.py`). Defer >0x800 giants as "matchable, deferred
to a real C-decomp track" rather than force-transcribe.

## Observations
- **v3.1 — size cap was the only blocker for large-but-linear (biggest byte lever, no new
  machinery).** Sub-classified the ranker's oversized bucket
  (`tools/decomp_candidates.py`): of 213 excluded-as-oversized, **117 are large-but-linear**
  (no gp / no jr-table, end in `jr ra`), 72 gp, 24 jr-table. Proof: `checkpoint_save`
  0x80054c90 (540 B — first >0x200 match) matched first try. The 0x200 cap was artificial.
- **v3.2 — the gp `small_data` path scales beyond getters.** Two committable-C gp *setters*
  matched: `reset_pickup_state` 0x800252a0 (`sh zero,0x732(gp); sw zero,0x5dc(gp)`) and
  `set_gp_ptr_plus_c` 0x8005d50c (`addiu a0,0xc; sw a0,0x584(gp)`). Compiler-proof ledger
  (`analysis/compiler_attempts.json`) records both (`-O2 -G0 -mcpu=3000`; the `-G8`
  small-data path is the *build* toolchain, the grid found `-G0` also reproduces these).
- **v3.3 — jr-table dispatchers need NO pooled-table placement machinery; the v2 "remaining
  constraint" was over-stated for the hand-asm route.** Two real switch dispatchers matched
  byte-exact: scene-verb dispatch 0x80054810 (18-case, 340 B) and `scene_verb_dispatcher`
  0x80054964 (17-case, 328 B). Both read their jump table by **absolute immediate**
  (`lui $at,0x8002; addu $at,$at,a0<<2; lw $v0,-0x4b4c($at)` → table @0x8001b4b4 / 0x8001b4fc)
  and the table lives in the rodata pool the byte-splat substrate **copies verbatim**. So the
  dispatch bytes match with the table addressed absolutely — no external placement, no
  relocation. The only real blocker was the **census extent**: r2's `realsz` truncates a
  dispatcher at its jr-table, splitting one function into a small head + a spurious `gap_code`
  tail (the case bodies). Fixed with a deterministic **extent-override** hook
  (`analysis/extent_overrides.json` + `tools/function_census.py`): pin the real end so the
  head absorbs its case bodies; the gap-recovery then finds no orphan jal sites. Both bogus
  `gap_code` records disappeared; the 18/17 case bodies + shared epilogue are now one function.

## Remaining constraint (honest)
- The pooled-table concern from [[EXP_2026-07-08_substrate_v2]] is **resolved for the hand-asm
  route** (absolute-VA table reference; table copied verbatim). It is **still open only for the
  C-compilation route**: a C `switch` emits an *inline* jump table adjacent to the function, so
  its `lw table(at)` offset differs from the game's pooled table. Byte-matching a dispatcher
  *from C* would still need the inline table pinned at the pooled VA — deferred to a future
  real-C-decomp track (out of scope for the byte-metric push, which uses hand-asm).
- **Giants (>0x800) are matchable-in-principle but impractical to hand-transcribe** — proof
  batches use the smallest members of each class; the giants are logged as deferred.

## Result
Resident matched **145 → 147 census-counted / 148 built (13.79%)**; bytes ~2.59%. jr-table
candidate exclusions 13 → 11. SHA-1 `af43de22…` PASS throughout; safe suite 78 green. The
three levers (raise `--max-size`, gp scaling, jr-table via extent-fix + absolute tables) are
each proven on real code; the full volume grind (117 large-linear + 58 small-gp + more
dispatchers) is documented continuation. Hand-asm sources are local-only (gitignored); the
metric rises purely by `segments.yml attempted:` + census regen. See [[SYS_decomp_substrate]] ·
[[SYS_function_census]] · [[EXP_2026-07-08_c_decompilation_campaign_v3]].
