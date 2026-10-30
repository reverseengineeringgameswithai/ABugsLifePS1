/* CD_vol @ 0x8006eda8 - push a 4-byte CD mixer volume block (LtoL,LtoR,RtoL,RtoR)
 * into the SPU CD-input volume registers via the two staged index/data ports. */
extern unsigned char *g_80081b8c;
extern unsigned char *g_80081b90;
extern unsigned char *g_80081b94;
extern unsigned char *g_80081b98;
int CD_vol(unsigned char *p)
{
    *g_80081b8c = 2;
    *g_80081b94 = p[0];
    *g_80081b98 = p[1];
    *g_80081b8c = 3;
    *g_80081b90 = p[2];
    *g_80081b94 = p[3];
    *g_80081b98 = 32;
    return 0;
}
