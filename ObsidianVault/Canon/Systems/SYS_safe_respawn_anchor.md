---
kind: system
id: SYS_safe_respawn_anchor
status: runtime_seen
confidence: confirmed
source_state: original_game
evidence: [analysis/phase4_checkpoint_respawn.json, analysis/phase4_respawn_status_policy.json, analysis/phase4_respawn_writer_catalog.json, analysis/phase4_respawn_row_provenance.json, analysis/phase4_e08_hazard_outcomes.json, analysis/phase4_c16_flight_death.json, config/phase4_checkpoint_respawn.yaml, config/phase4_respawn_status_policy.yaml]
---

# Safe respawn anchor

## Confirmed original-game interface

The resident player block contains a safe-position tuple:

| Field | Address | Type | Confirmed owners |
|---|---:|---:|---|
| live XYZ | `0x800A6500/04/08` | `3 × s32` | movement, collision, spawn and transition code |
| safe XYZ | `0x800A6550/54/58` | `3 × s32` | stores `0x80054E70/78/80`; loads `0x8005B1DC/E4/EC` |
| safe heading | `0x800A6578` | `s16` storage | store `0x80054E88` |
| shared status | `0x800A6590` bit `0x0008` | `u16` view | cleared/set inside `0x80054C90`; whole-word semantics remain shared |
| reset-selector gate | `0x800A6590` bit `0x0010` | `u16` view | exact one-bit denials prove necessity at the reproduced LEVEL03/LEVEL10 nearest-row and LEVEL04 fixed-tuple boundaries; source, whole-word and general policy remain open |
| DAT type-0x01 pointer | `0x80096DA4` | `u32` | shared type-table slot 1; scene 3 points to the authored `LEVEL03/LEVEL.DAT` coordinate record |

`FUNC_80054C90` is a gated, continuous updater. It checks player/scene state,
collision-region results and distances to live records before copying live XYZ
and heading. That behavior is an internal safe-position contract. It does not
by itself prove an authored, discrete or player-visible checkpoint.

On the reproduced pit path, overlay `0x800B3C54..0x800B3D78` runs before the
common tail. With status bit `0x0010` set, it scans the scene-local list reached
through `0x80096DA4`, chooses minimum squared X/Z distance in the `>>5` domain,
stores selected X/Z shifted left five at `0x800B3D24/0x800B3D40`, derives Y via
ground query `0x800B3D44` minus 256 and stores it at `0x800B3D54`. The common
tail of `FUNC_8005B134` then loads safe XYZ, writes live and previous XYZ,
resets player state, restores health to 4, and decrements lives.

The 292 runtime bytes match only the hash-verified pristine
`LEVEL03/LEVEL.BIN` slice at file offset `0x2B4` (SHA-256
`1fdeb0da151050edbde73a082b5951ae4326ec133979ca5bae2f0198bd8cfbf9`)
among staged BIN files. This pins the code authority. Static transfer
provenance could not map the save-state-restored row table back to a disc file;
the cold-boot asset join below supersedes that source limitation.

## Authored scene-3 row source

The shipping parser `0x8001CDC0..0x8001D3CC` is a byte-matched handwritten
build unit. Its non-negative top-level-record path stores the current record
pointer at `0x80096DA0 + type*4`; normal records advance by
`4 + count*0x0C`. Therefore `0x80096DA4` is shared DAT type-table slot 1, not a
bespoke respawn-table owner.

A pristine from-boot replay reaches scene 3 at movie frame 7000 with DAT base
`[0x80082498] = 0x8015E22C` and slot 1 equal to `0x8015E684`. The pointed
header is type 1/count 18. Its 220-byte SHA-256 is
`6adbdd60b3935d76caf6b929cb108fd4b338d39c1888a2ad4abe92d21416fee3`;
the 224-byte record-plus-next-header SHA-256 is
`fec6e92f69fc84357c1e56e03d2ff1e78423703faf532779b3660bbbda26382d`.
An exhaustive parse of all 21 hash-pinned staged `LEVEL*/*.DAT` inputs finds
that window only at `REBUILD/files/LEVEL03/LEVEL.DAT` offset `0x458`.

Selected row 6 is runtime `0x8015E6D0`, file offset `0x4A4`, raw XYZ
`[15678,0,15438]`, with row SHA-256
`88bb66f2ac5168493c220dcdf576a7adff6664b315802d8ed70c93c3c4ac0f49`.
Those bytes are exact in RAM and the staged asset. The earlier raw-X-only
`+128` branch changes safe/live X by `+4096`, so the combined evidence confirms
both authored source and selector consumption for this scene. It does not
generalize row activation/denial policy to other scenes or variants.

The same exact frame-156 boundary supplies a causal denial. Natural player
status is `0x0014`; clearing only mask `0x0010` changes one RAM byte,
`0x800A6590`, and leaves status `0x0004`. The pristine LEVEL03 selector then
executes a 17-instruction gate/return path through status load `0x800B3C64`,
mask `0x800B3C6C` and branch `0x800B3C70`, without executing safe-XYZ stores
`0x800B3D24/40/54`. The resident handler still executes the same 768-hit,
138-PC path as natural control and copies the prior safe tuple
`[507900,31787,503976]` to live XYZ while restoring health/lives to `4/4`.
Both the passive cached-block trace and its uninstrumented pass end with equal
RAM, registers, cycle and frame. This proves one necessary selector input, not
who sets the bit or the policy of the shared status word.

## Scene-qualified runtime boundaries

In the pinned LEVEL02 pit replay, the player is falling at movie frame 100 while
safe XYZ still holds its initial value. Frame 156 still has safe XYZ
`[507900,31787,503976]`; at frame 157 overlay selection and resident
consumption have made live and safe XYZ exactly `[501696,30092,494016]`, health
is 4 and lives is 4.

Changing only safe X by `+4096` at frame 100 does not change that stable result.
The same convergence occurs when stores `0x80054E70/78/80` are NOPed in both
comparison branches. At frame 156, row 6 is nearest; its raw X is 15678 and
scales to 501696. Changing only that source word by `+128` changes frame-157
safe/live X by `+4096`, while Z and health/lives are unchanged and Y is
ground-recomputed. Both one-frame branches execute identical selector and
resident-handler coverage and independently match their uninstrumented RAM,
register, cycle and frame results. This identifies the exact owner chain for
this path without generalizing to other overlays or death classes.

At that same boundary, the status-mask denial above preserves the frame-156
safe tuple rather than selecting row 6. Frame 157 live/safe XYZ is therefore
`[507900,31787,503976]`, with health/lives `4/4`. The unchanged resident path
separates selector denial from respawn denial: mask `0x0010` controls this
scene-qualified row writer, while the already-selected transition still runs
the common consumer.

The separately pinned Bug Bar contact path supplies the complementary resident
case. At fatal movie frame 350, scene 9 has live XYZ
`[-27693,-116008,-162370]`, retained safe XYZ
`[-23491,-112966,-142999]`, health -1 and lives 1. Changing only safe X by
`+4096` changes one RAM byte, `0x800A6551`. At the first completed respawn five
movie frames later, control live/safe XYZ equals the retained tuple and the
branch live/safe X is exactly `+4096`; Y/Z, scene and health/lives `4/0` are
unchanged. Both branches execute identical bounded coverage: 50 updater hits,
974 resident-handler hits and 670 Bug Bar overlay-window hits. The continuous
safe-XYZ store PCs are absent in that five-frame suffix, while all three exact
resident safe loads, live stores, health restore and lives decrement are
present. This causally proves direct retained-anchor consumption for this
ordinary contact death without assigning actor or hazard identity from the
fixture name.

Two further centrally pinned pit recordings widen the ordinary transition
boundary without assigning semantics from their filenames. In live scene 10,
movie frame 144 has live XYZ `[-163392,111928,1157047]`, health/lives `0/1`,
and safe X `-103436`; frame 145 has live/safe XYZ
`[-159648,3628,1182816]` and health/lives `4/0`. In live scene 4, frame 204
has live XYZ `[749740,121085,124853]`, health/lives `4/6`, and safe X
`744984`; frame 205 has live/safe XYZ `[727892,9584,165941]` and
health/lives `4/5`.

For each exact one-frame suffix, changing only pre-reset safe X by `+4096`
changes one RAM byte but produces zero safe/live X delta at the reset. Control
and mutation execute identical bounded updater, resident-handler and
scene-overlay-window coverage. The three continuous safe-XYZ store PCs are
absent while the exact resident safe loads, live stores, health restore and
lives decrement are present. Thus the scene-qualified transition path replaces
the tuple before resident consumption. The sampled bytes at
`0x800B3C54..0x800B3D78` have SHA-256 `52cb5a20…` in scene 10 and
`b88d820a…` in scene 4; neither matches the separately proven LEVEL03 selector
slice. Those same-address windows therefore cannot identify the writer.

Fresh short replays watched only safe XYZ/heading across each reset and supplied
the missing attribution. In scene 10, four complete writes come from
`0x800B3BAC/3BBC/3BC8/3BDC`; the enclosing exact function is
`0x800B3ADC..0x800B3C18`. Its 320-byte runtime slice uniquely matches pristine
`LEVEL10/LEVEL.BIN` offset `0x13C` (SHA-256
`97e72e5e4bf8c1029cabc98cfcef43d5077666edeb39617d012769f01285c4b8`).
It gates on status bit `0x0010`, selects the nearest row, scales X/Z by 32,
derives Y with the ground query, and preserves heading.

In scene 4, five complete writes come from
`0x800B3C94/3C9C/3CA8/3CB0/3CC4`; the enclosing exact function is
`0x800B3C5C..0x800B3CD4`. Its 124-byte runtime slice uniquely matches pristine
`LEVEL04/LEVEL.BIN` offset `0x2BC` (SHA-256
`8494bef9a426a6b2ceea0bb57a634c5520a12abb89c493ce4b88ab3d992764ba`).
It gates on the same status bit, installs fixed X/Z and heading `2048`, and
derives Y with the ground query. Access watching forces interpreter execution,
so these short captures prove exact write attribution, not timing equivalence;
the earlier passive, cycle-neutral natural/control pairs remain the behavioral
authority.

The same-state status controls now bind the gate on both functions. At scene 10
movie frame 144, natural status `0x0014` executes 279 writer hits across 70 PCs
and installs `[-159648,3628,1182816]`. Clearing only mask `0x0010` changes byte
`0x800A6590`, leaves `0x0004`, executes a 14-PC gate path with none of the four
decisive stores, and makes the unchanged 766-hit/136-PC resident handler consume
the prior tuple `[-103436,-4903,1209759]` at frame 145.

At scene 4 movie frame 204, the natural writer executes 31 PCs and installs
`[727892,9584,165941]` with heading `2048`. The same one-byte denial executes a
13-PC gate path with none of the five decisive stores; the unchanged
768-hit/138-PC resident handler consumes prior XYZ `[744984,4861,139049]` and
heading `1965` at frame 205. In both controls, health restoration/life
consumption and the exact resident safe-load/live-store chain still execute,
and every passive cached-block trace matches its own uninstrumented result.
Together with LEVEL03, this proves mask necessity across both known direct
nearest-row writers and one fixed-tuple writer. It does not establish who sets
or clears the bit, whole-word semantics, or general activation policy.

## Staged direct-writer variants

A deterministic static census of all 11 hash-pinned pristine staged
`LEVEL*/LEVEL.BIN` files finds 21 direct absolute stores to safe X/Y/Z or
heading in five files: LEVEL03, LEVEL04, LEVEL06, LEVEL08 and LEVEL10. The
target totals are five X stores, eight Y stores, five Z stores and three
heading stores. LEVEL03/04/10 retain the live scope above; LEVEL06 and LEVEL08
now have scene-qualified live activations.

LEVEL06 contains a fixed-safe-tuple initializer at
`0x800B3AEC..0x800B3B94`, file offset `0x14C`. Its 168-byte slice has SHA-256
`33b21c83ad52f8ef13786de5ff7d48ed615fcae8618d7c8833b64c6b481656be`
and directly writes X/Y/Z/heading `[35329,-85228,-154696,3063]` at
`0x800B3B00/3B24/3B3C/3B30`. LEVEL08 contains a fixed safe-and-live tuple
initializer at `0x800B3AE8..0x800B3B54`, file offset `0x148`. Its 108-byte
slice has SHA-256
`4b2e8bccbcd42dcb056b267d66a35bb8b7dbfdf9171eccd1a914ff1f67b029c9`
and directly writes X/Y/Z/heading `[-157682,5744,-12845,352]` at
`0x800B3B08/3B10/3B18/3B20`.

The resident static entry map supplies address-level caller candidates:
LEVEL06 entry `0x800B3AEC` is targeted at
`0x8005484C/0x8005485C/0x8005B194`, and LEVEL08 entry `0x800B3AE8` at
`0x8005B1A4`. Region A reuses those addresses, so a JAL alone is not overlay
identity; the LEVEL06 and LEVEL08 paths below separately match their loaded
runtime bytes.

## Scene-6 LEVEL06 activation

The centrally pinned scene-6 natural death replay provides that runtime join.
At movie target 487, scene is 6, health/lives are `4/4`, safe XYZ is
`[93783,-83752,-134554]`, and passive initializer coverage is zero. Target 488
executes all 42 distinct PCs in `0x800B3AEC..0x800B3B94` once without
truncation; safe XYZ becomes `[35329,-85228,-154696]`, heading remains 3063,
and lives becomes 3. The control/instrumented endpoints are byte-, register-,
cycle- and frame-equal.

At the exact entry, PC is `0x800B3AEC`, RA is `0x8005B19C`, `v1=3`, and the
call instruction at `0x8005B194` is `0x0C02CEBB`. The 168 loaded bytes have
SHA-256 `33b21c83ad52f8ef13786de5ff7d48ed615fcae8618d7c8833b64c6b481656be`,
equal to the pristine LEVEL06 slice. A complete four-event writer log attributes
safe X/Y/heading/Z to `0x800B3B00/3B24/3B30/3B3C`.

Four branches reload the same transient entry state after inspecting it and
re-verifying mounted pristine media. NOPing the X, Y or Z store preserves only
that field's prior value; changing the heading source immediate from 3063 to
3064 changes heading to 3064. All branches return at the same
cycle/frame/PC/SP boundary as control. This confirms each fixed field effect;
the state and code edits are transient and deleted.

The resident handler's pristine jump table covers scenes 3 through 10. Scene 6
selects `0x8005B194`; scenes 5, 7 and 9 route directly to the common tail, as
do values outside the bounded domain. This is the native selector policy, not
evidence that every selected overlay body has been live-qualified.

No direct absolute safe-tuple store is present under this scanner in staged
LEVEL00/01/02/05/07/09. This is not evidence that those files lack an indirect,
pointer-mediated or separately overlaid writer. The catalog does not establish
runtime activation by itself. The later scene-6 and scene-8 experiments close
that boundary only for LEVEL06/LEVEL08 and their bounded ordinary-respawn
paths; other row activation/denial policy, death classes and persistence remain open.

## Scene-8 LEVEL08 activation

The centrally pinned pristine `level_14.sav` scene-8 anchor supplies a natural
actor-contact death without adding another operator recording. After a bounded
health/lives and position setup, a cycle-neutral 180-frame replay executes the
resident scene-8 call `0x8005B1A4` and all 27 PCs in
`0x800B3AE8..0x800B3B50` exactly once. The loaded 108-byte body has SHA-256
`4b2e8bccbcd42dcb056b267d66a35bb8b7dbfdf9171eccd1a914ff1f67b029c9`,
equal to pristine `LEVEL08/LEVEL.BIN` offset `0x148`. The ordinary outcome
restores health to 4 and decrements lives from 3 to 2.

Changing only actor-state bit `0x0080` at the matched pre-contact boundary
changes one RAM byte, prevents the damage call and produces zero respawn-handler
and LEVEL08-initializer hits at an identical frame/cycle/PC/SP endpoint. A
later natural recurrence supplies the exact call/entry boundary:
PC/RA `0x800B3AE8/0x8005B1AC`, with call word `0x0C02CEBA`. This breakpoint
capture is not used as first-respawn timing authority; the passive movie trace
is.

A complete attribution-only writer log records seven direct stores: safe
X/Y/Z/heading at `0x800B3B08/10/18/20` and live X/Y/Z at
`0x800B3B28/30/38`. The resulting safe tuple is
`[-157682,5744,-12845,352]`, and live XYZ equals its first three fields.
Reloading one inspected transient entry state and changing only the X source by
`+4096` changes safe/live X by exactly `+4096`; changing only the heading
source by one changes safe heading from 352 to 353. Control and both mutations
return at the same frame/cycle/PC/SP boundary after mounted pristine media is
reverified. The state and runtime edits are transient and deleted.

## Disambiguation

`0x800823CC` is the resident setpiece record index read by
`FUNC_8004D698`/`0x8004D8CC` and written at `0x8005456C`/`0x8005B9D8`.
It is not written by `FUNC_80054C90` and must not be substituted for the
player-block safe XYZ tuple.

## Current-binary source provenance

The authored LEVEL03 source join has been requalified on DuckStation binary
SHA-256 `91cbe22b2c2e22ad83d695988ada36bbabb22c65366cb5ec9e8e30784de93af6`
without the prior config's undeclared completed-game memory card. From the
centrally declared pristine `level01_end_of_stage.sav`, native LEVEL01
completion writes exactly one transient `LEV02:00` card record. After stopping
that preparation process, a second process cold-boots the pinned LEVEL02 movie.

The unedited recording selects scene 1 because Left remains held for frames
6307..6315 after Tunnels is selected. An unsaved in-memory branch removes only
those nine Left samples; it is identical to control through frame 6300 and
reaches scene 3 at frame 7600. There, DAT base `0x8015E22C`, type-table slot-1
pointer `0x8015E684`, the 18-row type-0x01 record and row 6 are byte-identical
to pristine `LEVEL03/LEVEL.DAT` offsets `0x458/0x4A4`. The transient card is
unchanged across control and branch. These facts qualify the source join and
its provenance; they do not establish general row activation/denial policy or
another reset variant.

## MOD rule

Preserve DAT type-table construction, authored row bytes,
updater/transition-writer/consumer ordering and direct resident safe-anchor
consumption. Preserve the LEVEL03/LEVEL10/LEVEL04 status-mask gates before their
transition stores; do not assign or reuse mask `0x0010` without tracing its source and
shared whole-word semantics. Treat the exact LEVEL03/LEVEL10/LEVEL04/LEVEL06/LEVEL08 writers as
residency-qualified and enumerate other variants before replacing respawn
behavior. A new checkpoint system needs explicit
initialization, death-class reset, scene/load/save policy and a MOD-private
owner; a nickname or one static xref is not sufficient.
