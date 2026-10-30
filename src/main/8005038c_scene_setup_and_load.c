/* scene_setup_and_load - clear handle, if scene valid record base + display/resource init, dispatch frontend, restore. */
extern int g_80082504;
extern int g_800823ac;
extern void display_buffers_init(void);
extern void resource_id_dat_load_dispatcher(int id);
extern void sub_800b96e4(int a0);

void scene_setup_and_load(int a0, int scene_id)
{
    int saved = g_80082504;

    g_80082504 = 0;
    if (scene_id != -1) {
        g_800823ac = scene_id + 1084;
        display_buffers_init();
        resource_id_dat_load_dispatcher(0);
    }
    sub_800b96e4(a0);
    g_80082504 = saved;
}
