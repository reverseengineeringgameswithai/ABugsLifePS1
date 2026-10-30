---
kind: playbook
id: PB_vault_integrity_audit
name: Vault Integrity Audit — a reusable prompt
status: active
---

# Vault Integrity Audit

A prompt for auditing `ObsidianVault/` and the row registry. Paste the block below
into a fresh agent session. Everything above it is context for the human choosing to
run it.

**What this is for.** `tools/validate_vault.py` already catches dangling links, schema
violations, evidence-policy breaches, duplicate addresses and missing aliases — run it
first and do not re-implement it. This audit targets the classes it structurally
cannot see: pages that **contradict themselves**, claims that have been **retracted
elsewhere but survive here**, prose that has **drifted behind the evidence under it**,
and findings that are **stated more strongly than their method supports**.

**It resolves, it does not only report.** An earlier draft sorted every contradiction
into "needs a human", which would have produced a list and no improvement. The
operative split is: a contradiction about a **verifiable fact** (an address, an
opcode, a count, a branch target) is settled by re-deriving it from the pristine
image, and the auditor must do that; a contradiction about **interpretation** (what a
flag *means*) cannot be, and escalates. In this repository that split is load-bearing
— "exactly one setter" versus four was settled by a scan, while "the player is dying"
versus "gameplay suspended" needed a census *plus* a judgement call.

**Why those classes.** Every failure mode in the catalogue at the end of the prompt
actually occurred in this repository. The audit is empirical, not hypothetical.

---

## THE PROMPT

```
Audit the Obsidian vault at ObsidianVault/ and the row registry
analysis/mechanics_baseline.yaml for integrity defects, and RESOLVE the ones the
artifacts can settle. An audit that only produces a list of contradictions has moved
the work, not done it.

The split that decides whether you fix or escalate:

  * A contradiction about a VERIFIABLE FACT -- an address, an opcode, a count, a
    branch target, whether a store exists, what a table holds -- is not a judgement
    call. REBUILD/files/SCUS_942.88 and the overlay blobs settle it. You MUST
    re-derive it and resolve the page. Leaving it "for a human" is refusing the
    easiest and most valuable part of the job.
  * A contradiction about INTERPRETATION -- what a flag MEANS, whether a mechanic is
    "the same as" another, what a name should be -- cannot be settled by re-deriving.
    Escalate those, with both readings and the evidence for each.

If you cannot tell which kind you are looking at, ask: "is there a command that
returns the answer?" If yes, run it.

## Non-negotiables

1. NEVER delete a finding to resolve a contradiction. If two statements conflict,
   determine which is supported and mark the other as corrected — preserving the
   correction history. A vault that silently loses its wrong turns teaches nobody,
   and the next reader re-derives the same error.
2. NEVER trust prose over the artifact. If a page says "exactly seven writers",
   re-derive it. If it cites a PC, read that PC in REBUILD/files/SCUS_942.88 or the
   named overlay. Prose is the thing under audit; it is not evidence.
3. NEVER trust a name. Function names in analysis/functions.json are census-derived
   and have been wrong repeatedly, including in ways that changed conclusions. A name
   is a hypothesis. Check what the code does.
4. Cite file:line for every finding. A finding a human cannot navigate to in one
   click is not actionable.
5. Do not touch files another agent is mid-edit on. `git status` first; treat
   modified-but-uncommitted files as owned by someone else unless they are yours.
6. Static analysis and runtime evidence are different tiers. Do not upgrade one to
   the other. "Proven statically" and "observed running" are separate claims.

## Phase 0 — mechanical sweeps (do these first; they are cheap and exhaustive)

Run each across all of ObsidianVault/ excluding Archive/, and against
analysis/mechanics_baseline.yaml. Report counts, then the instances.

  a. DUPLICATED SECTIONS. For each page, list `^## ` headings and flag any repeated.
     Splice-style edits (`text[:i] + new + text[text.index(marker):]`) silently
     re-append whole regions when `marker` occurs earlier than intended.

  b. SELF-CONTRADICTION. Within a single page, find pairs of statements about the
     same address, PC, count or name that disagree. Highest-yield search: a page
     containing both "X means A" and "X means B", or both "RETRACTED" and a later
     unqualified restatement of the retracted claim.

  c. RETRACTED CLAIMS STILL LIVE. Grep the whole vault for RETRACTED / CORRECTION /
     "was wrong" / "no longer" and, for each, extract the retracted proposition. Then
     search the vault for that proposition asserted WITHOUT the qualifier. A
     retraction on page A does not clean up page B.

  d. NUMBERS THAT MUST MATCH SOMETHING. Any "N pins", "N writers", "N sites",
     "N of M rows" in prose: locate the tool or artifact that produces N and confirm.
     Counts drift when a later pass finds an extra site and the prose is not updated.

  e. ORPHANS AND STUBS. Pages with no inbound [[links]] from any non-Archive page;
     pages under 15 lines that assert a finding; pages whose `evidence:` or
     `src_paths:` frontmatter names a file that does not exist.

  f. LINK HYGIENE. Beyond validate_vault.py's dangling check: links pointing INTO
     Archive/ from live pages, links to a page whose `id:` differs from its filename,
     and findings that cite an experiment note or artifact without linking it.

## Phase 1 — over-claiming (the highest-value pass)

For each Canon page making a bounded or closure claim, classify the METHOD and check
the claim does not exceed it:

  - "domain closed" / "exactly N sites" / "the only writer". Was the scan general
    (tracking lui + addiu/ori chains, resolving off(reg), with $gp seeded as the
    proven constant 0x80081D98), or was it a fixed instruction-pattern match? A
    pattern match CANNOT close a domain — it closes one encoding. Flag every closure
    claim whose method was a pattern match, or which cannot be traced to a tool.
  - Scope of "closed". An OVERLAY-LOCAL address (region A, 0x800B39A0..0x800B5788)
    cannot be "closed over all images": every overlay reuses that RAM. The valid form
    is per-scope — this overlay, the resident EXE, every other overlay. Flag any
    overlay-local closure phrased globally.
  - Variable-index stores. `sb rt, off(base)` where base is computed at runtime is
    invisible to constant-tracking. A closure claim over an array (slots, tables)
    must say whether such stores were considered.
  - "verified" / "confirmed". By what? Static pins, a poll-only replay, a traced
    replay, or a controlled experiment? Poll-only fixtures (movie format v3) can
    NEVER have been traced — flag any page claiming a trace against one.
  - Negative claims ("nothing else writes it", "no fail state", "pays nothing").
    These are the easiest to overstate. Check the bound: negative over WHAT region,
    WHAT encodings, WHAT run?

## Phase 2 — staleness against evidence

  - Row registry: for every row in analysis/mechanics_baseline.yaml, does `missing`
    describe something the row's own bindings/Canon page already answers? Does
    `next` propose work that is already done? Does either assert a claim that a
    linked page retracts? A row that misstates its own state is worse than an
    incomplete one, because the summary field is what a reader trusts.
  - Canon `status:` and `confidence:` frontmatter versus body. A page whose body says
    "not established" while frontmatter says `confirmed` is a defect.
  - Experiment notes: does the note's conclusion still match the Canon page it feeds?
    Corrections tend to land in Canon and not propagate back.

## Phase 3 — attribution and duplication

  - Findings presented as novel that duplicate another row's earlier work. Search the
    vault for the address/PC before accepting "first pinned here". Cross-row
    duplication has happened and wasted a pass.
  - Claims inherited from a superseded page still cited as current. Anything under
    Archive/ or _Revamp/ cited by a live page needs justification.

## Output

Produce a findings table, most severe first. For each:

  file:line | class | what it says | what is true | evidence | proposed action

Classes: CONTRADICTION, RETRACTED-ALIVE, OVER-CLAIM, STALE, DUPLICATE, ORPHAN,
LINK, COUNT.

Then, separately:
  - RESOLVED BY ME: every factual contradiction you settled against the image, plus
    the mechanical defects (duplicate headings, broken links, counts you re-derived,
    frontmatter naming a nonexistent file). Each with the tool/pin that settles it.
  - NEEDS A DECISION: ONLY interpretation contradictions, claims whose evidence
    requires a runtime observation you cannot make, and fixes that would change a
    row's status. If this list is longer than the resolved list, you have probably
    mis-sorted factual questions into it -- re-check before reporting.

## Resolving a factual contradiction

For each one, produce a RESOLUTION, not an edit:

1. Re-derive the fact with a general scan or a direct read of the image. Never settle
   it by preferring the more recent page, the more confident wording, or the one with
   more detail -- all three have been wrong here.
2. Write or extend a tool that PINS the answer (compiled C against the pristine image
   is the standing convention; see tools/phase4_closure_audit.c for the shape). A
   resolution that exists only as prose will drift again.
3. Correct the losing page, keeping the wrong reading visible as correction history
   with a one-line reason. Do not delete it.
4. Add the guard.

If re-deriving DISAGREES WITH BOTH pages, that is the most valuable outcome available
and must be reported prominently rather than folded into a fix.

## Fix policy

Anything you fix must come with a GUARD that would have caught it — a pytest
assertion, added to the relevant tests/ file. Guards must assert what must NOT be
present, not only what must: every content check in this repo that failed to catch a
contradiction was checking for presence only. A page can satisfy "says the right
thing" and "says the wrong thing" at the same time.

Commit with tools/isolated_commit.sh (several agents share this checkout; never
`git add` on a shared file). One commit per defect class, not one giant sweep.

## Scope and termination

The vault has ~1,074 live pages. Do not attempt all of them in one pass. Prioritise:
  1. Canon/ (these are the pages other work is built on)
  2. analysis/mechanics_baseline.yaml rows with status partial or bounded
  3. Experiments/ notes from the last 14 days
  4. everything else, sampled

Stop when you have either audited Canon/ completely or produced 25 findings,
whichever comes first, and say which. A partial audit that says so is useful; an
audit that implies completeness it does not have is the same defect class it is
looking for.
```

---

## Known failure catalogue

Seed patterns for the audit. Every one occurred here, with the mechanism that
produced it — these are what the phases above are shaped around.

| # | Defect | Mechanism |
|---|---|---|
| 1 | Duplicated sections + a retracted claim restored | Splice on `t.index(marker)` found an EARLIER occurrence and re-appended the tail |
| 2 | Guards passed on a self-contradicting page | Every content guard asserted presence of the new text; none asserted absence of the old |
| 3 | "Exactly one setter" was four | The check was a fixed two-instruction pattern; the real site stored through a register |
| 4 | A closure claim scoped wrongly | An overlay-local address described as closed "over all images", where every overlay reuses the RAM |
| 5 | Row `missing` asserted a retracted claim | The finding was corrected in Canon and the tool; the row's prose kept the old version |
| 6 | Work re-done as novel | The row's `missing` was stale; a sibling row had pinned the same PC a day earlier |
| 7 | A census name drove a wrong conclusion | `resident_level_transition_initiator` actually contained the hit/knockback block |
| 8 | A correct claim "refuted" by a bad test | An execute breakpoint in shared overlay RAM fired for a different level's code |
| 9 | A count went stale behind a later discovery | Progress word banked as five writers; a later pass found the sixth and did not update the count |
| 10 | Reading stopped at the first plausible answer | The store without the loop after it; a shared block named after the first guard reaching it |

## Running it

1. `python3 tools/validate_vault.py --check` — the ratchet. Note pre-existing
   regressions before starting so they are not attributed to the audit.
2. `git status` — identify files owned by other agents.
3. Paste the prompt block.
4. Expect the first useful finding within a few minutes; the mechanical sweeps in
   Phase 0 are where the density is.
