---
kind: experiment
id: EXP_2026_07_14_phase3_iteration9_rpc_manifest_freshness
status: reproduced
created: 2026-07-14
updated: 2026-07-14
confidence: high
related:
  - PLAYBOOK_game_solving_phase_3
  - DUCKSTATION_API_INDEX
  - EXP_2026_07_14_phase3_iteration8_render_replay_durability
---

# Phase 3 iteration 9 — exact DuckStation RPC manifest freshness

## Trigger and authority

The fresh iteration-1 verifier rejected candidate
`76d75ecb5effd7d7ba0ee6c51212878ae03b37d7`. Direct enumeration of
`~/duckstation/src/duckstation-qt/debuggerrpc.cpp` produced 191 current RPC methods,
but `tools/duckstation_rpc_method_manifest.md` retained an obsolete 141-method
snapshot at revision `296955321fd9375fa94692d96df788eccd708135`, while
[[DuckStation_API_Index]] said 143. The accepted Phase-3 live artifacts instead name
revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` and the current dirty layer.

The acceptance contract SHA-256 was
`538666948ed9731e52fa657080a27f1b60f1b8ec931d79c0b22aa991698c7463`.
This repair inspects debugger source/toolchain identity only. It makes no
original-game behavioral claim, does not build or patch retail media, and does not
use ALLMODS as authority.

## Observation, inference, and causal confirmation

**Observation.** A brace-bounded extraction of `IsKnownMethod` from the current
dispatcher returns 191 unique methods. Repeating it on the Git HEAD version returns
114. The set difference is 77 dirty-only methods and the reverse difference is empty.
The current request-dispatch function contains the same 191 unique handler branches;
HEAD contains the same 114 as its allow-list. The external fork has 82 porcelain
status lines.

**Inference.** The old Markdown/Canon count describes a historical debugger
preservation milestone, not the binaries and APIs used by Phase 3. A Git revision
alone cannot identify an uncommitted API layer, and a prose count cannot guard it.
The durable representation must retain the method sets, complete dirty-status hash,
source/doc/client hashes, and exact binary hashes, then compare them against the
current fork during local validation.

**Causal confirmation.** `tools/phase3_duckstation_rpc_manifest.py` extracts both
allow-lists and dispatch-handler sets, refuses disagreement or duplicates, writes
`analysis/phase3_duckstation_rpc_manifest.json`, and deterministically renders
`tools/duckstation_rpc_method_manifest.md`. Its `--check` mode re-extracts
`~/duckstation` without writing and compares all retained semantic fields. The safe
guard deletes a dirty-only method and changes Canon identity in memory, then proves
the low-level set and linkage checks fail. A gate falsification changes the retained
count and proves `debugger_api_documentation.met` becomes false.

## Exact retained identity

- Fork revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`.
- Branch: `external-debugger-control`.
- Dirty status: 82 paths; SHA-256
  `0cc976e6940bcd551268d507fec764b867f26d73e4332cdfc036f4fce426b769`.
- Dispatcher SHA-256:
  `16f271258a614be46b17f3d444f779402f937c0622c77e136a36f8ae0f984e4a`.
- Dispatcher-at-HEAD SHA-256:
  `d7cd3dbe3a0bbe22871bfd412c21b76f8ad7fb55f8d154c6e37e113d48347ae3`.
- Dispatcher dirty-patch SHA-256:
  `0b8c747af8466cdd89c45edfb8acc68f26aa19e3b31d2270c9ae45a9fcbb65e4`.
- Normal binary SHA-256:
  `ebcfaf3c1dfd69df79bc1859c965f2b65b2e3c91d6e3f2e8c52dfe364bd7cae9`.
- Release binary SHA-256:
  `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.
- Method census: 114 committed + 77 dirty-only - 0 removed = 191 current.

The machine artifact also pins the four `external-debugger*.md` documents, debugger
client README, isolated launcher, and Python client by size and SHA-256. The complete
dirty status and all method names are retained without tokens, media, saves, movies,
captures, or credentials.

## Reproduction and validation

Direct source check:

`python3 tools/phase3_duckstation_rpc_manifest.py --check`

Observed: `FRESH: 191 methods at fe0cca16... with 82 dirty paths`, exit 0.

Focused guards:

`python3 -m pytest -q tests/test_phase3_duckstation_rpc_manifest.py tests/test_phase3_contradictions.py`

Observed: 9 passed. The ledger recomputed 5 reconciled, 6 bounded, 0 open.

Worktree matrix:

- `git diff --check`: exit 0, no output.
- `python3 tools/build_identity.py --verify`: PASS, 327/327 staged inputs.
- `python3 tools/knowledge_closure_audit.py --write`: 932 preservation fixtures,
  zero missing pins, untracked imports, source-pin errors, local-media errors,
  local-manifest errors, unpromoted addresses, or matrix errors.
- `python3 tools/phase3_knowledge_audit.py`: 19/19 findings FINISHED, 0 gaps.
- `python3 tools/phase3_gate_audit.py`: MET; WP1-WP9, inventory, upstream
  durability, decisive evidence, exact debugger documentation, and all five exit
  bullets recomputed from low-level inputs.
- Mandatory ownership/xref/dispatch/`jr`/overlay/record/hook generators: 107/107
  mechanic rows and zero ownership gaps; 40/63 statically referenced semantic
  entries and zero real writer contradictions; 44/44 dispatch slots; all 95 `jr`
  sites bounded; 20 overlays; 8 record views with 181/524-byte accounting; 15
  hooks comprising 5 proven + 10 discharged and zero degraded, unverified, owed,
  refused, or hard-violation rows.
- Remaining static/local generators: 327 assets/12 required roles with zero hash
  gaps; 1,112-function caller/callee graph; 134 native domains with zero independent
  errors; 15/15 scenes cross-verified; 11 contradiction rows (5 reconciled, 6
  bounded, 0 open); 29/29 generators and 30/30 artifacts closure-ready.
- `python3 mod/build.py --mods mod/mods_code_only.yaml --no-disc`: 1,195 EXE
  bytes changed; output SHA-1
  `5936596c576415847b3a7395599e993b36eb7906`, SHA-256
  `991fc38c131fe1139df30e9719a222a06a140054f1f8ee46b6321bbd9c0e6808`.
- `python3 tools/run_safe_tests.py`: 377 passed, 29 expected marker deselections.
- `python3 -m pytest -q -m local_media`: 28 passed, 378 deselected. This includes
  the fresh extraction against the exact external DuckStation worktree.
- `python3 -m pytest -q tests/test_phase1_*.py tests/test_phase2_*.py`: 61 passed.
- Final worktree `git status --short`: empty after deterministic regeneration.

The separately provisioned final-commit checkout reproduction and its exact path,
input count, and clean status are recorded in the next subsection after it completes.

## Clean-checkout reproduction

Candidate `aaac362656e70cb8365bb0e64cb9c21d5fb36cd7` was cloned with
`git clone --no-local` into `/tmp/phase3-i9-clean-mouNyT`. External bytes were
introduced only by:

```bash
python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL
python3 tools/provision_clean_checkout_inputs.py --operator-root ~/Downloads/ABL --verify-only
```

The first command copied exactly 1,262 centrally declared inputs; the second
verified 1,262/1,262. Class counts were 3 pristine media files, 327 pristine
staged inputs, 63 non-pristine fixtures, 127 pristine fixtures, 63
pristine-serial fixtures, 651 derived-retail assembly files, 3 derived-retail
disassembly files, and 25 derived-retail metadata files. Nothing outside the
central plan was provisioned.

The complete static/local generator matrix then reproduced the worktree counts
and hashes. `phase3_duckstation_rpc_manifest.py --check` returned the exact 191
methods/82-path dirty layer; build identity returned 327/327; the diagnostic build
returned both expected hashes; hook contracts returned 5 proven + 10 discharged;
knowledge returned 19/19 with zero gaps; inventory returned 29/29 generators and
30/30 artifacts closure-ready; WP1-WP9 and the gate returned MET. Retained live
artifacts were accepted only through their exact generator/shared-helper,
source/binary, pristine media/state, completeness, pagination, truncation, and
behavioral predicates; no live source dependency changed in iteration 9.

Serialized clean-checkout suites:

- `python3 tools/run_safe_tests.py`: 377 passed, 29 deselected.
- `python3 -m pytest -q -m local_media`: 28 passed, 378 deselected.
- `python3 -m pytest -q tests/test_phase1_*.py tests/test_phase2_*.py`: 61 passed.
- Final `git diff --check` and `git status --short`: empty after regeneration and
  both builds/tests.

The evidence-only final note commit was rechecked from a new checkout before closure;
it does not change any generator, artifact, guard, binary input, or low-level claim.

## Knowledge placement and residual

Toolchain/source identity and operating guidance belong in
[[DuckStation_API_Index]]; this Experiment retains the verifier trigger, failed old
surface, inference, causal guard, and exact reproduction. No MOD-private state or
intended behavior changed.

The current dirty debugger layer remains explicit rather than being described as a
clean commit. Future debugger changes must rerun `--check`, regenerate both artifacts,
and revalidate every retained live claim whose methods or binary identity changed.
