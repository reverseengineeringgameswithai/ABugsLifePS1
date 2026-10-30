---
kind: experiment
id: Experiment_-_Mover_VM_cold_boot_opcode_trace
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - Mover VM cold boot opcode trace.md
aliases:
  - "Experiment - Mover VM cold boot opcode trace"
---

# Experiment — mover-VM cold-boot LEVEL01 opcode-stream fixture

> Migrated from `ObsidianVault/Experiments/Experiment - Mover VM cold boot opcode trace.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — mover-VM cold-boot LEVEL01 opcode-stream fixture

> Captures a **fresh** opcode stream of the mover/PATH bytecode VM [[FUNC_8004C13C]] from a known
> cold start (no save-state dependence). Closes the prior open item ("mid-level saves only catch the
> VM mid-wait"). **Runtime is LOCAL-ONLY** ([[DuckStation Fork Reproducibility]] / GAP-0001). Isolated
> instance only (`~/duckstation`, `/tmp/duckstation-debugger`, port 23460). No save-states/dumps written.

## Fixture (reproducible)
1. Launch the isolated instance on the pristine disc; replay the boot movie
   `flik_to_level01_stall.mv.movie.json` (`movie.load` + `movie.startPlayback{load_start_state:true}`,
   fast-forward), advance to ~frame 4260 — **player spawned, `scene_id=1` (LEVEL01)**.
2. `execTrace` the VM: entry `0x8004c13c` (a0=object), fetch `0x8004c1f4` (v0=stream opcode, s1=IP),
   dispatch `0x8004c220`, persist `0x8004c834`; advance ~60 gameplay frames.
3. Re-arm watches after any `loadState`; settle a few frames before `addWatch` (known gotcha).

Driver pattern: `tools/trace_initial_spawn.py` / `tools/trace_shell_warp.py` (movie boot); scratch in `/tmp`.

## Result (RUNTIME-LOCAL-ONLY)
- **2 active LEVEL01 movers** (object structs `0x800a0a64` type 14, `0x8009fd80` type 9); mover-updater
  `0x8004d224` runs each frame; **124 opcode fetches** captured over ~60 frames.
- **The program runs a repeating loop** (object `0x800a0a64`): IP `0x800775fe → 0x80077602 → 0x80077606
  → 0x800775fc → …`, i.e. opcodes **`[17 player-proximity] [9 set-target] [0 backward-jump −10 → loop]`**
  (table indices; the LEVEL01 movers poll player-proximity then advance their path target each cycle).
- **The IP is in the RESIDENT EXE** (`0x800775xx`, within 0x80010000–0x80082800), and the program/data
  block `object[+0x80]` is in resident heap (`0x80094xxx`) — **NOT** the LEVEL.DAT buffer
  (DATbase=`0x801607f8`). A static dump of `0x800775fc` is **byte-exact** with the runtime stream.
- ⇒ confirms: the bytecode **PROGRAM is resident** (program-pointer table `0x80077af8`, 17 entries →
  programs `0x8007745c..0x800776ec`); LEVEL.DAT supplies only the opcode-9 **path waypoints** + the
  object spawn/selection. (Corrects the earlier "opcode stream in LEVEL.DAT" reading.)

## Significance
- The VM is **live with a fresh, non-trivial opcode stream** at LEVEL01 (not just the prior mid-level
  wait-ticks) — the GAP-0033 interpreter is exercised end-to-end from cold boot.
- **A non-transition authored trigger is reproducible from this route**: opcode 17 (player-proximity)
  → opcode 9 (set move-target from the LEVEL.DAT path) drives the LEVEL01 path-movers each cycle.

## Confidence
- LEVEL01 reached + VM live + 124 fetches + repeating op17/op9/op0 loop — **CONFIRMED (runtime LOCAL-ONLY)**.
- IP/program resident (not LEVEL.DAT); static dump matches runtime — **CONFIRMED (runtime + static)**.

## Related
[[FUNC_8004C13C]] · [[Event and scripting system]] · [[Finding - LEVEL.DAT records are object paths]] · [[Experiment - Initial spawn write-watch]] · [[DuckStation Fork Reproducibility]] · `tools/trace_initial_spawn.py`
