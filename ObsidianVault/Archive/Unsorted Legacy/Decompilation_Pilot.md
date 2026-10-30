---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Decompilation Pilot.md
aliases:
  - "Decompilation Pilot"
migration_action: superseded
superseded_by:
  - SYS_executable_image
  - RE_BASELINE_INDEX
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Decompilation Pilot.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Decompilation Pilot
type: plan
updated: 2026-06-20
tags: [decompilation, milestone3, modding, gap-0021]
---

# Decompilation pilot — DAT parser/relocator

> M3 modding-grade pilot definition. A matching build was **not forced**: the current repository has no PsyQ compiler revision, splat configuration, linker script, object boundaries, or objdiff tool. The useful pilot substrate already exists as a validated behavioral reconstruction.

## Candidate

| Field | Value |
|---|---|
| Function | [[FUNC_8001CDC0]] / `0x8001CDC0` |
| Existing reconstruction | `src_re/dat_parser_8001cdc0.c` → `dat_parse_relocate` |
| Documented size | `0x60C` bytes (`0x8001CDC0…0x8001D3CB`) |
| Why it matters | It relocates the baked offsets that make safe type-`0x3F` insertion possible; a wrong model causes black screens/corruption |
| Modding evidence | `tools/dat_reloc.py` reproduces all 1,248 LEVEL01 relocation writes; append/rebuild regressions validate the tool path |
| Status | behavioral C **Verified for the relocation model**; matching compilation **Deferred** |

## Existing evidence

- full annotated control-flow reconstruction in `src_re/dat_parser_8001cdc0.c`;
- nine relocation-site model documented in `docs/DAT_FORMAT_AND_RELOCATION.md`;
- runtime/global links in [[MEM - DAT runtime memory map]], [[MEM - Trail and pass3 tables]], and [[Symbol Map Baseline]];
- production behavior mirrored by `tools/dat_reloc.py` and its local copyrighted-input regression path;
- runtime GP fixed at `0x80081D98`; known caller [[FUNC_8003CF2C]].

## Readiness audit

| Requirement | Current evidence | M3 decision |
|---|---|---|
| Function boundary | `0x8001CDC0–0x8001D3CB` (`0x60C` bytes), one resident caller at `0x8003D568` | Sufficient for a future local code slice; boundary is evidence-backed |
| Calling convention | PS1 MIPS register ABI observed: `a0` overwritten/ignored, `a1` output-buffer offset, `v0` output byte count; `$gp=0x80081D98` | Sufficient behavioral contract; exact compiler ABI/object metadata still unavailable |
| Inputs/outputs | Loaded DAT via `G_DAT_BASE_PTR`; rewrites nine pointer-site classes and builds type/output tables; return advances caller heap cursor | Strong modding oracle |
| Behavioral verification | 1,248 LEVEL01 relocation writes match `tools/dat_reloc.py`; append/rebuild regressions cover the production edit path | Useful independent equivalence check |
| Reconstruction | `src_re/dat_parser_8001cdc0.c` preserves load widths, signedness, branches, GP globals, and explicit unknowns | Existing safe C-like scaffold; not buildable PS1 source |
| Compiler/link context | Exact PsyQ/`ccpsx`, library/object revision, original flags, linker script, and object split unconfirmed | Blocks meaningful instruction diff |
| Diff tooling | No pinned/configured splat, objdiff, asm-differ, or MIPS compiler | Blocks repeatable compile/diff |
| Legal boundary | Locally derived function bytes may be compared but not committed; reconstruction/config/tests may be tracked | Clear; no extracted object added |

## Why no compile/diff scaffold was added

Current tool discovery found radare2 5.9.8, but no configured `splat`, `objdiff`, `asm-differ`, MIPS cross-compiler, PsyQ/`ccpsx`, linker script, or object/library map. Exact original PsyQ release/object revisions remain unconfirmed. Adding an arbitrary modern compiler scaffold would measure compiler differences rather than improve modding reliability.

The C is intentionally interpretive: absolute-address lvalues, external stubs, and behavior-oriented names. Host compilation can check syntax but cannot establish PS1 ABI/code equivalence. A real diff also needs the function's original object/code slice and relocation/link context, derived locally without committing copyrighted bytes.

## Minimal next action

1. Preserve the DuckStation fork enough to trust `debugger.functionBounds`/symbol import, or verify bounds independently in r2.
2. Pin a decomp toolchain only when it serves a concrete modding regression. Preferred first comparison target remains `0x8001CDC0` because its behavior has an independent Python oracle.
3. Create a local-only split of `SCUS_942.88` and a small build definition; commit only configuration/original reconstruction, never extracted object bytes.
4. Compare compiler candidates against the function; record instruction/stack/register differences.
5. Gate promotion on both a code diff and existing `dat_reloc` behavioral tests.

## Future pilot success criteria

A later compile/diff pilot succeeds only when all of the following are recorded:

1. pinned compiler/diff-tool versions and build flags;
2. a local-only function/object slice whose SHA-1 and address range match SCUS-94288;
3. a build producing a comparable MIPS object without committing original bytes;
4. an objdiff/assembly report with honest match percentage and register/stack differences;
5. the existing 1,248-site relocation oracle still green;
6. a documented modding payoff, such as catching a relocation regression or validating a changed parser branch.

Compiler experimentation without items 2, 4, and 6 is not M3 work: it would create infrastructure without improving the declared modding target.

## Final M3 decision

The minimum safe pilot **is finalized as a behavioral/decomp scaffold**: selected function, verified boundary/ABI contract, C-like reconstruction, independent oracle, legal boundary, build plan, blockers, and future success criteria are all explicit. A real compile/objdiff was not feasible or useful with the current evidence and was not fabricated.

**GAP-0021: Deferred — payoff-gated under the modding-grade charter** (reaffirmed 2026-06-21; [[Gap Audit|GAP-0043]] reconciled). It is not Verified. Return only when the missing pinned toolchain/object context **and a concrete modding payoff** exist — none is identified today (LEVEL01 modding ships via DAT/RAW edits + behavioral RE + live tracing), so the deferral stands. No unsafe artifacts or speculative toolchain versions were added.

## Related

[[Roadmap]] · [[Symbol Map Baseline]] · [[MEM - Global memory map]] · `docs/DECOMPILATION_PLAN.md` · `docs/DAT_FORMAT_AND_RELOCATION.md` · `src_re/dat_parser_8001cdc0.c` · `tools/dat_reloc.py`
