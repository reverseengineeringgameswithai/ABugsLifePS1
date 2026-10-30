# Work order: finish the behavior-library tuple sweep (small, mechanical)

**Context:** a detached sweep is replaying the 39 Interpreter behavior clips
(3 × 60-site slices each) through the jr-tuple harness. It survives the
session that launched it. This order finishes the banking once it completes.
Everything below is also derivable from
`ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md`
(sections dated 2026-08-08) and `analysis/phase4_f01_jr_tuple_capture.json`.

## Where things are

- Sweep log: `/tmp/claude-1000/-home-user-Downloads-ABL/b04205bb-cdc2-4619-a19e-2eb79964b196/scratchpad/behavior_sweep.log`
  — done when its tail reads `BEHAVIOR-SWEEP-DONE failed:<list|none>`.
- Session outputs: `jrbehav_*.json` in that same scratchpad directory.
- Harness driver + analyzer (reference copies, sha-pinned):
  `~/Downloads/ABL-external-evidence/phase4_jr_tuple_capture_2026-08-08/`
  (`jr_tuple_session_60hz.py`, `jr_tuple_analysis.py`).
- The frozen 179-site universe + protected set:
  `analysis/phase4_target_exclusion_freeze.json`.
- Emulator instance: config dir recorded in scratchpad file `jr_cfg_path`;
  stop it ONLY via
  `~/duckstation/scripts/debugger-client/launch_debugger_instance.sh stop
  --config-dir <that dir>`.

## Steps once the log shows DONE

1. Health-gate every `jrbehav_*.json`: `positive_control_events` non-zero,
   `execution_mode.effective == "Interpreter"`, final movie not playing.
   Name any failures; exclude them.
2. Merge tuples across `jrbehav_*` AND the corpus results already in
   `analysis/phase4_f01_jr_tuple_capture.json` (`results.tuples`), with the
   overlay-attribution guard: sites in LEVELxx_* images count only from
   sessions replaying that same level's movie; MEMORY sites count from all.
3. Report exactly three things against the frozen universe:
   protected-set intersections (must list all, expected 0), violations of
   the pilot's entry-scoped proved domains (expected: only the known
   0x80018CBC → 0x8001961C), and newly-observed previously-silent sites.
4. Check the operator-visible hypothesis banked in the experiment log
   (10–25 newly-lit sites from the behavior library; final silent pile
   ~80–100). State plainly whether it held.
5. Preserve all `jrbehav_*.json` + the merged analysis into the external
   store directory above; refresh its `SHA256SUMS`.
6. Extend `analysis/phase4_f01_jr_tuple_capture.json` with a
   `behavior_library_sweep` section (mirror the `full_corpus_sweep` shape:
   sessions, observed/silent, tuples delta, violations, replication n/a).
7. Append the dated results section to the experiment log; update the
   relevant memory surfaces if the executor maintains any; commit
   (intentional paths only; operator WIP untouched).
8. Stop the emulator instance (step 0 path). Confirm nothing else runs.

## Rules (binding, unchanged)

Evidence, not proof: no census/disposition/status movement; F01 stays
`partial`. Counts are lower bounds (drain re-arm windows); target SETS are
the stable observable. Exact sets both directions; silences enumerated,
never elided. No instrumented run beyond the sweep already in flight.
