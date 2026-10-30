/* SetPolyF4 @ 0x80061CC8 — libgpu POLY_F4 primitive initializer (PsyQ 4.0.0). Twin of the matched
 * SetPolyGT4 @ 0x80061D04: sets len at +3 and prim code at +7. Clean-room
 * minimal tag struct (no Sony header). LIBGPU.H SetPolyF4 is
 * `{ setlen(p,5); setcode(p,0x28); }`.
 *   addiu v0,zero,5; sb v0,3(a0); addiu v0,zero,0x28; jr ra; sb v0,7(a0)
 */
typedef struct {
    unsigned char pad0, pad1, pad2, len;    /* +0..+3: 32-bit tag, len at +3 */
    unsigned char pad4, pad5, pad6, code;   /* +4..+7: color triplet + code at +7 */
} PrimTag;

void SetPolyF4(PrimTag *p)
{
    p->len = 5;
    p->code = 0x28;
}
