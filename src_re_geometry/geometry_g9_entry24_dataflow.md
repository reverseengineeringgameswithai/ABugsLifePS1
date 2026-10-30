# G9 entry24 dataflow trace

Status: RUNTIME REJECT RESULT RECORDED (2026-06-14).

Scope: trace pass-1 trail entry24 body values after the CONFIRMED `fcn.800140a0` reads. This is a
dataflow/runbook note only. Do not patch DAT files, build images, run patch scripts, or make
collision/pathing claims from this trace.

## Inputs

Entry24 row base in the confirmed trigger state is `0x80161edc`; the loop body has already advanced
`a0` to `0x80161ef0`, so the body reads use negative offsets from `a0`.

| field | source DAT offset | runtime address | read site | register | confidence |
|-------|------------------:|-----------------|-----------|----------|------------|
| `+0x00` | `0x16e4` | `0x80161edc` | `0x8001419c lw s3,-0x14(a0)` | `s3` | CONFIRMED |
| `+0x04` | `0x16e8` | `0x80161ee0` | `0x80014258 lw t1,-0x10(a0)` | `t1` | CONFIRMED |
| `+0x08` | `0x16ec` | `0x80161ee4` | `0x800141a0 lw s5,-0x0c(a0)` | `s5` | CONFIRMED |
| `+0x0c` | `0x16f0` | `0x80161ee8` | `0x800141a4 lh t4,-0x08(a0)` | `t4` | CONFIRMED |

Upstream values used by this block:

| register/value | source | role | confidence |
|----------------|--------|------|------------|
| `t5/t6/t7` | loaded from `a2=0x1f800384` at `0x800140dc..0x800140e4` | view/camera vector components subtracted from entry fields | LIKELY |
| `s2` | result of earlier `SQR` setup at `0x80014150..0x8001416c` | GTE-derived range threshold used at `0x8001427c` | LIKELY |
| `s7` | result of earlier `SQR` setup at `0x8001411c..0x80014138` | GTE-derived range threshold used at `0x80014300` | LIKELY |
| `a3` | `0x80096ea8` | accepted output pointer list A cursor | LIKELY |
| `s6` | `0x8009e338` | accepted output pointer list B cursor | LIKELY |

GTE opcode labels from static bytes:

| PC | opcode | label | confidence |
|----|--------|-------|------------|
| `0x80014128` | `0x4aa00428` | `SQR` | CONFIRMED |
| `0x8001415c` | `0x4aa00428` | `SQR` | CONFIRMED |
| `0x800141d4` | `0x4a49e012` | `MVMVA` | CONFIRMED |
| `0x8001425c` | `0x4aa00428` | `SQR` | CONFIRMED |
| `0x80014298` | `0x4a49e012` | `MVMVA` | CONFIRMED |

## Static trace: non-negative `+0x0c` path

Entry24 pristine `+0x0c` is `0x02de` (`734`), so the confirmed `+0x04` read uses the non-negative
path beginning at `0x8001423c`.

| PC | instruction | entry24 dataflow | confidence |
|----|-------------|------------------|------------|
| `0x8001419c` | `lw s3,-0x14(a0)` | `s3 = entry24 +0x00` | CONFIRMED |
| `0x800141a0` | `lw s5,-0x0c(a0)` | `s5 = entry24 +0x08` | CONFIRMED |
| `0x800141a4` | `lh t4,-0x08(a0)` | `t4 = sign_extend(entry24 +0x0c)` | CONFIRMED |
| `0x800141a8` | `sub t0,s3,t5` | `t0 = +0x00 - view_vec[0]` | CONFIRMED |
| `0x800141ac` | `bgez t4,0x8001423c` | branch depends on sign of `+0x0c`; entry24 takes this branch | CONFIRMED |
| `0x800141b0` | `sub t2,s5,t7` | delay slot: `t2 = +0x08 - view_vec[2]` | CONFIRMED |
| `0x8001423c` | `sra t9,t0,4` | coarse `(+0x00 - view_vec[0]) >> 4` | CONFIRMED |
| `0x80014240` | `sra s3,t4,4` | `s3` overwritten with `(+0x0c >> 4)` | CONFIRMED |
| `0x80014244` | `sra a1,t2,4` | coarse `(+0x08 - view_vec[2]) >> 4` | CONFIRMED |
| `0x80014248` | `mtc2 t9,t1,0` | coarse X-like component to GTE data reg | CONFIRMED |
| `0x8001424c` | `mtc2 s3,t2,0` | coarse extent/radius-like component to GTE data reg | CONFIRMED |
| `0x80014250` | `mtc2 a1,t3,0` | coarse Z-like component to GTE data reg | CONFIRMED |
| `0x80014258` | `lw t1,-0x10(a0)` | `t1 = entry24 +0x04` | CONFIRMED |
| `0x8001425c` | `SQR` | GTE operation on the coarse values loaded at `0x80014248..0x80014250` | CONFIRMED |
| `0x80014260` | `sub t1,t1,t6` | `t1 = +0x04 - view_vec[1]` | CONFIRMED |
| `0x80014264` | `add at,zero,t3` | preserves the row flag/selector for later `andi a2,at,0x40` | CONFIRMED |
| `0x80014268` | `mfc2 s3,t9,0` | reads first `SQR` output into `s3` | CONFIRMED |
| `0x8001426c` | `mfc2 t9,k0,0` | reads second `SQR` output into `t9` | CONFIRMED |
| `0x80014270` | `mfc2 a1,k1,0` | reads third `SQR` output into `a1` | CONFIRMED |
| `0x80014274..0x8001427c` | `sub/add/sub` | combines `SQR` outputs and threshold `s2` into `s3` | LIKELY |
| `0x80014280` | `bgez s3,0x80014170` | first reject branch; if taken, entry24 produces no output-list write this pass | LIKELY |
| `0x80014284` | `mtc2 t0,t1,0` | full `(+0x00 - view_vec[0])` to GTE data reg | CONFIRMED |
| `0x80014288` | `mtc2 t1,t2,0` | full `(+0x04 - view_vec[1])` to GTE data reg | CONFIRMED |
| `0x8001428c` | `mtc2 t2,t3,0` | full `(+0x08 - view_vec[2])` to GTE data reg | CONFIRMED |
| `0x80014298` | `MVMVA` | transforms the full difference vector | CONFIRMED |
| `0x800142a4` | `mfc2 t1,k1,0` | transformed component/axis result | CONFIRMED |
| `0x800142a8` | `mfc2 a1,t9,0` | transformed component/axis result | CONFIRMED |
| `0x800142b0` | branch on `t0` to `0x80014170` | reject branch after `t0=t1+t4`; depends on transformed result and `+0x0c` | LIKELY |
| `0x800142b4` | `mfc2 a2,k0,0` | transformed component/axis result | CONFIRMED |
| `0x800142b8..0x800142e8` | sign/extent tests | compares transformed `a1/a2` magnitudes against `t1/t4` derived thresholds | LIKELY |
| `0x800142ec..0x800142f4` | `sub/sub/bgez` | reject branch using `t1`, `t4`, and `t8` (`[0x80082440]`-derived size) | LIKELY |
| `0x800142f8` | `andi a2,at,0x40` | row flag bit selects output list path | CONFIRMED |
| `0x80014300..0x80014304` | `sub t9,t9,s7; bgez t9,0x80014170` | additional reject branch before list A write | LIKELY |
| `0x80014308..0x80014310` | `addi t0,a0,-0x14; sw t0,(a3)` | writes entry row pointer (`0x80161edc`) to list A at current `a3` | LIKELY |
| `0x8001431c..0x80014324` | `addi t0,a0,-0x14; sw t0,(s6)` | writes entry row pointer (`0x80161edc`) to list B at current `s6` when flag bit `0x40` is set | LIKELY |

Static boundary: the next meaningful boundary is either an early loop-back reject to `0x80014170` or
an accepted row-pointer write to output list A (`0x8001430c`) or list B (`0x80014320`).

## Runtime stepping result

Operator used DuckStation CPU debugger in the known entry24 trigger state, starting from a read watch:

| field | value |
|-------|-------|
| watch | `READ 0x80161ee0` |
| field | pass-1 trail entry24 `+0x04` |
| DAT offset | `0x16e8` |
| runtime address | `0x80161ee0` |
| PC shown at read hit | `0x8001425c` |
| actual read site | `0x80014258` |
| `a0` | `0x80161ef0` |

The operator then single-stepped forward through the GTE/math path:

| PC | observed register | branch result | interpretation | confidence |
|----|-------------------|---------------|----------------|------------|
| `0x80014280` | `s3 = 0xffff262b` | `bgez s3,0x80014170` NOT taken | `s3` is negative; entry24 passes the first reject test | CONFIRMED |
| `0x800142b0` | `t0 = 0x000010b1` | operator-observed `bgtz t0,0x80014170` taken | entry24 rejects here and does not reach later list-write/output path in this tested state | CONFIRMED |

Confirmed runtime conclusion:

> entry24 is read by `fcn.800140a0` and participates in GTE/math reject testing, but in the tested
> edge-of-level state it rejects at `0x800142b0` before the late list-write path.

This explains the G8 visual results conservatively:

| candidate | field | result | likely reason |
|-----------|-------|--------|---------------|
| A | `+0x08` `+256` | valid/read, no visual change | patched field influences reject calculation, but entry24 still does not reach list output in this state |
| A2 | `+0x08` `+1024` | valid/read/RAM-confirmed, no visual change | same |
| C | `+0x04` `+1024` | valid/read, no visual change | same |

Do not overstate this result:

- **UNKNOWN** whether entry24 can survive in another camera/player state.
- **UNKNOWN** whether the late list writes at `0x8001430c` / `0x80014320` are render visibility lists,
  though this remains **LIKELY** from static context.
- Collision/pathing impact remains **UNKNOWN**.

Earlier noisy EXEC observation: the late write path was observed for another row with
`t0=0x80161f40`, not entry24 rowbase `0x80161edc`. Therefore do not claim entry24 reached the
list-write path.

Mapping for that other late-write row:

| item | value |
|------|-------|
| observed rowbase | `0x80161f40` |
| `G_TRAIL_BLOCK_PTR` | `0x80161cfc` |
| row size | `0x14` |
| delta | `0x244` |
| entry index | `(0x80161f40 - 0x80161cfc) / 0x14 = 0x244 / 0x14 = 29` |
| row DAT `+0x00` | `0x1504 + 0x244 = 0x1748` |
| row DAT `+0x04` | `0x174c` |
| row DAT `+0x08` | `0x1750` |
| row DAT `+0x0c` | `0x1754` |

The rowbase aligns cleanly, so the runtime clue maps to pass-1 trail entry29. Entry29 is a better
G9b candidate than entry24 because it was observed at the late list-write path, while entry24 was
observed rejecting before that path in this state.

RAM/save-state note: a RAM dump alone would not have proven this branch result because the decisive
evidence was transient CPU/GTE register state at specific PCs. The saved state remains useful for
reproducing the trigger, but manual stepping or a CPU/GTE-aware trace is required to confirm
reject/list-write behavior.

## Field-by-field summary

| field | source DAT offset | read instruction | register loaded | next uses | GTE affected | downstream output/write | confidence |
|-------|------------------:|------------------|-----------------|-----------|--------------|-------------------------|------------|
| `+0x00` | `0x16e4` | `0x8001419c lw s3,-0x14(a0)` | `s3` | `t0=s3-t5`; `t9=t0>>4`; later `mtc2 t9,t1` and `mtc2 t0,t1` | coarse `SQR` input and full `MVMVA` input | no direct value write; if accepted, row pointer `a0-0x14` is written to list A/B | CONFIRMED dataflow through GTE; LIKELY culling/range role |
| `+0x04` | `0x16e8` | `0x80014258 lw t1,-0x10(a0)` | `t1` | `t1=t1-t6`; later `mtc2 t1,t2`; branch tests use MVMVA results | full `MVMVA` input paired with `+0x00/+0x08` | no direct value write; affects pass/reject before possible row-pointer write | CONFIRMED read and pair with vector; LIKELY culling/range role |
| `+0x08` | `0x16ec` | `0x800141a0 lw s5,-0x0c(a0)` | `s5` | `t2=s5-t7`; `a1=t2>>4`; later `mtc2 a1,t3` and `mtc2 t2,t3` | coarse `SQR` input and full `MVMVA` input | no direct value write; affects pass/reject before possible row-pointer write | CONFIRMED dataflow through GTE; LIKELY culling/range role |
| `+0x0c` | `0x16f0` | `0x800141a4 lh t4,-0x08(a0)` | `t4` | sign branch; `t4>>4` to coarse `SQR`; added/subtracted as extent/radius term in reject tests | coarse `SQR` input and scalar threshold around MVMVA outputs | no direct value write; affects branch path, reject thresholds, and possible list choice via flag-preserved path | CONFIRMED branch control; LIKELY radius/extent/bounds term |

## Conservative answers

- `+0x08` does not appear to feed a direct visible coordinate in this block. It is differenced against
  `t7`, right-shifted for the coarse `SQR` test, and later loaded as part of the full vector for
  `MVMVA`. Static evidence therefore points to a GTE culling/range/vector calculation, not a direct
  mesh-position write. Confidence: LIKELY.
- `+0x04` is paired with `+0x00` and `+0x08` as the middle component of a three-component difference
  vector: `(+0x00-t5, +0x04-t6, +0x08-t7)`. It is also interpreted under the `+0x0c >= 0` path.
  Confidence: CONFIRMED for the arithmetic pairing, LIKELY for axis/semantic names.
- Entry24 is more likely a culling/bounds/range row than a mesh-position row in `fcn.800140a0`.
  Evidence: the block subtracts a view vector, runs `SQR` and `MVMVA`, performs several reject
  branches, then writes the row pointer to output pointer lists if accepted. No direct GPU primitive,
  vertex, or visible coordinate write was observed in this block. Confidence: LIKELY.
- Best next downstream value to watch: the accepted row-pointer write. Watch/step at `0x8001430c`
  (`sw t0,(a3)`, list A base `0x80096ea8`) and `0x80014320` (`sw t0,(s6)`, list B base `0x8009e338`)
  and record whether the stored value is entry24 row base `0x80161edc`. Also record the first reject
  branch if the row loops back before either write.

## DuckStation G9 runtime runbook

Saved trigger context:

- Use `~/.local/share/duckstation/savestates/SCUS-94288_1.sav` if available. It exists on
  the operator machine and was captured near/at the entry24 trigger state.
- `pause_at_80161EE4.ram` was referenced in prior notes, but was not found in the repo or searched
  DuckStation paths during this documentation pass. Treat it as optional external operator context,
  not as a committed artifact.

Breakpoints and watches:

| type | address/PC | purpose |
|------|------------|---------|
| execute | `0x8001419c` | confirm `+0x00` read and `a0=0x80161ef0` |
| execute | `0x800141a0` | confirm `+0x08` read |
| execute | `0x800141a4` | confirm `+0x0c` read |
| execute | `0x8001423c` | confirm non-negative path is taken |
| execute | `0x80014258` | confirm `+0x04` read |
| execute | `0x80014280` | first GTE-derived reject branch |
| execute | `0x80014298` | full-vector `MVMVA` command |
| execute | `0x800142a4` | first post-`MVMVA` `mfc2` output |
| execute | `0x800142b0` | transformed-depth/extent reject branch |
| execute | `0x800142c8` | transformed lateral/extent reject branch |
| execute | `0x800142e8` | transformed lateral/extent reject branch |
| execute | `0x800142f4` | size/range reject branch |
| execute | `0x80014304` | list-A prewrite reject branch |
| execute | `0x8001430c` | output list A write |
| execute | `0x80014320` | output list B write |
| read watch | `0x80161edc/0x80161ee0/0x80161ee4/0x80161ee8` | optional re-confirm body reads |
| write watch | `0x80096ea8` | initial list A base write; if entries advance, step at `0x8001430c` |
| write watch | `0x8009e338` | initial list B base write; if entries advance, step at `0x80014320` |

Record one row per stop:

| PC | record |
|----|--------|
| read sites | `a0`, `a0-0x14`, loaded register (`s3/s5/t4/t1`), raw memory value |
| vector setup | `t0`, `t1`, `t2`, `t4`, `t5`, `t6`, `t7`, `t9`, `a1` |
| after `SQR` mfc2 | `s3`, `t9`, `a1`, branch result at `0x80014280` |
| after `MVMVA` mfc2 | `t1`, `a1`, `a2`, branch results at `0x800142b0/0x800142c8/0x800142e8/0x800142f4/0x80014304` |
| output write | write PC, target address (`a3` or `s6`), stored value (`t0`), expected entry24 row pointer `0x80161edc` |

Decision rule:

- If entry24 reaches `0x8001430c` or `0x80014320` and stores `0x80161edc`, record
  `CONFIRMED output-list membership` for entry24 and identify which list accepted it.
- If entry24 loops back to `0x80014170` before either write, record the first reject branch and the
  register values that caused it.
- Treat near-zero branch margins as the best future perturbation target only after runtime dataflow
  confirms them. G9 should prefer confirming output-list membership and branch margins over new DAT
  perturbations.

Next recommended experiment: **G9b** -- find a row that survives to `0x8001430c` or `0x80014320`,
then map that row back to its DAT offset and test whether its body fields produce visible changes.
The immediate candidate from runtime is entry29 (`rowbase=0x80161f40`, DAT row `0x1748`). Prefer
dataflow confirmation and mapping over new entry24 perturbations.

## → G10: what happens to survivors after the list write

The list-write path this trace stops at is decoded in
[`geometry_g10_payload_render_chain.md`](geometry_g10_payload_render_chain.md). Survivor row pointers
written to `LIST_A` (`0x80096ea8`) are consumed by `fcn.8001ea6c` / `fcn.800206e8`, which bridge
`row+0x10` → output record → `+0x18` → source record → `+0x14/+0x1c` → payload band
`[0x8bd8,0x4f32c]`, read the source `vec[3]` as the object's render position, and pack GPU primitives.
G10 maps **entry29** fully: source `@0x7388` (`vec`, `scale`, `angle`) → payload `@0x2f2f8`. The
recommended visible-geometry edit target is therefore the **source record / payload of a surviving
row**, not a trail/cull body field.

G10 §7 runtime (2026-06-14): a READ watch on entry29 source `vec[0]` (`0x80167b80`) hit inside the
builder, and the kind-dispatch (`0x8001eb34`) selected case `0x8001ec44`, which is statically decoded
(reads `vec`/`angle`/`scale`/payload-ptr, tail-calls emitter `fcn.80010000`).
