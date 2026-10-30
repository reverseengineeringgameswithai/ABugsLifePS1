/* _param @ 0x80064664 - stage a GPU command word (OR 0x10000000) and return the
 * low-24 next-address of the second staged packet. */
extern unsigned int *g_8007fc9c;
extern unsigned int *g_8007fc98;
unsigned int _param(unsigned int cmd)
{
    *g_8007fc9c = cmd | 0x10000000;
    return *g_8007fc98 & 0x00ffffff;
}
