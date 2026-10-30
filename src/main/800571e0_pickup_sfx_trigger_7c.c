/* FUNC_800571E0 @ 0x800571E0 — pickup handler (src_re/pickup_handlers_*): stores
 * its two args into the pickup state bytes at 0x800A65A4/0x800A65A5 and fires
 * sound event 124 via FUNC_80026DF4(124, 0, a0 & 0xff). Twin of FUNC_8005721C.
 *   a2=a0; a0=124; sb a1,0x65a5; a1=0; sb a2,0x65a4; jal sub_80026df4; andi a2,0xff
 */
extern unsigned char g_800a65a4;
extern unsigned char g_800a65a5;
extern int sub_80026df4(int a0, int a1, int a2);
void pickup_sfx_trigger_7c(int a0, int a1)
{
    g_800a65a5 = a1;
    g_800a65a4 = a0;
    sub_80026df4(124, 0, a0 & 0xff);
}
