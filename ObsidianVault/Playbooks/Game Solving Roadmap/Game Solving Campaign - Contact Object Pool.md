---
kind: campaign
id: CAMPAIGN_contact_object_pool
name: Game Solving Campaign - Contact Object Pool
status: partial
created: 2026-08-02
updated: 2026-08-02
confidence: high
parent: PLAYBOOK_game_solving_phase_4
rows:
  - E06_contact_object_pool
---

# Game Solving Campaign - Contact Object Pool

## Scope

Owning family: **Objects/events/hazards**. Phase 1 row:
`E06_contact_object_pool`.

E06's shared 64-record contact-object pool: allocation, construction metadata,
update/contact dispatch, rendering, retirement, reuse, capacity, and producer
interfaces.

Non-scope: exhaustive cosmetic naming, forced guest hangs, and claiming every
pickup/seed/enemy campaign complete merely because they share this substrate.

## Current result

The resident allocator core is bounded at high value:

- Exact `64 x 0x38` pool and cursor ownership.
- Exact 129-row metadata-B and 78-row metadata-A bounds.
- All 94 resident allocator call sites enumerated.
- Exact 117-entry behavior dispatch and 50-entry render-kind table.
- Static proof of non-return at 64/64 occupied records.
- Hash-verified natural allocation, retirement, reactivation, walker/render, and 12
  cursor wraps from a retained capsule.

## Exit decision

**Allocator core bounded-exhausted; E06 offline frontier open; strict Phase 4 status
remains `partial`.** Typed state and original interfaces are advanced but not met. The
dedicated oracle, complete cross-overlay/data-derived frontier, field/reset ownership,
stage breadth, cross-system campaign breadth, matching-source closure, and dedicated
behavioral gate remain open.

## Ten-part child-campaign audit

| Requirement | Status |
|---|---|
| Scope, family, row | met |
| Pristine oracle | not met |
| Semantic frontier | advanced, not met |
| Lifecycle, capacity, reset | advanced, not met; capacity itself has native A/B proof |
| Native positive/negative controls | advanced, not met |
| Stage/variant/exception breadth | not met |
| Cross-system consumption contracts | advanced, not met |
| Source/decompilation status | advanced, not met |
| Findings, residuals, supersession | met |
| Executable gate and exit | advanced, not met |

Exact machine audit: `analysis/phase4_e06_methodology_audit.json`.

No new Interpreter movie is needed now. First run the named C/offline frontier batch
and inventory existing Interpreter cold-boot fixtures. Escalate only for a named oracle,
reset, transition, or exceptional-path event absent from retained evidence.

## Evidence

[[EXP_2026-08-02_phase4_e06_bounded_exhaustion]] |
[[SYS_contact_object_pool]] |
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]]
