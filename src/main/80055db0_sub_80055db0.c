/* sub_80055db0 @ 0x80055DB0 - burst-spawn 16 effect particles via sub_80055f8c,
 * with per-mode (g_80082504) tuning: drift term, packed BGR color, and a
 * mul/div pair shaping the per-particle magnitude curve (i*(i+2)*mul/divi).
 * Default 8/-1(white)/3/5; modes 2,4,5,8,9,12,13,15 override (e.g. mode 9 =
 * 0xF0F0F0 * 7/10). Passes the caller's counter down, decrementing per spawn,
 * and returns the updated counter. The variable division is why the substrate
 * needs maspsx --expand-div (ASPSX-style break 7 / break 6 guards, discovered
 * here; SHA-1-verified as a global toolchain flag). */
typedef int s32;

extern s32 g_80082504;
extern int sub_80055f8c(s32, s32, s32, s32, s32, s32);

s32 sub_80055db0(s32 arg0, s32 arg1, s32 arg2)
{
    s32 drift;
    s32 color;
    s32 mul;
    s32 divi;
    s32 i;
    s32 mode;

    drift = 8;
    color = -1;
    mul = 3;
    divi = 5;
    mode = g_80082504;
    if (mode == 2)  { drift = -8; color = 0x6060;   mul = 1; divi = 1; }
    if (mode == 4)  { drift = 0;  color = 0x200040; mul = 1; divi = 1; }
    if (mode == 5)  { drift = 0;  color = 0x200040; mul = 1; divi = 1; }
    if (mode == 8)  { drift = 0;  color = 0x303030; mul = 1; divi = 1; }
    if (mode == 9)  { drift = 0;  color = 0xF0F0F0; mul = 7; divi = 10; }
    if (mode == 12) { drift = 0;  color = 0x300050; mul = 3; divi = 5; }
    if (mode == 13) { drift = 0;  color = 0x402000; mul = 1; divi = 1; }
    i = 0;
    if (mode == 15) { drift = 0;  color = 0x81018;  mul = 1; divi = 1; }
    do {
        sub_80055f8c(arg0, arg1, (i * (i + 2) * mul) / divi, arg2, drift, color);
        arg1 = arg1 - 1;
        i = i + 1;
    } while (i < 16);
    return arg1;
}
