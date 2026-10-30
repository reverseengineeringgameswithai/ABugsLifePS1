---
kind: experiment
id: EXP_2026-07-26_phase4_fmv_resident_code_identity
date: 2026-07-26
phase: 4
campaign: fmv_playback
row: E15_fmv
status: static_method_banked
confidence: high
source_state: original_game
artifact: analysis/phase4_fmv_resident_identity.json
---

# Phase 4 FMV resident code identity

## Work packet

Closure debt selected only `fmv_playback` / `E15_fmv`, with `lifecycle` first
unmet and the static lane binding. The exact claim was that a runtime event at
shared PC `0x800500D8` or `0x80050284` is admissible as the resident
scene-flow caller only when the exact pristine owner, identity window,
selector, loader-call and delay-slot words all match. The falsifier was any
drift in either identity window, loader target, selector/mode ABI or resident
owner hash.

The required evidence domain was the current offline FMV index plus pristine
resident executable bytes, owner ASM and loader ABI. The predicted
authoritative machine layers were a typed schema, semantic C, generated
identity artifact and mutation guard. No live result or dimension promotion
was predicted.

## Offline localization

Ordered regeneration passed with 55 preserved capsules, 107 queue rows, nine
derived indexes over 34 rows and only E15 selected. The queue reported 91 open
rows, zero `offline_ready`, 42 `offline_partial`, zero `live_required` and 65
`no_capsule`.

The closed iteration receipt
`4d5df9a746901b8685dce1fc8b2190ae1dbc1a3c8b5cb60455bdfe0004588459`
re-executes `tools/phase4_offline_receipt_query.py` against all 16,060,589
bytes of external `fmv-lifecycle-v2`, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`.
It finds zero records for both centrally pinned Menu movie hashes. This
retains the earlier exclusion and supplies no resident-code observation.

## Static reconstruction

The immutable resident executable is
`REBUILD/files/SCUS_942.88`, SHA-256
`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
The scene-flow owner spans `0x8004FCA0..0x800502C4`, has 1,572 bytes and
SHA-256
`02fc946a4c8757792f646d23e5cabdac5e0cf4755211b733cc75aa15b2f0592f`.
Its exact ASM is pinned by `tools/repro_inputs.sha256`.

Two byte-exact callsite identities follow:

- game-over LOSE window `0x800500A4..0x80050104`, SHA-256
  `4aa82b8843e66504c47cee1f8c22dae99941580632a307a6e2f617abc53922aa`:
  selector word `0x2404002E` at `0x800500D4`, loader call
  `0x0C00F9F0` at `0x800500D8`, mode-zero delay word `0x00002821`
  and return `0x800500E0`;
- finale-C window `0x80050258..0x8005029C`, SHA-256
  `f0636a7464d92d8fe63b63887ad1848be90d6f1701014f35a7a530ab9361602d`:
  selector word `0x24040028` at `0x80050280`, the same loader call at
  `0x80050284`, mode-zero delay word and return `0x8005028C`.

Bare PC observations from the rejected Menu methods satisfy none of these
identity joins and remain unattributed.

## Bounded synthetic control

The centrally provisioned C16 anchor already reproduces the selector-46 LOSE
path. A single code-word difference at `0x800500D4` is sufficient to form the
discriminator:

```text
baseline: 0x2404002E, selector 46, mode 0, caller/return unchanged, limit 281
positive: 0x24040028, selector 40, mode 0, caller/return unchanged, limit 3162
```

Both branches use movie frames `[300,4006)`; a precise run would require a
separate passive receipt over the strictly wider `[299,4006)` window. The
required observations include resident and owner identity, exact pre/post
word, loader `a0/a1/ra`, selected-limit writer, completion writer, common
teardown and endpoint. The synthetic branch cannot be described as natural
Menu or finale ownership.

## Typed after-load method

The control remains deliberately unexecuted, but the static method gap is now
closed. The current external-debugger dispatcher adds one closed
`scenario.loadStateAndRun.after_load` operation with exact keys `kind`,
`address`, `original_word`, and `replacement_word`. It is valid only for
`code_write`. After the state load and instrumentation setup, but before the
first guest frame, it:

1. verifies an aligned 32-bit address and distinct 32-bit words;
2. reads and requires the declared original word;
3. writes the replacement with translated-code invalidation forced;
4. reads back and requires the replacement; and
5. returns the before/after words, byte count and code-invalidation result.

Any failure clears instrumentation and rejects the atomic job.
`scenario.bootAndRun` rejects the field. The rebuilt release binary is
SHA-256
`3735016cd206e1915a49d980016e064d40efc83aa8253eac8f60338906c712de`;
the dispatcher is
`132915bd80b99b37e40a056e1432d2cff6c84f6c54f729ce43cee14a0947c817`.
No emulator process was launched to obtain these static identities.

`tools/phase4_duckstation_batch.py` admits at most one after-load job, requires
it to be the positive arm of exactly one same-anchor pair whose negative arm
has no write, and requires byte-for-byte equality with the single typed v2
`code_write` perturbation. It rejects unknown fields, boot recipes,
unaligned/non-RAM addresses, equal words and unpaired writes.

## Current iteration boundary and handoff

The current iteration's immutable before-ledger contained no planned selector
control, so the new method did not authorize a retrospective live run. Closed
offline receipt
`5820a478e6c3605cc1b563815a33d88b84593f7e1abab743282b840ad97324c6`
re-executed the pinned reader over the 16,060,589-byte
`fmv-lifecycle-v2` index and confirmed that retained frame-boundary evidence
cannot supply the selector-40 counterfactual.

Generated escalation
`P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL` is now `planned` for the next
controller iteration. Its passive plan covers `[299,4006)`; its precise
selector-46/selector-40 plan covers `[300,4006)`, holds movie, state, media,
settings, instrumentation, capture and result limits fixed, and changes only
the word at `0x800500D4`.

`config/phase4_fmv_resident_identity.yaml` is the typed source contract.
`tools/phase4_fmv_resident_identity.py --write --check` verifies pristine
identity, owner and callsite bytes, the one-word discriminator and finite
windows, then generates `analysis/phase4_fmv_resident_identity.json`.
`tests/test_phase4_fmv_resident_identity.py` recomputes it and mutates both
callsites, the loader ABI and the method-support contract.
`tests/test_phase4_duckstation_batch.py` validates both retained plans and
mutates the only-difference pairing. Lifecycle, original interfaces, breadth,
cross-system and source remain partial; no Canon gameplay fact, MOD-private
behavior, row or dimension is promoted.

Original static facts: [[SYS_fmv_player_streaming]]. Campaign boundary:
[[Game Solving Campaign - FMV Playback and Skip]].
