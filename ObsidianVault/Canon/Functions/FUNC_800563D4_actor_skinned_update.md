---
kind: function
id: FUNC_800563D4
aliases: [FUNC_800563D4, 0x800563D4, actor_skinned_update]
address: 0x800563D4
name: actor_skinned_update
status: static_seen
confidence: confirmed
source_state: original_game
system: [Gameplay_-_Input_and_Movement]
reads: [0x80082488, 0x800A6588, 0x800A6300, 0x800A6500, 0x800A6504, 0x800A6508, 0x800A6520, 0x800A6544, 0x800A6548, 0x800A6590]
writes: [0x800A6588, 0x800A6544]
calls: [FUNC_80059E44, 0x8005ec84, 0x8005044c]
evidence:
  - asm/nonmatchings/resident/800563d4.s
  - analysis/phase4_d15_daddy_long_legs.json
patch_policy: hook_sensitive
---

# FUNC_800563D4 - actor skinned update

## Confirmed slow-walk branch

The solved resident assembly at `0x800566CC..0x800566F8` reads the working pad
word at `0x80082488` and tests `0x0300` (L2 or R2). When either trigger is held,
the branch writes animation index `0x1D` (29) to player state `0x800A6588`;
otherwise it writes walk animation `0`.

This is independent of [[FUNC_80048138_player_vertical_update]], which applies
the same mask to locomotion throttle. Live OG/ALLMODS traces confirmed the bad
ALLMODS build reached animation 29 and advanced its phase, so the static-looking
slow walk was downstream render/model-data damage rather than a failure here.
See [[EXP_2026-07-10_allmods_slowwalk_animation_regression]].

## Animation-clip-keyed contact spawn (investigated as a D15 web-attack candidate, RULED OUT) — 2026-08-02

While tracing the D15 daddy-long-legs' web attack (`analysis/phase4_d15_daddy_long_legs.json`),
a live breakpoint + `$ra` trace at [[FUNC_80059E44]]'s entry, hit during frames
correlated with a confirmed web-attack health-drop event, pointed at the call
`0x80056de4` — `jal 0x80059e44` (`ctorType=49`) — inside this function. Disassembly
of `0x80056c60-0x80056e94` around that call site confirmed a real, distinct
gated-spawn mechanism: a multi-stage sequence against the `0x800A65xx` block
documented in [[MEM_800A6500]] as Flik's own position/state (pointer deref
`v0=*(0x800A6300); a0=*(v0+0x88)` → helper `0x8005ec84`; an angle accumulator at
`0x800A6544` that only proceeds on high-halfword wraparound; a distance gate
`(0x800A6548-0x800A6504)<1024`; a suppress-flag check on bit `0x80` of `0x800A6590`
— the same bit [[MEM_800A6500]] documents as the C13 grain-harvester "busy" flag,
a previously-undocumented cross-system read at this PC; finally `s2`, consistent
with an animation-clip index, checked against literal sets `{130,131,133}` /
`{135,138,145}` to pick between two symmetric `contact_alloc(ctorType=49)` calls).

**This call site was RULED OUT as the D15 web-attack producer.** A direct read of
metadata table row `ctorType=49` (`0x8007941c + 49*0x14 = 0x800797f0`) shows
`action_id=1`, not the `118` (`0x76`) confirmed live on the web projectile's own
contact-pool record — the coincidental breakpoint hit near the right frames was a
DIFFERENT, unidentified contact spawn (still gated by the mechanism described
above), not the web. The real web-attack producer chain is documented at
[[FUNC_80059E44]] (sibling allocator `0x8005a0e0`) instead. Kept here so a future
pass does not re-chase this same false lead. The gating mechanism itself (angle
accumulator, distance threshold, C13-shared suppress bit, animation-clip literal
sets) is a real, verified fact about this function — only its D15 attribution was
wrong.
