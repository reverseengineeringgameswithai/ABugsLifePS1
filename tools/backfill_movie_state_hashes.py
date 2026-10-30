#!/usr/bin/env python3
"""Backfill `start_state.sha256` into state-anchored movie fixtures.

⚠ STATUS 2026-08-05: THIS TOOL IS DONE AND SHOULD NOT BE NEEDED AGAIN. The fork now
hashes the start state AT RECORD TIME, so movies recorded from here on are bound by
construction (`sha256_origin: "recording"`) and there is nothing to backfill. Anything
this tool still touches is by definition a pre-2026-08-05 fixture. Keep the two
provenances distinct: `"recording"` means the digest was taken against the state the
movie was actually recorded on; `"backfill"` means only what the paragraph below says.

THE GAP (as it stood before that change). 123 movies are anchored to a save state and
every one records `start_state.sha256` as null. `movie.loadAndArm` already rejects a mismatch -- but
only when the movie carries a hash, so today it never rejects anything. A state that
drifts therefore replays silently: playback succeeds, `reproducible` reports true, and
the run goes off-script. Codex confirmed the emulator never populates the field on
recording, and `evidence.captureBundle` returns a digest without writing it back.

WHAT THIS DOES AND DOES NOT BUY YOU -- the distinction matters more than the change.

  IT BUYS forward protection. After the backfill, any future divergence between a
  movie and its state is caught at load, for all 123 fixtures instead of the 2 that
  currently have behavioural oracles.

  IT DOES NOT BUY retroactive validation. Hashing a .sav today pins "this is the
  state that was on disk on the backfill date". It cannot show the state still
  matches what the movie was recorded against. If a state has ALREADY drifted, this
  bakes the drifted hash in and certifies a broken fixture as good.

  Every record therefore carries `sha256_provenance` saying exactly that. Writing a
  bare hash would encode an inference as a passing check, which is the failure this
  repository has the most scar tissue about.

SAFETY. movies/ is NOT git-tracked, so an edit here is not reversible by git. The
default is a dry run; --apply requires an explicit backup directory and refuses to
proceed if it cannot create one.

    tools/backfill_movie_state_hashes.py                 # dry run, default
    tools/backfill_movie_state_hashes.py --apply --backup /path/to/backup
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVENANCE = ("sha256 of the referenced .sav as found on disk at backfill time. This "
              "detects FUTURE drift between movie and state. It does NOT establish "
              "that the state still matches what the movie was recorded against -- no "
              "recording-time hash exists to compare with.")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def survey():
    rows, digests = [], {}
    for m in sorted(ROOT.glob("movies/**/*.movie.json")):
        try:
            d = json.loads(m.read_text())
        except Exception as e:
            rows.append({"movie": m, "skip": "unparseable: %s" % e})
            continue
        ss = d.get("start_state") or {}
        if ss.get("from_boot", True):
            continue
        p = ss.get("path")
        sav = Path(p) if p else None
        if not sav or not sav.exists():
            rows.append({"movie": m, "skip": "state missing: %s" % p})
            continue
        if ss.get("sha256"):
            rows.append({"movie": m, "skip": "already hashed"})
            continue
        key = str(sav)
        if key not in digests:
            digests[key] = sha256(sav)
        rows.append({"movie": m, "doc": d, "sav": sav, "sha": digests[key],
                     "size": sav.stat().st_size})
    return rows, digests


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup", type=Path)
    a = ap.parse_args()

    rows, digests = survey()
    todo = [r for r in rows if "doc" in r]
    skipped = [r for r in rows if "skip" in r]

    print("state-anchored movies needing a hash : %d" % len(todo))
    print("distinct .sav to hash                : %d" % len(digests))
    print("skipped                              : %d" % len(skipped))
    for s in skipped[:8]:
        print("    %-46s %s" % (s["movie"].name, s["skip"]))

    shared = {}
    for r in todo:
        shared.setdefault(str(r["sav"]), []).append(r["movie"].name)
    multi = {k: v for k, v in shared.items() if len(v) > 1}
    if multi:
        print("\n⚠ states shared by more than one movie -- one drift breaks several:")
        for k, v in multi.items():
            print("    %-42s %d movies" % (Path(k).name, len(v)))

    print("\nsample of what would be written:")
    for r in todo[:3]:
        print("    %-46s %s… (%d bytes)"
              % (r["movie"].name, r["sha"][:16], r["size"]))

    if not a.apply:
        print("\nDRY RUN -- nothing written. Re-run with --apply --backup <dir>.")
        print("movies/ is NOT git-tracked; --apply copies every file it edits to the")
        print("backup directory first and refuses to run without one.")
        return 0

    if not a.backup:
        print("\nREFUSING: --apply requires --backup <dir>. movies/ is not git-tracked,")
        print("so there is no other way back.")
        return 2
    a.backup.mkdir(parents=True, exist_ok=True)

    written = 0
    for r in todo:
        rel = r["movie"].relative_to(ROOT)
        dst = a.backup / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(r["movie"], dst)                       # backup BEFORE touching
        d = r["doc"]
        d["start_state"]["sha256"] = r["sha"]
        d["start_state"]["sha256_provenance"] = PROVENANCE
        d["start_state"]["sha256_backfilled"] = True
        r["movie"].write_text(json.dumps(d, indent=1) + "\n")
        written += 1
    print("\nbacked up to %s" % a.backup)
    print("hashes written into %d movies" % written)
    print("\nFORWARD protection only: a future mismatch is now caught at load. This")
    print("does NOT certify that any state still matches its recording.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
