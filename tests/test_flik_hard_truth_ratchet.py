from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "flik_hard_truth_ratchet.sh"


def _executor_prompt_source() -> str:
    source = SCRIPT.read_text()
    start = source.index("make_executor_prompt()")
    end = source.index("make_verifier_prompt()", start)
    return source[start:end]


def test_persistent_context_is_read_by_every_executor_iteration():
    source = SCRIPT.read_text()
    prompt = _executor_prompt_source()

    assert "Persistent run context passed verbatim to every" in source
    assert 'if [[ -n "$INITIAL_CONTEXT_SNAPSHOT" ]]; then' in prompt
    assert '"$iteration" == "1"' not in prompt
    assert "persistent run context; re-read it" in prompt


def test_every_executor_gets_movie_discovery_and_provenance_policy():
    prompt = " ".join(_executor_prompt_source().split())

    required_fragments = (
        "$REPO/movies/Phase$PHASE/",
        "the broader $REPO/movies/ tree",
        "A filename is only a lead",
        "pair each movie with its declared start state",
        "verify pristine mounted/save media",
        "centrally hash-pin",
        "media-classify",
        "Do not force an unrelated movie into the active campaign",
        "treat a JSON serial string as media proof",
    )
    for fragment in required_fragments:
        assert fragment in prompt


def test_verifier_rejects_undeclared_or_filename_only_movie_evidence():
    source = SCRIPT.read_text()
    start = source.index("make_verifier_prompt()")
    end = source.index("write_feedback()", start)
    prompt = source[start:end]

    assert "Audit movie consumption specifically" in prompt
    assert "centrally" in prompt and "hash-pinned" in prompt
    assert "provisionable in the clean checkout" in prompt
    assert "claims inferred from filenames alone" in prompt


def test_every_phase4_iteration_uses_capsules_before_live_duckstation():
    source = SCRIPT.read_text()
    executor = _executor_prompt_source()
    verifier_start = source.index("make_verifier_prompt()")
    verifier_end = source.index("write_feedback()", verifier_start)
    verifier = source[verifier_start:verifier_end]

    for prompt in (executor, verifier):
        assert "analysis/phase4_trace_capsule_set.json" in prompt or "central capsule index" in prompt
        assert "offline reader" in prompt
        assert "DuckStation" in prompt
        assert "every-cycle" in prompt
    assert executor.index("offline reader") < executor.index("Before any live DuckStation escalation")
    assert "specific information absent from the capsules" in " ".join(executor.split())
    assert "Reject" in verifier and "high-level complete fields" in verifier


def test_phase4_prompt_requires_substantial_107_row_offline_queue():
    source = SCRIPT.read_text()
    executor = " ".join(_executor_prompt_source().split())
    verifier_start = source.index("make_verifier_prompt()")
    verifier_end = source.index("write_feedback()", verifier_start)
    verifier = " ".join(source[verifier_start:verifier_end].split())

    for prompt in (executor, verifier):
        assert "analysis/phase4_offline_opportunity_queue.json" in prompt
        assert "107" in prompt
        assert "offline_ready" in prompt
        assert "subsystem-sized batch" in prompt
        assert "three highest-value" in prompt
        assert "analysis/phase4_live_escalations.json" in prompt
        assert "higher-priority offline-ready" in prompt
        assert "load-bearing dependency" in prompt
    assert "omitted/duplicate rows" in verifier
    assert "Falsify its freshness and coverage guards" in verifier
    assert "Generic claims" in executor
    assert "Reject token offline preflights" in verifier


def test_boundary_stop_is_checked_before_each_new_executor():
    source = SCRIPT.read_text()
    loop = source[source.index("for ((iteration = 1;"):]

    assert "stop-after-iteration" in source
    assert "STOPPED_AFTER_ITERATION.txt" in source
    assert 'if stop_requested_at_boundary "$iteration"; then' in loop
    assert loop.index("stop_requested_at_boundary") < loop.index("make_executor_prompt")
    assert "No closure claim was made by this boundary stop" in source


def test_default_launcher_detaches_controller_from_terminal_viewer():
    source = SCRIPT.read_text()
    outer_start = source.index('if ! contains_arg "--internal-run"')
    outer_end = source.index("PHASE=3", outer_start)
    outer = source[outer_start:outer_end]

    assert 'nohup setsid "${child[@]}" </dev/null' in outer
    assert 'controller.log' in outer
    assert 'controller.pid' in outer
    assert 'tail --pid=$controller_pid' in outer
    assert outer.index('nohup setsid') < outer.index('gnome-terminal --title')
    assert "Closing the viewer does not stop the controller" in source


def test_phase4_prompt_uses_complete_archived_runtime_and_quota_safe_scratch():
    source = SCRIPT.read_text()
    executor = " ".join(_executor_prompt_source().split())
    verifier_start = source.index("make_verifier_prompt()")
    verifier_end = source.index("write_feedback()", verifier_start)
    verifier = " ".join(source[verifier_start:verifier_end].split())

    assert "preflight available space and user quota" in executor
    assert "/var/tmp or a dedicated scratch directory" in executor
    assert "duckstation-runtimes/trace-capsule-v1-20260718/duckstation-qt" in executor
    assert "standalone archived executable" in executor
    assert "validate its SHA256SUMS" in verifier
    assert "running-binary hash from debugger.capabilities" in verifier
