---
kind: experiment
id: EXP_2026-07-11_bonus_unlock_challenges
name: Pristine bonus unlock challenges and scene-16 handoff
status: confirmed
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: original_game_runtime
systems:
  - SYS_bonus_unlock_challenges
artifacts:
  - movies/Bonus_Level_01.movie.json
  - movies/Bonus_Level_01.movie.sav
  - movies/Bonus_Level_02.movie.json
  - movies/Bonus_Level_02.movie.sav
  - movies/Bonus_Level_03.movie.json
  - movies/Bonus_Level_03.movie.sav
  - src_re/bonus_unlock_challenges.c
  - src_re/player_bottomless_fall_800497f4.c
  - tools/scenarios/duckstation/bonus_unlock_suite.json
  - tools/fixtures.sha256
  - /tmp/abl-bonus1-probe/probe.json
  - /tmp/abl-bonus1-coverage/coverage.json
  - /tmp/abl-bonus2-probe-fine/probe.json
  - /tmp/abl-bonus2-coverage/coverage.json
  - /tmp/abl-bonus3-probe/probe.json
  - /tmp/abl-bonus3-coverage/coverage.json
  - /tmp/abl-bonus3-miss/miss_probe.json
  - /tmp/abl-bonus1-pitguard/coverage.json
  - /tmp/abl-bonus2-pitguard/coverage.json
  - /tmp/abl-bonus3-pitguard/coverage.json
---

# EXP_2026-07-11 Bonus unlock challenges

## Question

What do the three checked-in Bonus Level movies do before entering the bonus
level, which state and instruction blocks implement their counters, and what
exactly causes the scene transition?

## Workflow and provenance

- Followed the repository `AGENTS.md`, the `duckstation-external-debugger`
  skill, and [[DuckStation_API_Index]]. Existing movie fixtures, save anchors,
  debugger client, launch scripts, assembly baseline, symbols, `src_re`, and
  vault conventions were inspected before adding documentation.
- Repository revision: `e6402e8717f56df37b47405f6423aad0882ed502`;
  existing dirty user work was preserved.
- DuckStation fork revision:
  `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; debugger binary SHA-256
  `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.
- Only the pristine SCUS-94288 image was mounted. CUE SHA-256:
  `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`;
  BIN SHA-256:
  `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`.
  No MOD image was built or mounted for this experiment.
- Each replay used a unique `/tmp` config directory, loopback port, token, and
  owned PID. Cleanup stopped only that config's process. All Bonus investigation
  instances were confirmed closed; unrelated pre-existing DuckStation sessions
  were not touched.
- These are v3 state-anchored movies, not cold-boot fixtures. Each `.sav` was
  validated with `emulator.getStateInfo` as SCUS-94288 and the exact pristine
  cue before playback.

| Movie | Frames | Movie SHA-256 | Start-state SHA-256 |
|---|---:|---|---|
| Bonus 1 | 3,653 | `37083359bf7319acd323f3980fa96a6b0a676909209e2adf7a7986fe738f10cc` | `9d117f3b5780a4b9ecaf57b2491b600b662e7891a6a04ebc83f2d76895da95c1` |
| Bonus 2 | 10,045 | `bc9c6c4de35c2b260fadcbbbf9f1ec52034764fd30f2b293f6933734b7913459` | `ddc5d7c0d4335d39de4ee5d13ad801ea74e742c7b2ac2d16f8708b6f9d0eabd5` |
| Bonus 3 | 5,020 | `22ef450e2a88edcd7b3ef52bdfde7dc7cceff37d2967d37f377403bc6d7bf984` | `0dd145be44878df0424eee7942c9f645d4b0961e1bfe0a831e6acf0538d6b522` |

## Determinism correction: the first trace was rejected

The initial Bonus 1 attempt armed an `accessLog` CPU write watch. Per
[[DuckStation_API_Index]], CPU watches can force the precise interpreter and
perturb a timing-sensitive input movie. That happened here: at movie frame
1,250 the watched replay still reported `reproducible: true`, but bonus flags
were `0` instead of the clean replay's `2`, and both captured state regions
differed. The report (`/tmp/abl-bonus1-trace/trace.json`, SHA-256
`fad01f07b57fdbfb9efb055221e316d2a7f2fc12359f73511829cd3219fc4c1d`)
is rejected and none of its behavioral conclusions were used.

The replacement used unfiltered `movie.coverageToFrame`, which keeps the
CachedInterpreter execution path. At every checkpoint for all three movies,
the resulting full 2 MiB RAM SHA-256 matched an untouched
`movie.advanceToFrame` replay from a fresh anchor. For example, Bonus 1 frame
1,250 matched exactly:
`a26e2b60f8ab2581ac7362b4907f7290fe3d0a3eaef1d26c0d377b994e32061d`.
This is why `movie.status.reproducible` is treated as necessary but not
sufficient evidence.

## Common entry sequence

All three movies first solve a challenge in an ordinary scene. Success writes
transition latch `0x800823A0 = 6` and a fade timer, then the shell changes
`0x80082504` to scene `0x10`. The screen says **Bonus Level** while loading.
Scene `0x10` runs a playable bonus section, then the earned-clip result, and
returns to the journey menu (`scene 0`). The challenge and the bonus level are
therefore two separate stages of the flow.

## Bonus 1: Training spider butt-slams

Visual playback starts in Training (`scene 0x11`) in the spider arena. Flik
butt-slams five spiders. Counter `0x8008223C` and cycle-neutral PC coverage
showed:

| Movie frame | Counter | Relevant PCs in preceding interval |
|---:|---:|---|
| 250 | 1 | `0x8004B3A8` once |
| 500 | 2 | `0x8004B3A8` once |
| 750 | 4 | `0x8004B3A8` twice |
| 1,000 | 4 | no increment |
| 1,250 | 0 | increment, flag, latch, and reset once each |

At frame 1,250 flags are `0x02`, latch is `6`, and scene is already `0x10`.
The exact block is `0x8004B35C..0x8004B3D0` inside `FUNC_8004ABF4`: it guards
on high bit `0x20` and scene `0x10`, writes progress `old+114`, and on count 5
sets low bit `0x02`, fade `30`, and resets the counter. This solves the late
block without reclassifying the function's unrelated entry proximity test as a
normal level exit.

## Bonus 2: five different mushrooms in a row

Visual playback starts in scene `1`. Fine samples every 25 frames caught the
five signed bytes at `0x80082248..0x8008224C` filling as follows:

| Movie frame | Sequence (`-1` is empty) | Writer evidence |
|---:|---|---|
| 125 | `[6,-1,-1,-1,-1]` | append `0x8005C580` |
| 175 | `[6,5,-1,-1,-1]` | append `0x8005C580` |
| 225 | `[6,5,4,-1,-1]` | append `0x8005C580` |
| 275 | `[6,5,4,2,-1]` | append `0x8005C580` |
| 325 | `[6,5,4,2,3]` | append, latch `0x8005C6B8`, flag `0x8005C6E4` |
| 450 | unchanged | scene `0x10` |

Static assembly completes the behavioral rule: if the current mushroom ID is
already present, `0x8005C548..0x8005C56C` restarts the array with that ID in
slot 0 and `-1` in the other four slots. This is a distinct-plant chain, not a
raw five-bounce counter. Completion sets low flag `0x01`, latch `6`, fade `60`,
and vertical speed `-0x4000`.

## Bonus 3: blue berries and grasshoppers

Visual playback starts in Tunnels (`scene 3`) with native berry selector
`0x800A6597 = 1` (blue). Counter `0x80082240` progressed `1,2,3,4`, then the
fifth accepted kill executed this block once:

- increment store `0x800591C0`;
- flag OR `0x04` at `0x800591D0`;
- transition latch `6` at `0x800591DC`;
- success reset at `0x800591EC`.

Disassembly shows the increment occurs only after local enemy HP is `<= 0`,
contact damage class `hit+0x2C` is `0`, enemy actor ID is `15`
(grasshopper), and earned guard `0x40` is clear. Function entry resets the
streak at `0x80058B34` whenever the equipped selector is not blue.

### Case-13 reset: rejected early edits and accepted stationary control

Contact-dispatch case `13` unconditionally clears the streak at `0x80059A0C`.
Two early session-only edits around frame 900 were rejected because their added
throw changed the later route enough to enter native fall/respawn behavior; a
one-frame edit was too short to launch a berry. Those trials do not support the
miss claim.

The accepted control moved the minimum two-frame Square press to frames
`2150..2151`, after kill 4 while Flik was stationary. Every other recorded
button and axis was preserved in the session-scoped movie registry, and no
movie/save file was written:

| Movie frame | Streak | Coverage / result |
|---:|---:|---|
| 2,000 | 4 | fourth `0x800591C0` increment; source route not yet edited |
| 2,250 | 0 | case-13 reset `0x80059A0C` executed once |
| 2,500 | 1 | original fifth grasshopper executes `0x800591C0`, now step 1 |
| 2,750 | 1 | flags `0x33`, latch `0`, scene `3`; no bonus handoff |

This dynamically confirms case 13 as the missed-blue-berry reset for the
challenge. Report SHA-256:
`cf1f770ac875e14ee3b506f211af266a1c45228beeb599b818460f912e13afdf`.

## Native fall-path audit

The solved original ASM provided a direct desync guard. At `0x80049808`, the
tail of `FUNC_80048138` tests whether Flik has fallen below the scene threshold:
`player_y > [0x800822B4] + 8192`. The taken path reaches `0x80049858`, then calls
`FUNC_8004A700(..., mode=2)` at `0x80049868` to initiate fall/respawn transition
state `2`.

Cycle-neutral coverage over `0x800497F4..0x80049870` showed zero hits at both
taken-path PCs before every clean unlock. Each guard run also reproduced the
observer-free full-RAM hash exactly:

| Challenge checkpoint | RAM SHA-256 | `0x80049858` | `0x80049868` |
|---|---|---:|---:|
| Bonus 1 frame 1250 | `a26e2b60f8ab2581ac7362b4907f7290fe3d0a3eaef1d26c0d377b994e32061d` | 0 | 0 |
| Bonus 2 frame 450 | `a355fff03f1b17cb0273749ab27ebfb2f1381e8806343fcd249176ac00a2af31` | 0 | 0 |
| Bonus 3 frame 2750 | `c5cb62f1ca67d72e48095a33a98f4ea415f6afb7c4351b9398241ee2ac79a55d` | 0 | 0 |

Clean samples also kept Flik's Y/floor relationship and grounded state coherent.
This confirms that the checked-in Bonus movies themselves are synchronized; the
problem was limited to the earlier physics-divergent edits and intrusive
observer. The later stationary case-13 control is retained separately above.

## Source reconciliation

`extracted/re_baseline/SCUS_942.88.asm` and `tools/exe_read.py` supplied the
static instruction blocks and xrefs. `src_re/bonus_unlock_challenges.c` records
bounded C reconstructions without pretending the slices are standalone retail
functions. `src_re/player_bottomless_fall_800497f4.c` records the independent
native fall/respawn guard used to reject physics-divergent branches. Confirmed
addresses were also added to `config/semantic_state.yaml` for future debugger
scenarios and generated review snippets. The three positive
paths are executable through
`tools/scenarios/duckstation/bonus_unlock_suite.json`; assertions cover behavior
and semantic state rather than executable bytes.

The suite passed all three scenarios against the exact pristine cue. Every run
used a distinct scenario-runner config/PID and cleanup completed before the next
scenario; a post-suite process scan found no DuckStation process. Reports:

- suite `/tmp/abl-pristine-bonus-suite/suite.json`, SHA-256
  `ff9cdb48b3d49620d5d0c4bb6408747583533d550df5dcf90d0182d16747cf32`;
- Bonus 1 report SHA-256
  `04dc64e4d046b833236ca24b5aa428cf235f37cbdffb3ae95dd32163265d87ec`;
- Bonus 2 report SHA-256
  `7a8867d599e218d0ec5fe0dda3703ab33034d3b73eaa5f6b3059449e380ee5b5`;
- Bonus 3 report SHA-256
  `41de7141d94c403e96bd2685dc86b1d06d78045259b6bd435ca31567fafadd4e`.

Canonical original behavior is summarized in [[SYS_bonus_unlock_challenges]].
