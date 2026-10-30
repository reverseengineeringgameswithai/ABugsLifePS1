---
kind: experiment
id: EXP_2026_07_10_golddrop_pickup_retirement_flag_regression
name: Gold-drop pickup retirement-flag regression
status: success
confidence: confirmed
source_state: evidence
validates:
  - MOD_gold_berry_token_drop
  - HOOK_800589D4
  - FUNC_800498AC
fixtures:
  - killing_spider.movie.json
  - movies/golden_glyph_pickup_not_working.movie.json
artifacts:
  - /tmp/golddrop_pickup_retire_fix.json
  - /tmp/golddrop_retire_post_state.json
---

# EXP_2026-07-10 - Gold-drop pickup retirement-flag regression

## Symptom

During collection of deferred gold-kill glyphs, tagged spiders briefly popped up and disappeared. After all glyphs were collected, spiders returned one by one. The counter path appeared to work, so the earlier verifier did not catch the lifecycle regression.

## Playback control finding

`golden_glyph_pickup_not_working.movie.json` is a 13,282-frame from-boot recording. Clean replay reaches gameplay at movie frame 7600. Arming ordinary execution/access watches near frame 0 forces the interpreter and changes loading timing; the same input then lands on title/loading screens even though `movie.status.reproducible` remains true. The reliable workflow is:

1. replay clean from the recorded anchor;
2. advance cycle-neutrally to a narrow pre-event movie frame;
3. only then arm instruction/access watches (or use a movie-frame-gated trace action).

This was a debugger-instrumentation divergence, not a game regression.

## Static diagnosis

Solved original assembly at `0x800498AC` tests two independent bits in `a1`:

- `a1 & 1`: death-animation/update path;
- `a1 & 2`: terminal retirement path at `0x80049B68`, which clears actor ID when `+0x62 == 0` and removes the actor pointer from `0x80090748`.

The mod pickup called `0x800498AC(enemy, 1)`. It therefore replayed animation but never retired/unlinked the tagged enemy. The correct deferred-pickup operation is `0x800498AC(enemy, 2)`.

## Fix

- Active consolidated and standalone ASM now use `li a1,2` at the pickup call.
- Reference C names value `2` as `ENEMY_FINISH_RETIRE`.
- `mod/build.py` verifies bytes at `0x80078DF0` are `2b26010c02000524` (`jal 0x800498AC; li a1,2`) for every manifest containing `golddrop`.

## Verification

Rebuilt `ABL_ALLMODS` and reran the existing forced-drop verifier:

- glyph: record `0x800B17D0`, action `123`, flags `0xE2`, tag `0x8009FD80`;
- pickup hook/HUD pulse/quota store/all-defeated/finalizer call all hit;
- quota changed `1 -> 0`;
- tagged actor `0x8009FD80` had ID `0` after pickup;
- `0x8009FD80` was absent from `0x80090748` after pickup;
- execution remained valid at frame 5124 (`PC=0x800107A4`).

Artifact SHA-256: `/tmp/golddrop_pickup_retire_fix.json` = `19e5a9303fbdc9959fc26fe61cb73c7fcb88416bea4dbe15ff80c7ae22b1992d`.

## Result

Success. The counter-only surface remains intact and the tagged enemy now takes the actual terminal retirement/unlink path instead of replaying its death animation.

