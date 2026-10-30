---
kind: experiment
id: EXP_2026-08-02_phase4_d02_actor20
name: Phase 4 D02 enemy actor +0x20 classification
status: partial
created: 2026-08-02
updated: 2026-08-02
confidence: confirmed_negative
source_state: original_game_retained_capsules
artifacts:
  - analysis/phase4_d02_actor20.json
  - tools/phase4_d02_actor20_capsule.c
---

# Phase 4 D02 enemy actor `+0x20` classification

## Scope and decision

D02 is a broad unclassified-record row, so this pass selected one bounded, gameplay-relevant unknown: enemy actor record `+0x20`, located between confirmed X velocity at `+0x1C` and Z velocity at `+0x24`.

**Confirmed negative:** `+0x20` is not a direct per-frame Y delta analogous to the X and Z fields. D02 remains partial because the positive identity of the field is still open. The next required domain is exact instruction attribution, which needs the named Interpreter movie below.

## Capsule-first methodology

Six existing v3 capsules were validated and queried before considering live replay:

- `D11_grub_contact_kill`
- `D15_daddy_long_legs_contact_kill`
- `D08_fly_contact_kill`
- `D11_mite_contact_kill`
- `B11_blue_shooter_enemy`
- `B13_mine_enemy`

Every manifest and capture reports complete, untruncated, and error-free. Clean controls have no mismatches and report identical cycle, frame, RAM, and registers. A compiled C reader reconstructed 2,895 frame records and checked 8,685 RAM/VRAM/SPU domain hashes with zero mismatches.

The C analyzer auto-located the 40 x `0x84` actor pool at `0x8009FD80`. Across 77,071 active actor samples:

| Relation on moved frames | Exact | Total | Rate |
|---|---:|---:|---:|
| `+0x1C == delta X` | 2,003 | 2,127 | 94.2% |
| `+0x24 == delta Z` | 2,006 | 2,127 | 94.3% |
| `+0x20 == delta Y` | 61 | 1,431 | 4.3% |

The X/Z results reproduce the known controls, including expected collision/clamp mismatches. The Y candidate fails by a wide margin across grounded, contact, shooter, mine, mite, grub, daddy-long-legs, and fly contexts. `+0x20` is nonzero in 9,811 samples and spans `-3328..4096`, so it is not merely always-zero padding or one fixed grounded constant.

Observation: `+0x20` is motion-related in layout but not equal to the final frame-boundary Y displacement.

Inference only: it could be an input to vertical integration, a target/extent, or another state value. No positive name is promoted without writer/reader attribution.

## Rejected first model

The first C model incorrectly assumed actor position began at `+0x00`. It produced 0 exact X and Z control matches and was rejected immediately. Source SHA-256 `8df6417a668ac9f11bdc1d648186ec78ee29e64fdefe889cd37101ac4ae35d87`; output SHA-256 `570850cf553c0f098405014efba6a0d724524ae1bbdc07f9ae333bd201cc860e`. None of its Y conclusions were retained.

The corrected model uses actor ID at `+0x00` and XYZ at `+0x04/+0x08/+0x0C`, matching the Phase 3 generator and rediscovering the X/Z controls.

## Static reconstruction census

A separate compiled C search covered 65 `src_re` C/H files and 10,792 lines. It found no existing actor-specific attribution for `+0x20`. This is a negative over the current reconstruction corpus, not a whole-program alias proof and not a substitute for ASM access attribution.

## Evidence and reproduction

Transient root: `/tmp/abl-phase4-d02-20260802`

- accepted C source SHA-256: `7d57dcdf9b2e2a748f7dc8d6891f9f45ba3f614071abc118914c6667aabbe3fb`
- compiled analyzer SHA-256: `7e22e96e9ad55885bf9cebfe3f1fb1e67f9aeda2d6831581b263c283b54248df`
- grub/daddy output SHA-256: `449988ff2c9fd6794da042e8dd3f681b97f261004fd0fc988fe8d2000506c877`
- fly output SHA-256: `34dfa3dc0edc79fd92e262c03c8a7b003a19ecd675d0270925d3c31f477a171c`
- mite/shooter/mine output SHA-256: `402a739fb0cf0fc09b57720a6942ffb100bd741561d225221e7d118976f8931c`
- source-census output SHA-256: `b89e56ce06dd3cefd559a624334e15589236182a727e1e4419a72f63a3dd3c79`

```bash
gcc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_d02_actor20_capsule.c -o /tmp/phase4_d02_actor20_capsule -lzstd -lcrypto
/tmp/phase4_d02_actor20_capsule ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/D11_grub_contact_kill
```

## Exact Interpreter movie request

To positively identify `+0x20`, record approximately 8-10 seconds from the existing B13 mine start anchor in **Interpreter mode**, preserving the enemy movement/contact sequence, and save it as:

`phase4/movies/interpreter/D02_actor20_B13.movie.json`

B13 is selected because its retained capsule contains 450 Y-moving frames and the broadest `+0x20` range (`18..4096`). The old source movie is CachedInterpreter and must not be armed with `execTrace`. The new movie will be replayed at normal speed, with focused access watches on active actor `+0x20` fields; exported events will be classified in C against the existing ASM.

## Interpreter movie closure pass (2026-08-02)

### Corrected reproduction

The operator corrected the initial reproduction assumption: the gold-colored Mine Plant output does **not** explode merely because Flik jumps nearby. It explodes after being thrown or after an enemy approaches it. The accepted movie therefore records Flik throwing the mine at input `304`; it shortly collides with a spider.

Preserved operator evidence (do not commit as ordinary source):

- Movie: `movies/Phase4/Interpreter/D02.movie.json`, SHA-256 `5e7c4098dd95e7ae5f0d4c85d56877181715ceba781ed0fda11926fbe349b09e`
- State: `movies/Phase4/Interpreter/D02.movie.sav`, SHA-256 `6e6c9c221cdb93feb419f80ed611ae2ef38f7849a750d97c13f60d9ca8cebb4a`
- Movie v4, `armed_while_paused=true`, `phase_delay_owed=true`, 459 inputs, initial emulator frame `266857`
- Recording/replay mode: Interpreter

The movie is state-anchored because this is a narrow runtime attribution experiment. No code, disc, or asset changed, so cold boot is not required.

### Accepted live control

The accepted r4 run used a fresh config at `/tmp/abl-d02-actor20-20260802-r4`, dedicated port/token, the pristine `SCUS-94288` cue (SHA-1 `25adb139e50ba28c2d9c1ecab4528e9cf004b1d5`), and DuckStation binary SHA-256 `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`. Both passes used `debugger.resume` plus status polling at normal speed, never `movie.advanceToFrame`.

Clean and armed runs ended identically:

| Check | Clean | Armed |
|---|---:|---:|
| Final emulator frame | `267319` | `267319` |
| Final cycle | `151356445709` | `151356445709` |
| Full 2 MiB RAM SHA-256 | `de03646f236492b97ce7ddd38e99a9453608103f0fa373517a7a14e7b7e35ef4` | same |

Cycle delta is exactly zero. The 40 per-record `+0x20` read/write watches collected 1,991 events (1,178 reads, 813 writes), 23 actual instruction sites, and 417 events in movie inputs 296 through 380. The access ring reports `truncated=false`. Traced record indices were 1/2/11/15; their sampled IDs were 11/23/15/9. Slot 15 is inactive (`id=0`) by input 440, consistent with the operator-observed enemy collision/lifecycle, but that observation is not needed to name the field.

Rejected collection attempts are not evidence: r2 lost its declared output when the outer execution session terminated; r3 completed only the clean replay and the collector incorrectly treated DuckStation's normal end-of-movie cursor reset (`458 -> 0`) as desync. r4 corrected the collector condition and completed both control arms.

### C against retail ASM

`tools/phase4_d02_actor20_trace.c` consumes the normalized access events and reads retail `REBUILD/files/SCUS_942.88` directly as a PS-X EXE (`0x80010000` load base). It verifies each traced instruction word before decoding surrounding MIPS instructions.

Confirmed flows:

- `0x8004BF14..0x8004BF20`: add `0x100` to actor `+0x20`.
- `0x8004BF24..0x8004BF38`: cap actor `+0x20` at `0x1000`.
- `0x8004BFA4..0x8004BFB0`: add actor `+0x20` directly to actor Y (`+0x08`).
- `0x8004C02C..0x8004C04C`: after the collision integrator call, clear `+0x20` when its absolute value is below 2.
- `0x8004CF34..0x8004CF50`: a second actor path applies the same `+0x100` step and `0x1000` cap.
- `0x8004CF54..0x8004CF6C`: that path also adds `+0x20` into the Y value stored at actor `+0x08`.
- `0x8004D024..0x8004D02C`: a collision/result branch clears `+0x20`.
- `0x80049E00..0x80049E0C`: an airborne setup path stores either `-0xD00` or `-0xB60` to `+0x20`.
- Generic vector consumers at `0x80035DA4/0x80035E30/0x80035E3C` and `0x80035F40/0x80035FD0/0x80035FDC` access the watched word as the `+4` Y component of the XYZ velocity vector rooted at actor `+0x1C`.

Therefore actor record `+0x20` is confirmed as **signed vertical velocity (`velocity_y`)**: negative values are launch/upward impulses, gravity advances it by `+0x100` toward a `+0x1000` downward cap, actor update code consumes it in Y integration, and settle/collision paths clear it.

The earlier six-capsule result, where `+0x20 == frame-boundary deltaY` held for only 4.3% of moved samples, remains a valid negative result against *direct frame-delta equality*. It does not contradict `velocity_y`: the retail ASM proves that collision/update handlers consume, cap, and clear the value within the update before the next frame-boundary sample.

### Hashes and commands

- Retail EXE SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- Raw capture summary SHA-256: `fe8a1ee32c5cac40be4231d88f36c0c7ae37ee0b64f1436cd2f8e8572c4c0a56`
- Raw access events SHA-256: `3569cc636f32b05b14f9e0ee8ff743ecd9618287e58defbceec0877ad3aec407`
- C source SHA-256: `934b0f319de179a444d401a3ff78df6b7414181782fb5b53b95716805894f8e0`
- C binary SHA-256: `c35927170696d8b0dc2a8d6049e6e88e13b04bd238856dc056e55a22240d388c`
- C output SHA-256: `c26a531c2aa2117957657f3f790c156f7a31b87322ffa48ef8c469799f886161`

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_d02_actor20_trace.c -o /tmp/phase4_d02_actor20_trace
/tmp/phase4_d02_actor20_trace /tmp/abl-d02-actor20-20260802-r4/evidence/access_events.tsv REBUILD/files/SCUS_942.88
```

Structured preservation/closure record: `analysis/phase4_d02_actor20_runtime.json`.

### D02 disposition

The `+0x20` bounded subproblem is exhausted: static ownership, runtime reads/writes, initialization, integration, cap, and collision/settle clearing all agree, and no additional Interpreter movie is required for this field.

The broad D02 inventory row remains **substantiated partial**, not falsely complete, because other unclassified actor/object kinds remain category-wide. Those residual taxonomy items are low-return enumeration rather than a blocker on `+0x20`. Bank this result and move to another Phase 4 row.

## Deep closure audit (2026-08-02)

A final C semantic guard audited the already verified retail instruction words, MIPS delay slots, all runtime access-site counts, and competing field interpretations. It did not replay DuckStation or require another movie.

### Complete runtime-site accounting

Every accepted access is classified:

- Reads: 1,178 of 1,178 classified across 15 instruction sites; zero unexplained.
- Writes: 813 of 813 classified across 8 instruction sites; zero unexplained.
- The eight runtime writers are generic Y-vector transforms (`0x80035E3C`, `0x80035FDC`), initialization/impulse (`0x80049D90`, `0x80049E0C`), the two gravity paths (`0x8004BF20`, `0x8004CF40`), near-zero settling (`0x8004C04C`), and the second path clear (`0x8004D02C`).
- Static cap stores at `0x8004BF38` and `0x8004CF50` remain verified retail branches even though the accepted movie did not drive velocity beyond the cap.

This closes the possibility of an unexplained runtime writer assigning a competing meaning during the fixture.

### Delay-slot precision correction

`0x8004D02C` is the delay slot of the branch at `0x8004D028`. On MIPS it executes whether the branch is taken or not once control reaches that path. Therefore the precise statement is **path-level clear**, not "clear conditional on the branch result." This corrects the narrower wording in the first-pass summary without changing the field identification.

`0x8004C04C` is different: its zero store occurs only on the fall-through selected by `abs(velocity_y) < 2`, so that site is a true near-zero settle clear.

### Alternative-hypothesis audit

| Hypothesis | Disposition |
|---|---|
| Padding/unused | Rejected by 1,991 runtime accesses |
| Target, extent, or collision radius | Rejected by signed launch impulses, gravity step/cap, and direct Y integration |
| Exact frame-boundary `deltaY` | Rejected by the six-capsule 4.3% control |
| Generic accumulator with no velocity meaning | Less specific than the complete XYZ-vector, impulse, gravity, integration, and clearing contract |
| Signed `velocity_y` | Confirmed |

The only unresolved details are exact fixed-point/world-unit scale and per-species update cadence outside the two observed handlers. Neither changes field ownership or semantics, and pursuing them would be low-return Phase 4 work.

C guard hashes:

- Source SHA-256: `8632411fa54a914c72d52516f45a57c7b0badf3ca2e4d9f15120d9570028a809`
- Binary SHA-256: `466a9e10841a2a6eab4a229cd821a5f8fb6c0368409eef2aea2c922ca624c08b`
- Output SHA-256: `5d91f09adfcb986ff543a7317270f38b19de60d0b76ff6a7a77b73bd98d511a6`

Structured audit: `analysis/phase4_d02_actor20_deep_audit.json`.

**Final disposition:** the `+0x20` field is exhausted and needs no additional movie. The broad D02 taxonomy row remains substantiated partial only because unrelated unclassified kinds remain; bank this field and move on.

## Independent verification (2026-08-03)

Per the operator's "go deeper into confirming D02 is good to move on," checked for
corroborating or conflicting evidence beyond this investigation's own tooling before
accepting it.

**Cross-row corroboration**: `B02_propeller_plant` — a completely separate investigation,
different fixture, different methodology — independently found "each qualifying tick
subtracts 512 from actor+0x20," a propeller lift mechanic. That's exactly consistent with
this row's own sign convention (negative = upward): two unrelated mechanics (gravity/
collision here, propeller lift there) converge on the same field identity without either
citing the other.

**Independent live re-sample**: replayed the already-committed `D02.movie.json` again in a
fresh isolated instance, but with a newly-written polling script (not the banked accessLog
capture) sampling actor Y and `+0x20` every 15 frames. Slot 1 (actor id 11) shows a clean
projectile arc — `vy` samples `-3072 → -1024 → 768 → 0`, each step consistent with `+256`/tick
gravity, settling to exactly 0. The `-3072` sample is the documented `-0xD00` (`-3328`)
airborne-impulse constant plus exactly one gravity tick (`-3328+256=-3072`) — an exact
arithmetic match, not just qualitative agreement. Slot 15's actor id also independently
reproduces the banked claim that it's removed from the live table by the same point.

**One gap found, deliberately not fixed here**: `config/record_types.yaml` and its generated
`analysis/phase3_record_types.json` still assert "`+0x20` remains unknown" — now stale.
`tools/phase3_contradictions.py` has an explicit assertion checking for that literal
substring, as part of a separately-maintained Phase 3 contradiction-ledger gate with other
agents' own concurrent in-progress edits this session. Resolving it needs coordinated updates
across the config, the regenerator, and that assertion together — a Phase-3-track change, not
a Phase-4 row addition. Flagged for whoever owns that track, not touched here.

**Conclusion**: independent re-sampling and an unrelated cross-row finding both corroborate
the velocity_y identification with exact numeric agreement, not just directional consistency.
Good to move on. Full detail: `analysis/phase4_d02_actor20.json`'s
`INDEPENDENT_VERIFICATION_2026-08-03`.
