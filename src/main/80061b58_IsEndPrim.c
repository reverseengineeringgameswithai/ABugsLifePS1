/* IsEndPrim @ 0x80061B58 — true when a prim's 24-bit next-pointer tag is the
 * 0xFFFFFF terminator (PsyQ 4.0.0).
 *   lw v0,0(a0); v0&=0xffffff; v0^=0xffffff; jr ra; sltiu v0,v0,1
 */
int IsEndPrim(int *p)
{
    return ((*p & 0x00ffffff) ^ 0x00ffffff) < 1;
}
