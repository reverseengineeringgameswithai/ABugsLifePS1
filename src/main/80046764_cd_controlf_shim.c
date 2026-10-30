/* cd_controlf_shim - reset serial vol, CdControlF(13,{1,mode}), CdIntToPos+CdControlF(27). */
extern void SsSetSerialVol(int voll, int volr, int arg3);
extern void CdControlF(int com, void *param);
extern int  CdIntToPos(int i, void *loc);
extern int  g_80082408;
extern int  g_800821b4;

void cd_controlf_shim(int mode, int sector)
{
    unsigned char loc[8];
    unsigned char param13[8];

    SsSetSerialVol(0, 127, 127);

    param13[0] = 1;
    param13[1] = (unsigned char)mode;
    g_80082408 = mode;
    CdControlF(13, param13);

    CdIntToPos(sector, loc);
    g_800821b4 = sector;
    CdControlF(27, loc);
}
