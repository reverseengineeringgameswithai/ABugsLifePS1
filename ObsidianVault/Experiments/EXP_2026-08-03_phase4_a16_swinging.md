---
kind: experiment
id: EXP_2026-08-03_phase4_a16_swinging
date: 2026-08-03
status: complete
confidence: high
source_state: original_game
row: A16_swinging
classification: substantiated_partial_bounded_exhausted
---

# Phase 4 A16 - vine/web swinging

## Verdict

Move on from A16. The row is not a claim of total shared mover/camera-engine closure, but it is a substantiated partial with bounded exhaustion. Trigger/control, sustained latch, directional steering, attachment record identity, pendulum writer chain, exact Cross-release law, and landing are all supported. The remaining transform algebra and camera decomposition are sharply bounded shared-engine residuals with low A16-specific return.

No new Interpreter movie was required. The retained swing capsule answered the frame-boundary questions offline; two isolated save-state API experiments answered only the named missing domains.

## Authority and fixtures

- Retail cue: `~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue`, SHA-256 `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`, serial `SCUS-94288`.
- Pristine executable: `REBUILD/files/SCUS_942.88`, SHA-256 `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- DuckStation: `~/duckstation/build/bin/duckstation-qt`, SHA-256 `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`, revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`.
- Attached anchor: `on_swing.sav`, SHA-256 `7c8570ff595909324aa4f2c0ba213b6f2c318b55c544d7aa581afdbeee3cc7c2`; state metadata independently reported the same cue and serial before load.
- Approach anchor: `in_front_of_swing.sav`, SHA-256 `50cf0d173e6e1f70ab1d41042d6f99c8fe4bacae1a0efbe7e4be437de1f53b1a`.

## Capsule-first result

The accepted v3 capsule at `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/swing` reports no error or truncation and exact control fingerprints. The C reducer reconstructed 1,050 frame records and checked 3,150 RAM/VRAM/SPU frame fingerprints with zero mismatch.

The main attached interval is movie frames `124..905`, 782 display-frame boundaries. Mode is `5` and grounded is `0` for the entire interval. The corresponding resident gameplay clusters execute on 391 30 Hz ticks. Entry is mode `1 -> 5`; release is immediately mode `5 -> 1`, followed later by ordinary airborne/landing transitions.

The capsule was originally captured with forced CachedInterpreter. It was used only as an accepted offline capsule. Its movie was not replayed or instrumented; doing so would violate the project's mode-stability rule.

Transient reducer evidence:

- `/tmp/phase4_a16_capsule.c` / checked-in `tools/phase4_a16_capsule.c`, source SHA-256 `0498926e7ec566455640dc14af5d2574cb86947761e311d062000ad43f79eb36`.
- Reducer binary SHA-256 `d9da2b27a6a4f752f869d44330af4f84e5a7cbacd5447835c1942af217d8e312`.
- Reducer output SHA-256 `b72edfaf5082d31e2d6c9a3f05f85f061d586b75dc5cf21bda444b3155997b70`.

## C-based pristine ASM investigation

`tools/phase4_a16_static.c` scans the immutable executable rather than an overlay or derivative. It localized 345 relevant player-block references, 159 stores, nine button predicates, and 45 calls in the candidate ranges. Source SHA-256 is `5ba464d45e00e4c484814e25469388b0c380e85cc03c09cec16d6bdbb98c234d`; transient binary/output hashes are `997d8451547ad4b805b31fbe7ce19e0f519fe3108f43288f593fbe1b230172b4` and `c6b09e33202ba076c0a73d14c4d402fd142ef897cbd55c1ff7b5bf8a4939d6b5`.

Static conclusions:

- `0x80041AC4` is the moving-surface resolver. It publishes the one-based surface handle at `player+0x8C` and writes projected X/Y/Z velocity at `player+0x2C/+0x30/+0x34`.
- The player path calls it at `0x80048914`; a nonzero result reaches `0x8004892C`, writes mode `5`, and clears the timer/bind fields.
- The attached path calls `FUNC_80047EBC` for the camera-relative target heading and turns current heading toward it before calling the surface resolver again.
- A new Cross edge is tested at `0x80048A14/0x80048A2C`. Release calls `FUNC_80041A74`, selects action `3`, writes mode `1`, doubles velocity X/Z, and subtracts `0x800` from velocity Y.
- `FUNC_80041A74` is exact matched C: for nonzero `player+0x8C`, it writes `-30` to `0x8009C874 + (handle-1)*0x344`, then clears the handle.

No Up predicate exists in the attached mode-5 branch. Up+Cross at the approach anchor is therefore a successful approach/contact control, not evidence for a separate Up-only attachment latch in the resident handler.

## Same-save input counterfactuals

Config `/tmp/duckstation-debugger-phase4-a16-20260803-02`, port `24423`, used the hash-pinned `on_swing.sav`. Every case loaded the same state, cleared controller state, and re-armed 15 individual execTrace watches after the load. No movie was involved, so instrumentation-forced Interpreter could not alter movie timing.

| Input, 30 display frames | Mode | Ground | Handle | Heading | Target | Position |
|---|---:|---:|---:|---:|---:|---|
| Idle | 5 | 0 | 2 | 2207 | 2209 | `(-153104,-116994,161067)` |
| Left | 5 | 0 | 2 | 1727 | 968 | `(-152578,-117011,161085)` |
| Right | 5 | 0 | 2 | 2687 | 3438 | `(-153667,-117019,161386)` |
| Up | 5 | 0 | 2 | 2207 | 2209 | `(-153104,-116994,161067)` |
| Down | 5 | 0 | 2 | 2207 | 161 | `(-152270,-118148,164987)` |

Up equals idle because this anchor already points forward. Left, Right, and Down change the target/trajectory without releasing the latch.

Cross produces the causal contrast. At two display frames: mode `1`, ground `0`, handle `0`, action `3`, velocity `(386,-2140,1516)`. At 60 display frames: mode `0`, grounded `0x0101`, handle `0`, action `22`.

Raw log SHA-256: `b4ec111c5e37aae2030e22f2453706e06c4d3ce94d082d680d1db4659542278b`. C reducer output SHA-256: `b703c574f8dc33967d2b052e1991b5c9cb5bbb0734f5e5d0e8acb0a2279db25b`.

## Attachment object and writer attribution

The second isolated run used config `/tmp/duckstation-debugger-phase4-a16-20260803-03`, port `24424`. Handle `2` selects visual-sprite/mover record index `1`: pool base `0x8009C870`, record start `0x8009CBB4`, stride `0x344`, detach field `0x8009CBB8`.

Because the API caps one access watch at 256 bytes, four watches covered `0x8009CBB8..0x8009CEFB`; a fifth watched player position/velocity. The anchor was reloaded and watches re-armed before advancing eight display frames. The retained log contains 7,508 events. A C byte-diff found 132 changing bytes in the record's transform/geometry body while its active detach field stayed `1`, player mode stayed `5`, and handle stayed `2`.

Instruction attribution places the record-writing bulk in `0x800409F8..0x80041A70`, with additional first-field/geometry writes in the `0x80042428` pool update. `0x80041AC4..0x800423F4` then reads that record and publishes player velocity; the access API reports the three player velocity stores at post-access PCs `0x800423CC/0x800423E0/0x800423F4`, matching static store instructions `0x800423C8/0x800423DC/0x800423F0`. Player XYZ is subsequently integrated at `0x80036D20/34/48`.

Raw object log SHA-256: `72121da440034f69262e32cb8d27cd600efe73dbaf8b2c892f8274520891459a`. Final C reducer source/binary/output hashes: `0a2053088cf9b399dc1fd579310545b0e87ae5fb734ddf9271f6dde0fbf10aca`, `1c82a9d2284f8a4e6d228d850b6f67adc68f1c8eed575740ac1d07a10d5f71ee`, `387db761af4ffe4641c476c0cd3fce457e13e9213aaf3158ee1aac71f0be3060`.

## Evidence classification

Observation: the capsule sustains mode `5`; same-save directions steer without clearing handle `2`; Cross clears it and lands; record 2 changes while attached.

Inference: the vine/web uses the generic visual-sprite/mover surface machinery rather than a vine-only player physics implementation.

Causal confirmation: static stores plus exact exec/access hits bind moving-record geometry to player velocity, bind the fresh Cross branch to the detach helper and impulse, and the same-save Cross/idle controls diverge only on that input.

## Bounded residual and closure decision

Two residuals remain:

- algebraic semantic naming of every per-vertex constant in the shared `0x800409F8` transform/normal routine;
- swing-specific decomposition of camera behavior beyond the confirmed shared camera-relative target-heading input.

Those are shared mover/camera-engine questions, not missing A16 trigger/state/lifecycle branches. Their cost is high and their A16-specific return is minimal. A16 is therefore properly recorded as a substantiated partial with bounded exhaustion, and the campaign should move to another unfinished row.

Canon disposition: [[SYS_vine_web_swinging]]. Structured evidence: `analysis/phase4_a16_swinging.json`.
