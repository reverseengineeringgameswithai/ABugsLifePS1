/* TermPrim @ 0x80061C10 — libgpu: OR the primitive terminator mask into the tag
 * word and return it.
 *   lui v1,0xff; lw v0,0(a0); ori v1,v1,0xffff; or v0,v0,v1; sw v0,0(a0)
 */
unsigned int TermPrim(unsigned int *p)
{
    unsigned int v = *p | 0x00ffffff;
    *p = v;
    return v;
}
