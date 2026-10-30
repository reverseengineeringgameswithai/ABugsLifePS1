from copy import deepcopy

import pytest

import semantic_state as ss


def test_semantic_registry_valid_and_namespaces_separated() -> None:
    doc = ss.load_registry()
    namespaces = {entry["namespace"] for entry in doc["entries"]}
    assert namespaces == {"original", "mod_private", "hypothesis"}
    assert all(entry["address"] is None for entry in doc["entries"]
               if entry["namespace"] == "hypothesis")


def test_hypothesis_cannot_be_promoted_by_registry_edit() -> None:
    doc = ss.load_registry()
    bad = deepcopy(doc)
    hypothesis = next(e for e in bad["entries"] if e["namespace"] == "hypothesis")
    hypothesis["confidence"] = "confirmed"
    with pytest.raises(ss.RegistryError, match="must remain hypothesized"):
        ss.validate_registry(bad)


def test_generators_exclude_hypotheses_from_constants() -> None:
    doc = ss.load_registry()
    emitted = ss.emit_c(doc)
    assert "ORIGINAL_CURRENT_SCENE_ID" in emitted
    assert "HYPOTHESIS_PLAYER_CONTACT_DAMAGE_WRITER" not in emitted



# --- overlay keying -------------------------------------------------------------
# Every overlay is CdRead-loaded at the same VA, so an overlay address is not an
# identity. Keying on (namespace, address) alone made a second overlay's field at a
# shared VA UNRECORDABLE -- the gate rejected it as a duplicate of the first, so the
# registry could hold at most one overlay's view of any VA. The key is now
# (namespace, image, address). Regression: engineering-specs/phase4-overlay-keying-repair.md


def _training(doc):
    return next(e for e in doc["entries"] if e["id"] == "original.training_step")


def test_same_va_in_two_different_overlays_is_recordable() -> None:
    """The defect this keying fixes: 0x800B4A3C is `training_step` (0..13) in
    LEVEL07/LEVEL1.BIN and a separately measured field (0..320 over 1,896 writes) in
    LEVEL02/LEVEL1.BIN. Both must be expressible."""
    doc = ss.load_registry()
    bad = deepcopy(doc)
    second = deepcopy(_training(bad))
    second["id"] = "original.overlay_keying_probe"
    second["image"] = "LEVEL02_LEVEL1"
    bad["entries"].append(second)
    ss.validate_registry(bad)  # must NOT raise


def test_same_va_same_image_is_still_a_duplicate() -> None:
    doc = ss.load_registry()
    bad = deepcopy(doc)
    dupe = deepcopy(_training(bad))
    dupe["id"] = "original.overlay_keying_dupe"
    bad["entries"].append(dupe)
    with pytest.raises(ss.RegistryError, match="duplicates"):
        ss.validate_registry(bad)


def test_overlay_field_requires_an_image() -> None:
    doc = ss.load_registry()
    bad = deepcopy(doc)
    del _training(bad)["image"]
    with pytest.raises(ss.RegistryError, match="requires `image`"):
        ss.validate_registry(bad)


def test_overlay_image_must_be_a_known_blob() -> None:
    doc = ss.load_registry()
    bad = deepcopy(doc)
    _training(bad)["image"] = "LEVEL99_DOES_NOT_EXIST"
    with pytest.raises(ss.RegistryError, match="unknown image"):
        ss.validate_registry(bad)


def test_resident_fields_reject_an_image_tag() -> None:
    """A resident VA IS unique, so tagging one with an image would invent ambiguity."""
    doc = ss.load_registry()
    bad = deepcopy(doc)
    next(e for e in bad["entries"] if e["id"] == "original.current_scene_id")["image"] = "MEMORY"
    with pytest.raises(ss.RegistryError, match="only meaningful for overlay_field"):
        ss.validate_registry(bad)


def test_known_overlay_images_are_derived_not_hardcoded() -> None:
    names = ss.known_overlay_images()
    assert "LEVEL07_LEVEL1" in names and "MEMORY" in names
    assert len(names) >= 12, "overlay image set should come from the committed registries"


def test_declared_image_actually_contains_the_declared_address() -> None:
    """Containment check against the pinned blobs: an image that does not physically
    span the VA cannot own it. Skips if the staging tree is absent."""
    import json
    from pathlib import Path
    root = Path(ss.ROOT)
    contract = root / "analysis" / "phase4_d3_contract.json"
    if not contract.exists():
        pytest.skip("d3 contract absent")
    extents = {i["image"]: (int(i["file_va_base"], 16), i["size"])
               for i in json.loads(contract.read_text())["inputs"]["image_identities"]}
    for entry in ss.load_registry()["entries"]:
        image = entry.get("image")
        if not image or image not in extents:
            continue
        base, size = extents[image]
        addr = entry["address"]
        assert base <= addr <= base + size - 4, (
            f"{entry['id']}: {addr:#x} is outside {image} "
            f"[{base:#x}, {base + size:#x})")
