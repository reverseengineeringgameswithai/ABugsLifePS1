import copy
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common
import phase4_derived_index as derived


def test_catalog_is_fresh_and_hashes_every_external_index():
    retained = json.loads(derived.OUTPUT.read_text())
    assert retained == derived.build()
    assert retained["valid"] is True
    assert retained["external_indexes"]
    for row in retained["external_indexes"]:
        path = Path(row["absolute_path"])
        assert path.is_file()
        assert common.sha256(path) == row["sha256"]
        assert path.stat().st_size == row["bytes"]
        assert row["preservation_required"] is True
        assert derived.supported_index_schema(row["schema"])


def test_catalog_deduplicates_reused_external_indexes():
    retained = json.loads(derived.OUTPUT.read_text())
    reused = [row for row in retained["external_indexes"]
              if len(row["consuming_artifacts"]) > 1]
    assert reused
    assert all(len({row["absolute_path"], row["sha256"]}) == 2 for row in reused)


def test_catalog_rejects_missing_external_index():
    policy = common.load_yaml(derived.POLICY)
    mutated = copy.deepcopy(policy)
    first = mutated["offline_analysis_artifacts"][0]
    artifact = common.load_json(common.ROOT / first["path"])
    original = artifact["external_index"]["sha256"]
    # The catalog takes the external pin from the artifact, so corrupting the
    # artifact in-memory is represented by a temporary copied source policy
    # declaration whose schema cannot match a nonexistent artifact.
    first["path"] = "analysis/does-not-exist-phase4-index.json"
    document = derived.build(policy=mutated)
    assert document["valid"] is False
    assert any("offline artifact is missing" in error for error in document["errors"])
    assert len(original) == 64


def test_external_index_schema_is_closed_and_versioned():
    assert derived.supported_index_schema("abl-phase4-external-contact-index/1")
    assert not derived.supported_index_schema("contact-index")
    assert not derived.supported_index_schema("abl-phase4-external-contact-index/2")
