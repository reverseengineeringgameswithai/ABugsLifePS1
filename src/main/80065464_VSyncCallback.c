/* VSyncCallback @ 0x80065464 - install a VSync callback via the kernel event table. */
extern int g_80080de0;
void VSyncCallback(void *func)
{
    (*(void (**)(int, void *))(g_80080de0 + 0x14))(4, func);
}
