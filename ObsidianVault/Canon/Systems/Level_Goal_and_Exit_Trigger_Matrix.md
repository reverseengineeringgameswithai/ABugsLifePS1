---
kind: system
id: Level_Goal_and_Exit_Trigger_Matrix
created: 2026-07-08
updated: 2026-07-08
status: legacy_import_needs_curation
confidence: medium
source_state: original_game_or_mixed_legacy_note
legacy_source: ObsidianVault/Systems/Level Goal and Exit Trigger Matrix.md
aliases:
  - "Level Goal and Exit Trigger Matrix"
archived_source: ObsidianVault/Archive/Superseded/Systems_Level_Goal_and_Exit_Trigger_Matrix.md
patch_policy: unknown
---

# Level_Goal_and_Exit_Trigger_Matrix

## Canon Status

This page was created during the 2026-07-08 migration completion pass from `ObsidianVault/Systems/Level Goal and Exit Trigger Matrix.md`. It is a structured Canon landing page for search/linking, but the archived source remains the provenance copy. Treat specific claims as Canon only when they are supported by the evidence links, C source, or stronger curated pages.

- Legacy title: Level Goal and Exit Trigger Matrix
- Archived full source: `ObsidianVault/Archive/Superseded/Systems_Level_Goal_and_Exit_Trigger_Matrix.md`
- Migration action: `convert_to_canon`
- Migration confidence: `medium`
- Migration reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

## Legacy Heading Index

- `# Level Goal and Exit Trigger Matrix`
- `## Evidence Boundary`
- `## Region-Code Semantics`
- `## Save-State Trigger Matrix`
- `## Interpretation`
- `## Objective Scope Refinement`
- `## Be-Here Live Route Proof`
- `## Residual RCG-003 Work`
- `## Tool Output`

## Archived Source

The full legacy note is preserved at `ObsidianVault/Archive/Superseded/Systems_Level_Goal_and_Exit_Trigger_Matrix.md`. It is intentionally not copied into this Canon landing page, so stale or superseded claims do not pollute Canon search results.

## Unfiltered closure of the enumeration residual (E02, 2026-08-03)

The matrix's own residual — "the RAM catalog only sees codes 1..4 under
plausibility rules" — is closed: an unfiltered census keyed on the loader's
count global `[0x800822A0]` over all 16 anchors proves the campaign domain is
exactly {0,1,2,3,4} and reproduces every catalog row byte-for-byte. New
binding facts: **code 3's dispatch body is identical to code 2's** (so the
catalog's LEVEL02/04/05 be-here proofs live-prove code 3, and LEVEL01/14
prove code 2); **code 4 suppresses checkpoint saving** (checkpoint_save
0x80054C90 bails); code 1 additionally retires mover-updated objects
(+0x6E=0). See [[EXP_2026-08-03_phase4_e02_region_codes]] ·
`analysis/phase4_e02_region_code_census.json`.

## Region-code dispatch, fully decoded (F01, 2026-08-05)

The legacy `## Region-Code Semantics` table is superseded. All five arms of the
dispatch inside `player_vertical_update` are now pinned as exact instruction
words, with the branch targets decoded from the asserted words
(`tools/phase4_f01_objective_lifecycle.c`, 83 assertions, exit 0):

| code | target | effect |
|---:|---|---|
| 0 | — | skipped at `0x80049650` |
| 1 | `0x800496A8` | `player_damage_handler(0, 0, sp+0x2c, a3=1)`; sets commit flag `sp+0x50` |
| 2 | `0x800496C4` | request←`1`, timer←`23`, SFX `58`; sets commit flag `sp+0x50` |
| 3 | `0x800496E8` | request←`1`, timer←`23`, SFX `58`; **no** commit flag |
| 4 | `0x80049718` | if `player+0x7e == 0 && player+0x92 == 0`: `player_damage_handler(0, 0, sp+0x2c, a3=0)` |
| other | `0x80049748` | join, no effect |

⚠️ **Correction.** The legacy table read code 1 as "calls `FUNC_8004A700` type-2
transition path". `FUNC_8004A700` is the **player damage handler**; its `a3` is a
selector (`0x8004A720` → `s4`, tested `bnez` at `0x8004A73C`), not a destination.
Codes 1 and 4 are **hazard regions**, and the transition is a consequence
*inside* the handler rather than the arm's own effect.

**Refinement 2026-08-10 — `a3` is not a boolean, and the two paths differ in
kind.** `FUNC_8004A700` holds **two** stores of `[0x800823A0]`, and which one
runs is decided by `a3` alone:

| `a3` | path | request 2 store | fade | health |
|---:|---|---|---:|---|
| `0` (code 4, goo) | falls through `0x8004A740`: knockback, i-frame check `0x800A6592`, health `−1` at `0x8004A880` | `0x8004A8B4`, **conditional** on health going negative (`0x8004A890 bgez`) | `60` | decremented |
| `≠0` (code 1, pits) | branches `0x8004A828` → `0x8004A90C` → `0x8004A998` → `0x8004A9E8` | `0x8004A9F4`, **unconditional** — no health test on the path | `23` | untouched |

So a pit is **instant death by construction**, not by draining health: the
`a3≠0` path skips the knockback and the invincibility check entirely and stores
the request outright. This is the static proof of what the 2026-08-10 E10
re-sweep observed at runtime (code 1 → request 2, code 4 → no request). `a3`
further discriminates death *style* further down (`s4` compared against `3` at
`0x8004A998` and `2` at `0x8004A9B8`, selecting SFX `0x49` and power-word bits),
so it is a small enum, not a flag.

**Refinement of E02's "code 3's dispatch body is identical to code 2's":**
identical *except one store*. The commit flag `sp+0x50` is zero-initialised at
`0x800481BC` and set only by the code-1 and code-2 arms. At the join
(`0x80049748`), a set flag re-commits position from the previous-position mirror
and **clears `player+0x82`**. So code 2 drops Flik out of the grounded state on
the frame it fires and code 3 does not.

**The whole dispatch is gated on GROUNDED.** `FUNC_80038F38` returns `0` unless
the low byte of `player+0x82` is `1` (`0x0101` grounded / `0` airborne). Its
producer is the movement integrator `FUNC_8003633C` (`0x80036CB8`/`0x80036CC0`),
which also owns the current-sector slot `0x80090560 + index*20`
(`0x80036C00`/`0x80036C04`/`0x80036C14`). **No region code has any effect while
Flik is airborne**, and the re-entry guard at `0x8004965C` makes every region
trigger single-shot per scene.

See [[EXP_2026-08-05_phase4_f01_objective_lifecycle]] ·
`analysis/phase4_f01_objective_lifecycle.json` ·
`analysis/phase4_f01_runtime_lifecycle.json`.

## Where every region code physically is, on disc (F01 item 2, 2026-08-10)

The runtime census proved the campaign domain is `{0,1,2,3,4}` but cross-checked
the **disc** side for LEVEL01 only. `tools/phase4_e02_disc_region_code_census.py`
→ `analysis/phase4_e02_disc_region_code_census.json` closes that: per scene it
re-locates the authored sector array in its own container (binding from E02's
collision round trip) and reads `src+0x2C` from the container bytes.

**16/16 scenes located · 3,235 authored sectors compared · 0 disagreements**
with the runtime table's `+0x2E`. The 720 runtime-registered tail sectors carry
no nonzero code, so the authored prefix is the entire code population.

⚠️ **The array's (chunk, offset) is PER LEVEL** — the chunk index alone ranges
over 27–33, and four scenes hold the array in a flat `.ALL` container. LEVEL01's
`(32, 0x36570)` was hardcoded in `tools/edit_sector_region_code.py` until
2026-08-10, so every other level printed **nothing**; that silence was a tooling
artifact and never evidence of absence. The tool now resolves the location from
the census and errors out on an unknown container.

| code | meaning | sectors | where |
|---:|---|---:|---|
| 1 | pit — instant death (`a3≠0`, request 2, fade 23) | 15 | scene 3 ×9, scene 10 ×5, scene 4 ×1 |
| 2 | exit, commits position | 2 | scene 1 (s177), scene 8 (s334) |
| 3 | exit, does **not** commit position | 4 | scene 17 (s24), scene 3 (s579), scene 6 (s131), scene 10 (s297) |
| 4 | goo — damage only, suppresses checkpoint | 6 | scene 4, s220–225 |

⚡ **Code 3 is not dead code.** It is the ordinary exit trigger of training,
tunnels, cliffside canyon and riverbed run.

⚠️ **CORRECTION 2026-08-10 (same day):** I first wrote that code 3 "had never been
*observed* firing". **That was wrong** — over-generalised from the F01/E10 exec-watch
sweep, which watched the arm entry `0x800496E8`, to the corpus as a whole. The 100%
corpus write-watch sweep **did** observe it: `analysis/phase4_f01_campaign_breadth.json`
records writer PCs `0x800496DC` **and `0x800496FC`** for request value 1, and those pair
with the two exit arms' stores at `0x800496D8` (code 2) and **`0x800496F8` (code 3)** —
store PC + 4, the write-watch reporting convention, confirmed by the fact that neither
reported PC is itself a store. So the code-3 arm is **live at runtime**, not merely
present in terrain.

Scope of what that does and does not establish: the *store* in the code-3 arm was
observed writing request 1. A direct exec hit on the arm entry `0x800496E8` has still
not been recorded, and the sweep's `by_value` block does not break writers down per
level, so **which** levels drove it is not established here.

**Repair update, 2026-08-10:** the exact 19-level corpus was rerun from a fresh
detached checkout with the submitted fail-closed producer. All 19 replays completed
and reproduced; 35/35 transition decisions self-certified the pristine decision
instruction and the finalizer law, with 19 calls, 16 skips, and zero failures.
That closes the bounded corpus assertion and regeneration work, but not campaign
completeness: the independent applicability matrix and eight-type provenance map
remain NOT DONE. See [[EXP_2026-08-10_phase4_f01_oracle_breadth_repair]].

**Structural law, true in all 7 code-bearing scenes:** nonzero codes occupy a
single contiguous band at or near the END of the authored array — hazard and
exit sectors are appended after the terrain proper.

**Universe:** scene ids are valid `1..17` (`0x8003CF84`); the progression table
`0x80077FA0` lists 16 and the census covers those **16 of 17**. Scene **16** is
uncovered — absent from the table, reachable only via the force flag
`[0x8008225C]` (map/results), and it has no save anchor.
