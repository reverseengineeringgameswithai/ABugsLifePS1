/* CdComstr @ 0x8006D810 — maps a CD command code to its name string via the table
 * at 0x800818EC (28 entries), or a fixed default string at 0x8001C2D8 (PsyQ libcd).
 * INTERNAL-`j` class proof (substrate v2 --section-start): if/else merge -> `j end`.
 * Unsigned bounds check (sltiu), single-return if/else (tbl case first).
 *   a0&=0xff; sltiu v0,a0,28; if in range r=tbl[a0]; else r=(char*)0x8001c2d8
 */
extern char *g_800818ec[];
extern char g_8001c2d8[];   /* default string, la %hi/%lo */
char *CdComstr(int com)
{
    char *r;

    com &= 0xff;
    if ((unsigned int)com < 28)
        r = g_800818ec[com];
    else
        r = g_8001c2d8;
    return r;
}
