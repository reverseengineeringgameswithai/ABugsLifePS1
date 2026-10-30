---
kind: experiment
id: EXP_2026-07-15_phase4_event_vm
name: Phase 4 E07 event-VM closure
date: 2026-07-15
updated: 2026-07-16
status: reproduced
confidence: confirmed
source_state: original_game
system: SYS_event_vm_and_scripted_objects
artifacts: [analysis/phase4_event_vm.json, analysis/vm_programs.json]
---
# Phase 4 E07 event-VM closure

## Question and falsifiers

Does the pristine game expose a bounded, fully decodable resident event/mover
VM whose program selection, native calls, overlay meanings, and lifecycle are
safe for future consumers? The campaign would remain open if any opcode, valid
program start, CALL slot, applicable overlay target, actor/source owner, or
reset path escaped the retained frontier.

Specific falsifiers were:

- a selector-table boundary other than the byte-derived boundary;
- any opcode or CALL slot absent from all decoded programs;
- an unsigned branch target outside the program bank;
- one fixed meaning for a Region-A CALL VA across all images;
- a valid-source actor IP outside the decoded bank;
- selector 40 being rejected or clamped by retail; or
- pause, respawn, or scene reuse leaving stale VM ownership.

## Provenance and method

Static authority was only `REBUILD/files/SCUS_942.88` and the 20
`REBUILD/files/LEVELnn/LEVEL*.BIN` inputs after
the targeted `python3 tools/build_identity.py --verify ...` passed the resident
executable and all 20 overlay inputs (21/21). ALLMODS was not used as an input
or original-game authority. No disc build was performed in this correction.

Live work used the external-debugger fork revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, release binary SHA-256
`c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`, a
fresh `/tmp/abl-phase4-i1-e07-20260715-b` config, dedicated loopback port 19889, and the
hash-verified pristine retail CUE. The ephemeral token is not retained; its
hash and all process/toolchain provenance are in the artifact. The generator
stopped only PID 2263686 owned by that config. The replayed artifact also pins
the 203-method source manifest, 88-path dirty source identity, and current
release binary.

Before every state load, `emulator.getStateInfo` confirmed the centrally pinned
strict-pristine fixture and its embedded pristine media. Instrumentation was
re-armed after every load. The first 19 strict-pristine gameplay anchors cover
Training, stages 1–15, and bonuses 1–3.

Static reproduction:

```text
python3 tools/gen_vm_disasm.py
python3 tools/phase1_unclassified_inventory.py
```

Live reproduction used:

```text
python3 tools/phase4_event_vm.py --port 19889 --token <ephemeral> \
  --config-dir /tmp/abl-phase4-i1-e07-20260715-b --instance-state recreated
```

The cold-boot arm replayed `movies/go_to_end/LEVEL01.movie.json` from boot to
frame 8550, armed the fetch watch, then advanced to 8620. Save-state experiments
were separate and followed the pre-load inspections.

## Observations

Static observations:

- 40 selector pointers, 40 unique starts; following word `0x03020100`;
- 421 instructions; opcode indices exactly `0..25`;
- 13 CALL instructions covering slots `1..9`;
- signed branch `0x80077602 -> 0x800775FA` for operand `-5`;
- 20 pinned Region-A images, 19 non-stubs, and nine exact function bindings.

Live observations:

- cold boot: 83 fetch hits across the corrected 64-slot pool, scene 1, movie reproducible and not truncated;
- actor-pool bytes: `0x8004D248/24C` construct `0x8009FD80`, `0x8004D410`
  advances by `0x84`, and `0x8004D41C` loops while index is below 64;
- breadth: 19 anchors, 16 scene IDs, 37 naturally observed selectors, 37 fetch
  hits across six fixed windows, live-count range 1..64, and no valid-source
  actor IP outside the bank;
- selectors: `0 -> 0x8007745C`, `39 -> 0x80077AC0`,
  `40 -> 0x03020100`;
- pause flags `1,1,0`; paused and frozen actor hashes equal; post-resume actor
  hash changed even though that later 60-frame window did not fetch;
- fatal contact: lives `5 -> 4`, health restored to 4 at 180 frames, same scene,
  then four VM fetches in the re-armed 12-frame window; and
- scene reuse: scene IDs `1 -> 3 -> 1`, first/last actor-source maps equal and
  LEVEL02 distinct.

No full overlay image matched live RAM byte-for-byte after level activity; this
was retained, not hidden. Immutable entry bytes matched LEVEL01_LEVEL in scenes
1 and LEVEL05_LEVEL1 in scene 15, and the latter's exact CALL-5 function bytes
matched at `0x800B3BD4`. Static conclusions remain grounded in all pinned image
bytes; runtime identity claims are limited to those exact matches plus the
scene-qualified asset graph.

## Inferences

The resident VM frontier is complete and reusable. Program selection is a raw
unbounded source-byte table lookup, so validation is a MOD obligation. Overlay
CALL meanings are properties of an image/lifetime tuple, not virtual addresses.
Pause owns a freeze boundary; respawn and scene load rebuild/rearm transient
actor/script state.

## Failed hypotheses and corrections

- **Disproved:** the program table has 13 entries. That generator stopped early.
- **Disproved:** it has 17 entries. That legacy note also stopped early.
- **Disproved:** selectors 39 and 40 alias. Exact indexing shows 39 is the last
  valid pointer; 40 is `0x03020100`.
- **Disproved:** branch operands are unsigned. The `-5` control-flow target is
  inside the program bank.
- **Disproved:** every gameplay anchor must fetch within 12 frames. Thirteen
  windows were idle while their actor/source state remained valid; short-window
  silence is not absence.
- **Disproved:** a bare Region-A CALL address defines one native verb.
- **Disproved:** the 40-entry selector table also defines actor capacity. The
  independent fixed actor pool contains 64 records and begins one stride before
  the old `0x8009FE04` probe.
- **Disproved:** Bonus 2 has no live actors. A complete 64-slot read finds 32
  live records and nine fetches; the old observation began at slot 1 and stopped
  at the first zero hole.

## 2026-07-16 dependency refresh

Refreshing the Phase-3 overlay/scene graph changed only the pinned hash of
`analysis/phase3_overlay_map.json`, but the E07 artifact's static census consumes
that file directly. The artifact was therefore regenerated instead of editing
its fixture pin by hand.

The first fresh isolated run used the generic debugger config on port `19934`.
It mounted hash-verified pristine `SCUS-94288`, but the cold-boot window returned
42 VM fetches instead of the retained 83. That run was rejected. Its exact PID
`3636432` was stopped by owned cleanup, and no result from it was promoted.
This falsified the assumption that an otherwise isolated default execution
configuration was timing-equivalent for the boot movie.

The causal control used a second fresh config on port `19935`, with
CachedInterpreter execution and the pinned card seed through
`tools/launch_repro_playback.sh`. Media identity was reverified before the run.
It restored all retained predicates: 83 cold-boot fetches, 19 strict-pristine
anchors across 16 scenes, 37 selectors, 37 breadth fetches, selectors
`0/39/40 -> 0x8007745C/0x80077AC0/0x03020100`, pause freeze, four post-respawn
fetches, and identical LEVEL01 source maps across the LEVEL02 round trip. The
generator stopped only its owned PID `3636699`.

The refreshed artifact SHA-256 is
`6dbbe4042aea48d06a199aa51ba61d3a54f3603100046bded233fa1e026414c8`.
Its behavioral observations match the prior retained evidence; the material
machine change is the current overlay-map dependency hash
`457fd81b3565ddb754424505f067edf51b6401965ccc2c9ca68e33d6b593bb50`.

## 2026-07-17 date-bound dependency refresh

The safe suite regenerated the byte-pinned Phase-3 scene and overlay artifacts
after the local date boundary. The resulting semantic documents are unchanged,
but their retained `generated` fields and therefore exact dependency hashes are
new. E07 was replayed rather than having its source pin edited in place. The
first fresh generic config on port 20333 reverified the pristine retail CUE but
reproduced the already-known 42-fetch timing desync. It stopped only owned PID
274500 and was rejected. The accepted replay used the required
CachedInterpreter/card-seeded profile on fresh config
`/tmp/abl-phase4-i23-e07-cached-20339.DeSiks`, port 20339. It reproduced the
retained 83-fetch cold-boot result plus all breadth/control predicates and
stopped only owned PID 278731. The current overlay-map dependency is
`4226bdc21e9ef3eef2c6450519877eeb55c91c3691f287b6a7535dbb24d2f739`;
the accepted source-fresh E07 artifact is
`a764ba00a29c0b0cca1c997bb241db293fa4c112a6a588a57eb8dbf64a8596e6`.

## Result and handoff

E07 is complete for selection, interpreter, programs, CALL/motion dispatch,
overlay-target qualification, actor/source ownership and lifecycle. Downstream
damage, props/gates, rendering/assets, audio, persistence and objectives retain
their explicit campaign owners. See [[SYS_event_vm_and_scripted_objects]] and
[[Game Solving Campaign - Event VM and Scripted Objects]].
