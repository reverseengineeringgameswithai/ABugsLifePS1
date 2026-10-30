/* _spu_FgetRXXa @ 0x8006c250 - read an SPU reverb table halfword; scale unless flag==-1. */
extern short *g_800814c4;
extern int g_800814ec;
int _spu_FgetRXXa(int idx, int flag)
{
    unsigned short v = g_800814c4[idx];
    if (flag == -1)
        return v;
    return v << g_800814ec;
}
