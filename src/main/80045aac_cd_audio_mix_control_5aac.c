/* cd_audio_mix_control_5aac - build CD mix vol {b,0,b,0} from 0x80082218, CdMix, CdControl(12), CdControlF(27). */
extern unsigned short g_80082218;
extern void CdMix(void *vol);
extern int CdControl(int com, int param, int result);
extern int CdControlF(int com, int param);

void cd_audio_mix_control_5aac(void)
{
    unsigned char vol[4];

    vol[0] = (unsigned char)g_80082218;
    vol[1] = 0;
    vol[2] = (unsigned char)g_80082218;
    vol[3] = 0;
    CdMix(vol);
    CdControl(12, 0, 0);
    CdControlF(27, 0);
}
