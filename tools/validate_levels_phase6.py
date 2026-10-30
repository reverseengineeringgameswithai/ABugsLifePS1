#!/usr/bin/env python3
"""Option C Phase 6: cross-level non-mutating validation.

This tool sweeps the pristine extracted LEVEL DATs, reuses the Phase 1 catalog
decoder and the trusted relocation scanner, and reports cross-level facts before
any per-level mutation workflow is enabled:

- which levels carry a type-0x3f placement record;
- which DATs are relocation-bearing (and how many relocation sites);
- which levels have unusual type-0x3f counts relative to the LEVEL01 baseline;
- which source kinds appear that are unknown or flagged caution;
- a standing warning that the confirmed LEVEL01 identity map is proven for
  LEVEL01 only and must not be applied blindly to other levels.

It never writes DAT/BIN/CUE inputs. It only emits a Markdown/CSV report and
stdout summary.
"""

from __future__ import annotations

import argparse
import csv
import glob
from dataclasses import dataclass, field
from pathlib import Path

import catalog_type3f as cat
import dat_reloc

# LEVEL01 is the only level with a confirmed entry-index -> kind identity map.
LEVEL01_BASELINE_COUNT = 70
CAUTION_KINDS = {0x2C, 0x2D, 0x30}
BERRY_KINDS = {0x21, 0x22, 0x23, 0x24}

REPORT_COLUMNS = [
    "file",
    "has_type3f",
    "type3f_offset",
    "type3f_count",
    "count_vs_baseline",
    "relocation_sites",
    "relocation_bearing",
    "kinds_present",
    "unknown_kinds",
    "caution_kinds",
    "berry_kinds",
    "warnings",
]


@dataclass
class LevelResult:
    path: Path
    has_type3f: bool = False
    type3f_offset: int | None = None
    type3f_count: int | None = None
    reloc_sites: int | None = None
    reloc_error: str | None = None
    kinds_present: list[int] = field(default_factory=list)
    unknown_kinds: list[int] = field(default_factory=list)
    caution_kinds: list[int] = field(default_factory=list)
    berry_kinds: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parse_error: str | None = None

    @property
    def relocation_bearing(self) -> bool:
        return bool(self.reloc_sites)

    @property
    def count_vs_baseline(self) -> str:
        if self.type3f_count is None:
            return "n/a"
        if self.type3f_count == LEVEL01_BASELINE_COUNT:
            return "baseline"
        delta = self.type3f_count - LEVEL01_BASELINE_COUNT
        return f"{'+' if delta > 0 else ''}{delta}"


def kinds_from_summary(summary: cat.FileSummary) -> list[int]:
    return sorted({row.source_kind for row in summary.rows})


def scan_relocation(path: Path) -> tuple[int | None, str | None]:
    """Return (site_count, error). Reuses the trusted relocation walk; some
    structurally different DATs (e.g. LEVEL00) are not type-0x3f placement DATs
    and the walk does not apply to them."""
    try:
        sites, _meta = dat_reloc.DAT(path.read_bytes()).scan_sites()
        return len(sites), None
    except Exception as exc:  # noqa: BLE001 - record and keep validating.
        return None, str(exc)


def analyze_level(path: Path) -> LevelResult:
    result = LevelResult(path=path)
    try:
        summary = cat.analyze_file(path)
    except Exception as exc:  # noqa: BLE001 - mirror catalog tolerance.
        result.parse_error = str(exc)
        return result

    result.has_type3f = bool(summary.type3f_offsets)
    if summary.type3f_offsets:
        result.type3f_offset = summary.type3f_offsets[0]
    if summary.type3f_counts:
        result.type3f_count = summary.type3f_counts[0]

    kinds = kinds_from_summary(summary)
    result.kinds_present = kinds
    result.unknown_kinds = [k for k in kinds if k not in cat.GENERIC_KIND_IDENTITIES]
    result.caution_kinds = sorted(set(kinds) & CAUTION_KINDS)
    result.berry_kinds = sorted(set(kinds) & BERRY_KINDS)

    result.reloc_sites, result.reloc_error = scan_relocation(path)

    result.warnings = list(summary.warnings)
    if result.reloc_error:
        result.warnings.append(f"relocation scan not applicable: {result.reloc_error}")
    if not result.has_type3f:
        result.warnings.append("no type-0x3f placement record; out of scope for placement tooling")
    if cat.is_level01_pristine_basename(path):
        result.warnings.append("LEVEL01 is the only level with a confirmed identity map")
    else:
        result.warnings.append(
            "level-specific identities unverified; do not apply LEVEL01 map without evidence"
        )
    return result


def fmt_kinds(kinds: list[int]) -> str:
    return ", ".join(f"0x{k:02x}" for k in kinds) if kinds else "-"


def hex_or_dash(value: int | None) -> str:
    return f"0x{value:06x}" if value is not None else "-"


def expand_paths(args: list[str]) -> list[Path]:
    paths: list[Path] = []
    for arg in args:
        matches = [Path(m) for m in glob.glob(arg)]
        paths.extend(matches if matches else [Path(arg)])
    return sorted(dict.fromkeys(paths))


def row_for(result: LevelResult) -> dict[str, str]:
    return {
        "file": str(result.path),
        "has_type3f": "yes" if result.has_type3f else "no",
        "type3f_offset": hex_or_dash(result.type3f_offset),
        "type3f_count": "-" if result.type3f_count is None else str(result.type3f_count),
        "count_vs_baseline": result.count_vs_baseline,
        "relocation_sites": "n/a" if result.reloc_sites is None else str(result.reloc_sites),
        "relocation_bearing": "yes" if result.relocation_bearing else "no",
        "kinds_present": fmt_kinds(result.kinds_present),
        "unknown_kinds": fmt_kinds(result.unknown_kinds),
        "caution_kinds": fmt_kinds(result.caution_kinds),
        "berry_kinds": fmt_kinds(result.berry_kinds),
        "warnings": "; ".join(result.warnings) if result.warnings else "-",
    }


def write_csv(path: Path, results: list[LevelResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow(row_for(result))


def write_markdown(path: Path, results: list[LevelResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Option C Phase 6: Cross-Level Validation",
        "",
        "Generated by `tools/validate_levels_phase6.py`. Non-mutating cross-level",
        "sweep that reuses the Phase 1 catalog decoder and the trusted relocation",
        "scanner. No DAT/BIN/CUE files are written.",
        "",
        "## Cross-Level Summary",
        "",
        "| file | type-0x3f | offset | count | vs baseline (70) | reloc sites | reloc-bearing | unknown kinds | caution kinds | berry kinds |",
        "|---|:--:|---:|---:|:--:|---:|:--:|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| `{r.path}` | {'yes' if r.has_type3f else 'no'} | "
            f"`{hex_or_dash(r.type3f_offset)}` | "
            f"{'-' if r.type3f_count is None else r.type3f_count} | "
            f"{r.count_vs_baseline} | "
            f"{'n/a' if r.reloc_sites is None else r.reloc_sites} | "
            f"{'yes' if r.relocation_bearing else 'no'} | "
            f"{fmt_kinds(r.unknown_kinds)} | {fmt_kinds(r.caution_kinds)} | "
            f"{fmt_kinds(r.berry_kinds)} |"
        )

    levels_with_t3f = [r for r in results if r.has_type3f]
    reloc_bearing = [r for r in results if r.relocation_bearing]
    unusual = [r for r in levels_with_t3f if r.count_vs_baseline not in ("baseline",)]
    with_unknown = [r for r in results if r.unknown_kinds]

    lines.extend(
        [
            "",
            "## Findings",
            "",
            f"- Levels with a type-0x3f placement record: "
            + (", ".join(f"`{r.path.name}`" for r in levels_with_t3f) or "none") + ".",
            f"- Relocation-bearing DATs (byte shifts require relocation repair): "
            + (", ".join(f"`{r.path.name}` ({r.reloc_sites})" for r in reloc_bearing) or "none") + ".",
            f"- Levels whose type-0x3f count differs from the LEVEL01 baseline of "
            f"{LEVEL01_BASELINE_COUNT}: "
            + (", ".join(f"`{r.path.name}` ({r.type3f_count}, {r.count_vs_baseline})" for r in unusual) or "none") + ".",
            f"- Levels with source kinds not in the known generic map: "
            + (", ".join(f"`{r.path.name}` ({fmt_kinds(r.unknown_kinds)})" for r in with_unknown) or "none") + ".",
            "",
            "## Standing Cautions Before Per-Level Mutation",
            "",
            "- The confirmed entry-index -> identity map is proven for LEVEL01 only.",
            "  Other levels are decoded by source kind only; do not assume LEVEL01",
            "  entry semantics carry over without per-level evidence.",
            "- Caution source kinds (`0x2c`, `0x2d`, `0x30`) and any unknown kind",
            "  (e.g. `0x31`) must be reviewed per level before movement or append.",
            "- Real berry kinds (`0x21..0x24`) must keep their source kind; never",
            "  repurpose them as sacrifice slots.",
            "- Validate one level at a time after reviewing its warnings here; keep",
            "  original discs and pristine extracted DATs read-only.",
            "",
            "## Per-Level Warnings",
            "",
        ]
    )
    for r in results:
        lines.append(f"### `{r.path}`")
        lines.append("")
        if r.parse_error:
            lines.extend([f"- parse failure: {r.parse_error}", ""])
            continue
        for warning in r.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    path.write_text("\n".join(lines) + "\n")


def print_summary(results: list[LevelResult]) -> None:
    print(",".join(REPORT_COLUMNS))
    for r in results:
        row = row_for(r)
        print(",".join(str(row[c]).replace(",", " ") for c in REPORT_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cross-level non-mutating validation for type-0x3f placement DATs."
    )
    parser.add_argument(
        "dat",
        nargs="*",
        help="DAT paths or globs (default: pristine LEVEL00..LEVEL10 _LEVEL.DAT)",
    )
    parser.add_argument("--csv", type=Path, default=Path("DAT/phase6_cross_level.csv"))
    parser.add_argument("--md", type=Path, default=Path("DAT/phase6_cross_level.md"))
    parser.add_argument("--no-write", action="store_true", help="do not write reports")
    parser.add_argument(
        "--format",
        choices=("summary", "none"),
        default="summary",
        help="stdout format; reports are still written unless --no-write is used",
    )
    return parser.parse_args()


def default_paths() -> list[str]:
    return [f"DAT/LEVEL{n:02d}_LEVEL.DAT" for n in range(0, 11)]


def main() -> int:
    args = parse_args()
    patterns = args.dat or default_paths()
    paths = expand_paths(patterns)
    if not paths:
        raise SystemExit("no DAT files matched")

    results = [analyze_level(path) for path in paths]

    if not args.no_write:
        write_csv(args.csv, results)
        write_markdown(args.md, results)
        print(f"csv: {args.csv}")
        print(f"markdown: {args.md}")

    if args.format == "summary":
        print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
