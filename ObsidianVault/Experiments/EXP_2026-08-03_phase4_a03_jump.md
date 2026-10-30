---
kind: experiment
id: EXP_2026-08-03_phase4_a03_jump
created: 2026-08-03
status: completed
phase4_row: A03_jump
disposition: continue_required_partial
authority: pristine_original_game
---

# Phase 4 A03 - jump admission, release, apex, and landing

## Decision

`A03_jump` remains `Partial` and is well substantiated, but a follow-up audit
against `engineering-specs/phase4-closure.md` found that it is **not yet safe to
move on as bounded-exhausted**. Shipping ASM plus a retained capsule and four
same-anchor pristine controls close the normal jump recurrence. Directly
applicable ceiling/ledge behavior, powered release timing, an executable row
gate, a predeclared live escalation, and authoritative machine-layer integration
remain open. No new Interpreter movie is requested yet; fixture and offline
planning must identify whether the geometry controls require one.

## Evidence identity

- Disc: `~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue`
- Cue SHA-256: `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`
- Serial/title: `SCUS-94288`, `Disney-Pixar A Bug's Life`
- Save: `~/Downloads/ABL/level01_lookingdown_flatground.sav`
- Save SHA-256: `f25cb47f3270b65f6ecdc71c405e3e52d1b2069b8dca7915f2063e640cdbb337`
- Shipping ASM SHA-256: `f50038e52d548c44f59f8ac09ca17559e441be749d06dcf5b758cf6f13f38bdc`
- DuckStation source: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, dirty worktree recorded
- DuckStation binary SHA-256: `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`
- Isolated config/port: `/tmp/duckstation-a03-jump-20260803-01`, `24414`
- Owned PID `430474` was stopped through that config's launcher.

No disc, executable, save, guest RAM, or asset mutation occurred. This is a
save-anchored original-game mechanics experiment, so cold-boot reproduction is
not required.

## Capsule-first gate

The relevant retained evidence was queried before live replay:

`~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/B09_super_jump_comparison`

The capsule has 211 reconstructable frame-boundary records from emulator frame
`114952` through `115162`, no truncation/error, and no independent-control
mismatch. Manifest SHA-256 is
`9711ad5efaa441d97c65403a9c66827aa39b125577e185e0d6ac34155a6e469c`.
The movie Cross windows are `0..41` and `93..153`.

The first arc has power flags `0`, first stored `vy=-2816`, apex gain `16896`,
landing grounded `0x0101`, landing animation `5`, then idle `22`. The second arc
has `player+0x90 & 0x20`, first stored `vy=-3520`, apex gain `25984`, and the
same landing sequence. The direct v3 manifest supplies completeness and control
matching; the central Phase 4 preservation manifest and collection metadata
supply the fixture/movie/source/binary hash bindings. This is frame-boundary
evidence, not an every-cycle dump.

## Shipping ASM law

`asm/hand_written/80048138_player_vertical_update.s` establishes:

- `0x80048B60` tests Cross mask `0x4000`.
- Grounded admission is immediate; airborne admission additionally requires
  signed `(floor_y - y) < 1024` and `gp+0x69c == 0`.
- Animation `8`, caller-side `a0`, state `1`, and states `>=4` reject or divert
  admission.
- Accepted takeoff clears grounded, sets state `1`, requests animation `3`, and
  selects impulse `-3072` normally or `-3776` for `player+0x90 & 0x20`.
- Held Cross keeps state `1`; common gravity adds `256` per gameplay tick.
- Releasing in state `1` applies: if `vy < -800`, add `384`; arithmetic shift
  right one; subtract `256`; set state `2`; the common tail adds `256` again.
- Downward velocity is capped at `4096`.
- The swept-plane movement integrator owns ceiling/floor collision response and
  is the sole producer of grounded `0x0101`.

Reproducible C reducer: `tools/phase4_a03_static.c`. Documentation-grade C:
`src_re/jump_state_80048138.c`.

## Variable-height controls

The anchor starts at `y=-88578`, `floor_y=-88452`, `vy=0`, state `0`, grounded
`0x0101`, animation `22`. Externally injected input was cleared before and after
every load.

| Cross-held gameplay ticks | API frames at this anchor | Measured apex gain |
|---:|---:|---:|
| 1 | 2 | 6336 |
| 4 | 20 | 11520 |
| 11 | 62 | 17024 |
| 12 | 68 | 16896 |

All four branches returned to `vy=0`, state `0`, grounded `0x0101`, animation
`22`. Access-log rings were untruncated.

The 11-tick result is the important edge case. Releasing while `vy=-256` skips
the `+384` branch, halves to `-128`, and gains another 128 units. Holding through
the next tick reaches `vy=0` and therefore peaks at `16896`. The height curve is
mostly increasing but not strictly monotonic at its final step. The powered ASM
law analogously predicts a 14-tick release peak of `26080`, slightly above the
capsule's full-hold `25984`; that exact powered release timing was not replayed.

## Instruction-level causal trace

The one-tick tap armed `execTrace` over `0x80048B5C..0x80048D90` after loading
the save. It retained 506 events without truncation. The release chain was:

| PC | `s4` before instruction |
|---|---:|
| `0x80048D24` | -2816 |
| `0x80048D40` | -2432 |
| `0x80048D50` | -1472 |
| `0x80048D8C` | -1216 |

The corresponding apex gain was exactly `6336`. The retained transient JSON
hashes are:

- `/tmp/a03_h2_exec.json`: `c3106124fa057181ef7a3b1b9d0973b77ae7f513355b957e3d93de32f91d12a8`
- `/tmp/a03_h2_access.json`: `6cdf3dfb7e5fc02ab8629d1f50de9b7bd2ce44ed39cf75a4fb1d7257daf6dc29`
- `/tmp/a03_h4_access.json`: `7b1021727d24a516f672d39bd7d6e0e4674d2e464d9823dedd1e221f60f1a6ff`
- `/tmp/a03_h11_access.json`: `e97da5531515e3c06bb69c2855dc9c9ec12ca7ad2ebce633034c53eb83a9590d`
- `/tmp/a03_h12_access.json`: `409e9a90857d8455ac293d5bf6a51edebff73aa11ac0562c5a47ac66d3733327`

The launcher preseeded Interpreter. The traced branch also armed `execTrace`,
which forces the precise Interpreter observer. DuckStation later rewrote its
settings file without retaining a CPU stanza, so the uninstrumented curve runs
are not cited as a separate configured-mode proof. No movie was replayed in the
live session, so CachedInterpreter movie desync is not part of this evidence.

## Seed wording and row ownership

The baseline wording combines three mechanisms that should remain separate:

- A03 owns Cross-driven vertical jump admission, release, velocity, and landing.
- A13 owns the rising Cross edge that cycles a carried seed's selected output in
  `player_contact_response`.
- A15 owns physical seed cracking: jump plus butt-slam contact writes
  `seed+0x6c = 0x00010000` at `0x8004AF80`; the actor then sinks/cracks and calls
  `FUNC_8005BDBC` to spawn the plant.

Therefore A03 links to A13 and A15 rather than duplicating their selector,
color/tier, spawn, and plant-lifecycle matrices.

## Open closure work

- No retained A03 fixture supplies natural positive/negative ledge admission
  controls around the signed `<1024` threshold or a natural ceiling-contact
  state/velocity control.
- The exact ASM closes the `<1024` near-floor airborne admission mechanism and
  delegates collision to the swept-plane resolver, but that is not a behavioral
  sweep of arbitrary authored geometry.
- The powered 14-tick release micro-optimum is static-exact but lacks its own
  timing-varied runtime control.
- The input/power applicability matrix is not yet represented as an executable
  assertion across the row's declared modifiers.
- `analysis/phase4_live_escalations.json` contains no A03 declaration. The
  completed live run remains valid observation, but it cannot be retroactively
  called a contract-compliant escalation.
- `tools/phase4_a03_static.c` reduces the ASM law but does not yet guard the
  retained runtime outcomes or integrate the row into the authoritative queue,
  debt, campaign inventory, fixture audit, and Phase 4 gate.
- The transient trace hashes lack a centrally bound declarative regeneration
  scenario.
- Repository-wide indirect pointer-alias completeness remains low-return and
  can stay bounded after the directly applicable work above is resolved.

The first six items are active closure work, not harmless residuals. A new
Interpreter movie should be requested only if the fixture audit and non-movie
API controls cannot provide the required natural ledge/ceiling or powered-release
cases.

## Reproduction

```bash
cc -O2 -std=c11 -Wall -Wextra tools/phase4_a03_static.c -o /tmp/phase4_a03_static
/tmp/phase4_a03_static
```

Machine-readable evidence: `analysis/phase4_a03_jump.json`.

## Ceiling continuation: ASM plus pristine Level 11 resolver evidence

A03 is not closure-exhausted yet. The remaining direct behavior is a polygon-accepted natural ceiling response. This continuation closes the resolver semantics and bounds the available save-state search, but deliberately leaves the row continue_required.

### Observation

- The shipping 0x80035280 pass skips at 0x80035464 when endpoint distance s4 >= 0, then skips at 0x800354b4 when start distance s2 < 0. A crossing therefore requires d_end < 0 && d_start >= 0.
- 0x80032610 selects its 2D polygon projection using the largest absolute normal component, then branches on that component's sign. The resolver is not floor-sign-only.
- A C reduction of 3,176 untruncated resolver events from 13 pristine save-state anchors separated 2,203 floor events, 965 wall/boundary events, and 8 genuine ceiling-oriented events. Nine positive-ny wall planes were correctly excluded because nx or nz dominated.
- The sole dominant-positive-ny candidate was Level 11 sector 122, plane 0x8016fe20, normal (-7412,12324,-7847).
- From hash-pinned level_11.sav, walking Up for 60 API frames and jumping produced a real upward crossing: d_start=2771, d_end=-246.
- The same contact reached 0x80032610 with plane-relative arguments (-294,41,342), followed the positive-ny path for 62 instructions, and returned false at 0x80032d38 because the final projected edge test missed by 111 file-space units.
- Straight approach timing, left/right offsets, four air-steer controls, four one-frame grounded offsets, and six diagonal tail replacements produced no polygon-accepted retained ceiling winner. The closest case was Up=54, which crossed the plane but missed the final edge by 12; Up=53 did not reach the crossing.

### Inference

The original game implements ceiling-facing swept planes and the retained Level 11 data contains one. The available save anchor approaches the plane close enough to prove the signed-distance half of an upward ceiling collision, but not within the authored triangle footprint. Walls and cave boundaries are not being mistaken for ceilings because classification is by dominant normal axis.

### Decision and remaining gate

- Status: continue_required, substantiated partial.
- Machine-readable evidence: analysis/phase4_a03_ceiling.json.
- C reducers: tools/phase4_a03_ceiling_reduce.c, tools/phase4_a03_polygon_path.c.
- Remaining movie: movies/Phase4/Interpreter/A03_ceiling_contact.movie.json.
- Record on Interpreter from level_11.sav. Move Flik under a genuinely low or sloped retail ceiling in the cave area, jump straight into its underside while holding Cross, then release and land.
- Acceptance requires a truncated apex plus a dominant-positive-ny plane that passes both distance gates, returns true from 0x80032610, and becomes the retained resolver winner.
- Cold boot is not required because this is a narrow pristine runtime behavior check with no disc, code, asset, or RAM mutation.

Transient evidence and hashes are preserved in analysis/phase4_a03_ceiling.json. Raw traces remain under /tmp and are not repository artifacts.

## Interpreter ceiling movie attempt: negative control

The operator recorded movies/Phase4/Interpreter/A03_ceiling_contact.movie.json with an unobstructed first jump and a visually slanted-ceiling second jump. This movie is preserved as negative evidence; it does not close A03.

### Valid replay controls

- Movie format v4, 558 frames, reproducible, untruncated, no phase delay owed.
- Companion state SHA-256: 9e33f6c68ab576643636a9698c31291af326a2e1828b83417c5e055bdf23d091.
- Movie SHA-256: 0b7847cf99dda6986d8756c0186a475765984c542d1246d977ec9af7ffd2b0b6.
- The state-recorded cached cue and repository pristine cue both hash to 463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644.
- The accepted run used an isolated profile explicitly pinned to CPU ExecutionMode=Interpreter before playback, normal-speed debugger.resume polling, no fast-forward, and instrumentation armed only after the movie state load.
- An earlier run without an explicit ExecutionMode key was discarded and is not evidence.

### C-reduced result

- Exactly two jump admissions occurred.
- Control: base Y -3017, apex Y -23113, gain 20096.
- Claimed ceiling case: base Y -19977, apex Y -40073, gain 20096.
- Height delta: 0. The second jump is not truncated in world space.
- The replay retained six collision winners, all downward-facing floor/slope planes and all outside the ascent windows.
- During the second ascent there were zero dominant-positive-ny candidates, zero positive-ny wall candidates, and zero retained collision winners.
- All 936 endpoint events, 153 start events, 47 polygon returns, six winner events, 130 vertical events, and 357 Y writes were untruncated.

### Decision

A03 remains continue_required. Preserve the first movie as a negative control. Record the replacement as movies/Phase4/Interpreter/A03_ceiling_contact_v2.movie.json. Prefer a low flat underside or unmistakably concave overhang that hard-stops Flik well before the unobstructed apex, then release and land.

Machine-readable evidence: analysis/phase4_a03_ceiling_movie.json.
C reducer: tools/phase4_a03_movie_trace.c.

## Natural ceiling closure: Interpreter movie v2

### Fixture and method

- Movie: movies/Phase4/Interpreter/A03_ceiling_contact_v2.movie.json, SHA-256 04320a268ecbf412c0c7f5c702a4d4aa7ad6449fc13fd4e68c26461226cb465a.
- State: movies/Phase4/Interpreter/A03_ceiling_contact_v2.movie.sav, SHA-256 5dbeff5d02e1e391a251a4c55f55dc69f740911405f3c9ebff5180fb38af9baa.
- Pristine SCUS-94288 cue SHA-256: 463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644; no overlays.
- DuckStation revision fe0cca16b85e09a304cfde3c39669ce8c0adb8f5, binary SHA-256 f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899.
- Playback stayed in Interpreter at normal speed with debugger.resume and movie.status polling. Fast-forward and turbo were false. Instrumentation was armed after state load. Movie v4 reported reproducible, no phase delay owed, and no truncation.
- C reducer: tools/phase4_a03_movie_trace.c, SHA-256 735b84d8817f2102499cbc52036b11d31773639751056d75a199896b56254970.
- Trace counts: 2 jump admissions, 255 vertical events, 1,706 resolver endpoints, 1,085 resolver starts, 83 polygon returns, 24 retained winners, and 339 player-Y writes. Every stream was untruncated.

### Observation

The first jump is the uninterrupted in-movie control. Its render-Y gain was 20,096; subtracting the already established 3,200 entry displacement yields the exact 16,896 full-hold jump recurrence. It returned near its base and exhibited the expected vertical-velocity apex.

The second held jump rose only 10,880, truncating ascent by 9,216 relative to the recurrence control. It also returned near its base and landed.

At frame 162720 and cycle 92132163139, the collision resolver accepted plane 0x800f1d04 in sector 166, normal [-777, 16363, -288]. The segment crossed from d_start=219 to d_end=-1827; the polygon test returned true and the plane was retained as the winning collision. The reducer classified 243 ceiling endpoint events and excluded 216 positive-Y wall events, controlling the nearby-boundary confound.

### Inference

The dominant positive ny and accepted sign crossing identify the retained plane as a ceiling. The control and case share one state-anchored movie, so the reduced height is not a different jump recurrence or an input-release effect.

### Causal confirmation

The native resolver's accepted, polygon-contained, retained ceiling plane occurs during the truncated ascent, and the player subsequently descends and lands. This directly joins the static ASM ceiling branch to natural gameplay response.

### Disposition

A03_jump is **bounded-exhausted** and its direct behavior closure gate is **PASS**. The original movie remains a useful negative control; v2 supplies the missing positive natural-ceiling case. No additional Interpreter movie or cold boot is required for A03. Repository-wide Phase 4 queue, debt, campaign, and fixture controls remain separate from this row-level conclusion.
