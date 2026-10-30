/* StGetBackloc @ 0x80070AC0 - libpress/CD stream: return the current back-buffer
 * location. Fails (-1) while the stream lock g_80090744 is held; otherwise asks
 * the ring state at g_80088ff8 for its index (sub_8006de38), advances by one via
 * sub_8006dd34 (which also writes the caller's loc), and returns the resulting
 * sector value g_80088ffc. Healed mis-split: banked as one function over the
 * former 8-byte head + 88-byte tail fragments. */
extern int g_80090744;
extern int g_80088ff8[];
extern int g_80088ffc;
extern int sub_8006de38(void *);
extern int sub_8006dd34(int, void *);

int StGetBackloc(void *loc)
{
    if (g_80090744 != 0)
        return -1;
    sub_8006dd34(sub_8006de38(g_80088ff8) + 1, loc);
    return g_80088ffc;
}
