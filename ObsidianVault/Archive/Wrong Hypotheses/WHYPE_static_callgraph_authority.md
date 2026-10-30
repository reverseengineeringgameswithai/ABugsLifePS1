---
kind: wrong_hypothesis
id: WHYPE_static_callgraph_authority
status: resolved_wrong
confidence: confirmed
resolved_by:
  - ObsidianVault/_Revamp/CONFLICTS.md
  - ObsidianVault/Canon/Systems/SYS_re_evidence_policy.md
  - ObsidianVault/Blockers/Blocker - Function boundaries and overlays evade the static call graph.md
---

# WHYPE_static_callgraph_authority

## Wrong claim

Static r2 function boundaries and `jal` call graphs are authoritative enough to treat as complete Canon.

## Resolution

Wrong. Static RE is a hypothesis layer unless supported by stronger evidence. Jump-table cases, overlays, and manually reconstructed C helpers can evade or distort a simple static call graph.

## Canon destination

- `Canon/Systems/SYS_re_evidence_policy.md`
