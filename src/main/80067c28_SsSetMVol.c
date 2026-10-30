/* SsSetMVol @ 0x80067c28 - set the master L/R volume (scaled x129) via the sound cmd. */
extern void sub_8006ce84(void *cmd);
void SsSetMVol(int l, int r)
{
    struct { int type; short lv, rv; char pad[32]; } cmd;

    cmd.type = 3;
    cmd.lv = (short)l * 129;
    cmd.rv = (short)r * 129;
    sub_8006ce84(&cmd);
}
