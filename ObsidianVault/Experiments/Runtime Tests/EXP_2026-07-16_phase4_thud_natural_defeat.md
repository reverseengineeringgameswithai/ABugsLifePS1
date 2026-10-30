---
kind: experiment
id: EXP_2026-07-16_phase4_thud_natural_defeat
date: 2026-07-16
status: reproduced_partial
confidence: confirmed
source_state: original_game
evidence: [analysis/phase4_thud_defeat.json, analysis/phase4_thud_arena.json, analysis/phase4_thud_completion.json]
---

# Phase 4 — Thud natural resets, arena transition and defeat

## Question and fixture selection

Can an existing pristine recording reproduce Thud's repeated natural contact
damage/reset cycles, bind the reset-owner branch conditions and counter-8 arena
transition, and retain defeat/retirement/scene exit without requesting a new
operator fixture?

Before campaign selection, the run recursively inventoried 110 files under
`movies/Phase4` and 147 files in the broader movie tree. It reused the existing
root pair:

- movie SHA-256 `70e5988852315924e7eba7f8ba23632545ad329878e3e5b8a59de91955bcddaa`;
- save SHA-256 `789d9b601d592748af934c162513e91f1e63a8d2bbe8ce2cb3b9c16876b32a99`;
- movie format v1, 4113 frames, initial emulator frame 326743;
- inspected save version 84, serial `SCUS-94288`, with embedded and mounted
  pristine CUE/BIN SHA-1 pins `25adb139…` / `0bc1a297…`.

The filename and JSON serial were treated only as leads. Load-free save
inspection, media hashing, typed actor state and replay outcomes establish the
authority boundary.

## Observation

Six passive `movie.traceToFrame` targets reproduced with exact control versus
instrumented RAM/register/cycle/frame equality and untruncated coverage:

- target 0: scene 14, actor id 36, HP 50, flags `0x4055`, live slot present;
- target 3896: player health/lives `1/0`, actor HP 50, still live;
- target 3900: actor HP 0, still live and active;
- target 3902: active bit cleared and live slot zero;
- target 4041: scene 0, live slot still zero;
- target 4113: the same terminal typed state.

The target is the next input index; the post-step playback index is target - 1.
Recorded input is neutral in the late defeat interval, so it is not evidence of
a same-frame button or berry trigger.

Iteration 20 also replayed targets 964–967 with fresh passive pairs. They bind
Thud HP 50 → 48 → 48 → 50 while shared contact slot 26 holds action id 2,
damage class 0 and overlay target `0x800B4C70` holds 50. Every pair remained
cycle-neutral and untruncated. Iteration 22 later binds the particular recorded
player-projectile launch; this damage window alone does not.

## Transient writer attribution and controls

A separate 30-frame interpreter pass attributes HP 50 → 48 to resident
`0x800590E4` (`sh v0, 0x6e(s2)`) and HP 48 → 50 to save-owned runtime
`0x800B3ED0` (`sh v0, 0x6e(s3)`). At the damage store, `a0=50`, `v0=48`,
`s1=0x800B12D0`, `s2=0x8009FD80`; the selected record therefore begins at
`0x800B12C8`. At restore, `s3` is the Thud actor and `v0=50`. Exact target
reads occur at `0x800B3D44` and `0x800B3EC8`.

Static pristine EXE bytes show `0x8005905C` is an inner class-dispatch block
inside the resident `0x80058AF8` contact-vs-actor handler, not a standalone
entry. Class 0 takes the -2 branch. Resident `0x80054A64` calls the save-owned
overlay update at `0x800B3C70`; its exact 612-byte runtime slice hashes to
`6f01004b1528e9c2adac072c8afc9acb695637d0be3d4ffbb78061ed06b33574`.

Two fresh matched controls falsified independent alternatives:

- changing only contact damage class `0x800B12FC` from 0 to 127 at the same
  movie/emulator frame and cycle changed the next-frame HP outcome 48 → 46;
- changing only overlay target `0x800B4C70` from 50 to 49 changed the equal
  two-frame restored HP outcome 50 → 49.

These controls establish one damage class and one restore source. They do not
establish complete damage powers or the attack that launched the contact.

## Iteration 21 natural phase/reset observation

Fourteen additional passive `movie.traceToFrame` pairs reuse the first damage/
restore pair and retain seven later pairs. All are cycle-neutral and
untruncated:

```text
damage targets:  965 1311 1711 2125 2523 2939 3309 3739
restore targets: 967 1313 1713 2127 2525 2941 3311 3741
counter before:    0    1    2    3    4    5    6    7
counter after:     1    2    3    4    5    6    7    8
```

Each damage boundary has actor HP 48, target HP 50, derived value 0 and master
state 0. The exact arena sentinel alternates negative/positive. Each restore
has HP 50. The first seven restore to derived value 9 and master state 0; the
eighth has counter 8, master state 1, phase path coordinate 156704, heading 32 and
motion timer 149. Restore grain values are 0/0/0/4/8/12/14/14.

## Reset-owner attribution and causal controls

`debugger.disassemble` reconstructs all 153 instructions / 612 bytes at
`0x800B3C70` exactly to the pinned SHA-256. Two three-frame point-execution
windows at the first and eighth reset capture the actual equality, signed-floor,
negative/positive sentinel, counter-8, target-minus-four, grain-threshold and
restore-store operands. Point watches force the interpreter, so these windows
are operand attribution only.

Fresh matched branches all start from the same target-965 movie frame, cycle,
RAM hash and register hash before one named change and an equal two-frame step:

- target 50 → 48 matches actor HP and suppresses reset: HP/counter stay 48/0;
- actor HP 48 → 20 triggers the signed `<21` floor and suppresses reset;
- arena position exact sentinel → 0 restores HP but suppresses counter advance;
- counter 0 → 7 produces counter 8, master 1, heading 32, motion timer 149;
- grain 0 → 41 changes the same-frame derived result 9 → 8;
- with timer `0x800B4C44=0` in both branches, master state 0 produces
  HP/timer/counter/master 50/105/1/0, while changing only master to 1 produces
  48/0/0/1.

These outcomes causally bind the front-half reset conditions and the natural
counter-8 transition. The function continues after `0x800B3ED0`; they do not
bind a boss-owned attack, continuing attack policy or rolling-arena geometry,
ownership or completion.

## Iteration 22 — recorded player launch and counter-8 actor path

### Observation

At passive target 896 the player throw windup/in-flight count is 6/2 and slot
26 still has action 4. At target 915 the values are 9/3 and the same slot is
action 2 with TTL 99. An eight-frame interpreter attribution window beginning
at target 913 returns all 41 access events. Native allocator `0x8005A0E0`
writes action 4→2 at `0x8005A1D8`, TTL 100 at `0x8005A1E4`, and class 0 at
`0x8005A270`. Its sole entry has `ra=0x80047254`, which identifies the resident
player-throw call at `0x8004724C`.

After the eighth restore, passive targets 3741/3815/3896 show phase value
`0x800B4CB0` moving 156704→61984→-40416. Actor position moves
`[121858,-39328,-1751]`→`[102808,-39328,-3845]`→`[532,-39328,-1551]`.
Overlay stores `0x800B43B8/0x800B43BC` copy that value to actor +0x28/+0x34;
resident sites `0x8004CD6C/0x8004C928` read those X/Z fields. Offset +0x30 is
retained as raw `-608` but remains unnamed.

### Inference

The observed action-2 allocation belongs to the native player throw dispatcher,
not a Thud-owned attack. The sampled selector is insufficient to assign a berry
color. Address `0x800B4CB0`, historically labeled `arena_position`, is at least
a Thud phase path coordinate that feeds actor motion; actor motion does not by
itself identify the rolling-arena geometry owner.

### Causal confirmation

Two in-memory descendants of the same pinned movie are full-RAM, register,
cycle, frame, PC and SP equal at target 896. Clearing only Square in source
frames 896..917 suppresses the action-2 allocation at target 915, changes target
965 from HP/action 48/2 to 50/4, and suppresses the first counter increment at
target 967. No derivative movie bytes are retained.

At target 3741 a separate matched control changes only `0x800B4CB0` by +4096,
then advances both branches equally to target 3896. The mutation produces exact
+4096 deltas in actor +0x28/+0x34 and final actor X, with zero deltas in actor
Y/Z and player XYZ. Both branches still reach HP 0, flags `0x0055` and live slot
0 at target 3902. This binds the actor path but does not identify the complete
phase termination rule.

### Rejected hypotheses

- The action-2 contact is not a Thud-launched attack in this recording; its
  exact allocator caller is the resident player throw dispatcher.
- `0x800B4CB0` cannot be promoted to complete rolling-arena geometry from its
  old name; the causal result proves an actor path coordinate only.
- Actor +0x30 is not named from vector symmetry; only +0x28/+0x34 have exact
  stores, resident readers and the one-field propagation result.
- `debugger.functionBounds` around the save-owned overlay did not supply a
  trustworthy policy boundary and is not retained as function-ownership proof.

## Iteration 23 — one rolling-boulder contact is causal

### Observation

Passive targets 1466/1472 are cycle/RAM/register-neutral and move player health
3→2 while player position changes `[104318,1478,-20326]`→
`[99005,-934,-18472]`; Thud HP remains 50. Three transient PNG captures at
targets 1466/1470/1472 visibly show a large rolling boulder overlapping the
player. Their SHA-256 values are `696e37e7…`, `f702fae1…`, and `b0594f0f…`.
The captures remain under `/tmp` and are not retained as machine authority.

The save-owned runtime block `0x800B4814..0x800B4B20` reconstructs exactly
from 196 disassembled instructions / 784 memory bytes, SHA-256
`4169c4691a2d31867a9d237d006d91a83b5d3a2d2485c8669f0fed3e3032218d`.
Its first loop calls `0x800292DC` across ten rows. Its second loop processes six
rows and calls resident `pass2_object_transform_update` `0x80029508` followed
by resident `collision_candidate_builder` `0x80037320` for each row.

### Attribution

A six-frame interpreter-only window begins at target 1466. All row/transform/
candidate/distance watches return 12/12 events (six rows in each of two update
ticks), while the raw-player gate, row state store, damage call, resident entry
and health store each return 1/1 without truncation. At the contact tick:

```text
row  squared distance  threshold  inside
 0       13266474       490000    no
 1       64727638       250000    no
 2       46873046       160000    no
 3       16903332       490000    no
 4         454805       490000    yes
 5        7953178       490000    no
```

Only row 4 passes `0x800B4A60`. Its transformed position is
`[3448,-547,-919]`; its phase word is `0x800B4C88` and squared-distance
threshold is `0x800B4C1C`. Raw player field `0x800A6592` is zero, allowing
save-owned `0x800B4AE0` to call resident level-transition initiator
`0x8004A700` with `a3=0`. Access logging attributes the sole health write to
`0x8004A888` (`sh v1,0x6594(at)`), old 3, new 2. This forced-interpreter pass
is source attribution only; the passive pair carries natural timing.

### Causal confirmation

Two branches reload target 1466 with identical full-RAM/register hashes, cycle,
frame, PC and SP. The control retains row-4 threshold 490000. The mutation
changes only `0x800B4C1C` to zero. After six equal emulator frames, natural
health is 2 and threshold-zero health is 3; deterministic target-1471 endpoints
have identical player position `[99005,-934,-18472]`, frame, PC and SP. Fresh
iteration-34 replay places threshold-zero exactly one cycle earlier at the same
PC `0x8004FEA4`.
Therefore the
row-4 squared-distance gate is causal for this player-health decrement.

### Boundary and rejected alternatives

- This is one rolling-boulder transform/distance/damage contact, not complete
  rolling-arena geometry, ownership, phase linkage or completion.
- The transient picture supplies visual context but does not assign a GPU draw
  owner. Runtime calls, row operands and the one-field control assign causality.
- `0x80037320` receives caller-supplied transformed object coordinates here;
  it is a generic entity/object candidate builder, not the player-floor owner.
- `0x8004A700` remains a resident level-transition initiator with an `a3=0`
  health-decrement path; this one caller does not rename its whole function as
  an arena-damage-only ABI.

## Writer attribution

After loading the movie start state, instrumentation was re-armed at target
3896 and run for 145 frames. The log returned all 103 events without truncation:
HP 1 hit, flags 54, live slot 48 and scene 0. Exact value-changing stores were:

- HP 50 → 0 at `0x800B4528` (`0xA660006E`);
- final flags `0x4055` → `0x0055` at `0x8004D270` (`0xA6220000`);
- live slot `0x8009FD80` → 0 at `0x8004D43C` (`0xAC200748`).

Earlier frames contain active-clear/re-arm pairs. Selecting the last matching
clear, immediately before live-slot zero, distinguishes persistent retirement
from those pulses. The scene watch has zero events because the transition
resets/unloads instrumentation; passive target 4041 is the scene authority.

Access logging forces the interpreter, so no access-log frame/cycle is used as
behavioral evidence. The passive cached-interpreter pair supplies behavior.

## Static correction and failed identity hypothesis

The stale claim that Thud's VM at `0x800777A6` is undecoded is false. E07
already decodes all of `program_19`; `0x800777A6` is a confirmed one-instruction
jump back to the parking instruction at `0x800777A4`. The hypothesis that this
tiny loop is the full attack/phase FSM is rejected; higher policy remains with
unresolved callback/overlay state.

The hypothesis that the save-restored Region-A image exactly equals either
staged LEVEL08 executable is also rejected. Both complete candidate-length
hashes differ. The exact writer slice is retained as save-owned runtime bytes,
not laundered to a staged file identity.

Iteration 21 also rejected a full-movie access-log scan forced into the
interpreter. It diverged from the cached natural control and returned only
unrelated timer/master events, so it is neither retained nor used as behavior
authority. The bounded point windows plus separate passive pairs replace that
failed approach.

## Inference and causal confirmation

Scene graph plus typed actor id/source/callback identifies the active record as
Thud in Bug Bar. Eight passive damage/reset cycles, exact branch operands,
matched reset controls, the natural counter-8 transition, later HP-zero writer,
resident active/live retirement and passive scene exit confirm this bounded
lifecycle. One player-projectile launch and the post-counter-8 actor path are
also causal. One separate six-row rolling-boulder contact is causal for player
health 3→2. One Thud-owned action-20 launch and its player-proximity grain
effect and textured billboard are causal; other attacks, sound, the full hit curve, continuing overlay policy,
complete arena row/model breadth, phase linkage, ownership and completion remain
separate open claims.

## Commands and cleanup

```text
find ~/Downloads/ABL/movies/Phase4 -type f
find ~/Downloads/ABL/movies -type f
python3 tools/phase4_thud_defeat.py --port 20210 --token '<redacted>' --config-dir /tmp/abl-phase4-i20-thud-final3-20210 --instance-state recreated
python3 tools/phase4_thud_defeat.py --port 20213 --token '<redacted>' --config-dir /tmp/abl-phase4-i21-thud-retained-20213 --instance-state recreated
python3 tools/phase4_thud_defeat.py --port 20326 --token '<redacted>' --config-dir /tmp/abl-phase4-i22-thud-final-20326.xMbPk2 --instance-state recreated
python3 tools/phase4_thud_defeat.py --port 20332 --token '<redacted>' --config-dir /tmp/abl-phase4-i23-thud-final-20332.w3mppt --instance-state recreated
python3 tools/phase4_thud_defeat.py --port 20337 --token '<redacted>' --config-dir /tmp/abl-phase4-i23-thud-refresh-20337.pnfEgv --instance-state recreated
python3 tools/phase4_thud_defeat.py --port 20343 --token '<redacted>' --config-dir /tmp/abl-phase4-i23-thud2-refresh-20343.QUFmrn --instance-state recreated
python3 tools/phase3_record_types.py --probe --port 20328 --token '<redacted>' --config-dir /tmp/abl-phase4-i22-record-probe-normal-20328.QR6qVK --instance-state recreated
python3 tools/phase4_thud_defeat.py --port 20457 --token '<redacted>' --config-dir /tmp/abl-phase4-i26-thud-final-20457.wDA6LE --instance-state recreated
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_thud_natural_defeat.yaml
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_thud_action20_grain_control.yaml
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_thud_action20_source_suppression.yaml
pytest -q tests/test_phase4_thud_defeat.py
```

DuckStation revision was `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`;
binary SHA-256 was
`c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`.
The iteration-20 generator stopped only PID 3613937. The iteration-21 retained
generator stopped only PID 3919624 owned by its fresh config. Its independent declarative
scenario ran 21 phases / 63 assertions on hash-verified pristine media, passed
63/63, and stopped only PID 3863200; transient report SHA-256 was
`97cbee6d35c89fad63cf727289d87fc0b1cb0c8ed8e1286051cfe929d048c073`.
Iteration 22's final source-fresh generator stopped only PID 4078251 owned by
its new config. Retained artifact SHA-256 is
`91070630c5efdb5e35b8d4ee636acdf97b8bd4a0c37d65cc4b9bb8959a0baa85`.
The expanded declarative scenario passed 78/78 assertions across 24 phases on
independently hash-verified pristine media, stopped only PID 4084092, and wrote
transient report SHA-256
`ecbedac82fb830f2d33589b7fc965f96aec58a9b3752c4b995fd26259856a871`.
The dependent 42-anchor strict-pristine record probe was also regenerated after
typing +0x28/+0x34; it reports 53 varying, 3 constant and 24 zero remaining
actor unknown bytes, stopped only PID 4142887, and has artifact SHA-256
`3d4e0eb6a95acc4ac967d3e3fcf52da072db2dca7b56533c56eef5639b5a3ed7`.
Iteration 23's source-fresh generator stopped only PID 120633 owned by its new
config. Retained artifact SHA-256 is
`50e2487d17eb30db72d49bba13eb7e14b2a6c5cb38a461e4ad9fcc2cae280e99`.
The expanded declarative scenario passed 90/90 assertions across 26 phases on
independently hash-verified pristine media, stopped only PID 121804, and wrote
transient report SHA-256
`dfd8ca616b18899f9e0051e99876977f047e00626a625784b0f0c80c71f9066d`.
After the date-bound external-fixture and Event-VM dependency hashes changed,
the same generator was replayed after the accepted CachedInterpreter E07
refresh on fresh config `/tmp/abl-phase4-i23-thud2-refresh-20343.QUFmrn`, port
20343. It reverified the pristine mounted/save media, reproduced every
schema-v5 low-level predicate, and stopped only owned PID 278871. The
source-fresh artifact SHA-256 is
`c871428892140737509bd7590a7807c5506eb83d72d56498d5707f43093f9f3e`.
No movie, save, disc, BIOS, token or capture bytes are committed.

## Iteration 24 — post-restore Thud-owned launch

The required recursive inventory was repeated before campaign selection: 110
files exist under `~/Downloads/ABL/movies/Phase4` and 147 under the
broader movie tree. No additional Thud fixture was present, so the existing
centrally pinned movie/save pair remained the relevant oracle.

Fresh isolated exploration followed the save-owned function beyond restore
store `0x800B3ED0`. The exact slice `0x800B3ED4..0x800B4004` is 308 bytes / 77
instructions with SHA-256
`10992dee6815d74e6b89109980f16d6c60f0230d94f52f0730b7e217d30badba`.
It contains allocator call `0x800B3FF0`. A separate later call at `0x800B4324`
was not reached in this bounded first-reset window and is not promoted.

Passive `movie.traceToFrame` pairs at targets 970/971 were independently
cycle/RAM/register neutral. Derived countdown changed 9→8, slot 17
action/TTL/class changed 1/0/0→20/200/128, and cumulative counts changed
`0x800B3FF0` 1→2 plus allocator entry `0x8005A0E0` 6→7. The one-frame delta
therefore contains one natural allocation.

The attribution replay began at target 967 and ran ten frames under the forced
interpreter. It retained 27/27 untruncated writes over exact slot record
`0x800B10D0`: `0x8005A1D8` stores action 1→20, `0x8005A1E4` stores TTL 200,
and `0x8005A270` stores class 128. At call `0x800B3FF0`, `s3` names Thud actor
`0x8009FD80`; allocator entry sees return `0x800B3FF8`. This pass is source
attribution only, not timing evidence.

Matched target-970 branches began with identical full RAM, registers, cycle,
frame, PC and SP. The natural one-frame branch produced derived/action/TTL/class
8/20/200/128. Writing only `u32 0x800B4CB4` from 9 to zero produced
0/1/0/0 at the same movie and emulator frame. The mutation endpoint is one
cycle earlier and has a different PC because the named field changes control
flow; it is not described as a cycle-neutral counterfactual. Each passive
boundary remains cycle-neutral against its own control.

This confirms one Thud-owned action-20 contact-object source/launch. Generic
action-id searches did not establish a visual or damage meaning, so target,
hit, damage, completion effect and other variants remain open. D18/F09 remain
active and incomplete.

The source-fresh iteration-24 generator used port 20402 and fresh config
`/tmp/abl-phase4-i24-thud-final-20402.ePUqYe`, then stopped only owned PID
448687. Retained artifact SHA-256 is
`de98f3c863f4dd900d2f1afafe3cb8af0fdcded2a3b03d6d186e0a98013a871f`.
The independently launched scenario passed 99/99 assertions across 28 phases,
reported pristine serial `SCUS-94288`, stopped its PID-scoped instance, and
wrote transient report SHA-256
`25486c6d32a6230fb51f878dacdc3206802244af8fed4163ebb3c69b74aad59e`.

## Iteration 25 — action-20 natural miss and controlled grain effect

The required recursive inventory again found 110 files under the Phase-4 movie
tree and 147 in the broader movie tree. No additional Thud recording existed,
so the same centrally pinned pristine-classified movie/state pair remained the
relevant fixture. The pristine CUE/BIN and save media were reverified before
each isolated replay.

Passive targets 972/973/1021/1023 followed slot 17 after its bound action-20
launch. Action/radius/state remained 20/100/24 while active gate counted
200→199→175→0. Grain remained 0 and health remained 4. This falsifies the
attractive claim that launch alone guarantees a natural pickup, while one
sample cannot establish natural-hit frequency.

Static pristine disassembly maps dispatch-table entry `0x8001B5B8` to
`0x800589B8`; its common tail calls resident grain handler `0x80054EAC`.
Retained slice hashes are `c242b0ea…6563b`, `38012709…e600` and
`26aab721…87cb` for the dispatch entry, common tail and grain-writer window.
No save-owned Region-A meaning is projected onto those resident functions.

Matched target-972 control and mutation branches began with exact RAM,
register, cycle, frame, PC and SP equality. The only mutation wrote signed
radius_add `0x800B10F8` from 100 to 6000, changing two bytes. One frame later
the control retained grain/health/action/active/radius/state
`[0,4,20,199,100,24]`; the mutation produced `[1,4,20,1,6000,16]`. The
deterministic target-972 endpoint has exact equal frame, cycle, PC and SP.

Separate re-armed access and execution watches forced the interpreter only for
attribution. All ten access events were retained. Dispatch, grain handler,
grain store, state store, active store and bookkeeping call each executed once;
bookkeeping entry executed three times in the frame, with the decisive entry
returning to `0x80058A04` on the slot-17 record. Exact stores were
`0x80054F9C` (grain 0→1), `0x800589E0` (state 24→16) and `0x800589E4`
(active gate →1). No damage, visual, sound or completion result is inferred.

Iteration-34 deterministic movie targets supersede this pause-edge timing
paragraph: the row-4 threshold-zero arena branch is one cycle earlier at equal
PC/SP at target 1471, the radius mutation is one cycle later at PC `0x800104B8`
versus control PC `0x800198F0` at target 972, and fresh
iteration-34 replays place the derived-countdown-zero launch-suppression branch
one cycle later at target 971. The behavioral outcomes are unchanged.

The source-fresh schema-v7 generator ran on port 20421 with fresh config
`/tmp/abl-phase4-i25-thud-final-20421.ZVWTmP`, regenerated artifact SHA-256
`39a4ba53b2015e5a8faa984012a3e6cb0d20ca6979fb63d66b8d69a3ffe2862c`,
and stopped only owned PID 701681. The expanded natural scenario passed
108/108 assertions across 30 phases and stopped only PID 702689; transient
report SHA-256 is `09651de1b1421030cc33b478e1deca9fd0aae2895203a0ab239f68d15d9579d9`.
The new one-field scenario passed 16/16 assertions across two phases and
stopped only PID 702561; transient report SHA-256 is
`764bf1fd57077898584164781a5eb38537000b18921ad0554a41271e030648d4`.
Both report media checks were pristine and serial `SCUS-94288`. No external
fixture or report bytes are committed.

Because this iteration promoted contact action/radius/state into the shared
typed record, the dependent live record probe was also regenerated instead of
leaving Phase 3 stale. A fresh normal-binary instance on port 20422 sampled all
42 strict-pristine anchors, refused zero media, observed signed radius values
100..190 and signed action-state values -123..7 on the declared normal binary,
and stopped only owned PID 722524. Its artifact SHA-256 is
`39bbbe79b8c5fb83009459f9ce0a29de3a961a3feb866e561a76e44e251fe028`.

## Iteration 26 — action-20 textured billboard is causal

### Observation

The required inventory was repeated before campaign selection: 110 files under
the Phase-4 movie tree and 147 under the broader tree. No second Thud fixture
exists, so the same centrally declared movie/state pair was inspected again and
replayed on hash-verified pristine `SCUS-94288` media.

Natural and countdown-zero branches reload target 970 from identical full RAM,
registers, cycle, frame, PC and SP. Only `0x800B4CB4` changes 9→0. Both advance
to exact movie target 980 / emulator frame 327724. Fresh iteration-34 replay
retains natural PC `0x800104B8`; the suppressed branch is one cycle earlier at
PC `0x80010508`. The
natural action-20 branch and source-suppressed branch differ in 593 of 488000
framebuffer pixels, normalized score `0.0012151639344262295`, with one
`(449,159,28,35)` bounding box. The comparison remained in memory; no image or
diff-image bytes were written.

At natural pixel `(295,65)`, the GPU picker returns opaque RGBA
`[107,156,0,255]` and a textured GP0(2C) quad. Its exact DMA/RAM source is
`0x001CF3D4`, vertex pointer `0x001CF3D8`, probable linked-list header
`0x001CF3D0`, texture page `(512,0)` in 4bpp mode, CLUT `(880,221)`, UV range
240..255 / 112..127, and 20×13 screen rectangle. The session-relative GP0
index is not promoted as a stable identifier.

### Attribution

The pristine resident `0x80014844..0x80014AD4` slice is 656 bytes, SHA-256
`7fa7b409bac944db9fb8a779fe26d9965930b9ca986002f8e849875ff2e36a0e`,
and corresponds to `asm/hand_written/80014844_sub_80014844.s`. A re-armed
interpreter-only attribution pass retained all 118 access events: 102 slot reads
and 16 packet-window writes, without truncation. Twenty-two renderer reads at
frames 327716/327722 include action 20 at `0x8001496C`. The picked packet's first
writes map addresses `0x801CF3D4/DC/E4/EC/D0/E8/D8/E0` to instruction PCs
`0x80014A30/34/38/3C/40/44/58/6C`.

Record `+0x34` is loaded as command/color word `0x2C808080`; it is not an
ordering-table field. The renderer computes ordering depth and the table link
from GTE/depth-table state. Access logging forces the interpreter and carries
source attribution only; the matched cached-interpreter framebuffer control
carries the visual behavior and timing.

### Causal confirmation

Suppressing the already-bound countdown source eliminates the action-20 record
at the visual endpoint and eliminates exactly the attributed textured-billboard
region. The independent declarative source-suppression scenario asserts the
precondition, absent launch and absent action 20 at target 979. It passed 15/15
assertions across three phases on separately hash-verified pristine media and
stopped only PID 924711. Transient report SHA-256 is
`127c26780dc02228f24cc9b05d0eeaa393b8d968e16bd8e0b20c334f6ffdaff7`.

### Rejected hypotheses and retained boundary

- The 593-pixel region is not inferred from an attractive screenshot; source
  suppression, exact framebuffer diff, object pick and packet writes form the
  causal chain.
- Record `+0x34` is not renamed as an ordering-table link. Its full word is the
  GP0 command/color word, while the renderer creates the table relationship.
- The framebuffer and raw GP0 stream are not retained because typed metrics,
  draw provenance, exact writers and hashes are sufficient.
- This proves textured-billboard presentation only. Sound, natural-hit
  frequency, damage, completion and other attack variants remain open.

The source-fresh schema-v8 generator used fresh config
`/tmp/abl-phase4-i26-thud-final-20457.wDA6LE`, port 20457, stopped only PID
923866, and retained artifact SHA-256
`c8c56273cac471b69959ced9573031ecd44d4602ec67cd3f744b5ab61272de89`.
Independent natural and grain-control scenarios passed 108/108 and 16/16;
their transient hashes are
`b8953d62e4518ca69fcbfc6b08008356374c2662bcc9999214d52fef5afb0c8b`
and `a26b82049c4591b5dcf257a6e28dbbb52f7c5eca8af869479204cdc2b58dd336`.
They stopped only PIDs 924851 and 924975. No fixture, report, image, token, BIOS
or media bytes are committed.

## Iteration 27 — action-20 launch sound request and SPU sequence are causal

### Inventory and identity

Before reusing the campaign, the recursive census again found 110 files under
`~/Downloads/ABL/movies/Phase4` and 147 under the broader movie tree.
The sole relevant Thud pair remained the centrally declared v1 movie SHA-256
`70e5988852315924e7eba7f8ba23632545ad329878e3e5b8a59de91955bcddaa`
and pristine-classified state SHA-256
`789d9b601d592748af934c162513e91f1e63a8d2bbe8ce2cb3b9c16876b32a99`.
Fresh pre-load state inspection and mounted CUE/BIN hashing verified pristine
`SCUS-94288`; ALLMODS was not an input or authority.

### Attribution

A ten-frame interpreter window re-armed after state load watched save-owned
`0x800B3FFC`, resident `play_sound` `0x8005044C`, and positive dispatcher
`0x80050994`. The caller executes once with `a0=0xFFFFFFF2` (signed -14) and
`s3=0x8009FD80`. The exact `play_sound` entry receives `a1=0x8009FD84` and
`ra=0x800B4004`. Three `play_sound` entries occur in the window; the cue,
position pointer and return address distinguish the Thud request from two
unrelated cue-26 calls. The positive dispatcher has zero hits for this negative
request. All pages are complete and non-truncated.

The pristine 940-byte resident slice `0x8005044C..0x800507F8` has SHA-256
`ffd93c418662e743429c966f4080065688227dcee6b17aab0ba4b21d383331b1`.
The exact save-owned JAL word is `0x0C014113`.

### Exact-call causal control

Natural and call-NOP branches reload movie target 970 from identical full RAM,
register, cycle, frame, PC and SP state. The mutation changes exactly four
nonzero bytes at `0x800B3FFC..0x800B3FFF` to zero and the RPC acknowledges code
invalidation. SPU tracing is stopped/cleared before each load and re-armed only
after the branch origin and mutation are established.

Both branches advance to target 980 / emulator frame 327724 with equal movie
frame and SP. Two fresh iteration-34 replays retain natural PC `0x800104B8`,
NOP PC `0x8001046C`, and the NOP path one guest cycle earlier, so this is not
cycle-neutral timing proof. The full slot-17 record remains identical: action
20, active gate 195, class 128, position `[-173787,-38048,-261]`, velocity
`[-487,640,160]`, radius 100 and state 24. Actor/player/health/scene/phase state
also remains equal.

The natural SPU page contains 13 events and the NOP page 7. Natural-only early
key-ons occur at emulator frames 327715, 327716, 327718 and 327720 on voices
1/9/2/10, all at sample start `0x00009E10`; the NOP branch has no key-on before
shared frame 327722. This binds the exact -14 call to the bounded emulated SPU
sequence without making the call causal for the action-20 allocation itself.

### Scenario calibration and retained boundary

The first declarative control draft stopped at target 979, one update too early:
TTL was 196 rather than the generator endpoint's 195. It also incorrectly
treated frame 327722 as the first SPU event; the NOP page legitimately contains
two `completed` events at 327717 and another at 327721. That failed hypothesis
was corrected by targeting 980 and asserting the exact completed-event prefix
before the first key-on at 327722. The corrected fresh isolated scenario passed
19/19 assertions, verified pristine media and stopped only PID 1196846. Its
transient JSON report SHA-256 is
`1317c74125b63b5042069403adada143d45fb6ec93298421400b43681e7677c9`.

The source-fresh schema-v9 generator ran on config
`/tmp/abl-phase4-i27-thud-final-20472.bYyJl2`, port 20472, and stopped only PID
1188069. Artifact SHA-256 is
`86a96482ec1e127f3b81318a678504dd3506936859f5088415d5d7e5ae82bcd0`.
No fixture, report, audio, SPU RAM, capture, BIOS, token or media bytes are
committed.

The mechanics-baseline change invalidated the three source-dependent C16
context artifacts. Fresh isolated pristine replays regenerated Bonus-3 on port
20473, Stage-15 on 20474 and Thumper on 20475. Each generator reverified its
declared mounted/save media and stopped only its owned instance. The unchanged
bounded outcomes now hash to Bonus-3
`ddac4d0c16531d4c4d1f94ade57c76fe54a97816a31e69efefc0b9ce7886de02`,
Stage-15
`a1c88e0fe4a4c541efbc8717989f8e6cede88259dc27a011de1524c1a9481989`
and Thumper
`e9f4401ee8192d23c1eeebb8a6ff6bfd457733ee383bcd314e409451bcc48c76`.
This source-freshness replay does not extend C16, D16 or F03.

Adding `0x8009FD84` to the shared semantic registry intentionally invalidated
the Phase-3 lifetime completeness join. A fresh isolated Stage-1 transition
on pristine media regenerated 94 addressed entries: 49 scalar entries were
measured live and 45 non-scalars/constants were derived under the retained
classification rules. The actor-position table is resident RAM with pointer-
based writers, not immutable image data. Fresh config
`/tmp/abl-phase4-i27-semantic-lifetime-final-20476.QMZY6g`, port 20476, stopped
only owned PID 1277277. Artifact SHA-256 is
`db904f10aab218abb3ab08280f930ffc156166f4e86f32b4361e8f4438ff1456`.
The corresponding xref and ownership layers now retain an explicit method
limit and zero ownership gaps; no lifecycle behavior was inferred from the
sound-call pointer alone.

Because A07 embeds the Phase-3 xref artifact hash in its static census, the
xref extension also invalidated that otherwise complete campaign. A fresh
isolated pristine replay on port 20477 validated all 20 declared save headers,
reproduced all 19 responsive breadth anchors and exact controls, and stopped
only PID 1341105. The unchanged behavior is retained at SHA-256
`37001b491feab00011646617cce7cce65316bb6c0e5ba2ceff694953f212c4a4`.
This is source-freshness maintenance, not new A07 evidence.

This does not name a VAB/VAG asset, retain or decode a waveform, prove
host-speaker buffer drain, establish natural-hit frequency or complete E12.
D18/F09 therefore remain partial/open.

## Iteration 28 — all six arena rows have runtime identities and causal contact policy

The mandatory recursive inventory again found 110 Phase-4 movie-tree files and
147 broader files. There is no Thud recording under `movies/Phase4`; the sole
relevant centrally declared pair remains `thud_boss_movie.movie.json/.sav` with
movie SHA-256 `70e5988852315924e7eba7f8ba23632545ad329878e3e5b8a59de91955bcddaa`
and pristine save SHA-256
`789d9b601d592748af934c162513e91f1e63a8d2bbe8ce2cb3b9c16876b32a99`.
No new fixture was requested or imported.

Fresh read-only inspection resolved dynamic types 0..5 at `0x80096DA0` as six
distinct 58-point XYZ paths. Their six pass-2 object chains join to distinct
mesh pointers `0x8010B1AC/0x8010B890/0x8010C8A8/0x8010D118/0x8010DE40/
0x8010EB68`. Each mesh hash covers exactly the bytes up to the next pass-2 mesh
pointer. Only hashes, lengths and addresses are retained.

Four passive trace pairs reproduce natural contacts:

| row | targets | health | speed | ramp | post distance / threshold |
|---:|---:|---:|---:|---:|---:|
| 2 | 978/979 | 4→3 | -90→90 | 112→0 | 139469 / 160000 |
| 3 | 1098/1099 | 3→2 | 144→-144 | 100→0 | 468282 / 490000 |
| 4 | 1470/1471 | 3→2 | -110→110 | 104→0 | 420045 / 490000 |
| 0 | 3124/3125 | 4→3 | -100→100 | 92→0 | 463089 / 490000 |

Every passive trace is cycle-neutral and complete. Rows 1 and 5 never enter
their natural thresholds in this movie. Matched one-u32 branches therefore
change row 1 threshold 250000→700000 around distance 607965 and row 5 threshold
490000→1000000 around distance 916961. Before each write the branches have
identical full RAM, registers, frame, cycle, PC and SP. The mutation alone
clears the selected ramp, negates speed and lowers health by one at equal
endpoint frames with identical player/object positions. Row 5 ends at equal
cycle with distinct PCs; two fresh iteration-34 replays place row 1 one cycle
later at the same PC. This falsifies
the hypothesis that rows 1/5 have different contact law while preserving the
negative-natural observation.

Five additional passive traces retain row-loop cumulative counts
11226/11448/11694/11712/12120 at targets 3742/3816/3897/3903/4042. The loop
continues after counter 8 and across the measured defeat/retirement/exit suffix.
The counts do not reveal a distinct objective-completion request, so that claim
remains open.

The source-fresh command was:

```text
python3 tools/phase4_thud_arena.py --port 20488 --token '<redacted>' --config-dir /tmp/abl-phase4-i28-thud-arena-final-20488.FUyxlW --instance-state recreated
```

It produced `analysis/phase4_thud_arena.json` SHA-256
`2e38296b80f69a201fa16db8c904550b992af45c230d6f7335d450daf70bf79c`,
reverified pristine mounted/save media and stopped only owned PID 1552794.
`pytest -q tests/test_phase4_thud_arena.py` passed 9/9, including four explicit
falsification mutations. The natural, row-1 and row-5 declarative scenarios
passed 25/25, 9/9 and 9/9 assertions. Their transient JSON hashes are
`ef2b1e809310d2f12e39a1a224c78b3ab903455628c09a1ee1dc3244c5376e5c`,
`16e51bf6d470c2a8b75672a758c585e9ccb2cfdb88170e5af95726e9d6cf5508`
and `d610da08eef5f6d447bc988a6380522a7a851502065be1fde7d32cc8066668e9`;
all three scenario runners report successful PID-owned cleanup. No movie, save,
mesh, capture, disc, BIOS or token bytes are retained.

## Iteration 29 — exact counter-8 completion request is causal

The mandatory recursive inventory again found 110 files under `movies/Phase4`
and 147 files in the broader movie tree. No Thud recording exists in the Phase-4
subtree; the sole relevant centrally declared pair remains the root
`thud_boss_movie.movie.json/.sav` fixture with SHA-256
`70e5988852315924e7eba7f8ba23632545ad329878e3e5b8a59de91955bcddaa` /
`789d9b601d592748af934c162513e91f1e63a8d2bbe8ce2cb3b9c16876b32a99`.
No new fixture was requested, imported or retained.

Passive cycle-neutral traces bracket the eighth reset. Target 3739 / playback
3738 has scene/master/fade/counter/HP `14/0/0/7/48`; target 3742 / playback
3741 has `14/1/149/8/50`. Exact interpreter-only writer attribution identifies
save-owned `0x800B3E84` (`sh v0,0x23a0(at)`, 0→1) and paired
`0x800B3E90` (`sh v0,0x2470(at)`, 0→150). The containing 252-byte /
63-instruction runtime slice hashes to
`8ecf4b069584326f0ecc30acd387d168b34a355e618d5ff20c2a5c0c3dcfe53e`.

Matched branches reset to target 3739 with identical full RAM, registers,
emulator/movie frame, cycle, PC, SP, actor and player state. NOPing only the
four bytes at `0x800B3E84`, with acknowledged code invalidation, preserves
counter eight, fade 149, actor HP zero, flags `0x0055`, live-slot zero and
player/actor positions. The natural branch later reaches scene/master `0/1`;
the suppressed branch remains `14/0`. This falsifies fade-alone and
retirement-alone explanations and binds the master store as the causal Bug Bar
objective-completion request into resident scene flow. It does not assign a
global meaning to master state 1 or close either target row.

The source-fresh command was:

```text
python3 tools/phase4_thud_completion.py --port 20504 --token '<redacted-token>' --config-dir /tmp/abl-phase4-i29-thud-completion-settled-20504 --instance-state recreated
```

It produced `analysis/phase4_thud_completion.json` SHA-256
`fb086f2f1a3cc4760916cda337f6f01381d7b0b2aa74a825a34f858477c9fb13`,
reverified the inspected save and mounted pristine `SCUS-94288` CUE/BIN, and
stopped only owned PID 1855209. Before that settled replay, the central fixture
declaration refresh required a source-fresh arena replay. It preserved all six
row outcomes, produced arena artifact SHA-256
`d7db834ae0c3a83b55dfb1c217fc7bb75d9b1111d6e44f3ed9b4898eb3411408`
and stopped only owned PID 1855019. The low-level completion guard passes 7/7
tests.

The independent declarative scenario
`pristine_thud_completion_request_control.yaml` ran in fresh config
`/tmp/abl-ps1-scenario-jkkd48_3` on port 43583. It passed 20/20 assertions,
including explicit code invalidation and preserved fade/retirement with scene
14 retained, then stopped only owned PID 1796353. Its transient JSON report
SHA-256 is
`62bf0ee3609f5d20e0162170502bd17def57936e4628dc32f5d502b820e9ecac`.
No report, movie, save, disc, BIOS, token or capture bytes are committed.

## Iteration-35 fixture-manifest refresh

After the C15 fixture-consumer addition changed the central manifest pin, every
manifest-dependent Thud artifact was replayed in dependency order from fresh
isolated profiles. The root had no such dependency and stayed source-fresh.
Their
current SHA-256 values are root
`698fbd94fa10d9db1f2542a1fb462e12b7007a5c16858ac1fa4bc109f56d33ab`,
arena `7d8f0b99565004ec66081257ca74c3e30bb5aedb6bace2d5797733c709d7b74f`,
volley `9f0eed6474c3d71a1f0e0b6d43b8570fadaa405aae84a0910ae10a4e3496a75a`,
completion `363926f9248f4a88ba0ec7cca6092cd6d69485a4f344bd903a266d728cb2eaf5`
and row-4 C16
`0e0bb6730a301e2964a5440961172288392f04d7eb759d8b80394e993232e4c8`.
Every refreshed artifact records pristine mounted/save media verification and
owned-PID cleanup. Arena, volley, completion and row-4 C16 used ports
20622/20623/20624/20625 and stopped only PIDs
3198921/3199037/3199150/3199261.

The final volley run initially rejected its previous -1-cycle expectation while
preserving all gameplay state. Two more independent fresh-profile audits
reproduced the same result: changing only derived countdown 9→6 selects action
9 instead of action 20 at an endpoint equal in emulator frame, movie frame,
cycle, PC and SP. The retained control now requires exact zero cycle delta; this
is a strengthened reproduced guard, not a relaxed timing claim.

## Ratchet continuation iteration 1 — arena endpoint refresh

Two fresh isolated arena replays, using the default and movie-replay profiles,
both rejected the iteration-34 row-1 endpoint relation in the same way. The
control and one-u32 threshold mutation now end at equal cycle with distinct
PCs, matching row 5; all causal leaves remain unchanged: equal full-machine
origins, equal endpoint frames, identical player/object positions, threshold
250000→700000, health 4→3, ramp 96→0 and speed 120→-120. The generator now
requires this exact twice-reproduced endpoint relation.

The same two-profile check on the countdown-selected reward branch reproduced
the earlier one-cycle relation, not iteration 35's zero-cycle endpoint. Both
runs retain equal emulator/movie frame, PC and SP, with mutation exactly one
cycle earlier. The generator now requires that twice-reproduced relation while
preserving the identical full-machine origin and single u32 countdown write.

The root post-restore countdown-zero control independently observed the same
sign correction: after an identical full-machine target-970 origin, the
mutation remained at the same frame/PC/SP but ended exactly one cycle earlier,
while still suppressing only the Thud-owned action-20 allocation. A second
source-fresh root replay passed that boundary but then rejected the later
sound-control endpoint: typed gameplay state matched while cycle, RAM and
register digests did not. No root artifact was written, so its retained exact
relations remain authoritative pending a focused debugger endpoint diagnosis.

## Next experiment

Use the same movie to bind another distinct attack variant. Resolve named arena
visual/GPU ownership separately from the complete six-row runtime
path/model/contact policy and the exact objective-completion request. Leave
named audio-asset/waveform and host-lifecycle breadth to E12 unless it becomes
a direct Thud dependency.
