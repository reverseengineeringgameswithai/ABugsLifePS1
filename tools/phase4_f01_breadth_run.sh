#!/usr/bin/env bash
# Launch N isolated Interpreter instances and run the F01 breadth assertion pass across
# the corpus in parallel, then consolidate.
#
# One DuckStation per worker, each with its own absolute config dir, loopback port and
# token (AGENTS.md). Movies are claimed with atomic `mkdir`, longest first — the wall
# clock is bounded below by the longest single movie (LEVEL15, ~76k frames), so more
# workers than ~8 buys nothing and only adds CPU contention.
#
# Usage: tools/phase4_f01_breadth_run.sh [WORKERS] [BASEPORT] [WORKDIR]
set -euo pipefail

WORKERS="${1:-8}"
BASEPORT="${2:-23500}"
WORKDIR="${3:-/tmp/abl-f01-breadth}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISC="$ROOT/Disney-Pixar A Bug's Life (v1.0).cue"
STOP="$HOME/duckstation/scripts/debugger-client/launch_debugger_instance.sh"

mkdir -p "$WORKDIR"/{claims,results,logs}
echo "workers=$WORKERS baseport=$BASEPORT workdir=$WORKDIR"

pids=(); ports=(); cfgs=()
cleanup() {
  echo "stopping instances..."
  for c in "${cfgs[@]:-}"; do [ -n "$c" ] && "$STOP" stop --config-dir "$c" >/dev/null 2>&1 || true; done
}
trap cleanup EXIT

for i in $(seq 0 $((WORKERS-1))); do
  port=$((BASEPORT+i)); cfg="$WORKDIR/cfg-$port"; tok="f01b-$port"
  mkdir -p "$cfg"
  if "$ROOT/tools/launch_repro_playback.sh" --config-dir "$cfg" --port "$port" \
        --token "$tok" --execution-mode Interpreter --disc "$DISC" \
        > "$WORKDIR/logs/launch-$port.log" 2>&1; then
    ports+=("$port"); cfgs+=("$cfg")
    echo "  instance up on :$port"
  else
    echo "  FAILED to launch :$port (see $WORKDIR/logs/launch-$port.log)"
  fi
done

[ "${#ports[@]}" -eq 0 ] && { echo "no instances started"; exit 1; }

for i in "${!ports[@]}"; do
  port="${ports[$i]}"
  python3 "$ROOT/tools/phase4_f01_breadth_assert.py" --workdir "$WORKDIR" \
      --port "$port" --token "f01b-$port" > "$WORKDIR/logs/worker-$port.log" 2>&1 &
  pids+=("$!")
done
echo "${#pids[@]} worker(s) running; tail $WORKDIR/logs/worker-*.log"

fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done

python3 "$ROOT/tools/phase4_f01_breadth_assert.py" --workdir "$WORKDIR" --consolidate
exit $fail
