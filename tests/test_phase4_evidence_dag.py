"""Fail-closed tests for the bounded incremental Phase-4 evidence DAG."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_evidence_dag as dag  # noqa: E402


@pytest.mark.local_media
def test_retained_graph_reproduces_and_pilot_distinguishes_identities():
    report = dag.build_report()
    assert report["schema"] == dag.REPORT_SCHEMA
    assert report["summary"]["nodes"] == 6
    assert report["summary"]["live_nodes"] == 0
    promotion = next(row for row in dag.validate_config(dag.load_config(), ROOT)
                     if row["id"] == "promotion_preflight")
    assert promotion["accepted_exit_codes"] == [0, 1]
    assert report["pilot"] == {
        "schema": "abl-phase4-evidence-dag-pilot/1",
        "exact_churn_detected": True,
        "semantic_churn_suppressed": True,
        "semantic_change_detected": True,
        "exact_consumer_invalidated_by_identity_churn": True,
        "semantic_consumer_invalidated_by_identity_churn": False,
        "semantic_consumer_invalidated_by_value_change": True,
    }
    assert (ROOT / "analysis/phase4_evidence_dag.json").read_text() == dag.render(report)


def tiny_graph(tmp_path: Path) -> tuple[Path, dict]:
    for rel, data in {
        "tools/a.py": "print('a')\n",
        "tools/b.py": "print('b')\n",
        "inputs/source.json": '{"value":1}\n',
        "out/a.json": '{"schema":"x/1","generated":"one","value":7}\n',
        "out/b.json": '{"schema":"y/1","value":9}\n',
    }.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    config = {
        "schema": dag.SCHEMA,
        "nodes": [
            {"id": "a", "classification": "static", "generator": "tools/a.py",
             "command": ["{python}", "tools/a.py"],
             "verify_command": ["{python}", "tools/a.py", "--verify"], "depends_on": [],
             "inputs": [{"path": "inputs/source.json", "mode": "semantic"}],
             "outputs": [{"path": "out/a.json", "comparison": "semantic_json"}]},
            {"id": "b", "classification": "static", "generator": "tools/b.py",
             "command": ["{python}", "tools/b.py"],
             "verify_command": ["{python}", "tools/b.py", "--verify"], "depends_on": ["a"],
             "inputs": [{"path": "out/a.json", "mode": "exact"}],
             "outputs": [{"path": "out/b.json", "comparison": "exact"}]},
        ],
    }
    path = tmp_path / "config/dag.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    return path, config


def test_plan_suppresses_presentation_churn_but_exact_consumer_still_runs(tmp_path):
    path, _ = tiny_graph(tmp_path)
    retained = dag.build_report(path, tmp_path)
    output = tmp_path / "out/a.json"
    output.write_text('{"schema":"x/1","generated":"two","value":7}\n')
    current = dag.build_report(path, tmp_path)
    result = dag.plan(current, retained)
    assert "a" not in result["dirty_nodes"]
    assert result["dirty_nodes"] == ["b"]
    assert result["provisional_run_order"] == ["b"]


def test_semantic_input_churn_is_suppressed_and_value_change_propagates(tmp_path):
    path, _ = tiny_graph(tmp_path)
    retained = dag.build_report(path, tmp_path)
    source = tmp_path / "inputs/source.json"
    source.write_text('{"generated":"new","value":1}\n')
    assert dag.plan(dag.build_report(path, tmp_path), retained)["clean"] is True
    source.write_text('{"generated":"new","value":2}\n')
    result = dag.plan(dag.build_report(path, tmp_path), retained)
    assert result["dirty_nodes"] == ["a"]
    assert result["provisional_run_order"] == ["a", "b"]


def test_graph_rejects_missing_edges_cycles_paths_and_live_without_allow(tmp_path):
    path, config = tiny_graph(tmp_path)
    missing = copy.deepcopy(config)
    missing["nodes"][1]["depends_on"] = []
    with pytest.raises(dag.DagError, match="edge is absent"):
        dag.validate_config(missing, tmp_path)
    cycle = copy.deepcopy(config)
    cycle["nodes"][0]["depends_on"] = ["b"]
    with pytest.raises(dag.DagError, match="cycle"):
        dag.validate_config(cycle, tmp_path)
    unsafe = copy.deepcopy(config)
    unsafe["nodes"][0]["inputs"][0]["path"] = "../escape"
    with pytest.raises(dag.DagError, match="unsafe"):
        dag.validate_config(unsafe, tmp_path)
    nodes = dag.validate_config(yaml.safe_load(path.read_text()), tmp_path)
    nodes[0]["classification"] = "live"
    with pytest.raises(dag.DagError, match="explicit --allow-live"):
        dag.run_nodes(nodes, ["a"], root=tmp_path, allowed={"static"})


def test_graph_rejects_duplicate_owners_missing_paths_and_failed_commands(tmp_path):
    path, config = tiny_graph(tmp_path)
    duplicate = copy.deepcopy(config)
    duplicate["nodes"][1]["outputs"][0]["path"] = "out/a.json"
    with pytest.raises(dag.DagError, match="two owners"):
        dag.validate_config(duplicate, tmp_path)

    missing = copy.deepcopy(config)
    missing["nodes"][0]["inputs"][0]["path"] = "inputs/absent.json"
    missing_path = tmp_path / "config/missing.yaml"
    missing_path.write_text(yaml.safe_dump(missing, sort_keys=False))
    with pytest.raises(dag.DagError, match="path is missing"):
        dag.build_report(missing_path, tmp_path)

    (tmp_path / "tools/a.py").write_text("raise SystemExit(7)\n")
    nodes = dag.validate_config(yaml.safe_load(path.read_text()), tmp_path)
    with pytest.raises(dag.DagError, match="generator failed"):
        dag.run_nodes(nodes, ["a"], root=tmp_path, allowed={"static"})

    (tmp_path / "tools/a.py").write_text(
        "import sys\nraise SystemExit(9 if '--verify' in sys.argv else 0)\n")
    nodes = dag.validate_config(yaml.safe_load(path.read_text()), tmp_path)
    with pytest.raises(dag.DagError, match="post-generation verification failed"):
        dag.run_nodes(nodes, ["a"], root=tmp_path, allowed={"static"})


def test_config_only_contract_changes_invalidate_node(tmp_path):
    path, _ = tiny_graph(tmp_path)
    retained = dag.build_report(path, tmp_path)
    config = yaml.safe_load(path.read_text())
    config["nodes"][0]["classification"] = "local_media"
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    result = dag.plan(dag.build_report(path, tmp_path), retained)
    assert result["dirty_nodes"] == ["a"]
    assert result["provisional_run_order"] == ["a", "b"]


def test_tree_identity_detects_names_bytes_and_rejects_symlinks(tmp_path):
    tree = tmp_path / "movies"
    tree.mkdir()
    (tree / "a.movie.json").write_text("one")
    first = dag.tree_identity(tree)
    (tree / "a.movie.json").write_text("two")
    assert dag.tree_identity(tree)["sha256"] != first["sha256"]
    (tree / "b.movie.json").symlink_to(tree / "a.movie.json")
    with pytest.raises(dag.DagError, match="symlink"):
        dag.tree_identity(tree)


def test_incremental_runner_prunes_semantic_noop_descendant(tmp_path):
    path, _ = tiny_graph(tmp_path)
    retained = dag.build_report(path, tmp_path)
    # The source/generator changes, but A's normalized output does not. B reads
    # A semantically in this variant, so the dynamic pass must skip B.
    config = yaml.safe_load(path.read_text())
    config["nodes"][1]["inputs"][0]["mode"] = "semantic"
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    retained = dag.build_report(path, tmp_path)
    (tmp_path / "tools/a.py").write_text(
        "from pathlib import Path\n"
        "Path('out/a.json').write_text('{\\\"schema\\\":\\\"x/1\\\",'"
        "'\\\"generated\\\":\\\"two\\\",\\\"value\\\":7}\\n')\n")
    nodes = dag.validate_config(yaml.safe_load(path.read_text()), tmp_path)
    receipts = dag.run_incremental(nodes, retained, root=tmp_path, allowed={"static"})
    assert receipts[0]["executed"] is True
    assert receipts[1] == {"node": "b", "executed": False,
                           "reason": "identity_clean_after_upstream"}


def test_removed_node_is_never_reported_clean(tmp_path):
    path, config = tiny_graph(tmp_path)
    retained = dag.build_report(path, tmp_path)
    config["nodes"] = config["nodes"][:1]
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    current = dag.build_report(path, tmp_path)
    result = dag.plan(current, retained)
    assert result["removed_nodes"] == ["b"]
    assert result["clean"] is False
    nodes = dag.validate_config(yaml.safe_load(path.read_text()), tmp_path)
    with pytest.raises(dag.DagError, match="removed nodes"):
        dag.run_incremental(nodes, retained, root=tmp_path, allowed={"static"})
