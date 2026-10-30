---
kind: experiment
id: EXP_2026-08-02_phase4_d10_spider_chain
name: Phase 4 D10 spider chain and Bonus 1 handoff closure
status: confirmed
created: 2026-08-02
updated: 2026-08-02
confidence: confirmed
source_state: original_game_static_and_retained_capsule
systems:
  - SYS_bonus_unlock_challenges
artifacts:
  - analysis/phase4_d10_spider_chain.json
  - tools/phase4_d10_capsule.c
  - tools/scenarios/duckstation/bonus1_five_spider_stomps.yaml
---

# Phase 4 D10 spider chain and Bonus 1 handoff closure

## Decision and scope

D10 is confirmed for the scoped claim: qualifying Training spider interactions, the five-event counter, Bonus 1 unlock, handoff to scene `0x10`, commit of the high earned guard, and return to the journey menu. The internal rules of the playable bonus stage, FMV behavior, and persistence across a power cycle are separate systems and are not silently claimed here.

No live DuckStation escalation was needed. The relevant retained capsule is valid and covers the complete route. Its source movie was forced to CachedInterpreter, so it remains offline/poll-only evidence and must not be replayed with `execTrace`.

## Capsule validation and C reconstruction

Capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/bonus-objectives-v2-20260719/Bonus_Level_01`

The manifest reports `complete=true`; capture status reports `complete=true`, `truncated=false`, and an empty error. It pins pristine SCUS-94288 media, movie SHA-256 `37083359bf7319acd323f3980fa96a6b0a676909209e2adf7a7986fe738f10cc`, and start-state SHA-256 `9d117f3b5780a4b9ecaf57b2491b600b662e7891a6a04ebc83f2d76895da95c1`. Its clean control fingerprints are preserved in the manifest.

A compiled C reader reconstructed 3,654 frame records, checked all 10,962 RAM/VRAM/SPU frame-domain hashes, and found zero mismatches. Passive flow represented 145,850,969 executed instructions.

| Movie frame | Evidence |
|---:|---|
| 128 | stomp counter `0 -> 1` |
| 352 | `1 -> 2` |
| 590 | `2 -> 3` |
| 742 | `3 -> 4` |
| 1072 | `4 -> 0`; low flag `0x02`; latch `0 -> 6`; fade begins |
| 1131 | scene `0x11 -> 0x10` |
| 1722 | transition latch `6 -> 0` |
| 2742 | flags `0x02 -> 0x22`, committing the high earned guard |
| 3206 | scene `0x10 -> 0`, returning to the journey menu |

Basic-block flow in the counter range was internally consistent: `0x8004B35C`, `0x8004B378`, and `0x8004B38C` each executed on five frames, while the success block at `0x8004B3B4` executed once.

## C-assisted ASM result

The bounded ASM slice is exact:

- `0x8004B31C` reads the interaction record's signed halfword at `+0x0A`; nonzero reaches the bonus counter path.
- `0x8004B36C` rejects already-earned bit `0x20`.
- `0x8004B384` rejects scene `0x10`.
- `0x8004B398..0x8004B3A8` publishes progress `old_count+114` and increments the counter.
- `0x8004B3AC` compares the new value with exactly 5.
- `0x8004B3B4` ORs low unlock bit `0x02`.
- `0x8004B3C0` writes transition latch 6.
- `0x8004B3CC` writes fade 30.
- `0x8004B3D0` clears the counter after success.

A second compiled C census scanned 2,261 other ASM files and 226,254 lines for direct GP-relative references to counter `0x8008223C` (`gp+0x4A4`). It found only unconditional clears at `0x8004A6C4` and `0x8004A854` in the shared transition/reset area. No alternate direct increment was found. This is deliberately scoped as a direct-writer census, not proof that pointer aliases can never exist.

The correct behavioral wording is therefore **five qualifying interactions within the active scene session**. The counter block contains no uniqueness list and no miss reset. It is cleared by successful unlock and by shared transition/reset paths. The movie visually establishes that its five qualifying interactions are spider butt-slams.

## Controls and executable guard

The existing scenario already supplies the decisive threshold control: at four events, the scene remains Training and latch remains zero; after the fifth, count resets, low flag becomes `0x02`, latch becomes 6, and scene becomes `0x10`. The same movie contains an interval in which the counter remains at four before the fifth accepted event.

`tools/scenarios/duckstation/bonus1_five_spider_stomps.yaml` now also contains a final phase for movie frame 3653 asserting scene 0 and flags `0x22`. The complete extended scenario was rerun against pristine hash-pinned media on 2026-08-02 and all nine assertions passed.

## Transient evidence

Root: `/tmp/abl-phase4-d10-20260802`

- `d10_capsule_asm.c`: SHA-256 `ca65031a709c70a247dd5b99cfdbbd964e608af3f94c1ed593c9983e89f5fc85`
- compiled capsule analyzer: SHA-256 `d076b93960f7a73b8be02aa2ca64575a463f78eb807ec14a6f7a0a64c1a47d4f`
- capsule output: SHA-256 `cab1c5fa93598705e2dcc956d95ef463fda0e8e489f3f85ad7746fbc9d3a1a8b`
- `d10_asm_slice.c`: SHA-256 `cc85d19b1f280941ff645bb33315639a62fad285f3ebdfe85c8fad40ffd75e9c`
- ASM slice output: SHA-256 `87061c57ccd85ec26338f5bef0125c335554481d3c9753e8809ad79e4f367b45`
- `d10_writer_census.c`: SHA-256 `5df2b31488e2a0bb9c190a01a6ac2bca2e6dd1280d25904a63cc6bf9e3326bda`
- writer-census output: SHA-256 `64cc12f1dbe343e042434ee5636ad5bde695ff64aeac8d6f6fb44f66c6471507`

Reproduction command for the retained capsule query:

```bash
gcc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_d10_capsule.c -o /tmp/phase4_d10_capsule -lzstd -lcrypto
/tmp/phase4_d10_capsule asm/hand_written/8004abf4_proximity_updater.s ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/bonus-objectives-v2-20260719/Bonus_Level_01
```

## Movie escalation rule

No Interpreter movie is required now. Request a new normal-speed Interpreter recording only if a future question needs exact per-instruction attribution beyond the retained capsule, or if D10 is expanded to cover bonus-stage internals or persistent save behavior. The existing CachedInterpreter movie must never be armed with CPU instrumentation.

## Follow-up executable closure (2026-08-02)

The extended scenario was run cleanly with no CPU instrumentation:

```bash
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/bonus1_five_spider_stomps.yaml --output-dir /tmp/abl-phase4-d10-20260802/scenario-final
```

Result: `PASSED`, nine assertions passed and zero failed. The final phase independently observed scene 0 and flags `0x22` at movie frame 3653. Playback was reproducible, movie v3 reported no phase delay owed and no truncation, pristine CUE/BIN hashes matched, and isolated PID 124261 was stopped successfully. Report SHA-256: `48bd6c15841532bd293796e49af1f754e41ad6f1a39258a3b0f6584c779fa97d`; Markdown report SHA-256: `7ff0345d454c9205459a613da6b9771a3ffa8a6ebb429ddba7a607ff7b0b8b7b`.

A compiled instruction-model guard was also added as `tools/phase4_d10_logic_guard.c`. It passed five cases: four does not unlock, five unlocks exactly, the earned guard is side-effect-free, the scene-`0x10` guard is side-effect-free, and shared transition reset clears the streak. Source SHA-256: `2079d0418927e8fb0b21a2273bc5184e4e2ae84e1d4bbb5bf37984187a7be727`; output SHA-256: `489d1c5d8f258fd65503aa2729fb52e2a356bfba4527268d4f050d3fdea81c3c`.

This removes the remaining executable-gate gap. An exhaustive pointer-alias absence proof would have minimal practical return and power-cycle persistence belongs to the save system, not D10's challenge/handoff scope. D10 is bounded-exhausted for Phase 4 and can be left without a new Interpreter movie.
