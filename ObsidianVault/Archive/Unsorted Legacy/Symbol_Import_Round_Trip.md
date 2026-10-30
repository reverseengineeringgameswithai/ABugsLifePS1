---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Symbol Import Round Trip.md
aliases:
  - "Symbol Import Round Trip"
migration_action: superseded
superseded_by:
  - RE_BASELINE_INDEX
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Symbol Import Round Trip.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Symbol Import Round Trip
type: verification
updated: 2026-06-20
tags: [symbols, debugger, radare2, milestone3, gap-0018]
---

# Symbol import round trip

> M3 consumer proof for `symbols/re_symbols.sym`. **Result: 85/85 address/name pairs round-trip through both the documented DuckStation CSV representation and an r2 flag script.** This is reproducible from tracked text alone and does not require game media, emulator state, or the dirty fork binary.

## Source format

`symbols/re_symbols.sym` uses the fork's documented PS1 symbol syntax:

```text
AAAAAAAA label
```

`tools/validate_symbol_map.py` requires eight uppercase hexadecimal digits, one identifier-safe unique label per unique address, and strictly increasing addresses. The `.sym` format represents labels only: semantic type/confidence/source remain in [[Symbol Map Baseline]] and are intentionally not fabricated during conversion.

## Reproducible offline round trips

```bash
python3 tools/validate_symbol_map.py
python3 tools/symbol_roundtrip.py --format duckstation-csv --output /tmp/abl-re-symbols.csv
python3 tools/symbol_roundtrip.py --format r2 --output /tmp/abl-re-symbols.r2
```

- **DuckStation CSV:** exact fork-compatible header/rows: `address,name,comment` and `0xAAAAAAAA,label,`. The tool reparses the output using the same field boundary documented by `DebuggerControlService::ImportSymbols` and compares all address/name pairs to the source.
- **radare2:** output is one `f label = 0xAAAAAAAA` command per symbol. The tool reparses and compares all pairs. Local r2 5.9.8 also consumed the generated script successfully:

```bash
r2 -2 -q -i /tmp/abl-re-symbols.r2 -c 'fj' /dev/null
```

Result on 2026-06-20: `fj` returned all **85** names at their expected addresses. For actual static work, replace `/dev/null` with the owner-local executable and set MIPS32/little-endian/GP as documented in [[Executable and Overlays]].

The safe pytest suite runs both converter round-trips in a temporary directory. No generated CSV/r2 file is committed.

## Optional local DuckStation import

The fork client supports:

```bash
python3 ~/duckstation/scripts/debugger-client/duckstation_debug_client.py \
  --token '<local token>' sym-import --path "$(pwd)/symbols/re_symbols.sym" --sym-format sym
python3 ~/duckstation/scripts/debugger-client/duckstation_debug_client.py \
  --token '<local token>' sym-export --path /tmp/abl-live-export.csv --sym-format csv
```

This live path was **not run**: no debugger server was active, and the current fork source is dirty/not remotely preserved. A future live result must be labelled local-only until [[DuckStation Fork Reproducibility|GAP-0001]] is closed. Offline DuckStation-format and actual r2 consumption are sufficient for the modding-grade M3 baseline.

## Limitations

- `.sym`, DuckStation CSV, and r2 flags preserve address/name; they do not encode function/global/buffer type or confidence.
- Overlay labels are valid only while the matching module occupies its swap region.
- This proves tool consumption, not the semantic truth of every provisional label; authority remains [[Symbol Map Baseline]].
- Ghidra is now a **confirmed consumer** (cross-check layer, pilot 2026-06-22): Ghidra 12.1.2 (Flatpak) imports `SCUS_942.88` headless and applies `re_symbols.sym` via `ghidra/scripts/ABLPilot.java` (103/104 labels, 34 matched to auto-found functions). The `.sym` file remains authoritative — Ghidra consumes it and never writes back; re-run the script to re-sync after `.sym` changes. Verdict + setup: `ghidra/PILOT_REPORT.md`, `ghidra/README.md`.

## Status

**GAP-0018: Verified for the M3 symbol baseline.** A tracked authoritative map validates, round-trips through a fork-supported representation, and is consumed by r2. Live DuckStation round-trip remains an optional local corroboration, not an M3 blocker.

## Related

[[Symbol Map Baseline]] · [[API - symbols]] · [[Symbols Index]] · [[DuckStation Fork Reproducibility]] · `tools/symbol_roundtrip.py` · `tests/test_symbol_map.py`
