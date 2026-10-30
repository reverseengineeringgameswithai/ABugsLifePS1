# LEVEL01 type-0x3f Entry Map — A Bug's Life (SCUS-94288)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)

`LEVEL01\LEVEL.DAT` first top-level record is **type `0x3f`** at file offset `0x4`
(header `46 00 3f 00` = 70 entries, each `0x10` bytes, entries start at `0x8`).
Entry N is at file offset `0x0008 + N*0x10`. Layout: `+0x00` X, `+0x04` Y, `+0x08` Z
(s32 LE), `+0x0c` source kind (u32 LE). Runtime coords = file coords `<< 5`
(see [COORDINATE_MODDING.md](COORDINATE_MODDING.md)).

## Entry ranges (LEVEL01, pristine — 70 entries, count stays 70 for in-place edits)

| entries | role | source kind(s) |
|--------:|------|----------------|
| `0..49`  | grain (50) | `0x14` |
| `50..53` | visible FLIK letters | `0x10`=F, `0x11`=L, `0x12`=I, `0x13`=K |
| `54..57` | **special berries / power-ups** | `0x22`,`0x23`,`0x21`,`0x24` (see table) |
| `58..66` | seed-power tokens (9) | `0x29`,`0x2a`,`0x2b` |
| `67..69` | checkpoint / trigger candidates | `0x30` |
| `70`     | (example) appended entry via relocation-aware insert | e.g. `0x29` |

Note the special-berry block is entries 54/55/56/57 — entry 56 (kind `0x21`) sits between
55 and 57 in file order.

## Confirmed source-kind map (all in-game verified)

| kind | item | notes |
|-----:|------|-------|
| `0x10` | FLIK letter **F** | extra handler logic; coordinate-movable |
| `0x11` | FLIK letter **L** | |
| `0x12` | FLIK letter **I** | |
| `0x13` | FLIK letter **K** | |
| `0x14` | **grain** | 50 in LEVEL01; HUD count /50 at `0x800a65a1` |
| `0x21` | **Green Berry / Homing Berry** | entry 56; marker `0x800a6597`=2, sound `0x36` |
| `0x22` | **Gold Berry** | entry 54; marker 3, sound `0x38` |
| `0x23` | **Blueberry / Superberry** | entry 55; marker 1, sound `0x35` |
| `0x24` | **Purple Berry / Mega Homing Berry** | entry 57; marker 4, sound `0x37` |
| `0x29` | **orange/red seed token** | entries 63/64/65; counter `0x800a6598`, powered obj `0x16`, handler `0x800542f4` |
| `0x2a` | **blue seed token** | entries 60/61/66; counter `0x800a6599`, obj `0x17`, handler `0x8005433c` |
| `0x2b` | **green seed token** | entries 58/59/62; counter `0x800a659a`, obj `0x19`, handler `0x800543b8` |
| `0x30` | **checkpoint / trigger candidate** | entries 67/68/69; handler `0x80054554` (not a pickup) |

(The four berry contact handlers `0x80054288/98/ac/c0/d4` are symmetric — each only sets `0x800a6597`
and plays a sound; the berry *identity* lives in the overlay model, names are the in-game observations.)

## ⛔ WARNING — entries 54..57 are NOT safe sacrificial slots
Entries 54/55/56/57 (kinds `0x21..0x24`) back **real special berry / power-up pickups**. Overwriting their
kind deletes the associated berry (proven: converting 54/55/57 → `0x29` removed Gold / Blueberry /
Mega-Homing berries in-game). **Only edit their X/Y/Z; never change their kind.** To add NEW objects use the
relocation-aware true append (`tools/dat_reloc.py`), not berry-slot sacrifice. Fixed-count marker sacrifice
is obsolete (diagnostic only). See [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md) and
[DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md).

---

**Related docs:** [COORDINATE_MODDING.md](COORDINATE_MODDING.md) · [DAT_FORMAT_AND_RELOCATION.md](DAT_FORMAT_AND_RELOCATION.md) · [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)

[← Back to ABL_RE_NOTES.md (canonical index)](../ABL_RE_NOTES.md)
