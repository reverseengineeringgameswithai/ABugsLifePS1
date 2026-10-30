#!/usr/bin/env python3
"""Bind all six Thud rolling-arena rows on the pinned pristine recording.

Four rows contact the player naturally.  Rows 1 and 5 are negative natural
cases on this recording, so matched branches enlarge only their existing
squared-distance thresholds.  Passive movie traces carry timing; the matched
one-field branches carry causality.  The retained artifact contains addresses,
typed values and hashes, never movie, save, model, capture or framebuffer bytes.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

try:
    import phase4_c16_bonus_death as base
    import phase4_e08_operator_contacts as contacts
    import phase4_thud_defeat as thud
    from live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_thud_arena
    from tools import phase4_c16_bonus_death as base
    from tools import phase4_e08_operator_contacts as contacts
    from tools import phase4_thud_defeat as thud
    from tools.live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_thud_arena.json"

PASS2_BASE_POINTER = 0x80082338
TYPE_TABLE = 0x80096DA0
PASS2_ATTRIBUTE_TABLE = 0x80091210
ARENA_SPEED_BASE = 0x800B4BEC
ARENA_CAP_BASE = 0x800B4C00
ARENA_THRESHOLD_BASE = 0x800B4C0C
ARENA_RAMP_BASE = 0x800B4C78
ARENA_PHASE_BASE = 0x800B4C98

PATH_HASHES = (
    "132ff47bb6b7122c7dab69b5427cb1e1f261dc2e50610013c886a3276d248067",
    "46bcd9eab3373a5ba355c01e44d4933d088cbbe8016d494a32ddea0f7d696aa6",
    "59414101ee1f03559b5d4e0ed7b7ad699e1d86ba6b3c8dfed4ca4ba6fc1c082f",
    "b5b8d96df9db1f0e82e93def0e8ea07202203c4a346d09700d82211b377e263a",
    "077beda7cc84dbc8fb96daa816593808dc5026bf6ba76794f8b4e7d5f8a2eab2",
    "c29535663cd4e12cb8b05d3465fc8a8fd040273c7d800f036e85506313fae805",
)
PATH_ENDPOINTS = (
    ([767, -1597, -1705], [767, -1592, -1702]),
    ([-4885, -1508, -1892], [-4885, -1499, -1888]),
    ([-3439, -793, -1492], [-3439, -788, -1487]),
    ([-892, -1312, -1671], [-892, -1307, -1667]),
    ([3448, -1285, -1717], [3448, -1279, -1713]),
    ([5085, -1050, -1462], [5085, -1046, -1458]),
)
MESH_POINTERS = (
    0x8010B1AC, 0x8010B890, 0x8010C8A8, 0x8010D118,
    0x8010DE40, 0x8010EB68, 0x8010F890,
)
MESH_HASHES = (
    "beec3593aa4ab0580489b768bdd717451d0f52928a89ef96b753edbbe8b7197a",
    "072ed18f06e921761194813a474945434df37aed1d2dc4321b6fa624c447bf12",
    "2e89b66ec8d92d785c849750d4de88d2a5eb350525d0fdbe5063e274746648b4",
    "aee67cb5e884db404eef34b71072999157ec0b6b7d6b3c82ee261c5db72e91b7",
    "be0ab4aa8794fb2095051bd36a425e1a7a08ddb02c596aebaa2dd3feb47fc1d9",
    "1c41db4681a619e42d3f9c3c163b07bd059b6ca8f5a2a3e6fb74024870c710ab",
)
CAPS = (92, 96, 112, 100, 104, 88)
THRESHOLDS = (490000, 250000, 160000, 490000, 490000, 490000)

# traceToFrame targets are one greater than the retained playback index.
NATURAL_CONTACTS = (
    {"row": 2, "pre": 978, "post": 979, "health": (4, 3),
     "speed": (-90, 90), "ramp": 112},
    {"row": 3, "pre": 1098, "post": 1099, "health": (3, 2),
     "speed": (144, -144), "ramp": 100},
    {"row": 4, "pre": 1470, "post": 1471, "health": (3, 2),
     "speed": (-110, 110), "ramp": 104},
    {"row": 0, "pre": 3124, "post": 3125, "health": (4, 3),
     "speed": (-100, 100), "ramp": 92},
)
THRESHOLD_CONTROLS = (
    {"row": 5, "start": 1417, "end": 1418, "from": 490000,
     "to": 1000000, "distance": 916961, "health": (2, 1),
     "speed": (128, -128), "ramp": 88,
     "endpoint_alignment": {"emulator_frame": True, "cycle": True,
                            "movie_frame": True, "sp": True, "pc": False},
     "endpoint_cycle_delta": 0},
    {"row": 1, "start": 2689, "end": 2690, "from": 250000,
     "to": 700000, "distance": 607965, "health": (4, 3),
     "speed": (120, -120), "ramp": 96,
     "endpoint_alignment": {"emulator_frame": True, "cycle": True,
                            "movie_frame": True, "sp": True, "pc": False},
     "endpoint_cycle_delta": 0},
)

TRACE_RANGE = {
    "label": "arena_transform_collision",
    "start": f"0x{thud.ARENA_BLOCK_ADDRESS:08X}",
    "end": f"0x{thud.ARENA_BLOCK_ADDRESS + thud.ARENA_BLOCK_LENGTH:08X}",
}
PHASE_TRACE_TARGETS = (3742, 3816, 3897, 3903, 4042)
DECISIVE_PCS = (
    thud.ARENA_ROW_LOOP, thud.ARENA_TRANSFORM_CALL,
    thud.ARENA_CANDIDATE_CALL, thud.ARENA_DISTANCE_COMPARE,
    0x800B4A88, 0x800B4AA8, thud.ARENA_DAMAGE_CALL,
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(client: Any, address: int, length: int) -> bytes:
    return base._read_memory(client, address, length)


def _unpack(client: Any, address: int, fmt: str) -> int:
    return struct.unpack("<" + fmt, _read(
        client, address, struct.calcsize(fmt)))[0]


def _u32(client: Any, address: int) -> int:
    return _unpack(client, address, "I")


def _pass2_row(client: Any, row: int) -> dict[str, int]:
    table = _u32(client, PASS2_BASE_POINTER)
    obj = _u32(client, table + 4 + row * 4)
    registration = _u32(client, obj + 0x10)
    transform = _u32(client, registration + 0x18)
    mesh = _u32(client, transform + 0x1C)
    return {
        "table": table, "object": obj, "registration": registration,
        "transform": transform, "mesh": mesh,
    }


def _positions_and_distances(client: Any) -> tuple[list[int], list[dict[str, Any]]]:
    player = list(struct.unpack("<iii", _read(client, thud.PLAYER, 12)))
    scaled = [value >> 5 for value in player]
    rows = []
    for row in range(thud.ARENA_TRANSFORM_ROW_COUNT):
        links = _pass2_row(client, row)
        position = list(struct.unpack(
            "<iii", _read(client, links["transform"], 12)))
        distance = sum((a - b) ** 2 for a, b in zip(scaled, position))
        threshold = _u32(client, ARENA_THRESHOLD_BASE + row * 4)
        rows.append({
            "row": row, "position": position,
            "squared_distance": distance,
            "threshold": threshold, "inside": distance < threshold,
        })
    return player, rows


def _snapshot(client: Any, row: int | None = None,
              *, full_identity: bool = False) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    movie = client.call("movie.status", {})
    player, distances = _positions_and_distances(client)
    result = {
        "emulator_frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"), "sp": status.get("sp"),
        "movie_frame": movie.get("playback_index"),
        "movie_reproducible": movie.get("reproducible"),
        "movie_truncated": movie.get("truncated"),
        "scene": _u32(client, thud.SCENE),
        "master_state": _unpack(client, thud.MASTER_STATE, "H"),
        "phase_counter": _u32(client, thud.PHASE_COUNTER),
        "player_health": _unpack(client, thud.HEALTH, "h"),
        "player_position": player,
        "rows": distances,
    }
    if row is not None:
        result["selected_row"] = {
            **distances[row],
            "speed": _unpack(client, ARENA_SPEED_BASE + row * 2, "h"),
            "cap": _unpack(client, ARENA_CAP_BASE + row * 2, "h"),
            "ramp": _u32(client, ARENA_RAMP_BASE + row * 4),
            "phase": _u32(client, ARENA_PHASE_BASE + row * 4),
        }
    if full_identity:
        result["main_ram_sha256"] = _sha256_bytes(base._main_ram(client))
        result["registers_sha256"] = base._register_sha256(client)
    return result


def _compact_trace(client: Any, movie_path: Path, frame: int,
                   *, row: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": frame,
        "ranges": [TRACE_RANGE],
    }, timeout=900)
    trace = contacts._compact_trace(raw)
    if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(item.get("truncated") for item in trace.get("coverage") or []):
        raise SystemExit(f"arena trace was not complete/cycle-neutral at {frame}")
    snapshot = _snapshot(client, row)
    if snapshot["movie_reproducible"] is not True or \
            snapshot["movie_truncated"] is not False:
        raise SystemExit(f"arena movie lost reproducibility at {frame}")
    return trace, snapshot


def _counts(raw: dict[str, Any]) -> dict[str, int]:
    wanted = {f"0x{pc:08x}" for pc in DECISIVE_PCS}
    result = {pc: 0 for pc in wanted}
    for coverage in raw.get("coverage") or []:
        for item in (coverage.get("coverage") or {}).get("counts_by_pc") or []:
            pc = str(item.get("pc", "")).lower()
            if pc in result:
                result[pc] += int(item.get("count") or 0)
    return dict(sorted(result.items()))


def _runtime_census(client: Any, movie_path: Path) -> dict[str, Any]:
    thud._advance_movie_to(client, movie_path, thud.ARENA_DAMAGE_PRE_FRAME)
    table = _u32(client, PASS2_BASE_POINTER)
    last_index = _unpack(client, table, "i")
    code = _read(client, thud.ARENA_BLOCK_ADDRESS, thud.ARENA_BLOCK_LENGTH)
    if _sha256_bytes(code) != thud.ARENA_BLOCK_SHA256 or last_index != 9:
        raise SystemExit("arena runtime code/pass-2 table identity drifted")

    rows = []
    for row in range(thud.ARENA_TRANSFORM_ROW_COUNT):
        links = _pass2_row(client, row)
        path_pointer = _u32(client, TYPE_TABLE + row * 4)
        count = _unpack(client, path_pointer, "H")
        path_type = _unpack(client, path_pointer + 2, "h")
        path = _read(client, path_pointer, 4 + count * 12)
        mesh_end = _pass2_row(client, row + 1)["mesh"]
        mesh = _read(client, links["mesh"], mesh_end - links["mesh"])
        registration = _read(client, links["registration"], 0x20)
        attributes = _read(client, PASS2_ATTRIBUTE_TABLE + row * 0x10, 0x10)
        entry = {
            "row": row,
            "dynamic_type_record": {
                "type": path_type, "pointer": f"0x{path_pointer:08x}",
                "point_count": count, "byte_length": len(path),
                "sha256": _sha256_bytes(path),
                "first_point": list(struct.unpack("<iii", path[4:16])),
                "last_point": list(struct.unpack("<iii", path[-12:])),
            },
            "pass2_join": {
                "table": f"0x{links['table']:08x}",
                "object": f"0x{links['object']:08x}",
                "registration": f"0x{links['registration']:08x}",
                "registration_32_byte_sha256": _sha256_bytes(registration),
                "transform": f"0x{links['transform']:08x}",
                "attribute_s16": list(struct.unpack("<8h", attributes)),
            },
            "model_identity": {
                "mesh_pointer": f"0x{links['mesh']:08x}",
                "next_mesh_pointer": f"0x{mesh_end:08x}",
                "byte_length": len(mesh), "sha256": _sha256_bytes(mesh),
                "retention": "Hash/address metadata only; mesh bytes are not retained.",
            },
        }
        expected_first, expected_last = PATH_ENDPOINTS[row]
        if (path_type, count, entry["dynamic_type_record"]["sha256"],
                entry["dynamic_type_record"]["first_point"],
                entry["dynamic_type_record"]["last_point"],
                links["mesh"], mesh_end,
                entry["model_identity"]["sha256"]) != (
                    row, 58, PATH_HASHES[row], expected_first, expected_last,
                    MESH_POINTERS[row], MESH_POINTERS[row + 1],
                    MESH_HASHES[row]):
            raise SystemExit(f"arena row {row} path/model identity drifted: {entry}")
        rows.append(entry)

    speeds = list(struct.unpack("<10h", _read(client, ARENA_SPEED_BASE, 20)))
    caps = list(struct.unpack("<6h", _read(client, ARENA_CAP_BASE, 12)))
    thresholds = list(struct.unpack(
        "<6I", _read(client, ARENA_THRESHOLD_BASE, 24)))
    ramps = list(struct.unpack("<6I", _read(client, ARENA_RAMP_BASE, 24)))
    phases = list(struct.unpack("<6I", _read(client, ARENA_PHASE_BASE, 24)))
    if caps != list(CAPS) or thresholds != list(THRESHOLDS) or \
            speeds != [-100, 120, 90, -144, -110, 128, 32, 32, 32, 64] or \
            ramps != list(CAPS) or phases != [8596, 11552, 5448, 12058, 2616, 5640]:
        raise SystemExit("arena policy tables drifted at target 1466")
    return {
        "target_movie_frame": thud.ARENA_DAMAGE_PRE_FRAME,
        "save_owned_code": {
            "address": f"0x{thud.ARENA_BLOCK_ADDRESS:08x}",
            "length": thud.ARENA_BLOCK_LENGTH,
            "sha256": _sha256_bytes(code),
            "classification": "save-owned Region-A runtime; not staged provenance",
        },
        "pass2_table": {
            "global": f"0x{PASS2_BASE_POINTER:08x}",
            "runtime_base": f"0x{table:08x}", "last_index": last_index,
            "rotation_rows": last_index + 1, "collision_rows": 6,
        },
        "policy_tables": {
            "angular_increment_s16": speeds, "ramp_cap_s16": caps,
            "squared_distance_u32": thresholds,
            "current_ramp_u32": ramps, "path_phase_u32": phases,
        },
        "rows": rows,
        "decoded_policy": {
            "ramp_growth": {"compare": "0x800b48d0", "increment": 2,
                            "store": "0x800b48dc"},
            "path_source": f"0x{TYPE_TABLE:08x}+row*4",
            "path_coordinate": "high byte selects point; low byte interpolates",
            "transform_call": f"0x{thud.ARENA_TRANSFORM_CALL:08x}",
            "collision_candidate_call": f"0x{thud.ARENA_CANDIDATE_CALL:08x}",
            "distance_compare": f"0x{thud.ARENA_DISTANCE_COMPARE:08x}",
            "player_gate": f"0x{thud.ARENA_PLAYER_GATE:08x}",
            "contact_ramp_clear": "0x800b4a88",
            "contact_speed_negation_store": "0x800b4aa8",
            "damage_call": f"0x{thud.ARENA_DAMAGE_CALL:08x}",
        },
        "identity_boundary": (
            "Each mesh slice is bounded by the next pass-2 mesh pointer and each "
            "path by its typed 58-point record. These are runtime identities, "
            "not named visual assets or staged-overlay provenance."),
    }


def _natural_contacts(client: Any, movie_path: Path) -> list[dict[str, Any]]:
    results = []
    for spec in NATURAL_CONTACTS:
        pre_trace, pre = _compact_trace(
            client, movie_path, spec["pre"], row=spec["row"])
        post_trace, post = _compact_trace(
            client, movie_path, spec["post"], row=spec["row"])
        before = pre["selected_row"]
        after = post["selected_row"]
        inside = [item["row"] for item in post["rows"] if item["inside"]]
        observed = (
            (pre["player_health"], post["player_health"]),
            (before["speed"], after["speed"]),
            (before["ramp"], after["ramp"]), inside,
            pre["movie_frame"], post["movie_frame"],
        )
        expected = (
            spec["health"], spec["speed"], (spec["ramp"], 0),
            [spec["row"]], spec["pre"] - 1, spec["post"] - 1,
        )
        if observed != expected:
            raise SystemExit(
                f"natural arena row {spec['row']} drifted: {observed}")
        results.append({
            "row": spec["row"], "pre_target": spec["pre"],
            "post_target": spec["post"], "pre": pre, "post": post,
            "passive_traces": {"pre": pre_trace, "post": post_trace},
            "observed_transition": {
                "health": list(spec["health"]),
                "speed": list(spec["speed"]),
                "ramp": [spec["ramp"], 0],
                "inside_rows_post": inside,
            },
        })
    return results


def _ram_differences(before: bytes, after: bytes) -> list[dict[str, Any]]:
    return [
        {"address": f"0x{0x80000000 + index:08x}",
         "before": old, "after": new}
        for index, (old, new) in enumerate(zip(before, after)) if old != new
    ]


def _threshold_control(client: Any, movie_path: Path,
                       spec: dict[str, int]) -> dict[str, Any]:
    row = spec["row"]
    address = ARENA_THRESHOLD_BASE + row * 4

    def branch(mutate: bool) -> dict[str, Any]:
        thud._advance_movie_to(client, movie_path, spec["start"])
        ram_before = base._main_ram(client)
        before = _snapshot(client, row, full_identity=True)
        write = None
        after_write = None
        differences: list[dict[str, Any]] = []
        if mutate:
            write = client.call("debugger.writeU32", {
                "address": f"0x{address:08X}", "value": spec["to"]})
            ram_after = base._main_ram(client)
            differences = _ram_differences(ram_before, ram_after)
            after_write = _snapshot(client, row, full_identity=True)
        advance = client.call("movie.advanceToFrame", {
            "frame": spec["end"], "max_frames": spec["end"] + 1})
        return {
            "before": before, "write": write, "after_write": after_write,
            "write_differences": differences,
            "after": _snapshot(client, row, full_identity=True),
            "advance": advance,
        }

    control = branch(False)
    mutation = branch(True)
    aligned = ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
               "main_ram_sha256", "registers_sha256")
    if any(control["before"][key] != mutation["before"][key]
           for key in aligned):
        raise SystemExit(f"arena row {row} controls lack a shared origin")
    cb = control["before"]["selected_row"]
    ca = control["after"]["selected_row"]
    ma = mutation["after"]["selected_row"]
    endpoint_equal = {
        key: control["after"][key] == mutation["after"][key]
        for key in ("emulator_frame", "cycle", "movie_frame", "sp")
    }
    endpoint_equal["pc"] = control["after"]["pc"] == mutation["after"]["pc"]
    endpoint_relation = {
        "cycle_delta_mutation_minus_control":
            mutation["after"]["cycle"] - control["after"]["cycle"],
    }
    observed = (cb["threshold"], ca["squared_distance"], ca["inside"],
            ma["threshold"], ma["squared_distance"], ma["inside"],
            (control["before"]["player_health"],
             mutation["after"]["player_health"]),
            (cb["speed"], ma["speed"]), (cb["ramp"], ma["ramp"]),
            control["after"]["player_position"] ==
            mutation["after"]["player_position"],
            ca["position"] == ma["position"], endpoint_equal)
    expected = (
                spec["from"], spec["distance"], False,
                spec["to"], spec["distance"], True,
                spec["health"], spec["speed"], (spec["ramp"], 0),
                True, True,
                spec["endpoint_alignment"])
    if observed != expected:
        raise SystemExit(
            f"arena row {row} threshold outcome drifted: "
            f"observed={observed!r}; expected={expected!r}; "
            f"control_endpoint={{'cycle': {control['after']['cycle']}, "
            f"'pc': {control['after']['pc']!r}}}; "
            f"mutation_endpoint={{'cycle': {mutation['after']['cycle']}, "
            f"'pc': {mutation['after']['pc']!r}}}")
    expected_relation = {
        "cycle_delta_mutation_minus_control": spec["endpoint_cycle_delta"],
    }
    if endpoint_relation != expected_relation:
        raise SystemExit(
            f"arena row {row} endpoint relation drifted: "
            f"observed={endpoint_relation!r}; expected={expected_relation!r}")
    changed = {item["address"] for item in mutation["write_differences"]}
    allowed = {f"0x{address + offset:08x}" for offset in range(4)}
    if not changed or not changed <= allowed or \
            mutation["after_write"]["registers_sha256"] != \
            mutation["before"]["registers_sha256"]:
        raise SystemExit(f"arena row {row} write was not one-field: {changed}")
    return {
        "row": row, "origin_target": spec["start"],
        "endpoint_target": spec["end"],
        "single_field": {"address": f"0x{address:08x}", "width": "u32",
                         "from": spec["from"], "to": spec["to"]},
        "control": control, "mutation": mutation,
        "observed": {
            "squared_distance": spec["distance"],
            "health": list(spec["health"]),
            "speed": list(spec["speed"]), "ramp": [spec["ramp"], 0],
            "control_inside": False, "mutation_inside": True,
        },
        "endpoint_alignment": endpoint_equal,
        "endpoint_relation": endpoint_relation,
        "causal_confirmation": (
            "The branches share full RAM/register/cycle/frame/PC/SP identity "
            "before one u32 threshold write. The mutation alone admits this "
            "row, clears its ramp, reverses its angular increment and lowers "
            "health by one at an equal endpoint movie/emulator frame with "
            "identical player and object positions. The exact endpoint cycle "
            "delta and PCs are retained per row rather than generalized."),
    }


def _phase_linkage(client: Any, movie_path: Path) -> dict[str, Any]:
    points = []
    for target in PHASE_TRACE_TARGETS:
        raw = client.call("movie.traceToFrame", {
            "path": str(movie_path.resolve()), "frame": target,
            "ranges": [TRACE_RANGE],
        }, timeout=900)
        compact = contacts._compact_trace(raw)
        if (compact.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(item.get("truncated") for item in compact.get("coverage") or []):
            raise SystemExit(f"arena phase trace incomplete at {target}")
        snapshot = _snapshot(client)
        points.append({
            "target_movie_frame": target, "snapshot": {
                key: snapshot[key] for key in (
                    "movie_frame", "scene", "master_state", "phase_counter",
                    "player_health")},
            "decisive_counts_by_pc": _counts(raw), "trace": compact,
        })
    row_pc = f"0x{thud.ARENA_ROW_LOOP:08x}"
    counts = [point["decisive_counts_by_pc"][row_pc] for point in points]
    states = [(point["snapshot"]["scene"],
               point["snapshot"]["master_state"],
               point["snapshot"]["phase_counter"])
              for point in points]
    if states[:4] != [(14, 1, 8)] * 4 or states[4][0] != 0 or \
            not (counts[0] < counts[1] < counts[2] <= counts[3] <= counts[4]):
        raise SystemExit(f"arena counter-8/exit linkage drifted: {states} {counts}")
    return {
        "points": points,
        "row_loop_cumulative_counts": counts,
        "observation": (
            "Cycle-neutral traces show the six-row loop continues after the "
            "natural counter-8/master-state transition, through the approach "
            "to defeat and retirement boundary, with the final sample in "
            "scene 0. Counts are reported rather than assuming when scene "
            "geometry itself completes."),
    }


def _source_dependencies() -> dict[str, str]:
    paths = (
        "tools/phase4_thud_defeat.py",
        "analysis/phase4_thud_defeat.json",
        "analysis/phase0_2_external_fixture_set.json",
        "REBUILD/files/SCUS_942.88",
    )
    return {path: base._sha256(ROOT / path) for path in paths}


def derive_summary(document: dict[str, Any]) -> dict[str, Any]:
    census = document.get("runtime_census") or {}
    natural = document.get("natural_contacts") or []
    controls = document.get("threshold_controls") or []
    linkage = document.get("counter8_phase_linkage") or {}
    return {
        "arena_rows": len(census.get("rows") or []),
        "path_records": len(census.get("rows") or []),
        "distinct_model_hashes": len({
            (row.get("model_identity") or {}).get("sha256")
            for row in census.get("rows") or []}),
        "natural_contact_rows": [row.get("row") for row in natural],
        "controlled_contact_rows": [row.get("row") for row in controls],
        "all_contact_rows": sorted(
            [row.get("row") for row in natural] +
            [row.get("row") for row in controls]),
        "contact_health_delta": -1,
        "counter8_phase_points": len(linkage.get("points") or []),
        "d18_or_f09_completed": 0,
    }


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if document.get("schema") != "abl-phase4-thud-arena/1":
        gaps.append("Thud arena schema changed")
    if document.get("campaign_state") != "active_partial":
        gaps.append("Thud arena campaign state changed")
    if document.get("source_dependencies") != _source_dependencies():
        gaps.append("Thud arena source dependencies changed")
    census = document.get("runtime_census") or {}
    rows = census.get("rows") or []
    if [((row.get("dynamic_type_record") or {}).get("type"),
         (row.get("dynamic_type_record") or {}).get("point_count"),
         (row.get("dynamic_type_record") or {}).get("sha256"),
         (row.get("model_identity") or {}).get("byte_length"),
         (row.get("model_identity") or {}).get("sha256"))
        for row in rows] != [
            (row, 58, PATH_HASHES[row],
             MESH_POINTERS[row + 1] - MESH_POINTERS[row], MESH_HASHES[row])
            for row in range(6)]:
        gaps.append("Thud arena path/model census changed")
    if (census.get("policy_tables") or {}).get("ramp_cap_s16") != list(CAPS) or \
            (census.get("policy_tables") or {}).get(
                "squared_distance_u32") != list(THRESHOLDS):
        gaps.append("Thud arena policy tables changed")
    natural = document.get("natural_contacts") or []
    if [(row.get("row"), (row.get("observed_transition") or {}).get("health"),
         (row.get("observed_transition") or {}).get("speed"),
         (row.get("observed_transition") or {}).get("ramp"),
         (row.get("observed_transition") or {}).get("inside_rows_post"))
        for row in natural] != [
            (spec["row"], list(spec["health"]), list(spec["speed"]),
             [spec["ramp"], 0], [spec["row"]])
            for spec in NATURAL_CONTACTS]:
        gaps.append("Thud natural arena contacts changed")
    for item in natural:
        for side in ("pre", "post"):
            trace = (item.get("passive_traces") or {}).get(side) or {}
            if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                    any(row.get("truncated")
                        for row in trace.get("coverage") or []):
                gaps.append(f"Thud row {item.get('row')} {side} trace changed")
    controls = document.get("threshold_controls") or []
    if [(item.get("row"), (item.get("observed") or {}).get("squared_distance"),
         (item.get("observed") or {}).get("health"),
         (item.get("observed") or {}).get("speed"),
         (item.get("observed") or {}).get("ramp"),
         item.get("endpoint_alignment")) for item in controls] != [
            (spec["row"], spec["distance"], list(spec["health"]),
             list(spec["speed"]), [spec["ramp"], 0],
             spec["endpoint_alignment"])
            for spec in THRESHOLD_CONTROLS]:
        gaps.append("Thud negative-row threshold controls changed")
    if [item.get("endpoint_relation") for item in controls] != [{
            "cycle_delta_mutation_minus_control": spec["endpoint_cycle_delta"],
            } for spec in THRESHOLD_CONTROLS]:
        gaps.append("Thud negative-row exact endpoint relations changed")
    for item in controls:
        before_control = (item.get("control") or {}).get("before") or {}
        before_mutation = (item.get("mutation") or {}).get("before") or {}
        for key in ("emulator_frame", "cycle", "movie_frame", "pc", "sp",
                    "main_ram_sha256", "registers_sha256"):
            if before_control.get(key) != before_mutation.get(key):
                gaps.append(f"Thud row {item.get('row')} branch origin changed")
                break
        changed = {
            row.get("address") for row in
            ((item.get("mutation") or {}).get("write_differences") or [])}
        address = int((item.get("single_field") or {}).get("address", "0"), 0)
        if not changed or not changed <= {
                f"0x{address + offset:08x}" for offset in range(4)}:
            gaps.append(f"Thud row {item.get('row')} one-field write changed")
    linkage = document.get("counter8_phase_linkage") or {}
    points = linkage.get("points") or []
    if len(points) != len(PHASE_TRACE_TARGETS) or any(
            ((point.get("trace") or {}).get("comparison") or {}).get(
                "cycle_neutral") is not True for point in points):
        gaps.append("Thud counter-8 phase linkage changed")
    expected_summary = {
        "arena_rows": 6, "path_records": 6, "distinct_model_hashes": 6,
        "natural_contact_rows": [2, 3, 4, 0],
        "controlled_contact_rows": [5, 1],
        "all_contact_rows": [0, 1, 2, 3, 4, 5],
        "contact_health_delta": -1,
        "counter8_phase_points": 5,
        "d18_or_f09_completed": 0,
    }
    if document.get("summary") != derive_summary(document) or \
            document.get("summary") != expected_summary:
        gaps.append("Thud arena derived summary changed")
    gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned Thud arena process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixture = thud.build_fixture_census()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.writeU32", "debugger.getRegisters",
        "emulator.getMediaInfo", "emulator.getStateInfo",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.traceToFrame", "movie.stopPlayback", "movie.status",
        "movie.clear",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks arena methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, ROOT / thud.SAVE_REL, media)
    movie_path = ROOT / thud.MOVIE_REL
    thud._start_movie(client, movie_path)
    runtime = _runtime_census(client, movie_path)
    natural = _natural_contacts(client, movie_path)
    controls = [
        _threshold_control(client, movie_path, spec)
        for spec in THRESHOLD_CONTROLS
    ]
    phase_linkage = _phase_linkage(client, movie_path)
    base._cleanup(client)
    final_media = verified_media_identity(
        client, client.call("debugger.status", {}))
    provenance = finish_run(
        args, generator="tools/phase4_thud_arena.py",
        anchor={
            "type": "existing state-anchored Thud natural-defeat recording",
            "save": thud.SAVE_REL, "movie": thud.MOVIE_REL,
            "fixture_sha256": {
                thud.SAVE_REL: thud.SAVE_SHA256,
                thud.MOVIE_REL: thud.MOVIE_SHA256,
            },
            "state_inspections": [inspection], "media_identity": media,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "natural_contact_trace_targets": [
                [spec["pre"], spec["post"]] for spec in NATURAL_CONTACTS],
            "threshold_control_targets": [
                [spec["start"], spec["end"]]
                for spec in THRESHOLD_CONTROLS],
            "phase_linkage_targets": list(PHASE_TRACE_TARGETS),
            "trace_mode": (
                "passive cycle-neutral movie.traceToFrame pairs for natural "
                "contacts and phase linkage; fresh matched one-u32 branches "
                "for the two negative natural rows"),
        })
    document = {
        "_comment": (
            "Active D18/F09 arena breadth: all six rows have exact path/model "
            "runtime identities and a causal contact transition. Four occur "
            "naturally; two use matched threshold-only controls. Boss attack, "
            "retry/persistence and complete visual/geometry ownership remain open."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-thud-arena/1",
        "campaign_state": "active_partial",
        "fixture_census": fixture,
        "runtime_census": runtime,
        "natural_contacts": natural,
        "threshold_controls": controls,
        "counter8_phase_linkage": phase_linkage,
        "bounded_interpretation": {
            "observation": (
                "The save-owned block ramps and advances six typed 58-point "
                "paths, writes six pass-2 transforms, submits six collision "
                "candidates and compares six squared-distance thresholds. "
                "Rows 0/2/3/4 naturally clear their ramp, reverse speed and "
                "lower player health by one. Rows 1/5 remain outside their "
                "natural thresholds in this recording."),
            "inference": (
                "The pass-2 transform pointers join each path row to one exact, "
                "distinct bounded mesh payload. This identifies runtime model "
                "inputs but does not assign visual names or GPU ownership."),
            "causal_confirmation": (
                "For rows 1/5, increasing only the existing threshold above "
                "the measured distance produces the same ramp clear, speed "
                "reversal and one-health transition at equal endpoint frame "
                "with identical player/object positions. Row 5 ends at equal "
                "cycle with distinct PCs; row 1 ends one cycle later at the "
                "same PC. Full RAM, "
                "registers, frame, cycle, PC and SP match before each write."),
            "forbidden_claim": (
                "Do not infer named boulder variants, texture/GPU ownership, "
                "natural row-1/5 contact frequency, complete attack policy, "
                "retry/persistence policy, or D18/F09 completion."),
        },
        "bounded_open_frontier": {
            "closed_here": (
                "Six row paths, pass-2 transform/model joins, ramp/cap/threshold "
                "policy, contact reversal/reset/damage transition and post-"
                "counter-8 execution breadth."),
            "still_open": (
                "Other boss attacks, full visual/geometry ownership, exact "
                "arena objective/completion request, initialization, retry, "
                "checkpoint, persistence and campaign breadth."),
            "next_experiment": (
                "Use the same recording to bind another distinct attack or "
                "the exact objective/exit request; request another fixture only "
                "if neither boundary exists in the current movie."),
        },
        "source_dependencies": _source_dependencies(),
        "run_provenance": provenance,
    }
    document["summary"] = derive_summary(document)
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained Thud arena evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print("[thud-arena] six row path/model/contact policies bound")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        if (Path(args.config_dir) / "instance.pid").is_file():
            try:
                finish_run(
                    args, generator="tools/phase4_thud_arena.py",
                    anchor={"type": "aborted before retained arena evidence"},
                    timing={})
            except BaseException as cleanup_error:
                print(
                    f"owned Thud arena cleanup also failed: {cleanup_error}",
                    file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
