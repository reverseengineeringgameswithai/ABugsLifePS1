---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Gameplay - Resident Noise and Ctor 0x71.md
aliases:
  - "Gameplay - Resident Noise and Ctor 0x71"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Gameplay - Resident Noise and Ctor 0x71.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Gameplay_-_Resident_Noise_and_Ctor_0x71.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Gameplay - Resident Noise and Ctor 0x71
type: core
updated: 2026-06-20
tags: [core, gameplay, pickup, contact, prng, milestone6, gap-0033]
---

# Gameplay — ctor-0x71 entity & where the resident-noise jitter lands (GAP-0033)

> Closes the open thread from [[Gameplay - Resident Event Stream]]: *what does ctor-0x71 create, and are the `(byte−0x80)<<4` jitter offsets visible?* **Conclusion: ctor-0x71 builds a CONTACT/PROXIMITY entity in the contact array `0x800b0d18` (allocated by [[FUNC_80059E44]]), walked by the proximity walker [[FUNC_800586B0]] for collection/sound/marker logic. It is NOT rendered — the visible pickup is drawn separately from the type-0x3f *record* (projector `fcn.800253e8`). So the resident-noise jitter offsets the entity's CONTACT-DETECTION position; it is logic/contact variation, NOT visible decorative scatter or particles.** All STATIC (`tools/exe_read.py` + decompiled `src_re/*`); runtime is optional/corroborating ([[DuckStation Fork Reproducibility]] / GAP-0001).

## Where the jitter lands (creation path)
[[FUNC_80053814]] generic visible-construct branch (kind<0x30, ≠0x14): reads 3 noise bytes from cursor `0x800822f4` (→ resident table `0x80017DB4`) and calls
`contact_alloc( (recX<<5)+((bx−0x80)<<4), (recY<<5)+((by−0x80)<<4), (recZ<<5)+((bz−0x80)<<4), ctor=0x71, stackArg=0x18 )`.
⇒ the 3 jitter bytes land in the **contact-entity coords** `rec+0x00/0x04/0x08` of a freshly-allocated slot in **contact array `0x800b0d18`** (64×0x38). The pickup's *own* X/Y/Z stay in its type-0x3f record (untouched, coordinate-moddable).

## The contact entity (what ctor-0x71 builds) — CONTACT/logic, NOT visible
- **Allocation** ([[FUNC_80059E44]]): fills `rec+0x20` action_id, `+0x22` active_type, `+0x28` radius, `+0x33` flags from **metadata B** (`0x8007941c[ctorType]`); fills `rec+0x0c/10/14/18` from **table A** (`0x80079e30[stackArg]`, labelled "render/texture attrs" — but see *Render residual*).
- **Post-init** [[FUNC_80024DDC]] (`fcn.80024ddc`): **trivial** — sets one byte `rec+0x37` = `0x2c`/`0x2e` based on `flags & 0x60`. **No render callback, no update-list insert, no GPU.**
- **Processing** ([[FUNC_800586B0]] walker, per frame): proximity test `dist² < radius²` (player-relative, Y-biased −0x1cc0) → on contact, dispatch `action_id` through table `0x8001b570` → collection / sound / marker / counter logic (callees `fcn.8005044c/80050994/80054eac/...`). **No GPU/render emission.**

## Visibility verdict (evidence)
| Question | Evidence | Verdict |
|---|---|---|
| Is the contact array rendered? | `xref 0x800b0d18` → **10 readers, all in the pickup/contact subsystem `0x80057xxx–0x8005dxxx`**; none in a renderer | **No** |
| Does the walker draw entries? | [[FUNC_800586B0]] callees are pickup/sound/marker bookkeeping — **no GPU** | **No** |
| Is there a contact-render call in the frame loop? | `fcn.8004ecd4` runs `source3f_dispatch`→scene-dispatch→`contact_walker`; **no contact-array render** | **No** |
| What renders the visible pickup? | projector `fcn.800253e8` reads the **type-0x3f record** (not the array) | record, separately |
| Does post-init register a renderer? | [[FUNC_80024DDC]] sets one state byte only | **No** |

⇒ **ctor-0x71 = a contact/proximity-interaction entity; the noise jitter varies its contact-detection position — logic, not visible.**

## Relationship to type-0x3f objects
The type-0x3f **record** is the authoritative + *visible* object (rendered by `fcn.800253e8`, collected via the record-contact jump table `0x8001b42c` at dist<0x9c4). The **ctor-0x71 contact entity** is a transient runtime proximity instance spawned near the pickup; the resident-noise jitter perturbs only that instance's contact coords. The two are decoupled — which is exactly why editing a record's X/Z moves the pickup precisely ([[Finding - Type-0x3f pickups are coordinate-moddable]]) despite the jitter.

## Confidence
- ctor-0x71 → contact array `0x800b0d18` slot (jitter into `rec+0x00/04/08`) — **CONFIRMED (decompiled)**.
- Contact array not rendered (no render reader; walker emits no GPU; loop has no contact-render) — **CONFIRMED (static)**.
- [[FUNC_80024DDC]] = trivial field-init, no render/update registration — **CONFIRMED (decoded)**.
- ⇒ jitter is **contact-position variation (logic)**, not visible scatter — **LIKELY-HIGH**.
- **Render residual:** table-A attrs `rec+0x0c..0x18` are *set* ("render/texture" per [[FUNC_80059E44]]) but **no consumer of the contact array's attrs was found**. Either vestigial for ctor-0x71, or consumed by a draw helper that receives `rec` by pointer (not via the `0x800b0d18` base, so invisible to xref). **UNRESOLVED** but not the primary visible path.

## Modding relevance
The resident-noise table governs **contact-entity position jitter**, not visible placement or any event system. Editing it (a resident/EXE patch) would perturb pickup *contact volumes' centres*, not where objects appear (that's the type-0x3f records) and not scripted events. For a level editor: object placement = records; the noise table is a side-channel of the contact layer, safe to ignore for placement.

## Remaining unknowns
- The **render residual** above (do table-A attrs ever drive a draw?). Decisive next step: runtime (local-only) — freeze/alter `0x800822f4` and watch for any visible change; or static — trace consumers of `fcn.800593e8`'s attr outputs.
- Gameplay *purpose* of contact-position jitter (forgiving/varied contact volume? a quirk?) — UNKNOWN, bounded.

## Related
[[Gameplay - Resident Event Stream]] · [[FUNC_80024DDC]] · [[FUNC_80059E44]] · [[FUNC_800586B0]] · [[FUNC_80053814]] · [[FUNC_8005B714]] · [[MEM - Contact array 800B0D18]] · [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Core - Rendering OT and GPU Packets]] · `tools/exe_read.py`
