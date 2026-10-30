/* setIntrVSync @ 0x80065BC4 — writes val into the interrupt-callback table at
 * 0x80080DF4 index i, only if it differs (PsyQ libapi). Matching reimplementation.
 *   p=&tbl[i]; if(*p != val) *p = val;
 */
extern int g_80080df4[];
void setIntrVSync(int i, int val)
{
    if (val != g_80080df4[i])
        g_80080df4[i] = val;
}
