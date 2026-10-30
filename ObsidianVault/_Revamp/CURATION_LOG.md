---
kind: curation_log
id: REVAMP_CURATION_LOG
created: 2026-07-08
updated: 2026-07-08
---

# Revamp Curation Log

## 2026-07-08 - Gold Berry / Contact / HUD Safety Pass

### Curated Canon pages

- `Canon/Systems/SYS_contact_objects_and_drops.md`
- `Canon/Systems/SYS_enemy_death_and_permanence.md`
- `Canon/Systems/SYS_hud_counters.md`
- `Canon/Hooks/HOOK_800592A4_golddrop_death_tail.md`
- `Canon/Hooks/HOOK_800589D4_golddrop_pickup_default_branch.md`
- `Canon/Hooks/HOOK_forbidden_patch_ranges.md`

### Curated mod page

- `Mods/Gold Berry/MOD_gold_berry_token_drop.md`

Changes:

- Removed the pasted legacy working-note body from the curated mod page.
- Kept the active behavior: type-120 spinning glyph, floor landing, health-leaf-style timed despawn, guarded pickup, quota decrement, HUD pulse, and native enemy finalizer.
- Linked the verifier evidence ID `EXP_2026_07_07_golddrop_pickup_verifier`.
- Kept old wrong assumptions visible only as hazards or wrong-hypothesis references.

### Legacy notes annotated

- `Mods/Gold-berry drop on non-gold kills.md`
- `Systems/Session 2026-07-04 - board sign + consolidated build.md`
- `Systems/Berry projectile and homing.md`
- `Systems/Enemy AI state machine.md`
- `Systems/Retail Gameplay Completeness Gap Audit.md`
- `Systems/Consolidated mod build manifest.md`
- `Assets/Asset - Chunk 34 Master Mesh.md`
- `Hypotheses/HYP - visual equals collision.md`

### Current authoritative routing

- Gold Berry token implementation: `MOD_gold_berry_token_drop`
- Spawn hook: `HOOK_800592A4`
- Pickup hook: `HOOK_800589D4`
- Contact/drop Canon: `SYS_contact_objects_and_drops`
- Enemy quota/permanence Canon: `SYS_enemy_death_and_permanence`
- HUD counter Canon: `SYS_hud_counters`
- Patch-safety Canon: `HOOK_forbidden_patch_ranges`
- Visual/collision Canon: `SYS_render_collision_source_separation`

### Remaining curation backlog

- Work through `_Revamp/SRC_COVERAGE.md` subsystem by subsystem.
- Promote more runtime tests into stable `EXP_*` notes instead of relying on temporary `/tmp` artifacts.
- Continue adding superseded banners to legacy notes only when they contain claims that could mislead future implementation.

## 2026-07-08 - Blackberry / Berry Descriptor Safety Pass

### Curated Canon pages

- `Canon/Systems/SYS_berry_projectile_and_homing.md`
- `Canon/Systems/SYS_berry_pickup_render_descriptors.md`
- `Canon/Systems/SYS_seed_plant_behaviors.md`
- `Canon/Memory/MEM_80082030_native_berry_seed_descriptor.md`
- `Canon/Memory/MEM_80096B98_object_pointer_list.md`
- `Canon/Tables/TABLE_8001B42C_pickup_collect_dispatch.md`

### Curated mod page

- `Mods/Blackberry/MOD_blackberry_net_new_berry.md`

Changes:

- Removed the pasted legacy working-note body from the curated Blackberry page.
- Kept the active behavior: kind `0x25`, equip index `5`, private descriptor `0x80081234`, fast red-equivalent throw, HP-selector remap, and color word `0x2c2b051a`.
- Added `EXP_2026_07_07_blackberry_damage_parity` as the stable evidence note for the 2026-07-07 verification.
- Kept `0x80082030..0x8008203C` visible only as a forbidden native descriptor range, not as reusable scratch.
- Linked `0x80096B98` / `object_pointer_list[0x25]` as the targeted runtime repair path for Blackberry's private descriptor.

### Legacy notes annotated

- `Mods/Blackberry net-new berry.md`
- `Systems/Berry projectile and homing.md`
- `Systems/Consolidated mod build manifest.md`
- `Systems/Purple seed plant behaviors.md`
- `Systems/Seed plant output binding.md`
- `Systems/Yellow seed plant behaviors.md`

### Current authoritative routing

- Blackberry implementation: `MOD_blackberry_net_new_berry`
- Berry projectile / homing Canon: `SYS_berry_projectile_and_homing`
- Berry pickup descriptor/color Canon: `SYS_berry_pickup_render_descriptors`
- Seed plant Canon: `SYS_seed_plant_behaviors`
- Descriptor/cave safety Canon: `HOOK_forbidden_patch_ranges`

### Remaining curation backlog

- Continue `_Revamp/SRC_COVERAGE.md` subsystem passes for remaining seed colors, player health, level goal/exit triggers, and training tutorial systems.
- When code work resumes, verify purple seed colors and mega/homing visuals against the private-descriptor rule before patching.

## 2026-07-08 - Structural Migration Completion Pass

### Completed actions

- Moved legacy broad-folder Markdown notes into `Archive/Superseded` or `Archive/Unsorted Legacy`, or into the new `Experiments/*` and `Sessions/2026` locations where appropriate.
- Created structured Canon landing pages for remaining `convert_to_canon` / `split` rows that lacked a target page.
- Kept existing curated Gold Berry and Blackberry mod pages as the active mod records and archived their old working notes as superseded provenance.
- Closed the remaining `SRC_COVERAGE.md` `needs_review` rows by creating source-linked Canon/Mod notes or routing them to existing coverage.
- Regenerated `Canon/Indexes/Canon Index.md`, `Canon/Indexes/Address Index.md`, root `Home.md`, root `README.md`, and `Archive/Archive Index.md`.

### Counts

- Canon notes created from legacy migration rows: 150
- Source coverage notes created: 18
- Experiment notes migrated: 34
- Session notes migrated: 2
- Legacy notes archived/moved: 314
- Existing structured notes linked to archived legacy source: 33
- Archive aliases added for moved legacy notes: 314
- Legacy-source aliases added for migrated notes: 186
- Archive link placeholders created for old shorthand links: 44
- Legacy excerpts removed from mechanically imported Canon pages: 150
- Missing old sources already absent before this pass: 0

### Validation result

- `MIGRATION_MAP.md` has no unresolved action tokens.
- `SRC_COVERAGE.md` has no `needs_review` rows.
- Alias-aware wikilink sweep is clean.
- No legacy broad-folder Markdown remains outside the final structure, except intentional root landing pages.
