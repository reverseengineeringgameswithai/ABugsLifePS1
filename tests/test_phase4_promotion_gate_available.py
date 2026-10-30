"""The Phase-4 promotion gate must be RUNNABLE on master.

For weeks every row that reached a dimension claim recorded the same caveat --
"the full gate cannot be run here; the campaign registry lives in the unmerged
tranche" -- so only the two residual rules could ever be checked, never packet
identity, dimension claims, fixture pins or the frontier hash. That was a
standing blocker on the Phase-4 exit path, not a quirk of any one row.

The tranche (`ratchet/phase4-acceleration-scheduler-20260801`, tip 151a5a3b) is
not mergeable: it has 671 files master lacks and master has 575 it lacks. It is a
parallel line of development, not a branch waiting to land. So the gate was
extracted instead -- eight files, no other tranche content.

These tests pin that it stays runnable. They deliberately do NOT assert that any
packet passes: all three carried packets are tranche-era and fail on missing
evidence artifacts, which is the correct answer for master and must not be
"fixed" by weakening the gate.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools/phase4_promotion_preflight.py"
REGISTRY = ROOT / "config/phase4_promotion_packets.yaml"
POLICY = ROOT / "config/phase4_closure_policy.yaml"
DEBT = ROOT / "analysis/phase4_closure_debt.json"
OUT = ROOT / "analysis/phase4_promotion_preflight.json"

EXTRACTED = [
    "tools/phase4_promotion_preflight.py",
    "tools/phase4_common.py",
    "config/phase4_promotion_packets.yaml",
    "config/phase4_closure_policy.yaml",
    "config/phase4_campaigns.yaml",
    "config/phase4_findings.yaml",
    "config/phase4_inventory.yaml",
    "analysis/phase4_closure_debt.json",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_every_extracted_dependency_is_present():
    """A partial extraction is the failure mode: the gate imports phase4_common,
    which reads three configs master never had."""
    for rel in EXTRACTED:
        assert (ROOT / rel).is_file(), f"{rel} missing -- the gate cannot run without it"


def test_the_gate_actually_runs():
    """Exit 1 is the gate WORKING. It is fail-closed, so "0 ready, 3 not ready"
    is a nonzero exit by design -- asserting exit 0 here would demand that the
    gate pass before anything is ready for it. What must hold is that it builds a
    verdict rather than dying on a missing import or config.

    This calls `build()` IN MEMORY rather than the writing CLI. Running the CLI
    overwrites analysis/phase4_promotion_preflight.json, a tracked evidence
    artifact that routinely carries uncommitted operator work -- a test must
    never clobber it. (It did, three times, during the session that added this.)
    """
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_promotion_preflight as gate
    document = gate.build()
    assert isinstance(document, dict)
    assert document.get("packets"), "the gate built no packets"
    assert OUT.is_file(), "the retained verdict must still exist for the other tests"


def test_running_the_gate_cli_is_not_required_by_any_test():
    """Guard the rule above: no test in this file may invoke the writing CLI."""
    source = Path(__file__).read_text(encoding="utf-8")
    needle = "subprocess.run([sys.executable, " + "str(GATE)"
    occurrences = source.count(needle)
    assert occurrences == 0, (
        f"{occurrences} test(s) invoke the gate CLI, which overwrites "
        "analysis/phase4_promotion_preflight.json -- a tracked evidence artifact "
        "that routinely carries uncommitted operator work")


def test_the_extraction_is_internally_consistent():
    """The registry pins hashes of the policy and the debt snapshot. If a
    mismatched version of either had been pulled across, the gate would validate
    against a document nobody wrote."""
    reg = yaml.safe_load(REGISTRY.read_text())
    assert reg["policy_sha256"] == sha(POLICY)
    assert reg["debt_snapshot"]["sha256"] == sha(DEBT)


def test_it_never_mutates_the_registry():
    """The gate's own contract -- it reads and judges, it does not edit.

    Built in memory: invoking the CLI would overwrite a tracked evidence artifact.
    """
    sys.path.insert(0, str(ROOT / "tools"))
    import phase4_promotion_preflight as gate
    before = sha(REGISTRY)
    document = gate.build()
    assert sha(REGISTRY) == before
    assert document["registry_mutated"] is False


def test_a_packet_passes_only_when_its_evidence_is_actually_present():
    """The invariant this file has always cared about, now stated directly.

    It used to be written as "all three packets are not_ready", which was true
    only while every carried packet was tranche-era. Merging the frontier-closure
    workbench (b73493cfd1a5) brought `analysis/phase4_static_frontier_pilots.json`
    onto master, and that is the sole artifact E15's packet pins -- so E15 now
    passes BECAUSE its evidence appeared, which is precisely the case the old
    docstring allowed.

    Asserting the count would have to be edited every time evidence lands.
    Asserting the implication cannot be satisfied by weakening the gate: a packet
    may only be ready when every artifact it pins exists AND hashes as pinned.
    """
    import hashlib
    import yaml

    d = json.loads(OUT.read_text())
    packets = d["packets"]
    assert len(packets) >= 3
    registry = yaml.safe_load((ROOT / "config/phase4_promotion_packets.yaml").read_text())

    def pinned_artifacts(node, out):
        if isinstance(node, dict):
            if "artifact" in node and "sha256" in node:
                out.append((node["artifact"], node["sha256"]))
            for value in node.values():
                pinned_artifacts(value, out)
        elif isinstance(node, list):
            for value in node:
                pinned_artifacts(value, out)

    by_id = {p["id"]: p for p in registry.get("packets") or []}
    for packet in packets:
        if packet["verdict"] == "not_ready":
            assert packet.get("errors"), f"{packet['id']} is not_ready with no stated reason"
            continue
        refs: list[tuple[str, str]] = []
        pinned_artifacts(by_id.get(packet["id"], {}), refs)
        assert refs, f"{packet['id']} passed while pinning no evidence at all"
        for artifact, pin in refs:
            path = ROOT / artifact
            assert path.is_file(), f"{packet['id']} passed but {artifact} is absent"
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            assert actual == pin, f"{packet['id']} passed but {artifact} does not match its pin"


def test_the_extracted_registry_document_is_itself_valid():
    """`valid` is about the REGISTRY, not the packets.

    It means: schema recognised, policy at the expected path with a matching
    sha256 AND git-tracked, layer ids as declared, debt hash current, no
    duplicate packet ids. I first pinned `valid is False`, having seen that on
    the initial run without asking why -- it was False only because the freshly
    extracted policy file was still UNTRACKED. Committing it flipped the value,
    and the test I had written to describe the extraction instead described a
    moment during it. The gate checking that its own policy is committed is a
    feature; assert that it holds."""
    d = json.loads(OUT.read_text())
    assert d["valid"] is True, (
        "the extracted registry no longer validates -- check policy hash/tracking, "
        "the debt snapshot hash, and packet id uniqueness")


def test_the_gate_still_checks_more_than_the_residual_rules():
    """The point of having it: packet identity, claims, dependencies and frontier
    hashes -- the checks that were unavailable while it lived in the tranche."""
    codes = {e["code"] for p in json.loads(OUT.read_text())["packets"]
             for e in (p.get("errors") or []) if isinstance(e, dict)}
    assert codes - {"RESIDUAL_MALFORMED", "RESIDUAL_INTERSECTS"}, \
        "only residual codes fired; the wider gate is not engaging"


def test_e16s_campaign_exists_but_has_no_dimension_claim_yet():
    """Records exactly what authoring an E16 packet still needs, so the next
    person does not have to rediscover it: the campaign is there, the claim is
    not, and the gate refuses a packet whose claim is missing."""
    reg = yaml.safe_load((ROOT / "config/phase4_campaigns.yaml").read_text())

    def find(o):
        if isinstance(o, dict):
            if o.get("id") == "loading_overlays_resources":
                return o
            for v in o.values():
                r = find(v)
                if r:
                    return r
        elif isinstance(o, list):
            for x in o:
                r = find(x)
                if r:
                    return r
        return None

    camp = find(reg)
    assert camp is not None, "the E16 campaign disappeared from the registry"
    assert camp["primary_rows"] == ["E16_streaming_overlays"]
    assert "dimension_claims" not in camp, \
        "an E16 dimension claim now exists -- author its packet and update this test"
