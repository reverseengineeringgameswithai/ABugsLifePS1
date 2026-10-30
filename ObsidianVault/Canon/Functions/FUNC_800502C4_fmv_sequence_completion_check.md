---
kind: function
id: FUNC_800502C4
aliases:
- FUNC_800502C4
- '0x800502c4'
- fmv_sequence_completion_check
address: '0x800502c4'
name: fmv_sequence_completion_check
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- fmv_bin_load
- scene_setup_and_load
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_800502C4 - fmv_sequence_completion_check

## Purpose
Checks a 16-entry flag array for completion then triggers an FMV load

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Caller scene_flow_dispatcher; callees fmv_bin_load and sub_8005038c
- Sums 16 bytes of flag array at 0x8009B878, tests total==112, on match sets flag |=2, gp+1612=1, fmv_bin_load(41)

## Full decode, corrected and cross-verified (2026-08-03)

The array address above was garbled in the original static-inference pass ("0x800a-18312",
not a real address — it's `0x800A0000 - 0x4788`, i.e. `0x8009B878`). Fully disassembled and
cross-verified instruction-for-instruction against the raw pristine listing
(`asm/nonmatchings/resident/800502c4.s` — exact match): one byte per level (16 total), value 7
at 100% completion. A level index (read from a halfword at `0x8008245C`) whose own byte first
reaches 7 triggers that level's own FMV clip (id from a 16-entry table at `0x80077FE3`,
indexed by level). The campaign-wide sum==112 case (already documented above) plays FMV 41 —
this session's own D20/F15 work already live-confirmed FMV 41 as the game's true ending
cutscene. `FUNC_80055478` (the savegame serializer) persists this exact array (plus 3 trailing
bytes) into the save buffer. Live-confirmed via `movies/Phase4/Interpreter/100%
Runs/LEVEL06.movie.json`: index 6 (Birdnest, `scene_id` 5) jumps 0→7 in a single atomic write
at that level's own 100% completion. Full detail: `analysis/phase4_c17_movie_viewer.json`,
[[EXP_2026-08-03_phase4_c17_movie_viewer]].

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Live confirmation (2026-08-03, D20/F15 Hopper defeat)

Runtime-confirmed, not just statically inferred, for one concrete call site. An execute
breakpoint at `scene_setup_and_load`'s entry (`0x8005038c`), replayed against the
operator's own `movies/Phase4/Interpreter/D20.movie.json`, hit at movie-relative frame
16150 with `$ra = 0x800502d8` — inside this function's own bounds (`0x800502c4-0x80050388`,
`functionBounds` confidence exact), at the exact call site `jal 0x8005038c` (`0x800502d0`),
with `a0=4, a1=128`. This IS the function that fires Hopper's own defeat transition. A
follow-up capture confirmed what it leads into: driving input past the resulting
"level complete" results screen (~mf16700 in the same movie) triggers a genuine,
previously-uncaptured multi-shot ending cutscene (circus caravan, ant close-up, caterpillar,
ant colony in grass — consistent with the film's own ending), running for well over 5,000
frames in-engine (normal PC ranges throughout, not obviously MDEC/STR playback). Consistent
with this page's own already-documented static callee `fmv_bin_load(41)`. Full detail:
`ObsidianVault/Experiments/EXP_2026-08-03_phase4_f15_canyon_showdown.md`.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
