#!/usr/bin/env python3
"""Join retained native actor-contact controls to E08 source/type-word identity.

This is a deterministic cross-evidence generator.  It does not replay or mutate
operator fixtures.  Instead it recomputes a lossless join between:

* E08's 605 actor/source observations;
* A04's paired neutral/kick calls to the native proximity updater;
* A06's independent timer-12 contact negatives;
* A05's natural Bonus-1 accepted/expired abdomen-bounce counterfactual; and
* E07's complete selector/program disassembly.

The output deliberately classifies measured contact outcomes, not species names
or final subsystem ownership.  Classes without a direct control stay explicit.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_e08_outcome_join.json"

INPUTS = {
    "props_movers": ROOT / "analysis/phase4_props_movers.json",
    "kick": ROOT / "analysis/phase4_kick.json",
    "downhill_slide": ROOT / "analysis/phase4_downhill_slide.json",
    "abdomen_bounce": ROOT / "analysis/phase4_abdomen_bounce.json",
    "event_vm": ROOT / "analysis/phase4_event_vm.json",
}

PROXIMITY_OWNER = "0x8004abf4"
EXPECTED_REPRESENTATIVES = 28
EXPECTED_TYPE_WORDS = 22
EXPECTED_UNCLASSIFIED_CONTROLLED = 18
EXPECTED_UNCLASSIFIED_WITHOUT_CONTROL = 29


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _flag_class(flags: int) -> str:
    if flags & 0x20:
        return "separate_actor_path_0x20"
    if flags & 0x800:
        return "ordinary_contact_suppressed_0x800"
    if flags & 0x80:
        return "response_only_0x80"
    return "ordinary_damage_kick_response"


def _compact_player(row: dict[str, Any]) -> dict[str, Any]:
    fields = row["fields"]
    return {
        key: fields[key]
        for key in ("kick_timer", "state", "animation", "health", "lives")
        if key in fields
    }


def _compact_actor(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in ("id", "flags", "state", "hp_or_response", "record_sha256")
    }


def _validate_native_call(trial: dict[str, Any], *, label: str) -> None:
    call = trial["call"]
    before = trial["before"]["player"]
    after = trial["after"]["player"]
    status = call["status"]
    if call["address"].lower() != PROXIMITY_OWNER or \
            call["stopped_at"].lower() != call["return_address"].lower() or \
            status.get("paused") is not True or \
            status.get("game_serial") != "SCUS-94288" or \
            before["frame"] != after["frame"] or \
            before["frame"] != status["frame"] or \
            after["cycle"] != status["cycle"]:
        raise SystemExit(f"{label} is not an exact returned native contact call")


def _validate_kick_pair(key: str, trial: dict[str, Any]) -> str:
    neutral = trial["neutral"]
    kick = trial["kick"]
    _validate_native_call(neutral, label=f"A04 {key} neutral")
    _validate_native_call(kick, label=f"A04 {key} kick")
    representative = trial["representative"]
    flags = representative["flags"]
    outcome_class = _flag_class(flags)
    neutral_actor = neutral["after"]["actor"]
    kick_actor = kick["after"]["actor"]
    neutral_player = neutral["after"]["player"]["fields"]
    kick_player = kick["after"]["player"]["fields"]
    if neutral["timer"] != 0 or kick["timer"] != -16:
        raise SystemExit(f"A04 {key} lost the paired timer control")
    if outcome_class == "ordinary_damage_kick_response":
        valid = (
            neutral_actor["state"] == 15 and neutral_player["health"] == 3
            and kick_actor["state"] == 30 and kick_player["health"] == 4
            and kick_player["animation"] == 30
        )
    elif outcome_class == "response_only_0x80":
        valid = kick_actor["state"] == 15 and kick_player["health"] == 4
    else:
        valid = kick_actor["state"] != 30
    if not valid:
        raise SystemExit(f"A04 {key} raw outcomes contradict flags 0x{flags:04X}")
    return outcome_class


def _validate_slide_trial(key: str, trial: dict[str, Any]) -> None:
    _validate_native_call(trial, label=f"A06 {key}")
    before_player = trial["before"]["player"]["fields"]
    actor = trial["after"]["actor"]
    if before_player["action_timer"] != 12 or actor["state"] in {-20, 30}:
        raise SystemExit(f"A06 {key} no-offense contact control changed")


def _representative_core(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in ("anchor", "save", "table_index", "pointer", "id", "flags")
    }


def _actor_index(props: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    observations = 0
    for trial in props["live"]["breadth"]["trials"]:
        save = trial["save"]
        for actor in trial["before"]["actors"]["records"]:
            key = (save, actor["address"])
            if key in index:
                raise SystemExit(f"duplicate E08 actor identity: {key}")
            index[key] = actor
            observations += 1
    summary = props["live"]["source_actor_clusters"]["summary"]
    if observations != 605 or summary["observations"] != observations or \
            summary["behavior_classes"] != 54 or \
            summary["all_actor_source_ids_match"] is not True:
        raise SystemExit("E08 actor/source evidence lost its low-level breadth")
    return index


def _behavior_classes(props: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = props["live"]["source_actor_clusters"]["behavior_classes"]
    result = {row["type_word"].lower(): row for row in rows}
    if len(rows) != 54 or len(result) != 54:
        raise SystemExit("E08 behavior-class rows are not unique/exhaustive")
    return result


def _program_index(event_vm: dict[str, Any]) -> dict[int, dict[str, Any]]:
    vm = event_vm["static_census"]["vm"]
    by_entry = {row["entry"].lower(): row for row in vm["programs"]}
    result: dict[int, dict[str, Any]] = {}
    for selector in vm["selector_entries"]:
        program = by_entry[selector["entry"].lower()]
        result[selector["selector"]] = {
            "entry": program["entry"],
            "end": program["end"],
            "program_id": program["id"],
            "instruction_count": program["instruction_count"],
            "behavior_signature": program["behavior_signature"],
            "decode_complete": program["decode_complete"],
        }
    if len(result) != 40 or not all(row["decode_complete"] for row in result.values()):
        raise SystemExit("E07 selector/program frontier is incomplete")
    return result


def _compact_contact(trial: dict[str, Any]) -> dict[str, Any]:
    return {
        "timer": trial.get("timer"),
        "contact_center": trial["geometry"]["player_contact_center"],
        "before": {
            "frame": trial["before"]["player"]["frame"],
            "cycle": trial["before"]["player"]["cycle"],
            "player": _compact_player(trial["before"]["player"]),
            "actor": _compact_actor(trial["before"]["actor"]),
        },
        "call": {
            "address": trial["call"]["address"],
            "return_address": trial["call"]["return_address"],
            "stopped_at": trial["call"]["stopped_at"],
            "frame": trial["call"]["status"]["frame"],
            "cycle": trial["call"]["status"]["cycle"],
            "game_serial": trial["call"]["status"]["game_serial"],
            "paused": trial["call"]["status"]["paused"],
        },
        "after": {
            "frame": trial["after"]["player"]["frame"],
            "cycle": trial["after"]["player"]["cycle"],
            "player": _compact_player(trial["after"]["player"]),
            "actor": _compact_actor(trial["after"]["actor"]),
        },
    }


def _natural_abdomen_control(
        abdomen: dict[str, Any], actor_index: dict[tuple[str, str], dict[str, Any]]) \
        -> dict[str, Any]:
    trial = abdomen["live"]["timer_counterfactual"]
    control_before = trial["control_before"]
    edited_before = trial["edited_before"]
    control_after = trial["control_after"]
    edited_after = trial["edited_after"]
    before_actor = control_before["spiders"][0]
    control_actor = control_after["spiders"][0]
    edited_actor = edited_after["spiders"][0]
    if control_before["player"]["fields"] != edited_before["player"]["fields"] or \
            control_before["player"]["player_block_sha256"] != \
            edited_before["player"]["player_block_sha256"] or \
            control_before["player"]["cycle"] != edited_before["player"]["cycle"] or \
            control_after["player"]["frame"] != edited_after["player"]["frame"] or \
            control_after["player"]["cycle"] != edited_after["player"]["cycle"]:
        raise SystemExit("A05 natural counterfactual lost its matched boundary")
    if control_after["player"]["fields"]["health"] != 4 or \
            control_after["player"]["bonus_streak"] != 1 or \
            control_actor["response_state"] != -20 or \
            edited_after["player"]["fields"]["health"] != 3 or \
            edited_after["player"]["bonus_streak"] != 0 or \
            edited_actor["response_state"] != 15:
        raise SystemExit("A05 accepted/expired native outcomes changed")
    save = "movies/Bonus_Level_01.movie.sav"
    actor = actor_index[(save, before_actor["pointer"])]
    source = actor["source"]
    type_word = (source["program_selector"] << 8) | actor["id"]
    if actor["id"] != before_actor["id"] or actor["flags"] != before_actor["flags"]:
        raise SystemExit("A05 natural target no longer joins the E08 actor/source row")
    return {
        "type_word": f"0x{type_word:04X}",
        "save": save,
        "actor_address": actor["address"],
        "actor_id": actor["id"],
        "actor_flags": actor["flags"],
        "source_pointer": actor["source_pointer"],
        "movie_frames": [
            control_before["movie"]["playback_index"],
            control_after["movie"]["playback_index"],
        ],
        "matched_before": {
            "frame": control_before["player"]["frame"],
            "cycle": control_before["player"]["cycle"],
            "player_block_sha256": control_before["player"]["player_block_sha256"],
            "slam_aux": control_before["player"]["fields"]["slam_aux"],
            "actor_response_state": before_actor["response_state"],
        },
        "accepted_bounce": {
            "frame": control_after["player"]["frame"],
            "cycle": control_after["player"]["cycle"],
            "health": control_after["player"]["fields"]["health"],
            "bonus_streak": control_after["player"]["bonus_streak"],
            "actor_response_state": control_actor["response_state"],
            "actor_response_54": control_actor["response_54"],
            "actor_response_58": control_actor["response_58"],
        },
        "expired_contact": {
            "edit": trial["edit"],
            "frame": edited_after["player"]["frame"],
            "cycle": edited_after["player"]["cycle"],
            "health": edited_after["player"]["fields"]["health"],
            "bonus_streak": edited_after["player"]["bonus_streak"],
            "actor_response_state": edited_actor["response_state"],
        },
    }


def build() -> dict[str, Any]:
    docs = {name: _load(path) for name, path in INPUTS.items()}
    props = docs["props_movers"]
    actor_index = _actor_index(props)
    class_index = _behavior_classes(props)
    program_index = _program_index(docs["event_vm"])
    kick_trials = docs["kick"]["live"]["contact_matrix"]["trials"]
    slide_trials = docs["downhill_slide"]["live"]["contact_matrix"]["trials"]
    if set(kick_trials) != set(slide_trials) or \
            len(kick_trials) != EXPECTED_REPRESENTATIVES:
        raise SystemExit("A04/A06 actor representative sets diverged")

    rows = []
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key in sorted(kick_trials):
        kick = kick_trials[key]
        slide = slide_trials[key]
        kick_rep = _representative_core(kick["representative"])
        slide_rep = _representative_core(slide["representative"])
        if kick_rep != slide_rep:
            raise SystemExit(f"A04/A06 representative identity differs: {key}")
        actor = actor_index.get((kick_rep["save"], kick_rep["pointer"]))
        if not actor or actor["id"] != kick_rep["id"] or \
                actor["flags"] != kick_rep["flags"]:
            raise SystemExit(f"native representative has no exact E08 join: {key}")
        source = actor["source"]
        type_word_value = (source["program_selector"] << 8) | actor["id"]
        type_word = f"0x{type_word_value:04X}"
        behavior = class_index[type_word.lower()]
        outcome_class = _validate_kick_pair(key, kick)
        _validate_slide_trial(key, slide)
        row = {
            "representative_key": key,
            "identity": {
                "save": kick_rep["save"],
                "contact_table_index": kick_rep["table_index"],
                "actor_address": kick_rep["pointer"],
                "actor_id": kick_rep["id"],
                "actor_flags": kick_rep["flags"],
                "source_pointer": actor["source_pointer"],
                "type_word": type_word,
                "program_selector": source["program_selector"],
                "authored_signature_sha256": source["authored_signature_sha256"],
                "source_record_sha256": source["record_sha256"],
            },
            "frontier": {
                "e08_owner_classification": behavior["owner_classification"],
                "confirmed_downstream_owner": behavior["confirmed_downstream_owner"],
                "outcome_class": outcome_class,
                "vm_program": program_index[source["program_selector"]],
                "callbacks": behavior["callbacks"],
            },
            "native_controls": {
                "neutral": _compact_contact(kick["neutral"]),
                "kick": _compact_contact(kick["kick"]),
                "timer_12_slide": _compact_contact(slide),
            },
        }
        rows.append(row)
        by_type[type_word].append(row)

    type_words = []
    for type_word, type_rows in sorted(by_type.items()):
        first = type_rows[0]
        type_words.append({
            "type_word": type_word,
            "actor_id": first["identity"]["actor_id"],
            "program_selector": first["identity"]["program_selector"],
            "e08_owner_classification": first["frontier"]["e08_owner_classification"],
            "confirmed_downstream_owner": first["frontier"]["confirmed_downstream_owner"],
            "representatives": [row["representative_key"] for row in type_rows],
            "actor_flags": sorted({row["identity"]["actor_flags"] for row in type_rows}),
            "outcome_classes": sorted({row["frontier"]["outcome_class"] for row in type_rows}),
            "vm_program": first["frontier"]["vm_program"],
            "callbacks": first["frontier"]["callbacks"],
        })
    if len(type_words) != EXPECTED_TYPE_WORDS:
        raise SystemExit(f"native controls joined {len(type_words)} type words")

    unclassified_all = {
        type_word for type_word, row in class_index.items()
        if row["owner_classification"].startswith("unclassified")
    }
    controlled = {row["type_word"].lower() for row in type_words}
    unclassified_controlled = sorted(unclassified_all & controlled)
    unclassified_without = sorted(unclassified_all - controlled)
    if len(unclassified_controlled) != EXPECTED_UNCLASSIFIED_CONTROLLED or \
            len(unclassified_without) != EXPECTED_UNCLASSIFIED_WITHOUT_CONTROL:
        raise SystemExit(
            "E08 unclassified contact partition changed: "
            f"controlled={len(unclassified_controlled)} "
            f"without={len(unclassified_without)}")

    natural = _natural_abdomen_control(
        docs["abdomen_bounce"], actor_index)
    if natural["type_word"].lower() not in controlled:
        raise SystemExit("A05 natural control did not join the direct-contact matrix")

    outcome_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        outcome_counts[row["frontier"]["outcome_class"]] += 1
    return {
        "schema": "abl-phase4-e08-outcome-join/1",
        "generated_by": "tools/phase4_e08_outcome_join.py",
        "inputs": {
            name: {"path": str(path.relative_to(ROOT)), "sha256": _sha256(path)}
            for name, path in INPUTS.items()
        },
        "native_proximity_owner": PROXIMITY_OWNER,
        "summary": {
            "joined_representatives": len(rows),
            "contact_controlled_type_words": len(type_words),
            "outcome_class_representatives": dict(sorted(outcome_counts.items())),
            "unclassified_type_words_total": len(unclassified_all),
            "unclassified_type_words_with_native_contact_controls": len(
                unclassified_controlled),
            "unclassified_type_words_without_native_contact_control": len(
                unclassified_without),
            "exact_actor_source_joins": len(rows),
            "missing_actor_source_joins": 0,
        },
        "unclassified_type_words_with_native_contact_controls": unclassified_controlled,
        "unclassified_type_words_without_native_contact_control": unclassified_without,
        "type_words": type_words,
        "representatives": rows,
        "natural_abdomen_control": natural,
        "bounded_interpretation": {
            "observation": (
                "Twenty-eight retained A04/A06 representatives join exactly to "
                "E08 actor/source records. Their native proximity calls cover 22 "
                "type words, including 18 of E08's 47 unclassified classes."
            ),
            "causal_confirmation": (
                "A04 paired timer 0/-16 at an identical reconstructed contact "
                "center; A06 independently used timer 12; A05 naturally replayed "
                "accepted versus expired contact for type word 0x0109."
            ),
            "inference_boundary": (
                "Contact response does not establish species, switch/gate role, "
                "final campaign ownership, or persistence. The 18 classes remain "
                "unclassified candidates with measured outcomes, and 29 classes "
                "still lack a direct contact control."
            ),
            "next_experiment": (
                "Prioritize the 29 no-contact classes by callback/movement/VM "
                "signature, then capture a native outcome writer for each relevant "
                "class before assigning subsystem ownership."
            ),
        },
    }


def write(output: Path = OUTPUT) -> dict[str, Any]:
    document = build()
    output.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")
    return document


def main() -> int:
    document = write()
    summary = document["summary"]
    print(
        "[phase4-e08-outcome-join] "
        f"{summary['joined_representatives']} representatives -> "
        f"{summary['contact_controlled_type_words']} type words; "
        f"{summary['unclassified_type_words_with_native_contact_controls']}/"
        f"{summary['unclassified_type_words_total']} unclassified classes now "
        "carry native contact controls"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
