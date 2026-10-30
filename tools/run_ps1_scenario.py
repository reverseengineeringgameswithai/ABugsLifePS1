#!/usr/bin/env python3
"""Run one isolated declarative DuckStation scenario."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from ps1_scenario import (ROOT, ScenarioError, ScenarioRunner, load_scenario, parse_int,
                          resolve_path, write_reports)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--disc", type=Path, help="override target.disc")
    parser.add_argument("--output-dir", type=Path, help="report directory (default: unique /tmp directory)")
    parser.add_argument("--expect", action="append", default=[], metavar="ASSERTION=VALUE",
                        help="override an expected integer; useful for testing diagnostics")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    scenario_path = resolve_path(args.scenario)
    try:
        scenario = load_scenario(scenario_path)
        if args.validate_only:
            print(f"valid: {scenario_path} ({scenario['id']})")
            return 0
        overrides = {}
        for item in args.expect:
            if "=" not in item:
                raise ScenarioError(f"--expect needs ASSERTION=VALUE, got {item!r}")
            key, value = item.split("=", 1)
            overrides[key] = parse_int(value, f"--expect {key}")
        output_dir = args.output_dir
        if output_dir is None:
            output_dir = Path("/tmp") / f"abl-ps1-report-{scenario['id']}"
        else:
            output_dir = resolve_path(output_dir)
        disc = resolve_path(args.disc) if args.disc else None
        report = ScenarioRunner(scenario_path, scenario, disc_override=disc,
                                expected_overrides=overrides,
                                evidence_dir=output_dir / "evidence").run()
        json_path, md_path = write_reports(report, output_dir)
        print(f"{scenario['id']}: {report['status'].upper()}")
        print(f"JSON: {json_path}")
        print(f"Markdown: {md_path}")
        return 0 if report["status"] == "passed" else 1
    except ScenarioError as exc:
        print(f"scenario error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
