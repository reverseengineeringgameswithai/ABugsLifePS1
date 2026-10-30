import hashlib
import json
from pathlib import Path
import subprocess
import sys

from tools import phase4_seed_validation as seed_validation


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "phase4_seed_verifier.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def setup(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    repo, run = tmp_path / "repo", tmp_path / "run"
    (repo / "tools").mkdir(parents=True)
    (repo / "analysis").mkdir()
    (repo / "tests").mkdir()
    run.mkdir()
    script = repo / "tools" / "phase4_seed_falsifiers.py"
    script.write_text(
        "import argparse,json\n"
        "p=argparse.ArgumentParser();p.add_argument('--kind',required=True);a=p.parse_args()\n"
        "print(json.dumps({'schema':'abl-phase4-seed-falsifier-result/1',"
        "'kind':a.kind,'guard_rejected':True,'restored':True},sort_keys=True))\n"
        "print(f'PASS: bounded seed falsifier survived: {a.kind}')\n",
        encoding="utf-8",
    )
    (repo / "tools" / "build_identity.py").write_text(
        "print('[build_identity] PASS: 327/327 staged inputs match their pins')\n")
    (repo / "tools" / "phase3_gate_audit.py").write_text(
        "print('[gate] Phase-3 exit gate: MET')\n")
    (repo / "tools" / "validate_vault.py").write_text(
        "print('ObsidianVault consistency report')\n"
        "print(' dangling_links 0')\nprint(' evidence_policy 0')\n"
        "print(' evidence_deadfile 0')\nprint(' dup_address 0')\n"
        "print(' missing_alias 0')\nprint(' schema 0')\n")
    for rel in (
        "test_phase3_duckstation_rpc_manifest.py",
        "test_phase3_evidence_inventory.py",
        "test_phase3_runtime_guards.py",
        "test_phase3_gate.py",
        "test_phase4_gate.py",
    ):
        (repo / "tests" / rel).write_text(
            "def test_seed_fixture_guard():\n    assert True\n")
    write_json(repo / "analysis" / "phase3_evidence_inventory.json", {
        "closure_ready": True,
        "retained_artifact_fresh": True,
        "summary": {
            key: [] for key in (
                "missing_generator_declarations",
                "stale_generator_declarations", "orphan_artifacts",
                "missing_outputs", "live_artifacts_without_run_provenance",
                "live_artifact_environment_mismatches",
                "live_artifact_source_dependency_mismatches",
                "live_artifact_reproduction_guard_failures",
                "current_live_toolchain_gaps", "tracked_input_mutations",
            )
        },
    })
    write_json(repo / "analysis" / "phase3_gate_audit.json", {
        "gate_met": True,
        "evidence_inventory": {"met": True},
        "decisive_evidence": {"met": True},
        "bullets": {"one": {"met": True}},
    })
    write_json(repo / "analysis" / "phase4_gate.json", {
        "gate_met": False,
        "prerequisites": {
            "phase3_gate_recomputed": True,
            "pristine_build_identity": True,
        },
        "phase3_recomputed": {
            "met": True,
            "inventory": {
                "retained_artifact_fresh": True,
                "summary": {"tracked_input_mutations": []},
            },
        },
        "coverage_counts": {"baseline_rows": 107},
    })
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"],
                   cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    validation = run / "validation.json"
    write_json(validation, seed_validation.capture(repo, commit))
    assert json.loads(validation.read_text())["complete"] is True
    falsifiers = []
    for index, kind in enumerate(
            ("live-helper-drift", "retained-artifact-drift")):
        command = [
            sys.executable, "-B", "tools/phase4_seed_falsifiers.py",
            "--kind", kind,
        ]
        replay = subprocess.run(
            command, cwd=repo, text=True, capture_output=True, check=True)
        receipt = run / f"falsifier-{index}.json"
        write_json(receipt, {
            "schema": "abl-phase4-verifier-falsifier/1",
            "id": kind,
            "candidate_commit": commit,
            "command": command,
            "exit_code": 0,
            "outcome": "survived",
            "output": replay.stdout,
            "output_sha256": hashlib.sha256(
                replay.stdout.encode()).hexdigest(),
        })
        falsifiers.append({
            "id": kind,
            "outcome": "survived",
            "evidence": f"run:{receipt.name}@{sha256(receipt)}",
        })
    decision = run / "decision.json"
    write_json(decision, {
        "phase": 4,
        "status": "open_autonomous",
        "summary": "seed repaired and independently falsified",
        "gaps": [],
        "gap_codes": [],
        "falsifier_results": falsifiers,
        "verified_live_receipt_sha256s": [],
        "method_exceptions": [],
        "evidence": [
            f"repo:{rel}@{sha256(repo / rel)}"
            for rel in (
                "analysis/phase3_evidence_inventory.json",
                "analysis/phase3_gate_audit.json",
                "analysis/phase4_gate.json",
            )
        ],
        "validation": [
            f"run:{validation.name}@{sha256(validation)}"
        ],
        "required_input": "",
        "candidate_commit": commit,
    })
    return repo, run, decision, commit


def run_tool(
        repo: Path, run: Path, decision: Path, commit: str,
) -> subprocess.CompletedProcess:
    return subprocess.run([
        sys.executable, str(TOOL),
        "--decision", str(decision),
        "--candidate", commit,
        "--run-dir", str(run),
        "--tested-root", str(repo),
    ], text=True, capture_output=True)


def test_seed_verifier_replays_two_closed_falsifiers(tmp_path):
    repo, run, decision, commit = setup(tmp_path)
    result = run_tool(repo, run, decision, commit)
    assert result.returncode == 0, result.stdout + result.stderr
    assert subprocess.check_output(
        ["git", "status", "--porcelain=v1"], cwd=repo, text=True) == ""


def test_seed_verifier_rejects_fabricated_falsifier_output(tmp_path):
    repo, run, decision, commit = setup(tmp_path)
    doc = json.loads(decision.read_text())
    receipt_path = run / "falsifier-0.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["output"] = "PASS: fabricated\n"
    receipt["output_sha256"] = hashlib.sha256(
        receipt["output"].encode()).hexdigest()
    write_json(receipt_path, receipt)
    doc["falsifier_results"][0]["evidence"] = \
        f"run:{receipt_path.name}@{sha256(receipt_path)}"
    write_json(decision, doc)
    result = run_tool(repo, run, decision, commit)
    assert result.returncode == 1
    assert "does not reproduce" in result.stdout


def test_seed_verifier_rejects_content_free_reproducible_command(tmp_path):
    repo, run, decision, commit = setup(tmp_path)
    doc = json.loads(decision.read_text())
    receipt_path = run / "falsifier-0.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["command"] = [
        sys.executable, "-c",
        "print('{\"guard_rejected\": true, \"restored\": true}')",
    ]
    replay = subprocess.run(
        receipt["command"], cwd=repo, text=True, capture_output=True, check=True)
    receipt["output"] = replay.stdout
    receipt["output_sha256"] = hashlib.sha256(
        replay.stdout.encode()).hexdigest()
    write_json(receipt_path, receipt)
    doc["falsifier_results"][0]["evidence"] = \
        f"run:{receipt_path.name}@{sha256(receipt_path)}"
    write_json(decision, doc)
    result = run_tool(repo, run, decision, commit)
    assert result.returncode == 1
    assert "immutable bounded mutation" in result.stdout


def test_seed_verifier_rejects_prose_only_evidence(tmp_path):
    repo, run, decision, commit = setup(tmp_path)
    prose = repo / "evidence.log"
    prose.write_text("Trust me: repaired.\n")
    subprocess.run(["git", "add", "evidence.log"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "prose"], cwd=repo, check=True)
    new_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    doc = json.loads(decision.read_text())
    doc["candidate_commit"] = new_commit
    doc["evidence"] = [f"repo:evidence.log@{sha256(prose)}"]
    for item in doc["falsifier_results"]:
        receipt_path = run / item["evidence"].split(":", 1)[1].split("@", 1)[0]
        receipt = json.loads(receipt_path.read_text())
        receipt["candidate_commit"] = new_commit
        write_json(receipt_path, receipt)
        item["evidence"] = f"run:{receipt_path.name}@{sha256(receipt_path)}"
    validation_path = run / "validation.json"
    write_json(validation_path, seed_validation.capture(repo, new_commit))
    doc["validation"] = [
        f"run:{validation_path.name}@{sha256(validation_path)}"
    ]
    write_json(decision, doc)
    result = run_tool(repo, run, decision, new_commit)
    assert result.returncode == 1
    assert "must name the Phase-3 inventory/gate" in result.stdout


def test_seed_verifier_rejects_fabricated_validation_report(tmp_path):
    repo, run, decision, commit = setup(tmp_path)
    doc = json.loads(decision.read_text())
    validation_path = run / "validation.json"
    validation = json.loads(validation_path.read_text())
    validation["checks"][0]["output"] = \
        "[build_identity] PASS: 327/327 staged inputs match their pins\nfabricated\n"
    # Preserve the old canonical hash: replay must reject the authored body.
    write_json(validation_path, validation)
    doc["validation"] = [
        f"run:{validation_path.name}@{sha256(validation_path)}"
    ]
    write_json(decision, doc)
    result = run_tool(repo, run, decision, commit)
    assert result.returncode == 1
    assert "does not reproduce" in result.stdout or \
        "not derived" in result.stdout
