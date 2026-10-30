/* reset_visual_sprite_object_pool - zero the u16 active field of 8 stride-836 slots at 0x8009c870. */
extern short g_8009c870[];

void reset_visual_sprite_object_pool(void)
{
    int off;
    for (off = 5852; off >= 0; off -= 836)
        *(short *)((char *)g_8009c870 + off) = 0;
}
