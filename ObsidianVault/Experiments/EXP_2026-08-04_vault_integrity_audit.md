---
kind: experiment
id: EXP_2026-08-04_vault_integrity_audit
name: Vault integrity audit - Canon and mechanics registry
created: 2026-08-04
updated: 2026-08-04
status: complete
confidence: high
source_state: evidence
artifacts:
  - tools/validate_vault.py
  - tools/phase4_d02_actor20_semantic_guard.c
  - tools/phase4_e16_table_lifetime_guard.c
  - tools/phase4_player_state_writer_pins.c
  - tools/phase4_power_slot_writer_guard.c
  - tools/phase4_e16_marker20_guard.c
  - tools/phase4_integrity_scope_guard.c
---

# Vault integrity audit - Canon and mechanics registry

## Purpose

This note banks the 2026-08-04 integrity audit of `ObsidianVault/` and
`analysis/mechanics_baseline.yaml`. It is an audit of repository claims, not new
original-game Canon. Static facts were re-derived from the hash-verified pristine
`REBUILD/files/SCUS_942.88` and named overlay blobs. Existing runtime observations
remain a separate evidence tier and were not upgraded to static closure or trace
evidence.

The sorting rule was: if a command can return the answer, re-derive and resolve it.
Interpretation, missing runtime observations, and status-policy choices remain explicit
decisions.

Related prior campaign: [[Consistency Audit]].

## Scope and termination

- Canon audit: **784/784 pages**.
- Mechanical sweep: **1,075 live Markdown pages**, excluding `Archive/`.
- Registry priority set: **97/97 rows** whose status was `partial` or `bounded`.
- Recent Experiment priority set: **123 notes** from the preceding 14 days.
- Other live material: sampled after the priority sets.
- Stop reason: **Canon was completely audited**. The 25-finding threshold was also
  exceeded, but this note does not imply a complete semantic audit of all non-Canon
  pages.

Line references below identify the 2026-08-04 shared-worktree snapshot. References in
files already modified or untracked by another operator may move when that work lands.

## Phase 0 mechanical inventory

| sweep | count | disposition |
|---|---:|---|
| Repeated `##` headings | 1 group on 1 page; 1 surplus section | Still present in an operator-owned untracked page |
| Retraction markers | 477 marker occurrences on 454 lines in 145 files | High-risk live restatements are listed below |
| Bounded numeric phrases | 103 occurrences on 95 lines in 26 files | Canon closure/count claims were re-derived; remaining candidates stay enumerated |
| Orphans | 399 pages | 315 Canon, 54 Experiments; 305 are Canon Function census pages |
| Under-15-line asserting stubs | 2 pages | `SYS_mushroom_trampoline.md` and `Sessions/2026/README.md` |
| Dead `evidence:` / `src_paths:` references | 3 references on 3 pages | All 3 repaired |
| Dangling wikilinks | 2 | 1 repaired; 1 remains in an operator-owned page |
| Live-to-Archive wikilinks | 189 occurrences to 72 targets | Each needs a current target or explicit provenance justification |
| Link target ID differs from filename | 751 occurrences to 171 destinations | Mostly the established address-ID/descriptive-filename convention; not automatically broken |
| Unlinked literal citations | 2,962 occurrences on 2,546 lines in 850 pages | Candidate population, not automatically a defect |

The post-fix validator result was: `dangling_links=1`, `archive_only=189`,
`evidence_policy=6`, `evidence_deadfile=0`, `dup_address=2`, `missing_alias=1`, and
`schema=12`. The duplicate-address and schema findings were caused by concurrent
untracked Canon Function pages and were not edited by this audit.

## Findings

`OWNER` means the fact is settled but the file was already modified or untracked by
another operator. Those items are propagation work, not interpretation escalations.

| file:line | class | prior/live claim | artifact-supported result | action |
|---|---|---|---|---|
| `analysis/mechanics_baseline.yaml:1714` | CONTRADICTION | RGB scale constant `0x84218421` | Instructions at `0x8003AE14/0x8003AE24` form `0x84210843` | OWNER: replace and retain correction history |
| `ObsidianVault/Experiments/EXP_2026-08-04_phase4_e16_chunk_roles.md:141` | RETRACTED-ALIVE | Repeats the wrong scale constant | `0x84210843` | OWNER: propagate correction |
| `analysis/mechanics_baseline.yaml:1715` | COUNT | All 74 chunks are images; 57 remain unpinned | 63/74 confirmed images; 11 marker-`0x26` roles remain open | OWNER: strike live restatement |
| `analysis/mechanics_baseline.yaml:1800` | STALE | Lifetimes and ownership untouched | Registered-table lifetime and all 46 consumer formats are answered | OWNER: rewrite `next` |
| `ObsidianVault/Canon/Functions/FUNC_80048138_player_vertical_update.md:130` | RETRACTED-ALIVE | Approximate PCs are stores in a collision callee and the path is globally sole | Stores are `0x80036CB8/0x80036CC0` in the integrator; global exclusivity remains open | OWNER: propagate exact chain |
| `ObsidianVault/Experiments/EXP_2026-08-03_phase4_a03_jump.md:76` | OVER-CLAIM | Integrator is the sole producer of grounded `0x0101` | The exact player-call producer is proven; pointer/indirect residual remains | OWNER: scope wording |
| `analysis/mechanics_baseline.yaml:61` | STALE | Variable height, landing, and timing are all missing | Timing and apex law are measured; ledge/ceiling controls and guard integration remain | OWNER: refresh `missing` and `next` |
| `ObsidianVault/Canon/Memory/MEM_800A6500_Player_state_800A6500.md:81` | COUNT | Power slot has 7 writers / 5 readers, complete | 7 resolved direct writers / 7 readers, with residual retained | OWNER: replace stale count |
| `ObsidianVault/Canon/Memory/MEM_800A6500_Player_state_800A6500.md:84` | COUNT | Health has exactly 4 writers | 6 statically resolved writers; global closure is not claimed | OWNER: replace stale count |
| `analysis/mechanics_baseline.yaml:447` | RETRACTED-ALIVE | `0x8004AFB0` proves a power-slot access; later text says health has 4 writers | Store effective address is player+`0x82`; health has 6 resolved writers | OWNER: propagate both corrections |
| `analysis/mechanics_baseline.yaml:2120` | OVER-CLAIM | F16 counter domain closed across EXE and overlays | One read, one increment, and six clears are resolved; pointer residual remains | OWNER: scope to resolved sites |
| `analysis/mechanics_baseline.yaml:2128` | OVER-CLAIM | Bonus overlay completely accounted; global negatives and no position reward | Partition is structural, indirect flow remains, and runtime did not sample position | OWNER: use bounded Canon wording |
| `analysis/mechanics_baseline.yaml:2151` | OVER-CLAIM | F17's 16 stores and five progress writers close their domains | Those fixed-form sites are resolved, not pointer closure | OWNER: retain residual |
| `analysis/mechanics_baseline.yaml:2177` | OVER-CLAIM | F18 chain and progress domains are closed globally | One read/five writes are resolved; aliases remain | OWNER: scope wording |
| `ObsidianVault/Experiments/EXP_2026-08-04_phase4_f02_debris_damage_class.md:92` | RETRACTED-ALIVE | `record+0x33` has exactly two post-creation writers and can never change | Two sites are currently resolved; the census is not globally complete | OWNER: propagate Canon correction |
| `ObsidianVault/Canon/Systems/SYS_registered_chunk_image_resources.md:200` | OVER-CLAIM | A local-`lui` scan bounded all deliberate table pointers | It closes one encoding only | RESOLVED in `2341abad264f` |
| `ObsidianVault/Canon/Systems/SYS_bonus_stage.md:48` | CONTRADICTION | Bonus overlay is the only game image reading the ordinal | Resident EXE reads/writes it at `0x8004FFAC/0x8004FFD0` | RESOLVED in `2341abad264f` |
| `ObsidianVault/Canon/Systems/SYS_bonus_stage.md:80` | OVER-CLAIM | No timer/score/fail/enemy condition anywhere in the overlay | Negative is established only for the decoded completion path | RESOLVED in `2341abad264f` |
| `ObsidianVault/Canon/Systems/SYS_bonus_stage.md:171` | OVER-CLAIM | Nothing else is paid; no store in the whole overlay | Fixed-form scan plus five sampled runtime fields; position was not sampled | RESOLVED in `2341abad264f` |
| `ObsidianVault/Canon/Systems/SYS_fmv_player_streaming.md:82` | OVER-CLAIM | Four sites fully resolve the overlay and flag domain `{0,1}` | Four direct sites; 2,580 FMV unresolved-base accesses remain | RESOLVED in `2341abad264f` |
| `ObsidianVault/Canon/Systems/SYS_clover_forest_objective.md:79` | OVER-CLAIM | Overlay-local address is closed globally | Direct sets are pinned; resident and overlay pointer residual remains | RESOLVED in `2341abad264f` |
| `ObsidianVault/Canon/Functions/FUNC_800313A8_collision_grid_builder.md:60` | COUNT | Only writer; 14 other materialisations | One resolved writer; 14 fixed-form sites total means 13 others | RESOLVED in `2341abad264f` |
| `ObsidianVault/Canon/Systems/SYS_enemy_contact_damage.md:91,97` | DUPLICATE | Identical H2 and body appears twice | One section is surplus | OWNER: untracked page |
| `ObsidianVault/Experiments/EXP_2026-08-03_phase4_a18_pause.md:163` | LINK | Links to nonexistent experiment ID | No live target resolves | OWNER: untracked page |
| `ObsidianVault/Mods/Blackberry/MOD_blackberry_net_new_berry.md:33`; Gold Berry page line 23; HUD page line 13 | LINK | Frontmatter named three nonexistent evidence files | Historical evidence moved under `Archive/Superseded/` | RESOLVED with explicit provenance in `efeaf935404d` |
| `ObsidianVault/Canon/Functions/FUNC_8001DFE4_scene-geometry_draw_dispatcher.md:26` and 188 peers | LINK | Link resolves only into Archive | Needs current target or explicit historical justification | OPEN curation set: 189 links / 72 targets |
| `ObsidianVault/Canon/Functions/FUNC_80014504_build_render_survivor_list.md:1` and 398 peers | ORPHAN | No live inbound wikilink | 305 are function census pages; ownership/index policy is unclear | OPEN indexing/policy set |

## Resolved against the artifacts

### Actor record `+0x20`

Commit `52b9b6506bb9` corrects the former unnamed-field conclusion. The field is signed
vertical velocity. `tools/phase4_d02_actor20_semantic_guard.c` pins the pristine
instructions, and `tests/test_phase4_d02_actor20.py` forbids the old unqualified reading.

### Registered-table lifetime

Commit `db95a3fe81ef` proves that the `0x8009B4E8` table is cleared once by the startup
loop at `0x8005F690..0x8005F6B0`, not by each load. The surviving result is that no
per-load reset clears it. `tools/phase4_e16_table_lifetime_guard.c` pins the answer.

### Player action-state writer count

Commit `1d98c83d97a5` records 19 resolved direct writers and 8 readers. The sole resolved
value-3 writer is `0x80048CFC`. The closure boundary and negative wording are guarded by
`tools/phase4_player_state_writer_pins.c` and
`tests/test_phase4_player_state_writer_map.py`.

### Power slot, health, and results rendering

Commit `48c0dcacbf85` establishes:

- Power slot `0x800A657E`: 7 resolved direct resident writers and 7 readers.
- `0x8004AFB0` writes player+`0x82`, not player+`0x7E`.
- True health is `0x800A6594`, with 6 statically resolved writers.
- Damage decrement is `0x8004A888`; the alive-check branch is `0x8004F0E0`.
- `0x8004F0E8` is a call instruction, not the branch.
- Reward-marker bits select GPU ABE/semitransparency; they do not tint RGB.

The compiled guard is `tools/phase4_power_slot_writer_guard.c`. Negative content guards
prevent the former address, count, branch, and tint readings from returning live.

### LEVEL.RAW marker `0x20`

Commit `e4ed13839c91` is the most valuable contradiction in this pass because both Canon
and the JSON evidence were wrong. The pristine words at `0x8003AE14/0x8003AE24` form
`0x84210843`, not `0x84218421`. The settled resource count is 63/74 confirmed images:
17 marker-`0x20` sky/backdrops plus 46 registered frontend images. Eleven marker-`0x26`
roles remain open. `tools/phase4_e16_marker20_guard.c` pins 11 instructions and the
stores into the sky-color cache.

### Link and frontmatter repairs

Commit `efeaf935404d` repairs three dead frontmatter evidence paths and the dangling
`[[A10_handstand]]` link. The wrong paths remain described as former locations, and the
Archive provenance is explicitly justified. `tests/test_audit_link_hygiene.py` asserts
that the dead paths and dangling target cannot return.

### Closure and scope corrections

Commit `2341abad264f` adds `tools/phase4_integrity_scope_guard.c` with 49 pristine
instruction pins plus general census artifacts. It establishes or narrows:

- Grounded `0x0101` is written by bytes `{1,1}` at `0x80036CB8` and the
  `0x80036CC0` delay slot. The former PCs are a load, jump, and branch.
- Bonus ordinal has a resident read at `0x8004FFAC` and write at `0x8004FFD0`.
- Arena limit has one resolved direct writer and two readers. There are 14 total
  fixed-form materialisations, hence 13 others, with pointer residual retained.
- Contact `record+0x33` has two currently resolved post-construction stores, not a
  globally exact two-writer domain.
- FMV has four resolved direct accesses but 2,580 unresolved-base FMV accesses.
- Clover's direct sets are pinned, but overlay reuse and pointer residual prevent
  global closure.
- F16/F17/F18 counter and chain pages now distinguish resolved direct sites from
  pointer closure.
- Bonus-stage structural partition, completion-path negatives, and reward sampling
  are each limited to the method that produced them.

## Settled factual propagation backlog

These are command-answerable and should be corrected when their current owners finish.
They are not `NEEDS A DECISION` items.

1. Replace `0x84218421` with `0x84210843` in
   `analysis/mechanics_baseline.yaml:1714` and the E16 chunk-role Experiment. Preserve
   the old constant as correction history.
2. Replace the live all-74/57-unpinned claims at registry lines 1715 and 1800 with
   63/74 confirmed images and 11 unresolved marker-`0x26` roles. Registered consumers
   and table lifetime are already answered.
3. Propagate the exact grounded caller/store chain and retained census residual into
   `FUNC_80048138_player_vertical_update.md` and the A03 Experiment.
4. Correct `MEM_800A6500_Player_state_800A6500.md` to 7/7 resolved direct power-slot
   accesses and 6 resolved health writers.
5. Remove `0x8004AFB0` as power-slot evidence and the four-health-writer claim from the
   registry. The artifact pins already settle both.
6. Replace F16/F17/F18 global closure language with the bounded wording already in
   Canon. Preserve each old closure statement as correction history.
7. Replace F02's globally exact two-writer/contact-never-changes claim with the two
   currently resolved sites and explicit residual.
8. Deduplicate `SYS_enemy_contact_damage.md` and repair the pause Experiment's dangling
   link after their untracked owners finish.

## Needs a decision

Only interpretation, runtime-observation, and status-policy questions belong here.

1. **Grounded naming.** The raw set condition is
   `a3 != 2 && (s0 == 1 || a3 == 1)`. A pristine landing observation supports the
   name "ground contact", but static code alone does not prove that every matching raw
   collision result has that semantic meaning.
2. **F16/F17/F18 row status.** The rows remain `partial` while `missing` says the stage
   itself is answered. Variants 1 and 2 are statically pinned but only variant 0 was
   observed running. Decide whether that supports the current status, `bounded`, or a
   different registry state.
3. **Audio status taxonomy.** `SYS_audio_music.md` says `status: static_seen`, while its
   body records in-game confirmation. Changing frontmatter requires a policy decision
   about whether partial runtime confirmation upgrades a system page.
4. **Archive link policy.** For each of the 189 live-to-Archive links, choose a current
   Canon replacement or retain the Archive target with explicit historical provenance.
5. **Orphan policy.** Decide whether generated Function census pages must have topical
   inbound links, may be reachable only through a generated address index, or should be
   explicitly marked as intentional leaves.

## Verification

- `python tools/build_identity.py --verify`: **327/327 PASS**.
- Audit-focused pytest selection: **157 passed**.
- Broader selected run: **320 passed, 1 failed**.
- The sole broader failure was outside the audit commits:
  `tests/test_phase4_c05_three_tokens.py::test_c04_correction_is_explicit_in_both_artifacts`
  failed because the concurrently modified `analysis/phase4_c04_enemy_token.json`
  lacked `CORRECTION_2026-08-03_level01_quota_was_wrong`.
- `git diff --check` passed for every audit path.
- None of the seven audit commits' paths overlapped the tracked dirty set after commit.
- No poll-only fixture was represented as traced. No static result was upgraded to a
  runtime observation.

## Commit ledger

| commit | defect class | summary |
|---|---|---|
| `52b9b6506bb9` | CONTRADICTION | Resolve actor `+0x20` semantics |
| `db95a3fe81ef` | CONTRADICTION | Correct registered-table lifetime retraction |
| `1d98c83d97a5` | COUNT / OVER-CLAIM | Scope player action-state writer count |
| `48c0dcacbf85` | RETRACTED-ALIVE / COUNT | Remove live restatements of corrected facts |
| `e4ed13839c91` | CONTRADICTION / COUNT | Pin LEVEL.RAW marker `0x20` facts |
| `efeaf935404d` | LINK | Repair live evidence links and dead frontmatter paths |
| `2341abad264f` | OVER-CLAIM | Scope closure claims to their actual methods |

Audit commit range: `52b9b6506bb9^..2341abad264f`.

## Reproduction

Run the immutable-image identity check first:

```bash
python tools/build_identity.py --verify
```

Run the durable artifact and negative-content guards:

```bash
pytest -q \
  tests/test_phase4_d02_actor20.py \
  tests/test_phase4_e16_registered_chunks.py \
  tests/test_phase4_player_state_writer_map.py \
  tests/test_phase4_b06_b08_power_slot.py \
  tests/test_phase4_e16_chunk_census.py \
  tests/test_audit_link_hygiene.py \
  tests/test_phase4_integrity_scope_guard.py \
  tests/test_phase4_grounded_flag_scope.py
```

Re-run current vault validation:

```bash
python tools/validate_vault.py --check
```

Inspect exactly what the audit committed without staging shared work:

```bash
git log --oneline 52b9b6506bb9^..2341abad264f
git diff --stat 52b9b6506bb9^..2341abad264f
```

## Consumption rule

Use the corrected Canon pages and compiled pins for factual claims. Treat the registry
and owner-held propagation files listed above as stale until their corrections land.
Do not infer closure from a resolved-site count: every page must carry the residual and
method scope that produced that count.
