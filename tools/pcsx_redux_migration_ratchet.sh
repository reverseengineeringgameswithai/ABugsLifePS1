#!/usr/bin/env bash
# PCSX-Redux Full-Migration Ratchet
#
# Two-repository implementer -> fresh hard-ass verifier loop. The operator ABL,
# PCSX-Redux, and DuckStation checkouts are never edited. All implementation is
# committed on isolated ABL and Redux worktrees. Every verifier receives fresh
# detached worktrees and exact persistent context.

set -Eeuo pipefail

SCRIPT_NAME="PCSX-Redux Full-Migration Ratchet"
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

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

usage() {
  cat <<'EOF'
PCSX-Redux Full-Migration Ratchet

Implements the Obsidian PCSX-Redux migration plan through an autonomous loop:

  Step 1: an implementation owner advances the isolated ABL and Redux branches.
  Step 2: a fresh hard-ass verifier independently tests both exact commits.
  Accept: stop with a durable result.
  Reject: feed exact verifier gaps to a fresh implementation owner.
  External blocker: pause only after independent confirmation.

Usage:
  tools/pcsx_redux_migration_ratchet.sh [options]

Options:
  --abl-repo DIR          Operator ABL repository (default: containing repository)
  --redux-repo DIR        Operator Redux repository (default: ~/PCSX-Redux-RE)
  --abl-seed REF          ABL seed commit/ref (default: HEAD)
  --redux-seed REF        Redux seed commit/ref (default: HEAD)
  --plan FILE             Authoritative Obsidian migration plan
  --contract FILE         Strict migration acceptance contract
  --model MODEL           Optional Codex model override
  --sandbox MODE          Codex sandbox (default: danger-full-access)
  --max-rounds N          Maximum rounds; 0 means no limit (default: 0)
  --run-root DIR          Durable state root
                           (default: ~/.local/state/pcsx-redux-migration-ratchet)
  --resume RUN_ID         Resume an interrupted run from its preserved worktrees
  --status RUN_ID         Print durable status without changing the run
  --request-stop RUN_ID   Stop safely after the current implementer/verifier round
  --here                  Run the controller in this terminal
  --dry-run               Validate configuration without creating worktrees
  -h, --help              Show this help

Default launch behavior:

The controller is detached with nohup+setsid and a GNOME Terminal follows its durable
log. Closing the viewer does not stop the controller. Power loss does not erase branch
commits, worktrees, prompts, decisions, feedback, or the progress ledger.

Resume:

  ~/.local/state/pcsx-redux-migration-ratchet/runs/RUN_ID/resume.sh

Safe boundary stop:

  tools/pcsx_redux_migration_ratchet.sh --request-stop RUN_ID

The ratchet never merges or pushes either branch.
EOF
}

if contains_arg "--help" "$@" || contains_arg "-h" "$@"; then
  usage
  exit 0
fi

# The outer process launches a HUP-resistant controller. The terminal is only a
# viewer. Status/stop operations remain synchronous and never launch a controller.
if ! contains_arg "--internal-run" "$@" &&
   ! contains_arg "--here" "$@" &&
   ! contains_arg "--status" "$@" &&
   ! contains_arg "--request-stop" "$@"; then
  command -v gnome-terminal >/dev/null 2>&1 ||
    die "gnome-terminal is unavailable; rerun with --here"
  command -v setsid >/dev/null 2>&1 || die "setsid is unavailable"
  command -v nohup >/dev/null 2>&1 || die "nohup is unavailable"
  command -v tail >/dev/null 2>&1 || die "tail is unavailable"

  child=("$SCRIPT_PATH" --internal-run "$@")
  launcher_root="${XDG_STATE_HOME:-$HOME/.local/state}/pcsx-redux-migration-ratchet/launchers"
  launcher_id="$(date +%Y%m%d-%H%M%S)-$$"
  launcher_dir="$launcher_root/$launcher_id"
  launcher_log="$launcher_dir/controller.log"
  mkdir -p "$launcher_dir"
  : >"$launcher_log"
  nohup setsid "${child[@]}" </dev/null >>"$launcher_log" 2>&1 &
  controller_pid=$!
  printf '%s\n' "$controller_pid" >"$launcher_dir/controller.pid"
  {
    printf 'launcher_id=%s\n' "$launcher_id"
    printf 'controller_pid=%s\n' "$controller_pid"
    printf 'controller_log=%s\n' "$launcher_log"
    printf 'started=%s\n' "$(date --iso-8601=seconds)"
  } >"$launcher_dir/launcher.env"

  printf -v quoted_log '%q' "$launcher_log"
  viewer_cmd="tail --pid=$controller_pid -n +1 -F $quoted_log; printf '\\n%s\\n' 'Redux migration ratchet controller finished. Press Enter to close this viewer.'; read -r _"
  if ! gnome-terminal --title="$SCRIPT_NAME" -- bash -lc "$viewer_cmd"; then
    note "viewer failed to open; detached controller continues"
  fi
  note "launched detached controller pid $controller_pid"
  note "launcher log: $launcher_log"
  exit 0
fi

ABL_REPO=""
REDUX_REPO="$HOME/PCSX-Redux-RE"
ABL_SEED="HEAD"
REDUX_SEED="HEAD"
PLAN=""
CONTRACT=""
MODEL=""
SANDBOX="danger-full-access"
MAX_ROUNDS=0
MAX_ROUNDS_SET=0
RUN_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/pcsx-redux-migration-ratchet"
RESUME_ID=""
STATUS_ID=""
REQUEST_STOP_ID=""
DRY_RUN=0

while (($#)); do
  case "$1" in
    --abl-repo)
      (($# >= 2)) || die "--abl-repo requires a value"
      ABL_REPO="$2"; shift 2
      ;;
    --redux-repo)
      (($# >= 2)) || die "--redux-repo requires a value"
      REDUX_REPO="$2"; shift 2
      ;;
    --abl-seed)
      (($# >= 2)) || die "--abl-seed requires a value"
      ABL_SEED="$2"; shift 2
      ;;
    --redux-seed)
      (($# >= 2)) || die "--redux-seed requires a value"
      REDUX_SEED="$2"; shift 2
      ;;
    --plan)
      (($# >= 2)) || die "--plan requires a value"
      PLAN="$2"; shift 2
      ;;
    --contract)
      (($# >= 2)) || die "--contract requires a value"
      CONTRACT="$2"; shift 2
      ;;
    --model)
      (($# >= 2)) || die "--model requires a value"
      MODEL="$2"; shift 2
      ;;
    --sandbox)
      (($# >= 2)) || die "--sandbox requires a value"
      SANDBOX="$2"; shift 2
      ;;
    --max-rounds)
      (($# >= 2)) || die "--max-rounds requires a value"
      MAX_ROUNDS="$2"; MAX_ROUNDS_SET=1; shift 2
      ;;
    --run-root)
      (($# >= 2)) || die "--run-root requires a value"
      RUN_ROOT="$2"; shift 2
      ;;
    --resume)
      (($# >= 2)) || die "--resume requires a run ID"
      RESUME_ID="$2"; shift 2
      ;;
    --status)
      (($# >= 2)) || die "--status requires a run ID"
      STATUS_ID="$2"; shift 2
      ;;
    --request-stop)
      (($# >= 2)) || die "--request-stop requires a run ID"
      REQUEST_STOP_ID="$2"; shift 2
      ;;
    --here|--internal-run)
      shift
      ;;
    --dry-run)
      DRY_RUN=1; shift
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

[[ "$MAX_ROUNDS" =~ ^[0-9]+$ ]] || die "max rounds must be zero or a positive integer"
case "$SANDBOX" in
  read-only|workspace-write|danger-full-access) ;;
  *) die "invalid Codex sandbox: $SANDBOX" ;;
esac

json_field() {
  local path="$1" field="$2"
  python3 - "$path" "$field" <<'PY'
import json
import sys
value = json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]]
if isinstance(value, (dict, list)):
    print(json.dumps(value, ensure_ascii=False))
else:
    print(value)
PY
}

print_status() {
  local run_id="$1"
  local run_dir="$RUN_ROOT/runs/$run_id"
  [[ -d "$run_dir" ]] || die "run not found: $run_id"
  printf 'Run: %s\n' "$run_id"
  [[ -f "$run_dir/run.json" ]] && {
    printf 'ABL branch: %s\n' "$(json_field "$run_dir/run.json" abl_branch)"
    printf 'Redux branch: %s\n' "$(json_field "$run_dir/run.json" redux_branch)"
    printf 'ABL worktree: %s\n' "$(json_field "$run_dir/run.json" abl_worktree)"
    printf 'Redux worktree: %s\n' "$(json_field "$run_dir/run.json" redux_worktree)"
  }
  [[ -f "$run_dir/controller-state.json" ]] && {
    printf 'Stage: %s\n' "$(json_field "$run_dir/controller-state.json" stage)"
    printf 'Next round: %s\n' "$(json_field "$run_dir/controller-state.json" next_round)"
    printf 'Updated: %s\n' "$(json_field "$run_dir/controller-state.json" updated)"
  }
  if [[ -f "$run_dir/RESULT.md" ]]; then
    printf 'Terminal state: ACCEPTED\nResult: %s\n' "$run_dir/RESULT.md"
  elif [[ -f "$run_dir/HUMAN_INPUT_REQUIRED.md" ]]; then
    printf 'Terminal state: BLOCKED_EXTERNAL\nDetails: %s\n' \
      "$run_dir/HUMAN_INPUT_REQUIRED.md"
  elif [[ -f "$run_dir/INFRASTRUCTURE_PAUSED.md" ]]; then
    printf 'Terminal state: INFRASTRUCTURE_PAUSED\nDetails: %s\n' \
      "$run_dir/INFRASTRUCTURE_PAUSED.md"
  elif [[ -f "$run_dir/STOPPED_AT_BOUNDARY.md" ]]; then
    printf 'Terminal state: STOPPED_AT_BOUNDARY\nDetails: %s\n' \
      "$run_dir/STOPPED_AT_BOUNDARY.md"
  else
    printf 'Terminal state: ACTIVE_OR_INTERRUPTED\n'
  fi
  printf 'Feedback: %s\n' "$run_dir/feedback.json"
  printf 'Progress: %s\n' "$run_dir/progress-ledger.json"
}

if [[ -n "$STATUS_ID" ]]; then
  print_status "$STATUS_ID"
  exit 0
fi

if [[ -n "$REQUEST_STOP_ID" ]]; then
  stop_dir="$RUN_ROOT/runs/$REQUEST_STOP_ID"
  [[ -d "$stop_dir" ]] || die "run not found: $REQUEST_STOP_ID"
  {
    printf 'requested=%s\n' "$(date --iso-8601=seconds)"
    printf 'requester_pid=%s\n' "$$"
  } >"$stop_dir/stop-after-round"
  note "safe boundary stop requested for $REQUEST_STOP_ID"
  exit 0
fi

for cmd in git codex python3 sha256sum flock; do
  command -v "$cmd" >/dev/null 2>&1 || die "$cmd is not installed"
done

PLAN_REL="ObsidianVault/Playbooks/PCSX-Redux Migration Plan - Retire DuckStation as a Required Dependency.md"
CONTRACT_REL="engineering-specs/pcsx-redux-migration.md"
SCRIPT_REL="tools/pcsx_redux_migration_ratchet.sh"
TEST_REL="tests/test_pcsx_redux_migration_ratchet.py"
HUB_REL="ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md"
PHASE2_REL="ObsidianVault/Playbooks/Game Solving Roadmap/Phase 2 - Build the Pristine Whole-Game Behavioral Oracle.md"
PHASE4_REL="ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Solve Every Gameplay and Engine Subsystem.md"
DUCK_API_REL="ObsidianVault/Canon/Indexes/DuckStation_API_Index.md"
CAPSULE_NOTE_REL="ObsidianVault/Experiments/EXP_2026-07-18_phase4_trace_capsules.md"

validate_repositories() {
  git -C "$ABL_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "ABL is not a Git worktree: $ABL_REPO"
  git -C "$REDUX_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "Redux is not a Git worktree: $REDUX_REPO"
  git -C "$ABL_REPO" rev-parse --verify "${ABL_SEED}^{commit}" >/dev/null 2>&1 ||
    die "ABL seed does not resolve: $ABL_SEED"
  git -C "$REDUX_REPO" rev-parse --verify "${REDUX_SEED}^{commit}" >/dev/null 2>&1 ||
    die "Redux seed does not resolve: $REDUX_SEED"
  [[ -f "$PLAN" ]] || die "migration plan not found: $PLAN"
  [[ -f "$CONTRACT" ]] || die "migration contract not found: $CONTRACT"
  [[ -f "$ABL_REPO/AGENTS.md" ]] || die "ABL AGENTS.md is missing"
  [[ -f "$ABL_REPO/$TEST_REL" ]] || die "ratchet test is missing: $TEST_REL"
  [[ -f "$REDUX_REPO/LICENSE" ]] || die "Redux LICENSE is missing"
}

if [[ -n "$RESUME_ID" ]]; then
  RUN_ID="$RESUME_ID"
  RUN_DIR="$RUN_ROOT/runs/$RUN_ID"
  [[ -f "$RUN_DIR/run.json" ]] || die "resume run metadata missing: $RUN_DIR/run.json"
  ABL_REPO="$(json_field "$RUN_DIR/run.json" abl_repo)"
  REDUX_REPO="$(json_field "$RUN_DIR/run.json" redux_repo)"
  PLAN="$RUN_DIR/migration-plan.snapshot.md"
  CONTRACT="$RUN_DIR/acceptance-contract.snapshot.md"
  git -C "$ABL_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "recorded ABL repository is unavailable: $ABL_REPO"
  git -C "$REDUX_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "recorded Redux repository is unavailable: $REDUX_REPO"
  [[ -f "$PLAN" && -f "$CONTRACT" ]] ||
    die "run snapshots required for resume are missing"
else
  if [[ -z "$ABL_REPO" ]]; then
    ABL_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
  fi
  ABL_REPO="$(readlink -f "$ABL_REPO")"
  REDUX_REPO="$(readlink -f "$REDUX_REPO")"
  if [[ -z "$PLAN" ]]; then
    PLAN="$ABL_REPO/$PLAN_REL"
  elif [[ "$PLAN" != /* ]]; then
    PLAN="$ABL_REPO/$PLAN"
  fi
  if [[ -z "$CONTRACT" ]]; then
    CONTRACT="$ABL_REPO/$CONTRACT_REL"
  elif [[ "$CONTRACT" != /* ]]; then
    CONTRACT="$ABL_REPO/$CONTRACT"
  fi
  PLAN="$(readlink -f "$PLAN")"
  CONTRACT="$(readlink -f "$CONTRACT")"
  validate_repositories
fi

CODEX_VERSION="$(codex --version)"
CODEX_AUTH="$(codex login status 2>&1 || true)"
[[ "$CODEX_AUTH" == *"Logged in"* ]] || die "Codex is not authenticated: $CODEX_AUTH"

if [[ -n "$RESUME_ID" ]]; then
  RUN_ID="$RESUME_ID"
  RUN_DIR="$RUN_ROOT/runs/$RUN_ID"
  [[ -f "$RUN_DIR/run.json" ]] || die "resume run metadata missing: $RUN_DIR/run.json"

  ABL_REPO="$(json_field "$RUN_DIR/run.json" abl_repo)"
  REDUX_REPO="$(json_field "$RUN_DIR/run.json" redux_repo)"
  ABL_WORKTREE="$(json_field "$RUN_DIR/run.json" abl_worktree)"
  REDUX_WORKTREE="$(json_field "$RUN_DIR/run.json" redux_worktree)"
  ABL_BRANCH="$(json_field "$RUN_DIR/run.json" abl_branch)"
  REDUX_BRANCH="$(json_field "$RUN_DIR/run.json" redux_branch)"
  SANDBOX="$(json_field "$RUN_DIR/run.json" sandbox)"
  MODEL="$(json_field "$RUN_DIR/run.json" model)"
  if ((MAX_ROUNDS_SET == 0)); then
    MAX_ROUNDS="$(json_field "$RUN_DIR/run.json" max_rounds)"
  fi

  [[ -d "$ABL_WORKTREE/.git" || -f "$ABL_WORKTREE/.git" ]] ||
    die "ABL implementation worktree is missing: $ABL_WORKTREE"
  [[ -d "$REDUX_WORKTREE/.git" || -f "$REDUX_WORKTREE/.git" ]] ||
    die "Redux implementation worktree is missing: $REDUX_WORKTREE"
  PLAN_SNAPSHOT="$RUN_DIR/migration-plan.snapshot.md"
  CONTRACT_SNAPSHOT="$RUN_DIR/acceptance-contract.snapshot.md"
  AGENTS_SNAPSHOT="$RUN_DIR/AGENTS.snapshot.md"
  FEEDBACK="$RUN_DIR/feedback.json"
  PROGRESS="$RUN_DIR/progress-ledger.json"
  STATE="$RUN_DIR/controller-state.json"
  STOP_AFTER_ROUND="$RUN_DIR/stop-after-round"

  exec 9>"$RUN_DIR/controller.lock"
  flock -n 9 || die "another controller owns run $RUN_ID"
  if [[ -f "$RUN_DIR/RESULT.md" ]]; then
    note "run $RUN_ID is already independently accepted"
    printf 'Result: %s\n' "$RUN_DIR/RESULT.md"
    exit 0
  fi
  rm -f "$RUN_DIR/INFRASTRUCTURE_PAUSED.md" \
    "$RUN_DIR/STOPPED_AT_BOUNDARY.md" \
    "$RUN_DIR/HUMAN_INPUT_REQUIRED.md" \
    "$STOP_AFTER_ROUND"

  prior_stage="$(json_field "$STATE" stage)"
  next_round="$(json_field "$STATE" next_round)"
  stale_verify_abl="$(json_field "$STATE" active_verifier_abl)"
  stale_verify_redux="$(json_field "$STATE" active_verifier_redux)"
  if [[ -n "$stale_verify_abl" &&
        "$stale_verify_abl" == "$RUN_DIR"/verifier-worktrees/* &&
        -e "$stale_verify_abl/.git" ]]; then
    git -C "$ABL_REPO" worktree remove --force "$stale_verify_abl" || true
  fi
  if [[ -n "$stale_verify_redux" &&
        "$stale_verify_redux" == "$RUN_DIR"/verifier-worktrees/* &&
        -e "$stale_verify_redux/.git" ]]; then
    git -C "$REDUX_REPO" worktree remove --force "$stale_verify_redux" || true
  fi
  if [[ "$prior_stage" != "ready" ]]; then
    python3 - "$FEEDBACK" "$prior_stage" "$next_round" <<'PY'
import json
import os
import sys
from datetime import datetime
from pathlib import Path

out = {
    "source": "controller_recovery",
    "status": "rejected",
    "summary": "The prior controller was interrupted; preserve and audit both worktrees.",
    "gaps": [
        f"Recover interrupted stage {sys.argv[2]!r} at round {sys.argv[3]}. "
        "Inspect committed and uncommitted work in both isolated worktrees, retain valid "
        "progress, discard only proven transient output, and revalidate before claiming closure."
    ],
    "required_input": "",
    "evidence": [],
    "validation": [],
    "reviewed_abl_commit": "",
    "reviewed_redux_commit": "",
    "recovered_at": datetime.now().astimezone().isoformat(),
}
path = Path(sys.argv[1])
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
os.replace(tmp, path)
PY
  fi
  note "resuming run $RUN_ID at round $next_round (prior stage: $prior_stage)"
else
  note "ABL repository: $ABL_REPO"
  note "Redux repository: $REDUX_REPO"
  note "ABL seed: $ABL_SEED ($(git -C "$ABL_REPO" rev-parse "${ABL_SEED}^{commit}"))"
  note "Redux seed: $REDUX_SEED ($(git -C "$REDUX_REPO" rev-parse "${REDUX_SEED}^{commit}"))"
  note "plan: $PLAN"
  note "contract: $CONTRACT"
  note "Codex: $CODEX_VERSION"
  note "sandbox: $SANDBOX"
  if [[ -n "$(git -C "$ABL_REPO" status --porcelain=v1 --untracked-files=all)" ]]; then
    note "operator ABL checkout is dirty; it remains read-only"
  fi
  if [[ -n "$(git -C "$REDUX_REPO" status --porcelain=v1 --untracked-files=all)" ]]; then
    note "operator Redux checkout is dirty; it remains read-only"
  fi

  if ((DRY_RUN)); then
    note "dry run passed; no worktree or Codex session created"
    exit 0
  fi

  mkdir -p "$RUN_ROOT/runs" "$RUN_ROOT/worktrees"
  RUN_ID="redux-migration-$(date +%Y%m%d-%H%M%S)-$$"
  RUN_DIR="$RUN_ROOT/runs/$RUN_ID"
  ABL_WORKTREE="$RUN_ROOT/worktrees/$RUN_ID-abl"
  REDUX_WORKTREE="$RUN_ROOT/worktrees/$RUN_ID-redux"
  ABL_BRANCH="ratchet/redux-migration-${RUN_ID#redux-migration-}"
  REDUX_BRANCH="abl/redux-migration-${RUN_ID#redux-migration-}"
  mkdir -p "$RUN_DIR"

  exec 9>"$RUN_DIR/controller.lock"
  flock -n 9 || die "could not lock new run $RUN_ID"

  PLAN_SNAPSHOT="$RUN_DIR/migration-plan.snapshot.md"
  CONTRACT_SNAPSHOT="$RUN_DIR/acceptance-contract.snapshot.md"
  AGENTS_SNAPSHOT="$RUN_DIR/AGENTS.snapshot.md"
  FEEDBACK="$RUN_DIR/feedback.json"
  PROGRESS="$RUN_DIR/progress-ledger.json"
  STATE="$RUN_DIR/controller-state.json"
  STOP_AFTER_ROUND="$RUN_DIR/stop-after-round"

  cp -- "$PLAN" "$PLAN_SNAPSHOT"
  cp -- "$CONTRACT" "$CONTRACT_SNAPSHOT"
  cp -- "$ABL_REPO/AGENTS.md" "$AGENTS_SNAPSHOT"
  cp -- "$SCRIPT_PATH" "$RUN_DIR/controller.snapshot.sh"
  cp -- "$ABL_REPO/$TEST_REL" "$RUN_DIR/ratchet-test.snapshot.py"
  git -C "$ABL_REPO" status --short >"$RUN_DIR/abl-operator-status-at-start.txt"
  git -C "$REDUX_REPO" status --short >"$RUN_DIR/redux-operator-status-at-start.txt"

  for rel in "$HUB_REL" "$PHASE2_REL" "$PHASE4_REL" "$DUCK_API_REL" "$CAPSULE_NOTE_REL"; do
    if [[ -f "$ABL_REPO/$rel" ]]; then
      safe_name="$(printf '%s' "$rel" | tr '/ ' '__')"
      cp -- "$ABL_REPO/$rel" "$RUN_DIR/$safe_name.snapshot.md"
    fi
  done

  {
    printf 'abl_operator_head=%s\n' "$(git -C "$ABL_REPO" rev-parse HEAD)"
    printf 'abl_seed=%s\n' "$(git -C "$ABL_REPO" rev-parse "${ABL_SEED}^{commit}")"
    printf 'redux_operator_head=%s\n' "$(git -C "$REDUX_REPO" rev-parse HEAD)"
    printf 'redux_seed=%s\n' "$(git -C "$REDUX_REPO" rev-parse "${REDUX_SEED}^{commit}")"
    printf 'redux_submodules:\n'
    git -C "$REDUX_REPO" submodule status --recursive
    printf 'duckstation_head=%s\n' \
      "$(git -C "$HOME/duckstation" rev-parse HEAD 2>/dev/null || printf unavailable)"
    printf 'duckstation_status:\n'
    git -C "$HOME/duckstation" status --short 2>/dev/null || true
    printf 'codex=%s\n' "$CODEX_VERSION"
  } >"$RUN_DIR/source-state-at-start.txt"

  sha256sum "$PLAN_SNAPSHOT" "$CONTRACT_SNAPSHOT" "$AGENTS_SNAPSHOT" \
    "$RUN_DIR/controller.snapshot.sh" "$RUN_DIR/ratchet-test.snapshot.py" \
    >"$RUN_DIR/run-inputs.sha256"

  git -C "$ABL_REPO" worktree add -b "$ABL_BRANCH" "$ABL_WORKTREE" "$ABL_SEED"
  git -C "$REDUX_REPO" worktree add -b "$REDUX_BRANCH" "$REDUX_WORKTREE" "$REDUX_SEED"

  # Bootstrap only the explicitly selected ratchet/contract/plan files. The dirty
  # roadmap and all other operator WIP are not imported.
  bootstrap_rels=("$PLAN_REL" "$CONTRACT_REL" "$SCRIPT_REL" "$TEST_REL")
  bootstrap_sources=("$PLAN" "$CONTRACT" "$SCRIPT_PATH" "$ABL_REPO/$TEST_REL")
  for index in "${!bootstrap_rels[@]}"; do
    rel="${bootstrap_rels[$index]}"
    src="${bootstrap_sources[$index]}"
    mkdir -p "$ABL_WORKTREE/$(dirname "$rel")"
    cp -- "$src" "$ABL_WORKTREE/$rel"
  done
  chmod +x "$ABL_WORKTREE/$SCRIPT_REL"
  git -C "$ABL_WORKTREE" add -- "${bootstrap_rels[@]}"
  if ! git -C "$ABL_WORKTREE" diff --cached --quiet; then
    git -C "$ABL_WORKTREE" commit -m "chore(redux): bootstrap full-migration ratchet"
  fi

  cat >"$RUN_DIR/run.json" <<EOF
{
  "name": "$SCRIPT_NAME",
  "run_id": "$RUN_ID",
  "abl_repo": "$ABL_REPO",
  "redux_repo": "$REDUX_REPO",
  "abl_worktree": "$ABL_WORKTREE",
  "redux_worktree": "$REDUX_WORKTREE",
  "abl_branch": "$ABL_BRANCH",
  "redux_branch": "$REDUX_BRANCH",
  "abl_seed_ref": "$ABL_SEED",
  "redux_seed_ref": "$REDUX_SEED",
  "abl_seed_commit": "$(git -C "$ABL_REPO" rev-parse "${ABL_SEED}^{commit}")",
  "redux_seed_commit": "$(git -C "$REDUX_REPO" rev-parse "${REDUX_SEED}^{commit}")",
  "abl_bootstrap_commit": "$(git -C "$ABL_WORKTREE" rev-parse HEAD)",
  "redux_bootstrap_commit": "$(git -C "$REDUX_WORKTREE" rev-parse HEAD)",
  "plan_snapshot": "$PLAN_SNAPSHOT",
  "contract_snapshot": "$CONTRACT_SNAPSHOT",
  "sandbox": "$SANDBOX",
  "model": "$MODEL",
  "max_rounds": $MAX_ROUNDS,
  "started": "$(date --iso-8601=seconds)"
}
EOF

  cat >"$FEEDBACK" <<'EOF'
{
  "source": "initial",
  "status": "rejected",
  "summary": "No candidate has yet passed independent full-migration verification.",
  "gaps": [
    "Implement the authoritative WP0-WP10 migration plan and satisfy every machine-checked cutover predicate."
  ],
  "required_input": "",
  "evidence": [],
  "validation": [],
  "reviewed_abl_commit": "",
  "reviewed_redux_commit": ""
}
EOF
  printf '[]\n' >"$PROGRESS"
  cat >"$STATE" <<EOF
{
  "stage": "ready",
  "next_round": 1,
  "current_round": 0,
  "active_verifier_abl": "",
  "active_verifier_redux": "",
  "controller_pid": $$,
  "updated": "$(date --iso-8601=seconds)"
}
EOF

  cat >"$RUN_DIR/resume.sh" <<EOF
#!/usr/bin/env bash
exec "$RUN_DIR/controller.snapshot.sh" --resume "$RUN_ID" --run-root "$RUN_ROOT" "\$@"
EOF
  chmod +x "$RUN_DIR/resume.sh"
  ln -sfn "$RUN_DIR" "$RUN_ROOT/latest"
  next_round=1
fi

cat >"$RUN_DIR/implementer.schema.json" <<'JSON'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "role": {"type": "string", "enum": ["migration_implementer"]},
    "status": {"type": "string", "enum": ["candidate", "blocked_external"]},
    "summary": {"type": "string"},
    "completed_work": {"type": "array", "items": {"type": "string"}},
    "remaining_risks": {"type": "array", "items": {"type": "string"}},
    "evidence": {"type": "array", "items": {"type": "string"}},
    "validation": {"type": "array", "items": {"type": "string"}},
    "required_input": {"type": "string"},
    "abl_commit": {"type": "string"},
    "redux_commit": {"type": "string"}
  },
  "required": [
    "role", "status", "summary", "completed_work", "remaining_risks",
    "evidence", "validation", "required_input", "abl_commit", "redux_commit"
  ]
}
JSON

cat >"$RUN_DIR/verifier.schema.json" <<'JSON'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "role": {"type": "string", "enum": ["hard_ass_migration_verifier"]},
    "status": {"type": "string", "enum": ["accepted", "rejected", "blocked_external"]},
    "summary": {"type": "string"},
    "gaps": {"type": "array", "items": {"type": "string"}},
    "evidence": {"type": "array", "items": {"type": "string"}},
    "validation": {"type": "array", "items": {"type": "string"}},
    "required_input": {"type": "string"},
    "reviewed_abl_commit": {"type": "string"},
    "reviewed_redux_commit": {"type": "string"}
  },
  "required": [
    "role", "status", "summary", "gaps", "evidence", "validation",
    "required_input", "reviewed_abl_commit", "reviewed_redux_commit"
  ]
}
JSON

atomic_state() {
  local stage="$1" next="$2" current="$3" verify_abl="${4:-}" verify_redux="${5:-}"
  python3 - "$STATE" "$stage" "$next" "$current" "$verify_abl" "$verify_redux" "$$" <<'PY'
import json
import os
import sys
from datetime import datetime
from pathlib import Path

path = Path(sys.argv[1])
doc = {
    "stage": sys.argv[2],
    "next_round": int(sys.argv[3]),
    "current_round": int(sys.argv[4]),
    "active_verifier_abl": sys.argv[5],
    "active_verifier_redux": sys.argv[6],
    "controller_pid": int(sys.argv[7]),
    "updated": datetime.now().astimezone().isoformat(),
}
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
os.replace(tmp, path)
PY
}

append_progress() {
  local round="$1" role="$2" decision="$3"
  python3 - "$PROGRESS" "$round" "$role" "$decision" <<'PY'
import json
import os
import sys
from datetime import datetime
from pathlib import Path

path = Path(sys.argv[1])
try:
    rows = json.loads(path.read_text(encoding="utf-8"))
except FileNotFoundError:
    rows = []
try:
    decision = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
except Exception as exc:
    decision = {"structural_error": str(exc), "decision_path": sys.argv[4]}
rows.append({
    "round": int(sys.argv[2]),
    "role": sys.argv[3],
    "recorded": datetime.now().astimezone().isoformat(),
    "decision": decision,
})
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
os.replace(tmp, path)
PY
}

validate_implementer() {
  local path="$1" abl_head="$2" redux_head="$3"
  python3 - "$path" "$abl_head" "$redux_head" <<'PY'
import json
import sys

doc = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "role", "status", "summary", "completed_work", "remaining_risks",
    "evidence", "validation", "required_input", "abl_commit", "redux_commit"
}
if set(doc) != required:
    raise SystemExit(f"implementer keys differ: {sorted(set(doc) ^ required)}")
if doc["role"] != "migration_implementer":
    raise SystemExit("wrong implementer role")
if doc["status"] not in {"candidate", "blocked_external"}:
    raise SystemExit("invalid implementer status")
for key in ("completed_work", "remaining_risks", "evidence", "validation"):
    if not isinstance(doc[key], list) or not all(isinstance(v, str) for v in doc[key]):
        raise SystemExit(f"{key} must be an array of strings")
for key in ("summary", "required_input", "abl_commit", "redux_commit"):
    if not isinstance(doc[key], str):
        raise SystemExit(f"{key} must be a string")
if doc["abl_commit"] != sys.argv[2] or doc["redux_commit"] != sys.argv[3]:
    raise SystemExit("reported commits do not equal worktree HEADs")
if doc["status"] == "candidate" and doc["required_input"].strip():
    raise SystemExit("candidate cannot require external input")
if doc["status"] == "blocked_external" and not doc["required_input"].strip():
    raise SystemExit("blocked_external requires exact required_input")
PY
}

validate_verifier() {
  local path="$1" abl_head="$2" redux_head="$3"
  python3 - "$path" "$abl_head" "$redux_head" <<'PY'
import json
import sys

doc = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "role", "status", "summary", "gaps", "evidence", "validation",
    "required_input", "reviewed_abl_commit", "reviewed_redux_commit"
}
if set(doc) != required:
    raise SystemExit(f"verifier keys differ: {sorted(set(doc) ^ required)}")
if doc["role"] != "hard_ass_migration_verifier":
    raise SystemExit("wrong verifier role")
if doc["status"] not in {"accepted", "rejected", "blocked_external"}:
    raise SystemExit("invalid verifier status")
for key in ("gaps", "evidence", "validation"):
    if not isinstance(doc[key], list) or not all(isinstance(v, str) for v in doc[key]):
        raise SystemExit(f"{key} must be an array of strings")
if doc["reviewed_abl_commit"] != sys.argv[2]:
    raise SystemExit("reviewed ABL commit mismatch")
if doc["reviewed_redux_commit"] != sys.argv[3]:
    raise SystemExit("reviewed Redux commit mismatch")
if doc["status"] == "accepted" and (doc["gaps"] or doc["required_input"].strip()):
    raise SystemExit("accepted cannot carry gaps or required_input")
if doc["status"] == "rejected" and not doc["gaps"]:
    raise SystemExit("rejected requires exact gaps")
if doc["status"] == "blocked_external" and not doc["required_input"].strip():
    raise SystemExit("blocked_external requires exact required_input")
PY
}

worktree_clean() {
  [[ -z "$(git -C "$1" status --porcelain=v1 --untracked-files=all)" ]]
}

run_codex() {
  local role="$1" cwd="$2" add_dir="$3" prompt="$4" schema="$5" decision="$6" log="$7"
  local attempt rc delay
  local -a cmd
  cmd=(codex exec --ephemeral --color always -s "$SANDBOX")
  if [[ -n "$MODEL" ]]; then
    cmd+=(-m "$MODEL")
  fi
  cmd+=(-C "$cwd" --add-dir "$add_dir" --output-schema "$schema"
        --output-last-message "$decision" -)

  for attempt in 1 2 3; do
    rm -f -- "$decision"
    {
      printf '\n============================================================\n'
      printf '%s — %s — attempt %s\n' "$SCRIPT_NAME" "$role" "$attempt"
      printf '============================================================\n'
      cat "$prompt"
      printf '\n-------------------- Codex live output ---------------------\n'
    } | tee -a "$log"
    set +e
    "${cmd[@]}" <"$prompt" 2>&1 | tee -a "$log"
    rc=${PIPESTATUS[0]}
    set -e
    if ((rc == 0)); then
      return 0
    fi
    delay=$((attempt * attempt * 5))
    note "$role exited $rc (attempt $attempt/3); retrying in ${delay}s"
    sleep "$delay"
  done
  return "$rc"
}

write_controller_feedback() {
  local source="$1" summary="$2" gap="$3" abl_head="$4" redux_head="$5"
  python3 - "$FEEDBACK" "$source" "$summary" "$gap" "$abl_head" "$redux_head" <<'PY'
import json
import os
import sys
from pathlib import Path

doc = {
    "source": sys.argv[2],
    "status": "rejected",
    "summary": sys.argv[3],
    "gaps": [sys.argv[4]],
    "required_input": "",
    "evidence": [],
    "validation": [],
    "reviewed_abl_commit": sys.argv[5],
    "reviewed_redux_commit": sys.argv[6],
}
path = Path(sys.argv[1])
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
os.replace(tmp, path)
PY
}

write_verifier_feedback() {
  local decision="$1"
  python3 - "$decision" "$FEEDBACK" <<'PY'
import json
import os
import sys
from pathlib import Path

doc = json.load(open(sys.argv[1], encoding="utf-8"))
out = {
    "source": "hard_ass_migration_verifier",
    "status": doc["status"],
    "summary": doc["summary"],
    "gaps": doc["gaps"],
    "required_input": doc["required_input"],
    "evidence": doc["evidence"],
    "validation": doc["validation"],
    "reviewed_abl_commit": doc["reviewed_abl_commit"],
    "reviewed_redux_commit": doc["reviewed_redux_commit"],
}
path = Path(sys.argv[2])
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
os.replace(tmp, path)
PY
}

make_implementer_prompt() {
  local round="$1" out="$2"
  cat >"$out" <<EOF
You are Step 1, the implementation owner for round $round of the PCSX-Redux
full-migration ratchet. Work autonomously in two isolated implementation worktrees:

- ABL: $ABL_WORKTREE on $ABL_BRANCH
- Redux: $REDUX_WORKTREE on $REDUX_BRANCH

The operator checkouts $ABL_REPO, $REDUX_REPO, and $HOME/duckstation are read-only.
Do not merge or push.

Read completely before acting:

- $AGENTS_SNAPSHOT
- $CONTRACT_SNAPSHOT
- $PLAN_SNAPSHOT
- $RUN_DIR/source-state-at-start.txt
- $FEEDBACK
- $PROGRESS
- $ABL_WORKTREE/AGENTS.md
- $ABL_WORKTREE/$PLAN_REL
- $ABL_WORKTREE/$HUB_REL
- the candidate Phase 2 and Phase 4 notes, fixture manifests, machine layers, tests,
  scenarios, and relevant C/ASM
- the actual Redux source, tests, docs, and Git state under $REDUX_WORKTREE

The immutable plan and contract snapshots are authoritative. Candidate prose may add
evidence but may not weaken them. Prior agents, green summaries, checkboxes, API counts,
test counts, and this prompt are not proof.

The destination is not a Redux prototype. PCSX-Redux must become fully armed as the
primary and sole emulator required for ordinary ABL reverse engineering, deterministic
movies, scenario automation, persistent offline analysis, and release regression.
Frozen DuckStation remains readable historical evidence and an optional independent
cross-check. Satisfy every WP0-WP10 requirement and every cutover predicate in the plan.

Inspect both worktrees for interrupted or prior-round work. Preserve valid progress.
Use the progress ledger and verifier gaps to avoid redoing qualified work, then select
the highest-leverage unresolved dependency. Implement substantive safe work in the
appropriate repository or repositories. Update authoritative machine layers before
summaries and Obsidian prose. Add tests with deliberate falsification where practical.
Do not defer an autonomous requirement merely because the full migration is large.

Use only hash-verified pristine retail media as original-game behavioral authority.
ALLMODS is comparison/known-bad evidence only. Keep copyrighted fixtures external and
centrally hash-pinned. Follow exact isolated-profile, mounted-media, instrumentation
re-arming, cold-boot/state separation, and owned-PID cleanup rules. Inspect the frozen
DuckStation implementation only to understand independently specified behavior; never
copy its CC BY-NC-ND source into GPLv2 Redux.

For movie and state work, prove complete effective digital+analog input, exact frame
semantics, identity, state completeness, truncation/error handling, repeated
determinism, and instrumented/uninstrumented equality. For automation and RE work,
prove real ABL consumers, structured failures, provenance, captures, capsules/offline
queries, clean-checkout durability, and campaign/oracle integration. A newly recorded
Redux movie does not independently validate Redux. Use semantic milestones and
cross-emulator/hardware/static adjudication.

Run validation proportional to every change. Before returning, commit all scoped
non-copyrighted changes to the two named ratchet branches and leave both worktrees
clean. It is acceptable for one repository's HEAD to remain unchanged in a round, but
report both exact HEADs. Do not commit media, BIOS, saves, movies, cards, captures,
capsules, tokens, credentials, or generated discs.

Return status=candidate so the hard-ass verifier can independently decide whether the
entire migration is finished. List remaining risks honestly; they do not prevent the
verifier from examining real progress. Use blocked_external only for an exact
operator-only input that cannot be generated, recovered, converted, or replaced safely.
Return only the required JSON. abl_commit and redux_commit must equal the tested
worktree HEADs. Every validation entry must contain the command and observed result.
EOF
}

make_verifier_prompt() {
  local round="$1" abl_candidate="$2" redux_candidate="$3" claim="$4"
  local abl_verify="$5" redux_verify="$6" out="$7"
  cat >"$out" <<EOF
You are Step 2, a fresh, adversarial, hard-ass verifier for round $round of the
PCSX-Redux full-migration ratchet. You did not implement this candidate.

Detached candidate checkouts:

- ABL: $abl_verify at $abl_candidate
- Redux: $redux_verify at $redux_candidate

Read completely before testing:

- $AGENTS_SNAPSHOT
- $CONTRACT_SNAPSHOT
- $PLAN_SNAPSHOT
- $RUN_DIR/source-state-at-start.txt
- $PROGRESS
- $claim
- $abl_verify/AGENTS.md
- $abl_verify/$PLAN_REL
- $abl_verify/$HUB_REL
- the actual ABL consumers, fixtures, manifests, scenarios, tests, C/ASM, and knowledge
  layers in the detached candidate
- the actual Redux C++/Lua/API implementation, save-state schema, input path, tests,
  build system, and documentation in the detached candidate

Your acceptance standard is deliberately severe: accept only if PCSX-Redux is FULLY
armed to be the main replacement for this ABL RE project in actual daily operation.
Useful features, a movie prototype, partial API parity, a pilot, future work, attractive
documentation, or green high-level summaries are rejection outcomes.

Independently apply every WP0-WP10 requirement and every exit checkbox in the immutable
Obsidian plan snapshot. Recompute low-level predicates. Inspect actual C++ behavior and
actual ABL call sites rather than trusting method names. Falsify freshness, coverage,
identity, corruption, truncation, deterministic frame/input semantics, save-state
completeness, physical-input exclusion, structured failure, process isolation, cleanup,
capsule preservation, fixture declarations, and hidden-source imports.

Require repeated clean-profile cold-boot and state-anchored controls. Require
instrumented and uninstrumented equality over CPU registers/cycle, RAM, scratchpad,
GTE, VRAM, SPU RAM, movie/frame state, and every declared device domain. Require
digital and analog/two-port coverage. Require known-bad/corrupt controls to fail.
Require the complete load-bearing Phase-2 oracle and active Phase-4 scenario surface,
not a conveniently selected sample. A Redux recording validates only its input stream;
it cannot serve as independent proof that Redux emulates the pristine game correctly.

Require the exact external fixture and preservation set, Redux clean-checkout build,
source/submodule/toolchain/runtime hashes, emulator-neutral scenarios, campaign-used
trace/provenance features, persistent offline evidence, and continued readability of
historical DuckStation evidence. Reject copied DuckStation implementation, license
ambiguity, undeclared operator-tree dependencies, skipped fixtures, stale generated
artifacts, and documentation that outruns retained evidence.

Use pristine retail media as behavioral authority and ALLMODS only as comparison.
Obey isolated profile and exact-owned cleanup rules. You may build and generate
temporary outputs in run-owned /tmp or /var/tmp paths, but do not edit source, commit,
or leave either detached checkout dirty. Do not “fix” the candidate while verifying.

Return accepted only when every plan predicate is mechanically and semantically
satisfied, gaps=[], and required_input is empty. Return rejected with exact,
reproducible, prioritized gaps whenever safe autonomous work remains; those gaps feed
the next implementation owner verbatim. Return blocked_external only when you confirm
a precise operator-owned input that cannot be safely generated or replaced. Return
only the required JSON. reviewed_abl_commit must be $abl_candidate and
reviewed_redux_commit must be $redux_candidate.
EOF
}

pause_infrastructure() {
  local role="$1" log="$2" round="$3"
  atomic_state "infrastructure_paused" "$round" "$round"
  cat >"$RUN_DIR/INFRASTRUCTURE_PAUSED.md" <<EOF
# PCSX-Redux migration ratchet paused on infrastructure

- Run: \`$RUN_ID\`
- Round: $round
- Role: $role
- Log: \`$log\`
- ABL branch: \`$ABL_BRANCH\`
- Redux branch: \`$REDUX_BRANCH\`
- Paused: $(date --iso-8601=seconds)

No migration verdict was inferred from the process failure. Resume with:

\`$RUN_DIR/resume.sh\`
EOF
  die "$role failed after retries; preserved run can be resumed"
}

finish_blocked() {
  local decision="$1" round="$2"
  local required
  required="$(json_field "$decision" required_input)"
  atomic_state "blocked_external" "$((round + 1))" "$round"
  cat >"$RUN_DIR/HUMAN_INPUT_REQUIRED.md" <<EOF
# PCSX-Redux migration requires confirmed external input

- Run: \`$RUN_ID\`
- Round: $round
- ABL branch: \`$ABL_BRANCH\`
- Redux branch: \`$REDUX_BRANCH\`
- Decision: \`$decision\`

## Exact required input

$required

After the input is supplied, centrally hash-pinned, and preserved, resume with:

\`$RUN_DIR/resume.sh\`
EOF
  note "hard-ass verifier confirmed an external blocker"
  note "details: $RUN_DIR/HUMAN_INPUT_REQUIRED.md"
}

finish_accepted() {
  local decision="$1" round="$2" abl_head="$3" redux_head="$4"
  atomic_state "accepted" "$((round + 1))" "$round"
  cp -- "$decision" "$RUN_DIR/final-verifier.decision.json"
  cat >"$RUN_DIR/RESULT.md" <<EOF
# PCSX-Redux full migration independently accepted

- Run: \`$RUN_ID\`
- Round: $round
- ABL commit: \`$abl_head\`
- Redux commit: \`$redux_head\`
- ABL branch: \`$ABL_BRANCH\`
- Redux branch: \`$REDUX_BRANCH\`
- ABL worktree: \`$ABL_WORKTREE\`
- Redux worktree: \`$REDUX_WORKTREE\`
- Verifier decision: \`$RUN_DIR/final-verifier.decision.json\`
- Completed: $(date --iso-8601=seconds)

The hard-ass verifier accepted the complete immutable migration contract with no gaps
or required input. The branches were not merged or pushed.
EOF
  printf '\n************************************************************\n'
  printf 'PCSX-REDUX FULL MIGRATION ACCEPTED\n'
  printf 'ABL candidate: %s\nRedux candidate: %s\n' "$abl_head" "$redux_head"
  printf 'Result: %s\n' "$RUN_DIR/RESULT.md"
  printf 'No merge or push was performed.\n'
  printf '************************************************************\n'
}

note "run ID: $RUN_ID"
note "ABL branch: $ABL_BRANCH"
note "Redux branch: $REDUX_BRANCH"
note "ABL worktree: $ABL_WORKTREE"
note "Redux worktree: $REDUX_WORKTREE"
note "logs/state: $RUN_DIR"
note "WARNING: Codex runs autonomously with sandbox=$SANDBOX"
note "the hard-ass verifier runs after every structurally valid committed candidate"

round="$next_round"
while ((MAX_ROUNDS == 0 || round <= MAX_ROUNDS)); do
  if [[ -e "$STOP_AFTER_ROUND" ]]; then
    atomic_state "ready" "$round" "$((round - 1))"
    cat >"$RUN_DIR/STOPPED_AT_BOUNDARY.md" <<EOF
# PCSX-Redux migration ratchet stopped at a safe boundary

- Run: \`$RUN_ID\`
- Next round suppressed: $round
- ABL branch: \`$ABL_BRANCH\`
- Redux branch: \`$REDUX_BRANCH\`
- ABL HEAD: \`$(git -C "$ABL_WORKTREE" rev-parse HEAD)\`
- Redux HEAD: \`$(git -C "$REDUX_WORKTREE" rev-parse HEAD)\`
- Feedback: \`$FEEDBACK\`

No closure claim was made. Resume with:

\`$RUN_DIR/resume.sh\`
EOF
    note "safe boundary stop honored before round $round"
    exit 0
  fi

  attempt_tag="$(date +%Y%m%d-%H%M%S)-$$"
  impl_prompt="$RUN_DIR/round-${round}-${attempt_tag}-implementer.prompt.md"
  impl_decision="$RUN_DIR/round-${round}-${attempt_tag}-implementer.decision.json"
  impl_log="$RUN_DIR/round-${round}-${attempt_tag}-implementer.log"
  make_implementer_prompt "$round" "$impl_prompt"
  atomic_state "implementer_running" "$round" "$round"

  if ! run_codex "STEP 1 MIGRATION IMPLEMENTER $round" "$ABL_WORKTREE" \
      "$REDUX_WORKTREE" "$impl_prompt" "$RUN_DIR/implementer.schema.json" \
      "$impl_decision" "$impl_log"; then
    pause_infrastructure "implementer round $round" "$impl_log" "$round"
  fi

  abl_head="$(git -C "$ABL_WORKTREE" rev-parse HEAD)"
  redux_head="$(git -C "$REDUX_WORKTREE" rev-parse HEAD)"
  if ! validate_implementer "$impl_decision" "$abl_head" "$redux_head" \
      2>"$RUN_DIR/round-${round}-implementer-validation-error.txt"; then
    append_progress "$round" "implementer_structural_rejection" "$impl_decision"
    write_controller_feedback "implementer_structural_rejection" \
      "The implementation agent returned an invalid decision." \
      "Inspect the retained validation error, preserve both worktrees, commit scoped work, and return exact current ABL/Redux HEADs." \
      "$abl_head" "$redux_head"
    note "round $round implementer decision failed structural validation"
    round=$((round + 1))
    atomic_state "ready" "$round" "$((round - 1))"
    continue
  fi
  append_progress "$round" "implementer" "$impl_decision"

  if ! worktree_clean "$ABL_WORKTREE" || ! worktree_clean "$REDUX_WORKTREE"; then
    git -C "$ABL_WORKTREE" status --short \
      >"$RUN_DIR/round-${round}-abl-implementation-dirty.txt"
    git -C "$REDUX_WORKTREE" status --short \
      >"$RUN_DIR/round-${round}-redux-implementation-dirty.txt"
    write_controller_feedback "implementation_integrity" \
      "The candidate cannot enter fresh verification because an implementation worktree is dirty." \
      "Preserve and commit all scoped non-copyrighted work, remove transient outputs or redirect them outside the source trees, then revalidate both exact HEADs." \
      "$abl_head" "$redux_head"
    note "round $round candidate rejected before verification: dirty implementation worktree"
    round=$((round + 1))
    atomic_state "ready" "$round" "$((round - 1))"
    continue
  fi

  verify_abl="$RUN_DIR/verifier-worktrees/round-${round}-${attempt_tag}-abl"
  verify_redux="$RUN_DIR/verifier-worktrees/round-${round}-${attempt_tag}-redux"
  mkdir -p "$(dirname "$verify_abl")"
  git -C "$ABL_REPO" worktree add --detach "$verify_abl" "$abl_head"
  git -C "$REDUX_REPO" worktree add --detach "$verify_redux" "$redux_head"

  verifier_prompt="$RUN_DIR/round-${round}-${attempt_tag}-verifier.prompt.md"
  verifier_decision="$RUN_DIR/round-${round}-${attempt_tag}-verifier.decision.json"
  verifier_log="$RUN_DIR/round-${round}-${attempt_tag}-verifier.log"
  make_verifier_prompt "$round" "$abl_head" "$redux_head" "$impl_decision" \
    "$verify_abl" "$verify_redux" "$verifier_prompt"
  atomic_state "verifier_running" "$round" "$round" "$verify_abl" "$verify_redux"

  verifier_rc=0
  run_codex "STEP 2 HARD-ASS VERIFIER $round" "$verify_abl" "$verify_redux" \
    "$verifier_prompt" "$RUN_DIR/verifier.schema.json" "$verifier_decision" \
    "$verifier_log" || verifier_rc=$?

  verifier_abl_head="$(git -C "$verify_abl" rev-parse HEAD)"
  verifier_redux_head="$(git -C "$verify_redux" rev-parse HEAD)"
  verifier_abl_status="$(git -C "$verify_abl" status --porcelain=v1 --untracked-files=all)"
  verifier_redux_status="$(git -C "$verify_redux" status --porcelain=v1 --untracked-files=all)"
  {
    printf 'candidate_abl=%s\nverifier_abl=%s\nabl_status:\n%s\n' \
      "$abl_head" "$verifier_abl_head" "${verifier_abl_status:-<clean>}"
    printf 'candidate_redux=%s\nverifier_redux=%s\nredux_status:\n%s\n' \
      "$redux_head" "$verifier_redux_head" "${verifier_redux_status:-<clean>}"
  } >"$RUN_DIR/round-${round}-verifier-integrity.txt"
  git -C "$ABL_REPO" worktree remove --force "$verify_abl" || true
  git -C "$REDUX_REPO" worktree remove --force "$verify_redux" || true

  if ((verifier_rc != 0)); then
    pause_infrastructure "verifier round $round" "$verifier_log" "$round"
  fi

  if [[ "$verifier_abl_head" != "$abl_head" ||
        "$verifier_redux_head" != "$redux_head" ||
        -n "$verifier_abl_status" ||
        -n "$verifier_redux_status" ]]; then
    write_controller_feedback "verifier_integrity" \
      "The fresh verifier invalidated its read-only independence." \
      "Reproduce verification from detached candidate commits without editing source, committing, or leaving generated tracked/untracked drift in either checkout." \
      "$abl_head" "$redux_head"
    append_progress "$round" "verifier_integrity_rejection" "$verifier_decision"
    note "round $round verifier integrity failed; exact gap returns to implementer"
    round=$((round + 1))
    atomic_state "ready" "$round" "$((round - 1))"
    continue
  fi

  if ! validate_verifier "$verifier_decision" "$abl_head" "$redux_head" \
      2>"$RUN_DIR/round-${round}-verifier-validation-error.txt"; then
    write_controller_feedback "verifier_structural_rejection" \
      "The verifier output failed the ratchet schema and cannot close migration." \
      "Keep the candidate, inspect the retained verifier output/error, and address every reported or implied gap; accepted requires gaps=[] and no required input." \
      "$abl_head" "$redux_head"
    append_progress "$round" "verifier_structural_rejection" "$verifier_decision"
    note "round $round verifier decision failed structural validation"
    round=$((round + 1))
    atomic_state "ready" "$round" "$((round - 1))"
    continue
  fi

  append_progress "$round" "hard_ass_verifier" "$verifier_decision"
  verifier_status="$(json_field "$verifier_decision" status)"
  write_verifier_feedback "$verifier_decision"

  if [[ "$verifier_status" == "accepted" ]]; then
    finish_accepted "$verifier_decision" "$round" "$abl_head" "$redux_head"
    exit 0
  fi
  if [[ "$verifier_status" == "blocked_external" ]]; then
    finish_blocked "$verifier_decision" "$round"
    exit 2
  fi

  note "hard-ass verifier rejected round $round; exact gaps feed round $((round + 1))"
  round=$((round + 1))
  atomic_state "ready" "$round" "$((round - 1))"
done

atomic_state "round_limit" "$round" "$((round - 1))"
cat >"$RUN_DIR/ROUND_LIMIT.md" <<EOF
# PCSX-Redux migration ratchet reached its configured round limit

- Run: \`$RUN_ID\`
- Limit: $MAX_ROUNDS
- ABL branch: \`$ABL_BRANCH\`
- Redux branch: \`$REDUX_BRANCH\`
- Last feedback: \`$FEEDBACK\`

No closure claim was made. Resume with a higher limit or zero:

\`$RUN_DIR/resume.sh --max-rounds 0\`
EOF
die "round limit reached without independent acceptance; see $RUN_DIR"
