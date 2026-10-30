/* FUNC_80065ec4 @ 0x80065EC4 — sets the global at 0x80080E44 to a0 and returns
 * its previous value. Matching reimplementation. Global meaning UNKNOWN.
 *   lw v0,0xe44(0x8008); sw a0,0xe44(0x8008); jr ra (returns old value)
 */
extern int g_80080e44;
int swap_global_80080e44(int a0)
{
    int v = g_80080e44;
    g_80080e44 = a0;
    return v;
}
