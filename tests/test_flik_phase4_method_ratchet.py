from pathlib import Path
import subprocess

from tools import phase4_trial_boundary


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "flik_phase4_method_ratchet.sh"
REPORTER = ROOT / "tools" / "phase4_method_reports.py"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_controller_is_phase4_only_and_snapshots_the_accepted_method():
    source = _source()
    assert 'PHASE=4' in source
    assert '[[ "$PHASE" == "4" ]]' in source
    assert '"phase": {"type": "integer", "const": 4}' in source
    assert "Phase 4 - Reverse Engineering Operating Method.md" in source
    assert 'operating-method.sha256' in source
    assert "phase4_method_metrics.py --self-check" in source
    boundary = source[
        source.index('"boundary_mismatch"'):
        source.index('"evidence":', source.index('"boundary_mismatch"'))
    ]
    assert '"additionalProperties": false' in boundary
    assert '"PRECISE_WINDOW_UNAVOIDABLE"' in boundary


def test_contract_and_agents_snapshots_come_from_the_seed_not_dirty_operator_tree():
    source = _source()
    assert 'CONTRACT_DISPLAY="${SEED_REF}:${CONTRACT_REL}"' in source
    assert 'cat-file -e "${SEED_REF}:${CONTRACT_REL}"' in source
    assert 'show "${SEED_REF}:${CONTRACT_REL}"' in source
    assert 'show "${SEED_REF}:AGENTS.md"' in source
    assert 'cp -- "$REPO/AGENTS.md"' not in source
    assert 'CONTRACT="$RUN_DIR/acceptance-contract.md"' in source


def test_trial_boundary_reseeds_only_for_control_plane_changes():
    assert phase4_trial_boundary.critical_path(
        "tools/phase4_method_metrics.py")
    assert phase4_trial_boundary.critical_path(
        "tools/phase4_seed_validation.py")
    assert phase4_trial_boundary.critical_path(
        "tools/flik_phase4_method_ratchet.sh")
    assert phase4_trial_boundary.critical_path(
        "tools/phase4_movie_priority.py")
    assert phase4_trial_boundary.critical_path(
        "config/phase4_movie_priority.yaml")
    assert phase4_trial_boundary.critical_path(
        "tools/ratchet_reseed_guard.py")
    assert phase4_trial_boundary.critical_path(
        "engineering-specs/phase4-closure.md")
    assert phase4_trial_boundary.critical_path(
        "ObsidianVault/Playbooks/Game Solving Roadmap/"
        "Phase 4 - Reverse Engineering Operating Method.md")
    assert not phase4_trial_boundary.critical_path(
        "tools/phase4_live_escalations.py")
    assert not phase4_trial_boundary.critical_path(
        "analysis/phase4_campaign_inventory.json")
    assert not phase4_trial_boundary.critical_path(
        "analysis/phase4_movie_priority_queue.json")


def test_trial_boundary_compares_committed_blobs(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Ratchet Test"],
        check=True,
    )
    (repo / "tools").mkdir()
    critical = repo / "tools" / "phase4_method_metrics.py"
    ordinary = repo / "tools" / "phase4_kick.py"
    critical.write_text("VERSION = 1\n", encoding="utf-8")
    ordinary.write_text("VERSION = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "base"], check=True)
    base = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    critical.write_text("VERSION = 2\n", encoding="utf-8")
    ordinary.write_text("VERSION = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-qm", "candidate"], check=True)
    candidate = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

    doc = phase4_trial_boundary.build(repo, base, candidate)

    assert doc["complete"]
    assert doc["reseed_required"]
    assert doc["trial_critical_paths"] == [
        "tools/phase4_method_metrics.py"]
    assert doc["critical_identities"][
        "tools/phase4_method_metrics.py"]["base_sha256"]
    assert doc["critical_identities"][
        "tools/phase4_method_metrics.py"]["candidate_sha256"]


def test_trial_cannot_begin_without_v2_validator():
    source = _source()
    worktree_add = source.index('git -C "$REPO" worktree add -b')
    preflight = source.rindex("\nrepair_seed_before_trial\n")
    initialize = source.rindex(
        '\ninitialize_method_trial "$INITIAL_SELECTION_PACKET"\n')
    loop = source.index("for ((iteration = 1;")
    assert worktree_add < preflight < initialize < loop
    seed_guard = source[
        source.index("phase4_seed_preflight()"):
        source.index("make_seed_repair_prompt()")
    ]
    assert "phase4_method_metrics.py --self-check" in seed_guard
    assert "phase4_method_legacy_live_index.py --check" in seed_guard
    assert "tests/test_phase4_gate.py" in seed_guard
    assert 'if not phase3["met"]' in seed_guard
    assert seed_guard.count("|| exit $?") >= 8
    assert "provision_clean_checkout_inputs.py" in source[worktree_add:preflight]


def test_stale_seed_is_repaired_and_freshly_verified_before_trial_root():
    source = _source()
    repair = source[
        source.index("repair_seed_before_trial()"):
        source.index("initialize_method_trial()")
    ]
    assert "SEED REPAIR EXECUTOR" in repair
    assert "SEED REPAIR VERIFIER" in repair
    assert "for attempt in 1 2 3" in repair
    assert 'worktree add --detach "$verify_dir" "$actual"' in repair
    provision = repair.index(
        'python3 "$verify_dir/tools/provision_clean_checkout_inputs.py"'
    )
    verifier_preflight = repair.index(
        '"$RUN_DIR/seed-repair-${attempt}-verifier-preflight.log"'
    )
    assert provision < verifier_preflight
    assert '"$verify_dir" "$verifier_prompt"' in repair
    assert 'worktree remove --force "$verify_dir"' in repair
    assert "phase4_seed_repair_scope.py" in repair
    assert "--debt-before" in repair and "--debt-after" in repair
    assert "phase4_seed_verifier.py" in repair
    assert "phase4_seed_validation.py" in repair
    assert "phase4_seed_falsifiers.py" in source
    assert "Content-free scripts" in source
    assert '[[ "$(json_field "$verifier_decision" gaps)" != "[]" ]]' in repair
    assert "methodology trial not started" in repair


def test_every_executor_gets_the_method_funnel_and_receipt_contract():
    source = _source()
    start = source.index("make_executor_prompt()")
    end = source.index("make_verifier_prompt()", start)
    prompt = " ".join(source[start:end].split())
    for fragment in (
        "one exact claim",
        "one explicit falsifier",
        "OFFLINE",
        "STATIC",
        "LIVE",
        "BANK",
        "abl-phase4-offline-query/1",
        "abl-phase4-live-run-receipt/2",
        "free-form windows",
        "operating-method.md",
    ):
        assert fragment in prompt
    assert prompt.index("OFFLINE") < prompt.index("STATIC") < \
        prompt.index("LIVE") < prompt.index("BANK")


def test_controller_retains_all_normative_manifest_evidence():
    source = _source()
    start = source.index("write_method_manifest()")
    end = source.index("initialize_method_trial()", start)
    writer = source[start:end]
    required = (
        "debt_before", "debt_after", "progress_receipt",
        "offline_query_receipts", "live_run_receipts",
        "escalation_ledger_before", "escalation_ledger_after",
        "verifier_decision", "controller_events", "command_log",
        "validation_report", "knowledge_report", "vault_report",
        "clean_checkout_report",
    )
    for name in required:
        assert f'"{name}"' in writer
    assert '"schema": "abl-phase4-method-metrics/2"' in writer
    assert "reporter_sha256" in source


def test_fixed_reports_and_metrics_fail_closed_before_next_iteration():
    source = _source()
    finalizer = source[
        source.index("finalize_method_iteration()"):
        source.index("write_phase4_stagnation_feedback()")
    ]
    assert "capture_method_reports" in finalizer
    assert "--run-dir" in finalizer and "--check" in finalizer
    assert "METHOD_METRICS_FAILURE.txt" in finalizer
    loop = source[source.index("for ((iteration = 1;"):]
    assert '"METHOD_EVIDENCE_REPAIR"' in loop
    assert loop.count(
        '"METHOD_EVIDENCE_REPAIR" "$RUN_DIR/METHOD_METRICS_FAILURE.txt"'
    ) == 5
    reporter = REPORTER.read_text(encoding="utf-8")
    assert '"tests/test_phase4_gate.py"' in reporter


def test_controller_automatically_reseeds_banked_infrastructure_changes():
    source = _source()
    assert "phase4_trial_boundary.py" in source
    assert "automatic_reseed()" in source
    assert "MAX_ITERATIONS=0" in source
    assert "MAX_IDENTICAL_RESEEDS=3" in source
    assert "ratchet_reseed_guard.py" in source
    assert "MAX_AUTO_RESEEDS" not in source
    assert "--auto-reseed-depth" in source
    assert "--reseed-signature" in source
    assert "--reseed-repeat-count" in source
    assert "TRIAL_CRITICAL_CHANGE" in source
    assert "METHOD_EVIDENCE_REPAIR" in source
    assert "DEBT_AFTER_CAPTURE_FAILED" in source
    assert "EXECUTOR_PROCESS_OR_DECISION_FAILURE" in source
    assert "EXECUTOR_COMMIT_MISMATCH" in source
    assert 'exec "$candidate_script"' in source
    loop = source[source.index("for ((iteration = 1;"):]
    boundary = loop.index("phase4_trial_boundary.py")
    reports = loop.index("finalize_method_iteration")
    assert boundary < reports
    assert loop.count('automatic_reseed "$iteration" "$actual_commit"') >= 7


def test_progress_sensitive_reseed_guard_has_executable_regression_coverage():
    source = _source()
    guard = ROOT / "tools" / "ratchet_reseed_guard.py"
    assert guard.is_file()
    assert "def build(" in guard.read_text(encoding="utf-8")
    assert "ratchet_reseed_guard.py" in source


def test_default_iteration_loop_is_unlimited_but_accepts_explicit_bound():
    source = _source()
    assert "MAX_ITERATIONS=0" in source
    assert (
        "for ((iteration = 1; MAX_ITERATIONS == 0 || "
        "iteration <= MAX_ITERATIONS; iteration++))"
    ) in source
    assert "max iterations must be a non-negative integer" in source


def test_fresh_verifier_receipt_is_required_for_promotions():
    source = _source()
    assert "campaign_review_due" in source
    assert '"$row_transitions" != "[]"' in source
    assert '"$dimension_transitions" != "[]"' in source
    assert "run_campaign_verifier" in source
    verifier = source[
        source.index("make_campaign_verifier_prompt()"):
        source.index("write_feedback()", source.index("make_campaign_verifier_prompt()"))
    ]
    assert "claim/falsifier packet" in verifier
    assert "typed v2 run receipts" in verifier


def test_verifier_prompts_pin_phase_four_despite_phase3_prerequisite_names():
    source = _source()
    fresh = source[
        source.index("make_verifier_prompt()"):
        source.index("make_campaign_verifier_prompt()")
    ]
    campaign = source[
        source.index("make_campaign_verifier_prompt()"):
        source.index("write_feedback()", source.index("make_campaign_verifier_prompt()"))
    ]
    for prompt in (fresh, campaign):
        assert 'The returned JSON field "phase" must be the integer 4.' in prompt
        assert 'The decision must contain "phase": 4' in prompt
        assert "never the decision phase" in prompt


def test_controller_remains_detached_and_preserves_safe_boundary_stop():
    source = _source()
    assert 'nohup setsid "${child[@]}" </dev/null' in source
    assert "tail --pid=$controller_pid" in source
    assert "stop-after-iteration" in source
    assert "STOPPED_AFTER_ITERATION.txt" in source


def test_controller_event_json_and_run_root_boundaries_are_fail_closed():
    source = _source()
    assert 'payload="${3:-{}}"' not in source
    assert 'local path="$1" event_type="$2" payload="{}"' in source
    assert 'payload="$3"' in source
    assert '[[ "$RUN_ROOT" == "$REPO" || "$RUN_ROOT" == "$REPO/"* ]]' in source
    assert "run root must be outside the operator repository" in source


def test_unbanked_terminal_failures_are_retained_and_fail_closed():
    source = _source()
    assert "write_terminal_failure_manifest()" in source
    assert "abl-phase4-method-terminal-failure/1" in source
    for code in (
        "DEBT_BASELINE_CAPTURE_FAILED",
        "DIRTY_EXECUTOR_TERMINAL",
        "DEBT_AFTER_CAPTURE_FAILED",
        "METHOD_REPORT_CAPTURE_FAILED",
    ):
        assert code in source


def test_executor_is_told_the_derived_live_receipt_requirements():
    source = _source()
    prompt = source[
        source.index("make_executor_prompt()"):
        source.index("make_verifier_prompt()")
    ]
    for phrase in (
        "typed owned sessions",
        "Counters are",
        "capture window must sit inside its bound",
        "strictly wider passive prelude",
        "move to executed/closed",
    ):
        assert phrase in prompt
