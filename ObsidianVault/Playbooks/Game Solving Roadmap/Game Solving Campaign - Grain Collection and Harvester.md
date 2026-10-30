---
kind: campaign
id: grain_collection_harvester
phase: 4
family: collectibles_equipment_rewards
rows: [C01_grain_pickup, C02_fifty_grain_reward, C13_grain_harvester]
status: active
evidence: [analysis/phase4_collectibles_frontier.json, analysis/phase4_offline_collectibles_batch.json]
---

# Game Solving Campaign - Grain Collection and Harvester

## Scope and current decision

This active campaign owns ordinary grain pickup, the exact 50th-grain reward
path, grain-harvester equipment acquisition/follow, bit-`0x80` attraction,
ctor-`0x51` contact convergence, and the action-20 grain handoff. It does not
absorb HUD/results, generic contact capacity, audio assets, save/frontend
persistence, grain gates, or other collectibles.

The campaign is not complete and promotes no roadmap dimension. All selected
recordings are pristine save-start anchors, so `original_oracle` remains the
first unmet predicate.

## Reproduced frontier

- C01 frame boundaries 196 and 540, each with one grain increment and five
  action-4/radius-100 effect resets;
- the C02 frame-160 `49→50` boundary, unchanged true health 4, no same-frame
  SPU-RAM change, and the separately cycling display field;
- nine C13 action-20/grain boundaries and the frame-83 bit-`0x80` acquisition;
- actor ID 35 in fixed slot 63, its six authored stage rows, unique C13
  Stage-1 actor signature, and the `FLIKHARV.ALL`/`.ANM` asset dispatch;
- resident equip/follow function `0x80051DB4..0x80052090` and exact bit writer
  `0x80051EB0`;
- kind-`0x14` bit/radius gate, ctor-`0x51` metadata and target-`-1` store;
- the shared 64-contact updater's exact horizontal/vertical convergence law;
- distinct source squared radius `0x15F8F`, radius-add 100, and walker radius
  400; and
- grain increment `0x80054F9C`, unreachable fixed-address progress/life
  branch, and reachable health-4 store `0x80055124`.

## Open binding work

1. Preserve `original_oracle` as open until a centrally pinned cold-boot
   acquisition/reward reproduction exists.
2. Exhaust remaining static xrefs, source status, bit-removal and
   initialization/retirement ownership before live work.
3. If a later scheduler projection returns this campaign, predeclare one
   same-anchor control that changes only bit `0x80` or the attraction source
   radius; do not replay the same semantic observation.
4. Reuse existing central fixtures for denial, contact-capacity, reset,
   death/respawn, unload/reload and persistence breadth before requesting an
   operator recording.
5. Keep HUD presentation, audio identity, grain gates and persistence under
   their registered owners.

## Guard and handoff

`tools/phase4_collectibles_frontier.py` recomputes the frontier from the exact
external index, pristine executable/assets, Phase-1 census, central anchors
and semantic sources. `tests/test_phase4_collectibles_frontier.py` rejects
actor/asset/stage/bit joins, ctor metadata, convergence radii, reward
reachability, semantic-width, input-hash and instruction-byte drift.

The next lane remains `static`. A later live escalation is allowed only after
the debt scheduler reselects this campaign and the missing causal/control fact
is narrower than the remaining static and existing-fixture work.

Evidence: [[EXP_2026-07-30_phase4_collectibles_static_frontier]] ·
Canon: [[SYS_grain_collection_and_harvester]].
