---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Reproducibility Checklist.md
aliases:
  - "Reproducibility Checklist"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Reproducibility Checklist.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Reproducibility Checklist
type: plan
updated: 2026-06-21
tags: [plan, blockers, reproducibility, b2]
---

# Reproducibility Checklist (B2 hardening)

> Current checklist for [[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]] and [[Gap Audit|GAP-0001]]. Supersedes the stale 2026-06-18 statements that the fork was clean and only 14 files were uncommitted. Full evidence: [[DuckStation Fork Reproducibility]].

## Current audited state (2026-06-20)

- **ABL repository:** M0 `0d6b0af`, M1 `16aa807`, M2 `779849e`; safe tests pass. Disc/BIOS/save/extracted inputs remain ignored/local.
- **DuckStation location:** `~/duckstation`, Git branch `external-debugger-control`, HEAD `296955321fd9375fa94692d96df788eccd708135`.
- **DuckStation worktree:** **dirty** — 34 modified tracked paths + 16 untracked status entries. The current behavior is not represented by HEAD alone.
- **Remote:** only upstream `origin=https://github.com/stenzek/duckstation.git`; the custom branch has no upstream, tag, or remote branch. HEAD is 65 commits ahead of the local upstream merge-base.
- **API documentation:** present and extensive: fork contracts/client docs plus 35 feature notes in [[DuckStation API Index]]. Documentation is not the blocker.
- **API revision split:** 114 dispatched methods at HEAD; 27 additional methods only in the dirty worktree. Several vault API notes describe those dirty-only calls.
- **Current binary:** local dirty build SHA-256 `796965d722b6c2c5d135f4c3e457e68e16f20cab632c3ab2ef43b3708f8c6501`; not a substitute for recoverable source.
- **Fixture policy:** save states remain host-local/copyrighted. Reproduction must use owner-supplied inputs or a scripted route; never commit them.

## Completed safeguards

1. ABL source/docs/tools and the findings store are tracked.
2. Host paths resolve through `tools/_env.py`; safe tests enforce no user-home literals in tracked Python tools **and tests** (`tests/test_path_portability.py`), and a pinned `tools/requirements.txt` (+ `pyproject.toml`) provisions the committed tools (GAP-0003 ✅ 2026-06-21).
3. Critical inputs are hash-checked by `tools/verify_repro_inputs.py` / `tools/repro_inputs.sha256`.
4. The fork HEAD, branch, dirty boundary, method boundary, build recipe, binary/spec hashes, and API-note map are documented in [[DuckStation Fork Reproducibility]].
5. The [[Preservation Policy]] prohibits committing disc, BIOS, saves, RAM dumps, and extracted copyrighted assets.

## Closure checklist — executed 2026-06-21

- [x] Export the 34 modified + 16 untracked (23 files) fork entries as an explicit package — bundle (`72aa9fb0…`) + tracked patch (`d0b29800…`) + untracked archive (`c9279b28…`) in `~/duckstation-fork-preservation/`; clone+patch+extract reconstructs the operator source **byte-exact, 57/57 files**.
- [x] Anchor the validated source with a tag — non-destructive in-repo tag `abl-gap0001-fork-296955321` → `296955321` in `~/duckstation`.
- [ ] **Off-machine** push to a private remote — **operator-only residual** (`origin` is upstream stenzek; no credentials assumed). The off-host *bundle fallback* already exists locally; it just needs copying off-machine.
- [x] Verify a clean second-machine clone configures + builds `duckstation-qt` — independent clone `~/abl-fork-build` configured (CMake/Ninja/clang + vendored Qt6 pack) and built (exit 0).
- [x] Tie the binary hash + API contract to the clean source — clean-built binary `fd4bf9ed…`; methods pinned in `tools/duckstation_rpc_method_manifest.md`.
- [x] Re-run one representative closed ABL experiment from the clean-built binary — `tools/trace_spawn_floor.py` PASS (exit 0): spawn floor = LEVEL.DAT `fcn.80010000` (DAT `0x15dec..0x2f59c`), visual ≠ collision; fixture `SCUS-94288_1.sav`, disc `SCUS-94288` (`46310218…`); used dirty-only `gpu.pickObject`.
- [x] Update `tools/FORK_COMMIT.txt` with the preserved/clean-built state (this pass).
- [x] Keep a secure off-machine Git bundle as a fallback — bundle created (`72aa9fb0…`); **moving it off-host is the lone residual**. Not committed here (policy).

## Safe preservation commands (operator recipe, not executed)

```bash
git -C ~/duckstation bundle create /secure/off-machine/duckstation-external-debugger.bundle external-debugger-control
git -C ~/duckstation diff --binary HEAD > /secure/off-machine/duckstation-working-tree.patch
git -C ~/duckstation ls-files --others --exclude-standard > /secure/off-machine/duckstation-untracked-files.txt
```

## Status

**GAP-0001: Resolved on this host (2026-06-21).** The fork is preserved as a verified recoverable bundle + patchset + untracked archive (+ in-repo tag), an independent clone rebuilt `duckstation-qt`, and one headline experiment (`tools/trace_spawn_floor.py`) reproduced from that clean-built binary — all acceptance criteria met except physical off-host storage. **Lone residual:** replicate the preservation set off-host (operator credentials/ownership; `origin` is upstream). The recoverable mechanism exists and is verified locally; only off-site copy remains, which retires [[Blocker - Verification is bus-factor-1 on a private emulator fork|B2]] when done.

## GAP-0002 — findings-store overwrite hazard + fixture identity (Resolved on host 2026-06-21)

The canonical findings store `src_re_geometry/re_findings_backup.yaml` is git-tracked but historically had a documented overwrite footgun (`findings.save` clobbers it; you must `findings.load` first). The headline experiments also load **local-only** fixtures (saves/disc/movie) whose identity was not pinned. Both are now guarded:

**Findings-store guards (enforced in the safe suite = pre-commit gate):**
1. **Byte tamper-evidence** — `tools/verify_repro_inputs.py` hashes the store into `tools/repro_inputs.sha256`; `tests/test_repro_manifest.py` fails on any change (catches an accidental overwrite).
2. **Semantic tamper-evidence (new)** — `tools/check_findings_store.py` + `tests/test_findings_store.py` assert the *meaning* survives even if the byte-manifest is re-baselined: the YAML parses, **f13 is the sole CONFIRMED visible-floor answer**, f5/f10 are not, and f13 keeps its M7 evidence anchors (`trace_spawn_floor.py`, `trace_g29_pass3_arm_b.py`, collision sector-table SHA `6b7d858f…`).
3. **Load-before-save guard (new, code-level)** — `check_findings_store.py snapshot` (right after `findings.load`) then `guard-save NEW` refuses to promote a new store to the tracked backup unless it is byte-identical to the snapshot **and** passes the invariants (`--force` overrides). This guards the *promote-to-backup* step; it does not intercept the server-side `findings.save` in the fork.

**Operator workflow:** run `python3 tools/check_findings_store.py` and `python3 tools/verify_repro_inputs.py` before/after any session that may call `findings.save`; re-baseline intentionally (`verify_repro_inputs.py --write`) and re-run the safe suite.

**Fixture identity (hash-pinned):** every headline replay fixture is pinned in **`tools/fixtures.sha256`** (advisory: skip-if-absent, fail-on-drift) and documented in [[Fixtures Index]] with role / path / replay tool / regeneration route — covers the spawn-floor (`SCUS-94288_1.sav`), the G29 Pass-3 arms (shared spawn + from-boot movie + pristine disc), LEVEL02 (`SCUS-94288_3.sav` default + `level02.sav` evidence), and the pristine disc (`463102187c…`, matches [[Checksum Manifest]]). `tests/test_fixtures_manifest.py` validates the manifest and verifies present fixtures.

**No-forbidden-artifacts guard:** `.gitignore` now also excludes `*.png`/`*.bak`/`*.movie.json`/`*.loadlock`; `tests/test_no_forbidden_artifacts.py` fails the build if any disc/BIOS/save/memcard/screenshot/movie/dump is ever tracked (the codec oracles are allowlisted).

**Acceptance** (findings store tamper-evident; every fixture regenerable or hash-pinned) — **MET on host.** **Residual (→ GAP-0040, not GAP-0002-blocking):** the exact cold-boot frame/route to *regenerate* each `.sav` is UNKNOWN (hash-pinning satisfies the OR clause today), and the LEVEL02 default-vs-evidence fixture naming (`SCUS-94288_3.sav` ≠ `level02.sav`) should be reconciled.

## See also

[[DuckStation Fork Reproducibility]] · [[Fixtures Index]] · [[Checksum Manifest]] · [[DuckStation API Index]] · [[API - determinism]] · [[Playbook - Create a deterministic experiment]] · [[Toolchain Census]] · [[Preservation Policy]]
