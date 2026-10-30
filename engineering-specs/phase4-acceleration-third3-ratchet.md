# Phase-4 acceleration investments 7-9 hard-truth ratchet

## Scope

Review only the exact candidate implementing the external DuckDB/Parquet trace
warehouse, read-only binary schemas and deterministic fuzz harness, and hash-only
external-evidence content manager. The two accepted acceleration tranches remain
immutable. PCSX-Redux is out of scope. No verifier may launch, edit, rebuild, copy, or
kill DuckStation, and no real external evidence may be moved by this ratchet.

## Required identities

- Record the full candidate commit, accepted parent, dirty state, and exact pinned
  Python 3.14.5, PyYAML, pytest, Unicorn, and DuckDB versions.
- Provision a clean environment from `tools/requirements.txt`; DuckDB must resolve to
  exactly 1.5.5 and Unicorn to exactly 2.1.4.
- Verify pristine build identities read-only.
- Use a detached checkout and keep databases, Parquet, corpora, receipt sets, mutation
  copies, and caches outside Git.

## Trace-warehouse acceptance

1. Recompute `analysis/phase4_trace_warehouse_pilot.json` byte-for-byte.
2. Independently reproduce all four query packs and their synthetic results.
3. Build a disposable external database and Parquet set, reopen/query it, and verify
   its external manifest hashes every output file.
4. Reject incomplete/control-mismatched/truncated/error capsules, reproducibility
   drift, wrong capsule/tree bindings, partition hash/size/row drift, malformed rows,
   unknown domains/cohorts, traversal, symlinks, repository output, and collision.
   Top-level errors must be exactly empty, retained v2 rows may not inject undeclared
   status fields, integer fields reject booleans, and event frames must remain in the
   closed movie-relative boundary interval `[0, retained capsule frames]`. When the
   complete-set policy is enabled, bind the exact complete retained movie set: every
   retained movie appears exactly once across all capsule IDs and cohorts, with sorted
   missing/unexpected identity diagnostics before any output is created. Require canonical
   POSIX-relative partition spelling and reject repeated physical files, including
   hard links. Pin the complete recursively typed warehouse policy, including the
   complete/control requirements, domains, cohorts, limits, output contract, query
   definitions, and authority flags; `cross_movie` must count distinct movies.
5. Confirm extensions cannot auto-install/load and the engine is exactly DuckDB 1.5.5.
6. Confirm no real-capsule import, exact causality, campaign closure, or promotion is
   claimed by the synthetic pilot.

## Binary-schema and fuzz acceptance

1. Recompute `analysis/phase4_binary_schema_fuzz_pilot.json` byte-for-byte and validate
   all three `.ksy` documents independently.
2. Reproduce all 285 cases twice with no crash, timeout, output-limit escape, or
   nondeterminism; valid seeds must parse.
3. Reject schema ID/license/endian drift, processing/writable constructs, escaped or
   symlinked schemas, weakened limits, and non-synthetic retained-corpus policy. Pin
   `seed_table=le`, `level_raw_container=be`, and `level_raw_chunk=be` exactly.
   Also pin seed `424242`; input/output/case/time/memory limits
   `1048576/4194304/96/500/268435456`; the ordered schema declarations; the ordered
   `truncate`, `flip_bit`, `overwrite_u32_boundary`, `append_bytes` mutation set; and
   every authority boolean with exact JSON scalar types. Booleans never satisfy an
   integer field. File-loaded and caller-supplied in-memory policies pass through the
   same validator before any parser execution or corpus-output creation; a falsey
   supplied value never falls back to the retained policy.
4. Prove a hanging adapter is terminated, an unexpected base exception is classified
   as a crash, and declared decompression bombs are rejected before decoding.
5. Export a disposable AFL-style synthetic corpus externally; reject repository output,
   collision, and symlink redirection.
6. Confirm existing writers and retail-derived inputs are unchanged and no fuzz result
   has behavioral or promotion authority.

## External-evidence acceptance

1. Recompute both the 178-object hash-only registry and synthetic pilot byte-for-byte.
2. Confirm the registry contains no host-absolute path, evidence byte, availability
   assertion, secret, ALLMODS input, or public-remote instruction.
   The complete external-evidence policy is recursively exact: schema/hash/layout,
   copy count, remote kinds, physical-domain rules, media classes, backend settings,
   and every authority boolean reject missing, unknown, reordered-list, type, or value
   drift.
3. Independently verify two private copies in distinct failure domains. Local and
   removable roots must occupy distinct `st_dev` devices as well as distinct declared
   domains; caller labels cannot split one device. Private-annex roots do not count
   without a separately verifiable immutable remote attestation.
4. Reject tamper, missing object, wrong registry/hash/size/content path, traversal,
   symlink, canonical/inode aliases or overlapping roots, hard-linked physical copies,
   duplicate object/remote, public remote, and secret-bearing receipt. Registry and
   receipt top-level and nested contracts are exact. Byte/copy counts are strict JSON
   integers rather than booleans or floats, roles are non-empty strings, retained
   summary/authority/source fields are derived exactly, and no registry field may
   author preservation readiness.
5. Recompute a disposable capsule-manifest tree and runtime-SHA256SUMS tree.
   Bind each exact manifest SHA-256 into its tree object, require the manifest to
   cover every regular file other than itself, and reject undeclared files, missing
   files, noncanonical entries, special files, and symlinks recursively.
6. Confirm the git-annex plan executes nothing, initializes nothing, publishes
   nothing, and requires external receipts before availability is claimed.
7. Confirm the real registry honestly remains not preservation-ready until real
   receipts verify two independent copies of every object.

## Integration acceptance

- All new tools, outputs, schemas, tests, and notes are declared with no inventory gap.
- Focused tests, byte-exact retained artifact checks, inventory, vault validation,
  forbidden-artifact checks, pristine build identity, and a candidate-versus-parent
  safe-suite differential have no candidate-only failure.
- No DuckStation method/source/config/process, fixture, movie, save, capsule, receipt,
  campaign result, or accepted prior-tranche marker changes.
- Acceptance is external JSON using schema
  `abl-phase4-acceleration-third3-hard-truth-decision/1`, with an exact top-level
  contract, empty `gaps` and `required_inputs`, and accepted parent
  `f5f0b8ef3ec32fe9a32c3d6a9aa9ef06d70033cb`. `verified_at` must be a real
  timezone-bearing RFC3339 timestamp. The bank rejects unknown or missing fields,
  scalar/container type drift, an evidence-free result, and a parentless or
  wrong-parent result.
- The decision's exact evidence object must cover candidate/parent identities and
  isolation; pinned Python/dependency versions; byte-exact SHA-256 reproduction of
  all four retained artifacts plus the four warehouse packs, 285-case double fuzz
  replay, 178-object registry, and disposable external runs; the complete focused
  and integration check set; every exploit regression retained from all earlier audit
  rounds with an ordered, exact, non-empty, globally unique test-node catalog; and
  candidate-versus-parent safe-suite counts
  and identical failed-node-set hashes with no one-sided failure. Every required
  success or isolation boolean is literal JSON `true`; counts and exit codes are
  strict integers, never booleans. Only
  `tools/phase4_acceleration_third_bank.py` may replace the pending marker and
  frontmatter after this structured acceptance validates.
- Immediately before writing, the bank must verify exact `HEAD`, prove the pinned
  accepted parent is an ancestor of the reviewed commit, and require empty porcelain
  status for staged, unstaged, and non-ignored untracked changes. Ignored external
  support may remain present; an unrelated history or any Git-command failure rejects.
