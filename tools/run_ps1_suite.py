#!/usr/bin/env python3
"""Run a list of PS1 scenarios sequentially and summarize their reports."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "tools" / "scenarios" / "duckstation" / "regression_suite.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--disc", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/abl-ps1-regression-suite"))
    parser.add_argument("--stop-on-failure", action="store_true")
    args = parser.parse_args()
    suite_path = args.suite.resolve()
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    if suite.get("schema_version") != 1 or not isinstance(suite.get("scenarios"), list):
        raise SystemExit(f"invalid suite: {suite_path}")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for scenario_value in suite["scenarios"]:
        scenario = (ROOT / scenario_value).resolve()
        command = [sys.executable, str(ROOT / "tools" / "run_ps1_scenario.py"), str(scenario),
                   "--output-dir", str(output_dir / scenario.stem)]
        if args.disc:
            command += ["--disc", str(args.disc.resolve())]
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        report_candidates = sorted((output_dir / scenario.stem).glob("*.json"))
        report_path = report_candidates[0] if report_candidates else output_dir / scenario.stem / "missing.json"
        report = json.loads(report_path.read_text()) if report_path.is_file() else {}
        result = {"scenario": str(scenario.relative_to(ROOT)), "returncode": proc.returncode,
                  "status": report.get("status", "missing_report"), "report": str(report_path),
                  "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
        results.append(result)
        print(f"[{result['status'].upper():7}] {scenario.stem}")
        if proc.returncode and args.stop_on_failure:
            break
    summary = {"schema_version": 1, "suite_id": suite.get("id"),
               "finished_at": datetime.now(timezone.utc).isoformat(), "results": results,
               "passed": bool(results) and all(r["status"] == "passed" for r in results)}
    summary_json = output_dir / "suite.json"
    summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [f"# PS1 regression suite: {suite.get('id')}", "",
             f"Status: **{'PASSED' if summary['passed'] else 'FAILED'}**", "",
             "| Scenario | Status | Report |", "|---|---|---|"]
    for result in results:
        lines.append(f"| `{Path(result['scenario']).stem}` | {result['status']} | `{result['report']}` |")
    (output_dir / "suite.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"summary: {summary_json}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
