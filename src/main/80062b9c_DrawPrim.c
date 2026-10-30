/* DrawPrim @ 0x80062b9c - draw a single primitive via the current GPU driver vtable. */
extern void **g_8007fbc0;
void DrawPrim(unsigned char *prim)
{
    int code = prim[3];

    (*(void (**)(int))(g_8007fbc0 + 15))(0);
    (*(void (**)(void *, int))(g_8007fbc0 + 5))(prim + 4, code);
}
