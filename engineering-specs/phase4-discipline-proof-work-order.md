# Work order: prove indirect control flow by DISCIPLINE, not by target set (Phase 4)

**Date issued:** 2026-08-09 · **Baseline:** current `master` (verify `git rev-parse HEAD`
and `git status --short`; preserve operator WIP).
**Executor:** any agent (drafted for Codex hand-off; self-contained).

---

## 1. Why this order exists — read this first

F01 (Anthill) cannot close because item 2 demands an **enumerated, exhaustive**
account of everything that can write the objective table. That demand dies at
**179 unproved indirect control-flow sites** (`jr`/`jalr` whose complete target
set is not proved at gate grade). Until every one is bounded or excluded, no
universal "these are all the writers" claim is available, and F01 stays
`partial` with blockers `[IMAGE_CENSUS_INCOMPLETE, MECHANICALLY_INCOMPLETE]`.

**Three campaigns already attacked this and returned honest NO-GOs.** Do not
re-run them:

| campaign | receipt | outcome |
|---|---|---|
| caller-domain recovery | `analysis/phase4_caller_domain_pilot.json` | NO-GO 0/20 — 10 sites poisoned by OPEN caller sets |
| address-taken universes | `analysis/phase4_address_taken_pilot.json` | NO-GO 0/4 roots — openness is not table membership; also removed ~316 FALSE indirect sites (data decoding as `jalr`), correcting the universe to **179** |
| target-domain / exclusion | `analysis/phase4_target_exclusion_pilot.json` | NO-GO 0/12 — four sites have exact *entry-scoped* domains but sit below gate grade behind a **175-source interior-entry universe** |

All three shared one shape: **"enumerate this site's exact target set."** That
formulation is what keeps failing — each site's targets depend on callers,
whose targets depend on other unproved sites, and the recursion never bottoms
out.

**This order reformulates the goal.** Instead of enumerating targets per site,
prove that each site **obeys a discipline** — a structural property that bounds
where it can go without enumerating where it does go. A discipline proof is
local, compositional, and (unlike target enumeration) does not require closing
the caller graph first.

The reformulation is not speculation: a runtime campaign
(`analysis/phase4_f01_jr_tuple_capture.json`) observed these sites across ~200
movie replays and the observed behavior **sorts cleanly into exactly three
disciplines**. The runtime data is the roadmap that says which proof each site
needs. It is EVIDENCE ONLY and never substitutes for a proof.

### Runtime context (evidence, not proof — do not cite as proof anywhere)

- 79/179 sites observed; **100 silent** across any% runs, the 39-clip behavior
  library, and a complete operator-recorded 100% collection corpus. Gameplay
  evidence has converged (the full 100% corpus lit ZERO new sites).
- **Zero** observed target ever landed in the protected set (58 KNOWN_WRITERS +
  124 window sites + 4 closure roots).
- **One falsification, and it is the reason the strict bar exists:** the
  exclusion pilot's "exact" entry-scoped domain for `SCUS_942_88:0x80018CBC`
  omitted `0x8001961C` (`gte_quad_clip_emit_variant_c`), which runtime shows is
  that site's DOMINANT target (>330k observations). A local static claim of
  completeness was simply wrong. **Any discipline proof this order accepts must
  be immune to that failure mode** — i.e. it must not depend on "we found all
  the reaching definitions."
- ⚠️ Known data caveat: tuples recorded at `LEVEL07_LEVEL1:0x800B3FCC` include
  ~42 implausible targets (values outside any code range). This is residency
  contamination — the overlay region held other content during load phases.
  Treat overlay-site runtime data as untrusted unless residency is verified.

---

## 2. The three disciplines, with exact sizing

Sizing over the frozen 179-site universe
(`analysis/phase4_target_exclusion_freeze.json`, field
`pilot_selection.candidate_union_ids` — **this file is the universe; do not
re-derive it**):

| discipline | sites | observed/silent | dominant strata |
|---|---:|---|---|
| **D1 — return discipline** (`jr $ra`) | 19 | 15 / 4 | incoming-ra 9, register-provenance 5, table-backed 5 |
| **D2 — switch/computed locality** (`jr` on a computed register) | 20 | 15 / 5 | computed 15, table-backed 3, opaque 2 |
| **D3 — pointer dispatch** (`jalr`) | 140 | 49 / 91 | table-backed 66, opaque 36, mixed 33 |

D3 is the mass of the problem (78%). D1 is small but is the class whose
recursion poisoned the earlier pilots, so discharging it has leverage beyond
its count.

### D1 — return discipline

**Claim shape:** "this `jr $ra` transfers only to a *return address produced by
a call instruction*, therefore it creates no new edge the call graph does not
already contain."

**Proof obligation (per owner function):** `$ra` is written only by `jal`/`jalr`
link semantics or by a *balanced* stack save/restore of a value that was itself
such a link; it is never computed, offset, loaded from non-frame memory, or
aliased. Frame-slot reasoning must bound the store/load pair to the function's
own frame with no intervening write through an unproved pointer.

Runtime corroboration (not proof): observed `jr $ra` targets are call-site
successors — e.g. `0x800602A8` returned to 20 distinct callers, all legitimate.

### D2 — switch/computed locality

**Claim shape:** "the target is `base + f(index)` where the index is
bounds-checked before the jump, so the target set is exactly the decoded table
range."

**Proof obligation:** the standard gate-grade per-edge jump-table proof the
project already performs (`phase3_jr_tables.json` machinery + gate artifact).
⚠️ Standing review ruling: never generalize jr state propagation beyond a
proved edge. ⚠️ Table slots may share handlers (8 mover-VM slots → one handler):
count occurrences, not unique targets.

### D3 — pointer dispatch

**Claim shape (two parts, both required):**
1. **Table membership invariant:** every value the dispatch can load is drawn
   from a region whose contents are provably *function entries of the census*
   (or a named, bounded exception set). Prove it over the region's byte extent
   AND over its writers — the writer bound comes from the typed-state region
   machinery (`tools/region_provenance.c`, `tools/phase4_typed_state.py`), not
   from "we looked and saw only entries."
2. **Protected-set disjointness:** the membership set does not intersect the
   protected set. This is sufficient for F01 even when the exact target is
   unknown — an exclusion, not an enumeration.

**Known sub-problem — the dynamic-module region.** Some frontend dispatches
were observed transferring into **`0x800CABE0`-space, outside every static
image in the census**. That is dynamically-loaded module code. Its discipline
requires a **loader contract**: what the loader can place there, bounded by the
loader's own code and the residency machinery (`memory.getResidency`,
`transferLog`). If that contract cannot be established, say so and carry the
affected sites as a named residual — do NOT approximate it.

---

## 2b. Who this pays: the 179 sites are SHARED INFRASTRUCTURE, not Anthill code

Owner-subsystem mapping of the 179 sites (110 owner functions, derived
2026-08-09 from the static index + symbol table; buckets are name-based and
approximate, the counts are exact):

| owning subsystem | sites | share |
|---|---:|---:|
| unnamed / other | 62 | 34.6% |
| E14 frontend, save, pad | 48 | 26.8% |
| E01/E03/E11 render + geometry | 38 | 21.2% |
| E16 streaming, loaders, overlays | 17 | 9.5% |
| E12 audio | 7 | 3.9% |
| E02/E06 collision + contact | 4 | 2.2% |
| E07/E08 props, movers, event VM | 3 | 1.7% |

**Essentially none of it is Anthill-specific code.** F01 is merely the row
that ran into the wall first: 166 of the 179 sites are in the RESIDENT image,
shared by every level and every row.

⚠️ **CORRECTION (2026-08-10) — do not overstate the transfer.** An earlier
version of this section claimed each discipline proved "discharges the same
obligation for E01/E02/E03/E11/E14/E16". That was an inference, and reading
those rows' actual `missing` fields in `analysis/mechanics_baseline.yaml`
falsifies it. Their current blockers are SEMANTIC, not control-flow: payload
decode validation and marker-class word semantics (E01), transition semantics
and overlay ownership (E02), aux-list content and a transition fixture (E03),
field roles (E04/E05), interaction rules and scene→DAT binding (E08), event
maps and lifecycles (E12/E13/E15). Proving a discipline does not answer any
of those. The accurate statement is three-part:

1. **Ownership is shared (fact).** The sites live in those subsystems' code,
   so the proofs are performed ON E-section code, by people reading it — the
   understanding produced is E-section understanding.
2. **The obligation is probably DEFERRED, not currently binding (PARTLY
   INFERRED — read the caveat).** VERIFIED for four rows, which say
   frontier-shaped things in their own words: E09 states "no complete writer/callee frontier"
   explicitly; E06 wants "complete 0x38-field reader/writer typing" and an
   executable gate; E07 is "sufficiently exhausted to move on but not
   strict"; E16's per-overlay entry lists are bracketed with 18 of 42
   single-detector residuals and no runtime call check. For those four the
   payoff is direct once they advance.
   ⚠️ **NOT verified for the other rows.** The claim that they too will hit
   this wall assumes the 179 sites lie inside each row's own reachability
   frontier — a row's item-2 obligation is scoped to ITS structures, not the
   whole binary, and no per-row frontier has been computed (F01's extractor
   needs a per-row protected set, which does not exist for them). This is the
   SAME inference that made the 2026-08-09 version wrong, merely time-shifted.
   Treat it as a hypothesis; the cheap way to settle it per row is to define
   that row's protected set and run the existing frontier extractor.
3. **There is one immediate, modest payoff (fact).** D2/D3 resolution adds
   proved edges to the call graph, which is exactly what several rows need
   for *attribution* questions already on their lists: E05's unattributed
   second-registry writer, E14's side-table increment source, E01's untraced
   animated-tile uploader call site. Better indirect-edge resolution makes
   those findable.

Report per-discipline progress per owning subsystem anyway — it is how rows 1
and 2 above become visible instead of inferred.

## 3. Stages

### Stage 0 — discipline assignment (mechanical, cheap, do first)

Assign every one of the 179 sites to D1/D2/D3 **from the instruction encoding
and owner-function structure**, not from the runtime data. Where the encoding
is ambiguous, assign the *weakest* discipline (fail-closed) and name why.
Output: `analysis/phase4_discipline_assignment.json` — exact sets both
directions (per-discipline site lists AND a residual list of sites no
discipline claims), with the 110 owner functions enumerated.

Cross-check the assignment against the runtime tuple data and **report
disagreements** (a site whose observed behavior contradicts its assigned
discipline is a finding, not a nuisance — 0x80018CBC is the precedent).

### Stage 1 — per-discipline proof engines

Compiled C owns all instruction decoding (operator standing rule); Python
drivers own repository identity and pinning. Each engine emits, per site,
either a PROVED verdict with its derivation chain (instruction words cited) or
a NAMED WALL with the exact register/cell where the proof died. No confidence
scores, no "likely", no partial credit.

### Stage 2 — consumption

Feed proved sites into the gate/closure machinery, regenerate the chain
(index → census → seed re-pin → extractor → result), and report deltas against
the OLD pins before re-pinning tests intentionally. Report the corpus undecided
store count and the wall tallies.

---

## 4. PILOT (mandatory, first) — measure which discipline yields

Do **not** bet the campaign on one discipline. The pilot samples all three so
the data says where the leverage is.

- **Sample (mechanical, outcome-blind):** all 19 D1 sites; 8 D2 sites chosen by
  ascending pc; 12 D3 sites chosen as: every D3 site whose dispatch region is
  already a decoded table in `phase3_jr_tables.json` (ascending pc, up to 8),
  plus the next 4 by ascending pc. **Freeze this list, with the selection
  query, in `ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md`
  BEFORE attempting any proof.** The freeze-before-outcomes discipline has been
  honored by both prior pilots; honor it here.
- **Budget:** one session (~3 h compute).
- **GO:** ≥60% of D1 sites proved, **AND** ≥1 D3 table-membership invariant
  landed at gate grade, **AND** the runtime cross-check is clean (every
  observed target at every proved site lies inside what the proof allows — one
  violation is a soundness halt, regardless of counts; report it loudly, it is
  the most valuable possible outcome).
- **NO-GO:** below either threshold. Bank the reviewed negative with per-site
  walls and, for each discipline, one sentence on whether the wall is
  *technique-shaped* (a better engine would clear it) or *structure-shaped*
  (the binary genuinely does not permit the proof).
- **Independent cross-check:** for every landed proof in the pilot, a second
  implementation must re-derive the claim from the image bytes alone. The
  2×-inflation precedent and the 0x80018CBC falsification are both cases where
  a single implementation was confidently wrong.

---

## 5. Hard-truth rules (binding)

- Exact sets both directions; sample ≠ universe; every universe named.
- A proof cites instruction words. "We found all the reaching definitions" is
  NOT a proof — that exact claim is what 0x80018CBC falsified.
- Conventions are never relabeled as proof; convention-bounded sites stay a
  separate count.
- Never encode an inference as a passing check.
- Runtime data is evidence and corroboration ONLY. It may guide, cross-check,
  and falsify — it may never establish a universal claim.
- A count that changes moves on **every** surface (tables, prose, provenance).
- **F01 status does not move in this order.** `partial` stands; item 2 stays
  `not_met`; only a fresh detached verifier may bank a status change, and only
  the operator may rule on the item-2 bar.

## 6. Hygiene (binding)

- Compiled C for instruction decoding/probing; Python for identity/pinning.
- Pin DERIVED INPUTS, never mutually-pinning container artifacts (the
  receipt↔index cycle of 2026-08-07 is the named precedent).
- Additive artifacts; new filenames; preserve operator WIP; no destructive git.
- Extent audit regenerated POST-commit; detached-worktree byte-identical
  `--check` verification of the full chain (copy `REBUILD/files` pristine
  inputs) before calling any stage done.
- **No instrumented replay.** The runtime corpus is complete and banked
  (`analysis/phase4_f01_jr_tuple_capture.json` + the external evidence store
  `~/Downloads/ABL-external-evidence/phase4_jr_tuple_capture_2026-08-08/`,
  228 sha-pinned entries). If a live run ever seems necessary: STOP and ask the
  operator — it must be batched across rows under the standing batching rule.
  ⚠️ If a replay is ever authorized: movie replay works ONLY via
  `tools/launch_repro_playback.sh --execution-mode Interpreter`; the generic
  debugger launcher writes a settings.ini with no `[CPU]` section and silently
  desyncs Interpreter-recorded movies.
- ⚠️ Hoisted-load idiom (22 known sites) is a standing hazard for any
  pointer-load attribution — check for it explicitly.

## 7. Definition of done

1. Stage 0 artifact committed with `--check` mode, plus the frozen pilot list
   recorded pre-outcome in the experiment log.
2. Per-site outcome table, then the explicit GO/NO-GO sentence, in that order.
3. On GO: proof artifacts with `--check`; gate universe additions per-edge;
   chain regenerated with derived re-pins; tests green; worktree verification;
   experiment log + memory surfaces updated together; commit.
4. On NO-GO: the reviewed negative to the same standard, with each discipline's
   wall labeled technique-shaped or structure-shaped — that label is what tells
   the operator whether a fourth attempt is worth funding.
5. Final report, one sentence each: what is now proved that was not; what
   remains unproved and behind which wall; whether the residual (179 → N)
   changes the scale of the operator's item-2 bar decision.
