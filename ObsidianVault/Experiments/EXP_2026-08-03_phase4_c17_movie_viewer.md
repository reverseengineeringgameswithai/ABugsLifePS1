---
kind: experiment
id: EXP_2026-08-03_phase4_c17_movie_viewer
status: complete
source_state: original_game
system: [FUNC_800502C4, FUNC_80055478]
row: C17_movie_viewer
---

# Phase 4 C17: FMV unlock table, resolved

## Question

C17_movie_viewer's own scope: unlock table, persistence, menu presentation, and final clip
conditions. The row had two thin bindings (a bonus-challenge unlock byte, and a bare
savegame-serializer citation) and no dedicated investigation.

## The discovery: an existing, mis-cited finding from earlier this session

`FUNC_800502C4` ("fmv_sequence_completion_check") is already live-confirmed from THIS
session's own earlier D20/F15 work as "the function that fires Hopper's own defeat
transition," leading into the game's true ending cutscene — but that finding was never cited
into C17's own row, and the function's own static-inference page had a garbled address
citation for its key data structure ("0x800a-18312" — not a real address).

## Full decode, cross-verified against raw ASM

Disassembling the function directly (and cross-checking against the raw pristine listing —
every instruction word matches exactly) resolves the garbled citation: the array is at
`0x8009B878`, computed as `0x800A0000 - 0x4788` (18312 decimal), not a literal address
fragment.

**Structure**: one byte per level (16 total). A level's value goes from 0 to exactly 7
(`0b111`) at 100% completion — plausibly one bit per completion axis (grain/FLIK/seed,
matching the shared 3-counter results-screen layout already established for F06/F15), though
the individual bit-set instructions weren't traced this pass.

**Per-level clip trigger**: when a level index (read from a halfword, inferred to mean "the
level that just finished") has its own array byte reach 7 for the first time, that level's
own FMV clip plays — its id read from a 16-entry table at `0x80077FE3`, indexed by level.

**Campaign-wide ending trigger**: separately, the function always sums all 16 bytes. If the
total is 112 (all 16 levels at value 7 — the whole campaign 100%'d), it plays FMV id 41 —
already live-confirmed this session as the actual ending cutscene — and sets a bit in the
adjacent byte `0x8009B888`.

**Distinct from the bonus-challenge system**: `SYS_bonus_unlock_challenges.md`'s own
`0x8009B889` byte (the 3 hidden challenges) is immediately adjacent in memory but a
completely separate, smaller mechanism.

**Persistence confirmed**: already-Canon `FUNC_80055478` (the savegame serializer) writes
"19 bytes from `0x8009b878`" into the save buffer — exactly the 16-byte array plus the 3
bytes right after it. This directly answers the row's own persistence question.

## Live verification

Reused the pre-existing `LEVEL06.movie.json` 100% run (already used this session for C04's
own token-grant finding — no new recording needed). Sampling the full 16-byte array across
the run's own completion window:

- **Index 6 transitions 0→7 exactly at LEVEL06's own 100% completion** (the already-visually-
  confirmed "Congratulations! Bonus Movie Clip Earned" moment). LEVEL06 (Birdnest) is
  `scene_id` 5; array index 6 = `scene_id + 1`, matching this campaign's own established
  level-number-vs-scene_id offset convention.
- **The transition is instant, not incremental**: narrowed to 10-frame resolution and found
  the byte jumps directly from 0 to 7 in a single write, roughly 500 frames AFTER the
  underlying quota-completion trigger C04 already found — consistent with the array being
  finalized once the results-screen sequence completes, not the instant the last raw
  condition is met.
- Index 15 already reads 7 at frame 0 of this fixture — some other level was already
  completed in this save's own prior history, consistent with a genuine multi-level
  save-persisted structure.

## The menu reader, found (2026-08-03, operator-recorded fixture)

The operator recorded `movies/Phase4/Interpreter/C17_MovieViewer.movie.json` on request
(v4, 1940 frames, state-anchored): frontend → movie viewer → play the one available clip.
Read-watches on the unlock array and FMV-id table, armed from movie frame 0, caught exactly
one array reader across the whole recording: **PC `0x800b4120`, inside a frontend-overlay
function with its prologue at `0x800b4084`** — a single pass at menu-entry time reading array
indices 1–15 (index 0 never checked).

Disassembling that function decodes the **complete availability model**, four gate classes
merged into one per-slot menu-state buffer:

1. **Story clips** — available up to the campaign-progress halfword `0x80082284` (the same
   halfword the save serializer stores at buffer+1);
2. **Bonus clips** — per-level unlock array byte `== 7` (indices 1–15);
3. **`0x8009B888` bits `0x01`/`0x02`** — two more entries, bit `0x02` being the
   campaign-100% ending flag `FUNC_800502C4` sets;
4. **`0x8009B889`** — the separate hidden-challenge bits gate the bonus-challenge clips.

Visually: the viewer is a 3D theater of screens; locked clips are red "?" panels (the same
"?" convention as the results screen's locked tokens); the one available clip shows a real
thumbnail, and selecting it plays a genuine letterboxed FMV.

**Playback dispatch**: the menu does NOT go through `fmv_bin_load` (zero execTrace hits) and
does NOT touch the FMV boot-buffer window (zero write hits). An execTrace watch on FMV.BIN's
own dispatch entry `0x800B6250` (already Canon) caught the single play call: `movie_id=10`
(the intro clip), called from resident PC `0x8003f580` — a different resident caller than
`fmv_bin_load`'s own internal jump into the same entry.

The recording's own anchored save had the array all zeros and campaign progress 1 — an
incidental clean negative control: no bonus-gated slot was shown available while its array
byte was 0.

## What's still open

The exact select-handler code between the availability builder and the resident dispatch at
`0x8003f580` (not traced); the story-clip row→movie-id mapping beyond row 0 → id 10; the
exact per-axis bit semantics within the 0–7 value (inferred, not traced
instruction-by-instruction); the level-index source register's own provenance; the meaning of
the 19th serialized byte (`0x8009B88A`); and whether re-visiting an already-100%'d level can
ever regress its byte. All are refinements within a now-fully-mapped mechanism, not open
questions about how it works.

## Evidence

`analysis/phase4_c17_movie_viewer.json`; static source
`asm/hand_written/800502c4_sub_800502c4.s` (cross-verified against
`asm/nonmatchings/resident/800502c4.s`); corrected Canon
`ObsidianVault/Canon/Functions/FUNC_800502C4_fmv_sequence_completion_check.md`; save
persistence cross-reference
`ObsidianVault/Canon/Functions/FUNC_80055478_serialize_savegame_buffer.md`; reused fixture
`movies/Phase4/Interpreter/100% Runs/LEVEL06.movie.json`.
