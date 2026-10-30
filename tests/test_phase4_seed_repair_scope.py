import json
import hashlib
from pathlib import Path
import subprocess
import sys

from tools import phase4_seed_repair_scope as seed_scope


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "phase4_seed_repair_scope.py"


def debt(state: str = "gap") -> dict:
    dimensions = {
        name: {"state": state, "basis": "fixture", "errors": []}
        for name in (
            "original_oracle", "typed_state", "original_interfaces",
            "lifecycle", "source_closure", "cross_system_behavior",
            "campaign_breadth", "complete_frontier", "durable_evidence",
        )
    }
    rows = [
        {
            "row_id": f"R{index:03d}",
            "campaign_id": "campaign",
            "family": "family",
            "name": f"row {index}",
            "completion_state": "open",
            "dimensions": dimensions,
            "counts": {"met": 0, "not_applicable": 0, "remaining": 9},
            "next_lane": "static",
            "next_lane_reason": "test",
            "next_action": "test",
            "capsule_count": 0,
            "movie_count": 0,
            "prior_offline_analysis_count": 0,
            "dependency_unlock_count": 0,
        }
        for index in range(107)
    ]
    return {
        "schema": "abl-phase4-closure-debt/1",
        "valid": True,
        "errors": [],
        "dimension_order": list(dimensions),
        "scheduler": {
            "selected_campaigns": [{"campaign_id": "campaign", "rows": ["R000"]}]
        },
        "rows": rows,
    }


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def init_repo(path: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"],
                   cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True)
    (path / "analysis").mkdir()
    (path / "config").mkdir()
    (path / "ObsidianVault" / "Experiments").mkdir(parents=True)
    (path / "ObsidianVault" / "Playbooks" /
     "Game Solving Roadmap").mkdir(parents=True)
    (path / "src_re").mkdir()
    (path / "tests").mkdir()
    (path / "tools").mkdir()
    (path / "analysis" / "phase3_evidence.json").write_text("old\n")
    (path / "analysis" / "phase4_campaign.json").write_text("old\n")
    (path / "src_re" / "campaign.c").write_text("int campaign;\n")
    (path / "tools" / "phase3_fixture.py").write_text("# fixture\n")
    (path / "tools" / "phase3_shared.py").write_text("# shared\n")
    (path / "tools" / "knowledge_closure_audit.py").write_text(
        '''import argparse
import ast
import fnmatch
import re
import subprocess
from collections import defaultdict

preservation_indexes = {
        "phase4_movie_inventory.json",
}


def preserve_semantic_receipt_date(path: Path, doc: dict) -> dict:
    """Keep an existing receipt date when only the wall clock changed."""
    if not path.is_file():
        return doc
    try:
        retained = json.loads(path.read_text())
    except json.JSONDecodeError:
        return doc
    retained_semantic = {
        key: value for key, value in retained.items() if key != "generated"}
    computed_semantic = {
        key: value for key, value in doc.items() if key != "generated"}
    if retained_semantic == computed_semantic and isinstance(
            retained.get("generated"), str):
        doc["generated"] = retained["generated"]
    return doc
''')
    (path / "tools" / "phase4_method_legacy_live_index.py").write_text(
        "# legacy wall-clock generator\n")
    (path / "tools" / "phase4_seed_repair_scope.py").write_text(
        "# seed scope\n")
    for name in ("phase4_live_escalations.py", "phase4_offline_queue.py"):
        (path / "tools" / name).write_text(
            "#!/usr/bin/env python3\nraise SystemExit(0)\n")
    (path / "tests" / "test_phase4_method_metrics.py").write_text(
        "# method guard\n")
    (path / "tests" / "test_phase4_seed_repair_scope.py").write_text(
        "# scope guard\n")
    (path / "tests" / "test_knowledge_closure.py").write_text(
        '''def test_fixture_discovery_ignores_schema_keys_that_look_like_save_paths():
    fixtures = ["homing_berry.sav"]
    assert fixtures == ["homing_berry.sav"]


''')
    (path / "tests" / "test_phase4_offline_queue.py").write_text(
        '''def test_live_ledger_is_generated_and_retains_executed_missing_capsule_runs():
    selector = {
        "id": "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL",
        "state": "executed",
        "missing_fact_id": "E15/c16-selector40-lifecycle",
        "receipt_plan": {"receipts": [{}, {}]},
        "execution_result": {
            "execution_kind": "v2_receipt_set",
            "control_outcome": "falsified",
            "record_counts": {
                "emulator_launches": 2,
                "completed_atomic_jobs": 4,
                "exact_after_load_writes": 1,
                "lifecycle_observer_events": 0,
                "owned_pids_stopped": 2,
                "admissible_live_receipts": 0,
            },
            "banked_analysis": {
                "path": "analysis/phase4_fmv_c16_selector_control_result.json",
                "sha256":
                    "bd8a8fba7aeb81d5ccaaf974de457e284a744e2fc9f26750843147769c802159",
            },
        },
    }
    document = {
        "entries": [
            *[
                {"state": "executed", "execution_result": {}}
                for _ in range(18)
            ],
            selector,
        ],
        "counts": {"entries": 19, "executed": 19, "planned": 0},
    }
    executed = [entry for entry in document["entries"] if entry["state"] == "executed"]
    planned = [entry for entry in document["entries"] if entry["state"] == "planned"]
    assert len(executed) == 18
    assert [entry["id"] for entry in planned] == [
        "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL",
    ]
    menu_v2_runs = [
        entry for entry in executed
        if entry["execution_result"].get("execution_kind") ==
        "v2_receipt_set"]
    planned = document["entries"][-1]
    assert planned["id"] == \\
        "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL"
    assert planned["state"] == "planned"
    assert planned["missing_fact_id"] == "E15/c16-selector40-lifecycle"
    assert len(planned["receipt_plan"]["receipts"]) == 2
    assert document["counts"] == {"entries": 19, "executed": 18, "planned": 1}
''')
    write_json(path / "analysis" / "phase4_method_legacy_live_index.json", {
        "schema": "abl-phase4-method-legacy-live-index/2",
        "generated": "2026-07-26",
        "entries": [{"historical_execution": "unchanged"}],
    })
    write_json(path / "analysis" / "phase4_offline_opportunity_queue.json", {
        "inputs": {"fixture_audit_sha256": "0" * 64},
        "rows": {"R000": {"classification": "offline_partial"}},
    })
    result_path = \
        path / "analysis" / "phase4_fmv_c16_selector_control_result.json"
    write_json(result_path, {
        "schema": "abl-phase4-fmv-c16-selector-control-result/1",
        "valid": True,
        "claim_boundary": {"live_receipts_admissible": False},
    })
    result_sha = hashlib.sha256(result_path.read_bytes()).hexdigest()
    write_json(path / "analysis" / "phase4_live_escalations.json", {
        "schema": "abl-phase4-live-escalations/1",
        "inputs": {"queue_sha256": "1" * 64},
        "entries": [
            *[
                {
                    "id": f"P4-OLD-{index}",
                    "state": "executed",
                    "execution_result": {"observed": "unchanged"},
                    "derived_post_run_audit": {
                        "queue_source_hashes": {
                            "fixture_audit_sha256": "0" * 64,
                        },
                    },
                }
                for index in range(18)
            ],
            {
                "id": "P4-ITER96-E15-C16-SELECTOR-LIFECYCLE-CONTROL",
                "state": "executed",
                "execution_result": {
                    "execution_kind": "v2_receipt_set",
                    "control_outcome": "falsified",
                    "record_counts": {
                        "admissible_live_receipts": 0,
                        "lifecycle_observer_events": 0,
                    },
                    "banked_analysis": {
                        "path":
                            "analysis/phase4_fmv_c16_selector_control_result.json",
                        "sha256": result_sha,
                    },
                },
            },
        ],
        "counts": {"entries": 19, "executed": 19, "planned": 0},
    })
    write_json(path / "analysis" / "phase4_closure_debt.json", debt())
    write_json(path / "analysis" / "phase0_2_external_fixture_set.json", {
        "entries": {"fixture.sav": {"sha256": "0" * 64}},
    })
    write_json(path / "analysis" / "phase0_2_knowledge_closure_report.json", {
        "strict_blockers": {},
    })
    for relative in (
        "config/phase4_campaigns.yaml",
        "config/phase4_fmv_c16_selector_control_result.yaml",
        "config/phase4_live_escalations.yaml",
        ("ObsidianVault/Experiments/"
         "EXP_2026-07-27_phase4_fmv_c16_selector_control_falsified.md"),
        ("ObsidianVault/Playbooks/Game Solving Roadmap/"
         "Game Solving Campaign - FMV Playback and Skip.md"),
        ("ObsidianVault/Playbooks/Game Solving Roadmap/"
         "Phase 4 - Solve Every Gameplay and Engine Subsystem.md"),
    ):
        (path / relative).write_text("retained behavior\n")
    write_json(path / "analysis" / "phase4_campaign_inventory.json", {
        "structural_ready": True,
        "closure_ready": True,
        "schemas": [],
        "tests": [
            "tests/test_phase4_offline_queue.py",
            "tests/test_phase4_seed_repair_scope.py",
        ],
        "notes": [],
        "generators": {
            "tools/phase4_method_legacy_live_index.py": {
                "outputs": [{
                    "path": "analysis/phase4_method_legacy_live_index.json",
                }],
            },
            "tools/phase4_seed_repair_scope.py": {"outputs": []},
            "tools/knowledge_closure_audit.py": {"outputs": []},
            "tools/phase4_offline_queue.py": {
                "outputs": [{
                    "path":
                        "analysis/phase4_offline_opportunity_queue.json",
                }],
            },
            "tools/phase4_live_escalations.py": {
                "outputs": [{
                    "path": "analysis/phase4_live_escalations.json",
                }],
            },
        },
        "rows": {
            f"R{index:03d}": {
                "source_surfaces": (
                    [{"semantic_c": ["src_re/campaign.c"], "asm": []}]
                    if index == 0 else []
                ),
                "frontier": {"functions": [], "state": []},
            }
            for index in range(107)
        },
    })
    write_json(path / "analysis" / "phase3_evidence_inventory.json", {
        "generators": {
            "tools/phase3_fixture.py": {
                "shared_dependencies": [{
                    "path": "tools/phase3_shared.py",
                    "sha256": hashlib.sha256(
                        (path / "tools" / "phase3_shared.py").read_bytes()
                    ).hexdigest(),
                }],
                "source_path_literals": [],
                "guards": [],
                "notes": [],
                "outputs": [{
                    "path": "analysis/phase3_evidence.json",
                    "tracked": True,
                    "sha256": "0" * 64,
                }],
            },
        },
        "summary": {
            "missing_generator_declarations": [],
            "stale_generator_declarations": [],
            "orphan_artifacts": [],
            "missing_outputs": [],
        },
        "compatibility_external_fixture_set": {
            "replay_artifact_sha256": "1" * 64,
        },
        "compatibility_knowledge_report": {
            "replay_artifact_sha256": "2" * 64,
        },
    })
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=path, check=True)
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()


def commit_live_partition_guard_repair(repo: Path) -> None:
    test = repo / "tests" / "test_phase4_offline_queue.py"
    test.write_text(seed_scope._expected_live_ledger_guard(test.read_text()))
    for rel in (
        "tools/phase4_seed_repair_scope.py",
        "tests/test_phase4_seed_repair_scope.py",
    ):
        guard = repo / rel
        guard.write_text(guard.read_text() + "# live partition guard\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "repair live partition guard"],
        cwd=repo, check=True,
    )


def commit_fixture_index_control_repair(repo: Path) -> None:
    source = repo / "tools" / "knowledge_closure_audit.py"
    source.write_text(seed_scope._expected_fixture_index_source(
        source.read_text()))
    guard = repo / "tests" / "test_knowledge_closure.py"
    guard.write_text(seed_scope._expected_fixture_index_guard(
        guard.read_text()))
    (repo / "tools" / "phase4_seed_repair_scope.py").write_text(
        "# fixture_index_control_repair\n")
    (repo / "tests" / "test_phase4_seed_repair_scope.py").write_text(
        "# test_scope_admits_exact_fixture_index_control_repair\n"
        "# test_scope_rejects_fixture_index_control_repair_with_extra_"
        "source_drift\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "repair fixture index control"],
        cwd=repo, check=True,
    )


def write_stable_legacy_generator(repo: Path) -> None:
    (repo / "tools" / "phase4_method_legacy_live_index.py").write_text(
        """#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

INDEX_CREATED = "2026-07-26"
OUTPUT = Path(__file__).resolve().parents[1] / "analysis" / \
    "phase4_method_legacy_live_index.json"


def build():
    return {
        "schema": "abl-phase4-method-legacy-live-index/2",
        "generated": INDEX_CREATED,
        "entries": [{"historical_execution": "unchanged"}],
    }


parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
if args.check and json.loads(OUTPUT.read_text()) != build():
    raise SystemExit(1)
""")


def commit_legacy_control_repair(repo: Path) -> None:
    write_stable_legacy_generator(repo)
    for rel in (
        "tools/phase4_seed_repair_scope.py",
        "tests/test_phase4_method_metrics.py",
        "tests/test_phase4_seed_repair_scope.py",
    ):
        path = repo / rel
        path.write_text(path.read_text() + "# rollover guard\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "stabilize legacy control"],
        cwd=repo, check=True,
    )


def prepare_dependency_only_legacy_index_base(repo: Path) -> str:
    banked = repo / "analysis" / "retained_banked_analysis.json"
    write_json(banked, {
        "schema": "retained-test-evidence/1",
        "behavioral_payload": "unchanged",
    })
    banked_sha = hashlib.sha256(banked.read_bytes()).hexdigest()
    live_path = repo / "analysis" / "phase4_live_escalations.json"
    live = json.loads(live_path.read_text())
    live["entries"][0]["execution_result"] = {
        "observed": "unchanged",
        "banked_analysis": {
            "path": "analysis/retained_banked_analysis.json",
            "sha256": banked_sha,
        },
    }
    write_json(live_path, live)
    generator = repo / "tools" / "phase4_method_legacy_live_index.py"
    generator.write_text(
        """#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "analysis" / "phase4_live_escalations.json"
OUTPUT = ROOT / "analysis" / "phase4_method_legacy_live_index.json"
INDEX_CREATED = "2026-07-26"
LEGACY_ID = "P4-OLD-0"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False,
    ).encode()


def build():
    source = json.loads(SOURCE.read_text())
    raw = next(row for row in source["entries"] if row["id"] == LEGACY_ID)
    projected = {
        key: value for key, value in raw.items()
        if key != "derived_post_run_audit"
    }
    return {
        "schema": "abl-phase4-method-legacy-live-index/2",
        "generated": INDEX_CREATED,
        "source": {
            "path": "analysis/phase4_live_escalations.json",
            "baseline_sha256": "1" * 64,
            "projection": "exclude-derived-post-run-audit/1",
            "legacy_ids": [LEGACY_ID],
        },
        "entries": [{
            "escalation_id": LEGACY_ID,
            "target_row": "R000",
            "state": "executed",
            "normalization": "conservative_deny",
            "media_sha256": None,
            "movie_sha256": None,
            "state_sha256": None,
            "domain": None,
            "window": None,
            "source_entry_sha256": hashlib.sha256(
                canonical(projected)).hexdigest(),
        }],
        "counts": {
            "entries": 1, "normalized": 0, "conservative_deny": 1,
        },
        "complete": True,
        "errors": [],
    }


parser = argparse.ArgumentParser()
parser.add_argument("--write", action="store_true")
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
document = build()
if args.write:
    OUTPUT.write_text(json.dumps(document, indent=2) + "\\n")
if args.check and json.loads(OUTPUT.read_text()) != document:
    raise SystemExit(1)
""")
    document = {
        "schema": "abl-phase4-method-legacy-live-index/2",
        "generated": "2026-07-26",
        "source": {
            "path": "analysis/phase4_live_escalations.json",
            "baseline_sha256": "1" * 64,
            "projection": "exclude-derived-post-run-audit/1",
            "legacy_ids": ["P4-OLD-0"],
        },
        "entries": [{
            "escalation_id": "P4-OLD-0",
            "target_row": "R000",
            "state": "executed",
            "normalization": "conservative_deny",
            "media_sha256": None,
            "movie_sha256": None,
            "state_sha256": None,
            "domain": None,
            "window": None,
            "source_entry_sha256": "0" * 64,
        }],
        "counts": {
            "entries": 1, "normalized": 0, "conservative_deny": 1,
        },
        "complete": True,
        "errors": [],
    }
    index = repo / "analysis" / "phase4_method_legacy_live_index.json"
    write_json(index, document)
    write_json(
        repo / "analysis" / "phase4_upstream_dependency_reconciliation.json",
        {
            "schema": "abl-phase4-upstream-dependency-reconciliation/1",
            "valid": True,
            "errors": [],
            "joined_live_escalation_only_sha_leaves_changed": True,
            "joined_live_escalation_pins": [{
                "entry_id": "P4-OLD-0",
                "pin_kind": "controlled_banked_analysis",
                "path": "analysis/retained_banked_analysis.json",
                "sha256_after": banked_sha,
                "behavioral_payload_preserved": True,
            }],
            "artifacts": [{
                "path": "analysis/retained_banked_analysis.json",
                "artifact_sha256_after": banked_sha,
                "normalized_runtime_payload_sha256": "2" * 64,
                "only_dependency_metadata_or_joined_identity_changed": True,
                "historical_run_provenance_preserved": True,
            }],
        },
    )
    stale_index_sha = hashlib.sha256(index.read_bytes()).hexdigest()
    write_json(
        repo / "analysis" / "phase4_assertion_pin_reconciliation.json",
        {
            "schema": "abl-phase4-assertion-pin-reconciliation/2",
            "valid": True,
            "errors": [],
            "identity_artifacts": [{
                "path": "analysis/phase4_method_legacy_live_index.json",
                "sha256": stale_index_sha,
            }],
        },
    )
    (repo / "tools" / "phase4_reconcile_assertion_pins.py").write_text(
        """#!/usr/bin/env python3
# analysis/phase4_method_legacy_live_index.json
raise SystemExit(0)
""")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "prepare stale dependency projection"],
        cwd=repo, check=True,
    )
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def commit_dependency_only_legacy_index_repair(repo: Path) -> None:
    subprocess.run(
        [sys.executable, "tools/phase4_method_legacy_live_index.py", "--write"],
        cwd=repo, check=True,
    )
    for rel, marker in (
        (
            "tests/test_phase4_method_metrics.py",
            "# assert retained == legacy.build()\n",
        ),
        (
            "tests/test_phase4_seed_repair_scope.py",
            "# test_scope_admits_dependency_only_legacy_index_refresh\n"
            "# test_scope_rejects_dependency_legacy_refresh_with_changed_"
            "normalized_payload\n"
            "# test_exact_pc_legacy_consumer_normalizes_only_index_identity\n",
        ),
        (
            "tools/phase4_seed_repair_scope.py",
            "# dependency-only legacy projection scope\n",
        ),
    ):
        path = repo / rel
        path.write_text(path.read_text() + marker)
    index = repo / "analysis" / "phase4_method_legacy_live_index.json"
    report = json.loads(
        (repo / "analysis" /
         "phase4_assertion_pin_reconciliation.json").read_text())
    report["identity_artifacts"][0]["sha256"] = hashlib.sha256(
        index.read_bytes()).hexdigest()
    write_json(
        repo / "analysis" / "phase4_assertion_pin_reconciliation.json",
        report,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "repair dependency projection"],
        cwd=repo, check=True,
    )


def run_scope(
        repo: Path, base: str, before: Path, after: Path, out: Path,
) -> subprocess.CompletedProcess:
    candidate = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    return subprocess.run(
        [
            sys.executable, str(TOOL), "--repo", str(repo),
            "--base", base, "--candidate", candidate,
            "--debt-before", str(before), "--debt-after", str(after),
            "--out", str(out),
        ],
        text=True,
        capture_output=True,
    )


def test_scope_allows_phase3_repair_with_unchanged_phase4_debt(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    (repo / "analysis" / "phase3_evidence.json").write_text("replayed\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "repair phase3"], cwd=repo, check=True)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(out.read_text())["complete"] is True


def test_scope_admits_exact_fixture_index_control_repair(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    commit_fixture_index_control_repair(repo)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["fixture_index_control_repair"]["admitted"] is True
    assert report["fixture_index_control_repair"]["gaps"] == []


def test_scope_rejects_fixture_index_control_repair_with_extra_source_drift(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    commit_fixture_index_control_repair(repo)
    source = repo / "tools" / "knowledge_closure_audit.py"
    source.write_text(source.read_text() + "# unrelated weakening\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "weaken fixture index repair"],
        cwd=repo, check=True,
    )
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 1
    assert report["fixture_index_control_repair"]["admitted"] is False
    assert any("changed beyond" in gap
               for gap in report["fixture_index_control_repair"]["gaps"])
    assert "tools/knowledge_closure_audit.py" in \
        report["forbidden_phase4_changes"]


def test_scope_admits_only_complete_behavior_neutral_legacy_control_repair(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    commit_legacy_control_repair(repo)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["legacy_index_control_repair"]["admitted"] is True
    assert report["legacy_index_control_repair"]["gaps"] == []


def test_scope_admits_dependency_only_legacy_index_refresh(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    init_repo(repo)
    base = prepare_dependency_only_legacy_index_base(repo)
    commit_dependency_only_legacy_index_repair(repo)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["legacy_index_dependency_repair"]["admitted"] is True
    assert report["legacy_index_dependency_repair"]["gaps"] == []


def test_legacy_consumer_config_normalizes_nested_staged_admission():
    assert "analysis/phase4_upstream_dependency_reconciliation.json" in \
        seed_scope.LEGACY_INDEX_DEPENDENCY_REPAIR_CONSUMER_PATHS
    before = {
        "staged_successor": {
            "method_admission": {
                "validator": {"path": "validator.py", "sha256": "1" * 64},
                "legacy_index": {"path": "index.json", "sha256": "2" * 64},
                "overlapping_entry": {"id": "retained"},
            },
        },
    }
    after = json.loads(json.dumps(before))
    admission = after["staged_successor"]["method_admission"]
    admission["validator"]["sha256"] = "3" * 64
    admission["legacy_index"]["sha256"] = "4" * 64

    assert seed_scope._normalized_legacy_consumer_config(before) == \
        seed_scope._normalized_legacy_consumer_config(after)
    after["staged_successor"]["method_admission"]["overlapping_entry"][
        "id"] = "rewritten"
    assert seed_scope._normalized_legacy_consumer_config(before) != \
        seed_scope._normalized_legacy_consumer_config(after)


def test_exact_pc_legacy_consumer_normalizes_only_index_identity():
    assert seed_scope.LEGACY_INDEX_DEPENDENCY_CHAIN_PATHS == {
        "analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json",
        "analysis/phase4_fmv_levelb_transition_relocalization.json",
        "config/phase4_fmv_levelb_transition_relocalization.yaml",
        "config/phase4_fmv_levelb_two_pc_first_hit.yaml",
        "config/phase4_fmv_levelb_two_pc_first_hit_runtime.yaml",
        "analysis/phase4_fmv_levelb_two_pc_first_hit.json",
        "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json",
        "config/phase4_fmv_levelb_pre15792_partition.yaml",
        "analysis/phase4_fmv_levelb_pre15792_partition.json",
        "config/phase4_fmv_frame_sync_wait_ownership.yaml",
        "analysis/phase4_fmv_frame_sync_wait_ownership.json",
    }
    before = {
        "source_dependencies": {
            "analysis/phase4_method_legacy_live_index.json": "1" * 64,
            "tools/phase4_method_metrics.py": "2" * 64,
        },
        "claim_boundary": {"dimension_promoted": False},
    }
    after = json.loads(json.dumps(before))
    after["source_dependencies"][
        "analysis/phase4_method_legacy_live_index.json"] = "3" * 64
    assert seed_scope._normalized_legacy_index_dependency(before) == \
        seed_scope._normalized_legacy_index_dependency(after)

    after["claim_boundary"]["dimension_promoted"] = True
    assert seed_scope._normalized_legacy_index_dependency(before) != \
        seed_scope._normalized_legacy_index_dependency(after)


def test_generated_live_projection_normalizes_only_declared_joined_identities():
    before = {
        "inputs": {"queue_sha256": "1" * 64},
        "entries": [{
            "id": "P4-ITER91",
            "state": "executed",
            "execution_result": {
                "control_outcome": "falsified",
                "banked_analysis": {
                    "path": "analysis/retained.json",
                    "sha256": "2" * 64,
                },
            },
            "derived_post_run_audit": {"current_hashes": "old"},
        }],
    }
    after = json.loads(json.dumps(before))
    after["inputs"]["queue_sha256"] = "3" * 64
    after["entries"][0]["execution_result"]["banked_analysis"]["sha256"] = \
        "4" * 64
    after["entries"][0]["derived_post_run_audit"]["current_hashes"] = "new"
    replacements = {
        "2" * 64: "<current:analysis/retained.json>",
        "4" * 64: "<current:analysis/retained.json>",
    }
    assert seed_scope._generated_dependency_projection(
        "analysis/phase4_live_escalations.json", before, replacements,
    ) == seed_scope._generated_dependency_projection(
        "analysis/phase4_live_escalations.json", after, replacements,
    )

    after["entries"][0]["execution_result"]["control_outcome"] = "accepted"
    assert seed_scope._generated_dependency_projection(
        "analysis/phase4_live_escalations.json", before, replacements,
    ) != seed_scope._generated_dependency_projection(
        "analysis/phase4_live_escalations.json", after, replacements,
    )


def test_guard_source_normalizes_only_declared_joined_identities():
    before = 'assert sha256 == "' + "1" * 64 + '"\nassert outcome == "falsified"\n'
    after = 'assert sha256 == "' + "2" * 64 + '"\nassert outcome == "falsified"\n'
    replacements = {
        "1" * 64: "<current:analysis/retained.json>",
        "2" * 64: "<current:analysis/retained.json>",
    }
    assert seed_scope._replace_text_identities(
        before, replacements) == seed_scope._replace_text_identities(
            after, replacements)
    assert seed_scope._replace_text_identities(
        before, replacements) != seed_scope._replace_text_identities(
            after.replace("falsified", "accepted"), replacements)


def test_scope_rejects_dependency_legacy_refresh_with_live_payload_drift(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    init_repo(repo)
    base = prepare_dependency_only_legacy_index_base(repo)
    commit_dependency_only_legacy_index_repair(repo)
    live = repo / "analysis" / "phase4_live_escalations.json"
    document = json.loads(live.read_text())
    document["entries"][0]["execution_result"]["observed"] = "rewritten"
    write_json(live, document)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "rewrite retained live payload"],
        cwd=repo, check=True,
    )
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 1
    assert report["legacy_index_dependency_repair"]["admitted"] is False
    assert any(
        "changed a retained live execution/control leaf" in gap
        for gap in report["legacy_index_dependency_repair"]["gaps"])


def test_scope_rejects_dependency_legacy_refresh_without_payload_proof(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    init_repo(repo)
    base = prepare_dependency_only_legacy_index_base(repo)
    commit_dependency_only_legacy_index_repair(repo)
    reconciliation = (
        repo / "analysis" /
        "phase4_upstream_dependency_reconciliation.json")
    document = json.loads(reconciliation.read_text())
    document["artifacts"][0]["historical_run_provenance_preserved"] = False
    write_json(reconciliation, document)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "drop retained payload proof"],
        cwd=repo, check=True,
    )
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 1
    assert report["legacy_index_dependency_repair"]["admitted"] is False
    assert any(
        "normalized-payload and historical-provenance proof" in gap
        for gap in report["legacy_index_dependency_repair"]["gaps"])


def test_scope_rejects_dependency_legacy_refresh_with_changed_normalized_payload(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    init_repo(repo)
    base = prepare_dependency_only_legacy_index_base(repo)
    commit_dependency_only_legacy_index_repair(repo)
    reconciliation = (
        repo / "analysis" /
        "phase4_upstream_dependency_reconciliation.json")
    document = json.loads(reconciliation.read_text())
    document["artifacts"][0]["normalized_runtime_payload_sha256"] = "3" * 64
    write_json(reconciliation, document)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "rewrite normalized retained payload"],
        cwd=repo, check=True,
    )
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 1
    assert report["legacy_index_dependency_repair"]["admitted"] is False
    assert any(
        "does not preserve the immutable-base normalized runtime payload" in gap
        for gap in report["legacy_index_dependency_repair"]["gaps"])


def test_scope_admits_only_exact_behavior_neutral_live_partition_guard_repair(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    commit_live_partition_guard_repair(repo)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["live_ledger_partition_guard_repair"]["admitted"] is True
    assert report["live_ledger_partition_guard_repair"]["gaps"] == []


def test_scope_rejects_live_partition_guard_repair_with_extra_test_drift(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    commit_live_partition_guard_repair(repo)
    guard = repo / "tests" / "test_phase4_offline_queue.py"
    guard.write_text(guard.read_text() + "# unrelated weakening\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "weaken repaired guard"],
        cwd=repo, check=True,
    )
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 1
    assert report["live_ledger_partition_guard_repair"]["admitted"] is False
    assert any("changed beyond" in gap for gap in
               report["live_ledger_partition_guard_repair"]["gaps"])
    assert "tests/test_phase4_offline_queue.py" in \
        report["forbidden_phase4_changes"]


def test_scope_rejects_live_partition_guard_repair_with_execution_drift(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    commit_live_partition_guard_repair(repo)
    live = repo / "analysis" / "phase4_live_escalations.json"
    document = json.loads(live.read_text())
    document["entries"][-1]["execution_result"]["control_outcome"] = "accepted"
    write_json(live, document)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "rewrite live outcome"],
        cwd=repo, check=True,
    )
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 1
    assert report["live_ledger_partition_guard_repair"]["admitted"] is False
    assert any("changed retained" in gap or "exact 19-executed" in gap
               for gap in
               report["live_ledger_partition_guard_repair"]["gaps"])
    assert "analysis/phase4_live_escalations.json" in \
        report["forbidden_phase4_changes"]


def test_scope_rejects_legacy_control_repair_that_changes_retained_evidence(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    commit_legacy_control_repair(repo)
    index = repo / "analysis" / "phase4_method_legacy_live_index.json"
    document = json.loads(index.read_text())
    document["entries"][0]["historical_execution"] = "rewritten"
    write_json(index, document)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "rewrite retained evidence"],
        cwd=repo, check=True,
    )
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 1
    assert report["legacy_index_control_repair"]["admitted"] is False
    assert any("historical evidence" in gap
               for gap in report["legacy_index_control_repair"]["gaps"])
    assert "analysis/phase4_method_legacy_live_index.json" in \
        report["forbidden_phase4_changes"]


def test_scope_admits_hash_only_queue_and_live_audit_dependency_refresh(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    queue = repo / "analysis" / "phase4_offline_opportunity_queue.json"
    queue_doc = json.loads(queue.read_text())
    queue_doc["inputs"]["fixture_audit_sha256"] = "2" * 64
    write_json(queue, queue_doc)
    live = repo / "analysis" / "phase4_live_escalations.json"
    live_doc = json.loads(live.read_text())
    live_doc["inputs"]["queue_sha256"] = "3" * 64
    live_doc["entries"][0]["derived_post_run_audit"][
        "queue_source_hashes"]["fixture_audit_sha256"] = "2" * 64
    write_json(live, live_doc)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "refresh dependency joins"],
        cwd=repo, check=True,
    )
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 0, result.stdout + result.stderr
    assert report["phase4_dependency_refresh"]["admitted"] is True
    assert report["phase4_dependency_refresh"]["gaps"] == []


def test_scope_rejects_dependency_refresh_that_rewrites_execution_evidence(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    queue = repo / "analysis" / "phase4_offline_opportunity_queue.json"
    queue_doc = json.loads(queue.read_text())
    queue_doc["inputs"]["fixture_audit_sha256"] = "2" * 64
    write_json(queue, queue_doc)
    live = repo / "analysis" / "phase4_live_escalations.json"
    live_doc = json.loads(live.read_text())
    live_doc["inputs"]["queue_sha256"] = "3" * 64
    live_doc["entries"][0]["derived_post_run_audit"][
        "queue_source_hashes"]["fixture_audit_sha256"] = "2" * 64
    live_doc["entries"][0]["execution_result"]["observed"] = "rewritten"
    write_json(live, live_doc)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "rewrite execution evidence"],
        cwd=repo, check=True,
    )
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    report = json.loads(out.read_text())
    assert result.returncode == 1
    assert report["phase4_dependency_refresh"]["admitted"] is False
    assert any("execution" in gap
               for gap in report["phase4_dependency_refresh"]["gaps"])
    assert "analysis/phase4_live_escalations.json" in \
        report["forbidden_phase4_changes"]


def test_scope_accepts_real_hash_pinned_dependency_object_on_noop(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(out.read_text())["complete"] is True


def test_scope_rejects_phase4_campaign_file_change(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    (repo / "analysis" / "phase4_campaign.json").write_text("advanced\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "advance phase4"], cwd=repo, check=True)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    assert result.returncode == 1
    assert json.loads(out.read_text())["forbidden_phase4_changes"] == [
        "analysis/phase4_campaign.json"
    ]


def test_scope_rejects_phase4_dimension_change(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    (repo / "analysis" / "phase3_evidence.json").write_text("replayed\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "repair"], cwd=repo, check=True)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    changed = debt()
    changed["rows"][0]["dimensions"]["typed_state"]["state"] = "met"
    write_json(after, changed)
    result = run_scope(repo, base, before, after, out)
    assert result.returncode == 1
    assert json.loads(out.read_text())["debt_projection_equal"] is False


def test_scope_rejects_inventory_bound_campaign_source_without_phase4_name(
        tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    (repo / "src_re" / "campaign.c").write_text("int campaign = 1;\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "campaign work"], cwd=repo, check=True)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    assert result.returncode == 1
    assert json.loads(out.read_text())["forbidden_phase4_changes"] == [
        "src_re/campaign.c"
    ]


def test_scope_rejects_phase3_allowlisted_phase4_protected_overlap(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    inventory_path = repo / "analysis" / "phase3_evidence_inventory.json"
    inventory = json.loads(inventory_path.read_text())
    inventory["generators"]["tools/phase3_fixture.py"][
        "source_path_literals"
    ] = ["src_re/campaign.c"]
    write_json(inventory_path, inventory)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "--amend", "-qm", "base with overlap"],
        cwd=repo, check=True,
    )
    base = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    (repo / "src_re" / "campaign.c").write_text("int campaign = 1;\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "campaign work"], cwd=repo, check=True)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    assert result.returncode == 1
    assert json.loads(out.read_text())["forbidden_phase4_changes"] == [
        "src_re/campaign.c"
    ]


def test_scope_rejects_new_uninventoried_semantic_source(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    base = init_repo(repo)
    smuggled = repo / "src_re" / "fmv_smuggled_campaign.c"
    smuggled.write_text("int fmv_campaign_progress;\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "smuggled campaign work"],
                   cwd=repo, check=True)
    before, after, out = tmp_path / "before.json", tmp_path / "after.json", \
        tmp_path / "out.json"
    write_json(before, debt())
    write_json(after, debt())
    result = run_scope(repo, base, before, after, out)
    assert result.returncode == 1
    assert json.loads(out.read_text())["forbidden_phase4_changes"] == [
        "src_re/fmv_smuggled_campaign.c"
    ]
