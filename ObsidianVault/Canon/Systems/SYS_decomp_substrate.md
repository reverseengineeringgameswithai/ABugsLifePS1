---
kind: system
id: SYS_decomp_substrate
name: Decomp substrate (compile/link/asm-diff)
aliases: [Blocker_-_Decompilation_has_no_build_or_symbol_substrate]
status: live_confirmed
confidence: confirmed
source_state: original_game
functions: []
memory: []
tables: []
constants: []
evidence:
  - EXP_2026-07-08_first_matched_functions
  - EXP_2026-07-08_psyq_compiler_proof
  - EXP_2026-07-08_first_c_match
  - EXP_2026-07-08_c_decompilation_campaign_v1
  - EXP_2026-07-08_c_decompilation_campaign_v2
  - EXP_2026-07-08_substrate_v2
  - EXP_2026-07-08_c_decompilation_campaign_v3
  - EXP_2026-07-08_substrate_v3
  - EXP_2026-07-09_decomp_v5_bytepercent
  - EXP_2026-07-08_pseudocode_conversion_v2
  - EXP_2026-07-08_overlay_track
  - EXP_2026-07-08_trace_naming
  - EXP_2026-07-08_c_decompilation_campaign_v4
  - EXP_2026-07-08_understanding_campaign_u1
  - EXP_2026-07-09_c_decompilation_at_scale
  - EXP_2026-07-10_c_conversion_at_scale
  - EXP_2026-07-10_m2c_seed_pipeline
src_paths: [docs/SUBSTRATE.md, config/segments.yml, config/linker.ld, tools/build_psx_exe.py, tools/validate_build.py, tools/asmdiff.py, tools/split_exe.py, tools/substrate_common.py, tools/function_census.py, tools/compiler_proof.py, tools/dc_bank_c.py, tools/dc_permute.py, tools/dc_readable.py, tools/dc_m2c_seed.py, tools/dc_m2c_sdk_sigs.py, analysis/psyq_sdk_sigs.json, analysis/dc_deferred.json, analysis/extent_overrides.json, tests/test_substrate.py]
---

# SYS_decomp_substrate

## Purpose
The reconstruction build for `SCUS_942.88`: byte-splat model — original bytes
everywhere, except functions listed in `config/segments.yml` `attempted:`,
which are assembled from `asm/hand_written/*.s` at their original VA and must
be byte-identical. Closes the archived blocker B1 claim "C cannot be
compiled/linked/diffed" for the assembly layer. Full operating manual:
`docs/SUBSTRATE.md`.

## Current generated state (2026-07-10, dc campaign CLOSED)
The whole-function manifest contains **913 resident replacements**:
**626 hand-asm + 287 C = 381,684 / 388,644 code bytes (98.209%)** (authoritative:
`analysis/re_campaign_status.json`; byte-% is unchanged by C conversion by design — see
"C-Decompilation at Scale" below). The percentage is lower than the earlier v5 report because
analyzer-created interior labels are no longer counted as functions and three large,
only-partially-transcribed ranges are honestly unmatched. The residual includes unmatched
functions/padding tracked by the census rather than silently counted as source. Two levers:
(1) reclassified 16 KB of **data-in-code** — symbol-only VM/metadata tables (`0x80077xxx`) + dispatch pools —
out of the code denominator (the census now marks `discovery:['symbol'] && no jr ra`, and all-identical-word
fills, as `range_type:data`); (2) hand-asm every remaining function.
> **Byte-% is not understanding.** All 946 resident code functions are now *classified*
> (46 BIOS thunks / 1 crt0 / 519 game / 380 SDK, 0 `unknown`-class per the status file), but
> byte transcription carries no semantic claim — understanding is tracked separately
> (semantic naming / `naming_priority.json`; the sc campaign's naming residual is load-time
> functions the runtime accelerator cannot reach).

## Confirmed behavior
- Pipeline: GNU `as -march=mips1 -mabi=32 -EL -no-pad-sections -G0` →
  `ld -m elf32ltsmip -T config/linker.ld --defsym __va=<start>`
  (`elf32-tradlittlemips`, `SUBALIGN(4)`) → `objcopy -O binary` → splice at
  `file = va − 0x80010000 + 0x800`.
- `tools/validate_build.py` PASS = rebuilt image SHA-1 == `af43de22…`
  (byte-splat ⇒ exact by construction; each attempted function proves itself).
- **10/10 first-wave functions matched byte-exactly on first build**
  (2026-07-08): 6 BIOS-A0 thunks (`InitHeap` 0x39, `strcat` 0x15, `strcpy`
  0x19, `strlen` 0x1b, `memcpy` 0x2a, `rand` 0x2f), `__main`, and real-logic
  libgpu leaves `GetClut`, `TermPrim`, `GetTPage` (60 B, 15 instructions).
- `census_symbols.inc` (generated per build) lets sources `jal` engine
  functions by name; jal-to-absolute-`.equ` encoding proven by synthetic test.
- `asm/` is untracked (derived from the copyrighted EXE); matched sources are
  drift-pinned in `tools/repro_inputs.sha256` (absent=skip, drifted=FAIL).

### Campaign v1 (2026-07-08) — [[EXP_2026-07-08_c_decompilation_campaign_v1]]
- **27 functions reconstructed (10 asm + 17 C)** — 2.53% of resident functions
  (`analysis/decomp_progress.json`); `validate_build.py` SHA-1 PASS throughout.
- **auto-defsym**: undefined symbols resolve by explicit `externs` > census
  function name > address-anchored name (`sub_/g_/D_<hex>`) — C sources call
  engine functions / reference globals with no hand-listing.
- **ranker** `tools/decomp_candidates.py` → `analysis/decomp_candidates.json`
  (excludes matched/data-globals/truncated/jr-table/oversized/gp; scores by
  size + callees + behavior-known); **progress metric**
  `analysis/decomp_progress.json`.
- Each matched function has a Canon `FUNC_<addr>` note
  (`tools/gen_matched_canon_notes.py`): `calls` → callee ids, `src_paths` →
  the `src/main` C, `evidence` → the campaign EXP.

## The C gate — OPEN (2026-07-08)
Both conditions met: (1) ≥10 matched asm functions, and (2) the original
compiler proven — GCC **2.7.2** (PsyQ 4.0-era) `-O2 -G0 -mcpu=3000` + maspsx
`--dont-expand-li --expand-div` (the `--expand-div` pin added 2026-07-10 — retail's
division guards are ASPSX div-macro expansion; SHA-1 re-verified), pinned in
`config/segments.yml c_toolchain` and documented
in [[SYS_original_compiler]]. The final generated status (campaign close,
2026-07-10) is **287 resident C functions / 20,304 bytes**, plus 626 hand-asm
functions. `src/main/*.c` are committed authored reimplementations.

### Clean-room declaration and section profiles
- `config/declaration_profiles.yml` selects source-local, clean-room ANSI,
  clean-room K&R, or owner-supplied external PsyQ declarations. Original
  headers remain outside the repository; `tools/psyq_header_oracle.py` records
  only relative names and SHA-256 hashes.
- Per-entry `sections:` uses `config/linker_split.ld` to place compiler-emitted
  text, rodata, and data independently. This removes pooled jump-table placement
  as a substrate blocker; remaining switch mismatches are ordinary codegen.
- An assembly entry may use ordered `parts:` when corrected function boundaries
  join adjacent transcriptions. Partial fragments are not claimed as functions.

### Gate rules (what may enter src/main/)
- Only functions **registered in `config/segments.yml attempted`** with
  census-exact extents, that **build byte-exact** (`validate_build.py` stays
  SHA-1 PASS at every commit).
- Absolute-addressed globals are resolved via the entry's `externs:` map
  (name → VA, `--defsym` at link); no invented field semantics.
- Every C candidate's flag sweep is logged to `analysis/compiler_attempts.json`.
- **No broad decompilation** — one function at a time, each proven.

## substrate v2 (2026-07-08, [[EXP_2026-07-08_substrate_v2]])
Three linker/toolchain changes, each opt-in / non-regressing (all 80 prior matches
stay SHA-1-identical):
- **`--section-start=.out=<va>` RESOLVED the internal-`j` class.** Root cause:
  `--defsym __va` never reached the linker-script `DEFINED(__va)?__va:default`
  ternary, so the section landed at the 0x80010000 default. Harmless for
  position-independent code (branches / absolute-external `%hi/%lo` / `jal`) but an
  internal `j` to a LOCAL label (if/else & bounds-check merges) resolved against the
  wrong base. Pinning the section at its true VA fixes it. Proofs: SetSemiTrans,
  SetShadeTex, CdComstr, CdIntstr (4 byte-exact). CdComstr/CdIntstr also needed the
  default-string default referenced as an address-anchored **symbol** (la %hi/%lo,
  sign-adjusted) not a raw `(char*)` constant (lui/ori).
- **gp-relative RESOLVED** via per-entry `small_data: true`: compile+assemble with
  `-G8` (small-data threshold) so `lw $2,sym` macros expand to gp-relative
  (`%gprel`/R_MIPS_GPREL16), and link with `_gp` (top-level `gp: 0x80081d98`). Proofs:
  `0x80046B14`, `0x80045D5C` (2 byte-exact). Guarded by `test_synthetic_gp_relative`.
- **switch/jr-table mechanism PROVEN, real-game constraint remains.** With
  `.rdata*` added to the linker script + `--section-start`, cc1's inline switch
  jump table (`.rdata .word $Ln`) places correctly and its R_MIPS_32 entries resolve
  to the exact case-label VAs (synthetic end-to-end proof; `jr` dispatch verified).
  REMAINING gap: real game switches keep their jump tables in a **shared rodata pool
  at a fixed address** (e.g. table @0x8001B778 for the switch at 0x800593E8), placed
  BEFORE the function — a C `switch` emits an *inline* table (adjacent), so its
  `lw table(at)` offset differs. Byte-matching a game switch needs the table at its
  pooled address (external data blob) or a function whose table is adjacent; this is
  a data-placement concern, not a linking one. Census extents on switch dispatchers
  are also frequently mis-split (default target beyond the recorded end).

## substrate v3 (2026-07-08, [[EXP_2026-07-08_substrate_v3]])
Capability-first push to unlock the byte-% (13.8% by function but ~2.6% by *bytes* — the
matched set is small leaves; 81% of unmatched code bytes are in the ranker-excluded
>0x200 / gp / jr-table classes). Three levers, each proven on real code, all SHA-1-identical:
- **Size cap was artificial (biggest byte lever, no new machinery).** The ranker's oversized
  bucket sub-splits into **117 large-but-linear** (end in `jr ra`, match today), 72 gp, 24
  jr-table. Proof: `checkpoint_save` 0x80054c90 (540 B) matched first try.
- **gp `small_data` path scales to setters** (committable C): `reset_pickup_state` 0x800252a0,
  `set_gp_ptr_plus_c` 0x8005d50c — beyond the two v2 getters.
- **jr-table dispatchers need NO pooled-table PLACEMENT — the v2 "remaining constraint" was
  over-stated for the hand-asm route.** Real dispatchers address their jump table by **absolute
  immediate** (`lui 0x8002; lw -0x4b4c(at)` → table @0x8001b4b4), and the table sits in the
  rodata pool the byte-splat copies **verbatim** — so the dispatch matches with no external
  placement or relocation. The only real blocker is the **census EXTENT**: r2 truncates a
  dispatcher at its table, splitting it into a head + spurious `gap_code` tail. Fixed by a
  deterministic extent-override (`analysis/extent_overrides.json` + `tools/function_census.py`:
  pin the real end so the head absorbs its case bodies). Proofs: 0x80054810 (18-case, 340 B),
  0x80054964 `scene_verb_dispatcher` (17-case, 328 B) — both byte-exact.
  - Still open ONLY for the C-compilation route: cc1 emits an *inline* switch table (adjacent),
    so byte-matching a dispatcher *from C* would need it pinned at the pooled VA — deferred to a
    future real-C-decomp track (the byte-metric push uses hand-asm).

## C-Decompilation at Scale (dc, 2026-07-09, [[EXP_2026-07-09_c_decompilation_at_scale]])
Turning the 837 hand-asm transcriptions into readable byte-exact C (raises the **C fraction**, not
byte-%, which is already matched either way). Resident C **80 → 99** so far; all SHA-1-identical.
**dc-2/dc-3 closed** at the tractable-core boundary (cheap clusters harvested — the `sfx_voice_manager`,
`music_play_*`, and `vsync_wait_glue` families); the remaining game singletons + large sibling families
+ SDK library twins are documented continuation (low marginal understanding value, resume-anytime).
- **Honest convertibility selector** `tools/asm_to_c_candidates.py` → `analysis/asm_to_c_queue.json`.
  Over the `.s` entries it flags the sub-cases that byte-exact C **cannot** express even when the route
  is otherwise linear: **cop2/GTE** register moves (`swc2/lwc2/cop2`), **BIOS syscall/break**, and an
  **internal tail-`j`** (terminates by jumping into the MIDDLE of a shared routine — e.g. the mover-VM
  dispatch loop — a fallthrough, not a return). Result: 593 genuinely-ready (194 game); ~47 nominally-
  "plain" leaves are actually blocked by these. This corrected the earlier over-count.
- **Authoring levers proven (each a byte-exact match, per-function idiom):**
  1. **Early-return in the delay slot** — write `if (ok) return expr; return 0;` (NOT `if (!ok) return 0; …`)
     so GCC folds the `return 0` into the guard's branch delay slot (proof: `checkpoint_player_state_read`).
  2. **16-bit clear is `x &= 0xfffe`** (one `andi`), NOT `x &= ~1` (which expands to `li -2; and`)
     (proof: `transition_finalizer_subsystem_reset`).
  3. **Force a far global out of small data** under `-G8` by declaring it **>8 bytes**
     (`extern int g_ADDR[3]`); a gp function that also touches a distant scalar otherwise hits
     `R_MIPS_GPREL16 relocation truncated` (proof: unblocked `player_sector_lookup`'s relocation).
  4. **`(void*)0xADDR` literal → `extern T g_ADDR[]`** so GCC emits the `la` (lui+addiu) macro, not
     `lui/ori` (proof: `sfx_voice_manager_glue_0d1c` default sample bank).
  5. **Sibling functions convert as near-copies** once the family template matches (the
     `sfx_voice_manager_glue*` trio; the `music_play_once/looping` pair).
- **Bank tool** `tools/dc_bank_c.py`: compiler_proof → install → flip `segments.yml` `.s→.c` → build +
  SHA-1 validate, auto-revert on any failure (handles author-in-place `src/main/*.c`).
- **Deferred classes (stay `.s`, attempt logged) — never forced:**
  - **regalloc / reassociation divergence** — GCC's register choice or expression association differs and
    no readable-C form recovers the bytes (`spawn_fx_object` leaf-frame; `player_sector_lookup` reassoc).
  - **non-standard `v0`-input glue** — many small "glue" leaves *read* `v0` (or another non-arg register)
    at entry before defining it: the caller left a value there. This is not expressible in standard C
    (params arrive in `a0-a3`). Common in the `cd_ready_poll_control`/`event_*`/`dma_callback` glues.
  - **epilogue delay-slot scheduling** — the retail codegen sometimes fills the `jr $ra` delay slot with
    the `addiu $sp` frame-restore (`jr; addiu` vs `addiu; jr`); GCC's choice can differ on functions with
    several saved registers (`pad_subsystem_init` pair). A ~2-word diff, not worth contorting source.
  - Note: a raw `jalr` to a fixed BIOS B-table address (`jalr $ra,$t2` with `t2=0xb0`) is likewise not
    C-expressible; treat like the cop2/syscall blockers.
- **Ratchet:** `tests/test_re_campaign_status.py` pins the resident-C count; it is bumped per batch and
  `analysis/re_campaign_status.json` regenerated (`tools/re_campaign_status.py --write`).

## m2c-seeded pipeline (dc-9, 2026-07-10, [[EXP_2026-07-10_m2c_seed_pipeline]])
`tools/dc_m2c_seed.py` drives the **m2c** (mips-to-c) decompiler as an automatic *seed* generator for the
branchy grind pool, scoring its output through `dc_permute.score` and gating banks through `dc_bank_c`
(so a bad seed can never enter the build). Wall census first pinned the achievable ceiling: of the 638
remaining `.s`, **~240 convertible / ~398 walls → ceiling ≈ 515/913 (~56%)**; the convertible pool is
only ~19 clean vs **221 branchy-grind**, which is what m2c targets.
- **What m2c recovers (the hard part): control flow + exact global addresses + call targets.** `get_mode`
  auto-decompiled to the same 9w as the hand seed *with* the sign-extended address already correct.
- **Input-fidelity fixes required** to feed m2c our asm: translate `.word 0x.. # jal 0xADDR` back to real
  `jal sub_ADDR` (our byte-exact `.s` encode calls as `.word`; m2c reads `.word` as data and truncated
  every call-containing function — the biggest single blocker, 2856 calls); concatenate multi-part
  functions (27); concretize m2c's `?` unknown-type placeholder.
- **Blocker for full automation — lost load width.** m2c renders a pointer-arg field as `argN->unkHEX`
  (offset, no width): a word store and a byte store are indistinguishable, so **255 / 309** convertible
  functions come out wrong-size. Raw auto-match yield ≈ 0; the seeds are structurally right but need a
  **width-recovery layer** before they byte-match. `--no-unk-inference` / typed args / `--dump-typemap`
  do not surface the inferred widths.
- **Width-recovery layer BUILT (2026-07-10)** — a 2-pass struct-inference round-trip (pass 1 collects a
  pointer-arg's offsets → context declares it `struct { char unk_0[N]; }` → pass 2 emits the struct with
  correct field widths) plus three companion normalizations (global fn-ptr-call wrap, `**(void*)` element
  backfill, literal-address→`g_<hex>` anchoring to stop GCC CSEing a base across reuses). **Validated:**
  `CD_vol` auto-reproduces at 0w; the unattempted dispatcher `sub_80072f8c` auto-seeded to 3w and a
  one-line callee-signature fix banked it (0w, **first pipeline conversion**, C 275→276).
- **Signature-context expedite (2026-07-10)** — from a web survey of the PS1 decomp community (sotn-decomp,
  mgs_reversing, nix-decomp-psx; open SDK headers PSn00bSDK/PsyCross), the standard accelerator is feeding
  m2c a `--context` of function signatures so it stops guessing callee arg-counts per call. Implemented
  cleanroom-safe from our OWN banked source: `_signature_context()` emits `<ret> sub_<hex>(<args>);` for
  every `src/main/*.c` (types coarsened to void*/int). `sub_80072f8c` now auto-matches 0w with no
  hand-editing (was 3w + a manual fix); the effect compounds as banking proceeds.
- **Levers #1+#2 built (dc-10, C 276→277)** — cross-function inference (append unbanked callee asm so m2c
  infers sigs from bodies) + a coarsened public-PsyQ signature map (`analysis/psyq_sdk_sigs.json`, 22 fns,
  cleanroom interface facts vs PSn00bSDK — no layouts). Batch barely moved (`match 0→1`, `cc_error 288→286`):
  the unattempted pool is dominated by COMPILE errors (computed struct pointers `(v+0x80090000)->unkHEX`,
  void\* global derefs, saved_reg artifacts), not signatures. The levers pay off in the per-function grind
  (fewer hand-fixes) — new auto-match `_SsTrapIntrVSync` banked. Remaining: `decomp-permuter-psyq` eval.
- **Standing:** m2c is a proven per-function *accelerator* — `dc_m2c_seed.py --save <addr>` gives a
  structurally/address/width-correct seed (with callee signatures now auto-resolved for banked callees) to
  finish and bank through the SHA-1 gate. Unattended batch banking still needs the idiom long tail closed;
  the ~44% wall fraction is unaffected.

## dc-10 grind + `--expand-div` toolchain fix (2026-07-10, [[EXP_2026-07-10_m2c_seed_pipeline]])
- Worked the m2c closeness worklist to the floor: **21 → 5 candidates; 10 banked (C 277→287)** —
  `SetDefDrawEnv`, `_SsInit`, `FntLoad`, `sub_800709ac`, `StGetBackloc` (mis-split healed), `CdInit`,
  `CdReadBreak`, `_otc`, `boot_subsystem_init`, `sub_80055db0`. Deferrals + walls recorded in
  `analysis/dc_deferred.json`.
- **Toolchain pin updated:** `c_toolchain.maspsx_args` now `["--dont-expand-li", "--expand-div"]` —
  retail's variable-division guards (`break 7` zero-div, `break 6` overflow) are ASPSX div-macro
  expansion. SHA-1 re-verified byte-identical; required for div-bearing C (`sub_80055db0` first).
  `compiler_proof` grid + `dc_permute` + `dc_m2c_seed` synced.
- New authoring levers (returned-temp tail stores, address-giv counter vs loop reversal, shared-counter
  role swap, cross-call base pointer, volatile store targets, goto-retry vs invariant hoisting,
  struct-local dead stores, K&R short-param re-extension) and the residual **phantom-copy /
  allocation-order wall class** (`_dws`/`_drs`/`sub_80073578`/`sub_80043184`, exact size, 16–117w) are
  documented in the EXP note.

## Campaign CLOSED — pivot to modding (2026-07-10, operator decision)
The dc campaign stops at **C = 287/913 (~56% of the ~515 achievable ceiling)**: the worklist floored
at 5 candidates, all in the phantom-copy/allocation-order wall class or mis-splits, each costing hours
of SDK-internal puzzle-solving with no modding value. **Standing practice: decompile ON DEMAND** — when
a mod regression lands in an un-decompiled function, `tools/dc_m2c_seed.py --save <addr>` produces a
structure/address/width-correct C seed to read or finish through the same `dc_bank_c.py` SHA-1 gate.
Do not resume pool-grinding without a new lever for the allocation-order wall class. The regression
gate for modded discs is `mod/smoke_test.py` ([[EXP_2026-07-10_mod_smoke_gate]]).

## Unknowns
- Optimization level RESOLVED = **-O2** (campaign v1, `0x800457A0`
  discriminates); see [[SYS_original_compiler]].
- **Internal-`j` + gp-relative RESOLVED** in substrate v2; **jr-table dispatchers RESOLVED**
  for the hand-asm route in substrate v3 (absolute-VA table + extent-override; above). Pooled-
  table placement remains a gap ONLY for compiling a `switch` *from C* (inline table) — deferred
  to a real-C-decomp track.
- The big understood cluster (`dat_parser`, `source3f_dispatch`, HUD/walker,
  ~1.5–1.8 KB) DEFERRED to a depth milestone.
- Whether GCC 2.7.2 matches ALL game code or the game mixed compilation units
  (2.8.0/2.8.1 remain in the sweep; attempts log prevents rework).
- Whether GNU as can reproduce EVERY byte pattern in larger functions
  (branch-around-literal idioms, GTE cop2 syntax); armips is the recorded
  fallback per `docs/SUBSTRATE.md`.
- Overlay reconstruction (substrate v1).

## Evidence
- [[EXP_2026-07-08_first_matched_functions]] — 10/10 byte-exact + whole-image
  SHA-1 PASS.
- Relates: [[SYS_function_census]] (extent source of truth) ·
  supersedes the "no build substrate" claim of archived
  [[Blocker_-_Decompilation_has_no_build_or_symbol_substrate]] (B1, asm layer).
