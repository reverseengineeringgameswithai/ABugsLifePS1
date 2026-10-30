/* scene_config_apply @ 0x80055538 - unpack a scene-config record into runtime
 * globals (scalar fields, two lookup-indexed calls, two byte-copy tables). Call
 * args hoisted between the scalar stores to match the compiler's schedule. */
extern unsigned char g_800a65a0;
extern short g_80082284;
extern short g_80078b64[];
extern short g_80078b84[];
extern unsigned char g_8009b878[];
extern unsigned char g_80089938[];
extern void sub_8003f4d4(int a, int b);
extern void sub_80044ce8(int a, int b);
void scene_config_apply(unsigned char *cfg)
{
    int i;
    g_800a65a0 = cfg[0];
    {
        int a1 = *(short *)(cfg + 24);
        int a2 = *(short *)(cfg + 26);
        g_80082284 = cfg[1];
        sub_8003f4d4(a1, a2);
    }
    sub_80044ce8(g_80078b64[cfg[22]], g_80078b84[cfg[23]]);
    for (i = 0; i < 19; i++) { unsigned char *s = cfg + i; g_8009b878[i] = s[2]; }
    for (i = 0; i < 320; i += 5) {
        unsigned char *s = cfg + i;
        g_80089938[i+0]=s[28]; g_80089938[i+1]=s[29]; g_80089938[i+2]=s[30];
        g_80089938[i+3]=s[31]; g_80089938[i+4]=s[32];
    }
}
