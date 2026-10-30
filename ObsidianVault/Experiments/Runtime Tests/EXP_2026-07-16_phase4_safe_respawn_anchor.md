---
kind: experiment
id: EXP_2026-07-16_phase4_safe_respawn_anchor
date: 2026-07-16
status: reproduced_partial
confidence: confirmed
source_state: original_game
evidence: [analysis/phase4_checkpoint_respawn.json, analysis/phase4_respawn_writer_catalog.json, analysis/phase4_respawn_row_provenance.json, analysis/phase4_e08_hazard_outcomes.json, analysis/phase4_c16_flight_death.json]
---

# Phase 4 — safe respawn anchor and scene-qualified reset paths

## Question

What supplies the LEVEL02 pit reset position: the continuously maintained
`player+0x50` tuple, a later owner, or an authored checkpoint?

## Provenance and fixture selection

The run first recursively inventoried 110 files under `movies/Phase4` and 147
under the broader operator movie tree. The existing pair was reused:

- movie SHA-256 `55c2bb7729ad4460b13a26d91b70f835cd370336dd58aecee05339467c4fc1b8`;
- save SHA-256 `91a201a98f3e172e7cbb0d6ef7f8ea007d25097da45ba4a65ef3fa2f6d3bb58f`;
- mounted pristine CUE SHA-1 `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5` and BIN SHA-1 `0bc1a29748d4bd608d076495d085e825574880d1`;
- serial `SCUS-94288`; state version 84; embedded state media matched the pristine CUE.

The DuckStation fork was revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; binary SHA-256
`c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`.
Every retained run used a fresh absolute `/tmp` config and an owned loopback
port/token. The successful generator stopped only its launcher-owned PID.

## Observation

Cycle-neutral `movie.traceToFrame` branches established:

- frame 0/56: live and safe XYZ `[507900,31787,503976]`, health/lives `3/5`;
- frame 100: live XYZ `[508614,39723,516886]`, safe XYZ unchanged;
- frame 156: live XYZ `[508193,153067,517418]`, safe XYZ unchanged,
  status bit `0x0010` set and health/lives `3/5`;
- frame 157: live and safe XYZ `[501696,30092,494016]`, status bit `0x0010`
  clear and health/lives `4/4`;
- frame 160: live XYZ `[501696,30215,494013]`, safe XYZ
  `[501696,30092,494016]`, health/lives `4/4`;
- frame 358: live and safe XYZ `[501696,30215,494013]`, health/lives `4/4`.

The natural frame-160 trace executes the retained airborne/fall,
`0x80054C90` updater and `0x8005B134` respawn regions. Replacing only input
frames 57–87 with the exact frame-zero neutral pad leaves health/lives `3/5`
and has zero respawn-handler hits. The broader airborne/fall region still has
1,790 hits, so it is not itself a death discriminator.

## Exact owner observation

The frame-157 passive trace covers overlay `0x800B3C54..0x800B3D78` and the
resident respawn handler. The overlay's 292 runtime bytes match only the
hash-verified pristine `LEVEL03/LEVEL.BIN` slice at file offset `0x2B4`
(SHA-256 `1fdeb0da151050edbde73a082b5951ae4326ec133979ca5bae2f0198bd8cfbf9`)
among staged BIN files. Its exact chain is:

- `0x800B3C64`: read shared status; bit `0x0010` gates selection;
- `0x800B3C7C`: read the scene-local table pointer at `0x80096DA4`;
- `0x800B3CAC/CC0`: scan candidate X/Z and choose minimum squared distance
  after the player and row coordinates are reduced to the `>>5` domain;
- `0x800B3D24/40`: store selected X/Z shifted left five to safe X/Z;
- `0x800B3D44/54`: query ground height, subtract 256 and store safe Y;
- `0x8005B1DC/E4/EC` then load safe XYZ, and
  `0x8005B29C/A4/AC` write live XYZ.

`transferLog.resolve` cannot map either the save-state-restored overlay address
or selected runtime table row back to a disc file. Byte equality pins the code
to pristine media, but the row table's authored file origin remains open.

## Inference

Static code proves an internal safe-anchor producer/consumer pair. The producer
is continuously gated and is not evidence of a discrete authored checkpoint.
The natural pit outcome and static code identify a candidate owner chain, but
causal source perturbation is required to distinguish execution from ownership.

## Causal controls

At movie frame 100, two transient suffix branches differed only at safe-anchor
word `0x800A6550` (`+4096`; the byte difference was exactly `0x800A6551`). Both
converged at frame 160 to full-RAM SHA-256
`51c97bedd7064defe99eedfdb39289b31c8c06705a37fac719770e920237a893`.

A second same-code pair NOPed the three continuous store instructions at
`0x80054E70/78/80` in both branches, then applied the same single-word anchor
mutation to one branch. The NOPs remained present after replay; both branches
converged to full-RAM SHA-256
`90c57100bc5b3fd70ed5379f366685d98fd0e23283a57091279c71f030b7029c`.

This rejects the hypothesis that the stable LEVEL02 pit postcondition is
determined solely by the frame-100 safe-anchor value or by a later execution of
those three continuous stores. It does not reject the static read in
`FUNC_8005B134`, which may affect an earlier transient boundary.

At frame 156 the scene-local runtime pointer is `0x8015E684` with 18 rows. Row 6
is nearest; raw X/Z are `15678/15438`, and X scales to 501696. A second transient
pair changes only row-6 X at `0x8015E6D0` from 15678 to 15806. The sole changed
RAM byte is `0x8015E6D0`. With identical one-frame input, control produces
safe/live `[501696,30092,494016]`; the branch produces
`[505792,30120,494016]`. Thus X changes by exactly `+4096`, Z and health/lives
are unchanged, and Y is independently ground-recomputed at the displaced X.
Both branches have the same 400 selector hits and 768 resident-handler hits,
including every exact store/load above, and both independently match their
uninstrumented RAM/register/cycle/frame result. This is the causal confirmation
that overlay `0x800B3C54` supplies the reset tuple consumed by `0x8005B134`.

## Iteration-12 contact-death causal join

After re-inventorying the same 110 Phase-4 and 147 broader movie-tree files, the
campaign reused the existing C16 Bug Bar pair rather than requesting another
recording. Movie SHA-256 is
`39fa618a0adccf39e4dc5cf23870456594c630a179af41e8ae732ff7e61b30bf`;
save SHA-256 is
`e9c7a3b6545dffc8bc5455317b43bc58a6a1a6012e393768b64d81e22e1c1592`.
Load-free inspection returned version 84, serial `SCUS-94288` and the same
hash-verified pristine mounted CUE/BIN. A transient state changed only lives
`0→1` at `0x800A65A0`, selecting ordinary respawn; all derivative states and
movies were deleted.

At source movie frame 350, scene 9 has health/lives `-1/1`, live XYZ
`[-27693,-116008,-162370]` and retained safe XYZ
`[-23491,-112966,-142999]`. Same-code suffix branches then differ only by safe
X `+4096`; the sole differing RAM byte is `0x800A6551`. At source frame 355,
control live/safe XYZ is `[-23491,-112966,-142999]`, while the mutation is
`[-19395,-112966,-142999]`. Both have scene 9 and health/lives `4/0`.

Each branch independently matches its uninstrumented RAM, registers, cycle and
frame. Their five-frame coverage is also identical: updater 50 hits / 25 PCs
(`d027b629…`), resident handler 974 / 173 (`951f06d5…`) and Bug Bar overlay
window 670 / 368 (`48132d08…`). Updater stores `0x80054E70/78/80` are absent;
resident loads `0x8005B1DC/E4/EC`, live stores `0x8005B29C/A4/AC`, health store
`0x8005B30C` and lives store `0x8005B348` are all present. Observation is the
exact position split; inference is retained-anchor ownership; the
single-variable proportional output is the causal confirmation.

The iteration-12 generator used config
`/tmp/abl-phase4-i12-c15-ledger-20035`, port 20035 and owned PID 1434769, which
it stopped through the exact launcher. Retained artifact SHA-256 is
`3a132c9325b3f328b61b961290f467edd7b98caa6fb5fb9695cf1ce848142d79`.
The new declarative scenario passed 18/18 assertions and validated the pinned
movie start state and embedded pristine media before load; the existing pit
scenario also passed 18/18 through the strengthened runner.

## Iteration-35 pit breadth

The mandatory recursive census again found 110 Phase-4 files and 147 files in
the broader movie tree. No dedicated scripted, setpiece or exceptional C15
death recording exists. Rather than force an unrelated filename into the
campaign or request duplicate operator work, this run selected the existing
centrally declared pit pairs whose recorded start states reproduce different
live scenes:

- scene-10 movie/save SHA-256
  `c049d9b8075f458f87301134a3cb9998137ae0a82fa5d8d5516dd05b69c99e24` /
  `959bf87da9deb91fbdb1633175aebefc9de329d5aa4d7ef9ce18df0f34bc6a06`;
- scene-4 movie/save SHA-256
  `a06c81943700db5bd4e570165d54b098e54c67644cb116fde826bf75db8fee99` /
  `9e2cee6d4847c758ad6bae1e396fd7de31830f5b55220e63719a50cc1806973a`.

Load-free inspection of both version-84 saves returned serial `SCUS-94288`
and embedded media matching the mounted hash-pinned pristine CUE/BIN. The
fresh retained generator used `/tmp/abl-phase4-i35-c15-tracked-teI7ak`, port
20620 and owned PID 3198723, then stopped that exact PID.

Observation: scene 10 changes from frame-144 live XYZ
`[-163392,111928,1157047]`, safe XYZ `[-103436,-4903,1209759]` and
health/lives `0/1` to frame-145 live/safe XYZ
`[-159648,3628,1182816]` and `4/0`. Scene 4 changes from frame-204 live XYZ
`[749740,121085,124853]`, safe XYZ `[744984,4861,139049]` and `4/6` to
frame-205 live/safe XYZ `[727892,9584,165941]` and `4/5`. Every passive
boundary matches its uninstrumented RAM, registers, cycle and frame, and no
trace is truncated.

Causal confirmation: at each pre-reset boundary, same-code branches differ
only by safe X `+4096`; the sole changed RAM byte is `0x800A6551`. One original
input frame later, both safe/live X deltas are zero. Control and mutation have
identical updater, resident-handler and scene-overlay-window coverage. The
continuous safe-XYZ stores `0x80054E70/78/80` are absent, while resident loads
`0x8005B1DC/E4/EC`, live stores `0x8005B29C/A4/AC`, health restore
`0x8005B30C` and lives decrement `0x8005B348` are present. Therefore each
scene-qualified transition path replaces the safe tuple before resident
consumption.

The sampled 292-byte runtime comparison windows have SHA-256 `52cb5a20…` in
scene 10 and `b88d820a…` in scene 4. Neither equals the separately pinned
LEVEL03 selector slice. Their exact transition writers remain open; the movie
filenames are not used as hazard or owner evidence. This supersedes the
iteration-12 retained artifact with
`analysis/phase4_checkpoint_respawn.json` SHA-256
`e8454f2860ff6defec1fd3ca207bc4a54a6d7c21b651c2f1f2a1520f3ff742de`.

The two minimal scenarios each passed 15/15 assertions after verifying mounted
and save media. Transient report SHA-256 values are
`9a63c93a25b2627e7a08428e7dd6a9fce2d23fba9f4a114584ea49d7e7dbde17`
(scene 10) and
`cfae91d5cd668af62b04302a20ff540b0b4261bc4feb5eaad24ee9772e0bdeb6`
(scene 4).

## Iteration-36 exact transition-writer attribution

The mandatory recursive census again found 110 Phase-4 and 147 broader movie
files, with no dedicated scripted, setpiece or exceptional C15 recording. The
same centrally pinned scene-10/scene-4 pairs were therefore replayed from their
declared, pristine-verified start saves; no new fixture was requested.

A static census first matched the exact runtime writers against every pinned
staged `LEVEL*/LEVEL.BIN`. Scene 10's 320-byte slice
`0x800B3ADC..0x800B3C1C` uniquely matches
`REBUILD/files/LEVEL10/LEVEL.BIN` offset `0x13C` (SHA-256 `97e72e5e…`).
Function-bounds analysis returns exact, unmerged bounds
`0x800B3ADC..0x800B3C18`. Scene 4's 124-byte slice
`0x800B3C5C..0x800B3CD8` uniquely matches
`REBUILD/files/LEVEL04/LEVEL.BIN` offset `0x2BC` (SHA-256 `8494bef9…`),
with exact unmerged bounds `0x800B3C5C..0x800B3CD4`.

Short post-anchor access logs are complete and nontruncated. Scene 10 records
four writes at emulator frame 86844: safe X at `0x800B3BAC`, temporary Y at
`0x800B3BBC`, Z at `0x800B3BC8`, and final ground-derived Y at `0x800B3BDC`.
The resulting tuple is `[-159648,3628,1182816]`; heading 3141 is preserved.
Scene 4 records five writes at emulator frame 149037: X at `0x800B3C94`, Z at
`0x800B3C9C`, temporary Y at `0x800B3CA8`, heading 2048 at `0x800B3CB0`, and
final ground-derived Y at `0x800B3CC4`. The resulting tuple is
`[727892,9584,165941]`.

This is exact writer attribution. It does not supersede the passive causal
result: access watches force the interpreter, while the iteration-35
cycle-neutral natural/control pairs prove behavior and timing. The fresh
retained generator used
`/tmp/abl-phase4-i36-c15-writers-final-20642`, port 20642 and owned PID 3368619,
then stopped that exact PID. Artifact schema is
`abl-phase4-checkpoint-respawn/2`; SHA-256 is
`b8c68225d7001b5900a4b275cd9a2c23a0a57eddc7995481a2b4996dcde1aca3`.

## Iteration-37 staged writer census

The mandatory recursive inventory again counted 110 files in
`movies/Phase4` and 147 in the broader movie tree. Its sorted inventory has
SHA-256 `389eccbce1fafc21c81cda4a8e6151a886cfb3fcdbe5167cd0599fb77a6f2cc2`;
the broader manifest has SHA-256
`ec0f2c51217e4591d1bce0f8b2e1e9a7cfb179609f8d4175a42f7bb50c1b78ee`.
There is still no dedicated scripted, setpiece or exceptional C15 recording,
so no unrelated recording was forced into the campaign and no new operator
fixture was requested.

The selected experiment is load-free and static. A deterministic generator
verifies every staged `LEVEL*/LEVEL.BIN` through the central pristine build
identity, conservatively propagates constants within bounded MIPS code, and
recognizes only direct absolute stores to safe X/Y/Z/heading. An exact expected
write ledger fails closed on any added, removed or changed store. Mutation
tests separately change a LEVEL06 store target and its source constant; each
mutation falsifies the expected ledger.

Observation: the 11-file census finds 21 direct writes in LEVEL03/04/06/08/10.
The known LEVEL03/04/10 slices join the existing live artifact exactly. Two
distinct static-only initializers are newly bounded: LEVEL06 function
`0x800B3AEC..0x800B3B94`, slice SHA-256 `33b21c83…`, writes fixed safe
X/Y/Z/heading `[35329,-85228,-154696,3063]`; LEVEL08 function
`0x800B3AE8..0x800B3B54`, slice SHA-256 `4b2e8bcc…`, writes fixed safe and
live tuple values `[-157682,5744,-12845,352]`. Repeated generation is
byte-identical. A source-fresh Phase-3 join bounds resident address-level
caller candidates at `0x8005484C/0x8005485C/0x8005B194` for entry
`0x800B3AEC` and `0x8005B1A4` for entry `0x800B3AE8`; reused Region-A
addressing prevents those sites from proving loaded-overlay activation. The
retained artifact SHA-256 is
`d38c1eec603d33614840de89ad2fcc716043094d7a3b64452e3a7cb2ae7790c6`.

Inference boundary: six files have no direct absolute safe-tuple store under
this scanner, but may still contain pointer-mediated or separately overlaid
writers. The two new functions have not been observed executing. Runtime
activation of the static caller candidates, authored-source ownership, denial policy and lifecycle
semantics remain open. This static census therefore widens the variant map but,
by itself, does not promote C15 coverage.

## Iteration-38 LEVEL06 runtime activation and causal field controls

The mandatory recursive inventory again found 110 Phase-4 and 147 broader
movie-tree files. Sorted path/size manifests had SHA-256
`389eccbce1fafc21c81cda4a8e6151a886cfb3fcdbe5167cd0599fb77a6f2cc2`
and `ec0f2c51217e4591d1bce0f8b2e1e9a7cfb179609f8d4175a42f7bb50c1b78ee`.
The selected existing pair was
`movies/Phase4/E10/hazard_ground_bird_LEVEL04.movie.json` (SHA-256
`7b985f296d7a74311488bb05d9715fa95e82dab17025d737098d53364792dd98`)
and its paired state (SHA-256
`ff1c5fb1a2779ebf82caed0fd1777b8549685becdbf6d24072d3f78dec91caf1`).
Its filename was treated only as a lead. The v3 movie declares 580 frames and
the version-84 state declares serial `SCUS-94288`; load-free inspection and
every transient reload were verified against the mounted pristine CUE/BIN
hashes above.

Passive cycle-neutral traces localize the first LEVEL06 initializer execution
between targets 487 and 488. Target 487 has zero initializer hits, scene 6,
health/lives `4/4` and safe XYZ `[93783,-83752,-134554]`. Target 488 has
42 hits at 42 distinct PCs with no truncation, safe XYZ/heading
`[35329,-85228,-154696,3063]`, health 4 and lives 3. At the exact entry,
PC/RA are `0x800B3AEC/0x8005B19C`, selector `v1=3`, and the calling word at
`0x8005B194` is `0x0C02CEBB`. The 168 loaded bytes exactly match the pinned
pristine LEVEL06 slice SHA-256 `33b21c83…`.

An attribution-only short interpreter run records exactly four writes:
`0x800B3B00→safe X`, `0x800B3B24→safe Y`, `0x800B3B30→safe heading`, and
`0x800B3B3C→safe Z`. Causality comes from a separate matched experiment. One
transient state was saved at the natural initializer entry, inspected before
every load, and used for five branches. Control writes the fixed tuple. NOPing
the X, Y or Z store preserves only that field's old value; changing the heading
immediate from `0x0BF7` to `0x0BF8` changes heading from 3063 to 3064. Every
branch begins with the same full-RAM hash and returns at the same
cycle/frame/PC/SP boundary. Code invalidation was reported for each four-byte
edit. The transient state was deleted before retention.

Static pristine bytes independently bind the native selector: the handler
bounds `scene-3` to eight entries; scene 6 selects the JAL above, scenes 5/7/9
select the common tail, and out-of-domain scenes also skip to that tail. This
establishes one scene-6 LEVEL06 ordinary-respawn activation and its direct field
effects. It does not establish hazard species/ownership, LEVEL08 activation,
authored row provenance, other death classes, persistence or a player-visible
checkpoint.

The shared artifact is `analysis/phase4_e08_hazard_outcomes.json`, SHA-256
`614e7c7d32e52b3cde87687aa9eb6748af4bf91ef24a70b315f5156eef11e5de`.
The natural scenario
`tools/scenarios/duckstation/pristine_scene6_level06_respawn_initializer.yaml`
passes all 16 assertions with scenario-owned PID cleanup. The source-dependent
C16 breadth artifact was refreshed to SHA-256
`af9fb1c5d3900b2eea00714d491f785f33d45151a1e5c7ecd553001069e0c01e`;
its five-path conclusion is unchanged.

## Iteration-39 LEVEL08 runtime activation and safe/live field controls

The mandatory recursive inventory again found 110 files under `movies/Phase4`
and 147 under the broader movie tree. The only broader scene-8 filename lead
loads a different scene, so it was not forced into this campaign. The existing
centrally declared `level_14.sav` anchor was reused instead: SHA-256
`6e56d8c4780851f85059b477186b5b1346e23ed7e8eac79a134192e03fef5f50`,
version 84, serial `SCUS-94288`, scene 8. Load-free inspection and every
transient reload matched the mounted hash-pinned pristine CUE/BIN.

The bounded setup changes health to 0, lives to 3, and both live/previous XYZ
mirrors to the same point beside corrected live actor slot 5. It changes no
actor field or code byte. At emulator frame 223793 the natural and one-byte
response-only branches have identical timing origins. The natural passive
180-frame trace reaches call `0x8005B1A4`, all 27 PCs from
`0x800B3AE8..0x800B3B50`, and the ordinary resident health/lives writers; its
endpoint has health/lives `4/2`. Changing only actor flag bit `0x0080` changes
one RAM byte, prevents the contact damage call and produces zero initializer or
respawn-handler hits, with the same endpoint frame/cycle/PC/SP and health/lives
`0/3`.

The loaded 108-byte initializer SHA-256 is
`4b2e8bccbcd42dcb056b267d66a35bb8b7dbfdf9171eccd1a914ff1f67b029c9`,
equal to pristine `LEVEL08/LEVEL.BIN` offset `0x148`. A later natural
recurrence supplies the exact resident call and entry boundary at emulator
frame 224132: call word `0x0C02CEBA`, PC/RA
`0x800B3AE8/0x8005B1AC`. Because cached execution-point instrumentation did
not catch the first passive occurrence, this later breakpoint is exact
attribution/causality evidence, not the first-respawn timing authority.

An attribution-only short interpreter capture records exactly seven writes:
safe X/Y/Z/heading at `0x800B3B08/10/18/20` and live X/Y/Z at
`0x800B3B28/30/38`. Control returns with safe tuple
`[-157682,5744,-12845,352]` and matching live XYZ. Three branches reload one
inspected transient entry state. Changing only the X source instruction from
`0x34A5980E` to `0x34A5A80E` changes safe/live X by `+4096`; changing only the
heading source from `0x24020160` to `0x24020161` changes safe heading from 352
to 353. All branches reverify mounted pristine media and return at the same
frame/cycle/PC/SP boundary. The state and runtime edits are deleted.

The retained artifact is `analysis/phase4_c16_flight_death.json`, SHA-256
`6bb941bedd420ed8a9c1e31bd959505c9053920521cf2904b38c115507ba3033`.
The declarative natural scenario
`tools/scenarios/duckstation/pristine_scene8_level08_respawn_initializer.yaml`
passes 18/18 assertions with scenario-owned cleanup. Execution watches were
excluded from the scenario because the interpreter boundary changes this full
replay; passive `movie.traceToFrame` remains the execution-activation proof.
This closes LEVEL08 runtime activation and direct field effects only. Authored
row activation/denial policy, indirect writers, persistence,
other death classes and remaining-stage breadth stay open.

## Iteration-40 authored LEVEL03 row provenance

The required pre-campaign inventory hashed 110 files under `movies/Phase4`
and 147 under the broader movie tree. The transient sorted SHA-256 manifests
are `/tmp/phase4-i40-movie-inventory.sha256` SHA-256
`a9b7df5925239b760f786b0e882628389c63e410b49a611daa040ed074a27452`
and `/tmp/phase4-i40-all-movie-inventory.sha256` SHA-256
`6ad2b874a9aca427d56660661fa27625d6409f59a3876b9423a9285ff201dc3c`.
No dedicated scripted, setpiece or exceptional C15 movie exists. The existing
centrally hash-pinned from-boot LEVEL02 recording was selected because it
reaches scene 3 without a save-state source gap; its filename was only a lead.

Observation: a fresh CachedInterpreter/card-seeded replay advances from movie
frame 6300/scene 0/cycle `3567068715` to frame 7000/scene 3/cycle
`3963411358`, with playback reproducible and nontruncated. Mounted media before
and after matches pristine CUE SHA-1 `25adb139…` and BIN SHA-1 `0bc1a297…`.
At the scene-3 endpoint, `[0x80082498] = 0x8015E22C` and
`[0x80096DA4] = 0x8015E684`. The pointed record is type 1/count 18; its
220-byte SHA-256 is `6adbdd60…` and its 224-byte record-plus-next-header
SHA-256 is `fec6e92f…`. Row 6 at `0x8015E6D0` is raw XYZ
`[15678,0,15438]`, SHA-256 `88bb66f2…`.

Static ownership: all 21 centrally pinned staged `LEVEL*/*.DAT` files were
parsed with the exact shipping size rules. Only `LEVEL03/LEVEL.DAT` offset
`0x458` has the live 224-byte hash; row 6 is file offset `0x4A4`. The
byte-matched parser `0x8001CDC0..0x8001D3CC` has SHA-256 `7ffcc86c…` and its
exact `0x8001CEDC` store writes non-negative type pointers into
`0x80096DA0 + type*4`. Inference: `0x80096DA4` is shared DAT type-table slot 1
and the live coordinate rows are authored in the pinned LEVEL03 asset, not a
separately owned respawn table. Causal confirmation remains the iteration-11
single-variable row-6 raw-X `+128` branch, which changed reset safe/live X by
`+4096` under identical selector/handler coverage.

Two diagnostic methods were rejected rather than promoted. A transfer log
armed before the scene load retained 31,575 nontruncated events but zero
filtered CD-ROM DMA events into the target heap band; `transferLog.resolve`
returned no candidates for the table or edge rows. Its transient report is
`/tmp/phase4-i40-c15-provenance-explore3.json` SHA-256
`8f4a53d00c9fc7fae52afb3e28d0060e1ac4bbca706cbb03b2776f5160b5ba73`.
A pointer-slot access watch forced interpreter execution, ended one cycle away
from the passive replay, left the pointer zero, and captured only four BIOS
zeroing writes. It is not source or behavioral evidence; transient report
`/tmp/phase4-i40-c15-pointer-writer.json` SHA-256
`30e176bf357de0c4330ff3ad9538de03a443f9f88c21dcf9571b4b66bf54dfc0`.

The retained artifact is `analysis/phase4_respawn_row_provenance.json`,
SHA-256 `c2df5aad3f61b8590b8d55f5c5e6f92b396290d1f3013ff49e9edff504fde7b0`.
Its generator stopped only PID 315455 owned by config
`/tmp/abl-phase4-i40-c15-row-source-generic-qrQpG5`. C15 remains active:
activation/denial policy, reset scope, indirect writers, persistence, other
death classes and remaining-stage breadth are still open.

## Iteration-41 current-binary progression and movie repair

The retained capsule set was validated first: 50/50 capsules and
2,442,984,379 external bytes passed preservation/freshness. The exact pinned
offline reader queried `E10__hazard_pit_LEVEL02`; its 359 records are complete
and nontruncated, safe XYZ changes at frames 157 and 249, and the first
transition hotspot window is 140..160. This frame-domain, save-anchored capsule
cannot establish current-binary cold-boot progression, memory-card provenance,
the unedited control or the exact scene-3 DAT source. Those named missing
domains required a fresh isolated live replay. Thud and scene-14 dependency
refreshes were also outside the 50-capsule movie set or required exact current-
binary behavior rather than frame reconstruction.

Observation: the iteration-40 config was not independent. Its 131,072-byte
memory card, SHA-256
`63c08f0143e7b714309de900905f22944ae07f1da881ce9aa3a0237a5dacf517`,
contains one each of completed-game `BASCUS-94288LEV15:00` and `:01`. A fresh
isolated config has no card before the first native save. The historical
scene-3 join therefore had an undeclared progression dependency even though
its mounted disc and movie serial were pristine. That card is rejected rather
than imported or reclassified.

The replacement starts from centrally pinned pristine
`level01_end_of_stage.sav` (SHA-256
`42047329754c56f6daaf413e192ba8e88ca40889714bbc9f57216f3462ed739f`).
Load-free inspection verifies pristine `SCUS-94288` media. A native recipe—Up
for 1500 frames, then Cross/Square/Square/Square with 400/1200/1000/1000-frame
waits—completes LEVEL01 and produces exactly one `BASCUS-94288LEV02:00` record.
The transient game-written card is 131,072 bytes with SHA-256
`5ca4ee4e23d76fe4eb596d0fe7766c481dcac456557756734f28c903fa242d4c`.
The preparation generator receipts the state/media/card and stops its owned
PID. A second DuckStation process then cold-boots the pristine disc with the
same isolated card. No card bytes are retained outside `/tmp`.

The unedited centrally pinned LEVEL02 movie remains reproducible and
nontruncated. With the controlled `LEV02:00` card it loads Tunnels, but its
frames 6307..6315 hold Left and move selection back to Ant Hill; Cross at 6370
therefore reaches scene 1. Two earlier Square substitutions were rejected
because they overcorrected later load/save inputs. The accepted in-memory
branch removes only Left from those nine frames and saves no derivative. Its
semantic SHA-256 is
`8ad070c7d00135e6f48956819a8b73669203691145139edb1db5f4c635389e47`.
Control and branch are equal through movie frame 6300/scene 0. At frame 7600
the branch is in scene 3 with DAT base `0x8015E22C`, slot-1 pointer
`0x8015E684`, the expected 18-row type-0x01 record and selected row 6 at
`0x8015E6D0`; all bytes match the unique pinned `LEVEL03/LEVEL.DAT` offsets
`0x458/0x4A4`. The transient card is byte-identical before and after both
branches.

The current generator/artifact SHA-256 values are
`c2d0faf510d2db45deb9f3fb67dabb2405efa2c1e19af3ea23b6eb869742d88c`
and `1da77a6fb0d98775c1671f5384d0e3a9cc875e47069029bbbd2387704abfe592`.
The smallest retained reproduction is the dedicated two-process declarative
scenario `tools/scenarios/duckstation/pristine_c15_authored_row_provenance.yaml`
(SHA-256 `81dc60f669be9dfac82f34d9816401398e58d720de0a308a62d064db26a1da9f`),
whose eleven assertions are enforced by that generator.
The refreshed checkpoint artifact is
`1353bd90217a726c432644b2150c15b0ead3bd3d8c07e8840966fc5d7f07f226`;
the writer catalog is
`6be7a774080c5ed8fb02bce0b50e2cef136924f0b5649b2b0871e8ab068d2aaf`.
Central fixture-consumer reconciliation changed the preservation-manifest
hash, so affected E08/C16/Thud artifacts were live-replayed in dependency order
instead of having their source pins edited. Every run reverified pristine
mounted/save media and stopped only its owned PID. The Phase-4 inventory now
has 42/42 generators with no source-dependency mismatch.

This repairs current-toolchain and progression provenance; it does not close
C15. Activation/denial policy, reset scope, indirect/additional variants,
other death classes, persistence and remaining-stage breadth stay open.

## Iteration-42 exact LEVEL03 selector denial

Iteration 3 began with the mandatory recursive movie census: 110 files under
`movies/Phase4` and 147 across the broader tree. No new operator fixture was
requested. The retained capsule preservation/freshness validator passed all
50/50 capsules and 2,442,984,379 external bytes. The exact pinned offline
reader, SHA-256
`b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`,
queried `E10__hazard_pit_LEVEL02` first. It confirmed 359 complete,
nontruncated frame records, safe-anchor changes at movie frames 157 and 249,
the 140..160 execution hotspot window, and raw player status bytes `14 00` at
frame 156. A frame-boundary capsule cannot execute the one-bit counterfactual
or attribute its skipped instruction path, so that named missing causal domain
justified a fresh isolated API replay.

The current-binary C15 generator saved a transient exact frame-156 state after
reproducing the natural boundary. Natural status was `0x0014`. A checked
`debugger.writeU16` cleared only mask `0x0010`, producing status `0x0004` and a
single changed main-RAM byte, `0x800A6590`. The identical one-frame movie suffix
remained reproducible and nontruncated. The pristine LEVEL03 selector executed
17 hits/17 distinct PCs through load `0x800B3C64`, mask `0x800B3C6C` and denial
branch `0x800B3C70`; safe-XYZ stores `0x800B3D24/40/54` were absent. The
resident handler remained identical to the natural control at 768 hits/138
distinct PCs, including all exact safe loads and live stores. It copied prior
safe XYZ `[507900,31787,503976]` to live XYZ, restored health to 4 and
decremented lives to 4. The passive cached-block trace and its uninstrumented
pass were equal in RAM, registers, cycle and frame.

The smallest declarative regression is
`tools/scenarios/duckstation/pristine_c15_authored_row_denial.yaml`, SHA-256
`03d06a3187229cb948d51d9a838a7d3a81d4715472b551ce77aa76b8f0f0f582`;
it passed 19/19 assertions in a separate isolated run. The retained checkpoint
artifact is SHA-256
`51f953c286482d3408ff85e89a26bbd2a1f7749b250e81cfc0672ce398c2a53e`.
The writer catalog joined that denial and regenerated to
`c6a23f40484bd8b7a3905a0bdf9fbf9dd46bdaea0292b2a3c4083a51dfb0120e`.
The current-binary two-process authored source replay then rejoined the denial
to the unique LEVEL03 DAT record and retained SHA-256
`d1d408b1cdf0a9dd05337cb1bc6839678256462cc63485275478724d27996947`.

Exact source dependencies were replayed rather than edited in place. E08
hazard outcomes, C16 Flight and C16 death breadth retained their prior bounded
behavior at SHA-256
`e0563db922dd285b00c74a824c18958abf73a74953f267ba47cdbc7902f230a7`,
`382139a197e6b8cc6cb95b9c7573300e42ba7cdb6eb60d518241d36b4351309f`
and `8a58746634036eebd94d03af08beec36510990fd8a1403c26c47b4ac1e2f5002`.
Every replay reverified mounted/save media against pristine pins and stopped
only its config-owned PID. No card, save, movie derivative, capture or retail
asset byte is retained in Git.

This rejects the hypothesis that scene-3 authored-row selection is independent
of player status mask `0x0010`. It does not identify the writer/source of that
mask, assign whole-word status semantics, generalize denial to LEVEL10 or other
row-selecting variants, or complete C15. Inventory remains 42/42 generators;
coverage stays 16/107 complete, 91 open and 2/12 complete families.

## Iteration-43 LEVEL10/LEVEL04 status-gate breadth

Implementation iteration 4 again began with the mandatory recursive census:
110 files under `movies/Phase4` and 147 under the broader movie tree. No new
fixture was requested. The exact 50/50 capsule freshness/preservation validator
passed all 2,442,984,379 external bytes. The pinned reader queried the retained
LEVEL02, LEVEL05 and LEVEL07 pit capsules before any live replay. All were
complete/nontruncated (359, 263 and 343 records), and each natural pre-reset
boundary exposed player status `0x0014`; the next frame cleared it to `0x0000`.
Those frame-domain records establish the natural value and boundary but cannot
execute a one-bit branch or attribute skipped PCs. That named missing
counterfactual domain justified the isolated live escalation.

The focused generator reproduced scene 10 movie frame 144 and scene 4 movie
frame 204 from their centrally declared pristine saves. Each exact state
supplied an unmodified branch and a checked `debugger.writeU16` branch that
changed only byte `0x800A6590`, from word `0x0014` to `0x0004`, before replaying
the exact next recorded frame. Runtime writer bytes matched the pinned pristine
LEVEL10 slice SHA-256 `97e72e5e…` and LEVEL04 slice `8494bef9…`.

The scene-10 natural writer executed 279 hits/70 PCs and installed safe/live
XYZ `[-159648,3628,1182816]`. Its denial executed only 14 gate-path PCs and no
decisive stores, so the resident handler consumed prior XYZ
`[-103436,-4903,1209759]`; health/lives still became `4/0`. The resident
handler was exactly equal across both passive branches at 766 hits/136 PCs and
PC-list SHA-256 `7bde93c8…`.

The scene-4 natural writer executed 31 PCs and installed safe/live XYZ
`[727892,9584,165941]` plus heading `2048`. Its denial executed 13 gate-path
PCs and no decisive stores, so the resident handler consumed prior XYZ
`[744984,4861,139049]` plus heading `1965`; health/lives still became `4/5`.
Resident coverage was exactly equal across branches at 768 hits/138 PCs and
PC-list SHA-256 `3071281b…`. Every trace was nontruncated, cycle-neutral, and
matched its own uninstrumented RAM/register/cycle/frame endpoint.

The retained artifact is `analysis/phase4_respawn_status_policy.json`, SHA-256
`1e3c8d742024886fda039d6b6bfcccf2322c9819433d94d3e29e853fcdd4a207`.
The two 22-assertion declarative regressions are
`pristine_scene10_pit_status_denial.yaml` (SHA-256 `a3a9e779…`) and
`pristine_scene4_pit_status_denial.yaml` (SHA-256 `c30a7bdc…`). The live run
used current fork `fe0cca16…` and binary SHA-256 `91cbe22b…`, reverified
mounted/save media as pristine, retained no movie/save/RAM bytes, and stopped
only its config-owned PID. Inventory is 43/43 generators with all Phase-4
retained artifacts fresh.

This rejects independence from mask `0x0010` at the two additional exact
writers. The necessary-input result now covers both known direct nearest-row
writers (LEVEL03 and LEVEL10) and LEVEL04's fixed-tuple writer. It still does
not identify the mask source, setter/clearer, whole-word semantics or general
policy, nor cover indirect/additional writers, remaining death classes,
persistence or stage breadth. C15 stays partial; coverage remains 16/107
complete, 91 open and 2/12 complete families.

## Rejected method

An access-log trial was re-armed after state/movie load and correctly attributed
continuous stores, but forcing the interpreter changed the full natural replay:
the recorded death did not occur. Its behavioral output is excluded. The
interpreter boundary is retained as a failed full-replay method, not laundered
into the cycle-neutral conclusions above. Iteration 36 instead starts each
short attribution capture at its verified pre-reset movie anchor; this crosses
the writer successfully but remains attribution-only for the same reason.

## Commands

```text
python3 tools/phase4_checkpoint_respawn.py --port 20017 --token '<redacted-token>' --config-dir /tmp/abl-phase4-i11-c15-final-20017 --instance-state recreated
python3 tools/phase4_checkpoint_respawn.py --port 20035 --token '<redacted-token>' --config-dir /tmp/abl-phase4-i12-c15-ledger-20035 --instance-state recreated
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_contact_respawn_safe_anchor.yaml --output-dir /tmp/abl-phase4-i12-c15-contact-scenario
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_checkpoint_respawn.yaml --output-dir /tmp/abl-phase4-i12-c15-pit-scenario
python3 tools/phase4_checkpoint_respawn.py --port 20620 --token '<redacted-token>' --config-dir /tmp/abl-phase4-i35-c15-tracked-teI7ak --instance-state recreated
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_scene10_pit_respawn.yaml --output-dir /tmp/abl-phase4-i35-c15-scene10-final
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_scene4_pit_respawn.yaml --output-dir /tmp/abl-phase4-i35-c15-scene4-final
python3 tools/phase4_checkpoint_respawn.py --port 20642 --token '<redacted-token>' --config-dir /tmp/abl-phase4-i36-c15-writers-final-20642 --instance-state recreated
python3 tools/phase4_respawn_writer_catalog.py
python3 -m pytest -q tests/test_phase4_respawn_writer_catalog.py tests/test_phase4_checkpoint_respawn.py
python3 tools/phase3_xrefs.py
python3 tools/phase3_record_types.py
python3 tools/phase4_e08_hazard_outcomes.py --port 20681 --token '<redacted-token>' --config-dir /tmp/abl-phase4-i39-e08-sourcefinal-YZRwRM --instance-state recreated
python3 tools/phase4_lives_death_breadth.py --port 20682 --token '<redacted-token>' --config-dir /tmp/abl-phase4-i39-c16-breadth-sourcefinal-5kWg50 --instance-state recreated
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_scene6_level06_respawn_initializer.yaml
python3 tools/phase4_c16_flight_death.py --port 20680 --token '<redacted-token>' --config-dir /tmp/abl-phase4-i39-level08-sourcefinal-AvX097 --instance-state recreated
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_scene8_level08_respawn_initializer.yaml --output-dir /tmp/abl-phase4-i39-c15-scene8-scenario-pass
python3 tools/phase4_respawn_row_provenance.py --port 20716 --token '<redacted-token>' --config-dir /tmp/abl-phase4-i40-c15-row-source-generic-qrQpG5 --instance-state recreated --movie ~/Downloads/ABL-phase4-ratchet/worktrees/phase4-20260715-220101-2857888/movies/go_to_end/LEVEL02.movie.json
python3 tools/phase4_respawn_row_provenance.py --port 24211 --token '<redacted-token>' --config-dir /tmp/abl-p4-i2-c15-row-cascade-0lC20T --instance-state recreated --prepare-progression
python3 tools/phase4_respawn_row_provenance.py --port 24212 --token '<redacted-token>' --config-dir /tmp/abl-p4-i2-c15-row-cascade-0lC20T --instance-state reused --movie /absolute/checkout/movies/go_to_end/LEVEL02.movie.json
python3 tools/phase4_checkpoint_respawn.py --port 24331 --token '<redacted-token>' --config-dir /tmp/abl-p4-i3-c15-denial-UsIxHm --instance-state recreated
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_c15_authored_row_denial.yaml --output-dir /tmp/abl-p4-i3-c15-denial-scenario
python3 tools/phase4_respawn_status_policy.py --port 24519 --token '<redacted-token>' --config-dir /tmp/abl-p4-i4-c15-status-refresh-HDRffe --instance-state recreated
python3 tools/phase4_respawn_row_provenance.py --port 24520 --token '<redacted-token>' --config-dir /tmp/abl-p4-i4-c15-row-refresh-T9jdhL --instance-state recreated --prepare-progression
python3 tools/phase4_respawn_row_provenance.py --port 24521 --token '<redacted-token>' --config-dir /tmp/abl-p4-i4-c15-row-refresh-T9jdhL --instance-state reused --movie /absolute/checkout/movies/go_to_end/LEVEL02.movie.json
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_scene10_pit_status_denial.yaml --output-dir /tmp/abl-p4-i4-c15-scene10-denial
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/pristine_scene4_pit_status_denial.yaml --output-dir /tmp/abl-p4-i4-c15-scene4-denial
python3 tools/phase4_respawn_row_provenance.py --port 24339 --token '<redacted-token>' --config-dir /tmp/abl-p4-i3-row-guard-Qv5B3d --instance-state recreated --prepare-progression
python3 tools/phase4_respawn_row_provenance.py --port 24340 --token '<redacted-token>' --config-dir /tmp/abl-p4-i3-row-guard-Qv5B3d --instance-state reused --movie /absolute/checkout/movies/go_to_end/LEVEL02.movie.json
```

All derived saves/movies were transient and deleted. No operator-owned or
copyrighted bytes are retained in Git.

## Remaining

Establish the source/general policy of status mask `0x0010`, reproduce denial
in another row-selecting variant,
reproduce indirect or other overlay variants and
actor/scripted/exceptional death classes, and cover save/load/stage exceptional
paths. C15 stays partial.
