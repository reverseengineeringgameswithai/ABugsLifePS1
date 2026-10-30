/* SetShadeTex @ 0x80061C50 — sets/clears the shade-texture (bit 0) in a primitive's
 * code byte at +7 (PsyQ 4.0.0 libgpu). Internal-`j` class (if/else merge).
 *   if(tge) p[7] |= 1; else p[7] &= 0xfe; then sb p[7]
 */
void SetShadeTex(unsigned char *p, int tge)
{
    if (tge)
        p[7] |= 1;
    else
        p[7] &= 0xfe;
}
