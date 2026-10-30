---
kind: system
id: SYS_contact_objects_and_drops
name: Contact Objects and Drops
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - FUNC_80059E44
  - FUNC_800586B0
  - FUNC_80014844
memory:
  - MEM_800B0D18
tables:
  - TABLE_8007941C
  - TABLE_80079E30
  - TABLE_8001B570
constants:
  - CONST_DROP_TYPES_AND_ACTIONS
evidence:
  - EXP_2026-07-07_golddrop_pickup_verifier
  - src_re/contact_alloc_80059e44.c
  - src_re/contact_walker_800586b0.c
  - src_re/enemy_drops.c
  - src_re/contact_billboard_render_80014844.c
src_paths:
  - src_re/contact_alloc_80059e44.c
  - src_re/contact_walker_800586b0.c
  - src_re/enemy_drops.c
  - src_re/contact_billboard_render_80014844.c
  - src_re/contact_scatter_component_800593e8.c
---

# SYS_contact_objects_and_drops

## Purpose

Canonical hub for original-game contact/drop objects: allocator, contact-array records, metadata tables, action dispatch, pickup overlap, and lifetime gates.

## Confirmed original-game behavior

- `FUNC_80059E44` allocates records in the 64-slot contact array at `0x800B0D18`.
- Contact records use metadata table B at `0x8007941C` and render-attribute table A at `0x80079E30`.
- `FUNC_800586B0` walks records, checks Flik overlap, and dispatches by `action_id` through `0x8001B570[action_id - 2]`.
  ⚠️ Two qualifiers that are easy to lose: the walker reaches that dispatch **only** for records whose
  flags `+0x33` have bit `0x02` set (gate at `0x80058748`), and `action_id` is **not** the ctorType a
  spawner passes to the allocator — it is `metaB[ctorType]+0x00`. Contact objects that are not pickups
  run through a *separate* dispatch, [[TABLE_8001B7F0_contact_behaviour_class_dispatch]], keyed by
  `+0x2F`. See [[SYS_contact_object_pool]] for the full six-consumer gate table.
- `type 34` is a literal gold-berry pickup. Collecting it arms/equips gold.
- `type 38` is the health leaf. Its contact lifetime/despawn behavior is the model copied by the Gold Berry token mod.
- `type 120` is the native spinning gold-kill glyph visual row emitted by the original permanent-kill path.

## Mod boundary

The Gold Berry token mod reuses `type 120` only as a visual/contact-object carrier. The original game does not treat type-120 pickup as "credit this tagged enemy"; that behavior comes from the mod hook at `HOOK_800589D4`.

Do not collapse these meanings:

- Literal gold equip pickup: `type 34` / `action_id 34`.
- Gold-kill glyph carrier: `type 120` / `action_id 123`.
- Gold-token pickup credit: mod-only, guarded by a non-native enemy tag at contact-record `+0x1c`.

## Evidence

- `src_re/enemy_drops.c` documents the allocator, dispatch, known drop types, and the health-leaf/gold-token lifecycle distinction.
- `EXP_2026-07-07_golddrop_pickup_verifier` confirms that the modded type-120 floor glyph can be collected and advances the permanent-kill counter without arming gold.
- `WHYPE_gold_drop_type34_and_80049958` records the rejected type-34/token confusion so it is not promoted again.

## Unknowns

- Full semantics of table A and `fcn.800593e8` remain partially unknown.
- Some contact action side effects are labelled `UNKNOWN` in source and should stay out of Canon claims until verified.
- **Kind role classification (2026-08-02): 25 of 50 kinds (0x80096B98-indexed) still fully
  unknown-role**, down from 46 in `analysis/phase1_kind_actor_census.json`, via two free
  cross-reference passes (confirmed same numbering space as the 0x80096B98 table via
  [[MEM_80096B98]]'s own text: "Kind-indexed entries resolve type-0x3f/pickup
  descriptors") plus a static descriptor-shape pass:
  - **Pass 1** — 14 named by other already-solved systems sharing the table: FLIK letters
    16-19, grain 20, green/blue/purple-berry 33/35/36, seed-orange/blue/green/token
    41-45, animated-construct 49.
  - **Pass 2** — 5 more named by cross-referencing `src_re/contact_walker_800586b0.c`'s
    switch (the reversed `0x8001B570` dispatch table): kind 9 = B07 health grant, 12 =
    B06 invincibility grant, 15 = B09 super-jump grant, 32 = red/default berry, 46 = B08
    bubble grant. **2 more behaviorally characterized but not named**: kinds 2/8, a
    "post-angle" contact mechanism (calls `FUNC_8004A700` with a relative position
    vector; the source file's own comment marks that call's semantics **UNKNOWN** in this
    context).
  - **Descriptor-shape pass** (`analysis/phase4_e06_descriptor_shapes.json`) — dereferenced
    all 50 kind→descriptor pointers from the already-captured scene-invariant snapshot in
    `analysis/phase3_render_descriptors.json` (no live session needed: the pointer *table*
    is RAM/BSS but the descriptor *content* lives in the static EXE). All 50 have a
    non-null descriptor (type byte ∈ {0x1C,0x1D,0x1E}) — no dead slots. Type `0x1E`
    clusters 3 confirmed sprite kinds (38, 46, 49) with 6 unnamed (27, 31, 37, 39, 40,
    47) — structural evidence, not a name. Kinds 22-25 form a tight 4-entry family
    (type `0x1C`, near-identical bytes, one rotating offset byte) shaped like the
    FLIK-letter/seed-color quads — flagged, not identified.
  - ⚠️ **A first draft of the descriptor-shape artifact miscounted** (28 vs the correct 25
    fully-opaque kinds) because its named-kind dict omitted 3 of the 4 kinds already
    canon-bound *before this session* (29, 38, 48). Caught and fixed by re-deriving the
    count with asserts against `phase1_kind_actor_census.json` before banking, not by
    inspection.
  - Zero new experiments across all three passes. Full detail in
    `analysis/phase4_e06_kind_cross_reference.json` and
    `analysis/phase4_e06_descriptor_shapes.json`. Remaining 25 fully opaque:
    `0,1,3,4,5,6,7,10,11,13,14,21,22,23,24,25,26,27,28,30,31,37,39,40,47`.

## Live VRAM texture decode — 2026-08-02, resolves a long-open sibling system

Full evidence: `analysis/phase4_e06_texture_decode.json`. Isolated DuckStation instance
(never the operator's own), `level03.sav`. Two methods tried; one **rejected before
banking anything**:

- **Rejected: in-game screenshot pixel sampling.** Sampled sprite colour cycled with an
  **exact period of 8** across the test batch — kind 3's sampled colour equalled kind 14's
  equalled kind 28's, exactly — unrelated to which kind was actually set. Almost certainly
  3D-pipeline dithering/anti-aliasing noise at this tiny sprite scale. Caught by sampling
  numerically rather than trusting the eye; none of its results are used below.
- **Used: direct VRAM texture decode** (`gpu.decodeTexture` at the descriptor's own exact
  TPAGE/CLUT/u0/v0/width/height) — bypasses the 3D pipeline, dithering, and blur entirely.
  Validated first against kind 20 (grain, already Canon-bound): produced a clean,
  unmistakable single grain-kernel icon before trusting it on the unknowns.

**Resolves the mechanics baseline's own originally-UNRESOLVED `B03_dandelion_glide` row's
sprite identity for the first time: kind 13 is unmistakably a dandelion** — fluffy grey/white
fluff-head fanning from a brown stem. (Confirming this specific slot is the one actually
placed/reachable in the dandelion-glide stages was not done this pass.)

**Bounded correction from the retained B03 capsule (2026-08-02):** the actual
seed_plant_dandelion_handler trigger occurs at movie frame 180 while the 64-slot contact
pool contains zero live action-id-13 records across all 998 reconstructed frame
boundaries. Kind 13 remains confirmed dandelion artwork, but it is not the contact-pool
carrier for this captured plant interaction. Do not promote texture identity into actor
or attachment identity. See [[EXP_2026-08-02_phase4_b03_dandelion_capsule]].

**Other high-confidence visual identifications**: kind 8 = a spiky red/green ball
(hazard/mine-shaped; NOT confirmed as the already-solved yellow-seed MINE, which uses a
different numbering space — not cross-checked); 22 = red-capped mushroom; 24 = blue
flower; 25 = green leaf; 27 = gold coin (X mark); 28 = blue creature/grub face (two large
cartoon eyes); 30 = bronze "0"/"O" token; 31 = silver coin embossed "FLIK"; 47 = red
flower cluster; 23 = small red berry with a sparkle/star-burst overlay; 11 = branching
brown root/tendril structure (organic, unnamed).

**Two are confirmed NOT gameplay sprites at all**: kind 37 decodes to the literal text
"demo" in yellow, and kind 39 decodes to the **Traveller's Tales developer studio
logo/wordmark**. Both are leftover debug/credit assets — explains why no `ctorType` in the
scanned 0-199 range ever produces these action ids (never wired to real spawn code).

**Kinds 0/1/2/3/4/5/6/7/10/14 are plain grey/white geometric shapes** (sphere, ring, blob,
diamond, pebble, dome, pill) with no distinguishing marks — consistent with the
already-Canon grayscale CLUT-recolour placeholder system
([[EXP_2026-07-10_blackberry_square_and_selector_regression|grayscale CLUT recolouring evidence]]), likely tinted at runtime; not identifiable as
a specific game object from the base texture alone. **Kind 0 and kind 1 share byte-identical
descriptors** — the same sphere texture — but kind 0 never draws (the renderer's
documented action-id-0 sentinel) while kind 1 does, confirming kind 0's descriptor is real
and renderable and it is specifically the action id that's suppressed, not the asset.
**Kind 21's descriptor is a 1-texel-wide sliver** (degenerate, not a real icon — likely a
marker/line primitive or unused slot).

**Still open**: this decode gives the TEXTURE, not the game-object SEMANTIC role (when/
where each is placed, what collecting or triggering it does) — needs either a scene-asset
cross-reference or genuine in-context observation, not injection.

## Renderer decompiled to real C — 2026-08-02

`src_re/contact_billboard_render_80014844.c` — full documentation-grade C for `FUNC_80014844`
(`contact_record_billboard_render`), covering all 10 measured pipeline steps from
`analysis/phase4_contact_object_render.json` (liveness, draw-flag, GTE position transform,
quad build, descriptor lookup, depth/screen culling, OT insert, texture/colour). Compiles
clean (`gcc -fsyntax-only`, no errors; guarded by `tests/test_phase4_e15_e06_c_decompiles.py`).
Encodes the shared-descriptor-table correction (contact objects and type-0x3f pickups
index the SAME `0x80096B98` table, just via different fields) and the `action_id == 0`
do-not-draw rule directly in code, not just prose.

Also completed `src_re/contact_scatter_component_800593e8.c` — the render-attribute
helper `fcn.800593E8`, previously only an `extern` stub in `contact_alloc_80059e44.c`
with its internals marked UNRESOLVED. It was actually already SOLVED (24/24 live-verified,
2026-08-01) but never had its own source file; `contact_alloc_80059e44.c`'s header is now
corrected to point at it instead of listing it as unresolved. One transcription typo
caught before commit: the file was first named with an extra hex digit
(`80059e3e8` instead of `800593e8`) — caught and renamed, guarded by a test asserting the
filename matches the address documented in its own header.

## E06 methodology audit - 2026-08-02

The allocator core is now bounded-exhausted, not the complete E06 row. C static work
corrects metadata B to exactly 129 rows (`ctor 0..128`), metadata A to 78 rows, and
enumerates 94 resident allocator call sites. C reconstruction of the validated B06
capsule confirms natural activation, retirement, reactivation, walker/render execution,
and 12 cursor wraps across 1,098 frames with zero domain-hash mismatches. Capacity also
has the older native Phase 2 free-slot/all-occupied A/B proof.

Strict E06 status remains `partial`. Open high-value offline work is the overlay and
data-derived producer frontier, complete record-field access typing, pool/cursor clear
and reset ownership, and remaining action side effects. A dedicated cold-boot oracle,
stage/transition breadth, cross-system contracts, source closure, and executable E06
gate remain later campaign work. Exact decision:
`analysis/phase4_e06_methodology_audit.json`; campaign:
[[Game Solving Campaign - Contact Object Pool]]; focused Canon:
[[SYS_contact_object_pool]].
