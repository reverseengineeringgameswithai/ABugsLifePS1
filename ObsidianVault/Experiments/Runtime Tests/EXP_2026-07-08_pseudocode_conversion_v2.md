---
kind: experiment
id: EXP_2026-07-08_pseudocode_conversion_v2
name: Pseudocode → byte-exact C conversion (v2 phase 2)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_function_census]
fixtures: []
artifacts: [analysis/decomp_progress.json, config/segments.yml]
---

# EXP_2026-07-08_pseudocode_conversion_v2

## Question
Can the `src_re/` behavior notes (the non-compiling hand-decompilation track) be
converted into **byte-exact** `src/main/` C for the small, non-deferred functions
they document — turning "behavior known" into "bytes proven"?

## Method
Cross-rank the 51 `src_re/*.c` notes against `tools/decomp_candidates.py`,
disassemble each candidate, auto-flag the known blockers (internal-`j`, cop2/GTE,
gp, jr-table), and convert only the small clean ones. Same per-function gate as
phase 1 (`asmdiff` → `build_psx_exe` + `validate_build` SHA-1). Callees/globals
resolved by auto-defsym (census name or `sub_`/`g_<hex>` anchor).

## Observations — matched 75 → 80 (+5 documented functions), 7.02% → 7.49%
`validate_build.py` SHA-1 `af43de22…` PASS at every step.
- **`sector_region_code_query`** (0x80038F38) — the flagship: the LEVEL-exit
  region-code query documented in `src_re/level_exit_trigger.c`
  (`[[FUNC_80038F38]]`). Reads the player's current collision sector from
  G_CUR_SECTOR (0x80090560, stride 20) and returns SECTOR_TABLE[sector].region_code
  (0x800A7E48, stride 0x30, +0x2E). Match needed **array-of-struct indexing** (not
  raw `base + idx*size`) so GCC emits base-register-first `addu` — same fix as any
  commutative-`addu` operand-order divergence.
- **pickup_sfx_trigger_7c / _7d** (0x800571E0 / 0x8005721C) — twin pickup handlers
  from `src_re/pickup_handlers_*`: store two args into the pickup state bytes at
  0x800A65A4-7 and fire sound event 124/125 via FUNC_80026DF4.
- **sfx_menu_blip** (0x80050838) — menu-cursor SFX from `src_re/sfx_system.c`;
  1-callee wrapper computing an SPU voice/param address `((id-1)&0xf)<<7 + 0x1200`.
- **SsVabOpenHead** (0x8006B130) — PsyQ libspu, forwards to the named
  `SsVabOpenHeadWithMode(hdr, (short)vabid, 0, 0)` (correct SDK semantics),
  sign-extending the short arg and return; documented site in `src_re/sfx_system.c`.

## Skips (fail-cheap rule)
- **Mis-split function tails** — 0x8005CCE8 (green_seed) and 0x800639CC
  (backdrop_sky) start mid-function (use `s5`/`s1` and parent stack frame set up by
  a caller-body that precedes them); not independently compilable. Census artifact.
- **0x8003E760** (sprite 2-bit field setter, undocumented semantics) — matched to
  a **single** word: a commutative `addu` (`ptr + i` vs `i + ptr`) in the loop that
  GCC canonicalizes on its own. Deferred (not documented-behavior; low value).

## Result
The behavior-known → byte-proven path works: `src_re` notes accelerate naming and
structure, but byte-exactness still hinges on instruction selection (array-vs-raw
indexing, operand order). Most remaining `src_re` primaries are large / gp / jr /
internal-`j` and stay deferred to substrate v2. Canon notes for the 5 set to
`status: byte_matched`, `src_paths` → the new `src/main` C (whose headers cite the
`src_re` behavior source); v1 notes untouched. See [[SYS_decomp_substrate]].
