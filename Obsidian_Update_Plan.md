# Knowledge-system update plan — vault, instructions, and cross-agent parity

**Status: PROPOSAL. Nothing here is adopted or implemented.**
Written 2026-08-04. Measurements in §1 were taken on commit `0db04e7eb5ad` and are
reproducible with the commands shown. Lives at the repo root deliberately —
`ObsidianVault/` is under a separate deep audit and this document should not disturb it.

---

## 0. What this is, and what it is not

This came out of a design discussion about whether `ObsidianVault/` is sufficient as the
project's knowledge system, or should be replaced by a structured entity/claim/observation
ledger with a query CLI.

**The conclusion was: do not replace it, and do not demote it.** The vault is not the
correctness problem. It is already doing load-bearing work — including catching errors in
tools that would otherwise look authoritative (see §1.3). Replacing it with a different
notes application, or reducing it to a decorative "interpretation layer", would change the
interface while preserving every underlying weakness.

What *is* worth doing is narrower: close a cross-agent knowledge gap, remove the surfaces
that are manually duplicated, make corrected mistakes queryable, and require assertions to
expose their evidence. Those are the phases below.

**Explicitly rejected** (no present justification): a universal entity/claim ontology,
one-record-per-claim authoring, a graph database, a vector database as the primary
retrieval route, a hosted wiki, a second documentation repository, SQLite as an authored
source, an MCP service before a local CLI exists, and any generator that writes into
Claude's host-local memory directory.

---

## 1. The finding that sets the priority order

The original framing assumed the main risk was documentation drift inside the vault. That
turned out to be the *smaller* problem. The larger one is that **the two agents working
this repo do not share a knowledge floor.**

### 1.1 Measured asymmetry

```bash
# reproduce
ls -la AGENTS.md CLAUDE.md
grep -c "@AGENTS.md" CLAUDE.md
for p in "Interpreter" "arm.phase\|armed_while_paused" "PHYSICAL\|0x1FFFFFFF" "advanceFrames"; do
  printf "%-32s AGENTS:%s CLAUDE:%s\n" "$p" "$(grep -ci "$p" AGENTS.md)" "$(grep -ci "$p" CLAUDE.md)"
done
ls -d .claude/skills/* .agents/skills/* 2>/dev/null
ls ~/.claude/projects/-home-user-Downloads-ABL/memory/*.md | wc -l
```

| surface | Claude | Codex |
|---|---|---|
| `CLAUDE.md` — 9.5 KB; 12× Interpreter, 7× arm-phase, 2× advanceFrames | ✅ | ❌ |
| `AGENTS.md` — 3.7 KB; **0×** Interpreter, **0×** arm-phase, **0×** advanceFrames | ❌ | ✅ |
| auto-memory — **148 notes, 1.3 MB**, host-local, outside git, unversioned | ✅ | ❌ |
| `.claude/skills/duckstation-external-debugger` (no `.agents/skills/` exists) | ✅ | ❌ |

`CLAUDE.md` does **not** import `AGENTS.md`. They are two independently maintained
instruction files that have already diverged. The physical-breakpoint-address rule — where
a KSEG0 address is accepted, reports `enabled: true`, and never fires — is in **neither**
instruction file; it exists only in Claude's auto-memory.

### 1.2 Why this is a correctness problem, not a convenience problem

Codex today can record a movie on `CachedInterpreter`, arm a trace, and get a silently
desynced capture: `reproducible` still reports `true`, no error is raised, the game drifts
off-script, and the awaited event never fires. The capture looks plausible and is empty.
No surface Codex reads would have warned it.

The same applies to the arm-phase one-frame desync, the `advanceFrames` vs 60 Hz
difference, and the physical-address rule. These are the four highest-cost known traps in
the project and Codex is blind to all of them.

That failure is silent, permanent, and invisible from the operator's side — the work simply
comes back wrong-but-plausible. It outranks every documentation-structure concern here.

### 1.3 Why the vault stays load-bearing

A worked example from the same session that produced this plan, and the reason the
"demote prose" thesis was withdrawn:

A purpose-built C tool scanned resident text for references to the contact pool and
confidently reported **10**. It had a pinned executable hash, a pinned tool commit, a
recorded command, and deterministic output — i.e. perfect provenance. It was still wrong:
the extractor recognised `lui`+`addiu` base materialisation but not `lui`+`ori`, and so
missed the billboard renderer.

What falsified it was a prose sentence in a Canon page stating that a renderer scans the
same 64 records. **The narrative layer caught an error the structured layer would have
blessed** — and would have blessed *more* firmly for carrying provenance.

The lesson is not that prose is inherently more trustworthy. It is that trust follows
**evidence independence**, not file format. An extractor result rendered into YAML and then
into a Markdown table is one evidence path displayed three times, not three sources.

---

## 2. Phases

Each phase lists deliverables, who must decide, rough cost, and the failure it prevents.

### Phase 1 — One shared knowledge floor *(do this first)*

**Prevents:** silent, wrong-but-plausible captures from Codex; divergence between two
instruction files; procedural knowledge that cannot survive an agent switch.

| # | Deliverable | Notes |
|---|---|---|
| 1.1 | `AGENTS.md` becomes the single root contract; `CLAUDE.md` reduces to `@AGENTS.md` plus genuinely Claude-specific items | Removes a live duplication between two files that have already diverged |
| 1.2 | `docs/hazards/*.md` — in-repo, versioned, one file per durable procedural hazard | See migration list below |
| 1.3 | One canonical skill at `agent-skills/reverse-engineering/`, generated into `.claude/skills/` and `.agents/skills/` | Codex has no skill directory today |
| 1.4 | Auto-memory demotes to *reinforcement*: pointers into `docs/hazards/` + Claude-specific operational quirks | Repo becomes canonical. **No** repo→home-directory generator |

**Migrate (~10–15 notes, not all 148).** Only the *procedural* ones — 8 are already typed
`feedback`:

- DuckStation trace gotchas, including physical breakpoint addresses
- Interpreter-recorded movies survive instrumentation; record on Interpreter
- movie arm-phase desync + the v4 self-correcting format
- reach for the DuckStation API before brute-forcing RAM
- commit hygiene: slice a shared file, never `git add` the sliced file, assert the staged
  path list **and** the row diff before *and* after committing
- C-for-ASM-probing standing rule
- never encode an inference as a passing check

> **These keep their full narrative.** A thin pointer is not equivalent. The commit-hygiene
> note works precisely because it records that an agent knew the rule and violated it twice
> anyway, and that only a mechanical assert stopped it. Reduced to "see the hazard
> registry", it would not have changed behaviour. **Push complete procedures; push only
> pointers for facts.**

The remaining ~130 memory notes are *game findings*. Those belong in the vault and mostly
already are; memory keeps a one-line index entry pointing at them.

**Cost:** ~1 day. **Needs operator decision:** no.

---

### Phase 0 — Make the workspace attributable

**Prevents:** every session paying 10–20 minutes to answer "is this failure mine?", for
both agents.

| # | Deliverable |
|---|---|
| 0.1 | `tests/failure_baseline.json` — pinned commit, exact test command, tool/runtime versions, and every failing test name classified `expected / environmental / flaky / unexplained` |
| 0.2 | Concurrency contract written into `AGENTS.md`: the git index is shared, HEAD can move mid-session, stage explicit paths only, assert the staged file list and the registry row diff **before and after** commit |

Current baseline is 76 failed / 1361 passed / 36 deselected. The objective is **not** fixing
all 76 — it is making a new regression distinguishable from the existing floor.

**Cost:** ~half a day. **Needs operator decision:** no.

**Deferred, operator-gated:** inventorying the ~93 uncommitted files and moving agents into
isolated worktrees. Worktrees would fix the shared-index and moving-HEAD hazards, but a
clean worktree leaves the operator's in-progress work behind — and `AGENTS.md`'s first rule
is to preserve it. Classifying those files as required-shared-WIP vs operator-only needs
intent only the operator has, and returning patches against a snapshot changes the commit
workflow. Hold until §5's `workspace_interference` metric shows an actual wrong finding
rather than lost time.

---

### Phase 2 — One writable source per fact

**Prevents:** a value updated in one place and stale in another.

- Generate the vault's prose row surface from `analysis/mechanics_baseline.yaml`.
- Generate `Canon/Indexes/Address Index.md` from Canon frontmatter (hand-maintained today).
- Mark every generated region visibly, including: *projection of one source, not
  independent corroboration.*
- **Verify source → owned output in a clean temp directory. Never a repo-wide
  `git diff --exit-code`** — in a tree with ~93 dirty files and concurrent agents, that
  conflates a stale projection, another agent's edit, and unrelated dirt.

Generate only surfaces that have *demonstrably* drifted. Do not broadly generate Canon
pages; human interpretation must stay hand-written around generated factual sections.

---

### Phase 3 — Make dead ends queryable

**Prevents:** a correction being discoverable only by reading the one page that mentions it.

- `knowledge/traps.yaml`: id, address/symbol, build, previous classification, current
  classification, why the previous was rejected, evidence, replacement record.
- `tools/re addr <addr>` / `symbol <name>`, with `--json`.

Seed from negatives already scattered through the vault: the mover-VM "park opcodes don't
exist" finding, D17's jump being a halt rather than a park, the cases where a census name
was wrong, B09's unreachable super-jump combinations, the F02 table-vs-function
misclassification. Every one is currently reachable only by opening the right page.

---

### Phase 4 — Provenance and status rules in `validate_vault.py` (ratcheted)

**Prevents:** assertions outrunning their evidence, and status inflating between surfaces.

- A page marked `confirmed` cannot rely solely on a source that describes itself as
  inferred or unproven. *(This one alone would have caught the `render_attr` defect — the
  cited source literally says "inferred … not proven".)*
- A semantic field name must cite the instruction or experiment that assigned the meaning;
  static dataflow alone cannot support a behavioural name at `confirmed`.
- A numeric value must carry its extractor command or exact artifact locator.
- A dispatch assertion: every declared predicate cites evidence, and prose must not claim
  broader scope than the declared predicates support.
- A required-but-unresolved field needs a blocker and a next action — a bare `unknown` is
  invalid. *(Not "every table must have a row count": sentinel-terminated and dynamic
  extents are legitimate.)*
- A generated projection cannot carry stronger status than its source.
- `support:` entries that share one artifact do not count as separate corroboration.

These encode failure modes already observed. They **do not** verify that the game model is
true, and the implementation should say so rather than implying factual completeness.

---

### Phase 5 — Tool completeness discipline

**Prevents:** §1.3 — structured provenance laundering an incomplete extractor into
authority.

Every counting or enumerating tool emits a completeness claim:

```yaml
extractor:
  command: tools/find_contact_refs SCUS_942.88
  completeness_claim: none        # none | bounded | exhaustive
  recognizes:
    - lui_plus_addiu
    - lui_plus_ori                # added after it was missed
```

A tool may assert *"ten references were found by this search."* It may **not** assert
*"there are exactly ten references."* The second is a completeness claim requiring
exhaustive pattern coverage, independent confirmation, or an enumerated residual.

> The load-bearing field is `completeness_claim`, **not** the `recognizes` list. An
> exclusion list is an unknown-unknowns list — the author who knew to list `lui_plus_ori`
> would have handled it. `completeness_claim: none` is authorable *without* knowing what you
> missed. Treat `recognizes` as best-effort documentation that grows as gaps are found.

Retrofit highest-traffic tools first — the function census, `region_provenance`, the
reference scanners — because those feed Canon claims across the whole project.

---

### Phase 6 — Measure, then decide

One line appended to each investigation's experiment note:

```
dup_surfaces=<count>; missed_existing_knowledge=<yes|no>; workspace_interference=<none|time_only|wrong_finding>
```

Deliberately three fields, all answerable from work already done. An eight-metric pilot
would test willingness to fill in forms, not the architecture.

**Escalation triggers — formalize only on recurrence:**

| observation | response |
|---|---|
| same fact manually updated in >1 place, twice | generate that surface |
| same qualifier omission recurs | add a structured field + validator rule |
| superseded knowledge missed during normal lookup | expand the trap index |
| one subsystem repeatedly needs joins across experiments/addresses/builds | structure that subsystem only |
| `workspace_interference=wrong_finding` ever appears | do the deferred worktree migration immediately |
| structured authoring costs more than the defects it prevents | reduce granularity or remove it |

---

## 3. Principles this plan is built on

1. **The image, executable and runtime are the source of truth.** Everything else describes
   them and can drift or simply be wrong.
2. **The vault is the durable, human-readable project model and audit trail** — load-bearing,
   not decorative, and not the source of truth. That framing was already correct.
3. **Trust follows evidence independence, not file format.** Structured output is not
   categorically better than prose; either can expose an error in the other.
4. **Push complete procedures; push pointers for facts.** Procedures must change behaviour
   before an agent touches anything, so they need their full narrative. Build-scoped facts
   need exact scope and evidence, so they belong in a queryable record.
5. **Any assertion may live anywhere, but must expose its basis.** Exact values belong in
   prose when they make the reasoning falsifiable — a gate PC + mask table is what lets a
   reader check the disassembly. The rule is *generated or cited, never hand-typed*, not
   *no values in prose*.
6. **Repeated display is not corroboration.** One extractor result shown in three places is
   one evidence path.
7. **No validator can detect an unknown unknown.** Say so explicitly rather than implying
   completeness.

---

## 4. Recommended order

1. **Phase 1.1–1.2** — merge the instruction files, land `docs/hazards/`. Highest value,
   ~1 day, no operator decision, and it is the only item that fixes a *silent correctness*
   failure rather than a time cost.
2. **Phase 0.1–0.2** — baseline characterization and the concurrency contract.
3. Reassess with Phase 6 data before starting Phases 2–5.

Phases 2–5 are individually adoptable and none depends on the others. Resist doing them all
because they form a tidy set; each should be justified by an observed defect.

---

## 5. Open questions for the operator

1. **Instruction merge shape** — how much stays Claude-specific in `CLAUDE.md` after the
   `@AGENTS.md` import? (Proposal: only Claude-runtime specifics; all DuckStation/RE
   procedure moves to the shared root or `docs/hazards/`.)
2. **Worktrees vs shared tree** — deferred above, but it needs a decision eventually, and it
   changes whether agents commit directly to `master` or return patches.
3. **Whether `tools/re` should be a new binary or an extension of existing tooling.**
4. **Who owns generated surfaces** once Phase 2 lands, given concurrent agents.
