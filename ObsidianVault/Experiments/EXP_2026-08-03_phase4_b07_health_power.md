---
title: "Phase 4 B07 - blue tier-2 health power"
date: 2026-08-03
phase: 4
row: B07_health_power
status: complete
confidence: substantiated-partial
disposition: bounded-exhausted-move-on
---

# Phase 4 B07 - blue tier-2 health power

## Question

Close the high-value unknowns in B07: exact heal amount and cap behavior, the blue tier-2 production binding, production cadence, hostile-spike coexistence, and sufficient campaign applicability. The row must remain distinct from [[EXP_2026-08-03_phase4_c12_health_leaves]], which owns the generic health-leaf pickup.

## Conclusion

B07 is a **substantiated Partial and bounded-exhausted**. Blue tier 2 selects type-7 plant extra `0x3000`. Each qualifying type-7 activation emits exactly one object: constructor 38 health leaf for three of four RNG low-bit outcomes, or constructor 59 hostile spike when `(rng_byte & 3) == 0`. Collecting constructor 38 executes action 9, adds exactly one to true health `s16 0x800A6594`, and has no pickup-side maximum-health test or clamp. The accepted B07 capsule supplies the natural `3 -> 4` positive control.

No new DuckStation run or Interpreter movie is required. The remaining strict-Full controls are low-return evidence breadth, not unresolved row behavior.

## Method and evidence boundary

Phase 4 capsule-first methodology was followed. The retained capsules were validated before code investigation, their frame-boundary RAM was queried with the official reader, and a C reducer plus C pristine-EXE analyzers handled the repeated mathematical and block-flow work. No live replay was escalated because no named evidence domain remained missing.

Observation, inference, and causal confirmation are separated below. A capsule is used only for frame-boundary state evidence; exact instruction behavior comes from the pristine executable, not from passive block summaries.

## Capsule acceptance

### B07 partial-to-full control

- Capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B07_health_partial_full`
- Manifest SHA-256: `bde5cc0ca130e7e74a33c6cd1f556a4e4e2822b1dd2197fea8f4a69b28fc26f7`
- Movie SHA-256: `d587fec32c94dd618302cdcaf0f24f3c10007d1a4ccff321a50de4637eb59817`
- State SHA-256: `2de4884672ebc3b1a90ede89315881e5993cba21a203e57a3138421065611a9d`
- `complete=true`, `truncated=false`, `error=""`, 324 retained frame states, and 11,553,724 passive blocks.
- Movie is reproducible and untruncated on pristine `SCUS-94288`.
- Independent control mismatch map is empty.
- Capsule and control match for full machine state, RAM, registers, SPU RAM, and VRAM.

### Blue seed tier control

- Capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/A13__blue_seed_levels`
- Manifest SHA-256: `81053aba5b5ec9bb9e33fbb944fffd09d9df2ed95528ff8dafb931e042b7f17d`
- Movie SHA-256: `79d0aa0d26bcd760316f6bf685bf781f571ec63806a09d78be84d36ab01f5c3`
- State SHA-256: `9198c8c3daa896813f0198ecb2a1b7068c7035116aed0aadbc1072ffdb01f5c3`
- `complete=true`, `truncated=false`, `error=""`, 3,796 retained frames, and matching control fingerprints in every retained domain.

The pristine executable SHA-256 used by the C analyzers is `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`. The auxiliary pristine `health_test.sav` SHA-256 is `b8df83d76fce8da42c4020909219be27aa3b8319542e63ff6baea05a3fa4e6c7`.

## Observation

Offline boundary reads show true health at `0x800A6594` changing once:

| Movie frame | Emulator frame | Health |
|---:|---:|---:|
| 76 | 212376 | 3 |
| 77 | 212377 | 4 |
| 78 | 212378 | 4 |
| final | 212623 | 4 |

The word at `0x800A6590` remains `0x00000008` across the pickup. It is not a B07 health-power flag. The older `0x800A7E2A` binding is also not true health; it is a HUD pulse field.

The A13 capsule bounds the B2 plant interval at emulator frames `111470..112184`. The selected type-7 slot is initialized in this window and its qualifying state changes occur at frames `112074` and `112084`. These frame-boundary events support a single activation episode; they are not used as exact PC attribution.

## C-based pristine ASM confirmation

### Tier selection and object production

The blue pair-table entry at `0x8007A45C` is plant type 7 with extra `0x3000`. Selector `0x8005BDBC` reads the source color and the packed counter high nibble, chooses `color * 4 + tier - 1`, stores the selected type at `0x8005BE90`, and stores the extra at `0x8005BF3C`.

The type-7 handler at `0x8005C744..0x8005C818` admits a production event only for the qualifying plant state. It advances the RNG cursor once and emits one object:

- `(rng_byte & 3) != 0`: `(signed(extra) >> 12) + 35`; B07 extra `0x3000` therefore selects constructor 38.
- `(rng_byte & 3) == 0`: constructor 59 hostile spike.

The exact per-activation split is therefore **3/4 health leaf and 1/4 hostile spike**. The two outcomes coexist within the same B07 activation path; hostile spike is not a persistent alternate mode. The special already-active fallback associated with extra bit `0x4000` belongs to B09 and does not apply to B07 extra `0x3000`.

The handler contains no recurrence timer. It emits exactly one object per qualifying invocation, then returns through the common plant path. The interval between separate invocations belongs to the shared upstream plant-state scheduler, not a B07-specific timer. This resolves B07 cadence at the row boundary without expanding into a low-return reconstruction of the shared animation scheduler.

### Heal law and cap

Constructor 38 metadata selects action 9. Its handler begins at `0x80058864`:

- `0x80058880`: load halfword health from `0x800A6594`.
- `0x80058884`: prepare SFX 62.
- `0x80058888`: add exactly 1.
- `0x80058890`: store the result as a halfword.

There is no current-health comparison, maximum-health gate, or clamp in action 9. At this layer, collecting a leaf at health 4 writes 5. Constructor metadata gives a 200-logic-tick lifetime, approximately 6.67 seconds at 30 Hz, before the shared pickup tail expires it.

This statically proves the instruction law. The capsule independently proves that a naturally collected B07 output follows it for `3 -> 4`.

## Campaign applicability

The existing campaign inventory gives a visible type-7 plant model in operator levels `1, 3, 5, 6, 7, 8, 10, 13, 14, 15`, or 10/15 levels. Levels `1, 5, 6, 8, 10, 13, 15`, or 7/15, contain at least two locally authored blue tokens and can reach tier 2 from zero locally. The packed blue counter persists across levels, extending B07 selection to later type-7 plants after the tier has already been unlocked.

## Bounded-exhaustion decision

Resolved for B07:

- Exact heal delta: `+1`.
- Exact true-health binding: `s16 0x800A6594`.
- Cap behavior: no pickup-side cap or health gate; static `4 -> 5`.
- Tier binding: blue tier 2, type 7, extra `0x3000`, constructor 38.
- Cadence: one emission per qualifying activation; no B07-local recurrence timer.
- Hostile-spike coexistence: exact 1/4 spike versus 3/4 leaf branch.
- Natural runtime control: `3 -> 4`.
- Campaign applicability: bounded from the model/token inventory and persistent counter.

Strict-Full evidence would add a natural full-health visual control, repeated live sampling of the 1/4 spike branch, and reconstruction of the shared upstream plant-state timing. None can change the row-specific law now established by exact instructions, and their return is minimal. Keep the roadmap status Partial for breadth honesty, bank the limitation, and move on.

## Transient analysis artifacts

The transient C tools were stored under `/tmp`; the durable conclusions are in this note and `analysis/phase4_b07_health_power.json`.

| Artifact | SHA-256 |
|---|---|
| `/tmp/phase4_b07_static.c` | `6d5055691c821be57c2d8848fdbbbbab3e1e88089391608a9465fb63756caf56` |
| `/tmp/phase4_b07_static` | `c989478ff1d414c1a08c50d90032e61e959eae28d7340af0bfa3b857f2422b9d` |
| `/tmp/phase4_b07_static.out` | `0217f0e2baeaabb85687a5e7fe28567f34d4d93db91499713026a26333d4a053` |
| `/tmp/phase4_b07_static_v2.c` | `c976df74ca866f31ef6ff4d8884e4a564f3dd17151aca144a07a1163bb6e3a80` |
| `/tmp/phase4_b07_static_v2` | `6960e11a58d88e8f7bc713b6ecad25a6d2ce122775ed45897f2881f1d1b9bbf1` |
| `/tmp/phase4_b07_static_v2.out` | `facbc1d910ae2bb617419d8bc3e9e7ad405ce1418a4f4342c7568c1618b57888` |
| `/tmp/phase4_b07_production.c` | `2b2c3ffeb1f59693cbd2a27c9063d9760fb570bbbb2987bd9f1267f0b2436582` |
| `/tmp/phase4_b07_production` | `8cccd878ef1ee5a0b4ce945716c7fc5282721a6c1bb1601b9085b3126a5d79fa` |
| `/tmp/phase4_b07_production.out` | `7a4998ab19d4e6692c3251930661d41ede2b8c83d916dc693d9666138b524d1a` |
| `/tmp/phase4_b07_flow_join.c` | `99e9b1e64a700cf4a5bcffa46286172796409afcd2d730c092d5bfa3f684e91f` |
| `/tmp/phase4_b07_flow_join` | `cb6536ce645f279468b31356cb49bcfa639ca5f3de317fed68154c00bacb632a` |
| `/tmp/phase4_b07_flow_join.out` | `a835343f10b93d7eb7e3c95655f19f9e4348166ea9f7937b150bedbd094c1d3e` |

Offline query outputs retained in `/tmp` include capsule summary SHA-256 `d1a056452accd4d55fecc907e59a25a1e03bdd98dd15e6dbb267988c0695592f`, health changes `638229e5827e457702a61ef096527b24db0b734830694ae516dfc04e9fa0a7cd`, health boundary reads `f29aa4d56ff524f8017b76c44c5789ad75c29cf1c9ff149b8fe4baccbe458836`, and blue-capsule summary `07348ea5e83ab28041d384475839d93fa9d4de08812175ffc7f80e5b3211cb3a`.

## Durable links

- [[SYS_blue_health_power]]
- [[EXP_2026-08-03_phase4_c12_health_leaves]]
- `analysis/phase4_b07_health_power.json`
- `analysis/phase4_b06_b08_applicable_levels.json`
