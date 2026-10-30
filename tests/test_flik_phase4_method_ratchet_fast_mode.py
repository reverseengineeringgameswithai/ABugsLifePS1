from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "flik_phase4_method_ratchet.sh"


def test_fast_mode_is_explicit_and_applies_to_every_codex_role():
    text = SCRIPT.read_text()
    assert "--fast                 Run every Codex executor" in text
    assert "FAST_MODE=0" in text
    assert "--fast)" in text
    assert "codex_base+=(-c 'service_tier=\"fast\"' --enable fast_mode)" in text

    # All executor, verifier, and seed-repair calls share run_codex/codex_base.
    assert text.count('run_codex "') >= 5
    assert text.count("codex_base=(codex exec") == 1


def test_fast_mode_survives_automatic_reseed_and_is_recorded():
    text = SCRIPT.read_text()
    assert "args+=(--fast)" in text
    assert '"codex_fast_mode":' in text
    assert '"codex_service_tier":' in text


def test_capacity_retry_is_bounded_and_requires_unchanged_clean_state():
    text = SCRIPT.read_text()
    assert "CODEX_CAPACITY_RETRIES=3" in text
    assert 'grep -Fq "Selected model is at capacity" "$attempt_log"' in text
    assert '[[ -z "$starting_status" ]]' in text
    assert '[[ "$current_head" == "$starting_head" ]]' in text
    assert '[[ "$current_status" == "$starting_status" ]]' in text
    assert '>>"$RUN_DIR/codex-capacity-retries.log"' in text
    assert "delay=$((attempt * 10))" in text
