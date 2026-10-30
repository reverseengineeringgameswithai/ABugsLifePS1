---
kind: campaign
id: phase4_thud_bug_bar
phase: 4
rows: [D18_thud, F09_bug_bar]
family: bosses_special_objectives
status: active
evidence: [analysis/phase4_thud_defeat.json, analysis/phase4_thud_arena.json, analysis/phase4_thud_completion.json, analysis/phase4_thud_volley.json, config/phase4_thud.yaml]
---

# Game Solving Campaign — Thud Bug Bar

## Scope and exit decision

This campaign owns Thud's attack/phase and damage policy, natural defeat,
rolling-arena transformation, objective/scene exit, retry/persistence and fight
breadth. It consumes but does not inherit E07 event-VM, E02 collision, E08
mover/catalog, E12 audio, E13 HUD or E16 loading completion.

Status is **active / incomplete**. One existing centrally pinned pristine
recording plus a matched Square-cleared branch now directly reproduce one
player-projectile launch, one Thud-owned action-20 contact-object launch, eight
natural action-2/class-0 HP 50 → 48 → 50 cycles, six distinct rolling-arena
path/model joins and all six row-contact transitions, phase counter 0 → 8,
post-counter-8 arena execution, one separate actor path, later
HP 50 → 0, persistent retirement and scene 14 → 0. The action-20 derived-
countdown gate, boulder row-4 threshold, reset-owner front-half guards and path-
coordinate/actor-target join are causal. The action-20 record's natural
miss/retirement, one-field player-proximity grain effect and textured-billboard
presentation are now causal too. An exact-call NOP also binds its actor-
positioned -14 `play_sound` request to four early `0x00009E10` SPU key-ons
without removing action 20. Named sound-asset/waveform identity, host drain,
natural-hit frequency, other attacks, damage powers, named arena visual/GPU
ownership, initialization, retry, persistence, breadth and failures remain
open. The exact counter-8 completion request is now separately causal:
save-owned `0x800B3E84/0x800B3E90` request master state 1/fade 150, and
suppressing only the master store preserves counter eight and retirement while
preventing scene 14 from unloading.

The same recording now also binds seven exact ten-item reward volleys: 63
general action-20 paths, seven countdown-five action-9 health-leaf paths, 14
natural resident grain increments and four natural action-9 true-health
increments. At the first cycle-neutral 1432/1433 boundary, slot 47 action 9
retains position/radius/state while TTL changes 62→1 and health rises 2→3 through
exact resident store `0x80058890`. A one-field countdown 9→6 control changes the
next slot-17 action 20→9 from an identical origin. Universal action-9 collection/
drop rates, the full health domain and other attack sources remain open.

## Retained frontier

- Oracle: `thud_boss_movie.movie.json/.sav`, centrally hash-pinned, inspected
  before load, and replayed only on hash-verified pristine mounted media.
- Actor: fixed pool slot 0 / id 36 at `0x8009FD80`, HP `+0x6E`, flags `+0x5C`,
  X/Z motion targets `+0x28/+0x34`, VM IP `+0x70`, callback `+0x7C`, source
  `+0x80`, live slot `0x80090748`; `+0x30` remains unknown.
- Launch: targets 896/915 and allocator stores `0x8005A1D8/0x8005A1E4/
  0x8005A270` bind one action-2 projectile to player-throw caller `0x8004724C`.
- Input control: clearing only Square in source frames 896..917 suppresses the
  allocation, first HP decrement and first counter increment from an exactly
  aligned target-896 boundary; no derivative movie is retained.
- Thud-owned launch: passive targets 970/971 change slot 17 at `0x800B10D0`
  from action/TTL/class 1/0/0 to 20/200/128 while cumulative call counts add
  exactly one at save-owned `0x800B3FF0` and allocator `0x8005A0E0`.
- Attack control: full-RAM/register/cycle-aligned target-970 branches change
  only derived countdown `0x800B4CB4` from 9 to zero; the next equal
  movie/emulator frame retains 1/0/0 instead of allocating 20/200/128. The
  differing branch path is one cycle later and is not equal-cycle timing proof.
- Action-20 natural lifecycle: passive targets 972/973/1021/1023 retain action
  20, signed radius 100 and state 24 while active gate changes
  200→199→175→0; grain remains 0 and player health remains 4.
- Action-20 effect control: matched target-972 branches change only signed
  radius_add `0x800B10F8` from 100 to 6000 (two RAM bytes). The next equal
  movie/emulator frame changes grain 0→1, active gate 200→1 and state 24→16 at
  unchanged health. Fresh iteration-34 replay retains the mutation one cycle
  later at PC `0x800104B8` versus control PC `0x800198F0`; health and frame
  remain equal.
- Effect attribution: resident dispatch `0x800589B8` calls grain handler
  `0x80054EAC`; exact stores `0x80054F9C/0x800589E0/0x800589E4` write
  grain/state/active, followed by native bookkeeping. The pristine dispatch,
  common-tail and grain-writer slices are independently hash-pinned.
- Visual control: matched target-970 branches change only derived countdown
  `0x800B4CB4` from 9 to zero, then stop at exact movie target 980 with equal
  emulator frame, cycle and SP. The source-suppressed branch has no action-20
  record; the natural branch changes exactly 593 framebuffer pixels in one
  bounding box `(449,159,28,35)`. No framebuffer bytes are retained.
- Draw attribution: the natural changed pixel picks a textured opaque GP0(2C)
  quad from exact DMA/RAM source `0x001CF3D4`, 4bpp texture page `(512,0)` and
  CLUT `(880,221)`. The 656-byte pristine resident renderer
  `0x80014844..0x80014AD4` reads slot 17 twice and emits the picked packet.
  All 118 access events and the packet's 16 writes are complete; record `+0x34`
  is the command/color word, while ordering depth and table link are computed
  by the renderer.
- Launch sound: save-owned `0x800B3FFC` calls resident `play_sound`
  `0x8005044C` with signed cue -14 and actor-position context `0x8009FD84`.
  Matched target-970 branches change only that JAL to a NOP, preserve the full
  slot-17 record/gameplay endpoint at target 980 and change the bounded SPU page
  13→7. Natural-only early key-ons at frames 327715/16/18/20 all start at
  `0x00009E10`; this does not name an asset, waveform or host-drain event.
- Continuation identity: `0x800B3ED4..0x800B4004` is an exact 308-byte /
  77-instruction save-owned slice with SHA-256 `10992dee6815d74e6b89109980f16d6c60f0230d94f52f0730b7e217d30badba`.
- Transient boundaries: targets 964–967 bind HP 50 → 48 → 48 → 50,
  contact-pool slot 26 action 2/class 0 and overlay target 50.
- Transient writers: resident `0x800590E4` stores the -2 decrement;
  save-owned `0x800B3ED0` restores from target `0x800B4C70`.
- Causal controls: class 0 → 127 changes next HP 48 → 46; target 50 → 49
  changes restored HP 50 → 49 at equal movie/emulator frame and cycle.
- Rolling-boulder contact: passive targets 1466/1472 retain player health 3→2.
  Save-owned `0x800B4814..0x800B4B20` transforms six object rows; only row 4
  has squared distance 454805 below threshold 490000 at `0x800B4C1C`, then
  `0x800B4AE0` reaches resident health store `0x8004A888`. Zeroing only that
  threshold prevents the decrement at an exact movie-target endpoint with
  equal frame, cycle, PC, SP and player position.
- Six-row arena census: dynamic types 0..5 each provide one distinct 58-point
  path. Their pass-2 transform chains join to six distinct contiguous mesh
  slices, each bounded by the next mesh pointer and retained only as address,
  length and SHA-256 metadata. This is runtime model identity, not a visual name
  or GPU-owner claim.
- Natural row contacts: passive cycle-neutral pairs bind rows 2, 3, 4 and 0 at
  targets 978/979, 1098/1099, 1470/1471 and 3124/3125. Each selected row is the
  sole inside-threshold row, clears its ramp, negates its angular increment and
  lowers health by one.
- Negative-row controls: the recording never naturally admits rows 1 or 5.
  Fresh branches change only row 1 threshold 250000→700000 around measured
  distance 607965 and row 5 threshold 490000→1000000 around distance 916961.
  Each mutation executes the same ramp-clear/reversal/one-health transition at
  equal endpoint frames with identical player/object positions. Row 5 ends at
  equal cycle with distinct PCs; two fresh iteration-34 runs reproduce row 1
  one cycle later at the same PC. Full RAM, registers, frame, cycle, PC and SP
  match before each write.
- Counter-8 arena linkage: passive target counts for row-loop PC `0x800B48A4`
  are 11226/11448/11694/11712/12120 at targets
  3742/3816/3897/3903/4042. The loop therefore continues after counter 8 and
  through the measured defeat/retirement/scene-exit suffix. Counts do not by
  themselves name a geometry-completion request.
- Repeated reset boundaries: damage targets 965/1311/1711/2125/2523/2939/
  3309/3739 and restore targets 967/1313/1713/2127/2525/2941/3311/3741
  retain eight passive cycle-neutral HP 48 → 50 pairs and counter 0 → 8.
- Eighth restore: master state 1, heading 32 and motion timer 149.
- Completion request: the exact save-owned 252-byte slice at
  `0x800B3D9C` hashes to
  `8ecf4b069584326f0ecc30acd387d168b34a355e618d5ff20c2a5c0c3dcfe53e`.
  Counter store/gate `0x800B3DB0/0x800B3DB4` select master-state store
  `0x800B3E84` and paired fade store `0x800B3E90` on the eighth reset.
- Completion control: matched target-3739 branches begin with identical full
  RAM/register/cycle/PC/SP state. NOPing only `0x800B3E84` preserves counter 8,
  fade 149, HP zero, flags `0x0055`, live-slot zero and positions, but the
  natural scene/master `0/1` endpoint becomes `14/0` in the suppressed branch.
- Actor path: `0x800B43A8` decrements path coordinate `0x800B4CB0` by 2560;
  `0x800B43B8/BC` feed actor X/Z targets, and a +4096 mutation propagates
  exactly to both and final actor X without changing player XYZ or retirement.
  This is not rolling-arena geometry or completion proof.
- Reset controls: target=HP and signed HP<21 suppress reset; a non-sentinel
  arena value suppresses the counter; counter 7→8 selects the master-state
  transition; grain 41 changes the derived value 9→8; with shared timer-zero
  setup, master state 1 blocks the reset path.
- Natural boundaries: targets 3896, 3900, 3902 and 4041 bind active, HP-zero,
  retired and scene-exit states with passive cycle-neutral pairs.
- Writers: runtime `0x800B4528` sets HP zero; resident `0x8004D270` clears the
  active bit and `0x8004D43C` clears the live slot.
- VM: E07 fully decodes selector-19 `program_19`; it is a parking loop, not a
  complete Thud attack FSM.
- Scenarios: `tools/scenarios/duckstation/pristine_thud_natural_defeat.yaml`
  `tools/scenarios/duckstation/pristine_thud_action20_grain_control.yaml` and
  `tools/scenarios/duckstation/pristine_thud_action20_source_suppression.yaml`,
  plus the exact-call control
  `tools/scenarios/duckstation/pristine_thud_action20_sound_call_control.yaml`.
  The arena breadth is separately declarative in
  `pristine_thud_six_row_arena.yaml`, `pristine_thud_arena_row1_control.yaml`
  and `pristine_thud_arena_row5_control.yaml`; the request control is
  `pristine_thud_completion_request_control.yaml`.
  The reward variant is separately declarative in
  `pristine_thud_reward_variant_control.yaml`.

## Identity and method boundaries

The saved runtime Region-A image does not hash-match either staged LEVEL08
candidate. The exact 36-byte writer slice and 612-byte/153-instruction reset-
owner front half, the next 308-byte/77-instruction attack continuation, plus the
784-byte/196-instruction arena transform/collision block are identified; any
overlay hook must be qualified by that runtime identity. Other continuation
paths remain unproved, so the retained slices are not mislabeled as the complete
overlay policy. Access-log and point-
trace rows are instruction attribution only because they force the interpreter.
Passive trace pairs carry fixed-frame behavior.

`0x8005905C` is an inner block within the resident contact-vs-actor handler,
not a standalone entry. The launch belongs to the player throw dispatcher; its
sampled selector does not establish berry color or a boss attack. Earlier
active-clear/re-arm pulses are not retirement. Persistent retirement is the
final clear immediately before live-slot zero.

## Open work packages

- Widen action-9 collection/drop and health-domain breadth, cover other attack sources and
  continue unsampled policy after `0x800B4004`. Named sound-asset/waveform identity and
  host-audio lifecycle remain an independent E12 handoff if needed.
- Reproduce full damage powers. Resolve named arena visual/GPU ownership and
  any remaining presentation dependencies separately from the now-complete
  six-row runtime path/model/contact policy, actor path and exact counter-8
  objective-completion request.
- Reproduce initialization, re-engagement, retry/checkpoint, scene reload and
  save/load behavior.
- Cover representative damage variants and exceptional/failure paths.

## Handoff

Reuse the same recording to bind another attack source or health/drop boundary
before considering a new fixture. Do not promote D18 or F09 until every
open work package has direct behavioral evidence.

Iteration 32 extends the source-fresh reward-volley artifact to schema 2,
SHA-256 `bbdb01df6ba4e925b7eb54bce993c10b0fe4f9e1a45005a68ee45ab5075cc287`.
The final isolated replay used config
`/tmp/abl-phase4-i32-thud-action9-final-20542`, port 20542, reverified pristine
mounted/save media and stopped only owned PID 2198546. Cumulative tracing now
counts four natural action-9 handler/store executions. The first exact passive
1432/1433 boundary raises true health 2→3 while slot-47 action/position/radius/
state remain stable and TTL changes 62→1. The hash-pinned pristine resident
handler identifies exact health store `0x80058890`.

Focused volley guards pass 8/8. The independent read-only action-9 scenario
passes 14/14 assertions, stops only PID 2198781 and leaves its transient report
under `/tmp` with SHA-256
`6604de6923dcfae7c20cb3f0f05977070e421ac18d5c750213669ba89208c776`.
The baseline correction invalidated three C16 source pins; fresh pristine
replays preserved Bonus-3, Stage-15 boss and Thumper outcomes at artifact
SHA-256 `a0a22f104c68d00c8891f7af06def52d7d2beab7f0ac5933b7cdc9674c21dbf7`,
`854c263c7435c792176aae4ac4322fe8b0d0d97d970a5a00614e3f01d3ec21e3`
and `87e665b1a57ba8efdabb0b8563033186ed89917cab7831de52a553974ace803a`;
only their owned PIDs 2217541/2217676/2217822 were stopped. D18/F09 remain
partial because universal drop/collection policy, health breadth, other attacks,
retry/persistence and exceptional paths remain open.

Iteration 30 adds source-fresh reward-volley artifact SHA-256
`b5784018a113efea37701553e8ccd4f7ba8d431d905ecea8875b40958edba9b6`.
Fresh config `/tmp/abl-phase4-i30-thud-volley-refresh-20535`, port 20535,
reverified pristine mounted/save media and stopped only owned PID 2134698.
Nine cycle-neutral cumulative traces bind 70 allocations across seven volleys,
with 63 general action-20 and seven special action-9 paths plus 14 natural grain
stores. The matched countdown control has exact -1 mutation-branch cycle delta,
not false cycle equality. Focused guards pass 6/6. The separate declarative
scenario passes 11/11 assertions and stops only PID 2079425; transient report
SHA-256 is
`ed54a78869bd2733106b01a0d29182d11bc460a5f0def1cff30cff77055e1468`.
No operator fixture or copyrighted byte is committed.
The central fixture-set refresh also required source-fresh arena/completion
replays; unchanged outcomes now hash to `de90fd4ce4d389b69c2c1810dcca66a444efe2c25f04ad303dabd3dbd72ca25b` /
`1cdd0dda7046bbb7291be2844121362c65fd0247b31fb14d15ac2fec5e450be4`,
and only their owned PIDs 2134401/2134554 were stopped.

Iteration 33's new C16 consumer changed the central fixture-manifest source
dependency. Fresh pristine arena, completion and volley replays preserve the
same outcomes at SHA-256
`c0b8eceab13b21a212fef2ae8b35857df197889ce2354915be3267053245eae2`,
`fc781289f4ccffd26bfff032dde1a59d997463cdb3c2d14b07069691e3cac86c`
and `f2e2d41fdfdb4f24e4d585775aec0b93c1a820f55f007ce5a07140a6369918eb`;
only owned PIDs 2424323/2424482/2424641 were stopped.

Iteration 27's source-fresh schema-v9 artifact SHA-256 is
`86a96482ec1e127f3b81318a678504dd3506936859f5088415d5d7e5ae82bcd0`.
The generator on fresh config `/tmp/abl-phase4-i27-thud-final-20472.bYyJl2`,
port 20472, reverified pristine mounted/save media, reproduced all low-level
predicates and stopped only owned PID 1188069. The new exact-call declarative
scenario passed 19/19 assertions and stopped only owned PID 1196846; its
transient JSON report SHA-256 is
`1317c74125b63b5042069403adada143d45fb6ec93298421400b43681e7677c9`.
Previously retained independent pristine scenarios
passed 108/108 assertions across 30 natural phases, 16/16 across two grain-
control phases and 15/15 across three source-suppression phases; their transient
report hashes are `b8953d62e4518ca69fcbfc6b08008356374c2662bcc9999214d52fef5afb0c8b`,
`a26b82049c4591b5dcf257a6e28dbbb52f7c5eca8af869479204cdc2b58dd336`
and `127c26780dc02228f24cc9b05d0eeaa393b8d968e16bd8e0b20c334f6ffdaff7`.
The dependent shared-record probe also sampled all 42 strict-pristine anchors,
retained the new signed action/radius/state domains, and stopped only owned PID
722524 on the declared normal binary; artifact SHA-256 is
`39bbbe79b8c5fb83009459f9ce0a29de3a961a3feb866e561a76e44e251fe028`.
No movie, save, disc, BIOS, token or capture bytes are committed.

Iteration 28 adds the source-fresh arena artifact SHA-256
`2e38296b80f69a201fa16db8c904550b992af45c230d6f7335d450daf70bf79c`.
Fresh config `/tmp/abl-phase4-i28-thud-arena-final-20488.FUyxlW`, port 20488,
reverified pristine mounted/save media and stopped only owned PID 1552794.
The retained low-level guard reports no gaps. Three focused declarative
scenarios pass 25/25, 9/9 and 9/9 assertions for the four natural contacts and
two threshold-only controls. Their transient report hashes are
`ef2b1e809310d2f12e39a1a224c78b3ab903455628c09a1ee1dc3244c5376e5c`,
`16e51bf6d470c2a8b75672a758c585e9ccb2cfdb88170e5af95726e9d6cf5508`
and `d610da08eef5f6d447bc988a6380522a7a851502065be1fde7d32cc8066668e9`;
each stopped only its isolated owned PID. The source definitions contain no
recording or asset bytes.

Iteration 29 adds source-fresh completion artifact SHA-256
`fb086f2f1a3cc4760916cda337f6f01381d7b0b2aa74a825a34f858477c9fb13`.
Fresh config `/tmp/abl-phase4-i29-thud-completion-settled-20504`, port 20504,
reverified the pristine mounted/save media and stopped only owned PID 1855209.
The prerequisite source-fresh arena replay preserved all six row outcomes,
produced SHA-256
`d7db834ae0c3a83b55dfb1c217fc7bb75d9b1111d6e44f3ed9b4898eb3411408`
and stopped only owned PID 1855019.
Passive traces bind the counter 7→8, master 0→1 and fade 0→150 request; a
matched single-instruction suppression preserves fade, HP zero and retirement
but keeps scene 14 loaded at the natural exit boundary. Focused guards pass
7/7. The independent fresh-profile declarative scenario passes 20/20
assertions and stops only PID 1796353; transient report SHA-256 is
`62bf0ee3609f5d20e0162170502bd17def57936e4628dc32f5d502b820e9ecac`.
This closes the exact request boundary, not either row. No recording, save,
disc, BIOS, token, report or capture bytes are committed.

## Iteration 34 source-fresh reconciliation

The C16/F14 mechanics update invalidated retained source pins. Fresh pristine
arena, row-4 C16 and completion replays now hash to
`065eb18c59e735a9c2ecadeaeaa64f1d2b34b74432d11ea699d46d7722cd322d`,
`0968e3824edc263153a75e527cc66504059d477e651070f5d0c7738f35a6c0e1`
and `acfad40375df1db4a613e724dbd1cc76c9233c866de3bca4f9977a70745b6425`.
The arena replay retains identical full-machine branch origins and unchanged
contact outcomes. Its exact endpoint relation is row 5 at zero cycle delta with
distinct PCs and row 1 one cycle later at the same PC; incidental absolute PCs
at the RPC frame boundary remain raw evidence only. The final isolated configs
were `/tmp/abl-phase4-i34-refresh-thud-arena5.DktVMV`,
`/tmp/abl-phase4-i34-refresh-thud-boulder.UtVL90` and
`/tmp/abl-phase4-i34-refresh-thud-completion.s81YVY`; only owned PIDs
2745931/2746073/2746174 were stopped.

### Iteration-35 fixture-manifest refresh

Adding the C15 fixture consumers changed the central manifest source pin. The
manifest-dependent Thud artifacts were therefore regenerated in dependency
order from hash-verified pristine mounted/save media. Current
artifact SHA-256 values are root
`698fbd94fa10d9db1f2542a1fb462e12b7007a5c16858ac1fa4bc109f56d33ab`,
arena `7d8f0b99565004ec66081257ca74c3e30bb5aedb6bace2d5797733c709d7b74f`,
volley `9f0eed6474c3d71a1f0e0b6d43b8570fadaa405aae84a0910ae10a4e3496a75a`,
completion `363926f9248f4a88ba0ec7cca6092cd6d69485a4f344bd903a266d728cb2eaf5`
and row-4 C16
`0e0bb6730a301e2964a5440961172288392f04d7eb759d8b80394e993232e4c8`.
The final isolated configs were
`/tmp/abl-phase4-i35-arena-tracked-eF7jRY`,
`/tmp/abl-phase4-i35-volley-tracked-BUAGx4`,
`/tmp/abl-phase4-i35-completion-tracked-28yfcB` and
`/tmp/abl-phase4-i35-boulder-tracked-4vLicX`; only owned PIDs
3198921/3199037/3199150/3199261 were stopped. The root artifact had no manifest
dependency and remained source-fresh without a redundant live replay.

The matched countdown 9→6 variant control now reproduces full endpoint equality
in emulator frame, movie frame, cycle, PC and SP. Three fresh audit runs returned
the same zero cycle delta, so the retained generator and test require that stricter
relation. All attack, arena, reward, completion and death outcomes are unchanged;
this freshness correction closes no D18/F09 row.
