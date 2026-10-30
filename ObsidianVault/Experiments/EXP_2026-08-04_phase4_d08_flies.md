# Phase 4 D08: Horsefly / FLY bounded exhaustion

Date: 2026-08-04

## Question

Close the high-value D08 Horsefly gaps: identity, attack/contact behavior, three-stage variant differences, berry damage, lethal transition, drop/quota classification, and lifecycle ownership. Use the accepted trace capsule and pristine C/ASM analysis first; escalate live only for a domain absent from the capsule.

## Pinned inputs

- Retail CUE: `Disney-Pixar A Bug's Life (v1.0).cue`, SHA-256 `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`.
- Pristine executable: `SCUS_942.88`, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Movie: `movies/Phase4/D08_fly_contact_kill.movie.json`, v3, 554 frames, SHA-256 `fa735f27a99106f6bd457d44fd5f458b96e518da20220a0597cc66b0d1e6367f`.
- State: `movies/Phase4/D08_fly_contact_kill.movie.sav`, SHA-256 `ae78cdc4877c14c244b20dcf16f94daefcf92c7067dcdd1c9a2baacb8a4eb9c8`.
- Accepted capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/D08_fly_contact_kill`.
- Capsule manifest SHA-256: `d185aa76585e29b4e5f0b046913a0d58cc6bcf219b01bf6af711b9f5ae374314`; tree SHA-256 `5e532adf471ab4c2bd761e31ecfac2f2e5a5c036e3bd599cc31b159d328d6a7f`.
- Capsule result: complete, 554 movie frames, no errors/truncation/control mismatch; RAM/register/VRAM/SPU and cycle comparisons match its independent control.

The capsule is centrally preserved in `analysis/phase4_trace_capsule_set.json`. Bulk capsule/checkpoint data remains external.

## Capsule-first C analysis

The capsule query tool produced transient normalized TSVs. The C reducer rejects any TSV whose hash differs:

| Projection | SHA-256 |
|---|---|
| actor snapshots | `9ab2269b3f2f3d6f8e95be681a97e610d639e33a8be66f12210ac3d9cadba7a9` |
| semantic hotspots | `1aca727e15883a7af8b66e105e659f7d08c9a7202cd64f8e5b24601595c12f33` |
| actor-ID-6 census | `5d59e8362cee7da356c682b16709fa672424025b833e01a233e19cfec29c641d` |
| live exact-PC trace | `5fb7e2c102021fdb5adfdebcd5a3f1ddc1bf1b32942e9e4e78f2d4add797da1e` |
| live semantic writes | `c8b576bd099d7b4a04732526731238da45a289afd69dd82d40615e5f64d7acfd` |

Commands:

```bash
cc -std=c11 -O2 -Wall -Wextra tools/phase4_d08_static.c -lcrypto -o /tmp/phase4_d08_static
/tmp/phase4_d08_static SCUS_942.88 > analysis/phase4_d08_static.json

cc -std=c11 -O2 -Wall -Wextra tools/phase4_d08_evidence.c -lcrypto -o /tmp/phase4_d08_evidence
/tmp/phase4_d08_evidence \
  /tmp/phase4_d08_capsule_snapshots.tsv \
  /tmp/phase4_d08_hotspots_semantic.tsv \
  /tmp/phase4_d08_census.tsv \
  /tmp/phase4_d08_live_exec.tsv \
  /tmp/phase4_d08_live_access_semantic.tsv \
  > analysis/phase4_d08_evidence.json
```

The capsule identifies slot address `0x800A032C` as actor ID 6, callback `0x8004A144`, max HP 8, and mover IP `0x800776E4` inside the program at `0x800776D0`.

Observed movie-relative state:

| Frame | Reaction `+0x6C` | HP `+0x6E` | Meaning |
|---:|---:|---:|---|
| 0 | 0 | 8 | live Horsefly |
| 190 | 15 | 8 | ordinary contact; `0x8004B650` executes once |
| 218 | 1 | 8 | contact reaction nearly consumed |
| 220..400 | 1 | 8 | off-activity frame-boundary state; cause not overclaimed |
| 426 | 20 | 6 | first berry hit; `0x800590E4` executes once |
| 472 | 20 | 4 | second berry hit; `0x800590E4` executes once |
| 500 | 6 | 4 | reaction countdown |
| 510 | 1 | 4 | reaction countdown |
| 554 | 0 | 4 | movie ends alive |

This corrects the filename: `D08_fly_contact_kill` is not a kill recording.

## Pristine ASM result

`tools/phase4_d08_static.c` validates 44 exact instruction words plus the mover programs and shared program pointer.

- `0x8004A144` is a shared low-state sound callback, not an AI routine.
- Horsefly bytecode is a pure random wander/seek loop. It contains no proximity, native call, chase, or projectile operation; ordinary body contact is its only attack.
- Accepted projectile contact stores reaction 20 at `0x80058ED8`.
- The common marker switch stores HP at `0x800590E4`: marker `0/12=-2`, `1=-99`, `127=-4`, `128=-3`, default `-1`.
- Positive HP bypasses the KO tail at `0x8005915C`.
- Nonpositive class-one HP writes sentinel 999, clears `+0x60`, applies `flags | 0x0880 & ~0x0002`, loads program pointer `*[0x80077B2C] = 0x800776AC`, and calls `0x800498AC(actor,1)`.
- Class one branches around the class-two-or-greater effect/quota block. The quota store at `0x80059300` is therefore not expected for this temporary KO.
- `0x800776AC` decodes to `park_arrive_stop; jump_back[1]`.

## Named-stage breadth

The existing Phase-1 census supplies 22 independently placed actor-ID-6 records:

- Riverbed Run: 4.
- City Entrance: 9.
- City Square: 9.

All 22 share callback `0x8004A144` and mover program `0x800776D0`/active IP `0x800776E4`. Pose/model pointers differ consistently by stage (`0x80137B4C`, `0x8010F798`, `0x800CF480`). This closes the named variant question at the mechanics level while preserving the visual-data distinction.

## Named live escalation

Missing capsule domain: the accepted movie ended at HP 4 and could not prove the native D08 lethal transition. Static code proved the shared branch but not that an unmodified Horsefly takes it.

An isolated instance was created at `/tmp/duckstation-debugger-phase4-d08-20260804-a`, port `23708`, token `phase4-d08-20260804-a`. Media and state identity were verified before loading. Current debugger fork revision was `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; runtime binary SHA-256 `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`. The profile pinned `CPU/ExecutionMode=CachedInterpreter` for clean movie playback.

The movie was replayed at normal speed with `debugger.resume` plus polling, with fast-forward/turbo off and no CPU instrumentation. Playback stopped before any trace was armed. The resulting boundary was saved only to `/tmp/phase4_d08_tail.sav`. Instrumentation was then armed after scripted playback had ended, so its forced switch to Interpreter could not desynchronize movie inputs.

A non-mutating input matrix from that boundary found `Square` held five frames produces the third hit (`4 -> 2`); lateral/down variants miss. Exact-PC watches were then limited to `0x800590E4`, `0x80059154`, `0x800592A8/AC/B0/B4/B8/C8`, and write watches to the target state. A later Square throw connected at emulator frame 117886:

- `0x800590E4`: HP `2 -> 0`.
- `0x800592A8`: HP `0 -> 999`.
- `0x800592B0/B4/B8`: register `v1` progresses `0xD007 -> 0xD887 -> 0xD885` before the `+0x5C` store.
- `0x800592C8`: mover VM `0x800776E4 -> 0x800776AC`.
- All six KO-tail watches carry `s7=1`.
- Exact exec events: 10, not truncated. Access events: not truncated. Enemy-quota writes: 0.

The isolated PID was verified against its config-owned launch and stopped. No disc, movie, save, or guest RAM was modified; only normal controller input was supplied after replay.

## Closure judgment

`D08_flies` is **substantiated partial, bounded-exhausted (2026-08-04)**.

Closed at causal/mechanics level: family identity, attack/contact loop, damage/reaction, natural lethal transition, class-one KO behavior, quota/drop-path classification, shared respawn ownership, and Riverbed/City mechanics breadth.

Bounded residuals: exhaustive per-berry visual presentation, gold-kill effect presentation, exact Horsefly-instance respawn delay, and animation/audio naming. These are shared-system or presentation breadth with low expected return. Reopen only for a contradictory actor-ID-6 variant or a named Horsefly-specific presentation question. No additional Interpreter movie is required.
