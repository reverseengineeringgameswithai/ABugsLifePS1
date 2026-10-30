extern int sub_8006c1ac(int);
extern int g_800814ec;
extern short g_800814dc;

unsigned int SpuSetTransferStartAddr(unsigned int addr)
{
    unsigned int v;
    unsigned int lo = addr - 0x1010; if (lo > 0x7efe8) return 0;
    v = sub_8006c1ac(-1);
    g_800814dc = v;
    return (v & 0xffff) << g_800814ec;
}
