# Next-session prompt — ABL Phase 4 / F01

Paste this into a fresh Claude session. Everything referenced is committed.

---

## Orientation (read these first, in order)

1. `ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - F01 Closure Roadmap.md`
   — all nine DoD dimensions, current state, method, ordering. **This is the map.**
2. `ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md`
   — the append-only campaign log; the 2026-08-10 sections are the newest work.
3. `analysis/mechanics_baseline.yaml` → row `F01_anthill` → `dod_scorecard`
   — authoritative status. Re-read before trusting any summary, including this one.

## Where things stand (2026-08-10, end of day)

- **F01: 4 of 9 met, MEASURED (2026-08-11).** `durable_evidence`,
  `original_oracle`, `complete_frontier`, `lifecycle` — each promoted by an
  independent fresh detached verifier (registry commits 76273fd0, eb42bea6);
  lifecycle was first REJECTED over the +4 writer-PC convention, repaired with a
  compiled-C attribution probe, and re-adjudicated MET. Highest measured row in
  the campaign. Still verifier-owned: do not edit `analysis/mechanics_baseline.yaml`.
- ✅ **Roadmap §0 is CLEARED and stable** — `phase4_closure_debt.py --write`
  returns `PASS: rows=16/107 dimension_met=149` on consecutive runs (`3d74f34`).
  It broke twice today; the second break was self-inflicted by a fixture re-pin.
  Re-pin only at a proven fixed point, and note the tool needs `--write`.
- ❌ **`complete_frontier` is spent** — five avenues, all NO-GO, all four D3
  walls technique-shaped but funded only behind a NEW prerequisite engine.
  1,246 unresolved indirect occurrences (corrected from my double-counted 2,340).
- 🔴 **`original_oracle`: one recording away.** Adjudicated NOT MET on three
  elements; two repaired. The blocker is a **cold-boot movie in which Flik dies
  naturally** — D18_thud_fight and E02_FreshLoad_Clover were both replayed in
  full and neither contains a death, so the cheap path is ruled out.
- ❌ **`campaign_breadth`: reframed, not nearly done.** The branch law asserts
  clean (19/19 levels, 35 decisions, 0 failures, both skip edges, verified
  detached) but the dimension needs a **pre-outcome applicability matrix** and an
  **independently sourced eight-type taxonomy**. Design work.
- ⚠️ The scorecard *note* is stale in three places (it still says "no ABI
  ledger", "LEVEL01 only", and describes the injected oracle). Judge dimensions
  against artifacts, not the note. Deliberately not edited — registry is
  verifier-owned.

## Task 1 — verify Codex's D3 report: ✅ LANDED, VERIFIED, ACCEPTED

Codex's hard-truth verification accepted candidate `619cac8d604f5` with no gaps
and no required inputs — 327/327 pristine identities, 34/34 focused tests,
byte-identical post-commit extent audit, zero new extent findings, no live
replay and no forbidden artifact or status change. Acceptance banked at
`1e887011c19ab`. **F01 stays `partial`; item 2 stays `not_met`.**

Nothing pending. Keep the pattern below for the next pilot verification:
- Confirm **freeze-before-outcomes** by commit ancestry (the freeze commit must
  precede results and contain no outcome fields). All four prior pilots honoured
  this; check, don't assume.
- **Independently re-derive at least one landed claim from the image bytes.**
  This has caught real errors twice: the `$ra` structure finding, and the
  0x80018CBC domain that runtime falsified.
- Check the forbidden-path list (frontier/census/seed/gate/typed-state artifacts).
- Compare reported fractions against the artifact — a 3.7% match was once
  reported as an "exact near-miss".
- If NO-GO: the per-contract **technique-shaped vs structure-shaped** labels are
  the deliverable. Structure-shaped across all four means `complete_frontier`
  is finished and the operator's item-2 bar ruling is the only path left.

## Task 2 — region-code census: ✅ DONE 2026-08-10

⚠️ This was the task queue's item 2, **not** the DoD's item-2 bar (frontier
enumeration). No dimension moved; F01 is still `partial` / item 2 `not_met`.

`tools/phase4_e02_disc_region_code_census.py` →
`analysis/phase4_e02_disc_region_code_census.json`. **16/16 scenes, 3,235
authored sectors, 0 disagreements** with the runtime table.

- **Code 3 exists and is not dead**: 4 sectors — it is the ordinary exit trigger
  of training, tunnels, cliffside canyon and riverbed run. ⚠️ It is also
  **already observed at runtime**: the 100% corpus write-watch sweep recorded
  writer PC `0x800496FC` for request 1, which pairs with the code-3 arm's store
  at `0x800496F8`. (An earlier line here said it had never been observed — that
  was over-generalised from the E10 exec-watch sweep.) Still open: a direct exec
  hit on the arm entry `0x800496E8`, and which levels drove the writes.
- **E10's instant-kill census is served**: code 1 = 15 sectors (scene 3 ×9,
  scene 10 ×5, scene 4 ×1) and nowhere else. Code 4 = 6 sectors, all scene 4.
- **Covered 16 of 17 valid scene ids.** Scene 16 (map/results, force-flag only,
  no save anchor) is a named residual.
- ⚠️ **The locator already existed** — E02's collision round trip
  (`analysis/phase4_e02_collision_roundtrip.json`, 2026-08-04) binds every scene
  to its container *and* array offset. No new locator was needed. Same shape as
  `phase3_jr_tables.json`: **grep `analysis/` before building an extractor.**
- `tools/edit_sector_region_code.py` no longer hardcodes LEVEL01's
  `(chunk 32, 0x36570)` — both coordinates vary per level (chunks 27–33, plus
  four flat `.ALL` containers) and an unknown container is now a hard error.

## Task 3 — context you'll need (already done, do not redo)

The 5-arm dispatch is **located and its arms observed**:

```
8004964C  addu $v1,$v0,$zero    ; region code from sector_region_code_query(0x80038F38)
8004965C  lh   $v0,0x23a0($v0)  ; single-shot guard on [0x800823A0]
          code 1 -> 0x800496A8   code 2 -> 0x800496C4
          code 3 -> 0x800496E8   code 4 -> 0x80049718
```

- **code 1 = pits** → `0x8004A700` with `a3=1`, emits transition request 2 =
  instant-death terrain transition. **Now statically proven** (2026-08-10): the
  `a3≠0` path `0x8004A828`→`0x8004A90C`→`0x8004A998`→`0x8004A9E8` stores request
  2 **unconditionally** at `0x8004A9F4` (fade 23), skipping knockback, i-frames
  and the health decrement entirely.
- **code 4 = goo** → same callee with `a3=0`: knockback + i-frame check + health
  `−1`, and request 2 only *if* health goes negative (`0x8004A8B4`, fade 60).
- **code 2/3** = completion (request 1, timer 23, SFX 0x3a); they differ only by
  the `sp+0x50` commit flag.
- ⚡ `a3` is a small **enum**, not a boolean (`s4` vs `3` at `0x8004A998`, vs `2`
  at `0x8004A9B8`). Canon's exit-trigger matrix carries the corrected table.
- Spikes, falling rocks, acorn and ground bird fire **no** region-code arm —
  they damage via object/actor collision, a separate hazard family.
- ⚠️ Instrumentation note: capturing `$v1` at `0x8004964C` reads the pre-write
  value (that instruction *is* the `addu`). **Capture `$v0`.**

## Smaller queued items

- **Verify Codex's E04 exclusion** — it excluded a "stale self-referential field"
  from the `missing_central_pins` gate. Flagged as close to the line about never
  weakening gates; never checked.
- **`source_closure` retry** — currently 56/1503 words (3.7%). The method fix is
  known: gate region-by-region, region N must reach zero before N+1.
  `engineering-specs/phase4-f01-source-closure-work-order.md`.
- **Operator recordings pending**: five seed-color clips (replacing the
  CachedInterpreter A13 set), and a **cold-boot Anthill** movie where the
  objective completes naturally (needed for `original_oracle`).

## Standing rules (non-negotiable)

- Movie replay **only** via `tools/launch_repro_playback.sh --execution-mode
  Interpreter`. The generic debugger launcher writes a settings.ini with no
  `[CPU]` section and silently desyncs Interpreter-recorded movies.
- **Batch instrumented runs**: fill the 64-watch budget across ALL rows before
  spending a slow replay. Parallelism works well — 5 isolated instances with
  atomic `mkdir` work-claiming ran 19 movies in ~20 min vs ~57 sequential.
- `reproducible: true`, a firing positive control, and a completed run **do not
  prove sync**. Operator eyes caught two silent desyncs this session.
- Evidence ≠ proof. Exact sets both directions; name every universe; report the
  fraction before the adjective; `unknown` beats a plausible guess.
- Compiled C owns instruction decoding; Python owns identity and pinning.
- Pin **derived inputs**, never two artifacts that pin each other.
- If a tracked tool imports a module, **`git add` the module** — one left
  untracked broke clean-checkout reproducibility in three tools today.
- Bank findings in docs, not chat; a count that changes moves on every surface.
- Commit finished work by default (standing operator authorization).
- ⚡ **Grep `analysis/` before building an extractor, locator or census.** Item 2's
  "blocker" was an artifact that had been committed six days earlier; so was
  `phase3_jr_tables.json` (869 indirect targets). Twice now.
- ⚡ **A tool that reports nothing is not a negative result** until you have shown
  it can report something on a known-positive input. The LEVEL01-hardcoded
  offset made 15 levels look code-free.

## Suggested opening move

Everything on the old task queue is closed. Two things gate progress and only
one of them is an agent's to do.

### 1. ⚠️ OPERATOR: one recording closes `original_oracle`

A **cold-boot movie in which Flik dies naturally** — any level, any death, as
long as it starts from boot. Death is what produces transition request 2
naturally (`a3≠0` stores it unconditionally at `0x8004A9F4`), and the skip arm of
the finalizer law is the last thing still evidenced only by injection.

The cheap alternatives are already ruled out by full replay: `D18_thud_fight`
(15,600 frames, 1 decision, request [1], 0 death stores) and
`E02_FreshLoad_Clover` (5,562 frames, 0 decisions). Everything else for this
dimension is repaired and detached-verified, so this single fixture finishes it.

Same recording also helps `lifecycle`, which needs cold-boot coverage that no
state-anchored movie can supply (only 3 of 83 corpus movies are from-boot).

### 2. ⚠️ OPERATOR: the item-2 bar ruling — this decides whether 9/9 exists

Six dimensions are reachable with ordinary effort. `complete_frontier` and the
semantic half of `typed_state`/`original_interfaces` are **not reachable by any
funded method** — see the roadmap §3, now live. So:

- **Accept** the enumerated 179-site residual as a declared, signed assumption
  carried on the row → F01 has a path to closure.
- **Hold strict** → F01 is permanently `partial`, and the honest move is to
  record that with its reason and stop spending on the frontier.

Do not fund a sixth frontier campaign before this ruling; the D3 result
explicitly does not fund one.

### 3. Agent work available now, needs nobody

`campaign_breadth`'s **applicability matrix and independent taxonomy**
(`engineering-specs/phase4-f01-oracle-breadth-repair-work-order.md`, elements
C1/C2, both NOT DONE). This is design work: freeze the universe across stages,
objectives, actor variants, special modes and exceptional paths; source the
eight-type mapping from the row/Canon definition, the scene table `0x80077FA0`
and disc structure — never from which levels passed — and freeze it in its own
commit before any outcome is consulted.
