# G56 — The visible WALLS are chunk-35 (master mesh), distinct from the DAT-floor GROUND

Status: **live-confirmed (2026-06-24)**, isolated DuckStation, pristine `Disney-Pixar A Bug's Life (v1.0)`,
LEVEL01 reached via `flik_to_level01_stall.mv.movie.json` (4253-frame movie, ends in gameplay — no Start).
Operator hint: the walls are visible at level start a bit farther out; turn Flik with a `down` tap + ~2 s wait.

## Headline
The level's **dark-brown WALLS** (the curved boundary structures behind Flik, "farther out") are the
**chunk-35 terrain master mesh**, drawn by [[FUNC_800172DC]] as GP0(3c) quads — a SEPARATE render layer from
the **lighter GROUND** (the DAT `FUNC_80010000` floor payloads edited by `tools/sculpt_terrain.py`). This
splits the "terrain" into two independently-sourced layers:

| Layer | Source | Renderer | Edit status |
|---|---|---|---|
| **Ground** (lighter) | LEVEL.DAT `FUNC_80010000` floor payloads (node array @0x45f0) | FUNC_80010000 | ✅ `sculpt_terrain.py` (steps 6/9); moving all 30 floor payloads changed the ground ~20%, the wall 0% |
| **Walls** (darker) | **LEVEL.RAW chunk 35** (master mesh) | [[FUNC_800172DC]], GP0(3c) | 🟡 live-editable; permanent needs the master-mesh decode (below) |

## Evidence
1. **DAT floor ≠ wall.** Sculpting all 30 DAT floor payloads (Y −6000) reshaped the lighter ground (20% of
   the turned frame) but left the darker wall unchanged → walls are not DAT floor.
2. **pickObject.** A wall pixel (turned view, native 512×224) resolves to `GP0(3c) quad` (tpage x=0,y=0); a
   lower-ground pixel resolves to `GP0(2e)` tpage x=640. Different GP0 path → different layer.
3. **Live buffer poke = wall change.** The chunk-35 terrain buffer **`0x8012c1d0`** (the runtime render-quad
   array: 0x30 stride, vertex Y = **high16 of the words @ +0x04/+0x0c/+0x14/+0x1c**) — poking all 199 quads'
   Y reshaped/raised the wall (43% of the turned frame). So walls = the chunk-35 buffer. (−Y = up; model-Y
   world-scale 1.0, per the [[Plan - Terrain+collision matched bump (Option B)]] matrix.)
4. **Buffer ← chunk-35.** `0x8012c1d0` == decompressed chunk-35 **+0xc** (first 0x20 bytes byte-identical).

## The permanent-edit blocker (the master-mesh format)
The runtime buffer (199 fixed 0x30 quads) is the **processed render output**. The ON-DISK decompressed
chunk-35 is **NOT** that layout — it is a **master mesh** (same class as chunk 34):
- header `[0:0xc]` = marker `02 01 …`, a count `0x16` (=22 sub-meshes/pools) at **+0x0a**, data at **+0x0c**;
- the data is a **variable-length vertex + command stream** (only the first ~5 0x30-blocks look like quads;
  from +0xf0 on the per-0x30 "command" byte is random → it's not fixed quads).

Consequence (in-game, on rebuilt discs via `build_autolayout_disc.py`):
- identity-recompress of chunk 35 → **boots fine** (the codec is not the issue);
- editing **one** aligned vertex (dec35 +0xc, Y −0x300) → **boots fine** (Flik spawns);
- a **blanket** 0x30-stride Y edit over 199 blocks (any magnitude) → **CRASHES the level load** (Flik at
  origin) — it corrupts command-stream bytes that the load/render walk reads.

⇒ **Permanent wall editing requires decoding the master-mesh vertex/command split** (which bytes are vertex
coordinates vs draw commands, per sub-mesh) so only true vertices are edited. The runtime buffer is editable
LIVE today (the lever works); the on-disc path is gated on that decode. This is the chunk-34/35 master-mesh
gap ([[Gap Audit|GAP-0011]]/[[Gap Audit|GAP-0023]] territory).

## Next RE (to enable permanent wall edits)
1. Decode the chunk-35 master-mesh sub-mesh format: per-sub-mesh vertex table vs command stream (likely the
   same encoding as the chunk-34 master mesh / `FUNC_80010000` cmd stream — jump table `0x8001036C`).
2. Map a runtime buffer quad (which the wall renders from) back to its source sub-mesh vertices, so a
   "clicked wall" → editable on-disc vertices.
3. Then a `sculpt_wall.py` (decompress chunk 35 → edit only vertex-Y of the targeted sub-mesh → recompress →
   auto-layout rebuild) becomes safe.

## Tools / repro
Live lever: read/poke `0x8012c1d0` (0x30 quads, Y high16 @ +4/+0xc/+0x14/+0x1c). Codec: `decode_level_raw.py`
/ `recompress_level_raw.py`; build: `build_autolayout_disc.py`. Turn-to-see-wall: `down` 12f + idle ~150f.
