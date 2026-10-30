---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Training NPC progression.md
aliases:
  - "Training NPC progression"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Training NPC progression.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Training_NPC_progression.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Training NPC progression
type: system
updated: 2026-07-07
status: partial-live-confirmed
tags: [system, training, npc, objective, progression, pickup, reverse-engineering]
---

# Training NPC progression

Scope: follow-up to [[Plan - Training board dynamic sign trigger]]. This does not modify or rebuild ALLMODS. It explains how the stock Training instructor advances later objectives and how later objective items appear.

## Evidence

- Repo: `58c295976292c10a87efce514dd8c7d497dca412`, dirty before this work.
- DuckStation fork: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, dirty.
- DuckStation binary: `~/duckstation/build-release/bin/duckstation-qt`, SHA-256 `5538e0e0ca198b54f184ba5650e9a708ef4faf79b47180e49430e912fcc35448`.
- Disc booted read-only for the original progression pass: `build/ABL_ALLMODS.cue`; `ABL_ALLMODS.bin` SHA-256 `f64f26222ad7011198a31a74cae66c330b3b9e8448d80d95dbbe24020a106a5e`.
- Step-2 blackberry gate crash/fix pass: user DuckStation on port `2346`, then isolated verifiers on ports `23514` and `23515`. Current rebuilt `build/ABL_ALLMODS.bin` SHA-256 `3f001b4c385831183d211446caa2e2ba26553f84b55d27b40ea22249a400e688`.
- Movie: `TRAINING_NPC_STAGES.movie.json`, v3 from-boot, 8039 frames, SHA-256 `2b05a9758975a3dd983503a216e347b49a1b344ea9435954d2f325a29fe28f0d`.
- Isolated debugger: config `/tmp/duckstation-debugger-training-npc`, port `23617`, token `training-npc`.

## State Machine

`LEVEL07/LEVEL1.BIN` loads at `0x800B39A0`. The tutorial driver is `0x800B3F58`.

- Current step: `0x800B4A3C`.
- Per-step state: `0x800B4A58 + step*4`.
- Shared wait timer: `0x800B4A50`.
- Audio table: halfwords `0x800B4A14 = 0x18..0x25`.
- Common tail: `0x800B477C`.

The common tail stores the current handler state, and when a handler sets advance flag `s1=1` it calls `0x80045A60`, writes `0x800B4A50 = 30`, clears `0x800A65E0`, writes a timestamp-like value to `0x800A65F0`, and increments `0x800B4A3C`.

Jump table:

| Step | Handler |
|---:|---|
| 0 | `0x800B3FD4` |
| 1 | `0x800B402C` |
| 2 | `0x800B40C4` |
| 3 | `0x800B4128` |
| 4 | `0x800B4200` |
| 5 | `0x800B4368` |
| 6 | `0x800B4264` |
| 7 | `0x800B42C4` |
| 8 | `0x800B4318` |
| 9 | `0x800B43FC` |
| 10 | `0x800B4470` |
| 11 | `0x800B4570` |
| 12 | `0x800B45E0` |
| 13 | `0x800B4670` |

## Item Reveal

Training init `0x800B3C94` scans the type-0x3f pickup record at `[0x80096E9C]`.

- Kind `0x2B`: first two pointers cached at `0x800B4A34` and `0x800B4A38`.
- Kind `0x2C`: cached at `0x800B4A40..0x800B4A4C`.
- Every cached entry is hidden by adding `+8000` to `entry.y` and `entry+0x0E`.

Later handlers reveal those entries by subtracting `8000`. This is the important part: the tutorial overlay does not spawn a separate object itself. It moves already-authored type-0x3f entries back to normal coordinates, then the normal pickup pass `FUNC_80053814` constructs and collects them.

In the ALLMODS run at movie frame 3900, cached entries were:

| Pointer | Kind | Status | Hidden y | Hidden rest |
|---|---:|---:|---:|---:|
| `0x8011F3F0` | `0x2B` | 1 | 7672 | 8472 |
| `0x8011F400` | `0x2B` | 1 | 7461 | 8261 |
| `0x8011F410` | `0x2C` | 1 | 6242 | 7042 |
| `0x8011F420` | `0x2C` | 1 | 7519 | 8319 |
| `0x8011F430` | `0x2C` | 0 | 6098 | 6898 |
| `0x8011F440` | `0x2C` | 1 | 7414 | 8214 |

Revealed y/rest are each `hidden - 8000`. Completion for the single revealed entries is detected by `entry.y == 0x80000000`, the normal consumed sentinel.

## Step Notes

- Step 0 is the already-solved ALLMODS patch: stock audio play is preserved, the advance half raises sign 0 with blank count and waits on the voice-playing flag.
- Step 1 waits on `0x800A6580 == 1` with previous value `0` or `3`, increments per-step state, and updates sign 1 count until state reaches 7.
- Step 2 waits on `0x800A6584 == 9`, increments state, updates sign 2 count until state reaches 4.
- Step 6 reveals `0x800B4A34` by subtracting 8000, then advances when that entry is consumed.
- Step 9 reveals `0x800B4A38` by subtracting 8000, then advances when that entry is consumed.
- Step 13 reveals the cached kind `0x2C` batch at `0x800B4A40..0x800B4A4C`; it then remains in the final/tutorial-loop state, with the common audio tail alternating the final two voice ids via `0x800B4A54`.

More exact semantic names for steps 3-5, 7-8, and 10-12 still need correlation with gameplay labels, but their control-flow addresses and raw condition globals are now mapped in `src_re/training_tutorial_progression.c`.

## 2026-07-07 ALLMODS Step-2 Blackberry Gate

Custom behavior requested for step 2: append a hidden kind-`0x25` Blackberry/Fastberry pickup, reveal it when step 2 starts, and advance to step 3 only after both conditions are true:

- the step-2 voice line has fully ended (`[gp+0x6e0] & 1 == 0`);
- Flik has collected the blackberry (`0x800A6597 == 5`).

The first implementation put the gate cave at `0x800B4A30`, because the static `LEVEL07/LEVEL1.BIN` tail looked zero. That was wrong. Live crash evidence from the user's current DuckStation:

- mounted image: `~/Downloads/ABL/build/ABL_ALLMODS.cue`;
- frame `7784`, paused crash state;
- `PC = 0x000000A0`, `COP0_EPC = 0x800B4A34`, `SP = 0x000085C0`;
- live memory at `0x800B4A30` was runtime data, not our cave bytes.

This aligns with the state-machine RE above: `0x800B4A30` is real Training overlay state (`G_PREV_A6580`), followed by cached kind pointers and tutorial state/timer words. It is not safe code space even if the raw overlay file has zeros there.

Fixed allocation:

- main gate: `SCUS_942.88` resident EXE `0x8007F0D8..0x8007F118`;
- reveal shim: `SCUS_942.88` resident EXE `0x8007F930..0x8007F954`;
- step-2 wait block in `LEVEL07/LEVEL1.BIN` now only raises sign 2 blank and jumps to `0x8007F0D8`.

Static verification on the rebuilt disc:

- `LEVEL1.BIN` step-2 jump word is `0x0801FC36` (`j 0x8007F0D8`);
- no jump to `0x800B4A30` remains;
- `0x8007F130..0x8007F16F` remains zero in the embedded EXE;
- old input/global danger ranges `0x80081858` and `0x80081CF0` are not used by this gate.

Runtime verification:

- isolated DuckStation booted rebuilt `build/ABL_ALLMODS.cue`;
- advanced past the original crash point to frame `9003`, then to frame `12000`, without `PC=0x000000A0`;
- live reads showed cave bytes still intact at `0x8007F0D8` and `0x8007F930`;
- controller polling still changed the game-side pad word at `0x80082412` after the level settled.

## 2026-07-07 Green Token Right Build

User request: move the first green tutorial token noticeably to the right and build a new image, not `ABL_ALLMODS`.

- Source entry: `LEVEL07/LEVEL1.DAT` type-0x3f entry 56, kind `0x2B`.
- Coordinate change: file x `-1197 -> -597` (`+600`; runtime-scaled delta `+19200`).
- Superseded bad build: `build/ABL_GREEN_TOKEN_RIGHT_BROKEN_MANIFEST_REBUILD.bin` / `.cue`. This reran the full manifest through WIP Training word-pickup tooling and the user observed a black screen when loading Training.
- Fixed output image: `build/ABL_GREEN_TOKEN_RIGHT.bin` / `build/ABL_GREEN_TOKEN_RIGHT.cue`; alias copy also exists as `build/ABL_GREEN_TOKEN_RIGHT_FIXED.bin` / `.cue`.
- Fixed method: copied the known-working `build/ABL_ALLMODS.bin` and patched only the embedded `LEVEL07/LEVEL1.DAT` x-coordinate bytes. `ABL_ALLMODS` itself was not modified.
- Fixed verification: the new BIN differs from the source image by exactly two bytes at raw disc offsets `0x01BFD540` and `0x01BFD541`; direct embedded-DAT readback showed type-0x3f count `66`, entry 56 kind `0x2B`, x/y/z `-597/-50/148`.
- DuckStation verification: isolated config `/tmp/duckstation-debugger-green-token-fixed`, port `23623`, token `green-token-fixed`; movie `TRAINING_NPC_STAGES.movie.json` reached Training scene id `0x11` at frame 4500 with a normal nonblack frame, and live cached first kind-`0x2B` pointer `0x8011F54C` had x `-597`.
- Fixed output hashes: BIN SHA-256 `f2786fba653ed9b38017ef0472a951d55978f9f68a9c076fdc11d4e1682900ee`; main CUE SHA-256 `2998e665c9ce8b398c894b77ae95258f9c2da8aec08c891491affc6f4bb086d9`; alias CUE SHA-256 `9d7993cb3a268ce61e04024d46186d116e9bc05004f8f9f6531bed7d2b06c385`.
- Crash-prevention note: [[Training green token coord move crash note]].

## Related

[[Training green token coord move crash note]] · [[Training board sign images]] · [[Plan - Training board dynamic sign trigger]] · [[Experiment - Training in-world TRAINING pickup word]] · `src_re/training_tutorial_progression.c` · `src_re/training_board_sign.c`
