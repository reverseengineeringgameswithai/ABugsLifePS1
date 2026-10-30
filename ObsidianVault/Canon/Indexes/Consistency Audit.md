---
kind: index
id: CONSISTENCY_AUDIT
created: 2026-07-09
updated: 2026-08-19
status: generated
generated_by: RCA campaign (deep-dive audit + validate_vault.py)
tool: tools/validate_vault.py
test: tests/test_vault_consistency.py
baseline: tests/vault_lint_baseline.json
---

# Consistency Audit — repo-wide inconsistency / gap register (RCA campaign)

Authoritative ledger for the **Repo Consistency Audit & Remediation** campaign. A three-front deep-dive
(vault, C/decomp substrate, cross-artifact) found the repo's parallel sources of truth had silently diverged
while the vault sat mid-migration and **uncommitted** (`git status` at start: 305 deletions / 669 untracked /
108 modified). Each finding below has a stable `AUDIT-xx` id, severity, evidence, fix, and status. The linter
`tools/validate_vault.py` measures the vault-side findings; its counts ratchet down through
`tests/vault_lint_baseline.json` (test: `tests/test_vault_consistency.py`).

**Linter baseline (a0, campaign start):** dangling_links 55 (21 distinct) · archive_only 3938 (505 distinct) ·
evidence_policy 80 · evidence_deadfile 75 · dup_address 9 · missing_alias 174 · schema 2.

Status legend: `open` · `in_progress` · `resolved` · `deferred`.

---

## Theme B — wikilinks route to superseded content (trust-breaking)

| id | severity | finding | evidence | fix | status |
|----|----------|---------|----------|-----|--------|
| AUDIT-01 | critical | Canon Function/Memory notes carry `id:` but **no `aliases:`**; `Archive/Superseded/` copies do, so bare `[[FUNC_<addr>]]`/`[[MEM - …]]` links resolve to archived notes. 174 Canon Function+Memory notes lack a self-alias. | `validate_vault.py` missing_alias=174; `FUNC_80010000…md` (no aliases) | a1: add `aliases:[FUNC_<addr>,0x<addr>]` to every Canon Function/Memory note; strip colliding bare-ID aliases from 40 Archive copies | **resolved** (missing_alias 174→0) |
| AUDIT-02 | high | link occurrences resolve **only** to `Archive/` (`API - *`, `Finding - *`, `Experiment - *`); many should retarget the consolidated Canon note or a surviving Canon note. | archive_only | a1 aliasing dropped Archive-routed FUNC/MEM links (Canon now wins); linter re-scoped to LIVE sources → 230 live→archive links remain | **partial** (3938→230; rest a7) |
| AUDIT-03 | high | 22→15 distinct **truly dangling** FUNC IDs (all real function-starts: `result_upload_anim_frame, play_sound, berry_projectile_update, DMACallback, Ss/Spu/Cd SDK…`) + `MEM_GLOBAL_MEMORY_MAP`, `enemy-spawn-architecture`, `tools/decomp_candidates.py`. | dangling_links | a1: 15 stub Canon Function notes; retarget 2 live links; Memory aliasing fixed `MEM_GLOBAL_MEMORY_MAP` | **resolved** (live dangling → 0) |
| AUDIT-04 | medium | `[[Gap Audit\|…]]` etc. were **escaped-pipe table cells**, not malformed markdown (Obsidian handles `\|`); all originate in Archive history. | linter parse | a1: linter strips the `\` artifact + ignores Archive-sourced links (frozen history) | **resolved** (parser fixed) |
| AUDIT-05 | high | **82/135 Canon Function notes were orphans** (no resolvable inbound link) — a consequence of AUDIT-01. | vault audit | a1 aliases make bare-ID links resolve; a6 Address Index adds the rest | **partial** (aliases done; index a6) |

## Theme C — evidence-policy broken (trust-breaking)

| id | severity | finding | evidence | fix | status |
|----|----------|---------|----------|-----|--------|
| AUDIT-06 | critical | 80 Canon notes were `status: confirmed/live_confirmed/proven` with **no linked `EXP_`**. Per `SYS_re_evidence_policy`, static-only claims must be `static_seen`. | evidence_policy=80 | a2: linked the validating EXP to 11 SYS/HOOK/MOD notes (kept status); downgraded 72 unsubstantiated FUNC/MEM notes → `static_seen` (0 were census-dynamic); fixed 2 EXP date-typo refs | **resolved** (→0) |
| AUDIT-07 | critical | 75 evidence entries pointed at **deleted** legacy files. | evidence_deadfile=75 | a2: dropped dead-file evidence in the same pass (69 notes) | **resolved** (→0) |
| AUDIT-08 | low | `FUNC_800313A8` missing `name`+`evidence` keys and used a descriptive `id` (broke bare-ID links). | schema=2 | a2: added keys; normalized `id:FUNC_800313A8` + bare alias | **resolved** (→0) |

## Theme A — migration half-done / uncommitted (structural)

| id | severity | finding | evidence | fix | status |
|----|----------|---------|----------|-----|--------|
| AUDIT-09 | high | `Canon/Systems/` holds 29 real `SYS_` notes buried among ~126 legacy-prefixed imports (`Finding_ 47, Asset_ 13, Gameplay_ 8, Core_ 5, Enemy_ 5…`) with `status: legacy_import_needs_curation`. | `ls Canon/Systems` | a7: **committed** them (honestly flagged by their status); the structural migration is done. **Per-note topical merge into the 29 SYS_ notes is ongoing RE content work** (not mechanical) — tracked as the residual below | **partial** (committed; curation is a content backlog) |
| AUDIT-10 | high | `Canon/Memory/` has 8 confirmed `MEM_-_*` duplicate twins of `MEM_<addr>_*` notes (aliases live on the twin). Includes the `0x8012C1D0` contradiction (AUDIT-14). | dup_address | a7: merged all 8 (1 in a3 + 7 here) — twin aliases moved onto the canonical `MEM_<addr>_*` note (inbound `[[MEM - …]]` links redirect off Archive), twins deleted | **resolved** (dup_address → 0) |
| AUDIT-11 | high | Whole vault is uncommitted (305 D / 669 ?? / 108 M) — nothing enforces consistency; drift accrued invisibly. | `git status` | a0 committed the linter guard; a1–a6 committed per-theme; **a7 committed the migration in 3 batches** (Canon+Experiments / Archive+deletions / stragglers). Only the scratch `Untitled.canvas` + `.obsidian` UI state remain untracked | **resolved** |

## Theme D — function-identity conflicts (wrong-identity risk)

| id | severity | finding | evidence | fix | status |
|----|----------|---------|----------|-----|--------|
| AUDIT-12 | high | `0x80059e44` had **4 names** (note `ContactRecord_allocator` / src_re+wip `contact_alloc` / sym+memory `spawn_drop`). | note title vs sym | a3: renamed note → `FUNC_80059E44_spawn_drop`; evidence [[EXP_2026-07-07_golddrop_pickup_verifier]] (allocator = its constructor sub-role) | **resolved** |
| AUDIT-13 | high | `0x8005bdbc` note filename embedded a **foreign** address `fcn_8003e760`; sym=`plant_spawn`. | filename vs sym | a3: renamed → `FUNC_8005BDBC_plant_spawn`; runtime `functionBounds` confirmed `0x8003E760` (token_descriptor_reskin, 13 callers) is a distinct fn | **resolved** |
| AUDIT-14 | high | `0x8012C1D0` MEM twins: "Terrain vertex buffer" (inbound links land here) vs "Shared mesh vertex buffer (terrain **+ actors**)". | dup_address | a3: the twin was a redundant landing-page stub (its body already agreed "shared"); merged its aliases onto the canonical Shared note (6 inbound links redirected off Archive), deleted the twin | **resolved** |
| AUDIT-15 | high | `MEMORY.md` + `enemy-ai-state-machine.md` called `0x8004DF18` chaser-AI, contradicting the note's own 2026-07-03 correction + sym (`camera_follow_update`, `0x80095358`=camera). | auto-memory vs sym | a3: corrected both blurbs + added a top banner; live re-derivation blocked by the from-boot-movie limitation ([[EXP_2026-07-09_identity_reconciliation]]) so the **real chaser driver is flagged an OPEN residual** | **resolved** (residual logged) |
| AUDIT-16 | medium | `0x8005b134` "superseded_claim" vs sym `respawn_transition_state_handler`; `0x80060724` `libgte_transform_leaf_bank` vs `RotAverage4`; `0x8004d698` `setpiece_spawn_refs` vs `setpiece_spawn_manager`; +11 src_re↔sym drifts. | sym vs notes/src_re | a3: renamed all 3 notes to sym; **src_re name drift → a4** | **partial** (notes done) |
| AUDIT-17 | medium | Duplicate `0x8007403C` notes: bare `FUNC_8007403C.md` (byte-matched) + `FUNC_8007403C_consume_flag_37.md` (semantic). | dup_address | a3: merged the byte-match evidence/src_path into `consume_flag_37`, deleted the bare note | **resolved** |

## Theme E — symbol/census undercount (metadata drift)

| id | severity | finding | evidence | fix | status |
|----|----------|---------|----------|-----|--------|
| AUDIT-18 | medium | 10 shipping `src/main` C fns + 2 named asm fns absent from `re_symbols.sym` → census listed them `unknown`. | src/main vs sym | a4: `apply_symbol_names.py analysis/naming/rca_a4_batch.json` (12 names, tier inferred, 873→885); regen census + naming_priority | **resolved** (unknown 495→483) |
| AUDIT-19 | low | 5 src_re-documented fns have no sym entry. | src_re vs sym | a4: only `0x800B7DA0` is a resident start (and it's an overlay fn); the other 4 (`8003B280,80047170,80054288,80054554,8001DEA0`) are **mid-function/overlay non-starts** → NOT resident-nameable (would violate the start-requirement). Correctly left unnamed. | **resolved** (wontfix, documented) |
| AUDIT-20 | low | `naming_priority.md` and `.json` disagreed on the dynamic count. | naming_priority tool | a4: root cause = the tool labeled the **inferred-tier** count (dynamic + call-graph-connected) as "runtime-covered (dynamic)"; fixed `naming_priority.py` so md + json both report the same `dynamic_covered`, with the tier breakdown shown separately | **resolved** (tool fixed) |
| AUDIT-21 | high | 14 src_re pseudocode notes describe functions now byte-matched in `asm/hand_written/*.s` but don't say so — campaign may redo solved work. | src_re vs segments.yml | a4: stamped all 14 with a "SUPERSEDED for build — byte-matched as asm/hand_written/<x>.s" header banner | **resolved** |

## Theme F — census calls data "code" (metadata drift)

| id | severity | finding | evidence | fix | status |
|----|----------|---------|----------|-----|--------|
| AUDIT-22 | high | `0x80078D84` (golddrop's cave *gap*, NOT the streaming table `0x8007EFE8`) was `code` in `functions.json` + `memory_map`; `0x80082030` (forbidden) sat inside the `runtime_gp` span. | functions.json | a5: added `0x80078D84` to census `DATA_ANCHORS` (carved from the code span — golddrop's proven cave confirms it's not live code); `0x80082030` covered by the tail reclassification | **resolved** |
| AUDIT-23 | high | 14 resident gp/BSS globals typed `range_type:code` (`runtime_gp, G_DAT_ENTRY_COUNTER, master_game_state, current_scene_id, G_PASS3_BASE_PTR…`) — a modder could treat live globals as free code. | functions.json | a5: census reclassifies the resident tail `[0x80081D98,TEXT_HI)` → `range_type:data`/`class:data` (resident code count 1033→1019); `build_memory_map` skips census data rows so they paint `named_global`/`data` (`0x80081d98`→named_global). Invariants hold; suite green | **resolved** |

## Theme G — build / index artifacts (metadata drift)

| id | severity | finding | evidence | fix | status |
|----|----------|---------|----------|-----|--------|
| AUDIT-24 | medium | `config/segments.yml:55` vs `:170` **duplicate `__status` mapping** (asm + C for `0x80063d70`); metric correct only by dedup accident. | segments.yml | a6: removed the asm line (kept C); `validate_build.py` **PASS** SHA-1 `af43de22…`; decomp_progress unchanged (245/166/79) | **resolved** |
| AUDIT-25 | high | `Address Index.md` listed **50 of 149** notes; header counts stale (761 syms/1170 resident). | Address Index.md | a6: new `tools/gen_address_index.py` regenerates from all Canon notes — **176 rows**, accurate header (1019 resident, 885 syms); all links resolve | **resolved** |
| AUDIT-26 | high | `HOOK_forbidden_patch_ranges.md` listed **3 of 6** forbidden ranges; **`0x8007F130` undocumented in Canon**. | registry vs Canon | a6: completed the note to all 6 enforced ranges incl. `0x8007F130` | **resolved** |
| AUDIT-27 | medium | `registry.py` docstring names crash-hazards **not enforced** in `FORBIDDEN_CODE_RANGES`: `0x800B4A30, 0x80081858, 0x80081CF0, 0x800821FC, 0x8007FBC8, 0x8007FD58`. | registry.py | a6: annotated them in the HOOK note as event-transient hazards caught by the MSM runtime write-watch gate (not the static floor), with rationale + [[SYS_modding_safety]] link (safer than guessing static extents) | **resolved** |
| AUDIT-28 | low | `memory_map` ↔ sym asymmetry (`runtime_gp`, `contact_record_array`). | memory_map.json vs sym | a6: already consistent — `contact_record_array` is in both (sym + `bss_named_globals`); `runtime_gp` is a **file-tail** global painted a `named_global` region (by design not in the post-FILE_END BSS list). Original finding was a snapshot/key misread | **resolved** (no change needed) |

---

## Residual / ongoing (content work, not mechanical remediation)
These are tracked, not silently dropped. The lint ratchet holds them from growing.
- **RES-1 — archive-routed links: resolved 2026-08-19 (190 → 0).** Consolidated API and fixture names now
  resolve through explicit live indexes; migrated Memory names are aliases on their primary Canon notes;
  obsolete plans and blocker links were retargeted per occurrence to current evidence/status pages. Intentional
  wrong-hypothesis history uses an explicit Markdown path into Archive rather than a wikilink that can silently
  resolve to superseded material. The ratchet ceiling is now zero.
- **RES-2 — 126 legacy `Canon/Systems` imports (AUDIT-09).** Committed with `legacy_import_needs_curation`.
  Topical merge each into the relevant `SYS_` note (or re-home `Asset_`/`Finding_` to the right Canon area),
  then clear the status. This is RE reading/judgement per note, not a scripted move.

## Remediation phases (see plan RCA)
a0 register+linter (this note) · a1 aliases/links (B) · a2 evidence (C) · a3 identities (D, DuckStation-verified) ·
a4 symbol/census (E) · a5 data/code census (F) · a6 build/index (G) · a7 migration (A) · a8 verify+commit. **a0–a7 done.**

Related: [[SYS_function_census]] · [[SYS_modding_safety]] · [[DuckStation_API_Index]] · `tools/validate_vault.py`.
