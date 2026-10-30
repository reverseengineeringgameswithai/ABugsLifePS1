/* CdGetSector @ 0x8006DCB0 — thin wrapper: forwards to CD_getsector and returns
 * whether it returned 0 (PsyQ libcd). 1-callee wrapper class.
 *   jal CD_getsector; sltiu v0,v0,1 (return result == 0)
 */
extern int CD_getsector(int a0, int a1);
int CdGetSector(int a0, int a1)
{
    return CD_getsector(a0, a1) == 0;
}
