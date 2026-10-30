# ABL repository workflow

- Preserve operator work. Inspect `git status --short` before editing, never reset or
  overwrite unrelated dirty files, and keep generated discs, saves, captures, tokens,
  and copyrighted assets out of commits.
- Treat the hash-verified pristine retail image as immutable and as the sole patch/build
  base. Never patch ALLMODS, another existing MOD image, or any prior derivative.
  For every experiment or module combination, verify the pristine input hash, copy it
  to a new output, and apply the selected changes once in that build. ALLMODS may be
  inspected or replayed only as historical regression/comparison evidence, never as an
  input to a new patched image. Enforcement (Phase 0): `tools/build_baselines.json`
  pins every REBUILD/files input (`tools/build_identity.py --verify`); `mod/build.py`
  refuses non-pristine staged inputs, protected-output overwrites, module combinations
  absent from `mod/module_matrix.yaml`, and `_REL`-named outputs without
  `--profile release`; every disc build emits `<out>.build_manifest.json` naming its
  exact inputs, module set, toolchain, and output hashes.
- Run DuckStation work in a freshly created absolute config directory with a dedicated
  loopback port and token. Verify media identity after connecting. Stop only the PID
  owned by that config directory; never use broad process-name kills or the normal user
  profile.
- Treat cold boot and save-state validation as different evidence. Use a cold boot plus
  a timing-matched input movie for disc/code/asset changes. Use named, hash-pinned save
  states for narrow runtime experiments only after validating their media; re-arm all
  instrumentation after every state load.
- Diagnose before patching. Capture identity, trigger, frame/cycle, registers or memory,
  relevant trace limits, and the observed divergence before changing code. Keep
  observation, inference, and causal confirmation distinct.
- Convert a stable reproduction into the smallest declarative DuckStation scenario and
  behavioral assertion that would have caught it. Store transient evidence under `/tmp`
  and record hashes/commands in the relevant note.
- For repeated mathematical analysis of a pinned movie, a verified persistent trace capsule may be stored under the
  declared external-evidence root and queried without replaying DuckStation. Accept it only when its manifest reports
  no truncation/error, its RAM/VRAM/SPU/register/full-state fingerprint matches an independent pristine-media control,
  and its fixture/source/binary hashes are present. Capsules, checkpoints, saves, and movies remain external; commit a
  central hash/preservation manifest and link it from the relevant Experiment/Canon evidence instead.
- In Phase 4, validate and query a relevant retained trace capsule before starting another live replay. Use offline
  register/RAM/VRAM/SPU reconstruction and block-flow analysis when those domains answer the question. Escalate to an
  isolated DuckStation API run only for a named missing domain, exact instruction/DMA/GPU/SPU attribution, a required
  behavioral control, or a missing/invalid capsule, and record that reason. A capsule is frame-boundary evidence—not
  every-cycle evidence and not an automatic campaign-closure claim.
- Keep confirmed original-game behavior and provenance in `ObsidianVault/Canon`, runtime
  experiments and framework results in `ObsidianVault/Experiments`, and MOD-private
  state, hooks, cave allocations, and intended behavior in `ObsidianVault/Mods`.
- Validate MOD changes with the safe tests, hook/cave validator, consolidated build, and
  relevant cold-boot scenarios. Do not treat patched bytes alone as a behavioral test.
