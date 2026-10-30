"""Read-only schema and deterministic binary-fuzz harness tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import time

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_binary_schema_fuzz as fuzz  # noqa: E402


def test_retained_pilot_is_byte_exact_deterministic_and_synthetic():
    report = fuzz.run_pilot()
    assert report["schema"] == fuzz.PILOT_SCHEMA
    assert report["runtime_evidence"] is False
    assert report["synthetic_only"] is True
    assert report["summary"] == {"schemas": 3, "cases": 285, "failures": []}
    assert all(row["deterministic_replay"] for row in report["targets"])
    assert all(row["classifications"]["crash"] == 0 for row in report["targets"])
    assert all(row["classifications"]["timeout"] == 0 for row in report["targets"])
    assert report["production_contract"]["existing_writers_unchanged"] is True
    assert report["production_contract"]["campaign_promotion"] is False
    assert (ROOT / "analysis/phase4_binary_schema_fuzz_pilot.json").read_bytes() == \
        fuzz.canonical_json(report)


def test_kaitai_schema_set_is_read_only_hash_pinned_and_complete():
    rows = fuzz.validate_kaitai_schemas(fuzz.load_policy())
    assert {row["id"] for row in rows} == fuzz.KNOWN_ADAPTERS
    assert all(row["read_only"] and len(row["sha256"]) == 64 for row in rows)
    assert {row["id"]: row["endian"] for row in rows} == fuzz.EXPECTED_ENDIAN
    for row in rows:
        text = (ROOT / row["path"]).read_text(encoding="utf-8")
        assert "CC0-1.0" in text
        assert "write" not in text.lower()


@pytest.mark.parametrize("adapter", sorted(fuzz.KNOWN_ADAPTERS))
@pytest.mark.parametrize("drift", ["missing", "non_string", "swapped"])
def test_each_kaitai_schema_rejects_endian_drift(tmp_path, monkeypatch, adapter, drift):
    fake_root = tmp_path / "repo"
    schema_root = fake_root / "schemas/phase4"
    schema_root.mkdir(parents=True)
    policy = copy.deepcopy(fuzz.load_policy())
    for row in policy["schemas"]:
        source = ROOT / row["path"]
        copied = fake_root / row["path"]
        copied.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    declaration = next(row for row in policy["schemas"] if row["adapter"] == adapter)
    target = fake_root / declaration["path"]
    doc = yaml.safe_load(target.read_text(encoding="utf-8"))
    if drift == "missing":
        del doc["meta"]["endian"]
    elif drift == "non_string":
        doc["meta"]["endian"] = 1
    else:
        doc["meta"]["endian"] = "be" if fuzz.EXPECTED_ENDIAN[adapter] == "le" else "le"
    target.write_text(yaml.safe_dump(doc), encoding="utf-8")
    monkeypatch.setattr(fuzz, "ROOT", fake_root)
    with pytest.raises(fuzz.FuzzError, match="endian"):
        fuzz.validate_kaitai_schemas(policy)


@pytest.mark.parametrize("adapter", sorted(fuzz.KNOWN_ADAPTERS))
@pytest.mark.parametrize("drift", ["missing", "non_string", "swapped"])
def test_each_schema_declaration_rejects_endian_drift(adapter, drift):
    policy = copy.deepcopy(fuzz.load_policy())
    declaration = next(row for row in policy["schemas"] if row["adapter"] == adapter)
    if drift == "missing":
        del declaration["endian"]
    elif drift == "non_string":
        declaration["endian"] = 1
    else:
        declaration["endian"] = "be" if fuzz.EXPECTED_ENDIAN[adapter] == "le" else "le"
    with pytest.raises(fuzz.FuzzError, match="fields|endian"):
        fuzz.validate_kaitai_schemas(policy)


def test_schema_validation_rejects_wrong_id_forbidden_processing_and_escape(
        tmp_path, monkeypatch):
    fake_root = tmp_path / "repo"
    schema_root = fake_root / "schemas/phase4"
    schema_root.mkdir(parents=True)
    policy = copy.deepcopy(fuzz.load_policy())
    originals = {row["adapter"]: ROOT / row["path"] for row in policy["schemas"]}
    for row in policy["schemas"]:
        target = fake_root / row["path"]
        target.write_text(originals[row["adapter"]].read_text(encoding="utf-8"),
                          encoding="utf-8")
    monkeypatch.setattr(fuzz, "ROOT", fake_root)
    assert len(fuzz.validate_kaitai_schemas(policy)) == 3

    target = fake_root / policy["schemas"][0]["path"]
    doc = yaml.safe_load(target.read_text())
    doc["meta"]["id"] = "wrong"
    target.write_text(yaml.safe_dump(doc), encoding="utf-8")
    with pytest.raises(fuzz.FuzzError, match="meta.id"):
        fuzz.validate_kaitai_schemas(policy)
    doc["meta"]["id"] = fuzz.EXPECTED_SCHEMA_IDS[policy["schemas"][0]["adapter"]]
    doc["process"] = "xor(1)"
    target.write_text(yaml.safe_dump(doc), encoding="utf-8")
    with pytest.raises(fuzz.FuzzError, match="forbidden"):
        fuzz.validate_kaitai_schemas(policy)
    policy["schemas"][0]["path"] = "../escape.ksy"
    with pytest.raises(fuzz.FuzzError, match="unsafe"):
        fuzz.validate_kaitai_schemas(policy)


def test_valid_seeds_parse_and_mutation_corpus_is_stable():
    policy = fuzz.load_policy()
    seeds = fuzz.synthetic_seeds()
    for adapter, seed in seeds.items():
        result = fuzz.run_case(adapter, seed, policy["limits"])
        assert result["status"] == "ok"
        first = fuzz.mutate(seed, policy["limits"]["max_cases_per_target"],
                            policy["limits"]["max_input_bytes"])
        second = fuzz.mutate(seed, policy["limits"]["max_cases_per_target"],
                             policy["limits"]["max_input_bytes"])
        assert first == second
        assert len({fuzz.sha256_bytes(case) for case in first}) == len(first)


def test_declared_output_bomb_and_truncation_are_rejected_not_executed():
    policy = fuzz.load_policy()
    bomb = (policy["limits"]["max_output_bytes"] + 1).to_bytes(4, "big")
    bomb += (0).to_bytes(4, "big") + bytes(6)
    assert fuzz.run_case("level_raw_chunk", bomb, policy["limits"])["status"] == "rejected"
    assert fuzz.run_case("level_raw_container", b"\x00\x00", policy["limits"])[
        "status"] == "rejected"


def _hang(*_args):
    while True:
        time.sleep(0.01)


def _abort(*_args):
    raise KeyboardInterrupt()


def test_child_timeout_and_unexpected_base_exception_fail_closed(monkeypatch):
    limits = copy.deepcopy(fuzz.load_policy()["limits"])
    limits["timeout_ms"] = 50
    monkeypatch.setattr(fuzz, "_execute_adapter", _hang)
    assert fuzz.run_case("seed_table", b"x", limits)["status"] == "timeout"
    monkeypatch.setattr(fuzz, "_execute_adapter", _abort)
    assert fuzz.run_case("seed_table", b"x", limits)["status"] == "crash"


def test_synthetic_corpus_export_is_external_collision_safe_and_manifested(tmp_path):
    output = tmp_path / "corpus"
    report = fuzz.export_synthetic_corpus(output)
    assert report["synthetic_only"] is True and report["files"]
    assert all((output / row["path"]).is_file() for row in report["files"])
    assert all(fuzz.sha256_file(output / row["path"]) == row["sha256"]
               for row in report["files"])
    with pytest.raises(fuzz.FuzzError, match="overwrite"):
        fuzz.export_synthetic_corpus(output)
    with pytest.raises(fuzz.FuzzError, match="outside"):
        fuzz.export_synthetic_corpus(ROOT / "analysis/forbidden-corpus")


def _write_policy(path: Path, policy: dict) -> None:
    path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")


def _adversarial_in_memory_policies():
    """Cover every authority-bearing part of a supplied truthy policy."""
    base = fuzz.load_policy()
    cases = []

    def add(name, policy):
        assert policy
        cases.append(pytest.param(policy, id=name))

    for field in sorted(fuzz.EXPECTED_POLICY_FIELDS):
        policy = copy.deepcopy(base)
        del policy[field]
        add(f"top-missing-{field}", policy)
    policy = copy.deepcopy(base)
    policy["unknown"] = True
    add("top-unknown", policy)
    for value_name, value in (
            ("wrong", "wrong-schema"), ("bool", True), ("float", 1.0)):
        policy = copy.deepcopy(base)
        policy["schema"] = value
        add(f"schema-{value_name}", policy)
    for value_name, value in (
            ("wrong", fuzz.EXPECTED_SEED + 1), ("bool", True),
            ("float", float(fuzz.EXPECTED_SEED)),
            ("string", str(fuzz.EXPECTED_SEED))):
        policy = copy.deepcopy(base)
        policy["seed"] = value
        add(f"seed-{value_name}", policy)

    for value_name, value in (("list", []), ("string", "limits")):
        policy = copy.deepcopy(base)
        policy["limits"] = value
        add(f"limits-container-{value_name}", policy)
    policy = copy.deepcopy(base)
    policy["limits"]["unknown"] = 1
    add("limits-unknown", policy)
    for field, approved in fuzz.EXPECTED_LIMITS.items():
        policy = copy.deepcopy(base)
        del policy["limits"][field]
        add(f"limit-{field}-missing", policy)
        for value_name, value in (
                ("wrong", approved + 1), ("bool", True),
                ("float", float(approved)), ("string", str(approved))):
            policy = copy.deepcopy(base)
            policy["limits"][field] = value
            add(f"limit-{field}-{value_name}", policy)

    for value_name, value in (("dict", {}), ("string", "schemas")):
        policy = copy.deepcopy(base)
        policy["schemas"] = value
        add(f"schemas-container-{value_name}", policy)
    policy = copy.deepcopy(base)
    policy["schemas"].reverse()
    add("schemas-order", policy)
    policy = copy.deepcopy(base)
    policy["schemas"].pop()
    add("schemas-missing-declaration", policy)
    policy = copy.deepcopy(base)
    policy["schemas"].append(copy.deepcopy(policy["schemas"][0]))
    add("schemas-extra-declaration", policy)
    for index, expected in enumerate(fuzz.EXPECTED_SCHEMAS):
        policy = copy.deepcopy(base)
        policy["schemas"][index]["unknown"] = "value"
        add(f"schema-{index}-unknown-field", policy)
        for field in sorted(expected):
            policy = copy.deepcopy(base)
            del policy["schemas"][index][field]
            add(f"schema-{index}-{field}-missing", policy)
            policy = copy.deepcopy(base)
            policy["schemas"][index][field] = True
            add(f"schema-{index}-{field}-bool", policy)
            policy = copy.deepcopy(base)
            if field == "endian":
                policy["schemas"][index][field] = \
                    "be" if expected[field] == "le" else "le"
            else:
                policy["schemas"][index][field] = f"wrong-{field}"
            add(f"schema-{index}-{field}-wrong", policy)

    for value_name, value in (("dict", {}), ("string", "mutations")):
        policy = copy.deepcopy(base)
        policy["mutation_operators"] = value
        add(f"mutations-container-{value_name}", policy)
    policy = copy.deepcopy(base)
    policy["mutation_operators"].reverse()
    add("mutations-order", policy)
    policy = copy.deepcopy(base)
    policy["mutation_operators"].append("unknown")
    add("mutations-extra", policy)
    for index, operator in enumerate(fuzz.EXPECTED_MUTATION_OPERATORS):
        policy = copy.deepcopy(base)
        del policy["mutation_operators"][index]
        add(f"mutation-{operator}-missing", policy)
        policy = copy.deepcopy(base)
        policy["mutation_operators"][index] = True
        add(f"mutation-{operator}-bool", policy)
        policy = copy.deepcopy(base)
        policy["mutation_operators"][index] = f"wrong-{operator}"
        add(f"mutation-{operator}-wrong", policy)

    for value_name, value in (("list", []), ("string", "authority")):
        policy = copy.deepcopy(base)
        policy["policy"] = value
        add(f"authority-container-{value_name}", policy)
    policy = copy.deepcopy(base)
    policy["policy"]["unknown"] = True
    add("authority-unknown", policy)
    for field in fuzz.EXPECTED_AUTHORITY_POLICY:
        policy = copy.deepcopy(base)
        del policy["policy"][field]
        add(f"authority-{field}-missing", policy)
        for value_name, value in (
                ("false", False), ("integer", 1), ("string", "true")):
            policy = copy.deepcopy(base)
            policy["policy"][field] = value
            add(f"authority-{field}-{value_name}", policy)
    return cases


def _must_not_run(*_args, **_kwargs):
    raise AssertionError("invalid supplied policy reached fuzz execution")


@pytest.mark.parametrize("policy", _adversarial_in_memory_policies())
def test_high_level_entrypoints_validate_every_truthy_policy_before_work(
        tmp_path, monkeypatch, policy):
    monkeypatch.setattr(fuzz, "load_policy", _must_not_run)
    monkeypatch.setattr(fuzz, "validate_kaitai_schemas", _must_not_run)
    monkeypatch.setattr(fuzz, "synthetic_seeds", _must_not_run)
    monkeypatch.setattr(fuzz, "run_case", _must_not_run)
    with pytest.raises(fuzz.FuzzError):
        fuzz.run_pilot(policy)
    output = tmp_path / "corpus"
    with pytest.raises(fuzz.FuzzError):
        fuzz.export_synthetic_corpus(output, policy)
    assert not output.exists()


@pytest.mark.parametrize("policy", [
    pytest.param({}, id="empty-dict"),
    pytest.param([], id="empty-list"),
    pytest.param((), id="empty-tuple"),
    pytest.param("", id="empty-string"),
    pytest.param(b"", id="empty-bytes"),
    pytest.param(0, id="zero-int"),
    pytest.param(0.0, id="zero-float"),
    pytest.param(False, id="false-bool"),
    pytest.param(["not-a-policy"], id="truthy-list"),
    pytest.param("not-a-policy", id="truthy-string"),
    pytest.param(1, id="truthy-int"),
])
def test_supplied_non_policy_never_falls_back_to_loading_or_creates_output(
        tmp_path, monkeypatch, policy):
    monkeypatch.setattr(fuzz, "load_policy", _must_not_run)
    monkeypatch.setattr(fuzz, "validate_kaitai_schemas", _must_not_run)
    monkeypatch.setattr(fuzz, "synthetic_seeds", _must_not_run)
    monkeypatch.setattr(fuzz, "run_case", _must_not_run)
    with pytest.raises(fuzz.FuzzError):
        fuzz.run_pilot(policy)
    output = tmp_path / "corpus"
    with pytest.raises(fuzz.FuzzError):
        fuzz.export_synthetic_corpus(output, policy)
    assert not output.exists()


@pytest.mark.parametrize("field", list(fuzz.EXPECTED_LIMITS))
@pytest.mark.parametrize("drift", [
    "missing", "under", "over", "huge", "bool", "float", "string",
])
def test_each_resource_limit_is_exactly_pinned(tmp_path, field, drift):
    policy = copy.deepcopy(fuzz.load_policy())
    approved = fuzz.EXPECTED_LIMITS[field]
    if drift == "missing":
        del policy["limits"][field]
    elif drift == "under":
        policy["limits"][field] = approved - 1
    elif drift == "over":
        policy["limits"][field] = approved + 1
    elif drift == "huge":
        policy["limits"][field] = 10 ** 100
    elif drift == "bool":
        policy["limits"][field] = True
    elif drift == "float":
        policy["limits"][field] = float(approved)
    else:
        policy["limits"][field] = str(approved)
    path = tmp_path / "policy.yaml"
    _write_policy(path, policy)
    with pytest.raises(fuzz.FuzzError, match="limit|limits"):
        fuzz.load_policy(path)


@pytest.mark.parametrize("drift", ["missing", "under", "over", "huge", "bool", "string"])
def test_seed_is_exactly_pinned(tmp_path, drift):
    policy = fuzz.load_policy()
    if drift == "missing":
        del policy["seed"]
    elif drift == "under":
        policy["seed"] = fuzz.EXPECTED_SEED - 1
    elif drift == "over":
        policy["seed"] = fuzz.EXPECTED_SEED + 1
    elif drift == "huge":
        policy["seed"] = 10 ** 100
    elif drift == "bool":
        policy["seed"] = True
    else:
        policy["seed"] = str(fuzz.EXPECTED_SEED)
    path = tmp_path / "policy.yaml"
    _write_policy(path, policy)
    with pytest.raises(fuzz.FuzzError, match="field|seed"):
        fuzz.load_policy(path)


@pytest.mark.parametrize("field", list(fuzz.EXPECTED_AUTHORITY_POLICY))
@pytest.mark.parametrize("drift", ["missing", "false", "integer"])
def test_each_authority_field_is_exact_bool_true(tmp_path, field, drift):
    policy = copy.deepcopy(fuzz.load_policy())
    if drift == "missing":
        del policy["policy"][field]
    elif drift == "false":
        policy["policy"][field] = False
    else:
        # 1 == True in Python; the loader must still reject this type drift.
        policy["policy"][field] = 1
    path = tmp_path / "policy.yaml"
    _write_policy(path, policy)
    with pytest.raises(fuzz.FuzzError, match="authority"):
        fuzz.load_policy(path)


@pytest.mark.parametrize("section", [
    "top_level_extra", "limits_extra", "authority_extra", "schema_path",
    "schema_order", "mutation_order", "mutation_extra",
])
def test_remaining_policy_authority_is_exactly_pinned(tmp_path, section):
    policy = copy.deepcopy(fuzz.load_policy())
    if section == "top_level_extra":
        policy["unbounded_mode"] = True
    elif section == "limits_extra":
        policy["limits"]["worker_count"] = 999999
    elif section == "authority_extra":
        policy["policy"]["allow_in_repository_export"] = True
    elif section == "schema_path":
        policy["schemas"][0]["path"] = "schemas/phase4/other.ksy"
    elif section == "schema_order":
        policy["schemas"].reverse()
    elif section == "mutation_order":
        policy["mutation_operators"].reverse()
    else:
        policy["mutation_operators"].append("random_bytes")
    path = tmp_path / "policy.yaml"
    _write_policy(path, policy)
    with pytest.raises(fuzz.FuzzError, match="fields|declarations|operator"):
        fuzz.load_policy(path)
