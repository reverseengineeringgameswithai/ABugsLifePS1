/* gte_mesh_assembler_counted @ 0x800390f0 (gp) - run the assembler, bump a gp counter, return it. */
extern void gte_rtps_mesh_assembler(void);
extern volatile int g_80082438;

int gte_mesh_assembler_counted(void)
{
    gte_rtps_mesh_assembler();
    g_80082438 = g_80082438 + 1;
    return g_80082438;
}
