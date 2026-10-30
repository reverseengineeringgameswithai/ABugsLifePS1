/* FUNC_80065edc @ 0x80065EDC — returns the 32-bit global at 0x80080E44.
 * Matching reimplementation. Global meaning UNKNOWN.
 *   lui v0,0x8008; lw v0,0xe44(v0); jr ra
 */
extern int g_80080e44;
int load_global_80080e44(void)
{
    return g_80080e44;
}
