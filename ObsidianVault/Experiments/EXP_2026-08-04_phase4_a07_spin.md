---
kind: experiment
id: EXP_2026-08-04_phase4_a07_spin
created: 2026-08-04
status: completed
phase4_row: A07_spin
disposition: substantiated_partial_bounded_exhausted
authority: pristine_original_game
---

# Phase 4 A07 - directional spin recognizer

## Decision

The operator's Interpreter recording resolves the external lead. A07 is now a
**substantiated Partial and bounded-exhausted enough to move on**. The retail
game has a real table-driven directional recognizer inside `FUNC_80048138`; the
old 193-trial synthetic battery did not reproduce its accepted timing and was
correctly only a bounded negative.

The exact trigger is two clockwise cardinal rotations:

`Up, Right, Down, Left, Up, Right, Down, Left`.

The action requests animation 13 without creating a new player mode. It also
clears carry/seed/attachment state and drives a shared periodic SFX-64 timer.
The same animation is used by the propeller path, so animation 13 by itself is
not proof that the directional recognizer ran.

No additional Interpreter movie is required for A07. A direct carried-seed
presentation control or enemy-contact control may be recorded later for those
cross-row questions, but neither changes the recognizer, entry, timeout, latch,
or reset contract established here.

## Evidence identity

- Disc: `~/Downloads/ABL/Disney-Pixar A Bug's Life (v1.0).cue`
- Cue SHA-256:
  `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`
- Serial/title: `SCUS-94288`, `Disney-Pixar A Bug's Life`
- Pristine EXE: `REBUILD/files/SCUS_942.88`, SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- Shipping player ASM SHA-256:
  `f50038e52d548c44f59f8ac09ca17559e441be749d06dcf5b758cf6f13f38bdc`
- Movie: `movies/Phase4/Interpreter/A07_spin.movie.json`, SHA-256
  `af42baefa4120ab7585c9bac6b2ce2e757a5de683a475abfcec414592bebda7d`
- State: `movies/Phase4/Interpreter/A07_spin.movie.sav`, SHA-256
  `9c57d073a7ada8db8b069b80b3b6463b48d266662a76f4e26978b129f1853d5d`
- Movie: format v4, 996 frames, state-anchored at emulator frame 21620,
  `armed_while_paused=false`, `phase_delay_owed=false`, `reproducible=true`.
- DuckStation binary SHA-256:
  `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899`
- Fork source: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, dirty-state hash
  `de91329f6d9dba296f4a1746ec1ece5adb86e67c`, API 2.1.0 / schema
  2026-07-18 / 208 methods.
- Isolated run: `/tmp/duckstation-a07-spin-20260804-01`, port 24437,
  owned PID 2213296 stopped through that config's launcher.

No disc, executable, guest RAM, save, movie, or asset was mutated. This is a
narrow original-game state-anchored experiment, not a disc/code/asset change,
so cold-boot reproduction is not required.

## Capsule-first decision and live method

The central Phase 4 capsule index and declared external-evidence root contained
no A07/spin capsule. The missing domain was the positive trigger plus exact
instruction/write timing, so a fresh live replay was justified.

The pristine disc was mounted and identity-checked before loading the movie.
Playback used `debugger.resume` at normal speed; fast-forward and turbo both
reported false. After the movie loaded its start state, a non-halting write
watch was re-armed over `0x800A6500..0x800A65FF` at playback index zero. The
run retained 44,031 writes without truncation. It continued for a short neutral
tail while the client observed playback completion; all cited trigger and
release frames lie inside the 996 recorded frames.

The run was not predeclared in `analysis/phase4_live_escalations.json`. That is
an explicit strict-closure debt, not a reason to discard the pristine
observation. A07 therefore remains Partial rather than being promoted to Full.

## Observation

The movie's digital input changes start at relative frame 33. Its human-timed
sequence includes diagonals and varied holds; no action button is pressed.

The positive writer block runs in two windows:

| Window | Relative frames | Player ticks | Why it ends |
|---|---:|---:|---|
| First | 133..145 | 7 | next accepted Up changes the ring |
| Second | 209..247 | 20 | inactivity reaches the exact timeout |

Each of these five PCs executed 27 times, once per positive tick:

| PC | Write |
|---|---|
| `0x8004838C` | clear `player+0x7A` |
| `0x80048394` | clear carried actor offset `player+0x5C` |
| `0x8004839C` | clear seed-action byte `player+0xA3` |
| `0x800483A4` | request animation 13 at `player+0x88` |
| `0x800483AC` | clear queued action `player+0x9E` |

The first branch store is emulator frame 21753 / relative frame 133 / cycle
12,316,106,404. The actor animation commit at `0x800569AC` changes current
clip `player+0x8A` to 13 later that frame at cycle 12,316,181,992. No distinct
spin value appears in `player+0x80`.

Input becomes neutral at relative frame 848. The two motion fields used by the
clip-13 retention block decay:

`144/328 -> 16/284 -> 0/221 -> 0/157 -> 0/94 -> 0/31 -> 0/0`.

Idle 22 is first requested at relative 851 by `0x80056654`; current clip
commits `13 -> 22` at relative 857 / cycle 12,726,122,510. Release is therefore
motion-gated, not an immediate input-release cancel.

## Shipping ASM mechanism

`0x800481C4..0x8004829C` maintains an eight-halfword circular history at
`0x800894D0`. Index `0x800823B0` and inactivity counter `0x8008229A` are reset
with the ring during player spawn at `0x80046B34..0x80046B60`.

Only a changed full pad word equal to one exact cardinal value is admitted:

- Up `0x10`
- Right `0x20`
- Down `0x40`
- Left `0x80`

Diagonals pass the preliminary `&0xF0` test but fail exact equality and do not
enter the ring. The same is true if an action button is held with a cardinal.
Non-admitted ticks increment the counter; exact count 20 appends zero and
invalidates a stale history.

`0x800482A0..0x80048308` compares the circular history, oldest first, to the
sole directly referenced table at `0x80077304`:

`10 20 40 80 10 20 40 80`.

All eight entries must match. `player+0x90 & 0x80` then denies entry; this is
the same busy/suppression bit already owned by the grain-harvester work.

On admission, changing into clip 13 arms `0x80082294=120`. A positive carried
offset resolves against actor base `0x8009FD80`; the branch zeros actor
velocities `+0x1C/+0x20/+0x24`, clears actor flag `0x40`, then clears the player
carry fields. The sole call, byte-matched leaf `0x80041A74`, clears a separate
indexed attachment at `player+0x8C` after writing `-30` to its stride-836
record. The entry block has no attack, damage, unlock, save, or persistent
cheat write.

`actor_skinned_update` preserves requested clip 13 while current clip is 13 and
`player+0x38 >= 64 || abs(player+0x3C) >= 64`. Its common animation-13 tail
decrements the SFX timer. At zero it calls `0x80050C40` with ID 64 and re-arms
to `random_byte+60`. The propeller path shares clip 13 and this audio tail.

## C reconstruction and guard

`tools/phase4_a07_static.c` reads the immutable EXE, checks 29 instruction
anchors, proves the table/ring pointer pairs unique, decodes the retail table,
parses the movie's digital inputs, and simulates the 30 Hz recognizer. It must
produce exactly the two runtime windows 133..145 and 209..247.

```bash
cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_a07_static.c \
  -o /tmp/phase4_a07_static
/tmp/phase4_a07_static REBUILD/files/SCUS_942.88 \
  movies/Phase4/Interpreter/A07_spin.movie.json
```

Documentation-grade semantic C is in
`src_re/spin_directional_80048138.c`. It is explicitly not matching source.

Machine-readable evidence: `analysis/phase4_a07_spin.json`.

## Controls, confidence, and residuals

**Observation:** the prefix through frame 132 has no positive branch writes;
completion at 133 starts all five writes and commits clip 13 in the same frame.
The second natural match lasts the exact 20-tick timeout. Neutral input plus
motion decay restores idle.

**Inference:** the visible spin is animation clip 13 selected by the ring match.

**Causal confirmation:** pristine ASM supplies the only comparator, exact table,
gates, side effects, reset, timeout, retention, and audio path; the complete
untruncated write log hits every entry store at the predicted frames; the C
simulation reproduces both windows from the recorded inputs.

Bounded residuals:

- the no-seed movie does not show the visible placement/presentation of the
  instruction-exact carried-actor cleanup;
- no enemy-contact control tests a model-specific incidental contact effect,
  although the entry block creates no attack state or damage call;
- animation-asset frame semantics and exact SFX-64 presentation remain owned by
  the shared animation/audio campaigns;
- the missing pre-run escalation ledger entry prevents strict Full status.

These do not make another A07 movie necessary and do not invalidate the input,
state, lifecycle, or future-MOD contract. Reopen only for one of those named
cross-system questions.

## Transient evidence hashes

- `/tmp/a07_access_summary.json`:
  `da6d95a209e5846e14f861262fbc814c749b8bfba26b5f00955a4f7b5d2aee66`
- `/tmp/a07_access_page0.json`:
  `786dd95b346158d4008dd9102c5e89e5c32a568a64358649cf295f9ff1f26897`
- `/tmp/a07_access_page10000.json`:
  `047d51b0bb5cd55ca7a9c14a705d5b1bf757e689204805106bed156c8a760524`
- `/tmp/a07_access_page20000.json`:
  `cc13025fbf6000af47494817b4b8eb2977e52e065ea3a6b155bc7abfbb0d64fc`
- `/tmp/a07_access_page30000.json`:
  `4a1471b9375ef4376e0c5a1070e948d734727bd182a9e0557ad2bf74a45dd205`
- `/tmp/a07_access_page40000.json`:
  `3bf87ce8cd4968b88db96f427f4e6eefc517a5ff6fd13d8bca7a41bfdf611453`
- `/tmp/a07_access_reduced.txt`:
  `a246b4a49188b924bc68732c5645b17e51c62056e8ae2441d3114d95f7d3666b`
- `/tmp/a07_capabilities.json`:
  `797bde1b70c6ad4124d372829df784fef186ffbaf9ee60b92ea1d7f24036433f`

## Related

[[SYS_a07_spin_external_lead]] · [[FUNC_80048138_player_vertical_update]] ·
[[FUNC_800563D4_actor_skinned_update]] · [[FUNC_80041A74]] ·
[[EXP_2026-07-13_a07_spin_move_disproof]] ·
[[EXP_2026-07-31_interpreter_movies_survive_instrumentation]]
