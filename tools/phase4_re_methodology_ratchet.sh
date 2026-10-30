#!/usr/bin/env bash
# Phase 4 RE Methodology Advisory Ratchet
#
# A two-agent decision loop:
#   1. an Implementer Advisory proposes the most efficient evidence-backed method;
#   2. a fresh hard-truth verifier independently accepts or rejects it.
#
# The controller never edits the operator checkout. It writes only an isolated
# worktree/branch and never merges automatically.

set -Eeuo pipefail

SCRIPT_NAME="Phase 4 RE Methodology Ratchet"
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

usage() {
  cat <<'EOF'
Phase 4 RE Methodology Ratchet — advisory / hard-truth decision loop

Usage:
  tools/phase4_re_methodology_ratchet.sh [options]

Options:
  --seed-ref REF       Commit/branch to audit (default: HEAD)
  --repo DIR           ABL operator repository (default: containing repository)
  --contract FILE      Methodology acceptance contract
                       (default: engineering-specs/phase4-re-methodology-ratchet.md)
  --model MODEL        Codex model override (default: Codex configuration)
  --max-rounds N       Maximum advisory/verifier rounds (default: 6)
  --run-root DIR       Durable state root
                       (default: ~/.local/state/phase4-re-methodology-ratchet)
  --sandbox MODE       Codex sandbox (default: danger-full-access)
  --here               Run controller in this terminal
  --dry-run            Validate inputs without creating a worktree or agent
  -h, --help           Show this help

The default invocation starts a detached controller and opens a GNOME Terminal that
follows its durable log. Closing the viewer does not stop the controller.

Final output is an isolated branch containing:
  ObsidianVault/Playbooks/Game Solving Roadmap/
    Phase 4 - Reverse Engineering Operating Method.md

No merge is performed.
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

if ! contains_arg "--internal-run" "$@" && ! contains_arg "--here" "$@"; then
  command -v gnome-terminal >/dev/null 2>&1 ||
    die "gnome-terminal is unavailable; rerun with --here"
  command -v setsid >/dev/null 2>&1 || die "setsid is unavailable"
  command -v nohup >/dev/null 2>&1 || die "nohup is unavailable"
  child=("$SCRIPT_PATH" --internal-run "$@")
  launcher_root="${XDG_STATE_HOME:-$HOME/.local/state}/phase4-re-methodology-ratchet/launchers"
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
  viewer_cmd="tail --pid=$controller_pid -n +1 -F $quoted_log; printf '\\n%s\\n' 'Methodology ratchet finished. Press Enter to close this viewer.'; read -r _"
  if ! gnome-terminal --title="$SCRIPT_NAME" -- bash -lc "$viewer_cmd"; then
    note "viewer failed to open; detached controller continues"
  fi
  note "launched detached controller pid $controller_pid"
  note "viewer log: $launcher_log"
  exit 0
fi

SEED_REF="HEAD"
REPO=""
CONTRACT=""
MODEL=""
MAX_ROUNDS=6
RUN_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/phase4-re-methodology-ratchet"
SANDBOX="danger-full-access"
DRY_RUN=0

while (($#)); do
  case "$1" in
    --seed-ref) SEED_REF="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --contract) CONTRACT="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --max-rounds) MAX_ROUNDS="$2"; shift 2 ;;
    --run-root) RUN_ROOT="$2"; shift 2 ;;
    --sandbox) SANDBOX="$2"; shift 2 ;;
    --here|--internal-run) shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) die "unknown option: $1" ;;
  esac
done

[[ "$MAX_ROUNDS" =~ ^[1-9][0-9]*$ ]] || die "max rounds must be positive"
case "$SANDBOX" in
  read-only|workspace-write|danger-full-access) ;;
  *) die "invalid Codex sandbox: $SANDBOX" ;;
esac

command -v git >/dev/null || die "git is not installed"
command -v codex >/dev/null || die "codex is not installed"
command -v python3 >/dev/null || die "python3 is not installed"

if [[ -z "$REPO" ]]; then
  REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
fi
REPO="$(readlink -f "$REPO")"
git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
  die "not a Git worktree: $REPO"
git -C "$REPO" rev-parse --verify "${SEED_REF}^{commit}" >/dev/null 2>&1 ||
  die "seed ref does not resolve: $SEED_REF"

if [[ -z "$CONTRACT" ]]; then
  CONTRACT="$REPO/engineering-specs/phase4-re-methodology-ratchet.md"
elif [[ "$CONTRACT" != /* ]]; then
  CONTRACT="$REPO/$CONTRACT"
fi
CONTRACT="$(readlink -f "$CONTRACT")"
[[ -f "$CONTRACT" ]] || die "contract not found: $CONTRACT"
BANKER="$REPO/tools/phase4_re_methodology_bank.py"
[[ -f "$BANKER" ]] || die "banking helper not found: $BANKER"

HUB_REL="ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md"
PHASE4_REL="ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Solve Every Gameplay and Engine Subsystem.md"
METHOD_REL="ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Reverse Engineering Operating Method.md"
for required in AGENTS.md "$HUB_REL" "$PHASE4_REL"; do
  [[ -f "$REPO/$required" ]] || die "required authority missing: $required"
done

CODEX_VERSION="$(codex --version)"
CODEX_AUTH="$(codex login status 2>&1 || true)"
[[ "$CODEX_AUTH" == *"Logged in"* ]] || die "Codex is not authenticated: $CODEX_AUTH"

note "repository: $REPO"
note "seed: $SEED_REF ($(git -C "$REPO" rev-parse "${SEED_REF}^{commit}"))"
note "contract: $CONTRACT"
note "Codex: $CODEX_VERSION"
note "sandbox: $SANDBOX"
if [[ -n "$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)" ]]; then
  note "operator checkout is dirty; it is read/snapshot only and will not be edited"
fi
if ((DRY_RUN)); then
  note "dry run passed; no worktree or agent created"
  exit 0
fi

mkdir -p "$RUN_ROOT"
RUN_ID="phase4-method-$(date +%Y%m%d-%H%M%S)-$$"
RUN_DIR="$RUN_ROOT/runs/$RUN_ID"
WORKTREE="$RUN_ROOT/worktrees/$RUN_ID"
BRANCH="ratchet/phase4-methodology-${RUN_ID#phase4-method-}"
mkdir -p "$RUN_DIR" "$(dirname "$WORKTREE")"

cp -- "$CONTRACT" "$RUN_DIR/acceptance-contract.md"
cp -- "$REPO/AGENTS.md" "$RUN_DIR/AGENTS.snapshot.md"
cp -- "$REPO/$HUB_REL" "$RUN_DIR/roadmap-hub.snapshot.md"
cp -- "$REPO/$PHASE4_REL" "$RUN_DIR/phase4-roadmap.snapshot.md"
cp -- "$SCRIPT_PATH" "$RUN_DIR/controller.snapshot.sh"
cp -- "$BANKER" "$RUN_DIR/banker.snapshot.py"
git -C "$REPO" status --short >"$RUN_DIR/operator-status-at-start.txt"
{
  printf 'operator_head=%s\n' "$(git -C "$REPO" rev-parse HEAD)"
  printf 'seed_ref=%s\n' "$SEED_REF"
  printf 'seed_commit=%s\n' "$(git -C "$REPO" rev-parse "${SEED_REF}^{commit}")"
  printf 'duckstation_head=%s\n' "$(git -C "$HOME/duckstation" rev-parse HEAD 2>/dev/null || printf unavailable)"
  printf 'duckstation_status:\n'
  git -C "$HOME/duckstation" status --short 2>/dev/null || true
} >"$RUN_DIR/source-state.txt"

duck_files=(
  "$HOME/duckstation/docs/external-debugger.md"
  "$HOME/duckstation/docs/external-debugger-determinism.md"
  "$HOME/duckstation/docs/external-debugger-experiment-runner.md"
  "$HOME/duckstation/docs/external-debugger-movie.md"
  "$HOME/duckstation/docs/external-debugger-scenarios.md"
  "$HOME/duckstation/docs/external-debugger-trace-capsules.md"
  "$HOME/duckstation/src/duckstation-qt/debuggerrpc.cpp"
  "$HOME/duckstation/src/core/debugger_control_service.cpp"
  "$HOME/duckstation/src/core/dma.cpp"
  "$HOME/duckstation/build-release/bin/duckstation-qt"
)
: >"$RUN_DIR/duckstation-surface.sha256"
for path in "${duck_files[@]}"; do
  if [[ -f "$path" ]]; then
    sha256sum "$path" >>"$RUN_DIR/duckstation-surface.sha256"
  else
    printf 'MISSING  %s\n' "$path" >>"$RUN_DIR/duckstation-surface.sha256"
  fi
done

sha256sum \
  "$RUN_DIR/acceptance-contract.md" \
  "$RUN_DIR/AGENTS.snapshot.md" \
  "$RUN_DIR/roadmap-hub.snapshot.md" \
  "$RUN_DIR/phase4-roadmap.snapshot.md" \
  "$RUN_DIR/controller.snapshot.sh" \
  "$RUN_DIR/banker.snapshot.py" \
  >"$RUN_DIR/run-inputs.sha256"

cat >"$RUN_DIR/advisory.schema.json" <<'JSON'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "role": {"type": "string", "enum": ["implementer_advisory"]},
    "status": {
      "type": "string",
      "enum": ["ready_for_truth", "blocked_external"]
    },
    "summary": {"type": "string"},
    "methodology_claims": {"type": "array", "items": {"type": "string"}},
    "uncertainties": {"type": "array", "items": {"type": "string"}},
    "evidence": {"type": "array", "items": {"type": "string"}},
    "validation": {"type": "array", "items": {"type": "string"}},
    "required_input": {"type": "string"},
    "candidate_commit": {"type": "string"},
    "note_path": {"type": "string"}
  },
  "required": ["role", "status", "summary", "methodology_claims", "uncertainties",
               "evidence", "validation", "required_input", "candidate_commit",
               "note_path"]
}
JSON

cat >"$RUN_DIR/verifier.schema.json" <<'JSON'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "role": {"type": "string", "enum": ["hard_truth_verifier"]},
    "status": {
      "type": "string",
      "enum": ["accepted", "rejected", "blocked_external"]
    },
    "summary": {"type": "string"},
    "gaps": {"type": "array", "items": {"type": "string"}},
    "evidence": {"type": "array", "items": {"type": "string"}},
    "validation": {"type": "array", "items": {"type": "string"}},
    "required_input": {"type": "string"},
    "reviewed_commit": {"type": "string"},
    "note_path": {"type": "string"}
  },
  "required": ["role", "status", "summary", "gaps", "evidence", "validation",
               "required_input", "reviewed_commit", "note_path"]
}
JSON

git -C "$REPO" worktree add -b "$BRANCH" "$WORKTREE" "$SEED_REF"

cat >"$RUN_DIR/run.json" <<EOF
{
  "name": "$SCRIPT_NAME",
  "run_id": "$RUN_ID",
  "operator_repo": "$REPO",
  "worktree": "$WORKTREE",
  "branch": "$BRANCH",
  "seed_ref": "$SEED_REF",
  "seed_commit": "$(git -C "$WORKTREE" rev-parse HEAD)",
  "method_note": "$METHOD_REL",
  "started": "$(date --iso-8601=seconds)"
}
EOF

FEEDBACK="$RUN_DIR/feedback.json"
cat >"$FEEDBACK" <<'EOF'
{
  "source": "initial",
  "summary": "No prior verifier decision. Derive the methodology from current evidence.",
  "gaps": []
}
EOF

codex_base=(codex exec --ephemeral --color always -s "$SANDBOX")
if [[ -n "$MODEL" ]]; then
  codex_base+=(-m "$MODEL")
fi

json_field() {
  python3 - "$1" "$2" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]]
print(json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value)
PY
}

run_codex() {
  local role="$1" cwd="$2" prompt="$3" schema="$4" decision="$5" log="$6"
  printf '\n============================================================\n'
  printf '%s — %s\n' "$SCRIPT_NAME" "$role"
  printf '============================================================\n'
  cat "$prompt"
  printf '\n-------------------- Codex live output ---------------------\n'
  set +e
  "${codex_base[@]}" -C "$cwd" --output-schema "$schema" \
    --output-last-message "$decision" - <"$prompt" 2>&1 | tee "$log"
  local rc=${PIPESTATUS[0]}
  set -e
  return "$rc"
}

validate_advisory() {
  python3 - "$1" "$2" "$METHOD_REL" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
if doc["role"] != "implementer_advisory":
    raise SystemExit("wrong advisory role")
if doc["candidate_commit"] != sys.argv[2]:
    raise SystemExit("advisory commit mismatch")
if doc["note_path"] != sys.argv[3]:
    raise SystemExit("advisory note path mismatch")
if doc["status"] == "ready_for_truth" and doc["required_input"].strip():
    raise SystemExit("ready advisory cannot require external input")
if doc["status"] == "blocked_external" and not doc["required_input"].strip():
    raise SystemExit("blocked advisory requires exact input")
PY
}

validate_verdict() {
  python3 - "$1" "$2" "$METHOD_REL" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
if doc["role"] != "hard_truth_verifier":
    raise SystemExit("wrong verifier role")
if doc["reviewed_commit"] != sys.argv[2]:
    raise SystemExit("reviewed commit mismatch")
if doc["note_path"] != sys.argv[3]:
    raise SystemExit("verifier note path mismatch")
if doc["status"] == "accepted" and (doc["gaps"] or doc["required_input"].strip()):
    raise SystemExit("accepted cannot carry gaps or required_input")
if doc["status"] == "rejected" and not doc["gaps"]:
    raise SystemExit("rejected requires exact gaps")
if doc["status"] == "blocked_external" and not doc["required_input"].strip():
    raise SystemExit("blocked_external requires exact required_input")
PY
}

allowed_advisory_diff() {
  local before="$1" after="$2"
  local changed
  changed="$(git -C "$WORKTREE" diff --name-only "$before..$after")"
  [[ -n "$changed" ]] || return 1
  while IFS= read -r path; do
    [[ "$path" == "$METHOD_REL" || "$path" == "$PHASE4_REL" ]] || return 1
  done <<<"$changed"
}

make_advisory_prompt() {
  local round="$1" out="$2"
  cat >"$out" <<EOF
You are Step 1, the Implementer Advisory, round $round of a Phase 4 methodology
ratchet. Your task is to deduce the best-supported efficient way to reverse-engineer
the game through Phase 4. You are not implementing Phase 4 and may not close rows.

Read completely:
- $WORKTREE/AGENTS.md
- $RUN_DIR/acceptance-contract.md
- $RUN_DIR/roadmap-hub.snapshot.md
- $RUN_DIR/phase4-roadmap.snapshot.md
- $WORKTREE/$HUB_REL
- $WORKTREE/$PHASE4_REL
- $FEEDBACK
- $RUN_DIR/source-state.txt
- $RUN_DIR/duckstation-surface.sha256

Then inspect the actual current repository evidence on this branch and the retained
run history under ${XDG_STATE_HOME:-$HOME/.local/state}/flik-hard-truth-ratchet.
Audit representative relevant src_re C, ASM/symbols, typed schemas, registries,
generators, tests, fixture manifests, Phase 4 queues/campaigns, and Obsidian
Canon/Experiments. Inspect the current DuckStation API documentation and C++ source
under $HOME/duckstation; cite real methods and limitations rather than memory.

Measure the workflow's observed bottlenecks from retained decisions/logs and compare
at least the three alternatives required by the contract. Build a falsifiable operating
method that tells future agents exactly when to use static C/ASM work, retained
capsules/offline mathematics, a targeted isolated DuckStation API experiment, a cold
boot/movie proof, and a fresh verifier. It must explain how a result becomes durable
machine knowledge and linked Obsidian knowledge, how work is checkpointed, how
concurrent branches are integrated, and how efficiency is measured and reassessed.

Do not launch DuckStation or replay movies for this methodology audit: retained
evidence, API/source inspection, and static/offline checks are sufficient. Do not edit
Phase 4 implementation, evidence, C/ASM, tests, queues, scorecards, gates, or statuses.
Your only allowed edits are:
- $METHOD_REL
- $PHASE4_REL, solely for a reciprocal link to the method note.

Write or revise the method note with status: candidate and
methodology_ratchet: pending, all required sections, and exactly the verdict marker
block from the contract. Do not claim the method is verified. Add/maintain the
reciprocal Phase 4 link without rewriting roadmap requirements. Run appropriate
read-only/freshness/vault checks. Commit only the two allowed files and leave the
worktree clean.

Return only the advisory JSON. status=ready_for_truth when the candidate is ready for
independent attack. candidate_commit must equal tested HEAD and note_path must be
$METHOD_REL. If an exact external human decision truly prevents even a candidate
method, use blocked_external; ordinary uncertainty belongs in the note and
uncertainties array.
EOF
}

make_verifier_prompt() {
  local round="$1" candidate="$2" claim="$3" verify_dir="$4" out="$5"
  cat >"$out" <<EOF
You are Step 2, a very hard-ass independent truther, round $round. You did not write
the candidate. The detached clean checkout is $verify_dir at $candidate.

Read completely:
- $verify_dir/AGENTS.md
- $RUN_DIR/acceptance-contract.md
- $RUN_DIR/roadmap-hub.snapshot.md
- $RUN_DIR/phase4-roadmap.snapshot.md
- $verify_dir/$HUB_REL
- $verify_dir/$PHASE4_REL
- $verify_dir/$METHOD_REL
- $claim
- $RUN_DIR/source-state.txt
- $RUN_DIR/duckstation-surface.sha256

Independently inspect the current Phase 4 machine evidence, representative src_re C
and ASM/symbol/schema layers, tests, fixture/capsule manifests, campaign/queue logic,
Obsidian evidence, Git history, and retained ratchet logs. Inspect the actual current
DuckStation documentation and relevant C++ implementations under $HOME/duckstation.
Do not accept invented API capabilities or generic advice.

Try to falsify the proposed bottleneck diagnosis, lane-selection rules, batching,
evidence promotion, clean-checkout durability, concurrency/outage recovery, and
efficiency metrics. Compare it against credible alternatives. Acceptance means it is
the best-supported efficient operating method under current evidence—not merely
plausible, tidy, or consistent with the advisor. Apply every rejection condition in
the contract. Require that the method makes technically meaningful architectural RE
the unit of progress and cannot confuse replay churn, documentation churn, or green
summary counts with solved subsystem semantics.

Do not launch DuckStation or replay movies unless you first prove a specific
methodology claim cannot be checked from source, retained artifacts, or offline data;
this audit should normally remain static/read-only. Do not edit or commit anything.
Generated temporary outputs must not leave the verifier checkout dirty.

Return accepted only with gaps=[] and required_input empty after direct inspection and
falsification attempts. Return rejected with exact reproducible gaps for the next
advisor. Return blocked_external only for a precise human-owned input that prevents the
methodology decision itself. reviewed_commit must be $candidate and note_path must be
$METHOD_REL. Return only the verifier JSON.
EOF
}

write_feedback() {
  python3 - "$1" "$FEEDBACK" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
out = {
    "source": "hard_truth_verifier",
    "summary": doc["summary"],
    "gaps": doc["gaps"],
    "evidence": doc["evidence"],
    "validation": doc["validation"],
    "required_input": doc["required_input"],
    "reviewed_commit": doc["reviewed_commit"],
}
with open(sys.argv[2], "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
}

note "run ID: $RUN_ID"
note "branch: $BRANCH"
note "worktree: $WORKTREE"
note "logs/state: $RUN_DIR"
note "the ratchet may change only the methodology note and its Phase 4 link"

for ((round = 1; round <= MAX_ROUNDS; round++)); do
  advisory_prompt="$RUN_DIR/round-${round}-advisory.prompt.md"
  advisory_decision="$RUN_DIR/round-${round}-advisory.decision.json"
  advisory_log="$RUN_DIR/round-${round}-advisory.log"
  before="$(git -C "$WORKTREE" rev-parse HEAD)"
  make_advisory_prompt "$round" "$advisory_prompt"
  if ! run_codex "STEP 1 IMPLEMENTER ADVISORY $round" "$WORKTREE" \
      "$advisory_prompt" "$RUN_DIR/advisory.schema.json" \
      "$advisory_decision" "$advisory_log"; then
    die "advisory process failed structurally; retained log: $advisory_log"
  fi
  candidate="$(git -C "$WORKTREE" rev-parse HEAD)"
  if ! validate_advisory "$advisory_decision" "$candidate"; then
    note "advisory decision failed structural validation"
    continue
  fi
  if [[ "$(json_field "$advisory_decision" status)" == "blocked_external" ]]; then
    cp -- "$advisory_decision" "$RUN_DIR/HUMAN_INPUT_REQUIRED.json"
    die "advisor reported external blockage before verification"
  fi
  if [[ -n "$(git -C "$WORKTREE" status --porcelain=v1 --untracked-files=all)" ]]; then
    git -C "$WORKTREE" status --short >"$RUN_DIR/round-${round}-advisory-dirty.txt"
    note "advisory rejected: worktree is dirty"
    continue
  fi
  if ! allowed_advisory_diff "$before" "$candidate"; then
    git -C "$WORKTREE" diff --name-only "$before..$candidate" \
      >"$RUN_DIR/round-${round}-scope-violation.txt"
    note "advisory rejected: commit crossed methodology write boundary"
    continue
  fi

  verify_dir="$RUN_DIR/verifier-worktree-round-$round"
  verifier_prompt="$RUN_DIR/round-${round}-verifier.prompt.md"
  verifier_decision="$RUN_DIR/round-${round}-verifier.decision.json"
  verifier_log="$RUN_DIR/round-${round}-verifier.log"
  git -C "$REPO" worktree add --detach "$verify_dir" "$candidate"
  make_verifier_prompt "$round" "$candidate" "$advisory_decision" \
    "$verify_dir" "$verifier_prompt"
  verifier_rc=0
  run_codex "STEP 2 HARD-TRUTH VERIFIER $round" "$verify_dir" \
    "$verifier_prompt" "$RUN_DIR/verifier.schema.json" \
    "$verifier_decision" "$verifier_log" || verifier_rc=$?
  verifier_head="$(git -C "$verify_dir" rev-parse HEAD)"
  verifier_status_tree="$(git -C "$verify_dir" status --porcelain=v1 --untracked-files=all)"
  git -C "$REPO" worktree remove --force "$verify_dir" || true

  if ((verifier_rc != 0)); then
    die "verifier process failed structurally; retained log: $verifier_log"
  fi
  if [[ "$verifier_head" != "$candidate" || -n "$verifier_status_tree" ]]; then
    note "verifier independence failed: it changed its checkout"
    cat >"$FEEDBACK" <<EOF
{"source":"verifier_integrity","summary":"Verifier changed its detached checkout.","gaps":["Reproduce the audit without verifier source edits or generated checkout drift."],"evidence":[]}
EOF
    continue
  fi
  if ! validate_verdict "$verifier_decision" "$candidate"; then
    note "verifier decision failed structural validation"
    continue
  fi

  verdict_status="$(json_field "$verifier_decision" status)"
  if [[ "$verdict_status" == "rejected" ]]; then
    write_feedback "$verifier_decision"
    note "hard-truth verifier rejected round $round; exact gaps feed round $((round + 1))"
    continue
  fi
  if [[ "$verdict_status" == "blocked_external" ]]; then
    cp -- "$verifier_decision" "$RUN_DIR/HUMAN_INPUT_REQUIRED.json"
    die "hard-truth verifier confirmed an external methodology blocker"
  fi

  python3 "$RUN_DIR/banker.snapshot.py" \
    --note "$WORKTREE/$METHOD_REL" \
    --verdict "$verifier_decision" \
    --run-id "$RUN_ID" \
    --verified-at "$(date --iso-8601=seconds)"
  bank_changed="$(git -C "$WORKTREE" diff --name-only)"
  [[ "$bank_changed" == "$METHOD_REL" ]] ||
    die "banking step changed files outside the methodology note: $bank_changed"
  vault_log="$RUN_DIR/final-vault-validation.log"
  python3 "$WORKTREE/tools/validate_vault.py" --check >"$vault_log" 2>&1 ||
    die "vault validation failed after banking; inspect $vault_log"
  git -C "$WORKTREE" add -- "$METHOD_REL"
  git -C "$WORKTREE" commit -m "docs(phase4): bank verified RE operating method"
  final_commit="$(git -C "$WORKTREE" rev-parse HEAD)"
  [[ -z "$(git -C "$WORKTREE" status --porcelain=v1 --untracked-files=all)" ]] ||
    die "final methodology worktree is dirty"

  cat >"$RUN_DIR/RESULT.md" <<EOF
# Phase 4 RE methodology accepted

- Run: \`$RUN_ID\`
- Reviewed candidate: \`$candidate\`
- Final banked commit: \`$final_commit\`
- Branch: \`$BRANCH\`
- Worktree: \`$WORKTREE\`
- Obsidian note: \`$METHOD_REL\`
- Verifier decision: \`$verifier_decision\`
- Vault validation: \`$vault_log\`

The branch was not merged. This accepts the operating method only; Phase 4 remains
governed by its own roadmap exit gate.
EOF
  printf '\n************************************************************\n'
  printf 'PHASE 4 RE OPERATING METHOD ACCEPTED\n'
  printf 'Final commit: %s\nBranch: %s\nWorktree: %s\n' \
    "$final_commit" "$BRANCH" "$WORKTREE"
  printf 'Result: %s\n' "$RUN_DIR/RESULT.md"
  printf 'No merge was performed.\n'
  printf '************************************************************\n'
  exit 0
done

cat >"$RUN_DIR/ROUND_LIMIT.md" <<EOF
# Phase 4 methodology ratchet remains open

The ratchet reached $MAX_ROUNDS advisory/verifier rounds without independent
acceptance.

- Branch: \`$BRANCH\`
- Worktree: \`$WORKTREE\`
- Last feedback: \`$FEEDBACK\`

No final methodology was banked or merged.
EOF
die "round limit reached without hard-truth acceptance; see $RUN_DIR"
