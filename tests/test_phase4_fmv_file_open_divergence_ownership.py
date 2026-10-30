from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_file_open_divergence_ownership as ownership  # noqa: E402


def test_historical_endpoint_is_reclassified_without_dimension_promotion():
    document = ownership.build()
    capture = document["retained_capture"]
    assert capture["address"] == "0x800CAC08"
    assert capture["historical_label"] == "selected_frame_limit"
    assert capture["historical_label_is_semantic"] is False
    assert capture["positive"] == {
        "decoded": {"height": 240, "width": 24},
        "hex_le": "1800f000",
    }
    assert capture["native_negative"] == {
        "decoded": {"height": 128, "width": 24},
        "hex_le": "18008000",
    }
    assert capture["selected_frame_limit_difference_claimed"] is False
    assert document["typed_reclassification"]["actual_selected_frame_limit"] == {
        "address": "0x80131EEE",
        "captured_by_retained_control": False,
        "type": "s16",
        "writer": "0x800B6DC0",
    }
    assert document["claim_boundary"] == {
        "dimension_promoted": False,
        "endpoint_semantics_closed": True,
        "not_claimed": [
            "the exact runtime writer of the native height-128 endpoint",
            "a naturally failed file handle or native failure policy",
            "a selected-frame-limit difference",
            "lifecycle or any other nine-dimension promotion",
        ],
        "runtime_writer_closed": False,
        "selected_frame_limit_interpretation_superseded": True,
    }
    assert document["dimension_boundary"]["next_lane"] == "live"
    assert ownership.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


def test_static_owner_falsifier_preserves_the_unattributed_runtime_value():
    document = ownership.build()
    frontier = document["runtime_writer_frontier"]
    assert frontier["classified_direct_height_writers"] == ["0x800B6F18"]
    assert frontier["classified_direct_height_writer_value"] == 240
    assert frontier["native_height_128_writer_attributed"] is False
    assert frontier["positive_height_240_equals_static_initializer"] is True
    assert frontier["offline_index_result"] == \
        "exact_field_address_and_owner_absent"
    assert frontier["missing_domain"].startswith("instruction_or_DMA_attributed")
    assert document["falsifier"]["outcome"] == "falsified"
    assert document["falsifier"]["failed"][
        "exact_native_height_writer_attributed"
    ] is False


def test_closed_offline_receipt_proves_the_index_does_not_name_the_field():
    source = ownership.build()["inputs"]["offline_index_query"]
    assert source["external_index_sha256"] == \
        "e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab"
    assert source["exact_terms_found"] == 0
    assert source["exact_address_or_owner_named"] is False
    assert source["receipt"]["sha256"] == \
        "fb014629ad46e76e85f7b8f6c46fc05ef9702b1856da0289f378425f0949f40a"


@pytest.mark.local_media
@pytest.mark.parametrize("pc", [0x800B6DC0, 0x800B6F18, 0x800B6F40])
def test_each_distinct_field_writer_mutation_fails_closed(pc):
    data = bytearray(ownership.FMV_PATH.read_bytes())
    data[pc - ownership.FMV_BASE] ^= 1
    with pytest.raises(
        ValueError, match="FMV divergence owner opcode drifted"
    ):
        ownership.build(fmv_data=bytes(data), verify_identity=False)


def test_capture_decoder_rejects_wrong_size_and_endianness_claims():
    with pytest.raises(ValueError, match="not four bytes"):
        ownership._decode_rect("1800")
    assert ownership._decode_rect("f0001800") != {
        "width": 24,
        "height": 240,
    }
