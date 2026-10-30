/* GetDrawEnv @ 0x80062e90 - copy the current DRAWENV (92 B) into env; returns env. */
extern void *sub_8005f79c(void *dst, void *src, int n);
extern char g_8007fbd8[];
void *GetDrawEnv(void *env) { sub_8005f79c(env, g_8007fbd8, 92); return env; }
