---
kind: experiment
id: EXP_2026-07-15_phase4_props_movers_catalog
name: Phase 4 E08 pass-table and mover catalog
date: 2026-07-15
status: reproduced_partial
confidence: confirmed_with_open_consumers
source_state: original_game
system: SYS_pass_table_props_and_movers
artifacts: [analysis/phase4_props_movers.json, analysis/phase4_e08_outcome_join.json, analysis/phase4_e08_operator_contacts.json, analysis/phase4_e08_hazard_outcomes.json]
---
# Phase 4 E08 pass-table and mover catalog

## Question and falsifiers

Can E08 replace its legacy 13-fixture survey with an exhaustive pristine DAT
census and reproducible render/mover/lifecycle controls without pretending the
switch, gate, contact, and persistence policy is solved?

The work would fail if any pinned DAT escaped the walker; an opcode or exact row
count drifted; a visual edit also changed collision/player state; a pass-3
anchor negative crossed the cull boundary; actor breadth stopped at the first
zero slot; state loads lacked media inspection; or cleanup did not stop the
exact owned PID.

## Provenance and method

Static authority was only the hash-pinned pristine executable and all 21 staged
`LEVEL*.DAT` files. `python3 tools/build_identity.py --verify` reported 327/327
inputs matching. ALLMODS was not an input or original-game authority. No disc
was built or modified.

The retained live run used external-debugger fork revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, release binary SHA-256
`c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
fresh config `/tmp/abl-p4-e08-i2-final2`, dedicated loopback port 19928, and the
hash-verified pristine CUE/track. The startup wrapper recovered an
exec-before-inspection race only after proving one exact config owner. The
generator later stopped PID 2528356 owned by that config. The ephemeral token is
not retained.

After the richer E08 binding made the two table-pointer globals visible to the
Phase-3 ownership audit, a separate fresh reconciliation run used config
`/tmp/abl-p4-i2-phase3-lifetime`, port 19929, and the same hash-verified pristine
CUE. It measured `0x800824AC` and `0x80082508` as resident-RAM `u32` state written
by the DAT parser: each read zero before the scene load and a distinct nonzero
scene pointer afterward, so both initialize from level data and reload at scene
transition. The lifecycle generator stopped exact owned PID 2563550; the
ephemeral token is not retained.

Before each save load, `emulator.getStateInfo` verified the centrally declared
strict-pristine fixture and compatible mounted media. Every exec trace was
re-armed after the load. Cold-boot evidence separately replayed the v3 from-boot
LEVEL01 movie through frames 8,550–8,580.

```text
python3 tools/phase3_duckstation_rpc_manifest.py --check
python3 tools/build_identity.py --verify
python3 tools/verify_repro_inputs.py
python3 tools/phase4_props_movers.py --port 19928 --token <ephemeral> \
  --config-dir /tmp/abl-p4-e08-i2-final2 --instance-state recreated
```

## Observations

- Static: 21 DATs, 9,097 pass-1 rows, 1,684 pass-3 rows, exact parser/culler/
  initializer/mover region hashes, 10,779 in-file source pointers, two external
  source pointers, 10,667 in-file nested payloads, and 114 external/unresolved
  payload cases.
- Cold boot: movie `reproducible=true`, `truncated=false`, playback index 8,580,
  and scene 1 before and after the bounded window.
- Breadth: 19 anchors, 16 scene IDs, actor IDs `1..41`, ten per-actor mover
  callbacks, and 13 naturally moving anchors.
- Pass-1 control: record `214 <- 117` changed 2,872/114,464 pixels.
- Pass-3 positive: class-wide LEVEL01 bitmap clear changed 5,938 pixels.
- Pass-3 negative: visible record 61 X `122 -> 154`, visible on both branches,
  changed zero pixels.
- All three render controls left collision-sector hashes and player positions
  equal.
- Pause flags were `1,1,0`; paused/frozen actor hashes matched; resume produced
  eight mover callbacks.
- LEVEL01 -> LEVEL02 -> LEVEL01 rebuilt the first world identically and kept the
  middle scene distinct.
- The registry reconciliation owns `0x800824AC` as
  `original.pass1_instance_table_pointer` and `0x80082508` as
  `original.pass3_cull_table_pointer`; fresh lifecycle evidence classifies both
  as scene-reloaded rather than silently leaving Canon-only addresses.

## Failed hypotheses and corrections

- The development binary was assumed to expose the full source-manifest API;
  runtime rejected `debugger.capabilities`. That instance was cleaned up and the
  separately pinned release binary was used.
- A per-actor callback and then the outer mover updater were expected in one
  arbitrary cold-boot frame. Both zero-hit windows were retained as rejected
  timing assumptions; mover execution is proven across fixed save-state windows,
  while cold boot proves table/media identity.
- Two-frame displayed-buffer branches produced zero visual delta. The retained
  controls use the legacy experiment's 20-frame phase match.
- The old fixture pairing targeted the big-berry view and invisible pass-3
  record 56. The retained pass-1 control uses the centrally pinned acorn view;
  pass-3 positive control clears the complete active bitmap.
- Moving visible record 61 onto the player changed 124 pixels because it crossed
  a cull boundary. The accepted negative nudges X by 32 and requires the record
  to remain visible on both branches before accepting the zero-pixel result.
- The visible list was first treated as pass-3-only and terminated on the first
  non-pass-3 pointer. It is a shared mixed list; the corrected census filters all
  bounded entries and deduplicates aligned pointers into the pass-3 table.

## Result and next experiment

E08 now has an exhaustive pass-table census and reproduced render, actor breadth,
pause, cold-boot, and scene-ownership controls. It remains active because no
experiment yet maps every relevant source/actor class to native switch/gate/
mover contact outcomes or follows authored state through denial, success, death,
checkpoint, reload, and save/load.

The named source/actor clustering step is executed in the extension below. See
[[SYS_pass_table_props_and_movers]] and
[[Game Solving Campaign - Props Movers Switches and Gates]].

## 2026-07-16 source-cluster extension

The next experiment first re-inventoried all 110 files under `movies/Phase4`
and all 147 files in the broader movie tree. No filename supplied a dedicated
E08 movie/state pair. The existing centrally pinned `wooden_fence.sav` and
`offering_stone_and_ramp.sav` controls were therefore consumed alongside the
19 breadth anchors instead of requesting duplicate operator work. Each state
was inspected as pristine `SCUS-94288` before load.

The generator now follows every live actor `+0x80` backlink and decodes the
initializer-consumed `0x1C` source record without retaining copyrighted bytes.
All 605 observations matched source actor ID to live actor ID. The stable type
word `(source[0x0D] << 8) | source[0x0C]` produces 54 behavior classes and 283
authored variants across all 41 IDs, 37 naturally observed selectors, and ten
nonzero callbacks. Independent machine evidence owns seven type-word classes
through seed/Dot/Thumper/Thud actor IDs; 47 remain explicit candidates.

The first fresh run in config
`/tmp/abl-phase4-i3-e08-clusters-20260716-19931` correctly failed its new guard:
the proposed count 502 omitted the 103 bonus-anchor actors. The full retained
19-anchor sum is 605. Cleanup stopped exact owned PID 3476939. A second run
proved 283 stable authored signatures, but that was too fine a trigger frontier;
it was superseded by the native type-word behavior key and stopped exact owned
PID 3477197. The final retained run used fresh config
`/tmp/abl-phase4-i3-e08-clusters-final-20260716-19933`, dedicated port 19933,
the same 203-method/88-dirty-path fork and release binary hash, and stopped exact
owned PID 3479386.

The two focused controls both loaded scene 1 with 484 pass-1 rows, 140 pass-3
rows and 32 actors. Their 20-frame mover-entry traces returned zero and four
events. This disproves neither mover execution nor interaction; the filenames
remain visual leads until a native trigger changes typed state or outcome.

Retained artifact SHA-256:
`dd1fbe1d9c64805697cbc2ded6cd1b265ec0eb2609ff555ed9a878531df7bc10`.
The campaign stays active. The next experiment selects one native trigger per
unowned type-word class and captures overlay-qualified outcome writers through
denial, success, death, checkpoint, reload, and save/load.

## 2026-07-16 native contact cross-evidence extension

Iteration 4 again inventoried all Phase-4 and broader operator movies before
choosing work. No new fixture was needed for this step. The completed A04, A05,
and A06 artifacts already retain stronger low-level native controls on the
current 203-method fork and release binary; replaying them merely to create a
new trace would violate the run context's no-redundant-live-work rule.

`python3 tools/phase4_e08_outcome_join.py` instead recomputes a deterministic
cross-evidence join. For every A04/A06 representative it requires identical
save, compact-table index, actor address, ID and flags; follows the E08 actor
`+0x80` backlink; checks the source type word; attaches the exact decoded E07
selector program; and derives the native outcome from raw before/call/after
fields. Every `debugger.callFunction` row returned from `0x8004ABF4` to its
paused trap on pristine `SCUS-94288` within one emulator frame. All 28 rows
joined, with no missing or ambiguous actor/source identity.

The retained partition is 20 ordinary neutral-damage/kick-response rows, three
response-only rows, two `0x20` separate-path rows, and three `0x800` suppressed
rows. These represent 22 type words. Eighteen of the 47 unowned E08 candidates
now have direct native contact controls; 29 do not. The independent A06 timer-12
trials select neither target response -20 nor 30 for all 28. An initially
over-strong implementation also required health 4 after A06; raw type-`0x080F`
evidence correctly falsified that assumption because a slide can remain
non-offensive to the target while ordinary contact damages the player. The
accepted guard now states only the reproduced no-offensive-target result.

A05 contributes one natural causal branch. Type `0x0109` at actor
`0x800A0014` reaches response -20, streak 1 and health 4 with slam window 1.
Changing only that window to 0 at movie frame 124 yields response 15, streak 0
and health 3 at the same frame 128/cycle 5287761987. This routes an observed
consumer without turning an operator filename or generic contact law into a
species or final ownership claim.

Retained artifact SHA-256:
`437559dfca4db3005784f5db0f65c62c321b767ae0657cf959709bbcdbe2c632`.
Representative low-level mutation tests flip the raw A04 response and the E08
source-ID match and require the generator/guard to fail. E08 remains active.
The next experiment prioritizes the 29 no-contact classes by callback,
movement and decoded VM signature, then captures one native outcome writer per
relevant class before ownership or persistence claims.

## 2026-07-16 cycle-neutral operator-contact extension

Iteration 5 recursively inventoried all 110 files under `movies/Phase4` and all
147 files in the broader movie tree before choosing work. Five existing
Phase-4 contact movie/save pairs were relevant leads, so no new operator fixture
was requested. All ten external files are centrally source/path/hash/size
pinned; the operator-owned bytes remain outside Git. Before each state load,
`emulator.getStateInfo` verified pristine `SCUS-94288` save media and the helper
verified the mounted pristine CUE/track.

The first implementation advanced the replay one debugger frame at a time. Its
D08 final RAM hash differed from a continuously advanced control, so that
instrumented run was rejected. The replacement starts every probe from the
same inspected anchor and uses `movie.traceToFrame` for both control and
instrumented branches. A binary search locates the first stable typed outcome;
all retained branch comparisons have equal cycles and final RAM hashes. A
second rejected assumption expected an active movie frame at the exact movie
length; retail playback instead becomes inactive and reports frame/index zero
at that boundary, so the guard now accepts that reset only when the requested
target equals the declared frame count.

The retained run used fork revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, release binary SHA-256
`c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
fresh config `/tmp/abl-phase4-i5-e08-operator-contacts-corrected-19944`,
dedicated port 19944, and an ephemeral token. Cleanup stopped only
config-owned PID 3990636.

Four replays produced stable typed actor boundaries: `0x0F06` at movie frame
426, `0x0C13` at 437, `0x060C` at 343, and `0x0B11` at 400. Only `0x060C` was
absent from the prior 18-class native-contact partition, so the aggregate
frontier advances to 19/47 controlled and 28 without a native outcome control.
The complete D11 mite replay changed player health `4 -> 3` but produced no
stable typed actor boundary. It remains negative evidence against assigning a
role from the filename. No replay promotes a species, D-row owner, final E08
owner, interaction writer, or persistence law.

Retained artifact SHA-256:
`86f51bef5a309f1e7e631df6db04a65e9ef75e423a389464bdb31d1ce1847762`.
Low-level mutation tests erase a boundary, break trace neutrality, and alter the
derived partition; each turns the guard red. E08 remains active. The next
autonomous experiment targets the 28 remaining classes and the still-open
authored switch/gate state, denial/success, writer and persistence boundaries.

## 2026-07-16 cycle-neutral E10 hazard-lead extension

Iteration 6 again inventoried all 110 files under `movies/Phase4` and all 147
files in the broader movie tree before selecting work. Eight existing E10
movie/state pairs covered recorded acorn, falling-rock, falling-spike, goo,
ground-bird and pit leads across five campaign levels, so no operator recording
was requested. None was already in the central fixture intake. A load-free
inspection run first verified each save as valid version 84 with embedded
pristine `SCUS-94288` media while the mounted CUE/track matched the retail pins;
the inspection config then stopped only its owned PID 4717. All 16 external
files were source/path/hash/size/media-class pinned and provisioned without
tracking their bytes.

The retained run used current fork revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, 203-method capability manifest,
release binary SHA-256
`c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
fresh config `/tmp/abl-phase4-i39-e08-sourcefinal-YZRwRM`, dedicated port
20681 and an ephemeral token. Each complete replay used
`movie.traceToFrame` from its inspected anchor with resident actor/contact,
damage/immunity and Region-A ranges. Control and passive cached-block branches
matched RAM, registers, cycles and frames; all 24 range results were
untruncated. Cleanup stopped exact config-owned PID 94221.

```text
python3 tools/phase4_e08_hazard_outcomes.py --port 20681 \
  --token <ephemeral> \
  --config-dir /tmp/abl-phase4-i39-e08-sourcefinal-YZRwRM \
  --instance-state recreated
```

All eight movies produced a player health or lives outcome: acorn health
`1 -> -1`, rocks `4 -> 3`, spikes `1 -> 0`, goo `4 -> 2`, ground bird lives
`4 -> 3`, and the three pit leads lives `5 -> 4`, `1 -> 0`, and `6 -> 5`.
Coverage retained 8,056,072 actor/contact/update hits, 1,376,684 damage/
immunity hits and 4,038,407 Region-A hits. No final replay had a stable typed
actor retirement, response decrement or state -20/30 boundary. This falsifies
the assumption that these E10 filenames could directly supply any remaining
E08 actor-class control. It does not prove that no actor participates earlier
in a replay and does not assign a hazard writer or E10 owner.

The machine artifact is `analysis/phase4_e08_hazard_outcomes.json` SHA-256
`8ba145c10ab65701fd3aa89dd7ce064400a73cbbeb267f74b05040a14beae3ff`;
generator SHA-256 is
`d4f45f101305168861f66c202d39f6ef53b2da33a6f4c3b747f07c7fa9b93ae0`.
Mutation tests alter a player delta, trace-neutrality leaf and owner count; each
turns the guard red. E08 remains 19/47 outcome-controlled with 28 uncontrolled.
The next E08 experiment must use a native class-specific trigger or capture an
earlier typed boundary rather than reusing these eight final-state negatives.

## 2026-07-17 Event-VM dependency refresh

The accepted date-bound E07 replay changed the exact input hash consumed by the
static outcome join. The dependency chain was regenerated in order rather than
editing retained source pins: `phase4_e08_outcome_join.py`, then operator
contacts on fresh config
`/tmp/abl-phase4-i23-e08-operator-refresh-20344.WS7WqT`/PID 282617, then hazard
outcomes on `/tmp/abl-phase4-i23-e08-hazard-refresh-20345.PhtfVj`/PID 282765.
Both live generators reverified mounted/save media, reproduced their existing
behavioral predicates, and stopped only their owned PIDs. Current SHA-256 values
are join `cb67211158e254bde78617c340a6c6ba48a4349cf92ae5b65a145fb3dd15ad1c`,
operator contacts `1650f7affb3c76a9dcbb36d2c57dc6eddfdc7a79c410059535153f6bd1cfd6ad`,
and hazard outcomes `614e7c7d32e52b3cde87687aa9eb6748af4bf91ef24a70b315f5156eef11e5de`.
No E08/E10 ownership, species, persistence, or completion claim changed.
