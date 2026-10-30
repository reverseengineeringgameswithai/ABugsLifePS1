/* FUNC_80069604 @ 0x80069604 — zeroes the 16-bit global at 0x80091610.
 * Matching reimplementation. Global meaning UNKNOWN.
 *   lui at,0x8009; sh zero,0x1610(at); jr ra
 */
extern short g_80091610;
void clear_global_short_80091610(void)
{
    g_80091610 = 0;
}
