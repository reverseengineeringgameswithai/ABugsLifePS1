"""Phase-3 WP4 guard: the indirect CALL sites (jalr) and the callback slots.

These are the game's real extension points — a mod can install a handler by
writing a slot, without patching a single instruction. The guard pins what is
installed, because a mod that redirects a slot must know what it is replacing."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
J = json.loads((ROOT / "analysis" / "phase3_jalr_callbacks.json").read_text())


def test_every_jalr_site_is_classified():
    c = J["classification"]
    assert sum(c.values()) == J["jalr_sites"] == 139
    assert set(c) <= {"global_slot", "struct_field", "call_result", "unresolved"}
    assert c["unresolved"] <= 10          # the honest remainder
    assert J["fixture_sha256"], "no EXE pin (DoF #1)"


def test_callback_slots_resolve_to_real_handlers():
    inst = J["installed_handlers"]
    assert "_error" not in inst, inst
    named = [s for s, i in inst.items() if i.get("is_code") and i.get("handler")]
    assert len(named) >= 15, named
    # the ones a mod is most likely to touch, and most likely to break
    handlers = {i["handler"] for i in inst.values() if i.get("handler")}
    for expect in ("trapIntrVSync", "def_cbsync", "def_cbread"):
        assert expect in handlers, expect


def test_function_pointer_fields_are_reported():
    """A jalr through a struct field means that record HAS a function-pointer
    field — a typed-record fact, not just a dispatch fact."""
    fields = J["struct_field_offsets"]
    assert fields, "no function-pointer fields found"
    assert sum(fields.values()) == J["classification"]["struct_field"]


def test_null_slots_are_not_claimed_to_be_free():
    """12 slots hold NULL at this anchor. Whether the call site guards against
    NULL is UNVERIFIED — the artifact must not present them as safe hooks."""
    nulls = [s for s, i in J["installed_handlers"].items()
             if i.get("value") == "0x00000000"]
    assert nulls
    assert "unverified" in J["_comment"].lower() or "UNVERIFIED" in json.dumps(J)
