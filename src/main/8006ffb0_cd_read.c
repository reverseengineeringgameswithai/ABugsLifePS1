/* cd_read @ 0x8006ffb0 - seek to a position and start reading sectors; 1 on success. */
extern void sub_8006dd34(int pos, void *loc);
extern void sub_8006d8e8(int cmd, void *loc, int arg);
extern void sub_80070698(int mode, int sectors, int size);
extern int sub_8007079c(int a, int b);
int cd_read(int mode, int pos, int sectors)
{
    char loc[8];

    sub_8006dd34(pos, loc);
    sub_8006d8e8(2, loc, 0);
    sub_80070698(mode, sectors, 128);
    return sub_8007079c(0, 0) == 0;
}
