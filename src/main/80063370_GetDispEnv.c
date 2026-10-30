/* GetDispEnv @ 0x80063370 - copy the current DISPENV (20 B) into env; returns env. */
extern void *sub_8005f79c(void *dst, void *src, int n);
extern char g_8007fc34[];
void *GetDispEnv(void *env) { sub_8005f79c(env, g_8007fc34, 20); return env; }
