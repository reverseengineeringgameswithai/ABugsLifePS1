#!/usr/bin/env python3
"""Probe the two remaining from-boot movies for a natural F01 request-2 skip.

One invocation owns one already-launched isolated DuckStation.  Use `--consolidate`
after both receipts exist.  No guest state is written or injected.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

from phase4_f01_evidence import (  # noqa: E402
    external_identity,
    fixture_entries,
    observed_media_identity,
    pristine_executable_path,
    oracle_provenance_checks,
    pristine_media_checks,
    provisioned_path,
    require_checks,
    sha256_file,
)


CONSUMER = 0x8004FF14
DECISION = 0x8004FF28
FINALIZER = 0x8004FF48
HEALTH_DEATH_STORE = 0x8004A8B4
PIT_DEATH_STORE = 0x8004A9F4
REQUEST_WORD = 0x800823A0
REQUEST_PHYSICAL = REQUEST_WORD & 0x1FFFFFFF
OTHER_SKIP = 0x8008225C
CHUNK = 500
CYCLE_WINDOW = 2000
CONSUMER_TO_DECISION_CYCLE_WINDOW = 100000
MAX_REQUEST_TO_DECISION_FRAMES = 600
EXPECTED_MOVIES = frozenset({
    "movies/Phase4/Interpreter/D18_thud_fight.movie.json",
    "movies/Phase4/Interpreter/E02_FreshLoad_Clover.movie.json",
    # 2026-08-10: operator-recorded cold-boot natural death, the B1 dependency.
    # The first two were probed and neither contains a death (D18: 1 decision,
    # request [1], 0 death stores; E02: 0 decisions), which is why this exists.
    "movies/Phase4/Interpreter/F01_natural_death_FromBoot.movie.json",
})

WATCHES = {
    "consumer": CONSUMER,
    "decision": DECISION,
    "finalizer": FINALIZER,
}


def captured_memory(event: dict[str, Any]) -> dict[int, int]:
    values = {}
    for item in event.get("memory") or []:
        address = int(str(item.get("address")), 16)
        raw = item.get("hex") or item.get("value")
        values[address] = (
            int.from_bytes(bytes.fromhex(raw), "little")
            if isinstance(raw, str) else raw
        )
    return values


def event_integer(event: dict[str, Any], key: str, hex_key: str | None = None) -> int | None:
    raw = event.get(key)
    if raw is None and hex_key:
        raw = event.get(hex_key)
    if raw is None:
        return None
    return int(str(raw), 0)


def physical_address(address: int) -> int:
    return address & 0x1FFFFFFF if 0x80000000 <= address < 0xC0000000 else address


def overlaps_request(address: int, width: int) -> bool:
    start = physical_address(address)
    return start < REQUEST_PHYSICAL + 2 and REQUEST_PHYSICAL < start + width


def replay(args: argparse.Namespace) -> int:
    from duckstation_debug_client import DebuggerClient

    entries = fixture_entries()
    movie_identity = external_identity(args.movie, set(entries))
    if movie_identity not in EXPECTED_MOVIES:
        raise SystemExit(f"movie is outside the declared B1 probe pair: {movie_identity}")
    movie_path = provisioned_path(movie_identity)
    movie_doc = json.loads(movie_path.read_text())
    movie_hash = sha256_file(movie_path)
    movie_size = movie_path.stat().st_size

    image = pristine_executable_path().read_bytes()
    text_address = struct.unpack_from("<I", image, 0x18)[0]

    def image_word(address: int) -> int:
        return struct.unpack_from("<I", image, address - text_address + 0x800)[0]

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(3600)

    media = observed_media_identity(client.call("emulator.getMediaInfo", {}))
    require_checks(pristine_media_checks(media), "pristine media")
    mode = client.call("debugger.status", {}).get("execution_mode", {})
    if mode.get("effective") != "Interpreter":
        raise SystemExit(f"not Interpreter: {mode.get('effective')}")

    try:
        client.call("movie.stopPlayback", {})
    except Exception:
        pass
    loaded = client.call("movie.load", {"path": str(movie_path)})
    frames = loaded["frame_count"]
    started = client.call("movie.startPlayback", {"load_start_state": True})
    if started.get("playing") is not True or started.get("reproducible") is not True:
        raise SystemExit(f"playback did not start reproducibly: {started}")

    client.call("execTrace.clear", {})
    client.call("accessLog.clear", {})
    request_watch = client.call("accessLog.addWatch", {
        "address": f"0x{REQUEST_WORD:08x}",
        "length": 2,
        "type": "write",
        "max_events": 10000,
        "stop_on_hit": False,
    })
    for label, pc in WATCHES.items():
        capture_memory = [{"address": f"0x{pc:08x}", "width": 4}]
        capture = ["pc"]
        if label == "decision":
            capture_memory.extend([
                {"address": f"0x{REQUEST_WORD:08x}", "width": 2},
                {"address": f"0x{OTHER_SKIP:08x}", "width": 4},
            ])
        client.call("execTrace.addWatch", {
            "pc": f"0x{pc:08x}",
            "label": label,
            "capture": capture,
            "capture_memory": capture_memory,
            "max_events": 10000,
        })
    current = 0
    while current < frames:
        current = min(current + CHUNK, frames)
        advanced = client.call(
            "movie.resumeUntilMovieFrame",
            {"frame": current, "max_frames": frames + 900},
            timeout=3600,
        )
        execution = advanced.get("execution") or {}
        if execution.get("completed") is not True:
            raise SystemExit(
                f"early stop at movie frame {current}: "
                f"{execution.get('stop_reason')} {execution.get('stop_details')}"
            )

    trace = client.call("execTrace.get", {"offset": 0, "limit": 10000})
    events = trace.get("events") or []
    complete_page = (
        trace.get("total") == len(events) and trace.get("truncated") is False
    )
    access = client.call("accessLog.get", {
        "watch_id": request_watch.get("watch_id"),
        "offset": 0,
        "limit": 10000,
    })
    access_events = access.get("events") or []
    complete_access_page = (
        access.get("total") == len(access_events)
        and access.get("truncated") is False
    )

    retained: dict[str, list[dict[str, Any]]] = {}
    rejected: dict[str, int] = {}
    for label, pc in WATCHES.items():
        matching = [event for event in events
                    if int(str(event.get("pc")), 16) == pc]
        wanted_word = image_word(pc)
        retained[label] = [event for event in matching
                           if captured_memory(event).get(pc) == wanted_word]
        rejected[label] = len(matching) - len(retained[label])

    consumers = sorted(event["cycle"] for event in retained["consumer"])
    finalizers = sorted(event["cycle"] for event in retained["finalizer"])
    death_words = {
        HEALTH_DEATH_STORE: image_word(HEALTH_DEATH_STORE),
        PIT_DEATH_STORE: image_word(PIT_DEATH_STORE),
    }
    request_writes = []
    for event in access_events:
        instruction_pc = event_integer(event, "instruction_pc")
        instruction_word = event_integer(event, "instruction_word")
        address = event_integer(event, "address")
        stored = event_integer(event, "new_value", "new_value_hex")
        width = event.get("width")
        exact_resident_halfword = (
            instruction_pc in death_words
            and isinstance(address, int)
            and physical_address(address) == REQUEST_PHYSICAL
            and width == 2
        )
        is_resident_death = instruction_pc in death_words
        death_certified = (
            exact_resident_halfword
            and instruction_word == death_words[instruction_pc]
        )
        request_writes.append({
            "frame": event.get("frame"),
            "cycle": event.get("cycle"),
            "address": f"0x{address:08X}" if isinstance(address, int) else None,
            "physical_address": (
                f"0x{physical_address(address):08X}" if isinstance(address, int) else None
            ),
            "type": event.get("type"),
            "width": width,
            "instruction_pc": (
                f"0x{instruction_pc:08X}" if isinstance(instruction_pc, int) else None
            ),
            "instruction_word": (
                f"0x{instruction_word:08X}" if isinstance(instruction_word, int) else None
            ),
            "instruction": event.get("instruction"),
            "new_value": stored,
            "new_value_hex": (
                f"0x{stored & ((1 << (width * 8)) - 1):0{width * 2}X}"
                if isinstance(stored, int) and width in {1, 2, 4} else None
            ),
            "stored_u16": (
                stored & 0xFFFF
                if exact_resident_halfword and isinstance(stored, int) else None
            ),
            "overlaps_request_word": (
                overlaps_request(address, width)
                if isinstance(address, int) and width in {1, 2, 4} else False
            ),
            "resident_death_store": is_resident_death,
            "resident_pristine_certificate": {
                "required": exact_resident_halfword,
                "expected_instruction_word": (
                    f"0x{death_words[instruction_pc]:08X}"
                    if exact_resident_halfword else None
                ),
                "passed": death_certified if exact_resident_halfword else None,
            },
            "source_scope": (
                "resident pristine executable"
                if is_resident_death else
                "runtime writer; overlay file identity deliberately not inferred"
            ),
        })
    request_writes.sort(key=lambda row: row["cycle"])

    decisions = []
    for event in retained["decision"]:
        memory = captured_memory(event)
        request = memory.get(REQUEST_WORD)
        if request is not None and request >= 0x8000:
            request -= 0x10000
        cycle = event["cycle"]
        prior_writes = [write for write in request_writes if write["cycle"] < cycle]
        last_writer = prior_writes[-1] if prior_writes else None
        later_finalizers = [value for value in finalizers
                            if 0 < value - cycle <= CYCLE_WINDOW]
        prior_consumers = [
            value for value in consumers
            if 0 < cycle - value <= CONSUMER_TO_DECISION_CYCLE_WINDOW
        ]
        decisions.append({
            "frame": event.get("frame"),
            "cycle": cycle,
            "request": request,
            "gp4c4": memory.get(OTHER_SKIP),
            "consumer_proceeded": bool(prior_consumers),
            "finalizer_observed": bool(later_finalizers),
            "last_request_writer": last_writer,
            "request_writer_to_decision_frames": (
                event.get("frame") - last_writer["frame"]
                if last_writer and event.get("frame") is not None
                and last_writer.get("frame") is not None else None
            ),
            "self_certification": {
                "pc": f"0x{DECISION:08X}",
                "instruction_word": f"0x{memory[DECISION]:08X}",
                "pristine_instruction_word": f"0x{image_word(DECISION):08X}",
                "passed": memory.get(DECISION) == image_word(DECISION),
            },
        })

    request2_controls = [
        row for row in decisions
        if row["request"] == 2
        and row["gp4c4"] == 0
        and row["consumer_proceeded"] is True
        and row["finalizer_observed"] is False
        and row["last_request_writer"] is not None
        and int(row["last_request_writer"]["instruction_pc"], 16)
            in {HEALTH_DEATH_STORE, PIT_DEATH_STORE}
        and row["last_request_writer"]["resident_pristine_certificate"]["passed"] is True
        and row["last_request_writer"]["stored_u16"] == 2
        and isinstance(row["request_writer_to_decision_frames"], int)
        and 0 <= row["request_writer_to_decision_frames"]
            <= MAX_REQUEST_TO_DECISION_FRAMES
        and row["self_certification"]["passed"] is True
    ]

    provenance = oracle_provenance_checks(
        movie_identity=movie_identity,
        movie_doc=movie_doc,
        movie_sha256=movie_hash,
        movie_size=movie_size,
        central_pin=entries.get(movie_identity),
        media_identity=media,
        trace_truncated=trace.get("truncated"),
        playback_reproducible=started.get("reproducible"),
        playback_completed=True,
        declared_identities=set(entries),
    )
    retained_certificate_failures = sum(
        captured_memory(event).get(WATCHES[label]) != image_word(WATCHES[label])
        for label in WATCHES
        for event in retained[label]
    )
    completeness = [
        {"id": "trace_page_complete", "expected": True,
         "actual": complete_page, "passed": complete_page},
        {"id": "request_write_page_complete", "expected": True,
         "actual": complete_access_page, "passed": complete_access_page},
        {"id": "all_retained_events_self_certified", "expected": 0,
         "actual": retained_certificate_failures,
         "passed": retained_certificate_failures == 0},
    ]

    doc = {
        "schema": "abl-phase4-f01-request2-probe/1",
        "authority": {
            "is_proof": False,
            "promotes_original_oracle": False,
            "injection": "NONE",
        },
        "fixture": {
            "movie": movie_identity,
            "movie_sha256": movie_hash,
            "movie_size": movie_size,
            "frames": frames,
            "from_boot": (movie_doc.get("start_state") or {}).get("from_boot"),
            "reproducible": started.get("reproducible"),
            "playback_completed": True,
        },
        "runtime": {
            "port": args.port,
            "config_label": args.config_label,
            "execution_mode": mode.get("effective"),
            "media": media,
        },
        "method": {
            "launcher": "tools/launch_repro_playback.sh --execution-mode Interpreter",
            "playback": "movie.resumeUntilMovieFrame",
            "watches": {label: f"0x{pc:08X}" for label, pc in WATCHES.items()},
            "guard": "each retained PC hit equals the pristine word at that PC",
            "writer_attribution": "an accessLog write watch covers the request word itself; "
                                  "the last instruction-attributed write before each decision "
                                  "must be a resident death store, with no intervening write",
            "writer_to_decision_bound_frames": MAX_REQUEST_TO_DECISION_FRAMES,
            "writer_to_decision_bound_reason": "death timer is at most 60 and decrements "
                                               "every two frames; 600 frames retains a "
                                               "five-times scheduling margin while the address "
                                               "write watch excludes intervening writes",
            "consumer_to_decision_cycle_window": CONSUMER_TO_DECISION_CYCLE_WINDOW,
            "consumer_to_decision_window_reason": "the intervening consumer call measured "
                                                  "50,311 cycles in D18; 100,000 is a "
                                                  "bounded near-two-times margin",
            "injection": "none; read-only execTrace instrumentation",
        },
        "preload_noise_rejected": rejected,
        "watch_certification": {
            label: {
                "pc": f"0x{pc:08X}",
                "pristine_instruction_word": f"0x{image_word(pc):08X}",
                "retained_events": len(retained[label]),
                "all_retained_events_certified": all(
                    captured_memory(event).get(pc) == image_word(pc)
                    for event in retained[label]
                ),
            }
            for label, pc in WATCHES.items()
        },
        "request_write_watch": {
            "address": f"0x{REQUEST_WORD:08X}",
            "length": 2,
            "type": "write",
            "attribution": "accessLog instruction_pc/instruction_word/new_value",
            "overlay_identity_policy": "do not infer an overlay file from a runtime PC",
            "retained_events": len(request_writes),
        },
        "consumer_cycles": consumers,
        "finalizer_cycles": finalizers,
        "request_writes": request_writes,
        "decisions": decisions,
        "request_values": sorted({row["request"] for row in decisions}),
        "natural_request2_skip_controls": request2_controls,
        "natural_request2_skip_control_observed": bool(request2_controls),
        "provenance_assertions": provenance,
        "capture_assertions": completeness,
        "capture_accepted": (
            all(row["passed"] for row in provenance)
            and all(row["passed"] for row in completeness)
        ),
        "exec_trace": {
            "total": trace.get("total"),
            "returned": len(events),
            "truncated": trace.get("truncated"),
        },
        "access_log": {
            "total": access.get("total"),
            "returned": len(access_events),
            "truncated": access.get("truncated"),
        },
    }
    self_validation_errors, _ = validate_receipt(doc)
    doc["receipt_self_validation_errors"] = self_validation_errors
    doc["capture_accepted"] = (
        doc["capture_accepted"] and not self_validation_errors
    )
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(
        f"[request2] {movie_identity}: decisions={len(decisions)} "
        f"requests={doc['request_values']} writes={len(request_writes)} "
        f"controls={len(request2_controls)} accepted={doc['capture_accepted']}"
    )
    return 0 if doc["capture_accepted"] else 1


def validate_receipt(row: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    fixture = row.get("fixture") or {}
    identity = fixture.get("movie")
    entries = fixture_entries()
    if identity not in EXPECTED_MOVIES:
        return [f"unexpected movie identity: {identity}"], []
    path = provisioned_path(identity)
    movie_doc = json.loads(path.read_text())
    provenance = oracle_provenance_checks(
        movie_identity=identity,
        movie_doc=movie_doc,
        movie_sha256=sha256_file(path),
        movie_size=path.stat().st_size,
        central_pin=entries.get(identity),
        media_identity=(row.get("runtime") or {}).get("media") or {},
        trace_truncated=(row.get("exec_trace") or {}).get("truncated"),
        playback_reproducible=fixture.get("reproducible"),
        playback_completed=fixture.get("playback_completed"),
        declared_identities=set(entries),
    )
    errors.extend(check["id"] for check in provenance if not check["passed"])
    if fixture.get("movie_sha256") != sha256_file(path):
        errors.append("receipt movie hash mismatch")
    if fixture.get("movie_size") != path.stat().st_size:
        errors.append("receipt movie size mismatch")
    if (row.get("runtime") or {}).get("execution_mode") != "Interpreter":
        errors.append("execution mode is not Interpreter")
    if row.get("capture_accepted") is not True:
        errors.append("receipt does not declare an accepted capture")
    trace = row.get("exec_trace") or {}
    if not (
        type(trace.get("total")) is int
        and type(trace.get("returned")) is int
        and trace["total"] >= 0
        and trace["total"] == trace["returned"]
    ):
        errors.append("trace page is incomplete")

    capture_assertions = {
        assertion.get("id"): assertion
        for assertion in row.get("capture_assertions") or []
    }
    if set(capture_assertions) != {
        "trace_page_complete", "request_write_page_complete",
        "all_retained_events_self_certified"
    } or not all(
        assertion.get("passed") is True
        for assertion in capture_assertions.values()
    ):
        errors.append("capture assertions are missing or failed")

    certifications = row.get("watch_certification") or {}
    expected_words = {}
    image = pristine_executable_path().read_bytes()
    text_address = struct.unpack_from("<I", image, 0x18)[0]
    for label, pc in WATCHES.items():
        word = struct.unpack_from("<I", image, pc - text_address + 0x800)[0]
        expected_words[label] = f"0x{word:08X}"
        cert = certifications.get(label) or {}
        if not (
            cert.get("pc") == f"0x{pc:08X}"
            and cert.get("pristine_instruction_word") == expected_words[label]
            and cert.get("all_retained_events_certified") is True
            and type(cert.get("retained_events")) is int
            and cert["retained_events"] >= 0
        ):
            errors.append(f"{label} watch certificate invalid")

    request_writes = row.get("request_writes") or []
    access = row.get("access_log") or {}
    write_watch = row.get("request_write_watch") or {}
    if not (
        type(access.get("total")) is int
        and type(access.get("returned")) is int
        and access["total"] >= 0
        and access["total"] == access["returned"] == len(request_writes)
        and access.get("truncated") is False
        and write_watch.get("address") == f"0x{REQUEST_WORD:08X}"
        and write_watch.get("length") == 2
        and write_watch.get("type") == "write"
        and write_watch.get("retained_events") == len(request_writes)
        and write_watch.get("overlay_identity_policy")
            == "do not infer an overlay file from a runtime PC"
    ):
        errors.append("request write-watch page/count envelope is invalid")

    death_words = {
        HEALTH_DEATH_STORE: expected_words.get("health_death_store"),
        PIT_DEATH_STORE: expected_words.get("pit_death_store"),
    }
    # These resident stores are not part of WATCHES; derive their exact pristine words.
    for pc in death_words:
        word = struct.unpack_from("<I", image, pc - text_address + 0x800)[0]
        death_words[pc] = f"0x{word:08X}"
    valid_writes = []
    for write in request_writes:
        try:
            instruction_pc = int(str(write.get("instruction_pc")), 16)
            instruction_word = int(str(write.get("instruction_word")), 16)
            address = int(str(write.get("address")), 16)
        except (TypeError, ValueError):
            instruction_pc = instruction_word = address = None
        width = write.get("width")
        is_death = instruction_pc in death_words
        exact_death = (
            is_death
            and isinstance(address, int)
            and physical_address(address) == REQUEST_PHYSICAL
            and width == 2
        )
        death_cert = write.get("resident_pristine_certificate") or {}
        expected_scope = (
            "resident pristine executable" if is_death
            else "runtime writer; overlay file identity deliberately not inferred"
        )
        valid = (
            type(address) is int
            and type(width) is int
            and width in {1, 2, 4}
            and overlaps_request(address, width)
            and write.get("physical_address")
                == f"0x{physical_address(address):08X}"
            and write.get("overlaps_request_word") is True
            and write.get("type") == "write"
            and type(instruction_pc) is int
            and type(instruction_word) is int
            and type(write.get("cycle")) is int
            and type(write.get("frame")) is int
            and write["cycle"] >= 0
            and write["frame"] >= 0
            and type(write.get("new_value")) is int
            and 0 <= write["new_value"] < (1 << (width * 8))
            and write.get("new_value_hex")
                == f"0x{write['new_value']:0{width * 2}X}"
            and (type(write.get("stored_u16")) is int if exact_death
                 else write.get("stored_u16") is None)
            and write.get("resident_death_store") is is_death
            and write.get("source_scope") == expected_scope
            and death_cert.get("required") is exact_death
            and not (is_death and not exact_death)
            and "image" not in write
        )
        if exact_death:
            valid = valid and (
                write.get("instruction_word") == death_words[instruction_pc]
                and death_cert.get("expected_instruction_word")
                    == death_words[instruction_pc]
                and death_cert.get("passed") is True
            )
        else:
            valid = valid and (
                death_cert.get("expected_instruction_word") is None
                and death_cert.get("passed") is None
            )
        if not valid:
            errors.append(
                f"request write event lacks access/effective-writer provenance: "
                f"{write.get('instruction_pc')}"
            )
            continue
        valid_writes.append(write)

    if request_writes != sorted(request_writes, key=lambda write: write.get("cycle", -1)):
        errors.append("request-writer events are not in cycle order")
    valid_writes.sort(key=lambda write: write["cycle"])

    consumer_cycles = row.get("consumer_cycles") or []
    finalizer_cycles = row.get("finalizer_cycles") or []
    if not (
        all(type(value) is int and value >= 0 for value in consumer_cycles)
        and consumer_cycles == sorted(consumer_cycles)
        and len(consumer_cycles) == (certifications.get("consumer") or {}).get("retained_events")
    ):
        errors.append("consumer cycle list is invalid or inconsistent")
    if not (
        all(type(value) is int and value >= 0 for value in finalizer_cycles)
        and finalizer_cycles == sorted(finalizer_cycles)
        and len(finalizer_cycles) == (certifications.get("finalizer") or {}).get("retained_events")
    ):
        errors.append("finalizer cycle list is invalid or inconsistent")
    decisions = row.get("decisions") or []
    if len(decisions) != (certifications.get("decision") or {}).get("retained_events"):
        errors.append("decision list is inconsistent with its certified event count")
    controls = []
    for decision in decisions:
        cert = decision.get("self_certification") or {}
        if not (
            cert.get("pc") == f"0x{DECISION:08X}"
            and cert.get("instruction_word") == expected_words["decision"]
            and cert.get("pristine_instruction_word") == expected_words["decision"]
            and cert.get("passed") is True
            and type(decision.get("cycle")) is int
            and type(decision.get("frame")) is int
            and type(decision.get("request")) is int
            and type(decision.get("gp4c4")) is int
            and decision["cycle"] >= 0
            and decision["frame"] >= 0
        ):
            errors.append("decision certificate invalid")
            continue
        cycle = decision["cycle"]
        consumer = any(0 < cycle - value <= CONSUMER_TO_DECISION_CYCLE_WINDOW
                       for value in consumer_cycles)
        finalizer = any(0 < value - cycle <= CYCLE_WINDOW
                        for value in finalizer_cycles)
        prior_writes = [write for write in valid_writes if write["cycle"] < cycle]
        last_writer = prior_writes[-1] if prior_writes else None
        writer_delta = (
            decision.get("frame") - last_writer["frame"]
            if last_writer else None
        )
        if decision.get("consumer_proceeded") is not consumer:
            errors.append("stored consumer attribution is inconsistent")
        if decision.get("finalizer_observed") is not finalizer:
            errors.append("stored finalizer attribution is inconsistent")
        if decision.get("last_request_writer") != last_writer:
            errors.append("stored last-writer attribution is inconsistent")
        if decision.get("request_writer_to_decision_frames") != writer_delta:
            errors.append("stored writer-to-decision bound is inconsistent")
        if (decision.get("request") == 2 and decision.get("gp4c4") == 0
                and consumer and not finalizer and last_writer
                and int(last_writer["instruction_pc"], 16)
                    in {HEALTH_DEATH_STORE, PIT_DEATH_STORE}
                and last_writer["resident_pristine_certificate"]["passed"] is True
                and last_writer["stored_u16"] == 2
                and isinstance(writer_delta, int)
                and 0 <= writer_delta <= MAX_REQUEST_TO_DECISION_FRAMES):
            controls.append(decision)

    rejected = row.get("preload_noise_rejected") or {}
    if not (
        set(rejected) == set(WATCHES)
        and all(type(value) is int and value >= 0 for value in rejected.values())
        and trace.get("total") == (
            sum((certifications.get(label) or {}).get("retained_events", -1)
                for label in WATCHES)
            + sum(rejected.values())
        )
    ):
        errors.append("exec-trace retained/rejected counts do not reconcile to total")
    derived_request_values = sorted({
        decision.get("request") for decision in decisions
        if type(decision.get("request")) is int
    })
    if row.get("request_values") != derived_request_values:
        errors.append("stored request-value summary is inconsistent")
    if row.get("natural_request2_skip_controls") != controls:
        errors.append("stored request-2 control rows are inconsistent")
    if row.get("natural_request2_skip_control_observed") is not bool(controls):
        errors.append("stored request-2 control observation is inconsistent")
    if ("receipt_self_validation_errors" in row
            and row.get("receipt_self_validation_errors") != []):
        errors.append("receipt retains self-validation errors")
    return errors, controls


def consolidate(args: argparse.Namespace) -> int:
    receipts = [json.loads(Path(path).read_text()) for path in args.inputs]
    identities = [(row.get("fixture") or {}).get("movie") for row in receipts]
    # Generalized 2026-08-10 from a hardcoded pair to the exact declared set, when the
    # operator's cold-boot natural-death recording became the third candidate. Still an
    # exact-set check in both directions -- no receipt may be missing, duplicated or extra.
    exact_set = (len(receipts) == len(EXPECTED_MOVIES)
                 and len(set(identities)) == len(EXPECTED_MOVIES)
                 and set(identities) == EXPECTED_MOVIES)
    validations = [validate_receipt(row) for row in receipts]
    errors = {}
    for index, (row, validation) in enumerate(zip(receipts, validations)):
        if validation[0]:
            identity = (row.get("fixture") or {}).get("movie")
            errors[str(identity) if identity is not None else f"receipt-{index}"] = validation[0]
    accepted = exact_set and not errors
    controls = [
        {"movie": (row.get("fixture") or {}).get("movie"), "control": control}
        for row, validation in zip(receipts, validations)
        for control in validation[1]
    ]
    if not accepted:
        outcome = "NOT DONE"
        dependency = None
        would_satisfy = (
            f"{len(EXPECTED_MOVIES)} exact, independently valid receipts -- one for "
            "every movie in the declared candidate set."
        )
    elif controls:
        outcome = "DONE"
        dependency = None
        would_satisfy = None
    else:
        outcome = "BLOCKED"
        dependency = (
            "a centrally pinned pristine cold-boot movie in which Flik dies naturally"
        )
        would_satisfy = (
            "A complete nontruncated replay of that recording must self-certify the "
            "natural request-2 producer and decision, observe the consumer proceed, "
            "and observe no attributable finalizer call."
        )
    doc = {
        "schema": "abl-phase4-f01-request2-probe-consolidated/1",
        "authority": {"promotes_original_oracle": False},
        "declared_movies": sorted(EXPECTED_MOVIES),
        "exact_set_replayed": exact_set,
        "captures_accepted": sum(not validation[0] for validation in validations),
        "captures_required": len(EXPECTED_MOVIES),
        "receipt_validation_errors": errors,
        "results": {
            str((row.get("fixture") or {}).get("movie") or f"receipt-{index}"): row
            for index, row in enumerate(receipts)
        },
        "natural_request2_skip_controls": controls,
        "element_outcome": outcome,
        "dependency": dependency,
        "would_satisfy": would_satisfy,
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[request2] consolidated: accepted={accepted} controls={len(controls)} {outcome}")
    return 0 if accepted else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--movie")
    parser.add_argument("--port", type=int)
    parser.add_argument("--token")
    parser.add_argument("--config-label")
    parser.add_argument("--out", required=True)
    parser.add_argument("--consolidate", action="store_true")
    parser.add_argument("--inputs", nargs="*")
    args = parser.parse_args()
    if args.consolidate:
        if not args.inputs:
            raise SystemExit("--consolidate requires --inputs")
        return consolidate(args)
    if not all((args.movie, args.port, args.token, args.config_label)):
        raise SystemExit("probe mode requires --movie, --port, --token, and --config-label")
    return replay(args)


if __name__ == "__main__":
    raise SystemExit(main())
