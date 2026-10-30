---
kind: experiment
id: EXP_2026_08_03_phase4_a13_bounded_exhaustion
status: substantiated_partial
created: 2026-08-03
updated: 2026-08-03
confidence: high
related:
  - EXP_2026_07_30_phase4_a13_level01_brown_selector_packing
  - Seed_plant_output_binding
---

# Phase 4 A13 - plant-output cycling bounded exhaustion

## Disposition

**A13 is substantiated partial; high-value row-specific static work is exhausted.**
The prior operator pass correctly bound the five bytes and their packed nibbles. This
continuation owns the X handler, wrap and denial branches, timeout, writers, reset,
consumer bounds, malformed states, typed model, and executable static guard.

Strict promotion still needs a short scripted Interpreter positive/negative oracle.
No live replay was used here because the resident and overlay ASM answer every named
static domain. There was therefore no Phase-4 capsule-to-live escalation to perform.

## Exact X-handler

The owner is `player_contact_response` at `0x80047284`; the relevant block is
`0x80047A88..0x80047B9C`. It requires:

- a nonzero carry latch and valid carried actor index at `0x800A655C`;
- a rising X edge: current input `0x80082488 & 0x4000` is set while previous input
  `0x80082380 & 0x4000` is clear;
- scene ID is not Training (`0x11`);
- the carried actor's source record `+0x0E` supplies color `0..4`;
- `(selector & 7) >= 2`.

On acceptance it adds `0x10`. If the new selected high nibble exceeds the
low-three-bit availability, it writes `0x10 | availability`, wrapping selection to
tier 1. Maximum-four cycling is exactly `14 -> 24 -> 34 -> 44 -> 14`.

The accepted path then calls `0x8003E760` to re-skin the corresponding token
descriptor, calls `0x8005044C(-16, player)`, and writes `120` to timer
`0x800824A4`. The availability-below-two branch occurs before all four effects.
Therefore a one-tier/locked selector is unchanged and receives no descriptor update,
event `-16`, or timer arm. Static evidence distinguishes this from an unknown visual
or audio label: the event ID is exact, its presentation semantics are not promoted.

## Timeout and writer ownership

When the 120-tick timer reaches zero, `0x8004757C..0x800476A8` processes all five
lanes. Each is rebuilt as `(selector & 0x0F) * 17`, making selected equal maximum
available. Changed lanes are re-skinned; event `-16` is emitted once if any lane
changed. Selection is temporary, while the availability ceiling persists.

The complete direct resident writer classes are:

| Class | Stores | Contract |
|---|---|---|
| level load | `0x80046BEC` | brown `:= 0x11` after the player-block clear |
| timeout normalization | `0x800475C0`, `0x800475F8`, `0x80047630`, `0x80047668`, `0x800476A0` | selected `:=` maximum for five lanes |
| X cycle | `0x80047B6C` | indexed lane write |
| source token upgrades | `0x8005431C`, `0x80054364`, `0x800543E0`, `0x8005445C`, `0x800544F8` | `n=(old+1)&7`, then `(n<<4)|n` |

`0x80053754..0x80053814` contains a second generic upgrade helper with store
`0x80053794`, but the pristine resident image has no call, jump, or literal-pointer
owner for its entry. It is retained as latent code, not counted as an active path.

A compiled C scan of every retail `.BIN` finds no overlay writer. `LEVEL07/LEVEL.BIN`
reads brown and green; `LEVEL09/LEVEL.BIN` reads yellow. Resident readers include the
HUD's brown/blue/green loop and the all-five plant spawner.

## Reset and persistence

Level load calls the memset thunk at `0x80046B68` with player base `0x800A6500` and
length 168, covering all five selectors. The same initializer then writes brown
`0x11` at `0x80046BEC`. The resulting fresh-level array is
`[0x11, 0x00, 0x00, 0x00, 0x00]`.

The respawn handler `0x8005B1BC..0x8005B440` clears many player fields but does not
cover `0x800A6598..0x800A659C`; selectors survive ordinary respawn. No selector-specific
memory-card serialization or restore path exists in the direct frontier. Save states
preserve full RAM by definition and are not original-game persistence evidence.

## Consumer and malformed states

`plant_spawn` at `0x8005BDBC` computes
`color * 4 + selected_output - 1` and indexes the 20-row table at `0x8007A448`.
The compiled C guard confirms all 20 `(type, extra)` rows and the expected five-lane
matrix. The consumer has no selected-range guard.

Natural authored progression supplies maxima `1..4` and values `0x11..0x44`, but the
machine code is not defensive:

- selected zero underflows the lane's table base;
- availability `5..7` is accepted by X and may cross into the next lane or beyond;
- low bit 3 is ignored by X's `&7` comparisons but consumed by timeout's `&0x0F`;
- a selected value already above availability is repaired to tier 1 by one accepted X
  edge when availability is at least 2;
- pickup upgrade arithmetic is modulo 8, relying on authored maximum-four tokens.

These are malformed-state contracts, not promoted natural behaviors.

## Closure boundary and movie request

The reusable static guard is `tools/phase4_a13_static.c`; machine findings are in
`analysis/phase4_a13_static.json`; typed configuration is
`config/phase4_a13_plant_output.yaml`; Canon is [[Seed_plant_output_binding]].

For strict runtime promotion, record two short, normal-speed v4 Interpreter fixtures:

- `movies/Phase4/Interpreter/A13_wrap_timeout.movie.json`: carry a brown seed with
  selector `0x14`, press X through `14/24/34/44/14`, then idle at least 130 active
  gameplay ticks so the selection returns to `0x44`.
- `movies/Phase4/Interpreter/A13_denied_one_tier.movie.json`: carry a brown seed with
  selector `0x11` and press X several times; the byte must remain `0x11` with no
  `0x800824A4` arm.

Do not record more color-lane address-discovery movies. The remaining fixtures test
behavioral controls only.
## Runtime closure update: 2026-08-03

**Disposition:** `substantiated`, `bounded_exhausted`. No additional A13 movie is required.

### Prerequisite capsule and identities

- Retained capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/A13__brown_seed_levels`.
- Manifest SHA-256: `902bfdfffa3dcb6ef11d7ab77405ad306a96a330bb344e85944a46a20f88b1dd`.
- The manifest is complete, untruncated, and its independent full-state control matches.
- Retail serial: `SCUS-94288`.
- Loaded cue SHA-256: `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`.
- Loaded BIN SHA-256: `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`.
- The save-loaded cached cue and BIN hashes match the repository pristine media exactly.
- Retail executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- DuckStation revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` with dirty external-debugger work preserved.
- DuckStation binary SHA-256: `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`.
- Isolated config: `/tmp/duckstation-a13-deny-20260803-1`, port `29413`, token `a13-deny-20260803`.
- Execution was pure `Interpreter` at normal 1x speed. Fast-forward and turbo were false.

### Fixtures

- Denied control: `movies/Phase4/A13_denied_one_tier.movie.json`, SHA-256 `29345e4f76fec168218a15bb1cc942de3ed20a132d880c65291a287eedd6d880`, v4, 398 frames. Its save SHA-256 is `004a018d1c35d1e0e8b2201286262255e13867a886e060435c5b9849e9304f3e`.
- Wrap/timeout control: `movies/Phase4/Interpreter/A13_wrap_timeout.movie.json`, SHA-256 `405efceee50f4ffddb425a06db32f8ea0b7d1187fedc999d0802428bb06089d8`, v4, 897 frames. Its save SHA-256 is `b654b1327dc974b0793d30f552b34b395d43d267fd835982b2a7c5e443f7d3cc`.
- Both movies report `reproducible:true`, `armed_while_paused:false`, `phase_delay_owed:false`, and `truncated:false` when started from their recorded states.
- Cold boot was not required: these are narrow pristine-runtime controls with no code, disc, or asset change.

### One-tier denial

The deny movie began and ended with brown selector `0x11` and timer `0`. Eight Cross rising-edge paths reached through `0x80047B48`. The full handler range retained 3,760 events, but the selector and timer write watches each retained zero events. All three logs were untruncated. This confirms that availability below tier 2 is a silent deny before the selector store, timer arm, descriptor update, or feedback event.

An excluded pilot replay ran beyond movie completion because a quiet client suppressed the polling JSON. Its late final state was only corroborative and contributes no timing evidence. The armed replay above used working real-time polling and is the causal negative control.

### Wrap, re-arm, freeze, countdown, and expiry

- Emulator frame `25273`: `0x80047B6C` wrote selector `0x44 -> 0x14`; `0x80047B9C` wrote timer `0 -> 120`.
- Emulator frame `25309`: `0x80047B6C` wrote selector `0x14 -> 0x24`; `0x80047B9C` re-armed timer `120 -> 120`.
- The timer remained at `120` while Flik stayed within the seed/interactable proximity latch.
- Emulator frame `25685`: the last nonzero candidate write stored `0x800A0854` at `0x8008242C`.
- Emulator frame `25687`: `0x800472B8` cleared `0x8008242C` and no candidate store restored it. At the same gameplay tick, 384 cycles later, `0x80047578` performed the first timer write `120 -> 119`.
- The timer then decremented exactly 120 times, once every two video frames, through emulator frame `25925`.
- Emulator frame `25925`: `0x80047578` wrote timer `1 -> 0`; 237 cycles later `0x800475C0` wrote selector `0x24 -> 0x44`.
- The wrap trace retained exactly three selector writes and 122 timer writes: two arms plus 120 decrements. It was not truncated.

### C-based static explanation of the apparent delayed timer

`tools/phase4_a13_timeout_gate.c` verifies every owner of `gp+0x694`, runtime address `0x8008242C`, against the hash-pinned retail executable. The relevant owner beginning at `0x80047284` does this each gameplay tick:

1. `0x800472B8` clears the nearest-eligible-actor latch.
2. It scans actors requiring `actor+0x5C & 0x20`, rejects state `actor+0x40 == 4`, computes scaled squared distance, and keeps the nearest candidate below `0x57E40` at `0x8004736C`. A direct path can store at `0x80047398`.
3. `0x80047568` loads that latch.
4. `0x80047570` branches over the timer store whenever the latch is nonzero.
5. Only a zero latch reaches `0x80047578`, which commits `timer - 1`.

The timer therefore starts immediately but its countdown is frozen by a nearby eligible actor. This corrects the earlier simpler wording that the timeout always runs immediately after selection. The latch is generic, not seed-specific. In this movie its two observed candidates, `0x800A0854` and `0x800A08D8`, were state `3`, flags `0x4031`, and referenced descriptors with color byte `0` (brown), matching the nearby brown seed actors.

### Closure basis

- The earlier C state-space pass exhausts all natural packed selector states: 192 accepted and 64 denied cases.
- The v4 Interpreter denial control proves the low-availability negative branch.
- The v4 Interpreter wrap control proves maximum-to-tier-1 wrap, ordinary advance, timer re-arm, proximity freeze, the complete 120-tick countdown, and normalization to maximum.
- Existing static work covers all selector writers/readers, level initialization, respawn preservation, malformed states, plant-table consumers, and retail overlay references.
- Running every natural selector transition live would repeat the already exhaustive C proof with minimal additional return. It is not required for bounded exhaustion.

Normal-speed polling paused the clean and armed runs a few frames after movie completion, so this update does not claim a new exact final-cycle-neutral comparison. The state progression and instruction-attributed writes matched, and all causal logs used above report `truncated:false`.

Structured evidence is in `analysis/phase4_a13_runtime.json`; the declarative contract is in `config/phase4_a13_runtime.yaml`.
