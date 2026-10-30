---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Systems/Actor model binding catalog.md
aliases:
  - "Actor model binding catalog"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Systems/Actor model binding catalog.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Actor_model_binding_catalog.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Actor model binding catalog
type: system
status: solved for RCG-005
updated: 2026-07-02
confidence: CONFIRMED for format, plant type binding, type-0x3f discriminator, regular enemy/boss actor slots listed below; STATIC-CORPUS for unused/untested cast variants
tags: [system, models, actors, plants, editor, rcg-005]
---

# Actor Model Binding Catalog

> Closure note for [[Retail Gameplay Completeness Gap Audit]] `RCG-005`. The broad binding gap is no longer open: the project has a single `.ALL`/`.ANM` grammar, an editor-safe corpus parser, a plant type-to-model law, a type-`0x3f` kind discriminator for visible pickups/objects, and runtime actor-slot bindings for the regular enemy/boss families already decoded. Remaining retail feel work is narrower and stays in `RCG-006`, `RCG-008`, `RCG-013`, `RCG-014`, `RCG-020`, `RCG-023`, and `RCG-026`.

## Closure Claim

`RCG-005` asked to bind models to object kinds and runtime actors: Flik, enemies, bosses, plant outputs, carried seed, harvester, and animated props. The binding layer is now cataloged:

- **Format:** `tools/parse_all_anm.py` round-trips the full authored model corpus: `.ALL` 78/78 and `.ANM` 58/58. Current grammar lives in [[Asset - ALL ANM Format Grammar]].
- **Plants:** [[Seed plant output binding]] proves plant slot **type N -> PLANTNN.ALL** through `0x800A649C + type*4`, with the full 20-entry seed matrix live-verified. Source anchor: `src_re/plant_spawn_8005bdbc.c`.
- **Pickups / animated props:** [[MEM - Type-0x3f placement record]] and `src_re/source3f_dispatch_80053814.c` prove `kind` selects both visible object construction and contact behavior for FLIK letters, berries, seed tokens, grain, telescope/hint gem, and kind `0x31`.
- **Characters / enemies / bosses:** [[Enemy AI state machine]] binds the runtime actor slots and driving functions for regular chasers, mover-VM enemies, Hopper, Thumper, and the bird/finale actor. The model files are in the now-validated `CHARS*` corpus.
- **Source catalog:** `src_re/actor_model_binding_catalog.c` records the resolved bindings and explicitly routes non-claims.

No new mod C was needed for this closure. This was a catalog/RE documentation pass over existing runtime and static evidence.

## Binding Map

| Runtime thing | Model / asset family | Binding evidence | Residual routed elsewhere |
|---|---|---|---|
| Flik player | `CHARS/FLICK.ALL` + `FLICK.ANM` | Live residency/render evidence in [[Finding - Character ALL model format]]; current byte grammar in [[Asset - ALL ANM Format Grammar]] | Fine animation channel semantics only; not an RCG-005 blocker |
| Flik variants | `CHARS3/FLICKD.ALL`, `FLICKP.ALL`, `FLIKHARV.ALL` | Static corpus, validated parser | Harvester mechanic/equip/effect remains `RCG-020` |
| Carried / plantable seed | `BITS/SEED.ALL` | Static corpus + [[Seed planting system]] actor path | Per-level seed authoring stays in seed-system work |
| Planter prop | `BITS/PLANTTER.ALL` | Static corpus, same grammar | Exact scene role is event/authoring detail |
| Plant outputs | `PLANTS/PLANT01..11.ALL`, `PLANTS2/PLANT12..14.ALL` | `type N -> PLANTNN.ALL` via live plant model table; all 20 matrix rows verified | Per-level plant manifest source on disc; handler SFX/durations |
| FLIK letters | Type-`0x3f` kinds `0x10..0x13` | Generic visible construct + F/L/I/K handlers | Elevated authored Y drift remains `RCG-027` |
| Grain | Type-`0x3f` kind `0x14` | Grain construct ctor `0x51`, native relocation proven elsewhere | Sprite/material/FX polish remains `RCG-008/013/014` |
| Berries | Type-`0x3f` kinds `0x21..0x24` | Kind changes marker/equip behavior and object descriptor path | Berry projectile details remain [[Berry projectile and homing]] |
| Seed tokens | Type-`0x3f` kinds `0x29..0x2D` | Token handlers + `fcn_8003e760` atlas reskin; plant chosen later by seed spawner | Purple grant id map remains seed/berry residual |
| Telescope / hint gem | Type-`0x3f` kind `0x30` | Bobbing Y path + contact action decoded in `source3f_dispatch` | Telescope camera/special presentation remains `RCG-010` if pursued |
| Animated construct | Type-`0x3f` kind `0x31` | Dedicated source path exists and is cataloged | Full retail semantics remain `RCG-026` |
| Regular chaser enemies | `BADBUG`, `FLY`, `MOS`, `WASP`, `DRAGFLY`, `HSPIDER`, etc. | `0x80095358` + `FUNC_8004DF18` runtime family in [[Enemy AI state machine]] | Damage/death/permanent-kill rules stay `RCG-006/022` |
| Stationary / mover enemies | `BADWORM`, `ROLL`, `WEEVIL`, etc. | Mover-VM actor family `FUNC_8004C13C` | PATH and event program details stay `RCG-009/025` |
| Hopper | `CHARS2/HOPPER.ALL` + `.ANM` | Fight actor is chaser slot `0x80095358` | Defeat trigger/bird sequence remains `RCG-006` |
| Thumper | `CHARS2/THUMPER.ALL` + `.ANM` | Fight actor is chaser slot `0x80095358`; Y-law/defeat-chain decoded | Overlay HP/throw/berry bookkeeping remains `RCG-006` |
| Thud | `CHARS3/THUD.ALL` + `.ANM` | Static corpus binding | Runtime fight remains `RCG-006` |
| Bird/finale setpiece | `CHARS3/BBIRD.ALL` + `.ANM` | Actor `0x80090BC0`, driver `FUNC_8004DD98` | Hopper defeat context remains `RCG-006` |
| Cast NPCs | `ATTA*`, `DOT`, `GYPSY`, `HEIM`, `MANNY*`, `ROSIE`, `SLIM`, etc. | Static corpus, validated grammar | Dialogue/cutscene triggers are event/front-end work |

## Editor Interpretation

The editor now has enough authoritative binding information to stop treating actor presentation as an unknown model-discovery problem:

- Use `.ALL`/`.ANM` as the shared actor/plant/prop asset family, parsed by `tools/parse_all_anm.py`.
- For plant previews, bind by plant **type number**, not by seed color directly. Seed color/count maps to a type through the engine table; type maps to `PLANTNN.ALL`.
- For type-`0x3f` pickups/objects, bind by `kind`. The same byte selects both visible construction and behavior.
- For enemies and bosses, bind the actor family to the model corpus and use the runtime behavior notes to decide what is decoded versus still behavior-residual.

This does **not** claim the offline editor renders every actor exactly like retail. CLUT/material, transparency, pickup sparkle, health leaves, boss HP, death logic, and per-level model-load manifests are deliberately tracked by narrower gaps.

## Reproduction / Evidence

- Static parser proof: `python3 tools/parse_all_anm.py` over `REBUILD/files`.
- DuckStation runtime evidence reused from prior isolated sessions:
  - plant matrix: [[Seed plant output binding]] (`SCUS-94288_8.sav`, fork rev `fe0cca1`, port `23460`);
  - enemy/boss actors: [[Enemy AI state machine]];
  - Flik model residency/rendering: [[Finding - Character ALL model format]].
- Current project preflight for this closure: ABL repo HEAD `6faa6e65f4bb6ab49026a044c01e1a69423965ce`; DuckStation fork HEAD `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`. Both worktrees had pre-existing local changes; none were reverted.

## Related

[[Asset - ALL ANM Format Grammar]] · [[Asset - Character and plant models]] · [[Seed plant output binding]] · [[Seed planting system]] · [[MEM - Type-0x3f placement record]] · [[Enemy AI state machine]] · [[Retail Gameplay Completeness Gap Audit]] · `src_re/actor_model_binding_catalog.c` · `src_re/plant_spawn_8005bdbc.c` · `src_re/source3f_dispatch_80053814.c` · `tools/parse_all_anm.py`
