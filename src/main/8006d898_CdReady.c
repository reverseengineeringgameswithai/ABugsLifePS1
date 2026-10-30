/* CdReady @ 0x8006D898 — thin wrapper: forwards to CD_ready and returns its
 * result (PsyQ libcd). 1-callee wrapper class.
 *   jal CD_ready; return v0
 */
extern int CD_ready(int a0, int a1);
int CdReady(int a0, int a1)
{
    return CD_ready(a0, a1);
}
