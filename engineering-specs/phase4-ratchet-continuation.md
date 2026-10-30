# Phase 4 continuation context — substantial offline queue

The substantial-queue policy was banked at
`82c12cb0f4e351c8f21bd626ad3b6b8295b069c7`; the launched seed must be that commit or a
clean descendant. Verify the current HEAD before acting. Do not redo work already
banked by the preceding capsule-first run.

The preceding executor ended autonomously open after four iterations. Its final tested
candidate before the ratchet-policy commit was `886edc69af60dca5558e63cf692deb738baee6be`:

- Phase 4 honestly remained open at 16/107 complete rows, 91 open rows, and 2/12
  complete families.
- Iteration 4 added C15 status-mask denial breadth across the LEVEL10 nearest-row and
  LEVEL04 fixed-tuple respawn writers, plus clean-checkout validation.
- Its decision is retained at
  `~/Downloads/ABL-phase4-ratchet-capsule-first/runs/phase4-20260718-183524-1358250/iteration-4-executor.decision.json`.
- The remaining C15 setter/clearer, whole-word semantics, general policy,
  indirect/additional writers, death-class/stage, persistence, and reset breadth remain
  open.
- Inherited Phase-3 current-toolchain mismatches are dependencies only when they are
  mechanically load-bearing for the selected Phase-4 work.

The ratchet policy is now intentionally stronger. Every iteration first regenerates
and validates the 107-row offline opportunity queue required by the contract, then
takes a subsystem-sized batch of highest-value offline-ready work. A one-command
capsule summary is not substantial progress. Analyze every relevant Phase-4 capsule
and movie for the chosen cluster, retain generated non-copyrighted evidence and guards,
and predeclare any live DuckStation escalation in the machine-readable escalation
ledger. Prefer new open Phase-4 rows over repeatedly deepening C15 or refreshing Phase
3 unless retained evidence proves a load-bearing dependency.

Use only hash-verified pristine retail media as behavioral authority. Keep external
movies and capsules outside Git, verify their central pins, follow the Obsidian
placement philosophy, and keep each conclusion weaker than or equal to its evidence.

## 2026-07-19 interruption recovery

The offline-first continuation completed and banked six coherent batches covering 26
rows before the controller disappeared during iteration 7. Those batches exhausted the
then-current `offline_ready` set without promoting frame correlations beyond their
evidence: the queue reported 16/107 complete, 91 open, 33 `offline_partial`, six
`live_required`, and 68 `no_capsule`. Do not redo those six batches. Iteration 7's
audited live-escalation plans for `A10_handstand` and `A11_seed_as_weapon` were recovered,
validated, and banked at commit `10933d9c0eb9c4dc66ca39952542fd1051429955`.

The interruption exposed two infrastructure defects. The ratchet controller was tied
to its GNOME Terminal process, so the launcher now runs the controller in a detached,
HUP-resistant session and uses the terminal only as a log viewer. The archived
DuckStation executable was also not a standalone runtime, and its long filename fooled
the old process-name ownership check. The repaired launcher verifies ownership using
`/proc/<pid>/exe` plus an open config-directory descriptor, rejects incomplete app
roots, and cleans up an owned process on API-readiness timeout.

For any justified live escalation, validate and launch only the complete preserved
runtime at
`~/Downloads/ABL-external-evidence/duckstation-runtimes/trace-capsule-v1-20260718/duckstation-qt`.
Its executable SHA-256 remains
`55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8`; its 207-file
`SHA256SUMS` manifest has SHA-256
`1c1c6923e455ba35b888016efe58186018c21013b035259438a8eb13f6ed1228`.
The bundle was live-proven against pristine `SCUS-94288`, API 2.1.0, schema
2026-07-18, 208 methods, and the expected running-executable hash. The legacy lone
executable under `duckstation-binaries/` is identification evidence only and must not
be launched. Preflight `/tmp`; use `/var/tmp` or run-owned scratch for large work.

First reconcile the central capsule generator/index so the complete runtime bundle and
manifest become machine-validated preservation inputs. Then regenerate the 107-row
queue and resume with the already-declared A10/A11 escalation plans unless the queue
mechanically establishes a higher-priority offline dependency. Live work remains the
last resort, not a substitute for the retained offline files.
