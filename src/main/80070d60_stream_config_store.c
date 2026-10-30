/* stores three args into three scattered globals. Fields UNKNOWN. */
extern int g_800b0d08;
extern int g_8009538c;
extern int g_800b0cc0;

void stream_config_store(int a, int b, int c)
{
    g_800b0d08 = a;
    g_8009538c = b;
    g_800b0cc0 = c;
}
