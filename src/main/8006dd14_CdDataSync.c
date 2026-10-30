/* CdDataSync @ 0x8006DD14 — thin wrapper: forwards to CD_datasync and returns
 * its result (PsyQ libcd). 1-callee wrapper class.
 *   jal CD_datasync; return v0
 */
extern int CD_datasync(int a0);
int CdDataSync(int a0)
{
    return CD_datasync(a0);
}
