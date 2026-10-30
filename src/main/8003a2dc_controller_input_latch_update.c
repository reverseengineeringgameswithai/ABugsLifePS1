/* controller_input_latch_update @ 0x8003a2dc — latch the previous frame's pad
 * word, then refresh it from controller_input_update(1).
 *   g_800822e4 = g_80082412; g_80082412 = controller_input_update(1); */
extern unsigned short g_80082412;   /* current latched pad word */
extern unsigned short g_800822e4;   /* previous-frame copy */
extern int controller_input_update(int);

void controller_input_latch_update(void)
{
    g_800822e4 = g_80082412;
    g_80082412 = controller_input_update(1);
}
