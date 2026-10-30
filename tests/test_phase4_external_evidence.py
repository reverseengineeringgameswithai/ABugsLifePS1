"""Hash-only registry, private receipt, and preservation boundary tests."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_external_evidence as evidence  # noqa: E402


def walk_strings(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)
    elif isinstance(value, str):
        yield value


def make_receipts(tmp_path: Path, failure_domains=("device-a", "device-b")):
    policy = evidence.load_policy()
    blobs = {"synthetic:a": b"alpha\n", "synthetic:b": b"beta\n"}
    registry = evidence._synthetic_registry(blobs, policy)
    remotes, copies = [], []
    for index, domain in enumerate(failure_domains):
        root = tmp_path / f"remote-{index}"
        root.mkdir()
        remote_id = f"r{index}"
        remotes.append({"id": remote_id, "root": str(root), "kind": "offline_local",
                        "public": False, "failure_domain": domain})
        for object_id, blob in blobs.items():
            digest = evidence.sha256_bytes(blob)
            relative = evidence.content_relative(digest)
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
            copies.append({"object_id": object_id, "remote_id": remote_id,
                           "relative_path": relative, "sha256": digest,
                           "bytes": len(blob)})
    receipts = {"schema": evidence.RECEIPT_SCHEMA,
                "registry_sha256": evidence.sha256_bytes(evidence.canonical_json(registry)),
                "remotes": remotes, "copies": copies}
    return registry, receipts, blobs


def _write_copy(root: Path, object_id: str, blob: bytes, remote_id: str) -> dict:
    digest = evidence.sha256_bytes(blob)
    relative = evidence.content_relative(digest)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    return {"object_id": object_id, "remote_id": remote_id,
            "relative_path": relative, "sha256": digest, "bytes": len(blob)}


def test_real_registry_is_byte_exact_hash_only_and_honest_about_availability():
    capsule_set = json.loads(evidence.CAPSULE_SET_PATH.read_text(encoding="utf-8"))
    report = evidence.build_registry(capsule_set, capsule_set_path=evidence.CAPSULE_SET_PATH)
    assert report["schema"] == evidence.REGISTRY_SCHEMA
    expected_objects = 2 + (3 * capsule_set["capsule_count"]) + 3
    if capsule_set["schema"] == "abl-phase4-trace-capsule-set-v2":
        expected_objects += (2 * len(capsule_set.get("capsule_collections") or [])) + 2
    assert report["summary"]["objects"] == expected_objects
    assert report["summary"]["fully_replicated"] == 0
    assert report["summary"]["preservation_ready"] is False
    required_classes = {
        "pristine_media", "capsule_tree", "input_movie", "save_state",
        "emulator_binary", "emulator_source_snapshot",
        "offline_reader"}
    if capsule_set["schema"] == "abl-phase4-trace-capsule-set-v2":
        required_classes.add("emulator_runtime_bundle")
    assert {row["media_class"] for row in report["objects"]} >= required_classes
    assert all(row["availability"] == "unverified" for row in report["objects"])
    assert all(
        (row["verification_manifest_sha256"] is not None) ==
        (row["identity_kind"] == "tree_sha256")
        for row in report["objects"])
    assert not any(value.startswith("/") for value in walk_strings(report))
    assert not any("ALLMODS" in value for value in walk_strings(report))
    assert evidence.REGISTRY_PATH.read_bytes() == evidence.canonical_json(report)


def test_retained_pilot_is_byte_exact_and_detects_all_adversarial_cases():
    report = evidence.build_pilot()
    assert report["schema"] == evidence.PILOT_SCHEMA
    assert report["runtime_evidence"] is False and report["synthetic_only"] is True
    assert report["summary"] == {"objects": 2, "failures": []}
    assert report["cases"]["same_device_directories"]["preservation_ready"] is False
    assert report["cases"]["same_device_directories"]["fully_replicated"] == 0
    assert report["cases"]["distinct_physical_domain_model"] == {
        "independent_failure_domains": ["synthetic-device-1", "synthetic-device-2"],
        "ready_at_two": True,
    }
    assert report["cases"]["duplicate_physical_root_rejected"] is True
    assert report["cases"]["shared_physical_content_rejected"] is True
    assert report["cases"]["tampered_copy"]["preservation_ready"] is False
    assert report["cases"]["public_remote_rejected"] is True
    assert report["cases"]["symlink_rejected"] is True
    assert report["production_contract"]["campaign_promotion"] is False
    assert evidence.PILOT_PATH.read_bytes() == evidence.canonical_json(report)


def test_same_device_directories_and_same_declared_domain_count_once(tmp_path):
    registry, receipts, _ = make_receipts(tmp_path)
    result = evidence.verify_receipts(registry, receipts)
    assert result["summary"] == {"objects": 2, "fully_replicated": 0,
                                 "preservation_ready": False}
    assert all(len(row["independent_failure_domains"]) == 1 for row in result["objects"])
    same_domain = copy.deepcopy(receipts)
    same_domain["remotes"][1]["failure_domain"] = "device-a"
    result = evidence.verify_receipts(registry, same_domain)
    assert result["summary"]["fully_replicated"] == 0
    assert result["summary"]["preservation_ready"] is False


def test_distinct_device_and_declared_domain_model_requires_both_dimensions():
    rows = [
        {"physical_domain": ("st_dev", 1), "failure_domain": "site-a"},
        {"physical_domain": ("st_dev", 2), "failure_domain": "site-b"},
    ]
    assert evidence._independent_failure_domains(rows) == ["site-a", "site-b"]
    same_device = copy.deepcopy(rows)
    same_device[1]["physical_domain"] = ("st_dev", 1)
    assert len(evidence._independent_failure_domains(same_device)) == 1
    same_label = copy.deepcopy(rows)
    same_label[1]["failure_domain"] = "site-a"
    assert evidence._independent_failure_domains(same_label) == ["site-a"]
    unattested = copy.deepcopy(rows)
    unattested[1]["physical_domain"] = None
    assert evidence._independent_failure_domains(unattested) == ["site-a"]


def test_remote_aliases_and_shared_physical_content_cannot_fake_independence(tmp_path):
    registry, receipts, _ = make_receipts(tmp_path)
    duplicate_root = copy.deepcopy(receipts)
    root = Path(duplicate_root["remotes"][0]["root"])
    duplicate_root["remotes"][1]["root"] = str(root / ".." / root.name)
    with pytest.raises(evidence.EvidenceError, match="duplicate physical root"):
        evidence.verify_receipts(registry, duplicate_root)

    first = receipts["copies"][0]
    second = next(row for row in receipts["copies"]
                  if row["object_id"] == first["object_id"] and
                  row["remote_id"] != first["remote_id"])
    roots = {row["id"]: Path(row["root"]) for row in receipts["remotes"]}
    first_path = roots[first["remote_id"]] / first["relative_path"]
    second_path = roots[second["remote_id"]] / second["relative_path"]
    second_path.unlink()
    second_path.hardlink_to(first_path)
    with pytest.raises(evidence.EvidenceError, match="physical content source"):
        evidence.verify_receipts(registry, receipts)


def test_nested_roots_are_rejected_and_private_annex_is_not_independent(tmp_path):
    registry, receipts, blobs = make_receipts(tmp_path)
    outer = Path(receipts["remotes"][0]["root"])
    nested = outer / "nested"
    nested.mkdir()
    receipts["remotes"][1]["root"] = str(nested)
    with pytest.raises(evidence.EvidenceError, match="overlapping physical roots"):
        evidence.verify_receipts(registry, receipts)

    annex_root = tmp_path / "annex"
    annex_root.mkdir()
    _, annex_receipts, _ = make_receipts(annex_root)
    for remote in annex_receipts["remotes"]:
        remote["kind"] = "private_annex"
    result = evidence.verify_receipts(registry, annex_receipts)
    assert result["summary"]["preservation_ready"] is False
    assert all(row["unattested_domain_copies"] == 2 for row in result["objects"])


def test_tamper_symlink_public_remote_secret_and_registry_drift_fail_closed(tmp_path):
    registry, receipts, blobs = make_receipts(tmp_path)
    copy_row = receipts["copies"][-1]
    remote = next(row for row in receipts["remotes"] if row["id"] == copy_row["remote_id"])
    path = Path(remote["root"]) / copy_row["relative_path"]
    path.write_bytes(b"tampered\n")
    result = evidence.verify_receipts(registry, receipts)
    assert not result["summary"]["preservation_ready"] and result["failures"]
    path.unlink()
    other = Path(receipts["remotes"][0]["root"]) / copy_row["relative_path"]
    path.symlink_to(other)
    result = evidence.verify_receipts(registry, receipts)
    assert not result["summary"]["preservation_ready"] and result["failures"]

    public = copy.deepcopy(receipts)
    public["remotes"][0]["public"] = True
    with pytest.raises(evidence.EvidenceError, match="private"):
        evidence.verify_receipts(registry, public)
    secret = copy.deepcopy(receipts)
    secret["api_token"] = "do-not-retain"
    with pytest.raises(evidence.EvidenceError, match="secrets"):
        evidence.verify_receipts(registry, secret)
    drift = copy.deepcopy(receipts)
    drift["registry_sha256"] = "0" * 64
    with pytest.raises(evidence.EvidenceError, match="registry identity"):
        evidence.verify_receipts(registry, drift)
    wrong_layout = copy.deepcopy(receipts)
    wrong_layout["copies"][0]["relative_path"] = "loose/file"
    with pytest.raises(evidence.EvidenceError, match="content-addressed"):
        evidence.verify_receipts(registry, wrong_layout)


def test_capsule_tree_verifier_recomputes_manifest_tree_and_detects_drift(tmp_path):
    capsule = tmp_path / "capsule"
    (capsule / "chunks").mkdir(parents=True)
    files = []
    digest = hashlib.sha256()
    total = 0
    for name, payload in (("chunks/a.json", b"a\n"), ("chunks/b.json", b"b\n")):
        path = capsule / name
        path.write_bytes(payload)
        hashed = evidence.sha256_bytes(payload)
        files.append({"path": name, "sha256": hashed, "bytes": len(payload)})
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(hashed.encode())
        digest.update(b"\0")
        total += len(payload)
    manifest_path = capsule / "manifest.json"
    full_manifest = {
        "schema": "synthetic-capsule/1",
        "capture": {"complete": True, "errors": []},
        "files": files,
    }
    manifest_path.write_text(json.dumps(full_manifest), encoding="utf-8")
    manifest_sha256 = evidence.sha256_file(manifest_path)
    row = evidence._object("capsule:test", "capsule_tree", "tree_sha256",
                           digest.hexdigest(), total, "synthetic", 2,
                           "capsule_manifest_tree_v1", manifest_sha256)
    assert evidence.verify_object(capsule, row) == (digest.hexdigest(), total)
    manifest_path.write_text(json.dumps({"files": files}), encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="manifest identity"):
        evidence.verify_object(capsule, row)
    manifest_path.write_text(json.dumps(full_manifest), encoding="utf-8")
    (capsule / "undeclared.bin").write_bytes(b"undeclared\n")
    with pytest.raises(evidence.EvidenceError, match="exact tree"):
        evidence.verify_object(capsule, row)
    (capsule / "undeclared.bin").unlink()
    (capsule / "undeclared-link").symlink_to(capsule / "chunks/a.json")
    with pytest.raises(evidence.EvidenceError, match="symlink"):
        evidence.verify_object(capsule, row)
    (capsule / "undeclared-link").unlink()
    (capsule / "chunks/a.json").write_bytes(b"drift\n")
    with pytest.raises(evidence.EvidenceError, match="identity"):
        evidence.verify_object(capsule, row)


def test_runtime_tree_binds_manifest_and_rejects_undeclared_entries(tmp_path):
    runtime = tmp_path / "runtime"
    (runtime / "bin").mkdir(parents=True)
    payload = b"runtime\n"
    payload_path = runtime / "bin/runtime.dat"
    payload_path.write_bytes(payload)
    payload_sha256 = evidence.sha256_bytes(payload)
    manifest_path = runtime / "SHA256SUMS"
    manifest_path.write_text(f"{payload_sha256}  bin/runtime.dat\n", encoding="utf-8")
    manifest_sha256 = evidence.sha256_file(manifest_path)
    digest = hashlib.sha256()
    digest.update(b"bin/runtime.dat\0")
    digest.update(payload_sha256.encode())
    digest.update(b"\0")
    digest.update(str(len(payload)).encode())
    digest.update(b"\0")
    row = evidence._object(
        "runtime:test", "emulator_runtime_bundle", "tree_sha256",
        digest.hexdigest(), len(payload), "synthetic", 2,
        "runtime_sha256sums_tree_v1", manifest_sha256)
    assert evidence.verify_object(runtime, row) == (digest.hexdigest(), len(payload))

    (runtime / "undeclared-preload.so").write_bytes(b"preload\n")
    with pytest.raises(evidence.EvidenceError, match="exact tree"):
        evidence.verify_object(runtime, row)
    (runtime / "undeclared-preload.so").unlink()
    (runtime / "undeclared-link").symlink_to(payload_path)
    with pytest.raises(evidence.EvidenceError, match="symlink"):
        evidence.verify_object(runtime, row)
    (runtime / "undeclared-link").unlink()
    manifest_path.write_text(f"{payload_sha256} *bin/runtime.dat\n", encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="identity"):
        evidence.verify_object(runtime, row)


def test_private_annex_plan_is_nonexecuting_and_separates_tree_packaging():
    registry = json.loads(evidence.REGISTRY_PATH.read_text(encoding="utf-8"))
    plan = evidence.annex_plan(registry)
    assert plan["execute_automatically"] is False
    assert plan["public_remote_allowed"] is False
    assert plan["repository_initialization_performed"] is False
    assert "duckstation:binary" in plan["file_objects_ready_for_annex"]
    capsule_set = json.loads(evidence.CAPSULE_SET_PATH.read_text(encoding="utf-8"))
    if capsule_set["schema"] == "abl-phase4-trace-capsule-set-v2":
        assert "duckstation:runtime" in plan["tree_objects_require_external_packaging"]
    else:
        assert "duckstation:runtime" not in plan["tree_objects_require_external_packaging"]
    assert not any("git annex init" in step.lower() for step in plan["steps"])


def test_registry_rejects_authored_availability_weakened_copies_and_unknown_class():
    registry = json.loads(evidence.REGISTRY_PATH.read_text(encoding="utf-8"))
    policy = evidence.load_policy()
    mutations = [
        lambda row: row["objects"][0].update(availability="present"),
        lambda row: row["objects"][0].update(required_copies=1),
        lambda row: row["objects"][0].update(media_class="public_upload"),
        lambda row: row["objects"][0].update(sha256="bad"),
        lambda row: row["objects"].append(copy.deepcopy(row["objects"][0])),
        lambda row: next(obj for obj in row["objects"]
                         if obj["identity_kind"] == "file_sha256").update(
                             verification="capsule_manifest_tree_v1"),
        lambda row: next(obj for obj in row["objects"]
                         if obj["identity_kind"] == "tree_sha256").update(
                             verification_manifest_sha256=None),
    ]
    for mutate in mutations:
        changed = copy.deepcopy(registry)
        mutate(changed)
        with pytest.raises(evidence.EvidenceError, match="."):
            evidence.validate_registry(changed, policy)


def _policy_mutations(value, path=()):
    if type(value) is dict:
        yield path, "unknown-field"
        for key, child in value.items():
            yield from _policy_mutations(child, (*path, key))
    elif type(value) is list:
        yield path, "list-contract"
        for index, child in enumerate(value):
            yield from _policy_mutations(child, (*path, index))
    else:
        yield path, "scalar"


def _mutate_policy_path(doc, path, mutation):
    target = doc
    for part in path:
        target = target[part]
    if mutation == "unknown-field":
        target["unexpected_policy_field"] = True
        return
    parent = doc
    for part in path[:-1]:
        parent = parent[part]
    key = path[-1]
    old = parent[key]
    if mutation == "list-contract":
        parent[key] = [*old, "unexpected-list-value"]
    elif type(old) is bool:
        parent[key] = not old
    elif type(old) is int:
        parent[key] = float(old)
    elif type(old) is str:
        parent[key] = f"{old}-drift"
    else:  # list scalar reached through its integer path
        raise AssertionError(f"unsupported policy scalar {path!r}: {old!r}")


def test_policy_is_one_complete_recursively_typed_and_ordered_contract(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(yaml.safe_dump(evidence.EXPECTED_POLICY, sort_keys=False),
                           encoding="utf-8")
    assert evidence.load_policy(policy_path) == evidence.EXPECTED_POLICY

    cases = list(_policy_mutations(evidence.EXPECTED_POLICY))
    assert cases
    for path, mutation in cases:
        changed = copy.deepcopy(evidence.EXPECTED_POLICY)
        _mutate_policy_path(changed, path, mutation)
        policy_path.write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")
        with pytest.raises(evidence.EvidenceError, match="policy"):
            evidence.load_policy(policy_path)

    reordered = copy.deepcopy(evidence.EXPECTED_POLICY)
    first = next(iter(reordered))
    reordered[first] = reordered.pop(first)
    policy_path.write_text(yaml.safe_dump(reordered, sort_keys=False), encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="fields/order"):
        evidence.load_policy(policy_path)


def test_registry_rejects_every_round6_shape_type_and_authority_mutation():
    registry = json.loads(evidence.REGISTRY_PATH.read_text(encoding="utf-8"))
    policy = evidence.load_policy()
    mutations = [
        lambda row: row.update(availability_assertion=True),
        lambda row: row["objects"][0].update(bytes=True),
        lambda row: row["objects"][0].update(bytes=1.0),
        lambda row: row["objects"][0].update(required_copies=2.0),
        lambda row: row["objects"][0].update(required_copies=True),
        lambda row: row["objects"][0].update(role={"role": "synthetic"}),
        lambda row: row["objects"][0].update(role=""),
        lambda row: row["summary"].update(preservation_ready=True),
        lambda row: row["summary"].update(fully_replicated=1),
        lambda row: row["summary"].update(objects=True),
        lambda row: row["summary"].update(declared_bytes=float(row["summary"]["declared_bytes"])),
        lambda row: row["summary"].update(unknown_size_objects={}),
        lambda row: row["summary"].update(unexpected=True),
        lambda row: row["authority"].update(no_campaign_promotion=False),
        lambda row: row["authority"].update(same_failure_domain_counts_once=False),
        lambda row: row["authority"].update(allow_promotion=True),
        lambda row: row["policy"].update(minimum_independent_copies=True),
        lambda row: row["policy"].update(content_layout="loose/{sha256}"),
        lambda row: row["policy"].update(unexpected=True),
        lambda row: row["source"].update(capsule_count=True),
        lambda row: row["source"].update(unexpected=True),
        lambda row: row["source_dependencies"].update(unexpected="0" * 64),
        lambda row: row["objects"][0].update(unexpected=True),
        lambda row: row["objects"][0].update(sha256="0" * 64),
    ]
    for mutate in mutations:
        changed = copy.deepcopy(registry)
        mutate(changed)
        with pytest.raises(evidence.EvidenceError, match="."):
            evidence.validate_registry(changed, policy)


def test_receipts_reject_complete_top_level_nested_and_scalar_type_drift(tmp_path):
    registry, receipts, _ = make_receipts(tmp_path)
    mutations = [
        lambda row: row.update(unexpected=True),
        lambda row: row.update(schema={"schema": evidence.RECEIPT_SCHEMA}),
        lambda row: row.update(registry_sha256=[row["registry_sha256"]]),
        lambda row: row.update(remotes={}),
        lambda row: row.update(copies={}),
        lambda row: row["remotes"][0].update(unexpected=True),
        lambda row: row["remotes"][0].update(id=["r0"]),
        lambda row: row["remotes"][0].update(root=[row["remotes"][0]["root"]]),
        lambda row: row["remotes"][0].update(kind=["offline_local"]),
        lambda row: row["remotes"][0].update(public=0),
        lambda row: row["remotes"][0].update(failure_domain={"name": "device-a"}),
        lambda row: row["copies"][0].update(unexpected=True),
        lambda row: row["copies"][0].update(object_id=["synthetic:a"]),
        lambda row: row["copies"][0].update(remote_id=["r0"]),
        lambda row: row["copies"][0].update(relative_path=[row["copies"][0]["relative_path"]]),
        lambda row: row["copies"][0].update(sha256=[row["copies"][0]["sha256"]]),
        lambda row: row["copies"][0].update(bytes=True),
        lambda row: row["copies"][0].update(bytes=float(row["copies"][0]["bytes"])),
    ]
    for mutate in mutations:
        changed = copy.deepcopy(receipts)
        mutate(changed)
        with pytest.raises(evidence.EvidenceError, match="."):
            evidence.verify_receipts(registry, changed)


def test_two_real_st_dev_copies_cannot_turn_bool_or_float_counts_into_readiness(tmp_path):
    blob = b"x"  # one byte makes Python's historical True == 1 alias explicit.
    policy = evidence.load_policy()
    registry = evidence._synthetic_registry({"synthetic:a": blob}, policy)
    local_root = tmp_path / "local-remote"
    local_root.mkdir()
    with tempfile.TemporaryDirectory(prefix="abl-phase4-r6-", dir="/dev/shm") as shm_name:
        shm_root = Path(shm_name)
        assert local_root.stat().st_dev != shm_root.stat().st_dev
        remotes = [
            {"id": "local", "root": str(local_root), "kind": "offline_local",
             "public": False, "failure_domain": "local-device"},
            {"id": "shm", "root": str(shm_root), "kind": "offline_removable",
             "public": False, "failure_domain": "shm-device"},
        ]
        copies = [
            _write_copy(local_root, "synthetic:a", blob, "local"),
            _write_copy(shm_root, "synthetic:a", blob, "shm"),
        ]
        receipts = {
            "schema": evidence.RECEIPT_SCHEMA,
            "registry_sha256": evidence.sha256_bytes(evidence.canonical_json(registry)),
            "remotes": remotes,
            "copies": copies,
        }
        baseline = evidence.verify_receipts(registry, receipts)
        assert baseline["summary"] == {
            "objects": 1, "fully_replicated": 1, "preservation_ready": True}

        for field, malformed in (("bytes", True), ("bytes", 1.0),
                                 ("required_copies", True), ("required_copies", 2.0)):
            changed_registry = copy.deepcopy(registry)
            changed_registry["objects"][0][field] = malformed
            changed_receipts = copy.deepcopy(receipts)
            changed_receipts["registry_sha256"] = evidence.sha256_bytes(
                evidence.canonical_json(changed_registry))
            with pytest.raises(evidence.EvidenceError, match="."):
                evidence.verify_receipts(changed_registry, changed_receipts)

        for malformed in (True, 1.0):
            changed_receipts = copy.deepcopy(receipts)
            for copy_row in changed_receipts["copies"]:
                copy_row["bytes"] = malformed
            with pytest.raises(evidence.EvidenceError, match="byte"):
                evidence.verify_receipts(registry, changed_receipts)
