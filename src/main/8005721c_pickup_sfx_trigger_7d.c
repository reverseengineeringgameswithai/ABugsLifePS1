/* FUNC_8005721C @ 0x8005721C — pickup handler (src_re/pickup_handlers_*): stores
 * its two args into the pickup state bytes at 0x800A65A6/0x800A65A7 and fires
 * sound event 125 via FUNC_80026DF4(125, 0, a0 & 0xff). Twin of FUNC_800571E0.
 *   a2=a0; a0=125; sb a1,0x65a7; a1=0; sb a2,0x65a6; jal sub_80026df4; andi a2,0xff
 */
extern unsigned char g_800a65a6;
extern unsigned char g_800a65a7;
extern int sub_80026df4(int a0, int a1, int a2);
void pickup_sfx_trigger_7d(int a0, int a1)
{
    g_800a65a7 = a1;
    g_800a65a6 = a0;
    sub_80026df4(125, 0, a0 & 0xff);
}
