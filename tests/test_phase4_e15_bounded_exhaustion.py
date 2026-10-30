import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "analysis" / "phase4_e15_bounded_exhaustion.json"

def evidence():
    return json.loads(DATA.read_text(encoding="ascii"))

def test_disposition():
    e=evidence();assert e["status"]=="substantiated_partial";assert e["closure"]=="bounded_exhausted_move_on";assert e["additional_interpreter_movie_required"] is False

def test_nine_corrected_triggers():
    t={x["call_pc"]:x for x in evidence()["resident_triggers"]};assert len(t)==9
    assert (t["0x800500d8"]["movie_id"],t["0x800500d8"]["content"])==(46,"LOSE")
    assert (t["0x80050284"]["movie_id"],t["0x80050284"]["content"])==(40,"LEV15C")
    assert t["0x8005036c"]["movie_id"]==41

def test_tables_and_frontier():
    e=evidence();s=e["selector_tables"];f=e["static_frontier"]
    assert s["level_a_ids_scene_1_through_15"]==list(range(10,40,2));assert s["level_b_ids_scene_1_through_15"]==list(range(11,40,2))
    assert f["resident_fmv_bin_load_calls"]==9 and f["overlay_fmv_bin_load_calls"]==0
    assert f["reachable_words"]==2995 and f["unique_external_targets"]==39
    assert f["indirect_calls"]==0 and f["indirect_jumps"]==2

def test_capsule_and_skip_gate():
    e=evidence();c=e["capsule"];s=e["skip_lifecycle"]
    assert c["domain_hash_mismatches"]==0 and c["executed_outside_static_frontier"]==0
    assert s["frame_limit"]==386 and s["natural_completion_writer_block_hits"]==0
    assert s["abort_branch_hits"]==1 and s["cleanup_block_hits"]==1

def test_c_guards_exist():
    static=(ROOT/"tools/phase4_e15_fmv_static.c").read_text(encoding="ascii")
    capsule=(ROOT/"tools/phase4_e15_capsule.c").read_text(encoding="ascii")
    for x in ("0x8004fb5c","0x800500d8","0x8005036c","raw_jal!=538","ext_n!=39"):assert x in static
    for x in ("checks!=1626","outside","saw_386","expected"):assert x in capsule
