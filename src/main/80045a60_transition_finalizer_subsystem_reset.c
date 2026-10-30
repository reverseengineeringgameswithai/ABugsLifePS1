/* transition_finalizer_subsystem_reset @ 0x80045a60 (gp) — clear the low active bit (16-bit mask), reset the CD
 * audio active bit, reset the CD mixer to a zeroed attenuation packet, and stop.
 *   g_80082478 &= 0xfffe; CdMix({0,0,0,0}); CdControl(9,0,0); */
extern int g_80082478;
extern void CdMix(void *);
extern void CdControl(int, int, int);

void transition_finalizer_subsystem_reset(void)
{
    unsigned char pkt[4];
    g_80082478 &= 0xfffe;
    pkt[0] = 0;
    pkt[1] = 0;
    pkt[2] = 0;
    pkt[3] = 0;
    CdMix(pkt);
    CdControl(9, 0, 0);
}
