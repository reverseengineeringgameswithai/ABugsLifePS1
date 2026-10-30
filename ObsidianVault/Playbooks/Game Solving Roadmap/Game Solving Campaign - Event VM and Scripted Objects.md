---
kind: campaign
id: event_vm
phase: 4
family: objects_events_hazards
rows: [E07_event_vm]
status: completed
evidence: [analysis/phase4_event_vm.json]
---

# Game Solving Campaign - Event VM and Scripted Objects

## Scope, non-scope, and owner

This `objects_events_hazards` campaign owns E07 selection, bytecode fetch and
dispatch, all resident programs/opcodes/CALL/motion tables, the scene-qualified
overlay CALL frontier, actor/source typed state, and pause/respawn/reload
lifecycle. It does not own enemy damage/death, prop/gate policies,
rendering/animation assets, audio outcomes, persistence/results, or stage
objective outcomes; those remain D, E03/E05/E08-E14, and F rows.

## Pristine oracle and original behavior

The executable SHA-256 is
`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.
Twenty level overlays and all 19 live anchors are centrally pinned. The v3
from-boot LEVEL01 movie produced 83 fetches across the corrected 64-slot pool.
Exact selector-only controls produced the first program, last program, and first
invalid table word.

## Complete semantic frontier

- functions: selector `0x80049C30`, interpreter `0x8004C13C`, motion apply
  `0x8004C8AC`, and nine CALL stubs;
- dispatch: 26 opcodes, nine CALL slots, 16 motion handlers, 40 selectors;
- programs: 421 fully decoded instructions and signed branch targets;
- overlays: every five-target intersection in all 20 pinned images, with nine
  exact function starts qualified by image;
- state: 64 actor records at `0x8009FD80` with flags/wait/IP/callback/source,
  plus source selector `+0x0D` into a separate 40-entry program table; and
- boundary: collision, animation, audio, objectives and consumer policies keep
  independent owners.

## Initialization, lifecycle, and capacity

Scene-owned source records initialize fixed actor records and seed the resident
IP through the unbounded selector table. Capacity is 64 actors and 40 valid
selector entries. Pause freezes actor state. Native respawn rearms execution.
Scene load rebuilds sources/actors; LEVEL01 reproduced after LEVEL02. Actor,
source, callback, target and Region-A references retire before their owners
unload. None is progression persistence.

## Positive and negative controls

Positive controls were selector 0, selector 39, cold-boot fetch, natural
six-context fetch, resumed actor progress, post-respawn fetch, and exact LEVEL01
scene rebuild. Negative controls were selector 40, paused actor freeze, explicit
13-context idle windows, and rejection of universal Region-A meanings.

## Breadth and exceptional paths

Training, stages 1–15, and all three bonuses provided 19 strict-pristine
contexts across 16 scene IDs. Thirty-seven selectors occurred naturally;
selector 39 was additionally controlled directly. All 40 programs are fully
decoded whether or not their high-level family nickname appeared at an anchor.
Thirteen short idle trace windows are retained as observations, not absence
claims. The corrected full-pool read finds 32 live actors and nine fetches in
Bonus 2; its former zero-actor result was a slot-1/first-hole census artifact.

## Cross-system contract

Consumers may rely on selector domain `0..39`, opcode domain `0..25`, CALL
domain `1..9`, signed branch operands, the independent 64-record actor pool, and
image-qualified overlay targets. They may not infer stable identity from actor
slot/source pointer/Region-A VA or assign downstream damage, audiovisual,
persistence, prop/gate, or objective outcomes to E07.

## Source and schema status

The interpreter has a byte-matched handwritten assembly build unit. No matching
C is claimed for selector/interpreter/motion. `src_re/enemy_ai_programs.c` is
documentation-grade semantic C. `config/phase4_event_vm.yaml`, actor/semantic
schemas, the baseline, campaign registry, finding registry and inventory carry
the machine contract.

## Findings, disproven hypotheses, and bounded residuals

Confirmed reusable finding: `event_vm_contract`. It supersedes the 13/17-entry
counts, unsigned branch decode, and universal overlay-verb claim. Short-window
silence and high-level selector-family nicknames remain bounded consumer work:
all valid-source IPs and all program signatures are already closed, so those
labels do not intersect VM behavior. Downstream subsystem outcomes retain
explicit row owners.

## Executable gate and exit decision

`tests/test_phase4_event_vm.py` recomputes static bytes, retained live
predicates, fixture provenance, campaign/finding assertions, schema agreement,
and mutation failures. The child campaign exits **completed** because no
unresolved selector, instruction, opcode, CALL, overlay target, actor/source
field, capacity, or lifecycle owner intersects the E07 producer conclusion.

Evidence: [[EXP_2026-07-15_phase4_event_vm]] ·
Canon: [[SYS_event_vm_and_scripted_objects]].
