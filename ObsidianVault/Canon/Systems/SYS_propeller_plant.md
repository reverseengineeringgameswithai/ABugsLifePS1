# Propeller plant

## Canonical behavior

B02 is bounded-exhausted for the high-value Phase 4 questions. The propeller handler is
0x8005c258..0x8005c58c; the detach helper is 0x80046cac, and the XZ-radius helper is
0x800524b8.

Walking into the propeller while carrying the seed does not automatically release it.
The actor scan can apply lift to the carried seed without changing the carry offset.
The first release in the corrected movie is the ordinary throw writer at 0x80047ce8.

The propeller detach helper is reached only after the player lift predicate succeeds.
It is not a generic carried-object proximity response. On the high free-fall approach,
that player predicate succeeds while the carry offset is nonzero, so the helper clears
the carry offset and the handler then scans and lifts the same seed actor in the same
emulator frame.

## Exact player path

The player path requires XZ distance strictly below 40, player flag 0x80 clear,
contact field 0x800A6582 equal to zero, and plantY-playerY in 12289..40959. Latch 11
extends the lower band to 4097..12288.

Each qualifying handler tick calls 0x80046cac, sets player mode 5 and timer 0,
subtracts 512 from vertical velocity, clamps it to a floor of -3072, and selects
animation 13 with timer 120 when the animation changes.

## Exact actor path

The handler walks the compacted live actor pointer table at 0x80090748. It does not
test for seed ID and does not exclude carried actors. An actor requires flag 0x20 at
+0x5c, field +0x40 equal to zero, XZ distance strictly below 40, and
plantY-actorY in 12289..40959.

Each qualifying tick subtracts 512 from actor+0x20 without the player's -3072 clamp.
If both horizontal velocities are zero, two RNG bytes seed them. The handler clears
actor+0x5e after every qualifying actor lift.

## Interpreter runtime confirmation

Fixture hashes:

- Movie: movies/Phase4/Interpreter/B02.movie.json
- Movie SHA-256: 6992b9658e9fedec46a5489ff85a1ed160606fadeed41170ddc7840e439080ca
- State: movies/Phase4/Interpreter/B02.movie.sav
- State SHA-256: 3e19b52869076111e04b5810aefdbc18a01d2bec6d0674b77f2f708d5729c6df

The fixture is movie v4 with armed_while_paused and the built-in phase delay active.
Playback used pure Interpreter and normal-speed debugger.resume plus status polling.
A full-handler 10,000-event execTrace flight check remained visually synchronized.

The narrow causal replay produced 1,662 non-truncated exact-PC events and 61
non-truncated carry writes. C reduction established:

| Movie input | Runtime event |
|---:|---|
| 86..190 | No carry-offset write. The same seed actor is nevertheless lifted during 92..180. |
| 296 | Manual throw at 0x80047ce8, carry token 3696 to 0. |
| 298..326 | The thrown seed actor is lifted. |
| 401..423 | Player lift stores execute; visual riding continues through momentum. |
| 565 | Pickup at 0x80047858, carry token 0 to 3696. |
| 779 | Player lift calls the detach helper; 0x80046d04 changes 3696 to 0. |
| 779 | The player and actor 0x800A0BF0 are both lifted in the same emulator frame. |

The carry token 3696 is also the actor's offset from 0x8009FD80, resolving to
0x800A0BF0. This ties the pickup, detach, and actor-lift trace to the same seed.

All 59 detach calls paired by frame with all 59 player velocity stores. All 94 actor
velocity stores paired by frame and actor pointer with all 94 actor+0x5e clears.
All 10 player clamp stores wrote exactly -3072. Runtime actor velocity reached -3584,
corroborating the static result that the actor path has no equivalent clamp.

## Evidence and bounds

- Static artifact: analysis/phase4_b02_propeller_static.json
- Capsule artifact: analysis/phase4_b02_propeller_capsule.json
- Interpreter runtime artifact: analysis/phase4_b02_propeller_runtime.json
- Raw evidence: ~/Downloads/ABL-external-evidence/phase4/B02_propeller_interpreter_exec_20260802
- C reducer: tools/phase4_b02_runtime_trace_analyzer.c

Cold boot is not required because no disc, code, or asset was changed. Deferred work
is deliberately low-return: exhaustive RNG-byte distribution, every placement/actor
class, and pixel-level trajectory reconstruction.
