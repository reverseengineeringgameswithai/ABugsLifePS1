/* SetDumpFnt @ 0x80060fb4 - select the debug font id and install its dump handler. */
extern int g_8007f168;
extern int g_8007f16c;
extern int g_8007fbc4;
extern void sub_80061668();
void SetDumpFnt(int id)
{
    if (id < 0)
        return;
    if (g_8007f168 < id)
        return;
    g_8007f16c = id;
    g_8007fbc4 = (int)sub_80061668;
}
