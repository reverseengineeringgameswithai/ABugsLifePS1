#!/usr/bin/env bash
# Flik's Phase-4 Method Ratchet
#
# Autonomous ABL phase executor/verifier loop. The outer invocation starts a
# detached, HUP-resistant controller and opens a terminal that only follows its
# durable log. Closing that viewer cannot kill the controller. The operator working
# tree is used only as the repository/fixture source and is never edited by this
# script; Git worktree metadata is added for the isolated branch.

set -Eeuo pipefail

SCRIPT_NAME="Flik's Phase-4 Method Ratchet"
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"

usage() {
  cat <<'EOF'
Flik's Phase-4 Method Ratchet — evidence-funnel implement/verify loop

Usage:
  tools/flik_phase4_method_ratchet.sh [options]

The default invocation starts a detached controller, opens a GNOME Terminal log
viewer, and returns immediately. Closing the viewer does not stop the controller.

Options:
  --phase N              Roadmap phase to close (must be 4)
  --contract FILE        Acceptance contract. Default for Phase N:
                         engineering-specs/phaseN-closure.md when present,
                         otherwise the roadmap hub.
  --initial-context FILE Persistent run context passed verbatim to every
                         executor iteration. It informs the audit but cannot
                         override the roadmap or acceptance contract.
  --verify-first-claim FILE
                         Run a fresh verifier against --seed-ref before starting
                         another executor. If rejected, its exact gaps seed the
                         normal implementation loop. FILE may be a structurally
                         invalid prior closure claim; it is evidence, not authority.
  --selection-policy POLICY
                         Work-order policy: closure-debt (existing default) or
                         movie-ready. movie-ready uses the generated, preserved
                         movie/start-state queue without changing closure criteria.
  --seed-ref REF         Git commit/branch used for the isolated worktree
                         (default: current HEAD)
  --repo DIR             ABL operator repository (default: containing repo)
  --model MODEL          Codex model override (default: Codex configuration)
  --fast                 Run every Codex executor, seed-repair agent, and fresh
                         verifier with Fast mode (`service_tier="fast"` and
                         `features.fast_mode=true`). This increases supported-model
                         speed and credit consumption.
  --max-iterations N     Maximum terminal iterations. The default, 0, is unlimited;
                         use a positive value only for an explicit bounded run.
  --run-root DIR         Durable logs/state root
                         (default: ~/.local/state/flik-phase4-method-ratchet)
  --sandbox MODE         Codex sandbox mode (default: danger-full-access;
                         required for local DuckStation automation)
  --here                 Run in the current terminal instead of opening one
  --dry-run              Validate configuration without creating a worktree
  -h, --help             Show this help

Safe boundary stop for an active run:
  touch <run-root>/runs/<run-id>/stop-after-iteration

The sentinel is checked before every new executor iteration. The active executor
and any verifier belonging to its claim finish first; no following executor starts.
Committed trial-control changes and failed post-commit evidence reports automatically
chain into a fresh, seed-verified trial. The same controller PID and viewer survive;
a progress-sensitive circuit stops only after three semantically identical reseeds
with unchanged closure debt. Advancing candidates do not consume a lifetime quota.

Example from an existing Codex session:
  tools/flik_phase4_method_ratchet.sh \
    --phase 4 \
    --contract engineering-specs/phase4-closure.md \
    --seed-ref ratchet/phase4-method-v2-bootstrap

Decisions are machine-readable:
  closed            Executor believes every criterion is met. A fresh verifier
                    must independently agree before the script finishes.
  open_autonomous   Work remains but no operator-only input is required. The
                    next fresh executor receives the verifier/executor gaps.
  blocked_external  A specific operator fixture/recording/decision is required.
                    A fresh verifier must confirm the blocker before pausing.

The script never merges its branch into the operator branch.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

note() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*"
}

contains_arg() {
  local needle="$1"
  shift
  local arg
  for arg in "$@"; do
    [[ "$arg" == "$needle" ]] && return 0
  done
  return 1
}

if contains_arg "--help" "$@" || contains_arg "-h" "$@"; then
  usage
  exit 0
fi

# Start the controller outside the terminal's process/session tree. The GNOME
# Terminal is only a viewer, so closing it cannot SIGHUP the controller or its Codex
# child. Controller output is durable even if no viewer remains open.
if ! contains_arg "--internal-run" "$@" && ! contains_arg "--here" "$@"; then
  command -v gnome-terminal >/dev/null 2>&1 ||
    die "gnome-terminal is unavailable; rerun with --here"
  command -v setsid >/dev/null 2>&1 || die "setsid is unavailable"
  command -v nohup >/dev/null 2>&1 || die "nohup is unavailable"
  command -v tail >/dev/null 2>&1 || die "tail is unavailable"
  child=("$SCRIPT_PATH" --internal-run "$@")
  launcher_root="${XDG_STATE_HOME:-$HOME/.local/state}/flik-phase4-method-ratchet/launchers"
  launcher_id="$(date +%Y%m%d-%H%M%S)-$$"
  launcher_dir="$launcher_root/$launcher_id"
  launcher_log="$launcher_dir/controller.log"
  launcher_pidfile="$launcher_dir/controller.pid"
  mkdir -p "$launcher_dir"
  : >"$launcher_log"
  nohup setsid "${child[@]}" </dev/null >>"$launcher_log" 2>&1 &
  controller_pid=$!
  printf '%s\n' "$controller_pid" >"$launcher_pidfile"
  {
    printf 'launcher_id=%s\n' "$launcher_id"
    printf 'controller_pid=%s\n' "$controller_pid"
    printf 'controller_log=%s\n' "$launcher_log"
    printf 'started=%s\n' "$(date --iso-8601=seconds)"
  } >"$launcher_dir/launcher.env"
  printf -v quoted_log '%q' "$launcher_log"
  viewer_cmd="tail --pid=$controller_pid -n +1 -F $quoted_log; printf '\\n%s\\n' 'Flik ratchet controller finished. Press Enter to close this viewer.'; read -r _"
  if ! gnome-terminal --title="$SCRIPT_NAME" -- bash -lc "$viewer_cmd"; then
    note "viewer failed to open; detached controller continues"
  fi
  note "launched detached controller pid $controller_pid"
  note "viewer log: $launcher_log"
  exit 0
fi

PHASE=4
CONTRACT=""
INITIAL_CONTEXT=""
VERIFY_FIRST_CLAIM=""
SELECTION_POLICY="closure-debt"
SEED_REF="HEAD"
REPO=""
MODEL=""
FAST_MODE=0
MAX_ITERATIONS=0
RUN_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/flik-phase4-method-ratchet"
SANDBOX="danger-full-access"
DRY_RUN=0
AUTO_RESEED_DEPTH=0
RESEED_SIGNATURE=""
RESEED_REPEAT_COUNT=0
MAX_IDENTICAL_RESEEDS=3
PARENT_RUN=""
CONTINUATION_REASON=""
PREVIOUS_MOVIE_READY_PACKET=""
PREVIOUS_MOVIE_READY_PROGRESS=""
PREVIOUS_MOVIE_READY_QUEUE=""
PREVIOUS_MOVIE_READY_DEBT_BEFORE=""
PREVIOUS_MOVIE_READY_DEBT_AFTER=""

while (($#)); do
  case "$1" in
    --phase)
      (($# >= 2)) || die "--phase requires a value"
      PHASE="$2"
      shift 2
      ;;
    --contract)
      (($# >= 2)) || die "--contract requires a value"
      CONTRACT="$2"
      shift 2
      ;;
    --initial-context)
      (($# >= 2)) || die "--initial-context requires a value"
      INITIAL_CONTEXT="$2"
      shift 2
      ;;
    --verify-first-claim)
      (($# >= 2)) || die "--verify-first-claim requires a value"
      VERIFY_FIRST_CLAIM="$2"
      shift 2
      ;;
    --selection-policy)
      (($# >= 2)) || die "--selection-policy requires a value"
      SELECTION_POLICY="$2"
      shift 2
      ;;
    --seed-ref)
      (($# >= 2)) || die "--seed-ref requires a value"
      SEED_REF="$2"
      shift 2
      ;;
    --repo)
      (($# >= 2)) || die "--repo requires a value"
      REPO="$2"
      shift 2
      ;;
    --model)
      (($# >= 2)) || die "--model requires a value"
      MODEL="$2"
      shift 2
      ;;
    --fast)
      FAST_MODE=1
      shift
      ;;
    --max-iterations)
      (($# >= 2)) || die "--max-iterations requires a value"
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --run-root)
      (($# >= 2)) || die "--run-root requires a value"
      RUN_ROOT="$2"
      shift 2
      ;;
    --sandbox)
      (($# >= 2)) || die "--sandbox requires a value"
      SANDBOX="$2"
      shift 2
      ;;
    --auto-reseed-depth)
      (($# >= 2)) || die "--auto-reseed-depth requires a value"
      AUTO_RESEED_DEPTH="$2"
      shift 2
      ;;
    --reseed-signature)
      (($# >= 2)) || die "--reseed-signature requires a value"
      RESEED_SIGNATURE="$2"
      shift 2
      ;;
    --reseed-repeat-count)
      (($# >= 2)) || die "--reseed-repeat-count requires a value"
      RESEED_REPEAT_COUNT="$2"
      shift 2
      ;;
    --max-identical-reseeds)
      (($# >= 2)) || die "--max-identical-reseeds requires a value"
      MAX_IDENTICAL_RESEEDS="$2"
      shift 2
      ;;
    --parent-run)
      (($# >= 2)) || die "--parent-run requires a value"
      PARENT_RUN="$2"
      shift 2
      ;;
    --continuation-reason)
      (($# >= 2)) || die "--continuation-reason requires a value"
      CONTINUATION_REASON="$2"
      shift 2
      ;;
    --previous-movie-ready-packet)
      (($# >= 2)) || die "--previous-movie-ready-packet requires a value"
      PREVIOUS_MOVIE_READY_PACKET="$2"
      shift 2
      ;;
    --previous-movie-ready-progress)
      (($# >= 2)) || die "--previous-movie-ready-progress requires a value"
      PREVIOUS_MOVIE_READY_PROGRESS="$2"
      shift 2
      ;;
    --previous-movie-ready-queue)
      (($# >= 2)) || die "--previous-movie-ready-queue requires a value"
      PREVIOUS_MOVIE_READY_QUEUE="$2"
      shift 2
      ;;
    --previous-movie-ready-debt-before)
      (($# >= 2)) || die "--previous-movie-ready-debt-before requires a value"
      PREVIOUS_MOVIE_READY_DEBT_BEFORE="$2"
      shift 2
      ;;
    --previous-movie-ready-debt-after)
      (($# >= 2)) || die "--previous-movie-ready-debt-after requires a value"
      PREVIOUS_MOVIE_READY_DEBT_AFTER="$2"
      shift 2
      ;;
    --here|--internal-run)
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

[[ "$PHASE" =~ ^[0-9]+$ ]] || die "phase must be a non-negative integer"
[[ "$PHASE" == "4" ]] || die "this controller implements the Phase-4 method only"
[[ "$MAX_ITERATIONS" =~ ^[0-9]+$ ]] ||
  die "max iterations must be a non-negative integer"
[[ "$AUTO_RESEED_DEPTH" =~ ^[0-9]+$ ]] ||
  die "auto-reseed depth must be a non-negative integer"
[[ "$RESEED_REPEAT_COUNT" =~ ^[0-9]+$ ]] ||
  die "reseed repeat count must be a non-negative integer"
[[ "$MAX_IDENTICAL_RESEEDS" =~ ^[2-9][0-9]*$ ]] ||
  die "max identical reseeds must be at least 2"
[[ -z "$RESEED_SIGNATURE" || "$RESEED_SIGNATURE" =~ ^[0-9a-f]{64}$ ]] ||
  die "reseed signature must be an empty or lowercase SHA-256"
case "$SELECTION_POLICY" in
  closure-debt|movie-ready) ;;
  *) die "invalid selection policy: $SELECTION_POLICY" ;;
esac
case "$SANDBOX" in
  read-only|workspace-write|danger-full-access) ;;
  *) die "invalid Codex sandbox: $SANDBOX" ;;
esac

command -v git >/dev/null 2>&1 || die "git is not installed"
command -v codex >/dev/null 2>&1 || die "codex is not installed"
command -v python3 >/dev/null 2>&1 || die "python3 is not installed"

if [[ -z "$REPO" ]]; then
  REPO="$(git -C "$(dirname "$SCRIPT_PATH")" rev-parse --show-toplevel)"
fi
REPO="$(readlink -f "$REPO")"
RUN_ROOT="$(readlink -m "$RUN_ROOT")"
git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
  die "not a Git worktree: $REPO"
if [[ "$RUN_ROOT" == "$REPO" || "$RUN_ROOT" == "$REPO/"* ]]; then
  die "run root must be outside the operator repository: $RUN_ROOT"
fi
git -C "$REPO" rev-parse --verify "${SEED_REF}^{commit}" >/dev/null 2>&1 ||
  die "seed ref does not resolve to a commit: $SEED_REF"

CONTRACT_REL=""
CONTRACT_DISPLAY=""
if [[ -z "$CONTRACT" ]]; then
  phase_contract="engineering-specs/phase${PHASE}-closure.md"
  roadmap="ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md"
  if git -C "$REPO" cat-file -e "${SEED_REF}:${phase_contract}" 2>/dev/null; then
    CONTRACT_REL="$phase_contract"
  else
    CONTRACT_REL="$roadmap"
  fi
elif [[ "$CONTRACT" != /* ]]; then
  CONTRACT_REL="${CONTRACT#./}"
  case "/$CONTRACT_REL/" in
    */../*) die "relative contract may not escape the seed tree: $CONTRACT" ;;
  esac
else
  CONTRACT="$(readlink -f "$CONTRACT")"
  [[ -f "$CONTRACT" ]] || die "acceptance contract not found: $CONTRACT"
fi
if [[ -n "$CONTRACT_REL" ]]; then
  git -C "$REPO" cat-file -e "${SEED_REF}:${CONTRACT_REL}" 2>/dev/null ||
    die "acceptance contract is absent from seed commit: $CONTRACT_REL"
  CONTRACT_DISPLAY="${SEED_REF}:${CONTRACT_REL}"
else
  CONTRACT_DISPLAY="$CONTRACT"
fi
git -C "$REPO" cat-file -e "${SEED_REF}:AGENTS.md" 2>/dev/null ||
  die "AGENTS.md is absent from seed commit: $SEED_REF"
if [[ -n "$INITIAL_CONTEXT" ]]; then
  if [[ "$INITIAL_CONTEXT" != /* ]]; then
    INITIAL_CONTEXT="$REPO/$INITIAL_CONTEXT"
  fi
  INITIAL_CONTEXT="$(readlink -f "$INITIAL_CONTEXT")"
  [[ -f "$INITIAL_CONTEXT" ]] || die "initial context not found: $INITIAL_CONTEXT"
fi
if [[ -n "$VERIFY_FIRST_CLAIM" ]]; then
  if [[ "$VERIFY_FIRST_CLAIM" != /* ]]; then
    VERIFY_FIRST_CLAIM="$REPO/$VERIFY_FIRST_CLAIM"
  fi
  VERIFY_FIRST_CLAIM="$(readlink -f "$VERIFY_FIRST_CLAIM")"
  [[ -f "$VERIFY_FIRST_CLAIM" ]] ||
    die "verify-first claim not found: $VERIFY_FIRST_CLAIM"
fi
if [[ -n "$PREVIOUS_MOVIE_READY_PACKET" ]]; then
  PREVIOUS_MOVIE_READY_PACKET="$(readlink -f "$PREVIOUS_MOVIE_READY_PACKET")"
  [[ -f "$PREVIOUS_MOVIE_READY_PACKET" ]] ||
    die "previous movie-ready packet not found: $PREVIOUS_MOVIE_READY_PACKET"
fi
if [[ -n "$PREVIOUS_MOVIE_READY_PROGRESS" ]]; then
  PREVIOUS_MOVIE_READY_PROGRESS="$(readlink -f "$PREVIOUS_MOVIE_READY_PROGRESS")"
  [[ -f "$PREVIOUS_MOVIE_READY_PROGRESS" ]] ||
    die "previous movie-ready progress not found: $PREVIOUS_MOVIE_READY_PROGRESS"
fi
for previous_name in QUEUE DEBT_BEFORE DEBT_AFTER; do
  previous_variable="PREVIOUS_MOVIE_READY_${previous_name}"
  previous_value="${!previous_variable}"
  if [[ -n "$previous_value" ]]; then
    previous_value="$(readlink -f "$previous_value")"
    [[ -f "$previous_value" ]] ||
      die "previous movie-ready ${previous_name,,} not found: $previous_value"
    printf -v "$previous_variable" '%s' "$previous_value"
  fi
done
previous_movie_ready_count=0
for previous_value in "$PREVIOUS_MOVIE_READY_PACKET" \
    "$PREVIOUS_MOVIE_READY_PROGRESS" "$PREVIOUS_MOVIE_READY_QUEUE" \
    "$PREVIOUS_MOVIE_READY_DEBT_BEFORE" "$PREVIOUS_MOVIE_READY_DEBT_AFTER"; do
  [[ -z "$previous_value" ]] || previous_movie_ready_count=$((previous_movie_ready_count + 1))
done
if ((previous_movie_ready_count != 0 && previous_movie_ready_count != 5)); then
  die "previous movie-ready packet/progress/queue/debt-before/debt-after must be supplied together"
fi
if [[ "$SELECTION_POLICY" != "movie-ready" ]] && \
   ((previous_movie_ready_count)); then
  die "previous movie-ready state requires --selection-policy movie-ready"
fi

CODEX_VERSION="$(codex --version)"
CODEX_AUTH="$(codex login status 2>&1 || true)"
[[ "$CODEX_AUTH" == *"Logged in"* ]] || die "Codex is not authenticated: $CODEX_AUTH"

note "repository: $REPO"
note "phase: $PHASE"
note "selection policy: $SELECTION_POLICY"
note "contract: $CONTRACT_DISPLAY"
if [[ -n "$INITIAL_CONTEXT" ]]; then
  note "initial context: $INITIAL_CONTEXT"
fi
if [[ -n "$VERIFY_FIRST_CLAIM" ]]; then
  note "verify-first claim: $VERIFY_FIRST_CLAIM"
fi
note "seed: $(git -C "$REPO" rev-parse "${SEED_REF}^{commit}") ($SEED_REF)"
note "Codex: $CODEX_VERSION"
if ((FAST_MODE)); then
  note "Codex Fast mode: enabled for every executor and verifier"
else
  note "Codex Fast mode: disabled"
fi
note "sandbox: $SANDBOX"
if [[ -n "$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)" ]]; then
  note "operator repository is dirty; it will remain untouched"
fi

if ((DRY_RUN)); then
  if [[ "$SELECTION_POLICY" == "movie-ready" ]]; then
    git -C "$REPO" cat-file -e \
      "${SEED_REF}:tools/phase4_movie_priority.py" 2>/dev/null ||
      die "movie-ready generator is absent from seed commit"
    git -C "$REPO" cat-file -e \
      "${SEED_REF}:analysis/phase4_movie_priority_queue.json" 2>/dev/null ||
      die "movie-ready queue is absent from seed commit"
  fi
  note "dry run passed with selection policy $SELECTION_POLICY; no worktree or Codex session created"
  exit 0
fi

mkdir -p "$RUN_ROOT"
reseed_suffix=""
if ((AUTO_RESEED_DEPTH > 0)); then
  reseed_suffix="-r${AUTO_RESEED_DEPTH}"
fi
RUN_ID="phase${PHASE}-$(date +%Y%m%d-%H%M%S)-$$${reseed_suffix}"
RUN_DIR="$RUN_ROOT/runs/$RUN_ID"
WORKTREE="$RUN_ROOT/worktrees/$RUN_ID"
BRANCH="ratchet/phase${PHASE}-${RUN_ID#phase${PHASE}-}"
mkdir -p "$RUN_DIR" "$(dirname "$WORKTREE")"
METHOD_NOTE_REL="ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Reverse Engineering Operating Method.md"

if [[ -n "$CONTRACT_REL" ]]; then
  git -C "$REPO" show "${SEED_REF}:${CONTRACT_REL}" \
    >"$RUN_DIR/acceptance-contract.md"
else
  cp -- "$CONTRACT" "$RUN_DIR/acceptance-contract.md"
fi
git -C "$REPO" show "${SEED_REF}:AGENTS.md" >"$RUN_DIR/AGENTS.snapshot.md"
CONTRACT="$RUN_DIR/acceptance-contract.md"
sha256sum "$RUN_DIR/acceptance-contract.md" >"$RUN_DIR/acceptance-contract.sha256"
INITIAL_CONTEXT_SNAPSHOT=""
if [[ -n "$INITIAL_CONTEXT" ]]; then
  INITIAL_CONTEXT_SNAPSHOT="$RUN_DIR/initial-context.md"
  cp -- "$INITIAL_CONTEXT" "$INITIAL_CONTEXT_SNAPSHOT"
  sha256sum "$INITIAL_CONTEXT_SNAPSHOT" >"$RUN_DIR/initial-context.sha256"
fi
VERIFY_FIRST_CLAIM_SNAPSHOT=""
if [[ -n "$VERIFY_FIRST_CLAIM" ]]; then
  VERIFY_FIRST_CLAIM_SNAPSHOT="$RUN_DIR/verify-first-claim.json"
  cp -- "$VERIFY_FIRST_CLAIM" "$VERIFY_FIRST_CLAIM_SNAPSHOT"
  sha256sum "$VERIFY_FIRST_CLAIM_SNAPSHOT" \
    >"$RUN_DIR/verify-first-claim.sha256"
fi
PREVIOUS_MOVIE_READY_PACKET_SNAPSHOT=""
PREVIOUS_MOVIE_READY_PROGRESS_SNAPSHOT=""
PREVIOUS_MOVIE_READY_QUEUE_SNAPSHOT=""
PREVIOUS_MOVIE_READY_DEBT_BEFORE_SNAPSHOT=""
PREVIOUS_MOVIE_READY_DEBT_AFTER_SNAPSHOT=""
if [[ -n "$PREVIOUS_MOVIE_READY_PACKET" ]]; then
  PREVIOUS_MOVIE_READY_PACKET_SNAPSHOT="$RUN_DIR/previous-movie-ready-packet.json"
  cp -- "$PREVIOUS_MOVIE_READY_PACKET" "$PREVIOUS_MOVIE_READY_PACKET_SNAPSHOT"
  sha256sum "$PREVIOUS_MOVIE_READY_PACKET_SNAPSHOT" \
    >"$RUN_DIR/previous-movie-ready-packet.sha256"
fi
if [[ -n "$PREVIOUS_MOVIE_READY_PROGRESS" ]]; then
  PREVIOUS_MOVIE_READY_PROGRESS_SNAPSHOT="$RUN_DIR/previous-movie-ready-progress.json"
  cp -- "$PREVIOUS_MOVIE_READY_PROGRESS" "$PREVIOUS_MOVIE_READY_PROGRESS_SNAPSHOT"
  sha256sum "$PREVIOUS_MOVIE_READY_PROGRESS_SNAPSHOT" \
    >"$RUN_DIR/previous-movie-ready-progress.sha256"
fi
if [[ -n "$PREVIOUS_MOVIE_READY_QUEUE" ]]; then
  PREVIOUS_MOVIE_READY_QUEUE_SNAPSHOT="$RUN_DIR/previous-movie-ready-queue.json"
  cp -- "$PREVIOUS_MOVIE_READY_QUEUE" "$PREVIOUS_MOVIE_READY_QUEUE_SNAPSHOT"
  sha256sum "$PREVIOUS_MOVIE_READY_QUEUE_SNAPSHOT" \
    >"$RUN_DIR/previous-movie-ready-queue.sha256"
fi
if [[ -n "$PREVIOUS_MOVIE_READY_DEBT_BEFORE" ]]; then
  PREVIOUS_MOVIE_READY_DEBT_BEFORE_SNAPSHOT="$RUN_DIR/previous-movie-ready-debt-before.json"
  cp -- "$PREVIOUS_MOVIE_READY_DEBT_BEFORE" \
    "$PREVIOUS_MOVIE_READY_DEBT_BEFORE_SNAPSHOT"
  sha256sum "$PREVIOUS_MOVIE_READY_DEBT_BEFORE_SNAPSHOT" \
    >"$RUN_DIR/previous-movie-ready-debt-before.sha256"
fi
if [[ -n "$PREVIOUS_MOVIE_READY_DEBT_AFTER" ]]; then
  PREVIOUS_MOVIE_READY_DEBT_AFTER_SNAPSHOT="$RUN_DIR/previous-movie-ready-debt-after.json"
  cp -- "$PREVIOUS_MOVIE_READY_DEBT_AFTER" \
    "$PREVIOUS_MOVIE_READY_DEBT_AFTER_SNAPSHOT"
  sha256sum "$PREVIOUS_MOVIE_READY_DEBT_AFTER_SNAPSHOT" \
    >"$RUN_DIR/previous-movie-ready-debt-after.sha256"
fi

cat >"$RUN_DIR/decision.schema.json" <<'JSON'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "phase": {"type": "integer", "const": 4},
    "status": {
      "type": "string",
      "enum": ["closed", "open_autonomous", "blocked_external"]
    },
    "summary": {"type": "string"},
    "gaps": {"type": "array", "items": {"type": "string"}},
    "gap_codes": {"type": "array", "items": {"type": "string"}},
    "falsifier_results": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "id": {"type": "string"},
          "outcome": {"type": "string", "enum": ["survived", "falsified", "not_run"]},
          "evidence": {"type": "string"}
        },
        "required": ["id", "outcome", "evidence"]
      }
    },
    "verified_live_receipt_sha256s": {
      "type": "array", "items": {"type": "string"}
    },
    "method_exceptions": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "code": {"type": "string"},
          "live_receipt_sha256": {"type": "string"},
          "boundary_mismatch": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
              "clock": {"type": "string"},
              "capture_start": {"type": "integer"},
              "capture_stop": {"type": "integer"},
              "prelude_start": {"type": "integer"},
              "prelude_stop": {"type": "integer"},
              "predicate": {
                "type": "string",
                "enum": ["PRECISE_WINDOW_UNAVOIDABLE"]
              }
            },
            "required": [
              "clock", "capture_start", "capture_stop",
              "prelude_start", "prelude_stop", "predicate"
            ]
          }
        },
        "required": ["code", "live_receipt_sha256", "boundary_mismatch"]
      }
    },
    "evidence": {"type": "array", "items": {"type": "string"}},
    "validation": {"type": "array", "items": {"type": "string"}},
    "required_input": {"type": "string"},
    "candidate_commit": {"type": "string"}
  },
  "required": [
    "phase", "status", "summary", "gaps", "gap_codes",
    "falsifier_results", "verified_live_receipt_sha256s",
    "method_exceptions", "evidence", "validation", "required_input",
    "candidate_commit"
  ]
}
JSON

git -C "$REPO" worktree add -b "$BRANCH" "$WORKTREE" "$SEED_REF"
[[ -f "$WORKTREE/$METHOD_NOTE_REL" ]] ||
  die "accepted Phase-4 operating-method note is absent from the seed commit"
[[ -f "$WORKTREE/tools/phase4_method_metrics.py" ]] ||
  die "v2 method-metrics validator is absent from the seed commit"
if [[ "$SELECTION_POLICY" == "movie-ready" ]]; then
  [[ -f "$WORKTREE/tools/phase4_movie_priority.py" ]] ||
    die "movie-ready queue generator is absent from the seed commit"
  [[ -f "$WORKTREE/analysis/phase4_movie_priority_queue.json" ]] ||
    die "movie-ready queue artifact is absent from the seed commit"
fi
python3 "$WORKTREE/tools/provision_clean_checkout_inputs.py" \
  --operator-root "$REPO" ||
  die "central clean-checkout provisioning failed; trial not started"
python3 "$WORKTREE/tools/provision_clean_checkout_inputs.py" \
  --operator-root "$REPO" --verify-only ||
  die "central clean-checkout fixture verification failed; trial not started"
cp -- "$WORKTREE/$METHOD_NOTE_REL" "$RUN_DIR/operating-method.md"
sha256sum "$RUN_DIR/operating-method.md" >"$RUN_DIR/operating-method.sha256"
mkdir -p "$RUN_DIR/method-metrics"

cat >"$RUN_DIR/run.json" <<JSON
{
  "name": "Flik's Phase-4 Method Ratchet",
  "run_id": "$RUN_ID",
  "phase": $PHASE,
  "selection_policy": "$SELECTION_POLICY",
  "operator_repo": "$REPO",
  "worktree": "$WORKTREE",
  "branch": "$BRANCH",
  "seed_ref": "$SEED_REF",
  "seed_commit": "$(git -C "$WORKTREE" rev-parse HEAD)",
  "contract_snapshot": "$RUN_DIR/acceptance-contract.md",
  "contract_sha256": "$(sha256sum "$RUN_DIR/acceptance-contract.md" | awk '{print $1}')",
  "operating_method": "$RUN_DIR/operating-method.md",
  "operating_method_sha256": "$(sha256sum "$RUN_DIR/operating-method.md" | awk '{print $1}')",
  "metrics_validator_sha256": "$(sha256sum "$WORKTREE/tools/phase4_method_metrics.py" | awk '{print $1}')",
  "parent_run": "$PARENT_RUN",
  "auto_reseed_depth": $AUTO_RESEED_DEPTH,
  "reseed_signature": "$RESEED_SIGNATURE",
  "reseed_repeat_count": $RESEED_REPEAT_COUNT,
  "max_identical_reseeds": $MAX_IDENTICAL_RESEEDS,
  "continuation_reason": "$CONTINUATION_REASON",
  "previous_movie_ready_packet": "$PREVIOUS_MOVIE_READY_PACKET_SNAPSHOT",
  "previous_movie_ready_progress": "$PREVIOUS_MOVIE_READY_PROGRESS_SNAPSHOT",
  "previous_movie_ready_queue": "$PREVIOUS_MOVIE_READY_QUEUE_SNAPSHOT",
  "previous_movie_ready_debt_before": "$PREVIOUS_MOVIE_READY_DEBT_BEFORE_SNAPSHOT",
  "previous_movie_ready_debt_after": "$PREVIOUS_MOVIE_READY_DEBT_AFTER_SNAPSHOT",
  "codex_fast_mode": $([[ "$FAST_MODE" == "1" ]] && printf true || printf false),
  "codex_service_tier": "$([[ "$FAST_MODE" == "1" ]] && printf fast || printf standard)",
  "started": "$(date --iso-8601=seconds)"
}
JSON

FEEDBACK="$RUN_DIR/feedback.json"
STOP_AFTER_ITERATION="$RUN_DIR/stop-after-iteration"
python3 - "$FEEDBACK" "$INITIAL_CONTEXT_SNAPSHOT" <<'PY'
import json, sys
out = {
    "source": "initial",
    "instruction": (
        "Begin from the acceptance contract and roadmap. Treat the initial review "
        "as a concrete falsification/gap inventory to verify, not as authority and "
        "not as permission to weaken closure criteria."
    ),
    "initial_context": sys.argv[2],
    "gaps": [],
}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
    f.write("\n")
PY

codex_base=(codex exec --ephemeral --color always -s "$SANDBOX")
if ((FAST_MODE)); then
  codex_base+=(-c 'service_tier="fast"' --enable fast_mode)
fi
if [[ -n "$MODEL" ]]; then
  codex_base+=(-m "$MODEL")
fi
CODEX_CAPACITY_RETRIES=3

json_field() {
  local path="$1" field="$2"
  python3 - "$path" "$field" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
value = doc[sys.argv[2]]
if isinstance(value, (dict, list)):
    print(json.dumps(value, ensure_ascii=False))
else:
    print(value)
PY
}

valid_decision() {
  local path="$1"
  python3 - "$path" "$PHASE" <<'PY'
import json, sys
try:
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"invalid JSON decision: {exc}")
required = {
    "phase", "status", "summary", "gaps", "gap_codes",
    "falsifier_results", "verified_live_receipt_sha256s",
    "method_exceptions", "evidence", "validation", "required_input",
    "candidate_commit"
}
if set(doc) != required:
    raise SystemExit(f"decision keys differ: {sorted(set(doc) ^ required)}")
if doc["phase"] != int(sys.argv[2]):
    raise SystemExit("decision phase mismatch")
if doc["status"] not in {"closed", "open_autonomous", "blocked_external"}:
    raise SystemExit("invalid decision status")
for key in ("gaps", "gap_codes", "verified_live_receipt_sha256s",
            "evidence", "validation"):
    if not isinstance(doc[key], list) or not all(isinstance(v, str) for v in doc[key]):
        raise SystemExit(f"{key} must be an array of strings")
for key in ("summary", "required_input", "candidate_commit"):
    if not isinstance(doc[key], str):
        raise SystemExit(f"{key} must be a string")
if not doc["summary"].strip():
    raise SystemExit("summary must be non-empty")
if doc["status"] == "blocked_external" and not doc["required_input"].strip():
    raise SystemExit("blocked_external requires exact required_input")
if doc["status"] == "closed" and (doc["gaps"] or doc["required_input"].strip()):
    raise SystemExit("closed cannot carry gaps or required_input")
if len(doc["gaps"]) != len(doc["gap_codes"]):
    raise SystemExit("gaps and stable gap_codes must have equal length")
if not all(isinstance(v, dict) and set(v) == {"id", "outcome", "evidence"}
           and v["outcome"] in {"survived", "falsified", "not_run"}
           and isinstance(v["id"], str) and v["id"].strip()
           and isinstance(v["evidence"], str) and v["evidence"].strip()
           for v in doc["falsifier_results"]):
    raise SystemExit("invalid falsifier_results")
if not doc["gaps"] and (
        not doc["evidence"] or not doc["validation"] or
        len(doc["falsifier_results"]) < 2 or
        any(v["outcome"] != "survived" for v in doc["falsifier_results"])):
    raise SystemExit(
        "gap-free decision requires evidence, validation, and two survived falsifiers")
if not isinstance(doc["method_exceptions"], list):
    raise SystemExit("method_exceptions must be an array")
PY
}

run_codex() {
  local role="$1" cwd="$2" prompt="$3" decision="$4" log="$5"
  local validation_error="${decision%.json}.validation-error.txt"
  local starting_head starting_status current_head current_status
  local attempt=1 rc=0 delay attempt_log
  starting_head="$(git -C "$cwd" rev-parse HEAD)"
  starting_status="$(git -C "$cwd" status --porcelain=v1 --untracked-files=all)"
  : >"$log"
  printf '\n============================================================\n'
  printf '%s — Phase %s — %s\n' "$SCRIPT_NAME" "$PHASE" "$role"
  printf '============================================================\n'
  cat "$prompt"
  printf '\n-------------------- Codex live output ---------------------\n'
  while true; do
    attempt_log="${log%.log}.attempt-${attempt}.log"
    rm -f -- "$attempt_log" "$decision"
    if ((attempt > 1)); then
      printf '\n---------------- Codex capacity retry %s ----------------\n' \
        "$attempt" | tee -a "$log"
    fi
    set +e
    "${codex_base[@]}" -C "$cwd" \
      --output-schema "$RUN_DIR/decision.schema.json" \
      --output-last-message "$decision" - <"$prompt" 2>&1 |
      tee "$attempt_log" | tee -a "$log"
    rc=${PIPESTATUS[0]}
    set -e
    ((rc == 0)) && break

    current_head="$(git -C "$cwd" rev-parse HEAD)"
    current_status="$(git -C "$cwd" status \
      --porcelain=v1 --untracked-files=all)"
    if ((attempt <= CODEX_CAPACITY_RETRIES)) && \
       grep -Fq "Selected model is at capacity" "$attempt_log" && \
       [[ -z "$starting_status" ]] && \
       [[ "$current_head" == "$starting_head" ]] && \
       [[ "$current_status" == "$starting_status" ]]; then
      delay=$((attempt * 10))
      printf '%s role=%q attempt=%s exit=%s delay_seconds=%s state_unchanged=true\n' \
        "$(date --iso-8601=seconds)" "$role" "$attempt" "$rc" "$delay" \
        >>"$RUN_DIR/codex-capacity-retries.log"
      note "$role hit transient model capacity with unchanged clean state; retrying in ${delay}s"
      attempt=$((attempt + 1))
      sleep "$delay"
      continue
    fi

    printf '%s Codex process exited %s; inspect %s\n' "$role" "$rc" "$log" \
      >"$validation_error"
    note "$role Codex exited $rc"
    return "$rc"
  done
  if ! valid_decision "$decision" 2>"$validation_error"; then
    note "$role returned a decision that failed ratchet validation"
    cat "$validation_error" >&2
    return 65
  fi
  rm -f -- "$validation_error"
}

worktree_clean() {
  [[ -z "$(git -C "$1" status --porcelain=v1 --untracked-files=all)" ]]
}

capture_phase4_debt() {
  local out="$1" selection_packet="${2:-}" continuation="${3:-0}"
  if [[ "$PHASE" != "4" ]]; then
    return 0
  fi
  local tool="$WORKTREE/tools/phase4_closure_debt.py"
  [[ -f "$tool" ]] || {
    note "Phase-4 closure-debt generator is absent"
    return 1
  }
  local args=(python3 "$tool" --snapshot "$out")
  if [[ "$SELECTION_POLICY" == "movie-ready" && -n "$selection_packet" ]]; then
    [[ -f "$selection_packet" ]] || {
      note "movie-ready closure-debt capture packet is absent"
      return 1
    }
    local selected
    selected="$(python3 - "$selection_packet" <<'PY'
import json
import sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
batch = doc["selected_batch"]
print(batch["batch_id"])
for row_id in batch["rows"]:
    print(row_id)
PY
)"
    args+=(--selection-policy movie-ready
      --selected-batch-id "$(sed -n '1p' <<<"$selected")")
    if [[ "$continuation" == "1" ]]; then
      args+=(--selection-continuation)
    fi
    while IFS= read -r row_id; do
      [[ -n "$row_id" ]] && args+=(--selected-row "$row_id")
    done < <(sed -n '2,$p' <<<"$selected")
  fi
  "${args[@]}"
}

prepare_movie_ready_packet() {
  local iteration="$1" out="$2"
  [[ "$SELECTION_POLICY" == "movie-ready" ]] || return 0
  local tool="$WORKTREE/tools/phase4_movie_priority.py"
  [[ -f "$tool" ]] || {
    note "movie-ready queue generator is absent"
    return 1
  }
  python3 "$tool" --check || return $?
  local queue_snapshot="$RUN_DIR/iteration-${iteration}-movie-ready-queue.json"
  cp -- "$WORKTREE/analysis/phase4_movie_priority_queue.json" "$queue_snapshot"
  sha256sum "$queue_snapshot" \
    >"$RUN_DIR/iteration-${iteration}-movie-ready-queue.sha256"
  local args=(python3 "$tool" --packet "$out")
  local previous_packet="" previous_progress="" previous_queue=""
  local previous_debt_before="" previous_debt_after=""
  if ((iteration == 1)); then
    previous_packet="$PREVIOUS_MOVIE_READY_PACKET_SNAPSHOT"
    previous_progress="$PREVIOUS_MOVIE_READY_PROGRESS_SNAPSHOT"
    previous_queue="$PREVIOUS_MOVIE_READY_QUEUE_SNAPSHOT"
    previous_debt_before="$PREVIOUS_MOVIE_READY_DEBT_BEFORE_SNAPSHOT"
    previous_debt_after="$PREVIOUS_MOVIE_READY_DEBT_AFTER_SNAPSHOT"
  else
    previous_packet="$RUN_DIR/iteration-$((iteration - 1))-movie-ready-packet.json"
    previous_progress="$RUN_DIR/iteration-$((iteration - 1))-progress.json"
    previous_queue="$RUN_DIR/iteration-$((iteration - 1))-movie-ready-queue.json"
    previous_debt_before="$RUN_DIR/iteration-$((iteration - 1))-debt-before.json"
    previous_debt_after="$RUN_DIR/iteration-$((iteration - 1))-debt-after.json"
  fi
  if [[ -n "$previous_packet" ]]; then
    local required_snapshot
    for required_snapshot in "$previous_packet" "$previous_progress" \
        "$previous_queue" "$previous_debt_before" "$previous_debt_after"; do
      [[ -f "$required_snapshot" ]] || {
        note "movie-ready continuation is missing a required prior snapshot: $required_snapshot"
        return 1
      }
    done
    args+=(
      --previous-packet "$previous_packet"
      --previous-progress "$previous_progress"
      --previous-queue "$previous_queue"
      --previous-debt-before "$previous_debt_before"
      --previous-debt-after "$previous_debt_after"
    )
  fi
  "${args[@]}" || return $?
  python3 - "$out" "$iteration" <<'PY'
import json
import sys
path, iteration = sys.argv[1:]
doc = json.load(open(path, encoding="utf-8"))
if doc.get("phase") != 4 or doc.get("selection_policy") != "movie-ready":
    raise SystemExit("movie-ready packet phase/policy mismatch")
batch = doc.get("selected_batch") or {}
rows = batch.get("rows") or []
if not batch.get("batch_id") or not 1 <= len(rows) <= 3:
    raise SystemExit("movie-ready packet batch is structurally invalid")
print(
    f"PASS: iteration={iteration} batch={batch['batch_id']} "
    f"rows={','.join(rows)} rotation={doc['rotation']['applied']}")
PY
}

phase4_progress_record() {
  local before="$1" after="$2" iteration="$3" out="$4"
  python3 "$WORKTREE/tools/phase4_scheduler_policy.py" \
    --derive-progress --before "$before" --after "$after" \
    --iteration "$iteration" --out "$out"
}

phase4_stagnation_count() {
  python3 - "$RUN_DIR" <<'PY'
import glob
import json
import pathlib
import sys

run_dir = sys.argv[1]
count = 0
paths = sorted(
    glob.glob(str(pathlib.Path(run_dir) / "iteration-*-progress.json")),
    key=lambda path: int(pathlib.Path(path).name.split("-")[1]),
    reverse=True,
)
for path in paths:
    row = json.loads(pathlib.Path(path).read_text())
    if row.get("row_transitions") or row.get("dimension_transitions"):
        break
    count += 1
print(count)
PY
}

phase4_policy_value() {
  local key="$1"
  python3 - "$WORKTREE/config/phase4_closure_policy.yaml" "$key" <<'PY'
import sys
import yaml
doc = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
print(doc[sys.argv[2]])
PY
}

phase4_live_receipt_count() {
  local receipt_dir="$RUN_DIR/iteration-${1}-receipts"
  python3 - "$receipt_dir" <<'PY'
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
count = 0
if root.is_dir():
    for path in root.glob("*.json"):
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("schema") == \
                    "abl-phase4-live-run-receipt/2":
                count += 1
        except Exception:
            pass
print(count)
PY
}

sha256_path() {
  sha256sum "$1" | awk '{print $1}'
}

append_controller_event() {
  local path="$1" event_type="$2" payload="{}"
  if (($# >= 3)); then
    payload="$3"
  fi
  python3 - "$path" "$event_type" "$payload" <<'PY'
from datetime import datetime, timezone
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
event_type = sys.argv[2]
payload = json.loads(sys.argv[3])
if path.is_file():
    doc = json.loads(path.read_text(encoding="utf-8"))
else:
    doc = {
        "schema": "abl-phase4-controller-events/1",
        "iteration": int(path.stem.split("-")[1]),
        "events": [],
    }
doc["events"].append({
    "sequence": len(doc["events"]),
    "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "type": event_type,
    "payload": payload,
})
path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
PY
}

capture_phase4_escalation_ledger() {
  local out="$1"
  cp -- "$WORKTREE/analysis/phase4_live_escalations.json" "$out"
}

method_report_ref() {
  local scope="$1" path="$2" root="$3"
  python3 - "$scope" "$path" "$root" <<'PY'
import hashlib
import json
import pathlib
import sys
scope, rel, root = sys.argv[1:]
path = pathlib.Path(root) / rel
print(json.dumps({
    "scope": scope,
    "path": pathlib.PurePosixPath(rel).as_posix(),
    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
}, separators=(",", ":")))
PY
}

method_receipt_refs() {
  local receipt_dir="$1" schema="$2"
  python3 - "$receipt_dir" "$schema" "$RUN_DIR" <<'PY'
import hashlib
import json
import pathlib
import sys
directory, schema, run_root = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
refs = []
if directory.is_dir():
    for path in sorted(directory.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if doc.get("schema") != schema:
            continue
        refs.append({
            "scope": "run",
            "path": path.relative_to(run_root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
print(json.dumps(refs, separators=(",", ":")))
PY
}

capture_method_reports() {
  local iteration="$1" candidate="$2" executor_log="$3" verifier_log="${4:-}"
  local report_dir="$RUN_DIR/iteration-${iteration}-reports"
  local verify_dir="$RUN_DIR/report-worktree-iteration-${iteration}"
  [[ ! -e "$report_dir" && ! -e "$verify_dir" ]] ||
    die "refusing to overwrite retained method report/worktree for iteration $iteration"
  mkdir -p "$report_dir"
  git -C "$REPO" worktree add --detach "$verify_dir" "$candidate"
  if [[ -f "$verify_dir/tools/provision_clean_checkout_inputs.py" ]]; then
    python3 "$verify_dir/tools/provision_clean_checkout_inputs.py" \
      --operator-root "$REPO" >"$report_dir/provision.log" 2>&1
  fi
  local args=(
    python3 "$verify_dir/tools/phase4_method_reports.py"
    --out-dir "$report_dir"
    --executor-log "$executor_log"
  )
  if [[ -n "$verifier_log" ]]; then
    args+=(--verifier-log "$verifier_log")
  fi
  local rc=0
  "${args[@]}" >"$report_dir/capture.log" 2>&1 || rc=$?
  git -C "$REPO" worktree remove --force "$verify_dir" || true
  if ((rc != 0)); then
    cat "$report_dir/capture.log" >&2
    return "$rc"
  fi
}

write_method_manifest() {
  local iteration="$1" base_commit="$2" tested_commit="$3"
  local before_debt="$4" after_debt="$5" progress="$6"
  local before_ledger="$7" after_ledger="$8" events="$9"
  local verifier_decision="${10:-}"
  local receipt_dir="$RUN_DIR/iteration-${iteration}-receipts"
  local report_dir="$RUN_DIR/iteration-${iteration}-reports"
  local manifest="$RUN_DIR/method-metrics/iteration-$(printf '%03d' "$iteration").json"
  local selected campaign rows started finished validator_ref
  selected="$(python3 - "$before_debt" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
s=d["scheduler"]["selected_campaigns"][0]
print(s["campaign_id"])
print(json.dumps(s["rows"], separators=(",", ":")))
PY
)"
  campaign="$(sed -n '1p' <<<"$selected")"
  rows="$(sed -n '2p' <<<"$selected")"
  read -r started finished < <(python3 - "$events" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print(d["events"][0]["at"], d["events"][-1]["at"])
PY
)
  validator_ref="$(method_report_ref repo tools/phase4_method_metrics.py "$WORKTREE")"
  local before_ref after_ref progress_ref before_ledger_ref after_ledger_ref events_ref
  before_ref="$(method_report_ref run "${before_debt#"$RUN_DIR"/}" "$RUN_DIR")"
  after_ref="$(method_report_ref run "${after_debt#"$RUN_DIR"/}" "$RUN_DIR")"
  progress_ref="$(method_report_ref run "${progress#"$RUN_DIR"/}" "$RUN_DIR")"
  before_ledger_ref="$(method_report_ref run "${before_ledger#"$RUN_DIR"/}" "$RUN_DIR")"
  after_ledger_ref="$(method_report_ref run "${after_ledger#"$RUN_DIR"/}" "$RUN_DIR")"
  events_ref="$(method_report_ref run "${events#"$RUN_DIR"/}" "$RUN_DIR")"
  local offline_refs live_refs verifier_ref
  offline_refs="$(method_receipt_refs "$receipt_dir" abl-phase4-offline-query/1)"
  live_refs="$(method_receipt_refs "$receipt_dir" abl-phase4-live-run-receipt/2)"
  verifier_ref="null"
  if [[ -n "$verifier_decision" ]]; then
    verifier_ref="$(method_report_ref run "${verifier_decision#"$RUN_DIR"/}" "$RUN_DIR")"
  fi
  python3 - "$manifest" "$iteration" "$campaign" "$rows" \
    "$base_commit" "$tested_commit" "$started" "$finished" \
    "$validator_ref" "$before_ref" "$after_ref" "$progress_ref" \
    "$offline_refs" "$live_refs" "$before_ledger_ref" "$after_ledger_ref" \
    "$verifier_ref" "$events_ref" \
    "$(method_report_ref run "iteration-${iteration}-reports/command-log.json" "$RUN_DIR")" \
    "$(method_report_ref run "iteration-${iteration}-reports/validation-report.json" "$RUN_DIR")" \
    "$(method_report_ref run "iteration-${iteration}-reports/knowledge-report.json" "$RUN_DIR")" \
    "$(method_report_ref run "iteration-${iteration}-reports/vault-report.json" "$RUN_DIR")" \
    "$(method_report_ref run "iteration-${iteration}-reports/clean-checkout-report.json" "$RUN_DIR")" <<'PY'
import json
import pathlib
import sys

(path, iteration, campaign, rows, base, tested, started, finished,
 validator, debt_before, debt_after, progress, offline, live,
 ledger_before, ledger_after, verifier, events, command, validation,
 knowledge, vault, clean) = sys.argv[1:]
doc = {
    "schema": "abl-phase4-method-metrics/2",
    "iteration": int(iteration),
    "campaign_id": campaign,
    "row_ids": json.loads(rows),
    "base_commit": base,
    "tested_commit": tested,
    "started_at": started,
    "finished_at": finished,
    "validator": json.loads(validator),
    "evidence": {
        "debt_before": json.loads(debt_before),
        "debt_after": json.loads(debt_after),
        "progress_receipt": json.loads(progress),
        "offline_query_receipts": json.loads(offline),
        "live_run_receipts": json.loads(live),
        "escalation_ledger_before": json.loads(ledger_before),
        "escalation_ledger_after": json.loads(ledger_after),
        "verifier_decision": json.loads(verifier),
        "controller_events": json.loads(events),
        "command_log": json.loads(command),
        "validation_report": json.loads(validation),
        "knowledge_report": json.loads(knowledge),
        "vault_report": json.loads(vault),
        "clean_checkout_report": json.loads(clean),
    },
}
pathlib.Path(path).write_text(json.dumps(doc, indent=2) + "\n")
PY
}

phase4_seed_preflight() {
  local out="$1" root="${2:-$WORKTREE}"
  (
    cd "$root" || exit $?
    python3 tools/provision_clean_checkout_inputs.py \
      --operator-root "$REPO" --verify-only || exit $?
    python3 tools/phase4_method_metrics.py --self-check || exit $?
    python3 tools/phase4_method_legacy_live_index.py --check || exit $?
    python3 tools/phase4_movie_priority.py --check || exit $?
    python3 tools/build_identity.py --verify || exit $?
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. \
      python3 -m pytest -q -p no:cacheprovider \
        tests/test_phase4_gate.py \
        tests/test_phase4_method_metrics.py \
        tests/test_flik_phase4_method_ratchet.py \
        tests/test_phase4_offline_queue.py \
        tests/test_phase4_movie_priority.py || exit $?
    PYTHONPATH=tools python3 - <<'PY'
import phase4_gate

gate = phase4_gate.build()
phase3 = gate["phase3_recomputed"]
inventory = phase3["inventory"]
if not phase3["met"]:
    raise SystemExit("Phase-3 prerequisite does not recompute MET")
if inventory["retained_artifact_fresh"] is not True:
    raise SystemExit("Phase-3 retained live evidence is stale")
if inventory["summary"]["tracked_input_mutations"]:
    raise SystemExit("Phase-3 prerequisite was computed from tracked mutations")
if not all(gate["freshness"].values()):
    raise SystemExit("Phase-4 retained prerequisite summaries are stale")
PY
    rc=$?
    ((rc == 0)) || exit "$rc"
    python3 tools/validate_vault.py --check || exit $?
    git diff --check || exit $?
    test -z "$(git status --porcelain=v1 --untracked-files=all)"
  ) >"$out" 2>&1
}

make_seed_repair_prompt() {
  local attempt="$1" preflight_log="$2" out="$3"
  cat >"$out" <<EOF
You are the pre-trial seed-repair executor for ABL Phase 4, attempt $attempt.
Follow $WORKTREE/AGENTS.md and the accepted operating method at
$WORKTREE/$METHOD_NOTE_REL. Work only in $WORKTREE. Preserve operator WIP; the
operator checkout at $REPO is fixture intake only. The pristine retail image is the
sole behavioral authority; ALLMODS and derivatives are comparison evidence only.

The six-tested-iteration Phase-4 methodology trial has NOT started. Repair only the
load-bearing seed prerequisites reported by:

$preflight_log

Current output:
~~~text
$(tail -160 "$preflight_log")
~~~

Do not start or advance a Phase-4 subsystem campaign and do not manufacture a green
summary. Diagnose the exact stale generated/live evidence. Regenerate authoritative
machine artifacts first, strengthen or preserve guards, then reconcile Canon,
Experiments, roadmap handoffs, and generated summaries. If Phase-3 retained live
artifacts no longer reproduce because the DuckStation fork/source/binary changed,
use the duckstation-external-debugger skill and replay only the stale artifacts on
the current hash-pinned fork. Use fresh absolute config directories, dedicated
ports/tokens, pristine mounted-media and save-state verification, re-arm after every
load, and owned-PID cleanup. Do not claim an unavailable historic binary is
preserved. A hash-only stale-artifact edit is not a repair.

The repaired commit must pass, from a centrally provisioned clean checkout:
- tools/phase4_method_metrics.py --self-check;
- tools/phase4_method_legacy_live_index.py --check;
- tests/test_phase4_gate.py, including recomputed Phase-3 MET and retained evidence;
- pristine build identity, vault validation, relevant Phase-3 guards, and a clean
  worktree.

Commit every scoped non-copyrighted repair. Do not commit media, saves, movies,
captures, tokens, runtime binaries, or generated discs. Return the required JSON
decision. Phase 4 itself remains open, so use status=open_autonomous. Use an empty
gaps array only if the seed-repair preflight is genuinely clean; in that case retain
at least two concrete survived falsifiers, evidence, and exact validation commands.
candidate_commit must equal actual HEAD.
EOF
}

make_seed_repair_verifier_prompt() {
  local attempt="$1" candidate="$2" executor_decision="$3" preflight_log="$4"
  local verify_root="$5" fixed_validation="$6" out="$7"
  local inventory_ref gate3_ref gate4_ref validation_ref
  inventory_ref="repo:analysis/phase3_evidence_inventory.json@$(sha256_path "$verify_root/analysis/phase3_evidence_inventory.json")"
  gate3_ref="repo:analysis/phase3_gate_audit.json@$(sha256_path "$verify_root/analysis/phase3_gate_audit.json")"
  gate4_ref="repo:analysis/phase4_gate.json@$(sha256_path "$verify_root/analysis/phase4_gate.json")"
  validation_ref="run:$(realpath --relative-to="$RUN_DIR" "$fixed_validation")@$(sha256_path "$fixed_validation")"
  cat >"$out" <<EOF
You are the fresh pre-trial seed-repair verifier for ABL Phase 4, attempt $attempt.
Audit exact candidate $candidate in detached checkout $verify_root. Follow AGENTS.md and the accepted
Phase-4 operating method. Do not edit or commit and do not launch DuckStation.
The executor claim at $executor_decision is evidence to challenge, never authority.

Independently rerun the seed preflight represented by $preflight_log, relevant
Phase-3 live-evidence/provenance guards, Phase-4 gate tests, pristine identity,
fixture provisioning verification, vault validation, and clean status. Inspect the
low-level retained artifacts behind any regenerated summary. Reject:
- a stale or unavailable DuckStation source/binary/runtime presented as reproducible;
- rewritten hashes without replayed evidence;
- weakened/removed guards;
- Phase-3 or Phase-4 gate flags trusted instead of recomputation;
- non-pristine behavioral authority;
- missing fixtures, skips, dirty source, or uncommitted dependencies;
- any Phase-4 campaign progress mixed into this prerequisite repair.

Falsify at least two decisive guards in disposable copies and require them to turn
red. For the gap-free decision, evidence must be exactly these three closed,
semantically checked references:
- $inventory_ref
- $gate3_ref
- $gate4_ref

Validation must be exactly this controller-captured fixed-check report:
- $validation_ref

Create and cite two abl-phase4-verifier-falsifier/1 receipts under $RUN_DIR. Their
IDs and commands must be exactly:
- live-helper-drift:
  $(command -v python3) -B tools/phase4_seed_falsifiers.py --kind live-helper-drift
- retained-artifact-drift:
  $(command -v python3) -B tools/phase4_seed_falsifiers.py --kind retained-artifact-drift
Run them from $verify_root and retain their exact exit code, stdout, and SHA-256.
Content-free scripts, python -c, prose-only evidence, and alternate commands are
rejected mechanically.

Return the required JSON decision with candidate_commit=$candidate. Phase 4
itself is still open, so status must be open_autonomous. If and only if the seed is
safe for the measured trial, return gaps=[] and required_input="" with concrete
evidence, exact validations, and at least two survived falsifiers. Otherwise name
every autonomous gap with a stable gap code; use blocked_external only for genuinely
operator-only input.
EOF
}

repair_seed_before_trial() {
  local preflight="$RUN_DIR/seed-preflight.log"
  local seed_base seed_debt_before
  if phase4_seed_preflight "$preflight"; then
    note "seed prerequisites pass; measured trial may initialize"
    return 0
  fi
  note "seed prerequisites are stale; entering pre-trial repair loop"
  seed_base="$(git -C "$WORKTREE" rev-parse HEAD)"
  seed_debt_before="$RUN_DIR/seed-repair-debt-before.json"
  capture_phase4_debt "$seed_debt_before" ||
    die "cannot capture Phase-4 debt before prerequisite repair"
  local attempt prompt decision log actual verifier_prompt verifier_decision verifier_log
  local verify_dir verify_head verify_status tree_status seed_debt_after seed_scope
  local seed_verifier_validation fixed_seed_validation
  for attempt in 1 2 3; do
    prompt="$RUN_DIR/seed-repair-${attempt}-executor.prompt.md"
    decision="$RUN_DIR/seed-repair-${attempt}-executor.decision.json"
    log="$RUN_DIR/seed-repair-${attempt}-executor.log"
    make_seed_repair_prompt "$attempt" "$preflight" "$prompt"
    if ! run_codex "SEED REPAIR EXECUTOR $attempt" "$WORKTREE" "$prompt" \
        "$decision" "$log"; then
      note "seed-repair executor $attempt failed structurally"
      continue
    fi
    actual="$(git -C "$WORKTREE" rev-parse HEAD)"
    if [[ "$(json_field "$decision" candidate_commit)" != "$actual" ]] || \
       ! worktree_clean "$WORKTREE"; then
      note "seed-repair executor $attempt left an untrustworthy terminal state"
      continue
    fi
    seed_debt_after="$RUN_DIR/seed-repair-${attempt}-debt-after.json"
    seed_scope="$RUN_DIR/seed-repair-${attempt}-scope.json"
    capture_phase4_debt "$seed_debt_after" ||
      die "cannot recompute Phase-4 debt after seed-repair attempt $attempt"
    if ! python3 "$WORKTREE/tools/phase4_seed_repair_scope.py" \
        --repo "$WORKTREE" --base "$seed_base" --candidate "$actual" \
        --debt-before "$seed_debt_before" --debt-after "$seed_debt_after" \
        --out "$seed_scope"; then
      die "seed-repair attempt $attempt changed Phase-4 campaign scope; trial not started"
    fi
    if ! phase4_seed_preflight "$preflight"; then
      write_feedback "seed_repair_executor_$attempt" "$decision"
      note "seed-repair attempt $attempt did not close the mechanical preflight"
      continue
    fi
    verifier_prompt="$RUN_DIR/seed-repair-${attempt}-verifier.prompt.md"
    verifier_decision="$RUN_DIR/seed-repair-${attempt}-verifier.decision.json"
    verifier_log="$RUN_DIR/seed-repair-${attempt}-verifier.log"
    verify_dir="$RUN_DIR/seed-repair-${attempt}-verifier-worktree"
    git -C "$REPO" worktree add --detach "$verify_dir" "$actual"
    if ! python3 "$verify_dir/tools/provision_clean_checkout_inputs.py" \
        --operator-root "$REPO" \
        >"$RUN_DIR/seed-repair-${attempt}-verifier-provision.log" 2>&1; then
      git -C "$REPO" worktree remove --force "$verify_dir" || true
      note "detached verifier checkout could not be provisioned for attempt $attempt"
      continue
    fi
    if ! phase4_seed_preflight \
        "$RUN_DIR/seed-repair-${attempt}-verifier-preflight.log" "$verify_dir"; then
      git -C "$REPO" worktree remove --force "$verify_dir" || true
      note "detached verifier checkout failed seed preflight for attempt $attempt"
      continue
    fi
    fixed_seed_validation="$RUN_DIR/seed-repair-${attempt}-fixed-validation.json"
    if ! PYTHONPATH="$verify_dir/tools" \
        python3 "$verify_dir/tools/phase4_seed_validation.py" \
          --tested-root "$verify_dir" --candidate "$actual" \
          --out "$fixed_seed_validation" \
          >"$RUN_DIR/seed-repair-${attempt}-fixed-validation.log" 2>&1; then
      git -C "$REPO" worktree remove --force "$verify_dir" || true
      note "detached fixed seed validation failed for attempt $attempt"
      continue
    fi
    make_seed_repair_verifier_prompt "$attempt" "$actual" "$decision" \
      "$preflight" "$verify_dir" "$fixed_seed_validation" "$verifier_prompt"
    if ! run_codex "SEED REPAIR VERIFIER $attempt" "$verify_dir" "$verifier_prompt" \
        "$verifier_decision" "$verifier_log"; then
      git -C "$REPO" worktree remove --force "$verify_dir" || true
      note "seed-repair verifier $attempt failed structurally"
      continue
    fi
    seed_verifier_validation="$RUN_DIR/seed-repair-${attempt}-verifier-validation.log"
    if ! PYTHONPATH="$verify_dir/tools" \
        python3 "$verify_dir/tools/phase4_seed_verifier.py" \
          --decision "$verifier_decision" --candidate "$actual" \
          --run-dir "$RUN_DIR" --tested-root "$verify_dir" \
          >"$seed_verifier_validation" 2>&1; then
      verify_status="<verifier evidence invalid>"
    else
      verify_status=""
    fi
    verify_head="$(git -C "$verify_dir" rev-parse HEAD)"
    tree_status="$(git -C "$verify_dir" status --porcelain=v1 --untracked-files=all)"
    verify_status="${verify_status}${tree_status:+$'\n'$tree_status}"
    if ! phase4_seed_preflight \
        "$RUN_DIR/seed-repair-${attempt}-verifier-postflight.log" "$verify_dir"; then
      verify_status="<postflight failed>${verify_status:+$'\n'$verify_status}"
    fi
    git -C "$REPO" worktree remove --force "$verify_dir" || true
    if [[ "$(json_field "$verifier_decision" candidate_commit)" != "$actual" ]] || \
       [[ "$verify_head" != "$actual" ]] || \
       [[ -n "$verify_status" ]] || \
       [[ "$(json_field "$verifier_decision" status)" != "open_autonomous" ]] || \
       [[ "$(json_field "$verifier_decision" gaps)" != "[]" ]] || \
       [[ -n "$(json_field "$verifier_decision" required_input)" ]] || \
       ! phase4_seed_preflight "$preflight"; then
      write_feedback "seed_repair_verifier_$attempt" "$verifier_decision"
      note "fresh verifier rejected seed-repair attempt $attempt"
      continue
    fi
    note "seed repair accepted by mechanical preflight and a fresh verifier"
    return 0
  done
  die "seed prerequisites remain open after three pre-trial repair attempts; methodology trial not started"
}

initialize_method_trial() {
  local selection_packet="${1:-}"
  local debt="$RUN_DIR/method-metrics/trial-debt-before.json"
  local legacy="analysis/phase4_method_legacy_live_index.json"
  capture_phase4_debt "$debt" "$selection_packet"
  python3 - "$RUN_DIR/method-metrics/trial-root.json" \
    "$(git -C "$WORKTREE" rev-parse HEAD)" "$(sha256_path "$debt")" \
    "$(sha256_path "$WORKTREE/tools/phase4_method_metrics.py")" \
    "$(sha256_path "$WORKTREE/tools/phase4_method_reports.py")" \
    "$(method_report_ref repo "$legacy" "$WORKTREE")" <<'PY'
from datetime import datetime, timezone
import json
import pathlib
import sys
path, base, debt, validator, reporter, legacy = sys.argv[1:]
doc = {
    "schema": "abl-phase4-method-trial-root/1",
    "base_commit": base,
    "debt_before_sha256": debt,
    "validator_sha256": validator,
    "reporter_sha256": reporter,
    "legacy_index": json.loads(legacy),
    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}
pathlib.Path(path).write_text(json.dumps(doc, indent=2) + "\n")
PY
}

write_terminal_failure_manifest() {
  local iteration="$1" base_commit="$2" code="$3" events="$4"
  local actual_commit status_file manifest
  actual_commit="$(git -C "$WORKTREE" rev-parse HEAD)"
  status_file="$RUN_DIR/iteration-${iteration}-terminal-status.txt"
  manifest="$RUN_DIR/method-metrics/terminal-failure-$(printf '%03d' "$iteration").json"
  git -C "$WORKTREE" status --porcelain=v1 --untracked-files=all >"$status_file"
  python3 - "$manifest" "$iteration" "$base_commit" "$actual_commit" "$code" \
    "$status_file" \
    "$(method_report_ref run "${events#"$RUN_DIR"/}" "$RUN_DIR")" <<'PY'
import json
import pathlib
import sys

path, iteration, base, actual, code, status_path, events = sys.argv[1:]
status = pathlib.Path(status_path).read_text(encoding="utf-8").splitlines()
events_ref = json.loads(events)
run_root = pathlib.Path(path).parents[1]
events_doc = json.loads(
    (run_root / events_ref["path"]).read_text(encoding="utf-8"))
doc = {
    "schema": "abl-phase4-method-terminal-failure/1",
    "iteration": int(iteration),
    "base_commit": base,
    "actual_commit": actual,
    "code": code,
    "status": status,
    "controller_events": events_ref,
    "created_at": events_doc["events"][-1]["at"],
}
pathlib.Path(path).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
PY
  python3 "$WORKTREE/tools/phase4_method_metrics.py" \
    --run-dir "$RUN_DIR" --summary \
    >"$RUN_DIR/method-metrics/terminal-failure-summary.json"
}

finalize_method_iteration() {
  local iteration="$1" base_commit="$2" tested_commit="$3"
  local before_debt="$4" after_debt="$5" progress="$6"
  local before_ledger="$7" after_ledger="$8" events="$9"
  local executor_log="${10}" verifier_decision="${11:-}" verifier_log="${12:-}"
  append_controller_event "$events" iteration_reports_started \
    "{\"tested_commit\":\"$tested_commit\"}"
  if ! capture_method_reports "$iteration" "$tested_commit" "$executor_log" \
      "$verifier_log"; then
    append_controller_event "$events" infrastructure_failure \
      '{"code":"METHOD_REPORT_CAPTURE_FAILED","cleanup":["report worktree removal attempted","candidate retained for automatic reseed"]}'
    cat >"$RUN_DIR/METHOD_METRICS_FAILURE.txt" <<EOF
Phase-4 fixed report capture failed in iteration $iteration.
The caller must automatically reseed from the clean committed candidate. Inspect:
  $RUN_DIR/iteration-${iteration}-reports/capture.log
EOF
    return 1
  fi
  append_controller_event "$events" iteration_completed \
    "{\"tested_commit\":\"$tested_commit\"}"
  write_method_manifest "$iteration" "$base_commit" "$tested_commit" \
    "$before_debt" "$after_debt" "$progress" "$before_ledger" \
    "$after_ledger" "$events" "$verifier_decision"
  if ! python3 "$WORKTREE/tools/phase4_method_metrics.py" \
      --run-dir "$RUN_DIR" --check >"$RUN_DIR/method-metrics/latest-check.log" 2>&1; then
    cat >"$RUN_DIR/METHOD_METRICS_FAILURE.txt" <<EOF
Phase-4 v2 evidence validation failed in iteration $iteration.
The caller must automatically reseed from the clean committed candidate. Inspect:
  $RUN_DIR/method-metrics/latest-check.log
EOF
    cat "$RUN_DIR/method-metrics/latest-check.log" >&2
    return 1
  fi
  python3 "$WORKTREE/tools/phase4_method_metrics.py" \
    --run-dir "$RUN_DIR" --summary \
    >"$RUN_DIR/method-metrics/latest-summary.json"
  python3 - "$RUN_DIR/method-metrics/latest-summary.json" \
    "$before_debt" "$after_debt" "$RUN_DIR/METHOD_REASSESSMENT_REQUIRED.txt" \
    "$SELECTION_POLICY" <<'PY'
import json
import pathlib
import sys
summary_path, before_path, after_path, out_path = map(
    pathlib.Path, sys.argv[1:5])
selection_policy = sys.argv[5]
summary = json.loads(summary_path.read_text(encoding="utf-8"))
before = json.loads(before_path.read_text(encoding="utf-8"))
after = json.loads(after_path.read_text(encoding="utf-8"))
before_campaign = before["scheduler"]["selected_campaigns"][0]["campaign_id"]
after_selected = after["scheduler"]["selected_campaigns"]
after_campaign = after_selected[0]["campaign_id"] if after_selected else None
reasons = []
if summary["tested_iterations"] == 6:
    reasons.append("mandatory six-tested-iteration reassessment")
if selection_policy != "movie-ready" and \
        summary["consecutive_no_reduction_iterations"] >= 2:
    reasons.append("two consecutive no-reduction tested iterations")
if after_campaign != before_campaign:
    reasons.append(
        f"campaign boundary: {before_campaign} -> {after_campaign or 'none'}")
if reasons:
    out = {
        "schema": "abl-phase4-method-reassessment/1",
        "reasons": reasons,
        "summary": summary,
    }
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
PY
  return 0
}

finalize_infrastructure_iteration() {
  local iteration="$1" base_commit="$2" before_debt="$3"
  local before_ledger="$4" events="$5" executor_log="$6" code="$7"
  local actual_commit after_debt progress after_ledger
  actual_commit="$(git -C "$WORKTREE" rev-parse HEAD)"
  if [[ "$actual_commit" != "$base_commit" ]] || ! worktree_clean "$WORKTREE"; then
    cat >"$RUN_DIR/UNBANKED_TERMINAL_REQUIRES_RECOVERY.txt" <<EOF
Iteration $iteration hit $code after the implementation checkout changed.
The controller stopped before another iteration; it did not classify dirty or
unverified semantic state as infrastructure evidence.
Base: $base_commit
Actual: $actual_commit
Status:
$(git -C "$WORKTREE" status --short)
EOF
    return 1
  fi
  after_debt="$RUN_DIR/iteration-${iteration}-debt-after.json"
  progress="$RUN_DIR/iteration-${iteration}-progress.json"
  after_ledger="$RUN_DIR/iteration-${iteration}-escalations-after.json"
  cp -- "$before_debt" "$after_debt"
  cp -- "$before_ledger" "$after_ledger"
  phase4_progress_record "$before_debt" "$after_debt" "$iteration" "$progress"
  append_controller_event "$events" iteration_reports_started \
    "{\"tested_commit\":\"$base_commit\"}"
  if ! capture_method_reports "$iteration" "$base_commit" "$executor_log" ""; then
    append_controller_event "$events" infrastructure_failure \
      '{"code":"INFRASTRUCTURE_REPORT_CAPTURE_FAILED","cleanup":["report worktree removal attempted","no following iteration started"]}'
    write_terminal_failure_manifest "$iteration" "$base_commit" \
      "INFRASTRUCTURE_REPORT_CAPTURE_FAILED" "$events" || true
    cat >"$RUN_DIR/METHOD_METRICS_FAILURE.txt" <<EOF
Infrastructure iteration $iteration could not capture its fixed reports.
No next iteration was started.
EOF
    return 1
  fi
  append_controller_event "$events" infrastructure_failure \
    "{\"code\":\"$code\",\"cleanup\":[\"owned implementation worktree confirmed unchanged\",\"report worktree removed\"]}"
  write_method_manifest "$iteration" "$base_commit" "$base_commit" \
    "$before_debt" "$after_debt" "$progress" "$before_ledger" \
    "$after_ledger" "$events" ""
  python3 "$WORKTREE/tools/phase4_method_metrics.py" \
    --run-dir "$RUN_DIR" --check \
    >"$RUN_DIR/method-metrics/latest-check.log" 2>&1
}

write_phase4_stagnation_feedback() {
  local decision="$1" progress="$2" count="$3" candidate="$4"
  python3 - "$decision" "$progress" "$count" "$candidate" "$FEEDBACK" <<'PY'
import json
import pathlib
import sys

decision_path, progress_path, count, candidate, out_path = sys.argv[1:]
decision = json.loads(pathlib.Path(decision_path).read_text(encoding="utf-8"))
progress = json.loads(pathlib.Path(progress_path).read_text(encoding="utf-8"))
target = progress.get("campaign_id") or "selected campaign"
lane = "current"
gap = (
    f"Closure debt did not decrease for {target} in {count} consecutive iterations. "
    f"Do not add another {lane}-lane summary. Re-open the low-level evidence, identify "
    "the first unmet nine-dimension predicate, and change lane or experiment design; "
    "if that is impossible, record the exact external blocker."
)
gaps = [gap]
gaps.extend(item for item in decision.get("gaps", []) if item != gap)
out = {
    "source": "phase4_stagnation_guard",
    "status": "open_autonomous",
    "summary": (
        f"The {target} campaign is preserved at committed HEAD, but the machine debt "
        "ledger shows no row or dimension promotion; the next iteration must switch method."
    ),
    "gaps": gaps,
    "required_input": "",
    "evidence": list(decision.get("evidence", [])) + [progress_path],
    "validation": list(decision.get("validation", [])) + [
        f"phase4 stagnation guard: {count} consecutive no-debt-reduction iterations"
    ],
    "candidate_commit": candidate,
}
pathlib.Path(out_path).write_text(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

automatic_reseed() {
  local iteration="$1" candidate="$2" code="$3" details="${4:-}"
  local next_depth=$((AUTO_RESEED_DEPTH + 1))
  local guard="$RUN_DIR/AUTOMATIC_RESEED_GUARD.json"
  local decision="$RUN_DIR/iteration-${iteration}-executor.decision.json"
  local debt="$RUN_DIR/iteration-${iteration}-debt-before.json"
  local guard_rc=0
  local guard_args=(
    --reason "$code"
    --previous-signature "$RESEED_SIGNATURE"
    --previous-repeat-count "$RESEED_REPEAT_COUNT"
    --max-identical-reseeds "$MAX_IDENTICAL_RESEEDS"
    --out "$guard"
  )
  [[ -f "$decision" ]] && guard_args+=(--decision "$decision")
  [[ -f "$debt" ]] && guard_args+=(--debt "$debt")
  [[ -n "$details" && -f "$details" ]] && guard_args+=(--details "$details")
  python3 "$WORKTREE/tools/ratchet_reseed_guard.py" "${guard_args[@]}" ||
    guard_rc=$?
  [[ -f "$guard" ]] ||
    die "progress-sensitive reseed guard failed without a report"
  local next_signature next_repeat
  next_signature="$(json_field "$guard" semantic_signature)"
  next_repeat="$(json_field "$guard" repeat_count)"
  if ((guard_rc == 2)); then
    cat >"$RUN_DIR/AUTO_RESEED_CIRCUIT_OPEN.txt" <<EOF
Automatic Phase-4 trial reseeding repeated the same semantic/debt signature.
Run: $RUN_ID
Candidate: $candidate
Reason: $code
Lineage depth: $AUTO_RESEED_DEPTH
Repeated signature: $next_signature
Repeat count: $next_repeat/$MAX_IDENTICAL_RESEEDS
Details: ${details:-<none>}
No closure or blocker claim was inferred.
EOF
    die "automatic trial-reseed circuit opened after $next_repeat identical no-progress signatures"
  elif ((guard_rc != 0)); then
    die "progress-sensitive reseed guard failed with exit $guard_rc"
  fi

  local record="$RUN_DIR/AUTOMATIC_RESEED.json"
  python3 - "$record" "$RUN_ID" "$iteration" "$candidate" "$code" \
    "$details" "$AUTO_RESEED_DEPTH" "$next_depth" "$next_signature" \
    "$next_repeat" "$MAX_IDENTICAL_RESEEDS" <<'PY'
from datetime import datetime, timezone
import json
import pathlib
import sys

path, run_id, iteration, candidate, code, details, old_depth, new_depth, \
    signature, repeat_count, max_identical = sys.argv[1:]
doc = {
    "schema": "abl-phase4-automatic-reseed/2",
    "run_id": run_id,
    "iteration": int(iteration),
    "candidate_commit": candidate,
    "reason": code,
    "details": details or None,
    "previous_depth": int(old_depth),
    "next_depth": int(new_depth),
    "semantic_signature": signature,
    "identical_repeat_count": int(repeat_count),
    "max_identical_reseeds": int(max_identical),
    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "semantic_claim_admitted": False,
}
pathlib.Path(path).write_text(
    json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

  local candidate_script="$WORKTREE/tools/flik_phase4_method_ratchet.sh"
  local candidate_contract="$WORKTREE/engineering-specs/phase${PHASE}-closure.md"
  [[ -f "$candidate_script" ]] ||
    die "candidate lacks its ratchet controller: $candidate_script"
  [[ -f "$candidate_contract" ]] || candidate_contract="$CONTRACT"
  bash -n "$candidate_script" ||
    die "candidate ratchet syntax is invalid; refusing automatic reseed"

  local args=(
    --internal-run
    --phase "$PHASE"
    --selection-policy "$SELECTION_POLICY"
    --contract "$candidate_contract"
    --seed-ref "$candidate"
    --repo "$REPO"
    --max-iterations "$MAX_ITERATIONS"
    --run-root "$RUN_ROOT"
    --sandbox "$SANDBOX"
    --auto-reseed-depth "$next_depth"
    --reseed-signature "$next_signature"
    --reseed-repeat-count "$next_repeat"
    --max-identical-reseeds "$MAX_IDENTICAL_RESEEDS"
    --parent-run "$RUN_ID"
    --continuation-reason "$code"
  )
  if [[ -n "$MODEL" ]]; then
    args+=(--model "$MODEL")
  fi
  if ((FAST_MODE)); then
    args+=(--fast)
  fi
  if [[ -n "$INITIAL_CONTEXT_SNAPSHOT" ]]; then
    args+=(--initial-context "$INITIAL_CONTEXT_SNAPSHOT")
  fi
  if [[ "$SELECTION_POLICY" == "movie-ready" ]]; then
    local packet="$RUN_DIR/iteration-${iteration}-movie-ready-packet.json"
    local progress="$RUN_DIR/iteration-${iteration}-progress.json"
    local queue="$RUN_DIR/iteration-${iteration}-movie-ready-queue.json"
    local debt_before="$RUN_DIR/iteration-${iteration}-debt-before.json"
    local debt_after="$RUN_DIR/iteration-${iteration}-debt-after.json"
    local required_snapshot
    for required_snapshot in "$packet" "$progress" "$queue" \
        "$debt_before" "$debt_after"; do
      [[ -f "$required_snapshot" ]] ||
        die "movie-ready automatic reseed requires the complete five-snapshot continuation set: $required_snapshot"
    done
    args+=(
      --previous-movie-ready-packet "$packet"
      --previous-movie-ready-progress "$progress"
      --previous-movie-ready-queue "$queue"
      --previous-movie-ready-debt-before "$debt_before"
      --previous-movie-ready-debt-after "$debt_after"
    )
  fi
  note "automatically chaining a fresh trial from $candidate"
  note "reseed reason: $code (lineage depth $next_depth; identical signature $next_repeat/$MAX_IDENTICAL_RESEEDS)"
  note "lineage record: $record"
  exec "$candidate_script" "${args[@]}"
  die "automatic reseed exec failed"
}

stop_requested_at_boundary() {
  local next_iteration="$1"
  [[ -e "$STOP_AFTER_ITERATION" ]] || return 1
  local stopped_head request_text
  stopped_head="$(git -C "$WORKTREE" rev-parse HEAD)"
  request_text="$(head -c 4096 "$STOP_AFTER_ITERATION" 2>/dev/null || true)"
  cat >"$RUN_DIR/STOPPED_AFTER_ITERATION.txt" <<EOF
$SCRIPT_NAME stopped at a safe iteration boundary.
Next executor suppressed: $next_iteration
Branch: $BRANCH
Worktree: $WORKTREE
Candidate HEAD: $stopped_head
Selection policy: $SELECTION_POLICY
Last feedback: $FEEDBACK
Stop request: ${request_text:-<empty sentinel>}
No closure claim was made by this boundary stop.
EOF
  note "boundary-stop sentinel found; executor $next_iteration will not start"
  note "resume with --selection-policy $SELECTION_POLICY from candidate $stopped_head"
  return 0
}

make_executor_prompt() {
  local iteration="$1" out="$2" selection_packet="${3:-}"
  local initial_context_line=""
  local selection_context="- selection policy: $SELECTION_POLICY (the existing closure-debt scheduler remains the default)"
  if [[ -n "$INITIAL_CONTEXT_SNAPSHOT" ]]; then
    initial_context_line="- $INITIAL_CONTEXT_SNAPSHOT (persistent run context; re-read it and verify every claim this iteration)"
  fi
  if [[ -n "$selection_packet" ]]; then
    selection_context="$(cat <<EOF
- selection policy: movie-ready
- authoritative generated work packet: $selection_packet
  SHA-256: $(sha256_path "$selection_packet")
  The packet names the selected row(s), exact movie/start-state hashes,
  capsule/index availability, every score component/rationale, rotation state,
  and the previous attempted packet:
~~~json
$(cat "$selection_packet")
~~~
EOF
)"
  fi
  cat >"$out" <<EOF
You are the implementation owner for Phase $PHASE in Flik's Phase-4 Method Ratchet,
iteration $iteration. Work autonomously in this isolated Git worktree.

Read completely before acting:
- $WORKTREE/AGENTS.md
- $RUN_DIR/acceptance-contract.md (sha256 recorded beside it)
- $RUN_DIR/operating-method.md (accepted binding operating method; sha256
  recorded beside it)
- the roadmap Definition of Done, the linked Phase $PHASE binding sections,
  current status/handoff, and the selected child-campaign note; historical
  iteration prose only when a machine artifact or current claim links to it
- $FEEDBACK
$initial_context_line
$selection_context

The acceptance contract and roadmap are authoritative. Existing prose, gate flags,
test counts and previous model verdicts are not proof. Preserve operator work. Use
only hash-verified pristine retail media as original-game authority; ALLMODS is
comparison evidence only. Provision external inputs from $REPO only when centrally
declared and hash-verified. Never commit copyrighted media, saves, movies, captures,
BIOS, credentials or generated disc images.

This is a measured six-iteration trial of the accepted operating method. Before doing
work, state a compact work packet in the retained log: the one selected campaign, at
most three coupled rows, the first unmet nine-dimension predicate, one exact claim,
one explicit falsifier, the evidence domain needed, and the predicted authoritative
machine layer. Do not begin with DuckStation or prose. An iteration counts only when
the controller can retain its evidence receipts and recompute its debt delta.

Before selecting a campaign or requesting a new operator fixture, recursively inventory
$REPO/movies/Phase$PHASE/ and the broader $REPO/movies/ tree when present. Prefer an
existing relevant recording over duplicating operator work. A filename is only a lead:
pair each movie with its declared start state, verify pristine mounted/save media, replay
the trigger, derive assertions from observed outcomes, and centrally hash-pin,
media-classify and declare every consumed external fixture. Do not force an unrelated
movie into the active campaign, treat a JSON serial string as media proof, import dirty
operator source, or commit the copyrighted/operator-owned recording bytes.

For Phase 4, regenerate and validate, in order:
- analysis/phase4_trace_capsule_set.json (central capsule index and preservation);
- analysis/phase4_offline_opportunity_queue.json (evidence availability);
- analysis/phase4_derived_index.json (external indexes already available for reuse);
- analysis/phase4_closure_debt.json (the nine roadmap dimensions and scheduler).
- analysis/phase4_movie_priority_queue.json (movie-ready work order only; never
  a closure or evidence-sufficiency claim).
The movie inventory/queue must read the centrally provisioned $WORKTREE/movies tree.
Never let its default resolve to the mutable operator checkout at $REPO/movies; new
operator recordings enter only after central declaration, hash pinning, and
provisioning.
The offline 107-row queue does not schedule work: offline_partial means only that offline
evidence was touched, never that a row is close to solved. Select exactly the campaign
named by the active scheduler projection in the transient closure-debt snapshot and
keep work in progress to its configured one-campaign/three-row maximum. Under
movie-ready, the generated packet above is that binding projection: work only its
selected rows, never drift to E15 while it is deferred, and do not merely replay a
movie. The movie is a trigger/evidence anchor, not proof. Do not begin another partial
row while the selected campaign can safely reduce a named dimension.

Use the closure funnel for that campaign:
1. OFFLINE localizes exact frames, fields, correlations and block candidates from an
   existing hash-pinned derived index or retained capsule.
2. STATIC reconstructs function bounds, xrefs, dispatch, stores/readers, structures,
   constants, assets and source status before another replay.
3. LIVE proves only a named missing causal/interface/control fact in the narrowed
   window.
4. BANK updates authoritative ASM/C/schema/registry first, then guards, Canon,
   Experiments, Mods contracts and the campaign handoff.
The selected row's next_lane is binding unless new low-level evidence changes and
regenerates the debt ledger. Under the default policy, two consecutive no-reduction
iterations require a method/lane change; under movie-ready, one no-reduction iteration
rotates the next executor to a disjoint generated batch. A dimension becomes met only through a complete campaign
audit or a dimension_claim backed by fresh low-level assertions, tracked machine paths,
confidence and non-intersecting residuals. Merely adding another summary artifact is
not progress.

The funnel is an enforced order, not a menu. Validate and query a relevant retained
capsule/index first; then exhaust static C/ASM, xrefs, owners, state and asset evidence.
Only after naming the exact missing domain may you escalate live. Do not replay the
same semantic experiment under a new label.

Before scanning capsule bytes, query analysis/phase4_derived_index.json and reuse its
exact external index when it covers the row/movie/domain. Use the pinned offline reader only
for a missing offline question. Capsules determine when and what changed; static RE
determines which code can own it; live DuckStation establishes exact cause. Keep all
game-derived index/capsule bytes external and commit only hashes, schemas, generators,
bounded summaries and falsifiable guards.

Before any live DuckStation escalation, create or update a generated machine-readable
analysis/phase4_live_escalations.json entry naming the target row/hypothesis, every
relevant capsule queried, exact offline commands/windows/domains, answers already
obtained, the specific information absent from the capsules, the exact live experiment
and control, its expected new evidence, and why no higher-priority offline-ready batch
supersedes it. Generic claims such as "needs exact causality/control" are insufficient.
Live work is allowed only for a named missing domain or resolution, a required native
control, an invalid/missing capsule, or a proven load-bearing dependency. Do not inflate
frame-boundary evidence into every-cycle attribution. When live work yields reusable
frame evidence, extend/supersede the capsule set under its preservation contract.
Report queue counts, selected rows, offline batch commands, derived findings, and any
escalation-record ID in the iteration decision evidence.

Every offline query completed this iteration must leave a closed
abl-phase4-offline-query/1 receipt under
$RUN_DIR/iteration-${iteration}-receipts/ with at least one hash-pinned external
input and one retained output. It must also pin the tracked Phase-4 reader and retain
the exact bounded command that names that reader, the canonical query as @query, every
input/output as a canonical @run/... or @repo/... token, and its zero exit code plus
exact stdout hash/body. The validator re-executes it with disposable outputs and
requires byte-identical results; an authored query with no producer, executed command,
bytes read, or bytes produced is not work. Every live operation must leave a closed
abl-phase4-live-run-receipt/2 there. Live receipts use typed anchor, execution bound
and capture window, domain, observer, perturbation, and control identities; free-form
windows and anchors are rejected. The controller hashes and validates these receipts.
Every counted offline input must be centrally preserved and classified as pristine
authority or derived pristine evidence. ALLMODS and other non-pristine derivatives are
comparison-only and cannot satisfy an authority-bearing query. Reuse metrics count
unique retained input hashes and bytes, never newly produced output bytes.
Do not create a receipt for work that did not complete, truncated, or lost raw
dependencies. Raw live evidence is not a summary: retain typed owned sessions and
completed jobs with start/stop counters, contiguous pagination and command events,
method-schema hashes from debugger.capabilities, the three media/capability identity
calls, and typed stop+confirmation actions for the owned numeric PID. Counters are
recomputed from those jobs. Each command event must name the owned server-session ID,
and every counted job must join by ordered job ID to one scenario.runBatch event with
a plan hash derived from the typed experiment and a completed result-bearing
scenario.getBatch event for that batch. Identity calls must be unique and precede the
batch, every getBatch must follow runBatch, and raw frame/instruction counters must
remain inside the typed finite bounds. Identity calls alone never admit raw jobs. The
capture window must sit inside its bound; precise
observer methods require a strictly wider passive prelude. Control anchor,
only-difference and paired-basis hashes are derived, not free salts, and every planned
investigator escalation must move to executed/closed in the after-ledger.
The normalized identity command-event result bodies must be retained and hash-derived,
not represented by authored digest strings alone. The retail media SHA-256 and the
source, running-binary, and API-surface identities must join to
analysis/phase3_duckstation_rpc_manifest.json at candidate HEAD; refresh that manifest
from the actual fork before live work if it is stale. Job IDs are unique per server
session, all clocks/input ranges/result limits are finitely bounded, and config paths
are canonicalized before the normal-profile exclusion. Do not hide instrumentation in
a scenario.runBatch observer entry: the observer plan names the direct typed observer,
while the atomic scenario is retained in the command/result stream. A precise receipt
is invalid unless its passive prelude is also a separately retained and fully validated
v2 live receipt in the same iteration.
Every investigator live receipt must be consumed and hash-listed by the fresh
campaign verifier before the iteration can validate; a self-authored transcript is
never sufficient promotion evidence.
Every non-null movie/state anchor hash must resolve through the central fixture audit
to provisioned, preservation-required pristine evidence. The anchor settings hash must
equal the retained settings-snapshot hash. Opaque or undeclared anchor digests are not
evidence.

For an authorized live experiment, prefer tools/phase4_duckstation_batch.py with a
validated one-to-128-job atomic plan. It must call debugger.capabilities, require the
current scenario.runBatch/loadStateAndRun/bootAndRun, provenanceLog and capture.atomic
surface, verify mounted pristine serial+hash, and execute same-anchor positive/negative
controls. Use functionTrace, reverse, GPU causality or SPU tracing only for the named
missing domain. Client-driven full-movie accessLog/execTrace loops are a fallback that
must be justified in the escalation ledger. Never use batch automation to weaken the
fresh isolated-config, dedicated-port/token, save inspection, or owned-PID cleanup
requirements.

For large clean checkouts, capsule output, and isolated emulator profiles, preflight
available space and user quota on /tmp and /var/tmp. If /tmp is quota-constrained, use
/var/tmp or a dedicated scratch directory under the run root; a quota failure is an
infrastructure condition, not evidence and not an operator blocker. When reproducing
the 2026-07-18 capsule toolchain, never launch the standalone archived executable at
~/Downloads/ABL-external-evidence/duckstation-binaries/. It is identification
evidence only and lacks its app-root resources. Validate SHA256SUMS and launch the
complete preserved runtime at ~/Downloads/ABL-external-evidence/duckstation-runtimes/trace-capsule-v1-20260718/duckstation-qt.

Implement the selected campaign's next closure dimension. Regenerate low-level evidence
before summaries, strengthen rather than weaken guards, and reconcile machine layers
before Obsidian prose. Use focused validation every iteration; run campaign-level
fixture/live/clean-checkout validation only when promoting a dimension or row, and the
full safe/local-media/107-row clean-checkout suite only for periodic campaign review or
whole-phase closure. For
DuckStation, obey AGENTS.md isolation, mounted-media verification and owned-PID rules.
Every promoted dimension claim must include a structured knowledge_bindings entry for
each asserted artifact: the exact inventoried producer, hash-pinned semantic source
paths plus the artifact JSON leaves retaining those hashes, and exact inventoried
pytest node IDs. The method validator collects and runs
those nodes, mutates each bound artifact in the isolated checkout, and requires the
same nodes to fail before restoring byte-exact clean state; comments, filename
substrings, unrelated config files, trivial tests, or a generic green report cannot
satisfy the join.
Follow the Obsidian Vault philosophy exactly: original-game facts and provenance belong
in Canon, runtime experiments and failed hypotheses in Experiments, and MOD-private
state/hooks/intended behavior in Mods. The roadmap hub controls phase sequence and
shared closure rules; the linked Phase $PHASE note controls its binding work packages,
evidence, exit gate and handoff. Do not use attractive prose to override either layer.
If a central fixture/source-manifest refresh changes only retained dependency identity,
use the bounded Phase-4 dependency reconcilers and
tools/phase4_reconcile_assertion_pins.py --write before regenerating coverage/debt.
That tool may update only artifact hashes and SHA-valued joined leaves; never use it to
change a behavioral expected value or to excuse a failed assertion.

Before returning any status, commit all scoped non-copyrighted source, schemas,
generators, validators, evidence summaries, tests and notes to branch $BRANCH and leave
the worktree clean. This includes open_autonomous: uncommitted progress is rejected.
Do not merge or push. Return open_autonomous and continue in a later iteration whenever
safe work remains. blocked_external is allowed
only for an exact operator-only fixture/recording/decision that cannot be produced or
derived safely; name it precisely and explain why no autonomous experiment can replace
it. closed is allowed only when every acceptance criterion is directly reproduced.

Return only the required JSON decision. candidate_commit must be the tested HEAD for
every status. Every validation
entry must include its command and observed result; never trust a high-level passes or
gate_met field without recomputing its low-level predicates.
Use one stable uppercase gap_code per gap. Executor decisions normally use empty
falsifier_results, verified_live_receipt_sha256s, and method_exceptions; never invent
a verifier receipt or exception.
EOF
}

make_verifier_prompt() {
  local iteration="$1" candidate="$2" executor_decision="$3" verify_dir="$4" out="$5"
  local selection_packet="${6:-}" selection_context=""
  if [[ -n "$selection_packet" ]]; then
    selection_context="$(cat <<EOF
- $selection_packet (movie-ready packet, SHA-256 $(sha256_path "$selection_packet"));
  independently verify its selected rows, exact movie/start-state hashes,
  capsule/index availability, score/rationale, rotation and previous packet
EOF
)"
  fi
  cat >"$out" <<EOF
You are a fresh, adversarial, read-only-in-intent verifier for Phase $PHASE in
Flik's Hard-Truth Ratchet, iteration $iteration. You did not implement this candidate.
The detached verification worktree is $verify_dir at commit $candidate.
The returned JSON field "phase" must be the integer 4. Phase-3 prerequisite
filenames and audit fields are evidence inputs, never the decision phase.

Read completely before testing:
- $verify_dir/AGENTS.md
- $RUN_DIR/acceptance-contract.md
- $RUN_DIR/operating-method.md
- the Obsidian roadmap hub and linked Phase $PHASE execution note
- $executor_decision (executor claim; evidence to challenge, never authority)
$selection_context

Independently reproduce every acceptance criterion from the committed candidate and
only its declared, centrally hash-pinned external fixture set. You may generate build
and test outputs inside this disposable verifier worktree, but do not edit source to
make it pass and do not commit. Use only the pristine retail image as behavioral
authority. Missing fixtures, skips, stale summaries, high-level passes/gate flags,
dirty-tree imports, untracked source dependencies, contradictory claims, or failure to
regenerate decisive evidence require rejection. Test clean-checkout durability,
fixture/media identity, freshness, safe suite, executable gates and any required live
DuckStation evidence. Check the actual low-level evidence behind every decisive claim.
Audit movie consumption specifically: a candidate may use recordings discovered under
$REPO/movies/Phase$PHASE/ or $REPO/movies/ only when each consumed fixture is centrally
declared, hash-pinned, media-classified, provisionable in the clean checkout, and backed
by replayed behavioral assertions. Reject direct dependencies on undeclared operator
movie bytes or claims inferred from filenames alone.
Validate the v2 method evidence for this iteration with the pinned
tools/phase4_method_metrics.py. Reject absolute/escaping references, hash drift,
authored pass counters, broken commit/debt chains, duplicate typed live experiment
keys, missing escalation joins, free-form live windows, missing fixed reports, or a
dirty clean-checkout receipt. Method metrics measure progress; they never waive the
Phase-4 closure gate.
For Phase 4, independently regenerate and validate the central capsule index,
analysis/phase4_offline_opportunity_queue.json, analysis/phase4_derived_index.json and
analysis/phase4_closure_debt.json, plus analysis/phase4_movie_priority_queue.json when
selection policy is movie-ready. Require exactly 107 unique registry rows, all nine
roadmap dimensions per row, current capsule/fixture/source hashes, no trusted high-level
complete/pass fields, no missing campaigns, and no hidden dimension errors. The queue
is an evidence-availability map, not a completion metric or scheduler; offline_partial
must never be counted as nearly solved. Falsify freshness, coverage, hash and dimension
guards in disposable copies: omitted/duplicate rows, source drift, corrupted capsule
metadata, untracked machine paths, missing assertions, or residual conflicts must turn
the affected row/dimension red.
Run tools/phase4_reconcile_assertion_pins.py --check. Reject any candidate that carries
stale assertion artifact identities, changes a non-hash behavioral expectation through
reconciliation, or retains a migration delta instead of a stable current-state report.

Re-run a representative sample of each retained derived-index schema and prove it is
reproducible from the preserved capsules under its declared comparison rule. Verify the
closure funnel for each accepted campaign: offline localization, static ownership/xref/
dispatch reconstruction, narrowly justified live causality when necessary, then machine
layer/guard/Canon/Experiment/MOD-contract banking. Reject token summaries, parallel
partial-row accumulation, WIP beyond the declared one-campaign/three-row limit, or a
dimension promotion lacking fresh low-level assertions, tracked authoritative ASM/C/
schema/registry paths, confidence and non-intersecting residuals.
Use the exact pinned offline reader when sampling retained capsules and derived indexes;
do not substitute a mutable operator-checkout helper.
Reject authority-bearing offline receipts whose inputs are non-pristine comparison
media, and compute reused external bytes from unique retained inputs only, never
outputs.

Audit analysis/phase4_live_escalations.json before accepting live evidence. Reject a
live replay when the entry uses a generic "needs causality/control" rationale, omits a
relevant capsule/query/domain, skips a higher-priority offline-ready alternative
without a proven load-bearing dependency, or recreates evidence derivable from retained
capsules.
Require the exact live experiment/control and expected new evidence to be stated before
the run. Verify any external cross-movie index is hash-manifested and reproducible from
preserved capsules, with no copyrighted capsule bytes committed. Reject filename-only
claims, manually asserted pass fields, or every-cycle claims inflated from frame data.
Every consumed capsule must remain externally preserved, hash-valid, pristine-authority
bound, independently control-matched, and reproducible under its comparison rule.
Reject live evidence produced with the incomplete standalone archived executable.
Require the complete preserved runtime bundle, validate its SHA256SUMS before launch,
and require the running-binary hash from debugger.capabilities to match the capsule pin.
For new live campaigns require a validated tools/phase4_duckstation_batch.py plan using
the current atomic scenario API, same-anchor positive/negative controls, pristine mounted
serial+hash, capability/schema identity, bounded provenance/capture results and owned-PID
cleanup. Client-driven full-movie accessLog/execTrace loops require a recorded reason
that the atomic batch/provenance surface cannot answer the named question.
Reject a live receipt unless every movie/state anchor is centrally declared,
preservation-required, provisioned pristine evidence and its settings hash matches the
retained settings snapshot.
Enforce the Obsidian Vault philosophy: original facts/provenance in Canon, runtime and
failed hypotheses in Experiments, MOD-private contracts in Mods, with the roadmap hub
and linked Phase $PHASE note retaining their documented authority and reciprocal links.

The supplied claim may come from recovery after a structurally invalid decision (for
example, status=closed with items placed in gaps). Do not normalize or waive those
items. Decide independently whether each is a Phase-$PHASE blocker, a roadmap-permitted
bounded frontier, or an unsupported claim. Your own returned decision must satisfy the
schema: closed means gaps is empty and required_input is empty.

Return closed only if the written Phase $PHASE contract is mechanically and
semantically satisfied. Return open_autonomous with exact reproducible gaps whenever
Codex can fix them without operator-only input. Return blocked_external only when a
specific missing recording/save/movie/asset or human decision is genuinely required;
name it in required_input and explain why no safe autonomous alternative exists.
candidate_commit must equal $candidate. Return only the required JSON decision.
The decision must contain "phase": 4; any other phase is structurally invalid.
Use one stable uppercase gap_code per gap. Record each actual adversarial check in
falsifier_results with outcome survived/falsified/not_run; a gap-free decision without
at least one survived falsifier is not promotion evidence. In every decision,
cite only closed repo:relative/path@sha256 or run:relative/path@sha256 evidence,
validation, and falsifier receipts; retain each falsifier under the run root using the
abl-phase4-verifier-falsifier/1 contract. Plain success/failure prose is not evidence.
Hash-list every v2
fresh-verifier live receipt you actually consumed and leave method_exceptions empty
unless the exact PRECISE_WINDOW_UNAVOIDABLE predicate is mechanically proven.
EOF
}

make_campaign_verifier_prompt() {
  local iteration="$1" candidate="$2" executor_decision="$3" verify_dir="$4"
  local before_debt="$5" after_debt="$6" progress="$7" out="$8"
  local selection_packet="${9:-}" selection_context=""
  if [[ -n "$selection_packet" ]]; then
    selection_context="$(cat <<EOF
- $selection_packet (movie-ready packet, SHA-256 $(sha256_path "$selection_packet"));
  independently verify its selected rows, exact movie/start-state hashes,
  capsule/index availability, score/rationale, rotation and previous packet
EOF
)"
  fi
  cat >"$out" <<EOF
You are a fresh, adversarial campaign-progress verifier for Phase $PHASE in
Flik's Hard-Truth Ratchet, iteration $iteration. You did not implement this candidate.
The detached verification worktree is $verify_dir at commit $candidate.
The returned JSON field "phase" must be the integer 4. Phase-3 prerequisite
filenames and audit fields are evidence inputs, never the decision phase.

Read completely before testing:
- $verify_dir/AGENTS.md
- $RUN_DIR/acceptance-contract.md
- $RUN_DIR/operating-method.md
- the roadmap's nine-part solved-subsystem definition and Phase-$PHASE binding work
  packages/current handoff (historical iteration prose only when evidence links it)
- $before_debt and $after_debt
- $progress
- $executor_decision
$selection_context

This is a bounded campaign review, not a whole-phase closure run. Independently test
only the selected campaign, every dimension/row promotion shown by the machine debt
delta, and any new evidence on which that delta depends. Do not reject merely because
other Phase-$PHASE campaigns remain open. Conversely, do not accept a promotion merely
because a claim, summary, status or gate says it passed.
When selection policy is movie-ready, this review is mandatory after every completed
executor iteration, including a no-promotion iteration. Recompute the 107-row priority
queue from debt, central fixture/movie pins and actual provisioned bytes, capsules,
derived indexes and ownership. Reject a stale/malformed packet, an E15 selection while
another eligible row remains, a batch over three or without an exact coupling, or a
movie replay presented as closure. A rejection's exact gaps must be returned for the
next executor; this scoped review never replaces the final whole-phase verifier.
Apply the operating method adversarially: require the claim/falsifier packet, prove
offline/capsule and static work preceded any live escalation, reject duplicate
experiment identities, and require typed v2 run receipts for live work.

Require fresh low-level assertions, tracked authoritative ASM/C/schema/registry paths,
fixture/media/capsule/derived-index hashes, relevant positive/negative controls,
confidence and non-intersecting residuals. Recompute the affected debt leaves and
falsify at least one guard. If live evidence is involved, verify the pre-run escalation,
atomic scenario batch, pristine mounted-media identity, capability/binary identity,
trace bounds and owned-PID cleanup. If offline evidence is involved, prove the existing
derived index was reused or that the named domain was genuinely absent. Enforce Canon,
Experiments and Mods placement plus the future-MOD consumption contract.

Return status=open_autonomous with gaps=[] when the scoped progress is sound. Return
status=open_autonomous with exact gaps when any promoted dimension/row or its durability
is unsupported. Return blocked_external only for exact operator-only input and explain
why no static/offline/live autonomous substitute exists. Never return closed from this
campaign review. candidate_commit must equal $candidate. Return only the required JSON.
The decision must contain "phase": 4; any other phase is structurally invalid.
Use stable uppercase gap_codes and retain concrete falsifier_results. A gap-free
campaign decision must include at least two survived falsifiers with distinct,
non-empty evidence plus non-empty evidence and validation arrays. Every verifier
evidence, validation, and falsifier evidence string must be a closed
reference of the form repo:relative/path@sha256 or run:relative/path@sha256. Store each
falsifier as an abl-phase4-verifier-falsifier/1 JSON receipt under
$RUN_DIR/iteration-${iteration}-verifier-evidence/ with exactly its id, candidate
commit, command array, exit code, outcome, output, and derived output SHA-256; cite that
receipt. Plain prose such as "pytest passed" or "not run" is not evidence. Hash-list any v2
fresh-verifier live receipt consumed; do not self-author method exceptions.
EOF
}

write_feedback() {
  local source="$1" decision="$2"
  python3 - "$source" "$decision" "$FEEDBACK" <<'PY'
import json, sys
doc = json.load(open(sys.argv[2], encoding="utf-8"))
out = {
    "source": sys.argv[1],
    "status": doc["status"],
    "summary": doc["summary"],
    "gaps": doc["gaps"],
    "required_input": doc["required_input"],
    "evidence": doc["evidence"],
    "validation": doc["validation"],
    "candidate_commit": doc["candidate_commit"],
}
with open(sys.argv[3], "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
}

write_agent_error_feedback() {
  local source="$1" decision="$2" validation_error="$3" candidate="$4"
  python3 - "$source" "$decision" "$validation_error" "$FEEDBACK" \
    "$candidate" <<'PY'
import json
import pathlib
import sys

source, decision_path, error_path, out_path, candidate = sys.argv[1:]
decision = {}
try:
    decision = json.loads(pathlib.Path(decision_path).read_text(encoding="utf-8"))
except Exception:
    pass
try:
    error = pathlib.Path(error_path).read_text(encoding="utf-8").strip()
except Exception:
    error = "agent did not return a ratchet-valid decision; inspect its retained log"

reported_gaps = decision.get("gaps")
if not isinstance(reported_gaps, list):
    reported_gaps = []
gaps = [f"Decision validation failed: {error}"]
gaps.extend(
    f"Reported item requiring roadmap-based adjudication: {item}"
    for item in reported_gaps if isinstance(item, str)
)
gaps.append(
    "Return closed only with gaps=[] and required_input empty. If a reported item is "
    "a permitted bounded frontier rather than a Phase closure gap, retain it explicitly "
    "in summary/evidence and justify that classification from the roadmap; never drop it."
)
out = {
    "source": source,
    "status": "open_autonomous",
    "summary": "The prior agent output was rejected structurally; preserved work must be "
               "reassessed rather than terminating the ratchet.",
    "gaps": gaps,
    "required_input": "",
    "evidence": decision.get("evidence", [])
                if isinstance(decision.get("evidence"), list) else [],
    "validation": decision.get("validation", [])
                  if isinstance(decision.get("validation"), list) else [],
    "candidate_commit": candidate,
}
pathlib.Path(out_path).write_text(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

finish_closed() {
  local candidate="$1" verifier_decision="$2"
  local agreement="${3:-executor and fresh verifier agree}"
  cat >"$RUN_DIR/RESULT.txt" <<EOF
$SCRIPT_NAME
Phase $PHASE: CLOSED
Candidate commit: $candidate
Branch: $BRANCH
Worktree: $WORKTREE
Verifier decision: $verifier_decision
Completed: $(date --iso-8601=seconds)

The branch was not merged automatically.
EOF
  printf '\n************************************************************\n'
  printf 'PHASE %s IS CLOSED — %s.\n' "$PHASE" "$agreement"
  printf 'Candidate: %s\nBranch: %s\nWorktree: %s\n' "$candidate" "$BRANCH" "$WORKTREE"
  printf 'Evidence and logs: %s\n' "$RUN_DIR"
  printf 'No merge was performed.\n'
  printf '************************************************************\n'
}

VERIFIER_DECISION=""
VERIFIER_STATUS=""

run_fresh_verifier() {
  local label="$1" slug="$2" candidate="$3" claim="$4"
  local selection_packet="${5:-}"
  local verify_dir="$RUN_DIR/verifier-worktree-$slug"
  local verifier_prompt="$RUN_DIR/${slug}-verifier.prompt.md"
  local verifier_decision="$RUN_DIR/${slug}-verifier.decision.json"
  local verifier_log="$RUN_DIR/${slug}-verifier.log"
  local verifier_error="${verifier_decision%.json}.validation-error.txt"
  local verifier_rc=0 verifier_head verifier_tree_status verifier_integrity

  git -C "$REPO" worktree add --detach "$verify_dir" "$candidate"
  make_verifier_prompt "$label" "$candidate" "$claim" \
    "$verify_dir" "$verifier_prompt" "$selection_packet"
  run_codex "FRESH VERIFIER $label" "$verify_dir" "$verifier_prompt" \
    "$verifier_decision" "$verifier_log" || verifier_rc=$?

  verifier_head="$(git -C "$verify_dir" rev-parse HEAD)"
  verifier_tree_status="$(git -C "$verify_dir" status --porcelain=v1 --untracked-files=all)"
  verifier_integrity="$RUN_DIR/${slug}-verifier-integrity.txt"
  {
    printf 'candidate_head=%s\n' "$candidate"
    printf 'verifier_head=%s\n' "$verifier_head"
    printf 'git_status:\n%s\n' "${verifier_tree_status:-<clean>}"
  } >"$verifier_integrity"
  if [[ -n "$verifier_tree_status" ]]; then
    printf '%s\n' "$verifier_tree_status" \
      >"$RUN_DIR/${slug}-verifier-dirty-status.txt"
  fi
  git -C "$REPO" worktree remove --force "$verify_dir" || true

  if ((verifier_rc != 0)); then
    write_agent_error_feedback "verifier_error_$slug" "$verifier_decision" \
      "$verifier_error" "$candidate"
    note "verifier $label failed structurally; returning its error to an executor"
    return 1
  fi
  if [[ "$verifier_head" != "$candidate" || -n "$verifier_tree_status" ]]; then
    cat >"$FEEDBACK" <<EOF
{
  "source": "ratchet_verifier_integrity_check",
  "status": "open_autonomous",
  "summary": "Fresh verifier invalidated its independence by changing HEAD or leaving tracked/untracked source drift.",
  "gaps": ["Make validation reproduce from candidate $candidate without source edits, commits, or generated tracked-file drift."],
  "required_input": "",
  "evidence": ["$verifier_integrity"],
  "validation": ["verifier independence check: failed"],
  "candidate_commit": "$candidate"
}
EOF
    note "verifier integrity check failed; returning to executor"
    return 1
  fi
  if [[ "$(json_field "$verifier_decision" candidate_commit)" != "$candidate" ]]; then
    write_feedback "verifier_commit_mismatch_$slug" "$verifier_decision"
    note "verifier commit mismatch; returning to executor"
    return 1
  fi

  VERIFIER_DECISION="$verifier_decision"
  VERIFIER_STATUS="$(json_field "$verifier_decision" status)"
  return 0
}

CAMPAIGN_VERIFIER_DECISION=""
CAMPAIGN_VERIFIER_GAPS=""

run_campaign_verifier() {
  local iteration="$1" candidate="$2" claim="$3" before_debt="$4"
  local after_debt="$5" progress="$6" selection_packet="${7:-}"
  local slug="iteration-${iteration}-campaign"
  local verify_dir="$RUN_DIR/verifier-worktree-$slug"
  local prompt="$RUN_DIR/${slug}-verifier.prompt.md"
  local decision="$RUN_DIR/${slug}-verifier.decision.json"
  local log="$RUN_DIR/${slug}-verifier.log"
  local error="${decision%.json}.validation-error.txt"
  local rc=0 head tree_status integrity

  git -C "$REPO" worktree add --detach "$verify_dir" "$candidate"
  make_campaign_verifier_prompt "$iteration" "$candidate" "$claim" \
    "$verify_dir" "$before_debt" "$after_debt" "$progress" "$prompt" \
    "$selection_packet"
  run_codex "CAMPAIGN VERIFIER $iteration" "$verify_dir" "$prompt" \
    "$decision" "$log" || rc=$?
  head="$(git -C "$verify_dir" rev-parse HEAD)"
  tree_status="$(git -C "$verify_dir" status --porcelain=v1 --untracked-files=all)"
  integrity="$RUN_DIR/${slug}-verifier-integrity.txt"
  {
    printf 'candidate_head=%s\n' "$candidate"
    printf 'verifier_head=%s\n' "$head"
    printf 'git_status:\n%s\n' "${tree_status:-<clean>}"
  } >"$integrity"
  git -C "$REPO" worktree remove --force "$verify_dir" || true

  if ((rc != 0)); then
    write_agent_error_feedback "campaign_verifier_error_$iteration" \
      "$decision" "$error" "$candidate"
    note "campaign verifier $iteration failed structurally"
    return 1
  fi
  if [[ "$head" != "$candidate" || -n "$tree_status" ]]; then
    cat >"$FEEDBACK" <<EOF
{
  "source": "ratchet_campaign_verifier_integrity_check",
  "status": "open_autonomous",
  "summary": "Campaign verifier invalidated its independence by changing HEAD or leaving source drift.",
  "gaps": ["Reproduce the scoped campaign review from candidate $candidate without source edits."],
  "required_input": "",
  "evidence": ["$integrity"],
  "validation": ["campaign verifier independence check: failed"],
  "candidate_commit": "$candidate"
}
EOF
    return 1
  fi
  if [[ "$(json_field "$decision" candidate_commit)" != "$candidate" ]]; then
    write_feedback "campaign_verifier_commit_mismatch_$iteration" "$decision"
    return 1
  fi
  if [[ "$(json_field "$decision" status)" == "closed" ]]; then
    cat >"$FEEDBACK" <<EOF
{
  "source": "ratchet_campaign_verifier_scope_check",
  "status": "open_autonomous",
  "summary": "Campaign verifier exceeded its scope by claiming whole-phase closure.",
  "gaps": ["Repeat the bounded campaign review and leave whole-phase closure to the final verifier."],
  "required_input": "",
  "evidence": ["$decision"],
  "validation": ["campaign verifier scope check: failed"],
  "candidate_commit": "$candidate"
}
EOF
    return 1
  fi
  CAMPAIGN_VERIFIER_DECISION="$decision"
  CAMPAIGN_VERIFIER_GAPS="$(json_field "$decision" gaps)"
  return 0
}

finish_blocked() {
  local candidate="$1" verifier_decision="$2"
  local required
  required="$(json_field "$verifier_decision" required_input)"
  cat >"$RUN_DIR/HUMAN_INPUT_REQUIRED.txt" <<EOF
$SCRIPT_NAME
Phase $PHASE: BLOCKED — EXTERNAL HUMAN INPUT CONFIRMED
Candidate commit: $candidate
Branch: $BRANCH
Worktree: $WORKTREE
Required input: $required
Verifier decision: $verifier_decision
Paused: $(date --iso-8601=seconds)

After supplying and centrally pinning the required input, start a new ratchet run with:
  $SCRIPT_PATH --phase $PHASE --selection-policy $SELECTION_POLICY --contract $CONTRACT --seed-ref $BRANCH
EOF
  printf '\n************************************************************\n'
  printf 'PHASE %s NEEDS CONFIRMED HUMAN INPUT\n' "$PHASE"
  printf '%s\n' "$required"
  printf 'Details: %s\n' "$RUN_DIR/HUMAN_INPUT_REQUIRED.txt"
  printf '************************************************************\n'
}

note "run ID: $RUN_ID"
note "branch: $BRANCH"
note "worktree: $WORKTREE"
note "logs/state: $RUN_DIR"
note "WARNING: Codex runs autonomously with sandbox=$SANDBOX"
repair_seed_before_trial
INITIAL_SELECTION_PACKET=""
if [[ "$SELECTION_POLICY" == "movie-ready" ]]; then
  INITIAL_SELECTION_PACKET="$RUN_DIR/iteration-1-movie-ready-packet.json"
  prepare_movie_ready_packet 1 "$INITIAL_SELECTION_PACKET" ||
    die "cannot generate the initial movie-ready work packet"
fi
initialize_method_trial "$INITIAL_SELECTION_PACKET"
note "v2 method trial initialized; metrics are hash-bound under $RUN_DIR/method-metrics"
CONSECUTIVE_INFRA_FAILURES=0

if [[ -n "$VERIFY_FIRST_CLAIM_SNAPSHOT" ]]; then
  recovery_candidate="$(git -C "$WORKTREE" rev-parse HEAD)"
  note "running recovery verifier before any new implementation iteration"
  if run_fresh_verifier "RECOVERY" "recovery" "$recovery_candidate" \
      "$VERIFY_FIRST_CLAIM_SNAPSHOT" "$INITIAL_SELECTION_PACKET"; then
    if [[ "$VERIFIER_STATUS" == "closed" ]]; then
      finish_closed "$recovery_candidate" "$VERIFIER_DECISION" \
        "recovered closure claim and fresh verifier agree"
      exit 0
    fi
    write_feedback "verify_first_recovery" "$VERIFIER_DECISION"
    note "recovery verifier did not close Phase $PHASE; feeding its findings to executor 1"
  fi
fi

for ((iteration = 1; MAX_ITERATIONS == 0 || iteration <= MAX_ITERATIONS; iteration++)); do
  if stop_requested_at_boundary "$iteration"; then
    exit 0
  fi
  before_debt=""
  after_debt=""
  progress=""
  selection_packet=""
  if [[ "$SELECTION_POLICY" == "movie-ready" ]]; then
    selection_packet="$RUN_DIR/iteration-${iteration}-movie-ready-packet.json"
    if ((iteration > 1)); then
      prepare_movie_ready_packet "$iteration" "$selection_packet" ||
        die "cannot rotate/generate movie-ready packet for iteration $iteration"
    fi
  fi
  base_commit="$(git -C "$WORKTREE" rev-parse HEAD)"
  events="$RUN_DIR/iteration-${iteration}-controller-events.json"
  receipt_dir="$RUN_DIR/iteration-${iteration}-receipts"
  before_ledger="$RUN_DIR/iteration-${iteration}-escalations-before.json"
  after_ledger="$RUN_DIR/iteration-${iteration}-escalations-after.json"
  mkdir -p "$receipt_dir"
  append_controller_event "$events" iteration_started \
    "{\"base_commit\":\"$base_commit\"}"
  capture_phase4_escalation_ledger "$before_ledger"
  if [[ "$PHASE" == "4" ]]; then
    before_debt="$RUN_DIR/iteration-${iteration}-debt-before.json"
    if ! capture_phase4_debt "$before_debt" "$selection_packet"; then
      append_controller_event "$events" infrastructure_failure \
        '{"code":"DEBT_BASELINE_CAPTURE_FAILED","cleanup":["no executor launched","no following iteration started"]}'
      write_terminal_failure_manifest "$iteration" "$base_commit" \
        "DEBT_BASELINE_CAPTURE_FAILED" "$events" || true
      die "cannot compute the Phase-4 closure-debt baseline for iteration $iteration"
    fi
  fi
  executor_prompt="$RUN_DIR/iteration-${iteration}-executor.prompt.md"
  executor_decision="$RUN_DIR/iteration-${iteration}-executor.decision.json"
  executor_log="$RUN_DIR/iteration-${iteration}-executor.log"
  make_executor_prompt "$iteration" "$executor_prompt" "$selection_packet"

  executor_rc=0
  run_codex "EXECUTOR $iteration" "$WORKTREE" "$executor_prompt" \
    "$executor_decision" "$executor_log" || executor_rc=$?
  if ((executor_rc != 0)); then
    actual_commit="$(git -C "$WORKTREE" rev-parse HEAD)"
    write_agent_error_feedback "executor_error_iteration_$iteration" \
      "$executor_decision" "${executor_decision%.json}.validation-error.txt" \
      "$actual_commit"
    if [[ "$actual_commit" != "$base_commit" ]] && worktree_clean "$WORKTREE"; then
      append_controller_event "$events" infrastructure_failure \
        '{"code":"EXECUTOR_PROCESS_OR_DECISION_FAILURE","cleanup":["clean candidate retained","fresh trial root requested"]}'
      automatic_reseed "$iteration" "$actual_commit" \
        "EXECUTOR_PROCESS_OR_DECISION_FAILURE" "$executor_log"
    fi
    if ! finalize_infrastructure_iteration "$iteration" "$base_commit" \
        "$before_debt" "$before_ledger" "$events" "$executor_log" \
        "EXECUTOR_PROCESS_OR_DECISION_FAILURE"; then
      die "executor failure left state that cannot be classified safely"
    fi
    CONSECUTIVE_INFRA_FAILURES=$((CONSECUTIVE_INFRA_FAILURES + 1))
    if ((CONSECUTIVE_INFRA_FAILURES >= 2)); then
      cat >"$RUN_DIR/OUTAGE_CIRCUIT_OPEN.txt" <<EOF
Two consecutive infrastructure failures occurred against immutable work packets.
Autonomous retries stopped. No semantic conclusion or external blocker was inferred.
EOF
      die "Phase-4 methodology outage circuit opened after two failures"
    fi
    note "iteration $iteration retained as infrastructure failure; one bounded retry remains"
    continue
  fi

  executor_status="$(json_field "$executor_decision" status)"
  executor_commit="$(json_field "$executor_decision" candidate_commit)"
  actual_commit="$(git -C "$WORKTREE" rev-parse HEAD)"
  append_controller_event "$events" executor_finished \
    "{\"status\":\"$executor_status\",\"candidate_commit\":\"$actual_commit\"}"
  if [[ "$executor_commit" != "$actual_commit" ]]; then
    cat >"$FEEDBACK" <<EOF
{
  "source": "ratchet_integrity_check",
  "status": "open_autonomous",
  "summary": "Executor reported a candidate commit that does not equal worktree HEAD.",
  "gaps": ["Report and test the actual HEAD: expected $actual_commit, reported $executor_commit"],
  "required_input": "",
  "evidence": [],
  "validation": [],
  "candidate_commit": "$actual_commit"
}
EOF
    note "iteration $iteration rejected: candidate commit mismatch"
    if [[ "$actual_commit" != "$base_commit" ]] && worktree_clean "$WORKTREE"; then
      append_controller_event "$events" infrastructure_failure \
        '{"code":"EXECUTOR_COMMIT_MISMATCH","cleanup":["clean actual HEAD retained","fresh trial root requested"]}'
      automatic_reseed "$iteration" "$actual_commit" \
        "EXECUTOR_COMMIT_MISMATCH" "$executor_decision"
    fi
    if ! finalize_infrastructure_iteration "$iteration" "$base_commit" \
        "$before_debt" "$before_ledger" "$events" "$executor_log" \
        "EXECUTOR_COMMIT_MISMATCH"; then
      die "candidate mismatch after source change requires recovery; no next iteration started"
    fi
    CONSECUTIVE_INFRA_FAILURES=$((CONSECUTIVE_INFRA_FAILURES + 1))
    ((CONSECUTIVE_INFRA_FAILURES < 2)) ||
      die "Phase-4 methodology outage circuit opened after two failures"
    continue
  fi

  if ! worktree_clean "$WORKTREE"; then
    git -C "$WORKTREE" status --short >"$RUN_DIR/iteration-${iteration}-dirty-status.txt"
    cat >"$FEEDBACK" <<EOF
{
  "source": "ratchet_integrity_check",
  "status": "open_autonomous",
  "summary": "Executor status rejected because the implementation worktree is dirty.",
  "gaps": ["Bank all scoped non-copyrighted work and remove transient untracked dependencies, then revalidate from committed HEAD."],
  "required_input": "",
  "evidence": ["$RUN_DIR/iteration-${iteration}-dirty-status.txt"],
  "validation": ["git status --porcelain=v1 --untracked-files=all: non-empty"],
  "candidate_commit": "$actual_commit"
}
EOF
    note "iteration $iteration rejected: worktree is dirty"
    append_controller_event "$events" infrastructure_failure \
      '{"code":"DIRTY_EXECUTOR_TERMINAL","cleanup":["dirty status retained","no following iteration started"]}'
    write_terminal_failure_manifest "$iteration" "$base_commit" \
      "DIRTY_EXECUTOR_TERMINAL" "$events" || true
    die "dirty executor terminal requires recovery; no next iteration started"
  fi

  trial_boundary="$RUN_DIR/iteration-${iteration}-trial-boundary.json"
  if ! python3 "$WORKTREE/tools/phase4_trial_boundary.py" \
      --repo "$WORKTREE" --base "$base_commit" --candidate "$actual_commit" \
      --out "$trial_boundary"; then
    automatic_reseed "$iteration" "$actual_commit" \
      "TRIAL_BOUNDARY_CLASSIFICATION_FAILED" "$trial_boundary"
  fi
  if [[ "$(json_field "$trial_boundary" reseed_required)" == "True" ]]; then
    append_controller_event "$events" infrastructure_failure \
      '{"code":"TRIAL_CRITICAL_CHANGE","cleanup":["clean candidate retained","fresh trial root requested"]}'
    automatic_reseed "$iteration" "$actual_commit" \
      "TRIAL_CRITICAL_CHANGE" "$trial_boundary"
  fi

  if [[ "$PHASE" == "4" ]]; then
    after_debt="$RUN_DIR/iteration-${iteration}-debt-after.json"
    progress="$RUN_DIR/iteration-${iteration}-progress.json"
    if ! capture_phase4_debt "$after_debt" "$selection_packet" 1; then
      cat >"$FEEDBACK" <<EOF
{
  "source": "phase4_closure_debt_check",
  "status": "open_autonomous",
  "summary": "Committed candidate rejected because its Phase-4 closure debt cannot be regenerated.",
  "gaps": ["Repair the authoritative closure-debt inputs/generator without weakening any dimension and commit the regenerated artifact."],
  "required_input": "",
  "evidence": ["$after_debt"],
  "validation": ["tools/phase4_closure_debt.py --snapshot: failed"],
  "candidate_commit": "$actual_commit"
}
EOF
      append_controller_event "$events" infrastructure_failure \
        '{"code":"DEBT_AFTER_CAPTURE_FAILED","cleanup":["clean candidate retained","fresh trial root requested"]}'
      automatic_reseed "$iteration" "$actual_commit" \
        "DEBT_AFTER_CAPTURE_FAILED" "$after_debt"
    fi
    phase4_progress_record "$before_debt" "$after_debt" "$iteration" "$progress"
    capture_phase4_escalation_ledger "$after_ledger"
  fi

  if [[ "$executor_status" == "open_autonomous" ]]; then
    row_transitions="$(json_field "$progress" row_transitions)"
    dimension_transitions="$(json_field "$progress" dimension_transitions)"
    target_campaign="$(json_field "$progress" campaign_id)"
    debt_reduced=False
    if [[ "$row_transitions" != "[]" || "$dimension_transitions" != "[]" ]]; then
      debt_reduced=True
    fi
    verifier_interval="$(phase4_policy_value campaign_verifier_interval)"
    stagnation_limit="$(phase4_policy_value stagnation_limit)"
    stagnation_count="$(phase4_stagnation_count)"
    live_receipt_count="$(phase4_live_receipt_count "$iteration")"
    campaign_review_due=0
    if [[ "$SELECTION_POLICY" == "movie-ready" ]] || \
       [[ "$row_transitions" != "[]" || "$dimension_transitions" != "[]" ]] || \
       (( live_receipt_count > 0 )) || \
       (( iteration % verifier_interval == 0 )) || \
       (( stagnation_count >= stagnation_limit )); then
      campaign_review_due=1
    fi

    method_verifier_decision=""
    method_verifier_log=""
    if ((campaign_review_due)); then
      if ! run_campaign_verifier "$iteration" "$actual_commit" \
          "$executor_decision" "$before_debt" "$after_debt" "$progress" \
          "$selection_packet"; then
        note "iteration $iteration campaign review failed; returning its findings"
        method_verifier_log="$RUN_DIR/iteration-${iteration}-campaign-verifier.log"
      elif [[ "$CAMPAIGN_VERIFIER_GAPS" != "[]" ]]; then
        method_verifier_decision="$CAMPAIGN_VERIFIER_DECISION"
        method_verifier_log="$RUN_DIR/iteration-${iteration}-campaign-verifier.log"
        write_feedback "campaign_verifier_iteration_$iteration" \
          "$CAMPAIGN_VERIFIER_DECISION"
        note "iteration $iteration campaign promotion rejected by fresh verifier"
      else
        method_verifier_decision="$CAMPAIGN_VERIFIER_DECISION"
        method_verifier_log="$RUN_DIR/iteration-${iteration}-campaign-verifier.log"
        write_feedback "campaign_verifier_accepted_iteration_$iteration" \
          "$CAMPAIGN_VERIFIER_DECISION"
        note "iteration $iteration campaign progress accepted by a fresh verifier"
      fi
    else
      write_feedback "executor_iteration_$iteration" "$executor_decision"
    fi

    if [[ "$SELECTION_POLICY" != "movie-ready" ]] && \
       [[ "$debt_reduced" != "True" ]] && \
       (( stagnation_count >= stagnation_limit )); then
      write_phase4_stagnation_feedback "$executor_decision" "$progress" \
        "$stagnation_count" "$actual_commit"
      note "iteration $iteration hit the Phase-4 stagnation guard; next executor must switch method"
    else
      note "iteration $iteration remains autonomously open with committed, measured progress"
    fi
    if ! finalize_method_iteration "$iteration" "$base_commit" "$actual_commit" \
        "$before_debt" "$after_debt" "$progress" "$before_ledger" \
        "$after_ledger" "$events" "$executor_log" "$method_verifier_decision" \
        "$method_verifier_log"; then
      automatic_reseed "$iteration" "$actual_commit" \
        "METHOD_EVIDENCE_REPAIR" "$RUN_DIR/METHOD_METRICS_FAILURE.txt"
    fi
    CONSECUTIVE_INFRA_FAILURES=0
    if [[ -f "$RUN_DIR/METHOD_REASSESSMENT_REQUIRED.txt" ]]; then
      note "method trial stopped at its mandatory reassessment boundary"
      exit 0
    fi
    continue
  fi

  if [[ "$SELECTION_POLICY" == "movie-ready" ]]; then
    if ! run_campaign_verifier "$iteration" "$actual_commit" \
        "$executor_decision" "$before_debt" "$after_debt" "$progress" \
        "$selection_packet"; then
      if ! finalize_method_iteration "$iteration" "$base_commit" "$actual_commit" \
          "$before_debt" "$after_debt" "$progress" "$before_ledger" \
          "$after_ledger" "$events" "$executor_log" "" \
          "$RUN_DIR/iteration-${iteration}-campaign-verifier.log"; then
        automatic_reseed "$iteration" "$actual_commit" \
          "METHOD_EVIDENCE_REPAIR" "$RUN_DIR/METHOD_METRICS_FAILURE.txt"
      fi
      note "movie-ready iteration $iteration campaign verifier failed structurally; exact validation gaps feed the next executor"
      continue
    fi
    if [[ "$CAMPAIGN_VERIFIER_GAPS" != "[]" ]]; then
      write_feedback "campaign_verifier_iteration_$iteration" \
        "$CAMPAIGN_VERIFIER_DECISION"
      if ! finalize_method_iteration "$iteration" "$base_commit" "$actual_commit" \
          "$before_debt" "$after_debt" "$progress" "$before_ledger" \
          "$after_ledger" "$events" "$executor_log" \
          "$CAMPAIGN_VERIFIER_DECISION" \
          "$RUN_DIR/iteration-${iteration}-campaign-verifier.log"; then
        automatic_reseed "$iteration" "$actual_commit" \
          "METHOD_EVIDENCE_REPAIR" "$RUN_DIR/METHOD_METRICS_FAILURE.txt"
      fi
      note "movie-ready iteration $iteration rejected by the mandatory campaign verifier; exact gaps feed the next executor"
      continue
    fi
  fi

  if ! run_fresh_verifier "$iteration" "iteration-$iteration" "$actual_commit" \
      "$executor_decision" "$selection_packet"; then
    if ! finalize_method_iteration "$iteration" "$base_commit" "$actual_commit" \
        "$before_debt" "$after_debt" "$progress" "$before_ledger" \
        "$after_ledger" "$events" "$executor_log" "" \
        "$RUN_DIR/iteration-${iteration}-verifier.log"; then
      automatic_reseed "$iteration" "$actual_commit" \
        "METHOD_EVIDENCE_REPAIR" "$RUN_DIR/METHOD_METRICS_FAILURE.txt"
    fi
    CONSECUTIVE_INFRA_FAILURES=0
    if [[ -f "$RUN_DIR/METHOD_REASSESSMENT_REQUIRED.txt" ]]; then
      note "method trial stopped at its mandatory reassessment boundary"
      exit 0
    fi
    continue
  fi

  if ! finalize_method_iteration "$iteration" "$base_commit" "$actual_commit" \
      "$before_debt" "$after_debt" "$progress" "$before_ledger" \
      "$after_ledger" "$events" "$executor_log" "$VERIFIER_DECISION" \
      "$RUN_DIR/iteration-${iteration}-verifier.log"; then
    automatic_reseed "$iteration" "$actual_commit" \
      "METHOD_EVIDENCE_REPAIR" "$RUN_DIR/METHOD_METRICS_FAILURE.txt"
  fi
  CONSECUTIVE_INFRA_FAILURES=0

  if [[ "$executor_status" == "closed" && "$VERIFIER_STATUS" == "closed" ]]; then
    finish_closed "$actual_commit" "$VERIFIER_DECISION"
    exit 0
  fi

  if [[ "$executor_status" == "blocked_external" && \
        "$VERIFIER_STATUS" == "blocked_external" ]]; then
    finish_blocked "$actual_commit" "$VERIFIER_DECISION"
    exit 2
  fi

  if [[ -f "$RUN_DIR/METHOD_REASSESSMENT_REQUIRED.txt" ]]; then
    note "method trial stopped at its mandatory reassessment boundary"
    exit 0
  fi
  write_feedback "fresh_verifier_iteration_$iteration" "$VERIFIER_DECISION"
  note "executor/verifier disagree or phase remains open; feeding verifier gaps to next executor"
done

cat >"$RUN_DIR/ITERATION_LIMIT.txt" <<EOF
$SCRIPT_NAME reached its iteration limit ($MAX_ITERATIONS) for Phase $PHASE.
Branch: $BRANCH
Worktree: $WORKTREE
Last feedback: $FEEDBACK
No closure claim was made.
EOF
die "iteration limit reached without independently verified closure; see $RUN_DIR"
