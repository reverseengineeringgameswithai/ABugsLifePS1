#!/usr/bin/env python3
"""Consistency linter for the ObsidianVault (RCA campaign).

Encodes the deep-dive audit findings as machine checks so the vault can't
silently drift again. Read-only; emits a report and (with --check) ratchets
against tests/vault_lint_baseline.json so counts can only go down.

Categories
  dangling_links   [[T]] that resolves to no file (basename or alias)
  archive_only     [[T]] that resolves ONLY to Archive/ notes (Canon has no
                   matching basename/alias -> Obsidian misroutes to superseded)
  evidence_policy  Canon note status in {confirmed,live_confirmed,proven} with
                   no evidence entry referencing an existing EXP_ note
  evidence_deadfile evidence entry that is a path to a file that no longer exists
  dup_address      an address claimed as primary by >1 Canon Function/Memory note
  missing_alias    Canon Function/Memory note whose aliases don't include its id
  schema           frontmatter parse failure or missing required keys

Usage
  python tools/validate_vault.py            # human summary
  python tools/validate_vault.py --json     # full machine report
  python tools/validate_vault.py --check    # exit 1 if any count exceeds baseline
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "ObsidianVault"
BASELINE = ROOT / "tests" / "vault_lint_baseline.json"

CONFIRMED = {"confirmed", "live_confirmed", "proven"}
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FM_RE = re.compile(r"^---\n(.*?)\n---", re.S)
FENCE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_code(text: str) -> str:
    """Blank out fenced + inline code so wikilinks inside them aren't counted
    (Obsidian doesn't render links in code spans either)."""
    text = FENCE_RE.sub("", text)
    return INLINE_CODE_RE.sub("", text)

CATEGORIES = [
    "dangling_links", "archive_only", "evidence_policy",
    "evidence_deadfile", "dup_address", "missing_alias", "schema",
]


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


# Evidence trees that are local-only by policy (gitignored game-derived data:
# disassembly, staging, extraction, native-art references). A pointer into one
# of these is DEAD only when the tree itself is present locally but the file is
# missing; when the whole tree is absent (a clean source archive) the pointer
# is unverifiable-there by design, not dead.
LOCAL_EVIDENCE_ROOTS = (
    "asm/", "REBUILD/", "extracted/", "DAT/", "OVL/",
    "mod/glyphs/pickup_letters/reference",
)


def _local_evidence_absent(e: str) -> bool:
    for root in LOCAL_EVIDENCE_ROOTS:
        if e.startswith(root):
            return not (ROOT / root.rstrip("/")).exists()
    return False


def _is_archive(p: Path) -> bool:
    return "/Archive/" in str(p).replace("\\", "/")


def _is_canon(p: Path) -> bool:
    s = str(p).replace("\\", "/")
    return "/Canon/" in s


def load_notes():
    """Return (notes, index). notes: list of dicts. index: name->[paths]."""
    notes = []
    index = collections.defaultdict(list)          # lower name (stem|alias) -> paths
    exp_stems = set()
    for p in sorted(VAULT.rglob("*.md")):
        text = p.read_text(errors="replace")
        index[p.stem.lower()].append(p)
        if p.stem.startswith("EXP_"):
            exp_stems.add(p.stem)
        fm, err = {}, None
        m = FM_RE.match(text)
        if m:
            try:
                fm = yaml.safe_load(m.group(1)) or {}
                if not isinstance(fm, dict):
                    fm, err = {}, "frontmatter is not a mapping"
            except Exception as e:                 # noqa: BLE001
                fm, err = {}, f"yaml error: {str(e)[:80]}"
        aliases = fm.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        for a in aliases:
            if isinstance(a, str) and a.strip():
                index[a.strip().lower()].append(p)
        notes.append({"path": p, "text": text, "fm": fm, "err": err,
                      "aliases": [str(a).strip() for a in aliases if str(a).strip()]})

    # Obsidian wikilinks can target attachments as well as notes. Index both the
    # complete filename (``image.png``) and stem so embedded assets do not appear
    # as dangling merely because the consistency checks otherwise parse Markdown.
    for p in sorted(VAULT.rglob("*")):
        if p.is_file() and p.suffix.lower() != ".md":
            index[p.name.lower()].append(p)
            index[p.stem.lower()].append(p)
    return notes, index, exp_stems


def _norm_evidence(item) -> str:
    s = str(item).strip().strip('"').strip("'")
    s = s.strip("[]").strip()
    return s


def audit():
    notes, index, exp_stems = load_notes()
    findings = {c: [] for c in CATEGORIES}

    # --- link checks (only for links originating in LIVE notes; Archive is
    #     frozen history and its internal link-rot is out of scope) ---
    for n in notes:
        if _is_archive(n["path"]):
            continue
        for m in LINK_RE.finditer(_strip_code(n["text"])):
            raw = m.group(1).split("|")[0].split("#")[0].strip()
            raw = raw.rstrip("\\").strip()   # drop escaped-pipe artifact in table cells
            if not raw:
                continue
            cand = index.get(raw.lower(), [])
            if not cand:
                findings["dangling_links"].append({"from": _rel(n["path"]), "target": raw})
            elif all(_is_archive(c) for c in cand):
                findings["archive_only"].append({"from": _rel(n["path"]), "target": raw})

    # --- frontmatter-driven checks (Canon only) ---
    by_addr = collections.defaultdict(list)
    for n in notes:
        p, fm = n["path"], n["fm"]
        if n["err"]:
            findings["schema"].append({"note": _rel(p), "issue": n["err"]})
        if not _is_canon(p):
            continue
        kind = (fm.get("kind") or "").lower()
        nid = str(fm.get("id") or "")

        # schema: Canon Functions require the core keys
        if "/Canon/Functions/" in str(p):
            for k in ("kind", "id", "address", "name", "status", "evidence"):
                if k not in fm:
                    findings["schema"].append({"note": _rel(p), "issue": f"missing key '{k}'"})

        # evidence-policy + dead-file evidence
        status = str(fm.get("status") or "").lower()
        ev = fm.get("evidence") or []
        if isinstance(ev, str):
            ev = [ev]
        ev_norm = [_norm_evidence(x) for x in ev]
        has_exp = any(
            e.startswith("EXP_") and (e.split()[0] in exp_stems or any(e in s for s in exp_stems)
                                      or e in exp_stems)
            for e in ev_norm
        )
        if status in CONFIRMED and not has_exp:
            findings["evidence_policy"].append(
                {"note": _rel(p), "status": status, "evidence": ev_norm})
        for e in ev_norm:
            if "/" in e and not e.startswith("http"):
                if not (ROOT / e).exists() and not _local_evidence_absent(e):
                    findings["evidence_deadfile"].append({"note": _rel(p), "evidence": e})

        # dup address: two notes in the SAME Canon folder describing one address
        # (twin notes from the copy-first migration). Key on frontmatter address
        # else any 8-hex in the stem, scoped to the folder so a Function note and
        # a Memory note about the same address don't count as a duplicate.
        folder = "functions" if "/Canon/Functions/" in str(p) else \
                 "memory" if "/Canon/Memory/" in str(p) else None
        # Some retained notes are deliberately secondary or superseded views of
        # a primary address note. They may keep an address for historical search
        # and provenance, but must opt out explicitly instead of silently
        # competing as a second Canon authority.
        primary_address = fm.get("canonical_address", True) is not False
        if folder and not primary_address:
            primary_note = str(fm.get("superseded_by") or fm.get("primary_address_note") or "")
            candidates = index.get(primary_note.lower(), []) if primary_note else []
            if not primary_note or not candidates or all(_is_archive(c) for c in candidates):
                findings["schema"].append({
                    "note": _rel(p),
                    "issue": "canonical_address false requires a live superseded_by or primary_address_note",
                })
        if folder and primary_address:
            addr = str(fm.get("address") or "").lower()
            if not re.fullmatch(r"0x[0-9a-f]{8}", addr):
                sm = re.search(r"[0-9A-Fa-f]{8}", p.stem)
                addr = f"0x{sm.group(0).lower()}" if sm else ""
            if re.fullmatch(r"0x[0-9a-f]{8}", addr):
                by_addr[(folder, addr)].append(_rel(p))

        # missing alias: Canon Function/Memory should alias its id
        if ("/Canon/Functions/" in str(p) or "/Canon/Memory/" in str(p)) and nid:
            al = {a.lower() for a in n["aliases"]}
            if nid.lower() not in al:
                findings["missing_alias"].append({"note": _rel(p), "id": nid})

    for (folder, addr), paths in sorted(by_addr.items()):
        if len(paths) > 1:
            findings["dup_address"].append({"address": addr, "folder": folder, "notes": paths})

    counts = {c: len(findings[c]) for c in CATEGORIES}
    counts["dangling_links_distinct"] = len({f["target"] for f in findings["dangling_links"]})
    counts["archive_only_distinct"] = len({f["target"] for f in findings["archive_only"]})
    return findings, counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="dump full findings as JSON")
    ap.add_argument("--check", action="store_true", help="ratchet against baseline; exit 1 on regression")
    args = ap.parse_args()

    findings, counts = audit()

    if args.json:
        print(json.dumps({"counts": counts, "findings": findings}, indent=1))
        return 0

    print("ObsidianVault consistency report")
    for c in CATEGORIES:
        print(f"  {c:18s} {counts[c]:5d}")
    print(f"  {'(dangling distinct)':18s} {counts['dangling_links_distinct']:5d}")
    print(f"  {'(archive distinct)':18s} {counts['archive_only_distinct']:5d}")

    if args.check:
        if not BASELINE.exists():
            print("no baseline; run once and write tests/vault_lint_baseline.json")
            return 1
        base = json.loads(BASELINE.read_text())["max"]
        bad = False
        for c in CATEGORIES:
            if counts[c] > base.get(c, 0):
                print(f"REGRESSION {c}: {counts[c]} > baseline {base.get(c, 0)}")
                bad = True
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
