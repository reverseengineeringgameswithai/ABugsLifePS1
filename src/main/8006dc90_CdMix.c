/* CdMix @ 0x8006DC90 — thin wrapper: forwards to CD_vol and returns 1 (PsyQ
 * libcd). 1-callee wrapper class (auto-defsym resolves CD_vol by census name).
 *   addiu sp,-24; sw ra; jal CD_vol; lw ra; addiu v0,1; jr ra; addiu sp,24
 */
extern int CD_vol(int a0);
int CdMix(int a0)
{
    CD_vol(a0);
    return 1;
}
