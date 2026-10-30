typedef int s32; typedef unsigned int u32; typedef unsigned char u8; typedef signed char s8; typedef short s16; typedef unsigned short u16; typedef long s64; typedef unsigned long u64; typedef float f32;
#define NULL 0
extern s32 g_80088ffc;
extern s32 g_80090744;
s32 sub_8006de38(int);                                /* extern */

s32 StGetBackloc(void *arg0) {
    if (g_80090744 == 0) {
        sub_8006dd34(sub_8006de38(0x80088FF8) + 1, arg0);
        return g_80088ffc;
    }
    return -1;
}