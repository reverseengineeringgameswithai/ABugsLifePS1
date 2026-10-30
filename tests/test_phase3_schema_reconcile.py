"""Phase-3 WP9: the semantic registry and the record schema must not contradict.

An address that appears in BOTH config/semantic_state.yaml (absolute) and
config/record_types.yaml (record base + field offset) must agree on width. This
test exists because they DIDN'T: berries_in_flight was u16 in one and u8 in the
other, and nothing caught it until an external audit did."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

WIDTH_BYTES = {"u8": 1, "s8": 1, "u16": 2, "s16": 2, "u32": 4, "s32": 4}


def _record_fields_by_abs_addr():
    recs = yaml.safe_load((ROOT / "config" / "record_types.yaml").read_text())
    out = {}
    for r in recs["records"]:
        if r.get("instances", 1) != 1:
            continue                      # only single-instance records have a fixed abs addr
        base = r["base"]
        for f in r["fields"]:
            out[base + f["offset"]] = (r["id"], f["name"], f["width"])
    return out


def test_semantic_and_record_widths_agree():
    sem = yaml.safe_load((ROOT / "config" / "semantic_state.yaml").read_text())
    rec_by_addr = _record_fields_by_abs_addr()
    conflicts = []
    for e in sem["entries"]:
        a = e.get("address")
        if not isinstance(a, int) or e.get("width") not in WIDTH_BYTES:
            continue
        if a in rec_by_addr:
            rid, fname, rwidth = rec_by_addr[a]
            if WIDTH_BYTES[e["width"]] != WIDTH_BYTES[rwidth]:
                conflicts.append(
                    f"0x{a:08X}: semantic {e['id']}={e['width']} vs "
                    f"record {rid}.{fname}={rwidth}")
    assert not conflicts, "schema width contradictions:\n" + "\n".join(conflicts)


def test_the_known_fix_holds():
    """berries_in_flight must be u8 in the registry (a u16 there swallows
    equipped_berry at +0x97)."""
    sem = yaml.safe_load((ROOT / "config" / "semantic_state.yaml").read_text())
    b = next(e for e in sem["entries"]
             if e["id"] == "original.player_berries_in_flight")
    assert b["width"] == "u8"
