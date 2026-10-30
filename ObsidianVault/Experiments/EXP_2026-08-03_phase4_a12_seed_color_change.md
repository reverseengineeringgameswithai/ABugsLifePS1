# EXP 2026-08-03: Phase 4 A12 seed color change

## Verdict

A12 is a substantiated partial whose high-value row-specific work is
bounded-exhausted. Move on. No Interpreter movie is required for the reusable law.

The earlier 2026-07-30 scan remains invalidated: 0x800822A4 is an unrelated renderer
cache and unchanged source byte 0x80094C76 did not contain a Triangle edge. This
experiment independently resolves the actual selected actor, source pointer, writer,
color domain, denied states, unlock producers, presentation calls, and reset path.

## Evidence order

1. Validate and query the retained capsule.
2. Reconstruct the pristine executable with compiled C scanners.
3. Use an isolated pristine DuckStation run only for the missing causal input controls.
4. Separate observations, inference, and causal confirmation.

## Retained capsule

Capsule:
~/Downloads/ABL-external-evidence/trace-capsules/Phase4/a10-a11-v2-20260719/Phase_Helpers__carry_handstand

- Manifest SHA-256:
  5188a58af0c5c347b5f2a7685e12748631686823edf78ad15c2649d716f02a26
- 1,359 frame-boundary records, 23 chunks, and 4,077 RAM/VRAM/SPU hashes.
- All recorded hashes validate; the manifest reports no truncation or error.
- Movie frame 620 has selected offset 0x84, actor 0x8009FE04, source pointer
  0x80094A54, color/default 0/0, and unlock word 0.
- The retained movie has no Triangle edge. Passive flow reaches the selection gate
  449 times but none of the Triangle-taken blocks. The capsule is baseline state/flow
  evidence, not transition evidence.

Source pins:

| Artifact | SHA-256 |
|---|---|
| carry_handstand.movie.json | 65d344960a2c14b828a800bebd8ae0a9af30ba24db4b6822f48a630e7f46901c |
| carry_handstand.movie.sav | faa1874797000bb5d9b9581ddeca8a6a28abff33e762cd1df4e4fc113b19b3b2 |
| pristine SCUS_942.88 | 1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20 |

## C static-ASM result

The compiled scanner works from the pristine executable at load address 0x80010000.
It resolves this path:

| Address | Meaning |
|---|---|
| 0x800473B4 | load selected offset 0x800A655C |
| 0x800473BC | reject selected <= 0 |
| 0x800473C8 | load current pad 0x80082488 |
| 0x800473D0 | mask Triangle 0x1000 |
| 0x800473E0 | load previous pad 0x80082380 |
| 0x800473E8 | mask Triangle 0x1000 |
| 0x800473F4 | load selected actor |
| 0x800473FC | load actor+0x80 source pointer |
| 0x80047404 | read source+0x0F default/forced color |
| 0x80047410 | write source+0x18 transition timer |
| 0x8004741C | load four-nibble unlock order 0x800B0196 |
| 0x80047464 | write source+0x0E current color |
| 0x80047470 | call 0x8005044C with 30+color |
| 0x8004747C | call 0x800577DC color presentation |

The pristine executable has only two source+0x0E stores. The other, 0x80049DF4,
restores current color from source+0x0F during actor reinitialization and clears the
timer. Scene initialization at 0x8005BB60 clears 0x800B0196. The pickup handlers at
0x80054288..0x80054554 append indices 1..4 on first collection of token kinds
0x2A..0x2D; baseline kind 0x29 does not append.

The presentation helper indexes RGB table 0x80078E58 and effect object color+124.
Entries 0..4 are brown (128,64,0), blue (0,64,128), green (32,128,32), purple
(128,32,112), and orange/yellow (200,127,0). The sound argument is 30+color.

## Adversarial campaign census

The follow-up C audit parses pristine content directly rather than extrapolating one
level:

- C source: /tmp/phase4_a12_adversarial.c, promoted as
  tools/phase4_a12_adversarial.c.
- Source SHA-256:
  eb3552a5d436bd3efc3c39d5853180eb3b4caae9b7331aa5e4d311eb2dfcc0f2.
- Result: analysis/phase4_a12_campaign_census.json.
- Result SHA-256:
  41df059c03844d24997d3a7e9f239e9184e195dad4dcdc01b8809c7fef7b83f0.
- 21/21 LEVEL*.DAT resources parse; token totals for 0x29..0x2D are
  [18,25,36,26,7].
- 24/24 LEVEL*.RAW resources parse; 130 id-11 seed records use current colors
  {0:103, 1:14, 2:5, 3:4, 4:4}.
- All 130 records satisfy current == (default_byte & 0x0F). The default byte's high
  nibble ranges through 0x00, 0x10, 0x20, and 0x30, but introduces no sixth color.
- Across all 20 LEVEL*.BIN overlays, direct sb base+0x0E writer count is zero.
  Five lbu base+0x0E patterns are readers, not alternate mutation paths.

This turns campaign availability from an unmeasured residual into a bounded static
census. It does not claim every token was collected naturally in every stage.

## Isolated runtime controls

- Config: /tmp/dsrepro-phase4-a12-20260803
- Dedicated endpoint: 127.0.0.1:23712
- DuckStation binary SHA-256:
  f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899
- Media: pristine SCUS-94288 cue; save-state media validation succeeded.
- CPU mode: CachedInterpreter, matching the version-3 source movie.
- Playback: normal speed to movie frame 622/emulator frame 10483.
- Instrumentation: none. Arming execTrace would have changed execution mode and
  invalidated this legacy movie.
- Temporary anchor:
  /tmp/phase4_a12_anchor_f622.sav,
  SHA-256 63cf790196bc9629a4265fa68bec025a8eab3188991287af5e0b49df7d8b29ec.
- Transcript:
  /tmp/phase4_a12_runtime_evidence.txt,
  SHA-256 6e8b454c705e1161011f8d9d3a3c2d3c380d98627aa235a18becebb6c6406253.

Every case reloaded the anchor and used atomic RAM writes only to construct a
counterfactual. No disc, executable, asset, source movie, or source state was changed.

| Case | Observation |
|---|---|
| unlock word 0x4321 | fresh edges produced 0->1->2->3->4->0 |
| Triangle held | current/previous pad both 0x1000; color stayed 1 |
| unlock word 0 | selected stayed 0x84, color stayed 0, timer reached 18 after four frames |
| selected offset 0 | color stayed 0, timer only reached natural-control value 2 |
| source+0x0F = 3 | color became 3 and timer reached 18 |

The handler writes timer 16. The sampled 17/18 values include normal actor lifecycle
ticks after the edge; the no-selection control demonstrates that the larger jump is
caused by the A12 path.

## Fixed/mounted selection control

A second fresh isolated config replayed the same validated movie at normal speed to
movie frame 1049, within the capsule's fixed/mounted selected-seed epoch.

- Selected offset: 0x0108.
- Selected actor: 0x8009FE88.
- Actor+0x80 source: 0x80094A70.
- After stopping playback and flushing recorded input, both source color/default were
  zero and the selection remained active.
- Atomic runtime setup set unlock word 0x4321 and timer 0.
- A fresh Triangle edge changed source+0x0E from 0 to 1 and sampled timer 17.
- Transcript:
  /tmp/phase4_a12_fixed_control.txt,
  SHA-256 101e2234b9b9c4d920886e6a8ac0cd34feeae1d19adb2935bb54c1dafc55ef23.
- Temporary anchor:
  /tmp/phase4_a12_fixed_f1053.sav,
  SHA-256 9e469bc67606f6ce50a5791d603ede3781faacdaaacd3f9551790b5159a1deb1.

This causally confirms that positive selection, not carry mode, admits A12.

## Evidence classification

### Observation

- The capsule is hash-valid and contains a genuine selected carried seed but no
  Triangle edge.
- The live replay matches the capsule's selected actor/source/color/unlock state.
- Runtime controls produce the ordered color sequence, held denial, empty-list
  behavior, selected=0 denial, and forced-default behavior above.
- The fixed/mounted selected source also changes color on Triangle.
- The campaign census finds every token kind, only the five color indices, no authored
  current/default-low mismatch, and no direct overlay writer.

### Inference

- The handler is resident and has no explicit level-number gate. Per-stage color
  availability is therefore driven by scene content and token collection order.
- Current color persists through carry/drop while the source record remains live;
  actor reinitialization restores the authored/default nibble.

### Causal confirmation

- Changing only 0x800B0196 changes the Triangle result from brown feedback-only to
  the 1..4 ordered cycle.
- Changing only selection to zero prevents the handler's timer jump.
- Changing only source+0x0F to 3 forces output color 3.
- The static writer/caller frontier explains every controlled result without an
  alternative source+0x0E writer.

## Phase 4 closure

| Metric | State | Boundary |
|---|---|---|
| Original oracle | advanced | Genuine carry anchor and causal controls; no natural colored-token collection |
| Complete frontier | met | Input, writers, producers, reset, audio, VFX, and reinit covered |
| Typed state | met | All decisive fields and the five-value domain typed |
| Lifecycle | advanced | Pickup order through reinit covered; scene reload not replayed |
| Original interfaces | advanced | Controller, actor/source, token, HUD list, SFX, VFX, plant chain |
| Campaign breadth | bounded | All 21 DATs, 24 RAWs, and 20 overlays censused; exhaustive natural execution is low return |
| Cross-system | advanced | Token -> order -> source color -> feedback -> plant output |
| Source closure | met | Semantic C plus two compiled evidence tools |
| Durable evidence | advanced | Inputs and transient control outputs hash-pinned |

Strict status remains partial because Phase 4 requires every metric met. The missing
breadth and exact audiovisual timing have minimal return for the reusable mechanic.
Revisit only for a direct MOD dependency, a named stage's natural availability, exact
render-frame timing, or SPU waveform identity. Such a promoted question should use a
new Interpreter movie; the current legacy movie must remain poll-only.

## Tool pins

| Tool source | SHA-256 |
|---|---|
| tools/phase4_a12_static.c | 43966b63c2d5b2a624a7ec1a7fdfe8cbd48b026bb1e4855f01b0bf054ea86c15 |
| tools/phase4_a12_capsule.c | 0fb014c6e7862b9dfb1c8867dfdd0d232a32814a94c01993b3331ade3daa16f8 |
| tools/phase4_a12_adversarial.c | eb3552a5d436bd3efc3c39d5853180eb3b4caae9b7331aa5e4d311eb2dfcc0f2 |

The static tool is compiled against the pristine executable. The capsule tool accepts
the retained capsule directory and REBUILD/files, validates compressed chunks and
domain hashes, and reports the A12 gate/source state.

## Related

- [[SYS_seed_color_change]]
- [[EXP_2026-07-30_phase4_a12_level01_seed_color_address_narrowing]]
- [[Phase 4 - Solve Every Gameplay and Engine Subsystem]]
