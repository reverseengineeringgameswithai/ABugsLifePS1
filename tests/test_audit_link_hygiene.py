from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

CASES = {
    "ObsidianVault/Mods/Blackberry/MOD_blackberry_net_new_berry.md": (
        "ObsidianVault/Mods/Blackberry net-new berry.md",
        "ObsidianVault/Archive/Superseded/Mods_Blackberry_net-new_berry.md",
        "The full chronological working note remains at",
    ),
    "ObsidianVault/Mods/Gold Berry/MOD_gold_berry_token_drop.md": (
        "ObsidianVault/Mods/Gold-berry drop on non-gold kills.md",
        "ObsidianVault/Archive/Superseded/Mods_Gold-berry_drop_on_non-gold_kills.md",
        "The full chronological working note remains at",
    ),
    "ObsidianVault/Mods/HUD/MOD_grain_emblem_and_hud_total.md": (
        "ObsidianVault/Systems/Grain emblem and HUD total mod.md",
        "ObsidianVault/Archive/Superseded/Systems_Grain_emblem_and_HUD_total_mod.md",
        None,
    ),
}


def _frontmatter(text):
    return yaml.safe_load(text.split("---", 2)[1])


def test_migrated_mod_evidence_paths_exist_and_old_paths_are_not_live():
    for page, (former, archive, stale_sentence) in CASES.items():
        text = (ROOT / page).read_text()
        evidence = _frontmatter(text)["evidence"]
        assert former not in evidence
        assert archive in evidence
        assert (ROOT / archive).is_file()
        assert "Archive citation is intentional provenance" in " ".join(text.split())
        if stale_sentence:
            assert stale_sentence not in text


def test_player_action_page_does_not_restore_dangling_a10_link():
    page = (ROOT / "ObsidianVault/Canon/Systems/SYS_player_action_state_laws.md").read_text()
    assert "[[A10_handstand]]" not in page
    assert "[[#Handstand|A10 handstand]]" in page
    assert "## Handstand" in page
