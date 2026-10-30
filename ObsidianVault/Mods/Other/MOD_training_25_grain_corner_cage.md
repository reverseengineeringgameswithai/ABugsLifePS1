---
kind: mod
id: MOD_training_25_grain_corner_cage
created: 2026-07-11
updated: 2026-07-11
status: runtime_verified
systems:
  - SYS_native_grain_gates
artifacts:
  - mod/caves/training_grain_gate.c
  - tools/training_word_pickups.py
  - tools/scenarios/duckstation/training_grain_gate.yaml
  - ceiling_cage_issue.sav
  - fall_through_floor.sav
  - on_crate.sav
---

# MOD - TRAINING 25-grain corner cage

## Intended behavior

The final `G` of the configured eight-letter TRAINING word is type-`0x3F`
entry `65`, moved to Flik's position in `desired_letter_loc.sav`:

- original runtime anchor `(-29775, 5943, 122634)`, RELOCATED 2026-07-11 to
  `(-7104, 3092, 112128)` (25,000 local units out the front, clear of the wall);
- file X/Z after the native `<<5` conversion: `(-222, 3504)`;
- file Y after the pickup pass's `(playerY>>5)-0xE6` bias: `-134`;
- staged entry: `(kind=0x13, x=-222, y=-134, z=3504)`.

The cage stands free on open floor (relocated 2026-07-11 off the stone recess,
whose diagonal wall cut the footprint and admitted a fatal corner clip-through).
A distinct wooden cage supplies complete front, back, left, and right faces
plus a slatted roof around the letter. Each wall has five uprights and three
continuous rails. Its lowering front plaque shows `25` and an amber grain glyph
rather than copying LEVEL02's crossed-twig visual.

At grain `0..24`, the cage behaves as a rectangular solid. Each wall returns
Flik to his last valid X/Z and stops horizontal motion without changing Y/VY. A
downward crossing lands on the roof at body Y `-10628` (native grounded body
offset 128 above the plane); Flik can jump onto and walk across it. Entry `65` remains retryable and bit 7 is denied silently. Grain `25` alone
does nothing: physical wall or roof contact latches ACTIVE, then drop advances
by `320` on the existing HUD animation cadence to `16000`. Collision opens after
drop `12000`; only the packed OPEN flag authorizes native collection.

## Regression correction (2026-07-11)

The first implementation had three defects matching the operator's manual
report:

1. collision covered only a shallow front band, so Flik could walk around its
   decorative short returns and remain behind the barrier;
2. the rendered returns did not form a complete enclosure;
3. cage primitives linked at `GPU_OUTPUT+0x1B8`, the near/HUD ordering-table
   bucket, and therefore overpainted Flik.

The correction uses the full local rectangle
`across=[-10000,10000]`, `inward=[-18000,6500]` with a `1800` player pad,
renders all four faces, and selects the cage OT link from Flik's live view-Z
using the measured scene-depth curve. The cage packets are prepended after
native world packets already occupy that bucket, so the cage executes first and
Flik's existing packet executes afterward on top.

Native construction can consume the type-`0x3F` source Y before the collectible
entity awards its word bit. The Training-only C tick therefore restores entry
`65` to authored Y `-45` while bit 7 is absent. Below 25, the resident collection
cave denies bit 7 and the C tick clears it defensively; at 25, the source remains
retryable until the native award lands, after which the pin stops.

## Floor, activation, burial, and roof correction (2026-07-11)

The next operator pass found four more functional mismatches:

1. repeated closed contact could make Flik fall through the native floor;
2. grain 25 lowered the cage without contact;
3. lowered geometry remained visible underground;
4. Flik could enter from above, so the cage needed a roof.

The floor failure was reproduced with a cold-boot held-Up phase. Before this
correction, 360 contact frames changed Flik from Y `5943` to `9783`, left
vertical velocity `1280`, and cleared grounded to `0`. The nearest-face code ran
after native collision and also overwrote the render reference and respawn
anchor, so native floor resolution and MOD position no longer described the
same point.

The interim blocker changed only live X/Z, ejected every intrusion to one front
coordinate, called native ground query `0x80037A38`, and republished the spawn
contract (`Y=floor-256`, zero velocity, grounded `0x0101`). That stopped the
floor death but was subsequently superseded: it made an airborne wall hit snap
Flik down immediately, could shove a side approach toward the front, and did
not make the roof a standable platform. The current swept-solid correction is
described below.

Word `0x800813EC` is now packed: low `u16` is drop distance; byte `+2` bit 0 is
ACTIVE, bit 1 is the MOD roof-support latch, and bit 7 is OPEN. Contact at grain
25 sets ACTIVE; threshold alone leaves the word zero. The collection cave reads
OPEN gp-relatively, so even a fall from above cannot award G while the cage is
up. Thirteen horizontal roof slats render and participate in the same closed
solid.

All vertical cage packets are clipped to world Y `6500` while lowering, and the
roof is omitted when it reaches that plane. Consequently bars, plaque, digits,
and grain glyph disappear progressively from the ground up; at drop `16000` no
cage packet remains visible.

## Swept wall, standable roof, and silent denial correction (2026-07-11)

The next operator pass supplied `walk_up_sound_jingle.sav` and identified three
remaining mismatches: airborne contact snapped Flik to terrain, walking contact
could shift him across the cage, and approaching the locked letter played a
collection jingle despite not awarding the bit.

The collision cause was the interim response itself: every horizontal
intrusion rewrote Y to a ground-query result, cleared all three velocities, and
forced grounded state. It also chose the front face regardless of the crossed
face. The C code reconstructs previous local X/Z from live velocity and resolves
the crossed face (minimum penetration only for a warp already inside). The
later correction below changes a swept crossing to restore that previous point
and stop both horizontal velocities. Wall contact never writes Y, VY, air
state, render coordinates, or the respawn anchor.

The roof is a swept top plane at `CAGE_TOP_Y+drop`. A falling body is clamped
only when its motion crosses `roofY-256`; that landing writes Y/VY, dynamic floor
height, and the native grounded latch while preserving X/Z velocity. Side walls
do not act at or above the roof, so it can be jumped onto and traversed normally.
Actual wall/roof collision, rather than a padded proximity box, now supplies the
ACTIVE contact signal.

The sound defect was independent of collision. The closed-G EXE cave jumped to
retail `0x800545CC`, which assigns `s1=-2`; the shared tail at `0x800545E8`
interprets every nonzero `s1` by calling `0x8005044C`. Closed denial now jumps to
the pointer increment at `0x800545D0` with `s1=0` in the delay slot. The later C
tick restores authored source Y, so the G stays retryable without an effect or
jingle.

## Persistent roof and floor-edge correction (2026-07-11)

The operator supplied two tighter regressions:

- `ceiling_cage_issue.sav`: hold Jump+Up; Flik initially landed on the roof but
  the next native landing-state transition restored terrain Y and the cage's
  already-inside fallback shifted him off the box;
- `fall_through_floor.sav`: hold Up; tangential wall motion carried Flik along
  the cage boundary past the native floor edge, after which gravity produced a
  normal death fall.

The roof now latches bit 1 (`ROOFED`) after a real downward top-plane crossing.
While Flik remains inside the top footprint with non-upward velocity, the cage
republishes only body Y `roofY-256`, VY `0`, dynamic floor Y, and native grounded
`0x0101`. Jumping upward or leaving the footprint releases the latch. This keeps
the MOD platform present across native air-state `5` without rewriting the
native air-state byte or retriggering Jump.

A swept wall crossing now restores the immediately previous X/Z and clears VX
and VZ. It deliberately preserves Y/VY and every native floor/air owner. This
matches the requested stop-at-a-wall behavior and cannot slide Flik sideways
onto the floorless side of the stone recess. Minimum-face projection remains a
bounded fallback only for an artificial save/warp already inside the box.

## Native roof landing and walk-off correction (2026-07-11, fifth pass)

The operator's retest showed the roof still was not a first-class floor: after
a held jump onto it Flik slid around in the jump-fall pose, and stepping off
an edge sometimes killed him. Live per-frame tracing found both causes:

1. The grounded latch alone never runs the native landing. `air_state` stays in
   its transient (`1`/`5`), `anim_index` stays `4`, and — because ground walking
   is velocity-driven with friction applied only by the integrator's contact
   path — the touchdown momentum never decays. The roof-landing branch now
   publishes the complete native landing contract: `anim 5`, `air 0`, VX/VZ
   zeroed, exactly what the integrator's own contact path produces. The state
   machine then behaves natively (idle `22`, walk `0`, held-X bounce, jump).
2. The MOD tick runs after the native integrator, so while roofed the
   integrator glues grounded Flik down to the recomputed terrain floor each
   frame and the tick re-pins him. On footprint exit that glue survives one
   frame: a 14k instant teleport onto whatever native floor lies below, a death
   pit near the recess edge. On release, an exit whose Y sits more than `2048`
   below the roof plane is recognized as the glue and undone: `Y = roofY-256`,
   grounded cleared, `air 2`/`anim 4` published, so gravity produces an
   ordinary fall. The Y-delta is the discriminator because the glue can emit a
   small negative VY (observed `-2`), while a jump always leaves Y above the
   plane. The OPEN-while-roofed release performs the same airborne handoff.

Roof support also shrank from the padded wall rectangle to the exact slat
rectangle, so Flik can no longer stand on air past the visible roof edge.
Walking off any of the four edges now lands on terrain with no life lost;
jump-in-place re-lands on the roof natively.

Known native interaction (not a defect of this pass, present at handoff): once
OPEN is latched the native construct pass awards the final G at its native
letter-award radius (~13k runtime units, writer `0x80053d10`), so a player
riding the roof down receives G during the descent. Closed/below-threshold
denial remains silent and absolute.

## Butt-slam / integrator-parity correction (2026-07-11, sixth pass)

The operator's `crate_ceiling_issue.movie.json` showed butt-slam interactions
misbehaving on the roof. Root cause: the fifth pass wrote MORE than the native
integrator's contact path writes. Measured native landing contracts on pebbled
ground: the contact path writes Y-glue, `VY 0`, grounded `0x0101`, and the
landing anim keyed by incoming air state (`6` heavy-fall squash for `air 4`,
else `5`) — and it NEVER writes `air_state`; every recovery (`air 4 → 1 →
0/5`, squash-timer exit to idle, held-X parking in `air 5` without re-jumping)
belongs to the state machine. Forcing `air 0` at touchdown created a non-native
bounce loop under held X; forcing `air 2`/`anim 4` at walk-off broke the
heavy-fall recovery and left Flik stuck in squash anim `6` on plain terrain;
and releasing the latch on VY sign made it flap during roof sprints, because
native grounded slope math emits small negative VY blips with `air 0`.

The sixth pass makes the roof tick integrator-exact: touchdown writes only the
contact set plus the roof-only VX/VZ zero (no native ground friction exists on
the roof); `air_state` is never written; the latch releases only on a real
jump takeoff (`air 1` with rising VY) or footprint exit; the glue-undo and the
OPEN handoff touch only Y/VY/grounded. Slam and heavy-fall onto the roof now
reproduce the pebbled-ground sequence exactly, held X parks without bouncing,
and roof sprints hold one continuous latch. Evidence and native baselines:
[[EXP_2026-07-11_native_and_training_grain_gate]] (sixth regression).

## Walk-jolt / resolver-parity correction (2026-07-11, seventh pass)

`on_crate.sav` showed that plain walking on the deck lurched ~1500 units on
alternating game ticks and skated Flik off the roof. Cause: the integrator's
resolved commit normally DISCARDS the movement code's raw position proposal
and stores its own collision-resolved position (measured ground motion is
exactly previous + velocity per tick). Fifteen thousand units above the
sector floor the collision loop never settles, so the undocumented
unresolved-move fallback at `0x80036d00..0x80036d44` runs instead
(`player.XYZ += velocity`) and the raw proposal survives. While ROOFED (and
not in a takeoff tick) the C tick now re-commits the velocity-integrated
position `prev + V` using the native previous-tick position mirror at
`0x800A6510/18` before any footprint math — a no-op on unjolted ticks. The
stand offset also corrected from 256 to the native grounded body offset 128
(body Y on the roof is `roofY-128 = -9128`); 256 left Flik visibly hovering.
Ground-control measurements confirmed the rest of the movement feel
(acceleration ramp, stop decay, reversal) is identical to pebbled ground.
Findings and evidence: [[EXP_2026-07-11_native_and_training_grain_gate]]
(seventh regression) and `src_re/movement_integrator_8003633c.c`.

## Aesthetic pass (2026-07-11, render-only)

Same blob, no collision or state change. All members are now Gouraud-shaded
(GP0 `0x38`, 9-word packets) with a lit top and shadowed base (`150/256`), and
each wall face has its own ambient (front `256`, left `224`, right `200`, back
`164`) so the box reads as directionally lit wood. Seven bars per side (thicker
corner posts) replace the sparse five; the plaque gained a light wooden frame,
a gradient backing, drop-shadowed seven-segment digits, and the grain glyph
became a diamond kernel with a highlight facet; the roof is thirteen slats with
front-to-back falloff over two edge beams. Worst-case primitive usage near the
closed cage is `55,852` of `85,948` bytes per GPU output buffer.

## Mid-tick pin, relocation off the wall (2026-07-11, eighth pass)

`on_crate_1.sav` reported three defects: no walk animation on the deck, a camera
shift during R2 slow-walk, and a corner clip-through death -- with the
operator's own (correct) diagnosis that the cage protruded into the stone wall.

**Timing.** The pin ran only in the RAW blob's HUD-pump tick, which executes
AFTER its consumers. `actor_skinned_update` (0x800563D4) early-exits at
0x80056400 when grounded is clear, so the locomotion selector at 0x8005649C
never ran and the anim stayed idle; the camera follower likewise read the
unresolved mid-tick position. A write breakpoint caught the native grounded
clear at `0x80036B90` (inside the integrator) landing one frame ahead of the
MOD publish. The pin therefore now ALSO runs at integrator exit: `patch_exe`
hooks the pristine `jal 0x80037A38` at `0x800495D0` into a 13-word guard cave
at `0x8007FB28`, which in Training tail-jumps into a pin appended to the RAW
payload. The pin replays the ground query, overrides its result with the roof
plane (the caller publishes it as the floor), publishes grounded, pins Y/VY,
and re-commits `prev + V`. The guard's pointer word defaults to the native
query and is reset to it on every execution, so `jr` is always valid and a
stale RAW-arena pointer is unreachable; the Training pump republishes the live
address each frame.

**Relocation.** The cage and letter moved 25,000 local units straight out the
front, onto probed-solid open floor: anchor `(-7104, 3092, 112128)`, entry `65`
restaged to `(-222,-134,3504)`, `CAGE_TOP_Y` -10500, `CAGE_BOTTOM_Y` 5000, roof
body Y `-10628`. The stone recess is no longer part of the design at all. All
four padded corners settle grounded (floors 2084..4440); eight input-driven
approaches into every face and corner give zero penetration and zero deaths.

Post-fix on the deck: walk anim `0` and slow-walk anim `29` engage, and camera
motion is calmer than the ground control. See
[[EXP_2026-07-11_native_and_training_grain_gate]] (eighth regression), which
also records the boot-hang gotcha: `0x80081858` is listed "candidate_free" by
`--suggest-caves` but sits in a BOOT-POLLED table (readers 0x8006EAC8/0x8006EBAC)
and hangs the disc at the PlayStation logo -- watch candidate caves from cold
boot, not only in gameplay.

## Implementation

`mod/caves/training_grain_gate.c` owns behavior and rendering. It reads the live
camera matrix/position, projects Gouraud-shaded untextured quads, appends them
through the current primitive buffer, and links them into Flik's native
scene-depth OT bucket. Emission order doubles as overlay priority (first
emitted paints last). The `25` and grain glyph are geometry on the same
lowering face.

`tools/training_word_pickups.py` compiles the C as freestanding MIPS-I, disables
compiler jump tables, rejects `.text`/`.rodata` relocations, extracts only
`.text`, and appends the 9,072-byte blob (plus the mid-tick roof pin) to the
Training type-`0x22` helper chunk. Blob SHA-256:
`3fccd825b506308a4429d64ef984c5a4dfffbbbe595a09a40a5e5532841c4b02`.

Private packed state is boot-safe word `0x800813EC`. `patch_exe()` requires it to
be zero in the incoming consolidated EXE. The resident pump reaches the RAW
helper only after its Training scene gate.

## Verification

- Focused tests: `15 passed` in `tests/test_training_word_pickups.py`.
- Safe suite: `143 passed, 7 deselected`.
- Layout validator accepted `blackberry,golddrop,grain_hud`.
- Consolidated build embedded and hash-verified all 13 staged files.
- `build/ABL_ALLMODS.bin` SHA-256 (eighth pass):
  `281a560d715fd4792e75b518b7e645dd6727b3fba33da5d562167e6b8535227c`.
- Cold-boot scenario after the eighth pass: `74/74` assertions, adding
  `player_control_is_live` to the roof/slam/walk coverage; report SHA-256
  `014962b31bae6f75b33c66125ab7d5bc4d338a2bdc7848432e5d5d1cf5e70e28`.
- Superseded seventh-pass disc `aabff70c…` (its `72/72` report `f6a70319…`).
- Superseded sixth-pass disc SHA-256:
  `aa1fedc4cdc6e1a648b692dddaa0ee2980d710150b512bd0db6b0af2e1cd4cfc`
  (its `69/69` report `2fa66fd7…`).
- Superseded fifth-pass disc SHA-256:
  `3e6b1a11abd4d180ca9903badfe9ab5a306d89efefcccbc2e452767673b298f9`
  (its `59/59` report:
  `efee74bf0493b96f6b53c02f6db689ae70f1b38d5b98af4553d2763c6471ad96`).
- Smoke gate `mod/smoke_test.py --disc build/ABL_ALLMODS.cue`:
  BOOT/ALIVE/RENDER/WALK all PASS.
- Full fifth-pass runtime evidence and capture hashes:
  [[EXP_2026-07-11_native_and_training_grain_gate]].
- Superseded fourth-pass disc SHA-256 (flat renderer, pre roof-landing fix):
  `1d7ecc99ab91a721e065b6fa9eb7896327718765d4d0698e9cc9143f9b9dde5d`.
- `training_grain_gate` cold-booted the rebuilt disc, verified SCUS-94288 and
  scene `0x11`, checked front/right/roof denial at grain 24, proved 25 grain
  alone does not activate, proved contact does, verified packed ACTIVE/OPEN,
  checked full disappearance and passage, awarded G only after OPEN, preserved
  airborne VY on a wall hit, stopped both horizontal components at the closed
  wall without losing the native floor, retained a roof landing at Y `-9256`
  for 60 frames through the native transition, and executed the closed-G deny
  branch three times with zero executions of the pickup-sound call.
  Report SHA-256:
  `3bfea4a5a3cede4464b6c19cede4f06bf559c4f6f079b2473f4c922845cb15e5`.
- Closed/full-wrap/lowering/open/floor/roof capture SHA-256 values:
  `f52ce52ddbd6905053ba66ca06ef825e036de64515516ffe3cb008a6c6bb18a6`,
  `ef00d865c4c80a60aae9f26ee84f53344b6a5bc39a3baa8bf448138d2dd1518b`,
  `66b77ae0fd59228cd72cb57f4ee77599043466323e2fe65e3a7156fe0cea7568`,
  `9f051e6cee4db1712f184f1c1cef9a83cc9b69e6c4cbaa643c594c815a7d46f5`,
  `6fefc41fa5e6964d4992273aad2577e5ad607f6dc5e71b832520039e2d767572`,
  and `f8672d53a1cdfa573a2b1357b074a63702422e6bace941354f64848dce01acf9`.
  The lowering/open pair shows ground-up clipping followed by complete removal.

See [[EXP_2026-07-11_native_and_training_grain_gate]] and
[[SYS_native_grain_gates]]. Resume context is in
[[Session_2026-07-11_-_TRAINING_25-grain_cage_handoff]].
