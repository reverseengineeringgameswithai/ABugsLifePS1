/* NextPrim @ 0x80061B3C — returns the "next primitive" pointer packed in the low
 * 24 bits of a prim's ordering-table tag word, re-based into KSEG0 (PsyQ 4.0.0).
 *   lui v1,0xff; lw v0,0(a0); ori v1,0xffff; and; lui v1,0x8000; jr ra; or
 */
int *NextPrim(int *p)
{
    return (int *)((*p & 0x00ffffff) | 0x80000000);
}
