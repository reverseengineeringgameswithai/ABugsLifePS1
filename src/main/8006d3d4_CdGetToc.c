/* CdGetToc @ 0x8006D3D4 — forwards to CdGetToc2(1, toc) (PsyQ libcd). 1-callee
 * wrapper with fixed leading arg.
 *   a1=a0; a0=1; jal CdGetToc2
 */
extern void CdGetToc2(int mode, int toc);
void CdGetToc(int toc)
{
    CdGetToc2(1, toc);
}
