#!/usr/bin/env bash
# Executable guard for the B06/B08 frontier claims.
#
# The rows were once called solved on the strength of a census that could not be
# re-run and was wrong twice over: it under-counted readers, and -- worse -- it
# missed every zero-offset aliased-pointer access, including the grant itself.
# This regenerates all four censuses from pristine inputs and fails loudly on drift:
# a site lost, or a site appearing that is not in the reviewed baseline.
#
# It proves the frontier claim is REPRODUCIBLE. It does not prove closure: the
# analysis reports a residual (accesses through a pointer loaded from memory) which
# is demonstrably non-empty -- 0x8004AFB0 lives in it.
set -uo pipefail
cd "$(dirname "$0")/.."

# The pristine EXE and the staged overlay blobs are gitignored (copyrighted), so a clean
# checkout has neither. Detect that up front and say so, instead of letting each census
# report "everything disappeared" as though the frontier had drifted -- which is what a
# clean-clone verification run actually produced before this check existed.
missing=""
[ -f "SCUS_942.88" ] || missing="$missing SCUS_942.88"
[ -d "REBUILD/files" ] || missing="$missing REBUILD/files"
if [ -n "$missing" ]; then
  echo "CENSUS GATE: INPUTS ABSENT -->$missing"
  echo "  These are gitignored pristine inputs, not repository content."
  echo "  Provision with: python3 tools/verify_repro_inputs.py --provision"
  echo "  (this is NOT a frontier failure; the gate cannot run without them)"
  exit 2
fi

fail=0

echo "=== resident: power slot 0x800A657E"
python3 tools/census_address.py 0x800A657E --block 0x800A6500 \
  --expect analysis/phase4_b06_b08_census_expected.json \
  --json analysis/phase4_b06_b08_census_657e.json | tail -6 || fail=1

echo
echo "=== resident: true health 0x800A6594"
python3 tools/census_address.py 0x800A6594 --block 0x800A6500 \
  --expect analysis/phase4_b06_b08_census_expected_6594.json \
  --json analysis/phase4_b06_b08_census_6594.json | tail -6 || fail=1

echo
echo "=== callee writes (memset/memcpy performed by a callee, invisible to store sites)"
python3 tools/census_callee_writes.py 0x800A657E \
  --json analysis/phase4_callee_writes.json | tail -4 || fail=1

echo
echo "=== overlays: per-level LEVEL*.BIN + MEMORY.BIN"
python3 tools/census_overlays.py 0x800A657E \
  --extra REBUILD/files/BITS/MEMORY.BIN:0x800b5788 \
  --json analysis/phase4_b06_b08_census_overlays.json | head -1 || fail=1
python3 tools/census_overlays.py 0x800A6594 \
  --extra REBUILD/files/BITS/MEMORY.BIN:0x800b5788 \
  --json analysis/phase4_b06_b08_census_overlays_6594.json | head -1 || fail=1
python3 tools/check_overlay_census_baseline.py || fail=1

echo
echo "=== runtime writer union (empirical; needs an emulator, skipped with --static-only)"
if [ "${1:-}" != "--static-only" ]; then
  python3 tools/phase4_b06_b08_writer_union.py 23800 | tail -2 || fail=1
else
  echo "  skipped (--static-only)"
fi

echo
if [ "$fail" -ne 0 ]; then
  echo "CENSUS GATE: FAIL -- the frontier changed; review before updating the baselines."
  exit 1
fi
echo "CENSUS GATE: PASS"
