---
kind: experiment
id: EXP_2026-07-15_phase4_manual_camera_controls
name: Phase 4 manual camera controls campaign
status: complete
date: 2026-07-15
confidence: confirmed
---

# Phase 4 manual camera controls campaign

## Question and identity

What owns pristine L1 reset/look and R1 lock, which typed state do they change,
where do special scenes override them, and how is that state retired?

- Generator `tools/phase4_camera_controls.py`, SHA-256 `16d37e6712012fbf664fd4075450a4c96faa60adccba5bbb0a02a3e6d5a9c527`.
- Evidence `analysis/phase4_camera_controls.json`, SHA-256 `b46154304f59454d96739ceeac0876815a5272d28ff4a61d7b2fc6b80af47ccf`.
- Pristine executable SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- Pinned from-boot LEVEL01 movie and all 19 gameplay saves are centrally
  declared in `analysis/phase0_2_external_fixture_set.json`.
- DuckStation revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`,
  release binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and 203-method source manifest.

The retained run used fresh config `/tmp/abl-phase4-i11-camera-final-s4znQn`,
port 26453 and an ephemeral token. It verified the pristine mounted CUE/BIN,
inspected all 19 save headers before load, and stopped only PID 699221 owned by
that config. Regeneration requires fresh isolation values:

`python3 tools/phase4_camera_controls.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Diagnosis and retained controls

Static xrefs restricted s32 mode `0x80082220` to reset clear `0x8004DD6C`, L1
mode-2 writer `0x8004DFF0`, R1 mode-3 writer `0x8004E070`, and neutral clear
`0x8004E09C`. The byte-matched reset/update region hashes are
`44ea612d99d94718a92fdadbda47b9f60225cc3e65d4fd744d699145b09943ce`
and `121e043eba504843e57ee8df295fa4e88607bc5fe75cc800c55409476e8c66ca`.
HUD reads were attributed to `0x800527F4/0x80052A40`.

Every control reloaded `level01.sav`. Neutral remained mode 0, distance 900,
and byte-identical camera output. L1 selected 2, moved distance in -32 steps
around target 600, and changed output. R1 selected 3, moved distance in +32
steps around 1400, moved vertical toward 24576, and left orbit yaw locked.
L1+Up reached vertical 32768; L1+Down reached 4096 and orbit bias 11520, within
one 2304 step of its 12288 request. Left/right produced signed pitch steps
+16/-16. Simultaneous L1+R1 selected L1 mode 2. Every release ended at mode 0,
distance 900, vertical 12288, orbit bias 0, and suppression high byte 0.

The from-boot campaign paused playback before advancing to an exact pre-edit
checkpoint. Both edited branches matched the same pre-edit camera bytes and
cycle. Adding only L1 at frames 8103..8162 ended in mode 2; adding only R1
ended in mode 3, and each output diverged from the unedited control.

The 19-anchor matrix found 17 ordinary 2/3 contexts, Bug Bar 2/0, and Riverbed
Flight 0/0. Bonus 2 selected mode 3 but its 16-frame output triple matched
neutral, an explicit scene-consumer exception. Pause froze the camera block.
Native fatal/respawn reset mode 2/distance 612 to 0/900, decremented lives,
and permitted fresh L1 re-entry.

## Failed hypotheses and corrections

- **The manual mode word is unbound:** false; it is s32 `0x80082220` with the
  four exact resident writers above.
- **Distance smoothers clamp exactly at 600/1400:** false; the native law
  enters a one-step neighborhood, so exact final equality is timing-dependent.
- **Manual modes apply uniformly to all gameplay anchors:** false; Bug Bar and
  Riverbed Flight form distinct 2/0 and 0/0 classes.
- **Mode selection guarantees immediate output divergence:** false; Bonus 2
  selects R1 mode 3 without a 16-frame position/target divergence.
- **Sampling a running movie after `advanceToFrame` is an atomic pre-edit
  proof:** false. Rejected runs exposed a race; the retained run pauses before
  movie advancement so the helper restores a frozen checkpoint.
- **Camera position/target is authoritative control state:** false; prior
  Phase-3 pokes decay and A17 changes the producer inputs instead.

Static census, causal cold boot, exact controls, writer/HUD attribution,
19-anchor exceptions, pause, release and native respawn jointly confirm A17.
No copyrighted fixture, BIOS, capture, credential, token, save, movie or disc
image is added. Canonical result: [[SYS_manual_camera_controls]].
