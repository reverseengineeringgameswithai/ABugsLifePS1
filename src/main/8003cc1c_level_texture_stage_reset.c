/* zeroes a 249-byte region ending at 0x8009FB40 (top-down), then level_texture_stage. */
extern char g_8009fb40[];
extern void level_texture_stage(void);

void level_texture_stage_reset(void)
{
    int i = 248;
    char *p = g_8009fb40;
    do {
        *p = 0;
        i -= 1;
        p -= 1;
    } while (i >= 0);
    level_texture_stage();
}
