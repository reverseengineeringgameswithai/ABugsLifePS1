---
kind: experiment
id: EXP_2026-07-08_re_baseline_run
name: RE baseline full regeneration run
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_game_identity_and_provenance, SYS_executable_image, SYS_overlays_and_runtime_loading]
fixtures: []
artifacts: [extracted/re_baseline/report.json (regenerable, untracked)]
---

# EXP_2026-07-08_re_baseline_run - RE baseline full regeneration run

## Question
Can the whole RE-basics floor (provenance, exe map, disassembly, overlays, code/data
map, function inventory) be regenerated reproducibly from the owner's media, and do
the results match the recorded Canon values?

## Method
`python tools/re_baseline.py --all` on this host (r2 5.9.8, Python 3.14), plus
`python -m pytest tests/test_disc_provenance.py`.

## Observations
- **provenance: PASS** — disc BIN (CRC32 `607704bb`, MD5, SHA-1), cue SHA-1 and
  `SCUS_942.88` SHA-1/MD5 all match `tools/disc_provenance.json`.
- **exe: PASS** — `PS-X EXE` magic, load `0x80010000`, size `0x72800`, entry
  `0x8005f690`, SP `0x801ffff0`; header+text == exact file size.
- **disasm:** 837 r2 functions, 3,728 strings, 128,441-line listing (untracked).
- **overlays:** 21 blobs analyzed (Region A base `0x800b39a0`, MEMORY.BIN at Region B
  `0x800b5788` → 61 functions).
- **codemap:** 79.4% code + 5.3% strings classified; last function ends `0x8008219c`.
- **inventory:** 1,170 function addresses, 687 named (after PsyQ merge).
- Guard tests 4/4 pass; outputs land in git-ignored `extracted/re_baseline/`.

## Result
SUCCESS — every stage green and idempotent; counts recorded in the Canon notes this
run validates.

## Artifacts
`extracted/re_baseline/{report.json,report.md,provenance.json,exe_map.json,functions.json,strings.json,code_data_map.json,function_inventory.csv,overlays/}` — all regenerable, none committed.
