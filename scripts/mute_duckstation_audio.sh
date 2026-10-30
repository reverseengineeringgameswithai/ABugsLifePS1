#!/usr/bin/env bash
# Mutes DuckStation's PipeWire/PulseAudio playback stream (not DuckStation's in-app volume).
set -euo pipefail

ids=$(pactl list sink-inputs | awk '
  /^Sink Input #/ { id = $3; sub("#", "", id) }
  /application\.name = "DuckStation"/ { print id }
')

if [ -z "$ids" ]; then
  echo "No DuckStation sink-input found. Is DuckStation running?" >&2
  exit 1
fi

for id in $ids; do
  pactl set-sink-input-mute "$id" 1
  echo "Muted sink-input #$id"
done
