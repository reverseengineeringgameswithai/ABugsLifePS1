# PS1 RE/MOD investigation and regression framework

Status: architecture proposal, 2026-07-11

## Existing foundation to extend

- `tools/abl_dbg.py` is the project RPC seam over the fork's
  `duckstation_debug_client.py`; the runner should import that client rather than add a
  transport.
- `tools/launch_repro_playback.sh` is the proven cold-boot profile for the existing
  from-boot movies. It pins CachedInterpreter, BIOS behavior, controller type, and a
  freshly seeded isolated memory card. The generic fork launcher remains appropriate
  for fixtures that do not depend on that recording profile.
- `mod/smoke_test.py` already proves the useful BOOT/ALIVE/RENDER/WALK behavioral
  checks, but its lifecycle, addresses, and flow are hard-coded. It remains a fast
  smoke gate while its checks become reusable scenarios incrementally.
- `tools/scenarios/*.json` are specialized G3 authoring-campaign manifests. They are
  not debugger scenarios and will not be rewritten; debugger scenarios live below a
  named subdirectory so both formats remain unambiguous.
- `analysis/memory_map.json` and `mod/mods/registry.py` already reject several unsafe
  cave placements. A hook/cave manifest will add instruction-level contracts and will
  cross-check, not replace, those sources.
- `tools/fixtures.sha256`, `tools/repro_inputs.sha256`, the tracked input movies, and
  the existing live tests establish the repository's local-media and provenance
  conventions.
- Canon separates confirmed original behavior from experiment evidence and MOD
  behavior. The framework will preserve that boundary and will not generate Canon
  claims from a passing test.

## Proposed shape

1. `tools/ps1_scenario.py` provides schema loading, isolated lifecycle ownership,
   DuckStation RPC execution, triggers, capture, assertions, and JSON/Markdown reports.
   `tools/run_ps1_scenario.py` is its small command-line entry point.
2. `tools/scenarios/duckstation/` holds readable YAML scenarios. A scenario names its
   disc/movie or save anchor, timing profile, instrumentation, ordered phases, evidence
   captures, and behavioral assertions. Raw RPC calls are an explicit extension point,
   but common frame/memory/register/breakpoint/trace/capture operations are typed.
3. Every live run receives a fresh absolute temporary config directory, an available
   loopback port, and a random token. The runner records the process/config identity and
   stops only through the same config directory. Reports default to `/tmp`; no media,
   saves, captures, or tokens are committed.
4. `config/semantic_state.yaml` is the single curated semantic registry. Entries carry
   a namespace (`original`, `mod_private`, or `hypothesis`), kind, address, width,
   owner, writers, invariants, confidence, and evidence. A helper validates it and can
   emit review-only ASM, C, scenario, or Obsidian-table snippets to stdout or a new
   explicit output path; it never overwrites authored files.
5. `mod/hook_caves.yaml` declares module allocations, hook sites, expected displaced
   bytes, resume/delay-slot contracts, clobbers, forbidden regions, and supported module
   combinations. `tools/validate_mod_layout.py` validates declarations alone and, when
   given pristine/patched executables, proves actual changed bytes stay inside declared
   hooks/caves and expected displaced bytes match. `mod/build.py` calls this validator
   for selected code modules before disc staging.
6. Unit tests use fake clients/processes for schema, assertions, lifecycle ownership,
   cleanup, and overlap checks. Live/local-media scenarios remain explicit opt-ins.

## Incremental delivery

The first vertical slice is one cold-boot movie scenario, one frame trigger, one typed
memory assertion, isolated launch/cleanup, and dual reports. Once it passes end-to-end,
the same phase model expands to conditional breakpoints, access/function traces, atomic
captures, GPU/audio predicates, screenshots, hit counts, registers, and render diffs.
Existing high-value reproductions are converted only where their movie/anchor still
reaches the intended state; an unsuitable movie is documented and replaced by the
smallest owner-local fixture or input segment needed.

## Verification contract

- Record the repository/fork revisions, dirty status summaries, binary/disc/movie
  hashes, serial/media identity, timing profile, anchor type, frame/cycle, assertions,
  cleanup result, and exact divergence values.
- Run the safe suite and consolidated MOD build before and after integration; retain
  unrelated baseline failures separately.
- Run behavioral scenarios from a freshly rebuilt disc and preserve reports in `/tmp`.
- Exercise one expectation override that must fail, and require the report to name the
  assertion, address/source, expected value, actual value, and comparison.
