---
kind: experiment
id: EXP_2026-07-09_c_decompilation_at_scale
name: C-Decompilation at Scale (dc) — convert hand-asm transcriptions to readable byte-exact C
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_decomp_substrate]
fixtures: []
artifacts: [tools/asm_to_c_candidates.py, tools/dc_bank_c.py, analysis/asm_to_c_queue.json, config/segments.yml, analysis/compiler_attempts.json, analysis/re_campaign_status.json]
---

# EXP_2026-07-09_c_decompilation_at_scale

## Question
The reconstruction is byte-complete (98.2%, 917 functions) but **only 80 are real C** — the other
837 are hand-asm transcription (`asm/hand_written/*.s`): byte-exact, not readable source. The
substrate machinery (PsyQ header oracle, `small_data` gp path, `compiler_proof`) exists but had only
been applied to ~80 tiny leaves. Can the tractable classes be converted to authored, byte-exact C at
volume — raising the **C fraction** (not byte-%, already matched either way) — one proven function at
a time?

## Method
Per queue function: dump its `.s` + resolve callees/globals via the census; hand-author the C in the
correct idiom (`declaration_profile`, `externs`/anchor globals, `small_data:true` for gp); run
`tools/compiler_proof.py` (sweeps compiler×flags×profile, byte-compares, logs every attempt); on a
byte-exact row, `tools/dc_bank_c.py` installs the `.c`, flips the `segments.yml` entry `.s→.c`,
rebuilds, and re-validates SHA-1 `af43de22…` (auto-revert on any failure). A function that won't
match cleanly stays `.s` with the attempt logged — never force a near-match.

## Observations
- **The selector had to be made honest first.** `tools/asm_to_c_candidates.py` initially counted any
  `has_return` (including a tail-`j`) as convertible. Three sub-cases are byte-exact-C-**impossible**
  even when otherwise linear, and are now flagged/excluded: **cop2/GTE** register moves
  (`swc2/lwc2/cop2`), **BIOS syscall/break**, and an **internal tail-`j`** (jump into the middle of a
  shared routine — e.g. the mover-VM dispatch loop — a fallthrough, not a return). Honest ready pool:
  **593 (194 game)**; ~47 nominally-"plain" leaves are blocked by these.
- **Reusable authoring levers, each proven byte-exact:**
  1. **Delay-slot early return** — `if (ok) return expr; return 0;` folds `return 0` into the guard's
     bne delay slot; the inverted form (`if (!ok) return 0; …`) emits an extra `j` + tail block
     (proof: `checkpoint_player_state_read` 0x80038f84, 12-word diff → match).
  2. **16-bit clear is `x &= 0xfffe`** (one `andi`), NOT `x &= ~1` (which is `li -2; and`) — also
     reveals the flag word is 16-bit (proof: `transition_finalizer_subsystem_reset` 0x80045a60).
  3. **Far global out of small data:** declare it **>8 bytes** (`extern int g_ADDR[3]`) so `-G8`
     keeps it absolute; otherwise a gp function touching a distant scalar hits
     `R_MIPS_GPREL16 relocation truncated` (unblocked the relocation on `player_sector_lookup`).
  4. **`(void*)0xADDR` → `extern T g_ADDR[]`** to emit the `la` (lui+addiu) macro, not `lui/ori`
     (proof: `sfx_voice_manager_glue_0d1c` default bank at 0x800a6500).
  5. **Sibling near-copies:** once a family template matches, its variants convert immediately
     (`sfx_voice_manager_glue*` trio at priorities 128/180; `music_play_once/looping` pair).
- **Deferred, honestly (stay `.s`, attempt logged):** where GCC's **register allocation** or
  **expression reassociation** diverges and no readable-C form recovers the exact bytes —
  `spawn_fx_object` (leaf reserves an 8-byte frame + picks `a1`; GCC gives me neither),
  `player_sector_lookup` (its GPREL relocation is solved; only the final `idx-(g-1)` reassociation +
  regalloc differ).

## Deferred classes discovered (never forced)
Beyond regalloc/reassociation, the harvest surfaced two more "looks-plain-but-isn't" classes:
- **non-standard `v0`-input glue** — small glues that *read* `v0` (a non-arg register) at entry; the
  caller left a value there. Not expressible in standard C (`cd_ready_poll_control` 0x80070354,
  `event_open_enable`, `dma_callback_stub`, `event_poll_wait`).
- **epilogue delay-slot scheduling** — retail fills `jr $ra`'s delay slot with `addiu $sp` on some
  multi-save functions; GCC's choice differs (`pad_subsystem_init` pair, ~2-word diff).
- Also: a raw `jalr $ra,$t2` (t2=0xB0) BIOS B-table call is not C-expressible (like cop2/syscall).

## Result (session 2026-07-09) — dc-2/dc-3 CLOSED at the tractable-core boundary
Resident C **80 → 99** (+19), SHA-1 `af43de22…` PASS throughout; safe suite 110 green. Converted:
`music_play_once`/`_looping`, `sfx_dispatch_glue`, `controller_input_latch_update`, `cd_mix_shim`,
`cd_audio_volume_apply`, `checkpoint_player_state_read`, `sfx_voice_manager_glue_0e18`/`_0d1c`/`(0d98)`,
`cd_controlb_shim`, `transition_finalizer_subsystem_reset`, `vsync_wait_glue`/`_e8c4`, `load_named_file`.
The cheap sibling clusters are harvested; the remaining ~175 game singletons + large sibling families
(1–4 KB mesh/voice routines) + SDK library twins are **documented continuation** — full-cost per
function with a rising defer rate and low marginal understanding value, so closed here rather than
ground indefinitely. jr-table-from-C (dc-4) remains an optional research spike. See
[[SYS_decomp_substrate]] · [[EXP_2026-07-08_substrate_v3]] · [[SYS_original_compiler]].

> **Closed (2026-07-10):** the dc campaign continued through dc-6..dc-10 and CLOSED at **C = 287/913** (~56% of the achievable ceiling); see [[EXP_2026-07-10_c_conversion_at_scale]], [[EXP_2026-07-10_m2c_seed_pipeline]] and [[SYS_decomp_substrate]] "Campaign CLOSED".
