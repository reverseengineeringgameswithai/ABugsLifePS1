/* CdDataCallback @ 0x8006DCF0 — installs the CD data-ready callback by forwarding
 * to DMACallback(3, cb) (PsyQ libcd). 1-callee wrapper with fixed leading arg.
 *   a1=a0; a0=3; jal DMACallback
 */
extern void DMACallback(int ch, int cb);
void CdDataCallback(int cb)
{
    DMACallback(3, cb);
}
