# Work order: clear the last closure-debt error + the extent disagreement

**Date issued:** 2026-08-10 · **Baseline:** current `master`.
**Executor:** any agent (drafted for Codex hand-off; self-contained).
**Why this matters more than its size:** `tools/phase4_closure_debt.py` refuses
to write the retained ledger while ANY campaign error remains, and while it
cannot write, **no F01 dimension can be promoted** even once earned
("claim authored ≠ dimension met ≠ verifier promoted"). The blocker was taken
from 7 errors to 1 on 2026-08-10 (commit `fc772a006b8b`); this order clears the
last one. Full diagnosis is in
`ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md`
under "closure-debt blocker DIAGNOSED" and "closure-debt blocker REPAIRED".

---

## Task 1 — the last closure-debt error (3 entries)

Run `python3 tools/phase4_closure_debt.py --write`. The single remaining error
is `analysis/phase0_2_external_fixture_set.json:missing_central_pins`, which
must be `len_eq 0` and currently holds three entries:

1. **`E02_FreshLoad_Clover.movie.json`** — referenced by *bare filename*, while
   the file actually lives at
   `movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json`. (Note: it has no
   `.sav`; the behavior sweep skipped it as NOSAV. Its existence is not in
   question — only the reference form.)
2. **Two prose strings used where a path belongs**, in
   `analysis/phase3_gate_audit.json` and `analysis/phase2_row_coverage.json`:
   - `"6 progression-diverse saves reused read-only; live L1/R1 traces on level01.sav"`
   - `"6 progression-diverse saves reused read-only; live L1/R1/L1+left/R1-held traces on level01.sav"`

**Required approach — repair the source, never the gate.** The gate
(`missing_central_pins == 0`) is legitimate and must NOT be weakened, re-pinned
away, or have these entries whitelisted. Find where each reference is authored
(the consumer artifacts are generated — locate their generators and inputs) and
fix the *reference*:

- For (1): correct it to the real repository-relative path.
- For (2): these describe a **set of fixtures**, not one path. Replace each with
  the actual fixture paths it denotes, or with whatever the schema's correct
  representation of a multi-fixture reference is. If the six saves cannot be
  identified from the surrounding record, say so and stop — do not invent them.

Then regenerate in dependency order (`tools/knowledge_closure_audit.py --write`
→ re-pin the two `phase0_2_*` SHAs in `config/phase4_campaigns.yaml` → re-run
the debt tool) and confirm the ledger writes with **zero** errors.

⚠️ Re-pinning those two SHAs after regeneration is expected and correct — their
content legitimately changes. Do not re-pin anything *else*.

## Task 2 — the extent disagreement (found by the previous work order)

A substrate test fails because two authorities disagree about one function:
the configured end for `0x80042E94` is `0x80042F98`, while the census says
`0x80042FA0` — an 8-byte gap. Decide it **from the image bytes**, the way the
2026-08-10 manifest question was decided: disassemble the tail and determine
where the function actually ends (return + delay slot, next prologue,
alignment padding). Then correct whichever authority is wrong and record the
evidence. If the bytes are genuinely ambiguous, report that rather than
picking one.

---

## Hard rules

- **Do NOT touch** `analysis/phase4_*frontier*`, the census,
  `config/phase4_f01_frontier_seed.yaml`, the gate artifacts, the typed-state
  outputs, `analysis/phase4_f01_abi_ledger.json`, or
  `analysis/phase4_f01_source_closure.json`.
- ⚠️ **Concurrency:** the assistant is separately writing a
  `campaign_breadth` artifact and appending to the same Obsidian experiment
  log. Append your section at the end of the file as usual, but re-read the
  file immediately before appending so you do not clobber a section added while
  you worked.
- Do not modify `analysis/mechanics_baseline.yaml`; do not claim any dimension
  met. Only a fresh detached verifier banks status.
- Preserve operator WIP; commit only your own paths; extent audit regenerated
  POST-commit; detached-worktree verification before done.
- Exact numbers both directions; a gate must never be weakened to make a tool
  succeed; report the fraction before any adjective.

## Definition of done

1. `tools/phase4_closure_debt.py --write` succeeds with **0 errors**, and the
   retained ledger artifact is committed.
2. Task 2 decided from bytes, with the disassembly evidence in the commit
   message or a receipt, and the failing substrate test now passing.
3. Report, one sentence each: what each of the three entries turned out to be
   and how it was repaired; what the true extent of `0x80042E94` is and which
   authority was wrong; whether the debt ledger now writes cleanly.
