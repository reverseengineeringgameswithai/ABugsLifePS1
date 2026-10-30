# EXP 2026-08-03 - Phase 4 A06 downhill abdomen slide

## Question

Can Phase 4 row `A06_downhill_slide` close admission, sustained steering, release behavior, runtime latch timing, damage class, and the alleged natural slope-end termination using pristine ASM plus instrumentation-safe Interpreter movies?

## Method

1. Reject the name-adjacent retained capsule because its manifest pins `carry_handstand.movie.json`, not an A06 slide fixture.
2. Use compiled C extractors over pristine resident ASM to separate the `player+0x8C` contact fast path from the ordinary held-Cross state route.
3. Replay new v4 movies at normal speed on pristine media in an isolated DuckStation config with CPU mode fixed to Interpreter, fast-forward/turbo disabled, and instrumentation armed only after state load.
4. Reduce movie inputs, state writes, heading/motion writes, and block flow with compiled C programs under `/tmp`.
5. Keep observation, inference, and causal confirmation distinct.

The live escalation was required because the earlier static reconstruction attributed ordinary sliding to `0x8004892C..0x80048A70`, claimed release was inert, and claimed contact loss advanced state `5 -> 6`. The named missing domain was the actual runtime route and exit ordering.

## Fixture identity

Both runs used pristine `Disney-Pixar A Bug's Life (v1.0).cue`, serial `SCUS-94288`, with no overlays.

| Fixture | Movie SHA-256 | State SHA-256 | Frames | Initial emulator frame |
|---|---|---|---:|---:|
| `movies/Phase4/Interpreter/A06_slide_steering.movie.json` | `0d96c41768ad190e902312cdc78e8b88705ae8d83c78c56ddaf6809060d0ff4b` | `d22d122ef7d8e08e6b041d8e6c966f2d4a6eb34398d7fa5063e004ff8d0b3ba0` | 452 | 13701 |
| `movies/Phase4/Interpreter/A06_slide_natural_end.movie.json` | `2e51e56ec40089c5137f29e021be03edd119299d56569edd8afc36d16867717a` | `5ea40fbfc7705862af0b520e06e18bff77ee013b5148388a099bb44d8c0ca45a` | 689 | 15403 |

Both movies are format v4, `armed_while_paused=false`, `phase_delay_owed=false`, reproducible, and untruncated. Both normal-speed replays completed with target speed 1, fast-forward false, turbo false, and untruncated access/exec logs.

## Static correction

### Separate `+0x8C` fast path

- `0x80041AC4` can publish a contact-slot index plus one at `player+0x8C`.
- `0x800488D8..0x8004892C` tests that field and enters a surface-projector path when it is nonzero.
- `0x80048940..0x80048A70` contains its own bounded heading/projector logic and a new-Cross jump branch.
- Neither A06 movie wrote `player+0x8C`; the steering replay produced zero hits at `0x8004892C`, `0x80048940`, `0x80048A00`, and `0x80048A38` while visibly sliding.

Therefore this is a real but separate contact fast path, not the ordinary downhill abdomen slide exercised by A06.

### Ordinary held-Cross route

- `0x80048B5C..0x80048B6C` tests current Cross state (`0x4000`).
- With Cross held and the eligible player route active, state `4` or later reaches `0x80048CD8`.
- If `player+0x82` is grounded, the delay-slot value `5` is committed to `player+0x80` at `0x80048D64`.
- With Cross released, control goes to `0x80048D00`; if grounded, `0x80048D10` clears `player+0x80` to state `0`.
- If state `5` is ungrounded, this ordinary block does not synthesize a `5 -> 6` transition. The previous interpretation of `0x80048D58..0x80048D64` ignored the branch and delay-slot value flow.

The earlier admission result still holds: the dive sequence has no slope-angle comparison. State `2` uses the vertical floor/position separation test before state `4`; grounded held-Cross processing then latches state `5`.

### Terrain-driven slide maintenance and get-up

Visible sliding is controlled below the coarse action latch:

- `player+0x7A` is a 12-count slide-maintenance timer.
- After decrementing `12 -> 11`, `0x80048EE8..0x80048F3C` rearms it to `12` only while Cross is held and either projected component `+0x38 >= 0x300` or `abs(+0x3C) >= 0x300`.
- If both projected components are below threshold at that decision, the timer is not rearmed and continues down to zero.
- The animation selector builder at `0x800566F4..0x80056860` selects `0x1C` while the timer is exactly `12`, selects recovery animation `0x06` while the timer is positive but below `12`, and falls back when it reaches zero.
- `0x80056988..0x800569AC` copies desired selector `+0x88` to latched selector `+0x8A` and resets animation progress when the selector changes.

This is the terrain-driven natural termination mechanism. It can end visible sliding and start the get-up animation while action state `+0x80` remains `5` and Cross remains held.

### Ordinary steering

- `0x80047EBC` supplies the camera/analog-derived target heading at `player+0x28`.
- The ordinary input block subtracts or adds `0x20` from target heading for digital left/right at `0x800490D0` and `0x80049100`, then wraps it to 12 bits.
- `0x80049240..0x800492A8` converges current heading `+0x20` toward target `+0x28` using wrapped error, a cap, and a state parameter used as a right shift.
- The default ordinary path initializes cap `0x400` and uses shift `2` when the state parameter is zero, so its default correction is one quarter of error capped at `0x100` per update. Other resident state flags can select different parameters.

This shared ordinary steering law, not the fast path's `0x80` cap, is the correct A06 attribution. Motion then continues through the shared resident integrator; no universal slope-only scalar friction recurrence was found.

## Runtime observations

### Steering and release fixture

- Stable state `5`: movie frames `179..360`.
- Cross held: frames `147..359`; first released frame: `360`.
- State `0` store: frame `361`, one frame after release.
- During stable state `5`, digital left was held for 68 frames and right for 59 frames across multiple separated intervals.
- Current heading `+0x20` and target heading `+0x28` both changed during the steering intervals.
- The mid-run image visibly shows the abdomen slide; the start and end frames show standing states.

### Long-hold / alleged natural-end fixture

- Cross held continuously: frames `88..595`; first released frame: `596`.
- Coarse action state `5`: frames `119..596`; state `0` store at `597`, one frame after release.
- At relative frame `541`, the prior projected values are `+0x38 = 0x2FE` and `+0x3C = 0`, both below the `0x300` maintenance threshold.
- At frame `543`, timer `+0x7A` decrements to `11` and is not rearmed to `12`. Desired/latched animation changes from slide `0x1C` to recovery `0x06` while Cross is still held.
- The timer counts down to `0` at frame `565`, where the latched selector changes from `0x06` to `0x00`.
- Normal-speed captures bracket the visible transition: Flik is still sliding at playback `542`, is rising at `550`, and is upright at `568`.
- Position and velocity continue afterward because Up remains held through frame `592`; that later locomotion is not continued sliding.

The fixture therefore confirms terrain-driven natural termination while Cross remains held. It also shows that action state `5` is a coarse held-action latch, not a sufficient visible-slide predicate.

## Interpretation

**Observation:** the long-hold fixture changes slide animation `0x1C -> 0x06 -> 0x00` after projected motion drops below threshold, with Cross held throughout; coarse state `5` clears only after the later release.

**Inference:** ordinary sliding has two layers: terrain/motion controls visible slide maintenance and get-up, while held Cross controls the coarser action latch.

**Causal confirmation:** pristine ASM implements the exact `0x300` projected-motion test, timer rearm/countdown, selector mapping, and grounded release clear observed in the movie.

## Offensive contact class

The previously established shared phase-0 abdomen contact resolver remains applicable to offensive contacts: actor event `4` plus knockback/drop reaction, no direct actor-HP store in that resolver, followed by player rebound handling. The new runs did not need to repeat that already isolated resolver.

## Result and bounded limit

`A06_downhill_slide` is `substantiated` and `bounded_exhausted` for Phase 4.

- Admission is bounded to the dive/vertical-separation route followed by grounded held-Cross state `5`, not a slope-angle gate.
- Steering is confirmed through the ordinary target/current heading path.
- Terrain termination is confirmed: a below-threshold projected-motion sample prevents timer rearm, changes slide `0x1C` to recovery `0x06`, and reaches fallback animation at timer zero while Cross remains held.
- Grounded release separately clears the coarse state latch one frame later in both fixtures.
- The separate `+0x8C` surface-projector path must not be substituted for ordinary slide behavior.

A named obstacle, airborne release, or unusual collision surface could be studied later as a separate edge-case experiment. Exhaustively enumerating every surface would be high effort with minimal Phase 4 return and is not required to keep A06 open.
