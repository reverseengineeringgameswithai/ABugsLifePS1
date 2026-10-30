# EXP — Phase-4 FMV presentation RECT height static ownership

Date: 2026-07-28
Campaign: `fmv_playback`
Row: `E15_fmv`
First unmet dimension: `lifecycle`
Lane: offline localization → static reconstruction → bank

## Work packet

- Exact claim: pristine `0x800B6BF0` copies cached decoded height through the
  player-boundary pointer into presentation RECT height, and its callers plus
  resident `0x80064178` helper can be exhaustively classified without replay.
- Falsifier: reject the claim if the source/destination differs, either caller
  fails to pass the exact base, the helper changes the argument, a direct
  caller or retained writer PC is unclassified, or LoadImage's driver table
  does not resolve the resident helper to `_dws`.
- Needed domain: retained E15 derived index plus pristine FMV.BIN/resident
  bytes, source/symbol registry and the already-banked saturated writer result.
- Predicted machine layer:
  `analysis/phase4_fmv_present_rect_height_static_ownership.json`,
  documentation-grade semantic C and focused mutation guards.

## Offline localization

The central derived index
`analysis/phase4_derived_index.json` selects external
`fmv-lifecycle-v2/index.json`, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`,
16,060,589 bytes. It covers E15 block-flow, RAM, register, VRAM and SPU
frame-boundary domains.

The tracked offline reader searched exact terms `0x800B6BF0`,
`0x80064178`, `0x800CAC0A`, `0x800CAC02`, `cached_height` and
`presentation_rect`. All six return zero matches without truncation.
Receipt SHA-256 is
`4d3e3d60016374f2386c3f30173fbb9f94dc4928fa2d9375ded80bfdd2549d5e`;
retained output SHA-256 is
`53d13c7e5d8b00fbbe625108628271922055f8c50f3c1c97f216a47e8fa303b6`.
This localizes the missing domain to instruction/static ownership; it is not
an absence claim.

## Static result

The player materializes `0x800CABE0` at `0x800B7098/0x800B709C`, supplies it
to the first `0x800B6C24` call, preserves it in `s3`, and supplies it to the
second call. The helper retains `a0` and has the sole direct call to
`0x800B6A7C`. That callee binds `s1=a0`, loads the low halfword of cached
height `0x800B9A5C`, then writes:

- `s1+0x1E` → `0x800CABFE`, decode RECT 1 height;
- `s1+0x16` → `0x800CABF6`, decode RECT 0 height;
- `s1+0x2A` → `0x800CAC0A`, presentation RECT height.

Presentation function `0x800B6634` supplies `0x800CAC04` to matching-C
LoadImage. The pristine driver pointer at `0x8007FBC0` selects table
`0x8007FB80`; table index 2 is `gpu_present_drawotag_vsync`, while index 8 is
PsyQ `_dws`. The wrapper carries the same RECT to `_dws`; `_dws` clamps its
height to the GPU bound and stores it at `0x80064178`.

The prior 32-event runtime census is therefore completely classified:
initializer `0x800B6F18`, cached-height publish `0x800B6BF0`, downstream SDK
clamp `0x80064178`. The exact static falsifier survives.

## Boundary and next method

The prior broad write watch remains saturated, so the complete ordered
sequence and total `_dws` invocation count are still open. No roadmap
dimension is promoted and no live receipt is admitted here.

If complete ordered ownership remains load-bearing, the next experiment
family is a same-anchor `functionTrace` restricted to
`0x800B6A7C..0x800B6C24` over movie frames 160..260 with 32 events maximum.
The three retained calls predict six balanced function events. Saturation or
an unbalanced call falsifies completeness. Repeating the broad presentation-
RECT write watch is prohibited.

No MOD-private state, hook or intended behavior changed.

## Finite function-cardinality successor preflight

The next measured-method controller trial retained `fmv_playback` /
`E15_fmv` only, with `lifecycle` still the first unmet dimension. Work-packet
SHA-256
`142fb4879f1c548f8d625858797a10d87e5753233491e11689edf2f1a83879e3`
states one exact successor claim: two unmodified same-anchor replays must each
retain three complete calls, hence six balanced entry/exit events, for
`0x800B6A7C` from caller `0x800B6C24`. Saturation, an index other than one,
another caller, imbalance, sequence drift, escape from the finite window or
endpoint divergence falsifies that claim.

The current central `fmv-lifecycle-v2` index was reused rather than rescanned.
Closed receipt
`3859838856b1b00c9bca8a8d9a171b70986a49e60cf62db0e0261a59bdcfe61e`
re-executes the tracked reader over the exact 16,060,589-byte derived-pristine
input. Its bounded search for the function/caller, `functionTrace`, cached
height, presentation RECT and movie-frame window returns zero paths without
truncation. Retained output SHA-256 is
`b76c4fdd74eb95af8e6e789bb0d4d20d409ec78a83a72dd0395bc71a0e84fac8`.
This proves only that the frame-boundary index lacks the every-call
cardinality domain.

Planned escalation
`P4-ITER114-E15-PRESENT-RECT-FUNCTION-CARDINALITY` changes experiment family
from the saturated write watch to a finite direct observer. The passive repeat
uses movie frames 150..270. The precise repeat stages to frame 160, records
only `functionTrace.start` for `0x800B6A7C` with `max_events=32`, and stops at
frame 260. Both jobs use the same centrally pinned E15 state/movie anchor,
unmodified pristine guest code and identical endpoint captures.

Both plans pass the atomic batch validator. A focused plan guard also rejects
any mismatch between the typed v2 observer and each atomic job's
instrumentation; changing one job's event limit from 32 to 31 trips that
guard. The retained adapter and its historical live-receipt identities remain
byte-identical.

The immutable controller before-ledger contains zero planned escalations and
does not admit the new ID. No DuckStation process launched, no live receipt
was authored and no falsifier was executed. E15 therefore remains four
met/five remaining; Phase 4 remains 16/107 with 148 met, 46 partial and 769
gap dimensions. The exact passive/precise pair is banked for a later
controller iteration whose immutable before-ledger contains the ID. No
roadmap fact, Canon entry, MOD-private state, hook or intended behavior
changed.

## Executed function-cardinality control

The following controller iteration admitted
`P4-ITER114-E15-PRESENT-RECT-FUNCTION-CARDINALITY` from its immutable
before-ledger. Its work packet is SHA-256
`904f19d51008b2ed2543eeee67534ec4998b5c28f346c117c8d0302d1118e101`.
Before live work, closed offline receipt
`dcdf06fd4a24780d105e599151d2ee0d74544912b9805f90447181aa735f28af`
re-executed the exact bounded index query; its retained output remains
`b76c4fdd74eb95af8e6e789bb0d4d20d409ec78a83a72dd0395bc71a0e84fac8`
and returns zero paths without truncation.

Two fresh isolated DuckStation profiles then completed the wider passive pair
and narrower precise pair on the centrally declared E15 state/movie anchor.
Both profiles mounted pristine SCUS-94288 media, completed two atomic jobs and
stopped their owned numeric PID. The closed passive and precise receipt hashes
are
`5b820de153b9874f3f3d08eb996676aac72965b4c37301ad10437491ffaa1ba8`
and
`29b4e6f4031d997a3081305ce52a1f8899e040bd0c891a083f222ca4832951c6`.

The passive endpoints match at emulator frame 4505/cycle 2,550,166,735. The
precise endpoints and full ordered traces match at frame 4495/cycle
2,544,504,697, with presentation RECT height 128, selected limit 386,
running latch zero and scene one. Each precise trace retains indexes 1..22
against a 32-event limit, so it is unsaturated.

The predeclared three-call claim is falsified. Both branches retain eleven
entry/exit pairs for `0x800B6A7C`; the observer caller field is the JAL at
`0x800B6C34`, not the owning helper entry `0x800B6C24`; and the first exit is
observer-synthesized. Entry arguments form exactly three retained classes
with call counts 1, 1 and 9. These are bounded observations for movie frames
160..260, not semantic argument names, direct-return proof for the first call
or a complete downstream `_dws` count.

`tools/phase4_fmv_present_rect_height_function_trace_result.py --write
--check` joins the immutable authorization ledger, current offline receipt,
static JAL ownership and both complete v2 receipt dependency sets. Its focused
tests reject trace-index, call-instruction, pairing, argument and capacity
drift. The machine result promotes no dimension and keeps both investigator
receipts pending a fresh campaign verifier.

The binding next lane is static reconstruction of the `0x800B6C24` loop and
the three 1/1/9 argument classes. A repeated function-cardinality replay is
not authorized. No Canon or MOD-private fact changed.
