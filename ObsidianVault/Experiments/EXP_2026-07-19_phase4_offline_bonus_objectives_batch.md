---
type: experiment
status: complete
date: 2026-07-19
system: Phase 4 offline bonus-objective analysis
phase: 4
---

# Phase 4 offline bonus-objectives batch

This iteration consumed the coherent `C18_bonus_entry`,
`F16_bonus1_spiders`, `F17_bonus2_mushrooms`, and
`F18_bonus3_grasshoppers` cluster. All four campaign rows remain open. The
acceptance-contract sidecar matched SHA-256
`715f3e51648e781eccea4ff12940ac83363e0a0fa8b73097b38a398bd1e1cad2`;
the initial context, roadmap, Phase-4 note, capsule experiment, current
107-row queue, and recursive 110/147-file movie inventories were revalidated.

## Selection and escalation reason

Before collection the queue reported 16 complete / 91 open, with zero
`offline_ready`, 35 `offline_partial`, four `live_required`, and 68
`no_capsule`. C18/F16/F17/F18 were the complete remaining `live_required`
set at ranks 33–36 and shared three already-existing Bonus movies. Escalations
`P4-ITER70-C18-MISSING-CAPSULE`, `P4-ITER70-F16-MISSING-CAPSULE`,
`P4-ITER70-F17-MISSING-CAPSULE`, and
`P4-ITER70-F18-MISSING-CAPSULE` were generated and guard-validated before
launch. Their exact pre-run queue and ledger hashes are retained in
`config/phase4_live_escalations.yaml`.

`/tmp` had free space but the user's tmpfs quota was exhausted, so the two
fresh profiles used `/var/tmp`, distinct ports 20731/20732, and owned PIDs
1003519/1003987. Only the complete preserved runtime was launched; all 207
runtime manifest entries passed and the running executable SHA-256 was
`55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8`.
The standalone archived executable remained identification evidence only.

## Collection and preservation

Both runs verified mounted pristine `SCUS-94288` and inspected all three save
anchors before replay. JSON serials were not used as media proof. Each
collector replayed the exact 3,653-, 10,045-, and 5,020-frame recordings and
ran its cached-interpreter native control. The collection pairs are:

- `bonus-objectives-v1-20260719`: collection `b26151eb…`, batch `55fd0000…`;
- `bonus-objectives-v2-20260719`: collection `b155a6a3…`, batch `80b9cc9f…`.

Both batches report all three exact movies complete and zero failures. Every
frame chunk and every checkpoint is byte-identical across the independent
runs. Only the owned PIDs were stopped. The central preservation set now
passes 55/55 capsules, 70,589 movie frames, and 3,391,058,326 external bytes
under reader SHA-256
`b3898f928800efad5a949d1369aa65d786067505e0ed915eec8fdb99f0aa1dde`.

## Exact offline batch

The command was:

`python3 tools/phase4_offline_bonus_objectives_batch.py --external-output ~/Downloads/ABL-external-evidence/derived/Phase4/bonus-objectives-v1/index.json --write`

It reconstructed all 18,721 retained boundaries across registers, RAM, VRAM,
SPU RAM, and passive block flow. The external index is 85,458,183 bytes,
SHA-256
`20896ac78723fbf6be13754e3f9af1261d14fd9fe914012eb34ea79e386e1fb5`.
Git retains its generator, schema, hash manifest, bounded summary, tests, and
exact queue queries—not movie, save, checkpoint, or capsule bytes.

Observed natural timelines:

- Bonus 1: streak `1,2,3,4,0` at frames `128,352,590,742,1072`; completion
  changes latch `0→6` and flags `0→2`; scene `17→16` follows at `1131`.
- Bonus 2: sequences `[6]`, `[6,5]`, `[6,5,4]`, `[6,5,4,2]`, and
  `[6,5,4,2,3]` at `109,159,209,261,313`; completion changes latch `0→6`
  and flags `34→35`; scene `1→16` follows at `431`.
- Bonus 3: streak `1,2,3,4,0` at `337,743,1429,1969,2467`; completion
  changes latch `0→6` and flags `51→55`; scene `3→16` follows at `2526`.

The completion boundaries cover the documented resident challenge block
families. Passive block starts are not exact-instruction/cycle write
attribution. The natural movies do not replace the earlier expired-impact,
duplicate-mushroom, or stationary miss/reset controls, and do not decode
scene-16 asset selection, persistence, or return dispatch.

## Queue result

After registering and revalidating the batch, all four rows derive
`offline_partial`. The queue ends with zero `offline_ready`, 42
`offline_partial`, zero `live_required`, and 65 `no_capsule`; it remains 107
unique rows with 16 complete / 91 open. No campaign row or family closes.

The authoritative queue SHA-256 is
`06357a1d06f2ea9a4ad9edf172624a25e0d16a9c0ba94316116b4cf94bb7e0a3`;
the six-entry executed escalation ledger SHA-256 is
`c5d10cf8e51232668722046201c31a8927e930353ec3570f95b2f3ae16e2cf5c`.
The central fixture set now has 1,032 hash-pinned entries and SHA-256
`54148cdc0a7c2c275474d8f5f5c3a90143bd031c11566c0d99a3d839b3a4f8ae`.
Its capsule join promotes the three Bonus movie leads to `pristine` only from
the two media-verified, hash-identical capsule collections; JSON serials alone
remain insufficient. The generated upstream reconciliation records that
classification promotion and refreshes 14 dependency-only consumers while
preserving their normalized runtime/control payloads and historical live
provenance.
