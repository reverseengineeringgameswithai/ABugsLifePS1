#!/usr/bin/env python3
"""Phase-3 knowledge-closure audit against the roadmap's Definition of Finished.

The roadmap now says a finding is not FINISHED because it was demonstrated —
only when it is banked so a later agent or mod can locate, verify and consume it
without repeating the work. It also says the closure audit must SHOW that, not
assert it. So this tool checks each requirement mechanically and refuses to
trust config/phase3_findings.yaml's own prose:

  1 provenance   the declared fixtures exist AND the evidence artifact hash-pins
                 them (a fixture that can change silently is not provenance)
  2 machine      every declared machine representation exists
  3 evidence     the artifact exists, is regenerable, and names its command
  4 guard        the named test EXISTS, and (when a ::test is named) that test
                 function is actually defined in it — a guard that does not exist
                 is worse than none, because it looks like coverage
  5 placement    the Canon/roadmap page exists and LINKS to the evidence artifact
  6 mod contract non-empty AND states an unsafe assumption (an address without its
                 ownership and lifecycle is not a safe extension point)
  7 durability   every declared machine/evidence path is TRACKED IN GIT (no tracked
                 source may depend silently on an untracked file); operator media
                 may live outside git but must be hash-pinned in the artifact
  8 confidence   evidence-backed vocabulary; corrections list what they supersede

Any unmet requirement is a COMPUTED gap. Exit 1 while gaps remain.

Usage: python3 tools/phase3_knowledge_audit.py
Output: analysis/phase3_knowledge_audit.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import hashlib
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import knowledge_closure_audit  # noqa: E402
import phase3_duckstation_rpc_manifest as rpc_manifest  # noqa: E402
from live_session_provenance import retained_pristine_save_gaps  # noqa: E402
VOCAB = {"confirmed", "partial", "inferred", "disproven", "blocked"}
FIXTURE_SET = ROOT / "analysis" / "phase0_2_external_fixture_set.json"
BASELINES = ROOT / "tools" / "build_baselines.json"
STRICT_PRISTINE_AGGREGATES = {
    "analysis/phase3_record_probe.json",
    "analysis/phase3_render_descriptors.json",
    "analysis/phase3_fn_ptr_fields.json",
}


def tracked(rel: str) -> bool:
    try:
        subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                       cwd=ROOT, capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _load_external_fixtures() -> dict[str, dict]:
    doc = json.loads(FIXTURE_SET.read_text())
    return doc.get("entries") or {}


def _load_build_baselines() -> dict:
    return json.loads(BASELINES.read_text())


EXTERNAL_FIXTURES = _load_external_fixtures()
BUILD_BASELINES = _load_build_baselines()


def _artifact_pin(art: dict, rel: str) -> tuple[str | None, str | None]:
    for key in (rel, Path(rel).name):
        for field in ("fixture_sha256", "patched_fixture_sha256"):
            pins = art.get(field) or {}
            if key in pins:
                return pins[key], field
    return None, None


def _fixture_expectation(rel: str, art: dict) -> tuple[str | None, str | None, str]:
    path = ROOT / rel
    rel_stage = rel.removeprefix("REBUILD/files/")
    if rel in EXTERNAL_FIXTURES:
        return EXTERNAL_FIXTURES[rel]["sha256"], "external_fixture_set", FIXTURE_SET.name
    staged = ((BUILD_BASELINES.get("staged_inputs") or {}).get(rel)
              or (BUILD_BASELINES.get("staged_inputs") or {}).get(rel_stage))
    if staged:
        return staged["sha256"], "build_baseline", BASELINES.name
    media = (BUILD_BASELINES.get("pristine_media") or {}).get(Path(rel).name)
    if media and media.get("sha1"):
        return None, "pristine_media_sha1_only", BASELINES.name
    if rel.startswith(("extracted/", "build/", "OVL/", "DAT/")):
        pinned, field = _artifact_pin(art, rel)
        if pinned:
            return pinned, "local_media_artifact", field
        return None, "local_media_artifact", "unhashed"
    if path.exists():
        return sha256_file(path), "tracked_path", "workspace"
    return None, None, "unknown"


def audit_one(f: dict) -> list[str]:
    gaps: list[str] = []
    fid = f["id"]

    # 3 evidence (checked first: several other requirements read it)
    ev_rel = f.get("evidence", "")
    ev_path = ROOT / ev_rel
    if not ev_rel or not ev_path.exists():
        gaps.append(f"evidence artifact missing: {ev_rel!r}")
        art = {}
    else:
        art = json.loads(ev_path.read_text())
        if "_comment" not in art or "Regenerate" not in art.get("_comment", ""):
            gaps.append("evidence artifact does not record its regeneration method")
    if not f.get("command"):
        gaps.append("no exact command recorded")

    # 1 provenance — fixtures must EXIST and be HASH-PINNED in the artifact
    prov = f.get("provenance") or {}
    if not prov.get("media"):
        gaps.append("no media identity recorded")
    pinned = {**(art.get("fixture_sha256") or {}),
              **(art.get("patched_fixture_sha256") or {})}
    for fx in prov.get("fixtures") or []:
        artifact_hash, artifact_field = _artifact_pin(art, fx)
        expected_hash, fixture_class, source = _fixture_expectation(fx, art)
        if not artifact_hash:
            gaps.append(f"fixture not hash-pinned in the evidence artifact: {fx}")
            continue
        if not fixture_class:
            gaps.append(f"fixture class unknown/unpinned outside the artifact: {fx}")
            continue
        if expected_hash and artifact_hash != expected_hash:
            gaps.append(
                f"fixture hash mismatch for {fx}: artifact={artifact_hash} "
                f"expected={expected_hash} from {source}")
        if fixture_class == "pristine_media_sha1_only":
            gaps.append(f"fixture uses a sha1-only pristine-media pin; add a sha256 source: {fx}")
        if (fixture_class == "tracked_path" and not tracked(fx)
                and not fx.startswith(("build/", "extracted/", "OVL/", "DAT/"))):
            gaps.append(f"fixture exists locally but is not tracked or centrally pinned: {fx}")
        if artifact_field == "patched_fixture_sha256" and "build/" not in fx:
            gaps.append(f"patched fixture pin used for a non-build artifact: {fx}")
        external = EXTERNAL_FIXTURES.get(fx)
        if fx.endswith(".sav") and external and external.get("media_class") != "pristine":
            gaps.append(
                f"original-game save fixture is not strict pristine: {fx} "
                f"({external.get('media_class')})")
    if (prov.get("fixtures") or art.get("fixture_sha256")
            or art.get("patched_fixture_sha256")) and not pinned:
        gaps.append("evidence artifact pins no fixture hashes (DoF #1)")
    for gap in retained_pristine_save_gaps(
            art, require_selection=ev_rel in STRICT_PRISTINE_AGGREGATES):
        gaps.append(f"retained save-origin contradiction: {gap}")

    # 2 machine representation
    for m in f.get("machine") or []:
        if not (ROOT / m).exists():
            gaps.append(f"machine representation missing: {m}")

    # 4 executable guard — and it must really be there
    guard = f.get("guard") or ""
    if not guard:
        gaps.append("no executable guard and no recorded reason")
    else:
        gfile, _, gtest = guard.partition("::")
        gp = ROOT / gfile
        if not gp.exists():
            gaps.append(f"guard file does not exist: {gfile}")
        elif gtest and f"def {gtest}(" not in gp.read_text():
            gaps.append(f"guard test not defined: {guard}")

    # 5 placement + linkage
    canon = f.get("canon") or ""
    cp = ROOT / canon
    if not canon or not cp.exists():
        gaps.append(f"canon/roadmap page missing: {canon!r}")
    elif not canon.startswith("ObsidianVault/Canon/"):
        gaps.append(
            "original-game finding is not placed in ObsidianVault/Canon: "
            f"{canon}")
    elif ev_rel and ev_rel not in cp.read_text():
        gaps.append(f"canon page does not link its evidence artifact ({ev_rel})")

    # 6 MOD consumption contract
    contract = (f.get("mod_contract") or "").strip()
    if len(contract) < 80:
        gaps.append("mod consumption contract missing or too thin")
    elif not re.search(r"UNSAFE|must NOT|NOWHERE|HANGS|does NOT", contract):
        gaps.append("mod contract names no unsafe assumption")

    # 7 durability — tracked in git
    for rel in list(f.get("machine") or []) + ([ev_rel] if ev_rel else []) + \
            ([guard.partition("::")[0]] if guard else []):
        if (ROOT / rel).exists() and not tracked(rel):
            gaps.append(f"UNTRACKED dependency (clean checkout would break): {rel}")

    # 8 confidence + supersession
    if f.get("confidence") not in VOCAB:
        gaps.append(f"confidence not in the evidence vocabulary: {f.get('confidence')!r}")
    if not (f.get("residuals") or "").strip():
        gaps.append("no residuals/next experiment recorded")

    return gaps


def durability_gaps() -> list[str]:
    """Recompute clean-checkout source/fixture freshness, not its summary flag."""
    report, fixture_set = knowledge_closure_audit.build_report()
    blockers = {
        key: value for key, value in report["strict_blockers"].items()
        if key != "knowledge_phases_not_closed" and value
    }
    gaps = [f"{key}: {value}" for key, value in sorted(blockers.items())]

    def without_generated(doc):
        result = dict(doc)
        result.pop("generated", None)
        return result

    retained_report = json.loads(
        (ROOT / "analysis/phase0_2_knowledge_closure_report.json").read_text())
    retained_fixtures = json.loads(FIXTURE_SET.read_text())
    if without_generated(retained_report) != without_generated(report):
        gaps.append("retained Phase-0..2 knowledge report is stale")
    if without_generated(retained_fixtures) != without_generated(fixture_set):
        gaps.append("retained external fixture set is stale")
    return gaps


def debugger_api_documentation_gaps() -> list[str]:
    retained = json.loads(
        (ROOT / "analysis/phase3_duckstation_rpc_manifest.json").read_text())
    markdown = (ROOT / "tools/duckstation_rpc_method_manifest.md").read_text()
    canon = (ROOT / "ObsidianVault/Canon/Indexes/DuckStation_API_Index.md").read_text()
    return rpc_manifest.retained_gaps(retained, markdown, canon)


def main() -> int:
    doc = yaml.safe_load((ROOT / "config" / "phase3_findings.yaml").read_text())
    findings = doc["findings"]
    rows, total_gaps = {}, 0
    for f in findings:
        gaps = audit_one(f)
        total_gaps += len(gaps)
        rows[f["id"]] = {
            "title": f["title"],
            "confidence": f.get("confidence"),
            "finished": not gaps,
            "supersedes": f.get("supersedes") or [],
            "gaps": gaps,
        }
    durable_gaps = durability_gaps()
    total_gaps += len(durable_gaps)
    api_gaps = debugger_api_documentation_gaps()
    total_gaps += len(api_gaps)

    out = {
        "_comment": "Phase-3 knowledge-closure audit against the roadmap's "
                    "Definition of Finished. Each requirement is CHECKED, not "
                    "trusted: guards must really define the named test, canon "
                    "pages must really link their evidence, fixtures must really "
                    "be hash-pinned, dependencies must really be tracked. "
                    "Regenerate: python3 tools/phase3_knowledge_audit.py",
        "generated": date.today().isoformat(),
        "findings": len(findings),
        "finished": sum(1 for r in rows.values() if r["finished"]),
        "open_gaps": total_gaps,
        "durability_gaps": durable_gaps,
        "debugger_api_documentation_gaps": api_gaps,
        "superseded_claims": sorted(
            s for r in rows.values() for s in r["supersedes"]),
        "rows": rows,
    }
    path = ROOT / "analysis" / "phase3_knowledge_audit.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"[knowledge] {out['finished']}/{out['findings']} findings FINISHED "
          f"under the Definition of Finished; {total_gaps} open gaps")
    for fid, r in rows.items():
        mark = "OK " if r["finished"] else "GAP"
        print(f"  {mark} {fid}")
        for g in r["gaps"]:
            print(f"        - {g}")
    for gap in durable_gaps:
        print(f"  GAP clean_checkout_durability: {gap}")
    for gap in api_gaps:
        print(f"  GAP debugger_api_documentation: {gap}")
    return 1 if total_gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
