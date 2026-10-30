---
type: experiment
status: complete
date: 2026-08-10
system: scene transition lifecycle / F01 objective completion
phase: 4
dimension: original_oracle
artifacts:
  - analysis/phase4_f01_original_oracle.json
  - tools/phase4_f01_original_oracle.py
  - tools/phase4_f01_finalizer_entry_probe.c
fixtures:
  - movies/Phase4/Interpreter/Any% Runs/LEVEL01_AntHill_FromBoot.movie.json
---

# F01 `original_oracle`: the four finalizer leaves, observed on a natural cold-boot completion

## Verdict

All four declared leaves observed while the Anthill objective completes **naturally**
from a pristine cold boot, with **nothing injected**. 6/6 assertions pass.

**`original_oracle` remains `partial`.** This is evidence, not promotion — only a
fresh detached verifier may bank a dimension change, and `analysis/mechanics_baseline.yaml`
was not touched.

## Why this run was needed

`analysis/phase4_f01_finalizer_witness.json` is a causal witness for **one** branch.
Its own recorded defects: the anchor is a validated save state rather than a pristine
cold boot, the deciding value `2` is **injected** by a write to `0x800823A0`, and it
covers one branch across four declared leaves.

## The branch, from the image bytes

```
0x8004FF14  jal 0x80039BD8        consumer proceeded past its guard      (leaf 1)
0x8004FF28  lh  v1,0x23a0(v1)     the decision re-read                   (leaves 3,4)
0x8004FF30  beq v1,2 -> 0x8004FF50    request == 2 SKIPS the finalizer
0x8004FF38  lw  v0,0x4c4(gp)      [0x8008225C], the other skip condition
0x8004FF40  bnez v0 -> 0x8004FF50     nonzero SKIPS the finalizer
0x8004FF48  jal 0x80045A60        THE FINALIZER                          (leaf 2)
```

> The finalizer runs **iff** `request != 2 && [0x8008225C] == 0`.

⚡ **The natural run exercises the opposite branch from the injected witness.**
LEVEL01 exits on region code **2**, and that dispatch arm (`0x800496C4`) writes
request **1** — not 2. So the two arms together bracket the condition, with one side
produced by gameplay rather than by a poke.

## Fixture and method

| | |
|---|---|
| movie | `Any% Runs/LEVEL01_AntHill_FromBoot.movie.json`, **7,385 frames** |
| anchor | genuine cold boot — `from_boot: true`, no start state, `path: ""` |
| format | v4, `armed_while_paused: true`, `phase_delay_owed: true`, **`phase_correction_consumed_at: 2`** |
| launcher | `tools/launch_repro_playback.sh --execution-mode Interpreter` (verified `[CPU] ExecutionMode=Interpreter` present) |
| media | pristine `SCUS-94288`, verified before use |
| playback | `movie.resumeUntilMovieFrame` — the 60 Hz resume path, **not** frame stepping, because this recording carries the arm-phase correction |
| injection | **none** |

## Result

Scene timeline `624 → 0 → 1 → 0`: Anthill entered ~frame 4000, exited by 6000.

| leaf | value |
|---|---:|
| `consumer_proceeded_hits` | 1 |
| `decision_reread_hits` | 1 (frame 5895) |
| `request_at_decision` | **1** — produced by gameplay |
| `gp4c4_at_decision` | 0 |
| finalizer hits attributable to the decision | 1 |
| decision → finalizer | **28 cycles** (same basic block) |

## ⚠️⚠️ The trap: a PC watch is an ADDRESS watch, not a code watch

The first pass reported `finalizer_hits: 327` against `decision_reread_hits: 1`.
That is impossible on straight-line code, and chasing the impossibility is the whole
story of this experiment.

**On a from-boot movie the game EXE is not resident for the first ~1,000 frames.**

| movie frame | `[0x8004FF48]` | |
|---:|---|---|
| 300 | `0x00000000` | EXE not loaded |
| 700 | `0x00000000` | EXE not loaded |
| 1200 | `0x0C011698` | `jal 0x80045A60` |
| 5000 | `0x0C011698` | loaded |

The watch had been faithfully logging 326 executions of *whatever else occupied that
address during boot*. `capture_memory` is not at fault — its values matched
`debugger.readMemory` exactly at the same frames.

⚡ **My assertion could not have failed.** `finalizer_hits >= 1` is satisfied by the
326 phantom hits alone; it would have passed even if the real completion had
**skipped** the finalizer. Precisely the failure class already banked as
the `knockdown-not-a-slot-writer` auto-memory — committed inside a tool written to be careful.

**Fixed at source, not by filtering:** every watch now also captures the instruction
word **at its own PC**, and an event counts only when that word equals the pristine
image word. Re-run: `finalizer_hits_whole_run` **327 → 1**, with
`preload_noise_rejected: {finalizer_hits: 326}`.

⚠️ **This affects every from-boot replay in the corpus that arms PC watches.** Any
such count taken without an EXE-loaded guard may include pre-load executions.
State-anchored movies are immune, and so are pure memory write-watches.

## ⚡ A fabricated finding, caught before it was banked

Before checking whether the code was even loaded, this page was going to record the
326 hits as *"an observed indirect entry into the middle of a basic block, relevant
to `complete_frontier`"*. It is a plausible story — this binary has 179 unproved
indirect sites and switch-case fall-through is an ordinary compiler shape. **An
exotic finding that fits the project's known open problems is exactly the kind that
gets banked without enough scrutiny.**

What refuted it was a tool, not more reasoning:
`tools/phase4_f01_finalizer_entry_probe.c` (compiled C, self-tested on 5 decode
cases) scanned **22/22 unique images / 143,060 words** and found **zero** direct branch or jump
targets landing in `[0x8004FF14, 0x8004FF50)`, and **zero** matching entries in the
already-decoded `analysis/phase3_jr_tables.json`. With no direct entry and no decoded
indirect entry, "the code wasn't there yet" was what remained — and one memory read
settled it.

**2026-08-10 hard-truth correction:** the earlier `260,307`-word / `2,340`-indirect
totals double-counted SCUS and omitted LEVEL00's one-word sentinel. Re-running the
compiled-C probe over the deduplicated 22-image universe gives **143,060 words** and
**1,246 `jr`/`jalr` occurrences**, still with zero direct entries. The conclusion is
unchanged; the old corpus arithmetic was false.

> **Chase the mundane explanation before the exotic one, with a tool that can refute
> the exotic one.**

## Method notes carried from operator feedback

- **Compiled C owns instruction decoding.** The entry probe is C; earlier in the same
  session MIPS words were being decoded in Python, which is the wrong side of the line.
- **Arm everything in ONE replay.** This movie was replayed four times for different
  arming before the final single armed run; re-arming means re-replaying, which
  invites drift. The alternative is parallel instances on the same movie, consolidated
  afterwards.

Related: [[EXP_2026-08-05_phase4_f01_objective_lifecycle]] ·
[[Level_Goal_and_Exit_Trigger_Matrix]] · [[DuckStation_API_Index]]
