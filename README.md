> **Disclaimer:** Every step of this was used with AI. Some things may be inaccurate or false.

# A Bug's Life (PS1) — reverse engineering

Reverse-engineering notes, decompiled code and analysis for Disney·Pixar *A Bug's Life* on the
PlayStation (USA v1.0, `SCUS-94288`).

## What's here

| Path | Contents |
|------|----------|
| `ObsidianVault/` | The knowledge base (an Obsidian vault). `Canon/` holds findings about the original game (functions, memory, systems), `Experiments/` the runtime evidence, `Playbooks/` methods and the roadmap, `Mods/` notes on modification requirements. Start at `ObsidianVault/Home.md`. |
| `src/`, `src_re/`, `src_re_geometry/` | Decompiled and reconstructed C for game functions, with the original MIPS in the comments. |
| `analysis/` | Generated analysis artifacts: censuses, call graphs, traces, evidence JSON. |
| `tools/`, `tests/`, `config/` | Analysis and tracing tools (Python and C), most of them driving a custom DuckStation external-debugger fork, plus their tests and run configs. |
| `docs/`, `engineering-specs/` | File-format write-ups (LEVEL.DAT, LEVEL.RAW, overlays) and work orders. |
| `IDEA.md`, `ABL_RE_NOTES.md` | Project overview and the original index of findings. |

## Not included

No disc image, BIOS, executable, save states, input movies or extracted game assets. Files are
identified by SHA-256 only (for example `extracted/SHA256SUMS`), so reproducing anything needs your
own copy of the game. Paths such as `~/Downloads/ABL/...` refer to the original working copy, and
many tools expect the DuckStation fork and local evidence that is not published, so they will not
run as-is.
