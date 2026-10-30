---
kind: session
id: SESSION_2026-07-08_re_basics_baseline
name: RE basics baseline — consolidation, PsyQ signatures, Canon homing
date: 2026-07-08
---

# Session 2026-07-08 — RE basics baseline

Executed plan `~/.claude/plans/delightful-brewing-pinwheel.md`: make every RE-basics
checklist item done, reproducible, and Canon-homed per the new vault philosophy.

## Decisions (operator, 2026-07-07)
1. Disc hashes **assumed-canonical** — no online Redump cross-check (legal dump, never distributed).
2. Disassembly/strings/listings **script-generated, untracked** (`extracted/re_baseline/`); only script + counts committed.
3. PsyQ identification = **full signature matching** (not a light strings pass).
4. Archived `needs_review` RE-basics notes **promoted** into new Canon notes.

## Done
- `tools/disc_provenance.json` (machine-readable manifest, recovered from the
  git-HEAD-only Checksum Manifest) + `tests/test_disc_provenance.py` (4 pass).
- `tools/re_baseline.py` — one-shot regeneration: provenance PASS, exe map asserts,
  837 r2 functions / 3,728 strings / full listing, 21 overlays, codemap 79.4%+5.3%,
  merged inventory 1,170 addrs / 687 named.
- PsyQ pipeline: ghidra_psx_ldr 2026.07.02 on Ghidra 12.1.2 Flatpak, new ABLPsx
  project, **PsyQ 4.0.0 detected**, 644 EXE-range matches,
  `tools/merge_psyq_symbols.py` → `re_symbols.sym` 129 → **761**.
- **Correction:** `0x8006B1C0` was mislabeled `SsVabTransBody`; real name
  `SsVabOpenHeadWithMode`, real `SsVabTransBody` = `0x8006B59C`
  ([[EXP_2026-07-08_psyq_signature_match]]).
- Canon notes: [[SYS_game_identity_and_provenance]], [[SYS_executable_image]],
  [[SYS_overlays_and_runtime_loading]], [[RE_Baseline_Index]]; `ghidra/README.md`
  gained the ABLPsx section.
- Evidence: [[EXP_2026-07-08_re_baseline_run]], [[EXP_2026-07-08_psyq_signature_match]].
- Archive promotion: RE-basics legacy notes marked superseded (see Archive frontmatter
  `superseded_by`).

## Follow-ups
- Review hand names inside the library region: `frame_render_driver@0x80062C70`
  (psyq PutDrawEnv), `gpu_present_drawotag_vsync@0x800646B8` (psyq _addque2).
- Optionally re-point `src_re/sfx_system.c` comments at the corrected SsVab names.
