/* cd_controlb_shim @ 0x800467dc (gp) — issue CdControlB(0x0e) with a one-byte
 * mode packet (232), quiesce with CdControlF(9), then set the active bit.
 *   CdControlB(14, {232}, 0); CdControlF(9, 0); g_80082478 |= 1; */
extern int g_80082478;
extern void CdControlB(int, void *, int);
extern void CdControlF(int, void *);

void cd_controlb_shim(void)
{
    unsigned char pkt[4];
    pkt[0] = 232;
    CdControlB(14, pkt, 0);
    CdControlF(9, 0);
    g_80082478 |= 1;
}
