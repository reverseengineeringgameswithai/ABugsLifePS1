#!/usr/bin/env python3
"""Ratchet the overlay census for the B06/B08 subsystem.

Resident-image completeness is not whole-game completeness. The per-level
`LEVEL*.BIN` and the shared `MEMORY.BIN` are CdRead-loaded code running in the same
address space, and none of it had ever been censused when these rows were first
(wrongly) called solved.

Baseline, established 2026-08-01 over the 21 pristine overlay blobs:

  * NO overlay accesses the power slot 0x800A657E at all -- not one, read or write.
    That is a real negative: most blobs contain between 1 and 128 `lui rX, 0x800A`
    address formations, so they do compute addresses in that page; none of them
    lands on the slot.
  * THREE overlays touch true health, and every one of them is a READ. No overlay
    WRITES either address, so the damage-immunity claim -- which is about writes --
    is unaffected. They are nonetheless downstream consumers that DoD item 2
    requires to be enumerated, and no earlier census had found any of them:

        LEVEL03_LEVEL  0x800B41D0   s1 = 6 - health, alongside a counter bump at
                                    0x800822F4
        LEVEL08_LEVEL  0x800B3DAC   bgez health -- an in-overlay DEATH CHECK
        LEVEL10_LEVEL  0x800B3D50   80 - health*20 -> overlay var 0x800B41B8,
                                    gated on player Z (0x800A6508)

    This baseline was itself written wrong the first time -- from a truncated view
    that showed only LEVEL10 -- and the gate caught it on its first run. That is
    the gate doing its job, and the reason a census nobody can re-run is not
    evidence.

Any drift here means the overlay frontier changed and must be reviewed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SLOT = Path("analysis/phase4_b06_b08_census_overlays.json")
HEALTH = Path("analysis/phase4_b06_b08_census_overlays_6594.json")
def _pc(v: str) -> str:
    """Normalise a PC for comparison; `.upper()` alone would turn 0x into 0X."""
    return "0x%08X" % int(v, 16)


EXPECTED_HEALTH = {
    ("LEVEL03_LEVEL", "0x800B41D0", "read"),
    ("LEVEL08_LEVEL", "0x800B3DAC", "read"),
    ("LEVEL10_LEVEL", "0x800B3D50", "read"),
}


def main() -> int:
    ok = True
    slot = json.loads(SLOT.read_text())
    health = json.loads(HEALTH.read_text())

    # Distinguish MISSING INPUTS from a real frontier change. The pristine EXE and the
    # overlay blobs are gitignored (copyrighted), so a clean checkout has neither, and
    # scanning zero blobs would otherwise be reported as "every known access disappeared"
    # -- a missing-input condition masquerading as drift. A clean-clone run caught exactly
    # that. Provision with tools/verify_repro_inputs.py --provision before gating.
    if slot.get("blobs_scanned", 0) == 0 and health.get("blobs_scanned", 0) == 0:
        print("  INPUTS ABSENT: zero overlay blobs scanned. This is NOT drift -- the "
              "staged blobs are gitignored and are not in this checkout.")
        print("  Provision them (tools/verify_repro_inputs.py --provision) and re-run.")
        return 2

    if slot["total_hits"] != 0:
        print("  DRIFT: an overlay now accesses the power slot 0x800A657E:")
        for o in slot["overlays"]:
            for h in o.get("hits", []):
                print("    %s %s %s" % (o["overlay"], h["pc"], h["insn"]))
        ok = False

    hits = [(o["overlay"], h) for o in health["overlays"] for h in o.get("hits", [])]
    got = {(n, _pc(h["pc"]), h["kind"]) for n, h in hits}
    if got != EXPECTED_HEALTH:
        for miss in sorted(EXPECTED_HEALTH - got):
            print("  DRIFT: overlay health access no longer found: %s" % (miss,))
        for extra in sorted(got - EXPECTED_HEALTH):
            print("  DRIFT: new overlay health access, review it: %s" % (extra,))
        ok = False
    writes = [(n, h) for n, h in hits if h["kind"] == "write"]
    if writes:
        print("  DRIFT: an overlay now WRITES true health -- this would break the "
              "damage-immunity claim: %s" % writes)
        ok = False

    blobs = slot["blobs_scanned"]
    if blobs < 20:
        print("  DRIFT: only %d overlay blobs scanned; the staging tree may be incomplete" % blobs)
        ok = False

    print("  overlay baseline (%d blobs): %s" % (blobs, "OK" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
