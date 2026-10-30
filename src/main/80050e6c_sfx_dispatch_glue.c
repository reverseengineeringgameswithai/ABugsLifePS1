/* sfx_dispatch_glue @ 0x80050e6c — arm sfx params then fire sound id 51.
 *   sw a0,g_80082370; sh 1,g_8008229c; jal sfx_dispatch(51) */
extern int g_80082370;
extern short g_8008229c;
extern void sfx_dispatch(int);

void sfx_dispatch_glue(int a0)
{
    g_80082370 = a0;
    g_8008229c = 1;
    sfx_dispatch(51);
}
