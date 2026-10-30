---
date: 2026-08-04
phase: 4
row: F03_council_chamber
subject: Stage 3 Council Chamber - defeat Thumper
status: substantiated_partial
closure: bounded_exhausted
disposition: move_on
scenario: tools/scenarios/duckstation/phase4_f03_council_chamber.yaml
evidence_json: analysis/phase4_f03_council_chamber.json
---

# Phase 4 F03 - Council Chamber

## Result

F03 is **substantiated partial and bounded-exhausted**. The original row objective is "Stage 3 Council Chamber: defeat Thumper." The prior D16/F03 pass already closes the fight mechanics, mosquitoes, arena bound, cinematic transition, and exact goal-latch store. This pass adds the missing full-stage lifecycle: Council Chamber initialization, the natural fight, the once-only exit, MEMORY results entry, and results continuation all execute in one synchronized Interpreter scenario.

No additional movie is required. The existing `movies/Phase4/Interpreter/Any% Runs/LEVEL03_CouncilChamber.movie.json` is sufficient.

The row remains Partial rather than Full because the full overlay is not compiler-matched and several neighboring domains retain low-return questions. Those questions do not block the "defeat Thumper" objective.

## Capsule gate and escalation

No retained capsule covers F03. The existing structured D16/F03 trace is nontruncated and was queried first, but it is not a verified persistent capsule and its boss-specific movie did not reach the post-fight results continuation. A fresh isolated replay was therefore justified for the named missing domain: the full-stage results handoff.

The replay used pristine hash-pinned retail media and the version-4 Interpreter Any% movie. DuckStation was launched with `execution_mode: Interpreter`; instrumentation was armed only after the semantic HP initialization anchor. Instrumented intervals used `debugger.resume` plus `movie.status` polling, not `movie.advanceToFrame`.

## C-based pristine ASM verification

Two existing C analyzers were rerun rather than duplicated:

- `tools/phase4_d16_f03_static.c` loaded the pristine executable plus 21 overlays and passed **38/38** instruction pins. It binds the HP threshold, latch guard, cinematic call, goal store, camera-field semantics, and complete direct-address census.
- `tools/phase4_d16_fight_static.c` passed **40/40** instruction pins. It binds species dispatch, Thumper's actual callback, the mosquito callback, and the overlay-owned launcher path.

The first tool confirms the decisive overlay sequence in `LEVEL02/LEVEL.BIN`:

```text
0x800B4070  load Thumper HP [0x8009FE72]
0x800B4078  test HP < 21
0x800B4090  skip if goal latch [0x800823A0] is already nonzero
0x800B4138  start cinematic_camera_start_polar(flags=2)
0x800B4190  goal latch := 1
```

The loaded fight blob is `LEVEL02/LEVEL.BIN`, despite the scene-asset graph naming `level03/level1b`. Region A is a shared mutable swap buffer, so the executing writer PC remains the authoritative identity.

## Full-stage behavioral assertion

`tools/scenarios/duckstation/phase4_f03_council_chamber.yaml` passed all **7/7** assertions:

| Checkpoint | Observed |
|---|---|
| Semantic initialization | movie index 505; scene 2; Thumper HP 50 |
| Damage window | 16 generic damage-commit executions; threshold assertion `>=15` |
| Council exit | `0x800B4190` executed exactly once |
| Thumper cleanup | `0x800B45AC` executed exactly once |
| Results entry | `0x800B7DA0` executed exactly once |
| Results continuation | `0x800B8750` executed exactly once |

The Any% input route performs 16 generic damage commits. This does not change the HP threshold: the separate exact-address D16 trace proves the threshold arc is 15 two-point writes, `50 -> 20`. The scenario deliberately asserts `>=15` rather than encoding the false claim that a route cannot deliver an extra post-threshold hit.

## Load-order correction

The movie begins in a version-4 neutral/load interval. Scene 2 becomes visible while the reused goal latch and actor slot can still hold prior values. Consequently, frame 1 or frame 100 is not a valid "fight ready" oracle.

The durable scenario waits for the semantic condition `[0x8009FE72] == 50`. That occurs after 506 emulated frames at movie playback index 505. This avoids turning a load-order artifact into a gameplay assertion.

## Inherited D16 closure

The F03 stage row inherits the already-banked D16 findings because its objective is the same Council Chamber fight:

- Thumper is species 16, actor slot 1 at `0x8009FE04`, HP at `+0x6E`.
- The species callback `0x8004A0F4` only plays SFX 26. Fight structure belongs to the shared mover VM and overlay, not the callback.
- Council Chamber contains one Thumper and two mosquitoes. Species 10 uses callback `0x8004A180`; overlay code launches the mosquitoes and rotates a four-direction counter.
- The arena is not a geometry trigger or arena actor. Roster `+0x14 = 25`, scaled to 400 and combined with the measured 1.2.14 sine table, produces a fixed X/Z radius of 12,800 units. The observed maximum, 12,800.4, reaches the bound.
- `0x80090BEE` is cinematic-camera flags, not a defeat flag. The actual exit is the separate goal-latch store at `0x800B4190`.

## Why the old F03 residual text is stale

The shared mechanics baseline still says F03 needs an Interpreter re-take and results continuation. Both now exist. It also carries generic "route, collectibles, hazards" wording. The statically pinned Council exit has no collectible or hazard prerequisite: it tests Thumper HP and the goal latch. The Any% scenario covers the initialized objective through the results exit.

The shared baseline is currently dirty from other agents, so this pass records the corrected row conclusion here rather than overwriting their work.

## Phase 4 metrics

| Metric | F03 result |
|---|---|
| Campaign breadth | Met for the single-stage objective with boss-specific and full-stage movies |
| Complete frontier | Met from initialization through results continuation |
| Cross-system behavior | Met: actor HP/mover VM/overlay/cinematic/scene flow/results |
| Durable evidence | Met: two C verifiers, nontruncated trace, structured artifacts, passing scenario |
| Lifecycle | Met for the F03 objective |
| Original interfaces | Met |
| Original oracle | Met on pristine natural movies |
| Source closure | Substantiated partial: exact pins and census, not whole-overlay compiler matching |
| Typed state | Met |

## Bounded residuals outside F03

- Identify which berry/species index makes `0x800A6597 == 3` and reaches the optional `0x800B4158` branch.
- Trace the final consumer of `four_byte_store 0x80054AAC`; tint/fade plus duration remains supported rather than proven.
- Test whether roster `+0x14` is a general per-species arena-radius table.
- Compiler-match the complete fight overlay and shared mover VM.

These are berry-index, transition-rendering, campaign-generalization, and compiler-breadth work. They do not weaken the bound Council Chamber objective.

## Evidence and reproduction

- Structured closure: `analysis/phase4_f03_council_chamber.json`
- Scenario: `tools/scenarios/duckstation/phase4_f03_council_chamber.yaml`, SHA-256 `156995bda3e4c2d27d792eaf4a6c0eb7e01779f39bd2d5047e235b065c90bb3d`
- Passing report: `/tmp/phase4_f03_pass_20260804/phase4_f03_council_chamber.json`, SHA-256 `c6c30199ecdf2e5e834f15dfd0d11034bf279608941fe97386e81b2001c0231d`
- C camera/exit output: `/tmp/phase4_f03_static_verify.txt`, SHA-256 `b26d27e85f26c9ef513ecc760a925ccd3cb14e6045a6f0ae4e4763154db6b9b6`
- C fight/species output: `/tmp/phase4_f03_fight_static_verify.txt`, SHA-256 `5b9c5ac0289b7221943cfafcb80c17525549f65c786e5d431c4f47ea0b73a212`

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_d16_f03_static.c -o /tmp/f03-static
/tmp/f03-static
cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_d16_fight_static.c -o /tmp/f03-fight
/tmp/f03-fight REBUILD/files/SCUS_942.88
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/phase4_f03_council_chamber.yaml --output-dir /tmp/phase4_f03-report
```

The earlier `/tmp` calibration probes are excluded from positive evidence. They intentionally exposed the version-4 neutral/load interval and an over-specific `exactly 15 generic PC hits` assertion; the final semantic-anchor scenario supersedes them.
