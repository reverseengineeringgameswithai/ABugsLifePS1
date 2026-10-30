---
kind: conflict_register
created: 2026-07-08
updated: 2026-07-08
status: resolved_non_human_conflicts
---

# Conflict Register

This register resolves the technical conflicts that do not require operator judgment. Future
agents should treat the `Winning decision` column as the current source of truth unless a newer
live trace, movie verifier, or operator-confirmed observation explicitly supersedes it.

## Evidence Order

1. Live DuckStation trace, movie verifier, or replayable runtime artifact.
2. `src_re` C reference tied to addresses and runtime evidence.
3. Current mod ASM/C implementation.
4. Current Canon note with evidence links.
5. Old session notes and planning notes.
6. Static-only guesses.
7. Superseded or contradicted notes.

## Resolved Conflicts

| ID | Status | Losing claim | Winning decision | Evidence | Canon destination | Archive action |
|---|---|---|---|---|---|---|
| CF-001 | resolved | Gold-drop should spawn a literal type-34 gold berry. | Gold-drop mod uses a type-120 spinning gold-kill glyph. Type 34 remains original-game "arm/equip gold" behavior only. | `mod/caves/golddrop.c`; `src_re/enemy_drops.c`; operator-confirmed working pickup on 2026-07-07. | `Mods/Gold Berry/MOD_gold_berry_token_drop.md`; `Canon/Constants/CONST_drop_types_and_actions.md`; `Canon/Systems/SYS_contact_objects_and_drops.md` | `Archive/Wrong Hypotheses/WHYPE_gold_drop_type34_and_80049958.md` |
| CF-002 | resolved | `0x80049958` is a safe once-per-kill gold-drop spawn hook. | Do not use `0x80049958` for gold-drop spawning. Use one-shot contact-vs-actor tail hook `0x800592A4`; `0x80049958` can execute repeatedly for one death. | Forced spider trace hit old hook six times; `src_re/enemy_drops.c`; Gold Berry mod notes. | `Canon/Hooks/HOOK_800592A4_golddrop_death_tail.md`; `Mods/Gold Berry/MOD_gold_berry_token_drop.md` | `Archive/Wrong Hypotheses/WHYPE_gold_drop_type34_and_80049958.md` |
| CF-003 | resolved | Mega or homing berry is permanent like gold. | Only gold-berry permanent kills spend `0x800A658E` among berry throws. Mega, homing, blue, red, and Blackberry-red damage are temporary KOs. Mine Plant is a separate confirmed permanent lane. | `src_re/enemy_death_permanence.c`; `ObsidianVault/Systems/Enemy death and permanence.md`; runtime berry tests. | `Canon/Systems/SYS_enemy_death_and_permanence.md` | `Archive/Wrong Hypotheses/WHYPE_mega_permanent.md` |
| CF-004 | resolved | `0x80082030` is reusable descriptor/slack for custom berry visuals. | `0x80082030..0x8008203C` is native berry/seed descriptor memory. Do not overwrite; use a private descriptor and repair object pointer lists if needed. | `src_re/known_crash_cave_hazards.c`; Blackberry color regression; current Blackberry notes. | `Canon/Hooks/HOOK_forbidden_patch_ranges.md` | `Archive/Wrong Hypotheses/WHYPE_forbidden_patch_ranges.md` |
| CF-005 | resolved | `0x80081058..0x800810A4` is safe helper/code-cave space. | `0x80081058..0x800810A4` is live-zeroed during ALLMODS boot. Do not place helper code there. | `src_re/known_crash_cave_hazards.c`; live ALLMODS boot evidence. | `Canon/Hooks/HOOK_forbidden_patch_ranges.md` | `Archive/Wrong Hypotheses/WHYPE_forbidden_patch_ranges.md` |
| CF-006 | resolved | Visible floor is chunk-35 terrain buffer, or visual terrain equals collision. | Visual and collision are separate. Visible terrain/floor uses DAT payloads through `FUNC_80010000`; chunk-35/`FUNC_800172DC` is a shared mesh path with occluded terrain role in tested states; collision uses chunk-32 sector/plane data. | `Finding - Visual is not collision`; G28/G29/G30 experiments; `src_re/collision_source_converter_80030f60.c`. | `Canon/Systems/SYS_render_collision_source_separation.md` | `Archive/Wrong Hypotheses/WHYPE_visible_floor_equals_collision.md` |
| CF-007 | resolved | Mid-gameplay `scene_id` or substate pokes are clean warp levers. | `scene_id` is immutable during active gameplay. Native transition must go through transition state/fade/shell-phase sequencing; raw mid-gameplay `scene_id` mutation crashes because gameplay and overlay consumers dispatch against mismatched loaded resources. | `Experiment - In-game warp trigger`; `Gameplay - Warp and Level Transition`; event globals notes. | `Canon/Systems/SYS_warp_and_level_transition_safety.md` | `Archive/Wrong Hypotheses/WHYPE_midgame_scene_id_clean_lever.md` |
| CF-008 | resolved | Static r2 function boundaries and `jal` call graph are authoritative. | Static RE is a hypothesis layer unless backed by runtime, source, or overlay analysis. Jump-table cases and overlays can be invisible to `jal` scans and may use invented helper boundaries in C references. | `Blocker - Function boundaries and overlays evade the static call graph`; `src_re/pickup_handlers_80054288_80054554.c`; `Symbol Map Baseline`. | `Canon/Systems/SYS_re_evidence_policy.md` | `Archive/Wrong Hypotheses/WHYPE_static_callgraph_authority.md` |

## Human-Needed Conflicts

None from the current conflict set. Human input is still needed for:

- Firsthand operator observations not yet backed by trace/movie artifacts.
- Desired mod behavior when it intentionally differs from retail.
- Naming preferences for user-facing terms.

## Follow-Up Actions

- Keep original notes in place until a later archival pass is explicitly approved.
- When touching old notes, add a short superseded callout pointing to the relevant `WHYPE_*` archive note instead of deleting history.
- Do not promote old claims into Canon unless the winning decision above is revised by stronger evidence.
