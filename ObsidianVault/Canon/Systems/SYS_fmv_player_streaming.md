---
kind: system
id: SYS_fmv_player_streaming
created: 2026-07-08
updated: 2026-07-08
status: static_seen
confidence: medium
source_state: original_game_reference_or_mod_reference
src_paths:
  - src_re/fmv_player_streaming.c
  - src_re/fmv_movie_dispatch_800b6250.c
address: 0x58010006
patch_policy: safe_to_read
---

# SYS_fmv_player_streaming - fmv player streaming

## Purpose

This page closes the migration source-coverage gap for `src_re/fmv_player_streaming.c`. It records the symbol `FILE_LOADER_BY_NAME` and links the C reference into the structured vault.

- Address if known: `0x58010006`
- Coverage comments: globals/constants: FILE_LOADER_BY_NAME, FMV_BIN_LOAD, FMV_FRAME_GETTER, FMV_FRAME_SETTER, FMV_OVERLAY_BASE, FMV_OVERLAY_STOP_CALL, FMV_STREAM_POLL, FMV_TERMINATOR


## Corrected Static Slice

The previous imported excerpt misidentified the sequence at `0x800B7030` as
FMV termination. Static reconstruction against the named PsyQ library calls
shows that it is stream startup:

1. `CdControl(CdlGetlocP=0x15, 0x800CABD0, 0)` is retried until accepted.
2. `CdRead2(0x1C0)` at `0x800B704C` is retried until the streamed read starts.
3. `CdControl(CdlDemute=0x0C, 0, 0)` enables audio.

`0x80070898` is the byte-matched `CdRead2`, and `0x8006D8E8` is `CdControl`;
neither is an event primitive or terminator. The stream callback begins at
`0x80070A30` and includes the old false split at `0x80070A40`.
`StGetBackloc` begins at `0x80070AC0` and continues through `0x80070B20`.

Playback completion remains the overlay flag at `0x800CAC10`, set by the frame
limit comparisons around `0x800B6B18..0x800B6B48`. The per-movie limit is
loaded from `0x80131EEE`, populated by the 40-case frame-count table. Exact
instruction and overlay-hash evidence is in
`analysis/subsystems/fmv_stream_start.json`; the maintained reference is
`src_re/fmv_player_streaming.c`.

## Phase 4 E15 static frontier pass (2026-08-01)

Full evidence: `analysis/phase4_e15_fmv_frontier.json`. Method: linear jal/j/jr
decode of `FMV/FMV.BIN` past its documented `0x100`-byte manifest, cross-checked
against `analysis/functions.csv`; `census_overlays.py --extra` for the two known
coordination addresses. **Not** function-boundary-aware (unlike the 20 overlays
`function_census.py` already covers) — a bounded probe, not a sound complete
disassembly.

**Discharges the open "MDEC decode/DMA call site" residual** (named since
2026-06-22): 39 of 54 out-of-blob `jal` targets in valid PS1 RAM land exactly on
a *named* resident function start — `StSetStream`, `StGetNext`, `StClearRing`,
`StCdInterrupt`, `StSetRing`, `CdRead`/`CdRead2`/`CdReadSync`, `CdControl`,
`CdControlF`, `CdMix`, `CdGetToc2`, `DMACallback`, `ResetCallback`,
`SetDefDrawEnv`, `SetDefDispEnv`, `SetDispMask`, `DrawSync`, `PutDispEnv`,
`ClearImage`, `LoadImage`, `frame_render_driver`, `VSync`, plus event/critical-
section primitives and libc. 39/54 landing exactly on named function starts is
not plausible from decoding arbitrary data bytes.

**Completion flag `0x800CAC10` — four statically resolved direct overlay
accesses.** The general effective-address census resolves 3 writers + 1 reader in
FMV.BIN: `sw` at `0x800B6B24` and `0x800B6B48` (the two limit compares), `sw zero`
at `0x800B6DD0` (clear/reset), and `lw` at `0x800B743C` (read, adjacent to the
`0x800B7030` stream-start sequence already Canon). It also retains **2,580
unresolved-base memory accesses in FMV.BIN** and 7,547 across the scanned overlay
set, so those four sites are a resolved set, not an overlay closure.

**Resident side: 0 resolved direct writers, 0 resolved direct readers**
(`census_address.py` over the whole resident EXE), with its unresolved-base and
indirect-call residual still open. The row's open "teardown into scene-flow"
question is **not** answered by this flag — either a resident-side proxy this pass
didn't find exists, or the overlay calls back into scene-flow code directly rather
than signalling through a polled flag. Still open.

**Correction history (2026-08-04 audit):** the former “overlay side fully
resolved” reading exceeded the fixed-form census. Pointer-derived accesses were
enumerated but not resolved, so the page now states only what that method proves.

**Frame-limit table `0x80131EEE` — same result, same code block.** Read at
`0x800B6B2C` (`lh v0,0x1eee(v0)`, immediately before the two compares above),
write at `0x800B6DC0` (`sh s2,0x1eee(at)`, presumably per-STR from the
manifest). Tightens the `0x800B6B18..0x800B6B48` range above to the exact
bracketing instructions. Resident side: 0/0, same as the completion flag.

**Still open — this is not a complete frontier.** 169 of 538 `jal`-opcode
decodes in the post-manifest region point at addresses outside valid PS1 RAM
(e.g. `0x8ff00018`) — direct proof the blob interleaves code and data the way
every other overlay does, and this pass did not do the block-start/string-
exclusion separation `function_census.py` applies to the other 20. 15 more
valid-RAM targets don't match a named function start (unresolved either way).
The `jr` indirect-dispatch census is **unusable as evidence**: of 189 non-return
sites, several decode as `jr $0` — not a real MIPS pattern (register 0 is
hardwired zero), further proof of hitting non-code bytes. **Verdict: DoD item 2
for E15 is ADVANCED, not MET.** An `unclassified_xrefs:0` claim for the whole
blob would be unsupported — the same overclaim shape already retracted twice
today for B06/B08 ([[SYS_player_power_slot]]). Next static step: run FMV.BIN
through `function_census.py`'s existing block-start + string-exclusion pipeline
(extend `staged_overlay_targets()`'s pinned count from 20 to 21).

## Trigger + interface trace (2026-08-01) — corrects two open Canon claims

Full evidence: `analysis/phase4_e15_fmv_frontier.json` §`TRIGGER_AND_INTERFACE_TRACE`.
Manual instruction decode (own verified decoder, cross-checked against raw hex before
banking — one transcription error caught and corrected in this same pass) of the call
chain resolved via `analysis/phase3_call_graph.json`'s `callers` map.

**Corrects "trigger logic is likely overlay-resident, un-RE'd"** (Archive/Superseded
note): it is **resident**. `scene_flow_dispatcher` (`0x8004FCA0`) — already known as the
`jr`-dispatch target of `main_shell_substate_table` — calls `fmv_bin_load` (`0x8003E7C0`)
from 3 distinct sites: `0x8004FFD4` with a **computed** `a0 = (a2 & 0xFF) + 41` (likely
scene/level-dependent), and two with **literal** `a0` — `0x800500D8` → 46, `0x80050284` →
40 — under different guard conditions.

**Corrects "FMV.BIN entry point is NOT confirmed"**: it is now confirmed —
`fmv_bin_load(a0=movie_id, a1=flag)` does, in order: `jal display_buffers_init`; if
`a1≠0`, `jal transition_fade_draw_loop(a0=a1)`; `jal universal_file_loader(a0=&"fmv\
fmv.bin" [0x8001AE6C], a1=0x800B5788)` — byte-exact confirmation of the existing load
claim, now with the actual operand evidence dumped; if `a1≠0`,
`jal animated_overlay_display_loop_entry(a0=a1)`; **`jal 0x800B6250(a0=movie_id)`** — into
the just-loaded overlay, unchanged movie-id argument. `0x800B6250` is not in
`analysis/functions.csv` (FMV.BIN has never been function-censused, consistent with the
frontier finding above); `jal boot_subsystem_init` follows — name suggests boot-time
reuse, not resolved either way.

**Movie-id space ≠ manifest order.** The manifest's raw STR file order is 0-24; the
`movie_id` threaded through this whole chain (40, 46, and a computed value ≥41) is a
larger, different ID space — consistent with the already-documented 40-case frame-count
table. The ID→manifest-index resolution was **not found**; it must live inside FMV.BIN at
or after `0x800B6250`, never disassembled. Concrete next step, distinct from the
block-boundary-recovery step named above.

**Manifest recount (SUPERSEDED same-plus-one-day, see below).** Full 25-entry manifest
decoded: 3 boot/frontend clips (`tt.str`/`dlogo.str`/`ad.str`) + 22 per-level clips
`LEV1A/B .. LEV11A/B`. The archived note's excerpt ended `"...LEV9A.STR, LEV9B.STR"`,
reading as 9 levels; this pass said 11. **Both undercounts — see the 2026-08-02 section.**

## Movie-ID → STR-filename table — FULLY RESOLVED (2026-08-02)

Full evidence: `analysis/phase4_e15_fmv_frontier.json` §`MOVIE_ID_TABLE_2026-08-02`.
Resolves item 2's last named residual (the movie-id indirection past `0x800B6250`) and
closes item 6 groundwork. `sltiu $v0,$s0,0x2f` bounds `movie_id` to 0..46; a `jr`-table at
`0x800B5AA4` (47 words) dispatches to 41 distinct case handlers, each decoded for its
string pointer + literal frame count, or flagged as the shared `DEFAULT` (no-op,
clear-screen) handler. **One decoder bug caught and fixed before banking**: an early pass
didn't stop scanning at the `j` instruction and leaked frame-count literals from
unrelated adjacent code (two pairs of ids showed identical, wrong values). Fixed to stop
after the delay slot; 8 of the "new" strings independently spot-verified via raw byte
dump, not just the ASCII-filter path.

**Result: 47 slots = 3 boot clips (ids 0-2) + 7 unused/reserved (ids 3-9, one shared
DEFAULT handler) + 40 real dispatchable movies** — exactly matching the already-documented
"40-case frame-count table," now with the actual contents instead of just the count.

**⚠️ Attribution correction.** The frame-count *values* themselves and the
`0x800B6B18..0x800B6B48` completion logic were **already solved on 2026-07-04** —
`src_re/fmv_player_streaming.c` and the archived Finding note document the per-movie
`addiu a1,zero,<count>` literals at their exact file offsets (`0x0B4C(TT) 0x0B58(DLOGO)
0x0B74(AD) 0x0B94(LEV1A) … 0x0DC4(INTRO) 0x0DD0(LOSE)`) with a **live patch-test proof**
(TT `440→900` streamed the full clip) — stronger evidence than this pass's static read.
What is genuinely new in this 2026-08-01/02 pass is the **selection mechanism**: the
`jr`-dispatch table at `0x800B5AA4` that picks *which* case runs for a given `movie_id`,
the unused-ID range (3-9), the `scene_flow_dispatcher` trigger chain, and the resolution
of the two literal call-site constants (40→`LEV15C`, 46→`LOSE`). The frame-count column in
the table above is a cross-check against the 2026-07-04 values, not a new discovery — and
it matches exactly, which is good independent corroboration, not a redundant find.

## Typed state (item 3) — 2026-08-02

- **`0x800CAC10` completion flag** — `u32`; the values at the three resolved direct
  overlay writers are exactly `{0,1}`. Both non-clear sites canonicalize via a
  `beq`/`bne` + `addiu $v0,$zero,1` idiom before the store, confirmed by direct
  disassembly of `0x800B6B18..0x800B6B48`. It is cleared to `0` at movie start (`sw
  zero` at `0x800B6DD0`) and set to `1` when `frame_count >= total-2` (`addiu
  $v0,$v0,-2` at `0x800B6B34`, matching the already-banked pseudocode exactly). The
  census resolves one internal overlay read at `0x800B743C` and zero resident direct
  reads; it does not exclude pointer-derived accesses.
  **Correction history:** “the flag's domain is exactly `{0,1}`” generalized the
  values at the resolved writers into a closed domain. The writer-value fact remains;
  the domain closure is retracted.
- **`0x80131EEE` frame-limit cache** — `s16`, domain `[156, 3162]` per the resolved table
  (min = `DLOGO`, max = `LEV15C`). Written once per movie-start (`sh` at `0x800B6DC0`
  from `s2`, itself the case handler's `a1` literal); read once per frame at `0x800B6B2C`
  (`lh $v0,0x1EEE($v0)`).
- **`movie_id`** — register-threaded argument (not a fixed memory address), domain
  enforced by `sltiu $v0,$s0,0x2f` to `[0,46]`. Ids `[3,9]` are valid-but-unused: they
  fall back to the shared `DEFAULT` handler (screen clear, no STR playback) rather than
  erroring or crashing.
- **Dispatch table `0x800B5AA4`** — `u32[47]`, code-pointer array (`jr`-table), resident
  in the FMV overlay's own data region, not the resident EXE. No evidence of runtime
  mutation.

**This supersedes the 2026-08-01 recount above, which read only the file's own stale
25-entry header manifest.** The header's declared count does not match what the dispatch
table actually references. **The true count is 15 levels — matching the campaign's 15
stages (F01–F15) exactly** — plus 3 `ALT` endings, 1 `INTRO`, 1 `LOSE` clip. The manifest
and the dispatch table are two different, inconsistent in-file sources; the dispatch
table is authoritative for what code can actually invoke.

Level→id formula: `id = 10 + (N-1)*2` for the A-clip (N=1..14), +1 for B. **One verified
irregularity**: levels 4 and 5's A-clips are swapped in table order (`id16`→`LEV5A`,
`id18`→`LEV4A`) while their B-clips are not — real, re-checked against raw bytes, not a
decode artifact. Level 15 is a 4-clip special case (ids 38-41: A/B/C/D).

**Ties directly to yesterday's trigger trace, inferred not confirmed**: the two literal
`fmv_bin_load` call sites found at `0x800500D8`/`0x80050284` passed `a0=40` and `a0=46`.
Table lookup: **id 40 = `LEV15C`, 3162 frames — the longest clip in the entire table by a
wide margin** (next longest 1828), strongly suggesting the campaign finale. **id 46 =
`LOSE`, 281 frames** — short, and the literal filename makes the game-over inference
almost certain. The computed-argument site (`a0=(a2&0xFF)+41`) reaches `LEV15D`/`ALT1`/
`ALT2`/`ALT3` for `a2=0..3` — consistent with a variant-ending selector, though `a2`'s own
source was not traced this pass. All three readings are content-based inference, not a
traced guard-condition semantic — flagged as such, not claimed as confirmed.

## Dispatch decompiled to real C — 2026-08-02

`src_re/fmv_movie_dispatch_800b6250.c` — full documentation-grade C for the entry point,
with the complete 47-slot table as an actual C array (not just prose), the bounds check,
the DEFAULT-handler path, and the tail-call to the playback starter. Compiles clean
(`gcc -fsyntax-only`, no errors). Guarded by
`tests/test_phase4_e15_e06_c_decompiles.py`, which round-trips the C table against
`analysis/phase4_e15_fmv_frontier.json` to catch transcription drift between the two.

**Lead from the unmerged acceleration branch, independently verified before use**: that
branch (commit `151a5a3bbf07`, evaluated read-only, not merged) has extensive additional
FMV teardown/lifecycle tooling not on master (`phase4_fmv_teardown_ownership.py` and
sibling files). Ran its static teardown-ownership check and independently re-disassembled
its core claim (the shutdown call sequence `0x8007094C` → `0x800709AC` → `0x800B91AC`,
returning to `0x800B74AC`) directly from FMV.BIN's own bytes — it matches exactly. This
confirms the sequence but does NOT yet answer the still-open "teardown into scene-flow"
question: `0x800B74AC` continues into another FMV-internal call, not a return to resident
code. Worth revisiting as a lead for that specific gap, not yet incorporated as a finding.
