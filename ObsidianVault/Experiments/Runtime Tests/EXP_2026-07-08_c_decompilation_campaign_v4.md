---
kind: experiment
id: EXP_2026-07-08_c_decompilation_campaign_v4
name: Decompilation campaign v4 — understood-function committable C (then byte-% volume)
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate, SYS_function_census]
artifacts: [src/main/80070898_CdRead2.c, config/segments.yml, analysis/compiler_attempts.json, analysis/decomp_progress.json]
---

# EXP_2026-07-08_c_decompilation_campaign_v4

## Question
Substrate v3 proved the substrate can match large/gp/jr-table functions, but the metric is
~2.6% by *bytes* because **all committed C is tiny** (78 fns / 2,156 B, avg 28 B). Byte-exact
clean-room C of a multi-hundred-byte function had never been done here. Can the understood-function
backlog (`src_re/*.c`) be converted to **committable, byte-exact C** — persistent, readable
decompilation that advances understanding *and* moves byte-% — with the smallest members first
(capability-first), and hand-asm fallback where C won't converge?

## What changed
- **v4.1 capability PROVEN — `CdRead2` 0x80070898 (148 B) byte-matched from committable C**
  (`src/main/80070898_CdRead2.c`; SHA-1 `af43de22…` PASS; safe suite 78 green). ~5x the prior
  average committed-C size. Committed C 78 → 79 (2,156 → 2,304 B); resident matched 148 (13.88%).
  **Match lesson:** GCC -O2 compiles `(x & 0x20) ? 0 : 1` **branchlessly** (`srl`/`xori`), but the
  original uses a **branch**; writing the explicit `if/else` restored it. Recorded in [[FUNC_80070898]].

## Findings / caveats (backlog is NOT what the scoping agent reported)
- **The committable-C backlog is smaller than first estimated.** Re-verifying every candidate for the
  *standalone* property (starts with an `addiu sp,-N` prologue AND ends in `jr ra`) collapsed the
  "22 committable-C candidates" to **15 genuine standalone functions (34,800 B)**. The other 7 are
  **fragments / inner blocks** of larger routines — no prologue, use the parent's callee-saved
  registers, and `j` back into the parent — so they CANNOT be expressed as standalone C:
  - `berry_tough_damage_dispatch` 0x8005905c (448 B) — inner block of `fcn.80058af8` (all xrefs from
    it; starts `lh v0,0x6e(s2)`, ends `j 0x80059280`). Mislabeled "committable-C leaf" by the scan.
  - `player_movement_collision_integrator` 0x8003633c (2480 B) and the 5 seed-plant handlers
    (`type6/type7/cannon/propeller/purple_shooter`, 84–820 B) — same fragment pattern (confirms the
    campaign-v3 "seed handlers are r2-split fragments" finding).
  - **Discipline:** verify prologue+epilogue (or `debugger.functionBounds`) BEFORE scheduling a
    committable-C target — a fragment burns iteration and can never match as C.
- **The real standalone ladder (smallest→largest):** `CdRead2` 148 (done), `music_start` 292,
  `universal_file_loader` 520, `spawn_drop` 668, `sfx_dispatch` 684, `play_sound` 940,
  `backdrop_tile_builder` 1440, `dat_parser_relocator` 1548, then the giants (2384–8304).

## In-progress
- **`music_start` 0x8004699c (292 B, gp) — logic byte-identical, frame layout pending.** The C
  (`src/main/8004699c_music_start.c`, local WIP) matches the original in EVERY word EXCEPT a uniform
  stack-frame shift: GCC reserves a 0x40 frame, the original 0x58 (the extra 0x18 is outgoing-arg /
  scratch reservation, independent of buffer sizes). Register allocation, branch structure, all 8
  SDK calls, and the gp globals all match. Two match levers already found and applied: (a) **reload
  the table index from its gp global** for the second table access (`g_800772cc[g_800821b8].start`)
  so `idx` needs no extra callee-saved register — matches the original's `lw v1,0x420(gp)`; (b) make
  the function return `int` (0 on the bail path, fall-through on success) so the early-return compiles
  to `bne … / j epilogue` with `move v0,zero` filling the delay slot, not a single `beqz`. Remaining:
  reproduce the 0x58 frame. **Root-caused (GCC `.frame` accounting):** my build is
  `vars=32, args=16, regs=12 → 0x40`; the original is `0x58`, which requires the outgoing-args area
  `args=40` (a 10-word call: probing shows `args` scales 16/24/32/40 at 4/6/8/10 call args). BUT the
  original has **zero stores to sp+0x10..0x27** — so no 10-scalar-arg call, no struct-by-value arg
  (would emit copy stores), no struct return (would need a hidden a0 pointer), and no dead local (GCC
  eliminates un-address-taken locals). The 24 bytes are reserved-but-never-touched, unaccountable from
  the binary alone — it needs the original's local/struct DECLARATIONS, which a stripped binary does
  not preserve. **Not systematic:** `spawn_drop` 0x80059e44 (frame 0x30, no gp, reads its 5th arg from
  the incoming area) shows no such anomaly. So the frame idiom is function-specific, not a blanket rule;
  music_start is a hard case. Route options: hand-asm fallback, or obtain the PsyQ CD-struct headers to
  recover the missing local declarations.

## In-progress — `contact_alloc` / spawn_drop 0x80059e44 (668 B, -G0, WIP)
Second game-function C attempt (from the CONFIRMED `src_re/contact_alloc_80059e44.c` pseudocode).
**Structure fully matched** — 167 words vs 167 words (correct length + control flow) after one key
codegen lesson: the original **does not cache the record pointer in the allocator loop** — it
re-derives `0x800b0000 + slot*0x38 + const` per access (folding the array base into each load's
`lui`+offset), forming the `rec` pointer only *after* the loop. Writing the loop checks as **direct
global-array indexing** (`g_800b0d18[slot*0x38 + 0x33]`) instead of a cached `rec` pointer reproduced
that (and fixed a 5-word length gap). Also corrected the note's `+0x2e` sign vs the disasm
(sel==1 → +ctorType, else → −ctorType). **Remaining: ~69 words of register-allocation divergence**
(GCC relocates x/y/z out of a0-a2 early; allocates stackArg / the loop base to different registers,
cascading). Byte-exact register matching from clean-room C — without the original headers/source — is
a deep grind; WIP saved. **Strategic finding:** committable-C of real game functions hits two hard
walls — frame anomalies (music_start) and register-allocation divergence (spawn_drop) — each needing
either the original source artifacts or extensive per-function iteration; the CdRead2 proof (clean SDK
leaf) understated this. The capability is real; the pace on real game functions is slow.

## v4.2–v4.4 — hand-asm ladder (operator chose byte-% throughput over C-grind)
After the frame/regalloc walls, the operator directed switching the dense game-function ladder to
**hand-asm** (byte-exact + Canon-documented; C WIP preserved in `src/wip/`). Built
`tools/gen_handasm.py` (disassembles original bytes → assemblable hand-asm: real mnemonics + local
branch labels, `.word` for jal/cop2/unknown; byte-exactness guaranteed by the build+validate SHA-1
round-trip). Every function assembled byte-exact on the first try.
- **v4.2 (7 fns):** the standalone ladder — music_start, universal_file_loader, spawn_drop/contact_alloc,
  sfx_dispatch, play_sound, backdrop_tile_builder, dat_parser_relocator. **BYTES 2.6% → 4.1%.**
- **v4.3 (7 giants):** sfx_voice_manager, proximity_updater, collision_grid_builder, pickup_projector,
  collision_resolver_accumulate, player_vertical_update (6 KB), high_heap_loader (8.3 KB).
  **BYTES 4.1% → 10.9%.** Completes the corrected 15-function standalone backlog (1 C + 14 asm).
- **v4.4 (3 jr-table dispatchers):** source3f_dispatch (4 KB), contact_walker, berry_throw_dispatch —
  self-contained inline-case switches (0 external jal-targets). Extended the extent-override to DROP
  interior jumptable sub-blocks (v3.3 could only clamp to the first). **BYTES 10.9% → 12.2%.**

- **v4.5 (byte-% volume, 80 fns):** banked all clean large-linear UNKNOWN functions (73, >0x200,
  prologue + single `jr ra`, no gp/jr-table/fragment, structurally single — 0 interior
  prologues/symbols/jal-targets) + 7 more self-contained jr-table dispatchers. **BYTES 12.2% → 31.3%.**
  Over-merge detector added (interior `jr ra`→prologue / interior prologue). **v4.5 CLOSED** — the clean
  queue is exhausted (only the memory-flagged over-merge 0x8002b428 and 0 safe dispatchers remain).

**Net v4: resident matched 147 → 245 (13.8% → 23.7%); BYTES ~2.3% → 31.3% (13.6x).** SHA-1 clean, suite 78.

## Deferred (honest skip log)
- **event/mover-VM 0x8004c13c** — its opcode handlers are NAMED symbols (`mover_vm_op9_set_target`,
  `vm_motion_apply_chase`, …); bank them as individual handlers, not one merged blob
  (`test_every_text_symbol_is_a_census_start` correctly caught the over-merge).
- **enemy_deathanim 0x800498ac, contact_vs_actor 0x80058af8** — each absorbs a separate jal'd function
  (0x80049c30, 0x800593e8); need precise sub-function splitting before banking.
- **music_start, contact_alloc** — committable-C WIP (logic/structure-matched) in `src/wip/`; byte-exact
  match currently lives in hand-asm, pending PsyQ headers to close the C.
- **0x8002b428 (8740 B)** — memory-flagged r2 over-merge; structurally looks single (1 prologue/1 jr ra,
  no interior symbols/jal-targets) but skipped from v4.5 pending `debugger.functionBounds` confirmation.
- **Canon notes** for the v4.2–4.4 hand-asm functions: understanding is in `src_re/*.c`; per-function
  `FUNC_` notes are a lightweight follow-up (gen_matched_canon_notes handles only `.c`).

## Continuation
- v4.2: climb the standalone ladder (music_start frame first, then file_loader / spawn_drop /
  sfx_dispatch / play_sound / backdrop_tile_builder / dat_parser). Runtime-verify the behaviorally-
  clean ones via `tools/verify_function_runtime.py call` on a throwaway instance.
- v4.4: the understood **jr-table dispatchers** (event/mover-VM 0x8004c13c, etc.) → hand-asm (v3
  mechanism) — the fragment handlers above are the *arms* of these dispatchers.
- v4.5 (last): large-but-linear UNKNOWN functions → hand-asm volume.

## Evidence / links
[[SYS_decomp_substrate]] · [[SYS_function_census]] · [[FUNC_80070898]] ·
[[EXP_2026-07-08_substrate_v3]] · [[EXP_2026-07-08_c_decompilation_campaign_v3]].

> **Closed (2026-07-10):** campaign v4/v4.5 ended as recorded (byte-% lever banked as hand-asm); the readable-C line continued as the dc campaign, which CLOSED at **C = 287/913** ([[SYS_decomp_substrate]]).
