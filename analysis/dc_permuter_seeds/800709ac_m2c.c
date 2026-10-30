typedef int s32; typedef unsigned int u32; typedef unsigned char u8; typedef signed char s8; typedef short s16; typedef unsigned short u16; typedef long s64; typedef unsigned long u64; typedef float f32;
#define NULL 0
extern s32 g_800818e8;
extern s8 *g_80081c28;
extern s8 *g_80081c34;
int sub_800b9a14(int);                                  /* extern */
int sub_800b9a28(int);                                  /* extern */
int sub_80065fbc();                                   /* static */
int sub_80065fcc();                                   /* static */

void sub_800709ac(void) {
    sub_80065fbc();
    if (g_800818e8 == 1) {
        sub_800b9a28(0);
        sub_800b9a14(0);
    } else {
        sub_8006dcf0(0);
        sub_8006d8d0(0);
    }
    (*g_80081c28) = 0;
    (*g_80081c34) = 0;
    sub_80065fcc();
}