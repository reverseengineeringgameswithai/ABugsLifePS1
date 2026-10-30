---
type: experiment
status: complete
date: 2026-07-19
system: Phase 4 offline trace analysis
phase: 4
---

# Phase 4 offline handstand / seed-weapon batch

This iteration consumed the complete coherent `A11_seed_as_weapon` /
`A10_handstand` cluster. Both rows remain open. They began with no retained
capsule, so the predeclared missing-domain escalations
`P4-ITER69-A11-MISSING-CAPSULE` and `P4-ITER69-A10-MISSING-CAPSULE` collected
the two already-existing operator movies. The resulting frame evidence was
then analyzed offline under the exact archived reader.

## Selection and pre-run evidence

- The acceptance-contract sidecar matched SHA-256
  `715f3e51648e781eccea4ff12940ac83363e0a0fa8b73097b38a398bd1e1cad2`;
  persistent initial context was re-read rather than trusted as proof.
- Recursive inventory found 110 files under `movies/Phase4` and 147 in the
  broader movie tree. No filename or JSON serial was treated as media proof.
- Before collection, the generated 107-row queue was 16 complete / 91 open,
  with zero `offline_ready`, 33 `offline_partial`, six `live_required`, and 68
  `no_capsule`. A11/A10 were the highest-ranked live-required coherent pair at
  ranks 31/32. The exact pre-run queue and ledger hashes are `cbef7f…` and
  `9bc93d…`; their complete hashes are retained in the machine source/ledger.
- `/tmp` had 13 GiB free but the user was already at its 50,534 MiB quota.
  This was an infrastructure condition, not a fixture blocker, so both fresh
  profiles were placed under `/var/tmp`.

## Isolated collection and preservation

Only the complete preserved runtime was launched:

`~/Downloads/ABL-external-evidence/duckstation-runtimes/trace-capsule-v1-20260718/duckstation-qt`

Its `SHA256SUMS` validated all 207 files. The executable SHA-256 is
`55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8`.
The separate descriptive executable snapshot was identity evidence only and
was not launched.

Two fresh profiles used ports 20701/20702. Each verified mounted pristine
`SCUS-94288`, CUE `463102…`, BIN `2aeafa…`, and inspected the exact paired
state before loading it. Only owned PIDs 284041/284207 were stopped. The two
external collections are:

- `a10-a11-v1-20260719`: collection `8f7cae…`, batch `ea2c1b…`;
- `a10-a11-v2-20260719`: collection `9cf537…`, batch `097bf3…`.

Both report empty failures, complete/nontruncated controls and exact movie,
state, media, source and running-binary pins. A11 retains 462 records (461
movie frames); A10 retains 1,359 (1,358 movie frames). Independent frame-chunk
sets are byte-identical for each movie. The central preservation index now
validates 52/52 capsules, 51,871 movie frames and 2,527,165,846 external bytes.

## Exact offline batch

The generated queue retains every exact `summary`, `hotspots` and `changes`
command for player, actor, contact, enemy/state, VRAM and SPU-RAM ranges. The
repeatable batch command is:

```bash
python3 tools/phase4_offline_seed_actions_batch.py \
  --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/seed-actions-v1/index.json \
  --write
```

The pinned reader reconstructed all 1,821 records across registers, RAM,
VRAM, SPU-RAM and passive block-start counts. The external index is
21,234,533 bytes, SHA-256
`2876fc81ba8e0e8ec93a0d9ca666380074e157b74ad461e354f6c9ff5dbdfc5f`.
Git retains its generator, schema, exact source/capsule hashes, bounded summary
and falsifiable tests—not movies, saves, chunks or reconstructed frame bytes.

## A11 observations

The moving seed is id 11, actor slot 20 (`0x800A07D0`); the target is slot 0
(`0x8009FD80`). The second Square press is frame 327. Exact carry attachment
first breaks at frame 329. The target reaches `+0x6C == -20` at frame 349,
then holds each integer value for two frame records through `-1` at frame 388.
The target leaves the live table at frame 389, on a frame where that table,
the actor/contact/player pools, VRAM and SPU-RAM all change.

At frame 349 passive flow includes the statically known
`contact_vs_actor_handler` arm block start `0x80058E08`; the proximity twin arm
block `0x8004B2C0` is absent. This distinguishes the covered arm family for the
natural hit without claiming the exact `sh`, cycle or contact-kind cause.
Unlike the earlier synthetic positive trial, the natural movie's seed does
not stay within 64 units of its hit-frame position afterward. The retained
artifacts keep both observations separate; the native press/no-press trial
remains the causal authority for the landing claim.

## A10 observations

Square at 1040 enters the handstand sequence; Square at 1213 exits it. Player
XYZ is exactly `[-68257,9593,-7324]`, grounded zero, for all 114 records from
1102 through 1215. State changes 0→5 at 1216 and 5→6 at 1222, then returns to
zero at 1254.

No active plant slot exists during the frozen run. Seed actor slots 2/3/4 are
present but none exactly matches player X/Z; their minimum squared distances
are retained. At the state-6 boundary only generic
`gameplay_effect_spawner` function blocks appear among the declared writer
families, and its known writer block start is absent. The capsule therefore
does not identify the mounted collision object or exact dismount writer.

## Decision

After the artifact joined the scheduler, the mechanically regenerated queue is
still 16 complete / 91 open but now has zero `offline_ready`, 35
`offline_partial`, four `live_required`, and 68 `no_capsule`. A11/A10 are
`offline_partial`; their current queue ranks are 7/24 after all derived
classifications are reordered. The pre-run ledger preserves their coherent
missing-capsule selection at ranks 31/32 when no `offline_ready` row existed.
The current queue/ledger SHA-256 values are `a391791c437a0f71444d45c4e7fdd04c7c6f08e9ef84e2ac82fc76d4433a0d85`
and `97e86754b0fbd9137f9ce1d6a1b5dc5ff4bc565020071fd7b72fe22a97654667`.
The ledger is valid with two executed and zero planned entries, including
pre-run and current post-run audits.

The rows remain open because enemy-family/contact-kind breadth, mounted-object
identity, and exact instruction writers are unresolved. Counts-mode
frame-boundary evidence is not every-cycle attribution. No new operator
fixture is requested.

## Validation

- `python3 tools/run_safe_tests.py` uses `/var/tmp` for both pytest and
  subprocess scratch after the preflight proved `/tmp` was at its user quota:
  `686 passed, 51 deselected` in 292.29 seconds.
- `TMPDIR=/var/tmp PYTHONPATH=. pytest -q -m local_media tests` passes all 50
  centrally provisioned local-media tests.
- A fresh `/var/tmp` Git archive was created from the tested commit. `python3
  tools/provision_clean_checkout_inputs.py
  --operator-root ~/Downloads/ABL` copied and verified 1,362 declared
  inputs; `python3 tools/build_identity.py --verify` passed 327/327 pins.
- With `TMPDIR=/var/tmp`, `python3 mod/build.py --mods
  mod/mods_code_only.yaml --no-disc --profile diagnostic` built the supported
  code-only combination with 1,195 changed EXE bytes. `python3
  tools/validate_mod_layout.py` passed the declarations, and `python3
  tools/phase3_hook_contract.py` reported 15 hooks, zero hard violations, nine
  cave discharges, and one bounded degraded hook with the image pin matching.
- In that clean archive, `python3 tools/validate_vault.py --check` reported no
  dangling links or evidence/schema violations; the queue and live-ledger
  `--check` commands passed 107 rows and two executed entries. The safe suite
  passed 682 with four Git-metadata-only skips, and all 50 local-media tests
  passed. `python3 tools/phase4_gate.py` returned the required open result at
  16/107 complete with all four exit predicates unmet.
