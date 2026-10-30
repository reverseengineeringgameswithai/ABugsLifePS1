# Work order: D3 pointer-dispatch contracts (the last proof avenue for `complete_frontier`)

**Date issued:** 2026-08-10 · **Baseline:** current `master` (record
`git rev-parse HEAD` and `git status --short`; preserve operator WIP).
**Executor:** any agent (drafted for Codex hand-off; self-contained).

---

## 1. Standing — read this before anything else

F01's `complete_frontier` dimension is blocked by **179 unproved indirect
control-flow sites**. Four campaigns have attacked it; **do not re-run any of
them**:

| campaign | receipt | outcome |
|---|---|---|
| caller-domain recovery | `analysis/phase4_caller_domain_pilot.json` | NO-GO — OPEN caller sets |
| address-taken universes | `analysis/phase4_address_taken_pilot.json` | NO-GO — openness is not table membership |
| target-domain / exclusion | `analysis/phase4_target_exclusion_pilot.json` | NO-GO — 175-source interior-entry universe |
| discipline proof (D1/D2/D3) | `analysis/phase4_discipline_pilot.json` | NO-GO 0/39 |

The discipline pilot's verdict is the reason this order exists and is narrow:

- **D1 (return discipline, 19 sites) — STRUCTURE-SHAPED, dead.** Independently
  verified 2026-08-10: seven `jr $ra` sites in the GTE/clip region
  (0x80018F44, 0x8001923C, 0x80019614, 0x80019B3C, 0x80019F34, 0x8001A0DC,
  0x8001A1D4) jump to 18 targets whose `target−8` word is a **store**
  (`0xA6630030` = `sh $v1,0x30($s3)`), not a call. `$ra` is used as a
  general-purpose jump register in this binary, so return discipline is
  **false**, not merely unproven. No engine can prove a false property.
- **D2 (20 sites) — STRUCTURE-SHAPED, dead.** All sampled sites are
  materialized continuation jumps or a single-cell thunk, **not**
  bounds-checked indexed tables. The premise was wrong.
- **D3 (pointer dispatch, `jalr`, 140 sites = 78%) — CONTRACT-SHAPED, the only
  live avenue.** The pilot's own words: *"stronger alias and typed-state writer
  closure, object-field typing, or an ingress/BIOS exception contract could
  clear them."*

**This order pursues D3 and nothing else.** If D3 also returns
structure-shaped, `complete_frontier` has no known remaining technique and the
row's fate passes to the operator's item-2 bar ruling (roadmap §3).

## 2. What a D3 proof must establish (both parts, or it is not a proof)

For a dispatch site to clear:

1. **Table-membership invariant** — every value the dispatch can load is drawn
   from a region whose contents are provably census function entries (or a
   named, bounded exception set). Prove it over the region's **byte extent**
   AND over its **writer set**. The writer bound must come from the
   typed-state/region machinery (`tools/region_provenance.c`,
   `tools/phase4_typed_state.py`), **not** from "we looked and saw only
   entries."
2. **Protected-set disjointness** — the membership set does not intersect the
   protected set (58 KNOWN_WRITERS + 124 window sites + 4 closure roots = 128
   ids, pinned in `analysis/phase4_target_exclusion_freeze.json`).

Part 2 alone is sufficient for F01 even when the exact target is unknown: this
is an **exclusion**, not an enumeration. That is the whole reason D3 is still
alive after four NO-GOs.

⚠️ **Immunity requirement.** `SCUS_942_88:0x80018CBC` was declared to have an
"exact" 3-target domain; runtime showed a **fourth target taking >80% of
~38,000 dispatches** (`0x8001961C`, the one the analysis called dead-lexical).
**Any accepted proof must not depend on "we found all the reaching
definitions."** State explicitly, per proof, why that failure mode cannot apply.

## 3. The four named contracts — the actual work

The pilot named exactly what would clear D3. Each is a separate contract:

### (a) Shared dispatch cell `0x8007FBC4`
- Known lower-bound fact: one direct writer, `SetDumpFnt` at `0x80060FE8`.
- ⚠️ **4,266 unresolved store sites across 21 images (2,244 full-width) remain
  possible writers** — direct hits are a lower bound, **not a census**
  (`D3_shared_cell_writer_probe`, writer-identity sha
  `7aa7f59a9023c410…`). The contract must close this writer universe or bound
  it by region, or state precisely why it cannot.

### (b) Object-field provenance
Dispatches loading a function pointer from an object field need that field's
type/domain. This is the typed-state/region-binding machinery — the same wall
that leaves `original_interfaces` at **1/867 argument domains** (correction
banked 2026-08-10). Expect shared cost; report progress against **both**
dimensions.

### (c) BIOS / ingress exception contract
Some entries are reached from outside the analysed image (BIOS callbacks,
interrupt/exception vectors). Define what may legitimately enter, bounded by
the vector tables and the fork's residency machinery — or carry the affected
sites as a named residual.

### (d) Dynamic-module boundary
Frontend dispatches were observed transferring into **`0x800CABE0`-space,
outside every static image in the census** — dynamically loaded module code.
Requires a **loader contract**: what the loader can place there, bounded by the
loader's own code plus `memory.getResidency` / `transferLog` semantics. If it
cannot be established, say so; **do not approximate it**.

## 4. PILOT (mandatory, first)

- **Sample:** 12 D3 sites, chosen mechanically and outcome-blind: every D3 site
  whose dispatch region is already a decoded table in `phase3_jr_tables.json`
  (ascending pc, up to 8), plus the next 4 by ascending pc. Take the D3 set
  from `analysis/phase4_discipline_assignment.json` →
  `assignments.by_discipline.D3_pointer_dispatch` (140 ids — **this is the
  universe; do not re-derive it**).
- **Freeze the sample and the selection query in
  `ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md`
  BEFORE attempting any proof.** All four prior pilots honoured this; verified
  each time by commit ancestry.
- **Budget:** one session (~3 h compute).
- **GO:** ≥1 contract from §3 fully established **AND** ≥3 of the 12 sites
  clear both parts of §2 at gate grade **AND** the runtime cross-check is clean
  — every observed target at every proved site lies inside what the proof
  allows. Runtime corpus: `analysis/phase4_f01_jr_tuple_capture.json` (~200
  replays, 179 sites). **One violation is a soundness halt, regardless of
  counts — report it loudly; it is the most valuable possible outcome.**
- **NO-GO:** below either threshold. Bank the reviewed negative and, **per
  contract**, label the wall **technique-shaped** (a better engine clears it)
  or **structure-shaped** (the binary does not permit it). That label decides
  whether a sixth attempt is worth funding or whether `complete_frontier` is
  finished — say it plainly.
- **Independent cross-check:** every landed proof re-derived from image bytes
  by a second implementation. Precedents: the 2× count inflation, and the
  0x80018CBC falsification where one confident implementation was simply wrong.

## 5. Hard rules

- Exact sets both directions; universes named; conventions ≠ proof; `unknown`
  beats a plausible guess; nothing inferred encoded as a passing check.
- A proof cites instruction words. Runtime data may guide, corroborate and
  **falsify** — never establish a universal claim.
- ⚠️ Standing review ruling: **never generalize jr state propagation beyond a
  proved edge.** ⚠️ Table slots may share handlers (8 mover-VM slots → one
  handler): count **occurrences**, not unique targets. ⚠️ Hoisted-load idiom
  (22 sites) distorts pointer-load attribution — check explicitly.
- **F01 status does not move.** `partial` stands; item 2 `not_met`; only a
  fresh detached verifier banks. Do not touch
  `analysis/mechanics_baseline.yaml`.
- **You own the analysis chain for this order** (index → census → seed →
  extractor → result) — the assistant will not regenerate it while you run.
  Conversely, the assistant is working on the region-code dispatch and an E10
  hazard re-sweep, producing **new** artifacts only; do not touch
  `analysis/phase4_f01_campaign_breadth.json`,
  `analysis/phase4_f01_jr_tuple_capture.json`, or anything under
  `movies/Phase4/Interpreter/E10/`.
- ⚠️ Re-read the experiment log immediately before appending — the assistant
  appends to the same file.
- ⚠️ If a tool you add is imported by tracked code, **`git add` it**. A module
  left untracked on 2026-08-10 broke clean-checkout reproducibility in three
  tools and was caught only by the `tracked_python_untracked_imports` gate.
- No instrumented replay; the runtime corpus is complete and banked. Extent
  audit regenerated POST-commit; detached-worktree byte-identical verification
  before done.

## 6. Definition of done

1. Frozen sample recorded pre-outcome, then per-site and per-contract outcomes,
   then the explicit GO/NO-GO sentence — in that order.
2. On GO: proof artifacts with `--check`; gate universe additions per-edge;
   chain regenerated with derived re-pins; tests green; worktree verification;
   log + roadmap updated together.
3. On NO-GO: the reviewed negative to the same standard, each of the four
   contracts labelled technique- or structure-shaped.
4. Final report, one sentence each: what is now proved that was not; the
   residual (179 → N) and behind which contract; and whether
   `complete_frontier` retains any technical avenue at all. **Report fractions
   before adjectives** — a 3.7% match was once reported as an "exact
   near-miss."
