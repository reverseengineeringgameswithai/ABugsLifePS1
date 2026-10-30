---
kind: mod
id: MOD_native_blender_level_layout_export
name: Native Blender level-layout export pipeline
status: gate_a_accepted
created: 2026-08-10
updated: 2026-08-10
confidence: high_within_gate_a
source_state: mod
src_paths:
  - templates/g3_native_ready_replacement.blend
  - tools/abl_blender/export_g3_native_profile.py
  - tools/abl_blender/export_native_terrain_semantics.py
  - tools/g3_native_replacement_build.py
  - tools/native_mesh_codec.py
  - tools/native_terrain_export.py
  - tools/native_terrain_semantic_compiler.py
  - tools/heightfield_collision.py
  - tools/build_g3_native.py
  - tools/g3_native_gameplay_objects.py
  - tools/validate_g3_native_preflight.py
  - tools/scenarios/duckstation/g3_ready_replacement_objects.yaml
related:
  - MOD_g3_p74_ready_replacement_blender
  - MOD_g3_native_anchor_alignment
  - MOD_g3_visual_collision_coverage_boundary
  - EXP_2026_07_11_LEVEL01_native_terrain_reverse_engineering
  - EXP_2026_08_03_phase4_e01_terrain_visual
  - EXP_2026_08_04_phase4_e02_collision_roundtrip
  - EXP_2026_08_03_phase4_e03_ot_packet_census
  - SYS_render_collision_source_separation
---

# Native Blender level-layout export pipeline

## Decision

New level layouts will be authored in Blender and compiled into the original game's
native level formats. They will **not** use the Track-A SM64/Fast64-style custom
triangle renderer or custom collision engine.

The runtime architecture is:

```text
Blender scene
  -> native LEVEL.DAT node records and mesh payloads
  -> FUNC_80010000 / retail GTE and ordering-table renderer
  -> matching LEVEL.RAW collision sectors and plane groups
  -> pristine-base disc build
  -> cold-boot movie validation
```

The goal is a completely new playable layout inside an existing scene slot, not a
marginal deformation of the retail layout. The level may have a new route, terrain,
spawn, goal, elevations, object placement, enemies, and objectives while retaining
the original engine, player controller, camera, renderer, actors, and shell.

This note is the working contract for that pipeline. It supersedes any suggestion
that new layout work should extend `mod/caves/tier3_otrender.c` or
`mod/caves/tier3_collision.c`.

## Evidence versus intended behavior

### Confirmed

- The visible LEVEL01 terrain is supplied by `LEVEL.DAT` payloads consumed by
  `FUNC_80010000` and is separate from collision.
- The native mesh payload codec supports byte-exact decoding and re-encoding.
- Blender-authored height changes have rendered through `FUNC_80010000` and have
  been followed by matching native collision.
- Native payloads can be appended and their source records repointed.
- Phase 4 E01 found primary 0x18-byte node-record runs across all 21 campaign DATs.
- Phase 4 E02 reproduced the collision source-to-runtime conversion with zero field
  mismatches across all 16 scenes.
- Phase 4 E03 established the 1,228-bucket ordering table and representative retail
  packet counts needed for future layout budgets.

### Gate-A candidate now implemented

- One export produces the visual DAT, collision RAW, gameplay placements, build
  manifest, and validation inputs from the same authored source.
- The exporter treats `abl_g3_role` as authoritative, preserves the declared
  `runtime_preview_v2` coordinate contract, and rejects unsupported or ambiguous
  roles, incomplete grids, duplicate X/Z samples, unapplied terrain transforms, and
  native-coordinate overflow.
- The frozen starter exports a 97×161 native heightfield, Spawn/Marker/Goal, 24
  native objects, and two approved donor actors. Its roster is exhaustive: omitted
  supported native slots are parked and omitted retail actor slots are cleared.
- The protected wrapper compiles matching visual DAT and collision RAW, verifies the
  pristine retail tree, enters the consolidated module-matrix build, and emits the
  standard build manifest.
- The exact candidate disc has passed a cold boot and timing-matched input movie with
  terrain, collision, gameplay-object, actor, marker, goal, and no-Track-A assertions.

### Intended, not yet promoted

- A designer can create a genuinely new route in one `.blend` file without
  preserving the retail route or retail terrain shape. This is Gate B, not a claim
  established by the frozen Gate-A starter.
- Layout payload partitioning, node anchors, collision-sector assignment, and native
  representability checks are automatic rather than hand-authored offsets.
- General camera/performance closure and arbitrary topology remain deferred.

## Blender authoring contract

### Scene collections

The target scene has these logical collections:

- `G3_Terrain` — native visual terrain and collision source;
- `G3_Controls` — `Spawn`, `Goal`, and optional route-validation markers;
- `G3_GameplayObjects` — native pickups and supported interactive objects;
- `G3_Enemies` — supported actor donor/placement records;
- `G3_VisualOnly` — non-walkable banks, skirts, or coverage geometry when supported.

The collection names are organizational. Export eligibility must be determined by
explicit `abl_g3_role` / `abl_type` properties, with recognized names retained only
as a convenience.

### Coordinates

Use the `runtime_preview_v2` contract:

```text
Blender X = runtime X / 256
Blender Y = runtime Z / 256
Blender Z = -runtime Y delta / 256
```

Blender Z is up. All exported coordinates must round-trip to exact native integer
units. The exporter must reject ambiguous scale, unapplied transforms, duplicate
heightfield X/Z nodes, and coordinates outside the selected native representation.

### First supported geometry class

The first production target is a native heightfield-style outdoor layout:

- completely new terrain heights and route;
- mild and moderate ramps;
- broad hills, valleys, plateaus, and static platforms that remain representable by
  the native payload and collision formats;
- a new spawn, goal, pickups, and enemy placement;
- no requirement to preserve the retail path.

This is a content constraint, not a new-engine constraint. The renderer remains the
retail GTE path.

### Deferred geometry classes

Do not silently accept these until their named gates pass:

- visually clean open-bottom pits;
- arbitrary vertical barriers and cliffs viewed from below;
- caves, overhangs, or stacked floors;
- broad free-roam footprints outside the validated native coverage envelope;
- arbitrary pass-2 moving geometry;
- geometry that exceeds the measured native primitive/timing budget.

## Export products

Every export must produce a mutually bound set:

1. `*_surface.json` or the successor typed Blender scene document;
2. `*_profile.json` with source `.blend` hash and coordinate contract;
3. replacement `LEVEL.DAT` containing the native node/payload geometry;
4. replacement `LEVEL.RAW` containing collision and supported actor data;
5. an authoring report naming every payload, node anchor, collision sector, material,
   object, warning, and limit;
6. a build manifest proving the pristine input image and exact staged files;
7. a cold-boot validation report tied to a pinned input movie.

Visual and collision outputs must come from the same Blender source and source hash.
An output is invalid if only one side was regenerated.

## Intended designer loop

The eventual supported loop is:

```bash
# Make a working copy; never edit the frozen template in place.
cp templates/g3_native_ready_replacement.blend build/MY_NEW_LEVEL.blend

# Edit and save build/MY_NEW_LEVEL.blend in Blender.

# Export and validate without authoring a disc.
python3 tools/g3_native_replacement_build.py \
  build/MY_NEW_LEVEL.blend \
  --work-prefix build/MY_NEW_LEVEL \
  --out build/ABL_MY_NEW_LEVEL \
  --prepare-only

# After the preflight is clean, build a new output from the pristine base.
python3 tools/g3_native_replacement_build.py \
  build/MY_NEW_LEVEL.blend \
  --work-prefix build/MY_NEW_LEVEL \
  --out build/ABL_MY_NEW_LEVEL
```

These commands are the implemented Gate-A interface. They are still a diagnostic
authoring lane, not a production release or proof of a genuinely new Gate-B route.

## Initial blockers found on 2026-08-10

This is the historical rejection snapshot. The implementation log below records the
repairs and the remaining limits.

### 1. Ready-replacement Empty export is incomplete

`templates/g3_native_ready_replacement.blend` contains gameplay and enemy Empties,
and `tools/g3_native_replacement_build.py` expects `level_meta.native_objects` and
`level_meta.actors`. The current committed `export_g3_native_profile.py` exports
terrain plus Spawn/Goal/Marker but does not populate those two lists.

Required repair: make roles/properties authoritative, export both lists, test empty,
partial, exhaustive, overflow, unsupported-kind, and off-surface cases, and prove the
wrapper consumes the exported rows.

### 2. Authoring tests are not green

The focused native/Phase-4 check on 2026-08-10 produced 47 passes and 4 failures:

- `native_terrain_export` does not provide the `_slope_gouraud_attr` interface used
  by the ready-replacement shading test;
- `native_terrain_semantic_compiler` calls `heightfield_collision.quad_records`, but
  the helper exposes only `quad_record`.

The compiler/exporter contract must be repaired deliberately; do not add aliases
without deciding whether one quad should emit one native quad record or two triangle
records for non-planar collision.

### 3. Semantic layout compiler is investigation WIP

The semantic lane can already describe explicit target payloads, anchors, walkable
quads, visual-only faces, collision sectors, appended/repointed DAT payloads, and a
bottomless boundary. It still relies on hand-selected native payload offsets and is
not integrated into the ready-replacement wrapper.

Required repair: turn explicit offsets into a reviewed intermediate representation,
then add automatic payload partitioning/anchor assignment with native bounds checks.

### 4. Pit and lower-screen coverage is unresolved

The open-bottom collision behavior falls, dies, and respawns correctly, but authored
GTE geometry does not yet provide a universally clean replacement for the retail
lower-screen terrain coverage. Horizontal coverage reads as false ground or an
overhead slab; narrow vertical banks leave uncovered rays.

Do not promote pits as production-ready until the coverage primitive and backdrop
policy have a causal cold-boot proof.

### 5. Native performance budget is not yet enforced

Retail frames provide representative packet counts, but there is no exporter limit
that maps authored payload density to a validated 30 fps envelope. The V18 experiment
with about 2,200 visual quads changed cold-boot timing enough to invalidate the pinned
comparison frame.

The exporter must report total/visible primitives, payload counts, expected OT load,
and a conservative warning/error threshold. Runtime validation must record primitive
cursor high-water, GP0 family counts, GPU/DMA waits, and gameplay cadence.

## Implementation plan

## Implementation log — 2026-08-10

### James hard-truth review 1: REJECTED

The first verifier review rejected the lane even though build identity passed
327/327. The rejection was correct. The frozen template exported at 32 times the
intended horizontal scale, dropped all 24 gameplay objects and both actors, omitted
its preflight flags, called two missing collision/shading interfaces, and reached the
legacy direct autolayout builder with unconditional `--force` instead of the protected
consolidated build.

### James hard-truth review 2: REJECTED

James independently verified the R4 hashes, 38-file build closure, embedded bytes and
output LBAs, real frozen-template 0/0 preflight, 24+2 roster, focused/build/layout
gates, and 7/7-trigger 30/30-assertion runtime receipt. He still rejected Gate A on
two executable fail-closed gaps:

1. moving one terrain vertex by 0.03125 Blender unit (0.25 native file unit) still
   exported because terrain X/Z used the rounding path without `require_exact`;
2. `tests/test_ps1_scenario_identity.py` failed because the runner never queried
   authenticated `debugger.capabilities`, so hashing the expected on-disk binary did
   not prove which executable/schema served RPC.

The terrain converter now has one mandatory exact-grid vertex call with a documented
`1e-4` native-unit float tolerance. James's mutated `.blend` exits 1 and produces no
profile/surface. The starter itself was migrated from its preserved `.blend1` backup
by snapping only horizontal terrain nodes; authored heights, controls, 24+2 roster,
and exported dy range remain unchanged. Future starter generation creates exact
integer-native nodes directly.

The scenario runner now calls `debugger.capabilities` as its first RPC after
authentication, verifies `/proc/self/exe`-backed SHA-256/path against the launched
binary, verifies declared method count against the complete inventory, checks every
required scenario/cleanup method and method schema, and retains API/source/binary,
method names, schema coverage, and a canonical method-schema hash in the receipt.
The receipt also hashes the scenario YAML itself.

The executable rerun of James's Blender falsifier used his copied scene at
`~/.var/app/org.blender.Blender/cache/james_offgrid_surface.blend` and the
normal exporter entry point. It exited 1 with:

```text
G3NativeReadyReplacementTerrain vertex 0 x=-8208.750000000 is not on the exact
native export grid (tolerance 0.0001 native unit)
```

The isolated output directory contained only Blender stdout/stderr; neither requested
JSON product existed. The regression reproduces the same 0.03125-Blender-unit
(0.25-native-unit) displacement in `tests/test_g3_ready_replacement.py`.

### James hard-truth review 3: ACCEPTED

After the R5 pristine build, exact-grid Blender falsifier, authenticated runtime
capability guard, cold-boot receipt, and final protected regression gates were handed
back for independent review, James issued the exact verdict **ACCEPTED** on
2026-08-10.

This accepts Gate A: the frozen Blender-to-native authoring/build lane and its
fail-closed evidence contract. It does not accept or imply Gate B. A genuinely new
route still needs its own `.blend`, matching visual/collision output, and complete
driven-path proof without retained retail route ownership.

### Refactor completed so far

- `export_g3_native_profile.py` now reads and validates the declared coordinate
  mode. The real frozen template exports through `runtime_preview_v2` at native
  file-space scale.
- Explicit `abl_g3_role` is authoritative. Supported native objects and LEVEL01
  donor-backed actors are exported with stable names, coordinates, floor/float
  intent, exhaustive flags, and rejected ambiguity/unsupported identifiers.
- Spawn, Marker, and Goal now obey that same rule: an explicit control role may use
  any designer-facing object name, while the historical control names are only a
  convenience. Conflicting name/role and control kind/type properties are rejected.
- The real frozen template now exports a 97×161 rectangular surface, 24 native
  objects, 2 actors, authoritative exhaustive rosters, and the intended sink/max-step
  flags. Its Blender-inspected preflight passes with zero errors and zero warnings.
- Non-planar collision quads now deliberately compile into two native triangle
  records along the BL-to-TR diagonal. Plane Y edge vectors are reconstructed from
  the encoded normal for byte-format inspection.
- The optional slope helper now uses runtime X/Z units; the ready template generator
  no longer enables slope tint by default. Neutral `0x808080` remains the safe
  material default, avoiding the earlier false yellow patch.
- Empty exhaustive actor rosters now clear retail chunk-31 actor slots instead of
  silently retaining them.
- The wrapper verifies pristine identity before preparation, binds profile and
  surface hashes to the same `.blend`, and prepares matched DAT/RAW assets without
  invoking a disc builder.
- The direct `build_autolayout_disc.py --force` route was removed from the wrapper.
  Final discs now go through `mod/build.py`, its module matrix, pristine-tree/output
  guards, staged-file restoration, embedded-byte verification, and standard
  `.build_manifest.json` provenance.
- The active stager no longer writes an `ALLMODS`-named report or runtime label. It
  emits a build-prefix-specific generic Track-B report, and the wrapper binds that
  report hash. This removes a misleading historical name from a build that never
  reads ALLMODS or any derivative image.
- A stale collision helper dependency found by the real prepare run was repaired:
  the sector-array offset is derived from chunk 32 after every size-changing block
  splice rather than assuming the pristine fixed offset.

### Current executable evidence

```text
build identity: PASS 327/327
focused authoring/compiler/scenario tests: PASS 30/30
protected-build tests: PASS 16/16
hook/cave layout validator: PASS
git diff --check: PASS
real frozen-template Blender inspection preflight: PASS, 0 errors, 0 warnings
real frozen-template protected disc build: PASS
prepared roster: 24 native objects, 2 actors; remaining retail supported slots parked/cleared
Track-A renderer/collision modules: not selected
cold-boot timing-matched scenario: PASS, 7/7 triggers completed, 30/30 assertions
authenticated runtime contract: PASS, running binary bound and 221/221 RPC schemas inventoried
off-grid Blender falsifier: PASS, exporter exit 1 and no profile/surface emitted
```

The accepted Gate-A candidate is under `build/g3_gate_a_candidate_r5_*`; generated
disc/runtime evidence is not for commit. James independently accepted this R5
refactor. Gate B remains separate and unclaimed.

### Frozen-source and output binding

The protected build command was:

```bash
python3 tools/g3_native_replacement_build.py \
  templates/g3_native_ready_replacement.blend \
  --work-prefix build/g3_gate_a_candidate_r5 \
  --out build/ABL_G3_GATE_A_CANDIDATE_R5_20260810
```

Key SHA-256 bindings:

```text
frozen .blend       4782361f4e1cf6708915f5e6d5f1367c5cf5015d7bbe226df927b5380bbdb5e3
profile             9f9c1cb2de7616384b09df711632893d984cfeb032da85117ebee05bdde8a6ef
surface             69a21eb71decd4e7d2ea2fdb34feede657256238a316d1e8140df1c059086f37
authored roster     b786cf8efa27e306ad00bc9035720e997749c4e2d9aaa9eae4814a82b8628b59
replacement DAT     9b6ad6f94083d92a3ef0f7bb2d6b91a1c9e0695e73377c8be67fc674944002a3
replacement RAW     1efa2ad0999a4d15a7f12ee3971fdcea3e25941871d3dfa8ccd554f0e4df0edc
preflight report    5464fffdcc30820d2e146630b7a863db0a74c230c2cb8d84f92541c23574d22c
module manifest     5c5e259e88044d4edee35a99bbcf64d94cdb5867b816c561757e93cfaf67a2ec
stager report       1e6b6e21e2488b7d862f2609c556245d5b956648cd49616864e94af27bdd92ed
disc BIN            b0f72baf913994fa498eb31f69ceff73daad76f4b6bc5a26dac370919ce334e9
disc CUE            2ee411cc74f22aed1bddfcca0a5f8ac5ec368c071cbdfb8e8b4c0e009e02884b
build manifest      d6dce0ef6aaa327a7df4b0b39096229a0880ab73fc864493ea9cc0721195579d
wrapper report      c083432033b869ae95d5eb9658655bf74af5431ea418229e4ed1bc7a12c09a34
```

The real Blender export reports `runtime_preview_v2`, Spawn file coordinates
`(6159, 15403)`, a 97×161 grid with runtime delta-Y range -15507 through 11218,
the complete authored roster, and zero preflight errors/warnings. The standard build
manifest names the pristine input pins, every staged pristine/patched file hash,
the `g3-native-replacement-only` module combination, authoring/compiler source hashes,
toolchain versions, and final BIN/CUE hashes. Neither ALLMODS nor a derivative disc
appears in the build path.

For the size-changing auto-layout build, the manifest records the verified output
LBAs rather than the pristine-layout addresses: LEVEL01 DAT is at 2907 and RAW at
3071. Its 38-file hashed closure includes `mod/build.py`, `build_identity.py`,
`validate_mod_layout.py`, `build_baselines.json`, and the actual
`REBUILD/abl_autolayout.xml` in addition to the Blender/compiler/stager sources.
The R5 post-build audit found all 38 sources present with zero hash drift.

### Phase-4 capsule-first disposition

The retained Phase-4 capsule index was checked before live runtime work. A fresh
validation report at `/tmp/abl_g3_capsule_audit.json` (SHA-256
`8e66ec0495bd483e5e5b3898ac3027529070b3a6cf98d44cdcb3c85c97955dde`)
returned `complete=false`: current movie hashes disagree with the pinned index,
required manifests are absent, the batch is incomplete, and the independent
comparison has 87 mismatches. Even a valid pristine capsule would not contain the
newly compiled DAT/RAW/overlay state needed to validate this modified disc.

Named escalation reason: **missing/invalid relevant capsule plus modified-disc-only
behavioral domains**. That is why an isolated cold boot was necessary.

### Cold-boot runtime acceptance evidence

Command:

```bash
python3 tools/run_ps1_scenario.py \
  tools/scenarios/duckstation/g3_ready_replacement_objects.yaml \
  --disc build/ABL_G3_GATE_A_CANDIDATE_R5_20260810.cue \
  --output-dir /tmp/abl-g3-gate-a-candidate-r5-20260810-v1
```

Result: `PASSED`. The JSON receipt is
`/tmp/abl-g3-gate-a-candidate-r5-20260810-v1/g3_ready_replacement_objects.json`,
SHA-256 `c61327349e805b36710cee24c983c815871823517cc432acc44b13a043dd61aa`.
It binds the exact CUE/BIN above and movie
`fa2e81925fbad56af07081fbfe6980f2789a0dd72e6b63b13f9e7b5fc23ed264`.

The receipt records a reset/from-boot start, no save-state load, a fresh absolute
config directory, dedicated loopback port/token, verified `SCUS-94288` media, and
PID-owned cleanup. All seven trigger conditions completed. Assertions cover the
replacement spawn and Track-B resident gate, authored terrain/collision traversal,
grounded movement, Blender-authored grain pickup, spider presence, controlled marker
and goal/transition behavior, and pristine Track-A collision/render hook words.

Before media inspection or any guest mutation, the authenticated runner called
`debugger.capabilities` and verified the running executable path and SHA-256
`2ddaad7b1fdbca78110e3a871fd15496923e03be470d2e08e356a006b460dcf4`.
It reconciled `method_count=221` with the complete method inventory, required every
method used by scenario execution and cleanup, and checked each method's parameter,
result, and execution-policy schema. The canonical method-inventory SHA-256 is
`abdb61e0fe33c6e957685d2e2fbda20c08272276eeb3a77d45abe802789edd4e`.
The receipt also binds the scenario YAML SHA-256
`71fc28f505ac0dc7babe967f10cecc76e359c8745fa338b211d3e9920e55c6ff`
and runner SHA-256
`1a91407ddeddaf631aaaff36fb40c539463bfcd10754780c6804a5c15c8ebf9d`.

The marker/goal phases deliberately teleport the player to the exported controls as
a bounded Gate-A behavior test. They are not a claim that the frozen input movie
drove a wholly new start-to-goal route; that remains Gate B.

### Regression boundary

The focused command passed 30/30 and
`tests/test_build_identity.py tests/test_mod_layout.py` passed 16/16. The earlier
repository-wide safe runner was not globally green: 2857 passed, 306 failed, one was
skipped, and 149 were deselected. Those failures are broad pre-existing Phase-3/4
fixture/evidence drift in this already-dirty worktree; they are not being hidden or
claimed closed by this lane. The directly relevant tests, pristine verifier,
hook/cave validator, protected build, embedded output verification, and cold-boot
scenario are green.

### Gate A — restore the frozen Blender baseline

- Repair gameplay/enemy Empty export.
- Repair the four focused authoring failures.
- Remove or reconcile contradictory shading defaults between the template generator,
  P74 note, and exporter.
- Run the frozen template through `--prepare-only` and confirm its DAT/RAW/profile
  hashes and complete object roster.
- Cold boot a newly built image and pass Spawn, terrain, collision, Marker, Goal,
  pickup, enemy, and no-Track-A-renderer assertions.

### Gate B — blank-layout authoring proof

- Create a new `.blend` that does not preserve the retail terrain shape or route.
- Author a distinct start-to-goal path with at least two elevation changes and one
  branch or turn.
- Generate all visual and collision data from that `.blend`.
- Prove no retained retail floor payload owns pixels on the accepted route.
- Prove collision agrees with the exported terrain along the complete driven path.

### Gate C — layout sections and boundaries

- Partition the Blender surface into native payloads automatically.
- Assign/repoint node records and anchors without designer-authored file offsets.
- Compile collision-sector ownership and broad-phase bounds from the same partition.
- Add an explicit supported boundary policy; do not obtain a new route merely by
  leaving invisible retail collision active.

### Gate D — performance and camera envelope

- Establish a conservative per-frame native primitive budget.
- Reject or warn on unsafe payload density and excessive local subdivision.
- Validate ordinary follow-camera behavior over the full route.
- Record exceptional camera/setpiece dependencies in the build report.

### Gate E — production authoring release

- Freeze a clean starter template and its hashes.
- Publish one authoritative Blender property/schema reference.
- Make preflight, build, cold-boot scenario, and reports one command.
- Promote only after the safe test suite, build identity, and relevant cold-boot
  scenarios pass from the pristine base.

## Acceptance definition for “completely new level layout”

The milestone is met when a designer can create a Blender scene whose playable route,
terrain elevations, spawn, goal, collision, pickups, and enemies are not inherited
from the retail route, then produce a cold-booting replacement level without Track A.

Acceptance does **not** require a new scene slot, new renderer, arbitrary polygonal
world, caves, or new actor behaviors. It does require that the player can traverse a
wholly authored route and that no hidden retail visual/collision surface is providing
the accepted gameplay path.

## Preservation and validation rules

- The pristine hash-pinned retail image is the only build base.
- Never use ALLMODS or another derivative image as an input.
- Every layout build gets a new output path and build manifest.
- Disc/code/asset changes require cold boot plus a timing-matched movie; save states
  are diagnostic only.
- Keep generated discs, extracted assets, saves, movies, captures, and trace capsules
  outside commits.
- Validate relevant retained Phase 4 capsules before requesting a new live replay.
- Keep observation, inference, intended behavior, and acceptance results separate in
  follow-up notes.

## Next action

Create the separate Gate-B `.blend`: a genuinely new start-to-goal route with matched
visual/collision ownership and a complete cold-boot driven-path proof. Continue to
reject any claim of production readiness until the remaining geometry, performance,
camera, and release gates close.
