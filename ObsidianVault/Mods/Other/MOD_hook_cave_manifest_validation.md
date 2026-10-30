---
kind: mod
id: MOD_hook_cave_manifest_validation
name: Declarative hook and code-cave validation
status: integrated
created: 2026-07-11
updated: 2026-07-11
source_state: mod_infrastructure
artifacts:
  - mod/hook_caves.yaml
  - tools/validate_mod_layout.py
  - mod/build.py
  - config/semantic_state.yaml
evidence:
  - EXP_2026_07_11_ps1_scenario_regression_framework
  - EXP_2026_07_10_blackberry_throw_cave_overlap_crash
playbooks:
  - PLAYBOOK_mod_regression_troubleshooting
---

# Declarative hook and code-cave validation

`mod/hook_caves.yaml` is the machine-readable instruction-level contract for the
manifest-driven resident EXE modules. It complements `mod/mods/registry.py` and
`analysis/memory_map.json`; it does not replace module selection or the runtime
used/free map.

The manifest declares exact half-open allocations, forbidden/runtime-owned ranges,
supported enabled-module combinations, hook addresses, pristine displaced bytes,
resume addresses, delay-slot policy, register clobbers, and data patches.

The consolidated build now validates three layers before disc staging:

1. declarations, module combinations, allocation/forbidden/runtime overlaps, and
   registry-to-manifest range agreement;
2. each armips module assembled alone against pristine, proving its changed bytes
   remain inside that module's hooks/patches/allocations;
3. the composed executable, proving displaced bytes still match and all combined
   changes remain declared.

This closes the class demonstrated by the 2026-07-10 Blackberry throw crash, where
an emitted golddrop tail crossed its declared end and landed inside the adjacent
Blackberry cave. Existing post-assembly semantic signatures remain as independent
defense-in-depth checks.

The semantic registry's `mod_private` namespace records Blackberry-owned state
separately from original-game fields. Generated ASM/C snippets are never written into
hand-authored sources automatically.

For the operational order of build-time validation, scenario replay, and targeted
runtime diagnosis, see [[Regression Troubleshooting Playbook]].
