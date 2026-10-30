---
type: experiment
date: 2026-08-19
status: scaffolded-calibration-only
method: offline-cross-port-semantic-ranking
source_project: ABLPC
source_commit: b46b836644380e4ffc395e1f8022f954fd830864
source_binary_sha256: 97c95ba5572dce637f6ea6325dbfff0c9a2d002a30d3dc88f39e0f558a27b878
target_binary_sha256: 1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20
confidence: calibration_only
---

# PC-to-PS1 semantic bridge pilot

## Purpose

Provide a small, read-only inbound path for PC findings to generate ranked PS1
hypotheses without importing PC authority into the PS1 Canon. This is the
reverse direction of ABLPC's existing PS1-to-PC comparison workflow.

The pilot is deliberately outside the Phase 4 closure machinery. It can choose
a candidate or a smaller discriminating experiment; it cannot satisfy a
campaign predicate, promote a Canon statement, or authorize a live run.

## Boundary

- A PC packet enters this repository only as `external_lead`.
- It must pin the ABLPC commit, PC executable SHA-256, PC locator, and hashes of
  every cited committed ABLPC note.
- The ABL consumer verifies cited material through `git show <commit>:<path>`;
  it never treats ABLPC's working tree as evidence.
- The packet must target the pristine PS1 executable SHA-256
  `1aa28954...19d20` and use the architecture-neutral feature normal form.
- Rankings are always `ps1_candidate_only`; the result hard-codes
  `promotion_allowed: false`.
- A target-side PS1 static binding plus a PS1-native causal discriminator and
  falsifying control remain required before behavioral promotion.
- PC addresses, structure offsets, compiler shapes, timing, and platform
  behavior never transfer automatically.

This is the PC-to-PS1 mirror of ABLPC's `Cross-Port Evidence Policy`. Any
conflict is preserved as a port difference; the pristine PS1 build is
authoritative only for PS1 claims.

## Implemented surface

- `config/cross_port_semantic_lead.schema.json` — versioned inbound packet
  contract.
- `config/cross_port_semantic_candidate_catalog.schema.json` — versioned PS1
  candidate-catalog contract.
- `tools/cross_port_semantic_bridge.py` — strict JSON/provenance validation and
  deterministic exact-feature weighted ranking. It is read-only by default and
  refuses output replacement.
- `analysis/cross_port/pc_to_ps1_berry_accumulator_calibration.json` — one
  committed-PC-evidence calibration lead.
- `analysis/cross_port/ps1_semantic_candidate_calibration.json` — four curated,
  commit-pinned PS1 candidates used only to test the scoring boundary.
- `tests/test_cross_port_semantic_bridge.py` — identity, authority, width,
  signedness, duplicate-key, read-only, overwrite-refusal, provenance, and
  ranking guards.

The current catalog is curated. The pilot does **not** yet extract normalized
features automatically from MIPS or the PC Ghidra export. Adding an extractor
is a separate work packet and must keep raw decompiler text outside cross-port
packets.

## Calibration

The first packet encodes the PC-confirmed berry accumulator at `0x0041C9B0`:
five byte columns, `row*5+type`, unsigned `<200`, guarded `+2`, and threshold
`100`. The candidate catalog intentionally contains the already-known PS1
increment window, its related decay window, and two unrelated mathematical
controls.

The ranker returns:

1. `PS1-CAND-BERRY-ACCUMULATOR-INCREMENT`, `0x8004B4C0-0x8004B53C`, eligible,
   `10000/10000` basis points;
2. `PS1-CAND-BERRY-ACCUMULATOR-DECAY`, ineligible, `2222/10000` after the
   missing-required-feature penalty;
3. the dandelion and wall-math controls, ineligible, zero.

This is a circular positive calibration because the correspondence was already
known on both ports. It demonstrates fail-closed transport and scoring only; it
is not a new discovery, a new berry claim, or independent confirmation.

## Commands

```bash
python tools/cross_port_semantic_bridge.py validate-lead \
  analysis/cross_port/pc_to_ps1_berry_accumulator_calibration.json \
  --source-repo ~/ABLPC

python tools/cross_port_semantic_bridge.py validate-catalog \
  analysis/cross_port/ps1_semantic_candidate_calibration.json \
  --target-repo . --target-binary REBUILD/files/SCUS_942.88

python tools/cross_port_semantic_bridge.py rank \
  analysis/cross_port/pc_to_ps1_berry_accumulator_calibration.json \
  analysis/cross_port/ps1_semantic_candidate_calibration.json \
  --source-repo ~/ABLPC --target-repo . \
  --target-binary REBUILD/files/SCUS_942.88

pytest -q tests/test_cross_port_semantic_bridge.py
```

The three bridge commands are read-only unless `rank --output NEW_PATH` is
given. Output paths must not already exist.

## File identities

```text
cbab2f163213309854c4aa86dca8dbc5abb7f47470e5e8a0a649c4af4634bc9f  tools/cross_port_semantic_bridge.py
92ef41671566d7ca84b40a5951d65ccb9e2ffd9d8773e996aa62a9357fa7db33  config/cross_port_semantic_lead.schema.json
8ddf8f85c03139927d66f7eb43034cfaf37c5649899853aa43421c6fc0d17340  config/cross_port_semantic_candidate_catalog.schema.json
2d6b191be1cadeabdc006ee5698db03b1160f4255d242805c0635554a505b2b0  analysis/cross_port/pc_to_ps1_berry_accumulator_calibration.json
78b21267aed24d883ff04bb453a9df997cd0a808bbca60a6ee52e0400d748a4b  analysis/cross_port/ps1_semantic_candidate_calibration.json
f605474f345bbe70e96179a8bb666d987db8c6db5f2ceedc06a66708a28c777d  tests/test_cross_port_semantic_bridge.py
```

## Discovery activation gate

A first real discovery packet must:

1. come from a committed ABLPC state and committed PC-native evidence;
2. pose a bounded PS1 question;
3. omit any known PS1 locator or semantic name from the packet;
4. rank against candidates prepared without knowledge of the expected answer;
5. preregister the smallest PS1-native discriminator before inspecting the
   result; and
6. remain an Experiment lead until that discriminator succeeds.

Only after a successful blind or held-out case should automatic MIPS candidate
extraction or a neutral shared matcher be considered.

## ABLPC coordination record

ABLPC commit `1433df6` independently records the reciprocal coordination note
at `Vault/20-Research/Cross-Port/XPORT-20260819-008 - Bidirectional semantic
bridge coordination.md` and links it from ABLPC's Reverse Engineering MOC. The
commit adds documentation only; it does not implement a PC exporter.

The calibration packet intentionally remains pinned to ABLPC commit
`b46b836644380e4ffc395e1f8022f954fd830864`, where both cited PC evidence notes
exist with the recorded blob hashes. A later coordination commit does not alter
that evidence identity.

## Related

- [[Phase 4 - Closure Conundrum and Recovery Plan]]
- [[Phase 4 - Reverse Engineering Operating Method]]
- [[EXP_2026-08-04_phase4_e14_bounded_exhaustion]]
