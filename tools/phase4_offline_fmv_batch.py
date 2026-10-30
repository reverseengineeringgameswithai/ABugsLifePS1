#!/usr/bin/env python3
"""Build the external E15 FMV frame-boundary index and tracked summary."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

import phase4_common as common
import phase4_offline_contact_batch as frame_index


QUEUE_PATH = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
CAPSULE_PATH = common.ROOT / "analysis/phase4_trace_capsule_set.json"
OUTPUT = common.ROOT / "analysis/phase4_offline_fmv_batch.json"
CONFIG_PATH = common.ROOT / "config/phase4_offline_fmv_batch.yaml"
FMV_CONFIG_PATH = common.ROOT / "config/phase4_fmv.yaml"
CONTACT_TOOL_PATH = common.ROOT / "tools/phase4_offline_contact_batch.py"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
SELECTED_ROWS = tuple(CONFIGURATION["selected_rows"])
SELF_ARTIFACT = "analysis/phase4_offline_fmv_batch.json"
EXTERNAL_EVIDENCE_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()

COMMON_RANGES = {
    "player_block": ("ram", 0x0A6500, 0xB0),
    "actor_pool": ("ram", 0x09FD80, 0x2100),
    "contact_pool": ("ram", 0x0B0D18, 0xE00),
    "full_vram": ("vram", 0x0, 0x100000),
    "full_spu_ram": ("spu", 0x0, 0x80000),
    "fmv_boot_buffer_start": ("ram", 0x0814BC, 4),
    "fmv_boot_buffer_end": ("ram", 0x081530, 4),
}


def stable_generated(path: Path) -> str:
    if path.is_file():
        try:
            value = json.loads(path.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def u32(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<I", image, offset)[0]


def s16(image: bytearray, offset: int) -> int:
    return struct.unpack_from("<h", image, offset)[0]


def register_sha256(registers: dict[str, int]) -> str:
    payload = json.dumps(registers, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def intervals(frames: list[int]) -> list[dict]:
    if not frames:
        return []
    result = []
    start = prior = frames[0]
    for frame in frames[1:]:
        if frame != prior + 1:
            result.append({"start": start, "end": prior})
            start = frame
        prior = frame
    result.append({"start": start, "end": prior})
    return result


def typed_state(ram: bytearray) -> dict:
    typed = CONFIGURATION["typed_ranges"]
    head_spec = typed["overlay_head"]
    start = int(head_spec["offset"])
    head = bytes(ram[start:start + int(head_spec["length"])])
    head_sha = hashlib.sha256(head).hexdigest()
    resident = head_sha == CONFIGURATION["expected_overlay_head_sha256"]
    result = {
        "overlay_resident": resident,
        "overlay_head_sha256": head_sha,
        "fmv_running_latch": u32(ram, int(typed["fmv_running_latch"]["offset"])),
        "scene": u32(ram, int(typed["scene"]["offset"])),
        "shell_substate": u32(ram, int(typed["shell_substate"]["offset"])),
        "str_backloc": u32(ram, int(typed["str_backloc"]["offset"])),
        "fmv_boot_buffer_start": u32(ram, int(typed["fmv_boot_buffer_start"]["offset"])),
        "fmv_boot_buffer_end": u32(ram, int(typed["fmv_boot_buffer_end"]["offset"])),
        "completion_request": None,
        "selected_frame_limit": None,
    }
    if resident:
        result["completion_request"] = u32(
            ram, int(typed["completion_request"]["offset"]))
        result["selected_frame_limit"] = s16(
            ram, int(typed["selected_frame_limit"]["offset"]))
    return result


def delta(before: dict, after: dict) -> dict:
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }


def validate_sources(queue: dict, capsules: dict) -> tuple[dict, list[dict], object]:
    errors = []
    if CONFIGURATION.get("schema") != "abl-phase4-offline-fmv-batch-source/1":
        errors.append("offline FMV source schema is invalid")
    if not queue.get("valid") or queue.get("errors") or len(queue.get("rows") or []) != 107:
        errors.append("offline queue is invalid or not exactly 107 rows")
    if queue.get("counts") != CONFIGURATION["selection_snapshot"]["queue_counts"]:
        errors.append("offline queue counts drifted from selection snapshot")
    if SELECTED_ROWS != ("E15_fmv",):
        errors.append("offline FMV batch must select exactly E15_fmv")
    rows = {item["row_id"]: item for item in queue.get("rows") or []}
    row = rows.get("E15_fmv") or {}
    selection = CONFIGURATION["selection_snapshot"]["rows"][0]
    prior = {item.get("artifact") for item in row.get("prior_offline_analysis") or []}
    if row.get("current_completion_state") != selection["completion_state"] or \
            row.get("classification") != selection["classification"] or \
            (row.get("priority") or {}).get("rank") != selection["queue_rank"]:
        errors.append("E15 is no longer the selected rank-5 open partial")
    if prior and SELF_ARTIFACT not in prior:
        errors.append("E15 gained a different unaccounted offline analysis")
    queries = row.get("offline_batch_queries") or []
    expected_query_count = int(CONFIGURATION["expected_query_count"])
    if len(queries) != expected_query_count:
        errors.append(
            f"E15 query set has {len(queries)} entries, expected "
            f"{expected_query_count}")
    expected_movies = tuple(CONFIGURATION["expected_capsule_movies"])
    queries_by_movie = Counter(
        query.get("capsule_movie") for query in queries)
    expected_per_capsule = int(CONFIGURATION["expected_queries_per_capsule"])
    expected_query_distribution = Counter({
        movie: expected_per_capsule for movie in expected_movies
    })
    if queries_by_movie != expected_query_distribution:
        errors.append(
            "E15 query set does not cover every expected capsule exactly "
            f"{expected_per_capsule} times")
    capsule_by_movie = {
        item["movie"]: item for item in capsules.get("capsules") or []
    }
    relevant = row.get("relevant_capsules") or []
    if len(relevant) != int(CONFIGURATION["expected_unique_capsules"]):
        errors.append(
            "E15 relevant capsule count does not match the refreshed source contract")
    relevant_by_movie = {
        item.get("movie"): item for item in relevant
    }
    if set(relevant_by_movie) != set(expected_movies):
        errors.append("E15 relevant capsule movie set drifted")
    selected_capsules = []
    for movie in expected_movies:
        queue_capsule = relevant_by_movie.get(movie)
        capsule = capsule_by_movie.get(movie)
        if not queue_capsule or not capsule:
            errors.append(f"E15 capsule is absent from current evidence: {movie}")
            continue
        if any(capsule.get(key) != queue_capsule.get(key) for key in (
                "movie_sha256", "capsule_manifest_sha256", "capsule_tree_sha256")):
            errors.append(f"E15 queue and capsule-set pins disagree: {movie}")
        selected_capsules.append(capsule)
    reader_info = capsules.get("offline_reader_snapshot") or {}
    try:
        reader = frame_index.load_reader(
            Path(reader_info.get("absolute_path") or ""), reader_info.get("sha256") or "")
    except ValueError as exc:
        errors.append(str(exc))
        reader = None
    if errors:
        raise ValueError("; ".join(errors))
    return row, selected_capsules, reader


def scan(reader, capsule_row: dict, analysis_windows: list[dict]) -> tuple[dict, dict]:
    manifest = Path(capsule_row["capsule_directory"]) / "manifest.json"
    if common.sha256(manifest) != capsule_row["capsule_manifest_sha256"]:
        raise ValueError(f"capsule manifest pin drifted: {capsule_row['movie']}")
    capsule = reader.Capsule(Path(capsule_row["capsule_directory"]))
    frames = []
    typed_events = []
    prior_typed = None
    hotspots: Counter[int] = Counter()
    window_hotspots = {
        window["id"]: Counter() for window in analysis_windows
    }
    range_frames: dict[str, list[int]] = {key: [] for key in COMMON_RANGES}
    domain_frame_counts: Counter[str] = Counter()
    domain_byte_counts: Counter[str] = Counter()
    for item in capsule.frames():
        current = typed_state(item.state["ram"])
        changes = {}
        for domain in ("ram", "vram", "spu"):
            runs = item.changes[domain]
            changes[domain] = {
                "runs": len(runs),
                "bytes": sum(len(data) for _, data in runs),
            }
            if item.movie_frame > 0 and runs:
                domain_frame_counts[domain] += 1
                domain_byte_counts[domain] += changes[domain]["bytes"]
        correlations = {}
        for range_id, (domain, offset, length) in COMMON_RANGES.items():
            hit = frame_index.intersects(item.changes[domain], offset, length)
            correlations[range_id] = hit
            if item.movie_frame > 0 and hit:
                range_frames[range_id].append(item.movie_frame)
        frame_hotspots = Counter()
        for pc, count, _ in item.flow:
            hotspots[pc] += count
            frame_hotspots[pc] += count
            for window in analysis_windows:
                if int(window["start"]) <= item.movie_frame <= int(window["end"]):
                    window_hotspots[window["id"]][pc] += count
        if prior_typed is not None:
            fields = delta(prior_typed, current)
            if fields:
                typed_events.append({
                    "movie_frame": item.movie_frame,
                    "emulator_frame": item.frame,
                    "cycle": item.cycle,
                    "pc": f"0x{item.pc:08x}",
                    "fields": fields,
                    "range_correlations": correlations,
                    "top_frame_blocks": [
                        {"pc": f"0x{pc:08x}", "count": count}
                        for pc, count in frame_hotspots.most_common(12)
                    ],
                })
        frames.append({
            "movie_frame": item.movie_frame,
            "emulator_frame": item.frame,
            "cycle": item.cycle,
            "pc": f"0x{item.pc:08x}",
            "register_sha256": register_sha256(item.registers),
            "domain_sha256": item.hashes,
            "domain_changes": changes,
            "range_correlations": correlations,
            "typed_state": current,
            "top_frame_blocks": [
                {"pc": f"0x{pc:08x}", "count": count}
                for pc, count in frame_hotspots.most_common(16)
            ],
        })
        prior_typed = current
    expected_records = int(capsule_row["frames"]) + 1
    if len(frames) != expected_records:
        raise ValueError(
            f"E15 reconstructed {len(frames)} records, expected {expected_records}")
    overlay_frames = [
        item["movie_frame"] for item in frames
        if item["typed_state"]["overlay_resident"]
    ]
    summary = {
        "movie": capsule_row["movie"],
        "movie_sha256": capsule_row["movie_sha256"],
        "capsule_manifest_sha256": capsule_row["capsule_manifest_sha256"],
        "capsule_tree_sha256": capsule_row["capsule_tree_sha256"],
        "records": len(frames),
        "movie_frames": capsule_row["frames"],
        "first_boundary": frames[0],
        "last_boundary": frames[-1],
        "typed_state_events": typed_events,
        "overlay_resident_intervals": intervals(overlay_frames),
        "range_change_frames": {
            key: values for key, values in sorted(range_frames.items())
        },
        "range_change_intervals": {
            key: intervals(values) for key, values in sorted(range_frames.items())
        },
        "domain_change_frames_excluding_initial": dict(domain_frame_counts),
        "domain_changed_bytes_sum_excluding_initial": dict(domain_byte_counts),
        "top_hotspots": [
            {"pc": f"0x{pc:08x}", "count": count}
            for pc, count in hotspots.most_common(40)
        ],
        "window_hotspots": {
            window_id: [
                {"pc": f"0x{pc:08x}", "count": count}
                for pc, count in counts.most_common(24)
            ]
            for window_id, counts in window_hotspots.items()
        },
    }
    external = {
        "movie": capsule_row["movie"],
        "summary": summary,
        "frames": frames,
    }
    return external, summary


def selected_boundaries(frames: list[dict], frame_numbers: list[int]) -> list[dict]:
    by_frame = {item["movie_frame"]: item for item in frames}
    return [by_frame[number] for number in frame_numbers]


def assert_expected(capsule_summary: dict, frames: list[dict]) -> None:
    """Fail closed if the low-level reconstruction drifts from banked findings."""
    expected = CONFIGURATION["expected_findings"]
    if capsule_summary["records"] != int(expected["reconstructed_records"]):
        raise ValueError("E15 reconstructed record count drifted")
    if capsule_summary["overlay_resident_intervals"] != \
            expected["overlay_resident_intervals"]:
        raise ValueError("E15 exact overlay-residency interval drifted")
    typed_events = capsule_summary["typed_state_events"]
    event_frames = {
        field: [event["movie_frame"] for event in typed_events if field in event["fields"]]
        for field in (
            "fmv_running_latch", "scene", "shell_substate", "completion_request",
            "selected_frame_limit", "fmv_boot_buffer_start", "fmv_boot_buffer_end")
    }
    expected_frames = expected["typed_state_event_frames"]
    for field, observed in event_frames.items():
        if observed != expected_frames[field]:
            raise ValueError(f"E15 typed event frames drifted: {field}")
    backloc = [event["movie_frame"] for event in typed_events
               if "str_backloc" in event["fields"]]
    if not backloc or backloc[0] != int(expected_frames["str_backloc_first"]) or \
            backloc[-1] != int(expected_frames["str_backloc_last"]):
        raise ValueError("E15 backloc change frontier drifted")
    frame_map = {item["movie_frame"]: item for item in frames}
    for label, values in expected["initialization_values"].items():
        frame = int(label.removeprefix("frame_"))
        observed = frame_map[frame]["typed_state"]
        if any(observed[key] != value for key, value in values.items()):
            raise ValueError(f"E15 initialization state drifted at frame {frame}")
    observed_counts = {
        key: len(value) for key, value in capsule_summary["range_change_frames"].items()
    }
    if observed_counts != expected["range_change_frame_counts"]:
        raise ValueError("E15 scheduled range-change counts drifted")
    if capsule_summary["range_change_intervals"]["full_spu_ram"] != \
            expected["spu_change_intervals"]:
        raise ValueError("E15 SPU-RAM frame-boundary intervals drifted")
    for frame, pc in expected["selected_boundary_pcs"].items():
        if frame_map[int(frame)]["pc"] != f"0x{int(pc):08x}":
            raise ValueError(f"E15 selected boundary PC drifted at frame {frame}")


def build(external_output: Path) -> tuple[dict, dict]:
    queue = common.load_json(QUEUE_PATH)
    capsules = common.load_json(CAPSULE_PATH)
    row, capsule_rows, reader = validate_sources(queue, capsules)
    scans = {}
    for capsule_row in capsule_rows:
        movie = capsule_row["movie"]
        detail, summary = scan(
            reader, capsule_row,
            CONFIGURATION["analysis_windows_by_movie"][movie])
        scans[movie] = {
            "capsule": capsule_row,
            "detail": detail,
            "summary": summary,
        }
    expected_records = CONFIGURATION["expected_findings"][
        "reconstructed_records_by_movie"]
    for movie, expected in expected_records.items():
        observed = scans[movie]["summary"]["records"]
        if observed != int(expected):
            raise ValueError(
                f"{movie} reconstructed {observed} records, expected {expected}")
    primary_movie = CONFIGURATION["primary_capsule_movie"]
    primary = scans[primary_movie]
    capsule_summary = primary["summary"]
    detail = primary["detail"]
    assert_expected(capsule_summary, detail["frames"])
    reader_info = capsules["offline_reader_snapshot"]
    external_document = {
        "_comment": "External game-derived E15 frame index. Preserve outside Git; never commit.",
        "schema": CONFIGURATION["external_index"]["schema"],
        "generated": stable_generated(external_output),
        "selected_rows": list(SELECTED_ROWS),
        "reader": reader_info,
        "selection_snapshot": CONFIGURATION["selection_snapshot"],
        "capsule_index_sha256": common.sha256(CAPSULE_PATH),
        "capsules": [
            scans[movie]["detail"]
            for movie in CONFIGURATION["expected_capsule_movies"]
        ],
    }
    external_bytes = render(external_document)
    external_hash = hashlib.sha256(external_bytes).hexdigest()
    typed_events = capsule_summary["typed_state_events"]
    event_frames = {
        field: [event["movie_frame"] for event in typed_events if field in event["fields"]]
        for field in CONFIGURATION["typed_ranges"]
        if field != "overlay_head"
    }
    boundaries = selected_boundaries(
        detail["frames"], [333, 343, 416, 417, 418, 541])
    frame_map = {item["movie_frame"]: item for item in detail["frames"]}
    source_dependencies = {
        "analysis/phase4_trace_capsule_set.json": common.sha256(CAPSULE_PATH),
        "config/phase4_fmv.yaml": common.sha256(FMV_CONFIG_PATH),
        "config/phase4_offline_fmv_batch.yaml": common.sha256(CONFIG_PATH),
        "tools/phase4_offline_contact_batch.py": common.sha256(CONTACT_TOOL_PATH),
        "tools/phase4_offline_fmv_batch.py": common.sha256(Path(__file__)),
    }
    selection = CONFIGURATION["selection_snapshot"]["rows"][0]
    summary_document = {
        "_comment": "Non-copyrighted E15 frame-boundary summary and external preservation manifest; no every-cycle or producer claim.",
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(OUTPUT),
        "source_dependencies": source_dependencies,
        "selection_snapshot": CONFIGURATION["selection_snapshot"],
        "selected_rows": [{
            **selection,
            "capsules": list(CONFIGURATION["expected_capsule_movies"]),
        }],
        "offline_batch": {
            "reader_path": reader_info["absolute_path"],
            "reader_sha256": reader_info["sha256"],
            "generator_command": (
                "python3 tools/phase4_offline_fmv_batch.py --external-output "
                + str(external_output) + " --write"),
            "capsule_count": len(capsule_rows),
            "reconstructed_records": sum(
                item["summary"]["records"] for item in scans.values()),
            "reconstructed_records_by_capsule": {
                movie: scans[movie]["summary"]["records"]
                for movie in CONFIGURATION["expected_capsule_movies"]
            },
            "domains": CONFIGURATION["external_index"]["domains"],
            "exact_queue_queries": row["offline_batch_queries"],
            "query_count": len(row["offline_batch_queries"]),
        },
        "external_index": {
            "absolute_path": str(external_output),
            "sha256": external_hash,
            "bytes": len(external_bytes),
            "schema": external_document["schema"],
            "media_class": "external game-derived evidence; never commit",
            "preservation_required": True,
        },
        "capsule_summaries": [
            {
                key: scans[movie]["summary"][key] for key in (
                    "movie", "movie_sha256", "capsule_manifest_sha256",
                    "capsule_tree_sha256", "records", "movie_frames",
                    "domain_change_frames_excluding_initial",
                    "domain_changed_bytes_sum_excluding_initial")
            }
            for movie in CONFIGURATION["expected_capsule_movies"]
        ],
        "derived_findings": {
            "primary_movie": primary_movie,
            "overlay_resident_intervals": capsule_summary["overlay_resident_intervals"],
            "initialization_sequence": [
                {"movie_frame": frame, **frame_map[frame]["typed_state"]}
                for frame in (69, 86, 168, 183)
            ],
            "typed_state_event_frames": event_frames,
            "typed_state_events": typed_events,
            "range_change_frames": capsule_summary["range_change_frames"],
            "range_change_intervals": capsule_summary["range_change_intervals"],
            "selected_boundaries": boundaries,
            "full_movie_top_blocks": capsule_summary["top_hotspots"],
            "window_top_blocks": capsule_summary["window_hotspots"],
        },
        "bounded_conclusions": [
            "The exact pinned reader reconstructs all 4,549 retained frame records across the E15 skip and C16 LOSE capsules without a domain-hash error.",
            "Exact FMV.BIN identity first appears at frame 69 with old-looking completion/limit values; completion clears at 86, the limit clears at 168, and LEV1A limit 386 appears at 183. Residency is therefore not initialization-complete proof.",
            "Backloc changes from 1 at frame 218 through 73 at frame 362; the exact FMV.BIN identity remains through frame 416 and is absent at 417, bounding retirement to one frame without attributing its writer.",
            "SPU-RAM changes occur only in intervals 1..9 and 229..362, while the actor/contact pools and both boot-buffer words have no post-initial delta intersection. These are domain correlations, not audio voice or ownership evidence.",
            "Typed state changes, RAM/VRAM/SPU-RAM delta intersections and passive block starts are frame-boundary correlations, not exact writer or producer attribution.",
            "The retained Start branch cannot replace the existing Start-removed native control or generalize LEV1A behavior to the other 39 manifest paths.",
        ],
        "named_unknowns": {"E15_fmv": row["named_unknowns"]},
        "live_escalation": None,
        "campaign_closed": False,
        "errors": [],
        "valid": True,
    }
    return external_document, summary_document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--external-output", type=Path,
        default=EXTERNAL_EVIDENCE_ROOT / "derived/Phase4/fmv-lifecycle-v2/index.json")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    external_output = args.external_output.resolve()
    try:
        external, summary = build(external_output)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    external_bytes = render(external)
    summary_bytes = render(summary)
    if args.write:
        external_output.parent.mkdir(parents=True, exist_ok=True)
        external_output.write_bytes(external_bytes)
        OUTPUT.write_bytes(summary_bytes)
    elif args.check:
        if not external_output.is_file() or external_output.read_bytes() != external_bytes:
            print("external Phase-4 FMV index is missing or stale", file=sys.stderr)
            return 1
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != summary_bytes:
            print("tracked Phase-4 FMV summary is missing or stale", file=sys.stderr)
            return 1
    else:
        print(summary_bytes.decode(), end="")
    print(
        f"PASS: rows=1 capsules={summary['offline_batch']['capsule_count']} "
        f"records={summary['offline_batch']['reconstructed_records']} "
        f"external_sha256={summary['external_index']['sha256']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
