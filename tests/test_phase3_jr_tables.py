"""Phase-3 WP4 guard: the jr-dispatch frontier.

The headline is a correction, not a conquest: most of the 95 `jr` sites were never
table dispatches at all — they jump INTO CODE (unrolled loops / jump islands). A
tool that called them "undecoded tables" would have been lying about the size of
the frontier."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
J = json.loads((ROOT / "analysis" / "phase3_jr_tables.json").read_text())


def test_every_jr_site_is_classified():
    c = J["classification"]
    assert (c["table_dispatch"] + c["computed_code_jump"] + c["unresolved"]
            == J["jr_sites"] == 95)
    assert J["fixture_sha256"], "no EXE pin (DoF #1)"


def test_the_three_known_tables_are_recovered_independently():
    """Self-check: the slicer must rediscover the tables we already decoded by
    hand from the EXE. If it cannot, its other 33 tables are not trustworthy."""
    tables = {v["table"] for v in J["decoded"].values()}
    for known in ("0x8001B2F4",     # mover-VM opcodes
                  "0x8001B1C0",     # berry throw
                  "0x8001B848"):    # plant behaviours
        assert known in tables, known


def test_decoded_targets_all_land_in_named_functions():
    """A table whose entries do not resolve is a wrong slice, not a finding —
    the tool refuses to report those, so everything reported must resolve."""
    total = sum(v["entries"] for v in J["decoded"].values())
    named = sum(v["named_targets"] for v in J["decoded"].values())
    assert total >= 800
    assert named == total, f"{total - named} unresolved targets slipped through"


def test_most_jr_sites_are_not_tables():
    """The correction that matters: the majority jump into code."""
    c = J["classification"]
    assert c["computed_code_jump"] >= c["table_dispatch"]
    assert c["unresolved"] <= 20      # the honest remaining frontier
