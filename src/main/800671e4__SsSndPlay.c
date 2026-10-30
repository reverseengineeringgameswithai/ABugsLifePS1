/* _SsSndPlay @ 0x800671e4 - play a sound (prog, tone as 16-bit). */
extern void sub_80067210(int prog, int tone);
void _SsSndPlay(int prog, int tone) { sub_80067210((short)prog, (short)tone); }
