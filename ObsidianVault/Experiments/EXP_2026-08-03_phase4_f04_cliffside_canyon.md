---
type: experiment
status: complete
date: 2026-08-03
system: stage completion / Cliffside Canyon dandelion flight + bird hazard
phase: 4
artifacts:
  - analysis/phase4_f04_cliffside_canyon.json
  - analysis/phase4_d17_bird.json
  - analysis/phase4_b03_dandelion_static.json
  - analysis/phase4_b03_dandelion_capsule.json
  - analysis/phase4_b03_dandelion_runtime.json
---

# Phase 4 F04 Cliffside Canyon — a triple synthesis from B03, D17, and D11

## Question

F04_cliffside_canyon was `unresolved`, its own content thin (one scene-binding line,
`missing: Special flight and kill-zone mechanics`) but — unlike F15/F06 before it — with no
explicit `"See Dxx"` pointer of its own. Two named mechanics, two places to look.

## The "special flight" half: already closed by B03

`B03_dandelion_glide` is an already-`partial` row explicitly scoped `"stages: Cliffside
Canyon (4) primary"` — this row's own subject — and was deliberately stopped as
"bounded-exhaustion, STOP" after a genuinely deep pass: static ASM closure (892 files,
100,425 instructions), a hash-validated offline capsule reconstruction, a live Interpreter
runtime trace, and sprite identification.

The mechanism: contacting a mature dandelion plant (handler `0x8005C818`) detaches any
carried actor, launches the player upward (`vy=-4096`), and enters a glide mode with active
steering (VX/VZ change during the glide, not a fixed trajectory) — live-confirmed apex rise
of exactly 30,720 units, settling into a native grounded state ~537 frames later. A related
but distinct mechanism, propeller updrafts, share the same power-state field: dandelions
write latch 11 (a strong one-shot launch), propellers consume it for a slower sustained
lift, both clearing via the same handler family.

Nothing here needed re-deriving — cited straight from B03's own already-comprehensive row.

## The "kill-zone" half: already closed by D17

D17_bird's own `CLIFFSIDE_HAZARD_ENCOUNTER_2026-08-02` section is a complete, live-traced,
operator-cross-verified account of exactly this hazard, recorded specifically for it
(`D17_Cliffside_Bird_Death.movie.json`, 527 frames). `scene_id=6` at frame 50 confirms it's
this row's own subject.

The same actor (`id=30`) that fights as the Birdnest boss elsewhere is reused here purely
as an environmental hazard — hp 101 instead of 50, never damaged in the whole recording.
Its steering target locks to Flik's X/Z (a fixed hover altitude above him), while its real
physical position dives at him in a clean stoop once he lands (closing from 30,037 units to
1,365 at closest approach). Contact routes through the same generic damage handler used
everywhere else in the game, but the kill mechanism itself is distinctive: it doesn't
deplete health (which stays constant at 4 the whole time) — it's a direct lives decrement
plus forced reposition, with a fully timed recovery/respawn cycle (stagger at -45, recovery
to 0 by frame 419, black-screen transition, respawn commit at frame 448).

Two residuals inherited, not closed by this pass: the exact branch inside `FUNC_8004ABF4`
that fires the contact, and an unexplained power-flags bit (`0x10`) at the death branch that
D17's own exhaustive check couldn't attribute to any known resident code — likely
uncharted Cliffside-overlay logic.

## Bonus: campaign breadth for free

`D11_mites_grubs`, as a side effect of an unrelated census, already confirmed the mite
(`id=37`) spawns in this exact scene — and that this row's own pre-existing
`canyon_bug.sav`/`canyon_bug_aggro.sav` fixtures are actually that same, already-solved
species (the "canyon_bug" name was an artifact of an unrelated tangent, corrected in D11's
own pass).

## Residuals

Whether the flight and hazard mechanics interact or have a specific encounter order within
this stage's own level layout (neither source row addresses stage-level flow, only their
own mechanism in isolation); this stage's own critical path (the original stub's own
`fixture_need`, "flight-route movie incl. premature landing," was never satisfied by any
fixture, still isn't); `FUNC_8004ABF4`'s exact branch and the power-flags bit `0x10`
mystery (inherited from D17); B03's own explicitly-deferred breadth items (inherited, and
explicitly judged low-value there too); whether other enemies beyond the mite appear in
this scene; source closure; cross-system audio/HUD; no dedicated Canon page created.

**Assessment**: F04_cliffside_canyon moves from `unresolved` to `partial` via triple
synthesis — both named mechanics in its own `missing` field are now substantially covered
by citation from already-developed rows, with zero new live instrumentation needed. Not
claimed solved: several residuals are directly inherited rather than newly closed, and this
stage's own level-layout/flow question (how the two mechanics relate to each other
in-level) was never addressed by any of the three donor rows, since none of them were ever
about this stage's own critical path.

## 2026-08-04 route-closure continuation

### Result

F04 is now **substantiated partial / bounded-exhausted**. The prior synthesis proved the dandelion and bird mechanisms independently but correctly left their stage order and critical-path relationship open. The existing full-stage Interpreter fixture closes that frontier without a new recording.

### Accepted retained evidence

- B03 capsule manifest: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B03_dandelion_updraft/manifest.json`, SHA-256 `d97ab00a0abd67881d0fdc91dbc82a0c0a0d503bd87ea544b8d32ed865a9d14b`.
- Acceptance gate: `complete=true`, `error=null`, exact parser; independent control and capsule fingerprints match for full machine state, RAM, registers, VRAM, and SPU RAM.
- This older capsule's passive block coverage used CachedInterpreter. It was used only for offline B03 facts, not for the new phase-sensitive route replay.

### Live route experiment

- Fixture: `movies/Phase4/Interpreter/Any% Runs/LEVEL04_Cliffside.movie.json`, v4, 3,907 frames, `armed_while_paused=true`, `reproducible=true`.
- Movie SHA-256: `dec4cb6196b35015494f806045495ff0beb1c65cadf3aa494be552475e7129c8`.
- Start-state SHA-256: `1b12a0729a80a0c6e636ba01f0d28f674bd49298d618ab90f803ff7bbda112a6`.
- Retail cue SHA-256: `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`. The post-state-load cached cue matched the same hash.
- Isolated config: `/tmp/dsrepro-f04-20260804`, port `23544`, token local/transient; launched with `tools/launch_repro_playback.sh --execution-mode Interpreter`.
- DuckStation revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; binary SHA-256 `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
- Execution was true 60 Hz via `debugger.resume` and polling. No fast-forward, `movie.advanceToFrame`, or runtime mutation was used.
- Instrumentation was armed only after `movie.startPlayback(load_start_state=true)` and the resulting state load. All four exec and four access logs report `truncated=false`.
- Cleanup cleared exec/access traces, movie playback, and controller state, then stopped only PID `2411356` through the owned config directory.

### Observation

| Event | Exact evidence | Movie-relative frame |
|---|---|---:|
| Scene 6 load | `0x800503E0`, `0x80082504: 2 -> 6` | 59 |
| Dandelion handler interval | `0x8005C818`, 162 hits | 789-1111 |
| One-shot launch | `0x8005C848`, `v0=0xFFFFF000` (-4096) | 819 |
| Latch 11 begins | `0x8005C8BC`, 19 exec/access-confirmed writes | 831 |
| Last latch refresh | `0x8005C8BC` | 867 |
| Intended grounded clear | `0x80048700`, latch `11 -> 0` | 3215 |
| First scene-6 exit | `0x800503AC`, `0x80082504: 6 -> 0` | 3258 |

Latch 11 therefore remains resident for 2,384 frames and clears only 43 frames before the successful scene exit. The successful route recorded zero hits at D17's observed contact/death-path PC `0x8004A814`, zero post-launch life decrements, and ends with lives 9 and health 4.

### Static ASM and C reduction

`tools/phase4_f04_route_analyzer.c` parses the runtime TSV and computes instruction addresses from the pristine hand-written ASM rather than trusting labels in the trace summary. It matched all six required sites:

- `0x8005C848`: dandelion `vy=-4096` store.
- `0x8005C854`: mode-5 store.
- `0x8005C8BC`: latch-11 store.
- `0x800503AC` / `0x800503E0`: scene clear/restore stores.
- `0x8004A814`: contact stagger store on the D17-observed damage path.

The analyzer builds cleanly with:

```bash
gcc -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
  -o /tmp/abl-f04/phase4_f04_route_analyzer \
  tools/phase4_f04_route_analyzer.c
/tmp/abl-f04/phase4_f04_route_analyzer "$PWD" /tmp/abl-f04
```

Source SHA-256: `ee016ee8b598bae5c820b58ac010791747519de2dac7cff86a90433b65cb629d`. Compact result: `analysis/phase4_f04_route_analysis.json`, SHA-256 `f93edf98268b561e3e5cb4802941ae06c56eb71ebff505233c7c08e52b6e61a1`.

Transient raw evidence stayed under `/tmp/abl-f04`. Exec log hashes: `ce799d8551d797679abc8f6876a47e3ab4c319da78279f1f21cf421241dae9d2`, `05cf968db964877da5f48abf328630cbcf62d914513ca19274d62bcb57c0dbc2`, `3988cfe84238b475d3ab4c9d4a101d2132cde7842494af931f7395e00a9e6c10`, `39c7e899d2867325840660c6671e2b36bc527ec632d8457626ec9c203157b492`. Access log hashes: `4084593e800b657196c64c68cbb5cc5dc7f6803102b738ac7ab2677214e253b5`, `4707edd02128a9efb6fd2d05cf4182bdac0bf21be87bcf4ee3c116f8c926a82a`, `76e036c96f097c5ff81814c21923bf4e23d32d7673c00a94df50d4553d354d53`, `74c8c67fd1b507041a85ea7d057d0905eae0b9f88cbb42bccdb932d506ba2318`.

### Interpretation and closure boundary

- **Observation:** the successful full route loads scene 6, executes the dandelion launch, holds latch 11 through almost the entire traversal, clears it on the intended landing, and exits 43 frames later without entering the bird contact path or losing a life.
- **Inference:** dandelion flight is on the successful critical path; the bird is not an unavoidable scripted hit.
- **Causal composition:** D17's separate premature-landing fixture supplies the complementary control: ground contact is followed by actor 30's physical dive, `0x8004A814`, direct life loss, and respawn. Together they establish the named relationship without pretending a single explicit “if premature landing then bird” branch was traced.

Remaining work is low-return breadth: the exact sub-branch inside `FUNC_8004ABF4`, the Cliffside-overlay writer of power bit `0x10`, exhaustive pointer/instance and enemy census, source closure, and audio/HUD. None can overturn the named flight-plus-bird behavior or route ordering. Reopen only for a concrete downstream consumer.
