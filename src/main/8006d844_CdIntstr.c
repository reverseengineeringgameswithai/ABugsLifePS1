/* CdIntstr @ 0x8006D844 — maps a CD interrupt code to its name string via the table
 * at 0x8008196C (7 entries), or a fixed default string at 0x8001C2D8 (PsyQ libcd).
 * Internal-`j` class proof. Unsigned bounds check, single-return if/else.
 *   a0&=0xff; sltiu v0,a0,7; if in range r=tbl[a0]; else r=(char*)0x8001c2d8
 */
extern char *g_8008196c[];
extern char g_8001c2d8[];   /* default string, la %hi/%lo */
char *CdIntstr(int intr)
{
    char *r;

    intr &= 0xff;
    if ((unsigned int)intr < 7)
        r = g_8008196c[intr];
    else
        r = g_8001c2d8;
    return r;
}
