---
title: Phase 4 E12 - audio SFX, XA music, and voice lifecycle
date: 2026-08-04
status: substantiated-partial-bounded-exhausted
phase4_row: E12_audio
media: pristine-retail
additional_interpreter_movie_required: false
---

# Phase 4 E12 - audio SFX, XA music, and voice lifecycle

## Disposition

E12 is **substantiated partial, bounded-exhausted, and ready to move on**. The high-value engine boundaries are closed: SFX dispatch and sample selection, the finite caller frontier, SPU voice ownership and release, music selection for all 15 levels, XA transport, pause/reset behavior, and the extracted XA/VAB inventories.

No new Interpreter movie is required. The remaining questions are semantic naming and dynamic-site values with minimal return unless a MOD depends on them.

Machine-readable evidence: [`analysis/phase4_e12_audio.json`](../../analysis/phase4_e12_audio.json)

Durable C guard: [`tools/phase4_e12_audio_static.c`](../../tools/phase4_e12_audio_static.c)

## Evidence discipline

### Capsule-first audit

No E12-specific retained trace capsule exists. The nearest valid capsules are the B06 and B08 SFX controls:

| Capsule | Manifest SHA-256 | Useful domain | Limit |
|---|---|---|---|
| `B08_bubble_repeated_hits` | `7d8c4b7b6d8ef288e9a0d5bc6e2651cb1d81f99b2552bad90b0ef897fd5434f3` | Complete frame-boundary RAM and SPU RAM fingerprints; adjacent SFX control | No per-voice SPU register snapshot |
| `b06_invincibility_hits` | `492aa2134e8d4d4bc8b348cd0c6d16f757d9ac4e5e3134945b2c688132f18c11` | Complete frame-boundary RAM and SPU RAM fingerprints; adjacent SFX control | No per-voice SPU register snapshot |

They are accepted only for their declared frame-boundary domains. They do not establish every-cycle voice state. Voice ownership and lifecycle instead come from the pristine MIPS implementation plus the existing isolated SPU-key-on controls.

### Static method

The investigation used C over the pristine executable, every extracted `LEVEL.BIN`/`LEVEL1.BIN`, all five XA files, and all VH headers. The durable form is:

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror \
  -o /tmp/phase4_e12_audio_static tools/phase4_e12_audio_static.c
/tmp/phase4_e12_audio_static
```

The guard checks selected pristine instructions, direct call counts, XA channel/EOF inventories, and all VAB headers. This is deliberately an offline guard; it does not mutate the game or require emulator timing.

## SFX dispatch and finite trigger frontier

`sfx_dispatch` at `0x80050994` accepts a signed ID:

- Negative IDs use the variant/round-robin pool at `0x80089850`.
- Positive IDs compute `index = id - 16`, `program = index >> 7`, and `tone = index & 0x7f`, then enter the voice manager at `0x80044d28`.
- In the GLOBAL bank for IDs 16 through 58, the selected VAG is `id - 15`.
- The existing live control for ID `0x35` selected tone 37 and GLOBAL VAG 38.
- The dispatcher return value is not proof of audible success. SPU key-on is the positive playback observation.

The direct static frontier is bounded:

| Interface | Resident calls | Overlay calls | Total | Constant IDs | Dynamic sites |
|---|---:|---:|---:|---:|---:|
| `sfx_dispatch` | 22 | 9 | 31 | 27 | 4 |
| `play_sound` | 92 | 17 | 109 | 105 | 4 |

The resident constant counts use the prior alias-aware census; the C guard independently pins the finite direct-call totals. The four dynamic sites in each interface are an explicit residual, not an unsearched part of the binary.

B08 supplies a causal control: its unmodified grant produced three nearby SPU key-ons, while NOPing the SFX call left one. The call therefore accounts for two real voices. B06 executes its SFX call once at the grant frame. A separate failed B06 audio probe is excluded rather than treated as negative evidence.

See also [[SYS_sfx_system]], [[FUNC_80050994_sfx_dispatch]], and [`analysis/sfx_id_vag_map.json`](../../analysis/sfx_id_vag_map.json).

## SPU voice ownership and lifecycle

The main SFX voice pool has eight entries at `0x80089860`, stride 8. Each entry stores the descriptor at `+0` and voice ID at `+4`; `-1` is free. The manager reuses a matching descriptor or allocates a free entry. When all eight are owned, it drops the request.

The lifecycle is also bounded in ASM:

- `0x80044c5c` clears the eight primary entries and eight companion timer/ownership rows based at `0x8009fb56`.
- That initializer registers `0x80043284` as the audio tick callback.
- The callback decrements active timers, calls key-off when a timer expires, clears ownership, reconciles the primary pool, and polls all 24 hardware voices with `SpuGetAllKeysStatus`.
- `0x80043500` is the hard audio reset: it keys off all 24 voices and clears both eight-entry structures.
- The positional path uses the listener transform at scratchpad `0x1f800374`; master volume is at `0x8008247e`.

This closes ownership, release, reuse, full-pool failure, timed cleanup, positional-volume input, and reset behavior without inventing audible semantics for numeric IDs.

## Music selection and XA transport

Gameplay reset reads the scene/music ID at `0x8008245c`, subtracts one, and calls looping music. The packed identifier is decoded as:

```text
file_index = packed_id >> 3
channel    = packed_id & 7
disc file = AUDIO(file_index + 1).XA
```

This produces the complete level map:

| Level | Packed ID | XA file | Channel |
|---:|---:|---|---:|
| 1 | `0x00` | `AUDIO1.XA` | 0 |
| 2 | `0x01` | `AUDIO1.XA` | 1 |
| 3 | `0x02` | `AUDIO1.XA` | 2 |
| 4 | `0x03` | `AUDIO1.XA` | 3 |
| 5 | `0x04` | `AUDIO1.XA` | 4 |
| 6 | `0x05` | `AUDIO1.XA` | 5 |
| 7 | `0x06` | `AUDIO1.XA` | 6 |
| 8 | `0x07` | `AUDIO1.XA` | 7 |
| 9 | `0x08` | `AUDIO2.XA` | 0 |
| 10 | `0x09` | `AUDIO2.XA` | 1 |
| 11 | `0x0a` | `AUDIO2.XA` | 2 |
| 12 | `0x0b` | `AUDIO2.XA` | 3 |
| 13 | `0x0c` | `AUDIO2.XA` | 4 |
| 14 | `0x0d` | `AUDIO2.XA` | 5 |
| 15 | `0x0e` | `AUDIO2.XA` | 6 |

When the special flag at `0x8008225c` is active, the selector instead passes packed ID `0x15` (decimal 21): `AUDIO3.XA`, channel 5.

`music_start` at `0x8004699c` sets the CD-XA file/channel filter, mode `0xe8`, location, `ReadS`, and demute. Looping is a software poll/restart path, not an assumption about XA EOF. `AUDIO4.XA` and `AUDIO5.XA` serve the EOF-driven voice/dialogue side of the system. See [[SYS_audio_music]], [[SYS_xa_voice_streaming]], and [[FUNC_8004699C_music_start]].

### XA sector census

Each of the five XA files contains one EOF marker per channel:

| File | Total sectors | Audio sectors, channels 0 through 7 |
|---|---:|---|
| `AUDIO1.XA` | 38,992 | 4,842; 4,375; 4,723; 4,442; 4,664; 4,520; 4,762; 4,595 |
| `AUDIO2.XA` | 41,872 | 4,476; 4,683; 4,520; 4,477; 5,202; 4,572; 4,518; 204 |
| `AUDIO3.XA` | 19,248 | 204; 202; 227; 2,353; 2,282; 2,374; 204; 204 |
| `AUDIO4.XA` | 3,600 | 284; 217; 194; 418; 191; 137; 312; 93 |
| `AUDIO5.XA` | 4,264 | 44; 66; 186; 134; 381; 501; 501; 501 |

## VAB, pause, and reset boundaries

The extracted sound-bank inventory is complete at this layer: 21 `pBAV` version 6 VH banks, comprising GLOBAL plus 20 level banks. GLOBAL has 3 programs, 43 tones, and 43 VAGs. The evidence artifact preserves the full scope and the C guard enforces the bank count and header format.

Existing A18 runtime evidence establishes the mixed pause behavior: XA/CD read position stops during pause, while pause-menu SFX remain available. Scene flow clears or replaces `0x8008245c`, so the music selection is runtime scene state rather than persistent save state. The linked PsyQ sequence engine is inactive for game audio: it has no game caller and had zero runtime hits while `SsUtKeyOn` remained active.

## Closure boundary

Closed for Phase 4:

- All 15 level music file/channel selections and the special override.
- XA transport and complete file/channel/EOF inventory.
- Resident and overlay SFX direct-call frontier.
- Positive-ID sample-selection law and a live mapped control.
- Eight-slot voice ownership, allocation, timed release, key-state reconciliation, and full reset.
- Pause transport boundary and scene-reset ownership.
- GLOBAL and level VAB header inventory.
- Source closure in `src_re` for SFX, voice manager, music start, and XA voice streaming.

Bounded low-return residuals:

- Exact runtime values at the four dynamic sites for each SFX interface.
- Audible names for every numeric SFX ID.
- Exact scene association for every level VAB variant beyond the complete bank inventory.
- Human-readable XA track titles.
- Every-cycle SPU envelope evolution beyond frame-boundary retained evidence.

Reopen E12 only if a MOD depends on a dynamic callsite, replaces audio assets, or changes allocation, pause, reset, or music selection. Exact dynamic-site values would justify a normal-speed Interpreter replay with physical execution breakpoints and register capture. They do not justify another movie for the current Phase 4 row.
