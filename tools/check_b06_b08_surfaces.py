#!/usr/bin/env python3
"""Check that every surface carrying the B06/B08 findings agrees.

WHY THIS EXISTS
---------------
A finding in this repo lives on six surfaces at once, and a PARTIAL update is worse
than no update: it leaves Canon asserting something false, which the next agent will
believe and act on. That happened twice in one day on these rows --

  * the experiment note kept a "_solved" title after the rows were retracted;
  * SYS_player_power_slot (Canon) went on saying "No deterministic cold-boot oracle",
    "Fixtures are not durable", "No committed runner" and "does not collect either
    pickup in a second stage" for a whole commit after all four became false;
  * the Bubble shield row in the Whole-Game Mechanics Baseline kept four stale claims
    because a `str.replace` silently no-op'd on a string that no longer matched.

That last one is the argument for this file over careful editing: a replacement that
does not match fails SILENTLY, and prose surfaces have no schema to catch it.

This asserts agreement across the surfaces rather than the truth of any claim. It
cannot tell you a finding is right; it can tell you the docs disagree with each other,
which is the failure mode that actually bit.

USAGE
    tools/check_b06_b08_surfaces.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "analysis/mechanics_baseline.yaml"
ARTIFACT = ROOT / "analysis/phase4_b06_b08_powerups.json"
VAULT_ROWS = ROOT / "ObsidianVault/Playbooks/Game Solving Roadmap/Whole-Game Mechanics Baseline.md"
PHASE4 = ROOT / "ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Solve Every Gameplay and Engine Subsystem.md"
SYSNOTE = ROOT / "ObsidianVault/Canon/Systems/SYS_player_power_slot.md"
EXPNOTE = ROOT / "ObsidianVault/Experiments/EXP_2026-08-01_phase4_b06_b08_power_slot.md"

ROW_IDS = ("B06_invincibility", "B08_bubble_shield")
VAULT_ROW_LABELS = ("| Temporary invincibility", "| Bubble shield")

# Claims that were true once and are now false. If any reappears on any prose surface,
# that surface has been reverted or was never updated.
STALE = [
    "No deterministic cold-boot oracle",
    "no cold-boot oracle",
    "Fixtures are not durable",
    "fixtures not centrally hash-pinned",
    "No committed runner",
    "no overlay census",
    "frontier not alias-aware",
    "does not collect either pickup in a second stage",
]


def main() -> int:
    problems = []

    rows = yaml.safe_load(BASELINE.read_text())
    rows = rows["rows"] if isinstance(rows, dict) and "rows" in rows else rows
    status = {r["id"]: r.get("status") for r in rows if r["id"] in ROW_IDS}
    for rid in ROW_IDS:
        if status.get(rid) != "partial":
            problems.append(f"{BASELINE.name}: {rid} is {status.get(rid)!r}, expected 'partial' "
                            f"(open DoD items 2/4/6/7/8 remain)")

    vault = VAULT_ROWS.read_text()
    for label in VAULT_ROW_LABELS:
        line = next((l for l in vault.splitlines() if l.startswith(label)), None)
        if line is None:
            problems.append(f"{VAULT_ROWS.name}: row {label!r} not found")
            continue
        if "Partial" not in line:
            problems.append(f"{VAULT_ROWS.name}: {label!r} does not read Partial")
        if "Cold-boot oracle MET" not in line:
            problems.append(f"{VAULT_ROWS.name}: {label!r} does not record the cold-boot oracle")

    for path in (VAULT_ROWS, PHASE4, SYSNOTE, EXPNOTE):
        text = path.read_text()
        for claim in STALE:
            # allow it only where explicitly marked superseded/struck through
            for line in text.splitlines():
                if claim in line and not any(
                        m in line for m in ("~~", "Superseded", "superseded", "no longer true")):
                    problems.append(f"{path.name}: STALE claim still asserted: {claim!r}")
                    break

    for path, needle, what in ((SYSNOTE, "## Cold-boot oracle", "cold-boot section"),
                               (EXPNOTE, "## Cold-boot oracle", "cold-boot section"),
                               (PHASE4, "**MET 2026-08-01**", "DoD items marked met")):
        if needle not in path.read_text():
            problems.append(f"{path.name}: missing {what}")

    # Wider-vault sweep. The six-surface check above would not have caught
    # src_re/blue_seed_plants.c and the archived blue-seed note still asserting the
    # disproven "0x800A6590 bit 0x02 = invincibility" model for a whole day after
    # SYS_player_power_slot was corrected -- a partial update that left Canon
    # self-contradictory. Retired claims are allowed only where marked corrected.
    RETIRED = [
        ("bit 0x02", "invinc"),          # bit 0x02 is a transient per-action flag
        ("0x08", "BUBBLE SHIELD"),       # bit 0x08 is the checkpoint marker
    ]
    for path in list(ROOT.glob("src_re/*.c")) + list(ROOT.glob("ObsidianVault/**/*.md")):
        try:
            text = path.read_text()
        except Exception:
            continue
        # Require the SPECIFIC marker. An escape hatch as loose as `"corrected" in text`
        # would exempt most of the vault and make this sweep vacuous.
        if "CORRECTED 2026-08-01" in text:
            continue
        for a, b in RETIRED:
            for line in text.splitlines():
                if a in line and b.lower() in line.lower() and not line.lstrip().startswith(">"):
                    problems.append("%s: retired claim un-marked: %r"
                                    % (path.relative_to(ROOT), line.strip()[:90]))
                    break

    # STALENESS. The checks above assert invariants; they do NOT notice a narrative note
    # falling behind. The Experiment note once drifted 23 commits behind the artifact --
    # missing source closure, the renderer, the callee-write census, the writer union and
    # the promotion gate -- while this check still reported PASS. Every major artifact
    # section must therefore be represented on the notes that carry the narrative.
    art_probe = json.loads(ARTIFACT.read_text())
    COVERAGE = {
        "frontier": (["callee", "overlay"], (EXPNOTE, SYSNOTE)),
        "audio_assertion": (["VAG 50", "-3"], (EXPNOTE, SYSNOTE)),
        "production_chain": (["ctor 0x25", "`0x25`"], (EXPNOTE, SYSNOTE)),
        "render_and_asset_binding": (["80014844"], (EXPNOTE, SYSNOTE)),
        "source_closure": (["player_power_slot_800a657e"], (EXPNOTE, SYSNOTE)),
        "promotion_gate": (["clean clone", "clean-clone"], (EXPNOTE,)),
    }
    for section, (needles, notes) in COVERAGE.items():
        if section not in art_probe:
            continue
        for note in notes:
            text = note.read_text()
            if not any(n.lower() in text.lower() for n in needles):
                problems.append(
                    "%s: artifact has section %r but the note mentions none of %r "
                    "-- the note has fallen behind" % (note.name, section, needles))

    # SCORECARD COHERENCE + SUPERSEDED-CLAIM SWEEP.
    #
    # This is the check that was missing, and its absence cost a review cycle. The
    # COVERAGE sweep above tests that new findings are PRESENT. It never tested that
    # superseded ones are ABSENT, so when findings were added without retiring what they
    # replaced, the notes asserted BOTH -- items graded met in one paragraph and open two
    # screens down, an "8 of 9" score beside a table showing four ADVANCED -- and this
    # script still printed PASS. A partial documentation update is worse than none,
    # because it launders a contradiction as an update.
    scorecard = (art_probe.get("ROW_STATUS") or {}).get("scorecard", "")
    if scorecard:
        # Whatever the artifact says the score is, no surface may claim a different one.
        STALE_SCORES = ["4 met, 3 advanced", "8 of 9", "8/9",
                        "all nine items are met", "all nine items met",
                        "every item is met", "items 4, 7 and 8 remain"]
        for note in (EXPNOTE, SYSNOTE, PHASE4):
            text = note.read_text()
            for stale in STALE_SCORES:
                if stale.lower() in text.lower():
                    problems.append(
                        "%s: states a score that the artifact contradicts (%r vs %r) "
                        "-- a superseded count left in place"
                        % (note.name, stale, scorecard[:60]))

    # Claims retired by later work. Each is (needle, why) and must not appear un-negated:
    # a line is un-negated when it lacks a strikethrough, a supersession marker, or a
    # quote/callout prefix. These specific strings were all live in Canon at once while
    # their replacements were live too.
    SUPERSEDED = [
        ("exactly 7 writers", "the 7-writer census was structurally blind to aliased "
                              "accesses and missed the grant itself"),
        ("exactly 4 writers of true health", "same blind census"),
        ("No semantic source", "DoD 8 closed by src_re/player_power_slot_800a657e.c"),
        ("has only ever been collected in scene 11", "B08 collected in a second stage"),
        ("but not asserted at runtime", "audio asserted at runtime for both rows"),
    ]
    for note in (EXPNOTE, SYSNOTE, PHASE4, ROOT / "analysis/mechanics_baseline.yaml"):
        if not note.exists():
            continue
        for line in note.read_text().splitlines():
            stripped = line.strip()
            negated = (stripped.startswith(">") or stripped.startswith("~~")
                       or "~~" in stripped or "SUPERSEDED" in stripped.upper()
                       or "superseded" in stripped or "retracted" in stripped.lower()
                       or "was WRONG" in stripped)
            if negated:
                continue
            for needle, why in SUPERSEDED:
                if needle.lower() in stripped.lower():
                    problems.append(
                        "%s: superseded claim still asserted (%s): %r"
                        % (note.name, why, stripped[:80]))

    art = json.loads(ARTIFACT.read_text())
    if "cold_boot_oracle" not in art:
        problems.append(f"{ARTIFACT.name}: no cold_boot_oracle section")
    if "dod_progress" not in art.get("ROW_STATUS", {}):
        problems.append(f"{ARTIFACT.name}: ROW_STATUS has no dod_progress")

    for o in ("analysis/phase4_b06_oracle.json", "analysis/phase4_b08_oracle.json"):
        p = ROOT / o
        if not p.exists():
            problems.append(f"{o}: missing oracle artifact")
            continue
        d = json.loads(p.read_text())
        if d.get("verdict") != "PASS":
            problems.append(f"{o}: verdict is {d.get('verdict')!r}, not PASS")
        if not d.get("from_boot"):
            problems.append(f"{o}: not anchored to a cold boot")

    if problems:
        print("SURFACE CHECK: FAIL")
        for p in problems:
            print("  -", p)
        return 1
    print("SURFACE CHECK: PASS -- baseline, vault rows, Phase 4, Canon SYS, Experiment "
          "and artifacts all agree (rows partial, cold-boot oracle recorded everywhere)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
