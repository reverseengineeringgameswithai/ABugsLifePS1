# FLIK letter system

Status: Confirmed original-game behavior; Phase 4 boundary exhausted.

## Canon

- Extracted gameplay data for levels 1 through 10 contains one F, L, I, and K source per
  level. The parsed `LEVEL00` record contains none; separately observed Training sources
  are not attributed to that record.
- Letter sources are object type `0x3F`, subtypes `0x10` through `0x13`.
- Collection sets bits `1`, `2`, `4`, and `8` in the byte at `0x800A65A2`.
- The exact complete set is `0x0F`.
- Completing the set awards one life only if the current lives byte at `0x800A65A0` is
  less than 9. The life cap is therefore 9.
- The SELECT HUD and level-results overlay both consume the same four-bit mask.
- The save serializer persists the resulting lives byte but does not directly persist
  the FLIK mask.
- Gameplay/player initialization at `fcn.80046b20` preserves lives from player offset
  `+0xA0`, zero-fills the complete `0xA8`-byte player-state prefix, then restores lives.
  The FLIK mask at `+0xA2` is therefore cleared while lives survive.
- A natural 100% route confirmed mask writes `0x00 -> 0x04 -> 0x0C -> 0x0E -> 0x0F`.
  With lives already at 9, the fourth letter executes the cap check and skips the life
  increment. The complete mask then survives results, the post-level cutscene, and the
  Journey hub.

## Evidence boundary

Native runtime evidence confirms two natural collection orders, source consumption, the
results presentation, the cap branch, and the gameplay-init reset. At movie-relative
frame 644, the `0x800A6500`/`0xA8` zero-fill called at `0x80046B68` produced the observed
mask write at BIOS PC `0xBFC02BB0`; `0x80046C00` restored lives immediately afterward.
No mask write occurred after completion through the Journey-hub tail.

The v4 Interpreter closure fixture completes the remaining controls. Starting at five
lives, natural L/K/F/I collection reaches `0x0F`; I's pristine store at `0x800540B0`
increments lives exactly once from 5 to 6. The same continuous recording then enters the
next gameplay initialization: `fcn.80046b20` clears mask `0x0F -> 0x00`, temporarily
clears lives, and `0x80046C00` restores the awarded value to 6. C03 is confirmed and its
Phase 4 runtime/static boundary is exhausted.

The two July 2026 collection movies predate execution-mode provenance and remain poll-only.
The trace evidence above uses the v4 Interpreter fixture `LEVEL06.movie.json` instead.

See `ObsidianVault/Experiments/EXP_2026-08-03_phase4_c03_flik_letters.md`.
