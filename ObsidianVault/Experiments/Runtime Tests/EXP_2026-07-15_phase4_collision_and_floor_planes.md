---
kind: experiment
id: EXP_2026-07-15_phase4_collision_and_floor_planes
created: 2026-07-15
updated: 2026-07-15
status: reproduced
confidence: confirmed
system: SYS_collision_and_floor_planes
---

# Phase 4 collision and floor-plane experiment

## Question

Can E02 be reproduced from pristine authority across code, assets, all gameplay
contexts, causal geometry changes, lifecycle and the region/exit path without
using the non-pristine fall-through fixture?

## Isolation and authority

Each live attempt used a newly created absolute `/tmp` DuckStation config, a
dedicated loopback port/token and only its launcher-owned PID. The connected
instance reported SCUS-94288 and the mounted CUE/track hashes matched the
pristine pins. Every save was centrally declared, inspected with
`emulator.getStateInfo`, verified back to pristine media, and then loaded with
disc validation enabled. Cleanup used the same config/PID owner. The retained
artifact records DuckStation revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, binary SHA-256
`c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`
and `cleanup.owned_pid_stopped=true`.

## Static reproduction

`tools/phase4_collision.py` reverified the pinned retail executable, 13
byte-matched resident regions and 19 decisive opcodes. It selected all 24 RAW
files classified for collision in the Phase-3 asset provenance. Fourteen files
contained a `0x0103` collision chunk followed by a `0x0104` tail; all 28 marker
chunks were decoded, literal-recompressed and decoded again with semantic byte
equality. Files without these markers remained explicitly classified rather
than being misrepresented as collision payloads.

## Runtime procedure

1. Read the full `0x800A7E48` table for each of 19 gameplay anchors.
2. In every ordinary context, hold Up+Cross, stop first at the player call
   `0x800495C8`, then at integrator boundary `0x80036BC8`; read candidate count,
   pointers, owning sectors and typed plane records coherently while paused.
3. Compare neutral and Up+Cross branches at equal timing.
4. Trace player integrator, candidate boundary, resolver passes, Y commit and
   region query for 60 frames.
5. From the same LEVEL01 anchor compare baseline, current-sector origin shift,
   distant-sector origin shift and current-sector plane-reference shift.
6. Replay pause/resume, native death/respawn and LEVEL01→LEVEL02→LEVEL01 table
   reuse.
7. From the end-of-stage save, hold Up until current sector equals 177, then
   call the native region query with gate 1 and gate 0.
8. Replay the pinned from-boot input movie and its timing-matched neutral edit.

## Observation, inference, confirmation

Observation: table counts were 46–634 and all 19 table hashes differed. Eighteen
ordinary contexts exposed 2–27 player candidates; Flight bypassed the ordinary
boundary. Plane samples included 165 negative-Y floor/slope orientations and
eight other orientations. The traced ordinary branch hit the player integrator,
candidate boundary, swept resolver, resolved-Y commit and region query without
truncation.

Inference: the stable relationship is a scene-local oriented-plane system with
resident table/scratch addresses and per-use candidate publication. Visual
terrain, hazard policy and scene-transition dispatch are consumers or sibling
systems, not alternate descriptions of the plane payload.

Causal confirmation: active sector origin `+2048` and six active plane ref-Y
fields `+64` (scaled ×32) independently shifted the resulting player/floor by
`+2070/+2064`; a distant non-candidate sector `+2048` was exactly inert.
Natural travel reached region-code sector 177 and set the transition lever;
explicit query gate 1/0 returned 2/0.

## Failed hypotheses and corrected methods

- An exploratory expectation that uniformly shifting the active plane
  references would unground Flik was false. A uniform `+64` moves the surface
  coherently by 2048 world units, so grounding correctly remains set. The
  fail-closed generator rejected that over-specific assertion; the retained
  predicate checks scale, player/floor movement and grounding instead.
- At the first paused frame after entering sector 177, the `+0x82` gate byte was
  already 0 even though the native handler had set the transition lever. The
  earlier assumption that the gate must remain 1 at that later boundary was a
  timing error. The retained experiment separates natural sector/lever travel
  from direct native gate-1/gate-0 calls at the same sector.
- `0x80037320` is not promoted as the player-list builder. Static callers and
  the exact player boundary show it is the shared entity/projectile path; the
  player list is built inside `0x8003633C`.

## Reproduction and result

Static tests invoke `phase4_collision.build_static_census()` directly. The live
command is:

`python3 tools/phase4_collision.py --port <dedicated> --token <dedicated> --config-dir /tmp/<fresh> --instance-state recreated`

Retained result: `analysis/phase4_collision.json`, SHA-256
`d1987d886559928ba48ba8dae9c97157ad25fdec3c9233311b427fba8cdf9399`.
See [[SYS_collision_and_floor_planes]] for promoted original-game facts. No
MOD-private state or intended behavior was introduced.
