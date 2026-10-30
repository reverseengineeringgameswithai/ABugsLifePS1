# Decomp Substrate v0 — compile/link/asm-diff

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)

The minimal reconstruction build for `SCUS_942.88`: carve the image along the
**function census** (`analysis/functions.json`), re-emit everything as original
bytes, and replace individual functions with bytes assembled from source —
verifying byte-identity at every step. This is a NEW track parallel to the
notes-only hand-decompilation in [DECOMPILATION_PLAN.md](DECOMPILATION_PLAN.md)
(`src_re/` is untouched) and separate from the `mod/` patch pipeline.

## The byte-splat model

`tools/build_psx_exe.py` copies the owner's original EXE and splices in ONLY
the functions listed under `attempted:` in `config/segments.yml`, each
assembled from `asm/hand_written/<addr>_<name>.s` at its original VA
(`as -march=mips1 -mabi=32 -EL` → `ld -m elf32ltsmip -T config/linker.ld
--defsym __va=<start> --section-start=.out=<start>` → `objcopy -O binary`).
Consequences:

- The build is **byte-exact by construction**; `tools/validate_build.py`
  (rebuilt SHA-1 == `af43de22…`) must pass at every commit.
- Each new `attempted` entry proves only itself; a failed match points at
  exactly one function (`tools/asmdiff.py` shows word-level disassembled diffs).

## substrate v2 — self-referential addressing (2026-07-08)

Most functions are position-independent (branches are PC-relative; `%hi/%lo` and
`jal` resolve to absolute *external* symbols), so their bytes don't depend on where
the section is linked. Three classes DO reference the function's own section or the
runtime `$gp`, and need extra care:

- **Internal `j`/jr-table (local R_MIPS_26 / R_MIPS_32)** — `--section-start=.out=<va>`
  pins the section at its true VA so a `j` to a local label (if/else & switch merges)
  and a switch jump table's `.word $Ln` entries resolve to the correct VAs.
  `--defsym __va` alone does NOT (it never reaches the linker-script ternary). The
  linker script also catches `*(.rdata*)` (cc1 emits switch tables there).
- **gp-relative** — mark the entry `small_data: true`: cc1 + `as` run at `-G8` so
  small globals are addressed `%gprel` (R_MIPS_GPREL16), and the link defines `_gp`
  from the top-level `gp:` in `segments.yml`. Opt-in per entry; `-G0` matches unchanged.
- **Split sections** — C entries with `sections:` use `config/linker_split.ld`
  to place `.text`, `.rdata`, and `.data` at independent retail VAs. This covers
  pooled switch tables; `test_synthetic_split_text_rdata` proves the route.
  Census extents still need correction when an analyzer splits inline cases.

## substrate v3 — size cap, gp scaling, jr-table dispatchers (2026-07-08)

Capability-first push to raise the byte-% (matched set was small leaves — ~2.6% of code
*bytes*). Three levers, each proven on real code, all SHA-1-identical:

- **Size cap was artificial.** The ranker's oversized bucket sub-splits into large-but-linear
  (end in `jr ra` — match today with the existing loop), gp, and jr-table. `checkpoint_save`
  0x80054c90 (540 B) matched first try — the 0x200 cap was the only blocker for the linear set.
- **gp `small_data` path scales to setters** (`reset_pickup_state` 0x800252a0,
  `set_gp_ptr_plus_c` 0x8005d50c), not just the v2 getters.
- **jr-table dispatchers need NO pooled-table placement — hand-asm route.** A real dispatcher
  addresses its jump table by **absolute immediate** (`lui 0x8002; addu at,at,a0<<2;
  lw v0,-0x4b4c(at)` → table @0x8001b4b4) and the table sits in the rodata pool the byte-splat
  **copies verbatim** — so the dispatch bytes match with no external placement or relocation.
  The only real blocker is the **census extent**: r2's `realsz` truncates the dispatcher at its
  table, splitting one function into a head + a spurious `gap_code` tail. Fix = a deterministic
  **extent-override** in `analysis/extent_overrides.json` (applied by `tools/function_census.py`,
  resident space only): pin the real end so the head absorbs its case bodies; the gap-recovery
  then finds no orphan sites. Proofs: 0x80054810 (18-case, 340 B), 0x80054964 (17-case, 328 B).
  Pooled-table placement for C is now handled by the split-section path below.

## declaration profiles, split sections, and corrected assembly parts

- `config/declaration_profiles.yml` defines source-local, clean-room ANSI,
  clean-room K&R, and external-PsyQ profiles. The external profile requires
  `ABL_PSYQ_INCLUDE`; header contents never enter the repository, while
  `tools/psyq_header_oracle.py` emits hash-only evidence.
- A C entry may declare `sections: {text: ..., rdata: ..., data: ...}`. Each
  emitted section is linked at its own VA and byte-compared independently.
- An assembly entry may list ordered `parts:` to join adjacent transcription
  files after a false interior function boundary is removed. Parts must be
  contiguous and the outer range must equal the corrected census function.
- `compiler_proof.py --profiles ... --small-data` sweeps declaration shape and
  `$gp` behavior while including the source hash in each attempt key.

To correct a mis-split dispatcher extent: verify the real end (`debugger.functionBounds` or an
r2 boundary re-check — the function ends at its shared epilogue `jr ra` + delay nop, just before
the next start), add `"0x<start>": {"end": "0x<end>", "reason": "..."}` to
`analysis/extent_overrides.json`, regenerate the census, then register the full range in
`segments.yml`. See [[EXP_2026-07-08_substrate_v3]] and [[SYS_decomp_substrate]].

## Layout

| Path | Tracked? | Role |
|---|---|---|
| `config/segments.yml` | yes | image identity + the `attempted` registry |
| `config/linker.ld` | yes | one-function-at-VA link script (`elf32-tradlittlemips`, `SUBALIGN(4)`) |
| `tools/{split_exe,build_psx_exe,validate_build,asmdiff}.py`, `tools/substrate_common.py` | yes | the pipeline |
| `asm/nonmatchings/resident/` | **no** (regenerable) | per-function r2 reference listings carved by `split_exe.py` |
| `asm/hand_written/` | **no** (derived work: assembled bytes ≡ original) | assemblable sources for attempted functions |
| `build/substrate/` | no | rebuilt image, build manifest, `census_symbols.inc` |

`asm/hand_written/` is local-only by preservation policy (its content encodes
the copyrighted machine code). Every assembly source consumed by
`config/segments.yml` is centrally pinned in `tools/repro_inputs.sha256`; a clean
checkout provisions that exact set with
`python3 tools/verify_repro_inputs.py --provision`, and missing bytes are a hard
failure rather than a skip. An entirely new checkout can provision the full
central preservation set and the pristine staging tree with
`python3 tools/provision_clean_checkout_inputs.py`; it verifies sources before
copying and never overwrites an existing mismatched target. Canon-referenced
local disassembly listings are included in that central set as individual pins.
Whole-image census metadata is pinned separately in
`tools/re_baseline_inputs.sha256`; the census reads overlay bytes only from the
pristine `REBUILD/files` staging pins, never from local `OVL/` copies.
`census_symbols.inc`
(generated at build time) provides `.equ <name>, <addr>` for every named census
function so sources can `jal` engine functions by name.

## Attempting a function (the loop)

1. Pick a candidate (see criteria below); read its reference listing in
   `asm/nonmatchings/resident/<addr>_<name>.s` (regenerate with
   `python tools/split_exe.py --only <addrhex>`).
2. Write `asm/hand_written/<addr>_<name>.s` — start with
   `.set noreorder` / `.set noat`; **no pseudo-instructions** (write the exact
   instructions incl. delay-slot nops); `.include "census_symbols.inc"` if it
   calls engine functions.
3. Register it in `config/segments.yml` under `attempted:` (start/end must
   match the census record — test-enforced).
4. `python tools/build_psx_exe.py && python tools/validate_build.py` — and/or
   `python tools/asmdiff.py <addrhex>` for the word-level diff.

## First-candidate criteria (v0)

Best → worst: BIOS A0/B0/C0 thunks (census `classification: bios_thunk`, ~50 of
them, 12–16 B, no gp, no data) → tiny leaf PsyQ wrappers (`sdk_psyq`,
size ≤ 0x40, empty `callees`) → small leaf game functions without gp-relative
globals or `jr`-table dispatch. **Avoid in v0:** overlay loader path
(`0x8003D620`, `0x80046330`), LEVEL.RAW decompressor (`0x8001A1DC`), the
renderer cluster (`FUNC_80010000`…), anything gp-heavy or jump-table-driven.

## Picking the next function (ranker + progress)

`python tools/decomp_candidates.py [--top N] [--classes game,unknown]
[--include-gp] [--max-size 0x200]` ranks UNMATCHED resident functions by
matchability → `analysis/decomp_candidates.json`. It excludes already-matched
functions, data globals (symbol-only / BSS region / `*_OBJ_*`), truncated
extents (no return), `jr`-table/switch functions, oversized (> max-size), and
(by default) gp-relative. Score favors small, few-callee, and **behavior-known**
(has a `src_re` file or a real Canon name → also promotes a Canon note on match).
NOTE (substrate v3): these exclusions are conservative defaults, no longer hard
limits — oversized-but-linear, gp (`small_data`), and jr-table dispatchers
(absolute-VA table + `analysis/extent_overrides.json` extent fix) are all now
matchable as hand-asm. The oversized bucket is sub-classified in
`excluded_counts.size_breakdown` (`linear`/`gp`/`jr_table`) to surface the byte
opportunity; raise `--max-size` / `--include-gp` to pull them into the queue.

`analysis/decomp_progress.json` (emitted by `function_census.py`) is the live
completion metric: functions/bytes matched, split asm/C and by classification,
as a % of resident code.

For a new terminal, use the aggregate preflight rather than quoting counts from
this prose:
`python tools/re_campaign_status.py --check --preflight --run-tests --run-build`.
It derives the current counts, verifies local input/toolchain hashes, executes a
real GCC/maspsx smoke compile, runs the safe suite, and validates the rebuilt EXE.

## Attempting a function in C (the gate is OPEN)

1. Pick a candidate from the ranker. Read its reference listing.
2. Write `src/main/<addr>_<name>.c` — a clean-room matching reimplementation
   (never copy Sony SDK headers; declare callees / absolute-addressed globals
   `extern`). These files **are committed** (authored, like `src_re/` notes).
3. Sweep flags: `python tools/compiler_proof.py --function <addr>
   --source src/main/<file>.c [--extern name=0xVA ...] [--grid]` → logs every
   attempt to `analysis/compiler_attempts.json`, prints the winner.
4. Register in `config/segments.yml attempted` (`.c` source). Extents must match
   the census (test-enforced).

   **Symbol resolution (auto-defsym).** Undefined symbols the source references
   (jal targets, absolute globals) are resolved to their VA automatically, in
   priority: (1) the entry's explicit `externs: {name: 0xVA}`, (2) a census
   function name → its address, (3) an **address-anchored name** `sub_<hex>` /
   `func_<hex>` / `g_<hex>` / `D_<hex>` → that VA. So call engine functions by
   their census name or an `sub_<addr>` stub with no hand-listing; reserve
   `externs` for real-named data globals whose address isn't in the name. An
   unresolved symbol is a hard error naming it.
5. `python tools/build_psx_exe.py && python tools/validate_build.py` (must stay
   SHA-1 PASS) — `python tools/asmdiff.py <addr>` for the word-level diff.
6. `python tools/function_census.py` to record `match: c` on the record.

## The C gate — OPEN (2026-07-08)

Both conditions met:
1. **≥ 10 asm functions matched** byte-exactly, and
2. the original compiler is proven — **GCC 2.7.2 `-O2 -G0 -mcpu=3000` + maspsx
   `--dont-expand-li`** (pinned in `c_toolchain`; see
   `Canon/Systems/SYS_original_compiler.md`), demonstrated on SDK `SetPolyGT4`
   AND game function `0x80038F20`.

C proceeds **one registered, census-exact, byte-matching function at a time** —
no broad decompilation, no hand-tweaking output to force a match (a non-match is
recorded in the attempts log, not faked). `src_re/` pseudocode stays a separate
notes-only track and is never converted wholesale.

## Toolchain

### Assembly path (asm/hand_written/*.s)

`mips64-linux-gnu-{as,ld,objcopy}` (Fedora cross binutils; override prefix with
`ABL_MIPS_PREFIX`). Verified: GNU as `-march=mips1 -mabi=32 -EL
-no-pad-sections -G0` reproduces exact encodings for hand-written MIPS-I with
`.set noreorder` (synthetic round-trip + jal-to-absolute tests in
`tests/test_substrate.py`). armips (`~/abl-toolchain/armips`) remains the
fallback if a byte pattern proves unreachable with GNU as — record any such
exception here.

### C path (src/main/*.c) — era compiler + maspsx

Pinned in `tools/toolchain_manifest.json` (hash-only; binaries live outside the
repo under `~/abl-toolchain`, override with `ABL_OLDGCC_DIR` / `ABL_MASPSX`):

- **cc1/cpp**: prebuilt PSX GCC from `decompals/old-gcc` release 0.17 —
  **2.7.2** (primary, PsyQ 4.0/4.1-era) + **2.8.0 / 2.8.1** (fallbacks). All
  three are 32-bit i386 static ELF and run **natively on Fedora 44** (no
  container). Podman is the documented fallback if a host can't run them.
- **maspsx** (`mkst/maspsx`, MIT): translates cc1's MIPS asm into
  GNU-as-compatible input with ASPSX semantics. Key axis: `--dont-expand-li`
  (lets GNU as expand `li` of a small positive constant to `addiu`) vs default
  (`ori`); `--aspsx-version` sweeps assembler-version nuances.

Pipeline (`substrate_common.compile_at`): `cpp → cc1 -S → maspsx → ` the
**existing** assemble tail (`as → ld -m elf32ltsmip @VA → objcopy`). The
winning `(compiler, cc1 flags, maspsx args)` is pinned in the `c_toolchain:`
block of `config/segments.yml` and recorded in
`Canon/Systems/SYS_original_compiler.md`; every attempt (match or miss) is
logged to `analysis/compiler_attempts.json` so no flag combo is retested blind.

**Verified 2026-07-08**: `SetPolyGT4` (0x80061D04) reproduces byte-exactly via
`cc1 -O2 -G0 -mcpu=3000` + `maspsx --dont-expand-li` on all three compilers.

## Subsystem recovery order (after the substrate has ≥10 matches + compiler answer)

1. Boot/init (crt0 + entry flow — smallest, already mapped)
2. Memory allocator (InitHeap thunk + game wrappers)
3. Disc/asset loader (`0x80046330`, `0x8003D620`, `0x8003F5B8`, CdRead layer)
4. Compression (`0x8001A1DC` — byte-exact Python oracle already exists)
5. Main state machine (`0x8004FA40`, `0x8004ECD4`)
6. Input (PAD_* SDK + game polling)
7. Renderer submission (`0x800224EC` → OT submit)
8. Sound/SFX (`sfx_dispatch 0x80050994`, `vab_load 0x80042FA0`, Ss* layer)
9. Level data parser (`0x8001CDC0` DAT + LEVEL.RAW subtype dispatch)
10. Entity/object update loop (contact walker/allocator, mover-VM)
11. Collision (`0x8003633C` + sector/grid builders)
12. Camera

---
**Related:** [DECOMPILATION_PLAN.md](DECOMPILATION_PLAN.md) ·
[EXECUTABLE_AND_OVERLAYS.md](EXECUTABLE_AND_OVERLAYS.md) · `analysis/code_coverage.md` ·
vault `Canon/Systems/SYS_decomp_substrate.md`
