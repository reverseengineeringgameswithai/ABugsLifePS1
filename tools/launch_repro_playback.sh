#!/usr/bin/env bash
# Launch an isolated DuckStation whose emulation config REPRODUCES the environment the
# go_to_end movies were recorded in, so from-boot input movies replay 1:1 (no desync).
#
# WHY THIS EXISTS (hard-won — see Session/EXP notes): a from_boot movie is only
# deterministic when PLAYBACK matches RECORDING. Two things silently desync it while the
# movie's own `reproducible` flag stays true, because the movie system tracks neither:
#   1. CPU execution mode — playback must match RECORDING. Default here is
#      CachedInterpreter because the original go_to_end movies were recorded that way.
#      ⚠️ A CachedInterpreter movie CANNOT be traced: arming any accessLog watch,
#      execTrace or breakpoint forces CPUExecutionMode::Interpreter (see
#      CPU::CheckForExecutionModeChange), which is a mode change mid-replay and desyncs
#      it SILENTLY. Record on Interpreter and pass --execution-mode Interpreter here for
#      anything you intend to instrument; then arming requests the mode already in use
#      and nothing switches. See EXP_2026-07-31_interpreter_movies_survive_instrumentation.
#   2. Memory card — the recording booted with the owner's card (2 ABL saves). A blank
#      card sends BIOS/menu navigation down a different path → early desync. We seed the
#      card from a pristine snapshot before every boot so replay-saves never accumulate.
# The generic scripts/debugger fork launcher writes a minimal settings.ini with NO [CPU]
# section, so it CANNOT be used for movie replay — this wrapper owns the repro config.
#
#   tools/launch_repro_playback.sh [--config-dir DIR] [--port N] [--token T] [--disc CUE]
#                                  [--card-seed MCD] [--binary DUCKSTATION]
#                                  [--fork-launcher LAUNCHER] [--client CLIENT]
#                                  [--bootstrap-fastboot] [--display :0]
# Prints "READY ..." on success. Stop with the same fork launcher's `stop --config-dir`.
set -euo pipefail

CONFIG_DIR="${DSREPRO_CONFIG_DIR:-/tmp/dsrepro}"
PORT=23460
TOKEN="debugger-1000"
DISPLAY_ARG="${DISPLAY:-:0}"
BINARY="$HOME/duckstation/build-release/bin/duckstation-qt"
BIOS_DIR="$HOME/.local/share/duckstation/bios"
CARD_SEED="$HOME/.cache/abl/abl_card_seed.mcd"
CARD_NAME="Disney-Pixar A Bug's Life (USA)_1.mcd"
DISC=""
FORK_LAUNCHER="$HOME/duckstation/scripts/debugger-client/launch_debugger_instance.sh"
CLIENT="$HOME/duckstation/scripts/debugger-client/duckstation_debug_client.py"
BOOTSTRAP_FASTBOOT=0
EXEC_MODE="${EXEC_MODE:-CachedInterpreter}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execution-mode) EXEC_MODE="$2"; shift 2;;
    --config-dir) CONFIG_DIR="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    --token) TOKEN="$2"; shift 2;;
    --disc) DISC="$2"; shift 2;;
    --card-seed) CARD_SEED="$2"; shift 2;;
    --binary) BINARY="$2"; shift 2;;
    --fork-launcher) FORK_LAUNCHER="$2"; shift 2;;
    --client) CLIENT="$2"; shift 2;;
    --bootstrap-fastboot) BOOTSTRAP_FASTBOOT=1; shift;;
    --display) DISPLAY_ARG="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

[[ -x "$BINARY" ]] || { echo "duckstation-qt not found at $BINARY" >&2; exit 1; }
[[ -x "$FORK_LAUNCHER" ]] || { echo "fork launcher not found at $FORK_LAUNCHER" >&2; exit 1; }
[[ -f "$CLIENT" ]] || { echo "debugger client not found at $CLIENT" >&2; exit 1; }
[[ -f "$CARD_SEED" ]] || { echo "card seed not found at $CARD_SEED" >&2; exit 1; }
[[ -n "$DISC" && -f "$DISC" ]] || { echo "disc not found: $DISC" >&2; exit 1; }

# Stop any prior instance from this config-dir (reuse the fork launcher's clean, PID-scoped stop).
bash "$FORK_LAUNCHER" stop --config-dir "$CONFIG_DIR" --binary "$BINARY" >/dev/null 2>&1 || true
sleep 1

mkdir -p "$CONFIG_DIR/duckstation/memcards" "$CONFIG_DIR/runtime"
chmod 700 "$CONFIG_DIR/runtime"

# Seed the memory card fresh from the pristine snapshot every launch (relative Directory=memcards
# keeps the isolated instance from ever touching the owner's real card).
cp "$CARD_SEED" "$CONFIG_DIR/duckstation/memcards/$CARD_NAME"

# Determinism-matched settings.ini (mirrors ~/.local/share/duckstation/settings.ini for every
# emulation-affecting key; adds the ExternalDebugger block). Do NOT add PGXP/overclock/8MB-RAM.
cat > "$CONFIG_DIR/duckstation/settings.ini" <<EOF
[Main]
SetupWizardIncomplete=false
KeepWindowInBackground=true

[UI]
UnofficialBuildWarningConfirmed=true

[AutoUpdater]
CheckAtStartup=false

[Logging]
LogLevel=Info
LogToConsole=true
LogToFile=true
LogToWindow=false

[BIOS]
SearchDirectory=$BIOS_DIR
PatchFastBoot=false

[Display]
# Observability only -- the OSD is an overlay and touches no emulation state, so these
# do not affect replay determinism. Matches the operator's own profile so a repro
# instance looks like the one they debug in: the frame number on screen (which is what
# you compare against a movie's frame count) and the input display, which shows the
# buttons the movie is actually feeding the pad. Without this block the launcher wrote
# a settings.ini with no [Display] section at all, so a repro instance showed neither --
# which reads as "the build is outdated" when it is only unconfigured.
ShowOSDMessages=true
ShowFrameNumber=true
ShowInputs=true
ShowFPS=false
ShowSpeed=false
ShowFrameTimes=false
OSDMessageLocation=TopLeft
OSDScale=100

[Console]
Enable8MBRAM=false
Region=Auto

[CPU]
ExecutionMode=$EXEC_MODE
FastmemMode=MMap
OverclockEnable=false
OverclockNumerator=1
OverclockDenominator=1
RecompilerBlockLinking=true
RecompilerICache=false
RecompilerMemoryExceptions=false

[MemoryCards]
Card1Type=PerGameTitle
Card2Type=None
Directory=memcards

[ControllerPorts]
MultitapMode=Disabled

[Pad1]
Type=AnalogController

[ExternalDebugger]
Enabled=true
Port=$PORT
BindAddress=127.0.0.1
AuthToken=$TOKEN
EOF

# Launch directly (NOT via the fork launcher, which would overwrite settings.ini).
# The movies were recorded from a full boot (PatchFastBoot=false).  On forks that
# do not bring up the debugger server during the initial full BIOS boot,
# --bootstrap-fastboot may be used solely to establish the RPC connection: each
# from-boot movie's startPlayback(load_start_state=true) then power-cycles the
# console before frame 0, which is the cold-boot evidence boundary.
# Detach from the launcher shell just like the generic fork launcher. Without
# setsid + a closed stdin, non-interactive callers can report READY and then
# reap DuckStation as soon as the launching shell exits, making the documented
# repro command unusable from a clean automation session.
BOOT_ARGS=()
[[ "$BOOTSTRAP_FASTBOOT" -eq 1 ]] && BOOT_ARGS+=("-fastboot")
setsid env XDG_CONFIG_HOME="$CONFIG_DIR" XDG_RUNTIME_DIR="$CONFIG_DIR/runtime" \
  DISPLAY="$DISPLAY_ARG" QT_QPA_PLATFORM=xcb \
  "$BINARY" "${BOOT_ARGS[@]}" "$DISC" </dev/null >"$CONFIG_DIR/ds.log" 2>&1 &
PID=$!
# Match the fork launcher's pidfile ($CONFIG_DIR/instance.pid) so `stop --config-dir` finds us.
echo "$PID" > "$CONFIG_DIR/instance.pid"

for i in $(seq 1 40); do
  if python3 "$CLIENT" --quiet --port "$PORT" --token "$TOKEN" status >/dev/null 2>&1; then
    # Report the mode ACTUALLY written to settings.ini. This line used to print the
    # literal "CachedInterpreter" no matter what --execution-mode asked for, which is a
    # trap in a launcher whose whole job is mode-matching: a correct Interpreter launch
    # reads back as the one mode that cannot be traced.
    echo "READY pid=$PID port=$PORT token=$TOKEN config=$CONFIG_DIR ($EXEC_MODE, card-seeded)"
    exit 0
  fi
  kill -0 "$PID" 2>/dev/null || { echo "duckstation exited early; see $CONFIG_DIR/ds.log" >&2; exit 1; }
  sleep 1
done
echo "API did not come up within 40s; see $CONFIG_DIR/ds.log" >&2
exit 1
