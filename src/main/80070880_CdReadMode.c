/* CdReadMode @ 0x80070880 — sets the CD read-mode global (0x80081C10) to a0 and
 * returns the previous value (PsyQ libcd). Swap via a materialized address
 * (la form): the address is taken into a pointer, then loaded/stored through it.
 *   lui v1,0x8008; addiu v1,v1,0x1c10; lw v0,0(v1); sw a0,0(v1); jr ra
 */
extern volatile int g_80081c10;
int CdReadMode(int a0)
{
    volatile int *p = &g_80081c10;
    int v = *p;
    *p = a0;
    return v;
}
