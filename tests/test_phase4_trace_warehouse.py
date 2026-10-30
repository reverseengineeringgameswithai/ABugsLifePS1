"""Contract, mutation, and external-boundary tests for the trace warehouse."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_trace_warehouse as warehouse  # noqa: E402


def make_inputs(tmp_path: Path) -> tuple[Path, Path, dict, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    capsule_set = warehouse._synthetic_capsule_set()
    capsule_path = tmp_path / "capsules.json"
    capsule_path.write_bytes(warehouse.canonical_json(capsule_set))
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    events = [
        warehouse._event("p", "positive.movie", "positive", 2, "ram", "hp", "0a", "09"),
        warehouse._event("n", "negative.movie", "negative", 3, "ram", "hp", "0a", "0a"),
        warehouse._event("c", "control.movie", "control", 3, "block", "0x1", None, None,
                         "0x1", 4),
    ]
    raw = b"".join(json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                   for row in events)
    partition = dataset / "events.jsonl"
    partition.write_bytes(raw)
    bindings = []
    for capsule_id, cohort, row in zip(("p", "n", "c"),
                                       ("positive", "negative", "control"),
                                       capsule_set["capsules"]):
        bindings.append({"id": capsule_id, "movie": row["movie"], "cohort": cohort,
                         "capsule_manifest_sha256": row["capsule_manifest_sha256"],
                         "capsule_tree_sha256": row["capsule_tree_sha256"]})
    manifest = {
        "schema": warehouse.IMPORT_SCHEMA,
        "capsule_set_sha256": warehouse.sha256_bytes(warehouse.canonical_json(capsule_set)),
        "capsules": bindings,
        "partitions": [{"path": "events.jsonl", "sha256": warehouse.sha256_bytes(raw),
                        "bytes": len(raw), "rows": len(events)}],
    }
    manifest_path = dataset / "import.json"
    manifest_path.write_bytes(warehouse.canonical_json(manifest))
    return manifest_path, capsule_path, manifest, partition


def test_retained_pilot_is_byte_exact_and_non_authoritative():
    report = warehouse.build_pilot()
    assert report["schema"] == warehouse.PILOT_SCHEMA
    assert report["runtime_evidence"] is False
    assert report["engine"] == {"name": "DuckDB", "version": "1.5.5",
                                "extensions_allowed": False}
    assert set(report["queries"]) == set(warehouse.QUERY_SQL)
    assert report["queries"]["first_change"][0]["capsule_id"] == "p"
    assert report["queries"]["block_enrichment"][0] == {
        "block_pc": "0x80010000", "positive_count": 12, "comparison_count": 2}
    assert report["production_contract"]["campaign_promotion"] is False
    assert (ROOT / "analysis/phase4_trace_warehouse_pilot.json").read_bytes() == \
        warehouse.canonical_json(report)


def test_real_retained_capsule_set_is_eligible_but_not_silently_imported():
    policy = warehouse.load_policy()
    doc = json.loads(warehouse.CAPSULE_SET_PATH.read_text(encoding="utf-8"))
    rows = warehouse.validate_capsule_set(doc, policy)
    assert len(rows) == doc["capsule_count"]
    assert doc["schema"] in warehouse.CAPSULE_SET_SCHEMAS
    assert all(row["control_match"] for row in rows.values())


def test_capsule_set_rejects_incomplete_control_truncation_and_repro_drift():
    policy = warehouse.load_policy()
    original = warehouse._synthetic_capsule_set()
    mutations = [
        lambda row: row.update(complete=False),
        lambda row: row["capsules"][0].update(control_match=False),
        lambda row: row["capsules"][0].update(truncated=True),
        lambda row: row["capsules"][0].update(errors=["capture error"]),
        lambda row: row.update(errors=["independent capture failed"]),
        lambda row: row.pop("errors"),
        lambda row: row["reproducibility_comparison"].update(mismatches=["drift"]),
        lambda row: row["reproducibility_comparison"].update(
            frame_chunks_byte_identical=False),
        lambda row: row.update(capsule_count=99),
    ]
    for mutate in mutations:
        changed = copy.deepcopy(original)
        mutate(changed)
        with pytest.raises(warehouse.WarehouseError, match="."):
            warehouse.validate_capsule_set(changed, policy)


def test_capsule_set_rejects_integer_bool_and_row_status_schema_drift():
    policy = warehouse.load_policy()
    original = warehouse._synthetic_capsule_set()
    mutations = [
        lambda row: row.update(capsule_count=True, capsules=row["capsules"][:1]),
        lambda row: row["capsules"][0].update(frames=True),
        lambda row: row["capsules"][0].pop("frames"),
        lambda row: row["capsules"][0].update(truncated=False),
        lambda row: row["capsules"][0].update(errors=[]),
        lambda row: row["capsules"][0].update(truncated="false", errors={}),
        lambda row: row["capsules"][0].update(status="complete"),
        lambda row: row["capsules"][0].update(capture={"status": "complete"}),
        lambda row: row["capsules"][0].update(error=None),
        lambda row: row["capsules"][0].update(preservation_required=1),
        lambda row: row["capsules"][0]["start_state"].update(bytes=True),
        lambda row: row["capsules"][0]["start_state"].update(extra=False),
    ]
    for mutate in mutations:
        changed = copy.deepcopy(original)
        mutate(changed)
        with pytest.raises(warehouse.WarehouseError, match="."):
            warehouse.validate_capsule_set(changed, policy)


def test_capsule_rows_match_exact_supported_retained_schema():
    policy = warehouse.load_policy()
    synthetic = warehouse._synthetic_capsule_set()
    retained = json.loads(warehouse.CAPSULE_SET_PATH.read_text(encoding="utf-8"))
    for document in (synthetic, retained):
        validated = warehouse.validate_capsule_set(document, policy)
        assert document["schema"] in warehouse.CAPSULE_SET_SCHEMAS
        assert len(validated) == document["capsule_count"]
        assert all(set(row) == warehouse.CAPSULE_ROW_KEYS for row in validated.values())
        assert all(set(row["start_state"]) == warehouse.CAPSULE_START_STATE_KEYS
                   for row in validated.values())


def test_policy_is_recursively_exact_typed_and_fail_closed(tmp_path):
    original = copy.deepcopy(warehouse.EXPECTED_POLICY)
    mutations = [
        lambda row: row["input"].update(require_complete_capsule_set=1),
        lambda row: row["input"].update(require_control_match=1),
        lambda row: row["input"].update(reject_truncation_or_errors=1),
        lambda row: row["input"].update(max_partitions=True),
        lambda row: row["input"].update(max_partition_bytes=1073741825),
        lambda row: row["input"].update(max_rows=False),
        lambda row: row["input"]["allowed_domains"].append("status"),
        lambda row: row["input"].update(allowed_cohorts=["positive", "control"]),
        lambda row: row["input"].update(schema="abl-phase4-trace-warehouse-import/2"),
        lambda row: row["output"].update(external_only=1),
        lambda row: row["output"].update(overwrite=0),
        lambda row: row["output"].update(compression="uncompressed"),
        lambda row: row["output"]["files"].update(database="inside.duckdb"),
        lambda row: row["queries"][3].update(id="cross_capsule"),
        lambda row: row["authority"].update(frame_boundary_only=1),
        lambda row: row["authority"].update(exact_causality=True),
        lambda row: row["authority"].update(campaign_promotion=True),
        lambda row: row["authority"].update(
            live_escalation_requires_named_missing_domain=1),
        lambda row: row["engine"].update(extensions_allowed=0),
        lambda row: row.update(extra_security_boundary=False),
    ]
    for index, mutate in enumerate(mutations):
        changed = copy.deepcopy(original)
        mutate(changed)
        path = tmp_path / f"policy-{index}.yaml"
        path.write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")
        with pytest.raises(warehouse.WarehouseError, match="drifted"):
            warehouse.load_policy(path)


def test_build_writes_only_external_database_parquet_and_manifest(tmp_path):
    manifest_path, capsule_path, _, _ = make_inputs(tmp_path)
    output = tmp_path / "warehouse"
    report = warehouse.build_warehouse(manifest_path, capsule_path, output)
    assert report["schema"] == warehouse.EXTERNAL_MANIFEST_SCHEMA
    assert report["summary"] == {"events": 3, "domains": ["block", "ram"]}
    assert report["event_frame"] == warehouse.EVENT_FRAME_CONTRACT
    assert report["authority"]["exact_causality"] is False
    assert (output / "trace_warehouse.duckdb").is_file()
    assert (output / "parquet/domain=ram.parquet").is_file()
    assert (output / "trace_warehouse.manifest.json").read_bytes() == \
        warehouse.canonical_json(report)
    with pytest.raises(warehouse.WarehouseError, match="overwrite"):
        warehouse.build_warehouse(manifest_path, capsule_path, output)
    with pytest.raises(warehouse.WarehouseError, match="outside repository"):
        warehouse.build_warehouse(manifest_path, capsule_path,
                                  ROOT / "analysis/forbidden-warehouse")


def test_import_rejects_tamper_binding_unknown_fields_and_symlink(tmp_path):
    manifest_path, capsule_path, manifest, partition = make_inputs(tmp_path)
    policy = warehouse.load_policy()
    capsule_set = json.loads(capsule_path.read_text())

    changed = copy.deepcopy(manifest)
    changed["capsule_set_sha256"] = "0" * 64
    with pytest.raises(warehouse.WarehouseError, match="capsule-set"):
        warehouse.validate_import_manifest(changed, manifest_path, capsule_set, policy)
    changed = copy.deepcopy(manifest)
    changed["capsules"][0]["capsule_tree_sha256"] = "0" * 64
    with pytest.raises(warehouse.WarehouseError, match="tree"):
        warehouse.validate_import_manifest(changed, manifest_path, capsule_set, policy)
    changed = copy.deepcopy(manifest)
    changed["capsules"][0]["extra"] = True
    with pytest.raises(warehouse.WarehouseError, match="fields"):
        warehouse.validate_import_manifest(changed, manifest_path, capsule_set, policy)
    partition.write_bytes(partition.read_bytes() + b"{}\n")
    with pytest.raises(warehouse.WarehouseError, match="byte count"):
        warehouse.validate_import_manifest(manifest, manifest_path, capsule_set, policy)

    manifest_path, capsule_path, manifest, partition = make_inputs(tmp_path / "fresh")
    target = tmp_path / "outside.jsonl"
    target.write_bytes(partition.read_bytes())
    partition.unlink()
    partition.symlink_to(target)
    with pytest.raises(warehouse.WarehouseError, match="symlink"):
        warehouse.validate_import_manifest(
            manifest, manifest_path, json.loads(capsule_path.read_text()), policy)


def test_import_rejects_second_binding_for_same_retained_movie(tmp_path):
    manifest_path, capsule_path, manifest, _ = make_inputs(tmp_path)
    policy = warehouse.load_policy()
    capsule_set = json.loads(capsule_path.read_text())
    duplicate = copy.deepcopy(manifest["capsules"][0])
    duplicate["id"] = "different-capsule-id"
    duplicate["cohort"] = "control"
    manifest["capsules"].append(duplicate)
    with pytest.raises(warehouse.WarehouseError, match="movie.*exactly once"):
        warehouse.validate_import_manifest(
            manifest, manifest_path, capsule_set, policy)


def test_import_and_public_build_require_complete_retained_movie_binding_set(tmp_path):
    manifest_path, capsule_path, manifest, partition = make_inputs(tmp_path)
    policy = warehouse.load_policy()
    capsule_set = json.loads(capsule_path.read_text())

    bindings, partitions = warehouse.validate_import_manifest(
        manifest, manifest_path, capsule_set, policy)
    assert {row["movie"] for row in bindings} == {
        row["movie"] for row in capsule_set["capsules"]}
    assert len(partitions) == 1
    complete_output = tmp_path / "complete-warehouse"
    complete_report = warehouse.build_warehouse(
        manifest_path, capsule_path, complete_output)
    assert complete_report["source"]["capsules"] == capsule_set["capsule_count"]
    assert complete_output.is_dir()

    removed = manifest["capsules"].pop()
    retained_events = [
        json.loads(line) for line in partition.read_text().splitlines()
        if json.loads(line)["capsule_id"] != removed["id"]
    ]
    raw = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for row in retained_events)
    partition.write_bytes(raw)
    manifest["partitions"][0].update(
        sha256=warehouse.sha256_bytes(raw), bytes=len(raw), rows=len(retained_events))

    expected = (
        "complete retained movie set: missing=\\['control\\.movie'\\]; "
        "unexpected=\\[\\]")
    with pytest.raises(warehouse.WarehouseError, match=expected):
        warehouse.validate_import_manifest(
            manifest, manifest_path, capsule_set, policy)

    with_unexpected = copy.deepcopy(manifest)
    template = copy.deepcopy(manifest["capsules"][0])
    for capsule_id, movie in (("unexpected-z", "zeta.movie"),
                              ("unexpected-a", "alpha.movie")):
        binding = copy.deepcopy(template)
        binding.update(id=capsule_id, movie=movie)
        with_unexpected["capsules"].append(binding)
    sorted_identities = (
        "complete retained movie set: missing=\\['control\\.movie'\\]; "
        "unexpected=\\['alpha\\.movie', 'zeta\\.movie'\\]")
    with pytest.raises(warehouse.WarehouseError, match=sorted_identities):
        warehouse.validate_import_manifest(
            with_unexpected, manifest_path, capsule_set, policy)

    manifest_path.write_bytes(warehouse.canonical_json(manifest))
    output = tmp_path / "incomplete-warehouse"
    with pytest.raises(warehouse.WarehouseError, match=expected):
        warehouse.build_warehouse(manifest_path, capsule_path, output)
    assert not output.exists()


def test_import_rejects_noncanonical_alias_and_hardlink_identity(tmp_path):
    manifest_path, capsule_path, manifest, partition = make_inputs(tmp_path)
    policy = warehouse.load_policy()
    capsule_set = json.loads(capsule_path.read_text())

    alias = copy.deepcopy(manifest)
    alias["partitions"][0]["path"] = "./events.jsonl"
    with pytest.raises(warehouse.WarehouseError, match="canonical"):
        warehouse.validate_import_manifest(
            alias, manifest_path, capsule_set, policy)

    hardlink = partition.parent / "events-hardlink.jsonl"
    hardlink.hardlink_to(partition)
    duplicate = copy.deepcopy(manifest["partitions"][0])
    duplicate["path"] = hardlink.name
    manifest["partitions"].append(duplicate)
    with pytest.raises(warehouse.WarehouseError, match="physical partition identity"):
        warehouse.validate_import_manifest(
            manifest, manifest_path, capsule_set, policy)


def test_cross_movie_query_defensively_counts_distinct_movie_not_capsule_id():
    duckdb = warehouse.import_duckdb()
    connection = duckdb.connect(":memory:")
    warehouse._configure(connection)
    connection.execute("""
        CREATE TABLE events (
          capsule_id VARCHAR, movie VARCHAR, cohort VARCHAR, frame UBIGINT,
          domain VARCHAR, key VARCHAR, before_hex VARCHAR, after_hex VARCHAR,
          block_pc VARCHAR, block_count UBIGINT
        )
    """)
    connection.executemany(
        "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("capsule-a", "same.movie", "positive", 1, "ram", "hp",
             "00", "01", None, 0),
            ("capsule-b", "same.movie", "positive", 2, "ram", "hp",
             "01", "02", None, 0),
            ("capsule-c", "other.movie", "control", 3, "ram", "hp",
             "00", "01", None, 0),
        ],
    )
    assert warehouse._rows(connection, "cross_movie")[0]["movies"] == 2
    connection.close()


def test_event_rows_are_strictly_bound_to_capsule_movie_and_cohort(tmp_path):
    manifest_path, capsule_path, manifest, partition = make_inputs(tmp_path)
    policy = warehouse.load_policy()
    capsule_set = json.loads(capsule_path.read_text())
    bindings, partitions = warehouse.validate_import_manifest(
        manifest, manifest_path, capsule_set, policy)
    rows = partition.read_text().splitlines()
    event = json.loads(rows[0])
    event["movie"] = "negative.movie"
    rows[0] = json.dumps(event, sort_keys=True, separators=(",", ":"))
    raw = ("\n".join(rows) + "\n").encode()
    partition.write_bytes(raw)
    partitions[0].update(bytes=len(raw), sha256=warehouse.sha256_bytes(raw), rows=len(rows))
    with pytest.raises(warehouse.WarehouseError, match="binding"):
        warehouse.read_events(partitions, bindings, policy)


def _mutate_first_event(partition: Path, partitions: list[dict], **changes):
    rows = partition.read_text().splitlines()
    event = json.loads(rows[0])
    event.update(changes)
    rows[0] = json.dumps(event, sort_keys=True, separators=(",", ":"))
    raw = ("\n".join(rows) + "\n").encode()
    partition.write_bytes(raw)
    partitions[0].update(bytes=len(raw), sha256=warehouse.sha256_bytes(raw), rows=len(rows))


@pytest.mark.parametrize("frame", [0, 10])
def test_event_frame_accepts_closed_capsule_boundary_span(tmp_path, frame):
    manifest_path, capsule_path, manifest, partition = make_inputs(tmp_path)
    policy = warehouse.load_policy()
    capsule_set = json.loads(capsule_path.read_text())
    bindings, partitions = warehouse.validate_import_manifest(
        manifest, manifest_path, capsule_set, policy)
    _mutate_first_event(partition, partitions, frame=frame)
    events = warehouse.read_events(partitions, bindings, policy)
    assert events[0][3] == frame


@pytest.mark.parametrize("frame", [-1, 1_000_000, True, False])
def test_event_frame_rejects_outside_capsule_boundary_span_and_bool(tmp_path, frame):
    manifest_path, capsule_path, manifest, partition = make_inputs(tmp_path)
    policy = warehouse.load_policy()
    capsule_set = json.loads(capsule_path.read_text())
    bindings, partitions = warehouse.validate_import_manifest(
        manifest, manifest_path, capsule_set, policy)
    _mutate_first_event(partition, partitions, frame=frame)
    message = "integer" if isinstance(frame, bool) else "closed movie-relative"
    with pytest.raises(warehouse.WarehouseError, match=message):
        warehouse.read_events(partitions, bindings, policy)


@pytest.mark.parametrize("boolean", [True, False])
def test_block_and_partition_counts_reject_bool_as_int(tmp_path, boolean):
    manifest_path, capsule_path, manifest, partition = make_inputs(tmp_path)
    policy = warehouse.load_policy()
    capsule_set = json.loads(capsule_path.read_text())

    for field in ("rows", "bytes"):
        changed = copy.deepcopy(manifest)
        changed["partitions"][0][field] = boolean
        with pytest.raises(warehouse.WarehouseError, match="count"):
            warehouse.validate_import_manifest(
                changed, manifest_path, capsule_set, policy)

    bindings, partitions = warehouse.validate_import_manifest(
        manifest, manifest_path, capsule_set, policy)
    _mutate_first_event(partition, partitions, block_count=boolean)
    with pytest.raises(warehouse.WarehouseError, match="block_count"):
        warehouse.read_events(partitions, bindings, policy)
