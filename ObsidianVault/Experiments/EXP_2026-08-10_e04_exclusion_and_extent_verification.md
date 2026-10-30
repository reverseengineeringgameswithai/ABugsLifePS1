---
type: experiment
status: complete
date: 2026-08-10
system: control-plane data quality / extent partition
phase: 4
artifacts:
  - analysis/phase4_control_plane_data_quality.json
  - analysis/phase3_gate_audit.json
  - config/segments.yml
  - tools/knowledge_closure_audit.py
---

# Verifying two unchecked increments: the E04 gate exclusion, and the `0x80042E94` extent

Both were flagged in the 2026-08-10 handoff as "never checked". Neither had been
looked at by anyone other than its author.

## 1. The E04 exclusion — VERDICT: sound, correctly scoped, and provably not a gate weakening

**The claim under review** (`analysis/phase4_control_plane_data_quality.json`):
the string `6 progression-diverse saves reused read-only; live L1/R1 traces on
level01.sav` *"was a stale finding retained under
`analysis/phase3_gate_audit.json:upstream_durability.blockers.missing_fixture_pins`,
not an authored fixture reference"*, and the repair excludes *"only the
`missing_fixture_pins` output field of `phase3_gate_audit.json`"*, with
`gate_weakened_or_whitelisted: false`.

This sits directly on the standing rule about never weakening a gate to make it
pass, so it deserved a real check rather than a reading of the prose.

### The code does what the receipt says

`tools/knowledge_closure_audit.py:383`:

```python
skip_keys = ({"missing_fixture_pins"}
             if path.name == "phase3_gate_audit.json" else set())
```

One key, one file, inside the one `phase[123]_*.json` consumer sweep. The
central missing-pin predicate is untouched, and no whitelist of fixture paths
exists anywhere.

### Why the exclusion cannot hide a real reference — the argument that settles it

`missing_fixture_pins` is **purely derivative**: all 31 entries carry a
`consumers` list recording where the reference actually came from (verified —
`entries WITHOUT a consumers list: 0`). So any *real* authored reference in that
field is, by construction, also present in the consumer that produced it, and
those consumers are scanned independently. The only thing the field can
uniquely contribute is an entry whose sole consumer is the gate audit itself —
i.e. exactly the self-referential class.

And that is what the disputed string is:

| string | consumers |
|---|---|
| short E04 (`live L1/R1 traces`) | **`analysis/phase3_gate_audit.json`** — and nothing else |
| long E04 (`live L1/R1/L1+left/R1-held traces`) | `phase2_row_coverage.json`, `phase3_gate_audit.json`, `phase3_ownership_graph.json`, `mechanics:E04_camera_system` |

The long string is referenced by real authored artifacts — which is why
expanding it to the six named saves was the right repair. The short one is
referenced by **nothing but the audit's own output**. Corroborated by file
sweep: the short string appears only in `phase3_gate_audit.json` (its own
finding), `phase3_knowledge_audit.json` (a *stringified dump* of that same
finding — substring, not a value), the receipt, and the work order. It is
absent from `analysis/mechanics_baseline.yaml` and
`config/fixture_reference_sets.yaml`, the authored sources. **The diagnosis
holds.**

### ⚠️ But the receipt understates the exclusion's effect: it suppresses THREE entries, not one

Counterfactual, run in-process with nothing written — `build_fixture_set` with
the exclusion as shipped, then with `recursive_strings` patched to ignore
`skip_keys`:

```
as shipped         : missing_central_pins = 0
exclusion disabled : missing_central_pins = 3
```

The three are the short E04 string, the long E04 string, **and** the
`E02_FreshLoad_Clover.movie.json` basename — and all three now carry
`consumers: ['analysis/phase3_gate_audit.json']` **only**.

That is not a second gate weakening: the long-E04 and E02 references *were*
repaired at their real source (`config/fixture_reference_sets.yaml`), so what
the exclusion suppresses today are three **stale echoes** in an artifact that
has not been regenerated since. But the receipt reads as though a single string
is excluded and the other two were fixed outright, and that is not the current
state. Worth correcting on the record.

### The durable fix, not yet applied: regenerate the stale artifact

`phase3_gate_audit.json:missing_fixture_pins` holds **30 entries at `HEAD`, 31
in the working tree**, while the live count is **0**. It is simply stale.
Regenerate it and the field collapses, after which the exclusion suppresses
nothing and the gate passes on its own merits with no standing blind spot in
the scan.

⚠️ **Not done here**, deliberately: `tools/phase3_gate_audit.py` writes
`analysis/phase3_gate_audit.json` unconditionally (no `--out`), and that file is
currently **modified operator WIP**. Overwriting it would destroy work that is
not mine. This is a one-command increment for whoever owns that WIP.

**Net verdict:** the exclusion is legitimate, minimally scoped, and provably
incapable of hiding a live reference. It is a *workaround for stale data*
rather than a repair of it, and the repair is cheap.

## 2. The `0x80042E94` extent disagreement — VERDICT: correctly decided, fix landed, item closed

The handoff asked whether this is "still applicable". It is not — it was decided
and fixed inside the same control-plane increment that surfaced it. Verified
rather than assumed:

- **Re-derived all 8 tail words from the pristine image**: 8/8 match the
  receipt. `0x80042F98 = 0xA7820410` (`sh $v0,0x410($gp)`, 0x410 = 1040) and
  `0x80042F9C = 0x00021400` (`sll $v0,$v0,16`) are live fall-through result
  processing, so an extent ending at `0x80042F98` was eight bytes short.
- **`config/segments.yml` carries the fix**: `{start: 0x80042e94, end:
  0x80042fa0}` (268 bytes, matching the hand-ASM reproduction) and the adjacent
  `{start: 0x8001a1e0, end: 0x8001a900}` (1,824 bytes).
- **Independent support for the receipt's careful caveat.** It says `0x80042FA0`
  is a partition boundary, *not* a return claim. There is **no `jr $ra`
  anywhere in `[0x80042E94, 0x80042FA0)`** — the entry genuinely falls through
  into the callable suffix. The caveat was not hedging; it was accurate.
- **`tests/test_substrate.py`: 11 passed.** The test that originally exposed
  this now passes.

## 3. Incidental: I broke a test and fixed it

`tests/test_phase4_extent_audit.py::test_retained_report_is_fresh` failed while
I was working. Cause was **mine**: adding
`tools/phase4_e02_disc_region_code_census.py` moved the repo-wide sweep from
1,081 to 1,082 files scanned, so the retained report went stale — the same
post-commit refresh D3 needed at `619cac8`. Regenerated; **9 passed**, with
`unacknowledged_declarations: 0` and truncations unchanged at 17/17, so the new
tool introduced no findings.

⚡ **Adding any tracked file invalidates `analysis/phase4_extent_audit.json`.**
Refresh it in the same commit, or the next person inherits a red test that has
nothing to do with their work.

⚠️ **Order matters, and I got it wrong the second time too:** the sweep enumerates
**git-tracked** files, not the filesystem. Refreshing before `git add` leaves the
new files uncounted and the report stale again the moment they are staged
(1,082 → 1,084 here). Sequence is **`git add` the new files → refresh → commit**.

## 4. The one red test, resolved: LEVEL02 was re-recorded because it was desyncing

The pre-existing failure in §3's neighbourhood
(`test_declared_external_fixture_bytes_match_pins`) was
`movies/Phase4/Interpreter/100% Runs/LEVEL02_Tunnels.movie.json` at 24,987,387
bytes against a 34,576,444-byte pin. **Operator confirmed the capture was
re-recorded because the old one was desyncing.** That makes it a legitimate
re-pin with a reason, not the laundering of a changed fixture — the distinction
that decides whether updating a pin is honest.

| | superseded | current |
|---|---|---|
| movie | `a75ee6b1…` 34,576,444 B / 44,917 frames | `2d5a8ddc…` 24,987,387 B / 36,397 frames |
| state | `af51903f…` 1,725,912 B | `82c23124…` 1,699,343 B |

**The new pair is healthy where it matters.** Format v4, and the state binding is
*record-time*: `sha256_origin: recording`, `sha256_provenance: recording_start`,
`sha256_backfilled: false`, and the movie's declared `start_state.sha256` equals
the `.sav` on disk exactly — so both playback paths accept it rather than failing
`-32006`. `armed_while_paused: false`, anchored at frame 8688.

**No banked evidence rested on the desyncing capture.** The only artifact citing
this movie for a *result* is `analysis/phase4_f01_campaign_breadth.json`, whose
`sessions[5]` already records **`frames: 36397`** — the new movie. The breadth
sweep ran against the re-recording. Every other artifact carrying the old hash
was a pin registry.

### ⚠️ My drift census was ONE-DIRECTIONAL, and the regeneration proved it

Before regenerating I measured the blast radius: an offline sweep over all 526
previously-pinned fixtures found **exactly 2 drifted, 0 missing** — so a
regeneration could not silently launder anything else. Good as far as it went.

The regeneration moved **18 entries, not 2.** The extra 16 were **additions**:
the eight E10 hazard movies and their eight save states, present on disk and
already cited by the E10 re-sweep, but never pinned.

⚡⚡ **A pin→disk sweep cannot see a fixture that was never pinned.** I checked
"does every pin still match its bytes?" and called it a census; the other
direction — "is every fixture on disk pinned?" — was the one with findings in
it. Exact sets, *both* directions, is a standing rule here and I applied half of
it. Afterwards: all **542** entries re-hash to their on-disk bytes offline, 0
mismatches, and `test_knowledge_closure` is **16 passed / 0 failed** — the first
fully consistent state of the fixture corpus this session.

### Live-run justification, and a launcher caveat worth carrying

`AGENTS.md` requires naming the reason for escalating to a live instance:
`emulator.getStateInfo` media classification is the single field that cannot be
computed offline. Isolated instance, fresh absolute config dir, dedicated port
23481 and token, media verified pristine `SCUS-94288` before use, stopped
PID-scoped.

⚠️ **That generic launcher writes a `settings.ini` with no `[CPU]` section**, and
`debugger.status` confirmed the instance ran **`Recompiler`** — the operator
spotted it from the missing frame-count/controls in the window, which is their
standing tell for a desync-prone instance. **Harmless here** for a mechanical
reason, not a hopeful one: `audit_fixtures` replays nothing — it hashes files in
Python and reads save-state headers — and the outcome was confirmed by re-hashing
all 542 entries offline afterwards. It would **not** be harmless for movie
replay, which must use
`tools/launch_repro_playback.sh --execution-mode Interpreter`.
