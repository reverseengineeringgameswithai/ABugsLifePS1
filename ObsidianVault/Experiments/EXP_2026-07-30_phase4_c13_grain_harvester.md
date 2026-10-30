---
type: experiment
status: complete
date: 2026-07-30
system: grain harvester
phase: 4
artifacts:
  - analysis/phase4_c13_harvester.json
  - analysis/phase4_c13_harvester_live.json
  - config/phase4_c13_harvester.yaml
  - movies/Phase4/c13_GRAIN_HARVESTER.annotations.yaml
---

# Phase 4 C13 grain-harvester reconstruction

## Question

What does the operator's C13 movie establish about equip, attraction,
disengagement, and enemy contact on the pristine game?

## Provenance

- Authority: hash-verified pristine retail `SCUS-94288`; ALLMODS was not used.
- Movie SHA-256: `849ad9a4092502dcbac280f3bf92f61612d72bdb3718b0f0ad84b4c4dfc005ac`.
- Start-state SHA-256:
  `abb7eb74ce316d437f5ee6c168d1e9f876d0fe11ec30ffa2273bfaeec31666ce`;
  centrally media-classified and state-inspected before load.
- Annotation SHA-256:
  `fc625569d5fd008dc1048814045ac61b68efd42ce655b8e91b27c47d474f6811`.
- Capsule: external
  `trace-capsules/Phase4/v2/c13_GRAIN_HARVESTER`, manifest SHA-256
  `486be1c2d5ced63db19348806821b7079e27bf60cee3a63a80b2d2a72326adc7`,
  tree SHA-256
  `c03075522ba130fe5d858ee8c01952a488d9a8e50b48b3159ca8540cb33458fd`;
  complete and control-matched.
- Pristine staged executable SHA-256:
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

Movies, saves, capsule chunks, transient anchors, and tokens remain external or
operator-local and must not be committed.

## Method

The capsule was validated and queried first. `tools/phase4_c13_harvester.py`
reconstructs frames `0..617`, checks the annotated input edge and visual
windows, follows every type-`0x3f` source consumption into its newly allocated
contact slot, and joins those contacts to grain-count increments. It also
checks every cited resident instruction against the pristine executable.

The movie did not contain the two requested post-movie behaviors. That named
missing domain justified one isolated live escalation: from a single transient
movie-end anchor, run an uninstrumented Cross continuation, an equipped bee
continuation, and a matched immediate-Cross bee control. The instance used a
fresh `/tmp` config, dedicated port, ephemeral token, mounted-media hash
verification, and owned-PID cleanup.

Access logging was also tested tick-tight. It suppressed the Cross edge and
returned no writer event; a cycle-neutral `movie.traceToFrame` attempt on a
four-frame state-based movie reported `movie_frame: 0` rather than advancing.
Neither failed attribution route is used as behavioral evidence.

## Result

- Square frame `80`; state and bit rise at frame `83`; visible equip begins
  around frame `87`.
- Nine grains cross the exact native `0x15F8F` gate, become ctor-`0x51`
  contacts, and increment count `0 → 9`.
- Cross clears state `1 → 0` and bit `0x80`.
- Equipped bee: HP `4 → 998` at `+136`, retirement at `+222`.
- Immediate-Cross control: the same bee remains HP `4` and live.

The finding is promoted to [[SYS_grain_harvester]],
`config/phase4_c13_harvester.yaml`, the existing powerup-flags entry in
`config/semantic_state.yaml`, `src_re/grain_harvester_80051db4.c`, and the C13
mechanics row. New Phase-3 lifetime/record fields are intentionally deferred
until their retained live censuses can be regenerated; they were not
hand-blessed. The row is **partial**, not closed.

## Reproduction

```bash
python3 tools/phase4_c13_harvester.py --check
python3 -m pytest -q tests/test_phase4_c13_harvester.py
```

The live complement regenerates only against a fresh isolated pristine
instance:

```bash
python3 tools/phase4_c13_harvester_live.py \
  --port <dedicated> --token <ephemeral> \
  --config-dir /tmp/<fresh-c13-config> --instance-state recreated
```

## Residuals

Exact ctor-`0x51` steering and Cross clearing writers, enemy-family breadth,
all-level availability, and render/animation/audio/reset ownership remain open.

## 2026-08-02 C static-ASM continuation

The former exact-writer residuals are closed by
[[EXP_2026-08-02_phase4_c13_bounded_exhaustion]]. A C scan correlated the nine
capsule contacts with pristine ASM and retail words. Grain target `-1` selects
the shared homing updater; Y/X/Z write at `0x8005A4C8`, `0x8005A548`, and
`0x8005A56C`. Cross clears bit `0x80` at `0x8004A94C`, after which the ordinary
positive-slot tick at `0x80048654` clears the no-longer-maintained state `1`.

C13 is now **partial, high-yield row-specific work exhausted**. No Interpreter movie is required
unless a specific deferred level, enemy family, or persistence behavior is promoted
to an active question.

### Strict-closure correction - 2026-08-02

C13 remains partial; the prior high-value bounded-exhaustion statement did not
satisfy the Phase 4 campaign DoD. C static RAW analysis bounds applicability to
six placements (operator levels 1,2,5,8,10,11) with identical non-position
records, while retained behavioral evidence covers 1/6. The shared pointer
frontier remains OPEN at 251 / 149 / 4,967; see
analysis/phase4_c13_dod_scorecard.json. No new movie is requested while that
independent frontier makes strict closure impossible.
