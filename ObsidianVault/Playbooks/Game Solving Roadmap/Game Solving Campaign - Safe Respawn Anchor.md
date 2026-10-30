---
kind: campaign
id: phase4_safe_respawn_anchor
phase: 4
rows: [C15_checkpoints]
family: player_lifecycle
status: active
evidence: [analysis/phase4_checkpoint_respawn.json, analysis/phase4_respawn_status_policy.json, analysis/phase4_respawn_writer_catalog.json, analysis/phase4_respawn_row_provenance.json, analysis/phase4_e08_hazard_outcomes.json, analysis/phase4_c16_flight_death.json, config/phase4_checkpoint_respawn.yaml, config/phase4_respawn_status_policy.yaml]
---

# Game Solving Campaign — Safe Respawn Anchor

## Scope and exit decision

This campaign owns C15's internal safe-position producer/consumer interface,
death-class position selection, authored checkpoint/setpiece sources, reset and
persistence policy, and stage breadth. It does not inherit C16 lives/game-over,
E10 hazard identity, E02 collision or E16 overlay-loader completion.

Status is **active / incomplete**. The existing pristine LEVEL02 pit recording
has a natural positive, input-negative and two same-code RAM counterfactuals. A
frame-156 source-row counterfactual identifies the exact frame-157 owner chain:
overlay `0x800B3C54` writes safe XYZ and resident `0x8005B134` consumes it. The
existing Bug Bar contact recording now supplies the complementary direct
resident path: safe-X-only `+4096` at fatal frame 350 changes the first completed
respawn safe/live X by exactly `+4096` at frame 355 with identical execution
coverage. Existing pit pairs add scene-10 frame `144→145` and scene-4 frame
`204→205` boundaries. In both, a safe-X-only `+4096` branch is replaced before
the resident safe-to-live chain under execution-identical one-frame coverage;
the continuous safe-XYZ stores are absent. Short attribution-only replays now
bind the replacement writes to exact pristine code. Scene 10 uses the LEVEL10
function `0x800B3ADC..0x800B3C18`; scene 4 uses the LEVEL04 function
`0x800B3C5C..0x800B3CD4`. A complete direct-store census of the 11 staged
LEVEL.BIN files additionally bounds fixed initializers in LEVEL06 and LEVEL08.
An existing scene-6 death replay now activates the exact pristine LEVEL06
function at movie frame 488 through resident call `0x8005B194`; all 42
instructions and four safe-field stores are reproduced, then confirmed by four
same-entry instruction controls. The existing pristine scene-8 anchor now also
activates exact LEVEL08 through resident call `0x8005B1A4`: the natural trace
covers all 27 initializer PCs, a one-byte response-only control covers none,
seven complete writes install fixed safe/live state, and X/heading source
controls change only their predicted fields at identical return boundaries.
A current-binary pristine from-boot replay now closes the bounded authored
source for scene 3 without the old undeclared completed-game card. Native
progression from the pinned LEVEL01 completion state creates a transient
`LEV02:00` card; an unsaved nine-frame Left-only movie repair then reaches the
target while its unedited control reaches scene 1. The resident DAT parser sets
shared type-table slot 1 at
`0x80096DA4` to `LEVEL03/LEVEL.DAT` offset `0x458`, and the live 18-row record
plus selected row 6 are byte-identical to that hash-pinned file. Joined to the
prior row-6 mutation, this proves that the selector causally consumes the
authored row at file offset `0x4A4`. Clearing only player status mask `0x0010`
at frame 156 now adds the matching denial: one changed RAM byte removes every
LEVEL03 safe-XYZ store, leaves a 17-PC selector gate/return path, and the same
768-hit resident handler consumes the prior safe tuple. Two new same-state
controls widen that result: the exact LEVEL10 nearest-row writer falls from
279 hits/70 PCs to a 14-PC pre-store path, and the LEVEL04 fixed-tuple writer
falls from 31 PCs to a 13-PC pre-store path. Each `0x0014→0x0004` branch changes
only byte `0x800A6590`, skips every decisive writer store, and retains exactly
the natural branch's resident-handler coverage while consuming its prior safe
tuple. The campaign still does not identify the mask source, setter/clearer,
whole-word/general policy, other overlay/death variants, indirect writers,
persistence or a player-visible checkpoint.

## Retained frontier

- Producer: resident `0x80054C90..0x80054EAC`, exact stores
  `0x80054E70/78/80`.
- Consumer: resident `0x8005B12C..0x8005B440`, exact safe-XYZ loads
  `0x8005B1DC/E4/EC` and live-XYZ stores `0x8005B29C/A4/AC`.
- Reset selector: runtime `0x800B3C54..0x800B3D78`, byte-equal to pristine
  `LEVEL03/LEVEL.BIN` offset `0x2B4`; exact safe-XYZ stores
  `0x800B3D24/54/40`, ground query `0x800B3D44` and runtime table pointer
  `0x80096DA4`. Status load/mask/denial branch are
  `0x800B3C64/0x800B3C6C/0x800B3C70`.
- Authored row source: the shipping parser `0x8001CDC0..0x8001D3CC` constructs
  the shared DAT type table at `0x80096DA0`. In cold-boot scene 3, DAT base
  `0x8015E22C` plus type-0x01 file offset `0x458` produces slot-1 pointer
  `0x8015E684`; its 220 bytes match only the pinned `LEVEL03/LEVEL.DAT`
  type-0x01 record. Selected row 6 is file offset `0x4A4`, runtime
  `0x8015E6D0`, raw XYZ `[15678,0,15438]`.
- Scene-10 transition writer: runtime function `0x800B3ADC..0x800B3C18`,
  byte-equal to pristine `LEVEL10/LEVEL.BIN` offset `0x13C`; four exact writes
  install nearest-row scaled X/Z and ground-derived Y while preserving heading.
- Scene-4 transition writer: runtime function `0x800B3C5C..0x800B3CD4`,
  byte-equal to pristine `LEVEL04/LEVEL.BIN` offset `0x2BC`; five exact writes
  install fixed X/Z, heading `2048` and ground-derived Y.
- Scene-6 fixed initializer: LEVEL06 `0x800B3AEC..0x800B3B94` installs fixed
  safe X/Y/Z/heading `[35329,-85228,-154696,3063]`. Its runtime bytes match
  pristine `LEVEL06/LEVEL.BIN` offset `0x14C`; the resident scene selector
  reaches it through JAL `0x8005B194` and returns to `0x8005B19C`.
- Scene-8 fixed initializer: LEVEL08 `0x800B3AE8..0x800B3B54` installs fixed
  safe-and-live values `[-157682,5744,-12845,352]`. Its runtime bytes match
  pristine `LEVEL08/LEVEL.BIN` offset `0x148`; the resident scene selector
  reaches it through JAL `0x8005B1A4` and returns to `0x8005B1AC`.
- Typed state: live XYZ, safe XYZ/heading, shared status bit view, true health
  and lives in the one resident player block.
- Status-gate breadth: mask `0x0010` is causally necessary at the exact
  LEVEL03 and LEVEL10 nearest-row boundaries and LEVEL04 fixed-tuple boundary;
  source, whole-word semantics and general policy stay open.
- Fixtures: centrally hash-pinned LEVEL02, LEVEL05, LEVEL07 pit, Bug Bar and
  scene-6 death movie/state pairs plus the pristine `level_14.sav` anchor,
  plus the existing from-boot LEVEL02 recording and pristine
  `level01_end_of_stage.sav` used to generate a transient game-native
  `LEV02:00` card;
  each consumed fixture is hash-verified and replayed only on mounted pristine
  media.
- Scenarios: `tools/scenarios/duckstation/pristine_checkpoint_respawn.yaml`,
  `tools/scenarios/duckstation/pristine_contact_respawn_safe_anchor.yaml`,
  `tools/scenarios/duckstation/pristine_scene10_pit_respawn.yaml` and
  `tools/scenarios/duckstation/pristine_scene4_pit_respawn.yaml`, plus
  `tools/scenarios/duckstation/pristine_scene10_pit_status_denial.yaml` and
  `tools/scenarios/duckstation/pristine_scene4_pit_status_denial.yaml`, plus
  `tools/scenarios/duckstation/pristine_scene6_level06_respawn_initializer.yaml`
  and `tools/scenarios/duckstation/pristine_scene8_level08_respawn_initializer.yaml`.

## Controls

Positive: the exact recorded input reaches health/lives `4/4` and the
frame-157 selector/consumer reset. Negative: neutralizing only frames 57–87 leaves
health/lives `3/5` and never executes the respawn handler. Causal boundary:
safe-X `+4096` converges both with native updater code and with the three known
updater stores NOPed identically in both branches. At frame 156, changing only
selected row-6 raw X by `+128` changes frame-157 safe/live X by `+4096` under
identical selector/handler coverage. The paired denial changes only
`0x800A6590` from `0x0014` to `0x0004`; selector coverage falls from 400 hits
to a 17-PC pre-store gate/return path, while the resident handler remains
coverage-identical and copies prior safe XYZ `[507900,31787,503976]`. On the
Bug Bar path, changing only fatal
safe X by `+4096` changes first-completed-respawn safe/live X by exactly
`+4096`; Y/Z and health/lives `4/0` remain equal, and both branches have the
same updater, resident-handler and overlay-window coverage.

On the two added pit paths, scene 10 resets live/safe XYZ to
`[-159648,3628,1182816]` and health/lives to `4/0`; scene 4 resets them to
`[727892,9584,165941]` and `4/5`. Changing only their pre-reset safe X by
`+4096` yields zero safe/live X delta one frame later. Identical branch
coverage includes the exact resident safe loads, live stores, health restore
and lives decrement, but excludes continuous safe-XYZ stores. This confirms
transition-path tuple replacement. Complete nontruncated access logs attribute
the four scene-10 writes to `0x800B3BAC/3BBC/3BC8/3BDC` and the five scene-4
writes to `0x800B3C94/3C9C/3CA8/3CB0/3CC4`. Those watches force the interpreter,
so they establish write ownership only; the passive branch pairs remain the
behavioral and timing authority.

The matched status branches reuse those exact pre-reset states and the exact
next recorded frame. Scene 10 denial retains safe/live XYZ
`[-103436,-4903,1209759]` with health/lives `4/0`; scene 4 denial retains
`[744984,4861,139049]`, heading `1965`, and health/lives `4/5`. Their writer
coverage falls to 14 and 13 pre-store PCs respectively, while resident-handler
coverage is exactly equal to each natural control (766/136 and 768/138
hits/distinct PCs). Main-RAM comparison admits only byte `0x800A6590`.

On the scene-6 path, the cycle-neutral target-487 trace has zero initializer
hits and retains safe XYZ `[93783,-83752,-134554]` at health/lives `4/4`.
Target 488 executes 42/42 distinct initializer PCs without truncation and
produces safe XYZ/heading `[35329,-85228,-154696,3063]` while lives becomes 3.
The exact entry has RA `0x8005B19C`, selector `v1=3`, and a runtime body equal
to pristine slice SHA-256 `33b21c83…`. A complete attribution-only log records
the four direct stores. From one transient entry state, suppressing the X, Y or
Z store independently preserves only that old field; changing the heading
immediate from 3063 to 3064 changes heading by one. Every branch returns at the
same cycle/frame/PC/SP boundary, and the transient state is deleted.

On the scene-8 path, the natural cycle-neutral 180-frame trace executes all
27 LEVEL08 initializer PCs and reaches health/lives `4/2`; changing only actor
flag bit `0x0080` changes one RAM byte, prevents damage and yields zero
initializer/respawn hits at the same endpoint. The exact loaded function has
SHA-256 `4b2e8bcc…`. Seven complete direct writes install safe
XYZ/heading `[-157682,5744,-12845,352]` plus matching live XYZ. From one
inspected transient entry state, X-source `+4096` changes safe/live X by 4096,
while heading-source `+1` changes only safe heading to 353. These narrow
interpreter branches share the exact return boundary; the passive trace remains
timing authority.

The current-binary source replay first creates its transient progression card
from inspected pristine `level01_end_of_stage.sav` using native LEVEL01
completion and save UI. The preparation PID is stopped before a second process
cold-boots. With that card, the unedited movie reaches scene 1 because its Left
burst at frames 6307..6315 selects Ant Hill. Removing only those nine Left
samples in memory leaves control and branch equal through frame 6300 and
reaches scene 3 at frame 7600; no derivative movie is saved. Before and after,
mounted media match the pristine CUE/BIN hashes and the transient card is
byte-identical. Runtime DAT base, slot pointer, count, complete record hash and
row-6 hash all equal the unique staged LEVEL03 file slices. This observation
plus the byte-matched parser establishes source ownership; the earlier single-
variable row-6 mutation remains the behavioral causal confirmation.

## Current-binary provenance ratchet

The prior scene-3 run's isolated config contained undeclared completed-game
`LEV15:00/:01` card records and is retained only as historical evidence. The
current generator rejects that dependency. It receipts the pristine state,
fresh-card origin, generated `LEV02:00` marker, card SHA-256
`5ca4ee4e23d76fe4eb596d0fe7766c481dcac456557756734f28c903fa242d4c`,
both exact owned-PID cleanups, the unedited scene-1 control, the unsaved edit
window `[6307,6316)`, semantic movie SHA-256
`8ad070c7d00135e6f48956819a8b73669203691145139edb1db5f4c635389e47`
and the scene-3/DAT endpoint. The retained artifact is
`analysis/phase4_respawn_row_provenance.json`, SHA-256
`d1d408b1cdf0a9dd05337cb1bc6839678256462cc63485275478724d27996947`.
Its retained reproduction is the dedicated two-process declarative scenario
`tools/scenarios/duckstation/pristine_c15_authored_row_provenance.yaml`,
SHA-256 `81dc60f669be9dfac82f34d9816401398e58d720de0a308a62d064db26a1da9f`.
The current checkpoint root is SHA-256
`51f953c286482d3408ff85e89a26bbd2a1f7749b250e81cfc0672ce398c2a53e`;
the joined writer catalog is
`c6a23f40484bd8b7a3905a0bdf9fbf9dd46bdaea0292b2a3c4083a51dfb0120e`.
The exact denial scenario
`tools/scenarios/duckstation/pristine_c15_authored_row_denial.yaml` has
SHA-256 `03d06a3187229cb948d51d9a838a7d3a81d4715472b551ce77aa76b8f0f0f582`
and passes 19 assertions. This strengthens source/selector provenance but does
not change campaign status.

The focused status-policy artifact is
`analysis/phase4_respawn_status_policy.json`, SHA-256
`d2776352bc0b7e6e0922d882ec97e2a69f615e60eeae0568d33961d8224daa95`.
Its two 22-assertion scenarios have SHA-256
`a3a9e779e1bbf1f65b8d6ce2eea2b78de5e582fac0052b212deb85a0d7b9bd30`
and `c30a7bdc51f68b1fc10455ee7716358d172001134ee7583d178f5cf1660a4725`.
The current fork is `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; the
running binary is SHA-256
`91cbe22b2c2e22ad83d695988ada36bbabb22c65366cb5ec9e8e30784de93af6`.
Mounted and embedded save media were reverified as pristine, no transient
state/movie bytes were retained, and only the config-owned PID was stopped.

The 52-capsule preservation extension did not replay or rewrite this historical
live counterfactual. Generated
`analysis/phase4_capsule_consumer_reconciliation.json` reruns the exact pinned
reader over both relevant E10 capsules, proves both typed RAM query sets and
their manifest/tree identities unchanged, and updates only the offline capsule
lane plus its source hashes. The retained live payload and original generator
identity remain exact historical provenance.

## Open work packages

- Trace the source and general activation policy of player status mask `0x0010`.
- Reproduce an indirect/additional writer and its activation/denial boundary.
- Reuse relevant actor, scripted and exceptional death recordings to widen
  death-class breadth without inheriting their hazard-family semantics.
- Reproduce initialization, death, scene reload, save/load and frontend reset.
- Cover representative stages and exceptional paths.

## Handoff

Next experiment: trace the writer/source of player status mask `0x0010`,
including its setter/clearer and whole-word policy, or reproduce an indirect
writer. Then reuse an existing relevant actor or
scripted-death recording. Do not request a new operator movie until the
existing movie tree has been inventoried again.
