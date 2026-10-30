"""Phase-3 guard: function-pointer fields of the typed records.

The point of this one is the OPTIONALITY. `actor_record +0x7C` is a real callback
the game calls through — but only ~61% of live actors have one. A mod that assumes
the field is always populated will call through garbage in the other 39%."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
F = json.loads((ROOT / "analysis" / "phase3_fn_ptr_fields.json").read_text())
RECS = yaml.safe_load((ROOT / "config" / "record_types.yaml").read_text())["records"]
JALR = json.loads(
    (ROOT / "analysis" / "phase3_jalr_callbacks.json").read_text())


def test_evidence_is_broad_and_pinned():
    assert F["anchors_used"] >= 40
    assert F["fixture_sha256"], "no fixture pins (DoF #1)"


def test_actor_event_callback_is_real_and_called():
    a = F["records"]["actor_record"]["+0x7C"]
    assert a["instances_seen"] >= 500          # not a one-off coincidence
    assert a["distinct_handlers"] >= 5
    # independent corroboration: a jalr really calls through this offset
    assert a["called_by_a_jalr_at_this_offset"] is True
    assert "+0x7C" in JALR["struct_field_offsets"]


def test_the_callback_is_OPTIONAL():
    """61% populated — so the field is optional and every caller must null-check.
    If this ever reads ~1.0 the contract changes and mods may assume it."""
    a = F["records"]["actor_record"]["+0x7C"]
    assert 0.4 <= a["hit_rate"] <= 0.9, a["hit_rate"]


def test_it_is_typed_with_the_optionality_recorded():
    actor = next(r for r in RECS if r["id"] == "actor_record")
    fld = {f["name"]: f for f in actor["fields"]}["event_callback"]
    assert fld["offset"] == 0x7C
    assert "OPTIONAL" in fld["note"] and "null-check" in fld["note"]
