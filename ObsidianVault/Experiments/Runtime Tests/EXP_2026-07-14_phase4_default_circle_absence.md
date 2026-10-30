---
kind: experiment
id: EXP_2026-07-14_phase4_default_circle_absence
name: Phase 4 default Circle absence
status: complete
date: 2026-07-14
confidence: confirmed
---

# Phase 4 default Circle absence

## Question

Does pristine gameplay under the default controller profile consume raw Circle, and
can the same method falsify a too-broad claim that Circle is always inert?

## Setup and identity

- Generator: `tools/phase4_circle_absence.py`, SHA-256
  `dcf75b2bc2a4b9b212bcd6f3cd7ffeff05caa5c98ea3a0e2c61ad883cf81329c`.
- Evidence: `analysis/phase4_circle_absence.json`, SHA-256
  `c96af4d2cbfe5089c5157ddbdff10c856bbbf53e71958a35b27d45c3ea490076`.
- Executable: pinned pristine `REBUILD/files/SCUS_942.88`, SHA-256
  `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
- DuckStation fork revision `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, release binary SHA-256
  `c668bf0974a7da5dabdbc4f1bd5311df3027e8af56faceb19ac7648f6f24ccec`,
  and 203-method API manifest semantic SHA-256
  `0f3e6a032a81318afaacbddf5512dd75d0e4fbcda0f4be91d1142acc83f15ed4`.
- Fresh absolute config `/tmp/abl-phase4-circle-i2b-2984332`, dedicated loopback port,
  ephemeral token, mounted-media verification, disc validation on every state load,
  and cleanup limited to the config-owned PID.

## Procedure

The static census verified the executable and every decisive decoder instruction,
then decoded all eight native profile-table rows. Before any load, the live run joined
each candidate save to the central fixture set, accepted 42 strict-pristine anchors,
rejected none, and inspected embedded media identity.

For each anchor, the run loaded the same state twice, forced valid native selector 0,
settled two frames, held neutral or Circle for 30 frames, released for two, and compared
player/camera block hashes plus typed player/outcome fields. It then access-logged the
decoded action-word writer for profile 0 and profile 1 controls.

Regeneration command (port/token/config must always be new):

`python3 tools/phase4_circle_absence.py --config-dir /tmp/<fresh> --port <dedicated> --token <ephemeral> --instance-state recreated`

## Observations

- 42/42 anchors observed raw pad bit `0x2000` during the Circle branch.
- 42/42 neutral/Circle branches had equivalent decoded action words.
- 42/42 branches had no player/camera/typed-field divergence after release.
- Profile-0 negative control: raw `0x2000`, decoded action bits `0x0000`, one retained
  decoder write at `0x800512D0`, no truncation.
- Profile-1 positive control: raw `0x2000`, decoded action bits `0x8000`, with the
  decisive second action write at `0x80051318`, no truncation.
- The exact owned PID was stopped; the retained cleanup predicate is true.

## Failed hypothesis and causal conclusion

“Circle is globally unused” is false: profile 1 provides a native positive control.
The narrower A20 statement is confirmed: default profile 0 omits Circle from all three
action masks and the live breadth sweep observes no gameplay action or outcome delta.
Changing only the selector to a valid native alternative produces the predicted action,
which causally separates a functioning pad/decoder path from profile-0 absence.

## Residual

Frontend selector writers, remap persistence, and menu exceptional paths were not
claimed. They remain in the HUD/frontend family. No copyrighted save, capture, movie,
BIOS, credential, token, or generated disc was retained.

Canonical conclusion: [[SYS_default_circle_input_absence]].
