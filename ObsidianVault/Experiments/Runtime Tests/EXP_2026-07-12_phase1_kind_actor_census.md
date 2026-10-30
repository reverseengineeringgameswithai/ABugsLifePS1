---
id: EXP_2026-07-12_phase1_kind_actor_census
status: confirmed-bounded
date: 2026-07-12
media: SCUS-94288 pristine retail
---

# Phase 1 contact-kind and actor-record census

This experiment is the evidence home for `analysis/phase1_kind_actor_census.json`.
It was collected from the hash-verified pristine image using the individually
hash-pinned saves named in that artifact. The contact-kind pointer table at
`0x80096B98` has a bounded contiguous 0–49 census. The chunk-31 actor buffer at
`0x8009FE04`, stride `0x84`, yielded 456 records and 38 distinct IDs across
Training and stages 1–15. These counts do not classify all roles: 46 contact
kinds and 36 actor IDs remain explicit unknowns, and Thud is not authored in
Bug Bar's chunk-31 table.

Authoritative consumers are `config/record_types.yaml`,
`config/semantic_state.yaml`, `analysis/phase3_record_types.json`, and
`analysis/mechanics_baseline.yaml`. Guards are
`tests/test_phase1_census.py` and `tests/test_phase3_records.py`. The external
saves are preserved by hash and media class in
`analysis/phase0_2_external_fixture_set.json`; their bytes remain outside Git.

Future MOD code may use the record base, stride, and typed fields only through
the schemas above. It must not treat a nonzero record as live, infer an unknown
ID's role, or assume Thud uses the same allocation source. The allocator,
initialization, reset, and retirement contracts remain later-phase work where
the typed schema marks them unresolved.

Related: [[SYS_record_layouts_and_lifetimes]],
[[MEM_80096B98_object_pointer_list]], and
[[Phase 1 - Establish the Whole-Game Mechanics and Campaign Baseline]].
