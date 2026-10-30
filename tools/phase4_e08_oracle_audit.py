#!/usr/bin/env python3
"""Bank the bounded E08 original-game oracle from retained pristine evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import yaml

try:
    from build_identity import verify_staged_input
except ModuleNotFoundError:  # imported as tools.phase4_e08_oracle_audit
    from tools.build_identity import verify_staged_input


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_e08_oracle_audit.json"
CONFIG = ROOT / "config/phase4_e08_oracle_audit.yaml"
ORACLE_CONFIG = ROOT / "config/phase4_props_movers.yaml"
PROP_SEMANTIC_C = ROOT / "src_re/prop_decor_catalog.c"
PASS3_SEMANTIC_C = ROOT / "src_re/pass3_backdrop_cull_80014360.c"
EXE_BASE = 0x80010000
EXE_HEADER = 0x800


class AuditError(RuntimeError):
    """Raised when a retained or static oracle predicate does not reproduce."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def require(predicate: bool, message: str) -> None:
    if not predicate:
        raise AuditError(message)


def configured_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def region_bytes(executable: bytes, start: int, end: int) -> bytes:
    offset = EXE_HEADER + start - EXE_BASE
    size = end - start
    require(offset >= EXE_HEADER and size > 0, "invalid executable region")
    require(offset + size <= len(executable), "executable region escaped input")
    return executable[offset:offset + size]


def _source_dependency(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256(path),
    }


def build(
    *,
    props_doc: dict[str, Any] | None = None,
    executable: bytes | None = None,
    receipt_doc: dict[str, Any] | None = None,
    receipt_output: dict[str, Any] | None = None,
    work_packet: dict[str, Any] | None = None,
    derived_doc: dict[str, Any] | None = None,
    movie_inventory: dict[str, Any] | None = None,
    fixture_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(CONFIG.read_text())
    oracle_config = yaml.safe_load(ORACLE_CONFIG.read_text())
    require(
        config.get("schema") == "abl-phase4-e08-original-oracle-audit-config/1",
        "oracle-audit config schema changed",
    )
    require(
        oracle_config.get("schema") == "abl-phase4-props-movers/5",
        "props/movers schema changed",
    )
    expected = oracle_config["original_oracle"]

    retained = config["retained_inputs"]
    props_path = configured_path(retained["props_artifact"]["path"])
    require(
        sha256(props_path) == retained["props_artifact"]["sha256"],
        "retained props artifact hash changed",
    )
    props_doc = props_doc or load_json(props_path)

    exe_path = configured_path(expected["executable"]["path"])
    executable = executable if executable is not None else exe_path.read_bytes()
    try:
        verify_staged_input("SCUS_942.88", executable)
    except SystemExit as exc:
        raise AuditError("retail executable identity changed") from exc
    require(
        sha256_bytes(executable) == expected["executable"]["sha256"],
        "retail executable SHA-256 changed",
    )

    work_config = config["work_packet"]
    work_path = configured_path(work_config["path"])
    require(sha256(work_path) == work_config["sha256"], "work packet hash changed")
    work_packet = work_packet or load_json(work_path)
    require(
        work_packet.get("schema") == "abl-phase4-iteration-work-packet/1",
        "work packet schema changed",
    )
    require(
        work_packet.get("campaign_id") == config["campaign"]
        and work_packet.get("row_ids") == config["selected_rows"],
        "work packet selection changed",
    )
    first_predicate = work_packet.get("first_unmet_predicate") or {}
    require(
        first_predicate.get("row_id") == config["row"]
        and first_predicate.get("dimension") == config["dimension"],
        "work packet first predicate changed",
    )

    offline = config["offline_query"]
    receipt_path = configured_path(offline["receipt_path"])
    output_path = configured_path(offline["output_path"])
    require(sha256(receipt_path) == offline["receipt_sha256"], "offline receipt changed")
    require(sha256(output_path) == offline["output_sha256"], "offline output changed")
    receipt_doc = receipt_doc or load_json(receipt_path)
    receipt_output = receipt_output or load_json(output_path)
    require(
        receipt_doc.get("schema") == "abl-phase4-offline-query/1"
        and receipt_doc.get("complete") is True
        and receipt_doc.get("errors") == []
        and receipt_doc.get("execution", {}).get("exit_code") == 0,
        "offline receipt is not closed",
    )
    require(
        receipt_doc.get("reader", {}).get("path")
        == "tools/phase4_offline_receipt_query.py"
        and receipt_doc.get("reader", {}).get("sha256")
        == sha256(ROOT / "tools/phase4_offline_receipt_query.py"),
        "offline reader pin changed",
    )
    external_inputs = receipt_doc.get("external_inputs") or []
    require(
        len(external_inputs) == 1
        and external_inputs[0].get("sha256") == offline["external_index_sha256"],
        "offline receipt input identity changed",
    )
    outputs = receipt_doc.get("outputs") or []
    require(
        len(outputs) == 1
        and outputs[0].get("sha256") == offline["output_sha256"],
        "offline receipt output identity changed",
    )
    require(
        receipt_output.get("schema") == "abl-phase4-offline-json-search-result/1"
        and receipt_output.get("source", {}).get("sha256")
        == offline["external_index_sha256"],
        "offline output source identity changed",
    )
    for term, count in offline["expected_exact_counts"].items():
        require(
            receipt_output.get("terms", {}).get(term, {}).get("count") == count,
            f"offline exact count changed for {term}",
        )
    movie_terms = [
        term for term in receipt_output["query"]["terms"] if term.endswith(".movie.json")
    ]
    require(
        len(movie_terms) == 10
        and all(receipt_output["terms"][term]["count"] == 2 for term in movie_terms),
        "offline selected-movie coverage changed",
    )

    derived_path = configured_path(retained["derived_catalog"]["path"])
    derived_doc = derived_doc or load_json(derived_path)
    require(
        derived_doc.get("schema") == "abl-phase4-derived-index/1"
        and derived_doc.get("valid") is True,
        "derived-index catalog is invalid",
    )
    derived_rows = {row["row_id"]: row for row in derived_doc["rows"]}
    require(config["row"] in derived_rows, "E08 is absent from derived-index catalog")
    e08_sources = derived_rows[config["row"]]["sources"]
    require(
        any(
            row.get("artifact") == "analysis/phase4_offline_e08_batch.json"
            and row.get("external_index_sha256") == offline["external_index_sha256"]
            for row in e08_sources
        ),
        "E08 derived-index consumer join changed",
    )

    inventory_path = configured_path(retained["movie_inventory"]["path"])
    movie_inventory = movie_inventory or load_json(inventory_path)
    fixture = expected["fixture"]
    inventory_rows = {row["path"]: row for row in movie_inventory["files"]}
    movie_row = inventory_rows.get(fixture["path"]) or {}
    require(
        movie_inventory.get("valid") is True
        and movie_row.get("centrally_declared") is True
        and movie_row.get("sha256") == fixture["sha256"]
        and movie_row.get("bytes") == fixture["bytes"]
        and movie_row.get("declared_frame_count") == fixture["frames"]
        and movie_row.get("declared_from_boot") is True
        and movie_row.get("declared_media_class") == fixture["media_class"],
        "central movie inventory oracle changed",
    )
    fixture_path = configured_path(retained["fixture_set"]["path"])
    fixture_set = fixture_set or load_json(fixture_path)
    fixture_row = fixture_set.get("entries", {}).get(fixture["path"]) or {}
    require(
        fixture_set.get("missing_central_pins") == []
        and fixture_row.get("sha256") == fixture["sha256"]
        and fixture_row.get("size") == fixture["bytes"]
        and fixture_row.get("media_class") == fixture["media_class"]
        and fixture_row.get("preservation_required") is True
        and "phase4_campaign:props_movers_gates"
        in (fixture_row.get("consumers") or []),
        "central fixture declaration changed",
    )

    cold = props_doc["live"]["cold_boot"]
    started = cold["started"]
    status = cold["status"]
    media = props_doc["run_provenance"]["anchor"]["media_identity"]
    hash_verification = media["hash_verification"]
    require(
        cold["movie"] == {
            "path": fixture["path"],
            "sha256": fixture["sha256"],
            "size": fixture["bytes"],
            "media_class": fixture["media_class"],
            "frames": fixture["frames"],
        },
        "retained cold-boot movie identity changed",
    )
    require(
        started.get("reproducible") is True
        and started.get("playing") is True
        and started.get("truncated") is False
        and started.get("start_state", {}).get("from_boot") is True
        and status.get("reproducible") is True
        and status.get("truncated") is False
        and status.get("playback_index") == expected["observation"]["movie_window"][1],
        "retained cold-boot execution changed",
    )
    require(
        media.get("game_serial") == fixture["game_serial"]
        and media.get("rpc_before_hash") == media.get("rpc_after_hash")
        and hash_verification.get("pristine_verified") is True
        and all(
            row.get("matches_pin") is True
            for row in hash_verification.get("files", {}).values()
        ),
        "retained mounted-media authority changed",
    )
    observation = expected["observation"]
    require(
        cold["before"]["scene"] == observation["scene"]
        and cold["after"]["scene"] == observation["scene"]
        and cold["before"]["pass1"]["count"] == observation["pass1_rows"]
        and cold["after"]["pass1"]["count"] == observation["pass1_rows"]
        and cold["before"]["pass3"]["count"] == observation["pass3_rows"]
        and cold["after"]["pass3"]["count"] == observation["pass3_rows"]
        and cold["before"]["actors"]["capacity"] == observation["actor_capacity"]
        and cold["after"]["actors"]["capacity"] == observation["actor_capacity"]
        and cold["before"]["collision"]["sha256"] == observation["collision_sha256"]
        and cold["after"]["collision"]["sha256"] == observation["collision_sha256"],
        "retained scene-1 oracle observation changed",
    )

    controls = props_doc["live"]["render_controls"]
    control_rows: dict[str, Any] = {}
    for name, control_expected in expected["paired_render_controls"].items():
        row = controls[name]
        collision_stable = (
            row["control"]["after"]["collision"] == row["edited"]["after"]["collision"]
        )
        player_stable = (
            row["control"]["after"]["player"] == row["edited"]["after"]["player"]
        )
        require(
            row["frame_diff"]["changed_pixels"] == control_expected["changed_pixels"]
            and collision_stable
            and player_stable
            and control_expected["collision_and_player_stable"] is True,
            f"paired render control changed for {name}",
        )
        control_rows[name] = {
            "changed_pixels": row["frame_diff"]["changed_pixels"],
            "collision_sha256": row["control"]["after"]["collision"]["sha256"],
            "collision_stable": collision_stable,
            "player_stable": player_stable,
        }

    retained_static = props_doc["static_census"]
    require(
        retained_static["executable"]["sha256"] == expected["executable"]["sha256"],
        "retained executable pin changed",
    )
    static_regions: dict[str, Any] = {}
    for name, region in expected["executable"]["regions"].items():
        start, end = int(region["start"]), int(region["end"])
        actual_hash = sha256_bytes(region_bytes(executable, start, end))
        retained_region = retained_static["regions"].get(name) or {}
        require(
            actual_hash == region["sha256"]
            and retained_region.get("start") == f"0x{start:08X}"
            and retained_region.get("end") == f"0x{end:08X}"
            and retained_region.get("sha256") == region["sha256"],
            f"static executable region changed for {name}",
        )
        static_regions[name] = {
            "start": f"0x{start:08X}",
            "end": f"0x{end:08X}",
            "sha256": actual_hash,
        }

    source_dependencies = {
        "audit_contract": _source_dependency(CONFIG),
        "oracle_contract": _source_dependency(ORACLE_CONFIG),
        "prop_semantic_c": _source_dependency(PROP_SEMANTIC_C),
        "pass3_semantic_c": _source_dependency(PASS3_SEMANTIC_C),
    }
    return {
        "_comment": (
            "Hash-only Phase-4 E08 original-oracle audit. Copyrighted movie, "
            "save, disc, receipt-input and executable bytes remain external or "
            "in ignored pristine staging; only bounded facts and hashes are retained."
        ),
        "schema": "abl-phase4-e08-original-oracle-audit/1",
        "campaign": config["campaign"],
        "row": config["row"],
        "dimension": config["dimension"],
        "lane": config["lane"],
        "source_dependencies": {
            row["path"]: row["sha256"] for row in source_dependencies.values()
        },
        "source_dependency_records": source_dependencies,
        "retained_inputs": {
            "props_artifact": {
                "path": retained["props_artifact"]["path"],
                "sha256": retained["props_artifact"]["sha256"],
            },
            "derived_catalog": {
                "path": retained["derived_catalog"]["path"],
                "sha256": sha256(derived_path),
            },
            "movie_inventory": {
                "path": retained["movie_inventory"]["path"],
                "sha256": sha256(inventory_path),
            },
            "fixture_set": {
                "path": retained["fixture_set"]["path"],
                "sha256": sha256(fixture_path),
            },
            "work_packet": {
                "path": work_config["path"],
                "sha256": work_config["sha256"],
            },
        },
        "offline_reuse": {
            "receipt_path": offline["receipt_path"],
            "receipt_sha256": offline["receipt_sha256"],
            "receipt_complete": True,
            "reader_sha256": receipt_doc["reader"]["sha256"],
            "output_path": offline["output_path"],
            "output_sha256": offline["output_sha256"],
            "external_index_sha256": offline["external_index_sha256"],
            "exact_row_counts": offline["expected_exact_counts"],
            "exact_movie_terms": len(movie_terms),
            "all_movie_terms_found_twice": True,
            "e08_catalog_join": True,
            "direct_e08_literal_absent": True,
            "interpretation": offline["interpretation"],
        },
        "oracle": {
            "movie": fixture,
            "media_verified": True,
            "mounted_serial": media["game_serial"],
            "from_boot": True,
            "reproducible": True,
            "window": observation["movie_window"],
            "scene": observation["scene"],
            "pass1_rows": observation["pass1_rows"],
            "pass3_rows": observation["pass3_rows"],
            "actor_capacity": observation["actor_capacity"],
            "collision_sha256": observation["collision_sha256"],
            "collision_stable_across_window": True,
        },
        "paired_controls": {
            "controls": control_rows,
            "changed_pixels": [
                control_rows["pass1_payload_swap"]["changed_pixels"],
                control_rows["pass3_bitmap_disable"]["changed_pixels"],
                control_rows["pass3_anchor_nudge_negative"]["changed_pixels"],
            ],
            "all_collision_hashes_stable": True,
            "all_player_positions_stable": True,
        },
        "static_identity": {
            "executable": expected["executable"]["path"],
            "executable_sha256": expected["executable"]["sha256"],
            "regions": static_regions,
            "all_regions_match": True,
        },
        "claim_boundary": {
            "original_oracle_met": True,
            "promoted_dimensions": config["claim_boundary"]["promote_only"],
            "coupled_rows_promoted": config["claim_boundary"]["coupled_rows_promoted"],
            "other_e08_dimensions_promoted": config["claim_boundary"][
                "other_e08_dimensions_promoted"
            ],
            "live_escalation_authorized": config["claim_boundary"][
                "live_escalation_authorized"
            ],
            "residuals": config["claim_boundary"]["residuals"],
        },
    }


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        text = render(build())
    except AuditError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.write:
        OUTPUT.write_text(text)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != text:
            print("E08 original-oracle audit is missing or stale", file=sys.stderr)
            return 1
    else:
        print(text, end="")
    print("PASS: E08 original oracle reproduces from retained pristine evidence",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
