/* SetSemiTrans @ 0x80061C28 — sets/clears the semi-transparency (ABE, bit 1) in a
 * primitive's code byte at +7 (PsyQ 4.0.0 libgpu). INTERNAL-`j` class proof
 * (substrate v2 --section-start fix): the if/else merge compiles to `j`.
 *   if(abe) p[7] |= 2; else p[7] &= 0xfd; then sb p[7]
 */
void SetSemiTrans(unsigned char *p, int abe)
{
    if (abe)
        p[7] |= 2;
    else
        p[7] &= 0xfd;
}
