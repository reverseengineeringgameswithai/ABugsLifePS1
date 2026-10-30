/* handler_register_8007fbd4 - code selector in $v0; if >=2 call cb; install obj, return old. */
extern void (*g_8007fbc4)(void *, void *);
extern void *g_8007fbd4;
extern char g_8001bfc4[];

void *handler_register_8007fbd4(void *obj)
{
    register unsigned int code asm("$2");
    void *old;

    if (code >= 2)
        g_8007fbc4(g_8001bfc4, obj);
    old = g_8007fbd4;
    g_8007fbd4 = obj;
    return old;
}
