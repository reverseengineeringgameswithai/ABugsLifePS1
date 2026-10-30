/* SetPolyGT4 @ 0x80061D04 — libgpu primitive initializer (PsyQ 4.0.0).
 *
 * Matching reimplementation for the decomp substrate C path (docs/SUBSTRATE.md).
 * Clean-room: no copyrighted Sony header is used; the primitive tag layout below
 * is our own minimal struct with the field OFFSETS the hardware/prim format fix
 * (len at byte 3, prim code at byte 7 of the 8-byte tag). The public LIBGPU.H
 * SetPolyGT4 is `{ setlen(p,12); setcode(p,0x3c); }`.
 *
 * Stage-1 SDK match: proves the compile pipeline + flags. Compiler/flags pinned
 * in config/segments.yml c_toolchain; evidence EXP_2026-07-08_psyq_compiler_proof.
 */
typedef struct {
    unsigned char pad0, pad1, pad2, len;    /* +0..+3: 32-bit tag, len at +3 */
    unsigned char pad4, pad5, pad6, code;   /* +4..+7: color triplet + code at +7 */
} PrimTag;

void SetPolyGT4(PrimTag *p)
{
    p->len = 12;
    p->code = 0x3c;
}
