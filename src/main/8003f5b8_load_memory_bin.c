/* load_memory_bin (gp) - universal_file_loader, record ptr in gp global, call sub_800bd518. */
extern void universal_file_loader(void *cb, void *arg);
extern void sub_800bd518(void);
extern void sub_8001adfc(void);
extern char g_800b5788[16];
extern char g_800d5790[16];
extern void *g_80082320;

void load_memory_bin(void)
{
    universal_file_loader((void *)sub_8001adfc, g_800b5788);
    g_80082320 = g_800d5790;
    sub_800bd518();
}
