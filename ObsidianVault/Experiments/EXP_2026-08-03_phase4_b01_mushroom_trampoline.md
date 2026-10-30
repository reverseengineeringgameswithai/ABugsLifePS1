# EXP 2026-08-03: Phase 4 B01 mushroom trampoline

## Result

**B01 is a substantiated, bounded partial and is ready to move past.** The brown type-5 mushroom trampoline uses a fixed vertical-velocity assignment on every qualifying contact. Chaining does not multiply or preserve incoming speed. A separate five-distinct-mushroom bonus branch replaces the normal launch with a stronger completion launch.

No new DuckStation replay was required. The retained B01 trace capsule answered the runtime/frame-boundary questions, and pristine executable analysis answered the exact instruction and branch questions.

## Pinned evidence

- Movie: `movies/Phase4/B01_mushroom_chain.movie.json`
- Movie SHA-256: `c1542c669ff0ad7e5373de4f1570e953b9b6ddf61477c0ca62d6a74c690109be`
- State: `movies/Phase4/B01_mushroom_chain.movie.sav`
- State SHA-256: `65bacbc79563e36a4f754d39dbab90cf42e6e5563604efbedee516b9cd618f84`
- External capsule: `~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B01_mushroom_chain`
- Capsule manifest SHA-256: `9c9f304b52629cee0a4be7703fd9bde81aa79e9b642bfdd398dfda4100a40245`
- Capsule tree SHA-256: `928ee3b698d7582c69b3ca3317ebcdbd18469caf887d94bfe9806cb3df3ec541`
- Pristine executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- Handler ASM: `asm/hand_written/8005c58c_seed_plant_trampoline_handler.s`
- Handler ASM SHA-256: `ffe0c5327644cd6ff3bea1269c924d82786263aa38bc69c0b0c2c495cc7bf9ab`
- C static result: `analysis/phase4_b01_static.json`
- C capsule result: `analysis/phase4_b01_capsule.json`
- Closure record: `analysis/phase4_b01_bounded_exhaustion.json`

## Method

The investigation followed the Phase 4 capsule-first rule.

1. Validate and query the retained capsule in C before considering a live replay.
2. Reconstruct player, plant-slot, bonus-sequence, register, RAM, VRAM, SPU, and block-flow state at every retained frame boundary.
3. Analyze the hash-pinned pristine PS-X EXE and the existing ASM handler in C, checking exact opcode anchors rather than relying on a decompiler guess.
4. Separate direct observations, code-level inference, and causal conclusions.

Reproduction commands:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_b01_capsule.c -o /tmp/phase4_b01_capsule -lzstd -lcrypto
/tmp/phase4_b01_capsule ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v2/B01_mushroom_chain > analysis/phase4_b01_capsule.json
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_b01_static.c -o /tmp/phase4_b01_static -lcrypto
/tmp/phase4_b01_static SCUS_942.88 asm/hand_written/8005c58c_seed_plant_trampoline_handler.s > analysis/phase4_b01_static.json
```

## Capsule validity

The C parser reconstructed all 17 compressed chunks and all 978 records. It checked 2,934 retained RAM/VRAM/SPU domain hashes, with exact parsing and no failed hash. The capsule manifest reports complete, untruncated collection and full final control equality for frame/cycle, RAM, registers, VRAM, SPU, and machine state.

The capsule covers movie frames 0 through 977, emulator frames 23637 through 24614, and 240,308,096 executed instructions. This is frame-boundary evidence; the block-flow counts supply the connection to the exact handler path.

## Direct runtime observations

The capsule contains four qualifying contacts that execute the deep trampoline handler and expose the exact assigned velocity at the frame boundary:

| Movie frame | Mushroom slot | Incoming `vy` | Assigned `vy` | Mode after | Contact | Timer | Action |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 207 | 6 | 1792 | -3328 | 5 | 0 | 0 | 3 |
| 335 | 5 | 1536 | -3328 | 5 | 0 | 0 | 3 |
| 385 | 4 | 2816 | -3328 | 5 | 0 | 0 | 3 |
| 435 | 2 | 2816 | -3328 | 5 | 0 | 0 | 3 |

The different incoming velocities all converge on the same output. The retained block flow reaches `0x8005C5F4` through `0x8005C624` on these contacts. Ordinary handler entry appears on many other frames because the plant walker evaluates active mushroom slots; only four frames cross the eligibility branches and execute the bounce stores.

The sequence bytes show distinct mushroom identities entering the Bonus 2 bookkeeping. Frames 385 and 435 extend the active sequence from `[5,-1,-1,-1,-1]` to `[5,4,-1,-1,-1]` and then `[5,4,2,-1,-1]`. Physical bounce behavior is identical across those identities.

## Pristine ASM findings

The type-5 plant dispatch-table entry at `0x8001B854` points to `0x8005C58C`. The plant walker admits mature slots, and the handler then requires the current contact identity plus `extra_state & 2`.

The ordinary contact path is an assignment, not a coefficient:

- `0x8005C5F4`: materialize `-3328`.
- `0x8005C5FC`: store it to player vertical velocity `0x800A6530`.
- `0x8005C600` / `0x8005C608`: set player mode `5`.
- `0x8005C614`: clear contact at `0x800A6582`.
- `0x8005C61C`: clear timer at `0x800A6584`.
- `0x8005C60C` / `0x8005C624`: set action `3` at `0x800A6588`.

No incoming-velocity read participates in this assignment. The physical stores occur before the Bonus 2 sequence logic, so duplicate or reset bookkeeping cannot deny the bounce.

The five-byte sequence at `0x80082248` records distinct mushroom identities. A new identity appends at the first `-1`; the progress command is base `113` plus the filled count. Re-touching an identity already in the sequence resets the sequence to that identity in slot 0 and fills slots 1 through 4 with `-1`.

When all five entries are filled, a separate branch performs the completion behavior:

- transition latch `0x800823A0 = 6`
- fade timer `0x80082470 = 60`
- player vertical velocity `0x800A6530 = -16384`, overriding the normal `-3328`
- bonus flags `0x8009B889 |= 1`

The handler then enters the shared effect tail with identifier `15`.

## Observation, inference, and causal confirmation

**Observation:** four contacts on four plant slots replace different incoming velocities with `-3328` and apply the same player latches.

**Inference rejected:** mushroom chaining applies a multiplier, coefficient, or incoming-speed-dependent impulse.

**Causal confirmation:** the pristine handler materializes and stores the literal `-3328` on every qualifying contact. It contains no incoming-velocity read on that path. Duplicate bookkeeping follows the physical stores. The fifth-distinct case is explicitly a later `-16384` override.

## Scope boundary

The mature trampoline law, eligibility, latches, repeat behavior, cross-mushroom chain behavior, duplicate-sequence rule, and five-distinct completion branch are causally closed.

The handler invokes an animation routine and reaches effect identifier `15`, but mapping those to human-readable visual and SPU asset names would require asset-level attribution with little additional behavioral value. Non-mature carried or thrown seeds are excluded by the mature type-5 eligibility path, and the trampoline handler does not write plant-slot position. Those cases belong to seed growth/movement rather than the B01 contact law.

Reopen B01 only if a later row needs exact animation/audio asset identity or a reproducible mature type-5 contact contradicts the fixed assignment. An Interpreter movie is not currently required.

## Deep confirmation pass

A second C-only pass challenged the bounded closure rather than assuming it. The committed static and capsule analyzers were rebuilt with `-Wall -Wextra -Werror`. The capsule result reproduced byte-for-byte. The static result was semantically identical but originally differed in whitespace formatting; the stored JSON was normalized to the analyzer's exact emitted bytes.

`tools/phase4_b01_deep_static.c` then checked the full trampoline/reset instruction region and joined it to the retained capsule events. Its result is `analysis/phase4_b01_deep_confirmation.json`.

Additional causal bounds:

- There are zero conditional branches between accepted eligibility and the normal bounce/latch stores. Those stores therefore dominate the duplicate, append, incomplete, and completion sequence paths.
- The trampoline/reset region contains zero reads of player vertical velocity and exactly two writes: normal `-3328` and the later completion override `-16384`.
- The region contains zero writes to the plant eligibility halfword and zero writes to plant XYZ. The handler cannot make itself one-shot and cannot move the mushroom or a seed.
- The duplicate branch resolves to `0x8005C548`, the append branch to `0x8005C694`, and the not-yet-complete branch to `0x8005C6E8`.
- The shared effect tail spans `0x8005CCE0` through the return at `0x8005CD24` and contains zero player-velocity reads or writes. The `-16384` completion override therefore survives handler return.
- Each of the four retained contacts reaches `vy=-3072`, mode `6` exactly two movie frames after the `-3328`, mode `5` contact frame. All four consequently share the same observed `+128` velocity increment per frame after launch.
- Contact frames are 207, 335, 385, and 435, with intervals 128, 50, and 50 frames across four unique mushroom slots.

Reproduction command:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror tools/phase4_b01_deep_static.c -o /tmp/phase4_b01_deep_static -lcrypto
/tmp/phase4_b01_deep_static SCUS_942.88 analysis/phase4_b01_capsule.json > analysis/phase4_b01_deep_confirmation.json
```

This pass found no named missing runtime domain and does not change the disposition. B01 remains a substantiated, bounded partial that is ready to move past. A new Interpreter movie would duplicate the already validated contact evidence; it is required only if future work promotes exact visual/SPU asset identity into a closure requirement.

## Closure audit — 2026-08-04

Status: **Substantiated Partial / bounded-exhausted**.

The pristine C static guard, retained-capsule reducer, and deep control-flow guard were rerun for this audit. The fresh capsule reduction is byte-identical to `analysis/phase4_b01_capsule.json` (`f605862da1ec5a412d41f41b07cee12c544171f81293a534d76378983692549c`).

Closure metrics:

- Type-5 dispatch and 35 mechanism anchors verified against pristine `SCUS_942.88`.
- Four contacts across four mushroom slots assign exactly `-3328` despite distinct positive incoming velocities.
- Normal impulse has no incoming-velocity read or coefficient path.
- Duplicate contacts still bounce and reset the five-byte identity sequence.
- Five distinct identities select the separate `-16384` completion override, transition `6`, fade `60`, bonus bit `1`, and effect identifier `15`.
- No hidden eligibility write, plant-position mutation, or shared-tail velocity overwrite exists in the bounded handler region.
- Remaining animation/SPU asset naming is low-return attribution and does not block the Phase 4 behavioral row.

Machine-readable disposition: `analysis/phase4_b01_bounded_exhaustion.json` (`3e353a9536ac3b87c6ea0b2588717a65a1b08ca16b18ca9ed5a146a8d8d29db5`).

Additional Interpreter movie required: **no**.
