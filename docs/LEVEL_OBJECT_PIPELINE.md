# LEVEL Object / Pickup Pipeline

This document is the current practical reference for the reconstructed LEVEL/DAT object and pickup pipeline:

```text
LEVEL.DAT type-0x3f entry
  -> fcn.8001cdc0 parser/relocator
  -> dynamic type table 0x80096da0
  -> fcn.80053814 source-kind pass
  -> fcn.80059e44 ContactRecord allocator
  -> fcn.800586b0 proximity/contact walker
  -> pickup/action handlers
  -> fcn.800526f4 HUD display
```

## Scope And Confidence

This is focused on the LEVEL/DAT object and pickup systems. It is not a full-game decompilation.

The C-like files in `src_re/` are evidence-backed hand-decompilation notes. They preserve signedness, branch structure, and confirmed runtime behavior, but they are not compile-ready replacement source.

Confidence labels follow the project convention:

- `CONFIRMED`: supported by disassembly, tools, or in-game testing.
- `LIKELY`: supported by local evidence but not fully proven.
- `UNKNOWN` / `TODO`: intentionally unresolved.

## Data Formats

### `Type3FEntry`

`Type3FEntry` is the 0x10-byte source placement entry inside a DAT top-level type-`0x3f` record:

```c
typedef struct Type3FEntry {
    int32_t x;      /* +0x00 CONFIRMED file X */
    int32_t y;      /* +0x04 CONFIRMED file Y */
    int32_t z;      /* +0x08 CONFIRMED file Z */
    uint8_t kind;   /* +0x0c CONFIRMED source kind */
    uint8_t unk0d;  /* +0x0d LIKELY eligibility/status byte */
    uint8_t unk0e;  /* +0x0e UNKNOWN */
    uint8_t unk0f;  /* +0x0f UNKNOWN */
} Type3FEntry;
```

Runtime coordinate rule: `runtime = file_coordinate << 5`.

Y axis rule: more-negative Y is upward. Large upward moves can still contact early because the runtime contact walker underweights Y.

### `ContactRecord`

`ContactRecord` is the runtime proximity/contact record allocated by `fcn.80059e44`:

- Base: `0x800b0d18`
- Count: 64 records
- Stride: `0x38`
- Confirmed key fields:
  - `+0x00/+0x04/+0x08`: runtime `x/y/z`
  - `+0x20`: `action_id`
  - `+0x22`: `active_type`
  - `+0x28`: `radius_add`
  - `+0x33`: `flags`

Use [src_re/re_types.h](../src_re/re_types.h) for the current full field map. Unknown fields remain `unkNN` unless a decompiled body directly proves a stable name.

## Source-Kind Map

Confirmed LEVEL01 type-`0x3f` source kinds:

| Kind | Meaning | Confidence |
|-----:|---------|------------|
| `0x10..0x13` | FLIK letters F/L/I/K | CONFIRMED |
| `0x14` | Grain | CONFIRMED |
| `0x21..0x24` | Special berries | CONFIRMED |
| `0x29..0x2b` | Seed tokens | CONFIRMED |
| `0x30` | Checkpoint/trigger candidate | CONFIRMED as non-pickup checkpoint/trigger path |
| `0x2c/0x2d` | Token-like extra seed actions | CONFIRMED in handler code, not production-tested in LEVEL01 |

Do not assume this exact identity map applies blindly to every level. LEVEL01 is the production-tested baseline.

## Parser / Relocator

`fcn.8001cdc0` parses the loaded DAT, rebuilds the dynamic type table at `0x80096da0`, and relocates baked internal DAT offsets.

Key confirmed behavior:

- Positive type records are stored at `0x80096da0 + type*4`.
- Type `0x3f` size is `4 + count*0x10`.
- The type-`0x3f` pointer is available at `0x80096e9c`.
- Dynamic type table entries are rebuilt, not relocated.
- LEVEL01 has 1248 confirmed relocation sites handled by `tools/dat_reloc.py`.

Production implication: true append/insertion must use relocation-aware tooling. Naive byte-shift append leaves stale baked offsets.

## Constructor Behavior

`fcn.80053814` walks the type-`0x3f` record and performs construction and source-side pickup dispatch.

Confirmed constructor paths:

- Generic visible constructor: `ctorType 0x71`
  - Used for FLIK letters, berries, and seed tokens.
  - Requires `kind < 0x30`, `kind != 0x14`, proximity gate, and phase gate.
  - Phase gate: `(kind & 3) == [0x800910a4]`.
  - Adds three script-byte offsets from cursor `0x800822f4`.
- Grain constructor: `ctorType 0x51`
  - Used for kind `0x14`.
  - Uses exact entry coordinates shifted left by 5.
  - Marks the source entry consumed by writing sentinel Y.
- Checkpoint path:
  - Kinds `0x30/0x31` use checkpoint/trigger construction paths.
  - Inner animation and some trigger semantics remain `LIKELY` / `TODO`.

The constructor pass also tracks nearest eligible entries and dispatches source-side action handlers when close enough.

## Contact Behavior

`fcn.80059e44` allocates runtime `ContactRecord` slots. `fcn.800586b0` scans those slots for player proximity.

Confirmed walker behavior:

- 64 records.
- Stride `0x38`.
- Active gate: signed `active_type > 0`.
- Collidable/enabled gate: `(flags & 2) != 0`.
- Player snapshot is taken once per walker call.
- Player Y is biased by `-0x1cc0` before distance math.
- Radius: `0x12c + radius_add`.
- Contact condition is strict: `distance_squared < radius * radius`.

Exact walker math:

```c
player_x = [0x800a6500];
player_y = [0x800a6504] - 0x1cc0;
player_z = [0x800a6508];

dx = ((player_x - record.x) * 0x300) >> 13;
dy = ((player_y - record.y) * 0x100) >> 13;
dz = ((player_z - record.z) * 0x300) >> 13;

distance_squared = dx*dx + dy*dy + dz*dz;
radius = 0x12c + record.radius_add;
contact = distance_squared < radius*radius;
```

X and Z use multiplier `0x300`; Y uses `0x100`. Y therefore has one-third the X/Z weight before squaring, which explains auto-collect behavior for large vertical moves.

Record-side dispatch:

- `action_id` is read from `ContactRecord+0x20`.
- Dispatch index is `(int16_t)(action_id - 2)`.
- If unsigned index `< 0x75`, the walker jumps through table `0x8001b570`.
- Otherwise it uses the default case.

## Pickup / Action Behavior

Confirmed action-side globals:

- Grain count: `0x800a65a1`
  - Incremented by `fcn.80054eac`.
  - Target is `0x32` (50).
- FLIK bits / record flags:
  - Source-side FLIK action sets bitmask bits for kinds `0x10..0x13`.
  - HUD also reads FLIK object record pointers and collected flag `+0x1b`.
- Berry marker: `0x800a6597`
  - Kind `0x21` -> marker `2`.
  - Kind `0x22` -> marker `3`.
  - Kind `0x23` -> marker `1`.
  - Kind `0x24` -> marker `4`.
  - Kind `0x20` clears marker.
- Seed counters: `0x800a6598..0x800a659a`
  - Kinds `0x29/0x2a/0x2b`.
  - Stored encoding is `(n & 7) * 17`.
  - Extra token-like counters exist at `0x800a659b/0x800a659c` for `0x2c/0x2d`.
- Checkpoint first-fire behavior:
  - Gate at `0x800824dc`.
  - First fire saves an index to `0x800823cc`, sets the gate, clears checkpoint coords at `0x800a652c/30/34`, clears `0x800a6582`, and returns result `-9`.

Berry gameplay effects beyond marker values are still not fully named.

## HUD Closure

`fcn.800526f4` closes the pickup pipeline by drawing pickup state:

- Grain HUD reads `0x800a65a1`, target `0x32`, and packed digits at `0x800b018e`.
- Seed meters read exactly the displayed counters `0x800a6598..0x800a659a`.
- FLIK bit HUD reads `0x800a65a2`, bits `0..3`.
- FLIK record-icon HUD reads pointers `0x800a0220/0430/0a60/0d78` and collected flag `+0x1b`.

The HUD also contains scene-specific panels outside this pickup pipeline; those remain summarized as `UNKNOWN` / `TODO` in the Phase 6 notes.

## Production Rules

- Fixed-size coordinate edits are safe for moving existing type-`0x3f` entries.
- Preserve source kind when moving berries, tokens, FLIK letters, and grains.
- Use `tools/dat_reloc.py` for true insertion or append.
- Never use naive byte-shift append for relocation-bearing DATs.
- Entries `54..57` are real berries, not sacrifice slots.
- Avoid huge Y moves because weak-Y contact behavior can auto-collect high vertical moves.
- Treat `0x2c/0x2d` as token-like but not production-tested in LEVEL01.
- Treat checkpoint semantics as not fully proven outside the confirmed first-fire path.

## Evidence Links

Phase source files:

- [src_re/dat_parser_8001cdc0.c](../src_re/dat_parser_8001cdc0.c)
- [src_re/source3f_dispatch_80053814.c](../src_re/source3f_dispatch_80053814.c)
- [src_re/contact_alloc_80059e44.c](../src_re/contact_alloc_80059e44.c)
- [src_re/contact_walker_800586b0.c](../src_re/contact_walker_800586b0.c)
- [src_re/pickup_handlers_80054288_80054554.c](../src_re/pickup_handlers_80054288_80054554.c)
- [src_re/hud_800526f4.c](../src_re/hud_800526f4.c)
- [src_re/re_types.h](../src_re/re_types.h)

Related docs:

- [docs/DECOMPILATION_PLAN.md](DECOMPILATION_PLAN.md)
- [docs/DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md)
- [docs/LEVEL01_TYPE3F_MAP.md](LEVEL01_TYPE3F_MAP.md)
- [docs/COORDINATE_MODDING.md](COORDINATE_MODDING.md)
- [docs/TOOLING.md](TOOLING.md)
