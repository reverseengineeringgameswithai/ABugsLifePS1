from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "pcsx_redux_migration_ratchet.sh"
CONTRACT = ROOT / "engineering-specs" / "pcsx-redux-migration.md"
PLAN = (
    ROOT
    / "ObsidianVault"
    / "Playbooks"
    / "PCSX-Redux Migration Plan - Retire DuckStation as a Required Dependency.md"
)


def _section(source: str, start: str, end: str) -> str:
    return source[source.index(start) : source.index(end, source.index(start))]


def test_shell_syntax_and_two_repository_loop():
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'git -C "$ABL_REPO" worktree add -b "$ABL_BRANCH"' in source
    assert 'git -C "$REDUX_REPO" worktree add -b "$REDUX_BRANCH"' in source
    assert 'git -C "$ABL_REPO" worktree add --detach' in source
    assert 'git -C "$REDUX_REPO" worktree add --detach' in source
    assert "--add-dir" in source


def test_every_valid_candidate_reaches_a_fresh_hard_ass_verifier():
    source = SCRIPT.read_text(encoding="utf-8")
    loop = source[source.index('while ((MAX_ROUNDS == 0 || round <= MAX_ROUNDS))') :]
    assert "STEP 1 MIGRATION IMPLEMENTER" in loop
    assert "STEP 2 HARD-ASS VERIFIER" in loop
    assert loop.index("STEP 1 MIGRATION IMPLEMENTER") < loop.index(
        "STEP 2 HARD-ASS VERIFIER"
    )
    assert "hard_ass_migration_verifier" in source
    assert "accepted cannot carry gaps or required_input" in source
    assert "rejected requires exact gaps" in source
    assert "write_verifier_feedback" in loop
    assert "hard-ass verifier rejected round" in loop


def test_hard_ass_prompt_requires_actual_full_replacement():
    source = SCRIPT.read_text(encoding="utf-8")
    verifier = " ".join(
        _section(source, "make_verifier_prompt()", "pause_infrastructure()").split()
    )
    required = (
        "FULLY armed to be the main replacement",
        "every WP0-WP10 requirement",
        "complete load-bearing Phase-2 oracle",
        "active Phase-4 scenario surface",
        "instrumented and uninstrumented equality",
        "digital and analog/two-port coverage",
        "historical DuckStation evidence",
        "clean-checkout",
        "not a conveniently selected sample",
        "gaps=[]",
    )
    for fragment in required:
        assert fragment in verifier


def test_immutable_context_and_verifier_feedback_reach_every_round():
    source = SCRIPT.read_text(encoding="utf-8")
    implementer = " ".join(
        _section(source, "make_implementer_prompt()", "make_verifier_prompt()").split()
    )
    verifier = " ".join(
        _section(source, "make_verifier_prompt()", "pause_infrastructure()").split()
    )
    for prompt in (implementer, verifier):
        assert "$CONTRACT_SNAPSHOT" in prompt
        assert "$PLAN_SNAPSHOT" in prompt
        assert "$PROGRESS" in prompt
    assert "$FEEDBACK" in implementer
    assert "immutable plan and contract snapshots are authoritative" in implementer
    assert "feedback.json" in source
    assert "progress-ledger.json" in source


def test_resume_lock_retry_and_boundary_stop_are_durable():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "--resume RUN_ID" in source
    assert 'flock -n 9' in source
    assert "controller-state.json" in source
    assert "controller_recovery" in source
    assert "attempt $attempt/3" in source
    assert "INFRASTRUCTURE_PAUSED.md" in source
    assert "stop-after-round" in source
    assert "STOPPED_AT_BOUNDARY.md" in source
    assert "resume.sh" in source
    assert "Power loss does not erase" in source


def test_status_helper_is_safe_under_nounset():
    source = SCRIPT.read_text(encoding="utf-8")
    status = _section(source, "print_status()", 'if [[ -n "$STATUS_ID" ]]')
    assert 'local run_id="$1"' in status
    assert 'local run_dir="$RUN_ROOT/runs/$run_id"' in status
    assert 'local run_id="$1" run_dir=' not in status


def test_default_terminal_is_a_viewer_not_the_controller():
    source = SCRIPT.read_text(encoding="utf-8")
    outer = _section(source, 'if ! contains_arg "--internal-run"', "ABL_REPO=")
    assert 'nohup setsid "${child[@]}" </dev/null' in outer
    assert "controller.pid" in outer
    assert "controller.log" in outer
    assert "tail --pid=$controller_pid" in outer
    assert outer.index("nohup setsid") < outer.index("gnome-terminal --title")
    assert "Closing the viewer does not stop the controller" in source


def test_operator_wip_and_license_boundary_are_explicit():
    source = " ".join(SCRIPT.read_text(encoding="utf-8").split())
    contract = " ".join(CONTRACT.read_text(encoding="utf-8").split())
    for text in (source, contract):
        assert "CC BY-NC-ND" in text
        assert "GPLv2" in text
        assert "pristine" in text
        assert "ALLMODS" in text
        assert "never" in text.lower() and "merge" in text.lower()
    assert 'bootstrap_rels=("$PLAN_REL" "$CONTRACT_REL" "$SCRIPT_REL" "$TEST_REL")' in (
        SCRIPT.read_text(encoding="utf-8")
    )


def test_contract_and_plan_retain_complete_cutover_scope():
    contract = " ".join(CONTRACT.read_text(encoding="utf-8").split())
    plan = PLAN.read_text(encoding="utf-8")
    for wp in range(11):
        assert f"WP{wp}" in plan
    required = (
        "sole emulator required for ordinary ABL",
        "Implement deterministic movies in Redux core",
        "Instrumentation-neutrality protocol",
        "persistent offline evidence",
        "Migrate fixtures and behavioral evidence",
        "clean-checkout",
        "DuckStation no longer required for daily work",
    )
    joined_plan = " ".join(plan.split())
    for fragment in required:
        assert fragment in joined_plan
    assert "PCSX-Redux is fully armed" in contract
    assert "complete required Phase-2 oracle" in contract
    assert "active Phase-4 scenario" in contract


def test_no_automatic_merge_or_push():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "The ratchet never merges or pushes" in source
    assert "No merge or push was performed" in source
    assert "git merge" not in source
    assert "git push" not in source
