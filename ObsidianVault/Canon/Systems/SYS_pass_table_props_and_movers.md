---
kind: system
id: SYS_pass_table_props_and_movers
name: Pass-table props and scene-owned movers
status: live_confirmed_partial
confidence: confirmed_with_open_consumers
source_state: original_game
functions: [0x8001CDC0, 0x800140A0, 0x80014360, 0x80049C30, 0x8004B940, 0x8004D224]
evidence: [EXP_2026-07-15_phase4_props_movers_catalog, EXP_2026-07-30_phase4_e08_original_oracle, EXP_2026-07-30_phase4_e08_class_frontier]
src_paths: [config/phase4_props_movers.yaml, config/phase4_e08_oracle_audit.yaml, config/phase4_e08_class_frontier.yaml, tools/phase4_props_movers.py, tools/phase4_e08_oracle_audit.py, tools/phase4_e08_outcome_join.py, tools/phase4_e08_operator_contacts.py, tools/phase4_e08_hazard_outcomes.py, tools/phase4_e08_class_frontier.py, analysis/phase4_props_movers.json, analysis/phase4_e08_oracle_audit.json, analysis/phase4_e08_outcome_join.json, analysis/phase4_e08_operator_contacts.json, analysis/phase4_e08_hazard_outcomes.json, analysis/phase4_e08_class_frontier.json]
---
# Pass-table props and scene-owned movers

## Bounded original-game oracle

The E08 original oracle is confirmed for the centrally pinned pristine
from-boot LEVEL01 movie at frames 8550 through 8580. Mounted-media inspection
identified `SCUS-94288` and matched both retail CUE/BIN pins. The reproducible
non-truncated run remains in scene 1 with 484 pass-1 rows, 140 pass-3 rows and
the 64-record actor capacity.

Three phase-matched controls distinguish the observed rendering contract:
pass-1 payload replacement changes 2,872 pixels, pass-3 bitmap suppression
changes 5,938, and a cull-preserving pass-3 anchor nudge changes zero. Each
paired branch preserves collision and player state. Six retail executable
regions bind the parser, cullers and mover update surface.

This is an original-oracle fact, not whole-row closure. Interaction ownership,
authored switch/gate state, denial/success, lifecycle and persistence remain
open, and E10/D11 movie coupling confers no species or hazard owner.

## Confirmed original-game records

Every one of the 21 hash-pinned staged `LEVEL*.DAT` inputs was parsed with the
retail `0x8001CDC0` table arithmetic. Together they contain 9,097 pass-1 rows
and 1,684 pass-3 rows. Both use a `0x14`-byte record:

```text
+00 s32 X   +04 s32 Y   +08 s32 Z
+0C s16 extent          +0E u16 flags
+10 u32 source pointer  ; signed flags bit 15 terminates the table
```

The nested payload pointer is at `source+0x14`, or `source+0x1C` when flags bit
`0x08` is set. Most pointers name bytes inside the owning DAT. Retail also has
two external source rows and 114 corresponding external payload cases: one
positive-external source, one negative-relative source, 112 negative-relative
nested payload values, and two payloads unresolved because their source is
external. Hash-pinned enumeration confirms these are input classes to preserve,
not evidence of parser corruption.

## Pass-1 and pass-3 meanings

The pass-1 runtime pointer is read from `0x800824AC`; `0x800140A0` consumes the
instances. In the pristine acorn fixture, replacing record 214's source pointer
with record 117's source changed 2,872 of 114,464 displayed pixels after a
20-frame matched branch. The collision-sector hash and player position stayed
equal. Pass-1 therefore supplies a per-frame visual source/model handoff
separate from collision.

The pass-3 runtime pointer is read from `0x80082508`. Culler `0x80014360` reads
the enable bitmap downward from `0x800902C7`: record `i` uses byte
`0x800902C7-(i>>3)` and mask `0x80>>(i&7)`. Clearing all active LEVEL01 bits
changed 5,938 pixels with collision and player state unchanged. Nudging visible
record 61's X anchor by 32 preserved its membership in the visible list at
`0x80096EA8` and changed zero pixels. Within this reproduced control, pass-3
XYZ is a cull anchor rather than a draw position.

## Actor/mover ownership

The scene actor pool is 64 records of `0x84` bytes at `0x8009FD80`. Across
Training, stages 1–15, and three bonuses, 19 strict-pristine anchors covered 16
scene IDs and actor IDs `1..41`. Ten bounded `0x8004B940` hits occurred in five
anchors, while 13 anchors showed natural record movement. A short idle window
is not an absence proof.

Pause flags `1,1,0` froze the whole actor-pool hash and then rearmed native mover
callbacks. Loading LEVEL01, LEVEL02, then LEVEL01 reproduced the first scene's
pass-table hashes/counts and actor source map exactly, while LEVEL02 was
distinct. Resident parser/culler/updater code and fixed buffers are reused;
the DAT tables, actor records, and source identity are scene-owned.

## Shared actor-source records

Every live actor's `+0x80` backlink was followed to its `0x1C` source record.
Initializer `0x80049C30` consumes source `+0x0C` as the actor ID and `+0x0D`
as the VM selector; the stable type word is therefore
`(selector << 8) | actor_id`. It also reads configuration/initial-state bytes
at `+0x0F..+0x11` and flags at `+0x12`. Source `+0x0E` and `+0x18..+0x1B`
are runtime-mutable and are excluded from the stable behavior key.

Across the 19 strict-pristine anchors, all 605 live actors matched their
backlinked source ID. The corpus contains 54 type-word behavior classes, 283
authored variants, 41 actor IDs, 37 naturally observed selectors, and ten
nonzero callbacks. Actor IDs 11, 14, 16 and 36 already have independent
downstream ownership as seeds, Dot, Thumper and Thud, respectively. This
directly corrects the semantic owner of address `0x80094A38`: despite the
historical machine ID `original.enemy_spawn_source_table`, it is a shared
level-actor source table and cannot be owned only by regular enemies.

The remaining 47 behavior classes are retained as unclassified candidates.
Type-word identity is a cluster key, not proof of a prop, switch, gate, mover,
enemy, hazard, or objective role.

## Native contact-outcome handoff

The completed A04 and A06 campaigns already retain paired calls to native
proximity owner `0x8004ABF4` from fresh pristine anchors. A deterministic join
by save plus actor address maps all 28 representatives back through actor
`+0x80` to their E08 source records and through selector `+0x0D` to the fully
decoded E07 VM programs. There are zero missing joins. The controls cover 22
type words, 18 of which were among E08's 47 unowned candidates; 29 unowned
classes still have no direct contact control.

The raw outcomes, rather than the A04 summary, derive four classes: twenty
ordinary representatives take neutral damage/state 15 and select kick state 30
without player damage; three are response-only, two use the separate `0x20`
path, and three suppress the ordinary path with `0x800`. A06 independently
confirms that timer 12 selects neither offensive actor response -20 nor 30 for
all 28 representatives. Player damage may still occur, so this is not a generic
immunity result.

Type `0x0109` also has a natural movie control from A05. At movie frame 128,
the accepted abdomen bounce writes target state -20 and `+0x54/+0x58=4096`,
increments the Bonus-1 streak to 1, and preserves health 4. Changing only the
slam window from 1 to 0 at frame 124 produces, at the same frame and cycle,
state 15, streak 0, and health 3. This is causal contact behavior, but neither
it nor the paired direct calls establishes species, final subsystem ownership,
switch/gate policy, or persistence.

## Cycle-neutral existing-movie outcomes

Five centrally hash-pinned Phase-4 operator movie/save pairs were replayed only
after `emulator.getStateInfo` identified each save as pristine `SCUS-94288` and
the mounted CUE/track matched the pristine retail hashes. Each target frame was
reached from the inspected anchor with `movie.traceToFrame`; matched control and
instrumented branches retained identical cycle counts and final RAM hashes, so
debugger stepping did not create the outcome.

Four complete replays have stable typed actor boundaries. Type `0x0F06` changes
health/response `8 -> 6`, state `1 -> 20`; `0x0C13` changes `6 -> 4`, state
`0 -> 20`; new type `0x060C` changes `999 -> 0`, state `20 -> 19`; and
`0x0B11` changes `999 -> 0`. The complete D11 mite lead changes player health
`4 -> 3` but has no stable typed actor outcome. Consequently, the aggregate
unowned frontier is 19 classes with native outcomes and 28 without. These are
typed native outcomes, not writer attribution: zero species or D-row owners are
promoted from operator filenames.

The centrally pinned `wooden_fence.sav` and `offering_stone_and_ramp.sav`
controls both reproduce scene 1 with 484 pass-1 rows, 140 pass-3 rows and 32
actors. Their bounded 20-frame mover windows returned zero and four entry hits.
Those observations neither prove absence nor assign semantics from filenames.

## Cycle-neutral hazard-lead boundary

Eight additional centrally pinned E10 movie/state pairs cover recorded hazard
leads in LEVEL02, LEVEL04, LEVEL05, LEVEL07 and LEVEL11. Before load, every
state reported valid version-84 pristine `SCUS-94288` media and the mounted
CUE/track matched the pristine retail pins. Complete `movie.traceToFrame`
replays ended with identical control/instrumented RAM, registers, cycles and
frames, and all retained coverage rings were untruncated.

Every replay changes player health or lives: acorn `health 1 -> -1`; falling
rocks `4 -> 3`; falling spikes `1 -> 0`; goo `4 -> 2`; ground bird
`lives 4 -> 3`; LEVEL02 pit `lives 5 -> 4`; LEVEL05 pit `lives 1 -> 0`; and
LEVEL07 pit `lives 6 -> 5`. The eight runs retain 8,056,072 resident actor/
contact/update hits, 1,376,684 resident damage/immunity hits, and 4,038,407
Region-A hits. No run ends with a decisive typed actor retirement, response
decrement, or state -20/30 boundary. Therefore these are positive player
outcome controls and negative stable-actor routing results; they do not consume
any of the 28 uncontrolled type words or assign E08/E10 ownership from a
filename.

## Retained frame-boundary source activity

The exact pinned offline reader reconstructs all 5,753 boundaries in the 13
retained E08-relevant capsules. A deterministic join from every changed live
actor's `+0x80` source pointer resolves all 3,364 actor changes to authored
source identity. Seven of the 28 classes without native outcome controls occur
in those changes; five (`0x050D`, `0x1B1F`, `0x1E20`, `0x2528`, and `0x2629`)
have flag or fresh-knockback boundaries rather than VM timing alone.

Type `0x1B1F` activates knockback on LEVEL11 frames 428 and 548, the same frame
boundaries as player health losses. This is a retained original-game
correlation and a control-selection lead. It is not an actor-to-player causal
claim, semantic role, or ownership assignment. Frame capsules cannot order
stores within a frame, and fixture names remain discovery metadata only.

The same reconstruction reproduces the live HP leaves for types `0x0F06`,
`0x0C13`, `0x060C`, and `0x0B11`. Native-control status remains unchanged at
19 controlled / 28 uncontrolled classes. Detailed event lists and passive
hotspots are in [[EXP_2026-07-19_phase4_offline_e08_batch]].

## Static uncontrolled-class frontier

The 28 uncontrolled type words are now mechanically derived as the exact,
duplicate-free complement of 19 controlled classes inside the 47 unowned
actor/source classes. Each joins to exactly one selector in the complete
40-program E07 decode, its authored signatures, and any nonzero callback in the
ten-function resident callback census. Callback bounds and their byte-matched
C/ASM source paths are retained directly.

The existing frame index partitions this frontier into five classes with
significant actor boundaries, two with VM-timing changes only, and 21 absent
from the relevant actor-change records. Interface-first ordering ranks
`0x2528`, `0x2629`, `0x050D`, `0x1B1F`, and `0x1E20` first. No uncontrolled
class moved in the retained source catalog, so movement supplies no
distinguishing evidence here.

This is a static search-frontier fact, not a semantic classification. It does
not supply a native outcome writer, assign a prop/enemy/hazard owner, or order
same-frame stores. `complete_frontier` therefore remains open.

## Open consumer boundary

This evidence does not assign final owners to the 19 outcome-controlled unowned
classes or supply native outcomes for the other 28. Switch/gate contact
outcomes, native authored state, denial/success feedback, and checkpoint/death/
reload/save-load persistence remain open. Terrain visuals, collision, and
dynamic geometry remain owned by E01, E02, and E11. Static catalog membership,
a visual delta, a generic contact response, or a fixture name must not be
promoted into an interaction, species, ownership, or persistence claim.

Machine contract: `config/phase4_props_movers.yaml`. Retained reproduction:
`analysis/phase4_props_movers.json` and
`analysis/phase4_e08_outcome_join.json`; cycle-neutral operator replay:
`analysis/phase4_e08_operator_contacts.json`; bounded hazard replay:
`analysis/phase4_e08_hazard_outcomes.json`; offline retained-capsule consumer:
`analysis/phase4_offline_e08_batch.json`; exhaustive static class join:
`analysis/phase4_e08_class_frontier.json`.
