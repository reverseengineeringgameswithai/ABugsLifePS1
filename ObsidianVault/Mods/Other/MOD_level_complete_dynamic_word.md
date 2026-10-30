---
kind: mod
id: MOD_level_complete_dynamic_word
created: 2026-07-11
updated: 2026-07-11
status: runtime_verified
---

# MOD - LEVEL COMPLETE dynamic word

The active implementation is `tools/training_word_pickups.py`; its policy model is `mod/caves/training_result_word.c` and its retail/source reconstruction is `src_re/level_complete_results_800b7da0.c`.

The GUI spelling order is the source of truth. ALLMODS currently stages `FLIK` for Ant Hill/default and `TRAINING` for Training. Gameplay retains an origin selector at `0x800813E8` because the shared result overlay clears `current_scene_id`. `BITS/MEMORY.BIN` dispatches to FLIK/Training RAW blobs, and those blobs use ordered source tables plus private per-slot descriptors on tpage `0x0f`.

The result row starts at screen X `2` and advances `14` units per letter. The start was moved six units left from its initial X `8` after visual review. The stride replaces the initial `10`-unit spacing, whose widest spinning frames slightly overlapped, while retaining the compact eight-letter layout and dynamically positioning the counter after the word.

The objective counter uses a separate X offset of `-4`, moving `0/4` or `0/8` four units left without changing any letter positions.

Do not re-enable `flik_emblem_training_result` on `LEVEL00/LEVEL2.RAW` for this path: it is a global composite-image replacement and cannot select a word by origin. The generated row owns LEVEL COMPLETE spelling; level-local emblem images remain separate assets.

`tools/mod_studio_gui.py` follows this rule: its Training spelling field emits the wired `training_word_pickups` manifest entry, which owns the pickup, SELECT, and LEVEL COMPLETE order, while its Training emblem picker emits only level-local/in-game emblem layers. The GUI no longer regenerates the obsolete shared `flik_emblem_training_result` entry when saving `mod/mods.yaml`.

See [[EXP_2026-07-11_level_complete_dynamic_word]] and [[SYS_level_results_screen]].
