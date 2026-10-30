#!/usr/bin/env bash
# Flik's Hard-Truth Ratchet
#
# Autonomous ABL phase executor/verifier loop. The outer invocation starts a
# detached, HUP-resistant controller and opens a terminal that only follows its
# durable log. Closing that viewer cannot kill the controller. The operator working
# tree is used only as the repository/fixture source and is never edited by this
# script; Git worktree metadata is added for the isolated branch.

set -Eeuo pipefail

SCRIPT_NAME="Flik's Hard-Truth Ratchet"
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"

usage() {
  cat <<'EOF'
Flik's Hard-Truth Ratchet — autonomous ABL phase implement/verify loop

Usage:
  tools/flik_hard_truth_ratchet.sh [options]

The default invocation starts a detached controller, opens a GNOME Terminal log
viewer, and returns immediately. Closing the viewer does not stop the controller.

Options:
  --phase N              Roadmap phase to close (default: 3)
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
  --seed-ref REF         Git commit/branch used for the isolated worktree
                         (default: current HEAD)
  --repo DIR             ABL operator repository (default: containing repo)
  --model MODEL          Codex model override (default: Codex configuration)
  --max-iterations N     Maximum executor iterations (default: 12)
  --run-root DIR         Durable logs/state root
                         (default: ~/.local/state/flik-hard-truth-ratchet)
  --sandbox MODE         Codex sandbox mode (default: danger-full-access;
                         required for local DuckStation automation)
  --here                 Run in the current terminal instead of opening one
  --dry-run              Validate configuration without creating a worktree
  -h, --help             Show this help

Safe boundary stop for an active run:
  touch <run-root>/runs/<run-id>/stop-after-iteration

The sentinel is checked before every new executor iteration. The active executor
and any verifier belonging to its claim finish first; no following executor starts.

Example from an existing Codex session:
  tools/flik_hard_truth_ratchet.sh \
    --phase 3 \
    --contract engineering-specs/phase3-closure.md \
    --seed-ref wip/phase3-dirty-repair-20260713

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
  launcher_root="${XDG_STATE_HOME:-$HOME/.local/state}/flik-hard-truth-ratchet/launchers"
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

PHASE=3
CONTRACT=""
INITIAL_CONTEXT=""
VERIFY_FIRST_CLAIM=""
SEED_REF="HEAD"
REPO=""
MODEL=""
MAX_ITERATIONS=12
RUN_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/flik-hard-truth-ratchet"
SANDBOX="danger-full-access"
DRY_RUN=0

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
[[ "$MAX_ITERATIONS" =~ ^[1-9][0-9]*$ ]] ||
  die "max iterations must be a positive integer"
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
git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
  die "not a Git worktree: $REPO"
git -C "$REPO" rev-parse --verify "${SEED_REF}^{commit}" >/dev/null 2>&1 ||
  die "seed ref does not resolve to a commit: $SEED_REF"

if [[ -z "$CONTRACT" ]]; then
  phase_contract="$REPO/engineering-specs/phase${PHASE}-closure.md"
  roadmap="$REPO/ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md"
  if [[ -f "$phase_contract" ]]; then
    CONTRACT="$phase_contract"
  else
    CONTRACT="$roadmap"
  fi
elif [[ "$CONTRACT" != /* ]]; then
  CONTRACT="$REPO/$CONTRACT"
fi
CONTRACT="$(readlink -f "$CONTRACT")"
[[ -f "$CONTRACT" ]] || die "acceptance contract not found: $CONTRACT"
[[ -f "$REPO/AGENTS.md" ]] || die "AGENTS.md not found in $REPO"
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

CODEX_VERSION="$(codex --version)"
CODEX_AUTH="$(codex login status 2>&1 || true)"
[[ "$CODEX_AUTH" == *"Logged in"* ]] || die "Codex is not authenticated: $CODEX_AUTH"

note "repository: $REPO"
note "phase: $PHASE"
note "contract: $CONTRACT"
if [[ -n "$INITIAL_CONTEXT" ]]; then
  note "initial context: $INITIAL_CONTEXT"
fi
if [[ -n "$VERIFY_FIRST_CLAIM" ]]; then
  note "verify-first claim: $VERIFY_FIRST_CLAIM"
fi
note "seed: $(git -C "$REPO" rev-parse "${SEED_REF}^{commit}") ($SEED_REF)"
note "Codex: $CODEX_VERSION"
note "sandbox: $SANDBOX"
if [[ -n "$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)" ]]; then
  note "operator repository is dirty; it will remain untouched"
fi

if ((DRY_RUN)); then
  note "dry run passed; no worktree or Codex session created"
  exit 0
fi

mkdir -p "$RUN_ROOT"
RUN_ID="phase${PHASE}-$(date +%Y%m%d-%H%M%S)-$$"
RUN_DIR="$RUN_ROOT/runs/$RUN_ID"
WORKTREE="$RUN_ROOT/worktrees/$RUN_ID"
BRANCH="ratchet/phase${PHASE}-${RUN_ID#phase${PHASE}-}"
mkdir -p "$RUN_DIR" "$(dirname "$WORKTREE")"

cp -- "$CONTRACT" "$RUN_DIR/acceptance-contract.md"
cp -- "$REPO/AGENTS.md" "$RUN_DIR/AGENTS.snapshot.md"
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

cat >"$RUN_DIR/decision.schema.json" <<'JSON'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "phase": {"type": "integer"},
    "status": {
      "type": "string",
      "enum": ["closed", "open_autonomous", "blocked_external"]
    },
    "summary": {"type": "string"},
    "gaps": {"type": "array", "items": {"type": "string"}},
    "evidence": {"type": "array", "items": {"type": "string"}},
    "validation": {"type": "array", "items": {"type": "string"}},
    "required_input": {"type": "string"},
    "candidate_commit": {"type": "string"}
  },
  "required": [
    "phase", "status", "summary", "gaps", "evidence", "validation",
    "required_input", "candidate_commit"
  ]
}
JSON

git -C "$REPO" worktree add -b "$BRANCH" "$WORKTREE" "$SEED_REF"

cat >"$RUN_DIR/run.json" <<JSON
{
  "name": "Flik's Hard-Truth Ratchet",
  "run_id": "$RUN_ID",
  "phase": $PHASE,
  "operator_repo": "$REPO",
  "worktree": "$WORKTREE",
  "branch": "$BRANCH",
  "seed_ref": "$SEED_REF",
  "seed_commit": "$(git -C "$WORKTREE" rev-parse HEAD)",
  "contract_snapshot": "$RUN_DIR/acceptance-contract.md",
  "contract_sha256": "$(sha256sum "$RUN_DIR/acceptance-contract.md" | awk '{print $1}')",
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
if [[ -n "$MODEL" ]]; then
  codex_base+=(-m "$MODEL")
fi

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
    "phase", "status", "summary", "gaps", "evidence", "validation",
    "required_input", "candidate_commit"
}
if set(doc) != required:
    raise SystemExit(f"decision keys differ: {sorted(set(doc) ^ required)}")
if doc["phase"] != int(sys.argv[2]):
    raise SystemExit("decision phase mismatch")
if doc["status"] not in {"closed", "open_autonomous", "blocked_external"}:
    raise SystemExit("invalid decision status")
for key in ("gaps", "evidence", "validation"):
    if not isinstance(doc[key], list) or not all(isinstance(v, str) for v in doc[key]):
        raise SystemExit(f"{key} must be an array of strings")
for key in ("summary", "required_input", "candidate_commit"):
    if not isinstance(doc[key], str):
        raise SystemExit(f"{key} must be a string")
if doc["status"] == "blocked_external" and not doc["required_input"].strip():
    raise SystemExit("blocked_external requires exact required_input")
if doc["status"] == "closed" and (doc["gaps"] or doc["required_input"].strip()):
    raise SystemExit("closed cannot carry gaps or required_input")
PY
}

run_codex() {
  local role="$1" cwd="$2" prompt="$3" decision="$4" log="$5"
  local validation_error="${decision%.json}.validation-error.txt"
  printf '\n============================================================\n'
  printf '%s — Phase %s — %s\n' "$SCRIPT_NAME" "$PHASE" "$role"
  printf '============================================================\n'
  cat "$prompt"
  printf '\n-------------------- Codex live output ---------------------\n'
  set +e
  "${codex_base[@]}" -C "$cwd" \
    --output-schema "$RUN_DIR/decision.schema.json" \
    --output-last-message "$decision" - <"$prompt" 2>&1 | tee "$log"
  local rc=${PIPESTATUS[0]}
  set -e
  if ((rc != 0)); then
    printf '%s Codex process exited %s; inspect %s\n' "$role" "$rc" "$log" \
      >"$validation_error"
    note "$role Codex exited $rc"
    return "$rc"
  fi
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
Last feedback: $FEEDBACK
Stop request: ${request_text:-<empty sentinel>}
No closure claim was made by this boundary stop.
EOF
  note "boundary-stop sentinel found; executor $next_iteration will not start"
  note "resume by launching a new run from candidate $stopped_head"
  return 0
}

make_executor_prompt() {
  local iteration="$1" out="$2"
  local initial_context_line=""
  if [[ -n "$INITIAL_CONTEXT_SNAPSHOT" ]]; then
    initial_context_line="- $INITIAL_CONTEXT_SNAPSHOT (persistent run context; re-read it and verify every claim this iteration)"
  fi
  cat >"$out" <<EOF
You are the implementation owner for Phase $PHASE in Flik's Hard-Truth Ratchet,
iteration $iteration. Work autonomously in this isolated Git worktree.

Read completely before acting:
- $WORKTREE/AGENTS.md
- $RUN_DIR/acceptance-contract.md (sha256 recorded beside it)
- the Obsidian roadmap hub and its linked Phase $PHASE execution note
- $FEEDBACK
$initial_context_line

The acceptance contract and roadmap are authoritative. Existing prose, gate flags,
test counts and previous model verdicts are not proof. Preserve operator work. Use
only hash-verified pristine retail media as original-game authority; ALLMODS is
comparison evidence only. Provision external inputs from $REPO only when centrally
declared and hash-verified. Never commit copyrighted media, saves, movies, captures,
BIOS, credentials or generated disc images.

Before selecting a campaign or requesting a new operator fixture, recursively inventory
$REPO/movies/Phase$PHASE/ and the broader $REPO/movies/ tree when present. Prefer an
existing relevant recording over duplicating operator work. A filename is only a lead:
pair each movie with its declared start state, verify pristine mounted/save media, replay
the trigger, derive assertions from observed outcomes, and centrally hash-pin,
media-classify and declare every consumed external fixture. Do not force an unrelated
movie into the active campaign, treat a JSON serial string as media proof, import dirty
operator source, or commit the copyrighted/operator-owned recording bytes.

For Phase 4, the retained trace capsules are a substantial offline work queue, not a
one-query preflight. Read the Phase 4 capsule Experiment note and
analysis/phase4_trace_capsule_set.json, then validate its preservation/freshness and
the exact pinned offline reader. Create or refresh the authoritative generated
analysis/phase4_offline_opportunity_queue.json from the current 107-row registry,
coverage matrix, fixture audit, movie inventory, and capsule index before choosing the
iteration target. Its generator and guard must fail on stale inputs, omitted/duplicate
rows, non-current hashes, or a row count other than 107. For every row it must expose:
current completion state; campaign/family and dependencies; relevant movie/capsule
hashes and available domains; exact offline batch queries; questions and assertions
derivable offline; named unknowns; prior escalation; priority; and exactly one derived
classification from offline_ready, offline_partial, live_required, or no_capsule.
Never trust a manually authored pass/complete field.

Use that queue to select a subsystem-sized batch: analyze all relevant capsules for
one coherent campaign cluster, or at least the three highest-value open offline-ready
rows when no larger coherent cluster exists. Prefer open offline-ready rows over live-
only freshness/depth work. Do not repeatedly deepen one partial row or spend an
iteration mainly refreshing a prior phase while higher-ranked Phase-4 offline work is
available, unless a mechanically demonstrated load-bearing dependency blocks the
batch. Use the exact hash-pinned reader for cross-movie frame windows, RAM/register/
VRAM/SPU change points, deltas, correlations, and execution hotspots. Build or reuse an
external cross-movie derived index when repeated scans would otherwise replay the same
queries; keep copyrighted capsule bytes outside Git and commit only its generator,
schema, preservation manifest/hashes, non-copyrighted summaries, and falsifiable tests.

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

For large clean checkouts, capsule output, and isolated emulator profiles, preflight
available space and user quota on /tmp and /var/tmp. If /tmp is quota-constrained, use
/var/tmp or a dedicated scratch directory under the run root; a quota failure is an
infrastructure condition, not evidence and not an operator blocker. When reproducing
the 2026-07-18 capsule toolchain, never launch the standalone archived executable at
~/Downloads/ABL-external-evidence/duckstation-binaries/. It is identification
evidence only and lacks its app-root resources. Validate SHA256SUMS and launch the
complete preserved runtime at ~/Downloads/ABL-external-evidence/duckstation-runtimes/trace-capsule-v1-20260718/duckstation-qt.

Implement every safe in-scope requirement still open. Regenerate low-level evidence
before summaries, strengthen rather than weaken guards, run the required safe/live/
clean-checkout validation, and reconcile machine layers before Obsidian prose. For
DuckStation, obey AGENTS.md isolation, mounted-media verification and owned-PID rules.
Follow the Obsidian Vault philosophy exactly: original-game facts and provenance belong
in Canon, runtime experiments and failed hypotheses in Experiments, and MOD-private
state/hooks/intended behavior in Mods. The roadmap hub controls phase sequence and
shared closure rules; the linked Phase $PHASE note controls its binding work packages,
evidence, exit gate and handoff. Do not use attractive prose to override either layer.

Before returning closed or blocked_external, commit all scoped non-copyrighted source,
schemas, generators, validators, evidence summaries, tests and notes to branch
$BRANCH and leave the worktree clean. Do not merge or push. Return open_autonomous and
continue in a later iteration whenever safe work remains. blocked_external is allowed
only for an exact operator-only fixture/recording/decision that cannot be produced or
derived safely; name it precisely and explain why no autonomous experiment can replace
it. closed is allowed only when every acceptance criterion is directly reproduced.

Return only the required JSON decision. candidate_commit must be the tested HEAD for
closed/blocked_external, or the current HEAD for open_autonomous. Every validation
entry must include its command and observed result; never trust a high-level passes or
gate_met field without recomputing its low-level predicates.
EOF
}

make_verifier_prompt() {
  local iteration="$1" candidate="$2" executor_decision="$3" verify_dir="$4" out="$5"
  cat >"$out" <<EOF
You are a fresh, adversarial, read-only-in-intent verifier for Phase $PHASE in
Flik's Hard-Truth Ratchet, iteration $iteration. You did not implement this candidate.
The detached verification worktree is $verify_dir at commit $candidate.

Read completely before testing:
- $verify_dir/AGENTS.md
- $RUN_DIR/acceptance-contract.md
- the Obsidian roadmap hub and linked Phase $PHASE execution note
- $executor_decision (executor claim; evidence to challenge, never authority)

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
For Phase 4, independently validate the central capsule index and its exact pinned
offline reader, regenerate analysis/phase4_offline_opportunity_queue.json, and require
exactly 107 unique current registry rows with current capsule/fixture
hashes, priorities, dependencies, batch queries, no trusted high-level complete fields,
and exactly one derived classification per row from offline_ready, offline_partial,
live_required, or no_capsule. Falsify its freshness and coverage guards by
perturbing a disposable input: omitted/duplicate rows, source-hash drift, or corrupted
capsule metadata must turn the check red. Re-run a representative sample of the exact
pinned offline commands and confirm the claimed cross-movie deltas and assertions.
Reject token offline preflights: accepted progress must analyze a subsystem-sized batch
(one coherent campaign cluster or normally at least three highest-value offline-ready
rows) and retain material generated evidence/guards, not merely print a summary.

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
  local verify_dir="$RUN_DIR/verifier-worktree-$slug"
  local verifier_prompt="$RUN_DIR/${slug}-verifier.prompt.md"
  local verifier_decision="$RUN_DIR/${slug}-verifier.decision.json"
  local verifier_log="$RUN_DIR/${slug}-verifier.log"
  local verifier_error="${verifier_decision%.json}.validation-error.txt"
  local verifier_rc=0 verifier_head verifier_tree_status verifier_integrity

  git -C "$REPO" worktree add --detach "$verify_dir" "$candidate"
  make_verifier_prompt "$label" "$candidate" "$claim" \
    "$verify_dir" "$verifier_prompt"
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
  $SCRIPT_PATH --phase $PHASE --contract $CONTRACT --seed-ref $BRANCH
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

if [[ -n "$VERIFY_FIRST_CLAIM_SNAPSHOT" ]]; then
  recovery_candidate="$(git -C "$WORKTREE" rev-parse HEAD)"
  note "running recovery verifier before any new implementation iteration"
  if run_fresh_verifier "RECOVERY" "recovery" "$recovery_candidate" \
      "$VERIFY_FIRST_CLAIM_SNAPSHOT"; then
    if [[ "$VERIFIER_STATUS" == "closed" ]]; then
      finish_closed "$recovery_candidate" "$VERIFIER_DECISION" \
        "recovered closure claim and fresh verifier agree"
      exit 0
    fi
    write_feedback "verify_first_recovery" "$VERIFIER_DECISION"
    note "recovery verifier did not close Phase $PHASE; feeding its findings to executor 1"
  fi
fi

for ((iteration = 1; iteration <= MAX_ITERATIONS; iteration++)); do
  if stop_requested_at_boundary "$iteration"; then
    exit 0
  fi
  executor_prompt="$RUN_DIR/iteration-${iteration}-executor.prompt.md"
  executor_decision="$RUN_DIR/iteration-${iteration}-executor.decision.json"
  executor_log="$RUN_DIR/iteration-${iteration}-executor.log"
  make_executor_prompt "$iteration" "$executor_prompt"

  executor_rc=0
  run_codex "EXECUTOR $iteration" "$WORKTREE" "$executor_prompt" \
    "$executor_decision" "$executor_log" || executor_rc=$?
  if ((executor_rc != 0)); then
    actual_commit="$(git -C "$WORKTREE" rev-parse HEAD)"
    write_agent_error_feedback "executor_error_iteration_$iteration" \
      "$executor_decision" "${executor_decision%.json}.validation-error.txt" \
      "$actual_commit"
    note "iteration $iteration executor output rejected; continuing with preserved feedback"
    continue
  fi

  executor_status="$(json_field "$executor_decision" status)"
  executor_commit="$(json_field "$executor_decision" candidate_commit)"
  actual_commit="$(git -C "$WORKTREE" rev-parse HEAD)"
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
    continue
  fi

  if [[ "$executor_status" == "open_autonomous" ]]; then
    write_feedback "executor_iteration_$iteration" "$executor_decision"
    note "iteration $iteration remains autonomously open; starting a fresh executor"
    continue
  fi

  if ! worktree_clean "$WORKTREE"; then
    git -C "$WORKTREE" status --short >"$RUN_DIR/iteration-${iteration}-dirty-status.txt"
    cat >"$FEEDBACK" <<EOF
{
  "source": "ratchet_integrity_check",
  "status": "open_autonomous",
  "summary": "Closed/blocked claim rejected because the implementation worktree is dirty.",
  "gaps": ["Bank all scoped non-copyrighted work and remove transient untracked dependencies, then revalidate from committed HEAD."],
  "required_input": "",
  "evidence": ["$RUN_DIR/iteration-${iteration}-dirty-status.txt"],
  "validation": ["git status --porcelain=v1 --untracked-files=all: non-empty"],
  "candidate_commit": "$actual_commit"
}
EOF
    note "iteration $iteration rejected: worktree is dirty"
    continue
  fi

  if ! run_fresh_verifier "$iteration" "iteration-$iteration" "$actual_commit" \
      "$executor_decision"; then
    continue
  fi

  if [[ "$executor_status" == "closed" && "$VERIFIER_STATUS" == "closed" ]]; then
    finish_closed "$actual_commit" "$VERIFIER_DECISION"
    exit 0
  fi

  if [[ "$executor_status" == "blocked_external" && \
        "$VERIFIER_STATUS" == "blocked_external" ]]; then
    finish_blocked "$actual_commit" "$VERIFIER_DECISION"
    exit 2
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
