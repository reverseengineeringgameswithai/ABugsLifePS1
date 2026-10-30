/* SsVabFakeHead @ 0x8006b190 - open a VAB header (fake-head variant). */
extern int sub_8006b1c0(int a0, int a1, int a2, int a3);
short SsVabFakeHead(int a0, int a1, int a2)
{
    return (short)sub_8006b1c0(a0, (short)a1, 1, a2);
}
