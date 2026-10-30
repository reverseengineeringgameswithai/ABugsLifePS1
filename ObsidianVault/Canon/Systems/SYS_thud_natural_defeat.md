---
kind: system
id: SYS_thud_natural_defeat
status: runtime_seen
confidence: confirmed
source_state: original_game
evidence: [analysis/phase4_thud_defeat.json, analysis/phase4_thud_arena.json, analysis/phase4_thud_completion.json, analysis/phase4_thud_volley.json, config/phase4_thud.yaml]
---

# Thud natural damage, restore, defeat and retirement

## Confirmed original-game interface

In scene 14 (`level08\level5b`, Stage 9 Bug Bar), fixed actor-pool slot 0 at
`0x8009FD80` is actor id 36. Its confirmed fields in the retained state are:

| Field | Address | Type | Active value | Retired value |
|---|---:|---:|---:|---:|
| actor id | `0x8009FD80` | `u32` | 36 | 36 (bytes persist) |
| flags | `0x8009FDDC` | `u16` | `0x4055` | `0x0055` |
| HP | `0x8009FDEE` | `s16` | 50 | 0 |
| VM IP | `0x8009FDF0` | `u32` | `0x800777A4/A6` | persistent bytes |
| callback | `0x8009FDFC` | `u32` | `0x8004A0F4` | persistent bytes |
| source | `0x8009FE00` | `u32` | `0x80094A38` | persistent bytes |
| live slot 0 | `0x80090748` | `u32` | `0x8009FD80` | 0 |

The natural pristine replay has these post-step `traceToFrame` boundaries:

- target 3896: scene 14, HP 50, flags `0x4055`, live slot present;
- target 3900: scene 14, HP 0, actor still live;
- target 3902: scene 14, flags `0x0055`, live slot 0;
- target 4041: scene 0, live slot remains 0.

Each boundary is a passive control/instrumented replay with identical RAM,
registers, cycles and frames. `traceToFrame` names the next input index, so the
displayed post-step `playback_index` is one less than the target.

## Recorded player-projectile launch

The same pinned replay naturally changes shared contact slot 26 from action 4
to action 2. At target 896 player throw windup/in-flight count is 6/2; at target
915 it is 9/3 and action 2 has TTL 99. Exact allocator stores are
`0x8005A1D8` (action 4→2), `0x8005A1E4` (TTL 100) and `0x8005A270`
(damage class 0). Allocator entry `0x8005A0E0` has return address
`0x80047254`, binding its caller to resident player-throw site `0x8004724C`.

Two in-memory movie branches are full-RAM/register/cycle equal at target 896.
Clearing only Square in source frames 896..917 leaves target 915 at windup 0,
in-flight count 2 and action 4, prevents HP 50→48 at target 965, and prevents
the first phase-counter increment at target 967. No derivative movie is
retained. This proves one recorded player projectile; the sampled selector does
not prove berry color, and this is not a Thud-owned attack.

## Post-restore Thud-owned contact-object launch

After the first restore, passive targets 970 and 971 retain derived countdown
9 → 8 while contact-pool slot 17 (`0x800B10D0`) changes action/TTL/class
1/0/0 → 20/200/128. Cumulative execution counts change by exactly one at
save-owned call `0x800B3FF0` and resident allocator entry `0x8005A0E0` across
that one-frame boundary. Both endpoints are cycle/RAM/register-neutral
`traceToFrame` pairs.

An exact interpreter-only attribution pass binds action store `0x8005A1D8`
(1 → 20), TTL store `0x8005A1E4` (200) and class store `0x8005A270` (128).
At `0x800B3FF0`, `s3` is the Thud actor `0x8009FD80`; allocator entry sees
return address `0x800B3FF8`. The containing save-owned continuation
`0x800B3ED4..0x800B4004` is 308 bytes / 77 instructions with SHA-256
`10992dee6815d74e6b89109980f16d6c60f0230d94f52f0730b7e217d30badba`.

Matched branches are full-RAM/register/cycle equal at target 970. Changing
only derived countdown `0x800B4CB4` from 9 to zero leaves the next equal
movie/emulator frame at action/TTL/class 1/0/0 instead of 20/200/128. The
branch paths differ by one cycle, so this intervention is causal suppression,
not equal-cycle timing evidence. These results prove one Thud-owned action-20
contact-object source/launch. They do not identify its visual, target, hit,
damage amount, completion effect or other attack variants; visual and launch-
sound evidence below are independent controls.

## Action-20 natural miss and native grain effect

The launched slot-17 record is action 20 with signed `s16` active gate, radius
addition and state at `+0x22/+0x28/+0x2C`. Passive targets 972, 973, 1021 and
1023 retain action 20, radius 100 and state 24 while the active gate changes
200 → 199 → 175 → 0. Grain stays zero and player health stays 4. This is one
natural miss/retirement path, not a universal hit-frequency claim.

Matched target-972 branches begin with identical full RAM, registers, cycle,
frame, PC, SP, actor, player and record state. Changing only signed
`radius_add` at `0x800B10F8` from 100 to 6000 changes exactly two RAM bytes and
makes the existing object pass its native player-proximity test on the next
frame. Grain changes 0 → 1, player health remains 4, active gate becomes 1 and
state becomes 16. The branch endpoints share movie/emulator frame; the changed
control flow reaches exact target 972 with equal cycle, PC and SP.

The resident action-20 dispatch entry `0x8001B5B8` selects `0x800589B8`, whose
common tail calls resident grain handler `0x80054EAC`. Exact decisive stores
are `0x80054F9C` for grain, `0x800589E0` for state 16 and `0x800589E4` for
active gate 1, followed by bookkeeping call `0x800589FC` with result -1 and
record pointer. Static pristine slice hashes and ten exact access events are
retained in `analysis/phase4_thud_defeat.json`. This confirms the bounded
player-proximity grain effect, not its sound presentation, damage,
natural-hit frequency, objective/completion meaning or other attack variants.

## Action-20 textured-billboard presentation

Two branches reload exact target 970 from the same pinned movie/state with full
RAM, register, cycle, frame, PC and SP equality. The only mutation writes
derived countdown `0x800B4CB4` from 9 to zero, suppressing the action-20 source.
At exact movie target 980 both branches have emulator frame 327724, cycle
185557984749 and equal SP. Their expected PCs differ because the named source
gate changes control flow. An in-memory framebuffer comparison changes exactly
593 of 488000 pixels, normalized score `0.0012151639344262295`, in one bounding
box `(449,159,28,35)`. No framebuffer or diff-image bytes are retained.

Picking one changed natural pixel identifies an opaque textured GP0(2C) quad,
command 44, from exact DMA/RAM source `0x001CF3D4`. Its screen rectangle is
20×13, UV rectangle is 16×16, texture is 4bpp page `(512,0)`, and CLUT is
`(880,221)`. The pristine resident slice `0x80014844..0x80014AD4` is 656 bytes
with SHA-256
`7fa7b409bac944db9fb8a779fe26d9965930b9ca986002f8e849875ff2e36a0e`.
Complete access attribution retains 102 record reads and 16 packet-window
writes without truncation; 22 of those reads are inside this renderer at frames
327716 and 327722. Action id 20 is read at `0x8001496C`. The exact first-packet
writes run from `0x80014A30` through `0x80014A6C`. Record `+0x34` supplies the
GP0 command/color word `0x2C808080`; the renderer computes ordering depth and
table link rather than reading them from that field. This binds the action-20
textured billboard, not natural-hit frequency, damage or completion. Launch
sound is separately bounded below.

## Action-20 launch sound request and SPU key-ons

In a separate ten-frame interpreter attribution window, save-owned call
`0x800B3FFC` executes once with `a0=0xFFFFFFF2` (signed cue -14) and Thud actor
`s3=0x8009FD80`. Resident `play_sound` entry `0x8005044C` receives that cue,
position context `a1=0x8009FD84`, and return address `0x800B4004`. The window
contains three total `play_sound` entries, so the exact negative cue and return
address distinguish this launch request from two unrelated cue-26 calls. It
does not enter positive-id `sfx_dispatch` `0x80050994` in the same window. The
pristine 940-byte resident `play_sound` slice has SHA-256
`ffd93c418662e743429c966f4080065688227dcee6b17aab0ba4b21d383331b1`.

Matched branches reload target 970 with exact full-RAM, register, cycle, frame,
PC and SP equality. The mutation replaces only the four nonzero bytes of the
`jal 0x8005044C` at `0x800B3FFC` with a NOP and receives explicit code-cache
invalidation. Both branches advance to target 980 / emulator frame 327724 and
retain the same complete slot-17 action-20 record, actor/player state, health,
scene, PC and SP. The NOP path takes one extra guest cycle, so this is causal
behavior evidence rather than cycle-neutral timing evidence.

SPU tracing is stopped before every state load and re-armed afterward. The
natural bounded page has 13 events; the call-NOP page has 7, both complete.
Natural-only early key-ons occur at frames 327715, 327716, 327718 and 327720,
all with sample start address `0x00009E10`; the NOP branch has no key-on before
the shared frame 327722. Therefore the exact -14 call causes this bounded
emulated key-on sequence without causing the action-20 allocation itself.

This does not name a sound asset, retain SPU/audio bytes, prove a waveform or
host-speaker buffer drain, establish natural-hit frequency, or complete the
general E12 audio campaign.

## Natural contact damage and overlay restore

The same pristine replay has four earlier passive, cycle-neutral boundaries:

| `traceToFrame` target | Thud HP | contact slot 26 action/class | overlay target `0x800B4C70` |
|---:|---:|---:|---:|
| 964 | 50 | 2 / 0 | 50 |
| 965 | 48 | 2 / 0 | 50 |
| 966 | 48 | 2 / 0 | 50 |
| 967 | 50 | 2 / 0 | 50 |

Contact slot 26 is the `0x38`-byte record at `0x800B12C8` in the shared pool.
Its `u8` action id is at `+0x20` and damage class at `+0x34`. The exact natural
damage writer is resident `0x800590E4` (`sh v0, 0x6e(s2)`), 50 → 48.
`0x8005905C` is an inner class-dispatch block in the resident `0x80058AF8`
contact-vs-actor handler, not a standalone function entry. Class 0 selects the
-2 branch.

Resident `0x80054A64` calls the save-owned runtime update at `0x800B3C70`.
That owner reads target `0x800B4C70`; `0x800B3ED0`
(`sh v0, 0x6e(s3)`) restores HP 48 → 50. The exact 612-byte runtime owner slice
has SHA-256
`6f01004b1528e9c2adac072c8afc9acb695637d0be3d4ffbb78061ed06b33574`.

Fresh equal-frame controls establish causation. Changing only contact class
0 → 127 changes the next-frame HP outcome 48 → 46. Changing only overlay
target 50 → 49 changes the equal-two-frame restored HP outcome 50 → 49. These
controls do not establish complete damage powers or boss attack policy.

## Rolling-boulder transform and player-damage contact

The same pinned replay has passive targets 1466 and 1472 with player health
3 and 2, respectively. Player position changes from
`[104318,1478,-20326]` to `[99005,-934,-18472]`, while Thud HP remains 50.
Both boundaries are cycle/RAM/register-neutral `traceToFrame` pairs.

An exact save-owned runtime block at `0x800B4814..0x800B4B20` contains 196
instructions / 784 bytes and has SHA-256
`4169c4691a2d31867a9d237d006d91a83b5d3a2d2485c8669f0fed3e3032218d`.
Its front loop calls `0x800292DC` for ten object rows. A second loop processes
six rows, calls byte-matched resident `pass2_object_transform_update`
`0x80029508`, then resident `collision_candidate_builder` `0x80037320`, and
compares squared player distance with row thresholds at `0x800B4C0C..20`.

At the natural contact frame only row 4 passes: squared distance 454805 is
below threshold 490000 at `0x800B4C1C`; every other row is outside its sampled
threshold. With raw player field `0x800A6592` zero, save-owned call
`0x800B4AE0` enters resident level-transition initiator `0x8004A700` with
`a3=0`. Its exact store `0x8004A888` writes player health 3 → 2.

The matched causal control reloads both branches at target 1466 with equal
full RAM, registers, cycle, frame, PC and SP. Changing only row-4 threshold
`0x800B4C1C` from 490000 to zero prevents the decrement: natural health ends
at 2, threshold-zero health ends at 3, and both endpoints have identical player
position, frame, cycle, PC and SP at deterministic target 1471. Transient,
uncommitted frame captures show a
large rolling boulder overlapping the player in this window. The visual supplies
context only; the row trace and threshold control carry code causality.

This proves one rolling-boulder transform/distance/damage contact. It does not
yet identify every arena row/model, link the block to counter-8 phase policy,
or establish complete geometry ownership, rolling policy or completion.

## Six-row arena path, model and contact policy

The later six-row census supersedes only that breadth boundary; the original
row-4 observation and zero-threshold control remain valid. Dynamic type table
`0x80096DA0` supplies types 0..5, each with 58 XYZ points. The six record hashes
are distinct. Each row then joins through the pass-2 object table published at
`0x80082338` to a distinct mesh pointer. Each mesh slice is bounded by the next
pass-2 mesh pointer; only pointer, byte length and SHA-256 metadata are retained.
This establishes exact runtime model inputs, not visual names, texture identity
or GPU ownership.

The common save-owned policy is exact:

- ramp state `0x800B4C78 + row*4` grows by two up to the signed cap at
  `0x800B4C00 + row*2`;
- phase `0x800B4C98 + row*4` advances by that ramp, its high byte selects one
  typed path point and its low byte interpolates to the next point;
- `0x800B49E0` calls resident pass-2 transform update and `0x800B4A04` calls
  the resident collision-candidate builder;
- `0x800B4A60` compares player XYZ shifted right five with the interpolated
  row position under thresholds 490000/250000/160000/490000/490000/490000;
- an admitted row with player raw field `0x800A6592 == 0` clears its ramp at
  `0x800B4A88`, negates its angular increment at `0x800B4AA8`, and the retained
  row reaches the common one-health transition through `0x800B4AE0`.

Rows 2, 3, 4 and 0 contact naturally. Their passive pairs respectively bind
health 4→3, 3→2, 3→2 and 4→3; ramp 112/100/104/92→0; and angular increment
-90→90, 144→-144, -110→110 and -100→100. At each post boundary the named row
is the only inside-threshold row.

Rows 1 and 5 are negative natural cases in this recording. Matched controls
increase only row 1 threshold 250000→700000 around squared distance 607965 and
row 5 threshold 490000→1000000 around distance 916961. Each branch begins with
equal full RAM, registers, frame, cycle, PC and SP. The mutation alone admits
the row, clears its 96/88 ramp, reverses 120→-120 / 128→-128, and lowers health
4→3 / 2→1. Endpoint frame and cycle plus player/object positions remain equal.

Cycle-neutral row-loop counts at targets 3742, 3816, 3897, 3903 and 4042 are
11226, 11448, 11694, 11712 and 12120. The six-row policy therefore continues
after counter 8 and through the measured defeat/retirement/scene-exit suffix.
Those counts alone do not identify an objective-completion request or prove
named visual/GPU ownership. The request is separately bound below by its exact
stores and a matched one-instruction control.

## Natural reset counter and phase-path transition

The same pristine replay contains eight passive HP 48 → 50 reset pairs:

| cycle | damage target | restore target | counter before/after | arena sentinel before | master after |
|---:|---:|---:|---:|---:|---:|
| 1 | 965 | 967 | 0 / 1 | `0xFFFD6E20` | 0 |
| 2 | 1311 | 1313 | 1 / 2 | `0x00026E20` | 0 |
| 3 | 1711 | 1713 | 2 / 3 | `0xFFFD6E20` | 0 |
| 4 | 2125 | 2127 | 3 / 4 | `0x00026E20` | 0 |
| 5 | 2523 | 2525 | 4 / 5 | `0xFFFD6E20` | 0 |
| 6 | 2939 | 2941 | 5 / 6 | `0x00026E20` | 0 |
| 7 | 3309 | 3311 | 6 / 7 | `0xFFFD6E20` | 0 |
| 8 | 3739 | 3741 | 7 / 8 | `0x00026E20` | 1 |

Every damage boundary has HP 48, target 50, derived grain value 0 and master
state 0. Every restore has HP 50. The first seven have derived value 9; the
eighth has counter 8, master state 1, phase path coordinate 156704, heading 32 and
motion timer 149. Natural grain values after the restores are
0/0/0/4/8/12/14/14.

The pinned 612-byte slice at `0x800B3C70` contains 153 exact instructions.
Disassembly plus branch-operand watches and matched controls bind this front-
half policy:

- target HP equal to actor HP exits without reset;
- signed actor HP below 21 exits without reset;
- only exact path sentinels `0xFFFD6E20` or `0x00026E20` increment the counter;
- incremented counter 8 selects master state 1, heading 32 and motion timer 149;
- the grain threshold is 40; changing grain 0 → 41 changes the downstream
  same-frame derived result 9 → 8;
- with phase timer zero in both branches, changing only master state 0 → 1
  blocks the scene-14 reset integration path.

Point execution watches and mutations force the interpreter and establish
operands/causality only. The passive pairs establish natural frame and cycle
behavior. The exact next 308 bytes after the restore bind one action-20 launch,
and the resident dispatch/handler bind its player-proximity grain effect; the
exact sound caller binds one negative-cue SPU sequence. Other continuation
paths, named audio identity/host drain, natural-hit frequency, named arena
visual/GPU ownership and other attack variants remain unproved. The exact
counter-8 request is separately reproduced below.

## Exact counter-8 objective-completion request

Passive cycle-neutral boundaries bracket the eighth reset. At target 3739 /
playback index 3738, scene/master/fade/counter/HP are `14/0/0/7/48`. At target
3742 / playback index 3741 they are `14/1/149/8/50`. Later passive targets
3903 and 4042 retain boss retirement in scene 14 and the downstream scene-0
exit respectively.

The exact save-owned slice `0x800B3D9C..0x800B3E98` is 252 bytes / 63
instructions with SHA-256
`8ecf4b069584326f0ecc30acd387d168b34a355e618d5ff20c2a5c0c3dcfe53e`.
Its counter store at `0x800B3DB0` is followed by the counter-8 branch at
`0x800B3DB4`. On the eighth path, `0x800B3E84` writes resident master state
0→1 and `0x800B3E90` writes fade timer 0→150; the next passive boundary sees
149 after the resident fade decrement. Interpreter access logging attributes
these stores but is not timing authority.

Matched branches begin at target 3739 with identical full RAM, registers,
emulator/movie frame, cycle, PC, SP, actor and player state. The mutation NOPs
only the four bytes at `0x800B3E84` with explicit code-cache invalidation. Both
branches still reach counter 8, fade 149, HP zero, flags `0x0055` and live-slot
zero with identical player/actor positions. At the natural scene-exit target,
the control is scene/master `0/1`, while the suppressed branch remains `14/0`.

Therefore the master-state store is the causal Bug Bar objective-completion
request into resident scene flow; the paired fade write is necessary context
but is not sufficient by itself in this control. Scene 0 is the downstream
unload outcome, not the request instruction. This does not assign one global
meaning to master state 1 or complete D18/F09 attack, lifecycle, breadth or
failure-path packages.

## Post-counter-8 actor path

Passive targets 3741/3815/3896 retain phase path coordinate
156704/61984/-40416 and actor positions `[121858,-39328,-1751]`,
`[102808,-39328,-3845]`, and `[532,-39328,-1551]`. Save-owned
`0x800B43A8` decrements the coordinate by 2560 per update;
`0x800B43B8/0x800B43BC` copy it to actor +0x28/+0x34. Resident readers
`0x8004CD6C/0x8004C928` consume those X/Z motion targets.

Changing only the coordinate by +4096 at target 3741 causes exact +4096 deltas
in both X/Z targets and final actor X at target 3896. Actor Y/Z, player XYZ,
heading and motion timer do not change. Both branches still retire at target
3902. Therefore +0x28/+0x34 are typed X/Z motion targets and `0x800B4CB0` is a
causal Thud phase path coordinate. Actor +0x30 remains unknown. This does not
identify rolling-arena geometry or the complete phase termination rule.

## Exact writers

A separate, re-armed access-log replay attributes the stores. This pass forces
the interpreter and is writer evidence only, not timing evidence.

- `0x800B4528`, `sh zero, 0x6e(s3)`: HP 50 → 0.
- `0x800B3E84`, `sh v0, 0x23a0(at)`: master state 0 → 1 on counter 8.
- `0x800B3E90`, `sh v0, 0x2470(at)`: paired fade timer 0 → 150.
- `0x8004D270`, `sh v0, 0x0(s1)`: persistent flags `0x4055` → `0x0055`.
- `0x8004D43C`, `sw zero, 0x748(at)`: live slot `0x8009FD80` → 0.

The mover makes earlier active-clear/re-arm pulses. The retained retirement
event is the last matching clear, at cycle 187213136945, immediately before the
live-slot zero at 187213145270. Treating the first pulse as retirement would be
incorrect.

## VM and overlay boundaries

E07 already fully decodes selector 19 / `program_19`. It contains five
instructions; `0x800777A6` is the confirmed `jump_back` to `0x800777A4`, not an
undecoded attack FSM. The parking loop does not establish the callback/overlay
policy that controls the complete fight.

The save-restored Region-A bytes at `0x800B39A0` hash to
`65ed1a05668fedd73050c03cde965b7eb75ab3354694e4c3394f165119e9384e`
over 3500 bytes and
`d08da1b843674c62d9c153b62cb2e90e0c9d9284a2f3260e4d61e0d68beae3d2`
over 4064 bytes. They match neither staged `LEVEL08/LEVEL.BIN` nor
`LEVEL08/LEVEL1.BIN`. Therefore `0x800B4528` is bound only to the exact
save-owned runtime identity. Its 36-byte slice at `0x800B4518` has SHA-256
`971ab8241ab58d147d4dc0b8c2548cda182195982cdcc6b6de84b81014dad177`.
The separately bound counter-8 request slice is likewise save-qualified and
must not be treated as staged provenance.

## Boundary and MOD rule

This proves one recorded player-projectile launch, one Thud-owned action-20
contact-object launch plus its bounded native grain effect, textured billboard
and negative-cue SPU key-on sequence plus natural miss/retirement path, all six
rolling-arena path/model joins and row-contact transitions, eight natural
action-2/class-0 decrements and target-field restores, the counter-8 actor path
and reset-owner front-half guards, the exact counter-8 master/fade objective-
completion request, then one natural Thud HP-zero, retirement and scene exit.
It does not prove berry color, named action-20 sound asset/waveform, host drain
or natural-hit frequency, other attack variants, a complete damage curve,
named arena visual/GPU ownership, retry, persistence, or complete D18/F09.

A MOD must qualify Region-A hooks by exact residency, preserve HP-zero before
active/live retirement, and provide explicit initialization, reset, slot reuse,
scene transition and persistence policy. Do not assign the five-instruction VM
parking loop ownership of the full fight.

## Natural reward-volley frequency and action-9 variant

The complete pinned pristine replay executes seven post-restore reward volleys.
Passive, cycle-neutral cumulative coverage reaches exactly 70 save-owned
allocator calls at `0x800B3FF0`: 63 execute general path `0x800B3F7C` and
seven execute countdown-five path `0x800B3F34`. Each volley therefore contains
nine general contacts and one special contact. The same replay executes
resident action-20 tail `0x800589B8` and grain store `0x80054F9C` 14 times;
grain reaches 14 and remains there through counter 8 and terminal playback.

At identical full-RAM/register/cycle/PC/SP target-970 origins, changing only
derived countdown `0x800B4CB4` from 9 to 6 makes the next native decrement equal
five. Slot 17 changes from action/TTL/state `20/200/24` to
`9/200/-42`; emulator/movie frame, PC and SP remain equal while the special
path uses one fewer cycle. The independently bound resident dispatch and
semantic C sources type action 20 as grain and action 9 as health leaf.

The same cumulative trace executes action-9 handler/store
`0x80058864/0x80058890` four times. The first exact passive boundary is target
1432→1433 (post-step movie index 1431→1432): player health rises 2→3 while
slot 47 remains action 9 at position `[126549,-348,-14770]`, radius 100 and
state 7, with TTL 62→1. Both endpoints are independently cycle/RAM/register-
neutral. The pristine 56-byte action-9 handler slice hashes to
`e89382b9e86e29907d3cee300e6c7b706884bd20f352f2ff217c06e6f799f849`;
its decisive load/increment/store words are retained in the artifact.

Thus the original game emits nine action-20 contacts and one action-9 health-
leaf contact in each recorded reset suffix, and naturally collects four of the
action-9 leaves in this recording. This closes one natural health-increment
effect, not a universal collection/drop rate, the full health domain, other
attack sources or complete D18/F09 policy.
