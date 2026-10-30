extern int sub_8006bde4();
extern unsigned short g_800814dc;
extern int g_800814ec;
int _spu_Fr(int a, int b)
{
    unsigned int x = g_800814dc << g_800814ec;
    sub_8006bde4(2, x);
    sub_8006bde4(0, x);
    sub_8006bde4(3, a, b);
    return b;
}
